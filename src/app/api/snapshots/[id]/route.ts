import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { toSnapshotSummary } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/snapshots/[id] — detail satu snapshot. */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const row = await db.periodSnapshot.findUnique({ where: { id } });
  if (!row) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });
  return NextResponse.json({ snapshot: toSnapshotSummary(row) });
}

/** DELETE /api/snapshots/[id] — hapus periode (admin; tercatat AuditLog; DQ ikut dilepas). */
export async function DELETE(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const row = await db.periodSnapshot.findUnique({ where: { id } });
  if (!row) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });
  // BUILDING = komit sedang berjalan (audit 48-g-data): menghapusnya membuat
  // komit tersebut error — tolak, tunggu komit selesai atau gagal sendiri.
  if (row.state === "BUILDING") {
    return NextResponse.json(
      { error: "Snapshot sedang dibangun (komit berjalan) — tunggu sebentar lalu hapus lagi." },
      { status: 409 },
    );
  }
  const periodKey = row.periodKey;
  await db.periodSnapshot.delete({ where: { id } });
  await db.auditLog.create({
    data: {
      action: "SNAPSHOT_DELETE",
      entity: "PeriodSnapshot",
      entityId: id,
      detailJson: JSON.stringify({ periodKey }),
      actor: "analyst",
    },
  });
  return NextResponse.json({ ok: true, id, periodKey });
}
