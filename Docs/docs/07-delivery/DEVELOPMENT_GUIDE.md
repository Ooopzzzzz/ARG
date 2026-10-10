---
title: ARG Development Guide
version: 1.0
status: baseline
owner: Engineering
created: 2026-10-10
updated: 2026-10-10
tags: [arg, developer-guide]
related: [[IMPLEMENTATION_PLAN]], [[SAD]], [[TEST_STRATEGY]]
---

# 1. Prerequisites
- Git.
- Docker Engine and Docker Compose plugin.
- A supported Python version matching `apps/api/pyproject.toml`.
- A supported Node.js LTS version matching the web app's `package.json`.
- At least 8 GB RAM recommended for the full local stack.

Exact versions must be pinned in repository files when the scaffold is created; do not rely on global unpinned tools.

# 2. Expected local workflow
1. Clone repository.
2. Copy `infra/.env.example` to `infra/.env`.
3. Replace all development secrets with random local-only values.
4. Start PostgreSQL and API with Docker Compose.
5. Run database migrations.
6. Seed synthetic tenant, operator, agent, and policy data through a development-only seed command.
7. Start the web application.
8. Run unit, integration, and end-to-end tests.

# 3. Environment configuration
Required settings should include:
- `APP_ENV`
- `DATABASE_URL`
- `AGENT_KEY_PEPPER` or equivalent keyed lookup secret
- `OPERATOR_AUTH_MODE`
- `CORS_ORIGINS`
- `LOG_LEVEL`
- `AUDIT_HASH_KEY` only if the selected audit-chain design requires it

Production mode must fail startup if required secrets are missing or known development defaults are detected. Never use production data in local fixtures.

# 4. Branch and commit conventions
- Branches: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
- Commit style: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `security:`).
- One logical change per pull request.
- Require CI green before merge.

# 5. Code conventions
- Strict type checking for Python boundaries and TypeScript.
- Keep policy evaluator pure and deterministic.
- Use explicit enums for decision and state values.
- Use UTC timestamps.
- No secrets in source control.
- Avoid catch-all exception handling that returns success.
- Never add a new target adapter without a threat review and tests.
- No direct SQL without tenant scope in tenant-owned operations.

# 6. Local demo safety
The mock adapter must be the default. It should produce a synthetic outcome such as a mock record update and must never make network calls. Add an explicit, separately reviewed feature flag for any future live connector; do not introduce such a flag until its safety requirements are defined.
