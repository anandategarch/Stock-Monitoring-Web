// SM-WEB — shell utama (satu-satunya rute "/" — navigasi antar-tab internal).
// Sticky footer: mt-auto dalam flex-col min-h-screen (aturan platform).
"use client";

import { useEffect, useMemo } from "react";
import { useTheme } from "next-themes";
import {
  Activity, BadgeCheck, Boxes, ClipboardList, FlaskConical, LayoutDashboard,
  Moon, PackageSearch, PieChart, Play, Rows3, ScrollText, Settings, ShoppingCart, Sun, Table2,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useEngineHealth, useSnapshots } from "@/hooks/use-sm-api";
import { useSmStore, type TabKey } from "@/store/use-sm-store";
import { periodLabel } from "@/lib/format";
import { OverviewTab } from "@/components/smweb/tabs/OverviewTab";
import { IngestTab } from "@/components/smweb/tabs/IngestTab";
import PivotTab from "@/components/smweb/tabs/PivotTab";
import DeviasiTab from "@/components/smweb/tabs/DeviasiTab";
import SelisihInTab from "@/components/smweb/tabs/SelisihInTab";
import NominalTab from "@/components/smweb/tabs/NominalTab";
import LaporanTab from "@/components/smweb/tabs/LaporanTab";
import FollowUpTab from "@/components/smweb/tabs/FollowUpTab";
import PoTab from "@/components/smweb/tabs/PoTab";
import DqTab from "@/components/smweb/tabs/DqTab";
import ConfigTab from "@/components/smweb/tabs/ConfigTab";

const TABS: { key: TabKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "overview", label: "Ikhtisar", icon: LayoutDashboard },
  { key: "ingest", label: "Proses & Ingest", icon: Play },
  { key: "pivot", label: "Pivot Table", icon: Table2 },
  { key: "deviasi", label: "Deviasi GR/PCS", icon: Boxes },
  { key: "selisihin", label: "Selisih IN", icon: Activity },
  { key: "nominal", label: "Nominal Deviasi", icon: PieChart },
  { key: "laporan", label: "Laporan Deviasi", icon: ScrollText },
  { key: "followup", label: "Follow Up", icon: BadgeCheck },
  { key: "po", label: "Rincian PO", icon: ShoppingCart },
  { key: "dq", label: "Kualitas Data", icon: FlaskConical },
  { key: "config", label: "Config", icon: Settings },
];

function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const dark = (theme === "dark") || (theme === "system" && resolvedTheme === "dark");
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={dark ? "Ganti ke mode terang" : "Ganti ke mode gelap"}
      onClick={() => setTheme(dark ? "light" : "dark")}
    >
      {dark ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
    </Button>
  );
}

/** Toggle Tampilan Rapat (Task 33 fitur #1) — densitas tabel ala Treeview
 *  desktop zoom 80% (font 8pt / baris ±24px). Global: html[data-density]. */
function DensityToggle({ compact, onToggle }: { compact: boolean; onToggle: () => void }) {
  return (
    <Button
      variant={compact ? "secondary" : "ghost"}
      size="icon"
      aria-pressed={compact}
      aria-label={compact ? "Tampilan rapat AKTIF — klik untuk tampilan normal" : "Tampilan rapat (densitas tabel ala desktop)"}
      title={compact ? "Tampilan rapat AKTIF — klik untuk tampilan normal" : "Tampilan rapat (densitas tabel ala desktop)"}
      onClick={onToggle}
      className="relative"
    >
      <Rows3 className="h-4 w-4" aria-hidden />
      {compact ? (
        <span aria-hidden className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-500" />
      ) : null}
    </Button>
  );
}

