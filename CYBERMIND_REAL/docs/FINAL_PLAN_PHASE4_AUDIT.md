# Phase 4 audit — COMPLETE (2026-09-14)

Phase 4 exit criteria met within the implementation plan’s laptop preparation scope. User authorization covers Phase 4 and parallel Tracks A/B; Phase 5 has not begun. No exit gate or reviewed tolerance has been loosened.

## Checklist and evidence

| Item | Status | Evidence |
|---|---|---|
| 4.4 PCAP availability, checked first | Complete | `examples/phase4/packet_availability/availability.json` and source listings |
| 4.1 Four ablation configs and reviewed selection | Complete; configuration assertions pass | `configs/gb10_{full,edge_only,crf_only,baseline}.yaml`; `tests/test_phase4_readiness.py` |
| 4.2 Full architecture, tiny-batch laptop GPU preflight | Complete; all four pass on RTX 5060 | `examples/phase4/preflight/*.json` |
| 4.3 Transition and suspicious-edge attention diagnostics | Complete; actual checkpoint evaluated | `examples/phase4/attention/eval_*.json` |
| 4.5 CTU-13 access and limitations | Complete | `docs/PHASE4_CTU13_ACCESS.md` |
| Track A benchmark/FPR/feature coverage | Implemented and CPU verified | `examples/track_a_benchmark/selected185/comparison.md` |
| Track B analyst UI | Implemented; AppTest and browser verified | `docs/TRACK_B_ANALYST_UI_AUDIT.md` |
| Joint regression and historical evidence preservation | Complete; 189 tests, no skips | `examples/phase4/regression/verification.json` |

## Data readiness

