"""
golden_check.py — Gerbang paritas AC-B (PRD §6 Modul B / §11.2):
"output POST /process pada fixture mock = angka yang sama dengan test_mock.py desktop".

Tiga lapis verifikasi, semua atas bundle fixture YANG SAMA dengan run_test()
test_mock.py desktop v3.9.71 (resto MLGPAR; GULA/FRUCTOSE/CINCAU KG; saldo-only
BUMBU PASTA KUAH; harga 41.09 GR/KG; PO menunggu):

  LAPIS 1 — pipeline vendored ≡ asersi test_mock.py (klaim desktop yang tak
            boleh turun saat dibungkus service): resto 22.05 = MLGPAR,
            running stock [0,0,120,150,190], 4205 lalu Tanggal −28, sumber IN
            memuat '42.05 (Bulan Lalu)', JENIS append1 = 9 kanonik, SOURCE DATA
            SO = {'input so harian'}, KATEGORI DEVIASI, Rincian PO DEVIASI +
            3 pasangan PO Menunggu.
  LAPIS 2 — POST /process ≡ pipeline langsung (validasi pembungkus + mapper):
            tiap baris EngineRow = nilai append1 per (pasangan × hari × JENIS)
            yang direkonstruksi independen via pandas; COM direkonstruksi ulang;
            selisihIn direkonstruksi dari audit varian bulan-ini; PO ≡ rincian
            32.43 terfilter DEVIASI; prices/hargaEfektif/nominal konsisten INV-3.
  LAPIS 3 — kontrak & invariants: urutan baris, §82b (warningCount = jumlah
            baris log WARNING; tiap DQ WARNING/ERROR punya ≥1 log selevel),
            status akhir dari DQ, determinisme 2× (data identik; hanya
            startedAt/durationMs/uptime yang boleh beda).

Jalankan: `bun run golden` (mini-services/engine-fastapi) atau
          `python3 golden_check.py`. Exit 0 = LULUS semua.
"""
import io
import json
import os
import re
import sys
import tempfile
import contextlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

import fixtures
from starlette.testclient import TestClient

FAILURES = []
CHECKS = 0


def check(name: str, cond: bool, detail: str = ""):
    global CHECKS
    CHECKS += 1
    mark = "LULUS" if cond else "GAGAL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(f"{name}: {detail}")


