import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { parseJsonSafe, previousActiveSnapshot } from "@/lib/snapshot-service";
import { prevPeriodKey } from "@/lib/format";
import type {
  LaporanAnomaliRow, LaporanKomparasiRow, LaporanResponse,
} from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

interface PairNominal {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  nominal: number;
  qtyDeviasi: number;
  comTotal: number;
  bmTotal: number;
  inTotal: number;
}

async function aggregatePairs(snapshotId: string): Promise<Map<string, PairNominal>> {
  const rows = await db.snapshotRow.findMany({
    where: { snapshotId },
    select: {
      restoCode: true, restoName: true, itemName: true, satuan: true, kategori: true,
      nominal: true, qtyDeviasi: true, qtyCOM: true, qtyBarangMasuk: true, qtyIN: true,
    },
  });
  const map = new Map<string, PairNominal>();
  for (const r of rows) {
    const key = `${r.restoCode}|${r.itemName}|${r.satuan}`;
    let p = map.get(key);
    if (!p) {
      p = {
        restoCode: r.restoCode, restoName: r.restoName, itemName: r.itemName, satuan: r.satuan,
        kategori: r.kategori, nominal: 0, qtyDeviasi: 0, comTotal: 0, bmTotal: 0, inTotal: 0,
      };
      map.set(key, p);
    }
    if (r.nominal !== null) p.nominal += r.nominal;
    if (r.qtyDeviasi !== null) p.qtyDeviasi += r.qtyDeviasi;
    if (r.qtyCOM !== null) p.comTotal += r.qtyCOM;
    if (r.qtyBarangMasuk !== null) p.bmTotal += r.qtyBarangMasuk;
    if (r.qtyIN !== null) p.inTotal += r.qtyIN;
  }
  return map;
}

