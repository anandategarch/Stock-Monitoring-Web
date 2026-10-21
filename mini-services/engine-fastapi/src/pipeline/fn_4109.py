"""
fn_4109.py — v3.9.32 HARGA per barang dari laporan 41.09 "Nilai
Persediaan [ALL]" (folder '09.Harga' — alamat bisa diubah di config.json
key Folders.Harga; file contoh user: 4109.xlsx).

STRUKTUR FILE (dibedah dari upload user, sheet '#41.09. Nilai
Persediaan [ALL]'):
- 4 baris metadata (judul/periode 'Dari 01 Okt 2026 s/d 07 Okt 2026'/
  'Cabang : [Semua Cabang]') — TANPA dimensi resto → harga GLOBAL per
  barang (agregat semua cabang);
- header 2 baris: baris-1 grup ('Kategori Barang', 'Nama Barang',
  'Kode Barang', 'Nama Satuan', 'Saldo Awal', 'Masuk', 'Keluar',
  'Saldo Akhir'), baris-2 sub ('Kuantitas'/'Nilai'); kolom Keluar Nilai
  terpisah 1 kolom spacer;
- data dari baris ke-7; kolom KATEGORI ber-pola header grup (nilai
  hanya di baris pertama tiap grup — sisanya NaN → forward-fill, mirror
  pembacaan kategori fn_4217);
- baris subtotal per grup 'Total Nama Barang' + grand total 'Total
  Kategori Barang' → DIBUANG;
- HARGA = Nilai Saldo Akhir ÷ Kuantitas Saldo Akhir (Qty 0 → NaN;
  data real: baris Qty=0 ber-Nilai±≠0 ada → guard). Contoh data user:
  AIR MINERAL BOTOL (V.20) 490.467.647,94/393.524 = 1.246,35/BOTOL
  (satuan = terkecil rekap ✓); GULA (V.20) 18,25/GR; ARANG BAKARAN
  8,79/GR.

Output: DataFrame [Kategori, Nama Barang, Satuan, Harga] — 1 baris per
barang (harga GLOBAL lintas resto; duplikat nama barang → baris
terakhir menang, konsisten grup).
"""
import re

import pandas as pd

from .helpers import _list_excel_files, _list_sheet_names, fn_buka_sheet

SHEET_4109_DEFAULT = "#41.09. Nilai Persediaan [ALL]"

OUTPUT_COLUMNS = ["Kategori", "Nama Barang", "Satuan", "Harga"]


def _norm_sheet(v) -> str:
    """Nama sheet dibanding: buang [ ] ( ) spasi + lower (file user
    '#41.09. Nilai Persediaan [ALL]' vs mock tanpa kurung)."""
    s = str(v) if v is not None else ""
    for ch in "[]() ":
        s = s.replace(ch, "")
    return s.lower()


def _buka_4109(file_path: str, sheet_name: str):
    """Buka sheet 41.09 — exact match dulu, lalu fallback nama sheet
    ternormalisasi (prefix-match; beda versi export Accurate bisa beda
    nama persis)."""
    try:
        return fn_buka_sheet(file_path, sheet_name, raw=True)
    except Exception:
        pass
    names = _list_sheet_names(file_path)
    want = _norm_sheet(sheet_name)
    for nm in names:
        n = _norm_sheet(nm)
        if n == want or n.startswith(want[:24]) or want.startswith(n[:24]):
            try:
                return fn_buka_sheet(file_path, nm, raw=True)
            except Exception:
                continue
    return None


def _hdr(v) -> str:
    """Teks header kolom dibanding (strip + lower)."""
    return str(v).strip().lower() if v is not None else ""


def _extract_4109(raw: pd.DataFrame) -> pd.DataFrame | None:
    """Deteksi posisi kolom dari header 2 baris → frame bersih per file.

    Defensive terhadap pergeseran kolom antar versi export: kolom
    dicari berdasarkan NAMA header (bukan posisi tetap). Return None bila
    struktur tak dikenali (baris 'Kategori Barang' tidak ketemu)."""
    if raw is None or raw.empty:
        return None
    # baris header-1: kolom 'Kategori Barang'
    hdr_row = None
    for i in range(min(len(raw), 12)):
        for j in range(min(len(raw.columns), 6)):
            if _hdr(raw.iat[i, j]) == "kategori barang":
                hdr_row = i
                break
        if hdr_row is not None:
            break
    if hdr_row is None or hdr_row + 1 >= len(raw):
        return None
    sub_row = hdr_row + 1

    h1 = raw.iloc[hdr_row]
    h2 = raw.iloc[sub_row]

    def find_col(name: str, sub: str | None = None, after: int = -1):
        for j in range(len(raw.columns)):
            if j <= after:
                continue
            if _hdr(h1.iloc[j]) == name:
                if sub is None or _hdr(h2.iloc[j]) == sub:
                    return j
        return None

    c_kat = find_col("kategori barang")
    c_nama = find_col("nama barang")
    c_sat = find_col("nama satuan")
    if c_kat is None or c_nama is None:
        return None
    # Saldo Akhir (Qty, Nilai): label grup hanya di kolom PERTAMA pasangan
    # (file real: h1[13]='Saldo Akhir', h1[14]=NaN; h2[13]='Kuantitas',
    # h2[14]='Nilai') → cari posisi grup lalu pasangkan sub-label setelahnya
    c_sa = None
    for j in range(len(raw.columns)):
        if _hdr(h1.iloc[j]) == "saldo akhir":
            c_sa = j
            break
    c_sa_qty = c_sa_nil = None
    if c_sa is not None:
        for j in range(c_sa, len(raw.columns)):
            if c_sa_qty is None and _hdr(h2.iloc[j]) == "kuantitas":
                c_sa_qty = j
            elif c_sa_nil is None and _hdr(h2.iloc[j]) == "nilai":
                c_sa_nil = j
        # fallback pola klasik file user: grup+0 = Qty, grup+1 = Nilai
        if c_sa_qty is None:
            c_sa_qty = c_sa
        if c_sa_nil is None:
            c_sa_nil = c_sa + 1
    if c_sa_qty is None or c_sa_nil is None:
        return None

    data = raw.iloc[sub_row + 1:].copy()
    kat = data[c_kat].ffill()
    nama = data[c_nama]
    sat = data[c_sat] if c_sat is not None else None
    qty = pd.to_numeric(data[c_sa_qty], errors="coerce")
    nil = pd.to_numeric(data[c_sa_nil], errors="coerce")

    out = pd.DataFrame({
        "Kategori": kat,
        "Nama Barang": nama,
        "Satuan": (sat.astype(str).str.strip()
                   if sat is not None else ""),
    }, index=data.index)
    # harga = Nilai Saldo Akhir ÷ Kuantitas Saldo Akhir
    # (guard div-0: Qty 0 → NaN; data real ada baris Qty=0 ber-Nilai ±≠0)
    out["Harga"] = nil / qty.where(qty != 0)

    # filter (semua mask dihitung di index yang SAMA — bebas reindex):
    # - buang subtotal/grand total ('Total Nama Barang' / 'Total Kategori
    #   Barang' — kolom nama ATAU kolom kategori berawalan 'Total');
    # - buang baris tanpa nama barang (NaN/blank).
    _nama_s = out["Nama Barang"].astype(str).str.strip()
    _kat_s = out["Kategori"].astype(str).str.strip()
    keep = (~_nama_s.str.startswith("Total", na=False)
            & ~_kat_s.str.startswith("Total", na=False)
            & _nama_s.ne("")
            & _nama_s.str.lower().ne("nan"))
    out = out[keep]
    return out[["Kategori", "Nama Barang", "Satuan", "Harga"]] \
        .reset_index(drop=True)


