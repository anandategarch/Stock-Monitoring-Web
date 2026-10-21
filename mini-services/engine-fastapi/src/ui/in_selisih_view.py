"""
in_selisih_view.py — Tab "📤 Rekap Selisih IN" (v3.4 → v3.6).

v3.9.31 (user: "kolom Kuantitas di Rincian PO masih satuan besar (karton)
bukan satuan kecil (botol) seperti sheet barang masuk — tidak match waktu
cari deviasi murni") — KONVERSI SATUAN PO MENUNGGU:
- Kolom "PO Menunggu" kini menampilkan NILAI TERKONVERSI ke satuan
  terkecil (disetujui user) — apple-to-apple dengan kolom Selisih/Saldo
  (contoh: sisa -120 BOTOL vs PO menunggu 120 BOTOL = match kelihatan;
  dulu 5 KARTON vs -120 BOTOL tersembunyi). Konversi = peta rasio dari
  data transaksi aktual 42.05 ('Rasio Satuan' + '#Sat. Kirim' +
  '#Sat. Terkecil') + 32.24 ('Rasio Satuan' + 'Satuan') — dibangun
  pipeline di memori (konversi_satuan.build_konversi_map via append1
  konversi_out), TANPA file master excel tambahan.
- Catatan "PO Menunggu: PO.xxx (qty 120 BOTOL)" berlabel satuan
  terkecil; pasangan (barang, satuan-PO) tak ada di peta → qty PO
  as-is + penanda '*' (mis. "(qty 5 KARTON*)" — disetujui user).
- Tab 🛒 Rincian PO TETAP menampilkan Kuantitas satuan PO asli (itu
  memang satuan dokumen PO).

v3.9.30 (user: "cek Rincian PO file 32.43 — ada nama resto+barang
dgn status pesanan 'Menunggu diproses'; PO sudah ada tapi penerimaan
belum di-update di sistem → bisa jadi penyebab deviasi murni") — PO
MENUNGGU SEBAGAI PENJELAS DEVIASI MURNI:
- KOLOM BARU "PO Menunggu" (setelah Saldo): total qty PO 32.43
  ber-status 'Menunggu diproses' utk pasangan (resto, barang) baris
  itu (nilai konstanta per pasangan; '-' bila tak ada). Sumber =
  kolom 'Qty PO Menunggu' audit_df (fn_audit._apply_po_menunggu —
  pipeline membaca Rincian PO TANPA filter KATEGORI supaya barang
  non-DEVIASI-master pun PO-nya ikut; join resto = Cabang PO
  '1370.MLGPAR' → 'MLGPAR'). Filterable/sortable seperti kolom lain
  → pasangan ber-PO menunggu bisa diisolasi.
- Catatan "PO Menunggu: PO.xxx (qty n) (+m)" otomatis di-append ke
  Catatan Audit baris DEVIASI MURNI pasangan itu (di fn_audit —
  urutan: catatan VBA | PO Menunggu | catatan app B1-B4) → deviasi
  murni EXPLAINABLE (menunggu PO diproses → resolve saat RI masuk)
  vs yang perlu audit fisik terbedakan SEKILAS PANDANG.
- KPI chip baru "DEV MURNI · PO MENUNGGU" (amber) di antara DEVIASI
  MURNI & SISA GANTUNG (kpi 'dev_murni_po' = jumlah baris DEVIASI
  MURNI ber-PO menunggu varian aktif).
- Kolom ikut ke 💾 Export (opsi "PO Menunggu" di dialog export).

v3.9.27 (user: "pada rekap selisih in bisa mode hitung bulan lalu dan
hanya hitung bulan ini. Tapi default hitung bulan ini aja") — MODE
HITUNG (SegmentBar "MODE HITUNG", baris pertama kartu Filter):
- "📅 Bulan Ini" (DEFAULT): audit = varian BULAN BERJALAN SAJA — baris
  Tanggal negatif (rekap lalu 25..-31 + IN 42.05/32.24 bulan lalu)
  DIBUANG sebelum engine VBA (fn_audit.build_audit_from_app
  bulan_lalu=False) → perilaku identik sheet LAPORAN_DEVIASI workbook
  user (tgl 1..31, tanpa tanggal negatif). Rentang tampil 1..31.
- "📆 Lalu + Ini": audit = varian PENUH (incl. bulan lalu — saldo
  kumulatif menyambung dari 25..31 bulan lalu; perilaku v3.6-v3.9.26).
  Rentang tampil -31..31.
Kedua varian dihitung SEKALI oleh pipeline (kunci audit_result
"df"/"kpi"/"desc" + "df_bulan_ini"/"kpi_bulan_ini"/"desc_bulan_ini");
mode hanya MEMILIH varian (tanpa recompute). KPI chips + Saldo + Hasil
Audit ikut varian aktif. Ketik rentang tanggal negatif di mode Bulan
Ini → otomatis pindah ke Lalu + Ini (baris bulan lalu memang tidak ada
di varian bulan-ini — tanpa auto-switch tabel akan kosong senyap).
✕ Reset Filter & data baru → kembali ke default "Bulan Ini".
Keputusan: varian bulan-ini kehilangan pembanding "SO tanggal 1 = SO
bulan lalu terakhir" (v3.9.6 — engine melihat baris pertama bulan
berjalan sebagai awal grup) — inheren: pilih mode "📆 Lalu + Ini" bila
perlu pembanding bulan lalu. Export "Laporan Deviasi (Audit)" level
app TETAP varian penuh (kunci "df" tidak berubah).

v3.9.24 (klarifikasi user: periode bisnis 26→25) — RI BALANCING kini
TANGGAL-AWARE: satu periode = tgl 26 bulan lalu s/d tgl 25 bulan ini
(dua bulan kalender); PO bulan SEBELUM bulan RI tetap satu periode →
TIDAK dihitung balancing (dulu salah-flag). Logika = doc_codes.
_ri_balancing(nomor, po, tanggal).

v3.9.23 (user: "kerjakan semua poin B") — CATATAN AUDIT OTOMATIS:
kolom Catatan Audit diperkaya catatan app per baris, di-APPEND ke
catatan engine VBA (dipisah " | " — catatan VBA asli tetap PERTAMA,
isi lama tidak berubah; baris tanpa temuan tetap sendirian):
- B1 "RI Balancing: RI.2026.10.10354 (PO 2026-08)" — dokumen IN baris
  itu ber-periode PO di luar periode bisnis RI-nya (logika sama popup
  v3.9.19, kini modul bersama doc_codes.py);
- B2 "Nomor dobel: IT.2026.09.00123 ×2" — nomor dokumen sama muncul
  >1 baris utk pasangan yang sama (input ganda / sheet kembar);
- B3 "Selisih IN −3 (IN 13 > BM 10)" — BM ≠ IN dgn arah perbedaan;
- B4 "BM 0 padahal IN 13 (input rekap belum diisi)" — data quality
  (mirror temuan audit 37-a R1: workbook gabungan user tanpa baris BM).
Catatan ikut ke 💾 Export (kolom Catatan Audit sudah termasuk
AUDIT_EXPORT_COLUMNS). Helper kode dokumen diangkat ke doc_codes.py
(re-export nama lama — test §29/§30 tetap jalan).

Permintaan user (v3.4): "Tambah 1 tab lagi untuk rekap Selisih IN dan kolom
Resto, tanggal, nama barang, satuan, IN, Barang masuk dan selisih IN
dan bisa drill down atau pop up muncul rincian IN yaitu 42.05, 3224,
dan 9901 beserta nomor nya.
v3.9.17: sumber IN tambahan "42.05 (Bulan Lalu)" — folder
"4.1 4205 Bulan Lalu" (penambah IN periode ujung bulan lalu, mirror
32.24 bulan lalu).
v3.9.19: popup Rincian IN punya KOLOM CEK — "RI Balancing" bila
Nomor PO di luar periode bisnis RI-nya (v3.9.24; dulu: bulan Nomor
RI ≠ bulan Nomor PO) (struktur kode PO.2026.08.00571 /
RI.2026.10.10354: segmen 2 = tahun, segmen 3 = bulan; permintaan user:
RI dibuat beda bulan dari PO-nya = entries balancing).
FIX 35-c1: periode dibandingkan PENUH (tahun, bulan) — bulan sama
beda tahun = periode beda → tetap "RI Balancing"; bulan 1-2 digit
dibandingkan numerik.
v3.9.20 (deep audit 34-c+34-e/fix 35-c1): clone ⛶ reapply tag neg
per-cell (on_render_done — dulu minus kehilangan warna di Layar
Penuh) + buang literal None/nan/NaT dari daftar nilai popup filter.

v3.6 (permintaan user: "audit rekonsiliasi tidak perlu ambil dari sheet
29 — aplikasikan logika nya dengan tambah kolom SO dan kolom hasil audit
nya, bisa difilter"):
- SATU tabel (segment Ringkas|Audit dihapus) — baris per (Resto, Tanggal,
  Barang) dihitung pipeline fn_audit dari DATA APP (rekap SO + BARANG
  MASUK + IN per tanggal; sheet '29 Rekap Barang Masuk' TIDAK dibaca):
    IN            = Penerimaan Sistem (Accurate: 42.05 + 32.24 + 99.01
                    — incl. 42.05/32.24 bulan lalu, v3.9.17)
    Barang Masuk  = Qty SO Harian (input rekap JENIS='BARANG MASUK')
    Selisih IN    = Barang Masuk − IN
    Hasil SO      = kolom SO (rekap JENIS='SO'; hadir hanya di tanggal
                    yang SO benar-benar direkam — sel '-' = tidak ada SO)
    Saldo         = saldo kumulatif per (Resto × Barang) urut tanggal
    Hasil Audit   = port macro VBA BuatLaporanDeviasiSampel — VALID
                    (Sistem Masuk) / OK (Matching) / CUT-OFF RESOLVED /
                    OK (Dalam Cut-off) / DEVIASI MURNI
- Semua kolom difilter via header ⧩ (display-only: saldo & status
  dihitung dari data penuh, tidak terpotong rentang tanggal).
- v3.6: klik kanan heading / tombol ◱ Kolom = sembunyikan/tampilkan
  kolom; window ⛶ punya filter + sort sendiri.

Drill-down (double-click baris) → popup RINCIAN IN per dokumen:
  - ringkasan per sumber: 42.05 / 32.24 / 99.01 (+ 42.05 & 32.24 bulan lalu)
  - tabel dokumen: Source | Nomor | Nomor PO | Qty | #Tgl/Jam
  - copy Nomor (klik kanan / double-click cell / tombol Semua Nomor)
  - ⛶ Perbesar + ↔ Auto-Fit + Esc

Tanggal -25..-31 = data bulan lalu (selalu terbaca — LightMode dihapus v3.5).
v3.8: Default rentang 1 s/d 31 = periode BULAN BERJALAN saja (tanpa
bulan lalu — permintaan user "rekap selisih in hanya periode 1-31";
v3.9.27: kini bagian dari MODE HITUNG "📅 Bulan Ini" — audit varian
ikut, bukan sekadar filter tampilan).
v3.6 (lama): default -26 s/d 31.
"""
import contextlib
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

import pandas as pd

from .doc_codes import (
    _doc_code_str,  # v3.9.23 — helper kode dokumen diangkat ke modul
    _doc_month,  # noqa: F401 — re-export nama lama (test §29/§30)
    _doc_period,  # bersama doc_codes (logika RI Balancing tidak
    _ri_balancing,  # diduplikasi antar view; dipakai juga deviasi_view)
    duplicated_doc_numbers,
)
from .export_sheets import (
    AUDIT_EXPORT_COLUMNS,
    build_selisih_export_df,
    write_selisih_sheet,
)
from .theme import (
    C_ACCENT_DARK,
    C_BG,
    C_CARD,
    C_HEADER,
    C_TEXT_MUTED,
    font,
    register_find_tags,
)
from .widgets import (
    CELL_TAGS_SUPPORTED,
    FLASH_MS,  # v3.9.59 — kanon durasi status flash (bonus, agent B)
    KATEGORI_REKAP_VALUES,  # v3.9.49 — default kategori Rekap Mentah
    Card,
    ColumnManager,
    EmptyState,
    GhostButton,
    HeaderFilterGroup,
    LoadingOverlay,
    SegmentBar,
    TableExpander,
    _filter_value_sort_key,
    apply_cell_tag,
    apply_col_sel_restore,  # v3.9.66 — filter persisten antar sesi
    attach_clone_filters,
    auto_fit_columns,
    autofit_tree_once,  # v3.9.55 — F8
    col_sel_to_json,  # v3.9.66 — filter persisten antar sesi
    enable_col_resize,
    enable_multi_select,
    enable_smooth_wheel_list,  # v3.9.60 — leaderboard rekap ber-scroll
    fmt_int_id,
    identify_to_column,
    insert_tree_items,
    install_tree_find_binding,  # v3.9.64 — F-07: Ctrl+F aktif di popup
    open_tree_maximized,
    reset_autofit_once,  # v3.9.55 — F8
    run_async,
    sort_tree_by_column,
    validated_tgl_entry,
    zero_row_filter_message,  # v3.9.68 — pesan jujur 0-baris (⧩ kosong)
)

# --- Kolom tabel (v3.6: SATU tabel — Ringkas + Audit digabung) -------------
# v3.9.30 — KOLOM BARU 'PO Menunggu' (setelah Saldo): total qty PO
# 32.43 ber-status 'Menunggu diproses' utk pasangan (resto, barang)
# itu — penjelas deviasi murni (PO sudah dibuat, penerimaan/RI belum
# di-update sistem → selisih gantung akan resolve saat PO diproses).
# Nilai konstanta per pasangan; baris DEVIASI MURNI pasangan itu juga
# dapat catatan 'PO Menunggu: PO.xxx (qty n)' (fn_audit, ikut export).
COLUMNS = [
    ("Resto", 74, "w"),
    ("Tanggal", 64, "e"),
    ("Nama Barang", 200, "w"),
    ("KATEGORI", 110, "w"),
    ("Satuan", 56, "w"),
    ("Hasil SO", 90, "e"),         # ← kolom SO (v3.6)
    ("Barang Masuk", 110, "e"),    # = Qty SO Harian (input rekap)
    ("IN", 96, "e"),               # = Penerimaan Sistem (42.05+32.24+99.01)
    ("Selisih IN", 100, "e"),      # = Barang Masuk − IN
    ("Saldo", 100, "e"),           # saldo kumulatif audit
    ("PO Menunggu", 96, "e"),      # v3.9.30 — qty PO 32.43 'Menunggu diproses'
    ("Hasil Audit", 150, "w"),     # ← kolom hasil audit (v3.6)
    ("Catatan Audit", 260, "w"),
]

_ALL_COLS = [c[0] for c in COLUMNS]

# Kolom numerik (utk format & filter nilai)
_NUM_COLS = {"Hasil SO", "Barang Masuk", "IN", "Selisih IN", "Saldo",
             "PO Menunggu"}

