# Stock-Monitoring-Web (SM-WEB)

Platform web **Stock Monitoring** — migrasi & unifikasi aplikasi desktop Python/Tkinter
`Stock-Monitoring v3.9.71` (16 modul pipeline + 20 file UI) ke web, di atas pola repo
`Inventory-Control`: **Next.js 16 (App Router) · React 19 · TypeScript 5 · Prisma 6 ·
Tailwind CSS 4 + shadcn/ui · Zustand · TanStack Query**.

> Prinsip produk: **kualitas data → snapshot store → analisis → tindak lanjut.**
> Pipeline Python asli **TIDAK ditulis ulang** (FR-10, 0-rewrite) — dibungkus sebagai
> engine service FastAPI (`mini-services/engine-fastapi/`, pipeline v3.9.71 vendored).

| Dokumen | Isi |
|---|---|
| `docs/PRD-STOCK-MONITORING-WEB.md` | PRD v1.1 — keputusan D-1..D-8, FR, roadmap 5 fase |
| `docs/ARCHITECTURE.md` | Arsitektur: keputusan K-1..K-6, topologi, model data |
| `docs/ENGINE-CONTRACT.md` | Kontrak JSON engine v1 (sumber kebenaran) |

**Keputusan arsitektur yang mengikat**: database produksi = **Supabase PostgreSQL,
project BARU khusus SM-WEB — TERPISAH dari Inventory-Control** (D-5) · tanpa login,
single-user (D-6) · repo baru terpisah (D-8).

---

## 1. Yang bisa jalan di mana

| Mode | Ingest bundle real (ZIP export Accurate) | Run/seed DEMO | Semua tab analisis (Pivot, Deviasi, Selisih IN, Nominal, Laporan, PO, DQ, Follow-Up) |
|---|---|---|---|
| **Vercel + Supabase** | belum* (lihat §5.2) | ✅ via fallback **embedded** | ✅ penuh (baca snapshot di Supabase) |
| **Self-host (VPS/Railway: Next.js + engine co-located)** | ✅ penuh | ✅ | ✅ |
| **Dev lokal (SQLite)** | ✅ (jalankan engine produksi lokal) | ✅ | ✅ |

\* filesystem serverless Vercel bersifat ephemeral: unggah bundle kini ditulis ke `/tmp`
(eksplisit saat `VERCEL=1`) sehingga **manifest pratinjau per folder tetap bisa dipakai di Vercel**,
tapi proses bundle real tetap butuh engine FastAPI yang di-host (§5.2) — komit ulang (FR-12)
antar-lambda akan jujur meminta unggah ulang (roadmap: storage bersama, PRD Fase 5).

**Fallback embedded**: bila service engine demo (`SM_ENGINE_URL`) tidak terjangkau,
run DEMO (tanpa bundleId) otomatis diproses generator yang di-bundle ke dalam aplikasi —
kode generator **identik** dengan `mini-services/engine` sehingga hasil deterministik dan
sama (FR-12 idempotent tetap sahih; run di service, komit via embedded = snapshot konsisten).
Run bundle real TIDAK PERNAH di-fallback — gagal jujur (NFR-3). Matikan dengan
`SM_ENGINE_EMBED_FALLBACK=off`.

**Pilih folder tanpa ZIP manual (FR-1)**: di tab Proses & Ingest mode *Produksi*, tombol
**Pilih Folder…** (input `webkitdirectory`) membaca folder export Accurate langsung dari
komputer kamu — file Excel-nya dibungkus ZIP otomatis di browser (`fflate`, level 0) lalu
masuk jalur unggah yang sama dengan ZIP manual (satu jalur validasi manifest FR-2, batas
400 MB; folder induk/pembungkus otomatis dinormalisasi). Tombol **Pilih ZIP…** tetap
tersedia untuk `.zip` yang sudah jadi.

