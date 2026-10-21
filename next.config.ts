import type { NextConfig } from "next";

// CATATAN DEPLOY: `output: "standalone"` sengaja TIDAK dipakai — Vercel tidak
// mendukungnya. Untuk self-host (Docker/VPS) hasil `next build` standar sudah
// dijalankan `next start` (lihat README.md §Self-host).
const nextConfig: NextConfig = {
  // Domain preview sandbox (dev only — tidak berpengaruh di Vercel).
  allowedDevOrigins: ["*.space-z.ai"],
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
};

export default nextConfig;