# Warna status — mirror conditional formatting VBA (soft colors)
_STATUS_TAG = {
    "OK (Matching)": "st_ok",
    "OK (Dalam Cut-off)": "st_ok",
    "VALID (Sistem Masuk)": "st_valid",
    "CUT-OFF RESOLVED": "st_cutoff",
    "DEVIASI MURNI": "st_dev",
}
_STATUS_TAG_CFG = {
    # hijau soft — OK (RGB 226,239,218 / 55,86,35)
    "st_ok": {"background": "#e2efda", "foreground": "#375623"},
    # biru soft executive — VALID (RGB 222,235,247 / 31,78,120)
    "st_valid": {"background": "#deebf7", "foreground": "#1f4e78"},
    # kuning soft — CUT-OFF (RGB 255,242,204 / 128,96,0)
    "st_cutoff": {"background": "#fff2cc", "foreground": "#806000"},
    # merah soft — DEVIASI MURNI (RGB 252,228,214 / 198,89,17)
    "st_dev": {"background": "#fce4d4", "foreground": "#c65911"},
}

# Urutan sumber IN di popup rincian (+ warna chip ringkasan)
_SOURCES = [
    ("42.05", "#b45309"),              # amber — pemindahan/SJ
    ("42.05 (Bulan Lalu)", "#0e7490"), # teal — pemindahan bulan lalu (v3.9.17)
    ("32.24", "#2563eb"),              # biru — rincian penerimaan/RI
    ("32.24 (Bulan Lalu)", "#7c3aed"), # ungu — RI bulan lalu
    ("99.01", "#9C5700"),              # oranye — pembelian tanpa penerimaan
]

_POPUP_COLUMNS = [
    ("Source", 130, "w"),
    ("Nomor", 160, "w"),
    ("Nomor PO", 160, "w"),
    ("CEK", 110, "w"),            # v3.9.19 — "RI Balancing"
    ("Qty", 90, "e"),
    ("#Tgl/Jam Pembuatan IT", 150, "w"),
]
_POPUP_IDS = [c[0] for c in _POPUP_COLUMNS]

# v3.9.19 — struktur kode dokumen: PREFIKS.TAHUN.BULAN.NOMOR — kini
# tidak di sini (diangkat ke modul bersama .doc_codes v3.9.23 supaya
# logika RI Balancing TIDAK diduplikasi antar view; re-import di atas).


def _tgl_key(t):
    """v3.9.23 — kunci tanggal numerik utk catatan audit (NaN → None;
    int supaya 25.0 == 25 cocok dgn key dict)."""
    try:
        if pd.isna(t):
            return None
    except (TypeError, ValueError):
        return None
    try:
        return int(float(t))
    except (TypeError, ValueError):
        return None


def _join_notes(vba: str, notes) -> str:
    """v3.9.23 (poin B) — gabung catatan engine VBA + catatan otomatis
    app: VBA tetap PERTAMA (isi lama tidak berubah), catatan app
    di-append dipisah ' | '. Catatan VBA '-' dianggap kosong."""
    vba = str(vba).strip() if vba is not None else ""
    if not notes:
        return vba
    app = " | ".join(notes)
    if vba in ("", "-", "nan", "None"):
        return app
    return f"{vba} | {app}"


def _ri_balancing_by_date(in_detail: pd.DataFrame | None) -> dict:
    """v3.9.23 (poin B1) — dokumen RI Balancing per
    {(barang, resto): {tgl: [(nomor, po_period), ...]}} — nomor dokumen
    RI ber-periode PO di luar periode bisnisnya (v3.9.24: 26→25 —
    PO bulan SEBELUM RI tetap satu periode, tak dihitung) + periode
    PO-nya ("2026-08"), dikelompokkan PER TANGGAL dokumennya (catatan
    menempel pada baris tabel bertanggal sama; urut nomor). Logika
    periode = _ri_balancing (doc_codes, tanggal-aware)."""
    out: dict = {}
    if in_detail is None or getattr(in_detail, "empty", True):
        return out
    need = {"Nomor", "Nomor PO", "Nama Barang", "NAMA RESTO", "Tanggal"}
    if not need <= set(getattr(in_detail, "columns", [])):
        return out
    for nomor, nomor_po, b, r, t in zip(in_detail["Nomor"],
                                        in_detail["Nomor PO"],
                                        in_detail["Nama Barang"],
                                        in_detail["NAMA RESTO"],
                                        in_detail["Tanggal"]):
        if _ri_balancing(nomor, nomor_po, t) == "":
            continue
        n = _doc_code_str(nomor)
        if not n:
            continue
        tkey = _tgl_key(t)
        if tkey is None:
            continue
        p_po = _doc_period(nomor_po)
        po_txt = (f" (PO {p_po[0]:04d}-{p_po[1]:02d})"
                  if p_po is not None else "")
        per_pair = out.setdefault((str(b), str(r)), {})
        lst = per_pair.setdefault(tkey, [])
        item = (n, po_txt)
        if item not in lst:
            lst.append(item)
    for per_pair in out.values():
        for lst in per_pair.values():
            lst.sort()
    return out


def _duplicated_doc_dates(in_detail: pd.DataFrame | None,
                          dup: dict) -> dict:
    """v3.9.23 (poin B2) — tanggal kemunculan nomor dobel: dari hasil
    duplicated_doc_numbers (pasangan → {nomor: jumlah}), petakan ke
    {(barang, resto): {tgl: [(nomor, jumlah), ...]}} supaya catatan
    "Nomor dobel" menempel pada baris tabel bertanggal dokumen itu
    (urut nomor)."""
    out: dict = {}
    if in_detail is None or getattr(in_detail, "empty", True) or not dup:
        return out
    need = {"Nomor", "Nama Barang", "NAMA RESTO", "Tanggal"}
    if not need <= set(getattr(in_detail, "columns", [])):
        return out
    d = in_detail[in_detail["Nomor"].notna()].copy()
    if d.empty:
        return out
    d["_nomor"] = d["Nomor"].map(_doc_code_str)
    d = d[d["_nomor"].ne("")]
    if d.empty:
        return out
    d["_tgl"] = d["Tanggal"].map(_tgl_key)
    d = d[d["_tgl"].notna()]
    for (b, r), nomors in dup.items():
        sub = d[(d["Nama Barang"].astype(str) == str(b))
                & (d["NAMA RESTO"].astype(str) == str(r))
                & (d["_nomor"].isin(nomors))]
        if sub.empty:
            continue
        for t, nomor in zip(sub["_tgl"], sub["_nomor"]):
            out.setdefault((str(b), str(r)), {}).setdefault(
                int(t), []).append((str(nomor), int(nomors[str(nomor)])))
    for per_pair in out.values():
        for lst in per_pair.values():
            lst.sort()
            # dedup (dokumen dobel muncul di >1 tanggal → tiap tanggal
            # cukup satu entri)
            seen = set()
            lst[:] = [x for x in lst if not (x[0] in seen or seen.add(x[0]))]
    return out


