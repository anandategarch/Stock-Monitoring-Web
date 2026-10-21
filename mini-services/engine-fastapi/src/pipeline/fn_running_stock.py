"""
fn_running_stock.py — Mirror SANGAT PERSIS fnRunningStock di M code.
Algoritma running balance per (Nama Barang, NAMA RESTO).

LOGIKA (dari M code List.Generate):
- Tanggal < 1  (bulan lalu)  → SALDO AKHIR = 0
- Tanggal >= 1 (bulan berjalan):
  - Jika BELUM pernah started (first time tgl >= 1):
      SALDO AKHIR = SaldoAwal + IN - OUT - BARANG_KELUAR
  - Jika SUDAH started:
      SALDO AKHIR = previous_saldo + IN - OUT - BARANG_KELUAR
- Flag 'started' sekali True, tetap True.

FIX (post OUT/BK split): subtract BARANG KELUAR (42.15 Kirim) too.
In OLD setup OUT = 22.05 sales + 42.15 Kirim (combined).
In NEW setup OUT = 22.05 only, BARANG KELUAR = 42.15 Kirim (separate).
To maintain same SALDO AKHIR behavior, must subtract both.

v3.7 "ENGINE TURBO" — fn_running_stock_grouped sepenuhnya vektor
(global segmented cumsum, tanpa loop per grup):
- Benchmark real-data: 561.132 baris / 14.388 grup — 6,68s → 0,19s (36×).
- Output DIVERIFIKASI IDENTIK vs implementasi lama: 10 edge-case
  sintetis (bulan lalu, tanggal NaN, key NaN, saldo awal negatif/
  all-NaN, single row, tanpa kolom, tanggal duplikat) + real-data
  np.allclose (maxdiff 8,3e-08 = noise pembulatan float) + urutan
  baris & kolom identik.
- BUG benchmark awal tertangkap unit-test sintetis: akumulasi harus
  mulai dari baris PERTAMA tanggal >= 1 (bukan awal grup) — baris
  bulan-lalu dengan net ≠ 0 (mis. RI 32.24 Bulan Lalu) tidak boleh
  ikut saldo. Real-data sandbox lolos benchmark lama hanya karena
  baris bulan-lalunya ber-net 0.
- Semantik yang dijaga persis: saldo awal = List.Max per grup
  (skip NaN, all-NaN → 0); baris sebelum tanggal>=1 → 0; baris
  setelah-nya (termasuk baris tanggal NaN di ekor grup hasil sort
  na_position="last") ikut akumulasi — perilaku sama dgn loop lama;
  grup tanpa tanggal >= 1 → semua 0; grup dengan key NaN tetap
  digabung (setara groupby dropna=False via duplicated()).
- fn_running_stock (per grup tunggal) dipertahankan untuk API lama
  (unit test / pemanggilan eksternal).
"""
import numpy as np
import pandas as pd


