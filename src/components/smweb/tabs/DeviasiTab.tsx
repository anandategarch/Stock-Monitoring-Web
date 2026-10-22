"use client";
// Tab 📦 Deviasi GR / PCS — Task 55-d: WIDE-MATRIX PER-TANGGAL ala desktop
// (referensi kebenaran deviasi_view.py v3.9.71): kolom SO(H-2)..SO(H+2) +
// In(H-1)..In(H+1) dengan heading dinamis _col_display_name (1565-1586),
// Sistem = qtySaldoAkhir@H (2005), Deviasi = SO_H − Sistem (2058) bold +
// minus merah, Nominal = harga×deviasi@H, Dev to BOM%, Dev. Bulan Lalu,
// Rank method=min per kelompok nama barang (v3.9.65), label CEK dengan
// re-komputasi live "ACR to BOM" saat ambang diubah (FR-30), tombol +FU →
// kasus follow-up (FR-43), klik baris → drill-down (FR-32).
// TANGGAL H & AMBANG ACR: input LOKAL + tombol Apply (heading kolom
// per-tanggal ikut berubah) — nilai ter-apply tersinkron ke store
// (INV-8: satu sumber untuk GR dan PCS, persist antar-reload).
// "Warna ala desktop" (Task 33 #2): latar #fef3c7 kolom kunci Deviasi &
// SO_H (HIGHLIGHT_COLS 523-524) + teks header kolom In teal #0e7490
// (IN_COLS/IN_HEADER_COLOR 542-543) + warna teks baris per label CEK utama.

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, FileWarning, Play, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useCreateCase } from "@/hooks/use-sm-api";
import { ExportButton } from "@/components/smweb/export-button";
import { useSmStore } from "@/store/use-sm-store";
import { CekBadgeList } from "@/components/smweb/badges";
import { EmptyState } from "@/components/smweb/empty-state";
import { DrilldownSheet, type DrilldownTarget } from "@/components/smweb/drilldown-sheet";
import { mergeCekLabels } from "@/lib/cek";
import { cekRowTextClass, DEV_KEYCOL_BG, naturalCompare } from "@/lib/desktop-parity";
import { CEK_LABELS, type CekLabel } from "@/lib/types";
import type {
  DeviasiDesktopResponse, DeviasiDesktopRow,
} from "@/lib/deviasi-def";
import { cn } from "@/lib/utils";
import {
  fmtInt, fmtPct, fmtQty, fmtRp, prevPeriodKey, signedQtyClass, signedRpClass,
} from "@/lib/format";

// Sentinel opsi "Semua" (Radix Select tidak menerima item bernilai string kosong).
const SEMUA = "__semua__";

// Sel nilai missing (INV-1: missing ≠ 0) — dipakai lintas kolom angka.
const NULL_CELL = <span className="text-muted-foreground/50">—</span>;

type SortKey = "resto" | "nama" | "sistem" | "deviasi" | "nominal" | "rank";
type SortDir = "asc" | "desc";

// Urutan kolom per-tanggal PERSIS COLUMNS desktop (deviasi_view.py:487-494):
// SO(H-2), SO(H-1), In(H-1), SO(H), In(H), SO(H+1), In(H+1), SO(H+2).
const DATE_COL_ORDER = [
  "SO_H-2", "SO_H-1", "In_H-1", "SO_H", "In_H", "SO_H+1", "In_H+1", "SO_H+2",
] as const;

/** Meta kolom per-tanggal — `get` mengambil nilai milik baris (index stabil:
 *  server membangun soCols/inCols dengan urutan sama untuk semua baris). */
interface DateColMeta {
  key: string;
  label: string;
  isIn: boolean;
  isKeyH: boolean;
  get: (row: DeviasiDesktopRow) => number | null;
}

// State aktif tombol segmen — aksen emerald selaras identitas SM-WEB.
const SEG_ON =
  "data-[state=on]:border-emerald-400 data-[state=on]:bg-emerald-50 data-[state=on]:text-emerald-700 " +
  "dark:data-[state=on]:border-emerald-500/60 dark:data-[state=on]:bg-emerald-500/15 dark:data-[state=on]:text-emerald-300";

