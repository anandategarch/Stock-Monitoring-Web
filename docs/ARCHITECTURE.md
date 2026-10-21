# ARCHITECTURE.md — Stock Monitoring Web (SM-WEB)

> Deliverable Fase 0 (PRD §10). Pendamping: `docs/PRD-STOCK-MONITORING-WEB.md` (v1.1 — keputusan
> D-5/D-6/D-8 disahkan) dan `docs/ENGINE-CONTRACT.md` (kontrak JSON engine v1 — sumber kebenaran).
> Prinsip: **kualitas data → snapshot store → analisis → tindak lanjut** (PRD §10).

## 1. Keputusan arsitektur yang mengikat

| # | Keputusan | Nilai | Sumber |
|---|---|---|---|
| K-1 | Pipeline TIDAK di-port ke TypeScript | Engine service (produksi: FastAPI + `src/pipeline/*` 0-rewrite) di belakang Next.js | PRD §8.1 opsi B |
| K-2 | Database produksi | **Supabase PostgreSQL — project TERPISAH dari IC** (D-5 ✅); sandbox dev: SQLite via Prisma, skema portabel | PRD D-5 |
| K-3 | Model data single-user | Tanpa login Fase 1–3 (D-6 ✅); `actor` default `"analyst"`; AuditLog tetap jalan | PRD D-6 |
| K-4 | Repo | BARU terpisah dari IC (D-8 ✅); basis kode sandbox ini = calon repo `Stock-Monitoring-Web` | PRD D-8 |
| K-5 | Grain snapshot | **periode × resto × barang × satuan × hari** (D-1 final di Fase 0); agregat H/minggu dihitung saat query | PRD FR-20 |
| K-6 | Desktop | Dual-track tetap hidup sampai exit Fase 3 + 1 siklus penuh (D-7) | PRD D-7 |

## 2. Topologi

### 2.1 Sandbox (lingkungan pengembangan ini)

```
Browser ──► Gateway Caddy :81 ──┬── default ──► Next.js 16 (port 3000)
                                └── ?XTransformPort=N ──► localhost:N
Next.js (server, /api/*) ──┬──► Engine DEMO    http://127.0.0.1:3030 (mini-services/engine, Bun)
                           └──► Engine PRODUKSI http://127.0.0.1:3031 (mini-services/engine-fastapi,
                                FastAPI + pipeline Python v3.9.71 vendored di src/ — 0-rewrite FR-10)
Next.js ──► Prisma ──► SQLite db/custom.db
Unggahan ZIP bundle (FR-1) ──► bundles/{bundleId}/ (ekstrak+validasi) ──► bundlePath → engine produksi
```

- Browser **hanya** relative path; tidak pernah menyebut port/absolute URL (aturan platform).
- Browser **tidak pernah** memanggil engine langsung; semua lewat API Next.js.
- Pemilihan engine per-run: ada `bundleId` → `SM_ENGINE_PROD_URL` (:3031); else → `SM_ENGINE_URL` (:3030).

### 2.2 Produksi (target)

```
Vercel ── Next.js 16 (repo baru D-8)
           ├── API /api/* (Prisma → Supabase PostgreSQL, project BARU khusus SM-WEB — D-5)
           ├── run DEMO → fallback EMBEDDED (generator kontrak-identik in-process; §2.3)
           └── run bundle real → engine FastAPI co-located (Railway/VPS, pola mini-service IC)
                (Vercel murni: unggah bundle belum tersedia — filesystem ephemeral; lihat README §5.2)
Supabase PostgreSQL — PROJECT BARU khusus SM-WEB (D-5: TERPISAH dari IC; konsolidasi Fase 5 via API antar-app)
Desktop v3.9.x tetap dirilis (dual-track D-7) → dasar golden-file paritas
```

### 2.3 Fallback embedded (deploy tanpa engine co-located)

`src/lib/engine-embed.ts` — bila service engine DEMO tidak terjangkau, run tanpa
`bundleId` diproses generator `mini-services/engine/generator` **di dalam proses Next.js**.
Kode generator identik ⇒ hasil deterministik sama (FR-12 tetap sahih: process via service,
commit via embedded = snapshot konsisten). Run bundle real TIDAK PERNAH di-fallback (NFR-3).
Status jujur di UI: badge header "engine fallback" (amber) + kartu Config amber.
Matikan: `SM_ENGINE_EMBED_FALLBACK=off`. Runbook lengkap: `README.md` §3.

## 3. Komponen

