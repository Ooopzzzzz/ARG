---
title: ARG Threat Model
version: 1.0
status: initial-review-required
owner: Security Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, threat-model, stride]
related: [[SECURITY_BASELINE]], [[SAD]], [[TEST_STRATEGY]]
---

# 1. Assets
- Target-system credentials and capabilities.
- Tenant data and policy configuration.
- Runtime request/action payloads.
- Approval authority and execution grants.
- Agent API keys and operator sessions.
- Audit evidence and policy versions.
- Service availability and decision integrity.

# 2. Adversaries
- Malicious or compromised agent.
- Prompt-injection content that manipulates an agent's proposed actions.
- Malicious tenant user attempting privilege escalation.
- Cross-tenant attacker.
- Insider with excessive permissions.
- Compromised dependency or leaked credential.
- Operator error or stale policy configuration.

# 3. Trust assumptions
ARG can only mediate actions routed through its enforcement boundary. The MVP's mock adapter does not prove safety for arbitrary third-party APIs. Database administrators and infrastructure administrators may have privileges beyond application controls; tamper evidence is not equivalent to absolute immutability.

# 4. Threat register
| ID | Threat | Severity | Mitigation | Verification |
|---|---|---:|---|---|
| T-01 | Agent bypasses ARG and calls target directly | Critical | Keep target credentials away from agent; route execution through controlled adapter; document connector boundary | Architecture review and credential inspection |
| T-02 | Cross-tenant data access via guessed ID | Critical | Tenant-scoped repositories, authorization dependencies, optional DB RLS later | Cross-tenant API tests |
| T-03 | Replayed or modified approved action | Critical | Canonical action hash, expiry, one-time grant, atomic consume, policy re-evaluation | Replay and payload-tampering tests |
| T-04 | Disabled/revoked agent still acts | High | Credential revocation and agent status checked per request and execution | Revocation integration test |
| T-05 | Explicit DENY overridden by ALLOW rule | Critical | Fixed precedence: deny > approval > allow; default deny | Policy precedence property tests |
| T-06 | Policy store unavailable leads to allow | Critical | Fail closed; no execution on missing/invalid policy | Fault injection test |
| T-07 | Audit write fails but execution continues | Critical | Require durable audit/decision commit before execution | DB failure injection |
| T-08 | Approval spoofing or self-approval | High | Operator identity from auth; RBAC; configurable separation of duties | Authorization tests |
| T-09 | Prompt injection induces dangerous tool request | High | Treat action as untrusted; deterministic policy and data classification; target credentials isolated | Adversarial scenario tests |
| T-10 | Sensitive payload leaked through logs/export | High | Redaction, minimization, role checks, export limits | Log scanning and access tests |
| T-11 | Idempotency key reused with different payload | High | Unique key plus request hash; return 409 | API test |
| T-12 | Concurrent duplicate execution | Critical | Atomic grant consumption and target idempotency | Concurrency test |
| T-13 | Policy author activates unsafe policy | High | Draft validation, immutable versions, audit activation; future dual control | Policy activation tests |
| T-14 | Malicious dependency or supply-chain compromise | High | Lockfiles, dependency scanning, minimal images, review updates | CI security scan |
| T-15 | Denial of service via large payloads or repeated decisions | Medium/High | Limits, rate limits, bounded queries, DB indexes | Load/abuse tests |
| T-16 | Audit hash chain is misrepresented as immutable | Medium | Precise claims; verify chain; external anchor only in later hardening | Documentation review |

# 5. Abuse cases
- Agent submits `production` action with omitted classification.
- Agent asks to execute a different payload using an already approved request ID.
- Operator from tenant A approves a request from tenant B.
- A policy contains contradictory allow and deny rules.
- Policy is changed between approval and execution.
- Two execute calls race for the same grant.
- PostgreSQL becomes unavailable after decision but before executor authorization.
- Audit export attempts to retrieve all tenants' events.
- A target adapter returns timeout after an unknown side effect.

# 6. Required security tests before MVP release
All T-02 through T-12 must have automated tests. T-01 must be addressed by architecture and documented deployment assumptions. No unresolved critical finding may be accepted without explicit owner and mitigation plan.
