"""
app.py — Shell UI Stock Monitoring vX.Y.Z.

Struktur jendela (ala aplikasi Waste):
    ┌────────────────────────────────────────────────────┐
    │ ⬛ Toolbar gelap: 📊 judul + vX.Y.Z  + [💾 Export] │
    ├────────────────────────────────────────────────────┤
    │ Tab modern ber-ikon (10 tab, fungsi tidak berubah) │
    ├────────────────────────────────────────────────────┤
    │ Konten card-based per view (tabel lebar & besar)   │
    ├────────────────────────────────────────────────────┤
    │ StatusBar: ● status data + ringkasan baris          │
    └────────────────────────────────────────────────────┘

10 tab:
  1. ⚙️ Config          : RootPath + info config
  2. 🚀 Proses          : kontrol pipeline + KPI + konsol log gelap
  3. 📊 Pivot Table     : pivot matrix Excel-like (per resto default,
                          rentang tanggal default 26 BULAN LALU s/d 31
                          BULAN BERJALAN — v3.6)
  4. 📦 DEVIASI GR      : wide matrix + CEK anomaly (satuan GR) + ✓
                          (input TANGGAL H + Apply H — satu-satunya;
                          spinbox AMBANG ACR to BOM — v3.9.21) + kolom
                          Nominal (v3.9.34)
  5. 🧩 DEVIASI PCS     : wide matrix + CEK anomaly (non-GR) + ✓
                          (chip H read-only, ikut tab GR — v3.9;
                          spinbox ambang ACR sinkron — v3.9.21) + kolom
                          Nominal (v3.9.34)
  6. 📤 Rekap Selisih IN: SATU tabel IN (Accurate) vs Barang Masuk +
                          kolom SO + kolom Hasil Audit (logika macro VBA ×
                          data app — v3.6, tanpa sheet 29) + drill-down
  7. 📋 Laporan Deviasi : 3 MODE — ⚖ Komparasi File Deviasi (default,
                          v3.9.4; + kolom Nominal harga × GR Saat Ini —
                          v3.9.34) & 🚨 Anomali COM (v3.9.3) & 💰 Nominal
                          (H) (v3.9.32) + ✓
  8. 🧮 NOMINAL DEVIASI : Σ (Harga 41.09 × Qty Deviasi) per resto +
                          baris TOTAL + double-click resto → popup
                          rincian per barang (v3.9.34)
  9. ☑ Follow Up        : daftar baris tercentang + export (v3.2)
 10. 🛒 Rincian PO      : rekap PO + item (baris teal/putih, v3.9)

v3.9.34 ringkas (kolom Nominal di mana-mana + tab Σ per resto):
- Kolom Nominal (Harga 41.09 × Qty Deviasi) di tab 📦 Deviasi GR &
  🧩 Deviasi PCS (kolom Out_H/BK_H dihapus dari tampilan) dan di mode
  ⚖ Komparasi (harga × GR Saat Ini) — perhitungan = helper bersama
  src/ui/nominal_common.py (satu sumber kebenaran dgn mode 💰 Nominal
  (H)); app meneruskan harga_map/konversi_map audit_result ke view.
- TAB BARU 🧮 Nominal Deviasi: Σ nominal per resto + baris TOTAL +
  double-click resto → popup rincian per barang (user: "isinya total
  sum ... yang dapat dari harga × kuantitas deviasi, cuman ini disum
  per resto").

v3.7 "ENGINE TURBO" + DEEP AUDIT FIXES ringkasan:
- ENGINE 3,5-4× LEBIH CEPAT (output terverifikasi IDENTIK vs v3.6):
  * fn_running_stock_grouped vektor (global segmented cumsum):
    6,68s → 0,19s di real-data (36×); 6 edge-case sintetis ==
    implementasi lama (termasuk kasus baris bulan-lalu ber-net ≠ 0
    yang terlewat benchmark awal — tertangkap unit-test).
  * InformationGrouped vektor (pre-dedupe + agg C-level):
    6,7s → 0,05s (130×); 0/80.069 grup beda di real-data.
  * Reader rekap single-parse (jalur calamine): peek+full = 2× parse
    → 1× (peek nrows=8 di calamine mem-parse seluruh sheet juga).
  Pipeline real-data: 20,6s → 4,9s. Gunakan python-calamine (sudah di
  requirements.txt) supaya baca Excel pakai engine Rust.
- FIX 9 BUG fitur v3.6 (akar: setelah kolom disembunyikan, posisi
  display ≠ index logis values[] Treeview):
  * filter clone ⛶ membaca nilai kolom yang salah (kini: index logis)
  * auto-fit mengukur nilai kolom yang salah (kini: index logis)
  * filter '#0' clone pivot memakai text anak (metric) → semua baris
    hilang (kini: text parent = nama barang)
  * drill-down pivot ke resto/tanggal keliru setelah hide (kini:
    identify_to_column → nama kolom)
  * double-click copy Nomor/Nomor PO popup ambil kolom salah (2 popup)
  * toggle ✓ (Deviasi GR/PCS + Laporan + Follow Up) terpicu dari kolom
    lain setelah ✓ disembunyikan (kini: cocok nama kolom)
  * posisi popup filter melenceng (dulu ikut menghitung kolom
    tersembunyi + #0 phantom)
  * mirror hide/unhide clone↔sumber: state colmgr kini tersinkron
    (panel Kolom sumber tidak lagi menampilkan checkbox basi)

v3.6 ringkasan:
- BUG FIX KRITIS: tombol filter ⧩ di header TIDAK BISA DIKLIK dengan
  mouse (identify_column mengembalikan '#N' posisi-display sedangkan
  filter memakai nama kolom simbolik — tidak pernah match). Kini klik
  funnel membuka popup di SEMUA tabel, termasuk saat ada kolom
  tersembunyi. Clone ⛶ Perbesar juga kini punya filter + sort sendiri
  (sebelumnya ikon funnel tersalin tapi mati).
- HIDE/UNHIDE KOLOM: klik kanan judul kolom (Sembunyikan kolom ini /
  Tampilkan semua / auto-fit / filter) + tombol ◱ Kolom (panel
  checklist) — di semua tabel & window ⛶.
- AUDIT REKONSILASI DARI DATA APP: sheet '29 Rekap Barang Masuk' TIDAK
  dibaca. Tabel Rekap Selisih IN jadi SATU (segment dihapus) dengan
  kolom baru Hasil SO + Saldo + Hasil Audit + Catatan — semua bisa
  difilter ⧩. Catatan: kolom Barang Masuk terisi saat rekap memiliki
  input JENIS='BARANG MASUK'; selama belum diinput, baris ber-IN akan
  ditandai deviasi (sesuai logika).
- DEFAULT TANGGAL (v3.8): Pivot Table -31 s/d 31 = kolom tanggal
  lengkap tgl 25-31 BULAN LALU (label 25• s/d 31•, urut kronologis)
  lalu 1-31 bulan berjalan; Rekap Selisih IN 1 s/d 31 = bulan BERJALAN
  saja (tanpa bulan lalu).

Pipeline tetap dijalankan di thread terpisah; log stdout dipipakan lewat
queue thread-safe; Stop button mengirim stop_event yang dicek pipeline di
checkpoint major. Freeze-fix v2.1.1 (batch log + truncate) dipertahankan.
"""
import contextlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

# Suppress openpyxl noise warnings (no default style, etc.)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd

# Pastikan parent folder di sys.path agar `from src...` jalan
# v3.9.62 — _BASE frozen-aware: dihitung INLINE (bootstrap — sys.path
# harus siap SEBELUM import src.*); modul bersama app_base_dir() dari
# src/config.py (dipakai CONFIG_PATH/_SETTINGS_PATH) di-import SETELAH
# sys.path siap — mode PyInstaller → base = folder .exe.
_BASE = (Path(sys.executable).resolve().parent
         if getattr(sys, "frozen", False)
         else Path(__file__).resolve().parent.parent.parent)
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from src.config import app_base_dir as _app_base_dir
from src.main import PipelineStopped, run_pipeline
from src.pipeline.helpers import (
    read_cache_invalidate,
    read_cache_reset_counters,
    read_cache_stats,
)
from src.ui.deviasi_view import (
    DeviasiView,
    SharedACRThreshold,
    SharedPivotCache,
    SharedTanggalH,
    load_acr_threshold,
)
from src.ui.export_sheets import add_pivot_sheet
from src.ui.followup import FollowUpStore
from src.ui.followup_view import FollowUpView
from src.ui.in_selisih_view import InSelisihView
from src.ui.komparasi_deviasi_view import KomparasiDeviasiView
from src.ui.laporan_deviasi_view import LaporanDeviasiView
from src.ui.nominal_deviasi_view import NominalDeviasiView
from src.ui.nominal_resto_view import NominalRestoView
from src.ui.pivot_view import PivotTableView
from src.ui.refresh_sources import RefreshSourcesDialog
from src.ui.rincian_po_view import RincianPoView, _resto_name
from src.ui.theme import (
    C_AMBER,
    C_BG,
    C_CARD,
    C_GREEN,
    C_HEADER,
    C_ORANGE,
    C_RED,
    C_TEXT_MUTED,
    apply_theme,
    ctrl_wheel_dispatch,
    font,
    rescale_named_fonts,
    set_ui_scale,
    set_zoom_wheel_handler,
)
from src.ui.widgets import (
    AccentButton,
    DangerButton,
    GhostButton,
    KpiCard,
    KpiRow,
    LoadingOverlay,
    NotebookTabTooltips,
    SegmentBar,
    Spinner,
    StatusBar,
    Toolbar,
    auto_fit_columns,
    fmt_int_id,
    gc_shield_acquire,
    gc_shield_release,
    install_wheel_router,
    make_log_console,
    make_tree,
    open_tree_find,
    run_async,
)

# --- Konstanta UI -----------------------------------------------------------
APP_TITLE = "Stock Monitoring"
APP_VERSION = "3.9.71"  # v3.9.71 — TANPA KODE SI 22.05 + FREEZE KOLOM NAMA BARANG PIVOT (user: "22.05 tanpa kode SI ya maaf aku lupa bilang kemarin" — lanjutan v3.9.70 "semua kode masuk": Nomor # berawalan SI. dikecualikan, ACR./RETUR./dll. tetap masuk; + "di tab pivot tabel gak bsia freeze kolom nama barang ya? sehingga jika aku scroll ke kanan bisa kefreze"): (1) fn_2205 TANPA KODE SI — mask SI case-sensitive (mirror M Text.StartsWith; "si." lowercase + Nomor # kosong/None BUKAN SI), 'Nomor #' kembali jadi kunci filter TAPI tetap BUKAN kolom wajib identitas (hilang → baris diproses APA ADANYA + WARNING keras — ikut status amber pola §82b, kode SI jadi tak teridentifikasi); baris SI yang dikecualikan diberitahu via [fn_2205] INFO (bukan warning — jejak observabilitas filter bisnis yang disengaja); queries.query_out disinkron. (2) FREEZE-PANE PIVOT — widgets.FrozenNamePane BARU: DUA tree iid-identik (kiri = #0 nama barang + baris metric, kanan = kolom matrix dgn #0 width-0 + _autofit_skip), scroll vertikal + seleksi TERSINKRON DUA ARAH (guard utama KESAMAAN SELEKSI — flag tak melintasi antrean event <<TreeviewSelect>>: smoke pertama HANG ping-pong tak terbatas), hsb hanya milik sisi matrix → nama barang TIDAK bergeser saat scroll ke kanan (kontrak freeze ala Excel); funnel ⧩ Nama Barang pindah ke heading tree beku (HeaderFilter + screenshot/tes disinkron); auto-fit DUA sisi (sisi beku diukur di on_done batch kiri sendiri — tabel kecil: batch kanan selesai SINKRON sebelum insert kiri jalan); clone ⛶ Layar Penuh IKUT freeze (open_tree_maximized frozen_name=True OPT-IN — 12 view lain tak tersentuh; attach_clone_filters param filter_tree: funnel menempel di sisi beku, baris difilter di tree utama clone, hook _clone_filter_apply dipasang di KEDUA sisi utk kompatibilitas test; pasca filter/sort clone sisi beku disalin ulang mirror_from_right). VERIFIKASI: §84 BARU 11 check (freeze kontrak utama + iid/teks identik + yview 2-arah + seleksi 2-arah + xview beku tetap 0.0-1.0 + auto-fit tak membuka #0 + clone 2 sisi tersinkron pasca filter + SI case-sensitive/None/log-bersih) + §83a-1/a-2 & §79c/§79d disinkron (SI kembali tersaring; tanpa Nomor # kini WARNING jujur — dulu v3.9.70 senyap) + §0 versi 3.9.71. # v3.9.70 — AUDIT ULANG v3.9.69 (P2 CACHE SAAT EVIKSI) + 2205 SEMUA KODE MASUK (audit eksternal commit d0734ca: perbaikan cache v3.9.69 masih menyisakan entry lama di dict ketika eviksi dimulai; user: "pada file 2205 sekarang tidak perlu filter kode ACR lagi tapi semua kode masuk perhitungan"): (1) P2 AKUNTANSI CACHE SAAT EVIKSI — _read_cache_put kini MELEPAS entry lama key-sama dari dict (pop) SEBELUM eviksi FIFO → kontribusi selnya dikembalikan SEKALI (fix v3.9.69 hanya mengurangi counter TANPA melepas entry → bila entry lama ikut ter-eviksi FIFO, selnya dikurangi DUA KALI; contoh audit batas 100: A=30 B=40 C=20 → ganti A→50 → eviksi hapus A-lama → counter 80 padahal isi dict 110 — cache melewati batas; counter bisa negatif → keputusan eviksi/tolak kacau); frame yang melebihi batas maksimum SENDIRIAN kini DITOLAK SEBELUM eviksi (dulu loop eviksi mengosongkan SELURUH cache demi frame yang akhirnya ditolak guard juga — audit: "tangani frame yang melebihi batas sebelum menghapus cache lain"); dampak pengendalian memori/performa cache, bukan kebenaran data; TES BARU persis rekomendasi audit: ganti entry-tertua saat cache hampir penuh + frame lebih besar dari batas maksimum. (2) 2205 SEMUA KODE MASUK PERHITUNGAN (permintaan user) — fn_2205: filter M Text.StartsWith([#"Nomor #"], "ACR") DIHAPUS — seluruh dokumen penjualan 22.05 (SEMUA Nomor # — ACR./SI./RETUR./dll.) kini masuk sumber OUT; 'Nomor #' TAK LAGI kolom wajib (bukan lagi kunci filter — hilang pun baris tetap diproses; identitas cukup Nama Pelanggan + Nama Barang); queries.query_out ikut disinkron ("22.05 sales (ACR) only" basi). VERIFIKASI: §83 BARU 5 check (fn_2205 semua kode masuk · tanpa kolom 'Nomor #' aman tanpa warning · ganti entry-tertua hampir-penuh: counter == Σ sel dict tanpa dobel-kurang · entry hasil ganti tersaji benar · frame > batas ditolak tanpa mengosongkan cache) + §79c/§79d disinkron (3 baris — fixture memang memuat baris SI; dulu tersaring) + §0 versi 3.9.70. # v3.9.69 — PERBAIKI SEMUA BUG HASIL VALIDASI AUDIT EKSTERNAL KE-2 (user: "perbaiki semua bug" — audit kedua tervalidasi 100% akurat di Task-24, semua temuan masih-open dieksekusi penuh): (1) P1.1 ☑ HIDE-EMPTY PIVOT — "kosong" = SEMUA sel baris 0/kosong (dulu "total ≤ 0": baris cancel-out/retur seluruh-negatif & +10/−10 tersembunyinya padahal deviasi negatif justru sinyal penting; label checkbox kini "semua sel 0"; konsisten di DUA jalur — render _compute_payload + daftar ⧩ #0 _name_values: tiap baris df = satu sel → "ada ≥1 nilai ≠ 0" ≡ "≥1 metric tak semua-nol", daftar popup tak pernah menawarkan barang yang barisnya pasti tersembunyi); (2) P1.2 PERINGATAN SKEMA MENAIKKAN STATUS — _PIPELINE_WARN_RE menghitung peringatan format modul pipeline ([fn_XXXX] WARNING · [WARNING] combine_folder/4217/File harga/Harga 41.09 · [Append1] WARNING) di _poll_log_queue → _schema_warnings → status akhir "SELESAI DENGAN PERINGATAN" + bagian "N peringatan format file sumber (skema kolom berubah — lihat log)" (dulu hanya [WARNING] Skip file yang dihitung; peringatan hardening v3.9.67 lenyap di balik status HIJAU padahal data sumber berpotensi lenyap/nyasar; Skip file TETAP lewat _skipped_files anti hitung-ganda; peringatan UI sengaja tak dihitung; KONTRAK §82b: pola wajib menangkap SEMUA literal WARNING pipeline, format baru tanpa update pola = tes gagal); (3) P2.1 AKUNTANSI CACHE BACA — _read_cache_put menimpa key-sama kini MENGEMBALIKAN sel entry lama dulu (skenario audit 100→150 dulu counter 250 → eviksi prematur/entry baru ditolak guard; pemicu nyata sig-mismatch mtime+size antar-run tanpa Refresh eksplisit; dampak performa saja, bukan kebenaran data); (4) P2.2 CONFIG STARTUP DEFENSIF — akar non-dict (JSON list) & Folders/Sheets non-dict kini TERTANGANI + tampil jujur di area Info Config (baris ⚠ / ERROR, pola defensif _config_dpi_aware), RootPath non-str dikosongkan aman — dulu AttributeError `.get`/`.items()` di __init__ → crash.log + dialog, app tak jalan; (5) MINOR: run_tests.sh kini MENJALANKAN test_mock.py juga (setara job CI); harness screenshot +4 skenario sisa audit (25 filter-persist lintas-sesi via app kedua + settings temp anti side-effect · 26 hide-empty negatif · 27 data-parsial SELESAI PARSIAL jalur _load_view nyata · 28 clone ⛶ deviasi); docstring run_app.py bebas literal versi (masih v3.9.66 basi); row_fingerprint escape pipe — backward-compat: hash IDENTIK utk data bebas-pipe, beda HANYA utk nilai ber-pipe yang memang ambigu sejak awal. VERIFIKASI: §82 BARU (semantik pivot + kontrak pola warning + akuntansi cache + config defensif + fingerprint + harness static) + baterai penuh + ruff baseline + gerbang CI hijau pra-rilis. # v3.9.68 — GERBANG TES CI + EKSEKUSI AUDIT UI/UX EKSTERNAL (audit pihak ketiga 6 temuan, semua tervalidasi akurat lalu dijalankan): (1) T3 GERBANG TES — workflow GHA kini menjalankan test_ui_redesign (Xvfb 1920×1080) + test_mock + ruff (gerbang baseline ≤201, pin ruff==0.17.1) + py_compile + validasi config.json + smoke 2 entry di ubuntu-latest SEBELUM build EXE (build-windows needs: tests) + tes ikut jalan tiap push main/PR — rilis tidak lagi hijau hanya karena build sukses; (2) T1 TRI-STATE seleksi ⧩ kosong — restore kini memulihkan [] sebagai set() (filter aktif "0 baris" — dulu DIBUANG, tabel tampil semua baris lagi padahal user sengaja memilih nol) + HeaderFilter.set_selected tak lagi menelan koleksi kosong sebagai None (corong tetap menyala) + pesan jujur "0 baris — semua nilai tidak dipilih pada filter ⧩ 'X'…" di 10 titik render 9 view (deviasi GR/PCS, pivot, laporan, nominal, nominal-resto utama+anak tab, followup, rincian PO, rekap IN, komparasi); (3) T2 OBSERVABILITAS persist — kegagalan LOAD (buffer _FILTER_LOAD_WARNINGS di-flush setelah StreamToQueue aktif) / SAVE / SNAPSHOT / RESTORE per-view kini DI-LOG + statusbar ringkas (dulu senyap total — debugging "filter saya hilang" mustahil); restore TETAP sekali per sesi (retry akan menimpa kerja user — kontrak v3.9.33); (4) T5 TOOLTIP GRUP TAB — hover baris tab → label PENUH + kelompok alur kerja (Operasional / Pemeriksaan & Rekonsiliasi / Analisis / Tindak Lanjut; NotebookTabTooltips widgets.py; urutan tab sudah sesuai kelompok — tanpa sidebar/redesign); (5) T6 SUBTAB 🧮 aktif ikut disimpan & dipulihkan (dulu selalu kembali 'Per Resto'); (6) T4 HARNESS SCREENSHOT v2 — versi dinamis ikut APP_VERSION + 9 skenario baru (nominal per-resto / anak tab tanpa harga / zoom 50-80-100-200 / tabel kosong jujur / corong aktif / popup filter deviasi / jendela kecil). VERIFIKASI: §80/§81 BARU + baterai penuh + ruff baseline + GHA 'Gerbang Tes' hijau sebelum rilis. v3.9.67 — HARDENING KETAHANAN FORMAT EXPORT ACCURATE (user: "program ini kan banyak ambil dari beberapa file tarikan dari accurate online. misal suatu saat format tarikan dari accurete berubah aman gak? misal pada file 9901. ada beberapa koom yang tidak terpakai hilang apakah berpengaruh? umum nya perubahan file ada tambahan kolom ataupun kolom yang tidak terpakai hilang"): AUDIT KETAHANAN FORMAT + TUTUP 2 CELAH SENYAP (nol perubahan perilaku data — murni observabilitas). Eksperimen empiris 6 varian mutasi file 9901 + 5 varian 22.05 (tambah kolom di tengah / hapus kolom tak terpakai / reorder / rename kolom terpakai / hapus kolom VALUE / geser baris header) MEMBUKTIKAN: (A) AMAN-BY-DESIGN utk kasus yang user sebut — tambah kolom & hilangnya kolom tak terpakai = output IDENTIK baris+qty (semua reader seleksi kolom BY-NAMA bukan posisi; concat by-name union kolom; fn_9901 fleksibel kandidat persis→substring dgn exclude harga/nilai; fn_4109 & fn_rekap_mentah deteksi baris header DINAMIS scan-by-nama; nama sheet pun tahan: 9901 baca SEMUA sheet, keluarga punya fallback prefiks modul + key config Sheets). (B) 2 CELAH SENYAP ditemukan & DITUTUP: (1) fn_9901 — rename header terpakai ('Nama barang'→'Nama Item') + kolom lain ber-substring 'barang' terisi ('Kode Barang') → fallback _find_column SALAH-IKAT SENYAP (uji nyata: Nama Barang nyasar ke kode 'GL001'/'KP001', qty/resto benar, NOL warning; barang lalu tak cocok sumber lain → tersekat pivot tanpa jejak) → kini SETIAP pengikatan lewat fallback DI-LOG WARNING lengkap label→kolom tujuan; (2) keluarga header_row=4 (fn_2205/fn_3224/fn_4205/fn_4215) — kolom VALUE ('Kuantitas'/'Kts (Unit#1)'/'#Qty. Terkecil'/'Kts Diterima') & 'Tanggal' hilang/di-rename → dulu NA SENYAP (qty sumber lenyap dari pivot tanpa jejak log) → kini WARNING keras di titik NA-fill (n baris + nama kolom + sumber). Degradasi per-sumber TETAP (sumber lain jalan, tak pernah KeyError total — pola audit fix 48-a/61-a); semua WARNING tampil di log console internal (stdout→StreamToQueue). VERIFIKASI: §79 BARU (9 cek: kontrak permanen output-identik tambah/hapus/reorder + fallback-bind 9901 ter-log + VALUE-missing ter-log 4 reader + Tanggal-missing 2205) + eksperimen mutasi 11 varian + baterai penuh + ruff baseline. v3.9.66 — FILTER PERSISTEN ANTAR SESI (user: "kerjakan quick win" — roadmap Wave 1 quick-win #1, pola Snipe-IT, generalisasi persist ui_zoom v3.9.65): kombinasi filter terakhir PER TAB kini diingat antar sesi — zoom 80% sudah diingat sejak v3.9.65, FILTER belum. (1) CAPTURE saat jendela ditutup (_on_close_window → _capture_filter_state semua view → _save_filter_state settings.json key 'filter_state', read-modify-write atomik pola window_state; TIDAK menimpa bila sesi belum pernah run pipeline — append1_df None → state tersimpan lama dipertahankan). (2) RESTORE SEKALI sesudah fan-out load_data run pipeline PERTAMA sesi berikutnya (_apply_saved_filters_once — load_data me-reset filter v3.9.33, restore menyusul DI ATASNYA; run pipeline BERIKUTNYA di sesi yang sama TETAP RESET — restore tak pernah menimpa kerja user; data kosong → tunda ke run berikut; gagal per-view diisolasi ke log pola _load_view). Cakupan 10 view + state app: Pivot (mode 🏪/📅, RESTO/SOURCE/KATEGORI, rentang TANGGAL, checkbox baris kosong, ⧩ Nama Barang #0) · Deviasi GR & PCS (⧩ semua kolom + combobox KATEGORI + AKTIF/NON — nilai divalidasi vs values data baru, pola preserve v3.9.42) · Rekap Selisih IN (MODE HITUNG Bulan Ini/Lalu+Ini, rentang TANGGAL, checkbox Hanya Selisih ≠ 0, ⧩ — default kategori v3.9.22 tetap, snapshot ⧩ KATEGORI eksplisit menimpanya) · ⚖ Komparasi (3 checkbox semua-minggu/bulan/resto + ⧩ tabel utama + 2 tabel analisa Top/Flip) · 📋 Laporan & 💰 Nominal (⧩) · 🧮 Nominal Deviasi (⧩ + KATEGORI tabel Per Resto + anak tab Tanpa Harga: ⧩ + KATEGORI global) · ☑ Follow Up (⧩) · 🛒 Rincian PO (⧩ + CABANG/STATUS divalidasi) · MODE tab 📋 (SegmentBar Komparasi/Anomali/Nominal — key '_app.laporan_mode', dipulihkan via show_laporan_mode jalur persis klik user). TIDAK ikut: TANGGAL H (jendela data bersama dgn default dinamis dari data v3.9.22), AMBANG ACR (ambang analisa), path file deviasi ⚖ (sumber data — auto-load v3.9.53), tab aktif sub-notebook 🧮 (pemilih tampilan). (3) SERIALISASI defensif widgets.py col_sel_to_json/col_sel_from_json/apply_col_sel_restore: set|None → list terurut (JSON-safe); pemulihan hanya kolom yang MASIH ada di view + nilai string; seleksi KOSONG (set() = "0 baris" semantik v3.9.13) TIDAK PERNAH dipulihkan (anti tabel-kosong-misterius); ikon corong dipasang ulang via set_selected (pola preserve v3.9.42 — tanpa ini funnel mati padahal filter aktif). VERIFIKASI: §78 BARU + baterai penuh + ruff baseline. v3.9.65 — RANK PER-BARIS + STARTUP ZOOM-OUT (dua permintaan user): (1) FIX BUG RANK tab 📦 Deviasi GR & 🧩 Deviasi PCS (user: "ada bug pada deviasi gr dan deviasi pcs pada kolom rank, dimana data rank sama semua untuk tiap grup barang") — era v3.9.51-64 rank = PER BARANG (Σ|Deviasi| kelompok, SATU angka konstanta seluruh baris grup — warisan display merge-vertikal yang tak ada lagi sejak v3.9.60/61) → user melihat angka sama di tiap grup = dilaporkan bug. RESTORASI SEMANTIK SHEET ASLI: Rank = peringkat |Deviasi| BARIS di antara baris GRUP barangnya (1 = deviasi terbesar dalam grup, per resto), method="min" (seri berbagi rank, rank berikut MELONCAT — diprove pola 13,13,13,16 sheet asli), baris Deviasi==0/NaN → rank KOSONG (972/972 baris nol di sheet asli kosong). GROUND-TRUTH: kolom Rank sheet DEVIASI GR/PCS workbook asli user direkonstruksi & dibandingkan — 1347/1348 EKSAK (selisih tunggal = artefak rumus basu di file user sendiri: Susu Kental Manis DPKMAR tertulis 18, matematis 17). (2) STARTUP ZOOM-OUT (user: "bisa gak waktu aku buka udah ke zoom out") — app TERBUKA di zoom 80% (UI_ZOOM_DEFAULT 0.8): font/rowheight/kolom ter-skala sejak buka → lebih banyak baris terlihat; ukuran/maximize jendela tetap dikuasai restore window_state (zoom startup FONTS-ONLY via _apply_ui_zoom(target, resize_window=False) — jendela TIDAK ikut mengecil); CTRL+roda tetap resize penuh (perilaku v3.9.48 utuh; state baseline __init__ = 1.0 supaya penerapan startup selalu efektif). PLUS PERSIST: level zoom terakhir DISIMPAN ke settings.json (window_state.ui_zoom, validasi 0.5–2.0, tolak bool/string) saat jendela ditutup → buka berikutnya memulai di preferensi user (default 0.8 bila belum ada). VERIFIKASI: probe ground-truth rank (803+545 GR match) + probe zoom startup + §58 konstanta 0.8 + §61/§62 kontrak rank per-baris dirombak + §65 +ui_zoom + §77 BARU (ikat 1,1,1/loncat 1,1,3/nol kosong/sort Rank/persist round-trip+validasi+jalur close/startup dari settings.json via app kedua Toplevel). v3.9.64 — DEEP AUDIT 3-AGENT PARALEL (user: "Deep audit dan fix semua sebar agent no mistakes") — semua temuan audit 15-a/15-b/15-c difix: (1) HIGHLIGHT Ctrl+F KINI BENAR-BENAR TAMPIL di SEMUA tabel ber-tag latar baris (FIX 15-c F-01, BUG paling serius — prioritas tag Treeview = URUTAN CREATE, diuji pixel-probe Xvfb: find dibuat SETELAH zebra → oranye kalah & tak dirender di 🧮 kedua tree/📋 3 mode/☑ Follow Up/Rekap IN/Rincian-PO/Pivot; FIX = konstanta+register_find_tags di theme.py, dipanggil BARIS PERTAMA setup_tree_tags + _setup_tags 12 view — urutan list tag per-item TIDAK berpengaruh, diuji); (2) Ctrl+F kini JALAN DI DALAM popup rincian (DetailsPopup/DeviasiPopup/InDetailPopup) + window clone ⛶ (install_tree_find_binding — bindtag Toplevel sendiri tak memuat binding root) + popup Cari SELALU SATU app-wide (dulu 2 popup bisa koeksis utk 2 tree); (3) STALE-FIND pasca re-render (15-c F-03): iid posional row_N dipakai ulang view → highlight mendarat di baris SALAH senyap — FIX dua lapis: choke point insert_tree_items → _on_tree_rerendered (recompute otomatis) + validasi digest baris saat navigasi; (4) KLASIFIKASI KATEGORI word-boundary \bCOM\b/\bPACKAGING\b (15-a R1 — 'COMMERCIAL'/'COMPLIMENT' tak lagi terhitung COM, 'REPACKAGING' bukan PACKAGING; varian kanonik - RESTO/- CATERING tetap cocok); (5) _compute_resto() tanpa argumen tak lagi menghasilkan anak tab kosong (15-a R3 — pakai df bukan param data); (6) _refresh data-kosong kini MEMBERSIHKAN kedua tabel + tag per-cell (15-a R4 — dulu baris lama tersisa dgn status 'Belum ada data'); (7) minus merah PER-CELL anak tab Tanpa Harga (15-a N9, parity tabel utama) + refresh_icons ⧩ anak tab (N8) + fmt_pct_cell ribuan '+1.234,5%' & round-0 '0,0%' tanpa tanda (N11) + sort ⧩ '+12,5%' kini numerik (F-05) + dead code _event_col_name dihapus (N7); (8) run_tests.sh tanpa hard-require xdpyinfo (F-06 — fallback probe Tk; Xvfb hidup dicek walau x11-utils absen); (9) README root disinkronkan (F-02 — masih headline v3.9.62). VERIFIKASI: §76 BARU + baterai penuh + ruff baseline + tag v3.9.64 → GHA rilis .exe. v3.9.63 — RESTRUKTURISASI TAB 🧮 NOMINAL DEVIASI (user: 'kolom N Barang dan Tanpa harga hapus aja diganti dengan nominal deviasi per kategori ... dan itu buat anak tab baru di nominal deviasi yang menampilkan secara global'): (1) KOLOM BARU 'COM Deviasi' + 'Biaya Packaging' (Σ nominal pasangan per klas kategori — substring COM/PACKAGING; kategori lain hanya masuk kolom total) + 'Persen Kenaikan/Penurunan' ((H−Lalu)÷|Lalu|×100 — sort numerik %-aware + minus merah; kolom lama N Barang & Tanpa Harga DIHAPUS dari tabel); (2) ANAK TAB BARU 'Tanpa Harga' (sub-notebook tab 🧮): daftar barang tanpa harga GLOBAL semua resto & kategori — TIDAK terikat filter kategori tab Per Resto (pasangan_tanpa_harga_global) + kolom Kategori + combobox KATEGORI sendiri default 'Semua' (memilih 'Deviasi (COM + Packaging)' → hanya menampilkan sesuai kategori itu) — menggantikan popup double-click kolom Tanpa Harga; (3) app._primary_scrollable kini primary_tree() utk view ber-anak-tab (fallback router roda = tree anak tab AKTIF). v3.9.62 — IMPROVE dari riset referensi GitHub (4 fitur, tanpa dark-mode & login multi-user sesuai permintaan): (1) CARI DI TABEL Ctrl+F (find-window ala tksheet, in-house tanpa dependensi: substring case-insensitive semua kolom + highlight + navigasi Enter/Shift-Enter + status i/N — tabel 29k baris akhirnya bisa dicari); (2) SORT NATURAL campuran angka+teks ("Barang 2" < "Barang 10" — dulu leksikografis terbalik; fallback sort_tree_by_column + daftar nilai popup filter); (3) RILIS .exe OTOMATIS (GitHub Actions + PyInstaller onedir + build_exe.py + run_app.py + jalur frozen-aware app_base_dir — config/settings/followup/crash.log hidup di samping .exe); (4) HARNESS UJI OTOMATIS run_tests.sh (auto-Xvfb, manfaat pytest-xvfb tanpa konversi pytest). High-DPI Windows dipastikan SUDAH in-house sejak v3.9.46-48 (rantai per-monitor-v2 + kompensasi geometri + tk scaling — setara tkinter-unblur)
# FIX 6a-07: header docstring (judul + sketsa ASCII toolbar di atas)
# memakai placeholder "vX.Y.Z" yang disubstitusi ke versi AKTUAL saat
# import — dulu literal "v3.9.22" basi 35 rilis (titlebar/statusbar
# badge sudah benar; APP_VERSION tetap satu-sumber kebenaran versi —
# TIDAK ada bump versi di fix ini).
if __doc__:
    __doc__ = __doc__.replace("vX.Y.Z", f"v{APP_VERSION}")
