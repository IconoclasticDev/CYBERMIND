# CIC-IDS2018 risk-flag demo

Use `releases/CYBERMIND/demo/ssh_bruteforce_sample.csv` from the portable workspace. SHA-256: `e8d589ece9663d1fd8a82277a2c9fe8f5bda20ece855e9a94af9642a0f60dd02`. Its 1,200 rows are real CIC-IDS2018 flows selected from the February 14 SSH-BruteForce interval; the source PCAP hash and selection are recorded in `examples/test_cases/provenance.json`. The CSV itself is unchanged.

Import it via **Upload PCAP / CSV**, then open **Flagged-Flows Risk Telemetry Table**. An isolated API upload with previous traffic cleared produced 118 critical, 5 medium, and 127 benign/secured hints among the latest 250 flows. The 10-second SSH attempt-count rule marks early attempts medium and sustained bursts critical; benign flows remain secured. These are rule-based, source-label-aware **triage hints**, not per-flow predictions from `best.pt`.

The separate Threat Forecast uses the actual `best.pt` world model on graph windows. In the isolated run, the import generated a Reconnaissance horizon forecast with risk 0.665; a prior native UI test reported a different horizon risk because the displayed horizon/session differed. Present the live value shown by the app, not a fixed promised score. A single selected attack interval is a demonstration, not a held-out accuracy measurement.

Raw PCAP uploads have no embedded flow ground-truth labels. Their risk-table entries correctly remain unassessed, even if the graph-window model generates a high-risk forecast. The verified February 28 PCAP is useful for demonstrating raw-file ingestion and forecasting, but use the labeled SSH CSV for the three risk-flag categories.
