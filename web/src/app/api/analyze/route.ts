import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export const runtime = "nodejs";
/** Vercel Pro+ can use up to 60s+ depending on plan; Hobby is capped at ~10s (see web/VERCEL.md). */
export const maxDuration = 60;

const INTERNAL = "http://127.0.0.1:8000";

function isLocalhostUrl(u: string): boolean {
  try {
    const h = new URL(u).hostname;
    return h === "localhost" || h === "127.0.0.1" || h === "0.0.0.0" || h === "[::1]";
  } catch {
    return true;
  }
}

export async function POST(req: NextRequest) {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  const email = await verifySessionToken(token);
  if (!email) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const baseRaw = process.env.INTERNAL_API_URL?.replace(/\/$/, "") || INTERNAL;
  if (process.env.NODE_ENV === "production") {
    if (!process.env.INTERNAL_API_URL?.trim() || isLocalhostUrl(baseRaw)) {
      return NextResponse.json(
        {
          detail:
            "Server misconfiguration: set INTERNAL_API_URL in Vercel to your public FastAPI base URL (HTTPS, no trailing slash).",
        },
        { status: 503 }
      );
    }
  }
  const base = baseRaw;
  const internalKey = process.env.INTERNAL_API_KEY?.trim() || "";

  const formData = await req.formData();

  const headers: HeadersInit = {};
  if (internalKey) {
    headers["X-Internal-Key"] = internalKey;
  }

  const upstream = await fetch(`${base}/api/analyze`, {
    method: "POST",
    body: formData,
    headers,
  });

  const text = await upstream.text();
  const contentType = upstream.headers.get("content-type") || "application/json";
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "content-type": contentType },
  });
}