export default function Page() {
  const { activeTab, setActiveTab, periodKey, setPeriodKey, uiCompact, setUiCompact } = useSmStore();
  const { data: snapshotsData, isPending: snapsPending } = useSnapshots();
  const { data: engineHealth } = useEngineHealth();

  // Mode Tampilan Rapat: diterapkan global lewat atribut <html data-density>
  // (CSS di globals.css menangkap SEMUA tabel tanpa per-sel — lihat Task 33 #1).
  useEffect(() => {
    document.documentElement.dataset.density = uiCompact ? "compact" : "default";
  }, [uiCompact]);

  const activeSnapshots = useMemo(
    () => (snapshotsData?.snapshots ?? []).filter((s) => s.state === "ACTIVE"),
    [snapshotsData],
  );

  const periodOptions = useMemo(
    () => activeSnapshots.map((s) => ({ value: s.periodKey, label: periodLabel(s.periodKey) })),
    [activeSnapshots],
  );

  // periodKey tersimpan (sessionStorage) bisa basi — snapshot-nya sudah
  // dihapus/SUPERSEDED. Validasi terhadap opsi yang ADA; jatuh ke yang
  // pertama agar tab tidak menampilkan "belum ada snapshot" palsu (audit 48-g-ui).
  const effectivePeriodKey = useMemo(
    () =>
      periodOptions.some((p) => p.value === periodKey)
        ? periodKey
        : (periodOptions[0]?.value ?? null),
    [periodKey, periodOptions],
  );

  const activeSnapshot = useMemo(
    () => activeSnapshots.find((s) => s.periodKey === effectivePeriodKey) ?? null,
    [activeSnapshots, effectivePeriodKey],
  );

  const engineOk = engineHealth?.reachable === true;
  const embedAvail = engineHealth?.embedded?.available === true;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto w-full max-w-7xl px-3 sm:px-6">
          <div className="flex h-14 items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-sm shrink-0">
                SM
              </div>
              <div className="min-w-0">
                <p className="font-semibold leading-tight truncate">Stock Monitoring Web</p>
                <p className="text-[11px] text-muted-foreground leading-tight truncate hidden sm:block">
                  SM-WEB · PRD v1.1 · definisi 3.9.71-noSI
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "hidden sm:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px]",
                  engineOk
                    ? "border-emerald-300 text-emerald-700 dark:text-emerald-300"
                    : embedAvail
                      ? "border-amber-300 text-amber-700 dark:text-amber-300"
                      : "border-rose-300 text-rose-700 dark:text-rose-300",
                )}
                title={
                  engineOk
                    ? "Engine service sehat"
                    : embedAvail
                      ? "Engine service tidak terjangkau — run demo memakai fallback EMBEDDED"
                      : "Engine service tidak terjangkau"
                }
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    engineOk ? "bg-emerald-500" : embedAvail ? "bg-amber-500" : "bg-rose-500",
                  )}
                />
                engine {engineOk ? "sehat" : embedAvail ? "fallback" : "mati"}
              </span>

              {snapsPending ? (
                <Skeleton className="h-9 w-36" />
              ) : periodOptions.length > 0 ? (
                <Select value={effectivePeriodKey ?? undefined} onValueChange={(v) => setPeriodKey(v)}>
                  <SelectTrigger className="w-[150px] sm:w-[180px]" aria-label="Pilih periode snapshot">
                    <SelectValue placeholder="Pilih periode" />
                  </SelectTrigger>
                  <SelectContent>
                    {periodOptions.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : null}

              <ThemeToggle />
              <DensityToggle compact={uiCompact} onToggle={() => setUiCompact(!uiCompact)} />
            </div>
          </div>

          {/* Nav tab */}
          <nav aria-label="Navigasi tab utama" className="flex gap-1 overflow-x-auto nice-scroll pb-px -mb-px">
            {TABS.map((t) => {
              const Icon = t.icon;
              const active = activeTab === t.key;
              return (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => setActiveTab(t.key)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2 text-sm transition-colors",
                    active
                      ? "border-emerald-600 font-medium text-emerald-700 dark:text-emerald-300"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border",
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  {t.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Konten */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-3 sm:px-6 py-6">
        {activeTab === "overview" ? <OverviewTab /> : null}
        {activeTab === "ingest" ? <IngestTab /> : null}
        {activeTab === "pivot" ? <PivotTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "deviasi" ? <DeviasiTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "selisihin" ? <SelisihInTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "nominal" ? <NominalTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "laporan" ? <LaporanTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "followup" ? <FollowUpTab /> : null}
        {activeTab === "po" ? <PoTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "dq" ? <DqTab snapshotId={activeSnapshot?.id ?? null} /> : null}
        {activeTab === "config" ? <ConfigTab snapshotId={activeSnapshot?.id ?? null} /> : null}
      </main>

      {/* Footer sticky */}
      <footer className="mt-auto border-t bg-muted/40">
        <div className="mx-auto w-full max-w-7xl px-3 sm:px-6 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1.5 text-xs text-muted-foreground">
            <p className="flex items-center gap-1.5">
              <PackageSearch className="h-3.5 w-3.5" aria-hidden />
              SM-WEB v0.1 · PRD v1.1 · definisi 3.9.71-noSI · ingest ZIP / folder langsung / Google Drive
            </p>
            <p>
              Snapshot permanen per periode · 9 label CEK · INV missing≠0 · single-user (D-6) ·
              database terpisah IC (D-5)
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
