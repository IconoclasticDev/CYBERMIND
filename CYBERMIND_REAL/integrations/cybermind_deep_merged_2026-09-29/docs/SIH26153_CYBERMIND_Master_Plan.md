# SIH26153 — CYBERMIND
## Counterfactual World Model for Predictive Cyber Defence

> **One-line idea:** Existing IDS tells defenders what is happening. CYBERMIND learns how the network evolves, simulates where an attack can go next, and identifies the intervention that most reduces future compromise risk.

---

## 1. Problem Statement

**SIH PS:** SIH26153  
**Organization:** National Technical Research Organisation (NTRO)  
**Category:** Software  
**Theme in the supplied catalogue:** Space Technology  
**Working objective:** Build an AI system that learns evolving network behaviour, forecasts malicious progression before compromise is complete, maps the predicted progression to MITRE ATT&CK stages, explains the forecast, and operates offline.

The supplied SIH statement explicitly asks teams to move beyond static intrusion classification toward learned network-state transition dynamics and K-step forward simulation. It expects flow- and packet-level telemetry, a learned world model, infiltration forecasting, ATT&CK-stage mapping, explainability, an offline interface, and comparison against a logistic-regression baseline.

---

## 2. What the PS Actually Wants

Traditional IDS framing:

```text
Traffic → Benign / Malicious
```

SIH26153 framing:

```text
Network State at t
        ↓
Learn how the state evolves
        ↓
Predict future states
        ↓
Estimate future infiltration risk
        ↓
Predict future ATT&CK stage
        ↓
Explain why
```

The required mathematical core is the learned transition:

```text
P(S_t+1 | S_t)
```

followed by forward rollout:

```text
S_t → S_t+1 → S_t+2 → ... → S_t+K
```

The PS explicitly states that the system should model temporal relationships, infer evolving network state, forecast future attack progression, support MITRE ATT&CK mapping, and identify the traffic features driving the forecast.

---

## 3. Why a Normal Solution Will Not Be Enough

A weak interpretation of the PS would be:

```text
CIC-IDS → Transformer → attack probability → dashboard
```

That is technically valid only at a shallow level and is unlikely to be memorable.

The main competitive risk is building yet another:

- binary intrusion classifier
- anomaly detector
- LSTM over CSV rows
- SHAP dashboard
- generic SOC interface

The winning strategy is to implement the required world-model core and then add a **decision layer** around it.

---

# 4. CYBERMIND — Proposed Solution

## Core Concept

CYBERMIND is a **Graph-Temporal World Model** for cyber defence.

It continuously constructs a latent representation of the network, learns how that state evolves, rolls the model forward into multiple possible futures, forecasts attacker progression, and evaluates defensive interventions against those futures.

### The conceptual loop

```text
OBSERVE
   ↓
UNDERSTAND NETWORK STATE
   ↓
PREDICT FUTURE
   ↓
SIMULATE ALTERNATIVE FUTURES
   ↓
CHOOSE BEST INTERVENTION
   ↓
RE-OBSERVE
   ↓
REPLAN
```

This changes the product from a passive IDS into a **predictive cyber-defence engine**.

---

# 5. Architecture Overview

```text
                         ┌───────────────────────────┐
                         │      NETWORK TELEMETRY    │
                         │                           │
                         │ PCAP / NetFlow / Logs    │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │   STREAM FEATURE ENGINE   │
                         │                           │
                         │ Flow + Packet + Timing   │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────┐
                  │      DYNAMIC NETWORK GRAPH          │
                  │                                     │
                  │ Hosts = Nodes                       │
                  │ Flows = Edges                       │
                  │ Features = Temporal State           │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────┐
                       │ GRAPH-TEMPORAL ENCODER  │
                       │                         │
                       │ GAT / GraphSAGE         │
                       │ + Temporal Encoder      │
                       └────────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ LATENT NETWORK STATE │
                         │         z_t          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    WORLD MODEL CORE  │
                         │                      │
                         │ Temporal Transformer │
                         │ + Dynamics Model     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ MULTI-STEP ROLLOUT    │
                         │ t+1 ... t+K           │
                         └──────────┬───────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
               ▼                    ▼                    ▼
      ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
      │ INFILTRATION    │  │ ATT&CK STAGE    │  │ UNCERTAINTY /   │
      │ FORECAST        │  │ FORECAST        │  │ OOD             │
      └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    ▼
                        ┌─────────────────────────┐
                        │ MULTI-FUTURE GENERATOR │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ COUNTERFACTUAL ENGINE   │
                        │                         │
                        │ No Action               │
                        │ Block Host X             │
                        │ Block Port Y             │
                        │ Isolate Host Z           │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ INTERVENTION SCORING     │
                        │                         │
                        │ Risk reduction          │
                        │ Attack gravity           │
                        │ Future branch collapse   │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ DEFENDER DECISION PANEL │
                        └─────────────────────────┘
```

