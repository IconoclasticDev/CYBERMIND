# Real-data R2 audit — PASS

Date: 2026-09-16. Scope: the frozen R1 corrected-label real chunk.
**R2 exit criteria met.** R3 zero-shot evaluation is pre-authorized to start
after this audit. R4 training, main-plan Phase 5, and the GB10 window remain
unauthorized.

## Exit evidence

The canonical build consumed all 15 R1 CSVs and produced 15 Parquet files under
`data/intermediate_real_chunk_r2/`. Strict validation ran twice with
`--require-packet-features` explicitly enabled: once on the R1 inputs and once
on the canonical outputs. Both checks covered all 1,186,046 rows and reported:

| Check | Missing required | Invalid endpoints | Invalid timestamps | Invalid labels | Unverified labels | Invalid packet rows |
|---|---:|---:|---:|---:|---:|---:|
| R1 labeled inputs | 0 | 0 | 0 | 0 | 0 | 0 |
| Canonical R2 outputs | 0 | 0 | 0 | 0 | 0 | 0 |

The reports are `examples/real_data_validation/r2/r1_strict_validation.json`
(SHA256 `cc2af1912e48197d398f65ddc95f114e12770eec4b507d10a0d125f19758f383`)
and `canonical_strict_validation.json` (SHA256
`7160670f0e50903d65c99db65cafab2cdde1c22cbfbde4663ccf32e4f1efc195`).

Strict preparation used `configs/real_chunk_r2.yaml`: 60-second windows,
30-second stride, 16-state histories, and `require_packet_features: true`.
It completed without a hard failure and wrote:

| Split | Rows in chronological partition | Sequences | Packet coverage | Processed SHA256 |
|---|---:|---:|---:|---|
| Train | 829,903 | 1,699 | 1.0 | `27fd4b747fb9bad57c96569276706bebbc0d4ccf7e456256696f1671fb3a2ad6` |
| Validation | 199,369 | 428 | 1.0 | `53052bc3fc098340cfd6113ec588d033461275456d10040619d6dd4b28f3b78c` |
| Test | 155,886 | 431 | 1.0 | `9d8a8e8c4bdb54e6090e4c6d2751cdf433d5831f74962cbf6065410058244e63` |

The 60-second purge at both split boundaries intentionally removes 888 source
rows from the three reported partitions; it is the predeclared leakage guard,
not row loss during canonical conversion. The fitted training-only
normalization fingerprint is
`516ca73d339569212c98a5d698f9f54b54f5cbb0d4f995b8216c7eb9614f027d`.

`examples/real_data_validation/r2/output_audit.json` independently loaded all
2,558 samples. It found zero non-finite state tensors, zero invalid IP-node
occurrences, zero normalization-fingerprint failures, and zero 16-state
histories spanning an empty temporal gap.

## Pipeline defects fixed before the successful run

The unified adapter previously discarded the audited R1 `stage` and
`label_verified` fields. That would have remapped 26 Dropbox rows to
Unknown/Ambiguous and removed the evidence used by strict label validation. It
now preserves authoritative stages, label-verification fields, refinement
status, and source provenance.

The adapter also filled missing packet fields with zero while retaining a
caller-supplied availability value of one. It now determines availability from
the original 20 fields before compatibility filling and forces
`packet_features_available=0` for any missing, non-finite, or uncertified input.
Strict validation therefore cannot accept synthesized zeros as observed packet
telemetry. Regression coverage verifies both behaviors.

The first preparation attempt was stopped before publication after inspection
showed that `make_sequences()` rescanned all 1.18 million rows at every
30-second tick across the 16-day span. The implementation now uses sorted
timestamp index bounds for the identical half-open windows. It also separates
histories at empty intervals, preventing the final graph on one capture day
from becoming adjacent to the first graph days later. Window, stride, history,
split, feature, and exit-gate values were not changed. The focused data suite
passes 33 tests.

## Real graph identity and edge verification

`examples/real_data_validation/r2/graph_identity_audit.json`, SHA256
`75d85c4314bef9e2eac8c46dcf22c2b86af6349080eeb1bb6b23a105b271a0ca`,
uses a deterministic 60-second window anchored at the first corrected attack
flow on each frozen date. It decodes every graph edge through `node_ids` and
compares the full directed-pair set and aggregate byte/packet values with the
canonical source flows.

| Date | Window rows | Source / graph nodes | Source pairs / graph edges | Missing / extra pairs | Aggregate mismatches |
|---|---:|---:|---:|---:|---:|
| 2018-02-14 | 4,006 | 4 / 4 | 6 / 6 | 0 / 0 | 0 |
| 2018-03-01 | 112 | 20 / 20 | 36 / 36 | 0 / 0 | 0 |
| 2018-03-02 | 159 | 36 / 36 | 59 / 59 | 0 / 0 | 0 |

Examples include the documented February attacker/victim pair
`18.221.219.4 -> 172.31.69.25` and real March internal and external endpoints.
No endpoint identity was synthesized.

## Required provenance disclosures

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

## Verdict

**R2 exit criteria met.** `prepare_data.py --strict` passed on the real chunk
with packet features required, canonical row counts reconcile exactly with R1,
and graph endpoint identities and directed edges agree with source flows. This
is `source: real-chunk validation, pre-Phase-5 — not full-corpus accuracy`.
R3 may start under the recorded pre-authorization.
