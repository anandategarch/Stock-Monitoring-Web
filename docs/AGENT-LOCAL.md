# Agent Lokal — "Python di Laptop" (Task 51)

> **Idenya:** kamu klik **"Kirim N Folder → Laptop (Proses Python)"** di web →
> Python di laptopmu menjemput job → **menarik file Google Drive + menjalankan
> engine FastAPI (pipeline asli v3.9.71) secara LOKAL** → hasil diunggah ke web →
> **tampil di web sebagai run pratinjau** → kamu menekan **Komit** di web.
> Seluruh pekerjaan berat (unduh 100–300 MB, pipeline 79 ribu baris) terjadi di
> laptop — situs (serverless Vercel) hanya menerima hasilnya, jadi **bebas dari
> batas 60 detik / kuota /tmp / body 4,5 MB**.

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
