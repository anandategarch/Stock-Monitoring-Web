import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { commitStep } from "@/lib/snapshot-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Task 54 — komit BERTAHAP: tiap panggilan hanya bekerja ±30 dtk (anggaran di
// commitStep) lalu menyimpan tahap+cursor di snapshot.paramsJson; CLIENT
// memanggil endpoint ini berulang sampai done. Satu panggilan tidak pernah
// mendekati batas 60 dtk serverless lagi — run 88rb baris pun komit mulus.
export const maxDuration = 60;

/**
 * POST /api/ingest/commit — satu LANGKAH komit (Task 54). Respon:
 *  - { done:false, phase, written, total } → client panggil lagi (lanjut dari cursor).
 *  - { done:true, snapshotId, … }         → snapshot aktif, komit selesai.
 * Body opsional `budgetMs` (1.000–30.000, default 30.000) memperkecil langkah —
 * hanya tuas uji/kehati-hatian (langkah kecil = lebih banyak panggilan, hasil
 * sama). Kegagalan di tengah TIDAK menghapus kemajuan — tekan Komit ulang
 * untuk melanjutkan dari cursor (resumable), atau hapus BUILDING di tab
 * Konfigurasi.
 */
export async function POST(req: NextRequest) {
  let body: { runBatchId?: string; budgetMs?: number };
  try {
    body = (await req.json()) as { runBatchId?: string; budgetMs?: number };
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const runBatchId = typeof body.runBatchId === "string" ? body.runBatchId : "";
  if (!runBatchId) {
    return NextResponse.json({ error: "runBatchId wajib diisi." }, { status: 422 });
  }
  const budgetMs =
    typeof body.budgetMs === "number" && Number.isFinite(body.budgetMs)
      ? Math.min(30_000, Math.max(1_000, Math.floor(body.budgetMs)))
      : 30_000;
  try {
    const out = await commitStep(runBatchId, budgetMs);
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
