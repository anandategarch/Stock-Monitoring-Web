"""
config.py — Load konfigurasi dari config.json.
Menggantikan record Config di Power Query M code.
Path bisa diubah user tanpa mengubah kode.

v3.9.20 (deep audit 34-d/fix 35-d): setdefault
Sheets["Pemindahan4205Lalu"] (default = nilai sheet berjalan — config
lama tanpa key tetap jalan tanpa KeyError).

v3.9.33 — AUDIT FIX (48-f): validasi ramah — config.json valid-JSON
tapi KURANG key wajib dulu melempar KeyError mentah (English,
membingungkan user). Sekarang: RuntimeError pesan Indonesia yang
menyebut HANYA key yang benar-benar hilang + instruksi perbaikan
(app.py on_error menampilkan pesan ini ke user).

v3.9.42 — AUDIT FIX (61-a):
- F8: JSONDecodeError (config.json rusak — koma kelebihan dsb.) dulu
  melempar pesan Inggris mentah ke user; kini RuntimeError pesan
  Indonesia + instruksi (app.py on_error menampilkan dialog ramah).
- F1: 'KategoriBarang4217' di-validasi TIPE-nya — user salah tulis
  STRING (bukan daftar) dulu lolos ke fn_4217 → iterasi PER-KARAKTER
  → prefix-match 1 karakter → hampir semua kategori lolos whitelist
  (kelas bug item 100383, v3.9.41). Sekarang: bukan daftar-string →
  PERINGATAN + pakai default bawaan.
"""
import json
import os
import sys
from pathlib import Path


