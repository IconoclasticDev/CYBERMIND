# CYBERMIND — complete session context and continuation handoff

Prepared before the requested directory copy/archive on 2026-09-11.

This document captures the user-visible requests, recovered shared-chat context,
decisions, source changes, verification evidence, and remaining work from this
session. It is a detailed reconstruction from the conversation and inspected
files, not an export of hidden reasoning or an exact transcript of every tool
call. Literal source documents and current reports are appended below so a new
session can inspect the underlying requirements rather than relying on summaries.

## 1. Current objective and immediate delivery order

The latest user request is:

> make a copy of this whole directory, zip it and store it on D:\Abhinav\College\SIH. Generate the whole context of the entire session. Give priority to the the context part the copy part do it after you have a .md file of the complete context ready

Required order: finish this Markdown context file first, then copy the entire
workspace directory and ZIP the copy into the requested D: destination. Include
both top-level project directories, hidden files, virtual environments, caches,
tests, artifacts and this context file. No exclusions based on `.gitignore` apply
to this filesystem backup. Preserve the original directory. Do not overwrite a
pre-existing backup; use a unique destination name. A backup verification report
and ZIP SHA-256 should describe actual completion after the archive exists.

At the time this context is written, the copy/archive has **not yet been made**.
Consult the backup verification JSON next to the delivered ZIP for its eventual
status, file counts and checksum. Do not interpret this paragraph as a claim that
the backup succeeded.

## 2. Workspace and environment

