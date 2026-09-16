# CYBERMIND — Real-Data Validation Plan (Pre-Phase-5 Gate)

**Handoff target:** Codex (autonomous coding agent)
**Status this plan resolves:** Open item #1 ("resolve label/packet join on one day locally") — the documented, explicit blocker on Phase 5 GB10 authorization. This is not an optional pre-check. Per `CYBERMIND_CONTEXT.md` §8: *"Do not open the GB10 window until #1 is resolved."*
**Also resolves:** Open item #2 (benchmark degeneracy) — the Track A audit on synthetic data shows the feature-matched baseline **ties** the model exactly (F1 1.0 / FPR 0 / AP 1.0 / ROC-AUC 1.0 both rows, `examples/track_a_benchmark/selected185/comparison.md`). This plan re-runs that same protocol on real data, because a tie that only exists on synthetic data is a different finding than a tie that also exists on real data.

**Ground rules for Codex, carried over from the standing principles already established for this project:**
1. Never swap the fixture/dataset to get a pass. If a day's traffic doesn't produce a clean result, that's a finding, not a reason to pick a different day.
2. Never move a gate after seeing the result. The gates below are fixed before any run starts.
3. Any change to a gate or fixture requires explicit reviewer sign-off, recorded in the PR/commit.
4. Report null and negative results plainly — a documented failure is evidence.
5. Any metric from a non-full-corpus run must be labeled `source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy`.
6. Preserve every checkpoint, including failed ones. Never substitute a passing checkpoint post hoc.
7. Do not overclaim: a synthetic-trained checkpoint evaluated on real data zero-shot is an out-of-distribution test, not "validated on real data."

---

## Phase summary

| Phase | Hardware | Goal | Exit criterion |
|---|---|---|---|
| R0 | CPU only | Select and reprocess PCAP days into real 5-tuple flows | Flow CSVs with full 5-tuple + packet features for 2–3 selected days, hashes recorded |
| R1 | CPU only | Label via corrected schedule | Labeled real-chunk dataset, join methodology documented, discrepancies vs CIC's original labels logged |
| R2 | CPU only | Build real host graph, strict validation | `prepare_data.py --strict` passes on real chunk with `require_packet_features: true` |
| R3 | RTX 5060 (inference) | Zero-shot eval of existing synthetic-trained checkpoint | Results logged and explicitly labeled zero-shot / out-of-distribution |
| R4 | RTX 5060 (train) | Small-scale training run on real chunk (not full corpus) | Checkpoint exists; adapted 4-step rollout gate evaluated and recorded, pass or fail |
| R5 | RTX 5060 (inference) | Re-run Track A benchmark protocol on real chunk | Comparison table: baseline (node-only / node+edge / feature-matched) vs model, on real data |
| R6 | Review, no compute | Go/no-go decision for Phase 5 | Reviewer sign-off recorded; explicit statement of whether the model beats the feature-matched baseline on real data |

---

## Phase R0 — PCAP selection and reprocessing

**Why:** CSE-CIC-IDS2018's released "Processed Traffic Data" CSVs contain no source/destination IP (confirmed, CICFlowMeter issue #43). A 5-tuple join against PCAP is structurally impossible from those files. Real flows must be regenerated directly from PCAP.

**Tasks:**
- R0.1 Select 2–3 days from the 477.32 GB PCAP archive (ten dates total) covering distinct kill-chain stages — do not process the full archive. Cross-reference against the CIC attack schedule (Table 2) to pick days with Reconnaissance, Lateral Movement, and C2/Exfiltration representation, not three days of the same stage.
- R0.2 Run CICFlowMeter (or nProbe, whichever the existing toolchain in the repo already targets — check `scripts/` for any existing flow-export wrapper before writing a new one) against the selected PCAP files. Output: flows with full 5-tuple (Src IP, Dst IP, Src Port, Dst Port, Protocol), timestamps, and the ~80 CICFlowMeter feature columns plus packet-level attributes.
- R0.3 Record SHA256 hashes of both the source PCAP files and the output flow CSVs. Add entries to `data/manifests/dataset_registry.csv` and `SOURCE_PROVENANCE.md` following the existing format for other sources in that file.

**Exit criterion:** Flow CSVs with full 5-tuple for the selected days exist under a clearly named directory (e.g. `data/real_chunk/flows_raw/`), with hashes recorded. No labels yet.

---

## Phase R1 — Corrected labeling

**Why:** CIC's own attack schedule (Table 2) has documented errors (SQL Injection flows with no SQL payload; a Heartleech attack that's documented but never specified). The Distrinet corrected labelling (`https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html`) publishes exact per-attack rules (attacker IP, victim IP, time window) and documents these errors explicitly.

**Tasks:**
- R1.1 Pull the Distrinet corrected rule set for the selected days.
- R1.2 Join labels onto the R0 flow output by (Src IP, Dst IP, time window) per the Distrinet rules — not CIC's original schedule.
- R1.3 As a cross-check, also apply CIC's original Table 2 schedule to the same flows and diff the two label sets. Log every discrepancy explicitly (count, which attack categories affected) rather than silently preferring one. This is a finding to report, per standing principle #4, not a detail to smooth over.
- R1.4 Document the join methodology (exact matching logic, time-window tolerance used, handling of overlapping attack windows) in a new `data/real_chunk/LABELING_METHODOLOGY.md`.

**Exit criterion:** Labeled flow dataset for the selected days; discrepancy log between Distrinet and CIC labels committed; methodology documented and hashed.

---

## Phase R2 — Real graph build and strict validation

