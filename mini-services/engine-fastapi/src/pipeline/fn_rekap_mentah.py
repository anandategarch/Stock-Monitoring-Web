"""
fn_rekap_mentah.py — Mirror persis fnRekapMentah di M code.
Membaca folder Rekap Mentah (SO + BARANG MASUK), unpivot kolom tanggal.

CRITICAL FIX: NAMA RESTO berasal dari FILE NAME (bukan sheet column).
Mirror M: fnCombineFolder → Name column → PromoteHeaders → firstColumn = file1's name
           → rename → "NAMA RESTO" → Text.BeforeDelimiter(_, ".")

v3.3.1 — FALLBACK "combined workbook":
Sumber SO user kini berupa SATU file gabungan (mis. "01.1 CEK STOCK V2.xlsb",
sheet '1  DEVIASI WEEKLY') berisi SEMUA resto dalam satu sheet dengan kolom
NAMA RESTO — bukan file per-resto dengan sheet "REKAP MENTAH". Format lama
tidak cocok (sheet beda nama + .xlsb tidak ter-glob) → SO tidak pernah
 terbaca → "Saldo SO kosong semua" di tab Deviasi GR/PCS.
Bila folder tidak punya file per-resto "REKAP MENTAH", reader otomatis:
  1. scan semua file Excel (termasuk .xlsb) di folder tsb (+ folder induk
     untuk mode "berjalan" — file gabungan kadang disimpan di RootPath)
  2. deteksi sheet ber-schema rekap-mentah (kolom NAMA RESTO + JENIS +
     NAMA BARANG + SATUAN + ≥3 kolom hari 1..31) pada ≤6 baris pertama
  3. baca sheet tsb, NAMA RESTO diambil dari KOLOM (bukan nama file)

v3.4 — FIX "SO bulan lalu gak ke record meskipun LightMode OFF":
Data bulan lalu user ada di sheet 'SO BULAN LALU' (workbook gabungan di
RootPath) — schema: NAMA RESTO + NAMA BARANG + JENIS + kolom hari
"Sum of 1".."Sum of 31", TANPA SATUAN. Sebelumnya:
  - mode "lalu" tidak pernah scan folder induk/RootPath;
  - sheet itu gagal deteksi (kolom hari "Sum of N" + tanpa SATUAN).
Perbaikan:
  - deteksi schema menerima header hari "Sum of N" & SATUAN opsional
    (wajib: NAMA RESTO + JENIS + NAMA BARANG + ≥3 kolom hari);
  - mode "lalu" ikut scan RootPath, TAPI hanya sheet ber-nama "LALU"
    (jangan campur data bulan berjalan ke bulan lalu);
  - mode "berjalan" kini SKIP sheet ber-nama "LALU" (defensive — sheet
    '1  DEVIASI WEEKLY' tetap yang terbaca untuk bulan berjalan).

OPTIMIZED: vectorized text operations.

v3.9.42 — AUDIT FIX (61-a):
- F5: sheet_filter (pemisah sheet 'LALU' vs berjalan) dibangun SEKALI
  dan diteruskan ke KEDUA langkah scan — dulu hanya langkah-2 (folder
  induk) yang memakai filter: workbook gabungan yang berada DI DALAM
  folder RekapBerjalan/RekapLalu dibaca bebas-sheet → mode 'berjalan'
  bisa menelan sheet 'SO BULAN LALU' (bulan tercampur senyap).
- F6: filter JENIS jalur per-resto legacy kini case-insensitive
  (strip+upper KEDUA sisi — mirror jalur combined; dulu exact-case
  → 'so'/'So ' tertolak senyap); workbook gabungan lain di folder
  yang sama yang diabaikan first-match-wins kini DISEBUT di [INFO].

v3.9.49 — KOLOM KATEGORI REKAP MENTAH DIBAWA (user: "sebenernya sudah
ada KATEGORI dari file Rekap Mentah folder Deviasi Weekly jadi bisa
ambil kategori dari situ"): sheet '1  DEVIASI WEEKLY' user punya
kolom KATEGORI (nilai 'COM DEVIASI - RESTO' / 'Biaya Packaging -
RESTO') tepat setelah NAMA RESTO — sebelumnya kolom itu DIBUANG di
_combined_to_long (hanya _BASE_COLS + hari yang diseleksi) sehingga
lookup kategori app HANYA bergantung master '21. DBS Kategori'
(item tak terdaftar master → kategori kosong → kelas bug 100383).
Kini kolom KATEGORI dibawa di KEDUA jalur (combined + per-resto)
BILA ADA di sheet (schema lama tanpa KATEGORI tetap didukung — kolom
opsional, tidak mengubah bentuk output lama); konsumen:
query_full_rekap_mentah_so → append1 override prioritas.
"""
import os
from typing import List, Optional