---

# 6. Innovation Layer 1 — Counterfactual Cyber Twin

## The key differentiator

The PS asks:

> What happens next?

CYBERMIND additionally asks:

> What happens next **if we intervene differently?**

Example:

```text
CURRENT NETWORK STATE
          ↓
      WORLD MODEL
          ↓
  ┌───────┼────────┐
  ↓       ↓        ↓
No Action Block X  Isolate Y
  ↓       ↓        ↓
82%       43%      17%
Future    Future   Future
Risk      Risk     Risk
```

The system can therefore recommend an intervention based on predicted future risk rather than a simple present-time alert.

### Important terminology

Use:

- **Counterfactual Risk Simulation**
- **Intervention-Aware Forecasting**

Avoid claiming causal inference unless the causal assumptions are formally established.

---

# 7. Innovation Layer 2 — Attack Gravity

## Definition

Attack Gravity measures how strongly an asset pulls the future attack trajectory toward compromise.

For asset i:

```text
AttackGravity(i)
≈
P(future compromise | current state)
-
P(future compromise | isolate i)
```

Interpretation:

> If we can intervene on only one asset, which asset gives the largest predicted reduction in future compromise risk?

Example network:

```text
               Host A
                 │
                 │ gravity 0.18
                 │
Host B ─────── Host C ─────── Host D
                 ▲
                 │
           gravity 0.91
```

Host C becomes the highest-leverage defensive target.

### Why this is powerful

It turns a static “suspicious host” score into:

> **“This host is important because removing it changes the future trajectory the most.”**

---

# 8. Innovation Layer 3 — Multi-Hypothesis Future

A single forecast hides uncertainty.

CYBERMIND can produce multiple plausible futures:

```text
CURRENT STATE
      ↓
  WORLD MODEL
      ↓
 ┌────┼────┐
 ↓    ↓    ↓
A     B    C
48%  31%  21%
```

Example:

```text
Future A — 48%
Lateral Movement → C2 → Exfiltration

Future B — 31%
Lateral Movement → C2 → Stop

Future C — 21%
Initial Access → Contained
```

Then distinguish:

- **Most likely trajectory**
- **Most dangerous trajectory**
- **Highest-impact low-probability branch**

This is operationally more useful than a single attack label.

---

# 9. Innovation Layer 4 — Attack Path Forecasting

The PS asks for attack-stage mapping.

We can additionally forecast the **asset-to-asset path**:

```text
                 RECON
                   │
                   ▼
             INITIAL ACCESS
                   │
             ┌─────┴─────┐
             ▼           ▼
           Host A       Host B
             │           │
             └─────┬─────┘
                   ▼
            LATERAL MOVEMENT
                   │
                   ▼
                 Host C
                   │
                   ▼
                   C2
```

Instead of only reporting:

> Lateral Movement = 72%

the system can report:

> Host A → Host C is the most probable next movement path.

---

# 10. Innovation Layer 5 — Early Warning Lead Time

Do not optimize only for classification metrics.

Introduce a primary operational metric:

## Mean Early Warning Lead Time

Concept:

```text
Actual compromise
        │
        │
        │
        ▼
██████████████████
        ▲
        │
 CYBERMIND warning
```

Measure:

```text
lead time = actual critical-stage timestamp
            - first reliable forecast timestamp
```

Show alongside F1/precision/recall/FPR.

This directly communicates whether forecasting creates useful defender time.

---

# 11. Innovation Layer 6 — Risk vs Confidence

Risk and model certainty are not the same thing.

Example:

```text
INFILTRATION RISK
82%

MODEL CONFIDENCE
LOW

OOD SCORE
HIGH

Reason:
Unseen trajectory family
```

versus:

```text
INFILTRATION RISK
82%

MODEL CONFIDENCE
HIGH

OOD SCORE
LOW

Reason:
Known temporal pattern
```

