import { NextResponse } from "next/server";
import { engineHealth, ENGINE_PROD_URL } from "@/lib/engine";
import { embedFallbackEnabled, EMBED_ENGINE_NAME } from "@/lib/engine-embed";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/engine/health — status KEDUA engine (FR-14/FR-81):
 * demo (:3030, sintetis) + PRODUKSI (:3031, pipeline asli v3.9.71),
 * plus ketersediaan fallback embedded (deploy tanpa engine co-located,
 * mis. Vercel). Field `health` tetap engine demo (kompatibel header shell)
 * + `production` untuk panel Config. */
export async function GET() {
  const [health, production] = await Promise.all([
    engineHealth(),
    engineHealth(ENGINE_PROD_URL),
  ]);

  const embeddedAvailable = embedFallbackEnabled();
  const out: {
    reachable: boolean;
    health?: typeof health;
    error?: string;
    embedded: {
      available: boolean;
      engineName: string;
      note: string;
    };
    production: { reachable: boolean; health?: typeof production; error?: string };
  } = {
    reachable: Boolean(health),
    embedded: {
      available: embeddedAvailable,
      engineName: EMBED_ENGINE_NAME,
      note: embeddedAvailable
        ? "Run DEMO (tanpa bundle) otomatis memakai fallback embedded bila service demo tidak terjangkau — seed & pelatihan UI tetap jalan tanpa engine eksternal. Set SM_ENGINE_EMBED_FALLBACK=off untuk mematikan."
        : "Fallback embedded dimatikan (SM_ENGINE_EMBED_FALLBACK=off).",
    },
    production: {
      reachable: Boolean(production),
      ...(production
        ? {}
        : {
            error: `Engine PRODUKSI tidak terjangkau di ${ENGINE_PROD_URL}. Jalankan: cd mini-services/engine-fastapi && bun run dev (atau host Dockerfile — lihat README.md §Engine Produksi)`,
          }),
    },
  };
  if (health) {
    out.health = health;
  } else {
    out.error = "Engine demo tidak terjangkau di port 3030. Jalankan: cd mini-services/engine && bun run dev";
  }
  if (production) {
    out.production.health = production;
    delete out.production.error;
  }
  return NextResponse.json(out);
}
