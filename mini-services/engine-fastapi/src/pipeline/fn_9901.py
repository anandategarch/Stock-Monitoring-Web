"""
fn_9901.py — Process 9901 file (mutasi barang tanpa nomor penerimaan).
Sumber data IN tambahan (digabung dengan 3224, 4205 di query_in).

Filter:
  - "Nomor # Penerimaan Barang" = Blank (kosong)
  - "Jenis Barang Barang & Jasa" = "Persediaan"

Column mapping:
  - #Prime.Qty     → Value
  - Nama barang    → Nama Barang
  - Nama cabang    → NAMA RESTO (extract after titik TERAKHIR, e.g.,
                   "1137.CKGPAH" → "CKGPAH", "B.1001.MLGPAR" → "MLGPAR")
                   CONSISTENT with fn_3224/fn_4215/fn_4217/fn_4205 which extract
                   from between parentheses "(" and ")"
  - Tanggal        → Tanggal (day-of-month)
  - Nomor #        → Nomor (nomor faktur pembelian, mis. PI.2026.09.30973) — v3.4
  - Nomor # Pesanan Pembelian → Nomor PO — v3.4

v3.4: kolom Nomor / Nomor PO ditambahkan untuk tab "Rekap Selisih IN"
(rincian IN per dokumen 42.05 / 32.24 / 99.01 beserta nomornya).

v3.9.33 — AUDIT FIX (48-a, deep audit):
- SEMUA sheet × SEMUA file dibaca lalu di-concat TANPA dedup → sheet
  backup/ringkasan/file salinan masuk IN DUA KALI (groupby-SUM append1
  mendobel qty senyap). Sekarang: baris duplikat PERSIS dibuang + log
  mencolok + kontribusi baris per sheet dicatat (double-read terlihat).
- fallback kolom qty: "jumlah" dibuang dari kandidat + kandidat bernama
  'harga'/'nilai' di-exclude (dulu bisa nyasar kolom uang "Jumlah Harga").
- filter yang di-skip karena kolom hilang kini WAJIB teriak WARNING
  lengkap dengan jumlah baris yang dianggap lolos (risiko dobel hitung
  vs 32.24 jadi eksplisit, bukan senyap).

v3.9.42 — AUDIT FIX (61-a, F3): NAMA RESTO kini lewat helper bersama
resto_from_cabang_po (bagian setelah titik TERAKHIR, NA/float-safe).
Dulu membelah di titik PERTAMA → cabang ber-format 'B.1001.MLGPAR'
menjadi '1001.MLGPAR' (resto phantom — tidak cocok dgn sumber lain →
IN 9901 resto itu lenyap dari pivot).

v3.9.67 — HARDENING KETAHANAN FORMAT EXPORT (audit ketahanan,
user: "misal suatu saat format tarikan dari accurate berubah aman gak?").
Eksperimen 6 varian mutasi format membuktikan: tambah kolom / hapus
kolom tak terpakai / reorder = IDENTIK (seleksi kolom by-NAMA, bukan
posisi). Dua celah SENYAP ditemukan & ditutup:
- Rename header terpakai ('Nama barang' → nama lain) + ada kolom lain
  ber-substring 'barang' terisi ('Kode Barang') → fallback _find_column
  mengikat kolom yang SALAH tanpa jejak (uji nyata: Nama Barang nyasar
  ke kode barang 'GL001'/'KP001', qty benar, nol warning). Kini SETIAP
  pengikatan lewat fallback (bukan nama persis kandidat) DI-LOG
  WARNING lengkap dgn kolom tujuan ikatannya.
- (keluarga header_row=4: lihat fn_2205/3224/4205/4215 — kolom VALUE
  hilang kini ikut di-WARNING, dulu NA senyap.)
"""
import os

import pandas as pd

from .helpers import (
    date_to_day,
    resto_from_cabang_po,
    safe_to_numeric,
    safe_to_str,
)


