import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { createBundleWriter, BundleDiskFullError } from "@/lib/ingest-bundle";
import { computeFolderStats } from "@/lib/bundles";
import {
  canonicalDriveUrl, collectDriveFiles, dedupeDriveFiles, DriveAccessError, DriveFileBadError,
  downloadDriveFile, listDriveFolder, mapDriveFolderKey, parseDriveFolderId,
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
const MAX_FILES = 300;
const DOWNLOAD_CONCURRENCY = 4;
/** Pindai subfolder per folder target (struktur "14 folder dalam satu
 *  folder induk" harus muat — 16 memberi ruang; pelindung utama tetap
 *  MAX_FILES / MAX_TOTAL_BYTES / timeout listing). */
const MAX_SUBFOLDERS = 16;
/** Maksimal LINK tersimpan per tarikan (audit 48-g-api: batasi amplifikasi
 *  listing). Naik 8 → 16 (2026-10-21): struktur kanonik user = 14 folder —
 *  mereka harus bisa mencentang SEMUanya sekaligus seperti aplikasi desktop
 *  Python; pelindung nyata tetap jumlah file, total byte, dan dinding waktu. */
const MAX_TARGETS = 16;
/** Listing paralel lintas-target: 16 folder × ~1-2 dtk listing BERUNTUN
 *  ≈ 20-30 dtk sendiri sudah menabrak maxDuration serverless — pool kecil
 *  memotongnya jadi ±8 dtk tanpa membombardir Drive. */
const LISTING_CONCURRENCY = 3;

const EXCEL_RE = /\.(xlsx|xls|xlsb|xlsm)$/i;

/** True bila error = pelanggaran unique Prisma (P2002). */
function isP2002(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002";
}

// ---- Auto-bootstrap tabel DriveFolderLink ----
// Tabel ini ditambahkan Task 48 — Supabase produksi di-push terakhir kali sebelum
// itu, dan password DB tidak disimpan di sandbox (aman) sehingga DDL baru belum
// bisa dikirim dari sini. Bootstrapping idempoten ini membuat fitur Drive hidup
// di produksi SEGERA; statement identik output `prisma migrate diff` dan aman
// dipanggil ulang (IF NOT EXISTS). Ganti dengan `bun run db:push:supabase`
// (README §3 Langkah 3) kapan pun — hasilnya sama.
const DRIVE_DDL_SQLITE = [
  `CREATE TABLE IF NOT EXISTS "DriveFolderLink" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "url" TEXT NOT NULL,
    "folderId" TEXT NOT NULL,
    "folderName" TEXT NOT NULL,
    "folderKey" TEXT,
    "fileCount" INTEGER NOT NULL DEFAULT 0,
    "totalBytes" INTEGER NOT NULL DEFAULT 0,
    "lastCheckedAt" DATETIME,
    "lastUsedAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "DriveFolderLink_url_key" ON "DriveFolderLink"("url")`,
  `CREATE INDEX IF NOT EXISTS "DriveFolderLink_folderKey_idx" ON "DriveFolderLink"("folderKey")`,
];
const DRIVE_DDL_POSTGRES = [
  `CREATE TABLE IF NOT EXISTS "DriveFolderLink" (
    "id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "folderId" TEXT NOT NULL,
    "folderName" TEXT NOT NULL,
    "folderKey" TEXT,
    "fileCount" INTEGER NOT NULL DEFAULT 0,
    "totalBytes" INTEGER NOT NULL DEFAULT 0,
    "lastCheckedAt" TIMESTAMP(3),
    "lastUsedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "DriveFolderLink_pkey" PRIMARY KEY ("id")
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "DriveFolderLink_url_key" ON "DriveFolderLink"("url")`,
  `CREATE INDEX IF NOT EXISTS "DriveFolderLink_folderKey_idx" ON "DriveFolderLink"("folderKey")`,
];

let driveTableReady = false;
async function ensureDriveLinkTable(): Promise<void> {
  if (driveTableReady) return;
  try {
    await db.driveFolderLink.findFirst({ select: { id: true } });
    driveTableReady = true;
    return;
  } catch (err) {
    const isMissing =
      (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2021") ||
      /no such table|DriveFolderLink.*(does not|tidak) exist/i.test(err instanceof Error ? err.message : "");
    if (!isMissing) throw err;
    const isSqlite = (process.env.DATABASE_URL ?? "").startsWith("file:");
    for (const stmt of isSqlite ? DRIVE_DDL_SQLITE : DRIVE_DDL_POSTGRES) {
      await db.$executeRawUnsafe(stmt);
    }
    driveTableReady = true;
  }
}

function toLinkDto(row: {
  id: string; url: string; folderId: string; folderName: string; folderKey: string | null;
  fileCount: number; totalBytes: number; lastCheckedAt: Date | null; lastUsedAt: Date | null; createdAt: Date;
}): DriveFolderLinkDto {
  return {
    id: row.id,
    url: row.url,
    folderId: row.folderId,
    folderName: row.folderName,
    folderKey: row.folderKey,
    fileCount: row.fileCount,
    totalBytes: row.totalBytes,
    lastCheckedAt: row.lastCheckedAt?.toISOString() ?? null,
    lastUsedAt: row.lastUsedAt?.toISOString() ?? null,
    createdAt: row.createdAt.toISOString(),
  };
}

/** GET — daftar link folder Drive tersimpan ("biar ingat"). */
export async function GET() {
  await ensureDriveLinkTable();
  const rows = await db.driveFolderLink.findMany({ orderBy: { createdAt: "asc" } });
  return NextResponse.json({ links: rows.map(toLinkDto) });
}

/**
 * POST — tiga aksi:
 *  - action "save"    : { url } → cek folder Drive (listing langsung), deteksi
 *    folderKey kanonik dari JUDUL folder, simpan/segarkan baris link.
 *  - action "preview" : { ids } / { url } → PRATINJAU CEPAT — listing Drive
 *    saja, file TIDAK diunduh, disk serverless TIDAK tersentuh → bebas kuota
 *    /tmp & jauh di bawah 60 dtk untuk folder sebesar apa pun. Struktur (kunci
 *    folder, jumlah, duplikat, subfolder gagal) dilaporkat jujur; total byte
 *    tidak dihitung; manifest tidak bisa diproses (bundleId kosong).
 *  - action "process" : { ids } atau { url } → tarik SEMUA file Excel dari
 *    folder terkait (unduh oleh server), materialisasi bundle lewat SATU
 *    jalur validasi createBundleWriter (FR-2), kembalikan manifest — alur
 *    lanjutannya identik dengan unggah ZIP.
 */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const action =
    body.action === "process" ? "process"
    : body.action === "preview" ? "preview"
    : body.action === "save" ? "save"
    : null;
  if (!action) {
    return NextResponse.json({ error: "action wajib 'save', 'preview', atau 'process'." }, { status: 400 });
  }

  try {
    if (action === "save") return await handleSave(body);
    if (action === "preview") return await handlePreview(body);
    return await handleProcess(body);
  } catch (err) {
    // Error tahap perencanaan (validasi input / listing) → status sudah semantik.
    if (err instanceof DrivePlanError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    // Error AKSES folder → status semantik (audit 48-g-api: jangan endus teks).
    if (err instanceof DriveAccessError) {
      const status = err.code === "NOT_FOUND" ? 404 : 422;
      return NextResponse.json({ error: err.message }, { status });
    }
    // Disk penuh di lingkungan serverless (mkdir/meta di luar try bagian dalam)
    // → 507 Insufficient Storage + pesan ramah, bukan "ENOSPC" mentah.
    if (err instanceof BundleDiskFullError) {
      return NextResponse.json({ error: err.message }, { status: 507 });
    }
    if (err instanceof Error && /ENOSPC|no space left/i.test(err.message)) {
      return NextResponse.json({ error: new BundleDiskFullError().message }, { status: 507 });
    }
    // Pesan milik modul kita (bahasa Indonesia, tanpa path internal) boleh
    // diteruskan; error Prisma / error sistem (EACCES, path server) → generik.
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const leaksSystem =
      err instanceof Error && /EACCES|ENOENT|EEXIST|\/tmp\/|\/home\/|PrismaClient|prisma:/i.test(err.message);
    const message =
      !isPrisma && err instanceof Error && !leaksSystem
        ? err.message
        : "Permintaan Drive gagal — coba lagi sebentar.";
    const status = /tidak ditemukan|tidak dikenali|tidak valid|kosong|harus|wajib|melebihi/i.test(message) ? 422 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}

async function handleSave(body: Record<string, unknown>): Promise<Response> {
  await ensureDriveLinkTable();
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
  let row;
  try {
    row = existing
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
  } catch (err) {
    // Race dua POST save untuk folder sama (audit 48-g-api): tumpang-tindih
    // create → P2002 — perlakukan sebagai upsert yang kalah → update saja.
    if (isP2002(err)) {
      row = await db.driveFolderLink.update({
        where: { url: canonical },
        data: {
          folderId,
          folderName: listing.folderName,
          folderKey,
          fileCount: excelCount,
          lastCheckedAt: now,
        },
      });
    } else {
      throw err;
    }
  }

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
    warnings.push(`Folder berisi ${subfolderCount} subfolder — subfolder ikut dipindai saat ditarik (maks ${MAX_SUBFOLDERS}).`);
  }

  return NextResponse.json({ link: toLinkDto(row), created: !existing, warnings });
}

type Target = { folderId: string; rowId: string | null };

/** Error tahap perencanaan (validasi input / listing Drive) — status HTTP sudah
 *  semantik (422/404); dipakai bersama aksi "process" & "preview". */
class DrivePlanError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "DrivePlanError";
  }
}

