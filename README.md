# PARALLAX

PARALLAX is a disagreement-aware multi-agent decision-control MVP. It evaluates one emergency bridge/route scenario through three specialist agents, makes disagreements visible, and lets a deterministic Decision Gate return `ACT`, `ASK`, or `ABSTAIN`.

## Frozen MVP

- One emergency bridge/route decision scenario
- Three specialists: Perception, Operations, Verifier
- Structured claims linked to evidence
- NetworkX evidence/claim graph
- Deterministic conflict detection and Decision Gate
- Fresh evidence followed by explicit re-evaluation
- React + Vite frontend
- FastAPI + Python backend
- SQLite persistence
- Pydantic validation
- LLM use limited to evidence interpretation and structured claim extraction

There is intentionally no application code in this planning step. The implementation contract is in `MVP_SCOPE.md`; gate behavior is in `DECISION_RULES.md`; the intended demo flow is in `DEMO_SCRIPT.md`.

## Planned minimal structure

    backend/
      app/
        main.py
        api.py
        db.py
        models.py
        schemas.py
        agents.py
        evidence_graph.py
        conflict_detector.py
        decision_gate.py
        evaluation.py
      tests/
    frontend/
      src/
        api.ts
        App.tsx
        components/
        main.tsx
    pyproject.toml
    frontend/package.json

The tree is a target for implementation, not a requirement to create every file if a smaller equivalent is sufficient.
