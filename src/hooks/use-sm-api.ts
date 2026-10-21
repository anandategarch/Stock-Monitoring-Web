// Semua akses data klien lewat hooks ini (TanStack Query) — satu titik integrasi
// untuk seluruh tab. Subagent UI WAJIB memakai hooks ini, tidak fetch sendiri.
"use client";

import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  AuditLogDto, BundleManifest, CreateCaseRequest, DrilldownResponse, DqIssueDto, EngineHealth,
  FollowUpCaseDto, FollowUpEventDto, IngestCommitResponse, IngestProcessResponse,
  LaporanResponse, NominalResponse, OutletPICDto, OverviewResponse, PivotResponse,
  PoResponse, RunDetail, RunSummary, SelisihInResponse, SettingsDto, SnapshotSummary,
  DeviasiResponse, RestoRef, CaseEventRequest,
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
    mutationFn: (body: { runBatchId: string }) =>
      fetchJson<IngestCommitResponse>("/api/ingest/commit", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (out) => {
      toast.success(
        `Snapshot ${out.periodKey} terkomit (${out.rowCount.toLocaleString("id-ID")} baris)${out.supersededPrevious ? " — periode lama ditandai SUPERSEDED" : ""}.`,
      );
      invalidateAll();
    },
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
