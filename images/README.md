# System Screenshots & Architectural Walkthrough

Visual evidence of the ARG (Agent Runtime Governance) end-to-end pipeline, running locally with local Ollama (`qwen2.5:7b`), the ARG Operator Console, and the standalone Northstar Freight Core ERP.

---

### 1. Asynchronous Human-in-the-Loop Approval Queue
![ARG Approvals Queue](./Screenshot%20from%202026-10-11%2008-19-26.png)
* **Figure 1:** Inspecting an intercepted high-impact refund action (`erp.invoice.refund` for ₹2,000 on `INV-2088`) in the ARG Operator Console (`http://localhost:3000`). The policy engine assessed a risk score of 60/100 (`HIGH_VALUE_REFUND_REVIEW`), automatically pausing execution and displaying full context—including action parameters, risk factors, policy version rules, and expiration timestamp—before any mutation reaches the external ERP.

---

### 2. Live Ollama CLI Interception Staged in ARG Console (Side-by-Side View)
![Ollama CLI and ARG Console](./Screenshot%20from%202026-10-11%2008-24-04.png)
* **Figure 2:** Side-by-side demonstration of live local Ollama (`qwen2.5:7b`) tool-calling connected to the ARG Governance Gateway. Left: Ollama proposes a ₹50,000 refund, and ARG responds with an instantaneous Zero-Timeout pause (`Ticket ID: a936b7df...`, Risk: 80/100). Right: The pending request is immediately staged in the ARG Operator Console for human sign-off while the ERP database remains untouched.

---

### 3. Append-Only Cryptographic Audit Trail
![ARG Audit Trail](./Screenshot%20from%202026-10-11%2008-24-32.png)
* **Figure 3:** Comprehensive audit trail recording every runtime event in real time. Shows the lifecycle of governed requests from initial decision recording (`REQUIRE_APPROVAL`, `ALLOW`, or `DENY`), through operator approval sign-off (`APPROVAL APPROVED`), to final enterprise execution completion (`ENTERPRISE EXECUTION COMPLETED`) with cryptographic provenance.

---

### 4. Live Ollama CLI — All Three Governance Conditions Demonstrated
![Three Governance Conditions in CLI](./Screenshot%20from%202026-10-11%2008-37-48.png)
* **Figure 4:** Complete verification of the three ARG governance pathways running against local Ollama (`qwen2.5:7b`):
  1. **ALLOW (Top):** Routine customer status update automatically verified and permitted with a minted grant (Risk: 25/100).
  2. **REQUIRE APPROVAL (Middle):** High-impact ₹50,000 refund paused asynchronously for manager authorization (Ticket ID: `a936b7df...`, Risk: 80/100).
  3. **DENY (Bottom):** Prohibited customer record deletion instantly blocked by compliance policy (`DESTRUCTIVE_ACTION_BLOCKED`).

---

### 5. End-to-End System Architecture: ARG Console and Northstar Freight ERP
![ARG Console and Northstar ERP](./Screenshot%20from%202026-10-11%2008-40-11.png)
* **Figure 5:** Full dual-screen production view showing the complete governance architecture. Left: ARG Console Overview (`http://localhost:3000`) displaying the live 3-node runtime topology (`Ollama` ➔ `ARG Policy Engine` ➔ `Northstar ERP`). Right: Standalone Northstar Freight Core ERP (`http://localhost:8082`) showing the updated accounts receivable ledger with `INV-2088` settled via verified ARG HMAC-SHA256 single-use proof tokens.
