import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { cancelAgentJob, getAgentJob, AgentServiceError } from "@/lib/agent-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/agent/jobs/[id] — detail job untuk polling UI (progress live). */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  try {
    const job = await getAgentJob(id);
    return NextResponse.json({ job });
  } catch (err) {
    if (err instanceof AgentServiceError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Gagal memuat job agent.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

/**
 * POST /api/agent/jobs/[id] — batalkan job (UI). QUEUED → langsung CANCELLED;
 * RUNNING → CANCELLED (agent mendengarnya dari respons laporan berikutnya
 * lalu menghentikan pekerjaan); FINALIZING tidak bisa dibatalkan.
 */
export async function POST(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }
  if (body.action !== "cancel") {
    return NextResponse.json({ error: "action wajib 'cancel'." }, { status: 400 });
  }
  try {
    const job = await cancelAgentJob(id);
    return NextResponse.json({ job });
  } catch (err) {
    if (err instanceof AgentServiceError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Gagal membatalkan job.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
