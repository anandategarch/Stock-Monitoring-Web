"""
pivot_view.py — Pivot matrix view (v3.2).

v3.9.71 — FREEZE KOLOM NAMA BARANG (user: "di tab pivot tabel gak
bsia freeze kolom nama barang ya? sehingga jika aku scroll ke kanan
bisa kefreze"): kolom #0 (nama barang + baris metric) kini TAMPIL DI
TREE BEKU KIRI (widgets.FrozenNamePane) dan DISEMBUNYIKAN di tree
utama (width 0 + _autofit_skip) — menggulir ke KANAN tidak lagi
menggeser nama barang (kontrak freeze ala Excel). Scroll vertikal +
seleksi tersinkron dua arah; funnel ⧩ Nama Barang menempel di heading
tree beku; clone ⛶ Layar Penuh ikut memakai freeze-pane (open_tree_
maximized frozen_name=True — funnel clone di sisi beku, filter baris
tetap dijalankan di tree utama clone, isi beku disalin ulang setelah
filter/sort).

v3.9.69 — P1.1 (audit eksternal ke-2): semantik ☑ "Sembunyikan baris
kosong" = SEMUA sel baris 0/kosong (dulu "total ≤ 0" — baris deviasi
negatif/cancel-out tersembunyinya juga; sinyal retur justru penting).
Konsisten di DUA jalur: render _compute_payload + daftar ⧩ #0.

v3.9.33 — AUDIT FIX (48-d/48-f, fix 49-a):
- (LOW) fallback validasi TANGGAL AWAL kini -31 (dulu 1 — input
  invalid SENYAP mempersempit rentang; kini revert ke batas kiri
  default v3.8).
- (MEDIUM) _populate_filters me-reset seleksi RESTO/SOURCE/KATEGORI
  ke "(All)" saat reload data (dulu seleksi lama tetap terpasang
  senyap — nilai tak ada lagi di data baru → 0 baris senyap) +
  membersihkan daftar nilai bila kolom hilang di schema baru.
- (HIGH sebagian / 48-f) 0 baris pasca-pipeline → EMPTY STATE +
  status berpenjelasan aksi (dulu tabel kosong senyap di belakang
  pipeline "SELESAI" hijau).

v3.9.20 (deep audit 34-e/fix 35-c2): popup Nama Barang = barang yang
TAMPIL (RESTO mode Tanggal + SOURCE + KATEGORI + rentang Tanggal +
☑ hide-empty; filter sendiri dikecualikan) + merah negatif #dc2626
(seragam 11 view — dulu #CC0000 satu-satunya yang beda).

Dua mode pivot (segment "PIVOT PER" di atas tabel):
- 🏪 RESTO (default): baris = Nama Barang × JENIS, kolom = NAMA RESTO,
  nilai = total NILAI per resto dalam rentang Tanggal. Hanya baris dengan
  SEMUA sel 0/kosong yang disembunyikan (☑ "Sembunyikan baris kosong",
  default ON — semantik v3.9.69: baris dengan sel ≠ 0 TAMPIL, termasuk
  sel negatif/cancel-out); kolom Total sengaja TIDAK ditampilkan.
  Contoh: item yang hanya ada di resto MLGPAR tetap tampil (nilainya ada),
  item tanpa nilai di semua resto disembunyikan.
- 📅 TANGGAL: kolom = Tanggal (perilaku v3.0) + rentang tanggal.

v3.9.2 (permintaan user: "minus harusnya cuman merah per cell bukan per
baris dan pivot tabel nya bisa export excel"):
- MINUS MERAH PER CELL (bukan per baris) — Tk 9 `treeview tag cell add`
  (helper apply_cell_tag): hanya cell bernilai < 0 yang font-nya merah;
  baris 3.DEVIASI tidak lagi selalu merah; 7.Selisih ≠ 0 tetap dapat fill
  merah muda per baris, font merah per-cell pada nilai ≠ 0. Fallback Tk 8:
  perilaku lama (tag per baris) via CELL_TAGS_SUPPORTED.
- Tombol 💾 Export Excel: matrix pivot SESUAI TAMPILAN (filter RESTO/
  SOURCE/KATEGORI + rentang Tanggal + mode + sembunyikan-baris-kosong +
  kolom tampil ◱) → .xlsx via write_pivot_display_sheet — minus = font
  merah per cell (mirror UI), 0 = font putih (trik file user).

v3.8:
- Default rentang tanggal -31 s/d 31 (dulu -26): data bulan lalu mencakup
  tgl 25-31 (negatif -25 s/d -31) → kolom tanggal kini LENGKAP urut
  kronologis 25•,26•,27•,28•,29•,30•,31• lalu 1,2,3,... (dulu -27..-31
  terpotong filter sehingga kolomnya "25,26, lalu 1").

v3.2:
- KPI row di atas tabel DIHAPUS (tabel lebar & besar; ringkasan di footer)
- Lazy refresh: compute hanya saat tab terlihat (app → ensure_refreshed)
- Ekstraksi per-item via satu .loc (bukan item×metric) — lebih cepat

v3.1 (dipertahankan): filter corong di header, ⛶ perbesar, loading overlay,
compute/render async.

AUDIT 2c (fix 3-c):
- 2c-01/2c-02: pesan 0-baris pipeline menunjuk tab yang BENAR
  ('⚙️ Config' — dulu '⚙ Pengaturan' yang tak ada) DAN naik ke
  SUBTITLE EmptyState (status footer hidup di dalam content yang
  tersembunyi di balik EmptyState → teksnya tak pernah terlihat).
- 2c-04: rentang tanggal terbalik (awal > akhir) kini menukar ISI
  entry + warning 'Rentang dibalik otomatis' (dulu swap senyap —
  entry tetap '20 – 5' padahal filter memakai 5..20).
- 2c-07: tombol tanggal 'Apply' (EN) → 'Terapkan' (parity komparasi).
- 2c-06: hint footer abu 1 baris 'Dobel-klik baris = detail'.
- 2f-11: pesan sukses export memakai fmt_int_id ('1.347' — dulu
  '{n:,}' EN '1,347').
"""

import contextlib  # v3.9.66 — suppress senyap jalur restore filter
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from .theme import (
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
    FrozenNamePane,  # v3.9.71 — freeze kolom nama barang
    GhostButton,
    HeaderFilter,
    LegendRow,
    LoadingOverlay,
    SegmentBar,
    TableExpander,
    apply_cell_tag,
    attach_clone_filters,
    auto_fit_columns,
    col_sel_from_json,  # v3.9.66 — filter persisten antar sesi
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
    validated_tgl_entry,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)

# NB: write_pivot_display_sheet di-import LAZY di _do_export_excel —
# export_sheets mengimpor PivotTableView (METRICS) → import modul-level
# menciptakan circular import.


