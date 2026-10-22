"use client";
// Tab 📦 Deviasi GR / PCS — gabungan tab 4–5 desktop (FR-30): wide-matrix resto × barang,
// deviasi bertanda (INV-2), label CEK dengan re-komputasi live "ACR to BOM" saat ambang
// diubah, rank nominal per resto (§61/62), sort sisi klien, tombol +FU → kasus follow-up
// (FR-43), klik baris → drill-down (FR-32). TANGGAL H & AMBANG ACR satu sumber untuk
// GR dan PCS (paritas v3.9.21) dan terikat store (INV-8).
// Task 33: #2 toggle "Warna ala desktop" (latar amber kolom kunci + teks baris per
// label CEK utama — mirror deviasi_view.py v3.9.71); #3 susunan "Per Barang"
// (kelompok nama barang + rank method=min per kelompok — mirror v3.9.65 / 01.1 CEK
// STOCK V2.xlsb, dev=0 → kosong).

import { useEffect, useMemo, useState } from "react";
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
import { useCreateCase, useDeviasi, useRestos } from "@/hooks/use-sm-api";
import { useSmStore } from "@/store/use-sm-store";
import { CekBadgeList } from "@/components/smweb/badges";
import { EmptyState } from "@/components/smweb/empty-state";
import { DrilldownSheet, type DrilldownTarget } from "@/components/smweb/drilldown-sheet";
import { mergeCekLabels } from "@/lib/cek";
import {
  cekRowTextClass, DEV_KEYCOL_BG, naturalCompare, rankMinInGroups,
} from "@/lib/desktop-parity";
import { CEK_LABELS, type CekLabel, type DeviasiRow } from "@/lib/types";
import { cn } from "@/lib/utils";
import { fmtInt, fmtQty, fmtRp, signedQtyClass, signedRpClass } from "@/lib/format";

// Sentinel opsi "Semua" (Radix Select tidak menerima item bernilai string kosong).
const SEMUA = "__semua__";

type SortKey = "nama" | "devH" | "nominalBulan" | "rank";
type SortDir = "asc" | "desc";

// State aktif tombol segmen — aksen emerald selaras identitas SM-WEB.
const SEG_ON =
  "data-[state=on]:border-emerald-400 data-[state=on]:bg-emerald-50 data-[state=on]:text-emerald-700 " +
  "dark:data-[state=on]:border-emerald-500/60 dark:data-[state=on]:bg-emerald-500/15 dark:data-[state=on]:text-emerald-300";

