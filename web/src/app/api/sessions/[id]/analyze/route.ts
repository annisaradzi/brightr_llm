import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";
export const maxDuration = 300;

type Ctx = { params: Promise<{ id: string }> };

export async function POST(req: NextRequest, ctx: Ctx) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;
  const { id } = await ctx.params;
  const rerun = req.nextUrl.searchParams.get("rerun") === "true";

  try {
    const base = getInternalBase();
    const clientIp = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
    const headers = internalHeaders(emailOrRes) as Record<string, string>;
    if (clientIp) headers["X-Client-IP"] = clientIp;
    const upstream = await fetch(
      `${base}/api/sessions/${id}/analyze?rerun=${rerun}`,
      {
        method: "POST",
        headers,
      }
    );
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
