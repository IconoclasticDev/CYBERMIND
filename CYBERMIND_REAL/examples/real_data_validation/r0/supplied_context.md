# CYBERMIND — Full Session Context

**Purpose.** Complete context from an extended working session on the CYBERMIND project (SIH 2026, PS 26153). Written so a new agent or team member can resume without re-reading the conversation.
**Last updated.** 2026-09-14

---

## 1. Project identity

| | |
|---|---|
| Competition | Smart India Hackathon 2026 |
| Problem Statement | **26153** — AI-Based Network Attack Forecasting from Network Traffic Data |
| Organisation | National Technical Research Organisation (NTRO) |
| Theme | Blockchain & Cybersecurity · Software |
| Core ask | A **world model** learning `P(S_t+1 \| S_t)` over network state, K-step forward simulation, MITRE ATT&CK stage mapping, explainability, offline demo UI, benchmark vs logistic regression |

### Repositories

- **Current:** `https://github.com/IconoclasticDev/cybermind` — working repo
- **Earlier:** `https://github.com/IconoclasticDev/SIH26` — superseded
- Last inspected remote commit: **`e21a3c5`** (2026-09-13)
- ⚠️ **The remote has repeatedly lagged behind local work.** At last check, `examples/phase3_second_escalation/`, the periodic-feature module, `frozen_gate.py` and the gb10 variant configs existed only locally. Verify push state before assuming remote reflects reality.

### Hardware

- **Dev/smoke:** ASUS ROG Strix G16 — Intel Core Ultra 9 275HX (8P+16E, 24 cores/threads, 5.4 GHz), **RTX 5060 Laptop, 8 GB GDDR7, Blackwell**, confirmed 8,518,041,600 bytes device memory
- **Training target:** NVIDIA Blackwell **GB10**
- Useful property: RTX 5060 and GB10 are the **same architecture generation**, so bf16/tensor-core behaviour validated on the laptop transfers with low parity risk
- 275HX's 24 threads = real dataloader headroom; set `num_workers` 8–12 locally (GB10 config's `num_workers: 0` is a separate known issue)

---

## 2. Architecture (as built)

```
PCAP/CSV → feature extraction (flow + packet level)
         → dynamic host graph (34 node features, 27 edge features, 60s windows)
         → GATv2 graph encoder (edge-conditioned; pure-PyTorch DenseGraphAttention fallback)
         → temporal Transformer
         → latent state z_t
         → stochastic dynamics (diagonal Gaussian, clamped log-variance, reparameterised)
         → K-step rollout
            ├── future-state head
            ├── infiltration head (+ uncertainty)
            ├── stage head + linear-chain CRF (kill-chain constrained)
            ├── explainability (attention / gradient×input / occlusion)
            └── counterfactual engine (interventions, Attack Gravity)
```

**Loss:** `L = λ₁·transition + λ₂·infiltration + λ₃·stage + λ₄·calibration (+ graph consistency)`

**Stage taxonomy:** 7 classes — Benign, Reconnaissance, Initial Access, Lateral Movement, Command & Control, Exfiltration, Unknown/Ambiguous.

**CRF decoder:** transition matrix is `triu` (forward-only), Unknown row/col open, resets restricted to destinations ≤1, illegal transitions masked to `-inf`. `forward()` raises `ValueError` on illegal *observed* transitions rather than injecting `-inf` into the loss.

---

## 3. Assessment history

### Initial evaluation (10-point scale)

| Factor | Score | Realistic ceiling |
|---|---|---|
| Novelty | 6 | 7 (8 with kill-chain decoder + ablation) |
| Complexity / depth | 9 | 9 — saturated, do not add |
| Clarity / format | 8 | 9.5 |
| Feasibility | 7 | 9 |
| Practicability | 7 | 8 |
| Sustainability | 6 | 8 |
| Scale of impact | 7 | 8 |
| User experience | 5 | 9 |
| Future work | 8 | 9 |
| **Overall** | **7.0** | **~8.5** |

Novelty ceiling is **structural**: the PS itself prescribes LSTM/Transformer/GNN, K-step rollout, ATT&CK mapping and SHAP/attention. Building those is compliance, not novelty. Real differentiators are the counterfactual/planner layer and the kill-chain-constrained decoder.

### Competitive ranking (all four cloned and inspected, not README-judged)

**CYBERMIND ranked 3rd of 5** — 1st on architecture and verification discipline, 3rd on deliverables.

