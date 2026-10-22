// Semua akses data klien lewat hooks ini (TanStack Query) — satu titik integrasi
// untuk seluruh tab. Subagent UI WAJIB memakai hooks ini, tidak fetch sendiri.
"use client";

import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  AuditLogDto, BundleManifest, CommitStepProgress, CreateCaseRequest, DrilldownResponse, DriveFolderLinkDto, DqIssueDto, EngineHealth,
  FollowUpCaseDto, FollowUpEventDto, IngestCommitResponse, IngestProcessResponse,
  LaporanResponse, NominalResponse, OutletPICDto, OverviewResponse, PivotResponse,
  PoResponse, RunDetail, RunSummary, SelisihInResponse, SettingsDto, SnapshotSummary,
  DeviasiResponse, RestoRef, CaseEventRequest, AgentJobDto, AgentStatusDto,
} from "@/lib/types";

export const qk = {
  snapshots: ["snapshots"] as const,
  overview: ["overview"] as const,
  runs: ["runs"] as const,
  runDetail: (id: string) => ["runs", id] as const,
  restos: (id: string) => ["snapshots", id, "restos"] as const,
  pivot: (id: string, qs: string) => ["snapshots", id, "pivot", qs] as const,
  deviasi: (id: string, qs: string) => ["snapshots", id, "deviasi", qs] as const,
  drilldown: (id: string, resto: string, item: string) => ["snapshots", id, "drill", resto, item] as const,
  selisihIn: (id: string) => ["snapshots", id, "selisih-in"] as const,
  nominal: (id: string) => ["snapshots", id, "nominal"] as const,
  laporan: (id: string, mode: string, h: number) => ["snapshots", id, "laporan", mode, h] as const,
  po: (id: string, qs: string) => ["snapshots", id, "po", qs] as const,
  dq: (id: string) => ["snapshots", id, "dq"] as const,
  followups: (qs: string) => ["followup", qs] as const,
  followupCase: (id: string) => ["followup", id] as const,
  pics: ["pics"] as const,
  settings: ["settings"] as const,
  engineHealth: ["engine-health"] as const,
  audit: (limit: number) => ["audit", limit] as const,
  driveLinks: ["drive-links"] as const,
  agentStatus: ["agent-status"] as const,
  agentJob: (id: string) => ["agent-job", id] as const,
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init?.headers } : init?.headers,
  });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const msg =
      body && typeof body === "object" && "error" in body
        ? String((body as { error: unknown }).error)
        : `Permintaan gagal (HTTP ${res.status}).`;
    const err = new Error(msg) as Error & { status?: number; body?: unknown };
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body as T;
}

// ---------- Queries ----------

export function useSnapshots() {
  return useQuery({
    queryKey: qk.snapshots,
    queryFn: () => fetchJson<{ snapshots: SnapshotSummary[] }>("/api/snapshots"),
  });
}

export function useOverview() {
  return useQuery({
    queryKey: qk.overview,
    queryFn: () => fetchJson<OverviewResponse>("/api/overview"),
  });
}

export function useRuns() {
  return useQuery({
    queryKey: qk.runs,
    queryFn: () => fetchJson<{ runs: RunSummary[] }>("/api/runs"),
  });
}

export function useRunDetail(id: string | null) {
  return useQuery({
    queryKey: qk.runDetail(id ?? "-"),
    queryFn: () => fetchJson<RunDetail>(`/api/runs/${id}`),
    enabled: Boolean(id),
  });
}

export function useRestos(snapshotId: string | null) {
  return useQuery({
    queryKey: qk.restos(snapshotId ?? "-"),
    queryFn: () => fetchJson<{ restos: RestoRef[] }>(`/api/snapshots/${snapshotId}/restos`),
    enabled: Boolean(snapshotId),
  });
}

export function usePivot(snapshotId: string | null, qs: string) {
  return useQuery({
    queryKey: qk.pivot(snapshotId ?? "-", qs),
    queryFn: () => fetchJson<PivotResponse>(`/api/snapshots/${snapshotId}/pivot?${qs}`),
    enabled: Boolean(snapshotId),
    placeholderData: (prev) => prev,
  });
}

export function useDeviasi(snapshotId: string | null, qs: string) {
  return useQuery({
    queryKey: qk.deviasi(snapshotId ?? "-", qs),
    queryFn: () => fetchJson<DeviasiResponse>(`/api/snapshots/${snapshotId}/deviasi?${qs}`),
    enabled: Boolean(snapshotId),
    placeholderData: (prev) => prev,
  });
}

