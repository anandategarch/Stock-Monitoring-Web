import { PrismaClient } from '@prisma/client'

// ============================================================
// Serverless (Vercel) + Supabase session pooler: pool koneksi Prisma
// default = num_cpus×2+1 — banyak instance lambda yang masing-masing membuka
// beberapa koneksi akan memenuhi kuota klien pooler sesi (pool_size 15;
// error "EMAXCONNSESSION max clients reached" terverifikasi live 2026-10-21).
// Batasi 1 koneksi per instance — kueri antre di satu koneksi (cukup untuk
// beban app ini). Hanya di serverless; lokal/sandbox tak tersentuh.
// ============================================================
if (
  process.env.VERCEL &&
  process.env.DATABASE_URL &&
  !/[?&]connection_limit=/.test(process.env.DATABASE_URL)
) {
  process.env.DATABASE_URL +=
    (process.env.DATABASE_URL.includes('?') ? '&' : '?') +
    'connection_limit=1&connect_timeout=10&pool_timeout=30'
}

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: ['warn', 'error'],
  })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
