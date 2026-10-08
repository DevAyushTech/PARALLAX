import DecisionCard from "../components/DecisionCard";
import DecisionTimeline from "../components/DecisionTimeline";

function Decision({ decision, history, onReevaluate, reevaluating }) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">DECISION CENTER</span>

          <h1>Decision</h1>

          <p>Review the current decision, reasoning and decision history.</p>
        </div>
      </div>

      <div className="decision-page-grid">
        <div>
          <DecisionCard
            decision={decision}
            onReevaluate={onReevaluate}
            reevaluating={reevaluating}
          />
        </div>

        <div className="timeline-panel">
          <div className="panel-heading">
            <span className="eyebrow">DECISION HISTORY</span>

            <h2>Timeline</h2>
          </div>

          <DecisionTimeline history={history} />
        </div>
      </div>

      <div className="reevaluation-info">
        <div>
          <span className="eyebrow">RE-EVALUATION LOOP</span>

          <h2>New evidence can change the decision.</h2>

          <p>
            Add fresh evidence, run re-evaluation, and inspect the updated
            decision state.
          </p>
        </div>

        <div className="flow-labels">
          <span>ASK</span>
          <b>→</b>
          <span>NEW EVIDENCE</span>
          <b>→</b>
          <span>RE-EVALUATE</span>
          <b>→</b>
          <strong>ACT</strong>
        </div>
      </div>
    </div>
  );
}

export default Decision;
