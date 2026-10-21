/**
 * types.ts — salinan PERSIS semua tipe kontrak engine v1
 * (sumber kebenaran: /home/z/my-project/docs/ENGINE-CONTRACT.md).
 * Jangan ubah bentuk tipe tanpa bump contractVersion di kontrak.
 */

export type MetricKey =
  | "qtySaldoAwal" | "qtySO" | "qtySaldoAkhir" | "qtyDeviasi"
  | "qtyIN" | "qtyBarangMasuk" | "qtyCOM" | "qtySelisihIN"
  | "qtyBarangKeluar" | "qtyACR";

export const METRICS: { key: MetricKey; label: string; short: string }[] = [
  { key: "qtySaldoAwal",    label: "SALDO AWAL",        short: "SA"  },
  { key: "qtySO",           label: "1.SO",              short: "SO"  },
  { key: "qtySaldoAkhir",   label: "2.SALDO AKHIR",     short: "SKA" },
  { key: "qtyDeviasi",      label: "3.DEVIASI",         short: "DEV" },
  { key: "qtyIN",           label: "4.IN",              short: "IN"  },
  { key: "qtyBarangMasuk",  label: "5.BARANG MASUK",    short: "BM"  },
  { key: "qtyCOM",          label: "6.PEMAKAIAN (COM)", short: "COM" },
  { key: "qtySelisihIN",    label: "7.SELISIH IN",      short: "SIN" },
  { key: "qtyBarangKeluar", label: "8.BARANG KELUAR",   short: "BK"  },
  { key: "qtyACR",          label: "9.ACR",             short: "ACR" },
];

/** 9 label CEK kanonik (PRD Lampiran A.3) + catatan audit terpisah */
export type CekLabel =
  | "RI Balancing" | "Beda Tanggal" | "Promix 04" | "Kosong/Non Aktif"
  | "Hitung Manual" | "Turun Drastis" | "ACR to BOM" | "PO Menunggu" | "Selisih IN";
export type AuditNote = "B1" | "B2" | "B3" | "B4";

/** Grain baris: resto × barang × hari (D-1 SAH: grain hari) */
export interface EngineRow {
  restoCode: string;        // 6 huruf, mis. "CKGPAH"
  restoName: string;
  itemName: string;
  satuan: string;          // "kg" | "ltr" | "dus" | "pcs" | "gram" | "bks" | "pak"
  kategori: string;        // kosong = "(Tanpa Kategori)" — jujur, bukan error
  isGR: boolean;           // true = barang GR, false = PCS (FR-30 toggle)
  day: number;             // 1..31
  qtySaldoAwal: number | null;    // null = TIDAK ADA DATA (INV-1: missing ≠ 0)
  qtySO: number | null;
  qtySaldoAkhir: number | null;
  qtyDeviasi: number | null;      // SO − SALDO AKHIR, BERTANDA (INV-2)
  qtyIN: number | null;
  qtyBarangMasuk: number | null;
  qtyCOM: number | null;
  qtySelisihIN: number | null;   // BM − IN, bertanda
  qtyBarangKeluar: number | null;
  qtyACR: number | null;
  hargaEfektif: number | null;   // harga 41.09 dinormalkan (INV-3)
  konversiOk: boolean;            // false → penanda "*" & nominal null
  nominal: number | null;        // harga × deviasi; null bila konversi gagal / harga null
  cek: CekLabel[];                // label saat run (ambang run) — UI re-komputasi "ACR to BOM" live
  auditNote: AuditNote | null;
}

export interface EnginePrice {
  itemName: string;
  satuan: string;
  harga: number | null;
  rasioKonversi: number | null;  // rekap / 41.09
  konversiOk: boolean;
  alasan: string | null;         // alasan bila konversi gagal (Tanpa Harga)
}

export interface EngineSelisihInResto {
  restoCode: string;
  restoName: string;
  inAccurate: number;     // Σ 4.IN (42.05 + 32.24 + 99.01)
  barangMasuk: number;    // Σ 5.BARANG MASUK (rekap)
  selisih: number;        // BM − IN, bertanda
  hasilAudit: "OK" | "SELISIH";
  skorResto: number;      // itemBerselisih + tanggalTerdampak (🏆 SKOR RESTO)
  itemBerselisih: number;
  tanggalTerdampak: number;
}

export interface EnginePoItem {
  itemName: string;
  qty: number;
  satuan: string;
  status: string;          // "menunggu diproses" | "diproses" | "selesai" | "batal"
  diterimaSebagian: boolean;
}

