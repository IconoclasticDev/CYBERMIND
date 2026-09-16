# Real-data R0 audit — PASS

Date: 2026-09-16. Scope: reviewer-approved February 14 / March 1 / March 2,
2018 real chunk. **R0 exit criteria met.** R1 is pre-authorized to start after
this audit. Main-plan Phase 5 and the GB10 window remain unauthorized.

## Exit evidence

All 15 frozen source members were acquired and verified, then exported without
labels to `data/real_chunk/flows_raw/`. The per-file source/output manifest is
`data/manifests/r0_real_chunk_files.csv`, SHA256
`4356fb4616ad63cbad87e75e5e57ca5288568fc6b31f13cd70f1445328388b66`.
It records every source/output SHA256, byte count, capture member and row count.

The machine-readable audit is
`examples/real_data_validation/r0/fallback_output_audit.json`, SHA256
`37f616a8933bc38406861a164e91f2e874e8bc0381faa3ccf7bf82c35e3018fb`.

| Date | Capture files | Capture records | IPv4 processed | Non-IPv4 counted | Offload records | Flow rows |
|---|---:|---:|---:|---:|---:|---:|
| 2018-02-14 | 1 | 4,718,327 | 4,715,153 | 3,174 | 0 | 577,627 |
| 2018-03-01 | 3 | 782,254 | 776,574 | 5,680 | 376 | 206,055 |
| 2018-03-02 | 11 | 3,009,729 | 2,887,764 | 121,965 | 20,469 | 402,364 |
| **Total** | **15** | **8,510,310** | **8,379,491** | **130,819** | **20,845** | **1,186,046** |

Every CSV passed these unchanged checks:

- full source/destination IP, source/destination port, protocol and timestamps;
- all 20 packet-feature fields finite with `packet_features_available == 1`;
- source hash, capture date and capture member agree with frozen evidence;
- exact mandatory fallback provenance string present on every row;
- no label, stage, attack-stage or infiltration column exists;
- output SHA256 agrees with its atomically published export report.

Audit totals: 0 invalid tuple/time rows, 0 invalid packet rows, 0 provenance
mismatches and 0 label columns. The physical R0 CSV schema has 42 columns: the
fallback flow/packet fields with four label fields omitted, plus six provenance
fields. The reviewer-mandated `40-column schema` label remains verbatim.

## Preserved source and anomaly decisions

February 14 uses the reviewer-approved 4,718,327-complete-record derivative,
SHA256 `7fc8442ebf996dc065bbbad3cfb6a9bcde247b58cb8e459fca144a1bbf607394`.
The original capture remains unchanged at SHA256
`008f18cce0ff420ce013eba6d97ae0b974f36028a0707a977f78d4bfd7f48afc`.
The derivative excludes the final record at offset 852,795,085, where 291 of
371 declared bytes were available. No bytes were synthesized or repaired.

March 1 part 1 initially stopped at the first IPv4 total-length-zero record. A
full structural scan found 376 complete TCP records with equal captured/wire
lengths and valid transport headers; frames up to 23,094 bytes demonstrate the
host packet-offload super-packet pattern. The parser accepts only the complete
TCP signature, derives length from captured IP bytes, changes no source byte and
counts every occurrence. The initial failure report and successful rerun report
are both preserved. The same disclosed path counted 20,469 March 2 records.

The initial final-audit run also stopped on one valid whole-second ISO timestamp
after pandas inferred a fractional-second-only format for its chunk. Evidence is
preserved in `fallback_output_audit_diagnostic.json`. The auditor was corrected
to require ISO-8601 explicitly and rerun against identical files and gates; the
row then passed. No dataset, criterion or tolerance changed.

## Exporter limitation and Phase 5.0 finding

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

The parallel Phase 5.0 audit found that public-corpus acquisition only syncs CSV
and PCAP archives; it does not call CICFlowMeter or jnetpcap, but it also does
not extract/enrich packet features. `build_corpus.py` consumes CSV, the adapter
can fill missing packet fields with zeros, and the GB10 strict preparation path
then rejects those rows when `require_packet_features: true`. This remains a
separate blocker before any GB10 window. See
`docs/PHASE5_0_ACQUISITION_DEPENDENCY_AUDIT.md`.

## Required coverage disclosure

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.** This disclosure remains mandatory
in R4, R5, R6 and final submission sections that discuss stage coverage or
illegal-transition metrics.

## Verdict

**R0 exit criteria met.** The selected-day unlabeled flow CSVs exist with real
five-tuples, timestamps, all 20 required packet features, atomic reports and
registered hashes. This passes only the approved fallback contract and does not
claim CICFlowMeter feature parity or full-corpus validation.
