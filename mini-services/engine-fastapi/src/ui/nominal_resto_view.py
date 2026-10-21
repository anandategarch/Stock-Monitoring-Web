"""
nominal_resto_view.py — v3.9.34 TAB BARU 🧮 Nominal Deviasi (user:
"ada tab nominal Deviasi itu isinya Total sum dari nama barang kayak
di laporan sampel kolom nominal deviasi yang dapat dari harga ×
kuantitas deviasi cuman ini disum per resto").

Baris = SATU RESTO — Σ Nominal Deviasi seluruh barang pasangannya
(Nominal = Harga 41.09 × Qty Deviasi tanggal H; pasangan tanpa harga
TIDAK ikut Σ — kolom 'Tanpa Harga' transparan). Sesuai laporan sampel
user ('20.AGUSTUS 2026.xlsx' — kolom NOMINAL DEVIASI per bahan per
resto), diagregasi per resto. Baris TOTAL di ujung. Double-click baris
resto → popup RINCIAN per barang resto itu. Urutan default |Σ Nominal|
MENURUN.

v3.9.36 (user: "di tab nominal deviasi bisa pop up per item dengan
kolom: Nama resto, nama barang, Kuantiti deviasi, Nominal deviasi
Sekarang, Nominal deviasi bulan lalu" + "tambah filter Kategori dengan
default pilihan Kategori = Deviasi ... Yang tanpa harga juga bisa pop
up untuk tampilkan tanpa harga item apa aja"):
  - POPUP RINCIAN 5 KOLOM: Nama Resto · Nama Barang · Kuantiti Deviasi
    · Nominal Deviasi Sekarang · Nominal Deviasi Bulan Lalu. 'Bulan
    Lalu' = FILE DEVIASI tab ⚖ Komparasi (parse_deviasi_file — bulan
    TERBARU di file + minggu TERAKHIR per pasangan; harga 41.09 × DEV
    Lalu; perhitungan = nominal_common.hitung_nominal_lalu_pairs).
    File berganti/ber-load → app memanggil on_lalu_file_changed()
    (pola listener SharedTanggalH); tanpa file → kolom '-' + footer
    petunjuk.
  - FILTER KATEGORI (pola deviasi_view v3.9.19): combobox 'Semua' =
    tanpa filter; DEFAULT 'Deviasi' (case-insensitive, fallback
    'Semua'); diterapkan pra-compute di _compute_resto.
  - DOUBLE-CLICK KOLOM 'Tanpa Harga' → popup daftar barang TANPA HARGA
    resto itu (TOTAL row = semua resto) + alasan (tak ada di 41.09 /
    satuan tak terkonversi).

v3.9.38 (user: "Nominal Deviasi total per resto juga tambahan di tab
nominal deviasi ini buat versus bulan lalu"):
  - KOLOM BARU 'Nominal Deviasi Bulan Lalu' per resto = Σ 'Nominal Lalu'
    self._lalu_df (file deviasi ⚖ Komparasi) per resto-norm; resto tanpa
    baris di file → '-' ; baris TOTAL menjumlah; minus merah per-cell;
    filter header + sort numerik; footer/chip menyebut TOTAL LALU (atau
    petunjuk bila file belum dimuat).
  - QTY DEVIASI 0 tak dihitung 'tanpa harga' (aturan v3.9.38
    nominal_common — Nominal 0.0 ≠ None).
  - SUMBER 'Nominal Lalu' = KOLOM NOMINAL DEVIASI MILIK FILE (v3.9.38):
    angka RESMI laporan bulan lalu — bukan hitung ulang harga 41.09
    sekarang (temuan user: BUMBU PASTA KUAH (V.20) 41.09 sekarang
    107,6386854/GR — sama dgn hitungan manual — vs harga snapshot file
    ±113,048/GR → nominal beda; kini nominal lalu = angka file).

v3.9.41 (user: "pop up tab nominal deviasi ada bug kurang besar dan
lebar coba cek juga" + "Nominal deviasi pembanding dari bulan llau
sesuai kan week nya jika week 1 maka ambil data week 1 juga"):
  - POPUP BESAR & RESPONSIF: jendela ±94%×88% layar (dulu maks
    1000×560), lebar kolom DISKALA memenuhi lebar jendela (dulu fixed
    660px → sisi kanan kosong), re-scale otomatis saat user resize
    (<Configure>, idempoten dari basis), tombol ⛶ Perbesar + ↺ Muat
    Lebar; minsize dinaikkan (900×420). Popup tanpa-harga ikut.
  - MINGGU PEMBANDING TER-COCOK: h diteruskan ke
    hitung_nominal_lalu_pairs → minggu file yang MEMUAT H analisa
    (H 1-7 → WEEK 1; 8-14 → WEEK 2; 15-31 → WEEK 3/4) — dulu SELALU
    minggu terakhir (penutupan bulan) → minggu-1 vs minggu-4 = apple-
    to-oranges. Minggu terpilih DISEBUT di head + footer popup +
    footer tabel; kolom internal '_minggu' di frame lalu.

Perhitungan = src/ui/nominal_common.py (satu sumber kebenaran dgn
mode 💰 Nominal (H) tab 📋 Laporan Deviasi, kolom Nominal tab 📦
Deviasi GR/🧩 PCS & mode ⚖ Komparasi — v3.9.34).

v3.9.63 — RESTRUKTURISASI KOLOM + ANAK TAB (user: "kolom N Barang
dan Tanpa harga hapus aja diganti dengan nominal deviasi per kategori
yaitu kolom COM Deviasi + kolom Biaya Packaging ... jadi format kolomnya
Resto · Com deviasi · Biaya packaging · Nominal deviasi H · Nominal
deviasi bulan lalu · Persen kenaikan/penurunan (bisa sort) ... dan itu
buat anak tab baru di nominal deviasi yang menampilkan secara global"):
  - KOLOM BARU 'COM Deviasi' + 'Biaya Packaging' = Σ nominal pasangan
    per klas kategori (substring 'COM'/'PACKAGING' — nominal_common);
    'N Barang' + 'Tanpa Harga' DIHAPUS dari tabel (Σ pasangan & jumlah
    tanpa harga tetap dihitung agregasi — footer status + anak tab).
  - KOLOM BARU 'Persen Kenaikan/Penurunan' = (H − Lalu) ÷ |Lalu| × 100
    (hitung_persen_kenaikan; sort numerik + minus merah per-cell).
  - ANAK TAB (sub-notebook): 'Per Resto' (tabel utama + filter KATEGORI
    utama — perilaku lama) + 'Tanpa Harga' BARU — daftar barang tanpa
    harga GLOBAL (semua resto & kategori, TANPA filter kategori tab
    utama — pasangan_tanpa_harga_global) + kolom Kategori + filter
    KATEGORI SENDIRI (default 'Semua' = global; memilih 'Deviasi (COM +
    Packaging)' → hanya menampilkan sesuai kategori itu — permintaan
    user). Menggantikan popup double-click kolom 'Tanpa Harga'.

TANGGAL H = state bersama (SharedTanggalH — chip read-only + auto-
refresh dari tab 📦 Deviasi GR; pola mode Nominal). Minus merah
per-cell; format angka Indonesia; filter header ⧩ + sort (TOTAL dipin
di ujung) + ⛶ Layar Penuh + ⤢ Perbesar Tabel + ◱ Kolom + ↔ Auto-Fit
+ Ctrl+C salin baris terpilih (multi-select).
"""
import contextlib
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

import pandas as pd

