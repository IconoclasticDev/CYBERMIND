# CYBERMIND — Two-Page Architecture and Improvement Plan

**Problem statement:** SIH26153 — Predictive cyber defence with a network world model<br>
**Evidence date:** 26 September 2026<br>
**Scope:** Architecture document requested for the repository. The two-minute video and five-slide presentation are separate submission artifacts.

## Page 1 — System architecture

### Objective and operating model

CYBERMIND learns how a protected network changes over time instead of classifying each flow independently. Given observed graph states \(S_{t-H+1},\ldots,S_t\), it learns a latent transition distribution approximating \(P(z_{t+1}\mid z_t)\) and recursively simulates \(K\) possible future states. Each future state produces an infiltration probability, a coarse ATT&CK-aligned stage, rollout dispersion, and model-sensitivity evidence for an analyst. The system runs offline and now accepts a local PCAP, PCAPNG, CSV, or a reproducible prepared test sequence.

```mermaid
flowchart LR
    A[PCAP / PCAPNG / CSV] --> B[Schema adapter and provenance checks]
    B --> C[60 s windows / 30 s stride]
    C --> D[Dynamic host graph]
    D --> E[GATv2 edge-aware encoder]
    E --> F[Causal temporal Transformer]
    F --> G[Latent state z_t]
    G --> H[Gaussian dynamics model]
    H --> I[K-step stochastic rollouts]
    I --> J[Infiltration head]
    I --> K[Stage emissions + optional CRF]
    I --> L[Future-state decoder]
    J --> M[Risk timeline and FPR/F1]
    K --> M
    L --> M
    M --> N[Explanations and isolation sensitivity]
```

### Input and state representation

Hosts are graph nodes and observed communications are directed edges. Node features summarize packet and flow volume, peer and port diversity, protocol ratios, duration, inter-arrival time, activity rate, and packet statistics. Edge features include bytes, packets, protocol, port, direction, duration, inter-arrival time, TTL moments, TCP-window moments, fragmentation ratios, payload-size distribution, scan-order signals, and retransmission signals. Training-only means and standard deviations normalize every feature; the fingerprint is embedded in each checkpoint and checked again at inference.

The ingestion boundary is deliberately strict. Production checkpoints that require packet telemetry reject flow-only uploads. Inputs with missing timestamps or endpoint identities are rejected because chronological transitions and host graphs cannot be reconstructed faithfully. Uploaded labels are ignored during inference. CIC-IDS2018 labels remain attack-family labels, so stage supervision is a documented proxy mapping rather than native ATT&CK ground truth.

### Model and objective

GATv2 attention converts each variable-size graph into a graph representation. A causal temporal Transformer encodes the ordered graph history into latent states. The dynamics network predicts a diagonal-Gaussian next-state distribution; seeded sampling produces multiple repeatable futures. The stage decoder can apply a constrained linear-chain CRF that permits forward-or-stay progression, declared campaign resets, and an Unknown/Ambiguous state.

The improved training objective is:

\[
L=\lambda_dL_{Gaussian\ dynamics}+\lambda_sL_{future\ state}+\lambda_iL_{infiltration}
+\lambda_aL_{stage}+\lambda_cL_{CRF}+\lambda_bL_{Brier}+\lambda_gL_{consistency}.
\]

`L_future state` is connected to the explicit future-state decoder. Previously that head was serialized and displayed but received no loss gradient. The final grouped configuration assigns it weight `0.25`, preflight requires a finite non-zero gradient through the head, and the epoch-21 checkpoint was trained with the repaired objective.

### Offline analyst interface

The Streamlit console accepts a trusted local checkpoint and either an uploaded capture/table or a prepared held-out case. It shows observed topology, a K-step risk and stage timeline, rollout standard deviation, transition legality, feature/attention sensitivity, and model-space host-isolation comparisons. A coverage-aware evidence layer preserves the raw model stage, separately reports conservative host-level indicators for stages 3–5, and abstains to Unknown/Ambiguous when an unsupported stage lacks evidence. The rules use inverse-normalized observed telemetry plus the learned risk gate; they never change model risk and are not presented as trained stage accuracy. The console performs no network action. Temporary upload files are deleted after graph construction; inference does not require an external API.

---

## Page 2 — Evaluation, safeguards, evidence, and remaining work

### Leakage-safe evaluation

