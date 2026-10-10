import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { hasOperatorSession, sameOrigin } from "@/lib/operator-session";

const scenarios = {
  routine: {
    type: "customer.record.update",
    target: "demo-crm/customer/1042",
    parameters: { status: "review_required" },
    environment: "development",
    data_classification: "internal",
    impact: { amount: 0, currency: "INR" },
  },
  high_impact: {
    type: "customer.record.update",
    target: "demo-crm/customer/2088",
    parameters: { status: "refund_requested" },
    environment: "production",
    data_classification: "confidential",
    impact: { amount: 5000, currency: "INR" },
  },
  restricted: {
    type: "customer.record.delete",
    target: "demo-crm/customer/2088",
    parameters: { reason: "retention_hold" },
    environment: "production",
    data_classification: "restricted",
    impact: { amount: 0, currency: "INR" },
  },
} as const;

export async function POST(request: NextRequest) {
  if (!hasOperatorSession(request) || !sameOrigin(request)) {
    return NextResponse.json({ detail: "Operator session required" }, { status: 401 });
  }
  const apiUrl = process.env.API_URL;
  const agentKey = process.env.ARG_DEMO_AGENT_KEY;
  if (!apiUrl || !agentKey) {
    return NextResponse.json({ detail: "Demo agent configuration is missing" }, { status: 503 });
  }
  const input: { scenario?: keyof typeof scenarios; agent_id?: string } = await request.json();
  const action = input.scenario ? scenarios[input.scenario] : undefined;
  if (!action || !input.agent_id) {
    return NextResponse.json({ detail: "Choose a supported scenario and registered demo agent" }, { status: 422 });
  }
  const response = await fetch(`${apiUrl}/api/v1/runtime/decisions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${agentKey}`,
      "Content-Type": "application/json",
      "Idempotency-Key": randomUUID(),
    },
    body: JSON.stringify({ agent_id: input.agent_id, action }),
    cache: "no-store",
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
