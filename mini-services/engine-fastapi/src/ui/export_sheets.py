"""
export_sheets.py — Pembangun sheet export Excel (v3.8).

Empat bagian (dipanggil dari UI di thread worker — pure pandas + openpyxl):

1. build_selisih_export_df(base, tgl_start, tgl_end, audit_cols=None)
   Rekap Selisih IN PER RESTO (permintaan user v3.8): kolom
   Resto, Tanggal, Nama Barang, Kategori, Satuan, Hasil SO,
   Sheet Barang Masuk (input rekap), Kiriman HO (42.05),
   Kiriman Supplier (32.24), Pembelian by Resto (99.01), Selisih —
   urut Resto → Tanggal → Nama Barang, hanya baris dalam rentang
   tanggal aktif (default 1–31 bulan berjalan).
   v3.9 (permintaan user "waktu ekspor tambahin hasil auditnya aja
   tapi ada opsi buat tambahin kolom tersebut atau tidak"):
   audit_cols = daftar kolom audit opsional yang DITAMBAHKAN setelah
   Selisih — pilihan valid: "Hasil Audit", "Saldo", "Catatan Audit"
   (None/[] = tanpa kolom audit — perilaku v3.8).

2. add_pivot_sheet(writer, append1_df)
   Sheet "PIVOT" — mirror tab pivot "Mutasi Barang - New" milik user
   (dibaca langsung dari file-nya): layout identik —
     baris 1-3 : NAMA RESTO / SOURCE KIRIMAN / KATEGORI = (All)
     baris 5   : Sum of NILAI | Column Labels
     baris 6   : Row Labels | kolom tanggal -25..-31 (bulan lalu) lalu
                 1..31 — urut KRONOLOGIS
     baris 7+  : kolom A = row label (nama barang BOLD + jenis),
                 nilai = Sum of NILAI (semua resto = (All))
   CONDITIONAL FORMATTING persis file user (dxf & priority dibaca dari
   xl/styles.xml + xl/worksheets/sheet1.xml file user):
     p7  AND($A8="1.SO",B8>A8)          → font bold hijau 00B050
     p6  $A8="3.DEVIASI"                → border bawah tipis
     p5  AND($A8="7.Selisih IN",B8<>0)  → font bold merah + fill FFC9C9
     p4  cellIs = 0                     → font putih (nol "tak terlihat")
     p3  kolom A containsText "5.BARANG MASUK" → font 006100 + fill C6EFCE
     p2  kolom A containsText "4.IN"    → font 9C5700 + fill FFEB9C
     p1  header tanggal < 0 (bulan lalu)→ bold + fill biru muda
   Catatan: file lama user memakai "6.Selisih IN" (penomoran pra-v3.4);
   penomoran JENIS sejak v3.4 = "7.Selisih IN" — rumus disesuaikan,
   5 rumut lain identik karakter-per-karakter.
"""
import os

import pandas as pd
from openpyxl.formatting.rule import CellIsRule, FormulaRule, Rule
from openpyxl.styles import Border, Font, PatternFill, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.utils import get_column_letter

# Urutan metric — identik pivot_view.METRICS (satu sumber kebenaran)
from .pivot_view import PivotTableView

METRICS = list(PivotTableView.METRICS)

# Warna CF — dibaca dari dxf file "Mutasi Barang - New - Copy.xlsx"
C_SO_GREEN = "FF00B050"      # dxf14: bold + hijau
C_SELISIH_RED = "FFFF0000"   # dxf12: bold + merah
C_SELISIH_FILL = "FFFFC9C9"
C_WHITE = "FFFFFFFF"         # dxf11: font putih (nol disembunyikan)
C_IN_FONT = "FF9C5700"       # dxf9: 4.IN
C_IN_FILL = "FFFFEB9C"
C_BM_FONT = "FF006100"       # dxf10: 5.BARANG MASUK
C_BM_FILL = "FFC6EFCE"
C_HDR_FILL = "FFB4C6E7"      # dxf8: theme8 tint 0.6 (header tgl bulan lalu)

# Kolom export Selisih IN per resto (nama PERSIS permintaan user v3.8)
SELISIH_EXPORT_COLUMNS = [
    "Resto", "Tanggal", "Nama Barang", "Kategori", "Satuan", "Hasil SO",
    "Sheet Barang Masuk", "Kiriman HO", "Kiriman Supplier",
    "Pembelian by Resto", "Selisih",
]

