import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.evaluation import _build_audit
from app.schemas import Decision, DecisionType, Evidence, RiskLevel, SourceType


class ReevaluationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_id = uuid4()
        self.now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)

    def decision(self, value: DecisionType) -> Decision:
        return Decision(
            id=uuid4(),
            case_id=self.case_id,
            decision=value,
            reason=f"Deterministic reason for {value.value}.",
            risk_level=RiskLevel.MEDIUM,
            created_at=self.now,
        )

    def test_audit_records_previous_decision_new_evidence_and_reason(self) -> None:
        previous = self.decision(DecisionType.ASK)
        current = self.decision(DecisionType.ACT)
        evidence = Evidence(
            id=uuid4(),
            case_id=self.case_id,
            source_type=SourceType.SENSOR,
            source_name="current_camera",
            content="Bridge B is blocked.",
            timestamp=self.now,
            confidence=0.97,
            metadata={},
        )

        audit = _build_audit(previous, evidence, current, is_reevaluation=True)

        assert audit is not None
        self.assertEqual(audit.previous_decision, DecisionType.ASK)
        self.assertEqual(audit.new_evidence.id, evidence.id)
        self.assertEqual(audit.new_decision, DecisionType.ACT)
        self.assertIn("changed from ASK to ACT", audit.reason_for_change)

    def test_initial_analysis_has_no_reevaluation_audit(self) -> None:
        current = self.decision(DecisionType.ABSTAIN)

        self.assertIsNone(_build_audit(None, None, current, is_reevaluation=False))


if __name__ == "__main__":
    unittest.main()
