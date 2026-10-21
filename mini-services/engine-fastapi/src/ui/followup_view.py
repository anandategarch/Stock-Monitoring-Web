"""followup_view.py — Tab "☑ Follow Up" (v3.2.0) — ala repo Waste.

v3.9.20 (deep audit 34-e/fix 35-c2): nilai popup kolom = baris yang
TAMPIL (filter kolom lain dulu; kolom sendiri dikecualikan) + import
C_TEXT_MUTED tidak-terpakai dibersihkan (F401).

v3.9.6 (permintaan user: "Format Follow UP Seperti File Sample"):
format tabel mengikuti sheet Follow UP workbook asli user (01.1 CEK
STOCK V2.xlsb): Resto · Nama Barang · SO per tanggal (heading ANGKA
TANGGAL — H=25 → 23/24/25/26/27, persis kolom "22.0..27.0" sample) ·
Sistem · Deviasi · Loss Surplus to BOM · Keterangan · kolom kerja FU:
SO · DEVIASI · Selisih · Selisih Deviasi · Cek FU · PIC · Status TL ·
Ditambahkan. Snapshot lama tanpa field tanggal tetap dimuat (kolom
  tampil "-"). Export Excel mengikuti format yang sama.

Daftar baris anomali yang di-CENTANG (kolom ✓) di tab DEVIASI GR /
DEVIASI PCS / LAPORAN DEVIASI — shortlist investigasi berbentuk SNAPSHOT
(nilai apa adanya saat baris dicentang; TIDAK ikut filter/H aktif).

Perilaku:
- Baris menetap: tertutup aplikasi pun aman (followup.json, atomic write).
- Klik sel ✓ di tabel ini = KELUARKAN baris dari daftar.
- 💾 Export Excel: format file sample + kolom kerja FU (SO · DEVIASI ·
  Selisih · Selisih Deviasi · Cek FU · PIC — diisi petugas).
  (v3.8: fitur 📥 Impor Hasil TL DIHAPUS — permintaan user "gak terlalu
  perlu".)
- ✕ Kosongkan: hapus seluruh daftar (konfirmasi).
- Double-click baris → pop-up detail source (bila data pipeline tersedia).
- Sort kolom via klik judul (parse angka negatif kurung).
- v3.9.17: minus merah PER CELL (semua kolom numerik — Tk 9 tag cell;
  fallback Tk 8 = tag baris, konsisten view lain v3.9.2). Dulu SATU
  nilai minus mewarnai seluruh baris + menimpa warna status
  resolved/pending.
"""

import contextlib
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from .followup import CHECK_ON, DATE_COL_IDS, FollowUpStore, _cek_display_text
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
    FLASH_MS,  # v3.9.59 — kanon durasi status flash (bonus, agent B/F)
    AccentButton,
    Card,
    ColumnManager,
    DangerButton,
    EmptyState,
    GhostButton,
    HeaderFilterGroup,
    LoadingOverlay,
    TableExpander,
    _filter_value_sort_key,
    apply_cell_tag,
    apply_col_sel_restore,  # v3.9.66 — filter persisten antar sesi
    attach_clone_filters,
    auto_fit_columns,
    col_sel_to_json,  # v3.9.66 — filter persisten antar sesi
    enable_col_resize,
    enable_multi_select,
    fmt_int_id,
    identify_to_column,
    insert_tree_items,
    open_tree_maximized,
    run_async,
    sort_tree_by_column,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)

# kolom tabel Follow Up — FORMAT FILE SAMPLE (v3.9.6):
# ✓ · Resto · Nama Barang · [SO tgl H-2..H+2 — id "T-2".."T+2", heading
# dinamis angka tanggal] · Sistem · Deviasi · Loss Surplus to BOM ·
# Keterangan · SO · DEVIASI · Selisih · Selisih Deviasi · Cek FU · PIC ·
# Status TL · Ditambahkan (kolom kerja FU dari resolved store; Asal &
# tracking app tetap dibawa di bagian akhir).
COLUMNS = [
    ("✓", 34, "center"),
    ("Resto", 90, "w"),
    ("Nama Barang", 220, "w"),
    ("T-2", 64, "e"),
    ("T-1", 64, "e"),
    ("T", 64, "e"),
    ("T+1", 64, "e"),
    ("T+2", 64, "e"),
    ("Sistem", 80, "e"),
    ("Deviasi", 80, "e"),
    ("Loss Surplus to BOM", 105, "e"),
    ("Keterangan", 140, "w"),
    ("SO", 80, "e"),
    ("DEVIASI", 80, "e"),
    ("Selisih", 70, "e"),
    ("Selisih Deviasi", 90, "e"),
    ("Cek FU", 70, "center"),
    ("Asal", 100, "w"),
    ("Status TL", 90, "w"),
    ("PIC", 110, "w"),
    ("Ditambahkan", 120, "w"),
]


