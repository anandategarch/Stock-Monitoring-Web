"""
nominal_deviasi_view.py — v3.9.32 MODE '💰 Nominal (H)' tab 📋 Laporan
Deviasi (user: "tab baru 'Nominal' di Laporan Deviasi = Harga ×
kuantitas deviasi, per barang + total").

v3.9.34 — REFACTOR (zero behavior change): logika inti perhitungan
Nominal dipindahkan ke helper BERSAMA src/ui/nominal_common.py
(hitung_nominal_pairs / lookup_harga_pair / fmt_harga_id /
fmt_nominal_cell — port persis; kini juga dipakai mode ⚖ Komparasi
dan tab 🧮 Nominal Deviasi). _compute_nominal = wrapper;
_fmt_harga/_fmt_cell_num = delegasi. Semua perilaku render/filter/TOTAL
pin/busy lifecycle/listener H TIDAK berubah.

v3.9.33 — AUDIT FIX (48-e/48-f): (1) filter ⧩ kolom Harga kini benar
(_col_values memetakan "Harga" → "Harga Tampil" + _result_df tetap
snapshot display, pola laporan v3.9.5 — dulu apply filter Harga =
tabel kosong); (2) jalur render kosong tidak membuang refresh pending;
(3) _busy direset di render_done (bukan di awal done()) — sort saat
insert diantrekan; (4) baris TOTAL dipin di ujung setelah sort;
(5) guard dirty/ismapped pada listener H + _dirty di-clear saat
refresh; (6) load_data 0 baris → footer informatif.

Baris = pasangan (Nama Barang × Nama Resto × Satuan) dgn qty DEVIASI
(= 3.DEVIASI = SO − SALDO AKHIR sistem, baris tanggal H — nilai yang
sama dgn kolom Deviasi tab 📦 Deviasi GR) + HARGA per barang dari file
41.09 'Nilai Persediaan' (folder 09.Harga; harga GLOBAL — file tanpa
dimensi resto; Harga = Nilai Saldo Akhir ÷ Kuantitas Saldo Akhir) →
NOMINAL = Harga × Qty Deviasi. Baris TOTAL di ujung tabel (jumlah
nominal + jumlah qty).

NORMALISASI SATUAN HARGA (analisis data real: 176/187 barang rekap
match satuan 41.09; 5 beda — LPG 12KG KG-vs-TABUNG, MUTIARA BOBA
GR-vs-KG, dll): harga 41.09 per satuan-file → dinormalkan ke SATUAN
REKAP via peta rasio v3.9.31 (dari 42.05+32.24):
    harga_rekap = harga41 × rasio(satuanRekap) / rasio(satuan41.09)
(mis. harga 18,25/GR utk pasangan rekap KG → 18.250/KG). Tanpa
harga/rasio (pasangan tak ada di 41.09 / peta rasio tak men-cover) →
kolom harga tampil berlabel satuan asli + penanda '*', nominal '-' dan
TIDAK ikut baris TOTAL (transparan, bukan angka keliru).

TANGGAL H = state bersama (SharedTanggalH — chip read-only + auto-refresh
dari tab 📦 Deviasi GR, pola Anomali COM). Urutan default |Nominal|
MENURUN (dampak terbesar dulu). Minus merah per-cell; format angka
Indonesia; filter header ⧩ + sort + ⛶ Layar Penuh + ⤢ Perbesar Tabel +
◱ Kolom + ↔ Auto-Fit.
"""
import contextlib
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

import pandas as pd

# v3.9.34 — REFACTOR: logika inti perhitungan Nominal (filter
# 3.DEVIASI@H → group → harga loop → sort |Nominal|) DIPINDAHKAN ke
# helper bersama src/ui/nominal_common.py (dipakai juga mode ⚖ Komparasi,
# tab 📦/🧩 Deviasi & tab 🧮 Nominal Deviasi). View ini kini hanya
# wrapper + render; lookup_rasio tak lagi diimpor di sini (dipakai di
# nominal_common).
from .nominal_common import (
    fmt_harga_id,
    fmt_nominal_cell,
    fmt_rp_cell,
    hitung_nominal_pairs,
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
    Card,
    ColumnManager,
    EmptyState,
    GhostButton,
    HeaderFilterGroup,
    LegendRow,
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
    open_tree_maximized,
    reset_autofit_once,  # v3.9.55 — F8
    run_async,
    sort_tree_by_column,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)


