"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function StatCard({
  title,
  value,
  sub,
  icon: Icon,
  tone = "neutral",
}: {
  title: string;
  value: string;
  sub?: string;
  icon?: LucideIcon;
  tone?: "neutral" | "emerald" | "rose" | "amber" | "teal";
}) {
  const toneClass = {
    neutral: "text-foreground",
    emerald: "text-emerald-600 dark:text-emerald-400",
    rose: "text-rose-600 dark:text-rose-400",
    amber: "text-amber-600 dark:text-amber-400",
    teal: "text-teal-600 dark:text-teal-400",
  }[tone];
  return (
    <Card className="p-0 gap-0">
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs sm:text-sm font-medium text-muted-foreground">{title}</p>
          {Icon ? <Icon className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden /> : null}
        </div>
        <p className={cn("mt-1.5 text-xl sm:text-2xl font-semibold tracking-tight cell-num", toneClass)}>
          {value}
        </p>
        {sub ? <p className="mt-1 text-xs text-muted-foreground">{sub}</p> : null}
      </CardContent>
    </Card>
  );
}
