import { AlertTriangle, ArrowUpRight } from "lucide-react";

function ConflictPanel({ conflict }) {
  return (
    <div className="conflict-panel">
      <div className="conflict-header">
        <div className="conflict-title">
          <div className="conflict-icon">
            <AlertTriangle size={18} />
          </div>

          <div>
            <h3>{conflict.title}</h3>
            <span>{conflict.id}</span>
          </div>
        </div>

        <span className="severity-badge">{conflict.severity}</span>
      </div>

      <p className="conflict-description">{conflict.description}</p>

      <div className="competing-claims">
        {conflict.competingClaims.map((claim) => (
          <div className="claim-box" key={claim.source}>
            <span>{claim.source}</span>
            <p>{claim.claim}</p>
            <strong>{Math.round(claim.confidence * 100)}% confidence</strong>
          </div>
        ))}
      </div>

      <div className="conflict-footer">
        <span>Recommended next action</span>

        <div className="action-outline">
          <ArrowUpRight size={14} />
          {conflict.recommendedAction}
        </div>
      </div>
    </div>
  );
}

export default ConflictPanel;
