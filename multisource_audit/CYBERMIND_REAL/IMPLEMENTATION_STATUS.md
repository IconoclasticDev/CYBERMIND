# CYBERMIND — Implementation Status

## Complete before GPU training

- [x] Dynamic network graph construction
- [x] Node + edge temporal features
- [x] GATv2 graph encoder with development fallback
- [x] Temporal Transformer
- [x] Latent network-state representation
- [x] Learned dynamics model
- [x] K-step rollout
- [x] Future state head
- [x] Infiltration-risk head
- [x] Attack-stage head
- [x] Multi-task training loss + Brier calibration term
- [x] Mixed-precision CUDA training
- [x] Batch sequence training + gradient accumulation
- [x] Scenario/group-level leakage-safe split
- [x] Logistic baseline
- [x] Early-warning lead-time metric
- [x] Counterfactual intervention simulator
- [x] Attack Gravity
- [x] Gradient-based attribution
- [x] Rollout visualization
- [x] Offline Streamlit war-room UI
- [x] PCAP endpoint extraction
- [x] Unified dataset schema
- [x] CIC-IDS2018 public-data download path
- [x] Adapters for CIC/UNSW/CTU/CICIoT-style tabular flows
- [x] Knowledge-source registry for ATT&CK/CAPEC/NVD
- [x] Source provenance manifest + strict validation
- [x] 128-GB-GPU preflight + runbook
- [x] Synthetic forward/backward/checkpoint smoke tests previously executed

## Depends on the actual public data host

- [ ] Download/collect the desired CIC-IDS2018 raw CSV/PCAP corpus
- [ ] Run `build_corpus.py` over the real files
- [ ] Run strict validation and `prepare_data.py`
- [ ] Produce real train/val/test tensors and baseline results

Once those data artifacts exist and `gpu_preflight.py` passes, the final ML action is the real `train.py` run. The resulting checkpoint then feeds evaluation/UI/post-training evidence generation.

## Scientific guardrails

- Endpoint identity is never fabricated in strict mode.
- Coarse dataset-label -> stage mapping is explicitly marked as a proxy, not native ATT&CK ground truth.
- Scenario/group splits are used instead of random row splits.
- Cross-dataset metrics are reported separately from primary-source metrics.
- Counterfactual numbers are reported as simulated/model-based risk changes, not causal effects.

## Final training-ready state

All code paths required before the heavy model-training experiment are included:

- public-source manifests and provenance tracking
- CIC-IDS2018 public S3 acquisition helper
- generic public-source acquisition helper for ATT&CK/CAPEC/NVD and manual/direct-URL dataset collection
- unified event schema and adapters
- PCAP endpoint extraction path
- strict validation
- temporal graph construction
- scenario-aware / chronological leakage-safe split
- GraphSAGE/GATv2-compatible graph encoder
- temporal Transformer
- latent dynamics predictor and K-step rollout
- infiltration + stage + state-transition heads
- multi-task losses including Brier calibration term
- logistic baseline
- early-warning evaluation
- counterfactual intervention simulation + Attack Gravity
- gradient attribution
- rollout plotting
- offline Streamlit war-room
- CUDA/PyG preflight
- automated end-to-end training launcher with resume support

**Remaining experimental action:** train the model on the collected real corpus on the target GPU and record the resulting metrics/checkpoint. No fabricated performance numbers are included.