import pandas as pd

from .helpers import (
    _EXCEL_ENGINE,
    _list_excel_files,
    _list_sheet_names,
    _xlsb_engine,
    fn_buka_sheet,
    fn_combine_folder,
    promote_headers,
    safe_to_numeric,
    safe_to_str,
)

# Kolom base schema rekap mentah (urutan output konsisten format lama)
_BASE_COLS = ["NAMA RESTO", "SOURCE DATA", "JENIS", "STATUS",
              "NAMA BARANG", "SATUAN"]

# Kolom WAJIB utk deteksi schema combined (v3.4: SATUAN jadi opsional —
# sheet 'SO BULAN LALU' user tidak punya kolom SATUAN)
_REQUIRED_COLS = ["NAMA RESTO", "JENIS", "NAMA BARANG"]


def _parse_day_header(h: str):
    """Header kolom hari → nomor hari (1..31), atau None.
    Menerima '1' / 1 / 1.0 (gabungan v3.3.1) maupun 'Sum of 25' (pivot
    Excel — sheet 'SO BULAN LALU' user, v3.4)."""
    s = str(h).strip().upper()
    if s.startswith("SUM OF "):
        s = s[len("SUM OF "):].strip()
    elif s.startswith("SUM OF"):
        s = s[len("SUM OF"):].strip()
    if not s or s in ("NONE", "NAN"):
        return None
    try:
        d = int(float(s))
    except (TypeError, ValueError):
        return None
    return d if 1 <= d <= 31 else None


def _detect_rekap_header(peek: pd.DataFrame):
    """Deteksi baris header ber-schema rekap-mentah dalam peek (raw,
    header=None, ≤6 baris pertama). Format combined: kolom NAMA RESTO +
    JENIS + NAMA BARANG (+ SATUAN opsional) + ≥3 kolom hari (header 1..31
    atau 'Sum of N' — v3.4).
    Return (header_row_idx, {posisi_kolom: nomor_hari}) atau None.

    Diverifikasi terhadap workbook gabungan user (16 sheet): hanya sheet
    '1  DEVIASI WEEKLY' (berjalan) dan 'SO BULAN LALU' (lalu) yang lolos —
    sheet lain (SO BULAN INI, DEVIASI GR, Barang Masuk/Keluar, 29 Rekap,
    Follow UP, dll) tertolak karena tidak punya JENIS / NAMA RESTO persis /
    kolom hari.
    """
    if peek is None or peek.empty:
        return None
    for hr in range(min(6, len(peek))):
        headers = [str(h).strip() if h is not None else "" for h in peek.iloc[hr].tolist()]
        up = [h.upper() for h in headers]
        # v3.4: SATUAN opsional — wajib NAMA RESTO + JENIS + NAMA BARANG
        if any(rc not in up for rc in _REQUIRED_COLS):
            continue
        day_pos = {}
        for i, h in enumerate(up):
            if h in ("", "NONE", "NAN"):
                continue
            d = _parse_day_header(h)
            if d is not None:
                day_pos[i] = d
        if len(day_pos) >= 3:
            return hr, day_pos
    return None