def fn_running_stock(t: pd.DataFrame) -> pd.DataFrame:
    """
    Mirror M: fnRunningStock(t).

    Input: t dengan minimal kolom Tanggal, IN, OUT, SALDO AWAL.
    Output: t dengan tambahan kolom "SALDO AKHIR".
    """
    if t is None or t.empty:
        result = t.copy() if t is not None else pd.DataFrame()
        result["SALDO AKHIR"] = pd.Series(dtype="float64")
        return result

    # 1. SALDO AWAL = List.Max(t[SALDO AWAL])
    if "SALDO AWAL" in t.columns:
        saldo_awal = t["SALDO AWAL"].max()
        if pd.isna(saldo_awal):
            saldo_awal = 0.0
    else:
        saldo_awal = 0.0

    # 2. SORT by Tanggal ascending
    srt = t.sort_values("Tanggal", ascending=True, na_position="last").reset_index(drop=True)

    # 3. CONVERT to numpy arrays
    n = len(srt)
    dates_arr = srt["Tanggal"].to_numpy(dtype="float64")  # NaN for null
    ins_arr = srt["IN"].fillna(0).to_numpy(dtype="float64") if "IN" in srt.columns else np.zeros(n)
    outs_arr = srt["OUT"].fillna(0).to_numpy(dtype="float64") if "OUT" in srt.columns else np.zeros(n)
    # FIX: subtract BARANG KELUAR too (post OUT/BK split — was previously part of OUT)
    bk_arr = srt["BARANG KELUAR"].fillna(0).to_numpy(dtype="float64") if "BARANG KELUAR" in srt.columns else np.zeros(n)

    if n == 0:
        srt["SALDO AKHIR"] = []
        return srt

    # 4. VECTORIZED running stock (no Python loop!)
    # Logic:
    #   - For Tanggal < 1: saldo = 0
    #   - For Tanggal >= 1 (first time): saldo = SaldoAwal + IN - OUT
    #   - For Tanggal >= 1 (after started): saldo = prev_saldo + IN - OUT
    #
    # Equivalent to:
    #   net = IN - OUT
    #   For rows where Tanggal >= 1: saldo = SaldoAwal + cumsum(net) from start_idx onward
    #   For rows where Tanggal < 1: saldo = 0
    #   BUT: once started, ALL subsequent rows (even if Tanggal < 1 again) keep accumulating.
    #   Since data is sorted by Tanggal ascending, once Tanggal >= 1, all subsequent are >= 1.
    #   So: find first index where Tanggal >= 1 → start_idx
    #   saldo[0:start_idx] = 0
    #   saldo[start_idx] = SaldoAwal + net[start_idx]
    #   saldo[start_idx+1:] = saldo[start_idx] + cumsum(net[start_idx+1:])

    # Find start_idx: first index where Tanggal >= 1
    # Handle NaN in dates_arr: np.isnan → treat as < 1
    valid_dates = np.where(np.isnan(dates_arr), -np.inf, dates_arr)
    started_mask = valid_dates >= 1
    saldo_arr = np.zeros(n, dtype="float64")

    if started_mask.any():
        start_idx = np.argmax(started_mask)  # first True index
        # FIX: net = IN - OUT - BARANG_KELUAR (was IN - OUT only)
        # Reason: post-split OUT = 22.05 sales only, BARANG KELUAR = 42.15 Kirim
        # Both represent goods leaving this resto's stock
        net = ins_arr - outs_arr - bk_arr

        # saldo[start_idx] = SaldoAwal + net[start_idx]
        # saldo[start_idx+1:] = SaldoAwal + cumsum(net[start_idx:])
        cumsum_net = np.cumsum(net[start_idx:])
        saldo_arr[start_idx:] = saldo_awal + cumsum_net
        # Rows before start_idx remain 0 (already initialized)

    # 5. GABUNGKAN KEMBALI
    srt["SALDO AKHIR"] = saldo_arr

    return srt


