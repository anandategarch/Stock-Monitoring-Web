// ============================================================
// SM-WEB — Task 55-d: tipe respons DEVIASI ala DESKTOP (wide matrix
// per-tanggal). Tab Deviasi GR/PCS web kini menampilkan kolom
// SO(H-2)..SO(H+2) + In(H-1)..In(H+1) persis COLUMNS desktop
// (deviasi_view.py:473-519) dengan heading dinamis _col_display_name
// (deviasi_view.py:1565-1586). File ini HANYA tipe — dipakai bersama
// route /api/snapshots/[id]/deviasi dan DeviasiTab.
// ============================================================
import type { AuditNote, CekLabel } from "@/lib/types";

/** Satu kolom per-tanggal (SO/In). `key` = id kolom desktop
 *  ("SO_H-2".."SO_H+2", "In_H-1".."In_H+1"); `label` = heading dinamis
 *  _col_display_name (mis. H=25 → "SO_23"; tanggal hasil 0 → "…_lalu",
 *  tanggal < 0 → "…_—" — tanggal 0/negatif tak pernah ada sebagai
 *  tanggal); `value` = qty hari itu (null = missing INV-1). */
export interface DeviasiDateCol {
  key: string;
  label: string;
  value: number | null;
}

/** Satu pasangan resto × barang × satuan — grain baris wide-matrix. */
export interface DeviasiDesktopRow {
  fingerprint: string;
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  /** Kolom SO per-tanggal, urut H-2..H+2 (desktop "SO_H-2".."SO_H+2"). */
  soCols: DeviasiDateCol[];
  /** Kolom In (kiriman — BUKAN kolom Stock/SO), urut H-1..H+1
   *  (desktop IN_COLS baris 542-543, header teal #0e7490). */
  inCols: DeviasiDateCol[];
  /** Sistem = qtySaldoAkhir @H (desktop baris 2005); null = missing. */
  sistem: number | null;
  /** Deviasi = SO_H − Sistem bila SO_H tersedia (desktop baris 2058,
   *  sistem missing = 0 ala fillna desktop); null bila SO_H missing. */
  deviasi: number | null;
  /** Nominal = hargaEfektif @H × Deviasi (null-safe — analog kolom
   *  "Nominal" desktop = Harga × Deviasi@H). */
  nominal: number | null;
  /** |Deviasi| / max(Σ qtyACR semua hari pasangan, ε) × 100;
   *  Σ ACR = 0 → null (kolom "Dev to BOM%" desktop baris 505). */
  devToBomPct: number | null;
  /** Σ qtyDeviasi pasangan sama pada snapshot ACTIVE periode lalu;
   *  null bila snapshot lalu tak ada ATAU pasangan tak ada (sel "—"). */
  devBulanLalu: number | null;
  /** Σ qtyACR seluruh hari pasangan — bahan CEK "ACR to BOM" live & Dev to BOM%. */
  acrTotal: number;
  /** Label CEK tersimpan (gabungan cekJson semua hari pasangan, TANPA
   *  "ACR to BOM" — label itu dihitung ulang live di UI dari ambang,
   *  FR-30, semantik CEK web lama dipertahankan). */
  cek: CekLabel[];
  /** Catatan audit unik semua hari pasangan (B1–B4). */
  auditNotes: AuditNote[];
  /** Peringkat |Deviasi| dalam kelompok itemName (semua resto, pasangan
   *  satuan sama) — method min ala desktop v3.9.65 (nilai sama → rank
   *  sama); deviasi 0/null → rank null. */
  rank: number | null;
  harga: number | null;
  konversiOk: boolean;
}

export interface DeviasiDesktopResponse {
  snapshotId: string;
  periodKey: string;
  group: "GR" | "PCS";
  h: number;
  ambang: number;
  /** True bila snapshot ACTIVE periode lalu ditemukan. */
  hasPrev: boolean;
  /** periodKey snapshot lalu (null bila tak ada). */
  prevPeriodKey: string | null;
  totalRows: number;
  rows: DeviasiDesktopRow[];
}
