/**
 * generator.ts — Generator data DEMO deterministik (spesifikasi kontrak §4, ENGINE-CONTRACT.md).
 *
 * Seluruh angka dihasilkan dari PRNG mulberry32 dengan seed:
 *   fnv1a32(periodKey) ^ fnv1a32("tanggalH|ambangAcrPct|seed")
 * Urutan tarikan RNG selalu tetap dan stabil posisi (jumlah tarikan per posisi
 * tidak bergantung pada hasil), sehingga request identik menghasilkan
 * rows/prices/selisihIn/po/dqIssues/logs identik (FR-12 determinisme; boleh beda
 * hanya startedAt & durationMs). Data ini SINTETIS — bukan hasil pipeline Accurate asli.
 */
import type {
  AuditNote,
  CekLabel,
  EngineDqIssue,
  EngineLogLine,
  EnginePo,
  EnginePoItem,
  EnginePrice,
  EngineResult,
  EngineRow,
  EngineSelisihInResto,
  EngineSourceFile,
  EngineSummary,
  RunStatus,
} from "./types";
import type { NormalizedEngineParams } from "./validation";

// =====================================================================
// Konstanta identitas engine
// =====================================================================
const ENGINE_NAME = "SM-DEMO-Engine";
const ENGINE_VERSION = "0.1.0";
const DEFINITION_VERSION = "3.9.71-noSI";

/** 9 label CEK kanonik — urutan ini juga dipakai untuk urutan array `cek` & injeksi cakupan. */
const CEK_CANON: readonly CekLabel[] = [
  "RI Balancing",
  "Beda Tanggal",
  "Promix 04",
  "Kosong/Non Aktif",
  "Hitung Manual",
  "Turun Drastis",
  "ACR to BOM",
  "PO Menunggu",
  "Selisih IN",
];

const AUDIT_NOTES: readonly AuditNote[] = ["B1", "B2", "B3", "B4"];

/** Kategori kosong direpresentasi string ini (kontrak §3.7 — jujur, bukan error). */
const KATEGORI_KOSONG = "(Tanpa Kategori)";

/** Alasan konversi gagal pada barang Tanpa Harga (kontrak §3.3 INV-3). */
const ALASAN_TANPA_HARGA = "Tanpa Harga — tidak ditemukan harga 41.09 yang cocok untuk barang ini";

/** Jumlah hari per bulan — Februari selalu 28 (tanpa penanganan tahun kabisat, sesuai kontrak). */
const DAYS_IN_MONTH: readonly number[] = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

// =====================================================================
// Master tetap demo (kontrak §4) — 10 resto × 40 barang
// =====================================================================
const RESTOS: readonly { code: string; name: string }[] = [
  { code: "CKGPAH", name: "Resto Cikini" },
  { code: "MLGPAR", name: "Resto Malang" },
  { code: "BDGPRM", name: "Resto Bandung" },
  { code: "SBYKTR", name: "Resto Surabaya" },
  { code: "YGYKLM", name: "Resto Yogyakarta" },
  { code: "BNDKRA", name: "Resto Bandara" },
  { code: "SMGPTG", name: "Resto Semarang" },
  { code: "PLMGRL", name: "Resto Palembang" },
  { code: "BKLJUI", name: "Resto Bekasi" },
  { code: "DKJKTA", name: "Resto Jakarta" },
];

interface DemoItem {
  name: string;
  satuan: string;        // GR: kg/ltr/dus · PCS: pcs/gram/bks/pak
  kategori: string;      // "" = kosong → baris memakai "(Tanpa Kategori)"
  isGR: boolean;
  tanpaHarga: boolean;   // true → konversiOk=false, masuk daftar Tanpa Harga
  nonAktif: boolean;     // true → tidak bergerak sebulan (dorman di semua resto)
}

