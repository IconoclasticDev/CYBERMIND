# R1 real-chunk labeling methodology

Frozen before the R1 labeling run on 2026-09-16.

## Sources

- Corrected executable rules: Distrinet `GintsEngelen/CNS2022_Code`, commit
  `f0ce502818e59e6cd062720ab2286c5ff6f2bdec`, notebook
  `Distrinet_CICIDS2018_fixed_f0ce502.ipynb`, SHA256
  `e58bea8651f4c891383f3cf1e735de4b48f50c4ec8a9aef078b53972dca1422e`.
- Corrected documentation snapshot: `Distrinet_CSECICIDS2018.html`, SHA256
  `c9edddbcba999cf4a004a090d991e915ded9226cae3f0e9589fa302631f9803b`.
- Original schedule snapshot: UNB CSE-CIC-IDS2018 Table 2,
  `UNB_CSE_CIC_IDS2018.html`, SHA256
  `c1258503f336f0dd4b1877ce5506b8d870b2ddf67e14f90348c42bfd3258b9fe`.

## Corrected-rule join

The join uses the R0 `session_start` as the flow timestamp because the pinned
notebook compares CICFlowMeter's `Timestamp`, which denotes flow start. All
source rule times are UTC Unix times. Both boundaries are inclusive and the
tolerance is exactly **0 seconds**. Endpoint direction, destination-port filters,
and the March 1 NMAP source-port-68 exclusion are applied literally. Rules run
in pinned-notebook order, so later attempted rules override the corresponding
broad attack rule. Rows unmatched by any corrected rule become `BENIGN`, exactly
as the notebook's final operation does.

The notebook's `Total Length of Fwd Packet == 0` predicate maps to the custom
exporter's transport `payload_size_max == 0`. This is the available packet-level
semantic for “no payload”; captured frame bytes are not used because link/IP/TCP
headers keep `bytes_fwd` nonzero even when transport payload is empty.

The approved R0 output uses directional 300-second sessions, while Distrinet's
notebook targets 120-second CICFlowMeter biflows. Two March 2 attempted-Botnet
refinements require biflow-only fields: backward RST count, and simultaneous
forward/backward payload totals. R1 does not invent them. Matching rows retain
the verified broad `Botnet Ares` label and carry respectively
`unresolved_missing_bwd_rst_flags` or
`unresolved_missing_reverse_payload_total`. `label_verified` covers the broad
label; `label_refinement_verified` is false for those rows. Their counts are a
mandatory R1 audit finding and determine whether the exit criterion is met.

## Original-schedule cross-check

The independent original labeler uses only the attacker column, victim column,
attack name, date, start minute and finish minute published in UNB Table 2.
Schedule wall-clock values are converted to UTC by adding four hours, consistent
with the packet timestamps and the prior February 14 verification. A minute-
resolution finish includes the entire named minute. The original join is
attacker-to-victim only because those are the directions explicitly supplied by
the table; no corrected endpoint direction is imported into this cross-check.
Duplicate March 1 table rows are treated as one identical rule.

Every row stores both labels and `label_discrepancy`. The discrepancy log groups
all corrected/original label pairs by date, including pairs where one side is
`BENIGN`. It is evidence of rule differences, not an instruction to prefer the
original label.

## Stage mapping

- `BENIGN` → Benign (0)
- `Infiltration - NMAP Portscan` → Reconnaissance (1)
- FTP/SSH brute-force and `Infiltration - Dropbox Download` → Initial Access (2)
- `Botnet Ares` → Command & Control (4)
- `Infiltration - Communication Victim Attacker` → Unknown/Ambiguous (6)

The communication component remains Unknown because the March 1 documentation
describes console-like data with large packets toward the victim; the evidence
does not distinguish command-and-control from exfiltration reliably. No row is
assigned Lateral Movement or Exfiltration by assumption.

## Standing disclosures

`flow_feature_source: CYBERMIND custom directional packet exporter; 40-column
schema; satisfies the project's 20-field packet-feature contract when verified,
but is not CICFlowMeter and omits approximately 67 of the pinned CICFlowMeter
traffic-statistic columns. No CICFlowMeter feature parity is claimed.`

**Real-chunk validation does not include a Lateral Movement transition.
Kill-chain-diversity validation on real data covers the other represented stages
only; it does not validate Lateral Movement.**
