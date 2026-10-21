import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { claimAgentJob, AgentServiceError } from "@/lib/agent-service";
import { agentTokenConfigured, agentTokenMatches } from "@/lib/agent-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * POST /api/agent/claim — AGENT LAPTOP menjemput job berikutnya (polling).
 * Auth: header X-Agent-Token (env AGENT_TOKEN; di Vercel wajib diatur —
 * tanpa itu endpoint jujur menolak). Body: { agentName, engine? } — engine
 * = laporan /health engine FastAPI lokal (dipajang di UI sebagai info).
 * Respons: { job } (status RUNNING, targets Drive, parameter run) atau
 * { job: null } bila antrean kosong. Setiap poll juga meng-update
 * kehadiran agent (UI menampilkan "online").
 */
export async function POST(req: NextRequest) {
  if (!agentTokenConfigured()) {
    return NextResponse.json(
      { error: "Server belum mengatur AGENT_TOKEN — endpoint agent dinonaktifkan. Set env AGENT_TOKEN lalu redeploy." },
      { status: 503 },
    );
  }
  const token = req.headers.get("x-agent-token");
  if (!agentTokenMatches(token)) {
    return NextResponse.json({ error: "Token agent tidak valid (header x-agent-token)." }, { status: 401 });
  }

  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }
  const agentName = typeof body.agentName === "string" ? body.agentName : "agent-laptop";
  const engine =
    body.engine && typeof body.engine === "object" && !Array.isArray(body.engine)
      ? (body.engine as Record<string, unknown>)
      : undefined;

  try {
    const job = await claimAgentJob(agentName, engine);
    return NextResponse.json({ job });
  } catch (err) {
    if (err instanceof AgentServiceError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Gagal mengambil job.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
