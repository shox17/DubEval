# Roadmap

DubEval is a **general dubbing evaluator**: any original video and its dub, from any service (Perso, ElevenLabs,
HeyGen, Rask AI, Deepdub, ...) or from human voice actors. It checks dubs and never makes them.

It has been a public beta since October 2026, with an installer for Windows and, since 0.1.7, an app for Macs with Apple silicon. This page has no dates, and the order can
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
- **Meaning:** a numbers check on every line and a line-by-line translation check with your own Claude, Gemini or
  ChatGPT key, or a local model. Human dubs may adapt the script. (An offline similarity screen was tried and removed in
  0.1.8: it found about 1 in 4 of the errors a translation checker finds.)
- **Review:** a verdict, synced players, a timeline with every problem, real problem / false alarm votes and exports,
  including side-by-side clips of each problem.
- **Quality score:** since 0.1.8, a score out of 100 beside the verdict, with published weights and the points each check
  lost. It never replaces the verdict, and it is marked provisional, or left out, when too little could be measured.
- **Working in the app:** evaluations wait in line and run one at a time, with progress on the taskbar or Dock icon, the
  time left, and a notification when one is done.
- **Usage stats:** small counts of what happens in the app, off unless you say yes ([what is sent](privacy.md)).
- **Comparison:** ranks 2 to 8 dubs of one video with a fixed, printed rule, and says when first place isn't ready to
  deliver.
- **History:** pass rate over time, language pairs and the most frequent problems.
- **Desktop app:** a Windows installer with the main models inside, optional downloads and updates from inside the app.
  Since 0.1.6 the installer is signed by ESTsoft Corp., and the app installs only updates signed the same way.
- **Mac app:** since 0.1.7, for Apple silicon, signed with ESTsoft's Apple Developer ID and notarized by Apple, with the
  same updates.
- **Beyond the app:** command line, batch checks of many links and a REST API.
- **Lip sync in the verdict:** an optional download that finds a sound delay and tells a lip-synced dub from a
  plain one; 90% of moments lined up is Good, 30% or less Poor.
- **First validation:** planted problems and one person's grades on real dubs ([results](validation.md)).

## Now: proving the verdicts
A check is only useful if people can trust it, so this comes first.

1. **More graded dubs:** a second reviewer, and more dubs in languages other than Korean. Today's agreement rests on one
   person and 39 dubs (a second round of 19, Korean and Russian from several services, was graded in November), and
   only English → Korean has more than a few.
2. **Human dubs:** none of the graded dubs is a voice-actor dub yet. Test real ones and fix what raises false alarms.
3. **Calibration:** many bands are still first guesses, and some were set with a different speech recognizer. Check them
   on the graded dubs, on the CPU too, then settle the default speech model. The quality score's weights are reasoned,
   not measured: check them against the graded dubs too.
4. **Repeatable translation reviews:** the same transcripts can get a different verdict from run to run. Measure how
   often, then reduce it.

## Next: fewer blind spots
- **Less common languages:** speech recognition reads some of them poorly (a real Uzbek dub was heard as Kazakh), and
  the line-level checks then can't run.
- **Sounds it misses:** hum, buzz, crackle, noise shorter than 1.5 seconds and a muffled voice.
- **Lip-sync bands from graded dubs:** the 90% / 30% bands were set before any graded lip-synced dubs; check them
  against some.
- **Voice similarity checked by ear:** its bands come from 10 real dubs, and only the two "another voice" results have
  been listened to; nobody has checked the "same voice" ones.
- **The Docker image:** it is included but not tested yet.

## Under consideration
Ideas, not commitments.

- A sample evaluation in the app, so you can see a result before using your own videos.
- Apps for Linux and Intel Macs, which run from source today.
- A second look at close calls before a verdict is given.
- An optional switch that separates voices from background music.
- Pronunciation and fluency checks.
