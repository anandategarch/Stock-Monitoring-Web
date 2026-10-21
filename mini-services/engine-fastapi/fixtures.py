"""
fixtures.py — Generator bundle mock Accurate untuk SM-FastAPI-Engine.

PORT VERBATIM dari test_mock.py desktop v3.9.71 (fungsi create_mock_*,
0-perubahan-angka) — inilah fixture yang sama dengan baterai tes desktop
(1607/1607 PASS), sehingga verifikasi AC-B ("output POST /process pada
fixture mock = angka yang sama dengan test_mock.py desktop") memakai
data identik. Satu-satunya adaptasi: create_mock_rincian_po menerima
barang_list eksplisit (bukan global barbar_list) + build_fixture_bundle()
merakit pohon folder sesuai config template + menghasilkan config dict.

Dipakai oleh golden_check.py (gerbang paritas §11.2) — bukan dipakai
 oleh /process produksi (yang membaca bundle real).
"""
import os
from datetime import datetime

import openpyxl


def create_mock_file(filepath, sheet_name, headers, data_rows, metadata_rows=4):
    """Create a mock Excel file matching Accurate export format.
    metadata_rows: jumlah row metadata SEBELUM header row (default 4 = rows 1-4).
    Header row is at index metadata_rows (row 5 if metadata_rows=4).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]  # Excel sheet name max 31 chars

    # Write metadata rows (rows 1 to metadata_rows)
    for i in range(metadata_rows):
        ws.cell(row=i + 1, column=1, value=f"Metadata {i+1} - {sheet_name}")

    # Write header row (row metadata_rows + 1)
    header_row = metadata_rows + 1
    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=header_row, column=col_idx, value=header)

    # Write data rows
    for row_idx, row_data in enumerate(data_rows, header_row + 1):
        for col_idx, val in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_rekap_mentah(filepath, resto_code, barang_list, mode="berjalan"):
    """Create REKAP MENTAH sheet (header at row 1, no metadata)."""
    headers = ["NAMA RESTO", "SOURCE DATA", "JENIS", "STATUS", "NAMA BARANG", "SATUAN"]
    if mode == "berjalan":
        headers += [str(d) for d in range(1, 32)]  # 1..31
    else:
        headers += [str(d) for d in range(25, 32)]  # 25..31

    data_rows = []
    for barang, satuan in barang_list:
        # SO row (SOURCE DATA "input so harian" — varian promix dites desktop §29)
        row = [f"{resto_code}.001", "input so harian", "SO", "OK", barang, satuan]
        row += [100 if d == 1 else 0 for d in (range(1, 32) if mode == "berjalan" else range(25, 32))]
        data_rows.append(row)
        # BARANG MASUK row
        row = [f"{resto_code}.001", "input so harian", "BARANG MASUK", "OK", barang, satuan]
        row += [50 if d == 1 else 0 for d in (range(1, 32) if mode == "berjalan" else range(25, 32))]
        data_rows.append(row)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "REKAP MENTAH"
    for col_idx, h in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=h)
    for row_idx, row_data in enumerate(data_rows, 2):
        for col_idx, val in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_2205(filepath, resto_code, barang_list):
    """Create #22.05 sheet (4 metadata rows, header at row 5)."""
    headers = ["Nomor #", "Tanggal", "Nama Pelanggan", "Nama Barang", "Kuantitas"]
    data_rows = []
    for i, (barang, _) in enumerate(barang_list):
        data_rows.append([
            f"ACR.2026.09.{1000+i}",
            datetime(2026, 9, 5),
            f"RESTO MALANG ({resto_code})",
            barang,
            10 + i
        ])
    create_mock_file(filepath, "#22.05. Rincian Penjualan per B", headers, data_rows, metadata_rows=4)


def create_mock_3224(filepath, resto_code, barang_list, mode="berjalan"):
    """Create #32.24 sheet (konversi KG→GR rasio 1000 — uji konversi PO)."""
    headers = ["Tanggal", "Kts (Unit#1)", "Nama Barang", "Nama Gudang",
               "Nomor # RI", "Nomor # PO", "Tgl/Jam Pembuatan",
               "Satuan", "Rasio Satuan"]
    data_rows = []
    for i, (barang, satuan) in enumerate(barang_list):
        tgl = 5 if mode == "berjalan" else 28
        data_rows.append([
            datetime(2026, 9, tgl),
            20 + i,
            barang,
            f"GUDANG MALANG ({resto_code})",
            f"IT.2026.09.{2000+i}",
            f"PO.2026.09.{3000+i}",
            datetime(2026, 9, 3, 16, 52, 12),
            satuan,          # satuan dokumen (KG)
            1000,            # rasio → satuan terkecil (GR)
        ])
    create_mock_file(filepath, "#32.24. Rincian Penerimaan Bara", headers, data_rows, metadata_rows=4)


