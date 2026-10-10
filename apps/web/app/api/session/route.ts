import { NextRequest, NextResponse } from "next/server";
import { hasOperatorSession, sameOrigin, sessionCookieValue, SESSION_COOKIE, verifyOperatorToken } from "@/lib/operator-session";

export async function GET(request: NextRequest) {
  return NextResponse.json({ authenticated: hasOperatorSession(request) });
}

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ detail: "Origin rejected" }, { status: 403 });
  let input: { token?: string };
  try {
    input = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }
  if (!input.token || !verifyOperatorToken(input.token)) {
    return NextResponse.json({ detail: "Operator token is invalid" }, { status: 401 });
  }
  const value = sessionCookieValue();
  if (!value) return NextResponse.json({ detail: "Operator authentication is not configured" }, { status: 503 });
  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(SESSION_COOKIE, value, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.COOKIE_SECURE === "true",
    path: "/",
    maxAge: 28_800,
  });
  return response;
}

export async function DELETE(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ detail: "Origin rejected" }, { status: 403 });
  const response = NextResponse.json({ authenticated: false });
  response.cookies.set(SESSION_COOKIE, "", { httpOnly: true, sameSite: "strict", path: "/", maxAge: 0 });
  return response;
}
