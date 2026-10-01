# Native CYBERMIND end-to-end test — 2026-09-29

Tested the running `releases/CYBERMIND/CYBERMIND.exe` process through its private loopback FastAPI server and bundled React UI, using headless Edge automation. The native window remained responsive. The loaded checkpoint was `best.pt`, SHA-256 `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39`.

## Demo files

| Input | Bytes | SHA-256 | UI upload | Parsed flows | Observation windows | Current model output | First four future stages |
| --- | ---: | --- | --- | ---: | ---: | --- | --- |
| `ctu_iot23_capture_9_1_only5000.pcap` | 551,929 | `a761dcd52ede71a0f9a60272964e7392c25d9b6805f29735de7852b85bcb6ab6` | HTTP 200; success visible | 3,838 | 8 | Initial Access, risk 0.9850 | Initial Access ×3, Reconnaissance |
| `botnet_ares_sample.csv` | 357,387 | `894373193896f80b848333a778762dcae63d4134b733b559fa605cbe8947df7b` | HTTP 200; success visible | 1,200 | 8 | Benign, risk 0.0677 | Benign ×4 |
| `ssh_bruteforce_sample.csv` | 390,090 | `e8d589ece9663d1fd8a82277a2c9fe8f5bda20ece855e9a94af9642a0f60dd02` | HTTP 200; success visible | 1,200 | 8 | Reconnaissance, risk 0.9974 | Reconnaissance ×4 |

All three imports used source timestamps and generated forecasts. No browser JavaScript errors occurred. The PCAP is CTU IoT-23, outside the CIC-IDS2018 checkpoint's training domain; its high-risk output does not establish accuracy. The Botnet CSV contains 1,139 Botnet Ares and 61 Benign flows, but its final two minutes contain only two Benign flows. The SSH CSV contains 601 SSH-BruteForce and 599 Benign flows, with both labels in the final minute. These are short demos, not a held-out evaluation.

The loaded `best.pt` is presented by the application as using an argmax stage decoder (`app/api/routes.py`); the model defaults to argmax unless CRF decoding is enabled in its configuration. In the CTU PCAP run, the displayed future stages step backward from Initial Access to Reconnaissance at the fourth horizon. This is a stage-consistency limitation of this checkpoint/output and another reason not to present the out-of-domain PCAP forecast as validated attack-sequence accuracy. The PCAP demonstrates raw-file ingestion; the CIC-IDS2018 SSH CSV gives the clearer in-domain high-risk visual demonstration.

## Workflow verification

- Threat Forecast page rendered the loaded model trajectory.
- Built-in local sandbox check returned HTTP 200 and `SANDBOX_RESPONSES_OBSERVED`; four checks returned 200, 401, 200, 200. This is a sandbox-response check, not independent model validation.
- Benchmark modal loaded its saved comparison.
- Floating data assistant answered a question about the current forecast.
- Encrypted incident brief downloaded, decrypted in the UI with its generated key, and downloaded again as readable JSON. The readable report named checkpoint version `cybermind-5324902ca017`.
- Strix controlled validation remained unavailable because its external CLI, target service, and LLM provider are not bundled.

Screenshots and machine-readable responses are in `runtime/e2e_native_demo/`. The bundled demo files are in `releases/CYBERMIND/demo/` next to the native EXE.
