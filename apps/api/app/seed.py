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
    {
        "action_type": "customer.record.delete",
        "effect": "DENY",
        "reason_code": "DESTRUCTIVE_ACTION_BLOCKED",
    },
    {
        "action_type": "erp.invoice.refund",
        "effect": "REQUIRE_APPROVAL",
        "min_risk": 40,
        "reason_code": "HIGH_VALUE_REFUND_REVIEW",
    },
    {
        "action_type": "erp.invoice.refund",
        "effect": "ALLOW",
        "reason_code": "ROUTINE_REFUND_ALLOWED",
    },
    {
        "action_type": "customer.record.update",
        "effect": "REQUIRE_APPROVAL",
        "min_risk": 40,
        "reason_code": "HIGH_IMPACT_REVIEW",
    },
    {
        "action_type": "customer.record.update",
        "effect": "ALLOW",
        "reason_code": "CUSTOMER_UPDATE_ALLOWED",
    },
]


def seed() -> None:
    demo_key = os.environ.get("ARG_DEMO_AGENT_KEY", "")
    if len(demo_key) < 24:
        raise RuntimeError("Set ARG_DEMO_AGENT_KEY to a generated local secret before seeding")
    with SessionLocal.begin() as session:
        organization = session.scalar(
            select(Organization).where(Organization.name == DEMO_ORGANIZATION)
        )
        if organization is None:
            organization = Organization(name=DEMO_ORGANIZATION)
            session.add(organization)
            session.flush()
        agent = session.scalar(
            select(Agent).where(Agent.tenant_id == organization.id, Agent.name == DEMO_AGENT)
        )
        if agent is None:
            agent = Agent(
                tenant_id=organization.id,
                name=DEMO_AGENT,
                key_digest=digest_agent_key(demo_key),
                key_prefix=demo_key[:10],
            )
            session.add(agent)
        elif agent.key_digest != digest_agent_key(demo_key):
            agent.key_digest = digest_agent_key(demo_key)
            agent.key_prefix = demo_key[:10]
            agent.enabled = True
        policy = session.scalar(
            select(PolicyVersion).where(
                PolicyVersion.tenant_id == organization.id,
                PolicyVersion.name == DEMO_POLICY,
                PolicyVersion.active.is_(True),
            )
        )
        if policy is None:
            policy = PolicyVersion(
                tenant_id=organization.id,
                name=DEMO_POLICY,
                version=1,
                active=True,
                rules=DEMO_RULES,
            )
            session.add(policy)
        else:
            policy.rules = DEMO_RULES

        from app.models import ERPCustomer, ERPInvoice
        cust1 = session.scalar(select(ERPCustomer).where(ERPCustomer.tenant_id == organization.id, ERPCustomer.customer_code == "CUST-1042"))
        if cust1 is None:
            cust1 = ERPCustomer(
                tenant_id=organization.id,
                customer_code="CUST-1042",
                name="Acme Retail Solutions",
                status="ACTIVE",
                credit_limit=150000,
                current_balance=24500,
            )
            session.add(cust1)
            session.flush()

        cust2 = session.scalar(select(ERPCustomer).where(ERPCustomer.tenant_id == organization.id, ERPCustomer.customer_code == "CUST-2088"))
        if cust2 is None:
            cust2 = ERPCustomer(
                tenant_id=organization.id,
                customer_code="CUST-2088",
                name="Global Telecom Enterprise",
                status="ACTIVE",
                credit_limit=500000,
                current_balance=185000,
            )
            session.add(cust2)
            session.flush()

        inv1 = session.scalar(select(ERPInvoice).where(ERPInvoice.tenant_id == organization.id, ERPInvoice.invoice_code == "INV-1042"))
        if inv1 is None:
            inv1 = ERPInvoice(
                tenant_id=organization.id,
                invoice_code="INV-1042",
                customer_id=cust1.id,
                amount=1500,
                currency="INR",
                status="PAID",
                refund_status="NONE",
                refund_amount=0,
                notes="Standard logistics supply package",
            )
            session.add(inv1)

        inv2 = session.scalar(select(ERPInvoice).where(ERPInvoice.tenant_id == organization.id, ERPInvoice.invoice_code == "INV-2088"))
        if inv2 is None:
            inv2 = ERPInvoice(
                tenant_id=organization.id,
                invoice_code="INV-2088",
                customer_id=cust2.id,
                amount=50000,
                currency="INR",
                status="PAID",
                refund_status="NONE",
                refund_amount=0,
                notes="Enterprise freight & dedicated corridor contract",
            )
            session.add(inv2)

    logging.getLogger(__name__).info(
        "Seeded tenant=%s agent=%s active_policy=%s with ERP data", DEMO_ORGANIZATION, DEMO_AGENT, DEMO_POLICY
    )


if __name__ == "__main__":
    seed()

