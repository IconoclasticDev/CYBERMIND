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

## Phase 3 — COMPLETE under the recorded reviewer decisions

Final result: the reviewer-approved 0.05 F1 tolerance and validation stage-CE tie-breaker select **epoch 185**, which passes the unchanged integration diversity/legality gate at all four steps. The approved frozen mechanical gate also passes. See `../PHASE3_FINAL_AUDIT.md`. Phase 4 remains unstarted and requires separate approval.

### Third round — complete

- [x] Record exact reviewer selection pseudocode, fixed tolerance 0.05 and stage CE; predeclare extension to epoch 200.
- [x] Implement the approved opt-in policy in the actual training loop, preserving legacy F1-only defaults.
- [x] Apply the rule to all 100 historical validation records: selects epoch 98, correcting the document's epoch-94 prediction. Reproduce missing weights; all histories match within 1e-6 and epoch-100 model tensors match bit for bit.
- [x] Evaluate recovered epoch 98: step 1 fails, steps 2–4 pass. Preserve the failure.
- [x] Resume model/optimizer/RNG through epoch 200. Exact validation-selected epoch 185 passes all four original integration steps; last epoch 200 fails step 1 and is not substituted.
- [x] Verify interrupted/uninterrupted history parity and bitwise selected/last model parity.
- [x] Complete all four flag suites: 145 passed and zero skips each (580 executions), CPU pipelines, combined CUDA pipeline, frozen/both-off 1e-6 comparisons and historical hash preservation.
- [x] Deliver full Phase 3 audit, updated checklist and evidence manifest. Request separate Phase 4 approval only after delivery.

### Second escalation — authorized engineering Option 2

- [x] Record the user's “execute this plan immidiately” instruction with `CYBERMIND_Frozen_Fixture_Gate_Decision.pdf` as authorization for Tasks A/B; retain exact scope in `examples/phase3_second_escalation/REVIEW_DECISION.md`.
- [x] Task A: scope frozen gate to legal transitions and finite/non-degenerate supervised loss with gradient evidence. Original selected/last checkpoints pass; original diversity failures remain recorded. No regeneration or further frozen training.
- [x] Task B: add default-off sine/cosine channels from original per-node coordinate, keeping all raw tensors unchanged. Train-only calibration and checkpoint-safe inference implemented.
- [x] Run CPU diagnostic #6 for 100 epochs, same seed, optimizer, losses, selection and original integration gate. Epoch 94 selected: FAIL steps 1–3, PASS step 4. Epoch 100 last: PASS all steps; not substituted for selected checkpoint.
- [x] Complete current-code CPU/CUDA regression matrix: 131 passed with zero skips per flag context (524 executions); CPU pipelines, combined CUDA pipeline and baseline comparisons pass. Prior evidence hashes preserved; published `PHASE3_SECOND_ESCALATION_AUDIT.md`.
- [x] Resolved in the third round: the authorized validation-selected epoch 185 passes all four integration steps. Phase 4 remains closed.

Historical audit context: `../PHASE3_ROOT_CAUSE_AUDIT.md` superseded the earlier balanced-fixture completion claim and documented collapse on the original data. The records below preserve those earlier failures; they do not override the final reviewed result or grant Phase 4 permission.

### Earlier remediation diagnostics — completed with failed exit criteria

Authorized 2026-09-13. Full results: `../PHASE3_REMEDIATION_REAUDIT.md`. Completing the diagnostic checklist does not complete Phase 3.

- [x] Read `CYBERMIND_Phase3_Failure_Remediation.pdf`; preserve the original data and independent four-step gate.
- [x] Step 1: run 100 epochs on both original fixtures (400 integration / 1,800 frozen-smoke optimizer updates); selected and last checkpoints fail diversity at all four steps on both.
- [x] Step 2: rebuild identical graphs without centering/scaling; labels/topology unchanged and normalized reprojection error zero. The 100-epoch normalization-off diagnostic completed; outcome is retained for the re-audit.
- [x] Step 3: verify structural recoverability from existing model-visible coordinates. Actual history is 3/observed 2; training-only analytical period discovery succeeds. This diagnostic is excluded from the learned-model gate.
- [x] Step 4 implementation: optional training-only class-balanced StageHead CE; default-off compatibility, validation-weight handling and CPU/CUDA joint gradients verified.
- [x] Step 4 outcome: 100-epoch class-weighting diagnostic completed; selected and last checkpoints fail all four steps.
- [x] Step 5: predeclared CPU learning-rate sweep (0.0001, 0.001, 0.003, 0.01), 100 epochs each, completed; every selected and last checkpoint fails all four steps.
- [x] Re-audit current code: 118 tests passed with zero skips in each of four flag contexts (472 executions); four CPU pipelines, combined CUDA pipeline and both-off/frozen 1e-6 regressions pass. Published all per-step results and preservation evidence.
- [x] This failure was subsequently resolved by the approved periodic input and third-round selection/extension: epoch 185 passes steps 1–4. None of these earlier failed diagnostics is relabeled a pass.

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
