import os
import sqlite3
import time
from typing import Any
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

DB_PATH = os.environ.get("ERP_DB_PATH", "/tmp/northstar_erp.db")
ERP_SHARED_SECRET = os.environ.get("ARG_ERP_SHARED_SECRET", "northstar-enterprise-shared-secret-2026")

app = FastAPI(
    title="Northstar Enterprise ERP (External Standalone System)",
    description="Independent enterprise ERP representing a real third-party system governed by ARG.",
    version="1.0.0",
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_customers (
            customer_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tier TEXT NOT NULL,
            status TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_invoices (
            invoice_code TEXT PRIMARY KEY,
            customer_code TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            refund_status TEXT NOT NULL,
            refund_amount INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (customer_code) REFERENCES erp_customers (customer_code)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_consumed_grants (
            grant_id TEXT PRIMARY KEY,
            consumed_at INTEGER NOT NULL
        )
    """)

    # Seed default enterprise records if empty
    cursor.execute("SELECT count(*) FROM erp_customers")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO erp_customers (customer_code, name, tier, status, email)
            VALUES 
                ('CUST-1042', 'Global Logistics Ltd', 'Standard', 'ACTIVE', 'billing@globallogistics.com'),
                ('CUST-2088', 'Acme Corporation', 'Enterprise', 'ACTIVE', 'finance@acme.corp')
        """)
        cursor.execute("""
            INSERT INTO erp_invoices (invoice_code, customer_code, amount, status, refund_status, refund_amount, notes)
            VALUES 
                ('INV-1042', 'CUST-1042', 2500, 'PAID', 'NONE', 0, 'Standard logistics software subscription'),
                ('INV-2088', 'CUST-2088', 50000, 'PAID', 'NONE', 0, 'Enterprise annual SLA contract')
        """)
        conn.commit()
    conn.close()


init_db()


# Cryptographic Proof Token Verification
def require_arg_governance(
    x_arg_grant_token: str | None = Header(default=None, alias="X-ARG-Grant-Token")
) -> dict[str, Any]:
    if not x_arg_grant_token:
        raise HTTPException(
            status_code=403,
            detail="DIRECT_ACCESS_FORBIDDEN: External ERP requires verified ARG Grant Token (X-ARG-Grant-Token header missing).",
        )

    # Import dynamically from ARG security token spec
    try:
        from apps.api.app.security_tokens import verify_proof_token
        payload = verify_proof_token(x_arg_grant_token, ERP_SHARED_SECRET)
    except Exception as exc:
        raise HTTPException(
            status_code=403,
            detail=f"SECURITY_VIOLATION: Invalid or forged ARG Grant Token ({str(exc)})",
        )

    # Replay protection: verify grant token hasn't been consumed already
    request_id = payload.get("rid")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT consumed_at FROM erp_consumed_grants WHERE grant_id = ?", (request_id,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail="REPLAY_ATTACK_DETECTED: This ARG grant token has already been executed in ERP.",
        )

    cursor.execute(
        "INSERT INTO erp_consumed_grants (grant_id, consumed_at) VALUES (?, ?)",
        (request_id, int(time.time())),
    )
    conn.commit()
    conn.close()

    return payload


# Schema models
class RefundPayload(BaseModel):
    amount: int
    reason: str | None = "Processed via autonomous agent"


class StatusPayload(BaseModel):
    status: str
    reason: str | None = None


# Endpoints
@app.get("/health")
def health():
    return {"status": "ok", "system": "Northstar Enterprise ERP", "port": 8080}


@app.get("/api/v1/erp/customers")
def get_customers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_code, name, tier, status, email FROM erp_customers")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


@app.get("/api/v1/erp/invoices")
def get_invoices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT invoice_code, customer_code, amount, status, refund_status, refund_amount, notes 
        FROM erp_invoices
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


@app.post("/api/v1/erp/invoices/{invoice_code}/refund")
def refund_invoice(
    invoice_code: str,
    payload: RefundPayload,
    governance: dict[str, Any] = Depends(require_arg_governance),
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_invoices WHERE invoice_code = ?", (invoice_code,))
    invoice = cursor.fetchone()
    if not invoice:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_code} not found in ERP")

    cursor.execute(
        """
        UPDATE erp_invoices 
        SET refund_status = 'REFUNDED', 
            refund_amount = ?, 
            notes = ?
        WHERE invoice_code = ?
    """,
        (
            payload.amount,
            f"Authorized by ARG (Req: {governance.get('rid')}). Rationale: {payload.reason}",
            invoice_code,
        ),
    )
    conn.commit()

    cursor.execute("SELECT * FROM erp_invoices WHERE invoice_code = ?", (invoice_code,))
    updated = dict(cursor.fetchone())
    conn.close()

    return {
        "status": "SUCCESS",
        "system": "Northstar Enterprise ERP",
        "transaction_id": f"TXN-ERP-{int(time.time())}",
        "message": f"Successfully refunded ₹{payload.amount:,} on invoice {invoice_code}",
        "invoice": updated,
        "arg_governance": {
            "verified_request_id": governance.get("rid"),
            "policy_hash": governance.get("ahash"),
        },
    }


@app.post("/api/v1/erp/customers/{customer_code}/status")
def update_customer_status(
    customer_code: str,
    payload: StatusPayload,
    governance: dict[str, Any] = Depends(require_arg_governance),
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM erp_customers WHERE customer_code = ?", (customer_code,))
    customer = cursor.fetchone()
    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Customer {customer_code} not found in ERP")

    cursor.execute(
        "UPDATE erp_customers SET status = ? WHERE customer_code = ?",
        (payload.status.upper(), customer_code),
    )
    conn.commit()

    cursor.execute("SELECT * FROM erp_customers WHERE customer_code = ?", (customer_code,))
    updated = dict(cursor.fetchone())
    conn.close()

    return {
        "status": "SUCCESS",
        "system": "Northstar Enterprise ERP",
        "message": f"Customer {customer_code} status transitioned to {payload.status.upper()}",
        "customer": updated,
        "arg_governance": {
            "verified_request_id": governance.get("rid"),
        },
    }
