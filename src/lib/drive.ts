// ============================================================
// drive.ts — Tarik bundle export Accurate LANGSUNG dari folder
// Google Drive publik (FR-1, kelanjutan "tanpa ZIP manual").
// SERVER-ONLY.
//
// Cara kerja: Google Drive TIDAK memberi API anonim, tapi folder
// yang dibagikan "Siapa saja yang memiliki link" merender daftar
// isinya di endpoint embeddedfolderview (tanpa login) — server
// mem-parse daftar itu (nama, id, tanggal modifikasi, file/folder),
// lalu mengunduh tiap file Excel lewat uc?export=download. Tidak
// perlu ZIP, tidak perlu unduh manual oleh user — file "berjalan"
// dari Drive ke server sendiri. Jalur validasi TETAP SATU:
// hasil unduhan masuk materializeBundle() (FR-2) yang sama dengan
// ZIP unggahan — server tidak peduli asal file.
//
// Batasan jujur:
//  - Folder HARUS dibagikan publik ("Siapa saja yang memiliki link",
//    akses Viewer) — link privat/pw-protected tidak bisa ditarik.
//  - embeddedfolderview hanya menampilkan 1 level per folder →
//    subfolder di-walk eksplisit (batas kedalaman 2, folder ≤ 12).
//  - File ganda bernama SAMA di satu folder Drive diizinkan Drive;
//    bila tanggal modifikasi tersedia → versi TERBARU menang dan
//    versi lama dilaporkan jujur; bila tidak → semua dipertahankan
//    dengan akhiran __2, __3 (juga dilaporkan).
// ============================================================
import "server-only";
import { FOLDER_TEMPLATE } from "@/lib/bundles";

const LIST_URL = (folderId: string) => `https://drive.google.com/embeddedfolderview?id=${folderId}`;
const DOWNLOAD_URL = (fileId: string) => `https://drive.google.com/uc?export=download&id=${fileId}`;

const EXCEL_RE = /\.(xlsx|xls|xlsb)$/i;
const FOLDER_ID_RE = /^[A-Za-z0-9_-]{15,}$/;
const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36";

const MONTHS: Record<string, number> = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
};

// ---------- Parse link ----------

/** Terima: /drive/folders/{id}, /drive/u/0/folders/{id}, ?id={id},
 *  embeddedfolderview?id={id}, atau ID mentah. Selalu lempar Error
 *  berbahasa Indonesia bila tidak dikenali. */
export function parseDriveFolderId(raw: string): string {
  const s = raw.trim();
  if (!s) throw new Error("Link folder Drive kosong.");
  let m = s.match(
    /(?:https?:\/\/)?drive\.google\.com\/(?:drive\/(?:u\/\d+\/)?folders|folders)\/([A-Za-z0-9_-]+)/,
  );
  if (m?.[1] && FOLDER_ID_RE.test(m[1])) return m[1];
  m = s.match(/[?&]id=([A-Za-z0-9_-]{15,})/);
  if (m?.[1]) return m[1];
  if (FOLDER_ID_RE.test(s) && !s.includes("/") && !s.includes(".")) return s;
  throw new Error(
    "Link tidak dikenali — pakai link folder Drive, mis. https://drive.google.com/drive/folders/XXXX",
  );
}

/** Bentuk kanonik untuk disimpan (unique key): drive.google.com/drive/folders/{id}. */
export function canonicalDriveUrl(folderId: string): string {
  return `https://drive.google.com/drive/folders/${folderId}`;
}

// ---------- Util kecil ----------

function decodeEntities(s: string): string {
  return s
    .replace(/&#(\d+);/g, (_, d: string) => {
      const code = Number(d);
      // jaga-jaga dari entitas di luar rentang Unicode (audit 48-g-api: RangeError)
      return code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : "";
    })
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'");
}

/** Tanggal embeddedfolderview punya BEBERAPA format (en-US):
 *  - "Oct 20"       (baru, tahun berjalan)
 *  - "Oct 20, 2024" (lama, >1 tahun)
 *  - "8/25/25"      (lama, M/D/YY numerik — file 2025 dst.)
 *  - "12/3/2024"    (M/D/YYYY)
 *  → epoch ms, atau null bila tak terbaca. */
