"use client";
// Task 55-b — Tab 📊 Pivot Table REWRITE: struktur PERSIS aplikasi desktop
// v3.9.71 (pivot_view.py): baris PARENT = nama barang, SUB-BARIS = 10 metrik
// JENIS (SALDO AWAL, 1.SO, 2.SALDO AKHIR, 3.DEVIASI, 4.IN, 5.BARANG MASUK,
// 6.PEMAKAIAN (COM), 7.SELISIH IN, 8.BARANG KELUAR, 9.ACR) — keluhan user:
// "di tab pivot tabel metrik itu harusnya di row sama seperti repo ku stock
// monitoring". Kolom = SEMUA RESTO (mode 🏪 Per Resto, default) atau hari
// (mode 📅 Per Tanggal). COM hanya mode tanggal (dihitung server — port
// _compute_com desktop); hide-empty = semua sel 0/null (v3.9.69); "—" =
// INV-1 missing ≠ 0. TANPA dropdown metrik & TANPA kolom Total (desktop
// memang sengaja tanpa Total). Kontrol persist via store (pivotMode,
// pivotResto, pivotFrom, pivotTo, pivotHideEmpty, pivotRowColor).

import { Fragment, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { useRestos } from "@/hooks/use-sm-api";
import { useSmStore } from "@/store/use-sm-store";
import { EmptyState } from "@/components/smweb/empty-state";
import { ExportButton } from "@/components/smweb/export-button";
import { DrilldownSheet, type DrilldownTarget } from "@/components/smweb/drilldown-sheet";
import {
  metricPastelClass, metricValueFgClass, SIN_ANOMALY_BG,
} from "@/lib/desktop-parity";
import {
  PIVOT_KATEGORI_ALL, PIVOT_KATEGORI_GABUNGAN, PIVOT_METRIC_STICKY_BG,
  type PivotMatrixResponse,
} from "@/lib/pivot-def";
import { cn } from "@/lib/utils";
import { fmtInt, fmtQty, signedQtyClass } from "@/lib/format";

// State aktif tombol segmen — aksen emerald selaras identitas SM-WEB.
const SEG_ON =
  "data-[state=on]:border-emerald-400 data-[state=on]:bg-emerald-50 data-[state=on]:text-emerald-700 " +
  "dark:data-[state=on]:border-emerald-500/60 dark:data-[state=on]:bg-emerald-500/15 dark:data-[state=on]:text-emerald-300";

// Penanda global "user pernah menyentuh toggle warna" — default ON sampai
// disentuh (desktop tak punya toggle; warna selalu aktif di sana).
const ROWCOLOR_TOUCHED_KEY = "smweb-pivot-rowcolor-touched";

// ---- fetchJson + hook lokal (pola src/hooks/use-sm-api.ts; Task 55-b:
// kontrak respons baru PivotMatrixResponse → hook didefinisikan lokal) ----
async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
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
    const err = new Error(msg) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return body as T;
}

function usePivotMatrix(snapshotId: string | null, qs: string, enabled: boolean) {
  return useQuery({
    queryKey: ["snapshots", snapshotId ?? "-", "pivot-matrix", qs],
    queryFn: () => fetchJson<PivotMatrixResponse>(`/api/snapshots/${snapshotId}/pivot?${qs}`),
    enabled,
    placeholderData: (prev) => prev,
  });
}

