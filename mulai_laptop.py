#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mulai_laptop.py — LAUNCHER SEKALI-KLIK "Python di Laptop" (Task 52).

Menggantikan 4 langkah manual (git pull → pip install → terminal-1 engine →
terminal-2 agent) menjadi SATU dobel-klik:

  Windows : dobel-klik  mulai-laptop.bat
  macOS   : dobel-klik  mulai-laptop.command
  Linux   : ./mulai-laptop.sh  (atau: python3 mulai_laptop.py)

Yang otomatis dikerjakan launcher ini:
  1. git pull --ff-only (opsional, non-fatal — kode selalu terbaru)
  2. Menyiapkan Python + dependensi engine (pandas/openpyxl/uvicorn/…):
       a. pakai venv .venv-laptop bila sudah siap (paling cepat),
       b. atau pakai Python sistem bila dependensinya sudah terpasang
          (misal kamu pernah `pip install -r requirements.txt` manual),
       c. atau MEMBUAT venv + `pip install` otomatis saat pertama kali.
  3. Menjalankan ENGINE FastAPI produksi di :3031 (dipakai ulang bila sudah
     jalan — tidak pernah membunuh engine milik orang lain).
  4. Menjalankan AGENT agent/smweb_laptop_agent.py dengan token dari
     laptop_config.json (file lokal, di-gitignore — token tidak pernah
     masuk GitHub).
  5. Menampilkan status WEB ✓ / ENGINE ✓ / AGENT ✓ + job yang sedang
     diproses, lalu log langsung dari engine & agent.

Hanya STDLIB Python (tkinter bila tersedia; tanpa GUI pun tetap jalan).
Konfigurasi: laptop_config.json (dibuat otomatis saat pertama kali).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

# ------------------------- Path & konstanta -------------------------

APP_TITLE = "Stock Monitoring — Python di Laptop"
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "laptop_config.json"
VENV_DIR = ROOT / ".venv-laptop"
ENGINE_DIR = ROOT / "mini-services" / "engine-fastapi"
REQUIREMENTS = ENGINE_DIR / "requirements.txt"
AGENT_PATH = ROOT / "agent" / "smweb_laptop_agent.py"
DEPS_MARKER = VENV_DIR / ".smweb-deps-ok"

DEFAULT_CONFIG = {
    # URL web produksi (bisa diganti ke http://127.0.0.1:3000 untuk uji lokal)
    "server": "https://stock-monitoring-web.vercel.app",
    # Token agent — SAMA dengan env AGENT_TOKEN di server. Diisi SEKALI lewat
    # dialog/konfigurasi; file ini di-gitignore (tidak ikut ke GitHub).
    "agent_token": "",
    # Nama agent yang tampil di badge web (kosong = otomatis "laptop-<user>")
    "agent_name": "",
    "engine_host": "127.0.0.1",
    "engine_port": 3031,
    # Pakai venv .venv-laptop bila dependensi sistem tidak lengkap
    "use_venv": True,
    # git pull --ff-only tiap mulai (non-fatal bila gagal)
    "auto_update": True,
    # Langsung menyala sendiri begitu launcher dibuka (sekali-klik!)
    "autostart": True,
    # Buka browser ke dashboard web setelah tersambung
    "open_dashboard": False,
}

# Satu probe untuk semua dependensi engine (pandas<3 dst — requirements.txt)
ENGINE_IMPORT_PROBE = (
    "import pandas, openpyxl, numpy, httpx, fastapi, uvicorn, pyxlsb, "
    "python_calamine, sys; "
    "sys.exit(3 if int(pandas.__version__.split('.')[0]) >= 3 else 0)"
)

ANSI = {
    "INFO": "",
    "OK": "\033[92m",
    "WARN": "\033[93m",
    "ERR": "\033[91m",
    "DIM": "\033[90m",
}
RESET = "\033[0m"
_IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _supports_ansi() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        os.system("")  # mengaktifkan virtual-terminal di Windows 10+
    return _IS_TTY


USE_ANSI = _supports_ansi()


# ------------------------- Util -------------------------


def now_ts() -> str:
    return time.strftime("%H:%M:%S")


def http_get_json(url: str, timeout: float):
    """GET JSON; kembalikan dict atau None bila gagal (tidak pernah melempar)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "smweb-launcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read().decode("utf-8", "replace")
            return json.loads(body) if body.strip() else {}
    except Exception:
        return None


def run_capture(cmd, timeout: int, cwd=None, env=None):
    """subprocess.run dengan output gabung stdout+stderr sebagai teks."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        return p.returncode, (p.stdout or "")
    except Exception as e:  # timeout / binary hilang
        return 127, str(e)


# ------------------------- Konfigurasi -------------------------


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                for k in DEFAULT_CONFIG:
                    if k in user:
                        cfg[k] = user[k]
        except Exception:
            pass  # config rusak → pakai default, tulis ulang saat simpan
    return cfg


def save_config(cfg: dict) -> None:
    """Tulis atomik (tmp → rename) supaya selalu valid."""
    try:
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


def gitignore_has_entry(entry: str) -> bool:
    gi = ROOT / ".gitignore"
    if not gi.exists():
        return False
    try:
        return any(
            line.strip() in (entry, entry.strip("/"))
            for line in gi.read_text(encoding="utf-8", errors="replace").splitlines()
        )
    except Exception:
        return False


