// ============================================================
// agent-store.ts — penyimpanan & bootstrap tabel AGENT LOKAL
// ("Python di Laptop", Task 51). SERVER-ONLY.
//
// Tabel baru (AgentJob · AgentJobChunk · AgentResult) di-bootstrapping
// idempoten seperti DriveFolderLink (Task 48): password DB produksi tidak
// disimpan di sandbox, jadi DDL baru dikirim dari aplikasi saat pertama
// dipakai. Ganti dengan `bun run db:push:supabase` kapan pun — hasil sama.
//
// AgentResult.data = base64(gzip(JSON EngineResult)) — hasil utuh run yang
// diproses DI LAPTOP. Komit run agent memakai hasil ini TANPA memanggil
// ulang engine (FR-12: engine deterministik → hasil tersimpan = output
// kanonik run; serverless Vercel memang tidak punya engine FastAPI).
// ============================================================
import "server-only";
import { gzipSync, gunzipSync } from "zlib";
import { createHash, timingSafeEqual } from "crypto";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import type { EngineResult } from "@/lib/types";

// ---- Auto-bootstrap DDL (identik output prisma migrate diff per provider) ----

const AGENT_DDL_SQLITE = [
  `CREATE TABLE IF NOT EXISTS "AgentJob" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "kind" TEXT NOT NULL DEFAULT 'PROCESS_DRIVE',
    "status" TEXT NOT NULL,
    "periodKey" TEXT NOT NULL,
    "tanggalH" INTEGER NOT NULL,
    "ambangAcrPct" INTEGER NOT NULL,
    "bundleName" TEXT,
    "paramsJson" TEXT NOT NULL,
    "progress" INTEGER NOT NULL DEFAULT 0,
    "message" TEXT,
    "agentName" TEXT,
    "error" TEXT,
    "resultMetaJson" TEXT,
    "runBatchId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "claimedAt" DATETIME,
    "heartbeatAt" DATETIME,
    "finishedAt" DATETIME
  )`,
  `CREATE INDEX IF NOT EXISTS "AgentJob_status_createdAt_idx" ON "AgentJob"("status","createdAt")`,
  `CREATE INDEX IF NOT EXISTS "AgentJob_createdAt_idx" ON "AgentJob"("createdAt")`,
  `CREATE TABLE IF NOT EXISTS "AgentJobChunk" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "jobId" TEXT NOT NULL,
    "seq" INTEGER NOT NULL,
    "data" TEXT NOT NULL,
    CONSTRAINT "AgentJobChunk_jobId_fkey" FOREIGN KEY ("jobId") REFERENCES "AgentJob"("id") ON DELETE CASCADE
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "AgentJobChunk_jobId_seq_key" ON "AgentJobChunk"("jobId","seq")`,
  `CREATE TABLE IF NOT EXISTS "AgentResult" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "runBatchId" TEXT NOT NULL,
    "data" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "AgentResult_runBatchId_key" ON "AgentResult"("runBatchId")`,
];

