// bundles.ts — Registry bundle upload produksi (FR-1): ZIP Accurate diekstrak
// ke bundles/{bundleId}/, meta JSON di sampingnya; engine produksi menerima
// path hasil resolveBundlePath() (FR-10 bundlePath). Idempotensi komit (FR-12)
// memakai bundleId yang sama → bundlePath yang sama → hasil identik.
import "server-only";
import { promises as fs } from "fs";
import path from "path";
import type { BundleFolderStat, BundleManifest } from "@/lib/types";

export const BUNDLES_DIR = path.join(process.cwd(), "bundles");

/** Pemetaan folder kunci config.json — IDENTIK desktop v3.9.71 (FR-2). */
export const FOLDER_TEMPLATE: { folderKey: string; folderName: string }[] = [
  { folderKey: "RekapBerjalan", folderName: "1. DEVIASI WEEKLY" },
  { folderKey: "RekapLalu", folderName: "1.12 Rekap Mentah Bulan Lalu" },
  { folderKey: "Penjualan2205", folderName: "2. 22.05" },
  { folderKey: "Kirim4215", folderName: "3.1 42.15 Kirim" },
  { folderKey: "Terima4215", folderName: "3. 42.15" },
  { folderKey: "RI3224", folderName: "13. 32.24 RI" },
  { folderKey: "RI3224Lalu", folderName: "13.2 3224 RI Bulan Lalu" },
  { folderKey: "SaldoAwal4217", folderName: "6.1 42.17 Saldo Awal" },
  { folderKey: "DBSKategori", folderName: "21. DBS Kategori" },
  { folderKey: "Pemindahan4205", folderName: "4. 42.05" },
  { folderKey: "Pemindahan4205Lalu", folderName: "4.1 4205 Bulan Lalu" },
  { folderKey: "RincianPO", folderName: "25. Rincian PO" },
  { folderKey: "Data9901", folderName: "30. 9901" },
  { folderKey: "Harga", folderName: "09.Harga" },
];

const ID_RE = /^[a-f0-9-]{8,64}$/i;

export function bundleDir(bundleId: string): string {
  if (!ID_RE.test(bundleId)) {
    throw new Error("bundleId tidak valid.");
  }
  return path.join(BUNDLES_DIR, bundleId);
}

export function bundleMetaPath(bundleId: string): string {
  return `${bundleDir(bundleId)}.json`;
}

export async function saveBundleMeta(manifest: BundleManifest): Promise<void> {
  await fs.writeFile(bundleMetaPath(manifest.bundleId), JSON.stringify(manifest), "utf-8");
}

export async function readBundleMeta(bundleId: string): Promise<BundleManifest | null> {
  try {
    const raw = await fs.readFile(bundleMetaPath(bundleId), "utf-8");
    return JSON.parse(raw) as BundleManifest;
  } catch {
    return null;
  }
}

const topSegment = (p: string) => p.split(/[/\\]/)[0];

/**
 * Statistik folder kanonik (FR-2) dari daftar path file Excel hasil ekstraksi.
 * Bila TIDAK ada folder kanonik di level teratas DAN semua file berada di
 * bawah SATU folder pembungkus (mis. ZIP hasil macOS "Compress" atau pilih
 * folder induk via webkitdirectory), statistik dihitung satu level di bawahnya —
 * konsisten dengan resolveBundlePath() yang juga menurunkan RootPath engine
 * satu level, sehingga manifest UI tak pernah bertentangan dengan engine.
 */
export function computeFolderStats(entries: { path: string; bytes: number }[]): {
  folders: BundleFolderStat[];
  missingFolders: string[];
} {
  const canonical = new Set(FOLDER_TEMPLATE.map((t) => t.folderName));
  const topHasCanonical = entries.some((e) => canonical.has(topSegment(e.path)));
  const tops = new Set(entries.map((e) => topSegment(e.path)));
  const unwrap = !topHasCanonical && tops.size === 1;

  const stat = new Map<string, BundleFolderStat>(
    FOLDER_TEMPLATE.map((t) => [
      t.folderName,
      { folderKey: t.folderKey, folderName: t.folderName, fileCount: 0, totalBytes: 0, present: false },
    ]),
  );
  for (const e of entries) {
    const segs = e.path.split(/[/\\]/);
    const top = unwrap ? segs[1] : segs[0];
    if (!top) continue; // file tepat di root pembungkus — tak masuk folder mana pun
    const st = stat.get(top);
    if (st) {
      st.fileCount += 1;
      st.totalBytes += e.bytes;
      st.present = true;
    }
  }
  const folders = FOLDER_TEMPLATE.map((t) => stat.get(t.folderName)!);
  return {
    folders,
    missingFolders: folders.filter((f) => !f.present).map((f) => f.folderKey),
  };
}

/**
 * Direktori RootPath bundle untuk engine: hasil ekstraksi; bila ZIP berisi
 * SATU folder pembungkus (mis. "9.NEW QUERY/") dan tak ada file di root,
 * turun satu level — struktur "14 folder langsung" maupun "satu folder
 * induk" dua-duanya diterima (FR-1).
 */
export async function resolveBundlePath(bundleId: string): Promise<string> {
  const dir = bundleDir(bundleId);
  const stat = await fs.stat(dir).catch(() => null);
  if (!stat?.isDirectory()) {
    throw new Error(`Bundle ${bundleId} tidak ditemukan — unggah ulang ZIP-nya.`);
  }
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const filesAtRoot = entries.some((e) => e.isFile());
  if (!filesAtRoot && entries.length === 1 && entries[0].isDirectory()) {
    return path.join(dir, entries[0].name);
  }
  return dir;
}
