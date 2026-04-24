import { timingSafeEqual } from "node:crypto";

function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

function loadMap(): Map<string, string> {
  const raw = process.env.AUTH_USERS?.trim();
  if (!raw) return new Map();
  try {
    const obj = JSON.parse(raw) as Record<string, string>;
    const m = new Map<string, string>();
    for (const [k, v] of Object.entries(obj)) {
      m.set(normalizeEmail(k), v);
    }
    return m;
  } catch {
    return new Map();
  }
}

function constantTimeEqual(a: string, b: string): boolean {
  const bufA = Buffer.from(a, "utf8");
  const bufB = Buffer.from(b, "utf8");
  if (bufA.length !== bufB.length) return false;
  return timingSafeEqual(bufA, bufB);
}

export function verifyCredentials(email: string, password: string): boolean {
  const map = loadMap();
  const expected = map.get(normalizeEmail(email));
  if (expected === undefined) return false;
  return constantTimeEqual(password, expected);
}
