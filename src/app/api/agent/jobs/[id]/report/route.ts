import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import {
  reportProgress, reportChunk, reportComplete, reportFail, AgentServiceError,
} from "@/lib/agent-service";
import { agentTokenConfigured, agentTokenMatches } from "@/lib/agent-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// complete = rakit hasil (~MB gzip) + tulis RunBatch/DQ/AgentResult — beri
// ruang; proses berat justru di laptop, di sini hanya penulisan DB.
export const maxDuration = 60;

type Ctx = { params: Promise<{ id: string }> };

/**
 * POST /api/agent/jobs/[id]/report — SATU endpoint laporan agent (token):
 *  - { action: "progress", progress: 0..100, message } → heartbeat + kemajuan
 *  - { action: "chunk", seq, data } → potongan hasil base64(gzip) berurutan
 *  - { action: "complete" } → server merakit, memvalidasi kontrak v1, membuat
 *    run pratinjau dari hasil laptop, lalu COMPLETED
 *  - { action: "fail", error } → FAILED jujur
 * Respons selalu menyertakan { cancelled } supaya agent bisa berhenti begitu
 * user membatalkan.
 */
export async function POST(req: NextRequest, ctx: Ctx) {
  if (!agentTokenConfigured()) {
    return NextResponse.json(
      { error: "Server belum mengatur AGENT_TOKEN — endpoint agent dinonaktifkan." },
      { status: 503 },
    );
  }
  const token = req.headers.get("x-agent-token");
  if (!agentTokenMatches(token)) {
    return NextResponse.json({ error: "Token agent tidak valid (header x-agent-token)." }, { status: 401 });
  }

  const { id } = await ctx.params;
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const action = body.action;

  try {
    if (action === "progress") {
      const out = await reportProgress(id, body);
      return NextResponse.json(out);
    }
    if (action === "chunk") {
      const out = await reportChunk(id, body);
      return NextResponse.json(out);
    }
    if (action === "complete") {
      const out = await reportComplete(id);
      return NextResponse.json(out);
    }
    if (action === "fail") {
      const out = await reportFail(id, body.error);
      return NextResponse.json(out);
    }
    return NextResponse.json(
      { error: "action wajib 'progress' | 'chunk' | 'complete' | 'fail'." },
      { status: 400 },
    );
  } catch (err) {
    if (err instanceof AgentServiceError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = !isPrisma && err instanceof Error ? err.message : "Laporan agent gagal diproses.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
