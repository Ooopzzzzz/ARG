# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Inferred from the current implementation: ARG operators and reviewers who inspect agent proposals, approve or deny elevated risk actions, and trace resulting activity. Northstar ERP users review synthetic customer and invoice records.

## Product Purpose

Inferred from the current implementation and project documentation: ARG evaluates agent action proposals against deterministic policy, pauses actions requiring human review, and records decisions before an authorized executor reaches a target system. The local demo demonstrates this workflow with a standalone Northstar ERP ledger.

## Positioning

Inferred from the current implementation: policy evaluation and human approval sit between agent tool calls and target mutations, with request-linked audit records and a single-use proof token at the ERP boundary.

## Operating Context

Inferred from the current implementation: local hackathon demonstration using synthetic customer and invoice records, a local ARG API, an optional local Ollama model, and a standalone ERP service. Operators inspect pending approvals in the ARG console; ERP pages display the target ledger and consumed grants.

## Capabilities and Constraints

- Inferred: the ARG console includes overview, ERP records, agent chat, approval review, policy management, agent registry, and audit history.
- Inferred: the Northstar ERP demo exposes customer, invoice, and consumed-grant ledgers.
- Confirmed by README: the project is a local prototype; its data and demo tenant are synthetic, and it is not a production deployment.
- The browser chat currently uses deterministic intent parsing. The host CLI's Ollama tool-call flow was verified end to end with the local Northstar ERP. The API container cannot call a host Ollama listener bound only to loopback.
- The real ERP product, production integration target, identity model, and deployment environment remain undecided.

## Evidence on Hand

- `apps/erp/server.py`: standalone Northstar ERP service and ledger UI.
- `apps/api/app/agent_gateway.py` and `chat_with_ollama.py`: Ollama tool-call integration paths.
- `test_realtime_pipeline.py`: exercised the host Ollama tool-call flow through ARG approval and the standalone synthetic ERP during this review.
- `README.md`: local prototype scope and documented demo limitations.

## Product Principles

- Inferred: show the source and state of each action clearly.
- Inferred: make approval status and target execution status distinct.
- Inferred: never present synthetic data as production data.
- Inferred: make policy decisions traceable to a request and audit event.

## Accessibility & Inclusion

No product-specific accessibility requirement was confirmed. Follow WCAG 2.1 AA for the web console as a project standard.
