import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { engineHealth } from "@/lib/engine";
import { embedFallbackEnabled } from "@/lib/engine-embed";
import {
  latestActiveSnapshot, parseJsonSafe, previousActiveSnapshot, toSnapshotSummary,
} from "@/lib/snapshot-service";
import type { EngineSummary, OverviewResponse, RunSummary } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/overview — KPI + tren + engine untuk tab Ikhtisar. */
export async function GET() {
  const active = await latestActiveSnapshot();

  let overview: OverviewResponse["active"] = null;
  let previous: OverviewResponse["previous"] = null;
  let nominalDeltaPct: number | null = null;
  let nominalPerResto: OverviewResponse["nominalPerResto"] = [];
  let topDeviations: OverviewResponse["topDeviations"] = [];
  let restos: OverviewResponse["restos"] = [];
  let trend: OverviewResponse["trend"] = [];

  if (active) {
    overview = { ...toSnapshotSummary(active), snapshotId: active.id };

    const prev = await previousActiveSnapshot(active.periodKey);
    if (prev) {
      previous = {
        snapshotId: prev.id,
        periodKey: prev.periodKey,
        nominalTotal: prev.nominalTotal,
      };
      nominalDeltaPct =
        prev.nominalTotal !== 0
          ? ((active.nominalTotal - prev.nominalTotal) / Math.abs(prev.nominalTotal)) * 100
          : null;
    }

    const rows = await db.snapshotRow.findMany({
      where: { snapshotId: active.id },
      select: {
        restoCode: true, restoName: true, itemName: true, satuan: true, kategori: true,
        nominal: true, qtyDeviasi: true,
      },
    });

    const perResto = new Map<string, { restoName: string; nominal: number; deviasiQty: number }>();
    const perPair = new Map<string, { restoCode: string; restoName: string; itemName: string; satuan: string; kategori: string; nominal: number; qtyDeviasi: number }>();
    for (const r of rows) {
      let e = perResto.get(r.restoCode);
      if (!e) {
        e = { restoName: r.restoName, nominal: 0, deviasiQty: 0 };
        perResto.set(r.restoCode, e);
      }
      if (r.nominal !== null) e.nominal += r.nominal;
      if (r.qtyDeviasi !== null) e.deviasiQty += r.qtyDeviasi;

      if (r.nominal !== null && Math.abs(r.nominal) > 0) {
        perPair.set(`${r.restoCode}|${r.itemName}|${r.satuan}`, {
          restoCode: r.restoCode, restoName: r.restoName, itemName: r.itemName,
          satuan: r.satuan, kategori: r.kategori, nominal: r.nominal,
          qtyDeviasi: r.qtyDeviasi ?? 0,
        });
      }
    }

    restos = [...perResto.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([restoCode, v]) => ({ restoCode, restoName: v.restoName }));

    nominalPerResto = [...perResto.entries()]
      .map(([restoCode, v]) => ({ restoCode, restoName: v.restoName, nominal: v.nominal, deviasiQty: v.deviasiQty }))
      .sort((a, b) => Math.abs(b.nominal) - Math.abs(a.nominal));

    topDeviations = [...perPair.values()]
      .sort((a, b) => Math.abs(b.nominal) - Math.abs(a.nominal))
      .slice(0, 8);

    const actives = await db.periodSnapshot.findMany({
      where: { state: "ACTIVE" },
      orderBy: { periodKey: "asc" },
      select: { periodKey: true, nominalTotal: true, deviasiQtyTotal: true },
    });
    trend = actives.map((s) => ({
      periodKey: s.periodKey,
      nominalTotal: s.nominalTotal,
      deviasiQtyTotal: s.deviasiQtyTotal,
    }));
  }

  const caseGroups = await db.followUpCase.groupBy({ by: ["status"], _count: true });
  const cases = { pending: 0, diproses: 0, selesai: 0, dibatalkan: 0, total: 0 };
  for (const g of caseGroups) {
    const n = g._count;
    cases.total += n;
    if (g.status === "PENDING") cases.pending = n;
    else if (g.status === "DIPROSES") cases.diproses = n;
    else if (g.status === "SELESAI") cases.selesai = n;
    else if (g.status === "DIBATALKAN") cases.dibatalkan = n;
  }

  let dq = { error: 0, warning: 0, info: 0 };
  if (active) {
    const dqGroups = await db.dQIssue.groupBy({
      by: ["severity"],
      _count: true,
      where: { snapshotId: active.id },
    });
    for (const g of dqGroups) {
      const n = g._count;
      if (g.severity === "ERROR") dq.error = n;
      else if (g.severity === "WARNING") dq.warning = n;
      else if (g.severity === "INFO") dq.info = n;
    }
  }

  const runRows = await db.runBatch.findMany({ orderBy: { startedAt: "desc" }, take: 5 });
  const runs: RunSummary[] = runRows.map((r) => ({
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

  const engine = await engineHealth();

  const resp: OverviewResponse = {
    active: overview,
    previous,
    nominalDeltaPct,
    cases,
    dq,
    runs,
    nominalPerResto,
    trend,
    topDeviations,
    engine,
    engineReachable: engine !== null,
    engineEmbedAvailable: embedFallbackEnabled(),
    restos,
  };
  return NextResponse.json(resp);
}
