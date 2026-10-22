import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { METRICS, type MetricKey } from "@/lib/types";
import {
  isKategoriGabungan,
  matchKategoriValue,
  PIVOT_KATEGORI_ALL,
  PIVOT_KATEGORI_GABUNGAN,
  PIVOT_KATEGORI_REKAP,
  type PivotMatrixItem,
  type PivotMatrixMetric,
  type PivotMatrixResponse,
} from "@/lib/pivot-def";

// Task 55-b — GET /api/snapshots/[id]/pivot REWRITE: struktur PERSIS aplikasi
// desktop v3.9.71 (pivot_view.py). Baris PARENT = nama barang, SUB-BARIS =
// 10 metrik JENIS, kolom = SEMUA RESTO (mode=resto, default — mirror 🏪)
// atau HARI from..to (mode=tanggal — mirror 📅). COM hanya mode tanggal dan
// DIHITUNG di sini (port _compute_com pivot_view.py:1542-1592 VERBATIM).
// INV-1: sel null = tidak ada baris sama sekali — TIDAK dinolkan (0 ≠ null).
// TANPA kolom Total (desktop memang tanpa Total — pivot_view.py:43).

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 60;

type Ctx = { params: Promise<{ id: string }> };

// Kolom SnapshotRow yang diambil — SEMUA kolom qty metrik (Float? — null = missing INV-1).
const ROW_SELECT = {
  itemName: true,
  satuan: true,
  kategori: true,
  isGR: true,
  restoCode: true,
  day: true,
  qtySaldoAwal: true,
  qtySO: true,
  qtySaldoAkhir: true,
  qtyDeviasi: true,
  qtyIN: true,
  qtyBarangMasuk: true,
  qtyCOM: true,
  qtySelisihIN: true,
  qtyBarangKeluar: true,
  qtyACR: true,
} as const;

type PivotRowData = {
  itemName: string;
  satuan: string;
  kategori: string;
  isGR: boolean;
  restoCode: string;
  day: number;
} & Record<MetricKey, number | null>;

const METRIC_KEYS: MetricKey[] = METRICS.map((m) => m.key);

// Akumulasi sel per barang: kunci "metric|kolom" → { sum, has }.
// has=false ⇒ tidak ada nilai sama sekali → sel null (INV-1); "ada baris
// tapi null" TIDAK menambah sum → tetap null (0 vs null dibedakan).
interface CellAcc {
  sum: number;
  has: boolean;
}

interface ItemAcc {
  satuan: string;
  kategori: string;
  isGR: boolean;
  cells: Map<string, CellAcc>;
  /** Ada baris dalam rentang tampilan (desktop: barang tanpa baris di
   *  rentang memang tidak muncul di pivot sama sekali). */
  inRange: boolean;
}

/** Ambil/validasi param hari: clamp 1..dayCount (default = web lama 26 /
 *  akhir bulan — desktop -31..31 v3.8 tak mungkin: snapshot web hanya
 *  memuat bulan berjalan, hari 1..dayCount). */
function clampDay(raw: string | null, fallback: number, lo: number, hi: number): number {
  const n = Number(raw);
  const base = raw !== null && raw !== "" && Number.isFinite(n) ? Math.round(n) : fallback;
  return Math.min(Math.max(base, lo), hi);
}

const normKategori = (v: string) => v.trim().toUpperCase();

/**
 * PORT VERBATIM _compute_com (pivot_view.py:1542-1592) — 6.PEMAKAIAN (COM)
 * per tanggal: com(t) = base + IN(t) − BK(t) − SO(t).
 * base: t=1 → SALDO AWAL pasangan bila ada baris SA (fallback 0); selain
 * itu SO(t−1) (fallback 0 di tepi kiri rantai). Dipanggil atas rantai
 * tanggal 1..to PENUH lalu tampilan mengambil slice [from..to] — mirror
 * FIX 6c-01 desktop (com_full → reindex col_keys): SO(t−1)/SA di luar
 * rentang tampilan tetap dipakai supaya COM kolom pertama tidak minus palsu.
 * NB: desktop memakai series "4.IN" untuk suku masuk (bm = get_series("4.IN")).
 */