# v3.9: kolom hasil audit OPSIONAL (ditambahkan setelah Selisih bila
# pengguna mencentangnya di dialog opsi export — sumber kolom = base)
# v3.9.30: + "PO Menunggu" (qty PO 32.43 'Menunggu diproses' per
# pasangan — penjelas deviasi murni; numerik, NaN/0 → 0.0)
# v3.9.31: nilai qty PO Menunggu TERKONVERSI ke satuan terkecil (peta
# rasio 42.05+32.24 — apple-to-apple dgn Selisih; baris tak
# terkonversi = qty satuan PO asli, penanda '*' ada di Catatan Audit)
AUDIT_EXPORT_COLUMNS = ["Hasil Audit", "Saldo", "Catatan Audit",
                        "PO Menunggu"]


# =============================================================================
# 1. REKAP SELISIH IN PER RESTO
# =============================================================================
def _num_col(f: pd.DataFrame, name: str) -> pd.Series:
    """Kolom numerik defensif — kolom hilang → Series NA (bukan scalar)."""
    if name in f.columns:
        return pd.to_numeric(f[name], errors="coerce")
    return pd.Series(pd.NA, index=f.index, dtype="Float64")


def build_selisih_export_df(base: pd.DataFrame, tgl_start: int = 1,
                            tgl_end: int = 31,
                            audit_cols: list | None = None) -> pd.DataFrame:
    """Bangun tabel rekap Selisih IN per resto dari base (keluaran
    InSelisihView._compute_base — sudah membawa komponen 42.05/32.24/99.01).

    - Filter: rentang tanggal aktif (default 1–31 = bulan berjalan saja).
    - Urut: Resto → Tanggal → Nama Barang.
    - Hasil SO: NaN → sel kosong (tanggal tanpa SO tercatat);
      komponen IN & selisih: NaN → 0.
    - v3.9: audit_cols = subset ["Hasil Audit", "Saldo", "Catatan Audit"]
      → kolom tsb DITAMBAHKAN setelah Selisih (None/[] = tanpa audit).
      "Saldo" mengikuti nilai audit dari data PENUH (bukan rentang tampilan)
      — konsisten dgn kolom Saldo di tabel UI.
    """
    audit_cols = [c for c in (audit_cols or [])
                  if c in AUDIT_EXPORT_COLUMNS]
    empty = pd.DataFrame(columns=SELISIH_EXPORT_COLUMNS + audit_cols)
    if base is None or base.empty:
        return empty

    f = base
    t = pd.to_numeric(f["Tanggal"], errors="coerce")
    f = f[(t >= tgl_start) & (t <= tgl_end)]
    if f.empty:
        return empty

    out = pd.DataFrame({
        "Resto": f["Resto"].astype(str),
        "Tanggal": pd.to_numeric(f["Tanggal"], errors="coerce")
                      .astype("Int64"),
        "Nama Barang": f["Nama Barang"].astype(str),
        # FIX R7 (audit 37-a): None/pd.NA jangan menjadi literal "None"
        # di Excel — bersihkan dgn fillna("") (astype(str) saja menulis
        # 'None'/'<NA>').
        "Kategori": (f["KATEGORI"].fillna("").astype(str)
                     if "KATEGORI" in f.columns else
                     pd.Series(["-"] * len(f), index=f.index)),
        "Satuan": (f["Satuan"].fillna("").astype(str)
                   if "Satuan" in f.columns else
                   pd.Series(["-"] * len(f), index=f.index)),
        "Hasil SO": _num_col(f, "Hasil SO"),
        "Sheet Barang Masuk": _num_col(f, "Barang Masuk").fillna(0.0),
        "Kiriman HO": _num_col(f, "42.05").fillna(0.0),
        "Kiriman Supplier": _num_col(f, "32.24").fillna(0.0),
        "Pembelian by Resto": _num_col(f, "99.01").fillna(0.0),
        "Selisih": _num_col(f, "Selisih IN").fillna(0.0),
    })

    # v3.9: kolom hasil audit opsional — dibangun SEBELUM sort_values
    # (assignment Series sejajar INDEX f; setelah reset_index(drop=True)
    # index-nya berubah → nilai akan salah baris bila ditambahkan belakangan).
    # Sumber = base: nilai audit dihitung dari data PENUH oleh fn_audit,
    # tidak terpotong rentang tanggal tampilan (konsisten dgn UI).
    for col in audit_cols:
        if col == "Saldo":
            out[col] = _num_col(f, "Saldo").astype("Float64")
        elif col == "PO Menunggu":   # v3.9.30 — numerik (pair-level)
            # v3.9.31 — nilai terkonversi satuan terkecil (fallback qty
            # PO asli utk pasangan tak terkonversi — label '*' di catatan)
            out[col] = _num_col(f, "PO Menunggu").fillna(0.0)
        elif col in f.columns:
            out[col] = f[col].astype(str)
        else:
            out[col] = ""

    out = out.sort_values(["Resto", "Tanggal", "Nama Barang"],
                          kind="mergesort", na_position="last") \
        .reset_index(drop=True)
    # Hasil SO NaN → None (sel kosong di Excel, bukan 0)
    out["Hasil SO"] = out["Hasil SO"].astype("Float64").where(
        out["Hasil SO"].notna(), other=None)
    return out[SELISIH_EXPORT_COLUMNS + audit_cols]


