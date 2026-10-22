#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smweb_laptop_agent.py — AGENT "PYTHON DI LAPTOP" untuk Stock-Monitoring-Web (Task 51).

Cara kerja (arsitektur PULL — web tidak bisa menjangkau laptop di balik NAT):
  1. Kamu klik "Kirim N Folder → Laptop (Proses Python)" di web  → job QUEUED.
  2. Agent ini (berjalan di laptopmu) MENJEMPUT job lewat polling /api/agent/claim
     setiap beberapa detik.
  3. Agent MENYALIN file Excel langsung dari folder data di DISK LOKAL kamu
     (RootPath — mis. C:\\KERJA\\1. RESTO\\9.NEW QUERY, Task 53; Task 55:
     dukungan Google Drive DIHAPUS — permintaan pemilik produk), menjalankan
     ENGINE FASTAPI PRODUKSI secara LOKAL (pipeline asli v3.9.71, port :3031),
     lalu mengunggah hasilnya (ter-gzip, terpotong-potong agar lolos batas body
     serverless) ke web.
  4. Hasil TAMPIL DI WEB sebagai run pratinjau — kamu bisa langsung menekan
     KOMIT di web (komit memakai hasil tersimpan; serverless tidak butuh engine).

HANYALAH STDLIB PYTHON — tidak ada `pip install` untuk agent ini.
Yang harus jalan duluan di laptop:
  • Engine FastAPI produksi (mini-services/engine-fastapi, port 3031):
        cd mini-services/engine-fastapi
        pip install -r requirements.txt        # sekali saja
        python -m uvicorn app:app --port 3031 # atau: bun run dev
  • Lalu jalankan agent ini:
        python agent/smweb_laptop_agent.py

