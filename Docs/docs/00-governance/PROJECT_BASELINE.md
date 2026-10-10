---
title: ARG Project Baseline
version: 1.0
status: implementation-baseline
owner: Product and Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, baseline, scope]
related: [[PRD]], [[SAD]], [[THREAT_MODEL]]
---

# Purpose
Freeze the minimum shared understanding required to begin implementation without confusing the long-term vision with the MVP.

# Product statement
ARG is a runtime governance service that evaluates an AI-agent-proposed action before a controlled executor performs it. It combines request validation, authenticated caller identity, agent registration, deterministic policy evaluation, risk classification, approval state, and tamper-evident audit events.

# Non-negotiable invariant
**No target-side effect may be performed by the reference executor unless the current request has a valid, unexpired, tenant-scoped ALLOW decision or a valid approval-resume decision.** A `REQUIRE_APPROVAL` response is not permission to execute.

This invariant only applies to integrations that route execution through ARG's enforcement boundary. ARG cannot control an agent that retains direct credentials to the target system.

# Known project facts
- The concept is model-agnostic; ARG does not train or host an LLM in the MVP.
- The system is intended to complement, not replace, IAM, enterprise applications, API gateways, SIEM, or GRC systems.
- Core capabilities are identity/context, policy evaluation, risk, approval, decision, and audit.
- The current prototype stack proposed in project materials is Next.js/TypeScript, FastAPI/Python, PostgreSQL, and Docker.
- Initial integration targets mentioned previously include Google Workspace, Slack, GitHub, and PostgreSQL. The first implementation must use a mock target adapter before live integrations.

# Assumptions to validate
1. The first useful demonstration can be built without production enterprise connectors.
2. The first test users are developers and security/platform reviewers who can submit controlled action requests.
3. Policies can be represented as typed deterministic conditions for the initial scope.
4. Approval is performed by a human through the ARG dashboard/API; no autonomous approval agent is included.
5. The MVP runs locally or in a developer environment with synthetic data.

# Scope freeze: MVP
- Organization/tenant boundary.
- Agent registry with enabled/disabled state.
- API-key authentication for registered agents in local development; keys stored as hashes.
- Action request validation using a versioned schema.
- Deterministic policy rules and explicit policy version.
- Rule-based risk score with explainable factors.
- Decisions: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`.
- Human approval lifecycle: pending, approved, rejected, expired.
- Audit event for every decision and approval transition.
- A mock executor that demonstrates enforcement and idempotency.
- Minimal operator UI for agents, policies, approvals, and audit search.
- Docker Compose development environment and automated tests.

# Explicitly out of scope
- Production certification or claims of guaranteed safety.
- Live money movement, real invoice approval, destructive production actions.
- Broad support for arbitrary enterprise connectors.
- Natural-language policy authoring or LLM-based policy decisions.
- ML anomaly detection, model training, or cross-customer learning.
- Multi-region HA, Kubernetes, service mesh, billing, SSO/SAML, and customer VPC deployment.
- Replacing IAM, DLP, EDR, SIEM, API gateways, or enterprise policy systems.

# Product principles
1. **Fail closed:** invalid identity, unavailable policy state, malformed input, or unresolved enforcement state must not result in execution.
2. **Deterministic core:** critical decisions are based on explicit rules, not free-form LLM output.
3. **Explainable decisions:** every decision includes reason codes and the policy version used.
4. **Tenant isolation:** all persisted business records are tenant-scoped.
5. **Audit first:** record the request, decision, policy version, approval events, and execution outcome without storing unnecessary sensitive payloads.
6. **Enforce at the boundary:** a decision endpoint alone is not an enforcement mechanism; execution adapters must verify the decision.
7. **Least privilege:** ARG's credentials should be narrower than the agent's intended capabilities.
8. **Incremental architecture:** prove a vertical slice before splitting into services.

# Open questions that do not block the local prototype
- Initial commercial vertical and buyer.
- Exact enterprise deployment model.
- Required compliance frameworks and data residency.
- Production identity provider and SSO.
- Target SLOs validated with pilot workloads.
- Which live connector should follow the mock adapter.

# Definition of “ready to start”
- Repository structure and stack agreed.
- PRD acceptance criteria testable.
- API schemas and decision semantics frozen for v0.
- Threat model and test plan included.
- Open questions tracked instead of silently assumed.
