export const caseData = {
  id: "CASE-001",
  title: "Field Incident Analysis",
  description:
    "Operational case requiring evidence verification and decision support.",
  status: "Analyzed",
  createdAt: "2026-10-08 09:15",
};

export const summaryData = [
  {
    title: "Evidence",
    value: 6,
    subtitle: "Collected",
    type: "blue",
  },
  {
    title: "Agents",
    value: 3,
    subtitle: "Active",
    type: "purple",
  },
  {
    title: "Conflicts",
    value: 1,
    subtitle: "Detected",
    type: "orange",
  },
  {
    title: "Decision",
    value: "ASK",
    subtitle: "Current status",
    type: "yellow",
  },
];

export const agentsData = [
  {
    id: "AG-01",
    name: "Perception Agent",
    role: "Perception",
    icon: "Eye",
    claim:
      "The monitored area shows signs of abnormal activity based on recent observations.",
    confidence: 0.86,
    evidenceUsed: ["EV-001", "EV-002"],
    explanation:
      "Visual and sensor evidence indicates activity that differs from the expected baseline.",
    status: "Completed",
  },
  {
    id: "AG-02",
    name: "Operations Agent",
    role: "Operations",
    icon: "Settings",
    claim:
      "Current operational conditions may require additional field verification.",
    confidence: 0.72,
    evidenceUsed: ["EV-003", "EV-004"],
    explanation:
      "Operational records provide partial support but do not fully confirm the situation.",
    status: "Completed",
  },
  {
    id: "AG-03",
    name: "Verifier Agent",
    role: "Verifier",
    icon: "ShieldCheck",
    claim:
      "Available evidence contains conflicting information that should be verified.",
    confidence: 0.81,
    evidenceUsed: ["EV-002", "EV-005", "EV-006"],
    explanation:
      "The verifier identified disagreement between recent observations and operational records.",
    status: "Completed",
  },
];

export const evidenceData = [
  {
    id: "EV-001",
    source: "Field Sensor",
    claim: "Activity detected in monitored zone.",
    confidence: 0.91,
    timestamp: "2026-10-08 08:40",
    freshness: "8 min ago",
    type: "Sensor",
    status: "Verified",
  },
  {
    id: "EV-002",
    source: "Camera Feed",
    claim: "Movement detected near the restricted area.",
    confidence: 0.87,
    timestamp: "2026-10-08 08:43",
    freshness: "5 min ago",
    type: "Visual",
    status: "Verified",
  },
  {
    id: "EV-003",
    source: "Operations Log",
    claim: "No scheduled activity was recorded for the location.",
    confidence: 0.78,
    timestamp: "2026-10-08 08:20",
    freshness: "28 min ago",
    type: "Operational",
    status: "Verified",
  },
  {
    id: "EV-004",
    source: "Control Room",
    claim: "Area was expected to remain inactive during this period.",
    confidence: 0.74,
    timestamp: "2026-10-08 08:10",
    freshness: "38 min ago",
    type: "Report",
    status: "Verified",
  },
  {
    id: "EV-005",
    source: "Field Report",
    claim: "No unusual activity was observed during the last patrol.",
    confidence: 0.69,
    timestamp: "2026-10-08 07:55",
    freshness: "53 min ago",
    type: "Report",
    status: "Verified",
  },
  {
    id: "EV-006",
    source: "Mobile Unit",
    claim: "Additional field verification has been requested.",
    confidence: 0.83,
    timestamp: "2026-10-08 08:48",
    freshness: "2 min ago",
    type: "Field",
    status: "New",
  },
];

export const conflictData = {
  id: "C-01",
  title: "Activity Status Conflict",
  description:
    "Recent sensor and visual evidence indicate activity while operational records indicate expected inactivity.",
  severity: "Medium",
  competingClaims: [
    {
      source: "Perception Agent",
      claim: "Abnormal activity detected.",
      confidence: 0.86,
    },
    {
      source: "Operations Agent",
      claim: "No scheduled activity exists.",
      confidence: 0.72,
    },
  ],
  recommendedAction: "ASK",
};

export const currentDecision = {
  action: "ASK",
  reason:
    "The available evidence contains conflicting claims. Fresh field evidence is required before taking action.",
  supportingEvidence: ["EV-001", "EV-002", "EV-003", "EV-005"],
  conflicts: ["C-01"],
  timestamp: "2026-10-08 08:50",
};

export const decisionHistory = [
  {
    action: "ASK",
    reason: "Conflicting evidence requires additional verification.",
    timestamp: "2026-10-08 08:50",
  },
  {
    action: "ANALYSIS",
    reason: "Evidence and agent claims were evaluated.",
    timestamp: "2026-10-08 08:48",
  },
  {
    action: "EVIDENCE",
    reason: "Initial evidence was collected.",
    timestamp: "2026-10-08 08:40",
  },
];
