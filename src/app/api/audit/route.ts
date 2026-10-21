import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import type { AuditLogDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/audit?limit=50 — jejak audit (NFR-4). */
export async function GET(req: NextRequest) {
  const limitRaw = Number(req.nextUrl.searchParams.get("limit") ?? 50);
  const limit = Number.isFinite(limitRaw) ? Math.min(Math.max(limitRaw, 1), 200) : 50;
  const rows = await db.auditLog.findMany({ orderBy: { createdAt: "desc" }, take: limit });
  const logs: AuditLogDto[] = rows.map((r) => ({
    id: r.id, action: r.action, entity: r.entity, entityId: r.entityId,
    detailJson: r.detailJson, actor: r.actor, createdAt: r.createdAt.toISOString(),
  }));
  return NextResponse.json({ logs });
}
