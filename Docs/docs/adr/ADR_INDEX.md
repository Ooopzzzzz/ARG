---
title: Architecture Decision Record Index
version: 1.0
status: active
owner: Architecture
created: 2026-10-10
updated: 2026-10-10
tags: [arg, adr]
related: [[SAD]], [[TDD]]
---

# Decision process
Create an ADR when a decision changes module boundaries, data contracts, security invariants, operational requirements, or future migration cost. Accepted ADRs are immutable; supersede them with a new ADR.

## ADR-001 — Modular monolith for MVP
- **Status:** Accepted
- **Decision:** One FastAPI application with explicit modules, PostgreSQL, and separate Next.js UI.
- **Context:** Early-stage system; correctness and iteration speed dominate distributed scaling needs.
- **Trade-off:** Lower operational complexity; requires discipline to preserve module boundaries.

## ADR-002 — Deterministic policy engine first
- **Status:** Accepted
- **Decision:** Use typed policy rules and deterministic evaluation in MVP; do not let an LLM make the final enforcement decision.
- **Context:** Runtime governance decisions must be testable and explainable.
- **Trade-off:** Less expressive than natural-language policy interpretation; safer and easier to validate for the initial scope.

## ADR-003 — Mock executor before live connectors
- **Status:** Accepted
- **Decision:** The MVP ships with a mock target adapter only.
- **Context:** Real connectors introduce credentials, irreversible side effects, and integration-specific failure semantics.
- **Trade-off:** Demonstrates enforcement mechanics, not production integration reliability.

## ADR-004 — PostgreSQL as initial source of truth
- **Status:** Accepted
- **Decision:** Persist policies, requests, decisions, approvals, grants, executions, and audit events in PostgreSQL.
- **Context:** Strong constraints and transactions are useful for tenant isolation, idempotency, and grant consumption.
- **Trade-off:** Audit write throughput may eventually require partitioning or a separate analytics pipeline.

## ADR-005 — Fail closed on uncertainty
- **Status:** Accepted
- **Decision:** Missing policy, failed audit write, invalid identity, or unresolved grant state never authorizes execution.
- **Context:** Availability must not silently override governance.
- **Trade-off:** Some legitimate actions may be blocked during dependency failures.

## Proposed future ADRs
- OIDC/SSO provider and operator session design.
- Audit hash chaining and external anchoring.
- OPA/Rego adoption versus typed in-process policy engine.
- Connector framework and per-adapter idempotency.
- Data retention and tenant-specific deletion.
- Production deployment model and SLOs.
