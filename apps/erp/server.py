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
    title="Northstar Enterprise ERP (External Standalone System)",
    description="Independent enterprise ERP representing a real third-party system governed by ARG.",
    version="1.0.0",
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
            return "state state--complete"
        if normalized in {"PENDING", "REVIEW"}:
            return "state state--review"
        if normalized in {"SUSPENDED", "FAILED", "REJECTED"}:
            return "state state--exception"
        return "state state--neutral"

    invoice_rows = []
    for invoice in invoices:
        invoice_code = text(invoice["invoice_code"])
        customer_code = text(invoice["customer_code"])
        amount = int(invoice["amount"])
        refund_status = str(invoice["refund_status"])
        refund_amount = int(invoice["refund_amount"])
        refund_detail = f"₹{refund_amount:,} returned" if refund_status.upper() == "REFUNDED" else "No refund"
        invoice_rows.append(
            "<tr class=\"ledger-row\" data-search=\"{} {} {}\">"
            "<td><code>{}</code></td><td><span class=\"account-code\">{}</span></td>"
            "<td class=\"amount\">₹{:,}</td><td><span class=\"{}\">{}</span></td>"
            "<td><span class=\"{}\">{}</span><small class=\"subvalue\">{}</small></td>"
            "<td class=\"notes-cell\">{}</td></tr>".format(
                invoice_code, customer_code, text(refund_status), invoice_code, customer_code, amount,
                status_class(str(invoice["status"])), text(invoice["status"]),
                status_class(refund_status), text(refund_status), text(refund_detail),
                text(invoice["notes"] or "No note recorded"),
            )
        )

    customer_rows = []
    for customer in customers:
        customer_code = text(customer["customer_code"])
        customer_name = text(customer["name"])
        customer_rows.append(
            "<tr class=\"ledger-row\" data-search=\"{} {} {}\">"
            "<td><code>{}</code></td><td><strong>{}</strong><small class=\"subvalue\">{}</small></td>"
            "<td>{}</td><td><span class=\"{}\">{}</span></td></tr>".format(
                customer_code, customer_name, text(customer["email"]), customer_code,
                customer_name, text(customer["email"]), text(customer["tier"]),
                status_class(str(customer["status"])), text(customer["status"]),
            )
        )

    grant_rows = []
    for grant in consumed:
        grant_id = text(grant["grant_id"])
        granted_at = int(grant["consumed_at"])
        grant_rows.append(
            "<tr class=\"ledger-row\" data-search=\"{} hmac verified\">"
            "<td><code>{}</code></td><td><time datetime=\"{}\">{}</time></td>"
            "<td><span class=\"state state--complete\">Verified and consumed</span></td></tr>".format(
                grant_id, grant_id, time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(granted_at)),
                time.strftime("%d %b %Y · %H:%M:%S", time.localtime(granted_at)),
            )
        )

    active_count = sum(1 for customer in customers if str(customer["status"]).upper() == "ACTIVE")
    refunded_count = sum(1 for invoice in invoices if str(invoice["refund_status"]).upper() == "REFUNDED")
    page = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <meta name=\"theme-color\" content=\"#f0f3ef\">
  <title>Northstar | Invoice register</title>
  <style>
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-Regular.otf") format("opentype"); font-style: normal; font-weight: 400; font-display: swap; }
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-Medium.otf") format("opentype"); font-style: normal; font-weight: 500; font-display: swap; }
    @font-face { font-family: "Fira Sans"; src: url("/static/fonts/FiraSans-SemiBold.otf") format("opentype"); font-style: normal; font-weight: 600; font-display: swap; }
    @font-face { font-family: "Fira Mono"; src: url("/static/fonts/FiraMono-Regular.otf") format("opentype"); font-style: normal; font-weight: 400; font-display: swap; }
    :root {
      color-scheme: light;
      --ground: #f0f3ef;
      --surface: #ffffff;
      --ink: #1d2b27;
      --muted: #53635d;
      --line: #d3ddd7;
      --line-strong: #a9b8af;
      --harbor: #215944;
      --harbor-wash: #e6f1ea;
      --vermilion: #963e2d;
      --vermilion-wash: #f8e9e5;
      --amber: #76500b;
      --amber-wash: #f6efdc;
      --mono: "Fira Mono", "SFMono-Regular", Consolas, monospace;
      --sans: "Fira Sans", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; scroll-padding-top: 94px; }
    body { margin: 0; background: var(--ground); color: var(--ink); font: 15px/1.5 var(--sans); }
    a { color: inherit; }
    button, input { font: inherit; }
    button, a { -webkit-tap-highlight-color: transparent; }
    :focus-visible { outline: 3px solid var(--vermilion); outline-offset: 3px; }
    .masthead { background: var(--surface); border-bottom: 1px solid var(--line-strong); }
    .masthead-inner, .workspace { width: min(100% - 48px, 1320px); margin-inline: auto; }
    .masthead-inner { min-height: 72px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
    .brand { display: flex; align-items: center; gap: 13px; min-width: 0; }
    .brand-mark { width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid var(--harbor); color: var(--harbor); font: 700 11px/1 var(--mono); letter-spacing: -.08em; }
    .brand-name { font-size: 15px; font-weight: 650; letter-spacing: -.015em; }
    .brand-subtitle { color: var(--muted); display: block; font-size: 12px; margin-top: 2px; }
    .system-meta { display: flex; align-items: center; gap: 18px; color: var(--muted); font: 11px/1.3 var(--mono); }
    .system-meta span { white-space: nowrap; }
    .local-tag { padding: 7px 9px; color: var(--harbor); background: var(--harbor-wash); border: 1px solid #c4d8ca; }
    .subnav { border-bottom: 1px solid var(--line); background: var(--surface); }
    .subnav-inner { width: min(100% - 48px, 1320px); min-height: 48px; display: flex; align-items: stretch; gap: 26px; margin-inline: auto; }
    .subnav a { display: inline-flex; align-items: center; border-bottom: 2px solid transparent; color: var(--muted); font-size: 13px; font-weight: 550; text-decoration: none; }
    .subnav a:hover { color: var(--ink); border-color: var(--harbor); }
    .workspace { padding: 34px 0 54px; }
    .page-intro { display: flex; justify-content: space-between; align-items: end; gap: 28px; padding-bottom: 24px; }
    h1, h2, p { margin-top: 0; }
    h1 { margin-bottom: 7px; font-size: clamp(27px, 3vw, 36px); letter-spacing: -.04em; line-height: 1.12; font-weight: 600; }
    .intro-copy { max-width: 68ch; margin-bottom: 0; color: var(--muted); font-size: 14px; }
    .refresh-button { min-height: 44px; padding: 0 15px; border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink); cursor: pointer; }
    .refresh-button:hover { border-color: var(--harbor); color: var(--harbor); }
    .proof-strip { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 22px; padding: 12px 15px; border: 1px solid var(--line); background: #e8eeea; }
    .proof-copy { color: var(--ink); font-size: 13px; }
    .proof-copy strong { color: var(--harbor); font-weight: 650; }
    .proof-code { color: var(--muted); font: 11px/1.4 var(--mono); white-space: nowrap; }
    .register-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 26px; background: var(--surface); border: 1px solid var(--line); }
    .summary-item { min-width: 0; padding: 14px 18px 15px; border-right: 1px solid var(--line); }
    .summary-item:last-child { border-right: 0; }
    .summary-item span, .summary-item strong { display: block; }
    .summary-item span { color: var(--muted); font-size: 12px; }
    .summary-item strong { margin-top: 3px; font-size: 23px; font-weight: 600; font-variant-numeric: tabular-nums; }
    .ledger-section { margin-top: 32px; scroll-margin-top: 92px; }
    .section-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 12px; }
    .section-heading h2 { margin: 0; font-size: 20px; line-height: 1.25; font-weight: 600; letter-spacing: -.025em; }
    .section-note { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
    .section-count { color: var(--muted); font: 11px/1.4 var(--mono); white-space: nowrap; }
    .ledger-frame { background: var(--surface); border: 1px solid var(--line); }
    .table-tools { display: flex; align-items: end; justify-content: space-between; gap: 16px; padding: 13px 15px; border-bottom: 1px solid var(--line); }
    .table-tools label { display: grid; gap: 4px; color: var(--muted); font-size: 11px; font-weight: 600; }
    .table-tools input { width: min(100%, 340px); min-height: 44px; padding: 7px 10px; border: 1px solid var(--line-strong); color: var(--ink); background: var(--surface); }
    .result-count { color: var(--muted); font: 11px/1.4 var(--mono); }
    .table-scroll { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th { padding: 10px 14px; color: var(--muted); background: #f5f7f5; border-bottom: 1px solid var(--line); font-size: 10px; font-weight: 650; letter-spacing: .07em; text-transform: uppercase; white-space: nowrap; }
    td { padding: 12px 14px; border-bottom: 1px solid #e8ede9; vertical-align: middle; font-size: 13px; }
    tbody tr:last-child td { border-bottom: 0; }
    tbody tr:hover td { background: #f7faf8; }
    code, time, .account-code, .amount { font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
    code { color: #254c3d; }
    .amount { white-space: nowrap; text-align: right; }
    .subvalue { display: block; margin-top: 3px; color: var(--muted); font-size: 11px; font-weight: 400; }
    .notes-cell { max-width: 300px; color: var(--muted); font-size: 12px; }
    .state { display: inline-flex; align-items: center; min-height: 25px; padding: 3px 8px; border: 1px solid transparent; font-size: 11px; font-weight: 600; white-space: nowrap; }
    .state--complete { color: #174e38; background: var(--harbor-wash); border-color: #c4d8ca; }
    .state--review { color: #68470b; background: var(--amber-wash); border-color: #e6d9b4; }
    .state--exception { color: #873927; background: var(--vermilion-wash); border-color: #e8c7bf; }
    .state--neutral { color: #46564f; background: #eef2ef; border-color: #dce4df; }
    .empty-row td { padding: 24px; color: var(--muted); text-align: center; }
    .grant-table th, .grant-table td { padding-block: 14px; }
    .footer { display: flex; justify-content: space-between; gap: 20px; margin-top: 38px; padding-top: 14px; border-top: 1px solid var(--line-strong); color: var(--muted); font-size: 11px; }
    .footer code { font-size: 10px; }
    @media (max-width: 760px) {
      .masthead-inner, .workspace, .subnav-inner { width: min(100% - 32px, 1320px); }
      .masthead-inner { min-height: 64px; }
      .system-meta { gap: 8px; }
      .system-meta .last-sync { display: none; }
      .subnav-inner { gap: 22px; overflow-x: auto; }
      .subnav a { min-height: 46px; white-space: nowrap; }
      .workspace { padding-top: 25px; }
      .page-intro { align-items: start; }
      .proof-strip { align-items: start; flex-direction: column; gap: 5px; }
      .register-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .summary-item:nth-child(2) { border-right: 0; }
      .summary-item:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
      .table-tools { align-items: stretch; flex-direction: column; }
      .table-tools input { width: 100%; }
      .result-count { align-self: start; }
      .ledger-section { margin-top: 25px; }
      .footer { flex-direction: column; }
    }
    @media (max-width: 480px) {
      .masthead-inner, .workspace, .subnav-inner { width: min(100% - 24px, 1320px); }
      .brand { gap: 9px; }
      .brand-name { font-size: 13px; }
      .brand-subtitle { font-size: 10px; }
      .brand-mark { width: 30px; height: 30px; }
      .system-meta { display: grid; justify-items: end; font-size: 9px; }
      .local-tag { padding: 5px 6px; }
      .page-intro { flex-direction: column; gap: 15px; }
      .refresh-button { width: 100%; }
      .section-heading { align-items: start; flex-direction: column; gap: 4px; }
      .table-scroll table { min-width: 710px; }
      .grant-table { min-width: 560px !important; }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
    }
  </style>
</head>
<body>
  <header class=\"masthead\">
    <div class=\"masthead-inner\">
      <a class=\"brand\" href=\"/\" aria-label=\"Northstar home\">
        <span class=\"brand-mark\" aria-hidden=\"true\">NS</span>
        <span><span class=\"brand-name\">Northstar Freight Core</span><span class=\"brand-subtitle\">Accounts and customer records</span></span>
      </a>
      <div class=\"system-meta\"><span class=\"local-tag\">LOCAL · SYNTHETIC</span><span class=\"last-sync\">LEDGER · SQLITE</span></div>
    </div>
  </header>
  <nav class=\"subnav\" aria-label=\"Ledger sections\"><div class=\"subnav-inner\">
    <a href=\"#invoices\">Invoice register</a><a href=\"#customers\">Customer accounts</a><a href=\"#grants\">ARG grant receipts</a>
  </div></nav>
  <main class=\"workspace\">
    <section class=\"page-intro\" aria-labelledby=\"page-title\">
      <div><h1 id=\"page-title\">Invoice register</h1><p class=\"intro-copy\">Review Northstar billing records and confirm which refunds have reached the local ledger.</p></div>
      <button class=\"refresh-button\" type=\"button\" onclick=\"window.location.reload()\">Refresh ledger</button>
    </section>
    <section class=\"proof-strip\" aria-label=\"ARG execution boundary\">
      <div class=\"proof-copy\"><strong>ARG grant required</strong> · Direct ledger mutations are rejected without a verified, single-use proof token.</div>
      <div class=\"proof-code\">GATEWAY → REVIEW → ERP</div>
    </section>
    <section class=\"register-summary\" aria-label=\"Ledger summary\">
      <div class=\"summary-item\"><span>Invoice records</span><strong>{invoice_count}</strong></div>
      <div class=\"summary-item\"><span>Customer accounts</span><strong>{customer_count}</strong></div>
      <div class=\"summary-item\"><span>Active accounts</span><strong>{active_count}</strong></div>
      <div class=\"summary-item\"><span>Refunded invoices</span><strong>{refunded_count}</strong></div>
    </section>

    <section class=\"ledger-section\" id=\"invoices\" aria-labelledby=\"invoice-title\">
      <div class=\"section-heading\"><div><h2 id=\"invoice-title\">Accounts receivable</h2><p class=\"section-note\">Invoice value, accounting state, and refund outcome.</p></div><span class=\"section-count\">{invoice_count} RECORDS</span></div>
      <div class=\"ledger-frame\">
        <div class=\"table-tools\"><label for=\"invoice-search\">Find an invoice or customer<input id=\"invoice-search\" type=\"search\" placeholder=\"Invoice code or customer code\" autocomplete=\"off\"></label><span class=\"result-count\" id=\"invoice-count\" aria-live=\"polite\">Showing {invoice_count} invoices</span></div>
        <div class=\"table-scroll\" role=\"region\" tabindex=\"0\" aria-label=\"Invoice register table; scroll horizontally to view all columns\"><table><thead><tr>
          <th scope=\"col\">Invoice</th><th scope=\"col\">Customer account</th><th scope=\"col\">Billed amount</th><th scope=\"col\">Billing state</th><th scope=\"col\">Refund outcome</th><th scope=\"col\">Ledger note</th>
        </tr></thead><tbody id=\"invoice-rows\">{invoice_rows}<tr class=\"empty-row\" id=\"invoice-empty\" hidden><td colspan=\"6\">No invoices match this search.</td></tr></tbody></table></div>
      </div>
    </section>

    <section class=\"ledger-section\" id=\"customers\" aria-labelledby=\"customer-title\">
      <div class=\"section-heading\"><div><h2 id=\"customer-title\">Customer accounts</h2><p class=\"section-note\">Registered companies, account tier, and current standing.</p></div><span class=\"section-count\">{customer_count} ACCOUNTS · {active_count} ACTIVE</span></div>
      <div class=\"ledger-frame\">
        <div class=\"table-tools\"><label for=\"customer-search\">Find a customer<input id=\"customer-search\" type=\"search\" placeholder=\"Code, company, or contact\" autocomplete=\"off\"></label><span class=\"result-count\" id=\"customer-count\" aria-live=\"polite\">Showing {customer_count} accounts</span></div>
        <div class=\"table-scroll\" role=\"region\" tabindex=\"0\" aria-label=\"Customer accounts table; scroll horizontally to view all columns\"><table><thead><tr>
          <th scope=\"col\">Account code</th><th scope=\"col\">Company and contact</th><th scope=\"col\">Commercial tier</th><th scope=\"col\">Account standing</th>
        </tr></thead><tbody id=\"customer-rows\">{customer_rows}<tr class=\"empty-row\" id=\"customer-empty\" hidden><td colspan=\"4\">No accounts match this search.</td></tr></tbody></table></div>
      </div>
    </section>

    <section class=\"ledger-section\" id=\"grants\" aria-labelledby=\"grant-title\">
      <div class=\"section-heading\"><div><h2 id=\"grant-title\">ARG grant receipts</h2><p class=\"section-note\">Single-use proofs consumed by this ERP ledger.</p></div><span class=\"section-count\">{grant_count} RECEIPTS</span></div>
      <div class=\"ledger-frame\"><div class=\"table-scroll\" role=\"region\" tabindex=\"0\" aria-label=\"ARG grant receipts table; scroll horizontally to view all columns\"><table class=\"grant-table\"><thead><tr>
        <th scope=\"col\">ARG request ID</th><th scope=\"col\">Consumed at</th><th scope=\"col\">Verification result</th>
      </tr></thead><tbody>{grant_rows}<tr class=\"empty-row\" {grant_hidden}><td colspan=\"3\">No ARG grants have been consumed by this ERP yet.</td></tr></tbody></table></div></div>
    </section>
    <footer class=\"footer\"><span>Northstar Global Logistics · Local synthetic ledger</span><span>Mutations require ARG proof verification</span></footer>
  </main>
  <script>
    function bindLedgerSearch(inputId, rowsId, emptyId, countId, noun) {
      const input = document.getElementById(inputId);
      const rows = Array.from(document.querySelectorAll(`#${rowsId} .ledger-row`));
      const empty = document.getElementById(emptyId);
      const counter = document.getElementById(countId);
      if (!(input instanceof HTMLInputElement) || !(empty instanceof HTMLTableRowElement) || !counter) return;
      input.addEventListener('input', () => {
        const query = input.value.trim().toLocaleLowerCase();
        let visible = 0;
        for (const row of rows) {
          const matches = row.dataset.search?.toLocaleLowerCase().includes(query) ?? false;
          row.hidden = !matches;
          if (matches) visible += 1;
        }
        empty.hidden = visible > 0;
        counter.textContent = `Showing ${visible} ${noun}`;
      });
    }
    bindLedgerSearch('invoice-search', 'invoice-rows', 'invoice-empty', 'invoice-count', 'invoices');
    bindLedgerSearch('customer-search', 'customer-rows', 'customer-empty', 'customer-count', 'accounts');
  </script>
</body>
</html>"""

    replacements = {
        "{invoice_count}": str(len(invoices)),
        "{customer_count}": str(len(customers)),
        "{active_count}": str(active_count),
        "{refunded_count}": str(refunded_count),
        "{invoice_rows}": "".join(invoice_rows),
        "{customer_rows}": "".join(customer_rows),
        "{grant_count}": str(len(consumed)),
        "{grant_rows}": "".join(grant_rows),
        "{grant_hidden}": "hidden" if consumed else "",
    }
    marker_pattern = re.compile(r"\{(?:invoice_count|customer_count|active_count|refunded_count|invoice_rows|customer_rows|grant_count|grant_rows|grant_hidden)\}")
    page = marker_pattern.sub(lambda match: replacements[match.group(0)], page)
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
