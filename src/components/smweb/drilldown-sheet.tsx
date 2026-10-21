// Panel drill-down universal (INV-7) — dipakai tab Pivot, Deviasi, Selisih IN, Nominal.
// Klik sel/baris → panel samping menampilkan seri harian 10 metrik + ringkasan bulanan.
"use client";

import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useDrilldown } from "@/hooks/use-sm-api";
import { fmtQty, fmtRp, fmtSignedQty, signedQtyClass } from "@/lib/format";
import { METRICS } from "@/lib/types";
import { CekBadgeList } from "./badges";

export interface DrilldownTarget {
  resto: string;
  item: string;
}

export function DrilldownSheet({
  snapshotId,
  target,
  onClose,
}: {
  snapshotId: string | null;
  target: DrilldownTarget | null;
  onClose: () => void;
}) {
  const { data, isPending, error } = useDrilldown(
    snapshotId,
    target?.resto ?? null,
    target?.item ?? null,
  );

  return (
    <Sheet open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl p-0 flex flex-col">
        <SheetHeader className="p-4 pb-3 border-b">
          <SheetTitle className="text-base leading-snug">
            {target ? `${target.item}` : "Rincian"}
          </SheetTitle>
          <SheetDescription className="text-xs">
            {data
              ? `${data.resto.restoName} (${data.resto.restoCode}) · ${data.item.satuan} · ${data.item.kategori} · ${data.item.isGR ? "GR" : "PCS"}`
              : "Memuat rincian…"}
          </SheetDescription>
          {data && !data.item.konversiOk ? (
            <Badge variant="outline" className="w-fit border-amber-400 text-amber-700 dark:text-amber-300">
              * konversi satuan gagal — nominal null (INV-3)
            </Badge>
          ) : null}
          {data ? (
            <div className="flex flex-wrap gap-1.5 pt-1 text-xs">
              <Badge variant="secondary">Harga efektif: {data.item.harga !== null ? fmtRp(data.item.harga) : "—"}</Badge>
              <Badge variant="secondary">Deviasi bulan: {fmtSignedQty(data.monthly.deviasiBulan)}</Badge>
              <Badge variant="secondary">Nominal bulan: {data.item.konversiOk ? fmtRp(data.monthly.nominalBulan) : "—"}</Badge>
            </div>
          ) : null}
        </SheetHeader>

        <div className="flex-1 min-h-0 p-4">
          {isPending ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : error ? (
            <p className="text-sm text-destructive">
              {(error as Error).message}
            </p>
          ) : data ? (
            <ScrollArea className="h-full nice-scroll">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-1.5 pr-2 font-medium sticky left-0 bg-background">Hari</th>
                    {METRICS.map((m) => (
                      <th key={m.key} className="py-1.5 px-1.5 font-medium whitespace-nowrap text-right">
                        {m.short}
                      </th>
                    ))}
                    <th className="py-1.5 px-1.5 font-medium text-right">NOM</th>
                    <th className="py-1.5 px-1.5 font-medium">CEK</th>
                  </tr>
                </thead>
                <tbody>
                  {data.days.map((d) => (
                    <tr key={d.day} className="border-b border-border/50 hover:bg-muted/40">
                      <td className="py-1.5 pr-2 sticky left-0 bg-background font-medium">{d.day}</td>
                      {METRICS.map((m) => {
                        const v = d[m.key];
                        return (
                          <td
                            key={m.key}
                            className={`px-1.5 text-right cell-num ${m.key === "qtyDeviasi" ? signedQtyClass(v) : ""}`}
                          >
                            {v === null ? <span className="text-muted-foreground/50">—</span> : fmtQty(v)}
                          </td>
                        );
                      })}
                      <td className={`px-1.5 text-right cell-num ${signedQtyClass(d.nominal)}`}>
                        {data.item.konversiOk ? (d.nominal === null ? "—" : fmtRp(d.nominal)) : "—"}
                      </td>
                      <td className="px-1.5">
                        <CekBadgeList cek={d.cek} auditNotes={d.auditNote ? [d.auditNote] : []} compact />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[11px] text-muted-foreground">
                Kolom: SA = Saldo Awal · SO = Stock Opname · SKA = Saldo Akhir · DEV = Deviasi (SO−SKA, bertanda) ·
                IN = masuk Accurate · BM = Barang Masuk rekap · COM = Pemakaian · SIN = Selisih IN · BK = Barang Keluar ·
                ACR = penyesuaian · NOM = Nominal. Sel "—" = tidak ada data (missing ≠ 0 — INV-1).
              </p>
            </ScrollArea>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
