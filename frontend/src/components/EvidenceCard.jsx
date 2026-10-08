import { FileText, CheckCircle2, Clock3 } from "lucide-react";

function EvidenceCard({ evidence }) {
  return (
    <div className="evidence-card">
      <div className="evidence-card-header">
        <div className="evidence-source">
          <div className="evidence-icon">
            <FileText size={18} />
          </div>

          <div>
            <h3>{evidence.id}</h3>
            <span>{evidence.source}</span>
          </div>
        </div>

        <span className="status-badge verified">
          <CheckCircle2 size={14} />
          {evidence.status}
        </span>
      </div>

      <div className="evidence-content">
        <label>CLAIM / CONTENT</label>
        <p>{evidence.claim}</p>
      </div>

      <div className="evidence-meta">
        <div>
          <span>Confidence</span>
          <strong>{Math.round(evidence.confidence * 100)}%</strong>
        </div>

        <div>
          <span>Type</span>
          <strong>{evidence.type}</strong>
        </div>

        <div>
          <span>Timestamp</span>
          <strong>{evidence.timestamp}</strong>
        </div>

        <div>
          <span>Freshness</span>
          <strong>
            <Clock3 size={14} />
            {evidence.freshness}
          </strong>
        </div>
      </div>
    </div>
  );
}

export default EvidenceCard;
