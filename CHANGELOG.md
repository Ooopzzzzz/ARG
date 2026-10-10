# Change log

Record each meaningful project change during the event, newest first. Update this file in the same commit as the change. Use a real timestamp with timezone, for example `YYYY-MM-DDTHH:MM:SS+05:30`.

## Event build log

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