export function parseDriveDate(raw: string | null): number | null {
  if (!raw) return null;
  const s = raw.trim();

  // "Oct 20" / "Oct 20, 2024"
  let m = s.match(/^([A-Za-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?$/);
  if (m) {
    const month = MONTHS[m[1]!.toLowerCase()];
    if (month !== undefined) {
      const year = m[3] ? Number(m[3]) : new Date().getFullYear();
      const ms = Date.UTC(year, month, Number(m[2]));
      return Number.isFinite(ms) ? ms : null;
    }
  }

  // "8/25/25" / "12/3/2024" (en-US: bulan/tanggal/tahun)
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
  if (m) {
    const month = Number(m[1]) - 1;
    const day = Number(m[2]);
    let year = Number(m[3]);
    if (year < 100) year += 2000;
    if (month >= 0 && month <= 11 && day >= 1 && day <= 31) {
      const ms = Date.UTC(year, month, day);
      return Number.isFinite(ms) ? ms : null;
    }
  }

  // "9:53 pm" — Drive menampilkan JAM untuk file yang baru saja dimodifikasi
  // (<~24 jam). Anggap = hari ini + jam tsb — cukup akurat untuk mengurutkan
  // (selalu lebih baru dari tanggal-tanggal lama).
  m = s.match(/^(\d{1,2}):(\d{2})\s*(am|pm)$/i);
  if (m) {
    const now = new Date();
    let hour = Number(m[1]) % 12;
    if (/pm/i.test(m[3]!)) hour += 12;
    const ms = Date.UTC(
      now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, Number(m[2]),
    );
    return Number.isFinite(ms) ? ms : null;
  }
  return null;
}

/** Cocokkan judul folder Drive → kunci folder config.json (FR-2). */
export function mapDriveFolderKey(folderName: string): string | null {
  const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, " ");
  const hit = FOLDER_TEMPLATE.find((t) => norm(t.folderName) === norm(folderName));
  return hit?.folderKey ?? null;
}

/** Error akses folder Drive dengan kode eksplisit — route memetakan status
 *  tanpa mengendus teks pesan (audit 48-g-api). */
export class DriveAccessError extends Error {
  code: "PRIVATE" | "NOT_FOUND" | "EMPTY" | "INVALID_ID";
  constructor(code: DriveAccessError["code"], message: string) {
    super(message);
    this.name = "DriveAccessError";
    this.code = code;
  }
}

// ---------- Listing ----------

export type DriveEntry = {
  id: string;
  name: string;
  isFolder: boolean;
  modifiedMs: number | null;
};

export type DriveListing = {
  folderId: string;
  folderName: string;
  entries: DriveEntry[];
};

/** Daftar isi SATU folder Drive publik via embeddedfolderview (tanpa API key). */
export async function listDriveFolder(folderId: string): Promise<DriveListing> {
  if (!FOLDER_ID_RE.test(folderId)) {
    throw new DriveAccessError("INVALID_ID", "ID folder Drive tidak valid.");
  }
  const res = await fetch(LIST_URL(folderId), {
    headers: { "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9" },
    redirect: "follow",
    cache: "no-store",
    signal: AbortSignal.timeout(15_000),
  });
  if (res.status === 404) {
    throw new DriveAccessError("NOT_FOUND", "Folder Drive tidak ditemukan (404) — cek link-nya.");
  }
  if (!res.ok) {
    throw new Error(`Drive merespons HTTP ${res.status} — coba lagi sebentar.`);
  }
  const html = await res.text();
  const title = decodeEntities(html.match(/<title>([^<]*)<\/title>/)?.[1] ?? "").trim();

  // Deteksi halaman login Google secara STRUCTURAL (form accounts.google.com),
  // bukan regex judul bebas — folder bernama sah "Analisa Error 2024" tidak
  // boleh tertolak palsu (audit 48-g-engine).
  if (!title || html.includes("accounts.google.com")) {
    throw new DriveAccessError(
      "PRIVATE",
      "Folder Drive tidak bisa dibaca — pastikan dibagikan “Siapa saja yang memiliki link” akses Viewer.",
    );
  }

  const entries: DriveEntry[] = [];
  for (const block of html.split('<div class="flip-entry" id="entry-').slice(1)) {
    const end = block.indexOf(`"`);
    const id = block.slice(0, end > 0 ? end : 0);
    if (!FOLDER_ID_RE.test(id)) continue;
    const name = decodeEntities(block.match(/flip-entry-title">([^<]+)</)?.[1] ?? "");
    if (!name) continue;
    entries.push({
      id,
      name,
      isFolder: block.includes("/drive/folders/"),
      modifiedMs: parseDriveDate(
        block.match(/flip-entry-last-modified"><div>([^<]+)</)?.[1] ?? null,
      ),
    });
  }

  if (entries.length === 0) {
    throw new DriveAccessError("EMPTY", `Folder Drive “${title}” kosong atau isinya tidak terbaca.`);
  }
  return { folderId, folderName: title, entries };
}

// ---------- Kumpulkan file (1 level + rekursi subfolder) ----------

export type DriveFileRef = { id: string; path: string; name: string; modifiedMs: number | null };

export type DriveCollect = {
  folderName: string;
  folderKey: string | null;
  /** true bila ada subfolder yang di-walk (path relatif subfolder dipertahankan). */
  walkedSubfolders: boolean;
  files: DriveFileRef[];
  skippedNonExcel: number;
  subfolderCount: number;
  /** Batas tercapai — pelancongan DIPOTONG, dilaporkan jujur (audit 48-g-engine). */
  truncatedFiles: boolean;
  truncatedFolders: boolean;
  /** Subfolder yang listing-nya gagal dibaca (dilaporkan, tidak fatal). */
  failedSubfolders: string[];
};

/**
 * Kumpulkan daftar FILE Excel dari satu folder Drive (rekursi ke subfolder
 * s.d. kedalaman 2 — struktur bundle "14 folder" di dalam satu folder induk
 * tetap terpelihara). File diberi path relatif; bila folder root sendiri
 * bernama persis folder kanonik (mis. "1. DEVIASI WEEKLY"), path dibingkai
 * nama kanonik itu sehingga FR-2 langsung mengenalinya.
 */
export async function collectDriveFiles(
  folderId: string,
  limits: { maxFiles: number; maxFolders: number } = { maxFiles: 300, maxFolders: 16 },
): Promise<DriveCollect> {
  const root = await listDriveFolder(folderId);
  const canonicalName =
    FOLDER_TEMPLATE.find((t) => mapDriveFolderKey(root.folderName) === t.folderKey)?.folderName ?? null;

  const files: DriveFileRef[] = [];
  const subfolders: DriveEntry[] = [];
  let skippedNonExcel = 0;
  let truncatedFiles = false;

  for (const e of root.entries) {
    if (e.isFolder) {
      subfolders.push(e);
      continue;
    }
    if (!EXCEL_RE.test(e.name)) {
      skippedNonExcel += 1;
      continue;
    }
    if (files.length >= limits.maxFiles) {
      truncatedFiles = true;
      break;
    }
    files.push({ id: e.id, path: e.name, name: e.name, modifiedMs: e.modifiedMs });
  }

  // File root yang dibingkai nama folder KANONIK (normalisasi sekaligus):
  if (canonicalName) {
    for (const f of files) f.path = `${canonicalName}/${f.name}`;
  }

  // Rekursi subfolder (kedalaman 2: root + 1 level subfolder), listing
  // DIJALANKAN PARALEL (≤4) — listing beruntun 12×15 dtk bisa melewati
  // maxDuration serverless (audit 48-g-engine).
  const walked = new Set<string>([folderId]);
  const truncatedFolders = subfolders.length > limits.maxFolders;
  const toWalk = subfolders.slice(0, limits.maxFolders);
  const failedSubfolders: string[] = [];
  let subfolderCount = 0;

  let cursor = 0;
  const walkWorkers = Array.from({ length: Math.min(4, toWalk.length) }, async () => {
    while (cursor < toWalk.length) {
      if (files.length >= limits.maxFiles) {
        truncatedFiles = true;
        return;
      }
      const sub = toWalk[cursor]!;
      cursor += 1;
      if (walked.has(sub.id)) continue;
      let subList: DriveListing;
      try {
        subList = await listDriveFolder(sub.id);
      } catch {
        failedSubfolders.push(sub.name); // dilaporkan jujur, tidak fatal
        continue;
      }
      walked.add(sub.id);
      subfolderCount += 1;
      for (const e of subList.entries) {
        if (e.isFolder) continue; // lebih dalam dari 2 level tidak di-walk
        if (!EXCEL_RE.test(e.name)) {
          skippedNonExcel += 1;
          continue;
        }
        if (files.length >= limits.maxFiles) {
          truncatedFiles = true;
          break;
        }
        files.push({ id: e.id, path: `${sub.name}/${e.name}`, name: e.name, modifiedMs: e.modifiedMs });
      }
    }
  });
  await Promise.all(walkWorkers);

  if (files.length === 0) {
    throw new DriveAccessError(
      "EMPTY",
      `Tidak ada file Excel (.xlsx/.xls/.xlsb) di folder Drive “${root.folderName}”.`,
    );
  }
  return {
    folderName: root.folderName,
    folderKey: canonicalName ? mapDriveFolderKey(root.folderName) : null,
    walkedSubfolders: subfolderCount > 0,
    files,
    skippedNonExcel,
    subfolderCount,
    truncatedFiles,
    truncatedFolders,
    failedSubfolders,
  };
}

// ---------- Dedup nama sama ----------

export type DriveDedupe = {
  kept: DriveFileRef[];
  /** Nama sama, versi terbaru menang — versi lama dilewati (jujur dilaporkan). */
  skipped: { path: string; reason: string }[];
  /** Nama sama TANPA tanggal modifikasi → semua dipertahankan dengan akhiran __2 dst. */
  suffixed: string[];
};

/** Drive mengizinkan beberapa file bernama sama dalam satu folder.
 *  Kebijakan: SEMUA punya tanggal → terbaru menang (lama dilaporkan); jika
 *  ada yang tak bertanggal → semua dipertahankan. Setelahnya PASS KEUNIKAN
 *  GLOBAL lintas grup (audit 48-g-engine: grup “x.xlsx” vs file asli
 *  “x__2.xlsx” bisa berkolisi → writer menimpa senyap). */
export function dedupeDriveFiles(files: DriveFileRef[]): DriveDedupe {
  const groups = new Map<string, DriveFileRef[]>();
  for (const f of files) {
    const list = groups.get(f.path) ?? [];
    list.push(f);
    groups.set(f.path, list);
  }

  type Picked = { ref: DriveFileRef; path: string };
  const picked: Picked[] = [];
  const skipped: { path: string; reason: string }[] = [];

  for (const [path, list] of groups) {
    if (list.length === 1) {
      picked.push({ ref: list[0]!, path });
      continue;
    }
    const allDated = list.every((f) => f.modifiedMs !== null);
    if (allDated) {
      const sorted = [...list].sort((a, b) => (b.modifiedMs ?? 0) - (a.modifiedMs ?? 0));
      picked.push({ ref: sorted[0]!, path });
      for (const f of sorted.slice(1)) {
        const when = f.modifiedMs ? new Date(f.modifiedMs).toISOString().slice(0, 10) : "?";
        skipped.push({ path, reason: `versi ${when} (lebih lama) dilewati — ${f.id}` });
      }
    } else {
      for (const f of list) picked.push({ ref: f, path });
    }
  }

  // Pass keunikan GLOBAL: path final tidak boleh dipakai dua file apa pun.
  const used = new Set<string>();
  const kept: DriveFileRef[] = [];
  const suffixed: string[] = [];
  for (const p of picked) {
    let out = p.path;
    if (used.has(out)) {
      const dot = out.lastIndexOf(".");
      const base = dot > 0 ? out.slice(0, dot) : out;
      const ext = dot > 0 ? out.slice(dot) : "";
      let n = 2;
      while (used.has(`${base}__${n}${ext}`)) n += 1;
      out = `${base}__${n}${ext}`;
      suffixed.push(out);
    }
    used.add(out);
    kept.push({ ...p.ref, path: out });
  }
  return { kept, skipped, suffixed };
}

// ---------- Unduh ----------

/** Error kualitas FILE (bukan Excel / rusak / 0 byte): file DILEWATI dengan
 *  laporan jujur — konsisten dengan kelas DQ SKIP_FILE pipeline. Jangan
 *  batal seluruh bundle karena satu file jelek, tapi jangan pernah diam-diam. */
export class DriveFileBadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DriveFileBadError";
  }
}

function looksLikeHtml(buf: Uint8Array): boolean {
  const head = Buffer.from(buf.slice(0, 512)).toString("utf8").trimStart().toLowerCase();
  return head.startsWith("<!doctype") || head.startsWith("<html");
}

function isExcelMagic(buf: Uint8Array): boolean {
  if (buf.byteLength < 4) return false;
  const zipMagic = buf[0] === 0x50 && buf[1] === 0x4b && buf[2] === 0x03 && buf[3] === 0x04; // .xlsx/.xlsb
  const oleMagic = buf[0] === 0xd0 && buf[1] === 0xcf && buf[2] === 0x11 && buf[3] === 0xe0; // .xls lama
  return zipMagic || oleMagic;
}

/** Unduh satu file Drive publik. File besar (>100 MB) membuat Drive
 *  menampilkan halaman konfirmasi — di-retry dengan confirm=t; bila masih
 *  HTML, gagal jujur. Magic bytes Excel diverifikasi (anti-HTML-renamed). */
export async function downloadDriveFile(
  fileId: string,
  opts: { maxBytes: number; timeoutMs?: number },
): Promise<Uint8Array> {
  const url = DOWNLOAD_URL(fileId);
  const doFetch = (u: string) =>
    fetch(u, {
      headers: { "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9" },
      redirect: "follow",
      cache: "no-store",
      signal: AbortSignal.timeout(opts.timeoutMs ?? 180_000),
    });

  let res = await doFetch(url);
  if (res.status === 404) {
    throw new DriveFileBadError("File tidak ditemukan di Drive (404) — mungkin dihapus.");
  }
  if (!res.ok) {
    throw new Error(`Drive menolak unduhan (HTTP ${res.status}).`);
  }
  // Cek Content-Length SEBELUM buffering (audit 48-g-api/48-g-engine: file
  // raksasa bisa OOM lambda sebelum batas per-file sempat diuji).
  const declared = Number(res.headers.get("content-length") ?? "0");
  if (declared > opts.maxBytes) {
    throw new Error(
      `File ${(declared / 1024 / 1024).toFixed(0)} MB — melebihi batas ${(opts.maxBytes / 1024 / 1024).toFixed(0)} MB per file.`,
    );
  }
  let buf = new Uint8Array(await res.arrayBuffer());

  if (looksLikeHtml(buf)) {
    res = await doFetch(`${url}&confirm=t`);
    if (!res.ok) throw new Error(`Drive menolak unduhan ulang (HTTP ${res.status}).`);
    buf = new Uint8Array(await res.arrayBuffer());
  }
  if (looksLikeHtml(buf)) {
    throw new DriveFileBadError(
      "Drive mengembalikan halaman konfirmasi/konflik — file tidak bisa ditarik otomatis.",
    );
  }
  if (buf.byteLength === 0) {
    throw new DriveFileBadError("File kosong (0 byte).");
  }
  if (!isExcelMagic(buf)) {
    throw new DriveFileBadError(
      `Isi bukan Excel (.xlsx/.xls/.xlsb) — ${buf.byteLength} byte, kemungkinan file rusak/placeholder di Drive.`,
    );
  }
  if (buf.byteLength > opts.maxBytes) {
    throw new Error(
      `File ${(buf.byteLength / 1024 / 1024).toFixed(0)} MB — melebihi batas ${(opts.maxBytes / 1024 / 1024).toFixed(0)} MB per file.`,
    );
  }
  return buf;
}
