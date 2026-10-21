import { NextRequest, NextResponse } from "next/server";
import { commitRun } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** POST /api/ingest/commit — komit pratinjau run menjadi snapshot permanen (FR-4/FR-24). */
export async function POST(req: NextRequest) {
  let body: { runBatchId?: string };
  try {
    body = (await req.json()) as { runBatchId?: string };
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const runBatchId = typeof body.runBatchId === "string" ? body.runBatchId : "";
  if (!runBatchId) {
    return NextResponse.json({ error: "runBatchId wajib diisi." }, { status: 422 });
  }
  try {
    const out = await commitRun(runBatchId);
    return NextResponse.json(out);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Gagal mengkomit snapshot.";
    const status = message.includes("tidak ditemukan") ? 404 : message.includes("sudah dikomit") ? 409 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}
