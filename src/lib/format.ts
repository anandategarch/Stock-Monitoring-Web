// Format tampilan Bahasa Indonesia (NFR-7): ribuan titik, desimal koma, minus tetap
// bertanda (INV-2 — jangan disembunyikan), null = "—" (INV-1: missing ≠ 0).
const nfInt = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const nfRp = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
const nfPct = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 });

export function fmtQty(v: number | null | undefined, opts?: { decimals?: number }): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const f = opts?.decimals === 0 ? nfInt : nf2;
  return f.format(v);
}

export function fmtSignedQty(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const s = nf2.format(v);
  return v > 0 ? `+${s}` : s;
}

export function fmtRp(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const s = nfRp.format(Math.abs(v));
  return `${v < 0 ? "−" : ""}Rp ${s}`;
}

export function fmtNum(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return nf2.format(v);
}

export function fmtInt(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return nfInt.format(v);
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v) || !Number.isFinite(v)) return "—";
  return `${nfPct.format(v)}%`;
}

export function fmtDeltaPct(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  const s = nfPct.format(Math.abs(v));
  const arrow = v > 0 ? "▲" : v < 0 ? "▼" : "";
  return `${arrow} ${s}%`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
    timeZone: "Asia/Jakarta",
  }).format(d);
}

export function fmtDateTimeShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
    timeZone: "Asia/Jakarta",
  }).format(d);
}

const MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];

/** "2026-10" → "Oktober 2026" */
export function periodLabel(periodKey: string): string {
  const [y, m] = periodKey.split("-");
  const idx = Number(m) - 1;
  if (!MONTHS_ID[idx]) return periodKey;
  return `${MONTHS_ID[idx]} ${y}`;
}

export function periodLabelShort(periodKey: string): string {
  const [y, m] = periodKey.split("-");
  return `${y}-${m}`;
}

/** "2026-10" → "2026-09" */
export function prevPeriodKey(periodKey: string): string {
  const [ys, ms] = periodKey.split("-").map(Number);
  const d = new Date(Date.UTC(ys, ms - 1, 1)); // bulan berbasis-0
  d.setUTCMonth(d.getUTCMonth() - 1);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

export function currentPeriodKeyJakarta(): string {
  const now = new Date();
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit",
  }).formatToParts(now);
  const y = parts.find((p) => p.type === "year")?.value;
  const m = parts.find((p) => p.type === "month")?.value;
  return `${y}-${m}`;
}

/** Kelas warna deviasi bertanda: minus merah (kekurangan), plus hijau, 0 netral */
export function signedQtyClass(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-muted-foreground";
  if (v < 0) return "text-rose-600 dark:text-rose-400 font-medium";
  if (v > 0) return "text-emerald-600 dark:text-emerald-400";
  return "text-foreground";
}

export function signedRpClass(v: number | null | undefined): string {
  return signedQtyClass(v);
}
