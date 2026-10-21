"""
nominal_common.py — v3.9.34 helper BERSAMA perhitungan Nominal Deviasi
(Harga 41.09 × Qty Deviasi). Sebelum v3.9.34 logika ini hanya hidup di
nominal_deviasi_view.py (mode 💰 Nominal (H)); kini dipakai 4 tempat:

  1. mode  💰 Nominal (H)        tab 📋 Laporan Deviasi (per pasangan)
  2. kolom Nominal               tab 📦 Deviasi GR & 🧩 Deviasi PCS
  3. kolom Nominal               mode ⚖ Komparasi (tab Laporan Deviasi —
                                  harga × GR Saat Ini)
  4. tab   🧮 Nominal Deviasi    (BARU — Σ per resto + popup rincian)

v3.9.36 — TAMBAHAN: hitung_nominal_lalu_pairs — pasangan per-barang
dari FILE deviasi (parse_deviasi_file tab ⚖ Komparasi, diteruskan app
lewat lalu_provider): bulan TERBARU di file + minggu TERAKHIR per
pasangan (penutupan bulan) → Nominal Lalu = harga × DEV Lalu. Dipakai
popup rincian tab 🧮 (kolom 'Nominal Deviasi Bulan Lalu').

v3.9.38 — ATURAN "QTY DEVIASI 0 TAK PERLU CARI HARGA" (user:
"Kuantiti Deviasi 0 takperlu cari harga. Cek juga keseluruhan
terkait ini"): pasangan ber-qty-deviasi PERSIS 0 → lookup harga
DILEWATI (Harga None, Harga Tampil '-', tanpa label '*') dan
Nominal = 0.0 (BUKAN None) → pasangan itu TIDAK dihitung sebagai
'tanpa harga' (kolom Tanpa Harga / popup tanpa harga / footer mode
💰) dan tetap netral di Σ — dulu baris qty-0 tanpa harga ikut
terhitung 'tanpa harga' menyesatkan. Berlaku di hitung_nominal_pairs,
hitung_nominal_lalu_pairs, kolom Nominal tab 📦 Deviasi GR/PCS
dan mode ⚖ Komparasi.

v3.9.38 — SUMBER UTAMA 'Nominal Lalu' = KOLOM NOMINAL DEVIASI MILIK
FILE (angka resmi laporan bulan lalu; parse_deviasi_file → 'Nominal
Deviasi Lalu'). Dulu v3.9.36 menghitung ulang harga 41.09 SEKARANG ×
DEV Lalu → harga snapshot beda bulan → nominal menyimpang dari
laporan resmi (temuan user BUMBU PASTA KUAH (V.20): 41.09 sekarang
107,6386854/GR — SAMA dgn hitungan manual user — vs file
20.AGUSTUS ±113,048/GR → selisih nominal ±2,34jt utk 1 baris MLGPAR
W4). Kolom file kosong/NaN → fallback hitung ulang (perilaku lama).

v3.9.41 — MINGGU TER-COCOK (user: "Nominal deviasi pembanding dari
bulan lalu sesuaikan week nya jika week 1 maka ambil data week 1
juga"): param h (tanggal analisa) → minggu file yang MEMUAT H
(H 1-7 → WEEK 1 / cut-off 7; 8-14 → WEEK 2 / 14; 15-31 → WEEK 3-4 /
25 — mirror _h_to_week_target komparasi v3.9.22). Baris minggu
persis itu yang dipilih; minggu itu tidak ada di file → fallback
minggu TERBESAR ≤ target (perbandingan periode terdekat), lalu
TERKECIL > target (file hanya punya minggu setelahnya). h=None →
perilaku lama (minggu terakhir = penutupan bulan — kompatibilitas
pemanggil lama). Kolom internal '_minggu' = label minggu terpilih
(dipakai label popup/footer supaya minggu pembanding JELIHAT).

v3.9.63 — RESTRUKTURISASI TAB 🧮 NOMINAL DEVIASI (user: "kolom N
Barang dan Tanpa harga hapus aja diganti dengan nominal deviasi per
kategori ... dan itu buat anak tab baru di nominal deviasi yang
menampilkan secara global"):
  - agregasi_nominal_per_resto kini juga menghasilkan kolom 'COM
    Deviasi' + 'Biaya Packaging' (Σ nominal pasangan per klas kategori:
    substring case-insensitive 'COM' / 'PACKAGING' pada KATEGORI
    pasangan — 'COM DEVIASI - RESTO'/'- CATERING' → COM,
    'Biaya Packaging - RESTO' → PACKAGING; kategori lain hanya masuk
    kolom total) DAN menempel kolom KATEGORI pada frame pasangan
    (dipakai klasifikasi + anak tab Tanpa Harga).
  - pasangan_tanpa_harga_global — BARU: pasangan tanpa harga dari data
    MENTAH (TANPA filter kategori tab utama — global semua kategori &
    resto) utk ANAK TAB 'Tanpa Harga' (menggantikan popup double-click
    kolom 'Tanpa Harga' yang kolomnya dihapus).
  - hitung_persen_kenaikan / fmt_pct_cell — BARU: kolom 'Persen
    Kenaikan/Penurunan' tab 🧮 ((H − Lalu) ÷ |Lalu| × 100; NaN bila
    lalu kosong/0 dgn H ≠ 0 — tak terdefinisi; 0 bila keduanya 0).

ATURAN HARGA (identik sejak v3.9.32, kini satu sumber kebenaran):
  - harga_map   : {barang: (harga|None, satuan41-upper)} — global dari
                  file 41.09 (folder 09.Harga); Harga = Nilai Saldo
                  Akhir ÷ Kuantitas Saldo Akhir.
  - satuan sama (atau salah satu tak diketahui) → harga langsung.
  - satuan beda → normalisasi via peta rasio v3.9.31 (42.05+32.24):
        harga_rekap = harga41 × rasio(satuanRekap) / rasio(satuan41.09)
  - rasio tak men-cover → harga AS-IS berlabel satuan asli + penanda
    '*' dan nominal TIDAK dihitung (None) — transparan, bukan angka
    keliru; tidak ikut TOTAL.
  - barang tak ada di 41.09 / harga None → nominal None (tampil '-').
  - Qty Deviasi PERSIS 0 → TANPA lookup harga; Nominal 0.0 (bukan
    None — tak dihitung 'tanpa harga'; v3.9.38).

Qty Deviasi untuk pasangan = JENIS '3.DEVIASI' baris Tanggal H
(= SO − SALDO AKHIR sistem — nilai kolom Deviasi tab 📦 Deviasi GR).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.pipeline.konversi_satuan import lookup_rasio


# ---------------------------------------------------------------------------
# NORMALISASI SATELIT
# ---------------------------------------------------------------------------
def norm_sat(v) -> str:
    """Satuan → upper/strip; NaN/None → ''."""
    try:
        s = str(v).strip().upper()
    except Exception:
        return ""
    return "" if s in ("NAN", "NONE") else s


# ---------------------------------------------------------------------------
# FORMAT ANGKA INDONESIA (dipakai kolom Nominal/Harga semua tabel)
# ---------------------------------------------------------------------------
def fmt_harga_id(v) -> str:
    """Harga: pecahan → 2 desimal (18,25); bulat → 1.234 (fmt_int_id)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    av = abs(v)
    if av == int(av):
        # fmt_int_id lokal (hindari import widgets — modul UI-agnostic;
        # hasil identik: titik ribuan)
        s = f"{av:,.0f}".replace(",", ".")
        return s
    return f"{av:,.2f}".replace(",", "X").replace(".", ",") \
        .replace("X", ".")


