/**
 * validation.ts — validasi body POST /process (kontrak §2.2).
 * Semua pesan error dalam Bahasa Indonesia; gagal validasi → HTTP 422 { "error": string }.
 */

/** Hasil normalisasi request yang lolos validasi (seed & bundleName selalu terisi). */
export interface NormalizedEngineParams {
  periodKey: string;
  tanggalH: number;
  ambangAcrPct: number;
  bundleName: string | null;
  seed: number;
}

export type ValidationResult =
  | { ok: true; value: NormalizedEngineParams }
  | { ok: false; error: string };

const PERIOD_KEY_REGEX = /^\d{4}-(0[1-9]|1[0-2])$/;

export function validateProcessRequest(body: unknown): ValidationResult {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { ok: false, error: "Body request wajib objek JSON berisi periodKey, tanggalH, dan ambangAcrPct" };
  }
  const b = body as Record<string, unknown>;

  if (typeof b.periodKey !== "string" || !PERIOD_KEY_REGEX.test(b.periodKey)) {
    return { ok: false, error: "periodKey wajib teks berformat YYYY-MM dengan bulan 01..12 (contoh: 2026-10)" };
  }
  if (typeof b.tanggalH !== "number" || !Number.isInteger(b.tanggalH) || b.tanggalH < 1 || b.tanggalH > 31) {
    return { ok: false, error: "tanggalH wajib bilangan bulat antara 1..31" };
  }
  if (typeof b.ambangAcrPct !== "number" || !Number.isInteger(b.ambangAcrPct) || b.ambangAcrPct < 1 || b.ambangAcrPct > 200) {
    return { ok: false, error: "ambangAcrPct wajib bilangan bulat antara 1..200" };
  }

  let bundleName: string | null = null;
  if (b.bundleName !== undefined) {
    if (typeof b.bundleName !== "string") {
      return { ok: false, error: "bundleName wajib berupa teks" };
    }
    bundleName = b.bundleName;
  }

  let seed = 0;
  if (b.seed !== undefined) {
    if (typeof b.seed !== "number" || !Number.isFinite(b.seed)) {
      return { ok: false, error: "seed wajib berupa angka" };
    }
    seed = b.seed;
  }

  return {
    ok: true,
    value: { periodKey: b.periodKey, tanggalH: b.tanggalH, ambangAcrPct: b.ambangAcrPct, bundleName, seed },
  };
}
