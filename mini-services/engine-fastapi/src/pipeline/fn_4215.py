"""
fn_4215.py — Mirror persis fn4215 di M code.
Pemindahan Barang (modul 42.15) → sumber OUT (kirim) atau IN (terima).
OPTIMIZED: vectorized text operations.

v3.9.33 — AUDIT FIX (48-a):
- guard kolom — identitas ('Gudang Pengirim'/'Gudang Tujuan' → NAMA
  RESTO, 'Nama Barang') hilang → WARNING keras + baris dibuang
  (degradasi per-sumber, bukan KeyError total); VALUE ('Kts Diterima'/
  'Tanggal') hilang → NA. Loop NA-fill final_cols (dulu DEAD CODE —
  KeyError selalu terjadi lebih dulu) kini benar-benar reachable —
  schema output tetap IDENTIK.
- sheet_name param — queries.query_4215_gudang_kirim me-resolve key
  config Sheets['Pemindahan4215'] (config lama tanpa key tetap dapat
  default).

v3.9.67 — HARDENING KETAHANAN FORMAT EXPORT (audit ketahanan format
export Accurate, user: "misal suatu saat format tarikan dari accurate
berubah aman gak?"): kolom VALUE ('Kts Diterima') & 'Tanggal' yang
hilang/di-rename kini DI-WARNING keras di loop NA-fill final_cols
(mencakup cabang kirim & terima) — dulu NA SENYAP (qty pemindahan
42.15 lenyap tanpa jejak log; pola fn_2205 v3.9.67). Perilaku data
TIDAK berubah.
"""
import pandas as pd

from .helpers import (
    date_to_day,
    fn_combine_folder,
    safe_to_numeric,
    safe_to_str,
    vec_text_between_delimiters,
)

# Nama sheet standar 42.15 (export Accurate) — v3.9.33 default param
SHEET_4215 = "#42.15. Pemindahan Barang (KIRI"


def fn_4215(folder_path: str, side: str,
            sheet_name: str = SHEET_4215) -> pd.DataFrame:
    """
    Mirror M: fn4215(folderPath, side).
    side: "kirim" (Gudang Pengirim → NAMA RESTO) atau "terima" (Gudang Tujuan → NAMA RESTO).

    sheet_name: v3.9.33 — AUDIT FIX (48-a): default SHEET_4215; query
    me-resolve config Sheets['Pemindahan4215'].
    """
    prom = fn_combine_folder(folder_path, sheet_name, header_row=4)
    if prom.empty:
        return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

    # v3.9.33 — AUDIT FIX (48-a): kolom IDENTITAS hilang (header bergeser)
    # → dulu KeyError mematikan SELURUH pipeline. Sekarang: WARNING keras
    # (nama kolom + jumlah baris) + baris dibuang → frame kosong
    # ber-schema standar (degradasi per-sumber; schema output IDENTIK).
    if side == "kirim":
        needed = ["Tanggal", "Gudang Pengirim", "Nama Barang", "Kts Diterima"]
        available = [c for c in needed if c in prom.columns]
        sel = prom[available].copy()
        _ident_hilang = [c for c in ("Gudang Pengirim", "Nama Barang")
                         if c not in sel.columns]
        if _ident_hilang:
            print(f"  [fn_4215] WARNING: kolom identitas hilang "
                  f"{_ident_hilang} — {len(sel)} baris dibuang (header file "
                  f"bergeser? pipeline lanjut tanpa sumber 42.15 kirim ini)")
            return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

        # typed: vectorized
        sel["Gudang Pengirim"] = safe_to_str(sel["Gudang Pengirim"])
        sel["Nama Barang"] = safe_to_str(sel["Nama Barang"])
        # v3.9.33 — AUDIT FIX (48-a): VALUE hilang → NA (bukan KeyError)
        if "Kts Diterima" in sel.columns:
            sel["Kts Diterima"] = safe_to_numeric(sel["Kts Diterima"])

        # ext: vectorized
        if "Tanggal" in sel.columns:
            sel["Tanggal"] = date_to_day(sel["Tanggal"])
        sel["NAMA RESTO"] = vec_text_between_delimiters(sel["Gudang Pengirim"], "(", ")")

        if "Kts Diterima" in sel.columns:
            sel = sel.rename(columns={"Kts Diterima": "Value"})
    else:
        needed = ["Tanggal", "Nama Barang", "Kts Diterima", "Gudang Tujuan"]
        available = [c for c in needed if c in prom.columns]
        sel = prom[available].copy()
        _ident_hilang = [c for c in ("Gudang Tujuan", "Nama Barang")
                         if c not in sel.columns]
        if _ident_hilang:
            print(f"  [fn_4215] WARNING: kolom identitas hilang "
                  f"{_ident_hilang} — {len(sel)} baris dibuang (header file "
                  f"bergeser? pipeline lanjut tanpa sumber 42.15 terima ini)")
            return pd.DataFrame(columns=["Tanggal", "NAMA RESTO", "Nama Barang", "Value"])

        sel["Nama Barang"] = safe_to_str(sel["Nama Barang"])
        # v3.9.33 — AUDIT FIX (48-a): VALUE hilang → NA (bukan KeyError)
        if "Kts Diterima" in sel.columns:
            sel["Kts Diterima"] = safe_to_numeric(sel["Kts Diterima"])
        sel["Gudang Tujuan"] = safe_to_str(sel["Gudang Tujuan"])

        if "Tanggal" in sel.columns:
            sel["Tanggal"] = date_to_day(sel["Tanggal"])
        sel["NAMA RESTO"] = vec_text_between_delimiters(sel["Gudang Tujuan"], "(", ")")

        if "Kts Diterima" in sel.columns:
            sel = sel.rename(columns={"Kts Diterima": "Value"})

    final_cols = ["Tanggal", "NAMA RESTO", "Nama Barang", "Value"]
    for c in final_cols:
        if c not in sel.columns:
            # v3.9.33 — AUDIT FIX (48-a): loop NA-fill kini REACHABLE
            # (dulu dead code — KeyError terjadi lebih awal); dtype
            # disesuaikan kolomnya supaya concat query tetap konsisten.
            # v3.9.67 — HARDENING FORMAT: VALUE/Tanggal hilang kini ikut
            # DI-WARNING (dulu NA SENYAP — qty pemindahan 42.15 lenyap
            # tanpa jejak log; pola fn_2205 v3.9.67).
            if c == "Tanggal":
                print(f"  [fn_4215] WARNING: kolom 'Tanggal' tidak "
                      f"ditemukan — {len(sel)} baris masuk dengan "
                      f"Tanggal NA (header di-rename/hilang oleh export "
                      f"baru Accurate?)")
                sel[c] = pd.array([pd.NA] * len(sel), dtype="Int64")
            elif c == "Value":
                print(f"  [fn_4215] WARNING: kolom VALUE 'Kts Diterima' "
                      f"tidak ditemukan — {len(sel)} baris masuk dengan "
                      f"Value NA (qty pemindahan 42.15 {side} lenyap — "
                      f"header di-rename/hilang oleh export baru "
                      f"Accurate?)")
                sel[c] = pd.Series([float("nan")] * len(sel), index=sel.index)
            else:
                sel[c] = pd.NA
    result = sel[final_cols].reset_index(drop=True)

    return result
