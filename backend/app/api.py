from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .evaluation import AnalysisBundle, analyze_case, load_current_analysis
from .evidence_graph import build_case_graph_json
from .models import CaseRecord, EvidenceRecord
from .schemas import (
    AnalysisResponse,
    CaseCreate,
    CaseDetail,
    CaseResponse,
    Decision,
    Evidence,
    EvidenceCreate,
    EvidenceGraph,
)

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
@router.post("/decisions", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseResponse:
    case = CaseRecord(
        title=payload.title,
        scenario=payload.scenario,
        status=payload.status.value,
        risk_level=payload.risk_level.value,
    )
    db.add(case)
    db.flush()

    for item in payload.initial_evidence:
        db.add(_evidence_record(case.id, item))

    db.commit()
    return _case_response(db, case.id)


@router.get("/cases/{case_id}", response_model=CaseDetail)
@router.get("/decisions/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseDetail:
    return _case_detail(db, case_id)


@router.post(
    "/cases/{case_id}/evidence",
    response_model=Evidence,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/decisions/{case_id}/evidence",
    response_model=Evidence,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    case_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)
) -> Evidence:
    _get_case_or_404(db, case_id)
    evidence = _evidence_record(case_id, payload)
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return _evidence_response(evidence)


@router.get("/cases/{case_id}/evidence", response_model=list[Evidence])
@router.get("/decisions/{case_id}/evidence", response_model=list[Evidence])
def list_evidence(case_id: str, db: Session = Depends(get_db)) -> list[Evidence]:
    _get_case_or_404(db, case_id)
    statement = (
        select(EvidenceRecord)
        .where(EvidenceRecord.case_id == case_id)
        .order_by(EvidenceRecord.timestamp.asc())
    )
    return [_evidence_response(item) for item in db.scalars(statement).all()]


@router.post("/cases/{case_id}/analyze", response_model=AnalysisResponse)
def analyze(case_id: str, db: Session = Depends(get_db)) -> AnalysisResponse:
    case = _get_case_or_404(db, case_id)
    return _analysis_response(analyze_case(db, case))


@router.get("/cases/{case_id}/graph", response_model=EvidenceGraph)
def get_graph(case_id: str, db: Session = Depends(get_db)) -> EvidenceGraph:
    case = _get_case_or_404(db, case_id)
    evidence, claims, conflicts, decision = load_current_analysis(db, case.id)
    return EvidenceGraph.model_validate(
        build_case_graph_json(case.id, evidence, claims, conflicts, decision)
    )


@router.get("/cases/{case_id}/decision", response_model=Decision)
def get_decision(case_id: str, db: Session = Depends(get_db)) -> Decision:
    _get_case_or_404(db, case_id)
    _, _, _, decision = load_current_analysis(db, case_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not available")
    return decision


@router.post("/cases/{case_id}/reevaluate", response_model=AnalysisResponse)
def reevaluate(
    case_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)
) -> AnalysisResponse:
    case = _get_case_or_404(db, case_id)
    db.add(_evidence_record(case.id, payload))
    db.commit()
    return _analysis_response(analyze_case(db, case))


def _get_case_or_404(db: Session, case_id: str) -> CaseRecord:
    case = db.get(CaseRecord, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def _evidence_record(case_id: str, payload: EvidenceCreate) -> EvidenceRecord:
    return EvidenceRecord(
        case_id=case_id,
        source_type=payload.source_type.value,
        source_name=payload.source_name,
        content=payload.content,
        timestamp=payload.timestamp,
        confidence=payload.confidence,
        metadata_json=payload.metadata,
    )


def _evidence_response(evidence: EvidenceRecord) -> Evidence:
    return Evidence(
        id=evidence.id,
        case_id=evidence.case_id,
        source_type=evidence.source_type,
        source_name=evidence.source_name,
        content=evidence.content,
        timestamp=evidence.timestamp,
        confidence=evidence.confidence,
        metadata=evidence.metadata_json or {},
    )


def _case_response(db: Session, case_id: str) -> CaseResponse:
    case = _get_case_or_404(db, case_id)
    evidence, _, _, _ = load_current_analysis(db, case.id)
    return CaseResponse(
        id=case.id,
        title=case.title,
        scenario=case.scenario,
        status=case.status,
        risk_level=case.risk_level,
        created_at=case.created_at,
        evidence=evidence,
    )


def _case_detail(db: Session, case_id: str) -> CaseDetail:
    case = _get_case_or_404(db, case_id)
    evidence, claims, conflicts, decision = load_current_analysis(db, case.id)
    return CaseDetail(
        id=case.id,
        title=case.title,
        scenario=case.scenario,
        status=case.status,
        risk_level=case.risk_level,
        created_at=case.created_at,
        evidence=evidence,
        claims=claims,
        conflicts=conflicts,
        decision=decision,
    )


def _analysis_response(bundle: AnalysisBundle) -> AnalysisResponse:
    return AnalysisResponse(
        case_id=bundle.decision.case_id,
        claims=bundle.claims,
        conflicts=bundle.conflicts,
        decision=bundle.decision,
        graph=bundle.graph,
    )
