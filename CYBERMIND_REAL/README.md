# CYBERMIND — Counterfactual World Model for Predictive Cyber Defence

Research-grade implementation skeleton aligned to SIH26153 master plan.

## Current Phase 0–1 handoff (2026-09-11)

The current pipeline uses `configs/gb10_full.yaml`, seven stage labels, training-only
normalization, and stochastic dynamics. Follow `docs/PHASE01_FINAL_REPORT.md` for
the verified checklist and Phase 2 commands. The commands and launcher defaults
below use this GB10 configuration and its `data/processed_gb10` output directory.
Existing legacy checkpoints/data must be rebuilt for the new feature/model schema.
Synthetic artifacts under `examples/` are correctness checks, not real training evidence.

Recheck Phases 0–1 locally without starting Phase 2:

```bash
python -m pytest tests -q -p no:cacheprovider
python scripts/phase01_smoke.py
```

## What is implemented

- Dynamic network graph: hosts as nodes, communication relationships as edges.
- Node features: packet/flow counts, protocol distribution, port activity, timing/activity statistics, anomaly proxy.
- Edge features: bytes, packets, protocol, port, direction, duration, inter-arrival statistics.
- GATv2 graph encoder when PyTorch Geometric is available, with a pure-PyTorch graph-attention fallback.
- Temporal Transformer encoder with positional encoding.
- Latent network state `z_t`.
- Learned dynamics transition `z_t -> z_t+1`.
- Multi-step K-step rollout.
- Heads for future state, infiltration probability, and attack stage.
- Multi-task objective: transition + infiltration + stage + Brier/calibration loss, with optional graph consistency.
- Scenario-level split support to avoid row leakage.
- Logistic-regression baseline.
- Early-warning lead-time evaluation.
- Counterfactual intervention simulation: No Action, Block Host, Block Port, Isolate Host, Restrict Edge, Rate Limit.
- Attack Gravity scoring as predicted risk reduction under isolation.
- Multi-hypothesis future generation via stochastic latent rollouts.
- Lightweight future-oriented explanation from gradient/attention attribution.
- Offline rollout visualization.
- Strict metadata for endpoint identity quality and ATT&CK-stage supervision quality.

## Scientific honesty

CIC-IDS2018 CSVs are not guaranteed to contain endpoint identities or true ATT&CK-stage labels in every distribution. The preparation pipeline therefore records identity/stage provenance and can fail in `--strict` mode instead of inventing labels.

The supplied SIH plan requires the world-model core, K-step rollout, infiltration forecast, attack-stage mapping, explainability, offline operation, logistic baseline, and unseen-attack evaluation. Counterfactual Risk Simulation, Attack Gravity, multi-hypothesis futures, early warning, and confidence/OOD are extensions proposed by the plan.

## Quickstart

Supply real CIC-IDS2018 data with endpoint identities and genuinely aligned packet
features first. Flow-only downloads do not satisfy the packet-feature requirement.
On the GB10 host, prepare the data and pass preflight before the first training epoch:

```bash
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/validate_dataset.py --input data/intermediate/CIC-IDS2018 --strict
python scripts/prepare_data.py --config configs/gb10_full.yaml --input data/intermediate/CIC-IDS2018 --strict
python scripts/gpu_preflight.py --config configs/gb10_full.yaml
# Run only after preflight exits successfully:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --epochs 1
```

Inspect memory use and separate loss values before resuming:

```bash
python scripts/train.py --config configs/gb10_full.yaml --device cuda --resume checkpoints/best_gb10_last.pt
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split val
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split test
```

Tune `configs/gb10_full.yaml` for measured graph sizes and GB10 memory use.

## Real-data path

```text
CIC CSV / PCAP
   -> feature_extract.py
   -> graph_builder.py
   -> temporal.py
   -> GraphSequenceSample
   -> train/val/test .pt
   -> GATv2 -> Temporal Transformer -> Dynamics
   -> K-step rollout
   -> risk + stage + state forecasts
   -> metrics / visualization / counterfactual simulation
```

## Folder layout

