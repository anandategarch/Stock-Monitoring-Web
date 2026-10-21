// ============================================================
// agent-service.ts — logika PEMBORONG job "Python di Laptop" (Task 51).
// SERVER-ONLY. Arsitektur PULL: web tidak bisa menjangkau laptop di balik
// NAT, jadi agent Python polling /api/agent/claim; setelah job di-jemput,
// agent menarik file Drive + menjalankan engine FastAPI SECARA LOKAL,
// lalu mengunggah hasil EngineResult ter-chunk (gzip+base64). Server merakit
// hasil → membuat run pratinjau (RunBatch) → UI menampilkan → KOMIT memakai
// hasil tersimpan (tanpa engine — serverless tidak punya engine).
// ============================================================
import "server-only";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { clampString, parseIntInRange, isPeriodKey } from "@/lib/validate";
import { ensureAgentTables, unpackResult } from "@/lib/agent-store";
import { processRun } from "@/lib/snapshot-service";
import type { EngineResult, EngineSummary } from "@/lib/types";
import type { AgentJob, AgentJobChunk } from "@prisma/client";

/** Maksimal link Drive per job (samakan tarikan server: 14 kanonik + cadangan). */
const MAX_TARGETS = 16;
/** Maksimal potongan hasil (32 × ±2,2 MB gzip ≈ jauh di atas kebutuhan riil ±3–6 MB). */
const MAX_CHUNKS = 32;
/** Panjang maksimal base64 per potongan (≈2,25 MB biner — body JSON aman < 4,5 MB Vercel). */
const CHUNK_B64_MAX = 3_000_000;
/** Batas baris hasil run agent (pengaman; run nyata user ±79 ribu baris). */
const MAX_ROWS = 400_000;
/** Job RUNNING yang heartbeat-nya lebih tua dari ini dianggap agent mati. */
const STALE_RUNNING_MS = 15 * 60_000;
/** Job QUEUED yang tidak juga dijemput → kedaluwarsa. */
const STALE_QUEUED_MS = 24 * 60 * 60_000;
/** Jendela "agent online" (poll ±3 dtk; longgar untuk jeda jaringan). */
const ONLINE_WINDOW_MS = 30_000;

const PRESENCE_KEY = "agentPresence";
const ACTIVE_STATUSES = ["QUEUED", "RUNNING", "FINALIZING"] as const;

const ACTOR = "analyst";

/** Error layanan agent — status HTTP semantik (route tinggal memetakan). */
export class AgentServiceError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "AgentServiceError";
  }
}

// ---------- Tipe publik (dipakai types.ts untuk DTO) ----------

export type AgentJobTarget = {
  rowId: string | null;
  folderId: string;
  url: string;
  folderName: string;
  folderKey: string | null;
};

type JobRow = AgentJob & { chunks?: AgentJobChunk[] };

// ---------- Util kecil ----------

async function audit(action: string, entityId: string | null, detail: unknown) {
  try {
    await db.auditLog.create({
      data: {
        action,
        entity: "AgentJob",
        entityId: entityId ?? undefined,
        detailJson: JSON.stringify(detail),
        actor: ACTOR,
      },
    });
  } catch {
    // audit gagal tidak boleh membatalkan alur utama (pelajaran EMAXCONNSESSION Task 50)
  }
}

function isP2002(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002";
}

// ---------- Sweep job basi (dipanggil lazy oleh status/claim) ----------

async function sweepStaleJobs(): Promise<void> {
  const now = Date.now();
  try {
    // RUNNING/FINALIZING tanpa heartbeat ≥15 menit → agent mati di tengah jalan.
    const running = await db.agentJob.findMany({
      where: { status: { in: ["RUNNING", "FINALIZING"] } },
      select: { id: true, heartbeatAt: true, claimedAt: true, createdAt: true },
    });
    const deadIds = running
      .filter((j) => {
        const anchor = j.heartbeatAt ?? j.claimedAt ?? j.createdAt;
        return now - anchor.getTime() > STALE_RUNNING_MS;
      })
      .map((j) => j.id);
    if (deadIds.length > 0) {
      const upd = await db.agentJob.updateMany({
        where: { id: { in: deadIds }, status: { in: ["RUNNING", "FINALIZING"] } },
        data: {
          status: "FAILED",
          error: "Agent tidak melapor ≥15 menit — laptop mati/koneksi putus. Jalankan agent lalu ulangi job.",
          finishedAt: new Date(),
        },
      });
      if (upd.count > 0) {
        await db.agentJobChunk.deleteMany({ where: { jobId: { in: deadIds } } });
      }
    }
    // QUEUED >24 jam tidak pernah dijemput → kedaluwarsa.
    await db.agentJob.updateMany({
      where: { status: "QUEUED", createdAt: { lt: new Date(now - STALE_QUEUED_MS) } },
      data: { status: "CANCELLED", error: "Kedaluwarsa — tidak dijemput agent >24 jam.", finishedAt: new Date() },
    });
  } catch {
    // sweep tidak boleh merusak pemanggil
  }
}