# v3.9.59 — REVIEW UI/UX SEBAR-AGENT (user: "Review ui UX full sebar
# agent dan fix"): 6 agent audit UI/UX PARALEL read-only (2-a shell/
# theme · 2-b widgets · 2-c pivot/komparasi/laporan · 2-d deviasi+popup
# · 2-e selisih/nominal/PO/followup · 2-f support+cross-cutting) → 67
# temuan TERVERIFIKASI (1 HIGH / 25 MED / 41 LOW) + 60+ hipotesis
# ditolak dgn bukti → 6 agent fix PARALEL kepemilikan-file terpisah +
# verifikasi utama. SEMUA fix: (2a) STATUSBAR pesan panjang kini
# dipotong '…' (badge versi/zoom tak tertimpa; teks penuh tersimpan;
# recompute saat resize) · TINGGI bar toolbar/statusbar IKUT ZOOM ×ui_scale
# (48→96 / 34→68 @200%; dulu judul & badge zoom terpotong) · rujukan
# tab hantu '⚙ Pengaturan' → '⚙️ Config' (15 situs) · baris tab
# notebook COMPACT-LABEL saat meluap di zoom tinggi/jendela sempit
# (tab kanan tetap terjangkau) · hint zoom CTRL+roda tampil sejak
# start (bukan hanya setelah zoom) · copy EN/ID disatukan ('💾 Export
# Excel' · '↻ Refresh Sumber' · 'baris Append1' · 'tampilan') · dialog
# simpan-config menyebut data lama tampil sampai pipeline ulang ·
# focus_set notebook pasca pipeline-done (12 jalur) · export: nama file
# ber-timestamp semua jalur + error file-terkunci ramah ID + tawaran
# 'Buka folder' · waktu proses terakhir 'Data: dd-mm HH:MM' di status.
# (2b) HeaderFilter: nilai panjang lebar popup DINAMIS (cap 460px,
# truncation '…') · PREVIEW live-search mengikuti OPERATOR (dulu
# menampilkan nilai yang TIDAK dipilih Enter; kontrak §94 tetap) ·
# hint 'Enter = pilih nilai' · NAVIGASI KEYBOARD daftar nilai (Up/
# Down/Space + ring fokus; Down dari entry masuk daftar) · panel ◱
# tombol seragam Ghost · FLASH_MS tunggal 2500ms (dulu 3,0 vs 2,5s) ·
# clone ⛶ berjudul '(salinan)' · KpiRow kartu SERAGAM (uniform grid +
# tepi simetris) · GhostButton cursor hand2. (2c) pivot: rentang
# tanggal terbalik → swap + ENTRY DISINKRONKAN + warning (dulu senyap)
# · Top-N non-numerik → revert + ⚠ (paritas dgn negatif) · guidance
# 0-baris via SUBTITLE EmptyState (dulu tersembunyi di balik overlay)
# · 'Apply' → 'Terapkan' · baris MODE kembar di 📋 → 'TAMPILAN' (view-
# spesifik) · laporan 0-anomali → EmptyState jujur 'tidak ada anomali
# utk filter aktif' · footer hint 'Dobel-klik = detail · ✓ = pantau' ·
# export pivot fmt_int_id ('1.347'). (2d) STICKY MERGE: baris display
# nilai kini BBOX-TERVERIFIKASI (dulu bisa mendarat di baris terpotong
# tak terlihat pada offset fraksional — gejala 'nama barang tidak
# muncul' kambuh via drag scrollbar) · BAND grup #9aa7b9 (kontras
# 2,44:1 vs 1,096:1 — sekat kelompok benar-benar terlihat) ·
# DeviasiPopup DAPAT COPY (menu klik-kanan Nomor/PO + tombol 📋 +
# flash — paritas DetailsPopup) · Ctrl+C DetailsPopup: seleksi REGION
# sel prioritas (dulu menimpa binding region ala Excel) · flash label
# jujur (Nomor vs Nomor PO) · judul popup wraplength adaptif (bug HANG
# resize ronde-1 juga diperbaiki: filter event.widget child) · legenda
# swatch CEK #c2410c sinkron + entri '✓ = pantauan' · messagebox
# 'Invalid' → 'Input tidak valid' · footer deviasi wrap 2 baris (dulu
# klip dari kiri). (2e) nominal ⧉ nilai 'Rp …' IDENTIK sel (dulu
# '1.825' vs 'Rp 1.825' → filter clone 0 baris) · chips Rincian IN +
# KPI Rekap Selisih WRAP (dulu chip/kartu terakhir hilang @minsize) ·
# status jujur saat KATEGORI menghabiskan baris · FOLLOW UP angka
# format INDONESIA ('1.234,5' · '(1.234)' · '-' — dulu EN) · hint ✓
# destruktif di footer + cursor hand2 · leaderboard '+N resto
# lainnya' (dulu senyap terpotong 12) · Rincian PO BISA SORT (satu-
# satunya tabel tanpa sort) · EmptyState follow-up 'centang ✓ di tab
# Deviasi' (bukan 'jalankan pipeline') · popup nominal MODAL (grab) ·
# legenda marker nominal ('*'/'—') · export Rekap IN ATOMIK. (2f)
# config: pesan error rujuk '⚙️ Config' + JUJUR (hapus config.json
# TIDAK meregenerasi — dulu klaim palsu) · export pivot/selisih/
# follow-up ATOMIK (tmp+os.replace; dulu timpa parsial) · refresh:
# file berubah tampil MTIME + folder HILANG tampil baris 'Hilang' ·
# followup.json korup → PERINGATAN pengguna (dulu senyap: .bad +
# daftar lenyap) + API last_recovery/last_save_error utk view ·
# tanggal dialog refresh seragam. (P0) PANDAS 3 COMPAT: fresh install
# (requirements pandas>=2.0.0 resolve 3.x) CRASH pipeline
# 'assignment destination is read-only' (to_numpy CoW read-only) →
# copy=True (pandas 2 & 3) + PIN pandas<3 (semantik astype(str) NaN +
# parser tanggal berubah di pandas 3 — data diverifikasi di 2.x).
# VERIFIKASI: test_ui_redesign 1402/1402 PASS (1379 + §69 BARU 23
# check) + test_mock ALL PASS + ruff 195 < baseline 204 + py_compile
# + smoke 2 entry tanpa crash.log + probe ≈60 file (audit + fix +
# verifikasi per-agent). 20 file.
# v3.9.58 — DEEP AUDIT SEBAR-AGENT (user: "Deep audit dan fix sebar
# agent full"): 7 agent audit PARALEL read-only (6-a app/state/threading ·
# 6-b widgets ·  6-c pivot/laporan/komparasi · 6-d1 deviasi · 6-d2
# selisih/nominal ·  6-e popup/followup/export ·  6-f pipeline) → 38
# temuan (2 HIGH / 16 MED / 20 LOW) + puluhan probe verifikasi → 6 agent
# fix PARALEL kepemilikan-file terpisah + verifikasi utama. SEMUA fix:
# (6a) export: tombol Export macet-disabled pasca pipeline ERROR/STOP
# dgn data lama (sinkron semua jalur done) · Excel GAGAL menulis FILE
# PARSIAL/korup di tujuan (tmp + os.replace atomik; file lama utuh) ·
# dataset KOSONG "sukses" → IndexError openpyxl + file korup (guard
# df.empty dgn pesan ramah) · ZOOM CTRL+wheel 10× terlalu sensitif di
# roda resolusi tinggi (akumulator delta ala v3.9.57) · statusbar/KPI
# format Inggris "215,950"/"1 rows" → fmt_int_id "215.950"/"1 baris" ·
# worker pipeline hanya menangkap Exception → BaseException meninggalkan
# is_running + GC shield mati se-session (cleanup + re-raise) · header
# docstring basi v3.9.22 → placeholder dinamis.
# (6b) TableExpander.restore() MEMBALIK grup ber-anchor 'before' sama →
# layout tab Rekap Selisih IN ter-scramble pasca ⤢→⤡ (urutan asal
# direkam; restore urut) · Ctrl+C menyalin PANAH SORT ke header TSV +
# auto-fit mengukur panah · apply_cell_tag Tk9-native ADITIF & list
# kosong no-op vs dokumen 6 view "replace/clear" (kini semantic replace
# via tracking + tag cell remove — Tk9) · apply_tree_row_filters cache
# baris PARSIAL bila filter diklik saat copy clone ⛶ berjalan (cancel
# SEBELUM snapshot; sumber _full_items) · refresh saat ⤢ expanded →
# kartu tersembunyi muncul lagi (auto re-hide via <Map>) ·
# insert_tree_items 1 TclError mid-batch → baris dibuang + on_done tak
# pernah terpanggil (per-item try + on_done pasti) · enable_col_resize
# tanpa flag idempoten · Ctrl+C menyalin kolom TERSEMBUNYI.
# (6c/6d1) PIVOT COM rentang tanggal mulai >1: baris COM minus PALSU
# (base SO(t−1) dari matriks PENUH, bukan slice; probe '(5)' → '5') +
# ☑hide-empty bisa menghilangkan baris COM senyap · export 0-item
# karean FILTER kini pesan jujur (bukan "Jalankan pipeline dulu") ·
# deviasi fingerprint ✓ MEMUAT field cek VOLATIL → ambang ACR / file
# lalu ⚖ = centang hilang senyap + orphan (fp stabil cek-dinetralkan +
# legacy match + sweep) · load_data H-default berubah → render GANDA
# dgn filter kategori LAMA (transien tabel kosong; kini 1 render) ·
# H=1: SO_H-2 & SO_H-1 dobel baca kunci −1 + header "SO_0"/"SO_-1"
# fiktif (jujur '-' + label tanggal nyata) · listener FollowUpStore tak
# pernah di-unsubscribe (remove_listener dipasang; akar: binding Destroy
# kondisional) · _compute_pivot telan exception pivot_table senyap.
# (6d2) popup Rincian IN chips 'Barang Masuk'/'Selisih IN' SKALA 1000×
# salah (parse display "1.500" EN; kini RAW _keys) · leaderboard SKOR
# KOLAPSE jadi 1 resto saat baris diklik (skor dari frame pra-filter
# Resto; highlight is_active hidup lagi) · nominal_resto kolom dinamis
# reset displaycolumns TANPA colmgr.apply (hidden muncul lagi + panel
# desinkron) · double-click area kosong membuka popup resto SEBELUMNYA
# (identify_row) · PERF _lalu_map iterrows main-thread 103ms → vektor
# (identik nilai, ≥3×).
# (6e) CLONE ⛶ FOLLOW UP BASI: klik ✓ menghapus baris SALAH (persist
# followup.json!) — guard _view_gen + clone ditutup saat re-render
# (mirror 48-d); Laporan Deviasi kelas sama (_fp_map row_N posisional) ·
# POPUP MODAL kehilangan grab pasca funnel filter dibuka-tutup → main
# window interaktif di bawah popup "modal" (grab dipulihkan di SEMUA
# jalur tutup popup AutoFilter + Panel Kolom) · popup COM t>1 tanpa
# baris BASE SO(t−1) (formula tak bisa direkonstruksi; kini baris base
# + catatan jujur) · Tanggal mentah '-25' → konvensi '25•' + legenda ·
# kolom Cek Follow Up menampilkan segmen ANALISA seolah anomali CEK
# (prefiks 'Analisa: ') · PERF deviasi_popup 95-125ms sinkron main
# thread → mask factorize di-cache per df (A/B identik).
# (6f) fn_4217 melt: kolom ringkasan ber-kurung 'TOTAL (SEMUA GUDANG)'
# jadi resto PHANTOM → saldo 42.17 DOBEL (blacklist token ringkasan —
# gudang asli tetap lolos) · fn_audit kunci grup "Resto|Item" kolisi
# konkatenasi (tuple) · _combined_to_long kolom dobel-hari menimpa
# senyap (preferensi 'Sum of N' / SUM) · Config.folder()/sheet()
# KeyError mentah bila sub-key hilang (RuntimeError Indonesia ala
# v3.9.33). VERIFIKASI: test_ui_redesign 1379/1379 PASS (1308 + §68
# BARU 71 check — port probe terverifikasi: export/zoom/worker ·
# expander/copy/tag/insert · clone basi 6e-01/02 · grab 6e-03 · COM
# base 6c-02 · fingerprint stabil 6d1-01 · 1-render 6d1-02 · H=1 ·
# chips RAW · leaderboard · colmgr · identify_row · phantom-resto ·
# tuple-key · dobel-hari · config · PERF A/B) + test_mock ALL PASS +
# ruff 204 < baseline 205 (0 issue baru) + py_compile + smoke 2 entry.
# v3.9.57 — FIX AUDIT ("scroll daftar nilai filter belum menangani roda
# mouse beresolusi tinggi — cek ini"):
# (1) AKUMULATOR RODA HALUS untuk DAFTAR NILAI ber-canvas: fungsi BARU
#     enable_smooth_wheel_list (padanan enable_smooth_wheel utk Canvas)
#     dipasang di popup filter HeaderFilter (dulu cv.yview_scroll(
#     -1*(e.delta//120)) — roda/trackpad resolusi tinggi mengirim delta
#     < 120 per event → dibulatkan NOL SETIAP event = daftar TIDAK
#     PERNAH bergulir) & panel kolom ColumnManager (dulu trik
#     int(-e.delta/120) or -1 — justru memaksa 1 unit penuh per event
#     kecil = terlalu cepat): kontribusi -delta/120 diakumulasi,
#     int(acc) digulir, sisa dibawa; reset arah saat roda berbalik.
# (2) BINDING TINGKAT POPUP (Toplevel): Windows/Tk 8.6 mengirim wheel
#     ke widget FOKUS (popup memfokuskan ENTRY pencarian → binding
#     canvas lama tak pernah terpanggil dari entry!) — kini wheel di
#     anak APA PUN (entry/checkbox/scrollbar/label) menggulir daftar;
#     event yang jatuh ke canvas berhenti di 'break' (tanpa dobel).
# (3) X11 <Button-4/5> kini TER-BIND (dulu roda Linux hanya via drag
#     scrollbar); ARAH dibawa POLA BINDING (2 handler terpisah), bukan
#     event.num — event_generate sintetis tak bisa men-set %b/num
#     (Tk 9 memetakan <Button-4/5> → tombol fisik 8/9); refactor sama
#     diterapkan ke enable_smooth_wheel (tree — 2 closure terpisah).
# (4) CTRL+Scroll = ZOOM UI tetap murni: handler polos melewatkan
#     event bergaya Control (bit 0x4, tanpa 'break') ke bindtag 'all'
#     (bind_all fallback app); di canvas pola Control-* (bind_ctrl_zoom)
#     lebih spesifik & menang duluan.
# v3.9.56 — FIX BUG USER ("bug nama barang tidak muncul di tab deviasi
# gr dan pcs dan fix yang lain"):
# (1) STICKY MERGE-VERTIKAL: v3.9.55 merge native menulis nilai nama/rank
#     HANYA di baris head kelompok → saat scroll melewati head, viewport
#     penuh baris BLANK (kelompok bisa puluhan baris) = tampak "nama
#     barang tidak muncul". Kini baris DISPLAY per kelompok = head bila
#     terlihat, selain itu BARIS PERTAMA kelompok yang TERLIHAT (ala
#     merged-cell Excel — nilai selalu ada di area terlihat), dipindah
#     otomatis saat scroll (hook: wrap yscrollcommand + <Configure> +
#     _redraw_overlay_now; idempoten tulis-diff; pass murah 0,04 ms;
#     clone ⛶ punya state viewport sendiri; sort/render/filter =
#     normalisasi penuh kebal-state-awal).
# (2) FILTER CLONE ⛶ MERGE-AWARE (bug laten v3.9.51): apply_tree_row_
#     filters mencocokkan nilai DISPLAY tree → filter clone by Nama
#     Barang hanya meloloskan baris head/sticky (kelompok hilang
#     sebagian). Kini value_get(iid, kolom, cur) sumber RAW snapshot
#     (attach_clone_filters → _merge_value_get) → kelompok UTUH lolos.
# v3.9.55 — 8 PERMINTAAN USER ("kerjakan no bug no mistakes dan cek ulang
# jagan asumsi dan no lemet. Deep audit juga program kita biar cepat dan
# smooth"):
# (1) KATEGORI LABEL RINGKA: entry gabungan default kini "Deviasi (COM +
#     Packaging)" (dulu label virtual 49-char — dropdown kembali tampil
#     daftar kategori DBS; label lama tetap dikenali; semantik strict
#     v3.9.53 utuh); lebar combo 46 → 34 (deviasi/pivot/nominal).
# (2) NOMINAL KOSONG (user: "ada deviasi yang tidak ada nominal nya coba
#     cek"): (a) lookup harga 41.09 kini NORMALISASI kunci (strip + rapat
#     spasi + upper — kedua sisi build_harga_map/lookup_harga_pair):
#     selisih kapitalisasi/nama tak lagi membuat Nominal '-' senyap;
#     (b) DIAGNOSTIK transparan di status footer: n baris tanpa nominal
#     diklasifikasi (a tanpa harga 41.09 · b satuan tak terkonversi).
# (3) SKOR RESTO (Rekap Selisih IN; user: "Beri Skor per resto dengan
#     selisih terbanyak ... di tiap tanggal dan di keseluruhan tanggal"):
#     leaderboard kartu 🏆 — skor = item selisih + tanggal terdampak
#     (kronis > insidental, persis contoh user), top-3 medali + bar
#     proporsional; KLIK baris = filter tabel ke resto itu (toggle).
# (4) MERGE-VERTIKAL NATIVE Nama Barang + Rank (user: "Merger Vertical
#     Nama barang dan Rank ... sama kaya di tab rincian PO"): nilai sekali
#     di head run + band kelompok SERAGAM (grp_head & RankMergeOverlay
#     DIHAPUS — label overlay di atas tree = sumber glitch scroll);
#     adjacency dari _row_snaps; sort value_get (kelompok bergerak utuh);
#     double-click baca snapshot (baris lanjutan blank).
# (5) URUTAN KOLOM POPUP Deviasi GR/PCS: Tanggal, SO, Saldo Akhir,
#     Deviasi, COM, IN, Nomor, Nomor PO.
# (6) ANTI-GLITCH SCROLL (user: "Waktu scroll kok banyak glitch?"):
#     sync_tree_scroll_overlays — command scrollbar (vsb+hsb) DIWRAP
#     (drag thumb → redraw overlay sinkron — probe: yscrollcommand baru
#     jalan di IDLE) + bindtag OvScrollSync SETELAH kelas (keyboard) +
#     _redraw_overlay_now ikut refresh HeadingTint; dipasang otomatis di
#     SEMUA tree via enable_col_resize.
# (7) TOMBOL SORT ANALISA CEK (▲ Kenaikan / ▼ Penurunan Tertinggi):
#     sortir oleh segmen analisa lalu→kini di teks CEK (tuple tier+pct;
#     tanpa persen → ±∞; Berubah Arah tier tengah).
# (8) AUTO-FIT PERTAMA BUKA (user: "bisa gak sudah diset ke auto fit
#     biar gak adjust manual lagi?"): jendela MAXIMIZED saat pertama kali
#     + ukuran/maximize TERAKHIR diingat (settings.json, disimpan saat
#     ditutup); kolom auto-fit SEKALI per muat data di SEMUA view utama
#     (autofit_tree_once/reset — merge-aware via _autofit_value_get).
# v3.9.54 — FIX "ADA BUG di pop up pivot tabel yang kosong ketika aku double
# klik. Cari bug secara keseluruhan sebar agent dan fix" (user):
# (1) POPUP PIVOT KOSONG (P0, sejak v3.9.49): _on_double_click pivot
#     meneruskan seleksi KATEGORI combobox (default = entri GABUNGAN
#     VIRTUAL KATEGORI_DEFAULT_LABEL) ke show_details_popup yang memfilter
#     EXACT string — label virtual bukan nilai data → 0 baris → popup
#     KOSONG di setiap double-click dengan kategori default. FIX:
#     kategori_match_mask BARU (pipeline/helpers — mask kanonik 4 cabang
#     virtual: blank-label / gabungan / legacy 'Deviasi' passthrough /
#     exact; semantik PERSIS jalur tampilan view) dipakai kolom KATEGORI
#     popup (details_popup) — re-export widgets.
# (2) AUDIT SEBAR-AGENT (3 agent paralel: 8-a popup-consistency · 8-b
#     fitur v3.9.51-53 · 8-c baseline) → CONFIRMED & DIFIX:
#     - (8-a P0-1) popup baris 6.PEMAKAIAN (COM): JENIS COMPUTED (tak
#       pernah ada di data mentah — _compute_com) → popup kini menampilkan
#       baris PENYUSUN formula (SA/SO/IN/BK) + catatan 'formula COM'
#       (dulu exact-match = 0 baris → popup KOSONG di mode Tanggal);
#     - (8-a P1-2) popup pivot kini meneruskan RENTANG TANGGAL tampilan
#       (tgl_range — parity _compute_payload tnum.between; dulu baris di
#       luar rentang tetap muncul di popup);
#     - (8-a P1-3) popup Follow Up baris asal KOMPARASI: snap menyimpan
#       'resto' bentuk pendek + 'barang' nama FILE → exact-match data app
#       = 0 baris. FIX: field snapshot BARU barang_app/resto_app (diisi
#       komparasi via pair_index bila pair ada di data app; SNAPSHOT_
#       FIELDS +1 — fingerprint 9 field TAK berubah; snap lama → fallback
#       perilaku lama);
#     - (8-a P1-4) nominal_resto _event_col_name: posisi DISPLAY dipetakan
#       ke urutan LOGIS (kelas bug v3.6/v3.7 — sudah difix di semua view
#       lain) → setelah hide kolom, double-click sel 'Tanpa Harga' resolve
#       kolom SALAH. FIX: identify_to_column (displaycolumns-aware);
#     - (8-b P2) RankMergeOverlay.refresh: run LAMA menembus batas tree
#       re-render PARSIAL → IndexError di callback Tk. FIX: klip batas
#       atas children (cap 64 utk perf dipertahankan);
#     - (8-b P2) sort_tree_by_column default parser: 'Rp-aware'
#       SETENGAH (dulu buang ',' tapi TIDAK '.' ribuan → 'Rp 1.825' salah
#       skala 1000×, 'Rp 1.825.567' ValueError → kolom jatuh ke string).
#       FIX: mirror _parse_num_id ('.' ribuan dibuang, ',' desimal,
#       kurung negatif, '—'); non-numerik tetap raise → fallback string;
#     - (8-b doc) docstring rentang minggu komparasi disinkronkan kode
#       (H 15-31 → WEEK 3/4; file user hanya WEEK 1-4).
#     Test §64 BARU 31 check (mask kanonik · popup virtual 5 cabang · COM
#     formula · tgl_range · E2E handler pivot · Follow Up app-namespace +
#     fallback snap lama · guard overlay · parser Rp/ID · col-name
#     display-aware). Baseline 1238 → 1269 PASS.
# v3.9.53 — 3 PERMINTAAN USER (tab 📦 Deviasi GR / 🧩 PCS):
# (1) DEV. BULAN LALU = NILAI ASLI DARI FILE (user: "Deviasi bulan lalu
#     yang ditampilkan di tab deviasi gr danpcs pakai nilai asli yangan
#     pakai nilai absoulte yang ditampilkan. Absoulte untuk perhiutngan
#     saja"): kolom kini bersumber DEV Lalu FILE deviasi resmi (tab ⚖
#     Komparasi — parse_deviasi_file via lalu_provider app, pola
#     nominal_resto v3.9.36) — bertanda (minus kurung merah / plus
#     surplus), PERSIS angka kolom 'DEV Lalu' tab 📋 Laporan Deviasi
#     ('sama seperti di tab laporan deviasi secara kuantiti'); absolut
#     tetap HANYA utk hitungan ANALISA CEK lalu→kini (|kini| vs |lalu|).
#     Dulu v3.9.51-52 Σ 3.DEVIASI tgl negatif rekap lalu (hanya -25..-31,
#     nilai mentah tak sebanding → tampak 'nilai absolute'). Tanpa file →
#     '-' + petunjuk status; file auto-load SAAT STARTUP (maybe_auto_load
#     _last — parse worker, tidak menunggu tab 📋 dibuka); label
#     'WEEK n · bulan' dinyatakan di status + legend.
# (2) MINGGU PEMBANDING MENYESUAIKAN H (user: "Week sudah menyesuaikan
#     kolom H di tab deviasi GR dan PCS untuk Deviasi bulan lalu"):
#     _pilih_minggu_lalu v3.9.41 ('jika week 1 maka ambil data week 1') +
#     bulan TERBARU file (parity hitung_nominal_lalu_pairs tab 🧮).
#     Identitas file = BAGIAN KUNCI SharedPivotCache + on_lalu_file
#     _changed (clear + refresh) — pivot basi mustahil saat file
#     berganti; _on_dev_file_loaded app kini juga menyegarkan GR & PCS.
# (3) KATEGORI DEFAULT GABUNGAN STRICT (user: "kok ada nama barang yang
#     bukan kategori COM Deviasi + Packaging Deviasi misal BASKOM
#     STAINLESS 18 CM, BASKOM STAINLESS UK 26 CM dll coba cek apa ini
#     bug?"): passthrough barang TANPA kategori dihapus dari seleksi
#     default (kebijakan v3.9.45 (a) — barang tanpa kategori master
#     tadinya ikut tampil); kelas 100383 tetap terlindungi KATEGORI
#     REKAP v3.9.49 + entry '(Tanpa Kategori)' + jumlah tersembunyi
#     dinyatakan di status (tidak lenyap senyap). Berlaku konsisten:
#     Deviasi GR/PCS ×2 · Pivot ×2 · 🧮 Nominal Resto (helpers
#     kategori_passthrough).
# v3.9.52 — 2 PERMINTAAN USER (tab 📦 Deviasi GR / 🧩 PCS):
# (1) MERGE-VERTIKAL VISUAL kolom Rank (user: "kolom Rank kok tidak
#     termerger vertcial seperti kemauanku di atas? ... Merger vertcial
#     sama kaya di tab rincian PO"): v3.9.51 menampilkan nilai sekali di
#     baris kepala, TAPI batas warna grp_head-vs-band membuatnya tampak
#     sel TERPISAH (bukan satu sel tinggi) → RankMergeOverlay BARU
#     (widgets) menggambar SATU Label blok kontinu per kelompok ≥2
#     baris: latar warna band kelompok (sekat grp_head digantikan di
#     kolom Rank saja), nilai VERTIKAL CENTERED, seleksi ikut warna
#     seleksi; runs didorong _reapply_rank_merge (satu pintu dekorasi
#     render/sort/clone — urutan visual); reposisi otomatis scroll y/x
#     + resize kolom + zoom (_refit_all_tree_columns walk tree._rank_merge);
#     event area label diteruskan ke tree (pola CellColorOverlay +
#     double-click manual) supaya seleksi/klik-kanan/roda/double-click
#     rincian tetap bekerja; clone ⛶ overlay sendiri (+ dorong ulang
#     runs — insert_tree_items chunk pertama SINKRON: on_render_done
#     clone kecil bisa terjadi sebelum overlay terpasang).
# (2) SATUAN HIDDEN BY DEFAULT (user: "Secara default hide kolom Satuan
#     di tab Deviasi Gr dan PCS"): ColumnManager param BARU
#     default_hidden — DeviasiView pass ["Satuan"] (di tab GR seragam
#     'GR' — redundan; PCS mode sudah ditentukan tab); kolom tetap
#     bisa di-unhide (◱ Kolom / klik kanan); NILAI tetap hidup
#     (snapshot follow-up, popup rincian, filter mode) — displaycolumns
#     hanya soal tampilan; clone ⛶ menyalin displaycolumns sumber.
# v3.9.51 — 5 PERMINTAAN USER (tab 📦 Deviasi GR / 🧩 PCS + Laporan):
# (1) ANALISA di kolom CEK (user: "kolom Cek tambahkan analisa Penurunan
#     tertinggi, peningkatan tertinggi atau berubah arah seperti pada
#     tab laporan deviasi tab analisa. Cuman tidak hanya penurunan tinggi
#     atau peningkatan tinggi tapi berapa persen ... hitung ... di
#     absolute dulu"): per pasangan, |Deviasi(H)| vs |Σ Dev bulan lalu|
#     (3.DEVIASI Tanggal NEGATIF — rekap lalu 25..-31); tanda berlawanan
#     → 'Berubah Arah'; selisih absolut > toleransi → 'Peningkatan/
#     Penurunan Tertinggi ±p%' (basis |lalu|; |lalu|=0 → tanpa persen);
#     Stabil → tanpa label. Segmen ditambah ke teks CEK setelah ' · ';
#     tag warna & filter ⧩ & snapshot follow-up memakai LABEL UTAMA
#     (fingerprint ✓ lama tetap cocok).
# (2) KOLOM RANK MERGE-VERTIKAL per kelompok Nama Barang (pola tab 🛒
#     Rincian PO): rank kini PER BARANG (Σ|Deviasi| kelompok, frame
#     terfilter — renumber per tab/filter) ditampilkan sekali di baris
#     pertama kelompok; baris lanjutan kosong & dipasang ulang mengikuti
#     urutan visual pasca-sort/clone (_reapply_rank_merge).
# (3) KOLOM 'Stok Seharusnya' DIHAPUS dari tampilan GR/PCS → diganti
#     'Dev. Bulan Lalu' (kuantiti, Σ 3.DEVIASI tanggal negatif; NaN →
#     '-' tanpa rekap lalu, 0 → '0'); rumus W tetap internal utk CEK
#     'Hitung Manual'.
# (4) HEADER kolom In (In_H-1/In_H/In_H+1 — dinamis In_13/In_14/In_15
#     saat H=14) diberi STRIP WARNA TEAL (HeadingTintOverlay widgets —
#     ttk tak punya bg per-heading; event diteruskan supaya ⧩/resize/
#     roda tetap bekerja; ikut zoom via _refit_all_tree_columns).
# (5) SEMUA DATA NOMINAL → CURRENCY 'Rp' (fmt_rp_cell nominal_common):
#     kolom Nominal 📦/🧩, mode ⚖ Komparasi, mode 💰 Nominal (H) + baris
#     TOTAL/chip, tab 🧮 Nominal Deviasi + popup + footer; parser sort
#     & popup ⧩ membuang prefiks 'Rp'. KOLOM 'Selisih' mode ⚖ Komparasi
#     DIHAPUS dari tabel (user: "hapus juga kolom selish pada tab
#     laporan deviasi") — nilai internal tetap (Status/analisa/snapshot).
# v3.9.50 — DEEP AUDIT SEMUA FITUR BARU (user: "Deep audit semua
# fitur baru dan fix sebar agent" — 4 agent paralel: 3-a zoom/DPI,
# 3-b pipeline kategori, 3-c UI filter/banding, 3-d regresi+E2E;
# baterai penuh 1159/1159 + mock + ruff 190/15 + E2E real data
# semua HIJAU — temuan di bawah adalah sisa audit, bukan regresi):
# (1) [MAJOR 3-a] ZOOM TIDAK MENSKALAKAN LEBAR KOLOM TABEL: _apply_ui_
#     zoom menyentuh font/rowheight/jendela/overlay tapi BUKAN kolom —
#     auto_fit_columns clamp max_width=340 STATIS → Nama Barang di
#     zoom >±110% mulai TERPOTONG (butuh 634px di 200%, capped 340).
#     FIX: (a) auto_fit_columns menskalakan min_width/max_width/pad ×
#     theme.ui_scale() (pengukuran font(10) ter-zoom sudah benar —
#     hanya BOUNDS-nya yang statis); (b) _apply_ui_zoom memanggil
#     _refit_all_tree_columns() — auto-fit ULANG semua tree (root +
#     popup + clone ⛶, walk winfo_children recursive) setelah font
#     ter-rescale, sebelum invalidasi cache render → kolom mengikuti
#     zoom seperti janji 'zoom seluruh UI' (deterministik dari konten
#     via auto_fit — tanpa drift pembulatan rasio).
# (2) [MINOR 3-a] ROUND-TRIP JENDELA LEWAT CLAMP LAYAR: rasio dikali
#     dari ukuran TER-CLAMP (1100×800 → 200% clamp 1920×1080 → balik
#     100% = 1020×700 minsize, BUKAN 1100×800 — ukuran asli 'terbakar').
#     FIX: _zoom_base_wh (ukuran efektif 100%) + _zoom_expected_wh
#     (ukuran yang kita minta sendiri) + binding <Configure>
#     _on_root_configure: resize MANUAL user → base diperbarui
#     (current/zoom), perubahan dari zoom aplikasi sendiri (match
#     expected, termasuk hasil clamp) → base TIDAK berubah → round-
#     trip 100%→200%→100% EKSAK pulih meski lewat clamp layar.
# (3) [MINOR 3-a] MINSIZE×zoom DI-CLAMP LAYAR PENUH (1920×1080 di zoom
#     200% → user tak bisa mengecilkan jendela sama sekali): clamp
#     minsize kini fraksi 85% layar (bukan 100%).
# (4) [MINOR 3-a] 2 popup tree Nominal per Resto TANPA choke-point
#     (tanpa enable_col_resize → tanpa smooth wheel + binding CTRL
#     widget-level; klaim 'semua tree' meleset): _show_resto_popup +
#     _show_noharga_popup kini enable_col_resize(tree) — parity 14
#     call site lain (zoom tetap jalan via bind_all fallback, tapi
#     roda halus + prioritas binding widget kini utuh).
# (5) [MINOR 3-b] LANGKAH 5c filter blank TAK MEMBUANG '-'/'—' (cermin
#     token kategori_blank_mask): rekap kategori '-' kini TIDAK menimpa
#     master (dulu: item ber-master nyata 'kehilangan' kategorinya).
# (6) [MINOR 3-b] PRECEDENCE 5c: duplikat nama barang di rekap LALU vs
#     BERJALAN → drop_duplicates kini keep="last" (concat b-lalu lalu
#     a-berjalan → BERJALAN menang — bulan berjalan otoritatif; dulu
#     nilai BASI bulan lalu yang menang secara diam-diam).
# (7) [MINOR 3-b] LOG 5c kini juga melaporkan jumlah baris yang NILAINYA
#     BENAR-BENAR berubah dari master (rekonsiliasi audit — dulu hanya
#     'ber-rekap' yang tak membedakan sudah sama/berubah).
# (8) [MINOR 3-b] Asimetri case kategori_multi_values vs kategori_
#     passthrough (label gabungan exact-case vs lower): kini keduanya
#     case-insensitive (landmine pemanggil programatik hilang).
# (9) [MINOR 3-b] Pivot combobox KATEGORI width 16 → 46 (label gabungan
#     49-char default TERPOTONG di tab Pivot; 2 combobox lain sudah 46).
# (10) [MINOR 3-b] Deteksi KATEGORI jalur per-resto kini whitespace-
#     tolerant (strip — parity jalur combined; header 'KATEGORI ' di
#     sheet per-resto legacy tak lagi dibuang senyap).
# (11) [MINOR 3-c] KONTRAS fg cek_manual #ea580c di atas bg grp_head
#     #e2e8f0 = 2,89:1 (< 3:1 WCAG): digelapkan ke #c2410c (≈3,9:1) —
#     teks CEK 'Hitung Manual' di baris pertama kelompok tetap terbaca.
# (12) [MINOR 3-c] '(Kosong)' TERBUKTI BENAR (kategori_blank_mask
#     diterapkan ke kolom AKTIF/NON — helper detektor token blank
#     generik; penamaan saja yang misleading) — tidak diubah, hanya
#     didokumentasikan di sini supaya audit berikutnya tak curiga ulang.
# v3.9.49 — KATEGORI REKAP MENTAH + FILTER AKTIF/NON + SEKAT VISUAL
# KELOMPOK (4 permintaan 1 rilis):
# (1) KOLOM AKTIF/NON → FILTER (user: "kolom Aktif dan non aktif pindah
#     ke bagian filter dekat kategori aja"): kolom tabel dihapus dari
#     Deviasi GR/PCS; combobox AKTIF/NON kini DI KARTU FILTER samping
#     KATEGORI (Semua/AKTIF/NON AKTIF/(Kosong) — kecocokan case-
#     insensitive persis normalisasi CEK; '(Kosong)' = barang tanpa
#     status master, pola '(Tanpa Kategori)'). Nilai TETAP dihitung
#     internal: CEK 'Kosong/Non Aktif' + snapshot follow-up 'aktif'
#     utuh; default 'Semua' = tabel lama tanpa penyaringan.
# (2) KATEGORI DARI REKAP MENTAH + DEFAULT GABUNGAN (user: "sebenernya
#     sudah ada KATEGORI dari file Rekap Mentah folder Deviasi Weekly
#     jadi bisa ambil kategori dari situ jadi secara default di semua
#     tab kategori sudah pilih: COM DEVIASI - RESTO dan Biaya Packaging
#     - RESTO"): fn_rekap_mentah kini MEMBAWA kolom KATEGORI sheet rekap
#     (bila ada — schema lama tetap didukung) → query_full_rekap_
#     mentah_so → append1 LANGKAH 5c: kategori rekap MENIMPA master
#     '21. DBS Kategori' per barang (key ternormalisasi strip+upper;
#     barang tanpa rekap tetap pakai master). Entry combobox GABUNGAN
#     'COM DEVIASI - RESTO + Biaya Packaging - RESTO' (KATEGORI_DEFAULT_
#     LABEL — helpers) jadi DEFAULT di Deviasi GR/PCS · 🧮 Nominal per
#     Resto · Pivot (entry hanya muncul bila data ber-kategori rekap;
#     passthrough blank tetap — proteksi kelas 100383); Rekap Selisih IN:
#     filter header KATEGORI default = kedua nilai rekap yang hadir.
#     Ini juga menjawab "BUMBU PASTA KUAH MLGPAR kenapa masih tidak ada
#     ya?": item kini ber-kategori rekap → tampil di seleksi default
#     (bukan hanya via passthrough/'(Tanpa Kategori)').
# (3) SEKAT VISUAL ANTAR KELOMPOK BARANG di Deviasi GR/PCS (user:
#     "dibagian antara Cabe dan pentol itu ada semacam sekat visual yang
#     membatasi atau menandakan"): striping per-baris (evenrow/oddrow)
#     DIGANTI banding per KELOMPOK Nama Barang — grp0/grp1 = pita latar
#     bergantian per kelompok, grp_head = baris pertama kelompok
#     ber-anggota ≥2 (latar paling tegas = penanda 'kelompok baru');
#     tag dipasang ulang tiap sort/clone/filter mengikuti urutan visual
#     (_reapply_group_bands — invalidate cache overlay Tk 8). Kelompok
#     1-baris hanya pita (sort kolom lain tak bikin tabel seragam abu).
# (4) probe E2E data nyata: 150 barang (65.627 baris) ber-kategori
#     rekap; BUMBU PASTA KUAH (V.20) → 'COM DEVIASI - RESTO' tampil di
#     default; plain saldo-only tetap blank → passthrough default +
#     entry '(Tanpa Kategori)'.
# v3.9.48 — TAMPILAN HD TAJAM + ZOOM RUNTIME (2 keluhan user sekaligus):
# (1) "KOK TIDAK HD?" — akar = KEBIJAKAN opt-out v3.9.47: default
#     DpiAware=false membuat proses DPI-UNAWARE → Windows MENYALIN-
#     BESARKAN (bitmap-stretch) seluruh jendela di layar scaling
#     >100% → semua piksel direntangkan = KABUR (itu yang user lihat
#     sebagai "tidak HD"). FIX DEFAULT BARU: "DpiAware" kini default
#     TRUE (piksel 1:1 TAJAM) + KOMPENSASI GEOMETRI menjawab REGRESI
#     ukuran v3.9.46 yang dulu jadi alasan opt-out: ukuran jendela
#     dikali skala DPI (winfo_fpixels/96, khusus Windows) — 1280×760 di
#     layar 125% → 1600×950 piksel FISIK = ukuran FISIK jendela lama
#     yang di-stretch Windows, TAPI tajam; font tetap POINT (bukan
#     pixel) + tk scaling dari DPI monitor (v3.9.46) → ukuran relatif
#     font:geometry kembali IDENTIK dgn tampilan lama. Opt-out tetap
#     tersedia: "DpiAware": false = pipeline bitmap-stretch lama persis
#     (kabur tapi identik piksel-ke-piksel dgn pra-v3.9.46).
# (2) ZOOM RUNTIME CTRL+Scroll (50%–200%, langkah 10%):
#     - theme.py: font()/mono() kini NAMED FONT BERSAMA (tkfont.Font
#       di-cache per (size, weight)) — zoom cukup configure size SEKALI
#       per font dan SEMUA pemakai (ttk style, tk widget, tag Treeview,
#       konsol log, popup terbuka) re-render HIDUP. apply_theme kini
#       IDEMPOTEN + rowheight = 30×zoom (scale_px) — dipanggil ulang
#       oleh zoomer. auto_fit_columns mengukur dgn font ter-zoom.
#     - anti-BENTROK scroll: pola <Control-MouseWheel>/<Control-Button-4/5>
#       dipasang TINGKAT WIDGET di SEMUA widget scrollable (choke-point
#       enable_smooth_wheel/make_log_console/canvas filter) — pola Control
#       LEBIH SPESIFIK mengalahkan binding <MouseWheel> polos di bindtag
#       yang sama (aturan Tk: binding ter-spesifik menang) → CTRL+roda
#       TIDAK menggulir tabel/log, hanya zoom; roda polos tetap scroll.
#     - efek berlapis _apply_ui_zoom: named font (semua teks) + re-apply
#       theme (rowheight tabel) + ukuran jendela × rasio zoom (menghormati
#       resize manual user; clamp layar + 400×300) + minsize proporsional
#       + invalidasi cache render CellColorOverlay (label sel warna tak
#       tertinggal posisi lama) + badge "Zoom NNN%" di status bar kanan.
#     - dispatch lewat registry theme.set_zoom_wheel_handler (widgets→app
#       tanpa impor melingkar); fallback bind_all utk area non-scrollable
#       + bind_class Listbox (popdown Combobox).
#     - runtime saja (restart → 100%) — sengaja: zoom = preferensi sesi,
#     tidak menulis config.json diam-diam.
# v3.9.47 — FIX REGRESI UKURAN TAMPILAN (user: "kenapa sekarang
# tampilkan program nya lebih besar? kembalikan ke size tampilan
# lama cek dulu coba ini karna apa"):
# AKAR — satu-satunya perubahan v3.9.46 yang menyentuh UKURAN
# rendering adalah audit fix #2 (DPI-awareness Windows): v3.9.46
# memasang per-monitor-v2 awareness SEBELUM tk.Tk() (benar per dok
# Microsoft) → di layar Windows dgn scaling >100% (125%/150%)
# aplikasi berpindah dari pipeline LAMA (proses DPI-unaware →
# Windows bitmap-stretch jendela ke ukuran "normal" yang user lihat
# bertahun-tahun — panggilan awareness v3.9.45 kebetulan GAGAL senyap
# karena dipanggil SETELAH jendela pertama, E_ACCESSDENIED, return
# code tak diperiksa) ke pipeline BARU (pixel asli + tk scaling dari
# DPI monitor) → ukuran bersih NET berubah (di mesin user: LEBIH
# BESAR). KEBIJAKAN: ukuran tampilan yang user kenal MENANG atas
# ketajaman pixel — keduanya tak bisa dijamin identik lintas mesin.
# FIX: intervensi DPI kini OPT-IN via config.json key "DpiAware"
# (default FALSE): False = TIDAK memanggil API awareness sama sekali
# + TIDAK menyentuh tk scaling = pipeline PERSIS efektif pra-v3.9.46
# (Windows bitmap-scale, ukuran lama) · True = mode tajam per-monitor
# v3.9.46 (kode audit #2 yang benar tetap tersedia, hanya harus
# diminta). Key DIBACA mentah (json.load + .get) SEBELUM Tk — penuh
# defensif: config hilang/rusak/bukan dict → False (default aman;
# error config asli tetap dilaporkan app seperti biasa, tidak
# diduplikasi di sini).
# v3.9.46 — AUDIT EKSTERNAL 4 TEMUAN + KATEGORI KOSONG (user):
# (1) [P1] STATUS FINAL JUJUR — status hijau "SELESAI" dulu dipasang
#     SEBELUM view dimuat + mode refresh MENIMPA peringatan dengan hijau
#     polos → user bisa percaya semua view ter-update padahal parsial.
#     Kini: kegagalan view DIKUMPULKAN (failed_views) → status akhir
#     "SELESAI PARSIAL — N view gagal dimuat" (oranye) + view gagal
#     DITANDAI "⚠ Data tampilan BELUM DIPERBARUI…" di status_var-nya
#     sendiri; folder pre-flight hilang + file skip → "SELESAI DENGAN
#     PERINGATAN" (amber, prefight kini diingat sampai run usai);
#     bersih → hijau; mode refresh hanya menambah info "🔄 disegarkan"
#     TANPA menurunkan severitas.
# (2) [P2] DPI WINDOWS — komentar lama mengklaim per-monitor sambil
#     memanggil SetProcessDpiAwareness(1) (= SYSTEM-aware) SETELAH
#     tk.Tk() (terlambat — dok Microsoft: sebelum HWND pertama), tanpa
#     cek HRESULT. Kini: _set_windows_dpi_awareness() DIPANGGIL SEBELUM
#     tk.Tk(); rantai per-monitor-v2 (SetProcessDpiAwarenessContext -4,
#     argtypes c_void_p) → per-monitor (awareness 2) → system; return
#     code SETIAP API diperiksa (gagal senyap tak mungkin); tk scaling
#     dipisah ke _apply_windows_tk_scaling(root) pasca-Tk.
# (3) [P2] COPY LOG — flash "Log TERSALIN" + timer 2,5 dtk bisa
#     mengembalikan status pipeline BASI (pipeline selesai di tengah
#     flash → timer memulihkan "menjalankan…"; copy ke-2 menyimpan teks
#     flash sebagai prev). Kini: prev hanya di-snapshot dari kondisi
#     STABIL; saat timer menyala, status yang sudah DIGANTI pihak lain
#     MENANG — restore dilewati (_log_flash_restore).
# (4) [P3] REFRESH DIALOG — dialog dulu hanya transient: pipeline bisa
#     DIMULAI dari jendela utama selama dialog terbuka → _refresh_sources
#     membuang cache DULU → _start_pipeline menolak → cache terbuang
#     tanpa refresh, senyap. Kini: dialog MODAL (grab_set; grab_release
#     sebelum destroy supaya callback tak terblok) + re-check pipeline
#     TEPAT SEBELUM invalidasi cache (cache tak dibuang bila pipeline
#     hidup, pesan jelas) + guard _start_pipeline tetap lapis terakhir.
# (5) '(Tanpa Kategori)' SELALU ADA (user: "kategori tanpa kategori kok
#     kosong ya di tab deviasi gr dan pcs") — entry v3.9.45 dipasang
#     KONDISIONAL (hanya saat ada baris blank): master yang makin
#     lengkap membuat entry HILANG SENYAP dari dropdown; probe E2E
#     data nyata ×2 tab (GR 1.156 baris / PCS 751) membuktikan LOGIKA
#     filter benar — masalahnya OPDONYA hilang/kosong saat data tanpa
#     baris blank. Kini entry SELALU tampil (deviasi GR+PCS, 🧮, Pivot);
#     bila dipilih saat memang 0 baris kosong → status jujur
#     "0 baris tanpa kategori master — semua barang yang tampil di tab
#     ini sudah punya kategori '21. DBS Kategori'" (bukan tabel kosong
#     misterius).
# v3.9.45 — DUA PERBAIKAN (user: "filter kategori di tab deviasi gr
# dan deviasi pcs kok seperti ngebug ya? karna aku ganti tidak
# terjadi apa apa" + "TAB NOMINAL DEVIASI SUPPORT buat multiple file
# deviasi buat compare dengan beberapa bulan lalu kan?"):
# (1) FILTER KATEGORI STRICT — passthrough v3.9.44 terlalu luas:
#     baris TANPA kategori master ('-', probe data nyata 90% baris
#     pivot!) tampil di seleksi APA PUN → mengganti kategori = no-op
#     (Semua == DEVIASI == 1.347 baris). KEBIJAKAN BARU
#     (kategori_passthrough): passthrough HANYA seleksi default
#     'Deviasi' (perlindungan kelas 100383 tetap utuh — barang
#     ber-deviasi tanpa master tak lenyap senyap) · seleksi eksplisit
#     lain STRICT (filter bekerja normal) · entry combobox BARU
#     '(Tanpa Kategori)' (KATEGORI_BLANK_LABEL) utk akses eksplisit
#     kelas itu · status footer menyebut jumlah blank yang ikut
#     tampil. Dipasang di SEMUA 6 titik: Deviasi GR + PCS ·
#     🧮 pra-compute · Pivot ×2 (mirror combobox di 3 view).
# (2) TAB 🧮 MULTI-BULAN — hitung_nominal_lalu_multi: SATU frame per
#     bulan file deviasi (multi-file ⚖ Komparasi path ';' — v3.9.13)
#     urut terbaru-dulu, minggu TER-COCOK H per bulan; kolom dinamis
#     'Lalu <label bulan>' per bulan ≥2 (heading + TOTAL row + chip +
#     footer + popup rincian per barang per bulan; tree
#     _ensure_tree_columns reconfigure + HeaderFilterGroup.add_columns
#     → filter ⧩/sort aktif juga di kolom baru; bulan utama tetap
#     kolom 'Nominal Deviasi Bulan Lalu' lama — back-compat penuh:
#     hitung_nominal_lalu_pairs(bulan_sel=None) = perilaku lama).
# VERIFIKASI: probe E2E data nyata ×2 (kategori: TEPAT strict 0 vs
# 1.156 dulu; '(Tanpa Kategori)' 1.156 baris blank-only; 100383 tetap
# tampil default; multi-bulan: kolom 'Lalu JULI 2026' + heading label
# + popup 20.AGUSTUS nyata + mock JULI) + test 1076/1076 (§56 19 check
# baru) + mock ALL + ruff src 191 < 195 & test 14 == 14.
# v3.9.44 — FIX "BUMBU PASTA KUAH MLGPAR MASIH BELUM ADA DI TAB
# DEVIASI GR" (user; probe E2E data nyata rekap 01.1 + 42.17 mock):
# item 42.17-only 100383 lolos whitelist v3.9.41 & masuk pipeline
# sampai pivot, TAPI DUA filter menyembunyikannya SENYAP dari view:
# (a) KATEGORI NaN — item tidak terdaftar di master '21. DBS
#     Kategori' user (master hanya punya varian (V.20)) → filter
#     kategori default 'DEVIASI' membuang barisnya ('nan' ≠
#     'DEVIASI'); FIX: pipeline.helpers.kategori_blank_mask — baris
#     TANPA kategori master TIDAK disembunyikan oleh filter kategori
#     (master tak kenal ≠ disembunyikan; tampil di seleksi kategori
#     apa pun; nilai kategori tetap kosong — jujur) di SEMUA 6 titik
#     filter: deviasi_view ×2 (tab GR + PCS) · nominal_resto_view
#     (tab 🧮 pra-compute) · pivot_view ×2 + jejak [INFO] append1
#     (jumlah pasangan saldo-only tanpa kategori master);
# (b) fn_4217 HARDCODE Tanggal=1 utk pasangan saldo-only → baris
#     3.DEVIASI pasangan itu hanya ada di t=1 → hitung_nominal_pairs
#     filter Tanggal==h (h analisa 25/26) membuangnya dari tab 🧮
#     (padahal tab Deviasi GR menampilkannya); FIX: saldo-only
#     fallback — baris 3.DEVIASI t=1 pasangan saldo-only (ada
#     2.SALDO AKHIR@t1 · TANPA rekap 1.SO/5.BARANG MASUK non-nol ·
#     belum termuat di dev) ikut dihitung; pasangan ber-rekap tak
#     tersentuh (nilai tak berubah) & h=1 tanpa duplikasi.
# VERIFIKASI: probe E2E data nyata — plain 100383 TAMPIL di Deviasi
# GR default DEVIASI (Sistem 84.000) + popup 🧮 MLGPAR '(84.000)';
# test_ui_redesign 1057/1057 (§55: 13 check baru) + mock ALL + ruff
# 195 < 196.
# v3.9.43 — FIX LAUNCHER (user: "kenapa mulai.bat tidak bisa launch"):
# v3.9.42 mengganti MULAI.bat dgn wrapper PowerShell Start-Process
# -PassThru + tunggu 5 dtk + goto label — wrapper itu sendiri AKAR
# kegagalan launch di mesin user: (a) AV/SmartScreen/PowerShell
# Constrained-Language memblokir powershell satu-baris ber-Start-
# Process (pola launcher malware); (b) PS dingin >5 dtk salah dibaca
# gagal; (c) race ExitCode-null dibaca "sukses" = mati senyap; (d)
# file ber-line-ending LF-Unix + byte UTF-8 + goto/label → parser
# cmd.exe goyah. FIX: (1) MULAI.bat pola TERBUKTI v3.9.33 kembali
# (`start "" pythonw -m src.ui`) — tanpa powershell, tanpa goto, CRLF
# + ASCII murni; .gitattributes mengunci eol=crlf utk *.bat/*.cmd
# permanen; (2) entry BARU src.ui.__main__ = bootstrap stdlib-murni
# yang menangkap JUGA kegagalan import-level (pandas/tkinter hilang)
# yang main() tidak bisa lihat — dialog + crash.log + exit 1: pythonw
# tidak bisa mati senyap lagi, deteksi pindah KE DALAM Python (tidak
# tergantung powershell/AV/kebijakan mesin); (3) fallback python dgn
# petunjuk pemecah (PATH / SETUP.bat / Unblock ZIP / App Execution
# Aliases); `python -m src.ui.app` tetap didukung seperti biasa.
# v3.9.42 — DEEP AUDIT MENYELURUH (user: "Deep audit all sebar agent dan
# fix"): 4 agen audit paralel (engine / core views / framework / secondary
# + config + tests) menemukan & memperbaiki:
# (1) HOTFIX REGRESI v3.9.40: penerusan event dari sel warna MATI TOTAL
#     (klik-kanan menu copy, drag seleksi, wheel) — event_generate
#     menolak opsi -num/-delta (field Event selalu ada, berisi '??') →
#     TclError ditelan; kini kw selektif (state int, delta int khusus
#     <MouseWheel>) + roda X11 gulir langsung sinkron; modifier state
#     double-click kini sampai ke handler (_fire_tree_bindings %s).
# (2) OVERLAY STALE: guard `if cells:` di 11 view melanggar semantik
#     REPLACE apply_cell_tag → render baru tanpa sel minus
#     meninggalkan nilai/warna LAMA menimpa data baru (iid deterministik)
#     — guard dihapus (list kosong = clear); auto_fit_columns kini
#     memicu redraw overlay (label tak lagi salah posisi setelah
#     Auto-Fit programatik).
# (3) KONSISTENSI 🧮: kolom 'Nominal Deviasi Bulan Lalu' tabel kini
#     JOIN KIRI ke pasangan sekarang hasil filter kategori — SAMA dgn
#     popup rincian (dulu tabel = seluruh file per resto → angka tabel
#     ≠ angka popup utk resto sama); minggu WEEK 3+WEEK 4 (keduanya
#     _h=25) dipilih label TERBESAR deterministik (dulu keep="first"
#     baris file pertama); SATUAN 'GR' vs 'GR ' menyatu (dulu baris
#     kembar di popup); chip 💰 = format tabel (2 desimal, minus
#     kurung).
# (4) ENGINE: to_datetime_robust dayfirst+format='mixed' (tanggal teks
#     dd/mm/yyyy salah hari senyap utk hari ≤12; >12 jadi NaT); fn_9901
#     resto titik TERAKHIR ('B.1001.MLGPAR' → 'MLGPAR', dulu resto
#     phantom); fn_combine_folder log per-file + WARNING multi-file
#     (dobel hitung senyap); sheet_filter LALU diteruskan ke KEDUA
#     langkah scan rekap; fn_4217 guard tabrakan rename + fallback
#     kolom bersuara; Config validasi TIPE KategoriBarang4217 (string →
#     iterasi per-karakter = kelas bug 100383) + JSON rusak → pesan
#     ramah; MULAI.bat fallback pythonw gagal → python; main() crash
#     dialog + crash.log; backup config = file LAMA; refresh parsial
#     mempertahankan filter/seleksi/scroll; followup save-gagal
#     terlihat; _flash_after guard; bench_views diperbaiki.
# (5) POPUP SEMUA BESAR: 🧮 cap 2600×1440 (proporsional di monitor
#     besar), Tanpa Harga + hsb (kolom Keterangan tak terpotong) + Esc
#     + Destroy cleanup + minsize clamp layar kecil; DeviasiPopup cap
#     2200 + kolom diskala; DetailsPopup clamp layar + kolom diskala;
#     ⛶ restore ke ukuran manual TERAKHIR.
# v3.9.41 (user: "100383 BUMBU PASTA KUAH masih belum ada di program ini
# padahal pada gudang MLGPAR di file 42.17 ada saldo nya dan harusnya
# masuk. Cek deep." + "pop up tab nominal deviasi ada bug kurang besar
# dan lebar" + "Nominal deviasi pembanding dari bulan lalu sesuaikan
# week nya jika week 1 maka ambil data week 1 juga"):
# (1) WHITELIST 42.17 VERSI-TOLERAN: token versi ujung kategori
#     (V.1/V.2/V.3 BARU…) dibuang dari KEDUA sisi sebelum prefix-match
#     (_fam_kat/_kat_match) + DEFAULT + 2 varian FOOD legacy '- TIDAK
#     BOLEH' (temuan probe: kategori Accurate nyata; item lama bersaldo
#     terbuang senyap → "tidak muncul"; config user lama yang mem-pin
#     6 entri tetap tertolong oleh family match). Jejak saldo-only
#     append1 kini hanya menghitung SALDO AWAL ≠ 0.
# (2) POPUP 🧮 BESAR/LEBAR: jendela ±94%×88% layar (dulu maks
#     1000×560) + kolom diskala memenuhi lebar jendela + re-scale saat
#     resize (<Configure> idempoten) + tombol ⛶ Perbesar/↺ Muat Lebar;
#     popup Tanpa Harga ikut.
# (3) MINGGU PEMBANDING TER-COCOK: hitung_nominal_lalu_pairs(…, h)
#     memilih minggu file yang MEMUAT H analisa (H 1-7 → WEEK 1; 8-14
#     → WEEK 2; 15-31 → WEEK 3/4; fallback terbesar ≤ target lalu
#     terkecil > target; h=None = minggu terakhir — perilaku lama).
#     Minggu terpilih DISEBUT di heading kolom/footer popup & tabel.
# v3.9.40 (user: "scroll masih seperti glitch coba deep cek"):
# probe Xvfb menemukan akar yang luput dari fix v3.9.29:
# (1) callback yscrollcommand (wrap overlay) baru dipanggil Tk di
#     IDLE — bukan saat yview_scroll dieksekusi — dan place()/
#     place_forget() label juga DEFERRED ke idle geometri → sel warna
#     tertinggal ≥1 frame dari barisnya setiap notch (probe terukur:
#     lab_y=210 vs bbox_y=191) = 'glitch/tearing' yang dilaporkan.
#     FIX: _redraw_overlay_now dipanggil dari DALAM handler roda
#     (setelah yview_scroll — bbox valid saat itu juga) → label
#     pindah + update_idletasks memproses repaint tree & pergeseran
#     label dalam SATU burst sinkron (frame layar tidak pernah
#     menampilkan baris baru dengan label lama).
# (2) CellColorOverlay CACHE RENDER: style/rowheight/font, warna tag
#     baris per iid, anchor kolom — tidak dibaca ulang per sel per
#     notch; lompati configure/place yang tak berubah (164 configure
#     per notch = beban repaint terbesar); invalidasi saat set_cells/
#     Configure; label pool reuse aman (penanda xy di-reset).
# (3) enable_smooth_wheel: sisa akumulator arah lama DIBUANG saat
#     arah roda berbalik (dulu sisa 0.75 'memakan' notch arah baru).
# (4) Event overlay (label sel warna) kini meneruskan modifier
#     state/delta/num — Shift+klik sel warna men-extend seleksi
#     (dulu state hilang), wheel dari label membawa delta.
# v3.9.39 (user: "di tab deviasi GR kok tidak ada Bumbu Pasta Kuah?
# padahal di file 42.17 ada. Dulu pernah aku bilang look up nama barang
# harus dua arah tidak hanya nama barang yang ada di file atau sheet
# Rekap Mentah tapi juga di file 42.17"):
# (1) INVESTIGASI (jawab "cek dulu"): jalur dua arah v3.9.32 (mask
#     saldo-only + SATUAN fallback) TERVERIFIKASI masih bekerja —
#     probe dgn data mirror user (rekap 01.1 nyata: BUMBU PASTA KUAH
#     (V.20) MLGPAR SO W1-25) → pasangan TAMPIL di tab GR, bahkan
#     pasangan resto non-rekap (scope v3.9.18 memang longgar krn
#     baris '1.SO' nilai-0 unpivot). Sisa celah = PEMBACAAN 42.17:
#     whitelist kategori bisa membuang barang SENYAP (safety-net
#     hanya jalan bila SEMUA terbuang) + nama sheet export beda →
#     0 baris senyap;
# (2) WHITELIST PROTECT DUA ARAH: barang yang ber-pasangan di sumber
#     lain (Rekap SO/BM, IN, OUT, BK — _collect_protected_barangs,
#     reorder load append1: transaksi dulu → 4217) SELALU lolos
#     whitelist kategori 42.17 — saldo awal tidak boleh hilang
#     (kalau hilang: Sistem salah / barang lenyap dari Deviasi GR);
# (3) SHEET RESOLVE DEFENSIVE: nama '#42.17. Kuantitas Barang per Gu'
#     tidak ada di file → fallback sheet berprefiks '#42.17' + [INFO]
#     (export Accurate memotong nama 31 karakter — bukan 0 baris);
# (4) LOG TRANSPARAN: barang terbuang whitelist DISEBUT NAMANYA;
#     '4217 dua arah: N barang … dilindungi'; ringkas 'N barang ·
#     M resto'; jejak 'N pasangan saldo-only masuk Deviasi GR/PCS'
#     (nilai non-nol — baris '1.SO' nilai-0 unpivot tak dihitung).
# v3.9.38 (user: "Kuantiti Deviasi 0 takperlu cari harga. Cek juga
# keseluruhan terkait ini" + "Nominal Deviasi total per resto juga
# tambahan di tab nominal deviasi ini buat versus bulan lalu" + harga
# BUMBU PASTA KUAH (V.20) "kok berbeda per gr nya" — manual
# 107,6386854 via saldo akhir nilai/kuantitas):
# (1) VERIFIKASI HARGA: engine fn_4109 = SAMA persis dgn hitungan
#     manual user (Harga = Nilai Saldo Akhir ÷ Kuantitas Saldo Akhir —
#     107,6386854/GR; tampil '107,64' = pembulatan display saja).
#     Akar beda nominal: engine v3.9.36 RECOMPUTE Nominal Bulan Lalu
#     dgn harga 41.09 SEKARANG, sedangkan file laporan resmi memakai
#     harga snapshot saat laporan dibuat (BUMBU PASTA KUAH (V.20)
#     MLGPAR W4 ≈ 113,048/GR → resmi 48.980.811,43 vs recompute
#     46.637.074,58). FIX: Nominal Bulan Lalu kini = KOLOM NOMINAL
#     DEVIASI MILIK FILE (parse_deviasi_file → 'Nominal Deviasi Lalu'
#     exact-match); kosong/format lama → fallback recompute (lama);
# (2) QTY DEVIASI 0 TANPA CARI HARGA — menyeluruh (hitung_nominal_
#     pairs, hitung_nominal_lalu_pairs, kolom Nominal GR/PCS, mode ⚖
#     Komparasi): lookup DILEWATI, Nominal 0.0 BUKAN None → tak
#     dihitung 'tanpa harga' (kolom/popup/footer; dulu menyesatkan);
# (3) KOLOM 'Nominal Deviasi Bulan Lalu' PER RESTO tab 🧮 + baris
#     TOTAL + footer 'TOTAL LALU' + chip (versus bulan lalu; resto
#     tanpa baris di file → '-'; minus merah per-cell).
# v3.9.37 (user: "ada tombol refresh untuk file sumber, bisa gak? dan gak
# harus refresh semua tapi" + "Keterangan PO merger Vertical dengan
# Pemasok sama seperti Status Pesanan Juga dan kolom Keterangan PO hapus
# karna sudah termerger. Tanggal Jam pembuatan Merger vertical dengan
# Nomor #"):
# (1) DIALOG 🔄 REFRESH FILE SUMBER (toolbar + tab Proses): daftar semua
#     file Excel sumber dgn checkbox; default tercentang = file berubah
#     sejak proses terakhir; Refresh Terpilih = hanya file itu dibaca
#     ulang (file lain dari CACHE bacaan — fn_buka_sheet kini cache
#     per file+sheet divalidasi mtime+ukuran); Refresh Semua = buang
#     seluruh cache; run pipeline tetap satu jalur (stop/log/KPI sama);
#     refresh mode TIDAK melompat tab (tetap di tab aktif, data
#     diperbarui in-place);
# (2) RINCIAN PO: kolom Keterangan PO DIHAPUS — nilai jadi anotasi "↳"
#     di kolom Pemasok (pola Status Pesanan v3.9.35, urut status lalu
#     keterangan); kolom Tgl/Jam Pembuatan DIHAPUS — nilai jadi anotasi
#     "↳ 02 Juni 2024 09:00" di kolom Nomor # (#0) baris anak pertama;
#     skema 8 → 6 kolom nilai; tag redup po_status_note utk semua sel
#     anotasi (#0 + Pemasok).
# v3.9.34 (user: kolom Nominal di Deviasi GR/PCS + Komparasi + tab Σ per
# resto):
# (1) kolom Nominal (Harga 41.09 × Qty Deviasi) di tab 📦 Deviasi GR &
#     🧩 Deviasi PCS — kolom Out_H/BK_H dihapus dari tampilan;
# (2) kolom Nominal di mode ⚖ Komparasi File Deviasi (harga × GR Saat
#     Ini);
# (3) TAB BARU 🧮 Nominal Deviasi — Σ (harga × qty deviasi) PER RESTO +
#     baris TOTAL + double-click resto → popup rincian per barang
#     (user: "ada tab nominal Deviasi, isinya total sum dari nama barang
#     kayak di laporan sampel kolom nominal deviasi, yang dapat dari
#     harga × kuantitas deviasi, cuman ini disum per resto");
# (4) helper bersama src/ui/nominal_common.py — SATU sumber kebenaran
#     perhitungan nominal (mode 💰 Nominal (H) + kolom GR/PCS +
#     Komparasi + tab 🧮);
# (5) app meneruskan harga_map/konversi_map (audit_result pipeline) ke
#     deviasi GR/PCS + komparasi + nominal + tab 🧮 Nominal Deviasi.
# v3.9.33 — AUDIT FIX WAVE (Task 48: deep audit 6 agent → 8 HIGH / 31 MED / ~54 LOW):
# (1) clone ⛶ basi ditutup saat re-render + gen-guard (toggle ✓ baris salah);
# (2) fn_9901 dedup baris duplikat lintas sheet/file + log per-sheet;
# (3) filter ⧩ Harga Nominal diperbaiki (mapping 'Harga Tampil');
# (4) font tema lazy-resolve (fallback tidak lagi terkunci sejak import);
# (5) _on_pipeline_done isolasi error per-view + pre-flight folder data;
# (6) H=1 kini resolve SO bulan lalu (key 0 → -1) + saldo-only H<=3;
# (7) Qty PO Menunggu campur satuan → jumlah terkonversi saja;
# (8) konversi_satuan first-match + in_selisih cache race + Nominal pending/busy/TOTAL pin;
# (9) Ctrl+C salin baris multi-select (semua tabel) + Salin Log + ☑ sync lintas tab;
# (10) kolom guard fn_3224/2205/4215 + key Sheets config dihubungkan + ffill kategori per-file;
# (11) README Cara Pakai rewrite + SETUP.bat cek errorlevel + MULAI.bat pythonw.
# v3.9.32 (user: 6 permintaan — "YA KERJAKAN SEMUA DAN PUSH TO GIT HUB"):
# (1) MULTI-SELECT SEMUA TABEL (user: "kenapa aku tidak bisa select ya
#     untuk semua data?"): semua tree selectmode browse → EXTENDED +
#     binding Ctrl+A pilih semua baris (rekursif utk tabel hierarki
#     pivot; Ctrl+Klik tambah/lepas, Shift+Klik rentang) — dulu semua
#     tabel hanya bisa seleksi BARIS TUNGGAL. Interaksi lama (double-click
#     detail, klik ✓, klik-kanan) tak berubah; clone Layar Penuh & popup
#     ikut (widgets.enable_multi_select).
# (2) POPUP DETAIL TAB PIVOT DIPERBESAR (user: "popup di tab pivot ada
#     deviasinya — terlalu kecil, besarkan lagi dan HAPUS tombol
#     perbesar popup pivot"): DetailsPopup kini ±90% layar adaptif
#     (sebelumnya 1100×540; clamp posisi ke layar; minsize tetap 800×320)
#     + tombol ⛶ Perbesar & item menu-nya DIHAPUS KHUSUS jalur pivot
#     (param show_maximize=False; jalur laporan/komparasi/follow-up tetap
#     punya tombol — popup mereka ikut membesar).
# (3) BARANG 42.17-ONLY TAMPIL DI DEVIASI GR/PCS (user: "BUMBU PASTA KUAH
#     hanya ada di 42.17, tidak muncul — apakah lookup cuma dari Deviasi
#     Weekly, tidak dua arah dari 42.17?"): akar = fn_4217 HARDCODE
#     Tanggal=1 → pasangan saldo-only (tanpa rekap SO/IN/out) tak pernah
#     masuk window analisa H±2 (H>3) + pivot_table membuang SATUAN NaN.
#     FIX: (a) baris ('2.SALDO AKHIR', t=1) pasangan TANPA baris window
#     selalu ikut mask + Sistem pasangan itu = saldo 42.17 (Deviasi =
#     0 − saldo — selisih nyata); (b) SATUAN pasangan tanpa rekap diisi
#     dari kolom 'Nama Satuan' file 42.17 (fallback; rekap tetap menang).
#     Pasangan ber-window TIDAK tersentuh (nilai tabel tak berubah).
# (4) FILTER KATEGORI 42.17 LEBIH AWAL (user: "filter data 42.17 pakai
#     kolom kategori barang [whitelist 5 kategori]"): fn_4217 membaca
#     kolom Kategori Barang sebagai kolom id SEBELUM melt (dulu kolom
#     kategori/satuan ter-melt jadi pseudo-baris resto → terbuang senyap)
#     + ffill header grup + whitelist config "KategoriBarang4217"
#     (default: 00.COST, 01.COST-PACKAGING V.2, 01. COST-PACKAGING-TIDAK
#     BOLEH, 10.FOOD [BUMBU|RM|WIP]-COM V.2 — 5 kategori produksi +
#     varian lama; prefix-match case/whitespace-insensitive; file tanpa
#     kolom → tanpa filter; hasil 0 baris → auto-bypass + peringatan).
#     Log '4217 kategori filter: N/M baris lolos'.
# (5) HARGA 41.09 (user: "harga dari file 4109 (41.09) folder 09.Harga
#     [alamat bisa diubah] — kolom harga = Nilai/Kuantitas Saldo Akhir"):
#     modul BARU fn_4109 (header 2 baris dideteksi per NAMA — bukan
#     posisi tetap; subtotal 'Total Nama Barang'/'Total Kategori Barang'
#     dibuang; kategori ffilled; Qty=0 → harga NaN guard; file contoh
#     user 4109.xlsx: AIR MINERAL 1.246,35/BOTOL, GULA 18,25/GR) →
#     audit_result['harga_map'] {barang: (harga, satuan)} GLOBAL +
#     audit_result['konversi_map'] (peta rasio v3.9.31).
# (6) MODE BARU '💰 Nominal (H)' tab 📋 Laporan Deviasi (user: "tab baru
#     Nominal = Harga × kuantitas deviasi, per barang + total"): baris
#     per pasangan (Nama Barang · Resto · Satuan · Harga · Qty Deviasi ·
#     Nominal; qty deviasi = 3.DEVIASI tanggal H — nilai kolom Deviasi
#     tab GR) + baris TOTAL (jumlah qty + nominal; style khusus) + chip
#     total di kartu Filter. HARGA DINORMALISASI ke satuan rekap via peta
#     rasio (harga41 × rasio(rekap)/rasio(41.09) — analisis data real:
#     176/187 match, 5 beda seperti MUTIARA BOBA KG-vs-GR; tanpa
#     harga/rasio → tampil berpenanda '*' & nominal '-', tak dihitung ke
#     total). H bersama (chip read-only + auto-refresh); urutan default
#     |Nominal| menurun; minus merah per-cell; sort parser Indonesia;
#     filter ⧩ + ⛶ + ⤢ + ◱ + ↔.
# v3.9.31 (user: "Kolom Kuantitas di Rincian PO atau file 3243 itu masih
# satuan besar bukan satuan kecil seperti di sheet barang masuk ... air
# mineral di rincian po pakai satuan karton dan sheet barang masuk botol
# ini jadi tidak match waktu cari deviasi murni karna PO belum update
# penerimaan sistem. Solusi: ambil konversi per satuan pada 2 file yaitu
# 32.24 di kolom Rasio Satuan dan Satuan ... dan file 4205 juga pakai
# kolom Rasio Satuan dan #Sat. Kirim" + konfirmasi "tampilkan nilai
# terkonversi" & fallback qty as-is berpenanda): PETA KONVERSI SATUAN
# {(barang, satuan): rasio} + {barang: satuan terkecil} dibangun DI
# MEMORI dari baris IN transaksi aktual (TANPA file master excel
# tambahan — selalu segar): fn_4205 + fn_3224 kini ikut membaca kolom
# 'Rasio Satuan' + '#Sat. Kirim'/'Satuan' + '#Sat. Terkecil' (resolusi
# defensive beda versi export) → dibakukan SATUAN DOK / RASIO SATUAN /
# SATUAN TERKECIL (kolom ekstra tak ikut pivot append1 — pola SOURCE IN
# v3.9.29) → append1 konversi_out (build_konversi_map; konflik rasio
# dihitung utk log) → KEDUA varian audit: qty PO Menunggu = Kuantitas ×
# rasio[(barang, Satuan PO)] → SATUAN TERKECIL — apple-to-apple dgn
# Selisih/Saldo (sisa -120 BOTOL vs PO 5 KARTON = match 120 BOTOL kini
# KELIHATAN; verifikasi data real 42.05: identitas Kuantiti Terima =
# #Qty Kirim × Rasio 4.591/4.591, 0 konflik rasio, rasio konsisten
# lintas resto → join key Nama Barang saja). Lookup gagal → qty PO
# as-is + penanda '*' di catatan (disetujui user); catatan berlabel
# satuan '(qty 120 BOTOL)'; aturan implisit (barang, satuan-PO ==
# satuan terkecil) → rasio 1 (70/152 barang real tanpa baris
# satuan==terkecil di 42.05); desc audit + hitungan 'tdk terkonversi'.
# Tab 🛒 Rincian PO TETAP tampilkan Kuantitas satuan PO asli (satuan
# dokumennya). Kompatibel: pemanggil tanpa peta → perilaku v3.9.30.
# v3.9.30 (user: "ya kerjakan semua dulu dan push to git hub" — konfirmasi
# atas analisis PO 'Menunggu diproses' 32.43: "PO sudah ada tapi penerimaan
# belum di-update di sistem → bisa jadi penyebab deviasi murni"): Rincian
# PO 32.43 kini dibaca SEKALIGUS TANPA filter KATEGORI (build_rincian_po
# semua_out — barang non-DEVIASI-master pun PO-nya ikut terbaca; query
# utama tab 🛒 tetap terfilter DEVIASI persis mirror M) → pasangan (resto
# dari Cabang PO '1370.MLGPAR'→'MLGPAR', barang) ber-Status Pesanan
# 'Menunggu diproses' (extract_po_pending, case-insensitive) diteruskan ke
# KEDUA varian audit (fn_audit._apply_po_menunggu — dipasang SETELAH engine
# VBA, pemanggil lama tanpa PO tak tersentuh): (1) kolom audit 'Qty PO
# Menunggu' (total qty PO menunggu pasangan — konstanta per pasangan);
# (2) catatan 'PO Menunggu: PO.xxx (qty 50) (+m)' di-append ke Detail &
# Catatan Audit HANYA baris DEVIASI MURNI pasangan itu (maks 2 nomor +
# hitungan sisa) — deviasi murni EXPLAINABLE (akan resolve saat PO
# diproses jadi RI) vs perlu audit fisik; (3) KPI 'dev_murni_po'. UI tab
# Rekap Selisih IN: KOLOM BARU 'PO Menunggu' (setelah Saldo; filterable/
# sortable) + KPI chip 'DEV MURNI · PO MENUNGGU' (amber) + opsi kolom
# export 'PO Menunggu' (numerik). PO menunggu = keadaan TERKINI (bukan
# transaksi bertanggal) → tidak difilter varian bulan.
# v3.9.29 (user: "nama barang + resto yang berasal dari 42.05 harusnya
# kategori internal. dari 32.24 eksternal dan 9901 juga eksternal ... aku
# mau ganti" + konfirmasi: campuran→'Campuran'; tanpa IN→kosong; MENGGANTI
# nilai source kiriman + "perbaiki animasi scroll seperti tidak smooth dan
# patah patah" + "hapus kolom kategori di tab deviasi gr dan pcs karna
# sudah ada filter di atasnya"): (1) SOURCE KIRIMAN kini DITURUNKAN per
# pasangan (Nama Barang × NAMA RESTO) dari SUMBER IN AKTUAL — query_in
# men-tag SEMUA baris IN dgn 'SOURCE IN' (dulu hanya detail); append1
# LANGKAH 5b _source_kiriman_per_pair: hanya 42.05/42.05-Lalu → 'Internal',
# hanya 32.24(-Lalu)/99.01 → 'Eksternal', campuran → 'Campuran', pasangan
# tanpa dokumen IN → kosong (None — mirror kolom Z 'Kiriman' sheet terhide
# 'Data Base Cek Deviasi' workbook referensi; verifikasi data referensi:
# IT.=Internal 3.682 baris / RI.=Eksternal 3.377 baris 100% konsisten, 985
# pasangan: 687 Internal / 273 Eksternal / 25 campuran). Merge di frame
# LEBAR → nilai konstan per pasangan terbawa ke format long; kolom master
# DBS Kategori 'SOURCE KIRIMAN' TIDAK diambil lagi (master tetap suplai
# KATEGORI + AKTIF/NON) → filter combobox pivot/popup/export kini
# Internal/Eksternal/Campuran. (2) SCROLL HALUS: enable_smooth_wheel BARU
# (dipasang enable_col_resize = semua tabel + clone ⛶ + popup) — 1 baris
# per notch (default Tk 3 baris = lompatan patah-patah) + akumulator delta
# pecahan utk trackpad/roda resolusi tinggi + 'break' mematikan binding
# kelas (tanpa dobel); CellColorOverlay (Tk 8.6) LABEL POOL (reuse label,
# bukan destroy/create = pop-in telat 1 frame) + reposisi SINKRON di
# _wrap_scroll saat frac berubah (label tidak 'melayang' di baris salah).
# v3.9.28 (user: "push to git hub dan perbaiki stock seharusnya dan hitung
# manual"): AKAR BUG BARU DITEMUKAN & DIFIKS — file .xlsb dibaca engine
# pyxlsb menghasilkan sel TANGGAL sebagai SERIAL MENTAH (46290 = 2026-09-25);
# pd.to_datetime lama membacanya sbg NANODETIK-EPOCH → SEMUA transaksi jatuh
# ke Tanggal=1 → In_H = 0 utk H>1 → "Stok Seharusnya" (W = SO(H-1)+IN_H−
# KIRIMAN_H−PENJUALAN_H) kelebihan potong IN & rasio |H−W|/|W| meledak →
# flag "Hitung Manual" PALSU (reproduksi: sheet '4  42 05' workbook user —
# 4.591 baris serial → 100% hari 1 pra-fix). FIX: helpers.to_datetime_robust
# (BARU) — nilai numeric dlm rentang serial Excel wajar (20000..80000) di-
# konversi via epoch 1899-12-30 (pecahan waktu ikut); date_to_day dibangun
# di atasnya (dipakai 42.05/32.24/22.05/42.15/9901); '#Tgl/Jam Pembuatan IT'
# (fn_4205 + queries 3224/3224-lalu) & kolom tanggal Rincian PO ikut robust.
# VERIFIKASI: pipeline mock 464.205 baris IDENTIK pra-fix (0 baris beda —
# file .xlsx dgn tanggal datetime tak tersentuh); .xlsb user via fn_buka_sheet
# → hari 1..26 tersebar benar (dulu 100% hari 1); fn_4205 dgn mock SERIAL →
# hari 25/30/27 + Tgl/Jam 24 Sep 18:00 benar; parity sheet DEVIASI GR H=25
# (mock + 32.24 eksternal): Hitung Manual program 3 = sheet 3 (overlap 3/3),
# Stok Seharusnya 794→12/1.405 (11 = dokumen ADA di raw 42.05 tapi TIDAK di
# pivot 'Barang Masuk' sheet — inkonsistensi internal workbook; 1 = rekap SO
# vs pivot 'SO BULAN INI' beda) — rumus program = rumus sheet (rekomputasi
# rantai LET dari nilai sheet sendiri: 0 mismatch).
# v3.9.27 (user: "pada rekap selisih in bisa mode hitung bulan lalu dan
# hanya hitung bulan ini. Tapi default hitung bulan ini aja" + "kondisi
# beda tanggal kok menghasilkan data kosong semua? cek file 01.1 CEK
# STOCK V2.xlsb bagian sheet Data Base Cek Deviasi KOLOM Y ... cek semua
# logika nya dan bandingkan dengan yang ada di program"):
# (1) MODE HITUNG tab 📤 Rekap Selisih IN — SegmentBar "MODE HITUNG":
#     "📅 Bulan Ini" (DEFAULT; audit varian bulan berjalan saja — baris
#     Tanggal negatif dibuang sebelum engine, mirror sheet
#     LAPORAN_DEVIASI tgl 1..31; rentang 1..31) | "📆 Lalu + Ini"
#     (audit varian penuh incl. bulan lalu; rentang -31..31). Kedua
#     varian dihitung pipeline SEKALI (audit_result + kunci
#     df_bulan_ini/kpi_bulan_ini/desc_bulan_ini); KPI chips + Saldo +
#     Hasil Audit ikut varian; ketik tanggal negatif → auto pindah
#     Lalu+Ini; Reset & data baru → default Bulan Ini.
# (2) CEK tab Deviasi GR/PCS DI-PORT ULANG PERSIS formula LET sheet
#     terhide 'Data Base Cek Deviasi' kolom Y (LET KondisiKosong/
#     Naikturun/HitungManual/TurunDrastis/KondisiACR; simulasi 2.120
#     baris = label sheet 128/129 eksak): kondisi 2 "Beda Tanggal"
#     J = KIRIMAN KELUAR (8.BARANG KELUAR; dari 9.ACR — bug port
#     pertama; bukti MLGPAR/ADONAN GORENG MEKAR sheet='Beda Tanggal',
#     app lama=''), aturan SO-stale v3.9.22 DIHAPUS (men-flag pasangan
#     ber-SO_H=0 — 'data kosong' — hingga mendominasi), kondisi 3
#     "Hitung Manual" stok = W sheet = SO(H-1)+IN−KIRIMAN−PENJUALAN
#     (dulu sistem+IN−ACR−BK → 266 flag palsu), Stok Seharusnya = W
#     sheet (dulu SO(H-1)−ACR; 794/1.405 baris beda). Gate sheet
#     IF(V="","",…) (Total ACR=0 → CEK kosong 47% baris + kaskade
#     #N/A tanggal di luar cakupan pivot → 'data kosong semua') TIDAK
#     direplikasi — app mengevaluasi kondisi apa adanya (gejala yang
#     user pertanyakan = mekanisme tsb; terdokumentasi docstring
#     deviasi_view).
# v3.9.26 (user: "potensi flip flop itu harusnya yang selisih nya
# dikit aja"): ARAH LABEL ANALISA 'Potensi Flip Flop' DIBALIK —
# audit 41-a (logika hanya di 2 titik komparasi_deviasi_view) +
# 41-b data real (87,9% pasangan flip = Parsial; aturan lama
# melabeli flip miring/noise [DEV 0,1 → GR −780] sbg 'Potensi Flip
# Flop' sedang cermin sejati [−9.525 → +9.551, selisih 26] cuma
# 'Berubah Arah'). DEFINISI BARU: pasangan flip (tanda DEV
# berlawanan) dgn SELISIH MAGNITUDO KECIL (disparitas <
# FFLOP_DISP_MAX 40% — Kategori Sempurna/Dominan; nilai bercermin ±,
# mis. −50 → +55: deviasi sama besarnya cuma pindah sisi → rawan
# bolak-balik) = 'Potensi Flip Flop'; disparitas ≥ 40% (Parsial —
# sisi dominan jauh lebih besar, mis. −100 → +10: deviasi nyaris
# hilang/membesar, arah benar-benar berganti) = 'Berubah Arah'.
# SATU konstanta FFLOP_DISP_MAX 0.40 utk TABEL TOP SELISIH
# (_top_aggregate) & PERUBAHAN ARAH (_render_flip + batas Kategori
# flip — FFLOP ⟺ Sempurna/Dominan, ARAH ⟺ Parsial; batas 0.40
# PERSIS mengikuti Kategori: strictly <). Prioritas np.select utuh
# (flip > Stabil); tanda sama tidak pernah FFLOP; label string,
# warna tag, filter, sort, export TIDAK berubah.
# v3.9.25 (user: "POP UP DI tab deviasi gr dan deviasi pcs perbesar
# lagi dan tambah kolom nomor po dan COM"): popup ringkas Deviasi GR/PCS
# (double-click baris) DIPERBESAR 880×480 → 1180×640 (minsize 820×340;
# judul wraplength 1020) + DUA kolom baru:
# (1) "Nomor PO" — nomor pesanan pembelian (PO......) baris 4.IN per
#     tanggal, split koma → dedup → urut → gabung (pola kolom Nomor
#     v3.9.22; IT. pemindahan biasanya tanpa PO → kosong);
# (2) "COM" — pemakaian harian per tanggal, formula PERSIS baris
#     6.PEMAKAIAN (COM) tab Pivot / 🚨 Anomali COM:
#         com(t) = so_prev(t) + IN(t) − BK(t) − SO(t)
#     _compute_com_series (deviasi_popup) = PORT laporan_deviasi_view.
#     _compute_com_matrix: kolom tanggal GLOBAL (union 4 JENIS — SALDO
#     AWAL/1.SO/4.IN/8.BARANG KELUAR — SEMUA pasangan di frame, persis
#     col_keys laporan; pasangan tanpa baris SO di kolom global t−1
#     dibaca 0); tanggal 1 → base SALDO AWAL pasangan bila ada (audit
#     fix v3.9.5, dibaca TANPA fill), fallback so_prev; parity 48/48
#     nilai vs matrix Anomali COM (diverifikasi test §35 langsung vs
#     matrix). Tanggal di luar kolom global (mis. hanya 2.SALDO AKHIR)
#     → COM kosong. Dihitung DALAM grup satuan yang diklik (FIX 35-b).
#     COM minus ikut merah PER CELL (Tk 9; fallback Tk 8 tag baris).
# v3.9.24 (user: "jika saat ini bulan oktober maka 1 periode nya mulai
# dari 26 september - 25 oktober nah untuk cek RI balancing berarti
# dengan NO. PO yang bukan bulan september dan oktober … AIR MINERAL
# punya resto TGRGEL transaksi tanggal 1 oktober ada RI RI.2026.10.10354
# dengan PO PO.2026.08.00571"):
# DEFINISI RI BALANCING DIPERBAIKI — dari "bulan Nomor RI ≠ bulan
# Nomor PO" (v3.9.19-23) menjadi PERIODE BISNIS 26→25: satu periode =
# tgl 26 bulan lalu s/d tgl 25 bulan ini (mencakup DUA bulan kalender).
# Dokumen RI tgl 1-25 → PO periodenya {bulan-1, bulan}; tgl 26-31 →
# {bulan, bulan+1} (wrap tahun Des↔Jan; tanggal bulan-lalu negatif
# dibaca absolut). Balancing = Nomor PO dari periode DI LUAR dua bulan
# itu — contoh user: RI 1 Okt ↔ PO Agu → balancing; RI 1 Okt ↔ PO Sep
# → BUKAN balancing (v3.9.19-23 SALAH FLAG kasus ini — PO bulan
# sebelumnya satu periode dgn RI-nya). Satu logika doc_codes._ri_
# balancing(nomor, po, tanggal) dipakai CEK kolom utama Deviasi +
# popup Rincian IN + Catatan Audit B1; tanpa tanggal valid (NaN/
# invalid) → fallback aturan lama bulan≠bulan (konservatif).
# v3.9.23 (user: "kerjakan poin 6 dan kerjakan semua poin B"):
# (1) POIN 6 — CEK "RI Balancing" DI KOLOM CEK UTAMA tab Deviasi GR & PCS:
#     pasangan barang×resto yang punya ≥1 dokumen IN dgn periode Nomor RI
#     ≠ periode Nomor PO (tanggal dokumen ≤ H) kini TERFLAG langsung di
#     tabel utama — dulu hanya terlihat di popup Rincian IN (harus buka
#     baris per baris). Prioritas: Promix 04 → RI Balancing → kondisi
#     pola numerik (Kosong/Tanggal/Manual/Drastis/ACR) — anomali
#     struktural dokumen (faktual) di atas heuristik pola; helper
#     diangkat ke modul bersama doc_codes.py (tidak diduplikasi).
# (2) SEMUA POIN B — CATATAN AUDIT OTOMATIS tab Rekap Selisih IN: kolom
#     Catatan Audit diperkaya catatan app per baris (di-append ke catatan
#     engine VBA, dipisah " | " — isi VBA tidak berubah): B1 RI
#     Balancing (nomor dokumen + bulan beda), B2 Nomor Dobel (input
#     ganda/sheet kembar), B3 Selisih IN ≠ 0 (arah & besar perbedaan),
#     B4 BM 0 padahal IN > 0 (input rekap belum diisi). Ikut ke 💾 Export.
# v3.9.22 — 7 permintaan user + deep audit semua perhitungan:
# (1) PER-CELL WARNA DI SEMUA VERSI Tk (user: "Saat ini disemua tab
#     warna masih tidak per cell tapi per row. coba cari alternatif
#     lain"): Tk 8.6 (Python standar Windows) tidak punya API tag cell
#     → ALTERNATIF overlay tk.Label per sel (CellColorOverlay,
#     widgets.py — virtual, event forwarding, double-click manual,
#     merge 2 tag; clone ⛶ & hierarki pivot didukung).
# (2) ANALISA KOMPARASI TUNGGAL (user: "hapus tab liga deviasi" +
#     "hapus arah minoritas" + "dead code nya juga hapus"): bagian
#     Minoritas & Liga dihapus penuh — tersisa Top & Flip.
# (3) CEK "Beda Tanggal" SO-STAEL (user: "Dikolom CEK analisa Beda
#     tanggal kok tidak ada ya"): pasangan dgn tanggal SO nonzero
#     terakhir < H terflag (belum SO tanggal analisa); prioritas
#     Promix 04 tetap pertama.
# (4) POPUP + KOLOM NOMOR (user: "Pop up di tab Deviasi GR dan PCS ada
#     Nomor nya juga Misal IT...... atau RI......"): nomor dokumen IN
#     per tanggal (dedup+urut+koma).
# (5) TANGGAL H DINAMIS (user: "Tanggal harusnya tanggal 26 bukan dari
#     tanggal 25"): H = tanggal SO nonzero terakhir saat data dimuat
#     (fallback 26; reset di ✕ Reset Filter; minggu komparasi 15..31 →
#     WEEK 4 — dulu 26..31 → "WEEK 5" tak pernah ada di file).
# (6) REKAP SELISIH IN default KATEGORI = Deviasi (user: "Rekap selisih
#     IN Default Kategori Deviasi") — di load & reset, tetap fleksibel.
# (7) DEEP AUDIT (user: "deep audit semua perhitungan apakah sudah
#     benar dan sesuai dan valid?"): BUG append1 pivot_table(dropna=
#     False) KOMBINASI KARTESIAN pasangan×tanggal (baris fantom) →
#     groupby+pivot (data real 768.000 → 527.528 baris); JENIS
#     case-drift dinormalisasi; export None → literal 'None' dibersihkan.
# v3.9.21 — 4 permintaan user:
# (1) AMBANG ACR to BOM (user: "di bagian ACR to BOM itu harusnya ada
#     threshold > 80% absolute dan aku bisa atur"): CEK kondisi ke-5 kini
#     |Deviasi| > (ambang/100) × Total ACR — dulu kaku > 100% × Total
#     ACR. Ambang default 80, spinbox "AMBANG ACR to BOM" di kartu Filter
#     KEDUA tab Deviasi GR & PCS (sinkron via SharedACRThreshold — pola
#     TANGGAL H); ubah ambang → pivot cache di-clear + recompute live;
#     nilai bertahan lintas sesi (settings.json, atomic write; file
#     hilang/korup → default 80 senyap).
# (2) PROMIX 04 PER-TANGGAL (user: "pada bagian CEK ada muncul nilai
#     Promix 04 di filter tapi kenapa data nya tidak ada?"): sumber SO
#     kini diresolve PER (pasangan × tanggal) atas baris rekap ber-NILAI
#     NON-NOL (append1 LANGKAH 9 merge per (pasangan, Tanggal); 'input
#     so harian' menang atas promix pada tanggal sama — hitungan manual;
#     baris template bernilai 0/NaN & sumber whitespace-only tidak
#     menentukan). deviasi_view membaca sumber baris 1.SO TANGGAL H —
#     label "Promix 04" muncul HANYA bila SO tanggal analisa BENAR
#     bersumber promix. Menggantikan resolusi pair-level "tanggal
#     tertinggi" yang rapuh: v3.9.19 bisa melabel SEMUA pasangan campuran
#     Promix (tie urutan baris — persis phantom yang user lihat);
#     v3.9.20 swing kebalikan (tak pernah Promix meski SO tanggal H
#     memang turunan promix — data real 01.1 CEK STOCK V2: 12 pasangan
#     promix di tgl 25 kini terlabel benar, 0 phantom).
# (3) TIDAK BERTABRAKAN dgn CEK lain (user: "Promix 04 bakal bertabrakan
#     gak logika nya dengan analisa CEK yang lain?"): prioritas tetap —
#     Promix 04 kondisi PERTAMA (SO sistem-turunan → pola naik/turun SO
#     tak bermakna); dgn resolusi per-tanggal label jadi AKURAT sehingga
#     pasangan so-harian dievaluasi CEK normal sepenuhnya.
# (4) MINUS PER-CELL LAPORAN DEVIASI (user: "nilai minus juga diberi
#     warna merah pada cell aja di tab laporan deviasi"): Anomali COM —
#     Median & Selisih vs Median kini ikut merah per-cell (dulu hanya
#     COM); Liga Deviasi — Rate minus ikut merah (⟺ DEV minus).
# v3.9.20 — DEEP AUDIT & FIX (5 agen audit + 5 agen fix): 1 BUG + 15 RISK diperbaiki + penuntasan "semua filter = data yang ada" (komparasi reset/popup · deviasi satuan/chrono/source · rincian NA/float/NaT/periode · pivot/FU/export · pipeline LANGKAH 9/sheet lalu/fn_4205)
# v3.9.20 — DEEP AUDIT & FIX (gelombang audit 34-a..34-e + fix 35-a..35-d,
# 25 perbaikan; 1 BUG + 15 RISK + 9 hardening/NIT):
# (1) KOMPARASI (35-a/audit 34-a): reset filter 4 tabel analisa (Top/Flip/
#     Minoritas/Liga) di SEMUA jalur reset tabel utama (load_data /
#     _load_paths / _close_file / ✕ Reset Filter — dulu filter basi
#     senyap → 0 baris di file baru); nilai popup filter tabel utama ⚖
#     + Arah Minoritas + Liga Deviasi kini BARIS YANG TAMPIL (param
#     fmt_fn di _filtered_analisa_series — penuntasan "berlaku untuk
#     semua filter"); 4 entri format kolom mati Risk/Bench dibersihkan.
# (2) DEVIASI + POPUP (35-b/audit 34-b): _hl_cells diinisialisasi di
#     __init__ (sort/reapply tag sebelum render pertama tidak lagi
#     AttributeError di Tk 9); popup ringkas memfilter SATUAN — angka
#     GR/PCS = BARIS YANG DIKLIK (dulu menjumlahkan lintas satuan);
#     _chrono_key float-safe (urutan 25•..31• benar utk Tanggal
#     float64); _so_source_lookup keep-LAST sort-Tanggal (preferensi
#     append1 LANGKAH 9 — baris berjalan menang); _compute_cek (kode
#     mati) dihapus penuh.
# (3) RINCIAN PO + RINCIAN IN (35-c1/audit 34-c+34-e): BUG clone ⛶
#     InSelisihView kini reapply tag neg per-cell (on_render_done —
#     dulu minus kehilangan warna di Layar Penuh); _resto_name pd.NA-
#     safe + float integral (1370.0 → "1370", dulu "0"); _fmt_date/
#     _fmt_datetime NaT-safe (dulu ValueError → tab mati); load_data
#     reset combo Cabang/Status (dulu filter basi → 0 baris senyap);
#     RI Balancing membandingkan PERIODE (tahun, bulan) dgn bulan
#     1-2 digit numerik — lintas-tahun-same-month kini terflag;
#     literal "None"/"nan"/"NaT" dibuang dari daftar nilai popup.
# (4) PIVOT + FOLLOWUP + EXPORT (35-c2/audit 34-e): popup Nama Barang
#     pivot = barang yang TAMPIL (RESTO mode Tanggal + SOURCE +
#     KATEGORI + rentang Tanggal + ☑ sembunyikan-baris-kosong; filter
#     sendiri dikecualikan); popup kolom FollowUp = baris tampil; F401
#     C_TEXT_MUTED dibersihkan; merah negatif pivot #CC0000 → #dc2626
#     (seragam 11 view); export sheet "Rincian PO" + kolom Nama Resto
#     (import _resto_name — tanpa duplikasi helper).
# (5) PIPELINE (35-d/audit 34-d): append1 LANGKAH 9 tie-break
#     DETERMINISTIK (mergesort + kunci sekunder bentuk-string SOURCE
#     DATA — tie → "input so harian" menang, konservatif utk CEK
#     Promix 04) + na_position="first" (NA-Tanggal tak pernah menang)
#     + SOURCE DATA di-strip (NA-safe); resolusi sheet folder bulan-
#     lalu: key dedikasi Sheets["Pemindahan4205Lalu"] + fallback
#     prefiks modul "#42.05"/"#32.24" (sheet lalu beda nama ≠ lagi 0
#     baris senyap — 32.24 & 42.05 konsisten); fn_4205 mode "lalu"
#     filter baris resto SEBELUM max_t (mirror persis fn_3224 — NA-
#     resto tak lagi menggeser jendela 5 hari).
# v3.9.19 — KOLOM ANALISA + HAPUS RISIKO/BENCHMARK + DEFAULT KATEGORI + NAMA RESTO PO + FILTER DATA-ADA + PROMIX 04 + 9.ACR + RI BALANCING
# v3.9.19 — 8 permintaan user:
# (1) KOLOM ANALISA (user: "tambah kolom baru untuk keterangan kenaikan
#     tertinggi, penurunan tertinggi, stabil, berubah arah, potensi
#     flip flop pada laporan deviasi tab TOP and FLIP. 1 kolom aja"):
#     bagian 📊 Top & Flip mode 📈 Analisa (tab 📋 Laporan Deviasi) —
#     tabel Top Selisih & Perubahan Arah kini berkolom ANALISA:
#     Kenaikan Tertinggi · Penurunan Tertinggi · Stabil · Berubah Arah
#     · Potensi Flip Flop (tanda berlawanan + disparitas ambang 40%
#     sama dgn Kategori flip; warna per-cell).
# (2) HAPUS BAGIAN (user: "hapus tab resiko flip dan bencmark"):
#     baris BAGIAN kini 3 bagian (Top & Flip · Arah Minoritas · Liga
#     Deviasi) — render/UI/metode ⚡ Risiko Flip & 💰 Benchmark
#     dihapus penuh.
# (3) DEFAULT KATEGORI (user: "secara default kategori terfilter ke
#     kategori Deviasi"): combobox KATEGORI tab Deviasi GR/PCS default
#     "Deviasi" (case-insensitive; fallback "Semua") saat load data &
#     ✕ Reset Filter.
# (4) NAMA RESTO DI RINCIAN PO (user: "tambahkan kolom nama resto di
#     rincian PO"): kolom baru di baris induk — dari Cabang PO
#     ("1370.MLGPAR" → "MLGPAR"), ikut filter header ⧩.
# (5) FILTER = DATA YANG ADA (user: "isi filter harus menampilkan data
#     yang ada aja bukan termasuk data yang tidak ada — berlaku untuk
#     semua filter"): daftar nilai filter header dihitung dari baris
#     yang TAMPIL (mode Satuan + KATEGORI + filter kolom lain — kolom
#     sendiri dikecualikan; perilaku AutoFilter Excel) di tab Deviasi
#     GR/PCS, Rincian PO, Rekap Selisih IN (juga rentang tanggal +
#     hanya-selisih), Anomali COM, dan tabel Top/Flip komparasi.
# (6) CEK "Promix 04" (user: "jika SO nya bersumber tanpa input so
#     harian maka tampilkan Promix 04"): SOURCE DATA REKAP MENTAH
#     JENIS SO ("input so harian" / "input promix 04 dine in" /
#     "take away") dibawa append1 per pasangan; CEK kondisi ke-0
#     (prioritas pertama — pola CEK lain tak bermakna utk SO turunan
#     sistem): bukan "input so harian" → "Promix 04".
# (7) ISTILAH 9.OUT → 9.ACR (user: "ganti istilah 9.OUT menjadi
#     9.ACR"): JENIS penjualan 22.05 kini "9.ACR" (rename_map append1,
#     METRICS pivot, deviasi/komparasi/tests) — data mentah tak berubah.
# (8) CEK "RI Balancing" (user: "jika bulan PO dan bulan RI tidak sama
#     ... kasih aja keterangannya RI Balancing"): popup Rincian IN
#     (tab 📤) berkolom CEK — dokumen RI.2026.10.10354 vs
#     PO.2026.08.00571 (struktur PREFIKS.TAHUN.BULAN.NOMOR): bulan
#     beda → "RI Balancing" (amber per-cell).
# v3.9.18 — FOKUS RESTO 1. DEVIASI WEEKLY + POPUP RINGKAS + KOLOM + HIGHLIGHT (tab Deviasi GR/PCS)
# v3.9.18 — 5 permintaan user utk tab 📦 Deviasi GR & 🧩 Deviasi PCS:
# (1) FOKUS RESTO (user: "resto yang dianalisa hanya berfokus pada
#     resto yang ada di folder 1. DEVIASI WEEKLY aja jangan semua"):
#     pivot hanya memuat pasangan (barang × resto) yang RESTOnya punya
#     data rekap berjalan — JENIS 1.SO / 5.BARANG MASUK dgn Tanggal
#     POSITIF (= sheet '1  DEVIASI WEEKLY' folder RekapBerjalan; rekap
#     bulan lalu bernomor NEGATIF & berasal dari folder lain — tidak
#     ikut menentukan scope). Resto yang hanya ada di sumber app
#     (32.24/42.05/9901/22.05/42.15) dikeluarkan — barisnya dulu
#     menampilkan Deviasi = 0 − Sistem = minus palsu.
# (2) LOOKUP BARANG DUA ARAH (user: "look up nama barang ini pakai dua
#     arah ... tidak hanya barang di folder deviasi weekly aja tapi
#     juga sebaliknya"): barang TIDAK difilter — utk resto rekap,
#     barang ber-SO rekap MAUPUN barang yang HANYA ada di data app
#     (IN/OUT/SALDO AKHIR saja, SO = 0) keduanya tampil.
# (3) POPUP RINGKAS (user: "pop up di deviasi GR ataupun PCS hanya
#     tampilkan: nama barang, nama resto, nilai saldo akhir, nilai SO,
#     nilai IN, nilai deviasi"): double-click kini membuka popup
#     ringkas BARU (src/ui/deviasi_popup.py — judul 'Nama Barang —
#     Nama Resto (satuan)', tabel per Tanggal hanya Tanggal · Saldo
#     Akhir · SO · IN · Deviasi; '25•' = bulan lalu; baris H latar
#     lembut; minus merah per-cell + fallback Tk 8). Popup source
#     rows lama (JENIS/Nomor/Nomor PO/Tgl-Jam/KATEGORI/SOURCE) TIDAK
#     lagi terbuka dari tab ini — tetap dipakai tab Pivot/Laporan.
# (4) KOLOM DIHAPUS (user: "tab deviasi GR dan PCS hapus kolom: max
#     dev, acr, total acr"): kolom Max Deviasi / ACR / Total ACR
#     dihapus dari TAMPILAN GR & PCS — hitungan internal TETAP persis
#     v3.9.6 (CEK kondisi ke-5 'ACR to BOM' · Dev to BOM% · Stok
#     Seharusnya · snapshot loss_bom Follow Up tetap benar).
# (5) HIGHLIGHT (user: "highlight kolom deviasi dan kolom SO H"):
#     latar lembut #fef3c7 di SEMUA sel kolom Deviasi & SO_H via tag
#     cell (Tk 9 — terukur pixel: bg cell-tag menang atas bg
#     evenrow/oddrow; fg minus merah tetap hidup di atasnya; dipasang
#     ulang setelah sort/filter/clone). Fallback Tk 8: tanpa tint
#     kolom. Legenda + chip 'kolom Deviasi/SO_H'.
# v3.9.17 — (1) SUMBER IN BARU (permintaan user: "tambahkan juga di
# alamat C:\KERJA\1. RESTO\9.NEW QUERY\4.1 4205 Bulan Lalu — ini
# sebagai penambah IN untuk periode 25-31 bulan lalu sama seperti 32.24
# bulanlalu"): folder baru config Pemindahan4205Lalu dibaca
# fn_4205(mode="lalu") — MIRROR PERSIS fn_3224 "lalu": 5 hari terakhir
# file bulan lalu (Tanggal >= maxT-4) + Tanggal dinegasikan (hari
# negatif = bulan lalu) → masuk query_in sebagai sumber IN tag
# "42.05 (Bulan Lalu)" + Qty SJ audit (Kiriman HO / export) + popup
# Rincian IN (grup tabel & chip teal). Folder kosong/tidak ada → 0 baris
# senyap (tidak wajib ada tiap bulan). (2) FOLLOW UP MINUS PER-CELL:
# tab ☑ Follow Up kini mewarnai HANYA sel bernilai minus (semua kolom
# numerik — Tk 9 `tag cell`; fallback Tk 8 tag baris, konsisten view
# lain sejak v3.9.2) — dulu tab ini TIDAK punya jalur per-cell: satu
# Deviasi minus mewarnai SELURUH baris + tag 'negative' (menang
# pertama) menimpa warna status resolved/pending; sort & clone ⛶
# memasang ulang tag (pola FIX B-03/B-12).
# v3.9.16 — TOP SELISIH: ABSOLUT + MEDIAN MULTI-FILE (permintaan user,
# khusus mode 📈 Analisa di tab 📋 Laporan Deviasi — tabel utama ⚖ &
# bagian analisa lain TIDAK berubah):
# (1) ABSOLUT: Selisih = |GR Saat Ini| − |DEV Lalu| (kedua nilai
#     diabsolutkan DULU — pembalikan tanda −50 → +30 tidak lagi
#     menggembungkan selisih: dulu 80 kini 20); kolom DEV Lalu / GR
#     Saat Ini tetap NILAI ASLI; Status MATCH/SELISIH (khusus tabel
#     Top Selisih) ikut toleransi Selisih absolut.
# (2) MEDIAN MULTI-FILE: file deviasi >1 → nilai Lalu per pasangan
#     (resto×bahan×minggu sama) = MEDIAN antar-file — SATU baris per
#     pasangan (bukan satu baris per file); yang ditampilkan nilai
#     median saja; Periode 'Median n file · Minggu' (≥2 file) /
#     'BULAN · Minggu' (1 file); kolom Periode kini kolom NYATA.
# v3.9.15 — GELOMBANG 1 (adopsi rumus repo Inventory-Control user; 4
# analisa baru sebagai BAGIAN di mode 📈 Analisa — baris "BAGIAN"
# SegmentBar: Top & Flip · Risiko Flip · Arah Minoritas · Liga Deviasi ·
# Benchmark; hanya bagian AKTIF yang dirender — pola malas v3.9.14,
# komputasi VEKTOR penuh):
# (1) ⚡ RISIKO FLIP PER BAHAN: skor = min(100, 30×Sempurna + 10×Flip),
#     Level TINGGI/SEDANG/RENDAH; klik-2× → popup resto kontributor.
# (2) 🧭 ARAH MINORITAS PER BAHAN: resto yang arah DEV-nya melawan
#     mayoritas (mayoritas ketat) — kandidat salah-input; klik-2× →
#     popup resto minoritas.
# (3) 🏆 LIGA DEVIASI-RATE PER BAHAN: rate = |DEV|/|BOM| per resto;
#     baseline median+MAD → robust-z = (rate−median)/(1,4826×MAD);
#     guard ≥5 resto ber-BOM & MAD>0; DEV 0 ikut populasi tak diranking.
# (4) 💰 BENCHMARK OPPORTUNITY: per resto (kelompok = 3 huruf awal kode
#     resto) loss = Σ|DEV<0|; opportunity = max(0, loss − median
#     kelompok) + total.
# Analisa per-periode (2/3/4) = BULAN TERBARU + SATU minggu snapshot
# (minggu yang memuat H — minggu file kumulatif: menjumlah lintas minggu
# = menghitung ganda).
# v3.9.14 (permintaan user: "tab analisa kenapa lemot sekali" deep audit
# performa + "week di tab analisa harusnya menyesuaikan kolom H — jika 7
# berarti week 1" + "ganti istilah app menjadi Saat ini dan File menjadi
# Lalu") — SEMUA di komparasi_deviasi_view.py:
# (1) PERF: analisa dirender MALAS (hanya saat mode 📈 aktif — dulu ikut
#     dirender walau tersembunyi: ±4,8 dtk freeze PER refresh di file
#     40rb baris); flip VEKTOR (sort+shift — dulu groupby+sort per grup
#     4,7 dtk → ±50ms, hasil identik); nilai app per baris via MERGE
#     vektor (dulu loop Series.get 2,9 dtk → ±60ms; terverifikasi
#     identik); Top Selisih tanpa iterrows.
# (2) MINGGU: Top Selisih & Perubahan Arah difilter minggu yang MEMUAT
#     H (H=7 → WEEK 1) — konsisten tabel utama.
# (3) ISTILAH: kolom *File → *Lalu, *App → *Saat Ini; status 'TIDAK ADA
#     DI DATA APP' → 'TIDAK ADA DI DATA SAAT INI'.
# v3.9.13 (6 permintaan user + adopsi rumus repo Inventory-Control user):
# (1) FILTER "HASIL SEARCH = PILIHAN": Enter di popup filter header
#     (semua tab) menjadikan HASIL PENCARIAN sebagai seleksi — 0 hasil =
#     0 baris (perilaku Excel) + operator teks (Mengandung/Diawali/
#     Diakhiri/Tidak mengandung) + tombol ↔ Balik (invert). State
#     seleksi EKSAK (nilai >3000 non-materialized ikut terhitung);
#     uncheck-semua kini 0 baris (dulu tampil semua).
# (2) FILTER KATEGORI di tab 📦 Deviasi GR & 🧩 Deviasi PCS: kolom
#     KATEGORI (data DBS sudah ada di pipeline) + combobox KATEGORI di
#     kartu Filter (post-pivot — SharedPivotCache tetap 1× GR+PCS).
# (3) PATH FILE DEVIASI tersimpan & BISA DIUBAH: entry editable
#     (multi-file dipisah ";") + 📂 multi-select + ↻; komparasi_last.json
#     {"paths": [...]} + AUTO-LOAD file terakhir saat tab terlihat.
#     FIX BUG v3.9.10: .with_suffix pada str → json TIDAK PERNAH tersimpan
#     sejak v3.9.10 (path file deviasi "tidak pernah teringat").
# (4) KOLOM LAPORAN DEVIASI (permintaan "hapus kolom H, minggu juga
#     hapus, Dev to bom harusnya persen"): kolom Minggu & H DIHAPUS dari
#     tabel (16→14; data internal tetap utk filter minggu/join/popup);
#     DEV App kini %TO BOM — App = DEV·App / |BOM·App| (persen — dulu
#     kuantitas; konsisten %TO BOM File & Dev to BOM% tab Deviasi).
# (5) MODE 📈 ANALISA (adopsi rumus repo Inventory-Control user):
#     Top Selisih (peringkat |GR App − DEV File| tertinggi, Top-N) +
#     PERUBAHAN ARAH ("flip": bulan berurutan MINGGU SAMA dengan tanda
#     DEV berlawanan — minus bulan lalu → surplus sekarang; Disparitas
#     = |P1+P2|/max(|P1|,|P2|): Sempurna <10% / Dominan 10–40% / Parsial
#     ≥40%; urut disparitas naik).
# (6) MULTI-FILE DEVIASI: 📂 askopenfilenames — semua file diparse di
#     worker & digabung; BULAN ikut dedup-key (baris bulan lain TIDAK
#     dibuang); default tabel = BULAN TERBARU (checkbox "Tampilkan semua
#     bulan"); label info per-file; file gagal dilewati (dilaporkan).
# v3.9.12 — TAB 🎯 PARETO DIHAPUS (user: "hapus tab pareto dan dead code nya")
# v3.9.11 (TUNTAS SISA TEMUAN AUDIT — "kerjakan semua & repo pribadi"):
# (0) P0 D-11 DIEKSEKUSI: repo GitHub anandategarch/Stock-Monitoring
#     kini PRIVATE (permintaan user "repo untuk pribadi aja") — workbook
#     produksi + objek 2205.xlsx di history tidak lagi dapat diakses
#     publik; BFG rewrite tidak diperlukan.
# (1) FIX B-21 sort kini BERINDIKATOR ARAH di heading (↓ menurun / ↑
#     menaik; panah lama kolom lain dibersihkan) — sebelumnya sort via
#     popup ↕ mengubah urutan tanpa jejak kolom mana yang terurut.
# (2) FIX B-14 toggle filter di clone ⛶ tidak lagi MENGEMBALIKAN urutan
#     sort (rebuild dulu dari cache urutan asli; sort terakhir kini
#     dijalankan ulang SEBELUM reapply tag per-cell).
# (3) FIX B-09 sort_tree_by_column untuk tree BERHIRARKI: jalur baru
#     tree.move (subtree + text #0 + state open terjaga; jalur lama
#     delete+reinsert MENGHAPUS anak) — latent utk caller saat ini
#     (semua datar), jalur flat O(n) tetap + kini pertahankan text/open.
# (4) FIX B-18 mirror kolom ⛶ DUA ARAH: hide/unhide kolom di tabel
#     UTAMA kini tercermin juga di window clone yang terbuka (dulu satu
#     arah clone→source saja).
# (5) FIX B-17 cursor "watch" LoadingOverlay BER-REFCOUNT per toplevel
#     — overlay pertama yang selesai tidak lagi me-reset cursor saat
#     overlay kedua masih loading; + klaim dilepas saat widget destroy.
# (6) FIX B-16 TableExpander.restore iterasi REVERSE — ≥2 target pack
#     berturut di akhir urutan tidak lagi terpasang TERBALIK.
# (7) FIX B-12 validated_tgl_entry + _on_tanggal_change Selisih IN:
#     pecahan ("7.9") DITOLAK warning+revert — dulu dilantai SENYAP
#     menjadi 7 oleh int(float()).
# (8) FIX B-11 EmptyState frame center ADAPTIF (clamp 520×260) — dulu
#     fixed 520×260: konten CTA terpotong di jendela sempit.
# v3.9.10 (DEEP AUDIT UI/UX ROUND 2 — 4 agent paralel, 37 temuan):
# (1) P1 RACE & ROBUSTNESS: FIX A-01 Stop→MULAI kini menghentikan
#     benar (guard worker masih hidup — dulu 2 pipeline bisa jalan
#     paralel & stop_event.clear() membatalkan Stop); FIX D-01 worker
#     capture data/H di awal compute (cache poisoning — data basi
#     senyap saat pipeline selesai di tengah refresh view); FIX C-02
#     rincian_po & details_popup kini punya on_error (view tidak lagi
#     mati permanen setelah 1 exception — kelas fix B-01 v3.9.1);
#     FIX B-01 sort Rekap Selisih IN pakai parser angka Indonesia;
#     FIX D-04 file Excel terkunci/hilang di-skip → KPI/status kini
#     memberi tahu (dulu "SELESAI" polos menutupi data parsial).
# (2) P2 TABEL: FIX B-02 tag minus/merah per-cell bertahan di clone ⛶
#     setelah filter (4 view + popup detail); FIX B-03 sort Selisih
#     IN tidak lagi menghapus tag minus; FIX B-04 bind add="+" —
#     auto-fit double-click tepi kolom hidup lagi di semua tabel;
#     FIX B-05 filter header >3000 nilai: nilai hasil pencarian di
#     luar cap kini DAPAT dicentang (checkbox lazy); FIX B-06 gc_shield
#     thread-safe (Lock); FIX B-07 filter clone saat copy awal (cancel
#     batch); FIX B-08 sort saat render batch → antre (3 view);
#     FIX D-03 followup render race (cancel insert lama).
# (3) P2 SHELL: FIX A-02 tombol Export disabled kini tampak DIM
#     (set_enabled — fix v3.9.1 akhirnya dipakai di semua call-site);
#     FIX A-03 DPI-awareness Windows 125%/150%; FIX A-04 Ctrl+Tab
#     navigasi tab (notebook.enable_traversal); FIX A-11 routing tab
#     berbasis widget (bukan index — tab disisipkan tak merusak).
# (4) P3 KONSISTENSI: FIX C-03 format angka Indonesia di Rincian PO &
#     popup detail (dulu EN "1,234.5"); FIX C-04 minus merah per-cell
#     di tabel Rekap Selisih IN; FIX C-06 sisa frasa instruksi dipangkas;
#     FIX C-10 footer "rows"→"baris" + fmt Indonesia; FIX C-07/C-08
#     deviasi unsubscribe-H + refresh saat tersembunyi cukup dirty;
#     FIX D-05/D-06 config & komparasi_last atomic write; FIX A-09
#     literal warna → token theme.
# v3.9.12 (TAB 🎯 PARETO DIHAPUS — user: "hapus tab pareto dan dead
# code nya"):
# (1) tab 🎯 Pareto (v3.9.9) DIHAPUS dari notebook — app kembali 9 tab;
#     index tab setelahnya bergeser -1 (routing berbasis widget A-11 —
#     tidak ada index angka ajaib yang perlu digeser).
# (2) DEAD CODE dihapus penuh: src/ui/pareto_view.py (ParetoDeviasiView
#     — subclass DeviasiView, 823 baris) + write_pareto_sheet() section
#     4 di export_sheets.py + integrasi app.py (frame tab, notebook.add,
#     _build_pareto_tab, entry _tab_views, load_data fan-out).
# (3) Fitur lain TIDAK tersentuh: Deviasi GR/PCS tetap memakai
#     SharedPivotCache + SharedTanggalH; ✓ Follow Up dari tab lain
#     tetap jalan; export sheet lain tetap utuh.

