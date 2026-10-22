import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { processRun } from "@/lib/snapshot-service";
import { clampString, parseIntInRange, isPeriodKey } from "@/lib/validate";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Serverless: run produksi atas bundle real bisa >10 dtk (audit 48-g-engine;
// timeout klien engine 600 dtk — lambda default 10 dtk akan membunuhnya duluan).
export const maxDuration = 60;

/** POST /api/ingest/process — jalankan engine, simpan pratinjau run (BELUM komit, FR-4). */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }

  const periodKey = body.periodKey;
  if (!isPeriodKey(periodKey)) {
    return NextResponse.json(
      { error: "periodKey wajib format YYYY-MM (contoh: 2026-10)." },
      { status: 422 },
    );
  }

  const settingsRow = await db.setting.findUnique({ where: { key: "tanggalHDefault" } });
  const ambangRow = await db.setting.findUnique({ where: { key: "ambangAcrDefault" } });
  const defaultH = Number(settingsRow?.valueJson ?? "25");
  const defaultAmbang = Number(ambangRow?.valueJson ?? "80");

  const tanggalH = parseIntInRange(body.tanggalH ?? defaultH, 1, 31);
  const ambangAcrPct = parseIntInRange(body.ambangAcrPct ?? defaultAmbang, 1, 200);
  if (tanggalH === null) {
    return NextResponse.json({ error: "tanggalH wajib integer 1..31." }, { status: 422 });
  }
  if (ambangAcrPct === null) {
    return NextResponse.json({ error: "ambangAcrPct wajib integer 1..200." }, { status: 422 });
  }

  try {
    // Task 55: hanya ada jalur engine DEMO sintetis di server (data asli =
    // agent laptop, tab ini). mode/bundleId dari body diabaikan.
    const { runBatchId, result } = await processRun({
      periodKey,
      tanggalH,
      ambangAcrPct,
      bundleName: clampString(body.bundleName, 120),
    });
    return NextResponse.json({
      runBatchId,
      status: result.status,
      engineKind: result.engineKind,
      definitionVersion: result.definitionVersion,
      summary: result.summary,
      durationMs: result.durationMs,
    });
  } catch (err) {
    const isPrisma =
      err instanceof Prisma.PrismaClientKnownRequestError ||
      err instanceof Prisma.PrismaClientValidationError;
    const message = err instanceof Error && !isPrisma ? err.message : "Gagal memproses run.";
    // Samakan pemetaan dengan /commit (audit 48-g-api): salah-input 4xx,
    // bundle hilang 404, sisanya 502.
    const status = message.includes("tidak ditemukan")
      ? 404
      : message.includes("tidak valid") || message.includes("wajib")
        ? 422
        : 502;
    return NextResponse.json({ error: message }, { status });
  }
}
