# CYBERMIND — Predictive Cyber Defence War Room

**CYBERMIND** is an AI-driven *predictive* cyber-defence platform. Instead of only telling you
that an attack happened, it models how the network is **evolving** and forecasts **where the
attack is going next** — with confidence, explanation, and controlled validation.

> **Observe → Understand → Predict → Verify → Prevent**

```
TELEMETRY → TEMPORAL DYNAMIC GRAPH → GNN → TEMPORAL ENCODER → LATENT CYBER STATE
     → MULTI-STEP FORECAST → RISK / ATTACK STAGE / UNCERTAINTY
     → PARALLEL FUTURES + COUNTERFACTUAL DEFENCES
     → CONTROLLED VALIDATION (optional) → PREDICTION vs OBSERVED → REPLAN
```

---

## Highlights

| Capability | What it does |
|---|---|
| **Command Center** | Live risk, current attack stage, predicted next stage, network graph, event feed, model insights — every number traceable to real telemetry |
| **Parallel Futures** | Multi-hypothesis forecasting: the do-nothing baseline rollout **plus** one genuine model rollout per candidate defence (isolate host, block port, rate-limit…) |
| **Counterfactual Defence** | Baseline vs intervened future risk, ranked by reduction + confidence + reversibility + collateral impact |
| **Validation Engine** *(optional)* | Runs authorized adversarial scans against **registered sandbox targets only**, then compares CYBERMIND's prediction with real observed evidence |
| **Approval workflow** | Human-approval gate for recommended defences; autonomous mode hard-fails outside SANDBOX authorization |
| **Scenario Lab** | Deterministic synthetic kill-chain scenarios (recon → brute force → lateral movement → exfil) streamed through the full pipeline |
| **Replay & Experiments** | Scrub through recorded telemetry; every validation/experiment persisted and queryable |

The UI is a warm-white editorial "scientific instrument" design (cream, charcoal, terracotta) —
no neon, no cyberpunk. React 19 + TypeScript + Tailwind, served fully offline by FastAPI.

---

## Quickstart

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-app.txt
```

### 2. Place the model

```text
models/cybermind_final.pt
```

The app discovers and loads it automatically (CPU or CUDA). **No checkpoint? The app still
starts** in degraded mode: telemetry, graph, replay and scenario lab all work; inference
honestly reports unavailable instead of fabricating predictions. (See *Training* below to
produce the checkpoint.)

### 3. Run

```bash
./run_app.sh                     # http://127.0.0.1:8000
# or directly:
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. Feed it telemetry

- Open the UI and start a scenario from the **Scenario Lab** (e.g. *Lateral Movement (full kill chain)*), or
- `POST /api/telemetry/events` with your own events, or
- replay a file via `POST /api/replay/load`.

Replayed/synthetic data is always visibly labeled `REPLAY` / `SYNTHETIC` — never presented as live.

### Frontend development

```bash
cd frontend && npm install && npm run dev    # Vite dev server
npm run build                                 # production build → frontend/dist (served by FastAPI)
```

---

## Architecture

```text
app/                     FastAPI application layer
├── main.py              service wiring, static UI hosting
├── api/routes.py        REST + WebSocket (/ws/live)
├── services/
│   ├── model_runtime.py       single persistent model instance, CPU/CUDA
│   ├── state_engine.py        telemetry → temporal windows → graph state (incremental)
│   ├── forecast_service.py    K-step rollout → UI forecast
│   ├── counterfactual_service.py  parallel futures + attack gravity
│   ├── defence_service.py     ranked defence recommendations + approvals
│   ├── validation_service.py  predict-vs-observed comparison loop
│   ├── scenario_runner.py     deterministic scenario generator
│   └── experiment_store.py    durable experiment records (offline)
├── adapters/            validation engine integration (safety gate, runner, parser)
└── core/                config, logging

frontend/                React 19 + TS + Tailwind war-room UI
src/cybermind/           ML research core (graph + temporal encoders, dynamics)
scripts/                 training / data pipeline / demo
docs/                    architecture, specs, safety, integration docs
tests/                   30 backend tests (API + safety + validation loop)
```

The ML core (`src/cybermind/`) is untouched research code; the app layer is strictly
adapter-based around it.

---

## Validation Engine (fully optional)

The Validation Engine runs authorized adversarial scans against registered sandbox targets so
CYBERMIND's predictions can be compared with real observed evidence.

**Without it, nothing breaks.** The app probes once at startup; validation endpoints return a
clean typed `503`, the UI shows "Validation unavailable — forecast remains fully functional",
and the entire prediction stack keeps running.

