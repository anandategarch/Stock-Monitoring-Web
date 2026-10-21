// Tab 🚀 Proses & Ingest — paritas tab Proses desktop + alur Pratinjau → Komit (FR-1..5).
// Dua mode engine (kontrak §5): DEMO (sintetis :3030) dan PRODUKSI (pipeline asli
// v3.9.71, FastAPI :3031) — mode produksi mengunggah ZIP bundle export Accurate,
// divalidasi strukturnya (manifest per folder config.json — FR-1/FR-2), lalu
// diproses → pratinjau → Komit (FR-4: tidak pernah menimpa snapshot diam-diam).
"use client";

import { useEffect, useRef, useState, type InputHTMLAttributes } from "react";
import {
  AlertTriangle, Ban, CheckCircle2, Clock, Cloud, CloudDownload, Database, Eye, FileWarning, FolderOpen, FolderTree,
  Laptop, Loader2, PackageOpen, Play, Rocket, Save, Send, Trash2, UploadCloud, Wifi, WifiOff, XCircle,
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
  AlertDialogDescription, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  useAgentCancelJob, useAgentCreateJob, useAgentJob, useAgentStatus,
  useDriveDeleteLink, useDriveLinks, useDrivePull, useDriveSaveLink, useEngineHealth,
  useIngestCommit, useIngestProcess, useIngestUpload, useRunDetail, useRuns, useSettings,
} from "@/hooks/use-sm-api";
import { collectExcelFromFolder, MAX_FOLDER_BYTES, zipPickedFolder } from "@/lib/folder-pick";
import type { AgentJobDto, BundleManifest } from "@/lib/types";
import { useSmStore } from "@/store/use-sm-store";
import { EmptyState } from "@/components/smweb/empty-state";
import { DqSeverityBadge, RunStatusBadge } from "@/components/smweb/badges";
import { fmtDateTime, fmtInt, fmtQty, fmtRp, fmtSignedQty, periodLabel, signedQtyClass } from "@/lib/format";
import { toast } from "sonner";

type EngineMode = "demo" | "bundle";

// webkitdirectory/directory: atribut non-standar (boolean — hadir = aktif)
// untuk pemilih FOLDER: browser menyerahkan seluruh isi folder pilihan user,
// path relatif tiap file tersedia di File.webkitRelativePath.
const folderInputProps = {
  webkitdirectory: "",
  directory: "",
} as unknown as InputHTMLAttributes<HTMLInputElement>;

/** Ringkas daftar nama untuk peringatan manifest: 5 nama + hitungan sisanya. */
function clipList(items: string[], max = 5): string {
  return items.slice(0, max).join(", ") + (items.length > max ? ` … +${items.length - max} lainnya` : "");
}