def _find_column(df_cols, candidates, contains_any=None, exclude=None):
    """Find column by priority: exact match > substring > exact-short match.

    candidates: list of preferred exact names (case-insensitive, trimmed).
    contains_any: list of substrings to match if no exact match found.
    exclude: list of substrings — if a matched column contains any of these, skip it.
    Returns column name or None.
    """
    if df_cols is None or len(df_cols) == 0:
        return None
    # Normalize for case-insensitive comparison
    cols_lower = {str(c).strip().lower(): c for c in df_cols}

    def _is_excluded(col_name_lower):
        if not exclude:
            return False
        return any(ex.lower() in col_name_lower for ex in exclude)

    # 1) Exact match (case-insensitive, trimmed)
    for cand in candidates or []:
        key = str(cand).strip().lower()
        if key in cols_lower and not _is_excluded(key):
            return cols_lower[key]

    # 2) Substring match (prefer SHORTEST column name to avoid false positives)
    if contains_any:
        for substr in contains_any:
            substr_l = str(substr).lower()
            # Collect all matching columns, then pick shortest (most specific)
            matches = []
            for clow, corig in cols_lower.items():
                if substr_l in clow and not _is_excluded(clow):
                    matches.append((len(clow), corig))
            if matches:
                matches.sort(key=lambda x: x[0])  # shortest first
                return matches[0][1]

    return None


