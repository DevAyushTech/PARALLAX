import { useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import Dashboard from "./pages/Dashboard";
import Evidence from "./pages/Evidence";
import Agents from "./pages/Agents";
import Graph from "./pages/Graph";
import Decision from "./pages/Decision";

import {
  caseData,
  summaryData,
  agentsData,
  evidenceData,
  conflictData,
  currentDecision,
  decisionHistory,
} from "./data/mockData";

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [evidence, setEvidence] = useState(evidenceData);
  const [decision, setDecision] = useState(currentDecision);
  const [reevaluating, setReevaluating] = useState(false);

  const handleAddEvidence = (newEvidence) => {
    setEvidence((current) => [
      {
        ...newEvidence,
        id: `EV-${String(current.length + 1).padStart(3, "0")}`,
        status: "New",
        freshness: "Just now",
      },
      ...current,
    ]);
  };

  const handleReevaluate = () => {
    setReevaluating(true);

    setTimeout(() => {
      setDecision((current) => ({
        ...current,
        action: "ACT",
        reason:
          "Fresh evidence has been reviewed and the current case supports a decisive action path.",
        supportingEvidence: ["EV-001", "EV-002", "EV-006"],
        timestamp: new Date().toLocaleString(),
      }));
      setReevaluating(false);
    }, 800);
  };

  const renderPage = () => {
    switch (activePage) {
      case "Dashboard":
        return (
          <Dashboard
            caseData={caseData}
            summaryData={summaryData}
            agents={agentsData}
            evidence={evidence}
            conflict={conflictData}
            decision={decision}
            onReevaluate={handleReevaluate}
            reevaluating={reevaluating}
          />
        );
      case "Evidence":
        return <Evidence evidence={evidence} onAddEvidence={handleAddEvidence} />;
      case "Agents":
        return <Agents agents={agentsData} />;
      case "Evidence Graph":
        return <Graph />;
      case "Decision":
        return (
          <Decision
            decision={decision}
            history={decisionHistory}
            onReevaluate={handleReevaluate}
            reevaluating={reevaluating}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="app">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      <main className="main-area">
        <Topbar activePage={activePage} />

        <div className="content">{renderPage()}</div>
      </main>
    </div>
  );
}

export default App;
