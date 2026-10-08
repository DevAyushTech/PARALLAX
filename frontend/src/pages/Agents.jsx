import AgentCard from "../components/AgentCard";

function Agents({ agents }) {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">MULTI-AGENT ANALYSIS</span>

          <h1>Agents</h1>

          <p>
            Review claims and reasoning produced by the PARALLAX analysis
            agents.
          </p>
        </div>
      </div>

      <div className="agent-grid agents-page-grid">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}

export default Agents;
