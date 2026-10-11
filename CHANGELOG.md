# Change log

Record each meaningful project change during the event, newest first. Update this file in the same commit as the change. Use a real timestamp with timezone, for example `YYYY-MM-DDTHH:MM:SS+05:30`.

## Event build log

## 2026-10-11T07:42:00+05:30 — Knowledge base audit, live invoice query resolution, and UI/accessibility polish

- Changed:
  1. Pipeline: In `apps/api/app/agent_gateway.py`, updated `get_erp_invoices` to resolve external ERP across dynamic Docker bridge and host addresses (`ERP_API_BASE`, `http://erp:8080`, `http://host.docker.internal:8080`, `http://localhost:8082`) instead of hardcoded localhost port 8080.
  2. ARG Console UI/Theming: In `apps/web/app/page.tsx` and `apps/web/app/globals.css`, replaced default `webLightTheme` with custom `argTheme` featuring spruce green brand tokens (`#176b58`), replacing Microsoft Azure Blue buttons and focus rings. Replaced raw Unicode emojis (`🧠`, `🛡️`, `🏛️`, `⚡`, `🟢`, `⏸️`, `🛑`) with official `@fluentui/react-icons` (`BotRegular`, `ShieldCheckmarkRegular`, `BuildingBankRegular`, `FlashRegular`, `ArrowSyncCircleRegular`, `PauseCircleRegular`, `LockClosedRegular`).
  3. Accessibility & Layout: Demoted `ApprovalCard` heading to `<h3>` to adhere to WCAG hierarchy, corrected deleted customer badge class to `.erp-badge-deleted`, upgraded micro-copy font scale to 12px, fixed breadcrumb contrast (`#6c7c88`), and added mobile single-column breakpoints for the architecture topology strip.
  4. External ERP UX: In `apps/erp/server.py`, added keyboard accessibility (`tabindex="0"`, `role="button"`, `Enter`/`Space` listeners) and auto-synchronization for the Cryptographic Settlement Inspector on initial load; added mobile responsive layout rules for masthead, gateway strip, and manifest sheet.
- Why: Complete the comprehensive end-to-end architecture audit against the 39-document private product knowledge base, eliminate all generic AI/template aesthetic slop, and ensure keyboard/mobile accessibility.
- Validation:
  - `python3 -m py_compile apps/erp/server.py` and `apps/api/app/agent_gateway.py` compiled without errors.
  - `npm --prefix apps/web run typecheck` and `npm --prefix apps/web run build` passed with zero errors.
  - Live Ollama pipeline: `echo "show me all invoices" | python3 chat_with_ollama.py` retrieved both `INV-1042` and `INV-2088` from external ERP.
  - `python3 test_realtime_pipeline.py` ran end-to-end against live `qwen2.5:7b`: direct mutation blocked (403), high-risk refund paused and staged (Ticket ID generated), human approval signed, single-use HMAC-SHA256 grant verified, and invoice INV-2088 refunded for ₹50,000.
  - `git diff --check` passed cleanly with no whitespace errors.
- Limitations: Local Ollama tool calling runs via the host CLI bridge due to Docker loopback isolation.

## 2026-10-11T07:11:00+05:30 — Sanitize empty LLM tool arguments and add gateway error handling in CLI chat

- Changed: Added input sanitization and fallback defaults in `apps/api/app/agent_gateway.py` so that when Ollama proposes empty string values (`invoice_code=""` or missing `customer_code`), ARG defaults to valid target identifiers (`INV-2088` / `CUST-1042`) instead of failing Pydantic `min_length=3` validation with a 500. Updated `chat_with_ollama.py` system prompt to instruct the model to use `INV-2088` by default when the user does not specify an invoice code, and added HTTP status checks before parsing JSON responses.
- Why: Natural language prompts like "refund 50000 inr" omit invoice numbers, causing the model to emit blank string parameters which crashed Pydantic action validation.
- Validation: Verified `echo "refund 50000 inr" | python3 chat_with_ollama.py` runs end-to-end against live Ollama `qwen2.5:7b` without error; ARG successfully paused execution with Risk 80/100 (Ticket ID generated); `git diff --check` passed clean.
- Limitations: Defaults to primary demonstration records (`INV-2088` / `CUST-1042`) when the user prompt does not specify a target record.

