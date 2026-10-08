import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.agents import (
    AgentOutputError,
    LLMClaimProvider,
    MockClaimProvider,
    PerceptionAgent,
    VerifierAgent,
    build_default_agents,
)
from app.schemas import AgentName, ClaimDraft, Evidence, SourceType


class SpecialistAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime.now(timezone.utc)
        self.evidence = [
            Evidence(
                id=uuid4(),
                case_id=uuid4(),
                source_type=SourceType.SENSOR,
                source_name="camera_north_bridge",
                content="Camera shows water over the bridge approach.",
                timestamp=now,
                confidence=0.9,
                metadata={"frame": 12},
            ),
            Evidence(
                id=uuid4(),
                case_id=uuid4(),
                source_type=SourceType.DISPATCH,
                source_name="route_operations",
                content="East Detour is open for emergency traffic.",
                timestamp=now,
                confidence=0.8,
                metadata={"channel": "radio"},
            ),
        ]

    def test_each_agent_returns_the_shared_claim_contract(self) -> None:
        perception, operations, verifier = build_default_agents()
        perception_claims = perception.run(self.evidence)
        operations_claims = operations.run(self.evidence)
        verifier_claims = verifier.run(self.evidence, perception_claims + operations_claims)

        claims = perception_claims + operations_claims + verifier_claims
        self.assertEqual(len(claims), 3)
        for claim in claims:
            self.assertIsInstance(claim, ClaimDraft)
            self.assertIn(
                claim.agent_name,
                {AgentName.PERCEPTION, AgentName.OPERATIONS, AgentName.VERIFIER},
            )
            self.assertGreaterEqual(claim.confidence, 0.0)
            self.assertLessEqual(claim.confidence, 1.0)
            self.assertTrue(claim.evidence_ids)
            self.assertTrue(claim.claim)
            self.assertTrue(claim.reasoning_summary)
            self.assertIsInstance(claim.timestamp, datetime)
            self.assertFalse(hasattr(claim, "decision"))

        self.assertEqual(perception_claims[0].agent_name, AgentName.PERCEPTION)
        self.assertEqual(operations_claims[0].agent_name, AgentName.OPERATIONS)
        self.assertEqual(verifier_claims[0].agent_name, AgentName.VERIFIER)

    def test_default_provider_falls_back_without_an_llm(self) -> None:
        perception, operations, verifier = build_default_agents()

        claims = perception.run(self.evidence)
        claims += operations.run(self.evidence)
        claims += verifier.run(self.evidence, claims)

        self.assertEqual(len(claims), 3)

    def test_verifier_reports_obvious_claim_disagreement(self) -> None:
        provider = MockClaimProvider()
        verifier = VerifierAgent(provider)
        claims = [
            ClaimDraft(
                agent_name=AgentName.PERCEPTION,
                claim="The bridge is unsafe.",
                confidence=0.9,
                evidence_ids=[self.evidence[0].id],
                reasoning_summary="Camera evidence.",
                timestamp=self.evidence[0].timestamp,
            ),
            ClaimDraft(
                agent_name=AgentName.OPERATIONS,
                claim="The bridge is safe.",
                confidence=0.8,
                evidence_ids=[self.evidence[0].id],
                reasoning_summary="Operations report.",
                timestamp=self.evidence[0].timestamp,
            ),
        ]

        result = verifier.run(self.evidence, claims)

        self.assertEqual(len(result), 1)
        self.assertIn("conflicting", result[0].claim)
        self.assertEqual(result[0].agent_name, AgentName.VERIFIER)

    def test_llm_adapter_accepts_structured_claim_callback(self) -> None:
        now = datetime.now(timezone.utc)

        def interpreter(agent_name, evidence, context_claims):
            return [
                {
                    "agent_name": agent_name.value,
                    "claim": "Structured provider output.",
                    "confidence": 0.7,
                    "evidence_ids": [str(evidence[0].id)],
                    "reasoning_summary": "Returned by injected provider.",
                    "timestamp": now.isoformat(),
                }
            ]

        agent = PerceptionAgent(LLMClaimProvider(interpreter))
        claims = agent.run(self.evidence)

        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].agent_name, AgentName.PERCEPTION)

    def test_agent_rejects_provider_claim_for_wrong_role(self) -> None:
        class WrongRoleProvider:
            def interpret(self, agent_name, evidence, context_claims=()):
                return [
                    {
                        "agent_name": AgentName.OPERATIONS.value,
                        "claim": "Wrong role.",
                        "confidence": 0.5,
                        "evidence_ids": [str(evidence[0].id)],
                        "reasoning_summary": "Invalid provider output.",
                        "timestamp": evidence[0].timestamp.isoformat(),
                    }
                ]

        with self.assertRaises(AgentOutputError):
            PerceptionAgent(WrongRoleProvider()).run(self.evidence)


if __name__ == "__main__":
    unittest.main()
