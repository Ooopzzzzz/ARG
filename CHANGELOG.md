# Change log

Record each meaningful project change during the event, newest first. Update this file in the same commit as the change. Use a real timestamp with timezone, for example `YYYY-MM-DDTHH:MM:SS+05:30`.

## Event build log

## 2026-10-11T01:30:00+05:30 — Build Enterprise ERP Portal & Governed AI Agent Sandbox

- Changed: Added live PostgreSQL-backed Enterprise ERP data layer (`ERPCustomer`, `ERPInvoice`), Alembic migration `0002_erp_tables`, seed records for "Northstar Global Logistics", real ERP execution adapter (`apps/api/app/adapters/erp.py`), new `/api/v1/erp/records` endpoint, dedicated "Enterprise ERP Portal" dashboard tab with live customer ledger and invoice status, and an interactive "Live AI Agent (Chat)" sandbox demonstrating real-time natural language action proposal, policy interception, and human approval flow.
- Why: Provide undeniable proof of real enterprise middleware value for investors and judges by showing a real protected ERP system of record mutating live only when authorized by ARG.
- Validation: Database migration and seed verified; `/api/v1/erp/records` returned live accounts and invoices; web TypeScript, ESLint, and Next.js production build passed; Docker containers running healthy on ports 3000 and 8000.
- Limitations: LLM chat uses deterministic local intent parsing mapped to ARG action schemas; external cloud LLM key is optional.

## 2026-10-11T00:05:00+05:30 — Fix five pre-demo bugs

- Changed: Fixed policy re-activation SQLAlchemy dirty-tracking bug (added `session.refresh` before re-setting `active=True`); corrected API Dockerfile build order (source copied before `pip install .`) and added `CMD`; added `ENV HOSTNAME="0.0.0.0"` to web Dockerfile for standalone Next.js binding; wrapped initial `Spinner` in `FluentProvider` for theme context; added `try/catch` around `request.json()` in all three web API routes (`session`, `demo/action`, `demo/execute`) to return 400 instead of 500 on malformed bodies.
- Why: Policy activation bug could silently deactivate all policies during demo; Dockerfiles would fail or be unreachable; Spinner rendered unstyled without FluentProvider; uncaught JSON parse errors crashed routes with generic 500s.
- Validation: `python3 -m compileall -q apps/api/app/` passed, `npm run typecheck`, `npm run lint`, and `npm run build` all passed clean. Diff reviewed for each fix.
- Limitations: Docker image rebuild not re-run in this pass; Python TestClient still hangs in available runtimes.

## 2026-10-10T23:24:03+05:30 — Verify local demo and document trust boundary

- Changed: Added a web Docker ignore file to exclude local dependencies/build output, corrected flex alignment values that emitted Autoprefixer warnings, documented the agent-declared risk metadata limitation in README and threat model, and made Compose setup commands explicit about the root `.env` file.
- Why: Keep Docker builds small and make the demo's security boundary and reproducible local setup clear.
- Validation: Docker Compose V5.5.1 config validation passed; API and web images built; PostgreSQL reported healthy; API migration and seed completed; API liveness returned HTTP 200; production Next.js build, lint, and type validation passed during image build. Browser review passed sign-in layout at desktop/mobile dimensions, but authenticated scenarios remain under verification. Python pytest/Ruff/mypy were not verified because the system Python TestClient hangs on a minimal FastAPI app and the Python 3.12 dev dependency sync did not complete.
- Limitations: Compose startup currently depends on registry downloads; agent-declared risk metadata is untrusted; the remaining npm audit findings are confined to the development lint dependency chain.

## 2026-10-10T23:31:00+05:30 — Fix same-origin session check and verify demo flow

- Changed: Updated the web session CSRF check to validate the parsed Origin against the public Host and request protocol; rebuilt the production web image. Updated submission results with the completed authenticated demo walkthrough.
- Why: The previous check compared the browser origin to Next.js's internal container URL, rejecting valid local sign-in requests.
- Validation: Security reviewer found host/scheme comparison appropriate for the loopback Compose setup; production build and lint/type checks passed. Browser verified sign-in, all five sections, ALLOW plus mock execution, REQUIRE_APPROVAL then approval/resume, DENY, and audit history. Mobile layout had no horizontal overflow, keyboard focus was visible, and no console/request errors occurred.
- Limitations: Python automated tests still hang on a minimal synchronous FastAPI route in the available runtimes; Ruff and mypy findings are being addressed. Agent-declared risk context remains untrusted.

## 2026-10-10T23:01:23+05:30 — Build ARG MVP governance demo

- Changed: Added the FastAPI governance API, PostgreSQL persistence models and migration, local demo seeding, authenticated Next.js operator console, mock-only scenarios, policy and agent controls, approval review/resume, Docker Compose configuration, and API acceptance tests. Bound container ports to localhost and made generated `.env` files owner-only.
- Why: Implement the documented MVP P0 as a local prototype and demonstrate action evaluation, approval, controlled execution, and an audit trail.
- Validation: `python3 -m compileall -q apps/api/app apps/api/tests scripts/setup_local.py`, direct domain assertions for default deny/deny precedence/canonical hashing, `uv lock --check --offline --project apps/api`, `npm run typecheck --prefix apps/web`, `npm run lint --prefix apps/web`, `npm run build --prefix apps/web`, `impeccable detect`, and `git diff --check` passed. Python API tests, Ruff, and mypy could not complete: the approved package download stalled, and the system Python TestClient also hung while entering a minimal FastAPI app. Docker Compose startup could not run because the Compose V2 plugin is absent. `npm audit` reports five high-severity findings in the development-only ESLint dependency chain; the registry has no newer `braces` release to resolve them.
- Limitations: Local prototype only; one synthetic tenant and shared local operator token; mock adapter only; no live enterprise connectors or production hardening. See README for dependency audit findings.

```text
## <actual timestamp> — <short change title>

- Changed: <feature or files changed>
- Why: <reason for the change>
- Validation: <commands or manual checks actually run, with results>
- Limitations: <known issues or "None identified in these checks">
```

## Template setup — 10 October 2026

- Changed: Added the event README, rules, agent guide, change log, AI usage record, submission checklist, Git ignore rules, and pull request checklist.
- Why: Give participants a consistent starting point for event rules, basic coding patterns, documented changes, and regular commits.
- Validation: Checked local Markdown links, event detail consistency, required documents, and diff whitespace before publishing.
- Limitations: Documentation scaffolding only; no participant project, application, or working demo is included. GitHub publication and template status are verified separately after creation.