Evaluation now withholds the final \(K\) windows, supplies only `states[:-K]` to the model, and scores each future step in order. Reports include per-horizon and pooled precision, recall, F1, false-positive rate, average precision, stage accuracy, stage macro-F1, and illegal-transition rate. Expensive explanations are opt-in during bulk evaluation to reduce compute use.

The logistic comparison follows the same information boundary. One StandardScaler and one logistic head per horizon are fitted using only the training split. The feature-matched setting receives all node and edge columns plus fixed graph-topology summaries, but cannot reproduce graph message passing. Its threshold is fixed before test evaluation.

On the leakage-safe final grouped test split of 1,039 sequences, using four unseen windows and threshold `0.5`, the selected epoch-21 world model produced:

| Model | Precision | Recall | F1 | FPR | AP |
|---|---:|---:|---:|---:|---:|
| World model, pooled K=4 | 0.9970 | 0.9730 | 0.9849 | 0.0056 | 0.9985 |
| Feature-matched logistic, pooled K=4 | 0.9314 | 0.9219 | 0.9266 | 0.1314 | 0.9807 |

Across 4,156 future-window decisions, the world model produces 8 false positives and 74 misses versus the baseline's 186 false positives and 214 misses. This is a 5.82 percentage-point F1 gain and a 95.7% reduction in false alerts. The world model’s pooled stage accuracy is `0.3354`, stage macro-F1 is `0.2443`, and decoded illegal-transition rate is `0.0`. The low stage score is expected because stage 4 is deliberately unseen during training. Full machine-readable results are stored in `results/final_grouped/eval_test_k4.json`, `results/final_grouped/baseline_test_k4.json`, and `results/final_grouped/model_comparison.json`.

These are useful internal results, not proof of unseen-environment generalization. Capture-day groups are chronological and disjoint, validation contains benign and malicious targets, and stage 4 is an unseen-campaign test. Stages 3 and 5 remain absent from authoritative training data. The rule-supported analyst evidence closes a demonstration gap but does not close that training-data gap. No claim should extend beyond that evidence.

### Controls against overfitting

1. Split events chronologically before histories are formed, purge a full window at boundaries, and never randomly distribute rows from one episode across splits.
2. Fit normalization and class weights from training data only. Never tune a threshold on test labels.
3. Select checkpoints on validation metrics with early stopping; do not add epochs after validation stops improving.
4. Compare every candidate against the identical feature-matched logistic protocol and report confusion counts, FPR, and per-horizon degradation.
5. Use dropout, weight decay, gradient clipping, stochastic dynamics, and fixed seeds. Treat rollout variance as dispersion, not calibrated confidence.
6. Keep CTU-13 or another environment entirely held out. Report a flow-only external result separately when packet-feature parity cannot be established.

### Ordered improvement plan

| Priority | Improvement | Acceptance evidence |
|---:|---|---|
| 1 | Retrain the repaired combined model with edge features, CRF, and future-state loss; train a separate architecture baseline with both feature flags off | Two configuration-identified checkpoints, epoch reports, identical validation selection rules |
| 2 | Calibrate the operating threshold on a mixed-class validation split for a declared target FPR | Frozen threshold plus validation/test confusion matrices; no test tuning |
| 3 | Add genuine Lateral Movement and Exfiltration examples, or controlled labeled captures, without oversampling duplicates across splits | Non-zero train/validation/test support by stage and provenance hashes |
| 4 | Run external zero-shot evaluation | Dataset-specific report with feature-coverage differences stated explicitly |
| 5 | Replace the legacy directional PCAP exporter for future training with a verified bidirectional flow/packet join | Reverse traffic populates backward byte, packet, and IAT fields; deterministic capture tests pass |
| 6 | Distill/export only after the teacher is selected | CPU-only latency under 50 ms and artifact under 100 MB on the stated target machine |

The next training run should stop on validation evidence rather than a requested epoch count. The current epoch-21 checkpoint has 925,064 parameters and is approximately 10.69 MB because it includes optimizer/training state. A final inference-only state dictionary can be smaller.

### Submission readiness boundary

The architecture now directly covers the world-model transition objective, K-step forecasting, packet/flow graph inputs, stage progression, coverage-aware evidence, explainability, and offline PCAP/CSV ingestion. The final grouped checkpoint has been trained and evaluated without leakage across capture-day groups. Genuine learned stages 3 and 5 and external-environment validation remain future evidence requirements; until then the console abstains or labels telemetry rules explicitly. The official reference is the [SIH26153 problem statement](https://sih.gov.in/sih2026PS#ViewProblemStatement26153).
