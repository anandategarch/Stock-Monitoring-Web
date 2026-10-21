"""
mapper.py — Pemetaan DataFrame pipeline Stock-Monitoring v3.9.71 → EngineResult
(kontrak v1, docs/ENGINE-CONTRACT.md). HANYA pemetaan — logika hitung 100% milik
pipeline vendored `src/` (0-rewrite, FR-10); label CEK/COM/catatan audit dipindah
VERBATIM dari view desktop (sumber baris dicantumkan per fungsi).

Keputusan terdokumentasi (kontrak v1 + PRD):
- INV-1: append1 merepresentasikan metric yang absen pada hari teramati sebagai 0
  (parity angka desktop — PRD risiko R-4: engine tetap jujur pada angka desktop;
  pembedaan NA-vs-0 adalah urusan tampilan pivot baru). Baris EngineRow hanya ada
  untuk (pasangan, hari) yang TERAMATI; metric null hanya bila memang tak terdefinisi.
- INV-2: semua qty bertanda (deviasi/selisih minus = kekurangan).
- INV-3: konversiOk=false atau hargaEfektif=null ⇒ nominal=null (per baris hari:
  nominal = hargaEfektif × deviasi hari itu, null bila deviasi 0 — kontrak §4).
- cek = SEMUA kondisi terpicu (array label kanonik) — presentasi prioritas ala
  desktop (np.select Promix→RI Bal→Kosong→Tanggal→Manual→Drastis→ACR) tetap
  terdokumentasi di sini; UI web menampilkan badge per label dan menghitung ulang
  "ACR to BOM" live saat ambang berubah (FR-30).
- Catatan audit per baris: satu kode B1..B4 per (pasangan, hari), prioritas urutan
  append desktop: B1 → B2 → B4 → B3 (B4 DIDAHULUKAN B3 — in_selisih_view).
- selisihIn memakai varian audit BULAN INI (default desktop v3.9.27 — mirror
  LAPORAN_DEVIASI tgl 1..31); SKOR RESTO = item selisih + tanggal terdampak
  (v3.9.55 F3, dihitung SEBELUM filter "hanya selisih ≠ 0").
- §82b: summary.warningCount/errorCount = jumlah baris log WARNING/ERROR
  (termasuk baris observasi [ENGINE] yang di-append untuk DQ turunan, supaya
  setiap DQ WARNING/ERROR memiliki ≥1 baris log selevel — kontrak §3.4).
"""
import math
import os
import re
from datetime import datetime, timezone

import pandas as pd

from ports import doc_codes
from ports import nominal_common
from src.pipeline.helpers import (_list_excel_files, preflight_folders,
                                 resto_from_cabang_po)
from src.pipeline.fn_audit import extract_po_pending
from src.pipeline.konversi_satuan import lookup_rasio

# ---------------------------------------------------------------------------
# Konstanta kontrak
# ---------------------------------------------------------------------------

METRIC_BY_JENIS = {
    "SALDO AWAL": "qtySaldoAwal",
    "1.SO": "qtySO",
    "2.SALDO AKHIR": "qtySaldoAkhir",
    "3.DEVIASI": "qtyDeviasi",
    "4.IN": "qtyIN",
    "5.BARANG MASUK": "qtyBarangMasuk",
    "7.Selisih IN": "qtySelisihIN",
    "8.BARANG KELUAR": "qtyBarangKeluar",
    "9.ACR": "qtyACR",
}

# Urutan array `cek` (identik CEK_CANON generator demo — kontrak).
CEK_CANON = [
    "RI Balancing", "Beda Tanggal", "Promix 04", "Kosong/Non Aktif",
    "Hitung Manual", "Turun Drastis", "ACR to BOM", "PO Menunggu",
    "Selisih IN",
]

KATEGORI_TANPA = "(Tanpa Kategori)"  # kontrak §3.7 — jujur, bukan error
SELISIH_IN_LABEL_MIN = 8.0  # |Σ 7.Selisih IN pasangan| ≥ 8 → label (kontrak §4)
LALU_CLOSING_KEY = -1  # kunci rekap penutupan bulan lalu (fix 48-b)

ENGINE_NAME = "SM-FastAPI-Engine"
ENGINE_VERSION = "1.0.0"
DEFINITION_VERSION = "3.9.71-noSI"
CONTRACT_VERSION = "1"
PARITY_NOTE = (
    "Engine PRODUKSI: pipeline asli Stock-Monitoring v3.9.71 (f22bca6) dibungkus "
    "apa adanya (0-rewrite, FR-10) — angka = angka desktop. Label CEK, COM, "
    "catatan audit B1–B4 & SKOR RESTO dipindah verbatim dari view desktop. "
    "Paritas golden-file penuh atas bundle real menunggu bundle export asli "
    "(PRD §11.2); pada fixture mock, angka ≡ test_mock.py desktop (AC-B)."
)


# ---------------------------------------------------------------------------
# Util kecil (port verbatim)
# ---------------------------------------------------------------------------

def _tgl_key(t):
    """Port verbatim in_selisih_view._tgl_key — kunci tanggal numerik catatan
    audit (NaN → None; int supaya 25.0 == 25 cocok dgn key dict)."""
    try:
        if pd.isna(t):
            return None
    except (TypeError, ValueError):
        return None
    try:
        return int(float(t))
    except (TypeError, ValueError):
        return None


