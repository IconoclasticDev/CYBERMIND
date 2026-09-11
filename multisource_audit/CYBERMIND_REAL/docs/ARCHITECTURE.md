# CYBERMIND Architecture

## Mathematical core

The system learns a latent transition model approximating:

`P(S_(t+1) | S_t)`

and performs recursive rollout:

`S_t -> S_(t+1) -> ... -> S_(t+K)`

## Pipeline

```text
PCAP / NetFlow / Logs
        |
        v
Flow + Packet + Timing Features
        |
        v
Dynamic Network Graph
Hosts = nodes; communication = edges; features = temporal state
        |
        v
GATv2 Graph Encoder
        |
        v
Temporal Transformer
        |
        v
Latent network state z_t
        |
        v
Dynamics Predictor
        |
        +------------------+
        |                  |
        v                  v
Future state        Infiltration + Stage heads
        |
        v
K-step rollout
        |
        +-----> Early-warning / uncertainty / explanation
        |
        +-----> Counterfactual interventions
                  |
                  +--> risk reduction / Attack Gravity
```

## Loss

`L = λ1 transition + λ2 infiltration + λ3 stage + λ4 calibration`

Optional graph-consistency regularization can be added later.

## Data leakage policy

Split by scenario/time group; never randomly split individual rows from the same attack episode across train/test.

## Known limitations

1. Some CIC-IDS2018 CSV distributions remove endpoint identities. Without identities, a faithful host graph cannot be constructed; the pipeline reports this instead of inventing topology.
2. Dataset labels are attack-family labels, not native MITRE ATT&CK stage annotations. Current stage targets are configurable proxy mappings. For a defensible ATT&CK-stage result, enrich training labels from packet/flow semantics or controlled scenario ground truth.
3. Counterfactual scores are model-based risk differences, not formal causal effects.