# v3.9.6 (3 permintaan user sekaligus):
# (1) "tambah kategori Deviasi pada tab Deviasi PCS dan GR" — 5 kolom
#     baru (mirror sheet DEVIASI GR/PCS workbook asli): Max Deviasi ·
#     ACR (rata-rata penjualan harian = Σ 9.ACR 1..H / H) · Total ACR
#     (BOM per barang×resto = Σ penjualan 1..H) · Dev to BOM% (= Deviasi
#     / Total ACR — "Loss Surplus to BOM") · Stok Seharusnya (= SO(H−1) −
#     ACR) + CEK kondisi ke-5 "ACR to BOM" (|Deviasi| > Total ACR —
#     melengkapi port formula LET yang dulu 4/5 kondisi) + parser sort
#     Indonesia utk semua kolom numerik.
# (2) "Tab selisih in jika tanggal 1 pembanding SO nya SO bulan lalu" —
#     urutan baris audit kini KRONOLOGIS (bulan lalu 25•→31• lalu 1..31);
#     dulu sort numerik membalik urutan bulan lalu sehingga delta SO di
#     tanggal 1 membanding SO tgl 25• (BUKAN SO terakhir bulan lalu).
# (3) "Format Follow UP Seperti File Sample" — tabel + export tab ☑
#     Follow Up kini persis sheet Follow UP file asli: Resto · Nama
#     Barang · SO per tanggal (H-2..H+2, heading angka tanggal) ·
#     Sistem · Deviasi · Loss Surplus to BOM · Keterangan · SO · DEVIASI
#     · Selisih · Selisih Deviasi · Cek FU · PIC (+ pelacakan app).
# v3.9.4 (permintaan user: "Di file sampel kan ada Dev to bom ini kok gak
# ada ya? Padahal data udah lengkap 2205 itu bom. Aku barusan upload file
# deviasi. Nah aku mau compare file deviasi itu dengan yang deviasi di
# Tab deviasi GR terus coba cek kolom status week 1 itu sama dengan 7
# week 2 = 14 dan week = 25. Itu buat kolom h."):
# (1) TAB 📋 LAPORAN DEVIASI kini punya 2 MODE (SegmentBar):
#     ⚖ Komparasi File Deviasi (BARU — default) dan 🚨 Anomali COM (v3.9.3
#     dipertahankan, tinggal ganti segmen).
# (2) MODE KOMPARASI: pilih file deviasi resmi (mis. "20.AGUSTUS 2026.xlsx"
#     — RESTO/NAMA BAHAN/STATUS BULAN/QTY BOM/QTY COM/QTY DEVIASI/% TO
#     BOM). Tiap baris file dibandingkan sisi-app pada KOLOM H menurut
#     STATUS BULAN: WEEK 1→H 7 · WEEK 2→H 14 · WEEK 3/4→H 25 (permintaan
#     user; file sampel memakai WEEK 4, minggu = CUT-OFF KUMULATIF dari
#     tgl 1 — WEEK 2 ≈ 2× WEEK 1, konsisten semantik H).
# (3) "DEV TO BOM" kini ADA di app: BOM·App = Σ penjualan 22.05 (JENIS
#     9.ACR, tgl 1..H — "2205 itu bom"), COM·App = Σ pemakaian com(t)
#     tgl 1..H (com(t) = SO(t-1)+IN(t)−BK(t)−SO(t), formula identik
#     pivot 6.PEMAKAIAN & tab Anomali COM), DEV·App = COM−BOM (formula
#     identik file), GR·App = SO_H − Sistem_H (PERSIS kolom Deviasi di
#     tab 📦 Deviasi GR pada H minggu tsb — aljabar: GR·App = ΣOUT−SA−
#     ΣIN+ΣBK+SO_H = out_cum − com_cum = DEV·App, dua jalur hitung).
# (4) KOLOM: ✓ · Resto · Nama Barang · Satuan · Minggu · H · BOM/COM/DEV/
#     %TO BOM File · BOM/COM/DEV App · GR App · Selisih (GR App − DEV
#     File) · Status (MATCH / SELISIH / TIDAK ADA DI DATA APP / H TIDAK
#     ADA DI DATA). Resto file "1041.BDGUKU"/"B.1001.MLGPAR" dinormalkan
#     ke kode app (BDGUKU/MLGPAR). Default hanya resto yang ada di data
#     app (20 resto cek stock) — centang utk semua 340 cabang.
# (5) Infrastruktur utuh: ✓ follow-up (asal KOMPARASI), filter header ⧩,
#     sort parser Indonesia, ⛶ Layar Penuh, ⤢ Perbesar, ◱ Kolom, ↔
#     Auto-Fit, minus merah per-cell, sel Status hijau/amber/merah,
#     compute async + FIX B-01, path file terakhir diingat
#     (komparasi_last.json) → initialdir dialog.
# v3.9.3 — TAB LAPORAN DEVIASI → DAFTAR ANOMALI PEMAKAIAN (COM)
# v3.9.3 (permintaan user: "hapus isi data pada tab laporan deviasi dan
# sementara ganti dengan list nama barang dan resto yang pemakaian (com)
# nya minus atau lebih tinggi dari median pada pada kolom H"):
# (1) Isi tab 📋 LAPORAN DEVIASI DIGANTI (sementara; tabel Audit Harian
#     lama tersimpan di git history — commit e20141a): kini berisi DAFTAR
#     (Nama Barang × Resto) dengan nilai PEMAKAIAN (COM) pada kolom H yang
#     MINUS (< 0) atau LEBIH TINGGI dari MEDIAN pasangan tsb — v3.9.7
#     (koreksi user): median dihitung ANTAR TANGGAL (com(t) tgl 1..H
#     milik pasangan barang×resto; COM = pemakaian aktual harian di
#     resto, BOM = pemakaian harian versi sistem), BUKAN antar resto.
# (2) COM dihitung dgn formula identik baris 6.PEMAKAIAN (COM) di pivot
#     mode Tanggal: com(t) = SO(t-1) + IN(t) - BK(t) - SO(t), tanggal
#     pertama memakai SALDO AWAL. Matriks COM di-cache per data
#     (H-independen) — ganti H cukup pilih kolom, tanpa recompute pivot.
# (3) TANGGAL H = state bersama (SharedTanggalH v3.9): tab ini menampilkan
#     chip read-only + auto-refresh saat H di-apply di tab 📦 Deviasi GR.
# (4) Kolom: ✓ · Nama Barang · Resto · Satuan · COM (heading dinamis
#     "COM (H=25)") · Median · Selisih vs Median · Status (MINUS /
#     > MEDIAN / MINUS + > MEDIAN). Minus merah PER CELL (v3.9.2) + sel
#     Status merah/amber per-cell; parser sort numerik format Indonesia.
# (5) Follow-up ✓ tetap jalan (asal snapshot = LAPORAN-COM: SO=nilai COM,
#     Sistem=median, Deviasi=selisih, CEK=status).
# v3.9.2 — MINUS MERAH PER CELL + EXPORT PIVOT SESUAI TAMPILAN
# v3.9.2 (permintaan user: "minus harusnya cuman merah per cell bukan per
# baris dan pivot tabel nya bisa export excel"):
# (1) MINUS MERAH PER CELL (bukan per baris) di SEMUA tabel: Pivot matrix,
#     Deviasi GR/PCS, Laporan Deviasi, popup Rincian IN & popup Detail —
#     Tk 9 API `treeview tag cell add` (helper apply_cell_tag); hanya cell
#     bernilai negatif yang merah — label baris & cell lain tetap normal.
#     Baris 3.DEVIASI pivot tidak lagi selalu merah; 7.Selisih ≠ 0 tetap
#     fill merah muda per baris, font merah per-cell pada nilai ≠ 0.
#     Tag cell dipasang ulang otomatis setelah sort (delete+reinsert) &
#     clone ⛶ (hook on_render_done). Fallback Tk 8.6: perilaku lama.
# (2) Tombol 💾 Export Excel di tab 📊 PIVOT: matrix pivot SESUAI
#     TAMPILAN (filter RESTO/SOURCE/KATEGORI + rentang Tanggal + mode
#     🏪/📅 + sembunyikan-baris-kosong + kolom tampil ◱) → .xlsx:
#     minus = font merah PER CELL (mirror UI), 0 = font putih, metric bg,
#     header 25• bulan lalu biru, freeze B8 (write_pivot_display_sheet).
# v3.9.1 — DEEP AUDIT UI/UX → 15 FIX PORT KE v3.9
# v3.9.1 (hasil audit 39 temuan, 3 high — semua fix ditandai "# FIX <ID>"
# di kode, bisa di-grep):
# (1) B-01 (HIGH): _busy di-reset saat compute GAGAL — sebelumnya 1x error
#     membuat view mati permanen (Apply H/filter/reset berikutnya ditelan
#     guard `if self._busy`). on_error dipasang di 3 view (Deviasi/Pivot/
#     Rekap Selisih IN).
# (2) B-02 (HIGH): validasi input TANGGAL konsisten di semua view lewat
#     helper validated_tgl_entry (warning + revert, pola tab Deviasi) —
#     sebelumnya 3 perilaku beda: pivot fallback senyap, selisih int(float)
#     senyap, deviasi modal+revert. Jalur export selisih ikut tervalidasi.
# (3) B-03: popup funnel 600→3000 nilai + label jujur "menampilkan X dari Y".
# (4) B-07: ✕ Reset Filter kini juga reset TANGGAL H ke 25 (v3.9: lewat
#     SharedTanggalH — GR & PCS sync; tab GR ikut berlangganan listener).
# (5) C-03: format angka gaya INDONESIA konsisten (1.234.567 / 1.234,5 /
#     negatif kurung) di 3 view + KPI chips + log audit + popup TOTAL IN.
# (6) C-05: menu ⧩ Filter kolom non-#0 di Pivot tidak mati senyap — kini
#     diarahkan ke filter Nama + status bar menjelaskan.
# (7) A-01/A-02: tombol toolbar disabled kini terlihat DIM (teal→abu)
#     lewat Toolbar.add_action.set_enabled; konvensi konsisten.
# (8) A-04: (dihapus v3.9.8 — window Bantuan dihapus, UI clean).
# (9) A-08: teks fungsional font(8)→font(9): label KPI, legend, counter
#     filter, counter panel kolom, hint window clone (metadata tetap 8).
# Riwayat v3.9.0 — SHARED H + EXPORT AUDIT + RINCIAN PO RINGKAS + STYLE WASTE:
# (1) TANGGAL H dibagi 2 tab: input + "Apply H" hanya di tab 📦 Deviasi
#     GR, otomatis berlaku juga di tab 🧩 Deviasi PCS (chip read-only +
#     refresh otomatis — tidak ada double input; permintaan user);
#     SharedPivotCache thread-safe dgn lock (GR+PCS refresh bersamaan).
# (2) Export Rekap Selisih IN: dialog opsi kolom hasil audit (Hasil Audit /
#     Saldo / Catatan Audit — bisa ditambahkan atau tidak, permintaan user).
# (3) Rincian PO disederhanakan: baris TEAL = info PO lengkap sekali, baris
#     putih = item saja; kolom Tgl/Jam Pembuatan tersembunyi default.
# (4) STYLE WASTE: funnel header MERAH saat terfilter; tabel diperbesar
#     (font 10, rowheight 30); ⤢ Perbesar Tabel + ⛶ Layar Penuh semua tab.
# (5) CRASH FIX laten CPython 3.12 + Tk: GC shield saat thread worker hidup.
# Riwayat: v3.8.0 — selisih IN 1-31; pivot -31..31 (kolom 25•-31• lengkap);
# sheet PIVOT + CF; export selisih per resto; impor TL dihapus. v3.7.0 —
# ENGINE TURBO (output identik, 4× lebih cepat) + fix 9 bug index display.
# v3.6.0 — fix tombol filter; hide/unhide kolom; audit dari data app.
# v3.5.0 — LightMode dihapus; header filter semua kolom; KATEGORI.
# v3.4.0 — lebar kolom adjustable; SO bulan lalu; tab Rekap Selisih IN.
WINDOW_W, WINDOW_H = 1280, 760
# v3.9.48 — dipecah jadi angka utk KOMPENSASI GEOMETRI DPI (nilai string
# tak berubah — pipeline lama tetap "1280x760" di proses DPI-unaware):
# Windows + DpiAware → jendela = WINDOW_W/H × (fpixels/96) supaya
# ukuran FISIK sama dgn jendela lama yang di-bitmap-stretch (tapi TAJAM).
WINDOW_SIZE = f"{WINDOW_W}x{WINDOW_H}"
# FIX (audit 2-a QA visual): tinggi minimum 640 → 700 — di bawah ~695
# h-scrollbar tabel tertabrak tepi bawah (tidak bisa scroll horizontal).
WINDOW_MIN = (1020, 700)


