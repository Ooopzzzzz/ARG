import json
import os
import uuid
from typing import Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import get_session
from app.models import Agent
from app.schemas import Action, DecisionRequest
from app.security import require_agent

router = APIRouter(prefix="/api/v1/agent-gateway", tags=["Agent Gateway"])

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120"))
OLLAMA_CONNECT_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_CONNECT_TIMEOUT_SECONDS", "5"))


# Tools catalog exposed to LLM
ERP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_erp_invoices",
            "description": "Fetch current open invoices and customer balances from Northstar Enterprise ERP.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_erp_refund",
            "description": "Submit an invoice refund request into Northstar Enterprise ERP. Evaluated and governed by ARG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_code": {
                        "type": "string",
                        "description": "The ERP invoice code (e.g. INV-1042 or INV-2088)",
                    },
                    "amount": {
                        "type": "integer",
                        "description": "The amount in INR to refund (e.g. 2500 or 50000)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Customer justification or business rationale for refund",
                    },
                },
                "required": ["invoice_code", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer_status",
            "description": "Update customer record status in Enterprise ERP (e.g. ACTIVE, SUSPENDED, VIP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_code": {
                        "type": "string",
                        "description": "The customer code (e.g. CUST-1042 or CUST-2088)",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status for the customer",
                    },
                },
                "required": ["customer_code", "status"],
            },
        },
    },
]


class ChatTurnRequest(BaseModel):
    message: str = Field(..., description="User's prompt or instruction to the agent")
    conversation_id: str | None = Field(default=None, description="Optional conversation session ID")
    tool_call: dict[str, Any] | None = Field(default=None, description="Direct tool invocation from ChatGPT Web / Claude Custom Action")


@router.get("/tools")
def get_governed_tools():
    """Returns the tool definitions and JSON schemas compatible with OpenAI / Ollama / Claude tool calling."""
    return {"tools": ERP_TOOLS}


