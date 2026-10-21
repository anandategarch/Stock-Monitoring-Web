import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { toSnapshotSummary } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/snapshots — daftar snapshot periode (aktif & superseded, FR-82). */
export async function GET() {
  const rows = await db.periodSnapshot.findMany({
    orderBy: [{ periodKey: "desc" }, { committedAt: "desc" }],
  });
  return NextResponse.json({ snapshots: rows.map(toSnapshotSummary) });
}
