import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import type { SelisihInResponse } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * GET /api/snapshots/[id]/selisih-in?mode=bulan_ini (FR-33)
 * IN (Accurate 42.05+32.24+99.01) vs BARANG MASUK (rekap) + Hasil Audit + 🏆 SKOR RESTO.
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const mode = sp.get("mode") ?? "bulan_ini";

  const rows = await db.selisihInResto.findMany({
    where: { snapshotId: id },
    orderBy: { restoCode: "asc" },
  });

  const total = rows.reduce(
    (acc, r) => ({
      inAccurate: acc.inAccurate + r.inAccurate,
      barangMasuk: acc.barangMasuk + r.barangMasuk,
      selisih: acc.selisih + r.selisih,
    }),
    { inAccurate: 0, barangMasuk: 0, selisih: 0 },
  );

  const resp: SelisihInResponse = {
    snapshotId: id,
    mode,
    total,
    rows: rows.map((r) => ({
      restoCode: r.restoCode,
      restoName: r.restoName,
      inAccurate: r.inAccurate,
      barangMasuk: r.barangMasuk,
      selisih: r.selisih,
      hasilAudit: r.hasilAudit === "OK" ? "OK" : "SELISIH",
      skorResto: r.skorResto,
      itemBerselisih: r.itemBerselisih,
      tanggalTerdampak: r.tanggalTerdampak,
    })),
  };
  return NextResponse.json(resp);
}
