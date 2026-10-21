"""
widgets.py — Blok bangunan UI Stock Monitoring (v3.0 redesign → v3.9).

Semua komponen dipakai lintas view supaya tampilan konsisten:
- Card            : kartu putih + border slate + judul opsional
- KpiCard/KpiRow  : kartu metrik (label kecil, angka besar, aksen warna)
- Toolbar         : bar gelap slate-900 di atas jendela (judul + aksi)
- StatusBar       : bar status bawah (dot status + teks + info kanan)
- EmptyState      : placeholder saat belum ada data + tombol CTA
- AccentButton    : tombol teal solid (aksi utama)
- DangerButton    : tombol putih teks merah (aksi berbahaya)
- make_tree       : Treeview ter-style lengkap dgn scrollbar
- LegendRow       : chip legenda warna (untuk status/CEK)
- StatusDot       : titik warna + teks status
- TableExpander   : (v3.9) tombol ⤢ Perbesar Tabel ala Waste — ciutkan
                    baris kontrol supaya tabel memakai tinggi penuh

v3.9 "STYLE WASTE" (permintaan user: tiru repo Waste mulai dari tombol
filternya, perbesar tabelnya, dll — warna sudah identik sejak v3.0):
- funnel header filter ala Waste: MERAH saat aktif, idle = isi terang
  + outline gelap; ikon 11x8 → 13x11.
- theme.py: font tabel 9 → 10 + rowheight 26 → 30 (tabel besar).
- TableExpander ⤢ + tombol ⛶ "Layar Penuh" di semua view.
"""
from __future__ import annotations

import contextlib
import gc as _gc
import math
import re
import sys
import threading
import time as _time
import tkinter as tk
from tkinter import messagebox as _mb
from tkinter import ttk

# v3.9.44 — re-export helper filter kategori dari pipeline.helpers (satu
# sumber kebenaran; arah import UI→pipeline = pola app.py/nominal_common):
# mask baris TANPA kategori master (NaN/blank/'nan') — dipakai passthrough
# filter KATEGORI deviasi_view/nominal_resto_view/pivot_view. Akar
# "BUMBU PASTA KUAH MLGPAR masih belum ada di tab Deviasi GR": item
# 42.17-only 100383 tidak ada di master '21. DBS Kategori' user (hanya
# varian (V.20)) → KATEGORI NaN → filter default 'Deviasi' menyembunyikan
# barisnya. Kebijakan: master tak kenal ≠ disembunyikan — baris tampil di
# seleksi kategori apa pun (dokumentasi lengkap di pipeline/helpers.py).
# v3.9.45 — passthrough kini HANYA seleksi default 'Deviasi'
# (kategori_passthrough; keluhan "ganti kategori tidak terjadi apa apa" —
# 90% baris '-' buat passthrough universal = filter no-op) + entry
# combobox KATEGORI_BLANK_LABEL '(Tanpa Kategori)'.
# v3.9.49 — kategori gabungan default Rekap Mentah (KATEGORI_DEFAULT_
# LABEL + helper multi-nilai) — re-export utk semua view ber-filter
# kategori.
from ..pipeline.helpers import KATEGORI_BLANK_LABEL as KATEGORI_BLANK_LABEL  # noqa: PLC0414
from ..pipeline.helpers import KATEGORI_DEFAULT_LABEL as KATEGORI_DEFAULT_LABEL  # noqa: PLC0414
from ..pipeline.helpers import KATEGORI_REKAP_VALUES as KATEGORI_REKAP_VALUES  # noqa: PLC0414
from ..pipeline.helpers import kategori_blank_mask as kategori_blank_mask  # noqa: PLC0414
from ..pipeline.helpers import kategori_filter_mask as kategori_filter_mask  # noqa: PLC0414
from ..pipeline.helpers import (
    kategori_has_default_values as kategori_has_default_values,  # noqa: PLC0414
)
from ..pipeline.helpers import (
    kategori_match_mask as kategori_match_mask,  # noqa: PLC0414
)
from ..pipeline.helpers import kategori_passthrough as kategori_passthrough  # noqa: PLC0414
from .theme import (
    C_ACCENT,
    C_ACCENT_DARK,
    C_ACCENT_HOVER,
    C_ACCENT_SOFT,
    C_BG,
    C_BORDER,
    C_BORDER_DARK,
    C_CARD,
    C_GREEN,
    C_HEADER,
    C_LOG_BG,
    C_LOG_FG,
    C_RED,
    C_RED_SOFT,
    C_TEXT_MUTED,
    C_TEXT_SOFT,
    FIND_CUR_BG,
    FIND_CUR_TAG,
    FIND_HIT_BG,
    FIND_HIT_TAG,
    bind_ctrl_zoom,
    font,
    mono,
    setup_tree_tags,
    ui_scale,
)

# v3.9.59 — fix 2b-07 (audit 2-b): durasi flash status "TERSALIN" kini
# SATU konstanta bersama (dulu 3000ms di in_selisih_view/details_popup
# vs 2500ms di app.py — feedback copy tidak seragam antar permukaan).
# View/app cukup mengimpor konstanta ini untuk after(FLASH_MS, ...).
FLASH_MS = 2500

# Tombol aksen/berbahaya pakai tk.Button murni: kontrol penuh atas warna
# (ttk button tidak bisa diwarnai per-widget tanpa mendaftarkan style baru).
# v3.9.33 — AUDIT FIX (48-c HIGH-1): TANPA font di sini — dulu
# `font=font(10, "bold")` dipanggil di IMPORT TIME (sebelum tk.Tk()
# ada) → theme.font_family() memaksa resolusi pre-root dan mengunci
# fallback "DejaVu Sans" (Segoe UI/Noto tak pernah terpakai di Windows).
# Kini family di-resolve LAZY di konstruktor tombol (selalu pasca-root).
_BTN_BASE = dict(
    bd=0, highlightthickness=0, relief="flat",
    cursor="hand2",
    activeforeground="#ffffff", padx=14, pady=7,
)


def fmt_int_id(v) -> str:
    """FIX C-03: format integer gaya Indonesia — 1.234.567 (bukan 1,234,567)."""
    try:
        n = round(float(v))
    except (TypeError, ValueError):
        return str(v)
    return f"{n:,}".replace(",", ".")


# FIX B-19 (audit 2-b): key sort utk daftar nilai popup filter — nilai
# numerik format Indonesia ("1.234" / "12,5" / "(1.234)" / "12,5%")
# diurutkan secara NUMERIK; dulu leksikografis ("1.000" < "999").
_VALUE_NUM_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*(?:,\d+)?$|^\d+(?:,\d+)?$")


def _filter_value_sort_key(v: str):
    """Key tuple (numerik_dulu, angka, kunci_teks) — teks non-numerik
    masuk grup kedua (urut NATURAL v3.9.62), angka grup pertama (naik).
    v3.9.51: prefiks 'Rp ' (currency — fmt_rp_cell) dibuang dulu supaya
    nilai nominal tetap terurut numerik di popup filter ⧩.
    v3.9.62: cabang teks memakai natural_key ("Nomor PO 2" < "Nomor
    PO 10" — dulu leksikografis).
    v3.9.64: prefiks '+' juga dibuang (fmt_pct_cell bertanda — '+12,5%'
    dulu masuk grup TEKS sementara '-8,3%' numerik; audit 15-c F-05)."""
    s = str(v).strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1].strip()
    elif s.startswith("-"):
        neg, s = True, s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if s[:2].upper() == "RP":
        s = s[2:].lstrip()
    if not s or not _VALUE_NUM_RE.match(s):
        return (1, 0.0, natural_key(v))
    try:
        num = float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return (1, 0.0, natural_key(v))
    return (0, -num if neg else num, str(v))


# v3.9.62 — SORT NATURAL (referensi: fitur "natural sorting" tksheet):
# fallback string sort dulu memakai urutan Leksikografis — "Barang 10"
# < "Barang 2" (karakter '1' < '2'), "R02-777" < "R02-9". Kolom teks
# yang MENYEMBUNYIKAN angka (Nama Barang, Nomor PO, kode rak) terurut
# salah di mata pengguna.
_NATURAL_SPLIT_RE = re.compile(r"(\d+)")


def natural_key(value) -> tuple:
    """v3.9.62 — kunci sort NATURAL (campuran angka + teks).

    String dipecah per run digit: tiap potongan jadi tuple
    (jenis, angka, teks_casefold) — run digit dibandingkan NUMERIK,
    teks CASE-INSENSITIVE ("item" == "Item"). Contoh:
        natural_key("Barang 2")  < natural_key("Barang 10")
        natural_key("R02-9")     < natural_key("R02-777")
        natural_key("")          == ()  (selalu paling awal ascending)

    Pemakaian: (1) fallback `sort_tree_by_column` saat kolom tak terurut
    numerik (jalur parse-numerik TIDAK tersentuh); (2) cabang teks
    `_filter_value_sort_key` (daftar nilai popup filter ⧩).
    Stabil: nilai dgn kunci sama mempertahankan urutan (sort Python
    stabil)."""
    out = []
    parts = _NATURAL_SPLIT_RE.split(str(value))
    for idx, part in enumerate(parts):
        if not part:
            continue
        if idx % 2:            # run digit → numerik
            out.append((1, int(part), ""))
        else:                  # potongan teks → casefold
            out.append((0, 0, part.casefold()))
    return tuple(out)


def _ellipsize(text: str, meas, max_px: int) -> str:
    """v3.9.59 — fix 2a-02/2b-01: potong teks + '…' agar muat ``max_px``.

    ``meas`` = callable Font.measure (teks → lebar px). Teks yang sudah
    muat dikembalikan APA ADANYA. Pemotongan memakai binary-search jumlah
    karakter (log₂ n panggilan measure — murah utk teks ratusan char)."""
    try:
        if max_px <= 0 or meas(text) <= max_px:
            return text
        lo, hi = 1, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if meas(text[:mid] + "…") <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + "…"
    except tk.TclError:
        return text


def validated_tgl_entry(var, *, lo: int, hi: int, fallback: int,
                        label: str, parent) -> int:
    """FIX B-02: validasi input tanggal KONSISTEN di semua view — warning
    + revert entry (pola yang sudah dipakai tab Deviasi), menggantikan
    fallback senyap di Pivot & Rekap Selisih IN. Panggil dari MAIN thread."""
    raw = (var.get() or "").strip()
    val = None
    # FIX B-12 (audit 2-b): int(float(raw)) MELANTAI input pecahan secara
    # senyap ("7.9" → 7 dipakai tanpa memberitahu user). Kini hanya
    # bilangan BULAT yang diterima ("7", " 25 ", "7.0"); pecahan ditolak
    # dengan warning + revert — konsisten dengan penolakan "7,9".
    try:
        f = float(raw)
        if f == int(f):
            val = int(f)
    except (TypeError, ValueError, OverflowError):
        val = None
    if val is None or not (lo <= val <= hi):
        _mb.showwarning("Input tidak valid",
                        f"{label} harus angka {lo}–{hi}.",
                        parent=parent.winfo_toplevel())
        var.set(str(fallback))
        return fallback
    var.set(str(val))
    return val


def _take_grab(win):
    """FIX 6e-03 (audit 6-e MEDIUM) — ambil grab popup + CATAT pemegang
    grab sebelumnya. Popup AutoFilter/Panel Kolom membuka grab baru →
    Tk MENGGANTI grab lama (modal induk — mis. DetailsPopup — kehilangan
    modalitasnya PERMANEN setelah popup ditutup). Dipulihkan oleh
    _restore_grab() di SEMUA jalur tutup."""
    prev = None
    with contextlib.suppress(tk.TclError):
        prev = win.grab_current()
    win._prev_grab = (prev if (prev is not None and prev is not win
                               and hasattr(prev, "winfo_exists"))
                      else None)
    with contextlib.suppress(tk.TclError):
        win.grab_set()


def _restore_grab(win):
    """FIX 6e-03 — pulihkan grab pemegang sebelumnya (bila masih hidup).
    Dipanggil SEBELUM destroy popup (setelah grab_release bila ada)."""
    prev = getattr(win, "_prev_grab", None)
    if prev is None:
        return
    if prev.winfo_exists():
        with contextlib.suppress(tk.TclError):
            prev.grab_set()


class AccentButton(tk.Button):
    """Tombol aksi utama — teal solid, putih teks, hover teal-800."""

    def __init__(self, parent, text: str, command=None, **kw):
        # v3.9.33 — AUDIT FIX: font lazy (pasca-root) — _BTN_BASE tak lagi
        # membekukan family fallback di import time.
        cfg = dict(_BTN_BASE, bg=C_ACCENT, fg="#ffffff",
                   activebackground=C_ACCENT_HOVER, text=text,
                   command=command, font=font(10, "bold"))
        cfg.update(kw)
        super().__init__(parent, **cfg)
        self.bind("<Enter>", lambda e: self._set_bg(C_ACCENT_HOVER, enabled=True))
        self.bind("<Leave>", lambda e: self._set_bg(C_ACCENT, enabled=True))

    def _set_bg(self, color: str, enabled: bool = True):
        if str(self.cget("state")) == "disabled":
            return
        self.configure(background=color)

    def set_enabled(self, enabled: bool):
        """Enable/disable dengan warna sesuai state."""
        if enabled:
            self.configure(state="normal", bg=C_ACCENT, fg="#ffffff",
                           activebackground=C_ACCENT_HOVER)
        else:
            self.configure(state="disabled", bg="#94a3b8", fg="#e2e8f0",
                           activebackground="#94a3b8")


class DangerButton(tk.Button):
    """Tombol stop/batal — putih, teks merah, hover latar merah lembut."""

    def __init__(self, parent, text: str, command=None, **kw):
        # v3.9.33 — AUDIT FIX: font lazy (pasca-root), pola AccentButton.
        cfg = dict(_BTN_BASE, bg=C_CARD, fg=C_RED,
                   activebackground=C_RED_SOFT, activeforeground=C_RED,
                   text=text, command=command, font=font(10, "bold"))
        cfg.update(kw)
        super().__init__(parent, **cfg)
        self.bind("<Enter>", lambda e: self._set_bg(C_RED_SOFT))
        self.bind("<Leave>", lambda e: self._set_bg(C_CARD))

    def _set_bg(self, color: str):
        if str(self.cget("state")) == "disabled":
            return
        self.configure(background=color)

    def set_enabled(self, enabled: bool):
        if enabled:
            self.configure(state="normal", bg=C_CARD, fg=C_RED,
                           activebackground=C_RED_SOFT)
        else:
            self.configure(state="disabled", bg="#f1f5f9", fg=C_TEXT_SOFT,
                           activebackground="#f1f5f9")


class GhostButton(ttk.Button):
    """Tombol sekunder — ttk default ter-style (putih + border slate).

    FIX A-02 (audit 2-a): set_enabled API seragam — visual dim datang
    dari style.map("TButton", disabled) di theme.py; call-site kini punya
    satu pola (set_enabled) untuk SEMUA kelas tombol (Accent/Danger/Ghost/
    Toolbar), bukan campuran configure(state) polos.
    """

    def __init__(self, parent, text: str, command=None, **kw):
        # v3.9.59 — fix 2a-07/2b-10 (audit 2-a/2-b): cursor hand2 seperti
        # Accent/Danger/Toolbar — affordance klik konsisten di semua kelas
        # tombol (ttk.Button menerima opsi cursor; caller bisa override).
        kw.setdefault("cursor", "hand2")
        super().__init__(parent, text=text, style="TButton", command=command, **kw)

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state=("normal" if enabled else "disabled"))


