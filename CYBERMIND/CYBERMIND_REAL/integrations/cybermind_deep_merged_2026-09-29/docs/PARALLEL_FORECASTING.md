# Parallel Forecasting

CYBERMIND's central differentiator: it predicts how the network will **evolve**,
not just what already happened.

## Concept

From the current latent cyber state, the trained world model rolls the future
forward step by step:

```
CURRENT STATE
   │
   ├──── FUTURE A  (No Action — unmitigated baseline rollout)
   ├──── FUTURE B  (Isolate host X)
   ├──── FUTURE C  (Block port P)
   ├──── FUTURE D  (Rate limit)
   └──── …
```

Every branch is a **genuine model rollout** — the same trained model applied to
the same starting window, differing only by a simulated intervention applied
in-memory via `cybermind.counterfactual.simulator.mutate_state`. Nothing is
hardcoded or mocked.

Each branch exposes:

- per-step **risk trajectory** (model sigmoid output per future step)
- per-step **predicted stage** (model stage-head argmax)
- final risk + risk band (LOW/MEDIUM/HIGH/CRITICAL)
- relative risk vs baseline
- the intervention that produced it

## Branch probability

Branch "probability" is **relative risk** vs the do-nothing baseline
(`future_risk / baseline_risk`, clamped) — it is a model-derived weighting, not
a calibrated probability of occurrence. The UI labels it "relative risk" for
honesty.

## Counterfactual semantics

- The live state is **never mutated**; branches are computed on clones.
- Output is a model-based comparison of simulated futures, **not a causal
  effect estimate**. The disclaimer ships with every response.
- Intervention set is fixed and safe: `Isolate Host`, `Block Port`,
  `Rate Limit`, `Restrict Edge`, `Block Host` — never arbitrary commands.

## Attack stage mapping

Stage labels come from `knowledge/stage_mapping.yaml` (research proxy):
`0 BENIGN → 1 RECON/INITIAL ACCESS → 2 EXECUTION/LATERAL → 3 IMPACT/EXFIL`.
The UI always notes: *"Stage mapping is a research proxy, not native ATT&CK
ground truth."*

## UI

The **Parallel Futures** screen (`Threat Forecast → Parallel Futures`)
renders:

- branch cards with stage chains + per-step risk
- multi-line risk trajectory chart (click to highlight)
- summary table (path, rel. risk, final stage, final risk, band)
- per-branch detail panel
- **Scenario Analysis**: baseline vs recommended intervention with risk delta
- **Strix Validation**: run authorized validation, compare prediction vs
  observed evidence
- **Defence Recommendation**: ranked candidates with approval workflow

Branches update smoothly as new telemetry arrives; a full simulation is
explicitly user-triggered and survives live refresh (merge, not clobber).

## Key endpoints

```
GET  /api/forecast/current          latest forecast (stable forecast_id)
POST /api/forecast/generate         force regeneration (k steps)
GET  /api/forecast/{forecast_id}    historical forecast
POST /api/counterfactual/simulate   baseline + intervention branches
POST /api/counterfactual/attack-gravity  per-host gravity ranking
```
