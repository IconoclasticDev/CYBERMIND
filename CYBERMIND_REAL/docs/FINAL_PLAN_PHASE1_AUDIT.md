# Final implementation plan — Phase 1 audit

Date: 2026-09-12. Status: complete. Phase 2 has not started and requires user approval.

## Changes and resulting behavior

Both PyG `GATv2Conv` layers now receive the configured edge width and supplied edge attributes when `model.use_edge_features` is true. The dense fallback independently projects edge attributes into attention scores in each of its two layers, so the fallback also uses the new signal.

`WorldModel.encode_state` forwards `state.edge_attr`; single-sequence, batched-sequence, and forecast paths all reach that method. The flag defaults to false, including an explicit entry in `configs/smoke.yaml`. Disabled models create no extra parameters and retain the original initialization sequence and attention operations.

The graph builder was inspected without modification. Its actual output is `[E, 27]`, float32: seven original flow columns plus twenty packet-derived columns. The old Phase 0 synthetic fixture has seven columns. Training infers the width from the input graphs, validates any explicit configured width, and saves the enabled architecture in the checkpoint. Evaluation, app, counterfactual, visualization, and teacher-export model loading now recover these settings. This changes checkpoint construction only; no ONNX export or UI end-to-end validation is claimed here.

Enabled mode validates attribute shape, floating dtype, and device. Explicitly omitted attributes (`None`) retain node-only attention for that call, as allowed by the plan's optional argument. Disabled mode ignores attributes, including an unused configured width. Dense edge conditioning changes relative incoming-edge weights; a destination with only one incoming edge has a constant softmax, so the gradient fixtures deliberately contain competing incoming edges.

## Exit matrix

All eight combinations passed on the actual laptop runtime: CPU/CUDA × PyG/forced fallback × flag off/on. No matrix test was skipped. Each combination independently checked `encode_state`, `forward`, and `forward_batch`, finite test objectives, finite backward gradients, and edge perturbation behavior. The batch contains two sequences of two three-node graph windows, each with six directed edges and 27 edge attributes.

Representative enabled-mode gradient evidence from `forward_batch` (L1 norms):

| Device | Backend | First edge projection | Second edge projection |
|---|---|---:|---:|
| CPU | PyG | 94.139404 | 54.166313 |
| RTX 5060 CUDA | PyG | 94.139404 | 54.166298 |
| CPU | Dense fallback | 51.648800 | 92.269310 |
| RTX 5060 CUDA | Dense fallback | 51.648788 | 92.269310 |

Both enabled projections had nonzero finite gradients in all three model entry-point checks. Disabled cases had finite, nonzero graph gradients and no edge-projection parameters. Changing edge attributes changed enabled embeddings substantially (maximum changes about 0.507 for PyG and 2.079 for fallback), while disabled embeddings remained equal apart from CUDA reduction rounding.

Evidence: `examples/phase1_edge_attention/execution_matrix.json` and `pytest.xml` contain per-case losses, gradient norms and perturbation differences.

## Regression and integration checks

- Full suite: **69 passed, zero skipped** (34 existing tests plus 35 new attention/config tests). Warnings were recorded; the main source is existing PyG/Python 3.14 typing deprecations.
- Compared against the actual pre-change encoder source from commit `1d91b27`, not another instance of the modified implementation. Parameter names and initial values match exactly for both backends. CPU outputs and CUDA fallback outputs match bitwise. CUDA PyG's largest observed difference was `2.3841858e-7`, within the `1e-6` absolute/relative tolerance.
- Loaded the frozen Phase 0 checkpoint and evaluated it on CPU. The complete evaluation report matches the frozen report within `1e-6`, including per-sample explanations. All 49 frozen Phase 0 evidence-file hashes remain unchanged.
- Ran a separate one-epoch edge-enabled CPU smoke training and evaluation. Training loss was finite (`0.9181556587`). The run YAML omitted the edge width, training saved width seven from the legacy synthetic fixture, and evaluation successfully recovered it from the checkpoint. This is a checkpoint-wiring test, not a real-data performance result. Its isolated worker count is zero; the normal laptop smoke config retains eight workers.
- Malformed attributes, empty edges, optional missing attributes, invalid dimensions, checkpoint mismatches and disabled-mode compatibility have focused test coverage.
- `git diff --check` passed. Independent review found no blocking issue in checkpoint reconstruction or legacy behavior.

The first verification probe omitted the existing canonical preprocessing step; the probe was corrected without modifying the graph builder. The first full test run had one overly strict bitwise-equality assertion for CUDA PyG (68 other tests passed). It was corrected to the documented floating-point tolerance; the initial log is retained as `pytest_initial_strict_equality.log`. Model behavior was not altered to hide a failure.

## Scope and limitations

No CRF/stage-decoder work, combined-feature integration, ablation matrix, GB10 configuration edits, large dataset acquisition, or real training was performed. No improvement in detection accuracy/FPR is claimed. PyG and fallback are separate attention implementations and are not expected to have identical predictions or interchangeable checkpoints. Resuming an enabled training checkpoint requires its corresponding enabled run configuration.

The remaining Phase 1 changes are tests, reproducible verification tooling, source/result checksums, and local temporary/output ignore rules. This audit, implementation, and evidence form the local Phase 1 commit; nothing is pushed remotely.

## Next approval gate

Phase 1 exit criteria are satisfied. Request approval for Phase 2: kill-chain-constrained stage decoding. Do not start it until the user approves.
