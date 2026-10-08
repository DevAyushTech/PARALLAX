import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.agents import build_default_agents
from app.config import DecisionThresholds
from app.decision_gate import evaluate_decision
from app.schemas import (
    AgentName,
    Claim,
    Conflict,
    ConflictSeverity,
    DecisionType,
    Evidence,
    RiskLevel,
    SourceType,
)


class DecisionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_id = uuid4()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.thresholds = DecisionThresholds()

    def evidence(self, content: str, confidence: float = 0.9, age: timedelta = timedelta()) -> Evidence:
        return Evidence(
            id=uuid4(),
            case_id=self.case_id,
            source_type=SourceType.REPORT,
            source_name="bridge_demo",
            content=content,
            timestamp=self.now - age,
            confidence=confidence,
            metadata={},
        )

    def claim(
        self,
        content: str,
        evidence: Evidence,
        agent: AgentName = AgentName.PERCEPTION,
        confidence: float = 0.9,
    ) -> Claim:
        return Claim(
            id=uuid4(),
            case_id=self.case_id,
            agent_name=agent,
            claim=content,
            confidence=confidence,
            evidence_ids=[evidence.id],
            reasoning_summary="Test structured claim.",
            timestamp=self.now,
        )

    def conflict(self, left: Claim, right: Claim, severity: ConflictSeverity) -> Conflict:
        return Conflict(
            id=uuid4(),
            case_id=self.case_id,
            claim_ids=[left.id, right.id],
            severity=severity,
            reason="Claims disagree about the North Bridge.",
        )

    def test_all_material_claims_agree_returns_act(self) -> None:
        bridge = self.evidence("North Bridge is safe.")
        detour = self.evidence("East Detour is clear.")
        eta = self.evidence("East Detour ETA is acceptable.")
        claims = [
            self.claim("North Bridge is safe.", bridge, AgentName.PERCEPTION),
            self.claim("East Detour is clear.", detour, AgentName.OPERATIONS),
            self.claim("East Detour ETA is acceptable.", eta, AgentName.VERIFIER),
        ]

        decision = evaluate_decision(
            self.case_id, claims, [bridge, detour, eta], risk_level=RiskLevel.HIGH, now=self.now
        )

        self.assertEqual(decision.decision, DecisionType.ACT)
        self.assertEqual(decision.conflicting_claim_ids, [])
        self.assertEqual(
            set(decision.supporting_evidence_ids),
            {bridge.id, detour.id, eta.id},
        )
        self.assertIsNone(decision.next_evidence_request)

    def test_recoverable_conflict_returns_ask_with_request(self) -> None:
        safe_evidence = self.evidence("North Bridge is safe.", confidence=0.82)
        unsafe_evidence = self.evidence("North Bridge is unsafe.", confidence=0.75)
        safe = self.claim("North Bridge is safe.", safe_evidence, confidence=0.82)
        unsafe = self.claim("North Bridge is unsafe.", unsafe_evidence, AgentName.OPERATIONS, 0.75)

        decision = evaluate_decision(
            self.case_id,
            [safe, unsafe],
            [safe_evidence, unsafe_evidence],
            [self.conflict(safe, unsafe, ConflictSeverity.MEDIUM)],
            RiskLevel.MEDIUM,
            now=self.now,
        )

        self.assertEqual(decision.decision, DecisionType.ASK)
        self.assertEqual(set(decision.conflicting_claim_ids), {safe.id, unsafe.id})
        self.assertTrue(decision.next_evidence_request)

    def test_critical_unresolved_conflict_returns_abstain(self) -> None:
        safe_evidence = self.evidence("North Bridge is safe.", confidence=0.95)
        unsafe_evidence = self.evidence("North Bridge is unsafe.", confidence=0.95)
        safe = self.claim("North Bridge is safe.", safe_evidence, confidence=0.95)
        unsafe = self.claim("North Bridge is unsafe.", unsafe_evidence, AgentName.OPERATIONS, 0.95)

        decision = evaluate_decision(
            self.case_id,
            [safe, unsafe],
            [safe_evidence, unsafe_evidence],
            [self.conflict(safe, unsafe, ConflictSeverity.HIGH)],
            RiskLevel.HIGH,
            now=self.now,
        )

        self.assertEqual(decision.decision, DecisionType.ABSTAIN)
        self.assertIsNone(decision.next_evidence_request)
        self.assertEqual(set(decision.conflicting_claim_ids), {safe.id, unsafe.id})

    def test_stale_claim_does_not_outweigh_fresh_claim(self) -> None:
        stale_evidence = self.evidence("North Bridge is unsafe.", age=timedelta(hours=2))
        fresh_evidence = self.evidence("North Bridge is safe.")
        stale_claim = self.claim("North Bridge is unsafe.", stale_evidence, confidence=0.99)
        fresh_claim = self.claim("North Bridge is safe.", fresh_evidence, AgentName.OPERATIONS, 0.8)
        conflict = self.conflict(stale_claim, fresh_claim, ConflictSeverity.HIGH)

        decision = evaluate_decision(
            self.case_id,
            [stale_claim, fresh_claim],
            [stale_evidence, fresh_evidence],
            [conflict],
            RiskLevel.HIGH,
            now=self.now,
        )

        self.assertEqual(decision.decision, DecisionType.ACT)
        self.assertEqual(decision.supporting_evidence_ids, [fresh_evidence.id])
        self.assertIn("stale", decision.reason.lower())
        self.assertEqual(decision.conflicting_claim_ids, [])

    def test_equal_confidence_conflict_returns_ask(self) -> None:
        left_evidence = self.evidence("North Bridge is safe.", confidence=0.8)
        right_evidence = self.evidence("North Bridge is unsafe.", confidence=0.8)
        left = self.claim("North Bridge is safe.", left_evidence, confidence=0.8)
        right = self.claim("North Bridge is unsafe.", right_evidence, AgentName.OPERATIONS, 0.8)

        decision = evaluate_decision(
            self.case_id,
            [left, right],
            [left_evidence, right_evidence],
            [self.conflict(left, right, ConflictSeverity.MEDIUM)],
            RiskLevel.MEDIUM,
            now=self.now,
        )

        self.assertEqual(decision.decision, DecisionType.ASK)
        self.assertIn("equal confidence", decision.reason.lower())

    def test_unavailable_llm_uses_deterministic_mock_claims(self) -> None:
        bridge = self.evidence("North Bridge is safe.", confidence=0.9)
        bridge = bridge.model_copy(update={"source_type": SourceType.SENSOR, "source_name": "bridge_camera"})
        detour = self.evidence("East Detour is clear.", confidence=0.9)
        perception, operations, _ = build_default_agents()
        drafts = perception.run([bridge]) + operations.run([detour])
        claims = [
            Claim(id=uuid4(), case_id=self.case_id, **draft.model_dump()) for draft in drafts
        ]

        decision = evaluate_decision(
            self.case_id, claims, [bridge, detour], risk_level=RiskLevel.MEDIUM, now=self.now
        )

        self.assertEqual(decision.decision, DecisionType.ACT)

    def test_thresholds_are_configurable(self) -> None:
        evidence = self.evidence("North Bridge is safe.", confidence=0.65)
        claim = self.claim("North Bridge is safe.", evidence, confidence=0.65)
        strict = DecisionThresholds(material_confidence=0.6, act_confidence=0.9)

        decision = evaluate_decision(
            self.case_id,
            [claim],
            [evidence],
            risk_level=RiskLevel.LOW,
            thresholds=strict,
            now=self.now,
        )

        self.assertEqual(decision.decision, DecisionType.ASK)


if __name__ == "__main__":
    unittest.main()
