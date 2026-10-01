# Phase 4 GB10 handoff

These commands describe the later GB10 run; they have not been executed. Phase 5 requires separate authorization. Do not substitute synthetic tensors or flow-only CSVs for a real packet-complete corpus.

## Configuration and selection

All four `configs/gb10_*.yaml` files have identical settings except `model.use_edge_features` and `loss.use_crf_stage`. They use the reviewed `val_f1_stage_band` selection, F1 tolerance **0.05**, validation stage metric **stage**, and `min_delta: 0.0`. No synthetic periodic-coordinate transform is enabled. Existing GB10 rollout settings (12 future windows, 16 stochastic rollouts) are retained; this does not extend the Phase 3 four-step verification claim to 12 steps.

The four configs intentionally share output names. Use the new `train.py --run-name` suffix to keep selected checkpoints, last checkpoints and training histories separate:

```powershell
python scripts/train.py --config configs/gb10_baseline.yaml --run-name baseline
python scripts/train.py --config configs/gb10_edge_only.yaml --run-name edge_only
python scripts/train.py --config configs/gb10_crf_only.yaml --run-name crf_only
python scripts/train.py --config configs/gb10_full.yaml --run-name combined
```

For example, combined outputs are `checkpoints/best_gb10_combined.pt`, `checkpoints/best_gb10_combined_last.pt`, and `results/gb10_train_history_combined.json`. Resume with the same config and run name, and supply the last checkpoint with `--resume`; retain the previously selected checkpoint as required by the existing resume contract. Evaluate the selected checkpoint, never substitute the last epoch after seeing a gate result.

## Before any real training

- Obtain and verify the full authorized primary corpus on the target host. Remote availability is recorded in `examples/phase4/packet_availability/availability.json`: 10 PCAP archives, 477,321,665,202 compressed bytes, plus 6,886,649,507 bytes of processed CSVs. One capture archive is RAR; the remainder are ZIP. Extraction size and extraction success are unverified.
- Establish and verify actual timestamp/endpoint/label alignment and packet-feature enrichment. Generic filename-derived PCAP labels do not establish CIC-IDS2018 ground truth. This join remains unresolved.
- Build canonical data, run strict validation, and prepare chronological disjoint splits with training-only normalization. `require_packet_features: true` remains mandatory and preparation now rejects incomplete packet measurements before graph construction.
- Run ordinary `gpu_preflight.py --config ...` against the real processed data on GB10. The `--synthetic` mode only tests architecture execution and cannot certify readiness.
- Profile representative graph sizes and production batch/optimizer memory on GB10 before starting the full schedule. Laptop tiny-batch success does not certify production throughput or capacity.

## Interpretation

Phase 3 **passes under the reviewed protocol on synthetic verification data** at epoch 185. Evaluated epochs 98 and 200 fail step 1. The narrow passing result does not establish a stable training plateau, real-data generalization or correct kill-chain forecasting.

The Track A feature-matched logistic baseline ties the selected world model on the synthetic one-step test. Do not claim model superiority. CTU-13 public packet coverage is incomplete across classes; see `PHASE4_CTU13_ACCESS.md`. Analyst host-isolation comparisons are model-space sensitivity probes, not measured containment efficacy.