**Ambil dari Google Drive (FR-1, tanpa unduh & ZIP manual)**: bagian *Ambil dari Google
Drive* pada tab Proses & Ingest — tempel link folder Drive (satu link per folder export,
mis. `1. DEVIASI WEEKLY`), klik **Simpan Link** (listing diperiksa langsung; judul folder
yang cocok config.json otomatis dipetakan ke folderKey kanonik), lalu centang dan klik
**Tarik N Folder → Bundle**: server men-unduh file Excel langsung dari Drive
(`embeddedfolderview` listing + `uc?export=download`, magic bytes Excel diverifikasi)
dan mematerialisasinya lewat `createBundleWriter` — SATU jalur validasi/manifest dengan
ZIP (FR-2). Link tersimpan di tabel `DriveFolderLink` ("biar ingat"). Perilaku jujur:
file Drive bernama sama → versi **terbaru** menang (lama dilaporkan di manifest); file
rusak/bukan Excel → dilewati + dilaporkan (konsisten kelas DQ SKIP_FILE); folder harus
dibagikan "Siapa saja yang memiliki link · Viewer". Batas: 400 MB total, 60 MB/file,
200 file, 12 subfolder per folder. Di Vercel berlaku `maxDuration` 60 dtk — folder sangat
besar lebih baik ditarik dari self-host/lokal.

---

## 2. Menjalankan lokal (SQLite, tanpa Postgres)

```bash
bun install
cp .env.example .env          # aktifkan blok "DEV LOKAL": DATABASE_URL=file:../db/custom.db
bun run db:push               # turunkan schema.sqlite.prisma + buat tabel SQLite
bun run dev                   # Next.js di http://localhost:3000
# engine demo + produksi (opsional untuk run DEMO via service / ingest bundle):
bun run dev   # di mini-services/engine          → :3030
bun run dev   # di mini-services/engine-fastapi   → :3031  (butuh Python 3.11 + requirements.txt)
```

Buka aplikasi → tab **⚙️ Config & Admin** → **Isi data demo (2 periode)** untuk mengisi
snapshot demo awal, lalu jelajahi 11 tab (Ikhtisar, Proses & Ingest, Pivot, Deviasi GR/PCS,
Selisih IN, Nominal, Laporan, Follow Up, Rincian PO, Kualitas Data, Config).

### Skema database: kanonik PostgreSQL + cermin SQLite

- `prisma/schema.prisma` — **kanonik** (provider `postgresql`, `DATABASE_URL` + `DIRECT_URL`).
  Satu-satunya file yang diedit untuk model.
- `prisma/schema.sqlite.prisma` — **cermin dev** (provider `sqlite`), digenerate otomatis
  oleh `scripts/sync-prisma-schemas.mjs` (dipanggil `bun run db:push` / `db:generate` /
  `sync:db`). Jangan edit manual.

| Perintah | Target | Dipakai untuk |
|---|---|---|
| `bun run db:push` | cermin SQLite | dev lokal/sandbox (sync otomatis lalu push) |
| `bun run db:push:supabase` | kanonik PostgreSQL | menerapkan skema ke **Supabase** (pakai `DIRECT_URL`) |
| `bun run db:generate` | cermin SQLite | regenerasi klien Prisma dev |
| `bun run db:generate:prod` | kanonik PostgreSQL | regenerasi klien produksi (Vercel melakukannya via `build`) |

Aturan portabilitas model (sudah diberlakukan): tanpa array Prisma (list → kolom JSON
string), tanpa atribut `@db.*` vendor — jadi kedua provider identik dan bebas pindah.

---

## 3. Deploy ke Vercel + Supabase (runbook lengkap)