def main() -> int:
    print("=" * 70)
    print("  GOLDEN CHECK — SM-FastAPI-Engine vs pipeline desktop v3.9.71")
    print("=" * 70)

    workdir = tempfile.mkdtemp(prefix="smweb_golden_")
    bundle = os.path.join(workdir, "9.NEW QUERY")
    cfg_data = fixtures.build_fixture_bundle(bundle)
    cfg_path = os.path.join(workdir, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg_data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # LAPIS 1 — pipeline vendored ≡ asersi test_mock.py desktop
    # ------------------------------------------------------------------
    print("\n[LAPIS 1] Pipeline vendored ≡ asersi test_mock.py desktop")
    from src.config import Config
    from src.pipeline.fn_2205 import fn_2205
    from src.pipeline.fn_4205 import fn_4205
    from src.pipeline.fn_4217 import fn_4217
    from src.pipeline.fn_running_stock import fn_running_stock
    from src.pipeline.queries import query_in
    from src.pipeline.append1 import build_append1
    from src.pipeline.rincian_po import build_rincian_po
    from src.pipeline.fn_audit import extract_po_pending

    config = Config(cfg_path)

    q2205 = fn_2205(config.folder("Penjualan2205"))
    check("fn_2205 resto = MLGPAR", len(q2205) > 0 and q2205["NAMA RESTO"].iloc[0] == "MLGPAR",
          f"got {q2205['NAMA RESTO'].iloc[0] if len(q2205) else 'kosong'}")

    rs = fn_running_stock(pd.DataFrame({
        "Nama Barang": ["GULA"] * 5, "NAMA RESTO": ["MLGPAR"] * 5,
        "Tanggal": [-2, -1, 1, 2, 3], "IN": [0, 0, 30, 40, 50],
        "OUT": [0, 0, 10, 10, 10], "SALDO AWAL": [100, 100, 100, 100, 100],
    }))
    check("fn_running_stock [0,0,120,150,190]",
          rs["SALDO AKHIR"].tolist() == [0, 0, 120, 150, 190],
          f"got {rs['SALDO AKHIR'].tolist()}")

    q4205_lalu = fn_4205(config.folder("Pemindahan4205Lalu"), mode="lalu")
    check("fn_4205 lalu Tanggal −28 semua",
          len(q4205_lalu) > 0 and bool((q4205_lalu["Tanggal"] == -28).all()),
          f"n={len(q4205_lalu)}")

    _det = {}
    qin = query_in(config, detail_out=_det)
    srcs = set(_det["df"]["SOURCE IN"].unique())
    check("query_in memuat sumber '42.05 (Bulan Lalu)'",
          "42.05 (Bulan Lalu)" in srcs, f"sources={sorted(srcs)}")
    check("query_in JENIS semua 'IN'", bool((qin["JENIS"] == "IN").all()))

    q4217 = fn_4217(config.folder("SaldoAwal4217"))
    check("fn_4217 SALDO AWAL Tanggal 1",
          len(q4217) > 0 and q4217["JENIS"].iloc[0] == "SALDO AWAL"
          and q4217["Tanggal"].iloc[0] == 1)

    append1_df = build_append1(config)
    jenis_vals = set(append1_df["JENIS"].unique())
    check("append1 JENIS = 9 kanonik",
          jenis_vals == {"1.SO", "2.SALDO AKHIR", "3.DEVIASI", "4.IN",
                         "5.BARANG MASUK", "7.Selisih IN", "8.BARANG KELUAR",
                         "9.ACR", "SALDO AWAL"},
          f"got {sorted(jenis_vals)}")
    so_rows = append1_df[append1_df["JENIS"] == "1.SO"]
    check("append1 SOURCE DATA (1.SO) = {'input so harian'}",
          set(so_rows["SOURCE DATA"].dropna().astype(str)) == {"input so harian"},
          f"got {set(so_rows['SOURCE DATA'].dropna().astype(str))}")
    check("append1 KATEGORI memuat DEVIASI",
          "DEVIASI" in set(append1_df["KATEGORI"].dropna().astype(str)))

    po_semua: dict = {}
    rincian_po_df = build_rincian_po(config, semua_out=po_semua)
    check("Rincian PO terfilter DEVIASI semua",
          len(rincian_po_df) > 0 and all(rincian_po_df["DBS_Kategori.KATEGORI"] == "DEVIASI"))
    po_pending = extract_po_pending(po_semua.get("df"))
    check("PO Menunggu diproses = 3 pasangan item", len(po_pending) == 3,
          f"got {len(po_pending)}")

    # ------------------------------------------------------------------
    # LAPIS 2 & 3 — POST /process (TestClient in-process) vs pipeline langsung
    # ------------------------------------------------------------------
    print("\n[LAPIS 2/3] POST /process ≡ pipeline langsung + kontrak")
    import app as appmod
    client = TestClient(appmod.app)

    req = {"periodKey": "2026-09", "tanggalH": 25, "ambangAcrPct": 80,
           "bundleName": "fixture-mock", "bundlePath": bundle}
    r = client.post("/process", json=req)
    check("POST /process HTTP 200", r.status_code == 200,
          f"status={r.status_code} body={r.text[:300]}")
    if r.status_code != 200:
        print(json.dumps(FAILURES, indent=2))
        return 1
    res = r.json()

    check("contractVersion '1' + engineKind 'production'",
          res["contractVersion"] == "1" and res["engineKind"] == "production")
    check("definitionVersion '3.9.71-noSI'", res["definitionVersion"] == "3.9.71-noSI")
    check("periodKey echo", res["periodKey"] == "2026-09")
    check("params echo", res["params"]["tanggalH"] == 25
          and res["params"]["ambangAcrPct"] == 80
          and res["params"]["bundleName"] == "fixture-mock")

    rows = res["rows"]
    check("rows terurut restoCode→itemName→day",
          all((rows[i]["restoCode"], rows[i]["itemName"], rows[i]["day"])
              <= (rows[i + 1]["restoCode"], rows[i + 1]["itemName"], rows[i + 1]["day"])
              for i in range(len(rows) - 1)))
    check("semua day 1..31", all(1 <= x["day"] <= 31 for x in rows))

    # --- rekonstruksi independen: append1 long → expected rows ---
    METRIC = {"SALDO AWAL": "qtySaldoAwal", "1.SO": "qtySO",
              "2.SALDO AKHIR": "qtySaldoAkhir", "3.DEVIASI": "qtyDeviasi",
              "4.IN": "qtyIN", "5.BARANG MASUK": "qtyBarangMasuk",
              "7.Selisih IN": "qtySelisihIN", "8.BARANG KELUAR": "qtyBarangKeluar",
              "9.ACR": "qtyACR"}
    exp: dict = {}
    tnum = pd.to_numeric(append1_df["Tanggal"], errors="coerce")
    for i in range(len(append1_df)):
        t = tnum.iat[i]
        if pd.isna(t) or int(t) < 1:
            continue
        key = (str(append1_df["Nama Barang"].iat[i]).strip(),
               str(append1_df["NAMA RESTO"].iat[i]).strip(), int(t))
        d = exp.setdefault(key, {})
        mk = METRIC.get(append1_df["JENIS"].iat[i])
        if mk:
            v = pd.to_numeric(append1_df["NILAI"].iat[i], errors="coerce")
            d[mk] = 0.0 if pd.isna(v) else round(float(v), 6)

    got = {(x["itemName"], x["restoName"], x["day"]): x for x in rows}
    check("cakupan (pasangan × hari) identik dgn append1",
          set(got.keys()) == set(exp.keys()),
          f"engine={len(got)} append1={len(exp)}")

    mism = 0
    for key, exp_metrics in exp.items():
        row = got.get(key)
        if row is None:
            continue
        for mk, ev in exp_metrics.items():
            gv = row.get(mk)
            if gv is None or abs(gv - ev) > 1e-6:
                mism += 1
                if mism <= 5:
                    print(f"    mismatch {key} {mk}: engine={gv} append1={ev}")
    check("semua nilai metrik engine ≡ append1 (sel-per-sel)", mism == 0,
          f"{mism} mismatch")

    # COM — rekonstruksi rumus pivot_view._compute_com dari append1
    from mapper import build_pairs, compute_com
    pairs = build_pairs(append1_df)
    com_mism = 0
    for key, p in pairs.items():
        eng = {(x["itemName"], x["restoName"], x["day"]): x for x in rows}
        for day, cv in compute_com(p).items():
            row = eng.get((p.barang, p.resto, day))
            if row is None or row["qtyCOM"] is None \
                    or abs(row["qtyCOM"] - cv) > 1e-6:
                com_mism += 1
    check("qtyCOM ≡ rumus 6.PEMAKAIAN (COM) pivot desktop", com_mism == 0,
          f"{com_mism} mismatch")

    # nominal ≡ hargaEfektif × deviasi (INV-3: null bila konversi gagal/dev 0)
    nom_bad = [x for x in rows if (
        (x["nominal"] is None and x["konversiOk"] and x["hargaEfektif"] is not None
         and x["qtyDeviasi"] not in (None, 0))
        or (x["nominal"] is not None and (
            not x["konversiOk"] or x["hargaEfektif"] is None
            or abs(x["nominal"] - round(x["hargaEfektif"] * x["qtyDeviasi"], 2)) > 0.005)))]
    check("nominal per baris = hargaEfektif × deviasi (INV-2/INV-3)",
          len(nom_bad) == 0, f"{len(nom_bad)} baris janggal")

    # GR split — satuan 'GR' == isGR (mask desktop deviasi_view)
    gr_bad = [x for x in rows if x["isGR"] != (x["satuan"].strip().upper() == "GR")]
    check("isGR ≡ mask Satuan=='GR' desktop", len(gr_bad) == 0)

    # harga 41.09 dinormalkan — ekspektasi fixture (test_mock create_mock_4109)
    harga_by_pair = {}
    for x in rows:
        harga_by_pair.setdefault((x["itemName"], x["satuan"]), x["hargaEfektif"])
    check("harga GULA (KG) = 18.250 (18,25/GR × 1000)",
          harga_by_pair.get(("GULA (V.20)", "KG")) == 18250.0,
          f"got {harga_by_pair.get(('GULA (V.20)', 'KG'))}")
    check("harga CINCAU (KG) = 15 (satuan sama dgn 41.09)",
          harga_by_pair.get(("CINCAU (V.20)", "KG")) == 15.0,
          f"got {harga_by_pair.get(('CINCAU (V.20)', 'KG'))}")
    check("FRUCTOSE tanpa harga (Qty 41.09 = 0 → NaN)",
          harga_by_pair.get(("FRUCTOSE SYRUP (V.20)", "KG")) is None,
          f"got {harga_by_pair.get(('FRUCTOSE SYRUP (V.20)', 'KG'))}")
    fruct_rows = [x for x in rows if x["itemName"] == "FRUCTOSE SYRUP (V.20)"]
    check("FRUCTOSE konversiOk=true TANPA bintang (harga null ≠ konversi gagal — INV-3)",
          fruct_rows and all(x["konversiOk"] and x["nominal"] is None for x in fruct_rows),
          f"konversiOk={[x['konversiOk'] for x in fruct_rows[:2]]}")
    check("BUMBU PASTA KUAH (GR, saldo-only) harga = 12",
          harga_by_pair.get(("BUMBU PASTA KUAH", "GR")) == 12.0,
          f"got {harga_by_pair.get(('BUMBU PASTA KUAH', 'GR'))}")

    # BUMBU PASTA KUAH — pasangan saldo-only hadir (v3.9.32): deviasi = 0 − 84
    bpk = [x for x in rows if x["itemName"] == "BUMBU PASTA KUAH"]
    check("saldo-only BUMBU PASTA KUAH tampil (deviasi −84 @t=1)",
          any(x["day"] == 1 and x["qtyDeviasi"] == -84.0 for x in bpk),
          f"days={sorted(x['day'] for x in bpk)}")

    # label CEK — ekspektasi fixture: PO Menunggu di 3 pasangan DEVIASI;
    # tanpa Promix (semua sumber SO 'input so harian')
    po_menunggu_pairs = {(x["itemName"], x["restoName"])
                         for x in rows if "PO Menunggu" in x["cek"]}
    check("CEK 'PO Menunggu' menempel di 3 pasangan PO fixture",
          len(po_menunggu_pairs) == 3, f"got {sorted(po_menunggu_pairs)}")
    check("tanpa label 'Promix 04' (sumber SO harian)",
          not any("Promix 04" in x["cek"] for x in rows))

    # catatan audit — fixture sengaja memuat nomor dobel 3224 (lalu & berjalan
    # sama-sama IT.2026.09.200x → B2); prioritas append desktop B1→B2→B4→B3
    # membuat baris hari-5 (BM 0 padahal IN>0 → B4, tapi B2 lebih dulu) = B2.
    d5_notes = {x["auditNote"] for x in rows if x["day"] == 5}
    check("catatan audit menempel di baris hari-5 (B2 — prioritas append desktop)",
          d5_notes == {"B2"}, f"got {d5_notes}")

    # selisihIn ≡ rekonstruksi dari audit bulan-ini (independen)
    from src.main import run_pipeline
    import mapper
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _a1, _po, _ind, audit_result = run_pipeline(config_path=cfg_path, verbose=False)
    audit_bi = audit_result["df_bulan_ini"]
    notes_all = mapper.build_audit_notes(_ind, audit_bi)
    check("notes audit memuat B4 (BM 0 padahal IN>0 — fixture tgl 5)",
          any("B4" in v for v in notes_all.values()),
          f"codes={sorted({c for v in notes_all.values() for c in v})}")
    check("notes audit memuat B2 (nomor dobel 3224 lalu/berjalan)",
          any("B2" in v for v in notes_all.values()))
    exp_in = float(pd.to_numeric(audit_bi["Penerimaan Sistem"], errors="coerce")
                   .fillna(0).sum())
    exp_bm = float(pd.to_numeric(audit_bi["Qty SO Harian"], errors="coerce")
                   .fillna(0).sum())
    sel = res["selisihIn"]
    check("selisihIn ada entry MLGPAR", any(s["restoCode"] == "MLGPAR" for s in sel),
          f"got {[s['restoCode'] for s in sel]}")
    mlg = next((s for s in sel if s["restoCode"] == "MLGPAR"), None)
    check("selisihIn.inAccurate ≡ Σ Penerimaan Sistem audit bulan-ini",
          mlg is not None and abs(mlg["inAccurate"] - exp_in) < 1e-6,
          f"engine={mlg and mlg['inAccurate']} audit={exp_in}")
    check("selisihIn.barangMasuk ≡ Σ Qty SO Harian (BM rekap)",
          mlg is not None and abs(mlg["barangMasuk"] - exp_bm) < 1e-6,
          f"engine={mlg and mlg['barangMasuk']} audit={exp_bm}")
    check("selisihIn.hasilAudit SELISIH (fixture BM ≠ IN)",
          mlg is not None and mlg["hasilAudit"] == "SELISIH")
    check("SKOR RESTO = itemBerselisih + tanggalTerdampak",
          mlg is not None and mlg["skorResto"]
          == mlg["itemBerselisih"] + mlg["tanggalTerdampak"])

    # PO ≡ rincian 32.43 DEVIASI (mirror tab 🛒)
    po = res["po"]
    check("EnginePo = 3 PO fixture (satu per Nomor #)", len(po) == 3, f"got {len(po)}")
    check("semua PO status Menunggu (item 'Menunggu diproses')",
          all(p["status"] == "Menunggu" for p in po))
    check("annotasi ≡ '↳ ' + statusPesanan (echo raw status)",
          all(p["annotasi"] == f"↳ {p['statusPesanan']}" for p in po),
          f"got {[(p['annotasi'], p['statusPesanan']) for p in po]}")
    check("PO qty satuan KG (10/11/12 — fixture)",
          sorted(it["qty"] for p in po for it in p["items"]) == [10.0, 11.0, 12.0],
          f"got {sorted(it['qty'] for p in po for it in p['items'])}")

    # --- LAPIS 3: kontrak §82b + status + determinisme ---
    logs = res["logs"]
    summary = res["summary"]
    n_warn_logs = sum(1 for l in logs if l["level"] == "WARNING")
    n_err_logs = sum(1 for l in logs if l["level"] == "ERROR")
    check("§82b warningCount = jumlah baris log WARNING",
          summary["warningCount"] == n_warn_logs,
          f"summary={summary['warningCount']} log={n_warn_logs}")
    check("§82b errorCount = jumlah baris log ERROR",
          summary["errorCount"] == n_err_logs)
    warn_codes = {d["code"] for d in res["dqIssues"] if d["severity"] == "WARNING"}
    err_codes = {d["code"] for d in res["dqIssues"] if d["severity"] == "ERROR"}
    check("tiap DQ WARNING punya ≥1 log WARNING",
          all(any(d["code"] in l["message"] or _code_in_msg(d, l["message"])
                  for l in logs if l["level"] == "WARNING")
              for d in res["dqIssues"] if d["severity"] == "WARNING")
          or _dq_log_pair_ok(res),
          f"codes={sorted(warn_codes)}")
    if any(d["severity"] == "ERROR" for d in res["dqIssues"]):
        check("status SELESAI_PARSIAL (ada DQ ERROR)", res["status"] == "SELESAI_PARSIAL")
    elif any(d["severity"] == "WARNING" for d in res["dqIssues"]):
        check("status SELESAI_DENGAN_PERINGATAN (ada DQ WARNING)",
              res["status"] == "SELESAI_DENGAN_PERINGATAN")
    else:
        check("status SELESAI (tanpa DQ WARNING/ERROR)", res["status"] == "SELESAI")
    check("summary.rowCount = len(rows)", summary["rowCount"] == len(rows))
    check("summary.restoCount/itemCount > 0",
          summary["restoCount"] > 0 and summary["itemCount"] > 0)
    check("summary.poCount = len(po)", summary["poCount"] == len(po))
    check("nominalTotal ≡ Σ nominal baris",
          abs(summary["nominalTotal"]
              - round(sum(x["nominal"] or 0 for x in rows), 2)) < 0.005)
    check("deviasiQtyTotal bertanda ≡ Σ deviasi",
          abs(summary["deviasiQtyTotal"]
              - round(sum(x["qtyDeviasi"] or 0 for x in rows), 6)) < 1e-4)

    # PREFLIGHT jujur: folder Terima4215 memang tak dibuat fixture (gap desktop)
    check("DQ PREFLIGHT_FOLDER jujur (folder config kosong dilaporkan)",
          any(d["code"] == "PREFLIGHT_FOLDER" for d in res["dqIssues"]))
    # TANPA_HARGA jujur utk FRUCTOSE (INV-3)
    check("DQ TANPA_HARGA utk FRUCTOSE (harga 41.09 NaN)",
          any(d["code"] == "TANPA_HARGA" and "FRUCTOSE" in (d["message"] or "")
              for d in res["dqIssues"]))

    # determinisme — panggil ulang; data harus identik (FR-12)
    r2 = client.post("/process", json=req)
    res2 = r2.json()
    for field in ("rows", "prices", "selisihIn", "po", "dqIssues", "sourceFiles",
                  "status", "summary"):
        if field == "summary":
            s1 = dict(res["summary"]); s2 = dict(res2["summary"])
            s1.pop("durationMs", None); s2.pop("durationMs", None)
            check(f"determinisme: summary identik", s1 == s2,
                  f"{s1} vs {s2}")
        else:
            check(f"determinisme: {field} identik", res[field] == res2[field])

    # validasi 422
    r422 = client.post("/process", json={"periodKey": "2026-13", "tanggalH": 25,
                                         "ambangAcrPct": 80, "bundlePath": bundle})
    check("422 periodKey invalid", r422.status_code == 422)
    r422b = client.post("/process", json={"periodKey": "2026-09", "tanggalH": 25,
                                          "ambangAcrPct": 80})
    check("422 tanpa bundlePath", r422b.status_code == 422)
    r422c = client.post("/process", json={"periodKey": "2026-09", "tanggalH": 25,
                                          "ambangAcrPct": 80,
                                          "bundlePath": "/tidak/ada"})
    check("422 bundlePath tidak ada", r422c.status_code == 422)

    # health
    rh = client.get("/health")
    h = rh.json()
    check("GET /health kontrak (production/3.9.71-noSI/parityNote)",
          rh.status_code == 200 and h["engineKind"] == "production"
          and h["definitionVersion"] == "3.9.71-noSI"
          and h["contractVersion"] == "1" and "pipeline asli" in h["parityNote"]
          and h["lastStatus"] == res["status"])

    print("\n" + "=" * 70)
    if FAILURES:
        print(f"  HASIL: {len(FAILURES)}/{CHECKS} GAGAL")
        for f in FAILURES:
            print(f"   ✗ {f}")
        return 1
    print(f"  HASIL: LULUS SEMUA — {CHECKS}/{CHECKS} check")
    print(f"  status run: {res['status']} · {len(rows)} baris · "
          f"{summary['warningCount']} WARNING · {len(res['dqIssues'])} DQ issue")
    print("=" * 70)
    return 0


def _code_in_msg(d, msg: str) -> bool:
    """Heuristik longgar: pesan DQ ter-cermin di log (nama file/sumber)."""
    src = d.get("source") or ""
    return bool(src) and src in msg


def _dq_log_pair_ok(res) -> bool:
    """Semua DQ WARNING/ERROR: pesannya (atau sumbernya) muncul di ≥1 log
    selevel — kontrak §3.4 (baris [ENGINE] di-append mapper utk DQ turunan)."""
    logs = res["logs"]
    for d in res["dqIssues"]:
        if d["severity"] not in ("WARNING", "ERROR"):
            continue
        msg = d["message"]
        src = d.get("source") or ""
        key = src if d["code"] in ("SKIP_FILE", "KONVERSI_GAGAL", "TANPA_HARGA") else msg
        if not any(key in l["message"] and l["level"] == d["severity"]
                   for l in logs):
            return False
    return True


if __name__ == "__main__":
    sys.exit(main())
