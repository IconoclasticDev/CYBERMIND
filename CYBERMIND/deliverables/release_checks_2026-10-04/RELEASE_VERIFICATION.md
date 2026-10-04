# CYBERMIND October 4 release verification — incomplete gates

Release: `CYBERMIND_DOCKER_DESKTOP_ATTACK_LAB_2026-10-04.zip`

ZIP SHA-256: `4eed0e3fe858afc6cc77a95dc62a010102f9ee09af7ee3fdce242a004e621eae`

Image archive SHA-256: `5e54f47055a09242ffc948996ba6562ffb396106f9f11c53131a9962c8aa2eee`

Image ID: `sha256:f9533395cf873173d95cfea93c97b7a6326ad50604c2b5325e485ba4eadf7809`

Pinned best.pt SHA-256: `5324902ca017e946af58b41fbd576561553d7c03b532b37ee9255f4a3677cf39`

## Current results

| Required check | Result | Evidence |
|---|---|---|
| One linux/amd64 build and one image export | PASS | `single-build.txt`; Docker build ID `cmkal04xpm6mda16ibpxm8m0q` |
| ZIP and extracted file integrity | PASS | Actual ZIP SHA-256 matched; all 20 entries in embedded release.manifest.json matched |
| ZIP-only startup from stopped container | PASS while physically disconnected | offline-relaunch-summary.json and offline-relaunch-commands.txt: actual stop, fresh extraction, local image load, EXE launch and API health |
| Desktop app opens | PASS | Computer-use observed CYBERMIND — Analyst Console and CPU model online |
| Demo PCAP import | PASS via real API | `clean-zip-api-results.json` |
| Forecast | PASS; accuracy not established | Same evidence; UI displayed forecast and confidence/OOD warnings |
| Parallel Futures | PASS via real API | Same evidence |
| Local validation HTTP codes and SHA-256 | PASS | Same evidence; desktop accessibility exposed health 200, auth 401, share 200, query 200 plus response hashes |
| SSH succeeded → approved → blocked | PASS | 12 succeeded, then 12 blocked; zero unreachable |
| SQL injection analogue | PASS | 8 succeeded, then 8 blocked; zero unreachable |
| SMB lateral analogue | PASS | 10 succeeded, then 10 blocked; zero unreachable |
| C2 beacon analogue | PASS | 15 succeeded, then 15 blocked; zero unreachable |
| Default Docker socket absent | PASS | Container inspect showed only named data-volume mount |
| no-new-privileges | PASS | Container inspect returned no-new-privileges:true |
| Published ports loopback, automatic selection | PASS | Fresh EXE chose 127.0.0.1:50661; relaunch chose 127.0.0.1:56574 |
| Stop preserves named volume and records | PASS; follow-up read after reconnecting | Earlier before/after evidence plus offline-relaunch-records-before-stop.json and offline-relaunch-records-after-relaunch-observed.json; unchanged local-599bc905b974 |
| Encrypt report download | PASS | Actual saved encrypted JSON in Downloads, 10374 bytes; hash and envelope fields in encrypted-report-file-evidence.json |
| Correct-key and wrong-key decryption | PASS, user-observed desktop UI | User screenshots show readable decrypted preview and altered-key Decryption failed on the same file |
| Physical network disconnected during release test | PASS | Original run: 238 samples; stopped-container run: 427 samples, all observable/disconnected, API checks PASS |
| Relaunch health and persistence confirmed before reconnecting | PASS | offline-final-summary.json and before/after records; unchanged local-48f38f36efce, new loopback port rediscovered |
| Linux launcher execution | NOT VERIFIED | Only docker-desktop WSL distribution available; its Docker CLI explicitly refuses use there. App container has Docker CLI but no Compose plugin |
| Git LFS and prepared commit | PASS: changes staged | git lfs ls-files lists new ZIP hash 4eed0e3fe8; no commit or push performed |

## Changes

| Files | Change |
|---|---|
| Main and merged compose files | Remove default socket/DOCKER_HOST; add no-new-privileges and pull_policy never; retain loopback ports |
| compose.strix.yaml overrides | Explicit opt-in Docker socket and risk comment for external Strix CLI |
| packaging/container_entrypoint.py | Starts actual loopback sandbox before API; handles shutdown and existing one-hour sandbox expiry |
| packaging/Dockerfile.release | Offline layer over verified existing release image; adds startup and corrected sandbox only |
| Merged Dockerfile | Full-source builds use same entrypoint |
| sandbox/target_app.py | Correct telemetry endpoint to /api/telemetry/events and tag sandbox source |
| Sandbox Compose files | pull_policy never |
| tools/verify_offline_release_api.py | Actual HTTP PCAP, forecast, counterfactual, validation and four-vector loop checks with evidence output |
| New release ZIP and external manifest | EXE, launch/stop scripts, PCAP/CSV demo files, socket-free Compose, opt-in override, image and fresh integrity manifests |
| README.md and releases/README.md | New release/hash/security/verified built-in lab usage; badge points to existing recommended setup anchor |
| .gitignore and .gitattributes | Admit new ZIP/manifest and designate ZIP for Git LFS |

## Limits and command evidence

The built-in lab uses actual responses from a deliberately vulnerable HTTP sandbox. It is not a real SSH/SMB server exploit and does not run the optional external Strix CLI. The external CLI and LLM provider remain unconfigured. Sandbox events are simulated, explicitly tagged, and do not establish checkpoint accuracy or retrain the model.

The base image preserves the existing UI, checkpoint and dependencies. The sandbox expires after one hour; restart the service for another session. Earlier release data volumes remain untouched.

