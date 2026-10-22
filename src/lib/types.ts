// ============================================================
// SM-WEB — Tipe kontrak & API (cermin docs/ENGINE-CONTRACT.md v1)
// Sumber kebenaran: docs/ENGINE-CONTRACT.md — jangan ubah sembarangan.
// Dipakai bersama oleh API routes, hooks, dan semua tab UI.
// ============================================================

// ---------- Kontrak engine ----------

export type MetricKey =
  | "qtySaldoAwal" | "qtySO" | "qtySaldoAkhir" | "qtyDeviasi"
  | "qtyIN" | "qtyBarangMasuk" | "qtyCOM" | "qtySelisihIN"
  | "qtyBarangKeluar" | "qtyACR";

export const METRICS: { key: MetricKey; label: string; short: string }[] = [
  { key: "qtySaldoAwal", label: "SALDO AWAL", short: "SA" },
  { key: "qtySO", label: "1.SO", short: "SO" },
  { key: "qtySaldoAkhir", label: "2.SALDO AKHIR", short: "SKA" },
  { key: "qtyDeviasi", label: "3.DEVIASI", short: "DEV" },
  { key: "qtyIN", label: "4.IN", short: "IN" },
  { key: "qtyBarangMasuk", label: "5.BARANG MASUK", short: "BM" },
  { key: "qtyCOM", label: "6.PEMAKAIAN (COM)", short: "COM" },
  { key: "qtySelisihIN", label: "7.SELISIH IN", short: "SIN" },
  { key: "qtyBarangKeluar", label: "8.BARANG KELUAR", short: "BK" },
  { key: "qtyACR", label: "9.ACR", short: "ACR" },
];

export const METRIC_KEYS: MetricKey[] = METRICS.map((m) => m.key);

export type CekLabel =
  | "RI Balancing" | "Beda Tanggal" | "Promix 04" | "Kosong/Non Aktif"
  | "Hitung Manual" | "Turun Drastis" | "ACR to BOM" | "PO Menunggu" | "Selisih IN";

export const CEK_LABELS: CekLabel[] = [
  "RI Balancing", "Beda Tanggal", "Promix 04", "Kosong/Non Aktif",
  "Hitung Manual", "Turun Drastis", "ACR to BOM", "PO Menunggu", "Selisih IN",
];

export type AuditNote = "B1" | "B2" | "B3" | "B4";
export const AUDIT_NOTES: AuditNote[] = ["B1", "B2", "B3", "B4"];

export type DqSeverity = "ERROR" | "WARNING" | "INFO";

export type DqCode =
  | "SKIP_FILE" | "SCHEMA_WARNING" | "FALLBACK_BIND_9901" | "VALUE_MISSING"
  | "TANGGAL_MISSING" | "KONVERSI_GAGAL" | "KATEGORI_KOSONG" | "DUPLIKAT_BARIS"
  | "PREFLIGHT_FOLDER" | "TANPA_HARGA";

export const DQ_CODES: DqCode[] = [
  "SKIP_FILE", "SCHEMA_WARNING", "FALLBACK_BIND_9901", "VALUE_MISSING",
  "TANGGAL_MISSING", "KONVERSI_GAGAL", "KATEGORI_KOSONG", "DUPLIKAT_BARIS",
  "PREFLIGHT_FOLDER", "TANPA_HARGA",
];

export interface EngineRow {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  isGR: boolean;
  day: number;
  qtySaldoAwal: number | null;
  qtySO: number | null;
  qtySaldoAkhir: number | null;
  qtyDeviasi: number | null;
  qtyIN: number | null;
  qtyBarangMasuk: number | null;
  qtyCOM: number | null;
  qtySelisihIN: number | null;
  qtyBarangKeluar: number | null;
  qtyACR: number | null;
  hargaEfektif: number | null;
  konversiOk: boolean;
  nominal: number | null;
  cek: CekLabel[];
  auditNote: AuditNote | null;
}

export interface EngineSummary {
  restoCount: number;
  itemCount: number;
  rowCount: number;
  dayCount: number;
  nominalTotal: number;
  deviasiQtyTotal: number;
  skipFileCount: number;
  warningCount: number;
  errorCount: number;
  dqIssueCount: number;
  poCount: number;
}