```text
CYBERMIND/
├── data/raw/CIC-IDS-2018/
├── data/intermediate/
├── data/processed_gb10/
├── src/cybermind/
│   ├── data/
│   ├── models/
│   ├── baselines/
│   ├── evaluation/
│   ├── counterfactual/
│   ├── explainability/
│   └── utils/
├── scripts/
├── configs/
├── checkpoints/
├── results/
├── docs/
└── tests/
```

## Public-source registry

See `configs/sources.yaml` and `docs/PUBLIC_DATA_SOURCES.md`. Use the GB10 preparation commands above for the primary corpus; keep other datasets in separate held-out directories.

## Offline demo

After training: `streamlit run scripts/app.py`.

The legacy `scripts/pcap_to_corpus.py` helper infers labels from filenames. Real training requires genuine packet-to-label alignment.

## One-command training

For the production GPU host:

```bash
source .venv/bin/activate
./scripts/run_training_from_zero.sh
```

To make the launcher download the official public CIC-IDS2018 S3 corpus when the raw directory is empty:

```bash
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

Resume a previous run:

```bash
CYBERMIND_RESUME=checkpoints/best_gb10_last.pt ./scripts/run_training_from_zero.sh
```

Override epochs for a controlled smoke/validation run:

```bash
CYBERMIND_EPOCHS=1 ./scripts/run_training_from_zero.sh
```

## Final pre-training automation

For a GPU host with already prepared and normalized GB10 datasets:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --train-only --epochs 1
```

For a clean machine that should automatically fetch CIC-IDS2018 from the official public S3 bucket when the raw directory is empty:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --download-cic2018 --epochs 1
```

For a 1-epoch production-path sanity run:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --no-download-cic2018 --epochs 1
```

## Laptop export

After a trained checkpoint:

```bash
python scripts/distill_student.py --train-data data/processed_gb10/train.pt --output models/cybermind_student_quant.onnx
```

The student path is deliberately separated from the full PyG teacher because ONNX portability for variable-size graph operators is environment-dependent. The laptop runtime should keep the graph preprocessing layer and run the fixed-size student on its output.

## Safety boundary

The optional sandbox is isolated and non-destructive. It is for integration testing of the CYBERMIND demonstration path, not an exploit launcher.


## ONNX safety guardrails

All model output directories (`checkpoints/`, `export/`, `models/`) are created automatically before writes. Every ONNX export is immediately checked with `onnx.checker` and loaded with `onnxruntime.InferenceSession` on the CPU provider using dummy input. The **<100 MB size gate applies to the laptop student artifact only**; the teacher export is size-reported but not incorrectly rejected for exceeding the student budget.


## One-command lab training

After the one-epoch check on the GB10 host with 128 GB unified memory, the full pipeline can be launched from the project root:

```bash
python scripts/one_click_train.py
```

This uses `configs/gb10_full.yaml`, prepares `data/processed_gb10`, and runs preflight before baselines/training. It also requests evaluation, teacher export and student export. Automatic download cannot supply missing packet-label alignment; preflight rejects incomplete packet coverage. This full pipeline has not been verified on the GB10 yet.

To deliberately disable automatic dataset downloading:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --no-download-cic2018
```

## Submission artifacts

Submission strategy: checkpoints and benchmark JSON/PNG files are eligible for
normal Git tracking. The blanket `*.pt`, `results/*.json` and `results/*.png`
ignore rules have been removed before the first commit; force-add is unnecessary.
Python environments and caches remain ignored.

Once real training and evaluation produce the final files, explicitly stage
`checkpoints/best_gb10.pt`, `results/eval_val.json`, `results/eval_test.json`,
`results/baseline_val.json`, `results/baseline_test.json`,
`results/gb10_train_history.json` and the final benchmark PNGs. Include their
config and normalization constants from `data/processed_gb10/normalization.json`.
Review the staged file list before the submission commit. Synthetic checkpoints
under `checkpoints/phase01_*` and fixture results under `examples/` are not the
final submission evidence.

The workspace has not been initialized as a Git repository, committed, or pushed.
