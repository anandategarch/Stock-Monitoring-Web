import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { parseJsonSafe } from "@/lib/snapshot-service";
import type { DqCode, DqSeverity, EngineProcessRequest, EngineSummary, LogLineDto, RunDetail } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/runs/[id] — detail run: ringkasan, DQ, log, manifest file (pratinjau FR-1/FR-3). */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const run = await db.runBatch.findUnique({
    where: { id },
    include: {
      dqIssues: { orderBy: [{ severity: "asc" }, { createdAt: "asc" }] },
      sourceFiles: { orderBy: { folderKey: "asc" } },
    },
  });
  if (!run) {
    return NextResponse.json({ error: "Run tidak ditemukan." }, { status: 404 });
  }

  const params = parseJsonSafe<EngineProcessRequest>(run.paramsJson, {
    periodKey: run.periodKey, tanggalH: 25, ambangAcrPct: 80, bundleName: undefined,
  });

  const detail: RunDetail = {
    run: {
      id: run.id,
      periodKey: run.periodKey,
      bundleName: run.bundleName,
      status: run.status,
      definitionVersion: run.definitionVersion,
      engineKind: run.engineKind,
      engineVersion: run.engineVersion,
      durationMs: run.durationMs,
      actor: run.actor,
      startedAt: run.startedAt.toISOString(),
      committedAt: run.committedAt ? run.committedAt.toISOString() : null,
      summary: parseJsonSafe<EngineSummary | null>(run.summaryJson, null),
      params: { tanggalH: params.tanggalH, ambangAcrPct: params.ambangAcrPct, bundleName: params.bundleName ?? null },
    },
    dqIssues: run.dqIssues.map((d) => ({
      id: d.id,
      severity: d.severity as DqSeverity,
      code: d.code as DqCode,
      message: d.message,
      source: d.source,
      sheet: d.sheet,
      rawValue: d.rawValue,
      rowNumber: d.rowNumber,
    })),
    logs: parseJsonSafe<LogLineDto[]>(run.logJson, []),
    sourceFiles: run.sourceFiles.map((f) => ({
      id: f.id,
      folderKey: f.folderKey,
      fileName: f.fileName,
      sheetName: f.sheetName,
      rowCount: f.rowCount,
      sizeBytes: f.sizeBytes,
      status: (f.status as "OK" | "SKIP" | "WARNING") ?? "OK",
    })),
  };
  return NextResponse.json(detail);
}

/**
 * DELETE /api/runs/[id] — hapus run dari riwayat (Task 54: user meminta
 * pembersihan run demo/uji yang menumpuk). Jujur soal relasi:
 *  - Run YANG PUNYA snapshot → ditolak: hapus snapshot dulu di tab Konfigurasi
 *    (snapshot adalah data analisis yang sudah dikomit, bukan milik riwayat).
 *  - Run yang sedang dirakit job agent (RUNNING/FINALIZING) → ditolak.
 *  - Ikut terhapus cascade: DQIssue, SourceFile, PriceHistory, dan AgentResult
 *    (tabel tanpa relasi FK — dibersihkan manual di transaksi yang sama).
 */
export async function DELETE(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const run = await db.runBatch.findUnique({
    where: { id },
    include: { snapshot: { select: { id: true, periodKey: true, state: true } } },
  });
  if (!run) {
    return NextResponse.json({ error: "Run tidak ditemukan." }, { status: 404 });
  }
  if (run.snapshot) {
    return NextResponse.json(
      {
        error: `Run ini punya snapshot periode ${run.snapshot.periodKey} (${run.snapshot.state}) — hapus snapshot-nya dulu di tab Konfigurasi, barulah run bisa dihapus dari riwayat.`,
      },
      { status: 409 },
    );
  }
  const inflight = await db.agentJob.findFirst({
    where: { runBatchId: id, status: { in: ["RUNNING", "FINALIZING"] } },
    select: { id: true },
  });
  if (inflight) {
    return NextResponse.json(
      { error: "Run ini sedang dirakit dari job agent yang berjalan — tunggu job selesai dulu." },
      { status: 409 },
    );
  }
  const periodKey = run.periodKey;
  await db.$transaction([
    db.agentResult.deleteMany({ where: { runBatchId: id } }),
    db.runBatch.delete({ where: { id } }),
  ]);
  await db.auditLog.create({
    data: {
      action: "RUN_DELETE",
      entity: "RunBatch",
      entityId: id,
      detailJson: JSON.stringify({
        periodKey,
        bundleName: run.bundleName,
        engineKind: run.engineKind,
        status: run.status,
        rowCount: parseJsonSafe<{ rowCount?: number } | null>(run.summaryJson, null)?.rowCount ?? null,
      }),
      actor: "analyst",
    },
  });
  return NextResponse.json({ ok: true, id, periodKey });
}
