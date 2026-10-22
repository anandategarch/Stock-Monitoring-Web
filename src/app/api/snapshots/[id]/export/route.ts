// ============================================================
// Task 55-c — GET /api/snapshots/[id]/export — Export Excel (.xlsx)
// multi-sheet, parity fitur 💾 "Export Excel" aplikasi desktop.
//
//   ?sheet=all      → workbook 5 sheet (default)
//   ?sheet=pivot    → PIVOT      — matrix mutasi: baris barang × 10 metrik
//                                 (label METRICS @/lib/types), kolom SEMUA resto,
//                                 SUM qty metrik day 1..dayCount (null ≠ 0 → kosong).
//   ?sheet=deviasi  → DEVIASI    — wide-mirror desktop: SO_H±k / In_H±k / Sistem /
//                                 Deviasi / Nominal / Dev to BOM % / Rank / CEK /
//                                 Keterangan Audit (heading H dinamis params.tanggalH).
//   ?sheet=selisih  → SELISIH_IN — rekap Selisih IN per resto (model SelisihInResto).
//   ?sheet=nominal  → NOMINAL    — Σ nominal & Σ qty deviasi per resto + TOTAL.
//   ?sheet=po       → PO         — satu baris per item PO (header include items).
//
// INV-1 dipertahankan: nilai null ditulis sebagai SEL KOSONG, bukan 0.
// Route mandiri & generik — dipakai komponen <ExportButton /> yang dipasang
// integrator di tab-tab analisis (tanpa coupling state tab mana pun).
//
// Penyelarasan kontrak sibling (agar angka export = angka tab):
//   • DEVIASI mengikuti kanon Task 55-d (route /deviasi + deviasi-def.ts):
//     heading dinamis _col_display_name (tanggal 0 → "…_lalu", < 0 → "…_—"),
//     Deviasi = SO_H − (Sistem ?? 0) ala desktop 2058 (SO_H missing → null),
//     Dev to BOM % = |Deviasi| / max(Σ qtyACR pasangan semua hari, ε) × 100
//     (Σ ACR = 0 → null), Rank kelompok itemName+satuan method-min.
//     Redaksi awal task menyebut "Total ACR resto" — diikuti bentuk kanon
//     desktop baris 505 (per pasangan) supaya identik dengan tab Deviasi.
//   • PIVOT mengikuti semantik sel Task 55-b (route /pivot mode resto):
//     agregat { sum, has } — tanpa satu pun nilai → sel kosong (bukan 0).
// ============================================================

import { NextRequest, NextResponse } from "next/server";
import ExcelJS from "exceljs";
import { db } from "@/lib/db";
import { METRICS } from "@/lib/types";
import { parseJsonSafe } from "@/lib/snapshot-service";
import { naturalCompare, rankMinInGroups } from "@/lib/desktop-parity";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 60;

type Ctx = { params: Promise<{ id: string }> };

const SHEET_OPTIONS = ["all", "pivot", "deviasi", "selisih", "nominal", "po"] as const;
type SheetOption = (typeof SHEET_OPTIONS)[number];

// ---- styling minimum berkelas (mirror header export desktop export_sheets.py) ----
const HEAD_FILL = "FFE2E8F0"; // fill abu terang baris header
const MINUS_FONT = "FFCC0000"; // merah nilai minus (desktop: minus merah per-cell)
const NUM_FMT = "#,##0.00";
const EPS = 1e-9; // penjaga pembagian nol untuk Dev to BOM %

// Kunci metrik dari satu sumber kebenaran METRICS (@/lib/types).
type MetricKeyOf = (typeof METRICS)[number]["key"];
const METRIC_KEYS: MetricKeyOf[] = METRICS.map((m) => m.key);

/** Bentuk baris snapshot hasil SATU findMany — dipakai PIVOT/DEVIASI/NOMINAL. */
interface ExportRow {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  day: number;
  qtySaldoAwal: number | null;
  qtySO: number | null;
  qtySaldoAkhir: number | null;
  qtyDeviasi: number | null;
  qtyIN: number | null;
  qtyBarangMasuk: number | null;
  qtyCOM: number | null;
  qtySelisihIN: number | null;
  qtyBarangKeluar: number | null;
  qtyACR: number | null;
  hargaEfektif: number | null;
  nominal: number | null;
  cekJson: string;
  auditNote: string | null;
}

