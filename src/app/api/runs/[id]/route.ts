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
