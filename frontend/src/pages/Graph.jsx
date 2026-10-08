import { FileSearch, Bot, AlertTriangle, Gavel, ArrowDown } from "lucide-react";

function Graph() {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">REASONING GRAPH</span>

          <h1>Evidence Graph</h1>

          <p>
            Trace how evidence moves through agents, conflicts and the final
            decision.
          </p>
        </div>
      </div>

      <div className="graph-container">
        <div className="graph-node evidence-node">
          <div className="graph-node-icon">
            <FileSearch size={22} />
          </div>

          <div>
            <span>01</span>
            <h3>Evidence</h3>
            <p>EV-001 → EV-006</p>
          </div>
        </div>

        <ArrowDown className="graph-arrow" />

        <div className="graph-node agent-node">
          <div className="graph-node-icon">
            <Bot size={22} />
          </div>

          <div>
            <span>02</span>
            <h3>Agent Claims</h3>
            <p>Perception · Operations · Verifier</p>
          </div>
        </div>

        <ArrowDown className="graph-arrow" />

        <div className="graph-node conflict-node">
          <div className="graph-node-icon">
            <AlertTriangle size={22} />
          </div>

          <div>
            <span>03</span>
            <h3>Conflict</h3>
            <p>C-01 · Activity Status Conflict</p>
          </div>
        </div>

        <ArrowDown className="graph-arrow" />

        <div className="graph-node decision-node">
          <div className="graph-node-icon">
            <Gavel size={22} />
          </div>

          <div>
            <span>04</span>
            <h3>Decision</h3>
            <p>ASK · Fresh evidence required</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Graph;