class PivotTableView(tk.Frame):
    """Pivot matrix view dengan tampilan card-based."""

    # Metric order — fixed (identik versi lama):
    METRICS = [
        "SALDO AWAL", "1.SO", "2.SALDO AKHIR", "3.DEVIASI",
        "4.IN", "5.BARANG MASUK", "6.PEMAKAIAN (COM)",
        "7.Selisih IN", "8.BARANG KELUAR", "9.ACR",
    ]

    # Soft pastel background per metric (identik versi lama)
    METRIC_BG = {
        "SALDO AWAL": "#F5F5F5",
        "1.SO": "#F0F4FA",
        "2.SALDO AKHIR": "#F2F8EE",
        "3.DEVIASI": "#FDF6E3",
        "4.IN": "#FFFBE6",
        "5.BARANG MASUK": "#EEF7EC",
        "6.PEMAKAIAN (COM)": "#E8E0F0",
        "7.Selisih IN": "#FCEEE8",
        "8.BARANG KELUAR": "#FFF0E0",
        "9.ACR": "#F8F0F0",
    }

    def __init__(self, parent, data: pd.DataFrame = None,
                 go_to_proses: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.data: pd.DataFrame | None = None
        self.go_to_proses = go_to_proses
        self.pivot_mode = "resto"          # "resto" | "tanggal"
        self._name_selected: set | None = None
        self._busy = False
        self._pending = False
        self._dirty = False                # lazy refresh (v3.2)
        # v3.9.2: minus merah PER CELL (Tk 9 `tag cell`) — fallback Tk 8:
        # tag per baris (perilaku lama). Probe di main thread, sekali.
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._last_payload: dict = {}      # utk export sesuai tampilan
        self._red_cells: list = []         # [(iid, col)] — dipasang ulang
                                           # setelah insert/sort/clone
        self._build_ui()
        self._setup_tags()
        if data is not None and not data.empty:
            self.load_data(data)
        else:
            self._show_empty()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        # --- Empty state ---
        self.empty = EmptyState(
            self, icon="📊", title="Belum ada data pivot",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=self._cta_proses)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Konten utama (disembunyikan sampai ada data) ---
        self.content = tk.Frame(self, bg=C_BG)

        # (v3.2) KPI row DIHAPUS — tabel lebar & besar; ringkasan
        # (barang × kolom = baris) ada di status footer.

        # --- Filter card ---
        fcard = Card(self.content, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        fbody = fcard.body()

        # Row 0: RESTO (mode tanggal saja) / SOURCE / KATEGORI
        r0 = tk.Frame(fbody, bg=C_CARD)
        r0.pack(fill="x", pady=(0, 6))

        self.f_resto = tk.Frame(r0, bg=C_CARD)
        tk.Label(self.f_resto, text="RESTO", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.resto_var = tk.StringVar(value="(All)")
        self.resto_combo = ttk.Combobox(self.f_resto,
                                        textvariable=self.resto_var,
                                        state="readonly", width=16)
        self.resto_combo.pack(side="left", padx=(6, 0))
        self.resto_combo.bind("<<ComboboxSelected>>",
                              lambda e: self._refresh_pivot())

        self.f_source = tk.Frame(r0, bg=C_CARD)
        tk.Label(self.f_source, text="SOURCE KIRIMAN", bg=C_CARD,
                 fg=C_TEXT_MUTED, font=font(8, "bold")).pack(side="left")
        self.source_var = tk.StringVar(value="(All)")
        self.source_combo = ttk.Combobox(self.f_source,
                                         textvariable=self.source_var,
                                         state="readonly", width=16)
        self.source_combo.pack(side="left", padx=(6, 0))
        self.source_combo.bind("<<ComboboxSelected>>",
                               lambda e: self._refresh_pivot())

        self.f_kategori = tk.Frame(r0, bg=C_CARD)
        tk.Label(self.f_kategori, text="KATEGORI", bg=C_CARD,
                 fg=C_TEXT_MUTED, font=font(8, "bold")).pack(side="left")
        self.kategori_var = tk.StringVar(value="(All)")
        self.kategori_combo = ttk.Combobox(self.f_kategori,
                                           textvariable=self.kategori_var,
                                           # v3.9.50 — width 16→46: label
                                           # gabungan default 49-char
                                           # TERPOTONG (parity deviasi/
                                           # nominal 46 — audit 3-b)
                                           # v3.9.55 — label gabungan
                                           # kini RINGKA → 34.
                                           state="readonly", width=34)
        self.kategori_combo.pack(side="left", padx=(6, 0))
        self.kategori_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self._refresh_pivot())

        # Row 1: TANGGAL range + sembunyikan baris kosong + reset
        r1 = tk.Frame(fbody, bg=C_CARD)
        r1.pack(fill="x")
        tk.Label(r1, text="TANGGAL", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.tgl_start_var = tk.StringVar(value="-31")  # v3.8: 31 BULAN LALU
        t1 = ttk.Entry(r1, textvariable=self.tgl_start_var, width=6)
        t1.pack(side="left", padx=(6, 2))
        t1.bind("<Return>", lambda e: self._refresh_pivot())
        tk.Label(r1, text="–", bg=C_CARD, fg=C_TEXT_MUTED).pack(side="left")
        self.tgl_end_var = tk.StringVar(value="31")  # v3.6: 31 BULAN BERJALAN
        t2 = ttk.Entry(r1, textvariable=self.tgl_end_var, width=6)
        t2.pack(side="left", padx=(2, 6))
        t2.bind("<Return>", lambda e: self._refresh_pivot())
        # 2c-07 (audit 2c) — 'Apply' (EN) → 'Terapkan' (parity tombol
        # '↻ Terapkan' komparasi; app 99% Indonesia).
        GhostButton(r1, text="Terapkan", command=self._refresh_pivot).pack(
            side="left", padx=(0, 18))

        self.hide_empty_var = tk.BooleanVar(value=True)
        # v3.9.69 — P1.1 (audit eksternal ke-2): semantik "kosong" = SEMUA
        # sel baris 0/kosong (dulu "total ≤ 0" — baris cancel-out/retur
        # yang SELURUH selnya negatif ikut tersembunyi padahal menyimpan
        # informasi deviasi penting; total +10/−10 juga tersembunyi).
        self.chk_hide_empty = ttk.Checkbutton(
            r1, text="Sembunyikan baris kosong (semua sel 0)",
            variable=self.hide_empty_var,
            command=self._refresh_pivot)
        self.chk_hide_empty.pack(side="left", padx=(0, 18))

        GhostButton(r1, text="✕ Reset Filter",
                    command=self._reset_filter).pack(side="left")

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        # Header tabel: judul + segment mode + tombol perbesar
        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        title_label = tk.Label(head, text="Matrix Pivot", bg=C_CARD,
                               fg=C_HEADER, font=font(10, "bold"))
        title_label.pack(side="left")
        self.mode_seg = SegmentBar(
            head, ["🏪 Resto", "📅 Tanggal"], bg=C_CARD,
            command=self._on_mode_change)
        self.mode_seg.pack(side="left", padx=(14, 0))
        # v3.9 (ala Waste): ⛶ = Layar Penuh (window terpisah)
        btn_max = GhostButton(head, text="⛶ Layar Penuh",
                              command=self._maximize)
        btn_max.pack(side="right")
        # v3.9 (ala Waste): ⤢ = Perbesar Tabel (in-place)
        btn_expand = GhostButton(head, text="⤢ Perbesar Tabel")
        btn_expand.pack(side="right", padx=(0, 6))
        btn_cols = GhostButton(head, text="◱ Kolom",
                               command=lambda: self._colmgr.open_panel())
        btn_cols.pack(side="right", padx=(0, 6))
        btn_fit = GhostButton(head, text="↔ Auto-Fit", command=self._auto_fit)
        btn_fit.pack(side="right", padx=(0, 6))
        # v3.9.2: 💾 Export Excel — matrix pivot SESUAI TAMPILAN (filter +
        # mode aktif); nilai minus ditandai font merah per cell (mirror UI)
        btn_export = GhostButton(head, text="💾 Export Excel",
                                 command=self._on_export_excel)
        btn_export.pack(side="right", padx=(0, 6))

        self.tree = ttk.Treeview(tbody, show="tree headings", selectmode="extended")

        # v3.9.71 — FREEZE KOLOM NAMA BARANG (user: "di tab pivot tabel gak
        # bsia freeze kolom nama barang ya? sehingga jika aku scroll ke
        # kanan bisa kefreze"): #0 pindah ke TREE BEKU kiri (FrozenNamePane)
        # — tree utama menyembunyikan #0 (width 0 + _autofit_skip) dan
        # hanya menggulir kolom matrix horizontal → nama barang TETAP
        # terlihat saat scroll ke kanan.
        self.frozen = FrozenNamePane(
            self.tree, tbody, heading="Nama Barang",
            setup_tags=lambda t: self._setup_tags(t))
        self.name_tree = self.frozen.tree        # alias publik (test/clone)
        self.tree._frozen_pane = self.frozen     # dibaca clone ⛶ (lebar)
        self.tree._autofit_skip = {"#0"}         # auto-fit jangan buka #0

        vsb = ttk.Scrollbar(tbody, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal", command=self.tree.xview)
        # v3.9.71 — yscrollcommand chain: scrollbar + tree beku mengikuti
        self._tree_vsb = vsb
        self.tree.configure(yscrollcommand=self._on_tree_yscroll,
                            xscrollcommand=hsb.set)

        self.frozen.pane.grid(row=1, column=0, sticky="ns")
        self.tree.grid(row=1, column=1, sticky="nsew")
        vsb.grid(row=1, column=2, sticky="ns")
        hsb.grid(row=2, column=0, columnspan=2, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(1, weight=1)

        # v3.4: drag tepi heading = resize lebar kolom; double-click tepi =
        # auto-fit (dipasang SEBELUM HeaderFilter supaya "break" efektif)
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32
        # v3.9.71 — sisi beku: resize lebar kolom nama + multi-select
        # (Ctrl+A/seleksi tersinkron dua arah oleh pane)
        enable_col_resize(self.name_tree)
        enable_multi_select(self.name_tree)

        # Footer card: status
        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.status_var = tk.StringVar(value="Belum ada data.")
        tk.Label(foot, textvariable=self.status_var, bg=C_CARD, fg=C_HEADER,
                 font=font(8, "bold")).pack(side="right")
        # 2c-06 (audit 2c) — affordance minimal: hint abu 1 baris di
        # footer (double-click = popup detail; view pivot TIDAK punya
        # kolom ✓ follow-up — matriks barang × metric).
        tk.Label(foot, text="Dobel-klik baris = detail", bg=C_CARD,
                 fg=C_TEXT_MUTED, font=font(8)).pack(side="left")

        # Loading overlay (dibuat setelah tree → stacking di atas)
        self.overlay = LoadingOverlay(tbody, "Menghitung matrix pivot…")

        # Legend metric colors
        legend = LegendRow(
            self.content,
            [("IN", "#9C5700"), ("BARANG MASUK", "#006100"),
             ("Minus / nilai < 0", "#dc2626"), ("Selisih ≠ 0", "#FFC9C9"),
             ("tgl • = bulan lalu", "#94a3b8")])
        legend.pack(fill="x", padx=12, pady=(6, 0))
        self._legend = legend

        # v3.9 (ala Waste): ⤢ Perbesar Tabel — ciutkan kartu Filter + judul
        # + legenda (segment mode & tombol toolbar tetap tampil)
        self._expander = TableExpander(
            btn_expand, [fcard, title_label, legend])

        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04
        # v3.9.71 — sisi beku: double-click baris nama = popup detail juga
        self.name_tree.bind("<Double-1>", self._on_double_click, add="+")

        # Filter "Nama Barang" menempel di header kolom #0
        # v3.9.71 — #0 kini hidup di TREE BEKU (freeze kolom nama barang);
        # funnel + popup + ikon aktif mengikuti pindah ke sana.
        self.header_filter = HeaderFilter(
            self.name_tree, "#0",
            get_values=self._name_values,
            on_apply=self._on_name_filter,
            label="Nama Barang")

        # v3.6: hide/unhide kolom (klik kanan heading / tombol ◱ Kolom)
        # FIX C-05: item menu "⧩ Filter kolom" untuk kolom non-#0 tidak lagi
        # mati senyap — diarahkan ke filter Nama Barang + status menjelaskan.
        self._colmgr = ColumnManager(
            self.tree,
            open_filter=self._open_col_filter)

        self._apply_mode_ui()

    def _on_tree_yscroll(self, first, last):
        """v3.9.71 — chain yscrollcommand tree utama: scrollbar tetap
        ter-update + TREE BEKU mengikuti posisi gulir (guard anti-loop
        di FrozenNamePane.follow_right — roda mouse di sisi nama jalan
        lewat chain balik pane._on_left_scroll)."""
        self._tree_vsb.set(first, last)
        self.frozen.follow_right(first, last)

    def _open_col_filter(self, col: str):
        """Filter teks di view Pivot tersedia untuk kolom nama (#0); kolom
        matrix (resto/tanggal) difilter lewat kontrol RESTO/TANGGAL di atas
        tabel. Sebelumnya: klik menu di kolom lain TIDAK melakukan apa-apa."""
        if col != "#0":
            self.status_var.set(
                "ℹ Kolom matrix difilter lewat RESTO / TANGGAL di atas tabel "
                "— filter teks hanya untuk kolom 'Nama Barang'.")
        return self.header_filter.open_popup()

    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten.
        v3.9.71 — dua sisi freeze-pane: kolom matrix di tree utama
        (#0 di-skip via _autofit_skip supaya tetap tersembunyi) +
        kolom nama di tree beku."""
        auto_fit_columns(self.tree)
        auto_fit_columns(self.frozen.tree, columns=["#0"])

    def _name_values(self) -> list:
        """Nilai popup filter Nama Barang.

        v3.9.19 (penuntasan "berlaku untuk semua filter"): sumber nilai =
        barang yang TAMPIL SAAT INI (perilaku AutoFilter Excel — filter
        kolom lain diterapkan dulu, kolom sendiri dikecualikan): RESTO
        (mode Tanggal saja) + SOURCE + KATEGORI + rentang Tanggal + ☑
        "Sembunyikan baris kosong" (barang tanpa metric ber-sel ≠ 0
        memang tak ditampilkan — semantik v3.9.69: kosong = SEMUA sel
        0/kosong). Dulu: semua nama di data mentah — nama barang yang
        barisnya sudah terfilter tetap muncul di popup.
        Vektor (tanpa pivot tree) — murah, dipanggil saat popup dibuka."""
        df = self.data
        if df is None or df.empty or "Nama Barang" not in df.columns:
            return []
        resto = self.resto_var.get()
        if self.pivot_mode == "tanggal" and resto and resto != "(All)" \
                and "NAMA RESTO" in df.columns:
            df = df[df["NAMA RESTO"].astype(str) == resto]
        source = self.source_var.get()
        if source and source != "(All)" and "SOURCE KIRIMAN" in df.columns:
            df = df[df["SOURCE KIRIMAN"].astype(str) == source]
        kategori = self.kategori_var.get()
        if kategori and kategori != "(All)" and "KATEGORI" in df.columns:
            # v3.9.44 — passthrough barang TANPA kategori master (NaN/
            # blank — contoh BUMBU PASTA KUAH 100383 saldo-only 42.17
            # yang tak ada di '21. DBS Kategori' user): master tak kenal
            # ≠ disembunyikan — konsisten deviasi_view/nominal_resto.
            # v3.9.45 — passthrough HANYA seleksi default 'Deviasi'
            # (kelas 100383 tetap tampil by default); seleksi eksplisit
            # lain STRICT (fix "ganti kategori tidak terjadi apa apa" —
            # passthrough universal v3.9.44 + mayoritas baris '-'
            # membuat filter no-op); KATEGORI_BLANK_LABEL = khusus
            # baris tanpa kategori master.
            if kategori == KATEGORI_BLANK_LABEL:
                df = df[kategori_blank_mask(df["KATEGORI"])]
            elif kategori_filter_mask(df["KATEGORI"], kategori) is not None:
                # v3.9.49 — entri GABUNGAN default (kategori Rekap
                # Mentah). v3.9.53 — kini STRICT (hanya nilai gabungan;
                # passthrough blank DIHAPUS — user: "kok ada nama barang
                # yang bukan kategori COM Deviasi + Packaging Deviasi
                # ..."; kelas 100383 = kategori rekap v3.9.49 + entry
                # '(Tanpa Kategori)' tetap terjangkau).
                df = df[kategori_filter_mask(df["KATEGORI"], kategori)]
            elif kategori_passthrough(kategori):
                _blank = kategori_blank_mask(df["KATEGORI"])
                df = df[(df["KATEGORI"].astype(str) == kategori)
                        | _blank]
            else:
                df = df[df["KATEGORI"].astype(str) == kategori]
        # rentang tanggal berlaku untuk kedua mode (identik _compute_payload;
        # parse longgar tanpa dialog — pola in_selisih _col_values)
        if "Tanggal" in df.columns and not df.empty:
            try:
                t1 = int(float(self.tgl_start_var.get()))
                t2 = int(float(self.tgl_end_var.get()))
            except (TypeError, ValueError):
                t1 = t2 = None
            if t1 is not None and t2 is not None:
                if t1 > t2:
                    t1, t2 = t2, t1
                tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
                df = df[tnum.between(t1, t2)]
        if df.empty:
            return []
        if self.hide_empty_var.get() and {"JENIS", "NILAI"} <= set(df.columns):
            # barang tampil = punya ≥1 SEL MATRIKS ≠ 0 — PERSIS aturan
            # hide-empty di _compute_payload (semantik v3.9.69: baris
            # "kosong" = SEMUA sel 0/kosong; dulu total per (barang ×
            # JENIS) → baris cancel-out (−5,−2,−3) tak konsisten
            # tersembunyikan). Sel matriks = agregat per KOLOM PIVOT:
            # mode resto → (barang × JENIS × resto), mode tanggal →
            # (barang × JENIS × tanggal) — agregasi di granularity
            # PERSIS sel yang dirender supaya popup tak pernah menawarkan
            # barang yang barisnya pasti tersembunyi (mis. +10/−10
            # resto-sama → sel agregat 0 → baris TERSEMBUNYI → tak
            # ditawarkan; +10/−10 resto-BEDA → sel ≠ 0 → tampil).
            metrics = [m for m in self.METRICS
                       if m != "6.PEMAKAIAN (COM)"
                       or self.pivot_mode == "tanggal"]
            f = df[df["Nama Barang"].notna()]
            f = f[f["JENIS"].astype(str).isin(metrics)]
            if f.empty:
                return []
            vals = pd.to_numeric(f["NILAI"], errors="coerce").fillna(0)
            _grp_cols = [f["Nama Barang"].astype(str),
                         f["JENIS"].astype(str)]
            _key_col = ("NAMA RESTO" if self.pivot_mode == "resto"
                        else "Tanggal")
            if _key_col in f.columns:
                _grp_cols.append(f[_key_col].astype(str))
            grp = vals.groupby(_grp_cols).sum()
            nz = grp[grp != 0]
            if nz.empty:
                return []
            return sorted({ix[0] for ix in nz.index})
        return df["Nama Barang"].dropna().astype(str).unique().tolist()

    def _on_name_filter(self, selected):
        self._name_selected = selected
        self._refresh_pivot()

    def _on_mode_change(self, idx: int):
        self.pivot_mode = "resto" if idx == 0 else "tanggal"
        self._apply_mode_ui()
        self._refresh_pivot()

    def _apply_mode_ui(self):
        """RESTO filter hanya relevan di mode Tanggal (resto = kolom di mode Resto)."""
        for f in (self.f_resto, self.f_source, self.f_kategori):
            f.pack_forget()
        if self.pivot_mode == "tanggal":
            self.f_resto.pack(side="left", padx=(0, 18))
        self.f_source.pack(side="left", padx=(0, 18))
        self.f_kategori.pack(side="left", padx=(0, 18))

    def _cta_proses(self):
        if self.go_to_proses:
            self.go_to_proses()

    def _show_empty(self):
        self.content.pack_forget()
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

    def _set_empty_subtitle(self, subtitle: str):
        """2c-02 (audit 2c) — panduan diagnostik 0-baris naik ke SUBTITLE
        EmptyState (parameternya sudah tersedia, belum dipakai). Status
        label tetap diset, tapi footer hidup DI DALAM self.content yang
        disembunyikan EmptyState → tanpa subtitle, teks panduan TIDAK
        PERNAH terlihat user. Widget dibangun ulang hanya bila teks
        berubah (murah; paling banyak sekali per run pipeline)."""
        if getattr(self, "_empty_subtitle", None) == subtitle:
            return
        self._empty_subtitle = subtitle
        try:
            self.empty.destroy()
        except tk.TclError:
            pass
        self.empty = EmptyState(
            self, icon="📊", title="Belum ada data pivot",
            subtitle=subtitle,
            cta_text="🚀 Jalankan Pipeline",
            on_cta=self._cta_proses)

    def _show_content(self):
        self.empty.pack_forget()
        self.content.pack(fill="both", expand=True)

    def _setup_tags(self, tree=None):
        """Tag Treeview: warna metric + conditional formatting (identik lama).

        v3.9.2: 'neg_cell' = tag PER-CELL (minus merah, Tk 9 `tag cell`) —
        baris TIDAK lagi memerah satu baris penuh; 'selisih_anomaly_bg'
        = variasi bg-only utk baris Selisih ≠ 0 (font merah per-cell).
        """
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        for metric, color in self.METRIC_BG.items():
            tree.tag_configure(self._metric_tag(metric), background=color)

        tree.tag_configure(
            "item_header", font=font(9, "bold"), background="#e2e8f0",
            foreground=C_HEADER)
        tree.tag_configure("deviasi_row", foreground="#dc2626")
        tree.tag_configure("selisih_anomaly", foreground="#dc2626",
                           background="#FFC9C9")
        # v3.9.2 — bg saja (tanpa fg merah): font merah dipasang PER CELL
        tree.tag_configure("selisih_anomaly_bg", background="#FFC9C9")
        # v3.9.19: merah gelap #dc2626 (C_RED) — konsisten 10 view lain
        # (dulu #CC0000, satu-satunya yang beda — audit 34-e NIT-4)
        tree.tag_configure("neg_cell", foreground="#dc2626")
        tree.tag_configure("in_row", foreground="#9C5700",
                           background="#FFEB9C")
        tree.tag_configure("bm_row", foreground="#006100",
                           background="#C6EFCE")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("zero_value", foreground="#999999")

    # =========================================================================
    # DATA LOADING
    # =========================================================================
    def load_data(self, data: pd.DataFrame):
        self.data = data
        # v3.9.55 — F8: data baru → auto-fit SEKALI lagi saat render pertama
        reset_autofit_once(self)
        # v3.9.71 — freeze-pane: flag auto-fit sisi beku ikut di-reset
        self._autofit_once_frozen = False
        # v3.9: pulihkan layout bila sedang di-perbesar ⤢
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        # v3.9.33 — AUDIT FIX (48-f HIGH sebagian): 0 baris pasca-pipeline
        # → EMPTY STATE + status berpenjelasan aksi (dulu _show_content()
        # TANPA SYARAT → tabel kosong senyap di belakang pipeline
        # "SELESAI" hijau — user tak tahu harus cek folder data/RootPath).
        if data is None or getattr(data, "empty", True):
            # 2c-02 (audit 2c) — subtitle EmptyState membawa panduan
            # RootPath ke tempat TERLIHAT (status footer tersembunyi di
            # balik EmptyState); 2c-01 — nama tab dibetulkan '⚙️ Config'.
            self._set_empty_subtitle(
                "0 baris terbaca dari pipeline — cek folder data / "
                "RootPath di tab ⚙️ Config")
            self._show_empty()
            self._name_selected = None
            self.header_filter.clear()
            # v3.9.33 — AUDIT FIX (48-d MEDIUM, lanjutan _populate_filters):
            # data kosong = kolom "hilang" → seleksi combo di-reset (dulu
            # nilai lama terpasang senyap di tabel kosong).
            for var in (self.resto_var, self.source_var, self.kategori_var):
                var.set("(All)")
            self.status_var.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")
            return
        self._show_content()
        self._populate_filters()
        self._name_selected = None
        self.header_filter.clear()
        # (v3.2) lazy refresh — compute hanya bila tab terlihat
        if self.winfo_ismapped():
            self._refresh_pivot()
        else:
            self._dirty = True

    def ensure_refreshed(self):
        """Lazy refresh (v3.2): compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None and not self.data.empty:
            self._dirty = False
            self._refresh_pivot()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    # Snapshot / pulihkan kombinasi filter Matrix Pivot (mode PIVOT PER,
    # RESTO/SOURCE/KATEGORI, rentang TANGGAL, checkbox baris kosong,
    # seleksi ⧩ Nama Barang #0) — pola deviasi_view (lihat catatan sana).
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.pivot')."""
        st = {
            "mode": self.pivot_mode,
            "resto": self.resto_var.get(),
            "source": self.source_var.get(),
            "kategori": self.kategori_var.get(),
            "tgl_start": self.tgl_start_var.get(),
            "tgl_end": self.tgl_end_var.get(),
            "hide_empty": bool(self.hide_empty_var.get()),
        }
        _name = col_sel_to_json({"#0": self._name_selected})
        if "#0" in _name:
            st["name_sel"] = _name["#0"]
        return st

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.

        Combobox divalidasi terhadap values data BARU (pola preserve
        v3.9.42 — nilai hilang → "(All)" default tetap); mode lewat
        jalur segment yang sama dgn klik user (set_active_silent +
        _apply_mode_ui — tanpa refresh tambahan; refresh SEKALI di
        akhir bila ada perubahan)."""
        if not isinstance(state, dict):
            return
        if self.data is None or bool(getattr(self.data, "empty", True)):
            return
        changed = False
        _m = state.get("mode")
        if (_m in ("resto", "tanggal") and _m != self.pivot_mode):
            self.pivot_mode = _m
            with contextlib.suppress(Exception):
                self.mode_seg.set_active_silent(
                    0 if _m == "resto" else 1)
            self._apply_mode_ui()
            changed = True
        for key, var, combo in (
                ("resto", self.resto_var, self.resto_combo),
                ("source", self.source_var, self.source_combo),
                ("kategori", self.kategori_var, self.kategori_combo)):
            v = state.get(key)
            if not isinstance(v, str):
                continue
            try:
                vals = list(combo["values"])
            except tk.TclError:
                vals = []
            if v in vals and var.get() != v:
                var.set(v)
                changed = True
        for key, var in (("tgl_start", self.tgl_start_var),
                         ("tgl_end", self.tgl_end_var)):
            v = state.get(key)
            if (isinstance(v, str) and v
                    and var.get() != v):
                var.set(v)
                changed = True
        v = state.get("hide_empty")
        if isinstance(v, bool) and v != bool(self.hide_empty_var.get()):
            self.hide_empty_var.set(v)
            changed = True
        _ns = col_sel_from_json({"#0": state.get("name_sel")}, ("#0",))
        if "#0" in _ns:
            self._name_selected = _ns["#0"]
            with contextlib.suppress(Exception):
                self.header_filter.set_selected(self._name_selected)
            changed = True
        if changed and self.winfo_ismapped():
            self._refresh_pivot()

    def _populate_filters(self):
        if self.data is None or self.data.empty:
            return
        for col, combo, var in [
            ("NAMA RESTO", self.resto_combo, self.resto_var),
            ("SOURCE KIRIMAN", self.source_combo, self.source_var),
            ("KATEGORI", self.kategori_combo, self.kategori_var),
        ]:
            # v3.9.33 — AUDIT FIX (48-d MEDIUM): reload data dengan schema /
            # himpunan nilai berbeda TIDAK lagi meninggalkan seleksi lama
            # terpasang senyap (nilai tak ada di data baru → filter 0
            # baris senyap): seleksi di-reset ke "(All)" bila tak valid;
            # kolom hilang → daftar nilai dikosongkan + reset.
            if col in self.data.columns:
                values = ["(All)"] + sorted(
                    self.data[col].dropna().astype(str).unique().tolist())
                combo["values"] = values
                if var.get() not in values:
                    var.set("(All)")
            else:
                combo["values"] = []
                var.set("(All)")
        # v3.9.45 — entry '(Tanpa Kategori)' saat ADA baris tanpa master
        # (akses eksplisit kelas 100383 — pola deviasi_view v3.9.45;
        # disisipkan setelah '(All)').
        # v3.9.46 — entry SELALU ADA (mirror deviasi_view: master yang
        # makin lengkap membuat entry kondisional hilang senyap — user:
        # "kategori tanpa kategori kok kosong" — mencari opsi itu & tak
        # menemukannya di dropdown).
        # v3.9.49 — entry GABUNGAN default (kategori Rekap Mentah) setelah
        # '(All)' hanya bila data memuat salah satu nilai rekap (pola
        # deviasi_view; tanpa itu entry akan memfilter 0 baris di data
        # lama tanpa kategori rekap).
        if "KATEGORI" in self.data.columns:
            # v3.9.49 — susun ulang: '(All)' → entry gabungan default
            # (bila data ber-kategori rekap) → '(Tanpa Kategori)' →
            # nilai data terurut. Deterministik (idempoten — entri
            # virtual di-strip dulu lalu disisipkan ulang).
            _kv45 = [v for v in (self.kategori_combo["values"] or [])
                     if v not in ("(All)", KATEGORI_DEFAULT_LABEL,
                                  KATEGORI_BLANK_LABEL)]
            _head = ["(All)"]
            if kategori_has_default_values(self.data["KATEGORI"]):
                _head.append(KATEGORI_DEFAULT_LABEL)
            _head.append(KATEGORI_BLANK_LABEL)
            self.kategori_combo["values"] = _head + _kv45
        # v3.9.36 — DEFAULT KATEGORI = "Deviasi" (user: "di tab pivot
        # tabel default kategori Deviasi"; pola deviasi_view v3.9.19 —
        # case-insensitive, fallback "(All)" bila tak ada di data).
        # v3.9.49 — DEFAULT BARU: entry gabungan kategori Rekap Mentah
        # bila ada di data; fallback legacy 'Deviasi' → '(All)'.
        # Reset tiap load_data (pola _reset_kategori deviasi_view).
        self._reset_kategori()

    # v3.9.36 — default kategori 'Deviasi' (pola deviasi_view v3.9.19).
    # v3.9.49 — default BARU: entry gabungan kategori Rekap Mentah bila
    # ada di data; fallback legacy 'Deviasi' → '(All)'.
    def _default_kategori_value(self) -> str:
        values = list(self.kategori_combo["values"] or [])
        if KATEGORI_DEFAULT_LABEL in values:
            return KATEGORI_DEFAULT_LABEL
        for v in values:
            if str(v).strip().lower() == "deviasi":
                return str(v)
        return "(All)"

    def _reset_kategori(self):
        val = self._default_kategori_value()
        self.kategori_var.set(val)

    # =========================================================================
    # FILTER STATE + COMPUTE (pure — berjalan di thread)
    # =========================================================================
    def _filter_state(self) -> dict:
        # FIX B-02: validasi input konsisten (warning + revert) — sebelumnya
        # input invalid difallback SENYAP ke 1/31 tanpa memberi tahu user.
        # v3.9.33 — AUDIT FIX (48-d LOW): fallback TANGGAL AWAL kini -31
        # (batas kiri default v3.8) — dulu fallback 1 MEMPERSEMPIT rentang
        # secara senyap setelah satu kali input invalid.
        t1 = validated_tgl_entry(self.tgl_start_var, lo=-31, hi=31,
                                 fallback=-31, label="Tanggal awal",
                                 parent=self)
        t2 = validated_tgl_entry(self.tgl_end_var, lo=-31, hi=31,
                                 fallback=31, label="Tanggal akhir",
                                 parent=self)
        if t1 > t2:
            # 2c-04 (audit 2c) — rentang terbalik: selain menukar nilai
            # filter, ISI kedua entry ikut ditukar + warning (pola
            # validated_tgl_entry: invalid = warn + revert; dulu swap
            # SENYAP — entry tetap '20 – 5' padahal filter memakai 5..20,
            # membingungkan saat debugging filter).
            t1, t2 = t2, t1
            messagebox.showwarning(
                "Rentang dibalik otomatis",
                "Rentang dibalik otomatis (awal > akhir) — tanggal "
                f"yang dipakai: {t1} – {t2}.",
                parent=self.winfo_toplevel())
            self.tgl_start_var.set(str(t1))
            self.tgl_end_var.set(str(t2))
        return {
            "name_selected": self._name_selected,
            "resto": self.resto_var.get(),
            "source": self.source_var.get(),
            "kategori": self.kategori_var.get(),
            "tgl_start": t1,
            "tgl_end": t2,
            "mode": self.pivot_mode,
            "hide_empty": bool(self.hide_empty_var.get()),
        }

    def _compute_payload(self, st: dict) -> dict:
        """Compute pivot + siapkan baris tree (pure pandas, thread-safe).

        v3.9.2: payload juga membawa:
        - red_cells : [(iid, col)] — cell minus (< 0) + Selisih IN ≠ 0 →
          dipasang tag PER-CELL 'neg_cell' di main thread setelah insert
          (minus merah per CELL, bukan per baris — permintaan user).
        - rows_data : [(iid, label, is_item, metric, vals-float)] — data
          mentah utk tombol 💾 Export Excel sesuai tampilan.
        - filters  : snapshot filter aktif (resto/source/kategori/tgl/mode).
        """
        empty = {"columns": [], "col_kind": st["mode"], "items": [],
                 "kpi": (0, 0, 0), "status": "Belum ada data.",
                 "filtered_rows": 0, "red_cells": [], "rows_data": [],
                 "filters": dict(st)}
        df = self.data
        if df is None or df.empty:
            return empty

        # v3.9.13: seleksi kosong (set()) = 0 baris (semantik Excel) —
        # dulu truthiness menelan set() sebagai "tanpa filter".
        if st["name_selected"] is not None and "Nama Barang" in df.columns:
            df = df[df["Nama Barang"].astype(str).isin(st["name_selected"])]
        if st["resto"] and st["resto"] != "(All)" and \
                "NAMA RESTO" in df.columns and st["mode"] == "tanggal":
            df = df[df["NAMA RESTO"].astype(str) == st["resto"]]
        if st["source"] and st["source"] != "(All)" and \
                "SOURCE KIRIMAN" in df.columns:
            df = df[df["SOURCE KIRIMAN"].astype(str) == st["source"]]
        if st["kategori"] and st["kategori"] != "(All)" and \
                "KATEGORI" in df.columns:
            # v3.9.44 — passthrough barang tanpa kategori master (mirror
            # titik _col_values di atas — kategori_blank_mask).
            # v3.9.45 — passthrough HANYA seleksi default 'Deviasi';
            # seleksi eksplisit lain STRICT; KATEGORI_BLANK_LABEL
            # khusus baris tanpa kategori master (mirror _col_values).
            if st["kategori"] == KATEGORI_BLANK_LABEL:
                df = df[kategori_blank_mask(df["KATEGORI"])]
            elif kategori_filter_mask(df["KATEGORI"],
                                      st["kategori"]) is not None:
                # v3.9.49 — entri GABUNGAN default (kategori Rekap
                # Mentah). v3.9.53 — kini STRICT (hanya nilai gabungan;
                # passthrough blank DIHAPUS — mirror titik _col_values
                # di atas; kelas tanpa kategori = entry
                # '(Tanpa Kategori)').
                df = df[kategori_filter_mask(
                    df["KATEGORI"], st["kategori"])]
            elif kategori_passthrough(st["kategori"]):
                _blank = kategori_blank_mask(df["KATEGORI"])
                df = df[(df["KATEGORI"].astype(str) == st["kategori"])
                        | _blank]
            else:
                df = df[df["KATEGORI"].astype(str) == st["kategori"]]

        # FIX 6c-01 — snapshot df PRA-filter-rentang (kartu name/resto/
        # source/kategori tetap berlaku): matrix COM dihitung dari tanggal
        # PENUH lalu di-slice ke rentang tampilan — mirror
        # laporan_deviasi_view._compute_com_matrix (so.shift(1) atas matrix
        # penuh). Tanpa ini SO(t−1)/SA di luar rentang hilang → base kolom
        # PERTAMA rentang = 0 → COM minus palsu (mis. rentang 4..6 → COM(4)
        # '(5)' padahal oracle '5') + total COM salah → baris COM bisa
        # lenyap senyap di ☑ hide-empty.
        df_predate = df
        # rentang tanggal berlaku untuk kedua mode
        if "Tanggal" in df.columns and not df.empty:
            tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
            df = df[tnum.between(st["tgl_start"], st["tgl_end"])]

        if df.empty:
            out = dict(empty)
            # v3.9.68 — TRI-STATE (audit eksternal T1): seleksi #0
            # KOSONG = filter aktif 0 baris — pesan jujur + cara keluar
            # (bukan pesan generik "Tidak ada data setelah filter.").
            out["status"] = (zero_row_filter_message(
                {"Nama Barang": st.get("name_selected")})
                or "Tidak ada data setelah filter.")
            return out

        mode = st["mode"]
        hide_empty = st["hide_empty"]

        try:
            if mode == "resto":
                pivot = df.pivot_table(
                    index=["Nama Barang", "JENIS"],
                    columns="NAMA RESTO",
                    values="NILAI",
                    aggfunc="sum",
                    fill_value=0,
                )
            else:
                pivot = df.pivot_table(
                    index=["Nama Barang", "JENIS"],
                    columns="Tanggal",
                    values="NILAI",
                    aggfunc="sum",
                    fill_value=0,
                )
        except Exception as e:
            out = dict(empty)
            out["status"] = f"Error pivot: {e}"
            return out

        if pivot.empty:
            out = dict(empty)
            out["status"] = "Tidak ada data setelah pivot."
            out["filtered_rows"] = len(df)
            return out

        # v3.6: urut KRONOLOGIS — hari negatif (bulan lalu) diurut -25 → -31
        # lalu 1..31 (ascending naif meletakkan -31 sebelum -25 = terbalik;
        # juga membuat 6.PEMAKAIAN (COM) salah ambil SO hari-sebelumnya)
        def _chrono(v):
            try:
                iv = int(v)
                return (0, -iv) if iv < 0 else (1, iv)
            except (TypeError, ValueError):
                return (2, str(v))

        col_keys = sorted(pivot.columns.tolist(), key=_chrono)
        columns = [str(c) for c in col_keys]
        items = sorted(pivot.index.get_level_values("Nama Barang")
                       .unique().tolist())

        metrics = list(self.METRICS)
        if mode == "resto":
            # COM adalah metric harian (urutan tanggal) — hanya relevan
            # di mode Tanggal
            metrics = [m for m in metrics if m != "6.PEMAKAIAN (COM)"]

        # FIX 6c-01 — matrix COM PENUH (hanya bila rentang memotong sisi
        # KIRI data: tgl_start > tanggal minimum — rentang penuh dari
        # batas kiri tak memotong konteks SO(t−1)/SA). Pivot atas df
        # PRA-filter-rentang (semua JENIS, superset kolom rentang) →
        # _compute_com per item atas full_keys (rantai so_prev + SA(1)
        # persis laporan) → baris display memakai slice col_keys.
        com_full = None
        if mode == "tanggal" and "Tanggal" in getattr(
                df_predate, "columns", []) and not df_predate.empty:
            _tall = pd.to_numeric(df_predate["Tanggal"], errors="coerce")
            _tmin = _tall.min()
            if pd.notna(_tmin) and st["tgl_start"] > float(_tmin):
                try:
                    pivot_full = df_predate.pivot_table(
                        index=["Nama Barang", "JENIS"],
                        columns="Tanggal",
                        values="NILAI",
                        aggfunc="sum",
                        fill_value=0,
                    )
                    if not pivot_full.empty:
                        full_keys = sorted(pivot_full.columns.tolist(),
                                           key=_chrono)
                        com_full = {
                            item: self._compute_com(
                                pivot_full, item, full_keys)
                            for item in pivot_full.index.get_level_values(
                                "Nama Barang").unique().tolist()
                        }
                except (TypeError, ValueError):
                    com_full = None   # fallback: jalur lama (pivot rentang)

        tree_items = []
        rows_data = []          # v3.9.2 — data mentah utk export
        red_cells = []          # v3.9.2 — cell minus (per-cell merah)
        n_rows = 0
        n_items_shown = 0
        empty_series = pd.Series({c: 0 for c in col_keys})
        for item in items:
            item_iid = f"item_{n_items_shown}"
            child_rows = []
            # v3.2: SATU .loc per item (DataFrame metric×kolom) — bukan
            # satu .loc per (item × metric) — 10× lebih sedikit lookup
            try:
                item_grp = pivot.loc[item]
            except KeyError:
                item_grp = None
            for metric in metrics:
                if mode == "tanggal" and metric == "6.PEMAKAIAN (COM)":
                    # FIX 6c-01 — COM dari matrix PENUH di-slice ke rentang
                    # tampilan (SO(t−1)/SA di luar rentang tetap dipakai;
                    # col_keys ⊆ full_keys karena pivot rentang = subset
                    # tanggal df_predate). Fallback jalur lama bila matrix
                    # penuh tak tersedia.
                    if com_full is not None and item in com_full:
                        row_data = com_full[item].reindex(col_keys) \
                            .fillna(0.0)
                    else:
                        row_data = self._compute_com(pivot, item, col_keys)
                elif item_grp is not None:
                    try:
                        row_data = item_grp.loc[metric]
                    except KeyError:
                        row_data = empty_series
                else:
                    row_data = empty_series

                # v3.9.69 — P1.1 (audit eksternal ke-2): semantik
                # "kosong" = SEMUA sel baris 0/kosong — BUKAN "total ≤ 0"
                # (dulu baris cancel-out (−5,−2,−3) & total +10/−10 ikut
                # tersembunyikan padahal deviasi negatif justru sinyal
                # penting; audit: "perilaku terbukti + tes bisa lulus
                # walau perilaku bisnis diragukan" — kini baris tampil
                # bila ada SATU sel bernilai ≠ 0, termasuk negatif).
                try:
                    vals = pd.to_numeric(row_data, errors="coerce")\
                        .fillna(0)
                    if hide_empty and not bool(vals.ne(0).any()):
                        continue  # baris SEMUA sel nol/kosong → sembunyikan
                except Exception:
                    if hide_empty:
                        continue  # baris tak terbaca angka → kosongkan

                tags = self._compute_row_tags(metric, item, row_data,
                                              col_keys)
                values = [self._format_num(row_data.get(c, 0))
                          for c in col_keys]
                iid = f"{item_iid}_{self._metric_tag(metric)}"
                child_rows.append((
                    item_iid, iid,
                    {"text": metric, "values": values, "tags": tags,
                     "open": False}))

                # v3.9.2 — nilai mentah utk export + cell minus per-cell
                raw_vals = []
                for c in col_keys:
                    v = row_data.get(c, 0)
                    try:
                        v = float(v)
                        if pd.isna(v):
                            v = 0.0
                    except (TypeError, ValueError):
                        v = 0.0
                    raw_vals.append(v)
                    if self._cell_tags and (
                            v < 0 or (metric == "7.Selisih IN" and v != 0)):
                        red_cells.append((iid, str(c)))
                rows_data.append((iid, metric, False, metric, raw_vals))

            if not child_rows:
                continue  # item tanpa metric bernilai → sembunyikan parent

            tree_items.append(("", item_iid,
                               {"text": item,
                                "values": ["" for _ in columns],
                                "tags": ("item_header",), "open": True}))
            rows_data.append((item_iid, item, True, None, None))
            tree_items.extend(child_rows)
            n_items_shown += 1
            n_rows += 1 + len(child_rows)

        kpi = (n_items_shown, len(columns), n_rows)
        status = (
            f"{n_items_shown} barang × {len(columns)} "
            f"{'resto' if mode == 'resto' else 'tanggal'} = {n_rows} baris · "
            f"terfilter {fmt_int_id(len(df))}/{fmt_int_id(len(self.data))} "
            f"baris")  # FIX C-10: 'rows' EN + koma ribuan EN → ID
        return {"columns": columns, "col_kind": mode, "items": tree_items,
                "kpi": kpi, "status": status, "filtered_rows": len(df),
                "red_cells": red_cells, "rows_data": rows_data,
                "filters": dict(st)}

    # =========================================================================
    # REFRESH (async + render batched)
    # =========================================================================
    def _refresh_pivot(self, sync: bool = False):
        if self.data is None or self.data.empty:
            self.status_var.set("Belum ada data.")
            return
        if self._busy:
            self._pending = True
            return
        st = self._filter_state()
        self._busy = True

        def work():
            return self._compute_payload(st)

        def done(payload):
            self._render_payload(payload)

        # FIX B-01: _busy wajib di-reset saat compute GAGAL — tanpa ini
        # view mati permanen setelah 1x error (refresh berikutnya ditelan
        # senyap oleh guard `if self._busy: return`).
        def on_error(err):
            self._busy = False
            self._pending = False
            self.status_var.set(f"⚠ Gagal menghitung matrix pivot: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menghitung matrix pivot…", on_error=on_error,
                  sync=sync)

    def _render_payload(self, payload: dict):
        cols = payload["columns"]
        # v3.9.2: simpan payload terakhir — dipakai tombol 💾 Export Excel
        # (export = SESUAI TAMPILAN: filter + mode + hide-empty aktif)
        self._last_payload = payload
        self._red_cells = payload.get("red_cells", [])
        self.tree.delete(*self.tree.get_children())
        # reset displaycolumns SEBELUM re-assign columns — Tk memvalidasi
        # displaycolumns lama terhadap daftar kolom baru (mode resto→tanggal
        # ganti nama kolom total → 'Invalid column index' bila tidak direset)
        try:
            self.tree.configure(displaycolumns="#all")
        except tk.TclError:
            pass
        self.tree["columns"] = cols
        width = 90 if payload.get("col_kind") == "resto" else 70
        # v3.9.71 — #0 di tree utama DISEMBUNYIKAN (freeze kolom nama:
        # nama tampil di TREE BEKU; heading tetap diset supaya teks/
        # clone konsisten — tidak terlihat karena width 0).
        self.tree.column("#0", width=0, minwidth=0, stretch=False)
        self.tree.heading("#0", text="Nama Barang")
        # tree beku: kolom nama + funnel (HeaderFilter menempel di sini)
        self.frozen.tree.column("#0", width=280, minwidth=180,
                                stretch=False)
        self.frozen.tree.heading("#0", text="Nama Barang")
        for c in cols:
            self.tree.column(c, width=width, minwidth=50, anchor="e",
                             stretch=True)
            # v3.6: kolom tanggal bulan lalu diberi label '25•' (bukan
            # '-25') — legend '• = bulan lalu'
            try:
                ci = int(float(str(c)))
                htxt = f"{abs(ci)}•" if ci < 0 else str(ci)
            except (TypeError, ValueError):
                htxt = str(c)
            self.tree.heading(c, text=htxt)
        # re-pasang state kolom tersembunyian (reconfigure columns me-reset
        # displaycolumns ke #all)
        self._colmgr.apply()
        # pastikan ikon corong tetap terpasang + state benar
        self.header_filter.refresh_icon()

        # ringkasan (barang × kolom = baris) ada di status footer (v3.2 —
        # KPI row atas tabel dihapus)
        self.status_var.set(payload["status"])

        def render_done():
            # v3.9.2: pasang tag PER-CELL utk cell minus (SETELAH semua item
            # ter-insert — insert baru = tag cell ter-reset). Chunked &
            # fail-safe: bila re-render terjadi di tengah jalan, sisa chunk
            # dibatalkan (render baru memasang ulang).
            # v3.9.42 — audit 61-c P1-2: guard `and self._red_cells`
            # dihapus — list kosong = clear overlay (render baru tanpa
            # sel minus tidak meninggalkan label STALE).
            if self._cell_tags:
                apply_cell_tag(self.tree, "neg_cell", self._red_cells)
            # v3.9.55 — F8: auto-fit kolom SEKALI per muat data
            # v3.9.71 — freeze-pane: auto-fit DUA sisi; sisi matrix di
            # sini (render_done batch kanan), sisi nama di on_done batch
            # kiri (lihat mirror_items di bawah — tabel kecil: batch
            # kanan selesai SINKRON sebelum insert kiri jalan).
            self._autofit_first_load("main")
            self._busy = False
            if self._pending:
                self._pending = False
                self._refresh_pivot()

        insert_tree_items(self.tree, payload["items"], batch=500,
                          on_done=render_done)
        # v3.9.71 — TREE BEKU: isi identik (nama barang + baris metric,
        # tag warna sama; batch sendiri, batch lama otomatis dibatalkan);
        # auto-fit kolom nama di on_done batch KIRI sendiri supaya
        # pengukuran nama betul-betul melihat baris yang sudah masuk.
        self.frozen.mirror_items(
            payload["items"], batch=500,
            on_done=lambda: self._autofit_first_load("frozen"))

    def _autofit_first_load(self, side: str = "main"):
        """v3.9.71 — auto-fit SEKALI per muat data (pola v3.9.55 F8: flag
        di-reset load_data), PER-SISI freeze-pane:
        - side="main": kolom matrix tree utama — dipanggil render_done
          (batch kanan selesai; #0 di-skip via _autofit_skip);
        - side="frozen": kolom #0 nama tree beku — dipanggil on_done
          batch kiri (utk tabel kecil batch kanan selesai SINKRON
          sebelum insert kiri jalan — mengukur di render_done akan
          melihat tree beku MASIH KOSONG)."""
        if side == "main":
            if getattr(self, "_autofit_once", False):
                return
            self._autofit_once = True
            with contextlib.suppress(Exception):
                auto_fit_columns(self.tree)     # #0 tersembunyi di-skip
        else:
            if getattr(self, "_autofit_once_frozen", False):
                return
            self._autofit_once_frozen = True
            with contextlib.suppress(Exception):
                auto_fit_columns(self.frozen.tree, columns=["#0"])

    def _compute_row_tags(self, metric: str, item: str, row_data: pd.Series,
                          tanggals: list) -> tuple:
        """Conditional formatting rules.

        v3.9.2 — PER-CELL (Tk 9): minus dimerahkan PER CELL via tag
        'neg_cell' (dipasang di _render_payload), sehingga baris TIDAK
        lagi memerah satu baris penuh:
        - 'negative' per-baris      → TIDAK dipakai (fallback Tk 8 saja)
        - 'deviasi_row' selalu merah → TIDAK dipakai (bg metric tetap)
        - 'selisih_anomaly' fg+bg   → bg saja ('selisih_anomaly_bg');
          font merah dipasang per-cell pada nilai ≠ 0.
        """
        has_negative = any(
            (row_data.get(t, 0) or 0) < 0 for t in tanggals
        )

        if metric == "4.IN":
            return ("in_row",)
        if metric == "5.BARANG MASUK":
            return ("bm_row",)
        if metric == "7.Selisih IN":
            has_nonzero = any(row_data.get(t, 0) != 0 for t in tanggals)
            if has_nonzero:
                # v3.9.2: bg saja — font merah per-cell (lihat _render)
                if self._cell_tags:
                    return ("selisih_anomaly_bg",)
                return ("selisih_anomaly",)
            return (self._metric_tag(metric),)
        if metric == "3.DEVIASI":
            # v3.9.2: minus per-cell (baris tidak selalu merah lagi)
            if self._cell_tags:
                return (self._metric_tag(metric),)
            return ("deviasi_row",)
        if has_negative:
            if self._cell_tags:
                return (self._metric_tag(metric),)
            return ("negative", self._metric_tag(metric))
        return (self._metric_tag(metric),)

    def _reset_filter(self):
        self.resto_var.set("(All)")
        self.source_var.set("(All)")
        self._reset_kategori()    # v3.9.36 — reset = default 'Deviasi'
        self.tgl_start_var.set("-31")  # v3.8: 31 bulan lalu → 31 berjalan
        self.tgl_end_var.set("31")
        self.hide_empty_var.set(True)
        self._name_selected = None
        self.header_filter.clear()
        self._refresh_pivot()

    # =========================================================================
    # 💾 EXPORT EXCEL (v3.9.2 — sesuai tampilan)
    # =========================================================================
    def _visible_columns(self) -> list:
        """Kolom yang TAMPIL di tree (displaycolumns — utk export)."""
        try:
            dc = self.tree.cget("displaycolumns")
            items = [str(x) for x in dc] if isinstance(dc, (tuple, list)) \
                else str(dc).split()
        except tk.TclError:
            items = []
        if not items or "#all" in items:
            return list(self.tree["columns"])
        # hanya kolom yang masih ada (re-render bisa mengganti kolom)
        have = set(self.tree["columns"])
        return [c for c in items if c in have]

    def _on_export_excel(self):
        """v3.9.2 — Export matrix pivot SESUAI TAMPILAN (permintaan user:
        "pivot tabel nya bisa export excel"): filter + mode + kolom tampil
        ikut serta; nilai minus = font merah per cell (mirror UI)."""
        if not self._last_payload.get("items"):
            # FIX 6c-03 — bedakan dua kasus 0-item: data memang BELUM ADA
            # (belum pipeline) vs data ADA tapi filter aktif (kategori /
            # seleksi nama / rentang) meloloskan 0 baris. Dulu selalu
            # 'Jalankan pipeline dulu' — misleading: pipeline sudah
            # berjalan, akar masalahnya filter.
            if self.data is None or getattr(self.data, "empty", True):
                messagebox.showwarning(
                    "Export", "Belum ada data pivot. Jalankan pipeline dulu.",
                    parent=self.winfo_toplevel())
            else:
                messagebox.showwarning(
                    "Export",
                    "Tidak ada baris pivot yang lolos filter aktif "
                    "(kategori / seleksi nama / rentang tanggal / "
                    "☑ sembunyikan baris kosong). Kendurkan atau reset "
                    "filter dulu.",
                    parent=self.winfo_toplevel())
            return
        mode = "resto" if self.pivot_mode == "resto" else "tanggal"
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M")
        filepath = filedialog.asksaveasfilename(
            title="Simpan Matrix Pivot (sesuai tampilan)",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"pivot_{mode}_{stamp}.xlsx",
            parent=self.winfo_toplevel(),
        )
        if not filepath:
            return
        self._do_export_excel(filepath)

    def _do_export_excel(self, filepath: str):
        """Inti export — dipisah dari _on_export_excel supaya bisa
        dipanggil langsung oleh test tanpa dialog."""
        # lazy import — hindari circular import (export_sheets → pivot_view)
        from .export_sheets import write_pivot_display_sheet
        payload = dict(self._last_payload)      # snapshot (anti re-render)
        visible = self._visible_columns()

        def work():
            return write_pivot_display_sheet(filepath, payload,
                                             visible_cols=visible)

        def done(n):
            if not n:
                messagebox.showwarning(
                    "Export", "Tidak ada baris pivot untuk diekspor.",
                    parent=self.winfo_toplevel())
                return
            st = payload.get("filters") or {}
            mode = "Per Tanggal" if st.get("mode") == "tanggal" \
                else "Per Resto"
            # 2f-11 (audit 2f) — format ribuan Indonesia (fmt_int_id,
            # '1.347') konsisten permukaan lain (dulu '{n:,}' EN '1,347').
            self.status_var.set(f"Export {fmt_int_id(n)} baris pivot "
                                f"({mode}) → {filepath}")
            messagebox.showinfo(
                "Export Berhasil",
                f"Matrix pivot ({mode}, {fmt_int_id(n)} baris data)\n"
                f"di-export ke:\n{filepath}",
                parent=self.winfo_toplevel())

        def on_error(e):
            messagebox.showerror(
                "Export Gagal", f"Tidak bisa export:\n{e}",
                parent=self.winfo_toplevel())

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Mengekspor matrix pivot…",
                  on_error=on_error)

    # =========================================================================
    # ⛶ PERBESAR (fullscreen)
    # =========================================================================
    def _maximize(self):
        mode = "Per Resto" if self.pivot_mode == "resto" else "Per Tanggal"

        def filter_setup(new_tree):
            # funnel #0 (Nama Barang) jalan juga di window besar
            # v3.9.71 — clone memakai FREEZE-PANE: funnel menempel di
            # TREE BEKU clone (tree utama clone menyembunyikan #0), tapi
            # filter BARIS tetap dijalankan di tree utama clone
            # (attach_clone_filters filter_tree — cache snapshot
            # _full_items hidup di sisi kanan); setelah rebuild, sisi
            # beku disalin ulang lalu tag minus dipasang kembali.
            pane = getattr(new_tree, "_frozen_pane", None)
            target = pane.tree if pane is not None else new_tree

            def _after_filter(_t=None):
                if pane is not None:
                    pane.mirror_from_right()
                cells_setup(new_tree)

            attach_clone_filters(
                target, ["#0"],
                get_values=self._name_values,
                on_after_filter=_after_filter,
                filter_tree=new_tree)

        # v3.9.2: clone = insert ulang → tag cell minus ter-reset →
        # pasang ulang di clone (iid identik dengan tabel sumber)
        def cells_setup(new_tree):
            # v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (lihat
            # render_done).
            if self._cell_tags:
                apply_cell_tag(new_tree, "neg_cell", self._red_cells)

        return open_tree_maximized(
            self.tree, f"Pivot Table — {mode}",
            setup_tags=lambda t: self._setup_tags(t),
            on_double_click=self._on_double_click,
            on_filter_setup=filter_setup,
            on_render_done=cells_setup,
            frozen_name=True)   # v3.9.71 — freeze kolom nama di clone ⛶

    # =========================================================================
    # DOUBLE-CLICK → POPUP DETAILS
    # =========================================================================
    def _on_double_click(self, event):
        if self.data is None or self.data.empty:
            return
        tree = event.widget

        row_iid = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)

        if not row_iid:
            return

        parent_iid = tree.parent(row_iid)

        if parent_iid:
            nama_barang = tree.item(parent_iid, "text")
            jenis = tree.item(row_iid, "text")
        else:
            nama_barang = tree.item(row_iid, "text")
            jenis = None

        active_filters = {}
        tanggal = None
        if col_id and col_id != "#0":
            # v3.7 FIX (deep audit): resolve posisi-display → NAMA kolom
            # aktual — dulu memakai index posisi untuk membaca
            # tree["columns"] (urutan LOGIS) → setelah kolom disembunyikan,
            # double-click cell melakukan drill-down ke kolom yang SALAH
            # (resto / tanggal keliru).
            col_name = identify_to_column(tree, col_id)
            if col_name:
                try:
                    if self.pivot_mode == "resto":
                        active_filters["NAMA RESTO"] = str(col_name)
                    else:
                        tanggal = int(float(str(col_name)))
                except (ValueError, TypeError):
                    pass

        # filter kartu tetap diberlaku (RESTO hanya mode Tanggal)
        pairs = ([("NAMA RESTO", self.resto_var),
                  ("SOURCE KIRIMAN", self.source_var),
                  ("KATEGORI", self.kategori_var)]
                 if self.pivot_mode == "tanggal" else
                 [("SOURCE KIRIMAN", self.source_var),
                  ("KATEGORI", self.kategori_var)])
        for col, var in pairs:
            val = var.get()
            if val and val != "(All)":
                active_filters[col] = val

        # v3.9.54 FIX (audit 8-a P1-2) — rentang tanggal TAMPILAN
        # diteruskan ke popup (parity _compute_payload: tnum.between
        # — kedua mode memfilter rentang; parse longgar identik
        # _name_values). Dulu popup mengabaikan rentang → baris tanggal
        # di luar rentang yang difilter tabel tetap muncul di popup.
        tgl_range = None
        try:
            _t1 = int(float(self.tgl_start_var.get()))
            _t2 = int(float(self.tgl_end_var.get()))
            tgl_range = (min(_t1, _t2), max(_t1, _t2))
        except (TypeError, ValueError):
            pass

        from src.ui.details_popup import show_details_popup
        root = self.winfo_toplevel()
        show_details_popup(
            root, self.data,
            nama_barang=nama_barang,
            jenis=jenis,
            tanggal=tanggal,
            filters=active_filters,
            tgl_range=tgl_range,
            # v3.9.32 — popup pivot: sudah ±90% layar; tombol ⛶ Perbesar
            # DIHAPUS (user: "besarkan lagi dan HAPUS tombol perbesar
            # popup pivot")
            show_maximize=False,
        )

    # =========================================================================
    # HELPERS (identik versi lama)
    # =========================================================================
    @staticmethod
    def _metric_tag(metric: str) -> str:
        return metric.lower().replace(" ", "_").replace(".", "_").replace("-", "_")

    @staticmethod
    def _format_num(val) -> str:
        """Format angka: 1 desimal, separator ribuan, negatif dalam kurung."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            val = float(val)
        except (TypeError, ValueError):
            return str(val)
        if val == 0:
            return "-"
        # FIX C-03: format angka gaya Indonesia — 1.234.567 / 1.234,5
        # (sebelumnya koma gaya Inggris: 1,234,567 / 1,234.5).
        if val == int(val):
            s = fmt_int_id(val)
        else:
            s = f"{val:,.1f}".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
        if val < 0:
            return f"({s[1:]})"
        return s

    @staticmethod
    def _compute_com(pivot, item, tanggals):
        """Hitung 6.PEMAKAIAN (COM) per tanggal (port dari M code).

        v3.9.5 FIX (audit 19-a #6 / 19-b #2 — bareng laporan_deviasi_view
        & komparasi_deviasi_view): base com di TANGGAL 1 = SALDO AWAL
        milik item (baris SA ber-Tanggal=1, fn_4217) bila ada; fallback
        SO(t-1) (tanggal negatif bulan lalu), fallback 0. SEMANTIK LAMA:
        i==0 memakai SA kolom pertama GLOBAL — saat data memuat tanggal
        negatif (pipeline FULL), kolom pertama = −25 (SA=0 di situ) → SA
        tidak pernah terpakai & pair tanpa data bulan lalu mendapat
        com(1) ≈ −SO(1) = MINUS PALSU. Formula COM kini tetap identik
        antar ketiga view.
        """
        def get_series(jenis):
            try:
                return pivot.loc[(item, jenis)]
            except KeyError:
                return pd.Series({t: 0 for t in tanggals})

        so = get_series("1.SO")
        bm = get_series("4.IN")
        bk = get_series("8.BARANG KELUAR")
        sa = get_series("SALDO AWAL")

        # v3.9.5: SA pair di Tanggal 1 (None/NaN = tidak ada baris SA)
        sa_t1 = sa.get(1)
        has_sa_t1 = sa_t1 is not None and not pd.isna(sa_t1)
        sa_t1_val = float(sa_t1) if has_sa_t1 else 0.0

        com_values = {}
        for i, t in enumerate(tanggals):
            so_val = float(so.get(t, 0) or 0)
            bm_val = float(bm.get(t, 0) or 0)
            bk_val = float(bk.get(t, 0) or 0)

            try:
                is_t1 = int(float(t)) == 1
            except (TypeError, ValueError):
                is_t1 = False
            if is_t1 and has_sa_t1:
                # tanggal 1 → base SALDO AWAL pair (audit fix)
                base = sa_t1_val
            elif i == 0:
                base = 0.0
            else:
                base = float(so.get(tanggals[i - 1], 0) or 0)
            com_val = base + bm_val - bk_val - so_val
            com_values[t] = com_val

        return pd.Series(com_values)
