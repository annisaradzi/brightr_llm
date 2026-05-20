import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id } = await ctx.params;

  try {
    const base = getInternalBase();
    const upstream = await fetch(`${base}/api/reports/${id}/pdf`, {
      headers: internalHeaders(emailOrRes),
    });
    if (!upstream.ok) {
      const text = await upstream.text();
      return new NextResponse(text, { status: upstream.status });
    }
    const buf = await upstream.arrayBuffer();
    const headers = new Headers();
    const ct = upstream.headers.get("content-type");
    const cd = upstream.headers.get("content-disposition");
    if (ct) headers.set("content-type", ct);
    if (cd) headers.set("content-disposition", cd);
    return new NextResponse(buf, { status: 200, headers });
  } catch {
    return misconfigResponse();
  }
}