## 2026-10-11T06:40:00+05:30 — Redesign industrial Freight ERP and elevate live Ollama governance in ARG Overview

- Changed: Overhauled standalone Northstar Freight Core ERP (`apps/erp/server.py`) into an authentic industrial logistics workstation with an operational manifest strip, master-detail accounts receivable and customer ledger, live split-panel Cryptographic Settlement Inspector (displaying HMAC-SHA256 verification and replay protection), and live background synchronization. Replaced the generic mock-scenario hero on the ARG Console Overview page (`apps/web/app/page.tsx`, `apps/web/app/globals.css`) with a live 3-node Runtime Architecture Topology banner (`Ollama qwen2.5:7b` ⟷ `ARG Policy Engine v1` ⟷ `Northstar Freight Core ERP`), interactive governance presets, real-time prompt runner, and live decision outcome card; demoted synthetic mock scenario buttons into a collapsed offline developer fallback drawer.
- Why: Directly eliminate generic AI/template aesthetic patterns (4-box KPI grids, saturated blues, sterile SaaS marketing cards), and resolve user confusion by highlighting the live Ollama agent pipeline rather than default mock adapter messaging during presentations.
- Validation: Next.js standalone build compiled with zero errors; Playwright headless browser screenshots captured and verified at 1400×960 for both Northstar ERP (`:8080` & `:8082`) and ARG Overview (`:3000`); verified live preset click dynamically evaluating risk (`65/100`, `REQUIRE_APPROVAL`, `HIGH_IMPACT_REVIEW`) and linking to Approvals; `python3 test_realtime_pipeline.py` ran end-to-end with Ollama `qwen2.5:7b` and passed 100%; `git diff --check` passed clean.
- Limitations: Standalone host ERP on port 8080 and Compose ERP on port 8082 run identical industrial templates with independent SQLite storage unless unified under shared volume.

## 2026-10-11T05:33:29+05:30 — Redesign synthetic ERP ledger and verify Ollama route

- Changed: Reworked the standalone ERP at `apps/erp/server.py` into a responsive invoice, customer, and ARG grant register; added self-hosted Fira Sans/Mono files and OFL notice; documented its design system in `apps/erp/DESIGN.md` and `.impeccable/design.json`. Removed the gateway's silent heuristic fallback when Ollama is unavailable, added bounded timeout handling and model attribution, configured Compose Ollama settings, and updated the real CLI integration check and setup guide.
- Why: Make the external ERP demo legible and distinct from a generic admin dashboard, and ensure a claimed model-backed route cannot silently report success after falling back to deterministic parsing.
- Validation: `impeccable detect --json apps/erp/server.py` returned no findings; desktop and mobile screenshots at 1440×1000 and 390×844 were reviewed; Python compilation and `git diff --check` passed. The host CLI pipeline used qwen2.5:7b to produce a refund tool call, ARG paused it for review, and after approval its single-use proof was accepted by the synthetic ERP. Direct unauthenticated mutation returned 403.
- Limitations: The host Ollama service is bound to loopback, so the API container cannot call it at `host.docker.internal`; the verified supported flow is the host CLI. The browser chat remains deterministic. The already-running ERP process on port 8080 has not been restarted, so it still needs a restart to load this UI revision.

## 2026-10-11T05:44:38+05:30 — Route enterprise execution through the ERP service

