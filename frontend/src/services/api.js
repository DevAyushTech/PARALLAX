import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getHealth = () => api.get("/api/health");

export const createCase = (data) => api.post("/api/cases", data);

export const addEvidence = (caseId, data) =>
  api.post(`/api/cases/${caseId}/evidence`, data);

export const analyzeCase = (caseId) => api.post(`/api/cases/${caseId}/analyze`);

export const getCase = (caseId) => api.get(`/api/cases/${caseId}`);

export const getEvidenceGraph = (caseId) =>
  api.get(`/api/cases/${caseId}/graph`);

export const getDecision = (caseId) => api.get(`/api/cases/${caseId}/decision`);

export const reevaluateCase = (caseId, evidence) =>
  evidence
    ? api.post(`/api/cases/${caseId}/reevaluate`, evidence)
    : api.post(`/api/cases/${caseId}/reevaluate`);

export default api;