// ------------------------------------------------------------
// Util styling bersama
// ------------------------------------------------------------

/** Header baris 1: bold + fill abu terang. */
function styleHeaderRow(ws: ExcelJS.Worksheet): void {
  ws.getRow(1).eachCell((cell) => {
    cell.font = { bold: true };
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: HEAD_FILL } };
  });
}

/** Freeze pane baris 1 agar header tetap terlihat saat scroll. */
function freezeHeaderRow(ws: ExcelJS.Worksheet): void {
  ws.views = [{ state: "frozen", ySplit: 1 }];
}

/** Aproksimasi panjang teks sel untuk auto width. */
function cellTextLength(cell: ExcelJS.Cell): number {
  const v = cell.value;
  if (typeof v === "number") return v.toFixed(2).length;
  if (typeof v === "string") return v.length;
  return 0;
}

/** Auto width sederhana: max panjang teks per kolom, clamp 6..40. */
function applyAutoWidth(ws: ExcelJS.Worksheet): void {
  const maxes: number[] = [];
  ws.eachRow((row) => {
    row.eachCell({ includeEmpty: false }, (cell, colNumber) => {
      maxes[colNumber] = Math.max(maxes[colNumber] ?? 0, cellTextLength(cell));
    });
  });
  for (let c = 1; c < maxes.length; c++) {
    ws.getColumn(c).width = Math.min(Math.max((maxes[c] ?? 0) + 2, 6), 40);
  }
}

/** Sel numerik: null → sel kosong (INV-1), minus → font merah. */
function setNumCell(ws: ExcelJS.Worksheet, rowIdx: number, colIdx: number, v: number | null): void {
  if (v === null) return;
  const cell = ws.getCell(rowIdx, colIdx);
  cell.value = v;
  cell.numFmt = NUM_FMT;
  if (v < 0) cell.font = { color: { argb: MINUS_FONT } };
}

/** Sel integer (Rank/Skor/dll) tanpa format desimal; minus tetap merah. */
function setIntCell(ws: ExcelJS.Worksheet, rowIdx: number, colIdx: number, v: number | null): void {
  if (v === null) return;
  const cell = ws.getCell(rowIdx, colIdx);
  cell.value = v;
  if (v < 0) cell.font = { color: { argb: MINUS_FONT } };
}

/** Penutup sheet: baris "Tidak ada data" bila kosong + styling standar. */
function finishSheet(ws: ExcelJS.Worksheet, hasData: boolean): void {
  if (!hasData) {
    const note = ws.getCell(2, 1);
    note.value = "Tidak ada data";
    note.font = { italic: true, color: { argb: "FF94A3B8" } };
  }
  styleHeaderRow(ws);
  freezeHeaderRow(ws);
  applyAutoWidth(ws);
}

// ------------------------------------------------------------
// Sheet 1 — PIVOT (mirror desktop 🏪 mode resto)
// ------------------------------------------------------------

interface PivotAgg {
  sum: number;
  has: boolean;
}

interface PivotItem {
  itemName: string;
  satuan: string;
  kategori: string;
  /** restoCode → metrik → agregat SUM (null ≠ 0: tanpa satu pun nilai → sel kosong). */
  cells: Map<string, Map<MetricKeyOf, PivotAgg>>;
}