def _fmt_num(val) -> str:
    """Format angka: 0 → '-', ribuan koma, negatif dalam kurung (merah via tag)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "-"
    try:
        if pd.isna(val):
            return "-"
    except (TypeError, ValueError):
        pass
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


def _raw_num(arr, i):
    """FIX 6d2-01 — nilai numerik MENTAH kolom numpy (None bila kolom tak
    ada / NaN/invalid) — utk chip ringkasan popup Rincian IN: nilai display
    diformat _fmt_num Indonesia ('1.500') dan TIDAK boleh di-parse ulang
    dengan float EN (1.5 — salah skala 1000×)."""
    if arr is None:
        return None
    try:
        v = arr[i]
        if pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError, IndexError):
        return None


def _fmt_int(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        return str(int(val))
    except (TypeError, ValueError):
        return str(val)


def _fmt_jam(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y %H:%M:%S")
    try:
        return pd.to_datetime(val).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(val)


def _format_col_values(col: str, series: pd.Series) -> pd.Series:
    """Format satu kolom DataFrame → string tampilan (dipakai filter header
    & render — nilai filter selalu identik dgn yang tampil di tabel)."""
    if col == "Tanggal":
        return series.map(_fmt_int)
    if col in _NUM_COLS:
        return series.map(_fmt_num)
    return series.astype(str)


# =============================================================================
# POPUP RINCIAN IN (drill-down)
# =============================================================================

class InDetailPopup(tk.Toplevel):
    """Popup rincian IN per (Resto, Barang, Tanggal): breakdown dokumen
    42.05 / 32.24 / 99.01 (+ 42.05 & 32.24 bulan lalu) beserta nomornya."""

    def __init__(self, parent, resto: str, barang: str, tanggal,
                 detail_df: pd.DataFrame, row_summary: dict | None = None):
        super().__init__(parent)
        tgl_txt = _fmt_int(tanggal)
        self.title(f"Rincian IN — {barang} · {resto} · Tgl {tgl_txt}")
        try:
            pw, ph = 1000, 560   # v3.9.19: 880 → 1000 (kolom CEK baru)
            px = parent.winfo_rootx() + (parent.winfo_width() - pw) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - ph) // 2
            self.geometry(f"{pw}x{ph}+{max(px, 0)}+{max(py, 0)}")
        except Exception:
            self.geometry("1000x560")
        self.minsize(700, 340)
        self.configure(bg=C_BG)
        self.transient(parent)
        self.grab_set()

        self.detail_df = detail_df
        self._flash_after = None
        self._base_status = ""
        self._render_df: pd.DataFrame = detail_df
        # v3.9.2: minus merah PER CELL (kolom Qty) — fallback Tk 8 per baris
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        self._cek_cells: list = []   # v3.9.19 — sel CEK "RI Balancing"

        self._build_ui(barang, resto, tgl_txt, row_summary)
        self._render()
        self.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        # v3.9.42 — audit 61-c/61-d (F6 P3): timer flash status dibatalkan
        # saat popup di-destroy — restore 3 dtk tak pernah mendarat di
        # widget yang sudah mati (traceback noise di log).
        def _cancel_flash(_e):
            if self._flash_after:
                with contextlib.suppress(tk.TclError):
                    self.after_cancel(self._flash_after)
                self._flash_after = None
        self.bind("<Destroy>", _cancel_flash, add="+")

    # ---------------------------------------------------------------- UI ----
    def _build_ui(self, barang, resto, tgl_txt, row_summary):
        # --- Header band gelap ---
        header = tk.Frame(self, bg=C_HEADER)
        header.pack(fill="x")
        head_in = tk.Frame(header, bg=C_HEADER)
        head_in.pack(fill="x", padx=16, pady=12)
        tk.Label(head_in, text="📥 Rincian IN — dokumen pendukung",
                 bg=C_HEADER, fg="#5eead4", font=font(8, "bold")).pack(anchor="w")
        tk.Label(head_in,
                 text=f"{barang} · {resto} · Tanggal {tgl_txt}",
                 bg=C_HEADER, fg="#f1f5f9", font=font(12, "bold"),
                 wraplength=700, justify="left").pack(anchor="w", pady=(2, 0))

        btn_fit = tk.Button(
            head_in, text="↔ Auto-Fit", command=lambda: auto_fit_columns(self.tree),
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
            activeforeground="#ffffff", bd=0, relief="flat",
            highlightthickness=0, cursor="hand2", font=font(9, "bold"),
            padx=12, pady=5)
        btn_fit.pack(side="right", anchor="ne", padx=(0, 6))
        btn_max = tk.Button(
            head_in, text="⛶ Layar Penuh", command=self._maximize,
            bg="#1e293b", fg="#e2e8f0", activebackground="#334155",
            activeforeground="#ffffff", bd=0, relief="flat",
            highlightthickness=0, cursor="hand2", font=font(9, "bold"),
            padx=12, pady=5)
        btn_max.pack(side="right", anchor="ne")

        # --- Ringkasan per sumber (chips) ---
        sum_card = tk.Frame(self, bg=C_CARD, highlightbackground="#e2e8f0",
                            highlightthickness=1)
        sum_card.pack(fill="x", padx=12, pady=(12, 0))
        chips = tk.Frame(sum_card, bg=C_CARD)
        chips.pack(fill="x", padx=12, pady=10)

        df = self.detail_df
        totals = {}
        if df is not None and not df.empty and "SOURCE IN" in df.columns:
            g = df.groupby("SOURCE IN")["Value"].sum()
            totals = {k: float(v) for k, v in g.items()}
        total_in = sum(totals.values())
        # v3.9.59 — FIX 2e-01: 8 chip ringkasan dibungkus GRID 4-per-baris
        # (deterministik 2 baris). Dulu 8× pack side="left" SATU baris →
        # di popup minsize 700 lebar total chip (~786px+) MELUAP: chip
        # 'BARANG MASUK' terpotong sebagian & chip 'SELISIH IN' (angka
        # inti drill-down) SELURUHNYA tak terlihat tanpa indikasi.
        chip_specs = [(f"{src}", totals.get(src, 0.0), color)
                      for src, color in _SOURCES]
        chip_specs.append(("IN TOTAL", total_in, C_ACCENT_DARK))
        if row_summary:
            chip_specs.append(
                ("Barang Masuk", row_summary.get("bm", 0.0), "#006100"))
            chip_specs.append(
                ("Selisih IN", row_summary.get("selisih", 0.0),
                 "#dc2626"))
        _last_row = (len(chip_specs) - 1) // 4
        for _i, (_lab, _val, _col) in enumerate(chip_specs):
            self._chip(chips, _lab, _val, _col,
                       row=_i // 4, col=_i % 4, last_row=_last_row)

        # --- Tabel dokumen ---
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        card = tk.Frame(body, bg=C_CARD, highlightbackground="#e2e8f0",
                        highlightthickness=1)
        card.pack(fill="both", expand=True)
        cin = tk.Frame(card, bg=C_CARD)
        cin.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(cin, columns=_POPUP_IDS, show="headings",
                                 selectmode="extended")
        for col_name, width, anchor in _POPUP_COLUMNS:
            self.tree.column(col_name, width=width, minwidth=50, anchor=anchor)
            self.tree.heading(col_name, text=col_name)
        vsb = ttk.Scrollbar(cin, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(cin, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        cin.grid_rowconfigure(0, weight=1)
        cin.grid_columnconfigure(0, weight=1)

        self._setup_tags(self.tree)
        # v3.9.64 — FIX (audit 15-c F-07): Ctrl+F aktif DI DALAM popup
        # (Toplevel sendiri — bindtag-nya tak memuat binding root app).
        install_tree_find_binding(self, lambda: self.tree)
        # v3.4: drag tepi heading = resize; double-click tepi = auto-fit
        # (dipasang SEBELUM interaksi lain supaya "break" efektif)
        enable_col_resize(self.tree)
        enable_multi_select(self.tree)  # v3.9.32

        self.overlay = LoadingOverlay(cin, "Menyiapkan rincian…")

        # interaksi copy
        self.tree.bind("<Button-3>", self._on_context_menu, add="+")  # FIX B-04
        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04

        # --- Footer ---
        foot = tk.Frame(self, bg=C_BG)
        foot.pack(fill="x", padx=12, pady=(0, 12))
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(foot, textvariable=self.status_var,
                                     bg=C_BG, fg=C_TEXT_MUTED, font=font(9))
        self.status_label.pack(side="left")
        btn_copy = GhostButton(foot, text="📋 Semua Nomor",
                               command=lambda: self._copy_all_unique())
        btn_copy.pack(side="right", padx=(6, 0))
        from .widgets import AccentButton
        AccentButton(foot, text="Tutup (Esc)", command=self.destroy).pack(
            side="right", padx=(6, 0))

    def _chip(self, parent, label, value, color, row=0, col=0,
              last_row=0):
        """Chip ringkasan — GRID 4-per-baris (v3.9.59 FIX 2e-01; dulu
        pack side="left" tanpa wrap → terpotong di lebar popup minimum)."""
        box = tk.Frame(parent, bg="#f1f5f9", highlightbackground="#e2e8f0",
                       highlightthickness=1)
        box.grid(row=row, column=col, padx=(0, 8),
                 pady=(0, 6 if row < last_row else 0), sticky="w")
        tk.Label(box, text=label.upper(), bg="#f1f5f9", fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(box, text=_fmt_num(value), bg="#f1f5f9", fg=color,
                 font=font(11, "bold")).pack(anchor="w", padx=10, pady=(0, 6))

    def _setup_tags(self, tree=None):
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("neg_cell", foreground="#dc2626")  # v3.9.2
        # v3.9.19 — CEK "RI Balancing" (amber)
        tree.tag_configure("cek_ri_bal", foreground="#b45309")
        tree.tag_configure("subtotal", background="#f1f5f9",
                           foreground=C_HEADER)

    # ------------------------------------------------------------- RENDER ---
    def _render(self, sync: bool = True):
        df = self.detail_df
        self.tree.delete(*self.tree.get_children())
        if df is None or df.empty:
            self._base_status = "Tidak ada dokumen IN untuk kombinasi ini."
            self.status_var.set(self._base_status)
            return

        items = []
        n_docs = 0
        neg_cells = []   # v3.9.2 — per-cell minus (kolom Qty)
        cek_cells = []   # v3.9.19 — per-cell CEK "RI Balancing"
        subtotal_rows = []
        for src, _color in _SOURCES:
            sub = df[df["SOURCE IN"] == src]
            if sub.empty:
                continue
            sub = sub.sort_values(["Nomor", "Value"],
                                  ascending=[True, False],
                                  na_position="last")
            i = 0
            for _r, row in sub.iterrows():
                qty = row.get("Value")
                qty_txt, is_neg = _fmt_num(qty), (pd.notna(qty) and qty < 0)
                tags = []
                if is_neg:
                    # v3.9.2: minus merah PER CELL (kolom Qty saja) —
                    # sebelumnya satu nilai minus membuat SELURUH BARIS merah
                    if self._cell_tags:
                        neg_cells.append((f"doc_{len(items)}", "Qty"))
                    else:
                        tags.append("negative")
                # v3.9.19 — CEK "RI Balancing" (v3.9.24: periode
                # bisnis 26→25 tanggal-aware — PO bulan sebelum RI
                # tetap satu periode, tak dihitung)
                cek = _ri_balancing(row.get("Nomor"), row.get("Nomor PO"),
                                    row.get("Tanggal"))
                if cek and self._cell_tags:
                    cek_cells.append((f"doc_{len(items)}", "CEK"))
                tags.append("evenrow" if i % 2 == 0 else "oddrow")
                items.append(("", f"doc_{len(items)}", {
                    "values": (
                        str(row.get("SOURCE IN") or ""),
                        str(row.get("Nomor") or "") if pd.notna(row.get("Nomor")) else "",
                        str(row.get("Nomor PO") or "") if pd.notna(row.get("Nomor PO")) else "",
                        cek,
                        qty_txt,
                        _fmt_jam(row.get("#Tgl/Jam Pembuatan IT")),
                    ),
                    "tags": tuple(tags),
                }))
                n_docs += 1
                i += 1
            # baris subtotal per sumber
            subtotal_rows.append((len(items), f"TOTAL {src}",
                                  float(sub["Value"].sum())))

        # sisipkan subtotal mundur supaya index stabil
        for pos, label, total in reversed(subtotal_rows):
            items.insert(pos, ("", f"sub_{pos}", {
                "values": (label, "", "", "", _fmt_num(total), ""),
                "tags": ("subtotal",),
            }))
        if items:
            total_in = float(df["Value"].sum())
            items.append(("", "grand_total", {
                "values": ("TOTAL IN", "", "", "", _fmt_num(total_in), ""),
                "tags": ("subtotal",),
            }))

        self._base_status = (f"{n_docs} dokumen · "
                             f"Total IN: {_fmt_num(df['Value'].sum())}")
        self.status_var.set(self._base_status)
        self._neg_cells = neg_cells
        self._cek_cells = cek_cells   # v3.9.19

        def _done():
            # v3.9.2: pasang tag PER-CELL setelah semua baris ter-insert
            self._reapply_cell_tags(self.tree)

        insert_tree_items(self.tree, items, batch=400, on_done=_done)

    def _reapply_cell_tags(self, tree):
        """v3.9.2 — pasang ulang tag per-cell minus (juga utk clone ⛶);
        v3.9.19 — + sel CEK "RI Balancing" (amber).
        v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus (list kosong
        = clear overlay)."""
        if self._cell_tags:
            apply_cell_tag(tree, "neg_cell", self._neg_cells)
            apply_cell_tag(tree, "cek_ri_bal", self._cek_cells)

    # --------------------------------------------------------------- COPY ---
    def _copy_to_clipboard(self, text, label: str = "Nomor"):
        text = str(text or "").strip()
        if not text:
            self._flash_status("⚠ Tidak ada yang bisa di-copy (nilai kosong).")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        shown = text if len(text) <= 60 else text[:60] + "…"
        self._flash_status(f"📋 {label} TERSALIN: {shown}")

    def _flash_status(self, msg: str):
        if self._flash_after:
            try:
                self.after_cancel(self._flash_after)
            except Exception:
                pass
        self.status_var.set(msg)
        self.status_label.configure(fg=C_ACCENT_DARK)

        def restore():
            # v3.9.42 — audit 61-c/61-d (F6 P3): popup bisa sudah di-destroy
            # saat timer 3 dtk mendarat (user tutup/Esc) — dulu restore
            # menyentuh widget mati → traceback noise di log konsol.
            if not self.winfo_exists():
                return
            self.status_var.set(self._base_status)
            self.status_label.configure(fg=C_TEXT_MUTED)

        # v3.9.59 — bonus (flag agent B): literal 3000 → FLASH_MS kanon
        # (widgets) supaya durasi flash seragam antar permukaan.
        self._flash_after = self.after(FLASH_MS, restore)

    def _on_context_menu(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            return
        try:
            tree.selection_set(iid)
            tree.focus(iid)
        except Exception:
            pass
        values = tree.item(iid, "values")
        if not values:
            return
        row = dict(zip(_POPUP_IDS, values))
        nomor = str(row.get("Nomor", "") or "")
        menu = tk.Menu(tree, tearoff=0)
        if nomor:
            menu.add_command(label=f"📋 Copy Nomor: {nomor[:40]}",
                             command=lambda: self._copy_to_clipboard(nomor))
        po = str(row.get("Nomor PO", "") or "")
        if po:
            menu.add_command(label=f"📋 Copy Nomor PO: {po[:40]}",
                             command=lambda: self._copy_to_clipboard(po, "Nomor PO"))
        menu.add_separator()
        menu.add_command(label="📋 Copy baris (tab-separated)",
                         command=lambda: self._copy_row(values))
        if nomor or po:
            menu.add_separator()
        if nomor:
            menu.add_command(label="Copy SEMUA Nomor unik",
                             command=self._copy_all_unique)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_row(self, values):
        self._copy_to_clipboard("\t".join(str(v) for v in values), "Baris")

    def _on_double_click(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            return
        # v3.7 FIX (deep audit): resolve posisi-display → NAMA kolom
        # aktual — dulu index posisi ke _POPUP_IDS (urutan LOGIS) → setelah
        # kolom disembunyikan (clone ⛶ punya ColumnManager), double-click
        # men-copy nilai kolom yang SALAH.
        col = tree.identify_column(event.x)
        col_name = identify_to_column(tree, col)
        if col_name in ("Nomor", "Nomor PO"):
            val = tree.set(iid, col_name)
            if val:
                self._copy_to_clipboard(val, col_name)
                return
        # double-click baris biasa → copy Nomor (bila ada)
        nomor = tree.set(iid, "Nomor")
        if nomor:
            self._copy_to_clipboard(nomor, "Nomor")

    def _copy_all_unique(self):
        df = self._render_df
        if df is None or df.empty or "Nomor" not in df.columns:
            self._flash_status("⚠ Tidak ada Nomor untuk di-copy.")
            return
        vals = [str(v) for v in df["Nomor"].dropna().astype(str)
                if str(v).strip()]
        uniq = list(dict.fromkeys(vals))
        if not uniq:
            self._flash_status("⚠ Tidak ada Nomor untuk di-copy.")
            return
        self._copy_to_clipboard("\n".join(uniq),
                                f"{len(uniq)} Nomor unik")

    # ---------------------------------------------------------- PERBESAR ---
    def _maximize(self):
        return open_tree_maximized(
            self.tree, f"Rincian IN — {self.title().replace('Rincian IN — ', '')}",
            setup_tags=lambda t: self._setup_tags(t),
            on_context_menu=self._on_context_menu,
            on_render_done=self._reapply_cell_tags)  # v3.9.2 per-cell


# =============================================================================
# VIEW UTAMA — Rekap Selisih IN (Ringkas + Audit Rekonsiliasi)
# =============================================================================

class InSelisihView(tk.Frame):
    """Rekap Selisih IN + Audit Rekonsiliasi (v3.6: logika macro VBA × data
    app — tanpa sheet 29; SATU tabel dgn kolom SO & Hasil Audit yang bisa
    difilter lewat header ⧩)."""

    def __init__(self, parent, go_to_proses: Callable | None = None):
        super().__init__(parent, bg=C_BG)
        self.data: Optional[pd.DataFrame] = None
        self.in_detail: Optional[pd.DataFrame] = None
        self.audit_df: Optional[pd.DataFrame] = None
        self.audit_kpi: dict = {}
        self.audit_desc: str = ""
        # v3.9.27 — MODE HITUNG (user: "pada rekap selisih in bisa mode
        # hitung bulan lalu dan hanya hitung bulan ini. Tapi default hitung
        # bulan ini aja"):
        # - False (DEFAULT, "📅 Bulan Ini")   : audit varian BULAN BERJALAN
        #   SAJA (baris Tanggal negatif dibuang engine — mirror sheet
        #   LAPORAN_DEVIASI tgl 1..31) + rentang 1..31.
        # - True  ("📆 Lalu + Ini")           : audit varian PENUH
        #   (incl. bulan lalu — saldo menyambung) + rentang -31..31.
        # Kedua varian dihitung pipeline SEKALI (kunci audit_result
        # "df"/"df_bulan_ini") — mode hanya MEMILIH, tanpa recompute.
        self._mode_bulan_lalu = False
        self._audit_full: tuple | None = None      # (df, kpi, desc)
        self._audit_bulan_ini: tuple | None = None  # idem, tanpa bulan lalu
        self.go_to_proses = go_to_proses
        self._col_sel: dict = {c: None for c in _ALL_COLS}   # header filter ⧩
        self._busy = False
        self._pending = False
        self._dirty = False            # lazy refresh (ala v3.2)
        self._cached_base: pd.DataFrame | None = None
        # FIX D-01 (audit 2-d): identitas data pemilik _cached_base —
        # mencegah worker menempel base data LAMA dengan label data BARU.
        self._cached_base_data = None
        self._cached_base_detail = None   # v3.9.23 (poin B)
        # v3.9.33 — AUDIT FIX (48-e FIX 6): identitas VARIAN audit pemilik
        # _cached_base — MODE HITUNG menukar audit_df TANPA mengganti objek
        # data/in_detail; tanpa identitas ini worker in-flight dapat
        # menulis ulang cache varian LAMA setelah reset mode (tabel varian
        # basi + KPI chips varian baru).
        self._cached_base_audit = None
        # FIX C-04 (audit 2-c): minus merah PER CELL (mirror deviasi v3.9.2)
        self._cell_tags = CELL_TAGS_SUPPORTED
        self._neg_cells: list = []
        # FIX B-08 (audit 2-b): sort saat render batch → ANTRE, bukan dibuang
        self._pending_sort = None
        self._satuan_map: dict = {}
        self._kategori_map: dict = {}
        # FIX 6d2-05 — payload kunci MENTAH per iid {iid: {resto, barang,
        # tgl, bm, selisih}} (dibangun _prepare_rows, dikonsumsi
        # _on_double_click — sebelumnya dead code: dibangun tiap render
        # tapi tak pernah dibaca; lihat FIX 6d2-01).
        self._keys: dict = {}
        self.header_filters: HeaderFilterGroup | None = None
        self._colmgr: ColumnManager | None = None

        self._build_ui()
        self._setup_tags()
        if self.data is not None:
            self._refresh()
        else:
            self._show_empty()

    # ---------------------------------------------------------------- UI ----
    def _build_ui(self):
        # --- Empty state ---
        self.empty = EmptyState(
            self, icon="📤",
            title="Belum ada data Rekap Selisih IN",
            cta_text="🚀 Jalankan Pipeline",
            on_cta=lambda: self.go_to_proses() if self.go_to_proses else None)
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Konten utama ---
        self.content = tk.Frame(self, bg=C_BG)

        # --- Filter card (v3.5: RESTO combo DIHAPUS → header filter ⧩) ---
        # v3.9.60 — padding dipadatkan (bagian penghematan tinggi konten
        # tab rekap; lihat komentar _render_resto_scores).
        fcard = Card(self.content, title="Filter", padding=8)
        fcard.pack(fill="x", padx=12, pady=(12, 0))
        fbody = fcard.body()

        # v3.9.27 — MODE HITUNG: 📅 Bulan Ini (default) | 📆 Lalu + Ini.
        # SegmentBar (bukan tk opsi lain) — pola mode PIVOT PER 🏪/📅;
        # nama atribut sengaja `mode_bar` (BUKAN `mode_seg` — nama lama
        # dihapus v3.6 dan ditegaskan tidak boleh ada lagi oleh test §13).
        # v3.9.60 — SATU BARIS kontrol (MODE HITUNG + TANGGAL + opsi):
        # dulu 2 baris terpisah (~+28px) — bagian penghematan tinggi
        # konten tab rekap (lihat komentar _render_resto_scores); catatan
        # '(default: bulan ini saja)' dilepas (segment sudah
        # meng-ekspresikan mode aktif).
        r0 = tk.Frame(fbody, bg=C_CARD)
        r0.pack(fill="x")
        tk.Label(r0, text="MODE HITUNG", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.mode_bar = SegmentBar(
            r0, ["📅 Bulan Ini", "📆 Lalu + Ini"], bg=C_CARD,
            command=self._on_mode_change)
        self.mode_bar.pack(side="left", padx=(6, 14))

        tk.Label(r0, text="TANGGAL", bg=C_CARD, fg=C_TEXT_MUTED,
                 font=font(8, "bold")).pack(side="left")
        self.tgl_start_var = tk.StringVar(value="1")  # v3.8: 1–31 berjalan saja
        entry_start = ttk.Entry(r0, textvariable=self.tgl_start_var, width=6)
        entry_start.pack(side="left", padx=(6, 2))
        entry_start.bind("<Return>", lambda e: self._on_tanggal_change())
        tk.Label(r0, text="–", bg=C_CARD, fg=C_TEXT_MUTED).pack(side="left")
        self.tgl_end_var = tk.StringVar(value="31")  # v3.6: 31 BULAN BERJALAN
        entry_end = ttk.Entry(r0, textvariable=self.tgl_end_var, width=6)
        entry_end.pack(side="left", padx=(2, 8))
        entry_end.bind("<Return>", lambda e: self._on_tanggal_change())
        GhostButton(r0, text="Apply", command=self._on_tanggal_change).pack(
            side="left", padx=(0, 14))

        self.only_selisih_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(
            r0, text="Hanya Selisih ≠ 0",
            variable=self.only_selisih_var,
            command=self._refresh)
        chk.pack(side="left")

        GhostButton(r0, text="✕ Reset Filter",
                    command=self._reset_filter).pack(side="right")

        # --- KPI chips (mode Audit — mirror "EXECUTIVE RECONCILIATION
        #     SUMMARY" VBA) ---
        self.kpi_card = tk.Frame(self.content, bg=C_CARD,
                                 highlightbackground="#e2e8f0",
                                 highlightthickness=1)
        self.kpi_inner = tk.Frame(self.kpi_card, bg=C_CARD)
        # v3.9.60 — padding kartu KPI dipadatkan (pady 8→4 — bagian
        # penghematan tinggi konten; lihat komentar _render_kpi_chips).
        self.kpi_inner.pack(fill="x", padx=12, pady=4)

        # v3.9.55 — F3: kartu SKOR RESTO (user: "Di tab rekap selisih IN.
        # Beri Skor per resto dengan selisih terbanyak supaya aku bisa
        # langsung kasih perhatian resto itu. Selisih terbanyak di tiap
        # tanggal dan di keseluruhan tanggal") — leaderboard resto
        # berdasarkan baris selisih: SKOR = item selisih + tanggal
        # terdampak (resto kronis [selisih TIAP tanggal] mengungguli
        # resto insidental [1 tanggal banyak item] — persis contoh user:
        # periode 1-14 resto A selisih tiap tanggal vs resto B 1 tanggal
        # 5 item). Klik baris → filter tabel ke resto itu. Konten dibangun
        # ulang tiap render (_render_resto_scores dari payload worker).
        self._skor_zone = tk.Frame(self.content, bg=C_CARD,
                                   highlightbackground="#e2e8f0",
                                   highlightthickness=1)
        self._skor_zone_active_resto = None

        # --- Tabel card ---
        tcard = Card(self.content)
        tcard.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        self._tcard = tcard          # anchor pack utk kpi_card (before=)
        tbody = tcard.body()

        head = tk.Frame(tbody, bg=C_CARD)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.title_label = tk.Label(
            head, text="Rekap Selisih IN & Audit Rekonsiliasi — BM vs IN + "
                       "Hasil SO",
            bg=C_CARD, fg=C_HEADER, font=font(10, "bold"))
        self.title_label.pack(side="left")
        # v3.9 (ala Waste): ⛶ = Layar Penuh (window terpisah)
        btn_max = GhostButton(head, text="⛶ Layar Penuh",
                              command=self._maximize)
        btn_max.pack(side="right")
        # v3.9 (ala Waste): ⤢ = Perbesar Tabel (in-place)
        btn_expand = GhostButton(head, text="⤢ Perbesar Tabel")
        btn_expand.pack(side="right", padx=(0, 6))
        # v3.8: export rekap Selisih IN per resto (permintaan user)
        btn_export = GhostButton(head, text="💾 Export Excel",
                                 command=self._on_export)
        btn_export.pack(side="right", padx=(0, 6))
        btn_cols = GhostButton(head, text="◱ Kolom",
                               command=lambda: self._colmgr.open_panel())
        btn_cols.pack(side="right", padx=(0, 6))
        btn_fit = GhostButton(head, text="↔ Auto-Fit", command=self._auto_fit)
        btn_fit.pack(side="right", padx=(0, 6))

        self.tree = ttk.Treeview(tbody, columns=[c[0] for c in COLUMNS],
                                 show="headings", selectmode="extended")

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

        self.overlay = LoadingOverlay(tbody, "Menghitung rekap Selisih IN…")

        # v3.9 (ala Waste): ⤢ Perbesar Tabel — ciutkan kartu Filter + KPI
        # chips + kartu SKOR RESTO + judul; tombol toolbar tetap tampil
        # utk mengembalikan.
        self._expander = TableExpander(
            btn_expand, [fcard, self.kpi_card, self._skor_zone,
                         self.title_label])

        self._apply_columns()

        self.tree.bind("<Double-1>", self._on_double_click, add="+")  # FIX B-04

    def _apply_columns(self):
        """(Re)pasang kolom tree + heading + HeaderFilterGroup +
        ColumnManager (v3.6: satu set kolom — tanpa mode)."""
        # lepas binding filter lama dulu — mencegah binding ganda saat
        # kolom dikonfigurasi ulang (HeaderFilter.bind add="+")
        if self.header_filters is not None:
            self.header_filters.detach_all()
            self.header_filters = None

        col_ids = [c[0] for c in COLUMNS]
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=col_ids)
        for col_name, width, anchor in COLUMNS:
            self.tree.column(col_name, width=width, minwidth=40,
                             anchor=anchor)
            # sort via popup filter — klik heading membuka popup ⧩
            self.tree.heading(col_name, text=col_name)

        # buang state filter kolom yang tidak dikenal
        for c in list(self._col_sel.keys()):
            if c not in col_ids:
                self._col_sel[c] = None

        # filter header ⧩ di SEMUA kolom (incl. SO & Hasil Audit)
        self.header_filters = HeaderFilterGroup(
            self.tree, col_ids,
            get_values=self._col_values,
            on_apply=self._on_col_filter,
            on_sort=lambda c, d: self._sort_by(c, reverse=d))

        # v3.6: hide/unhide kolom (sekali saja — columns() dibaca live)
        if self._colmgr is None:
            self._colmgr = ColumnManager(
                self.tree,
                open_filter=lambda c: self.header_filters and
                self.header_filters.open_popup(c))
        else:
            # v3.7: pastikan state kolom tersembunyi tetap diterapkan
            # setelah reconfigure columns (defensive — displaycolumns
            # bisa di-reset Tk saat kolom dikonfigurasi ulang)
            self._colmgr.apply()

    def _setup_tags(self, tree=None):
        tree = tree if tree is not None else self.tree
        # v3.9.64 — FIX (audit 15-c F-01): tag Cari (Ctrl+F) WAJIB
        # didaftarkan SEBELUM tag bg view (prioritas = urutan create).
        register_find_tags(tree)
        tree.tag_configure("evenrow", background="#ffffff")
        tree.tag_configure("oddrow", background="#f8fafc")
        tree.tag_configure("negative", foreground="#dc2626")
        tree.tag_configure("zero", foreground="#64748b")
        # FIX C-04: tag per-cell (Tk 9 `tag cell`) minus merah — nama tag
        # identik dgn deviasi ('neg_cell').
        tree.tag_configure("neg_cell", foreground="#dc2626")
        # v3.5: warna status audit (mirror conditional formatting VBA)
        for tag, cfg in _STATUS_TAG_CFG.items():
            tree.tag_configure(tag, **cfg)

    # ------------------------------------------------------------ DATA ----
    def load_data(self, data: pd.DataFrame, in_detail: pd.DataFrame | None = None,
                  audit_result: dict | None = None):
        self.data = data
        self.in_detail = in_detail
        # v3.9.55 — F8: data baru → auto-fit SEKALI lagi saat render pertama
        reset_autofit_once(self)
        # v3.9.27 — MODE HITUNG: simpan KEDUA varian audit dari pipeline
        # ("df" = penuh incl. bulan lalu; "df_bulan_ini" = bulan berjalan
        # saja). Pemanggil lama/test tanpa kunci baru → varian bulan-ini
        # = None (mode "Bulan Ini" jatuh ke varian penuh — kompatibel,
        # angkanya identik saat memang tak ada data bulan lalu).
        if audit_result:
            self._audit_full = (audit_result.get("df"),
                                audit_result.get("kpi") or {},
                                audit_result.get("desc") or "")
            if audit_result.get("df_bulan_ini") is not None:
                self._audit_bulan_ini = (audit_result.get("df_bulan_ini"),
                                         audit_result.get("kpi_bulan_ini")
                                         or {},
                                         audit_result.get("desc_bulan_ini")
                                         or "")
            else:
                self._audit_bulan_ini = None
        else:
            self._audit_full = None
            self._audit_bulan_ini = None
        # data baru → mode di-RESET ke default user: "hitung bulan ini
        # aja" (segment + rentang 1..31; tgl entry di-set supaya konsisten
        # dgn mode walau sebelumnya user memakai rentang kustom).
        self._mode_bulan_lalu = False
        if getattr(self, "mode_bar", None) is not None:
            self.mode_bar.set_active_silent(0)
        self.tgl_start_var.set("1")
        self.tgl_end_var.set("31")
        self._apply_audit_mode()
        self._cached_base = None
        # v3.9.33 — AUDIT FIX (48-e FIX 6): seluruh identitas cache ikut
        # di-null (bukan hanya _cached_base) — worker yang masih in-flight
        # tidak bisa menimpa label cache dgn data baru.
        self._cached_base_data = None
        self._cached_base_detail = None
        self._cached_base_audit = None
        self._satuan_map = {}
        self._kategori_map = {}
        self._show_content()
        # v3.9: pulihkan layout bila sedang di-perbesar ⤢ (kpi_card akan
        # di-pack ulang oleh _render_kpi_chips di bawah)
        if getattr(self, "_expander", None) is not None:
            self._expander.reset()
        self._apply_columns()
        self._reset_filter_states()
        # v3.9.22 — DEFAULT KATEGORI DEVIASI (user: "Rekap selisih IN
        # Default Kategori Deviasi"): filter header ⧩ kolom KATEGORI
        # otomatis terseleksi ke nilai 'Deviasi' (case-insensitive) saat
        # data dimuat — mirror default KATEGORI tab Deviasi GR/PCS
        # (v3.9.19). Nilai lain tetap bisa dipilih lewat popup ⧩.
        self._apply_default_kategori()
        self._render_kpi_chips()
        # lazy refresh — hanya compute bila tab terlihat
        if self.winfo_ismapped():
            self._refresh()
        else:
            self._dirty = True
        # v3.9.33 — AUDIT FIX (48-f P0#6 sebagian): pipeline 0 baris
        # (data + audit kosong) → footer INFORMATIF (teks lama
        # diperpanjang; kata kunci 'Belum ada data' tetap ada).
        if (data is None or len(data) == 0) and \
                (self.audit_df is None or self.audit_df.empty):
            self.status_var.set(
                "Belum ada data — 0 baris terbaca dari pipeline "
                "(cek folder data / RootPath di tab ⚙️ Config).")

    # ------------------------------------------------ MODE HITUNG (v3.9.27) --
    def _apply_audit_mode(self):
        """Pasang audit_df/kpi/desc sesuai MODE aktif + invalidasi cache.

        KRITIS (audit coupling 42-a): _refresh.work() mengunci identitas
        cache _cached_base pada (data, in_detail) — TIDAK pada audit_df —
        maka pergantian varian WAJIB me-reset _cached_base manual, kalau
        tidak tabel diam-diam memakai varian lama (angka basi senyap)."""
        if self._mode_bulan_lalu or self._audit_bulan_ini is None:
            src = self._audit_full
        else:
            src = self._audit_bulan_ini
        if src is None:
            self.audit_df = None
            self.audit_kpi = {}
            self.audit_desc = ""
        else:
            self.audit_df, self.audit_kpi, self.audit_desc = src
        self._cached_base = None
        # v3.9.33 — AUDIT FIX (48-e FIX 6, P1): null SEMUA field identitas
        # cache (dulu hanya _cached_base) — worker yang masih in-flight
        # dan menulis ulang cache varian LAMA setelah reset ini tidak
        # lagi meninggalkan identitas cache yang 'tampak valid' bagi
        # refresh berikutnya (race ganti-mode saat compute berjalan).
        self._cached_base_data = None
        self._cached_base_detail = None
        self._cached_base_audit = None

    def _on_mode_change(self, idx: int):
        """v3.9.27 — toggle MODE HITUNG (SegmentBar). idx 0 = 📅 Bulan Ini
        (default), 1 = 📆 Lalu + Ini. Ganti varian audit + rentang tanggal
        + refresh (KPI chips ikut varian lewat _render_kpi_chips)."""
        self._mode_bulan_lalu = (idx == 1)
        self._apply_audit_mode()
        self._render_kpi_chips()
        if self._mode_bulan_lalu:
            self.tgl_start_var.set("-31")   # semua data bulan lalu (-25..-31)
            self.tgl_end_var.set("31")
        else:
            self.tgl_start_var.set("1")     # v3.8 default berjalan saja
            self.tgl_end_var.set("31")
        self._refresh()

    def _default_kategori_value(self) -> "str | None":
        """v3.9.22 — nilai KATEGORI 'Deviasi' persis seperti tertulis di
        data (case-insensitive; None bila tidak ada).
        v3.9.49 — default BARU: nilai kategori Rekap Mentah (COM DEVIASI
        - RESTO + Biaya Packaging - RESTO — user: "secara default di
        semua tab kategori sudah pilih") bila ada di data; fallback
        legacy 'Deviasi'; None bila dua-duanya tak ada. Return nilai
        DATA persis (filter header ⧩ mencocokkan nilai terformat
        eksak — bukan label virtual)."""
        for df in (self.audit_df, self.data):
            if df is None or getattr(df, "empty", True):
                continue
            if "KATEGORI" not in getattr(df, "columns", []):
                continue
            vals = df["KATEGORI"].dropna().astype(str).str.strip()
            # v3.9.49 — kumpulkan SEMUA nilai rekap default yang hadir
            # (case-insensitive, urutan tetap KATEGORI_REKAP_VALUES).
            found = []
            for rv in KATEGORI_REKAP_VALUES:
                for v in vals.unique():
                    if v and v.upper() == rv.upper():
                        found.append(v)
                        break
            if found:
                return found
            for v in vals:
                if v and v.lower() == "deviasi":
                    return [v]
        return None

    def _apply_default_kategori(self):
        """v3.9.22 — terapkan seleksi default KATEGORI=Deviasi (state
        _col_sel + ikon corong aktif).
        v3.9.49 — default = SEMUA nilai kategori Rekap Mentah yang
        hadir di data (multi-select list; legacy 'Deviasi' single)."""
        val = self._default_kategori_value()
        if val is None:
            return
        self._col_sel["KATEGORI"] = list(val)
        if self.header_filters is not None:
            self.header_filters.set_selected("KATEGORI", list(val))

    def ensure_refreshed(self):
        """Lazy refresh: compute hanya saat tab ini terlihat."""
        if self._dirty and self.data is not None and not self.data.empty:
            self._dirty = False
            self._refresh()

    def _reset_filter_states(self):
        for c in self._col_sel:
            self._col_sel[c] = None
        if self.header_filters is not None:
            self.header_filters.clear_all()

    # --- v3.9.66 — FILTER PERSISTEN ANTAR SESI (quick win Wave 1 #1) -------
    # Snapshot / pulihkan kombinasi filter Rekap Selisih IN (MODE HITUNG,
    # rentang TANGGAL, checkbox 'Hanya Selisih ≠ 0', seleksi ⧩ semua
    # kolom) — pola deviasi_view (lihat catatan sana). Default kategori
    # v3.9.22 (_apply_default_kategori) tetap jalan di load_data; snapshot
    # ⧩ KATEGORI menimpanya bila ada (seleksi eksplisit user menang).
    def capture_filter_state(self) -> dict:
        """v3.9.66 — snapshot filter aktif → dict JSON-safe (app simpan
        ke settings.json, key 'filter_state.in_selisih')."""
        st = col_sel_to_json(self._col_sel)
        st["mode_lalu_ini"] = bool(self._mode_bulan_lalu)
        st["tgl_start"] = self.tgl_start_var.get()
        st["tgl_end"] = self.tgl_end_var.get()
        st["only_selisih"] = bool(self.only_selisih_var.get())
        return st

    def restore_filter_state(self, state) -> None:
        """v3.9.66 — pulihkan snapshot capture_filter_state.

        Switch mode lewat jalur yang sama dgn klik user (set_active_
        silent + _apply_audit_mode + _render_kpi_chips — TANPA refresh
        tambahan; rentang tgl di-override dari snapshot SETELAH switch
        karena switch mode me-reset rentang ke default mode). Rentang
        tgl tetap tervalidasi validated_tgl_entry saat refresh (nilai
        korup dari settings.json di-revert + warning — perilaku lama)."""
        if not isinstance(state, dict):
            return
        _no_data = ((self.audit_df is None
                    or bool(getattr(self.audit_df, "empty", True)))
                   and (self.data is None
                        or bool(getattr(self.data, "empty", True))))
        if _no_data:
            return
        changed = apply_col_sel_restore(
            self, state, self._col_sel, self.header_filters)
        _m = state.get("mode_lalu_ini")
        if (isinstance(_m, bool) and _m != bool(self._mode_bulan_lalu)):
            self._mode_bulan_lalu = _m
            if getattr(self, "mode_bar", None) is not None:
                self.mode_bar.set_active_silent(1 if _m else 0)
            self._apply_audit_mode()
            self._render_kpi_chips()
            changed = True
        for key, var in (("tgl_start", self.tgl_start_var),
                         ("tgl_end", self.tgl_end_var)):
            v = state.get(key)
            if (isinstance(v, str) and v
                    and var.get() != v):
                var.set(v)
                changed = True
        v = state.get("only_selisih")
        if (isinstance(v, bool)
                and v != bool(self.only_selisih_var.get())):
            self.only_selisih_var.set(v)
            changed = True
        if changed and self.winfo_ismapped():
            self._refresh()

    # ------------------------------------------------------- KPI CHIPS ----
    def _render_kpi_chips(self):
        """KPI 'EXECUTIVE RECONCILIATION SUMMARY' — dihitung dari varian
        audit AKTIF (v3.9.27: ikut MODE HITUNG — Bulan Ini = bulan
        berjalan saja; Lalu + Ini = data penuh; tidak terpengaruh filter
        tampilan)."""
        for w in self.kpi_inner.winfo_children():
            w.destroy()
        if not self.audit_kpi:
            self.kpi_card.pack_forget()
            return
        k = self.audit_kpi
        # FIX C-03: KPI chips ikut format Indonesia (1.234.567, bukan
        # 1,234,567) — konsisten dgn formatter tabel.
        chips = [
            # v3.9.27 — chip mode di depan: varian audit yang menopang
            # angka-angka di bawahnya (Bulan Ini = baris negatif dibuang).
            ("MODE HITUNG",
             "📅 BULAN INI" if not self._mode_bulan_lalu else "📆 LALU + INI",
             "#0e7490"),
            ("TOTAL BARIS", fmt_int_id(k.get('rows', 0)), "#0f766e"),
            ("OK (MATCHING)", fmt_int_id(k.get('ok', 0)), "#16a34a"),
            ("VALID (SISTEM MASUK)", fmt_int_id(k.get('omit', 0)), "#1f4e78"),
            ("CUT-OFF RESOLVED", fmt_int_id(k.get('cutoff', 0)), "#806000"),
            ("DEVIASI MURNI", fmt_int_id(k.get('deviasi_murni', 0)), "#c65911"),
            # v3.9.30 — deviasi murni yang EXPLAINABLE (pasangannya ada
            # PO 32.43 'Menunggu diproses' — akan resolve saat PO
            # diproses jadi RI); sisanya perlu audit fisik.
            ("DEV MURNI · PO MENUNGGU",
             fmt_int_id(k.get('dev_murni_po', 0)), "#b45309"),
            ("SISA GANTUNG (NET)",
             fmt_int_id(k.get('deviasi_qty', 0.0)),
             "#dc2626" if abs(k.get("deviasi_qty", 0.0)) > 0.0001 else "#16a34a"),
        ]
        # v3.9.59 — FIX 2e-02: 8 kartu KPI dibungkus GRID 4-per-baris
        # (2 baris deterministik). Dulu 8× pack side="left" SATU baris
        # (~1014px lebar) → pada WINDOW_MIN app 1020px kartu terakhir
        # 'SISA GANTUNG (NET)' TERPOTONG +44px tanpa wrap/scroll; font
        # Windows lebih lebar dari bitmap Xvfb → borderline juga di
        # jendela default 1280.
        # v3.9.60 — KPI COMPACT (padat vertikal): kartu KPI + papan skor +
        # kartu filter menghabiskan tinggi konten (probe: tabel rekap sisa
        # 92px @1500×850, ≈0 @1020×700 minsize — gejala user "tidak bisa
        # scrol"): pady chip 6→3, nilai font 11→10 — hemat ~30px tanpa
        # mengubah informasi.
        _last_row = (len(chips) - 1) // 4
        for _i, (label, value, color) in enumerate(chips):
            _row, _col = _i // 4, _i % 4
            box = tk.Frame(self.kpi_inner, bg="#f8fafc",
                           highlightbackground="#e2e8f0", highlightthickness=1)
            box.grid(row=_row, column=_col, padx=(0, 8),
                     pady=(0, 3 if _row < _last_row else 0),
                     sticky="w")
            tk.Label(box, text=label, bg="#f8fafc", fg=C_TEXT_MUTED,
                     font=font(8, "bold")).pack(anchor="w", padx=10,
                                                pady=(3, 0))
            tk.Label(box, text=value, bg="#f8fafc", fg=color,
                     font=font(10, "bold")).pack(anchor="w", padx=10,
                                                 pady=(0, 3))
        self.kpi_card.pack(fill="x", padx=12, pady=(10, 0),
                           before=(self._skor_zone
                                   if self._skor_zone.winfo_ismapped()
                                   else self._tcard))

    # --------------------------------------------------- VALUES & FILTER ---
    def _col_values(self, col: str) -> list:
        base = self._cached_base
        if base is None:
            # FIX D-08 (audit 2-d): JANGAN menjalankan _compute_base()
            # (audit 35 ribu+ baris) di MAIN thread — dulu membuka popup
            # filter sebelum cache terisi MEMBEKUKAN UI berdetik-detik.
            # Ambil nilai dari baris yang SUDAH tampil (nilai TERFORMAT —
            # filter memang mencocokkan nilai terformat, identik
            # _prepare_rows; cache terisi setelah refresh pertama).
            vals = set()
            col_ids = list(self.tree["columns"])
            if col in col_ids:
                k = col_ids.index(col)
                for iid in self.tree.get_children(""):
                    v = self.tree.item(iid, "values")
                    if v and k < len(v):
                        s = str(v[k])
                        if s:
                            vals.add(s)
            # FIX 35-c1 (NIT C1): buang literal 'None'/'nan'/'NaT' juga di
            # jalur fallback D-08 (nilai string hasil render tree).
            return sorted(
                (v for v in vals if v not in ("None", "nan", "NaT")),
                key=_filter_value_sort_key)
        if base is None or base.empty:
            return []
        # v3.9.19 — sumber nilai = baris yang TAMPIL SAAT INI (permintaan
        # user: "isi filter harus menampilkan data yang ada aja"):
        # rentang tanggal + filter kolom LAIN + checkbox hanya-selisih
        # (kolom ini sendiri dikecualikan — perilaku AutoFilter Excel).
        # Dulu base mentah → tanggal bulan lalu / nilai baris tersembunyi
        # ikut muncul di daftar filter.
        f = base
        try:
            t_start = int(self.tgl_start_var.get())
            t_end = int(self.tgl_end_var.get())
        except (AttributeError, TypeError, ValueError):
            t_start = t_end = None
        if t_start is not None and t_end is not None:
            t = pd.to_numeric(f["Tanggal"], errors="coerce")
            f = f[(t >= t_start) & (t <= t_end)]
        for c, sel in self._col_sel.items():
            if sel is None or c == col or c not in f.columns:
                continue
            fmt = _format_col_values(c, f[c])
            f = f[fmt.isin(sel)]
        if (getattr(self, "only_selisih_var", None) is not None
                and self.only_selisih_var.get()
                and "Selisih IN" in f.columns):
            sv = pd.to_numeric(f["Selisih IN"], errors="coerce").fillna(0)
            f = f[sv != 0]
        if f.empty or col not in f.columns:
            return []
        # FIX 35-c1 (NIT C1): literal 'None'/'nan'/'NaT' (object cols dgn
        # None/pd.NA asli → astype(str)) jangan bocor ke daftar nilai
        # popup filter; '' tetap dipertahankan.
        vals = _format_col_values(col, f[col]).unique().tolist()
        return [v for v in vals if v not in ("None", "nan", "NaT")]

    def _on_col_filter(self, col: str, selected):
        self._col_sel[col] = selected
        self._refresh()

    # ------------------------------------------------------- COMPUTE ----
    def _compute_base(self, data: pd.DataFrame | None = None,
                      audit_df: pd.DataFrame | None = None,
                      in_detail: pd.DataFrame | None | bool = False
                      ) -> pd.DataFrame:
        """Bangun tabel tampilan dari hasil audit fn_audit (data app) +
        map Satuan/KATEGORI (v3.6).
        FIX D-01: data/audit_df bisa di-pass eksplisit (identitas pra-
        capture worker) — default membaca self.* (kompatibel test).
        v3.9.23 (poin B — "catatan Audit pada tab rekap selisih IN"):
        kolom Catatan Audit DIPERKAYA catatan otomatis app (RI
        Balancing / Nomor Dobel / Selisih IN / BM kosong) —
        ditambahkan SETELAH catatan engine VBA (dipisah ' | '),
        sehingga isi VBA asli tidak berubah; in_detail default =
        self.in_detail (sentinel False = tanpa enrichment, utk
        pemanggil lama/test yang tak peduli)."""
        df = self.audit_df if audit_df is None else audit_df
        if df is None or df.empty:
            return pd.DataFrame()
        data = self.data if data is None else data
        if in_detail is False:
            in_detail = self.in_detail
        if data is not None and not data.empty:
            self._ensure_maps(data)

        out = pd.DataFrame({
            "Resto": df["Resto"].astype(str),
            "Tanggal": pd.to_numeric(df["Tanggal"], errors="coerce"),
            "Nama Barang": df["Nama Item"].astype(str),
            "Hasil SO": pd.to_numeric(df["Hasil SO"], errors="coerce"),
            "Barang Masuk": pd.to_numeric(df["Qty SO Harian"],
                                           errors="coerce"),
            "IN": pd.to_numeric(df["Penerimaan Sistem"], errors="coerce"),
            "Selisih IN": pd.to_numeric(df["Selisih Harian"],
                                         errors="coerce"),
            "Saldo": pd.to_numeric(df["Saldo Kumulatif"], errors="coerce"),
            # v3.9.30 — qty PO 'Menunggu diproses' per pasangan (kolom
            # ditambah fn_audit saat pipeline membawa Rincian PO 32.43;
            # audit_df lama/test tanpa kolom → NA → tampil '-')
            "PO Menunggu": (pd.to_numeric(df["Qty PO Menunggu"],
                                           errors="coerce")
                             if "Qty PO Menunggu" in df.columns else
                             pd.Series([pd.NA] * len(df),
                                       index=df.index, dtype="Float64")),
            "Hasil Audit": df["Status Analisis Audit"].astype(str),
            # v3.9.33 — AUDIT FIX (48-e): NaN/None di kolom catatan engine
            # jangan jadi literal 'nan'/'None' setelah astype(str) —
            # dinolkan di SUMBER (sel tampil kosong, export bersih, dan
            # _join_notes konsisten di kedua jalur dgn/tanpa catatan app;
            # dulu baris tanpa catatan tampil 'nan' di kolom Catatan
            # Audit + ikut ke export).
            "Catatan Audit": (df["Detail & Catatan Audit"]
                              .where(df["Detail & Catatan Audit"].notna(),
                                     "")
                              .astype(str)),
        })
        # v3.8: komponen IN per sumber (utk 💾 Export per resto — kolom
        # Kiriman HO / Kiriman Supplier / Pembelian by Resto; tidak
        # ditampilkan di tabel, hanya dibawa oleh base)
        for col_out, col_in in (("42.05", "Qty SJ"),
                                 ("32.24", "Qty RI"),
                                 ("99.01", "Qty Pembelian")):
            out[col_out] = pd.to_numeric(df.get(col_in),
                                         errors="coerce") \
                if col_in in df.columns else pd.Series(
                    [pd.NA] * len(out), dtype="Float64")
        out.insert(3, "KATEGORI",
                   [self._kategori_map.get(b, "-")
                    for b in out["Nama Barang"]])
        out["Satuan"] = [self._satuan_map.get((b, r), "-")
                          for b, r in zip(out["Nama Barang"],
                                          out["Resto"])]
        # v3.9.23 (poin B) — CATATAN AUDIT OTOMATIS: catatan app
        # (RI Balancing · Nomor Dobel · Selisih IN · BM kosong)
        # di-APPEND ke catatan engine VBA (" | "); catatan VBA asli
        # tetap di posisi pertama — isi lama tidak berubah.
        _notes = self._build_audit_notes(out, in_detail)
        if _notes:
            out["Catatan Audit"] = [
                _join_notes(vba, _notes.get((r, t, b)))
                for vba, r, t, b in zip(out["Catatan Audit"],
                                        out["Resto"], out["Tanggal"],
                                        out["Nama Barang"])
            ]
        return out

    def _build_audit_notes(self, out: pd.DataFrame,
                           in_detail: pd.DataFrame | None) -> dict:
        """v3.9.23 (poin B — user: "catatan Audit pada tab rekap
        selisih IN") — catatan audit OTOMATIS per baris tabel
        (Resto, Tanggal, Nama Barang), dihitung dari detail dokumen
        IN per-dokumen + angka baris itu sendiri:

        B1 · RI Balancing — dokumen IN pada baris itu yang bulan
            Nomor RI-nya ≠ bulan Nomor PO-nya (logika sama popup
            Rincian IN v3.9.19, kini di modul bersama doc_codes):
            "RI Balancing: RI.2026.10.10354 (PO 2026-08)" — maks 2
            nomor dituliskan, sisanya dihitung.
        B2 · Nomor Dobel — nomor dokumen sama muncul >1 baris utk
            pasangan (barang, resto) yang sama = input ganda /
            sheet kembar (gejala audit 37-a R2 — fn_9901 membaca
            semua sheet): "Nomor dobel: IT.2026.09.00123 ×2".
        B3 · Selisih IN — BM (input rekap harian) ≠ IN (penerimaan
            sistem): "Selisih IN −3 (IN 13 > BM 10)" — tanda & arah
            perbedaan langsung terbaca tanpa buka popup.
        B4 · BM kosong — BM 0 padahal IN sistem > 0 (input rekap
            belum diisi — data quality, mirror temuan audit 37-a
            R1): "BM 0 padahal IN 13 (input rekap belum diisi)".

        Return dict {(resto, tgl_num, barang): [note, ...]} — baris
        tanpa temuan tidak masuk (catatan VBA tetap sendirian).
        Angka mengikuti format Indonesia _fmt_num (identik kolom
        tabel, filter ⧩ tetap konsisten dgn tampilan).
        """
        if out is None or out.empty:
            return {}
        notes: dict = {}

        def _add(r, t, b, note):
            notes.setdefault((str(r), _tgl_key(t), str(b)), []).append(note)

        # --- B1: RI Balancing (per tanggal — dokumen milik baris itu) ---
        rib = _ri_balancing_by_date(in_detail)
        if rib:
            for (b, r), per_tgl in rib.items():
                for t, docs in per_tgl.items():
                    shown = [f"{n}{po}" for n, po in docs[:2]]
                    extra = len(docs) - len(shown)
                    txt = ", ".join(shown)
                    if extra > 0:
                        txt += f" (+{extra})"
                    _add(r, t, b, f"RI Balancing: {txt}")

        # --- B2: Nomor dobel (level pasangan; baris bertanggal dokumen
        #     itu yang diberi catatan — dobel berdampak di tanggal itu) ---
        dup = duplicated_doc_numbers(in_detail)
        if dup:
            _dup_at = _duplicated_doc_dates(in_detail, dup)
            for (b, r), per_tgl in _dup_at.items():
                for t, items_ in per_tgl.items():
                    shown = [f"{n} ×{c}" for n, c in items_[:2]]
                    extra = len(items_) - len(shown)
                    txt = ", ".join(shown)
                    if extra > 0:
                        txt += f" (+{extra})"
                    _add(r, t, b, f"Nomor dobel: {txt}")

        # --- B3 + B4: dari angka baris tabel itu sendiri (vektor) ---
        # B4 DIDAHULUKAN dari B3: Selisih = BM − IN identitas aljabar —
        # bila BM 0 & IN > 0 maka selisih PASTI ≠ 0, dan diagnosis yang
        # benar bukan "selisih angka" melainkan "input rekap belum
        # diisi" (B3 umum hanya bila BM & IN sama-sama terisi).
        bm = pd.to_numeric(out["Barang Masuk"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        ins = pd.to_numeric(out["IN"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        sel = pd.to_numeric(out["Selisih IN"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        for i in range(len(out)):
            r = out["Resto"].iat[i]
            b = out["Nama Barang"].iat[i]
            t = out["Tanggal"].iat[i]
            if bm[i] == 0 and ins[i] > 0:
                _add(r, t, b,
                     f"BM 0 padahal IN {_fmt_num(ins[i])} "
                     f"(input rekap belum diisi)")
            elif sel[i] != 0:
                arah = (f"IN {_fmt_num(ins[i])} > BM {_fmt_num(bm[i])}"
                        if sel[i] < 0 else
                        f"BM {_fmt_num(bm[i])} > IN {_fmt_num(ins[i])}")
                _add(r, t, b,
                     f"Selisih IN {_fmt_num(sel[i])} ({arah})")
        return notes

    def _ensure_maps(self, df):
        """Lookup satuan per (barang, resto) + kategori per barang (v3.5)."""
        if not self._satuan_map and "SATUAN" in df.columns:
            sat = (df[["Nama Barang", "NAMA RESTO", "SATUAN"]]
                   .dropna(subset=["SATUAN"])
                   .drop_duplicates(subset=["Nama Barang", "NAMA RESTO"],
                                    keep="first"))
            self._satuan_map = {
                (str(b), str(r)): str(s)
                for b, r, s in zip(sat["Nama Barang"], sat["NAMA RESTO"],
                                   sat["SATUAN"])
            }
        if not self._kategori_map and "KATEGORI" in df.columns:
            kat = (df[["Nama Barang", "KATEGORI"]]
                   .dropna(subset=["KATEGORI"])
                   .drop_duplicates(subset=["Nama Barang"], keep="first"))
            self._kategori_map = {
                str(b): str(k)
                for b, k in zip(kat["Nama Barang"], kat["KATEGORI"])
            }

    # ------------------------------------------------------------- REFRESH
    def _refresh(self, sync: bool = False):
        if (self.audit_df is None or self.audit_df.empty) and \
                (self.data is None or self.data.empty):
            self.status_var.set("Belum ada data.")
            return
        if self._busy:
            self._pending = True
            return
        self._busy = True
        # FIX B-02: validasi konsisten (warning + revert) — sebelumnya
        # fallback senyap ke 1/31.
        tgl_start = validated_tgl_entry(self.tgl_start_var, lo=-31, hi=31,
                                        fallback=1, label="Tanggal awal",
                                        parent=self)
        tgl_end = validated_tgl_entry(self.tgl_end_var, lo=-31, hi=31,
                                      fallback=31, label="Tanggal akhir",
                                      parent=self)
        st = {
            "tgl_start": tgl_start,
            "tgl_end": tgl_end,
            "only_selisih": self.only_selisih_var.get(),
            # v3.9.13: seleksi kosong (set()) = filter AKTIF → 0 baris
            # (semantik Excel) — dulu truthiness `if s` menelannya.
            "col_sel": {c: s for c, s in self._col_sel.items()
                        if s is not None},
        }

        def work():
            # FIX D-01 (audit 2-d): capture identitas SEKALU di awal job —
            # self.data / self.audit_df bisa ditukar main thread (load_data
            # saat pipeline selesai) DI TENGAH compute; tanpa capture,
            # worker menempel base data LAMA dengan label data BARU →
            # refresh berikutnya SKIP recompute (angka basi, senyap).
            data = self.data
            audit_df = self.audit_df
            in_detail = self.in_detail   # v3.9.23 (poin B) — capture sama
            if (self._cached_base is None
                    or self._cached_base_data is not data
                    or self._cached_base_detail is not in_detail
                    # v3.9.33 — AUDIT FIX (48-e FIX 6): identitas cache
                    # kini ikut membandingkan VARIAN audit (audit_df) —
                    # ganti MODE HITUNG saat worker lama masih menghitung
                    # tidak lagi bisa meninggalkan cache varian basi yang
                    # dianggap 'valid' oleh refresh berikutnya (dulu:
                    # worker lama menulis ulang cache varian A pasca-reset
                    # → pending refresh SKIP recompute → tabel varian A,
                    # KPI chips varian B).
                    or self._cached_base_audit is not audit_df):
                base = self._compute_base(data, audit_df, in_detail)
                self._cached_base = base
                self._cached_base_data = data
                self._cached_base_detail = in_detail
                self._cached_base_audit = audit_df
            return self._prepare_rows(st)

        def done(payload):
            self._render_rows(payload)

        # FIX B-01: _busy wajib di-reset saat compute GAGAL — tanpa ini
        # view mati permanen setelah 1x error (filter/reset ditelan senyap).
        def on_error(err):
            self._busy = False
            self._pending = False
            self.status_var.set(f"⚠ Gagal menghitung rekap Selisih IN: {err}")

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Menghitung rekap Selisih IN…",
                  on_error=on_error, sync=sync)

    def _prepare_rows(self, st: dict) -> dict:
        base = self._cached_base
        if base is None or base.empty:
            return {"items": [], "status": "Tidak ada data."}

        f = base
        # rentang tanggal — display-only (audit dihitung dari data penuh;
        # ini hanya menyembunyikan baris dari tampilan)
        if st["tgl_start"] is not None and st["tgl_end"] is not None:
            t = pd.to_numeric(f["Tanggal"], errors="coerce")
            f = f[(t >= st["tgl_start"]) & (t <= st["tgl_end"])]

        # filter header ⧩ — kecocokan nilai TERFORMAT (identik dgn
        # yang tampil di tabel).
        # FIX 6d2-02 — kolom 'Resto' DIKECUALIKAN dari loop dan diterapkan
        # SETELAH snapshot f_pre: SKOR RESTO dihitung dari frame
        # PRA-FILTER-RESTO (rentang tanggal + ⧩ kolom lain + varian MODE
        # HITUNG tetap kontekstual) supaya leaderboard TIDAK kolapse ke 1
        # resto saat barisnya diklik (klik = fokus TABEL ke resto itu,
        # bukan menyusutkan papan skor — medali '#1' dari 1 peserta
        # menyesatkan); highlight is_active _render_resto_scores jadi
        # benar-benar berfungsi (dulu dead: board terfilter Resto hanya
        # memuat resto aktif sendiri).
        _resto_sel = st["col_sel"].get("Resto")
        for col, sel in st["col_sel"].items():
            if col == "Resto":
                continue
            if col in f.columns:
                fmt = _format_col_values(col, f[col])
                f = f[fmt.isin(sel)]

        # v3.9.55 — F3: snapshot frame pra-only_selisih (dasar SKOR RESTO
        # — baris selisih sama baik checkbox aktif / tidak).
        # FIX 6d2-02 — kini juga pra-filter-Resto (lihat komentar di atas).
        f_pre = f

        if _resto_sel is not None and "Resto" in f.columns:
            fmt_r = _format_col_values("Resto", f["Resto"])
            f = f[fmt_r.isin(_resto_sel)]

        if st["only_selisih"] and "Selisih IN" in f.columns:
            sv = pd.to_numeric(f["Selisih IN"], errors="coerce").fillna(0)
            f = f[sv != 0]

        # v3.9.55 — F3: SKOR RESTO (user: "Beri Skor per resto dengan
        # selisih terbanyak ... Selisih terbanyak di tiap tanggal dan di
        # keseluruhan tanggal") — dihitung dari frame TERFILTER rentang
        # tanggal + ⧩ lain (konteks apa yang sedang dilihat) KECUALI
        # filter Resto (FIX 6d2-02 — klik leaderboard tak boleh
        # menyusutkan papan skor; baris resto aktif di-highlight);
        # baris selisih = Selisih IN ≠ 0 (tak terpengaruh checkbox
        # 'Hanya Selisih ≠ 0' — skor selalu tentang baris bermasalah).
        # SKOR = jumlah ITEM selisih + jumlah TANGGAL terdampak
        # (bonus kronis: resto yang selisih TIAP tanggal periode 1-14
        # [14 item + 14 tgl = 28] mengungguli resto 1-tanggal-5-item [5+1
        # = 6] — persis contoh user). Diurut skor ↓, item ↓, nama resto ↑.
        resto_scores = []
        try:
            if "Selisih IN" in f_pre.columns:
                _sv3 = pd.to_numeric(f_pre["Selisih IN"],
                                     errors="coerce").fillna(0)
                _sel = f_pre[_sv3 != 0]
                if not _sel.empty:
                    _t_all = pd.to_numeric(f_pre["Tanggal"],
                                           errors="coerce")
                    _n_tgl_range = int(_t_all.dropna().nunique())
                    _resto_s = _sel["Resto"].astype(str)
                    _tgl_s = pd.to_numeric(_sel["Tanggal"],
                                           errors="coerce")
                    _grp = _sel.assign(_r=_resto_s, _t=_tgl_s).groupby("_r")
                    for resto, gdf in _grp:
                        n_items = len(gdf)
                        n_dates = int(gdf["_t"].dropna().nunique())
                        sum_abs = float(
                            pd.to_numeric(gdf["Selisih IN"],
                                          errors="coerce").abs().sum())
                        resto_scores.append({
                            "resto": resto, "n_items": n_items,
                            "n_dates": n_dates, "sum_abs": sum_abs,
                            "skor": n_items + n_dates,
                        })
                    resto_scores.sort(
                        key=lambda r: (-r["skor"], -r["n_items"],
                                       str(r["resto"])))
                    resto_scores = [
                        {**r, "n_tgl_range": _n_tgl_range}
                        for r in resto_scores]
        except (KeyError, TypeError, ValueError):
            resto_scores = []

        if f.empty:
            # v3.9.68 — TRI-STATE (audit eksternal T1): pesan jujur bila
            # penyebabnya seleksi ⧩ KOSONG (filter aktif → 0 baris).
            return {"items": [],
                    "status": (zero_row_filter_message(st["col_sel"])
                               or "Tidak ada data setelah filter."),
                    "resto_scores": resto_scores}

        col_ids = [c[0] for c in COLUMNS]

        # format kolom sekali (vektor per kolom — lebih cepat dari per-sel)
        formatted = {}
        for c in col_ids:
            if c in f.columns:
                formatted[c] = _format_col_values(c, f[c]).tolist()

        status_s = f["Hasil Audit"].astype(str).tolist()

        resto_np = f["Resto"].astype(str).to_numpy()
        barang_np = f["Nama Barang"].astype(str).to_numpy()
        tgl_np = pd.to_numeric(f["Tanggal"], errors="coerce").to_numpy()

        n = len(f)
        items = []
        # FIX 6d2-05/6d2-01 — payload kunci MENTAH per iid {iid: raw}:
        # resto/barang/tgl + bm/selisih numerik mentah (chip ringkasan
        # popup — display '1.500' Indonesia tidak boleh di-parse float
        # EN). Dibangun sesuai urutan item row_i (iid stabil di sort/clone).
        keys = {}
        # FIX C-04 (audit 2-c): minus merah PER CELL di kolom numerik —
        # mirror pola deviasi v3.9.2 (Tk 9 tag cell; fallback Tk 8 = tag
        # baris 'negative' yang sudah dikonfigurasi _setup_tags).
        neg_cells: list = []
        num_raw = {}
        for c in _NUM_COLS:
            if c in f.columns:
                num_raw[c] = pd.to_numeric(f[c], errors="coerce").to_numpy()
        # FIX 6d2-01 — kolom numerik MENTAH utk chip popup (lihat _raw_num)
        _bm_np = num_raw.get("Barang Masuk")
        _sel_np = num_raw.get("Selisih IN")
        for i in range(n):
            values = tuple(formatted[c][i] for c in col_ids)
            st_tag = _STATUS_TAG.get(status_s[i])
            tags = [st_tag] if st_tag else \
                ["evenrow" if i % 2 == 0 else "oddrow"]
            row_neg = False
            for c, raw in num_raw.items():
                v = raw[i]
                if pd.notna(v) and v < 0:
                    if self._cell_tags:
                        neg_cells.append((f"row_{i}", c))
                    else:
                        row_neg = True
            if row_neg:
                tags.append("negative")
            items.append(("", f"row_{i}", {"values": values,
                                            "tags": tuple(tags)}))
            # key utk drill-down: resto/barang/tgl MENTAH + bm/selisih
            # mentah per iid (FIX 6d2-05/6d2-01 — lihat komentar deklarasi
            # `keys` di atas; dikonsumsi _on_double_click)
            t = tgl_np[i]
            keys[f"row_{i}"] = {
                "resto": str(resto_np[i]),
                "barang": str(barang_np[i]),
                "tgl": None if pd.isna(t) else int(t),
                "bm": _raw_num(_bm_np, i),
                "selisih": _raw_num(_sel_np, i),
            }

        # ringkasan status
        # FIX C-10 (audit 2-c): koma ribuan EN ("1,234") terbaca desimal
        # dalam konvensi ID — kini fmt_int_id (⨯ konsistensi footer lain).
        status_txt = f"{n} baris · " + " · ".join(
            f"{k}: {fmt_int_id(v)}" for k, v in
            pd.Series(status_s).value_counts().head(3).items())
        return {"items": items, "status": status_txt, "keys": keys,
                "neg_cells": neg_cells,
                "resto_scores": resto_scores}

    def _render_rows(self, payload: dict):
        self.tree.delete(*self.tree.get_children())
        if self.header_filters is not None:
            self.header_filters.refresh_icons()
        self.status_var.set(payload["status"])
        self._keys = payload.get("keys", {})   # FIX 6d2-05 — {iid: raw}
        self._neg_cells = payload.get("neg_cells", [])  # FIX C-04
        # v3.9.55 — F3: kartu SKOR RESTO ikut render tiap refresh (konteks
        # filter tanggal/⧩ aktif).
        self._render_resto_scores(payload.get("resto_scores") or [])

        def render_done():
            # FIX C-04: tag per-cell dipasang SETELAH insert batch selesai
            self._reapply_cell_tags(self.tree)
            # v3.9.55 — F8: auto-fit kolom SEKALI per muat data
            autofit_tree_once(self, self.tree)
            self._busy = False
            if self._pending:
                self._pending = False
                self._refresh()
            elif self._pending_sort:
                # FIX B-08: mainkan sort yang mengantre saat render batch
                col, rev = self._pending_sort
                self._pending_sort = None
                self._sort_by(col, reverse=rev)

        insert_tree_items(self.tree, payload["items"], batch=500,
                          on_done=render_done)

    def _reapply_cell_tags(self, tree):
        """FIX C-04 (audit 2-c): pasang ulang tag per-cell minus — sort /
        filter = delete+reinsert me-reset tag cell (mirror deviasi v3.9.2;
        dipakai juga utk clone ⛶ lewat on_after_filter).
        v3.9.42 — audit 61-c P1-2: guard non-kosong dihapus."""
        if self._cell_tags:
            apply_cell_tag(tree, "neg_cell", self._neg_cells)

    # --------------------------------------------------- SKOR RESTO (F3) --
    _SKOR_RANK_BG = ("#fef3c7", "#e2e8f0", "#fffbeb")   # emas/perak/perunggu lembut

    def _render_resto_scores(self, scores: list):
        """v3.9.55 — F3: bangun ulang kartu leaderboard SKOR RESTO.

        Baris = resto urut SKOR ↓ (skor = item selisih + tanggal terdampak
        — lihat _prepare_rows). Kolom: peringkat · resto · tgl terdampak
        (n dari N tgl periode) · item selisih · Σ|Selisih| · skor + bar
        proporsional. Top-3 diberi latar medali lembut. KLIK baris = filter
        tabel Resto (klik lagi = lepas) — 'langsung kasih perhatian resto
        itu'. FIX 6d2-02: papan TETAP UTUH saat filter Resto aktif (skor
        dihitung pra-filter-Resto) — baris resto terseleksi di-highlight
        amber (is_active), bukan board menyusut jadi 1 baris."""
        zone = self._skor_zone
        for w in zone.winfo_children():
            w.destroy()
        if not scores:
            zone.pack_forget()
            self._skor_zone_active_resto = None
            return
        # FIX 6d2-02 — highlight SEMUA resto terseleksi kolom Resto (klik
        # leaderboard = 1 resto; popup ⧩ bisa multi-select). Semantik lama
        # (elemen PERTAMA list) membuat highlight hanya bermakna saat board
        # sudah kolapse — kini board utuh, highlight jadi sinyal fokus.
        _sel_resto = self._col_sel.get("Resto")
        active_set = ({str(x) for x in _sel_resto}
                      if isinstance(_sel_resto, list) else set())
        self._skor_zone_active_resto = (min(active_set)
                                        if active_set else None)

        head = tk.Frame(zone, bg=C_CARD)
        head.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(head, text="🏆 SKOR RESTO — Prioritas Perhatian",
                 bg=C_CARD, fg=C_HEADER, font=font(10, "bold")).pack(
            side="left")
        tk.Label(head, text=(
            "skor = item selisih + tgl terdampak · klik baris utk filter "
            "tabel ke resto itu"), bg=C_CARD, fg=C_TEXT_MUTED,
            font=font(8)).pack(side="right")

        cols = (("RESTO", 34), ("TGL TERDAMPAK", 15), ("ITEM", 9),
                ("Σ|SELISIH|", 13), ("SKOR", 24))
        hdr = tk.Frame(zone, bg="#f8fafc")
        hdr.pack(fill="x", padx=12)
        for text, wpx in cols:
            tk.Label(hdr, text=text, bg="#f8fafc", fg=C_TEXT_MUTED,
                     font=font(8, "bold"), width=wpx, anchor="w",
                     padx=6).pack(side="left")

        # v3.9.60 — LIST SCROLLABLE BER-CAP (user: "tab rekap selisih in
        # tidak bisa scrol"): 12 baris leaderboard + kartu KPI + kartu
        # filter menghabiskan SELURUH tinggi konten di jendela default/
        # kecil (probe 1500×850: tabel sisa 92px ≈ 3 baris; di 1020×700
        # minsize tabel ≈ 0 — tak terlihat, terasa "tidak bisa scroll").
        # Baris kini di CANVAS ber-scroll dengan tinggi DIBATASI
        # (±5 baris terlihat; sisanya digulir roda/scrollbar tipis) →
        # ruang vertikal dikembalikan ke TABEL utama (konten tab ini).
        listwrap = tk.Frame(zone, bg=C_CARD)
        listwrap.pack(fill="x", padx=12)
        cv = tk.Canvas(listwrap, bg=C_CARD, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(listwrap, orient="vertical", command=cv.yview)
        inner = tk.Frame(cv, bg=C_CARD)
        _winid = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        inner.bind(
            "<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind(
            "<Configure>",
            lambda e: cv.itemconfigure(_winid, width=cv.winfo_width()))

        max_skor = max(r["skor"] for r in scores) or 1
        for i, r in enumerate(scores[:12]):
            bg = self._SKOR_RANK_BG[i] if i < 3 else C_CARD
            # FIX 6d2-02 — membership (bukan == elemen pertama) → semua
            # resto terseleksi ter-highlight saat board utuh.
            is_active = (str(r["resto"]) in active_set)
            bg = "#fef3c7" if is_active else bg
            row = tk.Frame(inner, bg=bg, cursor="hand2",
                           highlightbackground="#e2e8f0",
                           highlightthickness=1 if is_active else 0)
            row.pack(fill="x", pady=(0, 1))
            _resto = str(r["resto"])
            vals = (
                f"#{i + 1}  {_resto}",
                f"{r['n_dates']} / {r.get('n_tgl_range', '—')} tgl",
                fmt_int_id(r["n_items"]),
                self._fmt_num_skor(r["sum_abs"]),
                fmt_int_id(r["skor"]),
            )
            for (text, wpx), val in zip(cols, vals):
                fg = ("#b91c1c" if (i == 0 and not is_active) else
                      ("#0e7490" if is_active else C_HEADER))
                tk.Label(row, text=val, bg=bg, fg=fg, width=wpx,
                         anchor="w", padx=6, font=font(
                             9, "bold" if i < 3 or is_active else "normal")
                ).pack(side="left")
            # bar proporsional skor (visual leaderboard)
            bar_w = max(6, int(150 * r["skor"] / max_skor))
            tk.Frame(row, bg=("#b91c1c" if i == 0 else "#64748b"),
                     height=6, width=bar_w, bd=0,
                     highlightthickness=0).pack(side="left", padx=(10, 0),
                                                pady=(6, 0))
            row.bind("<Button-1>", lambda e, rs=_resto:
                     self._on_skor_row_click(rs))
            for ch in row.winfo_children():
                ch.bind("<Button-1>", lambda e, rs=_resto:
                         self._on_skor_row_click(rs))
        # v3.9.60 — CAP TINGGI + SCROLL RODA daftar leaderboard: ukur
        # tinggi baris aktual (font Windows lebih tinggi dari Xvfb —
        # jangan hardcode piksel), tampilkan maks ±5 baris, dan pasang
        # akumulator roda halus (pola enable_smooth_wheel_list: trackpad
        # delta kecil). Scrollbar tipis hanya saat konten meluap.
        # v3.9.61 — FIX RODA "MASIH TIDAK BISA SCROLL" (user): (a) BARIS
        # leaderboard = Label di dalam inner — binding Tk tak bubble dari
        # frame induk → roda di atas BARIS (±90% area papan) MATI;
        # kini dicover install_wheel_router di Toplevel app (binding
        # Toplevel ada di bindtag semua anak + cari scrollable-bawah-
        # pointer); (b) canvas "units" default = 1/10 tinggi jendela
        # (±13px/notch — terlalu lambat) → yscrollincrement = tinggi
        # baris aktual → 1 notch = 1 baris (selaras tabel).
        try:
            zone.update_idletasks()
            _rows_in = inner.winfo_children()
            _req_h = inner.winfo_reqheight()
            _row_h = (_req_h // len(_rows_in)) if _rows_in else 24
            _cap_h = min(_req_h, max(_row_h * 5 + 2, 1))
            cv.configure(height=_cap_h)
            cv.configure(yscrollincrement=max(1, _row_h))
            if _req_h > _cap_h + 2:
                sb.pack(side="right", fill="y")
            enable_smooth_wheel_list(cv, container=listwrap)
        except tk.TclError:
            pass
        # v3.9.59 — FIX 2e-06: indikator sisa leaderboard — papan dipotong
        # di 12 baris (scores[:12]) tapi DULU tanpa jejak apa pun: resto
        # #13+ (yang juga berselisih) tak terlihat & papan terkesan
        # lengkap. Baris penutup NON-SKOR (abu-abu, tidak bisa diklik).
        if len(scores) > 12:
            more = tk.Frame(zone, bg=C_CARD)
            more.pack(fill="x", padx=12, pady=(4, 2))
            tk.Label(
                more,
                text=f"+{fmt_int_id(len(scores) - 12)} resto lainnya "
                     f"(dari {fmt_int_id(len(scores))} resto berskor) — "
                     "buka filter ⧩ kolom Resto utk daftar lengkap "
                     "(gulir papan skor utk peringkat 6-12)",
                bg=C_CARD, fg=C_TEXT_MUTED, font=font(8)
            ).pack(side="left")
        if not getattr(self._expander, "expanded", False):
            # v3.9.55 — saat ⤢ diperbesar (kartu disembunyikan), JANGAN
            # re-pack zona (restore milik TableExpander yang mengelola).
            zone.pack(fill="x", padx=12, pady=(10, 0), before=self._tcard)

    def _on_skor_row_click(self, resto: str):
        """v3.9.55 — F3: klik baris skor → TOGGLE filter kolom Resto
        (klik = fokus tabel ke resto itu; klik lagi = lepas). Filter "/7
        header ⧩ disinkronkan (ikon corong aktif)."""
        cur = self._col_sel.get("Resto")
        if isinstance(cur, list) and len(cur) == 1 and str(cur[0]) == str(resto):
            self._col_sel["Resto"] = None
            if self.header_filters is not None:
                self.header_filters.set_selected("Resto", None)
        else:
            self._col_sel["Resto"] = [resto]
            if self.header_filters is not None:
                self.header_filters.set_selected("Resto", [resto])
        self._refresh()

    @staticmethod
    def _fmt_num_skor(v) -> str:
        """Format Σ|selisih| gaya Indonesia (pola _fmt_num view lain;
        0 → '-' — resto tanpa selisih tak masuk leaderboard)."""
        try:
            v = float(v)
        except (TypeError, ValueError):
            return str(v)
        if v == 0:
            return "-"
        if v == int(v):
            return fmt_int_id(v)
        return f"{v:,.1f}".replace(",", "\u00a0").replace(".", ",").replace(
            "\u00a0", ".")

    # --------------------------------------------------------- EXPORT --
    def _export_options_dialog(self):
        """v3.9 — dialog opsi export: tambah kolom hasil audit atau tidak.

        Permintaan user: "waktu ekspor tambahin hasil auditnya aja tapi ada
        opsi buat tambahin kolom tersebut atau tidak". Return list kolom
        audit terpilih (bisa kosong) atau None bila dibatalkan.
        """
        parent = self.winfo_toplevel()
        win = tk.Toplevel(parent)
        win.title("Opsi Export — Rekap Selisih IN")
        win.configure(bg=C_CARD)
        win.transient(parent)
        win.resizable(False, False)
        with contextlib.suppress(Exception):
            win.grab_set()

        result = {"cols": None}

        body = tk.Frame(win, bg=C_CARD)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(body, text="💾 Export Rekap Selisih IN per Resto",
                 bg=C_CARD, fg=C_HEADER, font=font(11, "bold")).pack(
            anchor="w")

        vars_ = {}
        for col in AUDIT_EXPORT_COLUMNS:
            v = tk.BooleanVar(value=True)
            vars_[col] = v
            row = tk.Frame(body, bg=C_CARD)
            row.pack(fill="x", pady=2)
            cb = ttk.Checkbutton(row, text=col, variable=v)
            cb.pack(side="left")

        btns = tk.Frame(body, bg=C_CARD)
        btns.pack(fill="x", pady=(12, 0))

        def _ok():
            result["cols"] = [c for c, v in vars_.items() if v.get()]
            win.destroy()

        from .widgets import AccentButton
        # v3.9.59 — FIX 2f-13: label kanon '💾 Export Excel' (dulu '💾
        # Export Sekarang' — varian ke-4 label export di 5 permukaan).
        AccentButton(btns, text="💾 Export Excel", command=_ok).pack(
            side="right")
        GhostButton(btns, text="Tanpa Kolom Audit",
                    command=lambda: (result.update(cols=[]),
                                     win.destroy())).pack(
            side="right", padx=(0, 8))
        GhostButton(btns, text="✕ Batal",
                    command=win.destroy).pack(side="left")

        win.bind("<Escape>", lambda e: win.destroy())
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()
                                     - win.winfo_reqwidth()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height()
                                     - win.winfo_reqheight()) // 2
        win.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        win.wait_window()
        return result["cols"]

    def _on_export(self):
        """v3.8/v3.9 — Export rekap Selisih IN per resto ke Excel.

        Dialog opsi (v3.9) → pilih file → export async. Semua baris dalam
        rentang tanggal aktif (default 1–31 bulan berjalan); filter
        tampilan (⧩ / Hanya Selisih ≠ 0) tidak ikut — export = REKAP
        lengkap per resto + kolom hasil audit sesuai pilihan.
        """
        if (self.audit_df is None or self.audit_df.empty) and \
                (self.data is None or self.data.empty):
            messagebox.showwarning(
                "Export", "Belum ada data. Jalankan pipeline dulu.",
                parent=self.winfo_toplevel())
            return
        audit_cols = self._export_options_dialog()
        if audit_cols is None:
            return          # dibatalkan
        filepath = filedialog.asksaveasfilename(
            title="Simpan Rekap Selisih IN per Resto",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="selisih_in_per_resto.xlsx",
            parent=self.winfo_toplevel(),
        )
        if not filepath:
            return
        self._do_export(filepath, audit_cols)

    def _do_export(self, filepath: str, audit_cols: list):
        """Export inti (v3.9) — dipisah dari _on_export supaya bisa
        dipanggil langsung oleh test tanpa dialog."""
        # FIX B-02: jalur export ikut validasi konsisten (bukan fallback
        # senyap ke 1/31 seperti sebelumnya).
        tgl_start = validated_tgl_entry(self.tgl_start_var, lo=-31, hi=31,
                                        fallback=1, label="Tanggal awal",
                                        parent=self)
        tgl_end = validated_tgl_entry(self.tgl_end_var, lo=-31, hi=31,
                                      fallback=31, label="Tanggal akhir",
                                      parent=self)
        if tgl_start > tgl_end:
            tgl_start, tgl_end = tgl_end, tgl_start

        def work():
            base = self._cached_base
            if base is None:
                base = self._compute_base()
            df = build_selisih_export_df(base, tgl_start, tgl_end,
                                         audit_cols=audit_cols)
            if df.empty:
                return None
            # v3.9.59 — FIX 2f-04 (pola app._export_excel 6a-02): export
            # NON-atomik dulu — exception/styling-gagal DI DALAM blok
            # `with ExcelWriter` membuat pandas close() MENYIMPAN PAKSA
            # file PARSIAL ke path tujuan → export lama yang baik di
            # path sama HILANG. Kini tulis ke tmp → os.replace atomik;
            # gagal → tmp dihapus, file tujuan tak tersentuh.
            tmp_path = filepath + ".tmp.xlsx"
            _ok = False
            try:
                with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                    write_selisih_sheet(writer, df)
                os.replace(tmp_path, filepath)
                _ok = True
                return filepath, len(df)
            finally:
                if not _ok:
                    with contextlib.suppress(OSError):
                        os.unlink(tmp_path)

        def done(res):
            if res is None:
                messagebox.showwarning(
                    "Export", "Tidak ada baris dalam rentang tanggal "
                              f"{tgl_start}–{tgl_end}.",
                    parent=self.winfo_toplevel())
                return
            path, n = res
            self.status_var.set(
                f"Export {fmt_int_id(n)} baris → {path}")
            messagebox.showinfo(
                "Export Berhasil",
                f"Rekap Selisih IN per resto ({fmt_int_id(n)} baris)\n"
                f"di-export ke:\n{path}",
                parent=self.winfo_toplevel())

        def on_error(e):
            messagebox.showerror(
                "Export Gagal", f"Tidak bisa export:\n{e}",
                parent=self.winfo_toplevel())

        run_async(self, work, done, overlay=self.overlay,
                  loading_text="Mengekspor rekap Selisih IN…",
                  on_error=on_error)

    # ------------------------------------------------------------ FILTERS
    def _on_tanggal_change(self):
        # FIX B-12 (audit 2-b, kelas yang sama dgn validated_tgl_entry):
        # int(float()) melantai pecahan SENYAP ("7.9" → 7) — kini pecahan
        # DITOLAK dengan pesan status (hanya bilangan bulat).
        def _strict(raw):
            try:
                f = float(raw)
                return int(f) if f == int(f) else None
            except (TypeError, ValueError, OverflowError):
                return None
        s = _strict(self.tgl_start_var.get())
        e = _strict(self.tgl_end_var.get())
        if (s is None or e is None
                or not (-31 <= s <= 31 and -31 <= e <= 31)):
            self.status_var.set("Tanggal harus angka -31..31 (contoh: 1–31).")
            return
        if s > e:
            s, e = e, s
            self.tgl_start_var.set(str(s))
            self.tgl_end_var.set(str(e))
        # v3.9.27 — AUTO-UPGRADE mode: rentang minta tanggal NEGATIF (bulan
        # lalu) sedangkan mode masih "Bulan Ini" (varian audit tanpa baris
        # bulan lalu) → pindahkan otomatis ke "📆 Lalu + Ini" supaya baris
        # bulan lalu benar-benar ADA di varian audit aktif (tanpa ini:
        # tabel kosong senyap — baris negatif tak pernah ada di varian
        # bulan-ini). Arah sebaliknya TIDAK otomatis (varian penuh tetap
        # sah utk rentang 1..31 — perilaku pra-v3.9.27).
        if s < 0 and not self._mode_bulan_lalu \
                and self._audit_bulan_ini is not None:
            self._mode_bulan_lalu = True
            if getattr(self, "mode_bar", None) is not None:
                self.mode_bar.set_active_silent(1)
            self._apply_audit_mode()
            self._render_kpi_chips()
        self._refresh()

    def _reset_filter(self):
        # v3.9.27 — reset ikut MODE default user: "hitung bulan ini aja"
        # (varian audit bulan berjalan + rentang 1..31; dulu rentang saja
        # yang di-reset — kini varian + segmen ikut, konsisten dgn
        # load_data).
        self._mode_bulan_lalu = False
        if getattr(self, "mode_bar", None) is not None:
            self.mode_bar.set_active_silent(0)
        self._apply_audit_mode()
        self._render_kpi_chips()
        self.tgl_start_var.set("1")    # v3.8: 1–31 bulan berjalan saja
        self.tgl_end_var.set("31")
        self.only_selisih_var.set(True)
        self._reset_filter_states()
        self._apply_default_kategori()   # v3.9.22 — default Deviasi
        self._refresh()

    # -------------------------------------------------------------- SORT
    @staticmethod
    def _parse_num_id(s):
        """FIX B-01 (audit 2-b): parser sort format Indonesia (copy persis
        deviasi_view v3.9.6): '1.234' = 1234, '(1.234)' = -1234,
        '-' = 0, '12,5' = 12.5. Parser default widgets menganggap '1.234'
        = 1.234 dan '(12,5)' = -125 — SALAH utk format Indonesia; kolom
        numerik view ini diformat _fmt_num Indonesia."""
        s = str(s).replace("%", "").replace("—", "").strip()
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

    def _sort_by(self, col: str, reverse: bool = True, tree=None):
        # FIX B-08 (audit 2-b): sort saat render batch → ANTRE (pola
        # _pending_sort komparasi/laporan v3.9.5 — view ini terlewat).
        if self._busy and tree is None:
            self._pending_sort = (col, reverse)
            return  # render batch masih berjalan — sort ditunda
        tree = tree if tree is not None else self.tree
        # FIX B-01: parser angka Indonesia utk kolom numerik (sort numerik
        # benar — bukan string/fallback-salah).
        parse = self._parse_num_id if col in _NUM_COLS else None
        sort_tree_by_column(tree, col, reverse=reverse, parse=parse)
        # FIX B-03 (audit 2-b): delete+reinsert me-reset tag PER-CELL →
        # pasang ulang (identik deviasi/komparasi/laporan).
        self._reapply_cell_tags(tree)

    def _auto_fit(self):
        """v3.4 — auto-fit lebar semua kolom ke konten."""
        auto_fit_columns(self.tree)

    # ------------------------------------------------- ⛶ PERBESAR (clone)
    def _maximize(self):
        def filter_setup(new_tree):
            # v3.6: funnel ⧩ + sort jalan juga di window besar
            # FIX B-02 (audit 2-b): on_after_filter — tag minus per-cell
            # dipasang ulang setelah filter clone REBUILD (mirror deviasi;
            # fix v3.9.5 19-a #3 dulu hanya sampai komparasi/laporan).
            attach_clone_filters(
                new_tree, [c[0] for c in COLUMNS],
                get_values=self._col_values,
                on_sort=lambda c, d, t=new_tree: self._sort_by(c, reverse=d,
                                                               tree=t),
                on_after_filter=lambda t=new_tree:
                    self._reapply_cell_tags(t))

        win, new_tree = open_tree_maximized(
            self.tree, "Rekap Selisih IN & Audit Rekonsiliasi",
            setup_tags=lambda t: self._setup_tags(t),
            on_double_click=self._on_double_click,
            on_filter_setup=filter_setup,
            # FIX 35-c1 (BUG-E1/audit 34-e): clone ⛶ re-insert baris →
            # tag per-cell minus TERRESET; tanpa hook ini clone Layar
            # Penuh kehilangan merah per-sel (mirror deviasi_view:1330
            # / InDetailPopup._maximize).
            on_render_done=self._reapply_cell_tags)
        return win, new_tree

    # ------------------------------------------------- DOUBLE-CLICK POPUP
    def _on_double_click(self, event):
        if self.data is None or self.data.empty:
            return
        tree = event.widget
        row_iid = tree.identify_row(event.y)
        if not row_iid:
            return
        values = tree.item(row_iid, "values")
        if not values:
            return
        col_ids = list(tree["columns"])
        row = dict(zip(col_ids, values))
        # FIX 6d2-01 + 6d2-05 — resolve kunci + nilai MENTAH dari payload
        # _keys (iid → raw; iid stabil lintas sort/clone ⛶ — sort memakai
        # move/reinsert dgn iid sama, clone menyalin iid sumber). Display
        # resto/barang/tgl identik dgn raw (kolom string/int), tapi chip
        # bm/selisih WAJIB raw: display '1.500' (format Indonesia)
        # di-parse float EN = 1.5 (salah skala 1000×, bug 6d2-01).
        # Fallback (payload lama / _keys kosong): parse display via
        # _parse_num_id — parser Indonesia, BUKAN parser float EN lama.
        raw = (self._keys.get(row_iid)
               if isinstance(self._keys, dict) else None)
        resto = (raw.get("resto") if raw else None) or row.get("Resto")
        barang = (raw.get("barang") if raw else None) \
            or row.get("Nama Barang")
        tgl = (raw.get("tgl") if raw else None)
        if tgl is None:
            tgl_txt = str(row.get("Tanggal") or "")
            try:
                tgl = int(float(tgl_txt.replace(",", "")))
            except (TypeError, ValueError):
                tgl = None
        if not barang or tgl is None:
            return

        det = self._detail_for(resto, barang, tgl)
        if det is None:
            return

        # ringkasan utk chip popup — FIX 6d2-01: nilai MENTAH dari payload
        # _keys (diformat _fmt_num → '1.500' via fmt_int_id); fallback
        # parse display Indonesia _parse_num_id (bukan float EN lama).
        if raw is not None:
            row_summary = {"bm": raw.get("bm") or 0.0,
                           "selisih": raw.get("selisih") or 0.0}
        else:
            row_summary = {
                "bm": self._parse_num_id(row.get("Barang Masuk")),
                "selisih": self._parse_num_id(row.get("Selisih IN")),
            }
        InDetailPopup(self.winfo_toplevel(), resto, barang, tgl, det,
                      row_summary=row_summary)

    def _detail_for(self, resto, barang, tgl) -> Optional[pd.DataFrame]:
        """Ambil detail IN utk (resto, barang, tgl)."""
        det = self.in_detail
        if det is None or det.empty:
            # tidak ada detail IN (mis. sumber 42.05/3224/9901 kosong) —
            # tampilkan popup kosong supaya user tahu tidak ada dokumen
            return pd.DataFrame(columns=["NAMA RESTO", "Nama Barang",
                                         "Tanggal", "Value", "Nomor",
                                         "Nomor PO", "#Tgl/Jam Pembuatan IT",
                                         "SOURCE IN", "JENIS"])
        d = det
        d = d[d["NAMA RESTO"].astype(str) == str(resto)]
        d = d[d["Nama Barang"].astype(str) == str(barang)]
        t = pd.to_numeric(d["Tanggal"], errors="coerce")
        d = d[t == tgl]
        if d.empty:
            return d
        return d.reset_index(drop=True)

    # ------------------------------------------------------------ SHOW ---
    def _show_empty(self):
        self.content.pack_forget()
        self.empty.pack(fill="both", expand=True, padx=12, pady=12)

    def _show_content(self):
        self.empty.pack_forget()
        self.content.pack(fill="both", expand=True)
        # posisi kpi_card dikelola penuh oleh _render_kpi_chips()
        # (pack before tabel card / pack_forget)
