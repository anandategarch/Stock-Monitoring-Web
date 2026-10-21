import { NextRequest, NextResponse } from "next/server";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { clampString, isNonEmptyString } from "@/lib/validate";
import type { OutletPICDto } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** GET /api/pics — daftar PIC per outlet (dropdown FR-42). */
export async function GET() {
  const pics = await db.outletPIC.findMany({
    orderBy: [{ outletCode: "asc" }, { picName: "asc" }],
  });
  const data: OutletPICDto[] = pics.map((p) => ({
    id: p.id, outletCode: p.outletCode, picName: p.picName,
    waNumber: p.waNumber, notes: p.notes,
  }));
  return NextResponse.json({ pics: data });
}

/** POST /api/pics — tambah PIC (FR-42: dropdown + teks bebas). */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Body harus JSON valid." }, { status: 400 });
  }
  const outletCode = body.outletCode;
  const picName = body.picName;
  if (!isNonEmptyString(outletCode) || !isNonEmptyString(picName)) {
    return NextResponse.json({ error: "outletCode dan picName wajib diisi." }, { status: 422 });
  }
  const existing = await db.outletPIC.findFirst({
    where: { outletCode: outletCode.slice(0, 12), picName: picName.slice(0, 120) },
  });
  if (existing) {
    return NextResponse.json({ error: "PIC ini sudah terdaftar untuk outlet tersebut." }, { status: 409 });
  }
  let created;
  try {
    created = await db.outletPIC.create({
      data: {
        outletCode: outletCode.slice(0, 12),
        picName: picName.slice(0, 120),
        waNumber: clampString(body.waNumber, 40),
        notes: clampString(body.notes, 300),
      },
    });
  } catch (err) {
    // Race create ganda (audit 48-g-api) → 409 ramah, bukan 500 mentah.
    if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === "P2002") {
      return NextResponse.json(
        { error: "PIC ini sudah terdaftar untuk outlet tersebut." },
        { status: 409 },
      );
    }
    throw err;
  }
  await db.auditLog.create({
    data: {
      action: "PIC_CREATE",
      entity: "OutletPIC",
      entityId: created.id,
      detailJson: JSON.stringify({ outletCode: created.outletCode, picName: created.picName }),
      actor: "analyst",
    },
  });
  const dto: OutletPICDto = {
    id: created.id, outletCode: created.outletCode, picName: created.picName,
    waNumber: created.waNumber, notes: created.notes,
  };
  return NextResponse.json({ pic: dto }, { status: 201 });
}
