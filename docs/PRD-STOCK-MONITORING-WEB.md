# PRD — Stock Monitoring Web (SM-WEB)

> **Product Requirements Document** — Migrasi & unifikasi `Stock-Monitoring` (desktop Python/Tkinter v3.9.71) ke platform web, di atas fondasi repo `Inventory-Control`.
> Status: **v1.1 — IMPLEMENTASI DIMULAI.** 3 keputusan DISAHKAN pemilik produk 2026-10-21 (D-5: Supabase **database terpisah** dari IC · D-6: **single-user** tanpa login · D-8: **repo baru** terpisah dari IC); D-1..D-4 & D-7 menjalankan rekomendasi PRD kecuali dinyatakan lain. **Fase 0 selesai & Fase 1 dimulai 2026-10-21 di sandbox** (jejak: worklog Task 35–42): `ARCHITECTURE.md` + kontrak engine v1 + skema Prisma final (13 model) + engine DEMO kontrak-identik (port 3030) + 23 API route + 11 halaman kerja paritas + snapshot store hidup (3 periode demo terkomit). **Task 43 (2026-10-21): ENGINE PRODUKSI FastAPI TERPASANG** (`mini-services/engine-fastapi` :3031 — pipeline asli v3.9.71 dibungkus APA ADANYA, FR-10 0-rewrite) + unggah ZIP bundle (FR-1) + gerbang AC-B **LULUS 65/65** atas fixture `test_mock.py`; paritas golden-file penuh menunggu bundle export real pemilik produk.

| Atribut | Nilai |
|---|---|
| **Nama produk (proposisi)** | Stock Monitoring Web (SM-WEB) — repo BARU terpisah dari IC (D-8 SAH); nama final menyusul |
| **Dokumen** | PRD prospektif (what & why + kerangka how). Untuk sejarah implementasi baca `worklog.md`; untuk arsitektur detail menyusul `ARCHITECTURE.md` saat Fase 0 dimulai |
| **Pemilik produk** | Inventory Control Analyst (pemilik kedua repo, single-user saat ini) |
| **Basis kode sumber** | `anandategarch/Stock-Monitoring` — desktop, tag `v3.9.71`, commit `f22bca6`, 1607/1607 tes PASS, 2 gerbang CI hijau (tests + build EXE) |
| **Platform referensi** | `anandategarch/Inventory-Control` — Next.js 16 App Router + React 19 + Prisma 6/PostgreSQL (Supabase) + Tailwind 4/shadcn + Recharts + Zustand + TanStack Query; 12 model Prisma warehouse mingguan sudah live |
| **Ditulis / diperbarui** | 2026-10-21 (WIB) — v1.1: D-5, D-6, D-8 disahkan pemilik produk |
| **Cara baca** | Setiap klaim kondisi-app ("ADA/TIDAK ADA") di dokumen ini sudah **diverifikasi ke kode nyata** (worklog Task 29–32: 3 agen riset + spot-check; lihat Lampiran D jejak verifikasi) |

---

## 1. Ringkasan Eksekutif

`Stock-Monitoring` desktop saat ini menghitung **deviasi persediaan** (SO − Saldo Akhir, dalam satuan terkecil bertanda, per resto × barang × tanggal) langsung dari **export mentah Accurate** (22.05, 32.24, 42.05, 42.15, 42.17, 41.09, 9901, rekap), memutuskannya lewat 10 tab Tkinter, dan **tidak menyimpan hasil perhitungan antar-periode** — satu-satunya "memori" multi-bulan adalah file deviasi eksternal yang di-maintain manual di luar app dan dibandingkan lewat tab Komparasi.

`Inventory-Control` (repo web user yang sudah live) adalah lapisan **analisis** dari file laporan deviasi resmi yang sama — dengan data warehouse mingguan (54.000+ record/periode, 333 outlet, 14 area), deteksi anomali 19-rule, drill-down, benchmark antar-outlet, dan AI narrative — namun **tidak menghitung apa pun dari export mentah Accurate**; ia menerima angka yang sudah jadi.

**Dua produk ini adalah dua lapisan dari satu domain yang sama.** PRD ini mendefinisikan produk web yang menyatukan keduanya:

1. **Lapisan hitung** (sekarang di desktop): pipeline pandas murni 16 modul — *tidak ditulis ulang*, dibungkus menjadi **engine service Python (FastAPI)** yang berjalan di belakang aplikasi web.
2. **Lapisan simpan** (belum ada di mana pun): **snapshot store per periode** — hasil run (deviasi per resto×barang×hari, metrik pivot 10-jenis, nominal, label pemeriksaan CEK, sinyal kualitas data) disimpan permanen ke database, merekam **versi definisi deviasi** yang dipakai. Ini sekaligus menutup gap terverifikasi Task 31: *"snapshot store TIDAK ada"* — prasyarat 6 dari 8 fitur roadmap analisis.
3. **Lapisan tampil & tindak lanjut**: UI web tab-arah-kerja (10 tab desktop → halaman web), termasuk **Follow-Up 2.0** (status, PIC, tanggal, alasan, riwayat) yang hari ini hanya centang ✓ tanpa jejak waktu.

**Keputusan arsitektur inti**: JANGAN port 39 ribu baris logika teruji ke TypeScript (risiko drift logika + pembuangan aset 1607 tes). Pipeline `src/pipeline/` sudah UI-agnostic (pandas murni tanpa import Tkinter — terverifikasi Task 32), cukup dibungkus service. Desktop **tetap dirawat dual-track** selama transisi (opsi D-7, §14).

Estimasi cakupan: fondasi ~70% sudah tersedia dari Inventory-Control (auth scaffolding NextAuth, pola ingest + chunked upload, skema warehouse, DQIssue, AuditLog, OutletPIC, infra mini-service Python, CI). Pekerjaan baru utama: kontrak engine service, skema snapshot store + versi definisi, 10 UI paritas, follow-up ber-riwayat.

---

## 2. Latar Belakang

### 2.1 Kondisi saat ini — desktop (as-is, terverifikasi v3.9.71)

**Perangkat**: aplikasi Windows satu-pengguna (PyInstaller onedir, rilis otomatis via GitHub Actions), Python 3 + Tkinter + pandas 2.x, ~39,4 ribu baris di `src/` (16 modul `pipeline/` + 20 modul `ui/`), 1607 tes, ruff baseline ≤201, screenshot harness otomatis.