def _num(v):
    """Nilai → float murni (None bila NaN/None); pembulatan 6dp anti-noise.
    -0.0 dinolkan supaya JSON stabil (FR-12 determinisme byte-per-byte data)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        return None
    f = float(v)
    if not math.isfinite(f):
        return None
    f = round(f, 6)
    return 0.0 if f == 0 else f


def _norm_text(v) -> str:
    """Normalisasi kunci: strip + upper + rapat spasi (join pasangan audit/CEK)."""
    return re.sub(r"\s+", " ", str(v).strip().upper())


def _norm_resto(v) -> str:
    """Kode resto: mirror nominal_common._norm_resto_lalu ('B.1001.MLGPAR' →
    'MLGPAR'; tanpa titik → apa adanya) + rapat spasi."""
    s = _norm_text(v)
    if "." in s:
        s = s.split(".")[-1].strip()
    return s


def _kategori_or_tanpa(kat) -> str:
    """Kategori pasangan — blank (kategori_blank_mask desktop, termasuk token
    '-'/'—') → '(Tanpa Kategori)' (kontrak §3.7)."""
    if kat is None:
        return KATEGORI_TANPA
    try:
        if pd.isna(kat):
            return KATEGORI_TANPA
    except (TypeError, ValueError):
        pass
    s = str(kat).strip()
    if s == "" or s in ("-", "—", "nan", "None", "NONE", "NAN"):
        return KATEGORI_TANPA
    return s


# ---------------------------------------------------------------------------
# Log pipeline → baris log terstruktur + jejak skip/file (§82b)
# ---------------------------------------------------------------------------

_SKIP_RE = re.compile(r"\[WARNING\] Skip file (.+?): (.+)")
_COMBINE_RE = re.compile(
    r"\[INFO\] combine_folder (.+?): (\d+) baris dari (\d+) file \((.+)\)")
_COMBINE_WARN_RE = re.compile(r"\[WARNING\] combine_folder (.+?): (\d+) file menyumbang")


def parse_pipeline_log(text: str, started_at_iso: str) -> dict:
    """Teks stdout pipeline → {logs[], skipped[(file, reason)],
    per_file_rows{folder_abs: {basename: n}}, multiwarn_folders{folder_abs}}.

    Level: 'WARNING'/'[PERINGATAN]' → WARNING; 'ERROR' → ERROR; else INFO
    (pola §82b desktop: SEMUA literal WARNING pipeline terhitung)."""
    logs = []
    skipped = []
    per_file_rows = {}
    multiwarn = set()
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        msg = line.strip()
        upper = msg.upper()
        if "WARNING" in upper or "[PERINGATAN]" in upper:
            level = "WARNING"
        elif "ERROR" in upper:
            level = "ERROR"
        else:
            level = "INFO"
        logs.append({"ts": started_at_iso, "level": level, "message": msg})

        m = _SKIP_RE.search(msg)
        if m:
            skipped.append((m.group(1).strip(), m.group(2).strip()))
        m = _COMBINE_RE.search(msg)
        if m:
            folder_abs = m.group(1).strip()
            rincian = m.group(4)
            per_file_rows.setdefault(folder_abs, {})
            for part in rincian.split(","):
                if "=" in part:
                    name, _, n = part.rpartition("=")
                    per_file_rows[folder_abs][name.strip()] = int(n)
        m = _COMBINE_WARN_RE.search(msg)
        if m:
            multiwarn.add(m.group(1).strip())
    return {"logs": logs, "skipped": skipped,
            "per_file_rows": per_file_rows, "multiwarn": multiwarn}


def _classify_warning(msg: str) -> str:
    """Kode kelas DQ untuk baris WARNING pipeline (Task 31-c; v3.9.67/71
    literal WARNING: skip file, fallback 9901, NA-fill VALUE/Tanggal, schema)."""
    low = msg.lower()
    if "skip file" in low:
        return "SKIP_FILE"
    if "menyumbang baris" in low:
        return "DUPLIKAT_BARIS"
    if "fn_9901" in low and "fallback" in low:
        return "FALLBACK_BIND_9901"
    if "tanggal" in low and ("hilang" in low or "na" in low or "missing" in low):
        return "TANGGAL_MISSING"
    if ("nilai" in low or "value" in low or "kuantitas" in low or "qty" in low) \
            and ("hilang" in low or "na" in low or "missing" in low or "renamed" in low):
        return "VALUE_MISSING"
    return "SCHEMA_WARNING"


# ---------------------------------------------------------------------------
# Pasangan (pair) dari append1 long frame
# ---------------------------------------------------------------------------

class Pair:
    """Agregat per (Nama Barang, NAMA RESTO) — metric per hari + meta pasangan."""

    __slots__ = ("barang", "resto", "days", "satuan", "kategori", "aktif",
                 "source_data", "sa_t1", "sistem_t1")

    def __init__(self, barang, resto):
        self.barang = barang
        self.resto = resto
        self.days = {}          # day → {metricKey: nilai}
        self.satuan = None
        self.kategori = None
        self.aktif = None
        self.source_data = {}   # day → SOURCE DATA baris 1.SO (LANGKAH 9 append1)
        self.sa_t1 = None       # SALDO AWAL @ Tanggal 1 (base COM — pivot_view)
        self.sistem_t1 = None    # 2.SALDO AKHIR @ t=1 (fallback sistem, 48-b)

    def get(self, day, metric):
        d = self.days.get(day)
        if d is None:
            return 0.0
        v = d.get(metric)
        return 0.0 if v is None else v

    def has(self, day, metric):
        d = self.days.get(day)
        return d is not None and metric in d


def build_pairs(append1_df: pd.DataFrame) -> dict:
    """append1 long → {pair_key(norm_barang, norm_resto): Pair}.

    Hanya Tanggal >= 1 yang masuk EngineRow (kontrak day 1..31); hari negatif
    (rekap/IN bulan lalu) tetap dipakai lewat kunci LALU_CLOSING_KEY = -1 untuk
    SO(H-1) saat H=1 (fix 48-b: pemetaan 0 → −1)."""
    pairs: dict = {}
    if append1_df is None or append1_df.empty:
        return pairs
    tnum = pd.to_numeric(append1_df["Tanggal"], errors="coerce")
    jenis = append1_df["JENIS"].astype(str)
    nilai = pd.to_numeric(append1_df["NILAI"], errors="coerce")

    for i in range(len(append1_df)):
        t = tnum.iat[i]
        if pd.isna(t):
            continue
        day = int(t)
        if day < 0 and day != LALU_CLOSING_KEY:
            continue  # -2..-31 tidak dipakai mapper (tidak ada konsumennya)
        j = jenis.iat[i]
        metric = METRIC_BY_JENIS.get(j)
        b_raw = append1_df["Nama Barang"].iat[i]
        r_raw = append1_df["NAMA RESTO"].iat[i]
        key = (_norm_text(b_raw), _norm_text(r_raw))
        p = pairs.get(key)
        if p is None:
            p = Pair(str(b_raw).strip(), str(r_raw).strip())
            pairs[key] = p

        # meta pasangan (konstan per pasangan — first non-null menang)
        if p.satuan is None and "SATUAN" in append1_df.columns:
            s = append1_df["SATUAN"].iat[i]
            if s is not None and not (isinstance(s, float) and pd.isna(s)) \
                    and str(s).strip() not in ("", "nan", "None"):
                p.satuan = str(s).strip()
        if p.kategori is None and "KATEGORI" in append1_df.columns:
            k = append1_df["KATEGORI"].iat[i]
            try:
                if k is not None and not pd.isna(k) and str(k).strip() not in ("", "nan", "None"):
                    p.kategori = str(k).strip()
            except (TypeError, ValueError):
                pass
        if p.aktif is None and "AKTIF/NON" in append1_df.columns:
            a = append1_df["AKTIF/NON"].iat[i]
            try:
                if a is not None and not pd.isna(a) and str(a).strip() != "":
                    p.aktif = str(a).strip().upper()
            except (TypeError, ValueError):
                pass

        # SOURCE DATA per (pasangan, tanggal) pada baris 1.SO (v3.9.21)
        if j == "1.SO" and "SOURCE DATA" in append1_df.columns:
            sd = append1_df["SOURCE DATA"].iat[i]
            try:
                if sd is not None and not pd.isna(sd) and str(sd).strip() != "":
                    p.source_data[day] = str(sd).strip()
            except (TypeError, ValueError):
                pass

        if metric is not None:
            v = nilai.iat[i]
            d = p.days.setdefault(day, {})
            if metric not in d:  # satu nilai per (pair, day, metric)
                d[metric] = 0.0 if pd.isna(v) else float(v)
            if j == "SALDO AWAL" and day == 1:
                p.sa_t1 = d[metric]
            if j == "2.SALDO AKHIR" and day == 1:
                p.sistem_t1 = d[metric]
    return pairs


def compute_com(pair: Pair) -> dict:
    """6.PEMAKAIAN (COM) per tanggal — PORT VERBATIM rumus pivot_view._compute_com
    (v3.9.5): COM(t) = base + IN(t) − BK(t) − SO(t); base t=1 = SALDO AWAL
    pasangan bila ada (audit fix), fallback SO(t-1) teramati, fallback 0."""
    days = sorted(d for d in pair.days if d >= 1)
    out = {}
    for i, t in enumerate(days):
        so_val = pair.get(t, "qtySO")
        in_val = pair.get(t, "qtyIN")
        bk_val = pair.get(t, "qtyBarangKeluar")
        if t == 1 and pair.sa_t1 is not None:
            base = pair.sa_t1
        elif i == 0:
            base = 0.0
        else:
            base = pair.get(days[i - 1], "qtySO")
        out[t] = base + in_val - bk_val - so_val
    return out


def compute_cek(pair: Pair, h: int, ambang_pct: int,
                ri_bal_pairs: set, po_pending_pairs: set) -> list:
    """Label CEK pasangan — PORT VERBATIM kondisi deviasi_view v3.9.27/71
    (formula sheet 'Data Base Cek Deviasi' + kondisi app Promix/RI Balancing).
    Return SEMUA label terpicu (array kontrak); prioritas presentasi desktop
    (np.select Promix→RI Bal→Kosong→Tanggal→Manual→Drastis→ACR) terdokumentasi
    di urutan pengembalian CEK_CANON."""

    def _day_key(t):
        # fix 48-b: 0 → −1 (saldo penutupan bulan lalu) — H=1 → SO(H−1) = penutupan
        return LALU_CLOSING_KEY if t == 0 else t

    so_m1 = pair.get(_day_key(h - 1), "qtySO")
    so_h = pair.get(h, "qtySO")
    in_h = pair.get(h, "qtyIN")
    out_h = pair.get(h, "qtyACR")
    bk_h = pair.get(h, "qtyBarangKeluar")

    # Sistem = 2.SALDO AKHIR @H; pasangan TANPA baris saldo @H → saldo t=1
    # (v3.9.32/33 saldo-only — BUMBU PASTA KUAH); H≤3 pun ikut cabang ini.
    if pair.has(h, "qtySaldoAkhir"):
        sistem = pair.get(h, "qtySaldoAkhir")
    else:
        sistem = pair.get(1, "qtySaldoAkhir")
    deviasi = so_h - sistem

    total_acr = sum(pair.get(t, "qtyACR") for t in pair.days if 1 <= t <= h)

    triggered = []

    # Kondisi 0 "Promix 04" (v3.9.19/21) — sumber SO tanggal H ≠ 'input so harian'
    src = pair.source_data.get(h, "")
    if src and src.strip().lower() != "input so harian":
        triggered.append("Promix 04")

    # Kondisi 1 "RI Balancing" (v3.9.23/24) — pasangan ber-dokumen balancing
    if (_norm_text(pair.barang), _norm_text(pair.resto)) in ri_bal_pairs:
        triggered.append("RI Balancing")

    # Kondisi "Kosong/Non Aktif" — (AKTIF & SO<0) | (NON AKTIF & SO>0)
    a = (pair.aktif or "").strip().upper()
    if (a == "AKTIF" and so_h < 0) or (a == "NON AKTIF" and so_h > 0):
        triggered.append("Kosong/Non Aktif")

    # Kondisi 2 "Beda Tanggal" — port formula LET: J = KIRIMAN KELUAR (8.BK)
    if ((in_h > 0 and so_h < so_m1 and bk_h == 0)
            or (so_m1 > 0 and so_h > so_m1 + 0.5 * so_m1 and in_h == 0 and bk_h == 0)):
        triggered.append("Beda Tanggal")

    # Kondisi 3 "Hitung Manual" — stok = W sheet = SO(H−1)+IN_H−BK_H−PENJUALAN_H
    stok = so_m1 + in_h - bk_h - out_h
    if stok == 0:
        if so_h != 0:
            triggered.append("Hitung Manual")
    else:
        if abs(so_h - stok) / abs(stok) > 1.3:
            triggered.append("Hitung Manual")

    # Kondisi "Turun Drastis" — SO turun > 50% dari SO(H−1)
    if so_m1 > 0 and (so_h / so_m1) < 0.5:
        triggered.append("Turun Drastis")

    # Kondisi 5 "ACR to BOM" — |deviasi| > ambang% × Total ACR (1..H)
    if total_acr > 0 and abs(deviasi) > (float(ambang_pct) / 100.0) * total_acr:
        triggered.append("ACR to BOM")

    # "PO Menunggu" — pasangan ber-PO 32.43 'Menunggu diproses' (v3.9.30)
    if (_norm_text(pair.barang), _norm_resto(pair.resto)) in po_pending_pairs:
        triggered.append("PO Menunggu")

    # "Selisih IN" — |Σ 7.Selisih IN pasangan| ≥ 8 (kontrak §4)
    selisih_in_sum = sum(pair.get(t, "qtySelisihIN") for t in pair.days if t >= 1)
    if abs(selisih_in_sum) >= SELISIH_IN_LABEL_MIN:
        triggered.append("Selisih IN")

    return [c for c in CEK_CANON if c in triggered]


# ---------------------------------------------------------------------------
# Catatan audit B1–B4 per (resto, tgl, barang) — port in_selisih_view v3.9.23
# ---------------------------------------------------------------------------

def build_audit_notes(in_detail_df, audit_df_bulan_ini) -> dict:
    """{(norm_resto, tgl_int, norm_barang): ["B1", ...]} — prioritas urutan
    append desktop: B1 (RI Balancing per tanggal) → B2 (nomor dobel) → B4
    (BM 0 padahal IN > 0) → B3 (Selisih IN ≠ 0)."""
    notes: dict = {}
    if in_detail_df is None:
        in_detail_df = pd.DataFrame()
    if audit_df_bulan_ini is None:
        audit_df_bulan_ini = pd.DataFrame()

    def _add(resto, tgl, barang, code):
        if tgl is None:
            return
        key = (_norm_resto(resto), int(tgl), _norm_text(barang))
        if code not in notes.setdefault(key, []):
            notes[key].append(code)

    # B1 — dokumen RI Balancing per tanggal (port _ri_balancing_by_date)
    for (b, r), per_tgl in _ri_balancing_by_date(in_detail_df).items():
        for t in per_tgl:
            _add(r, t, b, "B1")

    # B2 — nomor dobel (port _duplicated_doc_dates)
    dup = doc_codes.duplicated_doc_numbers(in_detail_df)
    for (b, r), per_tgl in _duplicated_doc_dates(in_detail_df, dup).items():
        for t in per_tgl:
            _add(r, t, b, "B2")

    # B3/B4 — dari angka baris audit itu sendiri (vektor; B4 DIDAHULUKAN B3)
    if not audit_df_bulan_ini.empty:
        bm = pd.to_numeric(audit_df_bulan_ini["Qty SO Harian"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        ins = pd.to_numeric(audit_df_bulan_ini["Penerimaan Sistem"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        sel = pd.to_numeric(audit_df_bulan_ini["Selisih Harian"], errors="coerce") \
            .fillna(0).to_numpy(dtype="float64")
        for i in range(len(audit_df_bulan_ini)):
            r = audit_df_bulan_ini["Resto"].iat[i]
            b = audit_df_bulan_ini["Nama Item"].iat[i]
            t = _tgl_key(audit_df_bulan_ini["Tanggal"].iat[i])
            if bm[i] == 0 and ins[i] > 0:
                _add(r, t, b, "B4")
            elif sel[i] != 0:
                _add(r, t, b, "B3")
    return notes


def _ri_balancing_by_date(in_detail: pd.DataFrame) -> dict:
    """Port verbatim in_selisih_view._ri_balancing_by_date —
    {(barang, resto): {tgl: [(nomor, po_period), ...]}} (kunci tanggal _tgl_key)."""
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
        if doc_codes._ri_balancing(nomor, nomor_po, t) == "":
            continue
        n = doc_codes._doc_code_str(nomor)
        if not n:
            continue
        tkey = _tgl_key(t)
        if tkey is None:
            continue
        per_pair = out.setdefault((str(b), str(r)), {})
        lst = per_pair.setdefault(tkey, [])
        p_po = doc_codes._doc_period(nomor_po)
        item = (n, p_po)
        if item not in lst:
            lst.append(item)
    for per_pair in out.values():
        for lst in per_pair.values():
            lst.sort()
    return out


def _duplicated_doc_dates(in_detail: pd.DataFrame, dup: dict) -> dict:
    """Port verbatim in_selisih_view._duplicated_doc_dates — tanggal kemunculan
    nomor dobel: {(barang, resto): {tgl: [(nomor, jumlah), ...]}}."""
    out: dict = {}
    if in_detail is None or getattr(in_detail, "empty", True) or not dup:
        return out
    need = {"Nomor", "Nama Barang", "NAMA RESTO", "Tanggal"}
    if not need <= set(getattr(in_detail, "columns", [])):
        return out
    d = in_detail[in_detail["Nomor"].notna()].copy()
    if d.empty:
        return out
    d["_nomor"] = d["Nomor"].map(doc_codes._doc_code_str)
    d = d[d["_nomor"].ne("")]
    for (b, r), nomors in dup.items():
        sub = d[(d["Nama Barang"].astype(str) == str(b))
                & (d["NAMA RESTO"].astype(str) == str(r))
                & (d["_nomor"].isin(list(nomors.keys())))]
        per_tgl: dict = {}
        for nomor, t in zip(sub["_nomor"], sub["Tanggal"]):
            tkey = _tgl_key(t)
            if tkey is None:
                continue
            lst = per_tgl.setdefault(tkey, [])
            if nomor not in [x for x, _ in lst]:
                lst.append((nomor, int(nomors.get(nomor, 0))))
        if per_tgl:
            out[(str(b), str(r))] = {t: sorted(v) for t, v in per_tgl.items()}
    return out


# ---------------------------------------------------------------------------
# PO → EnginePo
# ---------------------------------------------------------------------------

def map_po(rincian_po_df: pd.DataFrame) -> list:
    """Rincian PO 32.43 (terfilter DEVIASI — mirror tab 🛒 desktop) → EnginePo[]
    dikelompokkan per Nomor #. status ringkas: semua 'menunggu diproses' →
    Menunggu; semua 'selesai' → Selesai; campuran → Diproses. annotasi
    '↳ <status dominan>' bila ada item menunggu (paritas desktop)."""
    out = []
    if rincian_po_df is None or rincian_po_df.empty:
        return out
    df = rincian_po_df
    if "Nomor #" not in df.columns:
        return out
    groups: dict = {}
    order: list = []
    for i in range(len(df)):
        nomor = str(df["Nomor #"].iat[i]).strip()
        if not nomor:
            continue
        g = groups.get(nomor)
        if g is None:
            g = {"cabang_raw": None, "tanggal": None, "supplier": None, "items": []}
            groups[nomor] = g
            order.append(nomor)
        if g["cabang_raw"] is None and "Cabang PO" in df.columns:
            g["cabang_raw"] = str(df["Cabang PO"].iat[i]).strip()
        if g["tanggal"] is None and "Tanggal" in df.columns:
            t = df["Tanggal"].iat[i]
            try:
                if t is not None and not pd.isna(t):
                    g["tanggal"] = pd.Timestamp(t).strftime("%Y-%m-%d")
            except (TypeError, ValueError, pd.errors.OutOfBoundsDatetime):
                pass
        if g["supplier"] is None and "Pemasok" in df.columns:
            g["supplier"] = str(df["Pemasok"].iat[i]).strip()
        qty = _num(df["Kuantitas"].iat[i]) if "Kuantitas" in df.columns else None
        status = (str(df["Status Pesanan Pembelian"].iat[i]).strip()
                  if "Status Pesanan Pembelian" in df.columns else "")
        out_item = {
            "itemName": str(df["Nama Barang"].iat[i]).strip(),
            "qty": qty if qty is not None else 0.0,
            "satuan": (str(df["Satuan"].iat[i]).strip() if "Satuan" in df.columns else ""),
            "status": status,
            "diterimaSebagian": "sebagian" in status.lower(),
        }
        g["items"].append(out_item)

    for nomor in order:
        g = groups[nomor]
        items = g["items"]
        statuses = [it["status"].strip().lower() for it in items]
        n_menunggu = sum(1 for s in statuses if s == "menunggu diproses")
        n_selesai = sum(1 for s in statuses if s == "selesai")
        if n_menunggu == len(statuses) and n_menunggu > 0:
            status = "Menunggu"
        elif n_selesai == len(statuses) and n_selesai > 0:
            status = "Selesai"
        else:
            status = "Diproses"
        # statusPesanan dominan (frekuensi; tie → urutan kemunculan pertama)
        status_pesanan = ""
        if statuses:
            counts: dict = {}
            for s in items[0]["status"], *[it["status"] for it in items[1:]]:
                counts[s] = counts.get(s, 0) + 1
            status_pesanan = max(counts.items(), key=lambda kv: kv[1])[0]
        annotasi = f"↳ {status_pesanan}" if n_menunggu > 0 and status_pesanan else None
        out.append({
            "cabang": resto_from_cabang_po(g["cabang_raw"]) or (g["cabang_raw"] or ""),
            "restoName": g["cabang_raw"] or "",
            "poNumber": nomor,
            "tanggal": g["tanggal"] or "",
            "supplier": g["supplier"] or "",
            "itemCount": len(items),
            "status": status,
            "statusPesanan": status_pesanan,
            "annotasi": annotasi,
            "items": items,
        })
    out.sort(key=lambda p: (p["cabang"], p["poNumber"]))
    return out


# ---------------------------------------------------------------------------
# Builder utama
# ---------------------------------------------------------------------------

def build_engine_result(*, config, params: dict, append1_df, rincian_po_df,
                        in_detail_df, audit_result, po_pending_df,
                        log_text: str, started_at: datetime,
                        duration_ms: int) -> dict:
    """Semua keluaran pipeline + log → EngineResult dict murni-Python (kontrak v1)."""
    started_at_iso = started_at.isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    parsed = parse_pipeline_log(log_text, started_at_iso)
    logs = list(parsed["logs"])
    skipped = parsed["skipped"]

    h = int(params["tanggalH"])
    ambang = int(params["ambangAcrPct"])

    harga_map = audit_result.get("harga_map") or {}
    konversi_map = audit_result.get("konversi_map") or {}
    audit_bulan_ini = audit_result.get("df_bulan_ini")
    if audit_bulan_ini is None:
        audit_bulan_ini = audit_result.get("df")
        if audit_bulan_ini is None:
            audit_bulan_ini = pd.DataFrame()

    # Pasangan CEK RI Balancing (deviasi_view) + pasangan PO menunggu (fn_audit)
    ri_bal_pairs = set()
    if in_detail_df is not None and not in_detail_df.empty:
        for (b, r) in doc_codes.ri_balancing_docs(in_detail_df).keys():
            ri_bal_pairs.add((_norm_text(b), _norm_text(r)))
    po_pending_pairs = set()
    if po_pending_df is not None and not po_pending_df.empty:
        for i in range(len(po_pending_df)):
            b = str(po_pending_df["Nama Barang"].iat[i]).strip()
            r_raw = (po_pending_df["Cabang PO"].iat[i]
                     if "Cabang PO" in po_pending_df.columns else None)
            po_pending_pairs.add((_norm_text(b), _norm_resto(r_raw)))

    audit_notes = build_audit_notes(in_detail_df, audit_bulan_ini)

    pairs = build_pairs(append1_df)

    rows = []
    prices_by_key: dict = {}
    kategori_tanpa_count = 0
    for key in sorted(pairs.keys()):
        p = pairs[key]
        resto_code = resto_from_cabang_po(p.resto) or p.resto
        satuan = p.satuan or ""
        kategori = _kategori_or_tanpa(p.kategori)
        if kategori == KATEGORI_TANPA:
            kategori_tanpa_count += 1
        is_gr = satuan.strip().upper() == "GR"

        # Harga efektif pasangan (lookup_harga_pair — port v3.9.55).
        # konversiOk = HANYA kegagalan konversi satuan (penanda '*' desktop);
        # "tanpa harga 41.09" = hargaEfektif null dengan konversiOk true —
        # dua penyebab nominal-null yang BERBEDA (INV-3; mirror desktop:
        # barang tanpa harga TIDAK diberi bintang).
        harga_norm, _label, bintang = nominal_common.lookup_harga_pair(
            harga_map, konversi_map, p.barang, satuan)
        konversi_ok = not bintang

        cek = compute_cek(p, h, ambang, ri_bal_pairs, po_pending_pairs)
        com = compute_com(p)

        for day in sorted(d for d in p.days if d >= 1):
            m = p.days[day]
            dev = _num(m.get("qtyDeviasi"))
            nominal = None
            if konversi_ok and harga_norm is not None and dev not in (None, 0):
                nominal = round(float(harga_norm) * dev, 2)
            note = audit_notes.get((_norm_resto(p.resto), day, _norm_text(p.barang)))
            rows.append({
                "restoCode": resto_code,
                "restoName": p.resto,
                "itemName": p.barang,
                "satuan": satuan,
                "kategori": kategori,
                "isGR": is_gr,
                "day": day,
                "qtySaldoAwal": _num(m.get("qtySaldoAwal")),
                "qtySO": _num(m.get("qtySO")),
                "qtySaldoAkhir": _num(m.get("qtySaldoAkhir")),
                "qtyDeviasi": dev,
                "qtyIN": _num(m.get("qtyIN")),
                "qtyBarangMasuk": _num(m.get("qtyBarangMasuk")),
                "qtyCOM": _num(com.get(day)),
                "qtySelisihIN": _num(m.get("qtySelisihIN")),
                "qtyBarangKeluar": _num(m.get("qtyBarangKeluar")),
                "qtyACR": _num(m.get("qtyACR")),
                "hargaEfektif": _num(harga_norm) if harga_norm is not None else None,
                "konversiOk": bool(konversi_ok),
                "nominal": nominal,
                "cek": cek,
                "auditNote": note[0] if note else None,
            })

        # prices — satu per (itemName, satuan rekap) dengan resolusi harga pair
        pk = (p.barang, satuan)
        if pk not in prices_by_key:
            if bintang:
                alasan = "Konversi satuan rekap↔41.09 gagal — harga as-is berpenanda * (INV-3)"
                prices_by_key[pk] = {
                    "itemName": p.barang, "satuan": satuan,
                    "harga": None, "rasioKonversi": None,
                    "konversiOk": False, "alasan": alasan,
                }
            elif harga_norm is None:
                prices_by_key[pk] = {
                    "itemName": p.barang, "satuan": satuan,
                    "harga": None, "rasioKonversi": None,
                    "konversiOk": True,
                    "alasan": "Harga 41.09 tidak tersedia untuk barang ini",
                }
            else:
                sat41 = None
                entry = (harga_map.get(nominal_common.norm_barang_harga_key(p.barang))
                         or harga_map.get(str(p.barang).strip()))
                if entry is not None:
                    sat41 = entry[1]
                rasio = None
                if sat41:
                    r_rekap, _t1 = lookup_rasio(konversi_map, str(p.barang).strip(), satuan)
                    r_41, _t2 = lookup_rasio(konversi_map, str(p.barang).strip(), sat41)
                    if r_rekap and r_41:
                        rasio = round(r_rekap / r_41, 6)
                prices_by_key[pk] = {
                    "itemName": p.barang, "satuan": satuan,
                    "harga": _num(harga_norm), "rasioKonversi": rasio,
                    "konversiOk": True, "alasan": None,
                }

    # --- selisihIn per resto (varian audit BULAN INI — default desktop) ---
    selisih_in = []
    if audit_bulan_ini is not None and not audit_bulan_ini.empty:
        per_resto: dict = {}
        order: list = []
        ins = pd.to_numeric(audit_bulan_ini["Penerimaan Sistem"], errors="coerce").fillna(0)
        bms = pd.to_numeric(audit_bulan_ini["Qty SO Harian"], errors="coerce").fillna(0)
        sel = pd.to_numeric(audit_bulan_ini["Selisih Harian"], errors="coerce").fillna(0)
        for i in range(len(audit_bulan_ini)):
            r_raw = str(audit_bulan_ini["Resto"].iat[i]).strip()
            code = _norm_resto(r_raw)
            e = per_resto.get(code)
            if e is None:
                e = {"restoCode": code or r_raw, "restoName": r_raw,
                     "inAccurate": 0.0, "barangMasuk": 0.0, "selisih": 0.0,
                     "items": set(), "dates": set()}
                per_resto[code] = e
                order.append(code)
            e["inAccurate"] += float(ins.iat[i])
            e["barangMasuk"] += float(bms.iat[i])
            e["selisih"] += float(sel.iat[i])
            if float(sel.iat[i]) != 0:
                e["items"].add(_norm_text(audit_bulan_ini["Nama Item"].iat[i]))
                t = _tgl_key(audit_bulan_ini["Tanggal"].iat[i])
                if t is not None and t >= 1:
                    e["dates"].add(t)
        for code in sorted(per_resto.keys()):
            e = per_resto[code]
            selisih_in.append({
                "restoCode": e["restoCode"],
                "restoName": e["restoName"],
                "inAccurate": _num(e["inAccurate"]),
                "barangMasuk": _num(e["barangMasuk"]),
                "selisih": _num(e["selisih"]),
                "hasilAudit": "SELISIH" if e["selisih"] != 0 or e["items"] else "OK",
                "skorResto": len(e["items"]) + len(e["dates"]),
                "itemBerselisih": len(e["items"]),
                "tanggalTerdampak": len(e["dates"]),
            })

    # --- DQ issues + baris log observasi [ENGINE] (§3.4: tiap DQ WARNING/ERROR
    #     punya ≥1 baris log selevel) ---
    dq_issues = []
    seen_warn_lines = set()

    # preflight folder (helpers.preflight_folders — mirror app.py desktop)
    missing_folders, _counts = preflight_folders(config)
    for key, full in missing_folders:
        msg = f"preflight: folder {key} ({full}) tidak ditemukan — 0 file terbaca"
        dq_issues.append({"severity": "WARNING", "code": "PREFLIGHT_FOLDER",
                          "message": msg, "source": key, "sheet": None,
                          "rawValue": None, "rowNumber": None})
        logs.append({"ts": now_iso, "level": "WARNING",
                     "message": f"[ENGINE] WARNING {msg}"})

    # skip file + klasifikasi baris WARNING pipeline (§82b — dari log)
    for fname, reason in skipped:
        dq_issues.append({"severity": "WARNING", "code": "SKIP_FILE",
                          "message": f"File dilewati: {fname} — {reason}",
                          "source": fname, "sheet": None,
                          "rawValue": reason, "rowNumber": None})
    for log in parsed["logs"]:
        if log["level"] in ("WARNING", "ERROR"):
            msg = log["message"]
            if msg in seen_warn_lines:
                continue
            seen_warn_lines.add(msg)
            dq_issues.append({"severity": log["level"],
                              "code": _classify_warning(msg),
                              "message": msg, "source": None, "sheet": None,
                              "rawValue": None, "rowNumber": None})

    # konversi gagal / tanpa harga (dari prices — INV-3)
    for pk in sorted(prices_by_key.keys()):
        pr = prices_by_key[pk]
        if not pr["konversiOk"]:
            msg = (f"Konversi satuan rekap↔41.09 gagal: {pr['itemName']} "
                   f"({pr['satuan']}) — harga as-is berpenanda * (INV-3)")
            dq_issues.append({"severity": "WARNING", "code": "KONVERSI_GAGAL",
                              "message": msg, "source": pr["itemName"], "sheet": None,
                              "rawValue": None, "rowNumber": None})
            logs.append({"ts": now_iso, "level": "WARNING",
                         "message": f"[ENGINE] WARNING {msg}"})
        if pr["harga"] is None and pr["konversiOk"]:
            msg = (f"Tanpa harga 41.09: {pr['itemName']} ({pr['satuan']}) — "
                   "nominal tidak dapat dihitung (INV-3)")
            dq_issues.append({"severity": "INFO", "code": "TANPA_HARGA",
                              "message": msg, "source": pr["itemName"], "sheet": None,
                              "rawValue": None, "rowNumber": None})

    # kategori kosong — agregat jujur (satu isu, dihitung per pasangan unik)
    if kategori_tanpa_count:
        msg = (f"{kategori_tanpa_count} pasangan tanpa kategori master — "
               f"tampil sebagai '{KATEGORI_TANPA}' (jujur, bukan error)")
        dq_issues.append({"severity": "INFO", "code": "KATEGORI_KOSONG",
                          "message": msg, "source": None, "sheet": None,
                          "rawValue": None, "rowNumber": None})

    # --- sourceFiles (manifest — FR-1/FR-2: pemetaan config.json) ---
    source_files = []
    skipped_names = {f for f, _r in skipped}
    sheet_by_folder = {
        "RekapBerjalan": "RekapMentah", "RekapLalu": "RekapMentah",
        "Penjualan2205": "Penjualan2205", "Kirim4215": "Pemindahan4215",
        "Terima4215": "Pemindahan4215", "RI3224": "Penerimaan3224",
        "RI3224Lalu": "Penerimaan3224", "SaldoAwal4217": "SaldoAwal4217",
        "DBSKategori": "DBSKategori", "Pemindahan4205": "Pemindahan4205",
        "Pemindahan4205Lalu": "Pemindahan4205", "RincianPO": "PesananPO",
        "Data9901": None, "Harga": "Harga",
    }
    for key in sorted(config.Folders.keys()):
        try:
            full = config.folder(key)
        except Exception:  # pragma: no cover — Config defensif
            continue
        rows_per_file = parsed["per_file_rows"].get(full, {})
        multi = full in parsed["multiwarn"]
        try:
            files = _list_excel_files(full)
        except Exception:  # pragma: no cover
            files = []
        for f in files:
            base = os.path.basename(f)
            sheet_key = sheet_by_folder.get(key)
            sheet_name = None
            if sheet_key:
                try:
                    sheet_name = config.sheet(sheet_key)
                except Exception:  # pragma: no cover
                    sheet_name = None
            if base in skipped_names:
                status = "SKIP"
            elif multi and base in rows_per_file:
                status = "WARNING"
            else:
                status = "OK"
            try:
                size = os.path.getsize(f)
            except OSError:
                size = 0
            source_files.append({
                "folderKey": key, "fileName": base, "sheetName": sheet_name,
                "rowCount": int(rows_per_file.get(base, 0)),
                "sizeBytes": size, "status": status,
            })

    # --- ringkasan + status akhir (§82b / §3.5) ---
    day_count = max((r["day"] for r in rows), default=0)
    resto_codes = {r["restoCode"] for r in rows}
    item_names = {r["itemName"] for r in rows}
    nominal_total = round(sum(r["nominal"] for r in rows if r["nominal"] is not None), 2)
    dev_total = round(sum(r["qtyDeviasi"] for r in rows if r["qtyDeviasi"] is not None), 6)
    warning_count = sum(1 for l in logs if l["level"] == "WARNING")
    error_count = sum(1 for l in logs if l["level"] == "ERROR")
    if any(d["severity"] == "ERROR" for d in dq_issues):
        status = "SELESAI_PARSIAL"
    elif any(d["severity"] == "WARNING" for d in dq_issues):
        status = "SELESAI_DENGAN_PERINGATAN"
    else:
        status = "SELESAI"

    logs.append({"ts": now_iso, "level": "INFO",
                 "message": f"[ENGINE] {status} — {len(rows)} baris · "
                            f"{len(dq_issues)} DQ issue · {warning_count} WARNING "
                            f"({len(logs) + 1} baris log)"})

    prices = [prices_by_key[k] for k in sorted(prices_by_key.keys())]

    return {
        "contractVersion": CONTRACT_VERSION,
        "engineKind": "production",
        "engineName": ENGINE_NAME,
        "engineVersion": ENGINE_VERSION,
        "definitionVersion": DEFINITION_VERSION,
        "periodKey": params["periodKey"],
        "params": {"tanggalH": h, "ambangAcrPct": ambang,
                   "bundleName": params.get("bundleName")},
        "status": status,
        "startedAt": started_at_iso,
        "durationMs": int(duration_ms),
        "summary": {
            "restoCount": len(resto_codes),
            "itemCount": len(item_names),
            "rowCount": len(rows),
            "dayCount": day_count,
            "nominalTotal": nominal_total,
            "deviasiQtyTotal": dev_total,
            "skipFileCount": len(skipped),
            "warningCount": warning_count,
            "errorCount": error_count,
            "dqIssueCount": len(dq_issues),
            "poCount": 0,  # diisi caller
        },
        "sourceFiles": source_files,
        "rows": rows,
        "prices": prices,
        "selisihIn": selisih_in,
        "po": [],  # diisi caller
        "dqIssues": dq_issues,
        "logs": logs,
    }
