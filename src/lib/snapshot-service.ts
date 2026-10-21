// ============================================================
// Snapshot service — jantung alur Ingest → Pratinjau → Komit (FR-3/FR-4/FR-12/FR-24).
// Strategi komit: engine IDEMPOTENT → komit memanggil ulang /process dengan
// parameter run yang sama, hasil identik, lalu menulis snapshot permanen.
// Snapshot immutable: periode lama → SUPERSEDED (tetap tersimpan).
// ============================================================
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { engineProcess, ENGINE_PROD_URL } from "@/lib/engine";
import { resolveBundlePath } from "@/lib/bundles";
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
  /** Mode produksi (FR-1/FR-10): id bundle terunggah — dipakai komit ulang
   *  (FR-12 idempotent: bundleId sama → bundlePath sama → hasil identik). */
  bundleId?: string | null;
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
 * Demo (tanpa bundleId) → engine demo :3030 · bundleId terisi → engine PRODUKSI :3031
 * (pipeline asli v3.9.71, FR-10).
 * Opsi `providedResult` (Task 51 — agent lokal): hasil EngineResult diproses di
 * PYTHON LAPTOP user (tarik Drive + engine FastAPI lokal) lalu diunggah agent —
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
    const engineUrl = params.bundleId ? ENGINE_PROD_URL : undefined;
    const bundlePath = params.bundleId ? await resolveBundlePath(params.bundleId) : undefined;
    const req: EngineProcessRequest = {
      periodKey: params.periodKey,
      tanggalH: params.tanggalH,
      ambangAcrPct: params.ambangAcrPct,
      bundleName: params.bundleName ?? undefined,
      seed: params.seed ?? 0,
      ...(bundlePath ? { bundlePath } : {}),
    };
    result = await engineProcess(req, engineUrl);
    paramsForLog = { ...req, bundleId: params.bundleId ?? null };
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
 * Langkah 2: KOMIT — dapatkan hasil run, tulis snapshot permanen. Periode lama
 * ACTIVE → SUPERSEDED. Kegagalan di tengah → snapshot dibersihkan, data lama
 * tak tersentuh (NFR-3).
 * Dua sumber hasil (Task 51):
 *  - run biasa        → panggil ulang engine (FR-12 idempotent → identik).
 *  - run agent laptop  → hasil EngineResult tersimpan (gzip+b64 di AgentResult)
 *                        DIPAKAI APA ADANYA — serverless Vercel tidak punya
 *                        engine; engine deterministik → hasil tersimpan =
 *                        output kanonik run itu (FR-12 tetap jujur).
 */
