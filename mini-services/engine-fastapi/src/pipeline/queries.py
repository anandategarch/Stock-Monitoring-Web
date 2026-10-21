"""
queries.py — Semua query antara (mirror M code shared queries).
Setiap function = 1 shared query di M code.

v3.9.20 (deep audit 34-d/fix 35-d): query_4205_bulan_lalu /
query_3224_bulan_lalu me-resolve sheet folder bulan-lalu — key
dedikasi Sheets["Pemindahan4205Lalu"] (default = nilai berjalan) +
fallback prefiks modul "#42.05"/"#32.24" (sheet lalu beda nama ≠
lagi 0 baris senyap).

v3.9.33 — AUDIT FIX (48-a): 5 key Sheets config yang dulu di-HARDCODE
reader kini benar-benar dipakai — Penjualan2205 / Pemindahan4215 /
SaldoAwal4217 / Penerimaan3224 / DBSKategori (dibaca defensif via
_sheet_cfg: config lama/mock tanpa key tetap dapat nilai default).
"""
import pandas as pd

from .fn_2205 import SHEET_2205, fn_2205
from .fn_3224 import SHEET_3224, fn_3224
from .fn_4205 import fn_4205
from .fn_4215 import SHEET_4215, fn_4215
from .fn_4217 import SHEET_4217, fn_4217
from .fn_9901 import fn_9901
from .fn_dbs_kategori import SHEET_DBS_KATEGORI, fn_dbs_kategori
from .fn_rekap_mentah import fn_rekap_mentah
from .helpers import _list_excel_files, _list_sheet_names, to_datetime_robust

# =============================================================================
# MASTER QUERIES (dari Config)
# =============================================================================


def _sheet_cfg(config, key: str, default: str) -> str:
    """v3.9.33 — AUDIT FIX (48-a): baca Sheets[key] DEFENSIF.

    config.sheet(key) raise KeyError utk config lama tanpa key; mock
    config test bahkan tak punya atribut Sheets. Di sini:
    Sheets.get(key, default) → nilai default hardcode reader tetap
    terpakai (config.json lama tanpa key baru TIDAK rusak)."""
    sheets = getattr(config, "Sheets", None)
    if not sheets:
        return default
    try:
        val = sheets.get(key, default)
    except AttributeError:
        return default
    return str(val) if val else default


def query_dbs_kategori(config) -> pd.DataFrame:
    """Mirror M: shared DBS_Kategori = fnDBSKategori(Config[RootPath] & Config[Folders][DBSKategori])

    v3.9.33 — AUDIT FIX (48-a): sheet dari config Sheets['DBSKategori']
    (default 'Sheet1' — perilaku lama)."""
    return fn_dbs_kategori(config.folder("DBSKategori"),
                           sheet_name=_sheet_cfg(config, "DBSKategori",
                                                 SHEET_DBS_KATEGORI))


def query_4217(config, protected_barangs: list | set | None = None
               ) -> pd.DataFrame:
    """Mirror M: shared #"4217" = fn4217(Config[RootPath] & Config[Folders][SaldoAwal4217])

    v3.9.32: whitelist kategori dari config ("KategoriBarang4217") ikut
    diteruskan — filter diterapkan SEBELUM melt di fn_4217 (lebih awal).

    v3.9.33 — AUDIT FIX (48-a): sheet dari config Sheets['SaldoAwal4217']
    (default '#42.17. Kuantitas Barang per Gu' — perilaku lama).

    v3.9.39 — LOOKUP DUA ARAH: protected_barangs (nama barang ber-pasangan
    di sumber lain — rekap/IN/out/BK; diisi build_append1) diteruskan ke
    fn_4217: baris barang itu SELALU lolos whitelist kategori (saldo awal
    tidak boleh hilang — akar "barang ada di 42.17 tapi tidak muncul di
    Deviasi GR")."""
    return fn_4217(config.folder("SaldoAwal4217"),
                   kategori_whitelist=getattr(config, "KategoriBarang4217",
                                              None),
                   sheet_name=_sheet_cfg(config, "SaldoAwal4217",
                                         SHEET_4217),
                   protected_barangs=protected_barangs)