export function IngestTab() {
  const setActiveTab = useSmStore((s) => s.setActiveTab);
  const [mode, setMode] = useState<EngineMode>("demo");
  const [periodKey, setPeriodKey] = useState("2026-10");
  const [tanggalH, setTanggalH] = useState("25");
  const [ambang, setAmbang] = useState("80");
  const [bundleName, setBundleName] = useState("");
  const [manifest, setManifest] = useState<BundleManifest | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [folderStage, setFolderStage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [driveUrl, setDriveUrl] = useState("");
  const [driveInclude, setDriveInclude] = useState<Record<string, boolean>>({});
  const [drivePendingAction, setDrivePendingAction] = useState<"process" | "preview" | null>(null);
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
  const upload = useIngestUpload();
  const driveLinksQuery = useDriveLinks();
  const driveSave = useDriveSaveLink();
  const drivePull = useDrivePull();
  const driveDelete = useDriveDeleteLink();
  const driveLinks = driveLinksQuery.data?.links ?? [];
  const includedDriveIds = driveLinks
    .filter((l) => driveInclude[l.id] !== false)
    .map((l) => l.id);
  // Jujur soal lingkungan: bila engine PRODUKSI tidak terjangkau (deploy
  // serverless Vercel tanpa engine FastAPI), user perlu tahu SEKARANG — bukan
  // nanti saat "Proses Bundle" gagal. Di sandbox/lokal kedua engine hidup →
  // catatan ini tidak muncul.
  const engineHealthQuery = useEngineHealth();
  const prodEngineDown = engineHealthQuery.data?.production?.reachable === false;
  const { data: runsData, isPending: runsPending, refetch: refetchRuns } = useRuns();
  const runList = runsData?.runs ?? [];
  const {
    data: detail, isPending: detailPending, error: detailError, refetch: refetchDetail,
  } = useRunDetail(selectedRunId);
  const { data: settingsData } = useSettings();
  const settingsApplied = useRef(false);

  useEffect(() => {
    // FR-80: default TANGGAL H & AMBANG dari tab Config (Setting) — diterapkan
    // SEKALI saat settings termuat, tanpa menimpa edit user (audit 48-g-ui).
    if (!settingsApplied.current && settingsData) {
      settingsApplied.current = true;
      setTanggalH(String(settingsData.settings.tanggalHDefault));
      setAmbang(String(settingsData.settings.ambangAcrDefault));
    }
  }, [settingsData]);

  // Job aktif dari papan (mis. halaman dimuat ulang saat agent sedang bekerja)
  // → lanjutkan pelacakan agar kemajuan tetap tampil.
  useEffect(() => {
    const active = agentStatusQuery.data?.activeJob;
    if (active && !agentJobId) setAgentJobId(active.id);
  }, [agentStatusQuery.data?.activeJob, agentJobId]);

  // Selesai → otomatis buka pratinjau run-nya (hasil diproses di laptop, tampil di web).
  const agentDoneRef = useRef<string | null>(null);
  useEffect(() => {
    if (!agentJob || agentJob.status !== "COMPLETED" || !agentJob.runBatchId) return;
    if (agentDoneRef.current === agentJob.id) return;
    agentDoneRef.current = agentJob.id;
    setSelectedRunId(agentJob.runBatchId);
    void refetchRuns();
    toast.success(
      `Job agent selesai — run pratinjau ${(agentJob.resultMeta?.summary.rowCount ?? 0).toLocaleString("id-ID")} baris siap ditinjau lalu dikomit.`,
    );
  }, [agentJob, refetchRuns]);

  const applyManifest = (out: BundleManifest, verb = "terunggah") => {
    setManifest(out);
    setBundleName(out.name);
    const missing = out.missingFolders.length;
    const msg =
      `Bundle "${out.name}" ${verb}: ${out.fileCount} file Excel · ${out.folders.length - missing}/${out.folders.length} folder dikenali${missing ? ` · ${missing} folder kosong/tidak ada` : ""}.`;
    if (missing > 0 || (out.skippedFiles?.length ?? 0) > 0) {
      toast.warning(msg);
    } else {
      toast.success(msg);
    }
  };

  const onPickFile = (file: File | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      toast.error("Pilih file .zip — bundle export Accurate yang di-zip (struktur 14 folder config.json).");
      return;
    }
    if (file.size > 400 * 1024 * 1024) {
      toast.error(`ZIP ${(file.size / 1048576).toFixed(0)} MB — di atas batas 400 MB (R-10). Zipping ulang per periode.`);
      return;
    }
    upload.mutate(file, {
      onSuccess: (out) => applyManifest(out),
      onError: (err) => toast.error(err instanceof Error ? err.message : "Unggah gagal."),
    });
  };

  // Pilih folder export LANGSUNG dari komputer (tanpa zip manual): browser
  // menyerahkan isi folder pilihan user → file Excel dibungkus ZIP otomatis
  // di sini (folder-pick.ts) → diunggah lewat jalur yang sama dengan ZIP manual
  // — server tak peduli ZIP dibuat siapa (satu jalur validasi FR-2).
  const onPickFolder = async (raw: File[]) => {
    if (raw.length === 0) return;
    setFolderStage("Memindai folder…");
    try {
      const scan = collectExcelFromFolder(raw);
      if (scan.files.length === 0) {
        toast.error(
          "Tidak ada file Excel (.xlsx/.xls/.xlsb) di folder itu — pilih folder export Accurate (struktur 14 folder config.json).",
        );
        return;
      }
      if (scan.totalBytes > MAX_FOLDER_BYTES) {
        toast.error(
          `Total file Excel ${Math.round(scan.totalBytes / 1024 / 1024)} MB — di atas batas aman 380 MB. Pisahkan per periode atau unggah sebagai ZIP.`,
        );
        return;
      }
      setFolderStage(
        `Membaca ${scan.files.length} file Excel (${(scan.totalBytes / 1024 / 1024).toFixed(1)} MB)…`,
      );
      const zip = await zipPickedFolder(scan, (done, total) => {
        setFolderStage(done === total ? "Membungkus ZIP…" : `Membaca file ${done}/${total}…`);
      });
      upload.mutate(zip, {
        onSuccess: (out) => applyManifest(out),
        onError: (err) => toast.error(err instanceof Error ? err.message : "Unggah gagal."),
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal membaca folder.");
    } finally {
      setFolderStage(null);
    }
  };

  // Google Drive: simpan link folder (dicek langsung oleh server), lalu tarik
  // file Excel-nya menjadi bundle — jalur validasi/manifest SAMA dengan ZIP
  // (FR-2); link tersimpan di database supaya diingat (“biar ingat”).
  const onDriveSave = () => {
    const u = driveUrl.trim();
    if (!u) {
      toast.error("Tempel link folder Drive dulu (drive.google.com/drive/folders/…).");
      return;
    }
    driveSave.mutate(u, {
      onSuccess: (out) => {
        toast.success(
          `Link tersimpan: folder “${out.link.folderName}”${out.link.folderKey ? ` — dikenali sebagai ${out.link.folderKey}` : " — nama TIDAK cocok template"} · ${out.link.fileCount} file Excel.`,
        );
        for (const w of out.warnings) toast.warning(w);
        setDriveUrl("");
      },
      onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal memeriksa link Drive."),
    });
  };

  // Satu jalur untuk dua aksi Drive: "process" (unduh file → bundle) dan
  // "preview" (listing Drive saja — Pratinjau Cepat, tanpa kuota serverless).
  // drivePendingAction memisahkan label spinner dua tombol yang berbagi
  // satu mutasi (isPending).
  const runDriveAction = (action: "process" | "preview") => {
    if (includedDriveIds.length === 0) {
      toast.error("Centang minimal satu link Drive yang mau ditarik.");
      return;
    }
    setDrivePendingAction(action);
    drivePull.mutate(
      { ids: includedDriveIds, action },
      {
        onSuccess: (out) =>
          action === "preview"
            ? applyManifest(out, "dipratinjau cepat (tanpa unduh)")
            : applyManifest(out, "ditarik dari Drive"),
        onError: (err) =>
          toast.error(
            err instanceof Error
              ? err.message
              : action === "preview"
                ? "Gagal mempratinjau folder Drive."
                : "Gagal menarik dari Drive.",
          ),
        onSettled: () => setDrivePendingAction(null),
      },
    );
  };
  const onDrivePull = () => runDriveAction("process");
  const onDrivePreview = () => runDriveAction("preview");

  // Kirim job ke papan agent: python di laptop menjemput, menarik file Drive
  // dan memproses via engine FastAPI lokal — hasil diunggah & tampil di sini.
  // Prasyarat sama dengan "Tarik" (link tersimpan dicentang) + parameter run di form bawah.
  const onAgentJob = () => {
    const h = Number(tanggalH);
    const amb = Number(ambang);
    if (!Number.isInteger(h) || h < 1 || h > 31) {
      toast.error("TANGGAL H harus integer 1..31.");
      return;
    }
    if (!Number.isInteger(amb) || amb < 1 || amb > 200) {
      toast.error("AMBANG ACR harus integer 1..200 (INV-9).");
      return;
    }
    if (includedDriveIds.length === 0) {
      toast.error("Centang minimal satu link Drive di atas — itu yang akan diproses agent di laptop.");
      return;
    }
    if (!agentOnline) {
      toast.warning(
        "Agent di laptop belum terlihat online — job tetap dibuat, tapi hanya akan diproses saat agent berjalan.",
      );
    }
    agentCreate.mutate(
      {
        ids: includedDriveIds,
        periodKey,
        tanggalH: h,
        ambangAcrPct: amb,
        bundleName: bundleName || undefined,
      },
      { onSuccess: (out) => setAgentJobId(out.job.id) },
    );
  };

  const onAgentCancel = () => {
    if (agentJob) agentCancel.mutate(agentJob.id);
  };

  const onProcess = () => {
    const h = Number(tanggalH);
    const amb = Number(ambang);
    if (!Number.isInteger(h) || h < 1 || h > 31) {
      toast.error("TANGGAL H harus integer 1..31.");
      return;
    }
    if (!Number.isInteger(amb) || amb < 1 || amb > 200) {
      toast.error("AMBANG ACR harus integer 1..200 (INV-9).");
      return;
    }
    if (mode === "bundle" && !manifest) {
      toast.error("Mode produksi: unggah ZIP bundle dulu sebelum memproses (FR-1).");
      return;
    }
    if (mode === "bundle" && manifest?.previewOnly) {
      toast.error(
        "Ini hanya pratinjau cepat — bundle tidak diunduh. Tekan “Tarik → Bundle” (di instalasi lokal) atau unggah ZIP untuk memproses.",
      );
      return;
    }
    process.mutate(
      mode === "bundle"
        ? {
            periodKey, tanggalH: h, ambangAcrPct: amb,
            bundleName: bundleName || manifest?.name,
            mode: "bundle", bundleId: manifest?.bundleId,
          }
        : { periodKey, tanggalH: h, ambangAcrPct: amb, bundleName: bundleName || undefined },
      {
        onSuccess: (out) => {
          setSelectedRunId(out.runBatchId);
          toast.success(
            `Run ${periodKey} selesai (${out.engineKind === "production" ? "engine PRODUKSI" : "engine demo"}): ${out.summary.rowCount.toLocaleString("id-ID")} baris · ${out.summary.warningCount} warning — TINJAU lalu KOMIT.`,
          );
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal memproses run."),
      },
    );
  };

  const onCommit = () => {
    if (!selectedRunId) return;
    commit.mutate({ runBatchId: selectedRunId });
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
          Jalankan pipeline atas bundle export Accurate. Mode <strong>produksi</strong> memakai engine
          FastAPI yang membungkus pipeline asli v3.9.71 apa adanya (0-rewrite, FR-10) — pilih{" "}
          <strong>folder export langsung</strong> (ZIP otomatis di browser), tarik lewat{" "}
          <strong>link Google Drive</strong>, kirim ke <strong>Python di laptop</strong> (agent),
          atau unggah ZIP bundle; mode <strong>demo</strong> memakai data sintetis deterministik. Hasil run menjadi{" "}
          <strong>pratinjau</strong> — snapshot periode hanya tersimpan setelah kamu menekan{" "}
          <strong>Komit</strong> (FR-4: tidak pernah menimpa snapshot lama diam-diam).
        </p>
      </div>

      {/* Pilihan mode engine */}
      <RadioGroup
        value={mode}
        onValueChange={(v) => setMode(v === "bundle" ? "bundle" : "demo")}
        className="grid gap-3 sm:grid-cols-2"
        aria-label="Mode engine"
      >
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
                Engine demo :3030 — data sintetis deterministik untuk melatih alur &amp; histori
                tren. Tanpa bundle.
              </p>
            </div>
          </div>
        </Label>
        <Label
          htmlFor="mode-bundle"
          className="rounded-xl border p-4 cursor-pointer has-[[data-state=checked]]:border-emerald-400 has-[[data-state=checked]]:bg-emerald-50/60 dark:has-[[data-state=checked]]:bg-emerald-500/10"
        >
          <div className="flex items-start gap-2.5">
            <RadioGroupItem value="bundle" id="mode-bundle" className="mt-1" />
            <div>
              <p className="text-sm font-semibold flex items-center gap-1.5">
                <PackageOpen className="h-4 w-4 text-muted-foreground" aria-hidden /> Produksi — bundle ZIP
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Engine FastAPI :3031 — pipeline asli v3.9.71 atas bundle export Accurate kamu
                (pilih folder langsung / Google Drive / unggah ZIP 14 folder, FR-1).
              </p>
            </div>
          </div>
        </Label>
      </RadioGroup>

      {/* Unggah bundle (mode produksi) */}
      {mode === "bundle" && (
        <div className="rounded-xl border bg-card p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium flex items-center gap-2">
                <UploadCloud className="h-4 w-4" aria-hidden /> Unggah bundle export Accurate
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Tiga cara: <strong>pilih folder</strong> export langsung dari komputer (ZIP otomatis
                di browser), <strong>link Google Drive</strong> (bagian bawah — tanpa unduh manual),
                atau file <strong>.zip</strong> yang sudah ada. Isi: 14 folder sesuai config.json
                (2. 22.05 · 4. 42.05 · dst.) — batas 400 MB. Struktur divalidasi per folder;
                folder kosong dilaporkan jujur (tetap bisa diproses).
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                e.target.value = ""; // pilih ulang file yang sama tetap memicu onChange
                onPickFile(f);
              }}
            />
            <input
              ref={folderInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => {
                const raw = Array.from(e.target.files ?? []);
                e.target.value = "";
                void onPickFolder(raw);
              }}
              {...folderInputProps}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => folderInputRef.current?.click()}
                disabled={upload.isPending || Boolean(folderStage)}
                className="gap-2"
              >
                {folderStage ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Menyiapkan…
                  </>
                ) : upload.isPending ? (
                  "Mengunggah…"
                ) : (
                  <>
                    <FolderTree className="h-4 w-4" aria-hidden /> Pilih Folder…
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={upload.isPending || Boolean(folderStage)}
                className="gap-2"
              >
                {upload.isPending ? "Mengunggah…" : (
                  <>
                    <UploadCloud className="h-4 w-4" aria-hidden /> Pilih ZIP…
                  </>
                )}
              </Button>
            </div>
          </div>

          {(folderStage || upload.isPending) && (
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              {folderStage ?? "Mengunggah ZIP ke server…"}
            </p>
          )}

          {/* Sumber Google Drive — link tersimpan “biar ingat” (FR-1) */}
          <div className="border-t pt-3 space-y-3">
            <div>
              <p className="text-sm font-medium flex items-center gap-2">
                <Cloud className="h-4 w-4" aria-hidden /> Ambil dari Google Drive — tanpa unduh &amp; ZIP manual
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Tempel link folder Drive (satu link per folder export, mis. “1. DEVIASI WEEKLY",
                atau satu link folder induk — subfolder ikut dipindai, maks 16) — server yang
                menarik file Excel-nya langsung, lalu memvalidasi lewat jalur yang sama dengan
                ZIP (FR-2). Syarat: folder dibagikan “Siapa saja yang memiliki link · Viewer”.
                Link tersimpan di sini supaya diingat — centang lalu Tarik.
              </p>
            </div>
            {prodEngineDown && (
              <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5 rounded-lg border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/10 px-3 py-2">
                <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                <span>
                  Instansi ini berjalan <strong>serverless tanpa engine FastAPI</strong> — link bisa
                  disimpan &amp; bundle bisa ditarik (maks ±60 dtk &amp; kuota disk sementara), tetapi{" "}
                  <strong>Proses Bundle data asli di server ini</strong> tidak bisa dijalankan.
                  Solusi tanpa batas serverless: <strong>Proses via Python di Laptop</strong> di
                  seksi bawah — di laptop cukup <strong>dobel-klik <code className="text-[11px]">mulai-laptop.bat</code></strong>
                  (repo), lalu kirim folder dari sini: laptop memproses, hasil tampil &amp; dikomit
                  di sini; atau jalankan penuh dari instalasi lokal (sandbox/PC) tempat engine
                  :3031 hidup.
                </span>
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Input
                className="flex-1 min-w-64"
                placeholder="https://drive.google.com/drive/folders/…"
                value={driveUrl}
                onChange={(e) => setDriveUrl(e.target.value)}
                inputMode="url"
                aria-label="Link folder Google Drive"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !driveSave.isPending) onDriveSave();
                }}
              />
              <Button variant="outline" onClick={onDriveSave} disabled={driveSave.isPending} className="gap-2">
                {driveSave.isPending ? (
                  <>Memeriksa…</>
                ) : (
                  <>
                    <Save className="h-4 w-4" aria-hidden /> Simpan Link
                  </>
                )}
              </Button>
            </div>

            {driveLinksQuery.isPending ? (
              <Skeleton className="h-12" />
            ) : driveLinks.length > 0 ? (
              <div className="space-y-2">
                <div className="max-h-48 overflow-y-auto nice-scroll rounded-lg border divide-y">
                  {driveLinks.map((l) => {
                    const checked = driveInclude[l.id] !== false;
                    return (
                      <div key={l.id} className="flex items-center gap-3 px-3 py-2">
                        <Checkbox
                          id={`drive-${l.id}`}
                          checked={checked}
                          onCheckedChange={(v) =>
                            setDriveInclude((prev) => ({ ...prev, [l.id]: v === true }))
                          }
                          aria-label={`Ikut sertakan folder ${l.folderName}`}
                        />
                        <div className="min-w-0 flex-1">
                          <Label
                            htmlFor={`drive-${l.id}`}
                            className="cursor-pointer text-sm font-medium truncate block"
                          >
                            {l.folderName}
                          </Label>
                          <p className="text-xs text-muted-foreground truncate">
                            {l.fileCount} file Excel
                            {l.totalBytes ? ` · ${(l.totalBytes / 1048576).toFixed(1)} MB` : ""}
                            {l.lastUsedAt ? ` · terakhir ditarik ${fmtDateTime(l.lastUsedAt)}` : ""}
                          </p>
                        </div>
                        {l.folderKey ? (
                          <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40">
                            {l.folderKey}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
                            TIDAK DIKENALI
                          </Badge>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-9 w-9 p-0 text-muted-foreground hover:text-rose-600"
                              disabled={driveDelete.isPending}
                              aria-label={`Hapus link ${l.folderName}`}
                            >
                              <Trash2 className="h-4 w-4" aria-hidden />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogTitle>Hapus link folder “{l.folderName}”?</AlertDialogTitle>
                            <AlertDialogDescription>
                              File di Google Drive tidak tersentuh — hanya link tersimpan di aplikasi
                              yang hilang. Kamu bisa menempelkan ulang link-nya kapan saja.
                            </AlertDialogDescription>
                            <div className="flex justify-end gap-2">
                              <AlertDialogCancel>Batal</AlertDialogCancel>
                              <AlertDialogAction onClick={() => driveDelete.mutate(l.id)}>
                                Hapus
                              </AlertDialogAction>
                            </div>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    );
                  })}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    onClick={onDrivePull}
                    disabled={drivePull.isPending || includedDriveIds.length === 0}
                    className="gap-2"
                  >
                    {drivePull.isPending && drivePendingAction === "process" ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Menarik{" "}
                        {includedDriveIds.length} folder dari Drive…
                      </>
                    ) : (
                      <>
                        <CloudDownload className="h-4 w-4" aria-hidden /> Tarik {includedDriveIds.length} Folder → Bundle
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={onDrivePreview}
                    disabled={drivePull.isPending || includedDriveIds.length === 0}
                    className="gap-2"
                    aria-describedby="drive-preview-hint"
                  >
                    {drivePull.isPending && drivePendingAction === "preview" ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Mempratinjau…
                      </>
                    ) : (
                      <>
                        <Eye className="h-4 w-4" aria-hidden /> Pratinjau Cepat
                      </>
                    )}
                  </Button>
                  <p className="text-xs text-muted-foreground flex-1 min-w-64" id="drive-preview-hint">
                    <strong>Tarik</strong> mengunduh file → bundle (maks 16 link · 400 MB — di
                    serverless dibatasi ±60 dtk &amp; kuota disk). <strong>Pratinjau Cepat</strong>
                    hanya membaca listing Drive — tanpa unduhan, aman untuk folder besar di
                    serverless. Manifest muncul di bawah.
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Belum ada link tersimpan — tempel link folder Drive pertamamu di atas.
              </p>
            )}
          </div>

          {/* Proses via Python di Laptop (agent lokal) — Task 51.
              Python di laptop menjemput job → menarik file Drive + engine FastAPI
              LOKAL → hasil diunggah & tampil di web (pratinjau + komit). */}
          <div className="border-t pt-3 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-64 flex-1">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Laptop className="h-4 w-4" aria-hidden /> Proses via Python di Laptop (Agent)
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Python di laptop menjemput job ini, <strong>menarik file Drive &amp; memproses
                  engine FastAPI secara lokal</strong> — bebas batas 60 dtk/kuota serverless — lalu
                  hasilnya diunggah dan <strong>tampil di web ini</strong> (pratinjau + Komit di
                  sini juga). Memakai link Drive yang dicentang di atas + parameter run di form
                  bawah. Di laptop: <strong>dobel-klik <code className="text-[11px]">mulai-laptop.bat</code></strong>
                  dari repo (Windows; <code className="text-[11px]">mulai-laptop.command</code> di
                  macOS) — engine + agent nyala otomatis sekali klik, token ditanya sekali
                  (panduan: <code className="text-[11px]">docs/AGENT-LOCAL.md</code>).
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
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                onClick={onAgentJob}
                disabled={
                  agentCreate.isPending ||
                  includedDriveIds.length === 0 ||
                  (agentJob !== null && ["QUEUED", "RUNNING", "FINALIZING"].includes(agentJob.status))
                }
                className="gap-2"
              >
                {agentCreate.isPending ? (
                  "Membuat job…"
                ) : (
                  <>
                    <Send className="h-4 w-4" aria-hidden /> Kirim {includedDriveIds.length} Folder → Laptop (Proses Python)
                  </>
                )}
              </Button>
              <p className="text-xs text-muted-foreground flex-1 min-w-64">
                {agentOnline
                  ? "Agent online — job biasanya dijemput beberapa detik lagi."
                  : "Agent offline — job dibuat dan menunggu sampai agent berjalan di laptop."}{" "}
                Tanpa batas waktu serverless: proses berat terjadi di laptop.
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

          {manifest ? (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                <strong>{manifest.name}</strong> — {manifest.fileCount} file Excel ·{" "}
                {manifest.previewOnly
                  ? "pratinjau cepat · total byte tidak dihitung"
                  : `${(manifest.totalBytes / 1024 / 1024).toFixed(2)} MB`}
                {manifest.skippedEntries > 0 ? ` · ${manifest.skippedEntries} entri non-Excel/terlalu besar dilewati` : ""}
              </p>
              {manifest.previewOnly && (
                <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5 rounded-lg border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/10 px-3 py-2">
                  <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                  <span>
                    Pratinjau cepat — file TIDAK diunduh, belum ada bundle untuk diproses.
                    Untuk memproses data asli: <strong>Tarik → Bundle</strong> +{" "}
                    <strong>Proses Bundle</strong> di instalasi lokal (sandbox/PC), atau unggah ZIP
                    di serverless (maks ±4,5 MB).
                  </span>
                </p>
              )}
              {/* Peringatan manifest — max-h + scroll supaya daftar panjang (33+ file)
                  tidak meledakkan kartu (audit 48-g-ui); daftar diringkas 5 nama. */}
              <div className="max-h-32 overflow-y-auto nice-scroll space-y-2 pr-1">
                {manifest.missingFolders.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                    Folder tak ditemukan: {clipList(manifest.missingFolders)} — engine preflight akan
                    mencatat peringatan; folder Terima4215 memang tidak dibaca desktop v3.9.71.
                  </p>
                )}
                {manifest.source === "drive" && manifest.driveFolders && manifest.driveFolders.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Ditarik dari Drive: {manifest.driveFolders.map((f) => `${f.folderName} (${f.fileCount})`).join(" · ")}
                  </p>
                )}
                {manifest.driveNotices && manifest.driveNotices.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                    {manifest.driveNotices.join(" · ")}
                  </p>
                )}
                {manifest.skippedDuplicates && manifest.skippedDuplicates.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                    {manifest.skippedDuplicates.length} file Drive bernama sama dilewati (versi TERBARU menang):{" "}
                    {clipList(manifest.skippedDuplicates.map((d) => d.path))}.
                  </p>
                )}
                {manifest.suffixedDuplicates && manifest.suffixedDuplicates.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                    {manifest.suffixedDuplicates.length} file duplikat ditulis dengan akhiran __2 dst.:{" "}
                    {clipList(manifest.suffixedDuplicates)}.
                  </p>
                )}
                {manifest.skippedFiles && manifest.skippedFiles.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                    {manifest.skippedFiles.length} file Drive DILEWATI karena rusak/bukan Excel (cek folder Drive-nya):{" "}
                    {clipList(manifest.skippedFiles.map((d) => d.path))}.
                  </p>
                )}
              </div>
              <ScrollArea className="h-48 nice-scroll rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Kunci folder</TableHead>
                      <TableHead>Folder</TableHead>
                      <TableHead className="text-right">File</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {manifest.folders.map((f) => (
                      <TableRow key={f.folderKey}>
                        <TableCell className="font-mono text-xs whitespace-nowrap">{f.folderKey}</TableCell>
                        <TableCell className="max-w-56 truncate">{f.folderName}</TableCell>
                        <TableCell className="text-right cell-num">{fmtInt(f.fileCount)}</TableCell>
                        <TableCell>
                          {f.present ? (
                            <Badge variant="secondary">ADA</Badge>
                          ) : (
                            <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
                              KOSONG
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground border-t pt-3">
              Belum ada bundle terunggah — pilih folder export / ZIP untuk melihat manifest per folder sebelum diproses.
            </p>
          )}
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
          <Label htmlFor="bundle">Label bundle (opsional)</Label>
          <Input
            id="bundle"
            value={bundleName}
            onChange={(e) => setBundleName(e.target.value)}
            placeholder={mode === "bundle" ? "mis. Oktober — KERJA" : "mis. Demo Oktober"}
          />
        </div>
        <Button
          size="lg"
          onClick={onProcess}
          disabled={process.isPending || (mode === "bundle" && (!manifest || manifest.previewOnly))}
          className="gap-2"
        >
          {process.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Memproses…
            </>
          ) : (
            <>
              <Play className="h-4 w-4" aria-hidden />
              {mode === "bundle" ? "Proses Bundle" : "Jalankan Proses"}
            </>
          )}
        </Button>
        <p className="sm:col-span-2 lg:col-span-5 text-xs text-muted-foreground">
          {mode === "bundle" ? (
            <>
              Run memakai <strong>pipeline asli Stock-Monitoring v3.9.71</strong> (0-rewrite) — angka =
              angka desktop; label CEK, COM, catatan audit B1–B4 &amp; SKOR RESTO dipindah verbatim
              dari view desktop. Komit memanggil ulang engine atas bundleId yang sama (FR-12 idempotent).
            </>
          ) : (
            <>
              Engine demo menghasilkan bundle sintetis deterministik (kontrak §4) — bukan angka Accurate.
              Pilih folder / unggah ZIP bundle produksi aktif pada mode <em>Produksi</em> di atas (FR-1).
            </>
          )}
        </p>
      </div>

      {/* Riwayat run */}
      <div className="rounded-xl border bg-card p-4">
        <p className="text-sm font-medium mb-3 flex items-center gap-2">
          <UploadCloud className="h-4 w-4" aria-hidden /> Riwayat run — pilih untuk pratinjau
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
                  <TableHead>Bundle</TableHead>
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
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Mengkomit…
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
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
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
          description="Setelah menjalankan proses (atau memilih dari riwayat), pratinjau ringkasan, manifest file, isu kualitas data, dan log pipeline tampil di sini sebelum komit."
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
        <p className="flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
          Komit memanggil ulang engine dengan parameter identik (FR-12 idempotent) — hasil identik, lalu snapshot
          ditulis permanen. Kegagalan di tengah komit tidak pernah menyentuh snapshot lama (NFR-3).
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
