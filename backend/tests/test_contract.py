import unittest
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from app.schemas import (
    AgentName,
    Case,
    CaseStatus,
    Claim,
    Conflict,
    ConflictSeverity,
    Decision,
    DecisionType,
    Evidence,
    RiskLevel,
    SourceType,
)


class StructuredContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_id = uuid4()
        self.evidence_id = uuid4()
        self.claim_id = uuid4()
        self.now = datetime.now(timezone.utc)

    def test_valid_payloads(self) -> None:
        case = Case(
            id=self.case_id,
            title="Emergency bridge route",
            scenario="emergency_bridge_route",
            status=CaseStatus.OPEN,
            risk_level=RiskLevel.HIGH,
            created_at=self.now,
        )
        evidence = Evidence(
            id=self.evidence_id,
            case_id=case.id,
            source_type=SourceType.SENSOR,
            source_name="bridge_sensor_7",
            content="Water level is rising near the North Bridge.",
            timestamp=self.now,
            confidence=0.92,
            metadata={"unit": "meters", "reading": 4.2},
        )
        claim = Claim(
            id=self.claim_id,
            case_id=case.id,
            agent_name=AgentName.PERCEPTION,
            claim="North Bridge conditions are unsafe for emergency traffic.",
            confidence=0.88,
            evidence_ids=[evidence.id],
            reasoning_summary="The sensor reading exceeds the emergency threshold.",
            timestamp=self.now,
        )
        conflict = Conflict(
            id=uuid4(),
            case_id=case.id,
            claim_ids=[claim.id, uuid4()],
            severity=ConflictSeverity.HIGH,
            reason="Operations reports the bridge remains passable.",
        )
        decision = Decision(
            id=uuid4(),
            case_id=case.id,
            decision=DecisionType.ASK,
            reason="Specialists disagree about bridge safety.",
            risk_level=RiskLevel.HIGH,
            conflicting_claim_ids=conflict.claim_ids,
            supporting_evidence_ids=[evidence.id],
            next_evidence_request="Request a current structural inspection.",
            created_at=self.now,
        )

        self.assertEqual(case.status, CaseStatus.OPEN)
        self.assertEqual(evidence.metadata["reading"], 4.2)
        self.assertEqual(claim.evidence_ids, [evidence.id])
        self.assertEqual(conflict.severity, ConflictSeverity.HIGH)
        self.assertEqual(decision.decision, DecisionType.ASK)

    def test_case_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(ValidationError):
            Case(
                id=self.case_id,
                title="Emergency bridge route",
                scenario="emergency_bridge_route",
                status=CaseStatus.OPEN,
            )

    def test_evidence_rejects_bad_confidence_and_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            Evidence(
                id=self.evidence_id,
                case_id=self.case_id,
                source_type=SourceType.REPORT,
                source_name="operator",
                content="Report",
                timestamp=self.now,
                confidence=1.1,
            )

        with self.assertRaises(ValidationError):
            Evidence(
                id=self.evidence_id,
                case_id=self.case_id,
                source_type=SourceType.REPORT,
                source_name="operator",
                content="Report",
                timestamp=self.now,
                confidence=0.5,
                unexpected="reject me",
            )

    def test_claim_rejects_empty_evidence_links(self) -> None:
        with self.assertRaises(ValidationError):
            Claim(
                id=self.claim_id,
                case_id=self.case_id,
                agent_name=AgentName.OPERATIONS,
                claim="The detour is clear.",
                confidence=0.8,
                evidence_ids=[],
                reasoning_summary="No evidence was linked.",
                timestamp=self.now,
            )

    def test_conflict_and_decision_reject_malformed_enums(self) -> None:
        with self.assertRaises(ValidationError):
            Conflict(
                id=uuid4(),
                case_id=self.case_id,
                claim_ids=[self.claim_id],
                severity="urgent",
                reason="Invalid conflict payload.",
            )

        with self.assertRaises(ValidationError):
            Decision(
                id=uuid4(),
                case_id=self.case_id,
                decision="MAYBE",
                reason="Invalid decision payload.",
                risk_level=RiskLevel.LOW,
                created_at=self.now,
            )


if __name__ == "__main__":
    unittest.main()
