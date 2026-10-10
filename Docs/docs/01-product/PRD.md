---
title: Product Requirements Document — ARG MVP
version: 1.0
status: baseline-for-implementation
owner: Product
created: 2026-10-10
updated: 2026-10-10
tags: [arg, prd, requirements]
related: [[PROJECT_BASELINE]], [[SAD]], [[API_CONTRACT]], [[TEST_STRATEGY]]
---

# 1. Executive summary
ARG provides a controlled decision and enforcement layer between an AI agent and a target system. The MVP proves one end-to-end flow: register an agent, submit an action proposal, evaluate policy and risk, require approval when appropriate, and execute only through a controlled mock adapter after authorization.

# 2. Problem
AI agents can use tools and APIs to create external side effects. Existing access controls answer identity and permissions questions but may not express action-specific business conditions, approval requirements, or a consistent decision trail across agent workflows. ARG aims to make these action-level decisions explicit and reviewable.

# 3. Goals
- Evaluate proposed actions before controlled execution.
- Enforce tenant-scoped identity and agent status.
- Apply deterministic, versioned policies.
- Return one of three explicit decisions: allow, deny, require approval.
- Explain each decision with reason codes.
- Preserve a queryable audit trail of requests, decisions, approvals, and execution outcomes.
- Demonstrate that approval is bound to a specific action and cannot be reused for a changed payload.
- Provide a developer API and a minimal operator interface.

# 4. Non-goals
See `PROJECT_BASELINE.md`. In particular, the MVP is not a universal proxy for every enterprise API and does not guarantee governance when an agent can bypass ARG.

# 5. Personas
## P1 — Agent developer
Integrates an agent with ARG and needs predictable schemas, low-friction local setup, and a clear response on whether an action may proceed.

## P2 — Security/platform operator
Registers agents, configures policies, reviews audit events, and needs to understand why a decision occurred.

## P3 — Approver
Reviews a pending action, its normalized summary and risk factors, then approves or rejects it.

## P4 — Auditor/reviewer
Searches decisions and approval events and verifies that actions followed the recorded policy path.

# 6. MVP user stories
- As an operator, I can register and disable an agent so only known agents can submit requests.
- As an operator, I can create and activate a policy version with explicit conditions and effects.
- As a developer, I can submit an action proposal and receive a decision, reason codes, request ID, and policy version.
- As an operator, I can define thresholds that require human approval for high-impact actions.
- As an approver, I can approve or reject a pending action after inspecting its summary.
- As a developer, I can resume an approved action only if its action hash and approval token match the original request.
- As an auditor, I can search audit records by request, agent, decision, time range, and action type.
- As an operator, I can see when execution failed after a decision was allowed.
- As a developer, I can retry a request safely with an idempotency key.

# 7. Functional requirements
Priority: P0 = required for MVP, P1 = after the core vertical slice, P2 = later.

## FR-001 Tenant context (P0)
Every authenticated request is associated with one organization. Tenant context must come from verified credentials, not an arbitrary body field. Cross-tenant access returns a generic authorization error and must not reveal record existence.

## FR-002 Agent registry (P0)
Operators can create, list, disable, and rotate credentials for agents. Agent credentials are shown once and stored only as a strong hash. Disabled agents cannot submit requests.

## FR-003 Action schema (P0)
A request includes action type, target identifier, normalized parameters, declared data classification, environment, and an idempotency key. Payload size and field lengths are bounded. Arbitrary executable code is never accepted.

## FR-004 Policy versioning (P0)
Policies have immutable versions. Activating a new version does not mutate historical versions. Each decision records the exact policy version evaluated.

## FR-005 Policy evaluation (P0)
The policy engine evaluates typed conditions using deterministic logic. It supports at minimum:
- action type / target matching;
- amount threshold for numeric actions;
- environment matching;
- agent enabled state;
- explicit deny rules;
- approval-required rules;
- default-deny when no applicable policy grants permission.

## FR-006 Risk evaluation (P0)
A deterministic risk score (0–100) is calculated from configured, explainable factors. The score is advisory input to policy rules; it is not an ML prediction. Missing risk inputs must be handled conservatively and reported.

