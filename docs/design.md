# Design notes

Why DubEval measures things the way it does: the choices that were tested, the ones that were rejected, and why.
For how each measure works and its bands, see [metrics.md](metrics.md); for the modules, [architecture.md](architecture.md).

## Principles
- **Explain every result.** Each measure carries a level (Good / Check / Poor), a plain explanation, and the
  thresholds it was graded with, so a saved report explains itself without the tool.
- **No single 0–100 score (for now).** Weights between unrelated measures would be arbitrary. The verdict is a rule:
  any Poor → Poor; otherwise any Check → Needs review; otherwise Good. Informational and not-measured items never
  count, and each not-measured item says why. When DubEval isn't sure of its own measurement (little or unclear
  speech, a replaced background, words it couldn't recognize), it says so and doesn't let that measurement decide
  (metrics.md §6).
- **`None` means "not measured".** No sentinel numbers.
- **Never fail a run because of an optional check.** A translation review that can't run becomes "not measured"
  with the reason.
- **Repeatable.** The same dub always gets the same scores (see below), so a changed report means the dub or the
  tool changed, not chance.
- **Calibrate with evidence.** Thresholds change only on reviewer votes and labelled batches, never on one example.

## Repeatable speech recognition
Whisper falls back to random sampling when it is unsure, so the same dub gave different transcripts from run to run
(one dub's speech timing read 49% in one run and 56% in the next). `transcribe` now seeds that sampling inside the
call, and two uncached runs of the same dubs match exactly. Cached results carry `CACHE_VERSION`, so results made
before a change are recomputed.

## Voice quality: DNSMOS, compared with the original
- **Chosen:** DNSMOS P.835 (a 1.1 MB ONNX model; about 4 s per minute of audio on a CPU). The dub is scored
  **against the original at the same moments**, never in absolute terms: background music lowers both tracks'
  scores alike.
- **At the same volume.** The model's scores move with volume alone, so a copy only 3 dB quieter could be flagged as a
  worse voice. The dub's window is brought to the original window's volume before it's scored; volume has its own checks.
- **Not where the original is too noisy.** Scores below 1.6 jump with any small change, so a stretch where the original
  scores that low isn't held against the dub. **Rejected:** applying this to the whole video. It also dropped simulated
  robotic voices in clean stretches of noisy videos (flagged on 7 of 17 dubs, against 9 of 17).
- **Rejected: UTMOS.** It rated clean synthetic speech well (3.9) but scored every real recording 1.2–1.5, even
  the originals and even after separating the voice from the music, so it could not tell a good dub from a bad one.
  Lesson: test any speech model on real dubs before relying on it.
- **Validated** by simulated damage on two real dubs: robotic (quantised) and clipped stretches were flagged in the
  right place; clean dubs stayed inside the bands. **Blind spot:** a muffled (low-passed) voice barely changes any
  score.

## Voice similarity: only on clean lines
- WeSpeaker ResNet34 (ONNX, downloaded once and checked against a pinned SHA-256), with a NumPy filterbank so
  there is no torchaudio dependency.
- Measured only on lines whose original background is quiet: music blurs voice fingerprints (on a film, even one
  actor's own lines scored below 0.45 against each other). On music-heavy videos it is honestly "not measured".
- Good or Check, never Poor: a different voice can be deliberate.
- **Rejected for now: pitch matching.** It tracked the music instead of the voice.

## Voice/music separation: measured, deferred
Separating the vocals with Demucs before transcription raised speech-timing overlap by 1.4 and 6.1 points on two
real dubs with music, and removed a false language guess caused by noise, at about five times the evaluation time
on a laptop. It was deferred because of a torchaudio version conflict, and an optional switch is under consideration
(see [roadmap.md](roadmap.md)).

## Translation check
- An LLM compares the two timestamped transcripts for meaning, omissions, additions, names and numbers.
- It reads **transcripts, not audio**, so a misheard word can look like a translation error. Issues the model marks
  as probable recognition errors never make the dub Poor, but a line it scores very low (4 or under) is Check: the
  model can't tell a mishearing from a real error there, so a person listens (a reversed meaning marked "maybe
  misheard" once vanished from the report).
- Results are cached per input (transcripts, languages, provider, model, prompt and schema), and failures are retried.
- Provider outages are expected (Gemini often returns "high demand"), so the judge retries and falls back across
  models before reporting "busy, try again".

## Lip movement: informational only
A heuristic (mouth opening against loudness, compared with the original). On an in-sync sample the original itself
scored −0.20, so the number is not reliable. It is shown for information and never changes the verdict. The optional
lip-sync check, an audio-visual model, replaces it when downloaded, and that check counts in the verdict: 90% of
moments lined up is Good, 30% or less Poor (the owner's decision of 2026-11-10). The bands rest on one tested real dub
and should be checked against graded lip-synced dubs (see [roadmap.md](roadmap.md)).

## Timing moments: confirmed by a voice detector
Timing moments come from recognized word timings, and a small change anywhere in a file can shift those all over it,
so moments appeared far from anything that changed. A voice detector only looks at the moment itself, so it now has to
agree that one track speaks and the other doesn't.
- **Fine settings, on purpose.** The detector's defaults ignore silences under 2 s and pad speech by 0.4 s. The first
  version used them: the known-problem test looked excellent, because its planted silences are 3 s or longer, but it
  removed short gaps a person had voted real. Keep gaps of 0.1 s, and check any change here against the reviewer votes
  as well as the test.
- **The overlap score stays on the words.** It grades the dub as a whole, so this changes the listed moments, not the
  verdict.
- **Silences without words.** Where a dub's words can't be read, the detector alone finds silences. It counts the
  original's speech inside the dub's silence: looking for stretches of "original voiced, dub not" missed planted
  silences, because the original's own pauses between phrases (0.3-0.45 s) cut them into pieces too short to flag.

## Line length: confirmed by nothing, skipped over music
The voice detector that fixed timing moments doesn't help here. It mostly agrees with the words on real dubs, so those
lines really are that different, and the settings that removed false alarms also removed a line a person voted real. Most
line-length false alarms came from one mostly-music dub, where word timings aren't reliable, so line length simply isn't
graded there. DubEval already says it isn't sure of such a dub.

## Meaning similarity: the cutoff stays
Lowering the 0.60 cutoff looks like the way to cut its false alarms, and it would be a mistake: at 0.50 it removes 13 of 19
false alarms but also 5 of the 6 flags Gemini agrees with. Most of those false alarms come from recognition hearing a line
differently from run to run, not from a bad cutoff. Only the mostly-music case had a clean fix.

## Noise: a floor that fills, not a voice score
DNSMOS rates 9 s windows and normal dubs dip as much as a 4 s burst, so a lower threshold only brought back false alarms
(it caught 1 of 15 planted bursts). Measuring the spectrum's floor against the dub's own usual level separates them
cleanly and needs no model. A second signal could have caught about half of the hum cases, but those were invented for the
test, so it isn't worth the extra code until a real dub shows the need.

## Known limits
- Speech-timing and pace bands were calibrated on one real EN→KO dub (81–82% overlap, 5.8 characters per second).
- Interval thresholds (long silence 2/4 s, loudness jump 10/16 dB, wrong language: original's 50/80%, other 80/95%)
  are first guesses checked on a sample only. The per-window language check needs about 3 s of speech per 10 s window.
- Voice-similarity bands come from synthetic voices (same voice 0.80–0.87 across languages; different voices median
  0.13, max 0.57) and need real cloned dubs to confirm.
