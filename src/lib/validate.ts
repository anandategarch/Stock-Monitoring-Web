// Validasi input API — pelengkap validasi engine (pertahanan kedua, server Next.js).
export const PERIOD_KEY_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

export function isPeriodKey(v: unknown): v is string {
  return typeof v === "string" && PERIOD_KEY_RE.test(v);
}

export function parseIntInRange(v: unknown, min: number, max: number): number | null {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  if (!Number.isInteger(n) || n < min || n > max) return null;
  return n;
}

export function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

export function clampString(v: unknown, maxLen: number): string | null {
  if (typeof v !== "string") return null;
  const s = v.trim();
  if (!s) return null;
  return s.slice(0, maxLen);
}
