# Final implementation plan — execution checklist

Source: `C:/Users/as030/Downloads/CYBERMIND_Final_Implementation_Plan.pdf`.
This tracks the NEW final plan's phase numbering, independently of older repository reports.

## Authorization and scope

- Phase 0 authorized on 2026-09-12: proceed according to the PDF.
- Full CIC-IDS2018 acquisition is deferred to Phase 5 on GB10, as the user explicitly corrected.
- Phase 0 downloads only MITRE ATT&CK, CAPEC, and an NVD snapshot.
- Verify CTU-13 access now; no heavy corpus download on the laptop.
- Audit each completed phase and request approval before starting the next.
- Phases 1–3 authorized on 2026-09-12. Phase 4 requires separate approval. Phases 5–8 are outside this implementation request.
- Subagents are authorized for independent work.

## Phase 0 — COMPLETE (commit `1d91b27`)

- [x] Read the final plan and distinguish it from older master-plan phases.
- [x] Locate active project and inspect existing acquisition tooling.
- [x] Detect RTX 5060, driver 616.56, 8151 MiB reported VRAM.
- [x] Check RAM and logical CPUs: 16,513,445,888 bytes, 24 threads.
- [x] 0.1 Save environment inventory and verify CUDA/bf16 with an actual operation (`hardware.json`).
- [x] 0.1 Set smoke dataloader workers to 8 after user freed RAM; recheck: 5.57 GiB available.
- [x] 0.2 Run existing pytest suite unmodified; 34 passed in each environment. CUDA-environment rerun passed with a workspace-local temporary directory.
- [x] 0.2 Run existing `scripts/phase01_smoke.py`; four steps and 25 evaluation samples passed.
- [x] 0.2 Run two CPU epochs with `configs/smoke.yaml`; evaluate the checkpoint on three held-out synthetic sequences.
- [x] 0.2 Preserve finite-loss train history and evaluation under `examples/smoke/baseline_before/`.
- [x] 0.3 Download and integrity-check MITRE ATT&CK Enterprise STIX (v19.2, 53,835,637 bytes).
- [x] 0.3 Download and integrity-check CAPEC ZIP/XML (v3.9, 587,404 bytes).
- [x] 0.3 Download and integrity-check a clearly scoped NVD snapshot (2,000 CVEs, 4,258,928 bytes).
- [x] 0.3 Verify CTU-13 official access: public, no permission request required. FAQ, license, citation and access status recorded in `data/manifests/phase0_access_status.json`.
- [x] Record source provenance, checksums, baseline configuration, and reproducibility limitations; 49 evidence files and three knowledge snapshots verified.
- [x] Write Phase 0 audit with explicit exit-criterion evidence and limitations (`FINAL_PLAN_PHASE0_AUDIT.md`).
- [x] Present Phase 1 approval gate with the Phase 0 audit. Await the user's decision; no Phase 1 work may start beforehand.

## Phase 1 — COMPLETE (commit `4772f70`)

- [x] 1.1 Inspect edge feature shape and dtype: graph builder emits `[E, 27]` float32; legacy synthetic fixture has seven columns.
- [x] 1.2 Pass edge dimensions/attributes into both GATv2 layers.
- [x] 1.3 Add independent learned edge projections to both dense fallback attention layers.
- [x] 1.4 Thread edge attributes through all world model entry points via `encode_state`.
- [x] 1.5 Add explicit default-off flag; infer/persist enabled width in checkpoints and reconstruct it in inference entry points. Legacy parameter initialization matches exactly; output matches within 1e-6.
- [x] 1.6 All eight CPU/GPU × PyG/fallback × on/off cases passed; both enabled projection gradients nonzero. Full suite: 69 passed, no skipped tests. Legacy checkpoint evaluation matches within 1e-6; all frozen Phase 0 hashes remain unchanged.
- [x] Audit exit criteria in `FINAL_PLAN_PHASE1_AUDIT.md` and present Phase 2 approval request. Await the user's decision.

## Phase 2 — COMPLETE (commit `555c219`)

- [x] 2.1 Define forward/stay transitions, destination-declared resets to 0/1, and unrestricted Unknown/Ambiguous transitions in the YAML policy.
- [x] 2.2 Implement fp32 masked linear-chain CRF and Viterbi decoder, with persisted policy buffers and strict supervision validation.
- [x] 2.3 Add optional, separately logged CRF loss alongside existing cross-entropy; use explicit `campaign_reset` metadata.
- [x] 2.4 Integrate decoded stages in evaluation, app, forecasts and rollouts; checkpoint loaders preserve the CRF flag.
- [x] 2.5 Add illegal-transition counts/rate and pool within-sequence pairs without crossing scenario boundaries.
- [x] 2.6 Verify finite loss/gradients, adversarial legal decoding, and flag-off path on CPU/GPU: 94 tests passed, zero skips; all six CPU/GPU exit checks passed. One-epoch CRF checkpoint trained and reloaded; all 49 frozen baseline files unchanged.
- [x] Audit exit criteria in `FINAL_PLAN_PHASE2_AUDIT.md`; present Phase 3 approval request. User approved Phase 3 with "continue" on 2026-09-12.