| Repo | Py LOC | FE LOC | Tests | Trained ckpt | Real benchmark+FPR | UI | Verdict |
|---|---|---|---|---|---|---|---|
| **NetGuard** (MADOUT20/SIH-2026) | 11,587 | 19,176 | 2 | ✅ | ✅ F1 .948 vs .739 baseline, FPR .017 vs .100 | ✅ | **The one to beat** |
| **Threatora** (Divyansh1982006) | 11,092 | 0 | 6 | ✅ 2 | ❌ | ✅ | README claims RSSM; **code is plain `nn.LSTM`** — no stochastic latent, no KL |
| **CYBERMIND (ours)** | ~3,300 | 0 | 13 files / 189 passing | ❌ | ❌ | ⚠️ built in Track B | Best architecture, weakest deliverables |
| **CYBERWORLD** (chandanbodugam-max) | 1,057 (1 file) | 3,417 | 0 | ❌ | ❌ **hardcoded in `BenchmarkPanel.tsx`** | ✅ | Real LSTM code, fabricated headline numbers |
| **CyberForecast** (darsan25-code) | 1,028 | 5,568 | 0 | ❌ | ❌ | ✅ | **Zero ML dependencies** — pure TS simulation |

Other notable SIH 26153 competitors: `l4keisn0tr34l/wmcy` (architecturally closest — graph encoder + dynamics + MITRE head), `sihcodesprit/external_hackathon`, `AbhijitK20/-SENTINEL`, `sairamsurajpattisapu-jpg/NexSolve-Research`, `csxzor-devcs/sih`, `utkarshkhampar/ThreatCast-AI-Network-Attack-Forecasting`, `div007x/SIH2026---UCS-INGESTION-PIPELINE`.

Reference repos worth borrowing from: `waimorris/Anomal-E` (edge-feature GNN), `lorenzo9uerra/GraphIDS` (NeurIPS 2025), `mayank02raj/MITRE-ATTACK-based-Attack-Chain-Prediction` (SECRYPT 2026, LSTM-Markov constrained decoding).

---

## 4. Phase history