def fmt_nominal_cell(val) -> str:
    """Nominal/qty: bulat → fmt ribuan titik; pecahan → 2 desimal koma;
    negatif dalam kurung; None/NaN/0 → '-'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "-"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    if v == 0:
        return "-"
    neg = v < 0
    av = abs(v)
    if av == int(av):
        s = f"{av:,.0f}".replace(",", ".")
    else:
        s = f"{av:,.2f}".replace(",", "X").replace(".", ",") \
            .replace("X", ".")
    return f"({s})" if neg else s


def fmt_rp_cell(val) -> str:
    """v3.9.51 — CURRENCY RUPIAH utk kolom nominal (user: "Semua data
    nominal diberi format Currency Rp"): 'Rp 1.825' / 'Rp 1.825,50' /
    negatif '(Rp 1.825)'; None/NaN/0 → '-' (konvensi sel nominal kosong
    — konsisten fmt_nominal_cell supaya 0=tanpa-harga & NaN tetap netral
    secara visual). Dipakai kolom Nominal tab 📦/🧩 Deviasi, mode ⚖
    Komparasi, mode 💰 Nominal (H), tab 🧮 Nominal Deviasi + popup-nya."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "-"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    if v == 0:
        return "-"
    neg = v < 0
    av = abs(v)
    if av == int(av):
        s = f"{av:,.0f}".replace(",", ".")
    else:
        s = f"{av:,.2f}".replace(",", "X").replace(".", ",") \
            .replace("X", ".")
    return f"(Rp {s})" if neg else f"Rp {s}"


def hitung_persen_kenaikan(h_val, l_val):
    """v3.9.63 — persen kenaikan/penurunan Nominal Deviasi vs bulan lalu
    (kolom baru tab 🧮, user: "Persen kenaikan/penurunan (bisa sort)"):
    (H − Lalu) ÷ |Lalu| × 100 (ber-tanda — positif = kenaikan).

    Tak terdefinisi (→ None, tampil '-'): H atau Lalu kosong/NaN, atau
    Lalu PERSIS 0 dengan H ≠ 0 (pembagi nol — kenaikan tak terhingga
    tak bisa direpresentasikan sort-able). Keduanya 0 → 0.0 (tak
    berubah). Absolut Lalu dipakai supaya ARAH tetap dari (H−Lalu)
    meski Lalu minus (perbandingan vs besaran bulan lalu — bukan
    flip tanda)."""
    def _f(v):
        try:
            if v is None or pd.isna(v):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    h, l = _f(h_val), _f(l_val)
    if h is None or l is None:
        return None
    if l == 0.0:
        return 0.0 if h == 0.0 else None
    return (h - l) / abs(l) * 100.0


def fmt_pct_cell(val) -> str:
    """v3.9.63 — format sel persen kenaikan/penurunan: '+12,5%' /
    '-8,3%' / '0,0%' (desimal koma Indonesia, 1 digit); None/NaN/'-'
    → '-' (tak terdefinisi — lihat hitung_persen_kenaikan).
    v3.9.64 — FIX (audit 15-a N11): (a) pemisah RIBUAN ('+1.234,5%' —
    dulu '+12345,5%'; parser sort _parse_num_id sudah ribuan-aware);
    (b) pembulatan ke 0 → '0,0%' TANPA tanda (dulu '+0,0%' utk nilai
    0<v<0,05 — inkonsisten dgn 0 persis)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "-"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    if pd.isna(v) or np.isinf(v):
        return "-"
    if round(v, 1) == 0:
        return "0,0%"
    s = f"{v:+,.1f}".replace(",", "X").replace(".", ",") \
        .replace("X", ".")
    return s + "%"


# ---------------------------------------------------------------------------
# LOOKUP HARGA PER PASANGAN (barang, satuan-rekap)
# ---------------------------------------------------------------------------
def norm_barang_harga_key(v) -> str:
    """v3.9.55 — normalisasi kunci nama barang utk lookup harga 41.09
    (strip + rapat spasi + UPPER). HARUS identik dgn
    fn_4109._norm_barang_key (duplikat lokal — nominal_common tak boleh
    import modul pipeline fn_4109 yg berat/ber-IO; kunci dinyatakan
    eksplisit di kedua sisi + dikuji test)."""
    s = re.sub(r"\s+", " ", str(v).strip()).upper()
    return "" if s in ("", "NAN", "NONE") else s


def lookup_harga_pair(harga_map: dict | None,
                      konversi_map: dict | None,
                      barang, satuan_rekap) -> tuple:
    """→ (harga_norm: float | None, label: str, bintang: bool)

    harga_norm = harga per SATUAN REKAP pasangan (siap × qty deviasi).
      None  → nominal tak bisa dihitung (tanpa harga / tak terkonversi)
      label → satuan hasil normalisasi (utk display harga)
      bintang → True bila satuan tak ter-cover rasio (fallback '*')
    v3.9.55 — kunci barang DINORMALISASI (parity build_harga_map):
    selisih kapitalisasi/spasi nama barang vs 41.09 tak lagi membuat
    nominal '-' senyap (akar keluhan "ada deviasi yang tidak ada nominal
    nya") — pasangan tetap fallback label '-'/'*' bila benar2 tak ada
    harga di 41.09 / satuan tak terkonversi.
    """
    b = norm_barang_harga_key(barang)
    entry = (harga_map or {}).get(b)
    if entry is None:
        # v3.9.55 — fallback exact-string lama (peta dibangun versi lama
        # / peta buatan test dgn kunci asli) supaya tak ada regresi.
        entry = (harga_map or {}).get(str(barang).strip())
    if entry is None:
        return None, "-", False
    h41, sat41 = entry
    if h41 is None:
        return None, "-", False
    sat_rekap = norm_sat(satuan_rekap)
    if not sat41 or not sat_rekap or sat41 == sat_rekap \
            or sat_rekap == "-":
        # satuan sama (atau tak diketahui) → harga langsung
        return float(h41), (sat41 or sat_rekap or ""), False
    # v3.9.55 — konversi_map BER-KUNCI nama asli (build_konversi_map tak
    # men-normalisasi kapitalisasi) → lookup_rasio memakai string ASLI
    # pasangan (bukan kunci normalisasi 41.09); fallback kunci-normalisasi
    # utk peta yg kebetulan ber-kunci kapital.
    _b_orig = str(barang).strip()
    r_rekap, _t1 = lookup_rasio(konversi_map, _b_orig, sat_rekap)
    r_41, _t2 = lookup_rasio(konversi_map, _b_orig, sat41)
    if not (r_rekap and r_41) and b != _b_orig:
        r_rekap2, _t3 = lookup_rasio(konversi_map, b, sat_rekap)
        r_41_2, _t4 = lookup_rasio(konversi_map, b, sat41)
        r_rekap = r_rekap or r_rekap2
        r_41 = r_41 or r_41_2
    if r_rekap and r_41:
        return float(h41) * r_rekap / r_41, sat_rekap, False
    # tak bisa dikonversi → harga as-is berpenanda '*'
    return None, f"{fmt_harga_id(float(h41))} {sat41}*", True


# ---------------------------------------------------------------------------
# NORMALISASI KUNCI FILE DEVIASI (mirror komparasi — v3.9.36)
# ---------------------------------------------------------------------------
def _norm_resto_lalu(v) -> str:
    """Mirror komparasi_deviasi_view._norm_resto: '1041.BDGUKU' /
    'B.1001.MLGPAR' / 'BDGUKU' → 'BDGUKU' (upper + strip + segmen
    setelah titik TERAKHIR). Duplikat LOKAL — nominal_common tidak
    boleh import komparasi_deviasi_view (komparasi sudah meng-import
    nominal_common sejak v3.9.34 → circular)."""
    s = str(v).strip().upper()
    if "." in s:
        s = s.split(".")[-1].strip()
    return s


def _norm_name_lalu(v) -> str:
    """Mirror komparasi_deviasi_view._norm_name: upper + rapat spasi
    ganda (duplikat lokal — alasan _norm_resto_lalu)."""
    return re.sub(r"\s+", " ", str(v).strip().upper())


# ---------------------------------------------------------------------------
# PASANGAN NOMINAL TANGGAL H (port inti _compute_nominal v3.9.32)
# ---------------------------------------------------------------------------
def hitung_nominal_pairs(data: pd.DataFrame | None, h: int,
                         harga_map: dict | None,
                         konversi_map: dict | None) -> pd.DataFrame:
    """Frame per pasangan tanggal H:
    [Nama Barang, Resto, Satuan, Harga, Harga Tampil, Qty Deviasi,
     Nominal] — urut |Nominal| MENURUN (pasangan tanpa nominal paling
    bawah, urut |qty deviasi|).

    Qty deviasi = JENIS '3.DEVIASI' Tanggal H (jumlah per pasangan).
    Dtype float64 EKSPLISIT utk Harga/Nominal (semua-None → kolom
    object → .abs() TypeError di worker — bug v3.9.32, dijaga di sini).
    DataFrame kosong bila tak ada baris DEVIASI tanggal H.
    """
    if data is None or data.empty:
        return pd.DataFrame()
    h = int(h)

    tnum = pd.to_numeric(data["Tanggal"], errors="coerce")
    _jenis = data["JENIS"].astype(str)
    dev = data[(_jenis == "3.DEVIASI") & (tnum == h)]
    # v3.9.44 — SALDO-ONLY FALLBACK (mirror mask saldo-only
    # deviasi_view v3.9.32; akar "BUMBU PASTA KUAH MLGPAR masih belum
    # ada"): pasangan 42.17-only (fn_4217 HARDCODE Tanggal=1 — contoh
    # nyata: plain 100383 saldo 84.000 @MLGPAR tanpa rekap) hanya punya
    # baris 3.DEVIASI di t=1 → filter Tanggal==h (h analisa 25/26)
    # membuangnya SENYAP dari tab 🧮 & mode 💰 padahal tab Deviasi GR
    # menampilkan pasangan itu (Deviasi = 0 − saldo). Baris 3.DEVIASI
    # t=1 pasangan SALDO-ONLY (ada 2.SALDO AKHIR@t1 · TANPA baris
    # rekap 1.SO/5.BARANG MASUK non-nol · belum termuat di dev) ikut
    # dihitung — pasangan ber-rekap tidak tersentuh (nilai tak berubah).
    if h != 1:
        _t1_dev = (_jenis == "3.DEVIASI") & (tnum == 1)
        if bool(_t1_dev.any()):
            _key = (data["Nama Barang"].astype(str) + "\x1f"
                    + data["NAMA RESTO"].astype(str))
            _dev_keys = (set(_key.loc[dev.index]) if not dev.empty
                         else set())
            _nil = pd.to_numeric(data["NILAI"], errors="coerce").fillna(0)
            _rk_keys = set(_key.loc[(_jenis.isin(("1.SO", "5.BARANG MASUK")))
                            & (_nil != 0)])
            _saldo_t1_keys = set(
                _key.loc[(_jenis == "2.SALDO AKHIR") & (tnum == 1)])
            _extra = data[_t1_dev
                          & ~_key.isin(_dev_keys)
                          & ~_key.isin(_rk_keys)
                          & _key.isin(_saldo_t1_keys)]
            if not _extra.empty:
                dev = pd.concat([dev, _extra], ignore_index=True)
    if dev.empty:
        return pd.DataFrame()
    dev = dev.copy()
    dev["NILAI"] = pd.to_numeric(dev["NILAI"], errors="coerce").fillna(0)

    # v3.9.42 — audit 61-a P3: SATUAN dinormalkan SEBELUM groupby —
    # 'GR' vs 'GR ' dulu membuat 2 grup → 2 baris pasangan KEMBAR di
    # popup per-resto (Σ tetap benar tapi baris dobel membingungkan).
    if "SATUAN" in dev.columns:
        dev["SATUAN"] = dev["SATUAN"].map(
            lambda v: norm_sat(v) if norm_sat(v) else "")

    grouped = (dev.groupby(["Nama Barang", "NAMA RESTO", "SATUAN"],
                           as_index=False, dropna=False)["NILAI"].sum())
    grouped = grouped.rename(columns={
        "NAMA RESTO": "Resto", "SATUAN": "Satuan",
        "NILAI": "Qty Deviasi"})
    grouped["Nama Barang"] = grouped["Nama Barang"].astype(str)
    grouped["Resto"] = grouped["Resto"].astype(str)
    grouped["Satuan"] = grouped["Satuan"].map(
        lambda v: norm_sat(v) if norm_sat(v) else "-")

    harga_vals = []
    harga_disp = []
    nominal_vals = []
    for _, r in grouped.iterrows():
        b = str(r["Nama Barang"]).strip()
        sat_rekap = norm_sat(r["Satuan"])
        # v3.9.38 — Kuantiti Deviasi 0 → TAK PERLU CARI HARGA (user:
        # "Kuantiti Deviasi 0 takperlu cari harga"): nominal pasti 0;
        # Harga None + Harga Tampil '-' (tanpa label '*') + Nominal
        # 0.0 — pasangan TIDAK dihitung 'tanpa harga' (isna) sehingga
        # kolom Tanpa Harga / popup tanpa harga / footer mode 💰 tak
        # menyesatkan (dulu qty-0 tanpa harga ikut terhitung).
        if float(r["Qty Deviasi"]) == 0.0:
            harga_vals.append(None)
            harga_disp.append("-")
            nominal_vals.append(0.0)
            continue
        harga, label, _bintang = lookup_harga_pair(
            harga_map, konversi_map, b, sat_rekap)
        if harga is not None:
            nom = harga * float(r["Qty Deviasi"])
            harga_disp.append(f"{fmt_harga_id(harga)} {label}")
        else:
            nom = None
            harga_disp.append(label or "-")
        harga_vals.append(harga)
        nominal_vals.append(nom)

    grouped["Harga"] = pd.Series(harga_vals, dtype="float64")
    grouped["Harga Tampil"] = harga_disp
    grouped["Nominal"] = pd.Series(nominal_vals, dtype="float64")

    grouped["_absnom"] = grouped["Nominal"].abs().fillna(0)
    grouped["_absqty"] = grouped["Qty Deviasi"].abs()
    grouped = (grouped.sort_values(
        ["_absnom", "_absqty"], ascending=[False, False],
        kind="mergesort").drop(columns=["_absnom", "_absqty"]))
    grouped = grouped.reset_index(drop=True)
    return grouped[["Nama Barang", "Resto", "Satuan", "Harga",
                    "Harga Tampil", "Qty Deviasi", "Nominal"]]


# ---------------------------------------------------------------------------
# AGREGASI PER RESTO (tab 🧮 Nominal Deviasi — v3.9.34)
# ---------------------------------------------------------------------------
# v3.9.63 — klas kategori utk kolom 'COM Deviasi' / 'Biaya Packaging'.
# v3.9.64 — FIX (audit 15-a R1): token kini dicocokkan dgn WORD-BOUNDARY
# regex (\bCOM\b / \bPACKAGING\b) — substring polos membuat kategori
# semacam 'COMMERCIAL'/'COMPLIMENT' terhitung COM dan 'REPACKAGING'
# terhitung PACKAGING (probe audit; domain nilai master DBS tak bisa
# diverifikasi — boundary = aman utk semua varian kanonik:
# 'COM DEVIASI - RESTO' / '- CATERING' / 'Biaya Packaging - …' tetap
# cocok karena COM/PACKAGING-nya berdiri sebagai kata utuh).
# Kategori lain — mis. 'DEVIASI'/'TEPAT'/blank — hanya masuk kolom
# total. Kategori yang memuat KEDUA token (mis. label gabungan virtual
# 'DEVIASI (COM + PACKAGING)' bila suatu saat jadi nilai data) dihitung
# di KEDUA kolom klas (per kategori — kolom total tetap Σ pasangan).
_KAT_COM_RE = r"\bCOM\b"
_KAT_PKG_RE = r"\bPACKAGING\b"


def _attach_kategori_pairs(pairs: pd.DataFrame,
                           data: pd.DataFrame | None) -> pd.DataFrame:
    """v3.9.63 — tempel kolom KATEGORI pada frame pasangan (map per
    Nama Barang dari data mentah — kategori master '21. DBS Kategori' /
    rekap mentah melekat per-BARANG, konstan lintas resto & tanggal;
    `groupby().first()` mengambil nilai non-kosong pertama).

    Pasangan barang tanpa kategori → NaN (blank — klasifikasi bukan
    COM/Packaging; anak tab Tanpa Harga menampilkannya '(Tanpa
    Kategori)'). Bila data tak ber-kolom KATEGORI → seluruh NaN."""
    if pairs is None or pairs.empty:
        return pairs
    out = pairs.copy()
    if data is None or "KATEGORI" not in getattr(data, "columns", []):
        out["KATEGORI"] = pd.Series(
            [float("nan")] * len(out), index=out.index, dtype="float64")
        return out
    _dk = data.dropna(subset=["KATEGORI"])
    _kat = _dk.groupby(_dk["Nama Barang"].astype(str))["KATEGORI"].first()
    out["KATEGORI"] = out["Nama Barang"].astype(str).map(_kat)
    return out


def pasangan_tanpa_harga_global(
        data: pd.DataFrame | None, h: int, harga_map: dict | None,
        konversi_map: dict | None) -> pd.DataFrame:
    """v3.9.63 — frame barang TANPA HARGA GLOBAL (ANAK TAB 'Tanpa Harga'
    tab 🧮 Nominal Deviasi; user: "barang yang tidak ada harga nya
    sesuai kategori yang difilter ... dan itu buat anak tab baru di
    nominal deviasi yang menampilkan secara global").

    Pasangan qty-deviasi ≠ 0 dengan Nominal NaN (barang tak ada di
    41.09 / satuan tak terkonversi) dari data MENTAH — TANPA filter
    kategori tab utama (GLOBAL: semua kategori & resto; filter kategori
    anak tab diterapkan di view saat render). Kolom: [Resto, KATEGORI,
    Nama Barang, Satuan, Qty Deviasi, Harga Tampil, Nominal] urut
    |Qty Deviasi| menurun (warisan urutan hitung_nominal_pairs)."""
    pairs = hitung_nominal_pairs(data, h, harga_map, konversi_map)
    if pairs is None or pairs.empty or "Nominal" not in pairs.columns:
        return pd.DataFrame()
    out = pairs[pairs["Nominal"].isna()].copy()
    if out.empty:
        return out
    out = _attach_kategori_pairs(out, data)
    return out[["Resto", "KATEGORI", "Nama Barang", "Satuan",
                "Qty Deviasi", "Harga Tampil", "Nominal"]] \
        .reset_index(drop=True)


def agregasi_nominal_per_resto(data: pd.DataFrame | None, h: int,
                               harga_map: dict | None,
                               konversi_map: dict | None) -> tuple:
    """→ (frame_per_resto, frame_pasangan).

    frame_per_resto: [Resto, N Barang, Tanpa Harga, Nominal Deviasi,
    COM Deviasi, Biaya Packaging] urut |Nominal Deviasi| MENURUN. Σ
    nominal skipna (pasangan tanpa harga tidak dihitung — transparan).
    v3.9.63 — 'COM Deviasi'/'Biaya Packaging' = Σ nominal pasangan per
    klas kategori (lihat _attach_kategori_pairs / token klas); resto
    tanpa pasangan klas itu → 0.0 (tampil '-' via fmt_rp_cell).
    frame_pasangan = output hitung_nominal_pairs + kolom KATEGORI
    (utk popup rincian + anak tab Tanpa Harga).
    """
    pairs = hitung_nominal_pairs(data, h, harga_map, konversi_map)
    if pairs.empty:
        return pd.DataFrame(columns=["Resto", "N Barang", "Tanpa Harga",
                                     "Nominal Deviasi", "COM Deviasi",
                                     "Biaya Packaging"]), pairs
    # v3.9.63 — kategori per pasangan (klas COM/Packaging + anak tab)
    pairs = _attach_kategori_pairs(pairs, data)
    g = (pairs.groupby("Resto", as_index=False)
         .agg(**{
             "N Barang": ("Nominal", "size"),
             "Tanpa Harga": ("Nominal",
                             lambda s: int(pd.isna(s).sum())),
             "Nominal Deviasi": ("Nominal", "sum")}))
    # v3.9.63 — Σ nominal per klas kategori (user: "diganti dengan
    # nominal deviasi per kategori: kolom COM Deviasi + kolom
    # Packaging") — v3.9.64 word-boundary regex (lihat _KAT_*_RE);
    # Σ skipna (transparan).
    _ku = pairs["KATEGORI"].fillna("").astype(str).str.upper()
    _com = (pairs.loc[_ku.str.contains(_KAT_COM_RE, regex=True,
                                       na=False)]
            .groupby("Resto")["Nominal"].sum())
    _pkg = (pairs.loc[_ku.str.contains(_KAT_PKG_RE, regex=True,
                                       na=False)]
            .groupby("Resto")["Nominal"].sum())
    g["COM Deviasi"] = (g["Resto"].map(_com).astype("float64")
                        .fillna(0.0))
    g["Biaya Packaging"] = (g["Resto"].map(_pkg).astype("float64")
                            .fillna(0.0))
    g["_abs"] = g["Nominal Deviasi"].abs().fillna(0)
    g = g.sort_values("_abs", ascending=False,
                      kind="mergesort").drop(columns=["_abs"])
    g = g.reset_index(drop=True)
    g["N Barang"] = g["N Barang"].astype(int)
    g["Tanpa Harga"] = g["Tanpa Harga"].astype(int)
    return g, pairs


# ---------------------------------------------------------------------------
# PASANGAN NOMINAL BULAN LALU — FILE DEVIASI (v3.9.36)
# ---------------------------------------------------------------------------
_LALU_COLS = ["Resto", "Nama Barang", "Satuan", "Qty Deviasi Lalu",
              "Harga", "Nominal Lalu", "_resto_norm", "_bahan_norm",
              "_minggu"]


def _h_to_week_target(h: int) -> int:
    """v3.9.41 — H analisa → CUT-OFF minggu yang MEMUAT H (mirror
    komparasi_deviasi_view._h_to_week_target v3.9.22; duplikat LOKAL —
    nominal_common tak boleh import komparasi (circular)):
    H 1-7 → 7 (WEEK 1) · H 8-14 → 14 (WEEK 2) · H 15-31 → 25
    (WEEK 3/4 — 26..31 juga 25: minggu yang memuat H 26 = WEEK 4)."""
    h = int(h)
    if h <= 7:
        return 7
    if h <= 14:
        return 14
    return 25


def _pilih_minggu_lalu(weeks_avail: list, h: int | None) -> int | None:
    """v3.9.41 — pilih _h minggu pembanding dari minggu yang tersedia
    di file (bulan terbaru):
    - h None → minggu TERBESAR (perilaku lama — penutupan bulan);
    - h ada → target = _h_to_week_target(h):
        (1) minggu PERSIS target bila ada;
        (2) minggu TERBESAR ≤ target (periode terdekat sebelumnya);
        (3) minggu TERKECIL > target (file hanya punya minggu
            setelahnya — satu-satunya pilihan).
    None bila tak ada minggu sama sekali."""
    if not weeks_avail:
        return None
    if h is None:
        return max(weeks_avail)
    target = _h_to_week_target(h)
    if target in weeks_avail:
        return target
    below = [w for w in weeks_avail if w < target]
    if below:
        return max(below)
    return min(weeks_avail)


def hitung_nominal_lalu_pairs(file_df: pd.DataFrame | None,
                              harga_map: dict | None,
                              konversi_map: dict | None,
                              h: int | None = None,
                              bulan_sel: int | None = None) -> pd.DataFrame:
    """Frame per pasangan dari FILE deviasi (tab ⚖ Komparasi):
    [_resto_norm, _bahan_norm, Resto, Nama Barang, Satuan,
    Qty Deviasi Lalu, Harga, Nominal Lalu, _minggu].

    file_df = output parse_deviasi_file (kolom internal _bulan_num /
    _h / _resto_norm / _bahan_norm milik komparasi). Seleksi:
      - BULAN: bulan_sel (v3.9.45 — param baru utk multi-bulan)
        atau BULAN TERBARU di file bila None (nomor bulan terbesar —
        multi-file History: bulan paling akhir = 'bulan lalu');
      - v3.9.41 MINGGU TER-COCOK dgn H analisa (param h — user:
        "jika week 1 maka ambil data week 1 juga"; lihat
        _pilih_minggu_lalu); h=None → minggu terakhir (perilaku lama).
    Nominal Lalu = SUMBER UTAMA kolom resmi file (v3.9.38) — harga
    snapshot saat laporan dibuat; kolom kosong/NaN/format lama →
    fallback Harga 41.09 (dinormalkan ke SATUAN BARIS FILE via peta
    rasio) × DEV Lalu.
    Tanpa harga / satuan tak terkonversi → None (tampil '-').
    Urut |Nominal Lalu| MENURUN (pasangan tanpa nominal paling
    bawah, urut |qty|). Frame kosong bila file kosong / kolom internal
    tak ada (file format lama).
    """
    empty = pd.DataFrame(columns=_LALU_COLS)
    if file_df is None or getattr(file_df, "empty", True):
        return empty
    need = ("_bulan_num", "_h", "_resto_norm", "_bahan_norm",
            "DEV Lalu", "Resto", "Nama Barang")
    missing = [c for c in need if c not in file_df.columns]
    if missing:
        return empty

    out = pd.DataFrame({
        "Resto": file_df["Resto"].astype(str).values,
        "Nama Barang": file_df["Nama Barang"].astype(str).values,
        "Satuan": (file_df["Satuan"].astype(str).values
                   if "Satuan" in file_df.columns else ""),
        # v3.9.41 — label minggu asli file (utk display minggu terpilih)
        "Minggu": (file_df["Minggu"].astype(str).str.strip().str.upper()
                   .values
                   if "Minggu" in file_df.columns
                   else np.full(len(file_df), "")),
        "_bulan_num": (pd.to_numeric(file_df["_bulan_num"],
                                    errors="coerce").fillna(0)
                       .astype(int).values),
        "_h": pd.to_numeric(file_df["_h"], errors="coerce")
            .fillna(0).values,
        "_resto_norm": file_df["_resto_norm"].astype(str).values,
        "_bahan_norm": file_df["_bahan_norm"].astype(str).values,
        "Qty Deviasi Lalu": (pd.to_numeric(file_df["DEV Lalu"],
                                           errors="coerce")
                             .fillna(0.0).values),
        # v3.9.38 — nominal RESMI milik file (parse_deviasi_file;
        # kolom tak ada di file format lama → NaN → fallback recompute)
        "Nominal Deviasi Lalu": (
            pd.to_numeric(file_df["Nominal Deviasi Lalu"],
                          errors="coerce").values
            if "Nominal Deviasi Lalu" in file_df.columns
            else np.full(len(file_df), np.nan)),
    })
    # (a) bulan TERBARU di file — atau bulan PILIHAN (v3.9.45 param
    # bulan_sel utk hitung_nominal_lalu_multi: satu frame per bulan)
    _bn = pd.to_numeric(out["_bulan_num"], errors="coerce")
    if bulan_sel is None:
        _target_bulan = _bn.max()
    else:
        _target_bulan = int(bulan_sel)
    out = out[_bn == _target_bulan].copy()
    if out.empty:
        return empty
    # (b) v3.9.41 — MINGGU TER-COCOK dgn H analisa (user: "jika week 1
    # maka ambil data week 1 juga"): minggu yang MEMUAT H dipilih;
    # minggu itu tak ada di file → minggu terdekat ≤ target, lalu
    # terkecil > target (lihat _pilih_minggu_lalu). h=None → minggu
    # terakhir (penutupan bulan — perilaku lama, kompatibilitas).
    _weeks_avail = sorted(int(w) for w in out["_h"].dropna().unique()
                          if pd.notna(w))
    _wk_sel = _pilih_minggu_lalu(_weeks_avail, h)
    if _wk_sel is None:
        return empty
    out = out[pd.to_numeric(out["_h"], errors="coerce") == _wk_sel].copy()
    # v3.9.42 — audit 61-a/61-b: WEEK 3 dan WEEK 4 sama-sama dipetakan
    # _h=25 (mirror komparasi v3.9.22). File yang memuat KEDUA label →
    # dedup keep="first" memilih baris file pertama (minggu tercampur
    # ARBITRER per pasangan). Fix: pilih SATU label minggu DETERMINISTIK
    # — label dgn NOMOR minggu TERBESAR (penutupan — semantik 'minggu
    # terakhir' v3.9.36) — lalu filter baris label itu SEBELUM dedup.
    if "Minggu" in out.columns and not out.empty:
        _labs = [str(x).strip().upper()
                 for x in out["Minggu"].dropna().unique()
                 if str(x).strip().upper() not in ("", "NAN", "NONE")]
        if len(_labs) > 1:
            def _lab_num(lab):
                m = re.search(r"(\d+)", lab)
                return int(m.group(1)) if m else 0
            _lab_sel = max(_labs, key=_lab_num)
            out = out[out["Minggu"].astype(str).str.strip()
                      .str.upper() == _lab_sel].copy()
    # label minggu terpilih utk display (label asli file; fallback
    # label cut-off bila kolom Minggu tak terbawa)
    _wk_fallback = {7: "WEEK 1", 14: "WEEK 2", 25: "WEEK 3/4"}.get(
        _wk_sel, f"WEEK cut-off H{_wk_sel}")
    _wk_label = _wk_fallback
    if "Minggu" in out.columns and len(out):
        _cand = str(out["Minggu"].iloc[0]).strip().upper()
        if _cand and _cand not in ("NAN", "NONE"):
            _wk_label = _cand
    out = out.drop_duplicates(subset=["_resto_norm", "_bahan_norm"],
                              keep="first")
    out = out.reset_index(drop=True)
    out["_minggu"] = _wk_label
    out = out.drop(columns=["Minggu"], errors="ignore")

    # (c) NOMINAL LALU — SUMBER UTAMA kolom resmi file (v3.9.38):
    # nilai file dipakai APA ADANYA (harga snapshot saat laporan dibuat —
    # angka resmi bulan lalu); kolom kosong/NaN / file format lama →
    # fallback hitung ulang harga 41.09 sekarang × DEV Lalu (lookup per
    # baris — pola komparasi v3.9.34a: TANPA cache persisten lintas-file).
    harga_vals = []
    nominal_vals = []
    for _, r in out.iterrows():
        b = str(r["Nama Barang"]).strip()
        sat_file = norm_sat(r["Satuan"])
        # v3.9.38 — nilai resmi file ADA → pakai langsung (harga lookup
        # tetap ditarik utk kolom Harga display; None bila tak ada).
        _fnom = r.get("Nominal Deviasi Lalu")
        _has_file_nom = _fnom is not None and not pd.isna(_fnom)
        if _has_file_nom:
            nominal_vals.append(float(_fnom))
            _hg, _lbl, _b = lookup_harga_pair(
                harga_map, konversi_map, b, sat_file)
            harga_vals.append(_hg)
            continue
        # v3.9.38 — DEV Lalu PERSIS 0 → tak perlu cari harga (mirror
        # hitung_nominal_pairs): Nominal Lalu 0.0 (bukan None → tak
        # dihitung 'tanpa pasangan/harga' di footer popup).
        if float(r["Qty Deviasi Lalu"]) == 0.0:
            harga_vals.append(None)
            nominal_vals.append(0.0)
            continue
        harga, _label, _bintang = lookup_harga_pair(
            harga_map, konversi_map, b, sat_file)
        if harga is not None:
            nominal_vals.append(harga * float(r["Qty Deviasi Lalu"]))
        else:
            nominal_vals.append(None)
        harga_vals.append(harga)
    out["Harga"] = pd.Series(harga_vals, dtype="float64")
    out["Nominal Lalu"] = pd.Series(nominal_vals, dtype="float64")

    out["_absnom"] = out["Nominal Lalu"].abs().fillna(0)
    out["_absqty"] = out["Qty Deviasi Lalu"].abs()
    out = (out.sort_values(["_absnom", "_absqty"],
                           ascending=[False, False],
                           kind="mergesort")
           .drop(columns=["_absnom", "_absqty"]))
    out = out.reset_index(drop=True)
    return out[_LALU_COLS]


# ---------------------------------------------------------------------------
# v3.9.45 — MULTI-BULAN: satu frame per bulan file deviasi (user: "tab
# nominal deviasi support buat multiple file deviasi buat compare dengan
# beberapa bulan lalu"). File deviasi dimuat MULTI-FILE di tab ⚖ Komparasi
# (path dipisah ';' — v3.9.13) → file_df memuat SEMUA bulan; fungsi ini
# memecahnya jadi [(label, pairs)] urut bulan TERBARU dulu.
# ---------------------------------------------------------------------------
_BULAN_NAMA = {1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
               5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
               9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER",
               12: "DESEMBER"}


def _bulan_label_multi(file_df: pd.DataFrame, bulan_num: int) -> str:
    """Label bulan kanonik utk satu nomor bulan: nilai kolom BULAN file
    paling SERING muncul di bulan itu (file user memakai kode periode
    '201.OKT 26' — dipakai APA ADANYA supaya user mengenalinya; dua
    file beda periode sama-sama bulan 10 → yang dominan menang), else
    nama bulan Indonesia, else 'BULAN n'."""
    try:
        sub = file_df[pd.to_numeric(
            file_df["_bulan_num"], errors="coerce") == int(bulan_num)]
        if "BULAN" in sub.columns and not sub.empty:
            vals = (sub["BULAN"].astype(str).str.strip().str.upper()
                    .replace("", pd.NA).dropna())
            vals = vals[~vals.str.lower().isin(["nan", "none"])]
            if not vals.empty:
                return str(vals.mode().iloc[0])
    except (KeyError, ValueError, TypeError):
        pass
    return _BULAN_NAMA.get(int(bulan_num), f"BULAN {bulan_num}")


def hitung_nominal_lalu_multi(
        file_df: pd.DataFrame | None,
        harga_map: dict | None,
        konversi_map: dict | None,
        h: int | None = None,
        max_months: int = 6) -> list:
    """v3.9.45 — list [(label_bulan, pairs_df)] dari SEMUA bulan file
    deviasi, urut bulan TERBARU dulu (index 0 = 'bulan lalu' utama =
    perilaku hitung_nominal_lalu_pairs lama; index berikut = bulan
    lebih lama lagi).

    Setiap frame = hitung_nominal_lalu_pairs(bulan_sel=n) — minggu
    TER-COCOK H diterapkan PER BULAN (bulan lalu punya minggu sendiri).
    Bulan dengan 0 baris minggu-ter-cocok di-skip. max_months (default
    6) menjaga lebar tabel wajar — user mengontrol sendiri jumlah
    bulan lewat berapa file yang dimuat di ⚖ Komparasi."""
    if file_df is None or getattr(file_df, "empty", True):
        return []
    if "_bulan_num" not in file_df.columns:
        return []
    try:
        nums = sorted(
            {int(n) for n in pd.to_numeric(
                file_df["_bulan_num"], errors="coerce").dropna().unique()
             if pd.notna(n)})
    except (TypeError, ValueError):
        return []
    frames = []
    for n in reversed(nums):          # terbaru dulu
        if len(frames) >= max(1, int(max_months)):
            break
        dfm = hitung_nominal_lalu_pairs(
            file_df, harga_map, konversi_map, h=h, bulan_sel=n)
        if dfm is None or dfm.empty:
            continue
        frames.append((_bulan_label_multi(file_df, n), dfm))
    return frames


# ---------------------------------------------------------------------------
# v3.9.53 — DEVIASI BULAN LALU (KUANTITI) utk tab 📦 Deviasi GR / 🧩 PCS
# ---------------------------------------------------------------------------
def dev_lalu_qty_map(file_df: pd.DataFrame | None,
                     h: int | None = None,
                     bulan_sel: int | None = None):
    """v3.9.53 — peta {(resto_norm, bahan_norm): qty_dev_lalu} NILAI ASLI
    (bertanda — plus surplus / minus kekurangan) dari FILE deviasi resmi
    (parse_deviasi_file tab ⚖ Komparasi; user: "Deviasi bulan lalu yang
    ditampilkan di tab deviasi gr dan pcs pakai nilai asli jangan pakai
    nilai absolute yang ditampilkan. Absolute untuk perhitungan saja" +
    "sama seperti di tab laporan deviasi secara kuantiti").

    Seleksi IDENTIK hitung_nominal_lalu_pairs (satu sumber kebenaran —
    angka tab 📋 Laporan Deviasi kolom 'DEV Lalu' & tab ini PERSIS SAMA):
      - BULAN: bulan_sel atau BULAN TERBARU di file;
      - MINGGU TER-COCOK H (user: "Week ... menyesuaikan kolom H di tab
        deviasi GR dan PCS untuk Deviasi bulan lalu" — mirror v3.9.41
        'jika week 1 maka ambil data week 1 juga'): minggu yang MEMUAT H;
        tidak ada → terbesar ≤ target, lalu terkecil > target; h=None →
        minggu terakhir (penutupan bulan);
      - dedup (resto, bahan) keep="first" + label minggu deterministik
        (WEEK 3 & WEEK 4 sama-sama _h=25 — nomor minggu terbesar menang).

    Return (map, label) — label = "WEEK n · <bulan>" (dipakai status/
    legend supaya asal angka JELIHAT; None bila file kosong/tak valid).
    Tanpa harga/loop iterrows (LEAN — hanya kuantiti)."""
    empty = ({}, None)
    if file_df is None or getattr(file_df, "empty", True):
        return empty
    need = ("_bulan_num", "_h", "_resto_norm", "_bahan_norm", "DEV Lalu")
    if any(c not in file_df.columns for c in need):
        return empty
    out = pd.DataFrame({
        "_bulan_num": (pd.to_numeric(file_df["_bulan_num"],
                                    errors="coerce").fillna(0)
                       .astype(int).values),
        "_h": pd.to_numeric(file_df["_h"], errors="coerce").values,
        "_resto_norm": file_df["_resto_norm"].astype(str).values,
        "_bahan_norm": file_df["_bahan_norm"].astype(str).values,
        "qty": (pd.to_numeric(file_df["DEV Lalu"], errors="coerce")
                .fillna(0.0).values),
        "Minggu": (file_df["Minggu"].astype(str).values
                   if "Minggu" in file_df.columns
                   else np.full(len(file_df), "")),
    })
    # (a) bulan TERBARU (atau bulan PILIHAN — parity hitung_nominal_lalu_
    # pairs; bulan paling akhir di file multi-bulan = 'bulan lalu')
    _bn = pd.to_numeric(out["_bulan_num"], errors="coerce")
    _target_bulan = (_bn.max() if bulan_sel is None else int(bulan_sel))
    out = out[_bn == _target_bulan].copy()
    if out.empty:
        return empty
    # (b) minggu TER-COCOK H (mirror _pilih_minggu_lalu v3.9.41)
    _weeks_avail = sorted(int(w) for w in out["_h"].dropna().unique()
                          if pd.notna(w))
    _wk_sel = _pilih_minggu_lalu(_weeks_avail, h)
    if _wk_sel is None:
        return empty
    out = out[pd.to_numeric(out["_h"], errors="coerce") == _wk_sel].copy()
    # (c) label minggu deterministik (WEEK 3/4 → _h=25 sama — mirror
    # audit 61-a/61-b: nomor minggu TERBESAR yang dipilih)
    _wk_fallback = {7: "WEEK 1", 14: "WEEK 2", 25: "WEEK 3/4"}.get(
        _wk_sel, f"WEEK cut-off H{_wk_sel}")
    _wk_label = _wk_fallback
    if not out.empty:
        _labs = [str(x).strip().upper()
                 for x in out["Minggu"].dropna().unique()
                 if str(x).strip().upper() not in ("", "NAN", "NONE")]
        if len(_labs) > 1:
            def _lab_num(lab):
                m = re.search(r"(\d+)", lab)
                return int(m.group(1)) if m else 0
            out = out[out["Minggu"].astype(str).str.strip()
                      .str.upper() == max(_labs, key=_lab_num)].copy()
        if not out.empty:
            _cand = str(out["Minggu"].iloc[0]).strip().upper()
            if _cand and _cand not in ("NAN", "NONE"):
                _wk_label = _cand
    out = out.drop_duplicates(subset=["_resto_norm", "_bahan_norm"],
                              keep="first")
    qty_map = {
        (str(r["_resto_norm"]), str(r["_bahan_norm"])): float(r["qty"])
        for _, r in out.iterrows()}
    label = f"{_wk_label} · {_bulan_label_multi(file_df, _target_bulan)}"
    return (qty_map, label)
