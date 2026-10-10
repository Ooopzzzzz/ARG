---
title: ARG Implementation Plan
version: 1.0
status: ready-to-execute
owner: Engineering Lead
created: 2026-10-10
updated: 2026-10-10
tags: [arg, roadmap, delivery]
related: [[PRD]], [[SAD]], [[DEVELOPMENT_GUIDE]], [[TEST_STRATEGY]]
---

# Delivery principle
Build a vertical slice first. Do not build a polished dashboard, connector catalogue, or microservices before proving the decision-to-enforcement invariant.

# Milestone 0 — Repository foundation
Deliverables:
- Monorepo folders for API, web, docs, infra.
- Python/Node version policy and dependency lockfiles.
- Docker Compose for API, web, PostgreSQL.
- Environment validation, structured logs, health endpoints.
- CI pipeline.
Exit criteria: clean clone boots locally; health/readiness works; CI is green.

# Milestone 1 — Domain and persistence
Deliverables:
- SQLAlchemy models and Alembic migrations.
- Organizations, agents, policy versions, runtime requests, decisions, approvals, grants, executions, audit events.
- Tenant-scoped repositories.
Exit criteria: migrations apply from empty database; repository tenant tests pass.

# Milestone 2 — Deterministic decision core
Deliverables:
- Pydantic schemas.
- Canonical action hash.
- Policy schema validator.
- Pure policy evaluator and precedence rules.
- Explainable risk evaluator.
Exit criteria: unit/property tests cover all policy and risk cases; no LLM dependency.

# Milestone 3 — Runtime API and audit
Deliverables:
- Agent API-key authentication and revocation.
- Decision endpoint with idempotency.
- Atomic persistence of request, decision, and audit events.
- Standard error handling.
Exit criteria: API acceptance suite passes; failure injection confirms fail-closed behavior.

# Milestone 4 — Approval and enforcement
Deliverables:
- Approval queue and state transitions.
- Action-hash-bound, expiring execution grant.
- Mock adapter.
- Atomic one-time execution and duplicate handling.
Exit criteria: approval tampering, expiry, race, and replay tests pass.

# Milestone 5 — Operator interface
Deliverables:
- Agent list/register/disable.
- Policy create/validate/activate.
- Pending approvals.
- Audit event search.
Exit criteria: essential flows usable; backend remains authoritative for every permission.

# Milestone 6 — Hardening and demonstration
Deliverables:
- E2E tests, security tests, seeded demo policy and synthetic data.
- CI security scanning.
- Local deployment guide and demo script.
- Known limitations and architecture decision log.
Exit criteria: clean setup, repeatable demo, all P0 acceptance criteria met.

# Suggested sequencing
For a small team, milestones can be parallelized only after the API/domain contracts are agreed. Backend policy and enforcement work should not be blocked on UI polish.

# Definition of done for every feature
- Requirement and acceptance criteria linked.
- Schema/API changes documented.
- Tests include success, denial, and failure paths.
- Tenant scope and audit behavior reviewed.
- Logs redact sensitive fields.
- Migrations are reproducible.
- Lint/type/test gates pass.
- Documentation updated.
- No unsupported claims about production readiness.