export interface EnginePrice {
  itemName: string;
  satuan: string;
  harga: number | null;
  rasioKonversi: number | null;
  konversiOk: boolean;
  alasan: string | null;
}

export interface EngineSelisihInResto {
  restoCode: string;
  restoName: string;
  inAccurate: number;
  barangMasuk: number;
  selisih: number;
  hasilAudit: "OK" | "SELISIH";
  skorResto: number;
  itemBerselisih: number;
  tanggalTerdampak: number;
}

export interface EnginePoItem {
  itemName: string;
  qty: number;
  satuan: string;
  status: string;
  diterimaSebagian: boolean;
}

export interface EnginePo {
  cabang: string;
  restoName: string;
  poNumber: string;
  tanggal: string;
  supplier: string;
  itemCount: number;
  status: string;
  statusPesanan: string;
  annotasi: string | null;
  items: EnginePoItem[];
}

export interface EngineDqIssue {
  severity: DqSeverity;
  code: DqCode;
  message: string;
  source: string | null;
  sheet: string | null;
  rawValue: string | null;
  rowNumber: number | null;
}

export interface EngineLogLine {
  ts: string;
  level: "INFO" | "WARNING" | "ERROR";
  message: string;
}

export interface EngineSourceFile {
  folderKey: string;
  fileName: string;
  sheetName: string | null;
  rowCount: number;
  sizeBytes: number;
  status: "OK" | "SKIP" | "WARNING";
}

export type RunStatus = "SELESAI" | "SELESAI_DENGAN_PERINGATAN" | "SELESAI_PARSIAL";

export interface EngineResult {
  contractVersion: "1";
  engineKind: "demo" | "production";
  engineName: string;
  engineVersion: string;
  definitionVersion: string;
  periodKey: string;
  params: { tanggalH: number; ambangAcrPct: number; bundleName: string | null };
  status: RunStatus;
  startedAt: string;
  durationMs: number;
  summary: EngineSummary;
  sourceFiles: EngineSourceFile[];
  rows: EngineRow[];
  prices: EnginePrice[];
  selisihIn: EngineSelisihInResto[];
  po: EnginePo[];
  dqIssues: EngineDqIssue[];
  logs: EngineLogLine[];
}

export interface EngineProcessRequest {
  periodKey: string;
  tanggalH: number;
  ambangAcrPct: number;
  bundleName?: string;
  seed?: number;
  /** Ekstensi PRODUKSI (FR-10): path server ke bundle yang sudah diekstrak
   *  (diunggah lewat /api/ingest/upload). Engine demo mengabaikan field ini. */
  bundlePath?: string;
}

export interface EngineHealth {
  status: "ok";
  engineKind: "demo" | "production";
  engineName: string;
  engineVersion: string;
  definitionVersion: string;
  contractVersion: string;
  lastProcessAt: string | null;
  lastDurationMs: number | null;
  lastStatus: string | null;
  uptimeSec: number;
  parityNote: string;
}

// ---------- Tipe API (respons Next.js) ----------

export interface SnapshotSummary {
  id: string;
  periodKey: string;
  /** BUILDING = komit mati di tengah jalan (snapshot setengah jadi — belum
   *  pernah terlihat di analisis); bisa dihapus lewat tab Konfigurasi setelah
   *  ±15 menit (Task 54 — jujur, bukan lagi ditampilkan sebagai SUPERSEDED). */
  state: "ACTIVE" | "SUPERSEDED" | "BUILDING";
  restoCount: number;
  itemCount: number;
  rowCount: number;
  dayCount: number;
  nominalTotal: number;
  deviasiQtyTotal: number;
  definitionVersion: string;
  params: { tanggalH: number; ambangAcrPct: number };
  committedAt: string;
  committedBy: string;
  supersededAt: string | null;
}

export interface RunSummary {
  id: string;
  periodKey: string;
  bundleName: string | null;
  status: string;
  definitionVersion: string;
  engineKind: string;
  engineVersion: string | null;
  durationMs: number | null;
  actor: string;
  startedAt: string;
  committedAt: string | null;
  summary: EngineSummary | null;
}

