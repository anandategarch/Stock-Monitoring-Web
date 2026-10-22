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
  // BUILDING = komit sedang menulis baris. Menghapusnya saat komit BENAR-BENAR
  // berjalan membuat komit itu error — tolak. Tapi fungsi serverless maks ±60
  // dtk: BUILDING yang berumur >15 menit pasti komit MATI DI TENGAH (terbukti
  // produksi: snapshot 88rb baris BUILDING yatim, Task 54) — biarkan dihapus.
  if (row.state === "BUILDING") {
    const ageMs = Date.now() - row.committedAt.getTime();
    if (ageMs < 15 * 60 * 1000) {
      return NextResponse.json(
        {
          error:
            "Snapshot ini sedang dibangun (komit berjalan, maks ±60 dtk) — tunggu sebentar. " +
            "Setelah 15 menit ia bisa dihapus: komit yang mati di tengah tidak pernah menyentuh data lama (NFR-3).",
        },
        { status: 409 },
      );
    }
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
