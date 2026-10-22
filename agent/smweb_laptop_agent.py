#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smweb_laptop_agent.py — AGENT "PYTHON DI LAPTOP" untuk Stock-Monitoring-Web (Task 51).

Cara kerja (arsitektur PULL — web tidak bisa menjangkau laptop di balik NAT):
  1. Kamu klik "Kirim N Folder → Laptop (Proses Python)" di web  → job QUEUED.
  2. Agent ini (berjalan di laptopmu) MENJEMPUT job lewat polling /api/agent/claim
     setiap beberapa detik.
  3. Agent menarik file Excel dari folder Google Drive kamu ATAU MENYALIN
     langsung dari folder data di disk lokal (Sumber Data — Task 53:
     "langsung dari disk C, tanpa Google Drive"), menjalankan
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
  SMWEB_DATA_SOURCE   sumber data job: auto (default) | local | drive
  SMWEB_LOCAL_ROOT    folder induk data lokal, setara RootPath config.json
                      desktop (mis. C:\\KERJA\\1. RESTO\\9.NEW QUERY) —
                      di dalamnya harus ada folder bernama sama dengan judul
                      job ("1. DEVIASI WEEKLY", "2. 22.05", dst); dipakai saat
                      sumber auto/local; launcher punya tombol "Sumber Data".
