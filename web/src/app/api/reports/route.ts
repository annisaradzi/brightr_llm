import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;

  try {
    const base = getInternalBase();
    const qs = req.nextUrl.searchParams.toString();
    const url = qs ? `${base}/api/reports?${qs}` : `${base}/api/reports`;
    const upstream = await fetch(url, { headers: internalHeaders(emailOrRes) });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
