import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { clampString, isPeriodKey } from "@/lib/validate";
import type { FollowUpCaseDto, FollowUpEventDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET /api/followup/[id] — detail kasus + timeline lengkap (FR-41). */
export async function GET(_req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const c = await db.followUpCase.findUnique({
    where: { id },
    include: { events: { orderBy: { createdAt: "asc" } } },
  });
  if (!c) return NextResponse.json({ error: "Kasus tidak ditemukan." }, { status: 404 });

  const caseDto: FollowUpCaseDto = {
    id: c.id, fingerprint: c.fingerprint, restoCode: c.restoCode, restoName: c.restoName,
    itemName: c.itemName, satuan: c.satuan, kategori: c.kategori,
    status: c.status as FollowUpCaseDto["status"], pic: c.pic,
    periodFirstSeen: c.periodFirstSeen, currentPeriodKey: c.currentPeriodKey,
    currentQtyDeviasi: c.currentQtyDeviasi, currentNominal: c.currentNominal,
    currentHarga: c.currentHarga, note: c.note,
    createdAt: c.createdAt.toISOString(), updatedAt: c.updatedAt.toISOString(),
    closedAt: c.closedAt ? c.closedAt.toISOString() : null,
    eventCount: c.events.length,
    lastEventAt: c.events.length ? c.events[c.events.length - 1].createdAt.toISOString() : null,
  };

  const events: FollowUpEventDto[] = c.events.map((e) => ({
    id: e.id, actor: e.actor, fromStatus: e.fromStatus, toStatus: e.toStatus,
    alasan: e.alasan, kategoriTindakan: e.kategoriTindakan, qtyTemuan: e.qtyTemuan,
    createdAt: e.createdAt.toISOString(),
  }));

  return NextResponse.json({ case: caseDto, events });
}

/** PATCH /api/followup/[id] — perbarui PIC/catatan/angka kasus (FR-42). */
export async function PATCH(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }

  const existing = await db.followUpCase.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Kasus tidak ditemukan." }, { status: 404 });

  const data: Record<string, string | number | null> = {};
  if ("pic" in body) data.pic = clampString(body.pic, 120);
  if ("note" in body) data.note = clampString(body.note, 500);
  if ("currentPeriodKey" in body) {
    // Validasi format penuh (audit 48-g-api) — bukan sekadar slice(0,7).
    if (typeof body.currentPeriodKey !== "string" || !isPeriodKey(body.currentPeriodKey)) {
      return NextResponse.json(
        { error: "currentPeriodKey wajib format YYYY-MM (contoh: 2026-10)." },
        { status: 422 },
      );
    }
    data.currentPeriodKey = body.currentPeriodKey;
  }
  if ("currentQtyDeviasi" in body) {
    const v = body.currentQtyDeviasi;
    data.currentQtyDeviasi = typeof v === "number" && Number.isFinite(v) ? v : null;
  }
  if ("currentNominal" in body) {
    const v = body.currentNominal;
    data.currentNominal = typeof v === "number" && Number.isFinite(v) ? v : null;
  }

  const updated = await db.followUpCase.update({ where: { id }, data });

  await db.auditLog.create({
    data: {
      action: "FOLLOWUP_UPDATE",
      entity: "FollowUpCase",
      entityId: id,
      detailJson: JSON.stringify({ fields: Object.keys(data) }),
      actor: "analyst",
    },
  });

  return NextResponse.json({ ok: true, pic: updated.pic, note: updated.note });
}