def _combined_to_long(df: pd.DataFrame, mode: str,
                      jenis_filter: Optional[List[str]]) -> Optional[pd.DataFrame]:
    """Ubah sheet combined (header sudah promote) → format long rekap
    mentah (schema output identik alur per-resto lama)."""
    if df is None or df.empty:
        return None
    headers = [str(c).strip() if c is not None else "" for c in df.columns]
    up = [h.upper() for h in headers]

    def _first(name: str) -> Optional[int]:
        return up.index(name) if name in up else None

    # kolom hari: cari ulang dari header aktual (posisi = posisi peek)
    # v3.4: header 'Sum of N' juga diterima (sheet SO BULAN LALU)
    days = {}
    for i, h in enumerate(up):
        if h in ("", "NONE", "NAN"):
            continue
        d = _parse_day_header(h)
        if d is not None:
            days[i] = d
    # mode "lalu" (mirror M): hanya hari 25..31, dinegasikan
    if mode != "berjalan":
        days = {i: d for i, d in days.items() if 25 <= d <= 31}
    if not days:
        return None

    # base columns — posisi (dari kolom, bukan nama file)
    sel = pd.DataFrame(index=df.index)
    for name in _BASE_COLS:
        pos = _first(name)
        if pos is not None:
            col = df.iloc[:, pos]
        else:
            col = pd.Series(None, index=df.index, dtype=object)
        # strip spasi tepi — SATUAN 'GR ' → 'GR' (57 nilai di data user punya
        # trailing space; tanpa strip, baris GR bocor ke tab Deviasi PCS)
        stripped = col.astype(str).str.strip()
        sel[name] = stripped.where(col.notna(), other=None)

    # v3.9.49 — kolom KATEGORI rekap mentah dibawa BILA ADA di sheet
    # (nilai dipakai append1 sebagai sumber kategori PRIORITAS atas
    # master '21. DBS Kategori'; schema lama tanpa kolom ini tetap
    # didukung — output tak berkolom KATEGORI).
    _kat_pos = _first("KATEGORI")
    if _kat_pos is not None:
        _kcol = df.iloc[:, _kat_pos]
        sel["KATEGORI"] = (_kcol.astype(str).str.strip()
                           .where(_kcol.notna(), other=None))

    # kolom hari → numeric
    # FIX 6f-03 (audit 6-f): dua posisi bisa parse ke HARI SAMA (mis.
    # '5' + 'Sum of 5' pada sheet pivot, atau duplikat kolom '5'/'5.1'
    # hasil mangling pd.read_excel) — assignment lama MENIMPA senyap
    # (nilai kolom pertama hilang tanpa jejak; kolom TERAKHIR menang).
    # Resolve eksplisit + log:
    # - tepat SATU kolom agregat pivot ('Sum of N') di antara duplikat
    #   → PAKAI agregat — blok 'Sum of N' adalah kolom rekap resmi
    #   (workbook real 'SO BULAN LALU': 'Sum of 1'.. = nilai SO, kolom
    #   plain '01'/'02'/'03' di ujung = kolom bantu avg dgn nilai
    #   BERBEDA — menjumlah keduanya = kacau);
    # - sisanya (2+ plain / 2+ agregat) → SUM (min_count=1: semua-NaN
    #   tetap NaN → terbuang dropna bawah, kehadiran data terjaga).
    _pos_by_day: dict = {}
    for _pos, _d in days.items():
        _pos_by_day.setdefault(_d, []).append(_pos)
    _dup_days = {_d for _d, _ps in _pos_by_day.items() if len(_ps) > 1}
    _done_dup: set = set()
    for pos, d in days.items():
        if d not in _dup_days:
            sel[str(d)] = safe_to_numeric(df.iloc[:, pos])
            continue
        if d in _done_dup:
            continue                 # sudah di-resolve di iterasi pertama
        _done_dup.add(d)
        _ps = _pos_by_day[d]
        _aggs = [p for p in _ps if up[p].startswith("SUM OF")]
        if len(_aggs) == 1:
            _use = _aggs[0]
            sel[str(d)] = safe_to_numeric(df.iloc[:, _use])
            _skip = [up[p] for p in _ps if p != _use]
            print(f"  [WARNING] fn_rekap_mentah: hari {d} punya {len(_ps)} "
                  f"kolom ({', '.join(up[p] for p in _ps)}) — memakai "
                  f"agregat '{up[_use]}' (dilewati: {', '.join(_skip)})")
        else:
            _vals = df.iloc[:, _ps].apply(safe_to_numeric)
            sel[str(d)] = _vals.sum(axis=1, min_count=1)
            print(f"  [WARNING] fn_rekap_mentah: hari {d} punya {len(_ps)} "
                  f"kolom ({', '.join(up[p] for p in _ps)}) — dijumlahkan "
                  "(SUM semua kolom)")

    # filter JENIS (case-insensitive — mirror jenis_filter alur lama)
    if jenis_filter is not None:
        jf = {str(j).strip().upper() for j in jenis_filter}
        jj = sel["JENIS"].fillna("").astype(str).str.strip().str.upper()
        sel = sel[jj.isin(jf)]
        if sel.empty:
            return None

    # unpivot hari → (Attribute, Value)
    # v3.9.49 — KATEGORI (bila ada) ikut sebagai id_vars supaya tiap
    # baris long membawa kategori rekap barangnya.
    _idv = [c for c in _BASE_COLS if c in sel.columns]
    if "KATEGORI" in sel.columns:
        _idv.append("KATEGORI")
    day_names = [str(d) for d in sorted(set(days.values()))]
    melted = sel.melt(
        id_vars=_idv,
        value_vars=day_names,
        var_name="Attribute",
        value_name="Value"
    )
    melted["Attribute"] = safe_to_numeric(melted["Attribute"]).astype("Int64")
    if mode != "berjalan":
        melted["Attribute"] = (-melted["Attribute"]).astype("Int64")
    melted["Value"] = safe_to_numeric(melted["Value"])
    melted = melted.dropna(subset=["Value"]).reset_index(drop=True)

    out_cols = ([c for c in _BASE_COLS if c in melted.columns]
                + (["KATEGORI"] if "KATEGORI" in melted.columns else [])
                + ["Attribute", "Value"])
    return melted[out_cols]