export interface DqIssueDto {
  id: string;
  severity: DqSeverity;
  code: DqCode;
  message: string;
  source: string | null;
  sheet: string | null;
  rawValue: string | null;
  rowNumber: number | null;
}

export interface SourceFileDto {
  id: string;
  folderKey: string;
  fileName: string;
  sheetName: string | null;
  rowCount: number | null;
  sizeBytes: number | null;
  status: "OK" | "SKIP" | "WARNING";
}

export interface LogLineDto {
  ts: string;
  level: "INFO" | "WARNING" | "ERROR";
  message: string;
}

export interface RunDetail {
  run: RunSummary & { params: { tanggalH: number; ambangAcrPct: number; bundleName: string | null } };
  dqIssues: DqIssueDto[];
  logs: LogLineDto[];
  sourceFiles: SourceFileDto[];
}

export interface RestoRef {
  restoCode: string;
  restoName: string;
}

export interface OverviewResponse {
  active: (SnapshotSummary & { snapshotId: string }) | null;
  previous: { snapshotId: string; periodKey: string; nominalTotal: number } | null;
  nominalDeltaPct: number | null;
  cases: { pending: number; diproses: number; selesai: number; dibatalkan: number; total: number };
  dq: { error: number; warning: number; info: number };
  runs: RunSummary[];
  nominalPerResto: { restoCode: string; restoName: string; nominal: number; deviasiQty: number }[];
  trend: { periodKey: string; nominalTotal: number; deviasiQtyTotal: number }[];
  topDeviations: { restoCode: string; restoName: string; itemName: string; satuan: string; kategori: string; nominal: number; qtyDeviasi: number }[];
  engine: EngineHealth | null;
  engineReachable: boolean;
  /** True bila fallback demo EMBEDDED aktif (deploy tanpa engine co-located). */
  engineEmbedAvailable: boolean;
  restos: RestoRef[];
}

export interface IngestProcessResponse {
  runBatchId: string;
  status: string;
  engineKind: string;
  definitionVersion: string;
  summary: EngineSummary;
  durationMs: number;
}

/** Satu folder kunci config.json (FR-2 — pemetaan identik desktop v3.9.71). */
export interface BundleFolderStat {
  folderKey: string;
  folderName: string;
  fileCount: number;
  totalBytes: number;
  present: boolean;
}

/** Hasil unggah + validasi struktur bundle (FR-1). */
export interface BundleManifest {
  bundleId: string;
  name: string;
  uploadedAt: string;
  fileCount: number;
  totalBytes: number;
  skippedEntries: number;
  folders: BundleFolderStat[];
  missingFolders: string[];
  /** Asal bundle: "drive" = ditarik langsung dari Google Drive (opsional). */
  source?: "upload" | "drive";
  /** File Drive bernama sama yang DILEWATI (versi terbaru menang, jujur dilaporkan). */
  skippedDuplicates?: { path: string; reason: string }[];
  /** File Drive bernama sama yang DIPERTAHANKAN SEMUANYA (tanpa tanggal → akhiran __2 dst.). */
  suffixedDuplicates?: string[];
  /** Rincian per folder Drive yang ditarik (hanya sumber drive). */
  driveFolders?: { folderName: string; folderKey: string | null; fileCount: number }[];
  /** File Drive yang DILEWATI saat ditarik (rusak/bukan Excel/0 byte) — jujur. */
  skippedFiles?: { path: string; reason: string }[];
  /** Pemotongan batas / subfolder gagal dibaca saat tarikan Drive — jujur. */
  driveNotices?: string[];
  /** True = hasil "Pratinjau Cepat" (listing Drive saja): file TIDAK
   *  diunduh, totalBytes tidak dihitung, bundleId kosong — TIDAK bisa
   *  diproses; hanya untuk cek struktur/jumlah (bebas kuota serverless). */
  previewOnly?: boolean;
}

/** Link folder Google Drive tersimpan — "biar ingat" (FR-1). */
export interface DriveFolderLinkDto {
  id: string;
  url: string;
  folderId: string;
  folderName: string;
  folderKey: string | null;
  fileCount: number;
  totalBytes: number;
  lastCheckedAt: string | null;
  lastUsedAt: string | null;
  createdAt: string;
}

// ---------- Agent lokal "Python di Laptop" (Task 51) ----------

