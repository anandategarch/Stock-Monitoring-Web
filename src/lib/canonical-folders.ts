// ============================================================
// canonical-folders.ts — 14 folder export Accurate config.json desktop
// (IDENTIK desktop v3.9.71, FR-2). Client-safe (dipakai UI + server):
// pemilihan folder job agent kini berbasis daftar kanonik ini — bukan
// link Google Drive (Task 55: fitur import Drive dihapus; agent membaca
// folder berjudul sama persis di RootPath disk lokal, mis.
// C:\KERJA\1. RESTO\9.NEW QUERY\).
// ============================================================

export interface CanonicalFolder {
  /** Kunci config.json desktop — dikirim ke agent sebagai identitas folder. */
  folderKey: string;
  /** Judul folder PERSIS di RootPath — agent mencocokkan nama ini. */
  folderName: string;
  /** False = folder dibaca engine desktop TIDAK dipakai (v3.9.71:
   *  "3. 42.15" hanya lewat sisi Kirim). Default checkbox: tidak tercentang. */
  dibaca: boolean;
}

export const CANONICAL_FOLDERS: CanonicalFolder[] = [
  { folderKey: "RekapBerjalan", folderName: "1. DEVIASI WEEKLY", dibaca: true },
  { folderKey: "RekapLalu", folderName: "1.12 Rekap Mentah Bulan Lalu", dibaca: true },
  { folderKey: "Penjualan2205", folderName: "2. 22.05", dibaca: true },
  { folderKey: "Kirim4215", folderName: "3.1 42.15 Kirim", dibaca: true },
  { folderKey: "Terima4215", folderName: "3. 42.15", dibaca: false },
  { folderKey: "RI3224", folderName: "13. 32.24 RI", dibaca: true },
  { folderKey: "RI3224Lalu", folderName: "13.2 3224 RI Bulan Lalu", dibaca: true },
  { folderKey: "SaldoAwal4217", folderName: "6.1 42.17 Saldo Awal", dibaca: true },
  { folderKey: "DBSKategori", folderName: "21. DBS Kategori", dibaca: true },
  { folderKey: "Pemindahan4205", folderName: "4. 42.05", dibaca: true },
  { folderKey: "Pemindahan4205Lalu", folderName: "4.1 4205 Bulan Lalu", dibaca: true },
  { folderKey: "RincianPO", folderName: "25. Rincian PO", dibaca: true },
  { folderKey: "Data9901", folderName: "30. 9901", dibaca: true },
  { folderKey: "Harga", folderName: "09.Harga", dibaca: true },
];

export const MAX_AGENT_FOLDERS = CANONICAL_FOLDERS.length;
