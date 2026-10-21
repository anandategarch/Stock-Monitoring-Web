// ============================================================
// sync-prisma-schemas.mjs — turunkan prisma/schema.sqlite.prisma (dev
// sandbox/lokal) dari KANONIK prisma/schema.prisma (PostgreSQL/Supabase).
//
// Dijalankan otomatis oleh `bun run db:push` / `bun run db:generate`
// (lihat package.json). Skrip ini satu-satunya cara pembuatan file
// cermin — file cermin TIDAK diedit manual.
//
// Transformasi: provider "postgresql" → "sqlite" + baris directUrl dibuang.
// Seluruh model/hubungan disalin apa adanya (aturan portabilitas §6
// ARCHITECTURE.md: tanpa array Prisma, tanpa atribut @db.* vendor).
// ============================================================
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const canonicalPath = join(root, "prisma", "schema.prisma");
const mirrorPath = join(root, "prisma", "schema.sqlite.prisma");

if (!existsSync(canonicalPath)) {
  console.error(`[sync] Kanonik tidak ditemukan: ${canonicalPath}`);
  process.exit(1);
}

const canonical = readFileSync(canonicalPath, "utf8");

// Guard fail-fast — aturan portabilitas §6 ARCHITECTURE.md: kanonik dilarang
// memakai atribut native @db.* (cermin SQLite tidak bisa menerjemahkannya).
// Komentar // dihapus dulu agar catatan "tanpa @db.*" di header skema sah
// tidak memicu guard — hanya atribut aktif yang dianggap pelanggaran.
if (canonical.replace(/\/\/[^\n]*/g, "").includes("@db.")) {
  throw new Error("Skema kanonik memakai @db.* — dilarang (aturan portabilitas SQLite↔Postgres).");
}

// Kanonik WAJIB provider postgresql — cermin sqlite hanya boleh lahir
// dari kanonik yang benar (mencegah sinkronisasi arah terbalik).
if (!/provider\s*=\s*"postgresql"/.test(canonical)) {
  console.error(
    '[sync] GAGAL: prisma/schema.prisma bukan provider "postgresql". ' +
      "Skrip ini hanya menurunkan cermin SQLite dari kanonik PostgreSQL (lihat README.md).",
  );
  process.exit(1);
}

// Buang blok komentar header lama (baris // di atas, sampai blok pertama).
const body = canonical.replace(/^(\/\/[^\n]*\n)+/, "");

// Buang baris directUrl + komentar di atasnya yang spesifik DDL pooler.
const withoutDirectUrl = body
  .replace(/^\s*\/\/.*(?:DDL|pooler|Runtime).*\n(?:\s*\/\/.*\n)*\s*directUrl\s*=.*$\n?/m, "")
  .replace(/^\s*directUrl\s*=.*$\n?/m, "");

const header =
  "// ============================================================\n" +
  "// FILE DIGENERATE OTOMATIS — jangan edit manual.\n" +
  "// Cermin SQLite (dev sandbox/lokal) dari kanonik prisma/schema.prisma\n" +
  "// (PostgreSQL/Supabase). Edit kanonik lalu jalankan: bun run db:push\n" +
  "// atau node scripts/sync-prisma-schemas.mjs.\n" +
  "// ============================================================\n\n";

const mirror = (
  header +
  withoutDirectUrl.replace(/(provider\s*=\s*)"postgresql"/, '$1"sqlite"')
).replace(/\n{3,}$/g, "\n");

const previous = existsSync(mirrorPath) ? readFileSync(mirrorPath, "utf8") : null;
if (previous === mirror) {
  console.log("[sync] prisma/schema.sqlite.prisma sudah sinkron — tidak ada perubahan.");
} else {
  writeFileSync(mirrorPath, mirror, "utf8");
  console.log("[sync] prisma/schema.sqlite.prisma ditulis ulang (cermin SQLite dari kanonik).");
}
