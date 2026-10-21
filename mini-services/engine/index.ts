/**
 * index.ts — SM-DEMO-Engine: engine demo kontrak v1 (docs/ENGINE-CONTRACT.md).
 *
 * Proyek Bun independen di port TETAP 3030 (tanpa env PORT, sesuai ARCHITECTURE.md §2.1).
 * Hanya server Next.js yang memanggil engine ini (http://127.0.0.1:3030) — browser
 * tidak pernah memanggil engine langsung; semua lewat /api/* Next.js.
 *
 * Endpoint:
 *   GET  /health   → EngineHealth
 *   POST /process  → validasi (422 bila gagal) → EngineResult (kontrak v1)
 *   lainnya         → 404 { "error": "Tidak ditemukan" }
 */
import type { EngineHealth } from "./types";
import { generateDemoResult } from "./generator";
import { validateProcessRequest, type NormalizedEngineParams } from "./validation";

const PORT = 3030;
const ENGINE_NAME = "SM-DEMO-Engine";
const ENGINE_VERSION = "0.1.0";
const DEFINITION_VERSION = "3.9.71-noSI";
const PARITY_NOTE =
  "Engine DEMO — data sintetis deterministik, bukan pipeline Accurate asli; paritas golden-file menunggu engine FastAPI produksi";

/** Status run terakhir (info runtime /health — boleh berbeda antar-request). */
let lastProcessAt: string | null = null;
let lastDurationMs: number | null = null;
let lastStatus: string | null = null;
const bootMs = Date.now();

function jsonResponse(data: unknown, status: number): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function buildHealth(): EngineHealth {
  return {
    status: "ok",
    engineKind: "demo",
    engineName: ENGINE_NAME,
    engineVersion: ENGINE_VERSION,
    definitionVersion: DEFINITION_VERSION,
    contractVersion: "1",
    lastProcessAt,
    lastDurationMs,
    lastStatus,
    uptimeSec: Math.floor((Date.now() - bootMs) / 1000),
    parityNote: PARITY_NOTE,
  };
}

async function handleProcess(request: Request): Promise<Response> {
  const bodyText = await request.text();
  let parsed: unknown;
  try {
    parsed = JSON.parse(bodyText);
  } catch {
    return jsonResponse({ error: "Body request bukan JSON yang valid" }, 422);
  }

  const validated = validateProcessRequest(parsed);
  if (!validated.ok) {
    return jsonResponse({ error: validated.error }, 422);
  }
  const params: NormalizedEngineParams = validated.value;

  try {
    const result = generateDemoResult(params);
    lastProcessAt = result.startedAt;
    lastDurationMs = result.durationMs;
    lastStatus = result.status;
    console.log(`[process] ${params.periodKey} H=${params.tanggalH} ACR=${params.ambangAcrPct}% → ${result.status} (${result.summary.rowCount} baris, ${result.durationMs} ms)`);
    return jsonResponse(result, 200);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return jsonResponse({ error: `Kesalahan internal engine: ${detail}` }, 500);
  }
}

const server = Bun.serve({
  port: PORT,
  fetch(request: Request): Response | Promise<Response> {
    const path = new URL(request.url).pathname;
    if (request.method === "GET" && path === "/health") {
      return jsonResponse(buildHealth(), 200);
    }
    if (request.method === "POST" && path === "/process") {
      return handleProcess(request);
    }
    return jsonResponse({ error: "Tidak ditemukan" }, 404);
  },
});

console.log(
  `[${ENGINE_NAME}] Engine demo berjalan di http://127.0.0.1:${server.port} — kontrak v1, definisi ${DEFINITION_VERSION}, port tetap 3030`,
);
