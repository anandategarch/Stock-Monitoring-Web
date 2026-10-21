"""
fn_4217.py — Mirror persis fn4217 di M code.
Kuantitas Barang per Gudang (modul 42.17) → SALDO AWAL.
OPTIMIZED: vectorized text operations.

v3.9.32 (user: "filter lebih awal data 42.17 pakai kolom kategori barang
[whitelist 5 kategori]" + barang 42.17-only tak muncul di Deviasi GR):
- KATEGORI BARANG dibaca sebagai KOLOM id SEBELUM melt (dulu kolom
  kategori/satuan/kode ter-melt jadi pseudo-baris NAMA RESTO → kosong →
  terbuang senyap). Kategori ber-pola header grup (nilai hanya di baris
  pertama tiap grup — sisanya NaN) → forward-fill.
- FILTER WHITELIST kategori DITERAPKAN SEBELUM melt (beban pipeline turun;
  default 5+1 kategori produksi — daftar BISA DIUBAH di config.json key
  "KategoriBarang4217"; file tanpa kolom kategori → tanpa filter +
  peringatan log; hasil 0 baris → filter di-bypass otomatis + peringatan
  [safety-net salah konfigurasi]).
- NAMA SATUAN per barang ikut keluar sebagai kolom SATUAN (fallback utk
  pasangan TANPA rekap — barang 42.17-only kini punya satuan di tabel
  Deviasi GR/PCS; pasangan ber-rekap tetap memakai satuan rekap).
- Matching kategori: normalisasi buang SEMUA whitespace + upper
  ('01. COST - PACKAGING - TIDAK BOLEH' == '01.COST-PACKAGING-TIDAKBOLEH')
  + PREFIX match supaya varian spasi/nama file user tetap cocok.

v3.9.39 (user: "di tab deviasi GR kok tidak ada Bumbu Pasta Kuah? padahal
  di file 42.17 ada. Dulu pernah aku bilang look up nama barang harus dua
  arah tidak hanya nama barang yang ada di file atau sheet Rekap Mentah
  tapi juga di file 42.17"):
- LOOKUP DUA ARAH PENUH: whitelist kategori TIDAK BOLEH memutus pasangan
  barang yang ber-transaksi — barang yang namanya terdaftar di sumber
  lain (Rekap Mentah SO/BARANG MASUK, IN, OUT, BARANG KELUAR) selalu
  lolos filter walau kategorinya di luar whitelist (saldo awal wajib
  masuk pipeline — kalau tidak, Sistem/Deviasi pasangan itu salah).
  Param protected_barangs diisi build_append1 dari gabungan sumber lain.
- LOG TRANSPARAN: barang yang benar-benar terbuang whitelist (tanpa
  pasangan) kini DISEBUT NAMANYA di log — tidak lenyap senyap lagi
  (akar keluhan "barang ada di 42.17 tapi tidak muncul").
- SHEET RESOLVE DEFENSIVE: nama sheet export Accurate bisa berbeda antar
  versi ('#42.17. Kuantitas Barang per Gu' terpotong 31 karakter).
  Bila nama persis tidak ada di file → fallback sheet berprefiks '#42.17'
  + [INFO] log (pola _resolve_lalu_sheet queries) — bukan 0 baris senyap.

v3.9.41 (user: "100383 BUMBU PASTA KUAH masih belum ada di program ini
  padahal pada gudang MLGPAR di file 42.17 ada saldo nya dan harusnya
  masuk. Cek deep"):
- AKAR (probe E2E data rekap nyata + snapshot 41.09 Accurate): pipeline
  saldo-only SEHAT — pasangan TAMPIL ketika kategorinya lolos whitelist
  (probe: kategori '10.FOOD [WIP] - COM V.2' → Sistem 84.000 tampil).
  Yang GAGAL: kategori item lama tak cocok whitelist yang mem-pin versi:
  (a) kategori legacy nyata '10.FOOD [RM] - COM- TIDAK BOLEH' &
      '10.FOOD [WIP] - COM TIDAK BOLEH' (±200 item lama bersaldo;
      v3.9.32 hanya menambahkan varian PACKAGING-TIDAK BOLEH —
      varian FOOD-nya TERLEWAT → saldo terbuang senyap);
  (b) drift versi ('10.FOOD [WIP] - COM V.3 BARU' ≠ prefix '…V.2').
- MATCHING VERSI-TOLERAN (_fam_kat/_kat_match): token versi ujung
  (V.1/V.2/V.3 BARU/V.20…) dibuang dari KEDUA sisi sebelum prefix-
  match → drift versi & varian '- TIDAK BOLEH' family sama lolos;
  family lain (SUPPLIES/ASSET/02.COST) tetap terbuang (whitelist tetap
  filter scope, bukan free-pass). Config user yang mem-pin daftar lama
  TETAP tertolong oleh family match.
- DEFAULT WHITELIST + 2 kategori FOOD legacy (mirror niat v3.9.32
  "item lama yang masih bersaldo tetap terpantau").

v3.9.42 — AUDIT FIX (61-a):
- F7: fallback kolom 'Nama Barang' (kolom PERTAMA) kini WAJIB teriak
  WARNING (dulu senyap — nyasar ke 'Kode Barang' dsb. tanpa jejak);
  rename 'KATEGORI BARANG'/'SATUAN AWAL'/'Nama Barang' diberi guard
  tabrakan (dua kolom yang menormalkan ke nama sama → rename menghasilkan
  kolom GANDA → prom[col] = DataFrame → crash).
- F1 (defense-in-depth): kategori_whitelist berupa STRING dibungkus
  jadi daftar 1-elemen sebelum dipakai — string diiterasi per-karakter
  oleh prefix-match → 1 karakter cocok hampir semua kategori (kelas
  bug item 100383; config.py kini memvalidasi — ini jaring kedua utk
  pemanggil lain).
"""
import re

