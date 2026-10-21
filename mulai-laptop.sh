#!/bin/bash
# ============================================================
#  SEKALI KLIK (Linux) — jalankan ./mulai-laptop.sh
#  Engine FastAPI + agent Python di laptop terhubung otomatis
#  ke web Stock Monitoring. Panduan: docs/AGENT-LOCAL.md
# ============================================================
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] python3 tidak ditemukan. Instal dengan manajer paket distro Anda (mis. sudo apt install python3 python3-venv python3-pip)."
  exit 1
fi

exec python3 mulai_laptop.py "$@"
