# Agent Lokal — "Python di Laptop" (Task 51 + launcher sekali-klik Task 52 + Sumber Data disk lokal Task 53)

> **Idenya:** kamu klik **"Kirim N Folder → Laptop (Proses Python)"** di web →
> Python di laptopmu menjemput job → **menarik file Google Drive ATAU menyalin
> langsung dari folder data di disk lokal, lalu menjalankan engine FastAPI
> (pipeline asli v3.9.71) secara LOKAL** → hasil diunggah ke web →
> **tampil di web sebagai run pratinjau** → kamu menekan **Komit** di web.
> Seluruh pekerjaan berat (unduh/salin 100–300 MB, pipeline 79 ribu baris) terjadi di
> laptop — situs (serverless Vercel) hanya menerima hasilnya, jadi **bebas dari
> batas 60 detik / kuota /tmp / body 4,5 MB**.

## Alur lengkap sehari-hari (Task 54 — "terus aku tekan apa?")

Tidak ada tombol rahasia — seluruh alurnya hanya 5 langkah:

1. **Web** — tab 🚀 *Proses & Ingest* → mode **Produksi** → **centang folder**
   sumber di daftar → (boleh) isi nama run → pastikan **TANGGAL H** & **AMBANG ACR**.
2. **Web** — tekan **“Kirim N Folder → Laptop (Proses Python)”**. Job masuk papan;
   agent online menjemputnya dalam hitungan detik.
3. **Laptop (otomatis, tidak perlu ditekan apa pun)** — agent menyalin Excel dari
   disk C (mode *Disk Lokal / Otomatis*) atau mengunduh dari Drive → engine FastAPI
   lokal memproses (pipeline asli v3.9.71) → hasil diunggah ke web.
4. **Web** — kartu job menunjukkan kemajuan → saat **SELESAI**, pratinjau run
   terbuka otomatis di panel bawah. **Tinjau** (ringkasan, manifest file, isu DQ,
   log pipeline) → tekan **Komit Snapshot** → snapshot periode tersimpan permanen
   (FR-4: tidak pernah menimpa snapshot lama diam-diam — periode sama menandai
   yang lama *SUPERSEDED*).
5. **Web** — buka tab analisis (Deviasi, Selisih IN, PO Menunggu, Pivot, Nominal,
   Follow-Up, Laporan) dan pilih periodenya. Selesai. Bulan berikutnya: ulangi
   langkah 1–5 dengan periode baru.

> **Komit run besar (±88 ribu baris):** komit dipecah jadi langkah-langkah
> singkat yang **bisa dilanjutkan** (Task 54) — tiap langkah menulis sepotong
> data lalu menyimpan posisinya; browser otomatis memanggil lanjutan sampai
> selesai, dengan kemajuan tampil di tombol Komit (baris 12.000 / 88.031 …).
> Komit yang terputus di tengah (listrik/internet/tab tertutup) **cukup ditekan
> Komit ulang** — ia melanjutkan dari posisi terakhir, tidak mengulang dari nol.
> Sisa build yang rusak tampil sebagai **BUILDING (komit terputus)** di tab
> Konfigurasi — setelah ±15 menit bisa dihapus bila mau mulai bersih;
> data lama tidak pernah tersentuh (NFR-3).
>
> **Membersihkan riwayat:** tombol 🗑 per baris run di *Riwayat run* (run demo /
> uji yang menumpuk boleh dihapus). Run yang sudah dikomit ditolak sampai
> snapshot-nya dihapus dulu di tab **Konfigurasi** — snapshot adalah data
> analisis, riwayat hanyalah catatan proses.

## Cara paling gampang — SEKALI KLIK (rekomendasi)

Setelah repo ada di laptop (clone sekali: `git clone
https://github.com/anandategarch/Stock-Monitoring-Web.git`), **dobel-klik SATU
file** — launcher mengurus sisanya:

| Sistem operasi | Cara |
|---|---|
| **Windows** | dobel-klik **`mulai-laptop.bat`** |
| **macOS** | dobel-klik **`mulai-laptop.command`** |
| **Linux** | `./mulai-laptop.sh` |

Saat **pertama kali** dijalankan:
1. Bila token agent belum terisi, muncul dialog kecil (mode terminal: prompt
   sederhana) — **tempel token agent sekali saja** (nilainya sama dengan env
   `AGENT_TOKEN` di server). Token tersimpan di `laptop_config.json` yang
   **otomatis di-gitignore — tidak pernah masuk GitHub**.
