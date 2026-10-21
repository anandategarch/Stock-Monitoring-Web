"""
deviasi_view.py — Wide matrix view DEVIASI GR/PCS (v3.2 → v3.9).

v3.9.53 (user: "Deviasi bulan lalu yang ditampilkan di tab deviasi gr dan
pcs pakai nilai asli jangan pakai nilai absolute yang ditampilkan.
Absolute untuk perhitungan saja" + "Week sudah menyesuaikan kolom H di
tab deviasi GR dan PCS untuk Deviasi bulan lalu" + "kok ada nama barang
yang bukan kategori COM Deviasi + Packaging Deviasi misal BASKOM
STAINLESS 18 CM ... coba cek apa ini bug?"):
- KOLOM 'Dev. Bulan Lalu' GANTI SUMBER: DEV Lalu FILE deviasi resmi
  (tab ⚖ Komparasi — parse_deviasi_file via lalu_provider app, pola
  nominal_resto v3.9.36) — NILAI ASLI bertanda (minus = kekurangan,
  kurung merah; PLUS = surplus — bukan absolut), minggu pembanding
  MENYESUAIKAN H + bulan TERBARU file (parity hitung_nominal_lalu_pairs
  → angka PERSIS sama dgn kolom 'DEV Lalu' tab 📋 Laporan Deviasi —
  'sama seperti di tab laporan deviasi secara kuantiti'). Dulu
  v3.9.51-52: Σ 3.DEVIASI tgl negatif rekap lalu (cakupan rekap lalu
  hanya -25..-31 & nilai mentahnya tak sebanding angka resmi → tampak
  'nilai absolute'). Tanpa file → '-' + petunjuk status; ABSOLUTE tetap
  dipakai HANYA utk klasifikasi ANALISA CEK lalu→kini (|kini| vs |lalu|).
  Identitas file = bagian KUNCI SharedPivotCache (file berganti → cache
  miss otomatis) + on_lalu_file_changed (clear + refresh; dipanggil app
  _on_dev_file_loaded) + label 'WEEK n · bulan' dinyatakan di status.
- FILTER KATEGORI default GABUNGAN kini STRICT (hanya COM DEVIASI -
  RESTO + Biaya Packaging - RESTO — passthrough barang TANPA kategori
  dihapus; kelas 100383 tetap terlindungi kategori rekap v3.9.49 +
  entry '(Tanpa Kategori)' + jumlah tersembunyi dinyatakan di status).

v3.9.34 (user: "Nominal harusnya ada di Deviasi GR dan Deviasi PCS
juga itu tambah kolom baru dan hapus kolom BK_7 dan OUT_7 misal H = 7"):
- TAMBAH kolom "Nominal" tepat setelah Deviasi = Harga 41.09
  (dinormalkan ke satuan pasangan — helper bersama
  nominal_common.lookup_harga_pair) × Deviasi; barang tanpa harga /
  satuan tak ter-cover rasio → NaN → tampil '-' (transparan).
- HAPUS kolom display "Out_H" & "BK_H" (heading dinamis OUT_7/BK_7
  saat H=7); nilai internal TETAP dihitung (dipakai rumus internal
  Stok Seharusnya W = SO(H-1)+IN−BK−OUT & CEK — tidak tersentuh).

v3.9.33 — AUDIT FIX (48-b/48-d/48-e/48-f, fix 49-a):
- (P0) clone ⛶ basi: re-render/load_data MENUTUP semua clone hidup +
  generasi render dicatat di tree clone (klik ✓/double-click clone
  generasi lama diabaikan) — dulu klik ✓ clone basi men-toggle
  pasangan SALAH (persist followup.json).
- (P1) H=1/H=2: SO(H−1)/SO(H−2) kini membaca kunci −1 (saldo
  penutupan bulan lalu) — dulu kunci 0 (tak pernah ada) → selalu 0.
- (P1-LOW) saldo-only 42.17 saat H≤3: Sistem = saldo t=1 juga utk
  pasangan TANPA baris ('2.SALDO AKHIR', H) — fix v3.9.32 tak lagi
  inert (dulu Deviasi 0−0).
- (MEDIUM) pasangan IN-only ber-SATUAN NaN tidak lagi lenyap dari
  pivot_table (SATUAN NaN → "").
- (P1) sinkron ✓ lintas tab: listener FollowUpStore memperbarui sel
  ✓ tanpa re-render penuh.
- (UX) chip H tab PCS diberi petunjuk "atur di 📦 Deviasi GR"; 0 baris
  pasca-pipeline → empty state + status berpenjelasan aksi; panah sort
  dipasang ulang setelah _update_headings.

1 row per (Barang × Resto) di sekitar Tanggal H (H-2 … H+2) — logika
komputasi 100% identik versi lama (pivot + CEK anomaly detection), kini
VEKTORISASI numpy (tanpa iterrows — 5-10× lebih cepat).

v3.9.27 (user: "Kondisi beda tanggal kok menghasilkan data kosong semua?
cek file 01.1 CEK STOCK V2.xlsb bagian sheet Data Base Cek Deviasi
KOLOM Y. Sheet tersebut terhide. Cek semua logika nya dan bandingkan
dengan yang ada di program.") — CEK DI-PORT ULANG PERSIS formula LET
sheet terhide tsb. (nama variabel LET terlihat dari defined names
_xlpm.KondisiKosong/Naikturun/HitungManual/TurunDrastis/KondisiACR;
simulasi Python 2.120 baris atas nilai sel workbook = label kolom Y
cached 128/129 eksak — 1 beda = 1 baris gate, lihat bawah):
- Kondisi 2 "Beda Tanggal": J = "Out H" = KIRIMAN KELUAR (8.BARANG
  KELUAR app) — DARI 9.ACR/PENJUALAN (bug sejak port pertama; bukti
  MLGPAR/ADONAN GORENG MEKAR: sheet 'Beda Tanggal', app lama kosong).
- ATURAN SO-STALE v3.9.22 (tanggal SO nonzero terakhir < H) DIHAPUS —
  tidak ada di sheet; di data real men-flag pasangan ber-SO_H=0
  (baris 'data kosong') hingga mendominasi (H≥26: ~semua pasangan).
- Kondisi 3 "Hitung Manual": stok = W sheet = SO(H-1)+IN_H−KIRIMAN
  KELUAR_H−PENJUALAN_H (dulu sistem+IN−ACR−BK → 266 flag palsu).
- Stok Seharusnya (tampil) = W sheet (dulu SO(H-1)−ACR-rata2 → 794/
  1.405 baris beda dgn sheet; klaim verifikasi v3.9.6 keliru).
- GATE sheet IF(V="","",…) TIDAK direplikasi (V = Dev to BOM%:
  Total ACR=0 → V="" → sheet mengosongkan SELURUH CEK — 47% baris
  workbook; + kaskade #N/A saat tanggal di luar cakupan pivot sumber
  → 'data kosong semua' — persis gejala yang ditanyakan). App
  mengevaluasi kondisi apa adanya (lebih informatif; deviasi
  terdokumentasi di sini).
- Prioritas & label tak berubah: Promix 04 → RI Balancing →
  Kosong/Non Aktif → Beda Tanggal → Hitung Manual → Turun Drastis →
  ACR to BOM (kondisi app-only tetap: dua struktur dokumen di atas
  heuristik pola angka sheet).

v3.9.24 (klarifikasi user: "jika saat ini bulan oktober maka 1 periode
nya mulai dari 26 september - 25 oktober nah untuk cek RI balancing
berarti dengan NO. PO yang bukan bulan september dan oktober") —
definisi RI Balancing = PERIODE BISNIS 26→25 (dokumen tanggal-aware):
PO di luar dua bulan periodenya → flag; PO bulan sebelum RI = satu
periode → tidak (dulu salah-flag). Logika = doc_codes._ri_balancing
(nomor, po, tanggal) — tanggal dokumen dipakai utk batas 25/26.

v3.9.23 (user: "kerjakan poin 6") — CEK "RI Balancing" DI KOLOM UTAMA:
pasangan barang×resto yang punya ≥1 dokumen IN dgn PERIODE Nomor PO di
luar periode bisnis RI-nya (struktur PREFIKS.TAHUN.BULAN.NNNNN) dan tanggal
dokumen ≤ H kini TERFLAG "RI Balancing" langsung di tabel — dulu hanya
terlihat di popup Rincian IN (harus double-click baris per baris).
Sumber = in_detail (query_in, per-dokumen — pemetaan Nomor↔Nomor PO
bersih; frame final menggabungkan info kolom sehingga pemetaannya bisa
ter-campur). Prioritas np.select: Promix 04 → RI Balancing →
Kosong/Non Aktif → Beda Tanggal → Hitung Manual → Turun Drastis →
ACR to BOM (anomali struktural dokumen di atas heuristik pola angka;
"Beda Tanggal" stale mendominasi data real — di urutan terakhir RI
Balancing nyaris tak pernah tampil). Helper periode = doc_codes.py
(modul bersama, logika sama popup & Catatan Audit). Detail IN
diteruskan app.load_data → view ini; None (test/pemanggil lama) →
kondisi tidak berlaku (semua perilaku lama utuh).

v3.9.21 (2 permintaan user):
- AMBANG ACR to BOM yang BISA DIATUR (user: "di bagian ACR to BOM itu
  harusnya ada threshold > 80% absolute dan aku bisa atur"): CEK
  kondisi ke-5 kini |Deviasi| > (ambang/100) × Total ACR — dulu kaku
  > 100% × Total ACR. Ambang default 80, spinbox di kartu Filter KEDUA
  tab (GR & PCS) sinkron via SharedACRThreshold (pola SharedTanggalH),
  tersimpan di settings.json (bertahan lintas sesi); ubah ambang →
  pivot cache di-clear + refresh (CEK hidup di pivot ter-cache).
- CEK "Promix 04" PER-TANGGAL (fix user: "ada muncul nilai Promix 04 di
  filter tapi kenapa data nya tidak ada"): sumber SO kini dibaca dari
  baris 1.SO TANGGAL ANALISA H (append1 LANGKAH 9 resolve sumber per
  (pasangan × tanggal) atas baris rekap ber-NILAI non-nol — 'input so
  harian' menang atas promix pada tanggal sama; baris 0 = template
  kosong, tidak ikut menentukan). Label muncul HANYA bila SO tanggal H
  BENAR bersumber promix — tidak lagi pair-level race tanggal-tertinggi
  (dulu: v3.9.19 bisa melabel SEMUA pasangan campuran sbg Promix krn
  tie urutan baris; v3.9.20 swing kebalikan: tak pernah Promix meski
  SO tanggal H memang turunan promix).

v3.9.20 (deep audit 34-b/fix 35-b): _hl_cells di-init di __init__ (sort/
reapply tag sebelum render pertama tidak crash di Tk 9) +
_so_source_lookup keep-LAST sort-Tanggal (preferensi append1 LANGKAH 9)
+ _compute_cek (kode mati) dihapus.

v3.9.18 (permintaan user: "resto yang dianalisa hanya berfokus pada resto
yang ada di folder 1. DEVIASI WEEKLY aja jangan semua" + "look up nama
barang ini pakai dua arah ... tapi juga sebaliknya" + popup ringkas +
hapus 3 kolom + highlight 2 kolom):
- FOKUS RESTO rekap: pivot kini hanya memuat pasangan (barang × resto)
  yang RESTOnya punya data rekap berjalan (JENIS 1.SO / 5.BARANG MASUK
  dengan Tanggal POSITIF — data sheet '1  DEVIASI WEEKLY' folder
  "1. DEVIASI WEEKLY"/RekapBerjalan; rekap bulan lalu bernomor negatif
  dan berasal dari folder lain). Resto yang hanya ada di sumber app
  (32.24/42.05/9901/22.05/42.15) tanpa rekap → TIDAK dianalisa lagi
  (barisnya dulu menampilkan Deviasi = 0 − Sistem = minus palsu).
- LOOKUP BARANG DUA ARAH: barang TIDAK difilter — utk resto rekap,
  barang ber-SO rekap MAUPUN barang yang hanya ada di data app
  (IN/OUT/SALDO AKHIR saja, SO = 0) keduanya tetap tampil (arah
  rekap→app dan arah app→rekap).
- KOLOM DIHAPUS dari tampilan GR & PCS (permintaan user): Max Deviasi,
  ACR, Total ACR. HITUNGAN INTERNAL TETAP dihitung persis v3.9.6 —
  Total ACR & ACR tetap dipakai CEK kondisi ke-5 "ACR to BOM", Dev to
  BOM% (= Deviasi/Total ACR) dan Stok Seharusnya (v3.9.27 = W sheet:
  SO(H-1) + IN_H − KIRIMAN KELUAR_H − PENJUALAN_H)
  tetap tampil + tetap masuk snapshot Follow Up (loss_bom).
- HIGHLIGHT KOLOM Deviasi & SO_H (permintaan user: "highlight kolom
  deviasi dan kolom SO H"): latar lembut #fef3c7 (amber-100) di SEMUA
  sel kedua kolom via tag cell (Tk 9; terukur probe: bg cell-tag
  MENANG atas bg item-tag evenrow/oddrow, fg merah minus tetap hidup
  di atasnya). Fallback Tk 8: tanpa tint kolom (tag cell tak tersedia).
- DOUBLE-CLICK → POPUP RINGKAS (bukan lagi popup source rows): hanya
  Nama Barang · Nama Resto · Saldo Akhir · SO · IN · Deviasi per
  Tanggal (lihat deviasi_popup.py).

v3.9.19 (3 permintaan user utk tab GR/PCS):
- DEFAULT KATEGORI = "Deviasi" (case-insensitive; fallback "Semua"
  bila tidak ada) saat load data & ✕ Reset Filter.
- CEK kondisi ke-0 "Promix 04" (PRIORITAS PERTAMA): SOURCE DATA rekap
  JENIS SO (kolom SOURCE DATA sheet REKAP MENTAH — "input so harian" /
  "input promix 04 dine in" / "input promix 04 take away"; dibawa
  append1 merge per pasangan) BUKAN "input so harian" → CEK = Promix
  04 (SO turunan sistem — pola CEK lain tidak bermakna); tanpa SOURCE
  DATA → kondisi tidak berlaku.
- ISI FILTER HEADER = data yang ADA saja (Excel-like): daftar nilai
  dihitung dari baris yang tampil saat ini (mode Satuan + KATEGORI +
  filter kolom LAIN — kolom sendiri dikecualikan), bukan pivot mentah
  (dulu: PCS bisa menampilkan nilai CEK yang hanya ada di baris GR).

v3.9.6 (permintaan user: "tambah kategori Deviasi pada tab Deviasi PCS
dan GR" — mirror sheet DEVIASI GR/PCS workbook asli user):
- 5 KOLOM BARU setelah Rank: Max Deviasi (max |Deviasi| per barang,
  semua resto) · ACR (rata-rata penjualan harian = Σ 9.ACR tgl 1..H / H)
  · Total ACR (BOM per barang×resto = Σ penjualan 1..H) · Dev to BOM%
  (= Deviasi / Total ACR — "Loss Surplus to BOM" sheet Follow UP;
  formula terverifikasi nilai-per-nilai dari sheet DEVIASI GR asli) ·
  Stok Seharusnya (v3.9.27 = W sheet: SO(H-1)+IN_H−KIRIMAN KELUAR_H−
  PENJUALAN_H — perkiraan stok hari H; dulu SO(H-1)−ACR).
  (v3.9.18: 3 kolom pertama DIHAPUS dari tampilan — lihat atas.)
- CEK kondisi ke-5 "ACR to BOM": |Deviasi| > Total ACR > 0 → selisih
  stok melebihi pemakaian teoretis sebulan → pasti salah (melengkapi
  port formula LET yang sebelumnya "4 dari 5 kondisi — ACR butuh BOM,
  TODO"); string kategori sama persis sheet asli user.
- Parser sort Indonesia (_parse_num_id) utk semua kolom numerik +
  persen; minus merah per-cell di "Dev to BOM%" & "Stok Seharusnya".
- Snapshot follow-up diperluas (so_m2/so_m1/so_p1/so_p2/loss_bom) —
  bahannya format Follow Up "seperti file sample" (v3.9.6 followup_view).

Fitur v3.9 (permintaan user: "kolom apply H atau input H cukup 1 tab aja
dan berlaku di 2 tab yang berkaitan yaitu Deviasi Gr dan Deviasi PCS
sehingga tidak double input"):
- SharedTanggalH: TANGGAL H kini STATE BERSAMA antar tab Deviasi GR &
  PCS. Input + tombol "Apply H" hanya ada di tab 📦 Deviasi GR (tab
  pertama); tab 🧩 Deviasi PCS menampilkan nilai H (read-only chip) dan
  OTOMATIS ikut refresh saat H diubah — tidak ada double input.
- Tombol ⤢ "Perbesar" (ala Waste): ciutkan kartu Filter + judul +
  legenda supaya tabel memakai tinggi penuh; ⛶ Layar Penuh = window
  fullscreen.

Fitur v3.2 (dipertahankan):
- Kolom ✓ follow-up: klik sel ✓ = daftarkan/keluarkan baris ke tab
  ☑ Follow Up (ala repo Waste; persist followup.json)
- Lazy refresh: view hanya compute saat tab-nya terlihat (app memanggil
  ensure_refreshed saat tab dipilih)

Fitur v3.1 (dipertahankan):
- Filter Nama Barang menempel di header kolom (corong, Excel-like)
- Loading overlay + compute/render async (UI tidak membeku)
"""
import contextlib
import json
import logging
import os
import re
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

import numpy as np
import pandas as pd

from ..config import app_base_dir as _app_base_dir  # v3.9.62 — frozen-aware
from .doc_codes import ri_balancing_docs  # v3.9.23 (poin 6)
from .followup import CHECK_OFF, CHECK_ON, FollowUpStore, row_fingerprint
from .nominal_common import (  # v3.9.34 — Nominal; v3.9.51 — Rp; v3.9.53 — lalu file
    _norm_name_lalu,  # v3.9.53 — kunci pasangan file deviasi (mirror komparasi)
    _norm_resto_lalu,  # v3.9.53 — idem (sisi resto)
    dev_lalu_qty_map,  # v3.9.53 — Dev. Bulan Lalu kuantiti dari FILE deviasi
    fmt_rp_cell,
    lookup_harga_pair,
)
from .theme import (
    C_ACCENT,
    C_BG,
    C_CARD,
    C_HEADER,
    C_TEXT_MUTED,
    font,
    register_find_tags,
)
from .widgets import (
    CELL_TAGS_SUPPORTED,
    KATEGORI_BLANK_LABEL,  # v3.9.45 — entry khusus baris tanpa kategori master
    KATEGORI_DEFAULT_LABEL,  # v3.9.49 — entry gabungan default (rekap)
    Card,
    ColumnManager,
    EmptyState,
    GhostButton,
    HeaderFilterGroup,
    HeadingTintOverlay,  # v3.9.51 — strip warna header kolom In (kiriman)
    LegendRow,
    LoadingOverlay,
    TableExpander,
    _set_sort_arrow,  # v3.9.33 — AUDIT FIX (48-d): pasang ulang panah sort
    apply_cell_tag,
    apply_col_sel_restore,  # v3.9.66 — filter persisten antar sesi
    attach_clone_filters,
    auto_fit_columns,
    autofit_tree_once,  # v3.9.55 — F8: auto-fit sekali per muat data
    col_sel_to_json,  # v3.9.66 — filter persisten antar sesi
    enable_col_resize,
    enable_multi_select,
    fmt_int_id,
    identify_to_column,
    insert_tree_items,
    kategori_blank_mask,  # v3.9.44 — passthrough barang tanpa kategori master
    kategori_filter_mask,  # v3.9.49 — mask seleksi kategori gabungan
    kategori_has_default_values,  # v3.9.49 — entry default hanya bila ada di data
    kategori_passthrough,  # v3.9.45 — passthrough HANYA seleksi default
    open_tree_maximized,
    reset_autofit_once,  # v3.9.55 — F8
    run_async,
    sort_tree_by_column,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)

# FIX 6d1-06 — logger modul: kegagalan pivot_table tidak lagi ditelan
# senyap (kelas pola berulang #5) — penyebab di-log sebelum re-raise ke
# jalur on_error run_async.
_LOG = logging.getLogger("stock_monitoring.deviasi")


class SharedPivotCache:
    """Cache pivot Deviasi yang DIBAGI antar view GR & PCS (v3.3).

    _compute_pivot() tidak bergantung satuan (filter GR/PCS terjadi di
    _prepare_rows) — sebelumnya tab DEVIASI GR dan DEVIASI PCS masing-
    masing menghitung pivot identik 2× (waktu + memori ganda).

    v3.9: + lock — Apply H kini me-refresh GR & PCS BERSAMAAN (shared H);
    tanpa lock kedua thread bisa sama-sama cache-miss → compute dobel +
    entry tertimpa objek berbeda (tes "objek DataFrame sama" gagal
    intermiten). Dengan lock: 1 compute, pemakai kedua dapat objek sama.
    """

    def __init__(self):
        self._entry: tuple | None = None   # (data_ref, h, pivot_df, lalu_ref)
        self.lock = threading.Lock()

    def get(self, data, h, lalu=None):
        # v3.9.53 — identitas FILE deviasi (sumber kolom 'Dev. Bulan
        # Lalu') menjadi BAGIAN KUNCI: file berganti (load/tutup tab ⚖)
        # → otomatis miss → pivot dihitung ulang dgn file baru (entri
        # basi mustahil — tanpa ini pivot (data,h) lama terus di-hit).
        # Default lalu=None = perilaku lama (pemanggil tanpa file).
        ent = self._entry
        if (ent is not None and ent[0] is data and ent[1] == h
                and ent[3] is lalu):
            return ent[2]
        return None

    def put(self, data, h, pivot, lalu=None):
        self._entry = (data, h, pivot, lalu)

    def clear(self):
        self._entry = None


