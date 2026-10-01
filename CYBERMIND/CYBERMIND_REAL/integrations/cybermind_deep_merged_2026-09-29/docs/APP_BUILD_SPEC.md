# CYBERMIND App Build Specification

## Purpose

This document is the implementation contract for turning the trained CYBERMIND model into the complete offline product: telemetry ingestion, state management, world-model inference, forecast visualization, counterfactual scenario management, explainability, replay/evaluation, and the analyst UI.

The implementation must use the existing model under `src/cybermind/models/world_model.py` as the canonical ML brain. Do not create a second ML architecture unless the model interface genuinely cannot support a required feature; in that case, add an adapter rather than replacing the model silently.

## Golden rule

The trained model is the only artifact that must be supplied manually for the app to become operational.

Expected placement:

```text
models/cybermind_final.pt
```

Optional deployment export:

```text
export/cybermind_compact.onnx
```

The application must discover the model, validate its checkpoint metadata, load it once, and expose model health/version information through the API.

## Product contract

CYBERMIND is an offline predictive cyber-defence war room, not a generic CRUD dashboard.

Primary loop:

```text
Observe → Understand → Forecast → Simulate → Recommend → Re-observe → Replan
```

The UI must make this loop visible.

## Runtime modes

### Replay mode

Used first and required for deterministic demos.

```text
recorded telemetry/scenario
        ↓
replay engine
        ↓
inference
        ↓
forecast + timeline + explanations
```

### Live mode

Consumes authorized telemetry from local files, a local collector, or a sandbox adapter. No mandatory cloud service.

### Scenario-lab mode

Runs only against the explicitly isolated local sandbox. The app should start/reset/stop a scenario through an adapter interface. The adapter must never assume internet access or expose the sandbox to external networks.

## Functional requirements

### F1 — Model management

- Detect `models/cybermind_final.pt`.
- Validate checkpoint structure before loading.
- Load model only once per backend process.
- Report model version, node dimension, model parameters, checkpoint path, device, and load status.
- Support CPU and CUDA inference.
- Default to safe device selection.
- Never fabricate a model score when the model is unavailable.

### F2 — Telemetry ingestion

Accept the unified event schema already defined in `data/manifests/schema.json`.

Required fields:

```text
timestamp, src, dst, label, source
```

Optional fields include ports, protocol, bytes, packets, duration, attack stage, technique ID, vulnerability context, scenario ID, source file, and provenance.

Support:

- JSON event
- JSONL file
- CSV file matching normalized schema
- replay bundle

Every ingested item must retain provenance.

### F3 — Temporal state engine

Convert events into time windows and graph states using the existing data-layer primitives where possible.

The backend must retain:

```text
current window
previous windows
node IDs
edge IDs
scenario ID
timestamps
provenance
```

Do not invent endpoint identities when the source does not provide them.

### F4 — Inference

For each completed observation window:

```text
Graph sequence
   ↓
CYBERMIND WorldModel
   ↓
current latent
   ↓
K-step rollout
```

Return:

- current risk
- future risk trajectory
- predicted stage trajectory
- latent state summary
- current graph summary
- inference latency
- model version

### F5 — Forecast API

Canonical response shape:

```json
{
  "timestamp": 0,
  "risk": 0.0,
  "stage": "unknown",
  "stage_id": 0,
  "confidence": 0.0,
  "step": 0
}
```

Risk is a model score. Unless calibrated and explicitly evaluated as a probability, do not label it as a causal probability.

### F6 — Explainability

Expose feature/node attribution from `src/cybermind/explainability/attribution.py` where compatible.

UI explanation should answer:

> Why did future risk increase?

Prefer evidence such as:

- high-volume edge
- unusual flow rate
- repeated connection pattern
- suspicious host centrality
- temporal trend
- model-attributed feature

Do not generate unsupported narrative explanations.

### F7 — Counterfactuals

The first implementation must be model-based risk comparison:

```text
baseline future
vs
intervened future
```

Supported intervention abstractions:

- isolate host
- block edge
- suppress destination port/edge
- remove selected node/edge from the simulated graph

Return:

```text
baseline risk
intervention risk
risk reduction
affected nodes/edges
```

Call this `Counterfactual Risk Simulation` or `Attack Gravity` only after the math is implemented and logged.

