"""
append1.py — Mirror SANGAT PERSIS query Append1 di M code.
Pipeline utama yang menggabungkan semua sumber data, melakukan pivot, running stock,
deviasi, merge kategori, dan unpivot ke format long.

Output: DataFrame long format dengan kolom:
  Nama Barang, NAMA RESTO, Tanggal, JENIS, NILAI, Nomor, Nomor PO,
  #Tgl/Jam Pembuatan IT, KATEGORI, SOURCE KIRIMAN (+ SOURCE DATA v3.9.19)

v3.9.21: LANGKAH 9 SOURCE DATA kini PER-(pasangan × Tanggal) atas baris
rekap ber-NILAI non-nol (fix user "Promix 04 muncul di filter tapi data
tidak ada"): tanggal sama ada 'input so harian' + promix → harian menang
(hitungan manual > turunan sistem); hanya promix non-nol → sumber promix;
baris template bernilai 0/NaN & sumber whitespace-only tidak menentukan.
Sumber menempel pada baris final per (pasangan, Tanggal) — deviasi_view
membaca sumber baris 1.SO tanggal H. Deterministik (mergesort, kunci
eksplisit); menggantikan resolusi pair-level "tanggal tertinggi" yang
rapuh (v3.9.19 melabel semua pasangan campuran Promix krn tie urutan
baris; v3.9.20 swing kebalikannya — tak pernah Promix).

v3.9.20 (deep audit 34-d/fix 35-d): LANGKAH 9 tie-break deterministik +
na_position="first" (NA-Tanggal tak pernah menang) + SOURCE DATA
di-strip (NA-safe, tanpa lower-case).
"""
import numpy as np
import pandas as pd

from .fn_running_stock import fn_running_stock_grouped

# v3.9.44 — mask baris tanpa kategori master (jejak saldo-only; lihat
# widgets.kategori_blank_mask utk konsumen view).
from .helpers import kategori_blank_mask
from .konversi_satuan import build_konversi_map
from .queries import (
    query_4217,
    query_barang_keluar,
    query_dbs_kategori,
    query_full_rekap_mentah_so,
    query_in,
    query_out,
)


def _value_to_text(val) -> str:
    """Mirror M: Text.From(_) — convert value to text.
    FIX BUG-21: float 0.0 → "0" (bukan "0.0") agar filter != "0" bekerja.
    Untuk datetime: format "DD/MM/YYYY HH:MM:SS".
    """
    if val is None:
        return None
    # Check for pandas/numpy NaN
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    # datetime → "DD/MM/YYYY HH:MM:SS"
    if isinstance(val, pd.Timestamp):
        return val.strftime("%d/%m/%Y %H:%M:%S")
    if hasattr(val, "strftime"):  # datetime object
        return val.strftime("%d/%m/%Y %H:%M:%S")
    # FIX: float yang whole number → format sebagai integer (mirror M Text.From)
    # M: Text.From(0.0) = "0", Text.From(1.0) = "1"
    if isinstance(val, (int, np.integer)):
        return str(val)
    if isinstance(val, (float, np.floating)):
        if val == int(val):
            return str(int(val))
        return str(val)
    return str(val).strip()


def _value_to_text_series(series: pd.Series) -> pd.Series:
    """Vectorized version of _value_to_text untuk pandas Series.
    OPTIMIZED: dtype-specific fast paths, no .apply().
    """
    # Fast path: datetime dtype
    if pd.api.types.is_datetime64_any_dtype(series):
        result = series.dt.strftime("%d/%m/%Y %H:%M:%S")
        return result.where(series.notna(), other=None)
    # Fast path: numeric dtype
    if pd.api.types.is_numeric_dtype(series):
        # Whole numbers → int string, others → float string
        is_nan = series.isna()
        # Use modulo to check integer-valued floats (avoid astype crash)
        is_int = ~is_nan & (series % 1 == 0)
        result = pd.Series(None, index=series.index, dtype=object)
        int_vals = series[is_int].astype('Int64').astype(str)
        result[is_int] = int_vals
        float_vals = series[~is_nan & ~is_int].astype(str)
        result[~is_nan & ~is_int] = float_vals
        return result
    # Object/mixed dtype: convert to str, preserve None
    is_null = series.isna()
    result = series.astype(str).where(~is_null, other=None)
    # Strip whitespace
    result = result.str.strip() if hasattr(result, 'str') else result
    return result


def _concat_valid_values(series: pd.Series) -> str:
    """
    Mirror M: untuk setiap InfoColumn di InformationGrouped.
    - Transform: null → null, else Text.Trim(Text.From(_))
    - Filter: not null, not "", not "0"
    - Distinct (preserve order)
    - Text.Combine dengan ", "

    OPTIMIZED: pre-convert series, avoid .apply() for common types.
    """
    # Fast path: if series is datetime dtype, use vectorized strftime
    if pd.api.types.is_datetime64_any_dtype(series):
        values = series.dt.strftime("%d/%m/%Y %H:%M:%S")
        values = values.where(series.notna(), other=None)
    elif pd.api.types.is_numeric_dtype(series):
        # Convert numeric to text (whole numbers as int, others as float)
        def _num_to_text(v):
            if pd.isna(v):
                return None
            if v == int(v):
                return str(int(v))
            return str(v)
        values = series.apply(_num_to_text)
    else:
        # Mixed/object dtype — use _value_to_text
        values = series.apply(_value_to_text)

    # Filter valid: not null, not "", not "0"
    mask = values.notna() & (values != "") & (values != "0")
    valid = values[mask]
    # Distinct (preserve order of first appearance)
    distinct = list(dict.fromkeys(valid.tolist()))
    # Join
    return ", ".join(distinct) if distinct else None


