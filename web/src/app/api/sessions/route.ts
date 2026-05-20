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
    const body = await req.json().catch(() => ({}));
    const upstream = await fetch(`${base}/api/sessions`, {
      method: "POST",
      headers: {
        ...internalHeaders(emailOrRes),
        "content-type": "application/json",
      },
      body: JSON.stringify({ createdBy: emailOrRes, ...body }),
    });
    return proxyResponse(upstream);
  } catch {
    return misconfigResponse();
  }
}
