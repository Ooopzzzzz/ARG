import os
import sqlite3
import time
from typing import Any
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
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
@app.get("/", response_class=HTMLResponse)
def erp_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_code, name, tier, status, email FROM erp_customers")
    customers = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT invoice_code, customer_code, amount, status, refund_status, refund_amount, notes FROM erp_invoices")
    invoices = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT grant_id, consumed_at FROM erp_consumed_grants ORDER BY consumed_at DESC")
    consumed = [dict(row) for row in cursor.fetchall()]
    conn.close()

    cust_rows = "".join(
        f"<tr><td><code>{c['customer_code']}</code></td><td><b>{c['name']}</b></td><td>{c['tier']}</td><td><span class='badge {c['status'].lower()}'>{c['status']}</span></td><td>{c['email']}</td></tr>"
        for c in customers
    )
    inv_rows_list = []
    for i in invoices:
        ref_text = f" (₹{i['refund_amount']:,})" if i['refund_status'] == 'REFUNDED' else ""
        inv_rows_list.append(
            f"<tr><td><code>{i['invoice_code']}</code></td><td>{i['customer_code']}</td><td><b>₹{i['amount']:,}</b></td>"
            f"<td><span class='badge paid'>{i['status']}</span></td>"
            f"<td><span class='badge {i['refund_status'].lower()}'>{i['refund_status']}{ref_text}</span></td>"
            f"<td><small>{i['notes'] or 'Standard invoice'}</small></td></tr>"
        )
    inv_rows = "".join(inv_rows_list)
    grant_rows = "".join(
        f"<tr><td><code>{g['grant_id']}</code></td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(g['consumed_at']))}</td><td><span class='badge verified'>VERIFIED BY ARG</span></td></tr>"
        for g in consumed
    ) if consumed else "<tr><td colspan='3' style='text-align:center; color:#888;'>No cryptographic tokens consumed yet.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Northstar Enterprise ERP (System of Record)</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; }}
    .header {{ background: #1e293b; padding: 20px 32px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }}
    .brand {{ font-size: 20px; font-weight: 700; letter-spacing: -0.5px; display: flex; align-items: center; gap: 12px; }}
    .brand span {{ background: #3b82f6; color: white; padding: 4px 10px; border-radius: 6px; font-size: 14px; }}
    .pill {{ background: #10b981; color: #022c22; font-weight: 600; padding: 4px 12px; border-radius: 12px; font-size: 12px; }}
    .container {{ max-width: 1200px; margin: 32px auto; padding: 0 24px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 24px; margin-bottom: 24px; }}
    .card-title {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
    th {{ background: #0f172a; color: #94a3b8; padding: 12px; border-bottom: 1px solid #334155; }}
    td {{ padding: 12px; border-bottom: 1px solid #334155; }}
    code {{ background: #0f172a; padding: 3px 6px; border-radius: 4px; font-size: 12px; color: #38bdf8; }}
    .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
    .badge.active, .badge.paid {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .badge.refunded {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
    .badge.none {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }}
    .badge.verified {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .security-banner {{ background: #0284c7; padding: 12px 18px; border-radius: 8px; font-size: 13px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
    .btn-refresh {{ background: #3b82f6; border: none; color: white; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; text-decoration: none; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="brand">
      <span>ERP</span> Northstar Global Logistics — Enterprise ERP
    </div>
    <div>
      <span class="pill">STANDALONE PORT 8080</span>
      <a href="/" class="btn-refresh" style="margin-left: 12px;">↻ Refresh Ledger</a>
    </div>
  </div>

  <div class="container">
    <div class="security-banner">
      <div>🛡️ <b>ARG RUNTIME GOVERNANCE ENFORCED:</b> Direct external write access is strictly forbidden (HTTP 403). Mutations require HMAC-SHA256 verified single-use <code>X-ARG-Grant-Token</code>.</div>
    </div>

    <div class="card">
      <div class="card-title">Financial Invoices & Ledger Status</div>
      <table>
        <thead>
          <tr><th>Invoice Code</th><th>Customer</th><th>Invoice Amount</th><th>Billing Status</th><th>Refund Ledger State</th><th>Notes</th></tr>
        </thead>
        <tbody>{inv_rows}</tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title">Customer Accounts Registry</div>
      <table>
        <thead>
          <tr><th>Customer Code</th><th>Company Name</th><th>Tier</th><th>Account Status</th><th>Billing Email</th></tr>
        </thead>
        <tbody>{cust_rows}</tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title">Cryptographic Execution Grants Verified & Consumed</div>
      <table>
        <thead>
          <tr><th>ARG Grant Request ID</th><th>Execution Timestamp</th><th>Cryptographic Security Status</th></tr>
        </thead>
        <tbody>{grant_rows}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


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