def fn_9901(folder_path: str) -> pd.DataFrame:
    """
    Process 9901 file in folder_path. Returns DataFrame with columns:
    Tanggal, NAMA RESTO, Nama Barang, Value
    """
    # The 9901 file may have varying sheet names. Try common ones.
    # First, attempt to list files and find a sheet name.
    from .helpers import _list_excel_files, fn_buka_sheet
    files = _list_excel_files(folder_path)
    if not files:
        print(f"  [fn_9901] No Excel files found in: {folder_path}")
        return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

    dfs = []
    for f in files:
        try:
            # Try to find a suitable sheet. Many 9901 exports have a single sheet
            # or use the default first sheet. We'll read all sheets and concat.
            import openpyxl
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
            sheet_names = wb.sheetnames
            wb.close()
        except Exception:
            sheet_names = [0]  # fallback to first sheet

        for sn in sheet_names:
            try:
                df = fn_buka_sheet(f, sn, header_row=0)
            except Exception:
                # Fallback: read with default openpyxl
                try:
                    df = pd.read_excel(f, sheet_name=sn, header=0, dtype=object)
                except Exception as e:
                    print(f"  [fn_9901] Skip sheet '{sn}' in {f}: {e}")
                    continue
            if df is not None and len(df) > 0:
                dfs.append(df)
                # v3.9.33 — AUDIT FIX (48-a): kontribusi baris per sheet
                # (file + sheet + jumlah baris) — sheet backup/salinan
                # yang kebaca dobel jadi KELIHATAN di log.
                print(f"  [fn_9901] {os.path.basename(f)} :: sheet "
                      f"'{sn}': {len(df)} baris")

    if not dfs:
        return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

    prom = pd.concat(dfs, ignore_index=True, sort=False)

    # v3.9.33 — AUDIT FIX (48-a HIGH): concat SEMUA sheet × SEMUA file tanpa
    # dedup → baris identik masuk 2× (sheet backup / ringkasan / file
    # salinan di folder bulan) → qty IN terhitung DOBEL senyap di pivot
    # append1. Buang baris duplikat PERSIS (semua kolom sama); jika ada
    # yang terbuang → log KERAS supaya user cek foldernya.
    n_before = len(prom)
    prom = prom.drop_duplicates()
    if n_before > len(prom):
        print(f"  [fn_9901] 9901 v3.9.33: {n_before - len(prom)} baris "
              f"duplikat persis dibuang (sheet backup/salinan?)")

    if prom.empty:
        return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

    # --- Locate columns (flexible matching) ---
    # Per screenshot from user: actual headers seen = 'Nomor # Penerimaan' (no 'Barang' suffix), 'Barang'
    col_nomor_penerimaan = _find_column(
        prom.columns,
        candidates=["Nomor # Penerimaan Barang", "Nomor # Penerimaan",
                    "Nomor Penerimaan Barang", "Nomor Penerimaan"],
        contains_any=["penerimaan"]
    )
    col_jenis = _find_column(
        prom.columns,
        candidates=["Jenis Barang Barang & Jasa", "Jenis Barang", "Barang & Jasa"],
        contains_any=["jenis", "barang & jasa", "barang jasa"]
    )
    # v3.9.33 — AUDIT FIX (48-a): "jumlah" DIHAPUS dari kandidat fallback
    # (bisa nyasar kolom uang "Jumlah Harga") + exclude nama kolom yang
    # mengandung 'harga'/'nilai' (kolom nilai rupiah, bukan qty).
    col_qty = _find_column(
        prom.columns,
        candidates=["#Prime.Qty", "Prime.Qty", "Prime Qty", "#Prime Qty"],
        contains_any=["prime", "qty", "kuantiti", "kuantitas"],
        exclude=["harga", "nilai"]
    )
    # Nama Barang: exclude Jenis column to avoid collision. Also accept 'Barang' alone.
    col_nama_barang = _find_column(
        prom.columns,
        candidates=["Nama barang", "Nama Barang", "NAMA BARANG", "Barang"],
        contains_any=["nama barang"],
        exclude=["jenis"]
    )
    # Fallback: if still not found, look for column containing 'barang' but not 'jenis'
    if col_nama_barang is None:
        col_nama_barang = _find_column(
            prom.columns,
            candidates=[],
            contains_any=["barang"],
            exclude=["jenis", "penerimaan", "kirim", "masuk", "keluar"]
        )
    col_nama_cabang = _find_column(
        prom.columns,
        candidates=["Nama cabang", "Nama Cabang", "Cabang"],
        contains_any=["cabang"]
    )
    col_tanggal = _find_column(
        prom.columns,
        candidates=["Tanggal", "TGL", "Date"],
        contains_any=["tanggal", "tgl", "date"]
    )
    # v3.4: nomor faktur pembelian (PI.2026…) + nomor pesanan (PO.2026…)
    col_nomor = _find_column(
        prom.columns,
        candidates=["Nomor #", "Nomor"],
        contains_any=[],
    )
    # pastikan col_nomor bukan kolom penerimaan/pesanan/aset
    if col_nomor is not None:
        cl = str(col_nomor).strip().lower()
        if any(x in cl for x in ("penerimaan", "pesanan", "aset", "kirim",
                                 "faktur pajak")):
            col_nomor = None
    col_nomor_po = _find_column(
        prom.columns,
        candidates=["Nomor # Pesanan Pembelian", "Nomor Pesanan Pembelian",
                    "Nomor # Pesanan"],
        contains_any=["pesanan pembelian", "pesanan"],
    )

    # Diagnostic logging (helps user debug if mapping fails)
    missing = []
    if col_nomor_penerimaan is None:
        missing.append("Nomor # Penerimaan Barang")
    if col_jenis is None:
        missing.append("Jenis Barang Barang & Jasa")
    if col_qty is None:
        missing.append("#Prime.Qty")
    if col_nama_barang is None:
        missing.append("Nama barang")
    if col_nama_cabang is None:
        missing.append("Nama cabang")
    if col_tanggal is None:
        missing.append("Tanggal")
    if missing:
        print(f"  [fn_9901] WARNING: could not find columns: {missing}")
        print(f"  [fn_9901] Available columns: {list(prom.columns)}")

    # v3.9.67 — HARDENING FORMAT: kolom yang diikat lewat FALLBACK
    # (substring match — bukan nama persis kandidat) kini DI-LOG keras.
    # Uji mutasi format: rename 'Nama barang' → 'Nama Item' + kolom
    # 'Kode Barang' terisi → fallback mengikat Nama Barang ke KODE
    # BARANG secara SENYAP (qty/resto benar, nama nyasar ke kode item;
    # barang lalu tak cocok sumber lain → tersekat di pivot tanpa jejak).
    _fallback_binds = []
    for _label, _col, _cands in (
        ("Nomor # Penerimaan", col_nomor_penerimaan,
         ("Nomor # Penerimaan Barang", "Nomor # Penerimaan",
          "Nomor Penerimaan Barang", "Nomor Penerimaan")),
        ("Jenis Barang", col_jenis,
         ("Jenis Barang Barang & Jasa", "Jenis Barang", "Barang & Jasa")),
        ("Qty", col_qty,
         ("#Prime.Qty", "Prime.Qty", "Prime Qty", "#Prime Qty")),
        ("Nama Barang", col_nama_barang,
         ("Nama barang", "Nama Barang", "NAMA BARANG", "Barang")),
        ("Nama Cabang", col_nama_cabang,
         ("Nama cabang", "Nama Cabang", "Cabang")),
        ("Tanggal", col_tanggal, ("Tanggal", "TGL", "Date")),
    ):
        if _col is not None:
            _cand_l = {str(c).strip().lower() for c in _cands}
            if str(_col).strip().lower() not in _cand_l:
                _fallback_binds.append(f"{_label}→'{_col}'")
    if _fallback_binds:
        print(f"  [fn_9901] WARNING: kolom diikat lewat FALLBACK (bukan "
              f"nama persis): {', '.join(_fallback_binds)} — cek header "
              f"file 9901 (di-rename/diubah oleh export baru Accurate?)")

    # --- Filter 1: Nomor # Penerimaan Barang = Blank ---
    if col_nomor_penerimaan is not None:
        nomor_series = prom[col_nomor_penerimaan]
        # Treat NaN, None, empty string, whitespace as blank
        is_blank = nomor_series.isna() | (
            nomor_series.astype(str).str.strip().isin(["", "nan", "None", "NaT"])
        )
        prom = prom[is_blank].copy()
        print(f"  [fn_9901] After filter Nomor # Penerimaan Barang = Blank: {len(prom)} rows")
    else:
        # If column missing, assume all rows match (no filter applied).
        # v3.9.33 — AUDIT FIX (48-a): skip tetap dipertahankan (perilaku
        # lama) tapi TIDAK lagi senyap — WARNING mencolok + jumlah baris
        # yang dianggap lolos (risiko dobel hitung vs 32.24: baris
        # ber-penerimaan ikut terbaca sebagai IN 99.01).
        print(f"  [fn_9901] 9901 WARNING: kolom 'Nomor # Penerimaan' "
              f"tidak ditemukan — {len(prom)} baris dianggap tanpa "
              f"penerimaan (risiko dobel hitung vs 32.24)")

    # --- Filter 2: Jenis Barang Barang & Jasa = Persediaan ---
    if col_jenis is not None:
        jenis_series = prom[col_jenis].astype(str).str.strip().str.lower()
        mask_persediaan = jenis_series == "persediaan"
        prom = prom[mask_persediaan].copy()
        print(f"  [fn_9901] After filter Jenis = Persediaan: {len(prom)} rows")
    else:
        # v3.9.33 — AUDIT FIX (48-a): mirror warning filter penerimaan —
        # baris jasa/aset ikut dianggap Persediaan (skip tidak senyap).
        print(f"  [fn_9901] 9901 WARNING: kolom 'Jenis Barang Barang & "
              f"Jasa' tidak ditemukan — {len(prom)} baris dianggap "
              f"Persediaan (risiko baris jasa/aset ikut terhitung vs "
              f"32.24)")

    if prom.empty:
        return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

    # --- Build output ---
    out = pd.DataFrame()

    # Tanggal → day-of-month
    if col_tanggal is not None:
        out["Tanggal"] = date_to_day(prom[col_tanggal])
    else:
        out["Tanggal"] = pd.NA

    # NAMA RESTO from Nama cabang
    # v3.9.42 — AUDIT FIX (61-a, F3): resto = bagian setelah titik TERAKHIR
    # lewat helper bersama resto_from_cabang_po (NA/float-safe; dipakai
    # juga fn_audit PO Menunggu + rincian_po_view) — dulu membelah di
    # titik PERTAMA: 'B.1001.MLGPAR' → '1001.MLGPAR' (resto phantom yang
    # tak cocok dgn sumber lain → IN 9901 resto itu lenyap dari pivot).
    # Scalar-safe → .map() per baris (fn_9901 ribuan baris — murah).
    if col_nama_cabang is not None:
        out["NAMA RESTO"] = prom[col_nama_cabang].map(resto_from_cabang_po)
    else:
        out["NAMA RESTO"] = pd.NA

    # Nama Barang
    if col_nama_barang is not None:
        out["Nama Barang"] = safe_to_str(prom[col_nama_barang])
    else:
        out["Nama Barang"] = pd.NA

    # Value from #Prime.Qty
    if col_qty is not None:
        out["Value"] = safe_to_numeric(prom[col_qty])
    else:
        out["Value"] = pd.NA

    # v3.4 — Nomor (faktur pembelian PI…) & Nomor PO (pesanan PO…)
    if col_nomor is not None:
        out["Nomor"] = safe_to_str(prom[col_nomor])
    else:
        out["Nomor"] = pd.NA
    if col_nomor_po is not None:
        out["Nomor PO"] = safe_to_str(prom[col_nomor_po])
    else:
        out["Nomor PO"] = pd.NA

    # Drop rows where NAMA RESTO is empty (mirror fn_3224 behavior)
    mask_valid_resto = out["NAMA RESTO"].notna() & (
        out["NAMA RESTO"].astype(str).str.strip() != "")
    out = out[mask_valid_resto].reset_index(drop=True)

    print(f"  [fn_9901] DONE: {len(out)} rows")
    return out
