import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { db } from "@/lib/db";
import { createBundleWriter } from "@/lib/ingest-bundle";
import {
  canonicalDriveUrl, collectDriveFiles, dedupeDriveFiles, DriveFileBadError, downloadDriveFile,
  listDriveFolder, mapDriveFolderKey, parseDriveFolderId,
} from "@/lib/drive";
import { clampString } from "@/lib/validate";
import type { BundleManifest, DriveFolderLinkDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Serverless: menarik file dari Drive bisa lama (unduhan jaringan) — 60 dtk
// adalah batas aman rencana manapun; lokal/self-host tidak memakai nilai ini.
export const maxDuration = 60;

const MAX_TOTAL_BYTES = 400 * 1024 * 1024; // samakan dengan batas ZIP (R-10)
const MAX_FILE_BYTES = 60 * 1024 * 1024;
const MAX_FILES = 200;
const DOWNLOAD_CONCURRENCY = 4;

const EXCEL_RE = /\.(xlsx|xls|xlsb)$/i;

function toLinkDto(row: {
  id: string; url: string; folderId: string; folderName: string; folderKey: string | null;
  fileCount: number; lastCheckedAt: Date | null; lastUsedAt: Date | null; createdAt: Date;
}): DriveFolderLinkDto {
  return {
    id: row.id,
    url: row.url,
    folderId: row.folderId,
    folderName: row.folderName,
    folderKey: row.folderKey,
    fileCount: row.fileCount,
    lastCheckedAt: row.lastCheckedAt?.toISOString() ?? null,
    lastUsedAt: row.lastUsedAt?.toISOString() ?? null,
    createdAt: row.createdAt.toISOString(),
  };
}

/** GET — daftar link folder Drive tersimpan ("biar ingat"). */
export async function GET() {
  const rows = await db.driveFolderLink.findMany({ orderBy: { createdAt: "asc" } });
  return NextResponse.json({ links: rows.map(toLinkDto) });
}

/**
 * POST — dua aksi:
 *  - action "save"   : { url } → cek folder Drive (listing langsung), deteksi
 *    folderKey kanonik dari JUDUL folder, simpan/segarkan baris link.
 *  - action "process" : { ids: string[] } atau { url } → tarik SEMUA file
 *    Excel dari folder terkait (unduh oleh server), materialisasi bundle
 *    lewat SATU jalur validasi createBundleWriter (FR-2), kembalikan
 *    manifest — alur lanjutannya identik dengan unggah ZIP.
 */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const action = body.action === "process" ? "process" : body.action === "save" ? "save" : null;
  if (!action) return NextResponse.json({ error: "action wajib 'save' atau 'process'." }, { status: 400 });

  try {
    if (action === "save") return await handleSave(body);
    return await handleProcess(body);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Permintaan Drive gagal.";
    const status = /tidak ditemukan|tidak dikenali|tidak valid|kosong|harus|wajib/i.test(message) ? 422 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}

async function handleSave(body: Record<string, unknown>): Promise<Response> {
  const url = typeof body.url === "string" ? body.url : "";
  if (!url) return NextResponse.json({ error: "url wajib ada (link folder Drive)." }, { status: 422 });

  const folderId = parseDriveFolderId(url);
  const listing = await listDriveFolder(folderId);
  const excelCount = listing.entries.filter((e) => !e.isFolder && EXCEL_RE.test(e.name)).length;
  const subfolderCount = listing.entries.filter((e) => e.isFolder).length;
  const folderKey = mapDriveFolderKey(listing.folderName);
  const canonical = canonicalDriveUrl(folderId);
  const now = new Date();

  const existing = await db.driveFolderLink.findUnique({ where: { url: canonical } });
  const row = existing
    ? await db.driveFolderLink.update({
        where: { url: canonical },
        data: {
          folderId,
          folderName: listing.folderName,
          folderKey,
          fileCount: excelCount,
          lastCheckedAt: now,
        },
      })
    : await db.driveFolderLink.create({
        data: {
          url: canonical,
          folderId,
          folderName: listing.folderName,
          folderKey,
          fileCount: excelCount,
          lastCheckedAt: now,
        },
      });

  await db.auditLog.create({
    data: {
      action: existing ? "DRIVE_LINK_REFRESH" : "DRIVE_LINK_SAVE",
      entity: "DriveFolderLink",
      entityId: row.id,
      detailJson: JSON.stringify({ folderName: listing.folderName, folderKey, excelCount }),
      actor: "analyst",
    },
  });

  const warnings: string[] = [];
  if (!folderKey) {
    warnings.push(
      `Judul folder “${listing.folderName}” tidak cocok 14 nama folder config.json — file tetap bisa ditarik, tapi tidak akan terbaca sebagai folder kanonik (FR-2).`,
    );
  }
  if (excelCount === 0) {
    warnings.push("Folder tidak berisi file Excel (.xlsx/.xls/.xlsb) saat ini diperiksa.");
  }
  if (subfolderCount > 0) {
    warnings.push(`Folder berisi ${subfolderCount} subfolder — subfolder ikut dipindai saat ditarik (maks 12).`);
  }

  return NextResponse.json({ link: toLinkDto(row), created: !existing, warnings });
}

type Target = { folderId: string; rowId: string | null };

async function handleProcess(body: Record<string, unknown>): Promise<Response> {
  const ids = Array.isArray(body.ids) ? body.ids.filter((x): x is string => typeof x === "string") : [];
  const url = typeof body.url === "string" ? body.url : "";
  const bundleName = clampString(body.bundleName, 120);

  const targets: Target[] = [];
  if (ids.length > 0) {
    const rows = await db.driveFolderLink.findMany({ where: { id: { in: ids } } });
    const missing = ids.filter((id) => !rows.some((r) => r.id === id));
    if (missing.length > 0) {
      return NextResponse.json(
        { error: `Link tersimpan tidak ditemukan (id: ${missing.join(", ")}).` },
        { status: 404 },
      );
    }
    for (const r of rows) targets.push({ folderId: r.folderId, rowId: r.id });
  } else if (url) {
    targets.push({ folderId: parseDriveFolderId(url), rowId: null });
  } else {
    return NextResponse.json(
      { error: "Sertakan ids (link tersimpan) atau url (sekali tarik)." },
      { status: 422 },
    );
  }

  // --- Kumpulkan daftar file (listing LIVE saat ditarik, bukan cache) ---
  type MergedFile = { id: string; path: string; name: string; modifiedMs: number | null };
  const merged: MergedFile[] = [];
  const skippedDuplicates: { path: string; reason: string }[] = [];
  const suffixedDuplicates: string[] = [];
  const driveFolders: NonNullable<BundleManifest["driveFolders"]> = [];
  let skippedNonExcelTotal = 0;

  const seenPaths = new Set<string>();
  for (const t of targets) {
    const collected = await collectDriveFiles(t.folderId, { maxFiles: MAX_FILES, maxFolders: 12 });
    const dedup = dedupeDriveFiles(collected.files);
    skippedNonExcelTotal += collected.skippedNonExcel;

    for (const f of dedup.kept) {
      if (seenPaths.has(f.path)) {
        return NextResponse.json(
          {
            error: `Dua link ter-petakan ke path yang sama (“${f.path}”) — hapus salah satu link tersimpan yang menunjuk folder identik.`,
          },
          { status: 422 },
        );
      }
      seenPaths.add(f.path);
      merged.push({ id: f.id, path: f.path, name: f.name, modifiedMs: f.modifiedMs });
    }
    skippedDuplicates.push(...dedup.skipped);
    suffixedDuplicates.push(...dedup.suffixed);
    driveFolders.push({
      folderName: collected.folderName,
      folderKey: collected.folderKey,
      fileCount: dedup.kept.length,
    });
  }

  if (merged.length === 0) {
    return NextResponse.json({ error: "Tidak ada file Excel yang bisa ditarik dari link itu." }, { status: 422 });
  }
  if (merged.length > MAX_FILES) {
    return NextResponse.json(
      { error: `Total ${merged.length} file melebihi batas ${MAX_FILES} per bundle — pisahkan per folder.` },
      { status: 422 },
    );
  }

  // --- Unduh (pool paralel kecil; file RUSAK dilewati dengan laporan,
  //     error jaringan/Drive → fail-fast dengan nama file). ---
  const bundleId = randomUUID();
  const writer = await createBundleWriter(bundleId);
  let totalBytes = 0;
  const skippedFiles: { path: string; reason: string }[] = [];

  const pullName =
    bundleName || (targets.length === 1 ? driveFolders[0]!.folderName : `Drive ${targets.length} folder`);

  try {
    let cursor = 0;
    const pullOne = async (file: MergedFile) => {
      let buf: Uint8Array;
      try {
        buf = await downloadDriveFile(file.id, { maxBytes: MAX_FILE_BYTES });
      } catch (err) {
        if (err instanceof DriveFileBadError) {
          skippedFiles.push({ path: file.path, reason: err.message });
          return;
        }
        throw err instanceof Error ? new Error(`${file.path}: ${err.message}`) : err;
      }
      totalBytes += buf.byteLength;
      if (totalBytes > MAX_TOTAL_BYTES) {
        throw new Error(
          `Total unduhan melebihi ${(MAX_TOTAL_BYTES / 1024 / 1024).toFixed(0)} MB — pisahkan folder Drive atau unggah sebagai ZIP.`,
        );
      }
      await writer.write(file.path, buf);
    };
    const workers = Array.from({ length: Math.min(DOWNLOAD_CONCURRENCY, merged.length) }, async () => {
      while (cursor < merged.length) {
        const file = merged[cursor]!;
        cursor += 1;
        await pullOne(file);
      }
    });
    await Promise.all(workers);

    if (skippedFiles.length === merged.length) {
      throw new Error(
        `Semua ${merged.length} file di folder Drive gagal ditarik (rusak/bukan Excel) — tidak ada bundle yang dibuat.`,
      );
    }

    const manifest = await writer.finish({
      name: pullName,
      source: "drive",
      skippedEntriesExtra: skippedNonExcelTotal,
      extras: {
        ...(skippedDuplicates.length ? { skippedDuplicates } : {}),
        ...(suffixedDuplicates.length ? { suffixedDuplicates } : {}),
        ...(skippedFiles.length ? { skippedFiles } : {}),
        driveFolders,
      },
    });

    // Segarkan baris link yang dipakai (urutan driveFolders = urutan targets).
    const now = new Date();
    await Promise.all(
      targets.map((t, i) =>
        t.rowId
          ? db.driveFolderLink.update({
              where: { id: t.rowId },
              data: {
                lastUsedAt: now,
                folderName: driveFolders[i]?.folderName ?? undefined,
                folderKey: driveFolders[i]?.folderKey ?? undefined,
                fileCount: driveFolders[i]?.fileCount ?? undefined,
              },
            })
          : Promise.resolve(null),
      ),
    );

    await db.auditLog.create({
      data: {
        action: "DRIVE_PULL_BUNDLE",
        entity: "BundleManifest",
        entityId: bundleId,
        detailJson: JSON.stringify({
          bundleId,
          folderNames: driveFolders.map((f) => f.folderName),
          fileCount: manifest.fileCount,
          totalBytes: manifest.totalBytes,
          skippedDuplicates: skippedDuplicates.length,
          suffixedDuplicates: suffixedDuplicates.length,
          skippedFiles: skippedFiles.length,
        }),
        actor: "analyst",
      },
    });

    return NextResponse.json(manifest);
  } catch (err) {
    await writer.abort();
    const message = err instanceof Error ? err.message : "Gagal menarik bundle dari Drive.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

/** DELETE ?id= — hapus link tersimpan (file di Drive tidak tersentuh). */
export async function DELETE(req: NextRequest) {
  const id = req.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "Query id wajib ada." }, { status: 400 });

  const row = await db.driveFolderLink.findUnique({ where: { id } });
  if (!row) return NextResponse.json({ error: "Link tersimpan tidak ditemukan." }, { status: 404 });

  await db.driveFolderLink.delete({ where: { id } });
  await db.auditLog.create({
    data: {
      action: "DRIVE_LINK_DELETE",
      entity: "DriveFolderLink",
      entityId: id,
      detailJson: JSON.stringify({ folderName: row.folderName, url: row.url }),
      actor: "analyst",
    },
  });
  return NextResponse.json({ ok: true, id });
}
