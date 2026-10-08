from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Protocol

from .schemas import AgentName, ClaimDraft, Evidence, SourceType


class ProviderUnavailable(RuntimeError):
    """Raised when a configured model provider cannot be used."""


class AgentOutputError(ValueError):
    """Raised when a provider returns a claim outside the shared contract."""


class ClaimProvider(Protocol):
    def interpret(
        self,
        agent_name: AgentName,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft] = (),
    ) -> Sequence[object]:
        """Interpret evidence into raw claim payloads, never a final decision."""


Interpreter = Callable[[AgentName, Sequence[Evidence], Sequence[ClaimDraft]], Sequence[object]]


class LLMClaimProvider:
    """Thin adapter boundary for a future structured-output LLM client.

    The callable is injected so this module has no vendor SDK dependency. It must
    return claim-shaped data; ACT/ASK/ABSTAIN is intentionally not part of its API.
    """

    def __init__(self, interpreter: Interpreter | None = None) -> None:
        self._interpreter = interpreter

    def interpret(
        self,
        agent_name: AgentName,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft] = (),
    ) -> Sequence[object]:
        if self._interpreter is None:
            raise ProviderUnavailable("No LLM interpreter is configured")
        return self._interpreter(agent_name, evidence, context_claims)


class FallbackClaimProvider:
    """Use the LLM adapter when available and deterministic samples otherwise."""

    def __init__(self, primary: ClaimProvider, fallback: ClaimProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def interpret(
        self,
        agent_name: AgentName,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft] = (),
    ) -> Sequence[object]:
        try:
            return self.primary.interpret(agent_name, evidence, context_claims)
        except ProviderUnavailable:
            return self.fallback.interpret(agent_name, evidence, context_claims)


class MockClaimProvider:
    """Small deterministic provider for tests and the hackathon demo."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def interpret(
        self,
        agent_name: AgentName,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft] = (),
    ) -> Sequence[ClaimDraft]:
        if agent_name is AgentName.PERCEPTION:
            return [self._evidence_claim(agent_name, item, "visual") for item in evidence if self._is_visual(item)]
        if agent_name is AgentName.OPERATIONS:
            return [
                self._evidence_claim(agent_name, item, "operational")
                for item in evidence
                if self._is_operational(item)
            ]
        return self._verify(evidence, context_claims)

    def _evidence_claim(self, agent_name: AgentName, item: Evidence, perspective: str) -> ClaimDraft:
        return ClaimDraft(
            agent_name=agent_name,
            claim=item.content,
            confidence=item.confidence,
            evidence_ids=[item.id],
            reasoning_summary=f"Deterministic demo interpretation of {perspective} evidence.",
            timestamp=self._clock(),
        )

    def _verify(
        self,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft],
    ) -> list[ClaimDraft]:
        if not evidence:
            return []

        evidence_ids = {item.id for item in evidence}
        linked_ids = [item.id for item in evidence]
        untraceable = [
            claim for claim in context_claims if any(ref not in evidence_ids for ref in claim.evidence_ids)
        ]
        contradictory = self._has_obvious_contradiction(context_claims)

        if untraceable:
            claim = "At least one specialist claim is not traceable to supplied evidence."
            confidence = 0.1
            reason = "Verifier found a claim with an unavailable evidence reference."
        elif contradictory:
            claim = "Specialist claims contain potentially conflicting statements."
            confidence = 0.4
            reason = "Verifier found opposing safety or route terms in the claim set."
        elif context_claims:
            claim = "Specialist claims are traceable to the supplied evidence."
            confidence = 0.95
            reason = "Verifier checked claim evidence references and found no obvious contradiction."
        else:
            claim = "No specialist claims were supplied for verification."
            confidence = 0.0
            reason = "Verifier cannot check consistency without specialist claims."

        return [
            ClaimDraft(
                agent_name=AgentName.VERIFIER,
                claim=claim,
                confidence=confidence,
                evidence_ids=linked_ids,
                reasoning_summary=reason,
                timestamp=self._clock(),
            )
        ]

    @staticmethod
    def _is_visual(item: Evidence) -> bool:
        haystack = f"{item.source_name} {item.content}".lower()
        return item.source_type is SourceType.SENSOR or any(
            marker in haystack for marker in ("camera", "visual", "photo", "image", "drone")
        )

    @staticmethod
    def _is_operational(item: Evidence) -> bool:
        haystack = f"{item.source_name} {item.content}".lower()
        return item.source_type is SourceType.DISPATCH or any(
            marker in haystack
            for marker in ("operation", "operator", "route", "map", "status", "traffic", "detour")
        )

    @staticmethod
    def _has_obvious_contradiction(claims: Sequence[ClaimDraft]) -> bool:
        text = " ".join(claim.claim.lower() for claim in claims)
        opposing_pairs = (("unsafe", "safe"), ("blocked", "clear"), ("closed", "open"))
        return any(left in text and right in text for left, right in opposing_pairs)


class SpecialistAgent:
    agent_name: AgentName

    def __init__(self, provider: ClaimProvider) -> None:
        self.provider = provider

    def _run(
        self,
        evidence: Sequence[Evidence],
        context_claims: Sequence[ClaimDraft] = (),
    ) -> list[ClaimDraft]:
        evidence_ids = {item.id for item in evidence}
        raw_claims = self.provider.interpret(self.agent_name, evidence, context_claims)
        claims: list[ClaimDraft] = []
        for raw_claim in raw_claims:
            try:
                claim = ClaimDraft.model_validate(raw_claim)
            except Exception as exc:
                raise AgentOutputError(f"{self.agent_name.value} returned an invalid claim") from exc
            if claim.agent_name is not self.agent_name:
                raise AgentOutputError(
                    f"Expected {self.agent_name.value} claim, got {claim.agent_name.value}"
                )
            if any(evidence_id not in evidence_ids for evidence_id in claim.evidence_ids):
                raise AgentOutputError("Agent claim references evidence outside the supplied set")
            claims.append(claim)
        return claims


class PerceptionAgent(SpecialistAgent):
    agent_name = AgentName.PERCEPTION

    def run(self, evidence: Sequence[Evidence]) -> list[ClaimDraft]:
        return self._run(evidence)


class OperationsAgent(SpecialistAgent):
    agent_name = AgentName.OPERATIONS

    def run(self, evidence: Sequence[Evidence]) -> list[ClaimDraft]:
        return self._run(evidence)


class VerifierAgent(SpecialistAgent):
    agent_name = AgentName.VERIFIER

    def run(
        self,
        evidence: Sequence[Evidence],
        claims: Sequence[ClaimDraft],
    ) -> list[ClaimDraft]:
        return self._run(evidence, claims)


def build_default_agents(
    llm_provider: ClaimProvider | None = None,
) -> tuple[PerceptionAgent, OperationsAgent, VerifierAgent]:
    provider: ClaimProvider = FallbackClaimProvider(
        primary=llm_provider or LLMClaimProvider(),
        fallback=MockClaimProvider(),
    )
    return PerceptionAgent(provider), OperationsAgent(provider), VerifierAgent(provider)