**Alur kerja pengguna** (semua di satu PC, offline):
1. Export mentah Accurate Online → folder Windows `C:\KERJA\1. RESTO\9.NEW QUERY\` (15 folder sumber didefinisikan `config.json`: RekapBerjalan, RekapLalu, Penjualan2205, Kirim4215, Terima4215*, RI3224, RI3224Lalu, SaldoAwal4217, DBSKategori, Pemindahan4205, Pemindahan4205Lalu, RincianPO, Data9901, Harga — *folder Terima4215 ada di config tapi tak pernah dibaca kode).
2. Buka app → tab 🚀 Proses → jalankan pipeline → 10 modul pembaca menghasilkan frame pandas → `append1` membangun pivot 10 metrik (SALDO AWAL, 1.SO, 2.SALDO AKHIR, 3.DEVIASI, 4.IN, 5.BARANG MASUK, 6.PEMAKAIAN (COM), 7.Selisih IN, 8.BARANG KELUAR, 9.ACR) → semua tab terisi.
3. Analisis lintas tab, input **TANGGAL H** (cut-off mingguan 7/14/25), atur **AMBANG ACR** (default 80%), baca 9 label CEK + Catatan Audit B1–B4, centang baris anomali → tab ☑ Follow Up → export Excel untuk dikerjakan TL outlet.

**Model data in-memory** (satu run = satu bulan berjalan + ekor bulan lalu hari 25–31):

- `Deviasi = SO − SALDO AKHIR`, satuan terkecil rekap, **bertanda** (minus = kekurangan).
- `SALDO AKHIR = SALDO AWAL (42.17) + IN − OUT − BARANG KELUAR`; `IN = 42.05 + 32.24 + 99.01`; `OUT = 22.05 tanpa kode SI` (sejak v3.9.71, case-sensitive); `BARANG KELUAR = 42.15 sisi kirim`.
- `Selisih IN = BARANG MASUK (rekap) − IN`; `ACR to BOM` = deviasi melebihi ambang% × Total ACR; harga efektif = 41.09 (Nilai ÷ Kuantitas saldo akhir, global per barang, dinormalkan satuan via rasio rekap/41.09).
- `Nominal Deviasi = Harga × Qty Deviasi` per pasangan; pasangan qty≠0 tanpa harga → daftar **Tanpa Harga** (alasan: tak ada di 41.09 / satuan tak terkonversi, penanda `*`).

**10 tab** (struktur Notebook terverifikasi `app.py:2575-2586`):

| # | Tab | Isi inti |
|---|---|---|
| 1 | ⚙️ Config | RootPath, folder/sheet mapping, validasi defensif |
| 2 | 🚀 Proses | Jalankan pipeline, log real-time, status SELESAI / DENGAN PERINGATAN / PARSIAL |
| 3 | 📊 Pivot Table | Matriks Excel-like per resto/tanggal, 10 metrik JENIS, freeze kolom nama barang (v3.9.71), filter persist |
| 4 | 📦 Deviasi GR | Wide matrix + 9 label CEK + kolom ✓ (one-stop input TANGGAL H + AMBANG ACR) + Nominal + Rank per-baris |
| 5 | 🧩 Deviasi PCS | Sama, untuk barang non-GR |
| 6 | 📤 Rekap Selisih IN | IN (Accurate) vs Barang Masuk + SO + Hasil Audit (port macro VBA) + 🏆 SKOR RESTO + drill-down |
| 7 | 📋 Laporan Deviasi | 3 mode: ⚖ Komparasi file deviasi eksternal (default) / 🚨 Anomali COM / 💰 Nominal (H) |
| 8 | 🧮 Nominal Deviasi | Σ nominal per resto + TOTAL + anak tab Tanpa Harga (global) + COM Deviasi/Biaya Packaging/% naik-turun |
| 9 | ☑ Follow Up | Baris anomali tercentang (snapshot 17 field + fingerprint md5) + export Excel |
| 10 | 🛒 Rincian PO | Rekap PO + item, status pesanan (32.43), anotasi ↳ Status, filter CABANG/STATUS |

**9 label CEK** (blok kanonik `deviasi_view.py:2209-2216`, kondisi persis diverifikasi Task 31-a): RI Balancing (26→25 Nomor RI vs Nomor PO), Beda Tanggal (port persis formula LET `01.1 CEK STOCK V2.xlsb` kolom Y), Promix 04, Kosong/Non Aktif, Hitung Manual, Turun Drastis, ACR to BOM, + **Catatan Audit B1–B4**; plus **PO Menunggu** (fn_audit, status "menunggu diproses") dan **Selisih IN** di tab 📤.

**Aset kualitas**: 1607 tes (unit + UI smoke Xvfb + mock fixture ground-truth: 1379 cek UI + mock, termasuk kontrak §82b pola warning & §84 freeze-pane), CI 2 gerbang, README changelog rinci per versi, baterai verifikasi "output identik" untuk mutasi format Excel (v3.9.67).

### 2.2 Keterbatasan terverifikasi (mengapa harus berubah)

Dari audit roadmap Task 31 (3 agen riset, semua dikonfirmasi ke kode):

1. **Snapshot store TIDAK ada.** Semua titik tulis terinventarisasi: `settings.json` (window/filter/zoom), `config.json` (path), `followup.json` (centang manual), `komparasi_last.json` (hanya path file), `crash.log`, export Excel manual. Tidak ada arsip hasil per periode yang menumpuk otomatis → **riwayat multi-bulan hanya bisa dari file eksternal yang user susun sendiri**, dan file itu pun tanpa harga per minggu (hanya nominal resmi).
2. **Definisi deviasi tidak stabil lintas versi**: v3.9.69 (OUT = ACR-only) → v3.9.70 (semua kode) → v3.9.71 (tanpa SI). Setiap snapshot historis di masa depan WAJIB merekam versi definisi — kalau tidak, perbandingan antar-periode membandingkan apel dengan jeruk.
3. **Follow-up tanpa jejak waktu**: hanya boolean pending/resolved per fingerprint; tidak ada timestamp perubahan status, tanggal selesai, alasan, riwayat/reopen; PIC hanya ada di skema legacy `followup_resolved.json` yang writer-nya dihapus sejak v3.8 (fitur Impor Hasil TL) — tak ada jalur input PIC dari UI.
4. **Fingerprint volatil**: kunci identitas baris memuat kolom `cek` → baris yang sama bisa berubah fingerprint hanya karena ambang ACR atau file bulan-lalu berubah → centang lama "hilang senyap" (mitigasi parsial "cek-dinetralkan" sudah ada, tapi identitas lintas-periode tetap rapuh).
5. **42.15 (transfer antar-outlet)**: sheet mentah memuat `Gudang Pengirim` + `Gudang Tujuan` + `Tanggal` + `Kts Diterima` per baris — tapi app hanya membaca **sisi kirim** dan membuang kolom tujuan; folder config `Terima4215` ada tapi tak pernah di-wire; **tidak ada nomor dokumen** yang dibaca → pencocokan kirim↔terima belum mungkin berbasis nomor dokumen.
6. **Prinsip missing≠0 belum konsisten**: engine jujur (NaN = tidak ada), tapi pivot mirror M tetap `fillna(0)` → sel "tidak ada data" dan "benar-benar nol" tampil sama.
7. **Single-user & terikat PC Windows**: kolaborasi TL outlet hanya lewat export Excel manual; tidak ada akses mobile; tidak ada audit trail siapa mengubah apa.

### 2.3 Mengapa web, dan mengapa fondasinya sudah 70% ada

Repo **Inventory-Control** user sudah memecahkan 4 dari 7 keterbatasan di atas di level platform:

| Keterbatasan desktop | Sudah tersedia di Inventory-Control |
|---|---|
| (1) Snapshot store tidak ada | Skema warehouse: `SourceFile → Week → InventoryRecord` (48 field, per minggu×outlet×item), `OutletPeriodSales`, `AggregationCache` — tinggal diperluas (§8.4) |
| (7) Single-user tanpa audit | `AuditLog` (action/detail/duration), `OutletPIC`, `Setting`; NextAuth wired (belum diekspos) |
| Kualitas data tersebar di log console | `DQIssue` (severity/code/message/rawValue/rowNumber) sudah jadi tabel first-class + panel |
| Distribusi hasil ke TL outlet | Web responsive, upload/import/delete cepat, export PDF |

Yang **belum** ada di Inventory-Control (dan menjadi pekerjaan PRD ini): lapisan hitung dari export mentah Accurate (pipeline), label CEK 9-jenis, Selisih IN/Hasil Audit, TANGGAL H/AMBANG ACR interaktif, follow-up ber-riwayat, dan paritas 10 tab kerja.

**Mengapa sekarang**: roadmap 8-fitur analisis (Task 31) terblokir hampir seluruhnya oleh absennya snapshot store — 6 fitur (deviasi kronis, dekomposisi nominal, baseline anomali, benchmark antar-resto, efektivitas follow-up, peringatan dini) membutuhkan histori terstruktur. Migrasi web adalah **prasyarat teknis** roadmap, bukan hanya kenyamanan.

---

## 3. Tujuan Produk

### 3.1 Visi

> Satu platform web tempat analis memproses export Accurate, membaca deviasi terpercaya (dengan jejak definisi), menindaklanjuti anomali bersama TL outlet — dan seluruh riwayat periodenya tersimpan sehingga analisis lanjutan (kronis, tren, benchmark, prediktif) tinggal query database, bukan susun Excel manual.

### 3.2 Goals (target 12 bulan setelah Fase 1 rilis)

| # | Goal | Ukuran keberhasilan |
|---|---|---|
| G-1 | Paritas fungsi inti desktop: seluruh perhitungan & 10 tab dapat direproduksi di web dari bundle export mentah yang sama | Golden-file test: output web ≡ output desktop pada bundle yang sama (lihat §11) |
| G-2 | Riwayat permanen: setiap run menghasilkan snapshot periode yang tersimpan & dapat di-query ulang kapan pun | Snapshot bulan N dapat dibuka ulang tanpa file sumber; retensi ≥ 24 bulan |
| G-3 | Follow-up ber-riwayat & multi-pelaku | Setiap perubahan status tercatat (siapa/kapan/apa/alasan); kasus dapat ditutup & dibuka kembali |
| G-4 | Waktu siklus audit berkurang | Dari export→laporan manual lintas-app menjadi satu alur di web; target laporan bulanan siap < 1 hari setelah SO terakhir (baseline desktop: manual multi-langkah) |
| G-5 | Fondasi roadmap 8-fitur terpasang | 6 fitur yang terblokir snapshot store menjadi dapat dikerjakan langsung di atas tabel snapshot (F1–F8 mapping §6 Modul J) |
| G-6 | Kualitas & kepercayaan tetap | Baterai tes pipeline tetap hijau di CI web (port tanpa rewrite); setiap angka di UI dapat di-drill-down ke baris sumbernya |

### 3.3 Non-Goals (eksplisit — TIDAK dikerjakan di rilis pertama)

1. **Tidak men-rewrite pipeline ke TypeScript/SQL.** Pipeline pandas tetap Python, dibungkus service (alasan §8.1).
2. **Tidak mengubah cara kerja analisis di Inventory-Control yang sudah live** (19-rule, Z-score, heatmap, AI narrative) — SM-WEB justru memberi mereka data hitung baru; konsolidasi fitur ganda = Fase 5.
3. **Tidak membangun aplikasi mobile native.** Web responsive desktop-first, sama seperti Inventory-Control.
4. **Tidak men-drop aplikasi desktop** sebelum paritas & kepercayaan terbukti (dual-track; keputusan pensiun = D-7).
5. **Tidak membangun RBAC penuh multi-tenant** di rilis pertama — single-user + jejak audit dulu (keputusan D-6); outlet manager self-serve menyusul (paralel "Phase C" IC).
6. **Tidak mengubah format export Accurate** — input tetap "bundle folder mentah" apa adanya (ketahanan format by-design sudah teruji v3.9.67; kewajiban kompatibilitas lihat NFR-8).
7. **Tidak menambah fitur prediktif** di rilis pertama (Tahap 3 roadmap — setelah ≥ 6 bulan snapshot tersimpan).

### 3.4 Prinsip produk yang WAJIB dijaga (invariants — dilanggar = bug prioritas)

Ini perilaku domain yang sudah ditempa 71 versi dan ribuan verifikasi; semuanya menjadi kontrak tes di web:

| ID | Prinsip | Asal verifikasi |
|---|---|---|
| INV-1 | **Missing ≠ 0.** Tidak ada data bukan berarti nol. Sel NA tetap NA di engine; UI membedakan "—" vs 0. (Pivot mirror M desktop masih melanggar ini → di web DIPERBAIKI, lihat FR-16 & risiko R-4) | fn_audit.py:14-17, :156-158; Task 31-c |
| INV-2 | **Satuan terkecil bertanda.** Semua qty deviasi bertanda; minus = kekurangan; deviasi negatif adalah sinyal penting, tidak boleh disembunyikan/di-nol-kan | append1.py:498; v3.9.69 P1.1 |
| INV-3 | **Harga global 41.09 dinormalkan satuan** via rasio rekap/41.09; konversi gagal → penanda `*` + Nominal None (bukan angka salah) | nominal_common.py:237-283 |
| INV-4 | **Definisi deviasi terversi.** Setiap angka deviasi menyimpan `definition_version` (mis. "3.9.71-noSI"); perbandingan antar-periode hanya sah antar versi yang sama atau dengan penanda perbedaan | Task 31: v3.9.69→70→71 |
| INV-5 | **Degradasi per-sumber.** Satu file sumber rusak tidak mematikan run; baris NA + WARNING; status akhir jujur (SELESAI / DENGAN PERINGATAN / PARSIAL) | v3.9.67, v3.9.69 P1.2; kontrak §82b |
| INV-6 | **Observabilitas penuh.** Setiap anomali format (skip file, fallback-bind, VALUE/Tanggal hilang, konversi gagal, kategori kosong, duplikat) menghasilkan entri DQIssue yang dapat dilihat, bukan log senyap | 10 kelas sinyal Task 31-c |
| INV-7 | **Baris bisa dilacak.** Setiap angka agregat dapat di-drill-down ke baris sumber (dokumen/tanggal/qty) | details_popup, drill-down 📤 |
| INV-8 | **Filter & preferensi persist, tapi tidak pernah menimpa kerja user** (restore sekali per sesi, seleksi kosong = 0 baris jujur) | v3.9.66, v3.9.68 T1/T2 |
| INV-9 | **Bilangan bulat kecil = serius.** Ambang ACR default 80% (range 1–200) mengubah label CEK dan harus tampil di snapshot sebagai parameter run | SharedACRThreshold; settings acr_threshold_pct |

---

## 4. Pengguna & Persona

| Persona | Peran hari ini | Kebutuhan di SM-WEB | Fase |
|---|---|---|---|
| **"Anda" — Inventory Control Analyst (primary)** | Menjalankan desktop end-to-end sendiri: proses export, audit deviasi, susun laporan, kejar TL | Semua halaman; boleh tetap kerja sendiri dulu (single-user) tapi semua terekam audit trail; golden-file paritas untuk kepercayaan angka | 1–4 |
| **Team Leader / Manajer Outlet (sekunder, terdekat)** | Menerima export Excel follow-up via WA/email, mengisi status di Excel, balik file manual | Buka daftar follow-up outlet-nya sendiri, isi status/alasan/PIC, lihat deviasi outlet vs peer (nanti) — akses read+write terbatas outlet-nya | 4 (input), 5 (self-serve) |
| **Ops Manager (sekunder jangka menengah)** | Menerima laporan Word/Excel bulanan | Dashboard ringkas + laporan bulanan otomatis + tren antar-periode (dari snapshot) | 3–5 |
| **Auditor/Manajemen (tersier)** | Sesekali minta angka ad-hoc | Tautan share read-only periode × resto × barang dengan jejak definisi | 5 |

Asumsi skala (dari data live Inventory-Control + benchmark desktop): puluhan outlet (kode 6-huruf), ~100–300 barang per resto, pivot per run ~29 ribu baris-metrik, real-data benchmark grup information-level 80 ribu; retensi DB target ≥ 24 bulan.

## 5. User Journey (target, setelah Fase 2–4)

**J-1 Siklus bulanan (menggantikan alur desktop)**
```
Export Accurate (bundle folder) → halaman 📥 Ingest → upload ZIP/folder
  → engine service memproses (log real-time + status SELESAI/PERINGATAN/PARSIAL)
  → pratinjau DQIssue (skip file, kolom hilang, duplikat) → analis konfirmasi
  → snapshot periode TERKOMIT ke DB (definition_version + parameter run ikut tersimpan)
  → semua halaman analisis langsung memuat periode baru
