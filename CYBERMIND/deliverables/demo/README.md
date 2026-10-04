# CYBERMIND demo

`CYBERMIND_demo.mp4` is the final 1:48 Full HD demo, with the checked captions and the user's narration. The opening caption lasts three seconds; the final architecture slide has no subtitles.

`project/` is its editable Hyperframes composition, including the exact cut clips, local fonts, slides and narration. It can render without the long original recording takes. Run its pinned npm scripts from that directory; Node.js, Hyperframes/Chrome and FFmpeg/FFprobe are required for authoring. They are not requirements for playing the MP4 or running the application release.

The subtitle audit is in `project/SUBTITLE_AUDIT.md`. Narrated benchmark values differ slightly from the recorded saved benchmark panel; the caption identifies them as narrated values.

The runnable Windows/Linux Docker bundle is in `../../releases/`. The MP4 itself is not the application.
