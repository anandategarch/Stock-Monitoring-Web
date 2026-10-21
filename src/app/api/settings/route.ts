import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { parseIntInRange } from "@/lib/validate";
import { engineHealth } from "@/lib/engine";
import type { SettingsDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEFAULTS: SettingsDto = {
  tanggalHDefault: 25,
  ambangAcrDefault: 80,
  engineKind: "demo",
  kategoriBarang4217: null,
};

/** GET /api/settings — config.json replika + preferensi (FR-2/FR-80). */
export async function GET() {
  const rows = await db.setting.findMany();
  const map = new Map(rows.map((r) => [r.key, r.valueJson]));
  const engine = await engineHealth();
  const settings: SettingsDto = {
    tanggalHDefault: parseIntInRange(map.get("tanggalHDefault"), 1, 31) ?? DEFAULTS.tanggalHDefault,
    ambangAcrDefault: parseIntInRange(map.get("ambangAcrDefault"), 1, 200) ?? DEFAULTS.ambangAcrDefault,
    engineKind: engine?.engineKind ?? DEFAULTS.engineKind,
    kategoriBarang4217: map.get("kategoriBarang4217") ?? null,
  };
  return NextResponse.json({ settings });
}

/** PUT /api/settings — ubah default (tercatat AuditLog; INV-9 ambang ACR default 80). */
export async function PUT(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }

  const updates: { key: string; value: string }[] = [];
  if ("tanggalHDefault" in body) {
    const h = parseIntInRange(body.tanggalHDefault, 1, 31);
    if (h === null) {
      return NextResponse.json({ error: "tanggalHDefault wajib integer 1..31." }, { status: 422 });
    }
    updates.push({ key: "tanggalHDefault", value: String(h) });
  }
  if ("ambangAcrDefault" in body) {
    const a = parseIntInRange(body.ambangAcrDefault, 1, 200);
    if (a === null) {
      return NextResponse.json({ error: "ambangAcrDefault wajib integer 1..200." }, { status: 422 });
    }
    updates.push({ key: "ambangAcrDefault", value: String(a) });
  }
  if (updates.length === 0) {
    return NextResponse.json({ error: "Tidak ada perubahan yang dikirim." }, { status: 422 });
  }

  for (const u of updates) {
    await db.setting.upsert({
      where: { key: u.key },
      update: { valueJson: u.value, updatedBy: "analyst" },
      create: { key: u.key, valueJson: u.value, updatedBy: "analyst" },
    });
  }

  await db.auditLog.create({
    data: {
      action: "SETTING_UPDATE",
      entity: "Setting",
      entityId: null,
      detailJson: JSON.stringify(updates),
      actor: "analyst",
    },
  });

  const rows = await db.setting.findMany();
  const map = new Map(rows.map((r) => [r.key, r.valueJson]));
  const settings: SettingsDto = {
    tanggalHDefault: parseIntInRange(map.get("tanggalHDefault"), 1, 31) ?? DEFAULTS.tanggalHDefault,
    ambangAcrDefault: parseIntInRange(map.get("ambangAcrDefault"), 1, 200) ?? DEFAULTS.ambangAcrDefault,
    engineKind: DEFAULTS.engineKind,
    kategoriBarang4217: map.get("kategoriBarang4217") ?? null,
  };
  return NextResponse.json({ settings });
}
