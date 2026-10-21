"""
details_popup.py — Popup detail source rows Append1 (v3.1).

Muncul saat user double-click cell/baris di PivotTableView / DeviasiView /
LaporanDeviasiView. Fitur v3.1:
- COPY Nomor / Nomor PO: klik-kanan (menu konteks), Ctrl+C, atau
  double-click cell kolom Nomor / Nomor PO → langsung tersalin ke clipboard
- Copy semua Nomor / Nomor PO (unik) via menu konteks / tombol footer
- Filter Nama Barang menempel di header kolom (corong, Excel-like)
- Tombol ⛶ Layar Penuh: buka tabel popup dalam window besar
  (v3.9.32: HANYA jalur non-pivot; popup pivot ±90% layar tanpa tombol;
  v3.9.59 fix 2f-13: label kanonik ⛶='Layar Penuh' — dulu '⛶ Perbesar'…
  glyph clone-fullscreen dipasangkan label in-place)
- Loading overlay saat render
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

import contextlib
import pandas as pd

from .theme import (
    C_ACCENT_DARK,
    C_ACCENT_SOFT,
    C_BG,
    C_BORDER,
    C_CARD,
    C_HEADER,
    C_TEXT_MUTED,
    font,
    register_find_tags,
)
from .widgets import (
    CELL_TAGS_SUPPORTED,
    FLASH_MS,  # v3.9.59 — fix 2b-07: durasi flash TERSALIN seragam (2500ms)
    AccentButton,
    ColumnManager,
    GhostButton,
    HeaderFilter,
    LoadingOverlay,
    apply_cell_tag,
    attach_clone_filters,
    auto_fit_columns,
    copy_cell_region_tsv,  # v3.9.59 — fix 2d-05: Ctrl+C region sel ala Excel
    copy_tree_selection_tsv,  # v3.9.33 — AUDIT FIX 48-c (Ctrl+C multi-baris)
    enable_col_resize,
    enable_multi_select,
    fmt_int_id,
    identify_to_column,
    insert_tree_items,
    install_tree_find_binding,  # v3.9.64 — F-07: Ctrl+F aktif di popup
    kategori_match_mask,  # v3.9.54 — popup KATEGORI virtual (fix kosong)
    open_tree_maximized,
    run_async,
)

# Column definitions: (column_id, width, anchor)
COLUMNS = [
    ("Nama Barang", 140, "w"),
    ("NAMA RESTO", 80, "w"),
    ("Tanggal", 60, "e"),
    ("JENIS", 100, "w"),
    ("NILAI", 90, "e"),
    ("Nomor", 130, "w"),
    ("Nomor PO", 130, "w"),
    ("#Tgl/Jam Pembuatan IT", 140, "w"),
    ("KATEGORI", 80, "w"),
    ("SOURCE KIRIMAN", 100, "w"),
]

COL_IDS = [c[0] for c in COLUMNS]

# v3.9.54 (audit 8-a P0-1) — JENIS COMPUTED pivot: "6.PEMAKAIAN (COM)"
# dihitung _compute_com (base + IN − BK − SO; base = SA tgl-1 / SO(t−1))
# — TIDAK PERNAH menjadi nilai JENIS di data mentah append1 (vocab:
# SALDO AWAL / 1.SO / 2.SALDO AKHIR / 3.DEVIASI / 4.IN / 5.BARANG MASUK
# / 7.Selisih IN / 8.BARANG KELUAR / 9.ACR). Exact match popup = 0 baris
# → popup KOSONG saat double-click baris COM (mode Tanggal). Popup kini
# menampilkan baris PENYUSUN formulanya (SA/SO/IN/BK).
_COM_JENIS_LABEL = "6.PEMAKAIAN (COM)"
_COM_FORMULA_JENIS = ("SALDO AWAL", "1.SO", "4.IN", "8.BARANG KELUAR")


def _chrono_lt(a: int, b: int) -> bool:
    """FIX 6c-02 — urut kronologis tanggal app: -31 … -1 lalu 1 … 31
    (negatif = bulan lalu; mirror laporan_deviasi_view._chrono /
    deviasi_popup._chrono_key)."""
    ka = (0, -a) if a < 0 else (1, a)
    kb = (0, -b) if b < 0 else (1, b)
    return ka < kb


def _com_prev_global_tgl(data: pd.DataFrame, t: int):
    """FIX 6c-02 / 6e-04 — tanggal kolom GLOBAL sebelum ``t``.

    Kolom global = union tanggal baris 4 JENIS formula COM di SELURUH
    frame (mirror col_keys laporan_deviasi_view._compute_com_matrix /
    deviasi_popup._compute_com_series): so_prev(t) = SO pasangan di
    tanggal kolom global SEBELUM t (0 bila pasangan tak punya baris
    di sana) — bukan tanggal pair-sebelumnya. Return None bila tak ada
    tanggal sebelum t (t = kolom pertama → base com = 0; t == 1 dengan
    SA pasangan ditangani cabang pemanggil — SA ber-Tanggal 1)."""
    try:
        jenis_s = data["JENIS"].astype(str)
        tn = pd.to_numeric(
            data.loc[jenis_s.isin(_COM_FORMULA_JENIS), "Tanggal"],
            errors="coerce").dropna()
    except (KeyError, TypeError, ValueError):
        return None
    prev = None
    for v in tn.unique().tolist():
        try:
            iv = int(v)
        except (TypeError, ValueError):
            continue
        if _chrono_lt(iv, t) and (prev is None or _chrono_lt(prev, iv)):
            prev = iv
    return prev


def _tgl_lalu_label(t) -> str:
    """FIX 6e-05 — label tanggal konvensi app: '25•' (bulan lalu) / '25'.
    (mirror deviasi_popup._fmt_tanggal + heading kolom pivot_view)."""
    try:
        d = int(float(t))
    except (TypeError, ValueError):
        return str(t)
    return f"{-d}•" if d < 0 else str(d)


class DetailsPopup(tk.Toplevel):
    """Popup window menampilkan source rows untuk kombinasi cell pivot."""

    def __init__(self, parent, title: str, df: pd.DataFrame,
                 filter_info: str = "", show_maximize: bool = True):
        super().__init__(parent)
        self._title = title
        self._show_maximize = show_maximize
        self.title(f"Detail — {title}")
        # v3.9.32 — popup diperbesar ADAPTIF ±90% layar (user: "popup di
        # tab pivot ada deviasinya — terlalu kecil, besarkan lagi");
        # diposisikan tengah parent + clamp ke layar. Jalur pivot memakai
        # show_maximize=False (tombol ⛶ dihapus — popup sudah besar).
        try:
            sw = max(int(self.winfo_screenwidth()), 1024)
            sh = max(int(self.winfo_screenheight()), 640)
            # v3.9.42 — audit 61-d P3: clamp lebar/tinggi ≤ layar (min
            # 1100 di layar 1024 melebarkan popup MELAMPAUI layar) +
            # simpan utk skala kolom (isi lebar jendela — dulu fixed).
            pw = min(sw, max(1100, int(sw * 0.90)))
            ph = min(sh, max(540, int(sh * 0.86)))
            px = parent.winfo_rootx() + (parent.winfo_width() - pw) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - ph) // 2
            px = max(0, min(px, sw - pw))
            py = max(0, min(py, sh - ph))
            self.geometry(f"{pw}x{ph}+{px}+{py}")
            self._geom_w = pw
        except Exception:
            self.geometry("1100x540")
        self.minsize(800, 320)
        self.configure(bg=C_BG)

        # Modal — block parent sampai ditutup
        self.transient(parent)
        self.grab_set()

        # State
        self.df = df
        self._name_selected: set | None = None
        self._busy = False
        self._pending = False
        self._base_status = ""
        self._flash_after = None
        self._render_df: Optional[pd.DataFrame] = df
        # v3.9.2: minus merah PER CELL (kolom NILAI) — fallback Tk 8 per baris
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []

        # Build UI
        self._build_ui(title, filter_info)

        # v3.9.42 — audit 61-d P3: kolom DISKALA memenuhi lebar jendela
        # (pola popup 🧮 v3.9.41; dulu fixed-width → sisi kanan kosong).
        with contextlib.suppress(tk.TclError):
            _avail = int(getattr(self, "_geom_w", 0)) - 48
            _total = sum(w for _n, w, _a in COLUMNS)
            if _total > 0 and _avail > _total:
                _extra = _avail - _total
                for _n, _w, _a in COLUMNS:
                    self.tree.column(
                        _n, width=_w + int(_extra * _w / _total))

        # Render data
        self._render()

        # Focus + close on Escape
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())

    # =====================================================================
    # UI BUILD
    # =====================================================================
    def _build_ui(self, title: str, filter_info: str):
        # --- Header band gelap ---
        header = tk.Frame(self, bg=C_HEADER)
        header.pack(fill="x")
        head_in = tk.Frame(header, bg=C_HEADER)
        head_in.pack(fill="x", padx=16, pady=12)

        tk.Label(head_in, text="🔍 Detail Source Data", bg=C_HEADER,
                 fg="#5eead4", font=font(8, "bold")).pack(anchor="w")
        tk.Label(head_in, text=title, bg=C_HEADER, fg="#f1f5f9",
                 font=font(12, "bold"), wraplength=760,
                 justify="left").pack(anchor="w", pady=(2, 0))
        if filter_info:
            tk.Label(head_in, text=f"Filter aktif: {filter_info}",
                     bg=C_HEADER, fg="#94a3b8", font=font(9)).pack(
                anchor="w", pady=(2, 0))

        # Aksi di kanan band: ⛶ Layar Penuh (v3.9.32: HANYA jalur non-pivot
        # — popup pivot sudah ±90% layar, tombol dihapus per permintaan
        # user; v3.9.59 fix 2f-13: label kanonik ⛶='Layar Penuh') + ◱ Kolom
        # + ↔ Auto-Fit
        btn_fit = tk.Button(
            head_in, text="↔ Auto-Fit", command=self._auto_fit,
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
            activeforeground="#ffffff", bd=0, relief="flat",
            highlightthickness=0, cursor="hand2", font=font(9, "bold"),
            padx=12, pady=5)
        btn_fit.pack(side="right", anchor="ne", padx=(0, 6))
        btn_cols = tk.Button(
            head_in, text="◱ Kolom",
            command=lambda: self._colmgr.open_panel(),
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
            activeforeground="#ffffff", bd=0, relief="flat",
            highlightthickness=0, cursor="hand2", font=font(9, "bold"),
            padx=12, pady=5)
        btn_cols.pack(side="right", anchor="ne", padx=(0, 6))
        self._btn_max = None
        if self._show_maximize:
            btn_max = tk.Button(
                head_in, text="⛶ Layar Penuh", command=self._maximize,
                bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
                activeforeground="#ffffff", bd=0, relief="flat",
                highlightthickness=0, cursor="hand2", font=font(9, "bold"),
                padx=12, pady=5)
            btn_max.pack(side="right", anchor="ne")
            self._btn_max = btn_max

        # --- Body: tabel ---
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        card = tk.Frame(body, bg=C_CARD, highlightbackground=C_BORDER,
                        highlightthickness=1)
        card.pack(fill="both", expand=True)
        card_in = tk.Frame(card, bg=C_CARD)
        card_in.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(card_in, columns=COL_IDS, show="headings",
                                 selectmode="extended")

        for col_name, width, anchor in COLUMNS:
            self.tree.column(col_name, width=width, minwidth=50, anchor=anchor)
            # kolom Nomor / Nomor PO tanpa sort-click (heading dipakai filter
            # Nama Barang; copy via klik kanan / double-click)
            self.tree.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(card_in, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(card_in, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        card_in.grid_rowconfigure(0, weight=1)
        card_in.grid_columnconfigure(0, weight=1)

        self._setup_tags(self.tree)
        # v3.9.64 — FIX (audit 15-c F-07): Ctrl+F aktif DI DALAM popup
        # (Toplevel sendiri — bindtag-nya tak memuat binding root app).
        install_tree_find_binding(self, lambda: self.tree)

        # v3.4: drag tepi heading = resize lebar kolom; double-click tepi =
        # auto-fit (dipasang SEBELUM HeaderFilter supaya "break" efektif)
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        # loading overlay (stacking di atas tree)
        self.overlay = LoadingOverlay(card_in, "Menyiapkan detail…")

        # interaksi copy
        self.tree.bind("<Button-3>", self._on_context_menu, add="+")  # FIX B-04
        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04
        self.tree.bind("<Control-c>", self._on_copy_key)
        self.tree.bind("<Control-C>", self._on_copy_key)

        # filter Nama Barang menempel di header kolom
        self.header_filter = HeaderFilter(
            self.tree, "Nama Barang",
            get_values=self._name_values,
            on_apply=self._on_name_filter,
            label="Nama Barang")

        # v3.6: hide/unhide kolom (klik kanan heading / tombol ◱ Kolom)
        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filter.open_popup()
            if c == "Nama Barang" else None)

        # --- Footer: status + tombol ---
        foot = tk.Frame(self, bg=C_BG)
        foot.pack(fill="x", padx=12, pady=(0, 12))

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(foot, textvariable=self.status_var,
                                     bg=C_BG, fg=C_TEXT_MUTED, font=font(9))
        self.status_label.pack(side="left")

        btn_copy_nomor = GhostButton(
            foot, text="📋 Semua Nomor",
            command=lambda: self._copy_all_unique("Nomor"))
        btn_copy_nomor.pack(side="right", padx=(6, 0))
        btn_copy_po = GhostButton(
            foot, text="📋 Semua Nomor PO",
            command=lambda: self._copy_all_unique("Nomor PO"))
        btn_copy_po.pack(side="right", padx=(6, 0))

        AccentButton(foot, text="Tutup (Esc)", command=self.destroy).pack(
            side="right", padx=(6, 0))

    def _name_values(self) -> list:
        if self.df is None or self.df.empty or \
                "Nama Barang" not in self.df.columns:
            return []
        return self.df["Nama Barang"].dropna().astype(str).unique().tolist()

    def _on_name_filter(self, selected):
        self._name_selected = selected
        self._render()

    def _setup_tags(self, tree=None):
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("neg_cell", foreground="#dc2626")  # v3.9.2

    # =====================================================================
    # RENDER (async + batched)
    # =====================================================================
    def _render(self, sync: bool = False):
        if self._busy:
            self._pending = True
            return
        self._busy = True
        df = self.df

        def work():
            return self._prepare_rows(df, self._name_selected,
                                       per_cell=self._cell_tags)

        def done(payload):
            self._render_rows(payload)

        # FIX C-02/D-02 (audit 2-c/2-d): on_error — kelas fix B-01 v3.9.1
        # yang terlewat di popup ini: tanpa reset _busy, satu exception di
        # _prepare_rows menempel _busy=True selamanya → popup tampak beku,
        # semua render berikutnya (filter/reset) ditelan guard.
        def on_error(err):
            self._busy = False
            self._pending = False
            with contextlib.suppress(Exception):
                self.status_var.set(f"⚠ Gagal menyiapkan detail: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menyiapkan detail…", sync=sync,
                  on_error=on_error)

    @staticmethod
    def _prepare_rows(df: pd.DataFrame, name_selected: set | None,
                      per_cell: bool = False) -> dict:
        """Pure: filter + format baris → payload render (thread-safe).

        v3.9.2: per_cell=True (Tk 9) → minus dikumpulkan sebagai neg_cells
        [(iid, 'NILAI')] utk tag PER-CELL; False (Tk 8) → tag per baris
        (perilaku lama)."""
        if df is None or df.empty:
            return {"items": [], "status": "Tidak ada source data untuk "
                                           "kombinasi ini.", "total": 0}

        render_df = df
        # v3.9.13: seleksi kosong (set()) = 0 baris (semantik Excel) —
        # dulu truthiness menelan set() sebagai "tanpa filter".
        if name_selected is not None and "Nama Barang" in df.columns:
            render_df = df[df["Nama Barang"].astype(str).isin(name_selected)]

        if render_df.empty:
            return {"items": [], "status": "Tidak ada source data untuk "
                                           "kombinasi ini.", "total": 0}

        col_data = {}
        for col_name, _, _ in COLUMNS:
            if col_name in render_df.columns:
                col_data[col_name] = render_df[col_name].tolist()
            else:
                col_data[col_name] = [""] * len(render_df)

        items = []
        n = len(render_df)
        total_nilai = 0.0
        neg_cells = []   # v3.9.2 — per-cell minus (kolom NILAI)
        has_lalu = False  # FIX 6e-05 — ada tanggal bulan lalu (label •)
        for i in range(n):
            values = []
            has_negative = False
            for col_name, _, _ in COLUMNS:
                val = col_data[col_name][i]
                if col_name == "NILAI":
                    formatted, is_neg = DetailsPopup._fmt_nilai(val)
                    values.append(formatted)
                    if is_neg:
                        has_negative = True
                    try:
                        total_nilai += float(val) if val is not None and \
                            not pd.isna(val) else 0
                    except (TypeError, ValueError):
                        pass
                else:
                    _txt = DetailsPopup._fmt_cell(val, col_name)
                    values.append(_txt)
                    if col_name == "Tanggal" and _txt.endswith("•"):
                        has_lalu = True  # FIX 6e-05
            tags = []
            if has_negative:
                # v3.9.2: minus merah PER CELL (kolom NILAI saja) —
                # sebelumnya satu nilai minus membuat SELURUH BARIS merah
                if per_cell:
                    neg_cells.append((f"row_{i}", "NILAI"))
                else:
                    tags.append("negative")
            tags.append("evenrow" if i % 2 == 0 else "oddrow")
            items.append(("", f"row_{i}", {"values": values,
                                           "tags": tuple(tags)}))

        if total_nilai == int(total_nilai):
            total_str = fmt_int_id(int(total_nilai))
        else:
            total_str = f"{total_nilai:,.1f}".replace(",", "X").replace(
                ".", ",").replace("X", ".")
        # FIX C-03/C-10 (audit 2-c): format ID + 'rows' EN → 'baris'
        status = f"{n} baris · Total NILAI: {total_str}"
        if has_lalu:
            # FIX 6e-05 — legend konvensi '25•' (pola deviasi_popup footer)
            status += " · • = bulan lalu"
        return {"items": items, "status": status, "total": total_nilai,
                "render_df_len": n, "neg_cells": neg_cells}

    def _render_rows(self, payload: dict):
        self.tree.delete(*self.tree.get_children())
        self._base_status = payload["status"]
        self.status_label.configure(fg=C_TEXT_MUTED)
        self.status_var.set(payload["status"])
        # simpan df tampilan saat ini (untuk copy semua unik)
        self._render_df = self._apply_name_filter_df()
        self.header_filter.refresh_icon()
        self._neg_cells = payload.get("neg_cells", [])   # v3.9.2 per-cell

        def render_done():
            # v3.9.2: tag PER-CELL setelah semua baris ter-insert
            self._reapply_cell_tags(self.tree)
            self._busy = False
            if self._pending:
                self._pending = False
                self._render()

        insert_tree_items(self.tree, payload["items"], batch=400,
                          on_done=render_done)

    def _reapply_cell_tags(self, tree):
        """v3.9.2 — pasang ulang tag per-cell minus (juga utk clone ⛶).
        v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list kosong
        = clear overlay — render tanpa sel minus tidak meninggalkan
        label STALE)."""
        if self._cell_tags:
            apply_cell_tag(tree, "neg_cell", self._neg_cells)

    def _apply_name_filter_df(self) -> pd.DataFrame:
        df = self.df
        if df is None or df.empty:
            return df
        # v3.9.13: seleksi kosong (set()) = 0 baris — `is not None`,
        # bukan truthiness (set() kosong tetap filter AKTIF).
        if self._name_selected is not None and "Nama Barang" in df.columns:
            return df[df["Nama Barang"].astype(str).isin(self._name_selected)]
        return df

    # =====================================================================
    # COPY Nomor / Nomor PO
    # =====================================================================
    def _copy_to_clipboard(self, text, label: str):
        text = str(text or "").strip()
        if not text:
            self._flash_status("⚠ Tidak ada yang bisa di-copy (nilai kosong).")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        shown = text if len(text) <= 60 else text[:60] + "…"
        self._flash_status(f"📋 {label} TERSALIN ke clipboard: {shown}")

    def _flash_status(self, msg: str):
        if self._flash_after:
            try:
                self.after_cancel(self._flash_after)
            except Exception:
                pass
        self.status_var.set(msg)
        self.status_label.configure(fg=C_ACCENT_DARK)

        def restore():
            # FIX D-09 (audit 2-d): popup bisa ditutup < 3 detik — jangan
            # sentuh widget yang sudah mati (dulu TclError → traceback
            # noise di log konsol tiap kali popup cepat ditutup).
            if not self.winfo_exists():
                return
            self.status_var.set(self._base_status)
            self.status_label.configure(fg=C_TEXT_MUTED)

        # v3.9.59 — fix 2b-07 (agent B): 3000 literal → konstanta bersama
        # FLASH_MS (2500ms — seragam dgn app/widgets; feedback copy kini
        # sama durasinya di semua permukaan).
        self._flash_after = self.after(FLASH_MS, restore)

    def _on_context_menu(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            return
        try:
            # v3.9.33 — AUDIT FIX (48-c LOW): bila baris yang diklik SUDAH
            # bagian seleksi (multi-select) → PERTAHANKAN seleksi (perilaku
            # standar multi-select); dulu selection_set(iid) selalu
            # MENGECOLAPSKAN seleksi ke satu baris yang diklik.
            if iid not in tree.selection():
                tree.selection_set(iid)
            tree.focus(iid)
        except Exception:
            pass
        values = tree.item(iid, "values")
        if not values:
            return
        row = dict(zip(COL_IDS, values))
        nomor = str(row.get("Nomor", "") or "")
        nomor_po = str(row.get("Nomor PO", "") or "")

        def _lbl(s: str) -> str:
            s = s.strip()
            if not s:
                return "(kosong)"
            return s[:26] + ("…" if len(s) > 26 else "")

        menu = tk.Menu(self, tearoff=0, bg=C_CARD, fg=C_HEADER,
                       activebackground=C_ACCENT_SOFT,
                       activeforeground=C_ACCENT_DARK,
                       font=font(9), bd=0, relief="flat")
        menu.add_command(
            label=f"📋 Copy Nomor — {_lbl(nomor)}",
            command=lambda: self._copy_to_clipboard(nomor, "Nomor"))
        menu.add_command(
            label=f"📋 Copy Nomor PO — {_lbl(nomor_po)}",
            command=lambda: self._copy_to_clipboard(nomor_po, "Nomor PO"))
        menu.add_separator()
        menu.add_command(
            label="📋 Copy seluruh baris (tab-separated)",
            command=lambda: self._copy_row(iid, tree))
        menu.add_command(
            label="📋 Copy SEMUA Nomor (unik)",
            command=lambda: self._copy_all_unique("Nomor"))
        menu.add_command(
            label="📋 Copy SEMUA Nomor PO (unik)",
            command=lambda: self._copy_all_unique("Nomor PO"))
        menu.add_separator()
        if self._show_maximize:   # v3.9.32 — jalur pivot tanpa ⛶
            menu.add_command(label="⛶ Layar Penuh",
                             command=self._maximize)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _copy_row(self, iid, tree):
        values = tree.item(iid, "values")
        if not values:
            return
        self._copy_to_clipboard("\t".join(str(v) for v in values),
                                "Baris lengkap")

    def _copy_all_unique(self, col: str):
        df = self._render_df
        if df is None or df.empty or col not in df.columns:
            self._flash_status("Tidak ada data untuk di-copy.")
            return
        vals = df[col].dropna().astype(str).str.strip()
        vals = vals[vals != ""]
        uniq = sorted(set(vals.tolist()))
        if not uniq:
            self._flash_status("Tidak ada nilai untuk di-copy.")
            return
        self._copy_to_clipboard("\n".join(uniq),
                                f"{len(uniq)} nilai {col} (unik)")

    def _on_double_click(self, event):
        """Double-click cell Nomor / Nomor PO → langsung copy nilai cell."""
        tree = event.widget
        iid = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not iid or not col or col == "#0":
            return
        # v3.7 FIX (deep audit): resolve posisi-display → NAMA kolom
        # aktual — dulu memakai index posisi ke COL_IDS (urutan LOGIS) →
        # setelah kolom disembunyikan, copy mengambil nilai kolom yang
        # SALAH (mis. hide Source → double-click Nomor men-copy Source).
        col_name = identify_to_column(tree, col)
        if col_name in ("Nomor", "Nomor PO"):
            val = tree.set(iid, col_name)
            self._copy_to_clipboard(val, col_name)

    def _on_copy_key(self, _event):
        """Ctrl+C — copy Nomor baris terpilih (fallback Nomor PO).

        v3.9.33 — AUDIT FIX (48-c LOW): dulu hanya sel[0] padahal tree ini
        multi-select — seleksi >1 baris kini disalin SEMUA sebagai TSV
        (pola shared widgets.copy_tree_selection_tsv: header + satu baris
        per iid terpilih).
        v3.9.59 — AUDIT FIX 2d-05: binding Ctrl+C popup dipasang TANPA
        add='+' → MENGGANTI binding _copy_rows enable_multi_select (region
        sel ala Excel diutamakan di sana) — seleksi sel yang DI-HIGHLIGHT
        diacuhkan, Ctrl+C menyalin Nomor baris saja. Region aktif kini
        MENANG dulu (persis prioritas widgets._copy_rows), perilaku lama
        popup (multi-baris TSV / Nomor) tetap utk tanpa region.
        v3.9.59 — AUDIT FIX 2d-06: label flash sesuai kolom ASAL nilai
        (dulu klaim 'Nomor' padahal nilai fallback = Nomor PO)."""
        tree = self.tree
        # 2d-05 — region sel aktif (seleksi sel ala Excel) → copy REGION
        if getattr(tree, "_cellsel_active", False):
            n = copy_cell_region_tsv(tree)
            if n:
                self._flash_status(
                    f"📋 {n} baris region TERSALIN (tab-separated) "
                    f"ke clipboard.")
                return
        sel = tree.selection()
        if not sel:
            return
        if len(sel) > 1:
            n = copy_tree_selection_tsv(tree)
            if n:
                self._flash_status(
                    f"📋 {n} baris TERSALIN (tab-separated) ke clipboard.")
            return
        values = tree.item(sel[0], "values")
        if not values:
            return
        row = dict(zip(COL_IDS, values))
        # 2d-06 — label = kolom asal nilai yang benar-benar disalin
        label = "Nomor"
        val = str(row.get("Nomor", "") or "")
        if not val:
            label = "Nomor PO"
            val = str(row.get("Nomor PO", "") or "")
        if val:
            self._copy_to_clipboard(val, label)

    # =====================================================================
    # ⛶ PERBESAR
    # =====================================================================
    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten."""
        auto_fit_columns(self.tree)

    def _maximize(self):
        def filter_setup(new_tree):
            # v3.6: funnel Nama Barang jalan juga di window besar
            # FIX B-02 (audit 2-b): on_after_filter + on_render_done — tag
            # minus per-cell dipasang ulang setelah filter clone REBUILD;
            # dulu minus merah TIDAK PERNAH muncul di clone (kedua callback
            # tidak dipass — fix v3.9.5 19-a #3 terlewat di popup ini).
            attach_clone_filters(
                new_tree, ["Nama Barang"],
                get_values=self._name_values,
                on_after_filter=lambda t=new_tree:
                    self._reapply_cell_tags(t))

        return open_tree_maximized(
            self.tree, f"Detail — {self._title}",
            setup_tags=lambda t: self._setup_tags(t),
            on_context_menu=self._on_context_menu,
            on_double_click=self._on_double_click,
            on_filter_setup=filter_setup,
            on_render_done=self._reapply_cell_tags)

    # =====================================================================
    # FORMAT (identik versi lama)
    # =====================================================================
    @staticmethod
    def _fmt_nilai(val):
        """Format NILAI: separator ribuan, negatif dalam kurung, 1 desimal.
        FIX C-03 (audit 2-c): format INDONESIA (1.234,5 · (1.234,5)) — dulu
        EN "1,234.5"; popup ini drill-down dari view berformat Indonesia,
        nilai sama harus tampil sama."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "", False
        try:
            v = float(val)
        except (TypeError, ValueError):
            return str(val), False
        is_neg = v < 0
        if v == 0:
            return "-", False
        if v == int(v):
            s = fmt_int_id(v)
        else:
            s = f"{v:,.1f}".replace(",", "X").replace(".", ",") \
                .replace("X", ".")
        if is_neg:
            return f"({s[1:]})", True
        return s, False

    @staticmethod
    def _fmt_cell(val, col_name: str) -> str:
        """Format cell value for display (identik versi lama)."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        if col_name in ("#Tgl/Jam Pembuatan IT",):
            if hasattr(val, "strftime"):
                return val.strftime("%d/%m/%Y %H:%M:%S")
            try:
                return pd.to_datetime(val).strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                return str(val)
        if col_name == "Tanggal":
            # FIX 6e-05 — konvensi app: bulan lalu '25•' (dulu mentah
            # '-25' — terlihat seperti data error; mirror deviasi_popup
            # _fmt_tanggal + heading kolom pivot_view + legend footer).
            try:
                d = int(float(val))
                return f"{-d}•" if d < 0 else str(d)
            except (TypeError, ValueError):
                return str(val)
        return str(val)