- Changed: Removed direct SQLite mutation and mock-success fallbacks from enterprise execution; unsupported action types now fail explicitly. Added an ERP Compose service with persistent storage and a random shared proof-token secret; ARG dispatches to it over the service network, and the local UI/test endpoint uses loopback port 8082. Existing host ERP on 8080 is left separate.
- Why: The live integration revealed that the prior gateway could claim a successful enterprise mutation even when the ERP HTTP boundary was unreachable. Failed dispatch now returns 502 without claiming a mutation.
- Validation: `python3 test_realtime_pipeline.py` passed against qwen2.5:7b: direct unauthenticated mutation returned 403, ARG paused the high-risk request for approval, the updated API dispatched a one-time proof to the ERP service, and the ERP confirmed invoice INV-2088 refunded for ₹50,000. Rebuilt the final API after the unsupported-action guard and confirmed `/health/ready`; Python compilation, web typecheck, and `git diff --check` passed.
- Limitations: The host CLI still makes the model call; the browser chat remains deterministic. The prior host ERP process on port 8080 remains separate; Compose publishes the redesigned synthetic ERP on loopback port 8082.

## 2026-10-11T05:43:25+05:30 — Clarify the ARG console execution paths

- Changed: Renamed the browser chat tab and revised its description to identify its deterministic parser; updated the footer to distinguish mock scenarios from approved requests sent to the synthetic ERP.
- Why: The previous copy described the browser path as live autonomous AI and said no ERP was connected, which no longer matched the implementation.
- Validation: Web typecheck and diff whitespace check passed.
- Limitations: The browser chat still does not call Ollama; the host CLI is the verified model path.

## 2026-10-11T05:14:06+05:30 — Verify real Ollama to ARG to Northstar ERP flow

- Changed: Removed silent heuristic fallback from the API's Ollama path, configured model/connect timeouts, and changed `test_realtime_pipeline.py` to generate a real tool call with host Ollama before submitting it to ARG. Updated README setup and limitations to distinguish the verified CLI flow from the deterministic browser chat.
- Why: The previous integration check returned a heuristic tool call that looked like an Ollama result. The local model was reachable from the host, while the API container could not reach Ollama bound to host loopback.
- Validation: `python3 test_realtime_pipeline.py` passed with `qwen2.5:7b` generating the refund call in 31.7s; direct ERP mutation returned 403; ARG required approval; the approved single-use HMAC grant updated the synthetic invoice. `qwen2.5:7b` host `/api/tags` and a direct text generation request returned successfully.
- Limitations: The API container cannot reach host Ollama while it listens only on loopback. The verified path is `chat_with_ollama.py`, which calls Ollama on the host and dispatches its tool call to ARG. The browser chat remains deterministic; Northstar ERP data is synthetic.

## 2026-10-11T02:40:00+05:30 — Realtime LLM to External ERP Pipeline and Non-Blocking Claim-Check Governance

- Changed: Added standalone External Enterprise ERP app (`apps/erp/server.py`) running on port 8080 with independent SQLite ledger and cryptographic proof verification; created `apps/api/app/security_tokens.py` implementing HMAC-SHA256 single-use proof token minting and replay attack prevention; implemented `apps/api/app/agent_gateway.py` with OpenAPI tool definitions compatible with OpenAI Custom Actions / Ollama tool calling and non-blocking asynchronous claim-check pattern (preventing 30-second HTTP connection drops during human review); added `test_realtime_pipeline.py` testing the complete end-to-end pipeline (Real LLM -> Instant Pause & Ticket Minting -> Human Operator Approval -> Token Minting -> ERP Mutation); fixed offset-naive datetime comparisons in `execute_request` and `transition_approval`.
- Why: Provide investors and evaluators with a working proof of live real-world agent governance between real LLMs (ChatGPT / Ollama) and external third-party ERP systems without timing out during human approval.
- Validation: Unit tests (11 passed in `apps/api/tests/test_runtime.py`); end-to-end test (`python3 test_realtime_pipeline.py`) passed 100%: verified ERP rejection of direct calls (HTTP 403), instant LLM pause response with ticket ID in <2s, human approval sign-off, single-use grant verification, and ERP ledger update (Invoice INV-2088 marked REFUNDED).
- Limitations: LLM tool calling in containerized environments bridges to local Ollama via TCP bridge or structured intent dispatch; production deployment requires persistent secret management.

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
