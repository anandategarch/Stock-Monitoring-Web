"""
app.py — SM-FastAPI-Engine: Engine PRODUKSI SM-WEB (kontrak v1, docs/ENGINE-CONTRACT.md §5).

Membungkus `src/main.py::run_pipeline` Stock-Monitoring v3.9.71 APA ADANYA
(0-rewrite, FR-10): pipeline + 16 modul dibaca dari `src/` vendored di sini —
satu-satunya kode baru adalah pembungkus transport (validasi request, penulisan
config run dengan RootPath = direktori bundle, penangkapan stdout pipeline →
log terstruktur §82b) dan pemetaan hasil (mapper.py).

Endpoint:
  GET  /health  → EngineHealth (engineKind "production", FR-14/FR-81)
  POST /process → EngineProcessRequest (+ bundlePath — ekstensi produksi:
                  bundle diekstrak & divalidasi oleh Next.js, path server
                  diteruskan di sini; FR-1/FR-2) → EngineResult

Stateless & idempotent (FR-12): tidak ada state antar-request selain metrik
/health (lastProcessAt/lastDurationMs/lastStatus — dikecualikan kontrak §1).
"""
import contextlib
import io
import json
import os
import re
import secrets
import sys
import tempfile
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

_SERVICE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SERVICE_DIR))

from src.config import Config                                   # noqa: E402
from src.main import run_pipeline                               # noqa: E402
from src.pipeline.rincian_po import build_rincian_po             # noqa: E402
from src.pipeline.fn_audit import extract_po_pending             # noqa: E402
import mapper                                                   # noqa: E402

app = FastAPI(title=mapper.ENGINE_NAME, version=mapper.ENGINE_VERSION)

_STARTED_AT = time.time()
_LOCK = threading.Lock()
_LAST = {"at": None, "durationMs": None, "status": None}  # hanya utk /health

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# ---- Guard opsional (audit 48-g-engine) ----
# SM_ENGINE_TOKEN: bila diisi, /process menolak panggilan tanpa header
# x-engine-token yang cocok (perbandingan konstan) — mesin yang terpapar di
# jaringan tidak bisa dipakai membaca bundlePath arbitrer.
# SM_ENGINE_ALLOWED_ROOTS: bila diisi (path absolut dipisah koma), bundlePath
# wajib berada di bawah salah satunya.
_ENGINE_TOKEN = os.environ.get("SM_ENGINE_TOKEN", "").strip()
_ALLOWED_ROOTS = [
    os.path.abspath(p.strip())
    for p in os.environ.get("SM_ENGINE_ALLOWED_ROOTS", "").split(",")
    if p.strip()
]

with open(_SERVICE_DIR / "config_template.json", "r", encoding="utf-8") as f:
    _CONFIG_TEMPLATE = json.load(f)