def show_details_popup(parent, data: pd.DataFrame, nama_barang: str = None,
                        jenis: str = None, tanggal=None,
                        filters: dict = None, show_maximize: bool = True,
                        tgl_range=None):
    """Filter data + show popup.

    v3.9.3: tanpa ``data.copy()`` upfront — setiap filter boolean sudah
    menghasilkan DataFrame baru, dan ``reset_index(drop=True)`` di ujung
    selalu mengembalikan objek baru (hemat ~10ms + memori di 200k baris).
    v3.9.32: show_maximize=False utk jalur PIVOT (popup sudah ±90% layar
    — tombol ⛶ dihapus per permintaan user).
    v3.9.54 (audit 8-a): (1) kolom KATEGORI virtual (gabungan default /
    '(Tanpa Kategori)' / legacy 'Deviasi') → mask kanonik
    kategori_match_mask — semantik identik jalur tampilan view (dulu
    exact match = popup KOSONG); (2) JENIS '6.PEMAKAIAN (COM)'
    (COMPUTED — tak pernah ada di data mentah) → popup menampilkan
    baris PENYUSUN formula (dulu exact match = 0 baris); (3) param
    tgl_range=(t1, t2) — rentang tanggal tampilan pivot diteruskan ke
    popup (parity _compute_payload tnum.between — dulu popup mengabaikan
    rentang → baris di luar rentang ikut tampil).
    """
    if data is None or data.empty:
        popup = DetailsPopup(parent, "Tidak ada data", pd.DataFrame(),
                             show_maximize=show_maximize)
        return popup

    df = data

    # v3.9.54 — catatan filter-info opsional (formula COM / rentang tgl)
    _formula_note = None
    _range_note = None
    # FIX 6c-02 / 6e-04 — tanggal kolom-global SEBELUM t (base formula
    # COM) utk cabang JENIS COMPUTED + tanggal; None = tanpa ekspansi.
    _com_prev_tgl = None

    # Build title parts
    title_parts = []
    if nama_barang:
        df = df[df["Nama Barang"].astype(str) == str(nama_barang)]
        title_parts.append(nama_barang)
    if jenis:
        if str(jenis) == _COM_JENIS_LABEL:
            # v3.9.54 FIX (audit 8-a P0-1) — baris 6.PEMAKAIAN (COM) di
            # pivot adalah COMPUTED (_compute_com: base + IN − BK − SO) —
            # nilainya TIDAK PERNAH menjadi JENIS di data mentah append1
            # → exact match lama = popup KOSONG ("Tidak ada source data
            # untuk kombinasi ini"). Popup kini menampilkan baris
            # PENYUSUN formula (SA/SO/IN/BK) + keterangan di filter info.
            df = df[df["JENIS"].astype(str).isin(_COM_FORMULA_JENIS)]
            title_parts.append(str(jenis))
            # FIX 6c-02 / 6e-04 (audit 6-c LOW / 6-e LOW) — filter SATU
            # tanggal membuat baris BASE formula hilang utk t>1:
            # COM(t) = SO(t−1) + IN(t) − BK(t) − SO(t) tak bisa
            # direkonstruksi dari popup (SO(24) penentu COM(25) minus
            # tidak pernah tampil). Kini baris 1.SO di tanggal kolom
            # GLOBAL sebelum t ikut ditampilkan (SALDO AWAL — base t=1 —
            # sudah terfilter di t=1), + catatan filter-info jujur
            # (SA tidak diklaim utk t>1).
            _t_probe = None
            if tanggal is not None:
                try:
                    _t_probe = int(tanggal)
                except (TypeError, ValueError):
                    _t_probe = None
            if _t_probe is not None and _t_probe != 1:
                _com_prev_tgl = _com_prev_global_tgl(data, _t_probe)
            if _com_prev_tgl is not None:
                # catatan sementara — finalisasi SETELAH semua filter
                # (NAMA RESTO bisa membuang baris base → klaim diubah
                # jujur ke 'base 0'; lihat bawah).
                _formula_note = "_COM_BASE_PENDING_"
            elif _t_probe is not None and _t_probe != 1:
                _formula_note = (
                    "JENIS=SO+IN+BK (formula COM: base 0 — tidak ada "
                    "tanggal sebelumnya)")
            if _formula_note is None:
                _formula_note = "JENIS=SA+SO+IN+BK (formula COM)"
        else:
            df = df[df["JENIS"].astype(str) == str(jenis)]
            title_parts.append(jenis)
    if tanggal is not None:
        try:
            tgl_int = int(tanggal)
            if _com_prev_tgl is not None:
                # FIX 6c-02 / 6e-04 — longgarkan filter tanggal HANYA utk
                # 1.SO: baris base SO(t−1) ikut tampil.
                _tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
                _so_m = df["JENIS"].astype(str) == "1.SO"
                df = df[(_so_m & _tnum.isin([tgl_int, _com_prev_tgl]))
                        | (~_so_m & (_tnum == tgl_int))]
            else:
                df = df[pd.to_numeric(df["Tanggal"], errors="coerce")
                        == tgl_int]
            title_parts.append(f"Tgl {tgl_int}")
        except (TypeError, ValueError):
            pass

    # v3.9.54 FIX (audit 8-a P1-2) — rentang tanggal tampilan pivot
    # (parity _compute_payload: tnum.between(t1, t2), kedua mode);
    # dulu popup mengabaikan rentang → baris di luar rentang yang
    # difilter tabel tetap muncul di popup.
    if tgl_range is not None:
        try:
            _t1, _t2 = int(tgl_range[0]), int(tgl_range[1])
            if _t1 > _t2:
                _t1, _t2 = _t2, _t1
            if _com_prev_tgl is not None:
                # FIX 6c-02 / 6e-04 — baris BASE SO(t−1) berboleh DI LUAR
                # rentang tampilan (base bukan bagian rentang — tanpa ini
                # rentang 4..6 membuang SO(3) yang justru penentu COM(4)).
                _tnum = pd.to_numeric(df["Tanggal"], errors="coerce")
                _so_m = df["JENIS"].astype(str) == "1.SO"
                df = df[((_tnum == _com_prev_tgl) & _so_m)
                        | _tnum.between(_t1, _t2)]
            else:
                df = df[pd.to_numeric(df["Tanggal"], errors="coerce")
                        .between(_t1, _t2)]
            _range_note = f"Tgl {_t1}..{_t2}"
        except (TypeError, ValueError, IndexError):
            _range_note = None

    # Apply additional filters (from active pivot filters)
    filter_info_parts = []
    if _formula_note == "_COM_BASE_PENDING_":
        # FIX 6c-02 / 6e-04 — finalisasi catatan formula SETELAH semua
        # filter (klaim baris BASE hanya bila baris 1.SO di tanggal base
        # benar-benar tampil — pasangan/resto tanpa SO di t−1 → base
        # com = 0, tak ada baris untuk diklaim).
        _prev_lbl = _tgl_lalu_label(_com_prev_tgl)
        try:
            _tn = pd.to_numeric(df["Tanggal"], errors="coerce")
            _has_base_row = bool(
                ((df["JENIS"].astype(str) == "1.SO")
                 & (_tn == _com_prev_tgl)).any())
        except (KeyError, TypeError, ValueError):
            _has_base_row = False
        if _has_base_row:
            _formula_note = (
                f"JENIS=SO+IN+BK + SO {_prev_lbl} BASE "
                "(formula COM: SO(t−1)+IN−BK−SO)")
        else:
            _formula_note = (
                f"JENIS=SO+IN+BK (formula COM: base 0 — "
                f"pasangan tanpa SO {_prev_lbl})")
    for _note in (_formula_note, _range_note):
        if _note:
            filter_info_parts.append(_note)
    if filters:
        for col, val in filters.items():
            if not val or val == "(All)" or col not in df.columns:
                continue
            if col == "KATEGORI":
                # v3.9.54 FIX — POPUP PIVOT KOSONG saat double-click
                # (user: "ADA BUG di pop up pivot tabel yang kosong ketika
                # aku double klik"): seleksi KATEGORI combobox view bisa
                # berupa entri VIRTUAL — entri gabungan DEFAULT
                # KATEGORI_DEFAULT_LABEL (sejak v3.9.49),
                # KATEGORI_BLANK_LABEL '(Tanpa Kategori)', legacy
                # 'Deviasi' (passthrough blank) — exact match lama = 0
                # baris utk entri virtual. Mask kanonik kategori_match_mask
                # = semantik IDENTIK jalur tampilan view (popup kini
                # menampilkan persis baris yang tabel tampilkan).
                m = kategori_match_mask(df["KATEGORI"], val)
                if m is None:
                    continue
                df = df[m]
            else:
                df = df[df[col].astype(str) == str(val)]
            filter_info_parts.append(f"{col}={val}")

    title = " / ".join(title_parts) if title_parts else "All Data"
    filter_info = ", ".join(filter_info_parts) if filter_info_parts else ""

    popup = DetailsPopup(parent, title, df.reset_index(drop=True),
                         filter_info, show_maximize=show_maximize)
    return popup
