// Tab 🧪 Kualitas Data — Panel Kualitas Data per snapshot (FR-60..62, INV-6):
// semua anomali format pipeline terlihat (bukan log senyap), dikelompokkan 10 kelas.
"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Database, FileWarning, FlaskConical, Info, ShieldCheck } from "lucide-react";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useDq } from "@/hooks/use-sm-api";
import { DqSeverityBadge } from "@/components/smweb/badges";
import { EmptyState } from "@/components/smweb/empty-state";
import { StatCard } from "@/components/smweb/stat-card";
import { fmtInt } from "@/lib/format";
import type { DqIssueDto, DqSeverity } from "@/lib/types";

/** Deskripsi singkat 10 kelas isu kualitas data (Task 31-c — FR-60). */
const DQ_CODE_DESC: Record<string, string> = {
  SKIP_FILE: "File dilewati — sumber tidak dapat dibaca/tidak ada",
  SCHEMA_WARNING: "Struktur sheet berbeda (fallback/missing kolom)",
  FALLBACK_BIND_9901: "Pengikatan 9901 fallback (tanpa Nomor Penerimaan)",
  VALUE_MISSING: "Kolom VALUE kosong pada baris",
  TANGGAL_MISSING: "Kolom Tanggal kosong/tidak valid",
  KONVERSI_GAGAL: "Konversi satuan rekap↔41.09 gagal (penanda *)",
  KATEGORI_KOSONG: "Kategori barang kosong — '(Tanpa Kategori)' jujur",
  DUPLIKAT_BARIS: "Baris persis duplikat dihapus otomatis",
  PREFLIGHT_FOLDER: "Preflight folder sumber",
  TANPA_HARGA: "Pasangan deviasi tanpa harga 41.09",
};

const SEVERITY_ORDER: Record<DqSeverity, number> = { ERROR: 0, WARNING: 1, INFO: 2 };

export default function DqTab({ snapshotId }: { snapshotId: string | null }) {
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const { data, isPending, error } = useDq(snapshotId);
  const issues = useMemo(() => data?.issues ?? [], [data]);

  const counts = useMemo(
    () => ({
      ERROR: issues.filter((i) => i.severity === "ERROR").length,
      WARNING: issues.filter((i) => i.severity === "WARNING").length,
      INFO: issues.filter((i) => i.severity === "INFO").length,
    }),
    [issues],
  );

  const filtered = useMemo(
    () =>
      severityFilter === "ALL"
        ? issues
        : issues.filter((i) => i.severity === severityFilter),
    [issues, severityFilter],
  );

  // Kelompokkan per code (10 kelas) — badge dominan = severity tertinggi di kelas tsb.
  const groups = useMemo(() => {
    const map = new Map<string, DqIssueDto[]>();
    for (const iss of filtered) {
      const list = map.get(iss.code);
      if (list) list.push(iss);
      else map.set(iss.code, [iss]);
    }
    return [...map.entries()]
      .map(([code, list]) => ({
        code,
        list,
        dominant: (["ERROR", "WARNING", "INFO"] as DqSeverity[]).find((s) =>
          list.some((i) => i.severity === s),
        ) ?? "INFO",
      }))
      .sort(
        (a, b) =>
          SEVERITY_ORDER[a.dominant] - SEVERITY_ORDER[b.dominant] ||
          b.list.length - a.list.length ||
          a.code.localeCompare(b.code),
      );
  }, [filtered]);

  const header = (
    <div>
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <FlaskConical className="h-5 w-5 text-emerald-600" aria-hidden /> 🧪 Kualitas Data
      </h2>
      <p className="text-sm text-muted-foreground mt-1">
        Setiap anomali format pipeline (skip file, kolom kosong, konversi gagal, …) tampil di sini —
        bukan log senyap (INV-6). Dikelompokkan per kelas, bisa di-drill-down per isu.
      </p>
    </div>
  );

  if (!snapshotId) {
    return (
      <div className="space-y-6">
        {header}
        <EmptyState
          icon={Database}
          title="Belum ada snapshot periode aktif"
          description="Panel kualitas data menempel pada snapshot terkomit. Pilih periode di header, atau jalankan pipeline di tab Proses & Ingest."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {header}

      {/* Ringkas per severity */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard title="ERROR" value={fmtInt(counts.ERROR)} icon={AlertTriangle} tone="rose" sub="wajib ditindak" />
        <StatCard title="WARNING" value={fmtInt(counts.WARNING)} icon={AlertTriangle} tone="amber" sub="perlu ditinjau" />
        <StatCard title="INFO" value={fmtInt(counts.INFO)} icon={Info} tone="neutral" sub="catatan saja" />
      </div>

      {/* Filter severity lokal */}
      <div className="rounded-xl border bg-card p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="dq-severity">Severity</Label>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger id="dq-severity" className="w-full" aria-label="Filter severity">
              <SelectValue placeholder="Semua" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Semua</SelectItem>
              <SelectItem value="ERROR">ERROR</SelectItem>
              <SelectItem value="WARNING">WARNING</SelectItem>
              <SelectItem value="INFO">INFO</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Kelompok per kode (Accordion) */}
      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon={FileWarning}
          title="Gagal memuat isu kualitas data"
          description={error instanceof Error ? error.message : "Permintaan gagal."}
        />
      ) : issues.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="Tidak ada isu kualitas data"
          description="Snapshot ini tidak memiliki isu format pipeline yang tercatat."
        />
      ) : groups.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="Tidak ada isu untuk severity ini"
          description="Tidak ada isu dengan severity terpilih. Ganti filter ke “Semua” untuk melihat semua kelas."
        />
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Accordion type="multiple" className="p-2 sm:p-4 space-y-1">
            {groups.map((g) => (
              <AccordionItem key={g.code} value={g.code} className="border-b last:border-b-0">
                <AccordionTrigger className="hover:no-underline py-3">
                  <span className="flex flex-1 items-center gap-2 text-left min-w-0">
                    <DqSeverityBadge severity={g.dominant} />
                    <span className="font-mono text-xs font-medium">{g.code}</span>
                    <span className="text-xs text-muted-foreground hidden sm:inline truncate">
                      {DQ_CODE_DESC[g.code] ?? ""}
                    </span>
                    <Badge variant="outline" className="ml-auto shrink-0">{fmtInt(g.list.length)}×</Badge>
                  </span>
                </AccordionTrigger>
                <AccordionContent className="space-y-3">
                  {g.list.map((iss) => (
                    <div key={iss.id} className="rounded-md border bg-muted/30 px-3 py-2 space-y-1">
                      <p className="text-sm">{iss.message}</p>
                      <p className="font-mono text-[11px] text-muted-foreground break-words">
                        {iss.source ?? "(tanpa sumber)"}
                        {iss.sheet ? ` · ${iss.sheet}` : ""}
                        {iss.rowNumber !== null ? ` · baris ${iss.rowNumber}` : ""}
                        {iss.rawValue ? ` · raw: ${iss.rawValue}` : ""}
                      </p>
                    </div>
                  ))}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Setiap isu juga tampil di pratinjau run (tab Proses &amp; Ingest) dan tercatat permanen pada snapshot.
      </p>
    </div>
  );
}
