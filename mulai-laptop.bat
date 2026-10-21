@echo off
setlocal
title Stock Monitoring - Python di Laptop
rem ============================================================
rem  SEKALI KLIK - engine FastAPI + agent Python di laptop
rem  terhubung otomatis ke web Stock Monitoring.
rem  Panduan lengkap: docs\AGENT-LOCAL.md
rem ============================================================

cd /d "%~dp0"
set PYTHONUTF8=1

set PY=
py -3 -c "import sys" >nul 2>nul && set PY=py -3
if not defined PY (
  python -c "import sys" >nul 2>nul && set PY=python
)
if not defined PY (
  echo.
  echo  [!] Python belum terpasang di laptop ini.
  echo      Unduh gratis dari https://www.python.org/downloads/
  echo      Saat menginstal: CENTANG "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

%PY% mulai_laptop.py %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo  Launcher berhenti dengan kode %EXITCODE%.
  echo  Baca pesan di atas untuk penyebabnya.
  pause
)
exit /b %EXITCODE%
