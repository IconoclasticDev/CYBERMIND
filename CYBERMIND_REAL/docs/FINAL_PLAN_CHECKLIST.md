# Final implementation plan — execution checklist

Source: `C:/Users/as030/Downloads/CYBERMIND_Final_Implementation_Plan.pdf`.
This tracks the NEW final plan's phase numbering, independently of older repository reports.

## Authorization and scope

- Phase 0 authorized on 2026-09-12: proceed according to the PDF.
- Full CIC-IDS2018 acquisition is deferred to Phase 5 on GB10, as the user explicitly corrected.
- Phase 0 downloads only MITRE ATT&CK, CAPEC, and an NVD snapshot.
- Verify CTU-13 access now; no heavy corpus download on the laptop.
- Audit each completed phase and request approval before starting the next.
- Phases 1 and 2 authorized on 2026-09-12. Phases 3–4 require separate approvals. Phases 5–8 are outside this implementation request.
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

## Phase 2 — COMPLETE (awaiting Phase 3 approval)

- [x] 2.1 Define forward/stay transitions, destination-declared resets to 0/1, and unrestricted Unknown/Ambiguous transitions in the YAML policy.
- [x] 2.2 Implement fp32 masked linear-chain CRF and Viterbi decoder, with persisted policy buffers and strict supervision validation.
- [x] 2.3 Add optional, separately logged CRF loss alongside existing cross-entropy; use explicit `campaign_reset` metadata.
- [x] 2.4 Integrate decoded stages in evaluation, app, forecasts and rollouts; checkpoint loaders preserve the CRF flag.
- [x] 2.5 Add illegal-transition counts/rate and pool within-sequence pairs without crossing scenario boundaries.
- [x] 2.6 Verify finite loss/gradients, adversarial legal decoding, and flag-off path on CPU/GPU: 94 tests passed, zero skips; all six CPU/GPU exit checks passed. One-epoch CRF checkpoint trained and reloaded; all 49 frozen baseline files unchanged.
- [x] Audit exit criteria in `FINAL_PLAN_PHASE2_AUDIT.md`; present Phase 3 approval request. Phase 3 remains unauthorized until the user approves.

## Phase 3 — NOT AUTHORIZED

- [ ] 3.1 Run tests and integration for all four feature-flag combinations.
- [ ] 3.2 Compare both-off results with the preserved Phase 0 baseline.
- [ ] 3.3 Run combined two-epoch smoke, verify finite loss, VRAM ceiling, and nondegenerate predictions.
- [ ] Check explicit reset metadata in integration fixtures and report Unknown-stage usage alongside prediction diversity.
- [ ] Resolve document inconsistency: constrained decoder should have zero illegal transitions; measure prediction diversity separately rather than requiring illegal transitions.
- [ ] Audit exit criteria; request Phase 4 approval.

## Phase 4 — NOT AUTHORIZED

- [ ] 4.1 Prepare baseline, edge-only, CRF-only, and combined GB10 configs.
- [ ] 4.2 Run tiny-batch GPU preflight for all four configs on laptop.
- [ ] 4.3 Report transition and suspicious-edge attention diagnostics end to end.
- [ ] 4.4 Establish definite PCAP/packet-feature availability for strict primary-corpus preparation.
- [ ] 4.5 Document CTU-13 access status and any evaluation risk.
- [ ] Audit all exit criteria and stop at the end of Phase 4.