def fn_4109(folder_path: str, sheet_name: str = SHEET_4109_DEFAULT) -> pd.DataFrame:
    """Baca folder harga 41.09 → DataFrame [Kategori, Nama Barang,
    Satuan, Harga] (harga GLOBAL per barang — file 41.09 tanpa dimensi
    resto). Folder kosong/tidak ada → DataFrame KOSONG + log (fitur
    harga menonaktifkan diri senyap; pipeline tetap jalan)."""
    files = _list_excel_files(folder_path)
    if not files:
        print(f"    41.09 Harga: folder '{folder_path}' kosong/tidak "
              "ada — peta harga tidak dibangun")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frames = []
    for f in files:
        try:
            raw = _buka_4109(f, sheet_name)
        except Exception as e:
            print(f"  [WARNING] Skip file harga {f}: {e}")
            continue
        if raw is None or raw.empty:
            continue
        extracted = _extract_4109(raw)
        if extracted is not None and not extracted.empty:
            frames.append(extracted)
        else:
            print(f"  [WARNING] File harga {f}: struktur 41.09 tidak "
                  "dikenali — dilewati")

    if not frames:
        print("    41.09 Harga: 0 baris terbaca — peta harga tidak dibangun")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    # duplikat barang (varian plain + (V.20) adalah barang BERBEDA —
    # keduanya dipertahankan; duplikat persis → terakhir menang)
    combined = combined.drop_duplicates(
        subset=["Nama Barang", "Satuan"], keep="last")
    print(f"    41.09 Harga: {len(combined):,} barang "
          f"(folder '{folder_path}')")
    return combined.reset_index(drop=True)


def _norm_barang_key(v) -> str:
    """v3.9.55 — kunci normalisasi nama barang utk peta harga 41.09:
    strip + rapat spasi ganda + UPPER. Latar (user: "ada deviasi yang
    tidak ada nominal nya coba cek"): kunci lama exact-string — nama
    yang sama tapi beda kapitalisasi/spasi ganda ('Gula Pasir' vs
    'GULA  PASIR') MELESET senyap → kolom Nominal '-' padahal harga
    ADA di 41.09. Normalisasi diterapkan KEDUA sisi (build + lookup)
    supaya tetap konsisten."""
    s = re.sub(r"\s+", " ", str(v).strip()).upper()
    return "" if s in ("", "NAN", "NONE") else s


def build_harga_map(harga_df: pd.DataFrame | None) -> dict:
    """{nama barang: (harga | None, satuan)} — harga GLOBAL per barang.

    Barang tanpa harga valid (Qty=0 → NaN) tetap masuk peta dgn harga
    None supaya view bisa menampilkan 'tanpa harga' secara eksplisit
    (bukan keliru dianggap tak ada di file).
    v3.9.55 — KUNCI DINORMALISASI (strip + rapat spasi + upper — lihat
    _norm_barang_key): lookup lookup_harga_pair memakai normalisasi
    SAMA → selisih kapitalisasi/spasi tak lagi membuat nominal hilang."""
    out: dict = {}
    if harga_df is None or getattr(harga_df, "empty", True):
        return out
    if "Nama Barang" not in getattr(harga_df, "columns", []):
        return out
    for _, r in harga_df.iterrows():
        b = _norm_barang_key(r["Nama Barang"])
        if not b:
            continue
        try:
            h = float(r["Harga"]) if pd.notna(r["Harga"]) else None
        except (TypeError, ValueError):
            h = None
        try:
            s = str(r["Satuan"]).strip() if pd.notna(r["Satuan"]) else ""
        except (TypeError, ValueError):
            s = ""
        if s.lower() in ("nan", "none"):
            s = ""
        out[b] = (h, s.upper())
    return out
