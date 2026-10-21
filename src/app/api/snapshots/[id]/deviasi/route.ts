import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { stableFingerprint } from "@/lib/fingerprint";
import { parseJsonSafe } from "@/lib/snapshot-service";
import type {
  AuditNote, CekLabel, DeviasiResponse, DeviasiRow,
} from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

interface PairAgg {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  devSumH: { sum: number; has: boolean };
  devSumAll: { sum: number; has: boolean };
  acrTotal: number;
  nomSumH: { sum: number; has: boolean };
  nomSumAll: { sum: number; has: boolean };
  harga: number | null;
  konversiOk: boolean;
  cek: Set<CekLabel>;
  auditNotes: Set<AuditNote>;
}

/**
 * GET /api/snapshots/[id]/deviasi?group=GR|PCS&resto=&h=25&ambang=80 (FR-30)
 * Wide-matrix per resto×barang: deviasi H, deviasi bulan, ACR total, nominal, label CEK
 * (TANPA "ACR to BOM" — dihitung ulang live di UI saat ambang berubah), rank nominal
 * per-baris (method min; 0/null → kosong — kontrak §61/62 desktop).
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const group = sp.get("group") === "PCS" ? "PCS" : "GR";
  const resto = sp.get("resto") ?? undefined;
  const params = parseJsonSafe(snapshot.paramsJson, { tanggalH: 25, ambangAcrPct: 80 });
  const h = Math.min(Math.max(Number(sp.get("h") ?? params.tanggalH) || params.tanggalH, 1), snapshot.dayCount);
  const ambang = Math.min(Math.max(Number(sp.get("ambang") ?? params.ambangAcrPct) || params.ambangAcrPct, 1), 200);

  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id, isGR: group === "GR", ...(resto ? { restoCode: resto } : {}) },
    orderBy: [{ restoCode: "asc" }, { itemName: "asc" }, { day: "asc" }],
  });

  const pairs = new Map<string, PairAgg>();
  for (const r of rows) {
    const key = `${r.restoCode}|${r.itemName}|${r.satuan}`;
    let p = pairs.get(key);
    if (!p) {
      p = {
        restoCode: r.restoCode, restoName: r.restoName, itemName: r.itemName, satuan: r.satuan, kategori: r.kategori,
        devSumH: { sum: 0, has: false }, devSumAll: { sum: 0, has: false },
        acrTotal: 0, nomSumH: { sum: 0, has: false }, nomSumAll: { sum: 0, has: false },
        harga: null, konversiOk: true, cek: new Set(), auditNotes: new Set(),
      };
      pairs.set(key, p);
    }
    if (r.qtyDeviasi !== null) {
      p.devSumAll.sum += r.qtyDeviasi;
      p.devSumAll.has = true;
      if (r.day <= h) {
        p.devSumH.sum += r.qtyDeviasi;
        p.devSumH.has = true;
      }
    }
    if (r.qtyACR !== null) p.acrTotal += r.qtyACR;
    if (r.nominal !== null) {
      p.nomSumAll.sum += r.nominal;
      p.nomSumAll.has = true;
      if (r.day <= h) {
        p.nomSumH.sum += r.nominal;
        p.nomSumH.has = true;
      }
    }
    if (r.hargaEfektif !== null && p.harga === null) p.harga = r.hargaEfektif;
    if (!r.konversiOk) p.konversiOk = false;
    if (r.auditNote) p.auditNotes.add(r.auditNote as AuditNote);
    for (const c of parseJsonSafe<CekLabel[]>(r.cekJson, [])) {
      if (c !== "ACR to BOM") p.cek.add(c); // re-komputasi live di UI (FR-30)
    }
  }

  // Rank nominal per-baris (method min) dalam masing-masing resto — kontrak §61/62
  const byResto = new Map<string, PairAgg[]>();
  for (const p of pairs.values()) {
    const arr = byResto.get(p.restoCode) ?? [];
    arr.push(p);
    byResto.set(p.restoCode, arr);
  }
  const rankMap = new Map<string, number | null>();
  for (const [, arr] of byResto) {
    const absVals = arr
      .map((p) => (p.nomSumAll.has && p.nomSumAll.sum !== 0 ? Math.abs(p.nomSumAll.sum) : null))
      .filter((v): v is number => v !== null)
      .sort((a, b) => b - a);
    for (const p of arr) {
      const key = `${p.restoCode}|${p.itemName}|${p.satuan}`;
      if (!p.nomSumAll.has || p.nomSumAll.sum === 0) {
        rankMap.set(key, null);
        continue;
      }
      const abs = Math.abs(p.nomSumAll.sum);
      let rank = 1;
      for (const v of absVals) {
        if (v > abs) rank++;
      }
      rankMap.set(key, rank);
    }
  }

  const out: DeviasiRow[] = [...pairs.values()].map((p) => {
    const key = `${p.restoCode}|${p.itemName}|${p.satuan}`;
    return {
      fingerprint: stableFingerprint(p.restoCode, p.itemName, p.satuan, p.kategori),
      restoCode: p.restoCode,
      restoName: p.restoName,
      itemName: p.itemName,
      satuan: p.satuan,
      kategori: p.kategori,
      deviasiH: p.devSumH.has ? p.devSumH.sum : null,
      deviasiBulan: p.devSumAll.has ? p.devSumAll.sum : null,
      acrTotal: p.acrTotal,
      nominalH: p.nomSumH.has ? p.nomSumH.sum : null,
      nominalBulan: p.nomSumAll.has ? p.nomSumAll.sum : null,
      harga: p.harga,
      konversiOk: p.konversiOk,
      cek: [...p.cek],
      auditNotes: [...p.auditNotes],
      rankNominal: rankMap.get(key) ?? null,
    };
  });

  const resp: DeviasiResponse = {
    snapshotId: id,
    periodKey: snapshot.periodKey,
    group,
    h,
    ambang,
    totalRows: out.length,
    rows: out,
  };
  return NextResponse.json(resp);
}
