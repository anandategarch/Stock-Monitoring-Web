"""
fn_audit.py — Audit Rekonsiliasi: engine VBA + input dari DATA APP (v3.6).

v3.6 (permintaan user): sheet '29 Rekap Barang Masuk' TIDAK DIBACA LAGI.
Logika macro VBA "BuatLaporanDeviasiSampel" diaplikasikan langsung ke data
yang SUDAH dibaca pipeline, dengan tambahan kolom SO (Hasil SO) + kolom
hasil audit — semuanya bisa difilter dari header tabel.

DUA bagian:

1. build_audit_input(rekap_so_df, in_detail_df)
   Bangun input 10 kolom kanonik (persis struktur input VBA) dari:
   - Hasil SO      ← rekap mentah JENIS='SO'
                     (hari 1..31 berjalan + -25..-31 bulan lalu; baris
                     HANYA ada di tanggal yang SO benar-benar direkam —
                     kehadiran terjaga, bukan 0-fill)
   - Qty SO Harian ← rekap mentah JENIS='BARANG MASUK' (input resto di
                     rekap; kosong selama belum diinput — audit akan
                     menandai baris IN sebagai deviasi sampai terisi)
   - Qty SJ        ← in_detail SOURCE IN='42.05' + '42.05 (Bulan Lalu)'
   - Qty RI        ← in_detail SOURCE IN='32.24' + '32.24 (Bulan Lalu)'
   - Qty Pembelian ← in_detail SOURCE IN='99.01'
   Baris = union tanggal dgn aktivitas (SO direkam / BM / IN ≠ 0),
   diurutkan per (Resto, Nama Item, Tanggal).

2. build_audit_rekap(df)
   Port 1:1 algoritma rekonsiliasi VBA (grup kontigu Resto+Item, urut
   tanggal; selisih & penerimaan dihitung ulang):
   - Penerimaan Sistem = SJ + RI + Pembelian
   - Selisih Harian    = Qty SO Harian − Penerimaan Sistem
   - ATURAN VALID: SO naik (deltaSO>0) + SO Harian=0 + Penerimaan>0
     → "VALID (Sistem Masuk)" (omit input harian)
   - "OK (Matching)" saat selisih=0 & saldo kumulatif=0
   - Saldo kumulatif per grup; kembali ±0.0001 → "CUT-OFF RESOLVED"
     (baris selisih≠0) / "OK (Dalam Cut-off)" (baris selisih=0)
   - Sisa gantung akhir grup → "DEVIASI MURNI" / "OK"
   - KPI: rows/cutoff/omit/deviasi_murni/deviasi_qty/ok

v3.9.6 (permintaan user: "tab selisih in jika tanggal 1 pembanding SO nya
SO bulan lalu"): urutan baris per grup kini KRONOLOGIS — bulan lalu
(Tanggal −25..−31) urut hari naik 25•→31•, lalu bulan berjalan 1..31.
Sort numerik lama membalik urutan bulan lalu (−31 duluan) sehingga baris
tepat sebelum tanggal 1 = Tanggal −25 (SO tgl 25•) — delta SO "SO Naik"
di tanggal 1 salah membanding. Dengan urutan kronologis, pembanding SO
tanggal 1 = SO TERAKHIR bulan lalu (31•) = "SO bulan lalu" yang benar.

Riwayat validasi: engine tervalidasi 100% identik dgn sheet
LAPORAN_DEVIASI user (output macro asli) pada input yang sama
(86.738 baris; 25 baris beda terbukti snapshot data lama) — port dipakai
apa adanya; v3.6 hanya mengganti SUMBER input.

v3.9.30 — PO MENUNGGU DIPROSES (32.43) sebagai PENJELAS DEVIASI MURNI
(hipotesis user: PO sudah dibuat tapi penerimaan belum di-update di
sistem → Qty RI = 0 → selisih SO Harian − Penerimaan menumpuk jadi
saldo gantung). Input opsional po_pending_df (Rincian PO mentah —
difilter status 'Menunggu diproses' internal) → kolom 'Qty PO
Menunggu' per pasangan + catatan 'PO Menunggu: PO.xxx (qty n)' di
baris DEVIASI MURNI + KPI 'dev_murni_po' (deviasi murni explainable
vs perlu audit fisik). Engine VBA TIDAK diubah — enrichment dipasang
SETELAH build_audit_rekap; pemanggil lama (tanpa PO) tak tersentuh.
"""
from typing import Optional

