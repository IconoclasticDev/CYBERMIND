# Track B — Analyst UI audit

Status: implemented and verified on CPU with the reviewed synthetic checkpoint. Phase 3 **passes under the reviewed protocol on synthetic verification data**. This UI does not establish real-data accuracy, causal intervention effects, or stable training behavior: the surrounding evaluated epochs 98 and 200 fail step 1 while the selected epoch 185 passes.

## Completed checklist

- [x] Replace numeric-stage skeleton with a three-column observed network, future forecast and intervention view.
- [x] Present step zero separately from four future windows; named coarse stages, risk, stochastic rollout SD, declared resets and transition legality are independently visible.
- [x] Show observed network connectivity with safely escaped host identifiers; cap rendering at 80 hosts and disclose truncation.
- [x] Compare host isolation with No Action using identical observed history, forecast horizon, rollout count and random seed. Preserve original states. No network action is executed.
- [x] Show measured risk reductions, including negative effects. Do not manufacture a recommendation when no tested action helps.
- [x] Compute feature sensitivity, temporal attention and occlusion explanations on demand using the existing model implementation.
- [x] Export a JSON case record with checkpoint and dataset SHA-256, epoch, selection policy, sequence, normalization fingerprint, forecasts, simulations and explanations.
- [x] Invalidate simulations and explanations when checkpoint, dataset contents, horizon or sequence changes. Exclude held-out target from inference.
- [x] Verify real Streamlit workflows using AppTest, actual checkpoint loading and CPU inference; exercise missing-checkpoint guidance.
- [x] Verify helper tests for illegal transitions versus declared reset/Unknown, same-history intervention comparison and immutability, and graph-label escaping/truncation.

## Evidence

`examples/track_b_analyst_ui/verification.json` records the actual epoch-185 case and successful AppTest actions. Three helper tests pass with `PYTHONPATH=src .phase01-venv/Scripts/python.exe -m pytest tests/test_analyst_ui.py -q`.

The recorded case has final model risk **0.749605656**. Simulated isolation of host `10.0.0.1` increases it to **0.897041559**, a reduction of **−0.147435904**. The console correctly retains No Action as the lower-risk comparison. These values are sensitivity results on synthetic input, not mitigation efficacy. The five rows cover Now plus steps 1–4, with zero illegal transitions for this case; this single UI case is not a replacement for the across-sequence Phase 3 gate.

Run the console from the project directory:

```powershell
$env:CYBERMIND_CHECKPOINT = (Resolve-Path examples/phase3_third_round/extended200/checkpoints/combined.pt).Path
$env:OMP_NUM_THREADS = '2'
.\.venv\Scripts\python.exe -m streamlit run scripts/app.py --server.address 127.0.0.1 --server.port 8511 --server.headless true --browser.gatherUsageStats false
```

The default production checkpoint remains `checkpoints/best_gb10.pt`; absent files produce guidance and no invented forecasts. Streamlit is already present in `.venv` and declared in `requirements-full.txt`. The CPU smoke environment does not contain Streamlit; AppTest used `.venv` on CPU.

## Scope and remaining limitations

The network map is observed topology, not an attributed attack path. Only host isolation is exposed: existing port-block mutation compares a normalized edge feature directly to a raw port, so it is not a defensible analyst action until raw-port semantics are implemented and verified. Existing isolation scales normalized features and removes incident edges; this is clearly presented as a model-space sensitivity probe. It is not asserted to simulate physical containment faithfully.

No live telemetry ingestion, operational control integration, analyst authentication, real-data validation or submission-ready performance claim is established. Explanations are computed on demand; running them over very large graphs may be slow. Checkpoint/data loading currently occurs per rerun and is intended for local inspection, not a production multiuser deployment.

Browser visual verification on localhost: observed network, forecast chart and analyst controls rendered successfully at 1280×720 in the in-app browser. The graph displayed the two actual observed hosts and their edge. AppTest covers interactions; this is not a multi-device responsive/accessibility certification.
