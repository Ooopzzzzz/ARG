# Project submission

Complete this file during the hackathon and use it to prepare your submission through the method announced by the organizers. Do not submit your project to the template repository.

## Project

- **Project name:** ARG — Agent Runtime Governance
- **Short description:** AI agents can propose actions that change enterprise data, but organizations need a way to enforce policy, require human review, and preserve an audit trail. ARG is a local prototype that evaluates proposed actions, explains allow/deny/approval outcomes, and routes approved work through a mock executor for agent developers and operations teams.
- **Code repository URL:** https://github.com/Ooopzzzzz/ARG
- **Final submitted implementation commit SHA:** 2b0acfb5a95bef185cc49492eb64fd2d3cad358b
- **Working demo URL or local demo steps:** Local demo: follow [README.md](README.md), generate a private `.env`, start Docker Compose, then open `http://localhost:3000`.
- **Demo access requirements:** Docker Engine and Docker Compose; the local operator token printed only in the ignored `.env` file. The demo uses synthetic data and a mock executor; no external services or credentials are required.

## Participants

Participate solo or in a team of up to 4. Remove unused rows.

**Team Name:** Dev-X

| Participant name | GitHub handle | Contribution |
| --- | --- | --- |
| Joel Shibu | Ooopzzzzz | System architecture, runtime governance gateway, external ERP integration, LLM tool-calling orchestration |
| Fathima Roshini Siyad | fathimaroshini | Product design, policy engine rules, evaluation testing, operator console UI/UX |

## Run and demonstrate

- **Prerequisites and versions:** Docker Engine with Docker Compose; Node.js 22 and Python 3.12 are only needed when running tools outside Docker.
- **Install command:** `python3 scripts/setup_local.py`
- **Required environment variable names:** `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `AGENT_KEY_PEPPER`, `OPERATOR_TOKEN`, `ARG_DEMO_AGENT_KEY`, `CORS_ORIGINS`, and `API_URL`; generated locally in ignored `.env`.
- **Start command:** `docker-compose --env-file .env -f infra/docker-compose.yml up --build -d`
- **Demo walkthrough:** Use **Overview** to submit a routine update and execute it through the mock adapter; submit a high-impact update, review and approve it in **Approvals**, then inspect the decision/approval/execution in **Audit trail**; submit a restricted deletion and confirm it is denied. Run `python3 chat_with_ollama.py` for live model-backed tool calling or `python3 test_realtime_pipeline.py` for automated end-to-end verification.
- **Checks performed and results:** Compose configuration and image builds passed; PostgreSQL reported healthy; migrations and demo seeding completed; API liveness returned HTTP 200; production Next.js build, lint, and type checks passed. Standalone Northstar Freight Core ERP on port 8080/8082 verified with HMAC-SHA256 single-use proof token verification and 403 rejection on un-governed calls. Live Ollama qwen2.5:7b tool calling verified end-to-end across ALLOW, REQUIRE_APPROVAL, and DENY pathways.
- **Known limitations or incomplete features:** Local demo uses synthetic enterprise records; host Ollama loopback binding requires host CLI tool execution to bridge model tool calling into the containerized runtime gateway.
- **Libraries, APIs, and public datasets used:** [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/), [Next.js](https://nextjs.org/docs), [React](https://react.dev/), and [Fluent UI React](https://react.fluentui.dev/). PostgreSQL 16 is used locally. No public datasets or external application APIs are used; demo records are synthetic.
- **AI usage record:** [AI_USAGE.md](AI_USAGE.md)
- **Development change log:** [CHANGELOG.md](CHANGELOG.md)

## Submission checklist

- [x] The project implementation started from scratch at the event.
- [x] I participated solo or with no more than 4 team members in total.
- [x] Codex was used during development and its usage is documented.
- [x] The code repository URL, short description, and working demo are provided.
- [x] README setup and demo instructions match the submitted code.
- [x] Actual checks and known limitations are documented.
- [x] Meaningful changes are documented and committed throughout development.
- [x] The final implementation is committed and pushed, and its SHA is recorded above.
- [x] No credentials or private data are included in the repository or demo instructions.
- [x] The organizers' announced submission method and timing have been followed.

Event reference: [DevDay Exchange Community: Kochi on Luma](https://luma.com/z10nz8gp). The event wraps up by **10:00 AM IST on 11 October 2026**.