function computeComSeries(acc: ItemAcc, tanggals: number[]): Map<number, number> {
  // Nilai metrik per hari — missing → 0 (mirror pivot.get(t, 0) or 0).
  const num = (mk: MetricKey, t: number): number => {
    const c = acc.cells.get(`${mk}|d${t}`);
    return c && c.has ? c.sum : 0;
  };
  const so = (t: number) => num("qtySO", t);
  const bmIn = (t: number) => num("qtyIN", t);
  const bk = (t: number) => num("qtyBarangKeluar", t);

  // SALDO AWAL pasangan di hari 1 (None/NaN = tidak ada baris SA).
  const saT1 = acc.cells.get("qtySaldoAwal|d1");
  const hasSaT1 = saT1 !== undefined && saT1.has;
  const saT1Val = hasSaT1 && saT1 ? saT1.sum : 0;

  const out = new Map<number, number>();
  tanggals.forEach((t, i) => {
    const soVal = so(t);
    const bmVal = bmIn(t);
    const bkVal = bk(t);
    let base: number;
    if (t === 1 && hasSaT1) {
      base = saT1Val; // tanggal 1 → base SALDO AWAL pasangan (audit fix v3.9.5)
    } else if (i === 0) {
      base = 0; // tepi kiri rantai tanpa konteks
    } else {
      base = so(tanggals[i - 1]); // SO hari sebelumnya
    }
    out.set(t, base + bmVal - bkVal - soVal);
  });
  return out;
}

