// Tab 🏠 Ikhtisar — ringkasan KPI periode aktif + tren + status engine + aktivitas.
"use client";

import { useMemo } from "react";
import {
  AlertTriangle, Boxes, CheckCircle2, Database, FileWarning, FlaskConical,
  ListChecks, PackageSearch, TrendingDown, TrendingUp, Wallet,
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, Legend,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useOverview, useSeedDemo } from "@/hooks/use-sm-api";
import { useSmStore } from "@/store/use-sm-store";
import { StatCard } from "@/components/smweb/stat-card";
import { EmptyState } from "@/components/smweb/empty-state";
import { RunStatusBadge } from "@/components/smweb/badges";
import {
  fmtDeltaPct, fmtDateTime, fmtInt, fmtPct, fmtQty, fmtRp, periodLabel, signedQtyClass,
} from "@/lib/format";

export function OverviewTab() {
  const { data, isPending, error } = useOverview();
  const seedDemo = useSeedDemo();
  const setActiveTab = useSmStore((s) => s.setActiveTab);

  const nominalChart = useMemo(
    () =>
      (data?.nominalPerResto ?? []).map((r) => ({
        name: r.restoCode,
        nominal: Math.round(r.nominal),
        deviasi: Math.round(r.deviasiQty),
      })),
    [data],
  );

  const trendChart = useMemo(
    () =>
      (data?.trend ?? []).map((t) => ({
        periode: t.periodKey,
        nominal: Math.round(t.nominalTotal),
        deviasiQty: Math.round(t.deviasiQtyTotal),
      })),
    [data],
  );

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={FileWarning}
        title="Gagal memuat ikhtisar"
        description={(error as Error).message}
      />
    );
  }

  if (!data?.active) {
    return (
      <EmptyState
        icon={Database}
        title="Belum ada snapshot periode"
        description="Jalankan pipeline di tab Proses & Ingest, atau isi data demo (2 periode sintetis dari engine demo) untuk mencoba seluruh halaman analisis."
        action={
          <div className="flex flex-wrap gap-2 justify-center">
            <Button onClick={() => setActiveTab("ingest")}>🚀 Buka Proses &amp; Ingest</Button>
            <Button variant="outline" disabled={seedDemo.isPending} onClick={() => seedDemo.mutate()}>
              {seedDemo.isPending ? "Menyiapkan demo…" : "🧪 Isi data demo (2 periode)"}
            </Button>
          </div>
        }
      />
    );
  }

  const a = data.active;
  const openCases = data.cases.pending + data.cases.diproses;

  return (
    <div className="space-y-6">
      {/* Status periode */}
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="secondary">Periode aktif: {periodLabel(a.periodKey)}</Badge>
        <Badge variant="outline">definisi: {a.definitionVersion}</Badge>
        <Badge variant="outline">H cut-off: {a.params.tanggalH}</Badge>
        <Badge variant="outline">ambang ACR: {a.params.ambangAcrPct}%</Badge>
        {data.previous ? (
          <Badge variant="outline">vs {periodLabel(data.previous.periodKey)}</Badge>
        ) : null}
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Σ Nominal Deviasi (bulan)"
          value={fmtRp(a.nominalTotal)}
          sub={data.nominalDeltaPct !== null ? `${fmtDeltaPct(data.nominalDeltaPct)} vs bulan lalu` : "belum ada pembanding"}
          icon={Wallet}
          tone={a.nominalTotal < 0 ? "rose" : "emerald"}
        />
        <StatCard
          title="Σ Deviasi (qty bertanda)"
          value={fmtQty(a.deviasiQtyTotal)}
          sub={`${a.restoCount} resto × ${a.itemCount} barang · ${fmtInt(a.rowCount)} baris`}
          icon={Boxes}
          tone={a.deviasiQtyTotal < 0 ? "rose" : "teal"}
        />
        <StatCard
          title="Kasus Follow-Up terbuka"
          value={fmtInt(openCases)}
          sub={`${data.cases.selesai} selesai · ${data.cases.dibatalkan} batal`}
          icon={ListChecks}
          tone={openCases > 0 ? "amber" : "emerald"}
        />
        <StatCard
          title="Isu kualitas data"
          value={fmtInt(data.dq.warning + data.dq.error + data.dq.info)}
          sub={`${data.dq.warning} warning · ${data.dq.error} error · ${data.dq.info} info`}
          icon={AlertTriangle}
          tone={data.dq.error > 0 ? "rose" : data.dq.warning > 0 ? "amber" : "emerald"}
        />
      </div>

      {/* Chart */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm font-medium mb-3">Nominal deviasi per resto — {periodLabel(a.periodKey)}</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nominalChart} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}rb`} />
                <Tooltip
                  formatter={(v: number | string) => fmtRp(Number(v))}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Bar dataKey="nominal" name="Nominal" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm font-medium mb-3">Tren nominal antar periode (dari snapshot — bukan file eksternal)</p>
          <div className="h-72">
            {trendChart.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChart} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="periode" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}rb`} />
                  <Tooltip
                    formatter={(v: number | string) => fmtRp(Number(v))}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="nominal" name="Nominal deviasi" stroke="var(--chart-1)" strokeWidth={2} dot />
                  <Line type="monotone" dataKey="deviasiQty" name="Qty deviasi" stroke="var(--chart-3)" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-center text-sm text-muted-foreground px-8">
                <p>
                  Menunggu ≥ 2 periode terkomit untuk menampilkan tren.
                  <br />
                  Komit periode berikutnya (atau seed demo) untuk melihat grafik ini.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Top deviasi */}
        <div className="rounded-xl border bg-card p-4">
          <p className="text-sm font-medium mb-3 flex items-center gap-2">
            <PackageSearch className="h-4 w-4" aria-hidden /> Top nominal deviasi (resto × barang)
          </p>
          <div className="max-h-72 overflow-y-auto nice-scroll">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Resto</TableHead>
                  <TableHead>Barang</TableHead>
                  <TableHead className="text-right">Deviasi</TableHead>
                  <TableHead className="text-right">Nominal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.topDeviations.map((t) => (
                  <TableRow key={`${t.restoCode}-${t.itemName}`}>
                    <TableCell className="font-medium whitespace-nowrap">{t.restoCode}</TableCell>
                    <TableCell className="whitespace-nowrap">{t.itemName} <span className="text-muted-foreground">({t.satuan})</span></TableCell>
                    <TableCell className={`text-right cell-num ${signedQtyClass(t.qtyDeviasi)}`}>{fmtQty(t.qtyDeviasi)}</TableCell>
                    <TableCell className={`text-right cell-num ${signedQtyClass(t.nominal)}`}>{fmtRp(t.nominal)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Run terakhir + engine */}
        <div className="space-y-4">
          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm font-medium mb-3">Run terakhir</p>
            <div className="max-h-48 overflow-y-auto nice-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Periode</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Waktu</TableHead>
                    <TableHead className="text-right">Durasi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.runs.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="whitespace-nowrap">{r.periodKey}{r.bundleName ? ` · ${r.bundleName}` : ""}</TableCell>
                      <TableCell><RunStatusBadge status={r.status} /></TableCell>
                      <TableCell className="whitespace-nowrap text-xs">{fmtDateTime(r.startedAt)}</TableCell>
                      <TableCell className="text-right cell-num text-xs">{r.durationMs !== null ? `${(r.durationMs / 1000).toFixed(2)}s` : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-4">
            <p className="text-sm font-medium mb-2 flex items-center gap-2">
              <FlaskConical className="h-4 w-4" aria-hidden /> Engine service
            </p>
            {data.engineReachable && data.engine ? (
              <div className="space-y-1.5 text-sm">
                <p className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden />
                  {data.engine.engineName} v{data.engine.engineVersion} — sehat
                </p>
                <p className="text-muted-foreground">{data.engine.parityNote}</p>
                <p className="text-muted-foreground text-xs">
                  Kontrak v{data.engine.contractVersion} · definisi {data.engine.definitionVersion} · uptime {Math.round(data.engine.uptimeSec)}s
                </p>
              </div>
            ) : data.engineEmbedAvailable ? (
              <p className="text-sm text-amber-700 dark:text-amber-400 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden />
                <span>
                  Engine service tidak terjangkau — run demo otomatis memakai fallback{" "}
                  <strong>EMBEDDED</strong> (generator identik, deterministik FR-12). Pipeline asli:
                  jalankan <code className="text-xs bg-muted px-1.5 py-0.5 rounded">mini-services/engine-fastapi</code>.
                </span>
              </p>
            ) : (
              <p className="text-sm text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" aria-hidden /> Engine tidak terjangkau — jalankan
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">cd mini-services/engine &amp;&amp; bun run dev</code>
              </p>
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        {data.nominalDeltaPct !== null && data.nominalDeltaPct > 0 ? (
          <TrendingUp className="h-3.5 w-3.5 text-rose-500" aria-hidden />
        ) : (
          <TrendingDown className="h-3.5 w-3.5 text-emerald-500" aria-hidden />
        )}
        Perbandingan antar-periode dihitung dari snapshot database ({fmtPct(data.nominalDeltaPct)} untuk nominal) —
        menutup alur lama yang membandingkan file deviasi eksternal manual.
      </p>
    </div>
  );
}