## Phase 3 — EXIT CRITERIA NOT MET (original-fixture four-step audit)

Current status supersedes the earlier balanced-fixture completion claim. See `../PHASE3_ROOT_CAUSE_AUDIT.md`: the original fixture remains collapsed at every future step 1–4; no successful model fix was established. The previously completed items below are historical evidence, not permission to enter Phase 4. No exit criterion has been changed by this audit.

### Remediation plan — ACTIVE, authorized 2026-09-13

- [x] Read `CYBERMIND_Phase3_Failure_Remediation.pdf`; preserve the original data and independent four-step gate.
- [x] Step 1: run 100 epochs on the unchanged fixture (400 optimizer updates); selected and last checkpoints both fail diversity at all four steps.
- [x] Step 2: rebuild identical graphs without centering/scaling; labels/topology unchanged and normalized reprojection error zero. The 100-epoch normalization-off diagnostic completed; outcome is retained for the re-audit.
- [x] Step 3: verify structural recoverability from existing model-visible coordinates. Actual history is 3/observed 2; training-only analytical period discovery succeeds. This diagnostic is excluded from the learned-model gate.
- [x] Step 4 implementation: optional training-only class-balanced StageHead CE; default-off compatibility and validation-weight handling tested (21 CPU tests passed).
- [ ] Step 4 outcome: complete the 100-epoch class-weighting diagnostic on the original fixture.
- [ ] Step 5: complete the predeclared CPU learning-rate sweep (0.0001, 0.001, 0.003, 0.01), 100 epochs each.
- [ ] Run current-code regression/tests and publish the full Phase 3 remediation re-audit with every per-step result. Do not claim completion unless the unchanged gate passes.

### Earlier execution record

- [x] 3.1 Run tests and integration for all four feature-flag combinations: 96 passed with zero skips per run, 384 test executions total; four two-epoch CPU pipeline runs passed.
- [x] 3.2 Fresh both-off evaluation/history and frozen checkpoint evaluation match the Phase 0 evidence within 1e-6; all 49 baseline hashes remain intact.
- [x] 3.3 Run both-true two-epoch GPU pipeline and configs/smoke.yaml checks: finite losses, peak reserved memory 88 MiB and 72 MiB respectively, below confirmed VRAM.
- [x] 3.3 Revised diversity gate passed on a separate balanced fixture: all six non-Unknown future stages predicted on CPU and CUDA, eight test predictions per stage, zero illegal transitions over 48 pairs per device. Earlier single-stage failures remain recorded unchanged.
- [x] Add explicit clock-derived reset metadata to the generated CRF integration fixture and report stage histograms/Unknown usage. No existing labels, features or frozen tensors changed.
- [x] User approved the revised gate on 2026-09-12: zero illegal transitions plus at least two non-Unknown predicted stages on a separate balanced synthetic fixture. Preserve original regression fixtures and failed diversity evidence.
- [x] Generate 192/48/48 balanced train/validation/test samples with fixed independent seeds, artificial feature prototypes, boundary metadata and verified split disjointness.
- [x] Train the combined model for two epochs with finite losses and 70 MiB peak reserved GPU memory; the validation-selected checkpoint passes the revised gate on CPU and CUDA. No test-based tuning.
- [x] Write the incomplete-phase audit in `FINAL_PLAN_PHASE3_AUDIT.md`, including failed diversity evidence and proposed corrective scope.
- [x] Complete `FINAL_PLAN_PHASE3_REVISED_AUDIT.md` and present the Phase 4 approval request. All 49 baseline files, 112 original Phase 3 evidence files and 27 original local tensor/checkpoint files remain unchanged. Phase 4 awaits separate approval.

## Phase 4 — NOT AUTHORIZED

- [ ] 4.1 Prepare baseline, edge-only, CRF-only, and combined GB10 configs.
- [ ] 4.2 Run tiny-batch GPU preflight for all four configs on laptop.
- [ ] 4.3 Report transition and suspicious-edge attention diagnostics end to end.
- [ ] 4.4 Establish definite PCAP/packet-feature availability for strict primary-corpus preparation.
- [ ] 4.5 Document CTU-13 access status and any evaluation risk.
- [ ] Audit all exit criteria and stop at the end of Phase 4.
