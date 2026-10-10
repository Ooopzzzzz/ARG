import { NextRequest, NextResponse } from "next/server";
import { hasOperatorSession, sameOrigin } from "@/lib/operator-session";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  if (!hasOperatorSession(request)) {
    return NextResponse.json({ detail: "Operator sign-in required" }, { status: 401 });
  }
  if (request.method !== "GET" && !sameOrigin(request)) {
    return NextResponse.json({ detail: "Origin rejected" }, { status: 403 });
  }
  const { path } = await context.params;
  const apiUrl = process.env.API_URL;
  const operatorToken = process.env.OPERATOR_TOKEN;
  if (!apiUrl || !operatorToken) {
    return NextResponse.json({ detail: "Server API configuration is missing" }, { status: 503 });
  }
  const endpoint = `${apiUrl}/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const body = request.method === "GET" ? undefined : await request.text();
  const response = await fetch(endpoint, {
    method: request.method,
    headers: { Authorization: `Bearer ${operatorToken}`, "Content-Type": "application/json" },
    body,
    cache: "no-store",
  });
  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

export const GET = proxy;
export const POST = proxy;
