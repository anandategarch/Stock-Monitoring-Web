// Label CEK kanonik (PRD Lampiran A.3) + re-komputasi "ACR to BOM" live (FR-30).
// Saat analis mengubah AMBANG ACR / TANGGAL H di UI, label ACR to BOM dihitung ulang
// dari bahan mentah (deviasi & total ACR) — tidak perlu run ulang engine.
import type { AuditNote, CekLabel } from "./types";

export const CEK_NOTE_MAP: Record<CekLabel, string> = {
  "RI Balancing": "Nomor RI ganda/26↔25 vs Nomor PO (rekonsiliasi penerimaan)",
  "Beda Tanggal": "Tanggal SO tidak cocok dengan tanggal H cut-off (formula kolom Y)",
  "Promix 04": "Barang Promix 04 — perlu verifikasi komposisi",
  "Kosong/Non Aktif": "Tidak ada pergerakan sepanjang periode",
  "Hitung Manual": "Pengisian manual (HM) — berpotensi salah input",
  "Turun Drastis": "Deviasi turun drastis dibanding pemakaian",
  "ACR to BOM": "|Deviasi| melebihi ambang% × Total ACR (penyesuaian vs pemakaian teoretis)",
  "PO Menunggu": "Ada PO item ini yang masih menunggu diproses (32.43)",
  "Selisih IN": "Barang Masuk (rekap) ≠ IN (Accurate) signifikan",
};

export const AUDIT_NOTE_TEXT: Record<AuditNote, string> = {
  B1: "Catatan Audit B1 — fisik lebih besar dari kartu stok",
  B2: "Catatan Audit B2 — kartu stok lebih besar dari fisik",
  B3: "Catatan Audit B3 — mutasi terakhir belum tercatat",
  B4: "Catatan Audit B4 — satuan/qty perlu konfirmasi TL",
};

/** Re-komputasi live label "ACR to BOM" (FR-30). */
export function isAcrToBom(
  deviasiH: number | null,
  acrTotal: number,
  ambangPct: number,
): boolean {
  if (deviasiH === null) return false;
  if (acrTotal <= 0) return false;
  return Math.abs(deviasiH) > (ambangPct / 100) * acrTotal;
}

/** Gabung label tersimpan (TANPA "ACR to BOM" run) + hasil re-komputasi live. */
export function mergeCekLabels(
  storedCek: CekLabel[],
  deviasiH: number | null,
  acrTotal: number,
  ambangPct: number,
): CekLabel[] {
  const base = storedCek.filter((c) => c !== "ACR to BOM");
  const set = new Set<CekLabel>(base);
  if (isAcrToBom(deviasiH, acrTotal, ambangPct)) set.add("ACR to BOM");
  // jaga urutan kanonik
  const canonical: CekLabel[] = [
    "RI Balancing", "Beda Tanggal", "Promix 04", "Kosong/Non Aktif",
    "Hitung Manual", "Turun Drastis", "ACR to BOM", "PO Menunggu", "Selisih IN",
  ];
  return canonical.filter((c) => set.has(c));
}
