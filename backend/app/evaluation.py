from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .agents import ClaimProvider, build_default_agents
from .decision_gate import evaluate_decision
from .config import DecisionThresholds, get_settings
from .evidence_graph import build_case_graph_json, identify_disagreements
from .models import (
    CaseRecord,
    ClaimRecord,
    ConflictRecord,
    DecisionRecord,
    EvidenceRecord,
    ReevaluationAuditRecord,
)
from .schemas import (
    Claim,
    Conflict,
    Decision,
    Evidence,
    EvidenceGraph,
    ReevaluationAudit,
    RiskLevel,
)


@dataclass(frozen=True)
class AnalysisBundle:
    claims: list[Claim]
    conflicts: list[Conflict]
    decision: Decision
    graph: EvidenceGraph
    audit: ReevaluationAudit | None = None


def analyze_case(
    db: Session,
    case: CaseRecord,
    *,
    provider: ClaimProvider | None = None,
    now: datetime | None = None,
    previous_decision: Decision | None = None,
    new_evidence: Evidence | None = None,
    is_reevaluation: bool = False,
) -> AnalysisBundle:
    """Run specialists, gate the result, and replace the case's current analysis."""

    evidence_records = list(
        db.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.case_id == case.id)
            .order_by(EvidenceRecord.timestamp.asc())
        ).all()
    )
    evidence = [evidence_from_record(item) for item in evidence_records]
    perception, operations, verifier = build_default_agents(llm_provider=provider)

    drafts = perception.run(evidence) + operations.run(evidence)
    drafts += verifier.run(evidence, drafts)
    evaluation_now = now or datetime.now(timezone.utc)
    claims = [
        Claim(id=uuid4(), case_id=UUID(case.id), **draft.model_dump())
        for draft in drafts
    ]
    conflicts = identify_disagreements(
        fresh_claims_for_conflicts(claims, evidence, evaluation_now)
    )
    decision = evaluate_decision(
        case.id,
        claims,
        evidence,
        conflicts,
        RiskLevel(case.risk_level),
        now=evaluation_now,
    )
    graph = EvidenceGraph.model_validate(
        build_case_graph_json(UUID(case.id), evidence, claims, conflicts, decision)
    )

    audit = _build_audit(previous_decision, new_evidence, decision, is_reevaluation)
    _replace_current_analysis(db, case.id, claims, conflicts, decision, audit)
    return AnalysisBundle(
        claims=claims,
        conflicts=conflicts,
        decision=decision,
        graph=graph,
        audit=audit,
    )


def fresh_claims_for_conflicts(
    claims: Sequence[Claim],
    evidence: Sequence[Evidence],
    now: datetime,
    thresholds: DecisionThresholds | None = None,
) -> list[Claim]:
    policy = thresholds or get_settings().decision_gate
    current = _as_utc(now)
    fresh_ids = {
        item.id
        for item in evidence
        if -policy.future_skew_seconds
        <= (current - _as_utc(item.timestamp)).total_seconds()
        <= policy.freshness_seconds
    }
    return [claim for claim in claims if set(claim.evidence_ids).issubset(fresh_ids)]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def load_current_analysis(
    db: Session,
    case_id: str,
) -> tuple[list[Evidence], list[Claim], list[Conflict], Decision | None]:
    evidence = [
        evidence_from_record(item)
        for item in db.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.case_id == case_id)
            .order_by(EvidenceRecord.timestamp.asc())
        ).all()
    ]
    claims = [
        claim_from_record(item)
        for item in db.scalars(
            select(ClaimRecord)
            .where(ClaimRecord.case_id == case_id)
            .order_by(ClaimRecord.timestamp.asc())
        ).all()
    ]
    conflicts = [
        conflict_from_record(item)
        for item in db.scalars(
            select(ConflictRecord)
            .where(ConflictRecord.case_id == case_id)
            .order_by(ConflictRecord.id.asc())
        ).all()
    ]
    decision_record = db.scalar(
        select(DecisionRecord)
        .where(DecisionRecord.case_id == case_id)
        .order_by(DecisionRecord.created_at.desc())
    )
    return evidence, claims, conflicts, decision_from_record(decision_record) if decision_record else None


def load_latest_audit(db: Session, case_id: str) -> ReevaluationAudit | None:
    record = db.scalar(
        select(ReevaluationAuditRecord)
        .where(ReevaluationAuditRecord.case_id == case_id)
        .order_by(ReevaluationAuditRecord.created_at.desc())
    )
    if record is None:
        return None
    new_evidence = (
        evidence_from_record(db.get(EvidenceRecord, record.new_evidence_id))
        if record.new_evidence_id
        else None
    )
    return ReevaluationAudit(
        previous_decision=record.previous_decision,
        new_evidence=new_evidence,
        new_decision=record.new_decision,
        reason_for_change=record.reason_for_change,
        created_at=record.created_at,
    )


