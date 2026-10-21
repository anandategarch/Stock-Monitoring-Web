"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("border-dashed", className)}>
      <CardContent className="flex flex-col items-center justify-center gap-3 p-8 sm:p-12 text-center">
        {Icon ? <Icon className="h-10 w-10 text-muted-foreground/60" aria-hidden /> : null}
        <div className="space-y-1">
          <p className="font-medium">{title}</p>
          {description ? (
            <p className="text-sm text-muted-foreground max-w-md">{description}</p>
          ) : null}
        </div>
        {action}
      </CardContent>
    </Card>
  );
}
