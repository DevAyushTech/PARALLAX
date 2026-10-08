import {
  caseData,
  evidenceData,
  agentsData,
  conflictData,
  currentDecision,
  decisionHistory,
} from "../data/mockData";

const delay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

export const mockApi = {
  async getCase() {
    await delay();
    return caseData;
  },

  async getEvidence() {
    await delay();
    return evidenceData;
  },

  async getAgents() {
    await delay();
    return agentsData;
  },

  async getConflict() {
    await delay();
    return conflictData;
  },

  async getDecision() {
    await delay();
    return currentDecision;
  },

  async getDecisionHistory() {
    await delay();
    return decisionHistory;
  },

  async addEvidence(evidence) {
    await delay();

    return {
      success: true,
      evidence: {
        ...evidence,
        id: `EV-${String(evidenceData.length + 1).padStart(3, "0")}`,
        status: "New",
      },
    };
  },

  async analyze() {
    await delay(1000);

    return {
      success: true,
      message: "Analysis completed successfully.",
    };
  },

  async reevaluate() {
    await delay(1200);

    return {
      success: true,
      decision: {
        action: "ACT",
        reason:
          "Fresh field evidence supports the decision to proceed with action.",
        timestamp: new Date().toLocaleString(),
      },
    };
  },
};
