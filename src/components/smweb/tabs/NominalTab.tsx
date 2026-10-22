// Tab 🧮 Nominal Deviasi (FR-34) — paritas tab 8 desktop.
// Σ nominal per resto + TOTAL + Biaya Packaging + Δ% vs bulan lalu DARI SNAPSHOT DB
// (menutup alur file deviasi eksternal manual) + anak-daftar Tanpa Harga (INV-3).
"use client";

import {
  Boxes, Database, FileWarning, Info, Package, TrendingUp, Wallet,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { useNominal } from "@/hooks/use-sm-api";
import {
  fmtDeltaPct, fmtRp, fmtSignedQty, periodLabel, signedQtyClass,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/smweb/empty-state";
import { StatCard } from "@/components/smweb/stat-card";
import { ExportButton } from "@/components/smweb/export-button";

const DRILLDOWN_HINT = "Drill-down per barang tersedia di tab Deviasi";

/**
 * Warna Δ% per resto: nominal negatif yang makin dalam (Δ% > 0) = memburuk → rose;
 * nominal negatif yang menyempit (Δ% < 0) = membaik → emerald; selainnya netral.
 */
function deltaPctClass(deltaPct: number | null, nominal: number): string {
  if (deltaPct === null || deltaPct === 0 || nominal >= 0) return "text-foreground";
  return deltaPct > 0
    ? "text-rose-600 dark:text-rose-400 font-medium"
    : "text-emerald-600 dark:text-emerald-400";
}

export default function NominalTab({ snapshotId }: { snapshotId: string | null }) {
  const { data, isPending, error } = useNominal(snapshotId);

  if (!snapshotId) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot periode"
        description="Pilih periode pada bilah atas, atau jalankan pipeline di tab Proses & Ingest lalu komit snapshot untuk melihat nominal deviasi."
      />
    );
  }

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={FileWarning}
        title="Gagal memuat nominal deviasi"
        description={(error as Error).message}
      />
    );
  }

  if (!data) return null;

  const t = data.total;
  let deltaTone: "neutral" | "rose" | "emerald" = "neutral";
  if (t.deltaPct !== null && t.deltaPct !== 0 && t.nominal < 0) {
    deltaTone = t.deltaPct > 0 ? "rose" : "emerald";
  }

  // Baris resto = data agregat → TIDAK drilldown; beri petunjuk arah tab Deviasi.
  const onRestoRow = () => {
    toast.info(DRILLDOWN_HINT);
  };

  return (
    <div className="space-y-5">
      {/* Judul + deskripsi */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">🧮 Nominal Deviasi</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Σ nominal deviasi per resto + TOTAL, biaya packaging, dan Δ% naik/turun vs bulan lalu —
            dari snapshot database, bukan file eksternal (FR-34).
          </p>
        </div>
        <div className="flex items-center gap-2">
          {snapshotId ? (
            <ExportButton snapshotId={snapshotId} sheet="nominal" size="sm" label="Export Nominal" />
          ) : null}
          <Badge variant="secondary">Periode: {periodLabel(data.periodKey)}</Badge>
        </div>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="TOTAL Nominal Deviasi"
          value={fmtRp(t.nominal)}
          sub={`${data.rows.length} resto`}
          icon={Wallet}
          tone={t.nominal < 0 ? "rose" : "emerald"}
        />
        <StatCard
          title="Δ vs Bulan Lalu"
          value={fmtDeltaPct(t.deltaPct)}
          sub="dari snapshot DB, bukan file eksternal"
          icon={TrendingUp}
          tone={deltaTone}
        />
        <StatCard
          title="Biaya Packaging"
          value={fmtRp(data.com.packagingNominal)}
          sub={`qty deviasi packaging ${fmtSignedQty(data.com.packagingDeviasiQty)}`}
          icon={Package}
          tone={data.com.packagingNominal < 0 ? "rose" : "emerald"}
        />
        <StatCard
          title="Deviasi Qty Total"
          value={fmtSignedQty(t.deviasiQty)}
          sub="satuan terkecil, bertanda (INV-2)"
          icon={Boxes}
          tone={t.deviasiQty < 0 ? "rose" : "teal"}
        />
      </div>

      {/* Tabel per resto + anak-tab Tanpa Harga */}
      <Tabs defaultValue="resto">
        <div className="rounded-xl border bg-card">
          <div className="p-4">
            <TabsList aria-label="Sub-tampilan nominal deviasi">
              <TabsTrigger value="resto">Per Resto</TabsTrigger>
              <TabsTrigger value="tanpa">Tanpa Harga ({data.tanpaHarga.length})</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="resto" className="mt-0">
            <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
              <table className="w-full caption-bottom text-sm">
                <caption className="sr-only">Nominal deviasi per resto</caption>
                <TableHeader className="sticky top-0 bg-background z-10">
                  <TableRow>
                    <TableHead>Resto</TableHead>
                    <TableHead className="text-right">Nominal</TableHead>
                    <TableHead className="text-right">Deviasi Qty</TableHead>
                    <TableHead className="text-right">Δ% vs Bulan Lalu</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                        Tidak ada data resto pada periode ini.
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.rows.map((r) => (
                      <TableRow
                        key={r.restoCode}
                        className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60"
                        tabIndex={0}
                        title={DRILLDOWN_HINT}
                        onClick={onRestoRow}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onRestoRow();
                          }
                        }}
                      >
                        <TableCell>
                          <span className="font-medium">{r.restoCode}</span>{" "}
                          <span className="text-muted-foreground">{r.restoName}</span>
                        </TableCell>
                        <TableCell className={cn("text-right cell-num", signedQtyClass(r.nominal))}>
                          {fmtRp(r.nominal)}
                        </TableCell>
                        <TableCell className={cn("text-right cell-num", signedQtyClass(r.deviasiQty))}>
                          {fmtSignedQty(r.deviasiQty)}
                        </TableCell>
                        <TableCell className={cn("text-right cell-num", deltaPctClass(r.deltaPct, r.nominal))}>
                          {fmtDeltaPct(r.deltaPct)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </table>
            </div>
            <p className="border-t p-3 text-xs text-muted-foreground">
              Urut nominal menurun (bawaan server) · data agregat — klik baris (atau Enter) untuk
              petunjuk drill-down.
            </p>
          </TabsContent>

          <TabsContent value="tanpa" className="mt-0">
            {data.tanpaHarga.length === 0 ? (
              <div className="border-t p-4">
                <EmptyState
                  icon={Info}
                  title="Tidak ada pasangan tanpa harga"
                  description="Semua pasangan dengan qty deviasi ≠ 0 memiliki harga 41.09 yang valid pada periode ini."
                />
              </div>
            ) : (
              <>
                <div className="border-t max-h-[70vh] overflow-auto nice-scroll">
                  <table className="w-full caption-bottom text-sm">
                    <caption className="sr-only">Daftar pasangan tanpa harga (nominal null)</caption>
                    <TableHeader className="sticky top-0 bg-background z-10">
                      <TableRow>
                        <TableHead>Barang</TableHead>
                        <TableHead>Satuan</TableHead>
                        <TableHead>Kategori</TableHead>
                        <TableHead>Alasan</TableHead>
                        <TableHead className="text-right">Qty Deviasi</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.tanpaHarga.map((r) => (
                        <TableRow key={`${r.itemName}|${r.satuan}`}>
                          <TableCell>
                            <span className="font-medium">{r.itemName}</span>
                            {r.alasan.startsWith("Konversi") ? (
                              <Badge
                                variant="outline"
                                className="ml-2 border-amber-300 text-amber-700 dark:border-amber-500/50 dark:text-amber-300"
                              >
                                ＊ konversi gagal
                              </Badge>
                            ) : null}
                          </TableCell>
                          <TableCell className="text-muted-foreground">{r.satuan}</TableCell>
                          <TableCell className="text-muted-foreground">{r.kategori}</TableCell>
                          <TableCell className="text-xs text-muted-foreground max-w-72 whitespace-normal">
                            {r.alasan}
                          </TableCell>
                          <TableCell className={cn("text-right cell-num", signedQtyClass(r.qtyDeviasi))}>
                            {fmtSignedQty(r.qtyDeviasi)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </table>
                </div>
                <p className="border-t p-3 text-xs text-muted-foreground flex items-start gap-1.5">
                  <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" aria-hidden />
                  Pasangan qty ≠ 0 tanpa harga → nominal null, bukan angka salah (INV-3: harga 41.09
                  global dinormalkan satuan; konversi gagal diberi penanda ＊).
                </p>
              </>
            )}
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