function buildPivotSheet(wb: ExcelJS.Workbook, rows: readonly ExportRow[]): void {
  const ws = wb.addWorksheet("PIVOT");

  // Agregasi in-memory atas SATU query: per (barang|satuan) × resto × 10 metrik,
  // SUM qtyMetrik day 1..dayCount. 88 ribu baris aman — murni Map + loop.
  const items = new Map<string, PivotItem>();
  const restoCodes = new Set<string>();
  for (const r of rows) {
    restoCodes.add(r.restoCode);
    const itemKey = `${r.itemName}|${r.satuan}`;
    let item = items.get(itemKey);
    if (!item) {
      item = { itemName: r.itemName, satuan: r.satuan, kategori: r.kategori, cells: new Map() };
      items.set(itemKey, item);
    }
    let byMetric = item.cells.get(r.restoCode);
    if (!byMetric) {
      byMetric = new Map();
      item.cells.set(r.restoCode, byMetric);
    }
    for (const key of METRIC_KEYS) {
      const v = r[key];
      if (v === null) continue; // missing ≠ 0
      let agg = byMetric.get(key);
      if (!agg) {
        agg = { sum: 0, has: false };
        byMetric.set(key, agg);
      }
      agg.sum += v;
      agg.has = true;
    }
  }

  const restoCols = [...restoCodes].sort();
  ws.addRow(["Nama Barang", "Metrik", "Satuan", "Kategori", ...restoCols]);

  const sortedItems = [...items.values()].sort(
    (a, b) => naturalCompare(a.itemName, b.itemName) || a.satuan.localeCompare(b.satuan),
  );

  let rowIdx = 2;
  for (const item of sortedItems) {
    for (const m of METRICS) {
      // Sub-baris metrik: nama barang (parent, bold) kolom 1 + metrik kolom 2.
      const nameCell = ws.getCell(rowIdx, 1);
      nameCell.value = item.itemName;
      nameCell.font = { bold: true };
      ws.getCell(rowIdx, 2).value = m.label;
      ws.getCell(rowIdx, 3).value = item.satuan;
      ws.getCell(rowIdx, 4).value = item.kategori;
      let colIdx = 5;
      for (const rc of restoCols) {
        const agg = item.cells.get(rc)?.get(m.key);
        setNumCell(ws, rowIdx, colIdx, agg && agg.has ? agg.sum : null);
        colIdx += 1;
      }
      rowIdx += 1;
    }
  }
  finishSheet(ws, rows.length > 0);
}

// ------------------------------------------------------------
// Sheet 2 — DEVIASI (mirror desktop, heading H dinamis)
// ------------------------------------------------------------

/**
 * Heading dinamis ala desktop _col_display_name (deviasi_view.py:1565-1586,
 * sama dengan route 55-d): H=14 → "SO_12", "In_14", dst; tanggal 0 → "…_lalu"
 * (penutupan bulan lalu); tanggal < 0 → "…_—" (tak pernah ada datanya).
 */
function colDisplayName(prefix: "SO" | "In", date: number): string {
  if (date === 0) return `${prefix}_lalu`;
  if (date < 0) return `${prefix}_\u2014`;
  return `${prefix}_${date}`;
}

interface DevRow {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  byDay: Map<number, ExportRow>;
  /** Σ qtyACR pasangan SEMUA hari — penyebut Dev to BOM % (kanon 55-d). */
  acrTotal: number;
  deviasi: number | null; // SO_H − (Sistem ?? 0); SO_H missing → null
  nominal: number | null; // hargaEfektif@H × Deviasi
}