// ---- Hook LOKAL Task 55-d (endpoint deviasi2 — use-sm-api.ts tak disentuh) ----

async function fetchDeviasiDesktop<T>(url: string): Promise<T> {
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
    throw new Error(msg);
  }
  return body as T;
}

function useDeviasiDesktop(snapshotId: string | null, qs: string) {
  return useQuery({
    queryKey: ["snapshots", snapshotId ?? "-", "deviasi2", qs],
    queryFn: () =>
      fetchDeviasiDesktop<DeviasiDesktopResponse>(`/api/snapshots/${snapshotId}/deviasi?${qs}`),
    enabled: Boolean(snapshotId),
    placeholderData: (prev) => prev,
  });
}

/** Header kolom sortable sisi klien — indikator ▲▼ + aria-sort; sticky top. */
function SortTh({
  label, active, dir, onSort, title, className,
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onSort: () => void;
  title?: string;
  className?: string;
}) {
  return (
    <th
      scope="col"
      title={title}
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : undefined}
      className={cn("sticky top-0 z-10 whitespace-nowrap border-b bg-background px-2.5 py-2 font-medium", className)}
    >
      <button
        type="button"
        onClick={onSort}
        className="inline-flex items-center gap-1 rounded-sm outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-emerald-600/50"
        aria-label={`Urutkan berdasarkan ${label}${active ? (dir === "asc" ? " (menaik)" : " (menurun)") : ""}`}
      >
        {label}
        <span
          aria-hidden
          className={cn(
            "text-[9px] leading-none",
            active ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground/40",
          )}
        >
          {active ? (dir === "asc" ? "▲" : "▼") : "▲▼"}
        </span>
      </button>
    </th>
  );
}

