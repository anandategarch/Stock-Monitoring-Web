import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { promises as fs } from "fs";
import path from "path";
import { unzipSync } from "fflate";
import { BUNDLES_DIR, FOLDER_TEMPLATE, bundleDir, saveBundleMeta } from "@/lib/bundles";
import type { BundleFolderStat, BundleManifest } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const MAX_ZIP_BYTES = 400 * 1024 * 1024; // R-10: batas jelas di FR-1
const EXCEL_RE = /\.(xlsx|xls|xlsb)$/i;

/**
 * POST /api/ingest/upload (FR-1) — unggah ZIP bundle export mentah Accurate.
 * Validasi struktur: entri .xls* saja (lainnya dilewati & dihitung), path
 * aman (tanpa ../ dan __MACOSX), lalu manifest per-folder memakai pemetaan
 * config.json desktop (FR-2 — 14 kunci folder kanonik). Folder yang tak
 * ditemukan dilaporkan jujur (missingFolders) — pipeline tetap dapat
 * dijalankan dan preflight engine akan memberi peringatan yang sama.
 */
export async function POST(req: NextRequest) {
  let file: File;
  try {
    const form = await req.formData();
    const f = form.get("file");
    if (!(f instanceof File)) {
      return NextResponse.json({ error: "Field 'file' (ZIP bundle) wajib ada." }, { status: 400 });
    }
    file = f;
  } catch {
    return NextResponse.json({ error: "Body harus multipart/form-data." }, { status: 400 });
  }

  if (!file.name.toLowerCase().endsWith(".zip")) {
    return NextResponse.json({ error: "File harus berekstensi .zip." }, { status: 422 });
  }
  if (file.size > MAX_ZIP_BYTES) {
    return NextResponse.json(
      { error: `ZIP terlalu besar (${(file.size / 1024 / 1024).toFixed(0)} MB) — batas 400 MB.` },
      { status: 422 },
    );
  }

  const bundleId = randomUUID();
  const dir = bundleDir(bundleId);
  try {
    const buf = new Uint8Array(await file.arrayBuffer());
    let entries: Record<string, Uint8Array>;
    try {
      entries = unzipSync(buf);
    } catch {
      return NextResponse.json({ error: "ZIP tidak dapat dibaca (rusak atau bukan zip)." }, { status: 422 });
    }

    let fileCount = 0;
    let totalBytes = 0;
    let skippedEntries = 0;
    const folderStat = new Map<string, BundleFolderStat>(
      FOLDER_TEMPLATE.map((t) => [
        t.folderName,
        { folderKey: t.folderKey, folderName: t.folderName, fileCount: 0, totalBytes: 0, present: false },
      ]),
    );

    await fs.mkdir(dir, { recursive: true });

    for (const [name, data] of Object.entries(entries)) {
      if (name.endsWith("/")) continue; // entri direktori
      if (name.startsWith("__MACOSX/") || name.includes("/__MACOSX/") || path.basename(name).startsWith("._")) {
        skippedEntries += 1;
        continue;
      }
      // sanitasi path: larang traversal / absolut
      const norm = path.normalize(name).replace(/^(\.\.(\/|\\|$))+/, "");
      if (!norm || path.isAbsolute(norm) || norm.startsWith("..") || norm.includes("\0")) {
        skippedEntries += 1;
        continue;
      }
      if (!EXCEL_RE.test(norm)) {
        skippedEntries += 1; // non-Excel dilewati (bundle = folder export .xls*)
        continue;
      }
      const dest = path.join(dir, norm);
      if (!dest.startsWith(dir + path.sep)) {
        skippedEntries += 1;
        continue;
      }
      await fs.mkdir(path.dirname(dest), { recursive: true });
      await fs.writeFile(dest, data);
      fileCount += 1;
      totalBytes += data.byteLength;

      const top = norm.split(/[/\\]/)[0];
      const st = folderStat.get(top);
      if (st) {
        st.fileCount += 1;
        st.totalBytes += data.byteLength;
        st.present = true;
      }
    }

    if (fileCount === 0) {
      await fs.rm(dir, { recursive: true, force: true }).catch(() => undefined);
      return NextResponse.json(
        {
          error:
            "Tidak ada file Excel (.xlsx/.xls/.xlsb) di dalam ZIP — pastikan ini bundle export Accurate (struktur 14 folder config.json).",
        },
        { status: 422 },
      );
    }

    const folders = FOLDER_TEMPLATE.map((t) => folderStat.get(t.folderName)!);
    const missingFolders = folders.filter((f) => !f.present).map((f) => f.folderKey);
    const manifest: BundleManifest = {
      bundleId,
      name: file.name.replace(/\.zip$/i, ""),
      uploadedAt: new Date().toISOString(),
      fileCount,
      totalBytes,
      skippedEntries,
      folders,
      missingFolders,
    };
    await saveBundleMeta(manifest);

    return NextResponse.json(manifest);
  } catch (err) {
    await fs.rm(dir, { recursive: true, force: true }).catch(() => undefined);
    const message = err instanceof Error ? err.message : "Gagal mengekstrak bundle.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET() {
  // observabilitas ringan: folder template yang diharapkan (FR-2)
  return NextResponse.json({
    bundlesDir: path.relative(process.cwd(), BUNDLES_DIR),
    folders: FOLDER_TEMPLATE,
  });
}
