import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { clampString } from "@/lib/validate";
import type { FollowUpCaseDto, FollowUpEventDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** Peta transisi status yang sah (FR-40 + reopen). Selain ini → 422. */
const ALLOWED: Record<string, string[]> = {
  PENDING: ["DIPROSES", "SELESAI", "DIBATALKAN"],
  DIPROSES: ["SELESAI", "DIBATALKAN", "PENDING"],
  SELESAI: ["PENDING"],
  DIBATALKAN: ["PENDING"],
};

/**
 * POST /api/followup/[id]/events — transisi status + alasan + qty temuan fisik (FR-41).
 * Setiap transisi menulis FollowUpEvent (timeline) + AuditLog; kasus menutup/membuka kembali
 * otomatis (closedAt) sesuai status tujuan.
 */
export async function POST(req: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }

  const toStatus = typeof body.toStatus === "string" ? body.toStatus : "";
  if (!["PENDING", "DIPROSES", "SELESAI", "DIBATALKAN"].includes(toStatus)) {
    return NextResponse.json({ error: "toStatus tidak valid." }, { status: 422 });
  }

  const existing = await db.followUpCase.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Kasus tidak ditemukan." }, { status: 404 });

  const fromStatus = existing.status;
  const allowed = ALLOWED[fromStatus] ?? [];
  if (fromStatus === toStatus) {
    return NextResponse.json({ error: `Kasus sudah berstatus ${fromStatus}.` }, { status: 422 });
  }
  if (!allowed.includes(toStatus)) {
    return NextResponse.json(
      { error: `Transisi ${fromStatus} → ${toStatus} tidak diizinkan. Yang sah: ${allowed.join(", ")}.` },
      { status: 422 },
    );
  }

  const isReopen = (fromStatus === "SELESAI" || fromStatus === "DIBATALKAN") && toStatus === "PENDING";
  const closing = toStatus === "SELESAI" || toStatus === "DIBATALKAN";
  const alasan = clampString(body.alasan, 500);
  if ((closing || isReopen) && !alasan) {
    return NextResponse.json(
      { error: "Alasan/tindakan wajib diisi untuk menutup atau membuka kembali kasus (FR-41)." },
      { status: 422 },
    );
  }

  const kategoriTindakan = clampString(body.kategoriTindakan, 80);
  const qtyTemuanRaw = body.qtyTemuan;
  const qtyTemuan =
    typeof qtyTemuanRaw === "number" && Number.isFinite(qtyTemuanRaw) ? qtyTemuanRaw : null;

  const event = await db.followUpEvent.create({
    data: {
      caseId: id,
      actor: "analyst",
      fromStatus,
      toStatus,
      alasan,
      kategoriTindakan,
      qtyTemuan,
    },
  });

  const updated = await db.followUpCase.update({
    where: { id },
    data: {
      status: toStatus,
      ...(closing ? { closedAt: new Date() } : {}),
      ...(isReopen ? { closedAt: null } : {}),
    },
  });

  await db.auditLog.create({
    data: {
      action: "FOLLOWUP_TRANSITION",
      entity: "FollowUpCase",
      entityId: id,
      detailJson: JSON.stringify({ fromStatus, toStatus, alasan }),
      actor: "analyst",
    },
  });

  const caseDto: FollowUpCaseDto = {
    id: updated.id, fingerprint: updated.fingerprint, restoCode: updated.restoCode,
    restoName: updated.restoName, itemName: updated.itemName, satuan: updated.satuan,
    kategori: updated.kategori, status: updated.status as FollowUpCaseDto["status"],
    pic: updated.pic, periodFirstSeen: updated.periodFirstSeen,
    currentPeriodKey: updated.currentPeriodKey, currentQtyDeviasi: updated.currentQtyDeviasi,
    currentNominal: updated.currentNominal, currentHarga: updated.currentHarga,
    note: updated.note, createdAt: updated.createdAt.toISOString(),
    updatedAt: updated.updatedAt.toISOString(),
    closedAt: updated.closedAt ? updated.closedAt.toISOString() : null,
    eventCount: 0,
    lastEventAt: event.createdAt.toISOString(),
  };

  const eventDto: FollowUpEventDto = {
    id: event.id, actor: event.actor, fromStatus: event.fromStatus, toStatus: event.toStatus,
    alasan: event.alasan, kategoriTindakan: event.kategoriTindakan, qtyTemuan: event.qtyTemuan,
    createdAt: event.createdAt.toISOString(),
  };

  return NextResponse.json({ case: caseDto, event: eventDto });
}
