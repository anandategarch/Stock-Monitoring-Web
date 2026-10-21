"""
fn_4205.py — Mirror persis fn4205 di M code.
Pemindahan Barang (modul 42.05) → sumber IN.
OPTIMIZED: vectorized text operations + removed redundant pd.to_datetime.
v3.9.17: mode "lalu" — mirror fn_3224(mode="lalu"): 5 hari terakhir file
bulan lalu + Tanggal dinegasikan (folder "4.1 4205 Bulan Lalu" = penambah
IN periode ujung bulan lalu, "sama seperti 32.24 bulan lalu").
v3.9.20 (deep audit 34-d/fix 35-d): mode "lalu" filter baris resto-valid
SEBELUM max_t (mirror PERSIS fn_3224 — baris NA-resto tak lagi menggeser
jendela 5 hari).
v3.9.31: kolom konversi satuan '#Sat. Kirim'/'Rasio Satuan'/
'#Sat. Terkecil' ikut terbaca → dibakukan SATUAN DOK / RASIO SATUAN /
SATUAN TERKECIL (peta konversi PO Menunggu → satuan terkecil —
konversi_satuan.build_konversi_map; kolom ekstra TIDAK ikut pivot
append1, pola 'SOURCE IN' v3.9.29).

v3.9.67 — HARDENING KETAHANAN FORMAT EXPORT (audit ketahanan format
export Accurate, user: "misal suatu saat format tarikan dari accurate
berubah aman gak?"): kolom VALUE ('#Qty. Terkecil') & 'Tanggal
#Terima' yang hilang/di-rename kini DI-WARNING keras — dulu NA SENYAP
(qty IN 42.05 lenyap tanpa jejak log; pola fn_2205 v3.9.67). Perilaku
data TIDAK berubah.
"""
import pandas as pd

from .helpers import (
    date_to_day,
    fn_combine_folder,
    safe_to_numeric,
    safe_to_str,
    to_datetime_robust,
    vec_text_between_delimiters,
)
from .konversi_satuan import (
    KOL_RASIO,
    KOL_SATUAN_DOK,
    KOL_TERKECIL,
    resolve_konversi_kolom,
)


