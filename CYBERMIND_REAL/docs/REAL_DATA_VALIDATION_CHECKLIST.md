# Real-data validation checklist

Plan: `CYBERMIND_Real_Data_Validation_Plan.md`, supplied and authorized on 2026-09-16.
This is a separate R0–R6 sequence before main-plan Phase 5. Existing Phase 3/4
audits remain historical evidence. No GB10 run is authorized by this plan.

## R0 — CICFlowMeter NO-GO; approved custom fallback active; exit criterion not met

Reviewer update 2026-09-16: dates fixed to February 14 / March 1 / March 2;
Lateral Movement coverage amendment and exact malformed-source derivative
approved. R0 only is authorized. See `REAL_DATA_R0_REVIEWER_DECISION_2026_09_16.md`.

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** Evaluation has not yet occurred.
Repeat this disclosure in every stage-coverage/illegal-transition artifact,
including R3–R6 and final architecture/novelty sections; never summarize it away.

- [x] Read the supplied plan and its referenced `CYBERMIND_CONTEXT.md`.
- [x] Preserve the earlier February 14 acquisition, failed regeneration, and strict-validation evidence.
- [x] Cross-check candidate stage coverage against primary-source documentation.
- [x] Rehash and register the failed February 14 precheck with explicit failure provenance.
- [x] Prevent failed custom extraction from publishing a final output filename; six focused tests pass.
- [x] Deliver `REAL_DATA_R0_AUDIT.md`; both proposals were subsequently approved and the derivative created.
- [x] R0.1 Freeze three dates and reviewer-approved coverage amendment.
- [ ] Freeze precise capture membership for the remaining dates before acquisition.
- [x] Create and hash the approved 4,718,327-record February 14 derivative; verify byte-identical source prefix and unchanged original hash.
- [x] Replace the earlier 2–4-hour estimate with the user's fixed 60-minute feasibility / 90-minute hard cap.
- [x] Pin/download upstream source and retrieve runtime candidate metadata; installation/build/export not completed.
- [x] On continuation, honor the elapsed deadline; publish `REAL_DATA_R0_RUNTIME_RESULT.md` without resetting the timer.
- [ ] Establish executable runtime and demonstrate schema acceptance; no retry currently authorized under the exhausted setup attempt.
- [x] Final bounded attempt: verified Java 8; pinned build failed on unresolved `org.jnetpcap:jnetpcap:1.4.1`; stopped without debugging or a third path.
- [x] Publish concrete CICFlowMeter NO-GO and record prior usage-limit interruption as tooling, not a CICFlowMeter result.
- [x] Assess fallback: existing 40-column exporter satisfies the implemented 20-field packet-feature contract in focused tests, but omits approximately 67 pinned CIC traffic statistics and differs in direction/session semantics.
- [ ] Implement an unlabeled, atomic fallback R0 export path with explicit feature-gap provenance; do not use the hardcoded schedule during R0.
- [ ] R0.2 fallback: export selected captures with full five-tuple/timestamps and all 20 project packet fields; disclose the approved approximately-67-statistic CIC gap on every output. CICFlowMeter parity is not claimed.
- [ ] R0.3 Record hashes for every selected input and completed output in the registry/provenance.
- [ ] Audit R0: unlabeled flow CSVs for all selected days exist and meet the declared schema.
- [ ] Obtain approval before entering R1, following the user's standing phase boundary instruction.

## R1 — NOT STARTED

- [ ] R1.1 Pin the corrected Distrinet rules for the selected dates.
- [ ] R1.2 Apply their endpoint, direction, time, port, and payload conditions to R0 flows.
- [ ] R1.3 Apply the original CIC schedule independently and retain all discrepancies by category and count.
- [ ] R1.4 Document matching, timezone, time tolerance, overlapping rules, and flow-boundary semantics; hash the methodology.
- [ ] Commit the discrepancy log and audit; request approval for R2.

## R2 — NOT STARTED

- [ ] R2.1 Build the corpus from R1 outputs.
- [ ] R2.2 Strict validation with packet features explicitly required; retain exact failures.
- [ ] R2.3 Strict preparation with `require_packet_features: true`.
- [ ] R2.4 Compare real graph endpoint identities/edges with source flows.
- [ ] Audit end-to-end results; R2 failure blocks R3. Request approval for R3 only after passing.

## R3 — NOT STARTED

- [ ] R3.1 Evaluate the preserved epoch-185 checkpoint; verify its preprocessing contract before inference.
- [ ] R3.2 Save per-window stage, illegal-transition, infiltration, and confidence outputs.
- [ ] R3.3 Label all outputs `source: zero-shot, synthetic-trained weights, real-corpus chunk — out-of-distribution test`.
- [ ] Audit results even if collapsed; request approval for R4.

## R4 — NOT STARTED

Before starting, flag the proposed overnight run to the user and satisfy
`REAL_DATA_R4_OVERNIGHT_REQUIREMENTS.md`: every-epoch checkpoints, incremental
disk logs, deliberate patience, first-collapse stop, and no automated retries.

- [ ] R4.1 Predeclare laptop configuration, split, seed, epoch budget and selection policy; train combined model on the real chunk only.
- [ ] R4.2 Evaluate each of four future steps independently: at least two distinct non-Unknown stages, zero illegal transitions, Unknown count below sample count.
- [ ] R4.3 Preserve every attempted epoch checkpoint, including failures.
- [ ] R4.4 Choose and justify patience before the run; do not inherit synthetic patience blindly.
- [ ] Audit selected checkpoint and unchanged gate outcomes; request approval for R5.
- [ ] Include the full no-Lateral-Movement disclosure beside stage coverage and illegal-transition results, even on failure.

## R5 — NOT STARTED

- [ ] R5.1 Use observed history only, unseen final-window target, threshold fixed at 0.5.
- [ ] R5.2 Compare node-only, node+edge, and fully feature-matched logistic baselines with the world model.
- [ ] R5.3 Record FPR, confusion counts and single-class handling.
- [ ] R5.4 Retain hashes, protocol version, sample probabilities and limitations.
- [ ] State whether the model beats the matched baseline; preserve ties/failures without weakening the baseline.
- [ ] Audit and submit to R6 review.
- [ ] Include the full no-Lateral-Movement disclosure wherever stage coverage or illegal-transition metrics appear.

## R6 — NOT STARTED; reviewer decision required

- [ ] R6.1 Confirm R2 passed.
- [ ] R6.2 Confirm R4/R5 outcomes are recorded.
- [ ] R6.3 Flag a matched-baseline tie to the submission owner if present.
- [ ] R6.4 Record explicit reviewer authorization or hold before any GB10 window.
- [ ] Preserve the full no-Lateral-Movement disclosure in R6 and final submission architecture/novelty sections.

All non-full-corpus metrics use the plan's exact real-chunk source qualifier;
R3 additionally uses its specific OOD qualifier. No result authorizes changing a
fixture, stage definition, tolerance, threshold, or exit gate.

## Independently authorized parallel deliverables

- [x] Isolation root cause and corrected probe: `ISOLATION_ROOT_CAUSE_AUDIT.md`; unchanged predicted risk on the degenerate synthetic graph, no containment-efficacy claim.
- [x] Track E five-slide editable deck: `TRACK_E_SLIDES_AUDIT.md`.
- [x] Track E 80-second captioned MP4: `TRACK_E_VIDEO_AUDIT.md`; captured-state montage, not continuous screen recording. All 1,920 frames decoded; root additionally inspected the actual output table frame and evidence slide.
