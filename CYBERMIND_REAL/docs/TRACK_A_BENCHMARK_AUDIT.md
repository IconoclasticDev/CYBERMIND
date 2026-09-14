# Track A benchmark audit

Status: completed on the reviewed synthetic verification dataset. Phase 3 **passes under the reviewed protocol on synthetic verification data**; this table is a one-step infiltration comparison and does not re-certify the four-step stage gate.

## Completed checklist

- [x] Correct the baseline input protocol to observed `states[:-1]` only; predict the unseen final-window label instead of any-positive whole-sequence labels.
- [x] Fit scaling and logistic regression using training sequences only; keep the probability threshold fixed at 0.5.
- [x] Include FPR and confusion counts, including single-class fallback; FPR is null when no negatives exist.
- [x] Compare node-only, node-plus-edge and exact periodic-feature coverage settings against the selected world model on identical targets.
- [x] Retain input/checkpoint hashes, protocol and feature registry, sample-level probabilities, counts and limitations.
- [x] Verify focused baseline and analyst helper tests (14 passed before joint regression).

## Actual results

See `examples/track_a_benchmark/selected185/comparison.md` and `comparison.json`. The 25 test targets comprise 19 negatives and six positives.

| Inputs / model | TP | FP | TN | FN | F1 | FPR | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic, raw node columns | 0 | 0 | 19 | 6 | 0 | 0 | 0.328259 | 0.552632 |
| Logistic, raw node and edge columns | 0 | 0 | 19 | 6 | 0 | 0 | 0.328259 | 0.552632 |
| Logistic, node/edge plus same two periodic columns | 6 | 0 | 19 | 0 | 1 | 0 | 1 | 1 |
| Selected world model, epoch 185 | 6 | 0 | 19 | 0 | 1 | 0 | 1 | 1 |

The feature-matched baseline ties the world model. An apparent advantage over the raw-feature baselines disappears once the approved synthetic periodic representation is supplied to both. No superiority claim is supported. Node/edge column coverage is matched, but logistic pooling discards graph topology; architecture and representation capacity are not identical.

Historical whole-sequence baseline figures remain preserved and are not directly comparable to the corrected forecasting protocol. This work supplies a reproducible comparison path and honest synthetic evidence. A real-data scoring benchmark remains unmeasured pending corpus preparation and actual training. The synthetic periodic transform is not enabled in GB10 configs.

To reproduce without overwriting evidence:

```powershell
.phase01-venv/Scripts/python.exe scripts/benchmark_compare.py --checkpoint examples/phase3_third_round/extended200/checkpoints/combined.pt --output-dir examples/track_a_benchmark/new_comparison
```

Implementation: `scripts/run_baseline.py`, `scripts/benchmark_compare.py`, `src/cybermind/baselines/{logistic,protocol}.py`; tests: `tests/test_baseline_protocol.py`. No new model training, GPU work or downloads were needed for this track.
