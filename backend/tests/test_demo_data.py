import unittest

from app.demo_data import evaluate_demo, demo_scenarios
from app.schemas import DecisionType


class DemoDatasetTests(unittest.TestCase):
    def test_bridge_conflict_reduces_after_fresh_re_evaluation(self) -> None:
        scenario = demo_scenarios()["bridge_conflict"]

        initial = evaluate_demo(scenario, at=scenario.initial_at)
        updated = evaluate_demo(
            scenario,
            scenario.initial_evidence + scenario.followup_evidence,
            at=scenario.reevaluation_at,
        )

        self.assertGreaterEqual(len(initial.conflicts), 1)
        self.assertIn(initial.decision.decision, {DecisionType.ASK, DecisionType.ABSTAIN})
        self.assertLess(len(updated.conflicts), len(initial.conflicts))
        self.assertEqual(updated.decision.decision, DecisionType.ACT)

    def test_fully_agreeing_fixture_uses_the_gate_for_act(self) -> None:
        scenario = demo_scenarios()["fully_agree_act"]

        evaluation = evaluate_demo(scenario)

        self.assertEqual(evaluation.conflicts, [])
        self.assertEqual(evaluation.decision.decision, DecisionType.ACT)

    def test_critical_fixture_uses_the_gate_for_abstain(self) -> None:
        scenario = demo_scenarios()["critical_abstain"]

        evaluation = evaluate_demo(scenario)

        self.assertTrue(evaluation.conflicts)
        self.assertEqual(evaluation.decision.decision, DecisionType.ABSTAIN)

    def test_mock_provider_fixture_works_without_llm(self) -> None:
        scenario = demo_scenarios()["mock_provider_fallback"]

        evaluation = evaluate_demo(scenario)

        self.assertGreaterEqual(len(evaluation.claims), 2)
        self.assertEqual(evaluation.decision.decision, DecisionType.ACT)

    def test_fixture_ids_and_evidence_are_repeatable(self) -> None:
        first = demo_scenarios()
        second = demo_scenarios()

        for key in first:
            self.assertEqual(first[key].case.id, second[key].case.id)
            self.assertEqual(first[key].initial_evidence, second[key].initial_evidence)
            self.assertEqual(first[key].followup_evidence, second[key].followup_evidence)


if __name__ == "__main__":
    unittest.main()
