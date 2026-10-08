from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseRecord(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scenario: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False, default="HIGH")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    evidence: Mapped[list[EvidenceRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    claims: Mapped[list[ClaimRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    conflicts: Mapped[list[ConflictRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    decisions: Mapped[list[DecisionRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    reevaluation_audits: Mapped[list[ReevaluationAuditRecord]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_case_timestamp", "case_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(String(5000), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    case: Mapped[CaseRecord] = relationship(back_populates="evidence")


class ClaimRecord(Base):
    __tablename__ = "claims"
    __table_args__ = (Index("ix_claims_case_timestamp", "case_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(30), nullable=False)
    claim: Mapped[str] = mapped_column(String(2000), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reasoning_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseRecord] = relationship(back_populates="claims")


class ConflictRecord(Base):
    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)

    case: Mapped[CaseRecord] = relationship(back_populates="conflicts")


class ReevaluationAuditRecord(Base):
    __tablename__ = "reevaluation_audits"
    __table_args__ = (Index("ix_reevaluation_audits_case_created", "case_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
    new_decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[CaseRecord] = relationship(back_populates="reevaluation_audits")


class DecisionRecord(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    conflicting_claim_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    next_evidence_request: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[CaseRecord] = relationship(back_populates="decisions")