class Card(tk.Frame):
    """Kartu putih: border 1px slate-200, padding konsisten.

    Pakai grid/pack di dalam. Judul opsional dirender sebagai baris pertama.
    """

    def __init__(self, parent, title: str = "", subtitle: str = "",
                 padding: int = 12, **kw):
        super().__init__(parent, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        self._padding = padding

        self.inner = tk.Frame(self, bg=C_CARD)
        if title:
            head = tk.Frame(self, bg=C_CARD)
            head.pack(fill="x", padx=padding, pady=(padding, 0))
            tk.Label(head, text=title, bg=C_CARD, fg=C_HEADER,
                     font=font(12, "bold")).pack(anchor="w")
            if subtitle:
                tk.Label(head, text=subtitle, bg=C_CARD, fg=C_TEXT_MUTED,
                         font=font(9)).pack(anchor="w", pady=(2, 0))
            self.inner.pack(fill="both", expand=True,
                            padx=padding, pady=(8 if subtitle else 6, padding))
        else:
            self.inner.pack(fill="both", expand=True, padx=padding, pady=padding)

    def body(self) -> tk.Frame:
        return self.inner


class KpiCard(tk.Frame):
    """Kartu KPI: aksen warna kiri, label kecil uppercase, angka besar, sub-teks.

    set_value(value, subtitle, accent) untuk update cepat.
    """

    def __init__(self, parent, label: str, value: str = "—",
                 subtitle: str = "", accent: str = C_ACCENT, **kw):
        super().__init__(parent, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        self._accent = accent

        row = tk.Frame(self, bg=C_CARD)
        row.pack(fill="both", expand=True, padx=12, pady=10)
        self._bar = tk.Frame(row, bg=accent, width=4)
        self._bar.pack(side="left", fill="y", padx=(0, 10))
        txt = tk.Frame(row, bg=C_CARD)
        txt.pack(side="left", fill="both", expand=True)

        self._label_var = tk.StringVar(value=label.upper())
        tk.Label(txt, textvariable=self._label_var, bg=C_CARD, fg=C_TEXT_MUTED,
                 # FIX A-08: label KPI 8→9pt — teks terkecil jangan untuk
                 # label kartu KPI yang penting (nyaris tak terbaca 1080p).
                 font=font(9, "bold"), anchor="w").pack(fill="x")

        self._value_var = tk.StringVar(value=value)
        tk.Label(txt, textvariable=self._value_var, bg=C_CARD, fg=C_HEADER,
                 font=font(16, "bold"), anchor="w").pack(fill="x", pady=(2, 0))

        self._sub_var = tk.StringVar(value=subtitle)
        # v3.9.59 fix 2a-01 (audit 2-a): C_TEXT_SOFT #94a3b8 = 2,56:1 di
        # kartu putih (WCAG AA 4,5:1 gagal) — teks panduan status KPI
        # (mis. 'lihat log untuk detail' saat ERROR) nyaris tak terbaca.
        # C_TEXT_MUTED #64748b = 4,76:1 (lolos AA).
        self._sub = tk.Label(txt, textvariable=self._sub_var, bg=C_CARD,
                             fg=C_TEXT_MUTED, font=font(9), anchor="w")
        if subtitle:
            self._sub.pack(fill="x")

    def set_value(self, value: str, subtitle: str | None = None,
                  accent: str | None = None):
        self._value_var.set(value)
        if subtitle is not None:
            if not self._sub.winfo_ismapped():
                self._sub.pack(fill="x")
            self._sub_var.set(subtitle)
        if accent is not None and accent != self._accent:
            self._accent = accent
            self._bar.configure(bg=accent)


class KpiRow(tk.Frame):
    """Barisan KpiCard yang sama lebar (grid weight=1).

    PENTING: KpiCard harus dibuat dengan KpiRow sebagai parent-nya:
        kpi = KpiRow(parent)
        card = KpiCard(kpi, "Label", "—", "sub")
        kpi.add(card)
    (bukan in_= sibling — stacking order Tk membuat widget tak terlihat.)
    """

    def __init__(self, parent, cards: list[KpiCard] | None = None, **kw):
        super().__init__(parent, bg=C_BG, **kw)
        self._cards: list[KpiCard] = []
        if cards:
            for c in cards:
                self.add(c)

    def add(self, card: KpiCard):
        # v3.9.59 — fix 2a-08/2b-08 (audit 2-a/2-b):
        # (a) grid columnconfigure uniform → semua kolom DIPAKSA sama lebar
        #     (dulu weight=1 saja membagi ruang SISA — lebar kartu tetap
        #     beda ±20px, tepi kanan baris KPI tak sejajar);
        # (b) padx SIMETRIS (4,4) per kartu — dulu conditional mati
        #     ``0 if self._cards else 0`` + (0,8): tepi kiri 0px vs kanan
        #     8px DAN kartu terakhir 8px lebih lebar dari yang lain.
        #     Celah antar kartu = 4+4 = 8px (sama seperti desain lama);
        #     tepi luar kiri/kanan = 4px masing-masing (simetris).
        col = len(self._cards)
        card.grid(row=0, column=col, sticky="nsew", padx=(4, 4))
        self._cards.append(card)
        self.grid_columnconfigure(col, weight=1, uniform="kpi")


class Toolbar(tk.Frame):
    """Bar gelap slate-900 paling atas: ikon+judul aplikasi, versi, aksi kanan.

    add_action(text, command, danger=False, accent=False) → tombol.

    v3.9.59 — fix 2a-03 (audit 2-a): tinggi bar mengikuti ZOOM aktif
    (``max(48, 48 × ui_scale)``). Dulu fixed 48px + pack_propagate(False)
    → font named ter-zoom membesar tapi bar tetap → judul aplikasi
    terpotong mulai ±140% (probe ua_clip3: 47/32px @200%). Pembaruan
    dipicu <Configure> bar (jendela di-resize oleh zoomer) DAN
    <Configure> label judul (named font di-rescale rescale_named_fonts
    → label re-layout → event).
    """

    BASE_H = 48

    def __init__(self, parent, title: str, version: str = "", **kw):
        super().__init__(parent, bg=C_HEADER, height=self._scaled_h(), **kw)
        self.pack_propagate(False)

        left = tk.Frame(self, bg=C_HEADER)
        left.pack(side="left", padx=(16, 0), pady=8)
        self._title_lbl = tk.Label(left, text=title, bg=C_HEADER,
                                    fg="#f1f5f9", font=font(13, "bold"))
        self._title_lbl.pack(side="left")
        if version:
            tk.Label(left, text=f" v{version} ", bg="#1e293b", fg="#5eead4",
                     font=font(8, "bold"), padx=8, pady=2).pack(
                side="left", padx=(10, 0))

        self._actions = tk.Frame(self, bg=C_HEADER)
        self._actions.pack(side="right", padx=(8, 16), pady=8)
        # 2a-03: hitung ulang tinggi saat zoom berubah (dua jalur lihat
        # docstring kelas; add="+" supaya tidak mengganti binding lain).
        self.bind("<Configure>", self._refresh_height, add="+")
        self._title_lbl.bind("<Configure>", self._refresh_height, add="+")

    @classmethod
    def _scaled_h(cls) -> int:
        try:
            return max(cls.BASE_H, round(cls.BASE_H * ui_scale()))
        except (TypeError, ValueError):
            return cls.BASE_H

    def _refresh_height(self, _event=None):
        h = self._scaled_h()
        with contextlib.suppress(tk.TclError):
            if int(self.cget("height")) != h:
                self.configure(height=h)

    def add_action(self, text: str, command=None, accent: bool = False,
                   danger: bool = False) -> tk.Button:
        bg = C_ACCENT if accent else "#1e293b"
        fg = "#ffffff" if accent else "#e2e8f0"
        hover = C_ACCENT_HOVER if accent else "#334155"
        btn = tk.Button(
            self._actions, text=text, command=command,
            bg=bg, fg=fg, activebackground=hover, activeforeground="#ffffff",
            bd=0, relief="flat", highlightthickness=0, cursor="hand2",
            font=font(9, "bold"), padx=12, pady=5,
        )
        btn.pack(side="left", padx=(6, 0))
        btn.bind("<Enter>", lambda e: btn.configure(background=hover)
                 if str(btn.cget("state")) != "disabled" else None)

        def _leave(_e=None):
            # FIX B-10 (audit 2-b): Leave saat disabled jangan menimpa
            # warna dim dari _set_enabled — dulu tombol disabled kembali
            # tampak berwarna normal setelah cursor lewat (tampak aktif
            # palsu padahal tidak bisa diklik).
            if str(btn.cget("state")) == "disabled":
                return
            btn.configure(background=bg)

        btn.bind("<Leave>", _leave)

        def _set_enabled(enabled: bool) -> None:
            # FIX A-01/A-02: state disabled harus terlihat dim & konsisten —
            # sebelumnya tombol toolbar (mis. 💾 Export) tetap berwarna teal
            # saat disabled sehingga TAMPAK AKTIF padahal tidak bisa diklik.
            if enabled:
                btn.configure(state="normal", background=bg, fg=fg)
            elif accent:
                btn.configure(state="disabled", background="#94a3b8",
                              fg="#1e293b")
            else:
                btn.configure(state="disabled", background="#0f172a",
                              fg="#64748b")

        btn.set_enabled = _set_enabled  # type: ignore[attr-defined]
        return btn


class StatusDot(tk.Frame):
    """Titik warna + teks status (mis. '● SIAP — menunggu pipeline').

    v3.9.59 — fix 2a-02: ``set()`` menyimpan teks PENUH di ``_full``;
    tampilan bisa dipotong '…' oleh StatusBar._truncate_status() bila
    ruang kurang (badge kanan tidak tertimpa). ``_var`` tetap variabel
    tampilan (API test/app lama: statusbar.dot._var.get()).
    """

    def __init__(self, parent, text: str = "SIAP", color: str = C_GREEN, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        self._canvas = tk.Canvas(self, width=10, height=10, bg=C_CARD,
                                 highlightthickness=0, bd=0)
        self._canvas.pack(side="left", padx=(0, 6))
        self._dot = self._canvas.create_oval(1, 1, 9, 9, fill=color,
                                             outline=color)
        self._color = color
        self._full = text
        self._fobj = font(9, "bold")
        self._var = tk.StringVar(value=text)
        self._lbl = tk.Label(self, textvariable=self._var, bg=C_CARD,
                             fg=C_HEADER, font=self._fobj)
        self._lbl.pack(side="left")

    def set(self, text: str, color: str):
        self._canvas.itemconfigure(self._dot, fill=color, outline=color)
        self._color = color
        self._full = text
        self._var.set(text)


class StatusBar(tk.Frame):
    """Bar status bawah: dot+kiri, info kanan (versi). Border atas slate.

    v3.9.59:
    - fix 2a-02: teks status panjang DIPOTONG '…' selebar ruang tersisa
      (teks penuh tetap disimpan dot._full) — dulu teks ±243 char menimpa
      / mengusir badge versi-zoom keluar bar (probe ua_layout2: overlap
      120px @1020; badge hilang sepenuhnya @200%). Dihitung ulang saat
      set_status/set_right dan <Configure> (resize jendela — termasuk
      resize oleh zoomer).
    - fix 2a-03: tinggi bar mengikuti zoom (max(34, 34 × ui_scale)) —
      dulu fixed 34px → badge kanan terpotong 2px @100% dan setengah
      @200% (probe ua_clip3). set_right() dipanggil app._update_zoom_badge
      di SETIAP perubahan zoom → tinggi ikut di-refresh saat zoom.
    """

    BASE_H = 34
    # offset lebar tetap: padx 12×2 (frame kiri) + dot 10 + padx 6
    # + padx 12×2 (label kanan) + tepi 2.
    _FIXED_W = 24 + 16 + 24 + 2

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        self.configure(height=self._scaled_h())
        self.pack_propagate(False)

        left = tk.Frame(self, bg=C_CARD)
        left.pack(side="left", fill="y", padx=12, pady=6)
        self.dot = StatusDot(left, "SIAP — menunggu pipeline", C_GREEN)
        self.dot.pack(side="left")

        self._right_var = tk.StringVar(value="")
        self._right_lbl = tk.Label(self, textvariable=self._right_var,
                                   bg=C_CARD, fg=C_TEXT_MUTED, font=font(9))
        # pady 7 (bukan 8): border 1px + propagate-off memakan 2px interior
        # — pady 8 menyisakan 16px < req 17px = badge ter-clip 1px di 100%
        # (audit 2a-03: "di 100% badge versi pun ter-clip 1-2px").
        self._right_lbl.pack(side="right", padx=12, pady=7)
        self.bind("<Configure>", self._on_configure, add="+")

    @classmethod
    def _scaled_h(cls) -> int:
        try:
            return max(cls.BASE_H, round(cls.BASE_H * ui_scale()))
        except (TypeError, ValueError):
            return cls.BASE_H

    # -- 2a-03: tinggi × zoom ------------------------------------------------
    def _refresh_height(self):
        h = self._scaled_h()
        with contextlib.suppress(tk.TclError):
            if int(self.cget("height")) != h:
                self.configure(height=h)

    def _on_configure(self, _event=None):
        self._refresh_height()
        self._truncate_status()

    # -- 2a-02: potong teks kiri agar badge kanan utuh ------------------------
    def _truncate_status(self):
        """Tampilkan dot._full utuh bila muat; '…' bila melebihi ruang
        antara dot kiri dan badge kanan. No-op sebelum ter-layout
        (winfo_width < 60 — <Configure> memicu ulang saat ter-map)."""
        full = self.dot._full
        if not full:
            return
        try:
            sb_w = self.winfo_width()
            if sb_w < 60:
                return
            self.update_idletasks()   # lebar badge terbaru (teks baru saja
                                      # di-set / font ter-rescale zoom)
            right_w = self._right_lbl.winfo_reqwidth() or 0
            avail = sb_w - self._FIXED_W - right_w
            if avail <= 0:
                return
            meas = getattr(self.dot._fobj, "measure", None)
            if meas is None:        # font() tuple fallback (pra-root)
                return
            shown = _ellipsize(full, meas, avail)
        except (tk.TclError, AttributeError):
            return
        if self.dot._var.get() != shown:
            self.dot._var.set(shown)

    def set_status(self, text: str, color: str = C_GREEN):
        self.dot.set(text, color)
        self._truncate_status()

    def set_right(self, text: str):
        self._right_var.set(text)
        # 2a-03: set_right dipanggil _update_zoom_badge (app) tiap zoom
        # berubah → refresh tinggi + lebar badge di hitungan potongan.
        self._refresh_height()
        self._truncate_status()


class EmptyState(tk.Frame):
    """Placeholder besar saat belum ada data: ikon + judul + sub + tombol CTA.

    on_cta: callback tombol (biasanya: pindah ke tab Proses).
    """

    def __init__(self, parent, icon: str = "📭", title: str = "Belum ada data",
                 subtitle: str = "", cta_text: str = "🚀 Jalankan Pipeline",
                 on_cta=None, **kw):
        super().__init__(parent, bg=C_CARD, highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        # Frame center adaptif (FIX B-11 audit 2-b): dulu FIXED 520x260 —
        # di jendela sempit (mis. < 560px lebar) konten ikon/judul/CTA
        # TERPOTONG senyap. Kini ukuran center mengikuti ukuran widget
        # (clamp maks 520x260) lewat event <Configure>.
        center = tk.Frame(self, bg=C_CARD)
        center.place(relx=0.5, rely=0.5, anchor="center",
                     width=520, height=260)
        center.pack_propagate(False)
        self._center = center
        self._subtitle_lbl = None

        tk.Label(center, text=icon, bg=C_CARD, font=font(40)).pack(
            pady=(28, 0))
        tk.Label(center, text=title, bg=C_CARD, fg=C_HEADER,
                 font=font(13, "bold")).pack(pady=(6, 2))
        if subtitle:
            self._subtitle_lbl = tk.Label(
                center, text=subtitle, bg=C_CARD, fg=C_TEXT_MUTED,
                font=font(10), wraplength=420, justify="center")
            self._subtitle_lbl.pack()
        if on_cta is not None and cta_text:
            AccentButton(center, text=cta_text, command=on_cta).pack(
                pady=(14, 20))
        else:
            # tanpa CTA: jaga padding bawah agar frame tetap proporsional
            tk.Frame(center, bg=C_CARD, height=20).pack()
        self.bind("<Configure>", self._resize_center, add="+")

    def _resize_center(self, event=None):
        """FIX B-11: kecilkan frame center saat widget sempit — konten
        tetap utuh (ikon/judul/CTA tidak terpotong)."""
        try:
            w = max(240, self.winfo_width())
            h = max(160, self.winfo_height())
            cw, ch = min(520, w - 24), min(260, h - 24)
            self._center.place(relx=0.5, rely=0.5, anchor="center",
                               width=cw, height=ch)
            if self._subtitle_lbl is not None:
                self._subtitle_lbl.configure(wraplength=max(160, cw - 100))
        except tk.TclError:
            return


class LegendRow(tk.Frame):
    """Baris chip legenda: titik warna + label (untuk CEK / Status Audit)."""

    def __init__(self, parent, items: list[tuple[str, str]], bg: str = C_CARD, **kw):
        """items: list [(label, warna_hex)]"""
        super().__init__(parent, bg=bg, **kw)
        for label, color in items:
            chip = tk.Frame(self, bg=bg)
            chip.pack(side="left", padx=(0, 14))
            cv = tk.Canvas(chip, width=9, height=9, bg=bg,
                           highlightthickness=0, bd=0)
            cv.pack(side="left", padx=(0, 5))
            cv.create_oval(0, 0, 8, 8, fill=color, outline=color)
            tk.Label(chip, text=label, bg=bg, fg=C_TEXT_MUTED,
                     font=font(9)).pack(side="left")  # FIX A-08: legend


def make_tree(parent, columns: list[str], show: str = "headings",
              extra_tags: dict | None = None) -> ttk.Treeview:
    """Buat Treeview ter-style lengkap dgn scrollbar v+h. Return tree.

    Kolom diatur oleh pemanggil (column/heading per view).
    v3.9.32: selectmode "extended" (multi-select) — lihat enable_multi_select.
    """
    frame = tk.Frame(parent, bg=C_CARD)
    frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(frame, columns=columns, show=show, selectmode="extended")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    setup_tree_tags(tree, extra_tags)
    tree._sm_frame = frame  # untuk akses layout jika perlu
    enable_multi_select(tree)  # v3.9.32
    # v3.9.42 — konsistensi interaksi (audit 61-c P3): tree buatan
    # make_tree (info_tree tab ⚙, dialog 🔄 Refresh) kini punya resize
    # kolom manual + roda halus 1-baris/notch (dulu default 3 baris/
    # notch — inkonsisten dgn semua view).
    enable_col_resize(tree)
    return tree


def _tsv_cell(v) -> str:
    """v3.9.33 — AUDIT FIX (48-f HIGH-#7): nilai ber-tab/newline diratakan
    ke spasi supaya satu baris TSV tetap = satu record."""
    return str(v).replace("\t", " ").replace("\n", " ").replace("\r", " ")


# FIX 6b-02 (audit 6-b): sufiks panah arah sort yang ditempel _set_sort_arrow
# ke teks heading — JANGAN ikut tersalin ke header TSV Ctrl+C / terukur oleh
# auto_fit (satu konstanta bersama dgn _set_sort_arrow).
_SORT_ARROW_MARKS = (" \u2193", " \u2191")   # " ↓", " ↑"


def _strip_sort_arrow(text: str) -> str:
    """FIX 6b-02 — buang sufiks panah sort (" ↓"/" ↑") dari teks heading."""
    for m in _SORT_ARROW_MARKS:
        if text.endswith(m):
            return text[: -len(m)]
    return text


def tree_selection_tsv(tree: ttk.Treeview) -> str:
    """v3.9.33 — AUDIT FIX (48-f HIGH-#7): susun seleksi tree jadi teks TSV.

    Baris pertama = HEADER: label '#0' (bila tree hierarki menampilkannya)
    + display-name tiap kolom. Baris berikut = SATU baris per iid terpilih
    (tree.item(iid, "values") di-tab-join). Tree hierarki (pivot parent):
    baris parent disalin APA ADANYA (values-nya sudah agregat) + teks #0
    sebagai sel pertama — anak TIDAK di-flatten ke baris parent.

    FIX 6b-02 (audit 6-b): header diambil dari teks heading TANPA panah
    sort (↓/↑) — dulu "Nama Barang ↓" ikut tersalin ke Excel.
    FIX 6b-08 (audit 6-b): kolom mengikuti URUTAN TAMPILAN
    (displaycolumns) — kolom yang disembunyikan ◱ Kolom TIDAK ikut
    tersalin; nilai values[] tetap diindeks LOGIS lalu dipetakan ke
    kolom display."""
    # FIX 6b-08: kolom display (urutan tampilan), bukan tree["columns"].
    cols = display_data_columns(tree)
    use_tree_col = False
    try:
        # deteksi kolom #0 (kompatibel Tk 8 & 9 — cget tuple vs string)
        raw = tree.cget("show")
        parts = (" ".join(str(x) for x in raw)
                 if isinstance(raw, (tuple, list)) else str(raw))
        if "tree" in parts and str(tree.heading("#0", "text") or "").strip():
            use_tree_col = True
    except tk.TclError:
        pass
    # FIX 6b-08: posisi LOGICAL tiap kolom display utk index values[].
    try:
        logical = [str(c) for c in (tree["columns"] or [])]
    except tk.TclError:
        logical = []
    col_pos = {c: i for i, c in enumerate(logical)}
    headers = []
    if use_tree_col:
        headers.append(_tsv_cell(_strip_sort_arrow(
            str(tree.heading("#0", "text") or ""))))
    for c in cols:
        try:
            headers.append(_tsv_cell(_strip_sort_arrow(
                str(tree.heading(c, "text") or c))))
        except tk.TclError:
            headers.append(_tsv_cell(c))
    lines = ["\t".join(headers)]
    for iid in tree.selection():
        vals = list(tree.item(iid, "values") or [])
        row = []
        if use_tree_col:
            row.append(_tsv_cell(tree.item(iid, "text")))
        # FIX 6b-08: satu sel per kolom DISPLAY (hidden kolom dilewati).
        for c in cols:
            k = col_pos.get(c)
            row.append(_tsv_cell(vals[k])
                       if k is not None and 0 <= k < len(vals) else "")
        lines.append("\t".join(row))
    return "\n".join(lines)


def copy_tree_selection_tsv(tree: ttk.Treeview) -> int:
    """v3.9.33 — AUDIT FIX (48-f HIGH-#7): salin SEMUA baris terpilih ke
    clipboard sebagai TSV. Return jumlah baris DATA yang tersalin (0 bila
    tidak ada seleksi / widget sudah mati — TclError ditelan)."""
    try:
        sel = tree.selection()
        if not sel:
            return 0
        text = tree_selection_tsv(tree)
        tree.clipboard_clear()
        tree.clipboard_append(text)
        return len(sel)
    except tk.TclError:
        return 0


# --- SELEKSI SEL ALA EXCEL (v3.9.35) -------------------------------------------
#
# User: "kenapa ya aku tidak bisa select di semua tabelnya? aku mau copy
# datanya seperti tabel di excel — di cell mana aja aku bebas buat select
# dan copy". Multi-select v3.9.32 = level BARIS penuh; kini tambah REGION
# SEL: klik sel → jangkar; drag / Shift+klik → persegi (baris terpilih ×
# rentang kolom jangkar→fokus); Ctrl+C → TSV per-sel TANPA header (persis
# semantik Excel: hanya sel yang di-highlight yang tersalin). Highlight
# memakai mekanisme tag per-cell yang SAMA dgn minus merah (overlay Label
# Tk 8.6 / tag native Tk 9) — teks sel + warna baris tetap terlihat,
# event klik/wheel diteruskan overlay, ikut re-posisi saat scroll.

_CELLSEL_TAG = "cellsel"
_CELLSEL_BG = "#99f6e4"      # teal-200 — lebih pekat drp seleksi baris (teal-100)
_CELLSEL_FG = "#134e4a"      # teal-900
# Batas aman: region > sel ini TIDAK digambar overlay (Ctrl+C tetap jalan)
# — mencegah UI beku saat Ctrl+A di tabel 100 ribu baris.
_CELLSEL_MAX_CELLS = 20000


def _cellsel_region_cols(tree: ttk.Treeview) -> list | None:
    """Rentang kolom region sel (urutan display, inklusif) — None bila
    tidak aktif / kolom jangkar atau fokus disembunyikan (ColumnManager)."""
    if not getattr(tree, "_cellsel_active", False):
        return None
    anchor = getattr(tree, "_cellsel_anchor", None)
    focus = getattr(tree, "_cellsel_focus", None)
    if not anchor or not focus:
        return None
    disp = _tree_display_columns(tree)
    if anchor not in disp or focus not in disp:
        return None
    i1, i2 = disp.index(anchor), disp.index(focus)
    lo, hi = (i1, i2) if i1 <= i2 else (i2, i1)
    return disp[lo:hi + 1]


def _cellsel_apply_cells(tree: ttk.Treeview, cells: list) -> None:
    """Pasang/bersihkan highlight region (semantik REPLACE).

    Tk 9 native: `tag cell add` bersifat TAMBAH — region yang menyusut
    akan meninggalkan sel basi jika hanya add → bersihkan dulu
    (`remove` tanpa cellList melepas SEMUA anggota tag) lalu pasang
    ulang (probe Tk 9.0: subcommand valid add/has/remove).
    Tk 8.6 overlay: set_cells([]) sudah semantik replace."""
    try:
        if CELL_TAGS_NATIVE:
            with contextlib.suppress(tk.TclError):
                tree.tk.call(str(tree), "tag", "cell", "remove",
                             _CELLSEL_TAG)
            if cells:
                apply_cell_tag(tree, _CELLSEL_TAG, cells)
            return
        apply_cell_tag(tree, _CELLSEL_TAG, cells)
    except tk.TclError:
        pass


def _cellsel_reapply(tree: ttk.Treeview) -> None:
    """Hitung ulang sel region = (baris terpilih) × (rentang kolom).

    Nonaktif bila seleksi baris kosong (re-render) atau kolom region
    disembunyikan. Region > _CELLSEL_MAX_CELLS → tanpa overlay (copy
    tetap berfungsi)."""
    if not getattr(tree, "_cellsel_active", False):
        return
    cols = _cellsel_region_cols(tree)
    try:
        sel = tree.selection()
    except tk.TclError:
        sel = ()
    if not cols or not sel:
        tree._cellsel_active = False
        tree._cellsel_anchor = None
        tree._cellsel_focus = None
        _cellsel_apply_cells(tree, [])
        return
    if len(sel) * len(cols) > _CELLSEL_MAX_CELLS:
        _cellsel_apply_cells(tree, [])
        return
    _cellsel_apply_cells(tree, [(str(iid), c) for iid in sel for c in cols])


def cell_region_tsv(tree: ttk.Treeview) -> str | None:
    """Susun REGION sel terpilih jadi teks TSV.

    v3.9.35 — TANPA baris header (semantik Excel: copy seleksi sel hanya
    memuat sel yang di-highlight; copy baris penuh — tree_selection_tsv —
    tetap memuat header). Baris mengikuti URUTAN TAMPILAN (walk hierarki);
    kolom = rentang display jangkar→fokus. None bila region tidak aktif /
    tidak ada baris."""
    cols = _cellsel_region_cols(tree)
    if not cols:
        return None
    try:
        sel_set = {str(i) for i in tree.selection()}
    except tk.TclError:
        return None
    if not sel_set:
        return None
    try:
        all_cols = [str(c) for c in (tree["columns"] or [])]
    except tk.TclError:
        all_cols = []
    col_idx = {c: i for i, c in enumerate(all_cols)}
    lines: list = []

    def _row_cells(iid) -> list:
        try:
            it = tree.item(iid)
        except tk.TclError:
            return []
        vals = it.get("values") or []
        out = []
        for c in cols:
            if c == "#0":
                out.append(_tsv_cell(it.get("text") or ""))
            else:
                i = col_idx.get(c, -1)
                out.append(_tsv_cell(vals[i]) if 0 <= i < len(vals) else "")
        return out

    def _walk(parent=""):
        try:
            kids = tree.get_children(parent)
        except tk.TclError:
            return
        for iid in kids:
            if str(iid) in sel_set:
                cells = _row_cells(iid)
                if cells:
                    lines.append("\t".join(cells))
            _walk(iid)

    _walk("")
    return "\n".join(lines) if lines else None


def copy_cell_region_tsv(tree: ttk.Treeview) -> int:
    """Salin region sel terpilih ke clipboard (TSV). Return jumlah baris
    data yang tersalin (0 bila tidak aktif / kosong / widget mati)."""
    try:
        text = cell_region_tsv(tree)
        if not text:
            return 0
        tree.clipboard_clear()
        tree.clipboard_append(text)
        return text.count("\n") + 1
    except tk.TclError:
        return 0


def enable_cell_select(tree: ttk.Treeview) -> ttk.Treeview:
    """v3.9.35 — aktifkan SELEKSI SEL ala Excel di sebuah tree.

    - Klik sel → jangkar region (baris ikut terpilih native — extended);
    - Drag / Shift+klik → perluas kolom fokus (baris diperluas native);
    - Ctrl+klik → toggle baris (region baris ikut — <<TreeviewSelect>>);
    - Ctrl+C → region TSV per-sel (tanpa header) via enable_multi_select;
      tanpa region → fallback copy baris penuh (v3.9.33);
    - Esc → bersihkan region ("break" saat aktif supaya window clone ⛶
      tidak ikut tertutup — Esc tanpa region tetap menutup clone);
    - klik heading/separator → region DIBIARKAN (drag resize kolom /
      popup filter ⧩ tidak menghilangkan seleksi); klik area kosong →
      region berakhir (perilaku Excel).

    Interaksi lama tidak berubah: double-click popup, klik ✓ follow-up,
    klik-kanan menu — binding additive tanpa "break" (resize kolom
    terpasang lebih dulu di sebagian view dan tetap memenangkan tepi).
    Idempoten (flag `_cellsel_bound`); dipasang otomatis ke SEMUA tree
    lewat enable_multi_select (make_tree + semua view + popup + clone ⛶).
    """
    if getattr(tree, "_cellsel_bound", False):
        return tree
    tree._cellsel_bound = True
    tree._cellsel_active = False
    tree._cellsel_anchor = None
    tree._cellsel_focus = None

    try:
        # tag per-cell (bukan tag baris — tak pernah dipasang ke item):
        # overlay membaca opsi ini utk warna highlight region.
        tree.tag_configure(_CELLSEL_TAG, background=_CELLSEL_BG,
                           foreground=_CELLSEL_FG)
    except tk.TclError:
        pass

    def _hit(event):
        """(valid, region, iid, kolom) dari koordinat event."""
        try:
            iid = tree.identify_row(event.y)
            reg = tree.identify_region(event.x, event.y)
            raw = tree.identify_column(event.x)
        except tk.TclError:
            return False, "", "", None
        if not iid or reg not in ("cell", "tree"):
            return False, reg, iid, None
        return True, reg, iid, identify_to_column(tree, raw)

    def _reapply_soon():
        # Binding WIDGET berjalan SEBELUM binding kelas ttk — saat press
        # handler ini dieksekusi, seleksi baris NATIVE belum terjadi
        # (selection() masih kosong) → reapply langsung akan melihat
        # seleksi kosong dan MENONAKTIFKAN region. after_idle menjalankan
        # reapply SETELAH seluruh rantai binding press (termasuk seleksi
        # native kelas) selesai.
        with contextlib.suppress(tk.TclError):
            tree.after_idle(lambda: _cellsel_reapply(tree))

    def _on_press(event):
        ok, reg, _iid, col = _hit(event)
        if ok and col:
            tree._cellsel_active = True
            tree._cellsel_anchor = col
            tree._cellsel_focus = col
            _reapply_soon()
            return
        # heading/separator (resize kolom / funnel ⧩) → region dibiarkan;
        # area kosong / sel tak valid → akhiri region (perilaku Excel).
        if reg not in ("heading", "separator"):
            tree._cellsel_active = False
            _cellsel_apply_cells(tree, [])

    def _on_shift(event):
        ok, _reg, _iid, col = _hit(event)
        if not ok or not col:
            return
        if not tree._cellsel_active or not tree._cellsel_anchor:
            tree._cellsel_active = True
            tree._cellsel_anchor = col
        tree._cellsel_focus = col
        _reapply_soon()

    def _on_motion(event):
        # drag memperluas KOLOM fokus (baris diperluas native extended);
        # motion di heading/separator diabaikan supaya resize tak ikut.
        if not tree._cellsel_active:
            return
        ok, _reg, _iid, col = _hit(event)
        if ok and col and col != tree._cellsel_focus:
            tree._cellsel_focus = col
            _reapply_soon()

    def _on_escape(_event=None):
        if tree._cellsel_active:
            tree._cellsel_active = False
            _cellsel_apply_cells(tree, [])
            return "break"    # clone ⛶ jangan tertutup oleh Esc
        return None

    def _on_select(_event=None):
        # seleksi baris berubah (drag/Ctrl+klik/Ctrl+A/re-render) →
        # sel region dihitung ulang; seleksi kosong → region berakhir.
        _cellsel_reapply(tree)

    tree.bind("<Button-1>", _on_press, add="+")
    tree.bind("<Shift-Button-1>", _on_shift, add="+")
    tree.bind("<B1-Motion>", _on_motion, add="+")
    tree.bind("<Escape>", _on_escape, add="+")
    tree.bind("<<TreeviewSelect>>", _on_select, add="+")
    return tree


def enable_multi_select(tree: ttk.Treeview) -> ttk.Treeview:
    """v3.9.32 — MULTI-SELECT + Ctrl+A semua tabel (user: "kenapa aku
    tidak bisa select ya untuk semua data?").

    Semua tree app sebelumnya selectmode="browse" (seleksi BARIS TUNGGAL
    — Ctrl+Klik / Shift+Klik / Ctrl+A tidak berfungsi). Kini:
    - selectmode "extended" → Ctrl+Klik (tambah/lepas), Shift+Klik
      (rentang), drag;
    - <Control-A> → pilih SEMUA baris (termasuk anak subtree utk tabel
      hierarki tab Pivot);
    - <Control-c>/<Control-C> → SALIN semua baris terpilih sebagai TSV
      ke clipboard (v3.9.33 — AUDIT FIX 48-f HIGH-#7: multi-select kini
      punya AKSI KONSUMSI di 9 tabel utama + popup + clone ⛶; sukses
      senyap — semantik clipboard standar; binding TREE-SCOPED, bukan
      bind_all — Entry/Combobox tidak terganggu).

    v3.9.33 — AUDIT FIX (48-c MEDIUM): IDEMPOTEN beneran (klaim lama
    salah) — bind add="+" MENUMPUK tiap panggilan ulang; kini flag
    `_multi_select_bound` (pola `_smooth_wheel_bound`). Dipasang juga ke
    clone Layar Penuh / popup (open_tree_maximized — tree BARU, jadi
    flag tidak terbawa → binding tetap terpasang di sana).

    v3.9.35 — SELEKSI SEL ALA EXCEL (user: "aku mau copy datanya seperti
    tabel di excel — di cell mana aja aku bebas buat select dan copy"):
    enable_cell_select dipanggil di sini → otomatis aktif di SEMUA tree
    (make_tree + semua view + popup + clone ⛶). Ctrl+C: region sel aktif
    → TSV per-sel tanpa header; tanpa region → baris penuh + header.

    Interaksi lama TIDAK berubah: double-click detail, klik ✓ follow-up,
    klik-kanan menu — semuanya memakai identify_row/event → tetap benar
    (popup yang mem-bind Ctrl+C sendiri MENGGANTI binding ini di
    tree-nya — details_popup: 1 baris = Nomor, >1 baris = TSV).
    """
    try:
        tree.configure(selectmode="extended")
    except tk.TclError:
        pass
    if getattr(tree, "_multi_select_bound", False):
        return tree
    tree._multi_select_bound = True

    def _select_all(_event=None):
        try:
            iids = []

            def _walk(iid):
                iids.append(iid)
                for ch in tree.get_children(iid):
                    _walk(ch)

            for top in tree.get_children(""):
                _walk(top)
            if iids:
                tree.selection_set(iids)
        except tk.TclError:
            pass

    def _copy_rows(_event=None):
        # v3.9.33 — Ctrl+C = aksi konsumsi multi-select (TSV ke clipboard)
        # v3.9.35 — REGION sel aktif (klik/drag sel ala Excel) MENANG:
        # copy rectangular per-sel TANPA header; tanpa region → baris
        # penuh dgn header (perilaku v3.9.33 dipertahankan).
        try:
            if (getattr(tree, "_cellsel_active", False)
                    and copy_cell_region_tsv(tree)):
                return
            copy_tree_selection_tsv(tree)
        except tk.TclError:
            pass

    tree.bind("<Control-a>", _select_all, add="+")
    tree.bind("<Control-A>", _select_all, add="+")
    tree.bind("<Control-c>", _copy_rows, add="+")
    tree.bind("<Control-C>", _copy_rows, add="+")
    enable_cell_select(tree)  # v3.9.35 — seleksi sel ala Excel
    return tree


def make_log_console(parent, **kw) -> tuple[tk.Text, tk.Frame]:
    """Konsol log gelap ala Waste (#0b1220 + Consolas). Return (text, frame).

    v3.9.33 — AUDIT FIX (48-f MEDIUM): state tetap "disabled" (isi tidak
    bisa diedit) TAPI seleksi kini bisa di-COPY — binding <Control-c>/
    <Control-C> di Text menyalin seleksi mouse aktif ke clipboard
    (traceback pipeline tidak lagi terjebak di konsol read-only; salin
    SELURUH log via tombol "📋 Salin Log" di tab Proses — app.py).
    """
    frame = tk.Frame(parent, bg=C_LOG_BG, highlightbackground=C_BORDER,
                     highlightthickness=1)
    frame.pack(fill="both", expand=True, **kw)

    text = tk.Text(frame, wrap="word", bg=C_LOG_BG, fg=C_LOG_FG,
                   insertbackground=C_LOG_FG, font=mono(10), relief="flat",
                   bd=0, padx=12, pady=10, state="disabled")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll.set)

    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    def _copy_selection(_event=None):
        # v3.9.33 — copy seleksi Text disabled (widget mati → senyap).
        try:
            content = text.get("sel.first", "sel.last")
            if content:
                text.clipboard_clear()
                text.clipboard_append(content)
        except tk.TclError:
            pass  # tidak ada seleksi aktif / widget sudah di-destroy
        return "break"

    text.bind("<Control-c>", _copy_selection)
    text.bind("<Control-C>", _copy_selection)
    # v3.9.48 — CTRL+Scroll di konsol log = ZOOM UI (bukan gulir teks;
    # pola Control lebih spesifik menang di bindtag widget — lihat
    # theme.bind_ctrl_zoom)
    bind_ctrl_zoom(text)
    return text, frame


# =============================================================================
# v3.1 — Komponen baru: loading spinner, overlay, segment, header-filter,
#         maximize table, async helper, insert batched
# =============================================================================

def _mix_hex(c1: str, c2: str, t: float) -> str:
    """Interpolasi dua warna hex (t=0 → c1, t=1 → c2)."""

    def parse(c: str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

    r1, g1, b1 = parse(c1)
    r2, g2, b2 = parse(c2)
    return f"#{round(r1 + (r2 - r1) * t):02x}{round(g1 + (g2 - g1) * t):02x}{round(b1 + (b2 - b1) * t):02x}"


class Spinner(tk.Canvas):
    """Spinner animasi (8 titik memudar) — indikasi loading proses."""

    def __init__(self, parent, size: int = 26, color: str = C_ACCENT,
                 bg: str = C_CARD, speed: int = 90, **kw):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, **kw)
        self._bg = bg
        self._speed = speed
        self._after_id = None
        self._phase = 0
        self._color = color
        cx = size / 2.0
        r = size / 2.0 - 3.0
        d = max(3.0, size * 0.17)
        self._dots = []
        for i in range(8):
            ang = i * (math.pi / 4)
            x = cx + r * math.cos(ang)
            y = cx + r * math.sin(ang)
            dot = self.create_oval(x - d / 2, y - d / 2, x + d / 2, y + d / 2,
                                   fill=color, outline=color)
            self._dots.append(dot)
        self._render()

    def _render(self):
        for i, dot in enumerate(self._dots):
            dist = (i - self._phase) % 8
            shade = _mix_hex(self._color, self._bg, (dist / 8.0) * 0.85)
            self.itemconfigure(dot, fill=shade, outline=shade)

    def start(self):
        self.stop()

        def tick():
            if not self.winfo_exists():
                self._after_id = None
                return
            self._phase = (self._phase + 1) % 8
            self._render()
            self._after_id = self.after(self._speed, tick)

        self._after_id = self.after(self._speed, tick)

    def stop(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None


class LoadingOverlay(tk.Frame):
    """Chip loading melayang di tengah parent: spinner + teks.

    show(text, delay_ms=180) — chip hanya benar-benar muncul bila proses
    berjalan lebih lama dari delay (anti-kedip untuk operasi cepat).
    """

    def __init__(self, parent, text: str = "Memuat…", **kw):
        super().__init__(parent, bg=C_CARD, highlightbackground=C_BORDER_DARK,
                         highlightthickness=1, **kw)
        inner = tk.Frame(self, bg=C_CARD)
        inner.pack(padx=24, pady=14)
        self.spinner = Spinner(inner, bg=C_CARD)
        self.spinner.pack(side="left", padx=(0, 12))
        self._var = tk.StringVar(value=text)
        tk.Label(inner, textvariable=self._var, bg=C_CARD, fg=C_HEADER,
                 font=font(11, "bold")).pack(side="left")
        self._show_after = None
        self._visible = False
        self._cursor_held = False   # FIX B-17: klaim cursor "watch" aktif?
        self.bind("<Destroy>", self._on_destroy, add="+")

    def show(self, text: str | None = None, delay_ms: int = 180):
        if text:
            self._var.set(text)
        if self._visible:
            return
        self._visible = True
        if delay_ms and delay_ms > 0:
            self._show_after = self.after(delay_ms, self._place)
        else:
            self._place()

    def _place(self):
        if not self._visible:
            return
        try:
            if not self.winfo_exists():
                return
            self.place(relx=0.5, rely=0.5, anchor="center")
            self.lift()
            self.spinner.start()
            self._acquire_watch_cursor()
        except tk.TclError:
            pass

    # FIX B-17 (audit 2-b): cursor "watch" kini BER-REFCOUNT per toplevel.
    # Dulu: overlay A & B sama-sama loading → A selesai duluan me-reset
    # cursor ke normal padahal B masih berjalan (dan sebaliknya kursor
    # watch tertinggal bila urutan hide tidak bersih). Tiap overlay yang
    # benar-benar mem-PLACEd memegang 1 klaim; reset hanya saat klaim
    # terakhir dilepas.
    def _acquire_watch_cursor(self):
        top = self.winfo_toplevel()
        n = int(getattr(top, "_watch_cursor_refs", 0)) + 1
        top._watch_cursor_refs = n
        if n == 1:
            top.configure(cursor="watch")
        self._cursor_held = True

    def _release_watch_cursor(self):
        top = self.winfo_toplevel()
        n = max(0, int(getattr(top, "_watch_cursor_refs", 1)) - 1)
        top._watch_cursor_refs = n
        if n == 0:
            top.configure(cursor="")

    def _on_destroy(self, _event=None):
        # widget overlay mati sebelum hide() → lepaskan klaim supaya
        # cursor tidak tertinggal "watch" seumur sesi.
        if self._cursor_held:
            self._cursor_held = False
            with contextlib.suppress(tk.TclError):
                self._release_watch_cursor()

    def hide(self):
        self._visible = False
        if self._show_after:
            try:
                self.after_cancel(self._show_after)
            except Exception:
                pass
            self._show_after = None
        try:
            self.place_forget()
            self.spinner.stop()
        except tk.TclError:
            pass
        if self._cursor_held:
            self._cursor_held = False
            with contextlib.suppress(tk.TclError):
                self._release_watch_cursor()


class SegmentBar(tk.Frame):
    """Segmented control kecil: beberapa opsi, satu aktif (teal)."""

    def __init__(self, parent, options: list[str], command=None,
                 bg: str = C_CARD, **kw):
        super().__init__(parent, bg=bg, **kw)
        self._command = command
        self._buttons: list[tk.Button] = []
        self._active = 0
        for i, opt in enumerate(options):
            b = tk.Button(self, text=opt, font=font(9, "bold"),
                          bd=0, relief="flat", highlightthickness=0,
                          cursor="hand2", padx=14, pady=5,
                          command=lambda idx=i: self._select(idx))
            b.pack(side="left", padx=(0 if i == 0 else 4, 0))
            self._buttons.append(b)
        self._render()

    def _select(self, idx: int):
        if idx == self._active:
            return
        self._active = idx
        self._render()
        if self._command:
            self._command(idx)

    @property
    def active(self) -> int:
        return self._active

    def set_active_silent(self, idx: int):
        """Set opsi aktif TANPA memicu command (dipakai saat inisialisasi
        / load_data supaya tidak refresh ganda)."""
        if idx != self._active:
            self._active = idx
            self._render()

    def _render(self):
        for i, b in enumerate(self._buttons):
            if i == self._active:
                b.configure(bg=C_ACCENT, fg="#ffffff",
                            activebackground=C_ACCENT_HOVER,
                            activeforeground="#ffffff")
            else:
                b.configure(bg="#f1f5f9", fg=C_TEXT_MUTED,
                            activebackground="#e2e8f0",
                            activeforeground=C_HEADER)


class TableExpander:
    """v3.9 — tombol ⤢ "Perbesar Tabel" ala aplikasi Waste.

    Permintaan user: "tiru style repo Waste mulai dari tombol filternya,
    perbesar tabelnya dan lain-lain". Di Waste, ⤢ menyembunyikan KPI +
    bar kontrol di sekitar tabel supaya TABEL memakai seluruh tinggi
    tampilan (tombol & toolbar tabel tetap terlihat supaya bisa
    dikembalikan); ⛶ Layar Penuh = window fullscreen terpisah.

    Pemakaian:
        exp = TableExpander(btn, [fcard, kpi_card, legend, title_label])
        btn.configure(command=exp.toggle)   # atau lewat constructor

    - Widget target pack: opsi pack dicatat + ANCHOR (widget non-target
      berikutnya) → restore mempertahankan urutan layout asli.
    - Widget target grid: grid_remove() mengingat opsi sendiri →
      restore cukup grid().
    """

    def __init__(self, button, targets, text_expand="⤢ Perbesar Tabel",
                 text_restore="⤡ Tampilkan Filter & KPI", on_toggle=None):
        self._button = button
        self._targets = list(targets)
        self._text_expand = text_expand
        self._text_restore = text_restore
        self._on_toggle = on_toggle
        self.expanded = False
        # (widget, manager, options, anchor, order_key) — order_key =
        # (id(parent), urutan pack ASLI) — FIX 6b-01.
        self._saved: list = []
        try:
            button.configure(command=self.toggle)
        except tk.TclError:
            pass
        # FIX 6b-05 (audit 6-b): pasang SEKALI — view boleh mem-pack ulang
        # target saat mode ⤢ aktif (mis. _render_kpi_chips setelah ganti
        # tanggal); <Map> men-trigger _on_target_map yang menyembunyikan
        # ulang widget selama self.expanded (lihat _on_target_map).
        for w in self._targets:
            try:
                w.bind("<Map>", self._on_target_map, add="+")
            except tk.TclError:
                pass
        self._update_text()

    def is_hidden(self, widget) -> bool:
        """FIX 6b-05 — helper publik: apakah widget target sedang
        disembunyikan expander (mode ⤢ aktif). View bisa memakainya utk
        guard pack() sendiri (pola _render_resto_scores in_selisih)."""
        return self.expanded and widget in self._targets

    # ---------------------------------------------------------------- state --
    def _update_text(self):
        try:
            self._button.configure(
                text=self._text_restore if self.expanded
                else self._text_expand)
        except tk.TclError:
            pass

    def toggle(self):
        if self.expanded:
            self.restore()
        else:
            self.collapse()
        if self._on_toggle:
            # callback view tidak boleh menjatuhkan toggle — telan error
            with contextlib.suppress(Exception):
                self._on_toggle(self.expanded)

    # ------------------------------------------------------------- collapse --
    def collapse(self):
        """Sembunyikan semua target → tabel memakai tinggi penuh."""
        if self.expanded:
            return
        target_set = {id(w) for w in self._targets}
        self._saved = []
        for w in self._targets:
            try:
                mgr = w.winfo_manager()
            except tk.TclError:
                continue
            if mgr == "pack":
                try:
                    info = w.pack_info()
                except tk.TclError:
                    continue
                # hitung anchor: sibling non-target BERIKUTNYA (jaga urutan
                # saat restore) — bila tak ada, sibling non-target sebelumnya
                anchor = None
                # FIX 6b-01 (audit 6-b): catat juga POSISI urutan pack ASLI
                # (id(parent), index) — restore memakainya utk memulihkan
                # grup target consecutive dgn urutan yang benar.
                order_key = (id(w.master), 0)
                try:
                    parent = w.master
                    order = list(parent.pack_slaves())
                    idx = order.index(w)
                    order_key = (id(parent), idx)
                    nxt = next((s for s in order[idx + 1:]
                                if id(s) not in target_set), None)
                    if nxt is not None:
                        anchor = ("before", nxt)
                    else:
                        prv = next((s for s in reversed(order[:idx])
                                    if id(s) not in target_set), None)
                        if prv is not None:
                            anchor = ("after", prv)
                except (tk.TclError, ValueError):
                    anchor = None
                info = dict(info)
                info.pop("before", None)
                info.pop("after", None)
                self._saved.append((w, "pack", info, anchor, order_key))
                w.pack_forget()
            elif mgr == "grid":
                # grid_remove mengingat semua opsi grid — restore = grid()
                self._saved.append((w, "grid", None, None,
                                    (id(w.master), 0)))
                w.grid_remove()
        self.expanded = True
        self._update_text()

    # -------------------------------------------------------------- restore --
    def restore(self):
        """Kembalikan semua target ke posisi semula (urutan asli).

        FIX B-16 (audit 2-b): grup target di AKHIR urutan (semua anchor
        'after' widget non-target sama) harus dipasang mundur — iterasi
        maju memasang mereka TERBALIK ([A, T1, T2] → [A, T2, T1]).

        FIX 6b-01 (audit 6-b): B-16 mundur SEMUA entri — grup anchor
        'before' yang SAMA (≥2 target pack berturut-turut diikuti tabel
        yang sama, mis. in_selisih [Filter, KPI, SKOR, tabel]) justru
        TERBALIK oleh iterasi mundur. Kini entri DIPARTISI:
        - anchor 'before' / tanpa anchor → dipasang URUT MAJU sesuai
          posisi pack ASLI (order_key) — tiap pack(before=X) menyisipkan
          tepat sebelum X;
        - anchor 'after' (grup ekor) → tetap URUT MUNDUR (kebalikan B-16).
        Kedua jenis tidak tumpang tindih dalam satu parent: target
        'after' selalu berada SETELAH non-target terakhir, target
        'before' selalu SEBELUM suatu non-target."""
        # FIX 6b-05: expanded dimatikan DULU — re-pack milik restore ini
        # sendiri tidak boleh ditelan lagi oleh _on_target_map.
        self.expanded = False
        fwd = []
        bwd = []
        for entry in self._saved:
            anchor = entry[3]
            if anchor is not None and anchor[0] == "after":
                bwd.append(entry)
            else:
                fwd.append(entry)
        fwd.sort(key=lambda e: e[4])   # urutan pack ASLI per parent
        bwd.sort(key=lambda e: e[4])
        for w, mgr, info, anchor, _key in fwd:
            self._repack(w, mgr, info, anchor)
        for w, mgr, info, anchor, _key in reversed(bwd):
            self._repack(w, mgr, info, anchor)
        self._saved = []
        self._update_text()

    @staticmethod
    def _repack(w, mgr, info, anchor):
        """Pasang ulang SATU target (options + anchor tersimpan)."""
        try:
            if mgr == "pack":
                kw = dict(info)
                if anchor is not None:
                    kw[anchor[0]] = anchor[1]
                w.pack(**kw)
            elif mgr == "grid":
                w.grid()
        except tk.TclError:
            pass

    def _on_target_map(self, event):
        """FIX 6b-05 (audit 6-b): target di-pack ulang view (render ulang
        KPI/SKOR pasca ganti tanggal / reset filter) saat mode ⤢ aktif →
        sembunyikan LAGI tanpa mengubah anchor tersimpan, supaya kartu
        tidak muncul sendiri & tombol tidak berbohong ('⤡ Tampilkan …')."""
        if not self.expanded:
            return
        w = event.widget
        try:
            mgr = w.winfo_manager()
        except tk.TclError:
            return
        try:
            if mgr == "pack":
                w.pack_forget()
            elif mgr == "grid":
                w.grid_remove()
        except tk.TclError:
            pass

    def reset(self):
        """Pulihkan bila sedang collapse (dipanggil load_data supaya layout
        view baru tidak terjebak setengah-collapse)."""
        if self.expanded:
            self.restore()


# --- Ikon corong utk header filter (digambar via PhotoImage, tanpa PIL) -----
# funnel ala Waste — TERISI MERAH saat kolom terfilter, versi idle = isi
# terang #cbd5e1 + outline gelap #64748b (terbaca jelas tanpa menutupi
# judul). Ikon diperbesar 11x8 → 13x11 supaya terlihat seperti funnel
# header Waste (_HF_ACTIVE "#dc2626" / _HF_IDLE "#94a3b8" + fill #cbd5e1).
_FUNNEL_CACHE: dict = {}

# Bentuk corong (mask per baris: x0..x1 inklusif) — 13 lebar x 11 tinggi:
# cone melebar di atas mengecil ke stem 3px di bawah.
_FUNNEL_SHAPE = [
    (0, 12),   # rim atas
    (1, 11),
    (2, 10),
    (3, 9),
    (4, 8),
    (4, 8),
    (5, 7),   # stem
    (5, 7),
    (5, 7),
    (5, 7),
    (5, 7),
]


def _funnel_mask() -> set:
    """Set piksel (x, y) milik bentuk corong."""
    mask = set()
    for y, (x0, x1) in enumerate(_FUNNEL_SHAPE):
        for x in range(x0, x1 + 1):
            mask.add((x, y))
    return mask


def funnel_image(active: bool = False) -> tk.PhotoImage:
    """Ikon corong 13x11 px dua-warna (ala Waste — v3.9).

    active=True  → terisi MERAH #dc2626 (kolom sedang terfilter).
    active=False → isi terang #cbd5e1 + outline #64748b (idle).

    Alpha via PhotoImage Tk 8.6 (transparency_set)."""
    key = "on" if active else "off"
    if key in _FUNNEL_CACHE:
        return _FUNNEL_CACHE[key]
    w = max(x1 for _, x1 in _FUNNEL_SHAPE) + 1
    h = len(_FUNNEL_SHAPE)
    img = tk.PhotoImage(width=w, height=h)
    mask = _funnel_mask()
    fill = "#dc2626" if active else "#cbd5e1"
    outline = "#b91c1c" if active else "#64748b"
    for y in range(h):
        for x in range(w):
            if (x, y) in mask:
                # piksel tepi (ada tetangga di luar bentuk) → outline gelap,
                # interior → warna isi — funnel terlihat "digambar", bukan
                # blok solid tipis yang nyaris tak terbaca di bg header.
                edge = any((x + dx, y + dy) not in mask
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                img.put(outline if edge else fill, (x, y))
            else:
                try:
                    img.transparency_set(x, y, True)
                except Exception:
                    pass
    _FUNNEL_CACHE[key] = img
    return img


# v3.9.59 — fix 2b-01 (audit 2-b): cap lebar popup daftar nilai +
# tunjangan ruang non-teks per baris (indikator checkbox ±18px + padx
# 8×2 + tepi canvas) — teks nilai diukur font(10) (style TCheckbutton).
_HF_POPUP_CAP = 460
_HF_CHK_ALLOW = 64


class HeaderFilter:
    """Filter kolom yang MENEMPEL DI HEADER Treeview (ala Excel AutoFilter).

    - Ikon corong dipasang di heading kolom; klik heading → popup filter.
    - Popup: pencarian nilai + operator teks (Mengandung / Diawali /
      Diakhiri / Tidak mengandung) + daftar checkbox nilai unik +
      pilih-semua + sort A→Z / Z→A (opsional) + reset + ↔ Balik (invert).
    - v3.9.13 (permintaan user: "habis search, hasil search-ku itulah
      yang jadi pilihan-nya"): tekan **Enter** di kolom pencarian →
      hasil pencarian MENJADI seleksi. Query kosong + Enter = reset.
      0 hasil = 0 baris (semantik Excel AutoFilter).
    - Setiap toggle checkbox / Enter / Balik memanggil on_apply(sel):
        None      → semua nilai tampil (tanpa filter)
        set(...)  → hanya nilai terpilih yang tampil
        set()     → 0 baris — seleksi kosong = TIDAK ada baris (v3.9.13;
                    dulu dipetakan None = tampil semua)
    - ``selected`` = state EKSAK otoritatif: nilai di luar cap
      MAX_CHECKS mengikuti state ini (bukan lagi heuristik "dianggap
      tercentang" — v3.9.10 B-05 kini exact).
    - get_values() dipanggil saat popup dibuka (nilai unik terbaru).
    """

    MAX_CHECKS = 3000  # FIX B-03: 600→3000 — gunakan 🔍 untuk list sangat besar

    # v3.9.13: operator pencocokan teks (dropdown readonly di samping 🔍).
    SEARCH_OPS = ("Mengandung", "Diawali", "Diakhiri", "Tidak mengandung")

    # FIX B-05 (audit 2-b): nilai di luar MAX_CHECKS kini tetap bisa
    # ditemukan & dicentang via pencarian (checkbox LAZY) — dan nilai
    # belum dimaterialisasi tidak lagi hilang diam-diam dari hasil filter.

    def __init__(self, tree: ttk.Treeview, col_id: str, *, get_values,
                 on_apply, label: str = "Nama Barang", on_sort=None,
                 popup_width: int = 330):
        self.tree = tree
        self.col_id = col_id
        self.get_values = get_values
        self.on_apply = on_apply
        self.on_sort = on_sort
        self.label = label
        self.popup_width = popup_width
        self.selected: set | None = None
        self._popup: tk.Toplevel | None = None
        self._closed_at = 0.0
        self._checks: dict[str, ttk.Checkbutton] = {}
        self._vars: dict[str, tk.BooleanVar] = {}
        self._search_var = tk.StringVar()
        # v3.9.13: operator pencocokan teks utk search-to-select (Enter).
        self._op_var = tk.StringVar(value="Mengandung")
        self._all_var = tk.BooleanVar(value=True)
        self._count_var = tk.StringVar(value="")
        self._values_list: list[str] | None = None   # FIX B-05
        self._all_values: set | None = None          # FIX B-05
        self._list_inner = None                      # FIX B-05
        self._more_label = None                      # FIX B-05
        # v3.9.59 — fix 2b-01: ruang teks popup (utk '…') + pengukur font;
        # fix 2b-04: state navigasi keyboard daftar nilai (Up/Down/Space).
        self._pop_text_px = 0
        self._pop_meas = None
        self._nav_cb = None
        self._nav_entry = None
        self._nav_box = None
        self._nav_canvas = None
        self.refresh_icon()
        self._bind_id = tree.bind("<Button-1>", self._on_tree_press, add="+")

    def detach(self):
        """Lepas binding klik-heading dari tree (dipakai saat kolom
        dikonfigurasi ulang — mencegah binding ganda/orsos)."""
        if getattr(self, "_bind_id", None):
            try:
                self.tree.unbind("<Button-1>", self._bind_id)
            except Exception:
                pass
            self._bind_id = None

    def set_selected(self, values):
        """v3.9.22 — set state seleksi SECARA PROGRAMATIK (default filter,
        mis. KATEGORI=DEVIASI di Rekap Selisih IN) + refresh ikon corong.
        v3.9.68 — TRI-STATE (audit eksternal T1): None = tanpa filter;
        koleksi KOSONG (set()/[]) = filter AKTIF yang menyaring 0 baris
        — ikon corong TETAP MENYALA. Dulu ``list(values) if values else
        None`` menelan koleksi kosong sebagai None → corong mati padahal
        filter aktif 0 baris (restore tri-state membuat kondisi ini
        kini bisa terjadi lintas sesi)."""
        if values is None:
            self.selected = None
        else:
            try:
                self.selected = set(values)
            except TypeError:
                self.selected = None
        self.refresh_icon()

    # -- ikon corong ---------------------------------------------------------
    def refresh_icon(self):
        active = self.selected is not None
        try:
            self.tree.heading(
                self.col_id,
                image=funnel_image(active=active))
        except tk.TclError:
            pass

    # -- klik heading --------------------------------------------------------
    def _on_tree_press(self, event):
        try:
            if self.tree.identify_region(event.x, event.y) != "heading":
                return
            # v3.6 BUG FIX: resolve '#N' posisi-display → nama kolom aktual
            # (klik mouse sungguhan sebelumnya tidak pernah match nama
            # simbolik; juga benar saat ada kolom tersembunyi)
            actual = identify_to_column(
                self.tree, self.tree.identify_column(event.x))
        except Exception:
            return
        if actual != self.col_id:
            return
        # hindari langsung terbuka lagi setelah ditutup (toggle natural)
        if _time.time() - self._closed_at < 0.35:
            return
        self.open_popup()

    # -- popup ----------------------------------------------------------------
    def open_popup(self):
        if self._popup is not None and self._popup.winfo_exists():
            self._close()
            return
        values = []
        try:
            # FIX B-19 (audit 2-b): urutkan numerik-aware — "1.000" harus
            # muncul SETELAH "999" (dulu leksikografis).
            values = sorted({str(v) for v in self.get_values()
                             if str(v) and str(v) != "nan"},
                            key=_filter_value_sort_key)
        except Exception:
            values = []
        if not values:
            _mb.showinfo("Filter", "Tidak ada nilai yang bisa difilter.",
                         parent=self.tree)
            return
        # FIX B-13 (audit 2-b): teks pencarian popup SEBELUMNYA menempel —
        # popup terbuka ulang dgn daftar sudah terfilter (tampak nilai
        # "hilang"). Reset tiap kali popup dibuka.
        self._search_var.set("")
        # FIX B-05: simpan daftar lengkap — nilai di luar cap tetap bisa
        # ditemukan via pencarian & dihitung benar saat filter diterapkan.
        self._values_list = values
        self._all_values = set(values)
        # v3.9.59 — fix 2b-01 (audit 2-b): lebar popup mengikuti nilai
        # TERPANJANG (clamp _HF_POPUP_CAP 460px) — dulu ruang teks tetap
        # ``popup_width-30`` (±284px) → nilai >±40 char terpotong TANPA
        # '…' dan dua nilai yang sama awalan tak bisa dibedakan (probe
        # ub_hf: 73-char → 577px vs 284px). Di atas cap teks dipotong
        # '…'; checkbox/variable tetap mewakili nilai PENUH.
        try:
            _cf = font(10)
            _cf.measure("")            # pastikan objek Font hidup
            self._pop_meas = _cf.measure
        except (tk.TclError, AttributeError):
            self._pop_meas = None
        _need = 0
        if self._pop_meas is not None:
            _meas = self._pop_meas
            _need = max((_meas(v) for v in values), default=0)
        pop_w = max(self.popup_width,
                    min(_need + _HF_CHK_ALLOW, _HF_POPUP_CAP))
        self._pop_text_px = max(40, pop_w - _HF_CHK_ALLOW)

        root = self.tree.winfo_toplevel()
        win = tk.Toplevel(root)
        self._popup = win
        win.title(f"Filter — {self.label}")
        win.configure(bg=C_CARD)
        win.transient(root)
        win.resizable(False, False)
        _take_grab(win)  # FIX 6e-03 — pulihkan grab modal induk saat ditutup

        body = tk.Frame(win, bg=C_CARD)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # pencarian nilai (menyaring daftar; Enter = jadikan seleksi)
        srow = tk.Frame(body, bg=C_CARD)
        srow.pack(fill="x")
        tk.Label(srow, text="🔍", bg=C_CARD, fg=C_TEXT_MUTED).pack(side="left")
        entry = ttk.Entry(srow, textvariable=self._search_var)
        entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        entry.bind("<KeyRelease>", lambda e: self._filter_list())
        # v3.9.13 (permintaan user: "habis search, hasil search-ku itulah
        # yang jadi pilihan-nya") — Enter menjadikan hasil pencarian
        # SELEKSI; operator teks ala Excel AutoFilter di sampingnya.
        entry.bind("<Return>", self._on_search_enter)
        op_box = ttk.Combobox(srow, width=11, state="readonly",
                              textvariable=self._op_var,
                              values=list(self.SEARCH_OPS))
        op_box.pack(side="left", padx=(6, 0))
        # v3.9.59 — fix 2b-03 (audit 2-b): hint semantik tombol — fitur
        # search-to-select (Enter = hasil pencarian jadi seleksi, §94)
        # tidak terdiscover: semantiknya hanya hidup di docstring.
        tk.Label(body, text="Enter = pilih nilai terfilter · Esc = tutup",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=font(9)).pack(
            fill="x", padx=(22, 0), pady=(2, 0))

        # pilih semua + counter
        arow = tk.Frame(body, bg=C_CARD)
        arow.pack(fill="x", pady=(10, 2))
        ttk.Checkbutton(arow, text=f"Pilih semua ({len(values)} nilai)",
                        variable=self._all_var,
                        command=self._toggle_all).pack(side="left")
        tk.Label(arow, textvariable=self._count_var, bg=C_CARD,
                 fg=C_TEXT_MUTED, font=font(9)).pack(side="right")  # FIX A-08

        # daftar nilai (scrollable checkbox)
        wrap = tk.Frame(body, bg=C_CARD, highlightbackground=C_BORDER,
                        highlightthickness=1)
        wrap.pack(fill="both", expand=True, pady=(6, 10))
        cv = tk.Canvas(wrap, bg=C_CARD, highlightthickness=0, bd=0,
                       width=pop_w - 30, height=300)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=C_CARD)
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw",
                         width=pop_w - 30)
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # scroll wheel — v3.9.57: roda HALUS ber-AKUMULATOR (audit: delta
        # < 120 dibulatkan-0 oleh kode lama = daftar macet di trackpad/
        # roda resolusi tinggi) + binding TINGKAT POPUP (wheel di anak apa
        # pun — entry pencarian fokus (Windows Tk 8.6 kirim wheel ke widget
        # FOKUS)/checkbox/scrollbar — tetap menggulir daftar) + X11
        # <Button-4/5>; CTRL+Scroll tetap ZOOM UI (v3.9.48).
        enable_smooth_wheel_list(cv, container=win)
        # FIX B-05: simpan container daftar — checkbox LAZY untuk nilai di
        # luar cap dibuat di sini saat pencarian menemukannya.
        self._list_inner = inner
        # v3.9.59 — fix 2b-04 (audit 2-b): navigasi KEYBOARD daftar nilai
        # (Up/Down gerakkan fokus baris + auto-scroll, Space toggle).
        # Binding TINGKAT POPUP (bindtag Toplevel ada di rantai SEMUA anak
        # — pola enable_smooth_wheel_list): kunci ditekan di entry/label
        # mana pun tetap menggerakkan fokus. Focus ring = style turunan
        # "HFFoc.TCheckbutton" (focuscolor TCheckbutton default putih di
        # kartu putih = tak terlihat — audit 2b-04).
        self._nav_entry = entry
        self._nav_box = op_box
        self._nav_canvas = cv
        self._nav_cb = None
        with contextlib.suppress(tk.TclError):
            _st = ttk.Style(win)
            _st.configure("HFFoc.TCheckbutton", background=C_ACCENT_SOFT,
                          focuscolor=C_ACCENT_DARK)
            _st.map("HFFoc.TCheckbutton",
                    background=[("active", _CELLSEL_BG)])
        for _seq in ("<Up>", "<Down>", "<space>"):
            win.bind(_seq, self._on_nav_key, add="+")

        self._vars.clear()
        self._checks.clear()
        for v in values[: self.MAX_CHECKS]:
            var = tk.BooleanVar(
                value=self.selected is None or v in self.selected)
            self._vars[v] = var
            cb = ttk.Checkbutton(inner, text=self._disp_text(v),
                                 variable=var, command=self._on_toggle)
            cb.pack(fill="x", padx=8, pady=1)
            self._checks[v] = cb
        self._more_label = None
        if len(values) > self.MAX_CHECKS:
            # FIX B-03: label jujur — tampilkan total nilai sebenarnya,
            # bukan hanya jumlah yang tersembunyi.
            self._more_label = tk.Label(
                inner, text=f"… menampilkan {self.MAX_CHECKS} dari "
                            f"{len(values)} nilai — gunakan 🔍 di atas "
                            "untuk mencari & mencentang nilai lain",
                bg=C_CARD, fg=C_TEXT_MUTED, font=font(9))
            self._more_label.pack(fill="x", padx=8, pady=4)

        # tombol aksi
        brow = tk.Frame(body, bg=C_CARD)
        brow.pack(fill="x")
        GhostButton(brow, text="↺ Reset", command=self._reset).pack(side="left")
        # v3.9.13: kebalikan seleksi (invert — filter advanced)
        GhostButton(brow, text="↔ Balik",
                    command=self._invert_selection).pack(side="left",
                                                         padx=(6, 0))
        if self.on_sort is not None:
            GhostButton(brow, text="↕ Sort A→Z",
                        command=lambda: self._do_sort(False)).pack(
                side="left", padx=(6, 0))
            GhostButton(brow, text="↕ Sort Z→A",
                        command=lambda: self._do_sort(True)).pack(
                side="left", padx=(6, 0))
        GhostButton(brow, text="✕ Tutup (Esc)", command=self._close).pack(
            side="right")

        self._update_count()
        self._filter_list()

        # posisikan tepat di bawah heading kolom
        win.update_idletasks()
        px, py = self._popup_position()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        px = min(max(px, 8), max(8, sw - win.winfo_reqwidth() - 8))
        py = min(max(py, 8), max(8, sh - win.winfo_reqheight() - 8))
        win.geometry(f"+{px}+{py}")
        entry.focus_set()
        win.bind("<Escape>", lambda e: self._close())

    def _popup_position(self):
        tree = self.tree
        try:
            # v3.7 FIX: posisi x dihitung dari kolom yang TAMPIL saja
            # (displaycolumns-aware; #0 hanya dihitung bila tree column
            # memang tampil) — dulu menjumlahkan lebar SEMUA kolom termasuk
            # yang tersembunyi + phantom #0 → popup melenceng setelah
            # kolom disembunyikan.
            cols = _tree_display_columns(tree)
            x = 0
            if self.col_id in cols:
                x = sum(tree.column(c, "width")
                        for c in cols[:cols.index(self.col_id)])
                first = tree.xview()[0]
                if first > 0:
                    content_w = sum(tree.column(c, "width") for c in cols)
                    visible_w = tree.winfo_width()
                    if content_w > visible_w:
                        x -= first * (content_w - visible_w)
            px = int(tree.winfo_rootx() + max(0, x))
            hy = 30
            for iid in tree.get_children(""):
                bbox = tree.bbox(iid)
                if bbox:
                    hy = bbox[1] + 4
                    break
            py = int(tree.winfo_rooty() + hy)
        except Exception:
            px, py = tree.winfo_rootx(), tree.winfo_rooty() + 40
        return px, py

    # -- aksi popup ------------------------------------------------------------
    def _on_toggle(self):
        # v3.9.13: _emit DULU — counter kini membaca state EKSAK hasil
        # emit (bukan hanya checkbox yang termaterialisasi).
        self._emit()
        self._update_count()

    def _toggle_all(self):
        to = self._all_var.get()
        for var in self._vars.values():
            var.set(to)
        # v3.9.13: "Pilih semua" EKSAK di semua kasus — termasuk nilai
        # di luar cap MAX_CHECKS yang belum termaterialisasi: nyala =
        # SEMUA nilai (None), mati = TIDAK ADA nilai (0 baris, Excel).
        if self._values_list is not None:
            self._apply_selection(set(self._values_list) if to else set())
            return
        self._emit()
        self._update_count()

    def _emit(self):
        # v3.9.13: state seleksi EKSAK (selected = set|None) — dasar utk
        # search-to-select & invert. Checkbox materialized hanya OVERRIDE;
        # nilai di luar cap MAX_CHECKS mengikuti state (v3.9.10 B-05 kini
        # exact, bukan heuristik "dianggap tercentang").
        total = (len(self._all_values)
                 if self._all_values is not None else len(self._vars))
        if self._all_values is not None:
            base = (set(self._all_values) if self.selected is None
                    else set(self.selected))
        else:
            base = (set(self._vars) if self.selected is None
                    else set(self.selected))
        for v, var in self._vars.items():
            if var.get():
                base.add(v)
            else:
                base.discard(v)
        if not total or len(base) == total:
            self.selected = None
        else:
            # v3.9.13 (permintaan user): seleksi KOSONG = 0 baris (perilaku
            # Excel) — dulu seleksi kosong dipetakan None (tampil semua).
            self.selected = base
        self.refresh_icon()
        if self.on_apply:
            self.on_apply(self.selected)

    def _update_count(self):
        # v3.9.13: counter EKSAK — nilai di luar cap MAX_CHECKS ikut
        # dihitung lewat state otoritatif `selected`.
        if self._values_list is not None:
            total = len(self._values_list)
            checked = total if self.selected is None else len(self.selected)
        else:
            total = len(self._vars)
            checked = sum(1 for var in self._vars.values() if var.get())
        self._all_var.set(total > 0 and checked == total)
        self._count_var.set(f"{checked}/{total} dipilih")

    # -- search-to-select (v3.9.13) --------------------------------------------
    def _search_pred(self, q: str):
        """v3.9.59 — fix 2b-02 (audit 2-b): predikat operator teks SATU
        sumber kebenaran untuk Enter-search DAN preview live-search.

        Dulu preview (``_filter_list``) memakai contains polos
        ``q in v.lower()`` sementara Enter memakai operator pilihan —
        op 'Diawali' + '100' → daftar masih menampilkan nilai yang TIDAK
        akan dipilih (mis. 'uang 100') → tekan Enter → tabel KOSONG
        mendadak (feedback menyesatkan). Kontrak Enter (§94: 0 hasil =
        0 baris) TIDAK berubah — hanya preview yang disinkronkan."""
        op = str(self._op_var.get() or "Mengandung")

        def _contains(v: str) -> bool:
            return q in v.lower()

        def _starts(v: str) -> bool:
            return v.lower().startswith(q)

        def _ends(v: str) -> bool:
            return v.lower().endswith(q)

        def _excludes(v: str) -> bool:
            return q not in v.lower()

        return {"Diawali": _starts, "Diakhiri": _ends,
                "Tidak mengandung": _excludes}.get(op, _contains)

    def _on_search_enter(self, _event=None):
        """v3.9.13: Enter → hasil pencarian menjadi SELEKSI (permintaan
        user: "habis search, hasil search-ku itulah yang jadi
        pilihan-nya"). Query kosong + Enter = reset; 0 hasil = 0 baris."""
        q = (self._search_var.get() or "").strip().lower()
        if self._values_list is None:
            return
        if not q:
            self._reset()
            return
        pred = self._search_pred(q)
        matches = {v for v in self._values_list if pred(v)}
        self._apply_selection(matches)

    def _apply_selection(self, matches: set):
        """v3.9.13: terapkan seleksi EKSAK (dipakai Enter-search, Balik,
        Pilih-semua) — seluruh hasil = satu-satunya nilai terpilih;
        checkbox + counter di-sync; on_apply dipanggil (0 hasil = 0
        baris; semua nilai = None/tampil semua)."""
        total = len(self._values_list) if self._values_list else 0
        self.selected = (None if (not total or len(matches) == total)
                         else set(matches))
        for v, var in self._vars.items():
            var.set(self.selected is None or v in self.selected)
        self._filter_list()   # daftar tetap menampilkan hasil pencarian
        self._update_count()
        self.refresh_icon()
        if self.on_apply:
            self.on_apply(self.selected)

    def _invert_selection(self):
        """v3.9.13: kebalikan seleksi (invert — filter advanced): nilai
        terpilih ↔ tidak terpilih; None (semua) → kosong (0 baris)."""
        if not self._values_list:
            return
        allv = set(self._values_list)
        cur = allv if self.selected is None else set(self.selected)
        self._apply_selection(allv - cur)

    def _disp_text(self, v: str) -> str:
        """v3.9.59 — fix 2b-01: teks TAMPILAN checkbox (terpotong '…' bila
        nilai melebihi ruang popup yang sudah di-cap); variable/state
        filter tetap memakai nilai PENUH (key ``self._checks``)."""
        px = self._pop_text_px
        meas = self._pop_meas
        if not px or meas is None:
            return v
        return _ellipsize(v, meas, px)

    def _filter_list(self):
        q = (self._search_var.get() or "").strip().lower()
        # v3.9.59 — fix 2b-02: preview memakai PREDIKAT OPERATOR yang sama
        # dengan Enter (self._search_pred) — apa yang terlihat = apa yang
        # akan terpilih (dulu contains polos → mismatch di op Diawali/
        # Diakhiri/Tidak mengandung).
        pred = self._search_pred(q) if q else None
        # FIX B-05: pencarian yang menemukan nilai DI LUAR cap → buat
        # checkbox-nya sekarang (lazy) supaya bisa dilihat & dicentang.
        if (q and pred is not None
                and self._values_list is not None
                and len(self._values_list) > self.MAX_CHECKS
                and self._list_inner is not None
                and self._list_inner.winfo_exists()):
            created = False
            for v in self._values_list[self.MAX_CHECKS:]:
                if v in self._checks or not pred(v):
                    continue
                var = tk.BooleanVar(
                    value=self.selected is None or v in self.selected)
                self._vars[v] = var
                cb = ttk.Checkbutton(self._list_inner,
                                     text=self._disp_text(v), variable=var,
                                     command=self._on_toggle)
                if self._more_label is not None \
                        and self._more_label.winfo_exists():
                    cb.pack(fill="x", padx=8, pady=1,
                            before=self._more_label)
                else:
                    cb.pack(fill="x", padx=8, pady=1)
                self._checks[v] = cb
                created = True
            if created:
                self._update_count()
        for v, cb in self._checks.items():
            # v3.9.13: _apply_selection (Enter/Balik/Pilih-semua) kini juga
            # bisa dipanggil programatik SETELAH popup ditutup — lewati
            # checkbox milik popup yang sudah mati (state tetap otoritatif).
            if not cb.winfo_exists():
                continue
            if not q or pred(v):
                cb.pack(fill="x", padx=8, pady=1)
            else:
                cb.pack_forget()
        # 2b-04: baris fokus keyboard yang tersembunyi oleh filter →
        # lepaskan ring fokusnya (jangan toggle baris tak terlihat).
        nav = self._nav_cb
        if (nav is not None and nav.winfo_exists()
                and nav.winfo_manager() != "pack"):
            self._nav_clear()

    # -- navigasi keyboard daftar nilai (v3.9.59 — fix 2b-04) ------------------
    def _nav_rows(self) -> list:
        """Checkbox yang TAMPIL saat ini (urutan pack = urutan visual).
        Nilai 'Pilih semua' tidak termasuk (ada di luar canvas)."""
        inner = self._list_inner
        if inner is None or not inner.winfo_exists():
            return []
        return [w for w in inner.pack_slaves()
                if isinstance(w, ttk.Checkbutton)]

    def _on_nav_key(self, event):
        """Up/Down: pindah fokus baris (+auto-scroll); Space: toggle.

        Bindtag Toplevel (rantai semua anak popup). Interaksi asli tidak
        diganggu: fokus di combobox operator → biarkan default (Up/Down
        = buka daftar operator); spasi di entry = karakter; fokus di
        checkbox/tombol → class binding ttk sudah menangani Space
        SEBELUM bindtag ini (jangan invoke ulang = toggle ganda).
        RESUME round: Down DI DALAM entry pencarian kini masuk ke baris
        pertama daftar (pola combobox) — dulu entry = dead-zone: satu-
        satunya jalan keyboard ke daftar adalah Tab (melewati combobox
        operator + 'Pilih semua' dulu), padahal alur utama user keyboard
        adalah ketik filter → turun ke hasil → Space mencentang."""
        if self._popup is None or not self._popup.winfo_exists():
            return None
        seq = str(getattr(event, "keysym", "") or "")
        if seq not in ("Up", "Down", "space"):
            return None
        try:
            focus = self._popup.focus_get()
        except tk.TclError:
            focus = None
        if focus is self._nav_box:
            return None
        rows = self._nav_rows()
        if not rows:
            return None
        if focus is self._nav_entry:
            if seq == "Down":
                self._nav_focus(rows[0])
                return "break"
            return None        # Up/space di entry = perilaku teks normal
        if seq in ("Up", "Down"):
            cur = rows.index(self._nav_cb) if self._nav_cb in rows else -1
            if seq == "Down":
                nxt = rows[min(cur + 1, len(rows) - 1)]
            else:
                nxt = rows[max(cur - 1, 0)]
            self._nav_focus(nxt)
            return "break"
        # seq == "space": class binding sudah toggle bila fokus di
        # checkbox/tombol — hanya jalur TANPA fokus (mis. Xvfb) yang perlu
        # di-invoke manual.
        if focus is None and self._nav_cb in rows:
            self._nav_cb.invoke()
            return "break"
        return None

    def _nav_focus(self, cb):
        """Pasang ring fokus (style HFFoc + focus_set) + auto-scroll."""
        prev = self._nav_cb
        self._nav_cb = cb
        with contextlib.suppress(tk.TclError):
            if prev is not None and prev is not cb and prev.winfo_exists():
                prev.configure(style="TCheckbutton")
            if cb is not None and cb.winfo_exists():
                cb.configure(style="HFFoc.TCheckbutton")
                cb.focus_force()
                self._nav_see(cb)

    def _nav_see(self, cb):
        """Gulir canvas supaya baris fokus tetap terlihat (mata-fokus
        pengguna keyboard di bawah lipatan)."""
        cv = self._nav_canvas
        inner = self._list_inner
        if cv is None or inner is None:
            return
        try:
            total = inner.winfo_reqheight() or 1
            y, h = cb.winfo_y(), max(cb.winfo_reqheight(), 1)
            view_h = cv.winfo_height()
            top = cv.yview()[0] * total
            bot = top + view_h
            if y < top:
                cv.yview_moveto(max(0.0, (y - 4) / total))
            elif y + h > bot:
                cv.yview_moveto(min(1.0, (y + h + 4 - view_h) / total))
        except tk.TclError:
            return

    def _nav_clear(self):
        """Lepas ring fokus navigasi (baris tersembunyi filter/popup
        ditutup) — state _nav_cb dikosongkan supaya Space tidak toggle
        baris yang tidak terlihat."""
        cb, self._nav_cb = self._nav_cb, None
        if cb is not None and cb.winfo_exists():
            with contextlib.suppress(tk.TclError):
                cb.configure(style="TCheckbutton")

    def _reset(self):
        # v3.9.13: reset EKSAK — `selected` dibersihkan DULU (state
        # otoritatif) supaya nilai di luar cap MAX_CHECKS ikut kembali
        # terhitung "terpilih" (bukan hanya yang termaterialisasi).
        self.selected = None
        for var in self._vars.values():
            var.set(True)
        self._emit()
        self._update_count()

    def _do_sort(self, descending: bool):
        if self.on_sort is not None:
            self.on_sort(descending)
        self._close()

    def _close(self):
        if self._popup is not None:
            try:
                self._popup.grab_release()
            except Exception:
                pass
            _restore_grab(self._popup)  # FIX 6e-03 — SEBELUM destroy
            try:
                self._popup.destroy()
            except Exception:
                pass
        self._popup = None
        self._closed_at = _time.time()

    def clear(self):
        """Reset state filter dari luar (dipanggil tombol Reset Filter view).
        TIDAK memanggil on_apply — view memicu refresh sendiri."""
        self.selected = None
        for var in self._vars.values():
            var.set(True)
        self.refresh_icon()


class HeaderFilterGroup:
    """Pasang HeaderFilter di BANYAK kolom sekaligus (v3.5).

    "Semua header punya filter" — klik judul kolom mana pun membuka popup
    filter (nilai unik + search + checkbox) ala Excel AutoFilter; sort
    tersedia di dalam popup (tombol ↕ Sort A→Z / Z→A via on_sort).

    Pemakaian:
        group = HeaderFilterGroup(tree, cols,
                                   get_values=view._col_values,
                                   on_apply=view._on_col_filter,
                                   on_sort=lambda c, d: view._sort_by(c, reverse=d))
        # view menyimpan state: self._col_sel[col] = selected_set_or_None
        group.clear_all()   # dipanggil tombol Reset Filter (tanpa refresh)
    """

    def __init__(self, tree: ttk.Treeview, cols: list,
                 *, get_values, on_apply, on_sort=None):
        self._tree = tree
        self._get_values = get_values
        self._on_apply = on_apply
        self._on_sort = on_sort
        self._filters: dict = {}
        for col in cols:
            self._add_column(col)

    def _add_column(self, col):
        self._filters[col] = HeaderFilter(
            self._tree, col,
            get_values=(lambda c=col: self._get_values(c)),
            on_apply=(lambda sel, c=col: self._on_apply(c, sel)),
            label=col,
            on_sort=((lambda desc, c=col: self._on_sort(c, desc))
                     if self._on_sort is not None else None),
        )

    def add_columns(self, cols: list):
        """v3.9.45 — daftarkan kolom TAMBAHAN setelah tree di-reconfigure
        (kolom DINAMIS bulan-lalu tab 🧮 Nominal Deviasi: satu kolom per
        bulan file deviasi yang dimuat user): header filter/sort aktif
        juga di kolom baru; kolom yang sudah terdaftar di-skip
        (idempoten — aman dipanggil tiap render)."""
        for col in cols:
            if col not in self._filters:
                self._add_column(col)

    def clear_all(self):
        for f in self._filters.values():
            f.clear()

    def set_selected(self, col: str, values):
        """v3.9.22 — set seleksi kolom tertentu secara programatik."""
        f = self._filters.get(col)
        if f is not None:
            f.set_selected(values)

    def refresh_icons(self):
        for f in self._filters.values():
            f.refresh_icon()

    def open_popup(self, col):
        """Buka popup filter kolom tertentu (dipakai menu klik-kanan)."""
        f = self._filters.get(col)
        if f is not None:
            f.open_popup()

    def detach_all(self):
        """Lepas SEMUA binding klik-heading (saat ganti mode/kolom tree)."""
        for f in self._filters.values():
            f.detach()


# --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 roadmap #1) --------
#
# Generalisasi persist ui_zoom v3.9.65 ke FILTER: kombinasi filter terakhir
# per tab disimpan saat jendela ditutup (settings.json key 'filter_state')
# dan dipulihkan SEKALI setelah run pipeline PERTAMA sesi berikutnya
# (load_data me-reset filter — restore menyusul setelahnya; kontrak
# "run berikutnya = reset" v3.9.33 tetap utuh).
# Serialisasi state ⧩ (set|None per kolom) JSON-safe + validasi defensif
# (kolom/nilai tak dikenal diabaikan senyap — settings.json korup tidak
# bisa menyuntik tipe aneh ke view).

def col_sel_to_json(col_sel: dict) -> dict:
    """v3.9.66 — state filter header ⧩ → JSON-safe.

    {kolom: set|None} → {kolom: [nilai terurut]} — hanya entri AKTIF
    (None = tanpa filter, tidak disimpan; set() kosong disimpan sebagai
    [] agar snapshot tetap EKSAK — pemulihannya difilter di
    col_sel_from_json)."""
    out: dict = {}
    try:
        items = list((col_sel or {}).items())
    except AttributeError:
        return out
    for col, sel in items:
        if sel is None:
            continue
        try:
            out[str(col)] = sorted({str(v) for v in set(sel)})
        except TypeError:
            continue
    return out


def col_sel_from_json(raw, allowed) -> dict:
    """v3.9.66 — JSON → state filter header ⧩ (kebalikan col_sel_to_json).

    VALIDASI defensif:
    - hanya kolom yang ada di `allowed` (kolom view saat ini) yang
      dipulihkan — kolom hilang / schema berganti diabaikan senyap;
    - hanya nilai string yang diterima (korupsi settings.json tidak
      bisa menyuntik objek arbitrer);
    - v3.9.68 — TRI-STATE (audit eksternal T1): seleksi KOSONG ([])
      kini DIPULIHKAN sebagai set() kosong = filter AKTIF "0 baris"
      (semantik v3.9.13) — dulu dibuang, sehingga kondisi "user
      sengaja tidak memilih nilai apa pun" lenyap lintas sesi dan
      tabel tiba-tiba menampilkan semua baris lagi. Perilaku data
      identik in-session; kolom ⧩ yang dimaksud kini jujur menampilkan
      pesan 0-baris (zero_row_filter_message) di tiap view.
    Return {kolom: set(nilai)} — hanya entri yang lolos validasi."""
    if not isinstance(raw, dict):
        return {}
    try:
        allowed_set = {str(c) for c in allowed}
    except TypeError:
        return {}
    out: dict = {}
    for col, vals in raw.items():
        c = str(col)
        if (c not in allowed_set
                or not isinstance(vals, (list, tuple, set, frozenset))):
            continue
        if len(vals) == 0:
            out[c] = set()      # tri-state: seleksi kosong = 0 baris
            continue
        s = {v for v in vals if isinstance(v, str)}
        if s:
            out[c] = s
    return out


def apply_col_sel_restore(view, state, col_sel: dict, group) -> bool:
    """v3.9.66 — pulihkan bagian seleksi ⧩ view dari snapshot.

    Tulis kembali `col_sel[col]` (state otoritatif yang dibaca
    _refresh/_prepare_rows) + pasang ikon corong via
    HeaderFilterGroup.set_selected (pola preserve v3.9.42 — tanpa ini
    funnel tetap mati padahal filter aktif). Return True bila ada
    seleksi yang dipulihkan (caller melanjutkan combo/checkbox lalu
    refresh bila perlu)."""
    if not isinstance(state, dict):
        return False
    sel_map = col_sel_from_json(state, col_sel.keys())
    changed = False
    for col, sel in sel_map.items():
        col_sel[col] = sel
        if group is not None:
            with contextlib.suppress(Exception):
                group.set_selected(col, sel)
        changed = True
    return changed


def col_sel_empty_columns(col_sel: dict) -> list:
    """v3.9.68 — kolom ⧩ yang seleksinya KOSONG (set() = filter aktif
    yang menyaring 0 baris — semantik v3.9.13; lihat col_sel_from_json
    tri-state). Dipakai view utk pesan status yang jujur."""
    try:
        return [str(c) for c, s in (col_sel or {}).items()
                if s is not None and len(s) == 0]
    except (TypeError, ValueError, AttributeError):
        return []


def zero_row_filter_message(col_sel: dict) -> str | None:
    """v3.9.68 — pesan jujur saat tabel 0 baris KARENA seleksi ⧩ kosong
    (audit eksternal T1: "filter aktif → 0 baris" yang disengaja tidak
    boleh disamakan dengan "tanpa filter"; pengguna diberi tahu
    KENAPA kosong + cara keluar). Return None bila tidak ada seleksi
    kosong (penyebab 0 baris bukan ⧩ kosong — status generik view
    tetap dipakai)."""
    cols = col_sel_empty_columns(col_sel)
    if not cols:
        return None
    return ("0 baris — semua nilai tidak dipilih pada filter ⧩ "
            + ", ".join(f"'{c}'" for c in cols)
            + " (klik corong ⧩ di header kolom lalu centang "
              "'Pilih semua' / pilih kembali nilainya)")


# --- Column hide/unhide (v3.6) --------------------------------------------------

class ColumnManager:
    """Sembunyikan / tampilkan kolom tabel (displaycolumns) — v3.6.

    Permintaan user: "aku bisa hide dan unhide kolom juga gak?"
    - Klik KANAN di area heading → menu konteks:
        ⧩ Filter kolom ini · ↔ Auto-fit kolom ini ·
        ◱ Sembunyikan kolom ini · ▦ Tampilkan Semua · ◫ Panel Kolom…
    - open_panel() (tombol "◱ Kolom" per view) → popup checklist semua
      kolom (centang = tampil) — satu-satunya jalur unhide setelah kolom
      tersembunyikan.
    - State in-memory per tabel (reset saat aplikasi ditutup).
    - mirror: tree lain (mis. clone ⛶ / tabel utama) yang diterapkan
      konfigurasi kolom yang sama.
    - default_hidden (v3.9.52): daftar kolom yang disembunyikan SEJAK
      AWAL (user: "Secara default hide kolom Satuan di tab Deviasi Gr
      dan PCS") — kolom tetap bisa di-unhide lewat ◱ Kolom / klik kanan
      (nilainya tetap terbaca via tree.set — displaycolumns hanya soal
      tampilan).
    """

    def __init__(self, tree: ttk.Treeview, *, open_filter=None, mirror=None,
                 on_change=None, default_hidden=None):
        self.tree = tree
        self.open_filter = open_filter       # callable(col) → buka popup filter
        self.mirror = mirror                 # tree lain yang ikut hide/unhide
        self.on_change = on_change
        self.hidden: list[str] = [
            str(c) for c in (default_hidden or []) if c in self.columns()]
        self._panel: tk.Toplevel | None = None
        tree.bind("<Button-3>", self._on_right_click, add="+")
        # v3.7: daftarkan diri di tree supaya ColumnManager lain (mis. clone
        # ⛶ yang mirror ke tree ini) bisa sinkron state `hidden` — tanpa ini
        # hide di clone mengubah displaycolumns tree sumber TAPI state
        # colmgr sumber tetap kosong → panel Kolom sumber menampilkan
        # checkbox basi (kolom tampak tercentang padahal tersembunyi) dan
        # apply() berikutnya menimpa state mirror.
        try:
            tree._column_manager = self
        except Exception:
            pass
        # FIX B-18 (audit 2-b): mirror DUA ARAH. colmgr clone mendaftarkan
        # dirinya di tree SUMBER — apply() di sumber kini juga mendorong
        # konfigurasi kolom ke semua clone yang terbuka (dulu SATU ARAH
        # clone→source: hide kolom di tabel utama saat window ⛶ clone
        # masih terbuka TIDAK tercermin di clone).
        if mirror is not None:
            with contextlib.suppress(Exception):
                refs = list(getattr(mirror, "_mirror_backrefs", None) or [])
                refs.append(self)
                mirror._mirror_backrefs = refs
        # v3.9.52 — default_hidden: terapkan SEKARANG (tree masih kosong —
        # displaycolumns aman dikonfigurasi kapan pun) supaya sejak render
        # pertama kolom sudah tersembunyi; clone ⛶ menyalin displaycolumns
        # sumber saat dibuka (v3.6) → state awal konsisten.
        if self.hidden:
            self.apply()

    # -- state ---------------------------------------------------------------
    def columns(self) -> list[str]:
        try:
            return [str(c) for c in self.tree["columns"]]
        except Exception:
            return []

    def visible(self) -> list[str]:
        self.hidden = [c for c in self.hidden if c in self.columns()]
        return [c for c in self.columns() if c not in self.hidden]

    def apply(self):
        vis = self.visible()
        if not vis:
            return  # minimal 1 kolom harus tetap tampil
        try:
            self.tree.configure(displaycolumns=vis)
        except tk.TclError:
            return
        # FIX B-18 (audit 2-b): peer = tree mirror (arah lama clone→source)
        # + SEMUA clone yang terdaftar di tree ini (arah baru source→clone).
        # Push langsung configure displaycolumns + sinkron state hidden
        # colmgr peer — TANPA memanggil peer.apply() (bebas rekursi).
        peers: list = []
        if self.mirror is not None:
            peers.append(self.mirror)
        for mgr in list(getattr(self.tree, "_mirror_backrefs", None) or []):
            t = getattr(mgr, "tree", None)
            if t is not None and t not in peers:
                peers.append(t)
        for t in peers:
            try:
                if t is self.tree or not t.winfo_exists():
                    continue
            except tk.TclError:
                continue
            with contextlib.suppress(Exception):
                same = [str(c) for c in t["columns"]]
                mv = [c for c in vis if c in same]
                if mv:
                    t.configure(displaycolumns=mv)
                    # v3.7: sinkronkan state colmgr di tree peer supaya
                    # panel Kolom-nya konsisten (checkbox = kondisi
                    # sebenarnya)
                    tm = getattr(t, "_column_manager", None)
                    if tm is not None and tm is not self:
                        tm.hidden = [c for c in self.hidden
                                     if c in tm.columns()]
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass

    def hide(self, col: str):
        if col in self.columns() and col not in self.hidden \
                and len(self.visible()) > 1:
            self.hidden.append(col)
            self.apply()

    def toggle(self, col: str, visible: bool):
        if col not in self.columns():
            return
        if visible:
            self.hidden = [c for c in self.hidden if c != col]
        elif col not in self.hidden and len(self.visible()) > 1:
            self.hidden.append(col)
        self.apply()

    def show_all(self):
        self.hidden = []
        self.apply()

    # -- klik kanan heading ----------------------------------------------------
    def _on_right_click(self, event):
        try:
            if self.tree.identify_region(event.x, event.y) != "heading":
                return
            col = identify_to_column(
                self.tree, self.tree.identify_column(event.x))
        except Exception:
            return
        if col is None:
            return
        menu = tk.Menu(self.tree, tearoff=0, bg=C_CARD, fg=C_HEADER,
                       activebackground=C_ACCENT,
                       activeforeground="#ffffff", relief="flat", bd=0)
        label = "Nama Barang (#0)" if col == "#0" else str(col)
        if col != "#0":
            if self.open_filter is not None:
                menu.add_command(
                    label=f"⧩ Filter kolom '{label}'",
                    command=lambda c=col: self._safe_open_filter(c))
            menu.add_command(
                label="↔ Auto-fit kolom ini",
                command=lambda c=col: auto_fit_columns(self.tree,
                                                       columns=[c]))
            can_hide = len(self.visible()) > 1
            menu.add_command(
                label=f"◱ Sembunyikan kolom '{label}'",
                command=lambda c=col: self.hide(c),
                state="normal" if can_hide else "disabled")
        menu.add_command(label="▦ Tampilkan Semua Kolom",
                         command=self.show_all,
                         state="normal" if self.hidden else "disabled")
        menu.add_separator()
        menu.add_command(label="◫ Panel Kolom…", command=self.open_panel)
        menu.add_command(label="↔ Auto-fit Semua Kolom",
                         command=lambda: auto_fit_columns(self.tree))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    def _safe_open_filter(self, col):
        if self.open_filter is None:
            return
        try:
            self.open_filter(col)
        except Exception:
            pass

    # -- panel checklist --------------------------------------------------------
    def open_panel(self):
        if self._panel is not None and self._panel.winfo_exists():
            _restore_grab(self._panel)  # FIX 6e-03 — tutup toggle
            self._panel.destroy()
            return
        cols = self.columns()
        if not cols:
            return
        root = self.tree.winfo_toplevel()
        win = tk.Toplevel(root)
        self._panel = win
        win.title("Kolom — Sembunyikan / Tampilkan")
        win.configure(bg=C_CARD)
        win.transient(root)
        win.resizable(False, False)
        _take_grab(win)  # FIX 6e-03 — catat pemegang grab sebelumnya

        def _close_panel():
            # FIX 6e-03 — semua jalur tutup panel memulihkan grab modal
            # induk (Esc / ✕ Tutup / WM close / toggle) — dulu grab modal
            # (mis. DetailsPopup) hilang PERMANEN setelah panel ditutup.
            _restore_grab(win)
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _close_panel)

        body = tk.Frame(win, bg=C_CARD)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        head = tk.Frame(body, bg=C_CARD)
        head.pack(fill="x")
        tk.Label(head, text="◫ Kolom yang ditampilkan", bg=C_CARD,
                 fg=C_HEADER, font=font(10, "bold")).pack(side="left")
        n_vis = tk.StringVar(value=f"{len(self.visible())}/{len(cols)} tampil")
        tk.Label(head, textvariable=n_vis, bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(9)).pack(side="right")  # FIX A-08

        btnrow = tk.Frame(body, bg=C_CARD)
        btnrow.pack(fill="x", pady=(6, 4))

        def _refresh_count():
            n_vis.set(f"{len(self.visible())}/{len(cols)} tampil")

        def _show_all():
            self.show_all()
            for v in vars_.values():
                v.set(True)
            _refresh_count()

        # v3.9.59 — fix 2b-05 (audit 2-b): tombol panel ◱ Kolom kini
        # GhostButton terang — sama dengan popup ⧩ Filter (dulu tombol
        # gelap #1e293b di panel terang: dua popup kembar beda gaya; cursor
        # hand2 ikut otomatis dari GhostButton — fix 2a-07/2b-10).
        GhostButton(btnrow, text="▦ Tampilkan Semua",
                    command=_show_all).pack(side="left")
        GhostButton(btnrow, text="✕ Tutup (Esc)",
                    command=_close_panel).pack(side="right")

        # checklist scrollable (pivot matrix bisa punya 30+ kolom tanggal)
        cv = tk.Canvas(body, bg=C_CARD, highlightthickness=0,
                       height=min(340, 26 * len(cols) + 10))
        sb = ttk.Scrollbar(body, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=C_CARD)
        inner.bind("<Configure>",
                   lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # v3.9.57 — roda HALUS ber-AKUMULATOR (dulu trik `or -1`: tiap
        # event kecil memaksa 1 unit penuh = terlalu cepat di trackpad/
        # roda resolusi tinggi) + binding TINGKAT POPUP + X11 <Button-4/5>;
        # CTRL+Scroll tetap ZOOM UI (v3.9.48).
        enable_smooth_wheel_list(cv, container=win)

        vars_: dict[str, tk.BooleanVar] = {}

        def _on_toggle(c, v):
            self.toggle(c, v.get())
            _refresh_count()

        for c in cols:
            v = tk.BooleanVar(value=c not in self.hidden)
            vars_[c] = v
            ttk.Checkbutton(inner, text=c, variable=v,
                            command=lambda c=c, v=v: _on_toggle(c, v)) \
                .pack(anchor="w", padx=8, pady=1)

        win.bind("<Escape>", lambda e: _close_panel())  # FIX 6e-03
        win.update_idletasks()
        x = min(max(self.tree.winfo_rootx() + 40, 0),
                max(root.winfo_screenwidth() - win.winfo_reqwidth() - 20, 0))
        y = min(max(self.tree.winfo_rooty() + 60, 0),
                max(root.winfo_screenheight() - win.winfo_reqheight() - 40, 0))
        win.geometry(f"+{x}+{y}")


def _tree_row_passes(iid: str, kw: dict, col_idx: dict, active: dict,
                     value_get=None, parent_text: str = "") -> bool:
    """Cek 1 baris snapshot {text, values} lolos filter kolom aktif.

    '#0' (kolom tree) dicocokkan terhadap TEXT baris — baris ANAK
    (mis. metric pivot) dicocokkan terhadap text PARENT-nya (nama
    barang), sehingga pilih nama → parent + semua anak metricnya
    tampil (v3.7 FIX: dulu memakai text anak [nama metric] → filter
    nama di clone pivot menyembunyikan SEMUA baris).

    v3.7 FIX (deep audit): col_idx HARUS dari urutan kolom LOGIS
    (tree["columns"]) — values[] item diindeks secara logis, BUKAN
    urutan tampilan; setelah kolom disembunyikan, index display ≠
    index logis → filter membaca nilai kolom yang SALAH.

    v3.9.56 — ``value_get(iid, col, cur)``: override sumber nilai per
    baris×kolom (deviasi_view: kolom MERGE-VERTIKAL Nama Barang/Rank —
    nilai tree hanya di baris head/sticky; tanpa override, filter
    clone ⛶ by nama hanya meloloskan baris display — kelompok hilang
    sebagian, laten sejak v3.9.51).
    """
    vals = kw.get("values") or []
    text = str(kw.get("text") or "")
    for c, sel in active.items():
        if c == "#0":
            v = parent_text if parent_text else text
        else:
            k = col_idx.get(c)
            v = str(vals[k]) if (k is not None and 0 <= k < len(vals)) else ""
            if value_get is not None:
                with contextlib.suppress((AttributeError, IndexError,
                                           TypeError, ValueError,
                                           tk.TclError)):
                    v = str(value_get(str(iid), c, v))
        if v not in sel:
            return False
    return True


def apply_tree_row_filters(tree: ttk.Treeview, filters: dict,
                           on_done=None, value_get=None):
    """Terapkan filter kolom (nilai TERFORMAT) ke baris tree IN PLACE (v3.6).

    Dipakai tabel CLONE (⛶ Perbesar): snapshot item lengkap di-cache saat
    filter pertama dipasang; setiap perubahan → rebuild (delete + insert
    batched, urutan asli dipertahankan, iid tetap). Hirarki 2 level
    (parent + anak, mis. pivot matrix) didukung: parent tampil bila ada
    anak yang lolos filter; filter '#0' mencocokkan text parent.

    v3.9.5 FIX (audit 19-a #3 / 19-c #4): rebuild (delete+insert) me-reset
    TAG PER-CELL — parameter ``on_done`` dipanggil setelah semua baris
    selesai di-insert ulang supaya view bisa memasang ulang tag cell
    (minus merah / warna Status) di clone ⛶.

    v3.9.56 — ``value_get(iid, col, cur)``: sumber nilai RAW per baris
    (kolom merge-vertikal deviasi_view — nilai tree head-only/sticky).

    FIX 6b-04 (audit 6-b): batch insert yang masih berjalan (copy awal
    clone ⛶) dibatalkan SEBELUM snapshot cache dibangun; bila copy masih
    in-flight, cache lengkap diambil dari snapshot ``tree._full_items``
    yang ditinggalkan open_tree_maximized (dulu cache dibangun dari baris
    PARSIAL → sisa batch dibatalkan → clone terpotong diam-diam).
    """
    # v3.9.13: seleksi KOSONG = filter AKTIF (0 baris, semantik Excel) —
    # dulu truthiness `if s` menelan set() sebagai "tanpa filter".
    active = {c: s for c, s in filters.items() if s is not None}
    try:
        # FIX 6b-04 (audit 6-b): batalkan batch insert pending DULU —
        # membangun cache dari baris parsial lalu membatalkan sisa batch
        # membuat clone kehilangan baris yang belum tersalin.
        prev = getattr(tree, "_row_filter_cancel", None)
        if prev is not None:
            prev()
        cache = getattr(tree, "_row_filter_cache", None)
        if cache is None:
            full = getattr(tree, "_full_items", None)
            if full:
                # FIX 6b-04: copy clone masih berjalan — sumber cache =
                # snapshot PENUH (bukan baris yang sempat ter-insert);
                # sekaligus finalisasi copy (hide overlay, label baris,
                # on_render_done) yang tidak akan pernah dipanggil batch
                # yang baru saja dibatalkan.
                cache = list(full)
                finalize = getattr(tree, "_copy_finalize", None)
                if finalize is not None:
                    with contextlib.suppress(Exception):
                        finalize()
            else:
                def rec(parent, out):
                    for iid in tree.get_children(parent):
                        it = tree.item(iid)
                        out.append((parent, iid, {
                            "text": it.get("text", ""),
                            "values": it.get("values", ""),
                            "tags": it.get("tags", ""),
                            "open": it.get("open", False),
                        }))
                        rec(iid, out)
                cache = []
                rec("", cache)
            tree._row_filter_cache = cache
        if not cache:
            return
        kids_map: dict = {}
        for parent, iid, kw in cache:
            kids_map.setdefault(parent, []).append((iid, kw))
    except tk.TclError:
        return

    # v3.7 FIX: index values = urutan kolom LOGIS (bukan display) —
    # nilai item Treeview diindeks sesuai tree["columns"]
    try:
        logical_cols = [str(c) for c in tree["columns"]]
    except Exception:
        logical_cols = []
    col_idx = {c: i for i, c in enumerate(logical_cols)}
    items = []
    if not active:
        items = [(p, i, kw) for (p, i, kw) in cache]
    else:
        for iid, kw in kids_map.get("", []):
            kids = kids_map.get(iid)
            if kids:
                # parent 2-level: '#0'/text diuji pada parent, kolom data
                # diuji pada anak — parent tampil bila ada anak yang lolos
                kept = [(k, w) for (k, w) in kids
                        if _tree_row_passes(k, w, col_idx, active,
                                            value_get=value_get,
                                            parent_text=str(kw.get("text") or ""))]
                if kept:
                    items.append(("", iid, kw))
                    items.extend((iid, k, w) for (k, w) in kept)
            elif _tree_row_passes(iid, kw, col_idx, active,
                                   value_get=value_get):
                items.append(("", iid, kw))

    try:
        tree.delete(*tree.get_children(""))
    except tk.TclError:
        return

    # FIX B-14 (audit 2-b): rebuild dari cache memakai URUTAN ASLI —
    # toggle filter dulu mengembalikan urutan sort senyap. Kini sort
    # TERAKHIR tree (tree._last_sort, dicatat sort_tree_by_column)
    # dijalankan ulang SEBELUM on_done, jadi tag per-cell dipasang pada
    # URUTAN FINAL (sort dulu, reapply tag sesudahnya).
    def _done():
        ls = getattr(tree, "_last_sort", None)
        if ls is not None:
            with contextlib.suppress(Exception):
                sort_tree_by_column(
                    tree, ls[0], reverse=ls[1], parse=ls[2],
                    value_get=(ls[3] if len(ls) > 3 else None))
        if on_done:
            on_done()
    tree._row_filter_cancel = insert_tree_items(tree, items, batch=600,
                                                on_done=_done)


def attach_clone_filters(tree: ttk.Treeview, cols: list, *,
                         get_values, on_sort=None, on_after_filter=None,
                         value_get=None, filter_tree=None):
    """HeaderFilterGroup utk tabel CLONE ⛶ (v3.6).

    Sebelumnya clone ⛶ MENYALIN ikon funnel dari heading sumber tapi TIDAK
    memasang binding apa pun → funnel tidak bisa diklik (bagian dari bug
    "tombol filter tidak bisa diklik"). Sekarang clone punya filter
    sendiri: on_apply memfilter baris clone IN PLACE (cache snapshot),
    sort via popup (tree-aware).

    v3.9.5 (audit 19-a #3): ``on_after_filter`` dipanggil setelah rebuild
    filter selesai — dipakai view utk memasang ulang TAG PER-CELL di
    clone (dulu: filter di clone menghapus minus-merah & warna Status).
    Callback apply juga disimpan di ``tree._clone_filter_apply``
    (dipakai test / integrasi).

    v3.9.56 — ``value_get(iid, col, cur)``: sumber nilai RAW utk kolom
    merge-vertikal (deviasi_view) — filter clone by Nama Barang/Rank
    mencocokkan nilai snapshot per baris, bukan nilai display tree
    (head-only) → kelompok UTUH lolos filter.

    v3.9.71 — ``filter_tree``: tree yang BARISNYA difilter bila berbeda
    dari tree tempat funnel menempel (freeze-pane pivot: funnel di tree
    beku kiri, baris difilter di tree utama kanan — cache snapshot
    `_full_items`/`_row_filter_cancel` hidup di sisi kanan). Default
    None = tree itu sendiri (perilaku lama, 12 view lain tak berubah);
    hook `_clone_filter_apply` dipasang di KEDUA tree supaya test yang
    membacanya dari tree utama clone tetap jalan.
    """
    state: dict = {}
    target = tree if filter_tree is None else filter_tree

    def on_apply(col, sel):
        state[col] = sel
        apply_tree_row_filters(target, state, on_done=on_after_filter,
                               value_get=value_get)

    tree._clone_filter_apply = on_apply
    if filter_tree is not None and filter_tree is not tree:
        filter_tree._clone_filter_apply = on_apply
    return HeaderFilterGroup(tree, cols, get_values=get_values,
                             on_apply=on_apply, on_sort=on_sort)


# --- Async + render batched ---------------------------------------------------

# BUG WORKAROUND (CPython 3.12 + Tk 9 di beberapa build): objek Thread daemon
# yang baru selesai dapat di-finalisasi oleh GC tepat saat main thread
# mengeksekusi Tk after(), yang bisa memicu segfault level C. Menyimpan
# referensi thread yang sudah selesai (bounded) mencegah finalisasi Thread
# oleh GC pada momen acak.
_worker_threads: list = []
_MAX_KEPT_THREADS = 40

# v3.9 CRASH FIX (terbukti saat test shared-H): tk.Variable.__del__ memanggil
# Tcl (globalunsetvar). Bila GC berjalan DI THREAD WORKER — termasuk tepat
# saat thread exit (threading._delete) — dan menemukan garbage
# Variable/StringVar sisa popup/clone window yang sudah ditutup, finalisasi
# terjadi dari thread BUKAN-main → segfault heap ("alloc: invalid block") di
# CPython 3.12 + Tk. Dulu nyaris tak pernah terjadi (hanya 1 job async pada
# satu waktu); v3.9 me-refresh 2 view sekaligus (GR + PCS saat Apply H) →
# 2 thread exit berdekatan → jendela crash kena. Solusi: GC dimatikan SELAMA
# thread worker hidup (bukan hanya saat work() — fase thread-exit juga
# rawan) dan hanya dinyalakan kembali dari MAIN thread SETELAH thread
# benar-benar mati (dicek via is_alive + retry 15ms).
_GC_HOLD = {"depth": 0, "was_enabled": True}
# FIX B-06 (audit 2-b): acquire dipanggil dari THREAD worker — dua job
# start hampir bersamaan dapat race read-modify-write `depth` (keduanya
# membaca 0 → depth akhir 1 padahal 2 job aktif → release pertama
# menyalakan GC saat worker kedua masih hidup = persis jendela segfault
# CPython 3.12+Tk yang shield dirancang cegah). Lock kecil menutupnya.
_GC_LOCK = threading.Lock()


def gc_shield_acquire() -> None:
    """Matikan GC otomatis — dipanggil dari thread yang akan bekerja.

    Nested-safe: job bersamaan dihitung depth; GC dinyalakan kembali saat
    job TERAKHIR dilepas (FIX B-06: dihitung atomik lewat _GC_LOCK)."""
    with _GC_LOCK:
        if _GC_HOLD["depth"] == 0:
            _GC_HOLD["was_enabled"] = _gc.isenabled()
            _gc.disable()
        _GC_HOLD["depth"] += 1


def gc_shield_release(thread_obj=None, retry_widget=None) -> None:
    """Nyalakan kembali GC — HARUS dipanggil dari MAIN thread.

    Bila thread_obj masih hidup, jadwalkan retry (after 15ms) sampai mati —
    thread-exit dengan GC menyala persis kondisi crash yang dihindari.
    retry_widget umumnya widget pemilik job (masih hidup). Bila widget juga
    mati, join singkat (bounded 0.3s) lalu lepas (app sedang ditutup).
    FIX B-06: seluruh manipulasi depth di dalam _GC_LOCK (atomik)."""
    with _GC_LOCK:
        if _GC_HOLD["depth"] <= 0:
            return
        if thread_obj is not None and thread_obj.is_alive():
            scheduled = False
            if retry_widget is not None:
                try:
                    if retry_widget.winfo_exists():
                        retry_widget.after(
                            15, lambda: gc_shield_release(thread_obj,
                                                          retry_widget))
                        scheduled = True
                except tk.TclError:
                    scheduled = False
            if scheduled:
                return
            # widget mati — tunggu thread mati secara singkat (bounded)
            thread_obj.join(0.3)
            if thread_obj.is_alive():
                # masih terjepit (sangat lama) — lepas; sisa risiko hanya bila
                # app ditutup di tengah proses (jarang, dapat diterima).
                pass
        _GC_HOLD["depth"] -= 1
        if _GC_HOLD["depth"] == 0 and _GC_HOLD["was_enabled"]:
            _gc.enable()


def _spawn_worker(target) -> threading.Thread:
    t = threading.Thread(target=target, daemon=True)
    _worker_threads.append(t)
    if len(_worker_threads) > _MAX_KEPT_THREADS:
        del _worker_threads[: _MAX_KEPT_THREADS // 2]
    t.start()
    return t


def _poll_host(widget):
    """v3.9.5 FIX (audit 19-c #1) — host timer poll run_async yang ABADI.

    Poll dulu dijadwalkan pada widget PEMILIK job (mis. Toplevel popup
    detail). Bila pemilik di-destroy di tengah job — popup ditutup saat
    render masih berjalan — callback after() tidak pernah menembak:
    on_done/on_error tidak jalan, shield GC tidak pernah dilepas, dan
    gc.disable() MENEMPEL seumur sesi (kebocoran memori seluruh app;
    cabang winfo_exists() di poll() tadinya kode mati). Poll dipindah ke
    ROOT aplikasi (naik rantai master — hidup sepanjang sesi)."""
    w = widget
    seen = set()
    while True:
        if id(w) in seen:
            break
        seen.add(id(w))
        master = getattr(w, "master", None)
        if master is None:
            break
        w = master
    return w


def run_async(widget, work, on_done, overlay: LoadingOverlay | None = None,
              loading_text: str | None = None, on_error=None,
              sync: bool = False) -> dict:
    """Jalankan work() (compute murni, TANPA sentuhan widget) di thread
    terpisah; hasil dikirim ke on_done(result) di main thread.

    Overlay otomatis show/hide. sync=True → blocking (untuk test).
    Return dict job: {"busy": bool, "cancel": callable}.

    v3.9: GC dimatikan SELAMA THREAD HIDUP (work + fase exit) — finalisasi
    tk.Variable dari thread worker (pemicu segfault CPython 3.12+Tk, mis.
    saat 2 view di-refresh bersamaan) jadi mustahil; GC dinyalakan kembali
    dari main thread setelah thread mati (gc_shield_release).
    """
    job = {"busy": True, "cancelled": False, "result": None, "error": None,
           "traceback": None, "_thread": None}
    host = _poll_host(widget)

    def finish():
        if overlay is not None:
            overlay.hide()
        # v3.9.5: retry pada HOST (root) — pemilik job bisa saja sudah
        # di-destroy saat finish menembak.
        gc_shield_release(job["_thread"], retry_widget=host)
        err = job["error"]
        if err is not None:
            if on_error is not None:
                on_error(err)
            else:
                try:
                    _mb.showerror(
                        "Error Memproses",
                        f"Gagal memproses data:\n\n{err}", parent=widget)
                except Exception:
                    print(job.get("traceback") or err)
        else:
            on_done(job["result"])

    def _exec_work():
        try:
            job["result"] = work()
        except Exception as e:  # pragma: no cover
            import traceback as _tb
            job["error"] = e
            job["traceback"] = _tb.format_exc()
        finally:
            # FIX B-20 (audit 2-b): BaseException (mis. SystemExit dari
            # dalam work) tidak boleh melompati reset busy — dulu poll
            # abadi 70ms + gc.disable() menempel seumur sesi.
            job["busy"] = False

    def runner():
        # PENTING (v3.9): GC dimatikan di sini dan TIDAK dinyalakan ulang di
        # thread ini — tetap mati sampai thread benar-benar mati, termasuk
        # saat threading._delete berjalan (bekas jendela crash: GC di
        # thread-exit mem-finalisasi tk.Variable sisa popup/clone window).
        gc_shield_acquire()
        _exec_work()

    if sync:
        # sync: work() di MAIN thread — shield dilepas langsung (aman:
        # finalisasi juga terjadi di main thread)
        gc_shield_acquire()
        try:
            _exec_work()
        except BaseException:
            # FIX B-20 (audit 2-b): BaseException (SystemExit dkk) di jalur
            # sync tidak boleh meninggalkan shield menempel — lepas dulu
            # lalu re-raise (job["busy"] sudah di-reset oleh finally di
            # _exec_work). Jalur worker pulih otomatis via poll→finish.
            gc_shield_release(None)
            raise
        finish()
        return job

    if overlay is not None:
        overlay.show(loading_text)
    job["_thread"] = _spawn_worker(runner)

    def _sched_poll():
        try:
            host.after(70, poll)
        except tk.TclError:
            pass

    def poll():
        if job["cancelled"]:
            # hasil dibuang — tapi tunggu thread selesai supaya shield GC
            # bisa dilepas dengan aman (thread-exit dgn GC nyala = crash)
            if job["busy"]:
                _sched_poll()
            else:
                if overlay is not None:
                    overlay.hide()
                gc_shield_release(job["_thread"], retry_widget=host)
            return
        try:
            if not widget.winfo_exists():
                # widget PEMILIK ditutup — buang hasil, lepas shield GC via
                # host (root, masih hidup). Cabang ini dulu KODE MATI:
                # poll dijadwalkan pada pemilik yang mati → tak pernah
                # menembak → gc.disable() menempel seumur sesi (audit 19-c
                # #1: popup detail ditutup saat render berjalan).
                if overlay is not None:
                    overlay.hide()
                gc_shield_release(job["_thread"], retry_widget=host)
                return
        except tk.TclError:
            return
        if job["busy"]:
            _sched_poll()
            return
        finish()

    with contextlib.suppress(tk.TclError):
        host.after(70, poll)
    job["cancel"] = lambda: job.update(cancelled=True)
    return job


def insert_tree_items(tree: ttk.Treeview, items: list, *, batch: int = 400,
                      on_done=None, chunk_callback=None, delay: int | None = None):
    """Insert items [(parent_iid, iid, kwargs)] bertahap per-batch via after()
    supaya UI tetap responsif (spinner tetap hidup) saat render data besar.

    v3.3: delay adaptif — tabel besar (>20k baris) memakai 1ms/batch,
    jadi 50k baris tidak lagi menunggu +1 detik ekstra (dulu 10ms/batch).

    FIX 6b-06 (audit 6-b): TclError PER-ITEM (mis. iid duplikat dari bug
    view / Tcl transien) dulu membatalkan SISA batch + on_done TIDAK
    pernah dipanggil — caller yang menunggu render_done (reset _busy,
    pasang tag cell, autofit pertama, hide overlay clone) menunggu
    selamanya tanpa pesan. Kini item gagal di-skip (dihitung + catatan
    stderr ringkas), batch lanjut, on_done SELALU dipanggil di akhir
    (kecuali tree sudah mati — view juga sudah tidak ada).

    Return fungsi cancel() utk membatalkan sisa batch.
    """
    if delay is None:
        delay = 10 if len(items) <= 20_000 else 1
    state = {"i": 0, "cancelled": False, "failed": 0, "finished": False}

    def _finish():
        # FIX 6b-06: dipanggil PERSIS SEKALI di akhir jalur sukses —
        # jalur error per-item tidak boleh memotong on_done.
        if state["finished"] or state["cancelled"]:
            return
        state["finished"] = True
        if state["failed"]:
            # tidak senyap: baris + jumlah ke stderr (tidak per-item supaya
            # batch 50k tidak membanjiri log)
            print(f"insert_tree_items: {state['failed']} item dilewati "
                  f"(TclError — iid duplikat/baris invalid)", file=sys.stderr)
        if on_done:
            on_done()
        # v3.9.64 — FIX (audit 15-c F-03): render penuh selesai → popup
        # Cari milik tree menghitung ULANG (iid posional row_N dipakai
        # ulang view pasca re-render; tanpa ini highlight lama mendarat
        # di baris SALAH — semua iid masih "ada" sehingga _refresh_stale
        # tidak terpicu).
        _pop = getattr(tree, "_find_popup", None)
        if _pop is not None:
            with contextlib.suppress(Exception):
                _pop._on_tree_rerendered()

    def chunk():
        if state["cancelled"]:
            return
        try:
            if not tree.winfo_exists():
                return
        except tk.TclError:
            return
        start = state["i"]
        end = min(start + batch, len(items))
        # FIX 6b-06 (audit 6-b): try/except PER-ITEM — satu TclError
        # (iid duplikat) tidak lagi membatalkan sisa batch.
        for parent_iid, iid, kw in items[start:end]:
            try:
                tree.insert(parent_iid, "end", iid=iid, **kw)
            except tk.TclError:
                state["failed"] += 1
        state["i"] = end
        if chunk_callback:
            try:
                chunk_callback(end, len(items))
            except Exception:
                pass
        if end < len(items):
            try:
                tree.after(delay, chunk)
            except tk.TclError:
                # timer gagal dipasang (tree mati di tengah) — tetap
                # finalisasi supaya caller tidak menggantung
                _finish()
        else:
            _finish()

    if items:
        chunk()
    else:
        # v3.9.64 — F-03: render "kosong" (0 item) juga menuntaskan siklus
        # render → popup Cari ikut menghitung ulang (query bisa jadi tak
        # cocok lagi — view terfilter habis).
        if on_done:
            on_done()
        _pop = getattr(tree, "_find_popup", None)
        if _pop is not None:
            with contextlib.suppress(Exception):
                _pop._on_tree_rerendered()

    def cancel():
        state["cancelled"] = True

    return cancel


# --- Per-cell tag (v3.9.2) — minus merah per CELL, bukan per baris -----------
#
# ttk.Treeview klasik hanya bisa mewarnai per BARIS (tag item). Tk 9.0
# menambah API `treeview tag cell add <tag> <cells>` — tag per CELL.
# Dipakai supaya nilai minus TIDAK mewarnai seluruh baris: hanya cell
# bernilai negatif yang merah (permintaan user v3.9.2).
# v3.9.22 (user: "Saat ini disemua tab warna masih tidak per cell tapi
# per row. coba cari alternatif lain"): Tk 8.6 (Python standar Windows)
# TIDAK punya API `tag cell` — semua warna jatuh ke fallback tag per BARIS.
# ALTERNATIF: overlay tk.Label per sel — Label di-place PERSIS di atas sel
# warna (bbox per sel) dgn teks + warna tag sel & latar baris efektif.
# Label hanya utk sel warna yang TERLIHAT (virtual — murah di tabel 6k+),
# dipasang ulang tiap scroll/resize/seleksi, dan meneruskan klik/wheel ke
# tree (event_generate) supaya seleksi, ✓ checkbox, klik-kanan copy, dan
# double-click popup tetap jalan.
#
# Konstanta:
# - CELL_TAGS_NATIVE    : API native `tag cell` tersedia (Tk >= 9.0).
# - CELL_TAGS_SUPPORTED : per-cell warna AKTIF di SEMUA versi Tk (native
#   Tk 9 / overlay Label Tk 8.6 — nama lama dipertahankan supaya view &
#   test yang mengimpornya tetap kompatibel).

CELL_TAGS_NATIVE = tk.TkVersion >= 9.0
CELL_TAGS_SUPPORTED = True


def _style_rowheight(style) -> int:
    """rowheight style Treeview (int) — fallback 20 bila kosong."""
    try:
        v = style.lookup("Treeview", "rowheight")
        return int(v) if str(v).strip() else 20
    except (ValueError, TypeError, tk.TclError):
        return 20


def _style_map_value(style, option: str, state: str) -> str:
    """Nilai style.map Treeview utk state tertentu (mis. 'selected')."""
    try:
        pairs = style.map("Treeview", option)
    except tk.TclError:
        return ""
    if isinstance(pairs, str):
        pairs = [tuple(pairs.split())] if pairs else []
    for pair in pairs or ():
        if len(pair) >= 2 and pair[0] == state:
            return str(pair[1])
    return ""


class CellColorOverlay:
    """v3.9.22 — per-cell warna di Tk 8.6 via OVERLAY Label.

    Satu overlay per Treeview (dibuat lazy `_overlay_for_tree`); dipakai
    `apply_cell_tag` bila `CELL_TAGS_NATIVE` False. Semantik mengikuti
    `treeview tag cell` Tk 9: `set_cells(tag, cells)` MENGGANTI anggota
    tag (replace — view selalu memanggil ulang dgn daftar lengkap setelah
    render/sort/filter/clone).

    Prioritas warna per sel (meniru Tk 9 — probe v3.9.18: bg cell-tag
    MENGALAHKAN bg item-tag; dua cell-tag beda opsi KOEXIST di sel sama):
      background: bg tag-SEL → bg tag BARIS (evenrow/oddrow/…) →
                  fieldbackground style
      foreground: fg tag-SEL → fg tag BARIS → fg style
    Baris TERSELEKSI: bg/fg seleksi (style.map 'selected') dipakai HANYA
    bila sel tidak punya opsi tag-nya sendiri (sel berwarna tetap tampak
    berwarna saat barisnya dipilih).
    """

    # <Button-1> ditangani handler `press` khusus (deteksi double manual)
    _FORWARD_SEQS = (
        "<Button-3>", "<ButtonRelease-1>",
        "<B1-Motion>", "<MouseWheel>", "<Button-4>", "<Button-5>",
    )

    # v3.9.29 — LABEL POOL: label yang keluar dari viewport dikembalikan
    # ke pool & DI-REUSE (bukan destroy/create tk.Label baru). Pembuatan
    # widget saat scroll beruntun = mahal + label 'pop-in' telat 1 frame
    # (= 'patah-patah' yang dikeluhkan user); reuse hanya reconfigure+
    # place (orde µs).
    _POOL_MAX = 96

    def __init__(self, tree: ttk.Treeview):
        self.tree = tree
        self._tag_cells: dict = {}      # tag -> set[(iid, col)]
        self._tag_opts: dict = {}       # tag -> {background/foreground}
        self._by_iid: dict = {}         # iid -> [(col, opts), ...]
        self._labels: dict = {}         # (iid, col) -> tk.Label (AKTIF)
        self._pool: list = []           # v3.9.29 — label nganggur (reuse)
        self._last_frac: dict = {}      # v3.9.29 — frac terakhir per opt
        self._pending = None
        self._alive = True
        # v3.9.40 — CACHE RENDER + FLUSH GEOMETRI SINKRON (anti-glitch
        # scroll; lihat _flush_geometry): nilai style, warna tag baris,
        # anchor kolom, dan warna baris per iid TIDAK berubah selama
        # scroll — dulu dibaca ulang via Tcl untuk SETIAP sel di SETIAP
        # notch (~500 panggilan/notch di tabel 20 kolom) + konfigurasi
        # label dikirim ulang meski isinya identik.
        self._style_cache = None       # (style, rowheight, font, ...)
        self._rowtag_cache: dict = {}  # tag baris -> (bg, fg)
        self._rowbg_cache: dict = {}   # iid -> (bg, fg) tag-baris efektif
        self._anchor_cache: dict = {}  # kolom -> anchor
        self._flushing = False
        # deteksi double-click manual (label press + press terforward
        # saat ini berjalan rekursif → sintesis <Double-1> Tk tidak bisa
        # diandalkan; timer 400ms ala Tk default)
        self._dbl_t = 0.0
        self._dbl_lab = None
        # v3.9.40 — REGISTRASI MANDIRI di tree: apa pun jalur pembuatan
        # ( konstruktor langsung / _overlay_for_tree), handler roda
        # (_redraw_overlay_now) menemukan overlay via atribut ini.
        with contextlib.suppress(AttributeError, tk.TclError):
            tree._cell_color_overlay = self
        self._wrap_scroll("yscrollcommand")
        self._wrap_scroll("xscrollcommand")
        tree.bind("<Configure>", self._on_configure, add="+")
        tree.bind("<<TreeviewSelect>>", self._schedule, add="+")
        tree.bind("<ButtonRelease-1>", self._schedule, add="+")
        tree.bind("<Destroy>", self._on_destroy, add="+")

    # -- cache render (v3.9.40) --------------------------------------------
    def _on_configure(self, _event=None):
        # v3.9.40 — ukuran widget berubah: rowheight/style bisa ikut berubah
        self._invalidate_render_cache()
        self._schedule()

    def _invalidate_render_cache(self):
        """Buang cache render — dipanggil saat konten/ukuran berubah
        (set_cells / <Configure>). Seleksi BARIS tidak perlu invalidate:
        warna seleksi diterapkan live saat draw (cache hanya menyimpan
        warna tag-baris mentah)."""
        self._style_cache = None
        self._rowtag_cache = {}
        self._rowbg_cache = {}
        self._anchor_cache = {}

    def _style_ctx(self):
        """(style, rowheight, font, field_bg, base_fg, sel_bg, sel_fg)
        — di-cache sampai invalidate (dulu 4+ lookup style per redraw)."""
        if self._style_cache is None:
            style = ttk.Style(self.tree)
            try:
                font = style.lookup("Treeview", "font") or "TkDefaultFont"
            except tk.TclError:
                font = "TkDefaultFont"
            self._style_cache = (
                style,
                _style_rowheight(style),
                font,
                style.lookup("Treeview", "background") or "#ffffff",
                style.lookup("Treeview", "foreground") or "#000000",
                _style_map_value(style, "background", "selected"),
                _style_map_value(style, "foreground", "selected"),
            )
        return self._style_cache

    def _rowtag_colors(self, tag):
        """(bg, fg) tag BARIS — di-cache per nama tag (dulu tag_configure
        per tag per baris per redraw)."""
        try:
            return self._rowtag_cache[tag]
        except KeyError:
            pass
        try:
            cfg = self.tree.tag_configure(tag)
        except tk.TclError:
            cfg = {}
        val = (str((cfg or {}).get("background") or ""),
               str((cfg or {}).get("foreground") or ""))
        self._rowtag_cache[tag] = val
        return val

    def _col_anchor(self, col):
        try:
            return self._anchor_cache[col]
        except KeyError:
            pass
        try:
            a = self.tree.column(col, "anchor") or "w"
        except tk.TclError:
            a = "w"
        self._anchor_cache[col] = a
        return a

    def _row_colors(self, iid, sel_set, sel_bg, sel_fg,
                    field_bg, base_fg):
        """Warna baris efektif utk sel TANPA opsi sendiri: tag baris
        (opsi pertama terisi menang — meniru Treeview) → seleksi.
        Warna tag-baris di-cache per iid; seleksi diterapkan live."""
        cached = self._rowbg_cache.get(iid)
        if cached is None:
            row_bg, row_fg = "", ""
            try:
                tags = self.tree.item(iid, "tags") or ()
            except tk.TclError:
                tags = ()
            for t in tags:
                bg, fg = self._rowtag_colors(str(t))
                if not row_bg and bg:
                    row_bg = bg
                if not row_fg and fg:
                    row_fg = fg
                if row_bg and row_fg:
                    break
            cached = (row_bg, row_fg)
            self._rowbg_cache[iid] = cached
        row_bg, row_fg = cached
        sel = iid in sel_set
        bg_row = sel_bg if (sel and sel_bg) else (row_bg or field_bg)
        fg_row = sel_fg if (sel and sel_fg) else (row_fg or base_fg)
        return bg_row, fg_row

    def _flush_geometry(self):
        """v3.9.40 — paksa Tk memproses pergeseran label SEKARANG.

        AKAR GLITCH SCROLL YANG TERSEDIA (probe Xvfb, terukur):
        ``place()``/``place_forget()`` itu DEFERRED — Tk baru memindahkan
        jendela label di idle GEOMETRI, sementara repaint isi tree
        terjadi lebih dulu → sel warna tampak TERTINGGAL 1 frame di
        posisi lama (probe: lab_y=210 vs bbox_y=191 segera setelah
        scroll tanpa update) → saat menggulir terus-menerus, sel warna
        'berenang' di atas baris yang salah (glitch/tearing).

        Flush ``update_idletasks`` di AKHIR redraw membuat pergeseran
        label + repaint tree terjadi dalam SATU burst sinkron
        (sub-milidetik) — tidak ada frame layar yang menyela. Guard
        ``_flushing`` mencegah rekursi (idle lain yang memicu scroll
        → redraw → flush bersarang)."""
        if self._flushing or not self._alive:
            return
        self._flushing = True
        try:
            self.tree.update_idletasks()
        except tk.TclError:
            pass
        finally:
            self._flushing = False

    # -- lifecycle -----------------------------------------------------------
    def _on_destroy(self, _event=None):
        self._alive = False
        if self._pending is not None:
            with contextlib.suppress(tk.TclError):
                self.tree.after_cancel(self._pending)
            self._pending = None
        # v3.9.29 — label (aktif + pool) adalah anak tree: ikut musnah
        # bersama tree; bersihkan referensi saja.
        self._labels.clear()
        self._pool.clear()

    def _wrap_scroll(self, opt: str):
        """Bungkus y/xscrollcommand tree supaya redraw terjadi tiap
        scroll / insert / delete / resize kolom (perubahan layout sel).

        v3.9.29 — SINKRON saat view BERUBAH (bukan menunggu idle):
        yscrollcommand dipanggil widget SETELAH state internal ter-update
        (bbox saat itu sudah benar). Menunggu after_idle membuat label
        tertinggal 1 frame di posisi lama → label 'melayang' di atas
        baris salah saat scroll (tearing / patah-patah). Redraw langsung
        kini murah berkat label pool. Frac TIDAK berubah → tetap idle
        (mis. callback ulang tanpa scroll — murah dan tetap aman)."""
        try:
            orig = str(self.tree.cget(opt))
        except tk.TclError:
            return

        def wrap(first, last, _orig=orig, _opt=opt):
            if _orig:
                with contextlib.suppress(tk.TclError):
                    self.tree.tk.call(_orig, first, last)
            if self._alive and self._last_frac.get(_opt) != (first, last):
                self._last_frac[_opt] = (first, last)
                self._redraw()
            else:
                self._schedule()

        with contextlib.suppress(tk.TclError):
            self.tree.configure(**{opt: wrap})

    # -- API (dipakai apply_cell_tag) ---------------------------------------
    def set_cells(self, tag: str, cells) -> None:
        """GANTI daftar sel utk satu tag (semantik replace ala Tk 9)."""
        if not self._alive:
            return
        tag = str(tag)
        spec = {(str(iid), str(col)) for iid, col in (cells or [])}
        self._tag_cells[tag] = spec
        opts = {}
        try:
            cfg = self.tree.tag_configure(tag)
        except tk.TclError:
            cfg = {}
        bg = str((cfg or {}).get("background") or "")
        fg = str((cfg or {}).get("foreground") or "")
        if bg:
            opts["background"] = bg
        if fg:
            opts["foreground"] = fg
        self._tag_opts[tag] = opts
        # v3.9.40 — konten/tema tag berubah → buang cache render
        self._invalidate_render_cache()
        self._rebuild()
        self._schedule()

    def _rebuild(self):
        """Gabungkan semua tag sel → indeks per iid (hanya sel dgn opsi
        warna — tag tanpa background/foreground tak digambar)."""
        merged: dict = {}
        for tag, spec in self._tag_cells.items():
            opts = self._tag_opts.get(tag) or {}
            if not opts:
                continue
            for key in spec:
                cell = merged.setdefault(key, {})
                for k, v in opts.items():
                    cell[k] = v
        by: dict = {}
        for (iid, col), opts in merged.items():
            by.setdefault(iid, []).append((col, opts))
        self._by_iid = by
        stale = [k for k in self._labels if k not in merged]
        for k in stale:
            self._destroy_label(k)

    # -- redraw ---------------------------------------------------------------
    def _schedule(self, *_args):
        if not self._alive or self._pending is not None:
            return
        with contextlib.suppress(tk.TclError):
            self._pending = self.tree.after_idle(self._redraw)

    def _visible_iids(self, rowheight: int) -> list:
        """iid baris yang terlihat di viewport — probe identify_row tiap
        rowheight (menangani tree hierarki + baris terpotong; area
        heading mengembalikan '' dan diabaikan)."""
        tree = self.tree
        out: list = []
        seen = set()
        try:
            height = tree.winfo_height()
        except tk.TclError:
            return out
        if height <= 1:
            return out
        y = 0
        while y < height:
            try:
                iid = tree.identify_row(y)
            except tk.TclError:
                iid = ""
            if iid and iid not in seen:
                seen.add(iid)
                out.append(iid)
            y += rowheight
        return out

    def _redraw(self):
        self._pending = None
        if not self._alive or not self._by_iid:
            return
        tree = self.tree
        try:
            if not tree.winfo_exists():
                self._alive = False
                return
        except tk.TclError:
            self._alive = False
            return
        # v3.9.40 — style + warna di-CACHE (dulu 4 lookup style +
        # tag_configure per tag per baris di-setiap redraw = puluhan
        # panggilan Tcl ekstra per notch scroll).
        (_style, rowheight, font, field_bg, base_fg, sel_bg, sel_fg) = \
            self._style_ctx()
        visible = self._visible_iids(rowheight)
        if not visible:
            return
        try:
            sel_set = set(tree.selection())
        except tk.TclError:
            sel_set = set()

        tree_width = tree.winfo_width()
        placed = set()
        for iid in visible:
            entries = self._by_iid.get(iid)
            if not entries:
                continue
            # latar/teks baris efektif (tag baris → seleksi) — warna
            # tag-baris per iid di-cache (v3.9.40); seleksi live.
            bg_row, fg_row = self._row_colors(iid, sel_set, sel_bg,
                                               sel_fg, field_bg, base_fg)
            for col, opts in entries:
                try:
                    box = tree.bbox(iid, col)
                except tk.TclError:
                    box = ""
                if not box:
                    continue
                # FIX: bbox mengembalikan koordinat kolom yang BELUM
                # ter-xscroll (x di luar lebar widget — Tk 9 tetap
                # memberi koordinat) → label melayang di luar tree.
                # Sel di luar viewport horizontal dilewati; sel TERPOTONG
                # di tepi kanan dipotong lebarnya (teks terklip — sama
                # perilaku tree yang menggambar sampai tepi widget).
                bx, by, bw, bh = box
                if bx + bw <= 0 or bx >= tree_width:
                    continue
                if bx + bw > tree_width:
                    bw = tree_width - bx
                    box = (bx, by, bw, bh)
                key = (iid, col)
                if col == "#0":
                    try:
                        text = str(tree.item(iid, "text") or "")
                    except tk.TclError:
                        continue
                else:
                    try:
                        text = str(tree.set(iid, col))
                    except tk.TclError:
                        continue
                lab = self._label_for(key)
                anchor = self._col_anchor(col)
                bg = opts.get("background") or bg_row
                fg = opts.get("foreground") or fg_row
                # v3.9.40 — LOMPATI configure bila tak berubah: saat
                # scroll, teks/warna/anchor/font sel identik (hanya posisi
                # y yang bergeser) — configure ulang = invalidasi paint
                # label yang tidak perlu (beban repaint terbesar).
                cfg_key = (text, bg, fg, anchor, font)
                if getattr(lab, "_ov_cfg", None) != cfg_key:
                    lab.configure(
                        text=text, font=font, anchor=anchor,
                        background=bg, foreground=fg)
                    lab._ov_cfg = cfg_key
                xy_key = (bx, by, bw, bh)
                if getattr(lab, "_ov_xy", None) != xy_key:
                    lab.place(x=bx, y=by, width=bw, height=bh)
                    lab._ov_xy = xy_key
                placed.add(key)
        # label sel yang tak lagi terlihat / itemnya hilang → bersihkan
        for key in list(self._labels):
            if key not in placed:
                self._destroy_label(key)
        # v3.9.40 — FLUSH SINKRON: tanpa ini place()/place_forget()
        # baru diproses Tk di idle geometri SETELAH repaint tree → sel
        # warna tertinggal 1 frame (glitch 'berenang' saat scroll).
        self._flush_geometry()

    # -- label pool + penerusan event -----------------------------------------
    def _label_for(self, key):
        lab = self._labels.get(key)
        if lab is None or not lab.winfo_exists():
            # v3.9.29 — ambil dari POOL dulu (reuse, tanpa buat widget
            # baru — pembuatan label saat scroll = pop-in telat 1 frame)
            if self._pool:
                lab = self._pool.pop()
            else:
                lab = tk.Label(self.tree, bd=0, highlightthickness=0,
                               takefocus=0, padx=5, pady=0)
                self._bind_forward(lab)
            self._labels[key] = lab
        return lab

    def _destroy_label(self, key):
        lab = self._labels.pop(key, None)
        if lab is not None:
            with contextlib.suppress(tk.TclError):
                lab.place_forget()
            # v3.9.40 — reset penanda posisi: label di pool akan
            # dipakai ulang utk sel lain — bila xy kebetulan sama, place
            # tidak boleh dilompati (label masih place_forget!).
            lab._ov_xy = None
            # v3.9.29 — kembalikan ke pool (reuse) bila masih hidup;
            # pool penuh → benar-benar destroy.
            try:
                if lab.winfo_exists() and len(self._pool) < self._POOL_MAX:
                    self._pool.append(lab)
                    return
            except tk.TclError:
                pass
            with contextlib.suppress(tk.TclError):
                lab.destroy()

    def _bind_forward(self, lab):
        """Teruskan klik/wheel dari Label ke tree supaya seleksi, binding
        view (✓ checkbox, klik-kanan copy), dan scroll tetap bekerja di
        sel warna.

        - Press direlay via event_generate (when=now): terbukti TIDAK
          menyentuh penghitung klik Tk → tidak pernah memicu double-click
          palsu di sel normal sekitarnya.
        - <Double-1> TIDAK bisa direlay — Tcl menolak modifier Double di
          `event generate`, dan dispatch rekursif press terforward
          mereset penghitung klik Label sehingga sintesis double-click Tk
          tidak terjadi. Solusi: DOUBLE-CLICK DIDETEKSI MANUAL (timer
          400ms ala Tk pada label yang sama) lalu skrip binding
          <Double-1> milik TREE dipanggil langsung lewat
          _fire_tree_bindings (parser skrip wrapper tkinter + skrip kelas
          ttk) — handler popup view menerima event.widget/x/y yang benar.
        """
        tree = self.tree

        def fwd(seq):
            def handler(event, _seq=seq):
                # v3.9.42 — HOTFIX REGRESI v3.9.40 (audit 61-c): objek
                # tkinter.Event SELALU punya field delta/num (berisi
                # string '??' utk event yang tak relevan) → event_generate
                # menolak opsi -num ("bad option") dan -delta utk event
                # Button → TclError ditelan → TIDAK ADA event yang pernah
                # terforward (klik-kanan/drag/wheel MATI di sel warna;
                # hanya <Button-1> press & <Double-1> yang masih jalan
                # karena jalur terpisah). Fix: bangun kw SELEKTIF —
                # state hanya bila int; delta HANYA utk <MouseWheel> dan
                # bila int; num TIDAK PERNAH dikirim (event_generate
                # menurunkan %b dari pola seq itu sendiri).
                try:
                    if _seq in ("<Button-4>", "<Button-5>"):
                        # X11 roda di sel warna: event_generate sintetis
                        # TIDAK bisa men-set %b/num (probe: arah salah) →
                        # gulir LANGSUNG + redraw overlay sinkron (pola
                        # enable_smooth_wheel._on_btn45).
                        try:
                            tree.yview_scroll(
                                -1 if _seq == "<Button-4>" else 1,
                                "units")
                        except tk.TclError:
                            return
                        _redraw_overlay_now(tree)
                        return
                    lx, ly = lab.winfo_x(), lab.winfo_y()
                    kw = {"x": lx + event.x, "y": ly + event.y,
                          "warp": False}
                    # v3.9.40 — modifier & field roda ikut diteruskan
                    # (dulu HILANG: Shift+klik di sel warna tidak bisa
                    # men-extend seleksi — event terforward datang dgn
                    # state kosong). v3.9.42: HANYA nilai VALID yang
                    # dikirim (state int; delta int khusus <MouseWheel>).
                    state = getattr(event, "state", 0)
                    if isinstance(state, int):
                        kw["state"] = state
                    if _seq == "<MouseWheel>":
                        d = getattr(event, "delta", None)
                        if isinstance(d, int):
                            kw["delta"] = d
                    tree.event_generate(_seq, **kw)
                except tk.TclError:
                    pass
            return handler

        for seq in self._FORWARD_SEQS:
            lab.bind(seq, fwd(seq), add="+")

        def press(event):
            now = _time.time()
            is_dbl = (self._dbl_lab is lab
                      and now - self._dbl_t <= 0.4)
            self._dbl_t, self._dbl_lab = now, lab
            try:
                lx, ly = lab.winfo_x(), lab.winfo_y()
                # v3.9.40 — state (modifier Shift/Ctrl) ikut diteruskan
                tree.event_generate(
                    "<Button-1>", x=lx + event.x, y=ly + event.y,
                    warp=False,
                    state=int(getattr(event, "state", 0) or 0))
            except tk.TclError:
                return
            if is_dbl:
                try:
                    _fire_tree_bindings(
                        tree, "<Double-1>", lx + event.x, ly + event.y,
                        state=int(getattr(event, "state", 0) or 0))
                except tk.TclError:
                    pass

        lab.bind("<Button-1>", press, add="+")


def _fire_tree_bindings(tree: ttk.Treeview, seq: str, x: int, y: int,
                        state: int = 0) -> int:
    """Panggil SEMUA binding `seq` milik tree (bindtags: widget, kelas,
    toplevel, all) seolah-olah event terjadi di (x, y) pada tree.

    v3.9.42 — param state (modifier Shift/Ctrl) diteruskan ke %s
    (dulu hard-code "0" → Ctrl/Shift saat double-click sel warna tak
    sampai ke handler).

    Dipakai overlay per-cell utk meneruskan <Double-1> — `event generate`
    Tcl menolak modifier Double/Triple, jadi skrip binding dipanggil
    langsung:
    - skrip wrapper tkinter  'if {"[CMD %# %b ...]" == "break"} break'
      → CMD dipanggil dgn nilai substitusi %-field (event.widget, x, y
      benar — handler python menerima Event lengkap);
    - skrip Tcl polos (mis. kelas ttk 'ttk::treeview::DoubleClick %W %x
      %y') → di-eval dgn substitusi manual.

    Return jumlah skrip yang terpanggil.
    """
    rootw = tree.winfo_toplevel()
    vals = {
        "%W": str(tree), "%x": str(int(x)), "%y": str(int(y)),
        "%X": str(rootw.winfo_rootx() + int(x)),
        "%Y": str(rootw.winfo_rooty() + int(y)),
        "%t": "0", "%T": "6", "%#": "0", "%b": "1",
        "%s": str(int(state)),
        "%w": "0", "%h": "0", "%k": "0", "%f": "0",
        "%A": "", "%E": "", "%K": "", "%N": "", "%D": "",
    }
    fired = 0
    for tag in tree.bindtags():
        try:
            script = str(tree.tk.call("bind", str(tag), seq)).strip()
        except tk.TclError:
            continue
        if not script:
            continue
        for chunk in script.split("\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.startswith('if {"'):
                # skrip wrapper tkinter: if {"[CMD %-fields...]" == "break"} break
                try:
                    inner = chunk[chunk.index('{"') + 2: chunk.rindex(']"')]
                except ValueError:
                    continue
                parts = inner.split()
                if len(parts) < 2:
                    continue
                cmd = parts[0].removeprefix("[")
                args = [vals.get(f, "") for f in parts[1:]]
                with contextlib.suppress(tk.TclError):
                    tree.tk.call(cmd, *args)
                    fired += 1
            else:
                # skrip Tcl polos — substitusi %-field manual lalu eval
                sub = chunk
                for f, v in vals.items():
                    sub = sub.replace(f, v)
                with contextlib.suppress(tk.TclError):
                    tree.tk.eval(sub)
                    fired += 1
    return fired


def _overlay_for_tree(tree: ttk.Treeview) -> CellColorOverlay:
    """Ambil/buat overlay per-cell milik tree (lazy — satu per tree)."""
    ov = getattr(tree, "_cell_color_overlay", None)
    if ov is None or not getattr(ov, "_alive", False):
        ov = CellColorOverlay(tree)
        with contextlib.suppress(AttributeError, tk.TclError):
            tree._cell_color_overlay = ov
    return ov


class HeadingTintOverlay:
    """v3.9.51 — strip warna TIPIS di ATAS heading kolom tertentu
    (user: "Header In_13 atau In_15 diberi warna beda biar aku tau itu
    bukan kolom Stock").

    ttk TIDAK mendukung background per-heading (style global saja) —
    penanda digambar sebagai Label 6px anak tree di y=0 lebar penuh
    kolom (padding heading 8px → teks heading & ikon corong ⧩ TIDAK
    tertutup). SEMUA event di area strip DITERUSKAN ke tree (pola
    forwarding CellColorOverlay v3.9.42 — kw selektif + koordinat
    diterjemahkan) supaya klik-heading (popup filter ⧩), drag tepi
    (resize kolom), klik-kanan (◱ kolom) & roda tetap bekerja.

    Reposisi otomatis: <Configure>, wrap xscrollcommand (heading ikut
    scroll horizontal), <ButtonRelease-1> (selesai resize kolom) +
    refresh() eksplisit dari view (render/sort/clone) & app (zoom —
    _refit_all_tree_columns). Kolom tersembunyi (◱ Kolom) → strip ikut
    hilang (place_forget).
    """

    STRIP_H = 6

    def __init__(self, tree: ttk.Treeview, cols: list, color: str = "#0e7490"):
        self.tree = tree
        self.cols = [str(c) for c in cols]
        self.color = color
        self._labels: dict = {}
        self._alive = True
        # registrasi mandiri (pola CellColorOverlay): handler zoom/refresh
        # menemukan overlay via atribut ini tanpa perlu view menyimpan.
        with contextlib.suppress(AttributeError, tk.TclError):
            tree._heading_tint = self
        tree.bind("<Configure>", lambda e: self.refresh(), add="+")
        tree.bind("<ButtonRelease-1>", lambda e: self.refresh(), add="+")
        tree.bind("<Destroy>", self._on_destroy, add="+")
        self._wrap_scroll("xscrollcommand")
        self.refresh()

    def _on_destroy(self, _event=None):
        self._alive = False
        self._labels = {}

    # -- reposisi ------------------------------------------------------------
    def _wrap_scroll(self, opt: str):
        """Bungkus xscrollcommand tree — heading ikut scroll horizontal
        → strip harus ikut bergeser (pola CellColorOverlay._wrap_scroll)."""
        try:
            orig = str(self.tree.cget(opt))
        except tk.TclError:
            return

        def wrap(first, last, _orig=orig):
            if _orig:
                with contextlib.suppress(tk.TclError):
                    self.tree.tk.call(_orig, first, last)
            self.refresh()

        with contextlib.suppress(tk.TclError):
            self.tree.configure(**{opt: wrap})

    def _label_for(self, col: str) -> tk.Label:
        lab = self._labels.get(col)
        if lab is None or not self._label_ok(lab):
            lab = tk.Label(self.tree, bg=self.color, bd=0,
                           highlightthickness=0, takefocus=0,
                           cursor="arrow")
            self._bind_forward(lab)
            self._labels[col] = lab
        return lab

    @staticmethod
    def _label_ok(lab) -> bool:
        try:
            return bool(lab.winfo_exists())
        except tk.TclError:
            return False

    def refresh(self):
        """Hitung ulang posisi strip dari lebar kolom + offset xview."""
        if not self._alive:
            return
        tree = self.tree
        try:
            if not tree.winfo_exists():
                return
            dcols = _tree_display_columns(tree)
        except tk.TclError:
            return
        x = 0
        pos = {}
        try:
            for c in dcols:
                if c == "#0":
                    x += int(tree.column("#0", "width") or 0)
                else:
                    pos[str(c)] = (x, int(tree.column(c, "width") or 0))
                    x += pos[str(c)][1]
            content_w = x
            frac = tree.xview()[0]
            visible_w = tree.winfo_width()
            offset = frac * max(0, content_w - visible_w)
        except tk.TclError:
            return
        for col in self.cols:
            lab = self._labels.get(col)
            if col not in pos:
                # kolom tersembunyi (displaycolumns) / tak ada → hilangkan
                if lab is not None and self._label_ok(lab):
                    with contextlib.suppress(tk.TclError):
                        lab.place_forget()
                continue
            lab = self._label_for(col)
            cx, cw = pos[col]
            with contextlib.suppress(tk.TclError):
                lab.place(x=int(cx - offset), y=0, width=max(1, cw),
                          height=self.STRIP_H)

    # -- forwarding event (pola CellColorOverlay) ---------------------------
    def _bind_forward(self, lab: tk.Label):
        tree = self.tree

        def fwd(seq):
            def handler(event, _seq=seq):
                try:
                    if _seq in ("<Button-4>", "<Button-5>"):
                        # X11 roda: event_generate sintetis tak bisa men-set
                        # %b → gulir LANGSUNG (pola enable_smooth_wheel).
                        try:
                            tree.yview_scroll(
                                -1 if _seq == "<Button-4>" else 1, "units")
                        except tk.TclError:
                            return
                        return
                    lx, ly = lab.winfo_x(), lab.winfo_y()
                    kw = {"x": lx + event.x, "y": ly + event.y,
                          "warp": False}
                    state = getattr(event, "state", 0)
                    if isinstance(state, int):
                        kw["state"] = state
                    if _seq == "<MouseWheel>":
                        d = getattr(event, "delta", None)
                        if isinstance(d, int):
                            kw["delta"] = d
                    tree.event_generate(_seq, **kw)
                except tk.TclError:
                    pass
            return handler

        for seq in ("<Button-3>", "<ButtonRelease-1>", "<B1-Motion>",
                    "<MouseWheel>", "<Button-4>", "<Button-5>"):
            lab.bind(seq, fwd(seq), add="+")

        def press(event):
            try:
                lx, ly = lab.winfo_x(), lab.winfo_y()
                tree.event_generate(
                    "<Button-1>", x=lx + event.x, y=ly + event.y,
                    warp=False,
                    state=int(getattr(event, "state", 0) or 0))
            except tk.TclError:
                return

        lab.bind("<Button-1>", press, add="+")


# v3.9.55 — RankMergeOverlay DIHAPUS (merge-vertikal kini NATIVE:
# nilai per-baris langsung di payload deviasi_view sejak v3.9.60 —
# tanpa widget LABEL di atas tree, bebas glitch scroll & mencakup kolom
# Nama Barang + Rank; v3.9.61 band kelompok ikut dihapus — baris seragam).
# Riwayat desain overlay lama lihat v3.9.52.


def _collect_iids(tree, parent="") -> set:
    """Kumpulkan SEMUA iid tree (parent + anak — mendukung hierarki 2
    level ala pivot). Dipakai fallback apply_cell_tag."""
    out = set()
    try:
        kids = tree.get_children(parent)
    except tk.TclError:
        return out
    for k in kids:
        out.add(str(k))
        out |= _collect_iids(tree, k)
    return out


def apply_cell_tag(tree: ttk.Treeview, tag: str, cells: list,
                   chunk: int = 3000) -> int:
    """Pasang TAG per-CELL ke daftar sel [(iid, column_id), ...]
    (native Tk 9 / overlay Label Tk 8.6).

    - Dikirim per-chunk supaya list Tcl tidak terlalu besar.
    - Item yang sudah tidak ada (re-render/filter terjadi di tengah
      jalan) → v3.9.5: chunk di-fallback ke pemasangan utk iid yang MASIH
      ADA (dulu SATU item hilang membatalkan SELURUH chunk — mis. clone ⛶
      yang difilter hanya memuat sebagian baris → semua tag gagal).
    - Tk 8.6 (v3.9.22): via OVERLAY Label (`CellColorOverlay`) — sel
      warna ditimpa Label ber-teks identik (alternatif fallback
      tag-per-baris; permintaan user "coba cari alternatif lain").
      Semantik replace per tag: panggil ulang dgn daftar lengkap tiap
      reapply (pola yang sudah dipakai semua view).
    - FIX 6b-03 (audit 6-b): jalur NATIVE Tk 9 kini juga REPLACE (dulu
      ADDITIF + list kosong = no-op — semantik 'replace'/'clear' yang
      didokumentasikan view hanya benar di jalur overlay Tk 8). Sel yang
      SEBELUMNYA ditandai lewat fungsi ini utk tag yang sama tapi TIDAK
      ada di daftar baru, dilepas via ``tag cell remove``; list kosong =
      bersihkan semua anggota tag (mirror ``_cellsel_apply_cells``).
      Perilaku Tk 8 & Tk 9 kini seragam. Pelacakan internal disimpan di
      ``tree._cell_tags_applied`` (map tag → set sel) — murni internal,
      API publik tidak berubah.
    Return jumlah cell yang berhasil ditandai.
    """
    if not CELL_TAGS_NATIVE:
        # v3.9.22 — Tk 8.6: OVERLAY Label per sel (alternatif fallback
        # tag-baris; list kosong = bersihkan anggota tag — replace).
        try:
            _overlay_for_tree(tree).set_cells(tag, list(cells or []))
            return len(cells or [])
        except tk.TclError:
            return 0
    cells = list(cells or [])
    path = str(tree)
    new_set = {(str(iid), str(col)) for iid, col in cells}
    # FIX 6b-03: pelacakan sel yang pernah dipasang per (tree, tag) —
    # atribut internal polos (pola _row_filter_cache/_last_sort).
    applied_map = getattr(tree, "_cell_tags_applied", None)
    if applied_map is None:
        applied_map = {}
        tree._cell_tags_applied = applied_map
    old = applied_map.get(tag) or set()
    if not cells:
        # FIX 6b-03: list kosong = CLEAR (semantik yang didokumentasikan
        # semua view sejak v3.9.42/audit 61-c P1-2 — hanya Tk 8 yang
        # sebelumnya benar-benar melakukannya).
        if old:
            _remove_cell_tag(tree, tag, old)
            applied_map[tag] = set()
        return 0
    # FIX 6b-03: lepas anggota LAMA yang tidak ada di daftar baru
    # (semantik replace) — remove cellList; bila ada iid yang sudah
    # dihapus user, seluruh remove gagal ("Item not found") → fallback
    # remove TANPA cellList (lepas semua anggota) lalu daftar baru
    # dipasang ulang penuh di bawah (hasil akhir ekuivalen).
    stale = old - new_set
    if stale:
        _remove_cell_tag(tree, tag, stale)
    applied = 0
    for i in range(0, len(cells), chunk):
        part = cells[i:i + chunk]
        spec = tuple((str(iid), str(col)) for iid, col in part)
        try:
            tree.tk.call(path, "tag", "cell", "add", tag, spec)
            applied += len(part)
            continue
        except tk.TclError:
            pass
        # fallback: sebagian iid sudah tidak ada (clone terfilter /
        # re-render di tengah jalan) — pasang hanya utk yang masih ada
        existing = _collect_iids(tree)
        part2 = [(iid, col) for iid, col in part if str(iid) in existing]
        if not part2:
            continue
        spec2 = tuple((str(iid), str(col)) for iid, col in part2)
        with contextlib.suppress(tk.TclError):
            tree.tk.call(path, "tag", "cell", "add", tag, spec2)
            applied += len(part2)
    applied_map[tag] = set(new_set)
    return applied


def _remove_cell_tag(tree: ttk.Treeview, tag: str, cells) -> None:
    """FIX 6b-03 (audit 6-b) — lepas tag dari sel (Tk 9 ``tag cell
    remove``). ``cells`` iterable {(iid, col), ...}; bila salah satu iid
    sudah tidak ada, TclError "Item not found" membatalkan seluruh
    panggilan → fallback remove TANPA cellList (lepas SEMUA anggota tag —
    pemanggil selalu memasang ulang daftar lengkap sesudahnya, jadi hasil
    akhir tetap benar). Best-effort: error ditelan."""
    path = str(tree)
    spec = tuple((str(iid), str(col)) for iid, col in cells)
    try:
        tree.tk.call(path, "tag", "cell", "remove", tag, spec)
        return
    except tk.TclError:
        pass
    with contextlib.suppress(tk.TclError):
        tree.tk.call(path, "tag", "cell", "remove", tag)


# --- Sort engine linear (v3.3) ------------------------------------------------

def sort_tree_by_column(tree: ttk.Treeview, col: str, reverse: bool = True,
                        parse=None, value_get=None) -> None:
    """Sort baris top-level tree berdasarkan kolom — WAKTU LINEAR (v3.3).

    Versi lama (v3.0-v3.2): ``tree.move(k, "", i)`` per baris → O(n²)
    internal Tk — klik judul kolom di Laporan Deviasi (50k baris)
    MEMBEKANKAN UI sampai 45 detik.

    Versi baru: 1x ``tree.item()`` per baris (snapshot values+tags) →
    ``delete`` semua → insert ulang berurutan di posisi 'end' (append
    cepat) → O(n). Benchmark @50k baris: 45.1s → 1.1s (42×).

    iid dipertahankan → pemetaan iid→fingerprint (_fp_map) dan toggle
    kolom ✓ tetap mengenai baris yang benar setelah sort.

    v3.9.55 — ``value_get(iid)``: override sumber nilai sort per baris
    (deviasi_view memakainya utk kolom MERGE-VERTIKAL Nama Barang/Rank —
    nilai tree baris lanjutan blank; kunci sort = nilai RAW snapshot).
    """
    # FIX B-14 (audit 2-b): catat sort TERAKHIR di tree — apply_tree_row_
    # filters (rebuild clone pasca toggle filter) menjalankan ulang sort
    # ini SEBELUM reapply tag per-cell, supaya toggle filter tidak
    # mengembalikan urutan ke urutan asli cache secara diam-diam.
    try:
        tree._last_sort = (col, bool(reverse), parse, value_get)
    except Exception:
        pass
    children = list(tree.get_children(""))
    if len(children) < 2:
        return
    try:
        col_idx = list(tree["columns"]).index(col)
    except (ValueError, tk.TclError):
        col_idx = -1

    info = {}
    keys = []
    for k in children:
        it = tree.item(k)
        info[k] = it
        if value_get is not None:
            # v3.9.55 — nilai sort dari sumber RAW (merge-vertikal).
            raw = value_get(k)
        else:
            vals = it.get("values") or []
            raw = vals[col_idx] if 0 <= col_idx < len(vals) else ""
        keys.append((raw, k))

    if parse is None:
        def parse(s):
            # v3.9.51: prefiks 'Rp ' (fmt_rp_cell) ikut dibuang supaya
            # kolom Nominal terurut numerik tanpa parser khusus per view.
            # v3.9.54 FIX (audit 8-b — default parser Rp-aware SETENGAH):
            # '.' pemisah RIBUAN Indonesia belum dibuang → 'Rp 1.825'
            # ter-parse 1.825 (skala salah 1000×) & 'Rp 1.825.567' ValueError
            # (kolom utuh jatuh ke fallback string). Kini mirror _parse_num_id
            # view ('1.825' → 1825 · '12,5' → 12.5 · '(Rp 500)' → -500 ·
            # '—'/'-' → 0). Non-numerik murni TETAP raise → fallback string
            # sort (perilaku lama utk kolom teks).
            s = str(s).replace("%", "").replace("—", "") \
                .replace("Rp", "").strip()
            if s in ("-", ""):
                return 0
            neg = s.startswith("(") and s.endswith(")")
            if neg:
                s = s[1:-1].strip()
            s = s.replace(".", "").replace(",", ".")
            v = float(s)
            return -v if neg else v
    try:
        keys.sort(key=lambda x: parse(x[0]), reverse=reverse)
    except (ValueError, TypeError):
        # v3.9.62 — fallback NATURAL (referensi tksheet): "Barang 2" <
        # "Barang 10" (dulu leksikografis terbalik di semua kolom teks
        # yang menyembunyikan angka — Nama Barang/Nomor PO/kode).
        keys.sort(key=lambda x: natural_key(str(x[0])), reverse=reverse)

    order = [k for _, k in keys]
    # FIX B-21 (audit 2-b): indikator ARAH sort di heading kolom — sebelumnya
    # tidak ada tanda kolom mana yang sedang terurut (setelah sort via popup
    # ↕, tabel berubah urutan tanpa jejak). Panah lama di kolom lain dibersihkan.
    _set_sort_arrow(tree, col, reverse)
    if order == children:
        return
    try:
        sel = set(tree.selection())
    except tk.TclError:
        sel = set()

    # FIX B-09 (audit 2-b): tree BERHIRARKI → tree.move per baris top-level
    # (subtree anak, text #0, dan state open IKUT TERJAGA — jalur lama
    # delete+reinsert hanya values+tags sehingga ANAK-ANAK HILANG).
    # Latent untuk caller saat ini (semuanya datar), tapi menutup jalur
    # rusak untuk tabel 2-level (mis. matrix pivot) di masa depan.
    # Tabel datar tetap memakai jalur O(n) delete+reinsert (benchmark
    # v3.3 45.1s → 1.1s @50k baris) — kini juga mempertahankan text #0
    # dan state open.
    if any(tree.get_children(k) for k in children):
        for i, k in enumerate(order):
            try:
                tree.move(k, "", i)
            except tk.TclError:
                pass
        return

    tree.delete(*children)
    for k in order:
        it = info[k]
        tree.insert("", "end", iid=k, text=it.get("text", ""),
                    values=it.get("values"), open=it.get("open", False),
                    tags=tuple(it.get("tags") or ()))
    keep = [k for k in order if k in sel]
    if keep:
        try:
            tree.selection_set(keep)
        except tk.TclError:
            pass


def _set_sort_arrow(tree: ttk.Treeview, col: str, descending: bool) -> None:
    """FIX B-21 (audit 2-b): panah arah sort di heading — ↓ menurun,
    ↑ menaik; panah lama di kolom LAIN dibersihkan.

    Hanya opsi ``text`` heading yang ditulis (ikon funnel HeaderFilter
    hidup di opsi ``image`` — tidak tersentuh). Heading yang tidak
    berubah teksnya tidak dikonfigurasi ulang sama sekali.
    """
    marks = _SORT_ARROW_MARKS   # FIX 6b-02 — konstanta bersama " ↓"/" ↑"
    try:
        cols = [str(c) for c in tree["columns"]]
    except tk.TclError:
        return
    for c in cols:
        try:
            cur = str(tree.heading(c, "text") or "")
        except tk.TclError:
            continue
        txt = cur
        for m in marks:
            if txt.endswith(m):
                txt = txt[: -len(m)]
                break
        if c == col:
            txt = txt + (marks[0] if descending else marks[1])
        if txt != cur:
            with contextlib.suppress(tk.TclError):
                tree.heading(c, text=txt)


# --- Column resize + auto-fit (v3.4) -------------------------------------------

def display_data_columns(tree: ttk.Treeview) -> list[str]:
    """Kolom DATA yang tampil (urutan display) — menghormati displaycolumns
    (v3.6: kolom bisa disembunyikan oleh ColumnManager)."""
    try:
        dc = tree.cget("displaycolumns")
        items = [str(x) for x in dc] if isinstance(dc, (tuple, list)) \
            else str(dc).split()
    except Exception:
        items = []
    if not items or "#all" in items:
        try:
            return [str(c) for c in tree["columns"]]
        except Exception:
            return []
    try:
        cols = list(tree["columns"])
    except Exception:
        return []
    return [c for c in items if c != "#0" and c in cols]


def identify_to_column(tree: ttk.Treeview, identified: str):
    """'#N' hasil identify_column() → nama kolom AKTUAL (v3.6).

    BUG FIX v3.6: identify_column() mengembalikan ID POSISIONAL ('#2')
    sesuai URUTAN TAMPILAN — sedangkan HeaderFilter memakai nama kolom
    simbolik ('Nama Barang') → klik funnel TIDAK PERNAH membuka popup
    dengan mouse sungguhan (hanya via pemanggilan programatik). Tk juga
    me-reindex saat kolom disembunyikan (displaycolumns).
    """
    if not identified or not str(identified).startswith("#"):
        return None
    try:
        n = int(str(identified)[1:])
    except ValueError:
        return None
    if n == 0:
        return "#0"
    disp = display_data_columns(tree)
    if 1 <= n <= len(disp):
        return disp[n - 1]
    return None


def _tree_display_columns(tree: ttk.Treeview) -> list[str]:
    """Kolom yang tampil (urutan layout): ['#0' bila show tree] + kolom
    data yang TAMPIL (displaycolumns-aware — v3.6)."""
    try:
        raw = tree.cget("show")
        parts = " ".join(str(x) for x in raw) if isinstance(raw, (tuple, list)) \
            else str(raw)
    except Exception:
        parts = "headings"
    cols = []
    if "tree" in parts:
        cols.append("#0")
    cols += display_data_columns(tree)
    return cols


def _tree_content_x(tree: ttk.Treeview, event_x: int) -> float:
    """Konversi x event (relatif widget) → koordinat konten kolom
    (memperhitungkan scroll horizontal)."""
    try:
        frac = tree.xview()[0]
        content_w = sum(tree.column(c, "width")
                        for c in _tree_display_columns(tree))
        visible_w = tree.winfo_width()
        offset = frac * max(0, content_w - visible_w)
    except Exception:
        offset = 0
    return event_x + offset


def _redraw_overlay_now(tree: ttk.Treeview) -> None:
    """v3.9.40 — redraw overlay + flush SEKARANG, dari DALAM handler
    roda (sebelum Tk sempat me-repaint tree).

    Temuan probe: callback ``yscrollcommand`` (wrap) baru dipanggil Tk
    di IDLE — bukan saat ``yview_scroll`` dieksekusi — sehingga redraw
    label dari dalam wrap SELALU ketinggalan repaint tree (glitch 'sel
    warna berenang'). Dengan memanggil redraw langsung dari handler
    roda SETELAH ``yview_scroll``: offset tree sudah ter-update (bbox
    valid saat itu juga) → label dipindah + ``update_idletasks``
    memproses repaint tree DAN pergeseran label dalam SATU burst
    sinkron — frame layar tidak pernah menampilkan baris baru dgn label
    lama. Tree tanpa overlay (Tk 9 native / tanpa sel warna) → no-op.
    v3.9.55 — strip header kolom In (HeadingTintOverlay) ikut
    di-refresh (scroll horizontal — scrollbar h / Shift+roda).
    """
    ov = getattr(tree, "_cell_color_overlay", None)
    if ov is not None and getattr(ov, "_alive", False):
        with contextlib.suppress(tk.TclError):
            ov._redraw()
    tint = getattr(tree, "_heading_tint", None)
    if tint is not None and getattr(tint, "_alive", False):
        with contextlib.suppress(tk.TclError):
            tint.refresh()
    # v3.9.56 — STICKY MERGE (deviasi_view): nilai Nama Barang/Rank per
    # kelompok berpindah mengikuti viewport (head tak terlihat → baris
    # pertama yang terlihat). Hook di sini = jalur SINKRON saat scroll
    # (roda/drag scrollbar/keyboard — semua memanggil fungsi ini);
    # wrap yscrollcommand di view menangkap sumber sisanya (idle).
    # Idempoten — tanpa merge state (tree non-deviasi) = no-op.
    _sticky = getattr(tree, "_sticky_merge_cb", None)
    if _sticky is not None:
        with contextlib.suppress(Exception):
            _sticky()


# v3.9.55 — bindtag BERSAMA utk sinkron overlay pasca keyboard-scroll
# (binding didaftarkan SEKALI per interpreter; handler membaca
# event.widget → tree mana pun yang menggulir via keyboard ikut sinkron;
# tidak ada kebocoran binding per-popup — tag dipakai bersama).
_OVSCROLL_SYNC_TAG = "OvScrollSync"
_OVSCROLL_SYNC_BOUND = False
_OVSCROLL_KEY_SEQS = ("<Up>", "<Down>", "<Prior>", "<Next>",
                      "<Home>", "<End>")


def _bind_ovscroll_sync_tag(tree: ttk.Treeview) -> None:
    """Daftarkan binding keyboard di bindtag bersama _OVSCROLL_SYNC_TAG
    (registrasi bind_class GLOBAL — cukup sekali; handler membaca
    event.widget). Binding dijalankan SETELAH binding kelas Treeview
    (urutan bindtags) → binding kelas telah menggulir tree saat handler
    kita jalan → redraw overlay sinkron (pola handler roda v3.9.40)."""
    global _OVSCROLL_SYNC_BOUND
    if _OVSCROLL_SYNC_BOUND:
        return
    _OVSCROLL_SYNC_BOUND = True

    def _after_key(event):
        with contextlib.suppress(tk.TclError):
            _redraw_overlay_now(event.widget)

    for seq in _OVSCROLL_KEY_SEQS:
        with contextlib.suppress(tk.TclError):
            tree.bind_class(_OVSCROLL_SYNC_TAG, seq, _after_key, add="+")


def sync_tree_scroll_overlays(tree: ttk.Treeview) -> None:
    """v3.9.55 — ANTI-GLITCH SCROLL SINKRON (user: "Waktu scroll kok banyak
    glitch ya di program nya?").

    Dua celah lag yang TERSISA setelah fix roda v3.9.29/40 (probe
    v3.9.55: ``tree.yview_moveto`` TIDAK memanggil command scrollbar /
    yscrollcommand secara sinkron — callback baru jalan di idle):
    1. DRAG SCROLLBAR: thumb digeser → command scrollbar → tree.yview
       moveto → tree menggulir & MENGGAMBAR, tapi redraw label overlay
       menunggu idle → label 'berenang' 1 frame di posisi lama.
       FIX: command scrollbar (vsb & hsb saudara tree — frame induk
       sama) DIWRAP: panggil command asli LALU redraw overlay SEKARANG
       (pola _redraw_overlay_now handler roda).
    2. KEYBOARD (Up/Down/PageUp/PageDown/Home/End): binding kelas
       Treeview menggulir TANPA melewati handler roda → lag yang sama.
       FIX: bindtag bersama _OVSCROLL_SYNC_TAG disisipkan SETELAH tag
       kelas di bindtags tree → binding kita jalan SETELAH scroll kelas
       selesai → redraw sinkron.

    Idempoten (flag per scrollbar / bindtag). Dipasang dari
    enable_col_resize (choke-point SEMUA tree termasuk popup & clone ⛶)
    + re-scan after_idle (scrollbar kadang dibuat SETELAH enable_col_
    resize — pola view lama)."""
    # (1) wrap scrollbar command
    try:
        sbs = [w for w in tree.master.winfo_children()
               if isinstance(w, ttk.Scrollbar)]
    except (tk.TclError, AttributeError):
        sbs = []
    for sb in sbs:
        if getattr(sb, "_ov_sync_bound", False):
            continue
        try:
            orig = str(sb.cget("command"))
        except tk.TclError:
            continue
        if not orig or orig == "":
            continue
        sb._ov_sync_bound = True

        def _cmd(*args, _orig=orig, _tree=tree):
            with contextlib.suppress(tk.TclError):
                _tree.tk.call(_orig, *args)
            # redraw SEKARANG — sebelum repaint idle (anti-glitch)
            _redraw_overlay_now(_tree)

        with contextlib.suppress(tk.TclError):
            sb.configure(command=_cmd)
    # (2) bindtag keyboard sync
    try:
        bts = list(tree.bindtags())
    except tk.TclError:
        bts = []
    if bts and _OVSCROLL_SYNC_TAG not in bts:
        try:
            cls_idx = bts.index("Treeview")
        except ValueError:
            cls_idx = 0
        bts.insert(cls_idx + 1, _OVSCROLL_SYNC_TAG)
        with contextlib.suppress(tk.TclError):
            tree.bindtags(bts)
    _bind_ovscroll_sync_tag(tree)
    # re-scan SEKALI di idle (scrollbar kadang dibuat SETELAH
    # enable_col_resize — flag cegah loop after_idle berulang).
    if not getattr(tree, "_ovsync_rescan", False):
        tree._ovsync_rescan = True

        def _rescan():
            with contextlib.suppress(Exception):
                if tree.winfo_exists():
                    sync_tree_scroll_overlays(tree)
        with contextlib.suppress(Exception):
            tree.after_idle(_rescan)


def enable_smooth_wheel(tree: ttk.Treeview, *, units_per_notch: float = 1.0):
    """v3.9.29 — SCROLL RODA HALUS (user: "perbaiki animasi scroll seperti
    tidak smooth dan patah patah").

    Akar patah-patah pada binding default Tk:
    1. Binding kelas ttk::treeview menggulir 3 BARIS per notch roda —
       lompatan besar terlihat kasar. Kini 1 baris per notch (3× lebih
       halus) dengan AKUMULATOR delta pecahan: roda/trackpad resolusi
       tinggi (delta < 120 per event, mis. trackpad macOS) dijumlahkan
       dulu — tanpa akumulator delta kecil dibulatkan 0 = tidak pernah
       menggulir (perilaku lama di beberapa tempat memakai trik
       `or -1` yang justru memaksa 1 baris per event kecil).
    2. (Tk 8.6 + overlay per-cell) label warna tertinggal 1 frame di
       posisi lama saat scroll → label 'melayang' di atas baris salah
       (tearing). Diperbaiki di CellColorOverlay (label pool + reposisi
       sinkron di _wrap_scroll).

    `return "break"` pada binding WIDGET mematikan binding kelas default
    supaya tidak menggulir DOBEL (default 3 baris + binding ini).
    Idempoten (flag `_smooth_wheel_bound`) — dipanggil dari
    enable_col_resize yang dipasang sekali per tree (termasuk clone ⛶).

    v3.9.40 — (a) RESET AKUMULATOR saat ARAH RODA BERBALIK: sisa ≤0.5
    baris arah lama dulu ikut tercampur → notch pertama arah baru bisa
    'dimakan' sisa (terasa macet sesaat); (b) sisanya ada di
    CellColorOverlay._flush_geometry (geometri label diproses SINKRON —
    probe Xvfb menunjukkan place() deferred ke idle = sel warna
    tertinggal 1 frame, akar 'glitch' yang dilaporkan user)."""
    if getattr(tree, "_smooth_wheel_bound", False):
        return
    tree._smooth_wheel_bound = True

    def _on_wheel(event):
        d = getattr(event, "delta", 0) or 0
        if d == 0:
            return None
        acc = getattr(tree, "_smooth_wheel_acc", 0.0)
        # v3.9.40 — ganti arah: buang sisa akumulator ARAH LAMA (tanpa
        # ini sisa +0.75 baris 'memakan' notch arah baru → respons
        # balik arah tertunda). Tanda KONTRIBUSI = -d (roda ke bawah
        # d<0 → kontribusi +): reset saat tanda kontribusi ≠ tanda akumulator
        # ⇔ (d > 0) == (acc > 0).
        if acc and ((d > 0) == (acc > 0)):
            acc = 0.0
        acc += (-d / 120.0) * units_per_notch
        steps = int(acc)              # potong menuju nol; sisa diakumulasi
        tree._smooth_wheel_acc = acc - steps
        if steps:
            try:
                tree.yview_scroll(steps, "units")
            except tk.TclError:
                pass
            # v3.9.40 — redraw overlay SEKARANG (sebelum repaint tree
            # di idle — probe: wrap/yscrollcommand baru jalan di idle,
            # terlambat utk mencegah label tertinggal 1 frame)
            _redraw_overlay_now(tree)
        return "break"

    def _on_btn_up(event):
        try:
            tree.yview_scroll(-1, "units")
        except tk.TclError:
            return
        _redraw_overlay_now(tree)
        return "break"

    def _on_btn_down(event):
        try:
            tree.yview_scroll(1, "units")
        except tk.TclError:
            return
        _redraw_overlay_now(tree)
        return "break"

    tree.bind("<MouseWheel>", _on_wheel, add="+")
    # v3.9.57 — X11 roda: arah dibawa POLA BINDING (2 handler terpisah),
    # BUKAN event.num: event_generate sintetis tak bisa men-set %b/num
    # (Tk 9 memetakan <Button-4/5> ke tombol fisik 8/9 — probe v3.9.40
    # overlay sudah membuktikan arah-num sintetis salah).
    tree.bind("<Button-4>", _on_btn_up, add="+")
    tree.bind("<Button-5>", _on_btn_down, add="+")
    # v3.9.48 — CTRL+Scroll = ZOOM UI (user): pola <Control-MouseWheel>/
    # <Control-Button-4/5> LEBIH SPESIFIK daripada binding <MouseWheel>
    # polos di atas (bindtag widget yang sama) → menurut aturan Tk,
    # CTRL+roda masuk dispatch zoom TANPA menggulir tabel; roda polos
    # tetap scroll halus. Choke-point ini terpasang di SEMUA tree
    # (enable_col_resize — termasuk clone ⤢ dan popup).
    bind_ctrl_zoom(tree)


def enable_smooth_wheel_list(cv: tk.Canvas, *,
                             container: tk.Misc | None = None,
                             units_per_notch: float = 1.0) -> None:
    """v3.9.57 — roda HALUS untuk DAFTAR NILAI ber-canvas (popup filter
    HeaderFilter & panel kolom ColumnManager) — padanan
    enable_smooth_wheel untuk Canvas, BUKAN ttk.Treeview.

    Audit (item "scroll daftar nilai filter belum menangani roda
    beresolusi tinggi") menemukan TIGA akar sekaligus:
    1. Binding lama membagi delta LANGSUNG: ``e.delta // 120`` —
       roda/trackpad resolusi tinggi (delta < 120 per event, mis.
       touchpad Precision Windows / trackpad macOS) dibulatkan ke
       NOL pada SETIAP event → daftar TIDAK PERNAH bergulir; varian
       panel kolom memakai trik ``int(-e.delta / 120) or -1`` yang
       justru memaksa 1 unit penuh per event kecil (terlalu cepat).
       FIX: AKUMULATOR delta pecahan (pola enable_smooth_wheel
       v3.9.29): kontribusi ``-delta/120`` dijumlahkan, ``int(acc)``
       digulir, sisa diakumulasi.
    2. Binding lama HANYA di canvas — (a) Windows/Tk 8.6 mengirim
       wheel ke widget FOKUS (popup memfokuskan ENTRY pencarian →
       binding canvas tak pernah terpanggil dari sana); (b) X11
       memakai <Button-4/5> yang tak di-bind sama sekali (roda polos
       di Linux hanya jalan via drag scrollbar). FIX: binding juga
       di Toplevel popup (``container``) — bindtag Toplevel ada di
       rantai SEMUA anak (entry/checkbox/label/scrollbar) → wheel di
       anak mana pun tetap menggulir daftar; event yang jatuh ke
       canvas sendiri berhenti di 'break' binding canvas (tidak
       dobel-gulir).
    3. CTRL+Scroll = ZOOM UI (v3.9.48) tetap tak terganggu: handler
       polos MELEWATKAN event bergaya Control (bit 0x4) tanpa
       'break' → berlanjut ke bindtag 'all' (bind_all app); di atas
       canvas, pola <Control-MouseWheel>/<Control-Button-4/5>
       (bind_ctrl_zoom) lebih spesifik dan menang duluan.

    Idempoten (flag ``_smooth_list_wheel_bound``)."""
    if getattr(cv, "_smooth_list_wheel_bound", False):
        return
    cv._smooth_list_wheel_bound = True

    _ctrl = 0x0004   # bit modifier Control (<MouseWheel> & X11 Button-4/5)

    def _on_wheel(event):
        state = getattr(event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None          # → bindtag 'all' (fallback zoom app)
        d = getattr(event, "delta", 0) or 0
        if d == 0:
            return None
        acc = getattr(cv, "_smooth_list_wheel_acc", 0.0)
        # ganti arah: buang sisa akumulator ARAH LAMA (v3.9.40 — tanpa
        # ini sisa arah lama 'memakan' notch pertama arah baru → respons
        # balik arah tertunda/terasa macet)
        if acc and ((d > 0) == (acc > 0)):
            acc = 0.0
        acc += (-d / 120.0) * units_per_notch
        steps = int(acc)         # potong menuju nol; sisa diakumulasi
        cv._smooth_list_wheel_acc = acc - steps
        if steps:
            try:
                cv.yview_scroll(steps, "units")
            except tk.TclError:
                pass
        return "break"

    # X11: arah DIBAWA POLA BINDING (bukan event.num — event_generate
    # sintetis tidak bisa men-set %b/num: Tk 9 memetakan <Button-4/5>
    # ke tombol fisik 8/9; probe v3.9.40 di overlay sudah membuktikan
    # arah-num sintetis salah) → 2 handler terpisah per sekuens.
    def _on_btn_up(_event):
        state = getattr(_event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None
        try:
            cv.yview_scroll(-1, "units")
        except tk.TclError:
            pass
        return "break"

    def _on_btn_down(_event):
        state = getattr(_event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None
        try:
            cv.yview_scroll(1, "units")
        except tk.TclError:
            pass
        return "break"

    cv.bind("<MouseWheel>", _on_wheel)
    cv.bind("<Button-4>", _on_btn_up)
    cv.bind("<Button-5>", _on_btn_down)
    if container is not None:
        container.bind("<MouseWheel>", _on_wheel)
        container.bind("<Button-4>", _on_btn_up)
        container.bind("<Button-5>", _on_btn_down)
    # v3.9.48 — CTRL+Scroll = ZOOM UI: pola Control-* lebih spesifik di
    # bindtag canvas (menang duluan atas <MouseWheel>/<Button-4/5> polos)
    # + handler polos di atas melewatkan event bergaya Control ke
    # fallback 'all' (jalur zoom utk wheel yang jatuh di anak popup).
    bind_ctrl_zoom(cv)


def install_wheel_router(top: tk.Misc, *,
                         get_primary_scrollable=None) -> None:
    """v3.9.61 — ROUTER RODA SERAKAT-AREA (user: "tab rekap selisih in
    aku masih tidak bisa scroll pakai wheele mouse").

    AKAR MASALAH (diagnosis v3.9.61, terpasang setelah fix viewport
    v3.9.60): roda hanya bergulir bila event jatuh PERSIS di widget yang
    punya binding roda (tree enable_smooth_wheel / canvas
    enable_smooth_wheel_list). Binding Tk TIDAK BUBBLE dari induk ke
    anak — bindtag anak = [anak, kelas, TOPLEVEL, all] — jadi:

    1. BARIS leaderboard rekap = Label di dalam frame inner canvas →
       pointer di atas baris (±90% area papan skor) → TIDAK ada binding
       yang terpanggil → roda MATI. (v3.9.60 mem-bind canvas + listwrap
       frame — dua area celah saja.)
    2. Area krom non-scrollable (kartu KPI · kartu Filter · footer ·
       legend · baris "+N resto") → roda MATI di SEMUA tab.
    3. Windows/Tk tertentu mengirim wheel ke widget FOKUS — pointer di
       atas tabel tapi fokus di Entry/Aplikasi → roda MATI walau tabel
       sehat.

    SOLUSI: SATU binding di TOPLEVEL utama — bindtag Toplevel ada di
    rantai SEMUA anak jendela, DAN berjalan SETELAH binding widget/kelas
    (yang konsumsi roda dengan "break" — tree/canvas smooth-wheel —
    tidak terganggu, tak ada gulir dobel). Router menggulir scrollable
    DI BAWAH POINTER (bukan widget penerima event — bereset masalah
    fokus #3): jalur master dari widget-bawah-pointer dicari naik
    sampai ketemu ttk.Treeview ATAU tk.Canvas ber-yscrollcommand
    (canvas dekoratif tanpa scrollbar dilewati). Bila tak ada
    scrollable di bawah pointer (area krom #2), fallback
    ``get_primary_scrollable()`` — tabel utama TAB AKTIF (perilaku
    standar aplikasi modern: roda di area kosong menggulir konten tab).

    Detail aman:
    - CTRL+roda diteruskan (return None → bindtag 'all' → zoom UI
      v3.9.48 — jangan dicampur gulir).
    - Widget-bawah-pointer di TOPLEVEL LAIN (popup filter / clone ⛶ /
      detail) → diabaikan (jendela itu punya mesin roda sendiri).
    - Akumulator delta pecahan PER TARGET (pola v3.9.40: berbalik arah
      → sisa arah lama dibuang) — trackpad resolusi tinggi tetap halus.
    - Treeview → 1 baris per notch + redraw overlay warna sel SEKARANG
      (pola _redraw_overlay_now — label overlay tak tertinggal 1 frame).
    - Canvas → "units" = yscrollincrement (leaderboard rekap v3.9.61
      men-set-nya = tinggi baris aktual → 1 baris per notch; canvas
      lain unit = 1/10 tinggi jendela — perilaku bawaan Tk).
    - Idempoten (flag ``_wheel_router_bound`` di Toplevel)."""
    if getattr(top, "_wheel_router_bound", False):
        return
    top._wheel_router_bound = True

    _ctrl = 0x0004   # bit modifier Control (<MouseWheel> & X11 Button-4/5)

    def _scrollable_under(px, py):
        try:
            w = top.winfo_containing(px, py)
        except tk.TclError:
            return None
        if w is None:
            return None
        # hanya area jendela INI — popup/clone punya Toplevel sendiri
        # (mesin roda + grab mereka sendiri; jangan digulir dari luar)
        try:
            if w.winfo_toplevel() is not top:
                return None
        except tk.TclError:
            return None
        cur = w
        while cur is not None and cur is not top:
            if isinstance(cur, ttk.Treeview):
                return cur
            if isinstance(cur, tk.Canvas):
                try:
                    if str(cur.cget("yscrollcommand")):
                        return cur
                except tk.TclError:
                    pass
            try:
                cur = cur.master
            except tk.TclError:
                return None
        return None

    def _apply_scroll(target, units) -> bool:
        try:
            target.yview_scroll(units, "units")
        except tk.TclError:
            return False
        if isinstance(target, ttk.Treeview):
            _redraw_overlay_now(target)
        return True

    def _event_target(event):
        px = getattr(event, "x_root", None)
        py = getattr(event, "y_root", None)
        if px is None or py is None:
            try:
                px, py = top.winfo_pointerxy()
            except tk.TclError:
                return None
        target = _scrollable_under(px, py)
        if target is None and get_primary_scrollable is not None:
            # fallback hanya bila pointer masih DI JENDELA INI — pointer
            # di popup/clone ⛶ (Toplevel lain) = mesin roda jendela itu
            # yang bekerja; jangan ikut menggulir tabel utama dari luar.
            try:
                _w = top.winfo_containing(px, py)
            except tk.TclError:
                _w = None
            if _w is None:
                return None
            try:
                if _w.winfo_toplevel() is not top:
                    return None
            except tk.TclError:
                return None
            try:
                target = get_primary_scrollable()
            except Exception:  # noqa: BLE001 — batas API callback view
                # (callback milik app/view; jangan biarkan exception di
                # sana mematikan jalur roda utama)
                target = None
        if target is None or not isinstance(target, (ttk.Treeview,
                                                     tk.Canvas)):
            return None
        return target

    def _on_wheel(event):
        state = getattr(event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None          # → bindtag 'all' (fallback zoom app)
        d = getattr(event, "delta", 0) or 0
        if d == 0:
            return None
        target = _event_target(event)
        if target is None:
            return None
        acc = getattr(target, "_wheel_router_acc", 0.0)
        # ganti arah: buang sisa akumulator ARAH LAMA (pola v3.9.40 —
        # kontribusi = -d; reset saat tanda kontribusi ≠ tanda akumulator)
        if acc and ((d > 0) == (acc > 0)):
            acc = 0.0
        acc += -d / 120.0
        steps = int(acc)         # potong menuju nol; sisa diakumulasi
        target._wheel_router_acc = acc - steps
        if steps and _apply_scroll(target, steps):
            return "break"
        return None

    # X11: arah DIBAWA POLA BINDING (bukan event.num — pola konsisten
    # enable_smooth_wheel/enable_smooth_wheel_list).
    def _on_btn_up(event):
        state = getattr(event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None
        target = _event_target(event)
        if target is None:
            return None
        target._wheel_router_acc = 0.0
        return "break" if _apply_scroll(target, -1) else None

    def _on_btn_down(event):
        state = getattr(event, "state", 0) or 0
        if isinstance(state, int) and state & _ctrl:
            return None
        target = _event_target(event)
        if target is None:
            return None
        target._wheel_router_acc = 0.0
        return "break" if _apply_scroll(target, 1) else None

    top.bind("<MouseWheel>", _on_wheel, add="+")
    top.bind("<Button-4>", _on_btn_up, add="+")
    top.bind("<Button-5>", _on_btn_down, add="+")


def enable_col_resize(tree: ttk.Treeview, *, edge_px: int = 7):
    """v3.4 — Resize lebar kolom MANUAL via drag + AUTO-FIT double-click.

    Masalah lama: lebar kolom terasa "tidak bisa di-adjust" —
    - zona separator bawaan Tk sangat sempit & sulit ditemukan;
    - klik heading men-trigger sort/popup filter (HeaderFilter membuka
      Toplevel + grab_set di Button-1 → pointer "dicuri" → drag mati).

    Solusi: binding sendiri yang DIPASANG PERTAMA (sebelum HeaderFilter/
    handler klik view lain) supaya `return "break"` saat drag mematikan
    sort/filter bawaan:
    - Press di area heading dalam `edge_px` px dari tepi KANAN kolom
      → mulai drag-resize kolom itu.
    - Drag (B1-Motion) → lebar mengikuti mouse (clamp minwidth).
    - Double-click di tepi kolom → auto-fit kolom itu ke lebar konten.

    v3.9.29 — juga memasang scroll roda HALUS (enable_smooth_wheel):
    choke-point tunggal — fungsi ini dipanggil sekali per tree di SEMUA
    view + clone ⛶ + popup (14 call site), jadi smooth wheel otomatis
    aktif di semua tabel tanpa harus menyentuh tiap view.
    v3.9.55 — juga memasang SYNC OVERLAY SCROLL (sync_tree_scroll_overlays:
    drag scrollbar + keyboard — dua jalur scroll yang dulu meninggalkan
    label sel warna 1 frame di posisi lama).
    FIX 6b-07 (audit 6-b): flag idempotensi ``tree._col_resize_bound``
    (pola _smooth_wheel_bound / _multi_select_bound) — make_tree SUDAH
    memanggil fungsi ini; view yang memanggil ulang (pola copy-paste)
    dulu mendapat binding drag/resize/auto-fit GANDA (tiap B1-Motion
    men-set width 2×, Double-1 auto-fit 2×).
    """
    # FIX 6b-07 (audit 6-b): dipanggil 2× = double binding — guard.
    if getattr(tree, "_col_resize_bound", False):
        return tree
    tree._col_resize_bound = True
    enable_smooth_wheel(tree)   # v3.9.29 — idempoten (flag)
    sync_tree_scroll_overlays(tree)   # v3.9.55 — idempoten (flag/bindtag)
    state = {"col": None, "start_x": 0, "start_w": 0}

    def _edges():
        cols = _tree_display_columns(tree)
        x = 0
        out = []
        for c in cols:
            x += tree.column(c, "width")
            out.append((x, c))
        return out

    def _near_edge(cx):
        best = None
        for edge_x, col in _edges():
            if abs(cx - edge_x) <= edge_px:
                best = col  # pilih yang terakhir dalam toleransi
        return best

    def _on_press(event):
        if state["col"] is not None:
            return "break"
        try:
            region = tree.identify_region(event.x, event.y)
        except Exception:
            return None
        if region not in ("heading", "separator"):
            return None
        col = _near_edge(_tree_content_x(tree, event.x))
        if col is None:
            return None  # klik heading biasa → sort/filter tetap jalan
        state["col"] = col
        state["start_x"] = event.x
        state["start_w"] = tree.column(col, "width")
        return "break"

    def _on_motion(event):
        if state["col"] is None:
            return None
        try:
            min_w = tree.column(state["col"], "minwidth") or 24
        except Exception:
            min_w = 24
        new_w = int(max(min_w, state["start_w"] + (event.x - state["start_x"])))
        try:
            tree.column(state["col"], width=new_w)
        except tk.TclError:
            pass
        return "break"

    def _on_release(_event):
        if state["col"] is None:
            return None
        state["col"] = None
        return "break"

    def _on_double(event):
        try:
            region = tree.identify_region(event.x, event.y)
        except Exception:
            return None
        if region not in ("heading", "separator"):
            return None
        col = _near_edge(_tree_content_x(tree, event.x))
        if col is None:
            return None
        auto_fit_columns(tree, columns=[col])
        return "break"

    tree.bind("<Button-1>", _on_press, add="+")
    tree.bind("<B1-Motion>", _on_motion, add="+")
    tree.bind("<ButtonRelease-1>", _on_release, add="+")
    tree.bind("<Double-1>", _on_double, add="+")
    return tree


def auto_fit_columns(tree: ttk.Treeview, columns=None, *,
                     max_width: int = 340, min_width: int = 44,
                     pad: int = 24, sample_rows: int = 400):
    """v3.4 — Auto-fit lebar kolom ke konten (judul + sampel baris).

    Ukuran dihitung dari font tabel via Font.measure:
    max(lebar judul, lebar isi terpanjang sampel) + pad, dibatasi
    [min_width, max_width]. Untuk tabel besar hanya sampel `sample_rows`
    baris merata yang diukur (ukur 400×30 sel < 100ms).
    v3.9.48 — mengukur dgn NAMED FONT ter-zoom (theme.font(10)) supaya
    auto-fit tetap akurat saat UI di-zoom CTRL+Scroll (dulu Font baru
    size-10 statis → lebar kolom salah hitung di zoom ≠ 100%).
    v3.9.50 — [MAJOR audit 3-a] BOUNDS ikut ter-skala ×theme.ui_scale():
    pengukuran font sudah ter-zoom tapi clamp max_width=340 STATIS →
    kolom panjang (Nama Barang) TERPOTONG mulai zoom ±110% (butuh
    634px di 200%, capped 340). Kini min/max/pad diskalakan → janji
    'zoom seluruh UI' berlaku juga utk lebar kolom tabel.
    """
    # v3.9.50 — bounds pixel ter-skala zoom (default DAN override caller
    # sama-sama diskalakan — satuan pixel konten berubah dgn zoom).
    _zs = ui_scale()
    max_width = round(max_width * _zs)
    min_width = round(min_width * _zs)
    pad = round(pad * _zs)
    try:
        meas = font(10).measure
    except Exception:
        def meas(s):  # fallback kasar
            return 7 * len(str(s))

    cols = list(columns) if columns is not None else _tree_display_columns(tree)

    # v3.9.71 — kolom beku (freeze-pane pivot): tree dgn atribut
    # `_autofit_skip` (set nama kolom) tidak menyentuh kolom yang
    # di-skip — tree utama pivot menyembunyikan #0 (width 0, nama tampil
    # di tree beku kiri); tanpa ini auto-fit me-LEBARKAN kembali #0 dan
    # nama muncul DOBEL di sisi kanan.
    _skip = getattr(tree, "_autofit_skip", None)
    if _skip:
        cols = [c for c in cols if str(c) not in _skip]

    try:
        children = tree.get_children("")
    except tk.TclError:
        return
    n = len(children)
    if n > sample_rows:
        step = n / float(sample_rows)
        idxs = sorted({min(n - 1, int(i * step)) for i in range(sample_rows)})
    else:
        idxs = list(range(n))

    # v3.7 FIX (deep audit): index values = urutan kolom LOGIS — values[]
    # item Treeview diindeks sesuai tree["columns"], bukan urutan display;
    # setelah kolom disembunyikan, auto-fit dulu mengukur nilai kolom yang
    # SALAH (lebar kolom tidak sesuai kontennya).
    try:
        logical_cols = [str(c) for c in tree["columns"]]
    except Exception:
        logical_cols = []

    # cache values per baris sampel (1 panggilan Tcl per baris)
    # v3.9.55 — MERGE-AWARE: tree dgn atribut _autofit_value_get(iid, col,
    # cur) (deviasi_view: kolom Nama Barang/Rank head-only — baris lanjutan
    # blank) mengukur nilai RAW per iid supaya lebar kolom tidak menyusut
    # hanya karena sampel tak mengenai baris head kelompok.
    _vg = getattr(tree, "_autofit_value_get", None)
    sampled_vals = []
    sampled_texts = []
    for i in idxs:
        it = tree.item(children[i])
        vals = list(it.get("values") or [])
        if _vg is not None:
            # v3.9.55 — override nilai pengukuran merge-aware; gagal →
            # pakai nilai asli (suppress sempit, bukan blind except).
            with contextlib.suppress((AttributeError, IndexError,
                                       TypeError, ValueError, tk.TclError)):
                vals = [
                    _vg(str(children[i]), logical_cols[k],
                        vals[k] if k < len(vals) else "")
                    for k in range(len(logical_cols))]
        sampled_vals.append(vals)
        sampled_texts.append(str(it.get("text") or ""))

    for col in cols:
        try:
            # FIX 6b-02 (audit 6-b): judul diukur TANPA sufiks panah sort —
            # kolom terakhir di-sort dulu ikut terukur +~12px (kosmetik).
            w = meas(_strip_sort_arrow(
                str(tree.heading(col, "text") or ""))) + pad + 10
        except tk.TclError:
            continue
        if col == "#0":
            for t in sampled_texts:
                w = max(w, meas(t) + pad + 18)
        else:
            k = logical_cols.index(col) if col in logical_cols else -1
            for vals in sampled_vals:
                if 0 <= k < len(vals):
                    w = max(w, meas(str(vals[k])) + pad)
        try:
            tree.column(col, width=int(min(max(w, min_width), max_width)))
        except tk.TclError:
            continue
    # v3.9.42 — redraw overlay SEKARANG (audit 61-c P2): lebar kolom
    # berubah programatik (tombol ↔ Auto-Fit / menu auto-fit kolom) TIDAK
    # memicu <Configure> tree maupun yscrollcommand → label sel warna
    # salah posisi/lebar sampai interaksi berikutnya. No-op tanpa overlay.
    _redraw_overlay_now(tree)


def autofit_tree_once(view, tree: ttk.Treeview) -> None:
    """v3.9.55 — F8 (user: "Waktu pertama kali buka program bisa gak sudah
    diset ke auto fit biar gak adjust manual lagi?"): auto-fit lebar kolom
    SEKALI per muat data — dipanggil view dari render_done (batch insert
    selesai → konten terukur). view me-reset flag via reset_autofit_once
    di load_data; view tanpa reset (test standalone) tetap sekali saja."""
    if getattr(view, "_autofit_once", False):
        return
    view._autofit_once = True
    with contextlib.suppress(Exception):
        auto_fit_columns(tree)


def reset_autofit_once(view) -> None:
    """v3.9.55 — F8: reset flag sekali-per-muat (dipanggil view.load_data)."""
    view._autofit_once = False


class FrozenNamePane:
    """v3.9.71 — FREEZE KOLOM NAMA BARANG (user: "di tab pivot tabel gak
    bsia freeze kolom nama barang ya? sehingga jika aku scroll ke kanan
    bisa kefreze") — split-pane ala spreadsheet utk ttk.Treeview.

    ttk.Treeview TIDAK punya kolom beku native; pola standar Tk = DUA
    tree berdampingan dgn iid/hirarki/teks/tag IDENTIK:
    - tree KIRI (``self.tree``): hanya kolom #0 — nama barang (parent)
      + baris metric (anak), heading + funnel menempel di sini;
    - tree KANAN (``right`` — tree utama view): #0 DISEMBUNYIKAN
      (width 0 + ``_autofit_skip``), hanya kolom matrix; scroll
      HORIZONTAL hanya milik sisi kanan → nama barang TIDAK ikut
      bergeser saat menggulir ke kanan (kontrak freeze).

    Sinkronisasi otomatis dua arah (guard anti-loop):
    - scroll VERTIKAL: roda mouse di salah satu sisi → sisi lain ikut;
      scrollbar milik view/pemanggil (vsb) tetap di-update lewat
      yscrollcommand tree utama yang memanggil ``follow_right``;
    - SELEKSI: klik / Ctrl+A / panah keyboard di salah satu sisi
      tersinkron — double-click popup & copy TSV tetap jalan per sisi
      (iid identik, handler view tree-agnostic).

    Isi kiri dibangun ulang lewat ``mirror_items(items)`` (render utama)
    atau ``mirror_from_right()`` (setelah filter/sort clone ⛶ mengubah
    isi kanan) supaya selalu identik dgn kanan.
    """

    def __init__(self, right: ttk.Treeview, parent, *,
                 heading: str = "Nama Barang", width: int = 280,
                 minwidth: int = 180, setup_tags=None,
                 selectmode: str = "extended"):
        self.right = right
        self._y_sync = False
        self._sel_sync = False
        self._insert_cancel = None

        self.pane = tk.Frame(parent, bg=C_CARD)
        self.tree = ttk.Treeview(self.pane, show="tree headings",
                                 selectmode=selectmode)
        self.tree.pack(side="left", fill="both", expand=True)
        # garis pemisah tipis ala freeze-pane Excel
        tk.Frame(self.pane, bg=C_BORDER, width=1).pack(
            side="left", fill="y")
        self.tree.heading("#0", text=heading)
        self.tree.column("#0", width=width, minwidth=minwidth,
                         stretch=False)
        if setup_tags is not None:
            # tag styling IDENTIK tree utama (warna metric/in_row/bm_row
            # mewarnai sel nama juga — urutan register_find_tags tetap
            # dijaga oleh setup_tags milik view, pola FIX 15-c F-01)
            with contextlib.suppress(Exception):
                setup_tags(self.tree)

        # roda mouse di atas kolom beku → tree utama ikut (chain balik
        # lewat yscrollcommand utama: vsb ikut ter-update)
        self.tree.configure(yscrollcommand=self._on_left_scroll)
        # seleksi dua arah (iid identik kedua sisi)
        self.tree.bind("<<TreeviewSelect>>",
                       lambda _e: self._sync_selection(self.tree,
                                                       self.right),
                       add="+")
        right.bind("<<TreeviewSelect>>",
                   lambda _e: self._sync_selection(self.right,
                                                   self.tree),
                   add="+")

    # -- scroll vertikal dua arah -------------------------------------------
    def _on_left_scroll(self, first, last):
        """Tree beku digulir (roda mouse di area nama) → tree utama ikut
        (yscrollcommand utama lalu men-update scrollbar + follow_right
        diblokir guard)."""
        if self._y_sync:
            return
        self._y_sync = True
        try:
            self.right.yview_moveto(float(first))
        except tk.TclError:
            pass
        finally:
            self._y_sync = False

    def follow_right(self, first, last):
        """Tree utama digulir → tree beku mengikuti. Dipanggil dari
        yscrollcommand tree utama (pemanggil tetap memegang vsb.set —
        pane hanya menyinkronkan baris nama, bukan scrollbar)."""
        if self._y_sync:
            return
        self._y_sync = True
        try:
            self.tree.yview_moveto(float(first))
        except tk.TclError:
            pass
        finally:
            self._y_sync = False

    # -- seleksi dua arah ----------------------------------------------------
    def _sync_selection(self, src, dst):
        # v3.9.71 FIX LOOP: <<TreeviewSelect>> diproses LEWAT ANTREAN
        # event — flag _sel_sync tidak melintasi batas antrean (handler
        # sisi lain jalan SETELAH flag direset → ping-pong tak terbatas;
        # terbukti hang saat smoke). Guard utama kini KESAMAAN SELEKSI:
        # menulis hanya bila beda — event pantulan berhenti sendiri
        # karena seleksi sudah sama (flag tetap dipertahankan sbg lapis
        # kedua utk event yang diproses sinkron, mis. event_generate
        # di test).
        if self._sel_sync:
            return
        try:
            sel = set(src.selection())
            cur = set(dst.selection())
        except tk.TclError:
            return
        if sel == cur:
            return
        self._sel_sync = True
        try:
            dst.selection_set(list(sel))
        except tk.TclError:
            pass   # iid belum ada di sisi lain (render berjalan) — abaikan
        finally:
            self._sel_sync = False

    # -- mirror isi ------------------------------------------------------------
    def mirror_items(self, items, *, batch: int = 500, on_done=None):
        """Bangun ulang isi tree beku dari daftar item sumber
        [(parent_iid, iid, kwargs)] — HANYA text/tags/open yang dibawa
        (kolom matrix tidak ada di sisi kiri). Batch async; batch lama
        dibatalkan dulu supaya re-render di tengah insert tidak
        menyisakan baris basi (pola insert_tree_items)."""
        cancel = self._insert_cancel
        if cancel is not None:
            with contextlib.suppress(Exception):
                cancel()
        try:
            self.tree.delete(*self.tree.get_children(""))
        except tk.TclError:
            return None
        name_items = [
            (p, iid, {"text": (kw or {}).get("text", ""),
                      "tags": (kw or {}).get("tags", ""),
                      "open": bool((kw or {}).get("open", False))})
            for (p, iid, kw) in items]
        self._insert_cancel = insert_tree_items(
            self.tree, name_items, batch=batch, on_done=on_done)
        return self._insert_cancel

    def mirror_from_right(self, *, batch: int = 500, on_done=None):
        """Sinkronkan tree beku dari isi tree utama SAAT INI — dipakai
        clone ⛶ setelah filter baris / sort mengubah sisi kanan."""
        items = []

        def _rec(parent):
            for iid in self.right.get_children(parent):
                it = self.right.item(iid)
                items.append((parent, iid, {
                    "text": it.get("text", ""),
                    "tags": it.get("tags", ""),
                    "open": bool(it.get("open", False)),
                }))
                _rec(iid)

        try:
            _rec("")
        except tk.TclError:
            return None
        return self.mirror_items(items, batch=batch, on_done=on_done)

    def cancel_pending(self):
        """Batalkan batch insert yang masih berjalan (window clone
        ditutup di tengah salin — pola FIX B-07 audit 2-b)."""
        cancel = self._insert_cancel
        if cancel is not None:
            with contextlib.suppress(Exception):
                cancel()
            self._insert_cancel = None


# --- Maximize table (fullscreen clone) ----------------------------------------

def open_tree_maximized(source_tree: ttk.Treeview, title: str, *,
                        setup_tags=None, on_double_click=None,
                        on_sort_setup=None, on_context_menu=None,
                        on_filter_setup=None, on_render_done=None,
                        frozen_name: bool = False):
    """Buka window besar berisi clone penuh dari source_tree — tombol ⛶.

    setup_tags(new_tree)   : pasang tag styling (mis. self._setup_tags).
    on_double_click(event) : handler double-click — harus tree-agnostic
                             (identifikasi baris via event.widget).
    on_sort_setup(new_tree): pasang command sort heading per view (LEGASI
                             v3.4 — utk view tanpa filter kolom).
    on_context_menu(event) : handler klik-kanan (copy Nomor/Nomor PO, dll).
    on_filter_setup(new_tree): v3.6 — pasang HeaderFilterGroup di clone
                             (klik funnel = popup filter + sort, ala tabel
                             utama). Sebelumnya funnel clone cuma ikon
                             mati — tidak bisa diklik.
    on_render_done(new_tree): v3.9.2 — dipanggil SETELAH semua item clone
                             selesai di-insert (batch async). Dipakai view
                             utk memasang ulang TAG PER-CELL (minus merah)
                             di clone — insert ulang menghapus tag cell.
    frozen_name (v3.9.71)  : True = clone memakai FREEZE-PANE kolom nama
                             (pola FrozenNamePane — tab Pivot matrix):
                             tree beku kiri berisi #0, tree utama clone
                             menyembunyikan #0 + isi kiri disalin dari
                             kanan. View membaca ``new_tree._frozen_pane``
                             di dalam on_filter_setup utk memasang funnel
                             di sisi beku (filter baris lewat
                             attach_clone_filters(..., filter_tree=
                             new_tree)). Default False = perilaku lama
                             (12 view lain tak tersentuh).

    v3.6: displaycolumns (kolom tersembunyian) disalin dari sumber; clone
    punya ColumnManager sendiri (klik kanan heading / tombol ◱ Kolom) yang
    MIRROR ke tabel sumber — hide/unhide di window besar juga berlaku di
    tabel utama setelah window ditutup.

    Return (win, new_tree).
    """
    root = source_tree.winfo_toplevel()
    win = tk.Toplevel(root)
    frozen_pane = None          # v3.9.71 — diisi bila frozen_name=True
    # v3.9.59 — fix 2b-09 (audit 2-b): judul menyatakan SALINAN — clone
    # adalah snapshot; data di dalamnya TIDAK diperbarui saat sumber
    # re-load/refresh (dulu bisa dianggap live view).
    win.title(f"{title} — Perbesar (salinan)")
    win.configure(bg=C_BG)
    win.transient(root)

    try:
        rw, rh = root.winfo_width(), root.winfo_height()
        rw = rw if rw > 300 else 1280
        rh = rh if rh > 300 else 760
        w, h = int(rw * 0.95), int(rh * 0.92)
        x = int(root.winfo_rootx() + (rw - w) / 2)
        y = int(root.winfo_rooty() + (rh - h) / 2)
        win.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        win.geometry("1240x760")

    # -- header band gelap --
    head = tk.Frame(win, bg=C_HEADER)
    head.pack(fill="x")
    hi = tk.Frame(head, bg=C_HEADER)
    hi.pack(fill="x", padx=16, pady=10)
    tk.Label(hi, text="⛶", bg=C_HEADER, fg="#5eead4",
             font=font(12, "bold")).pack(side="left")
    tk.Label(hi, text=title, bg=C_HEADER, fg="#f1f5f9",
             font=font(12, "bold")).pack(side="left", padx=(8, 0))
    tk.Button(
        hi, text="↔ Auto-Fit",
        command=lambda: (
            auto_fit_columns(new_tree),
            # v3.9.71 — clone freeze-pane: kolom nama (tree beku) ikut
            (auto_fit_columns(frozen_pane.tree, columns=["#0"])
             if frozen_pane is not None else None)),
        bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
        activeforeground="#ffffff", bd=0, relief="flat",
        highlightthickness=0, cursor="hand2", font=font(9, "bold"),
        padx=12, pady=5,
    ).pack(side="right", padx=(0, 6))
    tk.Button(
        hi, text="✕ Tutup (Esc)", command=win.destroy,
        bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
        activeforeground="#ffffff", bd=0, relief="flat",
        highlightthickness=0, cursor="hand2", font=font(9, "bold"),
        padx=12, pady=5,
    ).pack(side="right")

    # -- body --
    body = tk.Frame(win, bg=C_BG)
    body.pack(fill="both", expand=True, padx=12, pady=12)
    card = tk.Frame(body, bg=C_CARD, highlightbackground=C_BORDER,
                    highlightthickness=1)
    card.pack(fill="both", expand=True)
    cin = tk.Frame(card, bg=C_CARD)
    cin.pack(fill="both", expand=True, padx=8, pady=8)

    try:
        # Tk 9.x: cget("show") mengembalikan tuple index-object —
        # deteksi via representasi string (kompatibel Tk 8 & 9)
        raw = source_tree.cget("show")
        parts = " ".join(str(x) for x in raw) if isinstance(raw, (tuple, list)) \
            else str(raw)
        show_opt = "tree headings" if "tree" in parts else "headings"
    except Exception:
        show_opt = "headings"
    new_tree = ttk.Treeview(cin, columns=list(source_tree["columns"]),
                            show=show_opt, selectmode="extended")

    for cid in ["#0"] + list(source_tree["columns"]):
        try:
            cfg = source_tree.column(cid)
            new_tree.column(cid, width=cfg.get("width", 100),
                            minwidth=cfg.get("minwidth", 40),
                            anchor=cfg.get("anchor", "w"),
                            stretch=cfg.get("stretch", True))
            h = source_tree.heading(cid)
            kw = {"text": h.get("text", "")}
            if h.get("image"):
                kw["image"] = h["image"]
            new_tree.heading(cid, **kw)
        except tk.TclError:
            continue

    # v3.9.71 — clone freeze-pane: #0 di tree utama clone WAJIB tersembunyi
    # (nama tampil di tree beku; sumber biasanya sudah width-0 tapi clone
    # bisa dibuka pra-render — paksa konsisten) + auto-fit tak menyentuh
    # #0 di sisi ini.
    if frozen_name:
        new_tree.column("#0", width=0, minwidth=0, stretch=False)
        new_tree._autofit_skip = {"#0"}

    # v3.6: salin state kolom tersembunyi (displaycolumns) sumber → clone
    try:
        dc = source_tree.cget("displaycolumns")
        dc_items = [str(x) for x in dc] if isinstance(dc, (tuple, list)) \
            else str(dc).split()
    except Exception:
        dc_items = []
    if dc_items and "#all" not in dc_items:
        try:
            new_tree.configure(displaycolumns=dc_items)
        except tk.TclError:
            pass

    if setup_tags:
        try:
            setup_tags(new_tree)
        except Exception:
            pass

    # v3.9.64 — FIX (audit 15-c F-07): Ctrl+F jalan DI DALAM window clone ⛶
    # (Toplevel sendiri — bindtag Toplevel-nya tak memuat binding root app;
    # clone = tabel besar 29k baris, justru paling butuh pencarian).
    install_tree_find_binding(win, lambda: new_tree)

    # v3.4: resize kolom manual + auto-fit — dipasang PERTAMA supaya
    # "break" saat drag/double-click tepi kolom mematikan handler view
    enable_col_resize(new_tree)
    enable_multi_select(new_tree)  # v3.9.32

    # v3.9.71 — clone freeze-pane: tree beku + resize/multi-select di
    # sisi nama (lebar kolom mengikuti sisi beku sumber bila ada).
    if frozen_name:
        _src_pane = getattr(source_tree, "_frozen_pane", None)
        _w = 280
        if _src_pane is not None:
            with contextlib.suppress(Exception):
                _w = int(_src_pane.tree.column("#0", "width") or 280)
        frozen_pane = FrozenNamePane(
            new_tree, cin, heading="Nama Barang", width=_w,
            setup_tags=setup_tags)
        new_tree._frozen_pane = frozen_pane   # dibaca on_filter_setup view
        enable_col_resize(frozen_pane.tree)
        enable_multi_select(frozen_pane.tree)

    # v3.6: hide/unhide kolom di clone (klik kanan heading / tombol ◱ Kolom)
    # — mirror ke tabel sumber supaya state konsisten setelah window tutup
    clone_colmgr = ColumnManager(new_tree, mirror=source_tree)
    tk.Button(
        hi, text="◱ Kolom", command=clone_colmgr.open_panel,
        bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
        activeforeground="#ffffff", bd=0, relief="flat",
        highlightthickness=0, cursor="hand2", font=font(9, "bold"),
        padx=12, pady=5,
    ).pack(side="right", padx=(0, 6))

    vsb = ttk.Scrollbar(cin, orient="vertical", command=new_tree.yview)
    hsb = ttk.Scrollbar(cin, orient="horizontal", command=new_tree.xview)
    if frozen_pane is not None:
        # v3.9.71 — clone freeze-pane: vsb tetap milik tree utama, tree
        # beku mengikuti lewat FrozenNamePane; hsb hanya sisi matrix —
        # nama TIDAK ikut scroll horizontal (kontrak freeze).
        new_tree.configure(
            xscrollcommand=hsb.set,
            yscrollcommand=lambda f, l: (
                vsb.set(f, l), frozen_pane.follow_right(f, l)))
        frozen_pane.pane.grid(row=0, column=0, sticky="ns")
        new_tree.grid(row=0, column=1, sticky="nsew")
        vsb.grid(row=0, column=2, sticky="ns")
        hsb.grid(row=1, column=0, columnspan=2, sticky="ew")
        cin.grid_rowconfigure(0, weight=1)
        cin.grid_columnconfigure(1, weight=1)
    else:
        new_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        new_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        cin.grid_rowconfigure(0, weight=1)
        cin.grid_columnconfigure(0, weight=1)

    foot = tk.Frame(cin, bg=C_CARD)
    foot.grid(row=2, column=0,
              columnspan=(3 if frozen_pane is not None else 2),
              sticky="ew", pady=(6, 0))
    count_var = tk.StringVar(value="Menyalin tabel…")
    tk.Label(foot, textvariable=count_var, bg=C_CARD, fg=C_TEXT_MUTED,
             font=font(9)).pack(side="left")
    # v3.9.59 — fix 2b-09: catatan kaki penanda salinan (filter/sort clone
    # terpisah dari tabel sumber — filter di clone tidak memengaruhi sumber
    # dan sebaliknya utk baris/nilai).
    tk.Label(foot, text="Salinan — filter/sort terpisah", bg=C_CARD,
             fg=C_TEXT_MUTED, font=font(9)).pack(side="right")

    overlay = LoadingOverlay(cin, "Menyalin tabel…")
    overlay.show(delay_ms=120)

    items = []

    def collect(parent):
        for iid in source_tree.get_children(parent):
            it = source_tree.item(iid)
            items.append((parent, iid, {
                "text": it.get("text", ""),
                "values": it.get("values", ""),
                "tags": it.get("tags", ""),
                "open": it.get("open", False),
            }))
            collect(iid)

    collect("")

    def done():
        # FIX 6b-04 (audit 6-b): idempoten — bisa dipanggil normal oleh
        # insert_tree_items ATAU oleh apply_tree_row_filters ketika batch
        # copy dibatalkan di tengah jalan (filter diklik saat "Menyalin
        # n/total baris…" masih berjalan); tanpa ini overlay loading clone
        # menempel selamanya.
        if getattr(new_tree, "_copy_finalized", False):
            return
        new_tree._copy_finalized = True
        # FIX 6b-04: snapshot penuh hanya hidup selama copy — lepas
        # referensi (memori) + finalizer setelah selesai.
        new_tree._full_items = None
        new_tree._copy_finalize = None
        overlay.hide()
        # FIX B-15 (audit 2-b): format ribuan Indonesia — koma EN
        # ("1,346") terbaca desimal dalam konvensi Indonesia.
        count_var.set(f"{fmt_int_id(len(items))} baris · {title}")
        if on_render_done:
            # suppress (bukan try/except-pass): callback view defensive di
            # dalamnya; kegagalan tidak boleh memutus batch insert clone
            with contextlib.suppress(Exception):
                on_render_done(new_tree)

    # FIX 6b-04 (audit 6-b): simpan snapshot item PENUH + finalizer di
    # tree SELAMA copy berjalan — apply_tree_row_filters memakainya bila
    # filter diklik sebelum copy selesai (cache lengkap, bukan baris
    # parsial) dan memanggil _copy_finalize utk efek samping done().
    new_tree._full_items = items
    new_tree._copy_finalize = done

    insert_cancel = insert_tree_items(new_tree, items, batch=600,
                                      on_done=done,
                                      chunk_callback=lambda n, t: count_var.set(
                                          f"Menyalin {fmt_int_id(n)}/"
                                          f"{fmt_int_id(t)} baris…"))
    # v3.9.71 — clone freeze-pane: sisi nama ikut tersalin (batch sendiri,
    # iid/teks/tag identik — text/tags/open saja, kolom matrix tak dibawa)
    if frozen_pane is not None:
        frozen_pane.mirror_items(items, batch=600)
    # FIX B-07 (audit 2-b): daftarkan cancel batch ke tree — memfilter /
    # menyortir clone saat copy awal masih berjalan kini MEMBATALKAN batch
    # lama dulu (apply_tree_row_filters mengecek atribut ini); dulu cache
    # filter dibangun dari baris PARSIAL → clone rusak diam-diam.
    new_tree._row_filter_cancel = insert_cancel

    def _on_win_destroy(event):
        # batalkan batch + timer yang masih pending saat window ditutup
        if event.widget is win:
            insert_cancel()
            # v3.9.71 — clone freeze-pane: batch sisi nama ikut dibatalkan
            if frozen_pane is not None:
                frozen_pane.cancel_pending()
            overlay.hide()
            # FIX B-18 (audit 2-b): lepas registrasi backref colmgr clone
            # dari tree sumber — tanpa ini daftar _mirror_backrefs tumbuh
            # tiap buka/tutup ⛶ (apply() sumber membuang waktu membaca
            # referensi mati, meski sudah di-skip winfo_exists).
            with contextlib.suppress(Exception):
                refs = getattr(source_tree, "_mirror_backrefs", None)
                if refs and clone_colmgr in refs:
                    refs.remove(clone_colmgr)

    win.bind("<Destroy>", _on_win_destroy, add="+")

    if on_double_click:
        # FIX B-04 (audit 2-b): add="+" — bind polos MENGGANTI binding
        # auto-fit tepi kolom (enable_col_resize, v3.4) → double-click
        # tepi kolom di clone mati; handler view hanya boleh DITAMBAHKAN.
        new_tree.bind("<Double-1>", on_double_click, add="+")
    if on_context_menu:
        # FIX B-04: idem — jangan mengganti menu kolom ColumnManager.
        new_tree.bind("<Button-3>", on_context_menu, add="+")
    if on_filter_setup:
        try:
            on_filter_setup(new_tree)
        except Exception:
            pass
    elif on_sort_setup:
        on_sort_setup(new_tree)

    win.bind("<Escape>", lambda e: win.destroy())
    win.focus_set()
    return win, new_tree


# ============================================================================
# v3.9.62 — CARI DI TABEL (Ctrl+F) — referensi fitur "find window" tksheet,
# diimplementasikan IN-HOUSE utk ttk.Treeview stdlib (tanpa dependensi baru;
# tksheet sendiri berhenti dikembangkan kecuali bugfix).
# ============================================================================

# Tag & warna highlight — keluarga aksen oranye (non-blue, sejalan design
# sistem #c2410c); opsinya BACKGROUND SAJA supaya TIDAK bentrok dgn tag
# milik view yang memakai FOREGROUND (negative/zero_dev/CEK).
# v3.9.64 — FIX (audit 15-c F-01): konstanta dipindah ke theme.py + tag
# didaftarkan SEBELUM tag bg view (register_find_tags) — prioritas tag
# Treeview = URUTAN CREATE; di sini (pembukaan popup) terlambat = highlight
# kalah oleh zebra evenrow/oddrow dan TIDAK dirender. Re-export utk
# kompatibilitas (test/§72 mengimpor dari widgets).


class TreeFindPopup:
    """v3.9.62 — popup pencarian baris utk ttk.Treeview (Ctrl+F).

    Perilaku (pola find-window aplikasi modern / tksheet):
    - substring CASE-INSENSITIVE atas SEMUA kolom (values + teks #0)
    - semua baris cocok → latar lembut; baris AKTIF → latar kuat +
      ``tree.see`` (menggulir tabel ke baris itu)
    - navigasi: Enter = berikutnya · Shift+Enter = sebelumnya (wrap) ·
      tombol ‹ › · status "i / N baris cocok"
    - ketik ulang → rehitung DEBOUNCE 160 ms (tabel 29k baris tak
      discan tiap keystroke)
    - tangguh thd re-render: iid yang hilang di-skip; bila SEMUA cocok
      hilang (view reload/filter) → rehitung otomatis dari query aktif
    - ESC / tombol ✕ / tutup jendela → semua highlight DIBERSIHKAN
    - satu instance per tree (``tree._find_popup`` — pola _last_sort);
      non-modal: pengguna tetap bisa menggulir/sort tabel selama buka.
    """

    _DEBOUNCE_MS = 160
    _NAV_KEYSYM = frozenset({"Return", "KP_Enter", "Escape", "Tab",
                              "Shift_L", "Shift_R", "Left", "Right",
                              "Up", "Down", "Home", "End", "Prior",
                              "Next", "Control_L", "Control_R"})
    # v3.9.64 — FIX (audit 15-c F-07): popup Cari aktif SELALU SATU di
    # seluruh app (buka utk tree lain → popup lama ditutup; dulu popup
    # tree utama + popup anak tab bisa KOEKSISTEN — yang satu menempel
    # pada tabel tak terlihat).
    _ACTIVE: TreeFindPopup | None = None

    def __init__(self, tree: ttk.Treeview):
        self.tree = tree
        self._matches = []          # iid cocok (urut tampil)
        self._cur = -1              # indeks match aktif
        self._after_id = None
        self._digest: dict = {}     # v3.9.64 — iid → digest nilai baris saat match
        # v3.9.64 — single-active (audit 15-c F-07): tutup popup tree LAIN
        _prev = TreeFindPopup._ACTIVE
        if _prev is not None:
            with contextlib.suppress(Exception):
                _prev.close()
        TreeFindPopup._ACTIVE = self
        try:
            tree.tag_configure(FIND_HIT_TAG, background=FIND_HIT_BG)
            tree.tag_configure(FIND_CUR_TAG, background=FIND_CUR_BG)
        except tk.TclError:
            pass
        top = tree.winfo_toplevel()
        self.win = tk.Toplevel(top)
        self.win.title("Cari di tabel")
        self.win.transient(top)
        self.win.resizable(False, False)
        row = ttk.Frame(self.win, padding=(8, 8, 8, 2))
        row.pack(fill="x")
        ttk.Label(row, text="Cari:").pack(side="left")
        self.var = tk.StringVar()
        self.entry = ttk.Entry(row, textvariable=self.var, width=26)
        self.entry.pack(side="left", padx=(6, 6))
        self.entry.bind("<Return>", lambda e: self._nav(1))
        self.entry.bind("<Shift-Return>", lambda e: self._nav(-1))
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self._btn_prev = ttk.Button(row, text="‹", width=3,
                                    command=lambda: self._nav(-1))
        self._btn_prev.pack(side="left")
        self._btn_next = ttk.Button(row, text="›", width=3,
                                    command=lambda: self._nav(1))
        self._btn_next.pack(side="left", padx=(4, 8))
        self._btn_close = ttk.Button(row, text="✕", width=3,
                                     command=self.close)
        self._btn_close.pack(side="left")
        self.status = ttk.Label(
            self.win, padding=(10, 0, 10, 6),
            text="Ketik untuk mencari — Enter = berikutnya · "
                 "Shift+Enter = sebelumnya · Esc = tutup")
        self.status.pack(fill="x")
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._place(top)
        self.entry.focus_set()

    # --- penempatan jendela ------------------------------------------
    def _place(self, top) -> None:
        """Kanan-atas jendela pemilik (tak menutupi area kiri tabel)."""
        with contextlib.suppress(tk.TclError):
            self.win.update_idletasks()
            _w = self.win.winfo_reqwidth()
            _x = top.winfo_rootx() + max(8, top.winfo_width() - _w - 24)
            _y = top.winfo_rooty() + 56
            self.win.geometry(f"+{max(_x, 0)}+{max(_y, 0)}")

    # --- highlight tag (merge — jangan hapus tag milik view) ---------
    def _apply_tag(self, iid, tag: str) -> None:
        try:
            tags = tuple(tg for tg in (self.tree.item(iid, "tags") or ())
                         if tg not in (FIND_HIT_TAG, FIND_CUR_TAG))
            self.tree.item(iid, tags=tags + (tag,))
        except tk.TclError:
            pass   # iid hilang di tengah jalan (re-render / clone ⛶)

    def _clear_tags(self) -> None:
        for iid in list(self._matches):
            try:
                tags = tuple(
                    tg for tg in (self.tree.item(iid, "tags") or ())
                    if tg not in (FIND_HIT_TAG, FIND_CUR_TAG))
                self.tree.item(iid, tags=tags)
            except tk.TclError:
                continue

    # v3.9.64 — digest nilai baris (audit 15-c F-03): iid posisional
    # (row_0, row_1, …) DIPAKAI ULANG view saat re-render → iid "masih
    # ada" tapi isinya baris LAIN; tanpa validasi, highlight/Enter
    # mendarat di data SALAH senyap.
    def _row_digest(self, iid) -> str:
        it = self.tree.item(iid)
        hay = " ".join(str(v) for v in (it.get("values") or ()))
        txt = str(it.get("text") or "")
        return hay + "\x00" + txt

    # --- hitung ulang pencocokan --------------------------------------
    def _recompute(self) -> None:
        self._after_id = None
        self._clear_tags()
        self._matches = []
        self._cur = -1
        self._digest = {}
        q = (self.var.get() or "").strip().casefold()
        if not q:
            self._set_status("Ketik untuk mencari — Enter = berikutnya · "
                             "Shift+Enter = sebelumnya · Esc = tutup")
            return
        try:
            children = list(self.tree.get_children(""))
        except tk.TclError:
            return
        for iid in children:
            try:
                it = self.tree.item(iid)
            except tk.TclError:
                continue
            hay = " ".join(str(v) for v in (it.get("values") or ()))
            txt = str(it.get("text") or "")
            if q in hay.casefold() or q in txt.casefold():
                self._matches.append(iid)
                self._digest[iid] = hay + "\x00" + txt   # v3.9.64 — F-03
        if not self._matches:
            self._set_status("Tidak ada baris yang cocok")
            return
        for iid in self._matches:
            self._apply_tag(iid, FIND_HIT_TAG)
        self._cur = 0
        self._show_current()

    def _set_status(self, text: str) -> None:
        with contextlib.suppress(tk.TclError):
            self.status.configure(text=text)

    def _on_keyrelease(self, event=None) -> None:
        if event is not None and event.keysym in self._NAV_KEYSYM:
            return
        if self._after_id is not None:
            with contextlib.suppress(Exception):
                self.tree.after_cancel(self._after_id)
        self._after_id = self.tree.after(self._DEBOUNCE_MS, self._recompute)

    def _refresh_stale(self) -> None:
        """Match list basi (view re-render) → saring yang masih ada;
        bila habis → rehitung penuh dari query."""
        self._matches = [iid for iid in self._matches
                         if self.tree.exists(iid)]
        if not self._matches:
            if (self.var.get() or "").strip():
                self._recompute()
            return
        if self._cur >= len(self._matches):
            self._cur = 0
        self._show_current()

    def _on_tree_rerendered(self) -> None:
        """v3.9.64 — FIX (audit 15-c F-03): tree selesai RE-RENDER PENUH
        (choke point insert_tree_items) → hitung ulang dari query aktif.
        Iid posional dipakai ulang view → match lama bisa menempel di
        data SALAH tanpa satu pun iid hilang (bypass _refresh_stale).
        Query kosong → _recompute juga membersihkan highlight."""
        with contextlib.suppress(tk.TclError, AttributeError):
            self._recompute()

    def _show_current(self) -> None:
        if not self._matches:
            return
        self._cur %= len(self._matches)
        iid = self._matches[self._cur]
        self._set_status(f"{self._cur + 1} / {len(self._matches)} "
                         f"baris cocok")
        if not self.tree.exists(iid):
            self._refresh_stale()
            return
        # v3.9.64 — F-03: iid hidup tapi isinya BARIS LAIN (iid posional
        # dipakai ulang) → digest berubah → recompute penuh (rekursif aman:
        # digest baru tersimpan saat recompute).
        try:
            if self._digest.get(iid) is not None \
                    and self._digest[iid] != self._row_digest(iid):
                self._recompute()
                return
        except tk.TclError:
            self._refresh_stale()
            return
        for other in self._matches:
            if other != iid:
                self._apply_tag(other, FIND_HIT_TAG)
        self._apply_tag(iid, FIND_CUR_TAG)
        with contextlib.suppress(tk.TclError):
            self.tree.see(iid)

    def _nav(self, delta: int) -> None:
        if not self._matches:
            if (self.var.get() or "").strip():
                self._recompute()
            if not self._matches:
                return
        self._cur = (self._cur + delta) % len(self._matches)
        self._show_current()

    # --- tutup + bersihkan --------------------------------------------
    def close(self) -> None:
        if self._after_id is not None:
            with contextlib.suppress(Exception):
                self.tree.after_cancel(self._after_id)
            self._after_id = None
        self._clear_tags()
        self._matches = []
        if TreeFindPopup._ACTIVE is self:   # v3.9.64 — F-07 single-active
            TreeFindPopup._ACTIVE = None
        with contextlib.suppress(Exception):
            self.tree._find_popup = None
        with contextlib.suppress(tk.TclError):
            self.win.destroy()


def open_tree_find(tree: ttk.Treeview):
    """v3.9.62 — buka/fokus popup Cari utk tree (Ctrl+F; satu instance
    per tree — pola ``tree._find_popup``). Return popup atau None bila
    tree sudah tak hidup.
    v3.9.64 — single-active app-wide (audit 15-c F-07): membuka utk tree
    LAIN otomatis menutup popup lama (constructor TreeFindPopup)."""
    try:
        if not tree.winfo_exists():
            return None
    except tk.TclError:
        return None
    pop = getattr(tree, "_find_popup", None)
    if pop is not None:
        with contextlib.suppress(Exception):
            if pop.win.winfo_exists():
                pop.win.deiconify()
                pop.entry.focus_set()
                pop.entry.select_range(0, "end")
                return pop
    pop = TreeFindPopup(tree)
    tree._find_popup = pop
    return pop


def install_tree_find_binding(top, get_tree) -> None:
    """v3.9.64 — FIX (audit 15-c F-07): Ctrl+F utk Toplevel NON-root.

    Binding app dipasang di root (bindtag Toplevel hanya memuat root utk
    widget di jendela UTAMA) — popup rincian (DetailsPopup/DeviasiPopup/
    InDetailPopup) & clone ⛶ (open_tree_maximized) punya Toplevel sendiri
    → Ctrl+F mati di sana. Helper ini memasang binding yang sama, dengan
    target tree dari ``get_tree()`` (dipanggil saat event — tree dibuat
    setelah binding dipasang pun aman)."""
    def _open(_event=None):
        tree = None
        with contextlib.suppress(Exception):
            tree = get_tree()
        if tree is not None:
            open_tree_find(tree)

    for seq in ("<Control-f>", "<Control-F>"):
        try:
            top.bind(seq, _open)
        except tk.TclError:
            pass


# --- Tooltip grup tab notebook (v3.9.68) ------------------------------------------

class NotebookTabTooltips:
    """v3.9.68 — tooltip saat hover baris tab notebook (audit eksternal
    T5: 10 tab utama → beban navigasi; label COMPACT fallback v3.9.59
    memendekkan nama tab saat lebar sempit sehingga fungsi tab bisa
    kurang jelas).

    Solusi minim risiko (TANPA sidebar/redesign — urutan tab sudah
    mengikuti kelompok alur kerja): tooltip menampilkan LABEL PENUH +
    nama KELOMPOK alur kerja:
      Operasional            — ⚙️ Config · 🚀 Proses · 📊 Pivot Table
      Pemeriksaan & Rekonsiliasi — 📦 GR · 🧩 PCS · 📤 Rekap Selisih IN
      Analisis               — 📋 Laporan · 🧮 Nominal Deviasi
      Tindak Lanjut          — ☑ Follow Up · 🛒 Rincian PO

    - Hover di atas tab (elemen 'label') → tooltip muncul setelah
      ``delay_ms``; pindah ke tab lain → tooltip mengikuti; keluar dari
      baris tab → hilang.
    - Posisi mengikuti pointer (winfo_pointerx/y) — aman multi-monitor.
    - ``show(tab_key)`` / ``hide()`` publik utk pengujian (tanpa perlu
      sintesis event Motion pada koordinat tab yang bervariasi).
    - ``index("@x,y")`` Python wrapper menaikkan ValueError pada posisi
      kosong — karena itu resolusi tab memakai panggilan Tcl mentah
      (return '' bila bukan area tab; terverifikasi Xvfb :99).
    """

    def __init__(self, notebook, *, full_labels: dict, groups: dict,
                 delay_ms: int = 350):
        self.nb = notebook
        self.full_labels = dict(full_labels or {})
        self.groups = dict(groups or {})
        self._delay_ms = int(delay_ms)
        self._after_id = None
        self._tip = None
        self._tip_key = None
        notebook.bind("<Motion>", self._on_motion, add="+")
        notebook.bind("<Leave>", self._on_leave, add="+")

    # -- resolusi tab pada koordinat ---------------------------------------
    def _tab_key_at(self, x, y) -> str | None:
        try:
            idx = self.nb.tk.call(self.nb._w, "index",
                                  f"@{int(x)},{int(y)}")
        except tk.TclError:
            return None
        s = str(idx).strip()
        if not s:
            return None           # bukan area tab (halaman/notebook kosong)
        try:
            tabs = list(self.nb.tabs())
            i = int(s)
        except (tk.TclError, ValueError, TypeError):
            return None
        if 0 <= i < len(tabs):
            return str(tabs[i])
        return None

    # -- event --------------------------------------------------------------
    def _on_motion(self, event):
        key = self._tab_key_at(event.x, event.y)
        if key is None:
            self.hide()
            return
        if key == self._tip_key and self._tip is not None \
                and self._tip.winfo_exists():
            return                # tooltip utk tab ini sudah tampil
        self.hide()
        self._after_id = self.nb.after(
            self._delay_ms, lambda: self.show(key))

    def _on_leave(self, _event=None):
        self.hide()

    # -- tampil / sembunyi (publik — dipakai timer & pengujian) -------------
    def show(self, tab_key: str):
        """Tampilkan tooltip utk tab ``tab_key`` (key = str(widget tab))."""
        self._cancel_timer()
        if tab_key == self._tip_key and self._tip is not None \
                and self._tip.winfo_exists():
            return
        self._destroy_tip()
        label = self.full_labels.get(tab_key)
        group = self.groups.get(tab_key)
        if label is None or group is None:
            self._tip_key = None
            return
        tip = tk.Toplevel(self.nb)
        tip.withdraw()
        tip.overrideredirect(True)
        with contextlib.suppress(tk.TclError):
            tip.attributes("-topmost", True)
        tk.Label(tip, text=f"{label} — kelompok: {group}",
                 bg="#0f172a", fg="#f8fafc", font=font(9),
                 padx=10, pady=5).pack()
        with contextlib.suppress(tk.TclError):
            px = self.nb.winfo_pointerx() or self.nb.winfo_rootx()
            py = self.nb.winfo_pointery() or self.nb.winfo_rooty()
            tip.geometry(f"+{px + 14}+{py + 18}")
        tip.deiconify()
        self._tip = tip
        self._tip_key = tab_key

    def hide(self):
        """Sembunyikan tooltip + batalkan timer yang tertunda."""
        self._cancel_timer()
        self._destroy_tip()

    def _cancel_timer(self):
        if self._after_id is not None:
            with contextlib.suppress(tk.TclError):
                self.nb.after_cancel(self._after_id)
            self._after_id = None

    def _destroy_tip(self):
        if self._tip is not None:
            with contextlib.suppress(tk.TclError):
                self._tip.destroy()
        self._tip = None
        self._tip_key = None

    def current_text(self) -> str:
        """Teks tooltip yang sedang tampil ('' bila tidak ada) — helper
        pengujian."""
        if self._tip is None or not self._tip.winfo_exists():
            return ""
        kids = self._tip.winfo_children()
        for w in kids:
            if isinstance(w, tk.Label):
                return str(w.cget("text"))
        return ""