def _promote_at(df: pd.DataFrame, hr: int) -> pd.DataFrame:
    """Baris hr jadi header (duplikat diberi suffix _1/_2, None → ColumnN).

    v3.7 ENGINE TURBO: dipakai jalur single-parse (calamine) — sheet
    dibaca SEKALI (header=None), deteksi header + promote dilakukan di
    memori. Ekuivalen pd.read_excel(header=hr) untuk kebutuhan
    _combined_to_long (pencarian kolom posisional via nama pertama)."""
    headers = df.iloc[hr].tolist()
    body = df.iloc[hr + 1:].reset_index(drop=True)
    new_cols, seen = [], {}
    for i, h in enumerate(headers):
        if h is None or (isinstance(h, float) and pd.isna(h)):
            h = f"Column{i + 1}"
        h = str(h)
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        new_cols.append(h)
    body.columns = new_cols
    return body


def _read_combined_file(file_path: str, mode: str,
                        jenis_filter: Optional[List[str]],
                        sheet_filter=None) -> Optional[pd.DataFrame]:
    """Cari sheet rekap-mentah (combined) dalam satu file; baca → long.

    sheet_filter(sn) → bool: filter nama sheet (dipakai pemisah bulan
    berjalan vs bulan lalu saat scan folder induk/RootPath — v3.4).

    v3.7 ENGINE TURBO: dgn engine calamine, sheet dibaca SEKALI penuh
    (peek nrows=8 di calamine mem-parse seluruh sheet juga — 0,17s vs
    full 0,25s — jadi peek+full = 2× parse sia-sia). Deteksi header
    dilakukan pada 6 baris pertama frame yang SUDAH terbaca, lalu
    header di-promote di memori (_promote_at). Jalur openpyxl tetap
    peek-dulu (peek-8 baris murah di openpyxl read-only)."""
    if file_path.lower().endswith(".xlsb") and _xlsb_engine() is None:
        print(f"  [fn_rekap_mentah] SKIP {os.path.basename(file_path)}: file .xlsb "
              "butuh package pyxlsb/python-calamine (pip install pyxlsb)")
        return None
    if file_path.lower().endswith(".xlsb"):
        engine = _xlsb_engine()          # calamine > pyxlsb
    else:
        engine = _EXCEL_ENGINE           # calamine bila ada, else default
    engine_kwargs = {"engine": engine} if engine else {}
    single_parse = engine == "calamine"
    for sn in _list_sheet_names(file_path):
        if sheet_filter is not None and not sheet_filter(sn):
            continue
        raw = None
        try:
            if single_parse:
                # v3.9.37 — rutekan lewat fn_buka_sheet (cache bacaan file
                # sumber: Refresh Terpilih tak membaca ulang workbook
                # gabungan yang tak berubah; engine + kwargs identik).
                raw = fn_buka_sheet(file_path, sn, raw=True)
                peek = raw.iloc[:8]
            else:
                peek = pd.read_excel(file_path, sheet_name=sn, header=None,
                                     nrows=8, dtype=object, **engine_kwargs)
        except Exception:
            continue
        det = _detect_rekap_header(peek)
        if det is None:
            continue
        hr, _day_pos = det
        try:
            if single_parse and raw is not None:
                df = _promote_at(raw, hr)
                raw = None               # bebaskan memori
            else:
                # v3.9.37 — jalur openpyxl (tanpa calamine) ikut lewat
                # fn_buka_sheet = ter-cache (header=hr, dtype=object,
                # engine sama — pemetaan argumen identik pd.read_excel).
                df = fn_buka_sheet(file_path, sn, header_row=hr)
        except Exception as e:
            print(f"  [fn_rekap_mentah] Gagal baca sheet '{sn}' "
                  f"{os.path.basename(file_path)}: {e}")
            continue
        out = _combined_to_long(df, mode, jenis_filter)
        if out is not None and not out.empty:
            print(f"  [fn_rekap_mentah] Combined workbook: {os.path.basename(file_path)} "
                  f"» sheet '{sn}' (header baris {hr + 1}) → {len(out)} baris "
                  f"(NAMA RESTO dari kolom)")
            return out
    return None