export default function PivotTab({ snapshotId }: { snapshotId: string | null }) {
  const {
    pivotMode, setPivotMode, pivotResto, setPivotResto, pivotFrom, setPivotFrom,
    pivotTo, setPivotTo, pivotHideEmpty, setPivotHideEmpty, pivotRowColor,
    setPivotRowColor, setActiveTab,
  } = useSmStore();

  const [drillTarget, setDrillTarget] = useState<DrilldownTarget | null>(null);
  // Kategori = state lokal (Task 55-b): null = belum dipilih → default desktop
  // "Deviasi (COM + Packaging)". Route meringankan jadi tanpa-filter bila
  // snapshot tak memuat kategori rekap (mirror _default_kategori_value) —
  // select lalu menampilkan "(Semua)", konsisten dgn yang difilter server.
  const [kategoriSel, setKategoriSel] = useState<string | null>(null);
  const [rowColorTouched, setRowColorTouched] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(ROWCOLOR_TOUCHED_KEY) === "1")
        // eslint-disable-next-line react-hooks/set-state-in-effect -- restore preferensi SEKALI saat mount, baca localStorage pasca-hidrasi (pola IngestTab Task 54/55; bukan reaksi render)
        setRowColorTouched(true);
    } catch {
      /* localStorage tak tersedia — tetap pakai default ON */
    }
  }, []);

  // Default "Warna ala desktop" = ON (desktop selalu berwarna); setelah user
  // menyentuh toggle, nilai persist store pivotRowColor yang berlaku.
  const rowColor = rowColorTouched ? pivotRowColor : true;

  const { data: restosData, isPending: restosPending } = useRestos(snapshotId);
  const restos = useMemo(() => restosData?.restos ?? [], [restosData]);
  const restoName = useMemo(() => {
    const m = new Map(restos.map((r) => [r.restoCode, r.restoName] as const));
    return (code: string) => m.get(code) ?? code;
  }, [restos]);

  // Resto efektif mode tanggal: pilih otomatis resto pertama bila pilihan
  // belum ada / tak valid di snapshot ini (derived saat render — tanpa
  // setState dalam efek).
  const effectiveResto = useMemo(() => {
    if (pivotResto && restos.some((r) => r.restoCode === pivotResto)) return pivotResto;
    return restos[0]?.restoCode ?? "";
  }, [pivotResto, restos]);

  const kategoriParam = kategoriSel ?? PIVOT_KATEGORI_GABUNGAN;

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    p.set("mode", pivotMode);
    if (pivotMode === "tanggal") p.set("resto", effectiveResto);
    p.set("from", String(pivotFrom));
    p.set("to", pivotTo === null ? "" : String(pivotTo));
    p.set("kategori", kategoriParam);
    p.set("hideEmpty", pivotHideEmpty ? "1" : "0");
    return p.toString();
  }, [pivotMode, effectiveResto, pivotFrom, pivotTo, kategoriParam, pivotHideEmpty]);

  // Mode tanggal tanpa resto valid: query DITUNDA (enabled) → isPending →
  // skeleton — jangan pernah menembak 422 sesaat (pola lama).
  const queryEnabled = Boolean(snapshotId) && (pivotMode === "resto" || effectiveResto !== "");
  const { data, isPending, error, isFetching } = usePivotMatrix(snapshotId, qs, queryEnabled);

  const kategoriOptions = data?.kategoriOptions ?? [];
  // Tampilan select: nilai yang benar-benar ada di opsi; default gabungan
  // yang tak ada di data ditampilkan "(Semua)" — sama dgn perlakuan server.
  const kategoriShown = kategoriOptions.includes(kategoriParam)
    ? kategoriParam
    : PIVOT_KATEGORI_ALL;

  if (!snapshotId) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot"
        description="Jalankan Proses &amp; Ingest dulu untuk menghasilkan snapshot periode, lalu kembali ke tab ini."
        action={
          <Button onClick={() => setActiveTab("ingest")}>
            <Play className="h-4 w-4" aria-hidden /> Buka Proses &amp; Ingest
          </Button>
        }
      />
    );
  }

  const cols = data?.columns ?? [];
  const items = data?.items ?? [];
  const noRestos = !restosPending && restos.length === 0;

  const markRowColorTouched = () => {
    try {
      window.localStorage.setItem(ROWCOLOR_TOUCHED_KEY, "1");
    } catch {
      /* abaikan — preferensi hanya persist di store */
    }
  };

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg sm:text-xl font-semibold tracking-tight">
            <span aria-hidden>📊</span> Pivot Table
          </h2>
          {snapshotId ? (
            <ExportButton snapshotId={snapshotId} sheet="pivot" size="sm" label="Export Pivot" />
          ) : null}
        </div>
        <p className="text-sm text-muted-foreground">
          Struktur ala aplikasi desktop: tiap barang = baris induk dengan sub-baris 10 metrik
          JENIS; kolom = semua resto (Per Resto) atau hari (Per Tanggal). Klik sel untuk
          membuka rincian harian (drill-down).
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

        {pivotMode === "tanggal" ? (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pivot-resto" className="text-xs font-medium text-muted-foreground">Resto</Label>
            <Select value={effectiveResto === "" ? undefined : effectiveResto} onValueChange={setPivotResto}>
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
        ) : null}

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

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pivot-kategori" className="text-xs font-medium text-muted-foreground">Kategori</Label>
          <Select
            value={kategoriOptions.includes(kategoriShown) ? kategoriShown : undefined}
            onValueChange={(v) => setKategoriSel(v)}
          >
            <SelectTrigger id="pivot-kategori" className="w-[240px]">
              <SelectValue placeholder={isPending ? "Memuat kategori…" : "Pilih kategori"} />
            </SelectTrigger>
            <SelectContent>
              {kategoriOptions.map((k) => (
                <SelectItem key={k} value={k}>{k}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Switch id="pivot-hide-empty" checked={pivotHideEmpty} onCheckedChange={setPivotHideEmpty} />
          <Label htmlFor="pivot-hide-empty" className="text-xs">Sembunyikan baris kosong (semua sel 0)</Label>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Switch
            id="pivot-row-color"
            checked={rowColor}
            onCheckedChange={(v) => {
              markRowColorTouched();
              setPivotRowColor(v);
            }}
          />
          <Label
            htmlFor="pivot-row-color"
            className="text-xs"
            title="Baris pastel per sub-baris metrik + sel Selisih IN ≠ 0 merah muda + minus merah semua metrik — mirror pivot desktop"
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
      ) : isPending ? (
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
                Matriks pivot: baris induk nama barang dengan sub-baris per metrik JENIS;
                kolom {pivotMode === "resto" ? "resto (mode per resto)" : "tanggal (mode per tanggal)"};
                klik sel untuk membuka rincian harian.
              </caption>
              <thead className="sticky top-0 z-20 bg-background">
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-30 min-w-[220px] max-w-[280px] whitespace-normal border-r border-b bg-background px-3 py-2 text-left font-medium"
                  >
                    Nama Barang
                    <span className="block text-[11px] font-normal text-muted-foreground">
                      sub-baris: metrik JENIS
                    </span>
                  </th>
                  {cols.map((c) => (
                    <th
                      key={c.key}
                      scope="col"
                      title={pivotMode === "resto" ? restoName(c.key) : undefined}
                      className="min-w-[56px] whitespace-nowrap border-b bg-background px-2.5 py-2 text-right font-medium"
                    >
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={cols.length + 1} className="border-b px-4 py-10 text-center text-sm text-muted-foreground">
                      Tidak ada baris tampil — semua baris metrik kosong (semua sel 0/—) untuk
                      kombinasi filter ini. Matikan “Sembunyikan baris kosong” atau ubah
                      rentang/kategori.
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <Fragment key={item.itemName}>
                      {/* Baris parent = nama barang — item_header desktop #e2e8f0 (= slate-200) */}
                      <tr className="bg-slate-200 dark:bg-slate-700">
                        <th
                          scope="row"
                          className="sticky left-0 z-10 min-w-[220px] max-w-[280px] whitespace-normal border-r border-b border-border/60 bg-slate-200 px-3 py-1.5 text-left align-top dark:bg-slate-700"
                        >
                          <span className="block font-medium leading-tight">{item.itemName}</span>
                          <span className="block text-[11px] font-normal text-muted-foreground">
                            {item.satuan} · {item.kategori}
                          </span>
                        </th>
                        {cols.map((c) => (
                          <td key={c.key} className="border-b border-border/60" />
                        ))}
                      </tr>
                      {item.metrics
                        .filter((m) => m.active)
                        .map((m) => (
                          <tr key={`${item.itemName}|${m.key}`} className={cn(rowColor && metricPastelClass(m.key))}>
                            {/* Sub-baris metrik — kolom beku bg SOLID supaya tak tembus saat scroll horizontal */}
                            <th
                              scope="row"
                              className={cn(
                                "sticky left-0 z-10 border-r border-b border-border/60 py-1 pl-6 pr-3 text-left align-top text-xs font-normal",
                                rowColor ? PIVOT_METRIC_STICKY_BG[m.key] : "bg-card",
                              )}
                            >
                              {m.label}
                            </th>
                            {cols.map((c) => {
                              const v = m.values[c.key] ?? null;
                              const isSinAnomaly =
                                rowColor && m.key === "qtySelisihIN" && v !== null && v !== 0;
                              return (
                                <td key={c.key} className="border-b border-border/60 p-0">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setDrillTarget({
                                        resto: pivotMode === "resto" ? c.key : effectiveResto,
                                        item: item.itemName,
                                      })
                                    }
                                    aria-label={
                                      pivotMode === "resto"
                                        ? `Buka rincian ${item.itemName} (${m.label}) di resto ${restoName(c.key)}`
                                        : `Buka rincian ${item.itemName} (${m.label}) di resto ${restoName(effectiveResto)}, hari ${c.label}`
                                    }
                                    className={cn(
                                      "block w-full px-2.5 py-1 text-right text-xs transition-colors hover:bg-muted/60",
                                      isSinAnomaly && SIN_ANOMALY_BG,
                                    )}
                                  >
                                    {v === null ? (
                                      <span className="text-muted-foreground/50">—</span>
                                    ) : (
                                      <span
                                        className={cn(
                                          "cell-num",
                                          rowColor &&
                                            cn(metricValueFgClass(m.key), v < 0 && signedQtyClass(v)),
                                        )}
                                      >
                                        {fmtQty(v)}
                                      </span>
                                    )}
                                  </button>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                    </Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <p>
              {fmtInt(items.length)} dari {fmtInt(data.totalItems)} barang × {fmtInt(cols.length)}{" "}
              kolom ({pivotMode === "resto" ? "resto" : "tanggal"}) ·{" "}
              {fmtInt(data.hiddenEmptyRows)} baris metrik tersembunyi · rentang hari{" "}
              {data.from}–{data.to}
            </p>
            <p>
              <span className="text-muted-foreground/50">“—”</span> = tidak ada data ≠ 0
              {rowColor ? (
                <>
                  {" "}· <span className="text-[#9C5700] dark:text-amber-200">pastel</span> = sub-baris metrik
                  {" "}· <span className="text-rose-600 dark:text-rose-400">merah</span> = minus
                  {" "}· <span className="bg-[#FFC9C9] dark:bg-rose-500/25 px-1">merah muda</span> = Selisih IN ≠ 0
                </>
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