const ITEMS: readonly DemoItem[] = [
  // Bahan Pokok
  { name: "Beras Pandan Wangi",     satuan: "kg",   kategori: "Bahan Pokok",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Tepung Terigu Serbaguna", satuan: "kg",  kategori: "Bahan Pokok",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Gula Pasir Premium",     satuan: "kg",   kategori: "Bahan Pokok",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Minyak Goreng 2L",       satuan: "ltr",  kategori: "Bahan Pokok",    isGR: true,  tanpaHarga: true,  nonAktif: false },
  { name: "PROMIX 04",              satuan: "pcs",  kategori: "Bahan Pokok",    isGR: false, tanpaHarga: false, nonAktif: false },
  // Sembako
  { name: "Mie Telur Spesial",      satuan: "dus",  kategori: "Sembako",        isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Telur Ayam Negeri",      satuan: "kg",   kategori: "Sembako",        isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Susu Kental Manis",      satuan: "dus",  kategori: "Sembako",        isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Saus Tomat Kaleng",      satuan: "pcs",  kategori: "Sembako",        isGR: false, tanpaHarga: true,  nonAktif: false },
  { name: "Kopi Bubuk Arabika",     satuan: "kg",   kategori: "Sembako",        isGR: true,  tanpaHarga: false, nonAktif: false },
  // Minuman
  { name: "Sirup Melon 1L",         satuan: "ltr",  kategori: "Minuman",        isGR: true,  tanpaHarga: true,  nonAktif: false },
  { name: "Teh Tubruk Melati",      satuan: "kg",   kategori: "Minuman",        isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Air Mineral 600ml",      satuan: "dus",  kategori: "Minuman",        isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Coklat Bubuk 1kg",       satuan: "kg",   kategori: "Minuman",        isGR: true,  tanpaHarga: true,  nonAktif: false },
  { name: "Susu UHT Coklat 250ml",  satuan: "dus",  kategori: "Minuman",        isGR: true,  tanpaHarga: false, nonAktif: false },
  // Packaging
  { name: "Kantong Kresek 1/4 Kg",  satuan: "pak",  kategori: "Packaging",      isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Kardus Bekas 50x40",     satuan: "pcs",  kategori: "Packaging",      isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Paper Bag Medium",       satuan: "pak",  kategori: "Packaging",      isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Cup 16oz",               satuan: "bks",  kategori: "Packaging",      isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Sedotan Hitam 8mm",      satuan: "pak",  kategori: "Packaging",      isGR: false, tanpaHarga: false, nonAktif: false },
  // Bumbu & Rempah
  { name: "Bawang Putih Tunggal",   satuan: "kg",   kategori: "Bumbu & Rempah", isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Cabai Merah Keriting",   satuan: "kg",   kategori: "Bumbu & Rempah", isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Kecap Manis Refill 1L",  satuan: "ltr",  kategori: "Bumbu & Rempah", isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Royco Ayam 500gr",       satuan: "pcs",  kategori: "Bumbu & Rempah", isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Merica Bubuk 100gr",     satuan: "gram", kategori: "Bumbu & Rempah", isGR: false, tanpaHarga: false, nonAktif: false },
  // Frozen
  { name: "Kentang Goreng 5mm",     satuan: "kg",   kategori: "Frozen",         isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Sosis Ayam 500gr",       satuan: "kg",   kategori: "Frozen",         isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Nugget Ayam 1kg",        satuan: "kg",   kategori: "Frozen",         isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Pangsit Beku 500gr",     satuan: "gram", kategori: "Frozen",         isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Udang Beku Vaname",      satuan: "kg",   kategori: "Frozen",         isGR: true,  tanpaHarga: false, nonAktif: false },
  // Bahan Segar
  { name: "Ayam Broiler Utuh",      satuan: "kg",   kategori: "Bahan Segar",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "HM Ayam Racikan",        satuan: "kg",   kategori: "Bahan Segar",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Ikan Nila Segar",        satuan: "kg",   kategori: "Bahan Segar",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Sayur Campur Halus",     satuan: "kg",   kategori: "Bahan Segar",    isGR: true,  tanpaHarga: false, nonAktif: false },
  { name: "Tomat Merah Segar",      satuan: "kg",   kategori: "Bahan Segar",    isGR: true,  tanpaHarga: false, nonAktif: false },
  // Lain-lain
  { name: "Gas LPG 3kg",            satuan: "pcs",  kategori: "Lain-lain",      isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Sarung Tangan Vinyl",    satuan: "pak",  kategori: "",               isGR: false, tanpaHarga: false, nonAktif: false },
  { name: "Keripik Pisang Original", satuan: "pcs", kategori: "Lain-lain",      isGR: false, tanpaHarga: false, nonAktif: true },
  { name: "Sumping Vanila Coklat",  satuan: "pcs",  kategori: "Lain-lain",      isGR: false, tanpaHarga: false, nonAktif: true },
  { name: "Bumbu Racik Lama 90gr",  satuan: "gram", kategori: "Lain-lain",      isGR: false, tanpaHarga: false, nonAktif: true },
];

const SUPPLIERS: readonly string[] = [
  "PT Sumber Pangan Nusantara",
  "CV Mitra Boga Sejahtera",
  "PT Freshindo Sentosa",
  "CV Agro Makmur Jaya",
  "PT Tirta Bumi Perkasa",
  "CV Sinar Frozen Pratama",
];

/** 14 folder config.json yang terbaca pipeline desktop (Terima4215 → SKIP, rowCount 0). */
interface FileSpec {
  folderKey: string;
  filePrefix: string;
  sheetName: string | null;
  rowCount: number;
  sizeBytes: number;
  status: "OK" | "SKIP" | "WARNING";
}

const FILE_SPECS: readonly FileSpec[] = [
  { folderKey: "RekapBerjalan",       filePrefix: "RekapBerjalan",     sheetName: "Rekap",        rowCount: 1284, sizeBytes: 348160,  status: "OK" },
  { folderKey: "RekapLalu",          filePrefix: "RekapLalu",        sheetName: "Rekap",        rowCount: 1102, sizeBytes: 301056,  status: "OK" },
  { folderKey: "Penjualan2205",      filePrefix: "Penjualan_2205",   sheetName: "22.05",        rowCount: 4512, sizeBytes: 1204224, status: "OK" },
  { folderKey: "Kirim4215",          filePrefix: "Kirim_4215",       sheetName: "Sheet1",       rowCount: 2377, sizeBytes: 633864,  status: "OK" },
  { folderKey: "Terima4215",         filePrefix: "Terima_4215",      sheetName: "Sheet1",       rowCount: 0,    sizeBytes: 189440,  status: "SKIP" },
  { folderKey: "RI3224",             filePrefix: "RI_3224",          sheetName: "RI",           rowCount: 2140, sizeBytes: 572416,  status: "OK" },
  { folderKey: "RI3224Lalu",         filePrefix: "RI_3224_Lalu",     sheetName: "RI",           rowCount: 1705, sizeBytes: 456704,  status: "WARNING" },
  { folderKey: "SaldoAwal4217",      filePrefix: "SaldoAwal_4217",  sheetName: "DATA",         rowCount: 412,  sizeBytes: 118784,  status: "WARNING" },
  { folderKey: "DBSKategori",        filePrefix: "DBS_Kategori",     sheetName: "DBS-Kategori", rowCount: 268,  sizeBytes: 87040,   status: "OK" },
  { folderKey: "Pemindahan4205",     filePrefix: "Pemindahan_4205",  sheetName: "Sheet1",       rowCount: 1288, sizeBytes: 345088,  status: "OK" },
  { folderKey: "Pemindahan4205Lalu", filePrefix: "Pemindahan_4205_Lalu", sheetName: "Sheet1",   rowCount: 700,  sizeBytes: 190464,  status: "OK" },
  { folderKey: "RincianPO",          filePrefix: "RincianPO",        sheetName: "32.43",        rowCount: 356,  sizeBytes: 156672,  status: "OK" },
  { folderKey: "Data9901",           filePrefix: "Data9901",         sheetName: "9901",         rowCount: 47,   sizeBytes: 24576,   status: "OK" },
  { folderKey: "Harga",              filePrefix: "Harga_4109",       sheetName: "41.09",        rowCount: 352,  sizeBytes: 96256,   status: "OK" },
];

// =====================================================================
// PRNG deterministik
// =====================================================================

/** FNV-1a 32-bit — basis seed & hash pasangan (stabil lintas platform). */
function fnv1a32(text: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/** mulberry32 — PRNG standar, hasil [0, 1). */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return (): number => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// =====================================================================
// Helper
// =====================================================================

/** Bandingkan string kode-unit (deterministik & sama dengan sort_by jq). */
function cmpText(a: string, b: string): number {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

/** Pembulatan satuan: GR (kg/ltr/dus) ke kelipatan 0,5; PCS (pcs/gram/bks/pak) ke bilangan bulat. */
function roundStep(value: number, isGR: boolean): number {
  return isGR ? Math.round(value * 2) / 2 : Math.round(value);
}

/** Label CEK yang melekat pada barang (sifat item, bukan aktivitas harian). */
function itemLabels(item: DemoItem): CekLabel[] {
  const labels: CekLabel[] = [];
  if (item.name === "PROMIX 04") labels.push("Promix 04");
  if (item.name.startsWith("HM")) labels.push("Hitung Manual");
  return labels;
}

/** Status pesanan dominan (paritas status pesanan 32.43) — tie-break pakai prioritas Accurate. */
function dominantStatus(items: EnginePoItem[]): string {
  const priority = ["menunggu diproses", "diproses", "selesai", "batal"];
  let best = priority[priority.length - 1];
  let bestCount = -1;
  for (const status of priority) {
    const count = items.filter((it) => it.status === status).length;
    if (count > bestCount) {
      best = status;
      bestCount = count;
    }
  }
  return best;
}

// =====================================================================
// Struktur kerja internal
// =====================================================================

/** EngineRow dengan `cek` diganti Set agar penambahan label bebas duplikat & deterministik. */
type WorkingRow = Omit<EngineRow, "cek"> & { cekSet: Set<CekLabel> };

interface PairState {
  restoCode: string;
  restoName: string;
  item: DemoItem;
  konversiOk: boolean;
  dormant: boolean;
  rows: WorkingRow[];
  sumDeviasi: number;
  sumAcr: number;
  sumSelisihIN: number;
}

// =====================================================================
// Generator utama
// =====================================================================

export function generateDemoResult(params: NormalizedEngineParams): EngineResult {
  const startedAtDate = new Date();
  const t0 = performance.now();

  const month = Number(params.periodKey.slice(5, 7));
  const year = Number(params.periodKey.slice(0, 4));
  const yy = params.periodKey.slice(2, 4);
  const mm = params.periodKey.slice(5, 7);
  const dayCount = DAYS_IN_MONTH[month - 1];

  const rng = mulberry32(
    (fnv1a32(params.periodKey) ^ fnv1a32(`${params.tanggalH}|${params.ambangAcrPct}|${params.seed}`)) >>> 0,
  );

  // -------------------------------------------------------------------
  // 1) Harga per barang — sekali per run: 500..150.000, kelipatan 50
  // -------------------------------------------------------------------
  const hargaItem: number[] = ITEMS.map(() => 500 + 50 * Math.floor(rng() * 2991));

  // -------------------------------------------------------------------
  // 2) Satu loop besar resto × barang × hari — profil pasangan + seri harian.
  //    Jumlah tarikan RNG per posisi SELALU tetap (4 per pasangan + 16 per
  //    pasangan-hari), hasil pasangan dorman diabaikan begitu saja → aliran
  //    RNG stabil posisi dan output deterministik.
  // -------------------------------------------------------------------
  const pairs: PairState[] = [];

  for (const resto of RESTOS) {
    for (let itemIdx = 0; itemIdx < ITEMS.length; itemIdx++) {
      const item = ITEMS[itemIdx];
      const konversiOk = !item.tanpaHarga;
      const hargaEfektif = konversiOk ? hargaItem[itemIdx] : null;
      const kategoriTampil = item.kategori === "" ? KATEGORI_KOSONG : item.kategori;

      // Profil pasangan: dorman 15% (barang non-aktif dipaksa dorman di semua resto)
      const rDormant = rng();
      const rNoteHas = rng();
      const rNoteWhich = rng();
      const rSaldoAwal = rng();
      const dormant = item.nonAktif || rDormant >= 0.85;
      const auditNote = rNoteHas < 0.04 ? AUDIT_NOTES[Math.floor(rNoteWhich * 4)] : null;

      // INV-1: pasangan dengan hash % 13 == 0 tidak punya data SO pada hari 9..11 (null, BUKAN nol)
      const soMissing = fnv1a32(`${resto.code}|${item.name}`) % 13 === 0;

      const pair: PairState = {
        restoCode: resto.code,
        restoName: resto.name,
        item,
        konversiOk,
        dormant,
        rows: [],
        sumDeviasi: 0,
        sumAcr: 0,
        sumSelisihIN: 0,
      };

      let saldoAwal = roundStep(20 + Math.floor(rSaldoAwal * 201), item.isGR); // saldo awal(1): 20..220

      for (let day = 1; day <= dayCount; day++) {
        // --- 16 tarikan RNG per (pasangan, hari) — selalu ditarik, urutan tetap ---
        const rIn = rng();
        const qInR = rng();
        const qOutR = rng();
        const rBk = rng();
        const qBkR = rng();
        const rAcr = rng();
        const qAcrR = rng();
        const rDiff = rng();
        const qDiffR = rng();
        const sDiff = rng();
        const rJump = rng();
        const qDerauR = rng();
        const qJumpR = rng();
        const sDerau = rng();
        const rRi = rng();
        const rBt = rng();

        if (dormant) {
          // Pasangan dorman: semua metrik 0 (kecuali SO/deviasi null pada hari tanpa data INV-1)
          const soDormant = soMissing && day >= 9 && day <= 11 ? null : 0;
          pair.rows.push({
            restoCode: resto.code,
            restoName: resto.name,
            itemName: item.name,
            satuan: item.satuan,
            kategori: kategoriTampil,
            isGR: item.isGR,
            day,
            qtySaldoAwal: 0,
            qtySO: soDormant,
            qtySaldoAkhir: 0,
            qtyDeviasi: soDormant === null ? null : 0,
            qtyIN: 0,
            qtyBarangMasuk: 0,
            qtyCOM: 0,
            qtySelisihIN: 0,
            qtyBarangKeluar: 0,
            qtyACR: 0,
            hargaEfektif,
            konversiOk,
            nominal: null, // deviasi 0 ⇒ nominal null (kontrak §4 — harga × deviasi)
            cekSet: new Set<CekLabel>(["Kosong/Non Aktif", ...itemLabels(item)]),
            auditNote,
          });
          continue;
        }

        // --- seri harian aktif ---
        const qtyIn = rIn < 0.35 ? 10 + Math.floor(qInR * 51) : 0;               // pengiriman P 0.35, qty 10..60
        const qtyOut = roundStep(0.5 + qOutR * 1.5, item.isGR);                  // penjualan 0.5..2.0 unit/hari
        const qtyBk = rBk < 0.08 ? 1 + Math.floor(qBkR * 10) : 0;                 // transfer keluar P 0.08
        const qtyAcr = rAcr < 0.1 ? 1 + Math.floor(qAcrR * 8) : 0;                // penyesuaian P 0.10, qty 1..8
        const diff = rDiff < 0.2 ? (sDiff < 0.5 ? -1 : 1) * (1 + Math.floor(qDiffR * 4)) : 0; // selisih kecil ±1..4
        const qtyBm = Math.max(0, qtyIn + diff);                                 // BM = IN ± selisih kecil (tak boleh negatif)
        const selisihIN = roundStep(qtyBm - qtyIn, item.isGR);                   // BM − IN, bertanda
        const derau = rJump < 0.06
          ? (sDerau < 0.5 ? -1 : 1) * (4 + Math.floor(qJumpR * 22))              // lompatan opname 4..25 (P 0.06)
          : (sDerau < 0.5 ? -1 : 1) * Math.floor(qDerauR * 4);                   // derau opname biasa ±0..3

        const saldoAkhir = Math.max(0, roundStep(saldoAwal + qtyIn - qtyOut - qtyBk, item.isGR));
        const qtySO = soMissing && day >= 9 && day <= 11
          ? null
          : Math.max(0, roundStep(saldoAkhir + derau, item.isGR));
        const deviasi = qtySO === null ? null : roundStep(qtySO - saldoAkhir, item.isGR); // bertanda (INV-2)

        const cekSet = new Set<CekLabel>(itemLabels(item));
        if (rRi < 0.02) cekSet.add("RI Balancing");
        if (rBt < 0.03) cekSet.add("Beda Tanggal");
        if (deviasi !== null && Math.abs(deviasi) >= 20) cekSet.add("Turun Drastis");

        pair.rows.push({
          restoCode: resto.code,
          restoName: resto.name,
          itemName: item.name,
          satuan: item.satuan,
          kategori: kategoriTampil,
          isGR: item.isGR,
          day,
          qtySaldoAwal: saldoAwal,
          qtySO,
          qtySaldoAkhir: saldoAkhir,
          qtyDeviasi: deviasi,
          qtyIN: qtyIn,
          qtyBarangMasuk: qtyBm,
          qtyCOM: qtyOut,
          qtySelisihIN: selisihIN,
          qtyBarangKeluar: qtyBk,
          qtyACR: qtyAcr,
          hargaEfektif,
          konversiOk,
          nominal: konversiOk && hargaEfektif !== null && deviasi !== null && deviasi !== 0
            ? Math.round(hargaEfektif * deviasi * 100) / 100 // harga × deviasi (kontrak §4); null bila konversi gagal / deviasi 0 (INV-3)
            : null,
          cekSet,
          auditNote,
        });

        pair.sumDeviasi += deviasi ?? 0;
        pair.sumAcr += qtyAcr;
        pair.sumSelisihIN += selisihIN;
        saldoAwal = saldoAkhir; // saldo awal hari berikutnya = saldo akhir hari ini
      }

      pairs.push(pair);
    }
  }

  // -------------------------------------------------------------------
  // 3) Label per pasangan (butuh agregat bulanan) — dipasang ke semua baris pasangan
  // -------------------------------------------------------------------
  for (const pair of pairs) {
    if (pair.dormant) continue;
    if (Math.abs(pair.sumDeviasi) > (params.ambangAcrPct / 100) * pair.sumAcr) {
      for (const row of pair.rows) row.cekSet.add("ACR to BOM"); // dihitung SAAT RUN dengan ambang request (FR-30)
    }
    if (Math.abs(pair.sumSelisihIN) >= 8) {
      for (const row of pair.rows) row.cekSet.add("Selisih IN");
    }
  }

  // -------------------------------------------------------------------
  // 4) PO per resto — 1..3 PO (≈16 total), 2..6 item dari barang AKTIF resto,
  //    mayoritas item "menunggu diproses" (paritas status pesanan 32.43)
  // -------------------------------------------------------------------
  const pairAt = (restoIdx: number, itemIdx: number): PairState => pairs[restoIdx * ITEMS.length + itemIdx];
  const poMenungguKeys = new Set<string>();
  const poList: EnginePo[] = [];
  let poCounter = 0;

  for (let restoIdx = 0; restoIdx < RESTOS.length; restoIdx++) {
    const resto = RESTOS[restoIdx];
    const poolAktif: number[] = [];
    for (let i = 0; i < ITEMS.length; i++) {
      if (!pairAt(restoIdx, i).dormant) poolAktif.push(i);
    }

    const rC1 = rng();
    const rC2 = rng();
    const nPo = 1 + (rC1 < 0.55 ? 1 : 0) + (rC2 < 0.1 ? 1 : 0); // 1..3 PO per resto, E ≈ 1,65 → total ≈ 16
    for (let p = 0; p < nPo; p++) {
      const rDay = rng();
      const rSupplier = rng();
      const rNItem = rng();
      const pool = poolAktif.slice();
      const nItem = Math.min(2 + Math.floor(rNItem * 5), pool.length); // 2..6 item unik
      for (let k = 0; k < nItem; k++) {
        const rJ = rng();
        const j = k + Math.floor(rJ * (pool.length - k)); // Fisher-Yates parsial → item unik deterministik
        const tmp = pool[k];
        pool[k] = pool[j];
        pool[j] = tmp;
      }

      const poItems: EnginePoItem[] = [];
      for (let k = 0; k < nItem; k++) {
        const itemIdx = pool[k];
        const rQty = rng();
        const rStatus = rng();
        const rPartial = rng();
        const status =
          rStatus < 0.55 ? "menunggu diproses"
          : rStatus < 0.75 ? "diproses"
          : rStatus < 0.9 ? "selesai"
          : "batal";
        if (status === "menunggu diproses") poMenungguKeys.add(`${resto.code}|${ITEMS[itemIdx].name}`);
        poItems.push({
          itemName: ITEMS[itemIdx].name,
          qty: 5 + Math.floor(rQty * 96),
          satuan: ITEMS[itemIdx].satuan,
          status,
          diterimaSebagian: status === "diproses" && rPartial < 0.5,
        });
      }

      poCounter += 1;
      const statusPesanan = dominantStatus(poItems);
      const poStatus = poItems.some((it) => it.status === "menunggu diproses")
        ? "Menunggu"
        : poItems.some((it) => it.status === "diproses")
          ? "Diproses"
          : "Selesai";

      poList.push({
        cabang: resto.code,
        restoName: resto.name,
        poNumber: `PO-${yy}${mm}-${String(poCounter).padStart(4, "0")}`,
        tanggal: `${params.periodKey}-${String(1 + Math.floor(rDay * dayCount)).padStart(2, "0")}`,
        supplier: SUPPLIERS[Math.floor(rSupplier * SUPPLIERS.length)],
        itemCount: poItems.length,
        status: poStatus,
        statusPesanan,
        annotasi: `↳ ${statusPesanan}`,
        items: poItems,
      });
    }
  }
  poList.sort((a, b) => cmpText(a.cabang, b.cabang) || cmpText(a.poNumber, b.poNumber));

  // Label "PO Menunggu" untuk semua baris pasangan yang punya item PO menunggu
  for (const pair of pairs) {
    if (poMenungguKeys.has(`${pair.restoCode}|${pair.item.name}`)) {
      for (const row of pair.rows) row.cekSet.add("PO Menunggu");
    }
  }

  // -------------------------------------------------------------------
  // 5) Injeksi cakupan label (jaminan 9 label CEK masing-masing ≥1×):
  //    pasangan aktif ke-((fnv1a32(periodKey)+k) mod N) diberi label k pada hari H
  // -------------------------------------------------------------------
  const activePairs = pairs
    .filter((p) => !p.dormant)
    .sort((a, b) => cmpText(a.restoCode, b.restoCode) || cmpText(a.item.name, b.item.name));
  const injectBase = fnv1a32(params.periodKey);
  const dayH = Math.min(params.tanggalH, dayCount); // tanggal H bisa melewati dayCount (mis. H=31 di Feb) → jepit ke hari terakhir
  for (let k = 0; k < CEK_CANON.length; k++) {
    const target = activePairs[(injectBase + k) % activePairs.length];
    target.rows[dayH - 1].cekSet.add(CEK_CANON[k]);
  }

  // -------------------------------------------------------------------
  // 6) Rakit rows final — terurut restoCode → itemName → day
  // -------------------------------------------------------------------
  const rows: EngineRow[] = [];
  for (const pair of pairs) {
    for (const r of pair.rows) {
      rows.push({
        restoCode: r.restoCode,
        restoName: r.restoName,
        itemName: r.itemName,
        satuan: r.satuan,
        kategori: r.kategori,
        isGR: r.isGR,
        day: r.day,
        qtySaldoAwal: r.qtySaldoAwal,
        qtySO: r.qtySO,
        qtySaldoAkhir: r.qtySaldoAkhir,
        qtyDeviasi: r.qtyDeviasi,
        qtyIN: r.qtyIN,
        qtyBarangMasuk: r.qtyBarangMasuk,
        qtyCOM: r.qtyCOM,
        qtySelisihIN: r.qtySelisihIN,
        qtyBarangKeluar: r.qtyBarangKeluar,
        qtyACR: r.qtyACR,
        hargaEfektif: r.hargaEfektif,
        konversiOk: r.konversiOk,
        nominal: r.nominal,
        cek: CEK_CANON.filter((label) => r.cekSet.has(label)),
        auditNote: r.auditNote,
      });
    }
  }
  rows.sort((a, b) => cmpText(a.restoCode, b.restoCode) || cmpText(a.itemName, b.itemName) || a.day - b.day);

  let nominalTotal = 0;
  let deviasiQtyTotal = 0;
  let nominalRowCount = 0;
  for (const r of rows) {
    if (r.nominal !== null) {
      nominalTotal += r.nominal;
      nominalRowCount += 1;
    }
    if (r.qtyDeviasi !== null) deviasiQtyTotal += r.qtyDeviasi;
  }
  nominalTotal = Math.round(nominalTotal * 100) / 100;
  deviasiQtyTotal = Math.round(deviasiQtyTotal * 100) / 100;

  // -------------------------------------------------------------------
  // 7) Harga (satu per itemName) — INV-3: konversiOk=false ⇒ harga null + alasan
  // -------------------------------------------------------------------
  const prices: EnginePrice[] = ITEMS.map((item, i) => ({
    itemName: item.name,
    satuan: item.satuan,
    harga: item.tanpaHarga ? null : hargaItem[i],
    rasioKonversi: item.tanpaHarga ? null : 1,
    konversiOk: !item.tanpaHarga,
    alasan: item.tanpaHarga ? ALASAN_TANPA_HARGA : null,
  })).sort((a, b) => cmpText(a.itemName, b.itemName));

  // -------------------------------------------------------------------
  // 8) Rekap selisih IN per resto — agregat bulanan dari rows
  //    (itemBerselisih memakai ambang label "Selisih IN": |Σ selisihIN| ≥ 8;
  //     tanggalTerdampak = hari unik berselisihIN ≠ 0 pada pasangan yang ditandai)
  // -------------------------------------------------------------------
  const selisihIn: EngineSelisihInResto[] = RESTOS.map((resto) => {
    let inAccurate = 0;
    let barangMasuk = 0;
    let itemBerselisih = 0;
    const hariTerdampak = new Set<number>();
    for (const pair of pairs) {
      if (pair.restoCode !== resto.code) continue;
      for (const r of pair.rows) {
        inAccurate += r.qtyIN ?? 0;
        barangMasuk += r.qtyBarangMasuk ?? 0;
      }
      if (Math.abs(pair.sumSelisihIN) >= 8) {
        itemBerselisih += 1;
        for (const r of pair.rows) {
          if (r.qtySelisihIN !== null && r.qtySelisihIN !== 0) hariTerdampak.add(r.day);
        }
      }
    }
    const selisih = Math.round((barangMasuk - inAccurate) * 100) / 100;
    return {
      restoCode: resto.code,
      restoName: resto.name,
      inAccurate,
      barangMasuk,
      selisih,
      hasilAudit: selisih === 0 ? ("OK" as const) : ("SELISIH" as const),
      skorResto: itemBerselisih + hariTerdampak.size,
      itemBerselisih,
      tanggalTerdampak: hariTerdampak.size,
    };
  });
  selisihIn.sort((a, b) => cmpText(a.restoCode, b.restoCode));

  // -------------------------------------------------------------------
  // 9) sourceFiles (14) — manifest folder config.json (Terima4215 SKIP, rowCount 0)
  // -------------------------------------------------------------------
  const sourceFiles: EngineSourceFile[] = FILE_SPECS.map((spec) => ({
    folderKey: spec.folderKey,
    fileName: `${spec.filePrefix}_${yy}${mm}.xlsx`,
    sheetName: spec.sheetName,
    rowCount: spec.rowCount,
    sizeBytes: spec.sizeBytes,
    status: spec.status,
  }));

  // -------------------------------------------------------------------
  // 10) DQ issues (19) — 14 WARNING + 5 INFO → status akhir SELESAI_DENGAN_PERINGATAN
  // -------------------------------------------------------------------
  const tanpaHargaNames = ITEMS.filter((it) => it.tanpaHarga).map((it) => it.name);
  const dqIssues: EngineDqIssue[] = [
    { severity: "WARNING", code: "SKIP_FILE", message: "Folder 'Terima4215' ada di config.json tetapi tidak pernah dibaca pipeline (paritas desktop v3.9.71) — file dilewati", source: "Terima4215", sheet: "Sheet1", rawValue: null, rowNumber: null },
    { severity: "WARNING", code: "SCHEMA_WARNING", message: "Skema lembar 'DATA' folder SaldoAwal4217 berubah: kolom 'SALDO AWAL' kini 'SALDO AWAL (KG)' — pembacaan memakai posisi kolom", source: "SaldoAwal4217", sheet: "DATA", rawValue: "SALDO AWAL (KG)", rowNumber: 1 },
    { severity: "WARNING", code: "SCHEMA_WARNING", message: "Skema lembar 'Rekap' folder RI3224Lalu berubah: kolom 'QTY' hilang — fallback ke posisi kolom ke-7", source: "RI3224Lalu", sheet: "Rekap", rawValue: "QTY", rowNumber: 1 },
    { severity: "WARNING", code: "FALLBACK_BIND_9901", message: "Folder Data9901 tanpa kolom bind kantor — dipakai fallback bind 9901 default (cabang DKJKTA)", source: "Data9901", sheet: "9901", rawValue: null, rowNumber: 1 },
    { severity: "WARNING", code: "VALUE_MISSING", message: "Nilai QTY kosong di Penjualan2205 baris 1234 (item 'Kentang Goreng 5mm') — diperlakukan sebagai 0", source: "Penjualan2205", sheet: "22.05", rawValue: "", rowNumber: 1234 },
    { severity: "WARNING", code: "VALUE_MISSING", message: "Nilai QTY kosong di RekapBerjalan baris 1071 (item 'Cup 16oz') — diperlakukan sebagai 0", source: "RekapBerjalan", sheet: "Rekap", rawValue: "", rowNumber: 1071 },
    { severity: "WARNING", code: "TANGGAL_MISSING", message: "Tanggal kosong di Kirim4215 baris 882 — baris diberi tanggal periode berjalan", source: "Kirim4215", sheet: "Sheet1", rawValue: "", rowNumber: 882 },
    ...tanpaHargaNames.map((name) => ({
      severity: "WARNING" as const,
      code: "KONVERSI_GAGAL" as const,
      message: `Konversi harga gagal untuk '${name}' — tidak ada harga 41.09 yang cocok; nominal deviasi tidak dihitung (null)`,
      source: "Harga",
      sheet: "41.09",
      rawValue: name,
      rowNumber: null,
    })),
    { severity: "WARNING", code: "KATEGORI_KOSONG", message: "Kategori barang 'Sarung Tangan Vinyl' kosong di DBSKategori — ditampilkan sebagai (Tanpa Kategori)", source: "DBSKategori", sheet: "DBS-Kategori", rawValue: "Sarung Tangan Vinyl", rowNumber: 41 },
    { severity: "WARNING", code: "DUPLIKAT_BARIS", message: "Baris duplikat di RekapBerjalan (item 'Gula Pasir Premium', 2 baris identik) — baris kedua diabaikan", source: "RekapBerjalan", sheet: "Rekap", rawValue: "Gula Pasir Premium", rowNumber: 812 },
    { severity: "WARNING", code: "DUPLIKAT_BARIS", message: "Baris duplikat di RI3224 (resto MLGPAR, item 'Mie Telur Spesial') — baris kedua diabaikan", source: "RI3224", sheet: "RI", rawValue: "Mie Telur Spesial", rowNumber: 512 },
    { severity: "INFO", code: "PREFLIGHT_FOLDER", message: "Preflight folder: 15 folder config.json diperiksa — 14 terbaca, 1 dilewati (Terima4215)", source: "config.json", sheet: null, rawValue: null, rowNumber: null },
    ...tanpaHargaNames.map((name) => ({
      severity: "INFO" as const,
      code: "TANPA_HARGA" as const,
      message: `Barang '${name}' masuk daftar Tanpa Harga — nominal deviasi tidak dihitung (null)`,
      source: "Harga",
      sheet: "41.09",
      rawValue: name,
      rowNumber: null,
    })),
  ];

  // -------------------------------------------------------------------
  // 11) logs — INFO per modul pembaca (10) + append1/konversi/nominal/PO/audit
  //     + 1 baris WARNING/ERROR per DQ issue non-INFO (jejak §82b)
  //     + baris pembuka & penutup; ts deterministik (basis periode) demi FR-12
  // -------------------------------------------------------------------
  const logs: EngineLogLine[] = [];
  const logBaseMs = Date.UTC(year, month - 1, 1, 1, 0, 0); // 01:00 UTC = 08:00 WIB di tanggal 1 periode
  const pushLog = (level: "INFO" | "WARNING" | "ERROR", message: string): void => {
    logs.push({ ts: new Date(logBaseMs + logs.length * 50).toISOString(), level, message });
  };

  pushLog("INFO",
    `Mulai proses bundle ${params.bundleName === null ? "(tanpa nama)" : `"${params.bundleName}"`} — periode ${params.periodKey}, tanggal H ${params.tanggalH}, ambang ACR ${params.ambangAcrPct}% (${ENGINE_NAME} v${ENGINE_VERSION}, definisi ${DEFINITION_VERSION}, kontrak 1)`);
  // INFO per modul pembaca (10)
  pushLog("INFO", "Pembaca rekap: RekapBerjalan 1284 baris + RekapLalu 1102 baris (gabung berjalan+lalu)");
  pushLog("INFO", "Pembaca penjualan 22.05: Penjualan2205 4512 baris");
  pushLog("INFO", "Pembaca kirim 42.05: Kirim4215 2377 baris");
  pushLog("INFO", "Pembaca terima 42.15: folder Terima4215 SKIP — tidak pernah dibaca pipeline (paritas desktop v3.9.71)");
  pushLog("INFO", "Pembaca RI 32.24: RI3224 2140 baris + RI3224Lalu 1705 baris");
  pushLog("INFO", "Pembaca saldo awal 42.17: SaldoAwal4217 412 baris");
  pushLog("INFO", "Pembaca kategori: DBSKategori 268 barang");
  pushLog("INFO", "Pembaca pemindahan 42.05: Pemindahan4205 1288 baris + Pemindahan4205Lalu 700 baris");
  pushLog("INFO", "Pembaca PO 32.43: RincianPO 356 baris");
  pushLog("INFO", "Pembaca harga 41.09 + Data9901: Harga 352 baris, Data9901 47 baris");

  pushLog("INFO", `Append1: gabung rekap berjalan + lalu → ${rows.length} baris hasil`);
  pushLog("INFO", `Konversi harga 41.09: ${ITEMS.length - tanpaHargaNames.length} dari ${ITEMS.length} barang berhasil; ${tanpaHargaNames.length} barang masuk daftar Tanpa Harga (nominal = null)`);
  pushLog("INFO", `Hitung nominal deviasi: ${nominalRowCount} baris bernominal, total ${nominalTotal}`);

  const poMenungguItems = poList.reduce(
    (n, po) => n + po.items.filter((it) => it.status === "menunggu diproses").length,
    0,
  );
  pushLog("INFO", `Rincian PO: ${poList.length} PO dari ${RESTOS.length} resto, ${poMenungguItems} item menunggu diproses`);

  const restoSelisihCount = selisihIn.filter((s) => s.hasilAudit === "SELISIH").length;
  const totalSkorResto = selisihIn.reduce((n, s) => n + s.skorResto, 0);
  pushLog("INFO", `Audit selisih IN per resto: ${restoSelisihCount} resto SELISIH dari ${RESTOS.length} resto, total skor resto ${totalSkorResto}`);

  // 1 baris WARNING/ERROR per DQ issue non-INFO (kontrak §82b — jejak 1:1)
  for (const issue of dqIssues) {
    if (issue.severity === "INFO") continue;
    const prefiks = issue.source === null ? "" : `${issue.source} — `;
    pushLog(issue.severity, `[${issue.code}] ${prefiks}${issue.message}`);
  }

  const warningCount = logs.filter((l) => l.level === "WARNING").length;
  const errorCount = logs.filter((l) => l.level === "ERROR").length;

  const hasError = dqIssues.some((d) => d.severity === "ERROR");
  const hasWarning = dqIssues.some((d) => d.severity === "WARNING");
  const status: RunStatus = hasError ? "SELESAI_PARSIAL" : hasWarning ? "SELESAI_DENGAN_PERINGATAN" : "SELESAI";

  pushLog("INFO",
    `${status} — periode ${params.periodKey}: ${rows.length} baris, ${dqIssues.length} masalah kualitas data (${warningCount} peringatan, ${errorCount} error) (${logs.length + 1} baris log)`);

  // -------------------------------------------------------------------
  // 12) summary + rakit EngineResult
  // -------------------------------------------------------------------
  const summary: EngineSummary = {
    restoCount: RESTOS.length,
    itemCount: ITEMS.length,
    rowCount: rows.length,
    dayCount,
    nominalTotal,
    deviasiQtyTotal,
    skipFileCount: sourceFiles.filter((f) => f.status === "SKIP").length,
    warningCount,
    errorCount,
    dqIssueCount: dqIssues.length,
    poCount: poList.length,
  };

  return {
    contractVersion: "1",
    engineKind: "demo",
    engineName: ENGINE_NAME,
    engineVersion: ENGINE_VERSION,
    definitionVersion: DEFINITION_VERSION,
    periodKey: params.periodKey,
    params: { tanggalH: params.tanggalH, ambangAcrPct: params.ambangAcrPct, bundleName: params.bundleName },
    status,
    startedAt: startedAtDate.toISOString(),
    durationMs: Math.round(performance.now() - t0),
    summary,
    sourceFiles,
    rows,
    prices,
    selisihIn,
    po: poList,
    dqIssues,
    logs,
  };
}
