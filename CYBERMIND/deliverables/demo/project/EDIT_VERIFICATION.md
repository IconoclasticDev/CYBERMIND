# Demo edit verification

- Runtime: 108 seconds; 1920 × 1080; 30 fps.
- Narration: only the supplied `cybermind new 2.wav`, slowed to 90% with pitch-preserving `atempo`.
- Application scenes: actual desktop recordings, with waiting trimmed. No UI screenshots are used as video scenes.
- PCAP workflow: recorded Upload button and native picker, analyst-selected file, recorded Ingest action and actual success response.
- Built-in sandbox: eight accepted requests before defence; zero accepted and eight blocked after analyst-approved defence. External autonomous Strix is not claimed.
- Local validator: newly recorded HTTP responses and full SHA-256 response hashes beside a frozen forecast.
- Reports: real save dialog, downloaded encrypted JSON in Notepad, successful in-app decryption, and deliberate wrong-key rejection. The valid report key stays masked.
- Current displayed benchmark: F1 98.49%, FPR 0.56%. Caption uses these actual values; the provided narration differs slightly.
- Capture excludes ChatGPT/Codex and the taskbar.
- Motion: consistent full-desktop framing with one shared 2% focus, held through the application sequence. No per-shot zoom resets or changing crops. Dissolves occur only at the opening slide boundaries and the final architecture slide.

The supplied narration is preserved in full at the user's request, including “Wi-Fi is off.” The adapter was Up during these recordings; this footage demonstrates local processing, and does not itself verify a disconnected machine. Physical offline testing is documented separately in the release verification. The video remains an edited live demonstration with waits trimmed, rather than an unbroken take.

## Flow hints and Strix clarification — 5 October

Critical, Medium and Benign filters were recorded live using the labeled CIC-IDS2018 SSH CSV: 118 Critical, 5 Medium and 127 Benign in the displayed 250-flow buffer. This is a separate CSV case, not classification of the unlabeled PCAP. The Benign filter now includes backend LOW-band flows and Medium bars use orange. Source and shared desktop/Docker release UI were rebuilt and checked. Existing ZIP archives have not been refreshed by this edit.

Strix footage retains the actual 8 accepted → 8 blocked result and actual 39.2% forecast. Captions distinguish HTTP defence effectiveness from future graph-window risk, which is not guaranteed to decrease after blocking. The current app labels are Graph Risk Forecast and Lower forecast risk, with an explicit explanation. No forecast values were altered.

Hyperframes validation: zero lint, runtime, layout and motion issues; four contrast checks passed. Visual snapshots at 21, 23, 25 and 58 seconds confirm the replacement hints and defence caption. Duration remains 108 seconds.
