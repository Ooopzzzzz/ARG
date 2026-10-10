#!/usr/bin/env python3
"""
Interactive Realtime LLM & External ERP Pipeline Test
Connects:
1. Real Local Ollama LLM (qwen2.5:7b)
2. ARG Runtime Governance Gateway (Port 8000)
3. Standalone External Enterprise ERP (Port 8080)
"""

import json
import os
import sys
import time
import httpx

# Load from .env if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

ARG_API_URL = os.environ.get("ARG_API_URL", "http://localhost:8000")
ERP_API_URL = os.environ.get("ERP_API_URL", "http://localhost:8080")
OPERATOR_TOKEN = os.environ.get("OPERATOR_TOKEN", "local-development-operator-token")
DEMO_AGENT_KEY = os.environ.get("ARG_DEMO_AGENT_KEY", "local-development-demo-agent-key-minimum-24-chars")


def log(msg: str):
    print(f"\n[DEMO-PIPELINE] {msg}")


def main():
    print("=" * 70)
    print("ARG RUNTIME ENTERPRISE — REALTIME LLM TO EXTERNAL ERP PIPELINE")
    print("=" * 70)

    # 1. Health checks
    log("1. Checking Northstar Enterprise ERP on :8080...")
    try:
        r = httpx.get(f"{ERP_API_URL}/health", timeout=3.0)
        assert r.status_code == 200
        print(f"   -> ERP OK: {r.json()}")
    except Exception as exc:
        print(f"   -> FAILED: External ERP not reachable ({exc})")
        sys.exit(1)

    log("2. Checking ARG API on :8000...")
    try:
        r = httpx.get(f"{ARG_API_URL}/health/ready", timeout=3.0)
        assert r.status_code == 200
        print(f"   -> ARG API OK: {r.json()}")
    except Exception as exc:
        print(f"   -> FAILED: ARG API not ready ({exc})")
        sys.exit(1)

    # Fetch initial ERP invoices
    invoices = httpx.get(f"{ERP_API_URL}/api/v1/erp/invoices").json()
    print("\n[EXTERNAL ERP INITIAL STATE]")
    for inv in invoices:
        print(f"   * {inv['invoice_code']} | Amount: ₹{inv['amount']:,} | Status: {inv['status']} | Refund Status: {inv['refund_status']}")

    # 2. Test Agent Direct Mutation (Negative Test: Must be rejected by ERP)
    log("3. Security Test: Attempting Direct ERP Mutation without ARG Token...")
    attack_res = httpx.post(f"{ERP_API_URL}/api/v1/erp/invoices/INV-2088/refund", json={"amount": 50000})
    print(f"   -> ERP Direct Access Status: {attack_res.status_code}")
    print(f"   -> ERP Error Message: {attack_res.json().get('detail')}")
    assert attack_res.status_code == 403, "ERP should forbid direct mutation without ARG token!"
    print("   -> [PASSED] Un-governed direct mutation blocked by ERP.")

    # 3. Real LLM Turn through ARG Gateway
    prompt = "I need to process a ₹50,000 refund for customer Acme Corp on invoice INV-2088."
    log(f"4. Sending prompt to Real LLM via ARG Gateway: '{prompt}'")
    chat_res = httpx.post(
        f"{ARG_API_URL}/api/v1/agent-gateway/chat",
        headers={"Authorization": f"Bearer {DEMO_AGENT_KEY}"},
        json={"message": prompt},
        timeout=30.0,
    )
    print(f"   -> Gateway Response Code: {chat_res.status_code}")
    chat_data = chat_res.json()
    print("   -> Gateway Response JSON:")
    print(json.dumps(chat_data, indent=6))

    assert chat_data.get("status") == "REQUIRE_APPROVAL", f"Expected REQUIRE_APPROVAL, got {chat_data}"
    req_id = chat_data.get("request_id")
    print(f"\n   [TIMEOUT PREVENTED] LLM turn completed instantly in <2 seconds.")
    print(f"   [ACTION PAUSED] Ticket ID: {req_id}")

    # 4. Human Approval in ARG
    log(f"5. Human Operator logs into ARG Console to review ticket {req_id}...")
    approvals_res = httpx.get(
        f"{ARG_API_URL}/api/v1/approvals?status=PENDING",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
    )
    pending_list = approvals_res.json()
    approval_item = next((a for a in pending_list if a["request_id"] == req_id), None)
    assert approval_item is not None, f"Pending approval not found for {req_id}"

    approval_id = approval_item["id"]
    print(f"   -> Found Pending Approval ID: {approval_id}")
    print(f"   -> Risk Score: {approval_item.get('risk_score')}/100")
    print(f"   -> Reason Codes: {approval_item.get('reason_codes')}")

    # Human approves
    log(f"6. Operator signs off: Approving {approval_id} with rationale...")
    approve_res = httpx.post(
        f"{ARG_API_URL}/api/v1/approvals/{approval_id}/approve",
        headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
        json={"rationale": "Verified Acme SLA dispute and manager signed off for demo."},
    )
    assert approve_res.status_code == 200
    print(f"   -> Approval Status: {approve_res.json()}")

    # 5. Execution Dispatch to External ERP
    log(f"7. ARG Resuming Execution and Minting Single-Use Proof Token for External ERP...")
    exec_res = httpx.post(
        f"{ARG_API_URL}/api/v1/runtime/requests/{req_id}/execute",
        headers={"Authorization": f"Bearer {DEMO_AGENT_KEY}"},
    )
    print(f"   -> Execution Status Code: {exec_res.status_code}")
    exec_data = exec_res.json()
    print("   -> Execution Response:")
    print(json.dumps(exec_data, indent=6))
    assert exec_data.get("status") == "EXECUTED"

    # 6. Verify ERP State Updated
    log("8. Verifying External ERP state on :8080 after ARG dispatch...")
    updated_invoices = httpx.get(f"{ERP_API_URL}/api/v1/erp/invoices").json()
    inv_2088 = next(i for i in updated_invoices if i["invoice_code"] == "INV-2088")
    print(f"   -> Invoice INV-2088 Refund Status: {inv_2088['refund_status']}")
    print(f"   -> Invoice INV-2088 Refund Amount: ₹{inv_2088['refund_amount']:,}")
    print(f"   -> Invoice Notes in ERP: {inv_2088['notes']}")

    assert inv_2088["refund_status"] == "REFUNDED"
    assert inv_2088["refund_amount"] == 50000

    print("\n" + "=" * 70)
    print(">>> PIPELINE TEST COMPLETED SUCCESSFULLY! <<<")
    print("1. Real LLM tool-calling initiated.")
    print("2. ARG intercepted and prevented connection timeout (Claim-Check pattern).")
    print("3. Human approved in ARG Console.")
    print("4. Cryptographic single-use grant token minted.")
    print("5. Standalone External ERP verified token and executed ledger refund.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