def _err(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


@app.get("/health")
def health():
    with _LOCK:
        last = dict(_LAST)
    return {
        "status": "ok",
        "engineKind": "production",
        "engineName": mapper.ENGINE_NAME,
        "engineVersion": mapper.ENGINE_VERSION,
        "definitionVersion": mapper.DEFINITION_VERSION,
        "contractVersion": mapper.CONTRACT_VERSION,
        "lastProcessAt": last["at"],
        "lastDurationMs": last["durationMs"],
        "lastStatus": last["status"],
        "uptimeSec": int(time.time() - _STARTED_AT),
        "parityNote": mapper.PARITY_NOTE,
    }


@app.post("/process")
def process(body: dict, x_engine_token: str = Header(default="")):
    # ---- Guard shared-secret opsional (audit 48-g-engine) ----
    if _ENGINE_TOKEN and not secrets.compare_digest(x_engine_token, _ENGINE_TOKEN):
        return _err(401, "Token engine tidak valid (header x-engine-token).")

    # ---- Validasi request (mirror engine demo — 422 + {"error"}) ----
    if not isinstance(body, dict):
        return _err(422, "Body harus objek JSON.")
    period_key = body.get("periodKey")
    if not isinstance(period_key, str) or not _PERIOD_RE.match(period_key):
        return _err(422, "periodKey wajib format YYYY-MM (contoh: 2026-10).")

    def _int_in(name, lo, hi):
        v = body.get(name)
        if isinstance(v, bool) or not isinstance(v, int):
            try:
                v = int(v)
            except (TypeError, ValueError):
                return None
        return v if lo <= v <= hi else None

    tanggal_h = _int_in("tanggalH", 1, 31)
    if tanggal_h is None:
        return _err(422, "tanggalH wajib integer 1..31.")
    ambang = _int_in("ambangAcrPct", 1, 200)
    if ambang is None:
        return _err(422, "ambangAcrPct wajib integer 1..200.")

    bundle_path = body.get("bundlePath")
    if not isinstance(bundle_path, str) or not bundle_path.strip():
        return _err(422, "Engine produksi membutuhkan bundlePath — bundle export "
                        "Accurate yang sudah diekstrak (unggah via /api/ingest/upload).")
    bundle_path = os.path.abspath(bundle_path)
    if not os.path.isdir(bundle_path):
        return _err(422, f"bundlePath tidak ditemukan: {bundle_path}")
    if _ALLOWED_ROOTS and not any(
        bundle_path == root or bundle_path.startswith(root + os.sep)
        for root in _ALLOWED_ROOTS
    ):
        return _err(422, "bundlePath berada di luar direktori yang diizinkan "
                        "(SM_ENGINE_ALLOWED_ROOTS).")

    bundle_name = body.get("bundleName")
    if bundle_name is not None and not isinstance(bundle_name, str):
        bundle_name = str(bundle_name)

    params = {"periodKey": period_key, "tanggalH": tanggal_h,
              "ambangAcrPct": ambang, "bundleName": bundle_name}

    # ---- Config run: template (FR-2 — pemetaan folder/sheet identik
    #      config.json desktop) + RootPath = direktori bundle ----
    run_cfg = dict(_CONFIG_TEMPLATE)
    run_cfg["RootPath"] = bundle_path + os.sep
    cfg_fd, cfg_path = tempfile.mkstemp(prefix="smweb_run_", suffix=".json",
                                        dir=bundle_path)
    try:
        with os.fdopen(cfg_fd, "w", encoding="utf-8") as f:
            json.dump(run_cfg, f, ensure_ascii=False)
        config = Config(cfg_path)

        started = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        buf = io.StringIO()
        try:
            # run_pipeline verbose=True → seluruh jejak [fn_xxxx]/[Append1]/
            # [WARNING] Skip file tertangkap → log terstruktur §82b (FR-3)
            with contextlib.redirect_stdout(buf):
                append1_df, rincian_po_df, in_detail_df, audit_result = \
                    run_pipeline(config_path=cfg_path, verbose=True)
                po_semua: dict = {}
                build_rincian_po(config, semua_out=po_semua)
                po_pending_df = extract_po_pending(po_semua.get("df"))
        except Exception as e:  # noqa: BLE001 — kegagalan pipeline = 500 jujur
            import traceback
            traceback.print_exc(file=sys.stderr)
            return _err(500, f"Pipeline gagal: {e}")
        duration_ms = int((time.perf_counter() - t0) * 1000)

        result = mapper.build_engine_result(
            config=config,
            params=params,
            append1_df=append1_df,
            rincian_po_df=rincian_po_df,
            in_detail_df=in_detail_df,
            audit_result=audit_result,
            po_pending_df=po_pending_df,
            log_text=buf.getvalue(),
            started_at=started,
            duration_ms=duration_ms,
        )
        result["po"] = mapper.map_po(rincian_po_df)
        result["summary"]["poCount"] = len(result["po"])

        with _LOCK:
            _LAST["at"] = started.isoformat()
            _LAST["durationMs"] = duration_ms
            _LAST["status"] = result["status"]
        return JSONResponse(result)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(cfg_path)