Konfigurasi lewat ENV (atau ubah konstanta di bawah):
  SMWEB_SERVER        URL web (produksi: https://stock-monitoring-web.vercel.app)
  SMWEB_AGENT_TOKEN   token yang sama dengan env AGENT_TOKEN di server
  SMWEB_ENGINE_URL    URL engine FastAPI lokal (default http://127.0.0.1:3031)
  SMWEB_AGENT_NAME    nama yang tampil di web (default: nama komputer)
  SMWEB_LOCAL_ROOT    folder induk data lokal, setara RootPath config.json
                      desktop (mis. C:\\KERJA\\1. RESTO\\9.NEW QUERY) —
                      di dalamnya harus ada folder bernama sama dengan judul
                      job ("1. DEVIASI WEEKLY", "2. 22.05", dst).
                      (Task 55: SMWEB_DATA_SOURCE lama diabaikan — agent kini
                      HANYA membaca disk lokal; fitur Google Drive dihapus.)
"""

import base64
import calendar
import getpass
import gzip
import json
import os
import random
import re
import shutil
import signal
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# ------------------------- Konfigurasi -------------------------

SERVER = os.environ.get("SMWEB_SERVER", "http://127.0.0.1:3000").rstrip("/")
AGENT_TOKEN = os.environ.get("SMWEB_AGENT_TOKEN", "smweb-dev-agent-token")
ENGINE_URL = os.environ.get("SMWEB_ENGINE_URL", "http://127.0.0.1:3031").rstrip("/")
AGENT_NAME = os.environ.get(
    "SMWEB_AGENT_NAME",
    f"laptop-{getpass.getuser() if os.name != 'nt' else os.environ.get('USERNAME', 'user')}",
)[:80]
WORKDIR = Path(os.environ.get("SMWEB_AGENT_WORKDIR", Path(__file__).resolve().parent / "smweb-agent-work"))
# Sumber data job (Task 55): DISK LOKAL SAJA — fitur Google Drive sudah
# dihapus dari web (permintaan pemilik produk). Nilai SMWEB_DATA_SOURCE lama
# (auto/drive) diabaikan; dicatat sebagai warning sekali saat startup.
_DATA_SOURCE_ENV = (os.environ.get("SMWEB_DATA_SOURCE") or "").strip().lower()
_DATA_SOURCE_DEPRECATED = _DATA_SOURCE_ENV in ("auto", "drive")
DATA_SOURCE = "local"
LOCAL_ROOT = (os.environ.get("SMWEB_LOCAL_ROOT") or "").strip()
POLL_INTERVAL = 3.0          # detik antar polling job
HEARTBEAT_INTERVAL = 8.0     # detik antar heartbeat saat memproses
CHUNK_BYTES = 2_000_000      # potongan hasil gzip per unggahan (aman < batas body 4,5 MB)
MAX_FILES = 300              # samakan batas server
MAX_SUBFOLDERS = 16
MAX_FILE_BYTES = 60 * 1024 * 1024
MAX_TOTAL_BYTES = 400 * 1024 * 1024
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")

# Pemetaan folder kunci config.json — IDENTIK src/lib/canonical-folders.ts (FR-2).
FOLDER_TEMPLATE = [
    ("RekapBerjalan", "1. DEVIASI WEEKLY"),
    ("RekapLalu", "1.12 Rekap Mentah Bulan Lalu"),
    ("Penjualan2205", "2. 22.05"),
    ("Kirim4215", "3.1 42.15 Kirim"),
    ("Terima4215", "3. 42.15"),
    ("RI3224", "13. 32.24 RI"),
    ("RI3224Lalu", "13.2 3224 RI Bulan Lalu"),
    ("SaldoAwal4217", "6.1 42.17 Saldo Awal"),
    ("DBSKategori", "21. DBS Kategori"),
    ("Pemindahan4205", "4. 42.05"),
    ("Pemindahan4205Lalu", "4.1 4205 Bulan Lalu"),
    ("RincianPO", "25. Rincian PO"),
    ("Data9901", "30. 9901"),
    ("Harga", "09.Harga"),
]
CANONICAL_LOWER = {name.lower(): name for _key, name in FOLDER_TEMPLATE}

MONTHS = {"jan": 0, "feb": 1, "mar": 2, "apr": 3, "may": 4, "jun": 5,
          "jul": 6, "aug": 7, "sep": 8, "oct": 9, "nov": 10, "dec": 11}
EXCEL_RE = re.compile(r"\.(xlsx|xls|xlsb|xlsm)$", re.IGNORECASE)
FOLDER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{15,}$")

# ------------------------- Util umum -------------------------


def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    color = {"INFO": "\033[0m", "OK": "\033[92m", "WARN": "\033[93m", "ERR": "\033[91m"}.get(level, "")
    reset = "\033[0m" if color else ""
    print(f"{color}[{ts}] {msg}{reset}", flush=True)


def http_json(method, url, payload=None, token=None, timeout=30):
    """POST/GET JSON kecil. Melempar RuntimeError dengan pesan server bila non-2xx."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    if token:
        req.add_header("X-Agent-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read().decode("utf-8", "replace")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8", "replace")).get("error", "")
        except Exception:
            detail = e.read().decode("utf-8", "replace")[:200] if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} dari {url.split('?')[0]}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Tidak bisa menghubungi {url.split('?')[0]}: {e.reason}") from e


# ------------------------- Drive: listing + unduh (port drive.ts) -------------------------


def map_drive_folder_key(folder_name):
    norm = lambda x: " ".join(x.strip().lower().split())
    for key, name in FOLDER_TEMPLATE:
        if norm(name) == norm(folder_name):
            return key
    return None


def canonical_name_of(folder_name):
    """Judul folder → ejaan kanonik template (untuk membingkai path file root)."""
    norm = lambda x: " ".join(x.strip().lower().split())
    for _key, name in FOLDER_TEMPLATE:
        if norm(name) == norm(folder_name):
            return name
    return None


class DriveError(Exception):
    pass