Do not claim formal causal effects.

### F8 — Scenario lab

Scenario adapter interface:

```text
start(scenario_id)
stop(scenario_id)
reset(scenario_id)
status(scenario_id)
collect(scenario_id)
```

The initial adapter may be a safe mock/replay adapter. A Docker sandbox adapter may be implemented later.

The app must treat Strix/local-AI as a scenario generator, not as the CYBERMIND model itself.

### F9 — Replay and experiment records

Every run must have a unique `run_id`.

Persist:

```text
run_id
scenario_id
model_version
config_hash
start_time
end_time
input source
predictions
interventions
actual outcomes when available
metrics
provenance
```

Suggested storage:

- SQLite for local metadata/results
- JSONL for raw event replay
- Parquet/torch files for heavy datasets

Do not require a remote database.

### F10 — WebSocket live feed

Endpoint:

```text
/ws/live
```

Messages:

```json
{
  "type": "forecast",
  "run_id": "...",
  "timestamp": 0,
  "risk": 0.0,
  "stage": "...",
  "forecast": []
}
```

Also support event types:

```text
state
alert
forecast
scenario
intervention
system
```

## UI contract

### Single-screen war room

Use the master-plan composition:

```text
┌──────────────────────────────────────────────────────────────┐
│ CYBERMIND                         ● LIVE     MODEL: vX       │
├───────────────────┬────────────────────────┬─────────────────┤
│ NETWORK WORLD     │ FUTURE FORECAST        │ DEFENCE PANEL   │
│                   │                        │                 │
│ graph             │ NOW → +1 → ... → +K  │ risk            │
│ nodes             │ risk curve             │ gravity         │
│ attack path       │ stage path             │ recommended     │
│                   │ confidence             │ intervention    │
├───────────────────┴────────────────────────┴─────────────────┤
│ TIMELINE / EVIDENCE / REPLAY                                 │
└──────────────────────────────────────────────────────────────┘
```

### Required screens

1. War Room — default.
2. Scenario Lab — controlled/replay scenarios.
3. Replay — timestamp scrubber and actual-vs-predicted comparison.
4. Explain — evidence and attributions.
5. Experiments — model/version/metrics provenance.
6. System — model/data/runtime health.

## API surface

Implement these routes:

```text
GET  /api/health
GET  /api/model
POST /api/telemetry/events
POST /api/telemetry/replay
GET  /api/state/current
GET  /api/forecast
GET  /api/timeline
GET  /api/runs/{run_id}
POST /api/scenarios/start
POST /api/scenarios/stop
POST /api/scenarios/reset
GET  /api/scenarios/{scenario_id}
POST /api/counterfactual/simulate
GET  /api/experiments
GET  /api/experiments/{run_id}
WS   /ws/live
```

## Security and safety

- Bind locally by default.
- No default outbound network action.
- Scenario lab must use an isolated network.
- No destructive exploit automation.
- Never accept arbitrary shell commands through the API.
- Validate file paths against configured input roots.
- Redact secrets from logs.
- Keep sandbox adapter behind explicit configuration.

## Development order for an AI coding IDE

1. Read `AGENT.md`, this file, `docs/APP_ARCHITECTURE.md`, and `docs/APP_FOLDER_STRUCTURE.md`.
2. Verify the model loads from `models/cybermind_final.pt`.
3. Implement API health/model endpoints.
4. Implement telemetry schema validation and local run store.
5. Implement inference service using existing model code.
6. Implement forecast/timeline endpoints.
7. Implement WebSocket events.
8. Build the War Room UI against real API data.
9. Implement replay.
10. Implement counterfactual simulation.
11. Add scenario adapter and isolated sandbox integration.
12. Add experiment/evaluation views.
13. Run tests and an end-to-end demo using recorded/sandbox telemetry.

## Definition of done

The app is complete when a clean environment with:

```text
models/cybermind_final.pt
```

can be started locally and provides:

- health check
- model status
- telemetry ingestion
- live/replay inference
- current graph
- K-step forecast
- risk and stage outputs
- explainability
- counterfactual comparison
- scenario controls
- replay
- persisted experiment metadata
- offline frontend

The app must work without a cloud AI API.
