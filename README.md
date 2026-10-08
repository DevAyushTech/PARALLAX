# PARALLAX

PARALLAX is a disagreement-aware multi-agent decision-control MVP for one emergency bridge/route scenario. Perception, Operations, and Verifier interpret evidence into structured claims. A deterministic Decision Gate returns `ACT`, `ASK`, or `ABSTAIN`; the LLM/provider boundary never selects the final outcome.

## MVP capabilities

- structured evidence, claims, conflicts, decisions, and audit records
- NetworkX evidence trace graph
- deterministic freshness/confidence/conflict policy
- fresh evidence followed by explicit re-evaluation
- FastAPI + SQLAlchemy + SQLite backend
- React + Vite frontend
- deterministic mock fallback when an LLM provider is unavailable

The running frontend/backend contract, JSON examples, CORS rules, error shape, and loading states are documented in [`API_CONTRACT.md`](API_CONTRACT.md). `MVP_SCOPE.md` and `DECISION_RULES.md` are the original planning artifacts, not the implemented API/policy; the active deterministic policy is in `backend/app/decision_gate.py`.

## Prerequisites

- Python 3.11+ (Python 3.14 is also supported in the current hackathon environment)
- Node.js 20.19+ or 22.12+ recommended (tested with Node.js 24)
- npm

## Run from a clean checkout

Run each terminal command from the repository root.

### 1. Install backend dependencies

Use a virtual environment when the Python installation provides `venv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

If `venv` reports that `ensurepip` is unavailable on Debian/Ubuntu, install the matching Python venv package (for example `sudo apt install python3-venv`) or ask the environment owner to do so, then retry. Do not use a system-package override or commit installed packages.

Copy the secret-free backend defaults once; existing environment variables override values from `.env`:

```bash
cp -n .env.example .env
```

### 2. Start the backend

The database is created automatically at `./parallax.db` on startup. Existing data is preserved. Always run from the repository root so `.env` and the relative database path resolve correctly. Use the activated virtual environment from step 1 in this terminal.

```bash
PARALLAX_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
  PYTHONPATH=backend python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify startup in another terminal:

```bash
curl -fsS http://127.0.0.1:8000/api/health
# {"status":"ok"}
```

### 3. Start the frontend

In a second terminal, from the repository root:

```bash
cp -n frontend/.env.example frontend/.env
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>. The live API base URL is `http://localhost:8000`; the frontend `.env` file is local-only and ignored by Git.

## Deterministic clean-start demo

The commands below exercise the real backend flow without hardcoding a final decision. The short five-second freshness window keeps the conflict-to-re-evaluation demo quick; it is a demo configuration, not a production setting.

1. Stop any backend on port 8000, then start it with this instead of the normal command. A separate ignored `demo.db` keeps existing `parallax.db` data untouched; no pre-seeded rows are required:

```bash
rm -f demo.db
PARALLAX_DATABASE_URL=sqlite:///./demo.db \
PARALLAX_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
PARALLAX_DECISION_GATE__FRESHNESS_SECONDS=5 \
  PYTHONPATH=backend python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. In another terminal, create the case and three initial evidence items. The status-feed observation is only two seconds old, so it is still fresh for the first evaluation:

```bash
set -e
API=http://127.0.0.1:8000/api
NOW=$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')
OLD=$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat())')
CASE_JSON=$(curl -fsS -X POST "$API/cases" -H 'content-type: application/json' \
  -d '{"title":"Emergency Bridge B assessment","scenario":"emergency_bridge_route","risk_level":"MEDIUM"}')
CASE_ID=$(printf '%s' "$CASE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

curl -fsS -X POST "$API/cases/$CASE_ID/evidence" -H 'content-type: application/json' \
  -d "{\"source_type\":\"SENSOR\",\"source_name\":\"camera\",\"content\":\"Bridge B is blocked\",\"timestamp\":\"$NOW\",\"confidence\":0.92,\"metadata\":{}}" >/dev/null
curl -fsS -X POST "$API/cases/$CASE_ID/evidence" -H 'content-type: application/json' \
  -d "{\"source_type\":\"DISPATCH\",\"source_name\":\"status_feed\",\"content\":\"Bridge B is open\",\"timestamp\":\"$OLD\",\"confidence\":0.74,\"metadata\":{}}" >/dev/null
curl -fsS -X POST "$API/cases/$CASE_ID/evidence" -H 'content-type: application/json' \
  -d "{\"source_type\":\"REPORT\",\"source_name\":\"field_report\",\"content\":\"Access uncertain\",\"timestamp\":\"$NOW\",\"confidence\":0.61,\"metadata\":{}}" >/dev/null

INITIAL=$(curl -fsS -X POST "$API/cases/$CASE_ID/analyze")
printf '%s\n' "$INITIAL" | python3 -c 'import json,sys; print("initial decision:", json.load(sys.stdin)["decision"]["decision"])'
```

The first computed state is conflict-bearing and should be `ABSTAIN` under the default high-confidence conflict rule (a recoverable policy/configuration may yield `ASK`). Inspect `conflicts`, `decision.reason`, and `decision.conflicting_claim_ids`; do not substitute a UI decision.

3. Let the initial observations age out, then submit fresh corroborating evidence and re-evaluate. The audit response contains the previous decision, new evidence, new decision, and reason for change:

```bash
sleep 6
FRESH=$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')
curl -fsS -X POST "$API/cases/$CASE_ID/reevaluate" -H 'content-type: application/json' \
  -d "{\"source_type\":\"DISPATCH\",\"source_name\":\"current_road_crew\",\"content\":\"Bridge B is blocked\",\"timestamp\":\"$FRESH\",\"confidence\":0.97,\"metadata\":{\"fresh\":true}}" \
  | python3 -c 'import json,sys; result=json.load(sys.stdin); print("updated decision:", result["decision"]["decision"]); print("audit:", json.dumps(result["audit"], indent=2))'
```

The exact result is calculated by the backend. With this clean-start fixture, the fresh evidence is the only current observation and the conflict is removed; the gate returns `ACT`. No real-world action is executed. Restart the normal backend afterwards to restore the default 15-minute freshness window.

If the first analysis is delayed beyond five seconds, those observations may already be stale. Recreate the case and run the initial block promptly; do not force an outcome or change observation timestamps to conceal staleness.

## Tests and checks

Backend tests:

```bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
```

Frontend production build:

```bash
npm --prefix frontend run build
```

The API exposes interactive documentation at <http://127.0.0.1:8000/docs> and the machine-readable contract at <http://127.0.0.1:8000/openapi.json>.

## Repository hygiene

- `.env.example` files contain placeholders and no credentials.
- `.env`, SQLite databases, Python caches, virtual environments, `node_modules`, and frontend build output are ignored.
- No API key is required for the deterministic MVP demo. Never commit provider credentials.
- The frontend currently includes a visual mock shell; backend integration uses the endpoints in `API_CONTRACT.md`.
