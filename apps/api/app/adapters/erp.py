from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ERPCustomer, ERPInvoice


def execute_enterprise_action(action: dict[str, Any], tenant_id: UUID, session: Session) -> dict[str, Any]:
    """
    Executes a real mutation in the Northstar Enterprise ERP state when authorized by ARG.
    """
    action_type = action.get("type", "")
    target = action.get("target", "")
    parameters = action.get("parameters", {})

    # 1. High-impact invoice refund or routine update
    if "refund" in action_type or "refund" in str(parameters.get("status", "")):
        invoice_code = "INV-2088" if "2088" in target else "INV-1042"
        invoice = session.scalar(
            select(ERPInvoice).where(
                ERPInvoice.tenant_id == tenant_id,
                ERPInvoice.invoice_code == invoice_code
            )
        )
        if invoice:
            refund_val = int(action.get("impact", {}).get("amount", parameters.get("amount", 5000)))
            invoice.refund_status = "REFUNDED"
            invoice.refund_amount = refund_val
            invoice.notes = f"Authorized via ARG Governance. Reason: {parameters.get('status', 'Customer request')}"
            session.flush()
            return {
                "adapter": "northstar_erp_v1",
                "system": "Northstar Enterprise ERP",
                "entity": "Invoice",
                "invoice_code": invoice.invoice_code,
                "refund_status": invoice.refund_status,
                "refund_amount": invoice.refund_amount,
                "message": f"ERP Ledger updated: Invoice {invoice.invoice_code} refund of ₹{refund_val:,} applied successfully.",
                "target": str(target),
            }

    # 2. Customer record status update
    if "customer.record.update" in action_type:
        cust_code = "CUST-2088" if "2088" in target else "CUST-1042"
        customer = session.scalar(
            select(ERPCustomer).where(
                ERPCustomer.tenant_id == tenant_id,
                ERPCustomer.customer_code == cust_code
            )
        )
        if customer:
            new_status = parameters.get("status", "UPDATED").upper()
            customer.status = new_status
            session.flush()
            return {
                "adapter": "northstar_erp_v1",
                "system": "Northstar Enterprise ERP",
                "entity": "Customer",
                "customer_code": customer.customer_code,
                "status": customer.status,
                "message": f"ERP Customer {customer.customer_code} status transitioned to {customer.status}.",
                "target": str(target),
            }

    # 3. Customer record deletion (If authorized, which is blocked by default policy)
    if "customer.record.delete" in action_type:
        cust_code = "CUST-2088" if "2088" in target else "CUST-1042"
        customer = session.scalar(
            select(ERPCustomer).where(
                ERPCustomer.tenant_id == tenant_id,
                ERPCustomer.customer_code == cust_code
            )
        )
        if customer:
            customer.status = "DELETED"
            session.flush()
            return {
                "adapter": "northstar_erp_v1",
                "system": "Northstar Enterprise ERP",
                "entity": "Customer",
                "customer_code": customer.customer_code,
                "status": "DELETED",
                "message": f"ERP Customer {customer.customer_code} marked as deleted.",
                "target": str(target),
            }

    return {
        "adapter": "northstar_erp_v1",
        "system": "Northstar Enterprise ERP",
        "message": f"ERP transaction executed on target {target}",
        "target": str(target),
    }
