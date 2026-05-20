import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

const INTERNAL = "http://127.0.0.1:8000";

function isLocalhostUrl(u: string): boolean {
  try {
    const h = new URL(u).hostname;
    return h === "localhost" || h === "127.0.0.1" || h === "0.0.0.0" || h === "[::1]";
  } catch {
    return true;
  }
}

export function getInternalBase(): string {
  const baseRaw = process.env.INTERNAL_API_URL?.replace(/\/$/, "") || INTERNAL;
  if (process.env.NODE_ENV === "production") {
    if (!process.env.INTERNAL_API_URL?.trim() || isLocalhostUrl(baseRaw)) {
      throw new Error("INTERNAL_API_URL misconfigured");
    }
  }
  return baseRaw;
}

export async function requireUserEmail(req: NextRequest): Promise<string | NextResponse> {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  const email = await verifySessionToken(token);
  if (!email) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  return email;
}

export function internalHeaders(email?: string): HeadersInit {
  const headers: Record<string, string> = {};
  const internalKey = process.env.INTERNAL_API_KEY?.trim() || "";
  if (internalKey) headers["X-Internal-Key"] = internalKey;
  if (email) headers["X-User-Email"] = email;
  return headers;
}

export async function proxyResponse(upstream: Response): Promise<NextResponse> {
  const text = await upstream.text();
  const contentType = upstream.headers.get("content-type") || "application/json";
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "content-type": contentType },
  });
}

export function misconfigResponse(): NextResponse {
  return NextResponse.json(
    {
      detail:
        "Server misconfiguration: set INTERNAL_API_URL in Vercel to your public FastAPI base URL (HTTPS, no trailing slash).",
    },
    { status: 503 }
  );
}