from .nominal_common import (
    _norm_name_lalu,
    _norm_resto_lalu,
    agregasi_nominal_per_resto,
    fmt_nominal_cell,
    fmt_pct_cell,  # v3.9.63 — kolom Persen Kenaikan/Penurunan
    fmt_rp_cell,
    hitung_nominal_lalu_multi,  # v3.9.45 — multi-bulan file deviasi
    hitung_persen_kenaikan,  # v3.9.63 — idem
    pasangan_tanpa_harga_global,  # v3.9.63 — anak tab Tanpa Harga global
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
    LoadingOverlay,
    TableExpander,
    apply_cell_tag,
    apply_col_sel_restore,  # v3.9.66 — filter persisten antar sesi
    attach_clone_filters,
    auto_fit_columns,
    autofit_tree_once,  # v3.9.55 — F8
    col_sel_to_json,  # v3.9.66 — filter persisten antar sesi
    enable_col_resize,
    enable_multi_select,
    fmt_int_id,
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

# kolom popup rincian per resto (double-click) — v3.9.36 (user: "pop up
# per item dengan kolom: Nama resto, nama barang, Kuantiti deviasi,
# Nominal deviasi Sekarang, Nominal deviasi bulan lalu")
# v3.9.41 — lebar basis DILEBARKAN + kolom DISKALA memenuhi lebar
# jendela (user: "pop up tab nominal deviasi ada bug kurang besar dan
# lebar" — dulu total 660px di jendela 1000px → sisi kanan kosong).
POPUP_COLUMNS = [
    ("Nama Resto", 110, "w"),
    ("Nama Barang", 260, "w"),
    ("Kuantiti Deviasi", 120, "e"),
    ("Nominal Deviasi Sekarang", 160, "e"),
    ("Nominal Deviasi Bulan Lalu", 160, "e"),
]

# kolom popup barang TANPA HARGA — v3.9.63 kini ANAK TAB 'Tanpa Harga'
# GLOBAL (menggantikan popup double-click kolom 'Tanpa Harga' yang
# dihapus; user: "buat anak tab baru di nominal deviasi yang menampilkan
# secara global") + kolom KATEGORI (user: "sesuai kategori yang
# difilter misal deviasi COM +packaging berarti hanya menampilkan
# sesuai kategori aja" — kategori terlihat & bisa difilter sendiri).
NOHARGA_COLUMNS = [
    ("Resto", 110, "w"),
    ("Kategori", 150, "w"),
    ("Nama Barang", 260, "w"),
    ("Satuan", 70, "w"),
    ("Kuantiti Deviasi", 120, "e"),
    ("Keterangan", 240, "w"),
]


# ---------------------------------------------------------------------------
# v3.9.41 — POPUP BESAR + KOLOM RESPONSIF (user: "pop up tab nominal
# deviasi ada bug kurang besar dan lebar coba cek juga"):
# (1) jendela ±94% × 88% layar (dulu maks 1000×560 — terasa kecil di
#     monitor besar);
# (2) lebar kolom DISKALA memenuhi lebar jendela (proporsional bobot
#     basis; dulu kolom fixed 660px → sisa kanan jendela kosong abu);
# (3) re-scale OTOMATIS saat user me-resize jendela (binding <Configure>,
#     idempoten — selalu hitung ulang dari lebar basis, tanpa drift);
# (4) tombol ⛶ Perbesar (toggle ~layar penuh) + ↔ Muat Lebar (reset).
# ---------------------------------------------------------------------------
def _popup_geometry(win, w_max=2600, h_max=1440,
                    w_frac=0.94, h_frac=0.88) -> "tuple[int, int]":
    """Geometri popup adaptif besar + clamp posisi tengah layar.
    → (w, h) aktual (utk skala kolom awal).
    v3.9.41: batas atas DINAIKKAN (1800×900 — layar besar 1920 kini
    benar-benar 'besar & lebar'; dulu cap 1000×540 + 0.85×0.8 layar →
    terasa kecil; user: "pop up ... kurang besar dan lebar").
    v3.9.42 — audit 61-b P2: cap DINAIKAN lagi (2600×1440) — cap 1800
    membuat popup di monitor >1920 TIDAK proporsional (2560×1440 →
    1800×900 = 70%×62% layar; 4K → 47%). kini proporsional penuh di
    layar ≤2600px."""
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
    except tk.TclError:
        return w_max, h_max
    w = min(w_max, max(720, int(sw * w_frac)))
    hgt = min(h_max, max(420, int(sh * h_frac)))
    x = max(0, min(int(sw / 2 - w / 2), sw - w))
    y = max(0, min(int(sh / 2 - hgt / 2), sh - hgt))
    try:
        win.geometry(f"{w}x{hgt}+{x}+{y}")
    except tk.TclError:
        pass
    return w, hgt


def _scale_popup_columns(tree, col_spec, avail_w) -> None:
    """Skala lebar kolom memenuhi avail_w (proporsional bobot basis).

    Idempoten: selalu hitung ulang DARI LEBAR BASIS (bukan lebar
    sekarang) → dipanggil berulang (resize) tidak men-drift. avail_w
    lebih kecil dari total basis → kolom kembali ke basis (scroll-x
    treeview ambil alih)."""
    total = sum(w for _n, w, _a in col_spec)
    if total <= 0:
        return
    extra = max(0, int(avail_w) - total)
    for name, w, _anchor in col_spec:
        new_w = w + int(extra * w / total)
        try:
            tree.column(name, width=new_w)
        except tk.TclError:
            pass


def _bind_popup_rescale(win, tree, col_spec) -> None:
    """Re-scale kolom saat jendela popup di-resize user (<Configure>;
    guard delta >8px supaya tidak churn loop."""
    def _on_cfg(e, _tree=tree, _spec=col_spec, _win=win):
        if e.widget is not _win:
            return
        last = getattr(_win, "_rescale_w", None)
        if last is not None and abs(e.width - last) < 8:
            return
        _win._rescale_w = e.width
        # v3.9.42 — audit 61-b P3: simpan ukuran manual TERAKHIR (bukan
        # saat maks) → ⛶ toggle balik ke ukuran manual terakhir user
        # (dulu geometri tersimpan saat toggle PERTAMA — resize manual
        # setelahnya terlupakan).
        if not getattr(_win, "_is_max", False):
            _win._geom_manual_wh = (e.width, e.height)
        _scale_popup_columns(_tree, _spec, e.width - 36)
    try:
        win.bind("<Configure>", _on_cfg, add="+")
    except tk.TclError:
        pass


def _toggle_popup_max(win, tree, col_spec) -> None:
    """Toggle ⛶ Layar Penuh: ~layar penuh ↔ geometri normal (kolom ikut
    re-scale via binding <Configure>).
    v3.9.59 — FIX 2e-07/2f-13: label kanon ⛶ = 'Layar Penuh' (aksi
    resize jendela sendiri ke ~ukuran layar — bukan clone window).
    v3.9.42 — audit 61-b P3: restore memakai ukuran manual TERAKHIR
    (di-save binding <Configure>) — bukan geometri saat toggle pertama."""
    is_max = getattr(win, "_is_max", False)
    try:
        if not is_max:
            win._geom_normal = win.geometry()
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            win.geometry(f"{max(720, sw - 16)}x{max(420, sh - 72)}+8+32")
            win._is_max = True
        else:
            wh = getattr(win, "_geom_manual_wh", None)
            geom = getattr(win, "_geom_normal", None)
            if wh:
                sw = win.winfo_screenwidth()
                sh = win.winfo_screenheight()
                w, h = wh
                x = max(0, min(int(sw / 2 - w / 2), sw - w))
                y = max(0, min(int(sh / 2 - h / 2), sh - h))
                win.geometry(f"{w}x{h}+{x}+{y}")
            elif geom:
                win.geometry(geom)
            win._is_max = False
    except tk.TclError:
        pass


def _popup_head_buttons(head, win, tree, col_spec) -> None:
    """Tombol ⛶ Layar Penuh + ↺ Muat Lebar di head popup (pola tombol
    popup v3.9.32).
    v3.9.59 — FIX 2e-07: '⛶ Perbesar' → '⛶ Layar Penuh' (kata
    'Perbesar' dipakai ⤢ in-place '⤢ Perbesar Tabel' — dua aksi beda
    tak boleh sebutan sama; ⛶ selalu = Layar Penuh)."""
    GhostButton(head, text="⛶ Layar Penuh",
                command=lambda: _toggle_popup_max(win, tree, col_spec)
                ).pack(side="right", padx=(6, 0))
    GhostButton(head, text="↺ Muat Lebar",
                command=lambda: _scale_popup_columns(
                    tree, col_spec, win.winfo_width() - 36)
                ).pack(side="right", padx=(6, 0))


class NominalRestoView(tk.Frame):
    """Tab 🧮 Nominal Deviasi — Σ (Harga × Qty Deviasi) per resto."""

    # v3.9.63 — format kolom baru (user: "kolom N Barang dan Tanpa harga
    # hapus aja diganti dengan nominal deviasi per kategori ... Resto ·
    # Com deviasi · Biaya packaging · Nominal deviasi H · Nominal deviasi
    # bulan lalu · Persen kenaikan/penurunan (bisa sort)"):
    #   - 'COM Deviasi'/'Biaya Packaging' = Σ nominal per klas kategori
    #     (agregasi_nominal_per_resto; resto tanpa pasangan klas → 0.0
    #     tampil '-' via fmt_rp_cell);
    #   - 'Persen Kenaikan/Penurunan' = (H − Lalu) ÷ |Lalu| × 100 —
    #     sort numerik (parser '%'-aware) + minus merah per-cell.
    # 'N Barang'/'Tanpa Harga' DIHAPUS (jumlah tanpa harga kini di anak
    # tab 'Tanpa Harga' + footer status).
    COLUMNS = [
        ("Resto", 130, "w"),
        ("COM Deviasi", 120, "e"),
        ("Biaya Packaging", 120, "e"),
        ("Nominal Deviasi", 130, "e"),   # heading dinamis "(H=n)"
        # v3.9.38 — user: "Nominal Deviasi total per resto juga tambahan
        # di tab nominal deviasi ini buat versus bulan lalu"
        ("Nominal Deviasi Bulan Lalu", 130, "e"),
        # v3.9.63 — user: "Persen kenaikan/penurunan (bisa sort)"
        ("Persen Kenaikan/Penurunan", 110, "e"),
    ]

    # v3.9.63 — klas nominal + persen (parser sort _parse_num_id kini
    # '%'-aware: '+12,5%' → 12.5).
    NUMERIC_COLS = ("COM Deviasi", "Biaya Packaging", "Nominal Deviasi",
                    "Nominal Deviasi Bulan Lalu",
                    "Persen Kenaikan/Penurunan")

    # v3.9.45 — id kolom BASIS (statis) — pembanding utk register kolom
    # dinamis 'Lalu <label>' di _ensure_tree_columns.
    COLUMNS_IDS = tuple(c[0] for c in COLUMNS)

    def __init__(self, parent, go_to_proses: Callable | None = None,
                 h_state=None, lalu_provider: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.data: pd.DataFrame | None = None
        self.go_to_proses = go_to_proses
        self._h_state = h_state
        self.tanggal_h = int(h_state.h) if h_state is not None else 25
        self.harga_map: dict = {}
        self.konversi_map: dict | None = None
        # v3.9.36 — provider FILE DEVIASI (tab ⚖ Komparasi): () → df
        # parse_deviasi_file atau None. App memasang lambda pembaca
        # komparasi_view._file_df (referensi diganti — bukan dimutasi —
        # jadi pembacaan provider selalu segar); file berganti → app
        # memanggil on_lalu_file_changed().
        self._lalu_provider = lalu_provider
        self._lalu_df: pd.DataFrame | None = None   # snapshot popup lalu
        self._lalu_loaded = False      # provider pernah mengembalikan df
        self._lalu_week: str | None = None  # v3.9.41 label minggu lalu
        # v3.9.45 — MULTI-BULAN (user: "tab nominal deviasi support buat
        # multiple file deviasi buat compare dengan beberapa bulan
        # lalu"): [(label_bulan, pairs_df)] SEMUA bulan file deviasi
        # urut terbaru-dulu (index 0 = 'bulan lalu' utama = kolom
        # 'Nominal Deviasi Bulan Lalu' yang sudah ada); bulan ≥2 =
        # kolom dinamis 'Lalu <label>' (self._lalu_extra).
        self._lalu_frames: list = []
        self._lalu_extra: list = []   # [(col_id, label, week)] bulan ≥2
        # v3.9.63 — ANAK TAB 'Tanpa Harga' (global): frame pasangan tanpa
        # harga dari data MENTAH (pasangan_tanpa_harga_global — dihitung
        # di _compute_resto bersama tabel utama) + filter kategori & ⧩
        # anak tab SENDIRI (default 'Semua' = global — tidak terikat
        # filter KATEGORI tab Per Resto).
        self._noharga_df: pd.DataFrame | None = None
        self._nh_neg_cells: list = []   # v3.9.64 — N9: minus merah per-cell anak tab
        self._nh_kategori_sel: str | None = None
        self._nh_col_sel: dict = {
            c[0]: None for c in NOHARGA_COLUMNS}
        self._nh_insert_cancel = None
        # v3.9.36 — filter KATEGORI (pola deviasi_view v3.9.19):
        # None = 'Semua' = tanpa filter; default 'Deviasi'.
        self._kategori_sel: str | None = None
        # v3.9.59 — FIX 2e-03: jumlah baris 3.DEVIASI@H TANPA filter
        # kategori (dihitung _compute_resto; dipakai pesan status jujur
        # saat kategori menghabiskan semua baris).
        self._n_dev_h_unfiltered = 0
        self._busy = False
        self._pending = False
        self._dirty = False                # lazy refresh (pola v3.2)
        self._render_gen = 0
        self._insert_cancel = None
        self._pending_sort = None
        self._result_df = None
        self._pairs_df: pd.DataFrame | None = None   # rincian popup
        self._detail_wins: list = []       # popup rincian hidup
        self._col_sel: dict = {c: None for c in
                               [c[0] for c in self.COLUMNS]}
        # v3.9.2 minus merah PER CELL (fallback Tk 8 per baris)
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        self._total_cells: list = []       # sel baris TOTAL (style khusus)

        self._build_ui()
        self._setup_tags()
        self._show_empty()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        self.empty = EmptyState(
            self, icon="🧮",
            title="Belum ada data Nominal Deviasi per resto",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses
            else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        self.content = tk.Frame(self, bg=C_BG)

        # v3.9.63 — ANAK TAB (user: "dan itu buat anak tab baru di nominal
        # deviasi yang menampilkan secara global"): sub-notebook 2 anak
        # tab — 'Per Resto' (tabel utama + filter KATEGORI utama —
        # perilaku lama utuh) + 'Tanpa Harga' (daftar barang tanpa harga
        # GLOBAL semua resto & kategori + filter kategori SENDIRI).
        self._sub_nb = ttk.Notebook(self.content)
        self._sub_nb.pack(fill="both", expand=True)
        self._tab_main = tk.Frame(self._sub_nb, bg=C_BG)
        self._tab_noharga = tk.Frame(self._sub_nb, bg=C_BG)
        self._sub_nb.add(self._tab_main, text="Per Resto")
        self._sub_nb.add(self._tab_noharga, text="Tanpa Harga")

        # --- Filter card: chip H bersama (read-only) + TOTAL chip ---
        fcard = Card(self._tab_main, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        self._fcard = fcard
        fbody = fcard.body()

        r1 = tk.Frame(fbody, bg=C_CARD)
        r1.pack(fill="x")
        # chip H read-only + petunjuk (pola mode Nominal v3.9.33)
        tk.Label(r1, text="TANGGAL H · atur di 📦 Deviasi GR", bg=C_CARD,
                 fg=C_TEXT_MUTED, font=font(8, "bold")).pack(side="left")
        self._h_chip_var = tk.StringVar(value=str(self.tanggal_h))
        chip = tk.Frame(r1, bg="#f1f5f9", highlightbackground="#e2e8f0",
                        highlightthickness=1)
        chip.pack(side="left", padx=(6, 18))
        tk.Label(chip, textvariable=self._h_chip_var, bg="#f1f5f9",
                 fg=C_ACCENT, font=font(11, "bold")).pack(
            padx=10, pady=(2, 3))
        self._total_var = tk.StringVar(value="")
        tk.Label(r1, textvariable=self._total_var, bg=C_CARD,
                 fg=C_HEADER, font=font(9, "bold")).pack(
            side="left", padx=(8, 0))
        GhostButton(r1, text="✕ Reset Filter",
                    command=self._reset_filter).pack(side="left",
                                                     padx=(18, 0))
        tk.Label(r1, text="double-click resto → rincian per barang · "
                            "barang tanpa harga → anak tab 'Tanpa Harga'",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=font(8)).pack(
            side="right")

        # v3.9.36 — filter KATEGORI (user: "tambah filter Kategori dengan
        # default pilihan Kategori = Deviasi"; pola r0b deviasi_view):
        # 'Semua' = tanpa filter; DEFAULT 'Deviasi' (case-insensitive).
        # v3.9.49 — DEFAULT BARU: entry gabungan kategori Rekap Mentah
        # (user: "secara default di semua tab kategori sudah pilih: COM
        # DEVIASI - RESTO dan Biaya Packaging - RESTO") bila ada di data;
        # combo dilebarkan utk label gabungan panjang.
        # v3.9.55 — label gabungan kini RINGKA 'Deviasi (COM + Packaging)'
        # → lebar 34 (parity deviasi/pivot).
        r1b = tk.Frame(fbody, bg=C_CARD)
        r1b.pack(fill="x", pady=(6, 0))
        tk.Label(r1b, text="KATEGORI", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self._kategori_var = tk.StringVar(value="Semua")
        self._kategori_combo = ttk.Combobox(
            r1b, textvariable=self._kategori_var, state="readonly",
            width=34, font=font(9))
        self._kategori_combo.pack(side="left", padx=(6, 0))
        self._kategori_combo.bind(
            "<<ComboboxSelected>>", lambda e: self._on_kategori_changed())
        tk.Label(r1b, text="default: kategori Rekap Mentah (pola tab 📦 "
                            "Deviasi GR) · kolom Bulan Lalu = file "
                            "deviasi (⚖ Komparasi)",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=font(8)).pack(
            side="left", padx=(12, 0))

        # --- Tabel card ---
        tcard = Card(self._tab_main)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self._title_label = tk.Label(
            head, text="Nominal Deviasi per Resto — Σ (Harga 41.09 × "
                       "Qty Deviasi) — H shared",
            bg=C_CARD, fg=C_HEADER, font=font(10, "bold"))
        self._title_label.pack(side="left")
        btn_max = GhostButton(head, text="⛶ Layar Penuh",
                              command=self._maximize)
        btn_max.pack(side="right")
        btn_expand = GhostButton(head, text="⤢ Perbesar Tabel",
                                 command=lambda: None)
        btn_expand.pack(side="right", padx=(0, 6))
        btn_cols = GhostButton(head, text="◱ Kolom",
                               command=lambda: self._colmgr.open_panel())
        btn_cols.pack(side="right", padx=(0, 6))
        btn_fit = GhostButton(head, text="↔ Auto-Fit",
                              command=self._auto_fit)
        btn_fit.pack(side="right", padx=(0, 6))

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(tbody, columns=col_ids, show="headings",
                                 selectmode="extended")

        for col_name, width, anchor in self.COLUMNS:
            self.tree.column(col_name, width=width, minwidth=34,
                             anchor=anchor)
            self.tree.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(tbody, orient="vertical",
                            command=self.tree.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(0, weight=1)

        enable_col_resize(self.tree)
        enable_multi_select(self.tree)
        self.tree.bind("<Double-1>", self._on_double_click)

        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew",
                  pady=(6, 0))
        self.status_var_label = tk.StringVar(value="Belum ada data.")
        tk.Label(foot, textvariable=self.status_var_label, bg=C_CARD,
                 fg=C_HEADER, font=font(8, "bold")).pack(side="right")

        self.overlay = LoadingOverlay(tbody, "Menghitung nominal per "
                                              "resto…")

        self.header_filters = HeaderFilterGroup(
            self.tree, col_ids,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filters.open_popup(c))

        self._expander = TableExpander(btn_expand, [fcard,
                                                    self._title_label])

        # chip H bersama + auto-refresh saat H diubah di tab Deviasi GR
        if self._h_state is not None:
            self._h_state.subscribe(self._on_shared_h_changed)
            self.bind("<Destroy>", self._on_view_destroy, add="+")

        # v3.9.63 — anak tab 'Tanpa Harga' (global) — dibangun SETELAH
        # tree utama (header_filters/_colmgr utama tak terganggu).
        self._build_noharga_tab()

    # =========================================================================
    # v3.9.63 — ANAK TAB 'TANPA HARGA' (GLOBAL)
    # =========================================================================
    def _build_noharga_tab(self):
        """v3.9.63 — ANAK TAB 'Tanpa Harga' (user: "barang yang tidak ada
        harga nya sesuai kategori yang difilter misal deviasi COM +
        packaging berarti hanya menampilkan sesuai kategori aja. dan itu
        buat anak tab baru di nominal deviasi yang menampilkan secara
        global"): daftar pasangan tanpa harga GLOBAL (semua resto &
        kategori — pasangan_tanpa_harga_global, TANPA filter kategori
        tab Per Resto) + kolom Kategori + combobox KATEGORI sendiri
        (default 'Semua' = global; memilih kategori/gabungan → hanya
        menampilkan sesuai kategori itu). Menggantikan popup double-click
        kolom 'Tanpa Harga' (kolomnya dihapus v3.9.63)."""
        fcard = Card(self._tab_noharga, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        fbody = fcard.body()

        r = tk.Frame(fbody, bg=C_CARD)
        r.pack(fill="x")
        self._nh_h_var = tk.StringVar(value=str(self.tanggal_h))
        tk.Label(r, text="TANGGAL H", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        _nh_chip = tk.Frame(r, bg="#f1f5f9",
                            highlightbackground="#e2e8f0",
                            highlightthickness=1)
        _nh_chip.pack(side="left", padx=(6, 14))
        tk.Label(_nh_chip, textvariable=self._nh_h_var, bg="#f1f5f9",
                 fg=C_ACCENT, font=font(11, "bold")).pack(
            padx=10, pady=(2, 3))
        tk.Label(r, text="KATEGORI", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self._nh_kategori_var = tk.StringVar(value="Semua")
        self._nh_kategori_combo = ttk.Combobox(
            r, textvariable=self._nh_kategori_var, state="readonly",
            width=34, font=font(9))
        self._nh_kategori_combo.pack(side="left", padx=(6, 0))
        self._nh_kategori_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_nh_kategori_changed())
        GhostButton(r, text="✕ Reset Filter",
                    command=self._nh_reset_filter).pack(
            side="left", padx=(12, 0))
        tk.Label(r, text="GLOBAL — semua resto & kategori (tidak terikat "
                         "filter tab Per Resto) · barang tanpa harga tidak "
                         "ikut Σ Nominal Deviasi",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=font(8)).pack(
            side="right")

        # --- Tabel card ---
        tcard = Card(self._tab_noharga)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Label(head, text="Barang Tanpa Harga — global (semua resto & "
                            "kategori) — tidak ikut Σ Nominal Deviasi",
                 bg=C_CARD, fg=C_HEADER, font=font(10, "bold")).pack(
            side="left")
        GhostButton(head, text="↔ Auto-Fit",
                    command=lambda: auto_fit_columns(
                        self.tree_noharga)).pack(side="right")

        _nh_ids = [c[0] for c in NOHARGA_COLUMNS]
        self.tree_noharga = ttk.Treeview(
            tbody, columns=_nh_ids, show="headings",
            selectmode="extended")
        for col_name, width, anchor in NOHARGA_COLUMNS:
            self.tree_noharga.column(col_name, width=width, minwidth=34,
                                     anchor=anchor)
            self.tree_noharga.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(tbody, orient="vertical",
                            command=self.tree_noharga.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal",
                            command=self.tree_noharga.xview)
        self.tree_noharga.configure(yscrollcommand=vsb.set,
                                    xscrollcommand=hsb.set)
        self.tree_noharga.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(0, weight=1)

        enable_col_resize(self.tree_noharga)
        enable_multi_select(self.tree_noharga)
        self._setup_tags(self.tree_noharga)

        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self._nh_status_var = tk.StringVar(value="Belum ada data.")
        tk.Label(foot, textvariable=self._nh_status_var, bg=C_CARD,
                 fg=C_HEADER, font=font(8, "bold")).pack(side="right")

        # filter header ⧩ + sort (pola tabel utama; nilai = DISPLAY)
        self._nh_filters = HeaderFilterGroup(
            self.tree_noharga, _nh_ids,
            get_values=self._nh_col_values,
            on_apply=self._on_nh_col_filter,
            on_sort=lambda c, d: self._sort_noharga_by(c, reverse=d))

    def primary_tree(self):
        """v3.9.63 — tree utama utk FALLBACK router roda app (pola
        app._primary_scrollable): anak tab 'Tanpa Harga' aktif → tree
        anak tab (roda di krom kartu Filter anak tab bergulir tabelnya);
        selain itu tree utama 'Per Resto'."""
        try:
            if str(self._sub_nb.select()) == str(self._tab_noharga):
                return self.tree_noharga
        except tk.TclError:
            pass
        return self.tree

    def _on_nh_kategori_changed(self):
        """Combobox KATEGORI anak tab berubah → re-render TABEL anak tab
        saja (frame global SUDAH dihitung — tanpa recompute pipeline)."""
        val = self._nh_kategori_var.get()
        self._nh_kategori_sel = None if (not val or val == "Semua") else val
        self._render_noharga()

    def _nh_reset_filter(self):
        """Reset filter anak tab: kategori kembali 'Semua' (GLOBAL) + ⧩
        bersih → re-render."""
        for c in self._nh_col_sel:
            self._nh_col_sel[c] = None
        self._nh_filters.clear_all()
        self._nh_kategori_var.set("Semua")
        self._nh_kategori_sel = None
        self._render_noharga()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    # Snapshot / pulihkan kedua tabel tab 🧮: Per Resto (⧩ + KATEGORI) +
    # anak tab Tanpa Harga (⧩ + KATEGORI global). v3.9.68 — anak tab
    # AKTIF kini IKUT disimpan & dipulihkan (audit eksternal T6: user
    # yang terakhir menyelidiki 'Tanpa Harga' tidak perlu berpindah
    # subtab ulang tiap buka app; pemilih tampilan — dipulihkan TANPA
    # memicu refresh, terpisah dari logika filter data).
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.nominal_resto')."""
        st = col_sel_to_json(self._col_sel)
        st["kategori"] = self._kategori_var.get()
        _nh = col_sel_to_json(self._nh_col_sel)
        if _nh:
            st["nh_col_sel"] = _nh
        st["nh_kategori"] = self._nh_kategori_var.get()
        # v3.9.68 — T6 (audit eksternal): anak tab aktif ikut diingat.
        st["subtab"] = ("noharga"
                       if str(self._sub_nb.select())
                       == str(self._tab_noharga) else "perresto")
        return st

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.

        Combobox KATEGORI (keduanya) divalidasi terhadap values data
        BARU (pola preserve v3.9.42). Refresh SEKALI di akhir bila ada
        perubahan: _refresh men-render kedua tabel (utama + anak tab,
        v3.9.64 FIX 6) memakai state yang sudah dipulihkan; bila
        `_noharga_df` belum siap, render anak tab menyusul dari hasil
        compute worker (jalur normal)."""
        if not isinstance(state, dict):
            return
        if self.data is None or bool(getattr(self.data, "empty", True)):
            return
        # v3.9.68 — T6 (audit eksternal): pulihkan anak tab AKTIF dulu
        # (pemilih tampilan — TANPA memicu refresh; nilai asing/absen →
        # tetap default 'Per Resto').
        _sub = state.get("subtab")
        with contextlib.suppress(tk.TclError):
            if _sub == "noharga":
                self._sub_nb.select(self._tab_noharga)
            elif _sub == "perresto":
                self._sub_nb.select(self._tab_main)
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        _kv = state.get("kategori")
        if isinstance(_kv, str):
            try:
                _kvals = list(self._kategori_combo["values"])
            except tk.TclError:
                _kvals = []
            if (_kv in _kvals
                    and self._kategori_var.get() != _kv):
                self._kategori_var.set(_kv)
                self._kategori_sel = (None if _kv == "Semua" else _kv)
                changed = True
        _nh_state = state.get("nh_col_sel")
        if (isinstance(_nh_state, dict)
                and apply_col_sel_restore(
                    self, _nh_state, self._nh_col_sel,
                    self._nh_filters)):
            changed = True
        _nk = state.get("nh_kategori")
        if isinstance(_nk, str):
            try:
                _nvals = list(self._nh_kategori_combo["values"])
            except tk.TclError:
                _nvals = []
            if (_nk in _nvals
                    and self._nh_kategori_var.get() != _nk):
                self._nh_kategori_var.set(_nk)
                self._nh_kategori_sel = (
                    None if _nk == "Semua" else _nk)
                changed = True
        if not changed:
            return
        if self.winfo_ismapped():
            self._refresh()
        # tab tersembunyi → dirty flag load_data terpasang; anak tab
        # ikut di-render oleh _refresh saat tab dibuka.

    def _nh_format_col_series(self, col: str, series):
        """Format nilai kolom anak tab utk ⧩ (identik dgn sel tampil)."""
        if col == "Kuantiti Deviasi":
            return series.map(fmt_nominal_cell)
        if col == "Kategori":
            return series.map(self._nh_kategori_disp)
        return series.astype(str)

    @staticmethod
    def _nh_kategori_disp(kat) -> str:
        """Kategori pasangan utk tampilan anak tab (blank → '(Tanpa
        Kategori)' — konvensi label combobox)."""
        s = str(kat).strip() if kat is not None else ""
        if s.lower() in ("", "nan", "none", "-"):
            return KATEGORI_BLANK_LABEL
        return s

    def _nh_col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup ⧩ anak tab (pola _col_values:
        seleksi kolom LAIN diterapkan dulu supaya daftar selaras)."""
        df = self._noharga_df
        if df is None or df.empty or col not in df.columns:
            return []
        f = df
        m = self._kategori_mask_series(f["KATEGORI"],
                                       self._nh_kategori_sel)
        if m is not None:
            f = f[m]
        for c, sel in self._nh_col_sel.items():
            if sel is None or c == col or c not in f.columns:
                continue
            fmt = self._nh_format_col_series(c, f[c])
            f = f[fmt.isin(sel)]
        if f.empty:
            return []
        return self._nh_format_col_series(col, f[col]).unique().tolist()

    def _on_nh_col_filter(self, col: str, selected):
        self._nh_col_sel[col] = selected
        self._render_noharga()

    def _sort_noharga_by(self, col: str, reverse: bool = False):
        """Sort kolom anak tab (pola _sort_by; 'Kuantiti Deviasi'
        numerik — parser persen/Indonesia sama)."""
        parse = (self._parse_num_id if col == "Kuantiti Deviasi"
                 else None)
        sort_tree_by_column(self.tree_noharga, col, reverse=reverse,
                            parse=parse)
        # v3.9.64 — N9: pasang ulang minus merah per-cell pasca-sort
        # (sort = move — iid tetap; reapply defensif pola tabel utama)
        self._reapply_nh_cell_tags()

    @staticmethod
    def _kategori_mask_series(kat, sel):
        """v3.9.63 — mask kategori KANONIK utk render anak tab (semantik
        PERSIS blok filter _compute_resto: blank-label → blank mask;
        entri gabungan → kategori_filter_mask; legacy 'Deviasi' →
        passthrough blank; lainnya strict exact). sel kosong → None
        (tanpa filter)."""
        if not sel:
            return None
        if sel == KATEGORI_BLANK_LABEL:
            return kategori_blank_mask(kat)
        m = kategori_filter_mask(kat, sel)
        if m is not None:
            return m
        if kategori_passthrough(sel):
            return (kat.astype(str) == str(sel)) | kategori_blank_mask(
                kat).fillna(False)
        return kat.astype(str) == str(sel)

    def _reapply_nh_cell_tags(self, _tree=None):
        """v3.9.64 — FIX (audit 15-a N9): minus merah PER-CELL kolom
        'Kuantiti Deviasi' anak tab 'Tanpa Harga' (parity tabel utama +
        popup lama — dulu '(8)' tampil hitam). Dipanggil on_done
        insert_tree_items (tag cell terpasang SETELAH semua baris hidup)
        + pasca-sort; apply_cell_tag best-effort (Tk 8 no-op senyap)."""
        apply_cell_tag(self.tree_noharga, "neg_cell", self._nh_neg_cells)

    def _render_noharga(self):
        """Render tabel anak tab 'Tanpa Harga' dari frame GLOBAL
        self._noharga_df + filter kategori/⧩ anak tab (tanpa recompute —
        frame dihitung _compute_resto bersama tabel utama)."""
        if getattr(self, "_nh_insert_cancel", None) is not None:
            self._nh_insert_cancel()
            self._nh_insert_cancel = None
        self.tree_noharga.delete(
            *self.tree_noharga.get_children(""))
        # v3.9.64 — N8: segarkan ikon ⧩ (pola _render_rows — dulu hanya
        # di-clear saat load_data, ikon filter aktif bisa tersisa basi)
        # + N9: reset daftar sel minus + lepas tag cell lama.
        self._nh_neg_cells = []
        apply_cell_tag(self.tree_noharga, "neg_cell", [])
        if getattr(self, "_nh_filters", None) is not None:
            with contextlib.suppress(Exception):
                self._nh_filters.refresh_icons()
        self._nh_h_var.set(str(self.tanggal_h))
        df = self._noharga_df
        if df is None:
            self._nh_status_var.set(
                "Belum ada data — 0 baris terbaca dari pipeline (cek "
                "folder data / RootPath di tab ⚙️ Config).")
            return
        if df.empty:
            self._nh_status_var.set(
                "Tidak ada pasangan tanpa harga " + (
                    f"(KATEGORI {self._nh_kategori_sel})."
                    if self._nh_kategori_sel
                    else f"tanggal H={self.tanggal_h} — semua pasangan "
                         "ber-harga 41.09."))
            return
        f = df
        m = self._kategori_mask_series(f["KATEGORI"],
                                       self._nh_kategori_sel)
        if m is not None:
            f = f[m]
        # filter header ⧩ (nilai TERFORMAT — identik yang tampil)
        for col, sel in self._nh_col_sel.items():
            if sel is not None and col in f.columns:
                fmt = self._nh_format_col_series(col, f[col])
                f = f[fmt.isin(sel)]
        if f.empty:
            # v3.9.68 — TRI-STATE (audit eksternal T1): bila penyebabnya
            # seleksi ⧩ KOSONG → pesan jujur eksplisit + cara keluar.
            _hint = zero_row_filter_message(self._nh_col_sel)
            if _hint:
                self._nh_status_var.set(_hint)
                return
            _act = ", ".join(c for c, s in self._nh_col_sel.items()
                             if s is not None)
            self._nh_status_var.set(
                f"0 dari {fmt_int_id(len(df))} pasangan tanpa harga "
                f"lolos filter aktif"
                + (f" (KATEGORI: {self._nh_kategori_sel})"
                   if self._nh_kategori_sel else "")
                + (f" ({_act})" if _act else "") + ".")
            return
        items = []
        f = f.reset_index(drop=True)
        for i in range(len(f)):
            row = f.iloc[i]
            _qty76 = row.get("Qty Deviasi", 0)
            values = (
                str(row["Resto"]),
                self._nh_kategori_disp(row.get("KATEGORI")),
                str(row["Nama Barang"]),
                str(row.get("Satuan", "-")),
                fmt_nominal_cell(_qty76),
                self._noharga_ket(row.get("Harga Tampil")),
            )
            tags = ["evenrow" if i % 2 == 0 else "oddrow"]
            items.append(("", f"row_{i}",
                          {"values": values, "tags": tuple(tags)}))
            # v3.9.64 — N9: nilai Kuantiti Deviasi minus → tag per-cell
            try:
                if float(_qty76) < 0:
                    self._nh_neg_cells.append(
                        (f"row_{i}", "Kuantiti Deviasi"))
            except (TypeError, ValueError):
                pass
        self._nh_insert_cancel = insert_tree_items(
            self.tree_noharga, items, batch=500,
            on_done=self._reapply_nh_cell_tags)
        _n_all = len(df)
        status = (f"{fmt_int_id(len(f))} dari {fmt_int_id(_n_all)} "
                  f"pasangan tanpa harga · GLOBAL semua kategori & resto "
                  f"· TANGGAL H = {self.tanggal_h}")
        if self._nh_kategori_sel:
            status += f" · KATEGORI {self._nh_kategori_sel}"
        status += " · nominal '-' (transparan — tidak dihitung Σ)"
        self._nh_status_var.set(status)

    def _on_view_destroy(self, event):
        if event.widget is self and self._h_state is not None:
            with contextlib.suppress(Exception):
                self._h_state.unsubscribe(self._on_shared_h_changed)

    def _on_shared_h_changed(self, h):
        """Listener H bersama (pola mode Nominal v3.9.33): pane
        tersembunyi cukup ditandai dirty + chip diperbarui; refresh
        penuh saat tab terlihat (ensure_refreshed)."""
        self.tanggal_h = int(h)
        if hasattr(self, "_h_chip_var"):
            self._h_chip_var.set(str(self.tanggal_h))
        if self._dirty:
            return
        if not self.winfo_ismapped():
            self._dirty = True
            return
        if self.data is not None and not self.data.empty:
            self._refresh()

    # =========================================================================
    # FILTER / SORT
    # =========================================================================
    def _reset_filter(self):
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        self._reset_kategori()    # v3.9.36 — reset = default 'Deviasi'
        self._refresh()

    # v3.9.36 — combobox KATEGORI ("Semua" = tanpa filter; pola
    # deviasi_view v3.9.19; default 'Deviasi' — case-insensitive).
    # v3.9.49 — default BARU: entry gabungan kategori Rekap Mentah bila
    # ada di data; fallback legacy 'Deviasi' → 'Semua'.
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

    def _col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup filter header (pola mode
        Nominal v3.9.33 — nilai identik dgn sel yang tampil)."""
        result = self._result_df
        if result is None or result.empty:
            return []
        f = result
        for c, sel in self._col_sel.items():
            if sel is None or c == col:
                continue
            if c in f.columns:
                fmt = self._format_col_series(c, f[c])
                f = f[fmt.isin(sel)]
        if f.empty or col not in f.columns:
            return []
        return self._format_col_series(col, f[col]).unique().tolist()

    def _format_col_series(self, col: str, series):
        # v3.9.63 — klas nominal per kategori (COM Deviasi/Biaya
        # Packaging) ikut format Rp; kolom Persen → fmt_pct_cell.
        if col in ("COM Deviasi", "Biaya Packaging",
                   "Nominal Deviasi", "Nominal Deviasi Bulan Lalu") \
                or self._is_lalu_extra(col):
            # v3.9.59 — FIX 2f-01 (HIGH, pola deviasi_view v3.9.51 §61f):
            # daftar nilai popup ⧩ kolom nominal HARUS identik dgn SEL
            # TABEL (fmt_rp_cell sejak v3.9.51 — 'Rp 1.825'). Dulu
            # fmt_nominal_cell ('1.825' tanpa Rp) → dropdown ≠ tampilan +
            # filter clone ⛶ (apply_tree_row_filters mencocokkan nilai
            # DISPLAY tree vs seleksi) tak pernah cocok → 0 baris.
            return series.map(fmt_rp_cell)
        if col == "Persen Kenaikan/Penurunan":
            # v3.9.63 — nilai ⧩ identik dgn sel tabel ('+12,5%').
            return series.map(fmt_pct_cell)
        return series.astype(str)

    def _on_col_filter(self, col: str, selected):
        self._col_sel[col] = selected
        self._refresh()

    def _is_lalu_extra(self, col: str) -> bool:
        """v3.9.45 — kolom dinamis bulan-lalu ≥2 ('Lalu <label>')?"""
        return any(_cid == col for _cid, _l, _w in self._lalu_extra)

    def _result_cols(self) -> list:
        # v3.9.45 — + kolom dinamis 'Lalu <label>' per bulan file
        # deviasi (multi-file ⚖ Komparasi — lihat _lalu_extra).
        return ([c[0] for c in self.COLUMNS]
                + [c[0] for c in self._lalu_extra])

    def _ensure_tree_columns(self):
        """v3.9.45 — sinkronkan kolom tree dgn _result_cols() saat
        himpunan bulan-lalu berubah (pola _render_payload pivot_view:
        reset displaycolumns dulu — Tk memvalidasi displaycolumns lama
        terhadap daftar kolom baru 'Invalid column index'). Filter ⧩
        kolom yang hilang dibuang (bulan tak lagi dimuat)."""
        col_ids = self._result_cols()
        if list(self.tree["columns"]) == col_ids:
            return
        try:
            self.tree.configure(displaycolumns="#all")
        except tk.TclError:
            pass
        self.tree["columns"] = col_ids
        for col_name, width, anchor in self.COLUMNS:
            self.tree.column(col_name, width=width, minwidth=34,
                             anchor=anchor)
            self.tree.heading(col_name, text=col_name)
        for _cid, _lab, _wk in self._lalu_extra:
            self.tree.column(_cid, width=130, minwidth=34, anchor="e")
            self.tree.heading(_cid, text=_cid)
        # header filter/sort aktif juga di kolom baru (idempoten)
        self.header_filters.add_columns(
            [c for c in col_ids if c not in self.COLUMNS_IDS])
        # filter kolom bulan lama yang tak ada lagi → buang
        for c in list(self._col_sel):
            if c not in col_ids:
                del self._col_sel[c]
        # FIX 6d2-03 — mirror in_selisih _apply_columns v3.7 (defensive):
        # reconfigure columns di atas me-reset displaycolumns ke '#all' →
        # state kolom TERSEMBUNYI user (ColumnManager) WAJIB di-re-apply
        # setelah rebuild — tanpa ini kolom yang di-hide muncul lagi +
        # panel ◱ Kolom desync (checkbox basi) saat bulan file deviasi
        # berubah (multi-bulan ⚖ Komparasi). Prune dulu kolom hidden yang
        # tak ada lagi (bulan lalu tak lagi dimuat).
        self._colmgr.hidden = [c for c in self._colmgr.hidden
                               if c in col_ids]
        self._colmgr.apply()

    def _sort_by(self, col: str, reverse: bool = False):
        if col not in self._result_cols():
            return
        if self._busy:
            self._pending_sort = (col, reverse)
            return
        parse = (self._parse_num_id
                 if (col in self.NUMERIC_COLS
                     or self._is_lalu_extra(col)) else None)
        sort_tree_by_column(self.tree, col, reverse=reverse, parse=parse)
        self._pin_total_row(self.tree)
        self._reapply_cell_tags(self.tree)
        self._pending_sort = None

    def _pin_total_row(self, tree):
        """Baris TOTAL dipin di UJUNG setelah sort (pola mode Nominal
        v3.9.33 — sort menurun jangan melompatkan TOTAL ke atas)."""
        try:
            if "row_total" in tree.get_children(""):
                tree.move("row_total", "", "end")
        except tk.TclError:
            pass

    @staticmethod
    def _safe_float(v):
        """v3.9.63 — float aman utk minus-merah per-cell (None/NaN/'-'/
        string non-angka → None; pola try/float lama diringkas)."""
        try:
            if v is None or pd.isna(v):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_num_id(s):
        """Parser sort format Indonesia (pola mode Nominal): '1.234' =
        1234, '(1.234)' = -1234, '-' = 0, '12,5' = 12.5.
        v3.9.51: prefiks 'Rp ' dibuang DULU (fmt_rp_cell — kolom nominal:
        'Rp 1.825' → 1825, '(Rp 1.825)' → -1825) SEBELUM split parts[0].
        v3.9.63: sufiks '%' juga dibuang (fmt_pct_cell — kolom Persen
        Kenaikan/Penurunan: '+12,5%' → 12.5, '-8,3%' → -8.3; '-' → 0)."""
        s = str(s).replace("—", "").replace("Rp ", "") \
            .replace("Rp", "").replace("%", "").strip()
        parts = s.split()
        if parts:
            s = parts[0]
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
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("neg_cell", foreground="#dc2626")
        tree.tag_configure("total", background="#e2e8f0",
                           foreground="#0f172a")
        tree.tag_configure("total_cell", background="#e2e8f0",
                           foreground="#0f172a")

    # =========================================================================
    # DATA LOADING
    # =========================================================================
    def load_data(self, data: pd.DataFrame, harga_map: dict | None = None,
                  konversi_map: dict | None = None):
        self.data = data
        self.harga_map = harga_map or {}
        self.konversi_map = konversi_map
        self._render_gen += 1
        # v3.9.55 — F8: data baru → auto-fit SEKALI lagi saat render pertama
        reset_autofit_once(self)
        if self._insert_cancel is not None:
            self._insert_cancel()
            self._insert_cancel = None
        self._result_df = None
        self._pairs_df = None
        self._lalu_df = None          # v3.9.36 — snapshot basi dihapus
        self._lalu_loaded = False
        # v3.9.45 — snapshot multi-bulan ikut direset
        self._lalu_frames = []
        self._lalu_extra = []
        self._close_detail_wins()
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        self._show_content()
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        # v3.9.36 — isi combobox KATEGORI dari kolom data (merge '21.
        # DBS Kategori' di append1 — pola deviasi_view) + reset seleksi
        # ke DEFAULT 'Deviasi' (case-insensitive, fallback 'Semua').
        # v3.9.45 — entry '(Tanpa Kategori)' saat ADA baris tanpa
        # master (akses eksplisit kelas 100383).
        # v3.9.46 — entry SELALU ADA (mirror deviasi_view: master yang
        # makin lengkap membuat entry kondisional hilang senyap — user
        # mencari opsi itu & tak menemukannya).
        if data is not None and "KATEGORI" in getattr(data, "columns", []):
            _kv = data["KATEGORI"].dropna().astype(str).str.strip()
            kategori_vals = sorted(v for v in _kv.unique() if v)
        else:
            kategori_vals = []
        # v3.9.49 — entry GABUNGAN default (kategori Rekap Mentah) hanya
        # saat data memuat salah satu nilai rekap (pola deviasi_view).
        _kv45 = ["Semua"]
        if kategori_has_default_values(
                data.get("KATEGORI") if data is not None else None):
            _kv45.append(KATEGORI_DEFAULT_LABEL)
        _kv45.append(KATEGORI_BLANK_LABEL)
        _kv45 += kategori_vals
        self._kategori_combo["values"] = _kv45
        self._reset_kategori()
        # v3.9.63 — combobox KATEGORI ANAK TAB 'Tanpa Harga': daftar
        # nilai sama dgn tab utama; DEFAULT 'Semua' = GLOBAL (user:
        # "menampilkan secara global") — memilih kategori/gabungan →
        # hanya menampilkan sesuai kategori itu (user: "misal deviasi
        # COM +packaging berarti hanya menampilkan sesuai kategori aja").
        # Filter ⧩ anak tab + frame global ikut di-reset.
        self._nh_kategori_combo["values"] = _kv45
        self._nh_kategori_var.set("Semua")
        self._nh_kategori_sel = None
        for c in self._nh_col_sel:
            self._nh_col_sel[c] = None
        self._nh_filters.clear_all()
        self._noharga_df = None
        if self._nh_insert_cancel is not None:
            self._nh_insert_cancel()
            self._nh_insert_cancel = None
        # lazy refresh — compute hanya bila tab terlihat
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True
        # footer informatif jalur 0-baris (pola v3.9.33)
        if data is None or len(data) == 0:
            self.status_var_label.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")

    def ensure_refreshed(self):
        """Lazy refresh (v3.2): compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None \
                and not self.data.empty:
            self._dirty = False
            self._refresh()

    def on_lalu_file_changed(self):
        """v3.9.36 — file deviasi (tab ⚖ Komparasi) berubah (load baru /
        ditutup) → snapshot Bulan Lalu basi: refresh bila tab terlihat,
        tandai dirty bila tersembunyi (pola listener SharedTanggalH)."""
        if self.data is None or self.data.empty:
            return
        if self._busy:
            self._pending = True
            return
        if not self.winfo_ismapped():
            self._dirty = True
            return
        self._refresh()

    # =========================================================================
    # COMPUTE
    # =========================================================================
    def _compute_resto(self, data: pd.DataFrame | None = None,
                       h: int | None = None) -> pd.DataFrame:
        """Frame per resto: [Resto, COM Deviasi, Biaya Packaging, Nominal
        Deviasi, Nominal Deviasi Bulan Lalu, Persen Kenaikan/Penurunan]
        urut |Σ| menurun (v3.9.63 — 'N Barang'/'Tanpa Harga' tetap
        dihitung di agregasi tapi TIDAK ditampilkan). self._pairs_df
        (rincian popup), self._lalu_df (pasangan file deviasi — v3.9.36),
        self._noharga_df (anak tab Tanpa Harga global — v3.9.63) dan
        self._result_df (snapshot filter) ikut diisi."""
        df = self.data if data is None else data
        if df is None or df.empty:
            self._result_df = None
            self._pairs_df = None
            self._lalu_df = None
            self._lalu_loaded = False
            self._lalu_frames = []      # v3.9.45
            self._lalu_extra = []
            self._noharga_df = None     # v3.9.63
            return pd.DataFrame()
        if h is None:
            h = self.tanggal_h
        # v3.9.63 — ANAK TAB 'Tanpa Harga' GLOBAL: pasangan tanpa harga
        # dihitung dari data MENTAH PRA-FILTER (df — SEBELUM filter kategori
        # meng-rebind df di bawah) supaya TIDAK terikat filter KATEGORI
        # tab Per Resto (user: "menampilkan secara global").
        # v3.9.64 — FIX (audit 15-a R3): pakai `df`, BUKAN param `data` —
        # panggilan programatik _compute_resto() TANPA argumen (data=None)
        # dulu menghasilkan anak tab KOSONG senyap (df = self.data utk
        # jalur default; tabel utama tetap benar).
        # Dihitung di worker yang sama (sekali jalan, tak ada recompute
        # saat ganti anak tab / filter kategori anak tab).
        self._noharga_df = pasangan_tanpa_harga_global(
            df, h, self.harga_map, self.konversi_map)
        # v3.9.59 — FIX 2e-03: hitung PRA-kategori (baris 3.DEVIASI@H
        # di data mentah) — utk pesan status jujur di jalur render kosong.
        try:
            _tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
            self._n_dev_h_unfiltered = int(
                ((df["JENIS"].astype(str) == "3.DEVIASI")
                 & (_tnum == h)).sum())
        except (KeyError, TypeError, ValueError):
            self._n_dev_h_unfiltered = 0
        # v3.9.36 — filter KATEGORI combobox PRA-COMPUTE (kategori
        # melekat per-baris hasil merge '21. DBS Kategori').
        # v3.9.45 — passthrough HANYA seleksi default 'Deviasi' (kelas
        # 100383 tetap tampil by default — v3.9.44); seleksi eksplisit
        # lain STRICT (fix "ganti kategori tidak terjadi apa apa" —
        # passthrough universal + mayoritas baris tanpa master bikin
        # filter no-op); KATEGORI_BLANK_LABEL = khusus baris blank.
        if self._kategori_sel and "KATEGORI" in df.columns:
            if self._kategori_sel == KATEGORI_BLANK_LABEL:
                df = df[kategori_blank_mask(df["KATEGORI"])]
            elif kategori_filter_mask(df["KATEGORI"],
                                      self._kategori_sel) is not None:
                # v3.9.49 — entri GABUNGAN default (kategori Rekap
                # Mentah). v3.9.53 — kini STRICT (hanya nilai gabungan;
                # passthrough blank DIHAPUS — mirror deviasi_view; kelas
                # tanpa kategori = entry '(Tanpa Kategori)').
                df = df[kategori_filter_mask(
                    df["KATEGORI"], self._kategori_sel)]
            elif kategori_passthrough(self._kategori_sel):
                _blank = kategori_blank_mask(df["KATEGORI"])
                df = df[(df["KATEGORI"].astype(str)
                         == str(self._kategori_sel)) | _blank]
            else:
                df = df[df["KATEGORI"].astype(str)
                        == str(self._kategori_sel)]
            if df.empty:
                self._result_df = None
                self._pairs_df = None
                self._lalu_df = None
                self._lalu_loaded = False
                self._lalu_frames = []  # v3.9.45
                self._lalu_extra = []
                return pd.DataFrame()
        # v3.9.36 — snapshot pasangan Bulan Lalu dari FILE DEVIASI
        # (provider = pembaca komparasi_view._file_df; harga_map fresh
        # → dihitung ulang tiap compute).
        # v3.9.41 — h diteruskan: minggu pembanding TER-COCOK dgn H
        # analisa (user: "jika week 1 maka ambil data week 1 juga").
        # v3.9.45 — MULTI-BULAN: SEMUA bulan file deviasi jadi frame
        # terpisah (user: "support buat multiple file deviasi buat
        # compare dengan beberapa bulan lalu"); index 0 (terbaru) =
        # kolom 'Nominal Deviasi Bulan Lalu' yang sudah ada (perilaku
        # lama utuh), bulan ≥2 = kolom dinamis 'Lalu <label>'.
        fdf = None
        if self._lalu_provider is not None:
            with contextlib.suppress(Exception):
                fdf = self._lalu_provider()
        self._lalu_loaded = fdf is not None
        self._lalu_frames = hitung_nominal_lalu_multi(
            fdf, self.harga_map, self.konversi_map, h=h)
        # back-compat: frame kosong = DataFrame KOSONG (bukan None —
        # pola hitung_nominal_lalu_pairs; konsumen memeriksa .empty)
        self._lalu_df = (self._lalu_frames[0][1]
                         if self._lalu_frames else pd.DataFrame())
        self._lalu_week = (
            str(self._lalu_df["_minggu"].iloc[0])
            if self._lalu_df is not None and not self._lalu_df.empty
            and "_minggu" in self._lalu_df.columns else None)
        # metadata kolom dinamis bulan ≥2: (col_id, label, week)
        self._lalu_extra = []
        for _lab, _fr in self._lalu_frames[1:]:
            _wk = (str(_fr["_minggu"].iloc[0])
                   if _fr is not None and not _fr.empty
                   and "_minggu" in _fr.columns else None)
            self._lalu_extra.append((f"Lalu {_lab}", _lab, _wk))
        g, pairs = agregasi_nominal_per_resto(
            df, h, self.harga_map, self.konversi_map)
        if g.empty:
            self._result_df = None
            self._pairs_df = None
            return pd.DataFrame()
        self._pairs_df = pairs
        # v3.9.38 — KOLOM BARU 'Nominal Deviasi Bulan Lalu' per resto
        # (user: "Nominal Deviasi total per resto juga tambahan di tab
        # nominal deviasi ini buat versus bulan lalu"): Σ 'Nominal Lalu'
        # self._lalu_df per resto-norm (kunci join = _norm_resto_lalu —
        # pola popup: '1030.BDGSET' ↔ 'BDGSET'); resto tanpa baris di
        # file → NaN (tampil '-'); Σ skipna = pola kolom Sekarang.
        # v3.9.45 — generalisasi: SATU kolom per bulan (helper
        # _assign_lalu_column — bulan pertama pakai nama kolom lama).
        self._assign_lalu_column(g, pairs, "Nominal Deviasi Bulan Lalu",
                                 self._lalu_df)
        for _cid, _lab, _wk in self._lalu_extra:
            _fr = next((_f for _l, _f in self._lalu_frames[1:]
                        if f"Lalu {_l}" == _cid), None)
            self._assign_lalu_column(g, pairs, _cid, _fr)
        # v3.9.63 — KOLOM 'Persen Kenaikan/Penurunan' (user: "Persen
        # kenaikan/penurunan (bisa sort)"): (H − Lalu) ÷ |Lalu| × 100
        # per resto vs kolom Bulan Lalu UTAMA (hitung_persen_kenaikan —
        # None bila tak terdefinisi: lalu kosong/0 dgn H ≠ 0).
        g["Persen Kenaikan/Penurunan"] = pd.Series(
            [hitung_persen_kenaikan(_h, _l) for _h, _l in zip(
                g["Nominal Deviasi"],
                g["Nominal Deviasi Bulan Lalu"])],
            index=g.index, dtype="float64")
        # snapshot utk filter header (SEBELUM filter diterapkan)
        self._result_df = g.copy()
        return g

    def _assign_lalu_column(self, g: pd.DataFrame, pairs: pd.DataFrame,
                            col_id: str, lalu: "pd.DataFrame | None"):
        """v3.9.45 — pasang kolom nominal-bulan-lalu per resto (dipakai
        utk kolom 'Nominal Deviasi Bulan Lalu' utama MAUPUN kolom
        dinamis 'Lalu <label>' bulan ≥2 — logika identik v3.9.38/3.9.42).
        """
        if lalu is not None and not lalu.empty \
                and "Nominal Lalu" in lalu.columns:
            # v3.9.42 — audit 61-b P1: KOLOM LALU dibatasi ke pasangan
            # yang HADIR di data sekarang hasil filter kategori (join
            # kiri via (_resto_norm, _bahan_norm) — PERSIS popup
            # rincian & TOTAL LALU popup). Dulu: seluruh file per resto →
            # angka tabel ≠ angka popup utk resto SAMA (tampil hampir
            # bersamaan) + kolom pembanding tak ikut scope filter
            # kategori (pasangan Supplies lalu ikut terhitung →
            # perbandingan tidak sebanding).
            _key_now = set(zip(
                pairs["Resto"].astype(str).map(_norm_resto_lalu),
                pairs["Nama Barang"].astype(str).map(_norm_name_lalu)))
            lalu_f = lalu[[
                (_rn, _bn) in _key_now for _rn, _bn in zip(
                    lalu["_resto_norm"].astype(str),
                    lalu["_bahan_norm"].astype(str))]]
            per_lalu = lalu_f.groupby("_resto_norm")["Nominal Lalu"].sum()
            g[col_id] = (
                g["Resto"].astype(str).map(_norm_resto_lalu).map(per_lalu)
                .astype("float64"))
        else:
            g[col_id] = pd.Series(
                [float("nan")] * len(g), dtype="float64")

    # =========================================================================
    # REFRESH + RENDER
    # =========================================================================
    def _refresh(self, sync: bool = False):
        if self.data is None or self.data.empty:
            # v3.9.64 — FIX (audit 15-a R4): data kosong TIDAK boleh
            # menyisakan baris LAMA di layar — dulu early-return tanpa
            # clear → tabel utama + anak tab masih menampilkan render
            # sebelumnya dgn status "Belum ada data." (menyesatkan).
            # Bersihkan kedua tabel + tag per-cell + frame anak tab,
            # lalu render anak tab (status anak tab jujur).
            if self._insert_cancel is not None:
                self._insert_cancel()
                self._insert_cancel = None
            if self._nh_insert_cancel is not None:
                self._nh_insert_cancel()
                self._nh_insert_cancel = None
            self._noharga_df = None
            self._neg_cells = []
            self._total_cells = []
            self._nh_neg_cells = []
            with contextlib.suppress(tk.TclError):
                self.tree.delete(*self.tree.get_children(""))
            apply_cell_tag(self.tree, "neg_cell", [])
            apply_cell_tag(self.tree, "total_cell", [])
            self._render_noharga()
            self.status_var_label.set("Belum ada data.")
            with contextlib.suppress(Exception):
                self._total_var.set("")
            return
        if self._busy:
            self._pending = True
            return
        self._busy = True
        self._dirty = False          # clear saat refresh berjalan (pola 48-e)
        data = self.data
        h = self.tanggal_h
        gen = self._render_gen

        def work():
            return self._compute_resto(data, h)

        def done(payload):
            if gen != self._render_gen:
                self._busy = False
                if self._pending:
                    self._pending = False
                    self._refresh()
                return
            self._render_rows(payload)

        def on_error(err):
            self._busy = False
            self._pending = False
            self.status_var_label.set(
                f"⚠ Gagal menghitung nominal per resto: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menghitung nominal per resto…",
                  on_error=on_error, sync=sync)

    def _render_rows(self, result: pd.DataFrame):
        if self._insert_cancel is not None:
            self._insert_cancel()
            self._insert_cancel = None
        self.tree.delete(*self.tree.get_children(""))
        self._close_detail_wins()    # data baru → popup rincian basi
        self._neg_cells = []
        self._total_cells = []
        # v3.9.45 — kolom dinamis 'Lalu <label>' per bulan file deviasi
        # (multi-file ⚖ Komparasi): sinkronkan dulu SEBELUM heading
        # (heading kolom baru baru bisa dipasang).
        self._ensure_tree_columns()

        # heading dinamis mengikuti TANGGAL H
        self.tree.heading(
            "Nominal Deviasi",
            text=f"Nominal Deviasi (H={self.tanggal_h})")
        # v3.9.41 — heading lalu menyebut MINGGU pembanding ter-cocok;
        # v3.9.45 — multi-bulan: bulan utama + label bulan ≥2 di
        # heading kolom dinamis (label bulan + minggu masing-masing).
        _lab0 = (self._lalu_frames[0][0]
                 if self._lalu_frames else None)
        self.tree.heading(
            "Nominal Deviasi Bulan Lalu",
            text=("Nominal Deviasi Bulan Lalu"
                  + (f" · {_lab0}" if _lab0 else "")
                  + (f" ({self._lalu_week})" if self._lalu_week else "")))
        for _cid, _lab, _wk in self._lalu_extra:
            self.tree.heading(
                _cid,
                text=_cid + (f" ({_wk})" if _wk else ""))
        if getattr(self, "header_filters", None) is not None:
            self.header_filters.refresh_icons()
        # v3.9.63 — render ANAK TAB 'Tanpa Harga' GLOBAL di sini (SEBELUM
        # cabang kosong): frame dihitung _compute_resto dari data mentah
        # — tak tergantung hasil/filter kategori tabel utama, jadi tetap
        # dirender walau tabel utama kosong/terfilter habis.
        self._render_noharga()

        if result is None or result.empty:
            # v3.9.59 — FIX 2e-03: status JUJUR saat KATEGORI menghabiskan
            # baris — dulu SELALU 'Tidak ada baris DEVIASI tanggal H'
            # (menyalahkan tanggal H) padahal H punya baris; user terarah
            # mengubah TANGGAL H sia-sia. Mirror pesan lolos-filter aktif
            # (pola pivot 6c-03 / deviasi v3.9.49): sebut kategori +
            # jumlah baris pra-filter.
            if self._kategori_sel and self._n_dev_h_unfiltered > 0:
                self.status_var_label.set(
                    f"0 dari {fmt_int_id(self._n_dev_h_unfiltered)} baris "
                    f"DEVIASI tanggal {self.tanggal_h} lolos filter aktif "
                    f"(KATEGORI: {self._kategori_sel}).")
            else:
                self.status_var_label.set(
                    f"Tidak ada baris DEVIASI tanggal {self.tanggal_h}.")
            self._total_var.set("")

            def done_empty():
                self._busy = False
                if self._pending:
                    self._pending = False
                    self._refresh()

            done_empty()
            return

        # filter header ⧩ (nilai TERFORMAT — identik yang tampil)
        filtered = result
        for col, sel in self._col_sel.items():
            if sel is not None and col in filtered.columns:
                fmt = self._format_col_series(col, filtered[col])
                filtered = filtered[fmt.isin(sel)]
        if filtered.empty:
            # v3.9.68 — TRI-STATE (audit eksternal T1): bila penyebabnya
            # seleksi ⧩ KOSONG → pesan jujur eksplisit (bukan generik).
            _hint = zero_row_filter_message(self._col_sel)
            if _hint:
                self.status_var_label.set(_hint)
            else:
                # v3.9.59 — FIX 2e-03 (kolom ⧩): idem jalur kategori —
                # sebut kolom filter aktif + jumlah baris pra-filter.
                _act = ", ".join(c for c, s in self._col_sel.items()
                                 if s is not None)
                self.status_var_label.set(
                    f"0 dari {fmt_int_id(len(result))} resto lolos "
                    f"filter aktif"
                    + (f" ({_act})" if _act else "") + ".")
            self._total_var.set("")
            self._render_done_guard()
            return

        col_ids = self._result_cols()
        n = len(filtered)
        total_nom = float(filtered["Nominal Deviasi"].dropna().sum()) \
            if "Nominal Deviasi" in filtered.columns else 0.0
        total_lalu = float(
            filtered["Nominal Deviasi Bulan Lalu"].dropna().sum()) \
            if "Nominal Deviasi Bulan Lalu" in filtered.columns else 0.0
        # v3.9.45 — total per bulan ≥2 (kolom dinamis)
        totals_extra = {}
        for _cid, _lab, _wk in self._lalu_extra:
            totals_extra[_cid] = (
                float(filtered[_cid].dropna().sum())
                if _cid in filtered.columns else 0.0)
        # v3.9.63 — total per klas kategori + jumlah tanpa harga GLOBAL
        # (frame anak tab) — 'N Barang'/'Tanpa Harga' tak lagi jadi
        # kolom tabel (user: "hapus aja").
        total_com = float(filtered["COM Deviasi"].dropna().sum()) \
            if "COM Deviasi" in filtered.columns else 0.0
        total_pkg = float(
            filtered["Biaya Packaging"].dropna().sum()) \
            if "Biaya Packaging" in filtered.columns else 0.0
        _nh_total = (len(self._noharga_df)
                     if self._noharga_df is not None else 0)
        n_neg = int((filtered["Nominal Deviasi"] < 0).sum())

        items = []
        for i in range(n):
            row = filtered.iloc[i]
            nom = row.get("Nominal Deviasi", 0)
            nom_l = row.get("Nominal Deviasi Bulan Lalu")
            # v3.9.45 — nilai kolom dinamis bulan ≥2 + minus merah
            # per-cell (pola kolom Lalu utama)
            vals_extra = [row.get(_cid) for _cid, _l, _w
                          in self._lalu_extra]
            values = [
                str(row["Resto"]),
                # v3.9.63 — Σ nominal per klas kategori (user: "diganti
                # dengan nominal deviasi per kategori: kolom COM Deviasi
                # + kolom Packaging") — 0.0 → '-' (fmt_rp_cell).
                fmt_rp_cell(row.get("COM Deviasi")),
                fmt_rp_cell(row.get("Biaya Packaging")),
                # v3.9.51 — Currency Rp (user: "Semua data nominal diberi
                # format Currency Rp").
                fmt_rp_cell(nom),
                fmt_rp_cell(nom_l),
                # v3.9.63 — persen kenaikan/penurunan vs bulan lalu
                # (user: "Persen kenaikan/penurunan (bisa sort)").
                fmt_pct_cell(row.get("Persen Kenaikan/Penurunan")),
            ] + [fmt_rp_cell(v) for v in vals_extra]
            values = tuple(values)
            tags = ["evenrow" if i % 2 == 0 else "oddrow"]
            # v3.9.63 — minus merah per-cell SEMUA kolom nominal + persen
            # (COM Deviasi/Biaya Packaging/persen ikut — pola kolom Lalu).
            com_v = self._safe_float(row.get("COM Deviasi"))
            pkg_v = self._safe_float(row.get("Biaya Packaging"))
            pct_v = self._safe_float(
                row.get("Persen Kenaikan/Penurunan"))
            nom_v = self._safe_float(nom)
            noml_v = self._safe_float(nom_l)
            _neg_any = any(v is not None and v < 0
                           for v in (com_v, pkg_v, nom_v, noml_v, pct_v))
            if self._cell_tags:
                for _v, _c in ((com_v, "COM Deviasi"),
                               (pkg_v, "Biaya Packaging"),
                               (nom_v, "Nominal Deviasi"),
                               (noml_v, "Nominal Deviasi Bulan Lalu"),
                               (pct_v, "Persen Kenaikan/Penurunan")):
                    if _v is not None and _v < 0:
                        self._neg_cells.append((f"row_{i}", _c))
                for _j, _ev in enumerate(vals_extra):
                    _evf = self._safe_float(_ev)
                    if _evf is not None and _evf < 0:
                        self._neg_cells.append(
                            (f"row_{i}", self._lalu_extra[_j][0]))
                        _neg_any = True
            elif _neg_any:
                tags.append("negative")
            items.append(("", f"row_{i}",
                          {"values": values, "tags": tuple(tags)}))

        # baris TOTAL di ujung (jumlah semua resto tampil); v3.9.51 → Rp;
        # v3.9.63 → + Σ COM/Packaging + persen TOTAL (vs Lalu utama).
        values_total = (
            "TOTAL",
            fmt_rp_cell(total_com),
            fmt_rp_cell(total_pkg),
            fmt_rp_cell(total_nom),
            fmt_rp_cell(total_lalu),
            fmt_pct_cell(
                hitung_persen_kenaikan(total_nom, total_lalu)),
        ) + tuple(fmt_rp_cell(totals_extra[_cid])
                   for _cid, _l, _w in self._lalu_extra)
        items.append(("", "row_total",
                      {"values": values_total, "tags": ("total",)}))
        for col in col_ids:
            self._total_cells.append(("row_total", col))

        status = (f"{fmt_int_id(n)} resto · TANGGAL H = "
                  f"{self.tanggal_h}")
        if self._kategori_sel:
            status += f" · KATEGORI {self._kategori_sel}"
        if n_neg:
            status += f" · {fmt_int_id(n_neg)} resto minus"
        # v3.9.63 — jumlah tanpa harga GLOBAL (anak tab — kolom 'Tanpa
        # Harga' dihapus dari tabel; user: "dan itu buat anak tab baru").
        if _nh_total:
            status += (f" · {fmt_int_id(_nh_total)} pasangan tanpa harga "
                       "(anak tab Tanpa Harga)")
        # v3.9.38 — versus bulan lalu di footer (chip TOTAL juga);
        # v3.9.41 — minggu pembanding TER-COCOK H disebut (user:
        # "sesuaikan week nya ... supaya jelas minggu mana");
        # v3.9.45 — MULTI-BULAN: total per bulan ≥2 ikut disebut
        # (label bulan singkat — pembanding beberapa bulan sekaligus).
        if self._lalu_loaded:
            _wk = (f" ({self._lalu_week})"
                   if self._lalu_week else "")
            status += f" · TOTAL LALU {fmt_rp_cell(total_lalu)}{_wk}"
            for _cid, _lab, _wk in self._lalu_extra:
                _wkx = (f" ({_wk})" if _wk else "")
                status += (f" · LALU {_lab} "
                           f"{fmt_rp_cell(totals_extra.get(_cid, 0.0))}"
                           f"{_wkx}")
        else:
            status += " · LALU: file deviasi belum dimuat (⚖ Komparasi)"
        self.status_var_label.set(status)
        if self._lalu_loaded:
            _wk2 = (f" · MINGGU {self._lalu_week}"
                    if self._lalu_week else "")
            _chip = (f"TOTAL {fmt_rp_cell(total_nom)} · "
                     f"LALU {fmt_rp_cell(total_lalu)}{_wk2}")
            # v3.9.45 — chip: pembanding bulan ≥2 (ringkas — label bulan)
            for _cid, _lab, _wk in self._lalu_extra[:3]:
                _chip += (f" · {_lab} "
                          f"{fmt_rp_cell(totals_extra.get(_cid, 0.0))}")
            if len(self._lalu_extra) > 3:
                _chip += f" · +{len(self._lalu_extra) - 3} bulan lagi"
            self._total_var.set(_chip)
        else:
            self._total_var.set(
                f"TOTAL {fmt_rp_cell(total_nom)}")

        self._insert_cancel = insert_tree_items(
            self.tree, items, batch=500, on_done=self._render_done)

    def _render_done_guard(self):
        """Jalur hasil-kosong tetap berakhir di render_done (reset
        _busy + proses pending — pola 48-e FIX 2/3 mode Nominal)."""
        self._reapply_cell_tags(self.tree)
        # v3.9.55 — F8: auto-fit kolom SEKALI per muat data
        autofit_tree_once(self, self.tree)
        self._busy = False
        if self._pending:
            self._pending = False
            self._pending_sort = None
            self._refresh()
        elif self._pending_sort:
            col, rev = self._pending_sort
            self._pending_sort = None
            self._sort_by(col, reverse=rev)

    def _render_done(self):
        self._reapply_cell_tags(self.tree)
        # v3.9.55 — F8: auto-fit kolom SEKALI per muat data
        autofit_tree_once(self, self.tree)
        self._busy = False
        if self._pending:
            self._pending = False
            self._pending_sort = None
            self._refresh()
        elif self._pending_sort:
            col, rev = self._pending_sort
            self._pending_sort = None
            self._sort_by(col, reverse=rev)

    def _reapply_cell_tags(self, tree):
        """Pasang ulang tag per-cell (sort/clone = delete+reinsert →
        tag ter-reset; pola mode Nominal).
        v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list kosong
        = clear overlay — render tanpa sel minus tidak meninggalkan
        label STALE)."""
        if not self._cell_tags:
            return
        apply_cell_tag(tree, "neg_cell", self._neg_cells)
        apply_cell_tag(tree, "total_cell", self._total_cells)

    # =========================================================================
    # DOUBLE-CLICK → POPUP (rincian per resto / tanpa harga)
    # =========================================================================
    def _on_double_click(self, event):
        tree = event.widget
        try:
            # FIX 6d2-04 — resolve baris dari POSISI KLIK (identify_row),
            # bukan selection(): double-click di AREA KOSONG di bawah
            # baris terakhir TIDAK mengubah seleksi Tk → kode lama memakai
            # seleksi LAMA → popup resto SEBELUMNYA terbuka 'dari kotak
            # kosong' (parity in_selisih_view._on_double_click /
            # InDetailPopup). getattr: pemanggil programatik/test bisa
            # mengirim event tanpa posisi → fallback seleksi (perilaku
            # lama utuh utk jalur tanpa koordinat).
            _y = getattr(event, "y", None)
            iid = tree.identify_row(_y) if _y is not None else None
            if _y is not None and not iid:
                return          # klik area kosong — jangan buka popup basi
            if iid is None:
                sel = tree.selection()
                if not sel:
                    return
                iid = sel[0]
            # v3.9.63 — cabang kolom 'Tanpa Harga' DIHAPUS (kolomnya tak
            # ada lagi; daftar tanpa harga kini anak tab 'Tanpa Harga').
            # Baris TOTAL → tanpa popup (dulu: sel Tanpa Harga TOTAL →
            # popup SEMUA resto).
            if iid == "row_total":
                return
            resto = str(tree.set(iid, "Resto"))
        except tk.TclError:
            return
        self._show_resto_popup(resto)

    def _close_detail_wins(self):
        # v3.9.42 — iterasi COPY: binding <Destroy> (cleanup manual)
        # menghapus elemen dari list SAAT destroy → iterasi list asli
        # langsung = RuntimeError 'list changed size during iteration'.
        for w in list(self._detail_wins):
            with contextlib.suppress(tk.TclError):
                w.destroy()
        self._detail_wins = []

    def _lalu_map(self) -> dict:
        """v3.9.36 — peta (_resto_norm, _bahan_norm) → baris frame
        Bulan Lalu (snapshot self._lalu_df).
        PERF 6d2 (audit 6-d2) — dibangun VEKTOR (zip kolom +
        to_dict("records")), bukan `iloc` per baris: pembuatan Series per
        baris ~100ms @5.000 baris di MAIN thread SETIAP popup rincian
        dibuka (file deviasi multi-bulan nyata 10-30 ribu baris → ratusan
        ms). Kontrak konsumen identik: nilai = baris ber-.get kolom (dict
        record, bukan Series — konsumen hanya memanggil
        .get("Nominal Lalu") / cek None); kunci ganda: baris TERAKHIR
        menang (identik semantik loop lama)."""
        lalu = self._lalu_df
        if lalu is None or lalu.empty:
            return {}
        keys = zip(lalu["_resto_norm"].astype(str).tolist(),
                   lalu["_bahan_norm"].astype(str).tolist())
        return dict(zip(keys, lalu.to_dict("records")))

    def _lalu_maps(self) -> list:
        """v3.9.45 — list peta (_resto_norm, _bahan_norm) → baris frame
        Bulan Lalu PER BULAN (index 0 = bulan utama self._lalu_df;
        index berikut = bulan ≥2 self._lalu_frames[1:]) — popup rincian
        multi-bulan.
        PERF 6d2 (audit 6-d2) — vektor per frame (lihat _lalu_map)."""
        maps = []
        for _lab, _fr in self._lalu_frames:
            m = {}
            if _fr is not None and not _fr.empty:
                keys = zip(_fr["_resto_norm"].astype(str).tolist(),
                           _fr["_bahan_norm"].astype(str).tolist())
                m = dict(zip(keys, _fr.to_dict("records")))
            maps.append(m)
        return maps

    def _show_resto_popup(self, resto: str):
        """Popup RINCIAN PER ITEM utk satu resto (double-click baris) —
        v3.9.36 5 kolom (user: "Nama resto, nama barang, Kuantiti
        deviasi, Nominal deviasi Sekarang, Nominal deviasi bulan lalu").
        Data = self._pairs_df (sekarang) + self._lalu_df (bulan lalu —
        snapshot compute terakhir, read-only).
        v3.9.45 — MULTI-BULAN: + SATU KOLOM 'Lalu <label>' per bulan
        file deviasi ≥2 (user: "support buat multiple file deviasi buat
        compare dengan beberapa bulan lalu") — popup = pembanding per
        barang lintas beberapa bulan sekaligus."""
        pairs = self._pairs_df
        if pairs is None or pairs.empty:
            return
        sub = pairs[pairs["Resto"].astype(str) == str(resto)].copy()
        if sub.empty:
            return
        lalu_map = self._lalu_map()
        # v3.9.45 — peta per bulan ≥2 (kolom dinamis popup)
        _maps_extra = self._lalu_maps()[1:]
        _extra_cols = [(cid, 150, "e")
                       for cid, lab, wk in self._lalu_extra]

        win = tk.Toplevel(self)
        win.title(f"Nominal Deviasi — {resto} (H={self.tanggal_h})")
        self._detail_wins.append(win)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        # v3.9.42 — audit 61-b P3: popup ditutup manual → buang dari
        # _detail_wins (dulu referensi + closure df tertahan sampai
        # refresh berikutnya) + Esc menutup (pola popup lain).
        win.bind("<Destroy>", lambda _e, _w=win: (
            _w in self._detail_wins and self._detail_wins.remove(_w)),
            add="+")
        win.bind("<Escape>", lambda _e, _w=win: _w.destroy())
        with contextlib.suppress(tk.TclError):
            win.transient(self.winfo_toplevel())
        # v3.9.59 — FIX 2e-10: MODAL (grab_set) — paritas popup
        # drill-down tab lain (InDetailPopup in_selisih / deviasi_popup /
        # DetailsPopup semua grab). Dulu non-modal → jendela utama
        # tetap interaktif saat popup terbuka + popup ganda menumpuk;
        # destroy melepas grab otomatis.
        with contextlib.suppress(tk.TclError):
            win.grab_set()

        body = tk.Frame(win, bg=C_BG)
        body.pack(fill="both", expand=True)

        head = tk.Frame(body, bg=C_CARD)
        head.pack(fill="x")
        tk.Label(head, text=f"Rincian per barang — resto {resto} · "
                            f"TANGGAL H {self.tanggal_h}",
                 bg=C_CARD, fg=C_HEADER, font=font(10, "bold")).pack(
            side="left", padx=10, pady=8)
        # v3.9.41 — minggu pembanding file lalu DISEBUT (user: "sesuaikan
        # week nya" — supaya jelas minggu mana yang dibandingkan).
        _wk_txt = (f" · minggu {self._lalu_week} (ter-cocok H)"
                   if self._lalu_week else "")
        tk.Label(head,
                 text="Sekarang = Harga 41.09 × Deviasi (H) · Bulan Lalu "
                      f"= nilai RESMI file deviasi{_wk_txt}",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=font(8)).pack(
            side="right", padx=10)

        # v3.9.45 — kolom popup = BASIS + kolom dinamis per bulan ≥2
        # (heading menyebut label bulan + minggu ter-cocok masing2).
        _popup_cols = list(POPUP_COLUMNS) + _extra_cols
        col_ids = [c[0] for c in _popup_cols]
        tree = ttk.Treeview(body, columns=col_ids, show="headings",
                            selectmode="extended")
        # v3.9.50 — [MINOR audit 3-a] choke-point: popup ini dulu TANPA
        # enable_col_resize → tanpa smooth wheel + binding CTRL-zoom
        # tingkat widget (parity 14 call site tree lain).
        enable_col_resize(tree)
        # v3.9.41 — tombol ⛶/↺ (user: "pop up ... kurang besar dan
        # lebar") — setelah tree dibuat (command men-reference tree).
        _popup_head_buttons(head, win, tree, _popup_cols)
        for col_name, width, anchor in _popup_cols:
            tree.column(col_name, width=width, minwidth=34,
                        anchor=anchor)
            tree.heading(col_name, text=col_name)
        for _cid, _lab, _wk in self._lalu_extra:
            tree.heading(_cid, text=_cid + (f" ({_wk})" if _wk else ""))
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("neg_cell", foreground="#dc2626")
        tree.tag_configure("total", background="#e2e8f0",
                           foreground="#0f172a")
        tree.tag_configure("total_cell", background="#e2e8f0",
                           foreground="#0f172a")

        neg_cells = []
        total_cells = []
        items = []
        sub = sub.reset_index(drop=True)
        _nolalu = 0
        # v3.9.45 — Σ per bulan ≥2 (hanya pasangan yang TAMPIL — join
        # kiri dari pasangan sekarang, pola TOTAL LALU utama)
        totals_extra = [0.0] * len(_maps_extra)
        for i in range(len(sub)):
            row = sub.iloc[i]
            nom = row.get("Nominal")
            # pasangan Bulan Lalu — kunci ternormalisasi (pola join
            # komparasi: '1030.BDGSET' ↔ 'BDGSET')
            _key_l = (_norm_resto_lalu(resto),
                      _norm_name_lalu(row["Nama Barang"]))
            lrow = lalu_map.get(_key_l)
            nom_lalu = lrow.get("Nominal Lalu") if lrow is not None \
                else None
            if lrow is None:
                _nolalu += 1
            # nilai per bulan ≥2 + akumulasi total popup
            vals_extra = []
            for _mi, _m in enumerate(_maps_extra):
                _r = _m.get(_key_l)
                _v = _r.get("Nominal Lalu") if _r is not None else None
                vals_extra.append(_v)
                try:
                    if _v is not None and not pd.isna(_v):
                        totals_extra[_mi] += float(_v)
                except (TypeError, ValueError):
                    pass
            values = (
                str(resto), str(row["Nama Barang"]),
                fmt_nominal_cell(row.get("Qty Deviasi", 0)),
                # v3.9.51 — kolom nominal popup → Currency Rp (Qty tetap
                # format kuantitas).
                fmt_rp_cell(nom),
                fmt_rp_cell(nom_lalu),
            ) + tuple(fmt_rp_cell(v) for v in vals_extra)
            tags = ["evenrow" if i % 2 == 0 else "oddrow"]
            nom_v = None
            try:
                if nom is not None and not pd.isna(nom):
                    nom_v = float(nom)
            except (TypeError, ValueError):
                nom_v = None
            noml_v = None
            try:
                if nom_lalu is not None and not pd.isna(nom_lalu):
                    noml_v = float(nom_lalu)
            except (TypeError, ValueError):
                noml_v = None
            _neg_any = ((nom_v is not None and nom_v < 0)
                        or (noml_v is not None and noml_v < 0))
            if self._cell_tags:
                if nom_v is not None and nom_v < 0:
                    neg_cells.append(
                        (f"row_{i}", "Nominal Deviasi Sekarang"))
                if noml_v is not None and noml_v < 0:
                    neg_cells.append(
                        (f"row_{i}", "Nominal Deviasi Bulan Lalu"))
                for _j, _ev in enumerate(vals_extra):
                    _evf = None
                    try:
                        if _ev is not None and not pd.isna(_ev):
                            _evf = float(_ev)
                    except (TypeError, ValueError):
                        _evf = None
                    if _evf is not None and _evf < 0:
                        neg_cells.append(
                            (f"row_{i}", _extra_cols[_j][0]))
                        _neg_any = True
            elif _neg_any:
                tags.append("negative")
            items.append(("", f"row_{i}",
                          {"values": values, "tags": tuple(tags)}))

        total_nom = float(sub["Nominal"].dropna().sum()) \
            if "Nominal" in sub.columns else 0.0
        # Σ Bulan Lalu hanya pasangan yang TAMPIL di popup ini (join
        # kiri dari pasangan sekarang — pasangan file-tak-match tak
        # ditarik; skipna seperti TOTAL sekarang).
        total_lalu = 0.0
        for i in range(len(sub)):
            lrow = lalu_map.get(
                (_norm_resto_lalu(resto),
                 _norm_name_lalu(sub.iloc[i]["Nama Barang"])))
            if lrow is not None:
                v = lrow.get("Nominal Lalu")
                try:
                    if v is not None and not pd.isna(v):
                        total_lalu += float(v)
                except (TypeError, ValueError):
                    pass
        items.append(("", "row_total", {
            "values": ("TOTAL", "", "",
                       fmt_rp_cell(total_nom),
                       fmt_rp_cell(total_lalu))
            + tuple(fmt_rp_cell(v) for v in totals_extra),
            "tags": ("total",)}))
        for c in col_ids:
            total_cells.append(("row_total", c))

        vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        # v3.9.42 — audit 61-b P2: + SCROLLBAR HORIZONTAL — total lebar
        # kolom bisa melebihi jendela saat dikecilkan (dulu kolom
        # Keterangan/kanan TERPOTONG tanpa cara melihatnya).
        wrap = tk.Frame(body, bg=C_BG)
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set,
                       xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="top", fill="both", expand=True)
        wrap.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        enable_multi_select(tree)   # Ctrl+A + Ctrl+C TSV

        insert_tree_items(tree, items, batch=500, on_done=lambda: (
            apply_cell_tag(tree, "neg_cell", neg_cells),
            apply_cell_tag(tree, "total_cell", total_cells)))

        foot = tk.Frame(body, bg=C_CARD)
        foot.pack(fill="x")
        n_no = int(sub["Nominal"].isna().sum()) \
            if "Nominal" in sub.columns else 0
        foot_txt = (f"{len(sub)} barang · {fmt_int_id(n_no)} tanpa harga · "
                    f"TOTAL SEKARANG {fmt_rp_cell(total_nom)} · "
                    f"TOTAL BULAN LALU {fmt_rp_cell(total_lalu)}")
        if self._lalu_week:
            foot_txt += f" · Lalu: minggu {self._lalu_week} (ter-cocok H)"
        # v3.9.45 — total per bulan ≥2 di footer popup
        for _mi, (_cid, _lab, _wk) in enumerate(self._lalu_extra):
            foot_txt += (f" · {_lab} "
                         f"{fmt_rp_cell(totals_extra[_mi])}")
        if not self._lalu_loaded:
            foot_txt += " · file deviasi belum dimuat (⚖ Komparasi)"
        elif _nolalu:
            foot_txt += (f" · {fmt_int_id(_nolalu)} barang tanpa "
                         "pasangan di file")
        tk.Label(foot, text=foot_txt,
                 bg=C_CARD, fg=C_HEADER, font=font(8, "bold")).pack(
            side="left", padx=10, pady=6)
        # v3.9.59 — FIX 2f-13: 'Tutup (Esc)' (kanon — popup ini bind
        # <Escape>; 'Tutup' polos menyembunyikan shortcut).
        GhostButton(foot, text="Tutup (Esc)", command=win.destroy).pack(
            side="right", padx=10, pady=4)

        # v3.9.41 — ukuran BESAR (±94%×88% layar; dulu maks 1000×560)
        # + kolom diskala memenuhi lebar jendela + re-scale saat resize
        # (user: "pop up tab nominal deviasi ada bug kurang besar dan
        # lebar")
        # v3.9.42 — minsize DI-CLAMP ke geometri layar (audit 61-b P3:
        # minsize 900 di layar <960 melebarkan jendela MELAMPAUI layar).
        _w41, _h41 = _popup_geometry(win)
        _scale_popup_columns(tree, _popup_cols, _w41 - 36)
        _bind_popup_rescale(win, tree, _popup_cols)
        win.minsize(min(900, _w41), min(420, _h41))
        win.focus_set()

    # -------------------------------------------------------------------------
    # v3.9.63 — popup barang TANPA HARGA DIHAPUS (double-click sel kolom
    # 'Tanpa Harga' — kolomnya tak ada lagi): daftar tanpa harga kini
    # ANAK TAB 'Tanpa Harga' GLOBAL (selalu terlihat + filter kategori
    # sendiri — lihat _build_noharga_tab/_render_noharga; popup per-resto
    # digantikan penuh).
    # -------------------------------------------------------------------------

    @staticmethod
    def _noharga_ket(harga_tampil) -> str:
        """Alasan pasangan tanpa harga — dari 'Harga Tampil' pairs:
        '-' = barang tak ada / harga None di 41.09; ber-'*' = satuan
        rekap tak ter-cover peta rasio (harga as-is ditampilkan)."""
        s = str(harga_tampil or "").strip()
        if not s or s == "-":
            return "barang tak ada di 41.09 (09.Harga)"
        if "*" in s:
            return f"satuan tak terkonversi — harga 41.09: {s}"
        return "harga 41.09 kosong"

    # =========================================================================
    # TOOLBAR TABEL
    # =========================================================================
    def _auto_fit(self):
        auto_fit_columns(self.tree)

    def _maximize(self):
        def filter_setup(new_tree):
            def _after_filter(t=new_tree):
                self._pin_total_row(t)
                self._reapply_cell_tags(t)

            attach_clone_filters(
                new_tree, self._result_cols(),
                get_values=lambda c: self._col_values(c),
                on_after_filter=_after_filter)

        return open_tree_maximized(
            self.tree, "Nominal Deviasi per Resto",
            setup_tags=lambda t: self._setup_tags(t),
            on_filter_setup=filter_setup,
            on_render_done=self._reapply_cell_tags)
