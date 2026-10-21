// ============================================================
// ingest-bundle.ts — SATU jalur materialisasi bundle (FR-1/FR-2)
// untuk SEMUA sumber: unggah ZIP, pilih folder (auto-ZIP browser),
// dan tarik Google Drive. Writer meng-ekstrak aturan yang tadinya
// hidup di route upload: sanitasi path (anti traversal/__MACOSX/._),
// filter .xls*, tulis ke bundles/{bundleId}/, statistik folder
// kanonik computeFolderStats(), lalu manifest via saveBundleMeta().
// ============================================================
import "server-only";
import { promises as fs } from "fs";
import path from "path";
import { bundleDir, computeFolderStats, saveBundleMeta, sweepServerlessBundles } from "@/lib/bundles";
import type { BundleManifest } from "@/lib/types";

const EXCEL_RE = /\.(xlsx|xls|xlsb|xlsm)$/i; // xlsm: engine FastAPI juga membacanya (audit 48-g-engine)

export class BundleEmptyError extends Error {
  constructor() {
    super(
      "Tidak ada file Excel (.xlsx/.xls/.xlsb) di dalam bundle — pastikan ini bundle export Accurate (struktur 14 folder config.json).",
    );
    this.name = "BundleEmptyError";
  }
}

/** Batas kumulatif file Excel terlampaui (anti zip-bomb, audit 48-g-api). */
export class BundleLimitError extends Error {
  constructor(maxBytes: number) {
    super(`Total file Excel melebihi batas ${(maxBytes / 1024 / 1024).toFixed(0)} MB — bundle dilepas.`);
    this.name = "BundleLimitError";
  }
}

/** Disk penyimpanan bundle penuh (ENOSPC) — kuota /tmp serverless terlampaui
 *  oleh tarikan/unggahan sebesar itu (terverifikasi live di Vercel 2026-10-21:
 *  bundle 130 MB + tumpukan bundle lama → "no space left on device"). */
export class BundleDiskFullError extends Error {
  constructor() {
    super(
      "Penyimpanan bundle penuh (kuota disk serverless terlampaui) — bundle lama otomatis dibersihkan saat tarikan/unggahan berikutnya. Bila masih gagal: kecilkan tarikan (per folder) atau jalankan di instalasi lokal (sandbox/PC) yang tanpa kuota serverless.",
    );
    this.name = "BundleDiskFullError";
  }
}

export type BundleWriter = {
  /** Tulis satu entri (path relatif di dalam bundle). Entri tidak aman
   *  (traversal/absolut/__MACOSX/._x/non-Excel) dilewati & dihitung. */
  write(relPath: string, data: Uint8Array): Promise<void>;
  /** Selesaikan bundle: manifest FR-2 + meta JSON. Lempar BundleEmptyError
   *  bila tidak ada satu pun file Excel yang tertulis. */
  finish(meta: {
    name: string;
    source?: "upload" | "drive";
    skippedEntriesExtra?: number;
    extras?: Pick<
      BundleManifest,
      "skippedDuplicates" | "suffixedDuplicates" | "driveFolders" | "skippedFiles" | "driveNotices"
    >;
  }): Promise<BundleManifest>;
  /** Buang bundle yang setengah jadi (folder + seluruh isinya). */
  abort(): Promise<void>;
};

export async function createBundleWriter(
  bundleId: string,
  opts: { maxFileBytes?: number; maxTotalBytes?: number } = {},
): Promise<BundleWriter> {
  const dir = bundleDir(bundleId); // validasi bundleId sekali di sini
  // Serverless: /tmp sempit & efemeral — bersihkan bundle lama dulu supaya
  // tarikan besar tidak menabrak ENOSPC (bundle baru di-keep by id).
  await sweepServerlessBundles(bundleId);
  await fs.mkdir(dir, { recursive: true });

  let fileCount = 0;
  let totalBytes = 0;
  let skippedEntries = 0;
  const excelEntries: { path: string; bytes: number }[] = [];
  let aborted = false;

  const checkAborted = () => {
    if (aborted) throw new Error("Writer sudah di-abort.");
  };

  return {
    async write(relPath: string, data: Uint8Array): Promise<void> {
      checkAborted();
      if (relPath.endsWith("/")) return; // entri direktori
      if (
        relPath.startsWith("__MACOSX/") ||
        relPath.includes("/__MACOSX/") ||
        path.basename(relPath).startsWith("._")
      ) {
        skippedEntries += 1;
        return;
      }
      // sanitasi path: larang traversal / absolut (identik route upload lama)
      const norm = path.normalize(relPath).replace(/^(\.\.(\/|\\|$))+/, "");
      if (!norm || path.isAbsolute(norm) || norm.startsWith("..") || norm.includes("\0")) {
        skippedEntries += 1;
        return;
      }
      if (!EXCEL_RE.test(norm)) {
        skippedEntries += 1; // non-Excel dilewati (bundle = folder export .xls*)
        return;
      }
      const dest = path.join(dir, norm);
      if (!dest.startsWith(dir + path.sep)) {
        skippedEntries += 1;
        return;
      }
      // Batas ukuran (anti zip-bomb / file raksasa — audit 48-g-api): entri
      // per-file kelewat besar dihitung dilewati; total kumulatif → gagal jujur.
      if (opts.maxFileBytes !== undefined && data.byteLength > opts.maxFileBytes) {
        skippedEntries += 1;
        return;
      }
      if (opts.maxTotalBytes !== undefined && totalBytes + data.byteLength > opts.maxTotalBytes) {
        throw new BundleLimitError(opts.maxTotalBytes);
      }
      await fs.mkdir(path.dirname(dest), { recursive: true });
      try {
        await fs.writeFile(dest, data);
      } catch (err) {
        if ((err as NodeJS.ErrnoException)?.code === "ENOSPC") throw new BundleDiskFullError();
        throw err;
      }
      fileCount += 1;
      totalBytes += data.byteLength;
      excelEntries.push({ path: norm, bytes: data.byteLength });
    },

    async finish(meta): Promise<BundleManifest> {
      checkAborted();
      if (fileCount === 0) {
        throw new BundleEmptyError();
      }
      const { folders, missingFolders } = computeFolderStats(excelEntries);
      const manifest: BundleManifest = {
        bundleId,
        name: meta.name,
        uploadedAt: new Date().toISOString(),
        fileCount,
        totalBytes,
        skippedEntries: skippedEntries + (meta.skippedEntriesExtra ?? 0),
        folders,
        missingFolders,
        ...(meta.source ? { source: meta.source } : {}),
        ...(meta.extras?.skippedDuplicates ? { skippedDuplicates: meta.extras.skippedDuplicates } : {}),
        ...(meta.extras?.suffixedDuplicates ? { suffixedDuplicates: meta.extras.suffixedDuplicates } : {}),
        ...(meta.extras?.driveFolders ? { driveFolders: meta.extras.driveFolders } : {}),
        ...(meta.extras?.skippedFiles ? { skippedFiles: meta.extras.skippedFiles } : {}),
        ...(meta.extras?.driveNotices ? { driveNotices: meta.extras.driveNotices } : {}),
      };
      await saveBundleMeta(manifest);
      return manifest;
    },

    async abort(): Promise<void> {
      aborted = true;
      await fs.rm(dir, { recursive: true, force: true }).catch(() => undefined);
    },
  };
}
