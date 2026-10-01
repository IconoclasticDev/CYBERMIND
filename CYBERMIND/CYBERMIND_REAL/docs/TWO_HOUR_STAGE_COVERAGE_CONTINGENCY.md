# Two-Hour Stage-Coverage Contingency

The epoch-21 checkpoint remains unchanged. CYBERMIND now separates its analyst output into:

1. the raw learned model stage;
2. the coverage-aware reported stage; and
3. observed rule-supported evidence for stages 3–5.

Stages 3 (Lateral Movement), 4 (Command & Control) and 5 (Exfiltration) do not have complete training support. The analyst layer therefore abstains to `Unknown/Ambiguous` when a raw model stage in this range lacks supporting evidence. It never changes the learned infiltration probability.

The evidence layer inverse-transforms graph features with the checkpoint's training normalization and reports the contributing hosts and measurements. Its conservative indicators are:

- Stage 3: new internal peers, peer fan-out and node anomaly proxy after the learned risk gate passes.
- Stage 4: a repeated external peer across observed windows after the learned risk gate passes.
- Stage 5: an externally directed outbound-volume surge and high outbound/inbound ratio after the learned risk gate passes.

These indicators support analyst triage. They are not trained stage predictions, accuracy evidence, attack ground truth or causal conclusions. Hostnames that cannot be classified as RFC1918 or external IP addresses do not pass address-dependent rules.

The frozen four-window checkpoint results remain:

| Split | F1 | Precision | Recall | FPR | AP |
|---|---:|---:|---:|---:|---:|
| Validation | 0.894515 | 0.952096 | 0.843501 | 0.008914 | 0.892259 |
| Test | 0.984854 | 0.997008 | 0.972993 | 0.005650 | 0.998504 |

No new stage-accuracy claim is made. Genuine stage 3–5 learning still requires independently grouped, authoritative captures as specified in `STAGE_3_TO_5_COVERAGE_IMPLEMENTATION_PLAN.md`.

## Verification

- Full suite: **234 passed**.
- Frozen test evaluation: every protected metric reproduced exactly; all recorded differences are `0.0`.
- Machine-readable result: `results/final_grouped/stage_contingency_verification.json`.
- Real normalized-checkpoint smoke test: evidence generation and low-risk abstention completed successfully.
