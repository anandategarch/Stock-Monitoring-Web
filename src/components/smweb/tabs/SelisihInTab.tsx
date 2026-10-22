// Tab 📤 Rekap Selisih IN (FR-33) — paritas tab 6 desktop:
// IN (Accurate: 42.05+32.24+99.01) vs BARANG MASUK (rekap) + Hasil Audit + 🏆 SKOR RESTO.
"use client";

import { useMemo, useState } from "react";
import {
  ArrowDown, ArrowLeftRight, ArrowUp, ArrowUpDown, Database, Download, FileWarning,
  Info, PackagePlus, Trophy,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useSelisihIn } from "@/hooks/use-sm-api";
import type { SelisihInResponse } from "@/lib/types";
import { fmtInt, fmtQty, fmtRp, fmtSignedQty, signedQtyClass } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/smweb/empty-state";
import { StatCard } from "@/components/smweb/stat-card";
import { ExportButton } from "@/components/smweb/export-button";

type SelisihRow = SelisihInResponse["rows"][number];

/** Kolom tabel rekap yang bisa diklik untuk mengurutkan. */
type SortKey =
  | "restoCode" | "inAccurate" | "barangMasuk" | "selisih"
  | "skorResto" | "itemBerselisih" | "tanggalTerdampak";

const SORT_LABEL: Record<SortKey, string> = {
  restoCode: "Resto",
  inAccurate: "IN",
  barangMasuk: "Barang Masuk",
  selisih: "Selisih",
  skorResto: "SKOR RESTO",
  itemBerselisih: "Item Berselisih",
  tanggalTerdampak: "Tanggal Terdampak",
};

function sortValue(r: SelisihRow, key: SortKey): number | string {
  return key === "restoCode" ? r.restoCode : r[key];
}

