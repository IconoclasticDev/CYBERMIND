# `best.pt` UI integration and four-step comparison

Date: 2026-09-27. The React UI now runs with design-matched functional corrections at `http://127.0.0.1:50068/`. Its FastAPI backend loads `integrations/cybermind_deep-main/models/best.pt`, a hash-identical copy of the validation-selected epoch-21 `checkpoints/final_grouped/best.pt` (SHA-256 `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39`). The running `/api/model` endpoint reports `best.pt`, available on CUDA. The former `best_last.pt` and the archive's named `cybermind_final.pt` are not loaded. The earlier unchanged-source-hash check describes the pre-repair import; the subsequent UI repair corrected upload feedback, benchmark evidence, rollout labels, provenance text, and mobile layout.

The comparison below independently recomputes metrics from the existing sample-level `results/final_grouped/eval_test_k4.json` and `results/final_grouped/baseline_test_k4.json`. Each of the 1,039 test sequences has identical target labels and target timestamps in both files. Both use four observed history windows, four unseen target windows, and a threshold of 0.5. The logistic baseline uses the feature-matched node/edge representation and training-only scaling. The processed `data/processed_final_grouped` split is absent on this machine; **this is verification of saved predictions, not a new inference or baseline fit.** The training report identifies epoch 21 as selected, but the saved evaluation JSON does not itself embed the checkpoint SHA-256.

| Held-out horizon | Model F1 | Logistic F1 | Model FPR | Logistic FPR | Model TP/FP/TN/FN | Logistic TP/FP/TN/FN |
|---|---:|---:|---:|---:|---|---|
| 1 | 0.985272 | 0.947902 | 0.011299 | 0.118644 | 669/4/350/16 | 655/42/312/30 |
| 2 | 0.987454 | 0.951825 | 0.002825 | 0.093220 | 669/1/353/16 | 652/33/321/33 |
| 3 | 0.984456 | 0.921739 | 0.002825 | 0.166667 | 665/1/353/20 | 636/59/295/49 |
| 4 | 0.982222 | 0.883333 | 0.005650 | 0.146893 | 663/2/352/22 | 583/52/302/102 |
| Pooled | **0.984854** | **0.926632** | **0.005650** | **0.131356** | **2666/8/1408/74** | **2526/186/1230/214** |

Pooled precision/recall/AP are 0.997008/0.972993/0.998504 for the model and 0.931416/0.921898/0.980721 for logistic. The saved held-out predictions therefore show a 0.058222 absolute F1 gain and 178 fewer false positives for the selected model under this specific protocol. Validation also favors the model: pooled F1 0.894515 versus 0.767553 and FPR 0.008914 versus 0.041783. These are capture-grouped CIC-IDS2018 results, not evidence of generalization to a new network.

The saved representative fixed-hyperparameter suite (`results/final_grouped/baseline_suite_comparison.json`) uses the same feature-matched four-window protocol. This table reports its recorded pooled test metrics; unlike the logistic row above, the other baseline rows were not independently recomputed from sample-level probabilities in this audit.

| Model | F1 | FPR | False positives |
|---|---:|---:|---:|
| CYBERMIND `best.pt` | **0.984854** | **0.005650** | **8** |
| Random Forest | 0.952634 | 0.016949 | 24 |
| MLP | 0.940417 | 0.093220 | 132 |
| Logistic Regression | 0.926632 | 0.131356 | 186 |
| Linear SGD | 0.902042 | 0.115113 | 163 |
| RBF SVM | 0.834499 | 0.007062 | 10 |
| Histogram Gradient Boosting | 0.522650 | 0.057203 | 81 |
| Always Benign | 0 | 0 | 0; misses all 2,740 positive windows |

The model's test stage macro-F1 is only 0.244304. Authoritative training coverage lacks stages 3 and 5, and the unseen Command & Control campaign is not correctly identified. The binary forecasting advantage must not be described as accurate full kill-chain stage forecasting. The saved `model_comparison.json` lists 925,064 state-dictionary elements; the running model reports 859,528 parameters because the remaining 65,536 elements are a non-trainable positional-encoding buffer.
This checkpoint has `loss.use_crf_stage: false`, and its saved evaluation records `stage_decoding: argmax`; any static UI description of CRF decoding does not describe this loaded model.

A separate deterministic PCAP smoke test of the selected checkpoint accepted 144 flows and produced the observed step plus four future steps. It verifies the application path only, not model accuracy.
