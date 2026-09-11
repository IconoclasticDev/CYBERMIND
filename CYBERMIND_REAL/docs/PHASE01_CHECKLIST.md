# Phase 0–1 execution checklist

Updated 2026-09-11. Verified against the implementation plan; see PHASE01_FINAL_REPORT.md for evidence and limitations.

- [x] 0.1 Training-only fp32 normalization, stored constants and inference verification.
- [x] 0.2 Packet statistics, scan signatures and retransmissions.
- [x] 0.3 Five named stages plus Benign and Unknown/Ambiguous.
- [x] 0.4 Chronological environment chaining and disjoint temporal splits.
- [x] 0.5 Automatic gradient, attention and occlusion explanations.
- [x] 0.6 Training-derived class weighting and binary window targets.
- [x] 0.7 Graph consistency regularization.
- [x] 0.8 Stochastic dynamics and multiple forecast rollouts.
- [x] Phase 0 smoke-test exit criterion.
- [x] 1.1 Full CIC-IDS2018 primary policy; other corpora held out.
- [x] 1.2 Full-width GB10 bf16 joint-training config.
- [x] 1.3 Validation F1 checkpoint selection and early stopping.
- [x] Final regression: 34 tests passed, including full-width bf16 CPU backward.
- [x] Final synthetic build/preparation/training/evaluation integration: four steps passed, 25 explained evaluations.
- [x] Final plan recheck and readiness handoff documented.
- [ ] Phase 2 — intentionally unstarted.

**Signal: GO for Phase 2 preparation/preflight. Training is conditional on real, complete packet-enriched data and a successful GB10 preflight/memory check.**
