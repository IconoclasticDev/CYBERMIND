# CYBERMIND vs Feature-Matched Logistic Baseline

Both systems receive the same four observed graph windows, training split, held-out capture-day test split, fixed threshold `0.5`, and four unseen target windows. The baseline receives all node and edge columns with the registered graph-summary aggregations; it never reads future features.

## Held-out four-window result

| Model | Precision | Recall | F1 | FPR | AP | False positives | Misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| CYBERMIND world model | 99.70% | 97.30% | 98.49% | 0.56% | 99.85% | 8 | 74 |
| Feature-matched logistic | 93.14% | 92.19% | 92.66% | 13.14% | 98.07% | 186 | 214 |

## Judge-facing measured advantages

- **5.82 percentage-point F1 gain.**
- **95.7% fewer false alarms:** 8 instead of 186 across 4,156 future-window decisions.
- **23.3× lower false-positive rate:** 0.56% instead of 13.14%.
- **140 fewer missed attack windows:** 74 instead of 214.
- Compact teacher: **925,064 parameters** and **10.69 MB**, including training state.

## Capability difference

Logistic regression provides one binary probability per horizon. CYBERMIND additionally models graph relationships and temporal state transitions, generates stochastic future trajectories, estimates rollout dispersion, decodes stage progression, exposes host/edge evidence, and supports intervention sensitivity probes.

## Efficiency wording

The measured efficiency advantage is operational: dramatically fewer false alerts for analysts while producing several decision outputs in one compact model. Logistic regression is computationally simpler, so this report does not claim CYBERMIND has lower arithmetic cost or latency without a separate controlled benchmark.