class BadFileError(Exception):
    """File rusak/bukan Excel — DILEWATI dengan laporan jujur (bukan fatal)."""


def dedupe_drive_files(files):
    """Port dedupeDriveFiles: nama sama → terbaru menang; tanpa tanggal → akhiran __2."""
    groups = {}
    order = []
    for f in files:
        groups.setdefault(f["path"], []).append(f)
        if f["path"] not in order:
            order.append(f["path"])
    picked, skipped, suffixed = [], [], []
    for path in order:
        lst = groups[path]
        if len(lst) == 1:
            picked.append((lst[0], path))
            continue
        if all(f["modifiedMs"] is not None for f in lst):
            srt = sorted(lst, key=lambda f: f["modifiedMs"] or 0, reverse=True)
            picked.append((srt[0], path))
            for f in srt[1:]:
                when = time.strftime("%Y-%m-%d", time.gmtime((f["modifiedMs"] or 0) / 1000))
                skipped.append({"path": path, "reason": "versi %s (lebih lama) dilewati" % when})
        else:
            for f in lst:
                picked.append((f, path))
    used = set()
    kept = []
    for ref, path in picked:
        out = path
        if out in used:
            dot = out.rfind(".")
            base, ext = (out[:dot], out[dot:]) if dot > 0 else (out, "")
            n = 2
            while ("%s__%d%s" % (base, n, ext)) in used:
                n += 1
            out = "%s__%d%s" % (base, n, ext)
            suffixed.append(out)
        used.add(out)
        kept.append(dict(ref, path=out))
    return {"kept": kept, "skipped": skipped, "suffixed": suffixed}


def find_local_folder(folder_name):
    """Cari folder data di LOCAL_ROOT — case-insensitive (mirror perilaku
    Windows: job membawa judul kanonik, ejaan di disk boleh beda kapital).
    Return path absolut atau None bila folder tidak ada."""
    if not LOCAL_ROOT or not folder_name:
        return None
    direct = os.path.join(LOCAL_ROOT, folder_name)
    if os.path.isdir(direct):
        return direct
    try:
        low = folder_name.lower()
        with os.scandir(LOCAL_ROOT) as it:
            for e in it:
                if e.is_dir(follow_symlinks=False) and e.name.lower() == low:
                    return e.path
    except OSError:
        return None
    return None


def collect_local_files(abs_dir, folder_name):
    """Semantik IDENTIK collect_drive_files, sumber: folder disk lokal.
    Excel di root + subfolder (kedalaman 2, batas sama); file kunci Excel
    (~$xxx) dilewati. Tidak pernah melempar untuk folder kosong — keputusan
    (catatan jujur) ada di process_job, bukan di sini."""
    canonical = canonical_name_of(folder_name) or folder_name
    files, subfolders = [], []
    skipped_non_excel, truncated_files = 0, False

    def _mtime(p):
        try:
            return int(os.stat(p).st_mtime * 1000)
        except OSError:
            return None

    try:
        with os.scandir(abs_dir) as it:
            entries = sorted(it, key=lambda e: e.name.lower())
    except OSError as e:
        raise DriveError('Folder lokal "%s" tidak bisa dibaca: %s' % (abs_dir, e))
    for e in entries:
        name = e.name
        if name.startswith("~$"):
            continue  # file kunci Excel (workbook sedang dibuka) — bukan data
        if e.is_dir(follow_symlinks=False):
            subfolders.append(name)
            continue
        if not EXCEL_RE.search(name):
            skipped_non_excel += 1
            continue
        if len(files) >= MAX_FILES:
            truncated_files = True
            break
        p = os.path.join(abs_dir, name)
        files.append({"abs": p, "name": name, "modifiedMs": _mtime(p),
                      "path": ("%s/%s" % (canonical, name)) if canonical else name})
    truncated_folders = len(subfolders) > MAX_SUBFOLDERS
    failed_subfolders = []
    for sub in subfolders[:MAX_SUBFOLDERS]:
        sub_dir = os.path.join(abs_dir, sub)
        try:
            with os.scandir(sub_dir) as it:
                sub_entries = sorted(it, key=lambda e: e.name.lower())
        except OSError:
            failed_subfolders.append(sub)
            continue
        for e in sub_entries:
            name = e.name
            if name.startswith("~$"):
                continue
            if e.is_dir(follow_symlinks=False) or not EXCEL_RE.search(name):
                continue
            if len(files) >= MAX_FILES:
                truncated_files = True
                break
            p = os.path.join(sub_dir, name)
            files.append({"abs": p, "name": name, "modifiedMs": _mtime(p),
                          "path": "%s/%s" % (sub, name)})
    return {"folderName": folder_name, "folderKey": map_drive_folder_key(folder_name),
            "files": files, "skippedNonExcel": skipped_non_excel,
            "truncatedFiles": truncated_files, "truncatedFolders": truncated_folders,
            "failedSubfolders": failed_subfolders}