import pandas as pd

from .helpers import _list_excel_files, _list_sheet_names, fn_combine_folder

# Nama sheet standar 42.17 (export Accurate) — v3.9.33 default param;
# queries.py me-resolve key config Sheets['SaldoAwal4217'] (config lama
# tanpa key tetap dapat nilai ini).
SHEET_4217 = "#42.17. Kuantitas Barang per Gu"

# Kandidat nama kolom (beda versi export Accurate — resolusi defensive)
_KANDIDAT_KATEGORI = ["Kategori Barang", "Kategori"]
_KANDIDAT_SATUAN = ["Nama Satuan", "Satuan"]

# Default whitelist kategori produksi (config.json "KategoriBarang4217"
# menimpa; prefix-match + case/space-insensitive). 5 kategori aktif V.2 +
# varian PACKAGING lama '- TIDAK BOLEH' (item lama yang masih bersaldo
# tetap terpantau — mencegah saldo hilang senyap).
# v3.9.41 — + 2 varian FOOD legacy '- TIDAK BOLEH' (temuan probe
# BUMBU PASTA KUAH kode 100383: kategori Accurate nyata berisi
# '10.FOOD [RM] - COM- TIDAK BOLEH' & '10.FOOD [WIP] - COM TIDAK
# BOLEH' — item lama bersaldo; tanpa ini saldo awalnya terbuang senyap
# → barang "tidak muncul" di Deviasi GR). Matching kini juga VERSI-
# TOLERAN (lihat _fam_kat) — drift 'V.3 BARU' dsb. tetap cocok.
DEFAULT_KATEGORI_WHITELIST = [
    "00.COST",
    "01.COST - PACKAGING V.2",
    "01. COST - PACKAGING - TIDAK BOLEH",
    "10.FOOD [BUMBU] - COM V.2",
    "10.FOOD [RM] - COM V.2",
    "10.FOOD [RM] - COM- TIDAK BOLEH",
    "10.FOOD [WIP] - COM V.2",
    "10.FOOD [WIP] - COM TIDAK BOLEH",
]