class SharedTanggalH:
    """State TANGGAL H yang DIBAGI antar tab Deviasi GR & PCS (v3.9).

    Permintaan user: input H cukup 1× dan berlaku di KEDUA tab — sebelumnya
    tiap tab punya entry H sendiri (harus input 2×, nilai bisa beda).

    - Tab 📦 Deviasi GR memegang input + tombol "Apply H" (satu-satunya
      jalur mengubah H).
    - Tab 🧩 Deviasi PCS berlangganan: saat H berubah, chip nilai H di UI
      diperbarui + view di-refresh (pivot cache dibagi, jadi hitung 1×).
    """

    def __init__(self, initial: int = 26):
        """v3.9.22: fallback awal 26 (user: "Tanggal harusnya tanggal 26
        bukan dari tanggal 25" — data rekap user kini sampai tanggal 26;
        setelah data dimuat nilai di-reset DINAMIS ke tanggal SO nonzero
        terakhir oleh DeviasiView.load_data)."""
        self._h = int(initial)
        self._listeners: list[Callable] = []

    @property
    def h(self) -> int:
        return self._h

    def subscribe(self, fn: Callable):
        """Daftarkan listener fn(new_h) — dipanggil tiap H berubah."""
        self._listeners.append(fn)

    def unsubscribe(self, fn: Callable) -> None:
        """v3.9.5 (audit 19-b #3): lepas listener — dipanggil saat view
        yang berlangganan di-destroy (mencegah listener zombie / callback
        ganda bila view direbuild)."""
        with contextlib.suppress(ValueError):
            self._listeners.remove(fn)

    def set(self, new_h: int) -> bool:
        """Ubah H + panggil SEMUA listener. Return True bila nilai berubah."""
        new_h = int(new_h)
        if new_h == self._h:
            return False
        self._h = new_h
        for fn in list(self._listeners):
            # listener view tidak boleh menjatuhkan pemanggil — telan error
            with contextlib.suppress(Exception):
                fn(new_h)
        return True


class SharedACRThreshold:
    """State AMBANG ACR to BOM (%) yang DIBAGI antar tab Deviasi GR & PCS
    (v3.9.21 — permintaan user: "di bagian ACR to BOM itu harusnya ada
    threshold > 80% absolute dan aku bisa atur").

    CEK "ACR to BOM" terpicu bila |Deviasi| > (ambang/100) × Total ACR —
    dulu kaku > 100% × Total ACR. Default 80; diatur 1..200 via spinbox
    di kartu Filter kedua tab (sinkron seperti TANGGAL H).

    Nilai dibaca/ditulis ke settings.json folder aplikasi (pola
    followup.json: atomic save; file hilang/korup → default 80 senyap).
    """

    def __init__(self, initial: float = 80.0):
        self._pct = float(initial)
        self._listeners: list[Callable] = []

    @property
    def pct(self) -> float:
        return self._pct

    def subscribe(self, fn: Callable):
        self._listeners.append(fn)

    def unsubscribe(self, fn: Callable) -> None:
        with contextlib.suppress(ValueError):
            self._listeners.remove(fn)

    def set(self, new_pct) -> bool:
        """Ubah ambang + panggil SEMUA listener. Return True bila berubah."""
        try:
            new_pct = float(new_pct)
        except (TypeError, ValueError):
            return False
        if not (1.0 <= new_pct <= 200.0) or new_pct == self._pct:
            return False
        self._pct = new_pct
        for fn in list(self._listeners):
            with contextlib.suppress(Exception):
                fn(new_pct)
        return True


# --- persistensi ambang ACR (settings.json — pola followup.json) ----------
# v3.9.62 — frozen-aware (app_base_dir): mode PyInstaller → folder .exe.
_SETTINGS_BASE = _app_base_dir()


def acr_settings_path() -> Path:
    return _SETTINGS_BASE / "settings.json"


def load_acr_threshold() -> float:
    """Ambang tersimpan (default 80.0 bila file hilang/korup/nilai di luar
    1..200 — senyap, tidak menjatuhkan app)."""
    try:
        with open(acr_settings_path(), "r", encoding="utf-8") as f:
            val = float(json.load(f).get("acr_threshold_pct", 80.0))
        return val if 1.0 <= val <= 200.0 else 80.0
    except (OSError, ValueError, TypeError, AttributeError):
        return 80.0


