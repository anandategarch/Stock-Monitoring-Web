import { NextRequest, NextResponse } from "next/server";
import { processRun } from "@/lib/snapshot-service";
import { clampString, parseIntInRange, isPeriodKey } from "@/lib/validate";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

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
    // Mode engine (FR-10 §5): "bundle" → engine PRODUKSI FastAPI (pipeline asli
    // v3.9.71) atas bundle terunggah; default "demo" → engine sintetis :3030.
    const mode = body.mode === "bundle" ? "bundle" : "demo";
    const bundleId = typeof body.bundleId === "string" && body.bundleId ? body.bundleId : null;
    if (mode === "bundle" && !bundleId) {
      return NextResponse.json(
        { error: "Mode bundle membutuhkan bundleId — unggah ZIP dulu di /api/ingest/upload." },
        { status: 422 },
      );
    }
    if (mode === "demo" && bundleId) {
      return NextResponse.json(
        { error: "Mode demo tidak memakai bundleId — pilih mode 'bundle'." },
        { status: 422 },
      );
    }

    const { runBatchId, result } = await processRun({
      periodKey,
      tanggalH,
      ambangAcrPct,
      bundleName: clampString(body.bundleName, 120),
      bundleId: mode === "bundle" ? bundleId : null,
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
    const message = err instanceof Error ? err.message : "Gagal memproses run.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
