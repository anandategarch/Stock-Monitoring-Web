"""
deviasi_popup.py — Popup RINGKAS tab Deviasi GR/PCS (v3.9.18).

v3.9.20 (deep audit 34-b/fix 35-b): popup memfilter SATUAN (angka =
baris GR/PCS yang DIKLIK — dulu menjumlah lintas satuan) + _chrono_key
float-safe (urutan 25•..31• benar utk Tanggal float64).

Permintaan user: "pop up di deviasi GR ataupun PCS hanya tampilkan:
nama barang, nama resto, nilai saldo akhir, nilai SO, nilai IN,
nilai deviasi."

v3.9.22 (permintaan user: "Pop up di tab Deviasi GR dan PCS ada Nomor
nya juga Misal IT...... atau RI......"): kolom NOMOR DOKUMEN IN per
tanggal (IT. = pemindahan 42.05, RI. = penerimaan 32.24; >1 dokumen
digabung koma, didedup + diurut).

v3.9.25 (permintaan user: "POP UP DI tab deviasi gr dan deviasi pcs
perbesar lagi dan tambah kolom nomor po dan COM"): jendela diperbesar
880×480 → 1180×640 (judul wraplength ikut melebar) + DUA kolom baru:
- "Nomor PO" — nomor pesanan pembelian (PO......) baris 4.IN per
  tanggal, didedup + diurut (pola kolom Nomor v3.9.22);
- "COM" — pemakaian harian per tanggal, FORMULA IDENTIK baris
  6.PEMAKAIAN (COM) tab Pivot / 🚨 Anomali COM (port
  laporan_deviasi_view._compute_com_matrix → _compute_com_series;
  kolom tanggal GLOBAL union 4 JENIS — parity 48/48 nilai):
      com(t) = so_prev(t) + IN(t) − BK(t) − SO(t)
  so_prev(t) = SO pasangan di tanggal kolom global sebelumnya
  (SALDO AWAL/1.SO/4.IN/8.BARANG KELUAR — kolom pertama 0), tanggal 1
  memakai SALDO AWAL pasangan bila ada (audit fix v3.9.5), fallback
  so_prev. Tanggal yang TIDAK ada di kolom global (mis. hanya baris
  2.SALDO AKHIR) → COM kosong (tab lain juga tak punya nilainya).
  Dihitung DALAM grup satuan yang diklik (pola FIX 35-b).

Mengganti popup source rows (details_popup.DetailsPopup — JENIS/Nomor/
Nomor PO/#Tgl-Jam/KATEGORI/SOURCE KIRIMAN) yang DULU terbuka dari tab
Deviasi GR/PCS:

- NAMA BARANG + NAMA RESTO tampil di judul popup (dua-duanya).
- Tabel ringkas PER TANGGAL — 8 kolom (v3.9.25):
    Tanggal · Saldo Akhir (2.SALDO AKHIR / sistem) · SO (1.SO) ·
    IN (4.IN) · Nomor (dokumen IN — v3.9.22) · Nomor PO (pesanan
    pembelian — v3.9.25) · COM (pemakaian harian — v3.9.25) ·
    Deviasi (= SO − Saldo Akhir, identik kolom Deviasi tab Deviasi
    GR/PCS & JENIS 3.DEVIASI pipeline).
- Baris Tanggal H diberi latar lembut (#fef3c7 — sama dgn highlight
  kolom Deviasi/SO_H di tabel utama v3.9.18) supaya mudah ditemukan.
- Tanggal bulan lalu (negatif) diberi label '25•' (konvensi pivot_view
  — '• = bulan lalu', urut kronologis 25•…31• lalu 1…31).
- Minus merah PER CELL (tag cell Tk 9 — fallback Tk 8 tag baris,
  pola v3.9.2). Popup source rows LAMA tetap dipakai tab lain
  (Pivot/Laporan) — tidak tersentuh.
"""
import tkinter as tk
from tkinter import ttk

import numpy as np
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
    GhostButton,
    apply_cell_tag,
    auto_fit_columns,
    copy_cell_region_tsv,  # v3.9.59 — 2d-03/2d-05: region sel ala Excel
    copy_tree_selection_tsv,  # v3.9.59 — 2d-03: Ctrl+C multi-baris TSV
    enable_col_resize,
    enable_multi_select,
    fmt_int_id,
    identify_to_column,  # v3.9.59 — 2d-03: posisi display → nama kolom
    install_tree_find_binding,  # v3.9.64 — F-07: Ctrl+F aktif di popup
)