/**
 * GET /api/snapshots/[id]/laporan?mode=komparasi|anomali_com|nominal_h&h=25 (FR-35)
 * ⚖ Komparasi: kini vs SNAPSHOT periode lalu (utama; file eksternal = histori pra-web, P2).
 * 🚨 Anomali COM: pemakaian tanpa/lebih besar dari barang masuk.
 * 💰 Nominal (H): Σ nominal per resto hingga cut-off H.
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const modeParam = sp.get("mode") ?? "komparasi";
  const mode: LaporanResponse["mode"] =
    modeParam === "anomali_com" || modeParam === "nominal_h" ? modeParam : "komparasi";
  const params = parseJsonSafe(snapshot.paramsJson, { tanggalH: 25, ambangAcrPct: 80 });
  const h = Math.min(Math.max(Number(sp.get("h") ?? params.tanggalH) || params.tanggalH, 1), snapshot.dayCount);

  const current = await aggregatePairs(id);

  // ---- 💰 Nominal (H): per resto Σ nominal hari ≤ H
  if (mode === "nominal_h") {
    const rows = await db.snapshotRow.findMany({
      where: { snapshotId: id, day: { lte: h } },
      select: { restoCode: true, restoName: true, nominal: true, qtyDeviasi: true },
    });
    const perResto = new Map<string, { restoName: string; nominalH: number; nominalBulan: number; deviasiH: number }>();
    for (const r of rows) {
      let e = perResto.get(r.restoCode);
      if (!e) {
        e = { restoName: r.restoName, nominalH: 0, nominalBulan: 0, deviasiH: 0 };
        perResto.set(r.restoCode, e);
      }
      if (r.nominal !== null) e.nominalH += r.nominal;
      if (r.qtyDeviasi !== null) e.deviasiH += r.qtyDeviasi;
    }
    // nominal bulan penuh untuk kolom pembanding
    const monthRows = await db.snapshotRow.findMany({
      where: { snapshotId: id },
      select: { restoCode: true, nominal: true },
    });
    for (const r of monthRows) {
      const e = perResto.get(r.restoCode);
      if (e && r.nominal !== null) e.nominalBulan += r.nominal;
    }
    const list = [...perResto.entries()]
      .map(([restoCode, v]) => ({
        restoCode, restoName: v.restoName, nominalH: v.nominalH, nominalBulan: v.nominalBulan, deviasiH: v.deviasiH,
      }))
      .sort((a, b) => b.nominalH - a.nominalH);
    const resp: LaporanResponse = {
      mode, h, hasPrev: false, prevPeriodKey: null,
      komparasi: null, anomali: null,
      nominalH: { rows: list, total: { nominalH: list.reduce((s, r) => s + r.nominalH, 0) } },
    };
    return NextResponse.json(resp);
  }

  // ---- 🚨 Anomali COM (aturan demo — didokumentasikan; produksi mengikuti logika desktop):
  // pemakaian COM < 8% dari BARANG MASUK (BM ≥ 200) → indikasi pemakaian tidak tercatat.
  if (mode === "anomali_com") {
    const rows: LaporanAnomaliRow[] = [...current.values()]
      .filter((p) => p.bmTotal >= 200 && p.comTotal < p.bmTotal * 0.08)
      .map((p) => ({
        restoCode: p.restoCode, restoName: p.restoName, itemName: p.itemName, satuan: p.satuan,
        kategori: p.kategori, comTotal: p.comTotal, bmTotal: p.bmTotal, inTotal: p.inTotal,
        selisih: p.comTotal - p.bmTotal,
        nominal: p.nominal !== 0 ? p.nominal : null,
      }))
      .sort((a, b) => a.comTotal - b.comTotal)
      .slice(0, 150);
    const resp: LaporanResponse = {
      mode, h, hasPrev: false, prevPeriodKey: null,
      komparasi: null, anomali: { rows }, nominalH: null,
    };
    return NextResponse.json(resp);
  }

  // ---- ⚖ Komparasi vs SNAPSHOT periode lalu (DARI DB — FR-35)
  const prev = await previousActiveSnapshot(snapshot.periodKey);
  const prevPairs = prev ? await aggregatePairs(prev.id) : new Map<string, PairNominal>();

  const komparasiRows: LaporanKomparasiRow[] = [...current.values()]
    .map((p) => {
      const prevP = prevPairs.get(`${p.restoCode}|${p.itemName}|${p.satuan}`);
      const nominalKini = p.nominal;
      const nominalLalu = prevP ? prevP.nominal : 0;
      const delta = nominalKini - nominalLalu;
      const deltaPct = nominalLalu !== 0 ? (delta / Math.abs(nominalLalu)) * 100 : null;
      const arah: LaporanKomparasiRow["arah"] =
        delta > 0 ? "NAIK" : delta < 0 ? "TURUN" : "TETAP";
      return {
        restoCode: p.restoCode, restoName: p.restoName, itemName: p.itemName, satuan: p.satuan,
        kategori: p.kategori, nominalKini, nominalLalu, delta, deltaPct, arah,
        qtyDeviasiKini: p.qtyDeviasi, qtyDeviasiLalu: prevP ? prevP.qtyDeviasi : 0,
      };
    })
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 200);

  const totalKini = [...current.values()].reduce((s, p) => s + p.nominal, 0);
  const totalLalu = prevPairs.size > 0 ? [...prevPairs.values()].reduce((s, p) => s + p.nominal, 0) : 0;
  const totalDeltaPct = prevPairs.size > 0 && totalLalu !== 0
    ? ((totalKini - totalLalu) / Math.abs(totalLalu)) * 100
    : null;

  const resp: LaporanResponse = {
    mode, h,
    hasPrev: prevPairs.size > 0,
    prevPeriodKey: prev ? prevPeriodKey(snapshot.periodKey) : null,
    komparasi: { rows: komparasiRows, totalKini, totalLalu, deltaPct: totalDeltaPct },
    anomali: null,
    nominalH: null,
  };
  return NextResponse.json(resp);
}
