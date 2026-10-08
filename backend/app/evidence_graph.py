from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from itertools import combinations
import re
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import networkx as nx

from .schemas import (
    Claim,
    Conflict,
    ConflictSeverity,
    Decision,
    Evidence,
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    GraphNodeType,
)

_COPULA_PATTERN = re.compile(r"^(?P<subject>.+?)\s+(?:is|are|was|were|remains)\s+(?P<value>.+)$")


def extract_claim_subject(claim_text: str) -> tuple[str, str] | None:
    """Extract only an explicitly stated ``subject: value`` or ``subject is value``.

    Claims without one of these unambiguous forms are not compared. This keeps
    graph construction from inventing semantic relationships from free text.
    """

    text = " ".join(claim_text.strip().lower().split()).rstrip(".")
    if ":" in text:
        subject, value = text.split(":", 1)
    else:
        match = _COPULA_PATTERN.match(text)
        if match is None:
            return None
        subject, value = match.group("subject"), match.group("value")

    subject = _normalize_phrase(subject)
    value = _normalize_phrase(value)
    if not subject or not value:
        return None
    return subject, value


def identify_disagreements(claims: Sequence[Claim]) -> list[Conflict]:
    """Return conflicts only for claims with the same explicit subject and values that differ."""

    grouped: dict[tuple[UUID, str], list[tuple[Claim, str]]] = defaultdict(list)
    for claim in claims:
        parsed = extract_claim_subject(claim.claim)
        if parsed is None:
            continue
        subject, value = parsed
        grouped[(claim.case_id, subject)].append((claim, value))

    conflicts: list[Conflict] = []
    for (_, subject), subject_claims in grouped.items():
        for (left, left_value), (right, right_value) in combinations(subject_claims, 2):
            if left_value == right_value:
                continue
            severity = (
                ConflictSeverity.HIGH
                if max(left.confidence, right.confidence) >= 0.8
                else ConflictSeverity.MEDIUM
            )
            conflicts.append(
                Conflict(
                    id=uuid5(
                        NAMESPACE_URL,
                        "parallax:conflict:" + ":".join(
                            [str(left.case_id), *sorted((str(left.id), str(right.id)))]
                        ),
                    ),
                    case_id=left.case_id,
                    claim_ids=[left.id, right.id],
                    severity=severity,
                    reason=(
                        f"Claims disagree on subject '{subject}': "
                        f"'{left_value}' versus '{right_value}'."
                    ),
                )
            )
    return conflicts


