"""
rincian_po_view.py — Pivot table view untuk Rincian PO (v3.2 → v3.9).

v3.9.37 (user: "Keterangan PO merger Vertical dengan Pemasok sama
seperti Status Pesanan Juga dan kolom Keterangan PO hapus karna sudah
termerger. Tanggal Jam pembuatan Merger vertical dengan Nomor #"):
- KOLOM "Keterangan PO" DIHAPUS — nilai keterangan kini tampil di
  KOLOM PEMASOK sebagai anotasi "↳ Keterangan" PERSIS pola Status
  Pesanan v3.9.35: anotasi berjalan vertikal di baris anak (status
  di anak pertama, keterangan di anak kedua; PO ber-anak lebih
  sedikit dari anotasi → anotasi sisanya digabung ke sel anak
  TERAKHIR dipisah " · "), sekali per PO, teks redup (tag per-cell
  po_status_note).
- KOLOM "Tgl/Jam Pembuatan" DIHAPUS — nilai tgl/jam kini tampil di
  KOLOM NOMOR # (#0) pada baris anak PERTAMA tiap PO sebagai
  "↳ 02 Juni 2024 09:00" (merge-vertical di bawah nomor PO; teks
  redup tag per-cell yang sama).
- Skema tabel 8 → 6 kolom nilai: Tanggal · Nama Resto · Pemasok ·
  Nama Barang · Satuan · Kuantitas (info PO tetap lengkap — cuma
  lebih ringkas lebar-nya).

v3.9.35 (user: "kolom status pesanan bisa gak ditaruh di bawah kolom
pemasok? seperti merge vertical gitu. Sama kaya kolom nama barang
yang ditampilkan secara vertical. Format tanggal pakai 01 Oktober 2026
aja format panjang"):
- KOLOM "Status Pesanan" DIHAPUS dari tabel — nilai status kini tampil
  di KOLOM PEMASOK pada baris anak PERTAMA tiap PO sebagai "↳ Status"
  (merge-vertical look: tepat di bawah nama pemasok, nilai sekali per
  PO, baris anak lain kosong — persis pola kolom Nama Barang yang
  nilai-nya berjalan vertikal). Teks status dibuat redup via tag
  per-cell (po_status_note) supaya terbaca sebagai anotasi PO, bukan
  data pemasok. Filter status tetap tersedia di kartu Filter (combo
  STATUS PESANAN).
- TANGGAL format panjang Indonesia: "02 Juni 2024" (kolom Tanggal) dan
  "02 Juni 2024 09:00" (anotasi ↳ kolom Nomor # sejak v3.9.37) — nama
  bulan Indonesia.

v3.9.20 (deep audit 34-c/fix 35-c1): _resto_name pd.NA/float-safe
(1370.0 → '1370') + _fmt_date/_fmt_datetime NaT-safe (tab tidak mati) +
load_data reset combo Cabang/Status (filter basi) + literal
None/nan/NaT dibuang dari daftar nilai popup filter.

v3.9 — LAYOUT DISEDERHANAKAN (permintaan user: "tampilan rincian PO
apakah bisa lebih dipermudah lagi biar mudah dibaca?"):
- Baris INDUK (teal) kini memuat SEMUA info PO SEKALI: Nomor #, Tanggal,
  Pemasok, Status Pesanan, Keterangan PO, jumlah item & total kuantitas.
- Baris ANAK (putih) hanya berisi ITEM: Nama Barang, Satuan, Kuantitas —
  dulu setiap baris anak mengulang Tanggal/Pemasok/Tgl-Jam yang sama
  (tabel terasa penuh & sulit dipindai).
- Kolom "Tgl/Jam Pembuatan" (metadata PO, jarang dipakai) dipindah ke
  baris induk dan DISSEMBUNYIKAN default — tampilkan lewat tombol
  ◱ Kolom / klik kanan judul kolom.
- Tombol ⤢ Perbesar Tabel + ⛶ Layar Penuh (ala Waste).

Struktur mirror pivotTable di sample Excel (logika identik versi lama):
- Page filters: Cabang PO, Status Pesanan Pembelian
- Tree rows: Nomor# (parent) → detail children
- Value: Sum of Kuantitas per row + grand total row

v3.9.19 — KOLOM NAMA RESTO (permintaan user: "tambahkan kolom nama
resto di rincian PO"): diambil dari kolom Cabang PO ("1370.MLGPAR" →
"MLGPAR" — kode resto sesuai kolom Resto tab lain; tanpa titik →
nilai apa adanya). Diisi pada BARIS INDUK (info level-PO — konsisten
layout v3.9: anak hanya item); ikut filter header ⧩.
"""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

import pandas as pd

from .theme import C_BG, C_CARD, C_HEADER, C_TEXT_MUTED, font, register_find_tags
from .widgets import (
    _SORT_ARROW_MARKS,
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
    open_tree_maximized,
    reset_autofit_once,  # v3.9.55 — F8
    run_async,
    sort_tree_by_column,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)

# Kolom tabel v3.9.37 (6 kolom nilai — Keterangan PO & Tgl/Jam
# Pembuatan DIHAPUS sebagai kolom: keterangan merge-vertikal ke kolom
# Pemasok [↳ di baris anak, pola Status Pesanan v3.9.35], tgl/jam
# merge-vertikal ke kolom Nomor # #0 [↳ anak pertama]).
PO_COLUMNS = [
    "Tanggal", "Nama Resto", "Pemasok",
    "Nama Barang", "Satuan", "Kuantitas",
]

