import json
import unittest
from datetime import datetime, timezone
from uuid import uuid4

import networkx as nx

from app.evidence_graph import (
    build_case_graph,
    graph_to_json,
    identify_disagreements,
)
from app.schemas import (
    AgentName,
    Claim,
    Decision,
    DecisionType,
    Evidence,
    RiskLevel,
    SourceType,
)


class EvidenceGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_id = uuid4()
        self.now = datetime.now(timezone.utc)
        self.camera_evidence = Evidence(
            id=uuid4(),
            case_id=self.case_id,
            source_type=SourceType.SENSOR,
            source_name="north_bridge_camera",
            content="Camera shows the bridge approach.",
            timestamp=self.now,
            confidence=0.9,
            metadata={},
        )
        self.operations_evidence = Evidence(
            id=uuid4(),
            case_id=self.case_id,
            source_type=SourceType.DISPATCH,
            source_name="route_operations",
            content="East Detour status report.",
            timestamp=self.now,
            confidence=0.8,
            metadata={},
        )
        self.unlinked_evidence = Evidence(
            id=uuid4(),
            case_id=self.case_id,
            source_type=SourceType.REPORT,
            source_name="unlinked_report",
            content="Not referenced by any claim.",
            timestamp=self.now,
            confidence=0.5,
            metadata={},
        )
        self.unsafe_claim = Claim(
            id=uuid4(),
            case_id=self.case_id,
            agent_name=AgentName.PERCEPTION,
            claim="North Bridge is unsafe.",
            confidence=0.9,
            evidence_ids=[self.camera_evidence.id],
            reasoning_summary="Camera evidence indicates unsafe conditions.",
            timestamp=self.now,
        )
        self.safe_claim = Claim(
            id=uuid4(),
            case_id=self.case_id,
            agent_name=AgentName.OPERATIONS,
            claim="North Bridge is safe.",
            confidence=0.8,
            evidence_ids=[self.operations_evidence.id],
            reasoning_summary="Operations reports the bridge remains open.",
            timestamp=self.now,
        )
        self.detour_claim = Claim(
            id=uuid4(),
            case_id=self.case_id,
            agent_name=AgentName.OPERATIONS,
            claim="East Detour is clear.",
            confidence=0.8,
            evidence_ids=[self.operations_evidence.id],
            reasoning_summary="Route report says the detour is available.",
            timestamp=self.now,
        )

    def test_bridge_graph_has_traceable_json_nodes_and_edges(self) -> None:
        claims = [self.unsafe_claim, self.safe_claim, self.detour_claim]
        decision = Decision(
            id=uuid4(),
            case_id=self.case_id,
            decision=DecisionType.ASK,
            reason="North Bridge safety claims disagree.",
            risk_level=RiskLevel.HIGH,
            conflicting_claim_ids=[self.unsafe_claim.id, self.safe_claim.id],
            supporting_evidence_ids=[self.camera_evidence.id, self.operations_evidence.id],
            created_at=self.now,
        )

        graph = build_case_graph(
            self.case_id,
            [self.camera_evidence, self.operations_evidence, self.unlinked_evidence],
            claims,
            decision=decision,
        )
        payload = graph_to_json(graph)

        self.assertIsInstance(graph, nx.DiGraph)
        json.dumps(payload)
        node_types = [node["type"] for node in payload["nodes"]]
        self.assertEqual(node_types.count("evidence"), 3)
        self.assertEqual(node_types.count("claim"), 3)
        self.assertEqual(node_types.count("agent"), 2)
        self.assertEqual(node_types.count("conflict"), 1)
        self.assertEqual(node_types.count("decision"), 1)

        relations = [edge["relation"] for edge in payload["edges"]]
        self.assertEqual(relations.count("evidence_supports_claim"), 3)
        self.assertEqual(relations.count("claim_produced_by_agent"), 3)
        self.assertEqual(relations.count("claim_participates_in_conflict"), 2)
        self.assertEqual(relations.count("conflict_informs_decision"), 1)

        evidence_ids = {str(self.camera_evidence.id), str(self.operations_evidence.id)}
        evidence_claim_edges = [
            edge for edge in payload["edges"] if edge["relation"] == "evidence_supports_claim"
        ]
        self.assertTrue(all(edge["source"].split(":", 1)[1] in evidence_ids for edge in evidence_claim_edges))
        self.assertFalse(
            any(edge["source"] == f"evidence:{self.unlinked_evidence.id}" for edge in payload["edges"])
        )

    def test_disagreement_detection_requires_same_explicit_subject(self) -> None:
        conflicts = identify_disagreements([self.unsafe_claim, self.safe_claim, self.detour_claim])

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(
            set(conflicts[0].claim_ids),
            {self.unsafe_claim.id, self.safe_claim.id},
        )
        self.assertIn("north bridge", conflicts[0].reason.lower())

        unrelated = self.detour_claim.model_copy(update={"claim": "East Detour is clear."})
        self.assertEqual(identify_disagreements([self.unsafe_claim, unrelated]), [])

    def test_graph_rejects_missing_evidence_relationship(self) -> None:
        bad_claim = self.unsafe_claim.model_copy(update={"evidence_ids": [uuid4()]})

        with self.assertRaises(ValueError):
            build_case_graph(self.case_id, [self.camera_evidence], [bad_claim])


if __name__ == "__main__":
    unittest.main()