def _log_sisa_workbook(sisa_files: list) -> None:
    """v3.9.42 — AUDIT FIX (61-a, F6): sebut file Excel LAIN di folder
    yang sama yang TIDAK pernah dibaca (scan berhenti di workbook
    gabungan pertama yang cocok — first-match-wins). Dulu diabaikan
    SENYAP: duplikat workbook / export ganda di folder tidak kelihatan
    (data tidak dijumlah — hanya workbook pertama yang dipakai — tapi
    user tidak tahu workbook mana yang menang)."""
    if sisa_files:
        nama = ", ".join(os.path.basename(x) for x in sisa_files)
        print(f"  [INFO] fn_rekap_mentah: {len(sisa_files)} file lain di "
              f"folder sama diabaikan (first-match-wins): {nama}")


def _read_combined_rekap(folder_path: str, mode: str,
                         jenis_filter: Optional[List[str]]) -> Optional[pd.DataFrame]:
    """Fallback: cari workbook gabungan ber-schema rekap mentah.

    Urutan scan (v3.4):
    1. folder itu sendiri — file gabungan diletakkan langsung di folder
       RekapBerjalan/RekapLalu.
    2. folder induk / RootPath — file gabungan user sering disimpan di
       RootPath.

    v3.9.42 — AUDIT FIX (61-a, F5): pemisah bulan via NAMA SHEET kini
    berlaku utk KEDUA langkah (dulu hanya langkah-2): workbook gabungan
    yang kebetulan berada DI DALAM folder RekapBerjalan/RekapLalu juga
    difilter — mode 'berjalan' tidak lagi bisa menelan sheet 'SO BULAN
    LALU' (data bulan tercampur senyap):
    - mode "berjalan": SKIP sheet ber-nama "LALU"
    - mode "lalu"    : HANYA sheet ber-nama "LALU"
    """
    # v3.9.42 — filter dibangun SEKALI, dipakai langkah-1 DAN langkah-2
    if mode == "berjalan":
        sheet_filter = lambda sn: "LALU" not in sn.upper()  # noqa: E731
    else:
        sheet_filter = lambda sn: "LALU" in sn.upper()     # noqa: E731

    # 1. folder itu sendiri (v3.9.42 — kini ikut filter nama sheet)
    files_here = _list_excel_files(folder_path)
    for i, f in enumerate(files_here):
        out = _read_combined_file(f, mode, jenis_filter,
                                  sheet_filter=sheet_filter)
        if out is not None:
            _log_sisa_workbook(files_here[i + 1:])
            return out
    # 2. folder induk / RootPath (dengan filter nama sheet)
    parent = os.path.dirname(os.path.abspath(folder_path))
    if parent and os.path.isdir(parent) \
            and os.path.abspath(parent) != os.path.abspath(folder_path):
        files_parent = _list_excel_files(parent)
        for i, f in enumerate(files_parent):
            out = _read_combined_file(f, mode, jenis_filter,
                                      sheet_filter=sheet_filter)
            if out is not None:
                _log_sisa_workbook(files_parent[i + 1:])
                return out
    print(f"  [fn_rekap_mentah] WARNING: tidak ada file per-resto 'REKAP MENTAH' "
          f"dan tidak ada sheet gabungan rekap-mentah di: {folder_path}")
    return None