def write_selisih_sheet(writer, df: pd.DataFrame,
                        sheet_name: str = "Selisih IN per Resto") -> None:
    """Tulis df (keluaran build_selisih_export_df) ke sheet aktif writer +
    styling: header bold, freeze panes, autofilter, lebar kolom."""
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]

    head_font = Font(bold=True, color="FF1E293B")
    head_fill = PatternFill("solid", start_color="FFE2E8F0",
                            end_color="FFE2E8F0")
    for cell in ws[1]:
        cell.font = head_font
        cell.fill = head_fill

    widths = {
        "Resto": 14, "Tanggal": 10, "Nama Barang": 32, "Kategori": 18,
        "Satuan": 10, "Hasil SO": 14, "Sheet Barang Masuk": 18,
        "Kiriman HO": 14, "Kiriman Supplier": 16,
        "Pembelian by Resto": 18, "Selisih": 14,
        # v3.9: kolom audit opsional
        "Hasil Audit": 22, "Saldo": 12, "Catatan Audit": 40,
        "PO Menunggu": 14,   # v3.9.30
    }
    for j, col in enumerate(df.columns, start=1):
        ws.column_dimensions[get_column_letter(j)].width = \
            widths.get(col, 12)
    ws.freeze_panes = "A2"
    if len(df) > 0:
        ws.auto_filter.ref = (f"A1:{get_column_letter(len(df.columns))}"
                              f"{len(df) + 1}")


# =============================================================================
# 2. SHEET PIVOT (mirror "Mutasi Barang - New" user)
# =============================================================================
def _chrono(v):
    """Urut kronologis: hari negatif (bulan lalu) -25 → -31 lalu 1..31
    (identik pivot_view._chrono)."""
    try:
        iv = int(v)
        return (0, -iv) if iv < 0 else (1, iv)
    except (TypeError, ValueError):
        return (2, str(v))


def build_pivot_matrix(append1_df: pd.DataFrame) -> tuple:
    """Pivot Sum of NILAI: baris = Nama Barang (header) × JENIS (metric),
    kolom = Tanggal urut kronologis. Return (rows, date_cols) dengan
    rows = list (label, is_item, values-atau-None). Pure — tanpa openpyxl."""
    if append1_df is None or append1_df.empty:
        return [], []
    df = append1_df
    if not {"Nama Barang", "JENIS", "Tanggal", "NILAI"} <= set(df.columns):
        return [], []

    p = df.pivot_table(index=["Nama Barang", "JENIS"], columns="Tanggal",
                       values="NILAI", aggfunc="sum", fill_value=0)
    if p.empty:
        return [], []

    date_cols = sorted(p.columns.tolist(), key=_chrono)
    p = p[date_cols].reset_index()

    rank = {m: i for i, m in enumerate(METRICS)}
    p = p.assign(__rank=p["JENIS"].map(
        lambda j: rank.get(str(j), len(METRICS))))
    p = p.sort_values(["Nama Barang", "__rank", "JENIS"],
                      kind="mergesort")

    labels = p["Nama Barang"].tolist()
    jenis = p["JENIS"].tolist()
    vals = p[date_cols].to_numpy(dtype="float64")

    rows = []
    prev_item = None
    for i in range(len(p)):
        item = str(labels[i])
        if item != prev_item:
            rows.append((item, True, None))
            prev_item = item
        rows.append((str(jenis[i]), False, vals[i]))
    return rows, date_cols