**Why:** This step also removes the long-standing "endpoint identities stripped → no faithful host graph" caveat from the architecture doc, since real IPs mean real topology, not a synthetic proxy.

**Tasks:**
- R2.1 Run `build_corpus.py` against the R1 labeled output.
- R2.2 Run `validate_dataset.py --strict`. This must actually exercise `require_packet_features: true` — if it silently passes without packet features present, that is a validator bug, not a pass. Confirm packet-level attributes (not just flow-level CICFlowMeter columns) survived R0–R1 intact.
- R2.3 Run `prepare_data.py --strict` and confirm it does not hard-fail. If it does, the failure reason (missing packet features vs. missing labels vs. something else) must be logged verbatim, not worked around.
- R2.4 Confirm `graph_builder.py` produces real host-graph edges keyed on real IPs for this chunk (spot-check a handful of nodes/edges against the raw flow data manually).

**Exit criterion:** Strict validation passes end to end on the real chunk. If it does not pass, Phase R3 does not start — fix the pipeline, don't lower the gate.

---

## Phase R3 — Zero-shot evaluation (existing checkpoint)

**Why:** Cheapest possible signal, and it sets an honest expectation before spending a training run. A synthetic-trained checkpoint evaluated zero-shot on real data is very likely to degrade — that's expected and informative, not a failure of the plan.

**Tasks:**
- R3.1 Run the epoch-185 combined checkpoint (`examples/phase3_third_round/extended200/checkpoints/combined.pt`) in inference mode against the R2 real chunk.
- R3.2 Log: stage predictions, illegal-transition rate, infiltration-head outputs, and per-window confidence.
- R3.3 Label every number produced here `source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test` per standing principle #7. Do not describe this as "the model validated on real data" anywhere in docs or slides.

**Exit criterion:** Results recorded regardless of outcome. A collapse here is expected-case information, not a blocker to R4.

---

## Phase R4 — Small-scale real-chunk training

**Why:** This is the actual test of whether the architecture learns something real, as opposed to the synthetic fixture's known extrapolation pathology (train/val/test coordinate ranges that didn't overlap — see `CYBERMIND_CONTEXT.md` §4, Phase 3 root-cause audit).

**Tasks:**
- R4.1 Train on the R2 real chunk only — this is explicitly *not* the full corpus and *not* GB10. Use laptop-scale settings (`configs/laptop.yaml` as the base, both `use_edge_features` and `use_crf_stage` on, matching the combined config).
- R4.2 Reuse the Phase 3 four-step rollout gate (≥2 distinct non-Unknown stages per step, zero illegal transitions, fewer Unknowns than samples) against this real held-out chunk, not the synthetic fixture. If the real chunk is too small for a clean train/val/test split that satisfies this gate, say so explicitly rather than relaxing the gate.
- R4.3 Preserve every checkpoint from every epoch attempted, per standing principle #6. Do not discard failed runs.
- R4.4 Set `early_stopping_patience` deliberately (per the Phase 3 experience, the default of 10 was too low for meaningful convergence — start higher, but record the chosen value and justify it, don't silently reuse 101/201 from the synthetic run without checking it's appropriate for this chunk's size).

**Exit criterion:** A checkpoint exists trained on real data. The adapted rollout gate result (pass or fail) is recorded plainly either way.

---

## Phase R5 — Track A benchmark, real-chunk re-run

**Why:** This is the phase that actually answers the open question from the audit. The synthetic result was: raw-feature baselines score F1 0 / AP 0.33, but once the baseline gets the same periodic features as the model, it ties the model exactly. Real traffic does not hand either model a synthetic periodic column — it's real topology and real temporal structure. This is the first point in the whole project where that tie could actually break.

**Tasks:**
- R5.1 Re-run `scripts/benchmark_compare.py` against the R4 checkpoint, using the corrected protocol already established in Track A: observed `states[:-1]` only, predicting the unseen final-window label, probability threshold fixed at 0.5 before looking at results.
- R5.2 Run all three baseline settings from the original audit: node-only, node+edge, and the closest real-data equivalent of "feature-matched" coverage (i.e., give the baseline every feature the model has access to for this chunk — don't let the model have an unstated feature advantage).
- R5.3 Report FPR and confusion counts including the single-class fallback case (a real risk here — the chunk is small and may be class-imbalanced in ways the synthetic fixture wasn't).
- R5.4 Retain input/checkpoint hashes, protocol version, sample-level probabilities, and limitations, same as the original Track A artifact.

**Exit criterion:** A comparison table exists — baseline (all three feature settings) vs. model, on real data, at matched threshold. State plainly whether the model beats the feature-matched baseline. If it still ties, that goes in the report as a finding, not something to route around before GB10 time is spent chasing the same result at scale.

---

## Phase R6 — Go/no-go for Phase 5

**No compute — review only.**

- R6.1 Confirm R2's strict validation passed (packet-feature join is real, not assumed).
- R6.2 Confirm R4's rollout gate result and R5's benchmark result are both recorded, whichever way they came out.
- R6.3 If R5 shows the model still ties the feature-matched baseline on real data: this is a decision point for the novelty section of the submission, not a data problem — flag it to whoever owns the submission narrative before requesting GB10 time, since it changes what the ablation in Phase 6 of the master plan is actually able to claim.
- R6.4 Reviewer sign-off recorded in writing per standing principle #3, same as any other gate change on this project.

**Exit criterion:** Explicit authorization (or explicit hold, with reason) for opening the GB10 window, based on real-data evidence rather than the synthetic-verified status Phase 4 exit was based on.
