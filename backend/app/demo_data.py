"""Deterministic, frontend-independent scenarios for the hackathon demo.

The data contains no expected decision field. Each state is passed through the
same agents, conflict detection, graph builder, and deterministic gate used by
runtime analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from .agents import LLMClaimProvider, build_default_agents
from .decision_gate import evaluate_decision
from .evidence_graph import build_case_graph_json, identify_disagreements
from .evaluation import fresh_claims_for_conflicts
from .schemas import (
    Case,
    CaseStatus,
    Claim,
    ClaimDraft,
    Conflict,
    Decision,
    Evidence,
    EvidenceGraph,
    RiskLevel,
    SourceType,
)

DEMO_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class DemoScenario:
    key: str
    case: Case
    initial_evidence: tuple[Evidence, ...]
    followup_evidence: tuple[Evidence, ...]
    initial_at: datetime
    reevaluation_at: datetime


@dataclass(frozen=True)
class DemoEvaluation:
    claims: list[Claim]
    conflicts: list[Conflict]
    decision: Decision
    graph: EvidenceGraph


def demo_scenarios() -> dict[str, DemoScenario]:
    """Return fresh deterministic copies of all four demo scenarios."""

    return {
        "bridge_conflict": _bridge_conflict(),
        "fully_agree_act": _fully_agree_act(),
        "critical_abstain": _critical_abstain(),
        "mock_provider_fallback": _mock_provider_fallback(),
    }


def evaluate_demo(
    scenario: DemoScenario,
    evidence: Sequence[Evidence] | None = None,
    *,
    at: datetime | None = None,
) -> DemoEvaluation:
    """Run a scenario through the real deterministic pipeline."""

    evaluation_at = at or scenario.initial_at
    evidence = tuple(scenario.initial_evidence if evidence is None else evidence)
    # An unavailable provider is intentional here. build_default_agents falls
    # back to MockClaimProvider without changing the claim contract.
    perception, operations, verifier = build_default_agents(
        llm_provider=LLMClaimProvider()
    )
    drafts = perception.run(evidence) + operations.run(evidence)
    drafts += verifier.run(evidence, drafts)
    claims = [_claim_from_draft(scenario, draft, evaluation_at) for draft in drafts]
    conflicts = identify_disagreements(
        fresh_claims_for_conflicts(claims, evidence, evaluation_at)
    )
    decision = evaluate_decision(
        scenario.case.id,
        claims,
        evidence,
        conflicts,
        scenario.case.risk_level,
        now=evaluation_at,
    )
    graph = EvidenceGraph.model_validate(
        build_case_graph_json(scenario.case.id, evidence, claims, conflicts, decision)
    )
    return DemoEvaluation(claims, conflicts, decision, graph)


def _claim_from_draft(scenario: DemoScenario, draft: ClaimDraft, timestamp: datetime) -> Claim:
    payload = draft.model_dump()
    payload["timestamp"] = timestamp
    return Claim(
        id=uuid5(
            NAMESPACE_URL,
            f"parallax:demo:claim:{scenario.key}:{draft.agent_name.value}:"
            f"{draft.claim}:{','.join(str(item) for item in draft.evidence_ids)}",
        ),
        case_id=scenario.case.id,
        **payload,
    )


def _bridge_conflict() -> DemoScenario:
    case = _case("bridge-conflict", "Bridge B conflict assessment", RiskLevel.MEDIUM)
    initial_at = DEMO_NOW
    return DemoScenario(
        key="bridge_conflict",
        case=case,
        initial_evidence=(
            _evidence(case.id, "camera", SourceType.SENSOR, "bridge_camera", "Bridge B is blocked", 0.92, initial_at),
            _evidence(case.id, "status", SourceType.DISPATCH, "status_feed", "Bridge B is open", 0.74, initial_at - timedelta(minutes=12)),
            _evidence(case.id, "field", SourceType.REPORT, "field_report", "Access uncertain", 0.61, initial_at - timedelta(minutes=3)),
        ),
        followup_evidence=(
            _evidence(case.id, "fresh-camera", SourceType.SENSOR, "camera_current", "Bridge B is blocked", 0.97, initial_at + timedelta(minutes=5)),
        ),
        initial_at=initial_at,
        reevaluation_at=initial_at + timedelta(minutes=5),
    )


def _fully_agree_act() -> DemoScenario:
    case = _case("fully-agree-act", "Bridge B agreeing evidence", RiskLevel.MEDIUM)
    return DemoScenario(
        key="fully_agree_act",
        case=case,
        initial_evidence=(
            _evidence(case.id, "camera", SourceType.SENSOR, "bridge_camera", "Bridge B is blocked", 0.93, DEMO_NOW),
            _evidence(case.id, "status", SourceType.DISPATCH, "status_feed", "Bridge B is blocked", 0.91, DEMO_NOW),
        ),
        followup_evidence=(),
        initial_at=DEMO_NOW,
        reevaluation_at=DEMO_NOW,
    )


def _critical_abstain() -> DemoScenario:
    case = _case("critical-abstain", "Critical bridge safety disagreement", RiskLevel.HIGH)
    return DemoScenario(
        key="critical_abstain",
        case=case,
        initial_evidence=(
            _evidence(case.id, "camera", SourceType.SENSOR, "bridge_camera", "Bridge B is safe", 0.96, DEMO_NOW),
            _evidence(case.id, "status", SourceType.DISPATCH, "status_feed", "Bridge B is unsafe", 0.96, DEMO_NOW),
        ),
        followup_evidence=(),
        initial_at=DEMO_NOW,
        reevaluation_at=DEMO_NOW,
    )


def _mock_provider_fallback() -> DemoScenario:
    case = _case("mock-provider-fallback", "LLM unavailable demo", RiskLevel.MEDIUM)
    return DemoScenario(
        key="mock_provider_fallback",
        case=case,
        initial_evidence=(
            _evidence(case.id, "camera", SourceType.SENSOR, "bridge_camera", "Bridge B is blocked", 0.88, DEMO_NOW),
            _evidence(case.id, "dispatch", SourceType.DISPATCH, "route_operations", "Bridge B is blocked", 0.87, DEMO_NOW),
        ),
        followup_evidence=(),
        initial_at=DEMO_NOW,
        reevaluation_at=DEMO_NOW,
    )


def _case(key: str, title: str, risk_level: RiskLevel) -> Case:
    return Case(
        id=uuid5(NAMESPACE_URL, f"parallax:demo:case:{key}"),
        title=title,
        scenario="emergency_bridge_route",
        status=CaseStatus.OPEN,
        risk_level=risk_level,
        created_at=DEMO_NOW,
    )


def _evidence(
    case_id: UUID,
    key: str,
    source_type: SourceType,
    source_name: str,
    content: str,
    confidence: float,
    timestamp: datetime,
) -> Evidence:
    return Evidence(
        id=uuid5(NAMESPACE_URL, f"parallax:demo:evidence:{case_id}:{key}"),
        case_id=case_id,
        source_type=source_type,
        source_name=source_name,
        content=content,
        timestamp=timestamp,
        confidence=confidence,
        metadata={"demo": True, "fixture_key": key},
    )
