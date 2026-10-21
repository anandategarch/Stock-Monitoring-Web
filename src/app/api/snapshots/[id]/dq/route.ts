import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import type { DqCode, DqIssueDto, DqSeverity } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/snapshots/[id]/dq — isu kualitas data snapshot terkomit (FR-60/61, INV-6). */
export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const sp = req.nextUrl.searchParams;
  const severity = sp.get("severity") ?? "";
  const code = sp.get("code") ?? "";

  const issues = await db.dQIssue.findMany({
    where: {
      snapshotId: id,
      ...(severity ? { severity } : {}),
      ...(code ? { code } : {}),
    },
    orderBy: [{ createdAt: "desc" }],
  });

  const rows: DqIssueDto[] = issues.map((d) => ({
    id: d.id,
    severity: d.severity as DqSeverity,
    code: d.code as DqCode,
    message: d.message,
    source: d.source,
    sheet: d.sheet,
    rawValue: d.rawValue,
    rowNumber: d.rowNumber,
  }));
  return NextResponse.json({ issues: rows });
}
