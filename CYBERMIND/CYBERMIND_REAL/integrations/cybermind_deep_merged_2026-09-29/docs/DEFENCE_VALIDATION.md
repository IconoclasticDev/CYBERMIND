# Defence Validation Workflow

The loop: **Predict → Simulate → Validate → Defend → Replan**.

## Modes

### Approval Mode (default)

```
Forecast → Candidate defence → Strix validation → Recommendation
       → HUMAN APPROVAL REQUIRED → APPLY / REJECT
```

- The recommendation is created with `approval_required: true` and parked in
  `/api/defence/pending`.
- `POST /api/defence/approve` or `POST /api/defence/reject` resolves it; the
  decision (who, when, what) is logged and broadcast on `/ws/live`.
- No consequential action is ever auto-executed.

### Autonomous Sandbox Mode

Only for **registered SANDBOX** environments. `SafetyGate.authorize_autonomous()`
hard-fails (`AUTONOMOUS_NOT_SANDBOX`) for anything else. In this mode the
recommendation proceeds without the approval gate, and execution stays inside
the isolated sandbox scenario.

The UI always shows the active mode explicitly:

```
MODE  ○ Approval   ○ Autonomous Sandbox
```

## Ranking model

`DefenceService.score()` ranks candidates by weighted composite (0–1):

| Factor           | Weight | Notes |
|------------------|-------:|-------|
| Risk reduction   | +0.45  | saturating (min(reduction×2, 1)) |
| Model confidence | +0.20  | boosted slightly by validation evidence |
| Reversibility    | +0.15  | monitoring ≫ isolation |
| Collateral impact| −0.10  | isolation penalized |
| Validation match | ±0.15  | MATCH +0.15, PARTIAL +0.08, MISMATCH −0.10 |

Raw risk reduction alone never decides the ranking — a validated,
reversible control can beat a heavier unvalidated one.

Recommendation payload (abridged):

```json
{
  "recommendation_id": "…",
  "action": "Isolate Host",
  "baseline_risk": 82,
  "expected_risk": 31,
  "risk_delta": -51,
  "confidence": 0.86,
  "validated": true,
  "validation_run_id": "…",
  "approval_required": true,
  "candidates": [ … ranked … ]
}
```

## Validation comparison

Each `POST /api/scenarios/{id}/validate` produces:

| Field | Meaning |
|-------|---------|
| `predicted_stage` / `predicted_risk` | from the latest CYBERMIND forecast |
| `observed_stage` | inferred from real Strix findings (**always flagged inferred**) |
| `observed_risk_estimate` | severity-derived estimate, not a calibrated probability |
| `match` | `MATCH` / `PARTIAL` (±1 stage) / `MISMATCH` / `INCONCLUSIVE` |
| `prediction_error` | \|predicted risk − observed estimate\| |
| `lead_time` | forecast → observed seconds |

`INCONCLUSIVE` is recorded when a run fails, times out, or produces no
comparable evidence — a failed scan is never counted as a successful
prediction.

## Experiment persistence

Every validation is persisted via `ExperimentStore` as a queryable experiment
containing: scenario, forecast_id, strix_run_id, predicted outcome, observed
outcome (with inference flags), match, prediction error, lead time, model
version, timestamps. Listed at `GET /api/experiments`, visible on the
Experiments page.

## Replan

Comparisons feed future recommendations: validated interventions gain score,
mismatched ones lose it. The forecast itself is never edited by validation —
evidence changes the *defence choice*, not the prediction silently.
