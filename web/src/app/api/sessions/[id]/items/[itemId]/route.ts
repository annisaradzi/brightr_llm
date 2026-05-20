import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string; itemId: string }> };

export async function DELETE(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id, itemId } = await ctx.params;

  try {
    const base = getInternalBase();
    const upstream = await fetch(`${base}/api/sessions/${id}/items/${itemId}`, {
      method: "DELETE",
      headers: internalHeaders(emailOrRes),
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id, itemId } = await ctx.params;

  try {
    const base = getInternalBase();
    const body = await req.text();
    const upstream = await fetch(`${base}/api/sessions/${id}/items/${itemId}`, {
      method: "PATCH",
      headers: {
        ...internalHeaders(emailOrRes),
        "content-type": "application/json",
      },
      body,
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
