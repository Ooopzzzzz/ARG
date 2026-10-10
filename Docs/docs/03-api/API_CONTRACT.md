---
title: ARG API Contract
version: 1.0
status: baseline
owner: Backend Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, api, rest]
related: [[PRD]], [[TDD]], [[DATA_MODEL]]
---

# 1. API conventions
- Prefix: `/api/v1`.
- Content type: `application/json`.
- Timestamps: RFC 3339 UTC.
- IDs: UUIDv4/UUIDv7 strings.
- Authentication: `Authorization: Bearer <agent_api_key>` for agent endpoints; operator auth is separate and must not reuse agent keys.
- Tenant ID is derived from authentication. Do not trust `tenant_id` supplied in a request body.
- All mutation endpoints require authorization and emit audit events.
- Use bounded pagination; maximum page size 100.
- Include `X-Request-ID` in responses. Accept a client request ID only after validation or generate one.
- Agent mutation requests require `Idempotency-Key`.

# 2. Runtime request
`POST /api/v1/runtime/decisions`

Request:
```json
{
  "agent_id": "uuid",
  "action": {
    "type": "record.update",
    "target": "demo-crm/customer/123",
    "parameters": {"status": "review_required"},
    "environment": "development",
    "data_classification": "internal",
    "impact": {"amount": 0, "currency": "INR"}
  },
  "context": {
    "user_id": "operator-or-service-principal",
    "purpose": "customer record correction"
  }
}
```
The `agent_id` must match the authenticated credential's registered agent. The action target is an identifier, not a URL that the API fetches. The API must not fetch arbitrary URLs from request parameters.

Response:
```json
{
  "request_id": "uuid",
  "decision": "REQUIRE_APPROVAL",
  "reason_codes": ["POLICY_APPROVAL_REQUIRED"],
  "policy_version_id": "uuid",
  "risk": {"score": 62, "factors": [{"name": "impact", "points": 0, "reason": "No financial impact declared"}]},
  "approval_id": "uuid",
  "expires_at": "2026-10-10T12:00:00Z"
}
```
`approval_id` is omitted unless approval is required. `expires_at` is the decision/grant expiry as appropriate.

# 3. Execution
`POST /api/v1/runtime/requests/{request_id}/execute`
- Agent credential must own the request, unless an explicitly authorized operator action is designed later.
- Request body contains no action mutation; server loads the canonical action from storage.
- Only a valid `ALLOW` grant or approved, re-evaluated request can execute.
- Returns `EXECUTED`, `EXECUTION_FAILED`, or `UNKNOWN_OUTCOME`.
- In the MVP this calls only the mock adapter.

# 4. Approvals
- `GET /api/v1/approvals?status=PENDING&cursor=...`
- `GET /api/v1/approvals/{approval_id}`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`

Approver identity comes from operator authentication, never from the body. Approval request may include a short rationale. Rejecting requires a reason code or rationale.

# 5. Agents
- `POST /api/v1/agents`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `POST /api/v1/agents/{agent_id}/disable`
- `POST /api/v1/agents/{agent_id}/rotate-key`

New agent key is returned only once. Never expose stored key material.

# 6. Policies
- `POST /api/v1/policies` creates a draft.
- `POST /api/v1/policies/{policy_id}/validate`
- `POST /api/v1/policies/{policy_id}/activate`
- `GET /api/v1/policies`
- `GET /api/v1/policies/{policy_id}/versions`

Policy versions are immutable after activation.

# 7. Audit
`GET /api/v1/audit-events?request_id=&agent_id=&decision=&from=&to=&cursor=&limit=`
- Requires operator role.
- Results are tenant-scoped.
- Raw secrets and unnecessary sensitive parameters are excluded.
- Audit export is P1, not required for first vertical slice.

# 8. Platform endpoints
- `GET /health/live`: process is alive.
- `GET /health/ready`: process and required dependencies are ready.
- `GET /metrics`: internal deployment only; never expose unrestricted metrics publicly.

# 9. Error codes
- `400 INVALID_REQUEST`
- `401 UNAUTHENTICATED`
- `403 FORBIDDEN`
- `404 NOT_FOUND`
- `409 CONFLICT`, `IDEMPOTENCY_KEY_REUSED`, `INVALID_STATE_TRANSITION`
- `422 VALIDATION_ERROR`
- `429 RATE_LIMITED`
- `500 INTERNAL_ERROR`
- `503 POLICY_UNAVAILABLE`, `DEPENDENCY_UNAVAILABLE`

Business decisions (`DENY`) are successful decision evaluations, not HTTP errors. Infrastructure failures are errors and must never permit execution.

# 10. Compatibility
Breaking changes require a new API version or a documented migration window. Additive optional fields are preferred. The OpenAPI file is a starting schema and must be kept aligned with implementation.
