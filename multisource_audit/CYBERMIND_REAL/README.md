# CYBERMIND — Counterfactual World Model for Predictive Cyber Defence

Research-grade implementation skeleton aligned to SIH26153 master plan.

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

```bash
python scripts/prepare_cic2018_public.sh
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/validate_dataset.py --input data/intermediate --strict
python scripts/prepare_data.py --config configs/smoke.yaml --input data/intermediate --strict
python scripts/train.py --config configs/smoke.yaml
python scripts/eval.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt
python scripts/visualize_rollout.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt
# production:
python scripts/gpu_preflight.py --config configs/gpu_128gb.yaml
python scripts/train.py --config configs/gpu_128gb.yaml
```

For real training, edit `configs/final.yaml` to match the actual data volume and GPU.

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
├── data/processed/
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

See `configs/sources.yaml` and `docs/PUBLIC_DATA_SOURCES.md`. `scripts/run_all_pretraining.sh` performs the full pre-training preparation path after the real public dataset has been placed/downloaded.

## Offline demo

After training: `streamlit run scripts/app.py`.

For endpoint-aware PCAP-only material, use `scripts/pcap_to_corpus.py` before strict validation.

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
CYBERMIND_RESUME=checkpoints/best_128gb.pt ./scripts/run_training_from_zero.sh
```

Override epochs for a controlled smoke/validation run:

```bash
CYBERMIND_EPOCHS=3 ./scripts/run_training_from_zero.sh
```
