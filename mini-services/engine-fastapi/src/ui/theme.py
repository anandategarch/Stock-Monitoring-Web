"""
theme.py — Design system global untuk Stock Monitoring UI (v3.0 redesign).

Di-porting dari design language aplikasi Waste (PySide6): slate + teal,
card-based, dark toolbar, konsol log gelap. Token warna identik supaya
kedua aplikasi terasa satu keluarga.

Palet:
    C_BG       #f1f5f9  slate-100  — latar utama
    C_CARD     #ffffff             — kartu
    C_HEADER   #0f172a  slate-900  — judul + toolbar gelap
    C_BORDER   #e2e8f0  slate-200  — border kartu
    C_MUTED    #64748b  slate-500  — teks sekunder
    C_ACCENT   #0f766e  teal-700   — tombol aksi utama

Font: resolusi otomatis — Segoe UI (Windows) → Noto Sans → DejaVu Sans
(Linux) supaya metrik teks jujur di semua platform.

v3.9.48 — ZOOM UI (CTRL + Scroll, permintaan user "bisa gak kalau aku
CTRL + Scroll mouse jadi zoom in dan zoom out?") + fix "tampilan tidak
HD": font()/mono() kini mengembalikan NAMED FONT (tkfont.Font) yang
di-SHARE semua widget → zoom cukup configure size sekali per font dan
seluruh UI (style ttk + tk widget + tag Treeview + konsol log) ikut
HIDUP; apply_theme idempoten dan dipanggil ulang saat zoom berubah
(rowheight tabel ikut skala). Lihat bagian ZOOM di bawah.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# --- Palet warna -----------------------------------------------------------
C_BG = "#f1f5f9"            # slate-100 — latar utama
C_CARD = "#ffffff"           # kartu
C_HEADER = "#0f172a"         # slate-900 — teks judul + toolbar
C_BORDER = "#e2e8f0"         # slate-200 — border kartu
C_BORDER_DARK = "#cbd5e1"    # slate-300 — hover border
C_TEXT_MUTED = "#64748b"     # slate-500 — teks sekunder
C_TEXT_SOFT = "#94a3b8"      # slate-400 — teks jauh/disabled

C_ACCENT = "#0f766e"         # teal-700 — aksi utama
C_ACCENT_HOVER = "#115e59"   # teal-800
C_ACCENT_SOFT = "#ccfbf1"    # teal-100 — seleksi baris
C_ACCENT_DARK = "#134e4a"    # teal-900 — teks di atas seleksi

# Status colors — identik dengan STATUS_COLORS Waste
# (v3.3: varian *_SOFT & C_BLUE/C_PURPLE/C_LOG_MUTED yang tak terpakai
#  dihapus — view memakai hex literal untuk warna baris khusus)
C_RED = "#dc2626"
C_RED_SOFT = "#fef2f2"
C_ORANGE = "#ea580c"
C_AMBER = "#b45309"
C_GREEN = "#16a34a"

# Konsol log (mirror Waste: #0b1220)
C_LOG_BG = "#0b1220"
C_LOG_FG = "#cbd5e1"

# Zebra rows tabel
ROW_EVEN = "#ffffff"
ROW_ODD = "#f8fafc"

# --- Tag highlight CARI (Ctrl+F — v3.9.64) ----------------------------------
# v3.9.64 — FIX (audit 15-c F-01, pixel-probe Xvfb Tk 9.0.4): prioritas tag
# ttk.Treeview = URUTAN CREATE (tag yang DI-CONFIGURE lebih dulu MENANG;
# urutan list tag per-item TIDAK berpengaruh — diuji: prepend di list tetap
# kalah). Popup Cari (TreeFindPopup) membuka SETELAH view memasang tag
# zebra/bg → tag find kalah prioritas → highlight ORANYE TIDAK PERNAH
# TAMPIL di semua tree ber-tag latar baris (🧮 kedua tree, 📋 3 mode, ☑
# Follow Up, Rekap IN, Rincian-PO parent/TOTAL, Pivot header/anomaly).
# FIX: tag find WAJIB di-configure SEBELUM tag view — helper
# register_find_tags() dipanggil di BARIS PERTAMA setup_tree_tags +
# _setup_tags SETIAP view (idempotent — re-configure tak mengubah prioritas).
# Opsi background SAJA (fg milik view — negative/zero/CEK — tak tersentuh).
FIND_HIT_TAG = "__find_hit"
FIND_CUR_TAG = "__find_cur"
FIND_HIT_BG = "#ffedd5"   # orange-100 — SEMUA baris cocok
FIND_CUR_BG = "#fdba74"   # orange-300 — baris AKTIF (lebih kuat)


def register_find_tags(tree) -> None:
    """v3.9.64 — pasang tag highlight Cari SEBELUM tag baris view
    (prioritas tag Treeview = urutan create — lihat catatan di atas).
    Idempotent: tag_configure ulang tidak mengubah prioritas."""
    tree.tag_configure(FIND_HIT_TAG, background=FIND_HIT_BG)
    tree.tag_configure(FIND_CUR_TAG, background=FIND_CUR_BG)

# --- Font -------------------------------------------------------------------
_FONT_CANDIDATES = [
    "Segoe UI",      # Windows
    "Noto Sans",     # Linux modern
    "DejaVu Sans",   # Linux fallback
    "Helvetica",     # macOS
    "Arial",
]
_MONO_CANDIDATES = ["Consolas", "Cascadia Mono", "JetBrains Mono", "DejaVu Sans Mono", "Courier New"]

_font_family: str | None = None
_mono_family: str | None = None


def _pick_family(candidates: list[str], fallback: str) -> str | None:
    """Pilih family font pertama yang tersedia di platform ini.

    v3.9.33 — AUDIT FIX (48-c HIGH-1): return None bila daftar family
    TIDAK bisa di-query (belum ada Tk root — tkfont.families() raise).
    None = sinyal "belum bisa resolve" bagi pemanggil supaya fallback
    TIDAK di-cache (lihat font_family/mono_family)."""
    try:
        available = set(tkfont.families())
    except Exception:
        return None
    for name in candidates:
        if name in available:
            return name
    return fallback


def font_family() -> str:
    """Family font UI utama (resolve sekali setelah root ada, lalu cache).

    v3.9.33 — AUDIT FIX (48-c HIGH-1): dulu fallback "DejaVu Sans"
    ter-CACHE PERMANEN saat resolusi dipanggil SEBELUM tk.Tk() ada
    (import-time, mis. widgets._BTN_BASE) → rantai kandidat
    "Segoe UI → Noto Sans → DejaVu" tidak pernah jalan di Windows
    produksi. Kini: kegagalan resolve (belum ada root) TIDAK di-cache —
    fallback dikembalikan sebagai nilai HIDUP dan resolusi dicoba ulang
    tiap pemanggilan sampai berhasil SEKALI (apply_theme pasca-root),
    baru hasilnya di-cache."""
    global _font_family
    if _font_family is None:
        fam = _pick_family(_FONT_CANDIDATES, "DejaVu Sans")
        if fam is None:
            # Belum ada root — JANGAN cache; kembalikan fallback hidup.
            return "DejaVu Sans"
        _font_family = fam
    return _font_family


def mono_family() -> str:
    """Family font monospace untuk log konsol.

    v3.9.33 — AUDIT FIX (48-c HIGH-1): pola lazy yang sama (jalur ini
    memang baru terpakai pasca-root via make_log_console, tapi dibuat
    konsisten + defensive)."""
    global _mono_family
    if _mono_family is None:
        fam = _pick_family(_MONO_CANDIDATES, "Courier New")
        if fam is None:
            return "Courier New"
        _mono_family = fam
    return _mono_family


# --- v3.9.48: ZOOM UI (CTRL + Scroll) ----------------------------------------
# Dua mekanisme yang bekerja sama:
#
# (1) NAMED FONT BERSAMA: font()/mono() mengembalikan OBJEK tkfont.Font
#     (satu per (kind, size, weight), di-cache) — Tk menerima objek Font
#     untuk opsi font= di SEMUA jenis widget (tk widget, ttk style, tag
#     Treeview, Text). Karena satu objek dipakai bersama, zoom cukup
#     f.configure(size=...) SEKALI per font → semua pemakai re-render
#     HIDUP (perilaku standar Tk; tidak bergantung semantik `tk scaling`
#     yang tidak mereskalakan font yang sudah dirender).
#
# (2) DISPATCH RODA-CTRL: widgets.py memasang bind_ctrl_zoom() di semua
#     titik pembuatan widget scrollable (enable_smooth_wheel /
#     make_log_console / canvas daftar filter). Pola <Control-MouseWheel>
#     / <Control-Button-4/5> LEBIH SPESIFIK daripada binding <MouseWheel>
#     polos di bindtag widget yang sama → menurut aturan Tk (binding
#     ter-spesifik menang dalam satu bindtag) CTRL+roda TIDAK menggulir
#     widget, melainkan zoom — dan 'break' mematikan binding kelas di
#     bindtag berikutnya. Handler zoom hidup di app.py (StockMonitorApp)
#     dan dihubungkan lewat set_zoom_wheel_handler(); theme dipilih
#     sebagai lokus registry karena diimpor widgets & app tanpa impor
#     melingkar.
_ui_scale = 1.0                 # faktor zoom aktif (1.0 = 100%)
_font_cache: dict = {}          # {"_root": Tk, (kind, size, weight): Font}
_ctrl_wheel_handler = None


def ui_scale() -> float:
    """Faktor zoom UI aktif (1.0 = default/100%; 1.1 = 110%)."""
    return _ui_scale


def set_ui_scale(scale: float) -> float:
    """Set faktor zoom aktif — dipakai font()/mono()/apply_theme untuk
    widget BARU yang dibuat setelah zoom berubah (popup, view).
    Zoomer (app.py) memanggil ini lalu rescale_named_fonts()."""
    global _ui_scale
    _ui_scale = scale
    return _ui_scale


def scale_pt(size: int) -> int:
    """Ukuran font POINT dikali zoom aktif (lantai 4 — tidak lenyap)."""
    return max(4, round(size * _ui_scale))


def scale_px(px: int) -> int:
    """Ukuran PIXEL desain (rowheight tabel) dikali zoom aktif."""
    return max(1, round(px * _ui_scale))


def _cache_root():
    """Root default aktif (None bila belum ada Tk — jalur import time)."""
    return getattr(tk, "_default_root", None)


def _named_font(kind: str, size: int, weight: str):
    """Ambil/buat named font untuk (kind, size, weight) — SATU objek
    bersama semua pemakai. Cache di-RESET saat root/interp lain aktif
    (font milik interp lama tak bisa dipakai lintas Tk; _default_root
    menetap di root pertama — aman untuk app + test satu-root).
    Return None bila belum ada root → pemanggil jatuh ke tuple fallback
    (perilaku defensif v3.9.33 untuk panggilan import-time)."""
    r = _cache_root()
    if r is None:
        return None
    global _font_cache
    if _font_cache.get("_root") is not r:
        _font_cache = {"_root": r}
    key = (kind, size, weight)
    f = _font_cache.get(key)
    if f is None:
        if kind == "ui":
            f = tkfont.Font(root=r, family=font_family(),
                            size=scale_pt(size), weight=weight)
        else:
            f = tkfont.Font(root=r, family=mono_family(),
                            size=scale_pt(size))
        _font_cache[key] = f
    return f


def rescale_named_fonts() -> list:
    """v3.9.48 — configure ulang SEMUA named font ke size-dasar × zoom
    aktif. Semua widget pemakai otomatis re-render (satu named font =
    satu objek bersama — konfigurasi menyebarkan ke semua pemakainya).
    Return [(key, size_baru)] untuk verifikasi/test."""
    out = []
    for key, f in list(_font_cache.items()):
        if key == "_root":
            continue
        f.configure(size=scale_pt(key[1]))
        out.append((key, f.cget("size")))
    return out


def set_zoom_wheel_handler(handler) -> None:
    """Hubungkan handler zoom (app.py) ke dispatch roda-CTRL."""
    global _ctrl_wheel_handler
    _ctrl_wheel_handler = handler


def ctrl_wheel_dispatch(event):
    """Panggilan balik bindtag roda-CTRL (dipasang bind_ctrl_zoom di
    widget scrollable + bind_class Listbox oleh app).
    Tanpa handler (view mandiri di unit test) → None: event dibiarkan
    lanjut ke bindtag berikutnya (tidak ada yang mengonsumsi)."""
    if _ctrl_wheel_handler is not None:
        return _ctrl_wheel_handler(event)
    return None


def bind_ctrl_zoom(widget) -> None:
    """v3.9.48 — pasang pola roda-CTRL TINGKAT WIDGET (bindtag path).
    Dipanggil dari semua titik pembuatan widget scrollable.

    KUNCI anti-bentrok (diprobe di Xvfb): dalam SATU bindtag Tk hanya
    memanggil binding TERPILIH SPESIFIK — <Control-MouseWheel> mengalah-
    kan <MouseWheel> polos yang sudah terpasang → CTRL+roda masuk zoom
    TANPA menggulir tabel/log; roda polos tetap menggulir seperti biasa."""
    widget.bind("<Control-MouseWheel>", ctrl_wheel_dispatch)
    widget.bind("<Control-Button-4>", ctrl_wheel_dispatch)
    widget.bind("<Control-Button-5>", ctrl_wheel_dispatch)


def font(size: int = 10, weight: str = "normal") -> tkfont.Font | tuple:
    """Font UI standar — kini NAMED FONT (tkfont.Font) selama root sudah
    ada: satu objek per (size, weight) DI-SHARE lintas widget → zoom
    CTRL+Scroll (set_ui_scale/rescale_named_fonts) menyebarkan ke semua
    pemakai secara HIDUP. Tk menerima objek Font maupun tuple untuk opsi
    font= di semua widget/style/tag. Pre-root (import time) → tuple
    fallback (perilaku defensif v3.9.33 dipertahankan)."""
    f = _named_font("ui", size, weight)
    if f is None:
        return (font_family(), size, weight)
    return f


def mono(size: int = 10) -> tkfont.Font | tuple:
    """Idem font() untuk family monospace (konsol log)."""
    f = _named_font("mono", size, "")
    if f is None:
        return (mono_family(), size)
    return f


# --- Setup ttk style ---------------------------------------------------------
def apply_theme(root: tk.Tk) -> ttk.Style:
    """Pasang tema global ke root window. Dipanggil sekali di startup.

    v3.9.48 — dipanggil ULANG oleh zoomer (app._apply_ui_zoom) saat zoom
    berubah: konfigurasi style bersifat IDEMPOTEN (configure menimpa
    nilai sama) dan font kini NAMED FONT bersama — re-apply membuat
    rowheight tabel (scale_px) + seluruh style ikut zoom tanpa membangun
    ulang widget. Style KUSTOM milik view (dipasang setelah theme) tak
    tersentuh (nama style berbeda).

    Return objek ttk.Style (bisa dipakai untuk kustomisasi lanjutan).
    """
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    fam = font_family()

    # --- Base widgets --- (v3.9.48: font via pabrik NAMED — ikut zoom)
    style.configure(".", background=C_BG, foreground=C_HEADER,
                    font=font(10), borderwidth=0)
    style.configure("TFrame", background=C_BG, padding=0)
    style.configure("Card.TFrame", background=C_CARD, padding=0)

    style.configure("TLabel", background=C_BG, foreground=C_HEADER, font=font(10))
    style.configure("Card.TLabel", background=C_CARD, foreground=C_HEADER, font=font(10))
    style.configure("CardMuted.TLabel", background=C_CARD, foreground=C_TEXT_MUTED,
                    font=font(9))
    style.configure("Muted.TLabel", background=C_BG, foreground=C_TEXT_MUTED, font=font(9))
    style.configure("Title.TLabel", background=C_CARD, foreground=C_HEADER,
                    font=font(13, "bold"))
    style.configure("Subtitle.TLabel", background=C_CARD, foreground=C_TEXT_MUTED,
                    font=font(10))
    style.configure("Toolbar.TLabel", background=C_HEADER, foreground="#f1f5f9",
                    font=font(11))
    style.configure("ToolbarTitle.TLabel", background=C_HEADER, foreground="#f1f5f9",
                    font=font(12, "bold"))

    # --- Tombol (ghost/default — pakai ttk) ---
    # v3.9 (ala Waste): padding tombol 6px/14px → Tk (14, 7)
    style.configure("TButton", background=C_CARD, foreground=C_HEADER,
                    font=font(10), padding=(14, 7), borderwidth=1,
                    focuscolor=C_CARD)
    style.map("TButton",
              background=[("active", "#f8fafc"), ("disabled", "#f1f5f9")],
              foreground=[("disabled", C_TEXT_SOFT)])

    # --- Notebook (tab) ---
    style.configure("TNotebook", background=C_BG, borderwidth=0,
                    tabmargins=(6, 8, 6, 0))
    # FIX H-1 (audit 2-a — terkonfirmasi Xvfb): padding (18,9)+label
    # spasi-ganda = ±1280px utk 10 tab > minsize 1020px → tab kanan
    # terpotong. Kini (12,9): ±912px — muat dgn margin; tinggi tab tetap.
    style.configure("TNotebook.Tab", background="#e2e8f0", foreground=C_TEXT_MUTED,
                    padding=(12, 9), font=font(10), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", C_CARD), ("active", "#eef2f7")],
              foreground=[("selected", C_HEADER), ("active", C_HEADER)],
              font=[("selected", font(10, "bold"))])
    style.configure("TNotebook.Pane", background=C_BG, borderwidth=0)

    # --- Entry / Combobox ---
    style.configure("TEntry", fieldbackground=C_CARD, foreground=C_HEADER,
                    bordercolor=C_BORDER, insertcolor=C_HEADER, padding=(8, 4))
    style.map("TEntry", bordercolor=[("focus", C_ACCENT)])
    style.configure("TCombobox", fieldbackground=C_CARD, foreground=C_HEADER,
                    bordercolor=C_BORDER, arrowcolor=C_TEXT_MUTED, padding=(8, 4))
    # (font TEntry/TCombobox mengikuti style "." — named font bersama)
    style.map("TCombobox",
              bordercolor=[("focus", C_ACCENT)],
              fieldbackground=[("readonly", C_CARD), ("disabled", "#f8fafc")],
              foreground=[("disabled", C_TEXT_SOFT)])

    # Dropdown list Combobox (via option database)
    # v3.9.48 — font dropdown ikut zoom: option_add di-reset tiap
    # re-apply theme dgn size ter-skala (dropdown dibuat-ulang tiap buka)
    root.option_add("*TCombobox*Listbox.background", C_CARD)
    root.option_add("*TCombobox*Listbox.foreground", C_HEADER)
    root.option_add("*TCombobox*Listbox.selectBackground", C_ACCENT_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", C_ACCENT_DARK)
    root.option_add("*TCombobox*Listbox.font", (fam, scale_pt(10)))

    # --- Checkbutton ---
    style.configure("TCheckbutton", background=C_CARD, foreground=C_HEADER,
                    font=font(10), focuscolor=C_CARD)
    style.map("TCheckbutton",
              background=[("active", C_CARD)],
              indicatorcolor=[("selected", C_ACCENT), ("!selected", "#ffffff")])

    # --- Progressbar ---
    style.configure("Horizontal.TProgressbar", background=C_ACCENT,
                    troughcolor="#e2e8f0", borderwidth=0, thickness=8)

    # --- Scrollbar ---
    style.configure("Vertical.TScrollbar", background="#e2e8f0",
                    troughcolor="#f1f5f9", bordercolor="#f1f5f9",
                    arrowcolor=C_TEXT_MUTED, relief="flat", arrowsize=12)
    style.map("Vertical.TScrollbar", background=[("active", "#cbd5e1")])
    style.configure("Horizontal.TScrollbar", background="#e2e8f0",
                     troughcolor="#f1f5f9", bordercolor="#f1f5f9",
                     arrowcolor=C_TEXT_MUTED, relief="flat", arrowsize=12)
    style.map("Horizontal.TScrollbar", background=[("active", "#cbd5e1")])

    # --- Treeview (tabel utama) ---
    # v3.9 "PERBESAR TABEL" (permintaan user — mirror aplikasi Waste:
    # font tabel 13px + item padding 3px/8px + baris lapang):
    # font 9 → 10, rowheight 26 → 30 — tabel terlihat besar & mudah dibaca.
    # v3.9.48 — rowheight = 30 × zoom (scale_px): font baris membesar via
    # named font; rowheight statis akan MEMPOTONG teks. widgets.
    # _style_rowheight membaca nilai ini tiap invalidate cache.
    style.configure("Treeview", background=ROW_EVEN, fieldbackground=ROW_EVEN,
                    foreground=C_HEADER, rowheight=scale_px(30), font=font(10),
                    bordercolor=C_BORDER, relief="solid")
    style.configure("Treeview.Heading", background="#f8fafc", foreground=C_HEADER,
                    font=font(10, "bold"), relief="flat", bordercolor=C_BORDER,
                    padding=(8, 8))
    style.map("Treeview.Heading", background=[("active", "#e8edf3")])
    style.map("Treeview",
              background=[("selected", C_ACCENT_SOFT)],
              foreground=[("selected", C_ACCENT_DARK)])

    # --- Separator ---
    style.configure("TSeparator", background=C_BORDER)

    return style


# --- Zebra tags helper -------------------------------------------------------
def setup_tree_tags(tree: ttk.Treeview, extra_tags: dict | None = None) -> None:
    """Pasang tag zebra-row + negative standar ke sebuah Treeview.

    extra_tags: dict {tag: {"foreground": ..., "background": ...}} untuk
    pewarnaan spesifik view (status, CEK, dsb).
    v3.9.64 — tag Cari (Ctrl+F) didaftarkan PERTAMA (prioritas create —
    FIX audit 15-c F-01: highlight find harus menang atas zebra/bg view).
    """
    register_find_tags(tree)   # v3.9.64 — WAJIB sebelum tag bg view
    tree.tag_configure("evenrow", background=ROW_EVEN)
    tree.tag_configure("oddrow", background=ROW_ODD)
    tree.tag_configure("negative", foreground=C_RED)
    if extra_tags:
        for tag, cfg in extra_tags.items():
            tree.tag_configure(tag, **cfg)
