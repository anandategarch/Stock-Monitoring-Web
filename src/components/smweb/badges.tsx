"use client";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { AUDIT_NOTE_TEXT, CEK_NOTE_MAP } from "@/lib/cek";
import { CASE_STATUS_LABEL } from "@/lib/types";
import type { AuditNote, CekLabel, DqSeverity } from "@/lib/types";

/** Badge status akhir run — paritas 3 status desktop (§82b). */
export function RunStatusBadge({ status }: { status: string }) {
  if (status.startsWith("SELESAI_DENGAN")) {
    return <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300 border-amber-300 dark:border-amber-500/40 hover:bg-amber-100">⚠ SELESAI DENGAN PERINGATAN</Badge>;
  }
  if (status.startsWith("SELESAI_PARSIAL") || status === "GAGAL") {
    return <Badge variant="destructive">✖ {status === "GAGAL" ? "GAGAL" : "SELESAI PARSIAL"}</Badge>;
  }
  if (status === "SELESAI") {
    return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40 hover:bg-emerald-100">✓ SELESAI</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function DqSeverityBadge({ severity }: { severity: DqSeverity }) {
  if (severity === "ERROR") return <Badge variant="destructive">ERROR</Badge>;
  if (severity === "WARNING") {
    return <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300 border-amber-300 dark:border-amber-500/40 hover:bg-amber-100">WARNING</Badge>;
  }
  return <Badge variant="secondary">INFO</Badge>;
}

export function CaseStatusBadge({ status }: { status: string }) {
  const label = CASE_STATUS_LABEL[status] ?? status;
  if (status === "PENDING") {
    return <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-300">{label}</Badge>;
  }
  if (status === "DIPROSES") {
    return <Badge className="bg-teal-100 text-teal-800 dark:bg-teal-500/15 dark:text-teal-300 border-teal-300 dark:border-teal-500/40 hover:bg-teal-100">{label}</Badge>;
  }
  if (status === "SELESAI") {
    return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40 hover:bg-emerald-100">{label}</Badge>;
  }
  return <Badge variant="secondary">{label}</Badge>;
}

/** Label CEK + tooltip keterangan (9 label kanonik). */
export function CekBadgeList({ cek, auditNotes, compact }: { cek: CekLabel[]; auditNotes?: AuditNote[]; compact?: boolean }) {
  if (cek.length === 0 && (!auditNotes || auditNotes.length === 0)) {
    return <span className="text-muted-foreground text-xs">—</span>;
  }
  return (
    <TooltipProvider delayDuration={200}>
      <div className={cn("flex flex-wrap gap-1", compact && "gap-0.5")}>
        {cek.map((c) => (
          <Tooltip key={c}>
            <TooltipTrigger asChild>
              <Badge
                variant="outline"
                className={cn(
                  "cursor-help",
                  c === "ACR to BOM" && "border-rose-300 text-rose-700 dark:text-rose-300",
                  c === "Kosong/Non Aktif" && "text-muted-foreground",
                )}
              >
                {c}
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="max-w-64 text-xs">{CEK_NOTE_MAP[c]}</TooltipContent>
          </Tooltip>
        ))}
        {(auditNotes ?? []).map((n) => (
          <Tooltip key={n}>
            <TooltipTrigger asChild>
              <Badge variant="outline" className="cursor-help border-violet-300 text-violet-700 dark:text-violet-300">
                Audit {n}
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="max-w-64 text-xs">{AUDIT_NOTE_TEXT[n]}</TooltipContent>
          </Tooltip>
        ))}
      </div>
    </TooltipProvider>
  );
}
