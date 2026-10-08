# PARALLAX MVP Scope and Build Contract

## 1. Scope and scenario

The product demo answers one question:

> Should emergency vehicles be rerouted from the North Bridge to the East Detour?

The two allowed action IDs are:

- `REROUTE_EAST_DETOUR`
- `KEEP_NORTH_BRIDGE`

The scenario is fixed. The UI may display the scenario and accept new evidence, but it must not become a general workflow builder, multi-scenario planner, or chat application.

The first evaluation uses seeded or entered reports about bridge condition, detour clearance/ETA, and operational constraints. A later evidence submission demonstrates that fresh information causes a new evaluation and may change the gate result.

Out of scope: authentication, accounts, arbitrary agent configuration, background job infrastructure, file storage, file uploads, multi-scenario management, autonomous action execution, notifications, production deployment, and LLM-generated final decisions.

## 2. Minimal folder structure

    backend/
      app/
        main.py                 FastAPI app and startup
        api.py                  HTTP routes and response mapping
        db.py                   SQLite connection/session helpers
        models.py               SQLite/ORM entities
        schemas.py              Pydantic request and response models
        agents.py               Perception, Operations, Verifier adapters
        evidence_graph.py       NetworkX graph construction
        conflict_detector.py    Claim conflict detection
        decision_gate.py        Pure deterministic ACT/ASK/ABSTAIN rules
        evaluation.py           Evaluation orchestration and persistence
      tests/
        test_schemas.py
        test_conflicts.py
        test_decision_gate.py
        test_api.py

    frontend/
      src/
        main.tsx
        App.tsx
        api.ts
        components/
          GateBanner.tsx
          EvidencePanel.tsx
          AgentClaims.tsx
          ConflictPanel.tsx
          EvidenceGraph.tsx
          AddEvidenceForm.tsx

    pyproject.toml
    frontend/package.json

No separate services, message queues, worker processes, or shared package are needed for the MVP. The frontend uses the backend API directly.

## 3. Backend modules

### `main.py` and `api.py`

Create the FastAPI app, health route, CORS for the local Vite origin, and the decision/evidence/evaluation routes. Route handlers validate requests, call the evaluation service, and return the latest snapshot. They do not contain gate logic.

### `db.py` and `models.py`

Open one SQLite database, create the small set of tables on startup, and persist append-only evidence, claims, conflicts, agent runs, and evaluation results. A lightweight SQLAlchemy setup is acceptable; do not add a repository or migration framework unless the existing environment requires it.

### `schemas.py`

Define the Pydantic enums and request/response models listed below. Bounds and references are validated before data reaches the agents or gate.

### `agents.py`

Expose exactly three specialist roles:

- **Perception**: interprets physical/visual/sensor reports about bridge and roadway conditions.
- **Operations**: interprets route availability, ETA, capacity, and emergency logistics reports.
- **Verifier**: checks evidence coverage, freshness, and cross-agent consistency; it may issue structured verification claims but never chooses the final action.

Each role receives the current evidence set and returns validated structured claim drafts. The module owns the LLM adapter boundary. A deterministic fixture adapter must be available for tests and a reliable local demo when no API key is present.

### `evidence_graph.py`

Build a NetworkX directed graph for the current evaluation. Evidence and claims are nodes. Edges are `DERIVED_FROM`, `SUPPORTS`, or `CONTRADICTS`. The graph is for traceability and display; it must not decide the outcome.

### `conflict_detector.py`

Normalize claim fact keys and values, compare claims from the current evaluation, and persist explicit conflict records. A conflict is a disagreement about the same fact, not merely different wording or different specialist roles.

### `decision_gate.py`

A pure Python function consumes validated current claims, conflicts, required fact coverage, and agent-run status. It returns a `GateResult`. It has no LLM, database, network, or UI dependency. Exact rules are in `DECISION_RULES.md`.

### `evaluation.py`

For each evaluation version: load evidence, run all three roles, validate and persist claims, build the graph, detect conflicts, call the gate, and persist one immutable result. Existing evaluations remain available for the UI history; only the newest one is the active snapshot.

## 4. Frontend responsibilities

The single-page React UI contains:

1. Scenario/question header and the two possible actions.
2. Current gate banner showing `ACT`, `ASK`, or `ABSTAIN`, selected action when applicable, and reason codes.
3. Three specialist columns showing role, structured claims, confidence, stance, and linked evidence IDs.
4. Evidence list with source, timestamp/freshness, and content.
5. Conflict panel showing the two claims and the fact they disagree about.
6. Compact evidence graph visualization or a readable node/edge list if graph rendering becomes a time risk.
7. Form to add one fresh text evidence item and a button to re-evaluate.
8. Evaluation number/history indicator so the change after fresh evidence is obvious.

The frontend does not calculate confidence, detect conflicts, or choose an action. It renders API results and sends evidence/re-evaluation requests.