def _group_info_columns(info_prep: pd.DataFrame, key_columns: list,
                        info_columns: list) -> pd.DataFrame:
    """
    v3.7 ENGINE TURBO — pengganti groupby.agg(_smart_join) per grup.

    Cara lama: UDF Python dipanggil 160 rb kali (per grup × kolom) —
    6,7s di real-data. Cara baru: per kolom, drop baris kosong →
    konversi str vektor → drop_duplicates (key+nilai) →
    groupby().agg(', '.join) level C — 0,05s (≈130×).

    Paritas penuh dengan _smart_join lama (diverifikasi 8 edge-case
    sintetis + real-data 0/80.069 grup beda pada kedua kolom info):
    - nilai None/NaN dibuang (mirror dropna; "" dan "0" TIDAK difilter
      di sini — pre-convert di caller yang memfilternya, sama seperti
      alur lama);
    - nilai dikonversi str per-elemen-equivalen (astype(str) setelah
      dropna — mirror str(v));
    - distinct mempertahankan urutan kemunculan pertama;
    - gabung dengan ", ";
    - grup tanpa nilai valid → None (bukan NaN).
    Urutan baris hasil tidak di-sort (lama: groupby sort=True) — tidak
    berpengaruh karena hasilnya hanya dipakai untuk left-merge.
    """
    base = info_prep[key_columns].drop_duplicates(keep="first") \
        .reset_index(drop=True)
    result = base
    for col in info_columns:
        if col not in info_prep.columns:
            continue
        sub = info_prep[key_columns + [col]].dropna(subset=[col])
        if sub.empty:
            result[col] = None
            continue
        # mirror str(v) per elemen (None/NaN sudah dibuang) — vektor
        sub = sub.copy()
        sub[col] = sub[col].astype(str)
        sub = sub.drop_duplicates(subset=key_columns + [col], keep="first")
        g = sub.groupby(key_columns, dropna=False, sort=False)[col] \
            .agg(", ".join).reset_index()
        # Normalisasi dtype key: grup dengan key semua-None menghasilkan
        # kolom float64 di index groupby → samakan dengan dtype base
        # (null None/NaN/pd.NA tetap match saat merge)
        for c in key_columns:
            if c in g.columns and g[c].dtype != result[c].dtype:
                try:
                    g[c] = g[c].astype(result[c].dtype)
                except (ValueError, TypeError):
                    result[c] = result[c].astype(g[c].dtype)
        result = result.merge(g, on=key_columns, how="left")
    # samakan representasi kosong dengan UDF lama: None (bukan NaN)
    for col in info_columns:
        if col in result.columns:
            result[col] = result[col].astype(object) \
                .where(result[col].notna(), None)
    return result


# Tag SOURCE IN yang tergolong kiriman INTERNAL (pemindahan antar-gudang /
# cabang sendiri — modul 42.05). Semua tag lain (32.24, 32.24 Bulan Lalu,
# 99.01) = kiriman EKSTERNAL (penerimaan supplier / pembelian tanpa
# penerimaan). V3.9.29 — dasar klasifikasi SOURCE KIRIMAN per pasangan.
_INTERNAL_IN_TAGS = ("42.05", "42.05 (Bulan Lalu)")


def _source_kiriman_per_pair(in_df: "pd.DataFrame | None") -> pd.DataFrame:
    """v3.9.29 — klasifikasi SOURCE KIRIMAN per pasangan (Nama Barang ×
    NAMA RESTO) dari SUMBER IN aktual (konfirmasi user):
      - hanya dokumen 42.05 / 42.05 (Bulan Lalu)      → "Internal"
      - hanya 32.24 / 32.24 (Bulan Lalu) / 99.01      → "Eksternal"
      - campuran keduanya                              → "Campuran"
      - pasangan TANPA dokumen IN                      → tidak mengeluarkan
        baris (merge left → None = kosong, mirror kolom Z 'Kiriman' sheet
        'Data Base Cek Deviasi' yang kosong utk pasangan tanpa kiriman).

    Input: in_df = gabungan sumber IN hasil query_in (SEMUA baris kini
    bertag 'SOURCE IN', v3.9.29). Pre-KATEGORI-filter — identik dgn
    in_detail (klasifikasi mengikuti sumber dokumen apa adanya).
    """
    empty = pd.DataFrame(columns=["Nama Barang", "NAMA RESTO",
                                   "SOURCE KIRIMAN"])
    cols = ("Nama Barang", "NAMA RESTO", "SOURCE IN")
    if in_df is None or in_df.empty or any(c not in in_df.columns for c in cols):
        return empty
    d = in_df[list(cols)].copy()
    d["SOURCE IN"] = d["SOURCE IN"].fillna("").astype(str).str.strip()
    d["_int"] = d["SOURCE IN"].isin(_INTERNAL_IN_TAGS)
    g = d.groupby(["Nama Barang", "NAMA RESTO"], dropna=False, sort=False)["_int"] \
        .agg(has_int="any",
             has_eks=lambda s: bool((~s).any())).reset_index()

    def _cls(row) -> str:
        if row["has_int"] and row["has_eks"]:
            return "Campuran"
        if row["has_int"]:
            return "Internal"
        return "Eksternal"

    g["SOURCE KIRIMAN"] = g.apply(_cls, axis=1)
    return g[["Nama Barang", "NAMA RESTO", "SOURCE KIRIMAN"]]


def _collect_protected_barangs(dfs: list) -> set:
    """v3.9.39 — nama barang ternormalisasi dari SEMUA sumber transaksi
    (Full Rekap Mentah SO, OUT 22.05, BARANG KELUAR 42.15, IN).

    Dipakai query_4217 → fn_4217 'protected_barangs': barang yang
    ber-pasangan di sumber lain SELALU lolos whitelist kategori 42.17
    (LOOKUP DUA ARAH — saldo awal tidak boleh hilang, else pasangan itu
    kehilangan Sistem / barang "tidak muncul di Deviasi GR").

    Normalisasi = buang SEMUA whitespace + upper (mirror _norm_barang
    fn_4217): 'BUMBU PASTA KUAH (V.20)' == 'bumbu  pasta kuah (V.20)'.
    """
    prot: set = set()
    for df in dfs:
        if df is None or getattr(df, "empty", True):
            continue
        if "Nama Barang" not in getattr(df, "columns", []):
            continue
        vals = df["Nama Barang"].dropna().astype(str)
        for v in vals.unique():
            v_norm = "".join(str(v).strip().upper().split())
            if v_norm:
                prot.add(v_norm)
    return prot