# =============================================================================
# TRANSACTION QUERIES
# =============================================================================

def query_2205(config) -> pd.DataFrame:
    """Mirror M: shared #"2205" = fn2205(Config[RootPath] & Config[Folders][Penjualan2205])

    v3.9.33 — AUDIT FIX (48-a): sheet dari config Sheets['Penjualan2205']
    (default '#22.05. Rincian Penjualan per B' — perilaku lama)."""
    return fn_2205(config.folder("Penjualan2205"),
                   sheet_name=_sheet_cfg(config, "Penjualan2205",
                                         SHEET_2205))


def query_4215_gudang_kirim(config) -> pd.DataFrame:
    """
    Mirror M: shared #"4215_Gudang Kirim" = let
        fn4215(Kirim4215, "kirim"), filter NAMA RESTO <> ""

    v3.9.33 — AUDIT FIX (48-a): sheet dari config Sheets['Pemindahan4215']
    (default '#42.15. Pemindahan Barang (KIRI' — perilaku lama).
    """
    result = fn_4215(config.folder("Kirim4215"), "kirim",
                     sheet_name=_sheet_cfg(config, "Pemindahan4215",
                                           SHEET_4215))
    if not result.empty and "NAMA RESTO" in result.columns:
        mask = result["NAMA RESTO"].notna() & (result["NAMA RESTO"].astype(str).str.strip() != "")
        result = result[mask].reset_index(drop=True)
    return result


def query_3224(config) -> pd.DataFrame:
    """
    Mirror M: shared #"3224" = let
        fn3224(RI3224, "berjalan"), Changed Type #Tgl/Jam Pembuatan IT → datetime

    v3.9.33 — AUDIT FIX (48-a): sheet dari config Sheets['Penerimaan3224']
    (default SHEET_3224 — perilaku lama; query lalu memakai nilai yang
    sama sebagai probe _resolve_lalu_sheet, mirror pola 42.05).
    """
    result = fn_3224(config.folder("RI3224"), "berjalan",
                     sheet_name=_sheet_cfg(config, "Penerimaan3224",
                                           SHEET_3224))
    if "#Tgl/Jam Pembuatan IT" in result.columns:
        # v3.9.28: to_datetime_robust — .xlsb/pyxlsb memberi serial mentah
        result["#Tgl/Jam Pembuatan IT"] = to_datetime_robust(result["#Tgl/Jam Pembuatan IT"])
    return result


def query_3224_bulan_lalu(config) -> pd.DataFrame:
    """
    Mirror M: shared #"3224_Bulan Lalu" = let
        fn3224(RI3224Lalu, "lalu"), Changed Type #Tgl/Jam Pembuatan IT → datetime

    FIX R-3 (audit 34-d): sheet folder lalu di-resolve via
    _resolve_lalu_sheet (fallback deterministik prefiks modul '#32.24') —
    folder lalu dgn sheet bernama beda tidak lagi 0 baris senyap.
    """
    folder = config.folder("RI3224Lalu")
    # v3.9.33 — AUDIT FIX (48-a): probe nama sheet lalu memakai key config
    # 'Penerimaan3224' (default SHEET_3224 — resolusi prefiks #32.24 tetap
    # jadi fallback bila nama tak ada di folder lalu).
    sheet_name = _resolve_lalu_sheet(
        folder, _sheet_cfg(config, "Penerimaan3224", SHEET_3224), "#32.24")
    result = fn_3224(folder, "lalu", sheet_name=sheet_name)
    if "#Tgl/Jam Pembuatan IT" in result.columns:
        # v3.9.28: to_datetime_robust — .xlsb/pyxlsb memberi serial mentah
        result["#Tgl/Jam Pembuatan IT"] = to_datetime_robust(result["#Tgl/Jam Pembuatan IT"])
    return result