"""

import base64
import calendar
import getpass
import gzip
import html
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
# Sumber data job (permintaan user: "langsung dari disk C, tanpa Google Drive"):
#   auto  = folder ada di disk (SMWEB_LOCAL_ROOT) → salin dari disk; sisanya Drive
#   local = hanya disk — folder yang absen diberi catatan jujur, tanpa unduh Drive
#   drive = selalu Google Drive (perilaku lama sebelum fitur ini)
DATA_SOURCE = (os.environ.get("SMWEB_DATA_SOURCE") or "auto").strip().lower() or "auto"
if DATA_SOURCE not in ("auto", "drive", "local"):
    DATA_SOURCE = "auto"
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

# Pemetaan folder kunci config.json — IDENTIK src/lib/bundles.ts (FR-2).
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


def decode_entities(s):
    return html.unescape(s)


def parse_drive_date(raw):
    """Port parseDriveDate (UTC, setara Date.UTC TS): 'Oct 20' / 'Oct 20, 2024' /
    '8/25/25' / '12/3/2024' / '9:53 pm' → epoch ms, atau None."""
    if not raw:
        return None
    s = raw.strip()
    m = re.match(r"^([A-Za-z]{3})\s+(\d{1,2})(?:,\s*(\d{4}))?$", s)
    if m and m.group(1).lower() in MONTHS:
        year = int(m.group(3)) if m.group(3) else time.gmtime().tm_year
        try:
            return calendar.timegm((year, MONTHS[m.group(1).lower()] + 1, int(m.group(2)),
                                    0, 0, 0, 0, 0, 0)) * 1000
        except Exception:
            return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        if 1 <= month <= 12 and 1 <= day <= 31:
            return calendar.timegm((year, month, day, 0, 0, 0, 0, 0, 0)) * 1000
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)$", s, re.IGNORECASE)
    if m:
        now = time.gmtime()
        hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
        return calendar.timegm((now.tm_year, now.tm_mon, now.tm_mday, hour, int(m.group(2)),
                                0, 0, 0, 0)) * 1000
    return None


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


def list_drive_folder(folder_id, timeout=15):
    if not FOLDER_ID_RE.match(folder_id):
        raise DriveError("ID folder Drive tidak valid: %s" % folder_id)
    url = "https://drive.google.com/embeddedfolderview?id=" + folder_id
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            if res.status == 404:
                raise DriveError("Folder Drive tidak ditemukan (404) — cek link-nya.")
            html_text = res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise DriveError("Folder Drive tidak ditemukan (404) — cek link-nya.")
        raise DriveError("Drive merespons HTTP %d — coba lagi sebentar." % e.code) from e
    except urllib.error.URLError as e:
        raise DriveError("Tidak bisa menghubungi Drive: %s" % getattr(e, "reason", e)) from e

    m = re.search(r"<title>([^<]*)</title>", html_text)
    title = decode_entities(m.group(1)).strip() if m else ""
    if not title or "accounts.google.com" in html_text:
        raise DriveError('Folder tidak bisa dibaca — pastikan dibagikan "Siapa saja yang '
                         "memiliki link\" akses Viewer.")
    entries = []
    for block in html_text.split('<div class="flip-entry" id="entry-')[1:]:
        end = block.find('"')
        fid = block[:end] if end > 0 else ""
        if not FOLDER_ID_RE.match(fid):
            continue
        nm = re.search(r'flip-entry-title">([^<]+)<', block)
        if not nm:
            continue
        mod = re.search(r'flip-entry-last-modified"><div>([^<]+)<', block)
        entries.append({
            "id": fid,
            "name": decode_entities(nm.group(1)),
            "isFolder": "/drive/folders/" in block,
            "modifiedMs": parse_drive_date(decode_entities(mod.group(1)) if mod else None),
        })
    if not entries:
        raise DriveError('Folder Drive "%s" kosong atau isinya tidak terbaca.' % title)
    return {"folderId": folder_id, "folderName": title, "entries": entries}


def collect_drive_files(folder_id):
    """Port collectDriveFiles: file Excel root + subfolder (kedalaman 2)."""
    root = list_drive_folder(folder_id)
    canonical = canonical_name_of(root["folderName"])
    files, subfolders, skipped_non_excel, truncated_files = [], [], 0, False

    for e in root["entries"]:
        if e["isFolder"]:
            subfolders.append(e)
            continue
        if not EXCEL_RE.search(e["name"]):
            skipped_non_excel += 1
            continue
        if len(files) >= MAX_FILES:
            truncated_files = True
            break
        files.append({"id": e["id"], "name": e["name"], "modifiedMs": e["modifiedMs"],
                      "path": ("%s/%s" % (canonical, e["name"])) if canonical else e["name"]})
    truncated_folders = len(subfolders) > MAX_SUBFOLDERS
    failed_subfolders = []
    for sub in subfolders[:MAX_SUBFOLDERS]:
        try:
            sub_list = list_drive_folder(sub["id"])
        except DriveError:
            failed_subfolders.append(sub["name"])
            continue
        for e in sub_list["entries"]:
            if e["isFolder"] or not EXCEL_RE.search(e["name"]):
                continue
            if len(files) >= MAX_FILES:
                truncated_files = True
                break
            files.append({"id": e["id"], "name": e["name"], "modifiedMs": e["modifiedMs"],
                          "path": "%s/%s" % (sub["name"], e["name"])})
    if not files:
        raise DriveError('Tidak ada file Excel (.xlsx/.xls/.xlsb) di folder Drive "%s".' % root["folderName"])
    return {"folderName": root["folderName"], "folderKey": map_drive_folder_key(root["folderName"]),
            "files": files, "skippedNonExcel": skipped_non_excel,
            "truncatedFiles": truncated_files, "truncatedFolders": truncated_folders,
            "failedSubfolders": failed_subfolders}


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


def download_drive_file(file_id):
    """Port downloadDriveFile: confirm=t retry + magic bytes Excel + batas ukuran."""
    url = "https://drive.google.com/uc?export=download&id=" + file_id

    def fetch(u):
        req = urllib.request.Request(u)
        req.add_header("User-Agent", UA)
        req.add_header("Accept-Language", "en-US,en;q=0.9")
        with urllib.request.urlopen(req, timeout=180) as res:
            declared = int(res.headers.get("Content-Length") or 0)
            if declared > MAX_FILE_BYTES:
                raise DriveError("File %.0f MB — melebihi batas 60 MB per file." % (declared / 1048576))
            return res.read()

    buf = fetch(url)
    head = buf[:512].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        buf = fetch(url + "&confirm=t")
    head = buf[:512].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        raise BadFileError("Drive mengembalikan halaman konfirmasi/konflik — file tidak bisa ditarik otomatis.")
    if len(buf) == 0:
        raise BadFileError("File kosong (0 byte).")
    if not (buf[:4] == b"PK\x03\x04" or buf[:4] == b"\xd0\xcf\x11\xe0"):
        raise BadFileError("Isi bukan Excel (%d byte) — kemungkinan file rusak/placeholder." % len(buf))
    if len(buf) > MAX_FILE_BYTES:
        raise DriveError("File %.0f MB — melebihi batas 60 MB per file." % (len(buf) / 1048576))
    return buf


# ------------------------- Disk lokal: listing + salin (paralel Drive) -------------------------


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
    """Deskripsi sumber data untuk banner."""
    if DATA_SOURCE == "drive":
        return "Google Drive"
    if DATA_SOURCE == "local":
        return "disk lokal — %s" % (LOCAL_ROOT or "(folder root belum diatur!)")
    if LOCAL_ROOT:
        return "otomatis — disk %s dulu, sisanya Drive" % LOCAL_ROOT
    return "otomatis — Google Drive (folder data lokal belum diatur)"


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

        # ---- listing + dedupe lintas folder (port planDrivePull) ----
        # Sumber per-folder mengikuti DATA_SOURCE: "auto" = disk lokal dulu,
        # folder yang absen ditarik dari Drive; "local" = hanya disk (folder
        # absen → catatan, tanpa unduh); "drive" = seperti dulu.
        merged = []
        seen_paths = set()
        missing_local = []
        for t in targets:
            agent.check_cancel("saat listing")
            folder_name = str(t.get("folderName") or "")
            local_dir = find_local_folder(folder_name) if DATA_SOURCE in ("auto", "local") else None
            if local_dir:
                col = collect_local_files(local_dir, folder_name)
                src = "local"
                log('  Folder "%s" ← DISK LOKAL (%s)' % (folder_name, local_dir))
            elif DATA_SOURCE == "local":
                missing_local.append(folder_name or str(t.get("folderId") or "?"))
                notices.append('Folder "%s" tidak ada di disk lokal (%s) — dilewati.'
                               % (folder_name, LOCAL_ROOT or "root belum diatur"))
                continue
            else:
                col = collect_drive_files(t["folderId"])
                src = "drive"
                if DATA_SOURCE == "auto":
                    log('  Folder "%s" ← GOOGLE DRIVE (tidak ada di disk lokal)' % folder_name)
            ded = dedupe_drive_files(col["files"])
            if col["truncatedFiles"]:
                notices.append('Folder "%s": file melebihi batas %d.' % (col["folderName"], MAX_FILES))
            if col["truncatedFolders"]:
                notices.append('Folder "%s": subfolder lebih dari %d.' % (col["folderName"], MAX_SUBFOLDERS))
            for fs in col["failedSubfolders"]:
                notices.append('Subfolder "%s" gagal dibaca — dilewati.' % fs)
            for f in ded["kept"]:
                if f["path"] in seen_paths:
                    raise DriveError('Dua link memetakan ke path sama ("%s") — hapus salah satu.' % f["path"])
                seen_paths.add(f["path"])
                f["src"] = src
                merged.append(f)
            skipped_files.extend(ded["skipped"])
        if not merged:
            if missing_local:
                raise DriveError("Tidak ada file Excel — folder berikut tidak ditemukan di disk "
                                 'lokal "%s": "%s". Periksa tombol Sumber Data di launcher.'
                                 % (LOCAL_ROOT or "(root belum diatur)", '", "'.join(missing_local)))
            raise DriveError("Tidak ada file Excel yang bisa ditarik dari folder itu.")

        # ---- salin dari disk / unduh dari Drive ----
        n = len(merged)
        n_local = sum(1 for f in merged if f.get("src") == "local")
        n_drive = n - n_local
        if n_local:
            log("Menyalin %d file Excel dari disk lokal…" % n_local)
        if n_drive:
            log("Menarik %d file Excel dari Google Drive…" % n_drive)
        for i, f in enumerate(merged):
            is_local = f.get("src") == "local"
            agent.check_cancel("saat menyalin %s" % f["name"] if is_local
                               else "saat mengunduh %s" % f["name"])
            agent.progress(job_id, 5 + int(60 * i / max(n, 1)),
                           "%s %d/%d — %s" % ("Menyalin" if is_local else "Mengunduh",
                                              i + 1, n, f["name"]))
            rel = safe_rel_path(f["path"])
            if not rel:
                continue
            try:
                if is_local:
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
                else:
                    buf = download_drive_file(f["id"])
            except BadFileError as e:
                skipped_files.append({"path": f["path"], "reason": str(e)})
                log("  DILEWATI %s: %s" % (f["name"], e), "WARN")
                continue
            total_bytes += len(buf)
            if total_bytes > MAX_TOTAL_BYTES:
                raise DriveError("Total salinan/unduhan melebihi 400 MB — pisahkan foldernya.")
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(buf)
            log("  [%d/%d] %s (%.1f MB)%s" % (i + 1, n, f["name"], len(buf) / 1048576,
                " · disk" if is_local else ""), "OK")

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