function buildDeviasiSheet(wb: ExcelJS.Workbook, rows: readonly ExportRow[], h: number): void {
  const ws = wb.addWorksheet("DEVIASI");

  // Heading H dinamis — pola SO_H±k / In_H±k (H=14 → "SO_13", "In_14", dst).
  ws.addRow([
    "Resto", "Nama Barang", "Satuan", "Kategori",
    colDisplayName("SO", h - 2), colDisplayName("SO", h - 1), colDisplayName("In", h - 1),
    colDisplayName("SO", h), colDisplayName("In", h),
    colDisplayName("SO", h + 1), colDisplayName("SO", h + 2),
    "Sistem", "Deviasi", "Nominal", "Dev to BOM %", "Rank", "CEK", "Keterangan Audit",
  ]);

  // Pasangan (resto, item, satuan) + baris per hari + Σ ACR pasangan.
  const pairs = new Map<string, DevRow>();
  for (const r of rows) {
    const key = `${r.restoCode}|${r.itemName}|${r.satuan}`;
    let p = pairs.get(key);
    if (!p) {
      p = {
        restoCode: r.restoCode, restoName: r.restoName, itemName: r.itemName,
        satuan: r.satuan, kategori: r.kategori, byDay: new Map(),
        acrTotal: 0, deviasi: null, nominal: null,
      };
      pairs.set(key, p);
    }
    if (r.qtyACR !== null) p.acrTotal += r.qtyACR;
    if (!p.byDay.has(r.day)) p.byDay.set(r.day, r);
  }

  // Definisi mirror desktop/55-d: SO_H±k/In_H±k dari baris hari itu (tanpa
  // baris → kosong), Sistem = qtySaldoAkhir@H, Deviasi = SO_H − (Sistem ?? 0)
  // (sistem missing dianggap 0 — desktop 2058; SO_H missing → null), Nominal =
  // harga@H × Deviasi (null bila harga tak ada).
  for (const p of pairs.values()) {
    const at = p.byDay.get(h);
    const so = at?.qtySO ?? null;
    p.deviasi = so !== null ? so - (at?.qtySaldoAkhir ?? 0) : null;
    const harga = at?.hargaEfektif ?? null;
    p.nominal = p.deviasi !== null && harga !== null ? harga * p.deviasi : null;
  }

  // Rank |Deviasi| dalam kelompok Nama Barang+satuan — method min, 0 → kosong
  // (helper paritas desktop dari @/lib/desktop-parity; kanon grouping 55-d).
  const rankMap = rankMinInGroups(
    [...pairs.values()],
    (p) => `${p.itemName}|${p.satuan}`,
    (p) => p.deviasi,
  );

  // Urut: |Nominal| desc, lalu nama barang natural, lalu resto (deterministik).
  const sorted = [...pairs.values()].sort((a, b) => {
    const an = Math.abs(a.nominal ?? 0);
    const bn = Math.abs(b.nominal ?? 0);
    return (bn - an) || naturalCompare(a.itemName, b.itemName) || a.restoCode.localeCompare(b.restoCode);
  });

  let rowIdx = 2;
  for (const p of sorted) {
    const at = p.byDay.get(h);
    ws.getCell(rowIdx, 1).value = p.restoCode;
    ws.getCell(rowIdx, 2).value = p.itemName;
    ws.getCell(rowIdx, 3).value = p.satuan;
    ws.getCell(rowIdx, 4).value = p.kategori;
    setNumCell(ws, rowIdx, 5, p.byDay.get(h - 2)?.qtySO ?? null);
    setNumCell(ws, rowIdx, 6, p.byDay.get(h - 1)?.qtySO ?? null);
    setNumCell(ws, rowIdx, 7, p.byDay.get(h - 1)?.qtyIN ?? null);
    setNumCell(ws, rowIdx, 8, p.byDay.get(h)?.qtySO ?? null);
    setNumCell(ws, rowIdx, 9, p.byDay.get(h)?.qtyIN ?? null);
    setNumCell(ws, rowIdx, 10, p.byDay.get(h + 1)?.qtySO ?? null);
    setNumCell(ws, rowIdx, 11, p.byDay.get(h + 2)?.qtySO ?? null);
    setNumCell(ws, rowIdx, 12, at?.qtySaldoAkhir ?? null);
    setNumCell(ws, rowIdx, 13, p.deviasi);
    setNumCell(ws, rowIdx, 14, p.nominal);
    // Dev to BOM % = |Deviasi| / max(Σ ACR pasangan, ε) × 100; Σ ACR 0 → null.
    const bomPct =
      p.deviasi !== null && p.acrTotal > 0
        ? (Math.abs(p.deviasi) / Math.max(p.acrTotal, EPS)) * 100
        : null;
    setNumCell(ws, rowIdx, 15, bomPct);
    setIntCell(ws, rowIdx, 16, rankMap.get(p) ?? null);
    // CEK = gabungan label cekJson baris @H; Keterangan Audit = catatan B1–B4 @H.
    ws.getCell(rowIdx, 17).value = at ? parseJsonSafe<string[]>(at.cekJson, []).join(" · ") : "";
    ws.getCell(rowIdx, 18).value = at?.auditNote ?? "";
    rowIdx += 1;
  }
  finishSheet(ws, pairs.size > 0);
}

// ------------------------------------------------------------
// Sheet 3 — SELISIH_IN (rekap per resto, model SelisihInResto)
// ------------------------------------------------------------

