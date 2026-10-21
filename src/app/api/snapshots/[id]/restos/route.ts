import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import type { RestoRef } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/snapshots/[id]/restos — daftar resto unik snapshot (untuk dropdown filter). */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id },
    distinct: ["restoCode"],
    select: { restoCode: true, restoName: true },
    orderBy: { restoCode: "asc" },
  });
  const restos: RestoRef[] = rows.map((r) => ({ restoCode: r.restoCode, restoName: r.restoName }));
  return NextResponse.json({ restos });
}