class FollowUpView(tk.Frame):
    """Tab Follow Up: tabel snapshot baris tercentang + ekspor."""

    def __init__(self, parent, store: FollowUpStore,
                 get_data: Callable[[], pd.DataFrame | None] | None = None,
                 go_to_proses: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.store = store
        self.get_data = get_data      # akses append1_df (untuk popup detail)
        self.go_to_proses = go_to_proses
        # v3.3: peta iid → fingerprint (BUKAN index) — klik ✓ / double-click
        # mengenai baris yang benar WALAUPUN tabel sudah di-sort/di-reorder
        # (bug v3.2: tree.index() + _fp_order → salah baris setelah sort)
        self._iid_fp: dict[str, str] = {}
        # FIX 6e-01 (audit 6-e HIGH — mirror fix 48-d deviasi_view v3.9.33):
        # _render() membangun ulang tree + MENGGANTI _iid_fp dgn penomoran
        # posisi fu_N (store berubah via toggle ✓ dari tab mana pun →
        # listener _on_store_changed → _render) → fu_N kini menunjuk baris
        # LAIN, sedangkan clone ⛶ (non-modal, iid disalin saat dibuka) TIDAK
        # di-refresh → klik ✓ di clone basi menghapus baris SALAH (persist
        # followup.json). Kini: (1) setiap re-render MENUTUP semua clone hidup,
        # (2) generasi render dicatat di tree clone saat dibuka — handler
        # ✓/double-click mengabaikan clone generasi lama (defense-in-depth).
        self._render_gen = 0
        self._clone_wins: list = []
        # v3.9.17: minus merah PER CELL (konsisten view lain sejak v3.9.2)
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        # v3.9.59 — bonus (FIX 2f-07/2f-08 surfacing via API agent F):
        # catatan store (last_recovery / last_save_error) → flash status
        # kartu atas; _status_text = teks status normal terakhir (dasar
        # restore flash), _store_note = catatan aktif, _note_after timer.
        self._status_text = "0 baris."
        self._store_note: str | None = None
        self._note_after: str | None = None

        self._build_ui()
        self._setup_tags()
        store.add_listener(self._on_store_changed)
        self._render()

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        # --- Empty state ---
        # v3.9.59 — FIX 2e-09: subtitle jujur — daftar terisi dari centang
        # ✓ di tab Deviasi/Laporan (BUKAN dari pipeline); CTA pipeline
        # tetap (berguna bila data belum ada), tapi kini ada petunjuk
        # cara mengisi daftar. Dulu CTA sendirian menyesatkan: user yang
        # SUDAH menjalankan pipeline mengkliknya dan daftar tetap kosong.
        self.empty = EmptyState(
            self, icon="📌", title="Daftar Follow Up masih kosong",
            subtitle="Baris masuk daftar lewat centang ✓ di tab 📦 Deviasi "
                     "GR / 🧩 Deviasi PCS / 📋 Laporan Deviasi — jalankan "
                     "pipeline dulu bila data belum ada.",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Konten utama ---
        self.content = tk.Frame(self, bg=C_BG)

        # --- Kartu aksi (ringkas — tanpa KPI row) ---
        ccard = Card(self.content, title="Daftar Follow Up")
        ccard.pack(fill="x", padx=12, pady=(12, 0))
        cbody = ccard.body()

        r0 = tk.Frame(cbody, bg=C_CARD)
        r0.pack(fill="x")
        self.btn_export = AccentButton(r0, text="💾 Export Excel",
                                       command=self._on_export)
        self.btn_export.pack(side="left")

        self.btn_import = None  # v3.8: Impor Hasil TL DIHAPUS (user)

        self.btn_clear = DangerButton(r0, text="✕ Kosongkan",
                                      command=self._on_clear)
        self.btn_clear.pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar(value="0 baris.")
        tk.Label(r0, textvariable=self.status_var, bg=C_CARD, fg=C_HEADER,
                 font=font(9, "bold")).pack(side="right")

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        tbody = tcard.body()

        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        title_label = tk.Label(head, text="Follow Up — baris anomali terpilih",
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

        col_ids = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(tbody, columns=col_ids, show="headings",
                                 selectmode="extended")
        for col_name, width, anchor in COLUMNS:
            self.tree.column(col_name, width=width, minwidth=34,
                             anchor=anchor)
            # v3.5: SEMUA kolom pakai filter header ⧩ (sort via popup);
            # ✓ = keluarkan via klik sel
            self.tree.heading(col_name, text=col_name)

        vsb = ttk.Scrollbar(tbody, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tbody, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")
        tbody.grid_rowconfigure(1, weight=1)
        tbody.grid_columnconfigure(0, weight=1)

        # v3.4: drag tepi heading = resize lebar kolom; double-click tepi =
        # auto-fit (dipasang SEBELUM handler klik view supaya "break" efektif)
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        foot = tk.Frame(tbody, bg=C_CARD)
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        # v3.9.59 — FIX 2e-05: footer hint (dulu baris ini KOSONG —
        # satu-satunya tabel view tanpa footer; kolom ✓ = KELUARKAN
        # baris, destruktif utk snapshot, tanpa affordance on-screen
        # apa pun). Perilaku aktual: toggle-off menghapus baris + status
        # TL/PIC resolved-nya dari followup.json; recovery = centang
        # ulang di tab Deviasi (snapshot segar, status hilang).
        self._foot_hint = tk.Label(
            foot,
            text="klik ✓ = keluarkan baris dari daftar (status TL/PIC ikut "
                 "terhapus) · centang ✓ lagi di tab Deviasi utk menambah "
                 "· Dobel-klik baris = detail sumber",
            bg=C_CARD, fg=C_TEXT_MUTED, font=font(8))
        self._foot_hint.pack(side="left")

        # Loading overlay
        self.overlay = LoadingOverlay(tbody, "Menyiapkan daftar…")

        # v3.5: filter header ⧩ di SEMUA kolom (kecuali ✓)
        _filter_cols = [c[0] for c in COLUMNS if c[0] != "✓"]
        self._col_sel: dict = {c: None for c in _filter_cols}
        self.header_filters = HeaderFilterGroup(
            self.tree, _filter_cols,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        # v3.6: hide/unhide kolom (klik kanan heading / tombol ◱ Kolom)
        self._colmgr = ColumnManager(
            self.tree,
            open_filter=lambda c: self.header_filters.open_popup(c))

        # v3.9 (ala Waste): ⤢ Perbesar Tabel — ciutkan kartu aksi + judul
        self._expander = TableExpander(btn_expand, [ccard, title_label])

        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")
        # v3.9.59 — FIX 2e-05: cursor hand2 saat hover sel kolom ✓ (sinyal
        # klik-able — pola cheap: <Motion> identify kolom/region).
        self.tree.bind("<Motion>", self._on_tree_motion, add="+")

    def _on_tree_motion(self, event):
        """FIX 2e-05 — cursor hand2 di atas sel kolom ✓ (aksi klik =
        keluarkan baris; tanpa ini cursor default = tak ada sinyal
        kolom ✓ interaktif)."""
        tree = event.widget
        try:
            hand = (tree.identify_region(event.x, event.y) == "cell"
                    and identify_to_column(
                        tree, tree.identify_column(event.x)) == "✓"
                    and tree.identify_row(event.y))
            tree.configure(cursor="hand2" if hand else "")
        except tk.TclError:
            return

    def _setup_tags(self):
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(self.tree)
        self.tree.tag_configure("evenrow", background="#ffffff")
        self.tree.tag_configure("oddrow", background="#f8fafc")
        self.tree.tag_configure("negative", foreground="#dc2626")
        self.tree.tag_configure("neg_cell", foreground="#dc2626")  # v3.9.17
        self.tree.tag_configure("resolved", foreground="#059669")
        self.tree.tag_configure("pending", foreground="#b45309")

    # =========================================================================
    # RENDER
    # =========================================================================
    def _on_store_changed(self, store):
        # dipanggil listener store (toggle dari tab lain)
        try:
            if self.winfo_exists():
                self.after(0, self._render)
        except tk.TclError:
            pass

    def _show_empty(self):
        self.content.pack_forget()
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

    def _show_content(self):
        self.empty.pack_forget()
        self.content.pack(fill="both", expand=True)

    def _col_values(self, col: str) -> list:
        """Nilai unik TERFORMAT utk popup filter header (v3.5).

        v3.9.19 (penuntasan "berlaku untuk semua filter"): sumber nilai =
        baris yang TAMPIL SAAT INI — filter header kolom LAIN diterapkan
        dulu (kolom ini sendiri dikecualikan — perilaku AutoFilter
        Excel); dulu semua baris store → nilai baris yang sudah
        terfilter kolom lain tetap muncul di popup."""
        rows = list(self.store.rows.values())
        if not rows:
            return []
        idx = [i for i, c in enumerate(COLUMNS) if c[0] == col]
        if not idx:
            return []
        j = idx[0]
        col_idx = {c[0]: k for k, c in enumerate(COLUMNS)}
        other = [(col_idx[c], s) for c, s in self._col_sel.items()
                 if s is not None and c != col and c in col_idx]
        vals = []
        for snap in rows:
            info = self.store.resolved.get(snap.get("fp", ""), {})
            values = self._fu_row_values(snap, bool(info), info)
            if other and not all(str(values[k]) in s for k, s in other):
                continue
            vals.append(str(values[j]))
        # v3.9.33 — AUDIT FIX (48-e FIX 14): sort numerik-aware (pola
        # widgets._filter_value_sort_key ala in_selisih — "10" harus
        # muncul SETELAH "2"; dulu leksikografis).
        return sorted(set(vals), key=_filter_value_sort_key)

    def _on_col_filter(self, col: str, selected):
        self._col_sel[col] = selected
        self._render()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    # Follow Up: sumber data = FollowUpStore (persist sendiri di
    # followup.json) — guard toko kosong (belum ada ✓ yang disimpan).
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.followup')."""
        return col_sel_to_json(self._col_sel)

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.
        _render sinkron (kecil — daftar ✓ user), tanpa lazy dirty flag —
        aman dipanggil kapan pun setelah store terisi."""
        if not isinstance(state, dict):
            return
        try:
            if not self.store.rows:
                return
        except AttributeError:
            return
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        if changed:
            self._render()

    @staticmethod
    def _fu_num(v):
        """v3.9.59 — FIX 2e-04/2f-14: format angka INDONESIA (pola
        _fmt_num in_selisih_view / fmt_nominal_cell nominal_common):
        '1.234' / '1.234,5' / negatif KURUNG '(1.234)' / 0-None-NaN →
        '-'. Dulu koma ribuan EN + minus saran-tanda ('1,234.5' /
        '-1,234') — nilai snapshot sama tampil beda gaya antar tab
        (Deviasi GR '(1.234)' vs Follow Up '-1,234') → risiko salah
        baca koma desimal/ribuan."""
        if v in ("", None):
            return "-"
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)
        if pd.isna(f) or f == 0:
            return "-"
        neg = f < 0
        af = abs(f)
        if af == int(af):
            s = fmt_int_id(af)
        else:
            s = (f"{af:,.1f}".replace(",", "\u00a0")
                 .replace(".", ",").replace("\u00a0", "."))
        return f"({s})" if neg else s

    @staticmethod
    def _fu_pct(v):
        """Loss Surplus to BOM — rasio gaya file sample (1.0053 → '1,01';
        0.0524 → '0,05'; minus kurung).
        v3.9.59 — FIX 2f-14: desimal KOMA (dulu titik EN '1.01'); minus
        tetap kurung; NaN → '-' (bukan 'nan')."""
        if v in ("", None):
            return "-"
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)
        if pd.isna(f) or f == 0:
            return "-"
        s = (f"{abs(f):,.2f}".replace(",", "\u00a0")
             .replace(".", ",").replace("\u00a0", "."))
        return f"({s})" if f < 0 else s

    def _fu_row_values(self, snap, resolved, info) -> list:
        """Nilai terformat satu baris follow-up (urutan COLUMNS — dipakai
        render + filter header supaya nilai popup == yang tampil).
        v3.9.6: urutan FORMAT FILE SAMPLE — SO per tanggal (H-2..H+2),
        Sistem, Deviasi, Loss Surplus to BOM, Keterangan, kolom kerja FU
        (SO/DEVIASI salinan + Selisih/Selisih Deviasi/Cek FU dari info)."""
        dev = snap.get("deviasi", 0)
        try:
            dev_f = float(dev)
        except (TypeError, ValueError):
            dev_f = 0.0
        # v3.9.59 — FIX 2e-04: _fu_num kini ID + minus kurung sendiri
        # (dulu re-wrap manual '-' → dobel kurung dengan format baru).
        dev_txt = self._fu_num(dev) if dev_f else "-"

        def _so(v):
            try:
                return self._fu_num(float(v)) if v not in ("", None) else "-"
            except (TypeError, ValueError):
                return "-"

        # snapshot lama (pre-v3.9.6) tanpa field tanggal → "-"
        return [
            CHECK_ON,
            snap.get("resto", ""),
            snap.get("barang", ""),
            _so(snap.get("so_m2")), _so(snap.get("so_m1")),
            _so(snap.get("so")), _so(snap.get("so_p1")),
            _so(snap.get("so_p2")),
            _so(snap.get("sistem")),
            dev_txt,
            self._fu_pct(snap.get("loss_bom")),
            # FIX 6d1-04 — segmen ANALISA ('Berubah Arah' / 'Peningkatan
            # Tertinggi +p%') DIBEDAKAN dari 7 label CEK kanonik (mirror
            # definisi footer/popup CEK tab Deviasi — baris tsb bukan
            # anomali CEK); nilai popup filter kolom ikut nilai tampil.
            _cek_display_text(snap.get("cek", "")),
            _so(snap.get("so")),
            dev_txt,
            self._fu_num(info.get("Selisih")) if info.get("Selisih")
            not in ("", None) else "-",
            self._fu_num(info.get("Selisih Deviasi"))
            if info.get("Selisih Deviasi") not in ("", None) else "-",
            str(info.get("Cek FU", "") or "-"),
            snap.get("asal", ""),
            "Selesai" if resolved else "Menunggu",
            info.get("PIC", ""),
            (snap.get("added_at", "") or "")[:16].replace("T", " "),
        ]

    def _refresh_date_headings(self, rows):
        """v3.9.6: heading kolom tanggal = ANGKA TANGGAL dari H snapshot
        terbaru (H=25 → '23'..'27' — persis sheet Follow UP file sample
        '22.0..27.0'). H tidak ada → id default T-2..T+2."""
        h_ref = None
        for snap in reversed(rows):
            h_val = snap.get("h")
            if isinstance(h_val, (int, float)) and h_val:
                h_ref = int(h_val)
                break
        if h_ref is None:
            for col_id in DATE_COL_IDS:
                self.tree.heading(col_id, text=col_id)
        else:
            for col_id, off in zip(DATE_COL_IDS, (-2, -1, 0, 1, 2)):
                self.tree.heading(col_id, text=str(h_ref + off))
        if getattr(self, "header_filters", None) is not None:
            self.header_filters.refresh_icons()

    def _render(self):
        # FIX 6e-01 (audit 6-e HIGH): baris/iid di-render ulang (_iid_fp
        # segera diganti di bawah dgn penomoran posisi fu_N) → clone ⛶ yang
        # masih hidup memegang salinan LAMA (iid sama, baris lain) → DITUTUP
        # (clone basi lebih buruk daripada tertutup) + generasi naik (guard
        # handler ✓/double-click clone — mirror deviasi_view _render_rows).
        self._render_gen += 1
        self._close_stale_clones()
        rows = list(self.store.rows.values())
        self.tree.delete(*self.tree.get_children())
        self._iid_fp = {}
        if self.header_filters is not None:
            self.header_filters.refresh_icons()

        if not rows:
            self._show_empty()
            self._refresh_date_headings(rows)
            # v3.9.59 — FIX 2e-05/bonus 2f-07+2f-08: jalur kosong PUN jujur
            # (dulu status kartu menyisakan teks render sebelumnya) +
            # catatan store (korup/persist-gagal) ikut tampil sekali.
            self._status_text = "0 baris."
            self._apply_status()
            self._consume_store_notes()
            return
        self._show_content()
        self._refresh_date_headings(rows)

        # v3.5: filter header ⧩ (display-only — daftar store tidak berubah)
        col_idx = {c[0]: j for j, c in enumerate(COLUMNS)}
        # v3.9.13: seleksi kosong (set()) = filter AKTIF → 0 baris
        # (semantik Excel) — dulu truthiness `if s` menelannya.
        active = [(col_idx[c], s) for c, s in self._col_sel.items()
                  if s is not None]

        items = []
        neg_cells = []   # v3.9.17 — sel minus (iid, kolom)
        n_shown = 0
        for i, snap in enumerate(rows):
            fp = snap.get("fp", "")
            info = self.store.resolved.get(fp, {})
            resolved = bool(info)
            dev = snap.get("deviasi", 0)
            try:
                dev_f = float(dev)
            except (TypeError, ValueError):
                dev_f = 0.0

            values = self._fu_row_values(snap, resolved, info)
            if active and not all(str(values[j]) in s for j, s in active):
                continue

            self._iid_fp[f"fu_{n_shown}"] = fp
            tags = ["evenrow" if n_shown % 2 == 0 else "oddrow"]
            # v3.9.17: minus merah PER CELL (semua kolom numerik — Tk 9 tag
            # cell; fallback Tk 8 = tag baris 'negative', perilaku v3.9.1).
            # Dulu: tags.append("negative") TANPA jalur per-cell → satu
            # nilai minus mewarnai SELURUH baris + tag pertama-menang
            # menimpa warna status resolved/pending.
            row_neg = False
            for col, raw in (
                    ("T-2", snap.get("so_m2")),
                    ("T-1", snap.get("so_m1")),
                    ("T", snap.get("so")),
                    ("T+1", snap.get("so_p1")),
                    ("T+2", snap.get("so_p2")),
                    ("Sistem", snap.get("sistem")),
                    ("Deviasi", dev_f),
                    ("DEVIASI", dev_f),
                    ("Loss Surplus to BOM", snap.get("loss_bom")),
                    ("SO", snap.get("so")),
                    ("Selisih", info.get("Selisih")),
                    ("Selisih Deviasi", info.get("Selisih Deviasi"))):
                try:
                    rv = float(raw)
                except (TypeError, ValueError):
                    continue
                if rv < 0:
                    if self._cell_tags:
                        neg_cells.append((f"fu_{n_shown}", col))
                    else:
                        row_neg = True
            if row_neg:
                tags.append("negative")
            tags.append("resolved" if resolved else "pending")
            items.append(("", f"fu_{n_shown}", {"values": values,
                                                  "tags": tuple(tags)}))
            n_shown += 1

        n = len(rows)
        selesai = self.store.resolved_count()
        # v3.9.68 — TRI-STATE (audit eksternal T1): 0 baris tampil karena
        # seleksi ⧩ KOSONG → pesan jujur + cara keluar (bukan status
        # generik "N baris · 0 tampil").
        _hint = (zero_row_filter_message(self._col_sel)
                 if not n_shown else None)
        self._status_text = (_hint
                             or (f"{n} baris · {selesai} selesai · "
                                 f"{n - selesai} menunggu"
                                 + (f" · {n_shown} tampil (filter ⧩)"
                                    if n_shown != n else "")))
        self._apply_status()
        self._consume_store_notes()
        self.btn_clear.set_enabled(n > 0)
        self.btn_export.set_enabled(n > 0)

        # FIX D-03 (audit 2-d): batalkan batch insert LAMA sebelum render
        # baru — listener store memicu _render SINKRON tiap toggle ✓;
        # dulu chunk loop lama tetap berjalan setelah tree.delete →
        # baris duplikat / TclError iid 'fu_N' sudah ada → render baru
        # TERPOTONG diam-diam (pola komparasi/laporan: cancel disimpan).
        # v3.9.17: simpan sel minus utk reapply (sort/clone — insert ulang
        # me-reset tag cell) + pasang SETELAH batch insert selesai.
        self._neg_cells = neg_cells
        if getattr(self, "_insert_cancel", None) is not None:
            self._insert_cancel()
        self._insert_cancel = insert_tree_items(
            self.tree, items, batch=500,
            on_done=lambda: self._reapply_cell_tags(self.tree))

    def _reapply_cell_tags(self, tree):
        """v3.9.17 — pasang ulang tag per-cell minus (sort delete+reinsert
        dan clone ⛶ me-reset tag cell; pola deviasi/in-selisih).
        v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list kosong
        = clear overlay)."""
        if self._cell_tags:
            apply_cell_tag(tree, "neg_cell", self._neg_cells)

    def _apply_status(self):
        """v3.9.59 — status kartu atas = teks normal (_status_text) +
        catatan store aktif (bila ada — flash berjalan)."""
        if self._store_note:
            self.status_var.set(f"{self._store_note} · {self._status_text}")
        else:
            self.status_var.set(self._status_text)

    def _consume_store_notes(self):
        """v3.9.59 — bonus (API store agent F, FIX 2f-07/2f-08):
        ``store.last_recovery`` (followup.json korup → backup .bad,
        mulai kosong) & ``store.last_save_error`` (gagal persist —
        disk penuh/file terkunci) kini TAMPIL di tab ini sebagai flash
        status (dulu hanya [WARNING] di log tab 🚀 Proses — jauh dari
        aksi ✓). Flag di-reset SETELAH ditampilkan sekali (supaya tiap
        render tidak mengulang pesan)."""
        msgs = []
        rec = getattr(self.store, "last_recovery", None)
        if rec:
            msgs.append(f"⚠ followup.json korup — {rec}")
            with contextlib.suppress(Exception):
                self.store.last_recovery = None
        err = getattr(self.store, "last_save_error", None)
        if err:
            msgs.append(f"⚠ follow-up TIDAK TERSIMPAN — {err}")
            with contextlib.suppress(Exception):
                self.store.last_save_error = None
        if msgs:
            self._flash_store_note(" · ".join(msgs))

    def _flash_store_note(self, msg: str):
        """Flash catatan store di status kartu (2×FLASH_MS), lalu kembali
        ke teks status normal terbaru."""
        self._store_note = msg
        self._apply_status()
        if self._note_after:
            with contextlib.suppress(Exception):
                self.after_cancel(self._note_after)

        def restore():
            self._note_after = None
            if not self.winfo_exists():
                return
            self._store_note = None
            self._apply_status()

        self._note_after = self.after(FLASH_MS * 2, restore)

    # =========================================================================
    # ✓ KLIK = KELUARKAN (v3.3: iid-based — benar setelah sort)
    # =========================================================================
    def _on_tree_click(self, event):
        tree = event.widget
        # FIX 6e-01 (audit 6-e HIGH / mirror 48-d P0 deviasi_view): clone ⛶
        # generasi lama (dibuka sebelum re-render terakhir — _iid_fp sudah
        # dipetakan ulang) → handler DIABAIKAN senyap; dulu klik ✓ di clone
        # basi MENGHAPUS BARIS SALAH dari followup.json.
        if getattr(tree, "_view_gen", None) not in (None, self._render_gen):
            return
        try:
            if tree.identify_region(event.x, event.y) != "cell":
                return
            # v3.7 FIX: cocokkan NAMA kolom (bukan posisi display '#1') —
            # setelah kolom ✓ disembunyikan, posisi #1 jatuh ke kolom lain
            # → toggle keluarkan-baris terpicu dari kolom yang salah.
            col = identify_to_column(tree, tree.identify_column(event.x))
            if col != "✓":
                return
            row_iid = tree.identify_row(event.y)
        except Exception:
            return
        if not row_iid:
            return
        fp = self._iid_fp.get(row_iid)
        snap = self.store.rows.get(fp)
        if snap:
            # toggle → off (keluarkan); _render dipanggil via listener
            self.store.toggle(fp, snap)

    # =========================================================================
    # AKSI: EXPORT / KOSONGKAN
    # =========================================================================
    def _on_export(self):
        if not self.store.rows:
            messagebox.showinfo(
                "Export", "Daftar follow-up masih kosong.", parent=self)
            return
        filepath = filedialog.asksaveasfilename(
            title="Simpan Daftar Follow Up",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="follow_up.xlsx",
            parent=self,
        )
        if not filepath:
            return

        def work():
            return self.store.export_xlsx(filepath)

        def done(path):
            # FIX C-06 (audit 2-c): frasa instruksi "Kolom PIC / ...
            # diisi petugas" dihapus (aturan UI-clean v3.9.8 — dialog
            # sukses cukup memberi tahu hasil, bukan cara pakai).
            messagebox.showinfo(
                "Export Berhasil",
                f"Daftar follow-up di-export ke:\n{path}",
                parent=self)

        def on_error(e):
            messagebox.showerror(
                "Export Gagal", f"Tidak bisa export:\n{e}", parent=self)

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Mengekspor follow-up…", on_error=on_error)

    def _on_clear(self):
        if not self.store.rows:
            return
        if not messagebox.askyesno(
                "Kosongkan Follow Up",
                f"Hapus SEMUA {len(self.store.rows)} baris dari daftar "
                "follow-up?\n\nCentangan di tab Deviasi/Laporan ikut lepas.",
                parent=self):
            return
        self.store.clear()   # _render via listener

    # =========================================================================
    # ⛶ PERBESAR
    # =========================================================================
    def _maximize(self):
        def filter_setup(new_tree):
            # v3.6: funnel ⧩ + sort jalan juga di window besar
            attach_clone_filters(
                new_tree,
                [c[0] for c in COLUMNS if c[0] != "✓"],
                get_values=self._col_values,
                on_sort=lambda c, d, t=new_tree: self._sort_by(c, reverse=d,
                                                               tree=t))

        win, new_tree = open_tree_maximized(
            self.tree, "Daftar Follow Up",
            setup_tags=lambda t: self._setup_tags(),
            on_double_click=self._on_double_click,
            on_filter_setup=filter_setup,
            on_render_done=self._reapply_cell_tags)  # v3.9.17 tag per-cell
        # FIX 6e-01 (audit 6-e HIGH): catat clone hidup + generasi render
        # saat dibuka (tree clone diberi atribut _view_gen; handler
        # ✓/double-click memeriksanya; clone ditutup saat re-render —
        # mirror deviasi_view _register_clone).
        new_tree._view_gen = self._render_gen
        self._clone_wins.append(win)
        new_tree.bind("<Button-1>", self._on_tree_click, add="+")
        # v3.9.59 — FIX 2e-05: cursor hand2 kolom ✓ ikut aktif di clone ⛶
        new_tree.bind("<Motion>", self._on_tree_motion, add="+")
        return win, new_tree

    def _close_stale_clones(self):
        """FIX 6e-01 (audit 6-e HIGH — mirror deviasi_view): tutup SEMUA
        clone ⛶ yang masih hidup — dipanggil saat _render mengganti baris
        (iid fu_N dipetakan ulang; clone basi men-toggle baris SALAH).
        Window yang sudah ditutup user cukup dibersihkan dari daftar."""
        for w in self._clone_wins:
            try:
                if w.winfo_exists():
                    w.destroy()
            except tk.TclError:
                pass
        self._clone_wins = []

    # =========================================================================
    # SORT (v3.3: engine linear + parse khusus status TL)
    # =========================================================================
    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten."""
        auto_fit_columns(self.tree)

    def _sort_by(self, col: str, reverse: bool = True, tree=None):
        tree = tree if tree is not None else self.tree

        def parse_fu(s):
            # v3.9.59 — FIX 2e-04: parser sort format INDONESIA (mirror
            # default parser widgets v3.9.54 + _parse_num_id deviasi):
            # '1.234' = 1234 · '12,5' = 12.5 · '(1.234)' = -1234 ·
            # '-'/'—' = 0. Dulu koma-dibuang ('1,234.5' EN) — dgn format
            # display baru '1.234,5' akan ter-parse salah skala.
            s = str(s).strip()
            if s in ("Menunggu", "Selesai"):
                return 1 if s == "Menunggu" else 2
            if s in ("-", "", "—"):
                return 0
            neg = s.startswith("(") and s.endswith(")")
            if neg:
                s = s[1:-1]
            s = s.replace(".", "").replace(",", ".")
            v = float(s)
            return -v if neg else v

        sort_tree_by_column(tree, col, reverse=reverse, parse=parse_fu)
        # v3.9.17: delete+reinsert me-reset tag PER-CELL → pasang ulang
        # (identik deviasi/in-selisih — FIX B-03 audit 2-b).
        self._reapply_cell_tags(tree)

    # =========================================================================
    # DOUBLE-CLICK → POPUP DETAIL (v3.3: iid-based — benar setelah sort;
    # double-click di kolom ✓ = toggle keluarkan)
    # =========================================================================
    def _on_double_click(self, event):
        tree = event.widget
        # FIX 6e-01 (audit 6-e HIGH / mirror 48-d P0 deviasi_view): clone ⛶
        # generasi lama → _iid_fp tidak lagi cocok dgn baris clone → popup
        # detail membuka baris SALAH → DIABAIKAN senyap.
        if getattr(tree, "_view_gen", None) not in (None, self._render_gen):
            return
        row_iid = tree.identify_row(event.y)
        if not row_iid:
            return

        # v3.3: double-click sel ✓ = keluarkan baris (bukan popup) —
        # jalan juga saat data source belum tersedia
        # v3.7 FIX: cocokkan NAMA kolom (bukan posisi display '#1')
        try:
            if identify_to_column(tree, tree.identify_column(event.x)) == "✓":
                self._on_tree_click(event)
                return
        except Exception:
            pass

        data = self.get_data() if self.get_data else None
        if data is None or data.empty:
            return

        fp = self._iid_fp.get(row_iid)
        snap = self.store.rows.get(fp)
        if not snap:
            return

        # v3.9.54 FIX (audit 8-a P1-3) — baris asal KOMPARASI: snap
        # 'resto' = bentuk PENDEK ternormalisasi & 'barang' = nama FILE
        # (kapital/spasi bisa beda) → popup detail exact-match vs data
        # app = 0 baris (popup KOSONG). Field 'barang_app'/'resto_app'
        # (v3.9.54 — diisi komparasi bila pair ada di data app) dipakai
        # BILA ada; snap lama tanpa field baru → fallback field lama.
        _barang = snap.get("barang_app") or snap.get("barang")
        _resto = snap.get("resto_app") or snap.get("resto")

        from src.ui.details_popup import show_details_popup
        show_details_popup(
            self.winfo_toplevel(), data,
            nama_barang=_barang,
            jenis=None,
            tanggal=None,
            filters={"NAMA RESTO": _resto} if _resto else None,
        )