def app_base_dir() -> Path:
    """v3.9.62 — base direktori aplikasi (FROZEN-AWARE, PyInstaller).

    - Mode dev : root proyek (parent dari ``src/``).
    - Mode frozen (PyInstaller onedir): folder tempat .exe berada —
      config.json / settings.json / followup.json / crash.log hidup
      BERSAMA .exe (bukan di _MEIPASS/_internal yang temporer — file
      runtime HARUS editable/tahan-update).

    Dipakai semua jalur file runtime: app.py (CONFIG_PATH/_SETTINGS_PATH),
    followup.py (followup.json), deviasi_view (settings ACR), dan
    default Config ini — satu sumber kebenaran lintas modul."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


class Config:
    """Konfigurasi yang dimuat dari config.json. Mirror persis record Config di M code."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # v3.9.62 — app_base_dir() (frozen-aware): mode dev = root
            # proyek; mode PyInstaller = folder .exe (config.json
            # dibundel build_exe.py ke samping exe).
            config_path = app_base_dir() / "config.json"

        # v3.9.42 — AUDIT FIX (61-a, F8): JSON rusak (mis. koma kelebihan)
        # dulu melempar json.JSONDecodeError mentah berbahasa Inggris —
        # user bingung tak tahu harus apa. RuntimeError pesan Indonesia
        # (sudah ditangani app.py on_error → dialog ramah).
        # v3.9.59 — FIX 2f-02/2f-03 (audit 2-f): instruksi lama mengarah ke
        # 'tab ⚙ Pengaturan' yang TIDAK ADA (tab asli '⚙️ Config') dan
        # menyuruh menghapus file demi 'regenerasi otomatis' yang TIDAK
        # terjadi (app justru MENOLAK jalan tanpa config.json — app.py
        # preflight). Pesan kini jujur: perbaiki manual dgn editor teks.
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "config.json rusak (JSON tidak valid): " + str(e)
                + " — perbaiki dengan editor teks (mis. koma kelebihan). "
                "JANGAN hapus file: app tidak meregenerasi config.json — "
                "tanpa file ini app menolak jalan (salin ulang contoh "
                "dari paket SETUP bila file hilang)."
            ) from e

        # v3.9.33 — AUDIT FIX (48-f): key wajib hilang → pesan ramah
        # (bukan KeyError mentah). Sebut HANYA key yang benar-benar
        # hilang; data bukan dict (mis. list) → semua key dianggap
        # hilang. app.py on_error menampilkan pesan ini.
        _wajib_hilang = [k for k in ("RootPath", "Folders", "Sheets")
                         if not isinstance(data, dict) or k not in data]
        if _wajib_hilang:
            # v3.9.59 — FIX 2f-02: rujukan tab dulu '⚙ Pengaturan' (tab itu
            # tidak ada — yang asli '⚙️ Config' app.py, dan tab itu HANYA
            # bisa mengubah RootPath). Kini: key hilang → edit manual di
            # config.json (RootPath saja yang bisa via tab ⚙️ Config).
            raise RuntimeError(
                "config.json tidak lengkap — key berikut hilang: "
                + ", ".join(_wajib_hilang)
                + ". Tambahkan key itu dengan editor teks di config.json "
                "(contoh isi: README / paket SETUP). Catatan: tab ⚙️ Config "
                "hanya bisa mengubah RootPath — Folders/Sheets diedit "
                "langsung di config.json.")

        self.RootPath = data["RootPath"]
        # v3.5: LightMode DIHAPUS — pipeline selalu mode FULL
        # (SO bulan lalu tanggal -25..-31 selalu terbaca). Key "LightMode"
        # lama di config.json diabaikan dengan aman.
        # FIX 6f-04 (audit 6-f): blok Folders/Sheets yang bukan objek
        # dict (salah tulis list/string saat edit manual config.json)
        # dulu melempar AttributeError/TypeError Inggris mentah dari
        # setdefault di bawah — pesan ramah pola v3.9.33.
        for _blok in ("Folders", "Sheets"):
            if not hasattr(data[_blok], "keys"):
                # v3.9.59 — FIX 2f-02/2f-03: pesan jujur (tab ⚙️ Config
                # hanya RootPath; tidak ada regenerasi otomatis).
                raise RuntimeError(
                    "config.json salah format — key '" + _blok + "' "
                    "harus objek {\"key\": \"nilai\"}, bukan "
                    + type(data[_blok]).__name__
                    + ". Perbaiki langsung di config.json dengan editor "
                    "teks (tab ⚙️ Config hanya mengubah RootPath).")
        self.Folders = data["Folders"]
        # v3.9.17: key baru di-DEFAULT (config lokal pra-v3.9.17 yang belum
        # memuat 'Pemindahan4205Lalu' — mis. hasil git pull dgn config
        # ter-modifikasi — tetap jalan tanpa KeyError; nama folder kanonis).
        self.Folders.setdefault("Pemindahan4205Lalu",
                                "4.1 4205 Bulan Lalu")
        self.Sheets = data["Sheets"]
        # FIX R-3 (audit 34-d): key sheet khusus folder 42.05 bulan lalu —
        # di-default ke nilai sheet berjalan (pola 32.24: nama sheet sama utk
        # folder berjalan & lalu; config lama tanpa key tetap aman — tidak
        # KeyError; default in-memory, mirror pola Folders di atas).
        self.Sheets.setdefault(
            "Pemindahan4205Lalu",
            self.Sheets.get("Pemindahan4205",
                            "#42.05. Rincian Pemindahan Bara"))

        # v3.9.32 — HARGA 41.09 (folder '09.Harga', alamat bisa diubah di
        # config.json; sheet default = '#41.09. Nilai Persediaan [ALL]').
        # Config lama tanpa key tetap jalan (default in-memory).
        self.Folders.setdefault("Harga", "09.Harga")
        self.Sheets.setdefault("Harga", "#41.09. Nilai Persediaan [ALL]")

        # v3.9.32 — WHITELIST KATEGORI BARANG 42.17 (filter lebih awal,
        # user: "filter data 42.17 pakai kolom kategori barang [whitelist
        # 5 kategori]"). List BISA DIUBAH user di config.json key
        # "KategoriBarang4217" (prefix-match + case/whitespace-insensitive;
        # [] atau key hilang → tanpa filter; file tanpa kolom kategori →
        # tanpa filter + warning log).
        from src.pipeline.fn_4217 import DEFAULT_KATEGORI_WHITELIST
        # v3.9.42 — AUDIT FIX (61-a, F1): validasi TIPE whitelist — user
        # salah tulis STRING (bukan daftar) di config.json dulu diteruskan
        # apa adanya → fn_4217 mengiterasinya PER-KARAKTER → prefix-match
        # 1 karakter → hampir semua kategori lolos (kelas bug item 100383).
        # Bukan daftar-string → PERINGATAN + default bawaan (copy, supaya
        # mutasi pemanggil tidak menjinak konstanta modul fn_4217).
        _wl = data.get("KategoriBarang4217", DEFAULT_KATEGORI_WHITELIST)
        if not isinstance(_wl, list) or not all(isinstance(x, str) for x in _wl):
            # v3.9.59 — FIX 2f-02 (konsisten): rujukan tempat perbaikan =
            # config.json (key ini tidak bisa diedit dari tab ⚙️ Config).
            print("[PERINGATAN] config 'KategoriBarang4217' harus daftar string — "
                  "memakai default bawaan (edit key ini di config.json)")
            _wl = list(DEFAULT_KATEGORI_WHITELIST)
        self.KategoriBarang4217 = _wl

    # --- Helper: gabungkan RootPath + subfolder ---
    def folder(self, key: str) -> str:
        """Return full path untuk folder key (e.g., 'RekapBerjalan')."""
        # FIX 6f-04 (audit 6-f): sub-key Folders hilang (config.json
        # diedit manual — blok Folders diketik ulang) dulu melempar
        # KeyError Inggris mentah dari pipeline. Pesan ramah Indonesia
        # pola v3.9.33 _wajib_hilang: sebut key + blok + petunjuk
        # (app.py on_error menampilkan pesan ini ke user).
        try:
            sub = self.Folders[key]
        except (KeyError, TypeError):
            # v3.9.59 — FIX 2f-02/2f-03: arahkan ke config.json (bukan tab
            # 'Pengaturan' yang tak ada; hapus file tidak meregenerasi).
            raise RuntimeError(
                f"config.json tidak lengkap — key folder '{key}' tidak ada "
                "di blok 'Folders' (diedit manual?). Tambahkan key itu "
                "dengan editor teks di config.json — tab ⚙️ Config hanya "
                "mengubah RootPath."
            ) from None
        return os.path.join(self.RootPath, sub)

    def sheet(self, key: str) -> str:
        """Return sheet name untuk key (e.g., 'Penjualan2205')."""
        # FIX 6f-04 (audit 6-f): mirror folder() — sub-key Sheets hilang
        # → RuntimeError pesan Indonesia (bukan KeyError mentah).
        try:
            nama = self.Sheets[key]
        except (KeyError, TypeError):
            # v3.9.59 — FIX 2f-02/2f-03: mirror folder() — pesan jujur.
            raise RuntimeError(
                f"config.json tidak lengkap — key sheet '{key}' tidak ada "
                "di blok 'Sheets' (diedit manual?). Tambahkan key itu "
                "dengan editor teks di config.json — tab ⚙️ Config hanya "
                "mengubah RootPath."
            ) from None
        return nama
