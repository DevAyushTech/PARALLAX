import { CheckCircle2, FileSearch, Brain, MessageSquare } from "lucide-react";

const iconMap = {
  EVIDENCE: FileSearch,
  ANALYSIS: Brain,
  ASK: MessageSquare,
};

function DecisionTimeline({ history }) {
  return (
    <div className="timeline">
      {history.map((item, index) => {
        const Icon = iconMap[item.action] || CheckCircle2;

        return (
          <div className="timeline-item" key={index}>
            <div className="timeline-icon">
              <Icon size={17} />
            </div>

            <div className="timeline-content">
              <div className="timeline-top">
                <strong>{item.action}</strong>
                <span>{item.timestamp}</span>
              </div>

              <p>{item.reason}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default DecisionTimeline;