export function useDrilldown(snapshotId: string | null, resto: string | null, item: string | null) {
  return useQuery({
    queryKey: qk.drilldown(snapshotId ?? "-", resto ?? "-", item ?? "-"),
    queryFn: () =>
      fetchJson<DrilldownResponse>(
        `/api/snapshots/${snapshotId}/drilldown?resto=${encodeURIComponent(resto ?? "")}&item=${encodeURIComponent(item ?? "")}`,
      ),
    enabled: Boolean(snapshotId && resto && item),
  });
}

export function useSelisihIn(snapshotId: string | null) {
  return useQuery({
    queryKey: qk.selisihIn(snapshotId ?? "-"),
    queryFn: () => fetchJson<SelisihInResponse>(`/api/snapshots/${snapshotId}/selisih-in`),
    enabled: Boolean(snapshotId),
  });
}

export function useNominal(snapshotId: string | null) {
  return useQuery({
    queryKey: qk.nominal(snapshotId ?? "-"),
    queryFn: () => fetchJson<NominalResponse>(`/api/snapshots/${snapshotId}/nominal`),
    enabled: Boolean(snapshotId),
  });
}

export function useLaporan(snapshotId: string | null, mode: string, h: number) {
  return useQuery({
    queryKey: qk.laporan(snapshotId ?? "-", mode, h),
    queryFn: () => fetchJson<LaporanResponse>(`/api/snapshots/${snapshotId}/laporan?mode=${mode}&h=${h}`),
    enabled: Boolean(snapshotId),
  });
}

export function usePo(snapshotId: string | null, qs: string) {
  return useQuery({
    queryKey: qk.po(snapshotId ?? "-", qs),
    queryFn: () => fetchJson<PoResponse>(`/api/snapshots/${snapshotId}/po?${qs}`),
    enabled: Boolean(snapshotId),
  });
}

export function useDq(snapshotId: string | null) {
  return useQuery({
    queryKey: qk.dq(snapshotId ?? "-"),
    queryFn: () => fetchJson<{ issues: DqIssueDto[] }>(`/api/snapshots/${snapshotId}/dq`),
    enabled: Boolean(snapshotId),
  });
}

export function useFollowups(qs: string) {
  return useQuery({
    queryKey: qk.followups(qs),
    queryFn: () => fetchJson<{ cases: FollowUpCaseDto[] }>(`/api/followup?${qs}`),
  });
}

export function useFollowupCase(id: string | null) {
  return useQuery({
    queryKey: qk.followupCase(id ?? "-"),
    queryFn: () => fetchJson<{ case: FollowUpCaseDto; events: FollowUpEventDto[] }>(`/api/followup/${id}`),
    enabled: Boolean(id),
  });
}

export function usePics() {
  return useQuery({
    queryKey: qk.pics,
    queryFn: () => fetchJson<{ pics: OutletPICDto[] }>("/api/pics"),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: qk.settings,
    queryFn: () => fetchJson<{ settings: SettingsDto }>("/api/settings"),
  });
}

export function useEngineHealth() {
  return useQuery({
    queryKey: qk.engineHealth,
    queryFn: () =>
      fetchJson<{
        reachable: boolean;
        health?: EngineHealth;
        error?: string;
        embedded?: { available: boolean; engineName: string; note: string };
        production?: { reachable: boolean; health?: EngineHealth; error?: string };
      }>("/api/engine/health"),
    refetchInterval: 30_000,
  });
}

export function useAudit(limit = 50) {
  return useQuery({
    queryKey: qk.audit(limit),
    queryFn: () => fetchJson<{ logs: AuditLogDto[] }>(`/api/audit?limit=${limit}`),
  });
}

// ---------- Mutations ----------

function useInvalidateAll() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries();
  };
}

export function useIngestProcess() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (body: {
      periodKey: string; tanggalH?: number; ambangAcrPct?: number; bundleName?: string;
      mode?: "demo" | "bundle"; bundleId?: string;
    }) =>
      fetchJson<IngestProcessResponse>("/api/ingest/process", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateAll(),
  });
}

// ---------- Google Drive (FR-1: tarik tanpa ZIP manual) ----------

/** Daftar link folder Drive tersimpan — "biar ingat". */
export function useDriveLinks() {
  return useQuery({
    queryKey: qk.driveLinks,
    queryFn: () => fetchJson<{ links: DriveFolderLinkDto[] }>("/api/ingest/drive"),
  });
}

