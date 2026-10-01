# CYBERMIND demo film — continuous narration (3:18 target)

The supplied reference video moves from a brief problem-and-solution opening into one continuous product walkthrough, then spends its final minute on the architecture diagram before a short closing frame. Follow that same progression. **Record the voiceover as one uninterrupted take**; the time marks below are editing guides, not pauses or separate spoken segments. Let cursor movement and the result of each action motivate the next screen. Use gentle zooms or dissolves only where a screen transition is unavoidable. Cut processing waits under the continuing narration.

## On-screen flow (not spoken)

| Approximate time | Picture and live action |
|---|---|
| **0:00–0:17** | Show the SIH26153 challenge in a clean opening visual: observed network traffic becoming a future risk timeline. Reveal CYBERMIND as the proposed solution. Move into the running desktop app without a second title pause. |
| **0:17–0:41** | Begin in **Command Center**. Manually choose a real, provenance-recorded attack-window flow CSV using **Upload PCAP / CSV**; do not preload or call out its filename. Show the loaded case, risk cards, network graph, and one host click. Keep the cursor visible. |
| **0:41–1:02** | Follow that same case into **Live Monitor** and **Flagged Flows**. Scroll the timeline and inspect one flow’s endpoints, port, volume, and risk band. Let the camera follow the selected item rather than jumping between full-screen stills. |
| **1:02–1:30** | Open **Threat Forecast** and move across its future-window risk curve. Briefly show **Attack Graph** and **Benchmark**. In **Parallel Futures**, click **Simulate Parallel Futures** and compare **Future A (No Action)** with **Future B (Rate limit)**; hold on the actual relative-risk and final-risk values. |
| **1:30–1:49** | Return to **Command Center → Validation Engine** and click **Run local check**. Hold on the actual HTTP response codes and SHA-256 hashes. Open the floating assistant and ask **“How many flows are loaded?”**; show its case-grounded answer. |
| **1:49–2:12** | Open **Reports**. Export an encrypted incident brief, choose the destination, then import that JSON in **Decrypt Encrypted Incident Brief**. Enter the separately held key with the key field obscured; show the readable report and its download action. |
| **2:12–3:09** | Bring the supplied four-tier diagram over the app with a smooth zoom. Travel left to right across each tier as the narration reaches it. Give Tier 2’s model path enough screen time to read. Do not use four hard cuts between tiers. |
| **3:09–3:18** | Pull back to the entire diagram, then resolve to the CYBERMIND name and a simple closing line. Let the final music bed continue briefly after the last word. |

## Voiceover — read continuously

“An attack does not arrive as one neat alert. It unfolds through hosts, connections, and decisions, while defenders are still piecing together what happened. SIH26153 asks us to look ahead: can network evidence help an analyst see a plausible next step? CYBERMIND is our offline answer.

I begin with captured traffic. As I import this flow file, CYBERMIND turns it into a case, and the Command Center brings the hosts, recent activity, and current risk into one view. Selecting a host takes me from the overview to the evidence behind it. I can follow that same activity through Live Monitor, then open a connection in Flagged Flows to see its endpoints, port, and volume. The critical, medium, and secured bands here are rule-based triage of observed flows; they are not the model’s predictions.

For those, I move to Threat Forecast. The risk curve now extends beyond the observed windows, with coarse attack-stage and uncertainty estimates alongside it. Attack Graph restores the host-to-host context, while Benchmark shows the saved held-out evaluation. But a forecast matters most when it changes a decision. In Parallel Futures, I compare a simulated rate limit with the no-action baseline on copies of the graph. The predicted risk moves slightly, and nothing is silently enforced on the real network.

Before I share the case, I run the local validation check. It freezes the forecast and records the sandbox’s actual HTTP responses and hashes. I can also ask the offline assistant how many flows this case contains. Both answers stay tied to what the app actually observed. In Reports, I encrypt the incident brief, choose where to save it, and keep the one-time key separate. With that key, the recipient can open the encrypted JSON inside CYBERMIND and download a readable report.

The architecture connects this entire journey. In Tier One, ingestion preserves the capture’s provenance, normalization produces canonical flows, rolling windows build communication graphs, and a separate guard triages observed traffic. Tier Two is the pinned `best.pt` model: GATv2 encodes each graph, a temporal Transformer reads the sequence, latent dynamics project future states, and the prediction heads estimate risk and coarse stage. Tier Three turns those forecasts into the Command Centre, counterfactual comparisons, defence suggestions, and case-grounded questions. Tier Four records local sandbox evidence and protects reports with AES-256-GCM; decryption happens in the app with the separately held key. CYBERMIND runs offline on Windows through its desktop application and on Linux through the Docker launcher. It gives an analyst something more useful than a retrospective alert: an evidence-linked view of what may happen next.”

## Architecture graphic used in the final shot

![CYBERMIND four-tier architecture](architecture_diagram.jpeg)

**Production and accuracy notes (not spoken):** Use the manually selected SSH brute-force flow CSV for the filmed model forecast; it produced a high-risk forecast in the September 30 preflight. The Botnet Ares sample did not produce a corresponding high-risk model forecast. Capture actual application results; do not replace failed or unavailable controls with mock outcomes or promise a particular risk reduction. A raw PCAP has no attack ground-truth labels, so its individual flows can correctly show *Unassessed* even while graph-window forecasting runs. The model's stage mapping is a research proxy, not independently verified stage truth. The built-in local sandbox check records target behaviour; it does not establish attack-stage truth or retrain `best.pt`. The optional Strix-controlled scan is not part of this demonstrated path. The graphic’s “Authenticated Decrypt Desk” means possession of the separate report key in the current app; there is no recipient-identity verification. Do not show the key on camera. Treat the runtime as offline-capable rather than asserting an independently certified air gap.