2. Launcher otomatis: `git pull` → menyiapkan dependensi engine (memakai Python
   sistem bila kamu sudah pernah `pip install`; atau membuat venv
   `.venv-laptop` dan menginstal sendiri ±1–3 menit sekali jalan) → menyalakan
   engine FastAPI di `:3031` (bila sudah jalan, **dipakai ulang**) → menjalankan
   agent.
3. Dashboard kecil menampilkan **WEB ✓ · ENGINE ✓ · AGENT ✓**, job yang sedang
   diproses, dan log langsung dari engine + agent. Ada tombol **MULAI/BERHENTI**,
   **Buka Web**, **Perbarui GitHub**, **Ubah Token**, dan **Sumber Data**.
4. **Tinggalkan jendela terbuka** selama ingin tetap tersambung — tutup
   jendela (atau Ctrl+C) = putus dengan rapi. Agent punya `autostart` — begitu
   file dibuka semuanya menyala sendiri.

Saat berikutnya: dobel-klik file yang sama — langsung jalan (kode ikut
ter-update otomatis lewat git pull).

## Sumber Data — Google Drive vs DISK LOKAL (Task 53)

Sesuai permintaan ("tidak pakai Google Drive lagi, langsung dari disk C"), agent
bisa membaca Excel langsung dari folder data di disk laptop — **setara
`RootPath` aplikasi desktop**. Atur lewat tombol **Sumber Data** di launcher:

| Pilihan | Perilaku |
|---|---|
| **Otomatis** (default) | Folder yang ada di disk → disalin dari disk; folder yang tidak ada → ditarik dari Google Drive (link yang dicentang di web). |
| **Disk Lokal** | Tanpa Google Drive sama sekali. Folder yang tidak ada di disk diberi catatan jujur di log job (job tetap jalan dengan folder sisanya; bila SEMUA folder absen → job gagal dengan daftar folder yang hilang). |
| **Google Drive** | Perilaku lama — selalu unduh dari Drive. |

**Folder induk data lokal** (contoh: `C:\KERJA\1. RESTO\9.NEW QUERY`) harus
berisi folder bernama sama persis dengan struktur desktop — `"1. DEVIASI
WEEKLY"`, `"2. 22.05"`, `"3.1 42.15 Kirim"`, dst. Pencocokan judul folder
**case-insensitive** (ala Windows). File Excel yang sedang dibuka di Excel
(file kunci `~$…`) otomatis dilewati. Seleksi folder tetap dilakukan di web —
kamu tetap mencentang folder mana yang dikirim ke laptop; yang berubah hanya
**dari mana isinya dibaca**.

Tersimpan di `laptop_config.json` (`data_source` + `local_root`), atau lewat
CLI: `python mulai_laptop.py --source local --root "C:\\KERJA\\1. RESTO\\9.NEW QUERY"`.
Untuk agent manual tanpa launcher: env `SMWEB_DATA_SOURCE` (auto|local|drive)
+ `SMWEB_LOCAL_ROOT`.

Tanpa monitor/GUI (mis. SSH/server tanpa layar) launcher otomatis beralih ke
**mode terminal**; paksa dengan `--console`. Opsi lain: `--once` (proses satu
job lalu berhenti), `--status` (cetak status lalu keluar), `--no-update`,
`--server URL`, `--port N`, `--name NAMA` — `python mulai_laptop.py --help`.

Yang launcher TIDAK lakukan: mengubah engine yang sudah berjalan di `:3031`
milik proses lain (dipakai ulang apa adanya) dan membocorkan token (file
config lokal selalu di-gitignore).

## Cara manual (tanpa launcher) — setara

Syarat: Python 3.8+ (agent **murni stdlib — tanpa pip install**) dan engine
FastAPI dengan dependensinya (sudah ada di repo ini).

## Arsitektur (kenapa "tarik", bukan "dorong")

Web di Vercel **tidak bisa menjangkau laptopmu** (laptop berada di balik NAT
rumahan, tanpa IP publik). Maka arah komunikasinya dibalik — *polling*:

```
[Browser kamu]                         [Laptop — python agent]
1. klik "Kirim … → Laptop"   ──┐
   job QUEUED di DB            │      2. POST /api/agent/claim tiap ±3 dtk (token)
                               └────────────────────────────────▶ "ada job!" → RUNNING
                                     3. tarik file Excel dari Google Drive (lokal)
                                     4. POST /process ke engine FastAPI :3031 (lokal)
3. UI poll job → progress bar  ◀──────────────────────────────── 5. unggah hasil ter-gzip
   "70% Engine FastAPI…"             ter-chunk (aman batas body serverless)
   → SELESAI                        6. POST complete → server merakit + buat RunBatch
4. pratinjau run terbuka       ◀──── 7. KOMIT di web memakai hasil tersimpan —
   → klik KOMIT                      TANPA engine di server (serverless tidak punya)
```

- **Job board** = tabel `AgentJob` di database (Supabase). Kehadiran agent
  ("ONLINE/OFFLINE" di UI) dari *heartbeat* polling-nya.
- **Hasil run agent** disimpan utuh (gzip+base64, tabel `AgentResult`). Komit
  memakai hasil itu — FR-12 tetap jujur: engine deterministik, jadi hasil
  tersimpan = output kanonik run tersebut; situs tidak perlu engine untuk komit.
- **Batal** kapan pun: tombol *Batalkan* — job QUEUED langsung batal; yang
  RUNNING dihentikan agent pada laporan berikutnya (±beberapa detik).

## Cara pakai di laptop (sekali setup)

Syarat: Python 3.8+ (agent **murni stdlib — tanpa pip install**) dan engine
FastAPI dengan dependensinya (sudah ada di repo ini).

```bash
# 1. Ambil repo terbaru
git clone https://github.com/anandategarch/Stock-Monitoring-Web.git
cd Stock-Monitoring-Web

# 2. Install dependensi engine (sekali saja)
cd mini-services/engine-fastapi
pip install -r requirements.txt

# 3. Jalankan engine FastAPI produksi :3031 (biarkan jalan di terminal 1)
python -m uvicorn app:app --host 0.0.0.0 --port 3031     # atau: bun run dev

# 4. Jalankan agent (terminal 2)
cd ../..
SMWEB_SERVER=https://stock-monitoring-web.vercel.app \
SMWEB_AGENT_TOKEN=<token dari admin> \
python3 agent/smweb_laptop_agent.py
```

Agent akan menulis `Menunggu job…` — begitu kamu klik **Kirim … Folder →
Laptop (Proses Python)** di tab **🚀 Proses & Ingest** (mode *Produksi*,
centang link Drive yang mau diproses), agent menjemputnya dalam beberapa detik.
Sesudah selesai, pratinjau run terbuka otomatis di web — tinggal **Komit Snapshot**.

### Variabel environment agent

| Variabel | Default | Keterangan |
|---|---|---|
| `SMWEB_SERVER` | `http://127.0.0.1:3000` | URL web (produksi: `https://stock-monitoring-web.vercel.app`) |
| `SMWEB_AGENT_TOKEN` | `smweb-dev-agent-token` | **WAJIB** di produksi — sama dengan env `AGENT_TOKEN` di Vercel |
| `SMWEB_ENGINE_URL` | `http://127.0.0.1:3031` | URL engine FastAPI lokal |
| `SMWEB_AGENT_NAME` | `laptop-<user>` | Nama yang tampil di badge "AGENT ONLINE" |
| `SMWEB_AGENT_WORKDIR` | `agent/smweb-agent-work` | Folder kerja sementara (dibersihkan tiap job) |

Argumen `--once` = proses satu job lalu keluar (berguna untuk uji).

## Batas & perilaku jujur

- Maksimal **16 link Drive** per job, **300 file**, **60 MB per file**,
  **400 MB total** — sama dengan tarikan di sisi server.
- Hasil unggah dipecah potongan ±2 MB (gzip): 79 ribu baris nyata hanya
  ±0,7 MB ter-gzip — jauh di bawah batas.
- Job RUNNING yang heartbeat-nya hilang ≥15 menit (laptop mati/koneksi putus)
  otomatis ditandai GAGAL dengan pesan jujur; file rusak/bukan Excel dilewati
  dan dilaporkan — sama seperti tarikan server.
- Hanya **satu job aktif** dalam satu waktu (antrean sederhana; buat lagi
  setelah selesai/batal).
- `AGENT_TOKEN` **wajib** diatur di Vercel — tanpa itu endpoint agent menolak
  jujur (HTTP 503) demi keamanan. Ganti token = redeploy.
