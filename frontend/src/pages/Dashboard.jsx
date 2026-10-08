import SummaryCard from "../components/SummaryCard";
import AgentCard from "../components/AgentCard";
import EvidenceCard from "../components/EvidenceCard";
import ConflictPanel from "../components/ConflictPanel";
import DecisionCard from "../components/DecisionCard";

function Dashboard({
  caseData,
  summaryData,
  agents,
  evidence,
  conflict,
  decision,
  onReevaluate,
  reevaluating,
}) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">CASE {caseData.id}</span>

          <h1>{caseData.title}</h1>

          <p>{caseData.description}</p>
        </div>

        <div className="case-status">
          <span className="status-dot"></span>
          {caseData.status}
        </div>
      </div>

      <div className="summary-grid">
        {summaryData.map((item) => (
          <SummaryCard key={item.title} {...item} />
        ))}
      </div>

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <span className="section-number">01</span>
            <h2>Current Decision</h2>
          </div>
        </div>

        <DecisionCard
          decision={decision}
          onReevaluate={onReevaluate}
          reevaluating={reevaluating}
        />
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <span className="section-number">02</span>
            <h2>Agent Analysis</h2>
          </div>

          <span className="section-count">{agents.length} agents</span>
        </div>

        <div className="agent-grid">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <span className="section-number">03</span>
            <h2>Detected Conflict</h2>
          </div>
        </div>

        <ConflictPanel conflict={conflict} />
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <span className="section-number">04</span>
            <h2>Recent Evidence</h2>
          </div>

          <span className="section-count">{evidence.length} items</span>
        </div>

        <div className="evidence-list">
          {evidence.slice(0, 4).map((item) => (
            <EvidenceCard key={item.id} evidence={item} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
