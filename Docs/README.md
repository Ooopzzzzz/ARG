# ARG — Execution Documentation Pack

**Product:** Enterprise AI Runtime Governance Platform (ARG)  
**Document baseline:** 1.0  
**Status:** Initial implementation baseline — validate assumptions before production use.

This pack translates the current ARG concept into an implementable MVP specification. It deliberately chooses a **modular monolith** and a narrow, testable vertical slice before distributed services or broad enterprise connectors.

## Start here
1. Read [`docs/00-governance/PROJECT_BASELINE.md`](docs/00-governance/PROJECT_BASELINE.md).
2. Treat [`docs/01-product/PRD.md`](docs/01-product/PRD.md) as the product contract.
3. Implement against [`docs/02-architecture/SAD.md`](docs/02-architecture/SAD.md) and [`docs/03-api/API_CONTRACT.md`](docs/03-api/API_CONTRACT.md).
4. Use [`docs/05-security/THREAT_MODEL.md`](docs/05-security/THREAT_MODEL.md) and [`docs/06-testing/TEST_STRATEGY.md`](docs/06-testing/TEST_STRATEGY.md) from day one.
5. Follow [`docs/07-delivery/IMPLEMENTATION_PLAN.md`](docs/07-delivery/IMPLEMENTATION_PLAN.md).
6. Record deviations in [`docs/adr/ADR_INDEX.md`](docs/adr/ADR_INDEX.md).

## Documentation map
- `00-governance/PROJECT_BASELINE.md` — scope, facts, assumptions, terminology.
- `01-product/PRD.md` — users, requirements, acceptance criteria, exclusions.
- `01-product/USER_FLOWS.md` — core flows and state transitions.
- `02-architecture/SAD.md` — system architecture and trust boundaries.
- `02-architecture/TDD.md` — module-level implementation design.
- `03-api/API_CONTRACT.md` — initial HTTP contract and error semantics.
- `03-api/openapi.yaml` — machine-readable API starting point.
- `04-data/DATA_MODEL.md` — entities, constraints, retention.
- `05-security/SECURITY_BASELINE.md` — security controls.
- `05-security/THREAT_MODEL.md` — threats and mitigations.
- `06-testing/TEST_STRATEGY.md` — verification plan and release gates.
- `07-delivery/IMPLEMENTATION_PLAN.md` — milestones and definition of done.
- `07-delivery/DEVELOPMENT_GUIDE.md` — local setup and workflow.
- `08-operations/OBSERVABILITY_AND_RUNBOOK.md` — telemetry, health, incident handling.
- `adr/ADR_INDEX.md` — decisions and change process.

## Important
This is an engineering starting point, not a claim of production readiness or regulatory certification. The product must not be described as guaranteeing safety. A governance decision only protects actions that actually pass through the enforcement boundary. If an agent can call a target system directly, ARG cannot prevent that bypass.
