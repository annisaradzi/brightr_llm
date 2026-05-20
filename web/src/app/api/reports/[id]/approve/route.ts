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
    const upstream = await fetch(`${base}/api/reports/${id}/approve`, {
      method: "POST",
      headers: internalHeaders(emailOrRes),
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
