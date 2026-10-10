---
title: ARG Observability and Runbook
version: 1.0
status: baseline
owner: Operations
created: 2026-10-10
updated: 2026-10-10
tags: [arg, operations, observability]
related: [[SAD]], [[SECURITY_BASELINE]], [[TEST_STRATEGY]]
---

# 1. Structured logs
Include timestamp, level, service, environment, request ID, trace/correlation ID, event name, duration, and safe error code. Include tenant/agent IDs only where appropriate and never log secrets or raw sensitive payloads.

# 2. Metrics
Minimum metrics:
- request count by endpoint and status;
- decision count by outcome and reason code;
- decision latency histogram;
- policy evaluation failures;
- approval queue size and age;
- execution outcomes and unknown outcomes;
- idempotency conflict count;
- audit write failures;
- authentication failures and rate-limit events;
- DB connection saturation and query latency.

Avoid high-cardinality labels containing request IDs, user IDs, or arbitrary targets.

# 3. Alerts for a future hosted deployment
- Any audit persistence failure in the decision/execution path.
- Any execution without a matching decision/grant.
- Sudden increase in DENY/approval rates.
- Repeated cross-tenant authorization failures.
- Agent key abuse or high request rate.
- Elevated unknown execution outcomes.
- Database unavailable or backup failure.

# 4. Incident playbooks
## Suspected unauthorized execution
1. Disable affected agent key and relevant adapter.
2. Preserve request IDs and audit evidence.
3. Stop execution for the affected tenant if scope is unclear.
4. Determine whether the target side effect occurred.
5. Rotate affected credentials.
6. Notify designated security owner and customer contact according to incident plan.
7. Document root cause and regression tests before re-enabling.

## Policy misconfiguration
1. Disable or roll back activation to a previously validated policy version.
2. Do not delete historical versions or audit events.
3. Identify requests evaluated under the affected version.
4. Review executed outcomes and required remediation.
5. Add regression tests.

## Database or audit unavailable
1. Stop new execution; fail closed.
2. Recover service and verify integrity/continuity.
3. Reconcile requests with unknown outcomes before retrying.
4. Never replay side effects blindly.

# 5. Backups
Before production: encrypted backups, defined RPO/RTO, restore drills, access controls, and retention policy. A backup is not considered valid until a restore has been tested.