def fn_4205(folder_path: str, sheet_name: str = "#42.05. Rincian Pemindahan Bara",
            mode: str = "berjalan") -> pd.DataFrame:
    """
    Mirror M: fn4205(folderPath).
    mode: "berjalan" (as-is) atau "lalu" (v3.9.17 — 5 hari terakhir +
    Tanggal dinegasikan, mirror fn_3224).
    Output columns: Nomor, NAMA RESTO, Tanggal, Nama Barang, Value, #Tgl/Jam Pembuatan IT
    """
    # Source + Skip(3) + Promote = header=4
    prom = fn_combine_folder(folder_path, sheet_name, header_row=4)
    if prom.empty:
        return pd.DataFrame(columns=["Nomor", "NAMA RESTO", "Tanggal", "Nama Barang",
                                      "Value", "#Tgl/Jam Pembuatan IT",
                                      KOL_SATUAN_DOK, KOL_RASIO, KOL_TERKECIL])

    # v3.9.31 — resolusi kolom konversi (beda versi export: '#Sat. Kirim'
    # vs 'Satuan' — first-match SATU kolom supaya rename tak tabrakan)
    konv = resolve_konversi_kolom(prom.columns, "4205")

    # Selected
    needed = ["Nomor #Terima", "Gudang #Terima", "Tanggal #Terima", "Nama Barang",
              "#Qty. Terkecil", "#Tgl/Jam Pembuatan IT"] + list(konv.values())
    available = [c for c in needed if c in prom.columns]
    sel = prom[available].copy()

    # Typed: text columns (vectorized)
    for col in ["Nomor #Terima", "Gudang #Terima", "Nama Barang"]:
        if col in sel.columns:
            sel[col] = safe_to_str(sel[col])
    # Numeric
    if "#Qty. Terkecil" in sel.columns:
        sel["#Qty. Terkecil"] = safe_to_numeric(sel["#Qty. Terkecil"])
    else:
        # v3.9.67 — HARDENING FORMAT: kolom VALUE hilang dulu NA SENYAP —
        # qty IN 42.05 lenyap dari pivot tanpa jejak di log.
        print(f"  [fn_4205] WARNING: kolom VALUE '#Qty. Terkecil' tidak "
              f"ditemukan — {len(sel)} baris masuk dengan Value NA "
              f"(qty IN 42.05 lenyap — header di-rename/hilang oleh "
              f"export baru Accurate?)")
    # Datetime (only for #Tgl/Jam — NOT Tanggal #Terima, which goes through date_to_day)
    # v3.9.28: to_datetime_robust — file .xlsb (pyxlsb) memberi serial mentah;
    # pd.to_datetime biasa membacanya sbg nanodetik-epoch → 1970-01-01.
    if "#Tgl/Jam Pembuatan IT" in sel.columns:
        sel["#Tgl/Jam Pembuatan IT"] = to_datetime_robust(sel["#Tgl/Jam Pembuatan IT"])

    # Transformed: Tanggal#Terima → Date.Day, Gudang#Terima → BetweenDelimiters
    # date_to_day internally calls pd.to_datetime, so no need for separate conversion
    if "Tanggal #Terima" in sel.columns:
        sel["Tanggal #Terima"] = date_to_day(sel["Tanggal #Terima"])
    else:
        # v3.9.67 — HARDENING FORMAT: Tanggal hilang dulu NA SENYAP
        # (baris tanpa hari → lenyap dari kolom hari pivot).
        print(f"  [fn_4205] WARNING: kolom 'Tanggal #Terima' tidak "
              f"ditemukan — {len(sel)} baris masuk dengan Tanggal NA "
              f"(header di-rename/hilang oleh export baru Accurate?)")
    if "Gudang #Terima" in sel.columns:
        sel["NAMA RESTO"] = vec_text_between_delimiters(sel["Gudang #Terima"], "(", ")")

    # Renamed
    rename_map = {
        "Nomor #Terima": "Nomor",
        "Tanggal #Terima": "Tanggal",
        "#Qty. Terkecil": "Value",
    }
    # v3.9.31 — kolom konversi dibakukan ke nama standar (join key map)
    rename_map.update({orig: std for std, orig in konv.items()})
    sel = sel.rename(columns={k: v for k, v in rename_map.items() if k in sel.columns})

    # v3.9.31 — typed kolom konversi (setelah rename ke nama baku)
    for _std in (KOL_SATUAN_DOK, KOL_TERKECIL):
        if _std in sel.columns:
            sel[_std] = safe_to_str(sel[_std])
    if KOL_RASIO in sel.columns:
        sel[KOL_RASIO] = safe_to_numeric(sel[KOL_RASIO])

    # Final
    final_cols = ["Nomor", "NAMA RESTO", "Tanggal", "Nama Barang", "Value",
                  "#Tgl/Jam Pembuatan IT", KOL_SATUAN_DOK, KOL_RASIO, KOL_TERKECIL]
    for c in final_cols:
        if c not in sel.columns:
            sel[c] = pd.NA
    final = sel[final_cols].reset_index(drop=True)

    # v3.9.17: mode "lalu" — MIRROR PERSIS fn_3224(mode="lalu"): 5 hari
    # terakhir file bulan lalu (Tanggal >= maxT - 4) + Tanggal dinegasikan
    # (hari negatif = bulan lalu) → penambah IN periode ujung bulan lalu
    # (folder "4.1 4205 Bulan Lalu", permintaan user: "sama seperti 32.24
    # bulan lalu").
    # FIX R-4 (audit 34-d): mirror fn_3224 — baris resto-valid difilter
    # DULU sebelum max_t (filter & window identik fn_3224.py:54,68):
    # baris tanpa NAMA RESTO bertanggal akhir bulan tidak lagi menggeser
    # jendela 5 hari dan membuang semua baris resto. Output lalu = baris
    # resto-valid dalam jendela (identik bentuk output fn_3224 lalu);
    # mode berjalan TIDAK berubah (NA-resto tetap lolos — M-mirror asal).
    if mode == "lalu":
        # fil = Table.SelectRows(final, each [NAMA RESTO] <> null and <> "")
        mask = final["NAMA RESTO"].notna() & (
            final["NAMA RESTO"].astype(str).str.strip() != "")
        fil = final[mask].copy()
        # maxT = List.Max(fil[Tanggal])
        max_t = fil["Tanggal"].max()
        if pd.isna(max_t):
            return fil.iloc[0:0].copy()
        # fil5 = Table.SelectRows(fil, each [Tanggal] >= maxT - 4)
        # NA-safe mask: .fillna(False) for pandas < 2.1 compatibility
        mask5 = (fil["Tanggal"] >= (max_t - 4)).fillna(False)
        fil5 = fil[mask5].copy()
        # neg = Tanggal → -Tanggal
        fil5["Tanggal"] = (-fil5["Tanggal"]).astype("Int64")
        return fil5.reset_index(drop=True)

    return final
