import { NextResponse } from "next/server";
import { verifyCredentials } from "@/lib/auth-users";
import {
  createSessionToken,
  getSessionMaxAgeSec,
  SESSION_COOKIE,
} from "@/lib/session";

export async function POST(req: Request) {
  let body: { email?: string; password?: string; remember?: boolean };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const email = typeof body.email === "string" ? body.email : "";
  const password = typeof body.password === "string" ? body.password : "";
  const remember = Boolean(body.remember);

  if (!email || !password) {
    return NextResponse.json(
      { error: "Email and password are required" },
      { status: 400 }
    );
  }

  if (!verifyCredentials(email, password)) {
    return NextResponse.json({ error: "Invalid email or password" }, { status: 401 });
  }

  let token: string;
  try {
    token = await createSessionToken(email, remember);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Session error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: getSessionMaxAgeSec(remember),
  });
  return res;
}
