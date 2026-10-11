import os
import re
import sqlite3
import time
from html import escape
from typing import Any
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.environ.get("ERP_DB_PATH", "/tmp/northstar_erp.db")
ERP_SHARED_SECRET = os.environ.get("ARG_ERP_SHARED_SECRET", "northstar-enterprise-shared-secret-2026")

app = FastAPI(
    title="Northstar Freight Core ERP",
    description="Authoritative enterprise freight ledger governed by ARG runtime tokens.",
    version="2.0.0",
)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


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

    try:
        from apps.api.app.security_tokens import verify_proof_token
        payload = verify_proof_token(x_arg_grant_token, ERP_SHARED_SECRET)
    except Exception as exc:
        raise HTTPException(
            status_code=403,
            detail=f"SECURITY_VIOLATION: Invalid or forged ARG Grant Token ({str(exc)})",
        )

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
    cursor.execute("SELECT customer_code, name, tier, status, email FROM erp_customers ORDER BY customer_code")
    customers = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT invoice_code, customer_code, amount, status, refund_status, refund_amount, notes FROM erp_invoices ORDER BY invoice_code")
    invoices = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT grant_id, consumed_at FROM erp_consumed_grants ORDER BY consumed_at DESC")
    consumed = [dict(row) for row in cursor.fetchall()]
    conn.close()

    def text(value: object) -> str:
        return escape(str(value), quote=True)

    def status_class(value: str) -> str:
        normalized = value.upper()
        if normalized in {"PAID", "ACTIVE", "REFUNDED", "VERIFIED"}:
            return "badge-spruce"
        if normalized in {"PENDING", "REVIEW"}:
            return "badge-brass"
        if normalized in {"SUSPENDED", "FAILED", "REJECTED"}:
            return "badge-rust"
        return "badge-neutral"

    invoice_rows = []
    for invoice in invoices:
        invoice_code = text(invoice["invoice_code"])
        customer_code = text(invoice["customer_code"])
        amount = int(invoice["amount"])
        refund_status = str(invoice["refund_status"])
        refund_amount = int(invoice["refund_amount"])
        is_refunded = refund_status.upper() == "REFUNDED"
        refund_badge_class = "badge-rust" if is_refunded else "badge-neutral"
        refund_label = f"REFUNDED (-₹{refund_amount:,})" if is_refunded else "NONE / UNPAID"
        grant_note = text(invoice["notes"] or "Standard ledger entry")
        invoice_rows.append(
            f'<tr class="ledger-row" data-code="{invoice_code}" data-cust="{customer_code}" '
            f'data-amount="₹{amount:,}" data-refund="{refund_label}" data-notes="{grant_note}" '
            f'data-search="{invoice_code} {customer_code} {refund_status}">'
            f'<td><code class="code-primary">{invoice_code}</code></td>'
            f'<td><strong class="cust-code">{customer_code}</strong></td>'
            f'<td class="amt-col">₹{amount:,}</td>'
            f'<td><span class="badge {status_class(str(invoice["status"]))}">{text(invoice["status"])}</span></td>'
            f'<td><span class="badge {refund_badge_class}">{text(refund_label)}</span></td>'
            f'<td class="notes-cell">{grant_note}</td>'
            f'</tr>'
        )

    customer_rows = []
    for customer in customers:
        customer_code = text(customer["customer_code"])
        customer_name = text(customer["name"])
        customer_rows.append(
            f'<tr class="ledger-row" data-search="{customer_code} {customer_name} {text(customer["email"])}">'
            f'<td><code class="code-primary">{customer_code}</code></td>'
            f'<td><strong>{customer_name}</strong><small class="subtext">{text(customer["email"])}</small></td>'
            f'<td><span class="tier-tag">{text(customer["tier"])}</span></td>'
            f'<td><span class="badge {status_class(str(customer["status"]))}">{text(customer["status"])}</span></td>'
            f'</tr>'
        )

    grant_rows = []
    for grant in consumed:
        grant_id = text(grant["grant_id"])
        granted_at = int(grant["consumed_at"])
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(granted_at))
        ts_str = time.strftime("%d %b %Y · %H:%M:%S", time.localtime(granted_at))
        grant_rows.append(
            f'<tr class="ledger-row" data-search="{grant_id}">'
            f'<td><code>{grant_id}</code></td>'
            f'<td><time datetime="{ts_iso}">{ts_str}</time></td>'
            f'<td><span class="badge badge-spruce">HMAC-SHA256 CONSUMED</span></td>'
            f'</tr>'
        )

    active_count = sum(1 for customer in customers if str(customer["status"]).upper() == "ACTIVE")
    refunded_count = sum(1 for invoice in invoices if str(invoice["refund_status"]).upper() == "REFUNDED")
    total_billed = sum(int(inv["amount"]) for inv in invoices)
    total_refunded = sum(int(inv["refund_amount"]) for inv in invoices)

    page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f6f5f0">
  <title>Northstar Freight Core | Operational System of Record</title>
  <style>
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-Regular.otf") format("opentype"); font-style: normal; font-weight: 400; font-display: swap; }
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-Medium.otf") format("opentype"); font-style: normal; font-weight: 500; font-display: swap; }
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-SemiBold.otf") format("opentype"); font-style: normal; font-weight: 600; font-display: swap; }
    @font-face { font-family: "Fira Mono"; src: url("/static/fonts/FiraMono-Regular.otf") format("opentype"); font-style: normal; font-weight: 400; font-display: swap; }
    :root {
      color-scheme: light;
      --bg-ground: #f6f5f0;
      --bg-surface: #ffffff;
      --bg-header: #14171a;
      --ink-primary: #15181b;
      --ink-muted: #5c646b;
      --rule-line: #d4d2c9;
      --rule-dark: #2a2e33;
      --spruce: #194433;
      --spruce-wash: #e8f3ed;
      --spruce-border: #a8ccbb;
      --rust: #872b1e;
      --rust-wash: #fcedea;
      --rust-border: #e8b6af;
      --brass: #785312;
      --brass-wash: #faf3e4;
      --brass-border: #dfcaa2;
      --amber-accent: #d99b26;
      --mono: "Fira Mono", SFMono-Regular, Menlo, monospace;
      --sans: "Fira Sans", -apple-system, Segoe UI, sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg-ground); color: var(--ink-primary); font: 14px/1.5 var(--sans); }
    a { color: inherit; text-decoration: none; }
    code, time, .mono-val { font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
    :focus-visible { outline: 2px solid var(--amber-accent); outline-offset: 2px; }

    /* Industrial Masthead */
    .masthead { background: var(--bg-header); color: #eef1f4; border-bottom: 2px solid var(--amber-accent); padding: 0 28px; }
    .masthead-inner { max-width: 1440px; margin: 0 auto; height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .brand-block { display: flex; align-items: center; gap: 14px; }
    .brand-symbol { width: 32px; height: 32px; background: var(--amber-accent); color: #14171a; display: grid; place-items: center; font: 700 13px/1 var(--mono); border-radius: 2px; }
    .brand-meta h1 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; color: #ffffff; }
    .brand-meta span { display: block; font-size: 11px; color: #8e97a0; font-family: var(--mono); }
    .masthead-pills { display: flex; align-items: center; gap: 12px; font-family: var(--mono); font-size: 11px; }
    .env-tag { padding: 4px 8px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 2px; color: #c4ccd4; }
    .live-pulse { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px; background: rgba(25, 68, 51, 0.4); border: 1px solid #2f7a5c; border-radius: 2px; color: #6ee7b7; font-weight: 500; }
    .pulse-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; display: inline-block; animation: blink 2s infinite ease-in-out; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    /* Sub-bar / Gateway Security Notice */
    .gateway-strip { background: #eae8e1; border-bottom: 1px solid var(--rule-line); padding: 10px 28px; }
    .gateway-inner { max-width: 1440px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #3a4248; }
    .gateway-inner strong { color: var(--spruce); font-weight: 600; }

    /* Operational Manifest Strip */
    .manifest-bar { max-width: 1440px; margin: 24px auto 0; padding: 0 28px; }
    .manifest-sheet { background: var(--bg-surface); border: 1px solid var(--rule-line); padding: 16px 20px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; border-left: 4px solid var(--spruce); }
    .manifest-group { display: flex; flex-wrap: wrap; gap: 24px 32px; align-items: center; }
    .m-item small { display: block; font-size: 10px; font-family: var(--mono); color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; }
    .m-item b { font-size: 16px; font-weight: 600; font-family: var(--mono); color: var(--ink-primary); }

    /* Workstation Grid: Ledger Left, Inspector Right */
    .workstation { max-width: 1440px; margin: 22px auto 40px; padding: 0 28px; display: grid; grid-template-columns: minmax(0, 1.8fr) minmax(340px, 1.2fr); gap: 24px; align-items: start; }
    .ledger-pane { display: grid; gap: 24px; }
    .pane-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 10px; }
    .pane-header h2 { margin: 0; font-size: 16px; font-weight: 600; letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px; }
    .pane-counter { font-family: var(--mono); font-size: 11px; color: var(--ink-muted); }

    /* Tables */
    .table-container { background: var(--bg-surface); border: 1px solid var(--rule-line); overflow: hidden; }
    .table-toolbar { padding: 10px 14px; background: #faf9f6; border-bottom: 1px solid var(--rule-line); display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .search-box { width: 100%; max-width: 320px; padding: 6px 10px; border: 1px solid var(--rule-line); background: #ffffff; font-size: 12px; font-family: var(--sans); }
    .table-scroll { overflow-x: auto; max-height: 480px; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th { padding: 9px 12px; background: #f2f0ea; color: #434c54; font-size: 10px; font-weight: 600; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--rule-line); position: sticky; top: 0; z-index: 1; }
    td { padding: 10px 12px; border-bottom: 1px solid #ebe8e1; font-size: 13px; vertical-align: middle; }
    tr.ledger-row { cursor: pointer; transition: background 0.1s ease; }
    tr.ledger-row:hover { background: #fbf9f4; }
    tr.ledger-row.selected { background: #f3efe6; border-left: 3px solid var(--amber-accent); }
    .code-primary { color: #164e39; font-weight: 600; }
    .amt-col { font-family: var(--mono); font-weight: 600; text-align: right; white-space: nowrap; }
    .notes-cell { font-size: 11px; color: var(--ink-muted); max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .subtext { display: block; font-size: 11px; color: var(--ink-muted); font-weight: 400; }
    .tier-tag { font-family: var(--mono); font-size: 11px; color: #4a5568; }

    /* Badges */
    .badge { display: inline-flex; align-items: center; padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: var(--mono); border: 1px solid transparent; border-radius: 1px; white-space: nowrap; }
    .badge-spruce { background: var(--spruce-wash); color: var(--spruce); border-color: var(--spruce-border); }
    .badge-rust { background: var(--rust-wash); color: var(--rust); border-color: var(--rust-border); }
    .badge-brass { background: var(--brass-wash); color: var(--brass); border-color: var(--brass-border); }
    .badge-neutral { background: #eeebe3; color: #5a646c; border-color: #d6d2c8; }

    /* Right-side Inspector */
    .inspector-pane { background: var(--bg-surface); border: 1px solid var(--rule-line); position: sticky; top: 20px; }
    .inspector-header { background: #f2f0ea; padding: 12px 16px; border-bottom: 1px solid var(--rule-line); display: flex; align-items: center; justify-content: space-between; }
    .inspector-header h3 { margin: 0; font-size: 13px; font-weight: 600; text-transform: uppercase; font-family: var(--mono); letter-spacing: 0.04em; }
    .inspector-body { padding: 18px 16px; display: grid; gap: 16px; }
    .inspect-field small { display: block; font-size: 10px; font-family: var(--mono); color: var(--ink-muted); text-transform: uppercase; margin-bottom: 3px; }
    .inspect-field p { margin: 0; font-size: 13px; font-weight: 500; }
    .inspect-token-box { background: #faf9f6; border: 1px dashed var(--rule-line); padding: 12px; font-family: var(--mono); font-size: 11px; word-break: break-all; }
    .token-status { display: flex; align-items: center; gap: 6px; margin-top: 8px; font-size: 11px; color: var(--spruce); font-weight: 600; }

    @media (max-width: 1080px) {
      .workstation { grid-template-columns: 1fr; }
      .inspector-pane { position: static; }
    }
  </style>
</head>
<body>
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand-block">
        <div class="brand-symbol">NS</div>
        <div class="brand-meta">
          <h1>Northstar Freight Core</h1>
          <span>Operational Freight Settlement & Ledger · System of Record</span>
        </div>
      </div>
      <div class="masthead-pills">
        <span class="env-tag">ISOLATED PORT: 8080/8082</span>
        <span class="live-pulse"><span class="pulse-dot"></span>LIVE AUTO-SYNC (3S)</span>
      </div>
    </div>
  </header>

  <aside class="gateway-strip">
    <div class="gateway-inner">
      <div>🛡️ <strong>ARG Cryptographic Boundary Active</strong>: All ledger mutations strictly require verified, single-use HMAC-SHA256 proof grants.</div>
      <div class="mono-val">REPLAY PROTECTION: STRICT SINGLE-USE</div>
    </div>
  </aside>

  <div class="manifest-bar">
    <div class="manifest-sheet">
      <div class="manifest-group">
        <div class="m-item"><small>Manifest Ledger</small><b>MFR-2026-X89</b></div>
        <div class="m-item"><small>Invoices on Record</small><b>{invoice_count} ({total_billed})</b></div>
        <div class="m-item"><small>Settled / Refunded</small><b>{refunded_count} ({total_refunded})</b></div>
        <div class="m-item"><small>Customer Accounts</small><b>{customer_count} ({active_count} Active)</b></div>
        <div class="m-item"><small>ARG Grants Consumed</small><b>{grant_count} Proofs</b></div>
      </div>
      <button onclick="window.location.reload()" style="background:#ffffff;border:1px solid var(--rule-line);padding:6px 12px;font:600 12px var(--sans);cursor:pointer;">Refresh Ledger</button>
    </div>
  </div>

  <main class="workstation">
    <div class="ledger-pane">
      <!-- Invoices Section -->
      <section>
        <div class="pane-header">
          <h2>Accounts Receivable Ledger</h2>
          <span class="pane-counter">{invoice_count} Invoices</span>
        </div>
        <div class="table-container">
          <div class="table-toolbar">
            <input type="search" id="invoice-filter" class="search-box" placeholder="Filter invoices or customer..." oninput="filterTable('invoice-filter', 'invoice-table')">
            <span class="pane-counter">Click a row to inspect proof</span>
          </div>
          <div class="table-scroll">
            <table id="invoice-table">
              <thead>
                <tr>
                  <th>Invoice</th><th>Customer</th><th style="text-align:right">Billed</th><th>Status</th><th>Refund</th><th>Audit Provenance</th>
                </tr>
              </thead>
              <tbody id="invoice-tbody">
                {invoice_rows}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- Customers Section -->
      <section>
        <div class="pane-header">
          <h2>Customer Account Directory</h2>
          <span class="pane-counter">{customer_count} Accounts</span>
        </div>
        <div class="table-container">
          <div class="table-scroll">
            <table>
              <thead>
                <tr><th>Account Code</th><th>Company Name & Email</th><th>Tier</th><th>Standing</th></tr>
              </thead>
              <tbody>
                {customer_rows}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ARG Grants Vault -->
      <section>
        <div class="pane-header">
          <h2>Consumed Cryptographic Grants (ARG Vault)</h2>
          <span class="pane-counter">{grant_count} Proof Tokens</span>
        </div>
        <div class="table-container">
          <div class="table-scroll">
            <table>
              <thead>
                <tr><th>ARG Request ID</th><th>Verification Timestamp</th><th>Replay Status</th></tr>
              </thead>
              <tbody>
                {grant_rows}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <!-- Right Side: Cryptographic Settlement Inspector -->
    <aside class="inspector-pane">
      <div class="inspector-header">
        <h3>Cryptographic Settlement Inspector</h3>
        <span class="badge badge-spruce">HMAC-SHA256</span>
      </div>
      <div class="inspector-body" id="inspector-content">
        <div class="inspect-field">
          <small>Selected Record</small>
          <p id="inspect-code" class="mono-val" style="font-size:16px;font-weight:700;color:var(--spruce);">INV-2088</p>
        </div>
        <div class="inspect-field">
          <small>Customer Account</small>
          <p id="inspect-cust">CUST-2088 (Acme Corporation)</p>
        </div>
        <div class="inspect-field">
          <small>Invoice Value & Settlement Status</small>
          <p id="inspect-status">₹50,000 · <span class="badge badge-rust" id="inspect-refund-badge">REFUNDED (-₹50,000)</span></p>
        </div>
        <div class="inspect-field">
          <small>Cryptographic Authorization Audit</small>
          <div class="inspect-token-box" id="inspect-notes">
            Authorized by ARG Governance. Verified HMAC-SHA256 proof token received and consumed.
          </div>
          <div class="token-status">
            <span>🔒</span>
            <span id="inspect-status-msg">Single-Use Replay Protection Active. Direct mutations rejected with 403.</span>
          </div>
        </div>
        <div style="background:#f4f2ec;padding:12px;border:1px solid var(--rule-line);font-size:11px;color:var(--ink-muted);line-height:1.5;">
          <strong>Security Guarantee:</strong> Unauthenticated agent mutations fail immediately. Every mutation in this ledger requires an operator-authorized cryptographic grant generated by ARG.
        </div>
      </div>
    </aside>
  </main>

  <script>
    function filterTable(inputId, tableId) {
      const q = document.getElementById(inputId).value.toLowerCase();
      const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
      rows.forEach(r => {
        const text = r.getAttribute('data-search') || r.innerText.toLowerCase();
        r.style.display = text.toLowerCase().includes(q) ? '' : 'none';
      });
    }

    // Row selection for inspector
    const rows = document.querySelectorAll('#invoice-tbody tr.ledger-row');
    rows.forEach(r => {
      r.addEventListener('click', () => {
        rows.forEach(x => x.classList.remove('selected'));
        r.classList.add('selected');
        document.getElementById('inspect-code').innerText = r.getAttribute('data-code') || '';
        document.getElementById('inspect-cust').innerText = r.getAttribute('data-cust') || '';
        document.getElementById('inspect-status').innerHTML = (r.getAttribute('data-amount') || '') + ' · <span class="badge badge-rust">' + (r.getAttribute('data-refund') || '') + '</span>';
        document.getElementById('inspect-notes').innerText = r.getAttribute('data-notes') || 'Standard transaction';
      });
    });

    // Auto-select first row
    if (rows.length > 0) rows[rows.length - 1].classList.add('selected');

    // Live background sync polling every 3 seconds
    setInterval(async () => {
      try {
        const res = await fetch('/api/v1/erp/invoices');
        if (res.ok) {
          const data = await res.json();
          // Check if any invoice changed refund status
          data.forEach(inv => {
            const row = document.querySelector(`tr[data-code="${inv.invoice_code}"]`);
            if (row && inv.refund_status === 'REFUNDED') {
              const currentRefund = row.getAttribute('data-refund');
              if (!currentRefund || !currentRefund.includes('REFUNDED')) {
                window.location.reload();
              }
            }
          });
        }
      } catch (e) {}
    }, 3000);
  </script>
</body>
</html>"""

    replacements = {
        "{invoice_count}": str(len(invoices)),
        "{customer_count}": str(len(customers)),
        "{active_count}": str(active_count),
        "{refunded_count}": str(refunded_count),
        "{total_billed}": f"₹{total_billed:,}",
        "{total_refunded}": f"₹{total_refunded:,}",
        "{invoice_rows}": "".join(invoice_rows),
        "{customer_rows}": "".join(customer_rows),
        "{grant_count}": str(len(consumed)),
        "{grant_rows}": "".join(grant_rows),
    }
    marker_pattern = re.compile(r"\{(?:invoice_count|customer_count|active_count|refunded_count|total_billed|total_refunded|invoice_rows|customer_rows|grant_count|grant_rows)\}")
    page = marker_pattern.sub(lambda match: str(replacements[match.group(0)]), page)
    return HTMLResponse(content=page)


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


@app.get("/api/v1/erp/consumed-grants")
def get_consumed_grants():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT grant_id, consumed_at FROM erp_consumed_grants ORDER BY consumed_at DESC")
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