import numpy as np
import pandas as pd

from .helpers import resto_from_cabang_po
from .konversi_satuan import lookup_rasio

# Kolom kanonik input audit (struktur identik input VBA / sheet 29)
AUDIT_INPUT_COLUMNS = [
    "Resto", "Nama Item", "UoM", "Tanggal", "Hasil SO",
    "Qty SO Harian", "Qty SJ", "Qty RI", "Qty Pembelian", "Selisih Qty",
]

_KEY_COLS = ["NAMA RESTO", "Nama Barang", "Tanggal"]


def _agg_sum(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Groupby (resto, barang, tgl) → sum(value)."""
    d = df[_KEY_COLS + [value_col]].copy()
    d["Tanggal"] = pd.to_numeric(d["Tanggal"], errors="coerce")
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d = d.dropna(subset=_KEY_COLS)
    return d.groupby(_KEY_COLS, as_index=False, dropna=False)[value_col].sum()


def build_audit_input(rekap_so_df: Optional[pd.DataFrame],
                      in_detail_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Bangun input audit (10 kolom kanonik) dari data app.

    rekap_so_df : rekap mentah long (JENIS 'SO' / 'BARANG MASUK') —
                  keluaran query_full_rekap_mentah_so (dipapankan dari
                  build_append1 via rekap_so_out).
    in_detail_df: detail IN per dokumen (SOURCE IN 42.05 / 42.05 (Bulan
                  Lalu) / 32.24 / 32.24 (Bulan Lalu) / 99.01).
    """
    empty = pd.DataFrame(columns=AUDIT_INPUT_COLUMNS)

    so = pd.DataFrame()
    bm = pd.DataFrame()
    if rekap_so_df is not None and not rekap_so_df.empty \
            and "JENIS" in rekap_so_df.columns:
        jenis = rekap_so_df["JENIS"].fillna("").astype(str) \
            .str.strip().str.upper()
        so = rekap_so_df[jenis == "SO"]
        bm = rekap_so_df[jenis == "BARANG MASUK"]

    so_agg = _agg_sum(so, "Value").rename(columns={"Value": "Hasil SO"}) \
        if not so.empty else pd.DataFrame(columns=_KEY_COLS + ["Hasil SO"])
    bm_agg = _agg_sum(bm, "Value").rename(columns={"Value": "Qty SO Harian"}) \
        if not bm.empty else pd.DataFrame(columns=_KEY_COLS + ["Qty SO Harian"])

    sj = ri = pb = pd.DataFrame()
    if in_detail_df is not None and not in_detail_df.empty \
            and "SOURCE IN" in in_detail_df.columns:
        src = in_detail_df["SOURCE IN"].fillna("").astype(str).str.strip()
        # v3.9.17: 42.05 bulan lalu ikut Qty SJ (Kiriman HO) — sumber IN
        sj = in_detail_df[src.isin(["42.05", "42.05 (Bulan Lalu)"])]
        ri = in_detail_df[src.isin(["32.24", "32.24 (Bulan Lalu)"])]
        pb = in_detail_df[src == "99.01"]
    sj_agg = _agg_sum(sj, "Value").rename(columns={"Value": "Qty SJ"}) \
        if not sj.empty else pd.DataFrame(columns=_KEY_COLS + ["Qty SJ"])
    ri_agg = _agg_sum(ri, "Value").rename(columns={"Value": "Qty RI"}) \
        if not ri.empty else pd.DataFrame(columns=_KEY_COLS + ["Qty RI"])
    pb_agg = _agg_sum(pb, "Value").rename(columns={"Value": "Qty Pembelian"}) \
        if not pb.empty else pd.DataFrame(columns=_KEY_COLS + ["Qty Pembelian"])

    # baris = union tanggal dengan aktivitas:
    # SO direkam (baris rekap ada — hadir walaupun nilainya 0),
    # BM diinput, atau ada penerimaan sistem (IN ≠ 0)
    parts = []
    for d in (so_agg, bm_agg):
        if not d.empty:
            parts.append(d[_KEY_COLS])
    for d in (sj_agg, ri_agg, pb_agg):
        if not d.empty:
            nz = d[d.columns[-1]] != 0
            parts.append(d.loc[nz, _KEY_COLS])
    if not parts:
        return empty
    keys = pd.concat(parts, ignore_index=True).drop_duplicates()

    out = keys.merge(so_agg, on=_KEY_COLS, how="left") \
        .merge(bm_agg, on=_KEY_COLS, how="left") \
        .merge(sj_agg, on=_KEY_COLS, how="left") \
        .merge(ri_agg, on=_KEY_COLS, how="left") \
        .merge(pb_agg, on=_KEY_COLS, how="left")

    out = out.rename(columns={"NAMA RESTO": "Resto",
                              "Nama Barang": "Nama Item"})
    out["UoM"] = ""          # Satuan dipetakan view dari append1
    out["Tanggal"] = pd.to_numeric(out["Tanggal"], errors="coerce")
    out = out.dropna(subset=["Tanggal"])
    out["Tanggal"] = out["Tanggal"].astype("Int64")
    for c in ("Hasil SO", "Qty SO Harian", "Qty SJ", "Qty RI",
              "Qty Pembelian"):
        out[c] = pd.to_numeric(out[c], errors="coerce")  # NaN = tidak ada
    out["Selisih Qty"] = (
        out["Qty SO Harian"].fillna(0.0)
        - (out["Qty SJ"].fillna(0.0) + out["Qty RI"].fillna(0.0)
           + out["Qty Pembelian"].fillna(0.0))
    )
    out["Resto"] = out["Resto"].astype(str)
    out["Nama Item"] = out["Nama Item"].astype(str)
    out = out[AUDIT_INPUT_COLUMNS]
    # urut per (Resto, Nama Item) → grup kontigu; tanggal KRONOLOGIS:
    # bulan lalu (negatif) duluan urut hari NAIK (25•→31• = -25→-31),
    # lalu bulan berjalan 1..31.
    # v3.9.6 (permintaan user: "tab selisih in jika tanggal 1 pembanding
    # SO nya SO bulan lalu"): sort numerik lama membalik urutan bulan lalu
    # (−31/31• tampil PERTAMA, baris terakhir sebelum tgl 1 = −25/25•) —
    # delta SO di tanggal 1 membanding SO tgl 25 bulan lalu, BUKAN SO
    # terakhir bulan lalu (31•). Dengan sort kronologis, baris tepat
    # sebelum tanggal 1 = SO terakhir bulan lalu → pembanding benar.
    tgl_num = pd.to_numeric(out["Tanggal"], errors="coerce")
    _k1 = np.where(tgl_num < 0, 0, 1)          # 0 = bulan lalu, 1 = berjalan
    _k2 = np.where(tgl_num < 0, -tgl_num, tgl_num)  # hari (25..31 / 1..31)
    out = out.assign(_k1=_k1, _k2=_k2)
    out = out.sort_values(["Resto", "Nama Item", "_k1", "_k2"],
                          kind="mergesort", na_position="last")
    out = out.drop(columns=["_k1", "_k2"]).reset_index(drop=True)
    return out


# =============================================================================
# ENGINE AUDIT REKONSILIASI (port 1:1 VBA BuatLaporanDeviasiSampel)
# =============================================================================

# Status (persis string VBA)
ST_OK_MATCH = "OK (Matching)"
ST_VALID = "VALID (Sistem Masuk)"
ST_CUTOFF = "CUT-OFF RESOLVED"
ST_IN_CUTOFF = "OK (Dalam Cut-off)"
ST_DEV_MURNI = "DEVIASI MURNI"
ST_OK = "OK"

# v3.9.30 — status Pesanan Pembelian 32.43 yang berarti PO SUDAH dibuat
# tapi belum diproses jadi penerimaan (RI) — hipotesis user: penyebab
# deviasi murni (PO ada, penerimaan belum di-update sistem → Qty RI 0
# → selisih SO Harian − Penerimaan gantung).
PO_STATUS_MENUNGGU = "menunggu diproses"

_EPS = 0.0001


def _fmt_qty(v: float) -> str:
    """Format mirip VBA '#,##0' dgn locale Indonesia: bulat + titik ribuan
    (identik output macro user: 'SO Naik +63.405', 'Sisa Gantung: -5.705')."""
    iv = int(v + (0.5 if v >= 0 else -0.5))   # round half away from zero
    return f"{iv:,}".replace(",", ".")


def _fmt_signed(v: float) -> str:
    """Format VBA '+#,##0;-#,##0;0' (locale Indonesia) utk Sisa Gantung.
    VBA membulatkan ke integer DULU lalu pilih pola (+/-/0) — nilai
    -0.0004 tampil '0', bukan '-0'."""
    iv = int(v + (0.5 if v >= 0 else -0.5))
    if iv > 0:
        return f"+{f'{iv:,}'.replace(',', '.')}"
    if iv < 0:
        return f"-{f'{-iv:,}'.replace(',', '.')}"
    return "0"


def build_audit_rekap(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Jalankan algoritma rekonsiliasi → (df hasil + kolom audit, KPI dict).

    Baris diproses PERSIS urutan input; grup = blok kontigu dengan
    pasangan (Resto, Nama Item) sama — perilaku identik macro VBA (input
    v3.6 sudah diurutkan per Resto+Item+Tanggal). FIX 6f-02: pasangan
    dibandingkan sebagai TUPLE (bukan konkatenasi 'Resto|Item' — kolisi
    bila nilai memuat '|').
    """
    n = len(df)
    kpi = {
        "rows": n, "cutoff": 0, "omit": 0, "deviasi_murni": 0,
        "deviasi_qty": 0.0, "ok": 0,
    }
    out = df.copy()
    if n == 0:
        for c in ("Penerimaan Sistem", "Selisih Harian", "Saldo Kumulatif",
                  "Status Analisis Audit", "Detail & Catatan Audit"):
            out[c] = pd.Series(dtype="object")
        return out, kpi

    # --- array numerik (NaN → 0, kecuali Hasil SO yang mempertahankan
    # kehadiran — mirror IsNumeric/IsEmpty VBA) ---
    def _col(name: str) -> np.ndarray:
        return pd.to_numeric(df[name], errors="coerce").fillna(0.0) \
            .to_numpy(dtype="float64")

    hasil_so = pd.to_numeric(df["Hasil SO"], errors="coerce") \
        .to_numpy(dtype="float64")            # NaN = sel Hasil SO kosong
    so_harian = _col("Qty SO Harian")
    sj = _col("Qty SJ")
    ri = _col("Qty RI")
    pb = _col("Qty Pembelian")
    penerimaan = sj + ri + pb
    selisih = so_harian - penerimaan
    tgl = pd.to_numeric(df["Tanggal"], errors="coerce").fillna(0) \
        .to_numpy(dtype="float64")

    # FIX 6f-02 (audit 6-f): kunci grup = TUPLE (resto, item) — bukan
    # konkatenasi 'Resto|Item': pasangan ('A','B|C') dan ('A|B','C') dulu
    # menyatu jadi 'A|B|C' (satu grup palsu — saldo kumulatif lintas
    # pasangan menyambung, KPI cut-off/deviasi meleset). Tuple
    # dibandingkan eksak; konsisten dgn kunci pasangan (resto, barang)
    # di _po_menunggu_pairs / _apply_po_menunggu.
    keys = list(zip(df["Resto"].astype(str),
                    df["Nama Item"].astype(str)))

    saldo = [0.0] * n
    status = [""] * n
    detail = [""] * n

    def _tgl_int(i: int) -> int:
        return int(tgl[i])

    group_start = 0
    while group_start < n:
        group_end = group_start
        while group_end + 1 < n and keys[group_end + 1] == keys[group_start]:
            group_end += 1

        cum = 0.0
        start_idx = -1          # sentinel (VBA startIdx = 0, array 1-based)

        for i in range(group_start, group_end + 1):
            sel_val = selisih[i]
            has_so = not np.isnan(hasil_so[i])
            delta_so = 0.0
            if i > group_start:
                has_prev = not np.isnan(hasil_so[i - 1])
                if has_so and has_prev:
                    delta_so = hasil_so[i] - hasil_so[i - 1]

            # ATURAN BISNIS: SO Naik + Penerimaan Sistem > 0 + SO Harian = 0
            if delta_so > 0 and so_harian[i] == 0.0 and penerimaan[i] > 0.0:
                saldo[i] = cum
                status[i] = ST_VALID
                detail[i] = (f"SO Naik +{_fmt_qty(delta_so)} | Omit Input "
                             "SO Harian (Penerimaan Sistem OK)")
                kpi["omit"] += 1
            else:
                if sel_val == 0.0 and cum == 0.0:
                    saldo[i] = 0.0
                    status[i] = ST_OK_MATCH
                    detail[i] = "-"
                    kpi["ok"] += 1
                else:
                    if cum == 0.0 and sel_val != 0.0:
                        start_idx = i
                    cum += sel_val
                    saldo[i] = cum

                    if abs(cum) < _EPS and start_idx >= 0:
                        start_tgl = _tgl_int(start_idx)
                        end_tgl = _tgl_int(i)
                        jeda = abs(end_tgl - start_tgl)
                        for j in range(start_idx, i + 1):
                            if status[j] == "":
                                if selisih[j] != 0.0:
                                    status[j] = ST_CUTOFF
                                    detail[j] = (f"Beda {jeda} Hari "
                                                 f"(Periode Tgl {start_tgl} - "
                                                 f"{end_tgl})")
                                    kpi["cutoff"] += 1
                                else:
                                    status[j] = ST_IN_CUTOFF
                                    detail[j] = (f"Rentang Cut-off Tgl "
                                                 f"{start_tgl} - {end_tgl}")
                        cum = 0.0
                        start_idx = -1

        # sisa gantung di akhir grup → Deviasi Murni
        if start_idx >= 0 and abs(cum) >= _EPS:
            open_tgl = _tgl_int(start_idx)
            for j in range(start_idx, group_end + 1):
                if status[j] == "":
                    if selisih[j] != 0.0:
                        status[j] = ST_DEV_MURNI
                        detail[j] = (f"Sisa Gantung: {_fmt_signed(cum)} "
                                     f"(Sejak Tgl {open_tgl})")
                        kpi["deviasi_murni"] += 1
                    else:
                        status[j] = ST_OK
                        detail[j] = "-"
            kpi["deviasi_qty"] += cum

        group_start = group_end + 1

    out["Penerimaan Sistem"] = penerimaan
    out["Selisih Harian"] = selisih
    out["Saldo Kumulatif"] = saldo
    out["Status Analisis Audit"] = status
    out["Detail & Catatan Audit"] = detail
    return out, kpi


def _filter_bulan_ini(df: "pd.DataFrame | None") -> "pd.DataFrame | None":
    """v3.9.27 — buang baris Tanggal NEGATIF (data bulan lalu: rekap lalu
    25..31 dinegasikan + IN 42.05/32.24 bulan lalu) supaya engine audit
    berjalan di atas BULAN BERJALAN saja — perilaku identik sheet
    LAPORAN_DEVIASI workbook user (tgl 1..31, tanpa baris negatif).
    Baris tanpa Tanggal valid dibiarkan (dibuang lagi oleh
    build_audit_input dropna)."""
    if df is None or getattr(df, "empty", True) \
            or "Tanggal" not in getattr(df, "columns", []):
        return df
    t = pd.to_numeric(df["Tanggal"], errors="coerce")
    return df[(t >= 1) | t.isna()]


# =============================================================================
# v3.9.30 — PO MENUNGGU DIPROSES (32.43) → PENJELAS DEVIASI MURNI
# (user: "cek Rincian PO file 32.43 — ada nama resto+barang dengan status
# pesanan 'Menunggu diproses'; PO sudah ada tapi penerimaan belum
# di-update di sistem → bisa jadi penyebab deviasi murni")
# =============================================================================

def _po_nomor_str(v) -> str:
    """Nomor PO → string bersih (None/NaN → ''; float integral tanpa
    '.0') — mirror _doc_code_str/rincian _resto_name NA-safety."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def extract_po_pending(po_df: "pd.DataFrame | None") -> pd.DataFrame:
    """v3.9.30 — subset Rincian PO 32.43 ber-Status Pesanan Pembelian
    'Menunggu diproses' (case/whitespace-insensitive).

    Input boleh frame MENTAH (hasil merge build_rincian_po tanpa filter
    KATEGORI) maupun yang sudah terfilter — fungsi idempoten. Kolom
    status hilang / None / kosong → frame kosong (audit tanpa PO)."""
    if po_df is None or getattr(po_df, "empty", True):
        return pd.DataFrame()
    if "Status Pesanan Pembelian" not in getattr(po_df, "columns", []):
        return pd.DataFrame()
    status = po_df["Status Pesanan Pembelian"].fillna("") \
        .astype(str).str.strip().str.lower()
    return po_df[status == PO_STATUS_MENUNGGU].copy()


def _po_menunggu_pairs(po_pending_df: "pd.DataFrame | None",
                      konversi: "dict | None" = None) -> dict:
    """{(resto, barang): [(nomor, qty, satuan_label, unconverted), ...]}
    dari PO menunggu.

    resto = resto_from_cabang_po(Cabang PO '1370.MLGPAR' → 'MLGPAR') —
    join key identik dgn Resto audit; barang di-strip; nomor & qty
    defensif (kolom hilang → ''/0.0); urut per nomor; pasangan tanpa
    resto/barang valid dibuang.

    v3.9.31 — KONVERSI SATUAN: bila ``konversi`` (peta dari
    konversi_satuan.build_konversi_map — 42.05 '#Sat. Kirim'+'Rasio
    Satuan' + 32.24 'Satuan'+'Rasio Satuan') diberikan:
    qty × rasio[(barang, Satuan PO)] → SATUAN TERKECIL (apple-to-apple
    dgn Selisih/Saldo audit — user: "air mineral PO karton, barang
    masuk botol — tidak match waktu cari deviasi murni"); label =
    satuan terkecil barang. Lookup gagal (pasangan (barang, satuan-PO)
    tak terdaftar di 42.05/32.24) → qty AS-IS + label satuan PO +
    penanda unconverted=True (catatan diberi '*'). ``konversi`` None →
    perilaku v3.9.30 persis (qty mentah, tanpa label/penanda).
    """
    out: dict = {}
    if po_pending_df is None or getattr(po_pending_df, "empty", True):
        return out
    cols = set(getattr(po_pending_df, "columns", []))
    if not {"Cabang PO", "Nama Barang"} <= cols:
        return out
    n = len(po_pending_df)
    nomors = (po_pending_df["Nomor #"].tolist() if "Nomor #" in cols
              else [None] * n)
    qtys = (pd.to_numeric(po_pending_df["Kuantitas"], errors="coerce")
            .fillna(0.0).tolist() if "Kuantitas" in cols else [0.0] * n)
    satuans = (po_pending_df["Satuan"].tolist() if "Satuan" in cols
               else [None] * n)
    for cab, brg, nomor, qty, sat in zip(po_pending_df["Cabang PO"],
                                         po_pending_df["Nama Barang"],
                                         nomors, qtys, satuans):
        resto = resto_from_cabang_po(cab)
        b = _po_nomor_str(brg)
        if not resto or not b:
            continue
        qty = float(qty)
        if konversi is None:
            # legacy v3.9.30 — qty mentah, tanpa label/penanda
            out.setdefault((resto, b), []).append(
                (_po_nomor_str(nomor), qty, "", False))
            continue
        rasio, terk = lookup_rasio(konversi, b, sat)
        if rasio is not None and rasio > 0:
            out.setdefault((resto, b), []).append(
                (_po_nomor_str(nomor), qty * float(rasio),
                 str(terk) if terk else "", False))
        else:
            # fallback (disetujui user): qty PO as-is + penanda '*'
            _sat = _po_nomor_str(sat).upper()
            out.setdefault((resto, b), []).append(
                (_po_nomor_str(nomor), qty, _sat, True))
    for lst in out.values():
        lst.sort()
    return out


def _po_menunggu_note(items) -> str:
    """Catatan 'PO Menunggu: PO.xxx (qty 120 BOTOL), PO.yyy (qty 5
    KARTON*) (+2)' — maks 2 nomor dituliskan, sisanya dihitung (pola
    B1/B2 catatan audit view v3.9.23).

    v3.9.31 — qty menyertai LABEL SATUAN hasil konversi (satuan
    terkecil — apple-to-apple dgn Selisih/Saldo audit); '*' = tidak
    terkonversi (pasangan (barang, satuan-PO) tak ada di peta 42.05/
    32.24 — qty tampil dalam satuan PO asli, disetujui user)."""
    shown = []
    for n, q, sat, unconv in items[:2]:
        qtxt = _fmt_qty(q)
        if sat:
            qtxt = f"{qtxt} {sat}"
        if unconv:
            qtxt += "*"
        shown.append(f"{n} (qty {qtxt})" if n else f"(qty {qtxt})")
    extra = len(items) - len(shown)
    txt = ", ".join(shown)
    if extra > 0:
        txt += f" (+{extra})"
    return f"PO Menunggu: {txt}"


def _join_engine_note(existing: str, note: str) -> str:
    """Append catatan app ke catatan engine ('-' dianggap kosong) —
    mirror in_selisih_view._join_notes (VBA tetap PERTAMA, dipisah ' | ')."""
    s = str(existing).strip() if existing is not None else ""
    if s in ("", "-", "nan", "None"):
        return note
    return f"{s} | {note}"


def _apply_po_menunggu(audit: pd.DataFrame, kpi: dict,
                       pairs: dict) -> None:
    """v3.9.30 — perkaya hasil audit dgn info PO Menunggu (mutasi in
    place — frame fresh milik build_audit_from_app):

    - kolom 'Qty PO Menunggu': TOTAL qty PO menunggu pasangan (nilai
      konstanta di SEMUA baris pasangan itu — 0 bila tak ada); sumber
      utk kolom tabel 'PO Menunggu' Rekap Selisih IN + export.
      v3.9.31: nilai TERKONVERSI ke satuan terkecil bila peta konversi
      aktif (disetujui user "tampilkan nilai terkonversi") — baris
      tak terkonversi tampil qty satuan PO asli (penanda '*' di
      catatan).
      v3.9.33 — AUDIT FIX (48-b): pasangan CAMPURAN (sebagian PO
      terkonversi, sebagian fallback satuan PO asli) → kolom menjumlah
      baris TERKONVERSI SAJA (jumlah mentah '120 BOTOL + 3 KARTON =
      123' mencampur dua satuan — bukan angka apple-to-apple dgn
      Selisih/Saldo). Semua-terkonversi / semua-fallback → total
      persis perilaku lama; mix tetap tampil utuh di catatan (qty
      per-PO + penanda '*') dan desc ('N tdk terkonversi').
    - catatan 'PO Menunggu: …' di-append ke 'Detail & Catatan Audit'
      HANYA baris DEVIASI MURNI yang pasangannya punya PO menunggu —
      membedakan deviasi murni EXPLAINABLE (menunggu PO diproses →
      akan resolve saat RI masuk) vs yang perlu audit fisik.
    - KPI 'dev_murni_po': jumlah baris DEVIASI MURNI ber-PO menunggu.
    """
    audit["Qty PO Menunggu"] = 0.0
    kpi["dev_murni_po"] = 0
    if not pairs or audit.empty:
        return
    resto = audit["Resto"].astype(str).str.strip()
    item = audit["Nama Item"].astype(str).str.strip()
    status = audit["Status Analisis Audit"].astype(str)
    detail = audit["Detail & Catatan Audit"].astype(str).tolist()
    # pandas 3 (CoW): to_numpy() tanpa konversi dtype → view READ-ONLY →
    # qty[i] = ... ValueError "assignment destination is read-only"
    # (fresh install requirements pandas>=2.0.0 kini resolve ke 3.x).
    # copy=True aman utk pandas 2 & 3 (kwarg ada sejak lama).
    qty = audit["Qty PO Menunggu"].to_numpy(dtype="float64", copy=True)
    n_flagged = 0
    for i in range(len(audit)):
        items = pairs.get((resto.iat[i], item.iat[i]))
        if not items:
            continue
        # v3.9.33 — AUDIT FIX (48-b): jangan campur satuan di kolom TOTAL.
        # Semua PO satu kondisi (semua terkonversi / semua fallback) →
        # jumlah seluruh baris (perilaku lama). Pasangan CAMPURAN →
        # hanya baris TERKONVERSI (satuan terkecil) yang dijumlahkan
        # supaya tetap apple-to-apple dgn Selisih/Saldo; baris fallback
        # (satuan PO asli) tetap tampil di CATATAN '(qty 3 KARTON*)' +
        # desc 'N tdk terkonversi' — mix tetap transparan.
        _n_unconv = sum(1 for _n, _q, _s, u in items if u)
        if _n_unconv == 0 or _n_unconv == len(items):
            qty[i] = sum(q for _, q, _, _ in items)
        else:
            qty[i] = sum(q for _n, q, _s, u in items if not u)
        if status.iat[i] == ST_DEV_MURNI:
            detail[i] = _join_engine_note(
                detail[i], _po_menunggu_note(items))
            n_flagged += 1
    audit["Qty PO Menunggu"] = qty
    audit["Detail & Catatan Audit"] = detail
    kpi["dev_murni_po"] = n_flagged


def build_audit_from_app(rekap_so_df: Optional[pd.DataFrame],
                         in_detail_df: Optional[pd.DataFrame],
                         po_pending_df: "pd.DataFrame | None" = None,
                         bulan_lalu: bool = True,
                         konversi: "dict | None" = None
                         ) -> tuple[pd.DataFrame, dict, str]:
    """Input dari data app + engine sekali jalan.

    v3.9.27 (user: "pada rekap selisih in bisa mode hitung bulan lalu dan
    hanya hitung bulan ini. Tapi default hitung bulan ini aja") — param
    ``bulan_lalu``:
    - True  : SEMUA data (default pipeline; baris bulan lalu ber-Tanggal
              negatif ikut — saldo kumulatif menyambung dari bulan lalu).
    - False : baris Tanggal negatif DIBUANG sebelum engine → audit murni
              bulan berjalan (1..31) — mirror sheet LAPORAN_DEVIASI
              (output macro VBA user = 2.798 pasangan × 31 hari, tanpa
              tanggal negatif). Pembanding delta SO tanggal 1 jadi SO
              pertama YANG TERSISA di bulan berjalan (baris bulan lalu
              tidak ada).

    v3.9.30 — param ``po_pending_df``: Rincian PO 32.43 (frame mentah
    tanpa filter KATEGORI — difilter status 'Menunggu diproses' internal
    via extract_po_pending; None = pemanggil lama, output tak tersentuh).
    Pasangan (resto dari Cabang PO, barang) ber-PO menunggu → kolom
    'Qty PO Menunggu' + catatan 'PO Menunggu: …' di baris DEVIASI MURNI
    + KPI 'dev_murni_po' (lihat _apply_po_menunggu). PO menunggu adalah
    keadaan TERKINI (bukan transaksi bertanggal) → TIDAK difilter
    varian bulan — kedua varian (Lalu+Ini / Bulan Ini) memakai pasangan
    PO yang sama.

    v3.9.31 — param ``konversi``: peta konversi satuan (append1
    konversi_out['map'] — konversi_satuan.build_konversi_map dari
    42.05+32.24). Qty PO dikonversi ke SATUAN TERKECIL (apple-to-apple
    dgn Selisih/Saldo); catatan berlabel satuan '(qty 120 BOTOL)'; tak
    terkonversi → qty as-is + '*' (disetujui user). None = perilaku
    v3.9.30 persis (qty satuan PO tanpa label).

    Return (audit_df, kpi, source_desc). audit_df kosong + kpi["rows"]=0
    bila tidak ada data rekap SO / IN sama sekali; source_desc menjelaskan
    asal data (untuk status UI).
    """
    if not bulan_lalu:
        rekap_so_df = _filter_bulan_ini(rekap_so_df)
        in_detail_df = _filter_bulan_ini(in_detail_df)
    raw = build_audit_input(rekap_so_df, in_detail_df)
    po_pairs = _po_menunggu_pairs(
        extract_po_pending(po_pending_df), konversi) \
        if po_pending_df is not None else None
    if raw.empty:
        kpi0 = {"rows": 0, "cutoff": 0, "omit": 0, "deviasi_murni": 0,
                "deviasi_qty": 0.0, "ok": 0}
        if po_pairs is not None:
            # skema konsisten walau tanpa data rekap (kolom + kpi PO ada)
            raw["Qty PO Menunggu"] = pd.Series(
                dtype="float64")
            kpi0["dev_murni_po"] = 0
        return raw, kpi0, "tidak ada data rekap SO / IN utk audit"
    audit, kpi = build_audit_rekap(raw)
    if po_pairs is not None:
        _apply_po_menunggu(audit, kpi, po_pairs)
    n_so = int(pd.to_numeric(raw["Hasil SO"], errors="coerce")
               .notna().sum())
    n_in = int((pd.to_numeric(audit["Penerimaan Sistem"], errors="coerce")
                .fillna(0) != 0).sum())
    cakupan = "incl. bulan lalu" if bulan_lalu else "bulan berjalan saja"
    desc = (f"Data app (rekap SO + BM + IN 42.05/32.24/99.01 "
            f"{cakupan}) · "
            f"{len(raw):,} baris · {raw['Resto'].nunique()} resto · "
            f"SO {n_so:,} · IN {n_in:,}")
    if po_pairs:
        _tot_po = sum(q for v in po_pairs.values()
                      for _n, q, _s, _u in v)
        if konversi is not None:
            # v3.9.31 — qty terkonversi satuan terkecil + hitungan
            # baris PO yg tak terkonversi (transparansi fallback)
            _n_unc = sum(1 for v in po_pairs.values()
                         for _n, _q, _s, u in v if u)
            _qty_txt = f"{_fmt_qty(_tot_po)} qty sat. terkecil"
            if _n_unc:
                _qty_txt += f", {_n_unc} tdk terkonversi"
        else:
            _qty_txt = f"{_fmt_qty(_tot_po)} qty"
        desc += (f" · PO menunggu {len(po_pairs)} pasangan "
                 f"({_qty_txt})")
    return audit, kpi, desc