| Komponen | Lokasi | Peran |
|---|---|---|
| Engine service (demo) | `mini-services/engine/` | Generator sintetis deterministik, kontrak-identik; `engineKind:"demo"`; port 3030 |
| Engine service (PRODUKSI) | `mini-services/engine-fastapi/` | FastAPI membungkus `src/` pipeline v3.9.71 apa adanya (FR-10, port 3031); `mapper.py` = DataFrame→EngineResult; `ports/` = salinan verbatim `doc_codes`+`nominal_common`; `golden_check.py` = gerbang AC-B (65/65) |
| Client engine | `src/lib/engine.ts` | Server-only; `SM_ENGINE_URL` (:3030 demo) + `SM_ENGINE_PROD_URL` (:3031 produksi); timeout + pesan error jelas |
| Registry bundle | `src/lib/bundles.ts` | Ekstrak+validasi ZIP (FR-1), meta manifest per folder config.json (FR-2), resolve bundleId→path |
| API Next.js | `src/app/api/**` | Semua logika server: ingest→preview→komit, query analisis, follow-up, setting, audit |
| Skema Prisma | `prisma/schema.prisma` | Snapshot store + run + DQ + follow-up + setting/audit (lihat §5) |
| State klien | `src/store/` (Zustand) | Tab aktif, periode aktif, filter (GR/PCS, H, ambang ACR, resto) — persist per sesi (INV-8) |
| Server-state | TanStack Query | Semua fetch `/api/*` |
| UI | `src/components/smweb/` | Shell + 11 tab paritas (Ikhtisar, Proses, Pivot, Deviasi, Selisih IN, Nominal, Laporan, Follow Up, Rincian PO, Kualitas Data, Config) |
| Tema | `next-themes` | Light/dark; basis netral + aksen emerald/amber/rose (tanpa indigo/biru) |

## 4. Alur data inti

### 4.1 Ingest → Preview → Komit (FR-3/FR-4)

```
POST /api/ingest/process {periodKey, tanggalH, ambangAcrPct, bundleName}
  → buat RunBatch (status engine, definition_version, params)
  → simpan summary/log/sourceFiles + DQIssue (menempel runBatch, belum komit)
  → UI menampilkan pratinjau (ringkasan + DQ) — TIDAK menimpa snapshot lama
POST /api/ingest/commit {runBatchId}
  → panggil ulang engine /process DENGAN PARAMETER SAMA (FR-12 idempotent → hasil identik)
  → snapshot ACTIVE periode lama → SUPERSEDED (FR-24 immutable)
  → buat PeriodSnapshot + bulk SnapshotRow + PriceHistory + SelisihInResto + PoHeader/Item
  → AuditLog "SNAPSHOT_COMMIT"
```

### 4.2 Analisis (semua baca snapshot, INV-7 drill-down)

`/api/snapshots/[id]/pivot · deviasi · drilldown · selisih-in · nominal · laporan · po · dq`
— server mengagregasi; klien hanya menampilkan (tidak menghitung ulang domain, kecuali
label "ACR to BOM" yang sengaja re-komputasi live saat ambang ACR diubah — FR-30).

### 4.3 Follow-Up 2.0 (FR-40..44)

`FollowUpCase` (fingerprint stabil = md5(resto|barang|satuan|kategori) — FR-22, TANPA kolom cek/qty)
+ `FollowUpEvent` (timeline siapa/kapan/status/alasan/PIC/qty temuan) + transisi tervalidasi
`PENDING→DIPROSES→SELESAI/DIBATALKAN` + reopen. Setiap transisi → AuditLog.

## 5. Model data (skema final Fase 0 — prisma/schema.prisma)

| Entitas | Peran kunci | FR/INV |
|---|---|---|
| `RunBatch` | 1 run = 1 batch; status, definitionVersion, paramsJson, log; `committedAt=null` ⇒ hanya pratinjau | FR-5/11, INV-4 |
| `PeriodSnapshot` | Periode terkomit; state ACTIVE/SUPERSEDED; totals; immutable | FR-20/24 |
| `SnapshotRow` | Grain hari; 10 metrik `Float?` — **null = missing (INV-1)**, deviasi bertanda (INV-2); `cekJson` (JSON string — portabel SQLite↔PG); `fingerprint` stabil | FR-20/21/22 |
| `PriceHistory` | Harga 41.09 per barang per run (D-2: simpan sejak Fase 1) | FR-23 |
| `SelisihInResto` | IN vs BM + Hasil Audit + SKOR RESTO per resto | FR-33 |
| `PoHeader`/`PoItem` | Rincian PO + status 32.43 + anotasi ↳ | FR-36 |
| `DQIssue` | severity/code(10 kelas)/message/source/sheet/row; menempel runBatch atau snapshot | FR-60, INV-6 |
| `FollowUpCase`/`FollowUpEvent` | Kasus stabil lintas-periode + timeline | FR-40..43 |
| `OutletPIC` | PIC per outlet (dropdown FR-42) | FR-42 |
| `Setting` | config.json replika (tanggalH default, ambang ACR default, dll) — valueJson | FR-2/80 |
| `AuditLog` | semua aksi tulis (siapa/kapan/apa) | NFR-4 |
| `SourceFile` | manifest file per folder (pratinjau FR-1) | FR-1 |
| `TransferLedger4215` | DISEDIKAN Fase 5 (FR-50..52) — belum dipakai | FR-50..52 |

