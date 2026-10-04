# Repository setup verification — 5 October 2026

- Compared the contents of 1,857 tracked files. Found 83 identical-content groups of at least 128 bytes; consolidated 242 redundant generated research outputs and copied documents/notebooks.
- Retained 31 groups needed by independent training and Docker import/build contexts or distinct dated verification snapshots. Empty/small package initializers and structural configuration files are not disposable copies.
- `REPOSITORY_DUPLICATE_AUDIT.json` maps removed files to canonical originals. Recovery copies are outside the tracked repository in `tmp/duplicate_cleanup_2026-10-05/`.
- One current runnable release ZIP remains. The separate September source/training submission has a different purpose and is not an alternate app launcher.
- Windows entry point: `CYBERMIND/START_WINDOWS.cmd`. Linux entry point: `sh CYBERMIND/START_LINUX.sh`.
- Windows preparation was tested against the complete current archive: SHA-256 verified, archive extracted, EXE/UI/Compose/image files present. Cached preparation also passed without extraction.
- Linux launcher scripts passed shell syntax checks. Launching on a Linux host was not tested.
- Preparation handles Git LFS pointer-only downloads by fetching the pinned release archive from the repository and verifying its hash. The network-download branch was not exercised: this checkout already contains the complete archive. It requires the new commit/LFS objects to be published before a new remote clone/ZIP can retrieve this release.
- Subsequent launches use the verified `.runtime/` directory, which is ignored by Git. Generated caches, earlier recordings and recovery copies are also ignored.
- A clean ZIP generated from the committed repository contained no `.runtime/`, `tmp/` or original recording-workspace entries. Its complete release and launcher files were extracted into a separate directory; Windows preparation verified and extracted the bundled app successfully there.
- Linux shell launchers are explicitly stored with LF line endings for portable checkout and ZIP extraction.
- Docker is a host prerequisite. The core application and model are bundled, and GPU/CUDA is not required.

No runtime Python package or model source was removed merely because its bytes matched the separate training context.