async function buildSelisihSheet(wb: ExcelJS.Workbook, snapshotId: string): Promise<void> {
  const ws = wb.addWorksheet("SELISIH_IN");
  ws.addRow([
    "Resto", "IN", "Barang Masuk", "Selisih",
    "Hasil Audit", "Skor Resto", "Item Berselisih", "Tanggal Terdampak",
  ]);

  const list = await db.selisihInResto.findMany({
    where: { snapshotId },
    orderBy: { restoCode: "asc" },
  });

  let rowIdx = 2;
  for (const s of list) {
    ws.getCell(rowIdx, 1).value = s.restoCode;
    setNumCell(ws, rowIdx, 2, s.inAccurate);
    setNumCell(ws, rowIdx, 3, s.barangMasuk);
    setNumCell(ws, rowIdx, 4, s.selisih);
    ws.getCell(rowIdx, 5).value = s.hasilAudit === "OK" ? "OK" : "SELISIH";
    setIntCell(ws, rowIdx, 6, s.skorResto);
    setIntCell(ws, rowIdx, 7, s.itemBerselisih);
    setIntCell(ws, rowIdx, 8, s.tanggalTerdampak);
    rowIdx += 1;
  }
  finishSheet(ws, list.length > 0);
}

// ------------------------------------------------------------
// Sheet 4 — NOMINAL (Σ nominal & Σ qty deviasi per resto + TOTAL)
// ------------------------------------------------------------

function buildNominalSheet(wb: ExcelJS.Workbook, rows: readonly ExportRow[]): void {
  const ws = wb.addWorksheet("NOMINAL");
  ws.addRow(["Resto", "Nominal Deviasi", "Qty Deviasi"]);

  const perResto = new Map<string, { restoName: string; nominal: number; qty: number }>();
  for (const r of rows) {
    let e = perResto.get(r.restoCode);
    if (!e) {
      e = { restoName: r.restoName, nominal: 0, qty: 0 };
      perResto.set(r.restoCode, e);
    }
    if (r.nominal !== null) e.nominal += r.nominal;
    if (r.qtyDeviasi !== null) e.qty += r.qtyDeviasi;
  }

  // Urut nominal desc (materialitas — mirror route /nominal web).
  const list = [...perResto.entries()].sort((a, b) => b[1].nominal - a[1].nominal);

  let rowIdx = 2;
  for (const [restoCode, v] of list) {
    ws.getCell(rowIdx, 1).value = restoCode;
    setNumCell(ws, rowIdx, 2, v.nominal);
    setNumCell(ws, rowIdx, 3, v.qty);
    rowIdx += 1;
  }

  if (list.length > 0) {
    // Baris TOTAL di akhir — bold (merah bila minus).
    const totalNominal = list.reduce((s, [, v]) => s + v.nominal, 0);
    const totalQty = list.reduce((s, [, v]) => s + v.qty, 0);
    const label = ws.getCell(rowIdx, 1);
    label.value = "TOTAL";
    label.font = { bold: true };
    const cNom = ws.getCell(rowIdx, 2);
    cNom.value = totalNominal;
    cNom.numFmt = NUM_FMT;
    cNom.font = totalNominal < 0 ? { bold: true, color: { argb: MINUS_FONT } } : { bold: true };
    const cQty = ws.getCell(rowIdx, 3);
    cQty.value = totalQty;
    cQty.numFmt = NUM_FMT;
    cQty.font = totalQty < 0 ? { bold: true, color: { argb: MINUS_FONT } } : { bold: true };
  }
  finishSheet(ws, list.length > 0);
}

// ------------------------------------------------------------
// Sheet 5 — PO (satu baris per item PO)
// ------------------------------------------------------------

