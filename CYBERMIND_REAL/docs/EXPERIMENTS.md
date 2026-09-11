# Experimental plan

## Baseline

Train logistic regression on flow-level/tabular features. Report F1, precision, recall, FPR, AP and ROC-AUC where defined.

## World model

Report:

- transition validation error
- infiltration F1 / precision / recall / FPR / AP
- stage macro-F1
- Brier score / calibration
- K-step degradation by horizon
- mean early-warning lead time

## Generalization

1. Scenario-held-out test on CIC-IDS2018.
2. Later: cross-dataset validation on CTU-13 or UNSW-NB15.
3. Later: unseen attack family evaluation.

## Ablations

- no graph encoder
- no temporal encoder
- one-step only
- binary classifier baseline

These are not required to run the first working demo.

## Research claims

Use "counterfactual risk simulation" or "intervention-aware forecasting". Do not claim causal identification unless causal assumptions are formally justified.
