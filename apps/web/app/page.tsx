"use client";

import {
  Badge,
  Button,
  FluentProvider,
  MessageBar,
  MessageBarBody,
  Spinner,
  Tab,
  TabList,
  Text,
  webLightTheme,
} from "@fluentui/react-components";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Section = "overview" | "agents" | "policies" | "approvals" | "audit";
type Agent = { id: string; name: string; enabled: boolean; key_prefix: string };
type Policy = { id: string; name: string; version: number; active: boolean; rules: { action_type: string; effect: string; reason_code: string }[] };
type Approval = { id: string; request_id: string; status: string; execution_status: string | null; action: { type: string; target: string; parameters: Record<string, unknown>; environment: string; data_classification: string }; risk_score: number; risk_factors: { name: string; points: number; reason: string }[]; reason_codes: string[]; policy_rules: { action_type: string; effect: string; reason_code: string; min_risk?: number }[]; policy_version_id: string; expires_at: string };
type AuditEvent = { id: string; request_id: string | null; event_type: string; payload: Record<string, unknown>; created_at: string };
type Overview = { agents: number; pending_approvals: number; decisions: number; allowed: number; denied: number; requires_approval: number };
type RuntimeResult = { request_id: string; decision: string; state: string; reason_codes: string[]; policy_version_id: string; risk: { score: number; factors: { name: string; points: number; reason: string }[] }; approval_id: string | null; execution: { adapter?: string; message?: string; target?: string } | null };

const navigation: { id: Section; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "agents", label: "Agents" },
  { id: "policies", label: "Policies" },
  { id: "approvals", label: "Approvals" },
  { id: "audit", label: "Audit trail" },
];

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, { cache: "no-store" });
  const data: unknown = await response.json();
  if (!response.ok) throw new Error(typeof data === "object" && data !== null && "detail" in data ? String(data.detail) : "Request failed");
  return data as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data: unknown = await response.json();
  if (!response.ok) throw new Error(typeof data === "object" && data !== null && "detail" in data ? String(data.detail) : "Request failed");
  return data as T;
}

function StatusBadge({ value }: { value: string }) {
  const appearance = value === "ALLOW" || value === "APPROVED" || value === "EXECUTED" ? "success" : value === "DENY" || value === "REJECTED" ? "danger" : "warning";
  return <Badge appearance="filled" color={appearance}>{value.replaceAll("_", " ")}</Badge>;
}