## 5. API contract

All paths are prefixed with `/api`. JSON timestamps are ISO-8601 UTC strings. The backend owns IDs and evaluation version numbers.

### `GET /api/health`

Returns `{ "status": "ok" }`.

### `POST /api/decisions`

Creates the fixed emergency bridge/route case and runs evaluation 1 synchronously.

Request: `CreateDecisionRequest`

    {
      "scenario_key": "emergency_bridge_route",
      "initial_evidence": [EvidenceCreate, ...]
    }

`scenario_key` is required and only the frozen value is accepted. The initial evidence list may be omitted for a demo fixture, but a real evaluation with no usable evidence must produce `ABSTAIN` rather than inventing facts.

Response: `DecisionSnapshot` with HTTP 201.

### `GET /api/decisions/{decision_id}`

Returns the latest `DecisionSnapshot`, including the scenario, latest gate result, current claims, current conflicts, graph nodes/edges, agent-run statuses, and evidence. Evaluation history may be included as compact summaries.

### `POST /api/decisions/{decision_id}/evidence`

Appends one immutable evidence item. This route stores evidence only and does not silently change the gate.

Request: `EvidenceCreate`

Response: `Evidence` with HTTP 201.

### `POST /api/decisions/{decision_id}/reevaluate`

Runs all three specialists against the decision's evidence, increments the evaluation number, rebuilds the current graph, detects conflicts, and applies the deterministic gate.

Request: empty JSON object `{}`.

Response: latest `DecisionSnapshot` with HTTP 200. A failed/invalid specialist output is recorded in `agent_runs`; it cannot bypass validation or cause an unsafe action.

### Error behavior

- `404`: decision ID does not exist.
- `422`: Pydantic validation failure, invalid timestamp, unsupported scenario, or malformed evidence.
- `409`: a re-evaluation is already in progress, if the implementation needs a guard.
- A model parsing failure is represented in the snapshot and causes the gate to fail closed according to `DECISION_RULES.md`; it is not a model-selected outcome.

## 6. Pydantic schemas

These are the required shapes; field names should remain stable between backend and frontend.

### Enums

- `AgentRole`: `PERCEPTION`, `OPERATIONS`, `VERIFIER`
- `EvidenceKind`: `REPORT`, `SENSOR`, `DISPATCH`
- `Stance`: `SUPPORTS`, `OPPOSES`, `NEUTRAL`
- `Criticality`: `NORMAL`, `SAFETY_CRITICAL`
- `GateOutcome`: `ACT`, `ASK`, `ABSTAIN`
- `ActionId`: `REROUTE_EAST_DETOUR`, `KEEP_NORTH_BRIDGE`
- `ConflictStatus`: `OPEN`, `RESOLVED_BY_NEW_EVIDENCE`

### `EvidenceCreate`

- `source: str` — non-empty source label
- `kind: EvidenceKind`
- `content: str` — non-empty text for the MVP
- `observed_at: datetime`
- `expires_at: datetime | None` — optional explicit expiry; otherwise the scenario freshness window applies

### `Evidence`

`EvidenceCreate` plus:

- `id: str`
- `decision_id: str`
- `created_at: datetime`
- `is_fresh: bool` — computed by the backend, never trusted from the client

### `ClaimDraft`

The only model output accepted from an agent:

- `agent_role: AgentRole`
- `target_action: ActionId | None`
- `fact_key: str` — normalized semantic fact, such as `east_detour_clear`
- `value: str` — normalized comparison value, such as `true`, `false`, or `unknown`
- `stance: Stance`
- `confidence: float` — constrained to `0.0..1.0`
- `criticality: Criticality`
- `evidence_ids: list[str]` — at least one reference to supplied evidence
- `claim_text: str` — concise human-readable explanation

The adapter may return JSON only. It may not return an outcome, action command, or free-form instruction to the gate.

### `Claim`

`ClaimDraft` plus `id`, `decision_id`, `evaluation_id`, and `created_at`.

### `Conflict`

- `id: str`
- `decision_id: str`
- `evaluation_id: str`
- `claim_a_id: str`
- `claim_b_id: str`
- `fact_key: str`
- `severity: Criticality`
- `reason: str`
- `status: ConflictStatus`

### `AgentRun`

- `id: str`
- `evaluation_id: str`
- `agent_role: AgentRole`
- `status: ` `SUCCEEDED` or `FAILED`
- `claim_ids: list[str]`
- `error: str | None`
- `created_at: datetime`

### `GateResult`

- `evaluation_id: str`
- `outcome: GateOutcome`
- `selected_action: ActionId | None`
- `score_by_action: dict[ActionId, float]`
- `reason_codes: list[str]`
- `evaluated_at: datetime`

Reason codes are stable machine-readable strings such as `MISSING_REQUIRED_FACT`, `OPEN_CRITICAL_CONFLICT`, `LOW_ACTION_MARGIN`, and `SUFFICIENT_CONSENSUS`.

