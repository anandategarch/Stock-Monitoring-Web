import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { stableFingerprint } from "@/lib/fingerprint";
import { isNonEmptyString, isPeriodKey, clampString } from "@/lib/validate";
import type { CreateCaseRequest, FollowUpCaseDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toCaseDto(
  c: {
    id: string; fingerprint: string; restoCode: string; restoName: string; itemName: string;
    satuan: string; kategori: string; status: string; pic: string | null;
    periodFirstSeen: string; currentPeriodKey: string | null; currentQtyDeviasi: number | null;
    currentNominal: number | null; currentHarga: number | null; note: string | null;
    createdAt: Date; updatedAt: Date; closedAt: Date | null;
  },
  eventCount: number,
  lastEventAt: string | null,
): FollowUpCaseDto {
  return {
    ...c,
    status: (c.status as FollowUpCaseDto["status"]) ?? "PENDING",
    createdAt: c.createdAt.toISOString(),
    updatedAt: c.updatedAt.toISOString(),
    closedAt: c.closedAt ? c.closedAt.toISOString() : null,
    eventCount,
    lastEventAt,
  };
}

/** GET /api/followup?status=&resto=&q= — daftar kasus + ringkasan aktivitas (FR-40). */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const status = sp.get("status") ?? "";
  const resto = sp.get("resto") ?? "";
  const q = (sp.get("q") ?? "").trim().toLowerCase();

  const cases = await db.followUpCase.findMany({
    where: {
      ...(status ? { status } : {}),
      ...(resto ? { restoCode: resto } : {}),
    },
    orderBy: [{ updatedAt: "desc" }],
  });

  const ids = cases.map((c) => c.id);
  const grouped = ids.length
    ? await db.followUpEvent.groupBy({
        by: ["caseId"],
        _count: { caseId: true },
        _max: { createdAt: true },
        where: { caseId: { in: ids } },
      })
    : [];
  const countMap = new Map(grouped.map((g) => [g.caseId, { n: g._count.caseId, last: g._max.createdAt }]));

  let list = cases.map((c) => {
    const agg = countMap.get(c.id);
    return toCaseDto(c, agg?.n ?? 0, agg?.last ? agg.last.toISOString() : null);
  });
  if (q) {
    list = list.filter(
      (c) =>
        c.itemName.toLowerCase().includes(q) ||
        c.restoName.toLowerCase().includes(q) ||
        c.restoCode.toLowerCase().includes(q) ||
        (c.pic ?? "").toLowerCase().includes(q),
    );
  }
  return NextResponse.json({ cases: list });
}

/**
 * POST /api/followup — buat kasus dari baris anomali (FR-40/FR-43).
 * Fingerprint stabil → bila masih ada kasus TERBUKA dengan fingerprint sama, kembalikan
 * petunjuk "kasus berulang — tautkan ke kasus #N" (409) alih-alih duplikat diam-diam.
 */
export async function POST(req: NextRequest) {
  let body: CreateCaseRequest;
  try {
    body = (await req.json()) as CreateCaseRequest;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }

  const required: [string, unknown][] = [
    ["restoCode", body.restoCode],
    ["restoName", body.restoName],
    ["itemName", body.itemName],
    ["satuan", body.satuan],
    ["kategori", body.kategori],
    ["periodKey", body.periodKey],
  ];
  for (const [field, v] of required) {
    if (!isNonEmptyString(v)) {
      return NextResponse.json({ error: `Field ${field} wajib diisi.` }, { status: 422 });
    }
  }
  if (!isPeriodKey(body.periodKey)) {
    return NextResponse.json({ error: "periodKey wajib format YYYY-MM." }, { status: 422 });
  }

  const fingerprint = stableFingerprint(body.restoCode, body.itemName, body.satuan, body.kategori);

  const openDupe = await db.followUpCase.findFirst({
    where: { fingerprint, status: { in: ["PENDING", "DIPROSES"] } },
    orderBy: { createdAt: "desc" },
  });
  if (openDupe) {
    return NextResponse.json(
      {
        error: `Kasus berulang — sudah ada kasus #${openDupe.id.slice(0, 8).toUpperCase()} untuk pasangan ini yang masih terbuka. Tautkan ke kasus lama alih-alih membuat duplikat (FR-43).`,
        existingCaseId: openDupe.id,
        fingerprint,
      },
      { status: 409 },
    );
  }

  const created = await db.followUpCase.create({
    data: {
      fingerprint,
      restoCode: body.restoCode,
      restoName: body.restoName,
      itemName: body.itemName,
      satuan: body.satuan,
      kategori: body.kategori,
      status: "PENDING",
      periodFirstSeen: body.periodKey,
      currentPeriodKey: body.periodKey,
      // Koersi numerik defensif (audit 48-g-api): input bukan angka → null,
      // bukan PrismaClientValidationError 500.
      currentQtyDeviasi:
        typeof body.qtyDeviasi === "number" && Number.isFinite(body.qtyDeviasi)
          ? body.qtyDeviasi
          : null,
      currentNominal:
        typeof body.nominal === "number" && Number.isFinite(body.nominal) ? body.nominal : null,
      currentHarga:
        typeof body.harga === "number" && Number.isFinite(body.harga) ? body.harga : null,
      note: clampString(body.note, 500),
    },
  });

  await db.followUpEvent.create({
    data: {
      caseId: created.id,
      actor: "analyst",
      fromStatus: "BARU",
      toStatus: "PENDING",
      alasan: clampString(body.note, 500),
    },
  });

  await db.auditLog.create({
    data: {
      action: "FOLLOWUP_CREATE",
      entity: "FollowUpCase",
      entityId: created.id,
      detailJson: JSON.stringify({ restoCode: body.restoCode, itemName: body.itemName, periodKey: body.periodKey }),
      actor: "analyst",
    },
  });

  return NextResponse.json({ case: toCaseDto(created, 1, created.createdAt.toISOString()) }, { status: 201 });
}
