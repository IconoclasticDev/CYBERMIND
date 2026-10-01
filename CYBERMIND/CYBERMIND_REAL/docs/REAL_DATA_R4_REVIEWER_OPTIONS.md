# R4 reviewed resets and unresolved-transition options

Date: 2026-09-20. Scope: evidence requested after acceptance of the first R4
failure. This document preserves the analysis supplied for the decision.

Reviewer outcome, 2026-09-20: option (c) was authorized; options (a) and (b)
were rejected. Option (c) is now implemented and audited in
`REAL_DATA_R4_OPTION_C_AUDIT.md`. No second training attempt has started.

## 1. Three externally supported campaign resets

A separate derivative, `data/processed_real_chunk_r4_reviewed_resets`, was
created from the frozen R2 tensors. `campaign_reset: true` is declared only at
the destination state after these reviewed boundaries:

| Campaign | Corrected-rule end | Source → destination window starts | Split | CRF transition occurrences covered |
|---|---|---|---|---:|
| FTP-BruteForce | 2018-02-14 16:10:31 UTC | 16:10:12.813819 → 16:10:42.813819 | train | 3 |
| SSH-BruteForce | 2018-02-14 19:32:30 UTC | 19:32:12.813819 → 19:32:42.813819 | train | 15 |
| Botnet Ares | 2018-03-02 19:54:52 UTC | 19:54:42.830365 → 19:55:12.830365 | test | 15 |

