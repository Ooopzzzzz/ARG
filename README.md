# ARG — Enterprise AI Runtime Governance

ARG evaluates AI agent action proposals before a controlled executor can reach a target system. The hackathon MVP demonstrates deterministic policy checks, explainable risk, human approval, and an audit trail using synthetic customer data and a mock adapter.

**This is a local prototype, not a production deployment or a guarantee of safety.** ARG only governs actions routed through its enforcement boundary. The demo does not connect to live enterprise systems or perform real business actions.

## Current MVP features

- Tenant-scoped demo organization and agent credentials stored as keyed digests.
- Versioned deterministic policy rules with deny precedence and default deny.
- Explainable risk factors and `ALLOW`, `DENY`, `REQUIRE_APPROVAL` outcomes.
- Human approval bound to the original action hash and policy version.
- Mock executor with one-time execution grants and idempotent request handling.
- Operator console for overview, agents, policies, approvals, and audit events.
- Local PostgreSQL and Docker Compose development environment.

## Requirements

- Docker Engine and Docker Compose V2 plugin.
- Python 3.12+ (only needed to generate local configuration or run API tools outside Docker).
- Node.js 22+ and npm (only needed to run the web app outside Docker).

## Start locally

From the repository root:

```bash
python3 scripts/setup_local.py
docker compose -f infra/docker-compose.yml up --build
```

The setup script creates `.env` with random local secrets. It refuses to overwrite an existing `.env`. Keep that file private and out of Git. The API applies database migrations and seeds the synthetic demo tenant, agent, and policy on startup.

Open the operator console at `http://localhost:3000` and sign in with the `OPERATOR_TOKEN` value from your local `.env` file. The API health endpoints are `http://localhost:8000/health/live` and `http://localhost:8000/health/ready`; interactive API docs are at `http://localhost:8000/docs`.

To stop the services, press Ctrl+C. To stop and remove the local database volume, run `docker compose -f infra/docker-compose.yml down -v` (this deletes local demo data).

## Demo walkthrough

1. In **Overview**, submit **Routine customer update**. ARG should return `ALLOW`; use **Execute through mock adapter** to record the simulated result.
2. Submit **High-impact update**. ARG should return `REQUIRE_APPROVAL`; the page explicitly shows that no target action has executed.
3. Open **Approvals**, review the action summary, risk, and policy version, then select **Approve and resume**. The mock adapter records the action once.
4. Return to **Audit trail** to trace the decision, approval, and mock execution.
5. Submit **Restricted deletion**. The explicit deny rule blocks it.

All scenarios use fictional customers. No external connector or target network request is configured.

## API and checks

The API contract is documented in `Docs/docs/03-api/API_CONTRACT.md`. Core product and security requirements are in `Docs/docs/01-product/PRD.md`, `Docs/docs/02-architecture/TDD.md`, and `Docs/docs/05-security/THREAT_MODEL.md`.

```bash
uv sync --project apps/api --extra dev
uv run --project apps/api pytest apps/api/tests -q
uv run --project apps/api ruff check apps/api
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

The test suite uses an isolated SQLite database for fast API checks. The local demo uses PostgreSQL. A PostgreSQL integration run and visual browser check should also be performed when Docker Compose and browser tooling are available.

## Libraries

- FastAPI, Pydantic, SQLAlchemy, Alembic, psycopg, and Uvicorn.
- Next.js, React, and Fluent UI React Components.
- PostgreSQL 16 for local persistence.

## Limitations

- Local demo authentication uses a single operator token and one synthetic tenant; it is not an enterprise identity or RBAC implementation.
- Audit events are append-only through this API, but there is no hash chain or external tamper-evidence anchor.
- The executor is mock-only. External target failures, distributed transaction behavior, and connector idempotency are not demonstrated.
- Deployment hardening, rate limiting, SSO, production observability, backup/restore, and compliance certification are not included.
- On 10 October 2026, `npm audit` reported five high-severity findings in the development-only Next.js ESLint dependency chain (`braces` via `fast-glob`). The registry had no newer `braces` release at that check; PostCSS advisories were resolved with a compatible override.

See `CHANGELOG.md` for actual changes and checks, `AI_USAGE.md` for Codex assistance, and `SUBMISSION.md` for the event submission record.
