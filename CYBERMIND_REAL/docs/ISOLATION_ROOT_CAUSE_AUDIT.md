# Isolation root-cause audit

The reported rise from **0.749605656 to 0.897041559** is reproduced exactly. The old operation combined an edge cut with arbitrary scaling of normalized node measurements. The increase is driven by that measurement perturbation; the edge cut alone leaves this case's forecast unchanged. The corrected operation removes incident edges and preserves recorded node measurements. It produces **0.749605656 before and after**, not a claimed mitigation benefit.

This is CPU inference using validation-selected epoch 185, test sequence 0, host index 0 (`10.0.0.1`), the same two observed windows, four future steps, four draws and seed 0. No training, checkpoint selection, Phase 3 gate change, or new dataset is involved. The model **passes under the reviewed protocol on synthetic verification data**; this does not establish real-data forecasting or causal intervention efficacy.

## Logged decomposition

| Probe on final observed graph | Final risk, 4 draws / seed 0 | Mean final risk, 512 draws / seeds 0–9 | Mean paired difference from baseline |
|---|---:|---:|---:|
| No action | 0.749605656 | 0.789666373 | 0.000000000 |
| Legacy normalized-feature scaling only | 0.999340355 | 0.907436460 | +0.117770088 |
| Incident edge cut only | 0.749605656 | 0.789666373 | 0.000000000 |
| Legacy scaling plus edge cut | 0.897041559 | 0.903007013 | +0.113340640 |
| Corrected isolation implementation | 0.749605656 | 0.789666373 | 0.000000000 |

Every comparison uses common random draws. With 512 draws, baseline seed means range from 0.760243177 to 0.822594285; legacy combined means range from 0.876643181 to 0.924541235. The increase remains across these paired seeds, so independent stochastic draws cannot explain it. The four-draw display is noisy, and these seed statistics are a numerical sensitivity diagnostic, not calibrated confidence intervals.

The components interact nonlinearly: their effects must not be added. Scaling alone produces a larger risk increase than scaling with the edge removed. Edge removal alone has zero effect for this particular symmetric graph.

## Demonstrated feature-space error

The previous `Isolate Host` path applied `x[host] *= 0.05` to every normalized node column. For a standardized feature, `z=(raw-mean)/std`, this produces `raw_after=0.05*raw_before+0.95*mean`. It moves the measurement toward the training mean. It does not simulate removing 95% of network activity.

| Host 0 feature | Original normalized | Legacy normalized | Reconstructed original raw | Reconstructed legacy raw |
|---|---:|---:|---:|---:|
| bytes_total | 2.584192038 | 0.129209608 | 508.000 | 332.250 |
| bytes_per_flow | 2.584192038 | 0.129209608 | 254.000 | 166.125 |

Only these two normalized columns are nonzero in the affected row. All other raw measurements remain at their original training means under this multiplication; this is not a consistent reconstruction of post-isolation traffic.

The reviewed synthetic representation derives periodic features from normalized bytes_total. Its sine/cosine pair changes from **[0.000006268, -1.000000000]** to **[-0.195090339, -0.980785251]** for host 0 under the old multiplication. Host 1 retains its original pair. The operation therefore also perturbs the synthetic clock representation and breaks the original two-node symmetry.

This establishes a semantic bug in labeling that combined perturbation as isolation. It does not establish that the learned model will respond correctly to a real containment operation, or isolate the periodic feature's causal contribution from every other changed feature.

## Why the corrected edge cut has no effect here

The original graph has two hosts with exactly identical feature rows and one directed edge, 0 to 1. Removing host 0's incident edge changes the observed edge count from **1 to 0** and leaves the node count at **2**. The loaded graph backend is PyG, with self-loops enabled.

Direct instrumentation on the selected checkpoint finds:

- Maximum absolute difference between original and edge-cut graph embeddings: **0.0**.
- Maximum absolute difference between original and edge-cut temporal latents: **0.0**.
- All paired final risks in the logged ten-seed comparison are identical.

Identical node messages plus self-loops explain the invariance in this case: changing which identical messages are averaged does not change their value. This is a limitation of what this fixture can demonstrate. It is not evidence that connectivity never matters to the model, and not evidence that real isolation is ineffective.

## Implemented correction and checks

`mutate_state` now defines host blocking/isolation as an **edge-cut sensitivity probe**: remove incident edges and corresponding edge attributes; retain node measurements, node identities, timestamps, metadata and observed history. It validates supplied host indices. It does not invent unobserved traffic, renormalize measurements, force lower scores, or clip negative risk reductions. The console describes these semantics explicitly.

**12 focused CPU tests passed**, zero skips, covering edge/attribute alignment, input immutability, independent returned tensors, invalid host indices, periodic representation invariance, idempotence, common-history/common-draw UI comparison and existing analyst helpers. The selected checkpoint's exact before/after inference and representation checks are retained separately from the unit tests.

Other simulator actions, such as rate limiting and port blocking, are outside this isolated fix. Their existing feature-space semantics must not be presented as validated physical interventions; the console does not expose them as verified containment actions.

## Judge-facing answer

“The earlier risk increase came from an input-perturbation bug: our isolation probe also shrank standardized measurements toward training averages, changing the synthetic timing signal. We separated the effects and corrected isolation to cut incident edges while preserving observed measurements. On this symmetric synthetic example, the corrected graph produces the same risk, 74.96%, so we show no demonstrated risk reduction. These are model sensitivity simulations, not evidence that isolation causes—or prevents—an attack. Real containment claims require representative data and intervention validation.”

No favorable case was substituted for the reported anomaly. The old output remains preserved. The unchanged-risk result should be shown directly in the demonstration.

## Evidence and checklist

- [x] Reproduce the originally reported numbers: `examples/isolation_audit/before.json`.
- [x] Separate scaling, topology and common-draw stochastic effects: `before.json`, `after.json`.
- [x] Log raw/normalized features, periodic coordinates and edge tensors: both JSON records.
- [x] Confirm corrected selected-checkpoint inference: `after.json`, `after.log`.
- [x] Inspect representation invariance: `representation.json`.
- [x] Verify mutation/UI behavior: `pytest.xml`, `pytest.log`, `tests/test_isolation_semantics.py`.
- [x] Preserve previous Phase 3 and Phase 4 evidence and the original analyst result.

Reproduce the diagnostic with `.phase01-venv/Scripts/python.exe examples/isolation_audit/investigate.py NEW_OUTPUT_NAME.json`. The runner refuses to overwrite existing evidence. Run the focused checks with `python -m pytest tests/test_isolation_semantics.py tests/test_analyst_ui.py -q` with `PYTHONPATH=src`.
