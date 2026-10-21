import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { commitRun } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Serverless: komit memanggil ulang engine + menulis ~12k baris — beri jatah
// waktu bila engine di-host (audit 48-g-engine; default lambda 10 dtk kurang).
export const maxDuration = 60;

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
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message =
      err instanceof Error && !isPrisma ? err.message : "Gagal mengkomit snapshot.";
    const status = message.includes("tidak ditemukan")
      ? 404
      : message.includes("sudah dikomit") || message.includes("sedang dikomit")
        ? 409
        : 502;
    return NextResponse.json({ error: message }, { status });
  }
}
