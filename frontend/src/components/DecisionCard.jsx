import { ShieldCheck, ArrowUpRight } from "lucide-react";

function DecisionCard({ decision, onReevaluate, reevaluating }) {
  const actionClass = decision.action.toLowerCase();

  return (
    <div className={`decision-card ${actionClass}`}>
      <div className="decision-header">
        <div>
          <span className="decision-label">CURRENT DECISION</span>

          <h2>{decision.action}</h2>
        </div>

        <div className="decision-icon">
          <ShieldCheck size={26} />
        </div>
      </div>

      <div className="decision-reason">
        <span>Reason</span>
        <p>{decision.reason}</p>
      </div>

      <div className="decision-evidence">
        <span>Supporting Evidence</span>

        <div className="decision-tags">
          {decision.supportingEvidence?.map((id) => (
            <span key={id}>{id}</span>
          ))}
        </div>
      </div>

      <div className="decision-footer">
        <span>{decision.timestamp}</span>

        <button
          className="reevaluate-button"
          onClick={onReevaluate}
          disabled={reevaluating}
        >
          <ArrowUpRight size={17} />

          {reevaluating ? "Re-evaluating..." : "Re-evaluate"}
        </button>
      </div>
    </div>
  );
}

export default DecisionCard;
