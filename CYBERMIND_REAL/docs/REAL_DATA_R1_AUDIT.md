# Real-data R1 audit — PASS

Date: 2026-09-16. Scope: the frozen February 14 / March 1 / March 2, 2018
real chunk produced by R0. **R1 exit criteria met.** R2 is pre-authorized to
start after this audit. Main-plan Phase 5 and the GB10 window remain
unauthorized.

## Exit evidence

R1 produced 15 labeled CSVs under `data/real_chunk/labeled/`, preserving all
1,186,046 R0 rows. The immutable output manifest is
`data/manifests/r1_real_chunk_files.csv`, SHA256
`377333cbfa138835ec6b41603ad34f73d36ee48e3b87459a427034555d59a33e`.
The discrepancy log is
`examples/real_data_validation/r1/discrepancies.csv`, SHA256
`80463368aa37438595214898294ac9b73cd7765f44f0de0a3b2fb9e78f9ec4db`.

The methodology was frozen before labeling in
`data/real_chunk/LABELING_METHODOLOGY.md`, SHA256
`8e5aa653da6355a76ba0d36039dbdf0ac80f00e3455554cd1fd5aa63b0b64087`.
It specifies inclusive UTC `session_start` matching, zero time tolerance,
directional endpoint and port rules, payload semantics, rule precedence,
overlap handling, and the independent original-schedule comparison.

The final machine-readable audit is
`examples/real_data_validation/r1/output_audit.json`, SHA256
`7e922accbb6069a27a1f0c0b0fc8c4cda6b5f8f0a0a42e216e1c9b36a9564b30`.
It reports zero invalid packet-feature rows, zero invalid labels, zero invalid
stages, zero provenance failures, and exact row preservation. The combined R0
and R1 focused suite passed 13 tests.

## Pinned sources

| Source | Pin / role | SHA256 |
|---|---|---|
| `Distrinet_CICIDS2018_fixed_f0ce502.ipynb` | Distrinet commit `f0ce502818e59e6cd062720ab2286c5ff6f2bdec`; corrected executable rules | `e58bea8651f4c891383f3cf1e735de4b48f50c4ec8a9aef078b53972dca1422e` |
| `Distrinet_CSECICIDS2018.html` | corrected-rule documentation snapshot | `c9edddbcba999cf4a004a090d991e915ded9226cae3f0e9589fa302631f9803b` |
| `UNB_CSE_CIC_IDS2018.html` | original Table 2 schedule snapshot | `c1258503f336f0dd4b1877ce5506b8d870b2ddf67e14f90348c42bfd3258b9fe` |

## Corrected label results

| Date | Corrected label | Rows | Stage |
|---|---|---:|---|
| 2018-02-14 | BENIGN | 290,070 | Benign |
| 2018-02-14 | FTP-BruteForce - Attempted | 193,360 | Initial Access |
| 2018-02-14 | SSH-BruteForce | 94,197 | Initial Access |
| 2018-03-01 | BENIGN | 57,011 | Benign |
| 2018-03-01 | Infiltration - Communication Victim Attacker | 4 | Unknown/Ambiguous |
| 2018-03-01 | Infiltration - Dropbox Download | 16 | Initial Access |
| 2018-03-01 | Infiltration - Dropbox Download - Attempted | 10 | Initial Access |
| 2018-03-01 | Infiltration - NMAP Portscan | 149,014 | Reconnaissance |
| 2018-03-02 | BENIGN | 116,342 | Benign |
| 2018-03-02 | Botnet Ares | 286,022 | Command & Control |

## Independent original-schedule comparison

The original UNB schedule labeled 291,621 February 14 rows benign, 192,300
FTP, and 93,706 SSH; 206,051 March 1 rows benign and 4 Infiltration; and
305,150 March 2 rows benign and 97,214 Bot. Comparing every row yielded
722,627 rows where the literal label strings differ. The discrepancy CSV retains
all corrected/original pairs, including differences caused by corrected attack
windows, more specific categories, attempted variants, and rows assigned benign
by one source.

| Date | Corrected label | Original label | Rows |
|---|---|---|---:|
| 2018-02-14 | FTP-BruteForce - Attempted | BENIGN | 1,030 |
| 2018-02-14 | FTP-BruteForce - Attempted | FTP-BruteForce | 192,300 |
| 2018-02-14 | FTP-BruteForce - Attempted | SSH-Bruteforce | 30 |
| 2018-02-14 | SSH-BruteForce | BENIGN | 521 |
| 2018-02-14 | SSH-BruteForce | SSH-Bruteforce | 93,676 |
| 2018-03-01 | BENIGN | Infiltration | 4 |
| 2018-03-01 | Infiltration - Communication Victim Attacker | BENIGN | 4 |
| 2018-03-01 | Infiltration - Dropbox Download | BENIGN | 16 |
| 2018-03-01 | Infiltration - Dropbox Download - Attempted | BENIGN | 10 |
| 2018-03-01 | Infiltration - NMAP Portscan | BENIGN | 149,014 |
| 2018-03-02 | Botnet Ares | BENIGN | 188,808 |
| 2018-03-02 | Botnet Ares | Bot | 97,214 |

Rows where both literal labels agree are also retained in the discrepancy file
as comparison categories but are excluded from the 722,627 discrepancy total.

## Fine-grained refinement limitation

The corrected endpoint/time rules verify the broad `Botnet Ares` label and
Command & Control stage for every affected March 2 row. Of all 1,186,046 rows,
209 cannot be refined into the notebook's attempted subcategories: 33 require
backward RST counts and 176 require reverse-direction payload totals. Those
biflow-only fields do not exist in the reviewer-approved directional fallback
schema. The labeler does not invent them; each affected row has
`label_refinement_verified=false` and an explicit reason.

This limitation does not alter broad attack labels or stage targets, because
the broad and attempted Botnet variants map to the same Command & Control
stage. The audit therefore passes the fixed R1 exit criterion—labeled selected
days, committed discrepancy evidence, and hashed methodology—while explicitly
reporting that fine-grained attempted-subtype verification is incomplete.

## Required provenance disclosures

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**

## Verdict

**R1 exit criteria met.** The selected-day dataset is labeled from pinned
corrected rules, the original schedule was applied independently, every
comparison category is logged, and the frozen methodology is documented and
hashed. R2 may start under the recorded pre-authorization. This verdict makes no
claim of CICFlowMeter parity, fine-grained verification for the 209 disclosed
Botnet refinement rows, full-corpus validation, or Phase 5 authorization.
