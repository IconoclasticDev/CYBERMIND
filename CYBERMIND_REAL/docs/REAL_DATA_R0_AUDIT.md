# Real-data R0 audit — HOLD

Latest status: bounded setup was interrupted and its original 90-minute deadline
elapsed before continuation. Source is pinned/downloaded; runtime and schema
smoke verification remain incomplete. No setup resumed after the cap. See
`REAL_DATA_R0_RUNTIME_RESULT.md`. This supersedes the earlier 2–4-hour estimate
and timeline-pending wording below. **R0 exit criteria NOT met.**

## Subsequent reviewer decision — 2026-09-16

Both proposals below were approved by the reviewer. Dates are frozen to Feb 14,
Mar 1 and Mar 2; the exact derivative has been created and verified. See
`REAL_DATA_R0_REVIEWER_DECISION_2026_09_16.md` and
`examples/real_data_validation/r0/feb14_derivative.json`.
The original findings below remain a historical record, not pending requests
for the same approval. R0 remains incomplete: runtime/schema work has a proposed
2–4-hour budget with a first 60-minute stop; the remaining deadline is unknown
and setup has not started. R1 remains unauthorized.

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** Real-data evaluation is pending.

## Original pre-decision audit

Date: 2026-09-16. **R0 exit criteria NOT met. R1–R6 have not started.**
Main-plan Phase 5 and the GB10 window remain unauthorized.

## Work completed

Read and preserved the supplied validation plan and context, with SHA256 values
in `examples/real_data_validation/r0/preserved_input_hashes.json`. Created the
task-by-task `docs/REAL_DATA_VALIDATION_CHECKLIST.md`. Reviewed the source
schedule, corrected-label documentation, existing exporters and local tooling.
The detailed independent findings are in `docs/REAL_DATA_R0_TOOLCHAIN_REVIEW.md`.

Rehashed the existing February 14 source capture and failed partial output.
Neither was modified or replaced. The earlier capture represents one victim
host, not all 450 captures in that date's archive. Verified ZIP-member acquisition
does not imply structurally valid PCAP contents.

Fixed the custom exporter's failure-publication behavior: future incomplete
exports remain under a `.partial` filename, write an explicit failure report,
and re-raise the original error. Completed outputs are published only after
processing and closing the writer. Existing output, partial and report paths
are protected from overwrite. No packets are skipped to work around corruption.
This safety fix does not make the custom exporter satisfy R0's CICFlowMeter
requirement, and the original failed extraction was not rerun or relabeled.

Verification: **6 focused CPU tests passed, 0 skipped**, including truncated
capture failure retention, no final-file publication on failure, retry evidence
preservation, successful publication, and strict-validator behavior. Evidence:
`examples/real_data_validation/r0/export_safety_tests.xml`.

## Preserved real-input failures

| Evidence | Finding |
|---|---|
| `examples/one_day_join/acquisition.json` | Exact archive member acquired; ZIP CRC32 `c2144ce9` verified |
| Source PCAP SHA256 | `008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc` |
| `examples/one_day_join/pcap_structure.json` | 852,795,392 bytes; 4,718,327 complete packet records; final record truncated |
| Truncated record | Offset 852,795,085; declared 371 packet bytes; only 291 available; 80 bytes missing in the source member |
| `examples/one_day_join/regeneration.log` | `ValueError: Truncated PCAP record` |
| Earlier partial flow output | 578,771 rows; SHA256 `ef2c2b6fb0ea78c09fd1ab3b3a9c0279f0b61ad6f5c92a8290e37073f6474f45` |
| `examples/one_day_join/strict_validation_failed_attempt.json` | **FAIL**: 3,260 unverified-label rows; missing packet features did not cause this failure |

These are input-quality and pipeline diagnostics, not model accuracy metrics.
The 3,260 rows came from the original-schedule attempt, not an R1 corrected-label
run. No corrected-label success is claimed. The partial output is not an R0
unlabeled flow CSV, nor a complete one-day dataset.

## Why execution stops at the R0 gate

R0.1 requires Lateral Movement representation. The primary-source review does
not establish such labels. Internal scanning alone does not demonstrate lateral
movement. Corrected infiltration subtypes and bot communication can support a
narrower documented-stage experiment, but accepting that as the stated R0.1 gate
would change the requirement. See the linked primary evidence in the toolchain
review; no heuristic relabeling has been applied.

The supplied plan's ground rule 3 says:

> Any change to a gate or fixture requires explicit reviewer sign-off, recorded in the PR/commit.

The user's standing instruction additionally says to flag a questionable gate
and stop rather than substitute an easier one. Therefore no further capture
selection/download or processing is represented as satisfying this gate.

Other engineering work still required after the scope decision: establish a
pinned CICFlowMeter runtime (none is currently callable), verify its full biflow
schema, and augment packet attributes using the exact same flow boundaries.
The existing directional exporter has 40 fields, including labels, and cannot
stand in for the requested approximately 80 CIC features plus packet attributes.

## Concrete decisions for reviewer — proposals, NOT applied

1. **Coverage:** amend only R0.1's mandatory Lateral Movement coverage to require
   the distinct stages actually supported by the published corrected rules.
   Proposed dates are **February 14, March 1, and March 2, 2018**, retaining the
   February 14 failure. Freeze the dates before new processing; record precise
   capture membership before download. Describe missing Lateral Movement and
   any unverified Exfiltration interpretation explicitly. This does not change
   R2 strict validation, R4's four-step gate, selection tolerance, or R5's baseline.
   If mandatory Lateral Movement remains, supply defensible source annotations;
   the gate remains on hold until then.
2. **Malformed source:** permit an explicitly named derivative of the existing
   February 14 capture containing its **4,718,327 complete records only**.
   Preserve the original unchanged and hash both. Record exclusion of the
   final **307 on-disk bytes** (16-byte record header plus 291 available payload
   bytes), whose record is missing 80 payload bytes. Do not synthesize those
   missing bytes. Preserve the failed original run and disclose incomplete
   capture coverage in every derived provenance record. Without authorization,
   do not truncate, repair, or silently skip the damaged record.

Neither proposal guarantees a pass. Approval is needed because these are an
explicit coverage amendment and a source-fixture derivative. The remaining
pipeline may still fail. Separate phase approval is required before R1, as the
user requested; final GB10 authorization remains an R6 reviewer decision.

## Exit verdict

**R0 exit criteria NOT met.** Missing: reviewed stage/capture scope, accepted
handling of the malformed input, the required exporter and packet augmentation,
completed unlabeled CSVs for all selected dates, and their registered hashes.
No real-chunk training, benchmark, or Phase 5 authorization is claimed.
