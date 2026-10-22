// ============================================================
// SM-WEB — Warna & susunan PARITAS DESKTOP (Task 33 fitur #2 & #3)
// Semua nilai hex/aturan di bawah adalah CERMIN VERBATIM aplikasi
// desktop Stock-Monitoring v3.9.71 (f22bca6) — sumber: riset Task
// 33-a atas /home/z/desktop-src/stock-monitoring-python:
//   • deviasi_view.py:523-524  → HIGHLIGHT_COLS = Deviasi & SO_H,
//     HIGHLIGHT_BG #fef3c7 (amber-100) — selalu aktif di desktop;
//     di web jadi OPSI (toggle devRowColor) agar tampilan bersih
//     shadcn tetap tersedia sebagai default.
//   • deviasi_view.py:2774-2788 → warna TEKS baris per label CEK
//     utama (label pertama kolom CEK desktop).
//   • pivot_view.py:155-166 + 585-615 → METRIC_BG pastel per baris
//     metrik; override IN (#FFEB9C/#9C5700) & BARANG MASUK
//     (#C6EFCE/#006100); anomali 7.Selisih IN ≠ 0 → #FFC9C9.
//   • Rank kelompok (fitur #3): deviasi_view.py:2541-2572 —
//     |Deviasi| desc dalam kelompok Nama Barang, method="min",
//     dev=0/NaN → KOSONG (mirror 01.1 CEK STOCK V2.xlsb).
// Pemetaan web↔desktop: kolom Deviasi H + Nominal H ≈ kolom kerja
// yang di-highlight desktop (Deviasi & SO_H); deviasiH (Σ 1..H) =
// analog kumulatif web untuk Deviasi@H desktop.
// ============================================================
import type { CekLabel, MetricKey } from "@/lib/types";

/** Latar kolom kunci ala desktop (#fef3c7, amber-100) — HIGHLIGHT_BG. */
export const DEV_KEYCOL_BG =
  "bg-[#fef3c7] dark:bg-amber-500/15";

/** Warna teks baris per label CEK utama — mirror fg desktop
 *  (deviasi_view.py:2774-2788). Kosong berarti foreground netral
 *  (label PO Menunggu & Selisih IN memang tidak diberi tag fg
 *  khusus di desktop). */
const CEK_ROW_FG: Partial<Record<CekLabel, string>> = {
  "Promix 04": "text-[#0e7490] dark:text-cyan-300", // cek_promix
  "RI Balancing": "text-[#92400e] dark:text-amber-300", // cek_ri_bal
  "Kosong/Non Aktif": "text-[#b45309] dark:text-amber-400", // cek_kosong
  "Beda Tanggal": "text-[#2563eb] dark:text-blue-300", // cek_tanggal
  "Hitung Manual": "text-[#c2410c] dark:text-orange-300", // cek_manual
  "Turun Drastis": "text-[#dc2626] dark:text-red-300", // cek_drastis
  "ACR to BOM": "text-[#7c3aed] dark:text-violet-300", // cek_acr
};

/** Kelas warna teks untuk sel-sel TEKS baris (resto/nama/kategori)
 *  mengikuti label CEK utama — "" bila netral. */
export function cekRowTextClass(cek: CekLabel[]): string {
  if (cek.length === 0) return "";
  return CEK_ROW_FG[cek[0]] ?? "";
}

/** Pastel baris per metrik JENIS — mirror METRIC_BG pivot_view.py:155-166
 *  + override in_row (#FFEB9C) & bm_row (#C6EFCE) pivot_view.py:605-611.
 *  Varian dark memakai alpha agar kontras dark mode tetap terjaga
 *  (nilai pastel hex desktop hanya untuk tema terang). */
const METRIC_PASTEL: Record<MetricKey, string> = {
  qtySaldoAwal: "bg-[#F5F5F5] dark:bg-slate-500/15",
  qtySO: "bg-[#F0F4FA] dark:bg-sky-500/10",
  qtySaldoAkhir: "bg-[#F2F8EE] dark:bg-lime-500/10",
  qtyDeviasi: "bg-[#FDF6E3] dark:bg-yellow-500/10",
  qtyIN: "bg-[#FFEB9C] dark:bg-amber-400/20", // override in_row desktop
  qtyBarangMasuk: "bg-[#C6EFCE] dark:bg-emerald-500/20", // override bm_row
  qtyCOM: "bg-[#E8E0F0] dark:bg-violet-500/10",
  qtySelisihIN: "bg-[#FCEEE8] dark:bg-orange-500/10",
  qtyBarangKeluar: "bg-[#FFF0E0] dark:bg-orange-400/10",
  qtyACR: "bg-[#F8F0F0] dark:bg-rose-500/10",
};

/** Kelas pastel untuk <tr> pivot sesuai metrik aktif. */
export function metricPastelClass(metric: MetricKey): string {
  return METRIC_PASTEL[metric];
}

/** Override fg NILAI ala desktop untuk dua metrik bersignifikan
 *  ekonomi (in_row fg #9C5700 · bm_row fg #006100) — "" bila netral. */
export function metricValueFgClass(metric: MetricKey): string {
  if (metric === "qtyIN") return "text-[#9C5700] dark:text-amber-200";
  if (metric === "qtyBarangMasuk") return "text-[#006100] dark:text-emerald-200";
  return "";
}

/** Latar sel anomali 7.Selisih IN ≠ 0 — mirror #FFC9C9 desktop
 *  (pivot_view.py _compute_row_tags). */
export const SIN_ANOMALY_BG = "bg-[#FFC9C9] dark:bg-rose-500/25";

/** Sort natural ala desktop (v3.9.62 — angka+teks campuran):
 *  dipakai untuk urutan nama barang dalam mode kelompok. */
const natColl = new Intl.Collator("id", { numeric: true, sensitivity: "base" });
export function naturalCompare(a: string, b: string): number {
  return natColl.compare(a, b);
}

/** Rank method="min" descending dalam kelompok — cermin
 *  deviasi_view.py:2566-2572: rank = 1 + jumlah baris lain di
 *  kelompok dengan nilai ABSOLUT lebih besar; dev=0/NaN → null
 *  (tampil kosong). Diwebkan atas frame TERFILTER (renumber
 *  per filter — paritas komentar desktop 2563-2565). */
export function rankMinInGroups<T>(
  rows: T[],
  groupKey: (r: T) => string,
  value: (r: T) => number | null,
): Map<T, number | null> {
  const byGroup = new Map<string, T[]>();
  for (const r of rows) {
    const g = groupKey(r);
    const arr = byGroup.get(g) ?? [];
    arr.push(r);
    byGroup.set(g, arr);
  }
  const out = new Map<T, number | null>();
  for (const [, arr] of byGroup) {
    // |nilai| > 0 semua kandidat ranking — sisanya (0/null) otomatis kosong
    const absVals = arr
      .map((r) => {
        const v = value(r);
        return v === null || v === 0 ? null : Math.abs(v);
      })
      .filter((v): v is number => v !== null)
      .sort((a, b) => b - a);
    for (const r of arr) {
      const v = value(r);
      if (v === null || v === 0) {
        out.set(r, null);
        continue;
      }
      const abs = Math.abs(v);
      let rank = 1;
      for (const other of absVals) {
        if (other > abs) rank++;
      }
      out.set(r, rank); // method=min: ikat → rank sama
    }
  }
  return out;
}
