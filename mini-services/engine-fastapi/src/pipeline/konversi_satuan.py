"""
konversi_satuan.py — v3.9.31 Peta konversi satuan per (Nama Barang × Satuan).

MASALAH (user): kolom Kuantitas Rincian PO (32.43) masih satuan besar
(karton) sedangkan seluruh rantai IN/audit (42.05 '#Qty. Terkecil',
32.24 'Kts (Unit#1)', 99.01 '#Prime.Qty', pivot 'Barang Masuk' =
Sum of Kuantiti Terima, rekap '29' UoM) SATUAN TERKECIL (botol/GR/PCS)
→ kolom 'Qty PO Menunggu' v3.9.30 tidak apple-to-apple dengan
Selisih/Saldo (contoh: sisa -120 BOTOL vs PO menunggu 5 KARTON —
padahal 5×24=120 = match tersembunyi).

SOLUSI (user): peta konversi dari data transaksi AKTUAL 2 file:
- 32.24: kolom 'Rasio Satuan' + 'Satuan' (barang eksternal murni —
  GULA/KARUNG, SUSU ULTRA/KARTON, JERUK NIPIS, CINCAU, KERTAS MINYAK,
  SENDOK PLASTIK + satuan khusus RI: MIE/KANTONG, CABE RAWIT/KG,
  MIKA-CUP/KARTON, NATA DE COCO/GR, SUMPIT/PCS — TIDAK ter-cover 42.05)
- 42.05: kolom 'Rasio Satuan' + '#Sat. Kirim' + '#Sat. Terkecil'
  (identitas Kuantiti Terima = #Qty Kirim × Rasio terverifikasi
  4.591/4.591 baris data real; 0 konflik rasio per (barang, satuan);
  0 konflik terkecil per barang; rasio konsisten LINTAS resto →
  join key = NAMA BARANG saja, properti item)

Peta dibangun DI MEMORI dari baris IN hasil query_in (tanpa file
master excel tambahan — selalu segar mengikuti data transaksi);
kolom sumber dibaca oleh fn_4205/fn_3224 lalu dibakukan ke nama
kolom standar (lihat resolve_konversi_kolom) — kolom ekstra TIDAK
ikut pivot append1 (pola 'SOURCE IN' v3.9.29).

ATURAN LOOKUP (lookup_rasio):
1. exact (barang, satuan-PO) di peta → rasio;
2. satuan-PO == satuan terkecil barang (implisit → rasio 1 — WAJIB:
   70/152 barang real TIDAK punya baris satuan==terkecil di 42.05);
3. tidak ketemu → None (pemanggil menampilkan qty PO as-is + penanda).

Catatan edge (dari analisis data real): rasio pecahan ada (SUN QUICK
LEMON BOTOL 383.48 / KARTON 4601.76); nama satuan sama ≠ rasio sama
antar barang (KARUNG: SUMPIT 3000 vs TEPUNG ROTI 10000) → peta
key (barang, satuan) BUKAN satuan global; LPG 12KG = UoM rekap (KG)
≠ terkecil 42.05 (TABUNG) — inkonsistensi data existing user.
"""
import pandas as pd

# Nama kolom BAKU pada frame hasil fn_4205/fn_3224 (schema konsisten
# supaya concat query_in menyatukan kedua sumber; 99.01 tanpa kolom
# ini → NaN oleh concat sort=False — aman, #Prime.Qty sudah satuan dasar)
KOL_SATUAN_DOK = "SATUAN DOK"
KOL_RASIO = "RASIO SATUAN"
KOL_TERKECIL = "SATUAN TERKECIL"

# Kandidat nama kolom asli per sumber — beda versi export Accurate
# (file user: '#Sat. Kirim'; salinan lama workbook: 'Satuan') → resolusi
# defensive first-match, satu kolom saja supaya rename tidak tabrakan
_KANDIDAT_4205 = {
    KOL_SATUAN_DOK: ["#Sat. Kirim", "Satuan"],
    KOL_RASIO: ["Rasio Satuan"],
    KOL_TERKECIL: ["#Sat. Terkecil", "Sat. Terkecil"],
}
_KANDIDAT_3224 = {
    KOL_SATUAN_DOK: ["Satuan"],
    KOL_RASIO: ["Rasio Satuan"],
    KOL_TERKECIL: ["#Sat. Terkecil", "Sat. Terkecil"],
}