def _build_audit(
    previous_decision: Decision | None,
    new_evidence: Evidence | None,
    decision: Decision,
    is_reevaluation: bool,
) -> ReevaluationAudit | None:
    if not is_reevaluation:
        return None
    if previous_decision is None:
        reason = f"Initial decision established from submitted evidence: {decision.reason}"
    elif previous_decision.decision != decision.decision:
        reason = (
            f"Decision changed from {previous_decision.decision.value} to "
            f"{decision.decision.value}: {decision.reason}"
        )
    else:
        reason = (
            f"Decision remained {decision.decision.value} after deterministic re-evaluation: "
            f"{decision.reason}"
        )
    return ReevaluationAudit(
        previous_decision=previous_decision.decision if previous_decision else None,
        new_evidence=new_evidence,
        new_decision=decision.decision,
        reason_for_change=reason,
        created_at=decision.created_at,
    )


def evidence_from_record(record: EvidenceRecord) -> Evidence:
    return Evidence(
        id=UUID(record.id),
        case_id=UUID(record.case_id),
        source_type=record.source_type,
        source_name=record.source_name,
        content=record.content,
        timestamp=record.timestamp,
        confidence=record.confidence,
        metadata=record.metadata_json or {},
    )


def claim_from_record(record: ClaimRecord) -> Claim:
    return Claim(
        id=UUID(record.id),
        case_id=UUID(record.case_id),
        agent_name=record.agent_name,
        claim=record.claim,
        confidence=record.confidence,
        evidence_ids=[UUID(item) for item in record.evidence_ids],
        reasoning_summary=record.reasoning_summary,
        timestamp=record.timestamp,
    )


def conflict_from_record(record: ConflictRecord) -> Conflict:
    return Conflict(
        id=UUID(record.id),
        case_id=UUID(record.case_id),
        claim_ids=[UUID(item) for item in record.claim_ids],
        severity=record.severity,
        reason=record.reason,
    )


def decision_from_record(record: DecisionRecord) -> Decision:
    return Decision(
        id=UUID(record.id),
        case_id=UUID(record.case_id),
        decision=record.decision,
        reason=record.reason,
        risk_level=record.risk_level,
        conflicting_claim_ids=[UUID(item) for item in record.conflicting_claim_ids],
        supporting_evidence_ids=[UUID(item) for item in record.supporting_evidence_ids],
        next_evidence_request=record.next_evidence_request,
        created_at=record.created_at,
    )


def _replace_current_analysis(
    db: Session,
    case_id: str,
    claims: Sequence[Claim],
    conflicts: Sequence[Conflict],
    decision: Decision,
    audit: ReevaluationAudit | None,
) -> None:
    # The MVP keeps the latest analysis only. Evidence remains append-only, so
    # reevaluation can always be repeated from the complete evidence set.
    db.execute(delete(DecisionRecord).where(DecisionRecord.case_id == case_id))
    db.execute(delete(ConflictRecord).where(ConflictRecord.case_id == case_id))
    db.execute(delete(ClaimRecord).where(ClaimRecord.case_id == case_id))
    db.add_all(
        [
            ClaimRecord(
                id=str(claim.id),
                case_id=case_id,
                agent_name=claim.agent_name.value,
                claim=claim.claim,
                confidence=claim.confidence,
                evidence_ids=[str(item) for item in claim.evidence_ids],
                reasoning_summary=claim.reasoning_summary,
                timestamp=claim.timestamp,
            )
            for claim in claims
        ]
    )
    db.add_all(
        [
            ConflictRecord(
                id=str(conflict.id),
                case_id=case_id,
                claim_ids=[str(item) for item in conflict.claim_ids],
                severity=conflict.severity.value,
                reason=conflict.reason,
            )
            for conflict in conflicts
        ]
    )
    db.add(
        DecisionRecord(
            id=str(decision.id),
            case_id=case_id,
            decision=decision.decision.value,
            reason=decision.reason,
            risk_level=decision.risk_level.value,
            conflicting_claim_ids=[str(item) for item in decision.conflicting_claim_ids],
            supporting_evidence_ids=[str(item) for item in decision.supporting_evidence_ids],
            next_evidence_request=decision.next_evidence_request,
            created_at=decision.created_at,
        )
    )
    if audit is not None:
        db.add(
            ReevaluationAuditRecord(
                case_id=case_id,
                previous_decision=audit.previous_decision.value if audit.previous_decision else None,
                new_evidence_id=str(audit.new_evidence.id) if audit.new_evidence else None,
                new_decision=audit.new_decision.value,
                reason_for_change=audit.reason_for_change,
                created_at=audit.created_at,
            )
        )
    db.commit()
