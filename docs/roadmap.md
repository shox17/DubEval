# Roadmap

DubEval is a **general dubbing evaluator**: any original video and its dub, from any service (Perso, ElevenLabs,
HeyGen, Rask AI, Deepdub, ...) or from human voice actors. It checks dubs and never makes them.

It has been a public beta since October 2026, with an installer for Windows. This page has no dates, and the order can
change with what testing shows. What each version changed is in the
[releases](https://github.com/shox17/DubEval/releases).

## Done
- **Inputs:** two files, two links, a Perso share link or one file with two audio tracks, with optional subtitles
  (SRT/VTT).
- **Same video:** checks that both files are the same video, corrects a time shift, follows a differently cut dub or one
  whose picture drifts, reports the missing parts and refuses clearly different videos.
- **Timing:** line by line (length and lines running over) and across the video (length, speech overlap, pace).
- **Sound and voice:** loudness, silence, noise, distortion, dub language, clarity, voice quality, sound in sync and
  voice similarity (never for human dubs).
- **Meaning:** an offline similarity screen and numbers check on every line, then a line-by-line translation check with
  your own Claude, Gemini or ChatGPT key, or a local model. Human dubs may adapt the script.
- **Review:** a verdict, synced players, a timeline with every problem, real problem / false alarm votes and exports.
- **Usage stats:** small counts of what happens in the app, off unless you say yes ([what is sent](privacy.md)).
- **Comparison:** ranks 2 to 8 dubs of one video with a fixed, printed rule, and says when first place isn't ready to
  deliver.
- **History:** pass rate over time, language pairs and the most frequent problems.
- **Desktop app:** a Windows installer with the main models inside, optional downloads and updates from inside the app.
- **Beyond the app:** command line, batch checks of many links and a REST API.
- **Lip sync in the verdict:** an optional download that finds a sound delay and tells a lip-synced dub from a
  plain one; 90% of moments lined up is Good, 30% or less Poor.
- **First validation:** planted problems and one person's grades on real dubs ([results](validation.md)).

## Now: proving the verdicts
A check is only useful if people can trust it, so this comes first.

1. **More graded dubs:** a second reviewer, about 20 more English → Korean dubs, and more dubs in other languages.
   Today's agreement rests on one person and 20 dubs, and only English → Korean has more than a few.
2. **Human dubs:** none of the graded dubs is a voice-actor dub yet. Test real ones and fix what raises false alarms.
3. **Calibration:** many bands are still first guesses, and some were set with a different speech recognizer. Check them
   on the graded dubs, on the CPU too, then settle the default speech model.
4. **Repeatable translation reviews:** the same transcripts can get a different verdict from run to run. Measure how
   often, then reduce it.

## Next: fewer blind spots
- **Less common languages:** speech recognition reads some of them poorly (a real Uzbek dub was heard as Kazakh), and
  the line-level checks then can't run.
- **Sounds it misses:** hum, buzz, crackle, noise shorter than 1.5 seconds and a muffled voice.
- **Lip-sync bands from graded dubs:** the 90% / 30% bands were set before any graded lip-synced dubs; check them
  against some.
- **Voice similarity on real voice clones:** its bands come from synthetic voices.
- **The Docker image:** it is included but not tested yet.

## Under consideration
Ideas, not commitments.

- A sample evaluation in the app, so you can see a result before using your own videos.
- A code-signed installer, without the Windows warning.
- Installers for macOS and Linux, which run from source today.
- A second look at close calls before a verdict is given.
- An optional switch that separates voices from background music.
- Pronunciation and fluency checks.
- An overall score with published weights, shown next to the checks and never replacing them.
