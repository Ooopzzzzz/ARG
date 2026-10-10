# First 48 Hours — ARG Implementation Checklist

## Before code
- [ ] protect main branch. continues update github repo
- [ ] Copy this documentation pack into `docs/`.
- [ ] Confirm team agrees to MVP scope and the mock-only executor.
- [ ] Freeze API schemas and decision precedence.
- [ ] Create ADRs for any deviations.

## First working slice
- [ ] FastAPI app starts and exposes liveness/readiness.
- [ ] PostgreSQL and Alembic migration work from an empty DB.
- [ ] Create tenant and register agent with hashed credential.
- [ ] Submit one action request with idempotency key.
- [ ] Evaluate default-deny policy and return DENY.
- [ ] Activate a test ALLOW policy and return ALLOW.
- [ ] Submit approval-required action and prove executor does not run.
- [ ] Approve it and execute mock action once.
- [ ] Replay same execution and prove no second side effect.
- [ ] Verify audit trail for the complete lifecycle.
- [ ] Run cross-tenant and payload-tampering tests.

## Do not build yet
- [ ] No live Gmail/Slack/GitHub integration.
- [ ] No LLM policy interpreter.
- [ ] No ML anomaly detection.
- [ ] No microservices/Kubernetes.
- [ ] No production credentials or real business actions.
