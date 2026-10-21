// ============================================================
// Engine demo EMBEDDED — fallback in-process (SERVER-ONLY).
//
// Dipakai `src/lib/engine.ts` HANYA ketika:
//   1. service engine DEMO (SM_ENGINE_URL) tidak terjangkau (mis. deploy
//      Vercel tanpa engine co-located), DAN
//   2. run BUKAN run bundle real (target engine produksi tidak pernah
//      di-fallback — gagal jujur, NFR-3).
// Generator + validator yang sama persis dengan mini-services/engine
// (kontrak v1) ⇒ hasil identik & deterministik (FR-12 idempotent):
// run yang diproses lewat service dan dikomit lewat fallback tetap
// menghasilkan snapshot konsisten.
// Nonaktifkan dengan SM_ENGINE_EMBED_FALLBACK=off.
// ============================================================
import { generateDemoResult } from "../../mini-services/engine/generator";
import { validateProcessRequest } from "../../mini-services/engine/validation";
import type { EngineProcessRequest, EngineResult } from "./types";

export const EMBED_ENGINE_NAME = "SM-DEMO-Engine (embedded)";

export function embedFallbackEnabled(): boolean {
  return process.env.SM_ENGINE_EMBED_FALLBACK !== "off";
}

export function embeddedDemoProcess(req: EngineProcessRequest): EngineResult {
  const validated = validateProcessRequest(req);
  if (!validated.ok) throw new Error(validated.error);
  const result = generateDemoResult(validated.value);
  result.engineName = EMBED_ENGINE_NAME;
  result.logs = [
    ...result.logs,
    {
      ts: new Date().toISOString(),
      level: "INFO" as const,
      message:
        "Diproses oleh engine demo EMBEDDED (fallback in-process) — service demo di SM_ENGINE_URL " +
        "tidak terjangkau. Generator identik dengan mini-services/engine, hasil deterministik (FR-12).",
    },
  ];
  return result;
}
