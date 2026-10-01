# CIC-IDS2018 stage-expansion training report

The audited corpus was expanded with both corrected February 28 victim captures. The split remains chronological with a full-history purge at each boundary.

## Coverage

Target-window stage counts `[benign, recon, initial access, lateral movement, C2, exfiltration, unknown]`:

- **train:** `[30348, 5844, 5820, 0, 735, 0, 153]`
- **val:** `[0, 0, 0, 0, 5865, 0, 0]`
- **test:** `[2745, 0, 0, 0, 3165, 0, 0]`

CIC-IDS2018 provides supported labels here for benign, reconnaissance, initial access, and C2. The added captures do not provide verified lateral-movement or exfiltration labels, so those stages remain unsupported rather than receiving inferred labels.

## Fixed-threshold evaluation

| Split | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| Validation | 1.000000 | 1.000000 | 1.000000 | n/a (no benign targets) |
| Test | 0.962264 | 1.000000 | 0.980769 | 0.042105 |

## Artifact

- Selected epoch: `9`
- Checkpoint: `checkpoints/stage_expansion/best.pt` (10.42 MB)
- Selection used validation F1 with stage loss as a tie-breaker inside the configured F1 tolerance.

## Interpretation

Validation is an attack-only chronological segment because the Botnet Ares activity is continuous across that period. It supports early stopping on recall/F1 and stage loss but cannot estimate false positives. The final test contains both benign and C2 targets and supplies the fixed-threshold precision and false-positive measurement. The C2 holdout is later traffic from the same Botnet Ares campaign. It tests chronological generalization within that campaign; it does not establish generalization to unrelated C2 families. A defensible lateral-movement or exfiltration claim requires a separately labeled source with those stages and a source-isolated external test.