/** Header kolom sortable sisi klien — indikator ▲▼ + aria-sort. */
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
      className={cn("whitespace-nowrap border-b bg-background px-2.5 py-2 font-medium", className)}
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
    devGroup, setDevGroup, devResto, setDevResto, devH, setDevH,
    devAmbang, setDevAmbang, setActiveTab,
    devRowColor, setDevRowColor, devLayout, setDevLayout, uiCompact,
  } = useSmStore();

  const [drillTarget, setDrillTarget] = useState<DrilldownTarget | null>(null);
  const [search, setSearch] = useState("");
  const [cekFilter, setCekFilter] = useState<string>(""); // "" = semua label
  const [onlyDev, setOnlyDev] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("devH"); // default: |Deviasi H| desc
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const { data: restosData } = useRestos(snapshotId);
  const restos = useMemo(() => restosData?.restos ?? [], [restosData]);

  // Bersihkan pilihan resto yang tidak ada di snapshot aktif — “Semua resto” selalu sah.
  useEffect(() => {
    if (restos.length === 0) return;
    if (devResto !== "" && !restos.some((r) => r.restoCode === devResto)) setDevResto("");
  }, [restos, devResto, setDevResto]);

  const qs = useMemo(
    () => `group=${devGroup}&h=${devH}&ambang=${devAmbang}${devResto ? `&resto=${devResto}` : ""}`,
    [devGroup, devH, devAmbang, devResto],
  );

  const { data, isPending, error, isFetching } = useDeviasi(snapshotId, qs);
  const createCase = useCreateCase();

  // Label CEK final per baris = label tersimpan (tanpa "ACR to BOM" run) + hasil
  // re-komputasi live dari ambang aktif (FR-30) — satu sumber untuk badge, filter
  // label CEK, dan haystack pencarian.
  const enriched = useMemo(
    () =>
      (data?.rows ?? []).map((row) => ({
        row,
        cekMerged: mergeCekLabels(row.cek, row.deviasiH, row.acrTotal, devAmbang),
      })),
    [data, devAmbang],
  );

  // Rank per KELOMPOK nama barang (Task 33 #3) — mirror desktop v3.9.65
  // (deviasi_view.py:2566-2572): |Deviasi H| desc method=min di dalam kelompok
  // nama barang, atas frame terfilter; dev=0/tanpa data → KOSONG. Hanya dihitung
  // saat mode kelompok; mode flat tetap memakai rankNominal per resto (server).
  const groupRankByRow = useMemo(() => {
    if (devLayout !== "kelompok") return null;
    const byWrapper = rankMinInGroups(
      enriched, (vr) => vr.row.itemName, (vr) => vr.row.deviasiH,
    );
    const byRow = new Map<DeviasiRow, number | null>();
    for (const [vr, rank] of byWrapper) byRow.set(vr.row, rank);
    return byRow;
  }, [devLayout, enriched]);

  const filterAktif = search.trim() !== "" || cekFilter !== "" || onlyDev || devResto !== "";

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    const out = enriched.filter(({ row, cekMerged }) => {
      if (onlyDev && (row.deviasiH === null || row.deviasiH === 0)) return false;
      if (cekFilter !== "" && !cekMerged.includes(cekFilter as CekLabel)) return false;
      if (q !== "") {
        const hay = [
          row.restoCode, row.restoName, row.itemName, row.satuan, row.kategori,
          fmtQty(row.deviasiH), fmtQty(row.deviasiBulan), fmtQty(row.acrTotal),
          fmtRp(row.nominalH), fmtRp(row.nominalBulan),
          row.rankNominal === null ? "" : String(row.rankNominal),
          ...cekMerged,
        ].join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    const dir = sortDir === "asc" ? 1 : -1;
    const mag = (v: number | null) => (v === null ? null : Math.abs(v));
    // Mode KELOMPOK (Task 33 #3): layout default desktop — nama barang asc
    // (natural) lalu |Deviasi H| desc di dalam kelompok (mirror v3.9.65).
    // Kondisi mencakup sortKey "devH"+desc (default local useState) supaya
    // layout bertahan PASCA-RELOAD: sortKey tidak dipersist, devLayout iya.
    const kelompokDefault =
      devLayout === "kelompok" &&
      (sortKey === "nama" || (sortKey === "devH" && sortDir === "desc"));
    if (kelompokDefault) {
      out.sort((a, b) => {
        const c = sortKey === "nama"
          ? dir * naturalCompare(a.row.itemName, b.row.itemName)
          : naturalCompare(a.row.itemName, b.row.itemName);
        if (c !== 0) return c;
        return Math.abs(b.row.deviasiH ?? 0) - Math.abs(a.row.deviasiH ?? 0);
      });
      return out;
    }
    const sortVal = (r: DeviasiRow): number | null =>
      sortKey === "devH" ? mag(r.deviasiH)
        : sortKey === "nominalBulan" ? mag(r.nominalBulan)
          : sortKey === "rank"
            ? (groupRankByRow ? groupRankByRow.get(r) ?? null : r.rankNominal)
            : r.rankNominal;
    out.sort((a, b) => {
      if (sortKey === "nama") return dir * a.row.itemName.localeCompare(b.row.itemName, "id");
      const av = sortVal(a.row);
      const bv = sortVal(b.row);
      if (av === null && bv === null) return 0;
      if (av === null) return 1; // null/blank selalu di bawah (kontrak §61/62)
      if (bv === null) return -1;
      return dir * (av - bv);
    });
    return out;
  }, [enriched, search, cekFilter, onlyDev, sortKey, sortDir, devLayout, groupRankByRow]);

  const toggleSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
      return;
    }
    setSortKey(k);
    setSortDir(k === "devH" || k === "nominalBulan" ? "desc" : "asc");
  };

  const fu = (row: DeviasiRow) => {
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
        qtyDeviasi: row.deviasiH,
        nominal: row.nominalBulan,
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

  const colCount = (devResto === "" ? 1 : 0) + 10;

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-lg sm:text-xl font-semibold tracking-tight">
          <span aria-hidden>📦</span> Deviasi GR / PCS
        </h2>
        <p className="text-sm text-muted-foreground">
          Wide-matrix deviasi bertanda per resto × barang — gabungan tab Deviasi GR + PCS
          desktop. TANGGAL H &amp; AMBANG ACR di sini satu sumber untuk GR dan PCS
          (paritas v3.9.21); label CEK “ACR to BOM” langsung dihitung ulang saat ambang
          diubah. Klik baris untuk drill-down. Susun “Per Barang” menata baris per
          kelompok nama barang dengan rank per kelompok ala desktop; “Warna ala
          desktop” menyalakan latar kolom kerja + warna teks per label CEK.
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
          <span id="dev-layout-label" className="text-xs font-medium text-muted-foreground">Susun</span>
          <ToggleGroup
            type="single"
            variant="outline"
            value={devLayout}
            onValueChange={(v) => {
              if (v === "flat" || v === "kelompok") {
                setDevLayout(v);
                // Sort header mengikuti mode: kelompok = layout desktop (nama asc
                // + |Dev H| desc per kelompok); flat = default lama (|Dev H| desc).
                if (v === "kelompok") {
                  setSortKey("nama");
                  setSortDir("asc");
                } else {
                  setSortKey("devH");
                  setSortDir("desc");
                }
              }
            }}
            aria-labelledby="dev-layout-label"
          >
            <ToggleGroupItem value="flat" className={cn("h-9 px-3", SEG_ON)}>Rata</ToggleGroupItem>
            <ToggleGroupItem value="kelompok" className={cn("h-9 px-3", SEG_ON)}>Per Barang</ToggleGroupItem>
          </ToggleGroup>
          <p className="text-[11px] text-muted-foreground">
            {devLayout === "kelompok"
              ? "Kelompok nama barang + rank per kelompok (ala desktop)"
              : "Sort bebas per kolom (default |Deviasi H| desc)"}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-resto" className="text-xs font-medium text-muted-foreground">Resto</Label>
          <Select
            value={devResto === "" ? SEMUA : devResto}
            onValueChange={(v) => setDevResto(v === SEMUA ? "" : v)}
          >
            <SelectTrigger id="dev-resto" className="w-[230px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SEMUA}>Semua resto</SelectItem>
              {restos.map((r) => (
                <SelectItem key={r.restoCode} value={r.restoCode}>
                  {r.restoCode} · {r.restoName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-h" className="text-xs font-medium text-muted-foreground">Tanggal H (1–31)</Label>
          <Input
            id="dev-h"
            type="number"
            min={1}
            max={31}
            value={devH}
            onChange={(e) => {
              const n = Number(e.target.value);
              if (!Number.isNaN(n)) setDevH(n);
            }}
            className="w-[76px]"
          />
          <p className="text-[11px] text-muted-foreground">Cut-off deviasi H &amp; nominal H</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="dev-ambang" className="text-xs font-medium text-muted-foreground">Ambang ACR % (1–200)</Label>
          <Input
            id="dev-ambang"
            type="number"
            min={1}
            max={200}
            value={devAmbang}
            onChange={(e) => {
              const n = Number(e.target.value);
              if (!Number.isNaN(n)) setDevAmbang(n);
            }}
            className="w-[76px]"
          />
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
          <Label htmlFor="dev-row-color" className="text-xs" title="Latar amber kolom kerja (Deviasi/Nominal H) + warna teks baris per label CEK utama — mirror desktop">
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
                Tabel deviasi grup {devGroup} per resto × barang, tanggal H {devH},
                ambang ACR {devAmbang} persen
              </caption>
              <thead className="sticky top-0 z-10 bg-background">
                <tr>
                  {devResto === "" ? (
                    <th scope="col" className="border-b bg-background px-2.5 py-2 text-left font-medium">
                      Resto
                    </th>
                  ) : null}
                  <SortTh
                    label="Nama Barang"
                    active={sortKey === "nama"}
                    dir={sortDir}
                    onSort={() => toggleSort("nama")}
                    className="min-w-[190px] text-left"
                  />
                  <th scope="col" className="border-b bg-background px-2.5 py-2 text-left font-medium">
                    Kategori
                  </th>
                  <SortTh
                    label="Deviasi H"
                    active={sortKey === "devH"}
                    dir={sortDir}
                    onSort={() => toggleSort("devH")}
                    title={`Σ deviasi bertanda hari 1–${devH}`}
                    className="text-right"
                  />
                  <th
                    scope="col"
                    title="Σ deviasi bertanda seluruh hari bulan"
                    className="border-b bg-background px-2.5 py-2 text-right font-medium"
                  >
                    Deviasi Bulan
                  </th>
                  <th
                    scope="col"
                    title="Σ pemakaian ACR sepanjang bulan"
                    className="border-b bg-background px-2.5 py-2 text-right font-medium"
                  >
                    Total ACR
                  </th>
                  <th
                    scope="col"
                    title={`Σ nominal deviasi hari 1–${devH}`}
                    className="border-b bg-background px-2.5 py-2 text-right font-medium"
                  >
                    Nominal H
                  </th>
                  <SortTh
                    label="Nominal Bulan"
                    active={sortKey === "nominalBulan"}
                    dir={sortDir}
                    onSort={() => toggleSort("nominalBulan")}
                    title="Σ nominal deviasi sepanjang bulan"
                    className="text-right"
                  />
                  <SortTh
                    label="Rank"
                    active={sortKey === "rank"}
                    dir={sortDir}
                    onSort={() => toggleSort("rank")}
                    title={devLayout === "kelompok"
                      ? "Peringkat |Deviasi H| dalam kelompok nama barang — mirror desktop v3.9.65 (method=min; deviasi 0/tanpa data → kosong)"
                      : "Peringkat |nominal bulan| di dalam resto — dev 0/blank → kosong (kontrak §61/62)"}
                    className="text-right"
                  />
                  <th
                    scope="col"
                    title={`Label pemeriksaan — "ACR to BOM" dihitung ulang dari ambang ${devAmbang}%`}
                    className="border-b bg-background px-2.5 py-2 text-left font-medium"
                  >
                    CEK
                  </th>
                  <th scope="col" className="border-b bg-background px-2.5 py-2 font-medium">
                    <span className="sr-only">Aksi follow-up</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={colCount} className="border-b px-4 py-10 text-center text-sm text-muted-foreground">
                      Tidak ada baris yang cocok dengan pencarian/filter saat ini.
                    </td>
                  </tr>
                ) : (
                  visible.map(({ row, cekMerged }, i) => {
                    // Batas kelompok (mode Per Barang): hairline netral — bukan
                    // "sekat warna" desktop era lama (dihapus atas permintaan
                    // pemilik v3.9.61), hanya garis tipis penanda ganti kelompok.
                    const isGroupStart =
                      devLayout === "kelompok" &&
                      (i === 0 || visible[i - 1].row.itemName !== row.itemName);
                    const sepCls = isGroupStart ? "border-t border-border/70" : "";
                    // Warna teks baris ala desktop: label CEK utama → fg (mirror
                    // deviasi_view.py:2774-2788). Kosong bila netral/toggle mati.
                    const rowText = devRowColor ? cekRowTextClass(cekMerged) : "";
                    // Rank mode kelompok (method=min per barang) vs mode flat
                    // (rankNominal per resto dari server — kontrak §61/62).
                    const rankVal = groupRankByRow
                      ? (groupRankByRow.get(row) ?? null)
                      : row.rankNominal;
                    return (
                    <tr
                      key={row.fingerprint}
                      className="cursor-pointer hover:bg-muted/40"
                      onClick={() => setDrillTarget({ resto: row.restoCode, item: row.itemName })}
                    >
                      {devResto === "" ? (
                        <td className={cn("whitespace-nowrap border-b border-border/60 px-2.5 py-1.5", sepCls, rowText)}>
                          <span className="font-medium">{row.restoCode}</span>
                          <span className="block text-[11px] text-muted-foreground">{row.restoName}</span>
                        </td>
                      ) : null}
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5", sepCls, rowText)}>
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
                          {/* Mode rapat: satuan + penanda * ikut DALAM tombol nowrap —
                              mirror kolom Nama Barang + Satuan desktop (1 baris);
                              subline span lama (wrappable) memaksa nama panjang
                              melipat ke 2 baris dan menggembungkan tinggi baris. */}
                          {uiCompact ? (
                            <span className="font-normal text-muted-foreground">
                              {" "}{row.satuan}
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
                            {row.satuan}
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
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5 text-muted-foreground", sepCls)}>
                        {row.kategori}
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                        sepCls,
                        // Latar kolom kunci ala desktop #fef3c7 (HIGHLIGHT_BG
                        // deviasi_view.py:523-524 — kolom Deviasi & SO_H; analog
                        // web: Deviasi H + Nominal H) — hanya saat toggle aktif.
                        devRowColor && DEV_KEYCOL_BG,
                        signedQtyClass(row.deviasiH),
                      )}>
                        {row.deviasiH === null ? <span className="text-muted-foreground/50">—</span> : fmtQty(row.deviasiH)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5 text-right cell-num", sepCls, signedQtyClass(row.deviasiBulan))}>
                        {row.deviasiBulan === null ? <span className="text-muted-foreground/50">—</span> : fmtQty(row.deviasiBulan)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5 text-right cell-num text-muted-foreground", sepCls)}>
                        {fmtQty(row.acrTotal)}
                      </td>
                      <td className={cn(
                        "border-b border-border/60 px-2.5 py-1.5 text-right cell-num",
                        sepCls,
                        devRowColor && DEV_KEYCOL_BG,
                        signedRpClass(row.nominalH),
                      )}>
                        {row.nominalH === null ? <span className="text-muted-foreground/50">—</span> : fmtRp(row.nominalH)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5 text-right cell-num", sepCls, signedRpClass(row.nominalBulan))}>
                        {row.nominalBulan === null ? <span className="text-muted-foreground/50">—</span> : fmtRp(row.nominalBulan)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5 text-right cell-num", sepCls)}>
                        {rankVal === null ? <span className="text-muted-foreground/50">—</span> : fmtInt(rankVal)}
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1.5", sepCls, uiCompact && "max-w-[210px]")}>
                        <CekBadgeList cek={cekMerged} auditNotes={row.auditNotes} compact asText={uiCompact} />
                      </td>
                      <td className={cn("border-b border-border/60 px-2.5 py-1 text-center", sepCls)}>
                        <Button
                          variant="outline"
                          className={cn(uiCompact ? "h-6" : "h-9", "px-2.5 text-xs")}
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
              {devRowColor ? (
                <>· <span className="text-[#92400e] dark:text-amber-300">teks baris</span> = label CEK utama (ala desktop)</>
              ) : null}
            </p>
            {devLayout === "kelompok" ? (
              <p>
                Susunan <span className="font-medium text-foreground">Per Barang</span>:
                nama asc (natural) lalu |Deviasi H| desc · Rank = method=min dalam
                kelompok (mirror desktop v3.9.65) · garis tipis = batas kelompok
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
