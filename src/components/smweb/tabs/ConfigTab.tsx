// Tab ⚙️ Config & Admin — status engine service (FR-81), setting default run (FR-80),
// manajemen periode/snapshot (FR-82), jejak audit (NFR-4).
"use client";

import { useState } from "react";
import {
  AlertTriangle, CheckCircle2, Cog, Database, History, Loader2, Save, ScrollText,
  ServerCog, Settings2, Trash2, XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  useAudit, useDeleteSnapshot, useEngineHealth, useSaveSettings, useSeedDemo,
  useSettings, useSnapshots,
} from "@/hooks/use-sm-api";
import { EmptyState } from "@/components/smweb/empty-state";
import {
  fmtDateTime, fmtDateTimeShort, fmtInt, fmtRp, periodLabel,
} from "@/lib/format";

/** Detail JSON jejak audit dipotong 80 karakter (font-mono, text-xs). */
function truncateDetail(s: string | null): string {
  if (!s) return "—";
  return s.length > 80 ? `${s.slice(0, 80)}…` : s;
}

export default function ConfigTab({ snapshotId }: { snapshotId: string | null }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings2 className="h-5 w-5 text-emerald-600" aria-hidden /> ⚙️ Config &amp; Admin
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Status engine service, default parameter run, manajemen snapshot periode, dan jejak audit
          dari seluruh aksi tulis (FR-80..82).
        </p>
      </div>

      <EngineSection />
      <SettingsSection />
      <PeriodSection snapshotId={snapshotId} />
      <AuditSection />
    </div>
  );
}

// ---------- 1. Status Engine Service (FR-81) — demo + produksi ----------