export async function commitRun(runBatchId: string): Promise<{
  snapshotId: string;
  periodKey: string;
  rowCount: number;
  supersededPrevious: boolean;
  definitionVersion: string;
}> {
  const run = await db.runBatch.findUnique({ where: { id: runBatchId } });
  if (!run) throw new Error("Run tidak ditemukan.");
  if (run.committedAt) throw new Error("Run ini sudah dikomit sebelumnya.");

  const params = parseJsonSafe<EngineProcessRequest>(run.paramsJson, {
    periodKey: run.periodKey,
    tanggalH: 25,
    ambangAcrPct: 80,
    bundleName: run.bundleName ?? undefined,
  });
  // FR-12 idempotent: bundleId (bukan path) yang tersimpan — resolve ulang
  // supaya komit tetap sahih walau direktori bundle dipindah/di-rename.
  const parsed = parseJsonSafe<{
    bundleId?: string | null;
    engineSource?: string;
    agentName?: string | null;
  }>(run.paramsJson, {});
  const bundleId = typeof parsed.bundleId === "string" ? parsed.bundleId : null;
  const isAgentRun = parsed.engineSource === "agent";

  let result: EngineResult;
  if (isAgentRun) {
    const stored = await readAgentResult(run.id);
    if (!stored) {
      throw new Error(
        "Hasil run agent tidak tersimpan di server — jalankan ulang job agent (atau proses ulang run ini dari instalasi lokal).",
      );
    }
    result = stored;
  } else {
    result = await engineProcess(
      {
        periodKey: params.periodKey,
        tanggalH: params.tanggalH,
        ambangAcrPct: params.ambangAcrPct,
        bundleName: params.bundleName ?? undefined,
        seed: params.seed ?? 0,
        ...(bundleId ? { bundlePath: await resolveBundlePath(bundleId) } : {}),
      },
      bundleId ? ENGINE_PROD_URL : undefined,
    );
  }

  const summary = result.summary;

  // Buat snapshot dulu dalam state BUILDING (belum terlihat), isi semua data,
  // baru promosikan ACTIVE. Gagal di tengah → hapus (cascade) + lempar error.
  // Pra-bersih BUILDING yatim dari komit yang gagal sebelumnya (audit 48-g-data):
  // tanpa ini, snapshot BUILDING tua menahan unique(runBatchId) selamanya.
  await db.periodSnapshot.deleteMany({
    where: { runBatchId: run.id, state: "BUILDING" },
  });

  let snapshot;
  try {
    snapshot = await db.periodSnapshot.create({
      data: {
        periodKey: run.periodKey,
        runBatchId: run.id,
        state: "BUILDING",
        restoCount: summary.restoCount,
        itemCount: summary.itemCount,
        rowCount: summary.rowCount,
        dayCount: summary.dayCount,
        nominalTotal: summary.nominalTotal,
        deviasiQtyTotal: summary.deviasiQtyTotal,
        definitionVersion: result.definitionVersion,
        paramsJson: JSON.stringify({ tanggalH: params.tanggalH, ambangAcrPct: params.ambangAcrPct }),
        committedBy: ACTOR,
      },
    });
  } catch (err) {
    if (isP2002(err)) {
      throw new Error("Run ini sedang dikomit di permintaan lain — tunggu sebentar lalu cek lagi.");
    }
    throw err;
  }

  try {
    const rows = mapRows(result, snapshot.id);
    for (let i = 0; i < rows.length; i += 500) {
      await db.snapshotRow.createMany({ data: rows.slice(i, i + 500) });
    }

    if (result.prices.length > 0) {
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
    }

    if (result.selisihIn.length > 0) {
      await db.selisihInResto.createMany({
        data: result.selisihIn.map((s) => ({
          snapshotId: snapshot.id,
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
    }

    for (const po of result.po) {
      const header = await db.poHeader.create({
        data: {
          snapshotId: snapshot.id,
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
      if (po.items.length > 0) {
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
    }

    // Tautkan DQ issue run ini ke snapshot. Promosi ACTIVE + supersede periode
    // lama + committedAt DIBUNGKUS SATU TRANSAKSI (audit 48-g-data): komit ganda
    // konkuren dicek ulang DI DALAM transaksi — tak mungkin ada dua ACTIVE.
    await db.dQIssue.updateMany({ where: { runBatchId: run.id }, data: { snapshotId: snapshot.id } });

    const supersededList = await db.$transaction(async (tx) => {
      const cur = await tx.runBatch.findUnique({
        where: { id: run.id },
        select: { committedAt: true },
      });
      if (cur?.committedAt) {
        throw new Error("Run ini sudah dikomit sebelumnya.");
      }
      const toSupersede = await tx.periodSnapshot.findMany({
        where: { periodKey: snapshot.periodKey, state: "ACTIVE", id: { not: snapshot.id } },
        select: { id: true },
      });
      if (toSupersede.length > 0) {
        await tx.periodSnapshot.updateMany({
          where: { id: { in: toSupersede.map((s) => s.id) } },
          data: { state: "SUPERSEDED", supersededAt: new Date(), supersededById: snapshot.id },
        });
      }
      await tx.periodSnapshot.update({ where: { id: snapshot.id }, data: { state: "ACTIVE" } });
      await tx.runBatch.update({ where: { id: run.id }, data: { committedAt: new Date() } });
      return toSupersede;
    });

    await audit("SNAPSHOT_COMMIT", "PeriodSnapshot", snapshot.id, {
      periodKey: snapshot.periodKey,
      rowCount: summary.rowCount,
      definitionVersion: result.definitionVersion,
      superseded: supersededList.length,
    });

    return {
      snapshotId: snapshot.id,
      periodKey: snapshot.periodKey,
      rowCount: summary.rowCount,
      supersededPrevious: supersededList.length > 0,
      definitionVersion: result.definitionVersion,
    };
  } catch (err) {
    // NFR-3: kegagalan tidak boleh menyisakan snapshot setengah jadi.
    // PriceHistory di-key runBatchId (bukan snapshotId, tak ikut cascade) —
    // bersihkan juga, else komit ulang run yang sama P2002 selamanya (audit 48-g-data).
    await db.periodSnapshot.delete({ where: { id: snapshot.id } }).catch(() => undefined);
    await db.priceHistory.deleteMany({ where: { runBatchId: run.id } }).catch(() => undefined);
    throw err;
  }
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
    state: row.state === "ACTIVE" ? "ACTIVE" : "SUPERSEDED",
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
