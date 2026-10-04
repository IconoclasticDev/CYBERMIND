# CYBERMIND releases

## Progress for judge review

| Version | Progress | Files |
|---|---|---|
| 26 September 2026 | Initial SIH source/training submission, selected checkpoint, benchmark evidence and analyst console. | [Submission ZIP](CYBERMIND_SIH_SUBMISSION_2026-09-26.zip) and its manifest. |
| 4 October 2026 release, refreshed 5 October | Windows desktop launcher, complete saved Docker image, Linux launcher, upload-driven UI, local sandbox checks and in-app encrypted reporting/decryption. UI refresh corrects Benign filtering, Medium colors and forecast/defence labels. | [Current offline application ZIP](CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip) and [integrity manifest](CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.manifest.json). |
| 5 October 2026 setup refinement | One-click Windows/Linux preparation, archive verification and a cleaned application source/build context. | `../START_WINDOWS.cmd`, `../START_LINUX.sh` and `../CYBERMIND_REAL/`. |

The latest ZIP retains its dated release name and is the current runnable version.
Older intermediate development can be inspected in Git history; it is not copied
into additional runtime bundles. The latest ZIP's SHA-256 and complete ZIP integrity
were checked again during this repository cleanup. Linux launch has not been tested
on a Linux host.

## Current runnable application

Download `CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04.zip`, verify its SHA-256 against the adjacent manifest, and extract it. Keep the extracted folder intact.

- Windows: start Docker Desktop, then double-click `CYBERMIND.exe`.
- Linux x86-64: install Docker Engine and Compose, then run `sh launch_linux.sh`.
- Includes the desktop launcher, complete offline Docker image, pinned `best.pt`, backend, current shared UI, in-app encryption/decryption, built-in sandbox checks and launch/stop scripts.
- PCAP/CSV inputs are selected manually. The compiled `ui/` directory is shared by desktop and Linux Docker through Compose.

SHA-256: `1501067ff49208cbe1ca15e72bbef8a67f43c661a1cee9609d3e4eb7eb541e22`

The current UI fixes the Benign flow filter, uses orange for Medium hints and separates graph-window risk from HTTP defence evidence. External autonomous Strix requires a separately configured CLI and LLM provider. No local LLM is bundled.

See `../README.md` for the detailed application guide and `../deliverables/release_checks_2026-10-04/` for verification records. The refreshed ZIP was integrity-checked and the running Docker application was healthy with its model on CPU. The Linux launcher was not tested on a Linux host; the earlier full-machine offline test applies to the base image, not a repeated network-off test of this UI refresh.

## Source/training submission

`CYBERMIND_SIH_SUBMISSION_2026-09-26.zip` is a distinct source/training evidence package. It is retained with its manifest and package guide; it is not the current runnable application.

Superseded September desktop and October Attack Lab copies were removed from this folder. Local recoverable copies remain outside the tracked project in `tmp/retired_release_copies_2026-10-05/`.