// ---------- DTO ----------

export function toJobDto(row: JobRow) {
  const targets = safeParse<AgentJobTarget[]>(row.paramsJson, []);
  const meta = safeParse<{
    summary?: EngineSummary;
    engineKind?: string;
    durationMs?: number;
    rowCount?: number;
  }>(row.resultMetaJson, {});
  return {
    id: row.id,
    kind: row.kind,
    status: row.status as
      | "QUEUED" | "RUNNING" | "FINALIZING" | "COMPLETED" | "FAILED" | "CANCELLED",
    periodKey: row.periodKey,
    tanggalH: row.tanggalH,
    ambangAcrPct: row.ambangAcrPct,
    bundleName: row.bundleName,
    targets,
    progress: row.progress,
    message: row.message,
    agentName: row.agentName,
    error: row.error,
    runBatchId: row.runBatchId,
    resultMeta: meta.summary
      ? {
          summary: meta.summary,
          engineKind: meta.engineKind ?? null,
          durationMs: meta.durationMs ?? null,
        }
      : null,
    createdAt: row.createdAt.toISOString(),
    claimedAt: row.claimedAt?.toISOString() ?? null,
    heartbeatAt: row.heartbeatAt?.toISOString() ?? null,
    finishedAt: row.finishedAt?.toISOString() ?? null,
  };
}

export type AgentJobDto = ReturnType<typeof toJobDto>;

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

// ---------- Kehadiran agent (Setting) ----------

type Presence = { agentName: string; lastSeenAt: string; engine?: Record<string, unknown> };

async function touchPresence(agentName: string, engine?: Record<string, unknown>) {
  const value: Presence = {
    agentName: agentName.slice(0, 80),
    lastSeenAt: new Date().toISOString(),
    ...(engine ? { engine } : {}),
  };
  try {
    await db.setting.upsert({
      where: { key: PRESENCE_KEY },
      update: { valueJson: JSON.stringify(value) },
      create: { key: PRESENCE_KEY, valueJson: JSON.stringify(value) },
    });
  } catch {
    // presence best-effort — jangan gagalkan claim
  }
}

async function readPresence(): Promise<Presence | null> {
  try {
    const row = await db.setting.findUnique({ where: { key: PRESENCE_KEY } });
    return row ? safeParse<Presence | null>(row.valueJson, null) : null;
  } catch {
    return null;
  }
}

// ---------- Buat job (UI) ----------