# v3.9.55 — F8: persistensi STATE JENDELA (settings.json — pola
# acr_threshold deviasi_view: read-modify-write atomik; kegagalan I/O
# senyap). Disimpan saat jendela ditutup (jalur WM_DELETE_WINDOW asli —
# bukan root.destroy() langsung milik test); dipulihkan saat startup:
# pertama kali (tanpa state) → MAXIMIZED (auto-fit layar).
# v3.9.65 — ZOOM UI ikut dipersist (key 'ui_zoom' dalam window_state;
# pola sama — read-modify-write atomik): level zoom terakhir user
# dipulihkan saat buka; tanpa state → UI_ZOOM_DEFAULT (zoom-out).
_SETTINGS_PATH = _app_base_dir() / "settings.json"


def _load_window_state():
    """{w, h, maximized, ui_zoom} tersimpan; None bila tak ada/korup
    (first open). ui_zoom = float 0.5–2.0 (None bila tak ada/rusak)."""
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        st = data.get("window_state")
        if (isinstance(st, dict) and isinstance(st.get("w"), int)
                and isinstance(st.get("h"), int)
                and st["w"] >= WINDOW_MIN[0] and st["h"] >= WINDOW_MIN[1]):
            # v3.9.65 — zoom tersimpan (validasi rentang; float/int)
            _z = st.get("ui_zoom")
            if isinstance(_z, bool) or not isinstance(
                    _z, (int, float)):
                _z = None
            else:
                _z = float(_z)
                if not (UI_ZOOM_MIN <= _z <= UI_ZOOM_MAX):
                    _z = None
            return {"w": st["w"], "h": st["h"],
                    "maximized": bool(st.get("maximized")),
                    "ui_zoom": _z}
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def _save_window_state(w: int, h: int, maximized: bool,
                       ui_zoom: float | None = None) -> None:
    """Simpan state jendela (read-modify-write atomik; senyap gagal).
    v3.9.65 — ui_zoom ikut tersimpan bila diberikan (app asli selalu
    mengirim self.ui_zoom saat close); tanpa argumen = tanpa key
    (pemanggil lama tetap bekerja; buka berikutnya pakai default)."""
    old = {}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            old = loaded
    except (OSError, ValueError, TypeError):
        old = {}
    try:
        _st = {"w": int(w), "h": int(h), "maximized": bool(maximized)}
        # v3.9.65 — zoom terakhir user dipulihkan saat buka (default
        # zoom-out bila tak tersimpan)
        if ui_zoom is not None:
            _st["ui_zoom"] = round(float(ui_zoom), 2)
        old["window_state"] = _st
        tmp = _SETTINGS_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _SETTINGS_PATH)
    except (OSError, ValueError, TypeError):
        return


