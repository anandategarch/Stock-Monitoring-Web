import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { parseJsonSafe } from "@/lib/snapshot-service";
import type { EngineSummary, RunSummary } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/runs — riwayat run terbaru (FR-5). */
export async function GET() {
  const runs = await db.runBatch.findMany({ orderBy: { startedAt: "desc" }, take: 20 });
  const data: RunSummary[] = runs.map((r) => ({
    id: r.id,
    periodKey: r.periodKey,
    bundleName: r.bundleName,
    status: r.status,
    definitionVersion: r.definitionVersion,
    engineKind: r.engineKind,
    engineVersion: r.engineVersion,
    durationMs: r.durationMs,
    actor: r.actor,
    startedAt: r.startedAt.toISOString(),
    committedAt: r.committedAt ? r.committedAt.toISOString() : null,
    summary: parseJsonSafe<EngineSummary | null>(r.summaryJson, null),
  }));
  return NextResponse.json({ runs: data });
}
