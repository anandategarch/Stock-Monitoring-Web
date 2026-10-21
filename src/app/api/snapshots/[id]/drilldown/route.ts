import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { parseJsonSafe } from "@/lib/snapshot-service";
import type {
  AuditNote, CekLabel, DrilldownDay, DrilldownResponse,
} from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * GET /api/snapshots/[id]/drilldown?resto=CODE&item=NAME — panel rincian baris sumber
 * (INV-7): seluruh seri 10 metrik per hari + ringkasan bulanan + jejak harga/konversi.
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const resto = sp.get("resto") ?? "";
  const item = sp.get("item") ?? "";
  if (!resto || !item) {
    return NextResponse.json({ error: "Parameter resto dan item wajib." }, { status: 422 });
  }

  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id, restoCode: resto, itemName: item },
    orderBy: { day: "asc" },
  });
  if (rows.length === 0) {
    return NextResponse.json({ error: "Baris tidak ditemukan untuk pasangan resto×barang ini." }, { status: 404 });
  }

  const sum = (sel: (r: (typeof rows)[number]) => number | null) => {
    let s = 0;
    let has = false;
    for (const r of rows) {
      const v = sel(r);
      if (v !== null) {
        s += v;
        has = true;
      }
    }
    return has ? s : 0;
  };

  const first = rows[0];
  const days: DrilldownDay[] = rows.map((r) => ({
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
    nominal: r.nominal,
    cek: parseJsonSafe<CekLabel[]>(r.cekJson, []),
    auditNote: (r.auditNote as AuditNote | null) ?? null,
  }));

  const resp: DrilldownResponse = {
    resto: { restoCode: first.restoCode, restoName: first.restoName },
    item: {
      itemName: first.itemName,
      satuan: first.satuan,
      kategori: first.kategori,
      isGR: first.isGR,
      harga: first.hargaEfektif,
      konversiOk: rows.every((r) => r.konversiOk),
    },
    days,
    monthly: {
      deviasiBulan: sum((r) => r.qtyDeviasi),
      nominalBulan: sum((r) => r.nominal),
      acrTotal: sum((r) => r.qtyACR),
      inTotal: sum((r) => r.qtyIN),
      bmTotal: sum((r) => r.qtyBarangMasuk),
      sinTotal: sum((r) => r.qtySelisihIN),
      bkTotal: sum((r) => r.qtyBarangKeluar),
      comTotal: sum((r) => r.qtyCOM),
      soTotal: sum((r) => r.qtySO),
    },
  };
  return NextResponse.json(resp);
}