# (column_id, width, anchor) — persis daftar user: saldo akhir, SO, IN,
# deviasi (+ kolom Tanggal sbg sumbu baris; barang & resto di judul).
# v3.9.22 — kolom Nomor (permintaan user: "Pop up di tab Deviasi GR dan
# PCS ada Nomor nya juga Misal IT...... atau RI......"): nomor dokumen
# transaksi IN (IT. = pemindahan 42.05 / RI. = penerimaan 32.24) per
# tanggal — gabungan bila >1 dokumen.
# v3.9.25 — kolom Nomor PO (permintaan user: "tambah kolom nomor po dan
# COM"): nomor pesanan pembelian baris 4.IN per tanggal (pola Nomor) +
# kolom COM (pemakaian harian — formula identik Anomali COM).
# v3.9.22 — kolom Nomor (permintaan user: "Pop up di tab Deviasi GR dan
# PCS ada Nomor nya juga Misal IT...... atau RI......"): nomor dokumen IN
# per tanggal (IT. = pemindahan 42.05, RI. = penerimaan 32.24; >1 dokumen
# digabung koma, didedup + diurut).
# v3.9.25 — kolom Nomor PO (permintaan user: "tambah kolom nomor po dan
# COM"): nomor pesanan pembelian baris 4.IN per tanggal (pola Nomor) +
# kolom COM (pemakaian harian — formula identik Anomali COM).
# v3.9.55 — URUTAN KOLOM (user: "Urutan kolom di pop up deviasi GR dan
# PCS: Tanggal, SO, Saldo Akhir, Deviasi, COM, IN, Nomor, Nomor PO"):
# Tanggal → SO → Saldo Akhir → Deviasi → COM → IN → Nomor → Nomor PO
# (dulu Tanggal, Saldo Akhir, SO, IN, Nomor, Nomor PO, COM, Deviasi).
COLUMNS = [
    ("Tanggal", 76, "e"),
    ("SO", 110, "e"),
    ("Saldo Akhir", 110, "e"),
    ("Deviasi", 110, "e"),
    ("COM", 100, "e"),
    ("IN", 110, "e"),
    ("Nomor", 200, "w"),
    ("Nomor PO", 190, "w"),
]

COL_IDS = [c[0] for c in COLUMNS]

_H_ROW_BG = "#fef3c7"   # sama dgn HIGHLIGHT_BG deviasi_view (v3.9.18)

_JENIS_SALDO = "2.SALDO AKHIR"
_JENIS_SO = "1.SO"
_JENIS_IN = "4.IN"

# v3.9.25 — JENIS input formula COM (persis jenis_needed
# laporan_deviasi_view._compute_com_matrix / pivot 6.PEMAKAIAN).
_JENIS_SA = "SALDO AWAL"
_JENIS_BK = "8.BARANG KELUAR"
_COM_JENIS = (_JENIS_SA, _JENIS_SO, _JENIS_IN, _JENIS_BK)

# FIX 6e-PERF (audit 6-e perf note: 95-125 ms SINKRON di main thread per
# double-click @ ~216k baris) — lookup pasangan VEKTOR via factorize
# astype(str) + cache per IDENTITAS objek DataFrame (idiom pipeline
# immutable-copy: semua view menerima objek append1_df yang SAMA → cache
# hit lintas GR/PCS + double-click berturut-turut; guard `is not df` ala
# _cached_data di view — data berganti → cache invalid otomatis).
# Mask lama df[col].astype(str) == value (objek == per ~216k baris ≈
# 10-14 ms × 6-7 panggilan = mayoritas waktu popup) diganti kode int
# (codes == i ≈ 0,1 ms). Hasil IDENTIK: factorize dijalankan ATAS series
# astype(str) → kecocokan string-nya sama persis dgn == versi lama.
# Semua pemanggil (handler double-click / test) berjalan di main thread
# — cache modul tunggal aman.
_PERF_CACHE: dict = {"df": None, "codes": {}, "com_col_keys": None}


def _perf_state(df: pd.DataFrame) -> dict:
    """FIX 6e-PERF — state cache utk objek df ini (reset saat identitas
    berganti)."""
    if _PERF_CACHE["df"] is not df:
        _PERF_CACHE["df"] = df
        _PERF_CACHE["codes"] = {}
        _PERF_CACHE["com_col_keys"] = None
    return _PERF_CACHE


def _col_codes(df: pd.DataFrame, name: str):
    """FIX 6e-PERF — (codes ndarray, {nilai_str: kode}) utk kolom
    astype(str) — di-cache per identitas df."""
    st = _perf_state(df)
    ent = st["codes"].get(name)
    if ent is None:
        s = df[name].astype(str)
        codes, uniques = pd.factorize(s)
        ent = (codes, {v: i for i, v in enumerate(uniques.tolist())})
        st["codes"][name] = ent
    return ent


def _col_code_mask(df: pd.DataFrame, name: str, value) -> np.ndarray:
    """FIX 6e-PERF — mask boolean ndarray kolom == str(value)
    (IDENTIK df[name].astype(str) == str(value), via kode factorize;
    nilai tak ada → semua-False, sama seperti == versi lama)."""
    codes, lut = _col_codes(df, name)
    i = lut.get(str(value))
    if i is None:
        return np.zeros(codes.shape, dtype=bool)
    return codes == i


def _col_isin_mask(df: pd.DataFrame, name: str, values) -> np.ndarray:
    """FIX 6e-PERF — mask boolean ndarray kolom astype(str) ∈ values
    (IDENTIK df[name].astype(str).isin(values))."""
    codes, lut = _col_codes(df, name)
    ids = [lut[v] for v in values if v in lut]
    if not ids:
        return np.zeros(codes.shape, dtype=bool)
    return np.isin(codes, ids)


