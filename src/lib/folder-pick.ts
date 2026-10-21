// ============================================================
// folder-pick.ts — Pilih folder export Accurate LANGSUNG dari komputer,
// tanpa ZIP manual (FR-1). CLIENT-ONLY.
//
// Kenapa tetap perlu "perjalanan" file? Server web TIDAK BISA membaca
// isi komputer user — itu batas keamanan browser: halaman mana pun di
// internet dilarang mengintip folder lokal. Jalan satu-satunya: USER
// sendiri yang memilih foldernya (input webkitdirectory), lalu browser
// menyerahkan isi folder itu (file + path relatif) ke halaman.
//
// File-file itu lalu dibungkus ZIP DI BROWSER (fflate, level 0 / store —
// file Excel memang sudah terkompresi internally) dan diunggah ke
// /api/ingest/upload seperti biasa: SATU endpoint, SATU jalur validasi
// manifest (FR-2) — server tidak peduli ZIP-nya dibuat oleh siapa.
// Ketika pipeline berjalan di komputer yang sama (engine lokal), unggahan
// hanya "naik" ke localhost — praktis tanpa jaringan.
// ============================================================
import { zipSync } from "fflate";

const EXCEL_RE = /\.(xlsx|xls|xlsb)$/i;

/** Batas aman sisi klien: server menerima ZIP ≤ 400 MB, dan ZIP store-mode
 * ukurannya ≈ jumlah file Excel + overhead kecil → 380 MB aman. */
export const MAX_FOLDER_BYTES = 380 * 1024 * 1024;

export type PickedExcelFile = { rel: string; file: File };

export type FolderScan = {
  /** Nama folder yang dipilih user (dipakai menamai bundle, mis. "Export Okt"). */
  rootName: string;
  files: PickedExcelFile[];
  skippedCount: number;
  totalBytes: number;
};

/**
 * Kumpulkan file Excel dari hasil pilihan folder (input webkitdirectory).
 * - Entri sampah macOS (__MACOSX, .*) dan non-Excel dilewati & dihitung.
 * - Path direlativkan terhadap folder yang DIPILIH (segmen pertama
 *   webkitRelativePath = nama folder pilihan user → dibuang), sehingga
 *   entri ZIP langsung berbentuk "2. 22.05/xxx.xlsx" seperti yang
 *   diharapkan server (FR-2). Bila user memilih folder INDUK yang berisi
 *   folder export, server turunkan satu level lagi (computeFolderStats +
 *   resolveBundlePath — dua-duanya sudah menangani).
 */
export function collectExcelFromFolder(files: File[]): FolderScan {
  const picked: PickedExcelFile[] = [];
  const rootNames = new Set<string>();
  let skippedCount = 0;

  for (const f of files) {
    const rel = f.webkitRelativePath || f.name;
    if (rel.includes("__MACOSX") || rel.split(/[/\\]/).some((s) => s.startsWith("._"))) {
      skippedCount += 1;
      continue;
    }
    if (!EXCEL_RE.test(f.name)) {
      skippedCount += 1;
      continue;
    }
    const segs = rel.split(/[/\\]/);
    if (segs.length > 1) {
      rootNames.add(segs[0]);
      segs.shift();
    }
    picked.push({ rel: segs.join("/"), file: f });
  }

  const rootName =
    rootNames.size === 1 ? [...rootNames][0]! : picked.length > 0 ? "bundle-export" : "";
  const totalBytes = picked.reduce((sum, p) => sum + p.file.size, 0);
  return { rootName, files: picked, skippedCount, totalBytes };
}

/**
 * Bungkus hasil pilihan folder menjadi File .zip (siap diunggah), dengan
 * progres pembacaan file per file. Level 0 (store): .xlsx sudah terkompresi,
 * jadi ini praktis hanya "kemas ulang" — cepat, CPU ringan.
 */
export async function zipPickedFolder(
  scan: FolderScan,
  onRead?: (done: number, total: number) => void,
): Promise<File> {
  const data: Record<string, Uint8Array> = {};
  const total = scan.files.length;
  for (let i = 0; i < total; i += 1) {
    const { rel, file } = scan.files[i]!;
    data[rel] = new Uint8Array(await file.arrayBuffer());
    onRead?.(i + 1, total);
  }
  const zipped = zipSync(data, { level: 0 });
  return new File([zipped], `${scan.rootName || "bundle-export"}.zip`, {
    type: "application/zip",
  });
}
