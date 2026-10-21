import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { METRIC_KEYS, type MetricKey, type PivotResponse, type PivotRow } from "@/lib/types";
import { parseJsonSafe } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * GET /api/snapshots/[id]/pivot — matriks pivot 10 metrik JENIS (FR-31).
 * mode=resto  : baris = barang (satu resto), kolom = hari (default 26..akhir — paritas desktop)
 * mode=tanggal: baris = barang, kolom = resto (snapshot per hari terpilih)
 * INV-1: sel null ditampilkan "—" oleh UI — TIDAK dinolkan di sini.
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const mode = sp.get("mode") === "tanggal" ? "tanggal" : "resto";
  const metricParam = sp.get("metric") ?? "qtyDeviasi";
  const metric: MetricKey = METRIC_KEYS.includes(metricParam as MetricKey)
    ? (metricParam as MetricKey)
    : "qtyDeviasi";
  const defaultParams = parseJsonSafe(snapshot.paramsJson, { tanggalH: 25, ambangAcrPct: 80 });
  const dayCount = snapshot.dayCount;

  const hideEmpty = sp.get("hideEmpty") !== "0";
  const from = Math.min(Math.max(Number(sp.get("from") ?? 26) || 26, 1), dayCount);
  const to = Math.min(Math.max(Number(sp.get("to") ?? dayCount) || dayCount, 1), dayCount);
  const dayParam = Math.min(Math.max(Number(sp.get("day") ?? defaultParams.tanggalH) || defaultParams.tanggalH, 1), dayCount);

  if (mode === "resto") {
    const resto = sp.get("resto") ?? "";
    if (!resto) {
      return NextResponse.json({ error: "Parameter resto wajib untuk mode=resto." }, { status: 422 });
    }
    const rows = await db.snapshotRow.findMany({
      where: { snapshotId: id, restoCode: resto, day: { gte: from, lte: to } },
      orderBy: [{ itemName: "asc" }, { day: "asc" }],
      select: { itemName: true, satuan: true, kategori: true, isGR: true, day: true, [metric]: true },
    });
    const map = new Map<string, PivotRow>();
    for (const r of rows) {
      const key = `${r.itemName}|${r.satuan}`;
      let entry = map.get(key);
      if (!entry) {
        entry = { itemName: r.itemName, satuan: r.satuan, kategori: r.kategori, isGR: r.isGR, values: {} };
        map.set(key, entry);
      }
      entry.values[`d${r.day}`] = (r[metric] as number | null) ?? null;
    }
    const all = [...map.values()];
    const visible = hideEmpty
      ? all.filter((row) => Object.values(row.values).some((v) => v !== null && v !== 0))
      : all;
    const resp: PivotResponse = {
      mode,
      metric,
      columns: Array.from({ length: to - from + 1 }, (_, i) => ({
        key: `d${from + i}`,
        label: String(from + i),
      })),
      rows: visible,
      from,
      to,
      dayCount,
      totalRowsBeforeHide: all.length,
      hiddenEmptyRows: all.length - visible.length,
    };
    return NextResponse.json(resp);
  }

  // mode=tanggal
  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id, day: dayParam },
    orderBy: [{ itemName: "asc" }, { restoCode: "asc" }],
    select: { itemName: true, satuan: true, kategori: true, isGR: true, restoCode: true, restoName: true, [metric]: true },
  });
  const restoCols = new Map<string, string>();
  const map = new Map<string, PivotRow>();
  for (const r of rows) {
    restoCols.set(r.restoCode, r.restoName);
    const key = `${r.itemName}|${r.satuan}`;
    let entry = map.get(key);
    if (!entry) {
      entry = { itemName: r.itemName, satuan: r.satuan, kategori: r.kategori, isGR: r.isGR, values: {} };
      map.set(key, entry);
    }
    entry.values[r.restoCode] = (r[metric] as number | null) ?? null;
  }
  const all = [...map.values()];
  const visible = hideEmpty
    ? all.filter((row) => Object.values(row.values).some((v) => v !== null && v !== 0))
    : all;
  const columns = [...restoCols.keys()].sort().map((code) => ({ key: code, label: code }));
  const resp: PivotResponse = {
    mode,
    metric,
    columns,
    rows: visible,
    from: dayParam,
    to: dayParam,
    dayCount,
    totalRowsBeforeHide: all.length,
    hiddenEmptyRows: all.length - visible.length,
  };
  return NextResponse.json(resp);
}
