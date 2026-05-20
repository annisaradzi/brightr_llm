import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";
// Vercel Pro allows up to 300s. Multi-image uploads can take a while end-to-end.
export const maxDuration = 300;

type Ctx = { params: Promise<{ id: string }> };

export async function POST(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id } = await ctx.params;

  try {
    const base = getInternalBase();
    const formData = await req.formData();
    const upstream = await fetch(`${base}/api/sessions/${id}/images`, {
      method: "POST",
      headers: internalHeaders(emailOrRes),
      body: formData,
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
