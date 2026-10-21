// Tab 📋 Laporan Deviasi (FR-35) — paritas tab 7 desktop, 3 mode:
// ⚖ Komparasi (kini vs SNAPSHOT periode lalu) · 🚨 Anomali COM · 💰 Nominal (H).
"use client";

import { useState } from "react";
import {
  AlertTriangle, Database, FileWarning, GitCompare, ScrollText,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLaporan } from "@/hooks/use-sm-api";
import type { LaporanAnomaliRow, LaporanKomparasiRow, LaporanResponse } from "@/lib/types";
import {
  fmtDeltaPct, fmtQty, fmtRp, fmtSignedQty, periodLabel, signedQtyClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/smweb/empty-state";

type Mode = LaporanResponse["mode"];
type KomparasiData = NonNullable<LaporanResponse["komparasi"]>;
type NominalHData = NonNullable<LaporanResponse["nominalH"]>;

const MODES: { value: Mode; label: string }[] = [
  { value: "komparasi", label: "⚖ Komparasi" },
  { value: "anomali_com", label: "🚨 Anomali COM" },
  { value: "nominal_h", label: "💰 Nominal (H)" },
];

/** Badge arah perubahan: NAIK merah (memburuk), TURUN hijau (membaik), TETAP netral. */
function ArahBadge({ arah }: { arah: LaporanKomparasiRow["arah"] }) {
  if (arah === "NAIK") {
    return (
      <Badge className="border-rose-300 bg-rose-100 text-rose-800 dark:border-rose-500/40 dark:bg-rose-500/15 dark:text-rose-300">
        ▲ NAIK
      </Badge>
    );
  }
  if (arah === "TURUN") {
    return (
      <Badge className="border-emerald-300 bg-emerald-100 text-emerald-800 dark:border-emerald-500/40 dark:bg-emerald-500/15 dark:text-emerald-300">
        ▼ TURUN
      </Badge>
    );
  }
  return <Badge variant="secondary">TETAP</Badge>;
}

/** Mode ⚖ Komparasi: banner ringkasan + tabel top perubahan vs periode lalu. */
function KomparasiPanel({ k, prevPeriodKey }: { k: KomparasiData; prevPeriodKey: string | null }) {
  // Warna Δ total: total kini negatif yang makin dalam = memburuk → rose; menyempit = emerald.
  const deltaTone =
    k.deltaPct === null || k.deltaPct === 0 || k.totalKini >= 0
      ? "text-foreground"
      : k.deltaPct > 0
        ? "text-rose-600 dark:text-rose-400"
        : "text-emerald-600 dark:text-emerald-400";

  return (
    <div className="space-y-4">
      {/* Banner ringkasan */}
      <div className="rounded-xl border bg-card p-4 flex flex-wrap items-center gap-x-8 gap-y-3">
        <div className="min-w-32">
          <p className="text-xs text-muted-foreground">Σ Nominal Kini</p>
          <p className={cn("text-lg font-semibold cell-num", signedQtyClass(k.totalKini))}>
            {fmtRp(k.totalKini)}
          </p>
        </div>
        <div className="min-w-32">
          <p className="text-xs text-muted-foreground">Σ Nominal Lalu</p>
          <p className={cn("text-lg font-semibold cell-num", signedQtyClass(k.totalLalu))}>
            {fmtRp(k.totalLalu)}
          </p>
        </div>
        <div className="min-w-32">
          <p className="text-xs text-muted-foreground">Δ total</p>
          <p className={cn("text-2xl font-bold cell-num", deltaTone)}>{fmtDeltaPct(k.deltaPct)}</p>
        </div>
        <Badge variant="outline" className="self-center">
          vs periode lalu: {prevPeriodKey ? periodLabel(prevPeriodKey) : "—"}
        </Badge>
      </div>

      {/* Tabel top perubahan */}
      <div className="rounded-xl border bg-card">
        <div className="p-4 flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm font-medium">Top perubahan nominal (pasangan resto × barang)</p>
          <p className="text-xs text-muted-foreground">{k.rows.length} baris — urut |Δ| menurun</p>
        </div>
        <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
          <table className="w-full caption-bottom text-sm">
            <caption className="sr-only">Komparasi nominal kini vs periode lalu</caption>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                <TableHead>Resto</TableHead>
                <TableHead>Barang</TableHead>
                <TableHead>Kategori</TableHead>
                <TableHead className="text-right">Nominal Kini</TableHead>
                <TableHead className="text-right">Nominal Lalu</TableHead>
                <TableHead className="text-right">Δ</TableHead>
                <TableHead className="text-right">Δ%</TableHead>
                <TableHead className="text-center">Arah</TableHead>
                <TableHead className="text-right">Qty Dev Kini</TableHead>
                <TableHead className="text-right">Qty Dev Lalu</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {k.rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="h-24 text-center text-muted-foreground">
                    Tidak ada pasangan untuk dibandingkan.
                  </TableCell>
                </TableRow>
              ) : (
                k.rows.map((r) => (
                  <TableRow key={`${r.restoCode}|${r.itemName}|${r.satuan}`}>
                    <TableCell className="font-medium">{r.restoCode}</TableCell>
                    <TableCell>
                      {r.itemName}{" "}
                      <span className="text-muted-foreground">({r.satuan})</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{r.kategori}</TableCell>
                    <TableCell className={cn("text-right cell-num", signedQtyClass(r.nominalKini))}>
                      {fmtRp(r.nominalKini)}
                    </TableCell>
                    <TableCell className={cn("text-right cell-num", signedQtyClass(r.nominalLalu))}>
                      {fmtRp(r.nominalLalu)}
                    </TableCell>
                    <TableCell className={cn("text-right cell-num font-medium", signedQtyClass(r.delta))}>
                      {fmtRp(r.delta)}
                    </TableCell>
                    <TableCell className="text-right cell-num">{fmtDeltaPct(r.deltaPct)}</TableCell>
                    <TableCell className="text-center">
                      <ArahBadge arah={r.arah} />
                    </TableCell>
                    <TableCell className={cn("text-right cell-num", signedQtyClass(r.qtyDeviasiKini))}>
                      {fmtSignedQty(r.qtyDeviasiKini)}
                    </TableCell>
                    <TableCell className={cn("text-right cell-num", signedQtyClass(r.qtyDeviasiLalu))}>
                      {fmtSignedQty(r.qtyDeviasiLalu)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </table>
        </div>
      </div>

      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        <Database className="h-3.5 w-3.5 shrink-0" aria-hidden />
        Sumber: snapshot DB (FR-35) — menggantikan file deviasi eksternal manual.
      </p>
    </div>
  );
}

/** Mode 🚨 Anomali COM: pasangan dengan indikasi pemakaian tidak tercatat. */
function AnomaliPanel({ rows }: { rows: LaporanAnomaliRow[] }) {
  return (
    <div className="space-y-3">
      <div className="rounded-xl border bg-card">
        <div className="p-4 flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm font-medium">Indikasi pemakaian tidak tercatat (COM vs BM)</p>
          <p className="text-xs text-muted-foreground">
            {rows.length} anomali — urut pemakaian COM terkecil dulu
          </p>
        </div>
        <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
          <table className="w-full caption-bottom text-sm">
            <caption className="sr-only">Anomali pemakaian COM</caption>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                <TableHead>Resto</TableHead>
                <TableHead>Barang</TableHead>
                <TableHead>Kategori</TableHead>
                <TableHead className="text-right">COM (Pemakaian)</TableHead>
                <TableHead className="text-right">BM (Barang Masuk)</TableHead>
                <TableHead className="text-right">IN</TableHead>
                <TableHead className="text-right">Selisih COM−BM</TableHead>
                <TableHead className="text-right">Nominal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                    Tidak ada anomali COM pada periode ini.
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow key={`${r.restoCode}|${r.itemName}|${r.satuan}`}>
                    <TableCell className="font-medium">{r.restoCode}</TableCell>
                    <TableCell>
                      {r.itemName}{" "}
                      <span className="text-muted-foreground">({r.satuan})</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{r.kategori}</TableCell>
                    <TableCell className="text-right cell-num">{fmtQty(r.comTotal)}</TableCell>
                    <TableCell className="text-right cell-num">{fmtQty(r.bmTotal)}</TableCell>
                    <TableCell className="text-right cell-num">{fmtQty(r.inTotal)}</TableCell>
                    <TableCell className={cn("text-right cell-num font-medium", signedQtyClass(r.selisih))}>
                      {fmtSignedQty(r.selisih)}
                    </TableCell>
                    <TableCell className={cn("text-right cell-num", signedQtyClass(r.nominal))}>
                      {fmtRp(r.nominal)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </table>
        </div>
      </div>
      <p className="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-1.5">
        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
        Aturan demo: pemakaian &lt; 8% dari barang masuk (masuk ≥ 200) → indikasi pemakaian tidak
        tercatat. Produksi akan mengikuti logika macro desktop.
      </p>
    </div>
  );
}

/** Mode 💰 Nominal (H): Σ nominal per resto hingga cut-off H + baris TOTAL. */
function NominalHPanel({ data, h }: { data: NominalHData; h: number }) {
  return (
    <div className="rounded-xl border bg-card">
      <div className="p-4 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium">Nominal per resto hingga hari H</p>
        <p className="text-xs text-muted-foreground">
          cut-off H = {h} · Σ nominal hari 1..{h} vs bulan penuh
        </p>
      </div>
      <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
        <table className="w-full caption-bottom text-sm">
          <caption className="sr-only">Nominal per resto sampai cut-off H</caption>
          <TableHeader className="sticky top-0 bg-background z-10">
            <TableRow>
              <TableHead>Resto</TableHead>
              <TableHead className="text-right">Nominal s.d. H</TableHead>
              <TableHead className="text-right">Nominal Bulan Penuh</TableHead>
              <TableHead className="text-right">Deviasi H</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                  Tidak ada baris hingga hari H.
                </TableCell>
              </TableRow>
            ) : (
              data.rows.map((r) => (
                <TableRow key={r.restoCode}>
                  <TableCell>
                    <span className="font-medium">{r.restoCode}</span>{" "}
                    <span className="text-muted-foreground">{r.restoName}</span>
                  </TableCell>
                  <TableCell className={cn("text-right cell-num font-medium", signedQtyClass(r.nominalH))}>
                    {fmtRp(r.nominalH)}
                  </TableCell>
                  <TableCell className={cn("text-right cell-num", signedQtyClass(r.nominalBulan))}>
                    {fmtRp(r.nominalBulan)}
                  </TableCell>
                  <TableCell className={cn("text-right cell-num", signedQtyClass(r.deviasiH))}>
                    {fmtSignedQty(r.deviasiH)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell className="font-semibold">TOTAL</TableCell>
              <TableCell className={cn("text-right cell-num font-semibold", signedQtyClass(data.total.nominalH))}>
                {fmtRp(data.total.nominalH)}
              </TableCell>
              <TableCell className="text-right text-muted-foreground">—</TableCell>
              <TableCell className="text-right text-muted-foreground">—</TableCell>
            </TableRow>
          </TableFooter>
        </table>
      </div>
    </div>
  );
}

export default function LaporanTab({ snapshotId }: { snapshotId: string | null }) {
  // Mode lokal (default ⚖ Komparasi) + H cut-off lokal (default 25) — dipakai mode komparasi & nominal_h.
  const [mode, setMode] = useState<Mode>("komparasi");
  const [h, setH] = useState(25);
  const { data, isPending, error } = useLaporan(snapshotId, mode, h);

  if (!snapshotId) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot periode"
        description="Pilih periode pada bilah atas, atau jalankan pipeline di tab Proses & Ingest lalu komit snapshot untuk melihat laporan deviasi."
      />
    );
  }

  const onMode = (v: string) => {
    const m = MODES.find((x) => x.value === v);
    if (m) setMode(m.value);
  };

  const loading = (
    <div className="space-y-4">
      <Skeleton className="h-24" />
      <Skeleton className="h-96" />
    </div>
  );

  return (
    <div className="space-y-5">
      {/* Judul + deskripsi 3 mode */}
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ScrollText className="h-5 w-5 text-emerald-600" aria-hidden /> 📋 Laporan Deviasi
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          3 mode (paritas desktop): ⚖ Komparasi — kini vs snapshot periode lalu; 🚨 Anomali COM —
          pemakaian tidak tercatat; 💰 Nominal (H) — per resto hingga cut-off H.
        </p>
      </div>

      <Tabs value={mode} onValueChange={onMode}>
        {/* Toolbar: pilihan mode + H cut-off (sembunyi untuk mode anomali) */}
        <div className="flex flex-wrap items-end gap-3">
          <TabsList aria-label="Mode laporan deviasi">
            {MODES.map((m) => (
              <TabsTrigger key={m.value} value={m.value}>
                {m.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {mode !== "anomali_com" ? (
            <div className="w-44 space-y-1.5">
              <Label htmlFor="lap-h">TANGGAL H (cut-off)</Label>
              <Input
                id="lap-h"
                type="number"
                min={1}
                max={31}
                step={1}
                value={h}
                aria-describedby="lap-h-hint"
                onChange={(e) => {
                  if (e.target.value === "") return; // input kosong: pertahankan nilai lama
                  const v = Number(e.target.value);
                  if (Number.isFinite(v)) setH(Math.min(31, Math.max(1, Math.round(v))));
                }}
              />
              <p id="lap-h-hint" className="text-[11px] text-muted-foreground">
                dipakai mode ⚖ Komparasi &amp; 💰 Nominal (H)
              </p>
            </div>
          ) : null}
        </div>

        {/* ⚖ Komparasi */}
        <TabsContent value="komparasi" className="mt-4">
          {isPending ? (
            loading
          ) : error ? (
            <EmptyState
              icon={FileWarning}
              title="Gagal memuat laporan komparasi"
              description={(error as Error).message}
            />
          ) : !data || !data.komparasi ? null : !data.hasPrev ? (
            <EmptyState
              icon={GitCompare}
              title="Belum ada snapshot periode sebelumnya"
              description="komit ≥ 2 periode untuk membandingkan (sumber utama = snapshot DB, file eksternal hanya untuk histori pra-web)."
            />
          ) : (
            <KomparasiPanel k={data.komparasi} prevPeriodKey={data.prevPeriodKey} />
          )}
        </TabsContent>

        {/* 🚨 Anomali COM */}
        <TabsContent value="anomali_com" className="mt-4">
          {isPending ? (
            loading
          ) : error ? (
            <EmptyState
              icon={FileWarning}
              title="Gagal memuat anomali COM"
              description={(error as Error).message}
            />
          ) : !data || !data.anomali ? null : (
            <AnomaliPanel rows={data.anomali.rows} />
          )}
        </TabsContent>

        {/* 💰 Nominal (H) */}
        <TabsContent value="nominal_h" className="mt-4">
          {isPending ? (
            loading
          ) : error ? (
            <EmptyState
              icon={FileWarning}
              title="Gagal memuat nominal (H)"
              description={(error as Error).message}
            />
          ) : !data || !data.nominalH ? null : (
            <NominalHPanel data={data.nominalH} h={data.h} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
