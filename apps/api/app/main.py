from datetime import timedelta
import hashlib
import hmac
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.adapters.mock import execute_mock_action
from app.database import Base, engine, get_session
from app.domain import canonical_hash, evaluate_policy, risk_assessment
from app.models import (
    Agent,
    Approval,
    AuditEvent,
    Decision,
    Execution,
    ExecutionGrant,
    Organization,
    PolicyVersion,
    RuntimeRequest,
    utc_now,
)
from app.schemas import AgentInput, ApprovalInput, DecisionRequest, PolicyInput
from app.security import digest_agent_key, issue_agent_key, require_agent, require_operator

API_PREFIX = "/api/v1"
DECISION_TTL_MINUTES = 5
APPROVAL_TTL_MINUTES = 30
MAX_REQUEST_BYTES = 16_384

settings = get_settings()
app = FastAPI(title="ARG Runtime Governance API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


class RequestSizeLimitMiddleware:
    def __init__(self, application: ASGIApp) -> None:
        self.application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return
        chunks: list[dict[str, Any]] = []
        size = 0
        while True:
            message = await receive()
            chunks.append(message)
            size += len(message.get("body", b""))
            if size > MAX_REQUEST_BYTES:
                body = b'{"detail":"Request body exceeds the 16 KB limit"}'
                await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
            if not message.get("more_body", False):
                break
        remaining = iter(chunks)

        async def replay() -> dict[str, Any]:
            try:
                return next(remaining)
            except StopIteration:
                return {"type": "http.request", "body": b"", "more_body": False}

        await self.application(scope, replay, send)


app.add_middleware(RequestSizeLimitMiddleware)


def digest_operator_credential() -> str:
    return hmac.new(
        settings.agent_key_pepper.encode(), settings.operator_token.encode(), hashlib.sha256
    ).hexdigest()


@app.on_event("startup")
def validate_runtime_configuration() -> None:
    if settings.app_env != "development" and (
        settings.operator_token == "local-development-operator-token"
        or settings.agent_key_pepper == "local-development-pepper-change-before-use"
    ):
        raise RuntimeError("Development credentials are forbidden outside development mode")


def tenant_id(session: Session) -> UUID:
    tenant = session.scalar(select(Organization).order_by(Organization.created_at).limit(1))
    if tenant is None:
        raise HTTPException(status_code=503, detail="Demo tenant is not initialized")
    return tenant.id


def append_audit(
    session: Session, tenant: UUID, event_type: str, payload: dict[str, Any], request_id: UUID | None = None
) -> None:
    session.add(AuditEvent(tenant_id=tenant, request_id=request_id, event_type=event_type, payload=payload))


def request_result(session: Session, request: RuntimeRequest) -> dict[str, Any]:
    decision = session.scalar(
        select(Decision).where(Decision.request_id == request.id).order_by(Decision.created_at.desc())
    )
    approval = session.scalar(select(Approval).where(Approval.request_id == request.id))
    execution = session.scalar(select(Execution).where(Execution.request_id == request.id))
    if decision is None:
        raise HTTPException(status_code=503, detail="Decision record is unavailable")
    return {
        "request_id": str(request.id),
        "decision": decision.outcome,
        "state": request.state,
        "reason_codes": decision.reason_codes,
        "policy_version_id": str(decision.policy_version_id),
        "risk": {"score": decision.risk_score, "factors": decision.risk_factors},
        "approval_id": str(approval.id) if approval else None,
        "execution": execution.result if execution else None,
        "created_at": request.created_at.isoformat(),
    }


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(select(1))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Database is not ready") from error
    return {"status": "ready"}


@app.get(f"{API_PREFIX}/overview", dependencies=[Depends(require_operator)])
def overview(session: Session = Depends(get_session)) -> dict[str, Any]:
    tenant = tenant_id(session)
    decisions = session.scalars(select(Decision).where(Decision.tenant_id == tenant)).all()
    pending = session.scalar(
        select(func.count()).select_from(Approval).where(
            Approval.tenant_id == tenant, Approval.status == "PENDING"
        )
    ) or 0
    return {
        "agents": session.scalar(select(func.count()).select_from(Agent).where(Agent.tenant_id == tenant)) or 0,
        "pending_approvals": pending,
        "decisions": len(decisions),
        "allowed": sum(item.outcome == "ALLOW" for item in decisions),
        "denied": sum(item.outcome == "DENY" for item in decisions),
        "requires_approval": sum(item.outcome == "REQUIRE_APPROVAL" for item in decisions),
    }


@app.get(f"{API_PREFIX}/agents", dependencies=[Depends(require_operator)])
def list_agents(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    tenant = tenant_id(session)
    agents = session.scalars(select(Agent).where(Agent.tenant_id == tenant).order_by(Agent.created_at.desc())).all()
    return [{"id": str(item.id), "name": item.name, "enabled": item.enabled, "key_prefix": item.key_prefix} for item in agents]


@app.post(f"{API_PREFIX}/agents", dependencies=[Depends(require_operator)])
def create_agent(body: AgentInput, session: Session = Depends(get_session)) -> dict[str, str]:
    name = body.name.strip()
    tenant = tenant_id(session)
    key = issue_agent_key()
    agent = Agent(tenant_id=tenant, name=name, key_digest=digest_agent_key(key), key_prefix=key[:10])
    session.add(agent)
    try:
        append_audit(session, tenant, "AGENT_CREATED", {"name": name})
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Agent name already exists") from error
    return {"id": str(agent.id), "name": agent.name, "api_key": key}


@app.post(f"{API_PREFIX}/agents/{{agent_id}}/disable", dependencies=[Depends(require_operator)])
def disable_agent(agent_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    tenant = tenant_id(session)
    agent = session.scalar(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.enabled = False
    append_audit(session, tenant, "AGENT_DISABLED", {"agent_id": str(agent.id)})
    session.commit()
    return {"status": "disabled"}


@app.post(f"{API_PREFIX}/agents/{{agent_id}}/rotate-key", dependencies=[Depends(require_operator)])
def rotate_agent_key(agent_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    tenant = tenant_id(session)
    agent = session.scalar(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    key = issue_agent_key()
    agent.key_digest = digest_agent_key(key)
    agent.key_prefix = key[:10]
    agent.enabled = True
    append_audit(session, tenant, "AGENT_KEY_ROTATED", {"agent_id": str(agent.id)})
    session.commit()
    return {"id": str(agent.id), "api_key": key}


@app.get(f"{API_PREFIX}/policies", dependencies=[Depends(require_operator)])
def list_policies(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    tenant = tenant_id(session)
    versions = session.scalars(
        select(PolicyVersion).where(PolicyVersion.tenant_id == tenant).order_by(PolicyVersion.created_at.desc())
    ).all()
    return [{"id": str(row.id), "name": row.name, "version": row.version, "active": row.active, "rules": row.rules} for row in versions]


@app.post(f"{API_PREFIX}/policies", dependencies=[Depends(require_operator)])
def create_policy(body: PolicyInput, session: Session = Depends(get_session)) -> dict[str, Any]:
    rules = [rule.model_dump(exclude_none=True) for rule in body.rules]
    tenant = tenant_id(session)
    version = session.scalar(
        select(func.max(PolicyVersion.version)).where(PolicyVersion.tenant_id == tenant, PolicyVersion.name == body.name)
    ) or 0
    row = PolicyVersion(tenant_id=tenant, name=body.name, version=version + 1, active=False, rules=rules)
    session.add(row)
    append_audit(session, tenant, "POLICY_DRAFT_CREATED", {"policy": body.name, "version": version + 1})
    session.commit()
    return {"id": str(row.id), "name": row.name, "version": row.version, "active": row.active}


@app.post(f"{API_PREFIX}/policies/{{policy_id}}/validate", dependencies=[Depends(require_operator)])
def validate_policy(policy_id: UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    tenant = tenant_id(session)
    policy = session.scalar(select(PolicyVersion).where(
        PolicyVersion.id == policy_id, PolicyVersion.tenant_id == tenant
    ))
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    if not policy.rules:
        raise HTTPException(status_code=422, detail="Policy must contain at least one rule")
    return {"valid": True, "policy_version_id": str(policy.id), "rule_count": len(policy.rules)}


@app.post(f"{API_PREFIX}/policies/{{policy_id}}/activate", dependencies=[Depends(require_operator)])
def activate_policy(policy_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    tenant = tenant_id(session)
    row = session.scalar(select(PolicyVersion).where(PolicyVersion.id == policy_id, PolicyVersion.tenant_id == tenant))
    if row is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    session.scalars(
        select(PolicyVersion).where(PolicyVersion.tenant_id == tenant).with_for_update()
    ).all()
    session.execute(update(PolicyVersion).where(PolicyVersion.tenant_id == tenant).values(active=False))
    row.active = True
    append_audit(session, tenant, "POLICY_ACTIVATED", {"policy": row.name, "version": row.version})
    session.commit()
    return {"status": "active"}


@app.post(f"{API_PREFIX}/runtime/decisions")
def create_decision(
    body: DecisionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent: Agent = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if body.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Agent identity does not match credential")
    if not idempotency_key or len(idempotency_key) > 120:
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key is required")
    action = body.action.model_dump(mode="json")
    request_hash = canonical_hash({"tenant_id": str(agent.tenant_id), "agent_id": str(agent.id), "action": action})
    prior = session.scalar(select(RuntimeRequest).where(
        RuntimeRequest.tenant_id == agent.tenant_id, RuntimeRequest.idempotency_key == idempotency_key
    ))
    if prior is not None:
        if prior.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_KEY_REUSED")
        return request_result(session, prior)
    policy = session.scalar(select(PolicyVersion).where(
        PolicyVersion.tenant_id == agent.tenant_id, PolicyVersion.active.is_(True)
    ).order_by(PolicyVersion.created_at.desc()))
    if policy is None:
        raise HTTPException(status_code=503, detail="POLICY_UNAVAILABLE")
    risk_score, factors = risk_assessment(action)
    outcome, reasons = evaluate_policy(action, policy.rules, risk_score)
    request = RuntimeRequest(
        tenant_id=agent.tenant_id, agent_id=agent.id, idempotency_key=idempotency_key,
        request_hash=request_hash, action=action, state=outcome,
    )
    session.add(request)
    session.flush()
    decision = Decision(
        tenant_id=agent.tenant_id, request_id=request.id, policy_version_id=policy.id,
        outcome=outcome, reason_codes=reasons, risk_score=risk_score, risk_factors=factors,
    )
    session.add(decision)
    if outcome == "REQUIRE_APPROVAL":
        session.add(Approval(
            tenant_id=agent.tenant_id, request_id=request.id, action_hash=request_hash,
            policy_version_id=policy.id, expires_at=utc_now() + timedelta(minutes=APPROVAL_TTL_MINUTES),
        ))
    elif outcome == "ALLOW":
        session.add(ExecutionGrant(
            tenant_id=agent.tenant_id, request_id=request.id, action_hash=request_hash,
            policy_version_id=policy.id, expires_at=utc_now() + timedelta(minutes=DECISION_TTL_MINUTES),
        ))
    append_audit(session, agent.tenant_id, "DECISION_RECORDED", {
        "agent_id": str(agent.id), "decision": outcome, "reason_codes": reasons,
        "policy_version_id": str(policy.id), "risk_score": risk_score,
    }, request.id)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        prior_retry = session.scalar(select(RuntimeRequest).where(
            RuntimeRequest.tenant_id == agent.tenant_id, RuntimeRequest.idempotency_key == idempotency_key
        ))
        if prior_retry and prior_retry.request_hash == request_hash:
            return request_result(session, prior_retry)
        raise HTTPException(status_code=409, detail="IDEMPOTENCY_KEY_REUSED") from error
    return request_result(session, request)


@app.post(f"{API_PREFIX}/runtime/requests/{{request_id}}/execute")
def execute_request(
    request_id: UUID,
    agent: Agent = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    request = session.scalar(select(RuntimeRequest).where(
        RuntimeRequest.id == request_id, RuntimeRequest.tenant_id == agent.tenant_id,
        RuntimeRequest.agent_id == agent.id,
    ))
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    prior_execution = session.scalar(select(Execution).where(
        Execution.tenant_id == agent.tenant_id, Execution.request_id == request.id
    ))
    if prior_execution is not None:
        return {"status": prior_execution.status, "result": prior_execution.result, "replayed": True}
    decision = session.scalar(select(Decision).where(Decision.request_id == request.id))
    if decision is None or decision.outcome == "DENY":
        raise HTTPException(status_code=409, detail="Action is not authorized for execution")
    if decision.outcome == "REQUIRE_APPROVAL":
        approval = session.scalar(select(Approval).where(Approval.request_id == request.id))
        if approval is None or approval.status != "APPROVED" or approval.expires_at <= utc_now():
            raise HTTPException(status_code=409, detail="Approval is pending, rejected, or expired")
    policy = session.scalar(select(PolicyVersion).where(
        PolicyVersion.id == decision.policy_version_id, PolicyVersion.tenant_id == agent.tenant_id,
        PolicyVersion.active.is_(True),
    ).with_for_update())
    if policy is None:
        raise HTTPException(status_code=409, detail="Policy changed; submit a fresh decision")
    current_outcome, _ = evaluate_policy(request.action, policy.rules, decision.risk_score)
    if current_outcome == "DENY":
        raise HTTPException(status_code=409, detail="Current policy denies this action")
    grant = session.scalar(select(ExecutionGrant).where(
        ExecutionGrant.request_id == request.id, ExecutionGrant.tenant_id == agent.tenant_id,
        ExecutionGrant.action_hash == request.request_hash,
    ).with_for_update())
    if grant is None or grant.expires_at <= utc_now() or grant.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Execution grant is missing, expired, or consumed")
    consumed = session.execute(update(ExecutionGrant).where(
        ExecutionGrant.id == grant.id, ExecutionGrant.status == "ACTIVE",
        ExecutionGrant.expires_at > utc_now(),
    ).values(status="CONSUMED", consumed_at=utc_now()))
    if consumed.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=409, detail="Execution grant was already consumed")
    result = execute_mock_action(request.action)
    execution = Execution(tenant_id=agent.tenant_id, request_id=request.id, status="EXECUTED", result=result)
    session.add(execution)
    request.state = "EXECUTED"
    append_audit(session, agent.tenant_id, "MOCK_EXECUTION_COMPLETED", result, request.id)
    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(status_code=503, detail="Execution could not be durably recorded") from error
    return {"status": execution.status, "result": result, "replayed": False}


@app.get(f"{API_PREFIX}/approvals", dependencies=[Depends(require_operator)])
def list_approvals(status: str = "PENDING", session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    tenant = tenant_id(session)
    rows = session.scalars(select(Approval).where(
        Approval.tenant_id == tenant, Approval.status == status
    ).order_by(Approval.created_at.desc())).all()
    results = []
    for approval in rows:
        request = session.get(RuntimeRequest, approval.request_id)
        decision = session.scalar(select(Decision).where(Decision.request_id == approval.request_id))
        results.append({
            "id": str(approval.id), "request_id": str(approval.request_id), "status": approval.status,
            "action": request.action if request else {}, "risk_score": decision.risk_score if decision else 0,
            "reason_codes": decision.reason_codes if decision else [],
            "policy_version_id": str(approval.policy_version_id), "expires_at": approval.expires_at.isoformat(),
            "risk_factors": decision.risk_factors if decision else [],
            "policy_rules": (
                session.get(PolicyVersion, approval.policy_version_id).rules
                if session.get(PolicyVersion, approval.policy_version_id) else []
            ),
            "execution_status": (
                session.scalar(select(Execution.status).where(Execution.request_id == approval.request_id))
            ),
        })
    return results


@app.post(f"{API_PREFIX}/approvals/{{approval_id}}/{{transition}}", dependencies=[Depends(require_operator)])
def transition_approval(
    approval_id: UUID, transition: str, body: ApprovalInput, session: Session = Depends(get_session)
) -> dict[str, str]:
    if transition not in {"approve", "reject"}:
        raise HTTPException(status_code=404, detail="Approval action not found")
    tenant = tenant_id(session)
    approval = session.scalar(select(Approval).where(Approval.id == approval_id, Approval.tenant_id == tenant))
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "PENDING" or approval.expires_at <= utc_now():
        raise HTTPException(status_code=409, detail="Approval is no longer pending")
    request = session.scalar(select(RuntimeRequest).where(
        RuntimeRequest.id == approval.request_id, RuntimeRequest.tenant_id == tenant
    ))
    if request is None or request.request_hash != approval.action_hash:
        raise HTTPException(status_code=409, detail="Approved action has changed")
    policy = session.scalar(select(PolicyVersion).where(
        PolicyVersion.id == approval.policy_version_id, PolicyVersion.tenant_id == tenant,
        PolicyVersion.active.is_(True),
    ).with_for_update())
    if policy is None:
        raise HTTPException(status_code=409, detail="Policy changed; submit a fresh decision")
    decision = session.scalar(select(Decision).where(Decision.request_id == request.id))
    if decision is None:
        raise HTTPException(status_code=503, detail="Decision record unavailable")
    outcome, _ = evaluate_policy(request.action, policy.rules, decision.risk_score)
    if outcome == "DENY":
        raise HTTPException(status_code=409, detail="Current policy denies this action")
    next_status = "APPROVED" if transition == "approve" else "REJECTED"
    transitioned = session.execute(update(Approval).where(
        Approval.id == approval.id, Approval.tenant_id == tenant,
        Approval.status == "PENDING", Approval.expires_at > utc_now(),
    ).values(status=next_status, rationale=body.rationale))
    if transitioned.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=409, detail="Approval is no longer pending")
    approval.status = next_status
    request.state = approval.status
    if transition == "approve":
        session.add(ExecutionGrant(
            tenant_id=tenant, request_id=request.id, action_hash=request.request_hash,
            policy_version_id=policy.id, expires_at=utc_now() + timedelta(minutes=DECISION_TTL_MINUTES),
        ))
    append_audit(session, tenant, f"APPROVAL_{approval.status}", {
        "approval_id": str(approval.id), "rationale": body.rationale,
        "actor": "local_operator", "actor_credential_id": digest_operator_credential()[:16],
    }, request.id)
    session.commit()
    return {"status": approval.status}


@app.get(f"{API_PREFIX}/audit-events", dependencies=[Depends(require_operator)])
def list_audit_events(limit: int = 50, session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    tenant = tenant_id(session)
    events = session.scalars(select(AuditEvent).where(
        AuditEvent.tenant_id == tenant
    ).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [{
        "id": str(row.id), "request_id": str(row.request_id) if row.request_id else None,
        "event_type": row.event_type, "payload": row.payload, "created_at": row.created_at.isoformat(),
    } for row in events]
