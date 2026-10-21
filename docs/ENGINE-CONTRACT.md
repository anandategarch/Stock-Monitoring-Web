# Kontrak Engine Service — SM-WEB v1 (contractVersion "1")

> **Sumber kebenaran tunggal** untuk bentuk data yang keluar-masuk antara Next.js dan Engine Service.
> Deliverable Fase 0 (PRD §10). Perubahan kontrak = bump `contractVersion` + changelog.
> Engine produksi (Fase 1+, Python/FastAPI membungkus `src/pipeline/*` v3.9.71 — 0 rewrite) **wajib**
> memancangkan JSON yang identik dengan kontrak ini. Engine demo di sandbox (Bun) mengikuti
> kontrak yang sama 100% dengan `engineKind: "demo"` — data sintetis deterministik,
> **BUKAN** hasil pipeline Accurate asli.

## 1. Transport

| Aspek | Nilai |
|---|---|
| Lokasi (sandbox) | `mini-services/engine/` — proyek Bun independen, port **3030** |
| Penghubung | Hanya **server Next.js** yang memanggil engine (`http://127.0.0.1:3030`). Browser TIDAK PERNAH memanggil engine langsung — semua lewat `/api/*` Next.js (aturan gateway: browser hanya relative path) |
| Produksi | FastAPI co-located (pola mini-service IC/Railway); Next.js tetap satu-satunya penelepon |
| Format | JSON murni; `Content-Type: application/json` |
| State | **Stateless & idempotent** (FR-12): request identik → hasil identik byte-per-byte pada bagian data (boleh beda hanya `durationMs`, `startedAt`, `uptimeSec`) |

## 2. Endpoints

### 2.1 `GET /health` → `EngineHealth`

```ts
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
```

### 2.2 `POST /process`

**Request** (`EngineProcessRequest`):

```ts
export interface EngineProcessRequest {
  periodKey: string;       // "YYYY-MM", wajib, regex ^\d{4}-(0[1-9]|1[0-2])$
  tanggalH: number;        // cut-off H, wajib, integer 1..31 (default dari Setting: 25)
  ambangAcrPct: number;    // ambang ACR %, wajib, integer 1..200 (default 80)
  bundleName?: string;     // label bundle (tampilan saja)
  seed?: number;           // entropi tambahan opsional, default 0
}
```

Validasi gagal → HTTP 422 `{ "error": string }`. Sukses → HTTP 200 `EngineResult`.

**Response** (`EngineResult`) — SEMUA tipe di bawah adalah kontrak final:

```ts
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
```

## 3. Aturan semantik (WAJIB oleh kedua implementasi)

1. **INV-1 missing ≠ 0** — sel tanpa data = `null`, sel bernilai nol sungguhan = `0`.
2. **INV-2 bertanda** — deviasi/selisih minus = kekurangan; tidak boleh di-abs.
3. **INV-3 harga** — `konversiOk=false` atau `hargaEfektif=null` ⇒ `nominal=null` + `alasan` terisi di `prices`.
4. **§82b** — `summary.warningCount` HARUS sama dengan jumlah `logs` ber-level `WARNING`; `errorCount` sama dengan jumlah `ERROR`. Setiap DQ issue WARNING/ERROR wajib punya ≥1 baris log WARNING/ERROR.
5. **Status akhir** — dari DQ: ada ERROR → `SELESAI_PARSIAL`; else ada WARNING → `SELESAI_DENGAN_PERINGATAN`; else `SELESAI`.
6. **Determinisme (FR-12)** — `periodKey` + `tanggalH` + `ambangAcrPct` + `seed` sama ⇒ `rows`, `prices`, `selisihIn`, `po`, `dqIssues` identik. Inilah dasar strategi komit: Next.js **memanggil ulang** `/process` dengan parameter yang sama saat Komit Snapshot — tidak ada state cache antar-request.
7. **Kategori kosong** — direpresentasikan string `"(Tanpa Kategori)"` (jujur, PRD fn_dbs_kategori).
8. Setiap `restoCode` 6 huruf; `day` valid 1..`dayCount`.

## 4. Spesifikasi generator DEMO (sandbox) — deterministik