def save_acr_threshold(pct: float) -> None:
    """Simpan atomik (tmp → replace); kegagalan I/O senyap; key lain di
    settings.json dipertahankan (read-modify-write)."""
    p = acr_settings_path()
    old = {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            old = loaded
    except (OSError, ValueError, TypeError):
        old = {}
    try:
        old["acr_threshold_pct"] = round(float(pct), 2)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    except (OSError, ValueError, TypeError):
        return


class DeviasiView(tk.Frame):
    """Wide matrix view untuk DEVIASI GR/PCS.

    satuan_mode: "GR" → hanya SATUAN=GR
                 "PCS" → SATUAN selain GR (PCS, BOTOL, dll)
    """

    COLUMNS = [
        ("✓", 34, "center"),
        ("Resto", 70, "w"),
        ("Nama Barang", 180, "w"),
        ("Satuan", 50, "w"),
        # v3.9.29 — kolom KATEGORI DIHAPUS dari tabel (user: "hapus kolom
        # kategori di tab deviasi gr dan pcs karna sudah ada filter di
        # atasnya") — combobox KATEGORI di kartu Filter tetap; nilai tetap
        # hidup di pivot internal (filter post-pivot baris 1471).
        # v3.9.49 — kolom AKTIF/NON DIHAPUS dari tabel (user: "kolom Aktif
        # dan non aktif pindah ke bagian filter dekat kategori") — kini
        # combobox AKTIF/NON di kartu Filter (samping KATEGORI); nilai
        # tetap dihitung internal (CEK 'Kosong/Non Aktif' + snapshot
        # follow-up 'aktif' — baris dibangun dari cols_np, bukan COLUMNS).
        ("SO_H-2", 70, "e"),
        ("SO_H-1", 70, "e"),
        ("In_H-1", 70, "e"),
        ("SO_H", 70, "e"),
        ("In_H", 70, "e"),
        ("SO_H+1", 70, "e"),
        ("In_H+1", 70, "e"),
        ("SO_H+2", 70, "e"),
        ("Sistem", 80, "e"),
        ("Deviasi", 80, "e"),
        # v3.9.34 — kolom Nominal (Harga 41.09 × Deviasi) + Out_H/BK_H
        # dihapus dari tampilan (permintaan user; nilai internal TETAP
        # dihitung utk Stok Seharusnya W=SO(H-1)+IN−BK−OUT & CEK).
        ("Nominal", 100, "e"),
        ("Rank", 50, "e"),
        # v3.9.18 — kolom Max Deviasi / ACR / Total ACR DIHAPUS dari
        # tampilan (permintaan user); nilainya TETAP dihitung internal
        # (CEK "ACR to BOM" · Dev to BOM% · Stok Seharusnya ikut pakai).
        ("Dev to BOM%", 85, "e"),      # Deviasi / Total ACR (Loss Surplus to BOM)
        # v3.9.51 — "Stok Seharusnya" (W sheet, v3.9.27) DIHAPUS dari
        # TAMPILAN (user: "Stock seharusnya hide pada deviasi gr dan
        # deviasi pcs ganti dengan Deviasi bulan lalu sama seperti di
        # tab laporan deviasi secara kuantiti") — rumus W tetap dihitung
        # INTERNAL utk kondisi CEK-3 'Hitung Manual' (stok =
        # so_m1+in_h−bk_h−out_h, blok CEK di bawah).
        # v3.9.53 — sumber DIGANTI: DEV Lalu FILE deviasi (tab ⚖ Komparasi) —
        # nilai ASLI bertanda + minggu/bulan MENYESUAIKAN H (dulu Σ 3.DEVIASI
        # rekap lalu -25..-31 — cakupan terbatas, tak sebanding angka resmi).
        ("Dev. Bulan Lalu", 95, "e"),
        # v3.9.51 — CEK 120 → 210: label anomali + segmen analisa deviasi
        # lalu→kini (dipisah ' · ').
        ("CEK", 210, "w"),
    ]

    # v3.9.18 — kolom yang di-HIGHLIGHT latar lembut (permintaan user:
    # "highlight kolom deviasi dan kolom SO H") — tag cell Tk 9.
    HIGHLIGHT_COLS = ("Deviasi", "SO_H")
    HIGHLIGHT_BG = "#fef3c7"   # amber-100 — latar lembut, teks tetap terbaca

    # v3.9.61 — SEKAT WARNA KELOMPOK DIHAPUS (user: "hilangkan warna "
    # "untuk sekat visual tiap grup nama barang pada tab deviasi gr dan "
    # "deviasi pcs"): era v3.9.49-60 memakai pita latar grp0/grp1 bergantian
    # per kelompok Nama Barang (terakhir putih ↔ #9aa7b9). Kini baris
    # SELURUHNYA latar seragam (putih) — nama barang tetap PER-BARIS di
    # tiap baris (v3.9.60), kelompok tetap KONTIGU (sort default by
    # Nama Barang), pewarnaan afektif tersisa hanya teks fg (minus
    # merah/nol abu/label CEK) + highlight kolom Deviasi/SO_H. Konstanta
    # GRP_TAG_COLORS/_GRP_TAGS dan mesin _reapply_group_merge dihapus.

    CEK_THRESHOLD = 1.3

    # v3.9.51 — kolom In (kiriman — BUKAN kolom Stock/SO): header diberi
    # strip warna (user: "Header In_13 atau In 15 (Jika H = 14 contoh
    # nya) diberi warna beda biar aku tau itu bukan kolom Stock") —
    # HeadingTintOverlay (widgets) karena ttk tak punya bg per-heading.
    IN_COLS = ("In_H-1", "In_H", "In_H+1")
    IN_HEADER_COLOR = "#0e7490"   # teal-700 — beda dari latar heading & amber Deviasi/SO_H

    # v3.9.51 — ANALISA DEVIASI LALU→KINI di CEK (label = kata user;
    # klasifikasi mirror mode 📈 Analisa tab 📋 Laporan Deviasi).
    ANALISA_NAIK_TXT = "Peningkatan Tertinggi"
    ANALISA_TURUN_TXT = "Penurunan Tertinggi"
    ANALISA_ARAH_TXT = "Berubah Arah"

    # Toleransi 'Stabil' analisa lalu→kini (mirror TOL_ABS/TOL_REL
    # komparasi — selisih ≤ ini tak diberi label analisa).
    _LALU_TOL_ABS = 1.0
    _LALU_TOL_REL = 0.0001

    # v3.9.51 — 7 label anomali check kanonik (urutan np.select CEK):
    # pembanding hitungan 'CEK n' footer & pembeda dari segmen analisa.
    _CEK_CHECK_LABELS = (
        "Promix 04", "RI Balancing", "Kosong/Non Aktif", "Beda Tanggal",
        "Hitung Manual", "Turun Drastis", "ACR to BOM")

    # FIX 6d1-02 — counter load_data aktif (CLASS-level, dibagi antar
    # instance GR & PCS yang sama-sama berlangganan SharedTanggalH).
    # load_data memanggil _h_state.set(default-H-baru) SEBELUM filter
    # kategori/kolom/aktif di-reset → listener _on_shared_h_changed
    # (milik instance INI dan instance SAUDARA) me-render dengan state
    # filter LAMA → tabel kosong transien + status salah, lalu render
    # kedua dari akhir load_data (render ganda). Saat counter > 0 listener
    # hanya mensinkronkan state (chip/entry/cache) TANPA refresh — SATU
    # render benar di akhir load_data tiap view (pola antre _pending_sort).
    _load_depth = 0

    def __init__(self, parent, satuan_mode: str = "GR",
                 go_to_proses: Callable | None = None,
                 followup_store: FollowUpStore | None = None,
                 shared_cache: SharedPivotCache | None = None,
                 h_state: SharedTanggalH | None = None,
                 h_editable: bool = True,
                 acr_state: SharedACRThreshold | None = None,
                 lalu_provider: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.data: pd.DataFrame | None = None
        self.in_detail: pd.DataFrame | None = None   # v3.9.23 (poin 6)
        self._ri_bal_cache = None   # v3.9.23 — (df-id, h) → pasangan RI Bal
        self.satuan_mode = satuan_mode
        # v3.9: H dibagi GR & PCS — sumber nilai = SharedTanggalH bila ada
        self._h_state = h_state
        self._h_editable = h_editable
        # v3.9.22: fallback 26 (dynamics: di-reset oleh load_data ke
        # tanggal SO nonzero terakhir — lihat _default_h_from_data)
        self.tanggal_h = h_state.h if h_state is not None else 26
        # v3.9.21 — ambang ACR to BOM dibagi GR & PCS (persen |Deviasi| vs
        # Total ACR); tanpa acr_state (standalone/test) → 80.0.
        self._acr_state = acr_state
        self.acr_threshold = acr_state.pct if acr_state is not None else 80.0
        # v3.9.53 — Dev. Bulan Lalu: provider FILE deviasi resmi (app
        # meneruskan komparasi_view._file_df — pola lalu_provider
        # nominal_resto v3.9.36). None (standalone/test) → kolom '-' jujur.
        # File berganti → app memanggil on_lalu_file_changed (clear cache +
        # refresh — lihat _on_dev_file_loaded).
        self._lalu_provider = lalu_provider
        self._cached_pivot = None
        self._cached_h = None
        self._shared_cache = shared_cache   # dibagi GR & PCS (v3.3)
        # v3.9.34 — kolom Nominal: harga 41.09 + peta rasio dari pipeline
        # (audit_result['harga_map'] / ['konversi_map'] — diteruskan app
        # lewat load_data). Cache (barang, satuan) → harga_norm dibangun
        # sekali per data di _compute_pivot (reset di load_data — pola
        # _aktif_lookup).
        self.harga_map: dict = {}
        self.konversi_map: dict | None = None
        self._harga_pair_cache: dict | None = None
        self._aktif_lookup = {}
        # v3.9.13: lookup KATEGORI per barang (pola _aktif_lookup) + seleksi
        # combobox KATEGORI (None = "Semua" = tanpa filter).
        self._kategori_lookup = {}
        self._kategori_sel: str | None = None
        # v3.9.49 — filter AKTIF/NON (pindahan dari kolom tabel;
        # None = "Semua" = tanpa filter).
        self._aktif_sel: str | None = None
        self.go_to_proses = go_to_proses
        self._busy = False
        self._pending = False
        self._dirty = False                # lazy refresh (v3.2)
        self.store = followup_store       # shared FollowUpStore (v3.2)
        self._fp_map: dict[str, str] = {}     # iid → fingerprint
        self._row_snaps: dict[str, dict] = {}  # iid → snapshot raw (v3.2)
        # v3.9.51 — iid → rank TERFORMAT per baris; v3.9.65 — nilai
        # PER-BARIS rank dalam kelompok (semantik sheet asli — bukan
        # lagi konstanta per barang); dipakai sort/auto-fit/clone.
        self._rank_map: dict[str, str] = {}
        # v3.9.2: minus merah PER CELL (Tk 9 `tag cell`) — fallback Tk 8:
        # tag per baris (perilaku lama)
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []   # [(iid, 'Deviasi')] — dipasang ulang
                                     # setelah insert / sort / clone
        self._zero_cells: list = []  # [(iid, 'Deviasi')] deviasi == 0
        # v3.9.18 — highlight kolom Deviasi & SO_H. FIX 35-b (audit 34-b
        # RISK-1): WAJIB diinisialisasi di __init__ — _sort_by /
        # _reapply_cell_tags bisa jalan SEBELUM render pertama (clone ⛶ /
        # pemanggil program) → AttributeError di Tk 9 tanpa ini.
        self._hl_cells: list = []
        self._tnum = None                 # cache pd.to_numeric(Tanggal)
        self._tnum_data = None             # FIX D-01: identitas objek data milik _tnum
        # FIX B-08 (audit 2-b): sort saat render batch → ANTRE (bukan dibuang
        # senyap) — pola _pending_sort komparasi/laporan v3.9.5.
        self._pending_sort = None
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0) -------------------------------
        # Clone ⛶ basi: window clone memegang SALINAN baris saat dibuka
        # (iid identik dgn tabel utama). Saat view re-render, _fp_map/
        # _row_snaps DIGANTI → klik ✓ / double-click di clone lama
        # men-toggle pasangan SALAH (persist followup.json) & membaca
        # snapshot H salah. Kini: (1) setiap re-render MENUTUP semua
        # clone hidup, (2) generasi render dicatat di tree clone saat
        # dibuka — handler ✓/double-click mengabaikan clone generasi
        # lama (defense-in-depth).
        self._render_gen = 0
        self._clone_wins: list = []

        self._build_ui()
        self._setup_tags()
        # v3.9.33 — AUDIT FIX (48-e P1): sinkron ✓ lintas tab — baris
        # ditambah/dikeluarkan dari tab ☑ Follow Up (atau tab GR↔PCS)
        # memperbarui sel ✓ di sini TANPA re-render penuh (dulu sel
        # basi ☑ bertahan sampai render berikutnya). add_listener
        # idempoten (bound method dicek ==).
        if self.store is not None:
            self.store.add_listener(self._on_followup_store_changed)
        if self.data is not None:
            self._refresh()
        else:
            self._show_empty()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        mode_label = "GR" if self.satuan_mode == "GR" else "PCS / non-GR"

        # --- Empty state ---
        self.empty = EmptyState(
            self, icon="📦" if self.satuan_mode == "GR" else "🧩",
            title=f"Belum ada data Deviasi {mode_label}",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Konten utama ---
        self.content = tk.Frame(self, bg=C_BG)

        # (v3.2) KPI row DIHAPUS — tabel kini lebar & besar; ringkasan
        # (baris · total deviasi · anomali CEK) ada di status footer.

        # --- Filter card ---
        # v3.9: H diatur di tab GR (edit) / tab PCS chip read-only
        fcard = Card(self.content, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        self._fcard = fcard
        fbody = fcard.body()

        r0 = tk.Frame(fbody, bg=C_CARD)
        r0.pack(fill="x")
        # v3.5: RESTO combo DIHAPUS (duplikat → filter header kolom Resto ⧩)
        tk.Label(r0, text="TANGGAL H", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        if self._h_editable:
            self.tanggal_h_var = tk.StringVar(value=str(self.tanggal_h))
            tanggal_h_entry = ttk.Entry(r0, textvariable=self.tanggal_h_var,
                                        width=6)
            tanggal_h_entry.pack(side="left", padx=(6, 8))
            tanggal_h_entry.bind("<Return>",
                                 lambda e: self._on_tanggal_h_change())
            GhostButton(r0, text="Apply H",
                        command=self._on_tanggal_h_change).pack(
                side="left", padx=(0, 18))
        else:
            # v3.9: tab PCS tidak punya input H — chip read-only yang ikut
            # berubah saat H di-apply di tab Deviasi GR
            self._h_chip_var = tk.StringVar(value=str(self.tanggal_h))
            chip = tk.Frame(r0, bg="#f1f5f9", highlightbackground="#e2e8f0",
                            highlightthickness=1)
            chip.pack(side="left", padx=(6, 18))
            tk.Label(chip, textvariable=self._h_chip_var, bg="#f1f5f9",
                     fg=C_ACCENT, font=font(11, "bold")).pack(
                side="left", padx=(10, 0), pady=(2, 3))
            # v3.9.33 — AUDIT FIX (48-f UX): chip H read-only kini ber-
            # petunjuk di mana mengubahnya (dulu angka H berdiri sendiri
            # tanpa penjelasan — user tidak tahu harus ke tab GR).
            tk.Label(chip, text="· atur di 📦 Deviasi GR", bg="#f1f5f9",
                     fg=C_TEXT_MUTED, font=font(8)).pack(
                side="left", padx=(4, 10), pady=(2, 3))
        GhostButton(r0, text="✕ Reset Filter",
                    command=self._reset_filter).pack(side="left")

        # v3.9.13 — filter KATEGORI (user: "tambah filter kategori di tab
        # deviasi pcs dan gr"); diterapkan POST-PIVOT di _prepare_rows
        # supaya SharedPivotCache GR+PCS tetap dihitung 1×.
        # v3.9.49 — lebar combo dinaikkan (label entry gabungan default
        # kategori Rekap Mentah panjang: 'COM DEVIASI - RESTO + Biaya
        # Packaging - RESTO'). v3.9.55 — label gabungan kini RINGKA
        # 'Deviasi (COM + Packaging)' (user: "tambah kategorinya jadi 2 aja
        # dan default Deviasi") → lebar 34 cukup utk label + nilai DBS
        # terpanjang.
        r0b = tk.Frame(fbody, bg=C_CARD)
        r0b.pack(fill="x", pady=(6, 0))
        tk.Label(r0b, text="KATEGORI", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self._kategori_var = tk.StringVar(value="Semua")
        self._kategori_combo = ttk.Combobox(
            r0b, textvariable=self._kategori_var, state="readonly",
            width=34, font=font(9))
        self._kategori_combo.pack(side="left", padx=(6, 0))
        self._kategori_combo.bind(
            "<<ComboboxSelected>>", lambda e: self._on_kategori_changed())

        # v3.9.49 — filter AKTIF/NON (user: "kolom Aktif dan non aktif
        # pindah ke bagian filter dekat kategori aja"): kolom tabel
        # AKTIF/NON dihapus dari COLUMNS; combobox ini menggantikan fungsi
        # visibilitasnya. Nilai "Semua" default = perilaku tabel lama
        # (tak ada penyaringan); AKTIF / NON AKTIF = filter nilai master
        # (case-insensitive + strip — identik normalisasi CEK
        # 'Kosong/Non Aktif'); '(Kosong)' = barang tanpa status master
        # (kelas 100383 — pola entry '(Tanpa Kategori)').
        tk.Label(r0b, text="AKTIF/NON", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(18, 0))
        self._aktif_var = tk.StringVar(value="Semua")
        self._aktif_combo = ttk.Combobox(
            r0b, textvariable=self._aktif_var, state="readonly",
            width=12, font=font(9))
        self._aktif_combo["values"] = [
            "Semua", "AKTIF", "NON AKTIF", "(Kosong)"]
        self._aktif_combo.pack(side="left", padx=(6, 0))
        self._aktif_combo.bind(
            "<<ComboboxSelected>>", lambda e: self._on_aktif_changed())

        # v3.9.21 — AMBANG ACR to BOM (user: "di bagian ACR to BOM itu
        # harusnya ada threshold > 80% absolute dan aku bisa atur"):
        # CEK terpicu bila |Deviasi| > ambang% × Total ACR. Spinbox kedua
        # tab sinkron (SharedACRThreshold — pola TANGGAL H); ubah →
        # pivot cache dibersihkan + refresh (CEK hidup di pivot ter-cache).
        tk.Label(r0b, text="AMBANG ACR to BOM", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(18, 0))
        self._acr_var = tk.StringVar(value=str(int(self.acr_threshold))
                                     if float(self.acr_threshold).is_integer()
                                     else str(self.acr_threshold))
        acr_spin = ttk.Spinbox(
            r0b, textvariable=self._acr_var, from_=1, to=200,
            increment=1, width=5, font=font(9),
            command=self._on_acr_threshold_change)
        acr_spin.pack(side="left", padx=(6, 0))
        acr_spin.bind("<Return>", lambda e: self._on_acr_threshold_change())
        tk.Label(r0b, text="% ×BOM", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8)).pack(side="left", padx=(3, 0))

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        # Header tabel: judul + tombol perbesar
        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        mode_label = "GR" if self.satuan_mode == "GR" else "PCS / non-GR"
        title_label = tk.Label(
            head, text=f"Matrix Deviasi {mode_label} — CEK Anomaly",
            bg=C_CARD, fg=C_HEADER, font=font(10, "bold"))
        title_label.pack(side="left")
        # v3.9 (ala Waste): ⛶ = Layar Penuh (window terpisah)
        btn_max = GhostButton(head, text="⛶ Layar Penuh",
                              command=self._maximize)
        btn_max.pack(side="right")
        # v3.9 (ala Waste): ⤢ = Perbesar (in-place — ciutkan baris kontrol
        # supaya tabel memakai seluruh tinggi tab; v3.9.59 fix 2f-13 label
        # kanonik ⤢='Perbesar' — dulu '⤢ Perbesar Tabel')
        btn_expand = GhostButton(head, text="⤢ Perbesar")
        btn_expand.pack(side="right", padx=(0, 6))
        btn_cols = GhostButton(head, text="◱ Kolom",
                               command=lambda: self._colmgr.open_panel())
        btn_cols.pack(side="right", padx=(0, 6))
        btn_fit = GhostButton(head, text="↔ Auto-Fit", command=self._auto_fit)
        btn_fit.pack(side="right", padx=(0, 6))
        # v3.9.55 — TOMBOL SORT ANALISA CEK (user: "DI tab deviasi GR dan PCS
        # dan tombol buat sort kenaikan atau penurunan tertinggi berdasarkan
        # kolom CEK yang compare dengan file deviasi bulan lalu"): sortir
        # tabel oleh segmen analisa lalu→kini di teks CEK (kolom yang
        # membandingkan |Deviasi kini| vs |DEV Lalu file ⚖|).
        # ▲ Kenaikan: baris 'Peningkatan Tertinggi +p%' teratas (p% terbesar
        # dulu); ▼ Penurunan: 'Penurunan Tertinggi -p%' teratas (penurunan
        # terdalam dulu); 'Berubah Arah' di bawah baris ber-label; sisanya
        # (tanpa analisa) di ekor — urutan relatif lama dipertahankan.
        btn_sort_up = GhostButton(
            head, text="▲ Kenaikan Tertinggi",
            command=lambda: self._sort_analisa("naik"))
        btn_sort_up.pack(side="left", padx=(0, 6))
        btn_sort_down = GhostButton(
            head, text="▼ Penurunan Tertinggi",
            command=lambda: self._sort_analisa("turun"))
        btn_sort_down.pack(side="left")

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(tbody, columns=col_ids, show="headings",
                                 selectmode="extended")

        for col_name, width, anchor in self.COLUMNS:
            self.tree.column(col_name, width=width, minwidth=34, anchor=anchor)
            display = self._col_display_name(col_name)
            # v3.5: SEMUA kolom pakai filter header ⧩ (sort via popup);
            # ✓ tetap toggle follow-up via klik sel
            self.tree.heading(col_name, text=display)

        vsb = ttk.Scrollbar(tbody, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(0, weight=1)

        # v3.4: drag tepi heading = resize lebar kolom; double-click tepi =
        # auto-fit (dipasang SEBELUM HeaderFilter supaya "break" efektif)
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        # Footer: status
        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.status_var = tk.StringVar(value="Belum ada data.")
        # v3.9.59 — AUDIT FIX 2d-10: status real ±180-250 char, label
        # single-line pack side=right terpotong dari KIRI (jumlah baris/
        # Total |Deviasi| — info terpenting — hilang duluan). Kini label
        # TANPA textvariable: teks ditulis lewat trace status_var (var
        # tetap PENUH — status_var.get() dipakai assert test & flash)
        # dgn WRAP maks 2 baris + ekor '…' bila tak muat; wraplength
        # adaptif lebar footer (bind <Configure>). Baris pertama (KPI
        # utama) selalu utuh — yang terpotong segmen diagnostik ekor.
        self.status_label = tk.Label(foot, bg=C_CARD, fg=C_HEADER,
                                     font=font(8, "bold"), anchor="e",
                                     justify="right")
        self.status_label.pack(side="right", fill="x", expand=True)
        self._status_wrap = 760
        self.status_var.trace_add("write", self._on_status_var_write)
        foot.bind("<Configure>", self._on_foot_configure, add="+")
        self._on_status_var_write()

        # Loading overlay (stacking di atas tree)
        self.overlay = LoadingOverlay(tbody, "Menghitung deviasi…")

        # v3.5: filter header ⧩ di SEMUA kolom (kecuali ✓ = toggle)
        _filter_cols = [c[0] for c in self.COLUMNS if c[0] != "✓"]
        self._col_sel: dict = {c: None for c in _filter_cols}
        self.header_filters = HeaderFilterGroup(
            self.tree, _filter_cols,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        # v3.6: hide/unhide kolom (klik kanan heading / tombol ◱ Kolom)
        # v3.9.52 — SATUAN disembunyikan SEJAK AWAL di tab Deviasi GR & PCS
        # (user: "Secara default hide kolom Satuan di tab Deviasi Gr dan
        # PCS"): di tab GR nilainya seragam 'GR' (redundan), di PCS pun
        # mode-nya sudah ditentukan tab — kolom tetap bisa di-unhide via
        # ◱ Kolom / klik kanan; NILAI tetap hidup (snapshot follow-up,
        # popup rincian, filter mode Satuan — displaycolumns hanya soal
        # tampilan; clone ⛶ menyalin displaycolumns sumber).
        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filters.open_popup(c),
            default_hidden=["Satuan"])

        # v3.9.55 — AUTO-FIT MERGE-AWARE: era merge-vertikal nilai baris
        # lanjutan BLANK → pengukuran sampel auto_fit_columns bisa
        # kehilangan nama terpanjang. v3.9.60 nilai kembali PER-BARIS
        # (override redundant-by-design — tetap dipakai supaya pengukuran
        # membaca nilai RAW snapshot/_rank_map apa pun state display).
        # v3.9.56 — getter jadi METHOD bersama (_merge_value_get): dipakai
        # juga filter clone ⛶ (value_get attach_clone_filters — nilai RAW
        # supaya kelompok utuh lolos filter by Nama Barang/Rank).
        self.tree._autofit_value_get = self._merge_value_get

        # v3.9.51 — strip warna header kolom In (kiriman — BUKAN Stock):
        # In_H-1 / In_H / In_H+1 (heading dinamis In_13/In_14/In_15 saat
        # H=14) — ttk tak punya background per-heading → overlay strip
        # tipis 6px di atas heading (teks & corong ⧩ tak tertutup).
        self._in_tint = HeadingTintOverlay(
            self.tree, list(self.IN_COLS), self.IN_HEADER_COLOR)

        # v3.9.60 — NILAI PER-BARIS: Nama Barang & Rank ditulis payload di
        # SETIAP baris kelompoknya, TANPA widget tambahan & TANPA state
        # display yang bisa basi (era sticky v3.9.55-59 dihapus — lihat
        # komentar _prepare_rows). v3.9.65 — nilai Rank kini PER-BARIS
        # (rank |Deviasi| dalam kelompok — semantik sheet asli).
        # v3.9.61 — sekat warna kelompok dihapus (baris seragam putih).

        # Legend CEK
        legend = LegendRow(self.content, [
            ("Promix 04", "#0e7490"),     # v3.9.19 — kondisi ke-0
            ("RI Balancing", "#92400e"),  # v3.9.23 (poin 6) — kondisi ke-1
            ("Kosong/Non Aktif", "#b45309"),
            ("Beda Tanggal", "#2563eb"),
            # v3.9.59 — AUDIT FIX 2d-04: swatch disinkronkan ke warna
            # render tag cek_manual #c2410c (fix kontras v3.9.50 — dulu
            # legend masih #ea580c → pemetaan warna legenda ≠ warna sel).
            ("Hitung Manual", "#c2410c"),
            ("Turun Drastis", "#dc2626"),
            ("ACR to BOM", "#7c3aed"),   # v3.9.6 — kondisi ke-5
            ("negatif (merah)", "#dc2626"),
            # v3.9.18 — highlight kolom Deviasi & SO_H
            ("kolom Deviasi/SO_H", self.HIGHLIGHT_BG),
            # v3.9.51 — strip header kolom In (kiriman — bukan Stock)
            ("header kolom In (kiriman)", self.IN_HEADER_COLOR),
            # v3.9.51 — segmen analisa deviasi lalu-kini di teks CEK
            # (label legend TANPA panah '→' — cek v3.9.8 static-label);
            # v3.9.53 — sumber lalu kini FILE deviasi (⚖), minggu ikut H.
            ("analisa dev lalu-kini (teks CEK · file ⚖)", "#475569"),
            # v3.9.53 — kolom Dev. Bulan Lalu = nilai ASLI file deviasi
            # (⚖; minus merah kurung — BUKAN absolut; minggu menyesuaikan H)
            ("Dev. Bulan Lalu (file ⚖)", "#dc2626"),
            # v3.9.59 — AUDIT FIX 2d-08: kolom ✓ (satu-satunya kolom
            # ikon-only tanpa affordance — dikecualikan dari filter ⧩)
            # kini dijelaskan di legenda: mencentang = masuk/keluarkan
            # daftar pantauan (persist followup.json, tab ☑ Follow Up).
            ("✓ = tambah/keluarkan dari daftar pantauan (tab ☑ Follow Up)",
             "#475569"),
        ])
        legend.pack(fill="x", padx=12, pady=(6, 0))
        self._legend = legend

        # v3.9 (ala Waste): ⤢ Perbesar — ciutkan kartu Filter + judul
        # + legenda; tombol toolbar tetap tampil supaya bisa dikembalikan.
        self._expander = TableExpander(
            btn_expand, [self._fcard, title_label, legend])

        # v3.9: berlangganan perubahan H bersama (tab PCS otomatis ikut;
        # FIX B-07: tab GR juga berlangganan supaya Reset Filter H=25 dari
        # tab mana pun tersinkron ke KEDUA tab — Apply H di GR tetap aman:
        # SharedPivotCache ter-lock, pivot tetap dihitung 1×).
        if self._h_state is not None:
            self._h_state.subscribe(self._on_shared_h_changed)
        # v3.9.21 — ambang ACR dibagi GR & PCS (spinbox kedua tab);
        # unsubscribe defensif pola H (lihat _on_view_destroy).
        if self._acr_state is not None:
            self._acr_state.subscribe(self._on_shared_acr_changed)
        # FIX 6d1-05 — binding Destroy juga dipasang saat view memegang
        # listener FollowUpStore (dulu hanya bila h_state/acr_state ada —
        # view ber-store tanpa state bersama tak pernah melepas listener
        # store di _on_view_destroy).
        if (self._h_state is not None or self._acr_state is not None
                or self.store is not None):
            # FIX C-07 (audit 2-c): unsubscribe defensif saat view destroy
            # (pola laporan/komparasi) — tanpa ini listener tetap
            # hidup bila suatu saat view direbuild (dobel-refresh zombie).
            self.bind("<Destroy>", self._on_view_destroy, add="+")

        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04
        # v3.2: klik sel kolom ✓ → toggle follow-up (tree-agnostic)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")

    def _on_view_destroy(self, event):
        if event.widget is not self:
            return
        if self._h_state is not None:
            self._h_state.unsubscribe(self._on_shared_h_changed)
        if self._acr_state is not None:
            self._acr_state.unsubscribe(self._on_shared_acr_changed)
        # FIX 6d1-05 — lepas listener FollowUpStore (API remove_listener
        # v3.9.42 tersedia tapi tak pernah dipasang; _on_view_destroy dulu
        # hanya me-unsubscribe h_state/acr_state): tanpa ini listener zombie
        # menumpuk bila view suatu saat direbuild — callback _notify
        # mendarat di view mati (ditelan guard winfo_exists) + daftar
        # listener tumbuh tanpa batas.
        if self.store is not None:
            with contextlib.suppress(Exception):
                self.store.remove_listener(
                    self._on_followup_store_changed)

    # v3.9.21 — handler spinbox ambang ACR (dipanggil tombol spin / Enter).
    def _on_acr_threshold_change(self):
        try:
            val = float(str(self._acr_var.get()).strip().replace(",", "."))
        except ValueError:
            self._acr_var.set(self._fmt_threshold(self.acr_threshold))
            return
        if not (1.0 <= val <= 200.0):
            messagebox.showwarning(
                "Ambang ACR to BOM",
                "Ambang harus angka 1–200 (persen × Total ACR).",
                parent=self.winfo_toplevel())
            self._acr_var.set(self._fmt_threshold(self.acr_threshold))
            return
        if self._acr_state is not None:
            # jalur utama: state bersama → listener kedua tab + persist
            self._acr_state.set(val)
            save_acr_threshold(val)
        else:
            # standalone (tanpa shared state): refresh instance ini saja
            self.acr_threshold = val
            self._cached_pivot = None
            self._refresh()

    @staticmethod
    def _fmt_threshold(pct: float) -> str:
        f = float(pct)
        return str(int(f)) if f.is_integer() else str(f)

    # v3.9.21 — listener state bersama (dipanggil SharedACRThreshold saat
    # ambang diubah dari tab mana pun — termasuk tab ini sendiri).
    def _on_shared_acr_changed(self, new_pct):
        self.acr_threshold = float(new_pct)
        if hasattr(self, "_acr_var"):
            self._acr_var.set(self._fmt_threshold(self.acr_threshold))
        # CEK hidup di pivot ter-cache → invalidasi + recompute (H tetap).
        self._cached_pivot = None
        if self._shared_cache is not None:
            self._shared_cache.clear()
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True

    # =========================================================================
    # ✓ FOLLOW-UP (v3.2) — klik sel ✓ = daftarkan / keluarkan
    # =========================================================================
    @staticmethod
    def _fp_stable(row: dict) -> str:
        """FIX 6d1-01 — fingerprint STABIL: bagian 'cek' dinetralkan.

        row_fingerprint (followup.py) menggabung label CEK ke md5 — label
        itu VOLATIL: berubah oleh ambang ACR to BOM (kartu Filter — CEK
        kondisi ke-5) / file deviasi bulan lalu (tab ⚖ — segmen analisa
        jadi snap['cek']) TANPA baris data berubah → fp berubah → centang
        ✓ hilang senyap + entri orphan menetap di followup.json. Identitas
        stabil = 8 field v3.2 (asal|resto|barang|satuan|h|so|sistem|
        deviasi); format/urutan field row_fingerprint dipertahankan,
        bagian 'cek' dikosongkan (entri lama yang kebetulan ber-cek kosong
        otomatis match persis). Entri lama ber-cek tak match string →
        dicocokkan lewat _legacy_fp_index / _followup_keys_for."""
        return row_fingerprint({**row, "cek": ""})

    def _legacy_fp_index(self) -> dict:
        """FIX 6d1-01 — {fp-stabil → kunci-aktual} entri store LAMA.

        Entri followup.json era pra-fix berkunci fp yang memuat label
        'cek' saat dicentang — kunci itu TIDAK match fp stabil string-nya,
        tapi identitas stabilnya (dihitung ulang dari snapshot entri)
        tetap sama → dicocokkan via index ini. Thread worker aman: iterasi
        di-snapshot dulu (RuntimeError bila store dimutasi bersamaan →
        index kosong, fallback has(fp) saja)."""
        store = self.store
        if store is None or not store.rows:
            return {}
        try:
            items = list(store.rows.items())
        except RuntimeError:      # dict dimutasi main thread saat iterasi
            return {}
        idx: dict = {}
        for k, s in items:
            # snapshot json selalu dict (divalidasi FollowUpStore.load);
            # row_fingerprint total utk input mapping json.
            sid = self._fp_stable(s)
            if sid != k:
                idx.setdefault(sid, k)
        return idx

    def _followup_keys_for(self, fp: str) -> list:
        """FIX 6d1-01 — SEMUA kunci store yang mewakili baris ber-fp stabil:
        kunci stabil itu sendiri + entri lama ber-identitas sama (era
        fp-volatil bisa meninggalkan >1 entri per baris — uncheck
        menyapu semuanya, entri orphan tidak menetap)."""
        store = self.store
        if store is None:
            return []
        try:
            items = list(store.rows.items())
        except RuntimeError:
            return [fp] if store.has(fp) else []
        keys: list = []
        for k, s in items:
            if k == fp:
                keys.append(k)
                continue
            if self._fp_stable(s) == fp:
                keys.append(k)
        return keys

    def _on_tree_click(self, event):
        tree = event.widget
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0): clone ⛶ generasi lama
        # (dibuka sebelum re-render terakhir) → handler DIABAIKAN senyap —
        # dulu klik ✓ di clone basi men-toggle pasangan/ baris SALAH.
        if getattr(tree, "_view_gen", None) not in (None, self._render_gen):
            return
        try:
            if tree.identify_region(event.x, event.y) != "cell":
                return
            # v3.7 FIX: cocokkan NAMA kolom (bukan posisi display '#1') —
            # setelah kolom ✓ disembunyikan, posisi #1 jatuh ke kolom lain
            # → toggle follow-up terpicu dari kolom yang salah.
            col = identify_to_column(tree, tree.identify_column(event.x))
            if col != "✓":
                return
            row_iid = tree.identify_row(event.y)
        except Exception:
            return
        if not row_iid or self.store is None:
            return
        fp = self._fp_map.get(row_iid)
        snap = self._row_snaps.get(row_iid)
        if not fp or snap is None:
            return
        # FIX 6d1-01 — _fp_map kini memuat fp STABIL (tanpa 'cek' volatil).
        # Uncheck: hapus SEMUA entri ber-identitas-stabil sama (kunci stabil
        # + entri lama era fp-volatil — menyapu duplikat/orphan sekaligus).
        # Check: tambahkan SATU entri ber-kunci stabil (tahan perubahan
        # ambang ACR / file lalu berikutnya).
        keys = self._followup_keys_for(fp)
        if keys:
            for k in keys:
                self.store.toggle(k, snap)
            added = False
        else:
            added = self.store.toggle(fp, snap)
        try:
            tree.set(row_iid, "✓", CHECK_ON if added else CHECK_OFF)
        except tk.TclError:
            pass
        n = len(self.store)
        self.status_var.set(
            f"{'Masuk' if added else 'Keluar'} daftar Follow Up — total "
            f"{n} baris" if n else "Dikeluarkan — daftar Follow Up kosong")

    # ------------------------------------------------------------------
    # v3.9.59 — AUDIT FIX 2d-10: status footer wrap maks 2 baris
    # ------------------------------------------------------------------
    def _on_foot_configure(self, event):
        """wraplength label status mengikuti lebar footer (resize/zoom)."""
        wl = max(240, int(event.width) - 12)
        if abs(wl - self._status_wrap) >= 8:
            self._status_wrap = wl
            self._on_status_var_write()

    def _on_status_var_write(self, *_):
        """Render status_var → label (wrap ≤ 2 baris, ekor '…').

        status_var TETAP berisi teks penuh (dibaca test/flash); hanya
        TAMPILAN label yang dibatasi — dulu label single-line terpotong
        dari KIRI oleh packer."""
        try:
            text = self.status_var.get()
        except tk.TclError:
            return
        lbl = getattr(self, "status_label", None)
        if lbl is None or not text:
            if lbl is not None:
                with contextlib.suppress(tk.TclError):
                    lbl.configure(text=text)
            return
        wl = max(240, getattr(self, "_status_wrap", 760))
        _f = font(8, "bold")
        try:
            line_h = max(1, _f.metrics("linespace"))
        except (AttributeError, tk.TclError):
            line_h = 15   # tuple-font pre-root — estimasi aman

        def _fits(t: str) -> bool:
            with contextlib.suppress(tk.TclError):
                lbl.configure(text=t, wraplength=wl)
                return lbl.winfo_reqheight() <= 2 * line_h + 2
            return False

        if _fits(text):
            return
        # potong dari KANAN (biner-search): KPI utama di AWAL teks
        # dipertahankan; yang terpotong segmen diagnostik panjang di ekor.
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _fits(text[:mid].rstrip() + "…"):
                lo = mid
            else:
                hi = mid - 1
        with contextlib.suppress(tk.TclError):
            lbl.configure(text=text[:lo].rstrip() + "…", wraplength=wl)

    # v3.9.33 — AUDIT FIX (48-e P1) -------------------------------------------
    def _on_followup_store_changed(self, store=None):
        """Listener FollowUpStore (dipanggil toggle/clear dari tab mana
        pun): jadwalkan pembaruan sel ✓ di main thread — tanpa re-render
        penuh (pola followup_view; view bisa sudah mati → telan TclError)."""
        try:
            if not self.winfo_exists():
                return
            self.after(0, self._refresh_check_cells)
        except tk.TclError:
            pass

    def _refresh_check_cells(self):
        """Perbarui SEMUA sel kolom ✓ dari state store saat ini (iid →
        fingerprint via _fp_map; baris tanpa fp di-skip)."""
        if self.store is None or not self._fp_map:
            return
        try:
            children = self.tree.get_children("")
        except tk.TclError:
            return
        # FIX 6d1-01 — ☑ bila entri ber-kunci stabil ADA **atau** entri lama
        # ber-identitas-stabil sama masih terdaftar (fp era volatil).
        legacy = self._legacy_fp_index()
        for iid in children:
            fp = self._fp_map.get(iid)
            if fp is None:
                continue
            try:
                self.tree.set(
                    iid, "✓",
                    CHECK_ON if (self.store.has(fp) or fp in legacy)
                    else CHECK_OFF)
            except tk.TclError:
                return   # tree/view mati di tengah loop — batal

    def ensure_refreshed(self):
        """Lazy refresh (v3.2): compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None and not self.data.empty:
            self._dirty = False
            self._refresh()

    def on_lalu_file_changed(self):
        """v3.9.53 — file deviasi (tab ⚖ Komparasi) berganti: load baru /
        ditutup / auto-load startup. Sumber kolom 'Dev. Bulan Lalu' +
        ANALISA CEK lalu-kini basi → longgarkan SEMUA cache pivot (identitas
        file = bagian kunci SharedPivotCache — clear supaya recompute
        dijamin; dua lapis dgn cache-miss otomatis) + refresh. Tab
        tersembunyi cukup ditandai dirty (pola _on_shared_h_changed /
        on_lalu_file_changed nominal_resto v3.9.36). Dipanggil app dari
        _on_dev_file_loaded di main thread."""
        self._cached_pivot = None
        self._cached_h = None
        if self._shared_cache is not None:
            self._shared_cache.clear()
        if not self.winfo_ismapped():
            self._dirty = True
            return
        self._refresh()

    def _filtered_pivot(self, exclude_col: str | None = None):
        """v3.9.19 — baris pivot YANG TAMPIL SAAT INI (permintaan user:
        "isi filter harus menampilkan data yang ada aja bukan termasuk
        data yang tidak ada"): mode Satuan + filter KATEGORI + filter
        header kolom LAIN (kolom `exclude_col` sendiri dikecualikan —
        perilaku AutoFilter Excel: daftar nilai = nilai yang TERLIHAT).
        VEKTOR (pivot di-cache) — murah, dipanggil saat popup dibuka."""
        pivot_df = self._cached_pivot
        if pivot_df is None or pivot_df.empty:
            return pivot_df
        filtered = pivot_df
        # mode Satuan (GR / non-GR) — baris tampil per tab
        if self.satuan_mode == "GR":
            filtered = filtered[
                filtered["Satuan"].astype(str).str.upper() == "GR"]
        else:
            filtered = filtered[
                filtered["Satuan"].astype(str).str.upper() != "GR"]
        # filter KATEGORI combobox
        if self._kategori_sel and "KATEGORI" in filtered.columns:
            # v3.9.45 — REKONSILIASI dua keluhan user: (v3.9.44) barang
            # tanpa kategori master (KATEGORI '-' — contoh BUMBU PASTA
            # KUAH 100383) tidak boleh lenyap senyap → passthrough di
            # seleksi DEFAULT Deviasi; (v3.9.45) "ganti kategori tidak
            # terjadi apa apa" — passthrough UNIVERSAL v3.9.44 + master
            # yang men-cover sebagian barang (90% baris '-') bikin
            # filter no-op → seleksi eksplisit lain kini STRICT + entry
            # KATEGORI_BLANK_LABEL utk khusus baris tanpa kategori.
            if self._kategori_sel == KATEGORI_BLANK_LABEL:
                filtered = filtered[
                    kategori_blank_mask(filtered["KATEGORI"])]
            elif kategori_filter_mask(filtered["KATEGORI"],
                                      self._kategori_sel) is not None:
                # v3.9.49 — entri GABUNGAN default (kategori Rekap Mentah).
                # v3.9.53 — kini STRICT: HANYA nilai kategori yang cocok
                # (user: "kok ada nama barang yang bukan kategori COM
                # Deviasi + Packaging Deviasi misal BASKOM STAINLESS 18 CM
                # ... coba cek apa ini bug?" — passthrough blank v3.9.45(a)
                # membuat barang TANPA kategori ikut tampil di seleksi
                # default; proteksi kelas 100383 kini dipenuhi kategori
                # rekap v3.9.49 — kelas tanpa kategori = entry
                # '(Tanpa Kategori)' + jumlahnya dinyatakan di status,
                # tidak lenyap senyap). Popup ⧩ konsisten dgn tabel.
                filtered = filtered[kategori_filter_mask(
                    filtered["KATEGORI"], self._kategori_sel)]
            elif kategori_passthrough(self._kategori_sel):
                _blank = kategori_blank_mask(filtered["KATEGORI"])
                filtered = filtered[
                    (filtered["KATEGORI"].astype(str)
                     == str(self._kategori_sel))
                    | _blank]
            else:
                filtered = filtered[
                    filtered["KATEGORI"].astype(str)
                    == str(self._kategori_sel)]
        # filter header kolom lain (nilai TERFORMAT — identik render)
        for col, sel in self._col_sel.items():
            if sel is None or col == exclude_col:
                continue
            if col in filtered.columns:
                fmt = self._format_col_series(col, filtered[col])
                filtered = filtered[fmt.isin(sel)]
        return filtered

    def _merge_value_get(self, iid, col, cur):
        """v3.9.55/56 — nilai RAW kolom merge-vertikal per iid (sumber:
        snapshot barang / _rank_map) — dipakai (a) auto_fit_columns
        pengukuran lebar (tree._autofit_value_get), (b) filter clone ⛶
        (attach_clone_filters value_get — kelompok utuh lolos filter),
        (c) sort value_get jalurnya terpisah (closure di _sort_by).
        Kolom lain → nilai display tree (cur)."""
        if col == "Nama Barang":
            snap = self._row_snaps.get(str(iid))
            if snap:
                return str(snap.get("barang", cur))
        elif col == "Rank":
            rk = self._rank_map.get(str(iid))
            if rk is not None:
                return str(rk)
        return cur

    def _col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup filter header (v3.5 — semua
        kolom).

        v3.9.19: sumber nilai = baris yang TAMPIL SAAT INI (_filtered_
        pivot — mode Satuan + KATEGORI + filter kolom lain; kolom ini
        sendiri dikecualikan) — dulu pivot MENTAH: tab PCS bisa
        menampilkan nilai CEK yang hanya ada di baris GR (mis. "Beda
        Tanggal" padahal tidak ada baris PCS ber-CEK itu) dan KATEGORI
        Deviasi menampilkan nilai dari kategori lain.
        v3.9.65 — Rank = kolom DERIVED (dihitung _prepare_rows atas
        frame terfilter; tak pernah ada di pivot MENTAH) — dulu popup ⧩
        Rank SELALU KOSONG di semua versi sejak v3.9.51. Kini rumus
        rank dihitung ulang atas frame tampil-saat-ini supaya daftar ⧩
        = rank yang TAMPIL di tabel (renumber per filter — konsisten
        dgn render) & filter ⧩ Rank BERFUNGSI (diterapkan pasca-assign
        di _prepare_rows)."""
        pivot_df = self._filtered_pivot(exclude_col=col)
        if pivot_df is None or pivot_df.empty or col not in pivot_df.columns:
            # v3.9.65 — kolom derived Rank: hitung rumus rank atas frame
            # yang sama dgn sumber nilai popup (tanpa filter Rank itu
            # sendiri — perilaku AutoFilter Excel).
            if (col == "Rank" and pivot_df is not None
                    and not pivot_df.empty
                    and "Deviasi" in pivot_df.columns
                    and "Nama Barang" in pivot_df.columns):
                _abs = pd.to_numeric(pivot_df["Deviasi"],
                                     errors="coerce").abs()
                _rk = (_abs.groupby(pivot_df["Nama Barang"].astype(str))
                       .rank(method="min", ascending=False))
                return self._format_col_series(
                    "Rank", _rk.where(_abs.fillna(0) != 0)) \
                    .unique().tolist()
            return []
        return self._format_col_series(col, pivot_df[col]).unique().tolist()

    def _format_col_series(self, col: str, series):
        """Format kolom → string tampilan (identik render tabel).
        v3.9.51: Nominal → Currency Rp; Dev. Bulan Lalu → format khusus
        (NaN vs 0 dibedakan); CEK → LABEL UTAMA (sebelum ' · ') supaya
        popup ⧩ & APPLY tetap mengelompokkan label anomali check."""
        if col == "Dev to BOM%":
            return series.map(self._fmt_pct)
        if col == "Nominal":
            # v3.9.34 — NaN (tanpa harga) → 0 → '-' identik sel tabel
            # (NaN mentah akan tampil string kosong di popup ⧩ —
            # inkonsisten dgn tabel). v3.9.51 — format Currency Rp.
            return series.fillna(0).map(fmt_rp_cell)
        if col == "Dev. Bulan Lalu":
            return series.map(self._fmt_dev_lalu)
        if col == "CEK":
            # v3.9.51 — nilai popup = label utama; analisa lalu→kini
            # hanyalah segmen teks (mis. 'Turun Drastis · Penurunan
            # Tertinggi -25,3%' → entri 'Turun Drastis').
            return series.astype(str).map(lambda s: s.split(" \u00b7 ")[0])
        return series.map(self._fmt_num)

    def _on_col_filter(self, col: str, selected):
        self._col_sel[col] = selected
        self._refresh()

    # v3.9.13 — combobox KATEGORI ("Semua" = tanpa filter).
    # v3.9.19 — DEFAULT seleksi = kategori "Deviasi" (permintaan user:
    # "secara default kategori terfilter ke kategori Deviasi") —
    # dicocokkan case-insensitive dgn nilai data (mis. "DEVIASI");
    # fallback "Semua" bila kategori itu tidak ada di data.
    # v3.9.49 — DEFAULT BARU: entry GABUNGAN kategori Rekap Mentah
    # (user: "jadi secara default di semua tab kategori sudah pilih: COM
    # DEVIASI - RESTO dan Biaya Packaging - RESTO") bila data memuat
    # salah satu nilai rekap; fallback legacy 'Deviasi' → 'Semua'.
    def _on_kategori_changed(self):
        val = self._kategori_var.get()
        self._kategori_sel = None if (not val or val == "Semua") else val
        self._refresh()

    def _default_kategori_value(self) -> str:
        values = list(self._kategori_combo["values"] or [])
        if KATEGORI_DEFAULT_LABEL in values:
            return KATEGORI_DEFAULT_LABEL
        for v in values:
            if str(v).strip().lower() == "deviasi":
                return str(v)
        return "Semua"

    def _reset_kategori(self):
        val = self._default_kategori_value()
        self._kategori_var.set(val)
        self._kategori_sel = None if val == "Semua" else val

    # v3.9.49 — combobox AKTIF/NON ("Semua" = tanpa filter — pindahan
    # kolom tabel ke bagian filter, dekat KATEGORI).
    def _on_aktif_changed(self):
        val = self._aktif_var.get()
        self._aktif_sel = None if (not val or val == "Semua") else val
        self._refresh()

    def _reset_aktif(self):
        self._aktif_var.set("Semua")
        self._aktif_sel = None

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    # Snapshot / pulihkan kombinasi filter view ini (app menyimpan semua
    # view ke settings.json saat jendela ditutup + memanggil restore SEKALI
    # setelah load_data run pipeline PERTAMA sesi berikutnya).
    # TANGGAL H & AMBANG ACR TIDAK ikut: H = jendela data bersama dgn
    # default dinamis dari data (v3.9.22 — "tanggal harusnya tanggal 26"),
    # ACR = ambang ANALISA (bukan penyaringan baris).
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.deviasi_gr/deviasi_pcs')."""
        st = col_sel_to_json(self._col_sel)
        st["kategori"] = self._kategori_var.get()
        if hasattr(self, "_aktif_var"):
            st["aktif"] = self._aktif_var.get()
        return st

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.

        Combobox KATEGORI/AKTIF divalidasi terhadap values data BARU
        (pola preserve v3.9.42): nilai hilang → seleksi default tetap
        (tidak memasang filter 0-baris senyap). View tersembunyi → CUKUP
        menulis state (dirty flag load_data masih terpasang — compute
        saat tab dibuka memakai state yang sudah dipulihkan)."""
        if not isinstance(state, dict):
            return
        if self.data is None or bool(getattr(self.data, "empty", True)):
            return
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        _kv = state.get("kategori")
        if isinstance(_kv, str):
            try:
                _kvals = list(self._kategori_combo["values"])
            except tk.TclError:
                _kvals = []
            if _kv in _kvals and self._kategori_var.get() != _kv:
                self._kategori_var.set(_kv)
                self._kategori_sel = (None if _kv == "Semua" else _kv)
                changed = True
        if hasattr(self, "_aktif_var"):
            _av = state.get("aktif")
            if isinstance(_av, str):
                try:
                    _avals = list(self._aktif_combo["values"])
                except tk.TclError:
                    _avals = []
                if (_av in _avals
                        and self._aktif_var.get() != _av):
                    self._aktif_var.set(_av)
                    self._aktif_sel = (None if _av == "Semua" else _av)
                    changed = True
        if changed and self.winfo_ismapped():
            self._refresh()

    def _show_empty(self):
        self.content.pack_forget()
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

    def _show_content(self):
        self.empty.pack_forget()
        self.content.pack(fill="both", expand=True)

    def _setup_tags(self, tree=None):
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        # v3.9.61 — sekat warna kelompok DIHAPUS (user): konfigurasi tag
        # grp0/grp1 (band latar putih ↔ slate) tidak lagi dipasang; kelas
        # konfigurasi evenrow/oddrow lama dibiarkan (tak pernah dipakai
        # di view ini — nilai historis utk instansi kloning lama).
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("zero_dev", foreground="#64748b")
        # v3.9.2 — minus merah PER CELL (bukan satu baris penuh)
        tree.tag_configure("neg_cell", foreground="#dc2626")
        tree.tag_configure("zero_cell", foreground="#64748b")
        # v3.9.18 — highlight latar lembut kolom Deviasi & SO_H
        tree.tag_configure("hl_cell", background=self.HIGHLIGHT_BG)
        # CEK — palet modern (sejalan design system)
        tree.tag_configure("cek_kosong", foreground="#b45309")   # amber
        tree.tag_configure("cek_tanggal", foreground="#2563eb")  # blue
        tree.tag_configure("cek_manual", foreground="#c2410c")   # orange-700 (v3.9.50: kontras 2,89→3,9:1 di atas bg grp_head — audit 3-c)
        tree.tag_configure("cek_drastis", foreground="#dc2626")  # red
        tree.tag_configure("cek_acr", foreground="#7c3aed")      # purple
        # v3.9.19 — kondisi ke-0 "Promix 04" (SO bersumber non input so
        # harian): teal
        tree.tag_configure("cek_promix", foreground="#0e7490")
        # v3.9.23 (poin 6) — kondisi ke-1 "RI Balancing": amber gelap
        # (keluarga warna sama dgn popup Rincian IN v3.9.19 #b45309,
        # dgn nuansa lebih tua supaya terbedakan dari Kosong/Non Aktif)
        tree.tag_configure("cek_ri_bal", foreground="#92400e")

    # =========================================================================
    # LOGIKA (identik versi lama)
    # =========================================================================
    def _col_display_name(self, col_name: str) -> str:
        import re
        h = self.tanggal_h
        m = re.match(r"^(.*)_H([+-]\d+)?$", col_name)
        if m:
            prefix = m.group(1)
            offset_str = m.group(2)
            offset = int(offset_str) if offset_str else 0
            date = h + offset
            # FIX 6d1-03 — tanggal 0 / −1 TIDAK pernah ada sebagai tanggal
            # (rekap bulan lalu memakai kunci −1 = saldo penutupan):
            # header lama 'SO_0'/'SO_-1' men-label tanggal yang tak pernah
            # ada. Kolom ber-date 0 menampilkan penutupan bulan lalu
            # (pemetaan 0→−1 fix 48-b) → label jujur '…_lalu'; date < 0
            # (H=1, SO dua hari sebelum tanggal 1 — nilai dinolkan di
            # _compute_pivot) → label '…_—' dengan sel '-'.
            if date == 0:
                return f"{prefix}_lalu"
            if date < 0:
                return f"{prefix}_\u2014"
            return f"{prefix}_{date}"
        return col_name

    def _update_headings(self):
        # v3.5: heading tanpa command (klik = popup filter ⧩; sort via
        # popup) — nama display di-refresh per tanggal H
        for col_name, _, _ in self.COLUMNS:
            self.tree.heading(col_name,
                              text=self._col_display_name(col_name))
        if getattr(self, "header_filters", None) is not None:
            self.header_filters.refresh_icons()
        # v3.9.33 — AUDIT FIX (48-d LOW): menulis ulang teks heading (per
        # ganti H) MENGHAPUS panah indikator sort ↓/↑ — pasang ulang dari
        # state sort terakhir tree (sort_tree_by_column menyimpannya di
        # tree._last_sort; dulu indikator hilang diam-diam tiap Apply H).
        _ls = getattr(self.tree, "_last_sort", None)
        if _ls is not None:
            with contextlib.suppress(tk.TclError):
                _set_sort_arrow(self.tree, _ls[0], _ls[1])

    # =========================================================================
    # DATA LOADING
    # =========================================================================
    def _default_h_from_data(self, data) -> "int | None":
        """v3.9.22 — tanggal SO NONZERO terakhir (positif) dari data:
        default TANGGAL H saat data dimuat (permintaan user: "Tanggal
        harusnya tanggal 26 bukan dari tanggal 25" — rekap mingguan
        mereka kini berdata sampai 26). Baris template 0 tidak dihitung
        (kalau dihitung, kolom template 27..31 akan melompatkan H ke 31).
        Return None bila tidak ada baris SO → pemanggil memakai nilai
        state/fallback 26."""
        if data is None or getattr(data, "empty", True):
            return None
        if "JENIS" not in getattr(data, "columns", []):
            return None
        so = data[data["JENIS"] == "1.SO"]
        if so.empty:
            return None
        t = pd.to_numeric(so["Tanggal"], errors="coerce")
        v = pd.to_numeric(so["NILAI"], errors="coerce").fillna(0)
        m = (t >= 1) & (v != 0)
        if not bool(m.any()):
            return None
        h = int(t[m].max())
        return max(1, min(h, 31))

    def load_data(self, data: pd.DataFrame,
                  in_detail: pd.DataFrame | None = None,
                  harga_map: dict | None = None,
                  konversi_map: dict | None = None):
        self.data = data
        # v3.9.23 (poin 6) — detail dokumen IN per-dokumen (query_in):
        # sumber CEK "RI Balancing" kolom utama (bulan Nomor RI ≠ bulan
        # Nomor PO; pemetaan Nomor↔Nomor PO BERSIH per baris dokumen,
        # tidak ter-campur seperti kolom gabungan di frame final).
        # None (pemanggil lama/test) → kondisi tidak berlaku.
        self.in_detail = in_detail
        # v3.9.34 — kolom Nominal: harga 41.09 + peta rasio satuan
        # (audit_result['harga_map']/['konversi_map']); None/pemanggil
        # lama → tanpa harga → SEMUA sel Nominal tampil '-' (kompatibel).
        self.harga_map = harga_map or {}
        self.konversi_map = konversi_map
        self._harga_pair_cache = None   # dibangun ulang di _compute_pivot
        self._ri_bal_cache = None   # v3.9.23 — cache pasangan per (df, h)
        self._cached_pivot = None
        self._cached_h = None
        # v3.9.55 — F8: data baru → auto-fit SEKALI lagi saat render pertama
        reset_autofit_once(self)
        if self._shared_cache is not None:
            self._shared_cache.clear()
        self._aktif_lookup = {}
        self._kategori_lookup = {}   # v3.9.13 — diisi ulang di _compute_pivot
        self._so_source_lookup = {}  # v3.9.19 — diisi ulang di _compute_pivot
        self._tnum = None  # reset cache to_numeric(Tanggal)
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0): data berganti → semua clone
        # ⛶ hidup menampilkan salinan baris LAMA (iid sama, pasangan beda)
        # → DITUTUP + generasi naik (guard handler ✓/double-click clone).
        self._render_gen += 1
        self._close_stale_clones()
        # v3.9: pulihkan layout bila sedang di-perbesar ⤢ (data baru =
        # layout baru — jangan terjebak setengah-collapse)
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        # v3.9.22 — DEFAULT H DINAMIS (user: "Tanggal harusnya tanggal 26
        # bukan dari tanggal 25"): data baru → H di-reset ke tanggal SO
        # NONZERO terakhir (rekap user kini mencakup 1..26 → H=26; pola
        # reset kategori default DEVIASI). set() men-trigger listener tab
        # lain (chip PCS/Laporan/Komparasi ikut); nilai sama → no-op.
        # FIX 6d1-02 — counter _load_depth (class-level) menahan SEMUA
        # listener _on_shared_h_changed selama blok ini (instance ini +
        # saudara GR/PCS): dulu set() me-render DI TENGAH load dengan
        # filter kategori/kolom/aktif LAMA (render #1 = 0 baris + status
        # salah) sebelum reset filter di bawah → render #2 dari akhir
        # load_data. Kini SATU render di akhir load_data (state filter
        # baru sudah diterapkan).
        type(self)._load_depth += 1
        try:
            _new_h = self._default_h_from_data(data)
            if _new_h is not None:
                if self._h_state is not None:
                    self._h_state.set(_new_h)
                    self.tanggal_h = self._h_state.h
                else:
                    self.tanggal_h = _new_h
            elif self._h_state is not None and self.tanggal_h != self._h_state.h:
                self.tanggal_h = self._h_state.h
        finally:
            type(self)._load_depth -= 1
        if hasattr(self, "_h_chip_var"):
            self._h_chip_var.set(str(self.tanggal_h))
        if self._h_editable and hasattr(self, "tanggal_h_var"):
            self.tanggal_h_var.set(str(self.tanggal_h))
        # v3.9.33 — AUDIT FIX (48-f HIGH sebagian): 0 baris pasca-pipeline →
        # EMPTY STATE + status berpenjelasan aksi (dulu _show_content()
        # TANPA SYARAT → tabel kosong senyap di belakang pipeline
        # "SELESAI" hijau — user tak tahu harus cek folder data/RootPath;
        # pola teks lama "Belum ada data." dipertahankan di awal).
        _data_empty = data is None or getattr(data, "empty", True)
        if not _data_empty:
            self._show_content()
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        # v3.9.13: isi combobox KATEGORI dari kolom data (merge "21. DBS
        # Kategori" di append1) + reset seleksi — "Semua" = tanpa filter.
        # v3.9.45 — entry '(Tanpa Kategori)' saat ADA baris tanpa master
        # (akses eksplisis kelas 100383 tanpa menonaktifkan filter).
        # v3.9.46 — entry kini SELALU ADA (dulu kondisional _has_blank:
        # user: "kategori tanpa kategori kok kosong" — master yang makin
        # lengkap / data tanpa baris kosong membuat entry HILANG SENYAP
        # dari dropdown, user mencari opsi itu & tak menemukannya; bila
        # dipilih saat memang tak ada baris kosong, status menjelaskan
        # itu secara jujur — bukan tabel kosong misterius).
        if data is not None and "KATEGORI" in getattr(data, "columns", []):
            _kv = data["KATEGORI"].dropna().astype(str).str.strip()
            kategori_vals = sorted(v for v in _kv.unique() if v)
        else:
            kategori_vals = []
        # v3.9.49 — entry GABUNGAN default (kategori Rekap Mentah) hanya
        # saat data memuat salah satu nilai rekap (tanpa itu, entry akan
        # memfilter 0 baris di data lama yang tak ber-kategori rekap).
        _kv45 = ["Semua"]
        if kategori_has_default_values(
                data.get("KATEGORI") if data is not None else None):
            _kv45.append(KATEGORI_DEFAULT_LABEL)
        _kv45.append(KATEGORI_BLANK_LABEL)
        _kv45 += kategori_vals
        self._kategori_combo["values"] = _kv45
        self._reset_kategori()
        # v3.9.49 — filter AKTIF/NON direset ke 'Semua' tiap load data
        # (pola _reset_kategori; kolom pindahan dari tabel → filter).
        if hasattr(self, "_aktif_var"):
            self._reset_aktif()
        if _data_empty:
            self._show_empty()
            self.status_var.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")
            return
        # (v3.2) lazy refresh: hanya compute bila tab ini sedang terlihat;
        # tab lain menunggu dipilih (app memanggil ensure_refreshed).
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True

    # =========================================================================
    # PIVOT COMPUTATION (v3.2 — VEKTORISASI numpy, hasil identik versi lama)
    # =========================================================================
    def _compute_pivot(self, data: pd.DataFrame | None = None,
                       h: int | None = None,
                       lalu_map: dict | None = None,
                       lalu_label: str | None = None) -> pd.DataFrame:
        """FIX D-01 (audit 2-d): data/h bisa di-pass eksplisit (identitas
        yang dicapture worker) — default membaca self.* (kompatibel
        pemanggilan lama/test).

        v3.9.53 — lalu_map/lalu_label: peta {(resto_norm, bahan_norm):
        qty} + label 'WEEK n · <bulan>' dari FILE deviasi (dibangun work()
        via dev_lalu_qty_map sekali per job — pivot di-cache ber-identitas
        file). None/{} = tanpa file → kolom Dev. Bulan Lalu semua NaN
        (tampil '-')."""
        if data is None:
            data = self.data
        if h is None:
            h = self.tanggal_h
        if data is None or data.empty:
            return pd.DataFrame()

        df = data

        tanggal_range = [h - 2, h - 1, h, h + 1, h + 2]
        # v3.9.33 — AUDIT FIX (48-b P1): H=2 → kunci −1 (penutupan bulan
        # lalu — rekap lalu dinegasikan) ikut window supaya lookup
        # _day_key SO(H−2) menemukan barisnya (H=1 sudah termuat alami:
        # range −1..3). H≥3 tak berubah.
        if h == 2:
            tanggal_range.append(-1)
        relevant_jenis = ["1.SO", "2.SALDO AKHIR", "4.IN", "9.ACR",
                          "8.BARANG KELUAR"]

        # cache to_numeric(Tanggal) per objek data (hindari recompute tiap H)
        # FIX D-01: di-key IDENTITAS objek — reset/reset-silang dari main
        # thread tidak bisa membuat cache milik data lain terpakai.
        tnum = self._tnum if self._tnum_data is df else None
        if tnum is None:
            tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
            self._tnum = tnum
            self._tnum_data = df
        mask = (df["JENIS"].isin(relevant_jenis)) & (tnum.isin(tanggal_range))

        # v3.9.32 — BARANG 42.17-ONLY (user: "kenapa barang yang hanya ada
        # di 42.17, mis. BUMBU PASTA KUAH, tidak muncul di Deviasi GR?"):
        # fn_4217 HARDCODE Tanggal=1 untuk semua baris saldo → pasangan
        # yang SATU-SATUNYA datanya saldo 42.17 (tanpa rekap SO/IN/out)
        # hanya punya baris t=1 → TIDAK PERNAH masuk window H±2 (H>3)
        # → lenyap dari tabel. FIX: baris ('2.SALDO AKHIR', t=1) pasangan
        # yang TIDAK punya baris window mana pun SELALU ikut (pair
        # muncul) + Sistem pasangan itu = saldo t=1 (lihat bawah).
        # Pasangan ber-window TIDAK tersentuh (nilai tabel tak berubah).
        _pair_key = (df["Nama Barang"].astype(str) + "\x1f"
                     + df["NAMA RESTO"].astype(str))
        _window_pairs = pd.Index(_pair_key[mask].unique())
        _saldo_t1 = (df["JENIS"] == "2.SALDO AKHIR") & (tnum == 1)
        _mask_saldo_only = _saldo_t1 & ~_pair_key.isin(_window_pairs)
        mask = mask | _mask_saldo_only
        df_filtered = df[mask].assign(Tanggal_num=tnum[mask].to_numpy())
        # v3.9.33 — AUDIT FIX (48-d MEDIUM): pasangan IN-only (42.05/
        # 32.24/9901 — tanpa rekap-SO & tanpa 42.17) ber-SATUAN NaN lenyap
        # SENYAP dari pivot_table (index NaN di-drop secara default) →
        # janji lookup barang dua arah v3.9.18 tak penuh. SATUAN NaN →
        # "" (string kosong); pasangan ber-SATUAN asli tak tersentuh.
        if "SATUAN" in df_filtered.columns:
            df_filtered = df_filtered.assign(
                SATUAN=df_filtered["SATUAN"].fillna(""))

        if "AKTIF/NON" in df.columns and "Nama Barang" in df.columns:
            aktif_df = (
                df[["Nama Barang", "AKTIF/NON"]]
                .dropna(subset=["AKTIF/NON"])
                .drop_duplicates(subset=["Nama Barang"], keep="first")
            )
            self._aktif_lookup = dict(zip(
                aktif_df["Nama Barang"].astype(str),
                aktif_df["AKTIF/NON"].astype(str)
            ))
        else:
            self._aktif_lookup = {}

        # v3.9.13: lookup KATEGORI per barang (pola _aktif_lookup — kolom
        # KATEGORI hasil merge "21. DBS Kategori", 1:1 per Nama Barang).
        # Nilai di-strip supaya cocok dgn nilai combobox (juga di-strip).
        if "KATEGORI" in df.columns and "Nama Barang" in df.columns:
            kategori_df = (
                df[["Nama Barang", "KATEGORI"]]
                .dropna(subset=["KATEGORI"])
                .drop_duplicates(subset=["Nama Barang"], keep="first")
            )
            self._kategori_lookup = dict(zip(
                kategori_df["Nama Barang"].astype(str),
                kategori_df["KATEGORI"].astype(str).str.strip()
            ))
        else:
            self._kategori_lookup = {}

        # v3.9.19 — lookup SOURCE DATA per (barang, resto) dari baris
        # JENIS 1.SO. v3.9.21 — PER-TANGGAL (fix "Promix 04 muncul di
        # filter tapi data tidak ada"): sumber = baris 1.SO pada
        # TANGGAL ANALISA H saja (append1 LANGKAH 9 kini merge sumber per
        # (pasangan × tanggal) atas baris rekap ber-NILAI non-nol — 'input
        # so harian' menang atas promix pada tanggal sama; baris template
        # bernilai 0 tidak ikut menentukan). Pasangan tanpa SO ber-sumber
        # di tanggal H → tak berlabel Promix (kondisi tak berlaku).
        self._so_source_lookup = {}
        if "SOURCE DATA" in df.columns:
            so_src = df[
                (df["JENIS"] == "1.SO") & df["SOURCE DATA"].notna()
            ][["Nama Barang", "NAMA RESTO", "Tanggal", "SOURCE DATA"]]
            if not so_src.empty:
                _t = pd.to_numeric(so_src["Tanggal"], errors="coerce")
                so_src = so_src[_t == int(h)]
            if not so_src.empty:
                # dedup defensif per pasangan: 'input so harian' menang
                # (sudah unik per (pasangan×tanggal) dari LANGKAH 9 —
                # jalur ini hanya utk input df buatan/test).
                so_src = so_src.assign(
                    _s=so_src["SOURCE DATA"].astype(str))
                so_src = so_src[
                    so_src["_s"].str.strip().ne("")]
                so_src = (
                    so_src.assign(
                        _harian=so_src["_s"].str.strip().str.lower()
                        == "input so harian")
                    .sort_values("_harian", kind="mergesort")
                    .drop_duplicates(subset=["Nama Barang", "NAMA RESTO"],
                                     keep="last")
                )
                self._so_source_lookup = {
                    (str(b), str(r)): str(v).strip()
                    for b, r, v in zip(so_src["Nama Barang"],
                                       so_src["NAMA RESTO"],
                                       so_src["SOURCE DATA"])
                }

        # v3.9.23 (poin 6) — CEK "RI Balancing" KOLOM UTAMA: pasangan
        # (barang, resto) yang punya ≥1 dokumen IN ber-PERIODE Nomor PO
        # DI LUAR periode bisnis RI-nya (v3.9.24 klarifikasi user: satu
        # periode = tgl 26 bulan lalu s/d 25 bulan RI — RI 1 Okt ↔ PO
        # Sep TETAP satu periode [tak di-flag]; PO Agu di luar periode
        # → balancing) dgn TANGGAL DOKUMEN ≤ H (scope analisa — dokumen
        # tercatat setelah H belum termasuk; tanggal bulan-lalu negatif
        # tetap masuk, kronologis sebelum tanggal 1). Logika periode =
        # _ri_balancing (doc_codes — sama dgn popup Rincian IN & Catatan
        # Audit, tanggal-aware batas 25/26 + wrap tahun, hanya dokumen
        # berprefiks "RI.").
        # Cache per (identitas in_detail, h) — scan O(n) regex hanya saat
        # data/H berubah, bukan tiap refresh.
        _rib = self._ri_bal_cache
        _det = self.in_detail
        if _rib is not None and _rib[0] is _det and _rib[1] == h:
            self._ri_bal_pairs = _rib[2]
        else:
            if _det is not None and not _det.empty \
                    and "Tanggal" in getattr(_det, "columns", []):
                _t = pd.to_numeric(_det["Tanggal"], errors="coerce")
                _det_in_scope = _det[_t <= h]
            else:
                _det_in_scope = None
            self._ri_bal_pairs = frozenset(
                ri_balancing_docs(_det_in_scope).keys())
            self._ri_bal_cache = (_det, h, self._ri_bal_pairs)

        if df_filtered.empty:
            return pd.DataFrame()

        try:
            pivot = df_filtered.pivot_table(
                index=["Nama Barang", "NAMA RESTO", "SATUAN"],
                columns=["JENIS", "Tanggal_num"],
                values="NILAI",
                aggfunc="sum",
                fill_value=0,
            )
        except Exception:
            # FIX 6d1-06 — dulu exception ditelan senyap → frame kosong →
            # status generik 'Tidak ada data.' TANPA penyebab (kelas pola
            # berulang #5). Kini: log penyebab + RE-RAISE → run_async
            # on_error menampilkan status '⚠ Gagal menghitung deviasi:'
            # + me-reset _busy/_pending (jalur error yang sudah ada).
            _LOG.warning("deviasi: pivot_table gagal dibangun",
                         exc_info=True)
            raise

        if pivot.empty:
            return pd.DataFrame()

        pivot = pivot.reset_index()

        # v3.9.18 — FOKUS RESTO FOLDER "1. DEVIASI WEEKLY" (permintaan
        # user: "resto yang dianalisa hanya berfokus pada resto yang ada
        # di folder 1. DEVIASI WEEKLY aja jangan semua"). JENIS 1.SO /
        # 5.BARANG MASUK hanya bersumber dari rekap mentah; Tanggal POSITIF
        # = rekap berjalan (sheet '1  DEVIASI WEEKLY' folder RekapBerjalan)
        # — rekap bulan lalu dinegasikan (negatif) dan berasal dari folder
        # lain (1.12 Rekap Mentah Bulan Lalu), jadi TIDAK ikut menentukan
        # scope. Resto tanpa rekap (hanya ada di 32.24/42.05/9901/22.05/
        # 42.15) dikeluarkan — dulu barisnya menampilkan Deviasi =
        # 0 − Sistem = minus palsu.
        # BARANG tetap DUA ARAH (permintaan user: "look up nama barang ini
        # pakai dua arah ... tidak hanya barang di folder deviasi weekly
        # aja tapi juga sebaliknya"): barang ber-rekap MAUPUN barang yang
        # hanya ada di data app utk resto rekap — keduanya tampil.
        rekap_mask = df["JENIS"].isin(("1.SO", "5.BARANG MASUK")) & (tnum >= 1)
        rekap_restos = pd.Index(
            df.loc[rekap_mask, "NAMA RESTO"].astype(str).unique())
        pivot = pivot[
            pivot["NAMA RESTO"].astype(str).isin(rekap_restos)]

        n = len(pivot)

        # v3.9.33 — AUDIT FIX (48-b P1): kunci tanggal SO bulan-lalu. Rekap
        # bulan lalu bernomor NEGATIF (−1 = saldo penutupan bulan lalu) dan
        # Tanggal 0 TIDAK PERNAH ada (baris template kosong). Lookup
        # SO(H−1)/SO(H−2) lama membaca kunci 0 saat H≤2 → SELALU 0: di H=1,
        # SO bulan lalu (kunci −1) hanya terbaca sebagai SO(H−2) sehingga
        # W/CEK/Stok Seharusnya salah. Pemetaan 0 → −1: H=1 → SO(H−1) =
        # penutupan bulan lalu; H=2 → SO(H−2) = penutupan; H≥3 tak berubah
        # (konsisten fix fn_audit v3.9.6).
        def _day_key(t) -> int:
            return -1 if t == 0 else t

        def arr(jenis: str, tgl) -> np.ndarray:
            """Kolom (JENIS, Tanggal) sebagai array float64 (0 bila absen) —
            semantik identik get_val versi lama (NaN → 0)."""
            key = (jenis, float(tgl))
            if key in pivot.columns:
                return pd.to_numeric(
                    pivot[key], errors="coerce").fillna(0).to_numpy(
                    dtype="float64")
            return np.zeros(n, dtype="float64")

        # FIX 6d1-03 — H=1: SO(H−2) jatuh ke tanggal −1 = kunci rekap
        # PENUTUPAN bulan lalu — kunci yang SAMA dengan SO(H−1) (lewat
        # pemetaan 0→−1 fix 48-b) → dua kolom tampil DUPLIKAT saldo
        # penutupan. "Tanggal dua hari sebelum tanggal 1" tak pernah ada
        # (kunci −2 tidak ada di data) → kolom jujur kosong (0 → tampil
        # '-' di _fmt_num — pola `else 0` _prepare_rows); saldo penutupan
        # tetap tampil SEKALI di SO(H−1). H=2 tak berubah (SO(H−2) =
        # penutupan by-design fix 48-b); H≥3 tak tersentuh.
        so_m2 = (np.zeros(n, dtype="float64") if h == 1
                 else arr("1.SO", _day_key(h - 2)))
        so_m1 = arr("1.SO", _day_key(h - 1))
        in_m1 = arr("4.IN", h - 1)
        so_h = arr("1.SO", h)
        in_h = arr("4.IN", h)
        out_h = arr("9.ACR", h)
        bk_h = arr("8.BARANG KELUAR", h)
        so_p1 = arr("1.SO", h + 1)
        in_p1 = arr("4.IN", h + 1)
        so_p2 = arr("1.SO", h + 2)
        sistem = arr("2.SALDO AKHIR", h)

        # v3.9.32 — pasangan SALDO-ONLY (42.17): satu-satunya barisnya
        # ('2.SALDO AKHIR', t=1) → Sistem = saldo running-stock t=1
        # (= saldo 42.17; tidak ada mutasi sesudahnya). Deviasi = SO_H
        # (0) − saldo → pasangan tampil dgn selisih nyata, bukan 0−0.
        # v3.9.33 — AUDIT FIX (48-b P1-LOW): dulu mask hanya mencakup
        # pasangan TANPA baris window (efektif saat H>3) — untuk H≤3
        # baris t=1 42.17 MASUK window → Sistem = arr('2.SALDO AKHIR',
        # H) = 0 → fix v3.9.32 INERT (Deviasi 0−0). Kini cabang np.where
        # juga mencakup pasangan TANPA baris saldo ('2.SALDO AKHIR', H)
        # — Sistem = saldo t=1 juga (Deviasi = SO_H − saldo). Pasangan
        # BER baris saldo di H (AYAM-style) tetap jalur normal — nilai
        # tabel tak berubah (regresi diuji /tmp).
        _sistem_t1 = arr("2.SALDO AKHIR", 1)
        _saldo_h_pairs = pd.Index(_pair_key[
            (df["JENIS"] == "2.SALDO AKHIR") & (tnum == h)].unique())
        _pk_pivot = (pivot["Nama Barang"].astype(str) + "\x1f"
                     + pivot["NAMA RESTO"].astype(str))
        _saldo_only_rows = ~(_pk_pivot.isin(_window_pairs)
                             & _pk_pivot.isin(_saldo_h_pairs)).to_numpy()
        if _saldo_only_rows.any():
            sistem = np.where(_saldo_only_rows, _sistem_t1, sistem)

        # v3.9.53 — DEVIASI BULAN LALU (kuantiti) per pasangan = DEV Lalu
        # FILE deviasi resmi (tab ⚖ Komparasi — parse_deviasi_file) — NILAI
        # ASLI bertanda (user: "Deviasi bulan lalu yang ditampilkan di tab
        # deviasi gr dan pcs pakai nilai asli jangan pakai nilai absolute
        # yang ditampilkan. Absolute untuk perhitungan saja"); minggu
        # pembanding MENYESUAIKAN H (user: "Week ... menyesuaikan kolom H
        # di tab deviasi GR dan PCS untuk Deviasi bulan lalu" — mirror
        # _pilih_minggu_lalu v3.9.41 "jika week 1 maka ambil data week 1
        # juga") + bulan TERBARU file (parity hitung_nominal_lalu_pairs
        # tab 🧮 — angka PERSIS sama dgn kolom 'DEV Lalu' tab 📋 Laporan
        # Deviasi). Dulu v3.9.51-52: Σ 3.DEVIASI tgl negatif rekap lalu —
        # cakupan rekap lalu HANYA tgl -25..-31 (fn_rekap_mentah mode
        # 'lalu') & nilai mentahnya tak sebanding kuantitas deviasi resmi
        # → DIGANTI sumber file. NaN = pasangan tanpa file/tanpa baris
        # pembanding (tampil '-'); ABSOLUTE dipakai HANYA klasifikasi
        # ANALISA CEK lalu→kini di bawah (|kini| vs |lalu|). Kunci pasangan
        # (resto_norm, bahan_norm) — mirror normalisasi join komparasi;
        # satuan pasangan konstan, GR/PCS dipisah di _prepare_rows per tab.
        if lalu_map:
            _lkey53 = (pivot["NAMA RESTO"].astype(str)
                       .map(_norm_resto_lalu) + "\x1f"
                       + pivot["Nama Barang"].astype(str)
                       .map(_norm_name_lalu))
            _lmap53 = {f"{r}\x1f{b}": q
                       for (r, b), q in lalu_map.items()}
            dev_lalu = _lkey53.map(_lmap53).to_numpy(dtype="float64")
        else:
            dev_lalu = np.full(n, np.nan, dtype="float64")

        deviasi = so_h - sistem

        # --- v3.9.6: KATEGORI DEVIASI (mirror sheet DEVIASI GR/PCS asli) ---
        # Total ACR = BOM per (barang, resto, satuan) = Σ penjualan 9.ACR
        # tanggal 1..H (kolom "Dev to BOM%" sheet asli = Deviasi/Total ACR —
        # terverifikasi nilai-per-nilai dari sheet DEVIASI GR file user).
        h_safe = max(1, h)
        out_mask = (df["JENIS"] == "9.ACR") & (tnum >= 1) & (tnum <= h)
        out_df = df[out_mask]
        if not out_df.empty:
            _nil = pd.to_numeric(out_df["NILAI"], errors="coerce")
            out_sum = (
                # v3.9.33 — AUDIT FIX (48-d): SATUAN NaN → "" (join Total
                # ACR konsisten dgn pivot yang kini ber-SATUAN "")
                out_df.assign(_n=_nil,
                              SATUAN=out_df["SATUAN"].fillna(""))
                .groupby(["Nama Barang", "NAMA RESTO", "SATUAN"],
                         as_index=False, dropna=False)["_n"].sum()
            )
            # join via key-frame (pivot masih berkolom MultiIndex (JENIS,
            # Tanggal) — tidak bisa di-merge langsung)
            keys_df = pd.DataFrame({
                "Nama Barang": pivot["Nama Barang"].to_numpy(),
                "NAMA RESTO": pivot["NAMA RESTO"].to_numpy(),
                "SATUAN": pivot["SATUAN"].to_numpy(),
            }).merge(out_sum, on=["Nama Barang", "NAMA RESTO", "SATUAN"],
                     how="left")
            total_acr = pd.to_numeric(keys_df["_total_acr"] if "_total_acr"
                                      in keys_df.columns else keys_df["_n"],
                                      errors="coerce").fillna(0.0) \
                .to_numpy(dtype="float64")
        else:
            total_acr = np.zeros(n, dtype="float64")
        acr = total_acr / h_safe                    # rata-rata penjualan harian
        with np.errstate(divide="ignore", invalid="ignore"):
            dev_to_bom = np.where(total_acr > 0, deviasi / total_acr, 0.0)
        # v3.9.27 — STOK SEHARUSNYA = W sheet 'Data Base Cek Deviasi'
        # (SO(H-1) + IN_H − KIRIMAN KELUAR_H − PENJUALAN_H — bukti data
        # real: MLGPAR/ADONAN GORENG sheet 72.589,5 vs rumus lama
        # 83.098,5). v3.9.51: kolom TAMPILAN 'Stok Seharusnya' diganti
        # 'Dev. Bulan Lalu' (lihat COLUMNS); nilai W tetap hidup sebagai
        # variabel `stok` di blok CEK kondisi-3 'Hitung Manual' di bawah
        # — rumus persis sama (so_m1 + in_h − bk_h − out_h).

        # --- CEK vektorisasi (np.select — urutan kondisi PERSIS versi lama) ---
        barang_s = pivot["Nama Barang"].astype(str)
        aktif_s = (barang_s.map(self._aktif_lookup).fillna("")
                   .astype(str).str.strip().str.upper())
        # v3.9.13: KATEGORI per barang (v3.9.29: kolom TABEL dihapus —
        # nilai tetap dipakai filter combobox post-pivot; konvensi '-'
        # bila kosong — identik in_selisih_view).
        kategori_s = (barang_s.map(self._kategori_lookup).fillna("-")
                      .astype(str))
        a = aktif_s.to_numpy()

        cond_kosong = ((a == "AKTIF") & (so_h < 0)) | \
                      ((a == "NON AKTIF") & (so_h > 0))

        # v3.9.27 (user: "Kondisi beda tanggal kok menghasilkan data kosong
        # semua? cek file 01.1 CEK STOCK V2.xlsb bagian sheet Data Base
        # Cek Deviasi KOLOM Y ... cek semua logika nya dan bandingkan
        # dengan yang ada di program") — KONDISI 2 "Beda Tanggal" kini
        # PORT PERSIS formula LET sheet (audit 42: simulasi 2.120 baris
        # workbook = label cached Y 128/129 eksak):
        #   v2 = (I>0 & H<F & J=0) | (H > F+50%F & I=0 & J=0)
        #   I = "In H" (IN di H) · F = SO(H-1) · H = SO_H ·
        #   J = "Out H" = KIRIMAN KELUAR di H.
        # DUA perbaikan vs v3.9.6-v3.9.26:
        # (1) J dulu dibaca dari 9.ACR (PENJUALAN) — SALAH sumber: sheet
        #     memakai KIRIMAN KELUAR (= 8.BARANG KELUAR app). Bukti data
        #     real: MLGPAR/ADONAN GORENG MEKAR — SO 202.000 > 110.289 +
        #     50%·110.289 dgn IN=0 & KIRIMAN KELUAR=0 → sheet "Beda
        #     Tanggal", app lama '' (out_h PENJUALAN 37.699,5 ≠ 0 mematikan
        #     kondisi). Perbaikan ini juga = akar masalah permintaan
        #     v3.9.22 ("Beda tanggal kok tidak ada ya"): pola asli nyaris
        #     tak pernah terpicu BUKAN karena datanya tak ada, melainkan
        #     salah kolom pembanding.
        # (2) ATURAN SO-STALE v3.9.22 (pasangan dgn tanggal SO nonzero
        #     terakhir < H) DIHAPUS — TIDAK ada di formula sheet; di data
        #     real ia menlabel mayoritas pasangan (H=25: 598/1.346 GR;
        #     H≥26: ~SEMUA) yang justru ber-DATA KOSONG (SO_H=0 → tampil
        #     '-' — itulah "menghasilkan data kosong semua" yang user
        #     pertanyakan), menenggelamkan label sheet yang bermakna.
        # Guard (so_m1 > 0) pada cabang-2 DIPERTAHANKAN (sheet tanpa
        # guard; data real 2.120 baris: 0 beda — pasangan F=0 & H>0 & I=0
        # & J=0 tak ada; guard hanya melindungi data sparse app).
        cond_tanggal = (((in_h > 0) & (so_h < so_m1) & (bk_h == 0)) |
                        ((so_m1 > 0) & (so_h > so_m1 + 0.5 * so_m1) &
                         (in_h == 0) & (bk_h == 0)))

        # v3.9.27 — kondisi 3 "Hitung Manual": STOK kini = W sheet
        # (= Stok Seharusnya): W = F + I − J − S = SO(H-1) + IN_H −
        # KIRIMAN KELUAR_H − PENJUALAN_H. Dulu stok = sistem + in_h −
        # out_h − bk_h (base SALDO AKHIR sistem) → 266 "Hitung Manual"
        # palsu di data real (base sistem + komponen ganda), mis.
        # PWKTAM/ADONAN PANGSIT: stok lama = 27.870+0−102.330−0 =
        # −74.460 → rasio 6,8 > 1,3 padahal W sheet = 553.695−102.330 =
        # 451.365 → rasio 0,039 — tidak terpicu. Ambang 1,3 tetap
        # (sel Y1 sheet), termasuk kasus W=0 & H≠0.
        stok = so_m1 + in_h - bk_h - out_h
        stok_safe = np.where(stok == 0, 1.0, stok)
        ratio = np.abs(so_h - stok) / np.abs(stok_safe)
        cond_manual = np.where(stok == 0, so_h != 0, ratio > 1.3)

        with np.errstate(divide="ignore", invalid="ignore"):
            drop_ratio = np.divide(
                so_h, so_m1, out=np.full(n, np.inf), where=so_m1 > 0)
        cond_drastis = (so_m1 > 0) & (drop_ratio < 0.5)

        # v3.9.6: kondisi ke-5 "ACR to BOM" — |Deviasi| melebihi ambang%
        # × Total ACR (BOM/penjualan 1..H): selisih stok lebih besar dari
        # pemakaian teoretis sebulan → pasti salah. Melengkapi port
        # formula LET (dulu "4 dari 5 kondisi — ACR butuh BOM, TODO");
        # kategori sama persis string sheet Follow UP / DEVIASI GR file
        # asli user.
        # v3.9.21 (user: "harusnya ada threshold > 80% absolute dan aku
        # bisa atur"): dulu kaku > 100% × Total ACR — kini ambang bisa
        # diatur (default 80; spinbox kedua tab; SharedACRThreshold).
        _acr_cut = float(self.acr_threshold) / 100.0
        cond_acr = (total_acr > 0) & (np.abs(deviasi) > _acr_cut * total_acr)

        # v3.9.19 — kondisi ke-0 "Promix 04" (PRIORITAS PERTAMA):
        # SO pasangan ini bersumber BUKAN "input so harian" (mis. promix
        # 04 dine in / take away — SO turunan sistem penjualan) → pola
        # CEK lain (naik/turun SO, rasio stok) tidak bermakna utk SO
        # turunan; tampilkan sumbernya. Tanpa data SOURCE DATA (pasangan
        # tanpa rekap SO) → kondisi tidak berlaku (bukan promix).
        so_src_s = pd.Series(
            [self._so_source_lookup.get((b, r), "")
             for b, r in zip(barang_s, pivot["NAMA RESTO"].astype(str))],
            index=barang_s.index,
        )
        cond_promix = so_src_s.str.strip().str.lower().ne("") \
            & so_src_s.str.strip().str.lower().ne("input so harian")

        # v3.9.23 (poin 6) — kondisi ke-1 "RI Balancing": pasangan punya
        # dokumen IN (bulan Nomor RI ≠ bulan Nomor PO, tanggal dok ≤ H).
        # PRIORITAS: tetap di bawah Promix 04 (SO turunan sistem — by
        # design v3.9.19), di ATAS kondisi pola numerik (Kosong/Tanggal/
        # Manual/Drastis/ACR): anomali STRUKTUR DOKUMEN (faktual — RI
        # benar-benar dibuat beda bulan dari PO) lebih pasti & lebih
        # actionable daripada heuristik pola angka. (v3.9.22-26 aturan
        # SO-stale pernah mendominasi 97,8% pasangan GR — dihapus
        # v3.9.27, lihat blok kondisi 2 di atas.)
        _ri_bal_pairs = getattr(self, "_ri_bal_pairs", frozenset())
        cond_ri_bal = np.array(
            [(b, r) in _ri_bal_pairs
             for b, r in zip(barang_s, pivot["NAMA RESTO"].astype(str))],
            dtype=bool,
        )

        cek = np.select(
            [cond_promix, cond_ri_bal, cond_kosong, cond_tanggal,
             cond_manual, cond_drastis, cond_acr],
            ["Promix 04", "RI Balancing", "Kosong/Non Aktif",
             "Beda Tanggal", "Hitung Manual", "Turun Drastis",
             "ACR to BOM"],
            default="",
        )

        # v3.9.51 — ANALISA DEVIASI LALU→KINI di teks CEK (user: "kolom
        # Cek tambahkan analisa Penurunan tertinggi, peningkatan tertinggi
        # atau berubah arah seperti pada tab laporan deviasi tab analisa.
        # Cuman tidak hanya penurunan tinggi atau peningkatan tinggi tapi
        # berapa persen penurunann atau peningkatan tersebut. Tapi hitung
        # penurunan dan peningkatan kuantiti deviasi di absolute dulu
        # ya."). Pembanding = |Deviasi(H)| vs |Σ Dev bulan lalu| —
        # ABSOLUT DULU (mirror v3.9.16 komparasi); klasifikasi mirror
        # ANALISA komparasi: tanda berlawanan → Berubah Arah; |selisih| ≤
        # toleransi → Stabil (TANPA label — CEK tetap fokus anomali);
        # selisih > 0 → Peningkatan Tertinggi +p%, < 0 → Penurunan
        # Tertinggi -p% (basis |lalu|; |lalu|=0 → label tanpa persen —
        # pembagian tak terdefinisi). Pasangan tanpa baris rekap lalu →
        # tanpa analisa. Segmen ditambahkan ke teks CEK dengan pemisah
        # ' · ' (label anomali check tetap di depan).
        _has_lalu = ~np.isnan(dev_lalu)
        _a_now = np.abs(deviasi)
        _a_lalu = np.abs(dev_lalu)
        _sel_l = _a_now - _a_lalu
        _tol_l = self._LALU_TOL_ABS + self._LALU_TOL_REL * _a_lalu
        _flip_l = _has_lalu & ((deviasi * dev_lalu) < 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            _pct_l = np.where(_a_lalu > 0, _sel_l / _a_lalu, np.nan)
        ana = []
        for i in range(n):
            if not _has_lalu[i]:
                ana.append("")
            elif _flip_l[i]:
                ana.append(self.ANALISA_ARAH_TXT)
            elif abs(_sel_l[i]) <= _tol_l[i]:
                ana.append("")                    # Stabil — tanpa label
            else:
                _lab = (self.ANALISA_NAIK_TXT if _sel_l[i] > 0
                        else self.ANALISA_TURUN_TXT)
                _p = _pct_l[i]
                if not np.isnan(_p):
                    _sp = (f"{abs(_p) * 100:,.1f}"
                           .replace(",", "\u00a0").replace(".", ",")
                           .replace("\u00a0", "."))
                    _lab = f"{_lab} {'+' if _p > 0 else '-'}{_sp}%"
                ana.append(_lab)
        if any(ana):
            cek = np.array(
                [f"{c} \u00b7 {a}" if (c and a) else (c or a)
                 for c, a in zip(cek, ana)], dtype=object)

        result = pd.DataFrame({
            "Resto": pivot["NAMA RESTO"].astype(str).to_numpy(),
            "Nama Barang": barang_s.to_numpy(),
            "Satuan": pivot["SATUAN"].astype(str).to_numpy(),
            "AKTIF/NON": aktif_s.to_numpy(),
            "KATEGORI": kategori_s.to_numpy(),   # v3.9.13
            "SO_H-2": so_m2,
            "SO_H-1": so_m1,
            "In_H-1": in_m1,
            "SO_H": so_h,
            "In_H": in_h,
            "Out_H": out_h,
            "BK_H": bk_h,
            "SO_H+1": so_p1,
            "In_H+1": in_p1,
            "SO_H+2": so_p2,
            "Sistem": sistem,
            "Deviasi": deviasi,
            "_ABS": np.abs(deviasi),
            "CEK": cek,
            # v3.9.6 — kategori Deviasi:
            "Max Deviasi": np.abs(deviasi),   # di-update per-barang di bawah
            "ACR": acr,
            "Total ACR": total_acr,
            "Dev to BOM%": dev_to_bom,
            "Dev. Bulan Lalu": dev_lalu,   # v3.9.53 — NaN = tanpa file/pasangan
        })
        # v3.9.53 — label sumber Dev. Bulan Lalu ("WEEK n · <bulan>") menempel
        # di frame pivot: view cache-HIT (PCS membaca frame yang SAMA via
        # SharedPivotCache) → label konsisten antar tab; dibaca _prepare_rows
        # utk status (None = tanpa file → petunjuk muat file tab 📋 ⚖).
        result.attrs["dev_lalu_label"] = lalu_label

        # v3.9.34 — kolom Nominal = Harga 41.09 (dinormalkan ke satuan
        # pasangan) × Deviasi (helper bersama nominal_common; None → NaN
        # bila barang tak ada di 41.09 / harga None / satuan tak
        # ter-cover rasio → tampil '-'). Cache (barang, satuan) → harga
        # = TUPLE (peta, dict) — PEMBACA memvalidasi identitas `is`
        # (v3.9.34a RACE FIX, mirror komparasi: worker in-flight dgn peta
        # lama boleh menulis — tuple ber-peta-lama otomatis dibuang saat
        # dibaca → rebuild dari peta aktif; load_data reset tetap jalan).
        # Out_H/BK_H TETAP dihitung di result (rumus internal Stok
        # Seharusnya & CEK) — hanya kolom TAMPILAN yang dihapus.
        _c34 = self._harga_pair_cache
        if _c34 is not None and _c34[0] is self.harga_map:
            _cache: dict = _c34[1]
        else:
            _cache = {}
            # v3.9.38 — pasangan Deviasi PERSIS 0 TAK PERLU CARI HARGA
            # (user: "Kuantiti Deviasi 0 takperlu cari harga. Cek juga
            # keseluruhan terkait ini"): lookup dilewati utk baris qty-0
            # (cache tetap dibangun utk pasangan ≠ 0 — pasangan lain
            # resto lain boleh memakai kunci sama).
            _devn34 = pd.to_numeric(result["Deviasi"], errors="coerce")
            for _b, _s, _d in zip(result["Nama Barang"].astype(str),
                                  result["Satuan"].astype(str), _devn34):
                if (_b, _s) in _cache:
                    continue
                if pd.notna(_d) and float(_d) == 0.0:
                    continue          # qty dev 0 → tak perlu harga
                _cache[(_b, _s)] = lookup_harga_pair(
                    self.harga_map, self.konversi_map, _b, _s)[0]
            self._harga_pair_cache = (self.harga_map, _cache)
        _hpn = [_cache.get((str(_b), str(_s)))
                for _b, _s in zip(result["Nama Barang"],
                                  result["Satuan"])]
        # v3.9.38 — Deviasi 0 → Nominal 0.0 TANPA harga (mirror
        # nominal_common; tampil '-' identik NaN — perubahan semantik:
        # bukan 'tanpa harga').
        result["Nominal"] = pd.Series(
            [0.0 if (pd.notna(_d) and float(_d) == 0.0)
             else (np.nan if _h is None else float(_h) * float(_d))
             for _h, _d in zip(_hpn, pd.to_numeric(
                 result["Deviasi"], errors="coerce"))],
            dtype="float64")

        if result.empty:
            return result

        # v3.9.51 — Rank lama (per-BARIS dalam kelompok barang — 1..k per
        # resto) DIHAPUS dari pivot: kini RANK PER BARANG (Σ|Deviasi|
        # kelompok) dihitung di _prepare_rows atas frame TERFILTER (benar
        # per tab GR/PCS + renumber mengikuti filter aktif) dan tampil
        # MERGE-VERTIKAL per kelompok (pola tab 🛒 Rincian PO).
        # Max Deviasi = max |Deviasi| per barang (semua resto — terverifikasi
        # dari sheet DEVIASI GR file asli: kolom == groupby-max ABS Deviasi)
        result["Max Deviasi"] = result.groupby("Nama Barang")["_ABS"] \
            .transform("max")

        result = result.drop(columns=["_ABS"])
        return result

    # =========================================================================
    # RENDER (async + batched — logika filter identik versi lama)
    # =========================================================================
    def _refresh(self, sync: bool = False):
        if self.data is None or self.data.empty:
            self.status_var.set("Belum ada data.")
            return
        if self._busy:
            self._pending = True
            return
        self._busy = True
        st = {
            # v3.9.13: seleksi kosong = filter aktif (0 baris) — jangan
            # ditelan truthiness `if s` (set() dari HeaderFilter baru
            # berarti "tidak ada baris", bukan "tanpa filter").
            "col_sel": {c: s for c, s in self._col_sel.items()
                        if s is not None},
            "tanggal_h": self.tanggal_h,
            "kategori": self._kategori_sel,   # v3.9.13
            "aktif": self._aktif_sel,         # v3.9.49 — filter AKTIF/NON
        }

        def work():
            # FIX D-01 (audit 2-d): capture data & H SEKALI di awal job.
            # Dulu cache.get/put + _compute_pivot membaca self.data /
            # self.tanggal_h BERULANG selama compute — main thread
            # (load_data setelah pipeline / Apply H) bisa menukarnya di
            # tengah → entry cache (data_baru, h_baru) berisi pivot
            # (data_lama, h_lama) → refresh berikutnya HIT cache basi:
            # angka pipeline LAMA tampil dengan data BARU, senyap.
            # Kini seluruh operasi job memakai identitas pra-capture.
            data = self.data
            h = self.tanggal_h
            # v3.9.53 — FILE deviasi (sumber kolom Dev. Bulan Lalu + analisa
            # CEK lalu-kini) di-capture SEKALI di awal job (pola FIX D-01);
            # identitasnya jadi BAGIAN KUNCI SharedPivotCache → file
            # berganti (load baru/tutup di tab ⚖) otomatis cache-MISS →
            # pivot dihitung ulang dgn file baru (on_lalu_file_changed
            # juga clear + refresh — dua lapis anti-stale).
            lalu_df = (self._lalu_provider() if self._lalu_provider
                       else None)
            if lalu_df is not None:
                lalu_map, lalu_label = dev_lalu_qty_map(lalu_df, h=h)
            else:
                lalu_map, lalu_label = {}, None
            pivot = None
            cache = self._shared_cache
            if cache is not None:
                # v3.9: lock dipegang SELAMA get+compute+put — GR & PCS
                # bisa refresh bersamaan (Apply H); tanpa lock kedua thread
                # sama-sama miss → compute dobel + entry tertimpa.
                with cache.lock:
                    pivot = cache.get(data, h, lalu_df)
                    if pivot is None:
                        pivot = self._compute_pivot(data, h, lalu_map,
                                                     lalu_label)
                        if pivot is not None:
                            cache.put(data, h, pivot, lalu_df)
            else:
                pivot = self._compute_pivot(data, h, lalu_map, lalu_label)
            self._cached_pivot = pivot
            self._cached_h = h
            return self._prepare_rows(st)

        def done(payload):
            self._render_rows(payload)

        # FIX B-01: _busy wajib di-reset saat compute GAGAL — tanpa ini
        # view mati permanen setelah 1x error (Apply H / filter / reset
        # berikutnya ditelan senyap oleh guard `if self._busy: return`).
        def on_error(err):
            self._busy = False
            self._pending = False
            self.status_var.set(f"⚠ Gagal menghitung deviasi: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menghitung deviasi…", on_error=on_error,
                  sync=sync)

    def _prepare_rows(self, st: dict) -> dict:
        """Pure pandas: filter cached pivot + sort → items tree (thread-safe)."""
        pivot_df = self._cached_pivot
        if pivot_df is None or pivot_df.empty:
            return {"items": [], "kpi": (0, 0.0, 0),
                    "status": "Tidak ada data."}

        # Filter by Satuan mode
        if self.satuan_mode == "GR":
            filtered = pivot_df[pivot_df["Satuan"].astype(str).str.upper() == "GR"]
        else:
            filtered = pivot_df[pivot_df["Satuan"].astype(str).str.upper() != "GR"]

        # v3.9.13: filter KATEGORI POST-PIVOT (SharedPivotCache tetap dihitung
        # 1× utk GR+PCS — permintaan user: "tambah filter kategori di tab
        # deviasi pcs dan gr"). KATEGORI per-barang (1:1) → filter ini
        # barang-granular.
        # v3.9.45 — passthrough HANYA seleksi default 'Deviasi' (kelas
        # 100383 tetap tampil by default); seleksi eksplisit lain STRICT
        # (fix "ganti kategori tidak terjadi apa apa" — 90% baris '-'
        # membuat passthrough universal v3.9.44 = filter no-op);
        # KATEGORI_BLANK_LABEL = khusus baris tanpa kategori master.
        _nblank_hidden = 0   # v3.9.53 — transparansi barang blank tersembunyi
        if st.get("kategori") and "KATEGORI" in filtered.columns:
            if st["kategori"] == KATEGORI_BLANK_LABEL:
                filtered = filtered[
                    kategori_blank_mask(filtered["KATEGORI"])]
                if filtered.empty:
                    # v3.9.46 — pesan KOSONG yang jujur (bukan generik):
                    # entry SELALU ada sekarang — bila 0 baris, bilang
                    # KENAPA (semua baris tampil di tab ini sudah
                    # berkategori master) supaya tak dicurigai bug.
                    return {"items": [], "kpi": (0, 0.0, 0),
                            "status": (
                                "0 baris tanpa kategori master — semua "
                                "barang yang tampil di tab "
                                f"{self.satuan_mode} ini sudah punya "
                                "kategori '21. DBS Kategori'.")}
            elif kategori_filter_mask(filtered["KATEGORI"],
                                      st["kategori"]) is not None:
                # v3.9.49 — entri GABUNGAN default (kategori Rekap Mentah).
                # v3.9.53 — kini STRICT: HANYA nilai kategori yang cocok
                # (user: "kok ada nama barang yang bukan kategori COM
                # Deviasi + Packaging Deviasi misal BASKOM STAINLESS 18
                # CM, BASKOM STAINLESS UK 26 CM dll coba cek apa ini
                # bug?" — passthrough blank v3.9.45 (a) membuat barang
                # TANPA kategori (BASKOM dll.) ikut tampil di seleksi
                # default. Proteksi kelas 100383 kini dipenuhi KATEGORI
                # REKAP v3.9.49 (barang ber-deviasi ber-kategori rekap
                # tetap tampil, mis. BUMBU PASTA KUAH (V.20)); kelas
                # TANPA kategori = entry '(Tanpa Kategori)' + jumlah
                # tersembunyi dinyatakan di status — tidak lenyap senyap).
                _mmask = kategori_filter_mask(
                    filtered["KATEGORI"], st["kategori"])
                _nblank_hidden = int((~_mmask & kategori_blank_mask(
                    filtered["KATEGORI"])).sum())
                filtered = filtered[_mmask]
            elif kategori_passthrough(st["kategori"]):
                _blank = kategori_blank_mask(filtered["KATEGORI"])
                filtered = filtered[
                    (filtered["KATEGORI"].astype(str)
                     == str(st["kategori"]))
                    | _blank]
            else:
                filtered = filtered[
                    filtered["KATEGORI"].astype(str)
                    == str(st["kategori"])]
            if filtered.empty:
                return {"items": [], "kpi": (0, 0.0, 0),
                        "status": "Tidak ada baris untuk kategori ini."}

        # v3.9.49 — filter AKTIF/NON (user: "kolom Aktif dan non aktif
        # pindah ke bagian filter dekat kategori aja" — pindahan kolom
        # tabel). Nilai pivot dinormalisasi (strip+upper) saat compute —
        # kecocokan identik CEK 'Kosong/Non Aktif'; '(Kosong)' = barang
        # tanpa status master (kelas 100383 — pola blank kategori).
        if st.get("aktif") and "AKTIF/NON" in filtered.columns:
            if st["aktif"] == "(Kosong)":
                filtered = filtered[
                    kategori_blank_mask(filtered["AKTIF/NON"])]
            else:
                _a = filtered["AKTIF/NON"].astype(str).str.strip().str.upper()
                filtered = filtered[_a == str(st["aktif"]).strip().upper()]
            if filtered.empty:
                return {"items": [], "kpi": (0, 0.0, 0),
                        "status": ("Tidak ada baris untuk status "
                                    f"AKTIF/NON '{st['aktif']}'.")}

        # v3.5: filter header ⧩ — kecocokan nilai TERFORMAT (identik dgn
        # yang tampil di tabel; menggantikan RESTO/Nama Barang combo)
        for col, sel in st["col_sel"].items():
            if col in filtered.columns:
                fmt = self._format_col_series(col, filtered[col])
                filtered = filtered[fmt.isin(sel)]

        if filtered.empty:
            # v3.9.68 — TRI-STATE (audit eksternal T1): bila penyebab 0
            # baris adalah seleksi ⧩ KOSONG (filter aktif — bisa terjadi
            # lintas sesi via restore), katakan EXPLISIT + cara keluar.
            _hint = zero_row_filter_message(st["col_sel"])
            _generic = (f"Tidak ada data "
                        f"{'GR' if self.satuan_mode == 'GR' else 'PCS'} "
                        f"setelah filter.")
            return {"items": [], "kpi": (0, 0.0, 0),
                    "status": _hint or _generic}

        filtered = (
            filtered
            .assign(_abs_dev=filtered["Deviasi"].abs())
            .sort_values(["Nama Barang", "_abs_dev"], ascending=[True, False])
            .drop(columns=["_abs_dev"])
        )

        # v3.9.65 — RANK PER-BARIS DALAM KELOMPOK (RESTORASI SEMANTIK
        # SHEET ASLI — user: "ada bug pada deviasi gr dan deviasi pcs
        # pada kolom rank, dimana data rank sama semua untuk tiap grup
        # barang"): era v3.9.51-64 memakai rank PER BARANG (Σ|Deviasi|
        # kelompok — konstanta semua baris grup; dibuat utk display
        # merge-vertikal yang SUDAH TIDAK ADA sejak v3.9.60/61) → user
        # melihat satu angka sama di seluruh baris tiap grup = dilaporkan
        # bug. Ground truth sheet 'DEVIASI GR'/'DEVIASI PCS' workbook asli
        # user (diverifikasi 1.124/1.124 baris dev≠0 EKSAK di v3.9.65):
        # Rank = RANK |Deviasi| BARIS INI di antara baris GRUP barangnya
        # (1 = deviasi terbesar dalam grup, per resto), method="min"
        # (seri berbagi rank, rank berikut MELONCAT — diprove pola ikat
        # 13,13,13,16 sheet asli), dan baris Deviasi==0/NaN → rank
        # KOSONG (972/972 baris nol di sheet asli kosong rank-nya).
        # Urutan render default (Nama Barang, |Dev| desc) = rank asc dalam
        # grup — layout identik sheet asli. Rank dihitung atas frame
        # TERFILTER (renumber per tab GR/PCS + filter aktif — kontrak
        # v3.9.51 dipertahankan).
        _abs_rank = pd.to_numeric(filtered["Deviasi"],
                                  errors="coerce").abs()
        _rank_row = (_abs_rank
                     .groupby(filtered["Nama Barang"].astype(str))
                     .rank(method="min", ascending=False))
        filtered = filtered.assign(
            Rank=_rank_row.where(_abs_rank.fillna(0) != 0))
        # v3.9.65 — filter ⧩ kolom Rank (derived): loop col_sel di atas
        # melewatkannya (kolom Rank baru ADA setelah assign ini — pivot
        # mentah tak memuatnya; dulu seleksi ⧩ Rank DITELAN SENYAP).
        # Diterapkan SETELAH rank dihitung: kecocokan nilai TERFORMAT
        # identik dgn kolom lain ('1' = baris rank-1 tiap kelompok,
        # '' = baris tanpa rank/dev 0).
        _sel_rank = st["col_sel"].get("Rank")
        if _sel_rank is not None and len(filtered):
            _fmt_rank = self._format_col_series("Rank", filtered["Rank"])
            filtered = filtered[_fmt_rank.isin(_sel_rank)]
            if filtered.empty:
                # v3.9.68 — TRI-STATE (audit eksternal T1): idem titik
                # filter kolom di atas — pesan jujur bila seleksi ⧩ Rank
                # kosong (bukan pesan generik).
                _hint_r = zero_row_filter_message(st["col_sel"])
                _generic_r = (f"Tidak ada data "
                              f"{'GR' if self.satuan_mode == 'GR' else 'PCS'} "
                              f"setelah filter.")
                return {"items": [], "kpi": (0, 0.0, 0),
                        "status": _hint_r or _generic_r}
        # v3.9.51 — pivot basi tanpa kolom baru (teoretis — cache direset
        # load_data): guard supaya _prepare_rows tetap jalan.
        if "Dev. Bulan Lalu" not in filtered.columns:
            filtered = filtered.assign(**{"Dev. Bulan Lalu": np.nan})

        col_ids = [c[0] for c in self.COLUMNS]
        n = len(filtered)
        total_dev = float(filtered["Deviasi"].abs().sum())
        cek_series = filtered["CEK"].astype(str).str.strip()
        # v3.9.51 — hitung baris ber-LABEL ANOMALI CHECK saja (7 label
        # tetap): baris yang teks CEK-nya HANYA segmen analisa lalu-kini
        # ('Berubah Arah' / 'Penurunan Tertinggi -25,0%' / dst) bukan
        # anomali check — jangan menggelembungkan angka 'CEK n' footer.
        _cek_primary61 = cek_series.str.split(" \u00b7 ").str[0]
        cek_count = int(_cek_primary61.isin(self._CEK_CHECK_LABELS).sum())
        # v3.9.61 — SEKAT WARNA KELOMPOK DIHAPUS (user): urutan render
        # tetap di-sort by (Nama Barang, |Dev| desc) → kelompok barang
        # KONTIGU (nama/rank per-baris tetap berdekatan satu kelompok),
        # TAPI tanpa pita latar bergantian — baris seragam putih. Mesin
        # band (grp_start/grp_id/grp_band → tag grp0/grp1 + reapply
        # pasca-sort) dihapus total.
        items = []
        fp_map = {}
        row_snaps = {}
        rank_map = {}    # v3.9.51 — iid → rank terformat (v3.9.65: per-baris)
        neg_cells = []    # v3.9.2 — per-cell minus (kolom Deviasi)
        zero_cells = []   # v3.9.2 — per-cell deviasi == 0
        hl_cells = []     # v3.9.18 — highlight kolom Deviasi & SO_H
        store = self.store
        asal = f"DEVIASI {self.satuan_mode}"
        # FIX 6d1-01 — index entri store lama (kunci fp era volatil 'cek'):
        # {identitas-stabil → kunci aktual}. Baris tetap ☑ meski label
        # CEK-nya berubah pasca-entri (ambang ACR to BOM / file lalu);
        # uncheck menghapus entri lama tsb via _followup_keys_for.
        legacy_fp = self._legacy_fp_index()
        # v3.3.1 FIX "Saldo SO kosong semua": vektorisasi v3.2 lupa memasukkan
        # kolom matrix selain SO_H/Sistem/Deviasi ke cols_np → semua kolom
        # SO_H-2 … SO_H+2, In, Out, BK jatuh ke `else 0` → selalu tampil "-".
        # Kini SEMUA kolom numerik diekstrak (identik perilaku v3.1 row.get).
        # v3.9.34 — Out_H/BK_H keluar tampilan (tetap dipakai rumus
        # internal); Nominal masuk jalur numerik (NaN tanpa harga → 0
        # → tampil '-').
        cols_np = {c: filtered[c].to_numpy() for c in
                   ("Resto", "Nama Barang", "Satuan",
                    "AKTIF/NON", "CEK")}   # v3.9.29 — KATEGORI keluar tampilan
        for c in ("SO_H-2", "SO_H-1", "In_H-1", "SO_H", "In_H",
                  "SO_H+1", "In_H+1", "SO_H+2",
                  "Sistem", "Deviasi", "Nominal",
                  "Dev to BOM%"):
            cols_np[c] = pd.to_numeric(
                filtered[c], errors="coerce").fillna(0).to_numpy(
                dtype="float64")
        # v3.9.51 — Dev. Bulan Lalu: NaN DIPERTAHANKAN (format khusus
        # _fmt_dev_lalu — '-' = tanpa rekap lalu vs '0' = ada, bernilai 0;
        # fillna(0) akan menyamarkan keduanya).
        cols_np["Dev. Bulan Lalu"] = pd.to_numeric(
            filtered["Dev. Bulan Lalu"], errors="coerce").to_numpy(
            dtype="float64")
        cols_np["Rank"] = filtered["Rank"].to_numpy()
        for i in range(n):
            barang = str(cols_np["Nama Barang"][i])
            resto = str(cols_np["Resto"][i])
            values = [""] * len(col_ids)  # ✓ diisi di bawah
            for j, col_id in enumerate(col_ids):
                if col_id == "✓":
                    continue
                val = cols_np[col_id][i] if col_id in cols_np else 0
                if col_id == "Rank":
                    # v3.9.60 — PER-BARIS (user: "nama barang tidak
                    # muncul dan hanya muncul sekali di tiap grup nama
                    # barangnya? kenapa"): era merge-vertikal v3.9.55-59
                    # menyimpan nilai HANYA di baris head + memindahkan
                    # nilai display mengikuti viewport saat scroll
                    # (sticky). Mekanik pemindah itu yang terus bocor di
                    # pemakaian nyata (baris lanjutan kelihatan kosong).
                    # Kini SETIAP baris membawa nilainya sendiri
                    # (v3.9.65: rank |Deviasi| PER-BARIS dalam kelompok —
                    # semantik sheet asli; dev 0/NaN → kosong) — nama/rank
                    # tak mungkin tak muncul di viewport mana pun,
                    # sort/clone/scroll mana pun (v3.9.61: tanpa band —
                    # baris seragam putih).
                    values[j] = self._fmt_int(val)
                elif col_id == "Nama Barang":
                    # v3.9.60 — idem: nama barang di SEMUA baris
                    # kelompoknya (lihat komentar kolom Rank). Nilai mentah
                    # tetap di snapshot utk double-click/TSV/follow-up.
                    values[j] = barang
                elif col_id == "Dev. Bulan Lalu":
                    values[j] = self._fmt_dev_lalu(val)
                elif col_id == "Dev to BOM%":
                    values[j] = self._fmt_pct(val)
                elif col_id == "Nominal":
                    # v3.9.51 — Currency Rp (user: "Semua data nominal
                    # diberi format Currency Rp") — NaN/0 tetap '-'.
                    values[j] = fmt_rp_cell(val)
                else:
                    values[j] = self._fmt_num(val)

            # v3.2: fingerprint + snapshot (raw, tanpa format tampilan)
            # v3.9.6: snapshot diperluas — kolom tanggal SO (H-2..H+2) +
            # Loss Surplus to BOM (= Dev to BOM%) utk format Follow Up
            # "seperti file sample" (sheet Follow UP file asli user).
            snap = {
                "asal": asal,
                "resto": resto,
                "barang": barang,
                "satuan": str(cols_np["Satuan"][i]),
                "aktif": str(cols_np["AKTIF/NON"][i]),
                "h": st["tanggal_h"],
                "so": float(cols_np["SO_H"][i]),
                "sistem": float(cols_np["Sistem"][i]),
                "deviasi": float(cols_np["Deviasi"][i]),
                "cek": (str(cols_np["CEK"][i]).split(" \u00b7 ")[0]),
                "so_m2": float(cols_np["SO_H-2"][i]),
                "so_m1": float(cols_np["SO_H-1"][i]),
                "so_p1": float(cols_np["SO_H+1"][i]),
                "so_p2": float(cols_np["SO_H+2"][i]),
                "loss_bom": float(cols_np["Dev to BOM%"][i]),
            }
            # FIX 6d1-01 — fp STABIL (bagian 'cek' volatil dinetralkan —
            # lihat _fp_stable): centang bertahan saat label CEK berubah;
            # entri lama dicocokkan lewat identitas-stabil (legacy_fp).
            fp = self._fp_stable(snap)
            checked = store is not None and (
                store.has(fp) or fp in legacy_fp)
            values[0] = CHECK_ON if checked else CHECK_OFF
            fp_map[f"row_{i}"] = fp
            row_snaps[f"row_{i}"] = snap
            # v3.9.51 — rank mentah per iid; v3.9.65 — nilai PER-BARIS
            # (rank |Deviasi| dalam kelompok — sort/auto-fit/clone-filter).
            rank_map[f"row_{i}"] = self._fmt_int(cols_np["Rank"][i])

            tags = []
            deviasi = cols_np["Deviasi"][i]
            if pd.notna(deviasi):
                # v3.9.2: minus merah PER CELL (kolom Deviasi saja) —
                # sebelumnya SATU nilai minus membuat SELURUH BARIS merah.
                # Fallback Tk 8: perilaku lama (tag per baris).
                if deviasi < 0:
                    if self._cell_tags:
                        neg_cells.append((f"row_{i}", "Deviasi"))
                    else:
                        tags.append("negative")
                elif deviasi == 0:
                    if self._cell_tags:
                        zero_cells.append((f"row_{i}", "Deviasi"))
                    else:
                        tags.append("zero_dev")
            # v3.9.34 — mirror pola Deviasi utk kolom Nominal: minus
            # merah PER CELL (NaN tanpa harga di-skip; fallback Tk 8 =
            # tag baris 'negative' — persis jalur Deviasi).
            nominal = cols_np["Nominal"][i] if "Nominal" in cols_np \
                else None
            if pd.notna(nominal) and nominal < 0:
                if self._cell_tags:
                    neg_cells.append((f"row_{i}", "Nominal"))
                else:
                    tags.append("negative")
            # v3.9.6: kolom kategori Deviasi — minus merah PER CELL juga di
            # "Dev to BOM%" & "Stok Seharusnya" (ACR/Total ACR/Max Deviasi
            # non-negatif by construction).
            if self._cell_tags:
                if cols_np["Dev to BOM%"][i] < 0:
                    neg_cells.append((f"row_{i}", "Dev to BOM%"))
                # v3.9.51 — Stok Seharusnya keluar tampilan; minus merah
                # kini ke kolom penggantinya (Dev. Bulan Lalu bisa negatif).
                _dl = cols_np["Dev. Bulan Lalu"][i]
                if not (isinstance(_dl, float) and np.isnan(_dl)) \
                        and _dl < 0:
                    neg_cells.append((f"row_{i}", "Dev. Bulan Lalu"))
            # v3.9.18 — highlight latar lembut kolom Deviasi & SO_H
            # (permintaan user: "highlight kolom deviasi dan kolom SO H")
            # utk SEMUA baris; dikumpulkan utk tag cell (Tk 9 — terukur
            # probe: bg cell-tag menang atas bg evenrow/oddrow; fallback
            # Tk 8 tanpa tint kolom).
            if self._cell_tags:
                for hl_col in self.HIGHLIGHT_COLS:
                    hl_cells.append((f"row_{i}", hl_col))
            # v3.9.51 — kecocokan tag warna pada LABEL UTAMA teks CEK
            # (segmen analisa lalu→kini setelah ' · ' tak memengaruhi
            # warna — label anomali check tetap pewarna).
            cek_val = cek_series.iloc[i].split(" \u00b7 ")[0]
            if cek_val == "Promix 04":           # v3.9.19 — kondisi ke-0
                tags.append("cek_promix")
            elif cek_val == "RI Balancing":      # v3.9.23 (poin 6) — ke-1
                tags.append("cek_ri_bal")
            elif cek_val == "Kosong/Non Aktif":
                tags.append("cek_kosong")
            elif cek_val == "Beda Tanggal":
                tags.append("cek_tanggal")
            elif cek_val == "Hitung Manual":
                tags.append("cek_manual")
            elif cek_val == "Turun Drastis":
                tags.append("cek_drastis")
            elif cek_val == "ACR to BOM":
                tags.append("cek_acr")
            # v3.9.61 — tanpa tag band kelompok (sekat warna dihapus —
            # user: "hilangkan warna untuk sekat visual tiap grup nama
            # barang"); tag tersisa hanya pewarnaan afektif (minus/nol/
            # label CEK).

            items.append(("", f"row_{i}", {"values": values,
                                            "tags": tuple(tags)}))

        status = (
            f"{n} baris {self.satuan_mode} · Total |Deviasi| "
            f"{self._fmt_num(total_dev)} · CEK {cek_count} · "
            f"H={st['tanggal_h']}")
        # v3.9.45 — transparansi passthrough: seleksi default Deviasi
        # meng-include baris tanpa kategori master → SEBUT jumlahnya di
        # status (kelas 100383 terlihat, bukan lega; entry
        # '(Tanpa Kategori)' utk melihat khusus kelas itu).
        if st.get("kategori") and kategori_passthrough(st["kategori"]) \
                and "KATEGORI" in filtered.columns:
            _nblank = int(
                kategori_blank_mask(filtered["KATEGORI"]).sum())
            if _nblank:
                status += (f" · {_nblank} tanpa kategori master "
                           f"(pilih '{KATEGORI_BLANK_LABEL}')")
        # v3.9.53 — transparansi seleksi default GABUNGAN kini STRICT:
        # barang tanpa kategori (BASKOM dll.) TERSEMBUNYI → jumlahnya
        # dinyatakan (bukan lenyap senyap — kelas 100383 tetap bisa
        # dibuka lewat entry '(Tanpa Kategori)').
        if _nblank_hidden:
            status += (f" · {_nblank_hidden} baris tanpa kategori "
                       f"tersembunyi (lihat '{KATEGORI_BLANK_LABEL}')")
        # v3.9.55 — F2 DIAGNOSTIK NOMINAL KOSONG (user: "ada deviasi yang
        # tidak ada nominal nya coba cek"): baris ber-Deviasi ≠ 0 tapi
        # Nominal '-' diklasifikasikan penyebabnya — (a) barang TANPA harga
        # di 41.09 (tak ada di sheet / harga NaN) vs (b) satuan rekap tak
        # ter-konversi ke satuan 41.09 (harga ADA — beda satuan, label
        # bintang). Jujur di status footer (bukan '-' misterius).
        _diag_nom = self._diag_nominal_kosong(filtered)
        if _diag_nom:
            _n_miss, _n_noharga, _n_nosat = _diag_nom
            status += (f" · {_n_miss} tanpa nominal "
                       f"({_n_noharga} tanpa harga 41.09 · "
                       f"{_n_nosat} satuan tak terkonversi)")
        # v3.9.53 — asal angka Dev. Bulan Lalu JELIHAT di status: minggu
        # + bulan file deviasi yang dipakai (minggu MENYESUAIKAN H), atau
        # petunjuk memuat file bila belum ada (kolom '-' jujur).
        _lalu_lab = None
        try:
            _lalu_lab = pivot_df.attrs.get("dev_lalu_label")
        except (AttributeError, TypeError, ValueError):
            _lalu_lab = None
        if _lalu_lab:
            status += f" · Dev. Bulan Lalu: file ⚖ {_lalu_lab}"
        elif "Dev. Bulan Lalu" in filtered.columns \
                and int(pd.isna(filtered["Dev. Bulan Lalu"]).sum()) > 0:
            status += (" · Dev. Bulan Lalu: — (muat file deviasi di tab "
                       "📋 ⚖ Komparasi)")
        return {"items": items, "kpi": (n, total_dev, cek_count),
                "status": status, "fp_map": fp_map, "row_snaps": row_snaps,
                "rank_map": rank_map,
                "neg_cells": neg_cells, "zero_cells": zero_cells,
                "hl_cells": hl_cells}

    def _diag_nominal_kosong(self, filtered) -> "tuple[int, int, int] | None":
        """v3.9.55 — (n_tanpa_nominal, n_tanpa_harga, n_satuan_tak_konversi)
        utk baris Deviasi ≠ 0 ber-Nominal NaN; None bila tidak ada baris
        seperti itu. Klasifikasi per pasangan (barang, satuan) via
        lookup_harga_pair — label '-' = tanpa harga 41.09; bintang '*' =
        harga ada tapi satuan tak ter-konversi (beda satuan). Hitungan =
        jumlah BARIS (lookup di-dedup per pasangan unik)."""
        try:
            _dev = pd.to_numeric(filtered["Deviasi"], errors="coerce")
            _nom = pd.to_numeric(filtered["Nominal"], errors="coerce")
            _miss = filtered[_dev.notna() & (_dev != 0) & _nom.isna()]
            if _miss.empty:
                return None
            cls: dict = {}
            for _b, _s in zip(_miss["Nama Barang"].astype(str),
                              _miss["Satuan"].astype(str)):
                key = (_b, _s)
                if key in cls:
                    continue
                _h, _lab, _bint = lookup_harga_pair(
                    self.harga_map, self.konversi_map, _b, _s)
                cls[key] = ("nosat" if _bint else "noharga") \
                    if _h is None else "ok"
            n_noharga = sum(1 for _b, _s in
                            zip(_miss["Nama Barang"].astype(str),
                                _miss["Satuan"].astype(str))
                            if cls.get((_b, _s)) == "noharga")
            n_nosat = sum(1 for _b, _s in
                          zip(_miss["Nama Barang"].astype(str),
                              _miss["Satuan"].astype(str))
                          if cls.get((_b, _s)) == "nosat")
            if n_noharga == 0 and n_nosat == 0:
                return None
            return (len(_miss), n_noharga, n_nosat)
        except (KeyError, TypeError, ValueError):
            return None

    def _render_rows(self, payload: dict):
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0): baris/iid di-render ulang
        # (_fp_map/_row_snaps segera diganti di bawah) → clone ⛶ yang
        # masih hidup memegang salinan LAMA (iid sama, pasangan berbeda)
        # → DITUTUP (clone basi lebih buruk daripada tertutup) + generasi
        # naik (guard handler ✓/double-click clone).
        self._render_gen += 1
        self._close_stale_clones()
        self.tree.delete(*self.tree.get_children())
        self._update_headings()
        self.header_filters.refresh_icons()
        self._fp_map = payload.get("fp_map", {})
        self._row_snaps = payload.get("row_snaps", {})
        # v3.9.51 — rank per iid (v3.9.65: nilai per-baris rank dalam
        # kelompok — dipakai _merge_value_get utk auto-fit/clone-filter)
        self._rank_map = payload.get("rank_map", {})
        # v3.9.2 — cell minus per-cell (dipasang ulang juga setelah sort/clone)
        self._neg_cells = payload.get("neg_cells", [])
        self._zero_cells = payload.get("zero_cells", [])
        # v3.9.18 — highlight kolom Deviasi & SO_H (dipasang ulang juga
        # setelah sort/clone — delete+reinsert me-reset tag cell)
        self._hl_cells = payload.get("hl_cells", [])
        # ringkasan (baris · total deviasi · anomali) ada di status footer —
        # KPI row atas tabel sudah dihapus (v3.2)
        self.status_var.set(payload["status"])

        def render_done():
            # v3.9.2: tag PER-CELL setelah semua item ter-insert
            self._reapply_render_decorations(self.tree)
            # v3.9.55 — F8: auto-fit kolom SEKALI per muat data (user:
            # "waktu pertama kali buka program sudah diset ke auto fit").
            autofit_tree_once(self, self.tree)
            self._busy = False
            if self._pending:
                self._pending = False
                self._refresh()
            elif self._pending_sort:
                # FIX B-08 (audit 2-b): mainkan sort yang mengantre saat
                # render batch — dulu klik sort saat rendering dibuang
                # SENYAP (tampak "tidak jalan").
                # v3.9.55 — pending_sort kini 3-tupel (col, reverse, parse)
                # — sort analisa CEK (tombol ▲/▼) juga bisa mengantre.
                col, rev, pse = self._pending_sort
                self._pending_sort = None
                self._sort_by(col, reverse=rev, parse=pse)

        insert_tree_items(self.tree, payload["items"], batch=500,
                          on_done=render_done)

    def _reapply_render_decorations(self, tree):
        """v3.9.49 — pasang ulang SEMUA dekorasi render pasca-insert/sort/
        filter-clone: tag per-cell (minus/nol/highlight). Satu pintu supaya
        semua jalur (render_done · _sort_by · on_after_filter clone ·
        on_render_done clone) konsisten.
        v3.9.51 — + reposisi strip header kolom In (HeadingTintOverlay).
        v3.9.55-59 — + merge-vertikal nilai nama/rank (era sticky).
        v3.9.60 — nilai PER-BARIS dari payload (bukan bagian dekorasi).
        v3.9.61 — band kelompok DIHAPUS (sekat warna dilepas user);
        dekorasi tinggal tag per-cell + tint header."""
        self._reapply_cell_tags(tree)
        _tint = getattr(tree, "_heading_tint", None)
        if _tint is not None and getattr(_tint, "_alive", False):
            with contextlib.suppress(tk.TclError):
                _tint.refresh()

    def _reapply_cell_tags(self, tree):
        """v3.9.2 — pasang ulang tag per-cell minus di tree manapun
        (tabel utama / clone ⛶). Sort = delete+reinsert → tag cell hilang
        → dipanggil lagi dari _sort_by dan on_render_done clone."""
        if not self._cell_tags:
            return
        # v3.9.42 — audit 61-c P1-2: guard list-non-kosong DIHAPUS —
        # render baru TANPA sel minus harus MENGHAPUS sel lama (list
        # kosong = clear di overlay — semantik replace); guard lama
        # meninggalkan label overlay STALE (nilai/warna lama menimpa
        # data baru — iid deterministik row_i).
        apply_cell_tag(tree, "neg_cell", self._neg_cells)
        apply_cell_tag(tree, "zero_cell", self._zero_cells)
        # v3.9.18 — highlight kolom Deviasi & SO_H (Tk 9; no-op Tk 8)
        apply_cell_tag(tree, "hl_cell", self._hl_cells)

    # =========================================================================
    # ⛶ PERBESAR (fullscreen)
    # =========================================================================
    def _maximize(self):
        mode_label = "GR" if self.satuan_mode == "GR" else "PCS"

        def filter_setup(new_tree):
            # v3.6: funnel ⧩ + sort jalan juga di window besar
            # FIX B-02 (audit 2-b): on_after_filter — tag minus per-cell
            # dipasang ulang setelah filter clone REBUILD (delete+insert);
            # fix v3.9.5 19-a #3 dulu hanya diterapkan di komparasi/laporan.
            # v3.9.56 — value_get merge-aware: filter clone ⛶ by Nama
            # Barang/Rank mencocokkan nilai RAW snapshot (kelompok UTUH
            # lolos; v3.9.60 nilai tree kini per-baris — RAW tetap kanonik).
            attach_clone_filters(
                new_tree,
                [c[0] for c in self.COLUMNS if c[0] != "✓"],
                get_values=self._col_values,
                value_get=self._merge_value_get,
                on_sort=lambda c, d, t=new_tree: self._sort_by(c, reverse=d,
                                                               tree=t),
                on_after_filter=lambda t=new_tree:
                    self._reapply_render_decorations(t))

        win, new_tree = open_tree_maximized(
            self.tree, f"Deviasi {mode_label} — CEK Anomaly",
            setup_tags=lambda t: self._setup_tags(t),
            on_double_click=self._on_double_click,
            on_filter_setup=filter_setup,
            on_render_done=self._reapply_render_decorations)  # v3.9.2/49 per-cell
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0): catat clone hidup +
        # generasi render saat dibuka (guard handler + penutupan saat
        # re-render — lihat _close_stale_clones).
        self._register_clone(win, new_tree)
        # v3.9.51 — strip header kolom In jalan juga di clone ⛶ (overlay
        # milik tree clone; label anak tree → mati otomatis saat window
        # clone ditutup).
        with contextlib.suppress(tk.TclError):
            HeadingTintOverlay(new_tree, list(self.IN_COLS),
                               self.IN_HEADER_COLOR)
        # v3.9.61 — tanpa band kelompok di clone ⛶ (sekat warna dihapus);
        # nilai nama/rank sudah per-baris di salinan item clone.
        # v3.2: kolom ✓ aktif juga di window perbesar (iid identik)
        new_tree.bind("<Button-1>", self._on_tree_click, add="+")
        return win, new_tree

    def _register_clone(self, win, new_tree):
        """v3.9.33 — AUDIT FIX (48-d HIGH / P0): catat window clone ⛶ yang
        hidup + generasi render saat dibuka (tree clone diberi atribut
        _view_gen; handler ✓/double-click memeriksanya)."""
        new_tree._view_gen = self._render_gen
        self._clone_wins.append(win)

    def _close_stale_clones(self):
        """v3.9.33 — AUDIT FIX (48-d HIGH / P0): tutup SEMUA clone ⛶ yang
        masih hidup — dipanggil saat data/re-render mengganti baris (iid
        dipetakan ulang; clone basi men-toggle pasangan SALAH). Window
        yang sudah ditutup user cukup dibersihkan dari daftar."""
        for w in self._clone_wins:
            try:
                if w.winfo_exists():
                    w.destroy()
            except tk.TclError:
                pass
        self._clone_wins = []

    def _on_tanggal_h_change(self):
        """Apply H dari tab GR (v3.9: satu-satunya jalur ubah H).

        Nilai baru disimpan ke SharedTanggalH → listener (tab PCS +
        Laporan + tab GR sendiri) ikut refresh.
        v3.9.5 FIX (audit 19-c #2 — P2): dulu refresh eksplisit JUGA
        dijalankan setelah set() — padahal listener GR sendiri sudah
        me-render → GR dirender 2× tiap klik Apply (sort/selection
        ter-reset dua kali, waktu render 2×). Kini refresh eksplisit
        hanya bila H TIDAK berubah (listener tidak menembak; perilaku
        lama Apply = re-render tetap terjaga)."""
        try:
            new_h = int(self.tanggal_h_var.get())
        except ValueError:
            # v3.9.59 — AUDIT FIX 2d-09: judul dialog EN 'Invalid' →
            # konvensi app Indonesia (pola widgets._validate_int).
            messagebox.showwarning("Input tidak valid",
                                   "Tanggal H harus angka",
                                   parent=self.winfo_toplevel())
            self.tanggal_h_var.set(str(self.tanggal_h))
            return
        if not (1 <= new_h <= 31):
            messagebox.showwarning("Input tidak valid",
                                   "Tanggal H harus 1-31",
                                   parent=self.winfo_toplevel())
            self.tanggal_h_var.set(str(self.tanggal_h))
            return
        changed = False
        if self._h_state is not None:
            # set() memicu listener (PCS + Laporan + GR sendiri) — refresh
            # #1 terjadi di listener; hanya jalan bila H benar-benar berubah
            changed = self._h_state.set(new_h)
        if not changed or self._dirty:
            # H sama (listener tidak menembak) / view belum pernah dirender
            # → refresh eksplisit tetap diperlukan (Apply = re-render)
            self.tanggal_h = new_h
            self._cached_pivot = None
            self._refresh()

    def _on_shared_h_changed(self, new_h: int):
        """Listener tab pengikut (v3.9): H diubah/reset → ikut tanpa input.

        Chip/entry nilai H diperbarui + pivot cache dilonggarkan + refresh
        (bila tab belum pernah dilihat: tetap dirty, di-refresh saat
        tab dibuka — ensure_refreshed)."""
        self.tanggal_h = int(new_h)
        self._cached_pivot = None
        self._cached_h = None
        if hasattr(self, "_h_chip_var"):
            self._h_chip_var.set(str(new_h))
        # FIX B-07: sync juga entry H di tab GR (reset dari tab lain)
        if self._h_editable and hasattr(self, "tanggal_h_var"):
            self.tanggal_h_var.set(str(new_h))
        # FIX 6d1-02 — load_data (instance ini / saudara GR-PCS) sedang
        # berjalan: JANGAN refresh di tengah load dengan state filter lama
        # — akhir load_data memanggil _refresh/_dirty tunggal dengan state
        # filter baru (lihat _load_depth).
        if type(self)._load_depth > 0:
            return
        if self._dirty:
            return          # belum pernah dirender — refresh saat tab dibuka
        # FIX C-08 (audit 2-c): pane TIDAK terlihat → cukup _dirty (pola
        # laporan/komparasi v3.9.5 audit 19-c #3) — dulu _prepare_rows
        # + render penuh dijalankan untuk tab tersembunyi (pemborosan;
        # pivot tetap 1× via SharedPivotCache, hanya render yang terbuang).
        if not self.winfo_ismapped():
            self._dirty = True
            return
        if self.data is not None and not self.data.empty:
            self._refresh()

    def _reset_filter(self):
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        self._reset_kategori()   # v3.9.13 — combobox kategori ikut di-reset
        self._reset_aktif()      # v3.9.49 — combobox AKTIF/NON ikut di-reset
        # FIX B-07: ✕ Reset Filter kini juga me-reset TANGGAL H ke default
        # — sebelumnya nilai H lama tetap aktif, semantik reset tidak total
        # dan membingungkan. (v3.9: reset lewat SharedTanggalH supaya KEDUA
        # tab Deviasi GR & PCS ikut kembali.)
        # v3.9.22: default = tanggal SO nonzero terakhir (dulu konstan 25;
        # user: "Tanggal harusnya tanggal 26 bukan dari tanggal 25") —
        # fallback 26 bila data tak ber-SO.
        # v3.9.5 FIX (audit 19-c #2): H berubah → listener GR sendiri sudah
        # me-render; refresh eksplisit hanya bila H TIDAK berubah (dulu:
        # dobel render tiap reset).
        _default_h = self._default_h_from_data(self.data) or 26
        h_changed = self.tanggal_h != _default_h
        if h_changed:
            self.tanggal_h = _default_h
            self._cached_pivot = None
            self._cached_h = None
            if self._h_state is not None:
                # set() men-trigger listener tab lain (termasuk entry/chip H);
                # pivot dihitung ulang 1× lewat SharedPivotCache.
                self._h_state.set(_default_h)
            if self._h_editable and hasattr(self, "tanggal_h_var"):
                self.tanggal_h_var.set(str(_default_h))
            if hasattr(self, "_h_chip_var"):
                self._h_chip_var.set(str(_default_h))
        if not h_changed or self._dirty:
            self._refresh()

    @staticmethod
    def _parse_num_id(s):
        """v3.9.6: parser sort format Indonesia: '1.234' = 1234,
        '(1.234)' = -1234, '-' = 0, '12,5' = 12.5, '26,97%' = 26.97.
        (Parser default widgets menganggap '1.234' = 1.234 dan '(5,00)%'
        = -500 — salah utk format Indonesia; identik fix komparasi v3.9.3.)
        v3.9.51: prefiks 'Rp ' (fmt_rp_cell — kolom Nominal) dibuang dulu
        ('Rp 1.825' → 1825, '(Rp 1.825)' → -1825)."""
        s = str(s).replace("%", "").replace("—", "").replace("Rp", "") \
            .strip()
        if s in ("-", ""):
            return 0.0
        neg = s.startswith("(") and s.endswith(")")
        if neg:
            s = s[1:-1]
        s = s.replace(".", "").replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            return 0.0
        return -v if neg else v

    def _sort_by(self, col: str, reverse: bool = True, tree=None,
                 parse=None):
        """Sort kolom — engine LINEAR v3.3 (delete+reinsert, bukan
        treemove O(n²) yang membekukan UI di tabel besar).
        v3.9.2: delete+reinsert me-reset tag PER-CELL → dipasang ulang.
        v3.9.6: parser Indonesia utk kolom numerik + 'Dev to BOM%'
        (persen) — nilai format '1.234.567'/'(5,00)%' kini terurut benar.
        v3.9.55 — (a) parse bisa di-pass pemanggil (tombol analisa CEK ▲/▼
        memakai parser tuple (tier, pct)); (b) kolom Nama Barang / Rank
        memakai value_get dari snapshot/_rank_map — kunci sort nilai
        PENUH per baris supaya kelompok bergerak utuh + urutan dalam
        kelompok stabil (v3.9.60 nilai tree kini per-baris — RAW tetap
        dipakai sebagai sumber kanonik). v3.9.65 — Rank kini per-baris
        (rank |Deviasi| dalam kelompok): sort Rank = urut numerik antar
        baris (grup boleh ter-interleave — baris rank-1 tiap grup
        teratas)."""
        if self._busy and tree is None:
            # FIX B-08 (audit 2-b): sort saat render batch → ANTRE, bukan
            # dibuang senyap (fix v3.9.5 19-b #6 dulu hanya sampai komparasi
            # & laporan — view ini terlewat).
            self._pending_sort = (col, reverse, parse)
            return   # render batch masih berjalan — sort ditunda (v3.3)
        tree = tree if tree is not None else self.tree
        # v3.9.34 — Out_H/BK_H keluar tampilan; Nominal masuk parser
        # format Indonesia (mis. '(1.825)' → -1825, '-' → 0).
        numeric_like = col in (
            "SO_H-2", "SO_H-1", "In_H-1", "SO_H", "In_H",
            "SO_H+1", "In_H+1", "SO_H+2", "Sistem", "Deviasi", "Rank",
            "Nominal", "Dev to BOM%", "Dev. Bulan Lalu")
        if parse is None:
            parse = self._parse_num_id if numeric_like else None
        # v3.9.55 — kunci sort kolom merge-vertikal dari sumber RAW
        value_get = None
        if col == "Nama Barang":
            _snaps = self._row_snaps

            def _vg_barang(iid, _s=_snaps):
                return str((_s.get(str(iid)) or {}).get("barang", ""))
            value_get = _vg_barang
        elif col == "Rank":
            _rmap = self._rank_map

            def _vg_rank(iid, _r=_rmap):
                return str(_r.get(str(iid), ""))
            value_get = _vg_rank
        sort_tree_by_column(tree, col, reverse=reverse, parse=parse,
                            value_get=value_get)
        # v3.9.49 — banding kelompok ikut dipasang ulang (urutan visual
        # berubah → band dihitung ulang; nilai per-baris tak berubah).
        self._reapply_render_decorations(tree)

    # v3.9.55 — SORT ANALISA CEK (tombol ▲ Kenaikan / ▼ Penurunan) --------
    _ANALISA_PCT_RE = re.compile(r"([+-])([\d.,]+)%")

    def _sort_analisa(self, mode: str):
        """v3.9.55 — sortir tabel oleh segmen ANALISA lalu→kini di teks
        CEK (user: "tombol buat sort kenaikan atau penurunan tertinggi
        berdasarkan kolom CEK yang compare dengan file deviasi bulan
        lalu").

        mode 'naik'  → 'Peningkatan Tertinggi +p%' teratas (p% terbesar
        dulu; tanpa persen (|lalu|=0) dianggap +∞ — peningkatan tanpa
        dasar pembanding), lalu 'Berubah Arah', lalu sisanya.
        mode 'turun' → 'Penurunan Tertinggi -p%' teratas (penurunan
        terdalam dulu; tanpa persen = -∞), lalu 'Berubah Arah', lalu
        sisanya. Urutan relatif baris sebanding dipertahankan (sort
        Python stabil). Sort ASCENDING dgn kunci majemuk (2-tier, ±pct)
        — tier 2 → grup pertama, pct dibalik tanda sesuai mode supaya
        SATU arah sort menghasilkan urutan benar utk KEDUA mode (dulu
        tuple (tier, pct) + reverse per mode membuat turun terbalik:
        baris TANPA label naik ke atas)."""
        parse = self._analisa_parse(mode)
        self._sort_by("CEK", reverse=False, parse=parse)

    def _analisa_parse(self, mode: str):
        """Parser sort utk teks CEK → tuple kunci ASCENDING:
        (2 - tier, ±pct) — tier 2 = baris ber-label analisa arah mode,
        1 = 'Berubah Arah', 0 = lainnya; pct dibalik tanda utk mode
        'naik' (persen terbesar → kunci terkecil = teratas) dan
        dipertahankan bertanda utk 'turun' (penurunan terdalam =
        terkecil = teratas; tanpa persen → -∞). Tuple konsisten (tanpa
        mixed-type) di dlm sort_tree_by_column."""
        naik = mode == "naik"
        naik_txt = self.ANALISA_NAIK_TXT
        turun_txt = self.ANALISA_TURUN_TXT
        arah_txt = self.ANALISA_ARAH_TXT
        rex = self._ANALISA_PCT_RE

        def parse(s):
            t = str(s)
            label_hit = (naik_txt if naik else turun_txt)
            if label_hit in t:
                m = rex.search(t)
                if m:
                    pct = float(m.group(2)
                                .replace(".", "").replace(",", "."))
                    if m.group(1) == "-":
                        pct = -pct
                else:
                    # tanpa persen (|lalu|=0): kunci akhir -∞ di KEDUA mode
                    # (naik membalik tanda → sentinel inf; turun langsung).
                    pct = float("inf") if naik else float("-inf")
                # naik: persen terbesar dulu → balik tanda; turun:
                # penurunan terdalam (paling negatif) dulu → tanda asli.
                return (0, (-pct if naik else pct))
            if arah_txt in t:
                return (1, 0.0)
            return (2, 0.0)
        return parse

    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten."""
        auto_fit_columns(self.tree)

    # =========================================================================
    # DOUBLE-CLICK → POPUP (tree-agnostic via event.widget)
    # =========================================================================
    def _on_double_click(self, event):
        if self.data is None or self.data.empty:
            return

        tree = event.widget
        # v3.9.33 — AUDIT FIX (48-d HIGH / P0): clone ⛶ generasi lama
        # (dibuka sebelum re-render terakhir) → snapshot H/_row_snaps
        # tidak lagi cocok dgn baris clone → DIABAIKAN senyap.
        if getattr(tree, "_view_gen", None) not in (None, self._render_gen):
            return
        row_iid = tree.identify_row(event.y)
        if not row_iid:
            return

        # v3.3: double-click di sel kolom ✓ = toggle follow-up
        # (dulu tetap membuka popup detail — kurang intuitif)
        # v3.7 FIX: cocokkan NAMA kolom (bukan posisi display '#1') —
        # setelah kolom ✓ disembunyikan, posisi #1 jatuh ke kolom lain.
        try:
            if identify_to_column(tree, tree.identify_column(event.x)) == "✓":
                self._on_tree_click(event)
                return
        except Exception:
            pass

        values = tree.item(row_iid, "values")
        if not values:
            return

        col_ids = [c[0] for c in self.COLUMNS]
        row_data = dict(zip(col_ids, values))
        # v3.9.55 — pasangan dibaca dari SNAPSHOT RAW (nilai tak
        # terformat → lebih aman; v3.9.60 nilai tree kembali per-baris,
        # snapshot tetap sumber kanonik).
        # _view_gen guard di atas memastikan snapshot cocok dgn render
        # tree ini (clone basi diabaikan).
        _snap = self._row_snaps.get(str(row_iid))
        if _snap is not None:
            nama_barang = _snap.get("barang") or row_data.get("Nama Barang")
            nama_resto = _snap.get("resto") or row_data.get("Resto")
            satuan = _snap.get("satuan") or row_data.get("Satuan")
        else:
            nama_barang = row_data.get("Nama Barang")
            nama_resto = row_data.get("Resto")
            satuan = row_data.get("Satuan")

        if not nama_barang:
            return

        # v3.9.18 — POPUP RINGKAS (permintaan user: "pop up di deviasi GR
        # ataupun PCS hanya tampilkan: nama barang, nama resto, nilai
        # saldo akhir, nilai SO, nilai IN, nilai deviasi"): popup source
        # rows lama (JENIS/Nomor/Nomor PO/Tgl-Jam/KATEGORI/SOURCE) DIGANTI
        # tabel ringkas per Tanggal — hanya Nama Barang · Nama Resto ·
        # Saldo Akhir · SO · IN · Deviasi. Popup source rows lama tetap
        # dipakai tab lain (Pivot/Laporan) — tidak tersentuh.
        from src.ui.deviasi_popup import show_deviasi_popup
        root = self.winfo_toplevel()

        show_deviasi_popup(
            root, self.data,
            nama_barang=nama_barang,
            nama_resto=nama_resto,
            satuan=satuan,
            h=self.tanggal_h,
        )

    # =========================================================================
    # HELPERS (identik versi lama)
    # =========================================================================
    @staticmethod
    def _fmt_num(val) -> str:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            v = float(val)
        except (TypeError, ValueError):
            return str(val)
        if v == 0:
            return "-"
        # FIX C-03: format angka gaya Indonesia — 1.234.567 / 1.234,5
        # (sebelumnya koma gaya Inggris: 1,234,567 / 1,234.5).
        if v == int(v):
            s = fmt_int_id(v)
        else:
            s = f"{v:,.1f}".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
        if v < 0:
            return f"({s[1:]})"
        return s

    @staticmethod
    def _fmt_int(val) -> str:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            return str(int(val))
        except (TypeError, ValueError):
            return str(val)

    @staticmethod
    def _fmt_dev_lalu(val) -> str:
        """v3.9.53 — Dev. Bulan Lalu (FILE deviasi ⚖): NaN (tanpa file /
        pasangan tak ada di file) → '-'; 0 → '0' (ADA data bernilai nol
        — dibedakan dari tanpa data); lainnya NILAI ASLI bertanda format
        Indonesia (minus dalam kurung + merah per-cell — plus = surplus
        polos; absolut TIDAK dipakai di tampilan, hanya di hitungan
        analisa CEK)."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "-"
        try:
            v = float(val)
        except (TypeError, ValueError):
            return str(val)
        if v == 0:
            return "0"
        if v == int(v):
            s = fmt_int_id(v)
        else:
            s = f"{v:,.1f}".replace(",", "\u00a0").replace(
                ".", ",").replace("\u00a0", ".")
        return f"({s[1:]})" if v < 0 else s

    @staticmethod
    def _fmt_pct(val) -> str:
        """v3.9.6: ratio (0.2697) → '26,97%' (kolom Dev to BOM%) — format
        identik komparasi/laporan (Indonesia, minus kurung, -0.0 → 0,00%)."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "—"
        try:
            val = float(val)
        except (TypeError, ValueError):
            return str(val)
        if val == 0:
            return "0,00%"
        s = f"{val * 100:,.2f}".replace(",", "\u00a0").replace(
            ".", ",").replace("\u00a0", ".")
        if val < 0:
            return f"({s[1:]})%"
        return f"{s}%"
