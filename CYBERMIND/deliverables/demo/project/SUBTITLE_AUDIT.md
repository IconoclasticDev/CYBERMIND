# Subtitle audit — 5 October 2026

Reviewed every subtitle in the edit decision list against the supplied narration transcript (timestamps divided by 0.9 for the tempo change) and actual recorded footage. Reviewed 30 composition snapshots covering each scene plus caption boundaries.

- Opening caption lasts exactly 0–3 seconds. It describes the local offline release; it does not independently establish that the machine's Wi-Fi was disabled.
- Ending technical approach slide has no subtitle overlay.
- Narrated benchmark caption now says F1 98.51% and FPR 0.57%. The recorded benchmark panel shows F1 98.49% and FPR 0.56%; its saved values were not altered. The caption explicitly identifies its values as narrated rather than claiming they are the panel's displayed results.
- PCAP picker shot now starts at source second 30, when the native picker is actually visible. Previously its caption preceded the dialog.
- Flow triage captions identify the labeled CIC-IDS2018 CSV case. They do not imply that unlabeled PCAP flows have dataset labels or that flow hints are model forecasts.
- Parallel Futures retains the recorded 100 → 78 simulated comparison; it is identified as simulation for analyst review.
- Strix Lab captions describe the built-in bounded sandbox probe, eight accepted requests and eight blocked repeat requests. They do not claim external autonomous Strix execution, model retraining or guaranteed forecast reduction.
- Local validation captions distinguish HTTP/SHA-256 sandbox evidence from forecasting accuracy.
- Report captions describe actual encryption, save-location selection, ciphertext, separate key, readable JSON and wrong-key rejection. No narration was added or modified.
- Short scenes have shorter captions, including Attack Graph, successful ingestion, ciphertext and readable report preview. Styling remains consistent with the existing caption rail.

The transcript is an automatic transcription with recognition errors, so it is a timing reference rather than an authoritative replacement for the supplied WAV. The benchmark correction follows the user's explicit confirmation of the spoken FPR.

Duration remains 108 seconds, 1920×1080 at 30 fps. All previous renders are retained; the audited export is `renders/CYBERMIND_Demo_Final_Subtitles_Checked.mp4`.
