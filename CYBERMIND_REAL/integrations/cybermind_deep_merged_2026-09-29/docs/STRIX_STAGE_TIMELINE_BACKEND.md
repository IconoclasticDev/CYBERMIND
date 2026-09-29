# Strix stage timeline evidence — backend review contract

Status: backend comparator, local API route, and matching Live Command Center
panel implemented. The same Validation Engine card is also present in Parallel
Futures. Existing visual tokens and card structure are reused.

The comparator is `app/services/strix_timeline_evidence.py`. It compares an
immutable forecast snapshot with an independently recorded, analyst-verified
sandbox event. The first forecast step represents the current observation;
only later steps count as predictions. The event must fall after the frozen
forecast timestamp and inside its declared time horizon. A match requires the
predicted stage in the specific future window containing that event.

The two target stages are model ID 3 (Lateral Movement) and ID 5
(Exfiltration). Each stage result is `MATCH`, `MISMATCH`,
`NO_VERIFIED_EVENT`, or `EVENT_OUTSIDE_HORIZON`. These are **case evidence
verdicts**, not held-out stage accuracy metrics.

## Required inputs

| Input | Required fields | Purpose |
|---|---|---|
| Frozen model forecast | `forecast_id`, `forecast_ts`, `model_version`, consecutive `steps` with `step` and `stage_id` | Establish what the model said before validation |
| Window stride | `step_seconds`, finite and positive | Assign an event to one future prediction window |
| Independently verified sandbox event | `event_id`, `source=sandbox_event_log`, `stage_id`, `timestamp`, `evidence_ref`, `verified_by` | Establish what actually occurred in the isolated lab |
| Strix run and parsed findings | `run_id`, `status`, findings with `finding_id` and optional timestamps | Supporting vulnerability evidence only; never ground truth |

The sandbox event may link to Strix findings through `strix_finding_ids`. A
finding title, CWE, severity, or inferred stage cannot supply a verified
Lateral Movement or Exfiltration event by itself. Missing review or evidence
reference leaves the stage unverified. No event is synthesized from a Strix
finding or from the model's output.

## Response fields shown in the UI

`forecast_id`, `forecast_ts`, `model_version`, `strix_run_id`, `strix_status`,
`step_seconds`, `future_step_count`, and one record per target stage containing
`verdict`, `model_prediction`, `verified_observation`, and `strix_support`.
The response explicitly carries `metric_status=case_evidence_only_not_held_out_stage_accuracy`.

The approved UI integration calls
`POST /api/validations/{validation_id}/stage-evidence`. The route retrieves the
linked frozen forecast and completed, registered SANDBOX Strix run; it does not
start a scan or alter model output. It takes a JSON event log (`{"events": [...]}`),
uses the current graph-window stride, persists the comparison as a local
experiment, and returns the report. With no event log, both stages remain
unverified. The current Strix parser's stage hypotheses are heuristic and use
a different coarse-stage scheme; they are never silently converted into
model-stage labels. The uploaded reviewer name and evidence reference are
attestations, not cryptographically authenticated ground truth.

Focused verification: `pytest tests/app/test_strix_timeline_evidence.py` —
eight passing tests covering matching time windows, wrong-window mismatch,
Strix-only inconclusiveness, absent reviewer evidence, invalid timing,
API linkage to a frozen forecast, and the legacy coarse-stage comparison.
A held-out stage-accuracy claim still
requires multiple independent labeled campaigns and a separate evaluation.