# v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win #1 roadmap Wave 1,
# pola Snipe-IT): kombinasi filter terakhir PER TAB disimpan saat
# jendela ditutup (settings.json key 'filter_state') & dipulihkan
# SEKALI setelah load_data run pipeline PERTAMA sesi berikutnya.
# load_data me-reset filter (kontrak v3.9.33) — restore menyusul
# SETELAHNYA; run pipeline BERIKUTNYA di sesi yang sama tetap reset
# (perilaku lama utuh — restore tidak pernah menimpa kerja user).
# View-key stabil → nama atribut app (pemetaan tunggal, tak pernah
# berganti nama tab/emoji).
_FILTER_VIEW_KEYS = (
    ("pivot", "pivot_view"),
    ("deviasi_gr", "deviasi_gr_view"),
    ("deviasi_pcs", "deviasi_pcs_view"),
    ("in_selisih", "in_selisih_view"),
    ("komparasi", "komparasi_view"),
    ("laporan", "laporan_view"),
    ("nominal", "nominal_view"),
    ("nominal_resto", "nominal_resto_view"),
    ("followup", "followup_view"),
    ("rincian_po", "rincian_view"),
)


# v3.9.68 — buffer warning load settings.json (audit eksternal T2):
# _load_filter_state dipanggil SEBELUM StreamToQueue terpasang — print
# langsung akan lenyap sebelum console log hidup. App mem-flush buffer
# ini ke log tab 🚀 Proses begitu redirect aktif (lihat __init__).
_FILTER_LOAD_WARNINGS: list = []


# v3.9.69 — P1.2 (audit eksternal ke-2): pola peringatan yang diterbitkan
# MODUL PIPELINE (src/pipeline/*.py + src/main.py) — kini ikut menaikkan
# status akhir run menjadi "SELESAI DENGAN PERINGATAN" (dulu hanya
# "[WARNING] Skip file" yang dihitung FIX D-04; peringatan skema format
# Accurate v3.9.67 — "[fn_2205] WARNING: kolom VALUE …", salah-ikat
# fallback fn_9901, duplikat combine_folder — hanya jatuh di log, status
# tetap HIJAU padahal data sumber berpotensi lenyap/nyasar).
# Peringatan UI (buka-folder / followup / backup config) SENGAJA tidak
# termasuk — bukan jejak run pipeline. "[WARNING] Skip file" juga
# SENGAJA dikecualikan di sini (sudah dihitung _skipped_files — hitung
# ulang akan menggandakan angka di status).
# KONTRAK TES: §82b memindai SEMUA literal print WARNING di modul
# pipeline dan gagal bila ada format baru yang tak tertangkap pola ini.
_PIPELINE_WARN_RE = re.compile(
    r"\[WARNING\] (?:combine_folder|fn_rekap_mentah|File harga"
    r"|Harga 41\.09|4217)"
    r"|\[(?:fn_\w+|Append1)\][^\n]*?WARNING"
)


def _load_filter_state():
    """v3.9.66 — baca key 'filter_state' settings.json →
    {view_key: dict} | None (tak ada/korup → None).
    Validasi: hanya dict-of-dict yang diterima (entry korup dibuang —
    view lain tetap dipulihkan).
    v3.9.68 — kegagalan kini DI-LOG (audit eksternal T2: dulu korupsi
    file / entry rusak lenyap SENYAP — user tak pernah tahu
    preferensinya tidak dipulihkan; warning di-buffer ke
    _FILTER_LOAD_WARNINGS karena fungsi ini berjalan PRA-redirect)."""
    global _FILTER_LOAD_WARNINGS
    _FILTER_LOAD_WARNINGS = []
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError) as _exc:
        _FILTER_LOAD_WARNINGS.append(
            f"[PERINGATAN] Filter persist: gagal membaca "
            f"{_SETTINGS_PATH.name} ({_exc!r}) — kombinasi filter "
            "tersimpan TIDAK dipulihkan sesi ini.")
        return None
    if not isinstance(data, dict):
        _FILTER_LOAD_WARNINGS.append(
            "[PERINGATAN] Filter persist: settings.json korup "
            "(bukan objek) — kombinasi filter tersimpan TIDAK "
            "dipulihkan sesi ini.")
        return None
    st = data.get("filter_state")
    if st is None:
        return None
    if not isinstance(st, dict):
        _FILTER_LOAD_WARNINGS.append(
            "[PERINGATAN] Filter persist: key 'filter_state' korup "
            "(bukan dict) — kombinasi filter tersimpan TIDAK "
            "dipulihkan sesi ini.")
        return None
    dropped = [str(k) for k, v in st.items()
               if not (isinstance(v, dict) and v)]
    if dropped:
        _FILTER_LOAD_WARNINGS.append(
            "[PERINGATAN] Filter persist: entry korup dibuang — "
            + ", ".join(dropped) + ".")
    out = {str(k): v for k, v in st.items()
           if isinstance(v, dict) and v}
    return out or None


def _save_filter_state(state: dict) -> None:
    """v3.9.66 — simpan {view_key: dict} ke key 'filter_state'
    (read-modify-write atomik — pola _save_window_state; window_state
    & kunci lain tak tersentuh).
    v3.9.68 — kegagalan kini DI-LOG ke console (audit eksternal T2:
    dulu senyap total — user tidak pernah tahu preferensinya gagal
    tersimpan; dipanggil saat jendela ditutup → log tetap terbaca
    di sesi berikutnya & smoke test)."""
    old = {}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            old = loaded
    except (OSError, ValueError, TypeError):
        old = {}
    try:
        old["filter_state"] = (state if isinstance(state, dict) else {})
        tmp = _SETTINGS_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _SETTINGS_PATH)
    except (OSError, ValueError, TypeError) as _exc:
        print("[PERINGATAN] Filter persist: gagal MENYIMPAN kombinasi "
              f"filter ke {_SETTINGS_PATH.name} ({_exc!r}) — sesi "
              "berikutnya memakai kombinasi tersimpan LAMA.")


# v3.9.48 — ZOOM UI runtime (CTRL + Scroll) — rentang & langkah.
# 0.5–2.0 dipilih supaya teks tetap terbaca di kedua ujung (font 8pt
# di 50% ≈ 4pt = lantai scale_pt 4).
# v3.9.65 — DEFAULT 0.8 + PERSIST: user: "bisa gak waktu aku buka udah
# ke zoom out" — app kini TERBUKA dalam keadaan zoom-out 80% (konten
# lebih banyak muat; langkah roda tetap 0.1 → 90%/100% rapi), dan level
# zoom CTRL+roda terakhir DISIMPAN ke settings.json (window_state.
# ui_zoom) → buka berikutnya memulai persis seperti preferensi user.
# Dulu: selalu 100% tiap restart (preferensi sesi — hilang saat tutup).
UI_ZOOM_MIN = 0.5
UI_ZOOM_MAX = 2.0
UI_ZOOM_STEP = 0.1
UI_ZOOM_DEFAULT = 0.8

# Path config.json — v3.9.62 frozen-aware (mode dev: root proyek;
# mode PyInstaller onedir: folder .exe — build_exe.py menyalin config
# .json ke samping exe supaya tetap bisa diedit user)
CONFIG_PATH = _app_base_dir() / "config.json"

# --- Freeze-fix konstanta (dipertahankan dari v2.1.1) -----------------------
MAX_CHUNKS_PER_POLL = 200       # max chunks diproses per poll cycle
MAX_CHARS_PER_POLL = 50000      # max karakter di-append per poll (cap buffer)
MAX_LOG_LINES = 3000            # max baris di Text widget (truncate ke 2000)
LOG_POLL_INTERVAL_MS = 100      # interval poll

# Warna status pipeline
_ST_SIAP = ("SIAP — menunggu perintah", C_GREEN)
_ST_RUN = ("Pipeline berjalan…", C_ORANGE)
_ST_DONE = ("SELESAI", C_GREEN)
_ST_STOP = ("DIHENTIKAN oleh user", C_AMBER)
_ST_ERR = ("ERROR — lihat log", C_RED)

# v3.9.59 — FIX 2a-05 (audit 2-a): label COMPACT baris tab notebook —
# dipakai bila estimasi lebar baris tab MELUAP (zoom > 100% / jendela
# sempit — tab paling kanan terpotong dan tak terjangkau mouse;
# ttk.Notebook tidak punya scroll/shrink tab). Emoji dibuang + label
# panjang dipendekkan; badge jumlah '☑ Follow Up (N)' tetap membawa
# (N) — lihat _compact_tab_label / _apply_tab_label_fit.
_TAB_COMPACT_LABELS = {
    "⚙️ Config": "Config",
    "🚀 Proses": "Proses",
    "📊 Pivot Table": "Pivot",
    "📦 Deviasi GR": "Deviasi GR",
    "🧩 Deviasi PCS": "Deviasi PCS",
    "📤 Rekap Selisih IN": "Selisih IN",
    "📋 Laporan Deviasi": "Laporan",
    "🧮 Nominal Deviasi": "Nominal",
    "☑ Follow Up": "Follow Up",
    "🛒 Rincian PO": "Rincian PO",
}
# Estimasi padding per tab: style TNotebook.Tab padding (12, 9) → 2×12
# + tabmargins (6, 8, 6, 0) → 2×6 ≈ 36 px per tab.
_TAB_PAD_EST = 36


def _is_file_locked_error(exc: BaseException) -> bool:
    """v3.9.59 — FIX 2f-09 (audit 2-f): deteksi error "file target
    terkunci / tak bisa ditulis" — tipikal file export masih dibuka di
    Excel saat export dijalankan ulang. Dipakai utk memberi user pesan
    Indonesia yang actionable (bukan exception mentah English)."""
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        # winerror 32 = sharing violation, 5 = access denied (Windows);
        # errno 13 = EACCES, 26 = ETXTBSY (POSIX).
        return (getattr(exc, "winerror", None) in (5, 32)
                or getattr(exc, "errno", None) in (13, 26))
    return False


