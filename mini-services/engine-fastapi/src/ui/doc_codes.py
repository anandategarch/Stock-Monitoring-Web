"""
doc_codes.py — Parsing & analisa kode dokumen IN (SHARED, v3.9.24).

Dipakai bersama oleh in_selisih_view (popup Rincian IN + Catatan Audit)
dan deviasi_view (CEK "RI Balancing" kolom utama tab Deviasi GR/PCS).
Sebelumnya helper ini hidup di in_selisih_view.py; diangkat ke modul
sendiri supaya logika bisnis RI Balancing TIDAK diduplikasi (audit
34/37: duplikasi rumus = sumber bug senyap). in_selisih_view tetap
me-re-export nama lama (_doc_code_str/_doc_period/_doc_month/
_ri_balancing) — kompatibel test §29/§30 yang mengimpor dari sana.

Struktur kode dokumen: PREFIKS.TAHUN.BULAN.NOMOR
  "PO.2026.08.00571" / "RI.2026.10.10354" / "IT.2026.09.00123"
(segmen 2 = tahun, segmen 3 = bulan — bulan 1-2 digit, dibandingkan
NUMERIK; "8" == "08").

v3.9.24 (user: "jika saat ini bulan oktober maka 1 periode nya mulai
dari 26 september - 25 oktober nah untuk cek RI balancing berarti
dengan NO. PO yang bukan bulan september dan oktober … RI.2026.10.10354
dengan PO PO.2026.08.00571") — DEFINISI RI BALANCING DIPERBAIKI dari
"bulan RI ≠ bulan PO" (v3.9.19-23) menjadi PERIODE BISNIS 26→25:
satu periode = tgl 26 bulan lalu s/d tgl 25 bulan ini, mencakup DUA
bulan kalender. Dokumen RI tanggal 1-25 → bulan periodenya {bulan-1,
bulan}; tanggal 26-31 → {bulan, bulan+1} (wrap tahun Des↔Jan).
Balancing = Nomor PO dari periode DI LUAR dua bulan itu (contoh user:
RI 1 Okt ↔ PO Agustus → balancing; RI 1 Okt ↔ PO September → BUKAN
balancing — PO September masih satu periode dgn RI-nya). Tanpa tanggal
dokumen (NaN/invalid) → fallback aturan lama bulan≠bulan (konservatif).

v3.9.23 (user: "kerjakan poin 6 dan kerjakan semua poin B"):
- CEK "RI Balancing" diangkat ke kolom CEK utama Deviasi GR/PCS
  (dulu hanya di popup Rincian IN);
- Catatan Audit tab Rekap Selisih IN diperkaya catatan otomatis
  (RI Balancing / Nomor Dobel / Selisih IN / BM kosong).
"""
import re

import pandas as pd

# v3.9.19 — struktur kode dokumen: PREFIKS.TAHUN.BULAN.NOMOR
# (mis. "PO.2026.08.00571" / "RI.2026.10.10354" — 2026 tahun, 08/10
# bulan). FIX 35-c1: bulan boleh 1-2 digit ("RI.2026.8.10354" non-
# zero-pad dulu gagal pola → CEK senyap kosong) + validasi 1..12.
_DOC_CODE_RE = re.compile(r"^[A-Za-z]+\.(\d{4})\.(\d{1,2})\.")


def _doc_code_str(code) -> str:
    """Kode dokumen → teks aman (None/pd.NA/NaN → "")."""
    if code is None:
        return ""
    try:
        if pd.isna(code):
            return ""
    except (TypeError, ValueError):
        pass
    return str(code).strip()


def _doc_period(code):
    """FIX 35-c1 — (tahun, bulan) dari kode dokumen
    "PO.2026.08.00571" → (2026, 8); None bila pola tidak cocok /
    bulan di luar 1..12 ("RI.2026.13.1" → None). Bulan 1-2 digit
    dibandingkan NUMERIK (8 == 08)."""
    m = _DOC_CODE_RE.match(_doc_code_str(code))
    if not m:
        return None
    try:
        year = int(m.group(1))
        month = int(m.group(2))
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    return (year, month)


