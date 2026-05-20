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
    const body = await req.text();
    const upstream = await fetch(`${base}/api/reports/${id}/request-changes`, {
      method: "POST",
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
