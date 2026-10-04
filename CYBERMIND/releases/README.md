# CYBERMIND releases

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
