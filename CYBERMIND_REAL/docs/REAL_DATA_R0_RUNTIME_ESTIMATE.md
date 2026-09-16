# CICFlowMeter runtime and schema work — estimate before execution

**Closed incomplete on continuation: the original hard deadline elapsed during
the interruption. No further setup is running or queued by this task.** See
`REAL_DATA_R0_RUNTIME_RESULT.md` for evidence and uncompleted checks. Earlier
future-tense text below is retained as the original estimate/time-box record.

## Superseding user instruction and active timer

The user rejected extension beyond the original cap: **60-minute feasibility
checkpoint; 90-minute absolute hard stop** for setup/schema work, including
interactive diagnosis. The earlier 2–4-hour estimate below is historical and
does not authorize that duration. No unattended retries or clock extensions.

Started: **2026-09-15 19:41:17 UTC** (2026-09-16 01:11:17 IST).
Feasibility checkpoint: **20:41:17 UTC**.
Absolute hard stop: **21:11:17 UTC**.
All setup subprocesses must be bounded by the remaining time. If feasible early,
finish and report early; do not consume the time box merely because it exists.
Current work is R0 only. Later phases remain unauthorized.

## Superseded initial estimate

2026-09-16. **Runtime pinning, installation, builds and smoke exports have not
started.** Estimate based on the existing toolchain review, not measured setup
time. No callable Java/CICFlowMeter toolchain was found in that review.

Planning range: **2–4 hours** for runtime pinning and schema verification alone.
The available deadline has been requested; timeline fit is currently unknown.
Hold setup until it can be checked against that deadline.

| Work | Budget / stop rule |
|---|---|
| Pin upstream source/runtime/native dependencies and attempt a minimal CLI export | First 60 minutes; hard stop and report if no executable path or unresolved native dependency |
| Verify bidirectional identity, timestamps, timeout/termination, feature column names and numeric conventions on deterministic tiny captures | Next 60–120 minutes, only after feasibility succeeds and timeline permits |
| Record versions/hashes, schema contract, commands and findings | Remaining budget, total maximum 4 hours |

Acceptance: reproducible pinned runtime; full five-tuple and timestamps;
approximately 80 genuine CIC flow features; exact emitted schema recorded;
deterministic smoke cases establish forward/reverse association and flow
termination. Log unsupported fields, non-finite values and runtime failures.
Do not make missing packet attributes appear present by filling zeros.

Out of scope: processing selected real-day captures, packet-feature augmentation,
corrected labels, corpus preparation, model training and benchmarking. Measure
smoke throughput and inspect flow membership before estimating augmentation and
full R0 processing. Completing runtime setup does not complete R0.

No unbounded dependency migration, replacement exporter, container/WSL migration
or from-scratch flowmeter implementation is included. If the time box expires,
preserve logs and return the blocker and revised options before more work.
