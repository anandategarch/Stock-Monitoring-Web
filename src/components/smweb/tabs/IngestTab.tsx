// Tab 🚀 Proses & Ingest — alur Pratinjau → Komit (FR-3/FR-4).
// Dua jalur (kontrak §5, Task 55):
//   • PRODUKSI — agent "Python di Laptop": pilih folder kanonik config.json
//     di bawah → agent menyalin folder export dari DISK LOKAL (RootPath,
//     mis. C:\KERJA\1. RESTO\9.NEW QUERY\) dan memprosesnya lewat engine
//     FastAPI lokal → hasil unggah → pratinjau → Komit. Jalur unggah
//     ZIP/Google Drive KE SERVER sudah DIHAPUS (permintaan user — serverless
//     Vercel memang tidak punya engine produksi).
//   • DEMO — engine sintetis deterministik untuk melatih alur.
// Hasil run selalu PRATINJAU dulu — snapshot periode hanya tersimpan setelah
// menekan KOMIT (FR-4: tidak pernah menimpa snapshot lama diam-diam).
"use client";

import { useEffect, useRef, useState } from "react";
import {
  Ban, CheckCircle2, Clock, Database, FileWarning, FolderOpen, Laptop, Loader2,
  PackageOpen, Play, Rocket, Save, Send, Trash2, Wifi, WifiOff, XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  useAgentCancelJob, useAgentCreateJob, useAgentJob, useAgentStatus,
  useDeleteRun, useEngineHealth, useIngestCommit, useIngestProcess, useRunDetail, useRuns, useSettings,
} from "@/hooks/use-sm-api";
import { CANONICAL_FOLDERS } from "@/lib/canonical-folders";
import type { AgentJobDto } from "@/lib/types";
import { useSmStore } from "@/store/use-sm-store";
import { EmptyState } from "@/components/smweb/empty-state";
import { DqSeverityBadge, RunStatusBadge } from "@/components/smweb/badges";
import { fmtDateTime, fmtInt, fmtRp, fmtSignedQty, periodLabel, signedQtyClass } from "@/lib/format";
import { toast } from "sonner";

type EngineMode = "demo" | "bundle";

// Default pilihan folder = folder yang DIBACA engine desktop v3.9.71
// ("3. 42.15" dilewati — data 42.15 masuk lewat sisi Kirim saja).
const DEFAULT_FOLDER_SEL: Record<string, boolean> = Object.fromEntries(
  CANONICAL_FOLDERS.map((f) => [f.folderKey, f.dibaca]),
);

