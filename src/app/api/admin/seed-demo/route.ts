import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { commitRun, processRun } from "@/lib/snapshot-service";
import { currentPeriodKeyJakarta, prevPeriodKey } from "@/lib/format";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * POST /api/admin/seed-demo — isi 2 periode demo (bulan lalu + bulan berjalan) via engine
 * demo: proses → komit masing-masing. Dipakai untuk menyiapkan histori awal (tren & komparasi).
 * Menolak bila sudah ada snapshot aktif (data nyata tidak boleh tercampur diam-diam).
 */
export async function POST() {
  const existing = await db.periodSnapshot.findFirst({ where: { state: "ACTIVE" } });
  if (existing) {
    return NextResponse.json(
      { error: `Sudah ada snapshot aktif (periode ${existing.periodKey}). Seed demo hanya untuk database kosong — hapus snapshot lewat Config bila ingin mengulang.` },
      { status: 409 },
    );
  }

  const current = currentPeriodKeyJakarta();
  const periods = [prevPeriodKey(current), current];

  const created: { periodKey: string; snapshotId: string; rowCount: number }[] = [];
  try {
    for (const periodKey of periods) {
      const { runBatchId } = await processRun({
        periodKey,
        tanggalH: 25,
        ambangAcrPct: 80,
        bundleName: `Demo ${periodKey}`,
      });
      const out = await commitRun(runBatchId);
      created.push({ periodKey: out.periodKey, snapshotId: out.snapshotId, rowCount: out.rowCount });
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Seed demo gagal.";
    return NextResponse.json(
      { error: `${message} — periode yang sempat terkomit: ${JSON.stringify(created)}` },
      { status: 502 },
    );
  }

  await db.auditLog.create({
    data: {
      action: "SEED_DEMO",
      entity: "PeriodSnapshot",
      entityId: null,
      detailJson: JSON.stringify(created),
      actor: "analyst",
    },
  });

  return NextResponse.json({ created });
}
