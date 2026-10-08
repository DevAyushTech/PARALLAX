"""The deterministic PARALLAX decision engine.

This module consumes structured data only. It never calls a model and has no
code path that accepts an LLM-generated ACT, ASK, or ABSTAIN value.
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone
from itertools import combinations
from uuid import UUID, uuid4

from .config import DecisionThresholds, get_settings
from .evidence_graph import extract_claim_subject
from .schemas import Claim, Conflict, ConflictSeverity, Decision, DecisionType, Evidence, RiskLevel


def evaluate_decision(
    case_id: UUID | str,
    claims: Sequence[Claim],
    evidence: Sequence[Evidence],
    conflicts: Sequence[Conflict] = (),
    risk_level: RiskLevel = RiskLevel.HIGH,
    *,
    thresholds: DecisionThresholds | None = None,
    now: datetime | None = None,
) -> Decision:
    """Evaluate one case using fail-closed, configurable deterministic rules.

    Claims are material only when their confidence and every cited evidence item
    pass the configured freshness/confidence thresholds. Explicit conflicts and
    plainly structured ``subject is value`` disagreements are considered. A
    stale claim is excluded rather than allowed to outweigh fresh evidence.
    """

    case_uuid = UUID(str(case_id))
    risk_level = RiskLevel(risk_level)
    policy = thresholds or get_settings().decision_gate
    evaluated_at = _utc(now or datetime.now(timezone.utc))
    records = [*claims, *evidence, *conflicts]
    if any(record.case_id != case_uuid for record in records):
        raise ValueError("All decision inputs must belong to the requested case")
    for items in (claims, evidence, conflicts):
        if len({item.id for item in items}) != len(items):
            raise ValueError("Decision inputs must have unique IDs within each record type")

    evidence_by_id = {item.id: item for item in evidence}
    claim_by_id = {claim.id: claim for claim in claims}
    conflicting_claim_ids: set[UUID] = set()
    supporting_evidence_ids: set[UUID] = set()

    def result(
        decision: DecisionType,
        reason: str,
        next_evidence_request: str | None = None,
    ) -> Decision:
        return Decision(
            id=uuid4(),
            case_id=case_uuid,
            decision=decision,
            reason=reason,
            risk_level=risk_level,
            conflicting_claim_ids=sorted(conflicting_claim_ids, key=str),
            supporting_evidence_ids=sorted(supporting_evidence_ids, key=str),
            next_evidence_request=next_evidence_request,
            created_at=evaluated_at,
        )

    if any(reference not in evidence_by_id for claim in claims for reference in claim.evidence_ids):
        return result(DecisionType.ABSTAIN, "Claim references missing evidence; safety cannot be established.")
    if any(reference not in claim_by_id for conflict in conflicts for reference in conflict.claim_ids):
        return result(DecisionType.ABSTAIN, "Conflict references missing claims; safety cannot be established.")

    fresh_evidence_ids = {
        item.id
        for item in evidence
        if -policy.future_skew_seconds
        <= (evaluated_at - _utc(item.timestamp)).total_seconds()
        <= policy.freshness_seconds
    }
    grounded_claims = [
        claim for claim in claims if set(claim.evidence_ids).issubset(fresh_evidence_ids)
    ]
    if not grounded_claims:
        return result(DecisionType.ABSTAIN, "No claims have sufficiently fresh supporting evidence.")

    effective_confidence = {
        claim.id: min(
            claim.confidence,
            *(evidence_by_id[reference].confidence for reference in claim.evidence_ids),
        )
        for claim in grounded_claims
    }
    material_claims = [
        claim
        for claim in grounded_claims
        if effective_confidence[claim.id] >= policy.material_confidence
    ]
    if not material_claims:
        return result(DecisionType.ABSTAIN, "Critical safety cannot be established with the available confidence.")

    for claim in material_claims:
        supporting_evidence_ids.update(claim.evidence_ids)

    fact_groups: dict[str, list[tuple[Claim, str]]] = defaultdict(list)
    for claim in material_claims:
        fact = extract_claim_subject(claim.claim)
        if fact is not None:
            subject, value = fact
            fact_groups[subject].append((claim, value))

    # A free-form claim without an explicit subject/value cannot establish a
    # critical fact, but it may still be retained for traceability in callers.
    if not fact_groups:
        return result(DecisionType.ABSTAIN, "Critical safety cannot be established from unstructured claims.")

    disagreement_pairs: list[tuple[Claim, Claim, str]] = []
    for subject, subject_claims in fact_groups.items():
        for (left, left_value), (right, right_value) in combinations(subject_claims, 2):
            if left_value != right_value:
                disagreement_pairs.append((left, right, subject))
                conflicting_claim_ids.update((left.id, right.id))

    active_conflicts = []
    for conflict in conflicts:
        active_claim_ids = set(conflict.claim_ids).intersection(
            claim.id for claim in material_claims
        )
        if len(active_claim_ids) >= 2:
            active_conflicts.append(conflict)
            conflicting_claim_ids.update(active_claim_ids)

    has_conflict = bool(disagreement_pairs or active_conflicts)
    if has_conflict:
        severe_by_claims = any(
            min(effective_confidence[left.id], effective_confidence[right.id])
            >= policy.severe_conflict_confidence
            for left, right, _ in disagreement_pairs
        )
        severe_by_records = any(conflict.severity == ConflictSeverity.HIGH for conflict in active_conflicts)
        if risk_level == RiskLevel.HIGH:
            return result(
                DecisionType.ABSTAIN,
                "Critical safety conflict remains unresolved in a HIGH-risk scenario.",
            )
        if severe_by_claims or severe_by_records:
            return result(
                DecisionType.ABSTAIN,
                "Evidence is severely contradictory; critical safety remains unresolved.",
            )

        equal_confidence = any(
            abs(effective_confidence[left.id] - effective_confidence[right.id])
            <= policy.equal_confidence_tolerance
            for left, right, _ in disagreement_pairs
        )
        reason = (
            "Material claims have equal confidence and conflict; additional evidence could resolve the tie."
            if equal_confidence
            else "Material claims conflict, but additional evidence could reasonably resolve it."
        )
        subjects = sorted({subject for _, _, subject in disagreement_pairs})
        subjects.extend(
            conflict.reason for conflict in active_conflicts if conflict.reason not in subjects
        )
        subject_text = ", ".join(subjects) or "the conflicting claims"
        return result(
            DecisionType.ASK,
            reason,
            f"Request fresh independent evidence addressing {subject_text}.",
        )

    if any(effective_confidence[claim.id] < policy.act_confidence for claim in material_claims):
        return result(
            DecisionType.ASK,
            "Material claims agree, but confidence is below the ACT threshold.",
            "Request fresh independent confirmation of the low-confidence claims.",
        )

    stale_excluded = len(fresh_evidence_ids) < len(evidence)
    reason = "Material claims agree and their supporting evidence is sufficiently fresh."
    if stale_excluded:
        reason += " Stale evidence was excluded from this evaluation."
    if risk_level == RiskLevel.HIGH:
        reason += " No unresolved high-risk conflict remains."
    return result(DecisionType.ACT, reason)



class DecisionEngine:
    """Reusable façade for callers that evaluate multiple case snapshots."""

    def __init__(self, thresholds: DecisionThresholds | None = None) -> None:
        self.thresholds = thresholds or get_settings().decision_gate

    def evaluate(
        self,
        case_id: UUID | str,
        claims: Sequence[Claim],
        evidence: Sequence[Evidence],
        conflicts: Sequence[Conflict] = (),
        risk_level: RiskLevel = RiskLevel.HIGH,
        *,
        now: datetime | None = None,
    ) -> Decision:
        return evaluate_decision(
            case_id,
            claims,
            evidence,
            conflicts,
            risk_level,
            thresholds=self.thresholds,
            now=now,
        )


# Keep the module vocabulary aligned with the product name used in the demo.
DecisionGate = DecisionEngine


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
