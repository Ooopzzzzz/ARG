# Project submission

Complete this file during the hackathon and use it to prepare your submission through the method announced by the organizers. Do not submit your project to the template repository.

## Project

- **Project name:** ARG — Agent Runtime Governance
- **Short description:** AI agents can propose actions that change enterprise data, but organizations need a way to enforce policy, require human review, and preserve an audit trail. ARG is a local prototype that evaluates proposed actions, explains allow/deny/approval outcomes, and routes approved work through a mock executor for agent developers and operations teams.
- **Code repository URL:** https://github.com/Ooopzzzzz/ARG
- **Final submitted implementation commit SHA:** Record after the final implementation checkpoint is committed.
- **Working demo URL or local demo steps:** Local demo: follow [README.md](README.md), generate a private `.env`, start Docker Compose, then open `http://localhost:3000`.
- **Demo access requirements:** Docker Engine and Docker Compose; the local operator token printed only in the ignored `.env` file. The demo uses synthetic data and a mock executor; no external services or credentials are required.

## Participants

Participate solo or in a team of up to 4. Remove unused rows.

| Participant name | GitHub handle | Contribution |
| --- | --- | --- |
| Awaiting participant confirmation | Awaiting participant confirmation | Confirm contributor attribution before submission. |

## Run and demonstrate

- **Prerequisites and versions:** Docker Engine with Docker Compose; Node.js 22 and Python 3.12 are only needed when running tools outside Docker.
- **Install command:** `python3 scripts/setup_local.py`
- **Required environment variable names:** `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `AGENT_KEY_PEPPER`, `OPERATOR_TOKEN`, `ARG_DEMO_AGENT_KEY`, `CORS_ORIGINS`, and `API_URL`; generated locally in ignored `.env`.
- **Start command:** `docker-compose --env-file .env -f infra/docker-compose.yml up --build -d`
- **Demo walkthrough:** Use **Overview** to submit a routine update and execute it through the mock adapter; submit a high-impact update, review and approve it in **Approvals**, then inspect the decision/approval/execution in **Audit trail**; submit a restricted deletion and confirm it is denied.
- **Checks performed and results:** Compose configuration and image builds passed; PostgreSQL reported healthy; migrations and demo seeding completed; API liveness returned HTTP 200; production Next.js build, lint, and type checks passed. Authenticated desktop/mobile browser walkthrough passed: all five sections loaded, allow/approval/deny scenarios completed, audit events appeared, mobile had no horizontal overflow, and keyboard focus was visible. Python pytest hangs on synchronous FastAPI routes even with a minimal app in the available runtimes; Ruff reports 90 findings and mypy reports 7 errors. `npm audit` reports five high findings in the development-only ESLint dependency chain; `npm audit --omit=dev` reported zero.
- **Known limitations or incomplete features:** Local one-tenant prototype; operator uses one shared local token; risk environment/classification/impact are untrusted agent-declared inputs; executor is mock-only; no live target integrations or external audit anchor; Python test/static checks need follow-up; five development-only npm audit findings remain.
- **Libraries, APIs, and public datasets used:** [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/), [Next.js](https://nextjs.org/docs), [React](https://react.dev/), and [Fluent UI React](https://react.fluentui.dev/). PostgreSQL 16 is used locally. No public datasets or external application APIs are used; demo records are synthetic.
- **AI usage record:** [AI_USAGE.md](AI_USAGE.md)
- **Development change log:** [CHANGELOG.md](CHANGELOG.md)

## Submission checklist

- [ ] The project implementation started from scratch at the event.
- [ ] I participated solo or with no more than 4 team members in total.
- [ ] Codex was used during development and its usage is documented.
- [ ] The code repository URL, short description, and working demo are provided.
- [ ] README setup and demo instructions match the submitted code.
- [ ] Actual checks and known limitations are documented.
- [ ] Meaningful changes are documented and committed throughout development.
- [ ] The final implementation is committed and pushed, and its SHA is recorded above.
- [ ] No credentials or private data are included in the repository or demo instructions.
- [ ] The organizers' announced submission method and timing have been followed.

Event reference: [DevDay Exchange Community: Kochi on Luma](https://luma.com/z10nz8gp). The event wraps up by **10:00 AM IST on 11 October 2026**.