def _resolve_lalu_sheet(folder_path: str, sheet_name: str,
                        module_prefix: str) -> str:
    """FIX R-3 (audit 34-d): resolusi nama sheet folder bulan-lalu.

    Folder bulan lalu yang sheet-nya bernama beda (mis. '#42.05. Rincian
    Pemindahan LALU') dulu menghasilkan 0 baris SENYAP (fn_combine_folder
    me-skip file tanpa sheet tsb). Resolusi sekarang:
    1. bila ada ≥1 file Excel di folder yang memuat <sheet_name> persis
       → pakai <sheet_name> (perilaku lama, file lain tetap di-skip dgn
       WARNING oleh fn_combine_folder);
    2. bila TIDAK ADA → fallback DETERMINISTIK: sheet pertama (file
       ter-sort nama, urutan workbook) yang namanya diawali
       <module_prefix> (mis. '#42.05' / '#32.24') + INFO di log;
    3. bila tidak ada sheet berprefiks modul juga → <sheet_name>
       dipertahankan (0 baris, tapi WARNING per-file tetap tercetak —
       bukan senyap total; folder kosong/tak ada tetap 0 baris senyap
       sesuai spec v3.9.17).
    """
    files = _list_excel_files(folder_path)
    if not files:
        return sheet_name
    for f in files:
        if sheet_name in _list_sheet_names(f):
            return sheet_name
    pref = module_prefix.strip().lower()
    for f in files:
        for name in _list_sheet_names(f):
            if str(name).strip().lower().startswith(pref):
                print(f"    [INFO] Sheet lalu '{name}' dipakai "
                      f"(nama '{sheet_name}' tidak ada di folder)")
                return str(name)
    return sheet_name


def query_4205(config) -> pd.DataFrame:
    """Mirror M: shared #"4205" = fn4205(Config[RootPath] & Config[Folders][Pemindahan4205])"""
    sheet_name = config.sheet("Pemindahan4205")
    return fn_4205(config.folder("Pemindahan4205"), sheet_name=sheet_name)


def query_4205_bulan_lalu(config) -> pd.DataFrame:
    """v3.9.17 — mirror pola shared #"3224_Bulan Lalu": fn_4205(mode="lalu")
    atas folder Pemindahan4205Lalu ("4.1 4205 Bulan Lalu") → penambah IN
    periode ujung bulan lalu (5 hari terakhir file, Tanggal dinegasikan —
    "sama seperti 32.24 bulan lalu"). Key config di-default di Config
    (config lama pra-v3.9.17 tetap aman); folder kosong/tidak ada → 0
    baris senyap.
    FIX R-3 (audit 34-d): sheet folder lalu kini dari key DEDIKASI
    'Pemindahan4205Lalu' (di-default ke nilai berjalan — pola 32.24)
    + fallback deterministik prefiks modul '#42.05' via
    _resolve_lalu_sheet → sheet lalu bernama beda ≠ 0 baris senyap."""
    folder = config.folder("Pemindahan4205Lalu")
    sheet_name = _resolve_lalu_sheet(
        folder, config.sheet("Pemindahan4205Lalu"), "#42.05")
    return fn_4205(folder, sheet_name=sheet_name, mode="lalu")


def query_9901(config) -> pd.DataFrame:
    """Process 9901 file (mutasi tanpa nomor penerimaan) → sumber IN tambahan.

    Filter: Nomor # Penerimaan Barang = blank, Jenis = Persediaan.
    Kolom: #Prime.Qty → Value, Nama barang → Nama Barang,
          Nama cabang → NAMA RESTO (extract after ".", e.g., "1137.CKGPAH" → "CKGPAH"),
          Tanggal → Tanggal (day).
    """
    return fn_9901(config.folder("Data9901"))


# =============================================================================
# OUT & IN (combine queries)
# =============================================================================

def query_out(config) -> pd.DataFrame:
    """
    22.05 sales — SEMUA dokumen masuk KECUALI kode SI (v3.9.71, user:
    "22.05 tanpa kode SI ya maaf aku lupa bilang kemarin" — lanjutan
    v3.9.70 "semua kode masuk": Nomor # berawalan "SI." dikecualikan;
    ACR./RETUR./dll. tetap masuk). JENIS = "OUT".

    Previously combined with 4215 Kirim. Split per user request:
    COM formula needs BK = 42.15 Kirim only (separate from sales).
    """
    q2205 = query_2205(config)
    if not q2205.empty:
        q2205 = q2205.copy()
        q2205["JENIS"] = "OUT"
    return q2205 if not q2205.empty else pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value", "JENIS"])


