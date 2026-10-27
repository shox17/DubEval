# Design notes

Why DubEval measures things the way it does: the choices that were tested, the ones that were rejected, and why.
For how each measure works and its bands, see [metrics.md](metrics.md); for the modules, [architecture.md](architecture.md).

## Principles
- **Explain every result.** Each measure carries a level (Good / Check / Poor), a plain explanation, and the
  thresholds it was graded with, so a saved report explains itself without the tool.
- **No single 0–100 score (for now).** Weights between unrelated measures would be arbitrary. The verdict is a rule:
  any Poor → Poor; otherwise any Check → Needs review; otherwise Good. Informational and not-measured items never
  count, and each not-measured item says why.
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
on a laptop. It was deferred because of a torchaudio version conflict, and is planned for the general version
(see [roadmap.md](roadmap.md)).

## Translation check
- An LLM compares the two timestamped transcripts for meaning, omissions, additions, names and numbers.
- It reads **transcripts, not audio**, so a misheard word can look like a translation error. Issues the model marks
  as probable recognition errors are listed but never lower a level.
- Results are cached per input (transcripts, languages, provider, model, prompt and schema), and failures are retried.
- Provider outages are expected (Gemini often returns "high demand"), so the judge retries and falls back across
  models before reporting "busy, try again".

## Lip movement: informational only
A heuristic (mouth opening against loudness, compared with the original). On an in-sync sample the original itself
scored −0.20, so the number is not reliable. It is shown for information and never changes the verdict. A
SyncNet-style audio-visual model would replace it; it is the last item on the roadmap because video analysis is
expensive.

## Known limits
- Speech-timing and pace bands were calibrated on one real EN→KO dub (81–82% overlap, 5.8 characters per second).
- Interval thresholds (long silence 2/4 s, loudness jump 10/16 dB, wrong language: original's 50/80%, other 80/95%)
  are first guesses checked on a sample only. The per-window language check needs about 3 s of speech per 10 s window.
- Voice-similarity bands come from synthetic voices (same voice 0.80–0.87 across languages; different voices median
  0.13, max 0.57) and need real cloned dubs to confirm.