### Phases 0–1 — complete
Packet features, 7-stage taxonomy, attribution wired into `world_model.forecast`, `pos_weight` class weighting, `graph_consistency_loss`, stochastic dynamics head, validation-F1 checkpoint selection with split-disjointness assertion. All landed before the session began (the then-current plan document was stale and didn't mark them done).

### Phase 2 — kill-chain-constrained stage decoder
Linear-chain CRF over StageHead emissions, transition mask in `knowledge/stage_mapping.yaml`, illegal-transition-rate metric, constrained Viterbi at inference.

### Phase 3 — long failure sequence, eventually passed

**Gate:** at each of 4 rollout steps independently — ≥2 distinct non-Unknown stages, zero illegal transitions, fewer Unknowns than samples.

1. **Root cause audit** — total collapse: one stage predicted for all 25 test histories at every step. Traced to **pre-CRF emission degeneracy** (StageHead logits near-identical across histories, max SD ~0.002). Ruled out: learned stay-transition bias (removing it only changes *which* stage wins), CE/CRF scale imbalance (zeroing/rescaling CRF loss changes nothing).

2. **Remediation re-audit** — all five ranked diagnostics executed (more epochs, normalisation ablation, label recoverability, class weighting, LR sweep). 800 epochs. **All failed.**

3. **Second escalation** — reading raw diagnostic JSON revealed two *different* failure modes:
   - **Integration fixture = extrapolation problem.** Train coordinate range −1.7181 to 1.7181; validation 1.7740–2.5004; test 2.5563–3.2826. **100% of val and test windows lie entirely outside the training range.** Model must extrapolate a period-4 rule from a monotonic training domain — a known failure mode for smooth approximators.
   - **Frozen smoke fixture = provably unlearnable.** Generator uses `torch.rand(...)` for features, label from hidden `i % 3` never shown to the model. Generator record: `generator_does_not_condition_feature_distributions_on_attack_or_stage: true`. No model change could ever pass this.

4. **Decisions taken:**
   - **Frozen fixture → Option 2** (rescope gate to zero illegal transitions + finite loss; do *not* regenerate the fixture — regenerating until learnable = the balanced-fixture shortcut already rejected). Executed, passed.
   - **Diagnostic #6 → periodic feature encoding.** Sine/cosine of the existing clock coordinate (`slope=0.02793721242224979`, `intercept=-1.7181385639683615`, `period=4`), appended alongside the unchanged raw channel; 34→36 encoder columns. **Worked** — epoch 100 passed all four steps; pre-CRF logit SD rose from ~0.0004 to 0.67–3.89.
   - **Checkpoint selection → Option 2 with pre-registered tolerance.** `selection_metric: val_f1_stage_band`, `selection_f1_tolerance: 0.05`, `selection_stage_metric: stage`. Primary gate stays validation infiltration F1; near-ties broken on lower validation stage CE. Tolerance fixed **before** application.

5. **Final result — Phase 3 PASSED.** Extended to epoch 200 (patience 201). Selected **epoch 185**: val F1 1.0, stage CE 0.0095, passes all four steps. Epoch 98 (retrospective selection) fails step 1; epoch 200 fails step 1 — both preserved as failures, neither substituted.
   - Passing checkpoint: `examples/phase3_third_round/extended200/checkpoints/combined.pt`

### Phase 4 — complete (2026-09-14)
PCAP availability check, four ablation configs, tiny-batch preflight on RTX 5060 (all four PASS, peak ~293 MB allocated), attention diagnostics, CTU-13 access documentation, **Track A (benchmark) and Track B (analyst UI) both implemented and verified**. 189 tests passing, zero skips. 813 historical evidence entries unchanged.

### Phase 5 — NOT STARTED, requires authorization

---

## 5. Verified code findings (all confirmed by reading source)

| Finding | Detail |
|---|---|
| `edge_attr` computed then discarded | `graph_builder.py` built and normalised it; `encode_state` called `self.graph(state.x, state.edge_index)` only; `GATv2Conv` built with `edge_dim=None`. **Fixed in Phase 1 work.** |
| Stage CE metric key | `validate()` merges averaged loss components → key is **`metrics['stage']`**, NOT `metrics['stage_ce']` (the latter raises KeyError) |
| Selection metric guard | `train.py` lines 212 and 247 hard-reject any `selection_metric` other than the allowed value — extend deliberately, don't rename |
| `min_delta` ≠ tolerance band | Line 279: `improved = f1 > best + min_delta` is one-sided and also drives early stopping. Do not repurpose it for the symmetric tolerance band. Reviewed rule requires `min_delta = 0` |
| `early_stopping_patience` default | **10** — must be raised explicitly for long runs (Phase 3 used 101, then 201) |
| `selection_threshold` default | **0.5**, uncalibrated — item 3.2 threshold sweep still outstanding and now affects checkpoint selection |
| Baseline missing FPR | `LogisticBaseline.metrics()` returned f1/precision/recall/ap/roc_auc — **no FPR**, making the PS-mandated comparison impossible. Addressed in Track A |
| Baseline feature parity | `run_baseline.py:feat()` used `st.x.numpy().mean(0)` — node features only, while the model also consumes `edge_attr`. PS says "same features". Addressed in Track A |
| `app.py` hard stop | Called `st.stop()` without `checkpoints/best_gb10.pt`, blocking all UI work. Fallback to `examples/smoke/smoke.pt` unblocks it |
| `require_packet_features: true` | `gb10_full.yaml` + strict prep **hard-fails** on flow-only CSVs — fails loudly, not silently |

---

## 6. Corrections made during this session

Recorded for calibration — the audit process caught these, which is why its other conclusions are trustworthy.

| Claim made | Reality |
|---|---|
| "Packet features could silently vanish" | They **hard-fail** — `require_packet_features: true` + strict mode |
| "Tolerance rule will keep epoch 94 selected" | Replay over all 100 epochs selected **epoch 98** |
| "Validation stage CE was improving monotonically" | It **rose** at epoch 99 (0.2919 → 0.3046) before falling to 0.2771 at epoch 100 |
| Tie-breaker key `metrics['stage_ce']` | Correct key is `metrics['stage']` |
| Ranked "12th" (user's recollection) | Never happened — **12 competitor repos were listed**; CYBERMIND ranked **3rd of top 5** |

---

## 7. Current blocker — the label/packet join

**The join being attempted is structurally impossible.**

CSE-CIC-IDS2018 "Processed Traffic Data" CSVs **do not contain source/destination IPs**. They ship only `Dst Port`, `Protocol`, `Timestamp` + ~80 CICFlowMeter features. FlowID, SourceIP, DestinationIP, SourcePort are absent from the released files (documented in CICFlowMeter issue #43). A 5-tuple join from PCAP to those CSVs cannot work — one side has no 5-tuple.

### Recommended route

1. **PCAP → CICFlowMeter / nProbe** → flows with full 5-tuple, timestamps, and packet-level features from the same PCAP
2. **Label from CIC's published attack schedule** (Table 2 on the UNB page: attacker IPs, victim IPs, date, start/finish times)
3. **Preferably use the Distrinet corrected labelling** — `https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html` — which publishes exact per-attack rules (e.g. DoS Hulk: Src 18.219.193.20, Dst 172.31.69.25, unix 1518803127–1518803903) and documents genuine errors in CIC's original labels (SQL Injection flows with no SQL payload; a Heartleech attack documented but never specified). Citing a corrected labelling source is a methodological strength.

**Bonus:** this removes the long-standing "endpoint identities stripped → no faithful host graph" limitation from the architecture doc. Regenerating from PCAP gives real IPs, hence real graph topology — the premise of the whole GNN.

**Fallback:** `NF-CSE-CIC-IDS2018` (Sarhan et al.) — exported from the same PCAPs via nProbe, five-tuple keyed, ~8.4M flows with binary + multiclass labels already joined. Weaker for packet features, good cross-check.

**Scale note:** 477.32 GB across ten PCAP archive dates. Do **not** process all of it. Two or three days covering distinct kill-chain stages is sufficient.

---

## 8. Open items

| # | Item | Blocked by | GPU? |
|---|---|---|---|
| 1 | Resolve label/packet join on **one day** locally | — | No |
| 2 | Benchmark degeneracy — baseline and model **both** F1 1.0 / FPR 0 on synthetic; PS requires demonstrating measurable improvement, and a tie demonstrates nothing | #1 | No |
| 3 | Host isolation **increases** predicted risk in the verified case — degenerate fixture artifact or real problem in the counterfactual layer (the headline differentiator). Judges will ask | investigate | No |
| 4 | Threshold calibration sweep (item 3.2) — `selection_threshold` still hardcoded 0.5 | — | No |
| 5 | Track E — demo video (≤2 min) + 5 slides | Track B done, so unblocked | No |
| 6 | Push local work to remote | — | No |
| 7 | Phase 5 — corpus acquisition + GB10 training | #1, user authorization | Yes |

**Do not open the GB10 window until #1 is resolved.** Without a defensible label join, a training run produces a checkpoint nobody can stand behind.

---

## 9. Submission deliverable status

| PS deliverable | Status |
|---|---|
| Source code link | ✅ (verify remote is current) |
| README with setup instructions | ✅ Rewritten — 5-minute quick start against bundled smoke checkpoint, no GPU/data needed |
| Architecture document (≤2 pages) | ✅ Rewritten, verified exactly 2 pages when rendered |
| Demo video (≤2 min) | ❌ Not started — unblocked, start now |
| Technical presentation (≤5 slides) | ❌ Not started — unblocked, start now |
| Feature extraction pipeline | ✅ |
| Trained world model + scripts | ⚠️ Scripts yes; real-corpus checkpoint no |
| K-step infiltration engine | ✅ |
| Explainability | ✅ attention + gradient + occlusion |
| Offline demo interface | ✅ Track B |
| Benchmark vs logistic baseline | ⚠️ Pipeline exists; numbers degenerate on synthetic |

**Note on SHAP:** there is no SHAP in the repo. The PS says "SHAP values **or** model attention weights" — attention + gradient attribution satisfies it, but **state this explicitly** in README/architecture doc or a judge skimming for "SHAP" marks it missing.

---

## 10. Standing principles (established through the audit chain)

1. **Never swap the fixture to get a pass.** The balanced/prototype fixture was rejected once; regenerating a fixture until it becomes learnable is the same move in a different costume.
2. **Never move a gate after seeing the result.** Tolerances and thresholds are fixed before application, in writing.
3. **Gate/fixture changes require reviewer sign-off**, recorded. Engineering does not decide these unilaterally.
4. **Report null and negative results plainly.** A documented failure is evidence; a quiet reframe is not.
5. **Never report metrics from a smoke checkpoint** without labelling them `source: synthetic fixture — not real-corpus accuracy`.
6. **Preserve failed checkpoints**; never substitute a passing one post hoc.
7. **Don't overclaim architecture.** Stage labels are a documented proxy, not ATT&CK ground truth. Counterfactuals are model-based risk differences, not causal effects.
8. Phase 3's pass is **narrow** — epochs 98 and 200 both fail step 1, epoch 185 passes. Describe it as "passes under the reviewed protocol on synthetic verification data," never as verified forecasting capability.

---

## 11. Strategic position

**Biggest weapon:** no competitor has anything close to this audit discipline. Several make large accuracy claims that don't survive `grep` — one reports hardcoded benchmark constants, one has no ML dependencies at all, one claims an RSSM that is a plain LSTM. Pairing genuine rigour with a working demo is rarer than any architecture choice.

**Biggest risk:** deliverables, not capability. A judge scores what they can see and run.

**Path to 1st:** resolve the join → train on real data → produce the benchmark table at a calibrated operating point → record the video. Architecture is already ahead of the field; the gap is entirely mechanical.
