// Client engine service — SERVER ONLY (dipanggil dari API routes, bukan dari browser).
// Kontrak: docs/ENGINE-CONTRACT.md. URL via env supaya produksi tinggal ganti target.
// Dua engine: DEMO (default :3030 — data sintetis) dan PRODUKSI FastAPI (:3031 —
// pipeline asli v3.9.71, SM_ENGINE_PROD_URL; §5 kontrak: Next.js satu-satunya penelepon).
import type { EngineHealth, EngineProcessRequest } from "./types";
import type { EngineResult } from "./types";
import { embedFallbackEnabled, embeddedDemoProcess } from "./engine-embed";

const ENGINE_URL = process.env.SM_ENGINE_URL ?? "http://127.0.0.1:3030";
export const ENGINE_PROD_URL =
  process.env.SM_ENGINE_PROD_URL ?? "http://127.0.0.1:3031";

export async function engineHealth(engineUrl?: string): Promise<EngineHealth | null> {
  try {
    const res = await fetch(`${engineUrl ?? ENGINE_URL}/health`, {
      signal: AbortSignal.timeout(4000),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as EngineHealth;
  } catch {
    return null;
  }
}

export async function engineProcess(
  req: EngineProcessRequest,
  engineUrl?: string,
): Promise<EngineResult> {
  const target = engineUrl ?? ENGINE_URL;
  // Shared-secret opsional engine produksi (audit 48-g-engine): bila
  // SM_ENGINE_TOKEN diisi di kedua sisi, dikirim sebagai header; engine tanpa
  // token mengabaikannya (backward compatible).
  const token = process.env.SM_ENGINE_TOKEN;
  let res: Response;
  try {
    res = await fetch(`${target}/process`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-engine-token": token } : {}),
      },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(600000),
      cache: "no-store",
    });
  } catch (err) {
    // Fallback EMBEDDED hanya untuk run DEMO (engineUrl tidak diberikan = target
    // demo). Run bundle real selalu ke engine PRODUKSI — bila terjangkau gagal,
    // error jujur diteruskan (NFR-3: run gagal tak boleh mengarang data).
    if (engineUrl === undefined && embedFallbackEnabled()) {
      return embeddedDemoProcess(req);
    }
    // Serverless (Vercel): engine FastAPI memang TIDAK ADA di sana — jangan
    // suruh user "menjalankan bun run dev di 127.0.0.1:3031" (mustahil di
    // serverless). Katakan yang sebenarnya: pipeline real = instalasi lokal.
    if (process.env.VERCEL) {
      throw new Error(
        "Engine FastAPI tidak tersedia di serverless Vercel — pemrosesan bundle data asli dijalankan dari instalasi lokal (sandbox/PC) tempat engine produksi :3031 hidup. Run DEMO tetap jalan di sini (fallback embedded), dan semua snapshot yang sudah dikomit tetap terlihat di situs ini.",
      );
    }
    throw new Error(
      `Engine service tidak terjangkau di ${target} — pastikan service berjalan (demo: mini-services/engine :3030 · produksi: mini-services/engine-fastapi :3031). Detail: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new Error(body?.error ?? `Engine /process gagal (HTTP ${res.status})`);
  }
  return (await res.json()) as EngineResult;
}