/** Simpan + cek link folder Drive (listing langsung oleh server). */
export function useDriveSaveLink() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (url: string) =>
      fetchJson<{ link: DriveFolderLinkDto; created: boolean; warnings: string[] }>(
        "/api/ingest/drive",
        { method: "POST", body: JSON.stringify({ action: "save", url }) },
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.driveLinks }),
  });
}

/** Tarik file Excel dari link tersimpan → bundle (respons = manifest, sama
 *  dengan unggah ZIP — alur pratinjau/komit lanjutan identik).
 *  action "preview" = PRATINJAU CEPAT: listing Drive saja tanpa unduh —
 *  bebas kuota disk/durasi serverless (manifest.previewOnly = true). */
export function useDrivePull() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { ids?: string[]; url?: string; action?: "process" | "preview" }) =>
      fetchJson<BundleManifest>("/api/ingest/drive", {
        method: "POST",
        body: JSON.stringify({ action: vars.action ?? "process", ids: vars.ids, url: vars.url }),
      }),
    onSuccess: () => {
      // Segarkan "terakhir ditarik"/totalBytes/badge di daftar link (audit 48-g-ui).
      void qc.invalidateQueries({ queryKey: qk.driveLinks });
    },
  });
}

/** Hapus link tersimpan (file di Drive tidak tersentuh). */
export function useDriveDeleteLink() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<{ ok: boolean; id: string }>(`/api/ingest/drive?id=${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      toast.success("Link Drive dihapus.");
      void qc.invalidateQueries({ queryKey: qk.driveLinks });
    },
  });
}

/** FR-1 — unggah ZIP bundle export Accurate; multipart (bukan JSON) sehingga
 * memakai fetch langsung di titik integrasi hooks ini (fetchJson memaksa
 * Content-Type application/json). */
export function useIngestUpload() {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/ingest/upload", { method: "POST", body: fd });
      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        body = null;
      }
      if (!res.ok) {
        const msg =
          body && typeof body === "object" && "error" in body
            ? String((body as { error: unknown }).error)
            : `Unggah gagal (HTTP ${res.status}).`;
        throw new Error(msg);
      }
      return body as BundleManifest;
    },
  });
}

export function useIngestCommit() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    // Task 54 — komit bertahap resumable: loop panggil /api/ingest/commit
    // sampai done. Tiap langkah ±30 dtk kerja server; cursor tersimpan di
    // server, jadi langkah yang terputus (timeout/koneksi) aman diteruskan.
    mutationFn: async (vars: {
      runBatchId: string;
      onProgress?: (p: CommitStepProgress) => void;
    }) => {
      const call = () =>
        fetchJson<IngestCommitResponse | CommitStepProgress>("/api/ingest/commit", {
          method: "POST",
          body: JSON.stringify({ runBatchId: vars.runBatchId }),
        });
      let res = await call();
      let failures = 0;
      while (!res.done) {
        vars.onProgress?.(res);
        try {
          res = await call();
          failures = 0;
        } catch (err) {
          // Langkah terputus — komit melanjutkan dari cursor saat dicoba lagi.
          // 3 kali gagal beruntun → berhenti jujur (toast error).
          if (++failures >= 3) throw err;
          await new Promise((resolve) => setTimeout(resolve, 3000));
        }
      }
      return res;
    },
    onSuccess: (out) => {
      toast.success(
        `Snapshot ${out.periodKey} terkomit (${out.rowCount.toLocaleString("id-ID")} baris)${out.supersededPrevious ? " — periode lama ditandai SUPERSEDED" : ""}.`,
      );
      invalidateAll();
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Gagal mengkomit snapshot."),
  });
}

export function useSeedDemo() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: () => fetchJson<{ created: { periodKey: string; snapshotId: string; rowCount: number }[] }>("/api/admin/seed-demo", { method: "POST" }),
    onSuccess: (out) => {
      toast.success(`Demo seed selesai: ${out.created.map((c) => c.periodKey).join(", ")}.`);
      invalidateAll();
    },
  });
}

export function useCreateCase() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (body: CreateCaseRequest) =>
      fetchJson<{ case: FollowUpCaseDto }>("/api/followup", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("Kasus follow-up dibuat (status PENDING).");
      invalidateAll();
    },
  });
}

export function useCaseEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CaseEventRequest }) =>
      fetchJson<{ case: FollowUpCaseDto; event: FollowUpEventDto }>(`/api/followup/${id}/events`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (_out, vars) => {
      toast.success(`Status kasus diubah ke ${vars.body.toStatus}.`);
      void qc.invalidateQueries({ queryKey: ["followup"] });
      void qc.invalidateQueries({ queryKey: qk.overview });
    },
  });
}

export function useUpdateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      fetchJson<{ ok: boolean }>(`/api/followup/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("Kasus diperbarui.");
      void qc.invalidateQueries({ queryKey: ["followup"] });
    },
  });
}