export function IngestTab() {
  const setActiveTab = useSmStore((s) => s.setActiveTab);
  const [mode, setMode] = useState<EngineMode>("demo");
  const [periodKey, setPeriodKey] = useState("2026-10");
  const [tanggalH, setTanggalH] = useState("25");
  const [ambang, setAmbang] = useState("80");
  const [bundleName, setBundleName] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  // Label kemajuan komit bertahap (Task 54) — dipakai di tombol Komit Snapshot.
  const [commitStage, setCommitStage] = useState<string | null>(null);
  // Pilihan folder kanonik untuk job agent (Task 55) — persist per browser
  // supaya centangan user tidak hilang tiap reload.
  const [folderSel, setFolderSel] = useState<Record<string, boolean>>(DEFAULT_FOLDER_SEL);
  // Agent "Python di Laptop" (Task 51): job aktif dilacak id-nya supaya UI
  // tetap menampilkan kemajuan walau halaman dimuat ulang (status punya activeJob).
  const [agentJobId, setAgentJobId] = useState<string | null>(null);
  const agentStatusQuery = useAgentStatus(agentJobId);
  const agentCreate = useAgentCreateJob();
  const agentCancel = useAgentCancelJob();
  const agentJob = useAgentJob(agentJobId).data ?? null;
  const agentOnline = agentStatusQuery.data?.online === true;

  const process = useIngestProcess();
  const commit = useIngestCommit();
  const runDelete = useDeleteRun();
  const engineHealthQuery = useEngineHealth();
  const embedAvail = engineHealthQuery.data?.embedded?.available === true;
  const { data: runsData, isPending: runsPending, refetch: refetchRuns } = useRuns();
  const runList = runsData?.runs ?? [];
  const {
    data: detail, isPending: detailPending, error: detailError, refetch: refetchDetail,
  } = useRunDetail(selectedRunId);
  const { data: settingsData } = useSettings();
  const settingsApplied = useRef(false);

  const selectedFolders = CANONICAL_FOLDERS.filter((f) => folderSel[f.folderKey]);
  const selectedCount = selectedFolders.length;

  useEffect(() => {
    // FR-80: default TANGGAL H & AMBANG dari tab Config (Setting) — diterapkan
    // SEKALI saat settings termuat, tanpa menimpa edit user (audit 48-g-ui).
    if (!settingsApplied.current && settingsData) {
      settingsApplied.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sinkronisasi SEKALI dari data async ke state form (guard ref; pola Task 54, aman)
      setTanggalH(String(settingsData.settings.tanggalHDefault));
      setAmbang(String(settingsData.settings.ambangAcrDefault));
    }
  }, [settingsData]);

  // Task 54/55: mode engine terakhir diingat (localStorage) — mode "demo"
  // jangan menyala diam-diam lagi setelah user memakai Produksi. Pilihan
  // folder kanonik juga diingat. Gagal baca/tulis → abaikan diam-diam.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("smweb-ingest-mode");
      if (saved === "bundle" || saved === "demo")
        // eslint-disable-next-line react-hooks/set-state-in-effect -- restore preferensi sekali saat mount (data async localStorage)
        setMode(saved);
      const savedFolders = window.localStorage.getItem("smweb-folder-sel");
      if (savedFolders) {
        const parsed = JSON.parse(savedFolders) as Record<string, boolean>;
        if (parsed && typeof parsed === "object")
          setFolderSel((prev) => ({ ...prev, ...parsed }));
      }
    } catch {
      /* localStorage tak tersedia — pakai default */
    }
  }, []);
  const setModePersisted = (next: EngineMode) => {
    setMode(next);
    try {
      window.localStorage.setItem("smweb-ingest-mode", next);
    } catch {
      /* abaikan */
    }
  };
  const toggleFolder = (key: string, on: boolean) => {
    setFolderSel((prev) => {
      const next = { ...prev, [key]: on };
      try {
        window.localStorage.setItem("smweb-folder-sel", JSON.stringify(next));
      } catch {
        /* abaikan */
      }
      return next;
    });
  };

  // Job aktif dari papan (mis. halaman dimuat ulang saat agent sedang bekerja)
  // → lanjutkan pelacakan agar kemajuan tetap tampil.
  useEffect(() => {
    const active = agentStatusQuery.data?.activeJob;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- adopsi job aktif dari server sekali (resume tracking pasca reload)
    if (active && !agentJobId) setAgentJobId(active.id);
  }, [agentStatusQuery.data?.activeJob, agentJobId]);

  // Selesai → otomatis buka pratinjau run-nya (hasil diproses di laptop, tampil di web).
  const agentDoneRef = useRef<string | null>(null);
  useEffect(() => {
    if (!agentJob || agentJob.status !== "COMPLETED" || !agentJob.runBatchId) return;
    if (agentDoneRef.current === agentJob.id) return;
    agentDoneRef.current = agentJob.id;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reaksi sekali-per-job saat status jadi COMPLETED (event-driven, bukan sinkronisasi render)
    setSelectedRunId(agentJob.runBatchId);
    void refetchRuns();
    toast.success(
      `Job agent selesai — run pratinjau ${(agentJob.resultMeta?.summary.rowCount ?? 0).toLocaleString("id-ID")} baris siap ditinjau lalu dikomit.`,
    );
  }, [agentJob, refetchRuns]);

  const runParamsOk = () => {
    const h = Number(tanggalH);
    const amb = Number(ambang);
    if (!Number.isInteger(h) || h < 1 || h > 31) {
      toast.error("TANGGAL H harus integer 1..31.");
      return null;
    }
    if (!Number.isInteger(amb) || amb < 1 || amb > 200) {
      toast.error("AMBANG ACR harus integer 1..200 (INV-9).");
      return null;
    }
    return { h, amb };
  };

  // Job agent: laptop menyalin folder kanonik dari disk lokal + engine lokal.
  const onAgentJob = () => {
    const ok = runParamsOk();
    if (!ok) return;
    if (selectedCount === 0) {
      toast.error("Centang minimal satu folder kanonik — itu yang disalin agent dari disk lokal.");
      return;
    }
    if (!agentOnline) {
      toast.warning(
        "Agent di laptop belum terlihat online — job tetap dibuat, tapi hanya akan diproses saat agent berjalan.",
      );
    }
    agentCreate.mutate(
      {
        folders: selectedFolders.map((f) => f.folderKey),
        periodKey,
        tanggalH: ok.h,
        ambangAcrPct: ok.amb,
        bundleName: bundleName || undefined,
      },
      { onSuccess: (out) => setAgentJobId(out.job.id) },
    );
  };

  const onAgentCancel = () => {
    if (agentJob) agentCancel.mutate(agentJob.id);
  };

  // Task 54: hapus run dari riwayat (demo/uji menumpuk). Run terpilih yang
  // terhapus → tutup pratinjaunya; run berkomit ditolak server dengan pesan
  // jujur (hapus snapshot-nya dulu di tab Konfigurasi).
  const onRunDelete = (runId: string) => {
    runDelete.mutate(runId, {
      onSuccess: () => {
        if (selectedRunId === runId) setSelectedRunId(null);
      },
    });
  };

  // Jalankan engine DEMO sintetis (latih alur — bukan data Accurate).
  const onProcess = () => {
    const ok = runParamsOk();
    if (!ok) return;
    process.mutate(
      { periodKey, tanggalH: ok.h, ambangAcrPct: ok.amb, bundleName: bundleName || undefined },
      {
        onSuccess: (out) => {
          setSelectedRunId(out.runBatchId);
          toast.success(
            `Run demo ${periodKey} selesai: ${out.summary.rowCount.toLocaleString("id-ID")} baris · ${out.summary.warningCount} warning — TINJAU lalu KOMIT (atau hapus bila hanya uji coba).`,
          );
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal memproses run."),
      },
    );
  };

  const onCommit = () => {
    if (!selectedRunId) return;
    // Task 54: komit bertahap resumable — kemajuan langkah tampil di tombol;
    // bila terputus di tengah, tekan Komit ulang: cursor tersimpan di server
    // dan komit melanjutkan sendiri dari tempat terakhir.
    commit.mutate(
      {
        runBatchId: selectedRunId,
        onProgress: (p) =>
          setCommitStage(
            p.phase === "rows"
              ? `Mengkomit… baris ${fmtInt(p.written)} / ${fmtInt(p.total)}`
              : p.phase === "po"
                ? `Mengkomit… PO ${p.written} / ${fmtInt(p.total)}`
                : p.phase === "finalize"
                  ? "Memverifikasi & mengaktifkan…"
                  : `Mengkomit… tahap ${p.phase}`,
          ),
      },
      { onSettled: () => setCommitStage(null) },
    );
  };

  const existingPeriodKeys = new Set(
    runList.filter((r) => r.committedAt).map((r) => r.periodKey),
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Rocket className="h-5 w-5 text-emerald-600" aria-hidden /> Proses &amp; Ingest
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Jalankan pipeline atas folder export Accurate. Data asli diproses oleh{" "}
          <strong>Python di laptop</strong> (agent): agent menyalin folder yang dicentang dari{" "}
          <strong>disk lokal</strong> (struktur RootPath desktop — mis. <code className="text-[11px]">C:\KERJA\1. RESTO\9.NEW QUERY\</code>),
          engine FastAPI lokal memprosesnya, hasilnya tampil di sini sebagai{" "}
          <strong>pratinjau</strong> — snapshot periode hanya tersimpan setelah kamu menekan{" "}
          <strong>Komit</strong> (FR-4: tidak pernah menimpa snapshot lama diam-diam).
        </p>
      </div>

      {/* Pilihan jalur */}
      <RadioGroup
        value={mode}
        onValueChange={(v) => setModePersisted(v === "bundle" ? "bundle" : "demo")}
        className="grid gap-3 sm:grid-cols-2"
        aria-label="Jalur proses"
      >
        <Label
          htmlFor="mode-bundle"
          className="rounded-xl border p-4 cursor-pointer has-[[data-state=checked]]:border-emerald-400 has-[[data-state=checked]]:bg-emerald-50/60 dark:has-[[data-state=checked]]:bg-emerald-500/10"
        >
          <div className="flex items-start gap-2.5">
            <RadioGroupItem value="bundle" id="mode-bundle" className="mt-1" />
            <div>
              <p className="text-sm font-semibold flex items-center gap-1.5">
                <Laptop className="h-4 w-4 text-muted-foreground" aria-hidden /> Produksi — via Laptop (data asli)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Agent di laptop menyalin folder export dari <strong>disk lokal</strong> lalu engine
                FastAPI lokal memproses pipeline asli v3.9.71 — bebas batas waktu serverless. Di
                laptop cukup <strong>dobel-klik <code className="text-[11px]">mulai-laptop.bat</code></strong>.
              </p>
            </div>
          </div>
        </Label>
        <Label
          htmlFor="mode-demo"
          className="rounded-xl border p-4 cursor-pointer has-[[data-state=checked]]:border-emerald-400 has-[[data-state=checked]]:bg-emerald-50/60 dark:has-[[data-state=checked]]:bg-emerald-500/10"
        >
          <div className="flex items-start gap-2.5">
            <RadioGroupItem value="demo" id="mode-demo" className="mt-1" />
            <div>
              <p className="text-sm font-semibold flex items-center gap-1.5">
                <FolderOpen className="h-4 w-4 text-muted-foreground" aria-hidden /> Demo (sintetis)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Data sintetis deterministik untuk melatih alur &amp; histori tren — bukan angka
                Accurate. Cocok untuk mencoba tombol-tombol tanpa laptop.
              </p>
            </div>
          </div>
        </Label>
      </RadioGroup>

      {mode === "bundle" ? (
        // ================= PANEL PRODUKSI (AGENT LAPTOP) =================
        <div className="rounded-xl border bg-card p-4 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-64 flex-1">
              <p className="text-sm font-medium flex items-center gap-2">
                <Laptop className="h-4 w-4" aria-hidden /> Proses via Python di Laptop (Agent)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Agent menjemput job ini, <strong>menyalin folder yang dicentang di bawah dari disk
                lokal</strong> (RootPath di laptop — sesuai tombol <em>Root Data</em> di launcher),
                lalu <strong>memproses engine FastAPI secara lokal</strong>. Hasilnya diunggah dan{" "}
                <strong>tampil di web ini</strong> (pratinjau + Komit di sini juga). Di laptop:{" "}
                <strong>dobel-klik <code className="text-[11px]">mulai-laptop.bat</code></strong>
                dari repo (Windows; <code className="text-[11px]">mulai-laptop.command</code> di
                macOS) — engine + agent nyala otomatis sekali klik (panduan:{" "}
                <code className="text-[11px]">docs/AGENT-LOCAL.md</code>).
              </p>
              {/* Alur 5 langkah — jawaban permanen untuk "terus aku tekan apa?". */}
              <p className="text-xs text-muted-foreground mt-2 rounded-lg bg-muted/50 px-3 py-2">
                <strong>Alur lengkap:</strong> ① centang folder di bawah → ② tekan{" "}
                <em>Kirim N Folder → Laptop</em> → ③ tunggu kartu job <strong>SELESAI</strong>{" "}
                (agent menyalin file dari disk C + engine laptop memproses, otomatis) →{" "}
                ④ pratinjau run terbuka sendiri di panel bawah → tinjau lalu tekan{" "}
                <strong>Komit Snapshot</strong> → ⑤ data periode siap di semua tab analisis
                (Pivot, Deviasi, Selisih IN, PO, Nominal, Follow-Up, Laporan).
                <strong> Tidak ada tombol lain yang wajib ditekan — setelah Komit, selesai.</strong>
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0" aria-live="polite">
              {agentStatusQuery.isPending ? (
                <Skeleton className="h-6 w-36" />
              ) : agentOnline ? (
                <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40">
                  <Wifi className="h-3 w-3 mr-1" aria-hidden /> AGENT ONLINE
                  {agentStatusQuery.data?.agentName ? ` · ${agentStatusQuery.data.agentName}` : ""}
                </Badge>
              ) : (
                <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
                  <WifiOff className="h-3 w-3 mr-1" aria-hidden /> AGENT OFFLINE
                </Badge>
              )}
            </div>
          </div>

          {agentOnline && agentStatusQuery.data?.engine ? (
            <p className="text-xs text-muted-foreground">
              Engine di laptop: <strong>{String(agentStatusQuery.data.engine.engineName ?? "?")}</strong>{" "}
              v{String(agentStatusQuery.data.engine.engineVersion ?? "?")} · definisi{" "}
              {String(agentStatusQuery.data.engine.definitionVersion ?? "?")} · kontrak{" "}
              {String(agentStatusQuery.data.engine.contractVersion ?? "?")} — dilaporkan agent
              ({fmtDateTime(agentStatusQuery.data.lastSeenAt ?? "")}).
            </p>
          ) : null}

          {/* Pilihan folder kanonik (14 folder config.json desktop) */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium">
                Folder export yang disalin agent dari disk lokal
                <span className="ml-2 text-muted-foreground font-normal">
                  ({selectedCount} dari {CANONICAL_FOLDERS.length} tercentang)
                </span>
              </p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    const all = Object.fromEntries(CANONICAL_FOLDERS.map((f) => [f.folderKey, true]));
                    setFolderSel(all);
                    try {
                      window.localStorage.setItem("smweb-folder-sel", JSON.stringify(all));
                    } catch {
                      /* abaikan */
                    }
                  }}
                >
                  Centang semua
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    setFolderSel(DEFAULT_FOLDER_SEL);
                    try {
                      window.localStorage.setItem("smweb-folder-sel", JSON.stringify(DEFAULT_FOLDER_SEL));
                    } catch {
                      /* abaikan */
                    }
                  }}
                >
                  Standar (13)
                </Button>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto nice-scroll rounded-lg border divide-y">
              {CANONICAL_FOLDERS.map((f) => {
                const checked = folderSel[f.folderKey] === true;
                return (
                  <div key={f.folderKey} className="flex items-center gap-3 px-3 py-2">
                    <Checkbox
                      id={`folder-${f.folderKey}`}
                      checked={checked}
                      onCheckedChange={(v) => toggleFolder(f.folderKey, v === true)}
                      aria-label={`Ikut sertakan folder ${f.folderName}`}
                    />
                    <div className="min-w-0 flex-1">
                      <Label
                        htmlFor={`folder-${f.folderKey}`}
                        className="cursor-pointer text-sm font-medium truncate block"
                      >
                        {f.folderName}
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        kunci config: <code className="text-[11px]">{f.folderKey}</code>
                        {!f.dibaca ? " · tidak dibaca engine v3.9.71 (centang hanya bila perlu)" : ""}
                      </p>
                    </div>
                    {f.dibaca ? (
                      <Badge variant="secondary">DIBACA</Badge>
                    ) : (
                      <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
                        DILEWATI
                      </Badge>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Judul folder harus persis sama dengan yang ada di RootPath laptop. Folder yang tidak
              ditemukan dilaporkan jujur oleh agent (job tetap jalan untuk folder lain).
            </p>
          </div>

          {agentJob ? (
            <AgentJobCard
              job={agentJob}
              onCancel={onAgentCancel}
              cancelPending={agentCancel.isPending}
            />
          ) : null}
        </div>
      ) : (
        // ================= PANEL DEMO =================
        <div className="rounded-xl border bg-card p-4 space-y-2">
          <p className="text-sm font-medium flex items-center gap-2">
            <PackageOpen className="h-4 w-4" aria-hidden /> Engine demo sintetis
          </p>
          <p className="text-xs text-muted-foreground">
            Run demo menghasilkan bundle sintetis deterministik (kontrak §4) — bukan angka
            Accurate. Gunakan untuk melatih alur pratinjau → komit dan mengisi histori tren;
            hapus lewat tombol 🗑 bila hanya uji coba.
            {!engineHealthQuery.data?.reachable && embedAvail
              ? " Engine service :3030 tidak terjangkau — server memakai fallback EMBEDDED."
              : ""}
          </p>
        </div>
      )}

      {/* Form run */}
      <div className="rounded-xl border bg-card p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
        <div className="space-y-1.5">
          <Label htmlFor="period">Periode (YYYY-MM)</Label>
          <Input
            id="period"
            value={periodKey}
            onChange={(e) => setPeriodKey(e.target.value)}
            placeholder="2026-10"
            inputMode="numeric"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tanggalH">TANGGAL H (cut-off)</Label>
          <Input
            id="tanggalH"
            type="number"
            min={1}
            max={31}
            value={tanggalH}
            onChange={(e) => setTanggalH(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ambang">AMBANG ACR (%)</Label>
          <Input
            id="ambang"
            type="number"
            min={1}
            max={200}
            value={ambang}
            onChange={(e) => setAmbang(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bundle">Label run (opsional)</Label>
          <Input
            id="bundle"
            value={bundleName}
            onChange={(e) => setBundleName(e.target.value)}
            placeholder={mode === "bundle" ? "mis. Oktober — KERJA" : "mis. Demo Oktober"}
          />
        </div>
        {mode === "bundle" ? (
          <Button
            size="lg"
            onClick={onAgentJob}
            disabled={
              agentCreate.isPending ||
              selectedCount === 0 ||
              (agentJob !== null && ["QUEUED", "RUNNING", "FINALIZING"].includes(agentJob.status))
            }
            className="gap-2"
          >
            {agentCreate.isPending ? (
              "Membuat job…"
            ) : (
              <>
                <Send className="h-4 w-4" aria-hidden /> Kirim {selectedCount} Folder → Laptop
              </>
            )}
          </Button>
        ) : (
          <Button size="lg" onClick={onProcess} disabled={process.isPending} className="gap-2">
            {process.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Memproses…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" aria-hidden /> Jalankan Proses (Demo)
              </>
            )}
          </Button>
        )}
        <p className="sm:col-span-2 lg:col-span-5 text-xs text-muted-foreground">
          {mode === "bundle" ? (
            <>
              Run memakai <strong>pipeline asli Stock-Monitoring v3.9.71</strong> (0-rewrite) di laptop —
              angka = angka desktop. Komit run agent memakai hasil tersimpan di server (tanpa
              memanggil ulang engine).
            </>
          ) : (
            <>
              Engine demo menghasilkan data sintetis deterministik (kontrak §4) — bukan angka
              Accurate. Data asli? Pakai jalur <em>Produksi — via Laptop</em> di atas.
            </>
          )}
        </p>
      </div>

      {/* Riwayat run */}
      <div className="rounded-xl border bg-card p-4">
        <p className="text-sm font-medium mb-3 flex items-center gap-2">
          <Database className="h-4 w-4" aria-hidden /> Riwayat run — pilih untuk pratinjau
        </p>
        {runsPending ? (
          <Skeleton className="h-24" />
        ) : runList.length === 0 ? (
          <p className="text-sm text-muted-foreground">Belum ada run. Jalankan proses pertamamu di atas.</p>
        ) : (
          <div className="max-h-48 overflow-y-auto nice-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Periode</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead>Engine</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Komit?</TableHead>
                  <TableHead>Waktu</TableHead>
                  <TableHead className="text-right">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runList.map((r) => (
                  <TableRow
                    key={r.id}
                    className={selectedRunId === r.id ? "bg-muted/60" : "cursor-pointer"}
                    onClick={() => setSelectedRunId(r.id)}
                  >
                    <TableCell className="whitespace-nowrap font-medium">{r.periodKey}</TableCell>
                    <TableCell className="max-w-40 truncate">{r.bundleName ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={r.engineKind === "production" ? "border-emerald-400 text-emerald-700 dark:text-emerald-300" : ""}>
                        {r.engineKind === "production" ? "PRODUKSI" : "demo"}
                      </Badge>
                    </TableCell>
                    <TableCell><RunStatusBadge status={r.status} /></TableCell>
                    <TableCell>
                      {r.committedAt ? (
                        <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40">
                          <CheckCircle2 className="h-3 w-3 mr-1" aria-hidden /> Komit
                        </Badge>
                      ) : (
                        <Badge variant="outline">Pratinjau</Badge>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs">{fmtDateTime(r.startedAt)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRunId(r.id);
                          }}
                        >
                          Pratinjau
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-8 w-8 text-muted-foreground hover:text-rose-600 dark:hover:text-rose-400"
                              aria-label={`Hapus run periode ${r.periodKey} dari riwayat`}
                              title={
                                r.committedAt
                                  ? "Run berkomit — hapus snapshot-nya dulu di tab Konfigurasi"
                                  : "Hapus run ini dari riwayat"
                              }
                              disabled={runDelete.isPending}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Trash2 className="h-4 w-4" aria-hidden />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Hapus run {r.periodKey}{r.bundleName ? ` “${r.bundleName}”` : ""} dari riwayat?
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                Pratinjau, manifest file, isu DQ, log, dan hasil agent run ini ikut
                                terhapus. Snapshot yang sudah dikomit TIDAK tersentuh — run
                                berkomit akan ditolak sampai snapshot-nya dihapus di tab
                                Konfigurasi. Tindakan ini tidak bisa dibatalkan.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Batal</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-rose-600 hover:bg-rose-700 text-white"
                                onClick={() => onRunDelete(r.id)}
                              >
                                Hapus Run
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Pratinjau run terpilih */}
      {selectedRunId ? (
        detailPending ? (
          <Skeleton className="h-64" />
        ) : !detail ? (
          <EmptyState
            icon={FileWarning}
            title="Gagal memuat pratinjau run"
            description={
              detailError instanceof Error
                ? detailError.message
                : "Pilih ulang run dari riwayat di atas."
            }
            action={
              <Button variant="outline" onClick={() => void refetchDetail()}>
                Coba Lagi
              </Button>
            }
          />
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl border bg-card p-4 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <RunStatusBadge status={detail.run.status} />
                  <Badge variant="secondary">{detail.run.periodKey} — {periodLabel(detail.run.periodKey)}</Badge>
                  <Badge variant="outline">definisi {detail.run.definitionVersion}</Badge>
                  <Badge variant="outline">H {detail.run.params.tanggalH} · ambang {detail.run.params.ambangAcrPct}%</Badge>
                  <Badge variant="outline" className={detail.run.engineKind === "production" ? "border-emerald-400 text-emerald-700 dark:text-emerald-300" : ""}>
                    {detail.run.engineKind === "production" ? "engine PRODUKSI (pipeline asli)" : `${detail.run.engineKind} engine v${detail.run.engineVersion ?? "?"}`}
                  </Badge>
                </div>
                {detail.run.committedAt ? (
                  <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" aria-hidden /> Sudah dikomit {fmtDateTime(detail.run.committedAt)}
                  </Badge>
                ) : (
                  <Button
                    onClick={onCommit}
                    disabled={commit.isPending}
                    className="gap-2"
                    size="lg"
                  >
                    {commit.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {commitStage ?? "Mengkomit…"}
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" aria-hidden /> Komit Snapshot
                      </>
                    )}
                  </Button>
                )}
              </div>

              {existingPeriodKeys.has(detail.run.periodKey) && !detail.run.committedAt ? (
                <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                  <XCircle className="h-3.5 w-3.5" aria-hidden />
                  Periode {detail.run.periodKey} sudah punya snapshot aktif — komit akan menandai snapshot lama
                  SUPERSEDED (tetap tersimpan, FR-24) dan tercatat di AuditLog.
                </p>
              ) : null}

              {/* Ringkasan */}
              {detail.run.summary ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-sm">
                  <SummaryChip label="Baris" value={fmtInt(detail.run.summary.rowCount)} />
                  <SummaryChip label="Resto × Barang" value={`${detail.run.summary.restoCount} × ${detail.run.summary.itemCount}`} />
                  <SummaryChip label="Skip file" value={fmtInt(detail.run.summary.skipFileCount)} tone="amber" />
                  <SummaryChip label="Warning" value={fmtInt(detail.run.summary.warningCount)} tone="amber" />
                  <SummaryChip label="Nominal" value={fmtRp(detail.run.summary.nominalTotal)} tone={detail.run.summary.nominalTotal < 0 ? "rose" : "emerald"} />
                  <SummaryChip label="Durasi" value={detail.run.durationMs !== null ? `${(detail.run.durationMs / 1000).toFixed(2)}s` : "—"} />
                </div>
              ) : null}
            </div>

            <div className="grid lg:grid-cols-2 gap-4">
              {/* Manifest file */}
              <div className="rounded-xl border bg-card p-4">
                <p className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Database className="h-4 w-4" aria-hidden /> Manifest file sumber (pratinjau per folder)
                </p>
                <ScrollArea className="h-64 nice-scroll">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Folder</TableHead>
                        <TableHead>File</TableHead>
                        <TableHead className="text-right">Baris</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.sourceFiles.map((f) => (
                        <TableRow key={f.id}>
                          <TableCell className="whitespace-nowrap font-mono text-xs">{f.folderKey}</TableCell>
                          <TableCell className="max-w-48 truncate">{f.fileName}</TableCell>
                          <TableCell className="text-right cell-num">{fmtInt(f.rowCount)}</TableCell>
                          <TableCell>
                            {f.status === "OK" ? (
                              <Badge variant="secondary">OK</Badge>
                            ) : f.status === "SKIP" ? (
                              <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">SKIP</Badge>
                            ) : (
                              <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">WARNING</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </div>

              {/* DQ issues */}
              <div className="rounded-xl border bg-card p-4">
                <p className="text-sm font-medium mb-3 flex items-center gap-2">
                  <FileWarning className="h-4 w-4" aria-hidden /> Kualitas data ({detail.dqIssues.length} isu)
                </p>
                <ScrollArea className="h-64 nice-scroll">
                  <div className="space-y-2 pr-2">
                    {detail.dqIssues.map((d) => (
                      <div key={d.id} className="flex items-start gap-2 text-xs border-b pb-2 last:border-0">
                        <DqSeverityBadge severity={d.severity} />
                        <div>
                          <p className="font-mono">{d.code}</p>
                          <p className="text-muted-foreground">{d.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </div>

            {/* Log real-time */}
            <div className="rounded-xl border bg-card p-4">
              <p className="text-sm font-medium mb-3">Log pipeline ({detail.logs.length} baris — kontrak §82b:
                jumlah WARNING = {detail.run.summary?.warningCount ?? 0})</p>
              <ScrollArea className="h-56 nice-scroll">
                <div className="font-mono text-xs space-y-0.5 pr-2">
                  {detail.logs.map((l, i) => (
                    <p
                      key={i}
                      className={
                        l.level === "WARNING"
                          ? "text-amber-600 dark:text-amber-400"
                          : l.level === "ERROR"
                            ? "text-rose-600 dark:text-rose-400"
                            : "text-muted-foreground"
                      }
                    >
                      <span className="text-foreground/70">[{l.ts.slice(11, 19)}]</span> {l.message}
                    </p>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </div>
        )
      ) : (
        <EmptyState
          icon={Database}
          title="Pilih run untuk pratinjau"
          description="Setelah job agent selesai (atau run demo dijalankan), pilih run dari riwayat — ringkasan, manifest file, isu kualitas data, dan log pipeline tampil di sini sebelum komit."
        />
      )}

      <div className="text-xs text-muted-foreground space-y-1">
        <p>
          Σ deviasi qty run: {detail?.run.summary ? (
            <span className={signedQtyClass(detail.run.summary.deviasiQtyTotal)}>
              {fmtSignedQty(detail.run.summary.deviasiQtyTotal)}
            </span>
          ) : "—"} — bertanda; minus = kekurangan (INV-2).
        </p>
        <p>
          Run agent dikomit dari hasil tersimpan di server (deterministik, FR-12); run demo dikomit
          dengan memanggil ulang engine demo. Kegagalan di tengah komit tidak pernah menyentuh
          snapshot lama (NFR-3) — tekan Komit ulang untuk melanjutkan dari cursor.
        </p>
      </div>
    </div>
  );
}

function SummaryChip({ label, value, tone }: { label: string; value: string; tone?: "amber" | "rose" | "emerald" }) {
  const toneClass =
    tone === "amber"
      ? "text-amber-600 dark:text-amber-400"
      : tone === "rose"
        ? "text-rose-600 dark:text-rose-400"
        : tone === "emerald"
          ? "text-emerald-600 dark:text-emerald-400"
          : "";
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className={`font-semibold cell-num ${toneClass}`}>{value}</p>
    </div>
  );
}

function AgentJobStatusBadge({ status }: { status: AgentJobDto["status"] }) {
  const emerald =
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40";
  if (status === "QUEUED") {
    return (
      <Badge variant="outline" className="gap-1 border-amber-400 text-amber-700 dark:text-amber-300">
        <Clock className="h-3 w-3" aria-hidden /> MENUNGGU AGENT
      </Badge>
    );
  }
  if (status === "RUNNING") {
    return (
      <Badge className={`gap-1 ${emerald}`}>
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> AGENT MEMPROSES
      </Badge>
    );
  }
  if (status === "FINALIZING") {
    return (
      <Badge className={`gap-1 ${emerald}`}>
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> MERAKIT DI SERVER
      </Badge>
    );
  }
  if (status === "COMPLETED") {
    return (
      <Badge className={`gap-1 ${emerald}`}>
        <CheckCircle2 className="h-3 w-3" aria-hidden /> SELESAI
      </Badge>
    );
  }
  if (status === "FAILED") {
    return (
      <Badge variant="outline" className="gap-1 border-rose-400 text-rose-700 dark:text-rose-300">
        <XCircle className="h-3 w-3" aria-hidden /> GAGAL
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1">
      <Ban className="h-3 w-3" aria-hidden /> DIBATALKAN
    </Badge>
  );
}

/** Kartu job agent live: kemajuan (progress + pesan), error jujur, ringkasan
 *  hasil saat selesai — pratinjau run terbuka otomatis di panel bawah. */
function AgentJobCard({
  job, onCancel, cancelPending,
}: {
  job: AgentJobDto;
  onCancel: () => void;
  cancelPending: boolean;
}) {
  const active = job.status === "QUEUED" || job.status === "RUNNING" || job.status === "FINALIZING";
  return (
    <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <AgentJobStatusBadge status={job.status} />
        <Badge variant="secondary">{job.periodKey} — {periodLabel(job.periodKey)}</Badge>
        <Badge variant="outline">H {job.tanggalH} · ambang {job.ambangAcrPct}%</Badge>
        <Badge variant="outline">{job.targets.length} folder disk lokal</Badge>
        {job.agentName ? (
          <Badge variant="outline" className="max-w-40 truncate">{job.agentName}</Badge>
        ) : null}
        <span className="text-xs text-muted-foreground">dibuat {fmtDateTime(job.createdAt)}</span>
        {active ? (
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto h-8 gap-1 text-muted-foreground hover:text-rose-600"
            onClick={onCancel}
            disabled={cancelPending || job.status === "FINALIZING"}
            aria-label="Batalkan job agent"
          >
            <Ban className="h-3.5 w-3.5" aria-hidden /> Batalkan
          </Button>
        ) : null}
      </div>
      {(job.status === "RUNNING" || job.status === "FINALIZING") && (
        <div className="space-y-1">
          <Progress value={job.progress} className="h-2" aria-label="Kemajuan job agent" />
          <p className="text-xs text-muted-foreground">
            {job.progress}% — {job.message ?? "bekerja…"}
          </p>
        </div>
      )}
      {job.status === "QUEUED" && job.message ? (
        <p className="text-xs text-muted-foreground animate-pulse">{job.message}</p>
      ) : null}
      {job.status === "COMPLETED" ? (
        <p className="text-xs text-emerald-700 dark:text-emerald-400 flex items-start gap-1.5">
          <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
          <span>
            {job.resultMeta?.summary
              ? `${fmtInt(job.resultMeta.summary.rowCount)} baris · ${fmtInt(job.resultMeta.summary.warningCount)} warning · engine ${((job.resultMeta.durationMs ?? 0) / 1000).toFixed(1)}s`
              : "Selesai"}{" "}
            — pratinjau run terbuka di panel bawah; tekan <strong>Komit Snapshot</strong> untuk
            menyimpannya permanen.
          </span>
        </p>
      ) : null}
      {job.status === "FAILED" && job.error ? (
        <p className="text-xs text-rose-700 dark:text-rose-400 flex items-start gap-1.5">
          <XCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden /> {job.error}
        </p>
      ) : null}
      {job.status === "CANCELLED" ? (
        <p className="text-xs text-muted-foreground">{job.error ?? "Job dibatalkan."}</p>
      ) : null}
    </div>
  );
}
