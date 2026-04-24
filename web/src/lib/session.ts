import { SignJWT } from "jose/jwt/sign";
import { jwtVerify } from "jose/jwt/verify";

export const SESSION_COOKIE = "brightr_session";

function getSecretKey() {
  const s = process.env.AUTH_SECRET?.trim();
  if (s && s.length >= 16) {
    return new TextEncoder().encode(s);
  }
  if (process.env.NODE_ENV === "development") {
    return new TextEncoder().encode("dev-brightr-auth-secret-min-32-chars!");
  }
  return new TextEncoder().encode("");
}

export async function createSessionToken(
  email: string,
  remember: boolean
): Promise<string> {
  const e = email.trim().toLowerCase();
  const exp = remember ? "7d" : "12h";
  const key = getSecretKey();
  if (key.length === 0) {
    throw new Error("AUTH_SECRET must be set (min 16 characters)");
  }
  return new SignJWT({ sub: e })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(exp)
    .sign(key);
}

export async function verifySessionToken(
  token: string | undefined | null
): Promise<string | null> {
  if (!token) return null;
  try {
    const key = getSecretKey();
    if (key.length === 0) return null;
    const { payload } = await jwtVerify(token, key);
    const sub = payload.sub;
    return typeof sub === "string" ? sub : null;
  } catch {
    return null;
  }
}

export function getSessionMaxAgeSec(remember: boolean) {
  return remember ? 7 * 24 * 60 * 60 : 12 * 60 * 60;
}
