---
title: Technical Design Document — ARG MVP
version: 1.0
status: baseline
owner: Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, tdd, implementation]
related: [[SAD]], [[API_CONTRACT]], [[DATA_MODEL]]
---

# 1. Repository layout
```text
arg/
  apps/
    api/
      app/
        main.py
        core/                 # settings, logging, errors
        api/v1/               # routers and schemas
        auth/                 # agent and operator auth
        agents/
        policies/
        runtime/              # request, decision, risk, execution grant
        approvals/
        audit/
        adapters/mock.py
        db/                   # models, session, repositories
      migrations/
      tests/
      pyproject.toml
    web/
      app/
      components/
      lib/api-client.ts
      package.json
  docs/
  infra/
    docker-compose.yml
    .env.example
  scripts/
  .github/workflows/
```

# 2. Backend layering
- Router: HTTP concerns only.
- Schema: Pydantic request/response validation.
- Service: use-case orchestration and transaction boundary.
- Domain: enums, policy evaluator, risk function, state transitions.
- Repository: tenant-scoped persistence.
- Adapter: side effects to target systems; mock adapter only in MVP.
Avoid circular imports and do not put business rules in ORM models or route handlers.

# 3. Action request canonicalization
Create a stable canonical representation of:
`tenant_id, agent_id, action_type, target, parameters, environment, data_classification, policy_context`.
Canonical JSON must sort keys, normalize numeric representations, reject NaN/infinity, and use UTF-8. Compute SHA-256 over the canonical bytes. Do not hash volatile metadata such as request arrival time.

# 4. Policy model v0
A policy version contains:
- `id`, `tenant_id`, `version`, `status`, `created_by`, `created_at`;
- ordered rules with unique IDs;
- action matchers, optional target/environment matchers;
- conditions with typed operators;
- effect: `DENY`, `REQUIRE_APPROVAL`, or `ALLOW`;
- reason code and human-readable explanation.

Evaluation precedence:
1. Invalid policy or no active policy => no execution; return service error.
2. Any matching explicit DENY => DENY.
3. Any matching REQUIRE_APPROVAL => REQUIRE_APPROVAL.
4. At least one matching ALLOW and no higher-precedence match => ALLOW.
5. No matching rule => DENY (`DEFAULT_DENY`).
Rule ordering must not let a later ALLOW override an explicit DENY.

# 5. Risk score v0
Example deterministic factors (configurable and versioned):
- action sensitivity: 0–30;
- financial/impact magnitude: 0–30;
- environment: 0–20;
- data classification: 0–10;
- unusual context / missing required attributes: 0–10.
Clamp total to 0–100. Each factor returns `{factor, points, reason}`. Missing data must not silently reduce risk; either add conservative points or reject the request. Thresholds belong in policy, not hardcoded across modules.

# 6. Execution grant
Grant contains random opaque ID, tenant ID, request ID, action hash, policy version, expiry, and consumed timestamp. It is not a bearer secret exposed to untrusted clients without protection. The executor verifies it server-side and consumes it atomically. Use a database conditional update/row lock to prevent concurrent replay.

# 7. Approval transition
`PENDING -> APPROVED | REJECTED | EXPIRED | CANCELLED`. Only authorized operator may transition a pending record. Transition must be atomic and record approver ID and timestamp. Repeated same transition returns current state; conflicting transition returns 409.

# 8. Idempotent execution
Use unique constraints for tenant/idempotency key and execution grant. The executor transaction reserves execution before adapter invocation. For real external adapters, database transaction alone cannot guarantee exactly-once side effects; use target-side idempotency, outbox/reconciliation, or explicit `UNKNOWN_OUTCOME` handling.

# 9. Error model
Stable error object:
`{ "error": { "code": "...", "message": "...", "request_id": "..." } }`
Never return stack traces, SQL details, secret values, or internal policy payloads.

# 10. Configuration
All settings validated at startup. Fail startup when required secrets are missing outside development. No insecure production default secret. Use environment variables for local development and a secret manager in production.

# 11. Implementation order
1. Project skeleton, config, health checks, DB migration.
2. Tenant and agent API-key auth.
3. Agent registry.
4. Policy schema, validator, immutable versioning.
5. Pure policy evaluator and unit tests.
6. Risk evaluator and unit tests.
7. Runtime request/decision transaction and audit.
8. Approval lifecycle and action-hash binding.
9. Mock executor, grant consumption, idempotency/replay tests.
10. Operator API and minimal UI.
11. Docker Compose, CI, security tests, acceptance suite.