def create_mock_4215(filepath, resto_code, barang_list):
    """Create #42.15 sheet (kirim)."""
    headers = ["Tanggal", "Gudang Pengirim", "Nama Barang", "Kts Diterima"]
    data_rows = []
    for i, (barang, _) in enumerate(barang_list):
        data_rows.append([
            datetime(2026, 9, 5),
            f"GUDANG MALANG ({resto_code})",
            barang,
            5 + i
        ])
    create_mock_file(filepath, "#42.15. Pemindahan Barang (KIRI", headers, data_rows, metadata_rows=4)


def create_mock_4205(filepath, resto_code, barang_list, mode="berjalan"):
    """Create #42.05 sheet (mode 'lalu': tanggal ujung bulan = 28)."""
    headers = ["Nomor #Terima", "Gudang #Terima", "Tanggal #Terima", "Nama Barang",
               "#Qty. Terkecil", "#Tgl/Jam Pembuatan IT",
               "#Sat. Kirim", "Rasio Satuan", "#Sat. Terkecil"]
    data_rows = []
    tgl = 5 if mode == "berjalan" else 28
    nomor_base = 4000 if mode == "berjalan" else 5000
    for i, (barang, satuan) in enumerate(barang_list):
        data_rows.append([
            f"IT.2026.09.{nomor_base+i}",
            f"GUDANG BANDUNG ({resto_code})",
            datetime(2026, 9, tgl),
            barang,
            15 + i,
            datetime(2026, 9, tgl - 1, 10, 30, 0),
            satuan,          # #Sat. Kirim (satuan dokumen KG)
            1000,            # Rasio Satuan
            "GR",            # #Sat. Terkecil
        ])
    create_mock_file(filepath, "#42.05. Rincian Pemindahan Bara", headers, data_rows, metadata_rows=4)