def fn_rekap_mentah(folder_path: str, mode: str, jenis_filter: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Mirror M: fnRekapMentah(folderPath, mode, optional jenisFilter).

    mode: "berjalan" (tanggal 1..31) atau "lalu" (tanggal 25..31, dinegasikan).
    jenis_filter: list JENIS yang di-keep. None = no filter.

    Output columns: NAMA RESTO, SOURCE DATA, JENIS, STATUS, NAMA BARANG, SATUAN, Attribute, Value
    """
    # === STEP 1: fnCombineFolder(folderPath, "REKAP MENTAH") dengan doPromote=null ===
    # raw=True: baca tanpa header, add_name_col=True: tambah kolom "Name" (file name)
    expand = fn_combine_folder(folder_path, "REKAP MENTAH", raw=True, add_name_col=True)
    if expand.empty:
        # v3.3.1 FALLBACK: sumber gabungan (.xlsb / sheet apa pun ber-schema
        # rekap mentah, NAMA RESTO dari kolom) — fix "Saldo SO kosong semua"
        combined = _read_combined_rekap(folder_path, mode, jenis_filter)
        if combined is not None:
            return combined
        return pd.DataFrame(columns=_BASE_COLS + ["Attribute", "Value"])

    # === STEP 2: prom = Table.PromoteHeaders(expand, [PromoteAllScalars = true]) ===
    # Row 0 (file1's header row) → column names
    # Name column → renamed to file1's name (e.g., "MLGPAR.xlsx")
    prom = promote_headers(expand)

    # === STEP 3: firstColumn = Table.ColumnNames(prom){0} ===
    # firstColumn = file1's name (e.g., "MLGPAR.xlsx")
    first_column = prom.columns[0]

    # === STEP 4: ren = Table.RenameColumns(prom, {{firstColumn, "NAMA RESTO"}}) ===
    ren = prom.rename(columns={first_column: "NAMA RESTO"})

    # === STEP 4b: Handle duplicate "NAMA RESTO" columns ===
    # After rename, there may be TWO "NAMA RESTO" columns:
    #   1. Former Name column (file names) at position 0 — this is the one we want
    #   2. Sheet's original "NAMA RESTO" column (from PromoteHeaders) at position 1
    # M's Table.SelectColumns keeps the FIRST occurrence.
    # In pandas, we select by POSITION (not name) to keep only the first.
    cols = ren.columns.tolist()
    keep_positions = []
    seen_nama_resto = False
    for i, c in enumerate(cols):
        if c == "NAMA RESTO":
            if not seen_nama_resto:
                seen_nama_resto = True
                keep_positions.append(i)
            # else: skip duplicate (position 1+)
        else:
            keep_positions.append(i)
    ren = ren.iloc[:, keep_positions]

    # === STEP 5: clean = NAMA RESTO → Text.BeforeDelimiter(_, ".") ===
    # NAMA RESTO column berisi file names (e.g., "MLGPAR.xlsx", "BDGUKU.xlsx")
    # Text.BeforeDelimiter(_, ".") → "MLGPAR", "BDGUKU"
    # Vectorized: .str.split(".").str[0]
    nama_resto_series = ren["NAMA RESTO"]
    if isinstance(nama_resto_series, pd.DataFrame):
        # Still a DataFrame if duplicate wasn't resolved — take first column
        nama_resto_series = nama_resto_series.iloc[:, 0]
    ren["NAMA RESTO"] = nama_resto_series.astype(str).str.split(".").str[0]

    # === STEP 6: base columns + days ===
    base = ["NAMA RESTO", "SOURCE DATA", "JENIS", "STATUS", "NAMA BARANG", "SATUAN"]
    # v3.9.49 — kolom KATEGORI rekap mentah dibawa BILA ADA di sheet
    # per-resto (schema lama tanpa kolom ini tetap didukung; mirror
    # jalur combined _combined_to_long).
    # v3.9.50 — [audit 3-b] deteksi kini WHITESPACE-TOLERANT (strip —
    # parity jalur combined yang menormalisasi header; sheet per-resto
    # legacy 'KATEGORI ' trailing-space tak lagi dibuang senyap →
    # barangnya tetap dapat kategori rekap).
    _kat_src = next((c for c in ren.columns
                     if str(c).strip().upper() == "KATEGORI"), None)
    if _kat_src is not None:
        if _kat_src != "KATEGORI":
            ren = ren.rename(columns={_kat_src: "KATEGORI"})
        base = base + ["KATEGORI"]
    if mode == "berjalan":
        days = [str(d) for d in range(1, 32)]
    else:  # "lalu"
        days = [str(d) for d in range(25, 32)]

    # === STEP 7: sel = Table.SelectColumns(clean, base & days) ===
    all_cols = base + days
    available = [c for c in all_cols if c in ren.columns]
    sel = ren[available].copy()

    # === STEP 8: fil = filter JENIS (if jenisFilter given) ===
    if jenis_filter is not None:
        # v3.9.42 — AUDIT FIX (61-a, F6): normalisasi KEDUA sisi
        # (fillna→strip→upper — mirror _combined_to_long jalur combined)
        # — dulu exact-case: JENIS 'so' / 'So ' di file user tertolak
        # SENYAP, baris hilang tergantung kapitalisasi file.
        jf = {str(j).strip().upper() for j in jenis_filter}
        jj = (sel["JENIS"].fillna("").astype(str).str.strip()
              .str.upper())
        sel = sel[jj.isin(jf)].copy()

    # === STEP 9: Type cast: base → text, days → number ===
    # Vectorized text conversion
    for col in base:
        if col in sel.columns:
            sel[col] = safe_to_str(sel[col])
    for col in days:
        if col in sel.columns:
            sel[col] = safe_to_numeric(sel[col])

    # === STEP 10: up = Table.Unpivot(typed, days, "Attribute", "Value") ===
    available_days = [d for d in days if d in sel.columns]
    if not available_days:
        return pd.DataFrame(columns=base + ["Attribute", "Value"])

    up = sel.melt(
        id_vars=[c for c in base if c in sel.columns],
        value_vars=available_days,
        var_name="Attribute",
        value_name="Value"
    )

    # === STEP 11: final type conversion ===
    # berjalan → Attribute as Int64; lalu → Attribute = -Number.From(Attribute)
    up["Attribute"] = safe_to_numeric(up["Attribute"])
    if mode == "berjalan":
        up["Attribute"] = up["Attribute"].astype("Int64")
    else:
        up["Attribute"] = (-up["Attribute"]).astype("Int64")

    # Value → numeric
    up["Value"] = safe_to_numeric(up["Value"])

    # Drop rows where Value is null (M's Table.Unpivot doesn't create rows for nulls)
    up = up.dropna(subset=["Value"]).reset_index(drop=True)

    return up