@router.post("/chat")
def process_agent_chat(
    req: ChatTurnRequest,
    agent: Agent = Depends(require_agent),
    session=Depends(get_session),
):
    """
    Real LLM Agent Gateway:
    1. Direct Tool Call (from ChatGPT Web or Claude) OR Real local LLM (Ollama).
    2. The tool call is intercepted by ARG Risk & Policy engine.
    3. If REQUIRE_APPROVAL (e.g. > 10k refund), returns instant non-blocking response with Request Ticket ID.
    4. If ALLOW, resumes execution.
    Zero timeout crash!
    """
    tool_calls = []
    llm_model: str | None = None

    if req.tool_call:
        tool_calls = [req.tool_call]
    else:
        # Attempt calling real local Ollama
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an enterprise operations assistant connected to Northstar Enterprise ERP via the ARG Governance Gateway. "
                    "Whenever the user asks to view invoices, refund an invoice, or update customer status, use the provided tools. "
                    "Always be concise and helpful."
                ),
            },
            {"role": "user", "content": req.message},
        ]
        llm_model = OLLAMA_MODEL
        try:
            timeout = httpx.Timeout(OLLAMA_TIMEOUT_SECONDS, connect=OLLAMA_CONNECT_TIMEOUT_SECONDS)
            with httpx.Client(base_url=OLLAMA_HOST, timeout=timeout) as client:
                resp = client.post(
                    "/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": messages,
                        "tools": ERP_TOOLS,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                llm_data = resp.json()
                message_obj = llm_data.get("message", {})
                tool_calls = message_obj.get("tool_calls", [])
                if not tool_calls:
                    return {
                        "type": "text",
                        "content": message_obj.get("content", ""),
                        "model": OLLAMA_MODEL,
                    }
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Ollama model {OLLAMA_MODEL} did not respond within {OLLAMA_TIMEOUT_SECONDS:g} seconds.",
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama model {OLLAMA_MODEL} is unavailable at the configured local endpoint.",
            ) from exc

    # Process first tool call through ARG Governance
    tool_call = tool_calls[0]
    func_name = tool_call.get("function", {}).get("name")
    args = tool_call.get("function", {}).get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}

    # Handle read-only tool
    if func_name == "get_erp_invoices":
        try:
            with httpx.Client(base_url="http://localhost:8080", timeout=5.0) as erp_client:
                invoices = erp_client.get("/api/v1/erp/invoices").json()
        except Exception:
            invoices = []
        return {
            "type": "tool_executed",
            "tool": func_name,
            "status": "ALLOWED_READ_ONLY",
            "model": llm_model,
            "data": invoices,
            "summary": f"Retrieved {len(invoices)} invoices from Enterprise ERP.",
        }

    # Map mutation tool to ARG DecisionRequest
    if func_name == "request_erp_refund":
        try:
            amount = int(args.get("amount") or 50000)
        except (ValueError, TypeError):
            amount = 50000
        raw_code = str(args.get("invoice_code") or "").strip()
        invoice_code = raw_code if len(raw_code) >= 3 else "INV-2088"
        reason_val = str(args.get("reason") or "").strip() or "Customer requested refund"
        action_data = {
            "type": "erp.invoice.refund",
            "target": invoice_code,
            "parameters": {"amount": amount, "reason": reason_val},
            "environment": "production",
            "data_classification": "restricted",
            "impact": {"amount": amount, "currency": "INR"},
        }
    elif func_name == "update_customer_status":
        raw_cust = str(args.get("customer_code") or "").strip()
        cust_code = raw_cust if len(raw_cust) >= 3 else "CUST-1042"
        status_val = str(args.get("status") or "").strip().upper() or "ACTIVE"
        action_data = {
            "type": "customer.record.update",
            "target": cust_code,
            "parameters": {"status": status_val},
            "environment": "production",
            "data_classification": "pii",
            "impact": {"amount": 0, "currency": "INR"},
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {func_name}")

    # Evaluate action through ARG Runtime Engine
    from app.main import create_decision

    idempotency_key = f"llm-{uuid.uuid4()}"
    decision_payload = DecisionRequest(
        agent_id=agent.id,
        action=Action(**action_data),
    )

    evaluation = create_decision(
        body=decision_payload,
        idempotency_key=idempotency_key,
        agent=agent,
        session=session,
    )

    decision_outcome = evaluation.get("decision")
    request_id = evaluation.get("request_id")
    risk_score = evaluation.get("risk", {}).get("score", 0)

    if decision_outcome == "REQUIRE_APPROVAL":
        target_entity = action_data.get('target', '')
        amt = action_data.get('impact', {}).get('amount', 0)
        amt_str = f" of ₹{amt:,}" if amt else ""
        return {
            "type": "governance_paused",
            "status": "REQUIRE_APPROVAL",
            "model": llm_model,
            "request_id": request_id,
            "risk_score": risk_score,
            "reason_codes": evaluation.get("reason_codes", []),
            "action_proposed": action_data,
            "agent_message": (
                f"⏸️ [ARG GOVERNANCE PAUSED]: High-impact ERP mutation ({func_name} on {target_entity}{amt_str}) "
                f"exceeds autonomous threshold (Risk: {risk_score}/100, Reason: {', '.join(evaluation.get('reason_codes', []))}). "
                f"Action is staged safely for manager authorization in ARG Console. External ERP system of record remains untouched. "
                f"Ticket ID: {request_id} (Zero HTTP timeout crash)."
            ),
        }
    elif decision_outcome == "ALLOW":
        return {
            "type": "governance_allowed",
            "status": "ALLOW",
            "model": llm_model,
            "request_id": request_id,
            "risk_score": risk_score,
            "action_proposed": action_data,
            "agent_message": f"✅ [ARG GOVERNANCE ALLOWED]: Action verified within autonomous policy limits (Risk: {risk_score}/100). Cryptographic grant generated for request {request_id}.",
        }
    else:
        return {
            "type": "governance_denied",
            "status": "DENY",
            "model": llm_model,
            "request_id": request_id,
            "reason_codes": evaluation.get("reason_codes", []),
            "agent_message": f"🛑 [ARG POLICY BLOCKED]: Action denied by compliance rules: {', '.join(evaluation.get('reason_codes', []))}. System of record is protected.",
        }
