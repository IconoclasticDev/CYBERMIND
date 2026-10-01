# Real CIC-IDS2018 training report

This run trained CyberMind on 1,186,046 packet-derived flows reconstructed from
15 audited CIC-IDS2018 PCAP captures. All labeled CSV and canonical Parquet rows
passed strict endpoint, timestamp, label, verification, and packet-feature
validation before graph preparation.

## Run outcome

- GPU: NVIDIA GB10
- Precision: bfloat16
- Prepared sequences: 1,699 train, 428 validation, 431 test
- Maximum epochs: 50
- Completed epochs: 18
- Stop reason: early stopping after 15 epochs without selection improvement
- Selected checkpoint epoch: 3
- Selection rule: validation F1 with stage-loss tie-breaking inside a 0.03 F1 band
- Selected-epoch validation F1 during training: 0.9143546441

The fixed-checkpoint evaluator reported:

| Split | F1 | Precision | Recall | FPR | Average precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 0.8475033738 | 1.0 | 0.7353629977 | 0.0 | 1.0 |
| Test | 0.9766454352 | 1.0 | 0.9543568465 | 0.0 | 1.0 |

The validation and test periods contain BENIGN and BOTNET ARES labels. These
scores therefore measure the chronological held-out periods in this corpus; they
do not establish equal performance on every attack family or unseen networks.
Stage classes 3 through 5 have no training examples in this reconstructed chunk.

## Artifacts

- `checkpoints/real_best/best.pt`: selected epoch-3 checkpoint
- `checkpoints/real_best/best_last.pt`: final epoch-18 state
- `checkpoints/real_best/epochs/`: periodic epoch checkpoints
- `configs/real_best.yaml`: complete run configuration
- `data/intermediate_real_best/`: canonical Parquet inputs
- `data/processed_real_best/`: prepared train/validation/test tensors and normalization
- `results/real_best/eval_*_fixed.json`: fixed-checkpoint evaluations
- `results/real_best/train_history.json`: per-epoch history
- `results/real_best/rebuild/`: capture export and regenerated-label provenance

Checkpoint SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `best.pt` | `8f29e1127518a7d094e653abc7bf5af7ca83d6c4d90130915e41f025188ccfc5` |
| `best_last.pt` | `f9efa6efb4f11869ffd1c40c1c73bba2342c505b969c45d8015576e463663dbc` |
| `epoch_0005.pt` | `69a4b39c11c98cf5d3de7f547a03e67b9e47fb60acaf8ce233554f78ae24be61` |
| `epoch_0010.pt` | `cd9d4c8e0d66813461f64839a08b862f1e6520685fc29727378325161aa02544` |
| `epoch_0015.pt` | `3cf9ded20de3da5a3312d1923fa84b2007a522c3f4833545391e4b67bf3d2f1d` |

## Reproduction

Run `scripts/run_real_best_pipeline.sh` from `CYBERMIND_REAL`. The raw CIC-IDS2018
archives and reconstructed CSV files are intentionally excluded from Git because
individual files exceed GitHub's file-size limit and the full source corpus is
hundreds of gigabytes. The tracked download manifest, audited R0/R1 manifests,
rebuild script, strict validation reports, and regenerated-label manifest retain
the source paths, sizes, and cryptographic provenance required to reconstruct the
training package from the official archives.

## SIH26153 scope and recommended fine-tuning

Processing every downloaded archive is unnecessary for the SIH26153 prototype.
The problem asks for flow- and packet-level telemetry, a learned temporal network
state model, K-step infiltration forecasting, attack-stage mapping, interpretable
outputs, offline operation, and comparison with a logistic-regression baseline.
The current system already implements those architectural requirements. The next
work should strengthen the evidence around this checkpoint instead of maximizing
raw corpus size.

Recommended current-model fine-tuning:

1. Resume from `best.pt` with a learning rate of `2e-5` to `5e-5`, dropout of
   `0.25` to `0.35`, early-stopping patience of 5, and at most 10 additional
   epochs. The validation decline after epoch 6 makes long continuation harmful.
2. Use balanced window sampling and benign hard negatives. Preserve chronological
   train/validation/test boundaries and never tune against the test split.
3. Search only a compact matrix of learning rate, dropout, stage-loss weight, and
   weight decay. Rank candidates by infiltration F1 subject to an explicit FPR
   ceiling, then use stage loss as the tie-breaker.
4. Calibrate the decision threshold on a benign-rich validation subset and freeze
   it before the final test. Report F1, precision, recall, FPR, AUPRC, per-stage
   results, and K-step rollout quality.
5. Run the feature-matched logistic baseline on the identical histories and
   targets. SIH26153 explicitly asks for evidence that temporal dynamics add value;
   do not claim superiority unless the measured comparison supports it.
6. Train three seeds for the selected configuration and report mean and spread.
   Ensemble them only if the validation-only selection rule improves consistently.

On the current GB10 instance, this focused cycle should take about 2–4 hours:

| Work | Estimated time |
| --- | ---: |
| 6–10 compact fine-tuning trials | 75–150 minutes |
| Three-seed confirmation of the selected setup | 40–75 minutes |
| Threshold calibration, logistic baseline, and final report | 30–60 minutes |

If the evaluation needs broader attack-stage coverage, add only the capture
windows needed for the missing stages; allow another 4–8 hours for extraction,
label auditing, and retraining. An exhaustive 486 GB rebuild would take several
days and is not needed to demonstrate the SIH26153 deliverables.
