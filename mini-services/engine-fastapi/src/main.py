"""
main.py — Pipeline runner (orchestrator).
Menjalankan pipeline: build Append1 + Rincian PO + Audit Rekonsiliasi →
return DataFrames. Tidak ada Excel output — data ditampilkan langsung di UI.

Bisa dipanggil langsung (CLI) atau dari UI Tkinter.
"""
import sys
import time
import warnings
from pathlib import Path

import pandas as pd

# Suppress openpyxl noise warnings (no default style, etc.)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Tambah parent dir ke sys.path untuk import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.pipeline.append1 import build_append1
from src.pipeline.fn_4109 import build_harga_map, fn_4109
from src.pipeline.fn_audit import build_audit_from_app, extract_po_pending
from src.pipeline.rincian_po import build_rincian_po


class PipelineStopped(Exception):
    """Raised when user requests stop via UI Stop button."""
    pass


def run_pipeline(config_path: str = None, verbose: bool = True, stop_event=None):
    """
    Jalankan pipeline lengkap. Return DataFrames (no Excel output).

    Args:
        config_path: Path ke config.json (default: config.json di root project)
        verbose: Print progress
        stop_event: threading.Event — jika set, pipeline akan berhenti di checkpoint
                    berikutnya dengan raise PipelineStopped

    Returns:
        Tuple (append1_df, rincian_po_df, in_detail_df, audit_result)
        v3.4: in_detail_df = detail IN per dokumen (42.05 / 32.24 / 99.01
        + nomor) untuk tab "Rekap Selisih IN".
        v3.6: audit_result = dict {"df": audit_df, "kpi": kpi, "desc": ...}
        — logika macro VBA BuatLaporanDeviasiSampel diaplikasikan ke DATA
        APP (rekap SO + BARANG MASUK + IN per tanggal; sheet '29 Rekap
        Barang Masuk' TIDAK dibaca lagi) + kolom SO & hasil audit di tab
        Rekap Selisih IN.
        v3.9.27: + kunci "df_bulan_ini"/"kpi_bulan_ini"/"desc_bulan_ini" —
        varian audit BULAN BERJALAN SAJA (baris Tanggal negatif dibuang
        sebelum engine; mirror sheet LAPORAN_DEVIASI tgl 1..31) utk mode
        "Hanya Hitung Bulan Ini" tab Rekap Selisih IN (DEFAULT); kunci
        lama tetap varian PENUH (incl. bulan lalu) utk mode "Hitung
        Bulan Lalu + Bulan Ini".
        v3.9.30: Rincian PO 32.43 dibaca SEKALIGUS tanpa filter
        KATEGORI (semua_out) → pasangan ber-status 'Menunggu diproses'
        (extract_po_pending) diteruskan ke KEDUA varian audit sebagai
        penjelas deviasi murni (kolom 'Qty PO Menunggu' + catatan +
        KPI 'dev_murni_po' — lihat fn_audit._apply_po_menunggu).
    v3.9.31: peta KONVERSI SATUAN dari baris IN 42.05+32.24
        (append1 konversi_out — 'Rasio Satuan' + '#Sat. Kirim'/'Satuan')
        → qty PO Menunggu dikonversi ke satuan terkecil (apple-to-apple
        dgn Selisih/Saldo; user: "PO karton vs barang masuk botol tidak
        match waktu cari deviasi murni"; fallback qty as-is + '*').
    v3.9.32: HARGA 41.09 (folder '09.Harga' — Folders.Harga bisa diubah
        user) → audit_result['harga_map'] {barang: (harga, satuan)} +
        audit_result['konversi_map'] (peta rasio v3.9.31) — input mode
        'Nominal (H)' tab Laporan Deviasi (Harga × Qty Deviasi; harga
        dinormalkan ke satuan rekap via peta rasio).
    v3.9.33 — AUDIT FIX (48-b): harga 41.09 dibaca dalam try/except — 1
        file harga rusak kini hanya menonaktifkan peta harga (warning
        log + harga_map kosong), BUKAN menggagalkan seluruh pipeline.
    """
    start_time = time.time()

    # 1. Load config
    if verbose:
        print("=" * 60)
        print("  STOCK MONITORING - PIPELINE RUNNER")
        print("=" * 60)

    config = Config(config_path)

    if verbose:
        print(f"\n  RootPath: {config.RootPath}")
        print("  Mode: FULL (LightMode dihapus v3.5 — bulan lalu selalu terbaca)")

    # 2. Build Append1 (+ IN detail v3.4)
    if verbose:
        print("\n" + "-" * 60)
        print("  [1/3] Building Append1 (main pipeline)...")
        print("-" * 60)

    in_detail_holder: dict = {}
    rekap_so_holder: dict = {}
    konversi_holder: dict = {}
    append1_df = build_append1(config, stop_event=stop_event,
                               in_detail_out=in_detail_holder,
                               rekap_so_out=rekap_so_holder,
                               konversi_out=konversi_holder)

    # FIX: check stop_event after Append1 build
    if stop_event is not None and stop_event.is_set():
        raise PipelineStopped("Pipeline dihentikan oleh user setelah Append1")

    if verbose:
        print(f"\n  Append1 result: {len(append1_df)} rows")
        if not append1_df.empty:
            print(f"  Columns: {list(append1_df.columns)}")

    # 3. Build Rincian PO
    if verbose:
        print("\n" + "-" * 60)
        print("  [2/3] Building Rincian PO...")
        print("-" * 60)

    # v3.9.30 — salinan TANPA filter KATEGORI utk audit PO Menunggu
    # (barang non-DEVIASI-master pun PO-nya ikut terbaca; query utama
    # tab 🛒 Rincian PO tetap terfilter DEVIASI persis mirror M)
    po_semua: dict = {}
    rincian_po_df = build_rincian_po(config, semua_out=po_semua)
    po_pending_df = extract_po_pending(po_semua.get("df"))

    # FIX: check stop_event after Rincian PO build
    if stop_event is not None and stop_event.is_set():
        raise PipelineStopped("Pipeline dihentikan oleh user setelah Rincian PO")

    if verbose:
        print(f"\n  Rincian PO result: {len(rincian_po_df)} rows")
        if po_pending_df is not None and not po_pending_df.empty:
            print(f"  PO Menunggu diproses (v3.9.30): {len(po_pending_df)} "
                  f"rows — penjelas deviasi murni di audit")

    in_detail_df = in_detail_holder.get("df")
    if in_detail_df is None:
        in_detail_df = pd.DataFrame()
    if verbose:
        print(f"  IN detail (v3.4): {len(in_detail_df)} rows")

    # 4. Audit Rekonsiliasi (v3.6 — dari DATA APP: rekap SO + BM + IN per
    #    tanggal; tanpa sheet '29 Rekap Barang Masuk')
    if verbose:
        print("\n" + "-" * 60)
        print("  [3/3] Audit Rekonsiliasi (logika VBA × data app)...")
        print("-" * 60)
    audit_df, audit_kpi, audit_desc = build_audit_from_app(
        rekap_so_holder.get("df"), in_detail_df,
        po_pending_df=po_pending_df,
        konversi=konversi_holder.get("map"))
    audit_result = {"df": audit_df, "kpi": audit_kpi, "desc": audit_desc}

    # v3.9.27 — VARIAN KEDUA utk mode "HITUNG BULAN INI SAJA" tab Rekap
    # Selisih IN (user: "pada rekap selisih in bisa mode hitung bulan lalu
    # dan hanya hitung bulan ini. Tapi default hitung bulan ini aja"):
    # baris Tanggal negatif (bulan lalu) dibuang sebelum engine → audit
    # murni bulan berjalan, mirror sheet LAPORAN_DEVIASI (tgl 1..31).
    # Dihitung SEKALI di pipeline; view memilih varian saat mode diubah
    # (tanpa recompute). Kunci "df"/"kpi"/"desc" TETAP varian penuh —
    # pemanggil lama (app.py log + export "Laporan Deviasi (Audit)")
    # tidak berubah.
    audit_df2, audit_kpi2, audit_desc2 = build_audit_from_app(
        rekap_so_holder.get("df"), in_detail_df, po_pending_df=po_pending_df,
        bulan_lalu=False, konversi=konversi_holder.get("map"))
    audit_result["df_bulan_ini"] = audit_df2
    audit_result["kpi_bulan_ini"] = audit_kpi2
    audit_result["desc_bulan_ini"] = audit_desc2

    # v3.9.32 — HARGA 41.09 (user: "harga dari file 4109 (41.09) folder
    # 09.Harga [alamat bisa diubah] — kolom harga = Nilai/Kuantitas
    # Saldo Akhir") + peta konversi v3.9.31 → input mode 'Nominal (H)'
    # tab Laporan Deviasi. Folder/sheet diatur config (setdefault).
    # v3.9.33 — AUDIT FIX (48-b): baca harga SETELAH append1+audit selesai
    # — 1 file harga rusak/struktur aneh dulu menggagalkan SELURUH run
    # (hasil append1+audit yang SUDAH dihitung ikut terbuang). Bungkus
    # try/except → log warning + peta harga kosong (mode Nominal (H)
    # menonaktifkan diri dgn anggun; view lain tetap jalan).
    try:
        harga_df = fn_4109(config.folder("Harga"), config.sheet("Harga"))
        audit_result["harga_map"] = build_harga_map(harga_df)
    except Exception as e:  # noqa: BLE001 — degradasi anggun by design
        print(f"  [WARNING] Harga 41.09 dilewati: {e}")
        audit_result["harga_map"] = {}
    audit_result["konversi_map"] = konversi_holder.get("map")
    if verbose and audit_result["harga_map"]:
        _nh = len(audit_result["harga_map"])
        print(f"  Harga 41.09 (v3.9.32): {_nh:,} barang — mode Nominal "
              f"(H) siap (Harga × Qty Deviasi)")
    if verbose:
        n_neg = (pd.to_numeric(audit_df["Tanggal"], errors="coerce") < 0
                 ).sum() if not audit_df.empty else 0
        print(f"  Audit (mode Bulan Ini): {len(audit_df2)} rows "
              f"(varian penuh {len(audit_df)} rows, "
              f"{int(n_neg)} baris bulan lalu)")

    if stop_event is not None and stop_event.is_set():
        raise PipelineStopped("Pipeline dihentikan oleh user setelah Audit")

    if verbose:
        k = audit_kpi
        print(f"  Audit: {len(audit_df)} rows | OK {k['ok']:,} | "
              f"Cut-off {k['cutoff']:,} | Valid {k['omit']:,} | "
              f"Deviasi Murni {k['deviasi_murni']:,} | "
              f"Sisa Gantung {k['deviasi_qty']:,.0f}")
        if k.get("dev_murni_po", 0):
            print(f"  Deviasi Murni ber-PO Menunggu (v3.9.30): "
                  f"{k['dev_murni_po']:,} baris — explainable, "
                  f"sisanya perlu audit fisik")
        _km31 = konversi_holder.get("map") or {}
        if _km31.get("n_rasio"):
            print(f"  Konversi satuan PO (v3.9.31): peta "
                  f"{_km31['n_rasio']:,} rasio / "
                  f"{_km31['n_barang']:,} barang — qty PO Menunggu "
                  f"tampil satuan terkecil")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  SELESAI dalam {elapsed:.1f} detik")
        print(f"  Append1: {len(append1_df)} rows | Rincian PO: {len(rincian_po_df)} rows"
              f" | IN detail: {len(in_detail_df)} rows"
              f" | Audit: {len(audit_df)} rows")
        print(f"{'=' * 60}")

    return append1_df, rincian_po_df, in_detail_df, audit_result


if __name__ == "__main__":
    # CLI mode — just run pipeline and print summary
    import argparse
    parser = argparse.ArgumentParser(description="Stock Monitoring Pipeline")
    parser.add_argument("--config", default=None, help="Path ke config.json")
    args = parser.parse_args()

    try:
        append1_df, rincian_po_df, in_detail_df, audit = run_pipeline(
            config_path=args.config)
        print(f"\nAppend1: {len(append1_df)} rows")
        print(f"Rincian PO: {len(rincian_po_df)} rows")
        print(f"IN detail: {len(in_detail_df)} rows")
        print(f"Audit: {len(audit['df'])} rows — {audit['kpi']}")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