```bash
# Optional setup
export VALIDATOR_BIN=strix         # path to the scan engine binary
export VALIDATOR_TIMEOUT=1800      # hard wall-clock cap per run (s)
export VALIDATOR_MAX_BUDGET=5      # spend cap passed to the engine
```

Hard safety boundaries (enforced in code, see `docs/SAFETY_BOUNDARIES.md`):

- Every target must be **registered** with an explicit environment: `SANDBOX`, `REPLAY`, or
  `AUTHORIZED_TEST`. Unregistered targets are refused.
- Autonomous mode is **sandbox-only**.
- No arbitrary shell execution through the API.
- Observed attack stages from scan findings are always flagged **inferred** — never presented
  as ground truth.

---

## Benchmarks & verification (what is actually proven)

No fabricated accuracy claims. The current checkpoint is a small smoke-scale model; the numbers
below are **measured system benchmarks**, not detection-performance claims on real-world data.

### Measured this build

| Benchmark | Result | Conditions |
|---|---|---|
| Forecast latency (full 13-step rollout) | **~18 ms** | CPU, smoke checkpoint, live dashboard |
| End-to-end tick latency (ingest → windows → inference → broadcast) | **8–30 ms** | after incremental windowing (was 550 ms+ in the naive build) |
| Sustained scenario throughput | 139 events → 64 temporal windows → 80+ predictions, full kill chain | lateral-movement scenario, 5 s/tick |
| Parallel-futures simulation (baseline + 5 interventions) | 6 genuine model rollouts per run | CPU |
| Validation loop (forecast → scan → parse → compare → persist) | seconds end-to-end | controlled validation run |
| Backend test suite | **30/30 pass** | 13 API/state/WS tests + 17 safety/defence/validation tests |
| Frontend build | TypeScript strict, production bundle 343 KB JS (98 KB gz) | React 19 + Vite |

### Training smoke history (`results/train_history.json`)

| Epoch | Total loss | Infiltration loss | Stage loss | Brier |
|---|---|---|---|---|
| 1 | 1.461 | 0.656 | 1.384 | 0.231 |
| 2 | 1.188 | 0.568 | 1.050 | 0.189 |

Losses decrease across all heads on the smoke configuration — the training path converges.
This is **not** a claim of attack-detection accuracy; final metrics come with the real trained
model and real data.

### Data honesty

- `REPLAY` / `SYNTHETIC` / `CONTROLLED LAB` provenance is preserved and displayed.
- Stage mapping is labeled a *research proxy* (see `knowledge/stage_mapping.yaml`), never
  native ATT&CK ground truth.
- Attributions are gradient × input from the trained model — labeled as evidence, not SHAP,
  not causality.

---

## Training

```bash
# smoke path
python scripts/prepare_data.py --config configs/smoke.yaml --input data/intermediate --strict
python scripts/train.py --config configs/smoke.yaml

# production profile (single compact model)
python scripts/one_click_train.py --config configs/colab_t4.yaml
```

Then copy the final checkpoint to `models/cybermind_final.pt` and restart the app.
Full runbooks: `docs/COLAB_T4_RUNBOOK.md`, `docs/128GB_GPU_RUNBOOK.md`.

---

## Documentation index

- `docs/APP_BUILD_SPEC.md` — product/build spec
- `docs/APP_ARCHITECTURE.md` — app architecture
- `docs/PARALLEL_FORECASTING.md` — branching forecast semantics
- `docs/DEFENCE_VALIDATION.md` — ranking model, approval workflow, experiments
- `docs/SAFETY_BOUNDARIES.md` — hard security invariants
- `APP_AGENT.md` — AI-IDE handoff contract

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Model not loaded" banner | Place `models/cybermind_final.pt`, restart. App still runs degraded. |
| "Validation unavailable" | Validation engine not configured (`VALIDATOR_BIN`). Optional — the forecast stack is unaffected. |
| `TARGET_NOT_REGISTERED` | Register the scan target via `POST /api/strix/targets` with a valid environment. |
| `INSUFFICIENT_CONTEXT` (409) | Feed more telemetry (start a scenario) before forecasting/validating. |
| Port busy | `CYBERMIND_PORT=8000 uvicorn app.main:app` or pass `--port`. |
| Graph empty | State engine needs ≥ a few windows; start a scenario in the UI. |

---

*CYBERMIND observes an evolving cyber environment, builds a temporal representation of it,
predicts where an attack is going, explains why, and validates those predictions against
controlled evidence — so defenders can act a step ahead.*
