---
title: ARG User Flows and State Transitions
version: 1.0
status: baseline
owner: Product and Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, flows]
related: [[PRD]], [[API_CONTRACT]], [[DATA_MODEL]]
---

# 1. Standard action flow
1. Agent authenticates with its credential.
2. API derives tenant and agent identity from the credential.
3. API validates the action schema and idempotency key.
4. ARG loads the active policy version for that tenant.
5. Policy engine evaluates hard denies and applicable allow/approval rules.
6. Risk engine computes a deterministic score and reason factors.
7. Decision service produces `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`.
8. Request, decision, policy version, reasons, and risk factors are audited.
9. For `ALLOW`, the controlled executor verifies the grant again and executes the mock action.
10. Execution outcome is appended to the audit stream.

# 2. Approval flow
`PENDING -> APPROVED -> EXECUTED` or `PENDING -> REJECTED`. A pending approval may also become `EXPIRED` or `CANCELLED`.

Approval must bind to:
- tenant ID;
- request ID;
- canonical action hash;
- agent ID;
- policy version;
- expiration timestamp;
- approver identity.

On approval, re-evaluate current policy before execution. If the policy version changed or the current policy no longer permits execution, do not execute; require a fresh evaluation. This prevents stale approvals from silently overriding new policy.

# 3. Request state
`RECEIVED -> VALIDATED -> EVALUATED -> DECIDED -> [PENDING_APPROVAL] -> AUTHORIZED_TO_EXECUTE -> EXECUTED | EXECUTION_FAILED`

Terminal business outcomes: `DENIED`, `REJECTED`, `EXPIRED`, `EXECUTED`, `EXECUTION_FAILED`. Internal processing failures should be represented separately from business decisions.

# 4. Idempotency
The client sends an idempotency key per logical action. Store a unique `(tenant_id, idempotency_key)` and request hash. If the same key and same hash are repeated, return the original state/result. If the same key is reused with a different hash, return `409 IDEMPOTENCY_KEY_REUSED`.

# 5. Failure behavior
- Authentication failure: reject before policy evaluation.
- Disabled agent: reject and audit if identity is known.
- Invalid payload: `422`, no execution.
- Policy unavailable: `503`, no execution.
- Audit persistence failure: do not execute.
- Approval service unavailable: no execution.
- Executor timeout: mark outcome as unknown if side effect may have occurred; reconcile before retrying.
- Duplicate delivery: return original result and do not repeat side effect.

# 6. Operator flow
- Register agent and issue credential.
- Create a policy draft.
- Validate policy syntax and conflicts.
- Activate a new immutable policy version.
- Review pending approvals with action summary, risk factors, and applicable rules.
- Search audit trail to reconstruct a request's lifecycle.
