# PARALLAX Hackathon Demo Script

## Scenario

**Question:** Should emergency vehicles be rerouted from the North Bridge to the East Detour?

**Actions shown in the UI:**

- `REROUTE_EAST_DETOUR`
- `KEEP_NORTH_BRIDGE`

## Demo flow

### 1. Start with disagreement

Create the fixed scenario with three current evidence items:

- Perception source: water is rising and the North Bridge has visible structural damage.
- Operations source: the East Detour is reported blocked by debris.
- Verifier source: the available route and safety facts are not yet mutually confirmed.

The first evaluation runs all three specialists. The UI should show:

- claims grouped under Perception, Operations, and Verifier;
- evidence-to-claim links in the graph;
- an open conflict or unresolved safety fact;
- gate result `ASK`, with a reason such as `OPEN_CRITICAL_CONFLICT`.

The key message: PARALLAX exposes disagreement instead of averaging it into a hidden decision.

### 2. Add fresh evidence

Submit one new evidence item through the UI:

- Source: `road_crew`
- Kind: `REPORT`
- Content: the East Detour has been cleared and is usable for emergency vehicles; ETA is within the emergency limit.
- Observed at: now

The evidence endpoint should return the new item while the visible gate remains unchanged. This demonstrates that storing evidence and making a decision are separate actions.

### 3. Re-evaluate

Click **Re-evaluate**. The backend creates evaluation 2, runs all three specialists again, rebuilds the graph, checks conflicts, and applies the rules without asking the LLM for a decision.

The UI should now show:

- evaluation number `2`;
- the fresh report linked to new Operations/Verifier claims;
- the previous evaluation available in compact history;
- resolved or superseded disagreement visible rather than deleted;
- gate result `ACT` with selected action `REROUTE_EAST_DETOUR` when all required facts are covered and score thresholds pass.

The key message: fresh evidence changes the recommendation only after explicit re-evaluation.

### 4. Show fail-closed behavior

Use an insufficient or expired evidence set, or remove the fresh route confirmation in a local fixture. Re-evaluate and show:

- gate result `ABSTAIN`;
- no selected action;
- reason `MISSING_REQUIRED_FACT`, `NO_USABLE_EVIDENCE`, or `SPECIALIST_RUN_FAILED`.

This proves the system does not fabricate certainty when the evidence basis is inadequate.

## Speaking points

1. Specialist agents interpret evidence from different operational perspectives.
2. Every claim is structured, confidence-bounded, and traceable to evidence.
3. NetworkX makes the support and contradiction paths inspectable.
4. Conflict detection is explicit and deterministic.
5. The Decision Gate is pure Python: the LLM cannot choose the action.
6. `ASK` is meaningful disagreement; `ABSTAIN` is insufficient safe evidence; `ACT` requires freshness, coverage, consensus, and a clear margin.
