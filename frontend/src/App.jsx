import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import {
  addEvidence,
  analyzeCase,
  createCase,
  getCase,
  getHealth,
  reevaluateCase,
} from "./services/api";

const scenario = "emergency_bridge_route";
const nowIso = () => new Date().toISOString();

const initialEvidence = [
  {
    source_type: "SENSOR",
    source_name: "camera",
    content: "Bridge B is blocked",
    confidence: 0.92,
  },
  {
    source_type: "DISPATCH",
    source_name: "status_feed",
    content: "Bridge B is open",
    confidence: 0.74,
  },
  {
    source_type: "REPORT",
    source_name: "field_report",
    content: "Access uncertain",
    confidence: 0.61,
  },
];

function App() {
  const [caseId, setCaseId] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [freshContent, setFreshContent] = useState("Bridge B is blocked");
  const [freshConfidence, setFreshConfidence] = useState("0.97");
  const started = useRef(false);

  const claimsByAgent = useMemo(() => {
    const groups = {};
    (snapshot?.claims || []).forEach((claim) => {
      groups[claim.agent_name] ||= [];
      groups[claim.agent_name].push(claim);
    });
    return groups;
  }, [snapshot]);

  useEffect(() => {
    if (!started.current) {
      started.current = true;
      startDemo();
    }
  }, []);

  async function startDemo() {
    setLoading(true);
    setError("");
    try {
      await getHealth();
      const created = await createCase({
        title: "Emergency Bridge B assessment",
        scenario,
        risk_level: "MEDIUM",
      });
      const id = created.data.id;
      setCaseId(id);
      for (const item of initialEvidence) {
        await addEvidence(id, { ...item, timestamp: nowIso(), metadata: {} });
      }
      const analyzed = await analyzeCase(id);
      const currentCase = await getCase(id);
      setSnapshot({ ...analyzed.data, evidence: currentCase.data.evidence });
    } catch (err) {
      setError(readError(err));
    } finally {
      setLoading(false);
    }
  }

  async function submitFreshEvidence(event) {
    event.preventDefault();
    if (!caseId || !freshContent.trim()) return;
    setWorking(true);
    setError("");
    try {
      const response = await reevaluateCase(caseId, {
        source_type: "DISPATCH",
        source_name: "current_road_crew",
        content: freshContent.trim(),
        timestamp: nowIso(),
        confidence: Number(freshConfidence),
        metadata: { demo: true, fresh: true },
      });
      const currentCase = await getCase(caseId);
      setSnapshot({ ...response.data, evidence: currentCase.data.evidence });
    } catch (err) {
      setError(readError(err));
    } finally {
      setWorking(false);
    }
  }

  if (loading) {
    return <main className="demo-shell"><div className="panel loading">Connecting to PARALLAX and running the initial analysis…</div></main>;
  }

  const decision = snapshot?.decision;
  return (
    <main className="demo-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">PARALLAX / LIVE BACKEND DEMO</p>
          <h1>Emergency bridge route assessment</h1>
          <p className="subtitle">Evidence → specialist claims → conflict → deterministic decision gate</p>
        </div>
        <button className="secondary" onClick={startDemo}>Reset demo</button>
      </header>

      {error && <div className="error">{error}</div>}

      <section className={`decision decision-${String(decision?.decision || "").toLowerCase()}`}>
        <div>
          <p className="eyebrow">CURRENT GATE RESULT</p>
          <strong>{decision?.decision || "NOT ANALYZED"}</strong>
          <p>{decision?.reason || "No decision available."}</p>
        </div>
        <div className="decision-meta">
          <span>Risk: {decision?.risk_level || snapshot?.risk_level}</span>
          <span>Conflicts: {snapshot?.conflicts?.length || 0}</span>
          {decision?.next_evidence_request && <span>Request: {decision.next_evidence_request}</span>}
        </div>
      </section>

      {snapshot?.audit && (
        <section className="panel audit">
          <p className="eyebrow">REEVALUATION AUDIT</p>
          <div className="audit-grid">
            <span>Previous decision<strong>{snapshot.audit.previous_decision || "—"}</strong></span>
            <span>New evidence<strong>{snapshot.audit.new_evidence?.content || "Stored evidence"}</strong></span>
            <span>New decision<strong>{snapshot.audit.new_decision}</strong></span>
          </div>
          <p>{snapshot.audit.reason_for_change}</p>
        </section>
      )}

      <div className="workflow">
        <section className="panel">
          <div className="panel-heading"><h2>1. Evidence</h2><span>{snapshot?.evidence?.length || 0} items</span></div>
          <div className="evidence-list">
            {(snapshot?.evidence || []).map((item) => (
              <article className="evidence" key={item.id}>
                <div><b>{item.source_name}</b><span>{item.source_type} · {Math.round(item.confidence * 100)}%</span></div>
                <p>{item.content}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading"><h2>2. Specialist claims</h2><span>3 roles</span></div>
          <div className="agents">
            {["PERCEPTION", "OPERATIONS", "VERIFIER"].map((agent) => (
              <div className="agent" key={agent}>
                <b>{agent}</b>
                {(claimsByAgent[agent] || []).map((claim) => <p key={claim.id}>{claim.claim}<small>{Math.round(claim.confidence * 100)}% confidence</small></p>)}
                {!claimsByAgent[agent]?.length && <p className="muted">No applicable claim</p>}
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel conflict-panel">
        <div className="panel-heading"><h2>3. Conflicts and trace</h2><span>{snapshot?.graph?.nodes?.length || 0} nodes</span></div>
        {(snapshot?.conflicts || []).length ? snapshot.conflicts.map((conflict) => (
          <article className="conflict" key={conflict.id}><b>{conflict.severity} conflict</b><p>{conflict.reason}</p><small>Claims: {conflict.claim_ids.join(", ")}</small></article>
        )) : <p className="success">No current material conflict detected.</p>}
        <details><summary>Show graph JSON</summary><pre>{JSON.stringify(snapshot?.graph, null, 2)}</pre></details>
      </section>

      <section className="panel fresh-panel">
        <div className="panel-heading"><h2>4. Submit fresh evidence and re-evaluate</h2><span>Deterministic / no autonomous action</span></div>
        <form onSubmit={submitFreshEvidence} className="fresh-form">
          <input value={freshContent} onChange={(event) => setFreshContent(event.target.value)} aria-label="Fresh evidence" />
          <input value={freshConfidence} onChange={(event) => setFreshConfidence(event.target.value)} type="number" min="0" max="1" step="0.01" aria-label="Confidence" />
          <button disabled={working || !caseId}>{working ? "Re-evaluating…" : "Re-evaluate"}</button>
        </form>
        <p className="muted">The backend calculates ACT / ASK / ABSTAIN. This button only submits evidence and requests evaluation. In quick demo mode, wait for the freshness window before submitting to see stale conflict evidence excluded.</p>
      </section>
    </main>
  );
}

function readError(error) {
  return error?.response?.data?.detail || error?.message || "Could not reach the PARALLAX backend.";
}

export default App;