### `DecisionSnapshot`

- `decision_id: str`
- `scenario_key: str`
- `question: str`
- `options: list[ActionId]`
- `evaluation_number: int`
- `evidence: list[Evidence]`
- `agent_runs: list[AgentRun]`
- `claims: list[Claim]`
- `conflicts: list[Conflict]`
- `graph: { nodes: [...], edges: [...] }`
- `gate: GateResult`
- `history: list[{ evaluation_id, evaluation_number, outcome, selected_action, evaluated_at }]`

## 7. SQLite entities

Use foreign keys and indexes on `decision_id` and `evaluation_id`. Evidence, claims, conflicts, and evaluation results are append-only for traceability.

### `decisions`

`id`, `scenario_key`, `question`, `created_at`, `updated_at`

### `evaluations`

`id`, `decision_id`, `number`, `started_at`, `finished_at`, `status`, `outcome`, `selected_action`, `reason_codes_json`, `score_by_action_json`

Unique constraint: `(decision_id, number)`.

### `evidence`

`id`, `decision_id`, `source`, `kind`, `content`, `observed_at`, `expires_at`, `created_at`

### `agent_runs`

`id`, `evaluation_id`, `decision_id`, `agent_role`, `status`, `error`, `created_at`

### `claims`

`id`, `decision_id`, `evaluation_id`, `agent_run_id`, `agent_role`, `target_action`, `fact_key`, `value`, `stance`, `confidence`, `criticality`, `claim_text`, `created_at`

### `claim_evidence`

`claim_id`, `evidence_id`; composite primary key. This is the many-to-many trace from a claim to its source evidence.

### `conflicts`

`id`, `decision_id`, `evaluation_id`, `claim_a_id`, `claim_b_id`, `fact_key`, `severity`, `reason`, `status`, `created_at`

A graph snapshot does not need its own table for the MVP; reconstruct it from current claims, claim/evidence links, and conflicts. If the frontend needs a cached snapshot, store one JSON field on `evaluations` without changing gate behavior.

## 8. Test plan

### Unit tests

- Pydantic rejects empty evidence, invalid role/action values, confidence outside `0..1`, missing claim evidence references, and invalid timestamps.
- Evidence freshness handles current, expired, and explicitly short-lived evidence using an injected clock.
- Each agent fixture produces only valid claim drafts and maps evidence IDs correctly.
- NetworkX graph contains one node per current evidence/claim and expected derived/support/contradict edges.
- Conflict detection catches opposite values for the same fact and ignores unrelated facts or same-value claims.
- Gate table tests cover:
  - sufficient fresh coverage, no conflict, clear margin -> `ACT`;
  - fresh coverage with unresolved critical disagreement -> `ASK`;
  - no evidence -> `ABSTAIN`;
  - missing required safety fact -> `ABSTAIN`;
  - failed specialist or invalid model output -> `ABSTAIN`;
  - tie/low margin -> `ASK`;
  - stale evidence not counted as support -> no unsafe `ACT`.

### Backend integration tests

- Create the fixed scenario, verify evaluation 1 and persisted rows.
- Fetch a snapshot and verify claims trace back to evidence.
- Add evidence without re-evaluation and confirm the gate is unchanged.
- Re-evaluate and confirm evaluation number increments, new claims/conflicts are scoped to it, and history remains.
- Verify malformed or unknown decision IDs return the documented errors.

### Frontend smoke checks

- App loads against a running FastAPI server.
- Gate, three specialist panels, evidence, and conflicts render from one snapshot.
- Add-evidence flow returns success without changing the gate until re-evaluate is clicked.
- Re-evaluate refreshes the snapshot and visibly updates evaluation number, claims, conflicts, and gate banner.
- Loading and API error states are visible.

### Demo acceptance test

Start with a disagreement that produces `ASK`, add a fresh report resolving the route condition, re-evaluate, and show the deterministic transition to `ACT` with the selected action and evidence path visible. Also show an insufficient/stale evidence case producing `ABSTAIN`.

## 9. Implementation order

1. Create the minimal backend/frontend scaffolds and local run commands.
2. Add SQLite connection, entities, Pydantic schemas, and fixed scenario constants.
3. Add `POST /decisions`, `GET /decisions/{id}`, evidence persistence, and health route.
4. Implement the agent interface with deterministic fixtures first; then add the optional LLM evidence-to-claims adapter behind the same interface.
5. Persist claims and agent runs; construct the NetworkX evidence graph.
6. Implement conflict detection and unit-test it with opposing claims.
7. Implement and table-test the pure deterministic Decision Gate.
8. Wire evaluation orchestration, re-evaluation, history, and the remaining API routes.
9. Build the small React view and fresh-evidence flow.
10. Run backend tests, frontend checks, and the complete demo smoke test; fix failures before adding anything else.
