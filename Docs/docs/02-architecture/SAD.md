---
title: System Architecture Document — ARG
version: 1.0
status: baseline-for-implementation
owner: Architecture
created: 2026-10-10
updated: 2026-10-10
tags: [arg, architecture, sad]
related: [[PRD]], [[TDD]], [[THREAT_MODEL]], [[DATA_MODEL]]
---

# 1. Architecture decision
Use a **modular monolith** for the MVP: one FastAPI application with explicit modules and one PostgreSQL database. The frontend is a separate Next.js application. Do not begin with microservices; the core challenge is correctness of the governance boundary, not service distribution.

# 2. Logical architecture
```text
Agent / SDK
    |
    v
FastAPI API boundary
    |-- Authentication & tenant context
    |-- Request validation / idempotency
    |-- Agent registry
    |-- Policy service -> deterministic policy evaluator
    |-- Risk evaluator
    |-- Decision service
    |-- Approval service
    |-- Enforcement / mock executor
    |-- Audit service
    |
    v
PostgreSQL (tenant-scoped records, immutable policy versions, audit events)

Next.js operator UI -> authenticated operator API
```

# 3. Trust boundaries
- TB1: Agent/client to API. Treat all payloads as untrusted.
- TB2: Operator UI to API. Operators are authenticated but not automatically authorized for every action.
- TB3: Policy/configuration management to runtime decision path. Only validated active versions may be evaluated.
- TB4: Decision service to executor. Re-check grant state at execution time.
- TB5: Application to database. Use least-privilege DB credentials, parameterized queries, and tenant-scoped repository methods.
- TB6: Logs and audit exports. Treat exports as sensitive data and restrict access.

# 4. Core modules
## API layer
Owns HTTP contracts, request parsing, response mapping, authentication dependencies, and error handling. It must not contain policy semantics.

## Identity and agent registry
Authenticates agent API keys and operator sessions. Maps credentials to tenant and principal. API-key secret is displayed once and stored as a salted strong hash (e.g., Argon2id). A keyed HMAC digest can be used for indexed lookup, with the HMAC key held outside the database.

## Policy service
Stores immutable policy versions and manages draft/activate operations. Runtime evaluation receives a resolved immutable policy snapshot.

## Policy evaluator
Pure deterministic function from `(action, principal, context, policy_version)` to matched rules and policy effect. No network calls, LLM calls, or database writes inside the evaluator.

## Risk evaluator
Computes a transparent score from configured factors. Risk is not treated as probability of harm. Store factor values and scoring version.

## Decision service
Coordinates identity, policy, risk, and approval requirement. Produces a typed decision object and reason codes.

## Approval service
Enforces approver permissions, state transitions, expiry, and action-hash binding. It cannot directly call target systems.

## Enforcement/executor
The only module allowed to invoke target adapters. For the MVP, use a mock adapter. It verifies the execution grant, request hash, tenant, expiry, policy version, and one-time consumption before action execution.

## Audit service
Appends structured events. Audit writes must be required for security-relevant transitions. Avoid raw secrets, credentials, and unnecessary full content.

## Frontend
Operator-only interface for agents, policy versions, approvals, and audit records. It is not a security boundary; the backend enforces all permissions.

# 5. Recommended stack
- Frontend: Next.js, React, TypeScript.
- Backend: Python 3.12+, FastAPI, Pydantic v2.
- Persistence: PostgreSQL.
- Migrations: Alembic.
- ORM: SQLAlchemy 2.x.
- Tests: pytest, HTTPX/TestClient; Playwright for essential UI flows.
- Packaging: Docker Compose.
- Lint/type: Ruff, mypy or pyright, ESLint, TypeScript strict mode.
- Policy MVP: typed Python policy evaluator with JSON policy schema. Consider OPA/Rego later after evaluating policy complexity and operational need.
- Cache/queue: none required initially; introduce only when measured requirements justify them.

# 6. Data flow and transaction boundaries
For each request:
1. Validate input and authenticate.
2. Begin transaction; enforce idempotency uniqueness.
3. Resolve active policy version.
4. Evaluate policy/risk deterministically.
5. Persist request, decision, and audit event(s).
6. Commit.
7. If decision is `ALLOW`, create an execution grant and invoke the mock executor through a separate controlled path.
8. Persist execution outcome with idempotency protection.

For audit integrity, an append-only application interface is the baseline. A database administrator can still alter records; stronger tamper evidence can be added using hash chaining, periodic external anchoring, and restricted DB permissions. Do not claim immutable storage unless the deployment actually provides it.

# 7. Security invariants
- Default deny if no policy explicitly permits an action.
- No execution on errors, timeouts, missing policy, or audit failure.
- Every grant is tenant-scoped, action-hash-bound, time-limited, and one-time.
- Approval is not an execution capability by itself.
- Target credentials are held by the executor/connector, not the agent.
- Every repository query includes tenant scope except explicitly global administrative queries.
- Secrets are never logged or committed.
- UI visibility does not substitute for server authorization.

# 8. Deployment topology
Local development: Docker Compose with `api`, `web`, and `postgres`. Production topology is not fixed by this document. Production would require managed secrets, TLS, backups, alerting, hardened identity, rate limiting, deployment rollback, and an independently reviewed security design.

# 9. Scalability strategy
Start with a single API process and PostgreSQL. Measure decision latency, DB contention, audit write throughput, and payload sizes. Scale stateless API replicas first. Partition audit data or introduce asynchronous analytics only when measurements justify it. Keep the synchronous decision/audit/enforcement path simple and reliable.

# 10. Architecture limitations
- The reference system cannot stop direct calls that bypass ARG.
- A mock adapter proves workflow semantics, not the reliability of third-party integrations.
- Hash-chained audit events only detect some tampering if verification and key management are implemented correctly; they do not prevent privileged database compromise.
- Risk scoring is a heuristic and must not be represented as a calibrated probability.
