# Local offline verification

This check runs independently of Codex, saves local logs, and never changes network settings. It does not rebuild or export the image. Keep the ZIP unchanged.

1. Keep Docker Desktop running with its Linux engine. Close old CYBERMIND desktop windows so they do not keep polling a port from a prior launch.
2. Open PowerShell in the repository root while still online. The script's preflight has already passed on this machine.
3. Disconnect Wi-Fi manually and unplug any Ethernet connection. Leave them disconnected until the script prints its result.
4. Run:

```powershell
& .\CYBERMIND\tools\test_machine_offline_release.ps1
```

5. Allow several minutes for PCAP import and all four actual sandbox probe/approval/retest sequences. The script stops only the existing release container after checking its image ID, launches CYBERMIND.exe from a fresh ZIP extraction, then tests stop/relaunch and persisted validation records. It preserves named volumes and writes progress to the terminal.
6. Wait for `RESULT:` and `Logs saved to:`. Reconnect Wi-Fi. Send the result directory path in this chat so the logs can be inspected.

Results are written under `tmp/release_2026-10-04/offline_<timestamp>/`: commands.txt, summary.json, network-samples.jsonl, api-results.json, records-before-stop.json, records-after-relaunch.json, and the fresh extracted release. A physical adapter reconnecting during the test invalidates the network-off result. Adapter-query failures also fail that proof.

This script verifies archive integrity, desktop launcher/API startup, actual bundled PCAP import, forecasting, Parallel Futures, local validation, and all four built-in lab loops while physical network connections are disconnected. It does not prove visual UI correctness or report save/decryption; those remain separate checks. The desktop opening and named-volume persistence were previously tested separately. The updated harness adds start-from-stopped-container and persistence checks; those additions have not yet been run with the network disconnected.

If PowerShell refuses to run the script under your organization's policy, do not bypass that policy. Report the exact error. If adapter status cannot be queried, report that error rather than accepting the run as offline.

The built-in lab is an HTTP sandbox analogue. It does not test external machines or execute the optional external Strix CLI.