export type AgentJobStatus =
  | "QUEUED" | "RUNNING" | "FINALIZING" | "COMPLETED" | "FAILED" | "CANCELLED";

/** Target folder Drive yang dijemput agent dari daftar link tersimpan. */
export interface AgentJobTarget {
  rowId: string | null;
  folderId: string;
  url: string;
  folderName: string;
  folderKey: string | null;
}

export interface AgentJobDto {
  id: string;
  kind: string;
  status: AgentJobStatus;
  periodKey: string;
  tanggalH: number;
  ambangAcrPct: number;
  bundleName: string | null;
  targets: AgentJobTarget[];
  progress: number;
  message: string | null;
  agentName: string | null;
  error: string | null;
  runBatchId: string | null;
  resultMeta: {
    summary: EngineSummary;
    engineKind: string | null;
    durationMs: number | null;
  } | null;
  createdAt: string;
  claimedAt: string | null;
  heartbeatAt: string | null;
  finishedAt: string | null;
}

export interface AgentStatusDto {
  online: boolean;
  agentName: string | null;
  lastSeenAt: string | null;
  engine: Record<string, unknown> | null;
  tokenConfigured: boolean;
  activeJob: AgentJobDto | null;
  recentJobs: AgentJobDto[];
}

export interface IngestCommitResponse {
  snapshotId: string;
  periodKey: string;
  rowCount: number;
  supersededPrevious: boolean;
  definitionVersion: string;
}

export interface PivotRow {
  itemName: string;
  satuan: string;
  kategori: string;
  isGR: boolean;
  values: Record<string, number | null>;
}

export interface PivotResponse {
  mode: "resto" | "tanggal";
  metric: MetricKey;
  columns: { key: string; label: string }[];
  rows: PivotRow[];
  from: number;
  to: number;
  dayCount: number;
  totalRowsBeforeHide: number;
  hiddenEmptyRows: number;
}

export interface DeviasiRow {
  fingerprint: string;
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  deviasiH: number | null;
  deviasiBulan: number | null;
  acrTotal: number;
  nominalH: number | null;
  nominalBulan: number | null;
  harga: number | null;
  konversiOk: boolean;
  cek: CekLabel[];
  auditNotes: AuditNote[];
  rankNominal: number | null;
}

export interface DeviasiResponse {
  snapshotId: string;
  periodKey: string;
  group: "GR" | "PCS";
  h: number;
  ambang: number;
  totalRows: number;
  rows: DeviasiRow[];
}

export interface DrilldownDay {
  day: number;
  qtySaldoAwal: number | null;
  qtySO: number | null;
  qtySaldoAkhir: number | null;
  qtyDeviasi: number | null;
  qtyIN: number | null;
  qtyBarangMasuk: number | null;
  qtyCOM: number | null;
  qtySelisihIN: number | null;
  qtyBarangKeluar: number | null;
  qtyACR: number | null;
  nominal: number | null;
  cek: CekLabel[];
  auditNote: AuditNote | null;
}

export interface DrilldownResponse {
  resto: RestoRef;
  item: {
    itemName: string;
    satuan: string;
    kategori: string;
    isGR: boolean;
    harga: number | null;
    konversiOk: boolean;
  };
  days: DrilldownDay[];
  monthly: {
    deviasiBulan: number;
    nominalBulan: number;
    acrTotal: number;
    inTotal: number;
    bmTotal: number;
    sinTotal: number;
    bkTotal: number;
    comTotal: number;
    soTotal: number;
  };
}

export interface SelisihInResponse {
  snapshotId: string;
  mode: string;
  total: { inAccurate: number; barangMasuk: number; selisih: number };
  rows: {
    restoCode: string;
    restoName: string;
    inAccurate: number;
    barangMasuk: number;
    selisih: number;
    hasilAudit: "OK" | "SELISIH";
    skorResto: number;
    itemBerselisih: number;
    tanggalTerdampak: number;
  }[];
}

export interface NominalRestoRow {
  restoCode: string;
  restoName: string;
  nominal: number;
  deviasiQty: number;
  deltaPct: number | null;
}

export interface TanpaHargaRow {
  itemName: string;
  satuan: string;
  kategori: string;
  alasan: string;
  qtyDeviasi: number;
}