> Waktu total ± 15 menit. Prasyarat: akun [Vercel](https://vercel.com) &
> [Supabase](https://supabase.com) (keduanya punya free tier).

### Langkah 1 — Buat project Supabase BARU khusus SM-WEB (D-5)

1. Buka https://supabase.com/dashboard → **New project**.
2. Nama bebas (mis. `sm-web`). **Ini project terpisah dari Inventory-Control** — jangan
   pakai project IC yang sudah live (keputusan D-5: skema bebas berevolusi, IC tak tersentuh).
3. Simpan password database saat diminta.
4. Tunggu provisioning selesai (± 2 menit).

### Langkah 2 — Ambil dua connection string

Dashboard Supabase → project SM-WEB → **Project Settings → Database → Connection string**:

| String | Tab | Dipakai untuk | Environment variable |
|---|---|---|---|
| Session pooler | **Session pooler** (host `...pooler.supabase.com`, port `5432`) | koneksi runtime aplikasi | `DATABASE_URL` |
| Direct connection | **Direct connection** (host `db.<ref>.supabase.co`, port `5432`) | DDL — `prisma db push` | `DIRECT_URL` |

Ganti `[YOUR-PASSWORD]` dengan password dari Langkah 1 pada kedua URL.

### Langkah 3 — Terapkan skema ke Supabase (sekali, dari komputer Anda)

```bash
git clone https://github.com/anandategarch/Stock-Monitoring-Web.git
cd Stock-Monitoring-Web
bun install                       # atau: npm install
cp .env.example .env              # isi DATABASE_URL + DIRECT_URL (blok PRODUKSI)
bun run db:push:supabase          # membuat 14 tabel SM-WEB di Supabase
```

Selesai — cek di Supabase Dashboard → **Table Editor**: tabel `RunBatch`, `PeriodSnapshot`,
`SnapshotRow`, dst. sudah ada.

### Langkah 4 — Import repo ke Vercel

1. https://vercel.com/new → **Import Git Repository** → pilih `Stock-Monitoring-Web`
   (bila belum ada di daftar: add GitHub account/org).
2. Vercel mendeteksi **Next.js** otomatis — biarkan Build Command default
   (`bun run build` → menjalankan `prisma generate && next build`).
3. Buka **Environment Variables** dan tambah (centang Production + Preview + Development):

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Session pooler URL (Langkah 2) |
   | `DIRECT_URL` | Direct connection URL (Langkah 2) |

   `SM_ENGINE_URL` / `SM_ENGINE_PROD_URL` **tidak perlu** — tanpa keduanya, run demo
   memakai fallback embedded (§1).
4. **Deploy** — build pertama ± 2-3 menit.

### Langkah 5 — Isi data demo & verifikasi

1. Buka URL deployment → header menampilkan badge **“engine fallback”** (amber) — normal
   di Vercel.
2. Tab **⚙️ Config & Admin** → **Isi data demo (2 periode)** → sukses menulis snapshot
   ke Supabase (lihat juga di Supabase Table Editor: `PeriodSnapshot` berisi 2 baris ACTIVE).

   > Bila database Anda sudah berisi 2 periode demo dari **seed pra-deploy** (diisi sebelum
   > import ke Vercel), tombol ini menolak dengan pesan "sudah ada snapshot aktif" (HTTP 409)
   > — itu perilaku yang benar, data sudah ada dan tidak perlu diulang.
3. Jelajahi semua tab — Pivot, Deviasi GR/PCS, Selisih IN, Nominal, Laporan (Komparasi),
   Follow-Up, Rincian PO, Kualitas Data semuanya hidup dari data snapshot.

### Troubleshooting deploy

| Gejala | Sebab & solusi |
|---|---|
| Build gagal di `prisma generate` / `Environment variable not found` | `DATABASE_URL`/`DIRECT_URL` belum terisi di Vercel Environment Variables — tambahkan lalu **Redeploy**. |
| `P1001: Can't reach database` | Salah region/host di URL — pastikan pakai string dari tab **Session pooler** project yang benar; password mengandung karakter khusus harus di-URL-encode. |
| Error `prepared statement` saat runtime | Anda memakai **Transaction pooler** (port `6543`) — ganti ke **Session pooler** (port `5432`). Bila terpaksa transaction mode: tambahkan `?pgbouncer=true&connection_limit=1` ke `DATABASE_URL`. |
| `bun run db:push:supabase` gagal connect | Direct connection perlu IPv4 addon di beberapa jaringan, atau coba dari mesin dengan IPv6 — Supabase juga menyediakan **Session pooler** sebagai `DIRECT_URL` alternatif untuk DDL. |
| Badge “engine mati” (merah) | Fallback embedded dimatikan (`SM_ENGINE_EMBED_FALLOFF=off` di env Vercel) — hapus variabel tersebut, atau host engine (§5). |
| Halaman terbuka tapi semua tabel kosong | Belum ada snapshot — jalankan **Isi data demo** (Config) atau ingest bundle real dari self-host. |
| Tombol **Isi data demo** menolak (409 "sudah ada snapshot aktif") | Guard anti-campur: seed hanya untuk database kosong. Bila `PeriodSnapshot` sudah berisi baris ACTIVE, data demo sudah tersedia. Untuk mengulang dari nol: hapus periode lewat tab **Config & Admin** terlebih dahulu. |

---

## 4. Environment variables

| Variabel | Wajib? | Default | Keterangan |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | SQLite `file:` (dev) **atau** PostgreSQL Supabase (prod). |
| `DIRECT_URL` | ✅ (prod PG) | — | Koneksi direct untuk DDL Prisma (skema kanonik `postgresql`). |
| `SM_ENGINE_URL` | — | `http://127.0.0.1:3030` | Engine DEMO service. |
| `SM_ENGINE_PROD_URL` | — | `http://127.0.0.1:3031` | Engine PRODUKSI FastAPI (ingest bundle real). |
| `SM_ENGINE_EMBED_FALLBACK` | — | `on` | `off` = matikan fallback embedded demo. |

---

## 5. Engine service

### 5.1 Engine DEMO (`mini-services/engine`)

Generator sintetis deterministik kontrak-identik — data pelatihan/seed. Jalan sebagai
service Bun port tetap 3030, **atau otomatis via fallback embedded** bila service mati.

### 5.2 Engine PRODUKSI (`mini-services/engine-fastapi`) — pipeline asli v3.9.71

FastAPI membungkus `src/` pipeline v3.9.71 **apa adanya** (0-rewrite, FR-10);
`golden_check.py` = gerbang paritas (65/65 PASS atas fixture `test_mock.py`).

```bash
# lokal
cd mini-services/engine-fastapi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bun run dev            # uvicorn :3031 (hot reload)
```

**Hosting cloud (untuk ingest bundle real)** — deploy `mini-services/engine-fastapi`
dengan `Dockerfile` yang tersedia (Railway / Fly.io / Render / VPS):

```bash
docker build -t sm-engine-fastapi mini-services/engine-fastapi
docker run -p 3031:3031 sm-engine-fastapi          # PORT env dihormati (default 3031)
```

Lalu di host Next.js (bukan Vercel — lihat §1): set `SM_ENGINE_PROD_URL` ke URL engine.
**Catatan**: unggah bundle ZIP dari UI memerlukan Next.js & engine di-host dengan
filesystem yang sama (self-host). Pola yang disarankan: satu VPS/Railway service untuk
Next.js + engine co-located + volume persisten untuk `bundles/`.

### 5.3 Kontrak engine

Semua komunikasi Next.js ↔ engine mengikuti `docs/ENGINE-CONTRACT.md` (JSON v1,
idempotent FR-12). Next.js adalah satu-satunya penelepon engine — browser tidak pernah
memanggil engine langsung.

---

## 6. Struktur repo

```
prisma/schema.prisma            kanonik PostgreSQL/Supabase (14 model)
prisma/schema.sqlite.prisma     cermin dev (GENERATED — sync otomatis)
scripts/sync-prisma-schemas.mjs generator cermin
mini-services/engine/           engine DEMO (Bun, port 3030)
mini-services/engine-fastapi/   engine PRODUKSI (FastAPI :3031, pipeline v3.9.71 vendored)
src/app/api/**                  23 endpoint (ingest→preview→komit, analisis, follow-up, setting, audit)
src/components/smweb/**         shell + 11 tab (satu rute "/" — navigasi internal)
src/lib/                        db, engine client + fallback embed, snapshot-service, kontrak tipe
docs/                           PRD · ARCHITECTURE · ENGINE-CONTRACT
```

---

## 7. Catatan teknis

- `next.config.ts` sengaja **tanpa** `output: "standalone"` (Vercel tidak mendukung).
  Self-host memakai `next build` + `next start` (script `start` menghormati `$PORT`).
- Build Vercel menjalankan `prisma generate` (klien PostgreSQL) otomatis via script `build`.
- Single-user tanpa login (D-6) — untuk melindungi deployment publik, aktifkan
  **Vercel Authentication/Password Protection** di project settings, atau tarik di
  belakang proxy internal.
- Angka qty/nominal memakai `Float` (aturan portabilitas SQLite↔PG); saat butuh
  presisi desimal ketat di PostgreSQL, upgrade ke `Decimal` lewat migrasi tersurat
  (ARCHITECTURE.md §6).

## 8. Roadmap

Fase & status di `docs/PRD-STOCK-MONITORING-WEB.md` §10 — Fase 0 (fondasi) ✅,
Fase 1 (engine produksi + ingest + snapshot store) berjalan, Fase 2+ (halaman kerja
lanjutan, golden-file bundle real, benchmark antar-periode, konsolidasi IC) menyusul.
Riwayat implementasi: sesi kerja sandbox terdokumentasi di worklog internal.