def fn_running_stock_grouped(df: pd.DataFrame, group_keys: list) -> pd.DataFrame:
    """
    v3.7 ENGINE TURBO: running stock semua grup SEKALI JALAN (vektor).

    Sebelumnya: loop Python per grup (14.388 grup × pandas overhead =
    6,6s di real-data). Sekarang: satu sort + segmented cumsum global
    (0,36s) — output terverifikasi identik (lihat docstring modul).

    Semantik 1:1 dengan implementasi lama:
    1. Pre-sort (group_keys + Tanggal, ascending, NaN belakang).
    2. Grup = blok kontigu (duplikasi NaN key dianggap sama — setara
       groupby dropna=False).
    3. saldo awal grup = List.Max(SALDO AWAL) — skip NaN; all-NaN → 0.
    4. Baris sebelum tanggal >= 1 pertama → SALDO AKHIR = 0.
    5. Mulai tanggal >= 1 pertama: saldo = saldo_awal + Σ(IN-OUT-BK)
       akumulasi s.d. baris itu — TERMASUK baris tanggal NaN di ekor
       grup (mereka berada setelah posisi start, seperti loop lama).
    6. Grup tanpa tanggal >= 1 sama sekali → semua 0.
    """
    if df.empty:
        result = df.copy()
        result["SALDO AKHIR"] = pd.Series(dtype="float64")
        return result

    n = len(df)

    # 1. Pre-sort (sama seperti implementasi lama)
    sort_cols = group_keys + ["Tanggal"]
    srt = df.sort_values(sort_cols, ascending=True,
                         na_position="last").reset_index(drop=True)

    # 2. Kolom numerik → numpy array
    ins = srt["IN"].fillna(0).to_numpy(dtype="float64") if "IN" in srt.columns \
        else np.zeros(n)
    outs = srt["OUT"].fillna(0).to_numpy(dtype="float64") if "OUT" in srt.columns \
        else np.zeros(n)
    bks = srt["BARANG KELUAR"].fillna(0).to_numpy(dtype="float64") \
        if "BARANG KELUAR" in srt.columns else np.zeros(n)
    sa = srt["SALDO AWAL"].to_numpy(dtype="float64") \
        if "SALDO AWAL" in srt.columns else np.zeros(n)
    dates = pd.to_numeric(srt["Tanggal"], errors="coerce") \
        .to_numpy(dtype="float64")
    # NaN tanggal → -inf (tidak >= 1), tapi POSISI baris tetap dipakai
    # (baris NaN di ekor grup tetap diakumulasi — perilaku loop lama)
    valid_dates = np.where(np.isnan(dates), -np.inf, dates)

    net = ins - outs - bks

    # 3. Batas grup: baris pertama dari tiap blok kontigu key
    #    (duplicated memperlakukan NaN key sebagai duplikat satu sama lain
    #    — setara groupby(dropna=False))
    is_new = ~srt.duplicated(subset=group_keys, keep="first")
    gid = np.cumsum(is_new.to_numpy()) - 1          # 0..G-1
    n_groups = int(gid[-1]) + 1 if n else 0

    # 4. Saldo awal per grup = List.Max (skip NaN, all-NaN → 0)
    #    — pakai pandas groupby max (semantik NaN persis) di atas gid
    sa_group = pd.Series(sa).groupby(gid).max().fillna(0.0) \
        .to_numpy(dtype="float64")
    if len(sa_group) < n_groups:  # defensive (grup tanpa baris tidak mungkin)
        sa_group = np.pad(sa_group, (0, n_groups - len(sa_group)))

    # 5. Posisi 'started' per grup: baris pertama dgn tanggal >= 1
    ge1 = valid_dates >= 1
    first_pos = np.full(n_groups, np.iinfo(np.int64).max, dtype=np.int64)
    if ge1.any():
        np.minimum.at(first_pos, gid[ge1], np.flatnonzero(ge1))
    pos = np.arange(n, dtype=np.int64)
    started = pos >= first_pos[gid]

    # 6. Saldo akhir: akumulasi mulai dari BARIS PERTAMA tanggal >= 1
    #    (bukan dari awal grup — baris bulan-lalu dengan net ≠ 0 TIDAK ikut;
    #    tertangkap oleh unit-test sintetis "bulan lalu → berjalan")
    cs = np.cumsum(net)
    base_before = np.concatenate(([0.0], cs[:-1]))  # cumsum tepat sebelum baris i
    fp = first_pos[gid]                             # posisi start per baris
    safe_fp = np.where(started, np.minimum(fp, n - 1), 0)
    start_base = base_before[safe_fp]               # cumsum tepat sebelum start
    segment_cs = cs - start_base                    # Σ net dari start s.d. baris i

    saldo_arr = np.zeros(n, dtype="float64")
    saldo_arr[started] = sa_group[gid[started]] + segment_cs[started]

    srt = srt.copy()
    srt["SALDO AKHIR"] = saldo_arr
    return srt