def add_pivot_sheet(writer, append1_df: pd.DataFrame,
                    sheet_name: str = "PIVOT") -> bool:
    """Tambah sheet PIVOT ke writer aktif (panggil SEBELUM sheet lain agar
    jadi tab pertama). Return True bila sheet dibuat."""
    rows, date_cols = build_pivot_matrix(append1_df)
    if not rows or not date_cols:
        return False

    wb = writer.book
    if sheet_name in wb.sheetnames:      # idempoten saat re-export
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    # --- layout identik tab pivot file user ---
    ws["A1"] = "NAMA RESTO"
    ws["B1"] = "(All)"
    ws["A2"] = "SOURCE KIRIMAN"
    ws["B2"] = "(All)"
    ws["A3"] = "KATEGORI"
    ws["B3"] = "(All)"
    ws["A5"] = "Sum of NILAI"
    ws["B5"] = "Column Labels"
    ws["A6"] = "Row Labels"
    for j, t in enumerate(date_cols, start=2):
        c = ws.cell(row=6, column=j)
        try:
            c.value = int(t)
        except (TypeError, ValueError):
            c.value = t

    bold = Font(bold=True)
    r = 7
    first_metric_row = None
    for label, is_item, vals in rows:
        cell = ws.cell(row=r, column=1, value=label)
        if is_item:
            cell.font = bold
        else:
            if first_metric_row is None:
                first_metric_row = r
            if vals is not None:
                for j, v in enumerate(vals, start=2):
                    ws.cell(row=r, column=j, value=float(v))
        r += 1
    last_row = r - 1
    last_col = get_column_letter(1 + len(date_cols))

    ws.column_dimensions["A"].width = 30
    for j in range(2, 2 + len(date_cols)):
        ws.column_dimensions[get_column_letter(j)].width = 11
    ws.freeze_panes = "B7"

    # --- conditional formatting (persis file user; anchor baris metric
    #     pertama = baris 8 pada layout standar) ---
    a = first_metric_row if first_metric_row is not None else 8

    # p1: header tanggal < 0 (bulan lalu) → bold + fill biru muda
    ws.conditional_formatting.add(
        f"B6:{last_col}6",
        CellIsRule(operator="lessThan", formula=["0"],
                   font=Font(bold=True),
                   fill=PatternFill(start_color=C_HDR_FILL,
                                    end_color=C_HDR_FILL, fill_type="solid")))

    # p2: kolom A containsText "4.IN" → font amber + fill kuning
    rule_in = Rule(
        type="containsText", operator="containsText", text="4.IN",
        dxf=DifferentialStyle(
            font=Font(color=C_IN_FONT),
            fill=PatternFill(bgColor=C_IN_FILL)))
    rule_in.formula = ['NOT(ISERROR(SEARCH("4.IN",A7)))']
    ws.conditional_formatting.add(f"A7:A{last_row}", rule_in)

    # p3: kolom A containsText "5.BARANG MASUK" → font hijau + fill hijau
    rule_bm = Rule(
        type="containsText", operator="containsText", text="5.BARANG MASUK",
        dxf=DifferentialStyle(
            font=Font(color=C_BM_FONT),
            fill=PatternFill(bgColor=C_BM_FILL)))
    rule_bm.formula = ['NOT(ISERROR(SEARCH("5.BARANG MASUK",A7)))']
    ws.conditional_formatting.add(f"A7:A{last_row}", rule_bm)

    data_range = f"B{a}:{last_col}{last_row}"

    # p4: cellIs = 0 → font putih (nol "tak terlihat" — trik file user)
    ws.conditional_formatting.add(
        data_range,
        CellIsRule(operator="equal", formula=["0"],
                   font=Font(color=C_WHITE)))

    # p5: Selisih IN ≠ 0 → bold merah + fill merah muda
    ws.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f'AND($A{a}="7.Selisih IN",B{a}<>0)'],
            font=Font(bold=True, color=C_SELISIH_RED),
            fill=PatternFill(start_color=C_SELISIH_FILL,
                             end_color=C_SELISIH_FILL, fill_type="solid")))

    # p6: baris DEVIASI → border bawah tipis
    ws.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f'$A{a}="3.DEVIASI"'],
            border=Border(bottom=Side(style="thin"))))

    # p7: baris 1.SO + B8>A8 → bold hijau (rumus user, verbatim)
    ws.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f'AND($A{a}="1.SO",B{a}>A{a})'],
            font=Font(bold=True, color=C_SO_GREEN)))

    return True


