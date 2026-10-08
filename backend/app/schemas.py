from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SourceType(str, Enum):
    REPORT = "REPORT"
    SENSOR = "SENSOR"
    DISPATCH = "DISPATCH"


class AgentName(str, Enum):
    PERCEPTION = "PERCEPTION"
    OPERATIONS = "OPERATIONS"
    VERIFIER = "VERIFIER"


class ConflictSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DecisionType(str, Enum):
    ACT = "ACT"
    ASK = "ASK"
    ABSTAIN = "ABSTAIN"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScenarioKey(str, Enum):
    EMERGENCY_BRIDGE_ROUTE = "emergency_bridge_route"


class Case(ContractModel):
    id: UUID
    title: str = Field(min_length=1, max_length=200)
    scenario: str = Field(min_length=1, max_length=200)
    status: CaseStatus
    risk_level: RiskLevel
    created_at: datetime


class Evidence(ContractModel):
    id: UUID
    case_id: UUID
    source_type: SourceType
    source_name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=5000)
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimDraft(ContractModel):
    """The only output shape any specialist agent may return."""

    agent_name: AgentName
    claim: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=50)
    reasoning_summary: str = Field(min_length=1, max_length=2000)
    timestamp: datetime


class Claim(ClaimDraft):
    id: UUID
    case_id: UUID


class Conflict(ContractModel):
    id: UUID
    case_id: UUID
    claim_ids: list[UUID] = Field(min_length=2, max_length=20)
    severity: ConflictSeverity
    reason: str = Field(min_length=1, max_length=2000)


class Decision(ContractModel):
    id: UUID
    case_id: UUID
    decision: DecisionType
    reason: str = Field(min_length=1, max_length=2000)
    risk_level: RiskLevel
    conflicting_claim_ids: list[UUID] = Field(default_factory=list, max_length=50)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list, max_length=50)
    next_evidence_request: str | None = Field(default=None, max_length=1000)
    created_at: datetime

    @field_validator("next_evidence_request")
    @classmethod
    def reject_blank_request(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("next_evidence_request must not be blank")
        return value


class ReevaluationAudit(ContractModel):
    previous_decision: DecisionType | None = None
    new_evidence: Evidence | None = None
    new_decision: DecisionType
    reason_for_change: str = Field(min_length=1, max_length=2000)
    created_at: datetime


class EvidenceCreate(ContractModel):
    """Input accepted by the Phase 1 evidence endpoint."""

    source_type: SourceType = Field(
        validation_alias=AliasChoices("source_type", "kind")
    )
    source_name: str = Field(
        min_length=1,
        max_length=120,
        validation_alias=AliasChoices("source_name", "source"),
    )
    content: str = Field(min_length=1, max_length=5000)
    timestamp: datetime = Field(validation_alias=AliasChoices("timestamp", "observed_at"))
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseCreate(ContractModel):
    """Input for the existing case-creation endpoint."""

    title: str = Field(
        default="Emergency bridge route decision",
        min_length=1,
        max_length=200,
    )
    scenario: str = Field(
        default=ScenarioKey.EMERGENCY_BRIDGE_ROUTE.value,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("scenario", "scenario_key"),
    )
    status: CaseStatus = CaseStatus.OPEN
    risk_level: RiskLevel = RiskLevel.HIGH
    initial_evidence: list[EvidenceCreate] = Field(default_factory=list, max_length=50)


class CaseResponse(Case):
    evidence: list[Evidence] = Field(default_factory=list)


class CaseDetail(CaseResponse):
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    decision: Decision | None = None
    audit: ReevaluationAudit | None = None


class GraphNodeType(str, Enum):
    EVIDENCE = "evidence"
    CLAIM = "claim"
    AGENT = "agent"
    CONFLICT = "conflict"
    DECISION = "decision"


class GraphNode(ContractModel):
    id: str
    type: GraphNodeType
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(ContractModel):
    source: str
    target: str
    relation: str = Field(min_length=1, max_length=50)


class EvidenceGraph(ContractModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class AnalysisResponse(ContractModel):
    case_id: UUID
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    decision: Decision
    graph: EvidenceGraph
    audit: ReevaluationAudit | None = None


# Compatibility names for the existing API module; the contract types above are canonical.
EvidenceRead = Evidence
ClaimRead = Claim
DecisionRead = CaseResponse


# Kept for callers that used the original Phase 1 action constants.
class ActionId(str, Enum):
    REROUTE_EAST_DETOUR = "REROUTE_EAST_DETOUR"
    KEEP_NORTH_BRIDGE = "KEEP_NORTH_BRIDGE"
