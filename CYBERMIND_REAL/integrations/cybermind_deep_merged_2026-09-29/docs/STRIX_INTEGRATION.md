# Strix Integration

CYBERMIND uses [Strix](https://github.com/usestrix/strix) as its **controlled
adversarial validation layer**. Strix does NOT replace the CYBERMIND world
model — it provides real evidence from authorized, isolated scans that is
compared against CYBERMIND's predictions.

## Architecture

```
TELEMETRY
   ↓
CYBERMIND WORLD MODEL  (latent state, forecast, counterfactuals)
   ↓
PARALLEL FUTURES + CANDIDATE INTERVENTIONS
   ↓
STRIX VALIDATION  (authorized, isolated, registered targets only)
   ↓
OBSERVED EVIDENCE  (vulnerabilities.json + scan_metadata.json)
   ↓
PREDICTION vs OBSERVED COMPARISON  → persisted experiment
   ↓
DEFENCE RECOMMENDATION  → human approval (default) or autonomous sandbox
```

Module layout (`app/adapters/strix/`):

| File            | Role |
|-----------------|------|
| `schemas.py`    | Neutral types: environments, run records, findings, comparisons |
| `safety.py`     | HARD boundary: target registration + authorization gate |
| `client.py`     | Safe argv builder + availability probing (`strix -n --target …`) |
| `runner.py`     | Async run lifecycle (start/status/stop/collect), timeout enforcement |
| `parser.py`     | `vulnerabilities.json` → normalized findings (stage = *inferred*) |
| `artifacts.py`  | Collects Strix's structured artifacts (never scrapes terminal text) |

## Installation

```bash
# Install Strix (requires Docker running + an LLM API key)
curl -sSL https://strix.ai/install | bash
# or: pip install strix-agent

# Configure the LLM provider Strix uses (any LiteLLM-format id)
export STRIX_LLM="openrouter/z-ai/glm-5.3"
export LLM_API_KEY="your-key"      # never stored or logged by CYBERMIND
# optional local model:
# export LLM_API_BASE="http://127.0.0.1:11434"
```

## Environment variables

| Variable           | Default              | Purpose |
|--------------------|----------------------|---------|
| `STRIX_BIN`        | `strix`              | Path to the strix binary |
| `STRIX_LLM`        | —                    | Model id passed to the child env |
| `LLM_API_KEY`      | —                    | Passed through to child env only |
| `LLM_API_BASE`     | —                    | For local models (Ollama etc.) |
| `STRIX_RUNS_DIR`   | `data/strix_runs`    | Child CWD + artifact collection root |
| `STRIX_TIMEOUT`    | `1800`               | Hard wall-clock cap per run (s) |
| `STRIX_MAX_BUDGET` | —                    | `--max-budget` USD cap |

If Strix is not installed, CYBERMIND starts normally and shows
**"Validation unavailable — forecast remains available"**.

## Authorized target model

Every Strix execution must pass `SafetyGate.authorize()`:

1. The exact target string must be **registered** (`POST /api/strix/targets`).
2. The registration must carry an explicit environment:
   - `SANDBOX` — isolated local test rigs (loopback allowed)
   - `REPLAY` — recorded environments
   - `AUTHORIZED_TEST` — registered test assets (loopback/link-local/metadata IPs are refused)
3. Unregistered targets raise `TARGET_NOT_REGISTERED` (HTTP 403).
4. Autonomous mode additionally requires `SANDBOX` (`AUTONOMOUS_NOT_SANDBOX` otherwise).

Built-in sandbox targets for the four demo scenarios are auto-registered at
startup (`http://127.0.0.1:8081`, class SANDBOX).

## Artifact parsing

Strix writes `vulnerabilities.json`, `scan_metadata.json`,
`agent_traces.json`, `tool_executions.json` under its run directory. The
adapter copies these to `STRIX_RUNS_DIR/cybermind-<run_id>/` and parses the
JSON (never terminal output). Findings are normalized to: id, title,
severity, CVSS, affected asset, evidence, reproduction, remediation,
confidence, CVE/CWE.

**Stage hypotheses are heuristics.** Keyword/CWE-based mapping from finding
text to CYBERMIND research stages is always flagged
`attack_stage_inferred: true` — it is never presented as ATT&CK ground truth.

## API endpoints

```
GET    /api/strix/status              availability + registered targets
GET    /api/strix/targets
POST   /api/strix/targets             register (target, environment, label)
DELETE /api/strix/targets?target=…
GET    /api/strix/runs                recent runs
GET    /api/strix/runs/{run_id}
POST   /api/strix/runs                launch authorized run (403 if unregistered)
POST   /api/strix/runs/{run_id}/stop
GET    /api/strix/runs/{run_id}/findings   parsed artifacts
POST   /api/scenarios/{id}/validate   full loop: forecast→run→parse→compare→experiment
GET    /api/scenarios/{id}/validation
GET    /api/validations               all comparisons
GET    /api/validations/{id}
GET    /api/defence/recommendation    ranked recommendation
POST   /api/defence/simulate          counterfactual + recommendation package
POST   /api/defence/approve           human approval
POST   /api/defence/reject            human rejection
GET    /api/defence/pending
GET    /api/forecast/current | POST /api/forecast/generate | GET /api/forecast/{id}
```

## WebSocket events

`strix.run_started`, `strix.run_completed`, `validation.completed`,
`defence.recommendation`, `approval.granted`, `approval.rejected` — all on the
existing `/ws/live` stream.

## Failure behavior

- Strix missing → validation endpoints return 503 `STRIX_UNAVAILABLE`; the UI
  shows a "Validation unavailable" notice; forecasting is unaffected.
- Run fails/times out → comparison is recorded as `INCONCLUSIVE`, never as a
  successful match.
- Model missing → no fabricated predictions; validation is refused (409).

## Limitations

- Strix requires Docker + an LLM key; CYBERMIND itself stays offline-first.
- Observed stage/risk are evidence-based estimates (severity mapping +
  keyword inference), clearly labeled, not ground truth.
- Exit code 2 (findings found) is a *successful* validation run.
- Findings' severity drives an "observed risk estimate" — this is a heuristic
  bridge for comparison, not a calibrated probability.