/** Kepala kolom klik-urut: indikator arah + aria-sort (a11y). */
function SortHead({
  label, sortKey, activeKey, dir, onSort, align = "right",
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  dir: "asc" | "desc";
  onSort: (k: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sortKey === activeKey;
  const Icon = active ? (dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <TableHead
      className={align === "right" ? "text-right" : undefined}
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="inline-flex items-center gap-1 text-inherit hover:text-foreground"
        aria-label={`Urutkan berdasarkan ${label}`}
      >
        {label}
        <Icon className="h-3 w-3 opacity-70" aria-hidden />
      </button>
    </TableHead>
  );
}

/** Badge Hasil Audit (port logika macro VBA): OK bersih, SELISIH temuan. */
function HasilAuditBadge({ hasil }: { hasil: "OK" | "SELISIH" }) {
  if (hasil === "OK") {
    return (
      <Badge
        variant="outline"
        className="border-emerald-300 text-emerald-700 dark:border-emerald-500/40 dark:text-emerald-300"
      >
        OK
      </Badge>
    );
  }
  return (
    <Badge className="border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/15 dark:text-amber-300">
      SELISIH
    </Badge>
  );
}

export default function SelisihInTab({ snapshotId }: { snapshotId: string | null }) {
  const { data, isPending, error } = useSelisihIn(snapshotId);
  const [onlySelisih, setOnlySelisih] = useState(false); // paritas checkbox desktop
  const [sortKey, setSortKey] = useState<SortKey>("skorResto"); // default SKOR RESTO desc
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => data?.rows ?? [], [data]);

  const visibleRows = useMemo(() => {
    const filtered = onlySelisih ? rows.filter((r) => r.selisih !== 0) : rows;
    return [...filtered].sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const base =
        typeof av === "string" && typeof bv === "string"
          ? av.localeCompare(bv)
          : Number(av) - Number(bv);
      return sortDir === "asc" ? base : -base;
    });
  }, [rows, onlySelisih, sortKey, sortDir]);

  /** 3 resto dengan SKOR RESTO tertinggi (highlight ring; trofi untuk #1). */
  const top3 = useMemo(() => {
    const bySkor = [...rows].sort((a, b) => b.skorResto - a.skorResto);
    return bySkor.slice(0, 3).map((r) => r.restoCode);
  }, [rows]);

  const chartData = useMemo(
    () => rows.map((r) => ({ name: r.restoCode, selisih: Math.round(r.selisih) })),
    [rows],
  );

  const onSort = (k: SortKey) => {
    if (k === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      setSortDir(k === "restoCode" ? "asc" : "desc");
    }
  };

  if (!snapshotId) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot periode"
        description="Pilih periode pada bilah atas, atau jalankan pipeline di tab Proses & Ingest lalu komit snapshot untuk melihat rekap selisih IN."
      />
    );
  }

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-96" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={FileWarning}
        title="Gagal memuat rekap selisih IN"
        description={(error as Error).message}
      />
    );
  }

  if (!data) return null;

  const total = data.total;

  return (
    <div className="space-y-5">
      {/* Judul + deskripsi */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">📤 Rekap Selisih IN</h2>
          <p className="text-sm text-muted-foreground mt-1">
            IN (Accurate: 42.05+32.24+99.01) vs BARANG MASUK (rekap) + Hasil Audit + 🏆 SKOR RESTO.
          </p>
        </div>
        {snapshotId ? (
          <ExportButton snapshotId={snapshotId} sheet="selisih" size="sm" label="Export Selisih IN" />
        ) : null}
      </div>

      {/* KPI total — nilai ini KUANTITAS (audit 48-g-ui): jangan format Rupiah */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard
          title="Σ IN (Accurate, qty)"
          value={fmtQty(total.inAccurate)}
          sub="sumber 42.05 + 32.24 + 99.01"
          icon={Download}
          tone="emerald"
        />
        <StatCard
          title="Σ Barang Masuk (rekap, qty)"
          value={fmtQty(total.barangMasuk)}
          sub="sumber rekap BARANG MASUK"
          icon={PackagePlus}
        />
        <StatCard
          title="Σ Selisih (BM − IN, qty)"
          value={fmtSignedQty(total.selisih)}
          sub="bertanda dua arah (INV-2)"
          icon={ArrowLeftRight}
          tone={total.selisih < 0 ? "rose" : "emerald"}
        />
      </div>

      {/* Tabel rekap per resto */}
      <div className="rounded-xl border bg-card">
        <div className="p-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-medium">
            Rekap per resto
            <span className="font-normal text-muted-foreground">
              {" "}· urut {SORT_LABEL[sortKey]} {sortDir === "desc" ? "menurun" : "menaik"}
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline">
              Mode hitung: {data.mode === "bulan_ini" ? "Bulan Ini" : data.mode}
            </Badge>
            <Badge variant="secondary">
              {visibleRows.length} dari {rows.length} resto
            </Badge>
            <div className="flex items-center gap-2">
              <Checkbox
                id="selisih-in-filter"
                checked={onlySelisih}
                onCheckedChange={(v) => setOnlySelisih(v === true)}
              />
              <Label htmlFor="selisih-in-filter" className="cursor-pointer text-sm">
                Hanya resto dengan selisih ≠ 0
              </Label>
            </div>
          </div>
        </div>
        <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
          <table className="w-full caption-bottom text-sm">
            <caption className="sr-only">Rekap selisih IN per resto</caption>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                <SortHead label="Resto" sortKey="restoCode" activeKey={sortKey} dir={sortDir} onSort={onSort} align="left" />
                <SortHead label="IN" sortKey="inAccurate" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortHead label="Barang Masuk" sortKey="barangMasuk" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortHead label="Selisih" sortKey="selisih" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <TableHead>Hasil Audit</TableHead>
                <SortHead label="🏆 Skor Resto" sortKey="skorResto" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortHead label="Item Berselisih" sortKey="itemBerselisih" activeKey={sortKey} dir={sortDir} onSort={onSort} />
                <SortHead label="Tanggal Terdampak" sortKey="tanggalTerdampak" activeKey={sortKey} dir={sortDir} onSort={onSort} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleRows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                    Tidak ada resto yang cocok dengan filter.
                  </TableCell>
                </TableRow>
              ) : (
                visibleRows.map((r) => {
                  const rank = top3.indexOf(r.restoCode);
                  const isTop = rank >= 0;
                  return (
                    <TableRow key={r.restoCode}>
                      <TableCell>
                        <span className="font-medium">{r.restoCode}</span>{" "}
                        <span className="text-muted-foreground">{r.restoName}</span>
                      </TableCell>
                      <TableCell className="text-right cell-num">{fmtQty(r.inAccurate)}</TableCell>
                      <TableCell className="text-right cell-num">{fmtQty(r.barangMasuk)}</TableCell>
                      <TableCell className={cn("text-right cell-num", signedQtyClass(r.selisih))}>
                        {fmtSignedQty(r.selisih)}
                      </TableCell>
                      <TableCell>
                        <HasilAuditBadge hasil={r.hasilAudit} />
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={cn(
                            "inline-flex items-center justify-center gap-1 rounded-lg px-2 py-1 text-lg font-semibold cell-num",
                            isTop &&
                              "bg-amber-100 ring-2 ring-amber-400/80 dark:bg-amber-500/15 dark:ring-amber-500/50",
                          )}
                          title={isTop ? `Top ${rank + 1} SKOR RESTO periode ini` : undefined}
                        >
                          {rank === 0 ? (
                            <Trophy className="h-4 w-4 text-amber-600 dark:text-amber-400" aria-hidden />
                          ) : null}
                          {fmtInt(r.skorResto)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right cell-num">{fmtInt(r.itemBerselisih)}</TableCell>
                      <TableCell className="text-right cell-num">{fmtInt(r.tanggalTerdampak)}</TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </table>
        </div>
      </div>

      {/* Mini bar chart selisih per resto (bertanda) */}
      <div className="rounded-xl border bg-card p-4">
        <p className="text-sm font-medium mb-3">Selisih IN per resto (bertanda)</p>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v: number | string) => fmtQty(Number(v))}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  backgroundColor: "var(--popover)",
                  border: "1px solid var(--border)",
                  color: "var(--popover-foreground)",
                }}
              />
              <ReferenceLine y={0} stroke="var(--border)" />
              <Bar dataKey="selisih" name="Selisih IN" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Catatan paritas */}
      <p className="text-xs text-muted-foreground flex items-start gap-1.5">
        <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
        SKOR RESTO = item berselisih + tanggal terdampak (paritas macro VBA port).
      </p>
    </div>
  );
}