# Pemetaan nama kolom tampilan → kolom DataFrame sumber
# v3.9.19: "Nama Resto" bersumber kolom Cabang PO (kode resto = bagian
# setelah titik terakhir, mis. "1370.MLGPAR" → "MLGPAR").
# v3.9.35: "Status Pesanan" tidak lagi kolom tampilan (merge ke bawah
# Pemasok) — sumbernya tetap dibaca utk nilai ↳ + combo filter.
# v3.9.37: "Keterangan PO" & "Tgl/Jam Pembuatan" juga bukan kolom
# tampilan lagi (merge ↳ ke Pemasok / Nomor #) — sumber tetap dibaca
# utk nilai anotasi ↳.
COL_SRC = {
    "Nama Resto": "Cabang PO",
}

# v3.9.35 — nama bulan Indonesia utk format tanggal panjang
# ("01 Oktober 2026" — permintaan user).
_BULAN_ID = ("Januari", "Februari", "Maret", "April", "Mei", "Juni",
             "Juli", "Agustus", "September", "Oktober", "November",
             "Desember")


def _resto_name(val) -> str:
    """v3.9.19 — Cabang PO → nama resto: bagian setelah titik TERAKHIR
    ("1370.MLGPAR" → "MLGPAR"; tanpa titik → nilai apa adanya).
    v3.9.30 — logika diangkat ke pipeline helpers.resto_from_cabang_po
    (dipakai juga fn_audit PO Menunggu); wrapper ini tetap ada (app.py
    + test meng-import nama ini)."""
    from src.pipeline.helpers import resto_from_cabang_po
    return resto_from_cabang_po(val)


