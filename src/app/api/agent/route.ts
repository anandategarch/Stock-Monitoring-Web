import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { agentStatus, createAgentJob, AgentServiceError } from "@/lib/agent-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/agent — papan status "Python di Laptop" (UI):
 * kehadiran agent (online/offline + nama + engine yang dilaporkan agent),
 * job aktif, dan riwayat job terakhir.
 */
export async function GET() {
  try {
    const status = await agentStatus();
    return NextResponse.json(status);
  } catch (err) {
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Gagal memuat status agent.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

/**
 * POST /api/agent — buat job baru untuk diproses PYTHON DI LAPTOP (UI).
 * Body: { ids: string[] (link Drive tersimpan), periodKey, tanggalH,
 * ambangAcrPct, bundleName? }. Job masuk antrean (QUEUED) — agent laptop
 * menjemputnya lewat polling /api/agent/claim.
 */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  try {
    const job = await createAgentJob(body);
    return NextResponse.json({ job }, { status: 201 });
  } catch (err) {
    if (err instanceof AgentServiceError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Gagal membuat job agent.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