export interface EnginePo {
  cabang: string;          // restoCode
  restoName: string;
  poNumber: string;       // "PO-YYMM-####"
  tanggal: string;        // "YYYY-MM-DD"
  supplier: string;
  itemCount: number;
  status: string;         // ringkasan: "Menunggu" | "Diproses" | "Selesai"
  statusPesanan: string;  // status pesanan 32.43 dominan
  annotasi: string | null; // "↳ menunggu diproses" dst (paritas desktop)
  items: EnginePoItem[];
}

export type DqSeverity = "ERROR" | "WARNING" | "INFO";

/** 10 kelas sinyal kualitas data (Task 31-c) — kode tetap, jangan direname */
export type DqCode =
  | "SKIP_FILE" | "SCHEMA_WARNING" | "FALLBACK_BIND_9901" | "VALUE_MISSING"
  | "TANGGAL_MISSING" | "KONVERSI_GAGAL" | "KATEGORI_KOSONG" | "DUPLIKAT_BARIS"
  | "PREFLIGHT_FOLDER" | "TANPA_HARGA";

export interface EngineDqIssue {
  severity: DqSeverity;
  code: DqCode;
  message: string;          // Bahasa Indonesia, actionable
  source: string | null;    // nama file/folder
  sheet: string | null;
  rawValue: string | null;
  rowNumber: number | null;
}

export interface EngineLogLine {
  ts: string;               // ISO 8601
  level: "INFO" | "WARNING" | "ERROR";
  message: string;
}

export interface EngineSourceFile {
  folderKey: string;        // kunci folder config.json, mis. "Penjualan2205"
  fileName: string;
  sheetName: string | null;
  rowCount: number;
  sizeBytes: number;
  status: "OK" | "SKIP" | "WARNING";
}

export interface EngineSummary {
  restoCount: number;
  itemCount: number;
  rowCount: number;         // resto × item × hari
  dayCount: number;         // jumlah hari dalam periode (28..31)
  nominalTotal: number;     // Σ nominal (baris dengan nominal ≠ null)
  deviasiQtyTotal: number;  // Σ deviasi bertanda
  skipFileCount: number;
  warningCount: number;     // WAJIB = jumlah baris log ber-level WARNING (kontrak §82b)
  errorCount: number;       // WAJIB = jumlah baris log ber-level ERROR
  dqIssueCount: number;
  poCount: number;
}

export type RunStatus =
  | "SELESAI" | "SELESAI_DENGAN_PERINGATAN" | "SELESAI_PARSIAL";

export interface EngineResult {
  contractVersion: "1";
  engineKind: "demo" | "production";
  engineName: string;
  engineVersion: string;
  definitionVersion: string;   // "3.9.71-noSI" (INV-4 — ikut tersimpan di snapshot)
  periodKey: string;           // echo
  params: { tanggalH: number; ambangAcrPct: number; bundleName: string | null };
  status: RunStatus;           // ERROR dq > 0 → PARSIAL · WARNING dq > 0 → DENGAN_PERINGATAN · else SELESAI
  startedAt: string;           // ISO 8601
  durationMs: number;
  summary: EngineSummary;
  sourceFiles: EngineSourceFile[];
  rows: EngineRow[];          // terurut: restoCode → itemName → day
  prices: EnginePrice[];      // satu per itemName
  selisihIn: EngineSelisihInResto[];
  po: EnginePo[];
  dqIssues: EngineDqIssue[];
  logs: EngineLogLine[];       // memuat ≥1 baris per DQ issue (jejak §82b)
}

export interface EngineHealth {
  status: "ok";
  engineKind: "demo" | "production";
  engineName: string;        // demo: "SM-DEMO-Engine" · produksi: "SM-FastAPI-Engine"
  engineVersion: string;     // semver
  definitionVersion: string; // "3.9.71-noSI"
  contractVersion: string;   // "1"
  lastProcessAt: string | null;      // ISO 8601
  lastDurationMs: number | null;
  lastStatus: string | null;        // status run terakhir
  uptimeSec: number;
  parityNote: string;       // penanda jujur paritas (wajib tampil di UI Config)
}

export interface EngineProcessRequest {
  periodKey: string;       // "YYYY-MM", wajib, regex ^\d{4}-(0[1-9]|1[0-2])$
  tanggalH: number;        // cut-off H, wajib, integer 1..31 (default dari Setting: 25)
  ambangAcrPct: number;    // ambang ACR %, wajib, integer 1..200 (default 80)
  bundleName?: string;     // label bundle (tampilan saja)
  seed?: number;           // entropi tambahan opsional, default 0
}
