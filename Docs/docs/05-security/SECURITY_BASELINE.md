---
title: ARG Security Baseline
version: 1.0
status: mandatory-for-mvp
owner: Security Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, security]
related: [[THREAT_MODEL]], [[SAD]], [[TEST_STRATEGY]]
---

# 1. Security objective
Prevent unauthorized or policy-violating actions from executing through the ARG-controlled path, preserve evidence of decisions, and limit exposure if a component is compromised.

# 2. Authentication
- Agent keys are high-entropy random secrets, shown once.
- Store a strong hash (Argon2id) or a keyed digest designed for lookup; keep any HMAC pepper outside the database.
- Support key rotation and immediate revocation.
- Operator authentication is separate from agent authentication. Local development may use a documented dev-only operator mechanism; never ship a shared default credential.
- Production should use OIDC/SSO and MFA where supported.

# 3. Authorization
- Deny by default.
- Enforce role and tenant scope server-side on every request.
- Approval requires an approver role and tenant match.
- Agent keys cannot access operator endpoints.
- Never trust user-supplied tenant ID, role, approver ID, or agent ownership.
- Separate policy author, policy activator, approver, and auditor roles where operationally appropriate.

# 4. Execution boundary
- Target credentials are held by the executor/connector, not the agent.
- The executor loads the canonical action from storage; it does not accept a modified action from the execute call.
- Validate action hash, tenant, request owner, decision state, expiry, policy version, and grant consumption atomically.
- Re-evaluate policy after approval and before execution.
- Use target-side idempotency where available.
- Do not connect the MVP to production systems or money movement.

# 5. Input and output
- Pydantic schemas use strict validation and reject unknown fields where feasible.
- Limit body size, string lengths, nested structures, and parameter count.
- Treat all action parameters, retrieved content, and connector responses as untrusted data.
- Do not allow arbitrary URL fetching or shell execution through generic action parameters.
- Escape UI output and avoid rendering untrusted content as HTML.

# 6. Secrets and cryptography
- `.env` is ignored by Git; `.env.example` contains placeholders only.
- Use TLS outside localhost.
- Use a secret manager for production credentials.
- Rotate keys and document emergency revocation.
- Use established cryptographic libraries; do not design custom encryption.
- Hash-chain audit records only with canonical serialization and verification tests.

# 7. Logging and privacy
- Never log API keys, authorization headers, passwords, session cookies, or raw secrets.
- Minimize sensitive action payloads in audit events; prefer field summaries and hashes.
- Redact confidential values before persistence/logging.
- Restrict audit search/export and monitor bulk access.
- Do not send customer payloads to third-party LLMs in the MVP.

# 8. Application and infrastructure
- Use dependency pinning and vulnerability scanning.
- Run the application as a non-root user in containers.
- PostgreSQL is not exposed publicly in production.
- CORS allowlist is explicit.
- Rate limiting is required before public or multi-customer exposure.
- Use secure headers and CSRF protections if cookie-based browser sessions are used.
- Backups must be encrypted and restore-tested before production.
- Production requires threat review, penetration testing, incident response contacts, and a rollback procedure.

# 9. Development rules
- No real customer secrets/data in tests or screenshots.
- No secrets committed to Git.
- No bypass flags that can accidentally enable execution in production.
- Mock adapter is the only enabled adapter by default.
- Any change to decision precedence, approval binding, grant consumption, tenant scoping, or audit semantics requires security review and regression tests.