```

**J-2 Audit mingguan (paritas desktop, ditambah histori)**
```
Buka halaman Deviasi (GR/PCS) → pilih H (cut-off 7/14/25) & ambang ACR
  → baca 9 label CEK + B1–B4 → sort/filter (persist) → klik baris → drill-down baris sumber
  → centang anomali → masuk Follow Up otomatis
  → bandingkan dengan minggu/bulan lalu DARI SNAPSHOT (bukan file eksternal lagi)
```

**J-3 Tindak lanjut kolaboratif (baru)**
```
TL outlet menerima tugas → buka halaman Follow Up ( outlet-nya )
  → isi status (proses/selesai/batal) + alasan + qty temuan fisik
  → analis melihat riwayat di timeline; kasus tertutup otomatis saat status selesai
  → KPI efektivitas follow-up (fitur F8 roadmap) dapat dihitung dari data nyata
```

**J-4 Laporan bulanan**
```
Halaman Laporan → pilih periode → ringkasan otomatis (nominal, top deviasi, tren vs bulan lalu)
  → export Excel (paritas format lama) / PDF → distribusi
```

---

## 6. Kebutuhan Fungsional

Konvensi: **Prioritas** — P0 = wajib rilis pertama yang berguna (Fase 1–2), P1 = paritas penuh desktop (Fase 3), P2 = keunggulan web / roadmap (Fase 4–6). Setiap FR punya acceptance criteria (AC) yang menjadi dasar tes.

### Modul A — Ingest & Sumber Data (halaman 📥)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-1** | Upload **bundle export mentah Accurate** (ZIP berisi struktur folder sesuai `config.json`: 15 folder sumber). Sistem memvalidasi struktur, menampilkan pratinjau file per folder (nama, jumlah, ukuran), lalu meneruskan ke engine. | P0 |
| **FR-2** | **Pemetaan folder/sheet dipertahankan** dari `config.json` desktop (RootPath/Folders/Sheets/KategoriBarang4217) sebagai `Setting` di DB, dapat dilihat & diedit admin web; bundle upload memakai pemetaan yang sama supaya hasil ≡ desktop. | P0 |
| **FR-3** | Progres & log real-time saat pipeline berjalan (paritas tab 🚀 Proses): baris log streaming, ringkasan akhir **SELESAI / SELESAI DENGAN PERINGATAN / SELESAI PARSIAL** + jumlah skip file + jumlah peringatan format (kontrak §82b: SEMUA literal WARNING pipeline wajib terhitung). | P0 |
| **FR-4** | **Hasil run TIDAK otomatis menimpa snapshot** periode yang sudah dikomit: analis mereview pratinjau (metrik ringkas + DQIssue) lalu menekan **Komit Snapshot**. Menimpa periode lama = eksplisit + tercatat AuditLog. | P0 |
| **FR-5** | Riwayat run: daftar semua run (waktu, durasi, status, jumlah file, definition_version, siapa), dapat dibuka ulang untuk melihat log & DQIssue-nya. | P0 |
| **FR-6** | (P2) Jalur import lanjutan: upload dari Google Drive (pola `import-drive` IC) & chunked upload file besar (pola `FileChunk` IC). | P2 |

**AC-A**: bundle folder Windows yang dipakai desktop bulan ini, diupload ke web, menghasilkan rangkaian frame & pivot **identik** dengan run desktop (golden-file, §11). Status akhir & daftar skip/warning identik pula.

### Modul B — Engine Service (motor hitung; infrastruktur, bukan halaman)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-10** | **Engine service Python (FastAPI)** membungkus `src/pipeline/*` desktop APA ADANYA (16 modul; tanpa rewrite logika): endpoint `POST /process` menerima bundle (path/arsip) + konfigurasi run → menjalankan pipeline → mengembalikan hasil terstruktur (JSON): frame pivot 10 metrik, deviasi bertanda per resto×barang×hari, label CEK + catatan audit, nominal & pasangan tanpa harga, selisih IN + hasil audit, rincian PO, log + DQIssue + status. | P0 |
| **FR-11** | Kontrak versi: service mengekspos `definition_version` (mis. `3.9.71-noSI`) + parameter run (TANGGAL H, AMBANG ACR, mode laporan) yang ikut tersimpan pada setiap snapshot (INV-4). | P0 |
| **FR-12** | Engine **idempotent & stateless**: run yang sama (bundle + config sama) → hasil sama; tidak ada state antar-request. Cache baca file boleh (pola mtime+size), tapi tidak boleh mengubah hasil. | P0 |
| **FR-13** | Baterai tes pipeline desktop **tetap dijalankan di CI repo web** (pytest, tanpa bagian UI Tkinter) + gerbang paritas (§11). Upgrade dependensi (pandas <3 pin) mengikuti kebijakan `requirements.txt` desktop. | P0 |
| **FR-14** | Endpoint kesehatan/observabilitas service: versi, waktu proses terakhir, memori (informasi cache), error terakhir (untuk halaman status admin). | P1 |
| **FR-15** | (P2) Mode batch: proses beberapa periode sekaligus (backfill histori) via antrean. | P2 |

**AC-B**: `pytest` baterai pipeline (subset non-UI dari 1607) hijau; output `POST /process` pada fixture mock = angka yang sama dengan `test_mock.py` desktop.

### Modul C — Snapshot Store (fondasi data; menutup gap #1 Task 31)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-20** | Setiap run terkomit menghasilkan **snapshot periode** permanen. Grain utama: **periode × resto × barang × satuan × hari** (deviasi & 10 metrik JENIS tersedia hingga grain hari, atau minimal per H mingguan). Tidak ada lagi "hasil run lenyap saat run berikutnya". | P0 |
| **FR-21** | Setiap baris snapshot menyimpan: qty metrik bertanda (10 jenis), nominal & harga efektif yang dipakai (+ penanda konversi `*`), label CEK (saat run), `definition_version`, parameter run (H, ambang ACR), referensi `RunBatch`. | P0 |
| **FR-22** | **Fingerprint stabil lintas-periode (baru)**: identitas kasus = hash dari (resto, barang, satuan, kategori) — TANPA kolom CEK/qty (mengatasi fingerprint volatil gap #4). Fingerprint lama desktop dipetakan saat migrasi data follow-up lama. | P0 |
| **FR-23** | Histori harga: harga 41.09 per barang per run disimpan (bukan hanya dipakai saat-run) → memungkinkan P₀ historis untuk dekomposisi nominal (roadmap F2, keputusan D-2). | P1 |
| **FR-24** | Snapshot **immutable**: koreksi = run ulang + komit ulang periode (versi snapshot baru, lama tetap ada, ditandai superseded). Query "periode terkomit terbaru aktif" adalah default UI. | P1 |
| **FR-25** | (P2) Migrasi histori file deviasi eksternal (format tab ⚖) sebagai snapshot periode "impor" — agar tren panjang langsung tersedia tanpa menunggu bulan bertumpuk. | P2 |

**AC-C**: setelah komit 2 periode berturut, halaman analisis dapat membandingkan bulan N vs N−1 **tanpa file eksternal**; snapshot bulan lalu tetap utuh setelah run bulan baru; setiap baris membawa `definition_version`.

### Modul D — Halaman Kerja Inti (paritas 10 tab)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-30** | **Deviasi GR & PCS** (menggabung tab 4–5 desktop jadi 1 halaman + toggle GR/PCS): wide-matrix per resto (baris=barang dikelompokkan, kolom=periode/H, sel=deviasi bertanda), kolom CEK (9 label), Nominal, Rank per-baris (method=min, dev=0 → kosong — kontrak §61/62 desktop), filter kategori & funnel per-kolom persist. Input **TANGGAL H** & **AMBANG ACR** di sini (satu sumber, sinkron GR/PCS — paritas v3.9.21) dan re-komputasi label CEK saat berubah. | P0 |
| **FR-31** | **Pivot Table** (paritas tab 3): mode per-resto & per-tanggal, 10 metrik JENIS, rentang default 26 lalu–31 berjalan, **freeze kolom nama barang saat scroll horizontal** (kontrak §84), hide-empty "semua sel 0" (bukan total≤0 — v3.9.69 P1.1), seleksi ala Excel (klik/drag/Ctrl+C per-sel). | P0 |
| **FR-32** | **Drill-down universal** (INV-7): klik sel/angka → panel samping menampilkan baris sumber pipeline (dokumen, tanggal, qty, resto, satuan) — paritas popup rincian desktop, termasuk jejak konversi satuan & harga. | P0 |
| **FR-33** | **Rekap Selisih IN** (tab 6): tabel IN (42.05+32.24+99.01) vs BARANG MASUK + SO + **Hasil Audit** (port logika macro VBA), MODE HITUNG Bulan Ini/Lalu+Ini, checkbox hanya selisih≠0, 🏆 **SKOR RESTO** (item selisih + tanggal terdampak), drill-down per resto. | P1 |
| **FR-34** | **Nominal Deviasi** (tab 8): Σ nominal per resto + TOTAL, COM Deviasi & Biaya Packaging, % kenaikan/penurunan vs bulan lalu (DARI SNAPSHOT, bukan file eksternal), anak-tab **Tanpa Harga** global (alasan + kategori), popup rincian per resto→barang. | P1 |
| **FR-35** | **Laporan Deviasi 3 mode** (tab 7): ⚖ Komparasi (default — kini dibandingkan DENGAN SNAPSHOT periode lalu + opsional file eksternal untuk histori pra-web), 🚨 Anomali COM, 💰 Nominal (H). | P1 |
| **FR-36** | **Rincian PO** (tab 10): daftar PO + item, status pesanan (32.43), anotasi ↳ Status per PO, filter CABANG/STATUS persist, kolom PO Menunggu. | P1 |
| **FR-37** | **Komparasi lanjutan** (evolusi tab ⚖ + Task 31-a): tabel Top Selisih (median n bulan), Perubahan Arah (bulan-lalu→kini, kategori Sempurna<10% / Dominan 10–40% / Parsial≥40%), semua dari snapshot DB. | P2 |
| **FR-38** | **Pencarian global Ctrl+F-ala** (paritas v3.9.62): substring case-insensitive semua kolom + highlight + navigasi; sort natural (angka+teks campuran). | P1 |

**AC-D**: untuk bundle data yang sama, matriks Deviasi GR/PCS + Pivot + Selisih IN web menampilkan angka & label yang identik dengan desktop (golden-file perbandingan sel-per-sel untuk sampel baris terverifikasi manual); interaksi H/ambang langsung memperbarui label CEK.

### Modul E — Follow-Up 2.0 (menutup gap #3)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-40** | Daftar kasus follow-up dengan **status workflow**: `PENDING → DIPROSES → SELESAI / DIBATALKAN` (+ `REOPEN`). Bukan lagi centang boolean. | P0 |
| **FR-41** | Setiap perubahan status menyimpan: siapa, kapan (timestamp), status baru, **alasan/tindakan** (teks bebas + kategori tindakan pilihan), qty temuan fisik opsional. Riwayat tampil sebagai timeline di detail kasus. | P0 |
| **FR-42** | **PIC** dapat diisi dari UI (dropdown OutletPIC IC + teks bebas) — menutup jalur input yang hilang sejak v3.8. | P0 |
| **FR-43** | Kasus = entitas stabil lintas-periode (FR-22): baris anomali bulan ini yang cocok fingerprint kasus lama menawarkan **"kasus berulang — tautkan ke kasus #N"**, bukan mulai dari nol. | P1 |
| **FR-44** | Export Excel follow-up **kompatibel format lama** (SO·DEVIASI·Selisih·Selisih Deviasi·Cek FU·PIC) supaya TL yang belum migrasi tetap bisa kerja via file. | P1 |
| **FR-45** | Akses TL outlet (bila RBAC dinyalakan, D-6): TL hanya melihat kasus outlet-nya, dapat mengubah status+alasan; analis melihat semua. | P2 |
| **FR-46** | (P2, roadmap F8) KPI efektivitas: umur kasus, % selesai < X hari, deviasi berikutnya pada kasus yang pernah selesai (recurrence). | P2 |

**AC-E**: skenario uji — buat kasus → ubah status 2× oleh 2 akun → timeline menampilkan 2 entri lengkap → selesaikan → reopen → kasus tetap satu entitas dengan riwayat 3 entri; export Excel membuka di Excel tanpa perbaikan manual.

### Modul F — Rekonsiliasi Transfer 42.15 (menutup gap #5)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-50** | Pipeline membaca **BOTH sisi** 42.15: kirim (folder Kirim4215) dan **terima (folder Terima4215 — folder config SUDAH ADA, tinggal di-wire)**; baris menyimpan asal & tujuan (kolom `Gudang Pengirim`/`Gudang Tujuan` sudah ada di sheet mentah — terverifikasi mock `§79c`). | P1 |
| **FR-51** | **Ledger transfer**: daftar per (barang, tanggal, qty, asal, tujuan) → pencocokan kirim↔terima berbasis tuple kolom yang ADA (matching tanpa nomor dokumen — metode final = keputusan D-3: eksak-tuple vs toleransi-qty). Ketidakcocokan (kirim tanpa terima, qty beda, delay) jadi temuan tersendiri. | P2 |
| **FR-52** | Saldo akhir per resto memasukkan sisi terima (koreksi arah barang) dengan **flag provenance** supaya angka web dapat dibedakan dari desktop (desktop hanya sisi kirim) — dan perbedaannya dihitung & ditampilkan di panel rekonsiliasi, bukan senyap. | P2 |

**AC-F**: bundle uji dengan transfer CKGPAH→MLGPAR (fixture §79c) menghasilkan ledger dengan pasangan cocok + 1 pasangan sengaja-dikorupsi terdeteksi sebagai temuan.

### Modul G — Kualitas Data (memformalkan INV-5/INV-6)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-60** | Semua sinyal pipeline (10 kelas Task 31-c: skip file, schema-warning §82b, fallback-bind 9901, VALUE/Tanggal-missing, konversi gagal `*`, kategori kosong, duplikat baris-persis/multi-file, preflight folder, tanpa-harga) ditulis ke **DQIssue** (severity/code/message/rawValue/rowNumber/sheet) per run. | P0 |
| **FR-61** | **Panel Kualitas Data** per run: ringkas per kelas, klik → baris terdampak → drill-down. Skor kelengkapan sederhana per resto×sumber (roadmap F7 v1: proporsi baris bersih vs ber-isu). | P1 |
| **FR-62** | **Cakupan data** (belum ada di desktop — temuan Task 31-c): cek terpusat rentang tanggal per sumber & daftar outlet yang tidak muncul di sumber X (indikasi export belum lengkap) sebelum komit snapshot. | P1 |

**AC-G**: run dengan bundle sengaja-dikorupsi (hapus kolom VALUE 22.05, rename header 9901, file duplikat) menghasilkan panel DQ dengan 3 kelas isu + status akhir DENGAN PERINGATAN; snapshot TIDAK diblok, tapi isu tercatat & terlihat.

### Modul H — Export & Pelaporan

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-70** | Export Excel **paritas `export_sheets.py` desktop** (PIVOT/Append1/Rincian PO/Rincian IN/Audit/pivot-display/Selisih IN/FOLLOW UP) dari halaman web. | P1 |
| **FR-71** | Laporan bulanan ringkas: KPI periode (total nominal deviasi, top resto, top barang, tren vs bulan lalu, jumlah kasus follow-up & statusnya) — PDF (pola pdfkit IC) + Excel. | P1 |
| **FR-72** | Tautan share read-only (periode × resto) untuk auditor/ops — tanpa login bila D-6 menyetujui, atau token terbatas. | P2 |

### Modul I — Admin & Konfigurasi

| ID | Kebutuhan | Prioritas |
|---|---|---|
| **FR-80** | Halaman Config (paritas tab ⚙️): RootPath tidak relevan (ganti pemetaan upload FR-2), tapi Sheets/KategoriBarang4217/ambang ACR default/TANGGAL H default dikelola di sini; perubahan tercatat AuditLog. | P0 |
| **FR-81** | Status engine service: sehat/bermasalah, versi, definisi aktif, waktu proses terakhir (FR-14 diteruskan ke UI). | P0 |
| **FR-82** | Manajemen periode: daftar snapshot (aktif/superseded), retensi, tombol komit-ulang. | P1 |

### Modul J — Jembatan Roadmap 8-Fitur (Task 31 → web)

Pemetaan agar investasi web langsung membuka roadmap (angka F1–F8 mengikuti dokumen roadmap yang tervalidasi Task 31):

| Fitur roadmap | Dibuka oleh | Fase realistis |
|---|---|---|
| F1 Deviasi kronis multi-periode | FR-20/22/23 (snapshot + fingerprint stabil + histori harga) | 4 |
| F2 Dekomposisi nominal ΔN=ΔN_Q+ΔN_P (matematika tervalidasi tepat) | FR-23 (P₀ historis — D-2) | 4 |
| F3 Akar penyebab (kamus kasus) | FR-40–43 + CEK + drill-down | 4–5 |
| F4 Peringatan dini (naik-turun mingguan) | snapshot mingguan + FR-37 | 5 |
| F5 Rekonsiliasi antar-outlet 42.15 | FR-50–52 | 5 |
| F6 Benchmark antar-resto | snapshot multi-resto + pola `item-peer-comparison` IC | 4 |
| F7 Skor kualitas data | FR-60–62 | 4 |
| F8 Efektivitas follow-up | FR-40–46 | 5 |
| Tahap-3 prediktif | ≥ 6 bulan snapshot | 6 |

---

## 7. Kebutuhan Non-Fungsional

| ID | Kebutuhan | Target terukur |
|---|---|---|
| **NFR-1 Performa** | Proses bundle ≤ waktu desktop + overhead jaringan (desktop engine v3.7 "turbo": running stock 0,19s, information-level 0,05s di real-data) | Run lengkap ≤ 3 menit; halaman matriks interaktif (sort/filter/H) ≤ 2 detik untuk ~29 ribu baris (virtualisasi ala IC) |
| **NFR-2 Skalabilitas data** | Retensi ≥ 24 bulan × ~54 ribu record/periode (jajar IC) + grain harian SM-WEB | Query tren lintas-bulan < 5 detik (indeks + AggregationCache pola IC) |
| **NFR-3 Keandalan** | Run gagal tidak pernah merusak snapshot lama (snapshot immutable FR-24); kegagalan service terlihat jelas & dapat diulang | 0 snapshot rusak karena run gagal |
| **NFR-4 Audit & keamanan** | Semua aksi tulis (komit, ubah status follow-up, ubah setting) → AuditLog (siapa/kapan/apa); secret (PAT, DB URL) lewat env, TIDAK PERNAH hardcode/commit (pelajaran insiden PAT — lihat worklog Task 32) | AuditLog lengkap; 0 secret di repo |
| **NFR-5 Kompatibilitas input** | Bundle dari Windows (path case-insensitive, encoding lokal) diproses benar di server Linux | Golden-file bundle sample ber-3 platform |
| **NFR-6 Responsif & aksesibilitas** | Desktop-first (analis), dapat dipakai TL via tablet/ponsel untuk halaman follow-up | Halaman follow-up nyaman di ≥ 360px |
| **NFR-7 Bahasa & format** | UI Bahasa Indonesia; format angka/persen ala desktop (ribuan `1.234,5%`, minus merah) | Konsisten semua halaman |
| **NFR-8 Ketahanan format Accurate** | Menambah kolom / menghapus kolom tak terpakai / reorder di export TIDAK mengubah hasil (by-name selection — teruji v3.9.67); perubahan yang mengubah hasil wajib jadi DQIssue | Kontrak §79 desktop dipertahankan di web |
| **NFR-9 Keterjagaan perilaku** | 9 invariants §3.4 jadi kontrak tes otomatis; perubahan perilaku domain harus lewat keputusan eksplisit (changelog + version bump definisi) | CI merah bila invariant dilanggar |
| **NFR-10 Deployment** | Satu platform (Vercel/VPS) + engine service co-located (pola mini-service IC/Railway); tidak ada port terekspos selain gateway | Uji end-to-end dari browser eksternal |

---

## 8. Arsitektur Solusi (level keputusan produk)

### 8.1 Pilihan yang dievaluasi

| Opsi | Ringkas | Penilaian |
|---|---|---|
| **A. Port penuh ke TypeScript** | Rewrite 16 modul pipeline pandas → TS/SQL | ❌ **DITOLAK.** ~39 ribu baris logika teruji, 1607 tes, perilaku NaN/pandas/satuan sudah ditempa (pin pandas<3 bahkan di dokumentasikan); peluang drift logika & regresi sangat besar; pemborosan aset verifikasi terbesar yang dimiliki produk. |
| **B. Hybrid — engine service Python + web Next.js** (REKOMENDASI) | Pipeline `src/pipeline/*` dibungkus FastAPI; Next.js memanggil via gateway; hasil disimpan ke Prisma/Postgres; UI baru memakai komponen IC | ✅ **DIPILIH.** Logika 0-rewrite (FR-10/13), aset tes tetap hidup, fondasi IC ~70% terpakai; risiko terbesar pindah ke "integrasi" yang dapat diuji dengan golden-file paritas. |
| **C. Status quo + dashboard saja** | Desktop tetap; dashboard Next.js pendamping dibaca Excel hasil export | ❌ Tidak menutup satupun dari 7 keterbatasan §2.2; roadmap 8-fitur tetap terblokir snapshot store; kolaborasi TL tetap manual. |

**Dasar kelayakan B (terverifikasi)**: `src/pipeline/` desktop murni pandas — tidak mengimport Tkinter (UI-agnostic, Task 32); Inventory-Control sudah menyediakan pola gateway mini-service (`XTransformPort`), scaffolding infra Python runtime (`nixpacks.toml`, `railway.toml`, folder `mini-services/`), dan repo sandbox dev ini pun menegaskan aturan request lintas-service (`/?XTransformPort=` — tanpa absolut path/port).

### 8.2 Blueprint aliran data (target)

```
[Export Accurate — bundle folder, format TIDAK berubah]
        │ upload ZIP / (P2: Google Drive)
        ▼
┌───────────────────────── Next.js 16 (App Router, 1 domain) ─────────────────┐
│  📥 Ingest (FR-1..5)   Deviasi GR/PCS (FR-30)   Pivot (FR-31)               │
│  Selisih IN (FR-33)    Nominal (FR-34)         Laporan 3-mode (FR-35)      │
│  Follow-Up 2.0 (FR-40..46)  Rincian PO (FR-36)  DQ Panel (FR-60..62)       │
│  Config/Admin (FR-80..82)  Export (FR-70..72)                               │
└───────┬───────────────────────────────────┬────────────────────────────────┘
        │ POST /process  (XTransformPort)   │ Prisma ORM
        ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────────────┐
│  Engine Service      │  hasil   │  PostgreSQL (Supabase)       │
│  Python/FastAPI      │ ───────► │  (TERPISAH dari IC — D-5)    │
│  src/pipeline/*      │  JSON    │  RunBatch · PeriodSnapshot    │
│  (16 modul, 0-rewrite│          │  SnapshotRow · PriceHistory  │
│  + pytest baterai)   │          │  FollowUpCase/Event · DQIssue│
└──────────────────────┘          │  AuditLog · Setting · dst.    │
                                  └──────────────────────────────┘
        Desktop v3.9.x TETAP HIDUP (dual-track): pipeline sama →
        paritas mudah dicek; pensiun = keputusan D-7 setelah Fase 3.
```

### 8.3 Kontrak Engine Service (kerangka; detail teknis final di ARCHITECTURE.md Fase 0)

- `POST /process` — input: bundle (arsip/path) + config run (mapping folder/sheet dari Setting, TANGGAL H, ambang ACR, mode) → output: JSON hasil (frames pivot, deviasi, CEK, nominal, tanpa-harga, selisih IN, PO, log, DQIssues, status akhir, `definition_version`).
- `GET /health` — FR-14.
- Semua aturan gateway: pemanggilan dari Next.js **wajib** relative-path `/?XTransformPort={port}` (tanpa absolut URL/port), sesuai batasan platform.
- Kontrak data = satu sumber kebenaran: skema JSON engine adalah SATU-SATUNYA tempat definisi kolom hasil; UI & mapper-DB tidak boleh menghitung ulang domain (prinsip "helper bersama" ala `nominal_common.py` desktop).

### 8.4 Model data (rancangan awal — final di Fase 0)

Fondasi: **pola skema Prisma Inventory-Control direplikasi ke project Supabase TERPISAH** (D-5 SAH — bukan satu DB dengan IC; IC live tidak tersentuh): model relevan dibuat ulang di schema SM-WEB (`SourceFile`, `Outlet`, `Item`, `Setting`, `OutletPIC`, `FileChunk`, `AuditLog`, `DQIssue`, `AggregationCache`). Tambahan untuk SM-WEB (grain & domain berbeda dari IC yang per-minggu-analisis):

| Entitas baru/usulan | Inti field | Catatan |
|---|---|---|
| `RunBatch` | id, waktu, durasi, status (SELESAI/PERINGATAN/PARSIAL), definition_version, params (H, ambang ACR) JSON, actor, sourceFileId | 1 run = 1 batch; log & DQIssue menempel ke sini |
| `PeriodSnapshot` | id, runBatchId, periodKey (bulan), restoCount, totals, state (ACTIVE/SUPERSEDED) | FR-24 immutable; superseded tetap tersimpan |
| `SnapshotRow` | id, snapshotId, restoCode, itemName, satuan, kategori, tanggal/H, 10 metrik qty bertanda, nominal, hargaEfektif, flagKonversi, cekLabels[], fingerprintStabil | FR-20/21/22; grain hari; `null` ≠ 0 (INV-1) |
| `PriceHistory` | id, runBatchId, itemName, satuan41, harga, rasioKonversi | FR-23 |
| `FollowUpCase` | id, fingerprintStabil, restoCode, itemName, satuan, kategori, status, picId, createdAt, closedAt, periodFirstSeen, lastLinkedSnapshotId | FR-40/43 |
| `FollowUpEvent` | id, caseId, actor, timestamp, fromStatus→toStatus, alasan, kategoriTindakan, qtyTemuan | FR-41 — timeline |
| `TransferLedger42_15` | id, runBatchId, tanggal, itemName, qty, asalCode, tujuanCode, matchStatus, matchedWithId | FR-50/51 (Fase 5) |

Migrasi data lama: `followup.json` + `followup_resolved.json` desktop → `FollowUpCase/Event` dengan status awal PENDING/SELESAI + fingerprint mapping (FR-22).

## 9. Peta Paritas Desktop → Web (ringkas; inventaris detail di Lampiran A)

| Tab desktop | Halaman web | Perilaku identik | Perilaku berubah (disengaja) |
|---|---|---|---|
| ⚙️ Config | Config/Admin | Pemetaan sheet, kategori 42.17 | RootPath → pemetaan bundle upload; audit log baru |
| 🚀 Proses | Ingest | Log streaming, 3 status akhir, kontrak §82b | Komit snapshot eksplisit (FR-4); riwayat run |
| 📊 Pivot Table | Pivot | 10 metrik, 2 mode, freeze nama barang, hide-empty semua-sel-0 | Sel NA diberi keterangan "—" (INV-1 fix), bukan 0 |
| 📦 Deviasi GR | Deviasi (toggle GR) | 9 CEK, H+ambang, Nominal, Rank per-baris, filter persist | Re-komputasi label tanpa run ulang |
| 🧩 Deviasi PCS | Deviasi (toggle PCS) | sama | sama |
| 📤 Rekap Selisih IN | Selisih IN | Hasil Audit port VBA, SKOR RESTO, drill-down | — |
| 📋 Laporan (⚖/🚨/💰) | Laporan 3 mode | kolom, nominal, anomali COM | ⚖ membandingkan snapshot DB (utama) + file eksternal (opsional) |
| 🧮 Nominal Deviasi | Nominal | Per resto, COM/Packaging, %naik-turun, Tanpa Harga global | Bulan-lalu dari snapshot DB |
| ☑ Follow Up | Follow Up 2.0 | Daftar kasus, export lama | Status workflow + PIC + riwayat + tautan kasus berulang |
| 🛒 Rincian PO | Rincian PO | Kolom, ↳ Status, filter | — |
| ⚖ file eksternal (mode) | Komparasi lanjutan (P2) | 3 checkbox, Top/Flip | Sumber utama = snapshot DB |

---

## 10. Rencana Rilis Bertahap

> Prinsip urutan (dipertajam dari Task 31): **kualitas data → snapshot store (langkah-0) → analisis → tindak lanjut → rekonsiliasi → prediktif.** Setiap fase punya *exit criteria* yang dapat diverifikasi sebelum lanjut — tidak ada fase berikutnya sebelum fase sebelumnya diverifikasi. Durasi = estimasi kerja efektif, bukan janji tanggal.

| Fase | Isi | Exit criteria (verifikasi) | Estimasi |
|---|---|---|---|
| **0. Fondasi & keputusan** | D-5/D-6/D-8 SAH; sisa keputusan D-1..D-4 difinalisasi di sini; **repo BARU terpisah** (D-8) + **project Supabase baru terpisah** (D-5); ARCHITECTURE.md SM-WEB; setup engine service kosong + CI (pytest pipeline + lint + build) hijau; skema Prisma final + migrasi | PRD disetujui; CI hijau; kontrak JSON engine v1 ditulis & direview | 1–2 minggu |
| **1. Engine + Ingest + Snapshot** | FR-1,2,3,5,10,11,12,13,20,21,22,60,80,81; migrasi followup lama (FR-22 mapping) | Golden-file: bundle real → `POST /process` ≡ run desktop (metrik & status); snapshot 1 periode terkomit & query-able; DQIssue tampil | 2–4 minggu |
| **2. Halaman kerja inti** | FR-4 (komit eksplisit), FR-30, 31, 32, 38 | Analis dapat menyelesaikan audit mingguan **seluruhnya di web** pada bundle real; paritas H/ambang/CEK dicek; freeze-pane & sort/filter lulus uji interaksi browser | 3–5 minggu |
| **3. Paritas penuh** | FR-14, 23, 24, 33, 34, 35, 36, 44, 61, 62, 70, 71, 82 | Semua 10 tab desktop dapat direproduksi; export Excel dibuka & dibandingkan dengan export desktop (struktur kolom sama); analis TIDAK lagi buka desktop untuk siklus bulanan (dogfood) | 3–5 minggu |
| **4. Follow-Up 2.0 + analisis multi-periode** | FR-25 (impor histori eksternal), 40, 41, 42, 43, 45, 46, 72; fitur roadmap F1 (kronis), F6 (benchmark antar-resto), F7 (skor kualitas) versi pertama | TL mengisi status dari browser; KPI efektivitas tampil; tren ≥ 3 periode dari snapshot murni (tanpa file eksternal); kasus berulang ter-tautkan | 3–6 minggu |
| **5. Rekonsiliasi + konsolidasi IC** | FR-6, 15, 50, 51, 52, 37; fitur F4 (peringatan dini), F5 (42.15), F8 lanjutan; konsolidasi fitur ganda SM-WEB↔IC (satu nav, dua lapis data); AI narrative IC mulai membaca snapshot SM-WEB (lintas-DB terpisah → via API publik SM-WEB, D-5) | Ledger 42.15 menampilkan pasangan + temuan; peringatan dini mingguan aktif; keputusan konsolidasi produk (nama, nav) dijalankan | 4–6 minggu |
| **6. Prediktif & pensiun desktop** | Tahap-3 roadmap (baseline historis, prediksi) setelah ≥ 6 bulan snapshot; evaluasi pensiun desktop (D-7) | Model baseline terlatih pada histori snapshot; keputusan desktop go/no-go berbasis data pemakaian nyata | menyusul data |

Milestone "kiri-ke-kanan": Fase 1 = produk sudah **lebih kuat dari desktop** (ada snapshot), Fase 3 = **setara penuh**, Fase 4 = **melampaui** (kolaborasi + histori).

## 11. Strategi Pengujian & Kualitas

Aset terbesar produk ini adalah kepercayaan angka — strategi pengujian dirancang agar **tidak satu pun turun** saat migrasi:

1. **Baterai pipeline tetap hidup**: subset non-UI dari 1607 tes desktop (unit + mock + kontrak §79/§82b/§84) dijalankan di CI repo web pada setiap PR. Definisi "subset non-UI": semua tes `src/pipeline/*` + mock fixture; tes Tkinter tetap milik repo desktop.
2. **Golden-file paritas**: bundle export real (1 bulan aktual) diproses (a) desktop, (b) engine service → hasil pivot/deviasi/CEK/nominal/selisih-IN diekspor kedua-duanya → diff otomatis; toleransi nol (angka harus identik; beda = bug). Dijalankan tiap rilis fase 1–3.
3. **Tes invariants (NFR-9)**: 9 invariants §3.4 jadi kontrak tes otomatis permanen (pola §82b desktop: kontrak = tes gagal bila perilaku berubah tanpa keputusan).
4. **Tes integrasi web**: ujung-ke-ujung di browser otomatis (pola Agent-Browser) untuk golden-path: ingest→komit→deviasi→follow-up→export; responsif & aksesibilitas dasar.
5. **Uji DQ pura-pura**: bundle sengaja-dikorupsi (v3.9.67 style) sebagai fixture regression untuk panel kualitas data (AC-G).
6. **Gerbang rilis**: PR review + CI hijau (lint + tes + golden) sebelum merge — meniru gerbang dua-kerja CI desktop (tests → build) yang sudah terbukti menahan regresi 71 versi.

## 12. Risiko & Mitigasi

| # | Risiko | Dampak | Mitigasi |
|---|---|---|---|
| R-1 | **Drift logika** saat membungkus pipeline (perubahan tak-sengaja, semantik pandas, path Windows→Linux) | Angka web ≠ desktop → kepercayaan runtuh | 0-rewrite (FR-10); golden-file paritas tiap rilis (§11.2); pin pandas<3; tes subset 1607 |
| R-2 | **Perbedaan platform path/encoding** (Windows user vs Linux server; xlsb/calamine reader) | Run gagal / baris lenyap | NFR-5: bundle sample lintas-platform di CI; reader sama persis (python-calamine/pyxlsb pin) |
| R-3 | **Kehilangan kelincahan offline** desktop (internet/server mati saat tutuh buku) | Analis tidak bisa kerja | Dual-track eksplisit (D-7): desktop tetap dirilis sampai web terbukti; keduanya pipeline identik |
| R-4 | **Perbaikan INV-1 (NA vs 0) mengubah tampilan** vs kebiasaan user | Kebingungan "angka berubah" | Selisih NA-vs-0 ditampilkan dengan penanda jelas & hanya di pivot baru; changelog definisi; bukan perubahan angka hitungan (engine tetap jujur) |
| R-5 | **Snapshot store tumbuh besar** (grain harian × 24 bulan) | Query melambat, biaya naik | Grain disimpan per-hari hanya metrik yang perlu; agregat mingguan/bulanan via AggregationCache; retensi & arsip per sesuai kebijakan |
| R-6 | **Fingerprint migrasi** (lama→baru) salah map → kasus follow-up lama hilang/orphan | Riwayat kasus putus | Mapping diuji dengan followup.json real; fitur "cek-dinetralkan" desktop jadi referensi; tes migrasi terpisah |
| R-7 | **Rahasia & keamanan** (insiden PAT GitHub lampau — worklog Task 32) | Kebocoran akses | NFR-4: secret hanya env var; scan secret di CI; PAT lama sudah disarankan revoke |
| R-8 | **Scope creep / dua produk jalan sendiri-sendiri** (SM-WEB vs IC fitur kembar) | Pemeliharaan dobel, user bingung | §10 Fase 5 eksplisit konsolidasi; sampai itu, fitur baru SM-WEB dibatasi FR di PRD ini; IC tidak dikerjakan paralel untuk domain yang sama |
| R-9 | **Perubahan format export Accurate** di masa depan | Baris nyasar senyap | NFR-8: kontrak ketahanan by-name §79 + DQIssue wajib — arsitektur yang sama dgn bukti empiris v3.9.67 |
| R-10 | **Load upload besar** (bundle ratusan MB, koneksi lambat) | Proses tak selesai | Chunked upload (pola FileChunk IC, FR-6); resume; batas ukuran jelas di FR-1 |

## 13. Metrik Keberhasilan (di luar tes — diukur dari pemakaian)

| Metrik | Baseline desktop | Target |
|---|---|---|
| Waktu export Accurate → laporan siap kirim | multi-langkah manual (proses+analisis+Excel+WA) | < 1 hari kerja setelah SO terakhir; langkah manual tersisa: review DQ + komit |
| Riwayat periode dapat dibuka ulang | Hanya file eksternal yang di-maintain manual | 100% periode sejak rilis Fase 1; ≥ 6 bulan data untuk Fase 6 |
| Jejak tindak lanjut | Boolean ✓, tanpa waktu | 100% perubahan status ter-audit; umur kasus terukur |
| Kasus berulang terdeteksi | Tidak ada konsep | Tampil sebagai saran tautan di Fase 4 |
| Pemakaian desktop vs web (setelah Fase 3) | 100% desktop | Trend menurun; keputusan pensiun berbasis angka ini |
| Bug paritas angka (web vs desktop) | — | 0 bug paritas terbuka pada tiap exit fase 1–3 |

## 14. Keputusan (D-5, D-6, D-8 ✅ DISAHKAN pemilik produk 2026-10-21; D-1..D-4 & D-7 menjalankan rekomendasi PRD kecuali dinyatakan lain)

| ID | Keputusan | Opsi & rekomendasi PRD |
|---|---|---|
| **D-1** | Desain snapshot store — adopsi rancangan §8.4? | Rekomendasi: adopsi, finalisasi di Fase 0 (termasuk grain: hari vs minggu vs keduanya — implikasi ukuran R-5) |
| **D-2** | Harga periode-lalu P₀ untuk dekomposisi nominal (F2) | Opsi (a) aproksimasi P₀ = N₀/Q₀ dari file eksternal lama — cepat tapi bias pembagian; (b) tunggu histori harga 41.09 tersimpan beberapa run (FR-23) — akurat tapi menunda F2. Rekomendasi: (b) mulai simpan sejak Fase 1, aktifkan F2 saat ≥ 2 periode harga; (a) sebagai fallback eksperimen berlabel "aproksimasi" |
| **D-3** | Metode matching 42.15 tanpa nomor dokumen | Opsi (a) eksak-tuple (barang,tgl,qty,asal,tujuan); (b) toleransi-qty/tanggal + kategori kemiripan. Rekomendasi: (a) dulu + temuan ketidakcocokan eksplisit; (b) menyusul dengan label kepercayaan. Wire branch terima wajib (FR-50) |
| **D-4** | Ekstensi skema follow-up (§8.4) + jalur input | Rekomendasi: sahkan usulan FR-40..46; kategori tindakan awal disarikan dari export lama user |
| **D-5** | ✅ **SAH 2026-10-21 — Supabase PostgreSQL, DATABASE TERPISAH dari IC** (project Supabase baru khusus SM-WEB). Konsekuensi disadari & diterima: IC live 100% aman/tak tersentuh; skema bebas berevolusi; konsolidasi Fase 5 & AI narrative IC membaca snapshot SM-WEB **via API antar-app**, bukan query lintas-DB; dua `DATABASE_URL` dikelola terpisah |
| **D-6** | ✅ **SAH 2026-10-21 — SINGLE-USER tanpa login** untuk Fase 1–3 (AuditLog tetap jalan dengan user default "analyst"); login analis + token TL diaktifkan saat Fase 4 (FR-45) |
| **D-7** | Nasib desktop dual-track | Rekomendasi: tetap rilis desktop sampai exit Fase 3 + 1 siklus bulanan penuh tanpa desktop-blocker; pensiun = keputusan eksplisit dengan data metrik §13 |
| **D-8** | ✅ **SAH 2026-10-21 — REPO BARU TERPISAH** dari Inventory-Control (IC live tak tersentuh; risiko nol). Nama repo/produk: usulan `Stock-Monitoring-Web` (boleh diganti kapan pun — PRD memakai placeholder SM-WEB) |

---

## Lampiran A — Inventaris Desktop (rujukan paritas; semua terverifikasi v3.9.71)

**A.1 Pipeline (16 modul `src/pipeline/`)**

| Modul | Peran | Catatan kunci |
|---|---|---|
| `fn_2205` | Sales/OUT 22.05 (Rincian Penjualan) | Tanpa kode SI (case-sensitive) sejak v3.9.71; Nomor # bukan kolom wajib; INFO untuk baris SI |
| `fn_3224` | RI 32.24 (Rincian Penerimaan) — IN eksternal | Ber-Nomor # RI + Nomor PO; header_row=4 |
| `fn_4205` | 42.05 (Rincian Pemindahan) — IN internal per-outlet | Ber-Nomor #Terima; konversi satuan |
| `fn_4215` | 42.15 (Pemindahan Barang) — BARANG KELUAR | Sisi kirim dibaca (Gudang Pengirim→NAMA RESTO); side terima ADA di kode (fn_4215.py:83) tapi tak pernah dipanggil; kolom tujuan dibuang di output; folder Terima4215 di config tak pernah dibaca |
| `fn_4217` | 42.17 SALDO AWAL per gudang | Kategori barang filter (KategoriBarang4217); Tanggal=1 |
| `fn_4109` | 41.09 harga (Nilai÷Kuantitas Saldo Akhir, global per barang) | Deteksi header dinamis |
| `fn_9901` | 9901 IN tambahan (tanpa Nomor Penerimaan, Jenis Persediaan) | Fallback-bind kini ter-log WARNING (v3.9.67) |
| `fn_audit` | Rekonsiliasi Selisih Harian + Hasil Audit (port VBA) + PO Menunggu | "ACR to BOM" bukan di sini — ada di CEK deviasi_view |
| `fn_rekap_mentah` | Rekap bulan berjalan + bulan lalu (hari 25–31 dinegasikan) | Mode lalu = ekor bulan lalu |
| `fn_running_stock` | Saldo akhir segmented cumsum (turbo v3.7) | 6,68s→0,19s real-data |
| `fn_dbs_kategori` | Merge kategori 21. DBS Kategori | `(Tanpa Kategori)` jujur bila kosong |
| `konversi_satuan` | Peta rasio satuan rekap/41.09 (in-memory dari 42.05+32.24) | Gagal → penanda `*`, qty/harga as-is |
| `queries` | Query per sumber (IN/OUT/BK) | query_4215_gudang_kirim — hanya kirim |
| `rincian_po` | 32.42/32.43 PO | Status "menunggu diproses" |
| `append1` | Pivot 10 metrik + mirror Excel M | ⚠ masih fillna(0) (INV-1 fix di web); DEVIASI=SO−SALDO AKHIR; Selisih IN=BM−IN |
| `helpers` | Pembaca folder/file, kategori, dedup, preflight | baris-persis dedup; multi-file; skip-file log |

**A.2 UI (20 modul `src/ui/`)** — inti: `app.py` (Notebook 10 tab, orchestrator), `widgets.py` (tabel/find/funnel/clone ⛶/freeze), `deviasi_view` (9 CEK + H + ambang + rank), `pivot_view`, `in_selisih_view` (SKOR RESTO), `komparasi_deviasi_view` (file eksternal, Top/Flip, auto-load), `nominal_common` (satu sumber kebenaran nominal), `followup*`, `rincian_po_view`, `export_sheets`, `doc_codes` (RI Balancing/ri_balancing_docs/duplicated_doc_numbers), `details_popup/deviasi_popup` (drill-down).

**A.3 9 label CEK** (`deviasi_view.py:2209-2216`, kondisi port persis): ① RI Balancing ② Beda Tanggal (LET kolom Y) ③ Promix 04 ④ Kosong/Non Aktif ⑤ Hitung Manual ⑥ Turun Drastis ⑦ ACR to BOM (ambang% × Total ACR) ⑧/⑨ kondisi pelengkap blok `np.select` — plus Catatan Audit B1–B4; label ikut fingerprint (dikenetralkan saat matching).

**A.4 Persistensi file lokal desktop** (yang harus dimigrasi/dipetakan): `config.json`(+.bak) → Setting; `settings.json` (window/filter/zoom, acr_threshold_pct) → preferensi user web (filter persist tetap dipertahankan — INV-8); `followup.json`/`followup_resolved.json` → FollowUpCase/Event; `komparasi_last.json` → histori file eksternal; `crash.log` → log service.

## Lampiran B — Pemetaan skema IC → kebutuhan SM-WEB

> Catatan D-5 (SAH): pemakaian berarti **replikasi pola model ke database SM-WEB yang terpisah** — bukan berbagi DB dengan IC.

| Model IC (ada) | Dipakai SM-WEB? | Perlakuan |
|---|---|---|
| `SourceFile` | ✅ | Upload bundle = kumpulan SourceFile (dqStatus/dqErrorCount/dqWarningCount dipakai) |
| `Week` | ➖ (SM-WEB grain hari/H; IC grain minggu) | Dipakai bila display mingguan IC dikonsumsi pada konsolidasi Fase 5 |
| `Outlet`, `Item`, `OutletPIC`, `Setting`, `FileChunk`, `AuditLog`, `DQIssue`, `AggregationCache` | ✅ | Direplikasi ke DB baru (D-5); DQIssue dipetakan kelas sinyal Task 31-c; Setting menampung config.json |
| `InventoryRecord` (48 field) | ➖ | Milik lapisan analisis IC (file laporan resmi). TIDAK dipaksa menampung snapshot SM-WEB — dibuat entitas §8.4 supaya dua lapisan tidak saling mencemari. Saat konsolidasi (Fase 5), kedua grain hidup berdampingan & AI narrative IC dapat membaca keduanya **via API antar-app** (D-5: dua database terpisah) |

## Lampiran C — Glosarium

| Istilah | Arti |
|---|---|
| **SO / COM** | Stock Opname / Cost of Materials (pemakaian aktual) |
| **BOM / ACR** | Bill of Materials (pemakaian teoretis) / **ACR = dokumen penyesuaian Accurate** (kode "ACR." — juga metrik pivot ke-10, kolom 9.ACR); label CEK "ACR to BOM" menyala bila \|Deviasi\| > ambang% × Total ACR |
| **GR / PCS** | Satuan grosir (kg/ltr/dus) vs satuan pecahan (pcs/gram) |
| **IN / OUT / BK** | Sumber barang masuk (42.05+32.24+99.01) / keluar (22.05 tanpa SI) / barang keluar transfer (42.15 kirim) |
| **RI / SJ / PO** | Receipt (32.24) / Surat Jalan internal (42.05) / Purchase Order |
| **Deviasi** | SO − SALDO AKHIR (bertanda, satuan terkecil) |
| **Selisih IN** | BARANG MASUK (rekap) − IN (Accurate) |
| **TANGGAL H** | Cut-off analisa mingguan (7/14/25) |
| **CEK** | 9 label pemeriksaan kanonik (A.3) |
| **Snapshot** | Hasil run terkomit per periode, permanen & terversi (FR-20/24) |
| **definition_version** | Versi definisi deviasi saat run (mis. `3.9.71-noSI`) — INV-4 |
| **DQIssue** | Entri kualitas data (severity/code/message/row) |
| **TL / PIC** | Team Leader outlet / Person In Charge |
| **IC** | Repo Inventory-Control (platform web referensi) |
| **SM-WEB** | Placeholder produk yang didefinisikan PRD ini |

## Lampiran D — Jejak Verifikasi Klaim

Semua klaim kondisi-app dalam PRD ini berasal dari verifikasi kode nyata (bukan asumsi):

- **Task 29–30 (worklog)**: push v3.9.71, sinkron dashboard, CI hijau, 1607/1607.
- **Task 31-a/b/c (worklog, 3 agen riset)**: 5 pemeriksaan CEK (lokasi & kondisi persis: `deviasi_view.py:2102-2216`, `doc_codes.py:124-226`, `fn_audit.py`, `in_selisih_view.py`); snapshot store TIDAK ada (inventarisasi semua titik tulis); followup skema (`followup.py:57-193` — 17 field snapshot, fingerprint md5 9-field, resolved legacy tanpa writer); 42.15 sisi kirim/terima (`fn_4215.py:36-110`, folder Terima4215 config tak dibaca, tanpa nomor dokumen di kolom terbaca); harga 41.09 saat-run saja; pivot fillna(0) (INV-1); definisi deviasi v3.9.69→70→71.
- **Task 32 (worklog)**: struktur Inventory-Control (stack, 12 model Prisma, API routes, infra mini-service), pipeline desktop UI-agnostic (tanpa import Tkinter).
- **Penulisan PRD ini (Task 33)**: re-verifikasi langsung — clone tag `v3.9.71` (`f22bca6`): 16 modul `src/pipeline/` + 20 modul `src/ui/` ≈ 39,4 ribu baris; `config.json` 15 folder + 10 sheet; `requirements.txt` pin pandas<3; daftar 10 tab `app.py:2575-2586`; ⚖ = mode dalam tab 📋 (bukan tab); `InventoryRecord` 48 field; `PRD_RETROAKTIF.md`/`ARCHITECTURE.md` IC sebagai referensi format & pola.

---

*Dokumen ini adalah PRD (keputusan produk). Implementasi teknis detail (skema final, kontrak JSON lengkap, peta file) ditulis di ARCHITECTURE.md pada Fase 0 setelah D-1..D-8 disahkan.*