async function buildPoSheet(wb: ExcelJS.Workbook, snapshotId: string): Promise<void> {
  const ws = wb.addWorksheet("PO");
  ws.addRow([
    "Nomor PO", "Tanggal", "Cabang", "Resto", "Pemasok", "Item", "Qty", "Satuan",
    "Status", "Status Pesanan", "Diterima Sebagian (Ya/Tidak)", "Anotasi",
  ]);

  const headers = await db.poHeader.findMany({
    where: { snapshotId },
    include: { items: { orderBy: { itemName: "asc" } } },
    orderBy: [{ cabang: "asc" }, { poNumber: "asc" }],
  });

  let rowIdx = 2;
  let itemCount = 0;
  for (const h of headers) {
    for (const it of h.items) {
      ws.getCell(rowIdx, 1).value = h.poNumber;
      ws.getCell(rowIdx, 2).value = h.tanggal;
      ws.getCell(rowIdx, 3).value = h.cabang;
      ws.getCell(rowIdx, 4).value = h.restoName;
      ws.getCell(rowIdx, 5).value = h.supplier ?? "";
      ws.getCell(rowIdx, 6).value = it.itemName;
      setNumCell(ws, rowIdx, 7, it.qty);
      ws.getCell(rowIdx, 8).value = it.satuan;
      ws.getCell(rowIdx, 9).value = it.status;
      ws.getCell(rowIdx, 10).value = h.statusPesanan;
      ws.getCell(rowIdx, 11).value = it.diterimaSebagian ? "Ya" : "Tidak";
      ws.getCell(rowIdx, 12).value = h.annotasi ?? "";
      rowIdx += 1;
      itemCount += 1;
    }
  }
  finishSheet(ws, itemCount > 0);
}

// ------------------------------------------------------------
// GET — susun workbook & kirim sebagai unduhan
// ------------------------------------------------------------

export async function GET(req: NextRequest, ctx: Ctx) {
  try {
    const { id } = await ctx.params;

    const sheetParam = req.nextUrl.searchParams.get("sheet") ?? "all";
    if (!SHEET_OPTIONS.includes(sheetParam as SheetOption)) {
      return NextResponse.json(
        { error: `Parameter sheet tidak valid: "${sheetParam}". Gunakan: ${SHEET_OPTIONS.join(", ")}.` },
        { status: 400 },
      );
    }
    const sheet = sheetParam as SheetOption;

    const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
    if (!snapshot) {
      return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });
    }

    const params = parseJsonSafe(snapshot.paramsJson, { tanggalH: 25, ambangAcrPct: 80 });
    const h = Math.min(Math.max(Number(params.tanggalH) || 25, 1), snapshot.dayCount);

    const workbook = new ExcelJS.Workbook();
    workbook.creator = "Stock Monitoring Web";
    workbook.created = new Date();

    const wanted: Exclude<SheetOption, "all">[] =
      sheet === "all" ? ["pivot", "deviasi", "selisih", "nominal", "po"] : [sheet];

    // SATU findMany untuk semua sheet berbasis rows (PIVOT/DEVIASI/NOMINAL).
    const needsRows = wanted.some((s) => s === "pivot" || s === "deviasi" || s === "nominal");
    const rows: ExportRow[] = needsRows
      ? await db.snapshotRow.findMany({
          where: { snapshotId: id },
          select: {
            restoCode: true, restoName: true, itemName: true, satuan: true,
            kategori: true, day: true,
            qtySaldoAwal: true, qtySO: true, qtySaldoAkhir: true, qtyDeviasi: true,
            qtyIN: true, qtyBarangMasuk: true, qtyCOM: true, qtySelisihIN: true,
            qtyBarangKeluar: true, qtyACR: true,
            hargaEfektif: true, nominal: true, cekJson: true, auditNote: true,
          },
        })
      : [];

    for (const s of wanted) {
      if (s === "pivot") buildPivotSheet(workbook, rows);
      else if (s === "deviasi") buildDeviasiSheet(workbook, rows, h);
      else if (s === "selisih") await buildSelisihSheet(workbook, id);
      else if (s === "nominal") buildNominalSheet(workbook, rows);
      else await buildPoSheet(workbook, id);
    }

    const buf = await workbook.xlsx.writeBuffer();
    return new NextResponse(buf as ArrayBuffer, {
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="stock-monitoring-${snapshot.periodKey}${sheet !== "all" ? `-${sheet}` : ""}.xlsx"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "kesalahan tidak diketahui";
    return NextResponse.json({ error: `Gagal membuat file export Excel: ${msg}` }, { status: 500 });
  }
}
