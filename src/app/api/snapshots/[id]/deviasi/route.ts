// ============================================================
// SM-WEB — Task 55-d: GET /api/snapshots/[id]/deviasi
// ?group=GR|PCS&h=N&ambang=M&onlyDevH=0|1
// WIDE-MATRIX PER-TANGGAL ala desktop (referensi kebenaran:
// src/ui/deviasi_view.py v3.9.71):
//   • COLUMNS 473-519  — kolom SO(H-2), SO(H-1), In(H-1), SO(H), In(H),
//     SO(H+1), In(H+1), SO(H+2) + Sistem + Deviasi + Nominal + Rank +
//     Dev to BOM% + Dev. Bulan Lalu + CEK.
//   • _col_display_name 1565-1586 — heading dinamis per H: "SO_23" dst;
//     tanggal 0 → "…_lalu" (penutupan bulan lalu), tanggal < 0 → "…_—".
//   • Sistem 2005  = qtySaldoAkhir @H · Deviasi 2058 = SO_H − Sistem
//     (sistem missing dianggap 0 ala fillna desktop; SO_H missing → null, INV-1).
//   • Rank v3.9.65 = |Deviasi| per-baris dalam kelompok itemName
//     (semua resto, satuan sama), method "min" (nilai sama → rank sama),
//     dev 0/null → rank null.
//   • Dev. Bulan Lalu = Σ qtyDeviasi pasangan sama pada snapshot ACTIVE
//     periode lalu (prevPeriodKey "@/lib/format"); tak ada → null ("—").
// Semantik CEK web lama DIPERTAHANKAN: label tersimpan digabung dari
// cekJson semua hari pasangan TANPA "ACR to BOM" (label itu dihitung
// ulang live di UI saat ambang berubah — FR-30).
// ============================================================
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { prevPeriodKey } from "@/lib/format";
import { stableFingerprint } from "@/lib/fingerprint";
import { parseJsonSafe } from "@/lib/snapshot-service";
import { rankMinInGroups } from "@/lib/desktop-parity";
import type { AuditNote, CekLabel } from "@/lib/types";
import type { DeviasiDesktopResponse, DeviasiDesktopRow } from "@/lib/deviasi-def";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Pivot in-memory atas SEMUA baris grain hari pasangan + kueri snapshot
// bulan lalu — beri napas serverless (Task 55-d).
export const maxDuration = 60;

type Ctx = { params: Promise<{ id: string }> };

/** Metrik per-hari yang dipakai pivot @H (grain SnapshotRow: hari). */
interface PairDay {
  qtySO: number | null;
  qtyIN: number | null;
  qtySaldoAkhir: number | null;
  hargaEfektif: number | null;
}

/** Akumulator per pasangan resto × barang × satuan (semua hari). */
interface PairAgg {
  restoCode: string;
  restoName: string;
  itemName: string;
  satuan: string;
  kategori: string;
  days: Map<number, PairDay>;
  acrTotal: number;
  cek: Set<CekLabel>;
  auditNotes: Set<AuditNote>;
  konversiOk: boolean;
  // — hasil pivot @H (diisi pass kedua) —
  sistem: number | null;
  deviasi: number | null;
  nominal: number | null;
  harga: number | null;
  devToBomPct: number | null;
  devBulanLalu: number | null;
}

/**
 * Heading dinamis ala desktop _col_display_name (deviasi_view.py:1565-1586):
 * prefix + tanggal hasil H±k. Tanggal 0 tidak pernah ada sebagai tanggal
 * (rekap bulan lalu memakai kunci −1 = saldo penutupan) → label jujur
 * "…_lalu"; tanggal < 0 → "…_—" (sel selalu "—": tak pernah ada datanya).
 */
function colDisplayName(prefix: "SO" | "In", date: number): string {
  if (date === 0) return `${prefix}_lalu`;
  if (date < 0) return `${prefix}_\u2014`;
  return `${prefix}_${date}`;
}

