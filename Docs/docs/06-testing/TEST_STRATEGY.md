---
title: ARG Test Strategy
version: 1.0
status: required
owner: Quality Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, testing, qa]
related: [[PRD]], [[THREAT_MODEL]], [[IMPLEMENTATION_PLAN]]
---

# 1. Test layers
- Unit: policy evaluator, risk calculation, canonicalization, state transitions.
- Integration: API + PostgreSQL + migrations + authentication + audit.
- Contract: OpenAPI schemas and request/response compatibility.
- End-to-end: operator registers agent, creates policy, submits action, approves if needed, executes mock action, reviews audit.
- Security: tenant isolation, replay, malformed input, auth boundaries, secret leakage.
- Reliability: dependency failure, timeout, duplicate request, concurrent execute.
- Performance: decision latency and audit write throughput on synthetic payloads.

# 2. Mandatory scenario matrix
| Scenario | Expected result |
|---|---|
| Valid request matches ALLOW rule | ALLOW; audit exists; mock executor may execute |
| Explicit DENY and ALLOW both match | DENY |
| Approval rule matches | REQUIRE_APPROVAL; no execution |
| Pending approval rejected | execution permanently blocked for that request |
| Approval expired | no execution |
| Action changes after approval | grant invalid |
| Policy changes after approval | re-evaluation required; no stale execution |
| No policy matches | DENY / DEFAULT_DENY |
| Agent disabled after request | execution blocked |
| Agent key revoked | next request rejected |
| Wrong tenant requests another request ID | generic 404/403; no data leakage |
| Same idempotency key and same payload | original result returned |
| Same idempotency key and changed payload | 409 |
| Two concurrent execute requests | at most one side effect |
| Audit persistence fails | no execution |
| Policy store unavailable | no execution |
| Invalid risk input | reject or conservatively score; never lower risk silently |
| Target adapter timeout | explicit failed/unknown outcome; no blind duplicate retry |
| API key appears in logs | test fails |
| Pagination limit exceeded | validation error or capped result |

# 3. Property-based tests
- Any matching deny rule dominates any allow rule.
- Missing policy never produces ALLOW.
- Every execution has a valid decision and matching action hash.
- Every grant can be consumed at most once.
- Every tenant-scoped response belongs to authenticated tenant.
- Canonicalization produces the same hash for semantically equivalent object key order.
- Changing a policy-relevant action field changes the action hash.

# 4. CI gates
Every pull request:
1. Format/lint.
2. Static type checks.
3. Unit tests.
4. Integration tests with ephemeral PostgreSQL.
5. Migration consistency check.
6. OpenAPI validation.
7. Dependency vulnerability scan.
8. Secret scan.
9. Build backend and frontend.

# 5. Coverage
Use coverage as a diagnostic, not the only quality measure. Aim for at least 85% branch coverage on policy evaluation, approval transitions, grant validation, tenant authorization, and idempotency logic. All security invariants need direct tests regardless of aggregate coverage.

# 6. Release criteria
- All P0 acceptance criteria pass.
- No open critical security issues.
- Restore procedure tested for any non-local environment.
- API contract and migrations match code.
- Known limitations are documented.
- No real target credentials or production execution enabled by default.
