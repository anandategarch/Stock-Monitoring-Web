"""
rincian_po.py — Mirror persis query #"Rincian PO" di M code.
Rincian Pesanan Pembelian (modul 32.43) → filter KATEGORI = "DEVIASI".

v3.9.30 — param ``semua_out`` (dict opsional): keluaran MERGED TANPA
filter KATEGORI (semua item, semua status) disimpan ke
``semua_out["df"]`` — dipakai pipeline utk audit "PO Menunggu"
(fn_audit.extract_po_pending: status 'Menunggu diproses' per
resto+barang — penjelas deviasi murni; query utama TETAP difilter
DEVIASI persis mirror M supaya tab 🛒 Rincian PO tidak berubah).

v3.9.33 — AUDIT FIX (48-a): merge kategori + filter DEVIASI kini
CASE/WHITESPACE-INSENSITIVE — key join 'Nama Barang' dinormalisasi
(strip + upper) di KEDUA sisi (kolom key temp dibuang setelah merge;
nilai asli tetap utk display) dan perbandingan KATEGORI pakai
strip+upper == 'DEVIASI'. Dulu trailing-space/case drift antara file
PO dan master DBS Kategori menjatuhkan baris PO SENYAP (left-join
no-match → kategori kosong → terfilter).
"""
import pandas as pd

from .helpers import fn_combine_folder, safe_to_numeric, safe_to_str, to_datetime_robust
from .queries import query_dbs_kategori


def build_rincian_po(config, semua_out: dict | None = None) -> pd.DataFrame:
    """
    Mirror M: shared #"Rincian PO".

    Output columns: Nomor #, Tanggal, Cabang PO, Pemasok, Nama Barang, Satuan,
    Kuantitas, @Harga, Total Harga, Keterangan PO, Status Pesanan Pembelian,
    Tgl/Jam Pembuatan, DBS_Kategori.KATEGORI
    (filtered: DBS_Kategori.KATEGORI = "DEVIASI")

    v3.9.30 ``semua_out``: bila dict diberikan, frame merged SEBELUM
    filter DEVIASI (semua barang — termasuk non-DEVIASI-master) ikut
    disimpan ke ``semua_out["df"]``. PO barang non-DEVIASI tidak
    terbaca query utama; audit PO Menunggu perlu SEMUA pasangan.
    Return value TIDAK berubah (tetap terfilter DEVIASI).
    """
    # Source = fnCombineFolder(RincianPO, PesananPO, false) + Skip(3) + Skip(1) + Promote
    # = pandas header=4
    sheet_name = config.sheet("PesananPO")
    prom = fn_combine_folder(config.folder("RincianPO"), sheet_name, header_row=4)
    if prom.empty:
        # v3.9.30 — semua_out tetap terisi (frame kosong) supaya audit
        # PO Menunggu punya skema konsisten walau folder kosong
        if semua_out is not None:
            semua_out["df"] = pd.DataFrame()
        return pd.DataFrame(columns=[
            "Nomor #", "Tanggal", "Cabang PO", "Pemasok", "Nama Barang",
            "Satuan", "Kuantitas", "@Harga", "Total Harga", "Keterangan PO",
            "Status Pesanan Pembelian", "Tgl/Jam Pembuatan", "DBS_Kategori.KATEGORI"
        ])

    # Selected = Table.SelectColumns(Promote, {...}, MissingField.Ignore)
    needed = [
        "Nomor #", "Tanggal", "Cabang PO", "Pemasok", "Nama Barang",
        "Satuan", "Kuantitas", "@Harga", "Total Harga", "Keterangan PO",
        "Status Pesanan Pembelian", "Tgl/Jam Pembuatan"
    ]
    available = [c for c in needed if c in prom.columns]
    sel = prom[available].copy()

    # Typed
    text_cols = ["Nomor #", "Cabang PO", "Pemasok", "Nama Barang", "Satuan",
                 "Keterangan PO", "Status Pesanan Pembelian"]
    num_cols = ["Kuantitas", "@Harga", "Total Harga"]
    date_cols = ["Tanggal"]
    datetime_cols = ["Tgl/Jam Pembuatan"]

    for col in text_cols:
        if col in sel.columns:
            sel[col] = safe_to_str(sel[col])
    for col in num_cols:
        if col in sel.columns:
            sel[col] = safe_to_numeric(sel[col])
    for col in date_cols:
        if col in sel.columns:
            # v3.9.28: to_datetime_robust — .xlsb/pyxlsb memberi serial mentah
            sel[col] = to_datetime_robust(sel[col])
    for col in datetime_cols:
        if col in sel.columns:
            sel[col] = to_datetime_robust(sel[col])

    # BufferedKategori + Merged (LeftOuter on Nama Barang = NAMA BARANG)
    dbs_kategori = query_dbs_kategori(config)
    if len(dbs_kategori) > 0 and "Nama Barang" in sel.columns:
        kat = dbs_kategori[["NAMA BARANG", "KATEGORI"]].copy()
        kat = kat.rename(columns={"NAMA BARANG": "Nama Barang", "KATEGORI": "DBS_Kategori.KATEGORI"})
        sel["Nama Barang"] = sel["Nama Barang"].astype(str)
        kat["Nama Barang"] = kat["Nama Barang"].astype(str)
        # v3.9.33 — AUDIT FIX (48-a): join pada key TER-NORMALISASI
        # (strip + upper) — "Air Mineral " vs "AIR MINERAL" kini nyambung.
        # Nilai kolom asli dipertahankan utk display; duplikat key hasil
        # normalisasi di master dibuang (kardinalitas left-join tetap
        # 1:1 — mirror dedup fn_dbs_kategori, cegah multiplikasi baris);
        # kolom key temp dibuang setelah merge.
        _KEY = "__key_nama_barang__"
        sel[_KEY] = sel["Nama Barang"].str.strip().str.upper()
        kat[_KEY] = kat["Nama Barang"].str.strip().str.upper()
        kat = kat.drop_duplicates(subset=[_KEY], keep="first")
        merged = sel.merge(
            kat.drop(columns=["Nama Barang"]), on=_KEY, how="left")
        merged = merged.drop(columns=[_KEY])
    else:
        merged = sel.copy()
        merged["DBS_Kategori.KATEGORI"] = None

    # v3.9.30 — salinan TANPA filter utk audit PO Menunggu (semua
    # barang; filter DEVIASI query utama memotong barang non-DEVIASI
    # yang PO-nya justru bisa menunggu diproses)
    if semua_out is not None:
        semua_out["df"] = merged

    # Filtered = Table.SelectRows(Expanded, each [DBS_Kategori.KATEGORI] = "DEVIASI")
    if "DBS_Kategori.KATEGORI" in merged.columns:
        # v3.9.33 — AUDIT FIX (48-a): bandingkan normalisasi strip+upper —
        # "DEVIASI " / "deviasi" dulu gagal match (baris hilang senyap);
        # NaN/None tetap tidak lolos (mirror perilaku lama).
        _kat_norm = (merged["DBS_Kategori.KATEGORI"].astype(str)
                     .str.strip().str.upper())
        filtered = merged[_kat_norm == "DEVIASI"].reset_index(drop=True)
    else:
        filtered = merged.iloc[0:0].copy()

    return filtered