This prevents the interface from pretending the model is omniscient.

---

# 12. Innovation Layer 7 — Future-Oriented Explainability

Standard XAI:

> Port 445 contributed 22%.

CYBERMIND:

> Repeated SMB communication increased the predicted probability of lateral movement. Simulated isolation of Host C sharply reduces that future branch.

Use the chain:

```text
Observed evidence
      ↓
Predicted transition
      ↓
Future consequence
      ↓
Suggested intervention
```

Possible technical implementations:

- attention weights
- SHAP
- feature attribution
- graph-edge contribution
- temporal contribution maps

The PS explicitly requires interpretable forecasts and says black-box outputs without interpretability are unacceptable.

---

# 13. Network Representation

The network naturally maps to a graph.

```text
Node = Host / Server / Device
Edge = Communication relationship
Time = State evolution
```

Example:

```text
      User PC
        │
        │ SMB
        ▼
      File Server
        │
        │ DB traffic
        ▼
    Database Server
```

Each node can have dynamic features:

- packet statistics
- flow counts
- protocol distributions
- port activity
- timing statistics
- host activity level
- anomaly score

Each edge can have:

- bytes
- packets
- protocol
- port
- direction
- duration
- inter-arrival statistics

---

# 14. Model Architecture

## Recommended MVP

Do not build an enormous research model.

Use:

```text
GraphSAGE / GAT
      ↓
Temporal Transformer
      ↓
Latent State z_t
      ↓
Dynamics Predictor
      ↓
Multi-step Rollout
```

### Outputs

Multiple heads:

```text
                Latent State
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
  Future State   Infiltration   ATT&CK
    Decoder       Probability    Stage
        │            │             │
        └────────────┼─────────────┘
                     ▼
              Explanation Head
```

---

# 15. Data Strategy

The SIH PS explicitly mentions open datasets such as:

- CIC-IDS2018
- CTU-13
- UNSW-NB15
- CICIoT2023
- LANL Authentication Dataset
- DARPA intrusion-detection datasets

and public knowledge sources including MITRE ATT&CK, CAPEC and CVE/NVD.

## Recommended split

### Training
CIC-IDS2018 or a carefully curated subset.

### Cross-dataset validation
CTU-13 / UNSW-NB15.

### Unseen-attack evaluation
Hold out an entire attack family or scenario.

Do **not** rely on random row-level splitting only.

---

# 16. Avoid Data Leakage

This is one of the most important engineering details.

Bad:

```text
Same attack scenario
 ├── random rows → train
 └── random rows → test
```

Better:

```text
Scenario A/B/C/D → TRAIN
Scenario E       → VALIDATION
Scenario F       → TEST
```

Best practical demo:

> Train on known scenarios, then evaluate on an unseen scenario or attack family.

This gives a much stronger claim of generalization.

---

# 17. Training Targets

Build time windows:

```text
W1 → W2 → W3 → W4 → W5 ...
```

Create network states:

```text
S1, S2, S3, S4...
```

Train the dynamics model on:

```text
S_t → S_t+1
```

Then construct attack progression labels.

Possible supervision:

- state transition features
- infiltration probability
- attack stage
- scenario boundary

---

# 18. Multi-Task Objective

A practical training objective can combine:

```text
L_total =
  λ1 * transition_loss
+ λ2 * infiltration_loss
+ λ3 * stage_loss
+ λ4 * calibration_loss
```

Optional:

```text
+ λ5 * graph_consistency_loss
```

The purpose is to stop the model from learning only a binary attack classifier.

---

# 19. Counterfactual Simulation

This is the primary innovation layer.

For candidate intervention i:

```text
Current state S_t
       ↓
Counterfactual mutation
       ↓
S'_t(i)
       ↓
World Model rollout
       ↓
Future risk_i
```

Evaluate actions such as:

```text
No Action
Block Host
Block Port
Isolate Host
Restrict Edge
Rate Limit
```

Rank them by expected risk reduction.

---

# 20. Attack Gravity Implementation

For each node/edge:

```text
Baseline risk = R(S_t)

Counterfactual risk_i = R(S_t after intervention on i)

AttackGravity_i = Baseline risk - Counterfactual risk_i
```

Sort descending.

This yields the highest-leverage defensive intervention candidates.

---

# 21. Uncertainty & OOD

Practical options:

- prediction entropy
- ensemble variance
- Monte Carlo dropout
- distance in latent embedding space
- Mahalanobis distance
- known-vs-unseen trajectory score

The first MVP can simply combine calibrated probability with an OOD indicator.

---

# 22. Evaluation

## Mandatory SIH metrics

The PS asks for comparison against a logistic-regression baseline using:

- F1
- precision
- recall
- false-positive rate

and wants measurable evidence that temporal dynamics learning improves performance.

## Additional metrics

### 1. Early Warning Lead Time
How early before the critical attack stage did the model warn?

### 2. Calibration
Does a predicted 80% risk behave approximately like an 80% event probability?

### 3. Unseen Attack Performance
How well does the model generalize to an unseen attack family/scenario?

### 4. Forecast Stability
Does the prediction behave sensibly across adjacent time windows?

### 5. Counterfactual Risk Reduction
How much predicted future risk is removed by the recommended intervention?

---

# 23. Baselines

At minimum:

### Baseline 1
Logistic Regression — required by PS.

### Baseline 2
LSTM — temporal benchmark.

### Our model
Graph + Temporal World Model.

This creates a strong experimental story:

```text
Static classifier
      ↓
Temporal classifier
      ↓
Graph-temporal world model
      ↓
Counterfactual defence layer
```

---

# 24. Final Demo — The “WTF” Moment

## Simulated Enterprise Network

Use a controlled, safe synthetic environment.

```text
             INTERNET
                 │
              FIREWALL
                 │
       ┌─────────┼─────────┐
       │         │         │
      WEB      USER PC   FILE SERVER
                 │
                 ▼
                 DB
```

A benign baseline starts.

Then a controlled attacker sequence begins.

### Stage 1

```text
Risk = low
State = normal
```

### Stage 2

```text
Recon detected
Risk increases
```

### Stage 3

```text
Forecast:
Lateral Movement → 72%
```

### Stage 4

Click:

# RUN COUNTERFACTUAL

The UI produces:

```text
WITHOUT INTERVENTION
Future risk: HIGH

BLOCK HOST A
Future risk: MEDIUM

BLOCK PORT 445
Future risk: LOW-MEDIUM

ISOLATE HOST C
Future risk: VERY LOW
```

Then:

# RECOMMENDED ACTION

**Isolate Host C**

### Why?

```text
Host C has highest Attack Gravity.

Its isolation collapses the dominant
predicted lateral-movement branch.
```

Then resume the synthetic attack.

The model updates.

The defender replans.

---

# 25. War-Room UI

Do not make a generic CRUD dashboard.

Use a single-screen intelligence interface.

## LEFT — Network Map

Dynamic graph:

- normal nodes
- suspicious nodes
- high-gravity nodes
- attack-path edges

## CENTER — Future Forecast

```text
NOW ─ +1 ─ +2 ─ +3 ─ +4

48% → Lateral → C2 → Exfil
31% → Lateral → C2 → Stop
21% → Contained
```

## RIGHT — Defence Recommendation

```text
CURRENT RISK
82%

CRITICAL ASSET
Host C

ATTACK GRAVITY
0.91

RECOMMENDED ACTION
ISOLATE HOST C

PREDICTED RISK AFTER ACTION
17%
```

Numbers above are illustrative UI values only; final values must come from experiments.

---

# 26. Technology Stack

## Data

- Python
- Pandas
- NumPy
- Scapy / PyShark

## ML

- PyTorch
- PyTorch Geometric
- scikit-learn

## Models

- Logistic Regression
- LSTM
- GAT / GraphSAGE
- Temporal Transformer

## Explainability

- SHAP
- Attention analysis

## Visualization

- NetworkX
- Plotly
- lightweight web frontend or Streamlit for the first prototype

## Packaging

- Fully offline
- reproducible environment
- fixed model weights
- local data only during evaluation

---

# 27. What We Should NOT Do

## Do not build

```text
CSV → XGBoost → malicious/benign
```

and call it a world model.

## Do not rely only on

- generic dashboards
- binary classification
- one-step prediction
- random train/test splits
- giant LLM APIs
- cloud-only inference
- fake causal claims

## Do not train a huge model unnecessarily

The winning advantage is the **system architecture and experimental story**, not model size.

---

# 28. 36-Hour MVP Strategy

## Before SIH

Pre-build:

- datasets
- preprocessing
- feature pipeline
- graph construction
- baseline
- model training scripts
- candidate weights
- evaluation scripts
- UI skeleton
- attack-path visualizations

## During SIH

### Phase 1 — Integration
Wire the final model to the interface.

### Phase 2 — Benchmarking
Run baseline vs world-model experiments.

### Phase 3 — Counterfactual layer
Implement intervention simulation on the network graph.

### Phase 4 — Visual polish
Build the war-room interface.

### Phase 5 — Validation
Run unseen-scenario testing.

### Phase 6 — Submission package
Prepare:

- GitHub
- README
- architecture document
- demo video
- five-slide presentation

The SIH PS itself specifies a source-code link, setup instructions, architecture document, demo video and technical presentation deliverables.

---

# 29. Suggested Team Split

## Person 1 — Data/Telemetry
PCAP parsing, feature extraction, time windows.

## Person 2 — Graph Representation
Dynamic graph construction and node/edge features.

## Person 3 — World Model
GNN + temporal model + training.

## Person 4 — Forecasting/Explainability
Attack-stage mapping, SHAP/attention, uncertainty.

## Person 5 — Counterfactual Engine
Intervention simulator + Attack Gravity.

## Person 6 — Product/Demo
War-room UI, integration, presentation and demo orchestration.

---

# 30. Research Positioning

The research landscape already contains substantial work on:

- intrusion detection
- temporal cyber modelling
- graph neural networks
- attack forecasting
- predictive cyber defence

Therefore, the novelty should not be advertised as:

> “We invented AI-based cyber-attack prediction.”

Instead:

> **We combine temporal graph world modelling, multi-step attack trajectory forecasting, counterfactual risk simulation, and intervention ranking into one offline predictive-defence loop.**

This is a much more defensible innovation claim.

---

# 31. Strongest Pitch

## 10-second version

> **“IDS tells you what is happening. CYBERMIND predicts how the attack evolves, simulates the future, and tells you which intervention can stop it.”**

## 30-second version

> **“CYBERMIND models an enterprise network as a dynamic graph and learns how its state evolves over time. Instead of classifying isolated traffic, it rolls the learned world model forward to forecast attack progression and map future behaviour to MITRE ATT&CK. Then it simulates defensive actions—such as isolating a host or blocking a communication path—and recommends the intervention that maximally reduces predicted compromise risk.”**

## Hero statement

# PREDICT → SIMULATE → INTERVENE → REPLAN

---

# 32. Why This Can Stand Out

The strongest differentiation is not a single exotic algorithm.

It is the closed loop:

```text
OBSERVE
   ↓
MODEL NETWORK STATE
   ↓
FORECAST ATTACK TRAJECTORY
   ↓
GENERATE MULTIPLE FUTURES
   ↓
SIMULATE INTERVENTIONS
   ↓
RANK DEFENSIVE ACTIONS
   ↓
EXPLAIN THE DECISION
   ↓
REPLAN
```

Most student solutions will likely stop at:

```text
Detect → Alert
```

CYBERMIND aims to reach:

```text
Predict → Explain → Simulate → Act
```

---

# 33. Final Recommended Scope

## MUST HAVE

- flow + packet feature pipeline
- dynamic network state
- temporal world model
- K-step rollout
- infiltration probability
- ATT&CK stage forecast
- explainability
- logistic baseline
- offline demo
- unseen-attack evaluation

## HIGH-IMPACT INNOVATION

- counterfactual risk simulation
- Attack Gravity
- multi-hypothesis future
- early-warning lead time
- confidence/OOD layer

## IF TIME ALLOWS

- synthetic attacker environment
- online re-planning
- richer graph attention visualization
- calibrated probabilistic forecasting
- intervention policy learning

---

# 34. Final Product Definition

## CYBERMIND
### Counterfactual World Model for Predictive Cyber Defence

**Observe the network.**  
**Understand how it evolves.**  
**Predict where the attack is going.**  
**Simulate what happens if we intervene.**  
**Choose the highest-leverage action.**  
**Replan as reality changes.**

---

## Source Basis

This document is based primarily on the supplied SIH26153 problem-statement material and the SIH 2026 master catalogue. The PS specifies the network-state/world-model framing, required telemetry, K-step forecasting, ATT&CK mapping, explainability, offline operation, baseline comparison, and submission deliverables. It does **not** itself require the counterfactual/Attack Gravity layers; those are proposed innovation extensions.