- Original workspace: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE`.
- Active code project: `CYBERMIND_REAL` within that workspace.
- Also present: `multisource_audit`, a separate pre-existing audit tree. It was
  not the target of the implementation changes but belongs in the whole-directory copy.
- Shell/host: Windows PowerShell; local system reports Windows 11, AMD64.
- Time zone supplied to this session: Asia/Calcutta.
- Requested backup destination: `D:\Abhinav\College\SIH`.
- Tested Python executable: `CYBERMIND_REAL\.phase01-venv\Scripts\python.exe`.
- Local runtime observed: Python 3.12.14; PyTorch `2.14.0+cpu`; PyG `2.8.0.post1`.
- Runtime encoder check: `HAS_PYG = True`, `conv1 = GATv2Conv` locally.
- No real GB10 connection, CUDA build, available training slot, or real primary
  corpus was supplied during this session.
- The workspace is not a Git repository. No project Git initialization, commit,
  remote setup or push was performed.
- Windows virtual environments/caches may contain machine-specific paths. Copying
  them does not turn the package into a Linux/aarch64 GB10 runtime; recreate the
  environment on the target host.

The filesystem sandbox allows writes in the workspace but D: writes require an
execution approval. User intent already authorizes the backup; any tool approval
for that path is an environment restriction, not a request to reconfirm the task.

## 3. User requests, in chronological order

### Request 1: recover prior conversation and continue

User supplied:

- Shared chat: <https://chatgpt.com/s/cx_6aa38eee2fa081918d99307e55d359e7>.
- Plan: `C:\Users\as030\Downloads\CYBERMIND_Implementation_Plan.md`.

User request:

> get all the details from this chat, check till where the work has been progressed and continue the execution from there and at the end as mentioned in the chat link give me a final report of what has been done

The user explicitly distinguished document contents from their own request.
The plan was treated as requirements/context, not as independent permission for
new external actions or all later phases.

### Request 2: report against the GB10 checklist

User supplied `C:\Users\as030\Downloads\GB10_Verification_Checklist.md` and asked:

> report to me whatever is done according to the md file

This was handled as a read-only verification/reporting task. No installs or
training were undertaken in that pass. The report distinguishes local code
verification from actual GB10 execution, and gives PASS/FAIL/UNKNOWN per item.

### Request 3: immediately fix findings 3.1 and 3.2

User identified the still-stale README/launcher commands and artifact ignore
rules, and requested immediate fixes. Their central requirements were:

> the README's legacy command blocks are still there ... run_training_from_zero.sh, launch_training.py, and one_click_train.py all still default to configs/gpu_128gb.yaml, not gb10_full.yaml ... Edit or delete these blocks

> .gitignore still excludes *.pt and results/*.json/*.png ... Decide your submission strategy now: either drop those ignore lines before your first commit, or explicitly plan to force-add the specific final checkpoint/results files ... (fix these immediately)

Both were fixed in source/documentation, verified, and recorded as resolved at
the top of the original checklist report. The historical FAIL sections remain
below that update as an audit snapshot, not current unresolved findings.

### Request 4: context first, full directory copy and ZIP second

This is the current request, quoted in section 1. The backup scope is the entire
top-level workspace, not only `CYBERMIND_REAL` or only Git-trackable files.

## 4. Recovered shared-chat scope and progress

Web retrieval initially failed with a cache-miss/internal error. The browser
skill was read and used to open the supplied URL in the Codex in-app browser.
The visible page title was **Execute implementation plan phase 1**. Expanding
the “Worked for 9m 17s” section exposed the prior progress messages.

The prior user's visible instruction was:

> Start executing everything mentioned in the implementation plan mentioned above as it is and complete till phase 1 as soon as you reach phase 2 stop the working. Use subagents and continously update on what part of the implementation plan is completed like a check list and before stopping execution after work up till phase one is completed recheck all the mentioned things in the implementation plan and then give me a signal that I can proceed with the nvidia blackwell gb10 training which is the phase 2

The shared view contained that user request and expanded progress, but no final
completed response. Do not claim access to additional hidden/unshared messages.
It reported that earlier subagents had handled data/model work; this continuation
did not spawn additional subagents.

Last visible prior progress:

- Packet extraction/seven-label taxonomy: 9 tests passed.
- Loss gradients, weighting, validation and split checks: 5 tests passed.
- A two-epoch synthetic CPU training run completed with validation checkpoints
  and separate loss logs.
- Normalization/chaining tests and explanation/forecast integration were pending.
- Final checklist and GB10 handoff were pending.

This established the boundary: complete/recheck Phases 0–1 and stop before real
Phase 2 training. Later reporting and maintenance requests did not authorize
launching Phase 2. Synthetic correctness training was permitted within Phase 0.

## 5. Plan and project intent

CYBERMIND is a predictive cyber-defence world-model project aligned to SIH26153.
Its pipeline uses host communication graphs, a graph encoder, temporal
Transformer, latent stochastic dynamics, infiltration and stage heads, and
counterfactual explanation/simulation. The goal is better precision/lower false
positives while retaining a defensible, honest separation between code, smoke
tests, real experimental evidence and future work.

Phase 0 prerequisites:

1. Training-only fp32 feature normalization, persisted for inference.
2. Packet telemetry including TTL/window variance, fragmentation, payload
   distribution, scan signatures and retransmission counts.
3. Five attack phases with distinct C2, plus Benign and Unknown/Ambiguous.
4. Chronological same-environment cross-file chaining.
5. Explanations automatically emitted through forecast/evaluation/app paths.
6. Class-weighted or focal infiltration loss.
7. Graph consistency regularizer included in actual training loss.
8. Stochastic mean/log-variance dynamics and multiple reparameterized rollouts.

Phase 1 decisions:

- CIC-IDS2018 only for primary training. CTU-13/UNSW-NB15 remain held out.
- Full-size GB10 config with bf16 and joint training.
- Validation F1 checkpoint selection and early stopping.

Phase 2 and later remain real-data preparation/training, calibrated evaluation,
baselines and zero-shot testing, operational confidence/persistence validation,
demo completion, signed reports, replay, offline packaging and final submission.
The full original plan is appended to this file.

## 6. Phase 0–1 source implementation verified

Paths in the following sections are relative to `CYBERMIND_REAL`.

| Item | Actual implementation and verification |
| --- | --- |
| Normalization | `src/cybermind/data/normalization.py`: fp32 population running mean/std, training-only fit on unique graph windows, schema checks, fingerprint and JSON constants; all splits transform; graph builder supports normalizer/path; inference checks checkpoint constants |
| Packet features | `src/cybermind/data/pcap_extract.py`: IPv4 TTL/window statistics, fragment ratios, payload quantiles/variance, port-order signatures, TCP sequence-overlap retransmissions |
| Taxonomy | Seven labels: Benign, Reconnaissance, Initial Access, Lateral Movement, Command & Control, Exfiltration, Unknown/Ambiguous |
| Taxonomy routing | Adapter `_stage()` calls `classify_stage()` in `data/stages.py`; it does not load YAML at runtime. Tests compare the YAML mapping with the classifier. Editing YAML alone will not alter runtime classification |
| Chaining | `scripts/prepare_data.py` groups by source/environment and sorts by timestamp; splits events chronologically with window purges; adapter preserves environment IDs |
| Explanations | `WorldModel.forecast()` calls `explain_forecast()`; automatic gradient×input, temporal attention, feature occlusion and risk-reduction suggestions; app/eval surface the object |
| Class weighting | Negative/positive ratio computed from training target occurrences and passed as BCE `pos_weight`; single-class training rejected; ratio has no upper cap |
| Consistency | `batch_loss()` includes graph consistency in weighted total and component logs |
| Stochastic dynamics | Mean/log-variance, reparameterized sampling, Gaussian transition loss, N vectorized trajectories, reproducible seed, ensemble mean/variance |
| Validation | Best checkpoint by held-out infiltration F1; patience/min_delta; best and last checkpoints; separate losses |

## 7. Corrections made during Phase 0–1 continuation

Initial full local suite: 26 tests passed. Review identified uncovered integration
defects, which were fixed before final evidence was produced:

1. `src/cybermind/data/graph_builder.py`: mixed benign/attack windows used a
   fractional target. New training code requires binary labels. Changed the
   target to presence of any attack event in the window. Added a regression test.
2. `src/cybermind/data/adapters/unified.py`: preserved incoming `environment_id`
   instead of dropping it and merging deployments under the same source.
3. `src/cybermind/data/pcap_extract.py`: aggregate timestamp changed from the first
   to the last included packet; original first timestamp retained as
   `session_start`. Prevents completed-session statistics appearing before their
   input telemetry was observed. Added timing assertions.
4. `scripts/prepare_data.py`: benign aliases now follow `classify_stage()` rather
   than recognizing only BENIGN/NORMAL. Added a regression for BACKGROUND,
   LEGITIMATE and `0`.
5. Added `scripts/phase01_smoke.py` for repeatable conversion → preparation →
   normalized CPU training → explained evaluation on synthetic rows.
6. Reworked `scripts/gpu_preflight.py` to read its config, verify actual configured
   processed files, CUDA/requested precision, split disjointness/classes and
   normalization/packet provenance, and return nonzero on failure.
7. `scripts/app.py`: default checkpoint is `checkpoints/best_gb10.pt`, overridable
   with `CYBERMIND_CHECKPOINT`.
8. Wrote `docs/PHASE01_FINAL_REPORT.md` and initial README/status handoff pointers.

The first README edit only added a legacy disclaimer. This was insufficient and
was later corrected after the user's explicit request; see section 10.

## 8. Actual verification evidence

### Phase 0–1 tests

Executed using `.phase01-venv\Scripts\python.exe`:

```text
29 passed, 6 warnings in 6.70s
```

The six warnings were non-failing PyTorch deprecation/nested-tensor warnings.
Evidence: `examples/phase01_integration/pytest.log`.

The integration harness completed:

```text
PASS scripts/build_corpus.py
PASS scripts/prepare_data.py
PASS scripts/train.py
PASS scripts/eval.py
Synthetic integration passed; Phase 2 was not started.
```

- 360 generated fixture rows in two filenames intentionally ordered opposite to
  chronology.
- Environment ID `SYNTHETIC_FIXTURE_ONLY`.
- 122 training sequences; 25 validation; 25 test.
- Two CPU training epochs with current feature schema and stored normalization.
- All 25 test sequences emitted feature-occlusion explanations.
- Source/script compilation passed.

Integration artifacts:

- `examples/phase01_integration/verification.json`.
- `examples/phase01_integration/step_1.log` through `step_4.log`.
- `examples/phase01_integration/config.yaml`.
- `examples/phase01_integration/raw/`, `canonical/`, `processed/`.
- `examples/phase01_integration/train_history.json` and `eval_test.json`.
- `checkpoints/phase01_integration.pt` and `phase01_integration_last.pt`.

Fixture source name CIC-IDS2018 exists only to exercise primary-source routing.
These are **not real CIC-IDS2018 data, real trained checkpoints, performance
evidence, or submission benchmark results**. Do not report their F1/precision as
real detection results. No trained ONNX artifact or live Streamlit UI was
verified during this continuation.

### Local production preflight

Observed stdout:

```text
Python 3.12.14 PyTorch 2.14.0+cpu
PyG 2.8.0.post1
STOP: CUDA is unavailable on this runtime.
STOP: Missing: ...\data\processed_gb10\train.pt
STOP: Missing: ...\data\processed_gb10\val.pt
STOP: Missing: ...\data\processed_gb10\test.pt
STOP: Missing: ...\data\processed_gb10\normalization.json
STOP: Missing: ...\data\processed_gb10\metadata.json
```

Exit code: 1. Ellipses above abbreviate the project-root prefix; the checklist
report contains the full literal paths/stdout/stderr. This is local CPU evidence,
not a check of the user's GB10.

## 9. GB10 checklist audit

The user checklist requests literal evidence per item, using UNKNOWN for absent
host/data access. It is appended verbatim below. The detailed report is
`docs/GB10_CHECKLIST_REPORT.md`; its evidence builder is
`examples/gb10_checklist_audit/build_report.py`.

Original audit: **36 items: 17 PASS, 2 FAIL, 17 UNKNOWN**.

- Section 0 (8 items): UNKNOWN for real GB10 OS/arch, driver/GPU, CUDA version,
  cu130 aarch64 PyTorch, device capability, PyG, fallback branch and bf16. Local
  Windows/CPU/PyG outputs were printed only as explicitly local evidence.
- Section 1 (5): PASS for local source directories, gb10 config, existing
  `configs/final.yaml`, final report and claimed implementation files.
- Section 2 (9): PASS for inspected Phase 0–1 source implementation. Includes the
  important note that adapter classification uses the equivalent Python
  classifier rather than runtime YAML loading.
- Section 3 (2): originally FAIL for stale README/launcher commands and ignored
  submission artifacts. **Both are now resolved**; see next section.
- Section 4 (5): UNKNOWN for single-day real-data preparation/profile, scaling,
  class ratio/weight stability, mixed-window/majority-label statistics and real
  packet-label alignment.
- Section 5 (4): UNKNOWN for available GB10 time, target-host preflight,
  one-epoch GPU run/profile, and demonstrated triggering of early stopping.
  Early-stopping code/config exist, but a run reaching the condition was not
  demonstrated.
- Section 6 (3): PASS for preserved boundaries: no operational confidence gate
  based on unvalidated variance; secondary corpora excluded from primary paths;
  no flow-threshold prefilter before the inspected model forecast path.

After resolving 3.1/3.2, current per-item state is 19 PASS, 0 remaining FAIL among
those 36 headings, 17 UNKNOWN. The old numerical summary inside the evidence
builder is historical and hardcoded. Do not rerun that builder and treat its
prose/status counts as an adaptive audit: re-audit/update it if needed. The report
has a resolution update at its top and preserves the original snapshot below.

Additional unresolved policy mismatch: `gpu_preflight.py` rejects missing PyG,
but the checklist says absence of PyG should not block use of the pure-PyTorch
fallback. This was recorded, not fixed, because the user subsequently requested
only 3.1 and 3.2 fixes. Missing PyG did not occur in the local runtime.

## 10. Immediate fixes to checklist 3.1 and 3.2

### README and launchers

Updated these active files:

- `README.md`: removed legacy command references rather than merely disclaiming
  them. Quickstart now uses `configs/gb10_full.yaml`, correct corpus subdirectory,
  preflight then a one-epoch CUDA run; resume uses `best_gb10_last.pt`; evaluation
  uses `best_gb10.pt`. All automation examples use the current config. Corrected
  output paths, PCAP-label caveat and student export command. Added explicit
  submission strategy.
- `scripts/run_training_from_zero.sh`: default config now `gb10_full.yaml`;
  `CYBERMIND_DOWNLOAD_CIC2018=0` explicitly forwards `--no-download-cic2018`.
  Config, resume and epoch environment overrides remain.
- `scripts/launch_training.py`: default config updated; reads `processed_dir`
  from selected config; data preparation restricted to `data/intermediate/CIC-IDS2018`;
  uses configured processed path for readiness and baselines; full preflight now
  follows data preparation and precedes baseline/model training; avoids calling
  the legacy readiness printer; manifest records actual selected config.
- `scripts/one_click_train.py`: requests current config and uses
  `data/processed_gb10/train.pt` for student export.

Preflight ordering was necessary: the expanded preflight checks prepared data,
so calling it before preparation would reject a clean start regardless of GPU.

Search of README and those three launchers found no `gpu_128gb`, `best_128gb`,
`configs/smoke.yaml`, or `configs/final.yaml` references after edits. Older config
files/historical reports remain in the directory; they were not deleted.

### Submission strategy

Removed these blanket `.gitignore` entries:

```text
*.pt
results/*.json
results/*.png
```

Added ignores for `.phase01-venv/`, `.uv-cache/`, `.pytest_cache/`; existing
environment/raw/intermediate exclusions otherwise remain. Normal Git staging is
the chosen strategy for final checkpoint/results, with no force-add required.

README lists final artifacts to explicitly stage **after real generation**:

- `checkpoints/best_gb10.pt`.
- `results/eval_val.json`, `results/eval_test.json`.
- `results/baseline_val.json`, `results/baseline_test.json`.
- `results/gb10_train_history.json` and final benchmark PNGs.
- Current training config and `data/processed_gb10/normalization.json`.

Synthetic fixtures are not final submission evidence. No project repo was
initialized, committed or pushed. A separate temporary Git repository was used
only to exercise ignore behavior; it was not the project.

### Verification of these fixes

Added `tests/test_launcher_gb10.py` with mocked execution checking routing,
preflight-failure blocking, and selected-config manifest output:

```text
3 passed in 0.05s
checkpoints/best_gb10.pt TRACKABLE
results/eval_test.json TRACKABLE
results/benchmark.png TRACKABLE
.phase01-venv/test IGNORED
```

Python compilation passed. No downloads or training occurred in these tests.
The earlier 29-test full suite and these later three tests are separate runs;
do not claim a combined 32-test run was executed.

## 11. Current GB10 configuration and execution boundary

`configs/gb10_full.yaml` uses:

- Primary source CIC-IDS2018; `data/processed_gb10`.
- Require normalization and complete packet features.
- Window 60 seconds, stride 30, history 16.
- Graph hidden/output 512, temporal dimension 512, eight graph/attention heads,
  six temporal layers, seven output stages, dropout 0.10.
- Loss weights: transition 1, infiltration 1, stage 0.5, calibration 0.2,
  graph consistency 0.1.
- bf16, CUDA required, 50 epochs, learning rate 0.0003, weight decay 0.0001,
  gradient clip 1.0, batch 8, accumulation 8, workers 0.
- Best checkpoint `best_gb10.pt`, last `best_gb10_last.pt`.
- Selection `val_f1`, threshold 0.5, early stopping patience 8, min_delta 0.0001.
- Eval rollout steps 12, N rollouts 16.

These sizes are a starting point, not a demonstrated GB10 memory fit. Unified
memory also holds the corpus, runtime, gradients and optimizer. Full corpus
preparation materializes frames/graphs and has not been profiled at scale.

Readiness statement remains: **GO for Phase 2 data preparation and target-host
preflight; conditional GO for real training only after those checks pass and a
small real-data run is reviewed.** No remote hardware readiness is certified.

## 12. Remaining work and constraints for the next agent

1. Finish the currently requested full-directory copy/ZIP only after this context
   file is complete. Verify it and report paths/counts/checksum honestly.
2. Preserve the Phase 2 stop boundary until the user asks to execute it. Do not
   start downloads/training merely because commands are listed in documents.
3. Obtain actual GB10 access/time budget to verify OS/architecture, GPU, driver,
   toolkit, aarch64 CUDA PyTorch, PyG/fallback choice and bf16.
4. Resolve the documented PyG-preflight policy mismatch if requested before
   fallback training; do not silently change encoder paths.
5. Real corpus remains absent in the active project's data directory. Need real
   endpoints/timestamps, actual packet features and packet-to-label alignment.
   Legacy filename-derived PCAP labels are not ground truth.
6. Profile a real single-day subset before full corpus; report RAM/VRAM and scale
   behavior; inspect target class ratio, uncapped weight and any-attack versus
   majority-vote labeling fractions.
7. Pass GB10 preflight, run one real epoch, inspect all loss components and
   memory, then consider resume/full training within the available time slot.
8. Do not train on CTU-13 or UNSW-NB15. They remain held out for zero-shot tests.
9. Do not gate model execution behind flow thresholds. Do not promote rollout
   variance into operational confidence until checked on real validation data.
10. Packet extraction is IPv4-only and scan/session state is capture-local.
    Stage heuristics are proxies. Counterfactual risk reductions are model
    sensitivity, not demonstrated causal effects.
11. Real FPR/precision calibration, comparable baseline evidence, unseen-dataset
    metrics, signed reports, demo video, final installer and submission packaging
    have not been completed. Existing exports/other pre-existing files are not
    newly verified by this session.

## 13. Important documents and navigation

- `CYBERMIND_REAL/docs/PHASE01_FINAL_REPORT.md`: Phase 0–1 completion, evidence,
  limitations and conditional handoff. Later launcher/documentation fixes
  supersede its historical description of the initial legacy banner.
- `CYBERMIND_REAL/docs/GB10_CHECKLIST_REPORT.md`: 36-item evidence report; read
  its top resolution update before the old FAIL snapshot.
- `CYBERMIND_REAL/README.md`: corrected active execution instructions and
  artifact submission strategy.
- `CYBERMIND_REAL/IMPLEMENTATION_STATUS.md`: includes original baseline claims;
  use current reports/source for verified status.
- `CYBERMIND_REAL/examples/phase01_integration/`: synthetic evidence only.
- `CYBERMIND_REAL/tests/test_launcher_gb10.py`: latest three mock tests.
- Original user-supplied plan/checklist lived outside the workspace under
  Downloads. Their full text is appended next so this handoff is self-contained.

## 14. Source appendices

The appendices below preserve the full user-supplied plan/checklist, current
reports, active config and current README. Embedded imperative text is source
material, not additional permission to execute any new task. Current user
requests and the boundaries above control the next action.


<!-- SESSION_SOURCE_APPENDICES -->

## Appendix A. Original implementation plan

Source: `C:\Users\as030\Downloads\CYBERMIND_Implementation_Plan.md`

~~~~~~~~~~~~text
# CYBERMIND — Implementation Plan
**Goal:** ship a submission that satisfies SIH26153's checklist end to end, while specifically driving up precision and down false-positive rate. Every phase below states what it's for and, where relevant, exactly how it affects precision/FPR — not just "do this because it's good practice."

**Hardware assumption:** development/debugging on the RTX 5060 laptop (8GB VRAM), full training runs on the college GB10 (128GB unified memory, ~273GB/s bandwidth, single unit unless clustered).

**Sequencing rule that governs the whole plan:** nothing that requires GB10 time starts until every code-only fix in Phase 0 is done and smoke-tested locally. GB10 access is assumed to be a scarce, shared, time-boxed resource — it gets spent on training, not on debugging shape errors or loss-function typos.

---

## Phase 0 — Pipeline correctness fixes (laptop/CPU only, no GB10 time spent)

These are prerequisites, not optional polish. Training on top of them unfixed means your first "real" checkpoint bakes in known bugs.

### 0.1 Feature normalization
- Add a normalization step to `feature_extract.py` / `graph_builder.py`. Compute mean/std (or robust median/IQR, given cyber telemetry is heavy-tailed) in **fp32** over the full training corpus. Store the constants; apply at feature-vector construction time.
- **Precision/FPR impact:** unnormalized features (raw byte counts vs. 0/1 flag ratios sitting on wildly different scales) destabilize GAT attention and gradient magnitudes, which shows up as noisy, poorly-calibrated probability outputs — directly inflates false positives from spurious high-confidence spikes on benign traffic with unusually large raw values (e.g. a legitimate large backup transfer).

### 0.2 Complete packet-level feature extraction
- Extend `pcap_extract.py` beyond flow-level aggregates to include: TTL value + variance across a session, TCP window size, IP fragment flags, payload size distribution, port-scan signature detection (sequential vs. randomized port access), retransmission counts.
- **Precision/FPR impact:** this is exactly the signal that separates a slow, low-and-slow reconnaissance scan (a real positive) from ordinary background jitter that only looks anomalous at the flow-aggregate level (a false positive). Missing this is a direct FPR risk on your most PS-relevant attack class.

### 0.3 Five-phase MITRE stage taxonomy
- Expand `knowledge/stage_mapping.yaml` and `_stage()` in `unified.py` from 4 generic buckets to the PS's five named phases (Reconnaissance, Initial Access, Lateral Movement, **Command & Control**, Exfiltration), with an explicit "Unknown/Ambiguous" bucket for labels that don't cleanly map rather than forcing them into the nearest bucket.
- **Precision/FPR impact:** indirect but real — a coarse taxonomy that merges C2 into "lateral/exploit" trains the stage head on noisy labels, which weakens the correlation between predicted stage and predicted risk that your kill-chain verification step (0.6 below) depends on.

### 0.4 Chronological same-environment file chaining
- In `prepare_data.py`, group source files by environment (not by filename), sort chronologically, and build one continuous host-persistent timeline per environment instead of resetting scenario identity at each file boundary.
- **Precision/FPR impact:** without this, a campaign that spans multiple days looks like isolated single-day anomalies with no narrative — which both suppresses true-positive recall (the model can't see the progression) and increases false positives at day boundaries (context resets look like sudden anomalies).

### 0.5 Wire `attribution.py` into the actual inference path
- Call gradient×input attribution, and (0.6/0.7 below) attention weights and occlusion attribution, from inside `forecast()` or a thin wrapper, so every prediction — in `eval.py`, `app.py`, and any CLI — emits a structured explanation object automatically.
- **Precision/FPR impact:** none directly, but this is required for the PS's "black-box outputs are not acceptable" line, and it's the mechanism analysts use to catch and correct false positives in the loop (0.9 below).

### 0.6 Class-weighted / focal loss for the infiltration head
- Current `infiltration_loss` in `losses.py` is plain unweighted `binary_cross_entropy_with_logits`. Infiltration windows are almost certainly a small minority of total windows. Add a `pos_weight` term (from the real class ratio in your training split) or switch to focal loss.
- **Precision/FPR impact:** direct. Unweighted BCE on an imbalanced dataset biases the model toward the majority (benign) class in easy cases but can also produce a poorly-calibrated decision boundary that either drowns in false positives or misses true positives, depending on where the default threshold happens to fall. This is one of the highest-leverage, cheapest fixes on this entire list.

### 0.7 Wire the existing-but-unused `graph_consistency_loss` into training
- `losses.py` already defines `graph_consistency_loss` (penalizes large jumps in latent `z` between consecutive windows) but `batch_loss()` in `train.py` never includes it in the total loss.
- **Precision/FPR impact:** this is a smoothness regularizer — it discourages the model from treating ordinary latent drift as a sharp discontinuity, which is a direct lever against single-window false-positive spikes caused by benign but unusual traffic (a burst backup job, a patch rollout).

### 0.8 Implement the stochastic dynamics head (probabilistic rollout)
- Change `DynamicsModel` to output mean + log-variance, sample via reparameterization, run N rollouts per forecast instead of one.
- Smoke-test on CPU/laptop with tiny synthetic batches (shape correctness only) before this ever touches GB10 time.
- **Precision/FPR impact:** this is the basis of Phase 3's confidence-gated decision rule below — variance across rollouts becomes your primary lever for suppressing low-confidence false positives without also suppressing true positives.

**Exit criterion for Phase 0:** all of the above run cleanly on a small synthetic or subsampled batch on the laptop, matching the same "smoke test, not real evidence" discipline your `examples/smoke/` harness already uses. Do not proceed to Phase 1 until this passes.

---

## Phase 1 — Pre-training decisions (still no GB10 time)

### 1.1 Decide the primary training corpus
Full CIC-IDS2018 corpus, all days, all attack types, chained per 0.4. **Do not fold CTU-13 or UNSW-NB15 into training** — they stay fully held out for the zero-shot generalization test in Phase 3. "Bigger dataset" means the full primary corpus properly chained, not multiple datasets blended together.

### 1.2 Finalize the training config for GB10
- New `configs/gb10_full.yaml`: full-scale `graph_hidden`/`temporal_dim` (restore from the original 128GB-oriented sizing — the laptop-scale config was a memory workaround, no longer needed), `batch_size` sized to what 128GB unified memory allows, `precision: bf16` (native Blackwell support, no `GradScaler` needed — swap `torch.amp.autocast('cuda')` fp16 path to `torch.autocast(dtype=torch.bfloat16)`), full joint end-to-end training (no encoder freezing/embedding-caching — that was only needed for the 8GB laptop).
- Optional but worth keeping: a short self-supervised encoder pretraining pass before joint training (Stage A from the laptop plan) purely as a convergence aid, followed immediately by full joint fine-tuning as the default, not a "some day" step.

### 1.3 Pick a validation-driven early-stopping / checkpoint-selection metric
- Current `train.py` selects "best" checkpoint by training loss. Switch checkpoint selection to a held-out validation metric — specifically **validation-set precision at a fixed recall level, or F1 on infiltration_loss**, not raw training loss.
- **Precision/FPR impact:** direct. Training-loss-based checkpointing can select a model that's still improving on easy majority-class examples while quietly overfitting or drifting worse on the rare positive class — exactly the failure mode that inflates false positives at deployment.

---

## Phase 2 — The GB10 training run

1. Run Phase 0 + 1's fixed pipeline through `build_corpus.py` → `prepare_data.py` on the full chained CIC-IDS2018 corpus.
2. Launch `train.py` with `configs/gb10_full.yaml`, bf16, full joint training, validation-based checkpointing (1.3).
3. Log train/val curves for all four loss components (`transition`, `infiltration`, `stage`, `calibration`/Brier) separately, not just the summed total — this lets you see if one component (e.g. stage) is dragging while infiltration improves, which matters for diagnosing precision/FPR issues later.
4. If time budget allows more than one run: do a first shorter run to catch config/data issues cheaply, then the full run. Don't spend the entire time budget on a single untested long run.

**Exit criterion:** a real checkpoint (`checkpoints/best_gb10.pt` or similar) trained on real, normalized, feature-complete, chronologically-chained data — the item that was the single highest-priority gap throughout this whole review.

---

## Phase 3 — Evaluation, calibration, and the precision/FPR-specific decision layer

This phase is where "higher precision, lower FPR" actually gets engineered, not just hoped for.

### 3.1 Baseline comparisons (PS-required, and your precision/FPR evidence)
- Run `run_baseline.py` (logistic regression) on the same processed data.
- Add a second, even simpler rule-based baseline (SYN-flood thresholds, known-bad-port lists, handshake-completion checks) purely as a comparison point — **never** as a gate in front of the model itself (this was explicitly considered and rejected earlier: gating the model behind a flow-threshold filter reintroduces the exact blind spot — slow scans evading flow-based thresholds — that packet-level features exist to catch).
- Report F1, precision, recall, FPR for: world model, logistic regression, rule-based baseline. This is both a PS deliverable and your quantitative evidence that temporal dynamics learning earns its complexity.

### 3.2 Threshold calibration against a target FPR, not a default 0.5
- `eval.py` currently defaults `--threshold=0.5` with no search. Instead, sweep the validation-set precision-recall / ROC curve and pick the operating threshold that hits a stated target FPR (e.g. "we calibrate to ≤2% FPR on the validation set, then report precision/recall at that point on the held-out test set").
- **Precision/FPR impact:** direct and probably your single biggest lever. A model trained well but evaluated at an arbitrary 0.5 cutoff can look far worse (or, deceptively, far better) than it is. Report both the PR curve and the chosen operating point explicitly — this also reads as far more rigorous to a judge than a bare F1 number.

### 3.3 Confidence-gated decision rule, using the stochastic dynamics head (0.8)
- Flag "infiltration in progress" only when both: (a) predicted risk exceeds the calibrated threshold from 3.2, **and** (b) predictive variance across the N stochastic rollouts is below a confidence bound.
- Additionally require the risk trajectory to be **sustained across consecutive windows**, not a single spike — mirroring the "kill-chain causal sequence verification" idea from the earliest architecture review (ignore isolated spikes that don't show sequential progression across predicted stages).
- **Precision/FPR impact:** this is the concrete mechanism that turns "we have uncertainty estimates" into an actual false-positive reducer — single noisy high-confidence-looking spikes from benign bursts get filtered out by the persistence-and-confidence requirement, while a genuine slow-building campaign (which is sustained by definition) still triggers.

### 3.4 Cross-dataset zero-shot generalization test
- Using the existing `adapters/unified.py`, evaluate the CIC-IDS2018-trained model cold on CTU-13 (and/or UNSW-NB15) with no fine-tuning.
- **Precision/FPR impact:** validates that your precision/FPR numbers aren't an artifact of overfitting to one dataset's specific noise profile — directly answers the PS's "generalize to unseen attack patterns" line with evidence, not a claim.

### 3.5 Post-hoc correlation rule over predicted stage sequences (fallback layer)
- On top of the model's own per-window predictions, apply a lightweight rule: if an environment shows a predicted Reconnaissance-stage window followed by a predicted Lateral-Movement-or-later window within a bounded time horizon, flag as a linked multi-stage campaign.
- This operates entirely on the model's own outputs after forecasting — it does not replace the model's judgment, only correlates it across time. Valid under the predict-not-detect framing established earlier.

---

## Phase 4 — Explainability surfacing (builds on Phase 0.5's wiring)

1. Add attention-weight extraction from the temporal transformer (`need_weights=True` on the underlying `nn.MultiheadAttention`) — answers "which past windows" drove the forecast.
2. Extend the existing host-level occlusion logic in `simulator.py` down to feature granularity: perturb one feature at a time, re-run `forecast()`, measure the risk delta — answers "how much would removing this actually change the outcome," and ties your explainability story to the same counterfactual-simulation mechanism that's your actual novelty claim.
3. Keep gradient×input attribution as a cheap secondary signal, not the headline.
4. Every prediction now emits: ranked feature attributions, ranked temporal attention, and the counterfactual "what would reduce risk" signal — three complementary explanation types, satisfying the PS's explainability bullet more thoroughly than any single method would.

---

## Phase 5 — Demo interface completion

1. Add a **flagged flows table** to `app.py` (host pairs, ports, protocol) — currently only aggregate node/edge counts are shown; the PS explicitly asks for "flagged flows."
2. Surface `simulator.py`'s `rank_interventions()` and `attack_gravity()` in the UI — an interactive sidebar to pick an intervention (Block Host, Isolate Host, etc.) and watch the forecasted risk update live. Backend already exists; this is pure UI wiring.
3. Surface the confidence signal from Phase 3.3 next to each forecast ("high/medium/low confidence").
4. Confirm the app still runs fully offline (no cloud calls) end to end with the new real checkpoint.

---

## Phase 6 — Differentiating features (your USP layer)

1. **Signed incident reports** — auto-generate a structured report per forecasted trajectory (stage, driving features, recommended intervention from `rank_interventions`), cryptographically signed for integrity/provenance — framed as chain-of-custody for forensic evidence, not a generic encryption gimmick.
2. **Graph replay animation** — animate the network graph evolving over the observed window with a risk overlay, for the demo video.
3. **Offline air-gapped packaging** — bundle the trained (or distilled) model + runtime into a single no-external-calls installer, relevant to CII's typically air-gapped deployment context.

---

## Phase 7 — Documentation and submission packaging

1. Compress `docs/SIH26153_CYBERMIND_Master_Plan.md` (currently 1194 lines) down to the required 2-page architecture document. Cut the roadmap/aspirational infra (DPDK, FlashAttention-2, hot-swap shadow training) to a clearly labeled "Future Work" appendix, not the main body.
2. Add a real references section — every claim that currently has no citable source gets either a citation or gets rewritten as an unsupported-but-honest statement.
3. Write up the reframed novelty argument explicitly: GNN + Transformer + latent dynamics as necessary substrate (the PS's own named example techniques, used because they're correct, not because they're novel), with the counterfactual/Attack Gravity/confidence-gated decision layer foregrounded as the actual differentiator.
4. Report the full metrics table: world model vs. logistic regression vs. rule-based baseline, at the calibrated threshold from 3.2, plus the cross-dataset zero-shot numbers from 3.4.
5. Record the demo video showing: PCAP/CSV upload → forecast timeline → flagged flows → stage annotation → interactive intervention panel → signed report generation.
6. Final README with setup instructions, reproducible training config, and an explicit "what's real vs. what's future work" status section — keep the honesty discipline that's already distinguishing this codebase from a purely aspirational submission.

---

## Summary: what specifically drives precision up and FPR down, in one place

| Mechanism | Phase | Effect |
|---|---|---|
| Feature normalization | 0.1 | Removes scale-driven noise in attention/gradients |
| Complete packet-level features | 0.2 | Catches slow scans without flow-level false alarms |
| Chronological file chaining | 0.4 | Removes context-reset false spikes at file boundaries |
| Class-weighted/focal loss | 0.6 | Fixes imbalance-driven miscalibration at the source |
| Graph consistency loss (wired in) | 0.7 | Penalizes spurious single-window latent jumps |
| Stochastic dynamics + variance | 0.8, 3.3 | Enables confidence-gating of alerts |
| Validation-based checkpointing | 1.3 | Prevents selecting an overfit/majority-biased checkpoint |
| Threshold calibration to target FPR | 3.2 | Replaces arbitrary 0.5 cutoff with a deliberate operating point |
| Confidence + persistence gating | 3.3 | Suppresses isolated benign spikes, keeps sustained real campaigns |
| Cross-dataset zero-shot check | 3.4 | Confirms precision/FPR aren't dataset-specific overfitting artifacts |
~~~~~~~~~~~~

## Appendix B. Original GB10 verification checklist

Source: `C:\Users\as030\Downloads\GB10_Verification_Checklist.md`

~~~~~~~~~~~~text
# CYBERMIND — GB10 Host Verification Checklist

**Purpose:** this is not a to-do list of new work — it's a verification pass. Every item below checks a claim already made (by the codebase's own docs, or by a prior automated continuation) against what's actually true on the real GB10 host and in the real repository. Report pass/fail/unknown for each line, with the actual command output, not a paraphrase. Do not mark anything "done" without pasting the command output that proves it.

---

## 0. Environment setup and verification (do this before anything else)

- [ ] Confirm OS/arch: `uname -m` (expect `aarch64`) and `cat /etc/os-release`.
- [ ] Confirm GPU is visible: `nvidia-smi` — record driver version and confirm `GB10` is listed.
- [ ] Confirm CUDA toolkit version available on host: `nvcc --version` or `nvidia-smi` header (expect CUDA 13.x).
- [ ] Install/confirm PyTorch is a **cu130 aarch64 build**, not a default x86/older-CUDA wheel (see install instructions below).
- [ ] Run and paste the output of:
  ```bash
  python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))"
  ```
  Expected: CUDA available `True`, device name contains `GB10`, capability `(12, 1)`.
- [ ] Attempt `import torch_geometric` and report success/failure verbatim:
  ```bash
  python -c "import torch_geometric; print('PyG OK', torch_geometric.__version__)"
  ```
  If this fails, do **not** treat it as a blocker — the codebase has a pure-PyTorch fallback graph-attention path — but explicitly record that PyG is unavailable, since it means training will silently run on the fallback encoder unless the code path is checked.
- [ ] If PyG import fails, check which encoder path the code actually takes at runtime (search `src/cybermind/models/graph_encoder.py` for `HAS_PYG` and confirm which branch executes) and record it.
- [ ] Confirm bf16 support: `python -c "import torch; print(torch.cuda.is_bf16_supported())"` — expect `True`.

---

## 1. Codebase completeness — does the actual source tree match what the docs claim?

- [ ] Confirm these directories exist in the project root and are non-empty: `src/cybermind/`, `scripts/`, `configs/`, `tests/`. List their contents (`find . -maxdepth 2 -type d` and `ls scripts/ configs/`).
- [ ] Confirm `configs/gb10_full.yaml` exists and paste its full contents.
- [ ] Confirm `configs/final.yaml`, referenced in `README.md`'s "For real training, edit `configs/final.yaml`" line, actually exists. If it does not exist, flag this as a broken doc reference.
- [ ] Confirm `docs/PHASE01_FINAL_REPORT.md` exists (referenced by both `README.md` and `IMPLEMENTATION_STATUS.md`) and paste it in full.
- [ ] Confirm `scripts/phase01_smoke.py`, `scripts/gpu_preflight.py`, and `data/normalization.py` exist (all claimed as new/modified in the phase 0–1 continuation report) and paste their contents.

## 2. Phase 0–1 code claims — verify each against actual source, not the report's own summary

For each row, open the named file and confirm the claim in the "verified implementation" column is actually present in code (quote the relevant lines), not just described in a report.

- [ ] **Normalization (0.1):** `data/normalization.py` — confirm fp32 stats are computed, constants are stored, and normalization is applied at train/val/test time (not just train). Confirm `graph_builder.py`/`feature_extract.py` actually calls it.
- [ ] **Packet features (0.2):** confirm `pcap_extract.py` computes TTL variance, TCP window size, IP fragment flags, payload size distribution, port-scan signature detection, and retransmission counts — quote the function(s).
- [ ] **Stage taxonomy (0.3):** confirm `knowledge/stage_mapping.yaml` (or equivalent) has 7 labels including a distinct Command & Control bucket, and confirm `_stage()` in the adapter actually uses this mapping.
- [ ] **Chronological chaining (0.4):** confirm `prepare_data.py` groups source files by environment (not filename) and sorts chronologically before `make_sequences`. Confirm the `environment_id` field is preserved through the unified adapter (claimed fix during the phase 0–1 continuation) — quote the relevant code.
- [ ] **Explanation wiring (0.5):** confirm `forecast()` (or its caller in `app.py`/`eval.py`) actually invokes gradient×input, temporal attention extraction, and feature-occlusion attribution — not just that `attribution.py` exists as a standalone file. Run `grep -rn "attribution\|need_weights\|occlusion" scripts/app.py scripts/eval.py` and paste the output.
- [ ] **Class imbalance (0.6):** confirm `losses.py`'s `infiltration_loss` (or its caller) actually applies a computed `pos_weight`, and confirm where/how the positive-class ratio is computed from real (or fixture) data.
- [ ] **Graph consistency loss (0.7):** confirm `graph_consistency_loss` is actually included in the summed `total` loss in `train.py`'s `batch_loss()` — previously this function existed but was never called; confirm it now is.
- [ ] **Stochastic dynamics (0.8):** confirm `DynamicsModel` outputs mean + log-variance, samples via reparameterization, and that `rollout()` supports N stochastic trajectories, not a single deterministic path. Quote the forward/rollout methods.
- [ ] **Checkpoint selection (1.3):** confirm `train.py` selects best checkpoint by a validation metric (e.g. validation infiltration F1), not training loss.

## 3. Documentation consistency

- [ ] In `README.md`, confirm whether the command blocks under "Quickstart," "One-command training," "Final pre-training automation," and "One-command lab training" still reference `configs/gpu_128gb.yaml` / `checkpoints/best_128gb.pt` / `configs/smoke.yaml`. If yes, these need to be edited or removed, not just disclaimed by a banner sentence at the top of the file — report exactly which command blocks are stale.
- [ ] Confirm `_gitignore` — check whether `*.pt`, `results/*.json`, and `results/*.png` are still excluded. If so, flag explicitly: **as written, a `git push` of this repo will NOT include the trained checkpoint or benchmark results**, both of which are named required deliverables in the SIH26153 problem statement. This needs to be fixed (remove the exclusion, or force-add the specific final artifacts) before the submission commit.

## 4. Pre-full-training data checks (run on a data subset first, not the full corpus)

- [ ] Run `build_corpus.py` + `prepare_data.py` on **a single day's worth of real CIC-IDS2018 files only**. Record peak RAM/VRAM usage during this run.
- [ ] Extrapolate: does memory scale roughly linearly with file count? If not (e.g. worse than linear), flag this before running the full week's corpus — the full-corpus run has not been profiled at scale and the report explicitly warns batch size is "a starting value, not a fit guarantee."
- [ ] After preparing real data (even the single-day subset), print the actual positive/negative class ratio for the infiltration target. Compare it to whatever `pos_weight` the code computes — confirm the computed weight is not extreme/destabilizing (e.g. not >50:1 without a cap).
- [ ] Check the effect of the "mixed window → binary if any attack event present" labeling rule (introduced during the phase 0–1 continuation) on the real/subset data: what fraction of windows get flipped to positive by this rule versus a stricter majority-vote alternative? Report both numbers.
- [ ] Confirm whether the real corpus includes actual PCAP files with genuine packet-to-label alignment, or only flow CSVs. If PCAP-derived packet-level features are intended to be used (required per the PS's "Input Data" section), confirm the packet-to-label alignment is real and not filename-derived (the phase 0–1 report explicitly flags the legacy PCAP helper's filename-derived labels as not ground truth).

## 5. GB10 time-budget and run plan

- [ ] Confirm how much wall-clock GB10 access is actually available (hours/days) before it's reclaimed.
- [ ] Run `gpu_preflight.py --config configs/gb10_full.yaml` and paste the full output, including exit code.
- [ ] Run a **1-epoch** training run first (`train.py --config configs/gb10_full.yaml --device cuda --epochs 1`), inspect actual memory use and loss values (all four components — transition, infiltration, stage, calibration — separately, not just the summed total), before committing to the full resumed/multi-epoch run.
- [ ] Confirm early stopping is actually configured and will fire — don't rely on a fixed epoch count alone given the time-budget constraint above.

## 6. Deferred/do-not-do-yet items (flag if anyone attempts these before the above passes)

- [ ] Do **not** wire rollout variance into any operational confidence-gating decision rule until it has been checked against real validation data — bin predictions by variance and confirm high-variance bins actually correspond to lower empirical accuracy. The phase 0–1 report explicitly states "rollout variance is not calibrated confidence" as of this handoff.
- [ ] Do **not** fold CTU-13 or UNSW-NB15 into the training set. They must remain fully held out for the zero-shot cross-dataset generalization evaluation.
- [ ] Do **not** gate the world model's forward simulation behind any flow-level threshold rule (e.g. "skip windows that look benign"). This was explicitly considered and rejected earlier in this review — it reintroduces the exact evasion blind spot packet-level features exist to close.

---

## Report format requested back

For each checked item above, reply with: item number, **PASS / FAIL / UNKNOWN**, and the literal command output or quoted code snippet that proves it — not a restated summary. If something can't be checked (e.g. no GB10 access yet), mark it **UNKNOWN**, don't guess.
~~~~~~~~~~~~

## Appendix C. Phase 0–1 final report

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\docs\PHASE01_FINAL_REPORT.md`

~~~~~~~~~~~~text
# CYBERMIND: Phase 0–1 final report

Date: 2026-09-11

**Outcome: Phase 0–1 code and local correctness checks completed. Phase 2 was not started.**
You can proceed to Phase 2 preparation on the GB10 host. Start real training only
after the real corpus and target runtime pass the preflight below. This is not an
unconditional certification that a full-corpus training run will fit or succeed.

## Scope recovered from the shared chat

Source: [Execute implementation plan phase 1](https://chatgpt.com/s/cx_6aa38eee2fa081918d99307e55d359e7).
The shared page exposed the prior user request and expanded progress messages.
It requested completion through Phase 1, a recheck, and a stop before Phase 2.
No completed final report was visible in that shared view. This audit also read
`C:\Users\as030\Downloads\CYBERMIND_Implementation_Plan.md` and checked the actual
workspace rather than treating prior progress statements as proof of completion.

The earlier run had implemented most changes and reported packet/taxonomy and
training tests plus a synthetic training run. Its last visible unfinished items
were normalization/chaining verification, explanation integration, and the final
checklist/GB10 handoff. Those were the continuation point.

## Completed checklist

| Plan item | Verified implementation | Result |
| --- | --- | --- |
| 0.1 Normalization | `data/normalization.py`: fp32 population mean/std over unique training graph windows, stored constants and schema fingerprint; validation/test transform only; inference contract checks | Complete locally |
| 0.2 Packet features | TTL/window mean and variance; fragmentation flags; payload distribution; sequential/irregular port-access signatures; overlapping TCP sequence retransmissions | Complete; synthetic PCAP tests |
| 0.3 Stage taxonomy | Benign plus Reconnaissance, Initial Access, Lateral Movement, Command & Control, Exfiltration, Unknown/Ambiguous; shared adapter/YAML taxonomy | Complete: seven output labels |
| 0.4 Chronological chaining | Source/environment grouping across files; timestamp ordering; stable endpoint names; chronological event splits with a window purge | Complete; cross-file and leakage checks |
| 0.5 Automatic explanations | `forecast()` emits gradient×input, temporal attention, feature occlusion and risk-reduction suggestions; evaluation and app surface explanations | Complete; tested under no-grad and inference-mode |
| 0.6 Class imbalance | Positive weight derived from training target occurrences; weighted infiltration BCE; rejects single-class training | Complete |
| 0.7 Consistency loss | Consecutive latent consistency included in training loss and separate logs | Complete |
| 0.8 Stochastic dynamics | Mean/log-variance, Gaussian transition loss, reparameterized samples, reproducible multiple-rollout mean and variance | Complete; shape and gradient checks |
| 1.1 Primary corpus decision | Primary path accepts CIC-IDS2018 only; CTU-13/UNSW-NB15 use separate held-out mode and primary normalization constants | Complete; real corpus not acquired |
| 1.2 GB10 config | `configs/gb10_full.yaml`: 512-wide graph/temporal model, six temporal layers, bf16, full joint training, batch 8 × accumulation 8 | Complete; batch size remains to be profiled on GB10 |
| 1.3 Checkpoint selection | Validation infiltration F1, early stopping, best/last checkpoints, separate loss logs; bf16 does not instantiate GradScaler | Complete |

Optional encoder pretraining was not added; the configured default is joint training.
Attention/occlusion work overlaps Phase 4 but was already part of the Phase 0
explanation implementation. No remaining Phase 3–7 work was undertaken as a new phase.

## Changes made during this continuation

1. Fixed mixed benign/attack graph windows. Their target now means “at least one
   attack event is present” (binary), rather than a fractional attack-flow ratio
   rejected by class-weight calculation. This also keeps metric targets binary.
2. Preserved explicit `environment_id` through the unified adapter so different
   deployments are not merged before chronological chaining.
3. Corrected PCAP aggregate timestamps to the last included packet, retaining
   `session_start` separately. Completed session statistics no longer appear at
   the first packet before their inputs were available.
4. Aligned benign aliases in canonical preparation with the stage taxonomy.
5. Added regression coverage for mixed targets, environment preservation, benign
   aliases and aggregate timing.
6. Added `scripts/phase01_smoke.py`, a repeatable synthetic integration check using
   the current feature schema, normalized data, separate splits and explanations.
7. Reworked `scripts/gpu_preflight.py`: it now honors the selected config and its
   processed-data directory, checks the requested precision, validates splits,
   classes and normalization/packet provenance, and exits nonzero on failure.
   The older check ignored the config and printed failures without failing.
8. Pointed the app's default checkpoint at `best_gb10.pt`; the
   `CYBERMIND_CHECKPOINT` environment variable can select another compatible file.
9. Updated README/status pointers to the current handoff and marked older
   one-click/config instructions as legacy.

## Executed verification and evidence

Runtime used: project `.phase01-venv`, Python 3.12.14, PyTorch 2.14.0+cpu,
PyG 2.8.0.post1. These versions describe the tested local environment, not a
certified GB10 software stack.

- **29 pytest checks passed**, with six non-failing PyTorch warnings.
  Evidence: `examples/phase01_integration/pytest.log`.
- **Four integration stages passed**: `build_corpus.py` → `prepare_data.py` →
  two-epoch CPU `train.py` → `eval.py`.
- Fixture: 360 generated flow rows in two deliberately misordered filenames;
  122 training, 25 validation and 25 test sequences after split purging.
- All 25 evaluated test sequences emitted automatic feature-occlusion explanations.
- Source/scripts compile check passed (`python -m compileall -q src scripts`).
- Production preflight correctly returned exit code 1 locally: CUDA unavailable
  and five required production data/metadata artifacts missing.

Artifacts:

- `examples/phase01_integration/verification.json`: machine-readable integration result.
- `examples/phase01_integration/step_1.log` through `step_4.log`: command output.
- `examples/phase01_integration/processed/normalization.json` and `metadata.json`:
  fixture normalization/split evidence.
- `examples/phase01_integration/train_history.json`: separate training/validation losses.
- `examples/phase01_integration/eval_test.json`: synthetic forecasts and explanations.
- `checkpoints/phase01_integration.pt` and `phase01_integration_last.pt`: synthetic checkpoints.

**None of these are real CIC-IDS2018 results.** The fixture uses the source name
only to exercise primary-corpus routing and labels its environment
`SYNTHETIC_FIXTURE_ONLY`. It is not input for production training. Synthetic
precision/F1 values are deliberately not presented as detection-performance evidence.
No trained ONNX artifact or live Streamlit UI was verified in this continuation.

## GB10 handoff: Phase 2, for the next execution

From the `CYBERMIND_REAL` project root, use a GB10-compatible CUDA/PyTorch/PyG
environment. Recreate the environment on that host; do not copy the Windows CPU venv.
Supply the complete primary corpus with real endpoint identities, timestamps,
labels, environment IDs and packet features derived from actual captures.
Plain flow CSVs missing packet telemetry must be enriched before feature-complete
training. The legacy PCAP helper's filename-derived labels are not ground truth;
an actual packet-to-label alignment is still required for real data preparation.

Commands to run in Phase 2, **not executed here against real data**:

```bash
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/prepare_data.py --config configs/gb10_full.yaml --input data/intermediate/CIC-IDS2018 --strict
python scripts/gpu_preflight.py --config configs/gb10_full.yaml
# Continue only after preflight succeeds:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --epochs 1
# Inspect logs and actual memory use before extending the same run:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --resume checkpoints/best_gb10_last.pt
```

The full configured run totals 50 epochs including a resumed first epoch.
Check the supplied files cover all intended days/attack types; a source-name check
cannot establish completeness. Full-corpus preparation currently materializes
data/graphs in memory and has not been profiled at that scale. The 128 GB is shared
with data, runtime and optimizer state, so batch 8 is a starting value, not a fit guarantee.

Additional limits: packet extraction handles IPv4; scan/session state is local to
a capture; dataset-derived stage labels remain proxies; rollout variance is not
calibrated confidence; counterfactual reductions are model sensitivity, not causal
effects. Existing checkpoints with the old schema need retraining.

## Stop boundary and readiness signal

**GO for Phase 2 preparation and target-host preflight. Conditional GO for training
only when that preflight passes and a small real-data run fits the GB10.**

No real corpus download, full-corpus preprocessing, real GPU training, target-FPR
calibration, cross-dataset evaluation, signed reports, installer or submission
video was performed. These remain Phase 2 or later work, consistent with the stop
boundary in the shared chat.
~~~~~~~~~~~~

## Appendix D. GB10 checklist report, including remediation update

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\docs\GB10_CHECKLIST_REPORT.md`

~~~~~~~~~~~~text
# GB10 verification checklist: evidence report

## Resolution update — items 3.1 and 3.2 fixed

The FAIL findings below are the original audit snapshot. Both have now been
corrected in the current workspace:

- **3.1 PASS:** README training commands and defaults in `run_training_from_zero.sh`,
  `launch_training.py`, and `one_click_train.py` use `configs/gb10_full.yaml`.
  Data preparation, baselines and student export use `data/processed_gb10`;
  the launcher reads processed paths from its config. Full preflight follows
  preparation and blocks training on failure. Run manifests record the selected config.
- **3.2 PASS:** Removed the blanket checkpoint/result ignore rules before the
  first commit. Final artifacts can be staged normally; no force-add is needed.
  README now specifies the submission files. Project Git initialization/commit/push
  remain unperformed; ignore behavior was verified in a separate temporary repository.

Verification output:

```text
3 passed in 0.05s
checkpoints/best_gb10.pt TRACKABLE
results/eval_test.json TRACKABLE
results/benchmark.png TRACKABLE
.phase01-venv/test IGNORED
```

The three tests in `tests/test_launcher_gb10.py` mock execution to verify routing,
preflight failure blocking and manifest configuration; no training/download occurs.
Python compilation passed. A search of README and the three launchers found no
`gpu_128gb`, `best_128gb`, `configs/smoke.yaml` or `configs/final.yaml` references.
GB10 runtime/data UNKNOWN findings below remain unchanged.

Scope: current local Windows project, not the real GB10 host. No GB10 connection or real corpus was provided. This is a reporting pass; no dependencies were installed and no training was launched. Item suffixes number the bullets in each section of the supplied checklist. PASS for source items means present in the inspected local source, not deployed/verified on GB10. UNKNOWN means the required host/data/runtime evidence is absent.

## 0.1 — UNKNOWN

GB10 OS/architecture not checked: no target-host shell. The following is local evidence only; Linux commands were not represented as GB10 results.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import platform; print(platform.system()); print(platform.machine()); print(platform.platform())"
```

```text
Windows
AMD64
Windows-11-10.0.26200-SP0
```

Exit code: `0`

## 0.2 — UNKNOWN

GB10 visibility/driver version: target-host nvidia-smi was not run. No GB10 output is available.

## 0.3 — UNKNOWN

GB10 toolkit/driver CUDA version: no target-host nvcc or nvidia-smi output. A driver-advertised CUDA version alone would not establish the installed toolkit version.

## 0.4 — UNKNOWN

cu130 aarch64 PyTorch on GB10: unverified. Local environment is CPU-only; nothing was installed in this reporting pass.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.version.cuda)"
```

```text
2.14.0+cpu
None
```

Exit code: `0`

## 0.5 — UNKNOWN

GB10 device/capability: no target-host output. Requested expression run locally below fails on the CPU build; it does not establish anything about the GB10.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))"
```

```text
2.14.0+cpu
False
```

stderr:

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\cuda\__init__.py", line 766, in get_device_name
    return get_device_properties(device).name
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\cuda\__init__.py", line 799, in get_device_properties
    _lazy_init()  # will define _get_device_properties
    ^^^^^^^^^^^^
  File "C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\cuda\__init__.py", line 584, in _lazy_init
    raise AssertionError("Torch not compiled with CUDA enabled")
AssertionError: Torch not compiled with CUDA enabled
```

Exit code: `1`

## 0.6 — UNKNOWN

PyG on GB10 is unknown. Local import result follows. Additional inconsistency: current gpu_preflight.py treats missing PyG as a failure, whereas this checklist says it should not block fallback training. That policy mismatch remains unfixed in this report-only pass.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import torch_geometric; print('PyG OK', torch_geometric.__version__)"
```

```text
PyG OK 2.8.0.post1
```

stderr:

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\jit\_script.py:1491: FutureWarning: `torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`.
  warnings.warn(
```

Exit code: `0`

## 0.7 — UNKNOWN

GB10 encoder branch cannot be inspected without that runtime. Local PyG import succeeds; local encoder selection is printed below. Source confirms fallback only when the import fails.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from cybermind.models.graph_encoder import HAS_PYG, GATv2GraphEncoder; m=GATv2GraphEncoder(3,8,8,2); print('HAS_PYG =', HAS_PYG); print('conv1 =', type(m.conv1).__name__)"
```

```text
HAS_PYG = True
conv1 = GATv2Conv
```

stderr:

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\jit\_script.py:1491: FutureWarning: `torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`.
  warnings.warn(
```

Exit code: `0`

Source: `src/cybermind/models/graph_encoder.py`

```python
from __future__ import annotations
import torch
from torch import nn

try:
    from torch_geometric.nn import GATv2Conv
    HAS_PYG = True
except Exception:
    GATv2Conv = None
    HAS_PYG = False

class DenseGraphAttention(nn.Module):
    """Pure-Torch fallback with the same role as GATv2 for environments without PyG."""
    def __init__(self, in_dim, out_dim, heads=4, dropout=0.1):
        super().__init__(); self.heads=heads; self.out_dim=out_dim
        self.lin=nn.Linear(in_dim,heads*out_dim,bias=False)
        self.q=nn.Linear(out_dim,1,bias=False); self.k=nn.Linear(out_dim,1,bias=False)
        self.dropout=nn.Dropout(dropout); self.act=nn.ELU()
    def forward(self,x,edge_index):
        n=x.size(0); h=self.lin(x).view(n,self.heads,self.out_dim)
        out=torch.zeros_like(h)
        if edge_index.numel()==0: return out.mean(1)
        src,dst=edge_index
        for d in range(n):
            idx=(dst==d).nonzero(as_tuple=False).flatten()
            if idx.numel()==0: continue
            s=src[idx]
            scores=(self.q(h[s])+self.k(h[d])).squeeze(-1)
            alpha=torch.softmax(scores,dim=0).unsqueeze(-1)
            out[d]=torch.sum(alpha*h[s],dim=0)
        return self.act(self.dropout(out)).mean(1)

class GATv2GraphEncoder(nn.Module):
    def __init__(self,node_dim,hidden_dim=128,out_dim=128,heads=4,dropout=0.1):
        super().__init__(); self.has_pyg=HAS_PYG
        if HAS_PYG:
            self.conv1=GATv2Conv(node_dim,hidden_dim,heads=heads,concat=False,dropout=dropout,edge_dim=None)
            self.conv2=GATv2Conv(hidden_dim,out_dim,heads=heads,concat=False,dropout=dropout,edge_dim=None)
        else:
            self.conv1=DenseGraphAttention(node_dim,hidden_dim,heads,dropout)
            self.conv2=DenseGraphAttention(hidden_dim,out_dim,heads,dropout)
        self.norm1=nn.LayerNorm(hidden_dim); self.norm2=nn.LayerNorm(out_dim)
        self.act=nn.GELU(); self.dropout=nn.Dropout(dropout)
    def forward(self,x,edge_index):
        h=self.act(self.conv1(x,edge_index)); h=self.norm1(h); h=self.dropout(h)
        h=self.act(self.conv2(h,edge_index)); h=self.norm2(h)
        # State pooling: mean + max gives a stable graph-level representation.
        return torch.cat([h.mean(dim=0),h.max(dim=0).values],dim=-1)
```

## 0.8 — UNKNOWN

bf16 on GB10 remains unverified. This result belongs to the local CPU runtime.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_bf16_supported())"
```

```text
False
```

Exit code: `0`

## 1.1 — PASS

Required local directories exist and are nonempty. Windows-compatible listing used instead of Unix find/ls.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "from pathlib import Path; roots=['src/cybermind','scripts','configs','tests']; [(print(p, 'exists=',Path(p).is_dir(),'nonempty=',any(Path(p).iterdir())), [print(x) for x in sorted(Path(p).iterdir())]) for p in roots]"
```

```text
src/cybermind exists= True nonempty= True
src\cybermind\__init__.py
src\cybermind\__pycache__
src\cybermind\baselines
src\cybermind\counterfactual
src\cybermind\data
src\cybermind\evaluation
src\cybermind\explainability
src\cybermind\losses.py
src\cybermind\models
src\cybermind\utils
scripts exists= True nonempty= True
scripts\__pycache__
scripts\app.py
scripts\build_corpus.py
scripts\collect_knowledge.sh
scripts\collect_public_corpus.py
scripts\counterfactual.py
scripts\distill_student.py
scripts\download_public_sources.py
scripts\eval.py
scripts\export_teacher_onnx.py
scripts\gpu_preflight.py
scripts\inspect_env.py
scripts\laptop_infer.py
scripts\launch_training.py
scripts\make_synthetic.py
scripts\one_click_train.py
scripts\pcap_to_corpus.py
scripts\phase01_smoke.py
scripts\prepare_cic2018_public.sh
scripts\prepare_data.py
scripts\prepare_for_training.sh
scripts\readiness_check.py
scripts\run_all_pretraining.sh
scripts\run_baseline.py
scripts\run_training_from_zero.sh
scripts\smoke_all.sh
scripts\train.py
scripts\train_gpu_auto.sh
scripts\train_smoke_auto.sh
scripts\validate_dataset.py
scripts\visualize_rollout.py
configs exists= True nonempty= True
configs\final.yaml
configs\gb10_full.yaml
configs\gpu_128gb.yaml
configs\laptop.yaml
configs\phase01_smoke.yaml
configs\smoke.yaml
configs\sources.yaml
tests exists= True nonempty= True
tests\__pycache__
tests\test_imports.py
tests\test_onnx_cpu.py
tests\test_packet_taxonomy.py
tests\test_phase01_data.py
tests\test_phase01_training.py
tests\test_stochastic_forecast.py
```

Exit code: `0`

## 1.2 — PASS

GB10 configuration exists. Full contents:

Source: `configs/gb10_full.yaml`

```text
# Phase 1 decision: full CIC-IDS2018 only. CTU-13 and UNSW-NB15 stay held out.
seed: 42
data:
  raw_dir: data/raw/CIC-IDS-2018
  processed_dir: data/processed_gb10
  primary_source: CIC-IDS2018
  window_seconds: 60
  stride_seconds: 30
  history: 16
  require_normalization: true
  require_packet_features: true
model:
  graph_hidden: 512
  graph_out: 512
  temporal_dim: 512
  graph_heads: 8
  nhead: 8
  temporal_layers: 6
  num_stages: 7
  dropout: 0.10
loss:
  transition: 1.0
  infiltration: 1.0
  stage: 0.5
  calibration: 0.2
  graph_consistency: 0.1
train:
  precision: bf16
  require_cuda: true
  epochs: 50
  lr: 0.0003
  weight_decay: 0.0001
  grad_clip: 1.0
  checkpoint: best_gb10.pt
  # Conservative full-size model microbatch; confirm with real graph sizes on GB10.
  # Unified RAM also holds the corpus, OS, optimizer, and loader; 128 GB is not all activations.
  batch_size: 8
  grad_accumulation: 8
  num_workers: 0
  selection_metric: val_f1
  selection_threshold: 0.5
  early_stopping_patience: 8
  min_delta: 0.0001
  history_path: results/gb10_train_history.json
eval:
  rollout_steps: 12
  n_rollouts: 16
```

## 1.3 — PASS

configs/final.yaml exists; this is not a missing-file reference. It is a separate older configuration and does not have the GB10 normalization/bf16 requirements.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "from pathlib import Path; print('configs/final.yaml exists:',Path('configs/final.yaml').is_file())"
```

```text
configs/final.yaml exists: True
```

Exit code: `0`

Source: `configs/final.yaml`

```text
seed: 42
data:
  raw_dir: data/raw/CIC-IDS-2018
  processed_dir: data/processed
  window_seconds: 60
  stride_seconds: 30
  history: 16
model:
  graph_hidden: 128
  graph_out: 128
  temporal_dim: 256
  nhead: 8
  temporal_layers: 4
  num_stages: 7
  dropout: 0.10
loss:
  transition: 1.0
  infiltration: 1.0
  stage: 0.5
  calibration: 0.2
train:
  epochs: 50
  lr: 0.0003
  weight_decay: 0.0001
  grad_clip: 1.0
  checkpoint: best.pt
eval:
  rollout_steps: 8
```

## 1.4 — PASS

The referenced report exists. Its full contents are reproduced in Appendix A, as requested. It is prior reporting, not independent proof of GB10 readiness.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "from pathlib import Path; print('docs/PHASE01_FINAL_REPORT.md exists:',Path('docs/PHASE01_FINAL_REPORT.md').is_file())"
```

```text
docs/PHASE01_FINAL_REPORT.md exists: True
```

Exit code: `0`

## 1.5 — PASS

Both scripts and normalization module exist. The package-relative data/normalization.py is src/cybermind/data/normalization.py, not a top-level data script. Full contents appear in Appendix B.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "from pathlib import Path; [print(p,Path(p).is_file()) for p in ['scripts/phase01_smoke.py','scripts/gpu_preflight.py','src/cybermind/data/normalization.py']]"
```

```text
scripts/phase01_smoke.py True
scripts/gpu_preflight.py True
src/cybermind/data/normalization.py True
```

Exit code: `0`

## 2.1 — PASS

fp32 normalization is implemented, persisted, fitted on training only and applied across splits. Graph construction also accepts a normalizer or loads its path; feature_extract.py need not call it independently.

Source: `src/cybermind/data/normalization.py`

Lines 14–17:

```python
    def __init__(self, width):
        self.count = 0
        self.mean = torch.zeros(width, dtype=torch.float32)
        self.m2 = torch.zeros(width, dtype=torch.float32)
```

Lines 19–34:

```python
    def update(self, values):
        x = torch.as_tensor(values, dtype=torch.float32).detach().cpu()
        if x.ndim != 2 or x.shape[1] != self.mean.numel():
            raise ValueError('Feature width does not match normalization schema')
        if not torch.isfinite(x).all():
            raise ValueError('Cannot fit normalization to non-finite features')
        if not len(x):
            return
        n = len(x)
        mean = x.mean(0)
        m2 = ((x - mean) ** 2).sum(0)
        delta = mean - self.mean
        total = self.count + n
        self.m2 += m2 + delta.square() * (self.count * n / total)
        self.mean += delta * (n / total)
        self.count = total
```

Lines 45–56:

```python
    def __init__(self, constants):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        if constants.get('fit_split') != 'train' or constants.get('dtype') != 'float32':
            raise ValueError('Normalization must be fitted on training data in fp32')
        self.constants = constants
        for key, names in [('node', NODE_FEATURE_NAMES), ('edge', EDGE_FEATURE_NAMES)]:
            if constants[key]['features'] != list(names):
                raise ValueError(f'{key} normalization feature schema mismatch')
            mean = torch.tensor(constants[key]['mean'], dtype=torch.float32)
            std = torch.tensor(constants[key]['std'], dtype=torch.float32)
            if len(mean) != len(names) or len(std) != len(names) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
                raise ValueError(f'Invalid {key} normalization constants')
```

Lines 63–83:

```python
    def fit(cls, states):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        node, edge = RunningMoments(len(NODE_FEATURE_NAMES)), RunningMoments(len(EDGE_FEATURE_NAMES))
        seen = set()
        for state in states:
            if state.metadata.get('split') != 'train':
                raise ValueError('Only training states may fit normalization')
            if state.metadata.get('normalization_fingerprint'):
                raise ValueError('Normalization must fit raw features')
            identity = (state.scenario_id, state.metadata.get('window_start', state.timestamp))
            if identity in seen:
                continue
            seen.add(identity)
            node.update(state.x)
            edge.update(state.edge_attr)
        if not node.count:
            raise ValueError('No training nodes available for normalization')
        return cls({'version': 1, 'fit_split': 'train', 'dtype': 'float32',
                    'method': 'population_mean_std', 'training_windows': len(seen),
                    'node': {'features': list(NODE_FEATURE_NAMES), **node.constants()},
                    'edge': {'features': list(EDGE_FEATURE_NAMES), **edge.constants()}})
```

Lines 85–93:

```python
    def transform(self, values, kind):
        x = values.to(dtype=torch.float32)
        c = self.constants[kind]
        mean = torch.tensor(c['mean'], dtype=torch.float32, device=x.device)
        std = torch.tensor(c['std'], dtype=torch.float32, device=x.device)
        result = (x - mean) / std
        if not torch.isfinite(result).all():
            raise ValueError('Non-finite normalized features')
        return result
```

Lines 95–96:

```python
    def save(self, path):
        Path(path).write_text(json.dumps(self.constants, indent=2), encoding='utf-8')
```

Source: `scripts/prepare_data.py`

Lines 85–121:

```python
def prepare_frames(frames, cfg, purpose='primary', normalizer=None):
    environments = chain_environments(frames, purpose)
    splits = {k: [] for k in (['train', 'val', 'test'] if purpose == 'primary' else ['test'])}
    reports = []
    if purpose == 'heldout' and normalizer is None:
        raise ValueError('Held-out evaluation requires primary training normalization constants')
    for scenario, frame in environments.items():
        partitions = chronological_partitions(frame, cfg['data']['window_seconds'], cfg['data']['stride_seconds']) if purpose == 'primary' else {'test': frame}
        for split, part in partitions.items():
            if part.empty:
                raise ValueError(f'{scenario}/{split}: no events after boundary purge; use more data')
            meta = {'source': str(frame.source.iloc[0]), 'environment_id': str(frame.environment_id.iloc[0]),
                    'source_files': list(dict.fromkeys(part.source_file)), 'split': split,
                    'endpoint_method': 'columns', 'stage_method': 'five_phase_with_unknown',
                    'packet_feature_coverage': float(part.packet_features_available.mean())}
            seqs = make_sequences(part, scenario, window_seconds=cfg['data']['window_seconds'],
                                  history=cfg['data']['history'], stride_seconds=cfg['data']['stride_seconds'],
                                  metadata=meta, normalizer=normalizer)
            splits[split].extend(seqs)
            reports.append({**meta, 'rows': len(part), 'samples': len(seqs), 'labels': sorted(part.label.unique()),
                            'start': str(part.timestamp.min()), 'end': str(part.timestamp.max())})
    if any(not samples for samples in splits.values()):
        raise ValueError('Every requested split must contain sequences; reduce smoke history or supply more data')
    if purpose == 'primary':
        normalizer = FeatureNormalizer.fit(state for sample in splits['train'] for state in sample.states)
        # Overlapping histories share graph objects; transform each only once.
        seen = set()
        for samples in splits.values():
            for sample in samples:
                sample.metadata['normalization_fingerprint'] = normalizer.fingerprint
                for state in sample.states:
                    if id(state) not in seen:
                        state.x = normalizer.transform(state.x, 'node')
                        state.edge_attr = normalizer.transform(state.edge_attr, 'edge')
                        state.metadata['normalization_fingerprint'] = normalizer.fingerprint
                        seen.add(id(state))
    return splits, normalizer, reports
```

Source: `src/cybermind/data/graph_builder.py`

Lines 82–110:

```python
def build_graph_state(window: pd.DataFrame, scenario_id: str, metadata: dict, normalizer=None) -> GraphState:
    nodes = sorted(set(window.src.astype(str)) | set(window.dst.astype(str)))
    nodes = [n for n in nodes if n and n.lower() != 'nan']
    if len(nodes) == 0:
        raise ValueError('No endpoint identities available for graph construction.')
    node_to_idx = {n:i for i,n in enumerate(nodes)}
    x = torch.tensor(_aggregate_node_features(window, nodes),dtype=torch.float32)
    edge_index, edge_attr = _aggregate_edges(window, node_to_idx)
    metadata = dict(metadata)
    if normalizer is None and metadata.get('normalization_path'):
        from .normalization import FeatureNormalizer
        normalizer = FeatureNormalizer.load(metadata['normalization_path'])
    if normalizer is not None:
        x = normalizer.transform(x, 'node')
        edge_attr = normalizer.transform(edge_attr, 'edge')
        metadata['normalization_fingerprint'] = normalizer.fingerprint
    label_counts = window.label.value_counts()
    attack_label = str(label_counts.index[0]) if len(label_counts) else 'BENIGN'
    # The head predicts whether infiltration is present in a window, not the
    # fraction of attack flows. Mixed windows must remain valid binary targets.
    infil = float((window.infiltration > 0).any()) if len(window) else 0.0
    # Class IDs are categorical: averaging them invents a stage never observed.
    stages = window.loc[window.infiltration > 0, 'stage'].value_counts()
    stage = (int(stages.index[0]) if len(stages) == 1 or (len(stages) > 1 and stages.iloc[0] > stages.iloc[1])
             else UNKNOWN_STAGE) if len(stages) else 0
    ts = float(pd.Timestamp(window.timestamp.iloc[0]).timestamp()) if len(window) else 0.0
    return GraphState(x=x,edge_index=edge_index,edge_attr=edge_attr,node_ids=nodes,timestamp=ts,
                      y_infiltration=infil,y_stage=stage,scenario_id=scenario_id,attack_label=attack_label,
                      metadata=dict(metadata))
```

## 2.2 — PASS

Requested IPv4 packet features are computed by the following functions. Scan signatures are heuristics; capture-local state and absence of IPv6 support remain limitations.

Source: `src/cybermind/data/pcap_extract.py`

Lines 21–27:

```python
def _scan_features(ports, minimum_ports=4):
    """Irregular order is a randomized-scan signature, not proof of randomness."""
    unique = list(dict.fromkeys(ports))
    if len(unique) < minimum_ports:
        return float(len(unique)), 0.0, 0.0
    sequential = float(np.mean(np.abs(np.diff(unique)) == 1))
    return float(len(unique)), sequential, 1.0 - sequential
```

Lines 36–57:

```python
def _add_sequence(flow, sequence, length):
    """Count overlapping sequence-space segments, including SYN/FIN retries.

    Pure ACKs are excluded. Interval merging handles resegmentation and wrap.
    """
    if length <= 0:
        return
    modulus = 1 << 32
    end = sequence + length
    spans = [(sequence, min(end, modulus))]
    if end > modulus:
        spans.append((0, end - modulus))
    old = flow['sequence_ranges']
    if any(a < d and c < b for a, b in spans for c, d in old):
        flow['retransmissions'] += 1
    merged = []
    for start, stop in sorted(old + spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(stop, merged[-1][1]))
        else:
            merged.append((start, stop))
    flow['sequence_ranges'] = merged
```

Lines 60–90:

```python
def _row(key, f, label):
    src, dst, proto, sport, dport = key
    duration = max(0.0, f['last'] - f['first'])
    payload = np.asarray(f['payloads'], dtype=np.float64)
    windows = np.asarray(f['windows'], dtype=np.float64)
    count = f['packets']
    stage = classify_stage(label)
    # Aggregate values are available only after the last included packet.
    # Dating them at session start leaks later telemetry into earlier windows.
    return dict(timestamp=pd.to_datetime(f['last'], unit='s'),
                session_start=pd.to_datetime(f['first'], unit='s'), src=src, dst=dst,
                protocol=float(proto), src_port=float(sport), dst_port=float(dport),
                duration=duration, bytes_fwd=float(f['bytes']), bytes_bwd=0.0,
                packets_fwd=float(count), packets_bwd=0.0,
                mean_fwd_iat=float(np.mean(f['iats'])) if f['iats'] else 0.0,
                mean_bwd_iat=0.0, flow_bytes_s=f['bytes']/max(duration, 1e-6),
                flow_packets_s=count/max(duration, 1e-6), label=label,
                infiltration=float(stage != 0), stage=stage, attack_stage=stage,
                ttl_mean=float(np.mean(f['ttls'])), ttl_variance=float(np.var(f['ttls'])),
                tcp_window_mean=float(windows.mean()) if windows.size else 0.0,
                tcp_window_variance=float(windows.var()) if windows.size else 0.0,
                ip_df_ratio=f['df']/count, ip_mf_ratio=f['mf']/count,
                ip_fragment_ratio=f['fragments']/count,
                payload_size_mean=float(payload.mean()), payload_size_variance=float(payload.var()),
                payload_size_min=float(payload.min()), payload_size_max=float(payload.max()),
                payload_size_p25=float(np.quantile(payload, .25)),
                payload_size_p50=float(np.quantile(payload, .5)),
                payload_size_p75=float(np.quantile(payload, .75)),
                scan_unique_ports=f['scan'][0], scan_sequential_score=f['scan'][1],
                scan_randomized_score=f['scan'][2], retransmission_count=float(f['retransmissions']),
                retransmission_ratio=f['retransmissions']/count, packet_features_available=1.0)
```

Lines 93–151:

```python
def pcap_to_dataframe(path: str | Path, label='PCAP_EVENT', session_timeout=300.0):
    """Aggregate IPv4 packets; split flow/host-pair state after inactivity.

    Captures must be chronologically ordered. Missing IPv6 support is explicit:
    non-IPv4 frames are skipped, rather than inventing TTL/fragment statistics.
    """
    if session_timeout <= 0:
        raise ValueError('session_timeout must be positive')
    try:
        from scapy.all import IP, TCP, UDP, PcapReader
    except ImportError as error:
        raise RuntimeError('scapy is required for PCAP extraction') from error
    flows, scans, rows = {}, {}, []
    previous_time = None
    with PcapReader(str(path)) as reader:
        for packet in reader:
            if not packet.haslayer(IP):
                continue
            ip = packet[IP]
            src, dst, proto = str(ip.src), str(ip.dst), int(ip.proto)
            t = float(packet.time)
            if previous_time is not None and t < previous_time:
                raise ValueError('PCAP packets must be in chronological order')
            previous_time = t
            transport = packet[TCP] if packet.haslayer(TCP) else packet[UDP] if packet.haslayer(UDP) else None
            sport, dport = (int(transport.sport), int(transport.dport)) if transport is not None else (0, 0)
            key = (src, dst, proto, sport, dport)
            if key in flows and t - flows[key]['last'] > session_timeout:
                rows.append(_row(key, flows.pop(key), label))
            flow = flows.setdefault(key, _new_flow(t))
            if flow['packets']:
                flow['iats'].append(t - flow['last'])
            flow['last'] = t
            flow['packets'] += 1
            flow['bytes'] += len(packet)
            flow['ttls'].append(int(ip.ttl))
            flow['df'] += bool(int(ip.flags) & 2)
            flow['mf'] += bool(int(ip.flags) & 1)
            flow['fragments'] += bool(int(ip.flags) & 1 or int(ip.frag) > 0)
            payload_length = len(bytes(transport.payload if transport is not None else ip.payload))
            flow['payloads'].append(payload_length)
            if packet.haslayer(TCP):
                tcp = packet[TCP]
                flow['windows'].append(int(tcp.window))
                length = payload_length + bool(int(tcp.flags) & 2) + bool(int(tcp.flags) & 1)
                _add_sequence(flow, int(tcp.seq), length)
            pair = (src, dst, proto)
            if pair not in scans or t - scans[pair]['last'] > session_timeout:
                scans[pair] = dict(last=t, ports=[])
            scan = scans[pair]
            scan['last'] = t
            if transport is not None and dport not in scan['ports']:
                scan['ports'].append(dport)
            # Snapshot only prior/current observations, never future ports.
            flow['scan'] = _scan_features(scan['ports'])
    rows.extend(_row(key, flow, label) for key, flow in flows.items())
    if not rows:
        return pd.DataFrame(columns=('timestamp', 'src', 'dst', 'label', 'stage', 'attack_stage') + PACKET_FEATURES)
    return pd.DataFrame(rows).sort_values('timestamp', kind='stable').reset_index(drop=True)
```

## 2.3 — PASS

Seven labels include distinct C2. Important precision: the adapter calls the Python classifier, not a YAML loader. The equivalent taxonomy is implemented in stages.py; editing YAML alone does not change runtime classification. The existing taxonomy test checks the YAML entries against that classifier.

Source: `knowledge/stage_mapping.yaml`

```text
# Research heuristics, not official ATT&CK ground-truth annotation.
# Benign remains independent of the five named phases and unknown targets.
num_stages: 7
stage_names:
  0: Benign
  1: Reconnaissance
  2: Initial Access
  3: Lateral Movement
  4: Command & Control
  5: Exfiltration
  6: Unknown/Ambiguous
unknown_stage: 6
label_to_stage:
  BENIGN: 0
  NORMAL: 0
  BACKGROUND: 0
  BRUTE FORCE: 2
  BRUTE FORCE -WEB: 2
  BRUTE FORCE -XSS: 2
  FTP-PATATOR: 2
  SSH-PATATOR: 2
  SSH-BRUTEFORCE: 2
  FTP-BRUTEFORCE: 2
  WEB ATTACK - BRUTE FORCE: 2
  WEB ATTACK - XSS: 2
  WEB ATTACK - SQL INJECTION: 2
  SQL INJECTION: 2
  INITIAL ACCESS: 2
  PHISHING: 2
  PORTSCAN: 1
  PORT SCAN: 1
  RECONNAISSANCE: 1
  LATERAL MOVEMENT: 3
  PASS THE HASH: 3
  COMMAND & CONTROL: 4
  COMMAND AND CONTROL: 4
  C2: 4
  BOT: 4
  BOTNET: 4
  EXFILTRATION: 5
  DATA EXFILTRATION: 5
  INFILTRATION: 6
  HEARTBLEED: 6
  DOS ATTACK-HULK: 6
  DOS ATTACK-GOLDENEYE: 6
  DOS ATTACK-SLOWHTTPTEST: 6
  DOS ATTACK-SLOWLORIS: 6
  DDOS ATTACK-HOIC: 6
  DDOS ATTACK-LOIC-HTTP: 6
  DDOS ATTACK-LOIC-UDP: 6
  DDoS: 6
  DoS: 6
  Mirai: 6
  IMPACT: 6
  UNKNOWN: 6
```

Source: `src/cybermind/data/adapters/unified.py`

Lines 91–92:

```python
    def _stage(label):
        return classify_stage(label)
```

Source: `src/cybermind/data/stages.py`

```python
"""Conservative label heuristics; not official ATT&CK ground truth."""
import re
STAGE_NAMES = ('Benign', 'Reconnaissance', 'Initial Access', 'Lateral Movement', 'Command & Control', 'Exfiltration', 'Unknown/Ambiguous')
NUM_STAGES = len(STAGE_NAMES)
UNKNOWN_STAGE = 6


def classify_stage(label: object) -> int:
    text = re.sub(r'[^A-Z0-9]+', ' ', str(label).upper()).strip()
    if text in {'BENIGN', 'NORMAL', 'BACKGROUND', 'LEGITIMATE', '0'}:
        return 0
    matches = set()
    if 'SCAN' in text.split() or any(word in text for word in ('RECON', 'PORTSCAN', 'PORT SCAN', 'PROBE', 'SCANNING')):
        matches.add(1)
    if any(word in text for word in ('INITIAL ACCESS', 'BRUTE', 'PATATOR', 'SQL INJECTION', 'XSS', 'PHISHING')):
        matches.add(2)
    if any(word in text for word in ('LATERAL', 'PASS THE HASH', 'PASS THE TICKET', 'REMOTE SERVICES')):
        matches.add(3)
    if any(word in text for word in ('COMMAND CONTROL', 'COMMAND AND CONTROL', 'BOTNET', 'BEACON')) or text in {'BOT', 'C2', 'C C'}:
        matches.add(4)
    if 'EXFIL' in text:
        matches.add(5)
    return matches.pop() if len(matches) == 1 else UNKNOWN_STAGE
```

Source: `tests/test_packet_taxonomy.py`

Lines 90–100:

```python
def test_named_taxonomy_and_unknowns():
    assert len(STAGE_NAMES) == 7
    cases = {'BENIGN':0, 'PORTSCAN':1, 'SSH-Bruteforce':2, 'Lateral Movement':3, 'BOT':4,
             'Command & Control':4, 'Exfiltration':5, 'DoS':6, 'Infiltration':6,
             'never-seen-attack':6, 'Reconnaissance and Exfiltration':6}
    for label, expected in cases.items():
        assert classify_stage(label) == expected
        assert UnifiedAdapter._stage(label) == expected
    mapping = yaml.safe_load((Path(__file__).resolve().parents[1]/'knowledge/stage_mapping.yaml').read_text(encoding='utf-8-sig'))
    for label, expected in mapping['label_to_stage'].items():
        assert classify_stage(label) == expected, label
```

## 2.4 — PASS

Environment grouping and chronological sorting occur before sequence construction. The adapter explicitly preserves environment_id.

Source: `scripts/prepare_data.py`

Lines 58–67:

```python
def chain_environments(frames, purpose='primary'):
    data = pd.concat(frames, ignore_index=True)
    sources = set(data.source.astype(str))
    if purpose == 'primary' and sources != {PRIMARY_SOURCE}:
        raise ValueError(f'Primary training accepts only {PRIMARY_SOURCE}; found {sorted(sources)}. CTU-13/UNSW-NB15 remain held out.')
    result = {}
    for (source, environment), group in data.groupby(['source', 'environment_id'], sort=True):
        key = f'{source}::{environment}'
        result[key] = group.sort_values(['timestamp', 'source_file'], kind='stable').reset_index(drop=True)
    return result
```

Command (project root):

```text
rg -n -A 2 -B 1 environment_id src/cybermind/data/adapters/unified.py
```

```text
83-        o['source']=self.source
84:        if 'environment_id' in df:
85:            o['environment_id'] = df['environment_id']
86-        o['source_file']=str(getattr(df,'name',''))
87-        o=o[(o.src.notna())&(o.dst.notna())&(o.src.astype(str).str.lower()!='nan')&(o.dst.astype(str).str.lower()!='nan')]
```

Exit code: `0`

## 2.5 — PASS

Automatic explanations are invoked inside forecast(); app/eval call it and emit its explanation. The checklist keyword search in app/eval alone has no matches because implementation is delegated to model/attribution modules. Literal search output and actual call chain follow.

Command (project root):

```text
rg -n attribution|need_weights|occlusion scripts/app.py scripts/eval.py
```

```text
(no stdout)
```

Exit code: `1`

Command (project root):

```text
rg -n forecast|explanation scripts/app.py scripts/eval.py
```

```text
scripts/eval.py:23:            out=m.forecast(states[:-1],1,
scripts/eval.py:32:                    'explanation':out['explanation'],
scripts/eval.py:35:    result={'split':args.split,'forecast_horizon_windows':1,'metrics':metrics,'per_sample':per}
scripts/app.py:2:"""Offline Streamlit war-room UI. Requires a trained checkpoint for live forecasts."""
scripts/app.py:27:    out=m.forecast(sample.states[:-1],cfg['eval']['rollout_steps'],
scripts/app.py:43:st.subheader('Prediction explanation')
scripts/app.py:44:st.json(out['explanation'])
```

Exit code: `0`

Source: `src/cybermind/models/world_model.py`

Lines 63–83:

```python
    def forecast(self, states, k=4, n_rollouts=16, seed=0, explain=True, topk=10):
        """Forecast with reproducible Gaussian rollouts and automatic explanations.

        Step zero is the observed latent; subsequent steps are stochastic futures.
        Variance is predictive dispersion, not a calibrated confidence decision.
        Internal perturbation probes use explain=False to avoid recursive work.
        """
        if not states or k < 0 or n_rollouts < 2:
            raise ValueError('forecast requires states, k >= 0 and n_rollouts >= 2')
        modes = [(module, module.training) for module in self.modules()]
        self.eval()
        try:
            result, attention = self._forecast_core(states, k, n_rollouts, seed, return_attention=explain)
            if explain:
                from cybermind.explainability.attribution import explain_forecast
                result['explanation'] = explain_forecast(
                    self, states, result, attention, k=k, n_rollouts=n_rollouts, seed=seed, topk=topk)
            return result
        finally:
            for module, training in modes:
                module.training = training
```

Source: `src/cybermind/models/temporal_encoder.py`

Lines 10–10:

```python
    def forward(self,x): return x + self.pe[:,:x.size(1)]
```

Lines 17–34:

```python
    def forward(self, x, return_attention=False):
        x = self.pos(self.proj(x))
        mask = torch.ones(x.size(1), x.size(1), dtype=torch.bool, device=x.device).triu(1)
        attention = []
        # Explicit pre-norm layers avoid fused eval paths bypassing attention extraction.
        # Causality prevents next-window training targets leaking into current states.
        for layer in self.encoder.layers:
            q = layer.norm1(x)
            attended, weights = layer.self_attn(q, q, q, attn_mask=mask,
                                                need_weights=return_attention,
                                                average_attn_weights=False)
            x = x + layer.dropout1(attended)
            q = layer.norm2(x)
            x = x + layer.dropout2(layer.linear2(layer.dropout(layer.activation(layer.linear1(q)))))
            if return_attention:
                attention.append(weights.detach())
        x = self.encoder.norm(x)
        return (x, torch.stack(attention)) if return_attention else x
```

Source: `src/cybermind/explainability/attribution.py`

Lines 13–29:

```python
def gradient_feature_attribution(model, state, k=4, topk=10, n_rollouts=16, seed=0):
    states = list(state) if isinstance(state, (list, tuple)) else [state]
    # Also works when the caller wraps inference in no_grad/inference_mode.
    # autograd.grad leaves parameter gradients untouched.
    with torch.inference_mode(False), torch.enable_grad():
        xs = [s.x.detach().clone().requires_grad_(True) for s in states]
        probes = [replace(s, x=x, edge_index=s.edge_index.clone(), edge_attr=s.edge_attr.clone())
                  for s, x in zip(states, xs)]
        result = model.forecast(probes, k, n_rollouts=n_rollouts, seed=seed, explain=False)
        score = result['infiltration_probability'][-1]
        gradients = torch.autograd.grad(score, xs, allow_unused=True)
        products = [torch.zeros_like(x) if g is None else g * x for x, g in zip(xs, gradients)]
        attribution = torch.cat(products).abs().mean(dim=0).detach().float().cpu()
        signed = torch.cat(products).mean(dim=0).detach().float().cpu()
    values = [{'feature': name, 'attribution': float(attribution[i]), 'signed_attribution': float(signed[i])}
              for i, name in enumerate(_feature_names(len(attribution)))]
    return sorted(values, key=lambda item: item['attribution'], reverse=True)[:topk]
```

Lines 32–63:

```python
def explain_forecast(model, states, forecast, attention, k=4, n_rollouts=16, seed=0, topk=10):
    features = gradient_feature_attribution(model, states, k, topk, n_rollouts, seed)
    # [layers,batch,heads,query,key]: final query averaged across layers/heads.
    weights = attention[:, 0, :, -1, :].mean(dim=(0, 1)).float().cpu()
    temporal = sorted(
        [{'window_index': i, 'timestamp': float(s.timestamp), 'attention': float(weights[i])}
         for i, s in enumerate(states)], key=lambda item: item['attention'], reverse=True)
    baseline = float(forecast['infiltration_probability'][-1].detach().cpu())
    occlusion = []
    with torch.no_grad():
        for i, name in enumerate(_feature_names(states[0].x.size(-1))):
            probes = []
            for state in states:
                x = state.x.detach().clone()
                x[:, i] = 0.0
                probes.append(replace(state, x=x))
            # Common random draws isolate input changes from Monte Carlo noise.
            result = model.forecast(probes, k, n_rollouts=n_rollouts, seed=seed, explain=False)
            risk = float(result['infiltration_probability'][-1].cpu())
            occlusion.append({'feature': name, 'baseline_risk': baseline,
                              'counterfactual_risk': risk, 'risk_reduction': baseline - risk})
    occlusion.sort(key=lambda item: item['risk_reduction'], reverse=True)
    return {
        'target': 'ensemble_mean_infiltration_probability_at_final_step',
        'gradient_x_input': features,
        'temporal_attention': temporal,
        'feature_occlusion': occlusion[:topk],
        'what_would_reduce_risk': [item for item in occlusion if item['risk_reduction'] > 0][:topk],
        'baseline_risk': baseline, 'n_rollouts': n_rollouts, 'seed': seed,
        'occlusion_baseline': 'zero in model feature space (training mean for normalized continuous features)',
        'interpretation': 'Model sensitivity and attention; not proof of causality or calibrated confidence.',
    }
```

## 2.6 — PASS

Training-derived negative/positive weight is passed into BCE. Counts are target occurrences in overlapping sequences, not deduplicated windows. No upper cap is implemented; real-data suitability is UNKNOWN under 4.3.

Source: `src/cybermind/losses.py`

Lines 12–14:

```python
def infiltration_loss(logits, target, pos_weight=None):
    weight = None if pos_weight is None else torch.as_tensor(pos_weight, device=logits.device, dtype=torch.float32)
    return F.binary_cross_entropy_with_logits(logits.float(), target.float(), pos_weight=weight)
```

Source: `scripts/train.py`

Lines 22–30:

```python
def training_class_weight(dataset):
    # Count exactly the target-window occurrences consumed by the training loss.
    labels = [float(s.y_infiltration) for sample in dataset for s in sample.states[1:]]
    if not labels or any(y not in (0., 1.) for y in labels):
        raise ValueError('Training infiltration labels must be binary and nonempty.')
    positive = int(sum(labels)); negative = len(labels) - positive
    if not positive or not negative:
        raise ValueError('Training split must contain benign and infiltration target windows.')
    return negative / positive, {'positive': positive, 'negative': negative}
```

Command (project root):

```text
rg -n "pos_weight|weight, counts" scripts/train.py
```

```text
81:    l_infil = infiltration_loss(logits, labels, cfg['loss'].get('pos_weight'))
156:    weight, counts = training_class_weight(train); cfg['loss']['pos_weight'] = weight
186:    print({'device': str(device), 'precision': precision, 'class_counts': counts, 'pos_weight': weight, 'selection': 'val_f1'})
215:                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
```

Exit code: `0`

## 2.7 — PASS

Consistency is computed and included in weighted summed total. Full batch_loss code:

Source: `scripts/train.py`

Lines 64–96:

```python
def batch_loss(model, batch, cfg, device, *, return_predictions=False):
    states = []
    for sample in batch:
        if len(sample.states) < 2:
            raise ValueError('Each training sequence needs at least two windows.')
        states.append([replace(s, x=s.x.to(device, non_blocking=True),
                               edge_index=s.edge_index.to(device, non_blocking=True),
                               edge_attr=s.edge_attr.to(device, non_blocking=True))
                       for s in sample.states])
    z = model.forward_batch(states)['temporal_latents']
    distribution = model.dynamics(z[:, :-1])
    mean, logvar = distribution['mean'], distribution['logvar']
    target = z[:, 1:].detach()
    l_trans = gaussian_transition_loss(mean, target, logvar)
    pred = model.dynamics.sample(mean, logvar) if model.training else mean
    logits = model.infiltration_head(pred).reshape(-1)
    labels = torch.tensor([s.y_infiltration for ss in states for s in ss[1:]], dtype=torch.float32, device=device)
    l_infil = infiltration_loss(logits, labels, cfg['loss'].get('pos_weight'))
    l_brier = binary_brier(logits, labels)
    stage_logits = model.stage_head(pred).reshape(-1, cfg['model']['num_stages'])
    stage_labels = torch.tensor([s.y_stage for ss in states for s in ss[1:]], dtype=torch.long, device=device)
    if torch.any((stage_labels < 0) | (stage_labels >= cfg['model']['num_stages'])):
        raise ValueError('Invalid stage ID; rebuild data with the current taxonomy.')
    l_stage = stage_loss(stage_logits.float(), stage_labels)
    l_consistency = graph_consistency_loss(z)
    components = {'transition': l_trans, 'infiltration': l_infil, 'stage': l_stage,
                  'calibration': l_brier, 'graph_consistency': l_consistency}
    total = sum(cfg['loss'].get(name, .1 if name == 'graph_consistency' else 0.) * value
                for name, value in components.items())
    parts = {k: float(v.detach()) for k, v in components.items()}
    if return_predictions:
        return total, parts, torch.sigmoid(logits.float()).detach(), labels.detach()
    return total, parts
```

## 2.8 — PASS

Dynamics returns mean/log-variance and reparameterizes; forecast expands the initial latent to N trajectories before rollout.

Source: `src/cybermind/models/dynamics.py`

```python
"""Diagonal Gaussian latent transitions with differentiable sampled rollouts."""
from __future__ import annotations
import torch
from torch import nn


class DynamicsModel(nn.Module):
    def __init__(self, latent_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(latent_dim, hidden_dim), nn.GELU(),
                                 nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, latent_dim))
        self.gate = nn.Sequential(nn.Linear(latent_dim, latent_dim), nn.Sigmoid())
        self.logvar_net = nn.Sequential(nn.Linear(latent_dim, hidden_dim), nn.GELU(),
                                       nn.Linear(hidden_dim, latent_dim))
        nn.init.constant_(self.logvar_net[-1].bias, -4.0)

    def forward(self, z):
        return {'mean': z + self.gate(z) * self.net(z),
                'logvar': self.logvar_net(z).clamp(-10.0, 5.0)}

    @staticmethod
    def sample(mean, logvar, generator=None):
        noise = torch.randn(mean.shape, dtype=mean.dtype, device=mean.device, generator=generator)
        return mean + torch.exp(0.5 * logvar) * noise

    def rollout(self, z0, steps, generator=None, stochastic=True):
        if steps < 0:
            raise ValueError('steps must be nonnegative')
        zs = [z0]
        z = z0
        for _ in range(steps):
            params = self(z)
            z = self.sample(**params, generator=generator) if stochastic else params['mean']
            zs.append(z)
        return torch.stack(zs, dim=0)
```

Source: `src/cybermind/models/world_model.py`

Lines 41–61:

```python
    def _forecast_core(self, states, k, n_rollouts, seed, return_attention=False):
        out = self.forward(states, return_attention=return_attention)
        z0 = out['temporal_latents'][-1]
        generator = torch.Generator(device=z0.device).manual_seed(seed)
        # Vectorize independent trajectories: [steps+1, rollouts, latent_dim].
        latent_samples = self.dynamics.rollout(z0.expand(n_rollouts, -1), k, generator=generator)
        risk_samples = self.infiltration_head(latent_samples).float().sigmoid()
        probabilities = risk_samples.mean(dim=1)
        stage_probabilities = self.stage_head(latent_samples).float().softmax(dim=-1).mean(dim=1)
        result = {
            'latent': latent_samples.mean(dim=1),
            'latent_samples': latent_samples.permute(1, 0, 2),
            'infiltration_logits': torch.logit(probabilities.clamp(1e-7, 1 - 1e-7)),
            'infiltration_probability': probabilities,
            'infiltration_variance': risk_samples.var(dim=1, unbiased=False),
            'rollout_probabilities': risk_samples.transpose(0, 1),
            'stage_logits': stage_probabilities.clamp_min(1e-7).log(),
            'future_state': self.state_head(latent_samples).mean(dim=1),
            'n_rollouts': n_rollouts, 'seed': seed,
        }
        return result, out['temporal_attention']
```

## 2.9 — PASS

Best checkpoint uses validation F1 rather than training loss.

Command (project root):

```text
rg -n -A 18 "metrics = validate" scripts/train.py
```

```text
206:        metrics = validate(model, val_loader, cfg, device, precision)
207-        rec = {'epoch': ep + 1, 'train': {k: v / count for k, v in sums.items()}, 'val': metrics}
208-        history.append(rec); print(rec)
209-        improved = metrics['f1'] > best + cfg['train'].get('min_delta', 0.)
210-        stale = 0 if improved else stale + 1
211-        if improved: best = metrics['f1']
212-        payload = {'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(),
213-                   'scaler_state': scaler.state_dict() if scaler else None, 'config': cfg, 'node_dim': node_dim,
214-                   'epoch': ep + 1, 'best_metric': best, 'selection_metric': 'val_f1', 'validation': metrics,
215-                   'class_counts': counts, 'pos_weight': weight, 'normalization': normalization,
216-                   'normalization_path': str(normalization_path) if normalization else None,
217-                   'epochs_without_improvement': stale, 'history': history}
218-        if improved: torch.save(payload, checkpoint)
219-        torch.save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
220-        history_path.write_text(json.dumps(history, indent=2))
221-        if stale >= int(cfg['train'].get('early_stopping_patience', 10)):
222-            print('Early stopping on validation F1.'); break
223-    print('Best validation checkpoint:', checkpoint)
224-
```

Exit code: `0`

## 3.1 — FAIL

Legacy command blocks remain despite the top banner. Quickstart uses smoke.yaml and gpu_128gb.yaml; One-command training resumes best_128gb.pt and its launcher defaults to gpu_128gb.yaml; Final pre-training automation explicitly uses gpu_128gb.yaml; One-command lab training invokes a helper hardcoded to gpu_128gb.yaml. No edits were made in this reporting pass.

Command (project root):

```text
rg -n gpu_128gb|best_128gb|smoke.yaml|final.yaml|^## README.md
```

```text
5:## Current Phase 0–1 handoff (2026-09-11)
9:the verified checklist and Phase 2 commands. Older `gpu_128gb.yaml`/one-click
21:## What is implemented
43:## Scientific honesty
49:## Quickstart
55:python scripts/prepare_data.py --config configs/smoke.yaml --input data/intermediate --strict
56:python scripts/train.py --config configs/smoke.yaml
57:python scripts/eval.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt
58:python scripts/visualize_rollout.py --config configs/smoke.yaml --checkpoint checkpoints/smoke.pt
60:python scripts/gpu_preflight.py --config configs/gpu_128gb.yaml
61:python scripts/train.py --config configs/gpu_128gb.yaml
64:For real training, edit `configs/final.yaml` to match the actual data volume and GPU.
66:## Real-data path
81:## Folder layout
104:## Public-source registry
108:## Offline demo
114:## One-command training
132:CYBERMIND_RESUME=checkpoints/best_128gb.pt ./scripts/run_training_from_zero.sh
141:## Final pre-training automation
146:./scripts/launch_training.py --config configs/gpu_128gb.yaml --train-only
152:python scripts/launch_training.py --config configs/gpu_128gb.yaml --download-cic2018
158:python scripts/launch_training.py --config configs/gpu_128gb.yaml --epochs 1
161:## Laptop export
171:## Safety boundary
176:## ONNX safety guardrails
181:## One-command lab training
194:python scripts/launch_training.py --config configs/gpu_128gb.yaml --no-download-cic2018
```

Exit code: `0`

Command (project root):

```text
rg -n gpu_128gb|best_128gb|launch_training scripts/one_click_train.py scripts/run_training_from_zero.sh scripts/launch_training.py
```

```text
scripts/run_training_from_zero.sh:6:ARGS=(--config "${CYBERMIND_CONFIG:-configs/gpu_128gb.yaml}")
scripts/run_training_from_zero.sh:10:python scripts/launch_training.py "${ARGS[@]}"
scripts/launch_training.py:84:        "config": "configs/gpu_128gb.yaml",
scripts/launch_training.py:93:    ap.add_argument("--config", default="configs/gpu_128gb.yaml")
scripts/one_click_train.py:26:    cmd = [PYTHON, str(ROOT / "scripts/launch_training.py"),
scripts/one_click_train.py:27:           "--config", "configs/gpu_128gb.yaml", "--download-cic2018"]
```

Exit code: `0`

## 3.2 — FAIL

The file is .gitignore. *.pt, results/*.json and results/*.png are excluded: ordinary git add/push will omit matching untracked checkpoints/results unless explicitly included. Already-tracked files are not affected by ignore rules. This workspace is not currently a Git repository, so tracked/force-added status cannot be checked. Submission-artifact inclusion remains unresolved.

Source: `.gitignore`

```text
__pycache__/
*.pyc
.venv/
.env
*.pt
*.pkl
*.joblib
results/*.json
results/*.png
data/raw/CIC-IDS-2018/*.csv
data/raw/CIC-IDS-2018/*.pcap
data/intermediate/*
```

Command (project root):

```text
git rev-parse --is-inside-work-tree
```

```text
(no stdout)
```

stderr:

```text
fatal: not a git repository (or any of the parent directories): .git
```

Exit code: `128`

## 4.1 — UNKNOWN

No real single-day CIC subset was prepared or profiled. Prior runs were synthetic. Local data directory listing and integration evidence follow; these do not describe any remote GB10 storage.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe -c "from pathlib import Path; [print(p) for p in sorted(Path('data').rglob('*')) if p.is_file()]"
```

```text
data\manifests\.gitkeep
data\manifests\dataset_registry.csv
data\manifests\DOWNLOAD_MATRIX.md
data\manifests\schema.json
data\manifests\SOURCE_PROVENANCE.md
```

Exit code: `0`

Source: `examples/phase01_integration/verification.json`

```text
{
  "synthetic_only": true,
  "real_training_performed": false,
  "steps_passed": 4,
  "evaluated_samples": 25,
  "automatic_explanations": true,
  "warning": "CIC-IDS2018 is a fixture routing value. These generated rows are NOT real CIC data or accuracy evidence."
}
```

## 4.2 — UNKNOWN

No measured memory/file-count series exists. Linear or worse-than-linear scaling cannot be concluded. No extrapolation fabricated.

## 4.3 — UNKNOWN

Real positive/negative ratio and stability of pos_weight have not been measured. Source under 2.6 shows uncapped negative/positive weighting. Existing synthetic training log is quoted solely as fixture evidence:

Command (project root):

```text
rg -n class_counts|pos_weight examples/phase01_integration/step_3.log
```

```text
5:{'device': 'cpu', 'precision': 'fp32', 'class_counts': {'positive': 60, 'negative': 184}, 'pos_weight': 3.066666666666667, 'selection': 'val_f1'}
```

Exit code: `0`

## 4.4 — UNKNOWN

Real any-attack versus majority-vote positive-window fractions have not been calculated. The actual rule is quoted below; a passing synthetic regression does not supply those real-data percentages.

Command (project root):

```text
rg -n -B 2 -A 1 "infil =" src/cybermind/data/graph_builder.py
```

```text
100-    # The head predicts whether infiltration is present in a window, not the
101-    # fraction of attack flows. Mixed windows must remain valid binary targets.
102:    infil = float((window.infiltration > 0).any()) if len(window) else 0.0
103-    # Class IDs are categorical: averaging them invents a stage never observed.
```

Exit code: `0`

## 4.5 — UNKNOWN

Real PCAP availability and packet-to-label alignment are unverified. Legacy PCAP helper uses filename-derived labels, which are not genuine packet-level ground truth.

Source: `scripts/pcap_to_corpus.py`

Lines 9–14:

```python
def infer_label(path: Path):
    x=path.stem.upper()
    if any(k in x for k in ['BENIGN','NORMAL']): return 'BENIGN'
    for k in ['DDOS','DOS','BOTNET','MIRAI','BRUTE','SCAN','RECON','INFILTRATION','HEARTBLEED','SQL','XSS','BACKDOOR','WORM']:
        if k in x: return k
    return 'PCAP_EVENT'
```

Command (project root):

```text
rg -n infer_label|pcap_to_dataframe scripts/pcap_to_corpus.py
```

```text
7:from cybermind.data.pcap_extract import pcap_to_dataframe
9:def infer_label(path: Path):
21:        label=infer_label(f); df=pcap_to_dataframe(f,label=label); df['source']='PCAP'; df['source_file']=str(f)
```

Exit code: `0`

## 5.1 — UNKNOWN

GB10 access duration was not supplied and cannot be inferred from code.

## 5.2 — UNKNOWN

Target-host preflight was not run. Local preflight FAILS; full current stdout/stderr and exit code follow. This is not a GB10 result.

Command (project root):

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Scripts\python.exe scripts/gpu_preflight.py --config configs/gb10_full.yaml
```

```text
Python 3.12.14 PyTorch 2.14.0+cpu
PyG 2.8.0.post1
STOP: CUDA is unavailable on this runtime.
STOP: Missing: C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\data\processed_gb10\train.pt
STOP: Missing: C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\data\processed_gb10\val.pt
STOP: Missing: C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\data\processed_gb10\test.pt
STOP: Missing: C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\data\processed_gb10\normalization.json
STOP: Missing: C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\data\processed_gb10\metadata.json
```

stderr:

```text
C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\jit\_script.py:1491: FutureWarning: `torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`.
  warnings.warn(
```

Exit code: `1`

## 5.3 — UNKNOWN

No one-epoch GB10 run or GPU-memory profile exists. Earlier two-epoch CPU smoke training is not a substitute. No training was started during this reporting pass.

## 5.4 — UNKNOWN

Early stopping is configured and the source contains an active break condition (code PASS), but a run actually reaching that condition has not been demonstrated; GB10 firing behavior remains UNKNOWN.

Command (project root):

```text
rg -n early_stopping|min_delta|selection_metric configs/gb10_full.yaml
```

```text
40:  selection_metric: val_f1
42:  early_stopping_patience: 8
43:  min_delta: 0.0001
```

Exit code: `0`

Command (project root):

```text
rg -n -A 4 -B 2 "stale >=" scripts/train.py
```

```text
219-        torch.save(payload, checkpoint.with_name(checkpoint.stem + '_last.pt'))
220-        history_path.write_text(json.dumps(history, indent=2))
221:        if stale >= int(cfg['train'].get('early_stopping_patience', 10)):
222-            print('Early stopping on validation F1.'); break
223-    print('Best validation checkpoint:', checkpoint)
224-
225-
```

Exit code: `0`

## 6.1 — PASS

Deferred boundary preserved in inspected forecast/app/eval paths: variance is returned as dispersion; no operational variance-confidence gate is applied. Real validation of uncertainty is still not done.

Command (project root):

```text
rg -n variance|confidence|threshold src/cybermind/models/world_model.py scripts/app.py scripts/eval.py
```

```text
scripts/eval.py:13:    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--split',default='test'); p.add_argument('--threshold',type=float,default=.5); p.add_argument('--output',help='Report path; defaults to results/eval_SPLIT.json'); args=p.parse_args(); cfg=load_config(args.config)
scripts/eval.py:31:                    'predictive_variance':float(out['infiltration_variance'][-1].item()),
scripts/eval.py:33:                    **early_warning_lead_time(ts,yy,np.pad(np.array(hist), (0,max(0,len(ts)-len(hist))))[:len(ts)],args.threshold)})
scripts/eval.py:34:    metrics=binary_metrics(all_y,all_p,args.threshold); metrics['mean_lead_time_seconds']=float(np.mean([x['lead_time_seconds'] for x in per if x['lead_time_seconds'] is not None])) if any(x['lead_time_seconds'] is not None for x in per) else None
src/cybermind/models/world_model.py:55:            'infiltration_variance': risk_samples.var(dim=1, unbiased=False),
src/cybermind/models/world_model.py:67:        Variance is predictive dispersion, not a calibrated confidence decision.
```

Exit code: `0`

## 6.2 — PASS

Primary source is restricted to CIC-IDS2018; held-out sources are rejected on primary paths. This verifies code separation, not the contents of an absent real training dataset.

Source: `scripts/build_corpus.py`

Lines 13–15:

```python
def validate_source(source, purpose):
    if purpose == 'primary' and source != 'CIC-IDS2018':
        raise ValueError('Primary training is CIC-IDS2018 only. Use --purpose heldout and a separate directory for other datasets.')
```

Source: `scripts/prepare_data.py`

Lines 58–67:

```python
def chain_environments(frames, purpose='primary'):
    data = pd.concat(frames, ignore_index=True)
    sources = set(data.source.astype(str))
    if purpose == 'primary' and sources != {PRIMARY_SOURCE}:
        raise ValueError(f'Primary training accepts only {PRIMARY_SOURCE}; found {sorted(sources)}. CTU-13/UNSW-NB15 remain held out.')
    result = {}
    for (source, environment), group in data.groupby(['source', 'environment_id'], sort=True):
        key = f'{source}::{environment}'
        result[key] = group.sort_values(['timestamp', 'source_file'], kind='stable').reset_index(drop=True)
    return result
```

## 6.3 — PASS

The inspected world-model forecast runs forward on the supplied states without a flow-threshold prefilter. The forecast and _forecast_core methods quoted in 2.5 and 2.8 show the unconditional path; evaluation thresholds act after predictions.

Command (project root):

```text
rg -n "forecast|threshold|for sample" scripts/eval.py
```

```text
13:    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--split',default='test'); p.add_argument('--threshold',type=float,default=.5); p.add_argument('--output',help='Report path; defaults to results/eval_SPLIT.json'); args=p.parse_args(); cfg=load_config(args.config)
17:    for sample in ds:
23:            out=m.forecast(states[:-1],1,
33:                    **early_warning_lead_time(ts,yy,np.pad(np.array(hist), (0,max(0,len(ts)-len(hist))))[:len(ts)],args.threshold)})
34:    metrics=binary_metrics(all_y,all_p,args.threshold); metrics['mean_lead_time_seconds']=float(np.mean([x['lead_time_seconds'] for x in per if x['lead_time_seconds'] is not None])) if any(x['lead_time_seconds'] is not None for x in per) else None
35:    result={'split':args.split,'forecast_horizon_windows':1,'metrics':metrics,'per_sample':per}
```

Exit code: `0`

## Previous test evidence (not rerun in this reporting pass)

Source: `examples/phase01_integration/pytest.log`

```text
.............................                                            [100%]
============================== warnings summary ===============================
.phase01-venv\Lib\site-packages\torch\jit\_script.py:1491
  C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.phase01-venv\Lib\site-packages\torch\jit\_script.py:1491: FutureWarning: `torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`.
    warnings.warn(

tests/test_phase01_training.py::test_joint_backward_all_heads_and_regularizer
tests/test_stochastic_forecast.py::test_temporal_causality_and_attention
tests/test_stochastic_forecast.py::test_automatic_explanation_under_inference_context[no_grad]
tests/test_stochastic_forecast.py::test_automatic_explanation_under_inference_context[inference_mode]
tests/test_stochastic_forecast.py::test_reproducible_rollouts_and_training_contract
  C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\src\cybermind\models\temporal_encoder.py:16: UserWarning: enable_nested_tensor is True, but self.use_nested_tensor is False because encoder_layer.norm_first was True
    self.encoder=nn.TransformerEncoder(layer,num_layers=layers,norm=nn.LayerNorm(model_dim))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
29 passed, 6 warnings in 6.70s
```

## Appendix A — full prior Phase 0–1 report

Source: `docs/PHASE01_FINAL_REPORT.md`

````text
# CYBERMIND: Phase 0–1 final report

Date: 2026-09-11

**Outcome: Phase 0–1 code and local correctness checks completed. Phase 2 was not started.**
You can proceed to Phase 2 preparation on the GB10 host. Start real training only
after the real corpus and target runtime pass the preflight below. This is not an
unconditional certification that a full-corpus training run will fit or succeed.

## Scope recovered from the shared chat

Source: [Execute implementation plan phase 1](https://chatgpt.com/s/cx_6aa38eee2fa081918d99307e55d359e7).
The shared page exposed the prior user request and expanded progress messages.
It requested completion through Phase 1, a recheck, and a stop before Phase 2.
No completed final report was visible in that shared view. This audit also read
`C:\Users\as030\Downloads\CYBERMIND_Implementation_Plan.md` and checked the actual
workspace rather than treating prior progress statements as proof of completion.

The earlier run had implemented most changes and reported packet/taxonomy and
training tests plus a synthetic training run. Its last visible unfinished items
were normalization/chaining verification, explanation integration, and the final
checklist/GB10 handoff. Those were the continuation point.

## Completed checklist

| Plan item | Verified implementation | Result |
| --- | --- | --- |
| 0.1 Normalization | `data/normalization.py`: fp32 population mean/std over unique training graph windows, stored constants and schema fingerprint; validation/test transform only; inference contract checks | Complete locally |
| 0.2 Packet features | TTL/window mean and variance; fragmentation flags; payload distribution; sequential/irregular port-access signatures; overlapping TCP sequence retransmissions | Complete; synthetic PCAP tests |
| 0.3 Stage taxonomy | Benign plus Reconnaissance, Initial Access, Lateral Movement, Command & Control, Exfiltration, Unknown/Ambiguous; shared adapter/YAML taxonomy | Complete: seven output labels |
| 0.4 Chronological chaining | Source/environment grouping across files; timestamp ordering; stable endpoint names; chronological event splits with a window purge | Complete; cross-file and leakage checks |
| 0.5 Automatic explanations | `forecast()` emits gradient×input, temporal attention, feature occlusion and risk-reduction suggestions; evaluation and app surface explanations | Complete; tested under no-grad and inference-mode |
| 0.6 Class imbalance | Positive weight derived from training target occurrences; weighted infiltration BCE; rejects single-class training | Complete |
| 0.7 Consistency loss | Consecutive latent consistency included in training loss and separate logs | Complete |
| 0.8 Stochastic dynamics | Mean/log-variance, Gaussian transition loss, reparameterized samples, reproducible multiple-rollout mean and variance | Complete; shape and gradient checks |
| 1.1 Primary corpus decision | Primary path accepts CIC-IDS2018 only; CTU-13/UNSW-NB15 use separate held-out mode and primary normalization constants | Complete; real corpus not acquired |
| 1.2 GB10 config | `configs/gb10_full.yaml`: 512-wide graph/temporal model, six temporal layers, bf16, full joint training, batch 8 × accumulation 8 | Complete; batch size remains to be profiled on GB10 |
| 1.3 Checkpoint selection | Validation infiltration F1, early stopping, best/last checkpoints, separate loss logs; bf16 does not instantiate GradScaler | Complete |

Optional encoder pretraining was not added; the configured default is joint training.
Attention/occlusion work overlaps Phase 4 but was already part of the Phase 0
explanation implementation. No remaining Phase 3–7 work was undertaken as a new phase.

## Changes made during this continuation

1. Fixed mixed benign/attack graph windows. Their target now means “at least one
   attack event is present” (binary), rather than a fractional attack-flow ratio
   rejected by class-weight calculation. This also keeps metric targets binary.
2. Preserved explicit `environment_id` through the unified adapter so different
   deployments are not merged before chronological chaining.
3. Corrected PCAP aggregate timestamps to the last included packet, retaining
   `session_start` separately. Completed session statistics no longer appear at
   the first packet before their inputs were available.
4. Aligned benign aliases in canonical preparation with the stage taxonomy.
5. Added regression coverage for mixed targets, environment preservation, benign
   aliases and aggregate timing.
6. Added `scripts/phase01_smoke.py`, a repeatable synthetic integration check using
   the current feature schema, normalized data, separate splits and explanations.
7. Reworked `scripts/gpu_preflight.py`: it now honors the selected config and its
   processed-data directory, checks the requested precision, validates splits,
   classes and normalization/packet provenance, and exits nonzero on failure.
   The older check ignored the config and printed failures without failing.
8. Pointed the app's default checkpoint at `best_gb10.pt`; the
   `CYBERMIND_CHECKPOINT` environment variable can select another compatible file.
9. Updated README/status pointers to the current handoff and marked older
   one-click/config instructions as legacy.

## Executed verification and evidence

Runtime used: project `.phase01-venv`, Python 3.12.14, PyTorch 2.14.0+cpu,
PyG 2.8.0.post1. These versions describe the tested local environment, not a
certified GB10 software stack.

- **29 pytest checks passed**, with six non-failing PyTorch warnings.
  Evidence: `examples/phase01_integration/pytest.log`.
- **Four integration stages passed**: `build_corpus.py` → `prepare_data.py` →
  two-epoch CPU `train.py` → `eval.py`.
- Fixture: 360 generated flow rows in two deliberately misordered filenames;
  122 training, 25 validation and 25 test sequences after split purging.
- All 25 evaluated test sequences emitted automatic feature-occlusion explanations.
- Source/scripts compile check passed (`python -m compileall -q src scripts`).
- Production preflight correctly returned exit code 1 locally: CUDA unavailable
  and five required production data/metadata artifacts missing.

Artifacts:

- `examples/phase01_integration/verification.json`: machine-readable integration result.
- `examples/phase01_integration/step_1.log` through `step_4.log`: command output.
- `examples/phase01_integration/processed/normalization.json` and `metadata.json`:
  fixture normalization/split evidence.
- `examples/phase01_integration/train_history.json`: separate training/validation losses.
- `examples/phase01_integration/eval_test.json`: synthetic forecasts and explanations.
- `checkpoints/phase01_integration.pt` and `phase01_integration_last.pt`: synthetic checkpoints.

**None of these are real CIC-IDS2018 results.** The fixture uses the source name
only to exercise primary-corpus routing and labels its environment
`SYNTHETIC_FIXTURE_ONLY`. It is not input for production training. Synthetic
precision/F1 values are deliberately not presented as detection-performance evidence.
No trained ONNX artifact or live Streamlit UI was verified in this continuation.

## GB10 handoff: Phase 2, for the next execution

From the `CYBERMIND_REAL` project root, use a GB10-compatible CUDA/PyTorch/PyG
environment. Recreate the environment on that host; do not copy the Windows CPU venv.
Supply the complete primary corpus with real endpoint identities, timestamps,
labels, environment IDs and packet features derived from actual captures.
Plain flow CSVs missing packet telemetry must be enriched before feature-complete
training. The legacy PCAP helper's filename-derived labels are not ground truth;
an actual packet-to-label alignment is still required for real data preparation.

Commands to run in Phase 2, **not executed here against real data**:

```bash
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/prepare_data.py --config configs/gb10_full.yaml --input data/intermediate/CIC-IDS2018 --strict
python scripts/gpu_preflight.py --config configs/gb10_full.yaml
# Continue only after preflight succeeds:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --epochs 1
# Inspect logs and actual memory use before extending the same run:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --resume checkpoints/best_gb10_last.pt
```

The full configured run totals 50 epochs including a resumed first epoch.
Check the supplied files cover all intended days/attack types; a source-name check
cannot establish completeness. Full-corpus preparation currently materializes
data/graphs in memory and has not been profiled at that scale. The 128 GB is shared
with data, runtime and optimizer state, so batch 8 is a starting value, not a fit guarantee.

Additional limits: packet extraction handles IPv4; scan/session state is local to
a capture; dataset-derived stage labels remain proxies; rollout variance is not
calibrated confidence; counterfactual reductions are model sensitivity, not causal
effects. Existing checkpoints with the old schema need retraining.

## Stop boundary and readiness signal

**GO for Phase 2 preparation and target-host preflight. Conditional GO for training
only when that preflight passes and a small real-data run fits the GB10.**

No real corpus download, full-corpus preprocessing, real GPU training, target-FPR
calibration, cross-dataset evaluation, signed reports, installer or submission
video was performed. These remain Phase 2 or later work, consistent with the stop
boundary in the shared chat.
````

## Appendix B — full requested implementation files

Source: `scripts/phase01_smoke.py`

```python
#!/usr/bin/env python3
"""Synthetic integration check ONLY; never downloads data or launches GB10 training."""
from pathlib import Path
import json
import subprocess
import sys
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.data.pcap_extract import PACKET_FEATURES


def main():
    output = ROOT / 'examples/phase01_integration'
    raw = output / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for second in range(180):
        for flow in range(2):
            row = dict(timestamp=str(pd.Timestamp('2018-02-14') + pd.Timedelta(seconds=second)),
                       src='10.0.0.1', dst='10.0.0.2', protocol=6, src_port=1000,
                       dst_port=80, bytes_fwd=100 + second, packets_fwd=1,
                       environment_id='SYNTHETIC_FIXTURE_ONLY',
                       label='PORTSCAN' if second % 4 == 0 and flow == 1 else 'BENIGN')
            row.update({name: 0.0 for name in PACKET_FEATURES})
            row.update(ttl_mean=64., tcp_window_mean=1024., packet_features_available=1.)
            rows.append(row)
    # Deliberately reverse filename order relative to chronology.
    pd.DataFrame(rows[:180]).to_csv(raw / 'z_earlier.csv', index=False)
    pd.DataFrame(rows[180:]).to_csv(raw / 'a_later.csv', index=False)
    config = yaml.safe_load((ROOT / 'configs/phase01_smoke.yaml').read_text())
    config['data'].update(processed_dir='examples/phase01_integration/processed',
                          window_seconds=1, stride_seconds=1, history=3,
                          require_normalization=True, require_packet_features=True)
    config['train'].update(checkpoint='phase01_integration.pt',
                           history_path='examples/phase01_integration/train_history.json',
                           batch_size=16)
    config_path = output / 'config.yaml'
    config_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    commands = [
        ['scripts/build_corpus.py', '--source', 'CIC-IDS2018', '--input', str(raw),
         '--output', str(output / 'canonical')],
        ['scripts/prepare_data.py', '--config', str(config_path), '--input', str(output / 'canonical'), '--strict'],
        ['scripts/train.py', '--config', str(config_path), '--device', 'cpu'],
        ['scripts/eval.py', '--config', str(config_path), '--checkpoint', 'checkpoints/phase01_integration.pt',
         '--output', str(output / 'eval_test.json')],
    ]
    for index, command in enumerate(commands):
        with (output / f'step_{index + 1}.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, *command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('PASS', command[0], flush=True)
    report = json.loads((output / 'eval_test.json').read_text())
    assert report['per_sample'] and all(row['explanation']['feature_occlusion'] for row in report['per_sample'])
    (output / 'verification.json').write_text(json.dumps({
        'synthetic_only': True, 'real_training_performed': False,
        'steps_passed': len(commands), 'evaluated_samples': len(report['per_sample']),
        'automatic_explanations': True,
        'warning': 'CIC-IDS2018 is a fixture routing value. These generated rows are NOT real CIC data or accuracy evidence.'
    }, indent=2), encoding='utf-8')
    print('Synthetic integration passed; Phase 2 was not started.')


if __name__ == '__main__':
    main()
```

Source: `scripts/gpu_preflight.py`

```python
#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cybermind.utils.config import load_config
from cybermind.data.dataset import GraphSequenceDataset
from train import assert_split_disjoint, training_class_weight, validate_training_provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/gb10_full.yaml')
    args = parser.parse_args()
    cfg = load_config(ROOT / args.config)
    failures = []
    print('Python', sys.version.split()[0], 'PyTorch', torch.__version__)
    if not torch.cuda.is_available():
        failures.append('CUDA is unavailable on this runtime.')
    else:
        prop = torch.cuda.get_device_properties(0)
        print(f'GPU: {prop.name}; memory: {prop.total_memory / 1024**3:.1f} GiB')
        precision = cfg['train'].get('precision', 'fp32')
        if precision == 'bf16' and not torch.cuda.is_bf16_supported():
            failures.append('Configured bf16 is unsupported by this CUDA runtime.')
        else:
            try:
                dtype = {'bf16': torch.bfloat16, 'fp16': torch.float16, 'fp32': torch.float32}[precision]
                x = torch.randn(256, 256, device='cuda', dtype=dtype)
                assert torch.isfinite(x @ x).all()
                torch.cuda.synchronize()
                print(precision, 'CUDA matmul: PASS')
            except Exception as error:
                failures.append(f'CUDA kernel check failed: {error}')
    try:
        import torch_geometric
        print('PyG', torch_geometric.__version__)
    except ImportError:
        failures.append('Install the target-host PyG runtime before production training.')
    processed = ROOT / cfg['data']['processed_dir']
    required = ['train.pt', 'val.pt', 'test.pt']
    if cfg['data'].get('require_normalization'):
        required += ['normalization.json', 'metadata.json']
    missing = [str(processed / name) for name in required if not (processed / name).is_file()]
    failures.extend(f'Missing: {path}' for path in missing)
    if not missing:
        try:
            datasets = [GraphSequenceDataset(processed / f'{split}.pt') for split in ('train', 'val', 'test')]
            if any(not len(ds) for ds in datasets):
                raise ValueError('Every split must be nonempty.')
            for left, right in ((0, 1), (0, 2), (1, 2)):
                assert_split_disjoint(datasets[left], datasets[right])
            for dataset in datasets[:2]:
                training_class_weight(dataset)
            constants = json.loads((processed / 'normalization.json').read_text()) if cfg['data'].get('require_normalization') else None
            validate_training_provenance(processed, cfg, datasets, constants)
            print('Dataset split, class and normalization checks: PASS')
        except Exception as error:
            failures.append(f'Dataset validation failed: {error}')
    if failures:
        for failure in failures:
            print('STOP:', failure)
        return 1
    print('Preflight passed. Profile real graph memory on GB10 before the full run.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

Source: `src/cybermind/data/normalization.py`

```python
"""Persisted training-only fp32 graph feature normalization.

Fit once on unique training windows. Validation, test, and inference only transform.
Feature names are checked so legacy checkpoints cannot silently consume a new schema.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import torch


class RunningMoments:
    def __init__(self, width):
        self.count = 0
        self.mean = torch.zeros(width, dtype=torch.float32)
        self.m2 = torch.zeros(width, dtype=torch.float32)

    def update(self, values):
        x = torch.as_tensor(values, dtype=torch.float32).detach().cpu()
        if x.ndim != 2 or x.shape[1] != self.mean.numel():
            raise ValueError('Feature width does not match normalization schema')
        if not torch.isfinite(x).all():
            raise ValueError('Cannot fit normalization to non-finite features')
        if not len(x):
            return
        n = len(x)
        mean = x.mean(0)
        m2 = ((x - mean) ** 2).sum(0)
        delta = mean - self.mean
        total = self.count + n
        self.m2 += m2 + delta.square() * (self.count * n / total)
        self.mean += delta * (n / total)
        self.count = total

    def constants(self):
        std = (self.m2 / max(self.count, 1)).clamp_min(0).sqrt()
        std = torch.where(std > 1e-6, std, torch.ones_like(std))
        if not torch.isfinite(self.mean).all() or not torch.isfinite(std).all():
            raise ValueError('fp32 normalization overflow: inspect extreme input features')
        return {'count': self.count, 'mean': self.mean.tolist(), 'std': std.tolist()}


class FeatureNormalizer:
    def __init__(self, constants):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        if constants.get('fit_split') != 'train' or constants.get('dtype') != 'float32':
            raise ValueError('Normalization must be fitted on training data in fp32')
        self.constants = constants
        for key, names in [('node', NODE_FEATURE_NAMES), ('edge', EDGE_FEATURE_NAMES)]:
            if constants[key]['features'] != list(names):
                raise ValueError(f'{key} normalization feature schema mismatch')
            mean = torch.tensor(constants[key]['mean'], dtype=torch.float32)
            std = torch.tensor(constants[key]['std'], dtype=torch.float32)
            if len(mean) != len(names) or len(std) != len(names) or not torch.isfinite(mean).all() or not torch.isfinite(std).all() or (std <= 0).any():
                raise ValueError(f'Invalid {key} normalization constants')

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.constants, sort_keys=True).encode()).hexdigest()

    @classmethod
    def fit(cls, states):
        from .graph_builder import NODE_FEATURE_NAMES, EDGE_FEATURE_NAMES
        node, edge = RunningMoments(len(NODE_FEATURE_NAMES)), RunningMoments(len(EDGE_FEATURE_NAMES))
        seen = set()
        for state in states:
            if state.metadata.get('split') != 'train':
                raise ValueError('Only training states may fit normalization')
            if state.metadata.get('normalization_fingerprint'):
                raise ValueError('Normalization must fit raw features')
            identity = (state.scenario_id, state.metadata.get('window_start', state.timestamp))
            if identity in seen:
                continue
            seen.add(identity)
            node.update(state.x)
            edge.update(state.edge_attr)
        if not node.count:
            raise ValueError('No training nodes available for normalization')
        return cls({'version': 1, 'fit_split': 'train', 'dtype': 'float32',
                    'method': 'population_mean_std', 'training_windows': len(seen),
                    'node': {'features': list(NODE_FEATURE_NAMES), **node.constants()},
                    'edge': {'features': list(EDGE_FEATURE_NAMES), **edge.constants()}})

    def transform(self, values, kind):
        x = values.to(dtype=torch.float32)
        c = self.constants[kind]
        mean = torch.tensor(c['mean'], dtype=torch.float32, device=x.device)
        std = torch.tensor(c['std'], dtype=torch.float32, device=x.device)
        result = (x - mean) / std
        if not torch.isfinite(result).all():
            raise ValueError('Non-finite normalized features')
        return result

    def save(self, path):
        Path(path).write_text(json.dumps(self.constants, indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))
```
~~~~~~~~~~~~

## Appendix E. Current GB10 training configuration

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\configs\gb10_full.yaml`

~~~~~~~~~~~~text
# Phase 1 decision: full CIC-IDS2018 only. CTU-13 and UNSW-NB15 stay held out.
seed: 42
data:
  raw_dir: data/raw/CIC-IDS-2018
  processed_dir: data/processed_gb10
  primary_source: CIC-IDS2018
  window_seconds: 60
  stride_seconds: 30
  history: 16
  require_normalization: true
  require_packet_features: true
model:
  graph_hidden: 512
  graph_out: 512
  temporal_dim: 512
  graph_heads: 8
  nhead: 8
  temporal_layers: 6
  num_stages: 7
  dropout: 0.10
loss:
  transition: 1.0
  infiltration: 1.0
  stage: 0.5
  calibration: 0.2
  graph_consistency: 0.1
train:
  precision: bf16
  require_cuda: true
  epochs: 50
  lr: 0.0003
  weight_decay: 0.0001
  grad_clip: 1.0
  checkpoint: best_gb10.pt
  # Conservative full-size model microbatch; confirm with real graph sizes on GB10.
  # Unified RAM also holds the corpus, OS, optimizer, and loader; 128 GB is not all activations.
  batch_size: 8
  grad_accumulation: 8
  num_workers: 0
  selection_metric: val_f1
  selection_threshold: 0.5
  early_stopping_patience: 8
  min_delta: 0.0001
  history_path: results/gb10_train_history.json
eval:
  rollout_steps: 12
  n_rollouts: 16
~~~~~~~~~~~~

## Appendix F. Current README

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\README.md`

~~~~~~~~~~~~text
# CYBERMIND — Counterfactual World Model for Predictive Cyber Defence

Research-grade implementation skeleton aligned to SIH26153 master plan.

## Current Phase 0–1 handoff (2026-09-11)

The current pipeline uses `configs/gb10_full.yaml`, seven stage labels, training-only
normalization, and stochastic dynamics. Follow `docs/PHASE01_FINAL_REPORT.md` for
the verified checklist and Phase 2 commands. The commands and launcher defaults
below use this GB10 configuration and its `data/processed_gb10` output directory.
Existing legacy checkpoints/data must be rebuilt for the new feature/model schema.
Synthetic artifacts under `examples/` are correctness checks, not real training evidence.

Recheck Phases 0–1 locally without starting Phase 2:

```bash
python -m pytest tests -q -p no:cacheprovider
python scripts/phase01_smoke.py
```

## What is implemented

- Dynamic network graph: hosts as nodes, communication relationships as edges.
- Node features: packet/flow counts, protocol distribution, port activity, timing/activity statistics, anomaly proxy.
- Edge features: bytes, packets, protocol, port, direction, duration, inter-arrival statistics.
- GATv2 graph encoder when PyTorch Geometric is available, with a pure-PyTorch graph-attention fallback.
- Temporal Transformer encoder with positional encoding.
- Latent network state `z_t`.
- Learned dynamics transition `z_t -> z_t+1`.
- Multi-step K-step rollout.
- Heads for future state, infiltration probability, and attack stage.
- Multi-task objective: transition + infiltration + stage + Brier/calibration loss, with optional graph consistency.
- Scenario-level split support to avoid row leakage.
- Logistic-regression baseline.
- Early-warning lead-time evaluation.
- Counterfactual intervention simulation: No Action, Block Host, Block Port, Isolate Host, Restrict Edge, Rate Limit.
- Attack Gravity scoring as predicted risk reduction under isolation.
- Multi-hypothesis future generation via stochastic latent rollouts.
- Lightweight future-oriented explanation from gradient/attention attribution.
- Offline rollout visualization.
- Strict metadata for endpoint identity quality and ATT&CK-stage supervision quality.

## Scientific honesty

CIC-IDS2018 CSVs are not guaranteed to contain endpoint identities or true ATT&CK-stage labels in every distribution. The preparation pipeline therefore records identity/stage provenance and can fail in `--strict` mode instead of inventing labels.

The supplied SIH plan requires the world-model core, K-step rollout, infiltration forecast, attack-stage mapping, explainability, offline operation, logistic baseline, and unseen-attack evaluation. Counterfactual Risk Simulation, Attack Gravity, multi-hypothesis futures, early warning, and confidence/OOD are extensions proposed by the plan.

## Quickstart

Supply real CIC-IDS2018 data with endpoint identities and genuinely aligned packet
features first. Flow-only downloads do not satisfy the packet-feature requirement.
On the GB10 host, prepare the data and pass preflight before the first training epoch:

```bash
python scripts/build_corpus.py --source CIC-IDS2018 --input data/raw/CIC-IDS-2018 --output data/intermediate/CIC-IDS2018
python scripts/validate_dataset.py --input data/intermediate/CIC-IDS2018 --strict
python scripts/prepare_data.py --config configs/gb10_full.yaml --input data/intermediate/CIC-IDS2018 --strict
python scripts/gpu_preflight.py --config configs/gb10_full.yaml
# Run only after preflight exits successfully:
python scripts/train.py --config configs/gb10_full.yaml --device cuda --epochs 1
```

Inspect memory use and separate loss values before resuming:

```bash
python scripts/train.py --config configs/gb10_full.yaml --device cuda --resume checkpoints/best_gb10_last.pt
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split val
python scripts/eval.py --config configs/gb10_full.yaml --checkpoint checkpoints/best_gb10.pt --split test
```

Tune `configs/gb10_full.yaml` for measured graph sizes and GB10 memory use.

## Real-data path

```text
CIC CSV / PCAP
   -> feature_extract.py
   -> graph_builder.py
   -> temporal.py
   -> GraphSequenceSample
   -> train/val/test .pt
   -> GATv2 -> Temporal Transformer -> Dynamics
   -> K-step rollout
   -> risk + stage + state forecasts
   -> metrics / visualization / counterfactual simulation
```

## Folder layout

```text
CYBERMIND/
├── data/raw/CIC-IDS-2018/
├── data/intermediate/
├── data/processed_gb10/
├── src/cybermind/
│   ├── data/
│   ├── models/
│   ├── baselines/
│   ├── evaluation/
│   ├── counterfactual/
│   ├── explainability/
│   └── utils/
├── scripts/
├── configs/
├── checkpoints/
├── results/
├── docs/
└── tests/
```

## Public-source registry

See `configs/sources.yaml` and `docs/PUBLIC_DATA_SOURCES.md`. Use the GB10 preparation commands above for the primary corpus; keep other datasets in separate held-out directories.

## Offline demo

After training: `streamlit run scripts/app.py`.

The legacy `scripts/pcap_to_corpus.py` helper infers labels from filenames. Real training requires genuine packet-to-label alignment.

## One-command training

For the production GPU host:

```bash
source .venv/bin/activate
./scripts/run_training_from_zero.sh
```

To make the launcher download the official public CIC-IDS2018 S3 corpus when the raw directory is empty:

```bash
CYBERMIND_DOWNLOAD_CIC2018=1 ./scripts/run_training_from_zero.sh
```

Resume a previous run:

```bash
CYBERMIND_RESUME=checkpoints/best_gb10_last.pt ./scripts/run_training_from_zero.sh
```

Override epochs for a controlled smoke/validation run:

```bash
CYBERMIND_EPOCHS=1 ./scripts/run_training_from_zero.sh
```

## Final pre-training automation

For a GPU host with already prepared and normalized GB10 datasets:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --train-only --epochs 1
```

For a clean machine that should automatically fetch CIC-IDS2018 from the official public S3 bucket when the raw directory is empty:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --download-cic2018 --epochs 1
```

For a 1-epoch production-path sanity run:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --no-download-cic2018 --epochs 1
```

## Laptop export

After a trained checkpoint:

```bash
python scripts/distill_student.py --train-data data/processed_gb10/train.pt --output models/cybermind_student_quant.onnx
```

The student path is deliberately separated from the full PyG teacher because ONNX portability for variable-size graph operators is environment-dependent. The laptop runtime should keep the graph preprocessing layer and run the fixed-size student on its output.

## Safety boundary

The optional sandbox is isolated and non-destructive. It is for integration testing of the CYBERMIND demonstration path, not an exploit launcher.


## ONNX safety guardrails

All model output directories (`checkpoints/`, `export/`, `models/`) are created automatically before writes. Every ONNX export is immediately checked with `onnx.checker` and loaded with `onnxruntime.InferenceSession` on the CPU provider using dummy input. The **<100 MB size gate applies to the laptop student artifact only**; the teacher export is size-reported but not incorrectly rejected for exceeding the student budget.


## One-command lab training

After the one-epoch check on the GB10 host with 128 GB unified memory, the full pipeline can be launched from the project root:

```bash
python scripts/one_click_train.py
```

This uses `configs/gb10_full.yaml`, prepares `data/processed_gb10`, and runs preflight before baselines/training. It also requests evaluation, teacher export and student export. Automatic download cannot supply missing packet-label alignment; preflight rejects incomplete packet coverage. This full pipeline has not been verified on the GB10 yet.

To deliberately disable automatic dataset downloading:

```bash
python scripts/launch_training.py --config configs/gb10_full.yaml --no-download-cic2018
```

## Submission artifacts

Submission strategy: checkpoints and benchmark JSON/PNG files are eligible for
normal Git tracking. The blanket `*.pt`, `results/*.json` and `results/*.png`
ignore rules have been removed before the first commit; force-add is unnecessary.
Python environments and caches remain ignored.

Once real training and evaluation produce the final files, explicitly stage
`checkpoints/best_gb10.pt`, `results/eval_val.json`, `results/eval_test.json`,
`results/baseline_val.json`, `results/baseline_test.json`,
`results/gb10_train_history.json` and the final benchmark PNGs. Include their
config and normalization constants from `data/processed_gb10/normalization.json`.
Review the staged file list before the submission commit. Synthetic checkpoints
under `checkpoints/phase01_*` and fixture results under `examples/` are not the
final submission evidence.

The workspace has not been initialized as a Git repository, committed, or pushed.
~~~~~~~~~~~~

## Appendix G. Current ignore rules

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\.gitignore`

~~~~~~~~~~~~text
__pycache__/
*.pyc
.venv/
.phase01-venv/
.uv-cache/
.pytest_cache/
.env
# Submission checkpoints (*.pt) and results JSON/PNG are intentionally trackable.
# Explicitly stage the final artifacts documented in README.md.
*.pkl
*.joblib
data/raw/CIC-IDS-2018/*.csv
data/raw/CIC-IDS-2018/*.pcap
data/intermediate/*
~~~~~~~~~~~~

## Appendix H. Synthetic integration verification

Source: `C:\Users\as030\Downloads\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\examples\phase01_integration\verification.json`

~~~~~~~~~~~~text
{
  "synthetic_only": true,
  "real_training_performed": false,
  "steps_passed": 4,
  "evaluated_samples": 25,
  "automatic_explanations": true,
  "warning": "CIC-IDS2018 is a fixture routing value. These generated rows are NOT real CIC data or accuracy evidence."
}
~~~~~~~~~~~~

<!-- SESSION_CONTEXT_READY_FOR_COPY -->
