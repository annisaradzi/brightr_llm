import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string; itemId: string }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id, itemId } = await ctx.params;

  try {
    const base = getInternalBase();
    const upstream = await fetch(`${base}/api/sessions/${id}/items/${itemId}/image`, {
      headers: internalHeaders(emailOrRes),
    });
    if (!upstream.ok) {
      const text = await upstream.text();
      return new NextResponse(text, { status: upstream.status });
    }
    const buf = await upstream.arrayBuffer();
    const ct = upstream.headers.get("content-type") || "image/jpeg";
    return new NextResponse(buf, {
      status: 200,
      headers: { "content-type": ct },
    });
  } catch {
    return misconfigResponse();
  }
}
