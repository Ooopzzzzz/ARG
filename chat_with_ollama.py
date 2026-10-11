#!/usr/bin/env python3
"""
Interactive Realtime Ollama LLM to ARG Gateway CLI
Users or presenters can type any natural prompt here.
1. The prompt goes directly to local Ollama (qwen2.5:7b).
2. Ollama generates a tool call based on ARG tool schemas.
3. The tool call is sent into ARG Runtime Gateway.
4. If high-risk, ARG pauses without timing out and gives a ticket ID.
5. You can approve it in http://localhost:3000 to execute to ERP!
"""

import json
import os
import sys
import httpx

ARG_API_URL = os.environ.get("ARG_API_URL", "http://localhost:8000")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# Load credentials from .env
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

AGENT_KEY = os.environ.get("ARG_DEMO_AGENT_KEY", "arg_lRSZKaqW2_bEAillXegtlMV_qdc_NUFtJOeNM4M3Ig8KUXF6")


def main():
    print("=" * 70)
    print("  ARG LIVE CHAT — REAL LOCAL OLLAMA (qwen2.5:7b) CONNECTED TO ARG")
    print("=" * 70)
    print("Type your message to the AI agent (e.g., 'refund 50000 rupees to invoice INV-2088')")
    print("Type 'exit' to quit.\n")

    # Fetch tools from ARG
    try:
        tools_res = httpx.get(f"{ARG_API_URL}/api/v1/agent-gateway/tools", timeout=5.0)
        tools = tools_res.json().get("tools", [])
    except Exception as exc:
        print(f"[ERROR] Could not fetch tools from ARG Gateway: {exc}")
        sys.exit(1)

    while True:
        try:
            user_input = input("\n[YOU]: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            print("[OLLAMA]: Thinking...")
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an enterprise AI assistant connected to Northstar Enterprise ERP via ARG. "
                        "When the user asks to refund an invoice, check invoices, or update customer status, "
                        "use the available tools. Always pick the appropriate tool and arguments."
                    ),
                },
                {"role": "user", "content": user_input},
            ]

            # 1. Send user prompt to real Ollama
            ollama_res = httpx.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                },
                timeout=60.0,
            )
            msg_obj = ollama_res.json().get("message", {})
            tool_calls = msg_obj.get("tool_calls", [])

            if not tool_calls:
                # Ordinary conversation
                print(f"[AGENT]: {msg_obj.get('content', '')}")
                continue

            # 2. Ollama decided to call an ERP tool
            tool_call = tool_calls[0]
            func_name = tool_call.get("function", {}).get("name")
            args = tool_call.get("function", {}).get("arguments", {})
            print(f"\n⚡ [OLLAMA TOOL DECISION]: {func_name}({json.dumps(args)})")
            print("🛡️  [DISPATCHING TO ARG GATEWAY FOR GOVERNANCE EVALUATION]...")

            # 3. Send tool call into ARG Gateway
            gateway_res = httpx.post(
                f"{ARG_API_URL}/api/v1/agent-gateway/chat",
                headers={"Authorization": f"Bearer {AGENT_KEY}"},
                json={"message": user_input, "tool_call": tool_call},
                timeout=10.0,
            )
            data = gateway_res.json()

            status = data.get("status")
            if status == "REQUIRE_APPROVAL":
                req_id = data.get("request_id")
                score = data.get("risk_score")
                reasons = ", ".join(data.get("reason_codes", []))
                print("\n" + "═" * 74)
                print(f" ⏸️  ARG RUNTIME GOVERNANCE PAUSED EXECUTION (Risk: {score}/100)")
                print("═" * 74)
                print(f" Ticket / Request ID: {req_id}")
                print(f" Violation / Reason:  {reasons}")
                print(f" Agent Explanation:   {data.get('agent_message')}")
                print("─" * 74)
                print(" 🛡️  System of Record Status: SAFE & UNTOUCHED (No mutation executed)")
                print(" 🌐 ACTION REQUIRED: Open ARG Console at http://localhost:3000")
                print("    Go to 'Approvals' tab -> Click 'Approve & Execute' to authorize.")
                print("═" * 74)
            elif status == "ALLOW":
                print("\n" + "─" * 74)
                print(f" ✅ [ARG ALLOWED]: {data.get('agent_message')}")
                print("─" * 74)
            elif status == "DENY":
                print("\n" + "─" * 74)
                print(f" 🛑 [ARG BLOCKED]: {data.get('agent_message')}")
                print("─" * 74)
            else:
                print(f"\n[ARG RESPONSE]: {json.dumps(data, indent=2)}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        except Exception as exc:
            print(f"[ERROR]: {exc}")


if __name__ == "__main__":
    main()