type DrivePlan = {
  targets: Target[];
  pullName: string;
  merged: { id: string; path: string; name: string; modifiedMs: number | null; tIdx: number }[];
  skippedDuplicates: { path: string; reason: string }[];
  suffixedDuplicates: string[];
  driveFolders: NonNullable<BundleManifest["driveFolders"]>;
  driveNotices: string[];
  skippedNonExcelTotal: number;
};

type MergedFile = DrivePlan["merged"][number];

/**
 * Tahap PERSIPLAN tarikan Drive (dipakai bersama "process" dan "preview"):
 * validasi ids/url, listing LIVE per-target (pool paralel kecil, urutan
 * deterministik via tIdx), dedupe nama-sama, merge lintas-target dengan
 * deteksi path ganda. TIDAK mengunduh file apa pun di tahap ini.
 */
async function planDrivePull(body: Record<string, unknown>): Promise<DrivePlan> {
  await ensureDriveLinkTable();
  const ids = Array.isArray(body.ids) ? body.ids.filter((x): x is string => typeof x === "string") : [];
  const url = typeof body.url === "string" ? body.url : "";
  const bundleName = clampString(body.bundleName, 120);

  const targets: Target[] = [];
  if (ids.length > 0) {
    if (ids.length > MAX_TARGETS) {
      throw new DrivePlanError(
        422,
        `Maksimal ${MAX_TARGETS} link per tarikan — centang lebih sedikit folder.`,
      );
    }
    const rows = await db.driveFolderLink.findMany({ where: { id: { in: ids } } });
    const missing = ids.filter((id) => !rows.some((r) => r.id === id));
    if (missing.length > 0) {
      throw new DrivePlanError(404, `Link tersimpan tidak ditemukan (id: ${missing.join(", ")}).`);
    }
    for (const r of rows) targets.push({ folderId: r.folderId, rowId: r.id });
  } else if (url) {
    targets.push({ folderId: parseDriveFolderId(url), rowId: null });
  } else {
    throw new DrivePlanError(422, "Sertakan ids (link tersimpan) atau url (sekali tarik).");
  }

  // --- Kumpulkan daftar file (listing LIVE saat ditarik, bukan cache) ---
  const merged: MergedFile[] = [];
  const skippedDuplicates: { path: string; reason: string }[] = [];
  const suffixedDuplicates: string[] = [];
  const driveFolders: NonNullable<BundleManifest["driveFolders"]> = [];
  const driveNotices: string[] = [];
  let skippedNonExcelTotal = 0;

  const seenPaths = new Set<string>();
  // Listing LIVE per-target — PARALEL pool kecil (urutan tetap dipertahankan:
  // hasil diindeks tIdx, merge di bawah tetap berurutan & deterministik).
  const collectedPerTarget: Awaited<ReturnType<typeof collectDriveFiles>>[] = [];
  let listingCursor = 0;
  const listingWorkers = Array.from(
    { length: Math.min(LISTING_CONCURRENCY, targets.length) },
    async () => {
      while (listingCursor < targets.length) {
        const tIdx = listingCursor;
        listingCursor += 1;
        collectedPerTarget[tIdx] = await collectDriveFiles(targets[tIdx]!.folderId, {
          maxFiles: MAX_FILES,
          maxFolders: MAX_SUBFOLDERS,
        });
      }
    },
  );
  await Promise.all(listingWorkers);

  for (let tIdx = 0; tIdx < targets.length; tIdx += 1) {
    const collected = collectedPerTarget[tIdx]!;
    const dedup = dedupeDriveFiles(collected.files);
    skippedNonExcelTotal += collected.skippedNonExcel;

    // Jujur tentang pemotongan batas & subfolder gagal-dibaca (audit 48-g-engine):
    if (collected.truncatedFiles) {
      driveNotices.push(
        `Folder “${collected.folderName}”: jumlah file melebihi batas ${MAX_FILES} — hanya ${collected.files.length} versi terbaru yang ditarik.`,
      );
    }
    if (collected.truncatedFolders) {
      driveNotices.push(
        `Folder “${collected.folderName}” punya subfolder lebih dari ${MAX_SUBFOLDERS} — hanya ${MAX_SUBFOLDERS} pertama yang dipindai.`,
      );
    }
    for (const sub of collected.failedSubfolders) {
      driveNotices.push(`Subfolder “${sub}” di “${collected.folderName}” gagal dibaca — dilewati.`);
    }

    for (const f of dedup.kept) {
      if (seenPaths.has(f.path)) {
        throw new DrivePlanError(
          422,
          `Dua link ter-petakan ke path yang sama (“${f.path}”) — hapus salah satu link tersimpan yang menunjuk folder identik.`,
        );
      }
      seenPaths.add(f.path);
      merged.push({ id: f.id, path: f.path, name: f.name, modifiedMs: f.modifiedMs, tIdx });
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
    throw new DrivePlanError(422, "Tidak ada file Excel yang bisa ditarik dari link itu.");
  }

  return {
    targets,
    pullName:
      bundleName || (targets.length === 1 ? driveFolders[0]!.folderName : `Drive ${targets.length} folder`),
    merged,
    skippedDuplicates,
    suffixedDuplicates,
    driveFolders,
    driveNotices,
    skippedNonExcelTotal,
  };
}

/**
 * POST action "preview" — PRATINJAU CEPAT: listing Drive saja, file TIDAK
 * diunduh dan disk serverless TIDAK tersentuh → bebas kuota /tmp dan jauh
 * di bawah batas 60 dtk untuk folder sebesar apa pun (solusi untuk data
 * yang tumbuh tiap minggu di Vercel serverless). Struktur (14 kunci folder,
 * jumlah file, duplikat, subfolder gagal) dilaporkat jujur; total byte tidak
 * diketahui dari listing → tidak dihitung; bundleId kosong → manifest ini
 * TIDAK bisa diproses (validasi isi/magic bytes tetap milik tarikan penuh).
 */
async function handlePreview(body: Record<string, unknown>): Promise<Response> {
  const plan = await planDrivePull(body);
  const { folders, missingFolders } = computeFolderStats(
    plan.merged.map((f) => ({ path: f.path, bytes: 0 })),
  );
  if (plan.merged.length > MAX_FILES) {
    plan.driveNotices.push(
      `Total ${plan.merged.length} file melebihi batas ${MAX_FILES} per bundle — pisahkan per folder saat menarik penuh.`,
    );
  }
  plan.driveNotices.push(
    "Pratinjau cepat: file tidak diunduh — jumlah & struktur dari listing Drive; total byte tidak dihitung.",
  );

  // Segarkan lastCheckedAt + jumlah file live (bukan "terakhir ditarik" —
  // preview jujur tidak mengubah lastUsedAt/totalBytes). Kegagalan segarkan
  // (koneksi pooler sesaat penuh) TIDAK fatal — pratinjau tetap valid,
  // dilaporkan jujur sebagai notice.
  try {
    const now = new Date();
    await Promise.all(
      plan.targets.map((t, i) =>
        t.rowId
          ? db.driveFolderLink.update({
              where: { id: t.rowId },
              data: {
                lastCheckedAt: now,
                fileCount: plan.driveFolders[i]?.fileCount ?? undefined,
              },
            })
          : Promise.resolve(null),
      ),
    );

    await db.auditLog.create({
      data: {
        action: "DRIVE_PREVIEW",
        entity: "DriveFolderLink",
        entityId: plan.targets[0]?.rowId ?? clampString(plan.targets.map((t) => t.folderId).join(","), 200),
        detailJson: JSON.stringify({
          folderNames: plan.driveFolders.map((f) => f.folderName),
          fileCount: plan.merged.length,
          notices: plan.driveNotices.length,
        }),
        actor: "analyst",
      },
    });
  } catch {
    plan.driveNotices.push(
      "Waktu cek link tidak bisa disegarkan (koneksi DB sesaat penuh) — pratinjau tetap valid.",
    );
  }

  const manifest: BundleManifest = {
    bundleId: "",
    name: plan.pullName,
    uploadedAt: new Date().toISOString(),
    fileCount: plan.merged.length,
    totalBytes: 0,
    skippedEntries: plan.skippedNonExcelTotal,
    folders,
    missingFolders,
    source: "drive",
    previewOnly: true,
    skippedDuplicates: plan.skippedDuplicates,
    suffixedDuplicates: plan.suffixedDuplicates,
    driveFolders: plan.driveFolders,
    driveNotices: plan.driveNotices,
  };
  return NextResponse.json(manifest);
}

async function handleProcess(body: Record<string, unknown>): Promise<Response> {
  const plan = await planDrivePull(body);
  if (plan.merged.length > MAX_FILES) {
    throw new DrivePlanError(
      422,
      `Total ${plan.merged.length} file melebihi batas ${MAX_FILES} per bundle — pisahkan per folder.`,
    );
  }

  // --- Unduh (pool paralel kecil; file RUSAK dilewati dengan laporan,
  //     error jaringan/Drive → fail-fast dengan nama file). ---
  const bundleId = randomUUID();
  const writer = await createBundleWriter(bundleId);
  let totalBytes = 0;
  const skippedFiles: { path: string; reason: string }[] = [];
  /** Byte ter-unduh per target (indeks = urutan targets) — untuk totalBytes link. */
  const perTargetBytes: number[] = plan.targets.map(() => 0);
  const { pullName, driveFolders } = plan;

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
      perTargetBytes[file.tIdx] += buf.byteLength;
      if (totalBytes > MAX_TOTAL_BYTES) {
        throw new Error(
          `Total unduhan melebihi ${(MAX_TOTAL_BYTES / 1024 / 1024).toFixed(0)} MB — pisahkan folder Drive atau unggah sebagai ZIP.`,
        );
      }
      await writer.write(file.path, buf);
    };
    const workers = Array.from({ length: Math.min(DOWNLOAD_CONCURRENCY, plan.merged.length) }, async () => {
      while (cursor < plan.merged.length) {
        const file = plan.merged[cursor]!;
        cursor += 1;
        await pullOne(file);
      }
    });
    await Promise.all(workers);

    if (skippedFiles.length === plan.merged.length) {
      throw new Error(
        `Semua ${plan.merged.length} file di folder Drive gagal ditarik (rusak/bukan Excel) — tidak ada bundle yang dibuat.`,
      );
    }

    const manifest = await writer.finish({
      name: pullName,
      source: "drive",
      skippedEntriesExtra: plan.skippedNonExcelTotal,
      extras: {
        ...(plan.skippedDuplicates.length ? { skippedDuplicates: plan.skippedDuplicates } : {}),
        ...(plan.suffixedDuplicates.length ? { suffixedDuplicates: plan.suffixedDuplicates } : {}),
        ...(skippedFiles.length ? { skippedFiles } : {}),
        ...(plan.driveNotices.length ? { driveNotices: plan.driveNotices } : {}),
        driveFolders,
      },
    });

    // Segarkan baris link yang dipakai (urutan driveFolders = urutan targets).
    // totalBytes/folderKey disegarkan juga — folderKey eksplisit null agar
    // rename non-kanonik tidak tertinggal STALE (audit 48-g-data).
    // Kegagalan penyegaran/audit (mis. kuota koneksi pooler Supabase sesaat
    // penuh — EMAXCONNSESSION terverifikasi live) TIDAK boleh membuang bundle
    // yang baru selesai diunduh 47 detik ini: catat jujur sebagai notice,
    // manifest tetap dikembalikan (writer.abort di catch luar tak sempat
    // menyentuhnya karena kita return di dalam try ini).
    try {
      const now = new Date();
      await Promise.all(
        plan.targets.map((t, i) =>
          t.rowId
            ? db.driveFolderLink.update({
                where: { id: t.rowId },
                data: {
                  lastUsedAt: now,
                  folderName: driveFolders[i]?.folderName ?? undefined,
                  folderKey: driveFolders[i]?.folderKey ?? null,
                  fileCount: driveFolders[i]?.fileCount ?? undefined,
                  totalBytes: perTargetBytes[i] ?? undefined,
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
            skippedDuplicates: plan.skippedDuplicates.length,
            suffixedDuplicates: plan.suffixedDuplicates.length,
            skippedFiles: skippedFiles.length,
            notices: plan.driveNotices.length,
          }),
          actor: "analyst",
        },
      });
    } catch {
      manifest.driveNotices = [
        ...(manifest.driveNotices ?? []),
        "“Terakhir ditarik”/audit link gagal disegarkan (koneksi DB sesaat penuh) — bundle & manifest tetap valid.",
      ];
    }

    return NextResponse.json(manifest);
  } catch (err) {
    await writer.abort();
    if (err instanceof BundleDiskFullError) {
      return NextResponse.json({ error: err.message }, { status: 507 });
    }
    const message = err instanceof Error ? err.message : "Gagal menarik bundle dari Drive.";
    // ENOSPC dari mkdir/finish (bukan writeFile) → pesan ramah, bukan teks sistem.
    if (/ENOSPC|no space left/i.test(message)) {
      return NextResponse.json({ error: new BundleDiskFullError().message }, { status: 507 });
    }
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

/** DELETE ?id= — hapus link tersimpan (file di Drive tidak tersentuh). */
export async function DELETE(req: NextRequest) {
  await ensureDriveLinkTable();
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