def query_barang_keluar(config) -> pd.DataFrame:
    """
    42.15 Kirim (goods sent to other branches). JENIS = "BARANG KELUAR".
    Separated from OUT per user request.
    """
    result = query_4215_gudang_kirim(config)
    if not result.empty:
        result = result.copy()
        result["JENIS"] = "BARANG KELUAR"
    return result if not result.empty else pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value", "JENIS"])


def query_in(config, detail_out: dict | None = None) -> pd.DataFrame:
    """
    IN source = Table.Combine({3224, 3224_Bulan_Lalu, 4205,
    4205_Bulan_Lalu (v3.9.17 — folder "4.1 4205 Bulan Lalu", penambah IN
    ujung bulan lalu, mirror 32.24 bulan lalu), 9901})
    with JENIS = "IN".

    (v3.5: LightMode dihapus — 3224_Bulan_Lalu SELALU dibaca.)

    v3.4 — detail_out: bila dict diberikan, diisi DataFrame detail IN
    PER DOKUMEN (untuk tab "Rekap Selisih IN" — rincian 42.05 / 32.24 /
    99.01 beserta nomornya): kolom NAMA RESTO, Nama Barang, Tanggal,
    Value, Nomor, Nomor PO, #Tgl/Jam Pembuatan IT, SOURCE IN, JENIS.
    Baris detail identik 1:1 dengan baris IN di source (belum difilter
    KATEGORI — filter yang sama diterapkan build_append1).

    v3.9.29 — SEMUA baris IN kini juga membawa kolom 'SOURCE IN' (bukan
    hanya detail): append1 LANGKAH 5b menurunkan klasifikasi SOURCE
    KIRIMAN per pasangan (Nama Barang × NAMA RESTO) dari tag sumber ini
    (user: 42.05 → Internal; 32.24 & 9901 → Eksternal; campuran →
    'Campuran'; mengganti nilai master DBS Kategori). Kolom ekstra ini
    TIDAK ikut pivot/informasi append1 (hanya KeyColumns/InfoColumns/
    JENIS/Value yang diseleksi) — aman untuk pemanggil lama.

    FIX: query_pi (folder 26.Rincian PI) + query_27_konversi_satuan DIHAPUS
    dari pipeline karena sudah digantikan oleh 9901 (folder 30. 9901).
    9901 pakai #Prime.Qty (sudah unit utama) — tidak perlu konversi satuan.
    fn_pi.py + fn_konversi_satuan.py sudah dihapus dari codebase.
    """
    q3224 = query_3224(config)
    q3224_lalu = query_3224_bulan_lalu(config)   # v3.5: selalu baca bulan lalu
    q4205 = query_4205(config)
    q4205_lalu = query_4205_bulan_lalu(config)  # v3.9.17: penambah IN ujung bulan lalu
    q9901 = query_9901(config)
    print(f"    9901 (mutasi tanpa penerimaan): {len(q9901)} rows")

    tagged = [
        ("32.24", q3224),
        ("32.24 (Bulan Lalu)", q3224_lalu),
        ("42.05", q4205),
        ("42.05 (Bulan Lalu)", q4205_lalu),
        ("99.01", q9901),
    ]

    parts = []
    detail_parts = []
    for tag, df in tagged:
        if df is None or df.empty:
            continue
        # v3.9.29 — tag SOURCE IN pada SEMUA baris (dulu hanya salinan
        # detail): satu copy dipakai bersama parts + detail_parts.
        d = df.copy()
        d["SOURCE IN"] = tag
        parts.append(d)
        if detail_out is not None:
            detail_parts.append(d)

    if not parts:
        empty = pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang",
                                      "Value", "JENIS", "SOURCE IN"])
        if detail_out is not None:
            detail_out["df"] = pd.DataFrame(columns=IN_DETAIL_COLUMNS)
        return empty

    source = pd.concat(parts, ignore_index=True, sort=False)
    source["JENIS"] = "IN"

    if detail_out is not None:
        if detail_parts:
            detail = pd.concat(detail_parts, ignore_index=True, sort=False)
            detail["JENIS"] = "IN"
            for col in IN_DETAIL_COLUMNS:
                if col not in detail.columns:
                    detail[col] = pd.NA
            detail_out["df"] = detail[IN_DETAIL_COLUMNS].reset_index(drop=True)
        else:
            detail_out["df"] = pd.DataFrame(columns=IN_DETAIL_COLUMNS)

    return source