def source_label():
    """Deskripsi sumber data untuk banner (Task 55: disk lokal saja)."""
    return "disk lokal — %s" % (LOCAL_ROOT or "(folder root belum diatur!)")


# ------------------------- Bundle lokal + engine -------------------------


def safe_rel_path(path):
    """Sanitasi path relatif (port ingest-bundle): tanpa .., tanpa absolut, tanpa __MACOSX/._"""
    p = (path or "").replace("\\", "/").lstrip("/")
    parts = [s for s in p.split("/") if s not in ("", ".")]
    if any(s == ".." for s in parts):
        raise BadFileError("path tidak aman: %s" % path)
    if any(s.startswith("__MACOSX") or s.startswith("._") for s in parts):
        return None
    return "/".join(parts)


def resolve_bundle_root(root_dir):
    """Port resolveBundlePath: satu folder pembungkus non-kanonik → turun satu level."""
    entries = [e for e in os.listdir(root_dir) if not e.startswith(".")]
    if not entries:
        raise DriveError("Bundle lokal kosong — tidak ada file yang berhasil ditarik.")
    if len(entries) == 1 and os.path.isdir(os.path.join(root_dir, entries[0])):
        if entries[0].lower() not in CANONICAL_LOWER:
            return os.path.join(root_dir, entries[0])
    return root_dir


def engine_health():
    try:
        return http_json("GET", ENGINE_URL + "/health", timeout=6)
    except Exception:
        return None