export async function createAgentJob(body: Record<string, unknown>): Promise<AgentJobDto> {
  await ensureAgentTables();
  await sweepStaleJobs();

  const periodKey = body.periodKey;
  if (!isPeriodKey(periodKey)) {
    throw new AgentServiceError(422, "periodKey wajib format YYYY-MM (contoh: 2026-10).");
  }
  const tanggalH = parseIntInRange(body.tanggalH, 1, 31);
  const ambangAcrPct = parseIntInRange(body.ambangAcrPct, 1, 200);
  if (tanggalH === null) throw new AgentServiceError(422, "tanggalH wajib integer 1..31.");
  if (ambangAcrPct === null) throw new AgentServiceError(422, "ambangAcrPct wajib integer 1..200.");

  const ids = Array.isArray(body.ids)
    ? body.ids.filter((x): x is string => typeof x === "string")
    : [];
  if (ids.length === 0) {
    throw new AgentServiceError(422, "Centang minimal satu link Drive tersimpan untuk diproses agent.");
  }
  if (ids.length > MAX_TARGETS) {
    throw new AgentServiceError(422, `Maksimal ${MAX_TARGETS} link Drive per job agent.`);
  }

  const active = await db.agentJob.findFirst({
    where: { status: { in: [...ACTIVE_STATUSES] } },
    orderBy: { createdAt: "desc" },
  });
  if (active) {
    const dto = toJobDto(active);
    throw new AgentServiceError(
      409,
      `Masih ada job agent aktif (${dto.status}${dto.agentName ? ` · ${dto.agentName}` : ""}) — tunggu selesai atau batalkan dulu.`,
    );
  }

  const rows = await db.driveFolderLink.findMany({ where: { id: { in: ids } } });
  const missing = ids.filter((id) => !rows.some((r) => r.id === id));
  if (missing.length > 0) {
    throw new AgentServiceError(404, `Link tersimpan tidak ditemukan (id: ${missing.join(", ")}).`);
  }
  // Urutkan sesuai urutan ids UI (deterministik).
  const byId = new Map(rows.map((r) => [r.id, r]));
  const targets: AgentJobTarget[] = ids.map((id) => {
    const r = byId.get(id)!;
    return {
      rowId: r.id,
      folderId: r.folderId,
      url: r.url,
      folderName: r.folderName,
      folderKey: r.folderKey,
    };
  });

  const bundleName =
    clampString(body.bundleName, 120) ??
    (targets.length === 1 ? targets[0]!.folderName : `Agent ${targets.length} folder Drive`);

  let job;
  try {
    job = await db.agentJob.create({
      data: {
        kind: "PROCESS_DRIVE",
        status: "QUEUED",
        periodKey,
        tanggalH,
        ambangAcrPct,
        bundleName,
        paramsJson: JSON.stringify(targets),
        message: "Menunggu agent di laptop menjemput…",
      },
    });
  } catch (err) {
    if (isP2002(err)) {
      throw new AgentServiceError(409, "Job baru saja dibuat di tab lain — muat ulang daftar.");
    }
    throw err;
  }

  await audit("AGENT_JOB_CREATE", job.id, {
    periodKey,
    tanggalH,
    ambangAcrPct,
    targets: targets.map((t) => t.folderName),
  });
  return toJobDto(job);
}

// ---------- Status papan job (UI) ----------

export async function agentStatus(): Promise<{
  online: boolean;
  agentName: string | null;
  lastSeenAt: string | null;
  engine: Record<string, unknown> | null;
  tokenConfigured: boolean;
  activeJob: AgentJobDto | null;
  recentJobs: AgentJobDto[];
}> {
  await ensureAgentTables();
  await sweepStaleJobs();

  const presence = await readPresence();
  const online =
    !!presence &&
    Date.now() - new Date(presence.lastSeenAt).getTime() < ONLINE_WINDOW_MS;

  const recent = await db.agentJob.findMany({
    orderBy: { createdAt: "desc" },
    take: 6,
  });
  const active = recent.find((j) => ACTIVE_STATUSES.includes(j.status as never)) ?? null;
  return {
    online,
    agentName: presence?.agentName ?? null,
    lastSeenAt: presence?.lastSeenAt ?? null,
    engine: presence?.engine ?? null,
    tokenConfigured: true,
    activeJob: active ? toJobDto(active) : null,
    recentJobs: recent.map(toJobDto),
  };
}

// ---------- Detail job (UI polling) ----------

export async function getAgentJob(id: string): Promise<AgentJobDto> {
  await ensureAgentTables();
  const row = await db.agentJob.findUnique({ where: { id } });
  if (!row) throw new AgentServiceError(404, "Job agent tidak ditemukan.");
  return toJobDto(row);
}

// ---------- Batalkan job (UI) ----------

export async function cancelAgentJob(id: string): Promise<AgentJobDto> {
  await ensureAgentTables();
  const row = await db.agentJob.findUnique({ where: { id } });
  if (!row) throw new AgentServiceError(404, "Job agent tidak ditemukan.");
  if (row.status === "FINALIZING") {
    throw new AgentServiceError(409, "Job sedang dirakit di server — sebentar lagi selesai, tidak bisa dibatalkan.");
  }
  if (!ACTIVE_STATUSES.includes(row.status as never)) {
    throw new AgentServiceError(409, `Job sudah berstatus ${row.status} — tidak ada yang perlu dibatalkan.`);
  }
  await db.agentJob.update({
    where: { id },
    data: { status: "CANCELLED", finishedAt: new Date(), error: "Dibatalkan oleh user." },
  });
  await db.agentJobChunk.deleteMany({ where: { jobId: id } });
  await audit("AGENT_JOB_CANCEL", id, { fromStatus: row.status });
  return getAgentJob(id);
}

