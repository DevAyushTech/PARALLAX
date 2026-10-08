# PARALLAX MVP demo script

This script uses the real backend API and lets the deterministic Decision Gate calculate every outcome. It does not execute any real-world action.

## Scenario

**Question:** Should emergency vehicles be rerouted from the North Bridge to the East Detour?

The demo uses Bridge B as the observed route condition. Start the backend from a clean database using the exact commands in `README.md`.

## Flow

1. **Create a case** with `risk_level: MEDIUM`.
2. **Submit initial evidence:**
   - `SENSOR`: `Bridge B is blocked`, confidence `0.92`, current.
   - `DISPATCH`: `Bridge B is open`, confidence `0.74`, observed shortly before the first analysis.
   - `REPORT`: `Access uncertain`, confidence `0.61`, current.
3. **Analyze** with `POST /api/cases/{case_id}/analyze`.
4. **Show the conflict:** inspect `conflicts`, `decision.conflicting_claim_ids`, and the graph's `claim_participates_in_conflict` edges. The computed decision is expected to be `ABSTAIN` for the default high-confidence conflict rule; a configured recoverable policy may return `ASK`.
5. **Show the request for evidence:** for `ASK`, render `decision.next_evidence_request`; for `ABSTAIN`, render `decision.reason` and treat it as a fail-closed stop.
6. **Wait for the short demo freshness window** to expire, then submit current dispatch evidence: `Bridge B is blocked`, confidence `0.97`.
7. **Re-evaluate** with `POST /api/cases/{case_id}/reevaluate`, passing the fresh evidence object. The response includes the rebuilt claims, conflicts, graph, decision, and audit.
8. **Show the audit:**
   - `audit.previous_decision`
   - `audit.new_evidence`
   - `audit.new_decision`
   - `audit.reason_for_change`
9. **Show the updated trace:** use `GET /api/cases/{case_id}/graph` or the `graph` in the re-evaluation response. The backend, not the UI, determines whether the final state is `ACT`, `ASK`, or `ABSTAIN`.

With the clean-start commands in `README.md`, initial evidence ages out before the fresh dispatch observation is evaluated, so the conflict is removed and the gate normally computes `ACT`. The exact result remains policy-driven and must be rendered from the response.

## Additional checks

- Fully agreeing evidence should compute `ACT`.
- A high-risk, high-confidence safety disagreement should compute `ABSTAIN`.
- If no LLM provider is configured, the deterministic mock provider still supplies structured specialist claims.
- `ACT` is only a recommendation in this MVP. There is no dispatch, bridge controller, notification, or autonomous action integration.