export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) {
    return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });
  }

  const sp = req.nextUrl.searchParams;
  const mode = sp.get("mode") === "tanggal" ? "tanggal" : "resto";
  const dayCount = snapshot.dayCount;
  const hideEmpty = sp.get("hideEmpty") !== "0"; // default 1 (desktop ON)

  if (dayCount <= 0) {
    const resp: PivotMatrixResponse = {
      mode,
      columns: [],
      items: [],
      from: 0,
      to: 0,
      dayCount,
      totalItems: 0,
      hiddenEmptyRows: 0,
      kategoriOptions: [PIVOT_KATEGORI_ALL],
    };
    return NextResponse.json(resp);
  }

  // Rentang hari: clamp 1..dayCount; terbalik → tukar (mirror 2c-04 desktop).
  let from = clampDay(sp.get("from"), 26, 1, dayCount);
  let to = clampDay(sp.get("to"), dayCount, 1, dayCount);
  if (from > to) {
    const t = from;
    from = to;
    to = t;
  }

  const restoParam = (sp.get("resto") ?? "").trim();
  if (mode === "tanggal" && !restoParam) {
    return NextResponse.json(
      { error: "Parameter resto wajib untuk mode=tanggal (satu resto per matriks)." },
      { status: 422 },
    );
  }

  // Opsi KATEGORI + kolom resto: distinct atas snapshot PENUH (desktop
  // mengisi combo dari data utuh, bukan hasil filter — _populate_filters).
  const [kategoriGroups, restoGroups] = await Promise.all([
    db.snapshotRow.groupBy({ by: ["kategori"], where: { snapshotId: id } }),
    mode === "resto"
      ? db.snapshotRow.groupBy({ by: ["restoCode"], where: { snapshotId: id } })
      : Promise.resolve([] as { restoCode: string }[]),
  ]);
  const distinctKategori = kategoriGroups.map((g) => g.kategori).sort();
  // Entry gabungan hanya bila data memuat nilai rekap (kategori_has_default_values).
  const hasRekap = distinctKategori.some(
    (v) =>
      normKategori(v) === PIVOT_KATEGORI_REKAP[0].toUpperCase() ||
      normKategori(v) === PIVOT_KATEGORI_REKAP[1].toUpperCase(),
  );
  const kategoriOptions = [
    PIVOT_KATEGORI_ALL,
    ...(hasRekap ? [PIVOT_KATEGORI_GABUNGAN] : []),
    ...distinctKategori,
  ];

  // Filter kategori → himpunan nilai yang cocok (finite: dari distinct saja).
  // Seleksi yang tak ada di snapshot → tanpa filter (mirror reset combo saat
  // reload data, v3.9.33). Entri gabungan pada data tanpa rekap → tanpa
  // filter (mirror _default_kategori_value → fallback "(All)").
  const selKategori = (sp.get("kategori") ?? "").trim();
  let kategoriFilter: string[] | null = null;
  if (selKategori && selKategori !== PIVOT_KATEGORI_ALL && selKategori !== "(All)") {
    if (isKategoriGabungan(selKategori)) {
      kategoriFilter = hasRekap
        ? distinctKategori.filter((v) => matchKategoriValue(v, selKategori))
        : null;
    } else {
      const matched = distinctKategori.filter((v) => matchKategoriValue(v, selKategori));
      kategoriFilter = matched.length > 0 ? matched : null;
    }
  }

  // Data matrix — SATU findMany per request, agregasi in-memory (88k baris
  // aman < 60 dtk). Mode tanggal memuat hari 1..to (rantai COM butuh SO(t−1)
  // dan SA hari 1 di luar rentang tampilan); mode resto cukup hari dalam
  // rentang (COM tidak dihitung di mode resto).
  const rows = (await db.snapshotRow.findMany({
    where: {
      snapshotId: id,
      ...(mode === "tanggal"
        ? { restoCode: restoParam, day: { lte: to } }
        : { day: { gte: from, lte: to } }),
      ...(kategoriFilter ? { kategori: { in: kategoriFilter } } : {}),
    },
    select: ROW_SELECT,
  })) as PivotRowData[];

  // ---- Agregasi in-memory ----
  const items = new Map<string, ItemAcc>();
  for (const r of rows) {
    let acc = items.get(r.itemName);
    if (!acc) {
      acc = {
        satuan: r.satuan,
        kategori: r.kategori,
        isGR: r.isGR,
        cells: new Map(),
        inRange: false,
      };
      items.set(r.itemName, acc);
    }
    const inRange = r.day >= from && r.day <= to; // mode resto: selalu true (filter DB)
    if (inRange) acc.inRange = true;
    if (mode === "resto" && !inRange) continue; // defensif — DB sudah memfilter
    // Kolom sel: mode resto = restoCode (Σ hari dalam rentang, satuan-variant
    // ikut dijumlah — mirror pivot_table index "Nama Barang"×"JENIS");
    // mode tanggal = per hari (hari < from tetap masuk peta → input COM).
    const colKey = mode === "resto" ? r.restoCode : `d${r.day}`;
    for (const mk of METRIC_KEYS) {
      const v = r[mk];
      if (v === null) continue; // INV-1: baris ada tapi null → sel tetap null
      const key = `${mk}|${colKey}`;
      const cell = acc.cells.get(key);
      if (cell) {
        cell.sum += v;
        cell.has = true;
      } else {
        acc.cells.set(key, { sum: v, has: true });
      }
    }
  }

  const cellVal = (acc: ItemAcc, mk: MetricKey, col: string): number | null => {
    const c = acc.cells.get(`${mk}|${col}`);
    return c && c.has ? c.sum : null;
  };

  // Kolom matriks: mode resto = SEMUA resto (label = kode; nama resto di UI
  // dari /restos) — mode tanggal = hari from..to (label = string hari).
  const columns =
    mode === "resto"
      ? restoGroups
          .map((g) => g.restoCode)
          .sort()
          .map((code) => ({ key: code, label: code }))
      : Array.from({ length: to - from + 1 }, (_, i) => ({
          key: `d${from + i}`,
          label: String(from + i),
        }));

  // Rantai COM penuh 1..to (mode tanggal saja) — tampilan memakai slice [from..to].
  const comChainDays = mode === "tanggal" ? Array.from({ length: to }, (_, i) => i + 1) : [];

  // Urutan items: itemName asc (mirror sorted(pivot.index) desktop).
  const sortedNames = [...items.entries()]
    .filter(([, a]) => a.inRange)
    .map(([n]) => n)
    .sort();

  let hiddenEmptyRows = 0;
  const outItems: PivotMatrixItem[] = [];
  for (const name of sortedNames) {
    const acc = items.get(name)!;
    const metrics: PivotMatrixMetric[] = [];
    let allEmpty = true; // untuk hiddenAll saat hideEmpty=0
    for (const m of METRICS) {
      // COM hanya mode tanggal (pivot_view.py:979-982 — metrik harian).
      const active = !(mode === "resto" && m.key === "qtyCOM");
      if (!active) {
        metrics.push({ key: m.key, label: m.label, active: false, values: {} });
        continue;
      }
      const values: Record<string, number | null> = {};
      let hasNonZero = false;
      if (mode === "tanggal" && m.key === "qtyCOM") {
        // Anak COM = DERET hasil _compute_com (slice rentang tampilan).
        const com = computeComSeries(acc, comChainDays);
        for (const c of columns) {
          const t = Number(c.key.slice(1));
          const v = com.get(t) ?? 0;
          values[c.key] = v;
          if (v !== 0) hasNonZero = true;
        }
      } else {
        for (const c of columns) {
          const v = cellVal(acc, m.key, c.key);
          values[c.key] = v;
          if (v !== null && v !== 0) hasNonZero = true;
        }
      }
      // hide-empty v3.9.69: "kosong" = SEMUA sel 0/null — baris minus SEMUA
      // sel-nya ≠ 0 TETAP TAMPIL (sinyal retur/deviasi penting).
      if (hideEmpty && !hasNonZero) {
        hiddenEmptyRows++;
        continue;
      }
      if (hasNonZero) allEmpty = false;
      metrics.push({ key: m.key, label: m.label, active: true, values });
    }
    // Parent barang disembunyikan bila SEMUA anaknya tersembunyi (desktop:1093-1094).
    if (hideEmpty && metrics.every((m) => !m.active)) continue;
    outItems.push({
      itemName: name,
      satuan: acc.satuan,
      kategori: acc.kategori,
      isGR: acc.isGR,
      metrics,
      ...(hideEmpty ? {} : { hiddenAll: allEmpty }),
    });
  }

  const resp: PivotMatrixResponse = {
    mode,
    columns,
    items: outItems,
    from,
    to,
    dayCount,
    totalItems: sortedNames.length,
    hiddenEmptyRows,
    kategoriOptions,
  };
  return NextResponse.json(resp);
}
