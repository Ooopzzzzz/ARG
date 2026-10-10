import logging
import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Agent, Organization, PolicyVersion
from app.security import digest_agent_key

DEMO_ORGANIZATION = "Northstar Demo"
DEMO_AGENT = "Customer Operations Agent"
DEMO_POLICY = "Customer Operations Guardrails"

DEMO_RULES = [
    {"action_type": "customer.record.delete", "effect": "DENY", "reason_code": "DESTRUCTIVE_ACTION_BLOCKED"},
    {"action_type": "customer.record.update", "effect": "REQUIRE_APPROVAL", "min_risk": 40, "reason_code": "HIGH_IMPACT_REVIEW"},
    {"action_type": "customer.record.update", "effect": "ALLOW", "reason_code": "CUSTOMER_UPDATE_ALLOWED"},
]


def seed() -> None:
    demo_key = os.environ.get("ARG_DEMO_AGENT_KEY", "")
    if len(demo_key) < 24:
        raise RuntimeError("Set ARG_DEMO_AGENT_KEY to a generated local secret before seeding")
    with SessionLocal.begin() as session:
        organization = session.scalar(select(Organization).where(Organization.name == DEMO_ORGANIZATION))
        if organization is None:
            organization = Organization(name=DEMO_ORGANIZATION)
            session.add(organization)
            session.flush()
        agent = session.scalar(select(Agent).where(Agent.tenant_id == organization.id, Agent.name == DEMO_AGENT))
        if agent is None:
            agent = Agent(
                tenant_id=organization.id, name=DEMO_AGENT,
                key_digest=digest_agent_key(demo_key), key_prefix=demo_key[:10],
            )
            session.add(agent)
        elif agent.key_digest != digest_agent_key(demo_key):
            agent.key_digest = digest_agent_key(demo_key)
            agent.key_prefix = demo_key[:10]
            agent.enabled = True
        policy = session.scalar(select(PolicyVersion).where(
            PolicyVersion.tenant_id == organization.id, PolicyVersion.name == DEMO_POLICY,
            PolicyVersion.active.is_(True),
        ))
        if policy is None:
            policy = PolicyVersion(
                tenant_id=organization.id, name=DEMO_POLICY, version=1, active=True,
                rules=DEMO_RULES,
            )
            session.add(policy)
    logging.getLogger(__name__).info(
        "Seeded tenant=%s agent=%s active_policy=%s", DEMO_ORGANIZATION, DEMO_AGENT, DEMO_POLICY
    )


if __name__ == "__main__":
    seed()