# =============================================================================
# 3. SHEET PIVOT SESUAI TAMPILAN (v3.9.2 — export tombol 💾 di tab Pivot)
# =============================================================================
def _col_label(c) -> str:
    """Label kolom persis heading UI: tgl bulan lalu = '25•' (legend •)."""
    try:
        ci = int(float(str(c)))
        return f"{abs(ci)}•" if ci < 0 else str(ci)
    except (TypeError, ValueError):
        return str(c)


def _is_int(v: float) -> bool:
    try:
        return float(v) == int(float(v))
    except (TypeError, ValueError):
        return False


def write_pivot_display_sheet(filepath: str, payload: dict,
                              visible_cols: list | None = None,
                              sheet_name: str = "PIVOT") -> int:
    """v3.9.2 — Export TABEL PIVOT SESUAI TAMPILAN ke file .xlsx tunggal
    (permintaan user: "pivot tabel nya bisa export excel").

    payload = hasil PivotTableView._compute_payload — sudah memperhitungkan
    filter RESTO/SOURCE/KATEGORI + rentang TANGGAL + mode 🏪 resto / 📅
    tanggal + ☑ sembunyikan baris kosong. visible_cols = daftar kolom yang
    TAMPIL di tabel (displaycolumns — None = semua kolom payload).

    Style mirror UI v3.9.2 (minus merah PER CELL, bukan per baris):
    - header kolom tanggal bulan lalu (label 25•) → bold + fill biru muda
    - baris nama barang → bold + fill abu (ala tag item_header)
    - baris 4.IN / 5.BARANG MASUK → warna metric utuh (fg+bg)
    - baris 7.Selisih IN (ada nilai ≠ 0) → fill merah muda (ala anomaly)
    - nilai MINUS → font merah hanya di CELL itu (kurung ala UI)
    - nilai 0 → font putih "tak terlihat" (trik file user, CF p4)
    Return jumlah baris data yang ditulis.
    """
    rows = payload.get("rows_data") or []
    columns = [str(c) for c in payload.get("columns") or []]
    if not rows or not columns:
        return 0

    # kolom tampil (urut displaycolumns tree bila diberikan)
    if visible_cols:
        vis = [str(c) for c in visible_cols]
        idx = [i for i, c in enumerate(columns) if c in vis]
    else:
        idx = list(range(len(columns)))
    if not idx:
        idx = list(range(len(columns)))

    st = payload.get("filters") or {}
    mode = st.get("mode") or payload.get("col_kind") or "resto"
    mode_label = "Per Tanggal" if mode == "tanggal" else "Per Resto"
    t1, t2 = st.get("tgl_start", 1), st.get("tgl_end", 31)

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]

    # --- baris filter (ala layout "Mutasi Barang - New" + info mode) ---
    meta = [
        ("MODE", mode_label),
        ("NAMA RESTO", str(st.get("resto", "(All)"))),
        ("SOURCE KIRIMAN", str(st.get("source", "(All)"))),
        ("KATEGORI", str(st.get("kategori", "(All)"))),
    ]
    for i, (k, v) in enumerate(meta, start=1):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True,
                                                      color="FF475569")
        ws.cell(row=i, column=2, value=v)
    ws.cell(row=5, column=1, value="TANGGAL").font = Font(bold=True,
                                                          color="FF475569")
    ws.cell(row=5, column=2,
            value=f"{t1} s/d {t2} (negatif = bulan lalu)")
    ws.cell(row=6, column=1, value="Sum of NILAI").font = Font(bold=True)
    ws.cell(row=6, column=2, value="Column Labels").font = Font(bold=True)
    hdr = ws.cell(row=7, column=1, value="Row Labels")
    hdr.font = Font(bold=True)
    hdr.fill = PatternFill(start_color="FFE2E8F0", end_color="FFE2E8F0",
                           fill_type="solid")

    # header kolom — label persis UI (25• = bulan lalu → biru muda bold)
    for j, ci in enumerate(idx, start=2):
        c = columns[ci]
        cell = ws.cell(row=7, column=j, value=_col_label(c))
        cell.font = Font(bold=True)
        try:
            if int(float(str(c))) < 0:
                cell.fill = PatternFill(start_color=C_HDR_FILL,
                                        end_color=C_HDR_FILL,
                                        fill_type="solid")
        except (TypeError, ValueError):
            pass

    # --- data ---
    METRIC_BG = {k: v for k, v in PivotTableView.METRIC_BG.items()}
    fmt_int, fmt_dec = "#,##0;(#,##0)", "#,##0.0;(#,##0.0)"
    r = 8
    n_data = 0
    for iid, label, is_item, metric, vals in rows:
        cell = ws.cell(row=r, column=1, value=str(label))
        if is_item:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="FFE2E8F0",
                                    end_color="FFE2E8F0", fill_type="solid")
        else:
            n_data += 1
            # fill + fg baris metric — mirror tag UI (in/bm/anomaly/bg)
            fill = None
            fg = None
            if metric == "4.IN":
                fill, fg = C_IN_FILL, C_IN_FONT
            elif metric == "5.BARANG MASUK":
                fill, fg = C_BM_FILL, C_BM_FONT
            elif metric == "7.Selisih IN":
                fill = C_SELISIH_FILL   # fg dipecah per-cell di bawah
            else:
                bg = METRIC_BG.get(metric)
                if bg:
                    fill = "FF" + bg.lstrip("#").upper()
            if fill:
                cell.fill = PatternFill(start_color=fill, end_color=fill,
                                        fill_type="solid")
            if fg:
                cell.font = Font(color=fg)
            for j, ci in enumerate(idx, start=2):
                try:
                    v = float(vals[ci])
                except (TypeError, ValueError, IndexError):
                    continue
                vc = ws.cell(row=r, column=j, value=v)
                vc.number_format = fmt_int if _is_int(v) else fmt_dec
                # MINUS → font merah PER CELL (permintaan v3.9.2);
                # Selisih IN ≠ 0 → merah (anomaly per cell, mirror UI)
                red = v < 0 or (metric == "7.Selisih IN" and v != 0)
                if red:
                    vc.font = Font(color="FFCC0000",
                                   bold=metric == "7.Selisih IN")
                elif v == 0:
                    vc.font = Font(color=C_WHITE)   # nol tak terlihat
                elif fg:
                    vc.font = Font(color=fg)
        r += 1
    last_row = r - 1

    # catatan legenda
    note = ws.cell(row=last_row + 2, column=1,
                   value="• = tanggal bulan lalu · nilai dalam kurung = minus "
                         "(font merah) · 0 disembunyikan (font putih)")
    note.font = Font(italic=True, color="FF94A3B8")

    ws.column_dimensions["A"].width = 30
    for j in range(2, 2 + len(idx)):
        ws.column_dimensions[get_column_letter(j)].width = 11
    ws.freeze_panes = "B8"

    # v3.9.59 — FIX 2f-04 (audit 2-f): tulis ATOMIK (tmp + os.replace —
    # pola 6a-02 app._export_excel). wb.save(filepath) dulu menulis
    # LANGSUNG ke path tujuan → exception di tengah (disk penuh / error
    # styling) meninggalkan .xlsx PARSIAL yang MENIMPA export LAMA yang
    # baik di path sama. Kini file tujuan hanya tersentuh os.replace()
    # atomik SETELAH sukses penuh; kegagalan apa pun (finally) menghapus
    # tmp (tmp ber-ekstensi .xlsx — ekstensi .tmp polos dihindari demi
    # konsistensi dgn pola app & file manager preview).
    tmp_path = str(filepath) + ".tmp.xlsx"
    _ok = False
    try:
        wb.save(tmp_path)
        os.replace(tmp_path, str(filepath))
        _ok = True
    finally:
        if not _ok:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass
    return n_data
