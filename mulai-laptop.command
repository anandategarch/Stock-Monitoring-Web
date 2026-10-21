#!/bin/bash
# ============================================================
#  SEKALI KLIK (macOS) — dobel-klik file ini di Finder.
#  Engine FastAPI + agent Python di laptop terhubung otomatis
#  ke web Stock Monitoring. Panduan: docs/AGENT-LOCAL.md
# ============================================================
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] python3 tidak ditemukan di laptop ini."
  echo "    Instal dari https://www.python.org/downloads/ (atau jalankan: xcode-select --install)."
  read -r -p "Tekan Enter untuk menutup..." _
  exit 1
fi

exec python3 mulai_laptop.py "$@"
