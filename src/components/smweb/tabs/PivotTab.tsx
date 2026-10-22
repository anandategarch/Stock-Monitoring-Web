"use client";
// Tab 📊 Pivot Table — matriks 10 metrik JENIS (FR-31): mode per-resto (kolom hari) atau
// per-tanggal (kolom resto), kolom nama barang di-freeze saat scroll horizontal (kontrak
// §84), sel "—" ≠ 0 (INV-1), klik sel → drill-down rincian harian (FR-32).
// Semua kontrol terikat store sehingga persist per sesi (INV-8).
// Task 33 #2: toggle "Warna ala desktop" — baris pastel per metrik (mirror
// METRIC_BG pivot_view.py:155-166), fg khusus IN/BM (in_row/bm_row), dan sel
// 7.Selisih IN ≠ 0 → #FFC9C9 (pivot_view.py _compute_row_tags).

import { useEffect, useMemo, useState } from "react";
import { Database, FileWarning, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { usePivot, useRestos } from "@/hooks/use-sm-api";
import { useSmStore } from "@/store/use-sm-store";
import { EmptyState } from "@/components/smweb/empty-state";
import { DrilldownSheet, type DrilldownTarget } from "@/components/smweb/drilldown-sheet";
import {
  metricPastelClass, metricValueFgClass, SIN_ANOMALY_BG,
} from "@/lib/desktop-parity";
import { METRICS, type MetricKey } from "@/lib/types";
import { cn } from "@/lib/utils";
import { fmtInt, fmtQty, signedQtyClass } from "@/lib/format";

// State aktif tombol segmen — aksen emerald selaras identitas SM-WEB.
const SEG_ON =
  "data-[state=on]:border-emerald-400 data-[state=on]:bg-emerald-50 data-[state=on]:text-emerald-700 " +
  "dark:data-[state=on]:border-emerald-500/60 dark:data-[state=on]:bg-emerald-500/15 dark:data-[state=on]:text-emerald-300";

export default function PivotTab({ snapshotId }: { snapshotId: string | null }) {
  const {
    pivotMode, setPivotMode, pivotMetric, setPivotMetric, pivotResto, setPivotResto,
    pivotDay, setPivotDay, pivotFrom, setPivotFrom, pivotTo, setPivotTo,
    pivotHideEmpty, setPivotHideEmpty, pivotRowColor, setPivotRowColor, setActiveTab,
  } = useSmStore();
  const [drillTarget, setDrillTarget] = useState<DrilldownTarget | null>(null);

  const { data: restosData, isPending: restosPending } = useRestos(snapshotId);
  const restos = useMemo(() => restosData?.restos ?? [], [restosData]);

  // Mode resto: pilih otomatis resto pertama bila belum ada pilihan valid supaya matriks
  // tidak pernah kosong hanya karena belum ada interaksi; juga bersihkan pilihan resto
  // yang tidak ada di snapshot aktif.
  useEffect(() => {
    if (restos.length === 0) return;
    if (pivotResto === "" || !restos.some((r) => r.restoCode === pivotResto)) {
      setPivotResto(restos[0].restoCode);
    }
  }, [restos, pivotResto, setPivotResto]);

  const qs = useMemo(
    () =>
      `mode=${pivotMode}&metric=${pivotMetric}&resto=${pivotResto}&day=${pivotDay}` +
      `&from=${pivotFrom}&to=${pivotTo ?? ""}&hideEmpty=${pivotHideEmpty ? 1 : 0}`,
    [pivotMode, pivotMetric, pivotResto, pivotDay, pivotFrom, pivotTo, pivotHideEmpty],
  );

  const { data, isPending, error, isFetching } = usePivot(snapshotId, qs);

  const restoNameMap = useMemo(
    () => new Map(restos.map((r) => [r.restoCode, r.restoName] as const)),
    [restos],
  );
  const restoName = (code: string) => restoNameMap.get(code) ?? code;
  const metricLabel = METRICS.find((m) => m.key === pivotMetric)?.label ?? pivotMetric;

  if (!snapshotId) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot"
        description="Jalankan Proses & Ingest dulu untuk menghasilkan snapshot periode, lalu kembali ke tab ini."
        action={
          <Button onClick={() => setActiveTab("ingest")}>
            <Play className="h-4 w-4" aria-hidden /> Buka Proses &amp; Ingest
          </Button>
        }
      />
    );
  }

  const cols = data?.columns ?? [];
  const rows = data?.rows ?? [];
  // Mode resto sebelum daftar resto termuat: tunggu, jangan render error 422 sesaat.
  const matrixPending = isPending || (pivotMode === "resto" && pivotResto === "" && restosPending);
  const noRestos = !restosPending && restos.length === 0;

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-lg sm:text-xl font-semibold tracking-tight">
          <span aria-hidden>📊</span> Pivot Table
        </h2>
        <p className="text-sm text-muted-foreground">
          Matriks metrik JENIS per barang — mode per-resto (kolom hari) atau per-tanggal
          (kolom resto). Kolom nama barang dibekukan saat scroll horizontal; klik sel
          untuk membuka rincian harian (drill-down).
        </p>
      </header>

      <section
        aria-label="Kontrol pivot"
        className="rounded-xl border bg-card p-4 flex flex-wrap items-end gap-x-6 gap-y-4"
      >
        <div className="flex flex-col gap-1.5">
          <span id="pivot-mode-label" className="text-xs font-medium text-muted-foreground">Mode</span>
          <ToggleGroup
            type="single"
            variant="outline"
            value={pivotMode}
            onValueChange={(v) => {
              if (v === "resto" || v === "tanggal") setPivotMode(v);
            }}
            aria-labelledby="pivot-mode-label"
          >
            <ToggleGroupItem value="resto" className={cn("h-9 px-3", SEG_ON)}>🏪 Per Resto</ToggleGroupItem>
            <ToggleGroupItem value="tanggal" className={cn("h-9 px-3", SEG_ON)}>📅 Per Tanggal</ToggleGroupItem>
          </ToggleGroup>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pivot-metric" className="text-xs font-medium text-muted-foreground">Metrik</Label>
          <Select value={pivotMetric} onValueChange={(v) => setPivotMetric(v as MetricKey)}>
            <SelectTrigger id="pivot-metric" className="w-[190px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {METRICS.map((m) => (
                <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {pivotMode === "resto" ? (
          <>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pivot-resto" className="text-xs font-medium text-muted-foreground">Resto</Label>
              <Select value={pivotResto === "" ? undefined : pivotResto} onValueChange={setPivotResto}>
                <SelectTrigger id="pivot-resto" className="w-[230px]">
                  <SelectValue placeholder={restosPending ? "Memuat resto…" : "Pilih resto"} />
                </SelectTrigger>
                <SelectContent>
                  {restos.map((r) => (
                    <SelectItem key={r.restoCode} value={r.restoCode}>
                      {r.restoCode} · {r.restoName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="pivot-from" className="text-xs font-medium text-muted-foreground">
                Rentang hari (1–31)
              </Label>
              <div className="flex items-center gap-1.5">
                <Input
                  id="pivot-from"
                  type="number"
                  min={1}
                  max={31}
                  value={pivotFrom}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    if (!Number.isNaN(n)) setPivotFrom(n);
                  }}
                  className="w-[76px]"
                />
                <span className="text-xs text-muted-foreground" aria-hidden>–</span>
                <Input
                  id="pivot-to"
                  type="number"
                  min={1}
                  max={31}
                  value={pivotTo ?? ""}
                  placeholder="akhir"
                  aria-label="Hari sampai"
                  onChange={(e) => {
                    if (e.target.value === "") {
                      setPivotTo(null);
                      return;
                    }
                    const n = Number(e.target.value);
                    if (!Number.isNaN(n)) setPivotTo(n);
                  }}
                  className="w-[76px]"
                />
              </div>
              <p className="text-[11px] text-muted-foreground">Sampai kosong = akhir bulan</p>
            </div>
          </>
        ) : (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pivot-day" className="text-xs font-medium text-muted-foreground">Hari (1–31)</Label>
            <Input
              id="pivot-day"
              type="number"
              min={1}
              max={31}
              value={pivotDay}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isNaN(n)) setPivotDay(n);
              }}
              className="w-[76px]"
            />
            <p className="text-[11px] text-muted-foreground">Kolom matriks = resto pada hari ini</p>
          </div>
        )}

        <div className="flex items-center gap-2 pb-0.5">
          <Switch id="pivot-hide-empty" checked={pivotHideEmpty} onCheckedChange={setPivotHideEmpty} />
          <Label htmlFor="pivot-hide-empty" className="text-xs">Sembunyikan baris kosong (semua sel 0)</Label>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Switch id="pivot-row-color" checked={pivotRowColor} onCheckedChange={setPivotRowColor} />
          <Label
            htmlFor="pivot-row-color"
            className="text-xs"
            title="Baris pastel per metrik + sel Selisih IN ≠ 0 merah muda + minus merah semua metrik — mirror pivot desktop"
          >
            Warna ala desktop
          </Label>
        </div>
      </section>

      {noRestos ? (
        <EmptyState
          icon={Database}
          title="Snapshot ini tidak memiliki baris data"
          description="Tidak ada resto pada snapshot terpilih — snapshot mungkin kosong."
        />
      ) : matrixPending ? (
        <Skeleton className="h-[60vh] w-full rounded-xl" />
      ) : error ? (
        <EmptyState icon={FileWarning} title="Gagal memuat pivot" description={(error as Error).message} />
      ) : data ? (
        <section aria-label="Matriks pivot" className="space-y-2">
          <div
            aria-busy={isFetching}
            className={cn(
              "max-h-[70vh] overflow-auto nice-scroll rounded-xl border bg-card transition-opacity",
              isFetching && "opacity-60",
            )}
          >
            <table className="w-full text-sm border-separate border-spacing-0">
              <caption className="sr-only">
                Matriks pivot metrik {metricLabel}, mode{" "}
                {pivotMode === "resto" ? "per resto (kolom hari)" : "per tanggal (kolom resto)"}
              </caption>
              <thead className="sticky top-0 z-20 bg-background">
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-30 min-w-[220px] max-w-[280px] whitespace-normal border-r border-b bg-background px-3 py-2 text-left font-medium"
                  >
                    Nama Barang
                    <span className="block text-[11px] font-normal text-muted-foreground">satuan · kategori</span>
                  </th>
                  {cols.map((c) => (
                    <th
                      key={c.key}
                      scope="col"
                      title={pivotMode === "tanggal" ? restoName(c.key) : undefined}
                      className="min-w-[52px] whitespace-nowrap border-b bg-background px-2.5 py-2 text-right font-medium"
                    >
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={cols.length + 1} className="border-b px-4 py-10 text-center text-sm text-muted-foreground">
                      Tidak ada baris tampil — semua baris memiliki sel 0/kosong pada kombinasi
                      metrik &amp; rentang ini. Matikan “Sembunyikan baris kosong” atau ubah
                      rentang/metrik.
                    </td>
                  </tr>
                ) : (
                  rows.map((row) => (
                    <tr
                      key={`${row.itemName}|${row.satuan}`}
                      className={cn(
                        "group",
                        // Pastel baris per metrik ala desktop (METRIC_BG) — hanya
                        // saat toggle aktif. Kolom nama beku tetap bg-background,
                        // cermin pane beku FrozenNamePane desktop.
                        pivotRowColor && metricPastelClass(pivotMetric),
                      )}
                    >
                      <td className="sticky left-0 z-10 min-w-[220px] max-w-[280px] whitespace-normal border-r border-b border-border/60 bg-background px-3 py-1.5 group-hover:bg-muted/40">
                        <span className="block font-medium leading-tight">{row.itemName}</span>
                        <span className="block text-[11px] text-muted-foreground">{row.satuan} · {row.kategori}</span>
                      </td>
                      {cols.map((c) => {
                        const v = row.values[c.key] ?? null;
                        return (
                          <td key={c.key} className="border-b border-border/60 p-0">
                            <button
                              type="button"
                              onClick={() =>
                                setDrillTarget({
                                  resto: pivotMode === "resto" ? pivotResto : c.key,
                                  item: row.itemName,
                                })
                              }
                              aria-label={
                                pivotMode === "resto"
                                  ? `Buka rincian ${row.itemName} di ${restoName(pivotResto)}, hari ${c.label}`
                                  : `Buka rincian ${row.itemName} di ${restoName(c.key)}, hari ${pivotDay}`
                              }
                              className="block w-full px-2.5 py-1.5 text-right transition-colors hover:bg-muted/60"
                            >
                              {v === null ? (
                                <span className="text-muted-foreground/50">—</span>
                              ) : (
                                <span className={cn(
                                  "cell-num",
                                  pivotRowColor
                                    ? cn(
                                        // Paritas warna ala desktop: minus merah
                                        // untuk SEMUA metrik (neg_cell) + fg khusus
                                        // IN/BM (in_row/bm_row) + sel anomali
                                        // 7.Selisih IN ≠ 0 (#FFC9C9).
                                        metricValueFgClass(pivotMetric),
                                        v < 0 && signedQtyClass(v),
                                        pivotMetric === "qtySelisihIN" && v !== 0 && SIN_ANOMALY_BG,
                                      )
                                    : pivotMetric === "qtyDeviasi" && signedQtyClass(v),
                                )}>
                                  {fmtQty(v)}
                                </span>
                              )}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <p>
              {fmtInt(data.hiddenEmptyRows)} baris tersembunyi (semua sel 0/kosong) ·{" "}
              {fmtInt(rows.length)} baris tampil
            </p>
            <p>
              <span className="text-muted-foreground/50">“—”</span> = tidak ada data (missing ≠ 0,
              INV-1) · 0 = benar-benar nol
              {pivotRowColor ? (
                <>· <span className="text-[#9C5700] dark:text-amber-200">pastel baris</span> = metrik aktif (ala desktop){pivotMetric === "qtySelisihIN" ? <> · <span className="bg-[#FFC9C9] dark:bg-rose-500/25 px-1">merah muda</span> = Selisih IN ≠ 0</> : null}</>
              ) : null}
            </p>
          </div>
        </section>
      ) : null}

      <DrilldownSheet
        snapshotId={snapshotId}
        target={drillTarget}
        onClose={() => setDrillTarget(null)}
      />
    </div>
  );
}
