import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

export async function POST(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id } = await ctx.params;

  try {
    const base = getInternalBase();
    const body = await req.json().catch(() => ({}));
    const upstream = await fetch(`${base}/api/sessions/${id}/submit`, {
      method: "POST",
      headers: {
        ...internalHeaders(emailOrRes),
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