// ---------- Claim job (agent, token) ----------

export async function claimAgentJob(
  agentNameRaw: string,
  engine?: Record<string, unknown>,
): Promise<AgentJobDto | null> {
  await ensureAgentTables();
  await sweepStaleJobs();
  const agentName = clampString(agentNameRaw, 80) ?? "agent-laptop";
  await touchPresence(agentName, engine);

  // Klaim atomik: pilih QUEUED tertua lalu updateMany berjaga status — dua
  // agent yang meng-claim bersamaan tidak mungkin mendapat job yang sama.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const next = await db.agentJob.findFirst({
      where: { status: "QUEUED" },
      orderBy: { createdAt: "asc" },
    });
    if (!next) return null;
    const now = new Date();
    const upd = await db.agentJob.updateMany({
      where: { id: next.id, status: "QUEUED" },
      data: {
        status: "RUNNING",
        agentName,
        claimedAt: now,
        heartbeatAt: now,
        progress: 1,
        message: `Diambil oleh ${agentName} — menyiapkan tarikan…`,
      },
    });
    if (upd.count === 1) {
      await audit("AGENT_JOB_CLAIM", next.id, { agentName });
      return getAgentJob(next.id);
    }
  }
  return null;
}

// ---------- Progress / chunk / complete / fail (agent, token) ----------

async function jobRunningOrCancelled(id: string): Promise<AgentJob> {
  const row = await db.agentJob.findUnique({ where: { id } });
  if (!row) throw new AgentServiceError(404, "Job agent tidak ditemukan.");
  if (row.status !== "RUNNING" && row.status !== "CANCELLED") {
    throw new AgentServiceError(409, `Job berstatus ${row.status} — laporan agent ditolak.`);
  }
  return row;
}

export async function reportProgress(
  id: string,
  body: { progress?: unknown; message?: unknown },
): Promise<{ ok: true; cancelled: boolean }> {
  await ensureAgentTables();
  const row = await jobRunningOrCancelled(id);
  const progress = parseIntInRange(body.progress, 0, 100) ?? row.progress;
  const message = clampString(body.message, 200);
  if (row.status === "RUNNING") {
    await db.agentJob.update({
      where: { id },
      data: {
        progress,
        ...(message ? { message } : {}),
        heartbeatAt: new Date(),
      },
    });
  }
  return { ok: true, cancelled: row.status === "CANCELLED" };
}

export async function reportChunk(
  id: string,
  body: { seq?: unknown; data?: unknown },
): Promise<{ ok: true; cancelled: boolean; received: number }> {
  await ensureAgentTables();
  const row = await jobRunningOrCancelled(id);
  if (row.status === "CANCELLED") return { ok: true, cancelled: true, received: 0 };

  const seq = parseIntInRange(body.seq, 0, MAX_CHUNKS - 1);
  if (seq === null) throw new AgentServiceError(422, `seq potongan wajib integer 0..${MAX_CHUNKS - 1}.`);
  const data = typeof body.data === "string" ? body.data : "";
  if (!data || data.length > CHUNK_B64_MAX) {
    throw new AgentServiceError(422, "Potongan hasil kosong atau melebihi batas ukuran.");
  }
  const count = await db.agentJobChunk.count({ where: { jobId: id } });
  if (count >= MAX_CHUNKS) {
    throw new AgentServiceError(422, `Terlalu banyak potongan (maks ${MAX_CHUNKS}) — hasil terlalu besar.`);
  }
  if (seq !== count) {
    throw new AgentServiceError(
      409,
      `Potongan tidak berurutan: server menunggu seq ${count}, dikirim ${seq}. Ulangi unggahan dari potongan itu.`,
    );
  }
  try {
    await db.agentJobChunk.create({ data: { jobId: id, seq, data } });
  } catch (err) {
    if (isP2002(err)) {
      throw new AgentServiceError(409, "Potongan seq itu sudah ada — lanjut ke seq berikutnya.");
    }
    throw err;
  }
  await db.agentJob.update({
    where: { id },
    data: { heartbeatAt: new Date(), message: `Mengunggah hasil… (${count + 1} potongan)` },
  });
  return { ok: true, cancelled: false, received: count + 1 };
}