> Tujuan: menghidupkan seluruh UI sebelum pipeline Python asli terpasang.
> Data **sintetis**; tidak dipakai untuk klaim paritas angka. `engineKind:"demo"` + `parityNote`
> wajib menjelaskan ini di UI. Skala demo: **10 resto × 40 barang × dayCount hari ≈ 12.400 baris**.

- **PRNG**: `mulberry32`, seed = `fnv1a32(periodKey) ^ fnv1a32(tanggalH + "|" + ambangAcrPct + "|" + seed)`. Semua urutan pemanggilan RNG tetap (satu loop besar, tanpa percabangan RNG).
- **Resto tetap (10)**: `CKGPAH` Resto Cikini · `MLGPAR` Resto Malang · `BDGPRM` Resto Bandung · `SBYKTR` Resto Surabaya · `YGYKLM` Resto Yogyakarta · `BNDKRA` Resto Bandara · `SMGPTG` Resto Semarang · `PLMGRL` Resto Palembang · `BKLJUI` Resto Bekasi · `DKJKTA` Resto Jakarta.
- **Barang tetap (40)** lintas kategori (`Bahan Pokok`, `Sembako`, `Minuman`, `Packaging`, `Bumbu & Rempah`, `Frozen`, `Bahan Segar`, `Lain-lain`), satuan GR (`kg`/`ltr`/`dus`) & PCS (`pcs`/`gram`/`bks`/`pak`), termasuk barang spesial:
  - `PROMIX 04` (pcs) — pemicu label CEK "Promix 04";
  - `HM Ayam Racikan` — prefix "HM" pemicu label "Hitung Manual";
  - 4 barang `konversiOk=false` (mis. "Minyak Goreng 2L", "Sirup Melon 1L", "Saus Tomat Kaleng", "Coklat Bubuk 1kg") → masuk daftar **Tanpa Harga** (DQ `TANPA_HARGA` × 4);
  - 2–3 barang "non-aktif" (tidak bergerak sebulan) → label "Kosong/Non Aktif".
- **Profil per pasangan resto×barang**: 85% aktif / 15% dorman (deterministik via RNG). Dorman: semua metrik 0, `cek` memuat "Kosong/Non Aktif".
- **Seri harian aktif**: `saldoAwal(1) ∈ 20..220`; per hari: `in` pengiriman P≈0.35 qty 10..60; `out` penjualan proporsional 0.5–2.0 unit/hari; `bk` transfer keluar P≈0.08; `acr` penyesuaian P≈0.10 qty 1..8; `bm = in ± selisih kecil (P≈0.2, 1..4)`; `selisihIN = bm − in`; `saldoAkhir = saldoAwal + in − out − bk`; `so = saldoAkhir + derau opname`; `deviasi = so − saldoAkhir` (umumnya ±0..3; P≈0.06 lompatan 4..25 — kandidat follow-up); `saldoAwal(d+1) = saldoAkhir(d)`; GR dibulatkan 0.5, PCS integer, lainnya 2 desimal.
- **Missing-null INV-1**: pasangan dengan `(hash % 13) == 0` → `qtySO = null` pada hari 9–11 (bukan nol!).
- **Harga**: per barang sekali per run (500..150.000, kelipatan 50); `nominal = harga × Σ deviasi bulan` per pasangan, null bila konversi gagal/deviasi 0.
- **Label CEK**: "RI Balancing" P≈0.02/hari aktif; "Beda Tanggal" P≈0.03; "Turun Drastis" bila |deviasi hari| ≥ 20; "ACR to BOM" dihitung per pasangan: |Σ deviasi| > (ambang/100) × Σ acr (SAAT RUN); "Selisih IN" bila |Σ selisihIN pasangan| ≥ 8; "PO Menunggu" bila ada PO resto-berang dengan item "menunggu diproses". **Jaminan cakupan**: setiap label wajib muncul ≥1× — injeksi deterministik: pasangan ke-`((fnv1a32(periodKey)+k) mod jumlahPasanganAktif)` diberi label k pada hari-H.
- **Catatan Audit** B1–B4: P≈0.04 per pasangan (maks 1).
- **Selisih IN per resto**: agregat bulanan dari rows + `hasilAudit` + `skorResto = itemBerselisih + tanggalTerdampak`.
- **PO**: 1–3 per resto (≈16 total), 2–6 item/PO dari barang aktif resto tsb; mayoritas item "menunggu diproses" (paritas 32.43), `annotasi = "↳ " + statusPesanan`.
- **DQ demo (≈15)**: 1 `SKIP_FILE` (folder `Terima4215` — jujur meniru gap desktop v3.9.71: ada di config, tak pernah dibaca), 2 `SCHEMA_WARNING`, 1 `FALLBACK_BIND_9901`, 2 `VALUE_MISSING`, 1 `TANGGAL_MISSING`, 4 `KONVERSI_GAGAL`↔Tanpa Harga, 1 `KATEGORI_KOSONG`, 2 `DUPLIKAT_BARIS`, 1 `PREFLIGHT_FOLDER` (INFO), 4 `TANPA_HARGA` (INFO). Severity: semua WARNING kecuali PREFLIGHT_FOLDER & TANPA_HARGA = INFO → status akhir `SELESAI_DENGAN_PERINGATAN`.
- **sourceFiles (14)**: 15 folder config.json minus duplikat Lalu (RekapBerjalan, RekapLalu, Penjualan2205, Kirim4215, Terima4215→SKIP, RI3224, RI3224Lalu, SaldoAwal4217, DBSKategori, Pemindahan4205, Pemindahan4205Lalu, RincianPO, Data9901, Harga) — `rowCount`/`sizeBytes` realistis, `Terima4215` status `SKIP` rowCount 0.
- **logs**: INFO per modul pembaca (10) + append1 + konversi + nominal + PO + audit, plus 1 baris WARNING/ERROR per DQ issue non-INFO, plus baris pembuka/penutup; akhiri `SELESAI ... (N baris log)`.