def create_mock_4217(filepath, resto_code, barang_list):
    """Create #42.17 sheet (saldo awal) — termasuk BUMBU PASTA KUAH
    (saldo-only) & SUPPLIES ITEM (kategori luar whitelist → terfilter)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "#42.17. Kuantitas Barang per Gu"

    for i in range(4):
        ws.cell(row=i + 1, column=1, value=f"Metadata {i+1}")

    ws.cell(row=5, column=1, value="Nama Barang")
    ws.cell(row=5, column=2, value="Kode Barang")
    ws.cell(row=5, column=3, value="Kategori Barang")
    ws.cell(row=5, column=4, value="Nama Satuan")
    ws.cell(row=5, column=5, value=f"RESTO MALANG ({resto_code})")

    rows = []
    for i, (barang, satuan) in enumerate(barang_list):
        rows.append([barang, 90000 + i,
                     "10.FOOD [RM] - COM V.2" if i == 0 else None,
                     satuan, 200 + i * 10])
    rows.append(["BUMBU PASTA KUAH", 90999,
                 "10.FOOD [RM] - COM V.2", "GR", 84])
    rows.append(["SUPPLIES ITEM", 90998,
                 "SUPPLIES [OTHERS]", "PCS", 999])

    for r_idx, row_data in enumerate(rows, 6):
        for c_idx, val in enumerate(row_data, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_4109(filepath, barang_list):
    """Create #41.09. Nilai Persediaan [ALL] (folder 09.Harga) — struktur
    2-baris header + subtotal + kategori ber-pola header grup (ffill)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    # openpyxl tak bisa menulis '[' pada judul sheet — fn_4109 punya
    # fallback resolusi nama sheet ternormalisasi (buang [ ] ( ) spasi).
    ws.title = "#41.09. Nilai Persediaan ALL"

    ws.cell(row=1, column=4, value="PPA")
    ws.cell(row=2, column=4, value="#41.09. Nilai Persediaan [ALL]")
    ws.cell(row=3, column=4, value="Dari 01 Okt 2026 s/d 07 Okt 2026")
    ws.cell(row=4, column=4, value="Cabang : [Semua Cabang]")

    hdr = {4: ["Kategori Barang", "Nama Barang", None, None,
               "Kode Barang", "Nama Satuan", "Saldo Awal", None, "Masuk",
               None, "Keluar", None, None, "Saldo Akhir", None],
           5: [None, None, None, None, None, None, "Kuantitas", "Nilai",
               "Kuantitas", "Nilai", "Kuantitas", None, "Nilai",
               "Kuantitas", "Nilai"]}
    for r, vals in hdr.items():
        for c, v in enumerate(vals, 1):
            if v is not None:
                ws.cell(row=r, column=c, value=v)

    data = {
        "GULA (V.20)":        ("GR", 1000, 18250),    # 18,25/GR
        "FRUCTOSE SYRUP (V.20)": ("GR", 0, 0),        # Qty 0 → NaN
        "CINCAU (V.20)":      ("KG", 500, 7500),      # 15/KG
        "BUMBU PASTA KUAH":   ("GR", 700, 8400),      # 12/GR
    }
    rows = []
    kat_first = True
    for barang, (sat, qty, nil) in data.items():
        rows.append(["10.FOOD [RM] - COM V.2" if kat_first else None,
                     barang, None, None, 88001, sat,
                     qty, nil, 0, 0, 0, None, 0, qty, nil])
        kat_first = False
    rows.append(["21.COST.ASSET", "BARANG ASSET LAIN", None, None,
                 88999, "UNIT", 5, 5000, 0, 0, 0, None, 0, 5, 5000])
    rows.append([None, "Total Nama Barang", None, None, None, None,
                 None, None, None, None, None, None, None,
                 sum(r[13] or 0 for r in rows), None])

    for r_idx, row_data in enumerate(rows, 7):
        for c_idx, val in enumerate(row_data, 1):
            if val is not None:
                ws.cell(row=r_idx, column=c_idx, value=val)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_9901(filepath, resto, barang_list):
    """Create mock 9901 (mutasi tanpa nomor penerimaan). Nama cabang '1137.<RESTO>'."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    headers = ["Nomor # Penerimaan Barang", "Jenis Barang Barang & Jasa",
               "#Prime.Qty", "Nama barang", "Nama cabang", "Tanggal"]
    for col_idx, h in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=h)

    rows = []
    for i, (barang, _) in enumerate(barang_list[:2]):
        rows.append([None, "Persediaan", 5.0 * (i + 1), barang,
                     f"1137.{resto}", 5 + i])
    rows.append(["RI-900", "Persediaan", 99.0, barang_list[0][0],
                 f"1137.{resto}", 7])

    for r_idx, row_data in enumerate(rows, 2):
        for c_idx, val in enumerate(row_data, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_dbs_kategori(filepath, barang_list):
    """Create Sheet1 (DBS kategori). Header at row 1."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    headers = ["NAMA BARANG", "KATEGORI", "JENIS", "SOURCE KIRIMAN"]
    for col_idx, h in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=h)

    for i, (barang, _) in enumerate(barang_list):
        ws.cell(row=2 + i, column=1, value=barang)
        ws.cell(row=2 + i, column=2, value="DEVIASI")
        ws.cell(row=2 + i, column=3, value="BAHAN BAKU")
        ws.cell(row=2 + i, column=4, value="INTERNAL")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    wb.close()


def create_mock_rincian_po(filepath, resto_code, barang_list):
    """Create #32.43 sheet (rincian PO). 5 metadata rows (skip 4+1), header at row 5."""
    headers = ["Nomor #", "Tanggal", "Cabang PO", "Pemasok", "Nama Barang",
               "Satuan", "Kuantitas", "@Harga", "Total Harga", "Keterangan PO",
               "Status Pesanan Pembelian", "Tgl/Jam Pembuatan"]
    data_rows = []
    for i, (barang, satuan) in enumerate(barang_list):
        data_rows.append([
            f"PO.2026.09.{5000+i}",
            datetime(2026, 9, 5),
            f"1370.{resto_code}",
            "PT KREASI REMPAH INDONESIA",
            barang,
            satuan,
            10 + i,
            27000,
            (10 + i) * 27000,
            "REP",
            "Menunggu diproses",
            datetime(2026, 9, 3, 18, 12, 33)
        ])
    create_mock_file(filepath, "#32.43. Rincian Pesanan Pembeli", headers, data_rows, metadata_rows=4)


# ---------------------------------------------------------------------------
# Perakit bundle + config (mirror run_test() test_mock.py — struktur identik)
# ---------------------------------------------------------------------------

