# Roadmap

DubEval is moving from a Perso-only tool to a **general dubbing evaluator**: any original video and its dub, from
any service (Perso, ElevenLabs, HeyGen, Rask AI, Deepdub, ...) or from human voice actors.

## Now: the first version
In order:

1. **Engine foundation** (done): Python 3.11, faster-whisper, input from local files, links or a file with two
   audio tracks, optional subtitle files (SRT/VTT), input checks, a versioned report format
   (`schemas/report.schema.json`), and `dubeval evaluate --original A --dub B`. The Perso share link stays as one
   input option. Not yet verified: links to YouTube pages, macOS, Linux, the Docker image.
2. **Pairing and alignment** (done): check that the two files are the same video (motion, picture fingerprints and
   background sound), detect and correct a time shift (also part by part for a differently cut dub), report
   coverage and the missing parts, refuse clearly different videos, and match original segments with dub
   segments. Voice/background separation (Demucs) becomes an optional switch, added in Phase 3 or later
   (decided 2026-10-22: it is slow and changes transcripts, so it stays off by default).
3. **Length and timing** (done, bands to calibrate in Phase 5): line by line (each dub line's speaking time against
   the original's, ±15%; lines running into the next one), with every problem line as a timed interval, plus the
   whole-video measures (length, speech overlap, pace) and totals ("12 of 13 lines fit").
4. **Meaning** (done): an offline similarity screen on every line (BGE-M3), then a judge that reads both sides line
   by line (Claude, Gemini, or a local Qwen3 through Ollama) and flags omissions, additions, mistranslations, and
   names and numbers; human dubs may adapt the script (`--dub-type human`). Subtitles are used when given. Every
   dub in a benchmark should be judged by the same judge.
5. **Calibration** on a labelled test set of dubs from several services and human dubs, including new thresholds
   for faster-whisper (clarity, timing and pace were set with the original Whisper) and the choice of default model.
6. **Web interface** (first version done, `dubeval web`): choose files, paths or links; follow the stages; review
   with two synced players, a timeline with both waveforms, the lines and the problem intervals, a detail panel with
   both texts, and real problem / false alarm votes. Plain JavaScript, no build step, served on 127.0.0.1 with a
   per-launch link. Comparing 2-8 dubs of one original (recommendation, ranking, a review tab per dub; each dub with its own kind and language) is in too. The history page (trends, language pairs, frequent problems, reviewer votes) is in too. It replaced the Streamlit app (removed 2026-10-22), and it also takes Perso share links.
7. **Desktop app** for macOS and Windows (in progress): an Electron window around the web interface (`desktop/`).
   The proof starts the Python server on a free port and opens it with its launch link, no terminal. Still to come:
   bundling Python, the models and ffmpeg, installers, icon, signing and updates.
8. **Beta and v1.0.**

## Next
- Voice similarity (AI voice clones only; never for human dubs), speaker consistency, pronunciation, fluency.
- An overall score, with published weights, shown next to the per-measure scores.

## Last
- Lip sync with an audio-visual model. It comes last because video analysis is expensive.