function EngineSection() {
  const { data, isPending } = useEngineHealth();

  return (
    <Card className="p-0 gap-0">
      <CardContent className="p-4 sm:p-5 space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <ServerCog className="h-4 w-4 text-muted-foreground" aria-hidden /> Status Engine Service
          <span className="text-xs font-normal text-muted-foreground">FR-81 · dicek ulang tiap 30 detik</span>
        </h3>

        {isPending ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <EngineCard
              title="PRODUKSI — pipeline asli v3.9.71"
              hint="mini-services/engine-fastapi · port 3031 · dipakai saat ingest bundle ZIP (FR-10)"
              health={data?.production?.health ?? null}
              error={data?.production?.error}
              runCmd="cd mini-services/engine-fastapi && bun run dev"
            />
            <EngineCard
              title="DEMO — data sintetis deterministik"
              hint="mini-services/engine · port 3030 · seed/pelatihan UI (kontrak §4)"
              health={data?.health ?? null}
              error={data?.error}
              runCmd="cd mini-services/engine && bun run dev"
              fallbackNote={
                data?.embedded?.available
                  ? "Fallback EMBEDDED aktif — seed & run demo tetap jalan tanpa service (generator identik, deterministik FR-12)."
                  : undefined
              }
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EngineCard({
  title, hint, health, error, runCmd, fallbackNote,
}: {
  title: string;
  hint: string;
  health: import("@/lib/types").EngineHealth | null;
  error?: string;
  runCmd: string;
  /** Tampil bila service tidak terjangkau TAPI fallback embedded tersedia
   *  (deploy tanpa engine co-located) — kartu amber, bukan merah. */
  fallbackNote?: string;
}) {
  if (!health) {
    if (fallbackNote) {
      return (
        <div className="rounded-lg border border-amber-300 bg-amber-50/70 dark:bg-amber-500/10 dark:border-amber-500/40 p-3 space-y-2">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-300 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden /> {title}
          </p>
          <p className="text-sm text-muted-foreground">{error ?? "Service tidak terjangkau."}</p>
          <p className="text-sm text-muted-foreground">{fallbackNote}</p>
        </div>
      );
    }
    return (
      <div className="rounded-lg border border-rose-300 bg-rose-50/70 dark:bg-rose-500/10 dark:border-rose-500/40 p-3 space-y-2">
        <p className="text-sm font-medium text-rose-700 dark:text-rose-300 flex items-center gap-2">
          <XCircle className="h-4 w-4 shrink-0" aria-hidden /> {title}
        </p>
        <p className="text-sm text-muted-foreground">{error ?? "Service tidak terjangkau."}</p>
        <p className="text-sm text-muted-foreground">
          Jalankan: <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{runCmd}</code>
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border p-3 space-y-2.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden />
            {title}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>
        </div>
        <div className="text-right text-xs space-y-0.5">
          <p>
            <strong>{health.engineName}</strong> v{health.engineVersion} —{" "}
            <span className="text-emerald-700 dark:text-emerald-300">sehat</span> (kontrak v
            {health.contractVersion})
          </p>
          <p className="text-muted-foreground">
            definisi <span className="font-mono">{health.definitionVersion}</span> · uptime{" "}
            <span className="cell-num">{fmtInt(health.uptimeSec)}</span> dtk · proses terakhir{" "}
            {fmtDateTime(health.lastProcessAt)}
            {health.lastDurationMs !== null ? ` (${fmtInt(health.lastDurationMs)} ms)` : ""}
          </p>
        </div>
      </div>
      <p className="text-xs text-muted-foreground border-t pt-2">{health.parityNote}</p>
    </div>
  );
}

// ---------- 2. Setting Default Run (FR-80) ----------

function SettingsSection() {
  const { data, isPending } = useSettings();
  const save = useSaveSettings();

  const settings = data?.settings;

  // Pola "draft": prefill otomatis dari data termuat; ketikan user menimpa draft sampai disimpan.
  const [draft, setDraft] = useState<{ h: string; a: string } | null>(null);
  const hDefault = draft?.h ?? (settings ? String(settings.tanggalHDefault) : "");
  const aDefault = draft?.a ?? (settings ? String(settings.ambangAcrDefault) : "");

  const hNum = Number(hDefault);
  const aNum = Number(aDefault);
  const validH = hDefault.trim() !== "" && Number.isInteger(hNum) && hNum >= 1 && hNum <= 31;
  const validA = aDefault.trim() !== "" && Number.isInteger(aNum) && aNum >= 1 && aNum <= 200;
  const unchanged =
    !settings || (String(settings.tanggalHDefault) === hDefault.trim() && String(settings.ambangAcrDefault) === aDefault.trim());
  const canSave = !isPending && !unchanged && validH && validA;

  const onSave = () => {
    if (!validH) {
      toast.error("TANGGAL H default harus integer 1..31.");
      return;
    }
    if (!validA) {
      toast.error("AMBANG ACR default harus integer 1..200.");
      return;
    }
    save.mutate(
      { tanggalHDefault: hNum, ambangAcrDefault: aNum },
      {
        onSuccess: () => setDraft(null), // kembali mengikuti nilai tersimpan di server
        onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal menyimpan setting."),
      },
    );
  };

  return (
    <Card className="p-0 gap-0">
      <CardContent className="p-4 sm:p-5 space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Cog className="h-4 w-4 text-muted-foreground" aria-hidden /> Setting Default Run
          <span className="text-xs font-normal text-muted-foreground">FR-80 · perubahan tercatat di jejak audit</span>
        </h3>

        {isPending && !settings ? (
          <Skeleton className="h-24" />
        ) : settings ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 lg:items-start">
              <div className="space-y-1.5">
                <Label htmlFor="set-h">TANGGAL H default (1..31)</Label>
                <Input
                  id="set-h"
                  type="number"
                  min={1}
                  max={31}
                  value={hDefault}
                  onChange={(e) => setDraft({ h: e.target.value, a: aDefault })}
                  aria-invalid={!validH}
                />
                <p className="text-xs text-muted-foreground">Tanggal cut-off bulanan bawaan run baru.</p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="set-a">AMBANG ACR default (%)</Label>
                <Input
                  id="set-a"
                  type="number"
                  min={1}
                  max={200}
                  value={aDefault}
                  onChange={(e) => setDraft({ h: hDefault, a: e.target.value })}
                  aria-invalid={!validA}
                />
                <p className="text-xs text-muted-foreground">default 80% — INV-9 (ambang alami ACR to BOM).</p>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={onSave} disabled={!canSave} aria-label="Simpan setting default run">
                  {save.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  ) : (
                    <Save className="h-3.5 w-3.5" aria-hidden />
                  )}
                  Simpan
                </Button>
                {unchanged && !save.isPending ? (
                  <span className="text-xs text-muted-foreground">tidak ada perubahan</span>
                ) : null}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              engine: <strong className="font-medium">{settings.engineKind}</strong> · kategori barang 4217:{" "}
              {settings.kategoriBarang4217 ? (
                <span className="font-mono">{settings.kategoriBarang4217}</span>
              ) : (
                "belum diunggah (unggahan dikelola Fase 2, FR-2)"
              )}
            </p>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

// ---------- 3. Manajemen Periode (FR-82) ----------

function PeriodSection({ snapshotId }: { snapshotId: string | null }) {
  const { data, isPending, error } = useSnapshots();
  const del = useDeleteSnapshot();
  const seed = useSeedDemo();
  const snapshots = data?.snapshots ?? [];

  return (
    <Card className="p-0 gap-0">
      <CardContent className="p-4 sm:p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" aria-hidden /> Manajemen Periode
            <span className="text-xs font-normal text-muted-foreground">FR-82 · snapshot aktif / superseded</span>
          </h3>
          <div className="flex flex-col items-end">
            <Button
              variant="secondary"
              size="sm"
              disabled={seed.isPending}
              onClick={() => seed.mutate(undefined, { onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal mengisi data demo.") })}
              aria-label="Isi data demo dua periode"
            >
              {seed.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <Database className="h-3.5 w-3.5" aria-hidden />
              )}
              Isi data demo (2 periode)
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground -mt-1">
          Tombol di atas hanya untuk database kosong — membuat snapshot demo 2026-09 &amp; 2026-10 dari engine sintetis.
        </p>

        {isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : error ? (
          <EmptyState title="Gagal memuat daftar snapshot" description={error instanceof Error ? error.message : "Permintaan gagal."} />
        ) : snapshots.length === 0 ? (
          <EmptyState
            icon={Database}
            title="Belum ada snapshot periode"
            description="Jalankan pipeline di tab Proses & Ingest dan komit run, atau isi data demo untuk mencoba."
          />
        ) : (
          <div className="rounded-lg border overflow-x-auto">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-card">
                <TableRow>
                  <TableHead>Periode</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Definisi</TableHead>
                  <TableHead className="text-right">Baris</TableHead>
                  <TableHead className="text-right">Nominal</TableHead>
                  <TableHead>H / ambang</TableHead>
                  <TableHead>Dikomit</TableHead>
                  <TableHead className="w-12" aria-label="Aksi hapus"><span className="sr-only">Aksi</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshots.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">
                      {periodLabel(s.periodKey)}
                      {s.id === snapshotId ? (
                        <Badge variant="outline" className="ml-2 text-[10px]">dipilih</Badge>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {s.state === "ACTIVE" ? (
                        <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40 hover:bg-emerald-100">ACTIVE</Badge>
                      ) : (
                        <Badge variant="secondary">SUPERSEDED</Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{s.definitionVersion}</TableCell>
                    <TableCell className="text-right cell-num">{fmtInt(s.rowCount)}</TableCell>
                    <TableCell className="text-right cell-num">{fmtRp(s.nominalTotal)}</TableCell>
                    <TableCell className="text-xs">H {s.params.tanggalH} · {s.params.ambangAcrPct}%</TableCell>
                    <TableCell className="text-xs">{fmtDateTimeShort(s.committedAt)}</TableCell>
                    <TableCell>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300"
                            aria-label={`Hapus snapshot periode ${periodLabel(s.periodKey)}`}
                            disabled={del.isPending}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>
                              Hapus snapshot periode {periodLabel(s.periodKey)}?
                            </AlertDialogTitle>
                            <AlertDialogDescription>
                              Baris &amp; relasi ikut terhapus (cascade); DQ issue run tetap tercatat.
                              Tindakan ini tidak bisa dibatalkan.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Batal</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-rose-600 text-white hover:bg-rose-700"
                              onClick={() =>
                                del.mutate(s.id, {
                                  onError: (err) => toast.error(err instanceof Error ? err.message : "Gagal menghapus snapshot."),
                                })
                              }
                            >
                              Hapus
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------- 4. Jejak Audit (NFR-4) ----------

function AuditSection() {
  const { data, isPending, error } = useAudit(50);
  const logs = data?.logs ?? [];

  return (
    <Card className="p-0 gap-0">
      <CardContent className="p-4 sm:p-5 space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <ScrollText className="h-4 w-4 text-muted-foreground" aria-hidden /> Jejak Audit
          <span className="text-xs font-normal text-muted-foreground">NFR-4 · 50 entri terakhir</span>
        </h3>

        {isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : error ? (
          <EmptyState title="Gagal memuat jejak audit" description={error instanceof Error ? error.message : "Permintaan gagal."} />
        ) : logs.length === 0 ? (
          <EmptyState
            icon={History}
            title="Belum ada entri audit"
            description="Setiap aksi tulis (komit snapshot, ubah setting, transisi follow-up) tercatat di sini."
          />
        ) : (
          <div className="rounded-lg border overflow-x-auto max-h-[70vh] overflow-y-auto nice-scroll">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-card">
                <TableRow>
                  <TableHead>Waktu</TableHead>
                  <TableHead>Aksi</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Detail</TableHead>
                  <TableHead>Aktor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell className="text-xs whitespace-nowrap">{fmtDateTimeShort(l.createdAt)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-[11px]">{l.action}</Badge>
                    </TableCell>
                    <TableCell className="text-xs">{l.entity}</TableCell>
                    <TableCell className="font-mono text-xs max-w-72 whitespace-normal break-all">
                      {truncateDetail(l.detailJson)}
                    </TableCell>
                    <TableCell className="text-xs">{l.actor}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Setiap aksi tulis (komit snapshot, ubah setting, transisi follow-up) tercatat —
          siapa, kapan, aksi apa, dan detail payload singkat.
        </p>
      </CardContent>
    </Card>
  );
}
