import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import type { PoHeaderDto, PoResponse } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/**
 * GET /api/snapshots/[id]/po?q=&status=&cabang= (FR-36)
 * Rincian PO + item + status pesanan (32.43) + anotasi ↳ Status. Filter persist di UI.
 */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const q = (sp.get("q") ?? "").trim().toLowerCase();
  const status = sp.get("status") ?? "";
  const cabang = sp.get("cabang") ?? "";

  const headers = await db.poHeader.findMany({
    where: {
      snapshotId: id,
      ...(cabang ? { cabang } : {}),
      ...(status ? { statusPesanan: status } : {}),
    },
    include: { items: { orderBy: { itemName: "asc" } } },
    orderBy: [{ cabang: "asc" }, { poNumber: "asc" }],
  });

  const restosSet = new Map<string, string>();
  const statusSet = new Set<string>();
  const allHeaders = await db.poHeader.findMany({
    where: { snapshotId: id },
    select: { cabang: true, restoName: true, statusPesanan: true },
  });
  for (const h of allHeaders) {
    restosSet.set(h.cabang, h.restoName);
    statusSet.add(h.statusPesanan);
  }

  const filtered = q
    ? headers.filter(
        (h) =>
          h.poNumber.toLowerCase().includes(q) ||
          (h.supplier ?? "").toLowerCase().includes(q) ||
          h.items.some((it) => it.itemName.toLowerCase().includes(q)),
      )
    : headers;

  const rows: PoHeaderDto[] = filtered.map((h) => ({
    id: h.id,
    cabang: h.cabang,
    restoName: h.restoName,
    poNumber: h.poNumber,
    tanggal: h.tanggal,
    supplier: h.supplier,
    itemCount: h.itemCount,
    status: h.status,
    statusPesanan: h.statusPesanan,
    annotasi: h.annotasi,
    items: h.items.map((it) => ({
      id: it.id,
      itemName: it.itemName,
      qty: it.qty,
      satuan: it.satuan,
      status: it.status,
      diterimaSebagian: it.diterimaSebagian,
    })),
  }));

  const restos = [...restosSet.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([restoCode, restoName]) => ({ restoCode, restoName }));

  const resp: PoResponse = {
    rows,
    restos,
    statusOptions: [...statusSet].sort(),
  };
  return NextResponse.json(resp);
}