Denormalisasi sengaja: master resto/barang hidup di dalam `SnapshotRow` (restoCode/restoName/itemName/
satuan/kategori/isGR); model master terpisah menyusul saat fitur benchmark (F6) benar-benar dibangun —
menghindari duplikasi kebenaran di Fase 0/1.

## 6. Kebijakan database: SQLite (dev) → Supabase PostgreSQL (prod)

- **Kanonik**: `prisma/schema.prisma` = provider `postgresql` + `directUrl = env("DIRECT_URL")`
  (DDL via koneksi direct Supabase; runtime via `DATABASE_URL` pooler). Terapkan ke Supabase:
  `bun run db:push:supabase`.
- **Cermin dev**: `prisma/schema.sqlite.prisma` digenerate otomatis oleh
  `scripts/sync-prisma-schemas.mjs` (dipanggil `bun run db:push` / `db:generate`) —
  satu sumber kebenaran model, dua target provider. Jangan edit cermin manual.
- Skema hanya memakai tipe portabel: `String/Int/Float/Boolean/DateTime` + **JSON string** untuk
  list/objek (larangan array Prisma di SQLite tetap dipatuhi). Tanpa atribut `@db.*` spesifik vendor.
- `Float` dipakai untuk qty/nominal (SQLite tidak dukung `Decimal`); saat pindah PG, upgrade
  `nominal/harga` ke `Decimal @db.Decimal(14,2)` boleh dilakukan sebagai migrasi tersurat.
- Runbook pembuatan project Supabase + env Vercel: `README.md` §3.

## 7. Peta file (Fase 0/1 sandbox)

```
prisma/schema.prisma              — skema final (§5)
mini-services/engine/index.ts     — engine demo (kontrak v1), port 3030
mini-services/engine-fastapi/    — engine PRODUKSI (port 3031): app.py (FastAPI), mapper.py,
                                     src/ (pipeline v3.9.71 vendored), ports/ (doc_codes +
                                     nominal_common verbatim), fixtures.py (port create_mock_*),
                                     golden_check.py (gerbang AC-B), config_template.json (FR-2)
src/lib/db.ts                     — klien Prisma (global)
src/lib/engine.ts                 — client engine (server-only; demo + produksi)
src/lib/bundles.ts                — registry bundle unggahan ZIP (FR-1)
src/lib/types.ts                  — tipe kontrak + tipe API (cermin ENGINE-CONTRACT.md)
src/lib/format.ts                 — format id-ID (1.234,5 · minus merah · "—" untuk NA)
src/lib/cek.ts                    — konstanta CEK + re-komputasi ACR to BOM live
src/lib/fingerprint.ts            — md5(resto|barang|satuan|kategori)
src/app/api/**                    — endpoint per §4
src/store/use-sm-store.ts         — Zustand (tab, periode, filter)
src/components/providers.tsx       — QueryClient + Theme + Toaster (sonner)
src/components/smweb/**            — shell + tab (satu rute "/" — navigasi internal, aturan platform)
```

## 8. Keamanan & observabilitas

- Secret hanya via env (`DATABASE_URL`, `DIRECT_URL`, `SM_ENGINE_URL`, `SM_ENGINE_PROD_URL`,
  `SM_ENGINE_EMBED_FALLBACK`) — NFR-4; tidak ada hardcode.
- AuditLog: commit, setting-ubah, follow-up transisi, seed/hapus periode.
- Semua kegagalan engine → status jujur di UI (banner status + tombol coba lagi); run gagal
  tidak pernah menyentuh snapshot lama (NFR-3).
- Lint (`bun run lint`) + verifikasi browser (Agent Browser) = gerbang kualitas sandbox;
  gerbang produksi (pytest subset 1607 + golden-file) aktif saat repo GitHub + CI dibuat (Fase 1).

## 9. Status fase (jejak)

| Fase | Status | Catatan |
|---|---|---|
| 0 — Fondasi | ✅ Sandbox | PRD v1.1 SAH; ARCHITECTURE + kontrak engine v1 + skema final. Item di luar sandbox: repo GitHub baru (D-8, aksi user) + project Supabase baru (D-5, aksi user) |
| 1 — Engine + Ingest + Snapshot | 🟧 Lanjut | Engine DEMO + **ENGINE PRODUKSI FastAPI TERPASANG (:3031, 0-rewrite FR-10) + unggah ZIP bundle (FR-1) + gerbang AC-B LULUS 65/65 atas fixture test_mock**. Sisa: golden-file atas bundle REAL (aksi user: unggah bundle export aktual), migrasi followup.json asli |
| 2 — Halaman kerja inti | 🟧 Kerangka | Pivot/Deviasi/detil drill-down dibangun di atas snapshot demo |
| 3+ | ⬜ Menunggu | Sesuai PRD §10 |
