import json
import os
from collections.abc import Generator
from uuid import uuid4

os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["OPERATOR_TOKEN"] = "test-operator-token"
os.environ["AGENT_KEY_PEPPER"] = "test-pepper-value-for-unit-tests"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import Agent, AuditEvent, Execution, Organization, PolicyVersion, RuntimeRequest
from app.security import digest_agent_key

AGENT_KEY = "arg_test_agent_key_for_runtime_tests"
DENY_RULES = [{"action_type": "customer.record.delete", "effect": "DENY", "reason_code": "NO_DELETE"}]
ALLOW_RULES = [
    {"action_type": "customer.record.update", "effect": "ALLOW", "reason_code": "UPDATE_ALLOWED"},
    {"action_type": "customer.record.delete", "effect": "DENY", "reason_code": "NO_DELETE"},
]
APPROVAL_RULES = [
    {"action_type": "customer.record.update", "effect": "REQUIRE_APPROVAL", "min_risk": 40, "reason_code": "REVIEW"},
    {"action_type": "customer.record.update", "effect": "ALLOW", "reason_code": "UPDATE_ALLOWED"},
]


@pytest.fixture
def client() -> Generator[tuple[TestClient, sessionmaker[Session], str], None, None]:
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(test_engine)
    test_sessions = sessionmaker(bind=test_engine, expire_on_commit=False)
    with test_sessions.begin() as session:
        tenant = Organization(name=f"Test tenant {uuid4()}")
        session.add(tenant)
        session.flush()
        agent = Agent(
            tenant_id=tenant.id, name="Test agent", key_digest=digest_agent_key(AGENT_KEY),
            key_prefix=AGENT_KEY[:10],
        )
        session.add(agent)
        session.flush()
        agent_id = str(agent.id)

    def override_session() -> Generator[Session, None, None]:
        with test_sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client, test_sessions, agent_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def add_policy(sessions: sessionmaker[Session], rules: list[dict[str, object]]) -> None:
    with sessions.begin() as session:
        tenant = session.scalar(select(Organization))
        assert tenant is not None
        session.add(PolicyVersion(tenant_id=tenant.id, name="Test policy", version=1, active=True, rules=rules))


def action(action_type: str = "customer.record.update", amount: int = 0) -> dict[str, object]:
    return {
        "type": action_type, "target": "demo-crm/customer/1", "parameters": {"status": "review"},
        "environment": "production" if amount else "development",
        "data_classification": "confidential" if amount else "internal",
        "impact": {"amount": amount, "currency": "INR"},
    }


def decide(client: TestClient, agent_id: str, action_payload: dict[str, object], key: str = "request-1"):
    return client.post(
        "/api/v1/runtime/decisions", headers={"Authorization": f"Bearer {AGENT_KEY}", "Idempotency-Key": key},
        json={"agent_id": agent_id, "action": action_payload},
    )


def test_allow_can_execute_once_and_is_audited(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    response = decide(api, agent_id, action())
    assert response.status_code == 200
    assert response.json()["decision"] == "ALLOW"
    request_id = response.json()["request_id"]
    headers = {"Authorization": f"Bearer {AGENT_KEY}"}
    first = api.post(f"/api/v1/runtime/requests/{request_id}/execute", headers=headers)
    second = api.post(f"/api/v1/runtime/requests/{request_id}/execute", headers=headers)
    assert first.status_code == 200 and first.json()["status"] == "EXECUTED"
    assert second.status_code == 200 and second.json()["replayed"] is True
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Execution)) == 1
        assert session.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_approval_pauses_then_approves_and_executes(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, APPROVAL_RULES)
    response = decide(api, agent_id, action(amount=5000))
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "REQUIRE_APPROVAL"
    headers = {"Authorization": f"Bearer {AGENT_KEY}"}
    blocked = api.post(f"/api/v1/runtime/requests/{result['request_id']}/execute", headers=headers)
    assert blocked.status_code == 409
    approvals = api.get("/api/v1/approvals", headers={"Authorization": "Bearer test-operator-token"})
    assert approvals.status_code == 200 and len(approvals.json()) == 1
    approval_id = approvals.json()[0]["id"]
    approved = api.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers={"Authorization": "Bearer test-operator-token"}, json={"rationale": "Reviewed"},
    )
    assert approved.status_code == 200
    executed = api.post(f"/api/v1/runtime/requests/{result['request_id']}/execute", headers=headers)
    assert executed.status_code == 200
    assert executed.json()["status"] == "EXECUTED"


def test_explicit_deny_rule_never_executes(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    denied = decide(api, agent_id, action("customer.record.delete"), "delete-1")
    assert denied.status_code == 200 and denied.json()["decision"] == "DENY"
    blocked = api.post(
        f"/api/v1/runtime/requests/{denied.json()['request_id']}/execute",
        headers={"Authorization": f"Bearer {AGENT_KEY}"},
    )
    assert blocked.status_code == 409


def test_unmatched_action_uses_default_deny(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    response = decide(api, agent_id, action("customer.record.export"), "unmatched-1")
    assert response.status_code == 200
    assert response.json()["decision"] == "DENY"
    assert response.json()["reason_codes"] == ["DEFAULT_DENY"]


def test_idempotency_same_payload_returns_original_request(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    first = decide(api, agent_id, action(), "same-request")
    replay = decide(api, agent_id, action(), "same-request")
    assert first.status_code == replay.status_code == 200
    assert first.json()["request_id"] == replay.json()["request_id"]


def test_non_finite_impact_is_rejected(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    for value in (float("nan"), float("inf")):
        payload = {"agent_id": agent_id, "action": {**action(), "impact": {"amount": value, "currency": "INR"}}}
        response = api.post(
            "/api/v1/runtime/decisions",
            headers={"Authorization": f"Bearer {AGENT_KEY}", "Idempotency-Key": f"non-finite-{value}", "Content-Type": "application/json"},
            content=json.dumps(payload, allow_nan=True),
        )
        assert response.status_code == 422


def test_explicit_deny_dominates_matching_allow(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, [
        {"action_type": "customer.record.update", "effect": "ALLOW", "reason_code": "BROAD_ALLOW"},
        {"action_type": "customer.record.update", "effect": "DENY", "reason_code": "SPECIFIC_DENY"},
    ])
    response = decide(api, agent_id, action())
    assert response.status_code == 200
    assert response.json()["decision"] == "DENY"
    assert response.json()["reason_codes"] == ["SPECIFIC_DENY"]


def test_idempotency_key_changed_body_returns_conflict(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    assert decide(api, agent_id, action(), "stable-key").status_code == 200
    conflict = decide(api, agent_id, action(amount=10), "stable-key")
    assert conflict.status_code == 409


def test_missing_policy_fails_closed(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, _, agent_id = client
    response = decide(api, agent_id, action())
    assert response.status_code == 503


def test_audit_failure_rolls_back_decision(client: tuple[TestClient, sessionmaker[Session], str], monkeypatch: pytest.MonkeyPatch) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Injected audit persistence failure")

    monkeypatch.setattr("app.main.append_audit", fail_audit)
    with pytest.raises(RuntimeError, match="Injected audit persistence failure"):
        decide(api, agent_id, action())
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(RuntimeRequest)) == 0
        assert session.scalar(select(func.count()).select_from(Execution)) == 0


def test_non_finite_or_negative_impact_is_rejected(client: tuple[TestClient, sessionmaker[Session], str]) -> None:
    api, sessions, agent_id = client
    add_policy(sessions, ALLOW_RULES)
    invalid = action(amount=-1)
    response = decide(api, agent_id, invalid)
    assert response.status_code == 422
