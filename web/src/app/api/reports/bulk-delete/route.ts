import { NextRequest, NextResponse } from "next/server";
import {
  getInternalBase,
  internalHeaders,
  misconfigResponse,
  proxyResponse,
  requireUserEmail,
} from "@/lib/internal-api";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const emailOrRes = await requireUserEmail(req);
  if (emailOrRes instanceof NextResponse) return emailOrRes;

  try {
    const base = getInternalBase();
    const body = await req.text();
    const upstream = await fetch(`${base}/api/reports/bulk-delete`, {
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
