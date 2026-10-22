// Tab 🛒 Rincian PO — paritas tab 10 desktop: daftar PO + item + status pesanan (32.43)
// + anotasi "↳ Status" per PO, filter cabang/status persist (FR-36).
"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Database, FileWarning, ShoppingCart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { usePo } from "@/hooks/use-sm-api";
import { useDebounced } from "@/hooks/use-debounced";
import { EmptyState } from "@/components/smweb/empty-state";
import { ExportButton } from "@/components/smweb/export-button";
import { fmtInt, fmtQty } from "@/lib/format";
import type { PoHeaderDto } from "@/lib/types";

/** "2026-10-05" → "5 Okt 2026" — tanpa timezone, tampil apa adanya. */
function fmtPoDate(tanggal: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(tanggal);
  if (!m) return tanggal || "—";
  const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  const idx = Number(m[2]) - 1;
  return `${Number(m[3])} ${bulan[idx] ?? m[2]} ${m[1]}`;
}

/** Badge status ringkasan PO: menunggu (amber outline), selesai (emerald), diproses/lainnya (secondary). */
function PoStatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  if (s === "menunggu diproses" || s === "menunggu") {
    return (
      <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
        {status}
      </Badge>
    );
  }
  if (s === "selesai") {
    return (
      <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40">
        {status}
      </Badge>
    );
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export default function PoTab({ snapshotId }: { snapshotId: string | null }) {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [cabangFilter, setCabangFilter] = useState("ALL");
  const [expandedPoId, setExpandedPoId] = useState<string | null>(null);
  const qDebounced = useDebounced(q, 300);

  const qs = useMemo(() => {
    const params = new URLSearchParams();
    params.set("q", qDebounced.trim());
    params.set("status", statusFilter === "ALL" ? "" : statusFilter);
    params.set("cabang", cabangFilter === "ALL" ? "" : cabangFilter);
    return params.toString();
  }, [qDebounced, statusFilter, cabangFilter]);

  const { data, isPending, error } = usePo(snapshotId, qs);
  const rows = data?.rows ?? [];
  const restos = data?.restos ?? [];
  const statusOptions = data?.statusOptions ?? [];

  if (!snapshotId) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-emerald-600" aria-hidden /> 🛒 Rincian PO
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Daftar purchase order per periode: nomor, tanggal, cabang, supplier, item, dan status
            pesanan (32.42/32.43) + anotasi ↳ Status.
          </p>
        </div>
        <EmptyState
          icon={Database}
          title="Belum ada snapshot periode aktif"
          description="Tab ini membutuhkan snapshot periode terkomit. Pilih periode di header, atau jalankan pipeline di tab Proses & Ingest."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-emerald-600" aria-hidden /> 🛒 Rincian PO
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Daftar purchase order per periode: nomor, tanggal, cabang, supplier, item, dan status
            pesanan (32.42/32.43) + anotasi ↳ Status per PO.
          </p>
        </div>
        {snapshotId ? (
          <ExportButton snapshotId={snapshotId} sheet="po" size="sm" label="Export PO" />
        ) : null}
      </div>

      {/* Filter bar (state lokal → qs) */}
      <div className="rounded-xl border bg-card p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="po-q">Pencarian</Label>
          <Input
            id="po-q"
            placeholder="Nomor PO / supplier / nama item…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="po-status">Status pesanan</Label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger id="po-status" className="w-full" aria-label="Filter status pesanan">
              <SelectValue placeholder="Semua status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Semua status</SelectItem>
              {statusOptions.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="po-cabang">Cabang</Label>
          <Select value={cabangFilter} onValueChange={setCabangFilter}>
            <SelectTrigger id="po-cabang" className="w-full" aria-label="Filter cabang">
              <SelectValue placeholder="Semua cabang" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Semua cabang</SelectItem>
              {restos.map((r) => (
                <SelectItem key={r.restoCode} value={r.restoCode}>
                  {r.restoCode} — {r.restoName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabel PO */}
      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon={FileWarning}
          title="Gagal memuat rincian PO"
          description={error instanceof Error ? error.message : "Permintaan gagal."}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={ShoppingCart}
          title="Tidak ada PO yang cocok"
          description="Tidak ada PO untuk filter ini pada periode terpilih. Kosongkan pencarian/status/cabang untuk melihat semua."
        />
      ) : (
        <>
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto nice-scroll">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <TableHead className="w-8" aria-label="Buka rincian item"><span className="sr-only">Perluas</span></TableHead>
                    <TableHead>Nomor PO</TableHead>
                    <TableHead>Tanggal</TableHead>
                    <TableHead>Cabang</TableHead>
                    <TableHead>Supplier</TableHead>
                    <TableHead className="text-right">Jumlah item</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Status pesanan</TableHead>
                    <TableHead>Anotasi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((po) => {
                    const expanded = expandedPoId === po.id;
                    return (
                      <PoRow key={po.id} po={po} expanded={expanded} onToggle={() => {
                        setExpandedPoId((cur) => (cur === po.id ? null : po.id));
                      }} />
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Footer: jumlah PO tampil */}
          <p className="text-xs text-muted-foreground">
            Klik baris untuk membuka/menutup rincian item · <strong className="font-medium text-foreground">{fmtInt(rows.length)}</strong> PO tampil
          </p>
        </>
      )}
    </div>
  );
}

function PoRow({
  po,
  expanded,
  onToggle,
}: {
  po: PoHeaderDto;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <TableRow
        tabIndex={0}
        aria-expanded={expanded}
        aria-label={`Rincian item PO ${po.poNumber} — ${po.cabang}`}
        className="cursor-pointer hover:bg-muted/50 focus-visible:bg-muted/50 outline-none"
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
      >
        <TableCell className="w-8">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
          )}
        </TableCell>
        <TableCell className="font-mono text-xs">{po.poNumber}</TableCell>
        <TableCell className="text-xs">{fmtPoDate(po.tanggal)}</TableCell>
        <TableCell>
          <span className="font-medium">{po.cabang}</span>{" "}
          <span className="text-xs text-muted-foreground">{po.restoName}</span>
        </TableCell>
        <TableCell>{po.supplier ?? "—"}</TableCell>
        <TableCell className="text-right cell-num">{fmtInt(po.itemCount)}</TableCell>
        <TableCell><PoStatusBadge status={po.status} /></TableCell>
        <TableCell className="text-xs">{po.statusPesanan}</TableCell>
        <TableCell className="italic text-xs text-muted-foreground">{po.annotasi ?? "—"}</TableCell>
      </TableRow>

      {/* Baris ekspansi: tabel item PO */}
      {expanded ? (
        <TableRow className="bg-muted/30 hover:bg-muted/30">
          <TableCell colSpan={9} className="p-0">
            <div className="px-4 sm:px-8 py-3">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Item PO {po.poNumber} ({fmtInt(po.items.length)})
              </p>
              <div className="overflow-x-auto rounded-lg border bg-background">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama barang</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead>Satuan</TableHead>
                      <TableHead>Status item</TableHead>
                      <TableHead>Penerimaan</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {po.items.map((it) => (
                      <TableRow key={it.id}>
                        <TableCell>{it.itemName}</TableCell>
                        <TableCell className="text-right cell-num">{fmtQty(it.qty)}</TableCell>
                        <TableCell className="text-xs">{it.satuan}</TableCell>
                        <TableCell className="text-xs">{it.status}</TableCell>
                        <TableCell>
                          {it.diterimaSebagian ? (
                            <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">
                              diterima sebagian
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </TableCell>
        </TableRow>
      ) : null}
    </>
  );
}