def _com_col_keys(df: pd.DataFrame) -> list:
    """FIX 6e-PERF — kolom tanggal GLOBAL union 4 JENIS COM (persis
    col_keys _compute_com_series versi lama: sorted set to_numeric
    Tanggal baris 4 JENIS, kunci _chrono_key) — di-cache per identitas
    df (deterministik per data)."""
    st = _perf_state(df)
    if st["com_col_keys"] is None:
        m = _col_isin_mask(df, "JENIS", _COM_JENIS)
        tn = pd.to_numeric(df.loc[m, "Tanggal"], errors="coerce")
        st["com_col_keys"] = sorted(set(tn.dropna().tolist()),
                                     key=_chrono_key)
    return st["com_col_keys"]


class DeviasiPopup(tk.Toplevel):
    """Popup ringkas: nilai kunci per Tanggal utk 1 pasangan (barang, resto)."""

    def __init__(self, parent, title: str, rows: pd.DataFrame,
                 h_label: str = ""):
        super().__init__(parent)
        self._title = title
        self.title(f"Detail Deviasi — {title}")
        try:
            # v3.9.25: 880×480 → 1180×640 (permintaan user "perbesar
            # lagi" + 2 kolom baru Nomor PO & COM).
            # v3.9.33 — AUDIT FIX (48-c MEDIUM): ukuran ADAPTIF + clamp
            # posisi KEDUA SISI (mirror DetailsPopup v3.9.32) — dulu
            # fixed 1180×640 hanya clamp batas 0 → di layar kecil popup
            # melebihi layar / posisi off-screen kanan-bawah.
            # v3.9.42 — audit 61-d P3: cap 1180/640 → 2200/1000 — cap lama
            # membuat popup TIDAK proporsional di monitor >1300px (1920 →
            # 1180 = 61% layar; kelas keluhan user "popup kurang besar").
            sw = max(int(self.winfo_screenwidth()), 1024)
            sh = max(int(self.winfo_screenheight()), 640)
            pw = min(2200, int(sw * 0.90))
            ph = min(1000, int(sh * 0.86))
            px = parent.winfo_rootx() + (parent.winfo_width() - pw) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - ph) // 2
            px = max(0, min(px, sw - pw))
            py = max(0, min(py, sh - ph))
            self.geometry(f"{pw}x{ph}+{px}+{py}")
            self._geom_w = pw   # v3.9.42 — utk skala kolom (isi lebar)
        except Exception:
            self.geometry("1180x640")
        self.minsize(820, 340)
        self.configure(bg=C_BG)

        # Modal — block parent sampai ditutup (pola DetailsPopup)
        self.transient(parent)
        self.grab_set()

        self.rows = rows
        self._h_label = h_label
        # v3.9.2 (pola): minus merah PER CELL — fallback Tk 8 tag baris
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        # v3.9.59 — AUDIT FIX 2d-03: state flash status copy (pola
        # DetailsPopup — dulu Ctrl+C/TANPA menu klik-kanan & tombol copy,
        # fitur copy praktis tak terdiscover di popup ini).
        self._base_status = ""
        self._flash_after = None

        self._build_ui(title)

        # v3.9.42 — audit 61-d P3: kolom DISKALA memenuhi lebar jendela
        # (pola popup 🧮 v3.9.41 — dulu fixed-width → sisi kanan jendela
        # kosong abu di monitor besar; kelas keluhan 'kurang lebar').
        import contextlib as _cl42
        with _cl42.suppress(tk.TclError):
            _avail = int(getattr(self, "_geom_w", 0)) - 48
            _total = sum(w for _n, w, _a in COLUMNS)
            if _total > 0 and _avail > _total:
                _extra = _avail - _total
                for _n, _w, _a in COLUMNS:
                    self.tree.column(
                        _n, width=_w + int(_extra * _w / _total))

        self._render()

        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())

    # =====================================================================
    # UI
    # =====================================================================
    def _build_ui(self, title: str):
        # --- Header band gelap (pola DetailsPopup) ---
        header = tk.Frame(self, bg=C_HEADER)
        header.pack(fill="x")
        head_in = tk.Frame(header, bg=C_HEADER)
        head_in.pack(fill="x", padx=16, pady=12)

        tk.Label(head_in, text="🔍 Detail Deviasi", bg=C_HEADER,
                 fg="#5eead4", font=font(8, "bold")).pack(anchor="w")
        # judul = NAMA BARANG — NAMA RESTO (dua-duanya, permintaan user)
        title_lbl = tk.Label(head_in, text=title, bg=C_HEADER,
                             fg="#f1f5f9", font=font(12, "bold"),
                             wraplength=1020, justify="left")
        title_lbl.pack(anchor="w", pady=(2, 0))
        # v3.9.59 — AUDIT FIX 2d-07: wraplength ADAPTIF (dulu fixed 1020
        # — jendela bisa diciutkan sampai minsize 820: judul panjang
        # berhenti wrap & terpotong kanan; di monitor lebar wrap terlalu
        # dini). Bind <Configure> popup → wraplength mengikuti lebar.
        # RESUME-D: bind di TOPLEVEL menangkap event <Configure> SEMUA
        # widget turunan (bindtags default memuat toplevel) — e.width bisa
        # = lebar tombol/scrollbar anak → wraplength kacau + loop layout
        # (probe fd_popup2 hang saat resize). Guard e.widget is self.
        def _on_title_cfg(e, _lbl=title_lbl):
            if e.widget is not self:
                return   # Configure anak (btn/scrollbar) — bukan popup
            try:
                _lbl.configure(
                    wraplength=max(300, min(1020, e.width - 60)))
            except tk.TclError:
                pass
        self.bind("<Configure>", _on_title_cfg, add="+")

        btn_fit = tk.Button(
            head_in, text="↔ Auto-Fit", command=self._auto_fit,
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
            activeforeground="#ffffff", bd=0, relief="flat",
            highlightthickness=0, cursor="hand2", font=font(9, "bold"),
            padx=12, pady=5)
        btn_fit.pack(side="right", anchor="ne")

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
            self.tree.column(col_name, width=width, minwidth=50,
                             anchor=anchor)
            self.tree.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(card_in, orient="vertical",
                            command=self.tree.yview)
        hsb = ttk.Scrollbar(card_in, orient="horizontal",
                            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        card_in.grid_rowconfigure(0, weight=1)
        card_in.grid_columnconfigure(0, weight=1)

        self._setup_tags(self.tree)
        # v3.9.64 — FIX (audit 15-c F-07): Ctrl+F aktif DI DALAM popup
        # (Toplevel sendiri — bindtag-nya tak memuat binding root app).
        install_tree_find_binding(self, lambda: self.tree)
        # v3.4 (pola): drag tepi heading = resize; double-click = auto-fit
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        # v3.9.59 — AUDIT FIX 2d-03: interaksi COPY (port pola DetailsPopup
        # — menu klik-kanan 5-perintah + Ctrl+C + double-click cell + tombol
        # footer 📋 + flash TERSALIN; popup ini MEMAKAI kolom Nomor & Nomor
        # PO jadi paritas interaksi dgn popup kembar seharusnya ada).
        self.tree.bind("<Button-3>", self._on_context_menu, add="+")
        self.tree.bind("<Double-1>", self._on_double_click, add="+")
        # bind TANPA add='+' mengganti binding _copy_rows
        # enable_multi_select — _on_copy_key memprioritaskan region sel
        # dulu (fix 2d-05) supaya perilaku Ctrl+C tidak menyimpang dari
        # tabel lain (region aktif → copy region, bukan Nomor baris).
        self.tree.bind("<Control-c>", self._on_copy_key)
        self.tree.bind("<Control-C>", self._on_copy_key)

        # --- Footer: status + tombol ---
        foot = tk.Frame(self, bg=C_BG)
        foot.pack(fill="x", padx=12, pady=(0, 12))

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(foot, textvariable=self.status_var,
                                     bg=C_BG, fg=C_TEXT_MUTED, font=font(9))
        self.status_label.pack(side="left")

        # v3.9.59 — 2d-03: tombol footer copy SEMUA nilai unik (pola
        # DetailsPopup; label & istilah identik).
        btn_copy_nomor = GhostButton(
            foot, text="📋 Semua Nomor",
            command=lambda: self._copy_all_unique("Nomor"))
        btn_copy_nomor.pack(side="right", padx=(6, 0))
        btn_copy_po = GhostButton(
            foot, text="📋 Semua Nomor PO",
            command=lambda: self._copy_all_unique("Nomor PO"))
        btn_copy_po.pack(side="right", padx=(6, 0))
        AccentButton(foot, text="Tutup (Esc)",
                     command=self.destroy).pack(side="right", padx=(6, 0))

    def _setup_tags(self, tree=None):
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("neg_cell", foreground="#dc2626")  # v3.9.2 pola
        # v3.9.18 — baris Tanggal H (satu-satunya tag utk baris H:
        # TANPA evenrow — tidak ada konflik opsi background antar tag)
        tree.tag_configure("h_row", background=_H_ROW_BG)

    # =====================================================================
    # RENDER (sync — tabel kecil ≤ ~62 baris)
    # =====================================================================
    def _render(self):
        self.tree.delete(*self.tree.get_children())
        self._neg_cells = []
        rows = self.rows
        n = len(rows)

        if n == 0:
            self._base_status = "Tidak ada data utk kombinasi ini."
            self.status_var.set(self._base_status)
            return

        for i, rec in enumerate(rows.to_dict("records")):
            # v3.9.22 — kolom Nomor ikut (posisi mengikuti COLUMNS)
            values = [rec.get(c, "") for c in COL_IDS]
            tags = []
            if self._h_label and rec["Tanggal"] == self._h_label:
                tags.append("h_row")       # baris Tanggal H — latar lembut
            else:
                tags.append("evenrow" if i % 2 == 0 else "oddrow")
            has_neg = False
            # v3.9.25 — COM ikut minus merah per-cell (kolom numerik)
            for col in ("Saldo Akhir", "SO", "IN", "COM", "Deviasi"):
                if _is_neg_display(rec.get(col, "")):
                    has_neg = True
                    if self._cell_tags:
                        self._neg_cells.append((f"row_{i}", col))
            if has_neg and not self._cell_tags:
                tags.append("negative")     # fallback Tk 8 — tag baris
            self.tree.insert("", "end", iid=f"row_{i}", values=values,
                             tags=tuple(tags))

        # v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list kosong
        # = clear overlay).
        if self._cell_tags:
            apply_cell_tag(self.tree, "neg_cell", self._neg_cells)

        # footer status: jumlah baris + legenda '•' bila ada bulan lalu
        has_lalu = any(str(v).endswith("\u2022") for v in rows["Tanggal"])
        status = f"{n} baris"
        if has_lalu:
            status += " \u00b7 \u2022 = bulan lalu"
        if self._h_label:
            status += f" \u00b7 H={self._h_label}"
        # v3.9.59 — 2d-03: simpan status dasar utk pemulihan flash copy
        self._base_status = status
        self.status_var.set(status)

    def _auto_fit(self):
        """v3.4 (pola) — auto-fit lebar kolom ke konten."""
        auto_fit_columns(self.tree)

    # =====================================================================
    # v3.9.59 — AUDIT FIX 2d-03: COPY Nomor / Nomor PO (port pola
    # DetailsPopup: klik-kanan menu konteks + Ctrl+C + double-click cell
    # + tombol footer 📋 + flash TERSALIN — istilah & urutan identik).
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
            except tk.TclError:
                pass
        self.status_var.set(msg)
        self.status_label.configure(fg=C_ACCENT_DARK)

        def restore():
            # popup bisa ditutup < 3 detik — jangan sentuh widget mati
            # (pola FIX D-09 DetailsPopup).
            if not self.winfo_exists():
                return
            self.status_var.set(self._base_status)
            self.status_label.configure(fg=C_TEXT_MUTED)

        # v3.9.59 — fix 2b-07 (agent B): 3000 literal → konstanta bersama
        # FLASH_MS (2500ms — seragam dgn details_popup/app; pola port
        # 2d-03 tetap identik hanya durasinya).
        self._flash_after = self.after(FLASH_MS, restore)

    def _on_context_menu(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            return
        try:
            # multi-select: baris yang diklik sudah terseleksi → PERTAHANKAN
            # seleksi (pola fix 48-c DetailsPopup)
            if iid not in tree.selection():
                tree.selection_set(iid)
            tree.focus(iid)
        except tk.TclError:
            pass
        menu = self._build_copy_menu(iid, tree)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _build_copy_menu(self, iid, tree):
        """Bangun menu konteks copy (dipisah dari _on_context_menu supaya
        bisa diuji/di-invoke tanpa posting menu)."""
        values = tree.item(iid, "values")
        if not values:
            return tk.Menu(self, tearoff=0)
        row = dict(zip(COL_IDS, values))
        nomor = str(row.get("Nomor", "") or "").strip()
        nomor_po = str(row.get("Nomor PO", "") or "").strip()

        def _lbl(s: str) -> str:
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
        # pasangan kedua nomor dokumen baris tanggal itu (tab-separated —
        # paste Excel: 2 sel)
        pair = "\t".join(p for p in (nomor, nomor_po) if p)
        menu.add_command(
            label=f"📋 Copy Nomor + Nomor PO — {_lbl(nomor or nomor_po)}",
            command=lambda: self._copy_to_clipboard(
                pair, "Nomor + Nomor PO"))
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
        return menu

    def _copy_row(self, iid, tree):
        values = tree.item(iid, "values")
        if not values:
            return
        self._copy_to_clipboard("\t".join(str(v) for v in values),
                                "Baris lengkap")

    def _copy_all_unique(self, col: str):
        df = self.rows
        if df is None or df.empty or col not in df.columns:
            self._flash_status("Tidak ada data untuk di-copy.")
            return
        # kolom Nomor/Nomor PO popup ini = GABUNGAN beberapa nomor per
        # tanggal ('A, B') → pecah per nomor supaya benar2 unik.
        uniq: set = set()
        for v in df[col].dropna().astype(str):
            for part in str(v).split(","):
                part = part.strip()
                if part:
                    uniq.add(part)
        vals = sorted(uniq)
        if not vals:
            self._flash_status("Tidak ada nilai untuk di-copy.")
            return
        self._copy_to_clipboard("\n".join(vals),
                                f"{len(vals)} nilai {col} (unik)")

    def _on_double_click(self, event):
        """Double-click cell Nomor / Nomor PO → langsung copy nilai cell
        (pola DetailsPopup; resolve posisi-display → nama kolom aktual
        supaya kolom disembunyikan tidak salah sasaran)."""
        tree = event.widget
        iid = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not iid or not col or col == "#0":
            return
        col_name = identify_to_column(tree, col)
        if col_name in ("Nomor", "Nomor PO"):
            val = tree.set(iid, col_name)
            self._copy_to_clipboard(val, col_name)

    def _on_copy_key(self, _event):
        """Ctrl+C (pola DetailsPopup): region sel aktif ala Excel MENANG,
        >1 baris terpilih → TSV, 1 baris → Nomor (fallback Nomor PO —
        label flash sesuai kolom ASAL nilai)."""
        tree = self.tree
        # 2d-05 — region sel aktif → copy REGION (persis prioritas
        # widgets._copy_rows; binding ini mengganti binding itu di tree
        # popup — tanpa cek, seleksi sel yang di-highlight diacuhkan).
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
        label = "Nomor"
        val = str(row.get("Nomor", "") or "")
        if not val:
            label = "Nomor PO"
            val = str(row.get("Nomor PO", "") or "")
        if val:
            self._copy_to_clipboard(val, label)

    # =====================================================================
    # FORMAT
    # =====================================================================
    @staticmethod
    def _fmt_num(val) -> str:
        """Format angka Indonesia (pola DeviasiView._fmt_num): 0 → '-',
        minus dalam kurung, 1 desimal bila pecahan."""
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
            s = f"{v:,.1f}".replace(",", "\u00a0").replace(".", ",") \
                .replace("\u00a0", ".")
        if v < 0:
            return f"({s[1:]})"
        return s


def _is_neg_display(s) -> bool:
    """True bila string tampilan bernilai minus — '(1.234)' / '(12,5)'."""
    t = str(s or "").strip()
    return t.startswith("(") and t.endswith(")")


def _fmt_tanggal(t) -> str:
    """Tanggal → label: positif '25'; bulan lalu (negatif) '25•'
    (konvensi pivot_view — kronologis: 25• … 31• lalu 1 … 31)."""
    try:
        d = int(t)
    except (TypeError, ValueError):
        return str(t)
    if d < 0:
        return f"{-d}•"
    return str(d)


def _chrono_key(t):
    """Kunci urut numerik: bulan lalu (25•…31•) dulu, lalu 1..31 —
    negatif → abs(d) (25..31), positif → 100+d (101..131); ascending
    kronologis: 25•, 26•, … 31•, 1, 2, … 31 (konvensi pivot_view).

    FIX 35-b (audit 34-b RISK-3): parse via float — Tanggal float64
    (mis. ada NaN → pd.to_numeric menghasilkan float) membuat str(t)
    = '-25.0' yang GAGAL di int() → guard 999999 → bulan lalu TERBALIK
    senyap (31• dulu). int(float(...)) menerima '-25.0'/'-25' sama
    saja; guard 999999 tetap sbg fallback terakhir (NA/label non-angka).
    """
    try:
        d = int(float(str(t).rstrip("•")))
    except (TypeError, ValueError):
        return 999999
    return abs(d) if d < 0 else 100 + d


def _compute_com_series(df: pd.DataFrame, nama_barang: str,
                        nama_resto: str, satuan: str | None = None) -> dict:
    """v3.9.25 — COM (pemakaian) per tanggal utk 1 pasangan (barang, resto).

    PORT PERSIS laporan_deviasi_view._compute_com_matrix (tab 🚨 Anomali
    COM / baris 6.PEMAKAIAN (COM) — formula v3.9.5):
        com(t) = so_prev(t) + IN(t) − BK(t) − SO(t)

    SEMANTIK KOLOM GLOBAL (diverifikasi parity vs matrix laporan):
    so_prev(t) = SO pasangan di tanggal kolom GLOBAL SEBELUM t — kolom
    global = union tanggal baris 4 JENIS (SALDO AWAL · 1.SO · 4.IN ·
    8.BARANG KELUAR) dari SEMUA pasangan di frame (persis col_keys
    laporan). Pasangan TANPA baris SO di kolom global t−1 dibaca 0
    (fillna — BUKAN SO tanggal pair-sebelumnya): pair dgn SO di t=1 &
    t=3 mendapat com(3) = 0 − SO(3) bila kolom global t=2 ada (dari
    pasangan lain), = SO(1) − SO(3) bila t=2 tidak ada di frame —
    identik perilaku Anomali COM (dan M Table.Pivot atas kolom yang
    sama). Tanggal pertama kolom → so_prev 0; tanggal 1 → SALDO AWAL
    pasangan BILA ada (dibaca TANPA fill — 'SA ada nilainya 0' ≠
    'SA tidak ada'), fallback so_prev (tanggal negatif bulan lalu).

    Dihitung DALAM grup satuan yang diklik (pola FIX 35-b — konsisten
    dgn angka popup GR/PCS; matriks Anomali COM level pasangan tanpa
    satuan → identik utk pasangan 1-satuan, seluruh data real).
    Return: {tanggal(float) → nilai com} — kosong bila tak ada baris.
    """
    if df is None or df.empty:
        return {}

    # kolom GLOBAL (semua pasangan — mirror col_keys laporan)
    # FIX 6e-PERF — astype(str)+isin+to_numeric full-frame di-cache per
    # identitas df (IDENTIK hasil versi lama).
    col_keys = _com_col_keys(df)
    if not col_keys:
        return {}

    # baris pasangan (+satuan) 4 JENIS
    # FIX 6e-PERF — mask via kode factorize (IDENTIK astype(str) == /
    # isin versi lama; objek == full-frame × 4 diganti kode int).
    mask = (_col_code_mask(df, "Nama Barang", nama_barang)
            & _col_code_mask(df, "NAMA RESTO", nama_resto)
            & _col_isin_mask(df, "JENIS", _COM_JENIS))
    if satuan is not None:
        mask &= _col_code_mask(df, "SATUAN", satuan)
    sub = df[mask]
    if sub.empty:
        return {}

    tgl = pd.to_numeric(sub["Tanggal"], errors="coerce")
    nilai = pd.to_numeric(sub["NILAI"], errors="coerce")
    sub = sub.assign(_t=tgl, _v=nilai).dropna(subset=["_t"])
    if sub.empty:
        return {}

    # SALDO AWAL mentah per tanggal (TANPA fill — bedakan 'SA ada' dari
    # 'SA tidak ada'; mirror jenis_df(..., fill=False) laporan; dobel
    # SA dijumlahkan defensif — pivot laporan memakai aggfunc sum).
    sa_raw: dict = {}
    sa_rows = sub[sub["JENIS"].astype(str) == _JENIS_SA] \
        .dropna(subset=["_v"])
    for t, v in zip(sa_rows["_t"], sa_rows["_v"]):
        sa_raw[t] = sa_raw.get(t, 0.0) + float(v)

    # pivot SO/IN/BK per tanggal pasangan (fill 0 — mirror jenis_df
    # fill=True laporan; reindex ke kolom GLOBAL dilakukan via .get)
    piv = sub[sub["JENIS"].astype(str)
              .isin((_JENIS_SO, _JENIS_IN, _JENIS_BK))] \
        .pivot_table(index="_t", columns="JENIS", values="_v",
                     aggfunc="sum", fill_value=0.0)
    for col in (_JENIS_SO, _JENIS_IN, _JENIS_BK):
        if col not in piv.columns:
            piv[col] = 0.0

    def _num(v) -> float:
        """float() NaN/invalid-safe → 0.0 (defensif — pivot sudah
        fill 0, jalur .get default 0.0)."""
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 0.0
        return 0.0 if pd.isna(f) else f

    so_s = piv[_JENIS_SO]
    in_s = piv[_JENIS_IN]
    bk_s = piv[_JENIS_BK]

    com: dict = {}
    for i, t in enumerate(col_keys):
        try:
            is_t1 = int(float(t)) == 1
        except (TypeError, ValueError):
            is_t1 = False
        if is_t1 and t in sa_raw:
            base = sa_raw[t]           # base com(1) = SA pair (audit fix)
        elif i == 0:
            base = 0.0
        else:
            base = _num(so_s.get(col_keys[i - 1], 0.0))
        com[t] = (base + _num(in_s.get(t, 0.0)) - _num(bk_s.get(t, 0.0))
                  - _num(so_s.get(t, 0.0)))
    return com


def build_popup_rows(data: pd.DataFrame, nama_barang: str,
                     nama_resto: str, satuan: str | None = None
                     ) -> pd.DataFrame:
    """Pure pandas (thread-safe) — siapkan baris popup per Tanggal.

    Hanya 3 JENIS yang dipakai (permintaan user: nilai saldo akhir, SO,
    IN, deviasi — TANPA OUT/BARANG KELUAN/BARANG MASUK):
      Saldo Akhir = Σ 2.SALDO AKHIR · SO = Σ 1.SO · IN = Σ 4.IN
      Deviasi = SO − Saldo Akhir (identik 3.DEVIASI & tabel utama).

    v3.9.25 — dua kolom baru (user: "tambah kolom nomor po dan COM"):
      Nomor PO = nomor pesanan pembelian baris 4.IN per tanggal
                 (split koma → dedup → urut → gabung — pola Nomor);
      COM      = pemakaian harian, formula PERSIS
                 laporan_deviasi_view._compute_com_matrix
                 (_compute_com_series — kolom tanggal GLOBAL, parity
                 48/48 nilai vs matrix Anomali COM). Tanggal tampil di
                 luar kolom global (mis. hanya 2.SALDO AKHIR) → COM
                 kosong (tab Anomali COM juga tak punya nilainya).

    satuan (FIX 35-b / audit 34-b RISK-2): tabel utama memivot per
    (Nama Barang × NAMA RESTO × SATUAN) — pasangan yang punya baris GR
    DAN PCS menghasilkan 2 baris terpisah, jadi popup HARUS mengagregasi
    grup satuan yang sama dgn BARIS YANG DIKLIK (dulu jumlah lintas-
    satuan: GR Dev 2 + PCS Dev 5 → popup 7, tak cocok dgn keduanya).
    KEPUTUSAN kesamaan STRICT (TANPA OR satuan-NA): pivot utama
    (pivot_table dropna default) MENGHAPUS baris ber-SATUAN NA dari
    semua grup — baris NA tidak pernah menyumbang nilai baris tabel
    utama manapun (probe 35b_probe_na_satuan), jadi memasukkannya akan
    membuat popup LEBIH BESAR dari baris utama DAN terhitung ganda di
    popup GR maupun PCS. Di output pipeline append1 SATUAN memang
    konstan per pasangan (lookup LANGKAH 8 fillna per pasangan) — bentuk
    2-satuan hanya dari data satuan eksplisit, persis bentuk yang
    dimodelkan indeks pivot. None = tanpa filter satuan (perilaku lama
    utk pemanggil lain).
    """
    empty = pd.DataFrame(columns=["Tanggal", "Saldo Akhir", "SO", "IN",
                                  "Nomor", "Nomor PO", "COM", "Deviasi"])
    if data is None or data.empty:
        return empty

    df = data
    # FIX 6e-PERF — mask pasangan via kode factorize astype(str) (cache
    # per identitas df; IDENTIK hasil mask versi lama — objek == full-
    # frame × 3 + astype × 3 per popup diganti kode int ≈ 0,1 ms).
    # JENIS tetap isin RAW (persis versi lama — tanpa astype).
    mask = (_col_code_mask(df, "Nama Barang", nama_barang)
            & _col_code_mask(df, "NAMA RESTO", nama_resto)
            & df["JENIS"].isin(
                (_JENIS_SALDO, _JENIS_SO, _JENIS_IN)).to_numpy())
    # FIX 35-b — filter SATUAN grup yang diklik (astype(str) dua sisi:
    # encoding identik dgn nilai kolom Satuan yang dirender tree).
    if satuan is not None:
        mask &= _col_code_mask(df, "SATUAN", satuan)
    sub = df[mask]
    if sub.empty:
        return empty

    tgl = pd.to_numeric(sub["Tanggal"], errors="coerce")
    nilai = pd.to_numeric(sub["NILAI"], errors="coerce")
    sub = sub.assign(_t=tgl, _v=nilai).dropna(subset=["_t"])

    if sub.empty:
        return empty

    # v3.9.22 — Nomor dokumen IN per tanggal (user: "Pop up di tab
    # Deviasi GR dan PCS ada Nomor nya juga Misal IT...... atau
    # RI......"): kumpulkan Nomor baris 4.IN per tanggal (satu baris
    # bisa memuat beberapa nomor sekaligus, dipisah koma di data sumber
    # → dipecah, didedup, diurut, digabung kembali).
    _nomor_per_tgl: dict = {}
    # v3.9.25 — Nomor PO baris 4.IN per tanggal (pola Nomor: split koma
    # → dedup → urut → gabung; IT. pemindahan biasanya tanpa PO → kosong).
    _po_per_tgl: dict = {}
    if "Nomor" in sub.columns:
        in_rows = sub[sub["JENIS"] == _JENIS_IN]
        for _t, _no in zip(in_rows["_t"], in_rows["Nomor"]):
            if pd.isna(_no):
                continue
            for part in str(_no).split(","):
                part = part.strip()
                if part:
                    _nomor_per_tgl.setdefault(_t, set()).add(part)
        if "Nomor PO" in in_rows.columns:
            for _t, _po in zip(in_rows["_t"], in_rows["Nomor PO"]):
                if pd.isna(_po):
                    continue
                for part in str(_po).split(","):
                    part = part.strip()
                    if part:
                        _po_per_tgl.setdefault(_t, set()).add(part)

    # v3.9.25 — COM per tanggal (formula identik Anomali COM; dihitung
    # TERPISAH dari pivot tampilan 3 JENIS supaya union tanggal-nya =
    # persis union 4 JENIS laporan — baris tampilan tidak berubah).
    _com_by_t = _compute_com_series(df, nama_barang, nama_resto, satuan)

    wide = sub.pivot_table(index="_t", columns="JENIS", values="_v",
                           aggfunc="sum", fill_value=0.0)

    for col in (_JENIS_SALDO, _JENIS_SO, _JENIS_IN):
        if col not in wide.columns:
            wide[col] = 0.0

    out = pd.DataFrame({
        "_t": wide.index,
        "Saldo Akhir": wide[_JENIS_SALDO].to_numpy(),
        "SO": wide[_JENIS_SO].to_numpy(),
        "IN": wide[_JENIS_IN].to_numpy(),
    })
    # Deviasi = SO − Saldo Akhir (identik kolom Deviasi tabel utama)
    out["Deviasi"] = out["SO"] - out["Saldo Akhir"]
    out["Nomor"] = [", ".join(sorted(_nomor_per_tgl.get(t, ())))
                    for t in out["_t"]]
    out["Nomor PO"] = [", ".join(sorted(_po_per_tgl.get(t, ())))
                       for t in out["_t"]]
    # v3.9.25 — COM: numerik mentah (belum diformat) supaya minus tetap
    # terdeteksi _is_neg_display setelah diformat; tanggal di luar union
    # 4 JENIS → NaN (kolom kosong, bukan 0).
    out["COM"] = [_com_by_t.get(t, float("nan")) for t in out["_t"]]

    # label tampilan + urut kronologis (numerik — negatif abs 25..31
    # < positif 101..131, jadi bulan lalu dulu lalu 1..31)
    out["Tanggal"] = out["_t"].map(_fmt_tanggal)
    out = out.assign(_k=out["_t"].map(_chrono_key)) \
        .sort_values("_k") \
        .drop(columns=["_k"]).reset_index(drop=True)

    # format angka Indonesia (string — siap render)
    for col in ("Saldo Akhir", "SO", "IN", "COM", "Deviasi"):
        out[col] = out[col].map(DeviasiPopup._fmt_num)

    return out[["Tanggal", "Saldo Akhir", "SO", "IN", "Nomor",
                "Nomor PO", "COM", "Deviasi"]]


def show_deviasi_popup(parent, data: pd.DataFrame, nama_barang: str,
                       nama_resto: str, satuan: str | None = None,
                       h: int | None = None):
    """Buka popup ringkas utk pasangan (barang, resto).

    Dipanggil dari DeviasiView._on_double_click (tab Deviasi GR & PCS,
    termasuk window clone ⛶ — event.widget-agnostic).
    """
    title = f"{nama_barang} — {nama_resto}"
    if satuan:
        title += f"  ({satuan})"

    rows = build_popup_rows(data, nama_barang, nama_resto, satuan=satuan)
    h_label = _fmt_tanggal(h) if h is not None else ""
    popup = DeviasiPopup(parent, title, rows, h_label=h_label)
    return popup
