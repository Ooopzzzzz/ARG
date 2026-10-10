import { NextRequest, NextResponse } from "next/server";
import { hasOperatorSession, sameOrigin } from "@/lib/operator-session";

export async function POST(request: NextRequest) {
  if (!hasOperatorSession(request) || !sameOrigin(request)) {
    return NextResponse.json({ detail: "Operator session required" }, { status: 401 });
  }
  const apiUrl = process.env.API_URL;
  const agentKey = process.env.ARG_DEMO_AGENT_KEY;
  if (!apiUrl || !agentKey) {
    return NextResponse.json({ detail: "Demo agent configuration is missing" }, { status: 503 });
  }
  let body: { request_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }
  if (!body.request_id) {
    return NextResponse.json({ detail: "request_id is required" }, { status: 422 });
  }
  const response = await fetch(`${apiUrl}/api/v1/runtime/requests/${encodeURIComponent(body.request_id)}/execute`, {
    method: "POST",
    headers: { Authorization: `Bearer ${agentKey}` },
    cache: "no-store",
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