export function useCreatePic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { outletCode: string; picName: string; waNumber?: string }) =>
      fetchJson<{ pic: OutletPICDto }>("/api/pics", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("PIC ditambahkan.");
      void qc.invalidateQueries({ queryKey: qk.pics });
    },
  });
}

export function useSaveSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { tanggalHDefault?: number; ambangAcrDefault?: number }) =>
      fetchJson<{ settings: SettingsDto }>("/api/settings", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: (out) => {
      toast.success(
        `Setting disimpan — H default ${out.settings.tanggalHDefault}, ambang ACR default ${out.settings.ambangAcrDefault}%.`,
      );
      void qc.invalidateQueries({ queryKey: qk.settings });
    },
  });
}

export function useDeleteSnapshot() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<{ ok: boolean; id: string; periodKey: string }>(`/api/snapshots/${id}`, {
        method: "DELETE",
      }),
    onSuccess: (out) => {
      toast.success(`Snapshot periode ${out.periodKey} dihapus.`);
      invalidateAll();
    },
  });
}

/** Task 54: hapus run dari Riwayat (run demo/uji menumpuk). Server menolak
 *  run yang masih punya snapshot / sedang dirakit job agent — pesan jujur. */
export function useDeleteRun() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<{ ok: boolean; id: string; periodKey: string }>(`/api/runs/${id}`, {
        method: "DELETE",
      }),
    onSuccess: (out) => {
      toast.success(`Run periode ${out.periodKey} dihapus dari riwayat.`);
      invalidateAll();
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Gagal menghapus run."),
  });
}

// ---------- Agent lokal "Python di Laptop" (Task 51) ----------

/** Papan agent: online/offline + job aktif + riwayat. Poll lebih rapat saat
 *  ada job aktif supaya kemajuan terasa live. */
export function useAgentStatus(activeJobId: string | null) {
  return useQuery({
    queryKey: qk.agentStatus,
    queryFn: () => fetchJson<AgentStatusDto>("/api/agent"),
    refetchInterval: activeJobId ? 2_500 : 8_000,
  });
}

/** Detail satu job agent — polling hanya selama job masih berjalan. */
export function useAgentJob(id: string | null) {
  return useQuery({
    queryKey: qk.agentJob(id ?? "-"),
    queryFn: () => fetchJson<{ job: AgentJobDto }>(`/api/agent/jobs/${id}`),
    enabled: Boolean(id),
    select: (d) => d.job,
    refetchInterval: (query) => {
      const st = query.state.data?.job?.status;
      return st === "QUEUED" || st === "RUNNING" || st === "FINALIZING" ? 2_500 : false;
    },
  });
}

/** Buat job: agent laptop yang akan menarik file Drive + memproses via
 *  engine FastAPI lokal, lalu mengunggah hasil — web tinggal menampilkan. */
export function useAgentCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      ids: string[]; periodKey: string; tanggalH: number; ambangAcrPct: number; bundleName?: string;
    }) =>
      fetchJson<{ job: AgentJobDto }>("/api/agent", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (out) => {
      toast.success(
        `Job dikirim ke papan agent — python di laptop akan menjemputnya (job ${out.job.id.slice(0, 8)}…).`,
      );
      void qc.invalidateQueries({ queryKey: qk.agentStatus });
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal membuat job agent."),
  });
}

/** Batalkan job: QUEUED langsung batal; RUNNING dihentikan agent pada laporan berikutnya. */
export function useAgentCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<{ job: AgentJobDto }>(`/api/agent/jobs/${id}`, {
        method: "POST",
        body: JSON.stringify({ action: "cancel" }),
      }),
    onSuccess: () => {
      toast.success("Job agent dibatalkan.");
      void qc.invalidateQueries({ queryKey: qk.agentStatus });
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal membatalkan job."),
  });
}