def _open_folder_in_file_manager(path: str) -> bool:
    """v3.9.59 — FIX 2f-09 (audit 2-f): buka folder di file manager
    platform. Windows: os.startfile (API Windows — dicek hasattr dulu);
    macOS: open; lainnya: xdg-open. Gagal → [WARNING] ke log konsol,
    JANGAN raise dari jalur UI."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)          # Windows: Explorer
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError as e:
        print(f"[WARNING] Gagal membuka folder ({path}): {e}")
        return False


# --- Helper: redirect stdout ke Text widget via queue -----------------------
class StreamToQueue:
    """Object file-like yang menulis ke queue (thread-safe)."""

    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s: str):
        if s:
            self.q.put(s)

    def flush(self):
        pass


# --- Aplikasi utama ---------------------------------------------------------
class StockMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} — Python Edition")
        # v3.9.48 — (1) KOMPENSASI GEOMETRI DPI (fix "tidak HD" tanpa
        # regresi ukuran v3.9.46): default "DpiAware" kini TRUE = piksel
        # 1:1 TAJAM (Windows tak lagi bitmap-stretch = sumber kabur);
        # ukuran FISIK lama dipertahankan dgn mengalikan geometry dgn
        # skala DPI efektif (fpixels/96 — hanya Windows; non-Windows &
        # proses unaware = 1.0 → pipeline lama persis).
        # (2) ZOOM RUNTIME — state di bawah, mesin di _setup_ui_zoom.
        self._dpi_scale = self._read_dpi_scale()
        # v3.9.65 — baseline STATE 1.0 (font masih 100% di titik ini);
        # zoom startup (tersimpan / UI_ZOOM_DEFAULT 0.8) DITERAPKAN di
        # akhir __init__ via _apply_ui_zoom(target, resize_window=False)
        # — jangan set self.ui_zoom = target di sini (panggilan _apply
        # jadi no-op <1e-6 & font tak pernah ter-skala).
        self.ui_zoom = 1.0
        # v3.9.50 — [MINOR 3-a] ROUND-TRIP JENDELA: simpan ukuran BASE
        # (= ukuran efektif di zoom 100%) + ukuran EXPECTED (yang kita
        # minta sendiri via geometry — termasuk hasil clamp layar).
        # Binding <Configure> _on_root_configure membedakan resize MANUAL
        # user (→ base diperbarui = current/zoom) dari perubahan zoom
        # aplikasi sendiri (match expected → base tetap) → kembali ke
        # 100% dari zoom tinggi yang TER-CLAMP layar memulihkan ukuran
        # asli EKSAK (dulu: rasio dihitung dari ukuran ter-clamp →
        # 1100×800 → 200% → 100% = 1020×700 minsize 'collapse').
        self._zoom_base_wh = None
        self._zoom_expected_wh = None
        if self._dpi_scale != 1.0:
            _sw, _sh = (self.root.winfo_screenwidth(),
                        self.root.winfo_screenheight())
            _gw = min(round(WINDOW_W * self._dpi_scale), _sw)
            _gh = min(round(WINDOW_H * self._dpi_scale), _sh)
            self.root.geometry(f"{_gw}x{_gh}")
            self.root.minsize(
                min(round(WINDOW_MIN[0] * self._dpi_scale), _sw),
                min(round(WINDOW_MIN[1] * self._dpi_scale), _sh))
            self._zoom_base_wh = (_gw, _gh)
            self._zoom_expected_wh = (_gw, _gh)
            print(f"[DPI] Kompensasi ukuran jendela ×{self._dpi_scale:.2f} "
                  f"(piksel 1:1 tajam — ukuran fisik = tampilan lama)")
        else:
            self.root.geometry(WINDOW_SIZE)
            self.root.minsize(*WINDOW_MIN)
            self._zoom_base_wh = (WINDOW_W, WINDOW_H)
            self._zoom_expected_wh = (WINDOW_W, WINDOW_H)
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.configure(bg=C_BG)
        # v3.9.55 — F8 (user: "Waktu pertama kali buka program bisa gak
        # sudah diset ke auto fit biar gak adjust manual lagi?"):
        # (a) PERTAMA kali dibuka (tanpa state tersimpan) → jendela
        #     langsung MAXIMIZED (auto-fit layar — tak perlu adjust manual);
        # (b) sesi BERIKUTNYA → ukuran + status maximize TERAKHIR diingat
        #     (settings.json, pola acr_threshold): user resize sekali →
        #     terbuka persis seperti itu lagi. Simpan saat jendela ditutup
        #     (_on_close_window — jalur WM asli, bukan destroy() test).
        _saved_win = _load_window_state()
        # v3.9.66 — FILTER PERSISTEN: kombinasi filter terakhir per tab
        # dibaca SEKALI di startup; DIPULIHKAN setelah load_data run
        # pipeline PERTAMA (load_data me-reset filter — restore menyusul;
        # run berikutnya tetap reset — kontrak v3.9.33). File tak ada /
        # korup → None (sesi baru bersih, perilaku lama).
        self._filter_restore_state = _load_filter_state()
        # v3.9.65 — ZOOM STARTUP (user: "bisa gak waktu aku buka udah ke
        # zoom out"): target zoom = yang TERPERSIST di settings.json
        # (window_state.ui_zoom — level CTRL+roda terakhir user), atau
        # UI_ZOOM_DEFAULT (0.8 = zoom-out) bila belum ada. Diterapkan
        # SETELAH seluruh UI terbangun (font/rowheight/kolom live —
        # resize_window=False: ukuran jendela dikuasai restore F8 di
        # atas, zoom startup hanya mengecilkan KONTEN → lebih banyak
        # baris/kolom terlihat sejak buka).
        _saved_zoom = (_saved_win or {}).get("ui_zoom")
        self._startup_ui_zoom = (float(_saved_zoom)
                                 if _saved_zoom is not None
                                 else UI_ZOOM_DEFAULT)
        if _saved_win is not None:
            _sw = int(self.root.winfo_screenwidth())
            _sh = int(self.root.winfo_screenheight())
            _w = int(min(max(_saved_win.get("w", WINDOW_W),
                             WINDOW_MIN[0]), _sw))
            _h = int(min(max(_saved_win.get("h", WINDOW_H),
                             WINDOW_MIN[1]), _sh))
            with contextlib.suppress(tk.TclError):
                self.root.geometry(f"{_w}x{_h}")
            self._zoom_base_wh = (_w, _h)
            self._zoom_expected_wh = (_w, _h)
            if _saved_win.get("maximized"):
                self._maximize_root_window()
        else:
            self._maximize_root_window()

        # State
        self.log_queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.is_running = False
        # stop_event benar-benar memotong pipeline di checkpoint (dipertahankan)
        self.stop_event = threading.Event()
        self.append1_df = None
        self.rincian_po_df = None
        self.in_detail_df = None
        self.audit_result = None      # v3.5: {"df", "kpi", "desc"} audit rekonsiliasi
        self._log_line_count = 0
        self._run_start_time: float | None = None
        self._elapsed_after_id = None
        # FIX D-04: penghitung file Excel yang di-skip reader (terkunci/
        # hilang/rusak) — dihitung dari log pipeline, ditampilkan saat
        # pipeline selesai supaya data parsial tidak disembunyikan.
        self._skipped_files = 0
        # v3.9.69 — P1.2 (audit eksternal ke-2): penghitung peringatan
        # FORMAT/pipeline ([fn_XXXX] WARNING · combine_folder · 4217 ·
        # Append1 · Harga 41.09 — pola _PIPELINE_WARN_RE) — peringatan
        # skema tidak lagi berakhir di balik status hijau "SELESAI".
        self._schema_warnings = 0
        # v3.9.37 — waktu pipeline TERAKHIR selesai (time.time()) — acuan
        # "file sumber berubah" di dialog 🔄 Refresh File Sumber.
        self._last_run_finished_at: float | None = None

        # v3.2: store follow-up bersama (persist followup.json)
        self.followup_store = FollowUpStore()
        # v3.3: cache pivot Deviasi dibagi GR & PCS (compute 1×, bukan 2×)
        self._deviasi_pivot_cache = SharedPivotCache()
        # v3.9: TANGGAL H dibagi GR & PCS — input 1× (di tab GR), berlaku
        # di kedua tab (permintaan user: tidak double input)
        # v3.9.22: fallback awal 26 (user: "Tanggal harusnya tanggal 26
        # bukan dari tanggal 25"); setelah data dimuat DeviasiView mengatur
        # H DINAMIS ke tanggal SO nonzero terakhir (data user sampai 26).
        self._shared_h = SharedTanggalH(26)
        # v3.9.21: AMBANG ACR to BOM dibagi GR & PCS (user: "threshold
        # > 80% absolute dan aku bisa atur") — spinbox kedua tab sinkron;
        # nilai bertahan lintas sesi (settings.json), default 80.
        self._shared_acr = SharedACRThreshold(load_acr_threshold())

        # Style ttk (design system global)
        apply_theme(self.root)

        # Build UI
        self._build_toolbar()
        self._build_statusbar()
        # v3.9.48 — mesin zoom CTRL+Scroll (dipasang SETELAH statusbar —
        # badge zoom menulis ke statusbar kanan; lihat _setup_ui_zoom)
        self._setup_ui_zoom()
        self._build_notebook()

        # Redirect stdout/stderr ke queue
        sys.stdout = StreamToQueue(self.log_queue)
        sys.stderr = StreamToQueue(self.log_queue)
        # v3.9.68 — OBSERVABILITAS (audit eksternal T2): warning baca
        # settings.json dari _load_filter_state (dipanggil PRA-redirect)
        # di-flush ke console log begitu StreamToQueue aktif.
        for _w in _FILTER_LOAD_WARNINGS:
            print(_w)

        # Poll queue untuk update log (batched + throttled — freeze fix)
        self._poll_log_queue()

        # Load config awal ke tab Config
        self._load_config_to_form()

        # v3.9.65 — TERAPKAN ZOOM STARTUP (user: "bisa gak waktu aku buka
        # udah ke zoom out"): seluruh UI (toolbar/statusbar/notebook/semua
        # tree) sudah terbangun → efek berlapis _apply_ui_zoom bekerja
        # lengkap (named font + rowheight + auto-fit kolom + badge).
        # resize_window=False — ukuran/maximize jendela dikuasai restore
        # F8 di atas; zoom startup mengecilkan KONTEN saja. Target =
        # ui_zoom tersimpan (settings.json) atau UI_ZOOM_DEFAULT 0.8.
        # self.ui_zoom masih 1.0 (baseline state) → panggilan di bawah
        # selalu EFEKTIF (bukan no-op); bila target persis 1.0 → skip
        # (tidak ada yang perlu di-scale).
        _z_target = round(min(UI_ZOOM_MAX, max(UI_ZOOM_MIN,
                                               self._startup_ui_zoom)), 2)
        if abs(_z_target - 1.0) > 1e-6:
            self._apply_ui_zoom(_z_target, resize_window=False)

        # v3.9.33 — AUDIT FIX (48-c LOW): tombol X / WM_DELETE_WINDOW — dulu
        # TANPA handler (48-f: tidak ada WM_DELETE_WINDOW) → pipeline hidup
        # saat window ditutup → after() TclError ganda di thread daemon.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)

    # =====================================================================
    # SHELL: TOOLBAR + STATUSBAR + NOTEBOOK
    # =====================================================================
    def _build_toolbar(self):
        self.toolbar = Toolbar(self.root, f"📊 {APP_TITLE}", APP_VERSION)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # v3.9.37 — ↻ Refresh Sumber: dialog pilih file sumber yang mau
        # dibaca ulang (selektif — file lain dari cache bacaan).
        # v3.9.59 — FIX 2a-09/2f-13: glyph ↻ + SATU label kanonik per aksi
        # (tombol tab Proses dulu '🔄 Refresh File Sumber…' — dua label
        # untuk dialog yang sama membuat user ragu itu fitur berbeda).
        self.btn_refresh_tb = self.toolbar.add_action(
            "↻ Refresh Sumber", command=self._open_refresh_dialog)
        self.btn_export_tb = self.toolbar.add_action(
            "💾 Export Excel", command=self._export_excel, accent=True)
        # FIX A-02 (audit 2-a): set_enabled → tombol disabled TAMPAK dim
        # (abu) — bukan configure(state) yang meninggalkan warna teal.
        self.btn_export_tb.set_enabled(False)

    def _build_statusbar(self):
        self.statusbar = StatusBar(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar.set_right(f"v{APP_VERSION} · Python Edition")
        # v3.9.59 — FIX 2a-06 (audit 2-a): discoverability zoom — teks
        # status AWAL menyebut CTRL+roda SEKALI (hint '(CTRL+roda)' badge
        # kanan memang hanya tampil saat zoom ≠ 100% — kontrak test §58
        # dipertahankan; dulu user baru tahu fitur zoom ada SETELAH tak
        # sengaja menekan CTRL sambil scroll).
        self.statusbar.set_status(
            "SIAP — menunggu perintah · CTRL+roda = zoom tampilan", C_GREEN)

    # =====================================================================
    # v3.9.48 — ZOOM UI RUNTIME (CTRL + Scroll) — user: "bisa gak kalau
    # aku CTRL + Scroll mouse jadi zoom in dan zoom out?"
    # =====================================================================
    def _read_dpi_scale(self) -> float:
        """Skala DPI efektif utk KOMPENSASI GEOMETRI (Windows + DpiAware
        sukses): winfo_fpixels('1i')/96 — layar 125% → 1.25, 150% → 1.5.
        Proses DPI-unaware (\"DpiAware\": false) melihat 96 virtual → 1.0
        (geometry polos = pipeline lama persis). Non-Windows → 1.0 (X11/
        macOS tak bitmap-stretch; ukuran lama sudah benar di sana).
        Dibaca SEKALI di startup SETELAH main() memasang awareness+scaling
        DPI — jangan dibaca ulang setelah zoom (fpixels ikut tk scaling).
        """
        try:
            if sys.platform != "win32":
                return 1.0
            return max(1.0, round(self.root.winfo_fpixels("1i") / 96.0, 2))
        except tk.TclError:
            return 1.0

    def _setup_ui_zoom(self):
        """Pasang seluruh mesin zoom runtime:
        - handler roda-CTRL → registry theme (semua widget scrollable
          memanggil ctrl_wheel_dispatch via bind_ctrl_zoom — spesifisitas
          pattern Tk memangkas scroll ganda);
        - fallback bind_all utk area NON-scrollable (frame/label/kartu —
          tak ada binding roda lain yang bisa bentrok);
        - kelas Listbox (popdown Combobox — satu-satunya kelas scrollable
          tanpa factory choke-point);
        - badge persen zoom di status bar kanan (hint cara pakai)."""
        set_zoom_wheel_handler(self._on_zoom_wheel)
        for _seq in ("<Control-MouseWheel>", "<Control-Button-4>",
                     "<Control-Button-5>"):
            self.root.bind_all(_seq, self._on_zoom_wheel)
            self.root.bind_class("Listbox", _seq, ctrl_wheel_dispatch)
        self._update_zoom_badge()

    def _on_zoom_wheel(self, event):
        """CTRL + roda: arah atas = perbesar, bawah = perkecil.
        Windows/macOS: event.delta (±120 per notch, trackpad bisa kecil);
        X11: event.num 4 (naik) / 5 (turun).
        Selalu return \"break\" — mematikan binding kelas pada bindtag
        berikutnya supaya tabel/log TIDAK ikut bergulir saat zoom.

        FIX 6a-04: magnitudo delta kini DIHITUNG — akumulator delta
        pecahan (pola enable_smooth_wheel_list): kontribusi delta/120
        dijumlahkan, ``int(acc)`` langkah UI_ZOOM_STEP diterapkan, sisa
        dibawa ke event berikutnya; berbalik arah → sisa arah lama
        dibuang. Dulu hanya TANDA delta yang dipakai (±10% per EVENT):
        roda/trackpad resolusi tinggi mengirim delta < 120 per event
        (banyak event kecil per notch fisik) → 1 notch = +120% zoom
        (langsung clamp 200%), praktis tak terkendali di kelas device
        itu. X11 Button-4/5 tetap 1 langkah per event (perilaku lama)."""
        _d = getattr(event, "delta", 0) or 0
        if _d:
            acc = getattr(self, "_zoom_wheel_acc", 0.0)
            # FIX 6a-04: berbalik arah → buang sisa akumulator ARAH LAMA
            # (tanpa ini sisa arah lama 'memakan' notch pertama arah baru)
            if acc and ((_d > 0) != (acc > 0)):
                acc = 0.0
            acc += _d / 120.0
            steps = int(acc)          # potong menuju nol; sisa dibawa
            self._zoom_wheel_acc = acc - steps
            if steps:
                self._apply_ui_zoom(self.ui_zoom + steps * UI_ZOOM_STEP)
            return "break"
        _num = getattr(event, "num", 0) or 0
        if _num == 4:
            self._apply_ui_zoom(self.ui_zoom + UI_ZOOM_STEP)
        elif _num == 5:
            self._apply_ui_zoom(self.ui_zoom - UI_ZOOM_STEP)
        return "break"

    def _apply_ui_zoom(self, value: float,
                       resize_window: bool = True) -> bool:
        """Terapkan zoom UI (clamp 50%–200%, bulat 2 desimal). Return
        True bila zoom benar-benar berubah (nilai sama = no-op).

        Efek berlapis (urutan penting — style font membaca zoom aktif):
        (1) FONT NAMED: set_ui_scale + rescale_named_fonts — semua teks
            (ttk style, tk widget, tag tree, konsol log, popup TERBUKA)
            re-render HIDUP;
        (2) STYLE TABEL: apply_theme dipasang ULANG (idempoten) —
            rowheight = 30×zoom (font baris membesar; rowheight statis
            akan memotong teks) + style font ikut ter-refresh;
        (3) JENDELA: ukuran × rasio zoom (menghormati resize manual user;
            clamp batas layar + 400×300 minimum) + minsize proporsional;
        (4) CACHE RENDER: rowheight berubah → cache CellColorOverlay +
            batching insert virtual di-invalidasi (label sel warna tak
            tertinggal di posisi lama);
        (5) BADGE persen di status bar kanan.

        v3.9.65 — resize_window=False (STARTUP): terapkan FONT/ROWHEIGHT/
        KOLOM saja TANPA mengubah ukuran jendela — jendela dibuka persis
        seperti state tersimpan (maximized/float) & konten ter-zoom-out
        → lebih banyak baris terlihat (semantik 'sudah ke zoom out saat
        dibuka'); jendela baru ×rasio saat user CTRL+roda (jalur lama).
        Runtime CTRL+roda tetap resize_window=True (perilaku v3.9.48
        utuh)."""
        _new = round(min(UI_ZOOM_MAX, max(UI_ZOOM_MIN, value)), 2)
        _old = self.ui_zoom
        if abs(_new - _old) < 1e-6:
            return False
        self.ui_zoom = _new
        # (1) named font bersama — live ke semua pemakai
        set_ui_scale(_new)
        rescale_named_fonts()
        # (2) re-apply theme: rowheight + font style (idempoten)
        with contextlib.suppress(Exception):
            apply_theme(self.root)
        # (2b) v3.9.50 — [MAJOR 3-a] RE-FIT KOLOM SEMUA TABEL: font ter-
        # zoom + bounds auto_fit ter-skala → kolom mengikuti zoom (dulu
        # hanya font/rowheight/jendela — konten tabel terpotong di zoom
        # >±110% karena clamp max_width statis 340px).
        self._refit_all_tree_columns()
        # (3) jendela + minsize proporsional — v3.9.50: target = BASE×zoom
        # (bukan current×rasio) supaya round-trip lewat clamp layar pulih
        # eksak; resize manual terus ditrack ke base via _on_root_configure.
        # v3.9.65 — resize_window=False (startup) LEWATI geometry: ukuran
        # jendela dikuasai penuh oleh restore window_state (F8) — zoom
        # startup hanya mengecilkan KONTEN; base/expected tak disentuh.
        with contextlib.suppress(Exception):
            if resize_window and self._zoom_base_wh is not None:
                _bw, _bh = self._zoom_base_wh
                _sw, _sh = (self.root.winfo_screenwidth(),
                            self.root.winfo_screenheight())
                _tw = int(min(max(round(_bw * _new), 400), _sw))
                _th = int(min(max(round(_bh * _new), 300), _sh))
                self.root.geometry(f"{_tw}x{_th}")
                self._zoom_expected_wh = (_tw, _th)
            _ms = self._dpi_scale * _new
            # v3.9.50 — [MINOR 3-a] clamp minsize ke FRAKSI layar (85%):
            # dulu clamp 100% layar → di zoom 200% minsize = layar penuh
            # → user tak bisa mengecilkan jendela sama sekali.
            self.root.minsize(
                min(round(WINDOW_MIN[0] * _ms),
                    int(self.root.winfo_screenwidth() * 0.85)),
                min(round(WINDOW_MIN[1] * _ms),
                    int(self.root.winfo_screenheight() * 0.85)))
        # (4) cache render overlay/tree (rowheight berubah)
        self._invalidate_tree_render_caches()
        # (5) badge
        self._update_zoom_badge()
        # (5b) v3.9.59 — FIX 2a-05: font baris tab ikut membesar saat zoom
        # → cek label compact (debounce — geometry baru belum diterapkan
        # saat baris ini berjalan, <Configure> akan menyusul).
        self._schedule_tab_label_fit()
        return True

    def _on_root_configure(self, event):
        """v3.9.50 — [MINOR 3-a] lacak ukuran jendela utk base zoom.

        <Configure> TERIKAT di root menerima event CHILD widget JUGA
        (diprobe: event noteboo/toolbar ber-ukuran inset sampai ke
        binding root — ukuran child akan MENGKORUPSI base). Filter:
        hanya event milik ROOT sendiri (event.widget == root — diprobe
        terpisah: atribut .widget child ≠ root) yang diproses; event
        root yang match _zoom_expected_wh (ukuran yang KITA minta via
        geometry — termasuk hasil clamp layar oleh zoom aplikasi) →
        BUKAN resize user: base tak disentuh (round-trip eksak); beda →
        resize MANUAL user (WM) → base diperbarui = (current/zoom).
        Abaikan ukuran pra-map (< 400×300 — artefak inisialisasi Tk)."""
        with contextlib.suppress(Exception):
            if str(getattr(event, "widget", "")) != str(self.root):
                return
            _w, _h = int(getattr(event, "width", 0) or 0), \
                int(getattr(event, "height", 0) or 0)
            if _w < 400 or _h < 300:
                return
            if (_w, _h) == self._zoom_expected_wh:
                return
            _z = self.ui_zoom or UI_ZOOM_DEFAULT
            self._zoom_base_wh = (max(400, round(_w / _z)),
                                  max(300, round(_h / _z)))
            self._zoom_expected_wh = (_w, _h)

    def _refit_all_tree_columns(self):
        """v3.9.50 — [MAJOR 3-a] auto-fit ULANG semua tree setelah zoom.

        Walk recursive SEMUA widget (root + notebook semua tab + popup
        Toplevel + clone ⛶): tiap ttk.Treeview di-auto_fit_columns dgn
        bounds ter-skala ui_scale + pengukuran font(10) ter-zoom —
        deterministik dari konten (tanpa drift pembulatan rasio ×multi-
        langkah), idempoten, dan konsisten dgn apa yang auto-fit render
        data berikutnya akan hasilkan. Tree kosong hanya mengukur heading
        (murah). Popup yang sedang TERBUKA ikut (janji 'zoom seluruh UI').
        v3.9.51 — strip warna header kolom In (HeadingTintOverlay) ikut
        di-reposisi (lebar kolom berubah pasca auto-fit).
        v3.9.55 — merge-vertikal Rank kini NATIVE (tanpa overlay) → tidak
        ada reposisi overlay rank lagi (RankMergeOverlay dihapus)."""
        def _walk(_w):
            try:
                _kids = _w.winfo_children()
            except tk.TclError:
                return
            for _ch in _kids:
                _walk(_ch)
            if isinstance(_w, ttk.Treeview):
                with contextlib.suppress(Exception):
                    auto_fit_columns(_w)
                # v3.9.51 — reposisi strip header kolom In (bila ada)
                _tint = getattr(_w, "_heading_tint", None)
                if _tint is not None and getattr(_tint, "_alive", False):
                    with contextlib.suppress(Exception):
                        _tint.refresh()
                # v3.9.55 — merge-vertikal Rank kini NATIVE (nilai head +
                # band — RankMergeOverlay dihapus) → tak ada overlay yang
                # perlu di-reposisi pasca auto-fit.
        with contextlib.suppress(Exception):
            _walk(self.root)

    def _invalidate_tree_render_caches(self):
        """Invalidasi cache render SEMUA tree (termasuk popup/clone ⤢):
        CellColorOverlay (v3.9.40) menyimpan (style, rowheight, font) di
        cache sampai <Configure> — zoom di batas layar bisa TIDAK mengubah
        ukuran widget (clamp) → tanpa invalidasi eksplisit, label sel
        warna tertinggal di posisi rowheight lama & batching insert
        virtual salah hitung baris."""
        def _walk(_w):
            try:
                _kids = _w.winfo_children()
            except tk.TclError:
                return
            for _ch in _kids:
                _walk(_ch)
            _ov = getattr(_w, "_cell_color_overlay", None)
            if _ov is not None and getattr(_ov, "_alive", False):
                with contextlib.suppress(Exception):
                    _ov._invalidate_render_cache()
                    _ov._schedule()
        with contextlib.suppress(Exception):
            _walk(self.root)

    def _update_zoom_badge(self):
        """Badge zoom di status bar kanan: hint \"(CTRL+roda)\" tampil
        saat zoom ≠ 100% supaya fitur bisa ditemukan tanpa baca README;
        100% = teks versi polos (identik v3.9.47 — test lama utuh)."""
        with contextlib.suppress(Exception):
            if abs(self.ui_zoom - 1.0) < 1e-6:
                self.statusbar.set_right(f"v{APP_VERSION} · Python Edition")
            else:
                self.statusbar.set_right(
                    f"v{APP_VERSION} · Zoom "
                    f"{round(self.ui_zoom * 100)}% (CTRL+roda) · "
                    f"Python Edition")

    def _data_time_suffix(self) -> str:
        """v3.9.59 — FIX 2f-17 (audit 2-f): umur data terakhir untuk
        statusbar — ' · Data: dd-mm HH:MM' (kosong bila belum pernah
        ada data). Dulu waktu proses terakhir hanya hidup di dalam
        dialog 🔄 Refresh — user tak bisa menilai kesegaran tabel dari
        UI utama."""
        _ts = getattr(self, "_last_run_finished_at", None)
        if not _ts:
            return ""
        return " · Data: " + time.strftime("%d-%m %H:%M",
                                           time.localtime(_ts))

    def _focus_notebook_content(self):
        """v3.9.59 — FIX 2a-11 (audit 2-a): pindahkan fokus keyboard ke
        konten tab AKTIF setelah pergantian tab programatik (pipeline
        selesai → tab Pivot). Dipanggil via after_idle supaya tidak
        mencuri fokus saat user sedang mengetik (Entry/Text/Spinbox
        aktif → skip). Tanpa ini fokus menempel di root: pengguna
        keyboard (Tab/panah/Home) harus klik dulu sebelum bisa
        navigasi tabel."""
        with contextlib.suppress(Exception):
            _cur = self.root.focus_get()
            if isinstance(_cur, (tk.Entry, tk.Text, tk.Spinbox,
                                 ttk.Spinbox)):
                return   # user sedang mengetik — jangan ganggu
            self.notebook.focus_set()   # minimal: Ctrl+Tab traversal hidup
            _sel = self.notebook.select()
            if not _sel:
                return
            _tab = self.root.nametowidget(_sel)
            _stack = list(_tab.winfo_children())
            while _stack:   # BFS → tree pertama tab aktif = fokus tabel
                _w = _stack.pop(0)
                if isinstance(_w, ttk.Treeview):
                    _w.focus_set()
                    return
                _stack.extend(_w.winfo_children())

    def _go_to_proses_tab(self):
        """v3.9.59 — FIX 2a-11 (audit 2-a): pindah ke tab 🚀 Proses secara
        programatik (tombol 'ke tab Proses' di view kosong +
        _start_pipeline) lalu pindahkan fokus keyboard ke konten tab
        via after_idle (lihat _focus_notebook_content). Dulu fokus
        menempel di tombol pemicu/root — pengguna keyboard harus KLIK
        dulu setelah pindah tab sebelum Tab/panah bekerja."""
        self.notebook.select(self.tab_proses)
        self.root.after_idle(self._focus_notebook_content)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=(2, 6))

        self.tab_config = tk.Frame(self.notebook, bg=C_BG)
        self.tab_proses = tk.Frame(self.notebook, bg=C_BG)
        self.tab_pivot = tk.Frame(self.notebook, bg=C_BG)
        self.tab_deviasi_gr = tk.Frame(self.notebook, bg=C_BG)
        self.tab_deviasi_pcs = tk.Frame(self.notebook, bg=C_BG)
        self.tab_in_selisih = tk.Frame(self.notebook, bg=C_BG)
        self.tab_laporan = tk.Frame(self.notebook, bg=C_BG)
        # v3.9.34 — tab 🧮 Nominal Deviasi (Σ nominal per resto)
        self.tab_nominal_resto = tk.Frame(self.notebook, bg=C_BG)
        self.tab_followup = tk.Frame(self.notebook, bg=C_BG)
        self.tab_rincian = tk.Frame(self.notebook, bg=C_BG)

        self.notebook.add(self.tab_config, text="⚙️ Config")
        self.notebook.add(self.tab_proses, text="🚀 Proses")
        self.notebook.add(self.tab_pivot, text="📊 Pivot Table")
        self.notebook.add(self.tab_deviasi_gr, text="📦 Deviasi GR")
        self.notebook.add(self.tab_deviasi_pcs, text="🧩 Deviasi PCS")
        self.notebook.add(self.tab_in_selisih, text="📤 Rekap Selisih IN")
        self.notebook.add(self.tab_laporan, text="📋 Laporan Deviasi")
        # v3.9.34 — tab 🧮 Nominal Deviasi: Σ harga×qty deviasi per resto
        self.notebook.add(self.tab_nominal_resto,
                          text="🧮 Nominal Deviasi")
        self.notebook.add(self.tab_followup, text="☑ Follow Up")
        self.notebook.add(self.tab_rincian, text="🛒 Rincian PO")
        # v3.9.59 — FIX 2a-05: register label FULL per tab + pantau
        # lebar baris tab (fallback label compact saat meluap — badge
        # '☑ Follow Up (N)' ikut lewat _set_tab_label supaya konsisten).
        self._tab_full_labels = {
            str(self.tab_config): "⚙️ Config",
            str(self.tab_proses): "🚀 Proses",
            str(self.tab_pivot): "📊 Pivot Table",
            str(self.tab_deviasi_gr): "📦 Deviasi GR",
            str(self.tab_deviasi_pcs): "🧩 Deviasi PCS",
            str(self.tab_in_selisih): "📤 Rekap Selisih IN",
            str(self.tab_laporan): "📋 Laporan Deviasi",
            str(self.tab_nominal_resto): "🧮 Nominal Deviasi",
            str(self.tab_followup): "☑ Follow Up",
            str(self.tab_rincian): "🛒 Rincian PO",
        }
        self._tab_compact_mode = False
        self._tab_fit_after_id = None
        self.notebook.bind("<Configure>", self._on_notebook_configure)
        # v3.2: lazy refresh — tab data hanya compute saat TERLIHAT
        # (setelah pipeline selesai hanya tab aktif yang refresh; tab lain
        # menunggu dipilih → app terasa jauh lebih ringan)
        self.notebook.bind("<<NotebookTabChanged>>",
                           self._on_tab_changed)
        # FIX A-04 (audit 2-a): aktifkan navigasi keyboard antar-tab
        # (Ctrl+Tab / Ctrl+Shift+Tab) — ttk notebook punya mekanisme ini
        # tapi harus di-enable eksplisit dari aplikasi.
        self.notebook.enable_traversal()
        # v3.9.68 — TOOLTIP GRUP ALUR KERJA (audit eksternal T5): hover
        # baris tab → label PENUH + nama kelompok alur kerja (menambakan
        # label compact v3.9.59 saat jendela sempit). Tanpa sidebar /
        # redesign — urutan tab memang sudah mengikuti kelompok sejak
        # awal: Operasional → Pemeriksaan & Rekonsiliasi → Analisis →
        # Tindak Lanjut (rekomendasi pengelompokan audit terpenuhi
        # oleh struktur yang ada; yang kurang hanyalah PENAMAAN yang
        # jelas — tooltip menutup itu tanpa merisikokan layout).
        self._tab_groups = {
            str(self.tab_config): "Operasional",
            str(self.tab_proses): "Operasional",
            str(self.tab_pivot): "Operasional",
            str(self.tab_deviasi_gr): "Pemeriksaan & Rekonsiliasi",
            str(self.tab_deviasi_pcs): "Pemeriksaan & Rekonsiliasi",
            str(self.tab_in_selisih): "Pemeriksaan & Rekonsiliasi",
            str(self.tab_laporan): "Analisis",
            str(self.tab_nominal_resto): "Analisis",
            str(self.tab_followup): "Tindak Lanjut",
            str(self.tab_rincian): "Tindak Lanjut",
        }
        self._tab_tooltips = NotebookTabTooltips(
            self.notebook, full_labels=self._tab_full_labels,
            groups=self._tab_groups)
        self._update_followup_badge()

        self._build_config_tab()
        self._build_proses_tab()
        self._build_pivot_tab()
        self._build_deviasi_gr_tab()
        self._build_deviasi_pcs_tab()
        self._build_in_selisih_tab()
        self._build_laporan_tab()
        self._build_nominal_resto_tab()   # v3.9.34 — tab 🧮
        self._build_followup_tab()
        self._build_rincian_tab()
        self._build_tab_views()  # FIX A-11: routing tab berbasis widget
        # v3.9.61 — ROUTER RODA app-wide (user: "tab rekap selisih in aku
        # masih tidak bisa scroll pakai wheele mouse"): binding Toplevel
        # menggulir scrollable DI BAWAH POINTER (baris leaderboard = Label
        # tanpa binding sendiri — dulu mati) + fallback tabel utama tab
        # AKTIF utk area krom (KPI/Filter/footer). Detail: widgets.
        # install_wheel_router.
        install_wheel_router(self.root,
                             get_primary_scrollable=self._primary_scrollable)
        # v3.9.62 — CARI DI TABEL (Ctrl+F — find-window ala tksheet,
        # in-house): binding di TOPLEVEL (bindtag Toplevel ada di rantai
        # SEMUA anak jendela — pola router roda v3.9.61) menjangkar target
        # = tabel utama tab AKTIF (peta _primary_scrollable yang sama);
        # popup TreeFindPopup non-modal + highlight + Enter/Shift-Enter.
        for _seq in ("<Control-f>", "<Control-F>"):
            self.root.bind(_seq, self._on_find_shortcut)

    def _on_find_shortcut(self, _event=None):
        """v3.9.62 — Ctrl+F: buka/fokus popup Cari di tabel tab aktif
        (tab Config/Proses tanpa tabel data → no-op senyap)."""
        tree = self._primary_scrollable()
        if tree is not None:
            open_tree_find(tree)

    def _on_tab_changed(self, _event=None):
        """Tab baru dipilih → pastikan view-nya sudah di-refresh.

        FIX A-11 (audit 2-a): routing berbasis WIDGET FRAME (bukan index
        angka) — v3.9.9 terpaksa reindex manual saat Pareto disisipkan;
        mapping kini dibangun sekali di _build_tab_views() sehingga tab
        baru cukup menambah satu entry, tidak menggeser angka ajaib.
        """
        try:
            sel = self.notebook.select()  # string nama widget Tk
        except Exception:
            return
        views = getattr(self, "_tab_views", None)
        if not views:
            return
        view = views.get(sel)
        if view is self._laporan_tab_entry:
            # v3.9.4: refresh pane SESUAI MODE aktif di tab Laporan
            # v3.9.32: mode 2 = 💰 Nominal (H)
            _active = (getattr(self, "laporan_segment", None).active
                       if getattr(self, "laporan_segment", None) is not None
                       else 0)
            view = (self.komparasi_view if _active == 0
                    else (self.nominal_view if _active == 2
                          else self.laporan_view))
        if view is not None and hasattr(view, "ensure_refreshed"):
            view.ensure_refreshed()

    def _build_tab_views(self):
        """FIX A-11: peta nama-widget tab → view yang di-lazy-refresh.
        Follow Up sengaja tanpa entry (reaktif via store listener).
        """
        self._laporan_tab_entry = object()  # marker dispatch khusus
        self._tab_views = {
            str(self.tab_pivot): self.pivot_view,
            str(self.tab_deviasi_gr): self.deviasi_gr_view,
            str(self.tab_deviasi_pcs): self.deviasi_pcs_view,
            str(self.tab_in_selisih): self.in_selisih_view,
            str(self.tab_laporan): self._laporan_tab_entry,
            # v3.9.34 — dispatch _on_tab_changed → ensure_refreshed
            str(self.tab_nominal_resto): self.nominal_resto_view,
            str(self.tab_rincian): self.rincian_view,
        }

    def _primary_scrollable(self):
        """v3.9.61 — tabel utama TAB AKTIF (fallback router roda —
        install_wheel_router): dipakai saat roda berputar di area krom
        non-scrollable (kartu KPI/Filter/footer/legend) supaya konten
        tab tetap bergulir (perilaku aplikasi modern). Tab 📋 Laporan
        punya 3 mode pane — pilih view sesuai SegmentBar aktif. Tab
        ⚙️ Config/🚀 Proses tanpa tabel data → None (roda netral)."""
        views = getattr(self, "_tab_views", None)
        if not views:
            return None
        try:
            sel = self.notebook.select()  # string nama widget Tk
        except tk.TclError:   # teardown / notebook belum siap
            return None
        if not sel:
            return None
        view = views.get(sel)
        if view is self._laporan_tab_entry:
            _active = (getattr(self, "laporan_segment", None).active
                       if getattr(self, "laporan_segment", None) is not None
                       else 0)
            view = (self.komparasi_view if _active == 0
                    else (self.nominal_view if _active == 2
                          else self.laporan_view))
        elif view is None and sel == str(self.tab_followup):
            # Follow Up tak ada di _tab_views (reaktif store) — tapi
            # tetap punya tabel utk fallback roda.
            view = self.followup_view
        # v3.9.63 — view dgn ANAK TAB (tab 🧮 Nominal Deviasi —
        # sub-notebook 'Per Resto'/'Tanpa Harga'): primary_tree()
        # memilih tree anak tab AKTIF (fallback roda di krom anak tab
        # menggulir tabel yang TERLIHAT, bukan tabel tersembunyi).
        _pt63 = getattr(view, "primary_tree", None)
        if callable(_pt63):
            tree = _pt63() or getattr(view, "tree", None)
        else:
            tree = getattr(view, "tree", None)
        try:
            if tree is not None and not tree.winfo_exists():
                return None
        except tk.TclError:
            return None
        return tree

    def _update_followup_badge(self):
        """Badge jumlah baris di judul tab Follow Up."""
        with contextlib.suppress(Exception):
            n = len(self.followup_store)
            # FIX H-1 (audit 2-a hipotesis — TERKONFIRMASI): label tab
            # TANPA spasi ganda + padding ramping → semua tab muat di lebar
            # minimum 1020px (dulu ±1280px — tab paling kanan terpotong /
            # tak terjangkau; kritis juga di Windows 125% scaling).
            # v3.9.59 — FIX 2a-05: lewat _set_tab_label supaya mode label
            # compact (baris tab sempit) tetap konsisten dgn badge (N).
            self._set_tab_label(
                self.tab_followup,
                f"☑ Follow Up{' (' + str(n) + ')' if n else ''}")

    # =====================================================================
    # v3.9.59 — FIX 2a-05 (audit 2-a): BARIS TAB ADAPTIF (label compact)
    # =====================================================================
    def _on_notebook_configure(self, _event=None):
        """<Configure> notebook (resize jendela / zoom) → cek muat
        atau tidaknya baris tab (debounce — lihat
        _schedule_tab_label_fit)."""
        self._schedule_tab_label_fit()

    def _schedule_tab_label_fit(self):
        """Debounce 120 ms: resize/zoom memicu SERANGAN event
        <Configure> (tiap langkah geometry) — hanya cek TERAKHIR yang
        dieksekusi, dan cek itu sendiri idempoten (hanya perubahan mode
        yang menulis ulang label tab)."""
        _prev = getattr(self, "_tab_fit_after_id", None)
        if _prev is not None:
            with contextlib.suppress(Exception):
                self.root.after_cancel(_prev)
        self._tab_fit_after_id = self.root.after(
            120, self._apply_tab_label_fit)

    def _compact_tab_label(self, text: str) -> str:
        """Label compact dari label full: buang emoji + perpendek via
        _TAB_COMPACT_LABELS. Suffix badge jumlah ' (N)' (tab Follow Up)
        dipertahankan — informasi penting."""
        for _full, _short in _TAB_COMPACT_LABELS.items():
            if text.startswith(_full):
                return _short + text[len(_full):]
        return text

    def _set_tab_label(self, tab, full_label: str):
        """Simpan label FULL + terapkan ke tab sesuai mode compact
        (2a-05) — dipakai _update_followup_badge supaya badge (N) tidak
        menimpa mode label saat baris tab sempit."""
        self._tab_full_labels[str(tab)] = full_label
        with contextlib.suppress(tk.TclError):
            self.notebook.tab(
                tab, text=(self._compact_tab_label(full_label)
                           if getattr(self, "_tab_compact_mode", False)
                           else full_label))
        self._schedule_tab_label_fit()

    def _apply_tab_label_fit(self):
        """Terapkan label tab FULL/COMPACT sesuai ruang tersedia.

        Estimasi lebar baris = Σ font.measure(label) + padding per tab
        (font = named font style TNotebook.Tab pilihan-selected — bold,
        worst case; ikut ter-rescale saat zoom). Engage compact HANYA
        bila estimasi FULL meluap DAN zoom > 100% — di 100% label
        produksi memang muat (padding ramping fix H-1, terukur ±912px <
        lebar minimum 1020px; estimasi Xvfb lebih lebar karena font
        substitusi). Kembali ke label FULL begitu muat lagi."""
        self._tab_fit_after_id = None
        nb = getattr(self, "notebook", None)
        if nb is None:
            return
        with contextlib.suppress(Exception):
            _avail = int(nb.winfo_width())
            if _avail < 60:   # belum ter-map — tunggu <Configure> berikut
                return
            _f = font(10, "bold")   # named font style tab (selected)
            _full = [self._tab_full_labels.get(str(t), nb.tab(t, "text"))
                     for t in nb.tabs()]
            _est_full = sum(_f.measure(t) + _TAB_PAD_EST for t in _full)
            _est_compact = sum(
                _f.measure(self._compact_tab_label(t)) + _TAB_PAD_EST
                for t in _full)
            _want = (_est_full > _avail and self.ui_zoom > 1.0
                     and _est_compact < _est_full)
            if _want == getattr(self, "_tab_compact_mode", False):
                return   # idempoten — jangan tulis label tanpa perubahan
            self._tab_compact_mode = _want
            for _t in nb.tabs():
                _lbl = self._tab_full_labels.get(str(_t))
                if _lbl is None:
                    continue
                nb.tab(_t, text=(self._compact_tab_label(_lbl) if _want
                                 else _lbl))

    # =====================================================================
    # TAB: CONFIG
    # =====================================================================
    def _build_config_tab(self):
        tab = self.tab_config
        wrap = tk.Frame(tab, bg=C_BG)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Card: Lokasi Data ---
        card = tk.Frame(wrap, bg=C_CARD, highlightbackground="#e2e8f0",
                        highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=C_CARD)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(inner, text="Lokasi Data (RootPath)", bg=C_CARD,
                 fg=C_HEADER, font=font(12, "bold")).pack(anchor="w")

        form = tk.Frame(inner, bg=C_CARD)
        form.pack(fill="x")
        tk.Label(form, text="RootPath", bg=C_CARD, fg=C_HEADER,
                 font=font(9, "bold")).grid(row=0, column=0, sticky="nw", pady=6)
        self.rootpath_var = tk.StringVar()
        self.entry_rootpath = ttk.Entry(form, textvariable=self.rootpath_var)
        self.entry_rootpath.grid(row=0, column=1, sticky="ew", padx=(10, 8), pady=6)
        btn_browse = GhostButton(form, text="📂 Browse…", command=self._browse_folder)
        btn_browse.grid(row=0, column=2, pady=6)
        form.columnconfigure(1, weight=1)

        btn_row = tk.Frame(inner, bg=C_CARD)
        btn_row.pack(fill="x")
        AccentButton(btn_row, text="💾 Simpan Config",
                     command=self._save_config).pack(side="left")
        GhostButton(btn_row, text="↻ Reload Config",
                    command=self._load_config_to_form).pack(
            side="left", padx=(8, 0))

        # --- Card: Info Config (read-only) ---
        info_card = tk.Frame(wrap, bg=C_CARD, highlightbackground="#e2e8f0",
                             highlightthickness=1)
        info_card.pack(fill="both", expand=True, pady=(12, 0))
        info_inner = tk.Frame(info_card, bg=C_CARD)
        info_inner.pack(fill="both", expand=True, padx=16, pady=(14, 16))

        tk.Label(info_inner, text="Info Config (read-only)", bg=C_CARD,
                 fg=C_HEADER, font=font(12, "bold")).pack(anchor="w")

        self.info_tree = make_tree(info_inner, ["item", "value"], show="headings")
        self.info_tree.column("item", width=260, minwidth=160, anchor="w")
        self.info_tree.heading("item", text="Item")
        self.info_tree.column("value", width=420, minwidth=200, anchor="w")
        self.info_tree.heading("value", text="Nilai")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Pilih RootPath")
        if folder:
            if not folder.endswith(os.sep):
                folder += os.sep
            self.rootpath_var.set(folder)

    def _load_config_to_form(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._set_info_error(
                f"config.json tidak ditemukan di:\n{CONFIG_PATH}")
            self.rootpath_var.set("")
            return
        except json.JSONDecodeError as e:
            self._set_info_error(f"config.json rusak (JSON invalid):\n{e}")
            self.rootpath_var.set("")
            return

        # v3.9.69 — P2.2 (audit eksternal ke-2): struktur salah kini
        # TERTANGANI di startup — dulu akar non-dict (mis. JSON list)
        # → AttributeError `.get` L2902 dan `Folders`/`Sheets` list →
        # AttributeError `.items()` di _render_info_tree, keduanya
        # dipanggil __init__ → crash.log + dialog (bukan mati senyap,
        # tapi app tak jalan). Pola defensif _config_dpi_aware disalin:
        # nilai salah → tampil JUJUR di area Info Config + default kosong.
        if not isinstance(data, dict):
            self._set_info_error(
                "config.json rusak (struktur salah):\n"
                "akar file harus objek JSON {…}, yang terbaca "
                f"{type(data).__name__}.\n"
                "Perbaiki file (atau hapus — app akan memakai default) "
                "lalu buka kembali.")
            self.rootpath_var.set("")
            return
        rp = data.get("RootPath", "")
        if not isinstance(rp, str):
            # RootPath non-string (list/number) → jangan diredam ke Tcl
            # (StringVar.set menolak non-str); info ⚠ ditampilkan di
            # _render_info_tree lewat section FOLDERS bila terkait —
            # RootPath sendiri dikosongkan (jujur, bukan crash).
            rp = ""
        self.rootpath_var.set(rp)
        self._render_info_tree(data)
        # v3.9.5 FIX (audit 19-c #6): RootPath dibaca SAAT notebook dibangun
        # (SEBELUM config dimuat) → initialdir dialog 📂 Pilih File Deviasi
        # selalu "" saat app baru dibuka. Sinkronkan setiap RootPath berubah.
        self._sync_komparasi_initial_dir()

    def _sync_komparasi_initial_dir(self):
        """v3.9.5 (audit 19-c #6): initial dialog komparasi mengikuti
        RootPath terkini (config dimuat SETELAH notebook dibangun)."""
        rp = (self.rootpath_var.get().strip()
              if getattr(self, "rootpath_var", None) is not None else "")
        if rp and getattr(self, "komparasi_view", None) is not None:
            self.komparasi_view._initial_dir = rp

    def _render_info_tree(self, data: dict):
        self.info_tree.delete(*self.info_tree.get_children())
        for section, key in [("FOLDERS", "Folders"), ("SHEETS", "Sheets")]:
            sec_id = self.info_tree.insert(
                "", "end", values=(f"== {section} ==", ""))
            self.info_tree.item(sec_id, open=True)
            # v3.9.69 — P2.2: section non-dict (mis. Folders = list)
            # dulu AttributeError `.items()` DI STARTUP → crash.log;
            # kini baris ⚠ jujur — struktur salah TERLIHAT, app tetap hidup
            # (pola defensif _config_dpi_aware).
            sec = data.get(key, {}) if isinstance(data, dict) else {}
            if sec is None:
                continue  # JSON null → kosong (kelunakan lama `or {}`)
            if not isinstance(sec, dict):
                self.info_tree.insert(
                    sec_id, "end",
                    values=(f"⚠ {key} bukan objek JSON "
                            f"({type(sec).__name__}) — diperlakukan kosong",
                            ""))
                continue
            for k, v in sec.items():
                self.info_tree.insert(sec_id, "end", values=(k, v))
        self.info_tree.tag_configure("bold", font=font(9, "bold"))

    def _set_info_error(self, msg: str):
        self.info_tree.delete(*self.info_tree.get_children())
        self.info_tree.insert("", "end", values=("ERROR", msg), tags=("err",))
        self.info_tree.tag_configure("err", foreground=C_RED)

    def _save_config(self):
        new_root = self.rootpath_var.get().strip()
        if not new_root:
            messagebox.showwarning("Validasi", "RootPath tidak boleh kosong.",
                                   parent=self.root)
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError as e:
            messagebox.showerror(
                "Config Rusak",
                f"config.json tidak bisa dibaca (JSON invalid):\n{e}",
                parent=self.root)
            return

        data["RootPath"] = new_root
        # v3.5: LightMode dihapus — key lama (bila ada) dibuang saat save
        data.pop("LightMode", None)

        # FIX D-05 (audit 2-d): tulis ATOMIK (tmp + os.replace) — crash
        # di tengah write tidak lagi meninggalkan config.json korup
        # (pola sama followup.py; .bak tetap dibuat sebagai cadangan).
        # v3.9.42 — audit 61-c/61-d (F3 P3): .bak dulu ditulis dari `data`
        # (isi BARU — sama dgn config yang baru ditulis) → .bak tidak
        # berguna utk rollback. Kini: .bak = salinan file LAMA via
        # shutil.copy2 SEBELUM tmp/config baru ditulis (rollback bener);
        # gagal copy → [WARNING] (pola log app — app tetap tersimpan).
        backup_path = CONFIG_PATH.with_suffix(".json.bak")
        if CONFIG_PATH.exists():
            try:
                shutil.copy2(CONFIG_PATH, backup_path)
            except OSError as e:
                print(f"[WARNING] Gagal membuat backup config "
                      f"({backup_path.name}): {e}")

        tmp_path = CONFIG_PATH.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, CONFIG_PATH)
        except Exception as e:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
            messagebox.showerror(
                "Gagal Simpan", f"Tidak bisa menulis config.json:\n{e}",
                parent=self.root)
            return

        messagebox.showinfo(
            "Berhasil",
            f"Config disimpan.\n\nRootPath: {new_root}\n\n"
            # v3.9.59 — FIX 2a-10 (audit 2-a): data/view LAMA masih tampil
            # sampai pipeline dijalankan ulang — tanpa kalimat ini user
            # yakin data sudah berganti lalu melihat data lokasi lama.
            "Data lama tetap tampil sampai pipeline dijalankan ulang "
            "(klik 🚀 MULAI PROSES untuk membaca folder baru).",
            parent=self.root)
        self._load_config_to_form()

    # =====================================================================
    # TAB: PROSES
    # =====================================================================
    def _build_proses_tab(self):
        tab = self.tab_proses
        wrap = tk.Frame(tab, bg=C_BG)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Card: Kontrol Pipeline ---
        ctrl = tk.Frame(wrap, bg=C_CARD, highlightbackground="#e2e8f0",
                        highlightthickness=1)
        ctrl.pack(fill="x")
        ctrl_inner = tk.Frame(ctrl, bg=C_CARD)
        ctrl_inner.pack(fill="x", padx=16, pady=14)

        tk.Label(ctrl_inner, text="Kontrol Pipeline", bg=C_CARD, fg=C_HEADER,
                 font=font(12, "bold")).pack(anchor="w")

        btns = tk.Frame(ctrl_inner, bg=C_CARD)
        btns.pack(fill="x", pady=(0, 10))
        self.btn_mulai = AccentButton(btns, text="🚀 MULAI PROSES",
                                      command=self._start_pipeline)
        self.btn_mulai.pack(side="left")

        self.btn_stop = DangerButton(btns, text="⏹ Stop", state="disabled",
                                     command=self._stop_pipeline)
        self.btn_stop.pack(side="left", padx=(8, 0))
        # FIX A-02: state disabled dari constructor tidak memakai styling
        # dim → panggil set_enabled sekali supaya konsisten visual.
        self.btn_stop.set_enabled(False)

        self.btn_bersih = GhostButton(btns, text="🧹 Bersihkan Log",
                                      command=self._clear_log)
        self.btn_bersih.pack(side="left", padx=(8, 0))

        # v3.9.33 — AUDIT FIX (48-f MEDIUM): log konsol (state disabled) tidak
        # bisa di-copy — tombol salin SELURUH isi log ke clipboard.
        self.btn_salin_log = GhostButton(btns, text="📋 Salin Log",
                                         command=self._copy_log)
        self.btn_salin_log.pack(side="left", padx=(8, 0))

        # v3.9.37 — ↻ Refresh Sumber: dialog selektif (file yang berubah
        # sejak proses terakhir tercentang default; file lain tak dibaca
        # ulang — cache bacaan).
        # v3.9.59 — FIX 2a-09/2f-13: label disamakan dgn toolbar (dulu
        # '🔄 Refresh File Sumber…' — dua label utk aksi yang sama).
        self.btn_refresh_src = GhostButton(
            btns, text="↻ Refresh Sumber",
            command=self._open_refresh_dialog)
        self.btn_refresh_src.pack(side="left", padx=(8, 0))

        # v3.9.59 — FIX 2a-09/2f-13: label disamakan dgn toolbar (dulu
        # '💾 Export ke Excel' — dua label utk aksi yang sama).
        self.btn_export = GhostButton(btns, text="💾 Export Excel",
                                      state="disabled",
                                      command=self._export_excel)
        self.btn_export.pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar(value="Status: siap.")
        status_row = tk.Frame(ctrl_inner, bg=C_CARD)
        status_row.pack(fill="x")
        self.status_spinner = Spinner(status_row, size=18, bg=C_CARD)
        self.status_spinner.pack(side="left", padx=(0, 8))
        self.status_spinner.stop()
        tk.Label(status_row, textvariable=self.status_var, bg=C_CARD,
                 fg=C_HEADER, font=font(10, "bold")).pack(anchor="w")
        self.progress = ttk.Progressbar(ctrl_inner, mode="indeterminate",
                                        orient="horizontal")
        self.progress.pack(fill="x", pady=(6, 2))

        # --- KPI row ---
        kpi_row = KpiRow(wrap)
        self.kpi_status = KpiCard(kpi_row, "Status Pipeline", "SIAP",
                                  "menunggu perintah", C_GREEN)
        self.kpi_elapsed = KpiCard(kpi_row, "Waktu Berjalan", "0.0 dtk",
                                   "sejak MULAI PROSES", C_HEADER)
        # v3.9.59 — FIX 2a-09: label KPI berbahasa Indonesia (dulu 'Rows
        # …' EN — nilai di bawahnya sudah '1.500 baris' per FIX 6a-05,
        # label saja yang tertinggal).
        self.kpi_append = KpiCard(kpi_row, "Baris Append1", "—",
                                  "pipeline belum jalan")
        self.kpi_rincian = KpiCard(kpi_row, "Baris Rincian PO", "—",
                                   "pipeline belum jalan")
        for c in (self.kpi_status, self.kpi_elapsed, self.kpi_append,
                  self.kpi_rincian):
            kpi_row.add(c)
        kpi_row.pack(fill="x", pady=12)

        # --- Konsol log gelap ---
        log_card = tk.Frame(wrap, bg=C_CARD, highlightbackground="#e2e8f0",
                            highlightthickness=1)
        log_card.pack(fill="both", expand=True)
        log_head = tk.Frame(log_card, bg=C_CARD)
        log_head.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(log_head, text="Log Proses", bg=C_CARD, fg=C_HEADER,
                 font=font(12, "bold")).pack(anchor="w")

        log_wrap = tk.Frame(log_card, bg=C_CARD)
        log_wrap.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self.log_text, _ = make_log_console(log_wrap)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self._log_line_count = 0

    def _copy_log(self):
        """v3.9.33 — AUDIT FIX (48-f MEDIUM): salin SELURUH isi konsol log ke
        clipboard (traceback pipeline jadi bisa dibagikan) + feedback singkat
        di baris status kartu Kontrol Pipeline.

        v3.9.46 — audit 66 temuan #3: feedback TERSALIN tidak lagi bisa
        mengembalikan status pipeline BASI. Dulu: `prev` disimpan → flash
        2,5 dtk → timer memulihkan `prev` APA PUN YANG TERJADI — dua lubang:
        (a) pipeline SELESAI di tengah flash menimpa status_var dengan
        "Status: SELESAI." → timer lalu memulihkan "menjalankan pipeline…"
        (status LIE); (b) copy kedua <2,5 dtk menyimpan TEKS FLASH sebagai
        prev → timer memulihkan notifikasi, bukan status. Kini:
        (a) snapshot prev hanya diambil dari kondisi STABIL (flash lain
            belum aktif);
        (b) saat timer menyala, bila status_var sudah DIGANTI pihak lain
            (pipeline done/error/stop), status TERBARU yang menang —
            restore dilewati (lihat _log_flash_restore)."""
        try:
            content = self.log_text.get("1.0", "end-1c")
        except tk.TclError:
            return
        if not content.strip():
            messagebox.showinfo("Salin Log", "Log masih kosong.",
                                parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        n_baris = len(content.splitlines())
        if not getattr(self, "_log_flash_active", False):
            # snapshot hanya dari kondisi stabil — bukan dari teks flash
            # (copy ke-2 dlm rentang flash mempertahankan prev PERTAMA)
            self._log_flash_prev = self.status_var.get()
        self._log_flash_active = True
        self.status_var.set(
            f"📋 Log TERSALIN ke clipboard ({fmt_int_id(n_baris)} baris).")
        if getattr(self, "_log_flash_after", None):
            with contextlib.suppress(Exception):
                self.root.after_cancel(self._log_flash_after)

        self._log_flash_after = self.root.after(
            2500, self._log_flash_restore)

    def _log_flash_restore(self):
        """v3.9.46 — pemulihan status pasca-flash "Log TERSALIN".

        Status pipeline yang LEBIH BARU selalu menang: bila status_var
        sudah berubah sejak flash (pipeline selesai/error/stop di tengah
        2,5 dtk), pemulihan prev DILEWATI — hanya teks flash yang masih
        utuh yang diganti kembali ke prev."""
        self._log_flash_active = False
        self._log_flash_after = None
        if not self.root.winfo_exists():
            return
        cur = self.status_var.get()
        if cur.startswith("📋 Log TERSALIN"):
            self.status_var.set(getattr(self, "_log_flash_prev", ""))

    # =====================================================================
    # LOG QUEUE (freeze fix dipertahankan)
    # =====================================================================
    def _append_log_batched(self, text: str):
        """Append batch text ke konsol log dengan truncation otomatis."""
        if not text:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, text)

        new_lines = text.count("\n")
        self._log_line_count += new_lines

        if self._log_line_count > MAX_LOG_LINES:
            # v3.9.33 — AUDIT FIX (48-f LOW): baris awal dibuang TANPA jejak —
            # user tidak tahu lognya terpangkas. Sisipkan SATU baris marker
            # di puncak supaya jelas (+1 ke hitungan baris).
            self.log_text.delete("1.0", "1001.0")
            self._log_line_count -= 1000
            self.log_text.insert("1.0",
                                 f"(log dipangkas — {fmt_int_id(1000)} "
                                 "baris awal dibuang)\n")
            self._log_line_count += 1

        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self):
        """Batch log writes — ambil semua chunks dari queue (dengan cap).

        v3.9.42 — audit 61-c/61-d (F4 P3): reschedule dipindah ke
        `finally` — dulu `self.after(...)` adalah statement terakhir,
        exception di tengah badan (mis. Text widget log mati → TclError
        di _append_log_batched) mematikan polling log PERMANEN senyap:
        log berhenti mengalir tanpa jejak. Guard winfo_exists mencegah
        jadwal baru saat root sudah mati (tidak dobel-reschedule)."""
        try:
            chunks = []
            total_chars = 0
            chunk_count = 0
            try:
                while chunk_count < MAX_CHUNKS_PER_POLL \
                        and total_chars < MAX_CHARS_PER_POLL:
                    chunk = self.log_queue.get_nowait()
                    chunks.append(chunk)
                    total_chars += len(chunk)
                    chunk_count += 1
            except queue.Empty:
                pass

            if chunks:
                text = "".join(chunks)
                # FIX D-04: reader me-log "[WARNING] Skip file ..." ke stdout
                # (helpers.py) — dihitung di sini (jalur log = satu-satunya
                # tempat lewat) TANPA mengubah kontrak pipeline.
                n = text.count("[WARNING] Skip file")
                if n:
                    self._skipped_files += n
                # v3.9.69 — P1.2 (audit eksternal ke-2): peringatan FORMAT
                # pipeline ([fn_XXXX] WARNING · combine_folder · 4217 ·
                # Append1 · Harga 41.09) kini ikut dihitung → status akhir
                # "SELESAI DENGAN PERINGATAN" (dulu hanya Skip file yang
                # dihitung — skema rusak lenyap di balik status HIJAU).
                m = len(_PIPELINE_WARN_RE.findall(text))
                if m:
                    self._schema_warnings += m
                self._append_log_batched(text)
        finally:
            # pola suppress repo — widget mati (TclError) diabaikan; TIDAK
            # dobel-reschedule (poll tunggal, satu jadwal per invokasi).
            with contextlib.suppress(Exception):
                if self.root.winfo_exists():
                    self.root.after(LOG_POLL_INTERVAL_MS,
                                    self._poll_log_queue)

    # =====================================================================
    # PIPELINE CONTROL
    # =====================================================================
    def _start_pipeline(self, refresh_files=False):
        """Jalankan pipeline. refresh_files (v3.9.37):
        - False  → run normal (cache bacaan tetap dipakai utk file yang
          tak berubah — hasil identik, lebih cepat);
        - None   → REFRESH SEMUA (cache bacaan dikosongkan dulu oleh
          _refresh_sources — semua file dibaca ulang);
        - list   → REFRESH TERPILIH (entry cache file itu sudah
          diinvalidasi _refresh_sources — hanya file itu dibaca ulang;
          file lain disajikan cache: "gak harus refresh semua")."""
        if self.is_running:
            messagebox.showinfo(
                "Sedang Berjalan",
                "Pipeline sedang berjalan. Tunggu hingga selesai atau klik Stop.",
                parent=self.root)
            return

        if not CONFIG_PATH.exists():
            messagebox.showerror(
                "Config Tidak Ada",
                f"config.json tidak ditemukan:\n{CONFIG_PATH}", parent=self.root)
            return

        # FIX A-01 (audit 2-a): guard kedua — bila worker LAMA masih hidup
        # (baru di-Stop, belum sampai checkpoint), JANGAN jalankan thread
        # kedua: stop_event.clear() akan membatalkan Stop-nya & dua
        # pipeline berjalan paralel (log tercampur, data last-writer-wins).
        worker = getattr(self, "worker_thread", None)
        if worker is not None and worker.is_alive():
            messagebox.showinfo(
                "Masih Menghentikan",
                "Pipeline sebelumnya masih berhenti di checkpoint.\n"
                "Tunggu sampai status berubah, lalu Mulai lagi.",
                parent=self.root)
            return

        # FIX D-04: reset penghitung file yang di-skip reader
        self._skipped_files = 0
        # v3.9.69 — P1.2: reset penghitung peringatan skema pipeline
        # (status akhir mencerminkan run INI — pola FIX D-04).
        self._schema_warnings = 0
        # v3.9.37 — reset penghitung cache hit/miss per-file (log akhir
        # run mencerminkan run INI — file dibaca ulang vs disajikan cache)
        read_cache_reset_counters()

        # v3.9.33 — AUDIT FIX (48-f HIGH-#6): PRE-FLIGHT folder data SEBELUM
        # pipeline — dulu folder hilang / RootPath salah → pipeline berjalan
        # dan berakhir "SELESAI" HIJAU + tabel kosong SENYAP tanpa pesan aksi.
        # Kini kegagalan di-surface AWAL (log + dialog + status amber) lalu
        # run tetap lanjut (perilaku degrade yang sama, kini terlihat).
        # Kontrak: src/pipeline/helpers.preflight_folders(cfg) —
        # missing [(key, full_path)] folder Folders yang tidak ada;
        # counts [(key, n_file_excel)] per folder (folder hilang → 0).
        pre_missing: list = []
        try:
            from src.config import Config
            from src.pipeline.helpers import preflight_folders
            pre_missing, pre_counts = preflight_folders(Config(str(CONFIG_PATH)))
            for key, n in pre_counts:
                self._append_log_batched(f"  Pre-flight {key}: "
                                         f"{fmt_int_id(n)} file excel\n")
        except ImportError:
            # helper belum tersedia saat runtime → skip pre-flight graceful
            pre_missing = []
        except Exception as exc:  # defensive: config rusak dll — jangan blokir run
            pre_missing = []
            self._append_log_batched(
                f"\n[PERINGATAN] Pre-flight folder dilewati: {exc}\n")

        if pre_missing:
            daftar = "\n".join(f"  • {key} → {path}"
                               for key, path in pre_missing)
            self._append_log_batched(
                "\n[PERINGATAN] Folder data TIDAK DITEMUKAN —\n"
                + daftar +
                "\n  Pipeline tetap dijalankan (data jadi parsial/kosong).\n")
            messagebox.showwarning(
                "Folder data tidak ditemukan",
                "Folder data berikut TIDAK DITEMUKAN:\n\n" + daftar +
                "\n\nPipeline tetap dijalankan (data bisa parsial/kosong).\n"
                # v3.9.59 — FIX 2a-04: tab yang dimaksud adalah '⚙️
                # Config' (dulu '⚙ Pengaturan' — tab itu tidak pernah
                # tampil, panduan jadi dead-end).
                "Perbaiki RootPath / Folders di tab ⚙️ Config.",
                parent=self.root)
        # v3.9.46 — audit 66 temuan #1: preflight DIINGAT sampai run usai —
        # status akhir "SELESAI DENGAN PERINGATAN" (folder sumber
        # bermasalah) membutuhkan daftar ini di _on_pipeline_done (dulu
        # hanya tampil sekali di awal run lalu tertutup status hijau).
        self._pre_missing = list(pre_missing)

        is_refresh = refresh_files is not False
        if not is_refresh:
            # v3.9.59 — FIX 2a-11: pindah tab programatik + fokus ikut
            # pindah (dulu fokus menempel di tombol MULAI PROSES).
            self._go_to_proses_tab()
        # v3.9.37 — refresh mode: TETAP di tab aktif (data diperbarui
        # in-place; tab lain menyusul via lazy refresh saat dipilih —
        # "gak harus refresh semua" juga soal gangguan view).
        self.is_running = True
        self.stop_event.clear()
        self.btn_mulai.set_enabled(False)
        self.btn_stop.set_enabled(True)
        # FIX A-02: set_enabled (visual dim) — bukan configure(state) polos
        self.btn_export.set_enabled(False)
        self.btn_export_tb.set_enabled(False)
        if is_refresh:
            n_sel = 0 if refresh_files is None else len(refresh_files)
            label = ("SEMUA file sumber" if refresh_files is None
                     else f"{fmt_int_id(n_sel)} file sumber terpilih")
            self.status_var.set(f"Status: menyegarkan {label}…")
            self.statusbar.set_status(
                f"🔄 Refresh — {label} (file lain dari cache bacaan)…",
                C_ORANGE)
        else:
            self.status_var.set("Status: menjalankan pipeline…")
            self.statusbar.set_status(*_ST_RUN)
        self.status_spinner.start()
        if pre_missing:
            # v3.9.33 — status AMBER sebelum run: folder data bermasalah jangan
            # tertutup status "berjalan" polos (48-f: kegagalan senyap).
            self.statusbar.set_status(
                "Pipeline berjalan… ⚠ folder data tidak ditemukan — lihat log",
                C_AMBER)
        self.kpi_status.set_value(
            "MENYEGARKAN…" if is_refresh else "MENJALANKAN",
            "file sumber diproses ulang…" if is_refresh
            else "pipeline sedang diproses…", C_ORANGE)
        self.progress.start(12)
        self._run_start_time = time.time()
        self._tick_elapsed()

        self._append_log_batched("\n" + "=" * 60 + "\n")
        if is_refresh:
            n_sel = 0 if refresh_files is None else len(refresh_files)
            self._append_log_batched(
                "  🔄 REFRESH FILE SUMBER — "
                f"{'SEMUA' if refresh_files is None else fmt_int_id(n_sel)} "
                "file dibaca ulang dari disk;\n"
                "  file lain memakai bacaan cache (tak berubah — "
                "mtime/ukuran identik).\n")
        else:
            self._append_log_batched("  Memulai pipeline…\n")

        # v3.9.37 — flag refresh diteruskan ke _on_pipeline_done (tetap di
        # tab aktif saat selesai; log penutup beda).
        self._refresh_flag = refresh_files
        self.worker_thread = threading.Thread(
            target=self._run_pipeline_worker, daemon=True)
        self.worker_thread.start()

    def _tick_elapsed(self):
        """Update KPI waktu berjalan tiap detik selama pipeline aktif."""
        if self._run_start_time is None:
            return
        elapsed = time.time() - self._run_start_time
        if elapsed < 60:
            txt = f"{elapsed:.0f} dtk"
        else:
            txt = f"{int(elapsed // 60)} mnt {elapsed % 60:.0f} dtk"
        self.kpi_elapsed.set_value(txt)
        self._elapsed_after_id = self.root.after(1000, self._tick_elapsed)

    def _stop_elapsed(self):
        if self._elapsed_after_id:
            try:
                self.root.after_cancel(self._elapsed_after_id)
            except Exception:
                pass
            self._elapsed_after_id = None

    def _schedule_to_main(self, fn):
        """v3.9.33 — AUDIT FIX (48-c LOW): root.after() dari thread worker
        saat window sudah DITUTUP melempar TclError; jalur except lama
        memanggil after() LAGI → TclError tak tertangkap di thread daemon.
        Kini: root sudah mati → menyerah senyap (proses ikut mati bersama
        main thread — worker memang daemon)."""
        try:
            self.root.after(0, fn)
        except tk.TclError:
            pass

    def _run_pipeline_worker(self):
        """Worker thread: jalankan run_pipeline, tangkap error.

        v3.3 BUG FIX: dulu `except X as e:` + lambda tertunda → Python
        menghapus binding `e` di akhir blok except → NameError saat
        callback berjalan (error pipeline tidak pernah sampai ke UI).
        Kini error ditangkap ke tuple lokal dulu, lambda bebas closure.

        v3.9 CRASH FIX: GC dimatikan selama thread pipeline hidup — GC di
        thread worker bisa mem-finalisasi tk.Variable sisa popup yang
        sudah ditutup (destructor memanggil Tcl dari thread bukan-main →
        segfault CPython 3.12+Tk). Dilepas di _on_pipeline_done (main
        thread) setelah thread dipastikan mati.
        """
        gc_shield_acquire()
        # v3.9.37 — flag refresh (False/None/list) dibaca saat SELESAI:
        # worker tak membaca state app lain saat berjalan (pola lama).
        _rf = getattr(self, "_refresh_flag", False)
        try:
            append1_df, rincian_po_df, in_detail_df, audit_result = run_pipeline(
                verbose=True, stop_event=self.stop_event)
            self._schedule_to_main(lambda: self._on_pipeline_done(
                append1_df, rincian_po_df, in_detail_df, audit_result, None,
                _rf))
        except PipelineStopped as exc:
            err = (exc, None)
            self._schedule_to_main(lambda: self._on_pipeline_done(
                None, None, None, None, err, _rf))
        except Exception as exc:
            import traceback
            err = (exc, traceback.format_exc())
            self._schedule_to_main(lambda: self._on_pipeline_done(
                None, None, None, None, err, _rf))
        except BaseException as exc:
            # FIX 6a-06: BaseException (SystemExit/KeyboardInterrupt dari
            # kedalaman pipeline) dulu LOLOS kedua handler di atas →
            # _on_pipeline_done tak pernah terjadwal: is_running menempel
            # True (MULAI/⏹ mati seumur sesi), spinner/elapsed jalan terus,
            # dan gc_shield_acquire() tak pernah dilepas (gc.disable()
            # seumur sesi — pola B-20 yang sudah difix di widgets.run_async
            # tapi tidak di worker app). Kini: jadwalkan penyelesaian ERROR
            # (melepas shield GC + reset state + log di MAIN thread) LALU
            # re-raise supaya exception tetap propagasi (KeyboardInterrupt
            # tidak ditelan).
            import traceback
            err = (exc, traceback.format_exc())
            self._schedule_to_main(lambda: self._on_pipeline_done(
                None, None, None, None, err, _rf))
            raise

    def _sync_export_buttons(self) -> None:
        """FIX 6a-01 — sinkronkan tombol 💾 Export (toolbar + tab Proses)
        ke ketersediaan data AKTUAL app (kriteria sama dgn guard
        _export_excel: append1/rincian_po TERSEDIA).

        Dipanggil di SEMUA jalur keluar _on_pipeline_done (sukses / ERROR /
        STOP) + selesai/gagal export. Dulu hanya jalur SUKSES yang
        meng-enable: run yang gagal/di-STOP padahal data run LAMA masih
        tampil meninggalkan tombol mati selamanya — user dipaksa re-run
        pipeline penuh hanya untuk men-export data lama yang masih valid.
        (Di jalur ERROR/STOP data run lama sengaja DIPERTAHANKAN — self.
        append1_df dkk. tidak ditimpa; tombol mengikuti data itu.)"""
        has_data = (self.append1_df is not None
                    or self.rincian_po_df is not None)
        self.btn_export.set_enabled(has_data)
        self.btn_export_tb.set_enabled(has_data)

    def _on_pipeline_done(self, append1_df, rincian_po_df, in_detail_df,
                          audit_result, error, refresh_files=False):
        """Dijadwalkan ke main thread via after().

        v3.9.37 — refresh_files: False = run normal; None = refresh semua;
        list = refresh terpilih → penutup TIDAK melompat ke tab 📊 Pivot
        (tetap di tab aktif; view aktif refresh in-place oleh load_data,
        tab lain menyusul via lazy refresh)."""
        # v3.9: lepas GC shield SEBELUM UI work berat — bila thread pipeline
        # belum benar-benar mati, retry 15ms sampai mati (lihat widgets.py)
        gc_shield_release(self.worker_thread, retry_widget=self.root)
        self.progress.stop()
        self.status_spinner.stop()
        self._stop_elapsed()
        self.is_running = False
        self.btn_mulai.set_enabled(True)
        self.btn_stop.set_enabled(False)

        # Final elapsed
        if self._run_start_time is not None:
            elapsed = time.time() - self._run_start_time
            self.kpi_elapsed.set_value(f"{elapsed:.1f} dtk", "total waktu proses")
            self._run_start_time = None

        if error is not None:
            exc, tb = error
            if isinstance(exc, PipelineStopped):
                self.status_var.set("Status: DIHENTIKAN oleh user.")
                self.statusbar.set_status(*_ST_STOP)
                self.kpi_status.set_value("DIHENTIKAN", "oleh user", C_AMBER)
                self._append_log_batched(f"\n[STOP] {exc}\n")
                # FIX 6a-01: jalur STOP juga sinkron tombol export (data
                # run lama masih tampil & masih bisa di-export)
                self._sync_export_buttons()
                return
            self.status_var.set("Status: ERROR.")
            self.statusbar.set_status(*_ST_ERR)
            self.kpi_status.set_value("ERROR", "lihat log untuk detail", C_RED)
            self._append_log_batched("\n[ERROR] Pipeline gagal:\n")
            self._append_log_batched(str(exc) + "\n")
            if tb:
                self._append_log_batched("\n" + tb + "\n")
            messagebox.showerror(
                "Pipeline Gagal",
                f"Terjadi error:\n{exc}\n\nLihat log di tab Proses untuk detail.",
                parent=self.root)
            # FIX 6a-01: jalur ERROR juga sinkron tombol export (data run
            # lama masih tampil & masih bisa di-export)
            self._sync_export_buttons()
            return

        # Sukses — simpan + muat data ke semua view
        # (defensive: caller test boleh pass None — anggap kosong)
        if append1_df is None:
            append1_df = pd.DataFrame()
        if rincian_po_df is None:
            rincian_po_df = pd.DataFrame()
        if in_detail_df is None:
            in_detail_df = pd.DataFrame()
        self.append1_df = append1_df
        self.rincian_po_df = rincian_po_df
        self.in_detail_df = in_detail_df
        self.audit_result = audit_result
        audit_df = audit_result.get("df") if audit_result else None
        audit_kpi = audit_result.get("kpi") if audit_result else None
        audit_n = len(audit_df) if audit_df is not None else 0
        # v3.9.59 — FIX 2f-17: waktu selesai dicatat di AWAL jalur sukses
        # (data pipeline sudah balik; loading view menyusul) supaya SEMUA
        # status SELESAI di bawah bisa menyebut umur data (' · Data:
        # dd-mm HH:MM') — dulu timestamp ini hanya hidup di dialog 🔄
        # Refresh, statusbar tak pernah menyebut kesegaran data.
        self._last_run_finished_at = time.time()
        self.status_var.set("Status: SELESAI.")
        # FIX 6a-05: fmt_int_id + "baris" — dulu grouping EN "215,950
        # rows" di status bar & KPI padahal log/tabel/chip pakai 215.950
        # (campuran lokal satu layar) + "1 rows" (plural EN salah).
        self.statusbar.set_status(
            f"SELESAI — Append1: {fmt_int_id(len(append1_df))} baris · "
            f"Rincian PO: {fmt_int_id(len(rincian_po_df))} baris · "
            f"IN detail: {fmt_int_id(len(in_detail_df))} baris · "
            f"Audit: {fmt_int_id(audit_n)} baris{self._data_time_suffix()}",
            C_GREEN)
        self.kpi_status.set_value("SELESAI", "data siap dianalisis", C_GREEN)
        # v3.9.46 — audit 66 temuan #1: status hijau di atas adalah
        # PROVISORI — status AKHIR jujur ditetapkan SETELAH semua view
        # dimuat (lihat blok "STATUS AKHIR JUJUR" di bawah): kegagalan
        # view / folder hilang / file ter-skip tidak boleh berakhir
        # tampil sebagai sukses penuh. Ditulis dua fase agar chip KPI
        # & log tidak menunggu render view (lambat di data besar).
        self.kpi_append.set_value(fmt_int_id(len(append1_df)),
                                  "baris pivot siap di tab 📊")
        self.kpi_rincian.set_value(fmt_int_id(len(rincian_po_df)),
                                   "baris PO siap di tab 🛒")
        # FIX 6a-05: log penutup ikut fmt_int_id + "baris"
        self._append_log_batched(
            f"\n  Append1: {fmt_int_id(len(append1_df))} baris\n")
        self._append_log_batched(
            f"  Rincian PO: {fmt_int_id(len(rincian_po_df))} baris\n")
        if audit_df is not None and audit_n:
            # FIX C-03: log audit ikut format Indonesia (1.234.567) —
            # konsisten dgn formatter tabel & KPI chips.
            # FIX 6a-05: "rows" → "baris" (plural EN di teks Indonesia).
            self._append_log_batched(
                f"  Audit Rekonsiliasi: {fmt_int_id(audit_n)} baris · "
                f"OK {fmt_int_id(audit_kpi['ok'])} · "
                f"Cut-off {fmt_int_id(audit_kpi['cutoff'])} · "
                f"Valid {fmt_int_id(audit_kpi['omit'])} · "
                f"Deviasi Murni {fmt_int_id(audit_kpi['deviasi_murni'])} · "
                f"Sisa Gantung {fmt_int_id(audit_kpi['deviasi_qty'])}\n")
            # v3.9.30 — deviasi murni ber-PO 'Menunggu diproses'
            # (explainable — akan resolve saat PO diproses jadi RI)
            _n_po = audit_kpi.get("dev_murni_po", 0)
            if _n_po:
                self._append_log_batched(
                    f"  Deviasi Murni ber-PO Menunggu: "
                    f"{fmt_int_id(_n_po)} baris — explainable, sisanya "
                    f"perlu audit fisik\n")
        # v3.9.32 — harga 41.09 (mode Nominal siap?)
        _n_harga = len(audit_result.get("harga_map") or {}) \
            if audit_result else 0
        if _n_harga:
            self._append_log_batched(
                f"  Harga 41.09: {fmt_int_id(_n_harga)} barang — mode "
                f"💰 Nominal (H) tab 📋 Laporan Deviasi siap\n")
        # v3.9.34 — peta harga 41.09 + peta rasio konversi (dari
        # audit_result pipeline) diteruskan ke SEMUA view nominal:
        # kolom Nominal Deviasi GR/PCS, kolom Nominal mode Komparasi,
        # mode 💰 Nominal (H), tab 🧮 Nominal Deviasi (Σ per resto).
        _hm = (audit_result.get("harga_map") if audit_result else None)
        _kv = (audit_result.get("konversi_map") if audit_result else None)
        # v3.9.42 — audit 61-c/61-d (F2 P2): jalur REFRESH (refresh_files
        # None/list — "gangguan minimal" janji v3.9.37) meneruskan
        # preserve=True ke view yang mendukungnya: filter ⧩/combo, posisi
        # scroll & seleksi baris DIPERTAHANKAN (validasi combo terhadap
        # values data baru ada di view masing-masing). Run normal
        # (refresh_files=False) tetap reset — perilaku lama.
        _keep_state = refresh_files is not False

        # Load data into views (v3.2: lazy — hanya tab aktif yang compute;
        # tab lain menunggu dipilih via <<NotebookTabChanged>>)
        # v3.9.33 — AUDIT FIX (48-c HIGH-2): ISOLASI ERROR PER-VIEW — dulu
        # 8 load_data berurutan TANPA try/except: satu view exception →
        # view sisanya data BASI + tombol Export tetap mati + log
        # "[SELESAI]" tak pernah tercetak (padahal status bar sudah hijau).
        # Kini tiap view punya try/except sendiri → error DIBISINGKAN ke
        # log dan sisanya tetap dimuat; jalur error pipeline (on_error)
        # tetap terpisah — tidak tertelan di sini.
        # v3.9.46 — audit 66 temuan #1: kegagalan view KINI DIKUMPULKAN
        # (failed_views) → status akhir "SELESAI PARSIAL" + view gagal
        # DITANDAI eksplisit di status_var-nya sendiri ("Data tampilan
        # belum diperbarui") supaya data lama tidak dipakai tanpa sadar.
        failed_views: list = []

        def _load_view(nama: str, fn, view=None) -> None:
            try:
                fn()
            except Exception as exc:  # view gagal ≠ pipeline gagal — lanjut
                failed_views.append(nama)
                self._append_log_batched(
                    f"\n[ERROR] Gagal memuat view {nama}: {exc}\n")
                if view is not None:
                    # TANDAI DI VIEW: yang tampil bukan data run ini
                    with contextlib.suppress(Exception):
                        view.status_var.set(
                            "⚠ Data tampilan BELUM DIPERBARUI — gagal "
                            "memuat run ini (lihat log tab Proses)")

        _load_view("📊 Pivot Table",
                   lambda: self.pivot_view.load_data(append1_df),
                   self.pivot_view)
        # v3.9.23 (poin 6): detail dokumen IN ikut diteruskan ke tab
        # Deviasi GR & PCS — sumber CEK "RI Balancing" kolom utama
        # (bulan Nomor RI ≠ bulan Nomor PO, tanggal dok ≤ H).
        _load_view("📦 Deviasi GR",
                   lambda: self.deviasi_gr_view.load_data(
                       append1_df, in_detail_df,
                       harga_map=_hm, konversi_map=_kv),
                   self.deviasi_gr_view)
        _load_view("🧩 Deviasi PCS",
                   lambda: self.deviasi_pcs_view.load_data(
                       append1_df, in_detail_df,
                       harga_map=_hm, konversi_map=_kv),
                   self.deviasi_pcs_view)
        _load_view("📤 Rekap Selisih IN",
                   lambda: self.in_selisih_view.load_data(
                       append1_df, in_detail_df, audit_result=audit_result),
                   self.in_selisih_view)
        _load_view("🚨 Anomali COM",
                   lambda: self.laporan_view.load_data(
                       append1_df, preserve=_keep_state),
                   self.laporan_view)
        _load_view("⚖ Komparasi File Deviasi",
                   lambda: self.komparasi_view.load_data(
                       append1_df, harga_map=_hm, konversi_map=_kv),
                   self.komparasi_view)
        # v3.9.53 — AUTO-LOAD file deviasi terakhir SAAT STARTUP (bukan
        # menunggu tab 📋 dibuka): kolom 'Dev. Bulan Lalu' tab 📦/🧩 butuh
        # file aktif SEBELUM user membuka tab apa pun (parse di worker —
        # anti-beku; file hilang/error → status saja, tanpa dialog).
        with contextlib.suppress(Exception):
            self.komparasi_view.maybe_auto_load_last()
        # v3.9.32 — mode 💰 Nominal: append1 + peta harga 41.09 + peta
        # rasio konversi (dari audit_result — pipeline v3.9.32;
        # v3.9.34: sumber lokal _hm/_kv bersama semua view nominal)
        _load_view("💰 Nominal (H)",
                   lambda: self.nominal_view.load_data(
                       append1_df, harga_map=_hm, konversi_map=_kv),
                   self.nominal_view)
        # v3.9.34 — tab 🧮 Nominal Deviasi: Σ nominal per resto
        _load_view("🧮 Nominal Deviasi",
                   lambda: self.nominal_resto_view.load_data(
                       append1_df, harga_map=_hm, konversi_map=_kv),
                   self.nominal_resto_view)
        _load_view("🛒 Rincian PO",
                   lambda: self.rincian_view.load_data(
                       rincian_po_df, preserve=_keep_state),
                   self.rincian_view)
        # v3.9.66 — FILTER PERSISTEN: pulihkan kombinasi filter terakhir
        # per tab SEKALI (hanya run pertama sesi dgn data non-kosong;
        # load_data barusan me-reset filter — restore menyusul di atasnya;
        # view yang gagal dimuat skip sendiri lewat guard data kosong).
        self._apply_saved_filters_once()
        # FIX 6a-01: enable via sync helper (kriteria ketersediaan data
        # = guard _export_excel) — jalur ERROR/STOP di atas kini sync juga.
        self._sync_export_buttons()

        # =================================================================
        # v3.9.46 — STATUS AKHIR JUJUR (audit 66 temuan #1 — PRIORITAS #1)
        # =================================================================
        # Satu titik penetapan status AKHIR run, berdasar hasil AKTUAL:
        #   view gagal dimuat           → SELESAI PARSIAL (oranye)
        #   folder sumber / file skip /
        #   peringatan format pipeline   → SELESAI DENGAN PERINGATAN (amber)
        #   bersih                      → SELESAI (hijau)
        # Dulu: (a) status hijau dipasang SEBELUM view dimuat dan kegagalan
        # view hanya sempat tampil di log; (b) mode refresh MENIMPA dengan
        # hijau polos "SELESAI — 🔄 file sumber disegarkan" — peringatan
        # file-skip (FIX D-04) hilang tepat di jalur yang paling rawan
        # (user tetap di tab aktif, log Proses tak terlihat). Kini mode
        # refresh hanya menambah INFO "🔄 disegarkan" tanpa menurunkan
        # severitas; peringatan TETAP TERLIHAT sampai run berikutnya.
        _pre_missing = getattr(self, "_pre_missing", None) or []
        _n_missing = len(_pre_missing)
        _skipped = int(getattr(self, "_skipped_files", 0) or 0)
        # v3.9.69 — P1.2 (audit eksternal ke-2): peringatan FORMAT pipeline
        # (skema kolom salah-ikat / VALUE hilang / duplikat multi-file —
        # pola _PIPELINE_WARN_RE) ikut menaikkan severitas: run tetap
        # selesai, tapi user tidak lagi diberi status HIJAU padahal sumber
        # datanya berpotensi lenyap/nyasar (peringatan hanya di log).
        _warn_ct = int(getattr(self, "_schema_warnings", 0) or 0)
        _refresh_sfx = (" — 🔄 file sumber disegarkan"
                        if refresh_files is not False else "")
        if failed_views:
            # v3.9.59 — FIX 2a-09: istilah dev 'view' → 'tampilan' pada
            # teks user (log teknis per-view tetap memakai 'view').
            _detail = (f"{len(failed_views)} tampilan gagal dimuat ("
                       + ", ".join(failed_views) + ") — lihat log; "
                       "tampilan itu masih menampilkan data LAMA")
            self.status_var.set(
                "Status: SELESAI PARSIAL — sebagian tampilan gagal dimuat.")
            self.statusbar.set_status(
                f"SELESAI PARSIAL{_refresh_sfx} — ⚠ "
                f"{_detail}{self._data_time_suffix()}", C_ORANGE)
            self.kpi_status.set_value("SELESAI PARSIAL", _detail, C_ORANGE)
            self._append_log_batched(
                f"\n[PERINGATAN] SELESAI PARSIAL — {_detail}.\n")
        elif _n_missing or _skipped or _warn_ct:
            # FIX D-04 (audit 2-d): file Excel di-skip reader (terkunci/
            # hilang/rusak) tidak disembunyikan di balik status hijau
            # "SELESAI" — user berhak tahu datanya parsial.
            # v3.9.46: digabung + folder pre-flight ikut dihitung (dulu
            # hanya tampil di awal run lalu tertutup status hijau).
            # v3.9.69 — P1.2: peringatan skema pipeline ikut (audit
            # eksternal ke-2 — data sumber berpotensi lenyap/nyasar).
            _parts = []
            if _n_missing:
                _parts.append(f"{fmt_int_id(_n_missing)} folder sumber "
                              "tidak ditemukan")
            if _skipped:
                _parts.append(f"{fmt_int_id(_skipped)} file Excel "
                              "dilewati (terkunci/hilang/rusak)")
            if _warn_ct:
                _parts.append(f"{fmt_int_id(_warn_ct)} peringatan format "
                              "file sumber (skema kolom berubah — lihat log)")
            _warn = "; ".join(_parts) + " — data parsial, lihat log"
            self.status_var.set("Status: SELESAI DENGAN PERINGATAN.")
            self.statusbar.set_status(
                f"SELESAI DENGAN PERINGATAN{_refresh_sfx} — ⚠ "
                f"{_warn}{self._data_time_suffix()}",
                C_AMBER)
            self.kpi_status.set_value("SELESAI ⚠", _warn, C_AMBER)
            self._append_log_batched(f"\n[PERINGATAN] {_warn}\n")
        elif refresh_files is not False:
            # bersih + mode refresh (v3.9.37): TETAP di tab aktif; judul
            # menyebut REFRESH supaya jelas asal datanya.
            self.statusbar.set_status(
                "SELESAI — 🔄 file sumber disegarkan"
                f"{self._data_time_suffix()}", C_GREEN)
        # bersih + run normal: status hijau provisori (baris atas) sudah
        # tepat — tidak ditimpa.

        # v3.9.37 — catat waktu selesai (acuan "berubah" dialog Refresh
        # File Sumber; v3.9.59 FIX 2f-17: kini di-set di AWAL jalur sukses
        # supaya statusbar ikut menyebutnya) + observabilitas cache baca
        # file sumber (file dibaca ulang vs disajikan cache —
        # silent-failure culture 48).
        _ent, _nf, _hit, _miss = read_cache_stats()
        if _nf:
            self._append_log_batched(
                f"  File sumber (cache baca): {fmt_int_id(_miss)} file "
                f"dibaca ulang · {fmt_int_id(_hit)} file dipakai dari "
                f"cache ({fmt_int_id(_ent)} bacaan tersimpan)\n")

        if refresh_files is False:
            # Switch to Pivot Table tab (default view) — refresh pivot lewat
            # event tab-changed (lazy loading)
            self.notebook.select(self.tab_pivot)
            self.pivot_view.ensure_refreshed()
            # v3.9.59 — FIX 2a-11: pindahkan fokus keyboard ke konten tab
            # pivot (via after_idle — tidak mencuri fokus bila user sedang
            # mengetik; dulu fokus menempel di root sehingga pengguna
            # keyboard harus KLIK dulu sebelum Tab/panah bekerja).
            self.root.after_idle(self._focus_notebook_content)

            # v3.3: selesai = status bar (hijau) + log — TANPA dialog modal
            # (dulu messagebox "Selesai" mem-blok alur tiap kali pipeline usai)
            self._append_log_batched(
                "\n[SELESAI] Pipeline selesai — data siap dianalisis.\n"
                "Lanjut ke tab 📊 Pivot / 📦 Deviasi GR / 🧩 Deviasi PCS /\n"
                "📤 Rekap Selisih IN / 📋 Laporan / 🧮 Nominal Deviasi /\n"
                "☑ Follow Up / 🛒 Rincian PO.\n")
        else:
            n_sel = 0 if refresh_files is None else len(refresh_files)
            self._append_log_batched(
                f"\n[SELESAI] 🔄 Refresh file sumber selesai — "
                f"{'SEMUA' if refresh_files is None else fmt_int_id(n_sel)} "
                "file dibaca ulang, data diperbarui.\n")

    def _maximize_root_window(self):
        """v3.9.55 — F8: maximize jendela lintas platform.

        Urutan: (1) state('zoomed') — Windows (juga beberapa WM Linux);
        (2) attributes('-zoomed') — X11 EWMH; (3) fallback geometry 94%
        layar — HANYA bila ada window manager (tanpa WM — Xvfb headless
        test — biarkan geometry default supaya test deterministik).
        _zoom_base_wh/expected diperbarui oleh <Configure> listener saat
        ukuran akhir diketahui (maximize = bukan resize manual user)."""
        try:
            self.root.state("zoomed")
            return
        except tk.TclError:
            pass
        try:
            self.root.attributes("-zoomed", True)
            return
        except tk.TclError:
            pass
        try:
            if not str(self.root.winfo_manager()):
                return   # tanpa WM (headless) — jangan ubah geometry test
        except tk.TclError:
            pass
        with contextlib.suppress(tk.TclError):
            _sw = int(self.root.winfo_screenwidth())
            _sh = int(self.root.winfo_screenheight())
            _w, _h = int(_sw * 0.94), int(_sh * 0.94)
            self.root.geometry(f"{_w}x{_h}")
            self._zoom_base_wh = (_w, _h)
            self._zoom_expected_wh = (_w, _h)

    def _is_root_maximized(self) -> bool:
        """v3.9.55 — F8: status maximize utk disimpan (Windows 'zoomed'
        state; X11 attributes -zoomed)."""
        try:
            if str(self.root.state()) == "zoomed":
                return True
        except tk.TclError:
            pass
        try:
            if int(self.root.attributes("-zoomed")):
                return True
        except (tk.TclError, ValueError, TypeError):
            pass
        return False

    # =====================================================================
    # v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win #1 Wave 1)
    # =====================================================================
    def _apply_saved_filters_once(self):
        """v3.9.66 — pulihkan kombinasi filter terakhir per tab SEKALI.

        Dipanggil _on_pipeline_done SETELAH fan-out load_data (yang
        me-reset semua filter). Syarat: data non-kosong (0 baris →
        restore ditunda ke run berikutnya — belum ada yang bisa
        difilter). Setelah dipakai → state dilepas (run BERIKUTNYA
        sesi ini kembali ke perilaku reset v3.9.33 — restore tidak
        pernah menimpa kerja user di sesi berjalan). Mode tab 📋
        (SegmentBar) ikut dipulihkan via show_laporan_mode (jalur
        persis klik user).
        v3.9.68 — OBSERVABILITAS (audit eksternal T2): kegagalan
        per-view TIDAK lagi senyap — nama view + penyebab DI-LOG ke
        console log + status bar ringkas; view LAIN tetap dipulihkan.
        Restore TETAP sekali per sesi (KEGAGALAN TIDAK di-retry di run
        berikutnya — kontrak v3.9.33: run ke-2 me-reset filter, retry
        diam-diam justru akan MENIMPA kerja user yang mungkin sudah
        ia atur sendiri; solusi yang benar adalah jejak log, bukan
        retry senyap)."""
        st = getattr(self, "_filter_restore_state", None)
        if not st:
            return
        _df = getattr(self, "append1_df", None)
        if _df is None or bool(getattr(_df, "empty", True)):
            return   # tunda — data belum ada, coba lagi run berikutnya
        self._filter_restore_state = None   # SEKALI saja per sesi
        failed = []
        for key, attr in _FILTER_VIEW_KEYS:
            view = getattr(self, attr, None)
            if view is None:
                continue
            state = st.get(key)
            if not state:
                continue
            try:
                view.restore_filter_state(state)
            except Exception as exc:  # noqa: BLE001 — best-effort/view
                failed.append(key)
                print(f"[PERINGATAN] Filter persist: gagal memulihkan "
                      f"filter tab '{key}': {exc!r}")
        if failed:
            print(f"[PERINGATAN] Filter persist: {len(failed)} tab gagal "
                  f"dipulihkan: {', '.join(failed)} — kombinasi filter "
                  "tab tersebut kembali default sesi ini (detail di atas).")
            with contextlib.suppress(Exception):
                self.status_var.set(
                    f"⚠ Filter {len(failed)} tab gagal dipulihkan — "
                    "detail di log tab 🚀 Proses")
        # mode tab 📋 (state APP — bukan view): key khusus '_app'
        _appst = st.get("_app")
        if isinstance(_appst, dict):
            _m = _appst.get("laporan_mode")
            if isinstance(_m, int) and not isinstance(_m, bool) \
                    and _m in (0, 1, 2):
                try:
                    self.show_laporan_mode(_m)
                except Exception as exc:  # noqa: BLE001 — best-effort
                    print(f"[PERINGATAN] Filter persist: gagal memulihkan "
                          f"mode tab 📋 (idx {_m}): {exc!r}")

    def _capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot SEMUA view → {view_key: dict} (+ '_app').

        Dipanggil _on_close_window. View tanpa data/tanpa filter aktif
        menghasilkan dict kecil/kosong → dibuang (settings.json ramping).
        v3.9.68 — kegagalan per-view DI-LOG (audit eksternal T2: dulu
        senyap total; menutup app tetap tidak boleh gagal, tapi user
        berhak tahu tab mana yang snapshot-nya gagal — jejak ada di
        console log utk sesi berikutnya)."""
        out: dict = {}
        for key, attr in _FILTER_VIEW_KEYS:
            view = getattr(self, attr, None)
            if view is None:
                continue
            try:
                s = view.capture_filter_state()
                if isinstance(s, dict) and s:
                    out[key] = s
            except Exception as exc:  # noqa: BLE001 — close tak boleh gagal
                print(f"[PERINGATAN] Filter persist: gagal mengambil "
                      f"snapshot filter tab '{key}': {exc!r}")
        out["_app"] = {"laporan_mode":
                       int(getattr(self, "_laporan_mode_idx", 0) or 0)}
        return out

    def _on_close_window(self):
        """v3.9.33 — AUDIT FIX (48-c LOW): handler tombol X.

        Pipeline masih berjalan → konfirmasi dulu (worker daemon mati
        bersama proses bila user tetap keluar; tidak ada cleanup khusus
        lain di close path — state persist antara-sesi disimpan oleh
        mekanisme masing-masing saat berubah). Idle → langsung tutup.
        v3.9.55 — F8: sebelum destroy, STATE JENDELA (ukuran/maximize)
        disimpan ke settings.json → sesi berikutnya terbuka persis
        seperti kebiasaan user (tanpa adjust manual).
        v3.9.65 — ZOOM ikut tersimpan (ui_zoom): level CTRL+roda
        terakhir dipulihkan saat buka (default 0.8 bila belum ada).
        v3.9.66 — FILTER ikut tersimpan (filter_state): kombinasi
        filter terakhir per tab dipulihkan saat buka — TIDAK disimpan
        bila sesi ini belum pernah menjalankan pipeline (append1_df
        None): menutup app sebelum run manapun TIDAK boleh menimpa
        kombinasi tersimpan yang masih baik."""
        worker = getattr(self, "worker_thread", None)
        pipeline_hIDup = (self.is_running
                          or (worker is not None and worker.is_alive()))
        if pipeline_hIDup and not messagebox.askyesno(
                "Pipeline Masih Berjalan",
                "Pipeline masih berjalan.\n\nTetap keluar? (proses akan "
                "dihentikan paksa)",
                parent=self.root):
            return
        # v3.9.55 — simpan state jendela (F8); v3.9.65 — + zoom terakhir
        with contextlib.suppress(Exception):
            _max = self._is_root_maximized()
            _w = int(self.root.winfo_width())
            _h = int(self.root.winfo_height())
            if _w >= WINDOW_MIN[0] and _h >= WINDOW_MIN[1]:
                _save_window_state(_w, _h, _max,
                                   ui_zoom=getattr(self, "ui_zoom", None))
        # v3.9.66 — simpan kombinasi filter terakhir per tab (hanya bila
        # sesi ini pernah menjalankan pipeline — append1_df ada; menutup
        # app sebelum run TIDAK menimpa state tersimpan yang masih baik).
        with contextlib.suppress(Exception):
            if getattr(self, "append1_df", None) is not None:
                _save_filter_state(self._capture_filter_state())
        self.root.destroy()

    def _stop_pipeline(self):
        """Stop graceful — set stop_event, pipeline memeriksa di checkpoint."""
        if not self.is_running:
            return
        self.stop_event.set()
        self.is_running = False
        self.btn_stop.set_enabled(False)
        self.status_var.set("Status: menghentikan pipeline…")
        self.statusbar.set_status("menghentikan pipeline…", C_AMBER)
        self.kpi_status.set_value("MENGHENTIKAN…", "menunggu checkpoint", C_AMBER)
        self._append_log_batched(
            "\n[STOP] Permintaan stop dikirim. Pipeline akan berhenti "
            "di checkpoint berikutnya.\n")

    # =====================================================================
    # v3.9.37 — 🔄 REFRESH FILE SUMBER (selektif)
    # =====================================================================
    def _open_refresh_dialog(self):
        """Dialog pilih file sumber yang mau dibaca ulang (user: "ada
        tombol refresh untuk file sumber, bisa gak? dan gak harus
        refresh semua tapi"). File tak terpilih TIDAK dibaca ulang —
        bacaan cache-nya (fn_buka_sheet) yang dipakai."""
        if self.is_running:
            messagebox.showinfo(
                "Sedang Berjalan",
                "Pipeline sedang berjalan. Tunggu hingga selesai atau klik "
                "Stop.", parent=self.root)
            return
        worker = getattr(self, "worker_thread", None)
        if worker is not None and worker.is_alive():
            messagebox.showinfo(
                "Masih Menghentikan",
                "Pipeline sebelumnya masih berhenti di checkpoint.\n"
                "Tunggu sampai status berubah, lalu refresh lagi.",
                parent=self.root)
            return
        if not CONFIG_PATH.exists():
            messagebox.showerror(
                "Config Tidak Ada",
                f"config.json tidak ditemukan:\n{CONFIG_PATH}",
                parent=self.root)
            return
        try:
            from src.config import Config
            cfg = Config(str(CONFIG_PATH))
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            # OSError: file hilang/tak terbaca; ValueError: JSON rusak;
            # RuntimeError/KeyError: config.json tak lengkap (pesan
            # Indonesia v3.9.33 — ditampilkan ke user).
            messagebox.showerror(
                "Config Error",
                f"Tidak bisa membaca config.json:\n{exc}",
                parent=self.root)
            return
        try:
            RefreshSourcesDialog(
                self.root, cfg,
                last_run_at=self._last_run_finished_at,
                on_refresh=self._refresh_sources,
                can_refresh=self._can_refresh_now)
        except Exception as exc:  # defensive — dialog jangan matikan app
            messagebox.showerror(
                "Refresh Sumber",
                f"Gagal membuka dialog:\n{exc}", parent=self.root)

    def _can_refresh_now(self) -> bool:
        """v3.9.46 — audit 66 temuan #4: gate utk dialog 🔄 Refresh (dicek
        SEBELUM dialog menutup diri + SEBELUM cache diinvalidasi): pipeline
        hidup / masih menghentikan → False. Guard _refresh_sources dan
        _start_pipeline tetap ada sebagai lapis pertahanan berikutnya
        (race kecil antara cek ini dan eksekusi callback tetap tertutup)."""
        if self.is_running:
            return False
        worker = getattr(self, "worker_thread", None)
        return not (worker is not None and worker.is_alive())

    def _refresh_sources(self, paths):
        """Callback dialog 🔄 Refresh File Sumber: invalidasi cache bacaan
        (paths=None → SEMUA; list → file terpilih) lalu jalankan pipeline
        refresh mode (tetap di tab aktif; hanya file yang diinvalidasi
        dibaca ulang dari disk).

        v3.9.46 — audit 66 temuan #4: status pipeline di-RE-CHECK TEPAT
        SEBELUM invalidasi cache (dulu hanya dicek saat dialog DIBUKA +
        di _start_pipeline — celah: dialog hanya transient (bukan modal),
        user bisa memulai pipeline dari jendela utama selama dialog terbuka
        → _refresh_sources membuang cache DULU → _start_pipeline menolak
        → cache ter-invalidasi tanpa refresh + dialog sudah tertutup,
        user tak tahu refresh tidak jalan). Kini: pipeline hidup → cache
        TIDAK dibuang + pesan jelas; dialog juga modal (grab_set) supaya
        jendela utama tak bisa memulai pipeline saat dialog terbuka;
        guard _start_pipeline tetap sebagai lapis terakhir."""
        # v3.9.46 — guard SEBELUM invalidasi cache (audit 66 #4)
        if self.is_running:
            messagebox.showinfo(
                "Sedang Berjalan",
                "Pipeline sedang berjalan — cache bacaan TIDAK dibuang dan "
                "refresh DIBATALKAN.\n\nTunggu hingga selesai atau klik "
                "Stop, lalu buka ↻ Refresh Sumber lagi.",
                parent=self.root)
            return
        worker = getattr(self, "worker_thread", None)
        if worker is not None and worker.is_alive():
            messagebox.showinfo(
                "Masih Menghentikan",
                "Pipeline sebelumnya masih berhenti di checkpoint — cache "
                "bacaan TIDAK dibuang.\n\nTunggu sampai status berubah, "
                "lalu buka ↻ Refresh Sumber lagi.",
                parent=self.root)
            return
        n = read_cache_invalidate(paths)
        if paths is None:
            self._append_log_batched(
                f"\n[REFRESH] Cache baca dibuang SEMUA ({fmt_int_id(n)} "
                "entry) — semua file sumber dibaca ulang dari disk.\n")
        elif n:
            self._append_log_batched(
                f"\n[REFRESH] {fmt_int_id(n)} bacaan file terpilih "
                "dibuang — file itu akan dibaca ulang dari disk.\n")
        else:
            self._append_log_batched(
                "\n[REFRESH] File terpilih belum punya bacaan cache — "
                "akan dibaca saat pipeline berjalan.\n")
        # refresh_files: None = refresh SEMUA; list = refresh TERPILIH
        self._start_pipeline(refresh_files=paths)

    def _export_excel(self):
        """Export data (Append1 + Rincian PO + Rincian IN) ke Excel — async + loading."""
        # FIX 6a-03: guard kini juga menolak df KOSONG (bukan hanya None),
        # untuk SEMUA dataset alur export (Append1 / Rincian PO / Rincian
        # IN / Audit). Pipeline "sukses" pada folder kosong menghasilkan
        # DataFrame KOSONG (bukan None) → guard lama lolos → workbook
        # TANPA sheet → openpyxl IndexError mentah ("At least one sheet
        # must be visible") + file korup tertinggal di path user. Kini:
        # pesan ramah + TIDAK ADA file dibuat (dialog simpan pun tidak
        # dibuka — tiap sheet punya guard .empty sendiri di work()).
        def _ada_baris(df):
            return df is not None and not df.empty

        _audit_df = (self.audit_result.get("df")
                     if self.audit_result else None)
        if not (_ada_baris(self.append1_df)
                or _ada_baris(self.rincian_po_df)
                or _ada_baris(self.in_detail_df)
                or _ada_baris(_audit_df)):
            _pesan = ("Tidak ada baris untuk di-export — data yang "
                      "tersimpan kosong (lihat log tab Proses)."
                      if (self.append1_df is not None
                          or self.rincian_po_df is not None)
                      else "Belum ada data. Jalankan pipeline dulu.")
            messagebox.showwarning("Export", _pesan, parent=self.root)
            return
        # v3.9.59 — FIX 2f-10: nama file default ber-timestamp (pola pivot
        # 'pivot_{mode}_{YYYYmmdd_HHMM}.xlsx') — dulu hanya pivot yang
        # ber-stempel, jalur utama menimpa export sebelumnya secara default.
        filepath = filedialog.asksaveasfilename(
            title="Simpan sebagai Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=("stock_monitoring_"
                         f"{time.strftime('%Y%m%d_%H%M')}.xlsx"),
        )
        if not filepath:
            return

        append1_df = self.append1_df
        rincian_po_df = self.rincian_po_df
        in_detail_df = self.in_detail_df
        audit_df = self.audit_result.get("df") if self.audit_result else None

        # loading overlay di tengah jendela utama (dibuat lazily)
        if not hasattr(self, "_export_overlay"):
            self._export_overlay = LoadingOverlay(self.root,
                                                  "Mengekspor ke Excel…")
        self._export_overlay.show("Mengekspor ke Excel…", delay_ms=0)
        self.btn_export.set_enabled(False)
        self.btn_export_tb.set_enabled(False)

        def work():
            # FIX 6a-02: tulis ke file SEMENTARA satu folder dgn tujuan —
            # pandas ExcelWriter.__exit__ memanggil close() TAK-BERSYARAT
            # (workbook TETAP disimpan walau blok with gagal di tengah) →
            # menulis langsung ke path tujuan meninggalkan .xlsx PARSIAL/
            # KORUP yang MENIMPA export LAMA yang baik di path sama.
            # Kini file tujuan hanya tersentuh os.replace() atomik SETELAH
            # sukses penuh; kegagalan apa pun (finally) menghapus tmp.
            # (tmp ber-ekstensi .xlsx — pandas ExcelWriter menolak
            # ekstensi non-Excel seperti ".tmp".)
            tmp_path = filepath + ".tmp.xlsx"
            _ok = False
            try:
                with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                    # v3.8: sheet PIVOT ditulis DULU → jadi tab pertama
                    # (matrix mutasi barang + conditional formatting ala
                    # tab pivot "Mutasi Barang - New" user)
                    add_pivot_sheet(writer, append1_df)
                    if append1_df is not None and not append1_df.empty:
                        append1_df.to_excel(writer, sheet_name="Append1",
                                            index=False)
                    if rincian_po_df is not None and not rincian_po_df.empty:
                        # v3.9.19 (paritas UI): kolom "Nama Resto" — derivasi
                        # sama dgn rincian_po_view (Cabang PO → kode resto,
                        # rsplit titik terakhir; tanpa Cabang PO → "") —
                        # disisipkan tepat setelah Tanggal. Baris tanpa kode
                        # Cabang PO (parent tak terisi / NA) → "".
                        po_export = rincian_po_df.copy()
                        nama_resto = (po_export["Cabang PO"].map(_resto_name)
                                      if "Cabang PO" in po_export.columns
                                      else "")
                        po_cols = list(po_export.columns)
                        pos = (po_cols.index("Tanggal") + 1
                               if "Tanggal" in po_cols else 0)
                        po_export.insert(pos, "Nama Resto", nama_resto)
                        po_export.to_excel(writer, sheet_name="Rincian PO",
                                           index=False)
                    # v3.4: detail IN per dokumen (42.05/32.24/99.01 + nomor)
                    if in_detail_df is not None and not in_detail_df.empty:
                        in_detail_df.to_excel(writer, sheet_name="Rincian IN",
                                              index=False)
                    # v3.5: hasil Audit Rekonsiliasi (port macro VBA)
                    if audit_df is not None and not audit_df.empty:
                        audit_df.to_excel(
                            writer, sheet_name="Laporan Deviasi (Audit)",
                            index=False)
                os.replace(tmp_path, filepath)
                _ok = True
                return filepath
            finally:
                if not _ok:
                    # FIX 6a-02: gagal mid-write → tmp (parsial — bisa
                    # tersimpan paksa oleh __exit__ pandas) DIHAPUS; file
                    # tujuan TIDAK PERNAH tertinggal parsial/korup.
                    with contextlib.suppress(OSError):
                        os.unlink(tmp_path)

        def done(path):
            # FIX 6a-01: re-enable via sync (kriteria ketersediaan data
            # sama dgn guard export — dulu hanya cek append1_df: export
            # data rincian-PO-saja meninggalkan tombol mati selamanya).
            self._sync_export_buttons()
            # v3.9.59 — FIX 2f-09: tawarkan buka folder lokasi file (dulu
            # user harus menelusuri path manual di Explorer).
            if messagebox.askyesno(
                    "Export Berhasil",
                    f"Data di-export ke:\n{path}\n\nBuka folder lokasi "
                    "file?", parent=self.root):
                _open_folder_in_file_manager(
                    os.path.dirname(os.path.abspath(path)))

        def on_error(e):
            self._sync_export_buttons()   # FIX 6a-01 (lihat done())
            # v3.9.59 — FIX 2f-09: detail teknis ke LOG konsol; user diberi
            # pesan Indonesia yang actionable — file terkunci (masih
            # dibuka Excel) dulu tampil sebagai exception mentah English.
            self._append_log_batched(f"\n[ERROR] Export gagal: {e!r}\n")
            if _is_file_locked_error(e):
                messagebox.showerror(
                    "Export Gagal",
                    "File sedang dibuka (Excel?) — tutup dulu lalu "
                    f"ulangi.\n\nPath: {filepath}", parent=self.root)
            else:
                messagebox.showerror(
                    "Export Gagal", f"Tidak bisa export:\n{e}",
                    parent=self.root)

        run_async(self.root, work, done, overlay=self._export_overlay,
                  loading_text="Mengekspor ke Excel…", on_error=on_error)

    # =====================================================================
    # TAB LAIN (view)
    # =====================================================================
    def _build_pivot_tab(self):
        self.pivot_view = PivotTableView(
            self.tab_pivot, go_to_proses=self._go_to_proses_tab)
        self.pivot_view.pack(fill="both", expand=True)

    def _build_deviasi_gr_tab(self):
        # v3.9: tab GR = satu-satunya pemegang input H + Apply H
        self.deviasi_gr_view = DeviasiView(
            self.tab_deviasi_gr, satuan_mode="GR",
            go_to_proses=self._go_to_proses_tab,
            followup_store=self.followup_store,
            shared_cache=self._deviasi_pivot_cache,
            h_state=self._shared_h, h_editable=True,
            acr_state=self._shared_acr,   # v3.9.21 — ambang ACR bersama
            # v3.9.53 — Dev. Bulan Lalu: file deviasi aktif (tab ⚖ Komparasi)
            # via lalu_provider (pola nominal_resto v3.9.36 — lambda selalu
            # membaca _file_df AKTIF; file berganti → _on_dev_file_loaded
            # memanggil on_lalu_file_changed).
            lalu_provider=lambda: getattr(
                self.komparasi_view, "_file_df", None))
        self.deviasi_gr_view.pack(fill="both", expand=True)

    def _build_deviasi_pcs_tab(self):
        # v3.9: tab PCS TANPA input H — ikut H bersama dari tab GR
        # (chip read-only + auto-refresh saat H di-apply di tab GR)
        self.deviasi_pcs_view = DeviasiView(
            self.tab_deviasi_pcs, satuan_mode="PCS",
            go_to_proses=self._go_to_proses_tab,
            followup_store=self.followup_store,
            shared_cache=self._deviasi_pivot_cache,
            h_state=self._shared_h, h_editable=False,
            acr_state=self._shared_acr,   # v3.9.21 — ambang ACR bersama
            lalu_provider=lambda: getattr(
                self.komparasi_view, "_file_df", None))   # v3.9.53
        self.deviasi_pcs_view.pack(fill="both", expand=True)

    def _build_in_selisih_tab(self):
        """v3.4 — tab 📤 Rekap Selisih IN (drill-down rincian dokumen IN)."""
        self.in_selisih_view = InSelisihView(
            self.tab_in_selisih,
            go_to_proses=self._go_to_proses_tab)
        self.in_selisih_view.pack(fill="both", expand=True)

    def _build_laporan_tab(self):
        # v3.9.4: tab 📋 Laporan Deviasi = 2 MODE via SegmentBar:
        # ⚖ Komparasi File Deviasi (default — v3.9.4) & 🚨 Anomali COM
        # (v3.9.3, H bersama chip read-only + auto-refresh dari tab GR).
        # v3.9.32: mode ke-3 💰 Nominal (H) — Harga 41.09 × Qty Deviasi
        # per pasangan + baris TOTAL (user: "tab baru Nominal = Harga ×
        # kuantitas deviasi, per barang + total").
        self._laporan_container = tk.Frame(self.tab_laporan, bg=C_BG)
        self._laporan_container.pack(fill="both", expand=True)

        bar = tk.Frame(self._laporan_container, bg=C_BG)
        bar.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(bar, text="MODE", bg=C_BG, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 6))
        self.laporan_segment = SegmentBar(
            bar, ["⚖ Komparasi File Deviasi", "🚨 Anomali COM (H)",
                  "💰 Nominal (H)"],
            command=lambda idx: self.show_laporan_mode(idx))
        self.laporan_segment.pack(side="left")

        self.komparasi_view = KomparasiDeviasiView(
            self._laporan_container,
            go_to_proses=self._go_to_proses_tab,
            followup_store=self.followup_store,
            initial_dir=(self.rootpath_var.get().strip()
                         if getattr(self, "rootpath_var", None) is not None
                         else ""),
            h_state=self._shared_h,   # v3.9.7: filter minggu file
            # v3.9.36 — file deviasi berganti → segarkan kolom Bulan
            # Lalu popup tab 🧮 Nominal Deviasi (pola listener H).
            on_file_loaded=self._on_dev_file_loaded)
        self.laporan_view = LaporanDeviasiView(
            self._laporan_container,
            go_to_proses=self._go_to_proses_tab,
            followup_store=self.followup_store,
            h_state=self._shared_h)
        # v3.9.32 — mode Nominal: Harga × Qty Deviasi (+ baris TOTAL)
        self.nominal_view = NominalDeviasiView(
            self._laporan_container,
            go_to_proses=self._go_to_proses_tab,
            h_state=self._shared_h)
        # default: mode 0 (Komparasi) — COM & Nominal tersembunyi
        self.komparasi_view.pack(fill="both", expand=True)
        self.laporan_view.pack_forget()
        self.nominal_view.pack_forget()

    def show_laporan_mode(self, idx: int):
        """v3.9.4 — ganti mode tab 📋 Laporan Deviasi (dipakai SegmentBar
        & test): 0 = ⚖ Komparasi File, 1 = 🚨 Anomali COM,
        2 = 💰 Nominal (v3.9.32).
        v3.9.5 FIX (audit 19-c #7): sinkronkan SegmentBar (set_active_silent)
        — dulu pemanggilan programatik membuat segment.active basi →
        _on_tab_changed me-refresh pane yang SALAH & tombol mode tetap
        menyala di posisi lama."""
        if idx not in (0, 1, 2):
            idx = 0
        self.laporan_segment.set_active_silent(idx)
        # v3.9.66 — mode terakhir direkam utk filter persist (key
        # '_app.laporan_mode' — dipulihkan _apply_saved_filters_once).
        self._laporan_mode_idx = idx
        # lepas semua pane lalu pack pane aktif (urutan pack konsisten)
        self.laporan_view.pack_forget()
        self.nominal_view.pack_forget()
        self.komparasi_view.pack_forget()
        if idx == 0:
            self.komparasi_view.pack(fill="both", expand=True)
            self.komparasi_view.ensure_refreshed()
        elif idx == 2:
            self.nominal_view.pack(fill="both", expand=True)
            self.nominal_view.ensure_refreshed()
        else:
            self.laporan_view.pack(fill="both", expand=True)
            self.laporan_view.ensure_refreshed()

    def _on_dev_file_loaded(self):
        """v3.9.36 — file deviasi (tab ⚖ Komparasi) berubah: load baru /
        ditutup. Tab 🧮 Nominal Deviasi memakai file itu sebagai sumber
        kolom 'Nominal Deviasi Bulan Lalu' popup rincian → snapshot-nya
        basi → segarkan (pola listener SharedTanggalH; tab tersembunyi
        cukup ditandai dirty — refreshed saat dibuka).

        v3.9.53 — tab 📦 Deviasi GR & 🧩 PCS IKUT: kolom 'Dev. Bulan Lalu'
        + analisa CEK lalu-kini bersumber file yang sama → on_lalu_file
        _changed (clear cache pivot — identitas file bagian kunci — +
        refresh/dirty; user: "Deviasi bulan lalu ... pakai nilai asli")."""
        nr = getattr(self, "nominal_resto_view", None)
        if nr is not None:
            nr.on_lalu_file_changed()
        for dv in (getattr(self, "deviasi_gr_view", None),
                   getattr(self, "deviasi_pcs_view", None)):
            if dv is not None:
                with contextlib.suppress(Exception):
                    dv.on_lalu_file_changed()

    def _build_nominal_resto_tab(self):
        """v3.9.34 — tab 🧮 Nominal Deviasi: Σ (Harga 41.09 × Qty
        Deviasi) per resto + TOTAL + double-click resto → rincian per
        barang (user: "ada tab nominal Deviasi, isinya total sum dari
        nama barang kayak di laporan sampel kolom nominal deviasi, yang
        dapat dari harga × kuantitas deviasi, cuman ini disum per
        resto").

        v3.9.36 — lalu_provider: sumber kolom 'Nominal Deviasi Bulan
        Lalu' popup = file deviasi tab ⚖ Komparasi (komparasi_view.
        _file_df — referensi DIGANTI tiap load, jadi lambda ini selalu
        membaca file aktif; pembaruan dipicu on_file_loaded →
        _on_dev_file_loaded)."""
        self.nominal_resto_view = NominalRestoView(
            self.tab_nominal_resto,
            go_to_proses=self._go_to_proses_tab,
            h_state=self._shared_h,
            lalu_provider=lambda: getattr(
                self.komparasi_view, "_file_df", None))
        self.nominal_resto_view.pack(fill="both", expand=True)

    def _build_followup_tab(self):
        self.followup_view = FollowUpView(
            self.tab_followup, self.followup_store,
            get_data=lambda: self.append1_df,
            go_to_proses=self._go_to_proses_tab)
        self.followup_view.pack(fill="both", expand=True)
        # badge tab ikut berubah saat daftar berubah
        self.followup_store.add_listener(
            lambda _s: self.root.after(0, self._update_followup_badge))

    def _build_rincian_tab(self):
        self.rincian_view = RincianPoView(
            self.tab_rincian,
            go_to_proses=self._go_to_proses_tab)
        self.rincian_view.pack(fill="both", expand=True)


# --- Entry point ------------------------------------------------------------
# v3.9.46 — DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (handle -4) utk
# SetProcessDpiAwarenessContext; DPIAwareness(2) = PER_MONITOR_DPI_AWARE v1.
_DPI_PMV2_CTX = -4
_DPI_PER_MONITOR_AWARE = 2


def _windows_dpi_awareness_chain(windll) -> str:
    """v3.9.46 — audit 66 temuan #2: rantai pemilihan DPI-awareness Windows
    (PURE — menerima objek windll duck-typed supaya bisa diuji di Linux
    dengan stub; return label mode yang BERHASIL, "" bila semua gagal).

    Urutan (rekomendasi Microsoft — paling modern duluan):
      1. user32.SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)
         (Win10 1703+; BOOL — 0 = gagal, termasuk bila context lain
         sudah terpasang oleh manifest/proses lain)
      2. shcore.SetProcessDpiAwareness(PER_MONITOR_DPI_AWARE) (Win8.1+;
         HRESULT — 0 = S_OK)
      3. user32.SetProcessDPIAware() (system-aware, Win7; BOOL)

    Return code SETIAP API DIPERIKSA — kegagalan API Windows dilaporkan
    lewat HRESULT/BOOL, BUKAN exception (dulu `except` saja → gagal
    senyap dan kode mengira per-monitor aktif padahal tidak)."""
    # 1) per-monitor v2
    try:
        _rc = int(windll.user32.SetProcessDpiAwarenessContext(_DPI_PMV2_CTX))
        if _rc != 0:            # BOOL nonzero = sukses
            return "per-monitor-v2"
    except (AttributeError, TypeError, ValueError):
        pass
    # 2) per-monitor v1
    try:
        _hr = int(windll.shcore.SetProcessDpiAwareness(
            _DPI_PER_MONITOR_AWARE))
        if _hr == 0:            # HRESULT S_OK
            return "per-monitor"
    except (AttributeError, TypeError, ValueError):
        pass
    # 3) system-aware (fallback Win7)
    try:
        if int(windll.user32.SetProcessDPIAware()) != 0:
            return "system"
    except (AttributeError, TypeError, ValueError):
        pass
    return ""


def _set_windows_dpi_awareness() -> str:
    """v3.9.46 — audit 66 temuan #2: pasang DPI-awareness process, TANPA
    argumen root — HARUS dipanggil SEBELUM tk.Tk() (dokumentasi Microsoft:
    default DPI proses ditetapkan sebelum HWND pertama dibuat; dulu
    dipanggil SETELAH root = tk.Tk() → jendela sudah terinisialisasi dgn
    DPI lama).

    v3.9.47 — OPT-IN: fungsi ini hanya dipanggil bila config.json key
    "DpiAware" == true (default false — ukuran tampilan pra-v3.9.46
    dipertahankan; lihat _config_dpi_aware).

    Juga memperbaiki NILAI: komentar lama mengklaim per-monitor sambil
    memanggil SetProcessDpiAwareness(1) — nilai 1 = SYSTEM-DPI-aware.
    Kini benar-benar per-monitor (context -4 → awareness(2) → system).
    No-op (return "") di Linux/macOS. Mode yang terpasang di-return utk
    dicatat di log."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
    except ImportError:
        return ""
    try:
        with contextlib.suppress(Exception):
            # argtypes eksplisit: context adalah HANDLE (pointer-sized) —
            # tanpa ini int -4 dikonversi c_int 32-bit (tidak aman di x64)
            _fn = ctypes.windll.user32.SetProcessDpiAwarenessContext
            _fn.argtypes = [ctypes.c_void_p]
            _fn.restype = ctypes.c_int
        return _windows_dpi_awareness_chain(ctypes.windll)
    except Exception:
        # windll tak tersedia (Windows sangat tua / khusus) — aplikasi
        # tetap jalan (OS melakukan bitmap-scaling)
        return ""


def _config_dpi_aware() -> bool:
    """v3.9.47 → v3.9.48 — baca key "DpiAware" dari config.json.

    v3.9.48 — DEFAULT KINI TRUE (keluhan user: "kok program nya seperti
    tidak HD ya tampilan nya?"): proses DPI-unaware (default v3.9.47)
    selalu di-BITMAP-STRETCH Windows di layar scaling >100% → semua
    piksel direntangkan = KABUR. Kini default: proses DPI-aware =
    piksel 1:1 TAJAM, dgn ukuran fisik dipertahankan lewat KOMPENSASI
    GEOMETRI jendela (× fpixels/96 — StockMonitorApp.__init__) + tk
    scaling dari DPI monitor (v3.9.46) — kombinasi = tajam TANPA regresi
    ukuran yang dulu membuat v3.9.47 memilih opt-out. "DpiAware": false
    = opt-out eksplisit ke pipeline bitmap-stretch pra-v3.9.46 persis
    (kabur, ukuran identik piksel-ke-piksel — jalur darurat bila kompensasi
    tak cocok di mesin tertentu).

    Dibaca MENTAH (bukan lewat kelas Config — yang memvalidasi key
    wajib & bisa melempar RuntimeError): keputusan DPI harus tersedia
    SEBELUM tk.Tk() dan tak boleh tersandung masalah config lain
    (error config asli tetap dilaporkan app seperti biasa saat load
    pipeline). Penuh defensif: file hilang / JSON rusak / bukan dict /
    nilai bukan boolean true JSON → DEFAULT (True). STRICT `is True`
    (bukan bool()): string "false"/"true"/angka 1 tak sengaja ditulis
    user TIDAK dianggap aktif (bool("false") == True = jebakan klasik)
    — opt-in maupun opt-out harus boolean JSON eksplisit.
    Exception SPESIFIK (OSError + ValueError — cukup utk open+
    json.load: FileNotFoundError/PermissionError/JSONDecodeError/
    UnicodeDecodeError): bug kode lain tetap tersangkut crash
    handler main() (jujur), bukan ditelan senyap.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return True
        return data.get("DpiAware", True) is True
    except (OSError, ValueError):
        return True


def _apply_windows_tk_scaling(root: tk.Tk) -> None:
    """v3.9.46 — pasang tk scaling dari DPI aktual (dipisah dari
    _set_windows_dpi_awareness karena butuh root HIDUP; dipanggil SETELAH
    tk.Tk() dibuat). No-op di non-Windows.

    v3.9.47 — OPT-IN: hanya dipanggil bila config "DpiAware" == true
    DAN awareness berhasil terpasang (_dpi_mode != "") — tanpa itu,
    tk scaling TIDAK disentuh sama sekali (pipeline ukuran lama).
    """
    if sys.platform != "win32":
        return
    try:
        dpi = root.winfo_fpixels("1i")  # piksel per inci fisik
        if dpi > 0:
            root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


def main():
    # v3.9.42 — audit 61-c/61-d (F1 P2): startup TANPA try/except +
    # MULAI.bat memakai pythonw (tanpa konsol) → error sebelum redirect
    # stderr internal membuat aplikasi "tidak terbuka" TANPA pesan apa
    # pun (mati senyap). Kini: traceback ditulis ke crash.log (di samping
    # config.json — file satu-satunya jejak saat tanpa konsol) + dialog
    # ramah; `raise` tetap dijaga supaya exit code ≠ 0 (MULAI.bat
    # memakainya utk fallback python dgn traceback di konsol).
    root = None
    try:
        # v3.9.47 → v3.9.48 — DPI-AWARE KINI DEFAULT (fix "tampilan tidak
        # HD" — proses DPI-unaware selalu di-bitmap-stretch Windows di
        # layar scaling >100% = KABUR): "DpiAware" default TRUE = piksel
        # 1:1 tajam (SEBELUM jendela pertama, per dok Microsoft — audit
        # #2 v3.9.46) + tk scaling dari DPI monitor; REGRESI UKURAN
        # v3.9.46 dijawab KOMPENSASI GEOMETRI di StockMonitorApp.__init__
        # (jendela × fpixels/96 → ukuran FISIK = tampilan lama).
        # "DpiAware": false = opt-out eksplisit → TIDAK memanggil API
        # awareness sama sekali + TIDAK menyentuh tk scaling = pipeline
        # bitmap-stretch pra-v3.9.46 persis (kabur, ukuran lama).
        _dpi_mode = ""
        if _config_dpi_aware():
            _dpi_mode = _set_windows_dpi_awareness()
            if _dpi_mode:
                print(f"[DPI] Windows DPI awareness: {_dpi_mode} "
                      "(mode tajam 'DpiAware' default — ukuran fisik "
                      "dipertahankan via kompensasi geometri; CTRL+Scroll "
                      "= zoom 50–200%)")
        root = tk.Tk()
        if _dpi_mode:
            _apply_windows_tk_scaling(root)
        StockMonitorApp(root)
        root.mainloop()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        # crash.log di sebelah config.json (pythonw: tanpa konsol — file
        # satu-satunya jejak; pola suppress = repo, jangan masking error
        # asli dgn exception kedua saat crash handler sendiri bermasalah).
        with contextlib.suppress(Exception):
            _log = CONFIG_PATH.parent / "crash.log"
            _log.write_text(tb, encoding="utf-8")
        with contextlib.suppress(Exception):
            if root is None or not root.winfo_exists():
                root = tk.Tk()
                root.withdraw()
            from tkinter import messagebox
            messagebox.showerror(
                "Stock Monitoring — Gagal Memulai",
                "Terjadi error saat memulai aplikasi.\n\n"
                "Detail tersimpan di crash.log:\n" + tb[-600:])
        raise


if __name__ == "__main__":
    main()
