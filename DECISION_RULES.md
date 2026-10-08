# PARALLAX Deterministic Decision Rules

The Decision Gate is a pure, deterministic function. It never calls an LLM, reads raw prose, or infers an action from a model response. It receives validated claims, freshness information, conflicts, and agent-run status.

## Fixed scenario constants

- Actions: `REROUTE_EAST_DETOUR`, `KEEP_NORTH_BRIDGE`
- Required safety facts:
  - `north_bridge_safe_for_emergency_use`
  - `east_detour_clear`
  - `east_detour_eta_acceptable`
- Freshness window when an evidence item has no explicit expiry: 15 minutes
- Minimum claim confidence used for conflict detection: `0.50`
- Minimum action score for `ACT`: `0.70`
- Minimum score margin between first and second action for `ACT`: `0.15`
- High-confidence safety opposition threshold: `0.80`

The clock is injected into the evaluator so freshness decisions are reproducible in tests.

## Evidence and claim preparation

1. Evidence is usable only when it has non-empty source/content, a valid timestamp, is not explicitly expired, and is within the freshness window.
2. Future-dated evidence beyond the allowed small clock-skew tolerance is invalid and cannot support a claim.
3. Claims are usable only when Pydantic validation succeeds, every referenced evidence ID belongs to the decision, and at least one referenced evidence item is usable.
4. Claims from failed agent runs, claims with invalid references, and claims backed only by stale evidence are excluded from scoring.
5. Old claims are retained for history but never mixed into the current evaluation's score.
6. Values are normalized for comparison by trimming whitespace and comparing case-insensitively. The graph may preserve the original display text.

## Conflict detection

Two current, usable claims conflict when all of the following hold:

- they use the same `fact_key`;
- their normalized `value` fields differ;
- both claims have confidence at least `0.50`;
- the disagreement is not merely `NEUTRAL` wording with no asserted value.

A conflict is `SAFETY_CRITICAL` when either claim is safety-critical or the fact key is one of the three required safety facts. Otherwise it is `NORMAL`.

A conflict remains `OPEN` for the current evaluation. A later evaluation may record the previous conflict as resolved by new evidence, but it must not delete the old record.

Conflict detection is symmetric and deterministic: claim order only determines how `claim_a_id` and `claim_b_id` are displayed, not the result.

## Action scoring

For each action, use only current usable claims whose `target_action` equals that action. Ignore claims with `target_action = null` for action score, but use their fact coverage and conflict information.

Calculate:

- `support_mean`: mean confidence of `SUPPORTS` claims; `0` when none exist.
- `oppose_mean`: mean confidence of `OPPOSES` claims; `0` when none exist.
- `action_score = clamp(support_mean - oppose_mean, 0, 1)`.

If multiple claims from one agent repeat the same `fact_key` and stance, use the highest-confidence claim from that agent/fact combination. This prevents one agent or one piece of evidence from inflating a score.

The score is explanatory, not a probability. Display it with the gate reason codes so users can see why the result was reached.

## Outcome precedence

Apply rules in this order. The first matching fail-closed rule wins.

### 1. `ABSTAIN`: insufficient basis for a safe decision

Return `ABSTAIN` with no selected action when any of these are true:

- there are no usable claims;
- any of the three specialist runs is missing or failed;
- no current usable claim covers one or more required safety facts;
- all usable evidence is stale, expired, or invalid;
- the current data cannot produce a score for either action.

Reason codes should include the specific cause, for example `NO_USABLE_EVIDENCE`, `MISSING_REQUIRED_FACT`, or `SPECIALIST_RUN_FAILED`.

`ABSTAIN` means PARALLAX does not have enough trustworthy information to recommend even a human-facing choice. It is not an execution command.

### 2. `ASK`: evidence exists but disagreement or uncertainty remains

If the `ABSTAIN` conditions do not apply, return `ASK` with no selected action when any of these are true:

- an open safety-critical conflict remains;
- the highest score is below `0.70`;
- the difference between the highest and second-highest action scores is below `0.15`;
- a high-confidence (`>= 0.80`) safety-critical claim opposes the otherwise leading action;
- the leading action has unresolved conflicting support/opposition on a required fact.

Reason codes should include `OPEN_CRITICAL_CONFLICT`, `LOW_ACTION_SCORE`, `LOW_ACTION_MARGIN`, or `HIGH_CONFIDENCE_OPPOSITION`.

`ASK` means a human or new evidence is needed because the system has a meaningful but unresolved decision situation.

### 3. `ACT`: clear, adequately supported recommendation

Return `ACT` and select the highest-scoring action only when all of the following are true:

- all three specialist runs succeeded with at least one usable claim;
- all required safety facts are covered by current usable claims;
- there is no open safety-critical conflict;
- the selected action score is at least `0.70`;
- its score exceeds the other action by at least `0.15`;
- no high-confidence safety-critical claim opposes it.

Reason codes should include `SUFFICIENT_CONSENSUS` and may include `FRESH_EVIDENCE_REEVALUATED` when applicable.

The selected action is a recommendation only. The MVP does not call a bridge controller, dispatch service, or other external system.

## Fresh evidence and re-evaluation

1. `POST /evidence` appends evidence and leaves the current gate unchanged.
2. `POST /reevaluate` creates a new evaluation number and runs Perception, Operations, and Verifier again.
3. The new run may use all retained evidence, but only currently usable evidence contributes to claims and scores.
4. New claims, conflicts, graph edges, and gate result belong to the new evaluation. Previous results remain immutable history.
5. A fresh item can resolve a prior conflict only through a new evaluation; the old conflict is retained for traceability.
6. A fresh item that creates another unresolved critical conflict must result in `ASK`, not `ACT`.
7. Re-evaluation cannot improve a result by silently dropping contradictory evidence or failed specialist output.

## LLM boundary

The optional LLM adapter may:

- read evidence text;
- classify evidence for one specialist role;
- extract the fixed structured `ClaimDraft` fields;
- provide a short claim explanation.

The LLM may not:

- return `ACT`, `ASK`, or `ABSTAIN`;
- select an action directly;
- calculate gate scores;
- suppress evidence or conflicts;
- alter freshness, confidence bounds, or required-fact rules.

Every model response is parsed and validated. Invalid output is treated as a failed specialist run, causing a fail-closed result rather than a best-effort action.