// Definisi kolom per-tanggal — offset PERSIS COLUMNS desktop (baris 487-494).
const SO_OFFSETS: { key: string; off: number }[] = [
  { key: "SO_H-2", off: -2 },
  { key: "SO_H-1", off: -1 },
  { key: "SO_H", off: 0 },
  { key: "SO_H+1", off: 1 },
  { key: "SO_H+2", off: 2 },
];
const IN_OFFSETS: { key: string; off: number }[] = [
  { key: "In_H-1", off: -1 },
  { key: "In_H", off: 0 },
  { key: "In_H+1", off: 1 },
];

export async function GET(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const snapshot = await db.periodSnapshot.findUnique({ where: { id } });
  if (!snapshot) return NextResponse.json({ error: "Snapshot tidak ditemukan." }, { status: 404 });

  const sp = req.nextUrl.searchParams;
  const group = sp.get("group") === "PCS" ? "PCS" : "GR";
  const onlyDevH = sp.get("onlyDevH") === "1";
  const params = parseJsonSafe(snapshot.paramsJson, { tanggalH: 25, ambangAcrPct: 80 });
  const h = Math.min(Math.max(Number(sp.get("h") ?? params.tanggalH) || params.tanggalH, 1), snapshot.dayCount);
  const ambang = Math.min(Math.max(Number(sp.get("ambang") ?? params.ambangAcrPct) || params.ambangAcrPct, 1), 200);

  // Satu kueri utk seluruh kolom grain hari (pivot dilakukan in-memory).
  const rows = await db.snapshotRow.findMany({
    where: { snapshotId: id, isGR: group === "GR" },
    orderBy: [{ restoCode: "asc" }, { itemName: "asc" }, { day: "asc" }],
  });

  // Snapshot ACTIVE periode lalu → bahan kolom "Dev. Bulan Lalu".
  const prevKey = prevPeriodKey(snapshot.periodKey);
  const prevSnap = await db.periodSnapshot.findFirst({
    where: { periodKey: prevKey, state: "ACTIVE" },
    orderBy: { committedAt: "desc" },
  });
  const prevRows = prevSnap
    ? await db.snapshotRow.findMany({
        where: { snapshotId: prevSnap.id, isGR: group === "GR" },
        select: { restoCode: true, itemName: true, satuan: true, qtyDeviasi: true },
      })
    : [];

  // ---- Pass 1: akumulasi per pasangan (semua hari) ----
  const pairs = new Map<string, PairAgg>();
  for (const r of rows) {
    const key = `${r.restoCode}|${r.itemName}|${r.satuan}`;
    let p = pairs.get(key);
    if (!p) {
      p = {
        restoCode: r.restoCode, restoName: r.restoName, itemName: r.itemName,
        satuan: r.satuan, kategori: r.kategori,
        days: new Map(), acrTotal: 0, cek: new Set(), auditNotes: new Set(),
        konversiOk: true,
        sistem: null, deviasi: null, nominal: null, harga: null,
        devToBomPct: null, devBulanLalu: null,
      };
      pairs.set(key, p);
    }
    p.days.set(r.day, {
      qtySO: r.qtySO, qtyIN: r.qtyIN, qtySaldoAkhir: r.qtySaldoAkhir,
      hargaEfektif: r.hargaEfektif,
    });
    if (r.qtyACR !== null) p.acrTotal += r.qtyACR; // Σ semua hari (bahan Dev to BOM% + CEK live)
    if (!r.konversiOk) p.konversiOk = false;
    if (r.auditNote) p.auditNotes.add(r.auditNote as AuditNote);
    // CEK web lama: label digabung dari SEMUA hari pasangan; "ACR to BOM"
    // sengaja disisihkan — re-komputasi live di UI dari ambang (FR-30).
    for (const c of parseJsonSafe<CekLabel[]>(r.cekJson, [])) {
      if (c !== "ACR to BOM") p.cek.add(c);
    }
  }

  // Σ deviasi bulan lalu per pasangan (null bila pasangan tak ada → "—").
  const prevDev = new Map<string, number>();
  for (const r of prevRows) {
    if (r.qtyDeviasi === null) continue;
    const key = `${r.restoCode}|${r.itemName}|${r.satuan}`;
    prevDev.set(key, (prevDev.get(key) ?? 0) + r.qtyDeviasi);
  }

  // ---- Pass 2: pivot @H per pasangan ----
  const pairList = [...pairs.values()];
  for (const p of pairList) {
    const rowH = p.days.get(h);
    const soH = rowH?.qtySO ?? null;
    // Sistem = qtySaldoAkhir @H (desktop 2005). Deviasi = SO_H − Sistem
    // (desktop 2058); sistem missing → 0 (fillna desktop) tapi SO_H missing
    // → deviasi null (INV-1: missing tidak dibuat-buat jadi angka).
    p.sistem = rowH?.qtySaldoAkhir ?? null;
    p.deviasi = soH === null ? null : soH - (p.sistem ?? 0);
    p.harga = rowH?.hargaEfektif ?? null;
    p.nominal = p.harga !== null && p.deviasi !== null ? p.harga * p.deviasi : null;
    // Dev to BOM% = |Deviasi| / max(Σ ACR semua hari, ε) × 100; Σ ACR 0 → null.
    p.devToBomPct =
      p.deviasi !== null && p.acrTotal > 0
        ? (Math.abs(p.deviasi) / Math.max(p.acrTotal, Number.EPSILON)) * 100
        : null;
    p.devBulanLalu = prevDev.get(`${p.restoCode}|${p.itemName}|${p.satuan}`) ?? null;
  }

  // Rank |Deviasi| per kelompok itemName + satuan (semua resto) — method
  // "min" ala desktop v3.9.65 (deviasi_view.py:2566-2572): nilai sama →
  // rank sama; deviasi 0/null → rank null. Di atas frame GRUP PENUH
  // (bukan frame onlyDevH) supaya rank stabil saat saklar di-toggle.
  const rankMap = rankMinInGroups(
    pairList,
    (p) => `${p.itemName}\u001f${p.satuan}`,
    (p) => p.deviasi,
  );

  // ---- Pass 3: filter + peta ke baris respons ----
  const out: DeviasiDesktopRow[] = [];
  for (const p of pairList) {
    // "Hanya baris deviasi H ≠ 0" — perilaku web lama dipertahankan (server-side).
    if (onlyDevH && (p.deviasi === null || p.deviasi === 0)) continue;
    const soCols = SO_OFFSETS.map(({ key, off }) => ({
      key,
      label: colDisplayName("SO", h + off),
      value: p.days.get(h + off)?.qtySO ?? null, // null = missing INV-1
    }));
    const inCols = IN_OFFSETS.map(({ key, off }) => ({
      key,
      label: colDisplayName("In", h + off),
      value: p.days.get(h + off)?.qtyIN ?? null,
    }));
    out.push({
      fingerprint: stableFingerprint(p.restoCode, p.itemName, p.satuan, p.kategori),
      restoCode: p.restoCode,
      restoName: p.restoName,
      itemName: p.itemName,
      satuan: p.satuan,
      kategori: p.kategori,
      soCols,
      inCols,
      sistem: p.sistem,
      deviasi: p.deviasi,
      nominal: p.nominal,
      devToBomPct: p.devToBomPct,
      devBulanLalu: p.devBulanLalu,
      acrTotal: p.acrTotal,
      cek: [...p.cek],
      auditNotes: [...p.auditNotes],
      rank: rankMap.get(p) ?? null,
      harga: p.harga,
      konversiOk: p.konversiOk,
    });
  }

  // Urutan dasar = layout default desktop v3.9.65: Nama Barang asc lalu
  // |Deviasi| desc dalam kelompok — tab tetap bisa sort ulang sisi klien.
  out.sort(
    (a, b) =>
      a.itemName.localeCompare(b.itemName, "id") ||
      Math.abs(b.deviasi ?? 0) - Math.abs(a.deviasi ?? 0) ||
      a.restoCode.localeCompare(b.restoCode),
  );

  const resp: DeviasiDesktopResponse = {
    snapshotId: id,
    periodKey: snapshot.periodKey,
    group,
    h,
    ambang,
    hasPrev: prevSnap !== null,
    prevPeriodKey: prevSnap ? prevKey : null,
    totalRows: out.length,
    rows: out,
  };
  return NextResponse.json(resp);
}