export default function DeviasiTab({ snapshotId }: { snapshotId: string | null }) {
  const {
    devGroup, setDevGroup, devH, setDevH, devAmbang, setDevAmbang,
    setActiveTab, devRowColor, setDevRowColor, uiCompact,
  } = useSmStore();

  // Input H/ambang = state LOKAL (Task 55-d): tombol Apply men-set nilai
  // query — tidak auto setelah tiap ketik; nilai ter-apply juga disinkron ke
  // store agar tetap satu sumber GR/PCS + persist (INV-8).
  const [hInput, setHInput] = useState(devH);
  const [hApplied, setHApplied] = useState(devH);
  const [ambangInput, setAmbangInput] = useState(devAmbang);
  const [ambangApplied, setAmbangApplied] = useState(devAmbang);

  const [drillTarget, setDrillTarget] = useState<DrilldownTarget | null>(null);
  const [search, setSearch] = useState("");
  const [cekFilter, setCekFilter] = useState<string>(""); // "" = semua label
  const [onlyDev, setOnlyDev] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("nama"); // default desktop: nama asc
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const qs = useMemo(
    () => `group=${devGroup}&h=${hApplied}&ambang=${ambangApplied}&onlyDevH=${onlyDev ? 1 : 0}`,
    [devGroup, hApplied, ambangApplied, onlyDev],
  );

  const { data, isPending, error, isFetching } = useDeviasiDesktop(snapshotId, qs);
  const createCase = useCreateCase();

  const hDirty = hInput !== hApplied;
  const ambangDirty = ambangInput !== ambangApplied;

  const applyH = () => {
    const n = Math.min(Math.max(Math.round(Number(hInput) || 1), 1), 31);
    setHInput(n);
    setHApplied(n);
    setDevH(n);
  };
  const applyAmbang = () => {
    const n = Math.min(Math.max(Math.round(Number(ambangInput) || 1), 1), 200);
    setAmbangInput(n);
    setAmbangApplied(n);
    setDevAmbang(n);
  };

  // Meta kolom per-tanggal — semua baris berbagi key/label sama (dibangun
  // server dari H); selisih hanya nilai per baris.
  const dateCols: DateColMeta[] = useMemo(() => {
    const first = data?.rows[0];
    if (!first) return [];
    const soIdx = new Map(first.soCols.map((c, i) => [c.key, i] as const));
    const inIdx = new Map(first.inCols.map((c, i) => [c.key, i] as const));
    const out: DateColMeta[] = [];
    for (const k of DATE_COL_ORDER) {
      const si = soIdx.get(k);
      const ii = inIdx.get(k);
      if (si !== undefined) {
        out.push({
          key: k, label: first.soCols[si].label, isIn: false, isKeyH: k === "SO_H",
          get: (r) => r.soCols[si]?.value ?? null,
        });
      } else if (ii !== undefined) {
        out.push({
          key: k, label: first.inCols[ii].label, isIn: true, isKeyH: false,
          get: (r) => r.inCols[ii]?.value ?? null,
        });
      }
    }
    return out;
  }, [data]);

  // Label CEK final per baris = label tersimpan (tanpa "ACR to BOM" run) +
  // hasil re-komputasi live dari ambang aktif (FR-30) — satu sumber untuk
  // badge, filter label CEK, dan haystack pencarian.
  const enriched = useMemo(
    () =>
      (data?.rows ?? []).map((row) => ({
        row,
        cekMerged: mergeCekLabels(row.cek, row.deviasi, row.acrTotal, ambangApplied),
      })),
    [data, ambangApplied],
  );

  const filterAktif = search.trim() !== "" || cekFilter !== "";

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    const out = enriched.filter(({ row, cekMerged }) => {
      if (cekFilter !== "" && !cekMerged.includes(cekFilter as CekLabel)) return false;
      if (q !== "") {
        const hay = [
          row.restoCode, row.restoName, row.itemName, row.satuan, row.kategori,
          fmtQty(row.sistem), fmtQty(row.deviasi), fmtRp(row.nominal),
          fmtQty(row.devBulanLalu), fmtQty(row.acrTotal),
          row.rank === null ? "" : String(row.rank),
          ...cekMerged,
        ].join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    const dir = sortDir === "asc" ? 1 : -1;
    const mag = (v: number | null) => (v === null ? null : Math.abs(v));
    const sortVal = (r: DeviasiDesktopRow): number | string | null =>
      sortKey === "resto" ? r.restoCode
        : sortKey === "sistem" ? r.sistem
          : sortKey === "deviasi" ? mag(r.deviasi)
            : sortKey === "nominal" ? mag(r.nominal)
              : r.rank;
    out.sort((a, b) => {
      // Sort nama (default) + tiebreak |Deviasi| desc dalam kelompok —
      // mirror layout default desktop v3.9.65.
      if (sortKey === "nama") {
        const c = dir * naturalCompare(a.row.itemName, b.row.itemName);
        if (c !== 0) return c;
        return dir === 1
          ? Math.abs(b.row.deviasi ?? 0) - Math.abs(a.row.deviasi ?? 0)
          : Math.abs(a.row.deviasi ?? 0) - Math.abs(b.row.deviasi ?? 0);
      }
      const av = sortVal(a.row);
      const bv = sortVal(b.row);
      if (typeof av === "string" || typeof bv === "string") {
        return dir * String(av).localeCompare(String(bv), "id");
      }
      if (av === null && bv === null) return 0;
      if (av === null) return 1; // null/blank selalu di bawah (kontrak §61/62)
      if (bv === null) return -1;
      return dir * (av - bv);
    });
    return out;
  }, [enriched, search, cekFilter, sortKey, sortDir]);

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
      return;
    }
    setSortKey(k);
    setSortDir(k === "deviasi" || k === "nominal" ? "desc" : "asc");
  };

  // Tombol +FU — implementasi lama dipertahankan verbatim (nilai mengikuti
  // kolom desktop: qty deviasi @H & nominal @H).
  const fu = (row: DeviasiDesktopRow) => {
    if (!data) return;
    createCase.mutate(
      {
        restoCode: row.restoCode,
        restoName: row.restoName,
        itemName: row.itemName,
        satuan: row.satuan,
        kategori: row.kategori,
        periodKey: data.periodKey,
        snapshotId: snapshotId ?? undefined,
        qtyDeviasi: row.deviasi,
        nominal: row.nominal,
        harga: row.harga,
      },
      {
        onError: (err) => {
          const e = err as Error & { status?: number };
          // 409 = kasus berulang → tautkan ke kasus lama (FR-43), bukan duplikat diam-diam.
          if (e.status === 409) toast.info(e.message);
          else toast.error(e.message);
        },
      },
    );
  };

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

  // Kolom: ✓ + Resto + Nama + per-tanggal + Sistem, Deviasi, Nominal,
  // Dev to BOM %, Dev. Bulan Lalu, Rank, CEK, Keterangan Audit (8 kolom).
  const colCount = 3 + dateCols.length + 8;
  // Kolom minus-merah-saja (tanggal/Sistem): minus merah, nol/plus netral —
  // desktop mewarnai minus per sel, bukan plus hijau (kolom bertanda
  // ekonomi Deviasi/Nominal/Dev. Bulan Lalu tetap memakai signedQtyClass).
  const minusClass = (v: number | null) =>
    v !== null && v < 0 ? "text-rose-600 dark:text-rose-400" : "";

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg sm:text-xl font-semibold tracking-tight">
            <span aria-hidden>📦</span> Deviasi GR / PCS
          </h2>
          {snapshotId ? (
            <ExportButton snapshotId={snapshotId} sheet="deviasi" size="sm" label="Export Deviasi" />
          ) : null}
        </div>
        <p className="text-sm text-muted-foreground">
          Wide-matrix per resto × barang dengan kolom per-tanggal SO &amp; In ala
          desktop — heading kolom mengikuti TANGGAL H (mis. H=25 → SO_23…SO_27).
          Deviasi = SO_H − Sistem, Nominal = harga × deviasi, plus Dev to
          BOM%, Dev. Bulan Lalu, dan Rank per kelompok nama barang (method=min
          ala desktop v3.9.65). Label CEK “ACR to BOM” dihitung ulang saat
          AMBANG diubah. Klik baris untuk drill-down.
        </p>
      </header>

      <section
        aria-label="Kontrol deviasi"
        className="rounded-xl border bg-card p-4 flex flex-wrap items-end gap-x-6 gap-y-4"
      >
        <div className="flex flex-col gap-1.5">
          <span id="dev-group-label" className="text-xs font-medium text-muted-foreground">Grup satuan</span>
          <ToggleGroup
            type="single"
            variant="outline"
            value={devGroup}
            onValueChange={(v) => {
              if (v === "GR" || v === "PCS") setDevGroup(v);
            }}
            aria-labelledby="dev-group-label"
          >
            <ToggleGroupItem value="GR" className={cn("h-9 px-4", SEG_ON)}>GR</ToggleGroupItem>
            <ToggleGroupItem value="PCS" className={cn("h-9 px-4", SEG_ON)}>PCS</ToggleGroupItem>
          </ToggleGroup>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-h" className="text-xs font-medium text-muted-foreground">Tanggal H (1–31)</Label>
          <div className="flex items-center gap-1.5">
            <Input
              id="dev-h"
              type="number"
              min={1}
              max={31}
              value={hInput}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isNaN(n)) setHInput(n);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyH();
              }}
              className="w-[76px]"
            />
            <Button
              variant="outline"
              size="sm"
              className="h-9"
              onClick={applyH}
              disabled={!hDirty}
              title="Terapkan H — heading kolom per-tanggal ikut berubah"
            >
              Apply
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Heading kolom per-tanggal mengikuti H = {hApplied}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-ambang" className="text-xs font-medium text-muted-foreground">Ambang ACR % (1–200)</Label>
          <div className="flex items-center gap-1.5">
            <Input
              id="dev-ambang"
              type="number"
              min={1}
              max={200}
              value={ambangInput}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isNaN(n)) setAmbangInput(n);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyAmbang();
              }}
              className="w-[76px]"
            />
            <Button
              variant="outline"
              size="sm"
              className="h-9"
              onClick={applyAmbang}
              disabled={!ambangDirty}
              title="Terapkan ambang — label CEK ACR to BOM langsung dihitung ulang"
            >
              Apply
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground">
            mengubah AMBANG langsung menghitung ulang label CEK tanpa run ulang (FR-30)
          </p>
        </div>

        <div className="flex flex-1 min-w-[220px] flex-col gap-1.5">
          <Label htmlFor="dev-search" className="text-xs font-medium text-muted-foreground">Cari</Label>
          <Input
            id="dev-search"
            type="search"
            placeholder="Cari nama barang / resto / kategori / label CEK…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-cek" className="text-xs font-medium text-muted-foreground">Filter CEK</Label>
          <Select value={cekFilter === "" ? SEMUA : cekFilter} onValueChange={(v) => setCekFilter(v === SEMUA ? "" : v)}>
            <SelectTrigger id="dev-cek" className="w-[210px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SEMUA}>Semua label</SelectItem>
              {CEK_LABELS.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Switch id="dev-only" checked={onlyDev} onCheckedChange={setOnlyDev} />
          <Label htmlFor="dev-only" className="text-xs">Hanya baris deviasi H ≠ 0</Label>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Switch id="dev-row-color" checked={devRowColor} onCheckedChange={setDevRowColor} />
          <Label
            htmlFor="dev-row-color"
            className="text-xs"
            title="Latar #fef3c7 kolom kunci (Deviasi & SO_H) + teks header teal kolom In + warna teks baris per label CEK utama — mirror desktop"
          >
            Warna ala desktop
          </Label>
        </div>
      </section>

      {isPending ? (
        <Skeleton className="h-[60vh] w-full rounded-xl" />
      ) : error ? (
        <EmptyState icon={FileWarning} title="Gagal memuat data deviasi" description={(error as Error).message} />
      ) : data ? (
        <section aria-label="Tabel deviasi" className="space-y-2">
          <div
            aria-busy={isFetching}
            className={cn(
              "max-h-[70vh] overflow-auto nice-scroll rounded-xl border bg-card transition-opacity",
              isFetching && "opacity-60",
            )}
          >
            <table className="w-full text-sm border-separate border-spacing-0">
              <caption className="sr-only">
                Tabel deviasi grup {devGroup} per resto × barang dengan kolom
                per-tanggal SO/In untuk H={hApplied}, ambang ACR {ambangApplied} persen
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="sticky left-0 top-0 z-30 w-14 min-w-[3.5rem] border-b bg-background px-1 py-2">
                    <span className="sr-only">Aksi follow-up</span>
                  </th>
                  <SortTh
                    label="Resto"
                    active={sortKey === "resto"}
                    dir={sortDir}
                    onSort={() => toggleSort("resto")}
                    className="min-w-[80px] text-left lg:left-14 lg:z-30 lg:w-28 lg:min-w-[7rem]"
                  />
                  <SortTh
                    label="Nama Barang"
                    active={sortKey === "nama"}
                    dir={sortDir}
                    onSort={() => toggleSort("nama")}
                    className="min-w-[190px] text-left lg:left-[168px] lg:z-30"
                  />
                  {dateCols.map((c) => (
                    <th
                      key={c.key}
                      scope="col"
                      title={c.isIn
                        ? "Kiriman IN tanggal ini — BUKAN kolom Stock/SO (header teal ala desktop IN_HEADER_COLOR #0e7490)"
                        : c.isKeyH
                          ? "Stok fisik (SO) tanggal H — highlight #fef3c7 saat “Warna ala desktop” aktif (HIGHLIGHT_COLS desktop)"
                          : "Stok fisik (SO) tanggal ini"}
                      className={cn(
                        "sticky top-0 z-10 min-w-[64px] whitespace-nowrap border-b bg-background px-2.5 py-2 text-right font-medium",
                        c.isIn && "text-[#0e7490] dark:text-cyan-300",
                      )}
                    >
                      {c.label}
                    </th>
                  ))}
                  <SortTh
                    label="Sistem"
                    active={sortKey === "sistem"}
                    dir={sortDir}
                    onSort={() => toggleSort("sistem")}
                    title="Saldo akhir sistem @H (2.SALDO AKHIR — desktop baris 2005)"
                    className="min-w-[80px] text-right"
                  />
                  <SortTh
                    label="Deviasi"
                    active={sortKey === "deviasi"}
                    dir={sortDir}
                    onSort={() => toggleSort("deviasi")}
                    title="SO_H − Sistem (desktop baris 2058) — bold; minus merah"
                    className="min-w-[86px] text-right"
                  />
                  <SortTh
                    label="Nominal"
                    active={sortKey === "nominal"}
                    dir={sortDir}
                    onSort={() => toggleSort("nominal")}
                    title="Harga efektif @H × Deviasi"
                    className="min-w-[100px] text-right"
                  />
                  <th
                    scope="col"
                    title="|Deviasi| / Σ ACR semua hari × 100% (Loss Surplus to BOM — desktop baris 505)"
                    className="sticky top-0 z-10 min-w-[90px] whitespace-nowrap border-b bg-background px-2.5 py-2 text-right font-medium"
                  >
                    Dev to BOM %
                  </th>
                  <th
                    scope="col"
                    title={data.hasPrev
                      ? `Σ qtyDeviasi pasangan ini pada snapshot periode ${data.prevPeriodKey}`
                      : "Snapshot periode lalu tidak ada — sel “—”"}
                    className="sticky top-0 z-10 min-w-[96px] whitespace-nowrap border-b bg-background px-2.5 py-2 text-right font-medium"
                  >
                    Dev. Bulan Lalu
                  </th>
                  <SortTh
                    label="Rank"
                    active={sortKey === "rank"}
                    dir={sortDir}
                    onSort={() => toggleSort("rank")}
                    title="Peringkat |Deviasi| dalam kelompok nama barang (semua resto) — method=min ala desktop v3.9.65; dev 0/tanpa data → kosong"
                    className="min-w-[64px] text-right"
                  />
                  <th
                    scope="col"
                    title={`Label pemeriksaan — "ACR to BOM" dihitung ulang dari ambang ${ambangApplied}%`}
                    className="sticky top-0 z-10 border-b bg-background px-2.5 py-2 text-left font-medium"
                  >
                    CEK
                  </th>
                  <th
                    scope="col"
                    title="Catatan audit B1–B4 (badge kecil bila ada)"
                    className="sticky top-0 z-10 border-b bg-background px-2.5 py-2 text-left font-medium"
                  >
                    Keterangan Audit
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={colCount} className="border-b px-4 py-10 text-center text-sm text-muted-foreground">
                      Tidak ada baris yang cocok dengan pencarian/filter saat ini.
                      {onlyDev ? " Saklar “Hanya baris deviasi H ≠ 0” aktif — tidak ada pasangan dengan deviasi H ≠ 0." : ""}
                    </td>
                  </tr>
                ) : (
                  visible.map(({ row, cekMerged }) => {
                    // Warna teks baris ala desktop: label CEK utama → fg
                    // (mirror deviasi_view.py:2774-2788). Kosong bila netral
                    // atau toggle mati.
                    const rowText = devRowColor ? cekRowTextClass(cekMerged) : "";
                    return (
                    <tr
                      key={row.fingerprint}
                      className="group/row cursor-pointer hover:bg-muted/40"
                      onClick={() => setDrillTarget({ resto: row.restoCode, item: row.itemName })}
                    >
                      <td className="sticky left-0 z-20 border-b border-border/60 bg-card px-1 py-1 text-center group-hover/row:bg-muted/40">
                        <Button
                          variant="outline"
                          className={cn(uiCompact ? "h-6" : "h-9", "px-1.5 text-xs")}
                          disabled={createCase.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            fu(row);
                          }}
                          aria-label={`Buat kasus follow-up untuk ${row.itemName} (${row.restoCode})`}
                        >
                          <Plus className="h-3.5 w-3.5" aria-hidden /> FU
                        </Button>
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 lg:sticky lg:left-14 lg:z-20 lg:w-28 lg:min-w-[7rem] lg:bg-card lg:group-hover/row:bg-muted/40",
                        rowText,
                      )}>
                        <span className="font-medium">{row.restoCode}</span>
                        <span className="block text-[11px] text-muted-foreground">{row.restoName}</span>
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 lg:sticky lg:left-[168px] lg:z-20 lg:bg-card lg:group-hover/row:bg-muted/40",
                        rowText,
                      )}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDrillTarget({ resto: row.restoCode, item: row.itemName });
                          }}
                          className="text-left font-medium hover:underline"
                          aria-label={`Buka rincian ${row.itemName} (${row.restoCode})`}
                        >
                          {row.itemName}
                          {/* Mode rapat: satuan · kategori + penanda * ikut
                              DALAM tombol nowrap — subline span lama
                              (wrappable) memaksa nama panjang melipat ke 2
                              baris dan menggembungkan tinggi baris. */}
                          {uiCompact ? (
                            <span className="font-normal text-muted-foreground">
                              {" "}{row.satuan} · {row.kategori}
                              {!row.konversiOk ? (
                                <span
                                  className="text-amber-600 dark:text-amber-400"
                                  title="Konversi satuan gagal — nominal null (INV-3)"
                                >
                                  {" "}*
                                </span>
                              ) : null}
                            </span>
                          ) : null}
                        </button>
                        {!uiCompact ? (
                          <span className="block text-[11px] text-muted-foreground">
                            {row.satuan} · {row.kategori}
                            {!row.konversiOk ? (
                              <span
                                className="text-amber-600 dark:text-amber-400"
                                title="Konversi satuan gagal — nominal null (INV-3)"
                              >
                                {" "}*
                              </span>
                            ) : null}
                          </span>
                        ) : null}
                      </td>
                      {dateCols.map((c) => {
                        const v = c.get(row);
                        return (
                          <td
                            key={c.key}
                            className={cn(
                              "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                              // Kolom SO_H ikut di-highlight bersama Deviasi
                              // saat warna ON (HIGHLIGHT_COLS desktop 523-524).
                              c.isKeyH && devRowColor && DEV_KEYCOL_BG,
                              minusClass(v),
                            )}
                          >
                            {v === null ? NULL_CELL : fmtQty(v)}
                          </td>
                        );
                      })}
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                        minusClass(row.sistem),
                      )}>
                        {row.sistem === null ? NULL_CELL : fmtQty(row.sistem)}
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num font-semibold",
                        // Kolom kunci ala desktop #fef3c7 (HIGHLIGHT_BG
                        // deviasi_view.py:523-524 — kolom Deviasi & SO_H).
                        devRowColor && DEV_KEYCOL_BG,
                        signedQtyClass(row.deviasi),
                      )}>
                        {row.deviasi === null ? NULL_CELL : fmtQty(row.deviasi)}
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                        signedRpClass(row.nominal),
                      )}>
                        {row.nominal === null ? NULL_CELL : fmtRp(row.nominal)}
                      </td>
                      <td className="border-b border-border/60 px-2.5 py-1.5 text-right cell-num">
                        {row.devToBomPct === null ? NULL_CELL : fmtPct(row.devToBomPct)}
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                        signedQtyClass(row.devBulanLalu),
                      )}>
                        {row.devBulanLalu === null ? NULL_CELL : fmtQty(row.devBulanLalu)}
                      </td>
                      <td className="border-b border-border/60 px-2.5 py-1.5 text-right cell-num">
                        {row.rank === null ? NULL_CELL : fmtInt(row.rank)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5", uiCompact && "max-w-[210px]")}>
                        <CekBadgeList cek={cekMerged} compact asText={uiCompact} />
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5", uiCompact && "max-w-[150px]")}>
                        <CekBadgeList cek={[]} auditNotes={row.auditNotes} compact />
                      </td>
                    </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-1 text-xs text-muted-foreground lg:flex-row lg:items-center lg:justify-between">
            <p>
              Menampilkan <span className="font-medium text-foreground">{fmtInt(visible.length)}</span>{" "}
              dari {fmtInt(data.totalRows)} baris{filterAktif ? " (setelah filter)" : ""}
            </p>
            <p>
              <span className="text-muted-foreground/50">“—”</span> = tidak ada data (missing ≠ 0 — INV-1) ·
              minus = kekurangan, bertanda (INV-2) · * = konversi satuan gagal (INV-3)
            </p>
            {devRowColor ? (
              <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden className="inline-block h-3 w-3 rounded-sm bg-[#fef3c7]" />
                  = kolom kunci (Deviasi &amp; SO_H)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden className="inline-block h-3 w-3 rounded-sm bg-[#0e7490]" />
                  = kolom In
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden className="inline-block h-3 w-3 rounded-sm bg-rose-600" />
                  = minus
                </span>
              </p>
            ) : null}
            {!data.hasPrev ? (
              <p>
                Snapshot periode lalu ({prevPeriodKey(data.periodKey)}) tidak ada — kolom
                Dev. Bulan Lalu menampilkan <span className="text-muted-foreground/50">“—”</span>
              </p>
            ) : null}
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