def build_case_graph(
    case_id: UUID | str,
    evidence: Sequence[Evidence],
    claims: Sequence[Claim],
    conflicts: Sequence[Conflict] | None = None,
    decision: Decision | None = None,
) -> nx.DiGraph:
    """Build a directed traceability graph for one case.

    Relationships are created only from IDs present in the supplied records.
    Missing references are rejected rather than silently connected to another node.
    When conflicts are omitted, they are derived by ``identify_disagreements``.
    """

    _ensure_case_ids(case_id, evidence, claims, conflicts or (), decision)
    case_id_text = str(case_id)
    evidence_by_id = {item.id: item for item in evidence}
    claims_by_id = {item.id: item for item in claims}
    graph = nx.DiGraph(case_id=case_id_text)

    for item in evidence:
        graph.add_node(
            _node_id(GraphNodeType.EVIDENCE, item.id),
            node_type=GraphNodeType.EVIDENCE,
            label=item.source_name,
            data={
                "id": str(item.id),
                "source_type": item.source_type.value,
                "source_name": item.source_name,
                "content": item.content,
                "timestamp": item.timestamp.isoformat(),
                "confidence": item.confidence,
            },
        )

    for claim in claims:
        graph.add_node(
            _node_id(GraphNodeType.CLAIM, claim.id),
            node_type=GraphNodeType.CLAIM,
            label=claim.claim,
            data={
                "id": str(claim.id),
                "agent_name": claim.agent_name.value,
                "claim": claim.claim,
                "confidence": claim.confidence,
                "evidence_ids": [str(item) for item in claim.evidence_ids],
                "reasoning_summary": claim.reasoning_summary,
                "timestamp": claim.timestamp.isoformat(),
            },
        )
        agent_id = _node_id(GraphNodeType.AGENT, claim.agent_name.value)
        graph.add_node(
            agent_id,
            node_type=GraphNodeType.AGENT,
            label=claim.agent_name.value,
            data={"agent_name": claim.agent_name.value},
        )
        graph.add_edge(
            _node_id(GraphNodeType.CLAIM, claim.id),
            agent_id,
            relation="claim_produced_by_agent",
        )
        for evidence_id in claim.evidence_ids:
            if evidence_id not in evidence_by_id:
                raise ValueError(f"Claim {claim.id} references missing evidence {evidence_id}")
            graph.add_edge(
                _node_id(GraphNodeType.EVIDENCE, evidence_id),
                _node_id(GraphNodeType.CLAIM, claim.id),
                relation="evidence_supports_claim",
            )

    selected_conflicts = list(conflicts) if conflicts is not None else identify_disagreements(claims)
    for conflict in selected_conflicts:
        graph.add_node(
            _node_id(GraphNodeType.CONFLICT, conflict.id),
            node_type=GraphNodeType.CONFLICT,
            label=conflict.reason,
            data={
                "id": str(conflict.id),
                "claim_ids": [str(item) for item in conflict.claim_ids],
                "severity": conflict.severity.value,
                "reason": conflict.reason,
            },
        )
        for claim_id in conflict.claim_ids:
            if claim_id not in claims_by_id:
                raise ValueError(f"Conflict {conflict.id} references missing claim {claim_id}")
            graph.add_edge(
                _node_id(GraphNodeType.CLAIM, claim_id),
                _node_id(GraphNodeType.CONFLICT, conflict.id),
                relation="claim_participates_in_conflict",
            )

    if decision is not None:
        decision_id = _node_id(GraphNodeType.DECISION, decision.id)
        graph.add_node(
            decision_id,
            node_type=GraphNodeType.DECISION,
            label=decision.decision.value,
            data={
                "id": str(decision.id),
                "decision": decision.decision.value,
                "reason": decision.reason,
                "risk_level": decision.risk_level.value,
                "conflicting_claim_ids": [str(item) for item in decision.conflicting_claim_ids],
                "supporting_evidence_ids": [str(item) for item in decision.supporting_evidence_ids],
                "next_evidence_request": decision.next_evidence_request,
                "created_at": decision.created_at.isoformat(),
            },
        )
        decision_claim_ids = set(decision.conflicting_claim_ids)
        for conflict in selected_conflicts:
            if decision_claim_ids.intersection(conflict.claim_ids):
                graph.add_edge(
                    _node_id(GraphNodeType.CONFLICT, conflict.id),
                    decision_id,
                    relation="conflict_informs_decision",
                )

    return graph


def graph_to_json(graph: nx.DiGraph) -> dict[str, list[dict[str, Any]]]:
    """Serialize a graph into stable frontend-friendly nodes and edges."""

    nodes = [
        GraphNode(
            id=node_id,
            type=attributes["node_type"],
            label=attributes["label"],
            data=attributes.get("data", {}),
        )
        for node_id, attributes in sorted(graph.nodes(data=True), key=lambda item: item[0])
    ]
    edges = [
        GraphEdge(source=source, target=target, relation=attributes["relation"])
        for source, target, attributes in sorted(
            graph.edges(data=True), key=lambda item: (item[0], item[1], item[2]["relation"])
        )
    ]
    return EvidenceGraph(nodes=nodes, edges=edges).model_dump(mode="json")


def build_case_graph_json(
    case_id: UUID | str,
    evidence: Sequence[Evidence],
    claims: Sequence[Claim],
    conflicts: Sequence[Conflict] | None = None,
    decision: Decision | None = None,
) -> dict[str, list[dict[str, Any]]]:
    return graph_to_json(build_case_graph(case_id, evidence, claims, conflicts, decision))


def _node_id(node_type: GraphNodeType, value: UUID | str) -> str:
    return f"{node_type.value}:{value}"


def _normalize_phrase(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _ensure_case_ids(
    case_id: UUID | str,
    evidence: Sequence[Evidence],
    claims: Sequence[Claim],
    conflicts: Sequence[Conflict],
    decision: Decision | None,
) -> None:
    records = [*evidence, *claims, *conflicts]
    if decision is not None:
        records.append(decision)
    requested_case_id = str(case_id)
    if any(str(record.case_id) != requested_case_id for record in records):
        raise ValueError("All graph records must belong to the requested case")