BARANG_FIXTURE = [
    ("GULA (V.20)", "KG"),
    ("FRUCTOSE SYRUP (V.20)", "KG"),
    ("CINCAU (V.20)", "KG"),
]
RESTO_FIXTURE = "MLGPAR"


def fixture_config_data(root_path: str) -> dict:
    """config.json fixture — Folders/Sheets identik run_test() test_mock.py."""
    return {
        "RootPath": root_path + os.sep,
        "Folders": {
            "RekapBerjalan":  "1. DEVIASI WEEKLY",
            "RekapLalu":      "1.12 Rekap Mentah Bulan Lalu",
            "Penjualan2205":  "2. 22.05",
            "Kirim4215":      "3.1 42.15 Kirim",
            "Terima4215":     "3. 42.15",
            "RI3224":         "13. 32.24 RI",
            "RI3224Lalu":     "13.2 3224 RI Bulan Lalu",
            "PI":             "26.Rincian PI",
            "SaldoAwal4217":  "6.1 42.17 Saldo Awal",
            "KonversiSatuan": "27.Konversi Satuan Dex",
            "DBSKategori":    "21. DBS Kategori",
            "Pemindahan4205": "4. 42.05",
            "Pemindahan4205Lalu": "4.1 4205 Bulan Lalu",
            "RincianPO":      "25. Rincian PO",
            "Data9901":       "30. 9901",
            "Harga":          "09.Harga",
        },
        "Sheets": {
            "RekapMentah":     "REKAP MENTAH",
            "Penjualan2205":   "#22.05. Rincian Penjualan per B",
            "Pemindahan4215":  "#42.15. Pemindahan Barang (KIRI",
            "Penerimaan3224":  "#32.24. Rincian Penerimaan Bara",
            "SaldoAwal4217":   "#42.17. Kuantitas Barang per Gu",
            "FakturPembelian": "#32.42. Rincian Faktur Pembelia",
            "KonversiSatuan":  "Sheet1",
            "DBSKategori":     "Sheet1",
            "Pemindahan4205":  "#42.05. Rincian Pemindahan Bara",
            "PesananPO":       "#32.43. Rincian Pesanan Pembeli",
        },
    }


def build_fixture_bundle(root_path: str, barang_list=None, resto: str = RESTO_FIXTURE) -> dict:
    """Bangun pohon bundle mock di ``root_path`` (struktur folder + file
    identik run_test() test_mock.py). Return config dict siap pakai."""
    barang_list = barang_list or BARANG_FIXTURE
    os.makedirs(root_path, exist_ok=True)

    create_mock_rekap_mentah(os.path.join(root_path, "1. DEVIASI WEEKLY", f"{resto}.xlsx"), resto, barang_list, "berjalan")
    create_mock_rekap_mentah(os.path.join(root_path, "1.12 Rekap Mentah Bulan Lalu", f"{resto}.xlsx"), resto, barang_list, "lalu")
    create_mock_2205(os.path.join(root_path, "2. 22.05", "penjualan.xlsx"), resto, barang_list)
    create_mock_3224(os.path.join(root_path, "13. 32.24 RI", "ri.xlsx"), resto, barang_list, "berjalan")
    create_mock_3224(os.path.join(root_path, "13.2 3224 RI Bulan Lalu", "ri_lalu.xlsx"), resto, barang_list, "lalu")
    create_mock_4215(os.path.join(root_path, "3.1 42.15 Kirim", "kirim.xlsx"), resto, barang_list)
    create_mock_4205(os.path.join(root_path, "4. 42.05", "pemindahan.xlsx"), resto, barang_list)
    create_mock_4205(os.path.join(root_path, "4.1 4205 Bulan Lalu", "pemindahan_lalu.xlsx"), resto, barang_list, "lalu")
    create_mock_4217(os.path.join(root_path, "6.1 42.17 Saldo Awal", "saldo.xlsx"), resto, barang_list)
    create_mock_dbs_kategori(os.path.join(root_path, "21. DBS Kategori", "kategori.xlsx"),
                              barang_list + [("BUMBU PASTA KUAH", "GR")])
    create_mock_4109(os.path.join(root_path, "09.Harga", "4109.xlsx"), barang_list)
    create_mock_rincian_po(os.path.join(root_path, "25. Rincian PO", "po.xlsx"), resto, barang_list)
    create_mock_9901(os.path.join(root_path, "30. 9901", "mutasi.xlsx"), resto, barang_list)

    return fixture_config_data(root_path)