## 5. Produksi (Fase 1) — ✅ TERPASANG di sandbox (Task 43)

1. ~~Deploy FastAPI yang membungkus `src/pipeline/*`~~ **SELESAI 2026-10-21**: `mini-services/engine-fastapi/`
   (port **3031**, `bun run dev` → uvicorn --reload) membungkus `src/` v3.9.71 `f22bca6` APA ADANYA
   (0-rewrite — FR-10). Pemetaan `DataFrame → EngineResult` di `mapper.py`; label CEK (7 kondisi port
   `deviasi_view` v3.9.27/71), `6.PEMAKAIAN (COM)` (port `pivot_view._compute_com` v3.9.5), catatan
   audit B1–B4 (port `in_selisih_view` v3.9.23) & SKOR RESTO (v3.9.55) dipindah VERBATIM; helper harga
   `nominal_common.lookup_harga_pair` + `doc_codes` disalin utuh ke `ports/` (impor bersih, tanpa Tkinter).
2. **Ekstensi request produksi**: `EngineProcessRequest` + `bundlePath?` — path server ke bundle yang
   diekstrak Next.js dari unggahan ZIP (`/api/ingest/upload`, FR-1); tanpa `bundlePath` → 422. Semua
   tipe respons TIDAK berubah (`contractVersion` tetap "1"; engine demo mengabaikan field tambahan).
3. Next.js memilih engine per-run: `bundleId` ada → `SM_ENGINE_PROD_URL` (default `http://127.0.0.1:3031`);
   tanpa → `SM_ENGINE_URL` (demo `:3030`). Komit menyimpan **bundleId** (bukan path) di `paramsJson`
   supaya re-run idempotent (FR-12) tetap sahih walau direktori dipindah.
4. **Gerbang AC-B LULUS 65/65** (`bun run golden`): fixture bundle = port verbatim `create_mock_*`
   `test_mock.py` desktop → (a) pipeline vendored ≡ asersi test_mock (resto MLGPAR, running stock
   [0,0,120,150,190], 4205-lalu −28, sumber '42.05 (Bulan Lalu)', JENIS 9 kanonik, SOURCE DATA
   'input so harian', PO Menunggu ×3); (b) `/process` ≡ pipeline langsung sel-per-sel (94 baris,
   termasuk pasangan saldo-only BUMBU PASTA KUAH dev −84 & normalisasi harga GULA 18,25/GR→18.250/KG);
   (c) §82b + status + determinisme 2×.
5. Golden-file vs bundle REAL (§11.2) menunggu bundle export aktual pemilik produk — engine demo TIDAK
   dilibatkan; harness `golden_check.py` tinggal diarahkan ke bundle tersebut.