/** Validasi bentuk EngineResult dari agent (kontrak v1) — jujur menolak sampah. */
function validateAgentResult(result: unknown, job: AgentJob): EngineResult {
  const r = result as Partial<EngineResult> | null;
  const bad = (msg: string) => new AgentServiceError(422, `Hasil engine tidak valid: ${msg}`);
  if (!r || typeof r !== "object") throw bad("bukan objek JSON.");
  if (r.contractVersion !== "1") throw bad("contractVersion harus \"1\".");
  if (!["SELESAI", "SELESAI_DENGAN_PERINGATAN", "SELESAI_PARSIAL"].includes(String(r.status))) {
    throw bad("status run tidak dikenali.");
  }
  if (r.periodKey !== job.periodKey) {
    throw bad(`periodKey "${String(r.periodKey)}" ≠ job "${job.periodKey}".`);
  }
  if (typeof r.engineKind !== "string" || !r.engineKind) throw bad("engineKind kosong.");
  if (typeof r.definitionVersion !== "string" || !r.definitionVersion) {
    throw bad("definitionVersion kosong (INV-4).");
  }
  const s = r.summary as Partial<EngineSummary> | undefined;
  for (const key of [
    "restoCount", "itemCount", "rowCount", "dayCount", "nominalTotal",
    "deviasiQtyTotal", "skipFileCount", "warningCount", "errorCount", "dqIssueCount", "poCount",
  ] as const) {
    if (typeof s?.[key] !== "number" || !Number.isFinite(s[key])) {
      throw bad(`summary.${key} bukan angka.`);
    }
  }
  if (!Array.isArray(r.rows)) throw bad("rows bukan array.");
  if (r.rows.length > MAX_ROWS) throw bad(`rows ${r.rows.length} melebihi batas ${MAX_ROWS}.`);
  for (const arr of ["prices", "selisihIn", "po", "dqIssues", "logs", "sourceFiles"] as const) {
    if (!Array.isArray(r[arr])) throw bad(`${arr} bukan array.`);
  }
  // §82b: warningCount/errorCount harus cocok dengan log (kontrak engine).
  const logs = r.logs as { level?: string }[];
  const warn = logs.filter((l) => l?.level === "WARNING").length;
  const err = logs.filter((l) => l?.level === "ERROR").length;
  if (warn !== s!.warningCount) throw bad(`summary.warningCount (${s!.warningCount}) ≠ log WARNING (${warn}) — §82b.`);
  if (err !== s!.errorCount) throw bad(`summary.errorCount (${s!.errorCount}) ≠ log ERROR (${err}) — §82b.`);
  if (r.rows.length > 0) {
    const first = r.rows[0] as unknown as Record<string, unknown>;
    for (const key of ["restoCode", "itemName", "satuan", "kategori", "isGR", "day"]) {
      if (!(key in first)) throw bad(`baris rows pertama tidak punya "${key}".`);
    }
  }
  return r as EngineResult;
}

