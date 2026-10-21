import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { unzipSync } from "fflate";
import { BundleEmptyError, createBundleWriter } from "@/lib/ingest-bundle";
import { BUNDLES_DIR, FOLDER_TEMPLATE } from "@/lib/bundles";
import path from "path";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const MAX_ZIP_BYTES = 400 * 1024 * 1024; // R-10: batas jelas di FR-1

/**
 * POST /api/ingest/upload (FR-1) — unggah ZIP bundle export mentah Accurate.
 * Ekstraksi + validasi + manifest kini lewat createBundleWriter (SATU jalur
 * bersama dengan sumber Google Drive): entri .xls* saja (lainnya dilewati
 * & dihitung), path aman (tanpa ../ dan __MACOSX), lalu manifest per-folder
 * memakai pemetaan config.json desktop (FR-2 — 14 kunci folder kanonik).
 * Folder yang tak ditemukan dilaporkan jujur (missingFolders) — pipeline
 * tetap dapat dijalankan dan preflight engine akan memberi peringatan sama.
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

  let entries: Record<string, Uint8Array>;
  try {
    entries = unzipSync(new Uint8Array(await file.arrayBuffer()));
  } catch {
    return NextResponse.json({ error: "ZIP tidak dapat dibaca (rusak atau bukan zip)." }, { status: 422 });
  }

  const writer = await createBundleWriter(randomUUID());
  try {
    for (const [name, data] of Object.entries(entries)) {
      await writer.write(name, data);
    }
    const manifest = await writer.finish({ name: file.name.replace(/\.zip$/i, "") });
    return NextResponse.json(manifest);
  } catch (err) {
    await writer.abort();
    if (err instanceof BundleEmptyError) {
      return NextResponse.json({ error: err.message }, { status: 422 });
    }
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
