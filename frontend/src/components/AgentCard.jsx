import { Eye, Settings, ShieldCheck, CheckCircle2 } from "lucide-react";

const iconMap = {
  Eye,
  Settings,
  ShieldCheck,
};

function AgentCard({ agent }) {
  const Icon = iconMap[agent.icon] || ShieldCheck;

  return (
    <div className="agent-card">
      <div className="agent-header">
        <div className="agent-icon">
          <Icon size={20} />
        </div>

        <div className="agent-title">
          <h3>{agent.name}</h3>
          <span>{agent.role} Agent</span>
        </div>

        <div className="agent-status">
          <CheckCircle2 size={15} />
          {agent.status}
        </div>
      </div>

      <div className="agent-claim">
        <label>CLAIM</label>
        <p>{agent.claim}</p>
      </div>

      <div className="confidence-section">
        <div className="confidence-label">
          <span>Confidence</span>
          <strong>{Math.round(agent.confidence * 100)}%</strong>
        </div>

        <div className="confidence-bar">
          <div
            className="confidence-fill"
            style={{
              width: `${agent.confidence * 100}%`,
            }}
          ></div>
        </div>
      </div>

      <div className="agent-evidence">
        <label>Evidence Used</label>

        <div className="evidence-tags">
          {agent.evidenceUsed.map((id) => (
            <span key={id}>{id}</span>
          ))}
        </div>
      </div>

      <div className="agent-explanation">
        <label>Explanation</label>
        <p>{agent.explanation}</p>
      </div>
    </div>
  );
}

export default AgentCard;