export async function reportComplete(id: string): Promise<{
  ok: true;
  cancelled: boolean;
  runBatchId: string | null;
  rowCount: number | null;
}> {
  await ensureAgentTables();
  const row = await db.agentJob.findUnique({ where: { id } });
  if (!row) throw new AgentServiceError(404, "Job agent tidak ditemukan.");
  if (row.status === "CANCELLED") {
    return { ok: true, cancelled: true, runBatchId: null, rowCount: null };
  }
  if (row.status === "FINALIZING") {
    throw new AgentServiceError(409, "Job sudah sedang difinalisasi — tunggu sebentar.");
  }
  if (row.status !== "RUNNING") {
    throw new AgentServiceError(409, `Job berstatus ${row.status} — complete ditolak.`);
  }

  // Guard konkuren: hanya satu finalize yang boleh jalan.
  const guard = await db.agentJob.updateMany({
    where: { id, status: "RUNNING" },
    data: { status: "FINALIZING", heartbeatAt: new Date(), message: "Server merakit hasil & membuat run…" },
  });
  if (guard.count === 0) {
    throw new AgentServiceError(409, "Job sedang difinalisasi di permintaan lain.");
  }

  let result: EngineResult;
  try {
    const chunks = await db.agentJobChunk.findMany({ where: { jobId: id }, orderBy: { seq: "asc" } });
    if (chunks.length === 0) {
      throw new AgentServiceError(422, "Tidak ada potongan hasil yang diunggah.");
    }
    for (let i = 0; i < chunks.length; i += 1) {
      if (chunks[i]!.seq !== i) {
        throw new AgentServiceError(422, `Potongan hilang/tidak urut (seq ${chunks[i]!.seq} ≠ ${i}).`);
      }
    }
    const packed = Buffer.concat(chunks.map((c) => Buffer.from(c.data, "base64")));
    result = unpackResult(packed.toString("base64"));
    result = validateAgentResult(result, row);
  } catch (err) {
    // Hasil rusak/invalid → job FAILED jujur; potongan dibuang (tidak ada gunanya).
    await db.agentJob.update({
      where: { id },
      data: {
        status: "FAILED",
        error: err instanceof Error ? err.message : "Hasil agent tidak bisa dirakit.",
        finishedAt: new Date(),
      },
    });
    await db.agentJobChunk.deleteMany({ where: { jobId: id } });
    if (err instanceof AgentServiceError) throw err;
    throw new AgentServiceError(422, "Hasil agent tidak bisa dirakit — unduhan potongan korup.");
  }

  // Buat run pratinjau dari hasil agent (satu jalur processRun — FR-3).
  let runBatchId: string;
  try {
    const out = await processRun(
      {
        periodKey: row.periodKey,
        tanggalH: row.tanggalH,
        ambangAcrPct: row.ambangAcrPct,
        bundleName: row.bundleName,
      },
      { providedResult: result, agentName: row.agentName },
    );
    runBatchId = out.runBatchId;
  } catch (err) {
    // Kegagalan SISI SERVER (koneksi dsb.) → kembalikan ke RUNNING supaya agent
    // bisa mengirim ulang complete tanpa menarik ulang file (potongan tetap ada).
    await db.agentJob.updateMany({
      where: { id, status: "FINALIZING" },
      data: { status: "RUNNING", heartbeatAt: new Date(), message: "Server gagal membuat run — agent akan mencoba ulang." },
    });
    throw new AgentServiceError(502, `Gagal membuat run dari hasil agent: ${err instanceof Error ? err.message : "kesalahan server"}.`);
  }

  // FINALIZING → COMPLETED (berjaga status — bila user membatalkan di tengah
  // perakitkan, job tetap CANCELLED dan run hanya jadi pratinjau yatim).
  const done = await db.agentJob.updateMany({
    where: { id, status: "FINALIZING" },
    data: {
      status: "COMPLETED",
      runBatchId,
      progress: 100,
      message: "Selesai — hasil masuk sebagai run pratinjau. Tinjau lalu KOMIT.",
      resultMetaJson: JSON.stringify({
        summary: result.summary,
        engineKind: result.engineKind,
        engineName: result.engineName,
        durationMs: result.durationMs,
      }),
      finishedAt: new Date(),
    },
  });
  await db.agentJobChunk.deleteMany({ where: { jobId: id } });
  await audit("AGENT_JOB_COMPLETE", id, {
    runBatchId,
    rowCount: result.summary.rowCount,
    agentName: row.agentName,
    durationMs: result.durationMs,
  });

  if (done.count === 0) {
    return { ok: true, cancelled: true, runBatchId, rowCount: result.summary.rowCount };
  }
  return { ok: true, cancelled: false, runBatchId, rowCount: result.summary.rowCount };
}

export async function reportFail(id: string, errorRaw: unknown): Promise<{ ok: true }> {
  await ensureAgentTables();
  const row = await db.agentJob.findUnique({ where: { id } });
  if (!row) throw new AgentServiceError(404, "Job agent tidak ditemukan.");
  if (row.status === "COMPLETED" || row.status === "CANCELLED") {
    return { ok: true }; // sudah tamat — laporan gagal diabaikan jujur
  }
  const error = clampString(errorRaw, 400) ?? "Agent melaporkan kegagalan tanpa keterangan.";
  await db.agentJob.update({
    where: { id },
    data: { status: "FAILED", error, finishedAt: new Date() },
  });
  await db.agentJobChunk.deleteMany({ where: { jobId: id } });
  await audit("AGENT_JOB_FAIL", id, { error: error.slice(0, 120) });
  return { ok: true };
}