export interface NominalResponse {
  snapshotId: string;
  periodKey: string;
  rows: NominalRestoRow[];
  total: { nominal: number; deviasiQty: number; deltaPct: number | null };
  com: { packagingNominal: number; packagingDeviasiQty: number };
  tanpaHarga: TanpaHargaRow[];
}

export interface LaporanKomparasiRow {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  nominalKini: number;
  nominalLalu: number;
  delta: number;
  deltaPct: number | null;
  arah: "NAIK" | "TURUN" | "TETAP";
  qtyDeviasiKini: number;
  qtyDeviasiLalu: number;
}

export interface LaporanAnomaliRow {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  comTotal: number;
  bmTotal: number;
  inTotal: number;
  selisih: number;
  nominal: number | null;
}

export interface LaporanResponse {
  mode: "komparasi" | "anomali_com" | "nominal_h";
  h: number;
  hasPrev: boolean;
  prevPeriodKey: string | null;
  komparasi: {
    rows: LaporanKomparasiRow[];
    totalKini: number;
    totalLalu: number;
    deltaPct: number | null;
  } | null;
  anomali: { rows: LaporanAnomaliRow[] } | null;
  nominalH: { rows: { restoCode: string; restoName: string; nominalH: number; nominalBulan: number; deviasiH: number }[]; total: { nominalH: number } } | null;
}

export interface PoItemDto {
  id: string;
  itemName: string;
  qty: number;
  satuan: string;
  status: string;
  diterimaSebagian: boolean;
}

export interface PoHeaderDto {
  id: string;
  cabang: string;
  restoName: string;
  poNumber: string;
  tanggal: string;
  supplier: string | null;
  itemCount: number;
  status: string;
  statusPesanan: string;
  annotasi: string | null;
  items: PoItemDto[];
}

export interface PoResponse {
  rows: PoHeaderDto[];
  restos: RestoRef[];
  statusOptions: string[];
}

export interface FollowUpCaseDto {
  id: string;
  fingerprint: string;
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  status: "PENDING" | "DIPROSES" | "SELESAI" | "DIBATALKAN";
  pic: string | null;
  periodFirstSeen: string;
  currentPeriodKey: string | null;
  currentQtyDeviasi: number | null;
  currentNominal: number | null;
  currentHarga: number | null;
  note: string | null;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  eventCount: number;
  lastEventAt: string | null;
}

export interface FollowUpEventDto {
  id: string;
  actor: string;
  fromStatus: string;
  toStatus: string;
  alasan: string | null;
  kategoriTindakan: string | null;
  qtyTemuan: number | null;
  createdAt: string;
}

export interface CreateCaseRequest {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  periodKey: string;
  snapshotId?: string;
  qtyDeviasi?: number | null;
  nominal?: number | null;
  harga?: number | null;
  note?: string;
}

export interface CaseEventRequest {
  toStatus: "PENDING" | "DIPROSES" | "SELESAI" | "DIBATALKAN";
  alasan?: string;
  kategoriTindakan?: string;
  qtyTemuan?: number | null;
}

export const CASE_STATUSES = ["PENDING", "DIPROSES", "SELESAI", "DIBATALKAN"] as const;
export const CASE_STATUS_LABEL: Record<string, string> = {
  PENDING: "Pending",
  DIPROSES: "Diproses",
  SELESAI: "Selesai",
  DIBATALKAN: "Dibatalkan",
};
export const KATEGORI_TINDAKAN = [
  "Stock Opname Ulang",
  "Koreksi Data",
  "Kehilangan",
  "Selisih Fisik Wajar",
  "Menunggu Konfirmasi TL",
  "Lain-lain",
] as const;

export interface OutletPICDto {
  id: string;
  outletCode: string;
  picName: string;
  waNumber: string | null;
  notes: string | null;
}

export interface SettingsDto {
  tanggalHDefault: number;
  ambangAcrDefault: number;
  engineKind: string;
  kategoriBarang4217: string | null;
}

export interface AuditLogDto {
  id: string;
  action: string;
  entity: string;
  entityId: string | null;
  detailJson: string | null;
  actor: string;
  createdAt: string;
}

export interface ApiError {
  error: string;
}