class NominalDeviasiView(tk.Frame):
    """Tab 📋 Laporan Deviasi — mode 3 '💰 Nominal (H)': Harga × Qty
    Deviasi per pasangan + baris TOTAL."""

    COLUMNS = [
        ("Nama Barang", 200, "w"),
        ("Resto", 90, "w"),
        ("Satuan", 60, "w"),
        ("Harga", 100, "e"),          # heading dinamis "Harga (SATUAN)"
        ("Qty Deviasi", 100, "e"),    # heading dinamis "Qty Deviasi (H=25)"
        ("Nominal", 120, "e"),
    ]

    NUMERIC_COLS = ("Harga", "Qty Deviasi", "Nominal")

    def __init__(self, parent, go_to_proses: Callable | None = None,
                 h_state=None):
        super().__init__(parent, bg=C_BG)
        self.data: pd.DataFrame | None = None
        self.go_to_proses = go_to_proses
        self._h_state = h_state
        self.tanggal_h = int(h_state.h) if h_state is not None else 25
        # peta harga {barang: (harga|None, satuan41)} + peta rasio
        # v3.9.31 (konversi satuan harga → satuan rekap)
        self.harga_map: dict = {}
        self.konversi_map: dict | None = None
        self._busy = False
        self._pending = False
        self._dirty = False                # lazy refresh (v3.2)
        self._render_gen = 0
        self._insert_cancel = None
        self._pending_sort = None
        self._result_df = None
        self._col_sel: dict = {c: None for c in
                               [c[0] for c in self.COLUMNS]}
        # v3.9.2 minus merah PER CELL (fallback Tk 8 per baris)
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        self._total_cells: list = []   # sel baris TOTAL (style khusus)

        self._build_ui()
        self._setup_tags()
        self._show_empty()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        self.empty = EmptyState(
            self, icon="💰", title="Belum ada data Nominal (Harga × Deviasi)",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        self.content = tk.Frame(self, bg=C_BG)

        # --- Filter card: chip H bersama (read-only — pola Anomali COM) ---
        fcard = Card(self.content, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        self._fcard = fcard
        fbody = fcard.body()

        r1 = tk.Frame(fbody, bg=C_CARD)
        r1.pack(fill="x")
        # v3.9.33 — AUDIT FIX (48-f MEDIUM UX): chip H read-only diberi
        # petunjuk singkat di mana H bisa diatur (pola kata chip lama
        # dipertahankan supaya assertion 'TANGGAL H' tetap lolos).
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
                    command=self._reset_filter).pack(side="left", padx=(18, 0))

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self._title_label = tk.Label(
            head, text="Nominal Deviasi — Harga 41.09 × Qty Deviasi (kolom H)",
            bg=C_CARD, fg=C_HEADER, font=font(10, "bold"))
        self._title_label.pack(side="left")
        btn_max = GhostButton(head, text="⛶ Layar Penuh",
                              command=self._maximize)
        btn_max.pack(side="right")
        btn_expand = GhostButton(head, text="⤢ Perbesar Tabel")
        btn_expand.pack(side="right", padx=(0, 6))
        btn_cols = GhostButton(head, text="◱ Kolom",
                               command=lambda: self._colmgr.open_panel())
        btn_cols.pack(side="right", padx=(0, 6))
        btn_fit = GhostButton(head, text="↔ Auto-Fit", command=self._auto_fit)
        btn_fit.pack(side="right", padx=(0, 6))

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(tbody, columns=col_ids, show="headings",
                                 selectmode="extended")

        for col_name, width, anchor in self.COLUMNS:
            self.tree.column(col_name, width=width, minwidth=34,
                             anchor=anchor)
            self.tree.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(tbody, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(0, weight=1)

        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        # v3.9.59 — FIX 2f-16: LEGENDA MARKER mode 💰 (pola LegendRow
        # deviasi_view/pivot_view): kolom 'Harga' menampilkan penanda
        # '*' (satuan rekap tak ter-cover peta rasio → harga 41.09
        # ditampilkan as-is, Nominal TIDAK dihitung → '-') dan '-'
        # (barang tak ada/harga kosong di 41.09) — sebelumnya definisi
        # hanya ada di docstring + popup tanpa-harga tab 🧮; user baru
        # harus menebak arti marker di sel.
        legend = LegendRow(self.content, [
            (("* satuan tak terkonversi — harga 41.09 as-is, "
              "nominal tak dihitung"), "#b45309"),
            ("- tanpa harga 41.09 (barang tak ada / harga kosong)",
             "#64748b"),
        ])
        legend.pack(fill="x", padx=12, pady=(6, 0))
        self._legend = legend

        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.status_var_label = tk.StringVar(value="Belum ada data.")
        tk.Label(foot, textvariable=self.status_var_label, bg=C_CARD,
                 fg=C_HEADER, font=font(8, "bold")).pack(side="right")

        self.overlay = LoadingOverlay(tbody, "Menghitung nominal deviasi…")

        self.header_filters = HeaderFilterGroup(
            self.tree, col_ids,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filters.open_popup(c))

        self._expander = TableExpander(
            btn_expand, [fcard, self._title_label, self._legend])

        # chip H bersama + auto-refresh saat H diubah di tab Deviasi GR
        if self._h_state is not None:
            self._h_state.subscribe(self._on_shared_h_changed)
            self.bind("<Destroy>", self._on_view_destroy, add="+")

    def _on_view_destroy(self, event):
        if event.widget is self and self._h_state is not None:
            with contextlib.suppress(Exception):
                self._h_state.unsubscribe(self._on_shared_h_changed)

    def _on_shared_h_changed(self, h):
        """Listener H bersama (dari tab 📦 Deviasi GR).

        v3.9.33 — AUDIT FIX (48-e FIX 5a, pola laporan v3.9.5 audit 19-c
        #3): pane tersembunyi (mode lain aktif / tab lain) TIDAK di-
        compute ulang — cukup tandai dirty + perbarui chip; refresh
        terjadi saat pane benar-benar terlihat (ensure_refreshed). Dulu
        refresh penuh tiap ganti H walau tab tak terlihat."""
        self.tanggal_h = int(h)
        if hasattr(self, "_h_chip_var"):
            self._h_chip_var.set(str(self.tanggal_h))
        if self._dirty:
            return          # belum pernah dirender — refresh saat tab dibuka
        if not self.winfo_ismapped():
            self._dirty = True   # tersembunyi — refresh saat terlihat lagi
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
        self._refresh()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.nominal')."""
        return col_sel_to_json(self._col_sel)

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state (pola
        deviasi_view — lihat catatan lengkap di sana)."""
        if not isinstance(state, dict):
            return
        if self.data is None or bool(getattr(self.data, "empty", True)):
            return
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        if changed and self.winfo_ismapped():
            self._refresh()

    def _col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup filter header.

        v3.9.33 — AUDIT FIX (48-e FIX 1a, pola laporan v3.9.5 audit 19-b
        #1): kolom tampilan "Harga" disimpan di _result_df dengan nama
        INTERNAL "Harga Tampil" — dipetakan di sini juga. Dulu hanya
        jalur APPLY (_render_rows) yang memetakan → daftar nilai kolom
        Harga kosong (pra-render) / berisi angka mentah "18.250" ≠ sel
        tampil "18.250 KG" → apply filter Harga apa pun = "Tidak ada
        baris setelah filter" (tabel kosong)."""
        key = "Harga Tampil" if col == "Harga" else col
        result = self._result_df
        if result is None or result.empty:
            return []
        # nilai unik TERFORMAT dari baris tampil (filter kolom lain aktif)
        f = result
        for c, sel in self._col_sel.items():
            if sel is None or c == col:
                continue
            out_col = "Harga Tampil" if c == "Harga" else c
            if out_col in f.columns:
                fmt = self._format_col_series(c, f[out_col])
                f = f[fmt.isin(sel)]
        if f.empty or key not in f.columns:
            return []
        return self._format_col_series(col, f[key]).unique().tolist()

    def _format_col_series(self, col: str, series):
        if col in self.NUMERIC_COLS:
            # v3.9.51 — Nominal: Currency Rp (konsisten sel tabel); Harga &
            # Qty Deviasi tetap fmt lama.
            if col == "Nominal":
                return series.map(fmt_rp_cell)
            return series.map(self._fmt_cell_num)
        return series.astype(str)

    def _on_col_filter(self, col: str, selected):
        self._col_sel[col] = selected
        self._refresh()

    def _result_cols(self) -> list:
        return [c[0] for c in self.COLUMNS]

    def _sort_by(self, col: str, reverse: bool = False):
        if col not in self._result_cols():
            return
        if self._busy:
            self._pending_sort = (col, reverse)
            return
        parse = self._parse_num_id if col in self.NUMERIC_COLS else None
        sort_tree_by_column(self.tree, col, reverse=reverse, parse=parse)
        self._pin_total_row(self.tree)   # v3.9.33 — AUDIT FIX (48-e FIX 4)
        self._reapply_cell_tags(self.tree)
        self._pending_sort = None

    def _pin_total_row(self, tree):
        """v3.9.33 — AUDIT FIX (48-e FIX 4): baris TOTAL dipin di UJUNG
        tabel setelah sort — sort_tree_by_column mengurutkan SEMUA baris
        termasuk "row_total" (sort Nominal menurun → TOTAL melompat ke
        atas/tengah data). Dipanggil juga setelah filter clone ⛶ rebuild
        (apply_tree_row_filters menjalankan ulang sort terakhir tree)."""
        try:
            if "row_total" in tree.get_children(""):
                tree.move("row_total", "", "end")
        except tk.TclError:
            pass

    @staticmethod
    def _parse_num_id(s):
        """Parser sort format Indonesia: '1.234' = 1234, '(1.234)' =
        -1234, '-' = 0, '12,5' = 12.5 (identik deviasi_view v3.9.6 —
        harga tampil '18.250 KG' → 18250; parser default salah utk
        format Indonesia).
        v3.9.51: prefiks 'Rp ' dibuang DULU (fmt_rp_cell — kolom Nominal:
        'Rp 1.825' → 1825, '(Rp 1.825)' → -1825) SEBELUM split label
        satuan (parts[0])."""
        s = str(s).replace("—", "").replace("Rp ", "") \
            .replace("Rp", "").strip()
        parts = s.split()          # buang label satuan di ekor
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
        # baris TOTAL: latar lembut + teks gelap
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
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        self._show_content()
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        # lazy refresh — compute hanya bila tab terlihat
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True
        # v3.9.33 — AUDIT FIX (48-f P0#6 sebagian): pipeline 0 baris →
        # footer INFORMATIF (bukan 'Belum ada data.' polos — user tak
        # tahu harus mengecek apa); teks lama diperpanjang, jalur kosong
        # dari path lain (reset/H) tetap memakai teks lama.
        if data is None or len(data) == 0:
            self.status_var_label.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")

    def ensure_refreshed(self):
        """Lazy refresh (v3.2): compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None and not self.data.empty:
            self._dirty = False
            self._refresh()

    # =========================================================================
    # COMPUTE
    # =========================================================================
    def _compute_nominal(self, data: pd.DataFrame | None = None,
                         h: int | None = None) -> pd.DataFrame:
        """Frame per pasangan tanggal H: [Nama Barang, Resto, Satuan,
        Harga(nilai|None), Harga Tampil(str), Qty Deviasi, Nominal|None].

        Qty deviasi = JENIS '3.DEVIASI' baris Tanggal H (= SO − SALDO
        AKHIR sistem — nilai kolom Deviasi tab 📦 Deviasi GR; pasangan
        tanpa baris tanggal H → tak dihitung, kontribusi 0).
        self._result_df (snapshot utk filter header) ikut diisi.

        v3.9.34 — REFACTOR (zero behavior change): inti compute
        (filter 3.DEVIASI@H → groupby pasangan → loop harga +
        normalisasi satuan → sort |Nominal| menurun) kini PANGGILAN
        helper bersama nominal_common.hitung_nominal_pairs — port
        PERSIS logika v3.9.32/33 (dtype float64 eksplisit Harga/Nominal,
        urutan |Nominal|↓ lalu |qty|↓, fallback '*' transparan).
        Wrapper (df default self.data, empty → _result_df None, snapshot
        display kolom) dipertahankan apa adanya.
        """
        df = self.data if data is None else data
        if df is None or df.empty:
            self._result_df = None
            return pd.DataFrame()
        if h is None:
            h = self.tanggal_h
        h = int(h)

        # v3.9.34 — logika inti di nominal_common (port persis v3.9.32/33)
        grouped = hitung_nominal_pairs(df, h, self.harga_map,
                                       self.konversi_map)
        if grouped is None or grouped.empty:
            # tanpa baris 3.DEVIASI tanggal H (perilaku lama)
            self._result_df = None
            return pd.DataFrame()

        # snapshot utk filter header (SEBELUM filter diterapkan)
        self._result_df = grouped[
            ["Nama Barang", "Resto", "Satuan", "Harga Tampil",
             "Qty Deviasi", "Nominal"]].copy()
        return grouped

    # =========================================================================
    # REFRESH + RENDER
    # =========================================================================
    def _refresh(self, sync: bool = False):
        if self.data is None or self.data.empty:
            self.status_var_label.set("Belum ada data.")
            return
        if self._busy:
            self._pending = True
            return
        self._busy = True
        # v3.9.33 — AUDIT FIX (48-e FIX 5b, pola laporan v3.9.7): _dirty
        # di-clear saat refresh BERJALAN — dulu hanya ensure_refreshed
        # yang me-clear → load_data saat tab TERLIHAT me-render tabel
        # tapi _dirty tetap True → listener H berikutnya salah-skip
        # refresh (potensi tabel basi / compute pane tersembunyi dobel).
        self._dirty = False
        data = self.data
        h = self.tanggal_h
        gen = self._render_gen

        def work():
            # capture identitas pra-capture (pola FIX D-01)
            return self._compute_nominal(data, h)

        def done(payload):
            # v3.9.33 — AUDIT FIX (48-e FIX 3, pola sibling laporan /
            # in_selisih / rincian): _busy TIDAK lagi di-reset di awal
            # done() — reset hanya di render_done SETELAH batch insert
            # selesai. Dulu: sort yang diklik saat insert masih berjalan
            # dieksekusi di tengah sisipan → urutan campuran (prefix
            # terurut + ekor belum terurut).
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
            self.status_var_label.set(f"⚠ Gagal menghitung nominal: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menghitung nominal deviasi…",
                  on_error=on_error, sync=sync)

    @staticmethod
    def _fmt_harga(v) -> str:
        """Harga: pecahan → 2 desimal (18,25); bulat → fmt_int_id.

        v3.9.34 — REFACTOR: body diganti DELEGASI ke helper bersama
        nominal_common.fmt_harga_id (port persis; pemanggil internal
        tetap jalan — zero behavior change)."""
        return fmt_harga_id(v)

    def _fmt_cell_num(self, val) -> str:
        """Format kolom numerik (qty/nominal): bilangan bulat →
        fmt_int_id; pecahan → 2 desimal; negatif dalam kurung; None → '-'.

        v3.9.34 — REFACTOR: body diganti DELEGASI ke helper bersama
        nominal_common.fmt_nominal_cell (port persis; pemanggil internal
        tetap jalan — zero behavior change).
        """
        return fmt_nominal_cell(val)

    def _render_rows(self, result: pd.DataFrame):
        if self._insert_cancel is not None:
            self._insert_cancel()
            self._insert_cancel = None
        self.tree.delete(*self.tree.get_children(""))
        self._neg_cells = []
        self._total_cells = []
        # v3.9.33 — AUDIT FIX (48-e FIX 1b): _result_df TIDAK lagi
        # ditimpa df PENUH hasil compute — snapshot DISPLAY (kolom
        # "Harga Tampil") dari _compute_nominal dipertahankan supaya
        # daftar nilai popup ⧩ kolom Harga selalu identik dengan sel
        # yang tampil (pola laporan v3.9.5; dulu pasca-render popup
        # Harga berisi angka mentah "18.250" ≠ sel "18.250 KG" →
        # apply filter apa pun = tabel kosong).

        # heading dinamis mengikuti TANGGAL H
        self.tree.heading("Qty Deviasi",
                          text=f"Qty Deviasi (H={self.tanggal_h})")
        if getattr(self, "header_filters", None) is not None:
            self.header_filters.refresh_icons()

        # v3.9.33 — AUDIT FIX (48-e FIX 2): jalur kosong (tanpa baris
        # DEVIASI di H / habis terfilter) TIDAK lagi me-reset _busy /
        # membuang _pending sendiri — SEMUA jalur render berakhir di
        # render_done (satu-satunya titik reset), sehingga refresh H
        # yang mengantre saat compute tetap dieksekusi (dulu: ganti H
        # saat jalur kosong → refresh hilang senyap, chip sudah menunjuk
        # H baru tapi tabel masih H lama).
        items = []
        if result is None or result.empty:
            self.status_var_label.set(
                f"Tidak ada baris DEVIASI tanggal {self.tanggal_h}.")
            self._total_var.set("")
        else:
            # filter header ⧩ (nilai TERFORMAT — identik yang tampil)
            filtered = result
            for col, sel in self._col_sel.items():
                if sel is not None and col in filtered.columns:
                    key = "Harga Tampil" if col == "Harga" else col
                    fmt = self._format_col_series(col, filtered[key])
                    filtered = filtered[fmt.isin(sel)]
            if filtered.empty:
                # v3.9.68 — TRI-STATE (audit eksternal T1): seleksi ⧩
                # kosong = filter aktif 0 baris — pesan jujur + cara
                # keluar (bukan pesan generik).
                self.status_var_label.set(
                    zero_row_filter_message(self._col_sel)
                    or "Tidak ada baris setelah filter.")
                self._total_var.set("")
            else:
                col_ids = self._result_cols()
                n = len(filtered)
                total_nom = float(filtered["Nominal"].dropna().sum()) \
                    if "Nominal" in filtered.columns else 0.0
                total_qty = float(filtered["Qty Deviasi"].sum()) \
                    if "Qty Deviasi" in filtered.columns else 0.0
                n_no_harga = int(filtered["Nominal"].isna().sum()) \
                    if "Nominal" in filtered.columns else 0

                for i in range(n):
                    row = filtered.iloc[i]
                    harga_disp = str(row.get("Harga Tampil", "-") or "-")
                    qty = row.get("Qty Deviasi", 0)
                    nom = row.get("Nominal")
                    values = (
                        str(row["Nama Barang"]), str(row["Resto"]),
                        str(row["Satuan"]), harga_disp,
                        self._fmt_cell_num(qty),
                        # v3.9.51 — Nominal: Currency Rp (user: "Semua data
                        # nominal diberi format Currency Rp") — NaN tetap
                        # '-' (tanpa harga).
                        fmt_rp_cell(nom) if nom is not None
                        and not pd.isna(nom) else "-",
                    )
                    tags = ["evenrow" if i % 2 == 0 else "oddrow"]
                    # minus per-cell: Qty Deviasi & Nominal (Tk 8 fallback baris)
                    try:
                        qv = float(qty)
                    except (TypeError, ValueError):
                        qv = 0.0
                    nom_v = None
                    try:
                        if nom is not None and not pd.isna(nom):
                            nom_v = float(nom)
                    except (TypeError, ValueError):
                        nom_v = None
                    if self._cell_tags:
                        if qv < 0:
                            self._neg_cells.append((f"row_{i}", "Qty Deviasi"))
                        if nom_v is not None and nom_v < 0:
                            self._neg_cells.append((f"row_{i}", "Nominal"))
                    elif qv < 0 or (nom_v is not None and nom_v < 0):
                        tags.append("negative")
                    items.append(("", f"row_{i}",
                                  {"values": values, "tags": tuple(tags)}))

                # baris TOTAL di ujung (jumlah qty + nominal) — minus dalam
                # kurung konsisten dgn baris data; v3.9.51 nominal → Rp.
                values_total = (
                    "TOTAL", "", "", "", self._fmt_cell_num(total_qty),
                    fmt_rp_cell(total_nom),
                )
                items.append(("", "row_total",
                              {"values": values_total,
                               "tags": ("total",)}))
                for col in col_ids:
                    self._total_cells.append(("row_total", col))

                status = (f"{fmt_int_id(n)} pasangan · TANGGAL H = "
                          f"{self.tanggal_h}")
                if n_no_harga:
                    status += f" · {fmt_int_id(n_no_harga)} tanpa harga"
                self.status_var_label.set(status)
                # v3.9.42 — audit 61-b P2: chip TOTAL memakai format tabel
                # (v3.9.51: nominal → Currency Rp; qty tetap fmt lama —
                # dulu fmt_int_id (dibulatkan) → chip ≠ baris TOTAL di
                # bawahnya utk nilai yang sama).
                self._total_var.set(
                    f"TOTAL {fmt_rp_cell(total_nom)} "
                    f"({self._fmt_cell_num(total_qty)} qty)")

        def render_done():
            # v3.9.33 — AUDIT FIX (48-e FIX 3): satu-satunya titik reset
            # _busy (setelah batch insert selesai) + proses refresh/sort
            # yang mengantre (pola render_done laporan/in_selisih).
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

        # items kosong → insert_tree_items memanggil on_done SINKRON →
        # render_done tetap berjalan (reset _busy + proses _pending).
        self._insert_cancel = insert_tree_items(
            self.tree, items, batch=500, on_done=render_done)

    def _reapply_cell_tags(self, tree):
        """Pasang ulang tag per-cell (sort/clone = delete+reinsert → tag
        ter-reset). Baris TOTAL diberi style khusus di SEMUA selnya."""
        if not self._cell_tags:
            return
        # v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list
        # kosong = clear overlay — render tanpa sel minus tidak
        # meninggalkan label STALE).
        apply_cell_tag(tree, "neg_cell", self._neg_cells)
        apply_cell_tag(tree, "total_cell", self._total_cells)

    # =========================================================================
    # TOOLBAR TABEL
    # =========================================================================
    def _auto_fit(self):
        auto_fit_columns(self.tree)

    def _maximize(self):
        def filter_setup(new_tree):
            def _after_filter(t=new_tree):
                # v3.9.33 — AUDIT FIX (48-e FIX 4): clone ⛶ — TOTAL tetap
                # di ujung setelah filter rebuild (apply_tree_row_filters
                # menjalankan ulang sort terakhir tree) + tag per-cell
                # dipasang ulang.
                self._pin_total_row(t)
                self._reapply_cell_tags(t)

            attach_clone_filters(
                new_tree, self._result_cols(),
                get_values=lambda c: self._col_values(c),
                on_after_filter=_after_filter)

        return open_tree_maximized(
            self.tree, "Nominal Deviasi — Harga × Qty Deviasi",
            setup_tags=lambda t: self._setup_tags(t),
            on_filter_setup=filter_setup,
            on_render_done=self._reapply_cell_tags)
