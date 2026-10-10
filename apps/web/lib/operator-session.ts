import { createHmac, timingSafeEqual } from "node:crypto";
import { NextRequest } from "next/server";

export const SESSION_COOKIE = "arg_operator_session";

function equal(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

export function hasOperatorSession(request: NextRequest): boolean {
  const received = request.cookies.get(SESSION_COOKIE)?.value;
  const token = process.env.OPERATOR_TOKEN;
  if (!token || !received) return false;
  const [expiresAt, signature] = received.split(".");
  const expiry = Number(expiresAt);
  if (!Number.isFinite(expiry) || expiry <= Date.now() || !signature) return false;
  const expected = createHmac("sha256", token).update(`arg-operator-console:${expiresAt}`).digest("hex");
  return equal(expected, signature);
}

export function sameOrigin(request: NextRequest): boolean {
  return request.headers.get("origin") === request.nextUrl.origin;
}

export function sessionCookieValue(): string | null {
  const token = process.env.OPERATOR_TOKEN;
  if (!token) return null;
  const expiresAt = String(Date.now() + 28_800_000);
  const signature = createHmac("sha256", token).update(`arg-operator-console:${expiresAt}`).digest("hex");
  return `${expiresAt}.${signature}`;
}

export function verifyOperatorToken(candidate: string): boolean {
  const expected = process.env.OPERATOR_TOKEN;
  return Boolean(expected && equal(expected, candidate));
}