const AGENT_DDL_POSTGRES = [
  `CREATE TABLE IF NOT EXISTS "AgentJob" (
    "id" TEXT NOT NULL,
    "kind" TEXT NOT NULL DEFAULT 'PROCESS_DRIVE',
    "status" TEXT NOT NULL,
    "periodKey" TEXT NOT NULL,
    "tanggalH" INTEGER NOT NULL,
    "ambangAcrPct" INTEGER NOT NULL,
    "bundleName" TEXT,
    "paramsJson" TEXT NOT NULL,
    "progress" INTEGER NOT NULL DEFAULT 0,
    "message" TEXT,
    "agentName" TEXT,
    "error" TEXT,
    "resultMetaJson" TEXT,
    "runBatchId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "claimedAt" TIMESTAMP(3),
    "heartbeatAt" TIMESTAMP(3),
    "finishedAt" TIMESTAMP(3),
    CONSTRAINT "AgentJob_pkey" PRIMARY KEY ("id")
  )`,
  `CREATE INDEX IF NOT EXISTS "AgentJob_status_createdAt_idx" ON "AgentJob"("status","createdAt")`,
  `CREATE INDEX IF NOT EXISTS "AgentJob_createdAt_idx" ON "AgentJob"("createdAt")`,
  `CREATE TABLE IF NOT EXISTS "AgentJobChunk" (
    "id" TEXT NOT NULL,
    "jobId" TEXT NOT NULL,
    "seq" INTEGER NOT NULL,
    "data" TEXT NOT NULL,
    CONSTRAINT "AgentJobChunk_pkey" PRIMARY KEY ("id")
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "AgentJobChunk_jobId_seq_key" ON "AgentJobChunk"("jobId","seq")`,
  `CREATE TABLE IF NOT EXISTS "AgentResult" (
    "id" TEXT NOT NULL,
    "runBatchId" TEXT NOT NULL,
    "data" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "AgentResult_pkey" PRIMARY KEY ("id")
  )`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "AgentResult_runBatchId_key" ON "AgentResult"("runBatchId")`,
  `ALTER TABLE "AgentJobChunk" ADD CONSTRAINT "AgentJobChunk_jobId_fkey" FOREIGN KEY ("jobId") REFERENCES "AgentJob"("id") ON DELETE CASCADE`,
];

let agentTablesReady = false;

/** Pastikan tabel agent ada (idempoten, dipanggil semua route agent + komit). */
export async function ensureAgentTables(): Promise<void> {
  if (agentTablesReady) return;
  try {
    await db.agentJob.findFirst({ select: { id: true } });
    agentTablesReady = true;
    return;
  } catch (err) {
    const isMissing =
      (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2021") ||
      /no such table|AgentJob.*(does not|tidak) exist/i.test(err instanceof Error ? err.message : "");
    if (!isMissing) throw err;
    const isSqlite = (process.env.DATABASE_URL ?? "").startsWith("file:");
    for (const stmt of isSqlite ? AGENT_DDL_SQLITE : AGENT_DDL_POSTGRES) {
      // FK sqlite sudah dibuat inline di CREATE TABLE — statement ALTER hanya
      // untuk Postgres; error duplikat constraint saat bootstrap ganda diabaikan.
      try {
        await db.$executeRawUnsafe(stmt);
      } catch (e) {
        if (!/duplicate|already exists/i.test(e instanceof Error ? e.message : "")) throw e;
      }
    }
    agentTablesReady = true;
  }
}

// ---- Autentikasi agent ----

/**
 * Token bersama agent (header X-Agent-Token). Produksi (Vercel) WAJIB mengatur
 * AGENT_TOKEN — tanpa itu endpoint agent menolak jujur (503) daripada terbuka.
 * Dev/sandbox memakai token default yang terdokumentasi supaya E2E jalan
 * tanpa setup. Perbandingan konstan-waktu (hash SHA-256 kedua sisi).
 */
export const AGENT_TOKEN_DEFAULT_DEV = "smweb-dev-agent-token";

export function expectedAgentToken(): string | null {
  const t = process.env.AGENT_TOKEN?.trim();
  if (t) return t;
  return process.env.VERCEL ? null : AGENT_TOKEN_DEFAULT_DEV;
}

export function agentTokenConfigured(): boolean {
  return expectedAgentToken() !== null;
}

export function agentTokenMatches(provided: string | null | undefined): boolean {
  const expected = expectedAgentToken();
  if (!expected) return false;
  const a = createHash("sha256").update(expected).digest();
  const b = createHash("sha256").update(provided ?? "").digest();
  return timingSafeEqual(a, b);
}

// ---- Pack/unpack hasil EngineResult (gzip + base64) ----

export function packResult(result: EngineResult): string {
  return gzipSync(Buffer.from(JSON.stringify(result), "utf8")).toString("base64");
}

export function unpackResult(packed: string): EngineResult {
  const buf = gunzipSync(Buffer.from(packed, "base64"));
  return JSON.parse(buf.toString("utf8")) as EngineResult;
}

/** Hasil run agent tersimpan? (dipakai komit run agent — snapshot-service). */
export async function readAgentResult(runBatchId: string): Promise<EngineResult | null> {
  await ensureAgentTables();
  const row = await db.agentResult.findUnique({ where: { runBatchId }, select: { data: true } });
  if (!row) return null;
  try {
    return unpackResult(row.data);
  } catch {
    return null; // data rusak → komit akan memberi pesan jujur di bawah
  }
}

export async function saveAgentResult(runBatchId: string, result: EngineResult): Promise<void> {
  await db.agentResult.create({ data: { runBatchId, data: packResult(result) } });
}