The single build completed even though PowerShell's initial Tee-Object destination was incorrect. The build was not repeated. Its actual log was recovered with `docker buildx history logs cmkal04xpm6mda16ibpxm8m0q` and saved as single-build.txt.

Actual API requests, status codes, timings and result bodies are in the two evidence JSON files. Build output is in the build log. Every tool command and its actual output, including failed access, path and automation attempts, is visible in the task conversation; this document does not claim those failed attempts passed. Report save/decryption, startup from a stopped container while offline, offline persistence, and Linux execution remain unverified. The completed physical-network-off API test is recorded below.

Linux shell syntax checks: sh -n launch_linux.sh and sh -n stop_linux.sh both succeeded (exit 0). This is not a Linux launcher execution test.

A local network-off test harness is now available in CYBERMIND/tools/test_machine_offline_release.ps1. PowerShell parser validation passed, PreflightOnly verified the actual ZIP SHA-256 and required local executables, and an actual online run was correctly rejected before launch. OFFLINE_TEST_INSTRUCTIONS.md explains how to run it without live chat monitoring. The original harness completed with physical adapters disconnected; its logs have now been collected. Added stopped-container startup and persistence checks remain unexecuted.
## Report save blocker

The native desktop Save report dialog was reached, but its filename control could not be targeted reliably by the automation helper. A subsequent browser attempt displayed saved/copied status, but its download event timed out and no matching report file was found. Actual save and correct/wrong-key decryption remain unverified. No encryption key has been added to release evidence.

## Collected offline run — October 4

The user completed the local harness at 03:02–03:06 IST. Independently inspected API evidence reports PASS, and all 238 physical-adapter samples show no connected adapter. Fresh extraction integrity, local image load, EXE invocation, health, real PCAP ingestion, forecasting, counterfactual comparison, local response validation and all four succeeded/approved/blocked sandbox loops passed. Evidence is preserved alongside this document as offline-summary.json, offline-api-results.json, offline-network-samples.jsonl and offline-commands.txt.

This supersedes the earlier missing offline-run evidence. The harness permits reuse of an existing container with the correct image; this run does not prove a cold container start. The encrypted report has still not appeared at the requested path, so actual save and correct/wrong-key in-app decryption remain unverified. Linux launcher runtime execution also remains unverified. Wi-Fi is now reconnected.


## Harness follow-up

The local harness now explicitly stops the matching release container before EXE startup, then stops/relaunches it after the API tests and compares the saved validation record. It preserves volumes and uses pull never. Parser validation passed; the additional runtime checks have not yet run offline. The previously collected offline results remain valid for their original scope.

## Offline retry failure and harness correction

The 03:17 IST retry verified extracted integrity, loaded the local image and stopped the existing container, then invoked CYBERMIND.exe. The first Compose port query raised a PowerShell terminating error because the service was not running yet. The harness exited before its startup deadline. This run is FAIL, preserved in offline-retry-summary.json, offline-retry-commands.txt and offline-retry-network-samples.jsonl. Startup polling now catches the transient stopped-service result and continues to the original deadline without restarting the app. Parser validation passed; the corrected offline runtime check is still pending.

## Offline stopped-container run and dynamic-port correction

The 03:33 IST run passed extracted integrity, startup from a stopped container, PCAP import, forecasting, Parallel Futures, local validation and all four lab loops. All 427 physical-adapter samples were observable and disconnected. The harness then stopped and relaunched the release, but retained the old URL 127.0.0.1:57917. Docker assigned 127.0.0.1:51754, so the script incorrectly timed out on the old port. Its overall result is preserved as FAIL, not rewritten.

Independent follow-up found the release running on 51754 with health ok and model available. Validation record local-599bc905b974 survived unchanged; the actual response is preserved as offline-relaunch-records-after-relaunch-observed.json. That follow-up was after reconnecting, so it proves persistence but does not itself prove a successful health request during the offline interval. The corrected harness rediscovers the loopback port during relaunch polling; parser validation passed. Report save and correct/wrong-key decryption remain unverified.

## Corrected full offline runtime check — PASS

The 03:52–03:57 IST run completed all harness checks: fresh extraction integrity, actual stopped-container startup through CYBERMIND.exe, PCAP ingestion, forecasting, Parallel Futures, local HTTP validation, all four lab loops, stop/relaunch health and unchanged persisted record local-48f38f36efce. Initial port 55938 changed to 62764 on relaunch and was correctly rediscovered. Independently audited API evidence reports PASS; all 269 physical-adapter samples are observable and disconnected. Full evidence is preserved in the offline-final files beside this report. Prior FAIL runs remain preserved as historical attempts. Actual encrypted report save and correct/wrong-key in-app decryption remain pending; the user is performing that check. Linux launcher execution remains unverified because no suitable Linux host is available.

## User-observed in-app decryption

The user confirmed that report decryption is working and supplied a screenshot showing the Decrypted incident brief preview with readable CYBERMIND Incident Brief JSON and the loaded CPU best.pt model metadata. This establishes user-observed correct-key decryption in the application. It does not establish wrong-key rejection; that check is still pending. No secret key is collected or stored as release evidence.

## Report encryption/decryption check — user-observed PASS

The actual encrypted file is present in Downloads and its SHA-256 is ddd81b968b61c540ff0fb526263476d80274bc6bcf01746ba7bebfb928533e38. Its envelope fields are format, version, encryption, key_encoding, iv and ciphertext; the key is excluded. The user's first screenshot showed readable in-app decryption. The next screenshot showed Decryption failed for the altered key on the same named file. Both UI checks are user-observed PASS. The key visible in the second screenshot is deliberately not copied into evidence or the repository. These UI tests were performed separately from the monitored network-disconnected harness; the report cryptography UI has not been independently observed with the physical network disconnected.