def _doc_month(code) -> "int | None":
    """Bulan dari kode dokumen PO.2026.08.00571 → 8; None bila pola
    tidak cocok / nilai kosong (FIX 35-c1: bulan 1-2 digit + sanity
    1..12 via _doc_period)."""
    period = _doc_period(code)
    return period[1] if period is not None else None


def _shift_period(y: int, m: int, delta: int):
    """v3.9.24 — geser (tahun, bulan) sebanyak delta bulan, year-aware
    (Des + 1 → Jan tahun depan; Jan − 1 → Des tahun lalu)."""
    idx = (y * 12) + (m - 1) + delta
    return (idx // 12, idx % 12 + 1)


def _ri_period_months(p_ri, day: int) -> set:
    """v3.9.24 (klarifikasi user) — dua (tahun, bulan) yang dicakup
    PERIODE BISNIS dokumen RI: satu periode = tgl 26 bulan lalu s/d
    tgl 25 bulan RI (cut-off 25/26). RI bertanggal 1-25 → periodenya
    {bulan-1, bulan} (mis. RI Okt tgl 1 → periode 26 Sep–25 Okt →
    {Sep, Okt}); RI bertanggal 26-31 → {bulan, bulan+1} (RI 26 Sep
    & RI 1 Okt satu periode). Wrap tahun Des↔Jan ditangani."""
    y, m = p_ri
    if day <= 25:
        return {(y, m), _shift_period(y, m, -1)}
    return {(y, m), _shift_period(y, m, +1)}


def _day_of(tanggal):
    """v3.9.24 — tanggal dokumen (kolom Tanggal = HARI bulan; bulan-lalu
    NEGATIF, mis. -28 = tgl 28 bulan lalu) → hari absolut 1..31;
    None bila kosong/NaN/bukan angka/di luar 1..31 (→ fallback aturan
    lama). Float '20.0' / teks '24' diterima."""
    if tanggal is None:
        return None
    try:
        if pd.isna(tanggal):
            return None
    except (TypeError, ValueError):
        pass
    try:
        day = abs(int(float(tanggal)))
    except (TypeError, ValueError):
        return None
    return day if 1 <= day <= 31 else None


def _ri_balancing(nomor, nomor_po, tanggal=None) -> str:
    """v3.9.24 (klarifikasi user) — "RI Balancing" bila PERIODE Nomor PO
    DI LUAR dua bulan periode bisnis RI-nya (26 bulan lalu – 25 bulan
    RI). Contoh user: RI.2026.10.10354 transaksi 1 Okt (periodennya
    26 Sep–25 Okt) + PO.2026.08.00571 (Agustus ∉ {Sep, Okt}) →
    "RI Balancing"; PO September / Oktober → "" (satu periode dgn
    RI-nya, BUKAN balancing — v3.9.19-23 salah flag kasus ini).
    tanggal = kolom Tanggal baris dokumen (hari bulan; bulan-lalu
    negatif); menentukan sisi batas 25/26 periode.
    Tanpa tanggal valid (NaN/invalid/None — panggilan test lama §29/§30
    2-arg) → FALLBACK aturan lama v3.9.19-23: periode RI ≠ periode PO
    (bulan ≠ bulan, tahun-aware FIX 35-c1) → flag (konservatif: tanggal
    tak terverifikasi tetap dianggap mencurigakan).
    Tetap hanya dokumen RI (prefiks "RI." — PI = invoice pembelian,
    bukan balancing); bulan 1-2 digit numerik ("8" == "08")."""
    n = _doc_code_str(nomor)
    if not n.upper().startswith("RI."):
        return ""
    p_ri = _doc_period(n)
    p_po = _doc_period(nomor_po)
    if p_ri is None or p_po is None:
        return ""
    day = _day_of(tanggal)
    if day is None:
        # fallback aturan lama: bulan (tahun-aware) beda → balancing
        return "RI Balancing" if p_ri != p_po else ""
    return "RI Balancing" if p_po not in _ri_period_months(p_ri, day) \
        else ""


def ri_balancing_docs(in_detail: pd.DataFrame | None):
    """v3.9.23 — daftar dokumen IN "RI Balancing" per pasangan
    (Nama Barang, NAMA RESTO) dari frame detail IN per-dokumen.
    v3.9.24: kolom Tanggal baris ikut dipakai (periode bisnis 26→25 —
    lihat _ri_balancing); frame tanpa kolom Tanggal → fallback aturan
    lama bulan≠bulan.

    Return dict {(barang, resto): [nomor, ...]} — nomor dokumen RI
    ber-periode PO di luar periode bisnisnya (urut, unik). Frame in_detail
    berasal dari query_in: kolom NAMA RESTO · Nama Barang · Tanggal ·
    Value · Nomor · Nomor PO · SOURCE IN · JENIS (per dokumen × item —
    pemetaan Nomor↔Nomor PO BERSIH, tidak ter-campur seperti kolom
    gabungan di frame final). Dipakai:
    - deviasi_view → CEK "RI Balancing" kolom utama (pasangan
      ber-dokumen balancing TERFLAG);
    - in_selisih_view → Catatan Audit (nomor dokumen dituliskan).
    """
    out: dict = {}
    if in_detail is None or getattr(in_detail, "empty", True):
        return out
    cols = set(getattr(in_detail, "columns", []))
    if not {"Nomor", "Nomor PO", "Nama Barang", "NAMA RESTO"} <= cols:
        return out
    has_tgl = "Tanggal" in cols
    tgl_iter = (in_detail["Tanggal"] if has_tgl
                else [None] * len(in_detail))
    for nomor, nomor_po, b, r, t in zip(in_detail["Nomor"],
                                       in_detail["Nomor PO"],
                                       in_detail["Nama Barang"],
                                       in_detail["NAMA RESTO"],
                                       tgl_iter):
        if _ri_balancing(nomor, nomor_po, t) == "":
            continue
        key = (str(b), str(r))
        n = _doc_code_str(nomor)
        if n and n not in out.setdefault(key, []):
            out[key].append(n)
    return out


def duplicated_doc_numbers(in_detail: pd.DataFrame | None) -> dict:
    """v3.9.23 (poin B — catatan audit) — deteksi NOMOR DOBEL pada
    detail IN per dokumen: nomor dokumen sama muncul >1 baris untuk
    (Resto, Barang) PASANGAN YANG SAMA = input ganda (double-entry /
    sheet kembar — gejala RISK R2 audit 37-a: fn_9901 membaca semua
    sheet → IN terhitung 2×).

    Satu dokumen yang sah memuat >1 item berbeda TIDAK terflag
    (grouping per pasangan barang); begitu pula dokumen yang berisi
    item yang sama di resto lain. Return dict
    {(barang, resto): {nomor: jumlah_baris}} hanya utk pasangan yang
    punya nomor dobel.
    """
    out: dict = {}
    if in_detail is None or getattr(in_detail, "empty", True):
        return out
    cols = {"Nomor", "Nama Barang", "NAMA RESTO"}
    if not cols <= set(getattr(in_detail, "columns", [])):
        return out
    d = in_detail[in_detail["Nomor"].notna()].copy()
    if d.empty:
        return out
    d["_nomor"] = d["Nomor"].map(_doc_code_str)
    d = d[d["_nomor"].ne("")]
    if d.empty:
        return out
    grp = d.groupby(["Nama Barang", "NAMA RESTO", "_nomor"],
                    dropna=False).size().reset_index(name="_n")
    dup = grp[grp["_n"] > 1]
    for b, r, nomor, n in zip(dup["Nama Barang"], dup["NAMA RESTO"],
                              dup["_nomor"], dup["_n"]):
        out.setdefault((str(b), str(r)), {})[str(nomor)] = int(n)
    return out