def resolve_konversi_kolom(prom_columns, sumber: str) -> dict:
    """{nama kolom BAKU: nama kolom ASLI di sheet} — first-match dari
    kandidat; kolom tak ada → tidak masuk dict (frame final diberi
    kolom NA oleh pemanggil supaya schema concat konsisten).

    v3.9.33 — AUDIT FIX (48-a): dict-comprehension lama menimpa nilai per
    kandidat → LAST-match menang ('Satuan' menimpa '#Sat. Kirim' bila
    keduanya ada — KONTRA janji first-match docstring ini). Loop
    eksplisit: kandidat PERTAMA yang ditemukan per kolom baku menang
    (break) — fallback kandidat kedua tetap terpakai bila utama absen
    (salinan lama workbook 'Satuan')."""
    kandidat = _KANDIDAT_4205 if sumber == "4205" else _KANDIDAT_3224
    cols = set(prom_columns) if prom_columns is not None else set()
    out: dict = {}
    for std, cands in kandidat.items():
        for c in cands:
            if c in cols:
                out[std] = c
                break  # first-match — kandidat berikutnya TIDAK menimpa
    return out


def _norm_sat(v) -> str:
    """Satuan → 'BOTOL' (strip + upper); None/NaN/blank → ''."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(v).strip().upper()
    return "" if s in ("NAN", "NONE") else s


def build_konversi_map(in_df: "pd.DataFrame | None") -> dict:
    """Peta konversi dari frame gabungan IN (hasil query_in — kolom
    ekstra SATUAN DOK / RASIO SATUAN / SATUAN TERKECIL dari fn_4205 +
    fn_3224; kolom bulan-lalu ikut — makin banyak baris makin lengkap
    coverage pasangan (barang, satuan)).

    Return {"rasio": {(barang, satuan): float},
            "terkecil": {barang: satuan_upper},
            "n_rasio": int, "n_barang": int, "n_conflict": int}.

    Kebijakan konflik (barang, satuan sama, rasio beda — tidak pernah
    teramati di data real 42.05 tapi 32.24 bisa beda versi): nilai
    PERTAMA yang terlihat dipakai + dihitung utk log; rasio <= 0 / NaN
    dibuang. Terkecil: kolom '#Sat. Terkecil' (42.05) menang; baris
    rasio == 1 (satuan dokumen = satuan dasar) sebagai inferensi.
    """
    out = {"rasio": {}, "terkecil": {}, "n_rasio": 0,
           "n_barang": 0, "n_conflict": 0}
    if in_df is None or getattr(in_df, "empty", True):
        return out
    cols = set(getattr(in_df, "columns", []))
    if not {KOL_SATUAN_DOK, KOL_RASIO, "Nama Barang"} <= cols:
        return out

    n = len(in_df)
    barang = in_df["Nama Barang"].tolist()
    sat = in_df[KOL_SATUAN_DOK].tolist()
    rasio = pd.to_numeric(in_df[KOL_RASIO], errors="coerce").tolist()
    terk = (in_df[KOL_TERKECIL].tolist() if KOL_TERKECIL in cols
            else [None] * n)
    for i in range(n):
        b = str(barang[i]).strip() if barang[i] is not None else ""
        if not b or b.lower() in ("nan", "none"):
            continue
        s = _norm_sat(sat[i])
        r = rasio[i]
        if not s or r is None or pd.isna(r) or float(r) <= 0:
            continue
        key = (b, s)
        prev = out["rasio"].get(key)
        if prev is None:
            out["rasio"][key] = float(r)
        elif abs(prev - float(r)) > 1e-9:
            out["n_conflict"] += 1
        t = _norm_sat(terk[i])
        if t:
            out["terkecil"].setdefault(b, t)
        elif float(r) == 1.0:
            # satuan dokumen == satuan dasar (baris rasio 1)
            out["terkecil"].setdefault(b, s)
    out["n_rasio"] = len(out["rasio"])
    out["n_barang"] = len({b for b, _ in out["rasio"]})
    return out


def lookup_rasio(kmap: "dict | None", barang, satuan) -> tuple:
    """(rasio | None, satuan_terkecil | None) utk (barang, satuan PO).

    1. exact (barang, sat-upper) di peta → rasio;
    2. sat == terkecil barang → 1.0 (aturan implisit);
    3. tak ketemu → (None, terkecil) — pemanggil pakai fallback
       qty as-is + penanda.
    """
    if not kmap or barang is None or satuan is None:
        return None, None
    b = str(barang).strip()
    s = _norm_sat(satuan)
    if not b or not s:
        return None, None
    terk = kmap.get("terkecil", {}).get(b)
    rasio = kmap.get("rasio", {}).get((b, s))
    if rasio is None and terk is not None and s == terk:
        rasio = 1.0
    return rasio, terk
