# CYBERMIND Application Architecture

## 1. System boundary

The existing ML repository is the research/ML core. This application layer turns that core into an analyst-facing offline system.

```text
┌───────────────────────────────────────────────────────────────┐
│                       CYBERMIND PRODUCT                       │
│                                                               │
│  ┌────────────────────── FRONTEND ─────────────────────────┐ │
│  │ War Room │ Scenario Lab │ Replay │ Explain │ Experiments │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │ REST + WebSocket                 │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                        FASTAPI                           │ │
│  │ routing · validation · sessions · websocket · security │ │
│  └───────┬─────────────────┬─────────────────┬──────────────┘ │
│          │                 │                 │                │
│   ┌──────▼───────┐  ┌──────▼────────┐  ┌────▼─────────────┐ │
│   │ Event Engine │  │ Inference     │  │ Scenario Adapter │ │
│   │ + State      │  │ Service       │  │ / Replay         │ │
│   └──────┬───────┘  └──────┬────────┘  └────┬─────────────┘ │
│          │                 │                 │                │
│          └─────────────────┼─────────────────┘                │
│                            ▼                                  │
│                    ┌────────────────┐                          │
│                    │ CYBERMIND ML   │                          │
│                    │ WorldModel     │                          │
│                    └───────┬────────┘                          │
│                            │                                  │
│          ┌─────────────────┼───────────────────┐              │
│          ▼                 ▼                   ▼              │
│       Forecast         Stage/Risk        Explanation         │
│          │                 │                   │              │
│          └─────────────────┼───────────────────┘              │
│                            ▼                                  │
│                 Counterfactual Simulator                     │
│                            │                                  │
│                            ▼                                  │
│                  Local Run / Experiment Store                │
└───────────────────────────────────────────────────────────────┘
```

## 2. Components

### Model runtime

Source of truth:

`src/cybermind/models/world_model.py`

The app must not duplicate model internals. Use an adapter so that the web layer knows only about:

```text
load_model()
predict(sequence)
forecast(sequence, k)
metadata()
```

### Event engine

Responsible for converting normalized events into the graph/time windows expected by the ML layer. Prefer existing components:

- `src/cybermind/data/feature_extract.py`
- `src/cybermind/data/graph_builder.py`
- `src/cybermind/data/temporal.py`
- `src/cybermind/data/types.py`

### State store

Use in-process state for the first live stream and SQLite/JSONL for durable experiment records.

Do not introduce Redis/PostgreSQL until scale requires it.

### Scenario adapter

Interface-based design:

```python
class ScenarioAdapter:
    def start(self, scenario_id): ...
    def stop(self, scenario_id): ...
    def reset(self, scenario_id): ...
    def status(self, scenario_id): ...
    def collect(self, scenario_id): ...
```

Implement `ReplayScenarioAdapter` first. Implement `DockerSandboxAdapter` second.

Strix/local model integration sits behind the adapter and should emit actions/events, never execute through arbitrary API shell commands.

## 3. Data flow

```text
Telemetry event
    ↓ validate
UnifiedEvent
    ↓ append provenance
Event store
    ↓ windowing
Temporal windows
    ↓ graph build
GraphSequenceSample
    ↓ inference
WorldModel
    ↓ rollout
ForecastResult
    ↓ persist + broadcast
UI / experiment record
```

## 4. Forecast semantics

A forecast is always attached to:

```text
run_id
model_version
timestamp
observation_window
K
```

Without that context, predictions must not be shown as reproducible evidence.

## 5. Counterfactual semantics

Do not mutate the real live state. Clone a graph/window in memory, apply a permitted intervention, and run the same model.

```text
observed state
      │
      ├── baseline → rollout A
      │
      └── intervention → rollout B

risk reduction = risk(A) - risk(B)
```

Persist both trajectories.

## 6. Offline-first requirement

The following must work with no internet connection after installation:

- loading the model
- replaying telemetry
- running inference
- opening the UI
- generating forecasts
- counterfactual comparison
- viewing experiment records

External knowledge datasets may be acquired during development, but runtime inference must not require them.

## 7. Performance targets

Initial target on an RTX 5050/5060 laptop:

- single-scenario batch size = 1
- inference should feel interactive
- WebSocket updates should not block inference
- retain only bounded recent live windows in memory
- archive full replay to disk

Do not claim a hard latency SLA until benchmarked on the real laptop.
