import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { previousActiveSnapshot } from "@/lib/snapshot-service";
import type { NominalResponse, NominalRestoRow, TanpaHargaRow } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * GET /api/snapshots/[id]/nominal (FR-34)
 * Σ nominal per resto + TOTAL + Biaya Packaging (kategori Packaging) + % naik-turun
 * DARI SNAPSHOT periode lalu (bukan file eksternal) + anak-daftar Tanpa Harga global.
 */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id },
    select: {
      restoCode: true, restoName: true, itemName: true, satuan: true, kategori: true,
      nominal: true, qtyDeviasi: true, hargaEfektif: true, konversiOk: true,
    },
  });

  const perResto = new Map<string, { restoName: string; nominal: number; deviasiQty: number }>();
  let packagingNominal = 0;
  let packagingDeviasiQty = 0;
  const tanpaHargaMap = new Map<string, TanpaHargaRow>();

  for (const r of rows) {
    let entry = perResto.get(r.restoCode);
    if (!entry) {
      entry = { restoName: r.restoName, nominal: 0, deviasiQty: 0 };
      perResto.set(r.restoCode, entry);
    }
    if (r.nominal !== null) entry.nominal += r.nominal;
    if (r.qtyDeviasi !== null) entry.deviasiQty += r.qtyDeviasi;

    // Biaya Packaging — kategori mengandung kata PACKAGING (word-boundary,
    // mirror klasifikasi desktop komparasi v3.9.64: 'Biaya Packaging - RESTO'
    // / '01. COST - PACKAGING V.2' cocok; 'REPACKAGING' tidak).
    if (/\bPACKAGING\b/i.test(r.kategori)) {
      if (r.nominal !== null) packagingNominal += r.nominal;
      if (r.qtyDeviasi !== null) packagingDeviasiQty += r.qtyDeviasi;
    }

    const hargaMissing = !r.konversiOk || r.hargaEfektif === null;
    const devSignificant = r.qtyDeviasi !== null && r.qtyDeviasi !== 0;
    if (hargaMissing && devSignificant) {
      const key = `${r.itemName}|${r.satuan}`;
      const existing = tanpaHargaMap.get(key);
      const alasan = !r.konversiOk
        ? "Konversi satuan rekap↔41.09 gagal — penanda * (INV-3)"
        : "Harga 41.09 tidak tersedia untuk barang ini";
      if (!existing) {
        tanpaHargaMap.set(key, {
          itemName: r.itemName,
          satuan: r.satuan,
          kategori: r.kategori,
          alasan,
          qtyDeviasi: r.qtyDeviasi ?? 0,
        });
      } else {
        existing.qtyDeviasi += r.qtyDeviasi ?? 0;
      }
    }
  }

  // % naik-turun vs snapshot periode lalu (DARI DB — menutup alur file eksternal)
  const prev = await previousActiveSnapshot(snapshot.periodKey);
  let prevByResto = new Map<string, number>();
  if (prev) {
    const prevRows = await db.snapshotRow.findMany({
      where: { snapshotId: prev.id },
      select: { restoCode: true, nominal: true },
    });
    prevByResto = new Map<string, number>();
    for (const r of prevRows) {
      prevByResto.set(r.restoCode, (prevByResto.get(r.restoCode) ?? 0) + (r.nominal ?? 0));
    }
  }

  const rowList: NominalRestoRow[] = [...perResto.entries()]
    .map(([restoCode, v]) => {
      const prevNom = prevByResto.get(restoCode);
      const deltaPct =
        prev !== null && prevNom !== undefined && prevNom !== 0
          ? ((v.nominal - prevNom) / Math.abs(prevNom)) * 100
          : null;
      return {
        restoCode,
        restoName: v.restoName,
        nominal: v.nominal,
        deviasiQty: v.deviasiQty,
        deltaPct,
      };
    })
    .sort((a, b) => b.nominal - a.nominal);

  const totalNominal = rowList.reduce((s, r) => s + r.nominal, 0);
  const totalDeviasiQty = rowList.reduce((s, r) => s + r.deviasiQty, 0);
  const prevTotal = prev ? [...prevByResto.values()].reduce((s, v) => s + v, 0) : 0;
  const totalDeltaPct =
    prev && prevTotal !== 0 ? ((totalNominal - prevTotal) / Math.abs(prevTotal)) * 100 : null;

  const resp: NominalResponse = {
    snapshotId: id,
    periodKey: snapshot.periodKey,
    rows: rowList,
    total: { nominal: totalNominal, deviasiQty: totalDeviasiQty, deltaPct: totalDeltaPct },
    com: { packagingNominal, packagingDeviasiQty },
    tanpaHarga: [...tanpaHargaMap.values()].sort((a, b) => Math.abs(b.qtyDeviasi) - Math.abs(a.qtyDeviasi)),
  };
  return NextResponse.json(resp);
}