export default function Home() {
  const [section, setSection] = useState<Section>("overview");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [approvedApprovals, setApprovedApprovals] = useState<Approval[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [latest, setLatest] = useState<RuntimeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [sessionLoaded, setSessionLoaded] = useState(false);
  const [operatorToken, setOperatorToken] = useState("");
  const [agentName, setAgentName] = useState("");
  const [issuedAgentKey, setIssuedAgentKey] = useState<string | null>(null);
  const [policyName, setPolicyName] = useState("Customer Operations Guardrails");
  const [policyRules, setPolicyRules] = useState('[\n  {"action_type":"customer.record.delete","effect":"DENY","reason_code":"DESTRUCTIVE_ACTION_BLOCKED"},\n  {"action_type":"customer.record.update","effect":"REQUIRE_APPROVAL","min_risk":40,"reason_code":"HIGH_IMPACT_REVIEW"},\n  {"action_type":"customer.record.update","effect":"ALLOW","reason_code":"CUSTOMER_UPDATE_ALLOWED"}\n]');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, agentData, policyData, approvalData, approvedData, eventData] = await Promise.all([
        getJson<Overview>("overview"), getJson<Agent[]>("agents"), getJson<Policy[]>("policies"),
        getJson<Approval[]>("approvals"), getJson<Approval[]>("approvals?status=APPROVED"), getJson<AuditEvent[]>("audit-events?limit=50"),
      ]);
      setOverview(overviewData);
      setAgents(agentData);
      setPolicies(policyData);
      setApprovals(approvalData);
      setApprovedApprovals(approvedData);
      setEvents(eventData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "ARG could not load the console data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    void fetch("/api/session", { cache: "no-store" }).then(async (response) => {
      const result: { authenticated: boolean } = await response.json();
      if (!mounted) return;
      setAuthenticated(result.authenticated);
      setSessionLoaded(true);
      if (result.authenticated) await refresh();
      else setLoading(false);
    }).catch(() => { if (mounted) { setSessionLoaded(true); setLoading(false); setError("Could not check operator session."); } });
    return () => { mounted = false; };
  }, [refresh]);

  const activePolicy = useMemo(() => policies.find((policy) => policy.active), [policies]);
  const demoAgentAvailable = agents.some((agent) => agent.name === "Customer Operations Agent" && agent.enabled);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      const response = await fetch("/api/session", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: operatorToken }),
      });
      const result: { detail?: string } = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Sign-in failed");
      setOperatorToken(""); setAuthenticated(true); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-in failed"); }
    finally { setBusy(false); }
  }

  async function signOut() {
    await fetch("/api/session", { method: "DELETE" });
    setAuthenticated(false); setOverview(null); setAgents([]); setPolicies([]); setApprovals([]);
    setApprovedApprovals([]); setEvents([]); setLatest(null); setError(null); setNotice(null);
  }

  async function registerAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null); setIssuedAgentKey(null);
    try {
      const response = await postJson<{ id: string; name: string; api_key: string }>("agents", { name: agentName });
      setIssuedAgentKey(response.api_key); setAgentName(""); setNotice("Agent created. Copy this credential now; it is not shown again."); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not register agent"); }
    finally { setBusy(false); }
  }

  async function disableAgent(agent: Agent) {
    setBusy(true); setError(null);
    try { await postJson(`agents/${agent.id}/disable`, {}); setNotice(`${agent.name} disabled.`); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not disable agent"); }
    finally { setBusy(false); }
  }

  async function createPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      const rules: unknown = JSON.parse(policyRules);
      if (!Array.isArray(rules)) throw new Error("Rules must be a JSON array.");
      await postJson("policies", { name: policyName, rules }); setNotice("Policy draft created. Activate it after review."); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create policy draft"); }
    finally { setBusy(false); }
  }

  async function activatePolicy(policy: Policy) {
    setBusy(true); setError(null);
    try {
      const validation = await postJson<{ valid: boolean }>(`policies/${policy.id}/validate`, {});
      if (!validation.valid) throw new Error("Policy validation failed.");
      await postJson(`policies/${policy.id}/activate`, {});
      setNotice(`${policy.name} version ${policy.version} activated.`); await refresh();
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not activate policy"); }
    finally { setBusy(false); }
  }

  async function submitScenario(scenario: "routine" | "high_impact" | "restricted") {
    const agent = agents.find((item) => item.name === "Customer Operations Agent" && item.enabled);
    if (!agent) { setError("Enable the seeded Customer Operations Agent to run the fixed local scenarios."); return; }
    setBusy(true); setError(null); setNotice(null); setLatest(null);
    try {
      const response = await fetch("/api/demo/action", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario, agent_id: agent.id }),
      });
      const result: RuntimeResult | { detail: string } = await response.json();
      if (!response.ok || !("decision" in result)) throw new Error("detail" in result ? result.detail : "Action could not be evaluated");
      setLatest(result);
      setNotice(result.decision === "REQUIRE_APPROVAL" ? "Paused by ARG. The mock target has not been called." : result.decision === "DENY" ? "Blocked by policy. No simulated action was executed." : "Policy allowed this action. Execution remains a separate, controlled step.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Action request failed");
    } finally { setBusy(false); }
  }

  async function executeLatest() {
    if (!latest) return;
    setBusy(true); setError(null);
    try {
      const response = await fetch("/api/demo/execute", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: latest.request_id }),
      });
      const result: { status?: string; result?: RuntimeResult["execution"]; detail?: string; replayed?: boolean } = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Mock execution failed");
      setLatest({ ...latest, state: result.status ?? latest.state, execution: result.result ?? null });
      setNotice(result.result?.message ?? "The controlled mock executor completed.");
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Mock execution failed"); }
    finally { setBusy(false); }
  }

  async function resumeApproval(approval: Approval) {
    setBusy(true); setError(null);
    try {
      const response = await fetch("/api/demo/execute", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: approval.request_id }),
      });
      const result: { status?: string; result?: RuntimeResult["execution"]; detail?: string; replayed?: boolean } = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Approved action could not resume");
      setNotice(result.replayed ? "The action already executed. ARG returned its recorded outcome." : "Approved action executed through the mock adapter.");
      setLatest((current) => current?.request_id === approval.request_id
        ? { ...current, state: result.status ?? "EXECUTED", execution: result.result ?? null }
        : current);
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Approved action could not resume"); }
    finally { setBusy(false); }
  }

  async function resolveApproval(approval: Approval, action: "approve" | "reject") {
    setBusy(true); setError(null);
    try {
      await postJson(`approvals/${approval.id}/${action}`, { rationale: action === "approve" ? "Reviewed against the active demo policy." : "Rejected during demo review." });
      setNotice(action === "approve" ? "Approved. ARG is resuming the authorized request." : "Rejected. The action remains blocked.");
      if (action === "approve") await resumeApproval(approval);
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Approval update failed"); }
    finally { setBusy(false); }
  }

  if (!sessionLoaded) return <FluentProvider theme={webLightTheme}><div className="session-loading"><Spinner label="Checking operator session" /></div></FluentProvider>;
  if (!authenticated) return (
    <FluentProvider theme={webLightTheme}>
      <main className="login-shell"><form className="login-panel" onSubmit={(event) => void signIn(event)}>
        <div className="brand login-brand"><span className="brand-mark">A</span><span><strong>ARG</strong><small>Runtime Governance</small></span></div>
        <Text className="eyebrow">LOCAL OPERATOR ACCESS</Text><h1>Sign in to ARG</h1>
        <p>Enter the operator token generated in your local `.env` file.</p>
        {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
        <label htmlFor="operator-token">Operator token</label><input id="operator-token" type="password" autoComplete="current-password" value={operatorToken} onChange={(event) => setOperatorToken(event.target.value)} required />
        <Button appearance="primary" type="submit" disabled={busy || operatorToken.length < 12}>{busy ? "Signing in" : "Sign in"}</Button>
        <small>ARG clears the token from this form after sign-in and uses a short-lived, HTTP-only session cookie.</small>
      </form></main>
    </FluentProvider>
  );

  return (
    <FluentProvider theme={webLightTheme}>
      <div className="shell">
        <aside className="sidebar" aria-label="Primary navigation">
          <div className="brand"><span className="brand-mark">A</span><span><strong>ARG</strong><small>Runtime Governance</small></span></div>
          <div className="workspace-label">WORKSPACE</div>
          <div className="tenant-name"><span className="tenant-avatar">N</span><span>Northstar Demo<small>Local environment</small></span></div>
          <TabList vertical selectedValue={section} onTabSelect={(_, data) => setSection(data.value as Section)} aria-label="Console sections">
            {navigation.map((item) => <Tab key={item.id} value={item.id}>{item.label}{item.id === "approvals" && approvals.length > 0 && <span className="nav-count">{approvals.length}</span>}</Tab>)}
          </TabList>
          <div className="sidebar-foot"><span className="status-pulse" />Mock adapter configured <small>Local demo only</small><Button appearance="transparent" size="small" onClick={() => void signOut()}>Sign out</Button></div>
        </aside>

        <main className="main-content">
          <header className="topbar"><div><span className="crumb">Northstar Demo <span>/</span> {navigation.find((item) => item.id === section)?.label}</span></div><div className="topbar-right"><Badge appearance="tint" color="success">DEVELOPMENT</Badge><span className="operator-chip">Local operator</span></div></header>
          <section className="page-head"><div><Text className="eyebrow">AI ACTION CONTROL</Text><h1>{section === "overview" ? "Governance overview" : navigation.find((item) => item.id === section)?.label}</h1><p>{section === "overview" ? "Review agent activity and control every simulated action before it reaches a target." : section === "approvals" ? "Inspect action context and risk before authorizing a pending request." : "Manage the runtime controls that shape every governed action."}</p></div><Button appearance="secondary" onClick={() => void refresh()} disabled={loading}>Refresh data</Button></section>
          {error && <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>}
          {notice && <MessageBar intent="info"><MessageBarBody>{notice}</MessageBarBody></MessageBar>}
          {loading ? <div className="loading-state"><Spinner label="Loading governance data" /></div> : (
            <>
              {section === "overview" && <>
                <div className="summary-strip" aria-label="Governance summary">
                  <Summary label="Registered agents" value={overview?.agents ?? 0} detail="Known runtime identities" />
                  <Summary label="Pending approvals" value={overview?.pending_approvals ?? 0} detail="Actions paused before execution" />
                  <Summary label="Evaluated actions" value={overview?.decisions ?? 0} detail="Recorded governance decisions" />
                  <Summary label="Active policy" value={activePolicy?.name ?? "None"} detail={activePolicy ? `Version ${activePolicy.version}` : "No active policy"} />
                </div>
                <div className="content-grid">
                  <section className="panel demo-panel"><PanelHeader title="Run a controlled scenario" detail="Each proposal goes through the runtime API and uses the mock adapter." />
                    <div className="scenario-list">
                      <Scenario title="Routine customer update" detail="Low-impact update, expected to be allowed." onClick={() => void submitScenario("routine")} disabled={busy || !demoAgentAvailable} />
                      <Scenario title="High-impact update" detail="Production action with declared financial impact." onClick={() => void submitScenario("high_impact")} disabled={busy || !demoAgentAvailable} />
                      <Scenario title="Restricted deletion" detail="Explicit deny rule, no execution path." onClick={() => void submitScenario("restricted")} disabled={busy || !demoAgentAvailable} />
                    </div>
                    {latest && <div className="decision-result"><div className="result-top"><div><Text className="eyebrow">LATEST DECISION</Text><div className="decision-line"><StatusBadge value={latest.decision} /><span>Risk score {latest.risk.score}/100</span></div></div><code>{latest.request_id.slice(0, 8)}</code></div><p className="reason-line">{latest.reason_codes.join(" · ")}</p><div className="factor-row">{latest.risk.factors.map((factor) => <span key={factor.name}>{factor.name}: <b>{factor.points}</b></span>)}</div>{latest.decision === "ALLOW" && !latest.execution && <Button appearance="primary" onClick={() => void executeLatest()} disabled={busy}>Execute through mock adapter</Button>}{latest.execution && <div className="mock-outcome"><StatusBadge value={latest.state} /><span>{latest.execution.message} at {latest.execution.target}</span></div>}</div>}
                  </section>
                  <section className="panel"><PanelHeader title="Recent governance activity" detail="Latest audit events across the workspace." /><AuditList events={events.slice(0, 6)} /></section>
                </div>
              </>}
              {section === "agents" && <section className="panel"><PanelHeader title="Agent registry" detail="Credentials are stored as keyed digests. A new key is displayed once." />
                <form className="inline-form" onSubmit={(event) => void registerAgent(event)}><label htmlFor="agent-name">Agent name</label><input id="agent-name" value={agentName} onChange={(event) => setAgentName(event.target.value)} minLength={2} maxLength={120} required /><Button appearance="primary" type="submit" disabled={busy}>Register agent</Button></form>
                {issuedAgentKey && <div className="credential-result"><strong>Copy this agent credential now</strong><code>{issuedAgentKey}</code><small>ARG stores only a keyed digest. This value will not be shown again.</small></div>}
                {agents.length === 0 ? <EmptyState message="No agents registered." /> : <div className="table-wrap"><table><thead><tr><th>Agent</th><th>Key prefix</th><th>Status</th><th>Credential</th><th>Action</th></tr></thead><tbody>{agents.map((agent) => <tr key={agent.id}><td>{agent.name}</td><td><code>{agent.key_prefix}…</code></td><td><StatusBadge value={agent.enabled ? "ENABLED" : "DISABLED"} /></td><td><Button appearance="secondary" size="small" disabled={busy} onClick={async () => { setBusy(true); setIssuedAgentKey(null); try { const result = await postJson<{ api_key: string }>(`agents/${agent.id}/rotate-key`, {}); setIssuedAgentKey(result.api_key); setNotice("Credential rotated. Copy it now; the previous key is invalid."); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not rotate credential"); } finally { setBusy(false); } }}>Rotate key</Button></td><td>{agent.enabled && <Button appearance="secondary" size="small" disabled={busy} onClick={() => void disableAgent(agent)}>Disable</Button>}</td></tr>)}</tbody></table></div>}
              </section>}
              {section === "policies" && <section className="panel"><PanelHeader title="Policy versions" detail="Draft, validate, and activate deterministic rules. Active policy is rechecked before execution." />
                <form className="policy-editor" onSubmit={(event) => void createPolicy(event)}><label htmlFor="policy-name">Policy version name</label><input id="policy-name" value={policyName} onChange={(event) => setPolicyName(event.target.value)} minLength={2} maxLength={120} required /><label htmlFor="policy-rules">Rules in JSON</label><textarea id="policy-rules" rows={8} value={policyRules} onChange={(event) => setPolicyRules(event.target.value)} spellCheck={false} /><small>Effects: ALLOW, DENY, REQUIRE_APPROVAL. A deny takes precedence over an allow.</small><Button appearance="primary" type="submit" disabled={busy}>Create policy draft</Button></form>
                {policies.length === 0 ? <EmptyState message="No policy versions are available." /> : policies.map((policy) => <div className="policy-row" key={policy.id}><div><strong>{policy.name}</strong><span>Version {policy.version} · {policy.rules.length} rules</span></div><div className="policy-status"><Badge appearance="tint" color={policy.active ? "success" : "informative"}>{policy.active ? "ACTIVE" : "DRAFT"}</Badge>{!policy.active && <Button appearance="secondary" size="small" disabled={busy} onClick={() => void activatePolicy(policy)}>Validate and activate</Button>}</div><div className="rule-list">{policy.rules.map((rule, index) => <span key={`${rule.reason_code}-${index}`}><StatusBadge value={rule.effect} /> {rule.action_type} · {rule.reason_code}</span>)}</div></div>)}
              </section>}
              {section === "approvals" && <section className="panel"><PanelHeader title="Human review" detail="Review the action, risk factors, matching policy, and expiry. Pending actions have not executed." />
                {approvals.length === 0 && <EmptyState message="No pending approvals. Run the high-impact scenario to see a review request." />}
                {approvals.map((approval) => <ApprovalCard key={approval.id} approval={approval} pending busy={busy} onApprove={() => void resolveApproval(approval, "approve")} onReject={() => void resolveApproval(approval, "reject")} />)}
                {approvedApprovals.length > 0 && <div className="approved-section"><h2>Approved requests</h2>{approvedApprovals.map((approval) => <ApprovalCard key={approval.id} approval={approval} busy={busy} onResume={() => void resumeApproval(approval)} />)}</div>}
              </section>}
              {section === "audit" && <section className="panel"><PanelHeader title="Append-only audit events" detail="Trace decisions, approvals, administrative changes, and mock execution outcomes." /><AuditList events={events} /></section>}
            </>
          )}
          <footer className="page-footer"><span>ARG runtime governance prototype</span><span>Actions are simulated. No enterprise system is connected.</span></footer>
        </main>
      </div>
    </FluentProvider>
  );
}

function Summary({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return <div className="summary-item"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function PanelHeader({ title, detail }: { title: string; detail: string }) {
  return <header className="panel-header"><div><h2>{title}</h2><p>{detail}</p></div></header>;
}

function Scenario({ title, detail, onClick, disabled }: { title: string; detail: string; onClick: () => void; disabled: boolean }) {
  return <div className="scenario-row"><div><strong>{title}</strong><span>{detail}</span></div><Button appearance="secondary" onClick={onClick} disabled={disabled}>Submit action</Button></div>;
}

function ApprovalCard({
  approval, pending = false, busy, onApprove, onReject, onResume,
}: {
  approval: Approval;
  pending?: boolean;
  busy: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onResume?: () => void;
}) {
  const action = approval.action;
  const parameterSummary = Object.entries(action.parameters)
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join(" · ");
  const matchingRules = approval.policy_rules.filter((rule) => rule.action_type === action.type);

  return <article className="approval-item">
    <div className="approval-title"><div><StatusBadge value={approval.status} /><h2>{action.type}</h2><p>{action.target} · {action.environment} · {action.data_classification}</p></div><div className="risk-number">{approval.risk_score}<small>risk score</small></div></div>
    <div className="approval-facts">
      <div><span>Action parameters</span><strong>{parameterSummary || "No parameters"}</strong></div>
      <div><span>Risk factors</span><strong>{approval.risk_factors.map((factor) => `${factor.name} +${factor.points} — ${factor.reason}`).join(" · ") || "None"}</strong></div>
      <div><span>Decision reasons</span><strong>{approval.reason_codes.join(" · ")}</strong></div>
      <div><span>Policy version</span><strong>{approval.policy_version_id.slice(0, 8)} · {matchingRules.map((rule) => `${rule.effect} (${rule.reason_code})`).join(" · ") || "No action rule"}</strong></div>
    </div>
    <div className="not-executed"><span className="status-square" />{pending ? `Not executed · expires ${new Date(approval.expires_at).toLocaleString()}` : approval.execution_status ? `Execution ${approval.execution_status.toLowerCase()}` : `Approved · expires ${new Date(approval.expires_at).toLocaleString()}`}</div>
    <div className="approval-actions">
      {pending && <><Button appearance="primary" onClick={onApprove} disabled={busy}>Approve and resume</Button><Button appearance="secondary" onClick={onReject} disabled={busy}>Reject</Button></>}
      {!pending && approval.status === "APPROVED" && !approval.execution_status && <Button appearance="primary" onClick={onResume} disabled={busy}>Resume approved action</Button>}
    </div>
  </article>;
}

function AuditList({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) return <EmptyState message="Audit events will appear when ARG evaluates or changes an action." />;
  return <div className="audit-list">{events.map((event) => <div className="audit-row" key={event.id}><span className="audit-glyph" aria-hidden="true">{event.event_type.startsWith("APPROVAL") ? "A" : event.event_type.includes("EXECUTION") ? "E" : "D"}</span><div><strong>{event.event_type.replaceAll("_", " ")}</strong><small>{event.request_id ? `Request ${event.request_id.slice(0, 8)}` : "Workspace event"} · {new Date(event.created_at).toLocaleString()}</small></div><code>{String(event.payload.decision ?? event.payload.policy ?? "RECORDED")}</code></div>)}</div>;
}

function EmptyState({ message }: { message: string }) {
  return <div className="empty-state"><span className="empty-mark" aria-hidden="true">—</span><p>{message}</p></div>;
}