Each declaration cites the pinned
[Distrinet corrected-rule notebook at commit f0ce502](https://github.com/GintsEngelen/CNS2022_Code/blob/f0ce502818e59e6cd062720ab2286c5ff6f2bdec/Labelling/CICIDS2018_labelling_fixed_CICFlowMeter.ipynb),
the local file `data/real_chunk/rules/Distrinet_CICIDS2018_fixed_f0ce502.ipynb`,
its SHA256
`e58bea8651f4c891383f3cf1e735de4b48f50c4ec8a9aef078b53972dca1422e`,
and the R4 reviewer decision dated 2026-09-16.

The identity audit compares every sample and state. Node tensors, edges, edge
features, labels, timestamps, sample structure, normalization, and all existing
metadata are unchanged. The only additions are the ten reset-provenance keys at
the three authorized destination timestamps. Because 16-state histories
overlap, those three physical states occur 19 times in train and 16 times in
test. This does not represent 35 different reset boundaries.

The unchanged transition audit now reports:

| Split | Illegal occurrences | Unique illegal boundaries |
|---|---:|---:|
| train | 91 | 7 |
| validation | 0 | 0 |
| test | 0 | 0 |

The two February 14 and one March 2 physical boundaries are now covered. No
March 1 reset was declared. The R4 config points to this derivative so a future
reviewed run cannot silently fall back to the reset-free R2 files; this is setup
only and does not authorize execution.

## 2. Concrete choices for the seven untouched March 1 boundaries

### Option (a): campaign-state targets

This would redefine the stage target from “a matching attack flow is present in
this 60-second window” to “the externally declared campaign stage is active in
this window,” at least when no matching attack flow is observed. The source of
the active interval would have to be the pinned corrected rules, never a target
reversion or model output.

Concretely it requires:

- adding an authoritative campaign-interval/stage annotation to preprocessing,
  most naturally in `scripts/prepare_data.py` before graph construction;
- changing `build_graph_state()` in `src/cybermind/data/graph_builder.py` to use
  that annotation when constructing `y_stage`;
- deciding whether `y_infiltration` remains observed-flow presence. If it does,
  some windows will intentionally have `y_infiltration=0` and non-Benign
  `y_stage`; changing it too would alter both detection targets and class
  weights;
- regenerating and re-auditing R2-derived train/validation/test files, stage
  counts, checkpoint inputs, R3 evidence, and R4 preflight hashes.

This would change more than the seven failing edges. Every otherwise-Benign
window inside the Dropbox and NMAP intervals could acquire a campaign-stage
target. It converts the target into campaign-state weak supervision and may
label quiet periods as active attack stages. Features and normalization need
not change, but dataset hashes and stage cross-entropy supervision would.

### Option (b): non-monotonic CRF policy

This would permit selected backward transitions, such as Reconnaissance→Benign
and Initial Access→Benign, without a reset. The coherent implementation is to
change `transition_matrix` in `knowledge/stage_mapping.yaml`; `StageDecoder`
uses that matrix for both CRF normalization/training and Viterbi decoding.

Concretely it requires:

- defining whether only the observed 1→0 and 2→0 edges become legal or whether
  all attack-stage regressions become legal;
- updating the transition policy, exhaustive CRF tests, adversarial decoding
  tests, transition metrics, Phase 2 claims, R3/R4 audits, and any UI wording
  that describes forward-only kill-chain decoding;
- repeating checkpoint compatibility and synthetic Phase 3 regression checks,
  because the learned partition function and decoded paths both change.

This changes model and exit-gate semantics globally. A decoded regression would
no longer count as illegal under the same policy, including on future datasets.
It therefore resolves the present exception by weakening the monotonic
kill-chain constraint rather than changing labels. Making only the training
target legal while leaving it outside the decoder support would not be a valid
CRF likelihood and is not a coherent sub-option.

### Option (c): disclosed CRF-loss boundary exclusions

This would retain every `y_stage`, stage cross-entropy target, transition matrix,
Viterbi rule, and illegal-transition evaluation rule. Only the seven named
physical March 1 destination boundaries would be excluded from the structured
CRF transition loss.

Concretely it requires:

- adding explicit provenance metadata such as `crf_transition_loss_excluded`
  only at the seven reviewed destination timestamps;
- extending `batch_loss()` and `StageDecoder.forward()` to accept a separate
  transition-loss boundary mask. The existing `mask` cannot represent an
  interior omission because it only accepts contiguous prefixes;
- treating each excluded edge as a segment break for CRF NLL, so the left and
  right contiguous portions remain valid CRF sequences without inventing a
  campaign reset;
- reporting both seven unique exclusions and their 91 repeated training
  occurrences caused by overlapping histories, with tests that prove stage CE
  still includes those destination windows and inference remains unchanged.

This is the narrowest data effect: no relabeling and no inference-policy change.
It reduces structured supervision at seven physical boundaries and creates a
dataset-specific loss exception. The final disclosure would need to state that
monotonicity was not trained across those seven edges, even though the decoder
still enforces monotonicity at inference. It must not be represented as an
external campaign reset.

This was the pre-decision status. The subsequent option-(c) implementation,
whole-corpus transition audit, focused loss tests, and hashed full-suite run are
recorded in `REAL_DATA_R4_OPTION_C_AUDIT.md`. Explicit reviewer authorization is
still required before another R4 launch.

## 3. Independent provenance checks

### R0 manifest

`data/manifests/r0_real_chunk_files.csv` has SHA256:

```text
4356fb4616ad63cbad87e75e5e57ca5288568fc6b31f13cd70f1445328388b66
```

This exactly matches the supplied Antigravity value. No manifest diff is
required.

### Earlier “203 passed, 13 skipped” statement

The run is traceable to the Codex execution transcript at:

```text
C:\Users\as030\.codex\sessions\2026\09\16\rollout-2026-09-16T18-15-48-01a0aa40-7d6a-76c0-9e45-faad8d2f81e4.jsonl
```

The successful command was:

```powershell
$env:PYTHONPATH='src'; .\.phase01-venv\Scripts\python.exe -m pytest -q
```

It ran from the project root immediately before commit `d631d32` and reported
`203 passed, 13 skipped, 41 warnings in 17.21s`. An earlier invocation without
`PYTHONPATH` failed collection with two errors.

**The successful run is not traceable to a contemporaneously hashed test
artifact.** No repository pytest log, JUnit XML, manifest entry, or SHA256 was
created for it. The current `.pytest_cache` is cumulative and cannot establish
those totals. The suite was not rerun to recreate matching numbers.

## Status

R4 remains stopped. Its exit criterion is not met, and no second training run is
authorized or running.

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**