# Kolom standar detail IN per dokumen (v3.4 — tab Rekap Selisih IN)
IN_DETAIL_COLUMNS = [
    "NAMA RESTO", "Nama Barang", "Tanggal", "Value", "Nomor",
    "Nomor PO", "#Tgl/Jam Pembuatan IT", "SOURCE IN", "JENIS",
]


# =============================================================================
# Full Rekap Mentah SO
# =============================================================================

def query_full_rekap_mentah_so(config) -> pd.DataFrame:
    """
    Mirror M: shared #"Full Rekap Mentah SO" = let
        a = fnRekapMentah(RekapBerjalan, "berjalan", {"BARANG MASUK", "SO"}),
        b = fnRekapMentah(RekapLalu, "lalu", {"BARANG MASUK", "SO"}),
        c = Table.Combine({b, a}),  ← b first, then a
        d = rename Attribute→Tanggal, NAMA BARANG→Nama Barang,
        e = select {NAMA RESTO, Nama Barang, JENIS, Tanggal, Value},
        f = Tanggal → Int64

    (v3.5: LightMode dihapus — RekapLalu SELALU dibaca.)
    """
    jenis_filter = ["BARANG MASUK", "SO"]

    a = fn_rekap_mentah(config.folder("RekapBerjalan"), "berjalan", jenis_filter=jenis_filter)
    b = fn_rekap_mentah(config.folder("RekapLalu"), "lalu", jenis_filter=jenis_filter)   # v3.5: selalu

    # c = Table.Combine({b, a}) — b first
    parts = []
    if not b.empty:
        parts.append(b)
    if not a.empty:
        parts.append(a)

    if not parts:
        return pd.DataFrame(columns=["NAMA RESTO", "Nama Barang", "JENIS", "Tanggal", "Value"])

    c = pd.concat(parts, ignore_index=True, sort=False)

    # d = rename: Attribute → Tanggal, NAMA BARANG → Nama Barang
    c = c.rename(columns={"Attribute": "Tanggal", "NAMA BARANG": "Nama Barang"})

    # e = select {NAMA RESTO, Nama Barang, JENIS, Tanggal, Value, SATUAN}
    # SATUAN ditambahkan untuk DEVIASI GR/PCS split (perlu satuan per barang)
    # v3.9.19: SOURCE DATA ikut dibawa (REKAP MENTAH JENIS SO — "input so
    # harian" / "input promix 04 dine in" / "input promix 04 take away")
    # utk CEK "Promix 04" di tab Deviasi GR/PCS (append1 merge per pasangan).
    # v3.9.49: KATEGORI rekap mentah ikut dibawa (user: "ambil kategori
    # dari file Rekap Mentah") — dipakai append1 LANGKAH 5 sebagai sumber
    # kategori PRIORITAS atas master '21. DBS Kategori'; kolom opsional
    # (schema rekap lama tanpa KATEGORI tetap didukung).
    needed = ["NAMA RESTO", "Nama Barang", "JENIS", "Tanggal", "Value",
              "SATUAN", "SOURCE DATA", "KATEGORI"]
    available = [col for col in needed if col in c.columns]
    e = c[available].copy()

    # f = Tanggal → Int64
    if "Tanggal" in e.columns:
        e["Tanggal"] = pd.to_numeric(e["Tanggal"], errors="coerce").astype("Int64")

    return e
