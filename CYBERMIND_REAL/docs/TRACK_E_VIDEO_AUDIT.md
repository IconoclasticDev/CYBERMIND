# Track E — Video audit

Completed `artifacts/track_e/video/CYBERMIND_demo.mp4`: an **80-second edited sequence of captured UI states**, with burned captions and no audio. It is not a continuous screen recording or an end-to-end live demonstration.

- [x] Inspect all supplied UI screenshots before editing.
- [x] Preserve source files; composite only resizing/letterboxing and caption bands.
- [x] Cover analyst workflow, architecture, observed graph and forecast, isolation comparison, interpretation limits and the next evidence gate.
- [x] State synthetic provenance at the start and throughout; retain the exact reviewed Phase 3 claim and neighboring-checkpoint limitation.
- [x] Show the actual unchanged isolation result: both baseline and probe return approximately 0.749606 risk. No beneficial intervention or causal effect is invented.
- [x] Encode H.264/yuv420p with fast-start MP4 at 1600×900, 24 fps, 80.0 seconds (under 120 seconds).
- [x] Decode every one of 1,920 output frames successfully and inspect decoded frames at 5, 25, 40, 50 and 70 seconds. Captions fit and remain readable; no caption overlays obscure the source screenshots.

Evidence: `artifacts/track_e/video/video_verification.json` includes source hashes, scene captions/durations, output hash and decoding metadata. Reproducible build script: `artifacts/track_e/video/build_walkthrough.py`. Decoded inspection frames and composed source frames are in `walkthrough_build/`.

SHA-256: `28356d582c8498a4778ab24a521ad0cbf0fc0b82cc4c47c72d0c7339a5a79c8e`.

The original isolation screenshot has a partially clipped heading and horizontally constrained UI table; these are capture limitations preserved as evidence. A separate actual table capture displays both risks and zero reductions. The video is silent and readable without audio. The deck's synthetic benchmark tie and pending real-data gate remain visible; this artifact does not certify current corpus readiness or authorize Phase 5.