def build_append1(config, stop_event=None, in_detail_out: dict | None = None,
                 rekap_so_out: dict | None = None,
                 konversi_out: dict | None = None) -> pd.DataFrame:
    """
    Mirror M: shared Append1.
    Pipeline lengkap dari source data sampai output long format.

    (v3.5: LightMode DIHAPUS — pipeline selalu FULL: InfoColumns diproses,
    semua KATEGORI lolos, bulan lalu selalu dibaca.)

    v3.4 — in_detail_out: dict opsional; diisi DataFrame detail IN per
    dokumen (lihat query_in).
    v3.6 — rekap_so_out: dict opsional; diisi rekap mentah long
    (JENIS 'SO' / 'BARANG MASUK', Tanggal -25..-31 + 1..31) — input
    Audit Rekonsiliasi dari data app (fn_audit.build_audit_input).
    v3.9.31 — konversi_out: dict opsional; diisi peta konversi satuan
    {(barang, satuan): rasio} + {barang: terkecil} dari baris IN
    (kolom SATUAN DOK / RASIO SATUAN / SATUAN TERKECIL fn_4205+fn_3224;
    konversi_satuan.build_konversi_map) — dipakai fn_audit utk
    konversi qty PO 32.43 (satuan PO karton) ke satuan terkecil
    (user: "air mineral di rincian po pakai karton, sheet barang masuk
    botol — tidak match waktu cari deviasi murni").

    stop_event: threading.Event — jika set, raise PipelineStopped di checkpoint.
    """
    print("  [Append1] Mode: FULL (LightMode dihapus v3.5)")
    print("  [Append1] Loading master data...")
    # Pre-load master queries (dipakai multiple times)
    # FIX: query_27_konversi_satuan dihapus — PI sudah digantikan 9901, konversi gak dipakai lagi
    dbs_kategori = query_dbs_kategori(config)
    print(f"    DBS Kategori: {len(dbs_kategori)} rows")

    # =========================================================================
    # 1. SOURCE — Table.Combine({4217, Full Rekap Mentah SO, OUT, BARANG KELUAR, IN})
    # =========================================================================
    print("  [Append1] Loading transaction data...")
    # v3.9.39 — REORDER + LOOKUP DUA ARAH (user: "look up nama barang harus
    # dua arah ... Rekap Mentah ↔ 42.17"): sumber TRANSAKSI dibaca DULU,
    # lalu nama barangnya jadi protected set → query_4217 memakainya agar
    # whitelist kategori TIDAK PERNAH memutus pasangan barang yang
    # ber-transaksi (dulu: barang di luar whitelist terbuang senyap dari
    # 42.17 → saldo awal hilang → Sistem salah / barang "tidak muncul";
    # urutan M code asli {4217, ...} tidak mengubah hasil gabungan).
    full_rekap_so = query_full_rekap_mentah_so(config)
    print(f"    Full Rekap Mentah SO: {len(full_rekap_so)} rows")
    if rekap_so_out is not None:
        rekap_so_out["df"] = full_rekap_so

    out_df = query_out(config)
    print(f"    OUT (22.05 sales): {len(out_df)} rows")

    keluar_df = query_barang_keluar(config)
    print(f"    BARANG KELUAR (42.15 Kirim): {len(keluar_df)} rows")

    in_df = query_in(config, detail_out=in_detail_out)
    print(f"    IN: {len(in_df)} rows")
    if in_detail_out is not None:
        print(f"    IN detail (per dokumen, v3.4): {len(in_detail_out.get('df'))} rows")

    _protected_barangs = _collect_protected_barangs(
        [full_rekap_so, out_df, keluar_df, in_df])
    print(f"    4217 dua arah: {len(_protected_barangs):,} nama barang "
          "ber-pasangan (rekap/IN/out/BK) → dilindungi dari whitelist")

    q4217 = query_4217(config, protected_barangs=_protected_barangs)
    if not q4217.empty:
        _n_resto = q4217["NAMA RESTO"].nunique()
        _n_barang = q4217["Nama Barang"].nunique()
        print(f"    4217 (Saldo Awal): {len(q4217)} rows "
              f"({_n_barang} barang · {_n_resto} resto)")
    else:
        print(f"    4217 (Saldo Awal): {len(q4217)} rows")

    # FIX: Stop checkpoint after 4217 load
    if stop_event is not None and stop_event.is_set():
        from src.main import PipelineStopped
        raise PipelineStopped("Dihentikan setelah load 4217")

    # v3.9.31 — peta konversi satuan dari baris IN (42.05 + 32.24;
    # dipakai fn_audit utk konversi qty PO Menunggu → satuan terkecil).
    # Dibangun SEKALI dari data transaksi aktual — tanpa file master
    # excel tambahan (selalu segar; berjalan + bulan lalu ikut supaya
    # coverage (barang, satuan) maksimal).
    if konversi_out is not None:
        konversi_out["map"] = build_konversi_map(in_df)
        _km = konversi_out["map"]
        _km_log = (f"Konversi satuan (v3.9.31): {_km['n_rasio']:,} rasio / "
                   f"{_km['n_barang']:,} barang")
        if _km["n_conflict"]:
            _km_log += (f" — {_km['n_conflict']:,} konflik rasio "
                        "(nilai pertama dipakai)")
        print(f"    {_km_log}")
    # v3.9.29 — peta klasifikasi SOURCE KIRIMAN per pasangan (dipakai
    # LANGKAH 5b; mengganti nilai master DBS Kategori)
    _src_kiriman = _source_kiriman_per_pair(in_df)
    if not _src_kiriman.empty:
        _n_int = int((_src_kiriman["SOURCE KIRIMAN"] == "Internal").sum())
        _n_eks = int((_src_kiriman["SOURCE KIRIMAN"] == "Eksternal").sum())
        _n_mix = int((_src_kiriman["SOURCE KIRIMAN"] == "Campuran").sum())
        print(f"    SOURCE KIRIMAN per pasangan: {_n_int} Internal / "
              f"{_n_eks} Eksternal / {_n_mix} Campuran")

    # FIX: Stop checkpoint after IN load
    if stop_event is not None and stop_event.is_set():
        from src.main import PipelineStopped
        raise PipelineStopped("Dihentikan setelah load IN")

    # Combine all 5 sources
    parts = []
    for df in [q4217, full_rekap_so, out_df, keluar_df, in_df]:
        if not df.empty:
            parts.append(df)

    if not parts:
        print("  [Append1] WARNING: No source data found!")
        return pd.DataFrame(columns=[
            "Nama Barang", "NAMA RESTO", "Tanggal", "JENIS", "NILAI",
            "Nomor", "Nomor PO", "#Tgl/Jam Pembuatan IT", "KATEGORI", "SOURCE KIRIMAN"
        ])

    # Table.Buffer equivalent — just use the DataFrame (already in memory)
    source = pd.concat(parts, ignore_index=True, sort=False)
    print(f"    Combined source: {len(source)} rows")

    # =========================================================================
    # 2. KONFIGURASI
    # =========================================================================
    InfoColumns = ["Nomor", "Nomor PO", "#Tgl/Jam Pembuatan IT"]
    KeyColumns = ["Nama Barang", "NAMA RESTO", "Tanggal"]
    # FIX: jangan skip InfoColumns (Nomor/Nomor PO perlu terisi)
    # LightMode tetap proses InfoColumns untuk popup details
    AvailableInfoColumns = [c for c in InfoColumns if c in source.columns]


    # =========================================================================
    # 3. INFORMATION — group by KeyColumns, concat valid values for InfoColumns
    # =========================================================================
    print("  [Append1] Building information (grouped)...")
    info_cols = KeyColumns + AvailableInfoColumns
    info_available = [c for c in info_cols if c in source.columns]
    information = source[info_available].copy()

    if AvailableInfoColumns and len(information) > 0:
        # v3.7 ENGINE TURBO: pre-convert kolom info → teks + filter nilai
        # invalid, lalu agregasi via _group_info_columns (vektor, ≈130×
        # lebih cepat dari UDF per-grup; output terverifikasi identik).
        info_prep = information.copy()

        # Pre-process each InfoColumn: convert to text, replace invalid values with None
        for col in AvailableInfoColumns:
            if col in info_prep.columns:
                info_prep[col] = _value_to_text_series(info_prep[col])
                # Set invalid values (None, "", "0", "0.0") to None
                mask_valid = info_prep[col].notna() & (info_prep[col] != "") & (info_prep[col] != "0")
                info_prep[col] = info_prep[col].where(mask_valid, other=None)

        information_grouped = _group_info_columns(
            info_prep, KeyColumns, AvailableInfoColumns)
    else:
        information_grouped = information[KeyColumns].drop_duplicates().reset_index(drop=True) if KeyColumns else information.copy()

    # =========================================================================
    # 4. PERHITUNGAN — pivot, replace null→0, group+fnRunningStock, deviasi, selisih, rename
    # =========================================================================
    print("  [Append1] Pivot + running stock + calculations...")
    calc_columns = KeyColumns + ["JENIS", "Value"]
    calc_available = [c for c in calc_columns if c in source.columns]
    calculation_source = source[calc_available].copy()
    # FIX R5 (audit 37-a): filter rekap fn_rekap_mentah CASE-INSENSITIVE
    # ('so' lolos) tapi rename/pivot append1 EXACT-CASE — JENIS case-
    # variant ('So') hilang SENYAP dari output (SO pasangan lenyap).
    # Normalisasi: JENIS di-strip + di-upper supaya konsisten dgn filter
    # rekap (probe: rekap 'So' → dulu 1.SO = 0, kini nilai utuh).
    if "JENIS" in calculation_source.columns:
        calculation_source["JENIS"] = (
            calculation_source["JENIS"].astype(str).str.strip().str.upper())

    # pivoted = Table.Pivot(CalculationSource, distinct JENIS, "JENIS", "Value", List.Sum)
    if len(calculation_source) > 0 and "JENIS" in calculation_source.columns:
        # Ensure Value is numeric
        calculation_source["Value"] = pd.to_numeric(calculation_source["Value"], errors="coerce").fillna(0)

        # Pivot: group by KeyColumns, columns = JENIS, values = sum(Value)
        # FIX B1 (audit 37-a): pivot_table(dropna=False) MENGHITUNG ULANG
        # kombinasi KARTESIAN level index (pasangan × tanggal yang TIDAK
        # pernah ada di data — pandas me-reindex ke produk level; terbukti
        # probe: 3 kombinasi teramati → 8 baris) → baris FANTOM dgn
        # SO=0/SALDO ter-ffill → 3.DEVIASI = −SALDO muncul di tanggal
        # tanpa data. M `Table.Pivot` hanya memutarkan KOMBINASI TERAMATI.
        # Pengganti: groupby-sum (dropna=False — kunci NA-resto tetap
        # dipertahankan, mirror M) + pivot ulang kolom JENIS — kombinasi
        # index tetap TERAMATI, sel JENIS kosong → NaN (nol-kan oleh
        # ReplaceValue step di bawah, persis perilaku M).
        _grouped = calculation_source.groupby(
            KeyColumns + ["JENIS"], as_index=False, dropna=False,
            sort=False)["Value"].sum()
        pivoted = _grouped.pivot(
            index=KeyColumns, columns="JENIS", values="Value"
        ).reset_index()
        # Flatten column index (pivot creates MultiIndex column name)
        pivoted.columns.name = None
    else:
        pivoted = pd.DataFrame(columns=KeyColumns)

    # ReplaceColumns = {"SALDO AWAL", "SO", "BARANG MASUK", "OUT", "IN", "BARANG KELUAR"}
    # AvailableReplaceColumns = intersection with pivoted columns
    # FIX: include BARANG KELUAR (was missing after OUT/BK split)
    replace_columns = ["SALDO AWAL", "SO", "BARANG MASUK", "OUT", "IN", "BARANG KELUAR"]
    available_replace = [c for c in replace_columns if c in pivoted.columns]

    # replaced = Table.ReplaceValue(pivoted, null, 0, ..., AvailableReplaceColumns)
    for col in available_replace:
        pivoted[col] = pivoted[col].fillna(0)

    # grouped = Table.Group(replaced, {Nama Barang, NAMA RESTO}, fnRunningStock)
    # OPTIMIZED: pakai fn_running_stock_grouped (pre-sort + groupby C-level)
    group_keys = ["Nama Barang", "NAMA RESTO"]
    available_group_keys = [c for c in group_keys if c in pivoted.columns]

    if len(pivoted) > 0 and len(available_group_keys) == 2:
        # Use optimized grouped version (pre-sort once, iterate at C-level)
        combined = fn_running_stock_grouped(pivoted, available_group_keys)
    else:
        combined = pivoted.copy()
        if "SALDO AKHIR" not in combined.columns:
            combined["SALDO AKHIR"] = 0.0

    # typed = SALDO AKHIR → number
    if "SALDO AKHIR" in combined.columns:
        combined["SALDO AKHIR"] = pd.to_numeric(combined["SALDO AKHIR"], errors="coerce").fillna(0)

    # deviasi = SO - SALDO AKHIR (try [SO] otherwise 0)
    so_vals = combined["SO"] if "SO" in combined.columns else pd.Series(0, index=combined.index)
    saldo_akhir_vals = combined["SALDO AKHIR"] if "SALDO AKHIR" in combined.columns else pd.Series(0, index=combined.index)
    combined["DEVIASI"] = so_vals.fillna(0) - saldo_akhir_vals.fillna(0)

    # noNull = filter Nama Barang not null
    if "Nama Barang" in combined.columns:
        combined = combined[combined["Nama Barang"].notna()].reset_index(drop=True)

    # selisih = BARANG MASUK - IN (try [BARANG MASUK] otherwise 0 - try [IN] otherwise 0)
    bm_vals = combined["BARANG MASUK"] if "BARANG MASUK" in combined.columns else pd.Series(0, index=combined.index)
    in_vals = combined["IN"] if "IN" in combined.columns else pd.Series(0, index=combined.index)
    combined["Selisih IN"] = bm_vals.fillna(0) - in_vals.fillna(0)

    # renamed — beri prefix nomor (NEW numbering scheme after OUT/BK split)
    #   7.Selisih IN (was 6.Selisih IN)
    #   8.BARANG KELUAR (NEW — was not in rename_map before)
    #   9.ACR (was 9.OUT / 7.OUT — istilah user v3.9.19: "Ganti istilah 9.OUT menjadi 9.ACR")
    rename_map = {
        "SALDO AKHIR": "2.SALDO AKHIR",
        "SO": "1.SO",
        "DEVIASI": "3.DEVIASI",
        "IN": "4.IN",
        "BARANG MASUK": "5.BARANG MASUK",
        "Selisih IN": "7.Selisih IN",
        "BARANG KELUAR": "8.BARANG KELUAR",
        "OUT": "9.ACR",
    }
    # Only rename columns that exist
    valid_rename = {old: new for old, new in rename_map.items() if old in combined.columns}
    renamed = combined.rename(columns=valid_rename)

    # =========================================================================
    # 5. MERGE INFORMATION + KATEGORI
    # =========================================================================
    print("  [Append1] Merging information + kategori...")
    # MergedInformation = LeftOuter join renamed × InformationGrouped on KeyColumns
    if AvailableInfoColumns and len(information_grouped) > 0:
        # Ensure KeyColumns exist in both
        merge_keys = [c for c in KeyColumns if c in renamed.columns and c in information_grouped.columns]
        if merge_keys:
            # Drop InfoColumns from renamed that will come from InformationGrouped (to avoid suffix)
            info_cols_to_drop = [c for c in AvailableInfoColumns if c in renamed.columns]
            renamed_clean = renamed.drop(columns=info_cols_to_drop, errors="ignore")
            expanded_information = renamed_clean.merge(
                information_grouped, on=merge_keys, how="left"
            )
        else:
            expanded_information = renamed.copy()
            for col in AvailableInfoColumns:
                expanded_information[col] = None
    else:
        expanded_information = renamed.copy()

    # mergedKategori = LeftOuter join × DBS_Kategori on Nama Barang = NAMA BARANG
    # FIX: also bring AKTIF/NON column (was missing → AKTIF/NON always empty in UI)
    # v3.9.29: kolom SOURCE KIRIMAN TIDAK diambil dari master lagi — nilainya
    # kini DITURUNKAN per pasangan dari SUMBER IN aktual (LANGKAH 5b di
    # bawah; konfirmasi user: "nama barang + resto yang berasal dari 42.05
    # harusnya kategori internal, dari 32.24 eksternal dan 9901 juga
    # eksternal — mengganti nilai source kiriman"). Master DBS Kategori
    # tetap menyuplai KATEGORI + AKTIF/NON (per Nama Barang).
    if len(dbs_kategori) > 0 and "Nama Barang" in expanded_information.columns:
        # Prepare DBS_Kategori for merge — include AKTIF/NON if present
        kat_cols = ["NAMA BARANG", "KATEGORI"]
        if "AKTIF/NON" in dbs_kategori.columns:
            kat_cols.append("AKTIF/NON")
        kat = dbs_kategori[kat_cols].copy()
        kat = kat.rename(columns={"NAMA BARANG": "Nama Barang"})
        # Ensure Nama Barang is string for merge
        expanded_information["Nama Barang"] = expanded_information["Nama Barang"].astype(str)
        kat["Nama Barang"] = kat["Nama Barang"].astype(str)
        # v3.9.33 — AUDIT FIX (48-a): join pada key TER-NORMALISASI
        # (strip + upper) — trailing-space/case drift antara file data
        # dan master DBS Kategori dulu menjatuhkan KATEGORI SENYAP
        # (left-join no-match). Nilai kolom asli tetap utk display;
        # duplikat key hasil normalisasi di master dibuang supaya
        # kardinalitas left-join tetap 1:1 (tanpa multiplikasi baris);
        # kolom key temp dibuang setelah merge (schema tak berubah).
        _KEY = "__key_nama_barang__"
        expanded_information[_KEY] = (
            expanded_information["Nama Barang"].str.strip().str.upper())
        kat[_KEY] = kat["Nama Barang"].str.strip().str.upper()
        kat = kat.drop_duplicates(subset=[_KEY], keep="first")
        expanded_kategori = expanded_information.merge(
            kat.drop(columns=["Nama Barang"]), on=_KEY, how="left")
        expanded_kategori = expanded_kategori.drop(columns=[_KEY])
    else:
        expanded_kategori = expanded_information.copy()
        expanded_kategori["KATEGORI"] = None
        expanded_kategori["AKTIF/NON"] = None

    # =========================================================================
    # 5c. KATEGORI REKAP MENTAH — PRIORITAS ATAS MASTER (v3.9.49)
    # =========================================================================
    # user: "Saat ini look up nama barang ambil dari dbs kategori ya?
    # sebenernya sudah ada KATEGORI dari file Rekap Mentah folder Deviasi
    # Weekly jadi bisa ambil kategori dari situ jadi secara default di
    # semua tab kategori sudah pilih: COM DEVIASI - RESTO dan Biaya
    # Packaging - RESTO" (+ "BUMBU PASTA KUAH MLGPAR INI kenapa masih
    # tidak ada ya?" — item tak terdaftar master → kategori kosong →
    # kelas bug 100383). Kolom KATEGORI rekap SO (fn_rekap_mentah v3.9.49
    # → query_full_rekap_mentah_so) kini MENIMPA nilai master utk barang
    # yang punya baris rekap: lookup per Nama Barang pada key
    # TER-NORMALISASI (strip + upper — pola _KEY master LANGKAH 5 di
    # atas). Barang tanpa baris rekap (IN-only / saldo-only) TETAP
    # memakai kategori master; AKTIF/NON tetap murni master.
    # v3.9.50 — [audit 3-b] 3 penguatan: (a) token blank '-'/'—' ikut
    # dibuang (cermin kategori_blank_mask — dulu rekap '-' MENIMPA
    # master nyata → item 'kehilangan' kategorinya); (b) duplikat nama
    # barang antar rekap LALU vs BERJALAN: keep="last" (concat queries
    # b-lalu lalu a-berjalan → BERJALAN menang — bulan berjalan
    # otoritatif; dulu nilai basi bulan lalu menang diam-diam); (c) log
    # juga melaporkan baris yang NILAINYA benar-benar BERUBAH dari master
    # (rekonsiliasi audit — 'ber-rekap' tak membedakan sama/berubah).
    _n_rk_barang = 0
    _n_rk_rows = 0
    _n_rk_changed = 0
    if ("KATEGORI" in full_rekap_so.columns
            and "Nama Barang" in full_rekap_so.columns
            and "Nama Barang" in expanded_kategori.columns):
        _rk = full_rekap_so[["Nama Barang", "KATEGORI"]].copy()
        _rk["Nama Barang"] = _rk["Nama Barang"].astype(str).str.strip().str.upper()
        _rk["KATEGORI"] = _rk["KATEGORI"].astype(str).str.strip()
        _rk = _rk[_rk["KATEGORI"].ne("")
                  & _rk["KATEGORI"].str.lower().ne("nan")
                  & _rk["KATEGORI"].str.lower().ne("none")
                  & ~_rk["KATEGORI"].isin(["-", "—"])]
        _rk = _rk.drop_duplicates(subset=["Nama Barang"], keep="last")
        _rk_map = dict(zip(_rk["Nama Barang"], _rk["KATEGORI"]))
        if _rk_map:
            _kk = expanded_kategori["Nama Barang"].astype(str).str.strip().str.upper()
            _rk_val = _kk.map(_rk_map)
            _has_rk = _rk_val.notna()
            if bool(_has_rk.any()):
                # v3.9.50 — hitung baris yang nilai kategorinya BENAR
                # berubah dari master (rekonsiliasi; master disalin dulu
                # sbg string utk perbandingan stabil None/NaN→'None').
                _before_rk = expanded_kategori["KATEGORI"].astype(str)
                expanded_kategori["KATEGORI"] = _rk_val.where(
                    _has_rk, expanded_kategori["KATEGORI"])
                _n_rk_changed = int(
                    (_has_rk
                     & (expanded_kategori["KATEGORI"].astype(str)
                        != _before_rk)).sum())
                _n_rk_barang = len(_rk_map)
                _n_rk_rows = int(_has_rk.sum())
    if _n_rk_barang:
        print(f"    KATEGORI Rekap Mentah (prioritas atas master): "
              f"{_n_rk_barang} barang ({_n_rk_rows:,} baris) ber-kategori "
              f"rekap ({_n_rk_changed:,} baris berubah dari master)")

    # =========================================================================
    # 5b. SOURCE KIRIMAN PER PASANGAN (v3.9.29 — MENGGANTI nilai master)
    # =========================================================================
    # Klasifikasi dari sumber IN AKTUAL per (Nama Barang, NAMA RESTO):
    #   hanya 42.05/42.05-Lalu → "Internal"; hanya 32.24(-Lalu)/99.01 →
    #   "Eksternal"; campuran → "Campuran"; tanpa dokumen IN → kosong
    #   (None — mirror perilaku kolom Z 'Kiriman' sheet terhide 'Data Base
    #   Cek Deviasi' workbook referensi: pasangan tanpa kiriman kosong).
    # Merge terjadi pada frame LEBAR (1 baris = 1 pasangan) → nilai konstan
    # per pasangan, terbawa utuh ke format long setelah unpivot.
    if {"Nama Barang", "NAMA RESTO"} <= set(expanded_kategori.columns):
        if _src_kiriman is not None and not _src_kiriman.empty:
            expanded_kategori = expanded_kategori.merge(
                _src_kiriman, on=["Nama Barang", "NAMA RESTO"], how="left")
        else:
            expanded_kategori["SOURCE KIRIMAN"] = None
    else:
        expanded_kategori["SOURCE KIRIMAN"] = None
        if "NAMA RESTO" not in expanded_kategori.columns:
            print("  [Append1] WARNING: kolom NAMA RESTO absen — "
                  "SOURCE KIRIMAN per pasangan dilewati (semua kosong)")

    # =========================================================================
    # 6. UNPIVOT — 8 metric columns + SALDO AWAL → (JENIS, NILAI)
    # =========================================================================
    print("  [Append1] Unpivoting metrics...")
    # FIX: include 8.BARANG KELUAR (was missing → all BK data lost)
    # FIX: use new numbering 7.Selisih IN + 9.ACR (matches pivot_view METRICS)
    unpivot_columns = [
        "2.SALDO AKHIR", "1.SO", "3.DEVIASI", "4.IN",
        "5.BARANG MASUK", "7.Selisih IN", "8.BARANG KELUAR", "9.ACR", "SALDO AWAL"
    ]
    available_unpivot = [c for c in unpivot_columns if c in expanded_kategori.columns]

    if not available_unpivot:
        print("  [Append1] WARNING: No metric columns found for unpivot!")
        return pd.DataFrame(columns=[
            "Nama Barang", "NAMA RESTO", "Tanggal", "JENIS", "NILAI",
            "Nomor", "Nomor PO", "#Tgl/Jam Pembuatan IT", "KATEGORI", "SOURCE KIRIMAN"
        ])

    # id_vars = all columns except the unpivot columns
    id_vars = [c for c in expanded_kategori.columns if c not in available_unpivot]
    unpivoted = expanded_kategori.melt(
        id_vars=id_vars,
        value_vars=available_unpivot,
        var_name="JENIS",
        value_name="NILAI"
    )

    # Drop rows where NILAI is null (M's Table.Unpivot doesn't create rows for nulls)
    # After ReplaceValue null→0, metrics are 0 not null. But SALDO AWAL might have nulls.
    unpivoted = unpivoted.dropna(subset=["NILAI"]).reset_index(drop=True)

    # =========================================================================
    # 7. RESTORE URUTAN KOLOM FINAL
    # =========================================================================
    final_columns = KeyColumns + ["JENIS", "NILAI"] + AvailableInfoColumns + [
        "KATEGORI", "SOURCE KIRIMAN", "SATUAN", "AKTIF/NON"]
    available_final = [c for c in final_columns if c in unpivoted.columns]
    final = unpivoted[available_final].copy()

    # Type: Tanggal → Int64, NILAI → numeric
    if "Tanggal" in final.columns:
        final["Tanggal"] = pd.to_numeric(final["Tanggal"], errors="coerce").astype("Int64")
    if "NILAI" in final.columns:
        final["NILAI"] = pd.to_numeric(final["NILAI"], errors="coerce")

    # =========================================================================
    # 8. LOOKUP SATUAN (untuk DEVIASI GR/PCS split)
    # =========================================================================
    # SATUAN hanya ada di Full Rekap Mentah SO (dari fn_rekap_mentah).
    # Di pivot+unpivot, SATUAN hilang. Lookup dari full_rekap_so berdasarkan (Nama Barang, NAMA RESTO).
    if full_rekap_so is not None and "SATUAN" in full_rekap_so.columns:
        # Build SATUAN mapping: (Nama Barang, NAMA RESTO) → SATUAN (first non-null)
        satuan_map = (
            full_rekap_so[["Nama Barang", "NAMA RESTO", "SATUAN"]]
            .dropna(subset=["SATUAN"])
            .drop_duplicates(subset=["Nama Barang", "NAMA RESTO"], keep="first")
        )
        if not satuan_map.empty:
            # Merge SATUAN to final (creates SATUAN column if not exists, fills if exists)
            if "SATUAN" in final.columns:
                final = final.merge(
                    satuan_map.rename(columns={"SATUAN": "_SATUAN_LOOKUP"}),
                    on=["Nama Barang", "NAMA RESTO"], how="left"
                )
                final["SATUAN"] = final["SATUAN"].fillna(final["_SATUAN_LOOKUP"])
                final = final.drop(columns=["_SATUAN_LOOKUP"])
            else:
                final = final.merge(satuan_map, on=["Nama Barang", "NAMA RESTO"], how="left")

    # v3.9.32 — FALLBACK SATUAN 42.17 ('Nama Satuan' file per barang):
    # pasangan TANPA rekap SO (barang 42.17-only — saldo tanpa SO, contoh
    # user: BUMBU PASTA KUAH) kini punya SATUAN. Tanpa ini barisnya
    # dibuang senyap oleh pivot_table Deviasi GR/PCS (index SATUAN NaN)
    # — inilah separuh akar "barang 42.17 tidak muncul". Rekap tetap
    # menang (urutan fillna), 42.17 hanya menambung yang kosong.
    if q4217 is not None and not q4217.empty \
            and "SATUAN" in q4217.columns \
            and "Nama Barang" in final.columns \
            and "NAMA RESTO" in final.columns:
        _sat4217 = q4217[["Nama Barang", "NAMA RESTO", "SATUAN"]].copy()
        _sat4217["Nama Barang"] = _sat4217["Nama Barang"].astype(str)
        _sat4217["NAMA RESTO"] = _sat4217["NAMA RESTO"].astype(str)
        _sat4217["SATUAN"] = _sat4217["SATUAN"].astype(str).str.strip()
        _sat4217 = _sat4217[_sat4217["SATUAN"] != ""]
        _sat4217 = (
            _sat4217.dropna(subset=["Nama Barang", "NAMA RESTO"])
            .drop_duplicates(subset=["Nama Barang", "NAMA RESTO"],
                             keep="first")
        )
        if not _sat4217.empty:
            if "SATUAN" in final.columns:
                final = final.merge(
                    _sat4217.rename(columns={"SATUAN": "_SAT4217"}),
                    on=["Nama Barang", "NAMA RESTO"], how="left")
                final["SATUAN"] = final["SATUAN"].fillna(final["_SAT4217"])
                final = final.drop(columns=["_SAT4217"])
            else:
                final = final.merge(_sat4217,
                                    on=["Nama Barang", "NAMA RESTO"],
                                    how="left")

    # v3.9.39 — JEJAK DUA ARAH (transparansi "barang 42.17 tidak muncul"):
    # pasangan SALDO-ONLY = ada baris 'SALDO AWAL' 42.17 tapi TANPA rekap
    # SO/BARANG MASUK — baris ini tetap masuk Deviasi GR/PCS via mask
    # saldo-only (v3.9.32) dan kini DICECUT di log supaya kelihatan
    # jumlah pasangan 42.17 yang benar-benar terbawa ke tabel.
    # v3.9.41 — hanya SALDO AWAL ber-NILAI ≠ 0 yang dihitung: unpivot
    # LANGKAH 6 membuat baris 'SALDO AWAL' nilai-0 utk SEMUA pasangan ×
    # tanggal teramati (fillna 0) — dulu ikut terhitung → angka jejak
    # menyesatkan (probe: 3 barang 42.17 → "983 pasangan saldo-only").
    try:
        _nil = pd.to_numeric(final["NILAI"], errors="coerce").fillna(0)
        _sa_pairs = (final[(final["JENIS"] == "SALDO AWAL")
                           & (_nil != 0)]
                     [["Nama Barang", "NAMA RESTO"]].drop_duplicates())
        # 'ber-rekap' = ada baris 1.SO/5.BARANG MASUK ber-NILAI non-nol
        # (unpivot LANGKAH 6 membuat baris '1.SO' nilai-0 utk SEMUA
        # pasangan × tanggal teramati — termasuk pasangan 42.17-only;
        # tanpa cek NILAI jejak ini selalu 0).
        _rk = final[(final["JENIS"].isin(("1.SO", "5.BARANG MASUK")))
                    & (_nil != 0)]
        _rk_pairs = _rk[["Nama Barang", "NAMA RESTO"]].drop_duplicates()
        if not _sa_pairs.empty:
            _only = _sa_pairs.merge(
                _rk_pairs, on=["Nama Barang", "NAMA RESTO"],
                how="left", indicator=True)
            _n_only = int((_only["_merge"] == "left_only").sum())
            print(f"    4217 dua arah: {_n_only} pasangan saldo-only "
                  "(barang 42.17 tanpa rekap SO) masuk Deviasi "
                  "GR/PCS")
            # v3.9.44 — transparansi kategori master: pasangan saldo-only
            # TANPA entri di '21. DBS Kategori' (KATEGORI NaN — contoh
            # nyata: BUMBU PASTA KUAH 100383, master user hanya punya
            # varian (V.20)) dulu lenyap senyap dari tab Deviasi GR
            # karena filter KATEGORI default 'Deviasi' membuang baris
            # NaN — kini view me-passthrough baris tanpa kategori
            # (v3.9.45: HANYA di seleksi default Deviasi + entry
            # '(Tanpa Kategori)' — lihat widgets.kategori_passthrough);
            # jejak ini menyebut jumlahnya supaya keluhan "barang tidak
            # muncul" langsung ketemu penyebabnya di log.
            try:
                if "KATEGORI" in final.columns and _n_only:
                    _only_k = _only[_only["_merge"] == "left_only"][
                        ["Nama Barang", "NAMA RESTO"]].drop_duplicates()
                    # KATEGORI konstan per pasangan (merge master by nama)
                    # — hitung PASANGAN, bukan baris long (31 tanggal ×
                    # 9 JENIS akan menggelembungkan angka jejak).
                    _kk = (final[["Nama Barang", "NAMA RESTO", "KATEGORI"]]
                           .drop_duplicates(
                               subset=["Nama Barang", "NAMA RESTO"])
                           .merge(_only_k,
                                  on=["Nama Barang", "NAMA RESTO"],
                                  how="inner"))
                    _kk_blank = int(
                        kategori_blank_mask(_kk["KATEGORI"]).sum()) \
                        if len(_kk) else 0
                    if _kk_blank:
                        print(f"    [INFO] 4217: {_kk_blank} pasangan "
                              "saldo-only TANPA kategori master (barang "
                              "lama 42.17 belum masuk '21. DBS Kategori' "
                              "— contoh BUMBU PASTA KUAH 100383) — tampil "
                              "di seleksi DEFAULT Deviasi & entry "
                              "'(Tanpa Kategori)' (v3.9.45)")
            except (KeyError, ValueError, TypeError):
                pass  # defensif — kolom tak lengkap pada input aneh
    except (KeyError, ValueError, TypeError):
        pass  # defensif — final tanpa kolom JENIS/Nama Barang (input aneh)


    # =========================================================================
    # 9. LOOKUP SOURCE DATA (v3.9.19 — CEK "Promix 04" di tab Deviasi;
    # v3.9.21 — PER-TANGGAL, fix "Promix 04 muncul di filter tapi data
    # tidak ada")
    # =========================================================================
    # SOURCE DATA hanya ada di Full Rekap Mentah (JENIS 'SO': "input so
    # harian" / "input promix jam 4 dine in" / "input promix jam 4 take
    # away" / "input penjualan dine in/take away 04"). Struktur rekap
    # real: SATU pasangan punya BEBERAPA baris sumber (manual + promix
    # dine in + promix take away) — template baris dengan sel hari 0 di
    # tanggal tanpa hitungan; sel bernilai = sumber SO aktual tanggal itu.
    #
    # v3.9.21 RESOLUSI PER (Nama Barang, NAMA RESTO, Tanggal) atas baris
    # ber-NILAI NON-NOL saja:
    # - tanggal sama ada baris 'input so harian' + promix → SO HARIAN
    #   menang (hitungan manual mengalahkan turunan sistem);
    # - hanya promix (nilai non-nol) → sumber promix → CEK "Promix 04"
    #   di tanggal itu (deviasi_view membaca baris 1.SO tanggal H);
    # - nilai 0/NaN → TIDAK ikut menentukan sumber (baris template);
    # - sumber whitespace-only ('   ') → dianggap TIDAK ada sumber.
    # Deterministik penuh (mergesort + kunci eksplisit; tidak bergantung
    # urutan baris sheet) dan bebas race "tanggal tertinggi" pair-level
    # (v3.9.19 bisa melabel semua pasangan campuran sbg Promix krn tie
    # urutan baris di tanggal tertinggi; v3.9.20 swing kebalikannya).
    if (full_rekap_so is not None
            and "SOURCE DATA" in full_rekap_so.columns
            and "Nama Barang" in final.columns
            and "NAMA RESTO" in final.columns
            and "Tanggal" in final.columns):
        so_rows = full_rekap_so[
            (full_rekap_so["JENIS"].astype(str).str.strip().str.upper()
             == "SO")
            & full_rekap_so["SOURCE DATA"].notna()
        ]
        if not so_rows.empty:
            # nilai non-nol saja + strip sumber (whitespace-only → ''
            # dibuang — bukan sumber). Kolom nilai = "Value" (schema
            # query rekap); fallback "NILAI" utk input buatan.
            _val_col = ("Value" if "Value" in so_rows.columns
                        else ("NILAI" if "NILAI" in so_rows.columns
                              else None))
            if _val_col is not None:
                _val = pd.to_numeric(so_rows[_val_col], errors="coerce")
                _src0 = so_rows["SOURCE DATA"].map(
                    lambda v: v.strip() if isinstance(v, str) else v)
                _t0 = pd.to_numeric(so_rows["Tanggal"], errors="coerce")
                _keep = ((_val.fillna(0) != 0)
                         & _src0.astype(str).str.strip().ne("")
                         & _t0.notna())   # NA-Tanggal tak match kunci merge
                so_rows = so_rows[_keep]
        if not so_rows.empty:
            _src = so_rows["SOURCE DATA"].map(
                lambda v: v.strip() if isinstance(v, str) else v)
            _s = _src.astype(str)
            src_map = (
                so_rows.assign(_src=_src, _s=_s,
                               _harian=_s.str.strip().str.lower()
                               == "input so harian")
                .sort_values(["_harian", "_s"], kind="mergesort")
                .drop_duplicates(
                    subset=["Nama Barang", "NAMA RESTO", "Tanggal"],
                    keep="last")
                [["Nama Barang", "NAMA RESTO", "Tanggal", "_src"]]
                .rename(columns={"_src": "SOURCE DATA"})
            )
            # samakan tipe kunci Tanggal dgn final (Int64; NA tak match —
            # memang tanpa sumber)
            src_map = src_map.assign(
                Tanggal=pd.to_numeric(
                    src_map["Tanggal"], errors="coerce").astype("Int64"))
            _merge_on = ["Nama Barang", "NAMA RESTO", "Tanggal"]
            if "SOURCE DATA" in final.columns:
                final = final.merge(
                    src_map.rename(columns={"SOURCE DATA": "_SRC_LOOKUP"}),
                    on=_merge_on, how="left")
                final["SOURCE DATA"] = final["SOURCE DATA"].fillna(
                    final["_SRC_LOOKUP"])
                final = final.drop(columns=["_SRC_LOOKUP"])
            else:
                final = final.merge(src_map, on=_merge_on, how="left")
            print(f"    SOURCE DATA (rekap SO per tanggal): "
                  f"{len(src_map)} pasangan-tanggal")
        else:
            print("    SOURCE DATA (rekap SO): 0 baris ber-sumber non-nol")

    print(f"  [Append1] DONE: {len(final)} rows")
    return final