# ------------------------- Log -------------------------


class LogBus:
    """Buffer memori + distribusi ke konsol dan callback UI (thread-safe)."""

    def __init__(self):
        self.lines = deque(maxlen=3000)
        self.lock = threading.Lock()
        self.ui_cb = None  # fn(ts, prefix, msg, level) — dipasang UI

    def emit(self, msg: str, level: str = "INFO", prefix: str = "") -> None:
        line = f"[{now_ts()}]{' ' + prefix if prefix else ''} {msg}"
        with self.lock:
            self.lines.append((line, level))
        if USE_ANSI and ANSI.get(level):
            print(f"{ANSI[level]}{line}{RESET}", flush=True)
        else:
            print(line, flush=True)
        cb = self.ui_cb
        if cb:
            try:
                cb(now_ts(), prefix, msg, level)
            except Exception:
                pass

    def tail(self, n: int = 40):
        with self.lock:
            return list(self.lines)[-n:]


LOG = LogBus()


# ------------------------- Controller -------------------------


class StackController:
    """Mengelola engine + agent sebagai subprocess, plus status polling."""

    def __init__(self, cfg: dict, args):
        self.cfg = cfg
        self.args = args
        self.state = "idle"  # idle | starting | running | stopping
        self.engine_proc = None
        self.agent_proc = None
        self.owns_engine = False
        self.engine_url = self._engine_url()
        self.stop_flag = threading.Event()
        self.status = {
            "web": None, "engine": None,
            "agent": False, "agent_reason": "", "job": None,
        }
        self.status_cb = None      # fn(status dict) — UI
        self.state_cb = None       # fn(state str) — UI
        self._lock = threading.Lock()
        self._restart_engine = 0
        self._restart_agent = 0
        self._poll_count = 0
        self._web_warned = False
        self.start_failed = False
        self._py = sys.executable or "python3"

    # ---- helper ----

    def _engine_url(self) -> str:
        host = str(self.cfg.get("engine_host") or "127.0.0.1")
        if host in ("0.0.0.0", "::", "*"):
            host = "127.0.0.1"  # connect selalu lewat loopback
        port = int(self.cfg.get("engine_port") or 3031)
        return f"http://{host}:{port}"

    def _set_state(self, s: str) -> None:
        self.state = s
        if self.state_cb:
            try:
                self.state_cb(s)
            except Exception:
                pass

    def _push_status(self) -> None:
        if self.status_cb:
            try:
                self.status_cb(dict(self.status))
            except Exception:
                pass

    # ---- siklus hidup ----

    def start_async(self) -> None:
        threading.Thread(target=self._start_sync, daemon=True, name="starter").start()

    def _start_sync(self) -> None:
        with self._lock:
            if self.state in ("starting", "running", "stopping"):
                return
            self._set_state("starting")
        try:
            self._do_start()
        except Exception as e:
            LOG.emit(f"Gagal memulai: {e}", "ERR")
            LOG.emit("Klik MULAI lagi setelah memperbaiki penyebab di atas.", "WARN")
            self.start_failed = True
            self._set_state("idle")

    def _do_start(self) -> None:
        stop_flag = self.stop_flag

        # 0) Token wajib — tanpa ini agent pasti ditolak server
        if not str(self.cfg.get("agent_token") or "").strip():
            raise RuntimeError(
                "Token agent kosong — isi lewat tombol \u201cUbah Token\u201d "
                "(nilainya sama dengan env AGENT_TOKEN di server web)."
            )

        # 1) Perbarui kode (opsional, non-fatal)
        if self.cfg.get("auto_update") and not self.args.no_update:
            if (ROOT / ".git").exists():
                LOG.emit("Memperbarui kode dari GitHub (git pull)…", "DIM")
                code, out = run_capture(
                    ["git", "-C", str(ROOT), "pull", "--ff-only"], timeout=90
                )
                out_lines = [l for l in out.splitlines() if l.strip()][:4]
                for l in out_lines:
                    LOG.emit(f"git: {l[:160]}", "DIM")
                if code == 0:
                    LOG.emit("Kode mutakhir." if "Already up to date" in out
                             else "Kode diperbarui dari GitHub.", "OK")
                else:
                    LOG.emit("git pull dilewati (offline/konflik) — lanjut dengan kode yang ada.", "WARN")
            else:
                LOG.emit("Folder bukan repo git — langkah pembaruan dilewati.", "DIM")
        if stop_flag.is_set():
            return

        # 2) Siapkan Python + dependensi engine
        LOG.emit("Memeriksa dependensi engine (pandas, uvicorn, dll)…", "DIM")
        try:
            self._py = self._resolve_python()
        except RuntimeError as e:
            LOG.emit(str(e), "ERR")
            raise
        if stop_flag.is_set():
            return

        # 3) Engine FastAPI :3031
        if not self._ensure_engine():
            raise RuntimeError("Engine tidak dapat dijalankan.")
        if stop_flag.is_set():
            return

        # 4) Agent
        if not self._spawn_agent():
            raise RuntimeError("Agent tidak dapat dijalankan.")

        self._set_state("running")
        LOG.emit("=" * 60, "OK")
        LOG.emit(f"SEMUA SIAP ✓ — server: {self.cfg.get('server')}", "OK")
        LOG.emit("Sekarang buka web, centang folder Drive, klik "
                "\u201cKirim … Folder \u2192 Laptop (Proses Python)\u201d.", "OK")
        LOG.emit("Tinggalkan jendela ini terbuka selama ingin tetap tersambung.", "DIM")
        if self.cfg.get("open_dashboard"):
            try:
                import webbrowser
                webbrowser.open(self.cfg.get("server"))
            except Exception:
                pass

        # 5) Loop status (thread ini terus berjalan sebagai poller)
        self._monitor_loop()

    # catatan: _monitor_loop keluar dengan return — sinyal stop diproses
    # lewat stop_flag; semua jalur keluarnya sudah memanggil stop_sync.

    # ---- Python & dependensi ----

    def _venv_python(self) -> Path:
        if os.name == "nt":
            return VENV_DIR / "Scripts" / "python.exe"
        return VENV_DIR / "bin" / "python"

    def _venv_ready_marker(self) -> str | None:
        try:
            want = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
            if DEPS_MARKER.exists() and DEPS_MARKER.read_text(encoding="utf-8").strip() == want:
                return want
        except Exception:
            pass
        return None

    def _write_marker(self) -> None:
        try:
            VENV_DIR.mkdir(parents=True, exist_ok=True)
            DEPS_MARKER.write_text(
                hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest(), encoding="utf-8"
            )
        except Exception:
            pass

    def _probe(self, py: str) -> bool:
        code, _ = run_capture([py, "-c", ENGINE_IMPORT_PROBE], timeout=90)
        return code == 0

    def _pip_install_venv(self, venv_py: Path) -> None:
        LOG.emit("Mengunduh dependensi engine sekali saja (±1–3 menit, tergantung internet)…", "DIM")
        cmd = [str(venv_py), "-m", "pip", "install", "-r", str(REQUIREMENTS),
               "--disable-pip-version-check"]
        proc = subprocess.Popen(
            cmd, cwd=str(ENGINE_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        t0 = time.time()
        last_beat = t0
        for raw in proc.stdout or []:
            line = raw.strip()
            if line and ("Downloading" in line or "Collecting" in line or "Installing" in line):
                LOG.emit(line[:150], "DIM")
            now = time.time()
            if now - last_beat > 30:
                last_beat = now
                LOG.emit(f"… masih memasang dependensi ({int(now - t0)} dtk)", "DIM")
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(
                "pip install gagal (kode %d). Cek koneksi internet lalu jalankan lagi. "
                "Bisa juga manual: %s -m pip install -r %s"
                % (proc.returncode, sys.executable, REQUIREMENTS)
            )

    def _ensure_venv(self) -> Path:
        venv_py = self._venv_python()
        if not venv_py.exists():
            LOG.emit("Membuat lingkungan Python terpisah (.venv-laptop)…", "DIM")
            code, out = run_capture(
                [sys.executable, "-m", "venv", str(VENV_DIR)], timeout=180
            )
            if code != 0 or not venv_py.exists():
                hint = ""
                if "ensurepip" in out:
                    hint = " Di Linux: sudo apt install python3-venv python3-pip."
                raise RuntimeError(
                    "Gagal membuat venv .venv-laptop.%s Log: %s" % (hint, out.strip()[-300:])
                )
        if venv_py.exists() and self._venv_ready_marker():
            return venv_py  # cepat: marker cocok
        if venv_py.exists() and self._probe(str(venv_py)):
            LOG.emit("Dependensi venv sudah lengkap.", "OK")
            self._write_marker()
            return venv_py
        self._pip_install_venv(venv_py)
        if not self._probe(str(venv_py)):
            raise RuntimeError(
                "Dependensi engine tetap tidak lengkap setelah pip install. "
                "Coba manual: %s -m pip install -r %s" % (venv_py, REQUIREMENTS)
            )
        self._write_marker()
        LOG.emit("Dependensi engine siap (tersimpan di .venv-laptop).", "OK")
        return venv_py

    def _resolve_python(self) -> str:
        if self.args.force_venv:
            return str(self._ensure_venv())
        # a) venv sudah siap (marker)
        venv_py = self._venv_python()
        if venv_py.exists() and self._venv_ready_marker():
            LOG.emit("Memakai .venv-laptop (dependensi lengkap).", "OK")
            return str(venv_py)
        # b) python sistem sudah punya semua dependensi (mis. pernah pip install manual)
        if self._probe(sys.executable or "python3"):
            LOG.emit("Dependensi ditemukan di Python sistem — dipakai apa adanya (tanpa unduh ulang).", "OK")
            return sys.executable or "python3"
        # c) siapkan venv
        if not self.cfg.get("use_venv", True):
            raise RuntimeError(
                "Dependensi engine belum terpasang dan use_venv=false. "
                "Jalankan: pip install -r %s (atau set use_venv=true di laptop_config.json)"
                % REQUIREMENTS
            )
        return str(self._ensure_venv())

    # ---- engine ----

    def _engine_health(self, timeout: float = 4.0):
        return http_get_json(self.engine_url + "/health", timeout)

    def _spawn_engine(self, py: str):
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [py, "-m", "uvicorn", "app:app",
               "--app-dir", str(ENGINE_DIR),
               "--host", str(self.cfg.get("engine_host") or "127.0.0.1"),
               "--port", str(self.cfg.get("engine_port") or 3031)]
        proc = subprocess.Popen(
            cmd, cwd=str(ENGINE_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        self._attach_reader(proc, "ENGINE")
        return proc

    def _ensure_engine(self) -> bool:
        health = self._engine_health()
        if health and health.get("status") == "ok":
            self.owns_engine = False
            self.engine_proc = None
            LOG.emit(f"Engine sudah berjalan di {self.engine_url} — dipakai ulang.", "OK")
            return True
        LOG.emit(f"Menyalakan engine FastAPI di {self.engine_url}…", "DIM")
        proc = self._spawn_engine(self._py)
        self.engine_proc = proc
        self.owns_engine = True
        t0 = time.time()
        deadline = t0 + 180  # import pandas pertama bisa lambat
        while time.time() < deadline:
            if self.stop_flag.is_set():
                return False
            if proc.poll() is not None:
                LOG.emit("Engine mati saat menyala (cek log [ENGINE] di bawah).", "ERR")
                return False
            time.sleep(1.0)
            if self._engine_health():
                dur = int(time.time() - t0)
                LOG.emit(f"Engine FastAPI siatap {self.engine_url} ({dur} dtk).", "OK")
                return True
        LOG.emit("Engine tidak menjawab /health dalam 180 dtk.", "ERR")
        return False

    # ---- agent ----

    def _spawn_agent(self) -> bool:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["SMWEB_SERVER"] = str(self.cfg.get("server") or "").rstrip("/")
        env["SMWEB_AGENT_TOKEN"] = str(self.cfg.get("agent_token") or "")
        env["SMWEB_ENGINE_URL"] = self.engine_url
        name = str(self.cfg.get("agent_name") or "").strip()
        if name:
            env["SMWEB_AGENT_NAME"] = name
        cmd = [self._py, str(AGENT_PATH)]
        if self.args.once:
            cmd.append("--once")
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(ROOT), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            LOG.emit(f"Gagal menjalankan agent: {e}", "ERR")
            return False
        self.agent_proc = proc
        self._attach_reader(proc, "AGENT")
        self.status["agent"] = True
        self.status["agent_reason"] = ""
        self._restart_agent = 0
        LOG.emit("Agent berjalan — menunggu/menjemput job dari web…", "OK")
        return True

    # ---- reader & monitor ----

    def _attach_reader(self, proc, prefix: str) -> None:
        def reader():
            try:
                for raw in iter(proc.stdout.readline, ""):
                    line = raw.rstrip()
                    if line:
                        LOG.emit(line[:220], "INFO", prefix)
            except Exception:
                pass
        threading.Thread(target=reader, daemon=True, name=f"read-{prefix}").start()

    def _monitor_loop(self) -> None:
        while not self.stop_flag.is_set():
            self._poll_count += 1
            self._poll_once()
            if self._agent_died():
                if not self._handle_agent_death():
                    return
            if self._engine_died():
                if not self._handle_engine_death():
                    return
            self.stop_flag.wait(4.0)

    def _poll_once(self) -> None:
        # WEB
        web = http_get_json(self.cfg.get("server", "").rstrip("/") + "/api/agent", 8.0)
        self.status["web"] = web
        if web is None:
            if self._poll_count % 15 == 1:
                LOG.emit(f"Server web tidak terjangkau: {self.cfg.get('server')}", "WARN")
        elif web.get("tokenConfigured") is False and not self._web_warned:
            self._web_warned = True
            LOG.emit("Server belum mengatur AGENT_TOKEN — agent akan ditolak (503). "
                     "Pasang env AGENT_TOKEN di Vercel dulu.", "WARN")
        # ENGINE
        eng = self._engine_health()
        self.status["engine"] = eng
        # AGENT
        self.status["agent"] = self.agent_proc is not None and self.agent_proc.poll() is None
        # JOB aktif dari status web
        job = None
        if isinstance(web, dict):
            aj = web.get("activeJob")
            if isinstance(aj, dict):
                job = aj
        self.status["job"] = job
        self._push_status()

    def _agent_died(self) -> bool:
        p = self.agent_proc
        return p is not None and p.poll() is not None

    def _handle_agent_death(self) -> bool:
        code = self.agent_proc.poll() or 0
        if self.args.once:
            LOG.emit(f"Agent selesai (--once, kode {code}) — launcher berhenti.", "OK")
            self.stop_sync()
            return False
        if code == 2:
            LOG.emit("Agent BERHENTI: server menolak token (401/503/4xx).", "ERR")
            LOG.emit("Perbaiki token lewat tombol \u201cUbah Token\u201d (nilai = env "
                     "AGENT_TOKEN di server), lalu tekan MULAI lagi.", "ERR")
            self.stop_sync()
            return False
        self._restart_agent += 1
        if self._restart_agent > 3:
            LOG.emit(f"Agent mati berkali-kali (kode {code}) — stack dihentikan.", "ERR")
            self.stop_sync()
            return False
        LOG.emit(f"Agent mati tak terduga (kode {code}) — nyala ulang dalam 5 dtk…", "WARN")
        time.sleep(5.0)
        if self.stop_flag.is_set() or self.state != "running":
            return False
        self._spawn_agent()
        return True

    def _engine_died(self) -> bool:
        p = self.engine_proc
        return self.owns_engine and p is not None and p.poll() is not None

    def _handle_engine_death(self) -> bool:
        code = self.engine_proc.poll() or 0
        self._restart_engine += 1
        if self._restart_engine > 3:
            LOG.emit(f"Engine mati berkali-kali (kode {code}) — berhenti mencoba.", "ERR")
            self.stop_sync()
            return False
        LOG.emit(f"Engine mati (kode {code}) — menyala ulang dalam 3 dtk…", "WARN")
        time.sleep(3.0)
        if self.stop_flag.is_set():
            return False
        if not self._ensure_engine():
            self.stop_sync()
            return False
        return True

    # ---- stop ----

    def stop_async(self) -> None:
        threading.Thread(target=self.stop_sync, daemon=True, name="stopper").start()

    def stop_sync(self) -> None:
        with self._lock:
            if self.state == "stopping":
                return
            prev = self.state
            self._set_state("stopping")
        if prev == "idle":
            self._set_state("idle")
            return
        self.stop_flag.set()
        LOG.emit("Menghentikan engine & agent…", "DIM")
        agent = self.agent_proc
        if agent and agent.poll() is None:
            try:
                agent.terminate()
                agent.wait(timeout=6)
            except Exception:
                try:
                    agent.kill()
                except Exception:
                    pass
        if self.owns_engine:
            eng = self.engine_proc
            if eng and eng.poll() is None:
                try:
                    eng.terminate()
                    eng.wait(timeout=6)
                except Exception:
                    try:
                        eng.kill()
                    except Exception:
                        pass
        self.agent_proc = None
        self.engine_proc = None
        self.status["agent"] = False
        # engine bersama (dipakai ulang) TIDAK kami miliki — biarkan statusnya
        # apa adanya (masih hidup); hanya milik kami yang dinol-kan.
        if self.owns_engine:
            self.status["engine"] = None
        self.owns_engine = False
        self.status["job"] = None
        self._push_status()
        LOG.emit("Berhenti. Sampai jumpa 👋", "OK")
        # reset supaya bisa MULAI lagi
        self.stop_flag = threading.Event()
        self._restart_engine = 0
        self._restart_agent = 0
        self._set_state("idle")


# ------------------------- UI: konsol -------------------------


class ConsoleUI:
    """Tanpa tkinter / tanpa monitor — dashboard di terminal."""

    def __init__(self, cfg, args, controller: StackController):
        self.cfg = cfg
        self.args = args
        self.c = controller
        self._last_line = ""
        self._ever_started = False
        LOG.ui_cb = None
        controller.status_cb = self.on_status
        controller.state_cb = self._on_state

    def _on_state(self, state: str) -> None:
        if state == "starting":
            self._ever_started = True

    def _fmt_status(self, s: dict) -> str:
        web = s.get("web")
        web_txt = "✓" if web else "✗"
        eng = s.get("engine")
        eng_txt = f"✓ {self.c.engine_url}" if eng else "✗"
        ag = "✓" if s.get("agent") else ("✗ " + (s.get("agent_reason") or ""))
        job = s.get("job")
        job_txt = ""
        if isinstance(job, dict) and job.get("status") in ("QUEUED", "RUNNING", "FINALIZING"):
            job_txt = f" · Job {job.get('status')} {job.get('progress', 0)}% — {job.get('message') or ''}"
        return f"WEB {web_txt} · ENGINE {eng_txt} · AGENT {ag}{job_txt}"

    def on_status(self, s: dict) -> None:
        line = self._fmt_status(s)
        if line != self._last_line:
            self._last_line = line
            LOG.emit(line, "DIM")

    def run(self) -> None:
        banner = "=" * 62
        print(banner)
        print(APP_TITLE + " — launcher sekali-klik")
        print(f"  Server : {self.cfg.get('server')}")
        print(f"  Engine : {self.c.engine_url} (dipakai ulang bila sudah jalan)")
        print(f"  Agent  : {AGENT_PATH.relative_to(ROOT)}")
        print("  Tekan Ctrl+C untuk berhenti.")
        print(banner, flush=True)
        if self.cfg.get("autostart") or self.args.once:
            self.c.start_async()
        else:
            LOG.emit("autostart=false — jalankan dengan tombol/flag. "
                     "(Set autostart=true di laptop_config.json untuk sekali-klik.)", "WARN")
        try:
            while True:
                time.sleep(0.5)
                if self.args.once and self._ever_started and self.c.state == "idle":
                    break
        except KeyboardInterrupt:
            print()
            LOG.emit("Ctrl+C diterima — menghentikan…", "WARN")
        finally:
            self.c.stop_sync()
        return 1 if self.c.start_failed else 0


# ------------------------- UI: tkinter -------------------------


class TkApp:
    """Dashboard kecil: status + tombol MULAI/BERHENTI + log langsung."""

    COLOR = {
        "INFO": "#e2e8f0", "OK": "#4ade80", "WARN": "#fbbf24",
        "ERR": "#f87171", "DIM": "#94a3b8",
    }

    def __init__(self, cfg, args, controller: StackController):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.cfg = cfg
        self.args = args
        self.c = controller
        self.q: "queue.Queue" = queue.Queue()

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.minsize(660, 540)
        try:
            self.root.configure(bg="#ffffff")
        except Exception:
            pass

        # Header
        head = tk.Frame(self.root, bg="#0f172a", padx=16, pady=12)
        head.pack(fill="x")
        tk.Label(head, text=APP_TITLE, bg="#0f172a", fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(head, text="Sekali klik: engine FastAPI + agent Python tersambung ke web",
                 bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9)).pack(anchor="w")
        def open_url(_e=None):
            try:
                import webbrowser
                webbrowser.open(str(cfg.get("server")))
            except Exception:
                pass
        url_lbl = tk.Label(head, text=str(cfg.get("server")), bg="#0f172a",
                           fg="#38bdf8", font=("Segoe UI", 9), cursor="hand2")
        url_lbl.pack(anchor="w")
        url_lbl.bind("<Button-1>", open_url)

        # Baris status
        chips = tk.Frame(self.root, bg="#f1f5f9", padx=14, pady=10)
        chips.pack(fill="x")
        self.chip_web = self._chip(chips, "WEB")
        self.chip_engine = self._chip(chips, "ENGINE")
        self.chip_agent = self._chip(chips, "AGENT")
        self.info_var = tk.StringVar(value="Belum berjalan — klik MULAI.")
        tk.Label(chips, textvariable=self.info_var, bg="#f1f5f9",
                 fg="#334155", font=("Segoe UI", 9), wraplength=600,
                 justify="left").pack(anchor="w", pady=(6, 0))

        # Tombol utama
        actions = tk.Frame(self.root, bg="#ffffff", padx=14, pady=10)
        actions.pack(fill="x")
        self.btn_main = tk.Button(
            actions, text="▶  MULAI — hubungkan ke web",
            command=self.on_toggle, bg="#16a34a", fg="#ffffff",
            activebackground="#15803d", activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
            padx=14, pady=8,
        )
        self.btn_main.pack(fill="x")
        small = tk.Frame(actions, bg="#ffffff")
        small.pack(fill="x", pady=(8, 0))
        self.btn_web = self._small_btn(small, "Buka Web", self.open_web)
        self.btn_git = self._small_btn(small, "Perbarui GitHub", self.on_git)
        self.btn_token = self._small_btn(small, "Ubah Token", self.on_token)

        # Log
        logwrap = tk.Frame(self.root, bg="#ffffff", padx=14)
        logwrap.pack(fill="both", expand=True, pady=(0, 12))
        self.txt = tk.Text(
            logwrap, bg="#0f172a", fg="#e2e8f0", wrap="word",
            font=("Consolas", 9), relief="flat", height=16,
            insertbackground="#e2e8f0",
        )
        bar = ttk.Scrollbar(logwrap, command=self.txt.yview)
        self.txt.configure(yscrollcommand=bar.set)
        self.txt.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for lvl, col in self.COLOR.items():
            self.txt.tag_configure(lvl, foreground=col)
        self.txt.tag_configure("CHILD", foreground="#cbd5e1")

        # Wiring
        LOG.ui_cb = self._log_q
        controller.status_cb = self._status_q
        controller.state_cb = self._state_q
        self.root.after(150, self._drain)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- widget helpers ----

    def _chip(self, parent, label):
        var = self.tk.StringVar(value=f"● {label}: —")
        lbl = self.tk.Label(parent, textvariable=var, bg="#f1f5f9", fg="#64748b",
                       font=("Segoe UI", 10, "bold"))
        lbl.pack(side="left", padx=(0, 18))
        return var

    def _small_btn(self, parent, text, cmd):
        b = self.tk.Button(parent, text=text, command=cmd, bg="#ffffff",
                      fg="#334155", relief="flat", cursor="hand2",
                      activebackground="#e2e8f0", font=("Segoe UI", 9),
                      highlightthickness=1, highlightbackground="#cbd5e1",
                      highlightcolor="#94a3b8", padx=10, pady=4)
        b.pack(side="left", padx=(0, 8))
        return b

    # ---- queue → UI (thread-safe) ----

    def _log_q(self, ts, prefix, msg, level):
        self.q.put(("log", (ts, prefix, msg, level)))

    def _status_q(self, status):
        self.q.put(("status", status))

    def _state_q(self, state):
        self.q.put(("state", state))

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    ts, prefix, msg, level = payload
                    tag = "CHILD" if prefix in ("ENGINE", "AGENT") else level
                    line = f"[{ts}]{' ' + prefix if prefix else ''} {msg}\n"
                    self.txt.configure(state="normal")
                    self.txt.insert("end", line, tag)
                    # trim agar tidak membengkak
                    if float(self.txt.index("end-1c").split(".")[0]) > 1600:
                        self.txt.delete("1.0", "200.0")
                    self.txt.configure(state="disabled")
                    self.txt.see("end")
                elif kind == "status":
                    self._render_status(payload)
                elif kind == "state":
                    self._render_state(payload)
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            # sinyal saat mainloop — berhenti rapi lewat jalur penutupan jendela
            self.root.after(1, self.on_close)
        self.root.after(150, self._drain)

    # ---- render ----

    def _render_status(self, s):
        web = s.get("web")
        if web is None:
            self.chip_web.set("● WEB: ✗ tidak terjangkau")
        else:
            self.chip_web.set("● WEB: ✓")
        eng = s.get("engine")
        if eng:
            up = eng.get("uptimeSec")
            self.chip_engine.set(f"● ENGINE: ✓ :{self.cfg.get('engine_port')} · nyala {up} dtk")
        else:
            self.chip_engine.set(f"● ENGINE: ✗ :{self.cfg.get('engine_port')}")
        if s.get("agent"):
            self.chip_agent.set("● AGENT: ✓ berjalan")
        else:
            reason = s.get("agent_reason") or ""
            self.chip_agent.set(f"● AGENT: ✗ {reason}" if reason else "● AGENT: ✗")

        info = []
        if isinstance(web, dict):
            if web.get("online"):
                info.append(f"Agent \u201c{web.get('agentName')}\u201d ONLINE di web")
            engweb = web.get("engine") if isinstance(web.get("engine"), dict) else None
            if engweb:
                info.append(f"engine laptop: {engweb.get('engineName')} v{engweb.get('engineVersion')}")
            if web.get("tokenConfigured") is False:
                info.append("⚠ server belum mengatur AGENT_TOKEN")
        job = s.get("job")
        if isinstance(job, dict) and job.get("status") in ("QUEUED", "RUNNING", "FINALIZING"):
            info.append(
                f"Job aktif: {job.get('status')} · {job.get('progress', 0)}% — "
                f"{job.get('message') or ''} ({job.get('bundleName') or ''})"
            )
        self.info_var.set(" · ".join(info) if info else "Semua normal — menunggu kamu mengirim job dari web.")

    def _render_state(self, state):
        if state in ("starting",):
            self.btn_main.configure(
                text="…  MENYIAPKAN (unduh/nyalakan — lihat log)",
                bg="#64748b", activebackground="#475569", state="disabled",
            )
        elif state == "running":
            self.btn_main.configure(
                text="■  BERHENTI (putuskan dari web)",
                bg="#dc2626", activebackground="#b91c1c", state="normal",
            )
        elif state == "stopping":
            self.btn_main.configure(text="…  MENGHENTIKAN", bg="#64748b",
                                    activebackground="#475569", state="disabled")
        else:  # idle
            self.btn_main.configure(
                text="▶  MULAI — hubungkan ke web",
                bg="#16a34a", activebackground="#15803d", state="normal",
            )

    # ---- aksi ----

    def on_toggle(self):
        if self.c.state in ("starting", "running", "stopping"):
            self.c.stop_async()
        else:
            self.c.start_async()

    def open_web(self):
        try:
            import webbrowser
            webbrowser.open(str(self.cfg.get("server")))
        except Exception:
            pass

    def on_git(self):
        if self.c.state in ("starting", "running"):
            self._log_q(now_ts(), "", "Tidak bisa git pull saat berjalan — BERHENTI dulu.", "WARN")
            return
        self._log_q(now_ts(), "", "git pull…", "DIM")
        code, out = run_capture(["git", "-C", str(ROOT), "pull", "--ff-only"], timeout=90)
        for l in [l for l in out.splitlines() if l.strip()][:4]:
            self._log_q(now_ts(), "git", l[:160], "DIM")
        self._log_q(now_ts(), "",
                    "Kode mutakhir." if "Already up to date" in out
                    else ("Kode diperbarui — jalankan MULAI." if code == 0
                          else f"git pull gagal (kode {code})"), "OK" if code == 0 else "ERR")

    def on_token(self):
        self._token_dialog(then_start=False)

    def _token_dialog(self, then_start: bool) -> None:
        tk = self.tk
        win = tk.Toplevel(self.root)
        win.title("Token Agent")
        win.configure(bg="#ffffff", padx=16, pady=14)
        win.grab_set()
        tk.Label(
            win, justify="left", wraplength=430, bg="#ffffff", fg="#334155",
            font=("Segoe UI", 9),
            text=(
                "Tempel TOKEN AGENT — nilainya sama dengan env AGENT_TOKEN yang "
                "dipasang di server web (diberikan pemilik situs / kamu sendiri).\n\n"
                "Token disimpan HANYA di laptop_config.json di laptop ini — "
                "file itu di-gitignore, tidak pernah ikut ke GitHub."
            ),
        ).pack(anchor="w")
        var = tk.StringVar(value=str(self.cfg.get("agent_token") or ""))
        ent = tk.Entry(win, textvariable=var, width=56, font=("Consolas", 10),
                       highlightthickness=1)
        ent.pack(fill="x", pady=(10, 10))
        ent.focus_set()

        def save():
            tok = var.get().strip()
            if tok:
                self.cfg["agent_token"] = tok
                save_config(self.cfg)
                self._log_q(now_ts(), "", "Token tersimpan di laptop_config.json.", "OK")
            win.destroy()
            if then_start and tok:
                self.c.start_async()

        row = tk.Frame(win, bg="#ffffff")
        row.pack(fill="x")
        tk.Button(row, text="Simpan", command=save, bg="#16a34a", fg="#ffffff",
                  relief="flat", font=("Segoe UI", 10, "bold"), padx=14, pady=4,
                  cursor="hand2").pack(side="right")
        win.bind("<Return>", lambda _e: save())

    def on_close(self):
        try:
            self._log_q(now_ts(), "", "Jendela ditutup — menghentikan…", "DIM")
            self.c.stop_sync()
        finally:
            self.root.destroy()

    # ---- loop ----

    def run(self) -> None:
        if self.cfg.get("autostart") or self.args.once:
            if str(self.cfg.get("agent_token") or "").strip():
                self.root.after(400, self.c.start_async)
            else:
                self._log_q(now_ts(), "", "Token agent belum diisi — isi sekali, lalu langsung mulai.", "WARN")
                self.root.after(300, lambda: self._token_dialog(then_start=True))
        else:
            self._log_q(now_ts(), "", "Klik MULAI untuk menghubungkan laptop ke web.", "INFO")
        self.root.mainloop()


# ------------------------- main -------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mulai_laptop.py",
        description="Launcher sekali-klik: engine FastAPI + agent Python di laptop, "
                    "hasil tampil di web Stock Monitoring.",
    )
    p.add_argument("--console", action="store_true",
                   help="paksa mode terminal (tanpa jendela GUI)")
    p.add_argument("--once", action="store_true",
                   help="proses satu job lalu berhenti (berguna untuk uji)")
    p.add_argument("--status", action="store_true",
                   help="cetak status sekali lalu keluar")
    p.add_argument("--no-update", action="store_true",
                   help="jangan git pull saat mulai")
    p.add_argument("--force-venv", action="store_true",
                   help="paksa siapkan .venv-laptop (abaikan Python sistem)")
    p.add_argument("--server", help="override URL web (contoh: http://127.0.0.1:3000)")
    p.add_argument("--token", help="override token agent (satu kali ini)")
    p.add_argument("--port", type=int, help="override port engine (default 3031)")
    p.add_argument("--name", help="override nama agent (tampil di badge web)")
    return p


def apply_overrides(cfg: dict, args) -> dict:
    if args.server:
        cfg["server"] = args.server.rstrip("/")
    if args.token:
        cfg["agent_token"] = args.token
    if args.port:
        cfg["engine_port"] = args.port
    if args.name:
        cfg["agent_name"] = args.name
    return cfg


def main() -> int:
    args = build_parser().parse_args()

    # SIGTERM (mis. tombol stop / timeout) → alur berhenti yang sama dengan Ctrl+C
    try:
        import signal as _signal

        def _on_sigterm(_sig, _frm):
            raise KeyboardInterrupt()
        _signal.signal(_signal.SIGTERM, _on_sigterm)
    except Exception:
        pass

    cfg = load_config()

    # pertama kali → tulis config contoh + pastikan gitignore melindunginya
    if not CONFIG_PATH.exists():
        save_config(cfg)
    if not gitignore_has_entry("laptop_config.json"):
        gi = ROOT / ".gitignore"
        try:
            with open(gi, "a", encoding="utf-8") as f:
                f.write("\n# Launcher sekali-klik (Task 52) — token TIDAK ikut ke GitHub\n"
                        "/laptop_config.json\n/.venv-laptop/\n")
        except Exception:
            pass

    cfg = apply_overrides(cfg, args)
    controller = StackController(cfg, args)

    # mode --status: sekali poll, cetak, keluar (tanpa menjalankan apa pun)
    if args.status:
        controller._poll_once()
        s = controller.status
        web = s.get("web")
        eng = s.get("engine")
        print(f"WEB    : {'✓ ' + str(web.get('server') or cfg['server']) if web else '✗ tidak terjangkau'}")
        if web:
            print(f"         agent online: {web.get('online')} · nama: {web.get('agentName')} · "
                  f"tokenConfigured: {web.get('tokenConfigured')}")
        print(f"ENGINE : {'✓ ' + controller.engine_url + ' · ' + str(eng.get('engineName')) if eng else '✗ ' + controller.engine_url}")
        print(f"AGENT  : {'belum berjalan (launcher idle)' if not s.get('agent') else 'berjalan'}")
        return 0

    use_gui = not args.console
    if use_gui:
        try:
            import tkinter  # noqa: F401
            app = TkApp(cfg, args, controller)
        except Exception as e:
            LOG.emit(f"GUI tidak tersedia ({e}) — beralih ke mode terminal.", "WARN")
            use_gui = False
    if use_gui:
        app.run()
    else:
        # konsol: token interaktif bila kosong + autostart
        if not str(cfg.get("agent_token") or "").strip():
            print("Token agent belum diisi (nilai env AGENT_TOKEN di server).")
            try:
                tok = input("Tempel token lalu Enter (kosong = batal): ").strip()
            except (EOFError, OSError):
                tok = ""
            if tok:
                cfg["agent_token"] = tok
                save_config(cfg)
            else:
                print("Tanpa token agent tidak bisa tersambung. "
                      "Edit laptop_config.json lalu jalankan lagi.")
                return 2
        return ConsoleUI(cfg, args, controller).run()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nDihentikan.")
        sys.exit(130)
