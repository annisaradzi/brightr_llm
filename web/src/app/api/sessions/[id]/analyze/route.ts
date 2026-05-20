import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";
export const maxDuration = 60;

type Ctx = { params: Promise<{ id: string }> };

export async function POST(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id } = await ctx.params;
  const rerun = req.nextUrl.searchParams.get("rerun") === "true";

  try {
    const base = getInternalBase();
    const upstream = await fetch(
      `${base}/api/sessions/${id}/analyze?rerun=${rerun}`,
      {
        method: "POST",
        headers: internalHeaders(emailOrRes),
      }
    );
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
