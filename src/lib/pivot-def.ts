// ============================================================
// SM-WEB — Task 55-b: kontrak & konstanta PIVOT MATRIX.
// Mirror STRUKTUR aplikasi desktop Stock-Monitoring v3.9.71
// (src/ui/pivot_view.py): baris PARENT = nama barang, SUB-BARIS =
// 10 metrik JENIS, kolom = resto (mode 🏪) atau tanggal (mode 📅).
// Dipakai bersama route /api/snapshots/[id]/pivot + tabs/PivotTab.
// ============================================================
import type { MetricKey } from "@/lib/types";

/** Satu sub-baris metrik untuk satu barang: nilai per kolom matriks.
 *  null = tidak ada baris sama sekali (INV-1: missing ≠ 0 — 0 vs null
 *  harus dibedakan; route hanya mengirim sel dengan nilai non-null). */
export interface PivotMatrixMetric {
  key: MetricKey;
  label: string;
  /** false = metrik tak aktif untuk mode ini (6.PEMAKAIAN (COM) hanya
   *  mode tanggal — mirror pivot_view.py:979-982); values kosong. */
  active: boolean;
  values: Record<string, number | null>;
}

/** Parent barang — mirror Treeview desktop: item_header + anak metric. */
export interface PivotMatrixItem {
  itemName: string;
  satuan: string;
  kategori: string;
  isGR: boolean;
  metrics: PivotMatrixMetric[];
  /** true = SEMUA sub-baris metrik aktifnya kosong (semua sel 0/null).
   *  Hanya muncul saat hideEmpty=0 — saat hideEmpty=1 parent seperti
   *  ini sudah dibuang server (mirror pivot_view.py:1093-1094). */
  hiddenAll?: boolean;
}

export interface PivotMatrixResponse {
  mode: "resto" | "tanggal";
  /** mode resto → SEMUA resto (key = restoCode, label = restoCode);
   *  mode tanggal → hari from..to (key = "d{n}", label = String(n)). */
  columns: { key: string; label: string }[];
  items: PivotMatrixItem[];
  from: number;
  to: number;
  dayCount: number;
  /** Jumlah barang sebelum baris kosong disembunyikan. */
  totalItems: number;
  /** Jumlah SUB-BARIS metrik tersembunyi (semua sel 0/null — v3.9.69). */
  hiddenEmptyRows: number;
  /** Opsi combo KATEGORI ala desktop: "(Semua)" → entri gabungan (bila
   *  data memuat kategori rekap) → nilai kategori terurut. */
  kategoriOptions: string[];
}

// ---------- KATEGORI (mirror pipeline/helpers.py v3.9.49/53/55) ----------

/** Entri gabungan default — KATEGORI_DEFAULT_LABEL (label ringkas v3.9.55). */
export const PIVOT_KATEGORI_GABUNGAN = "Deviasi (COM + Packaging)";
/** Label panjang v3.9.49–54 tetap dikenali (seleksi tersimpan lama —
 *  mirror _KATEGORI_DEFAULT_LABEL_LEGACY kategori_multi_values). */
export const PIVOT_KATEGORI_GABUNGAN_LEGACY = "COM DEVIASI - RESTO + Biaya Packaging - RESTO";
/** Dua nilai kategori rekap yang dicocokkan entri gabungan — KATEGORI_REKAP_VALUES
 *  (helpers.py:192; kecocokan EXACT pasangan, case-insensitive, BUKAN substring). */
export const PIVOT_KATEGORI_REKAP = ["COM DEVIASI - RESTO", "Biaya Packaging - RESTO"] as const;
/** Label tanpa filter (desktop "(All)" — web memakai "(Semua)"). */
export const PIVOT_KATEGORI_ALL = "(Semua)";

/** Apakah seleksi = entri gabungan (case-insensitive + strip — mirror
 *  kategori_multi_values helpers.py:199-221). */
export function isKategoriGabungan(sel: string): boolean {
  const s = sel.trim().toLowerCase();
  return (
    s === PIVOT_KATEGORI_GABUNGAN.toLowerCase() ||
    s === PIVOT_KATEGORI_GABUNGAN_LEGACY.toLowerCase()
  );
}

/** Apakah seleksi = 'Deviasi' legacy (kategori_passthrough desktop v3.9.45 —
 *  seleksi default era pra-kategori-rekap: exact | baris tanpa kategori). */
export function isKategoriDeviasiLegacy(sel: string): boolean {
  return sel.trim().toLowerCase() === "deviasi";
}

/** Apakah NILAI kategori cocok dengan seleksi combo — mirror blok filter
 *  KATEGORI _compute_payload pivot_view.py:883-906:
 *  1. entri gabungan → isin pasangan rekap (case-insensitive, strip);
 *  2. legacy 'Deviasi' → exact | '(Tanpa Kategori)' (kategori_passthrough);
 *  3. seleksi lain → exact string. */
export function matchKategoriValue(value: string, sel: string): boolean {
  if (isKategoriGabungan(sel)) {
    const norm = value.trim().toUpperCase();
    return (
      norm === PIVOT_KATEGORI_REKAP[0].toUpperCase() ||
      norm === PIVOT_KATEGORI_REKAP[1].toUpperCase()
    );
  }
  if (isKategoriDeviasiLegacy(sel)) {
    return value === sel || value === "(Tanpa Kategori)";
  }
  return value === sel;
}

// ---------- Warna kolom beku (khusus UI) ----------

/** Latar SOLID kolom beku kiri untuk sub-baris metrik. Hex terang VERBATIM
 *  METRIC_BG pivot_view.py:155-166 + override in_row/bm_row (#FFEB9C /
 *  #C6EFCE — _compute_row_tags:1262-1265), konsisten dgn metricPastelClass
 *  di desktop-parity.ts. Varian dark harus SOLID (bukan alpha) supaya
 *  kolom beku tidak tembus saat scroll horizontal (dark mode hanya
 *  konvensi web — desktop Tk tema terang saja). */
export const PIVOT_METRIC_STICKY_BG: Record<MetricKey, string> = {
  qtySaldoAwal: "bg-[#F5F5F5] dark:bg-slate-700",
  qtySO: "bg-[#F0F4FA] dark:bg-slate-700",
  qtySaldoAkhir: "bg-[#F2F8EE] dark:bg-slate-700",
  qtyDeviasi: "bg-[#FDF6E3] dark:bg-slate-700",
  qtyIN: "bg-[#FFEB9C] dark:bg-slate-800",
  qtyBarangMasuk: "bg-[#C6EFCE] dark:bg-slate-800",
  qtyCOM: "bg-[#E8E0F0] dark:bg-slate-700",
  qtySelisihIN: "bg-[#FCEEE8] dark:bg-slate-700",
  qtyBarangKeluar: "bg-[#FFF0E0] dark:bg-slate-700",
  qtyACR: "bg-[#F8F0F0] dark:bg-slate-700",
};