def engine_process(job, bundle_path):
    body = {
        "periodKey": job["periodKey"],
        "tanggalH": job["tanggalH"],
        "ambangAcrPct": job["ambangAcrPct"],
        "bundleName": job.get("bundleName"),
        "bundlePath": bundle_path,
    }
    log("Memanggil engine FastAPI %s/process …" % ENGINE_URL)
    req = urllib.request.Request(ENGINE_URL + "/process", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    token = os.environ.get("SM_ENGINE_TOKEN")
    if token:
        req.add_header("x-engine-token", token)
    with urllib.request.urlopen(req, data=json.dumps(body).encode("utf-8"), timeout=900) as res:
        return json.loads(res.read().decode("utf-8", "replace"))


# ------------------------- State agent -------------------------

class Agent:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.stop_event = threading.Event()
        self.heartbeater = None
        self.progress_pct = 0
        self.progress_msg = "menyiapkan…"

    # ---- laporkan kemajuan; balasan cancelled → set cancel_event ----
    def report(self, job_id, action, payload=None, retries=2):
        body = {"action": action}
        if payload:
            body.update(payload)
        last = None
        for attempt in range(retries + 1):
            try:
                out = http_json("POST",
                                "%s/api/agent/jobs/%s/report" % (SERVER, job_id),
                                body, token=AGENT_TOKEN, timeout=45)
                if out.get("cancelled"):
                    self.cancel_event.set()
                return out
            except RuntimeError as e:
                last = e
                if "HTTP 40" in str(e) or "HTTP 422" in str(e):
                    raise  # salah input — jangan diulang
                time.sleep(2 * (attempt + 1))
        raise last

    def progress(self, job_id, pct, msg):
        self.progress_pct = pct
        self.progress_msg = msg
        return self.report(job_id, "progress", {"progress": pct, "message": msg})

    def fail(self, job_id, error):
        try:
            self.report(job_id, "fail", {"error": error[:400]})
        except Exception:
            pass

    def start_heartbeat(self, job_id):
        def beat():
            while not self.cancel_event.is_set():
                time.sleep(HEARTBEAT_INTERVAL)
                try:
                    self.report(job_id, "progress",
                                {"progress": self.progress_pct, "message": self.progress_msg})
                except Exception:
                    pass
        self.heartbeater = threading.Thread(target=beat, daemon=True)
        self.heartbeater.start()

    def check_cancel(self, note=""):
        if self.cancel_event.is_set():
            raise KeyboardInterrupt("dibatalkan dari web%s" % (" — " + note if note else ""))


# ------------------------- Pemrosesan satu job -------------------------


def process_job(agent, job):
    job_id = job["id"]
    targets = job.get("targets") or []
    work = WORKDIR / job_id
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    skipped_files, notices = [], []
    try:
        agent.progress(job_id, 2, "Membaca daftar file (%d folder)…" % len(targets))

        # ---- listing + dedupe lintas folder ----
        # Task 55: sumber = DISK LOKAL SAJA (fitur Google Drive dihapus).
        # Folder yang tidak ada di RootPath diberi catatan jujur dan dilewati;
        # semua folder absen → job gagal dengan pesan yang bisa ditindaklanjuti.
        merged = []
        seen_paths = set()
        missing_local = []
        for t in targets:
            agent.check_cancel("saat listing")
            folder_name = str(t.get("folderName") or "")
            local_dir = find_local_folder(folder_name)
            if local_dir:
                col = collect_local_files(local_dir, folder_name)
                src = "local"
                log('  Folder "%s" ← DISK LOKAL (%s)' % (folder_name, local_dir))
            else:
                missing_local.append(folder_name or str(t.get("folderKey") or "?"))
                notices.append('Folder "%s" tidak ada di disk lokal (%s) — dilewati.'
                               % (folder_name, LOCAL_ROOT or "root belum diatur"))
                continue
            ded = dedupe_drive_files(col["files"])
            if col["truncatedFiles"]:
                notices.append('Folder "%s": file melebihi batas %d.' % (col["folderName"], MAX_FILES))
            if col["truncatedFolders"]:
                notices.append('Folder "%s": subfolder lebih dari %d.' % (col["folderName"], MAX_SUBFOLDERS))
            for fs in col["failedSubfolders"]:
                notices.append('Subfolder "%s" gagal dibaca — dilewati.' % fs)
            for f in ded["kept"]:
                if f["path"] in seen_paths:
                    raise DriveError('Dua folder memetakan ke path sama ("%s") — cek isi RootData.' % f["path"])
                seen_paths.add(f["path"])
                f["src"] = src
                merged.append(f)
            skipped_files.extend(ded["skipped"])
        if not merged:
            raise DriveError("Tidak ada file Excel — folder berikut tidak ditemukan di disk "
                             'lokal "%s": "%s". Atur SMWEB_LOCAL_ROOT / folder Root Data di '
                             'launcher ke folder induk export (mis. C:\\KERJA\\1. RESTO\\9.NEW QUERY).'
                             % (LOCAL_ROOT or "(root belum diatur)", '", "'.join(missing_local)))

        # ---- salin dari disk lokal ----
        n = len(merged)
        log("Menyalin %d file Excel dari disk lokal…" % n)
        for i, f in enumerate(merged):
            agent.check_cancel("saat menyalin %s" % f["name"])
            agent.progress(job_id, 5 + int(60 * i / max(n, 1)),
                           "Menyalin %d/%d — %s" % (i + 1, n, f["name"]))
            rel = safe_rel_path(f["path"])
            if not rel:
                continue
            try:
                with open(f["abs"], "rb") as fh:
                    buf = fh.read()
                if len(buf) == 0:
                    raise BadFileError("File kosong (0 byte).")
                if len(buf) > MAX_FILE_BYTES:
                    raise DriveError("File %.0f MB — melebihi batas 60 MB per file."
                                     % (len(buf) / 1048576))
                head = buf[:4]
                if not (head == b"PK\x03\x04" or head == b"\xd0\xcf\x11\xe0"):
                    raise BadFileError("Isi bukan Excel (%d byte) — kemungkinan rusak." % len(buf))
            except BadFileError as e:
                skipped_files.append({"path": f["path"], "reason": str(e)})
                log("  DILEWATI %s: %s" % (f["name"], e), "WARN")
                continue
            total_bytes += len(buf)
            if total_bytes > MAX_TOTAL_BYTES:
                raise DriveError("Total salinan melebihi 400 MB — pisahkan foldernya.")
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(buf)
            log("  [%d/%d] %s (%.1f MB) · disk" % (i + 1, n, f["name"], len(buf) / 1048576), "OK")

        # ---- jalankan engine LOKAL ----
        agent.check_cancel("sebelum engine")
        bundle_root = resolve_bundle_root(str(work))
        agent.progress(job_id, 70, "Engine FastAPI memproses pipeline v3.9.71 di laptop…")
        result = engine_process(job, bundle_root)
        rows = len(result.get("rows", []))
        log("Engine selesai: %s · %s baris · %.1fs" % (
            result.get("status"), format(rows, ","), (result.get("durationMs") or 0) / 1000), "OK")

        # ---- unggah hasil ter-gzip ter-chunk ----
        agent.check_cancel("sebelum unggah")
        agent.progress(job_id, 90, "Mengunggah hasil (%s baris)…" % format(rows, ","))
        gz = gzip.compress(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
        chunks = [gz[i:i + CHUNK_BYTES] for i in range(0, len(gz), CHUNK_BYTES)]
        for seq, piece in enumerate(chunks):
            agent.check_cancel("mengunggah potongan %d" % seq)
            out = agent.report(job_id, "chunk",
                               {"seq": seq, "data": base64.b64encode(piece).decode("ascii")}, retries=3)
            if out.get("cancelled"):
                agent.cancel_event.set()
                raise KeyboardInterrupt("dibatalkan dari web saat mengunggah")
            log("  potongan %d/%d terunggah (%.1f KB)" % (seq + 1, len(chunks), len(piece) / 1024))
        log("Mengabarkan server untuk merakit hasil…")

        # ---- complete (server merakit & membuat run) — 5x percobaan utk fluktuasi jaringan ----
        last = None
        for attempt in range(5):
            try:
                out = agent.report(job_id, "complete", retries=0)
                break
            except RuntimeError as e:
                msg = str(e)
                if "HTTP 409" in msg and "dibatalkan" in msg:
                    agent.cancel_event.set()
                    raise KeyboardInterrupt("job dibatalkan di web")
                last = e
                log("  complete gagal (%s) — coba lagi %d/5…" % (msg, attempt + 1), "WARN")
                time.sleep(3 * (attempt + 1))
        else:
            raise last

        if out.get("cancelled"):
            log("Job %s DIBATALKAN di web — hasil dibuang." % job_id[:8], "WARN")
        else:
            log("RUN DIBUAT DI WEB: runBatchId %s · %s baris" % (
                out.get("runBatchId"), format(out.get("rowCount") or 0, ",")), "OK")
            log("Buka %s → tab 🚀 Proses & Ingest → pratinjau run → tekan KOMIT." % SERVER, "OK")

        # pesan progres akhir jujur (kalau job masih hidup)
        notes = ""
        if skipped_files:
            notes += " · %d file dilewati" % len(skipped_files)
        if notices:
            notes += " · %d catatan" % len(notices)
        try:
            agent.progress(job_id, 100, "Selesai — hasil sudah di web%s." % (notes or ""))
        except Exception:
            pass
    except KeyboardInterrupt as e:
        log("Job %s berhenti: %s" % (job_id[:8], e), "WARN")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------- Loop utama -------------------------


def claim_once(agent):
    eng = engine_health()
    body = {"agentName": AGENT_NAME, "engine": eng}
    out = http_json("POST", SERVER + "/api/agent/claim", body, token=AGENT_TOKEN, timeout=30)
    return out.get("job"), eng


def main():
    once = "--once" in sys.argv
    log("=" * 64)
    log("SM-WEB Agent Lokal — python memproses di laptop, hasil tampil di web")
    log("  Server : %s" % SERVER)
    log("  Engine : %s" % ENGINE_URL)
    log("  Agent  : %s" % AGENT_NAME)
    log("  Sumber : %s" % source_label())
    log("  Kerja  : %s" % WORKDIR)
    log("=" * 64)
    if _DATA_SOURCE_DEPRECATED:
        log("Catatan: SMWEB_DATA_SOURCE=%s diabaikan — fitur Google Drive sudah "
            "DIHAPUS (Task 55); agent hanya membaca disk lokal." % _DATA_SOURCE_ENV, "WARN")
    if not LOCAL_ROOT:
        log("Catatan: SMWEB_LOCAL_ROOT belum diatur — agent memakai RootPath bawaan "
            "(atur lewat tombol Root Data di launcher bila folder data bukan default).", "WARN")

    agent = Agent()

    def on_sigint(_sig, _frm):
        agent.stop_event.set()
        agent.cancel_event.set()
    signal.signal(signal.SIGINT, on_sigint)

    polls = 0
    while not agent.stop_event.is_set():
        try:
            job, eng = claim_once(agent)
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 401" in msg or "HTTP 503" in msg:
                log("STOP: %s" % msg, "ERR")
                log("   Set env SMWEB_AGENT_TOKEN sama dengan AGENT_TOKEN di server.", "ERR")
                sys.exit(2)
            if "HTTP 4" in msg:
                log("Server menolak: %s" % msg, "ERR")
                sys.exit(2)
            log("Poll gagal: %s" % msg, "WARN")
            time.sleep(POLL_INTERVAL * 2)
            continue

        if not eng:
            log("⚠ Engine FastAPI di %s belum jalan — jalankan dulu " % ENGINE_URL +
                "mini-services/engine-fastapi (uvicorn app:app --port 3031), " +
                "kalau tidak job yang diambil akan gagal jujur.", "WARN")

        if not job:
            polls += 1
            if polls % 20 == 1:
                log("Menunggu job… (klik \"Kirim … Folder → Laptop\" di tab Proses & Ingest)")
            time.sleep(POLL_INTERVAL + random.uniform(0, 1.0))
            continue

        agent.cancel_event.clear()
        agent.progress_pct, agent.progress_msg = 1, "job dijemput"
        log("Job dijemput: %s · %s · %d folder target" % (
            job["id"][:10], job.get("periodKey"), len(job.get("targets") or [])), "OK")
        agent.start_heartbeat(job["id"])
        try:
            process_job(agent, job)
        except KeyboardInterrupt as e:
            log("Job berhenti: %s" % e, "WARN")
            break
        except Exception as e:
            log("Job GAGAL: %s" % e, "ERR")
            agent.fail(job["id"], str(e))
        finally:
            agent.cancel_event.set()
        if once:
            break
    log("Agent berhenti. Sampai jumpa 👋")


if __name__ == "__main__":
    main()
