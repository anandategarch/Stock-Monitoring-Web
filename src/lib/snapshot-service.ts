// ============================================================
// Snapshot service — jantung alur Ingest → Pratinjau → Komit (FR-3/FR-4/FR-12/FR-24).
// Strategi komit: engine IDEMPOTENT → komit memanggil ulang /process dengan
// parameter run yang sama, hasil identik, lalu menulis snapshot permanen.
// Snapshot immutable: periode lama → SUPERSEDED (tetap tersimpan).
// Task 55: jalur bundle server-side (unggah ZIP/Drive → engine :3031 di server)
// DIHAPUS — data asli kini HANYA lewat agent laptop (disk lokal) atau engine
// demo sintetis. Komit run agent memakai AgentResult tersimpan (tanpa engine).
// ============================================================
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { engineProcess } from "@/lib/engine";
import { readAgentResult, saveAgentResult } from "@/lib/agent-store";
import { stableFingerprint } from "@/lib/fingerprint";
import { prevPeriodKey } from "@/lib/format";
import type {
  AuditNote, CekLabel, DqSeverity, EngineProcessRequest, EngineResult, EngineSummary,
} from "@/lib/types";

export function parseJsonSafe<T>(raw: string | null | undefined, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/** True bila error = pelanggaran unique Prisma (P2002). */
function isP2002(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002";
}

export interface RunParams {
  periodKey: string;
  tanggalH: number;
  ambangAcrPct: number;
  bundleName: string | null;
  seed?: number;
}

const ACTOR = "analyst";

async function audit(action: string, entity: string, entityId: string | null, detail: unknown) {
  await db.auditLog.create({
    data: {
      action,
      entity,
      entityId: entityId ?? undefined,
      detailJson: JSON.stringify(detail),
      actor: ACTOR,
    },
  });
}

/** Langkah 1: jalankan engine, simpan RunBatch + DQ + manifest + log (BELUM komit).
 * Tanpa `providedResult` → engine demo sintetis :3030 (data latih alur; di
 * serverless memakai fallback EMBEDDED).
 * Opsi `providedResult` (Task 51 — agent lokal): hasil EngineResult diproses di
 * PYTHON LAPTOP user (salin folder disk lokal + engine FastAPI lokal) lalu diunggah agent —
 * server TIDAK memanggil engine; hasil utuh disimpan di AgentResult (gzip+b64)
 * supaya KOMIT serverless tetap mungkin tanpa engine. FR-12 tetap jujur: engine
 * deterministik, jadi hasil tersimpan = output kanonik run itu. */
export async function processRun(
  params: RunParams,
  opts: { providedResult?: EngineResult; agentName?: string | null } = {},
): Promise<{ runBatchId: string; result: EngineResult }> {
  let result: EngineResult;
  let paramsForLog: Record<string, unknown>;
  if (opts.providedResult) {
    result = opts.providedResult;
    paramsForLog = {
      periodKey: params.periodKey,
      tanggalH: params.tanggalH,
      ambangAcrPct: params.ambangAcrPct,
      bundleName: params.bundleName ?? null,
      seed: params.seed ?? 0,
      bundleId: null,
      engineSource: "agent",
      agentName: opts.agentName ?? null,
    };
  } else {
    const req: EngineProcessRequest = {
      periodKey: params.periodKey,
      tanggalH: params.tanggalH,
      ambangAcrPct: params.ambangAcrPct,
      bundleName: params.bundleName ?? undefined,
      seed: params.seed ?? 0,
    };
    result = await engineProcess(req);
    paramsForLog = { ...req, engineSource: "demo" };
  }

  const runBatch = await db.runBatch.create({
    data: {
      periodKey: params.periodKey,
      bundleName: params.bundleName,
      status: result.status,
      definitionVersion: result.definitionVersion,
      paramsJson: JSON.stringify(paramsForLog),
      summaryJson: JSON.stringify(result.summary),
      sourceInfoJson: JSON.stringify(result.sourceFiles),
      logJson: JSON.stringify(result.logs),
      engineKind: result.engineKind,
      engineVersion: result.engineVersion,
      contractVersion: result.contractVersion,
      durationMs: result.durationMs,
      actor: ACTOR,
      finishedAt: new Date(),
    },
  });

  // Hasil utuh run agent (dipakai KOMIT — serverless tanpa engine, Task 51).
  if (opts.providedResult) {
    await saveAgentResult(runBatch.id, result);
  }

  if (result.dqIssues.length > 0) {
    await db.dQIssue.createMany({
      data: result.dqIssues.map((d) => ({
        runBatchId: runBatch.id,
        severity: d.severity,
        code: d.code,
        message: d.message,
        source: d.source ?? null,
        sheet: d.sheet ?? null,
        rawValue: d.rawValue ?? null,
        rowNumber: d.rowNumber ?? null,
      })),
    });
  }

  if (result.sourceFiles.length > 0) {
    await db.sourceFile.createMany({
      data: result.sourceFiles.map((f) => ({
        runBatchId: runBatch.id,
        folderKey: f.folderKey,
        fileName: f.fileName,
        sheetName: f.sheetName ?? null,
        rowCount: f.rowCount,
        sizeBytes: f.sizeBytes,
        status: f.status,
      })),
    });
  }

  await audit("INGEST_PROCESS", "RunBatch", runBatch.id, {
    periodKey: params.periodKey,
    status: result.status,
    rowCount: result.summary.rowCount,
    warningCount: result.summary.warningCount,
    ...(opts.providedResult ? { engineSource: "agent", agentName: opts.agentName ?? null } : {}),
  });

  return { runBatchId: runBatch.id, result };
}

function mapRows(result: EngineResult, snapshotId: string) {
  return result.rows.map((r) => ({
    snapshotId,
    restoCode: r.restoCode,
    restoName: r.restoName,
    itemName: r.itemName,
    satuan: r.satuan,
    kategori: r.kategori,
    isGR: r.isGR,
    day: r.day,
    qtySaldoAwal: r.qtySaldoAwal,
    qtySO: r.qtySO,
    qtySaldoAkhir: r.qtySaldoAkhir,
    qtyDeviasi: r.qtyDeviasi,
    qtyIN: r.qtyIN,
    qtyBarangMasuk: r.qtyBarangMasuk,
    qtyCOM: r.qtyCOM,
    qtySelisihIN: r.qtySelisihIN,
    qtyBarangKeluar: r.qtyBarangKeluar,
    qtyACR: r.qtyACR,
    hargaEfektif: r.hargaEfektif,
    konversiOk: r.konversiOk,
    nominal: r.nominal,
    cekJson: JSON.stringify(r.cek),
    auditNote: r.auditNote ?? null,
    fingerprint: stableFingerprint(r.restoCode, r.itemName, r.satuan, r.kategori),
  }));
}

/**
 * Langkah 2: KOMIT — tulis snapshot permanen atas hasil run. Periode lama
 * ACTIVE → SUPERSEDED. Kegagalan di tengah → data lama tak tersentuh (NFR-3).
 * Dua sumber hasil (Task 51):
 *  - run biasa        → panggil ulang engine (FR-12 idempotent → identik).
 *  - run agent laptop  → hasil EngineResult tersimpan (gzip+b64 di AgentResult)
 *                        DIPAKAI APA ADANYA — serverless Vercel tidak punya
 *                        engine; engine deterministik → hasil tersimpan =
 *                        output kanonik run itu (FR-12 tetap jujur).
 *
 * Task 54 — KOMIT BERTAHAP (resumable): menulis ±88rb baris snapshot ke DB
 * remote dalam SATU panggilan serverless TERBUKTI >60 dtk (FUNCTION_INVOCATION_
 * TIMEOUT dua kali di produksi; snapshot BUILDING yatim). Kini komit dipecah:
 *  - pemanggil (browser / seed-demo) memanggil commitStep() BERULANG sampai
 *    done; tiap langkah bekerja maks ±30 dtk — jauh di bawah 60 dtk.
 *  - TAHAP + CURSOR tersimpan di snapshot.paramsJson (tanpa ubah schema DB);
 *    langkah berikutnya melanjutkan dari cursor — komit yang terputus dimanapun
 *    (tab tertutup, koneksi putus, timeout) cukup ditekan Komit ulang.
 *  - cursor maju lewat compare-and-set paramsJson (updateMany WHERE paramsJson
 *    = nilai lama) — dua langkah paralel tidak bisa menggandakan potongan sama.
 *  - tiap potongan baris = SATU createMany = SATU statement INSERT = atomik;
 *    kegagalan di tengah tidak menyisakan setengah potongan.
 *  - harga (unique runBatchId+item+satuan) & selisih (unique snapshot+resto)
 *    ditulis skipDuplicates → aman diulang; PO idempoten lewat unique
 *    (snapshotId, poNumber) + item hanya ditulis bila header masih kosong.
 *  - sebelum promosi ACTIVE: jumlah baris/selisih/PO DIVERIFIKASI = ringkasan
 *    run — build rusak ditolak jujur (hapus BUILDING di Konfigurasi, komit
 *    ulang), tidak pernah aktif diam-diam.
 */
export type CommitPhase = "rows" | "prices" | "selisih" | "po" | "finalize";

export type CommitStepResult =
  | { done: false; phase: CommitPhase; written: number; total: number }
  | {
      done: true; snapshotId: string; periodKey: string; rowCount: number;
      supersededPrevious: boolean; definitionVersion: string;
    };

const COMMIT_PHASES: CommitPhase[] = ["rows", "prices", "selisih", "po", "finalize"];

/** Cache hasil run per-instance lambda: langkah-langkah komit memakai instance
 *  hangat yang sama — baca AgentResult 5–15 MB / panggil ulang engine cukup
 *  sekali per instance, bukan sekali per langkah. TTL 10 menit. */
const commitResultCacheHolder = globalThis as unknown as {
  __smCommitResultCache?: Map<string, { result: EngineResult; expires: number }>;
};
const commitResultCache =
  commitResultCacheHolder.__smCommitResultCache ?? new Map<string, { result: EngineResult; expires: number }>();
commitResultCacheHolder.__smCommitResultCache = commitResultCache;

function buildParamsJson(tanggalH: number, ambangAcrPct: number, phase: CommitPhase, cursor: number) {
  // Bentuk kanonik (urutan kunci tetap) — dipakai sebagai nilai compare-and-set.
  return JSON.stringify({ tanggalH, ambangAcrPct, buildPhase: phase, buildCursor: cursor });
}

/** Satu langkah komit. Panggil berulang (dari route yang sama) sampai done. */
export async function commitStep(runBatchId: string, budgetMs = 30_000): Promise<CommitStepResult> {
  const run = await db.runBatch.findUnique({
    where: { id: runBatchId },
    include: { snapshot: true },
  });
  if (!run) throw new Error("Run tidak ditemukan.");
  if (run.committedAt) throw new Error("Run ini sudah dikomit sebelumnya.");

  const params = parseJsonSafe<EngineProcessRequest>(run.paramsJson, {
    periodKey: run.periodKey,
    tanggalH: 25,
    ambangAcrPct: 80,
    bundleName: run.bundleName ?? undefined,
  });
  // Task 55: run produksi selalu hasil agent (engineSource="agent"); sisanya
  // demo. Run lawas ber-marker bundleId tidak bisa dikomit lagi di serverless
  // tanpa bundle — pesan jujur mengarahkan ke agent.
  const parsed = parseJsonSafe<{
    bundleId?: string | null;
    engineSource?: string;
    agentName?: string | null;
  }>(run.paramsJson, {});
  const bundleId = typeof parsed.bundleId === "string" ? parsed.bundleId : null;
  const isAgentRun = parsed.engineSource === "agent";
  if (bundleId && !isAgentRun) {
    throw new Error(
      "Run lama berbasis unggahan bundle — jalur unggah sudah dihapus. Jalankan ulang lewat agent laptop (tab Proses & Ingest) lalu komit run barunya.",
    );
  }

  // ---- Hasil run (cache per-instance, lihat commitResultCache) ----
  const cached = commitResultCache.get(run.id);
  if (cached && cached.expires <= Date.now()) commitResultCache.delete(run.id);
  let result: EngineResult | undefined =
    cached && cached.expires > Date.now() ? cached.result : undefined;
  if (!result) {
    if (isAgentRun) {
      const stored = await readAgentResult(run.id);
      if (!stored) {
        throw new Error(
          "Hasil run agent tidak tersimpan di server — jalankan ulang job agent (atau proses ulang run ini dari instalasi lokal).",
        );
      }
      result = stored;
    } else {
      result = await engineProcess({
        periodKey: params.periodKey,
        tanggalH: params.tanggalH,
        ambangAcrPct: params.ambangAcrPct,
        bundleName: params.bundleName ?? undefined,
        seed: params.seed ?? 0,
      });
    }
    commitResultCache.set(run.id, { result, expires: Date.now() + 10 * 60_000 });
  }

  // ---- Snapshot BUILDING: LANJUTKAN dari cursor, atau mulai bersih ----
  let snapshot = run.snapshot;
  const buildState = snapshot
    ? parseJsonSafe<{ buildPhase?: unknown; buildCursor?: unknown }>(snapshot.paramsJson, {})
    : {};
  const resumable =
    snapshot !== null &&
    snapshot.state === "BUILDING" &&
    typeof buildState.buildPhase === "string" &&
    COMMIT_PHASES.includes(buildState.buildPhase as CommitPhase) &&
    typeof buildState.buildCursor === "number";
  if (snapshot && snapshot.state !== "BUILDING") {
    // Hanya mungkin bila promosi setengah jalan (seharusnya transaksi atomik).
    throw new Error(
      `Snapshot run ini berstatus ${snapshot.state} tapi run belum tercatat komit — segarkan halaman, cek tab Konfigurasi.`,
    );
  }
  if (snapshot && !resumable) {
    // BUILDING yatim kode LAMA (komit sekali-jalan tanpa cursor — terbukti ada
    // di produksi) tidak bisa dilanjutkan dengan aman → bersihkan, mulai baru.
    await db.periodSnapshot.delete({ where: { id: snapshot.id } }).catch(() => undefined);
    await db.priceHistory.deleteMany({ where: { runBatchId: run.id } }).catch(() => undefined);
    snapshot = null;
  }
  if (!snapshot) {
    // Pra-bersih BUILDING yatim lain dari run yang sama (menahan unique runBatchId).
    await db.periodSnapshot.deleteMany({
      where: { runBatchId: run.id, state: "BUILDING" },
    });
    await db.priceHistory.deleteMany({ where: { runBatchId: run.id } });
    try {
      snapshot = await db.periodSnapshot.create({
        data: {
          periodKey: run.periodKey,
          runBatchId: run.id,
          state: "BUILDING",
          restoCount: result.summary.restoCount,
          itemCount: result.summary.itemCount,
          rowCount: result.summary.rowCount,
          dayCount: result.summary.dayCount,
          nominalTotal: result.summary.nominalTotal,
          deviasiQtyTotal: result.summary.deviasiQtyTotal,
          definitionVersion: result.definitionVersion,
          paramsJson: buildParamsJson(params.tanggalH, params.ambangAcrPct, "rows", 0),
          committedBy: ACTOR,
        },
      });
    } catch (err) {
      if (isP2002(err)) {
        throw new Error("Run ini sedang dikomit di permintaan lain — tunggu sebentar lalu cek lagi.");
      }
      throw err;
    }
  }
  const snap = snapshot;
  let phase: CommitPhase = resumable ? (buildState.buildPhase as CommitPhase) : "rows";
  let cursor: number = resumable ? (buildState.buildCursor as number) : 0;
  let paramsJsonNow = snap.paramsJson;

  // Compare-and-set tahap+cursor: hanya maju bila paramsJson belum berubah.
  const cas = async (nextPhase: CommitPhase, nextCursor: number): Promise<boolean> => {
    const nextJson = buildParamsJson(params.tanggalH, params.ambangAcrPct, nextPhase, nextCursor);
    const res = await db.periodSnapshot.updateMany({
      where: { id: snap.id, paramsJson: paramsJsonNow },
      data: { paramsJson: nextJson },
    });
    if (res.count !== 1) return false; // langkah lain sudah maju — baca ulang nanti
    paramsJsonNow = nextJson;
    phase = nextPhase;
    cursor = nextCursor;
    return true;
  };

  const summary = result.summary;
  const t0 = Date.now();
  const rows = phase === "rows" ? mapRows(result, snap.id) : [];

  while (Date.now() - t0 < budgetMs) {
    if (phase === "rows") {
      if (cursor >= rows.length) {
        if (!(await cas("prices", 0))) break;
        continue;
      }
      // 2000×25 kolom = 50.000 parameter < batas protokol Postgres 65.535.
      const slice = rows.slice(cursor, cursor + 2000);
      await db.snapshotRow.createMany({ data: slice });
      if (!(await cas("rows", cursor + slice.length))) break;
      continue;
    }
    if (phase === "prices") {
      if (result.prices.length > 0) {
        // Idempoten tanpa skipDuplicates (tak didukung SQLite): satu createMany
        // = satu statement atomik; P2002 = fase ini sempat tuntas sebelumnya.
        try {
          await db.priceHistory.createMany({
            data: result.prices.map((p) => ({
              runBatchId: run.id,
              itemName: p.itemName,
              satuan: p.satuan,
              harga: p.harga,
              rasioKonversi: p.rasioKonversi,
              konversiOk: p.konversiOk,
              alasan: p.alasan ?? null,
            })),
          });
        } catch (err) {
          if (!isP2002(err)) throw err;
        }
      }
      if (!(await cas("selisih", 0))) break;
      continue;
    }
    if (phase === "selisih") {
      if (result.selisihIn.length > 0) {
        // Idempoten — sama seperti fase harga (unique snapshotId+restoCode).
        try {
          await db.selisihInResto.createMany({
            data: result.selisihIn.map((s) => ({
              snapshotId: snap.id,
              restoCode: s.restoCode,
              restoName: s.restoName,
              inAccurate: s.inAccurate,
              barangMasuk: s.barangMasuk,
              selisih: s.selisih,
              hasilAudit: s.hasilAudit,
              skorResto: s.skorResto,
              itemBerselisih: s.itemBerselisih,
              tanggalTerdampak: s.tanggalTerdampak,
            })),
          });
        } catch (err) {
          if (!isP2002(err)) throw err;
        }
      }
      if (!(await cas("po", 0))) break;
      continue;
    }
    if (phase === "po") {
      if (cursor >= result.po.length) {
        if (!(await cas("finalize", 0))) break;
        continue;
      }
      // Idempoten: header unik (snapshotId, poNumber); items satu createMany
      // atomik — hanya ditulis bila header masih kosong (lanjut ulang aman).
      const po = result.po[cursor];
      let header = await db.poHeader.findUnique({
        where: { snapshotId_poNumber: { snapshotId: snap.id, poNumber: po.poNumber } },
      });
      if (!header) {
        header = await db.poHeader.create({
          data: {
            snapshotId: snap.id,
            cabang: po.cabang,
            restoName: po.restoName,
            poNumber: po.poNumber,
            tanggal: po.tanggal,
            supplier: po.supplier,
            itemCount: po.itemCount,
            status: po.status,
            statusPesanan: po.statusPesanan,
            annotasi: po.annotasi ?? null,
          },
        });
      }
      const existingItems = await db.poItem.count({ where: { poHeaderId: header.id } });
      if (po.items.length > 0 && existingItems === 0) {
        await db.poItem.createMany({
          data: po.items.map((it) => ({
            poHeaderId: header.id,
            itemName: it.itemName,
            qty: it.qty,
            satuan: it.satuan,
            status: it.status,
            diterimaSebagian: it.diterimaSebagian,
          })),
        });
      }
      if (!(await cas("po", cursor + 1))) break;
      continue;
    }
    // phase === "finalize"
    const rowCount = await db.snapshotRow.count({ where: { snapshotId: snap.id } });
    const selisihCount = await db.selisihInResto.count({ where: { snapshotId: snap.id } });
    const poCount = await db.poHeader.count({ where: { snapshotId: snap.id } });
    if (
      rowCount !== summary.rowCount ||
      selisihCount !== result.selisihIn.length ||
      poCount !== result.po.length
    ) {
      throw new Error(
        `Snapshot build tidak utuh (baris ${rowCount}/${summary.rowCount} · selisih ${selisihCount}/${result.selisihIn.length} · PO ${poCount}/${result.po.length}) — hapus snapshot BUILDING ini di tab Konfigurasi, lalu tekan Komit ulang. Data lama tidak tersentuh (NFR-3).`,
      );
    }
    await db.dQIssue.updateMany({ where: { runBatchId: run.id }, data: { snapshotId: snap.id } });

    // Promosi ACTIVE + supersede periode lama + committedAt + paramsJson bersih
    // (buang buildPhase/buildCursor) — SATU TRANSAKSI (audit 48-g-data).
    const supersededList = await db.$transaction(async (tx) => {
      const cur = await tx.runBatch.findUnique({
        where: { id: run.id },
        select: { committedAt: true },
      });
      if (cur?.committedAt) {
        throw new Error("Run ini sudah dikomit sebelumnya.");
      }
      const toSupersede = await tx.periodSnapshot.findMany({
        where: { periodKey: snap.periodKey, state: "ACTIVE", id: { not: snap.id } },
        select: { id: true },
      });
      if (toSupersede.length > 0) {
        await tx.periodSnapshot.updateMany({
          where: { id: { in: toSupersede.map((s) => s.id) } },
          data: { state: "SUPERSEDED", supersededAt: new Date(), supersededById: snap.id },
        });
      }
      await tx.periodSnapshot.update({
        where: { id: snap.id },
        data: {
          state: "ACTIVE",
          paramsJson: JSON.stringify({ tanggalH: params.tanggalH, ambangAcrPct: params.ambangAcrPct }),
        },
      });
      await tx.runBatch.update({ where: { id: run.id }, data: { committedAt: new Date() } });
      return toSupersede;
    });

    await audit("SNAPSHOT_COMMIT", "PeriodSnapshot", snap.id, {
      periodKey: snap.periodKey,
      rowCount: summary.rowCount,
      definitionVersion: result.definitionVersion,
      superseded: supersededList.length,
    });
    commitResultCache.delete(run.id);

    return {
      done: true,
      snapshotId: snap.id,
      periodKey: snap.periodKey,
      rowCount: summary.rowCount,
      supersededPrevious: supersededList.length > 0,
      definitionVersion: result.definitionVersion,
    };
  }

  // Anggaran waktu habis (atau CAS kalah dari langkah paralel) — client
  // memanggil langkah berikutnya; cursor sudah tersimpan di paramsJson.
  return {
    done: false,
    phase,
    written: cursor,
    total: phase === "rows" ? rows.length : phase === "po" ? result.po.length : 0,
  };
}

/** Snapshot ACTIVE terbaru (periode paling akhir). */
export async function latestActiveSnapshot() {
  return db.periodSnapshot.findFirst({
    where: { state: "ACTIVE" },
    orderBy: [{ periodKey: "desc" }, { committedAt: "desc" }],
  });
}

export async function activeSnapshotByPeriod(periodKey: string) {
  return db.periodSnapshot.findFirst({
    where: { periodKey, state: "ACTIVE" },
    orderBy: { committedAt: "desc" },
  });
}

export async function previousActiveSnapshot(periodKey: string) {
  return activeSnapshotByPeriod(prevPeriodKey(periodKey));
}

/** Bentuk ringkas snapshot untuk API/UI. */
export function toSnapshotSummary(row: {
  id: string; periodKey: string; state: string; restoCount: number; itemCount: number;
  rowCount: number; dayCount: number; nominalTotal: number; deviasiQtyTotal: number;
  definitionVersion: string; paramsJson: string; committedAt: Date; committedBy: string;
  supersededAt: Date | null;
}): import("./types").SnapshotSummary {
  return {
    id: row.id,
    periodKey: row.periodKey,
    state:
      row.state === "ACTIVE" ? "ACTIVE" : row.state === "BUILDING" ? "BUILDING" : "SUPERSEDED",
    restoCount: row.restoCount,
    itemCount: row.itemCount,
    rowCount: row.rowCount,
    dayCount: row.dayCount,
    nominalTotal: row.nominalTotal,
    deviasiQtyTotal: row.deviasiQtyTotal,
    definitionVersion: row.definitionVersion,
    params: parseJsonSafe(row.paramsJson, { tanggalH: 25, ambangAcrPct: 80 }),
    committedAt: row.committedAt.toISOString(),
    committedBy: row.committedBy,
    supersededAt: row.supersededAt ? row.supersededAt.toISOString() : null,
  };
}

export type { CekLabel, AuditNote, DqSeverity, EngineResult, EngineSummary };
