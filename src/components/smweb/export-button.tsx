"use client";

// ============================================================
// Task 55-c — Tombol Export Excel (.xlsx) generik.
// Parity fitur 💾 desktop: memicu unduhan workbook multi-sheet
// dari GET /api/snapshots/[id]/export (route mandiri — sheet
// tunggal via ?sheet=, default semua sheet).
// Komponen ini dipasang integrator di tab-tab analisis; tidak
// memegang state loading karena unduhan ditangani browser
// lewat window.location.assign (halaman tidak berpindah).
// ============================================================

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Sheet yang tersedia di endpoint export (sama dengan route API). */
export type ExportSheet = "all" | "pivot" | "deviasi" | "selisih" | "nominal" | "po";

export interface ExportButtonProps {
  /** ID snapshot yang datanya di-export. */
  snapshotId: string;
  /** Sheet yang diminta: "all" (default) atau satu sheet tertentu. */
  sheet?: ExportSheet;
  /** Teks tombol — default "Export Excel". */
  label?: string;
  /** Ukuran tombol shadcn/ui — default "default". */
  size?: "sm" | "default";
  /** Kelas tambahan untuk penempatan oleh integrator. */
  className?: string;
}

export function ExportButton({
  snapshotId,
  sheet = "all",
  label = "Export Excel",
  size = "default",
  className,
}: ExportButtonProps) {
  const sheetText = sheet === "all" ? "semua sheet" : `sheet ${sheet}`;

  function handleClick() {
    // Unduhan langsung: response API membawa Content-Disposition
    // attachment → browser menyimpan file, halaman tetap di tempat.
    const url = `/api/snapshots/${encodeURIComponent(snapshotId)}/export?sheet=${sheet}`;
    window.location.assign(url);
  }

  return (
    <Button
      type="button"
      variant="outline"
      size={size}
      className={className}
      onClick={handleClick}
      disabled={!snapshotId}
      aria-label={`${label} — unduh ${sheetText} snapshot ini sebagai file Excel`}
    >
      <Download aria-hidden="true" />
      {label}
    </Button>
  );
}