OUTPUT_COLUMNS = ["Nama Barang", "NAMA RESTO", "Value", "Tanggal",
                  "JENIS", "SATUAN"]


def _norm_kat(v) -> str:
    """Kategori → '01.COST-PACKAGING-TIDAKBOLEH' (buang SEMUA whitespace,
    upper); None/NaN/blank → ''."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip().upper()
    return "".join(s.split()) if s else ""


def _norm_barang(v) -> str:
    """v3.9.39 — nama barang → kunci dua arah (buang SEMUA whitespace +
    upper): 'BUMBU PASTA KUAH (V.20)' == 'Bumbu  Pasta  Kuah (V.20)'.
    Dipakai match barang 42.17 ↔ sumber lain (rekap/IN/out/BK)."""
    return _norm_kat(v)


# v3.9.41 — token versi di ujung kategori ternormalisasi: 'V.2',
# 'V.3BARU', 'V.20', 'V.1BARU'… (family Accurate: 'COM V.2' /
# 'COM V.3 BARU' / 'COM TIDAK BOLEH' — versi hanya penanda gelombang
# item, bukan identitas family produksi).
_VERSI_UJUNG = re.compile(r"V\.?\d+(BARU)?$")

# FIX 6f-01 (audit 6-f) — deteksi kolom RINGKASAN file 42.17 (kolom
# total/jumlah ber-kurung, mis. 'TOTAL (SEMUA GUDANG)' → resto phantom
# 'SEMUA GUDANG' + saldo dobel). Word-boundary + case-insensitive
# supaya nama gudang legit ('GUDANG BDGUKU (BDGUKU)',
# 'RESTO MALANG (MLGPAR)') TIDAK kena.
_SUMMARY_COL_RE = re.compile(r"\b(TOTAL|JUMLAH|SUB\s?TOTAL|GRAND|SEMUA)\b",
                             re.IGNORECASE)


def _fam_kat(v_norm: str) -> str:
    """v3.9.41 — kategori ternormalisasi → FAMILY (token versi ujung
    dibuang): '10.FOOD[WIP]-COMV.3BARU' → '10.FOOD[WIP]-COM'.

    Dipakai matching whitelist VERSI-TOLERAN: file dengan kategori
    gelombang baru/lama ('V.1', 'V.3 BARU', tanpa versi) tetap cocok
    dgn entri whitelist family yang sama — whitelist tidak lagi
    "kedaluwarsa" hanya karena Accurate menaikkan versi kategori
    (akar 'BUMBU PASTA KUAH 100383 masih belum ada di program')."""
    return _VERSI_UJUNG.sub("", v_norm)


def _kat_match(kat_norm: str, wl_norm: list) -> bool:
    """v3.9.41 — kategori file lolos whitelist bila:
    (a) prefix persis (perilaku lama — '01.COST-PACKAGING-TIDAKBOLEH'
        .startswith('01.COST-PACKAGING')), ATAU
    (b) prefix FAMILY versi-toleran: _fam_kat(kat).startswith(
        _fam_kat(whitelist)) — menutup drift versi ('V.2' vs 'V.3 BARU'
        vs tanpa-versi) & varian '- TIDAK BOLEH' family sama
        ('10.FOOD[WIP]-COMTIDAKBOLEH'.startswith('10.FOOD[WIP]-COM')).
    Family lain (SUPPLIES / ASSET / 02.COST-BAHAN-PEMBANTU) tetap
    TIDAK cocok — whitelist tetap filter scope, bukan free-pass."""
    for w in wl_norm:
        if kat_norm.startswith(w):
            return True
        if _fam_kat(kat_norm).startswith(_fam_kat(w)):
            return True
    return False


def _resolve_sheet_4217(folder_path: str, sheet_name: str) -> str:
    """v3.9.39 — resolusi nama sheet 42.17 DEFENSIVE (pola
    _resolve_lalu_sheet queries):
    1. sheet persis ada di salah satu file → pakai (perilaku lama);
    2. tidak ada → sheet pertama berprefiks '#42.17' + [INFO] log
       (export Accurate memotong nama sheet 31 karakter — '…per Gu'
       bisa jadi '…per Gudang' dsb.);
    3. tidak ada juga → pertahankan nama (WARNING per-file dari
       fn_combine_folder tetap tercetak — bukan senyap total)."""
    try:
        files = _list_excel_files(folder_path)
    except (OSError, ValueError):
        return sheet_name
    if not files:
        return sheet_name
    for f in files:
        if sheet_name in _list_sheet_names(f):
            return sheet_name
    pref = "#42.17"
    for f in files:
        for name in _list_sheet_names(f):
            if str(name).strip().lower().startswith(pref.lower()):
                print(f"    [INFO] 4217: sheet '{name}' dipakai "
                      f"(nama '{sheet_name}' tidak ada di file)")
                return str(name)
    return sheet_name


def _find_col(prom_columns, kandidat):
    """Kolom pertama yang cocok (case-insensitive) dari kandidat nama."""
    if prom_columns is None:
        return None
    lookup = {str(c).strip().lower(): c for c in prom_columns}
    for k in kandidat:
        c = lookup.get(str(k).strip().lower())
        if c is not None:
            return c
    return None


def fn_4217(folder_path: str, kategori_whitelist: list | None = None,
            sheet_name: str = SHEET_4217,
            protected_barangs: list | set | None = None) -> pd.DataFrame:
    """
    Mirror M: fn4217(folderPath).

    kategori_whitelist: list kategori yang LOLOS (prefix-match normalisasi;
    None/kosong → tanpa filter). Sumber default: config "KategoriBarang4217".

    protected_barangs: v3.9.39 — nama barang yang ber-pasangan di sumber
    lain (rekap/IN/out/BK) — barisnya SELALU lolos whitelist (lookup dua
    arah: saldo awal tidak boleh hilang karena kategorinya di luar
    whitelist, else Sistem pasangan itu salah). Normalisasi buang-semua-
    whitespace + upper.

    sheet_name: v3.9.33 — AUDIT FIX (48-a): nama sheet bisa diatur dari
    config.json key Sheets['SaldoAwal4217'] (dihantarkan queries.query_4217;
    default = nama sheet export standar — pemanggil lama tak berubah).
    v3.9.39: bila nama persis tidak ada di file → fallback prefiks '#42.17'.

    Output columns: Nama Barang, NAMA RESTO, Value, Tanggal, JENIS, SATUAN
    (SATUAN = 'Nama Satuan' file per barang; file tanpa kolom → '').
    """
    # v3.9.39 — sheet resolve defensive (nama export beda ≠ 0 baris senyap)
    sheet_resolved = _resolve_sheet_4217(folder_path, sheet_name)

    # expand + Skip(3) + Promote = header=4
    # v3.9.33 — AUDIT FIX (48-a): ffill kategori PER FILE (ffill_cols) —
    # dulu ffill pada frame CONCAT membuat grup pertama file-2 mewarisi
    # kategori TERAKHIR file-1 (bleed lintas file). Mirror pola per-file
    # fn_4109.
    prom = fn_combine_folder(folder_path, sheet_resolved, header_row=4,
                             ffill_cols=_KANDIDAT_KATEGORI)
    if prom.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # up = Table.UnpivotOtherColumns(prom, {"Nama Barang"}, "NAMA RESTO", "Value")
    # Cari kolom "Nama Barang"
    nama_barang_col = None
    for c in prom.columns:
        if str(c).strip().lower() == "nama barang":
            nama_barang_col = c
            break

    if nama_barang_col is None:
        nama_barang_col = prom.columns[0]
        # v3.9.42 — AUDIT FIX (61-a, F7): fallback senyap menyulitkan
        # diagnosis — kolom pertama bisa kolom APA PUN ('Kode Barang',
        # 'No', …) → Nama Barang nyasar tanpa jejak. WAJIB teriak supaya
        # user melihat kenapa 42.17 salah-baca.
        print(f"[WARNING] 4217 {sheet_resolved}: kolom 'Nama Barang' tak "
              f"ditemukan — memakai kolom pertama '{nama_barang_col}'")

    if nama_barang_col != "Nama Barang":
        # v3.9.42 — AUDIT FIX (61-a, F7): guard tabrakan rename — sheet
        # dgn dua kolom yang sama-sama menormalkan ke 'nama barang'
        # (mis. 'Nama Barang' + 'nama barang') membuat rename menghasilkan
        # 2 kolom bernama sama → prom['Nama Barang'] = DataFrame → crash.
        # Buang dulu kolom ejaan persis target (yang dipertahankan =
        # kolom pilihan pencarian di atas, satu-satunya yang di-rename).
        if "Nama Barang" in prom.columns:
            prom = prom.drop(columns=["Nama Barang"])
        prom = prom.rename(columns={nama_barang_col: "Nama Barang"})

    # v3.9.32 — kolom KATEGORI BARANG + NAMA SATUAN sebagai id SEBELUM melt
    kat_col = _find_col(prom.columns, _KANDIDAT_KATEGORI)
    sat_col = _find_col(prom.columns, _KANDIDAT_SATUAN)

    if kat_col is not None and kat_col != "KATEGORI BARANG":
        # v3.9.42 — AUDIT FIX (61-a, F7): guard tabrakan rename — bila
        # sheet punya 'Kategori'/'Kategori Barang' DAN kolom lain bernama
        # persis 'KATEGORI BARANG' (ejaan beda, key lookup sama → _find_col
        # bisa memilih yang bukan ejaan persis), rename menghasilkan 2
        # kolom 'KATEGORI BARANG' → prom[kat_col] = DataFrame → crash di
        # map whitelist. Buang kolom ejaan persis target dulu.
        if "KATEGORI BARANG" in prom.columns:
            prom = prom.drop(columns=["KATEGORI BARANG"])
        prom = prom.rename(columns={kat_col: "KATEGORI BARANG"})
        kat_col = "KATEGORI BARANG"
    if sat_col is not None and sat_col != "SATUAN AWAL":
        # v3.9.42 — AUDIT FIX (61-a, F7): guard tabrakan rename (mirror
        # KATEGORI BARANG di atas) utk kolom satuan.
        if "SATUAN AWAL" in prom.columns:
            prom = prom.drop(columns=["SATUAN AWAL"])
        # nama sementara supaya tidak bentrok dgn output "SATUAN"
        prom = prom.rename(columns={sat_col: "SATUAN AWAL"})
        sat_col = "SATUAN AWAL"

    # Kategori ber-pola header grup: nilai hanya di baris pertama grup →
    # forward-fill PER FILE (v3.9.33 — AUDIT FIX 48-a, ffill_cols di
    # fn_combine_folder di atas — BUKAN ffill frame concat: file-2 tidak
    # boleh mewarisi kategori ekor file-1; baris leading-NaN pra-grup
    # pertama per file dibiarkan NaN → terbuang oleh filter whitelist).

    # --- FILTER KATEGORI WHITELIST (SEBELUM melt — "lebih awal") ---
    prom_raw = prom.copy()          # utk safety-net bypass di bawah
    _kat_was = kat_col is not None
    _sat_was = sat_col
    # v3.9.42 — AUDIT FIX (61-a, F1 defense-in-depth): whitelist STRING
    # (config salah tulis / pemanggil lama) dulu diiterasi PER-KARAKTER
    # oleh prefix-match di bawah → prefix 1 karakter → hampir SEMUA
    # kategori lolos (kelas bug item 100383). Bungkus jadi daftar
    # 1-elemen di sini — jaring kedua setelah validasi tipe config.py,
    # supaya jalur pemanggil manapun aman.
    if isinstance(kategori_whitelist, str):
        print("    [WARNING] 4217: kategori_whitelist STRING "
              f"'{kategori_whitelist}' diperlakukan sebagai 1 kategori "
              "(harusnya daftar — cek config.json 'KategoriBarang4217')")
        kategori_whitelist = [kategori_whitelist]
    if kat_col is not None and kategori_whitelist:
        wl_norm = [_norm_kat(k) for k in kategori_whitelist
                   if _norm_kat(k)]
        if wl_norm:
            kat_norm = prom[kat_col].map(_norm_kat)
            # prefix-match: entri whitelist '01.COST - PACKAGING V.2'
            # cocok dgn kategori file yang berawal sama (normalisasi).
            # v3.9.41 — + VERSI-TOLERAN family match (_fam_kat): drift
            # 'V.3 BARU' / varian '- TIDAK BOLEH' family sama tetap
            # lolos — whitelist tak memutus saldo barang lama hanya
            # karena versi kategori dinaikkan di Accurate.
            keep = kat_norm.map(lambda v: _kat_match(v, wl_norm))
            # v3.9.39 — LOOKUP DUA ARAH (user: "look up nama barang harus
            # dua arah ... Rekap Mentah ↔ 42.17"): barang yang
            # ber-pasangan di sumber lain (rekap SO/BM, IN, OUT, BK)
            # SELALU lolos — whitelist tidak boleh memutus pasangan
            # (saldo awal hilang = Sistem/Deviasi pasangan itu salah;
            # akar "Bumbu Pasta Kuah ada di 42.17 tapi tidak muncul").
            _prot = {_norm_barang(b) for b in (protected_barangs or [])
                     if b is not None}
            if _prot and "Nama Barang" in prom.columns:
                _b_norm = prom["Nama Barang"].map(_norm_barang)
                _n_prot = int((_b_norm.isin(_prot) & ~keep.fillna(False)
                               ).sum())
                keep = keep | _b_norm.isin(_prot)
                if _n_prot:
                    print(f"    4217 dua arah: {_n_prot} baris barang "
                          "ber-pasangan (rekap/IN/out) dipertahankan "
                          "meski kategori di luar whitelist")
            n_total = len(prom)
            prom = prom[keep.fillna(False)]
            n_keep = len(prom)
            print(f"    4217 kategori filter: {n_keep:,}/{n_total:,} baris "
                  f"lolos whitelist ({len(wl_norm)} kategori)")
            # v3.9.39 — LOG BARANG TERBUANG (transparan, bukan senyap):
            # sebut nama barang yang benar-benar terbuang (tanpa pasangan
            # di sumber lain) supaya keluhan "barang ada di file tapi
            # tidak muncul" langsung terlihat penyebabnya di log.
            if n_total > n_keep and "Nama Barang" in prom_raw.columns:
                _dropped = prom_raw.loc[~keep.fillna(False).reindex(
                    prom_raw.index, fill_value=False)]
                _dropped_names = (_dropped["Nama Barang"].dropna()
                                  .astype(str).str.strip())
                _dropped_names = [x for x in _dropped_names.unique() if x]
                if _dropped_names:
                    _show = ", ".join(_dropped_names[:10])
                    if len(_dropped_names) > 10:
                        _show += f" … (+{len(_dropped_names) - 10})"
                    print(f"    4217 whitelist terbuang: "
                          f"{len(_dropped_names)} barang — {_show} "
                          "(kategori di luar whitelist; tidak ada "
                          "pasangan di rekap/IN/out; tambahkan kategori "
                          "di config.json 'KategoriBarang4217' bila "
                          "saldo ini harus masuk)")
            if prom.empty and n_total:
                # SAFETY-NET: whitelist salah config (mis. nama kategori di
                # file user beda total) → JANGAN kosongkan saldo awal;
                # bypass filter + peringatan mencolok di log.
                print("    [PERINGATAN] 4217: whitelist kategori "
                      "menyaring SEMUA baris — filter di-bypass (cek "
                      "config.json 'KategoriBarang4217' vs kolom Kategori "
                      "Barang file 42.17)")
                prom = prom_raw
                kat_col = "KATEGORI BARANG" if _kat_was else None
                sat_col = _sat_was
    elif kat_col is None:
        print("    4217: kolom Kategori Barang tidak ditemukan — "
              "filter kategori tidak diterapkan")

    id_vars = ["Nama Barang"]
    if sat_col is not None and sat_col in prom.columns:
        id_vars.append(sat_col)

    # FIX 6f-01 (audit 6-f): buang kolom RINGKASAN sebelum melt. Export
    # Accurate bisa menambah kolom total ber-kurung (mis. 'TOTAL (SEMUA
    # GUDANG)', 'JUMLAH (ALL)') — melt menjadikannya resto PHANTOM
    # (between-delimiters 'SEMUA GUDANG') → saldo tiap barang terhitung
    # 2× (gudang + total). Kolom gudang LEGIT juga ber-kurung — nama
    # 'GUDANG X (KODE)' / 'RESTO MALANG (MLGPAR)', kode resto di DALAM
    # kurung — jadi kriteria = token ringkasan (word-boundary,
    # case/whitespace-insensitive) pada nama kolom: TOTAL / JUMLAH /
    # SUBTOTAL / GRAND / SEMUA. Kolom non-id TANPA kurung tetap terbuang
    # oleh mask NAMA RESTO kosong di bawah (perilaku lama).
    _summary_cols = []
    for c in prom.columns:
        if c in id_vars:
            continue
        _nm = re.sub(r"\s+", " ", str(c)).strip().upper()
        if _SUMMARY_COL_RE.search(_nm):
            _summary_cols.append(c)
    if _summary_cols:
        prom = prom.drop(columns=_summary_cols)
        _show = ", ".join(str(c) for c in _summary_cols[:5])
        if len(_summary_cols) > 5:
            _show += f" … (+{len(_summary_cols) - 5})"
        print(f"    4217 ringkasan: {len(_summary_cols)} kolom "
              f"total/jumlah dibuang sebelum melt — {_show} (bukan kolom "
              "gudang resto — mencegah resto phantom + saldo dobel)")

    up = prom.melt(id_vars=id_vars, var_name="NAMA RESTO", value_name="Value")

    # SATUAN → string bersih ('' bila kolom tak ada / kosong)
    if sat_col is not None and sat_col in up.columns:
        up = up.rename(columns={sat_col: "SATUAN"})
    else:
        up["SATUAN"] = ""
    up["SATUAN"] = (up["SATUAN"].astype(str).str.strip()
                    .replace({"nan": "", "None": "", "NaN": ""}))

    # ext = NAMA RESTO → BetweenDelimiters(_, "(", ")") — vectorized
    # (pseudo-baris non-resto — mis. 'Kode Barang' bila masih ada —
    # menghasilkan '' dan terbuang oleh mask bawah)
    from .helpers import vec_text_between_delimiters
    up["NAMA RESTO"] = vec_text_between_delimiters(up["NAMA RESTO"], "(", ")")

    # addT = Tanggal = 1
    up["Tanggal"] = pd.array([1] * len(up), dtype="Int64")

    # addJ = JENIS = "SALDO AWAL"
    up["JENIS"] = "SALDO AWAL"

    # Value → numeric
    up["Value"] = pd.to_numeric(up["Value"], errors="coerce")

    # fil = Table.SelectRows(addJ, each [Value] <> 0 and [Value] <> null and [NAMA RESTO] <> "")
    mask = (
        up["Value"].notna() &
        (up["Value"] != 0) &
        up["NAMA RESTO"].notna() &
        (up["NAMA RESTO"].astype(str).str.strip() != "")
    )
    fil = up[mask].reset_index(drop=True)

    return fil[OUTPUT_COLUMNS]