Ten publicly accessible primary PCAP archives total **477,321,665,202 bytes** (477.32 decimal GB), with archive dates covering all ten processed CSV dates. Those CSVs total **6,886,649,507 bytes**. Metadata listings and HEAD responses were inspected, not corpus payloads. Nine archives are ZIP and one is RAR. Extraction size, integrity after download and actual label/packet alignment remain unverified. The source registry documents public access: [AWS registry](https://registry.opendata.aws/cse-cic-ids2018/), [CIC dataset description](https://www.unb.ca/cic/datasets/ids-2018.html).

Primary feature-complete data is **not ready**. A verified timestamp/endpoint/ground-truth join from the original PCAPs to labeled CIC events remains unresolved. Generic filename labels from `pcap_to_corpus.py` do not satisfy that requirement. Full acquisition stays in Phase 5 on GB10. Preparation now rejects incomplete packet measurements before graph construction, retaining `require_packet_features: true`.

## Interpretation to carry into submission

Phase 3 **passes under the reviewed protocol on synthetic verification data** at selected epoch 185. Evaluated epochs 98 and 200 fail step 1. This is a narrow demonstrated passing result, not a stable plateau or verified real-data forecasting capability.

The corrected one-step benchmark uses only observed history and predicts the unseen final window. At threshold 0.5, the feature-matched periodic logistic baseline and selected world model both achieve synthetic F1 1 and FPR 0. This does not support a superiority claim. Feature coverage parity still leaves architectural differences: pooled logistic inputs discard topology.

The analyst UI shows four future steps for the reviewed checkpoint, with named stages, uncertainty, transition legality, explanations and provenance. Host-isolation comparisons are model-space sensitivity probes. In the verified case, isolation increases predicted risk; the UI does not invent a beneficial recommendation. Port blocking is unavailable because its existing normalized-feature semantics are not defensible.

## GPU preflight evidence

Actual NVIDIA GeForce RTX 5060 Laptop GPU: 8,518,041,600 bytes of reported device memory. All runs used the full 512-wide, six-layer configured model, bf16 precision, history 16, batch one, three nodes and four edges per window, with 34 node and 27 edge columns. Each performed the actual multi-task loss and backward pass. Finite, nonzero gradients were verified for required model groups and independently for both enabled edge projections and the CRF.

| Config | Edge / CRF | Loss | Peak allocated bytes | Peak reserved bytes | Result |
|---|---|---:|---:|---:|---|
| baseline | off / off | 3.722842 | 291312128 | 318767104 | PASS |
| edge_only | on / off | 3.833838 | 293081600 | 320864256 | PASS |
| crf_only | off / on | 14.525350 | 291314176 | 318767104 | PASS |
| full | on / on | 15.155413 | 293083648 | 318767104 | PASS |

These are architecture execution checks, not model training experiments or production graph/batch/optimizer memory certification. The regular production preflight was run separately and returned the expected failure for five missing real-data artifacts; see `preflight/production_readiness.json`. The synthetic mode cannot serve as production approval.

## End-to-end diagnostics

The selected epoch-185 checkpoint was evaluated on its original 25 test sequences. The existing supervised metric uses one unseen target window per sequence, so one-step classification and 25 transition pairs are reported; the established four-step Phase 3 gate is preserved separately. Illegal transitions: **0/25**. Both diagnostic runs retain F1 1 and FPR 0 on this synthetic split.

The heuristic selects an observed non-self edge when reconstructed raw bytes meet the specified threshold OR its aggregate port is outside the declared common-port set (22, 53, 80, 123, 443, 3389, absolute tolerance 0.001). Training normalization is inverted before selection. Automatic self-loops are excluded. Weights are pooled equally across selected edge occurrences, heads and both layers; repeated windows in overlapping histories count again. No target graph or label is used.

| Diagnostic setting | Observed graph/edge occurrences | Selected edge occurrences | Coefficients | Mean attention | Status |
|---|---:|---:|---:|---:|---|
| Default 1 MiB | 50 / 50 | 0 | 0 | null | No matching edges |
| Explicit synthetic 512 bytes | 50 / 50 | 45 | 360 | 0.5 | Available |

The second threshold exercises the diagnostic on small synthetic values; it does not replace or loosen a diversity/legality gate. Both layers return mean 0.5 in this symmetric fixture. This demonstrates measurement plumbing, not preferential attention to attacks. The default no-match result is preserved rather than presented as zero attention. Disabled edge features and missing normalization are reported explicitly with null measurements. Focused tests check raw-scale selection, self-loop exclusion, exact coefficient pooling, both PyG and dense backends, unchanged forward outputs and unchanged RNG state.

## Verification and changes

- Full suite: **189 passed, zero skipped**, including actual CPU/CUDA tests and all four flag combinations. Initial run found two obsolete unit assumptions: plain `val_f1`, and seven-column/CRF-disabled synthetic input for the now-enabled full config. Those tests were updated to assert the explicitly authorized policy and actual 34/27-column architecture, retaining the original finite-backward requirement. Initial failure logs/XML remain preserved. No Phase 3 exit gate was changed.
- Fresh both-off synthetic pipeline and frozen checkpoint evaluation match all original fields within 1e-6. All 49 Phase 0 evidence files and 764 Phase 3 evidence/tensor/checkpoint entries are unchanged (813 total).
- Preparation now rejects missing, nonfinite or unavailable packet features before graph creation, including falsely claimed availability when canonicalization would otherwise fill missing columns. Legacy flag-off behavior remains compatible.
- All four configs differ only in the two ablation flags. Reviewed tolerance remains exactly 0.05; validation stage CE is the tie-breaker. `min_delta` is zero as required by the reviewed rule. No periodic synthetic-coordinate transform was added to GB10.
- `train.py --run-name` isolates selected/last checkpoint and history names without introducing non-flag config differences. See `PHASE4_GB10_HANDOFF.md` for later commands and resume requirements.
- Analyst UI AppTest passed after final dataset-hash/horizon-aware cache invalidation. Prior browser layout verification and the final CPU execution log are retained with the Track B evidence.

## Final verdict

**Phase 4 exit criteria met.** Tracks A and B implementation/verification are complete in the documented synthetic/local scope. Real-data benchmark scores, operational analyst validation, corpus acquisition/enrichment and production training remain unestablished. The unresolved label/packet join and missing real tensors prevent starting a defensible GB10 training run. Phase 5 has not begun and requires separate user authorization.
