---
title: ARG Data Model
version: 1.0
status: baseline
owner: Backend Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, database, schema]
related: [[SAD]], [[TDD]], [[SECURITY_BASELINE]]
---

# 1. General rules
- PostgreSQL is the source of truth for MVP state.
- UUID primary keys; UTC timestamps; `created_at` and `updated_at` where applicable.
- Every tenant-owned row has `tenant_id NOT NULL`.
- Use foreign keys and uniqueness constraints, not application checks alone.
- Keep active policy version separate from immutable policy-version records.
- Avoid storing raw API keys, access tokens, full confidential documents, or unnecessary action payload fields.

# 2. Entities
## organizations
`id, name, status, created_at`

## principals
`id, tenant_id, principal_type (operator|service), subject, role, status, created_at`
Unique constraint appropriate to `(tenant_id, principal_type, subject)`.

## agents
`id, tenant_id, name, status, key_digest, key_prefix, created_by, created_at, disabled_at, last_used_at`
Never store the raw agent key. Key rotation invalidates the prior key.

## policies
`id, tenant_id, name, description, active_version_id, created_by, created_at`

## policy_versions
`id, tenant_id, policy_id, version_number, status (draft|active|retired), schema_version, document_json, content_hash, created_by, created_at, activated_at`
Unique `(policy_id, version_number)`. Active version changes through an atomic operation.

## runtime_requests
`id, tenant_id, agent_id, idempotency_key, request_hash, action_type, target, canonical_action_json, context_json_redacted, state, created_at, expires_at`
Unique `(tenant_id, idempotency_key)`. Define retention and payload minimization before pilot use.

## decisions
`id, tenant_id, request_id, decision, reason_codes_json, policy_version_id, risk_score, risk_factors_json, decision_version, created_at, expires_at`
One or more decisions may exist if explicit re-evaluation is supported; retain history rather than overwrite.

## approvals
`id, tenant_id, request_id, action_hash, policy_version_id, status, expires_at, requested_at, decided_at, approver_principal_id, rationale_redacted`
Approval state transitions must be atomic.

## execution_grants
`id, tenant_id, request_id, action_hash, policy_version_id, status, expires_at, consumed_at, created_at`
Unique/conditional state transition ensures one-time consumption.

## executions
`id, tenant_id, request_id, grant_id, adapter_name, status, idempotency_key, result_redacted_json, started_at, completed_at`
Unique `(tenant_id, idempotency_key)` for mock executor; use adapter-specific idempotency for real integrations.

## audit_events
`id, tenant_id, sequence_number, event_type, actor_type, actor_id, request_id, occurred_at, payload_redacted_json, previous_hash, event_hash`
Per-tenant sequence or equivalent ordering. Hash chaining is an optional hardening step; if implemented, define canonical event serialization and key management. Application interfaces must not offer update/delete operations.

# 3. Indexes
- All tenant-owned tables: `(tenant_id, id)`.
- `runtime_requests(tenant_id, created_at DESC)`.
- `runtime_requests(tenant_id, agent_id, created_at DESC)`.
- `decisions(tenant_id, decision, created_at DESC)`.
- `approvals(tenant_id, status, requested_at DESC)`.
- `audit_events(tenant_id, occurred_at DESC)`.
- Unique constraints listed above.

# 4. Tenant isolation
Repository methods must require tenant ID explicitly. Never fetch a record by ID alone for a tenant-owned entity. Consider PostgreSQL Row-Level Security for a later hardening stage; application-level tenant scoping is mandatory from the first commit.

# 5. Audit retention
MVP default is configurable retention for local synthetic data. Before handling real customer data, define retention, legal hold, deletion, export, backup, and regional residency requirements with the customer. Audit records can themselves contain sensitive information.

# 6. Migration policy
Use Alembic migrations. Every schema change includes an upgrade path and, where practical, downgrade. Production migrations must be backward-compatible with the currently deployed application version or executed as a coordinated release.