class RincianPoView(tk.Frame):
    """Pivot table view untuk Rincian PO data (tree-based)."""

    def __init__(self, parent, data: pd.DataFrame = None,
                 go_to_proses: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.data: pd.DataFrame | None = None
        self.go_to_proses = go_to_proses
        self._busy = False
        self._pending = False
        self._dirty = False                # lazy refresh (v3.2)
        # v3.9.42 — audit 61-c/61-d (F2 P2): snapshot state tampilan utk
        # refresh preserve=True (posisi scroll + seleksi baris; dipulihkan
        # di render_done — lihat _restore_view_state).
        self._preserve_after_render = None

        self._build_ui()
        self._setup_tags()
        if data is not None:
            self.load_data(data)
        else:
            self._show_empty()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        # --- Empty state ---
        self.empty = EmptyState(
            self, icon="🛒", title="Belum ada data Rincian PO",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Konten utama ---
        self.content = tk.Frame(self, bg=C_BG)

        # (v3.2) KPI row DIHAPUS — tabel lebar & besar; ringkasan
        # (PO · item · total kuantitas) ada di status footer.

        # --- Filter card ---
        fcard = Card(self.content, title="Filter")
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        fbody = fcard.body()

        r0 = tk.Frame(fbody, bg=C_CARD)
        r0.pack(fill="x")
        tk.Label(r0, text="CABANG PO", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.cabang_var = tk.StringVar(value="(All)")
        self.cabang_combo = ttk.Combobox(r0, textvariable=self.cabang_var,
                                         state="readonly", width=22)
        self.cabang_combo.pack(side="left", padx=(6, 18))
        self.cabang_combo.bind("<<ComboboxSelected>>",
                               lambda e: self._on_combo_filter())

        tk.Label(r0, text="STATUS PESANAN", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.status_pesanan_var = tk.StringVar(value="(All)")
        self.status_combo = ttk.Combobox(r0,
                                         textvariable=self.status_pesanan_var,
                                         state="readonly", width=22)
        self.status_combo.pack(side="left", padx=(6, 18))
        self.status_combo.bind("<<ComboboxSelected>>",
                               lambda e: self._on_combo_filter())

        GhostButton(r0, text="✕ Reset Filter",
                    command=self._reset_filter).pack(side="left")

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        self._tcard = tcard
        tbody = tcard.body()

        # Header tabel: judul + tombol perbesar
        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        title_label = tk.Label(
            head, text="Rincian PO — per PO (teal) + item barang",
            bg=C_CARD, fg=C_HEADER, font=font(10, "bold"))
        title_label.pack(side="left")
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

        # v3.9: expander ⤢ — ciutkan kartu filter + judul
        self._expander = TableExpander(btn_expand, [fcard, title_label])

        cols = PO_COLUMNS
        self.tree = ttk.Treeview(tbody, columns=cols, show="tree headings",
                                 selectmode="extended")

        # v3.9.37 — #0 lebih lebar: memuat anotasi "↳ 02 Juni 2024 09:00"
        # (Tgl/Jam Pembuatan merge-vertical ke Nomor #).
        self.tree.column("#0", width=185, minwidth=150)
        self.tree.heading("#0", text="Nomor #")
        col_widths = {
            "Tanggal": 132, "Nama Resto": 90, "Pemasok": 200,
            "Nama Barang": 200, "Satuan": 64, "Kuantitas": 90,
        }
        for c in cols:
            self.tree.column(c, width=col_widths.get(c, 100), minwidth=50,
                             anchor="e" if c == "Kuantitas" else "w")
            self.tree.heading(c, text=c)

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

        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.status_var = tk.StringVar(value="Belum ada data.")
        tk.Label(foot, textvariable=self.status_var, bg=C_CARD, fg=C_HEADER,
                 font=font(8, "bold")).pack(side="right")

        # Loading overlay (stacking di atas tree)
        self.overlay = LoadingOverlay(tbody, "Menyiapkan pivot PO…")

        # v3.5: filter header ⧩ di SEMUA kolom (#0 = Nomor # + 7 kolom data)
        _filter_cols = ["#0"] + cols
        self._col_sel: dict = {c: None for c in _filter_cols}
        self.header_filters = HeaderFilterGroup(
            self.tree, _filter_cols,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            # v3.9.59 — FIX 2e-08: sort ⧩ tersambung (dulu None —
            # satu-satunya tabel data tanpa tombol ↕ Sort di popup).
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        # v3.6: hide/unhide kolom (klik kanan heading / tombol ◱ Kolom)
        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filters.open_popup(c))
        # v3.9.37: "Tgl/Jam Pembuatan" kini anotasi ↳ di kolom Nomor #
        # (kolomnya sendiri dihapus — tidak ada lagi yang perlu
        # disembunyikan default).

    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten."""
        auto_fit_columns(self.tree)

    def _col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup filter header (v3.5; v3.9 —
        mapping nama kolom tampilan → kolom df sumber).

        v3.9.19 — sumber nilai = baris yang TAMPIL SAAT INI (permintaan
        user: "isi filter harus menampilkan data yang ada aja"): filter
        CABANG PO + STATUS PESANAN + filter header kolom LAIN diterapkan
        dulu (kolom ini sendiri dikecualikan — perilaku AutoFilter Excel);
        dulu df mentah → nilai kategori/barang cabang lain ikut tampil
        meski barisnya sudah terfilter."""
        df = self._filtered_data(exclude_col=col)
        if df is None or df.empty:
            return []
        if col == "#0":
            if "Nomor #" in df.columns:
                vals = df["Nomor #"].dropna().astype(str).unique().tolist()
                return [v for v in vals if v not in ("None", "nan", "NaT")]
            return []
        src = COL_SRC.get(col, col)
        if src not in df.columns:
            return []
        # FIX 35-c1 (NIT C1): literal 'None'/'nan'/'NaT' (object cols dgn
        # None asli via safe_to_str) jangan bocor ke daftar nilai popup
        # filter — '' tetap dipertahankan (baris anak sah bernilai kosong).
        vals = self._format_col_series(col, df[src]).unique().tolist()
        return [v for v in vals if v not in ("None", "nan", "NaT")]

    def _filtered_data(self, exclude_col: str | None = None):
        """v3.9.19 — df setelah filter combobox + header kolom lain
        (vektor; dipanggil saat popup filter dibuka)."""
        df = self.data
        if df is None or df.empty:
            return df
        for c, val in [("Cabang PO", self.cabang_var.get()),
                       ("Status Pesanan Pembelian",
                        self.status_pesanan_var.get())]:
            if val and val != "(All)" and c in df.columns:
                df = df[df[c].astype(str) == val]
        for c, sel in self._col_sel.items():
            if sel is None or c == exclude_col:
                continue
            src_col = "Nomor #" if c == "#0" else COL_SRC.get(c, c)
            if src_col in df.columns:
                fmt = self._format_col_series(c, df[src_col])
                df = df[fmt.isin(sel)]
        return df

    def _format_col_series(self, col: str, series):
        """Format kolom → string tampilan (identik render tabel)."""
        if col == "Tanggal":
            return series.map(self._fmt_date)
        if col == "Kuantitas":
            return series.map(self._fmt_num)
        if col == "Nama Resto":   # v3.9.19 — Cabang PO → kode resto
            return series.map(_resto_name)
        return series.astype(str)

    def _on_combo_filter(self):
        # v3.9.42 — audit 61-c/61-d (F2 P2): combo diubah user saat refresh
        # mengantre → buang snapshot restore (intent user menang) lalu
        # refresh tabel.
        self._preserve_after_render = None
        self._refresh()

    def _on_col_filter(self, col: str, selected):
        # v3.9.42 — audit 61-c/61-d (F2 P2): user mengubah filter saat
        # refresh mengantre → buang snapshot restore (intent user
        # menang atas restore refresh).
        self._preserve_after_render = None
        self._col_sel[col] = selected
        self._refresh()

    def _sort_by(self, col: str, reverse: bool = False, tree=None):
        """v3.9.59 — FIX 2e-08: sort level PO (baris INDUK).
        Dulu on_sort=None — satu-satunya tabel data tanpa sort (popup ⧩
        tanpa tombol ↕) padahal 7 view lain semuanya tersambung; sort
        per Tanggal/Nomor #/Pemasok bermakna (mengurutkan grup PO).
        Anak item ikut induk (jalur tree.move hirarki
        sort_tree_by_column — tag per-cell anotasi ↳ tetap utuh);
        GRAND TOTAL dipin di ujung (pola _pin_total_row nominal).
        Kolom level-item (Nama Barang/Satuan) → kunci = anak PERTAMA
        PO; Tanggal (label panjang '01 Oktober 2026') → kunci ISO
        supaya urut KRONOLOGIS (sort abjad '01 Oktober' < '02 Juni'
        salah antar bulan); Kuantitas induk 'Total: N' → N numerik."""
        tree = tree if tree is not None else self.tree
        try:
            cols = ["#0"] + [str(c) for c in tree["columns"]]
        except tk.TclError:
            return
        if col not in cols:
            return
        k = (-1 if col == "#0"
             else [str(c) for c in tree["columns"]].index(col))

        def _key(iid):
            try:
                if k < 0:
                    return str(tree.item(iid, "text") or "")
                src = iid
                if col in ("Nama Barang", "Satuan"):
                    kids = tree.get_children(iid)
                    if kids:
                        src = kids[0]     # nilai level-item: anak pertama
                vals = tree.item(src, "values") or []
                v = str(vals[k]) if 0 <= k < len(vals) else ""
                if col == "Kuantitas" and v.startswith("Total:"):
                    v = v[len("Total:"):].strip()
                elif col == "Tanggal":
                    v = self._date_sort_key(v)
                return v
            except tk.TclError:
                return ""

        sort_tree_by_column(tree, col, reverse=reverse, value_get=_key)
        # GRAND TOTAL selalu di ujung (sort jangan melompatkannya ke atas)
        try:
            if tree.exists("grand_total"):
                tree.move("grand_total", "", "end")
        except tk.TclError:
            pass
        if col == "#0":
            self._set_arrow0(tree, reverse)
        else:
            # sort kolom DATA → panah #0 lama DIBERSIHKAN (_set_sort_arrow
            # widgets hanya menyapu heading kolom data, bukan #0).
            self._set_arrow0(tree, None)

    @staticmethod
    def _date_sort_key(s: str) -> str:
        """'01 Oktober 2026' → '2026-10-01' (kunci sort KRONOLOGIS;
        teks lain apa adanya → fallback string sort)."""
        parts = str(s).split()
        if len(parts) == 3:
            try:
                d = int(parts[0])
                m = _BULAN_ID.index(parts[1]) + 1
                y = int(parts[2])
                return f"{y:04d}-{m:02d}-{d:02d}"
            except (ValueError, IndexError):
                pass
        return str(s)

    @staticmethod
    def _set_arrow0(tree, reverse) -> None:
        """FIX 2e-08 — panah arah sort kolom #0 (Nomor #): _set_sort_arrow
        (widgets, B-21) hanya menulis heading kolom DATA; #0 diberi panah
        manual di sini (marker kanon sama: ' ↓' menurun / ' ↑' naik).
        ``reverse=None`` → hanya MENGHAPUS panah (sort pindah ke kolom
        data — panah #0 basi jangan tertinggal)."""
        try:
            cur = str(tree.heading("#0", "text") or "")
            for m in _SORT_ARROW_MARKS:
                if cur.endswith(m):
                    cur = cur[: -len(m)]
                    break
            if reverse is not None:
                cur += (_SORT_ARROW_MARKS[0] if reverse
                        else _SORT_ARROW_MARKS[1])
            tree.heading("#0", text=cur)
        except tk.TclError:
            pass

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
        # Nomor# parent row — teal tint + bold (v3.9: font 10 sej tabel)
        tree.tag_configure("po_header", font=font(10, "bold"),
                           background="#ccfbf1",
                           foreground="#134e4a")
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        # Grand total row — slate
        tree.tag_configure("grand_total", font=font(10, "bold"),
                           background="#e2e8f0",
                           foreground="#0f172a")
        # v3.9.35 — anotasi status PO (↳ di bawah Pemasok, anak pertama
        # tiap PO): teks REDUP via tag per-CELL (bukan tag baris — tidak
        # pernah dipasang ke item; mekanisme overlay sama dgn minus
        # merah view lain). Dipasang _apply_status_notes pasca-render.
        tree.tag_configure("po_status_note", foreground=C_TEXT_MUTED)

    # =========================================================================
    # DATA LOADING
    # =========================================================================
    def load_data(self, data: pd.DataFrame, preserve: bool = False):
        """Muat data baru (dari pipeline).

        v3.9.42 — audit 61-c/61-d (F2 P2): preserve=True (jalur REFRESH
        app v3.9.37) TIDAK me-reset state tampilan — dulu load_data
        SELALU me-reset combo Cabang/Status (FIX 35-c1) + _col_sel ⧩ +
        clear_all() padahal refresh menjanjikan "gangguan minimal":
        filter, posisi scroll & seleksi baris lenyap tiap refresh.
        Nilai combo dipertahankan HANYA bila masih ada di values data
        BARU (validasi — hilang → "(All)", guard basi 35-c1 tetap
        jalan); _col_sel dipakai ulang _prepare_rows; scroll+seleksi
        dipulihkan SETELAH baris ter-insert (render_done). Default
        False = load awal, perilaku lama."""
        self.data = data

        # v3.9.55 — F8: data baru → auto-fit SEKALI lagi saat render pertama
        reset_autofit_once(self)
        # v3.9: pulihkan layout bila sedang di-perbesar ⤢
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        self._show_content()
        self._populate_filters()
        # FIX 35-c1 (RISK C5): combo CABANG/STATUS ikut di-reset saat data
        # berganti — dulu hanya _col_sel + header ⧩; var basi (mis. data baru
        # tanpa cabang itu) membuat tabel 0 baris SENYAP ("Tidak ada data
        # setelah filter.") & popup filter kolom mati.
        # v3.9.42 — audit 61-c/61-d (F2 P2): cabang reset itu benar utk LOAD
        # AWAL — tapi jalur REFRESH kini preserve=True: nilai combo
        # divalidasi terhadap values data BARU (bukan dibuang begitu saja).
        if preserve:
            for var, combo in ((self.cabang_var, self.cabang_combo),
                               (self.status_pesanan_var, self.status_combo)):
                val = var.get()
                try:
                    vals = list(combo["values"])
                except tk.TclError:
                    vals = []
                if val not in vals:
                    var.set("(All)")
            # filter header ⧩: _col_sel DIPERTAHANKAN (dibaca lagi oleh
            # _refresh → _prepare_rows) + funnel aktif di-reassert via
            # API HeaderFilterGroup.set_selected (v3.9.22) supaya ikon
            # state-nya sinkron dgn seleksi yang dipertahankan.
            for c, sel in self._col_sel.items():
                if sel is not None:
                    self.header_filters.set_selected(c, sel)
            # scroll + seleksi baru bisa dipulihkan SETELAH semua baris
            # ter-insert (insert async batch → render_done) — simpan dulu.
            try:
                frac = self.tree.yview()[0]
                sel_iids = list(self.tree.selection())
            except tk.TclError:
                frac, sel_iids = 0.0, []
            self._preserve_after_render = {"frac": frac, "iids": sel_iids}
        else:
            self._preserve_after_render = None
            self.cabang_var.set("(All)")
            self.status_pesanan_var.set("(All)")
            for c in self._col_sel:
                self._col_sel[c] = None
            self.header_filters.clear_all()
        # (v3.2) lazy refresh — compute hanya bila tab terlihat
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True
        # v3.9.33 — AUDIT FIX (48-f P0#6 sebagian): pipeline 0 baris →
        # footer INFORMATIF (teks lama diperpanjang; kata kunci 'Belum
        # ada data' tetap ada supaya assertion lama tetap lolos).
        if data is None or len(data) == 0:
            self.status_var.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")

    def ensure_refreshed(self):
        """Lazy refresh (v3.2): compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None and not self.data.empty:
            self._dirty = False
            self._refresh()

    def _populate_filters(self):
        if self.data is None or self.data.empty:
            return
        for col, combo in [("Cabang PO", self.cabang_combo),
                           ("Status Pesanan Pembelian", self.status_combo)]:
            if col in self.data.columns:
                values = ["(All)"] + sorted(
                    self.data[col].dropna().astype(str).unique().tolist())
                combo["values"] = values

    # =========================================================================
    # RENDER (async + batched — logika identik versi lama)
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
            "cabang": self.cabang_var.get(),
            "status_pesanan": self.status_pesanan_var.get(),
            # v3.9.13: seleksi kosong (set()) = filter AKTIF → 0 baris
            # (semantik Excel) — dulu truthiness `if s` menelannya.
            "col_sel": {c: s for c, s in self._col_sel.items()
                        if s is not None},
        }

        def work():
            return self._prepare_rows(st)

        def done(payload):
            self._render_rows(payload)

        # FIX C-02/D-02 (audit 2-c/2-d): on_error — kelas fix B-01 v3.9.1
        # yang terlewat di view ini: TANPA reset _busy, satu exception di
        # _prepare_rows membuat tab 🛒 Rincian PO MATI PERMANEN sesi
        # (guard `if self._busy` menelan semua refresh berikutnya).
        def on_error(err):
            self._busy = False
            self._pending = False
            self.status_var.set(f"⚠ Gagal menyiapkan pivot PO: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menyiapkan pivot PO…", sync=sync,
                  on_error=on_error)

    def _prepare_rows(self, st: dict) -> dict:
        """Pure pandas: filter + group → items tree (thread-safe).

        v3.9 LAYOUT RINGKAS:
        - PARENT (teal, "po_header"): Nomor # + SEMUA info PO sekali
          (Tanggal, Pemasok, Status, Keterangan PO, Tgl/Jam Pembuatan
          [kolom tersembunyi default]) + ringkasan "N item" + total qty.
        - ANAK (putih, zebra): HANYA item — Nama Barang, Satuan, Kuantitas.
        """
        df = self.data
        for col, val in [("Cabang PO", st["cabang"]),
                         ("Status Pesanan Pembelian", st["status_pesanan"])]:
            if val and val != "(All)" and col in df.columns:
                df = df[df[col].astype(str) == val]

        # v3.5: filter header ⧩ — kecocokan nilai TERFORMAT (semua kolom;
        # v3.9: mapping nama kolom tampilan → kolom df sumber)
        for col, sel in st["col_sel"].items():
            src_col = "Nomor #" if col == "#0" else COL_SRC.get(col, col)
            if src_col in df.columns:
                fmt = self._format_col_series(col, df[src_col])
                df = df[fmt.isin(sel)]

        if df.empty:
            # v3.9.68 — TRI-STATE (audit eksternal T1): pesan jujur bila
            # penyebabnya seleksi ⧩ KOSONG (filter aktif → 0 baris).
            return {"items": [], "kpi": (0, 0, 0),
                    "status": (zero_row_filter_message(st["col_sel"])
                               or "Tidak ada data setelah filter.")}

        if "Nomor #" not in df.columns:
            return {"items": [], "kpi": (0, 0, 0),
                    "status": "Kolom 'Nomor #' tidak ditemukan."}

        sort_cols = [c for c in ["Nomor #", "Tanggal"] if c in df.columns]
        df_sorted = df.sort_values(sort_cols) if sort_cols else df

        total_qty = 0
        po_count = 0
        item_count = 0
        items = []

        def _first_str(series) -> str:
            """Nilai non-kosong pertama dari series (info level-PO)."""
            s = series.dropna().astype(str).str.strip()
            s = s[s != ""]
            return s.iloc[0] if len(s) else ""

        def _first_fmt(series, fmt) -> str:
            """v3.9.33 — AUDIT FIX (48-e FIX 13): nilai TERFORMAT non-kosong
            PERTAMA dari series (pola _first_str, utk kolom datetime) —
            'Tgl/Jam Pembuatan' dulu memakai .iloc[0]: baris PERTAMA
            NaT/kosong menampilkan kolom kosong padahal baris lain di PO
            yang sama punya nilai."""
            s = series.map(fmt).astype(str).str.strip()
            s = s[s != ""]
            return s.iloc[0] if len(s) else ""

        def _fmt_qty(v) -> str:
            """Kuantitas: bulat tanpa desimal, pecahan 1 desimal (v3.9).
            FIX C-03 (audit 2-c): format INDONESIA — dulu EN "1,234.5"
            (koma = ribuan) tidak konsisten dgn 6 view lain."""
            try:
                f = float(v)
            except (TypeError, ValueError):
                return str(v)
            if f == int(f):
                return fmt_int_id(f)
            return f"{f:,.1f}".replace(",", "X").replace(".", ",") \
                .replace("X", ".")

        # nilai per kolom PO: konsisten dalam satu PO → ambil nilai pertama
        for nomor, group in df_sorted.groupby("Nomor #", sort=False):
            po_count += 1
            n_items = len(group)
            po_qty = (group["Kuantitas"].sum()
                      if "Kuantitas" in group.columns else 0)
            total_qty += po_qty
            parent_iid = f"po_{po_count}"
            # v3.9.35 — STATUS PESANAN utk anotasi ↳ di kolom Pemasok
            # (baris anak PERTAMA — merge vertical; kolom tersendiri
            # DIHAPUS permintaan user).
            status_po = (_first_str(group["Status Pesanan Pembelian"])
                         if "Status Pesanan Pembelian" in group.columns
                         else "")
            # v3.9.37 — KETERANGAN PO utk anotasi ↳ di kolom Pemasok
            # (pola SAMA dgn status: merge vertical; kolom tersendiri
            # DIHAPUS — "Keterangan PO merger Vertical dengan Pemasok
            # sama seperti Status Pesanan Juga").
            ket_po = (_first_str(group["Keterangan PO"])
                      if "Keterangan PO" in group.columns else "")
            # v3.9.37 — TGL/JAM PEMBUATAN utk anotasi ↳ di kolom NOMOR #
            # ("Tanggal Jam pembuatan Merger vertical dengan Nomor #";
            # nilai TERFORMAT non-kosong pertama — FIX 48-e 13).
            tgljam_po = (_first_fmt(group["Tgl/Jam Pembuatan"],
                                    self._fmt_datetime)
                         if "Tgl/Jam Pembuatan" in group.columns else "")
            # anotasi ↳ kolom Pemasok — urutan: STATUS dulu, lalu
            # KETERANGAN (status duluan pola v3.9.35, keterangan menyusul
            # di baris anak berikutnya — nilai berjalan vertikal per PO).
            pemasok_notes = [f"↳ {status_po}"] if status_po else []
            if ket_po:
                pemasok_notes.append(f"↳ {ket_po}")
            # BARIS INDUK = info PO lengkap + ringkasan (v3.9)
            # v3.9.19: NAMA RESTO (dari Cabang PO — level-PO; anak baris
            # tetap hanya item, konsisten layout ringkas v3.9)
            # v3.9.37: Keterangan PO & Tgl/Jam Pembuatan TIDAK lagi kolom
            # tampilan (lihat anotasi anak di bawah).
            items.append(("", parent_iid,
                          {"text": str(nomor),
                           "values": [
                               self._fmt_date(group["Tanggal"].iloc[0])
                               if "Tanggal" in group.columns else "",
                               _resto_name(_first_str(group["Cabang PO"]))
                               if "Cabang PO" in group.columns else "",
                               _first_str(group["Pemasok"])
                               if "Pemasok" in group.columns else "",
                               f"▸ {n_items} item",
                               "",
                               f"Total: {_fmt_qty(po_qty)}",
                           ],
                           "tags": ("po_header",), "open": True}))

            # BARIS ANAK = hanya item barang (v3.9 — tanpa mengulang info
            # PO). v3.9.35: anak PERTAMA membawa STATUS PO (↳ …) di kolom
            # PEMASOK — merge-vertical ala kolom Nama Barang; anak
            # berikutnya kosong (nilai status sekali per grup PO).
            # v3.9.37: (a) anak PERTAMA juga membawa TGL/JAM PEMBUATAN
            # (↳ …) di kolom NOMOR # #0 — merge vertical dengan Nomor #;
            # (b) anotasi Pemasok bisa LEBIH DARI SATU (status lalu
            # keterangan) — anotasi ke-i di baris anak ke-i; PO dgn anak
            # lebih sedikit dari anotasi → sisa anotasi digabung ke sel
            # anak TERAKHIR dipisah " · " (nilai tetap sekali per PO).
            last_i = n_items - 1
            for i, (_idx, row) in enumerate(group.iterrows()):
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                item_count += 1
                # anotasi Pemasok utk baris anak ini
                if i < len(pemasok_notes):
                    note = pemasok_notes[i]
                else:
                    note = ""
                if i == last_i and len(pemasok_notes) > n_items:
                    # PO dgn anak lebih sedikit dari anotasi (mis. 1 anak
                    # ber-status+keterangan): sisa anotasi digabung ke sel
                    # anak TERAKHIR — nilai tetap sekali per PO.
                    extra = " · ".join(pemasok_notes[n_items:])
                    note = f"{note} · {extra}" if note else extra
                items.append((
                    parent_iid, f"{parent_iid}_{item_count}",
                    {"text": f"↳ {tgljam_po}"
                              if (i == 0 and tgljam_po) else "",
                     "values": [
                         "", "",
                         note,
                         str(row.get("Nama Barang", "")),
                         str(row.get("Satuan", "")),
                         self._fmt_num(row.get("Kuantitas")),
                     ],
                     "tags": (tag,), "open": False}))

        # 6 kolom nilai (grand total: N PO di kolom Nama Barang, total qty
        # sejajar kolom Kuantitas)
        items.append(("", "grand_total",
                      {"text": "GRAND TOTAL",
                       "values": ["", "", "",
                                   f"{po_count} PO", "",
                                   _fmt_qty(total_qty)],
                       "tags": ("grand_total",), "open": False}))

        status = (f"{po_count} PO · {item_count} item · "
                  f"Total Kuantitas: {_fmt_qty(total_qty)}")
        return {"items": items, "kpi": (po_count, item_count, total_qty),
                "status": status}

    def _render_rows(self, payload: dict):
        self.tree.delete(*self.tree.get_children())
        self.header_filters.refresh_icons()
        # ringkasan (PO · item · total qty) ada di status footer (v3.2)
        self.status_var.set(payload["status"])

        # v3.9.35 — anotasi status ↳ (tag per-cell, teks redup)
        # dipasang SETELAH semua baris masuk (insert async batch).
        # v3.9.37 — anotasi keterangan ↳ (Pemasok) + tgl/jam ↳ (Nomor #)
        # ikut diberi tag (dipanggil fungsi yang sama).
        def render_done():
            self._busy = False
            self._apply_status_notes()
            # v3.9.55 — F8: auto-fit kolom SEKALI per muat data
            autofit_tree_once(self, self.tree)
            # v3.9.42 — audit 61-c/61-d (F2 P2): pulihkan posisi scroll +
            # seleksi yang disimpan load_data(preserve=True) — baru aman
            # di sini karena SEMUA baris sudah ter-insert (insert async
            # batch); iid yang lenyap di data baru di-skip senyap.
            self._restore_view_state()
            if self._pending:
                self._pending = False
                self._refresh()

        insert_tree_items(self.tree, payload["items"], batch=500,
                          on_done=render_done)

    def _restore_view_state(self):
        """v3.9.42 — audit 61-c/61-d (F2 P2): pulihkan yview fraction +
        seleksi baris pasca-render (dipanggil render_done; snapshot dibuat
        load_data(preserve=True)). Sekali pakai — snapshot dikonsumsi."""
        snap = self._preserve_after_render
        if not snap:
            return
        self._preserve_after_render = None
        try:
            if not self.winfo_exists():
                return
            if snap.get("frac"):
                self.tree.yview_moveto(snap["frac"])
            for iid in snap.get("iids") or ():
                if self.tree.exists(iid):
                    self.tree.selection_add(iid)
        except tk.TclError:
            # view/tree sudah tiada saat timer mendarat — abaikan.
            pass

    def _reset_filter(self):
        # v3.9.42 — audit 61-c/61-d (F2 P2): reset eksplisit user → buang
        # snapshot restore refresh yang mengantre (jangan hidupkan lagi).
        self._preserve_after_render = None
        self.cabang_var.set("(All)")
        self.status_pesanan_var.set("(All)")
        for c in self._col_sel:
            self._col_sel[c] = None
        self.header_filters.clear_all()
        self._refresh()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.rincian_po')."""
        st = col_sel_to_json(self._col_sel)
        st["cabang"] = self.cabang_var.get()
        st["status_pesanan"] = self.status_pesanan_var.get()
        return st

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.

        Combobox CABANG/STATUS divalidasi terhadap values data BARU
        (pola preserve v3.9.42 — nilai hilang → "(All)" default tetap;
        tanpa ini settings.json basi memasang filter 0-baris senyap)."""
        if not isinstance(state, dict):
            return
        if self.data is None or bool(getattr(self.data, "empty", True)):
            return
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        for key, var, combo in (
                ("cabang", self.cabang_var, self.cabang_combo),
                ("status_pesanan", self.status_pesanan_var,
                 self.status_combo)):
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
        if changed and self.winfo_ismapped():
            self._refresh()

    # =========================================================================
    # ⛶ PERBESAR (fullscreen)
    # =========================================================================
    def _maximize(self):
        def filter_setup(new_tree):
            # v3.6: funnel ⧩ jalan juga di window besar
            # v3.9.59 — FIX 2e-08: sort ikut aktif di clone ⛶.
            attach_clone_filters(
                new_tree, ["#0"] + [str(c) for c in new_tree["columns"]],
                get_values=self._col_values,
                on_sort=lambda c, d, t=new_tree: self._sort_by(
                    c, reverse=d, tree=t))

        return open_tree_maximized(
            self.tree, "Rincian PO — Pivot Nomor #",
            setup_tags=lambda t: self._setup_tags(t),
            on_filter_setup=filter_setup,
            # v3.9.35 — anotasi status ↳ ikut dipasang di clone ⛶
            on_render_done=lambda t: self._apply_status_notes(t))

    def _apply_status_notes(self, tree=None):
        """v3.9.35 — pasang tag per-cell `po_status_note` (teks redup) ke
        sel STATUS (↳ …) di kolom Pemasok baris anak pertama tiap PO.

        v3.9.37 — diperluas ke SEMUA sel anotasi ↳:
        - kolom PEMASOK (↳ Status Pesanan + ↳ Keterangan PO — semua
          baris anak yang nilainya terisi);
        - kolom NOMOR # #0 (↳ Tgl/Jam Pembuatan — anak pertama).

        Dipanggil pasca-render (insert async) di tabel utama + clone ⛶.
        Tag per-cell ≠ tag baris — tidak pernah memengaruhi styling baris
        anak lain (mekanisme sama dgn minus merah per-cell view lain).
        Deteksi berbasis NILAI SEL (bukan posisi): baris anak kolom
        Pemasok hanya berisi anotasi (item tidak punya nilai pemasok),
        dan teks #0 anak hanya berisi anotasi ↳ (nomor PO ada di baris
        induk) — aman terhadap urutan/filter."""
        tree = tree if tree is not None else self.tree
        cells = []
        try:
            for po in tree.get_children(""):
                if po == "grand_total":
                    continue
                kids = tree.get_children(po)
                for k in kids:
                    # anotasi Tgl/Jam Pembuatan (↳ …) di kolom Nomor # #0
                    if str(tree.item(k, "text") or "").startswith("↳"):
                        cells.append((k, "#0"))
                    # anotasi Status/Keterangan (↳ …) di kolom Pemasok
                    try:
                        if tree.set(k, "Pemasok"):
                            cells.append((k, "Pemasok"))
                    except tk.TclError:
                        continue
        except tk.TclError:
            return
        apply_cell_tag(tree, "po_status_note", cells)

    # =========================================================================
    # HELPERS (identik versi lama)
    # =========================================================================
    @staticmethod
    def _fmt_num(val) -> str:
        """FIX C-03 (audit 2-c): format angka INDONESIA (1.234,5 · negatif
        kurung · 0 = '-') — dulu gaya EN "1,234.5"; nilai yang sama kini
        tampil konsisten dgn tabel sumber drill-down-nya."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            v = float(val)
        except (TypeError, ValueError):
            return str(val)
        if v == 0:
            return "-"
        if v == int(v):
            s = fmt_int_id(v)
        else:
            s = f"{v:,.1f}".replace(",", "X").replace(".", ",") \
                .replace("X", ".")
        if v < 0:
            return f"({s[1:]})"
        return s

    @staticmethod
    def _fmt_date(val) -> str:
        # v3.9.35 — FORMAT PANJANG Indonesia "01 Oktober 2026" (user:
        # "Format tanggal pakai 01 Oktober 2026 aja format panjang") —
        # nama bulan Indonesia manual (strftime %B = locale C → English).
        # FIX 35-c1 (RISK C6): NaT-safe tetap — NaT.strftime RAISES
        # ValueError di pandas 2.2.3 (to_datetime(errors="coerce") bisa
        # menghasilkan NaT) → satu baris NaT tidak mematikan tab.
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            if pd.isna(val):
                return ""
        except (TypeError, ValueError):
            pass
        d = val if hasattr(val, "strftime") else None
        if d is None:
            try:
                d = pd.to_datetime(val)
            except Exception:
                return str(val)
        try:
            return f"{d.day:02d} {_BULAN_ID[d.month - 1]} {d.year}"
        except (AttributeError, IndexError, TypeError, ValueError):
            return str(val)

    @staticmethod
    def _fmt_datetime(val) -> str:
        # v3.9.35 — format panjang + jam menit: "01 Oktober 2026 14:23"
        # (detik dibuang — kolom tersembunyi default, hemat lebar).
        # FIX 35-c1 (RISK C6): NaT-safe (lihat _fmt_date).
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        try:
            if pd.isna(val):
                return ""
        except (TypeError, ValueError):
            pass
        d = val if hasattr(val, "strftime") else None
        if d is None:
            try:
                d = pd.to_datetime(val)
            except Exception:
                return str(val)
        try:
            return (f"{d.day:02d} {_BULAN_ID[d.month - 1]} {d.year} "
                    f"{d.hour:02d}:{d.minute:02d}")
        except (AttributeError, IndexError, TypeError, ValueError):
            return str(val)
