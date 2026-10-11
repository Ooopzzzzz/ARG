# ARG — Enterprise AI Runtime Governance

ARG evaluates AI agent action proposals before a controlled executor can reach a target system. The local demo includes deterministic policy checks, human approval, an audit trail, a local Ollama tool-calling CLI, and a standalone synthetic Northstar ERP protected by single-use HMAC grants.

**This is a local prototype, not a production deployment or a guarantee of safety.** ARG only governs actions routed through its enforcement boundary. Northstar is a synthetic local ERP, not a real third-party system.

## Current MVP features

- Tenant-scoped demo organization and agent credentials stored as keyed digests.
- Versioned deterministic policy rules with deny precedence and default deny.
- Explainable risk factors and `ALLOW`, `DENY`, `REQUIRE_APPROVAL` outcomes.
- Human approval bound to the original action hash and policy version.
- Mock executor with one-time execution grants and idempotent request handling.
- Standalone synthetic Northstar ERP that rejects direct mutations and verifies one-time ARG proof tokens.
- `chat_with_ollama.py` sends prompts to local Ollama, then dispatches its generated tool call through the ARG gateway.
- Operator console for overview, agents, policies, approvals, and audit events.
- Local PostgreSQL and Docker Compose development environment.

## Requirements

- Docker Engine and Docker Compose V2 plugin.
- Python 3.12+ (only needed to generate local configuration or run API tools outside Docker).
- Node.js 22+ and npm (only needed to run the web app outside Docker).
- Ollama with the `qwen2.5:7b` model (only needed for the local agent flow).

## Start locally

From the repository root:

```bash
python3 scripts/setup_local.py
docker-compose --env-file .env -f infra/docker-compose.yml up --build -d
```

The setup script creates `.env` with random local secrets, including the ARG-to-ERP shared proof-token key. It refuses to overwrite an existing `.env`. Keep that file private and out of Git. The API applies database migrations and seeds the synthetic demo tenant, agent, and policy on startup. Compose starts the ERP as a separate service with its own persistent data volume.

Open the operator console at `http://localhost:3000` and sign in with the `OPERATOR_TOKEN` value from your local `.env` file. The API health endpoints are `http://localhost:8000/health/live` and `http://localhost:8000/health/ready`; interactive API docs are at `http://localhost:8000/docs`.

Open the standalone synthetic ERP at `http://localhost:8082`. ARG calls it over the Compose network; its published port is loopback-only. The previous host-run ERP can remain on port 8080 without being exposed to the network.

For the Ollama flow, start Ollama on the host and install the model once with `ollama pull qwen2.5:7b`. In another terminal, run `python3 chat_with_ollama.py`. Prompts go to Ollama on the host; generated ERP tool calls go to ARG. Review the resulting request in the ARG console. **Agent chat demo** in the browser uses deterministic parsing and does not call Ollama.

To stop the services, run `docker-compose --env-file .env -f infra/docker-compose.yml down`. To stop and remove the local database volume, add `-v` (this deletes local demo data).

## Demo walkthrough

1. Start `python3 chat_with_ollama.py` and ask for a ₹50,000 refund on `INV-2088`.
2. Ollama proposes a refund tool call. ARG returns `REQUIRE_APPROVAL` with a request ID; the ERP remains untouched while approval is pending.
3. Open **Approvals**, review the request, then approve it. ARG resumes execution using a single-use proof token.
4. Open the ERP site at `http://localhost:8082` to review its invoice ledger and consumed grant record.
5. In **Overview**, use the fixed scenarios to demonstrate the separate mock adapter's ALLOW, approval, and DENY paths.

To verify the live Ollama → ARG approval → ERP path, run `python3 test_realtime_pipeline.py` with the Compose stack and local Ollama running.

All customer and invoice data are fictional. Ollama runs locally; no cloud model or production ERP is configured.

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
- Fira Sans and Fira Mono for the ERP ledger typography; font files and SIL OFL 1.1 notice are in `apps/erp/static/` (upstream: [Fira Sans](https://github.com/bBoxType/FiraSans)).

## Limitations

- Local demo authentication uses a single operator token and one synthetic tenant; it is not an enterprise identity or RBAC implementation.
- Environment, data classification, and impact used in risk scoring are declared by the agent request. They are illustrative inputs, not independently verified facts; a compromised agent can understate them. Production enforcement would need trusted, server-side context and target-specific rules.
- Audit events are append-only through this API, but there is no hash chain or external tamper-evidence anchor.
- The Northstar connector targets the local synthetic ERP service in Compose. The API reports external execution failures instead of substituting a mock result; production ERP integration, distributed transaction behavior, and production connector idempotency are not demonstrated.
- The API container cannot reach an Ollama service bound only to host loopback. The supported Ollama path is the host CLI, which sends generated tool calls to ARG. The browser chat remains deterministic.
- Deployment hardening, rate limiting, SSO, production observability, backup/restore, and compliance certification are not included.
- On 10 October 2026, `npm audit` reported five high-severity findings in the development-only Next.js ESLint dependency chain (`braces` via `fast-glob`); `npm audit --omit=dev` reported no production dependency findings. The registry had no newer `braces` release at that check; PostCSS advisories were resolved with a compatible override.

See `CHANGELOG.md` for actual changes and checks, `AI_USAGE.md` for Codex assistance, and `SUBMISSION.md` for the event submission record.