## FR-007 Decision response (P0)
Return `ALLOW`, `DENY`, or `REQUIRE_APPROVAL` with request ID, reason codes, evaluated policy version, risk score, and timestamp. Internal exceptions must not become `ALLOW`.

## FR-008 Approval lifecycle (P0)
A pending approval can be approved or rejected by an authenticated operator authorized for the tenant. Approval is bound to the request hash, tenant, agent, policy version, and expiry. Changed action content requires a new decision and approval.

## FR-009 Controlled execution (P0)
The mock executor checks the decision/approval state server-side immediately before simulating the side effect. It rejects missing, expired, revoked, mismatched, or already-consumed execution grants. It supports idempotent retries.

## FR-010 Audit records (P0)
Record request received, identity result, policy result, risk result, decision, approval transitions, execution attempt, execution result, and administrative policy/agent changes. Audit records are append-only through application interfaces.

## FR-011 Audit query/export (P1)
Operators can filter by time, agent, action type, decision, and request ID. Export JSONL or CSV with access control and size limits.

## FR-012 Minimal dashboard (P0)
Provide pages for overview, agents, policies, pending approvals, and audit events. The UI must show loading, empty, error, and permission-denied states.

## FR-013 Health/readiness (P0)
Expose liveness and readiness endpoints. Readiness verifies required dependencies such as PostgreSQL.

## FR-014 Security controls (P0)
Use request validation, authentication, tenant authorization, secret hashing, secure headers, bounded request sizes, rate limits for public-facing deployments, and redaction of sensitive data from logs.

# 8. Decision semantics
- `ALLOW`: the request satisfies policy and may be executed only through the controlled executor before the decision expires.
- `DENY`: the action must not execute. No approval resume is available unless a new request is submitted under changed policy.
- `REQUIRE_APPROVAL`: execution is paused. Approval is a separate state transition and is not itself execution.
- Any missing/invalid policy state, identity uncertainty, timeout, or unexpected internal error results in no execution. The API may return an error instead of a business decision, but must never imply permission.

# 9. Acceptance criteria
- AC-01: An unregistered or disabled agent cannot receive `ALLOW`.
- AC-02: A request that violates an explicit deny rule returns `DENY` and creates audit events.
- AC-03: A request meeting an approval rule returns `REQUIRE_APPROVAL`; the mock executor does not execute it.
- AC-04: An approved request can execute once; duplicate retries return the original outcome without repeating the side effect.
- AC-05: Changing the action parameters after approval invalidates the grant.
- AC-06: A request with no matching allow policy is denied.
- AC-07: Every completed decision identifies the policy version and reason codes.
- AC-08: Cross-tenant reads and writes are rejected.
- AC-09: Database/policy evaluation failure never causes execution.
- AC-10: Audit entries for decisions and approval transitions are queryable.
- AC-11: Automated tests cover allow, deny, approval, expiry, replay, disabled agent, and tenant isolation.
- AC-12: A clean clone can run the local stack using the documented setup.

# 10. Success metrics for the prototype
- 100% pass rate on the defined deterministic policy test suite.
- 100% of decision outcomes have an audit record in the same transaction boundary or a clearly surfaced failure.
- Zero unauthorized executions in the adversarial acceptance suite.
- P95 policy-decision latency target: under 100 ms in local test environment, excluding external integrations; measure rather than assume.
- Local developer setup completed in under 30 minutes on a supported machine.
These are targets, not measured results.

# 11. Risks
- Integration bypass makes enforcement incomplete.
- Incorrect policy semantics can block legitimate work or allow unsafe work.
- Human approvals can be spoofed, replayed, or applied to changed actions if not bound cryptographically and transactionally.
- Audit logs may contain sensitive information if payload minimization is ignored.
- Excessive approval prompts can lead to approval fatigue.

# 12. Release gate
Do not call the MVP complete until AC-01 through AC-12 pass, the threat model has no unmitigated critical finding, and a clean local deployment is reproducible.
