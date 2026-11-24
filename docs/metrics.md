# Evaluation Metrics

This page explains how each score is produced (`dubeval/evaluate.py`), how to read it, and where it breaks down.
Reference numbers ("Sample") come from a real Perso EN→KO lip-sync dub of a 28.7 s talking-head clip, Whisper `small`. The default model is now `base`, which gave the same verdict and scores on this sample (82% vs 81% speech overlap, 4/5 meaning) with a 3× smaller download.

## 0. Same video, time shift and coverage (`pairing.py`)

Runs first, on both files, before anything else is measured.

**Evidence.** Each video is read as tiny grayscale frames (32×18) at up to 10 per second (fewer for long videos, at
most 6000 frames).
- *Motion*: how much each frame differs from the previous one (log, normalized, capped at ±4). Its rhythm (head
  turns, gestures, cuts) is distinctive even in a static talking-head shot. The two motion signals are
  cross-correlated window by window (8 s windows, 2 s apart, shifts up to ±60 s or half the shorter file); a window
  counts when its best correlation is at least 0.6 and beats the best shift more than 1 s away by 0.1. Neighbouring
  windows at the same shift form a *part*; where the dub jumps back in time between two parts, the frames in between
  are the part of the original that was cut (the split is placed where the motion fits best).
- *Pictures*: a 64-bit difference hash per frame; two frames match when at most 12 bits differ. At the chosen
  shift, the share of matching frames decides "same video", and runs of non-matching frames of at least 1 s are
  parts of the original missing from the dub (cut or replaced). Without usable motion, the hashes alone give the
  shift (and up to 5 parts for a differently cut dub).
- *A picture that drifts*: some dubs have their picture slowed down or sped up in places, so the shift keeps changing
  and no fixed shift fits. When the matching above finds under 90% of the original, DubEval looks for the path through the
  shifts (from 0 to the files' length difference, 2 s further) with the most matching frames. It's used if it finds at
  least 90% of the original and 10 points more. The dub's sound is then laid onto the original in parts with one shift
  each, split at the dub's quietest moments, so lines stay whole. A really cut dub has frames no path can find, so it's
  still reported as cut. In a still shot frames also match at the wrong time, so a path whose shift falls 2 s within 5 s is
  treated as a cut, not a drift. Following a drift skips bits of the dub's sound, so a drifting dub's speaking pace is
  measured on its own untouched sound; a recut dub's stays on the sound its words were heard in.
- *Sound*: the onset envelope of each audio track every 10 ms. When it correlates at least 0.15, it refines the
  picture's shift within ±0.3 s; with a file that has no picture, it decides alone (and never refuses).

Motion wins whenever it explains at least 60% of the original; otherwise the answer that finds more of the original
in the dub wins. **Correction:** shifts of 0.1 s or more are corrected by moving the dub's audio onto the original's
timeline (one shift), or by laying it part by part (a differently cut dub; missing parts stay silent), so every time
in the report is the original's.

| Measure | Good | Needs review | Poor |
|---|---|---|---|
| Same video (matching frames at the best shift, or coverage) | ≥ 60% | 25–60% | < 25% (the run stops unless `--allow-different-videos`) |
| Time shift | information only | | |
| Coverage (share of the original found in the dub) | ≥ 98% | 90–98% | < 90% |
| Sound in sync with the picture | under 0.3 s | 0.3–0.6 s | ≥ 0.6 s |

**Sound in sync with the picture** (`pairing.sound_sync`, graded by `report.sound_sync_level`): most dubs keep the
original's music and effects, so the dub's soundtrack lines up with the original's where its picture does. The
onset envelopes are searched ±2 s around the picture's shift; how far the best match lands from it is how late (+)
or early (−) the dub's sound is against its own picture. The picture's shift is only known to half the time
between the frames compared (0.1 s apart on a short video, 0.6 s on an hour-long one, since at most 6,000 frames are
compared), so that much of the gap is never counted: a long film whose sound is in step isn't called late. Not
measured on files under 15 s (a 7 s clip showed a stray 0.9 s match) or when the soundtracks match below 0.2 there
(the dub replaced the background), nor on a recut dub.
Validation: a dub's sound moved 1 s late was found at exactly +1.0 s in all 12 of 16 tune dubs where it was measured,
with every control within 0.24 s. A Needs review or Poor result is also a whole-dub "sound out of sync" problem interval.

Each missing part of at least 1 s is a "missing from the dub" problem interval: Needs review, Poor from 5 s (shorter slivers,
such as files differing in length by a frame, are never listed: `intervals.SLIVER_SEC`).

**Verified** on synthetic clips (aligned, shifted 2 s, 5 s cut out, unrelated) and on real PersoDub dubs: a dub
with 2.5 s added at the start measured +2.50 s (speech timing back to the untouched 90%); a dub with 40–45 s cut out
reported 95% coverage and the missing part at 40.1–45.1 s; an unrelated pair was refused; 7 untouched real pairs
were all "same video", no shift, 100% coverage. A real English → Korean dub whose picture drifted between 0 and 5.1 s went
from 77% to 100% coverage. **Limits:** a dub that is cropped, letterboxed or reframed (for
example 16:9 → 9:16) changes the hashes and may read as "unsure"; parts that are missing from a perfectly static
shot can only be found through the sound or speech timing.

## 1. Acoustics (`analyze_acoustics`)

Audio is decoded to 16 kHz mono with the bundled ffmpeg.

| Field | Definition | Read as | Sample |
|---|---|---|---|
| `duration_diff_sec` | dubbed − original | ≈ 0 for a time-aligned dub. Beyond ±20%, a warning is raised because the pair probably doesn't match | 0.00 |
| `rms_ratio` | mean RMS dub ÷ original | ≈ 1.0 means matched loudness. `null` if the original is silent | 1.00 |
| `*_volume_stability_pct` | `(1 − std/mean RMS)·100` | Higher is steadier. Useful as a comparison, not as an absolute | 60 → 63 |
| `*_silence_ratio` | 1 − non-silent time ÷ duration (`top_db=20`, relative to the clip's peak) | Music beds hide silence | 0.1% → 0.6% |

Whisper's fallback sampling is seeded (`WHISPER_SEED`). Even so, on a graphics card the same audio can give slightly different text between runs (`docs/validation.md`), so results are cached per file.

## 2. Script accuracy (`score_transcript`, only when you give a script)

Share links don't include a script, so this is scored only when you pass one on the command line (`--script` / `--script-file`). It isn't listed as "not measured" otherwise: it's an optional extra, not a gap.

1. Whisper transcribes the dub with `language=target` (`whisper_language` maps Perso's `fil` → `tl` and `jv` → `jw`). For Cebuano, Chichewa, Irish and Kyrgyz Whisper has no model, so it auto-detects and the run warns that the script scores are rough. The original is transcribed in the share project's source language, or with auto-detection when that is unknown (`detected_source_language`).
2. Both reference and hypothesis are normalized: NFKC, lowercase, punctuation and symbols removed, whitespace collapsed.
3. `wer` is word-level. `cer` is character-level with spaces removed, so spacing differences are not errors.
4. **Primary metric:** `cer` for `ko`, `ja`, `zh`, `th`, and `wer` otherwise. `error_rate` and `accuracy_pct = max(0, 1 − error_rate)·100` come from it.
5. An empty ground truth gives `null` scores. An empty transcript gives error 1.0.

**Why CER for Korean and Japanese:** Japanese has no spaces, so WER treats a whole sentence as a single "word". Korean spacing units are coarse and ASR spacing is inconsistent. For example, `소프트웨어 공학을` vs `소프트웨어공학을` is a 100% word error but a 0% character error.

**Reading it:** on a Korean dub of the sample, a correct dub scored about 60% (CER ≈ 0.4) against an independently written Korean script. That is **not** a 40% dubbing failure. The number mixes three things:
- **Paraphrase:** the dub's translation is valid but worded differently from your script (for example, `공부하고` vs `전공하고`).
- **ASR error:** Whisper mishears proper nouns (`인하대학교` → `이나데아크`).
- **Real dubbing errors.**

The highlighted diff under **What was said** shows which is which. For meaning rather than wording, use the translation check (§5). The default speech model is **automatic**: Whisper `large-v3-turbo` when it is downloaded (Settings → Models), otherwise `base`. Since 2026-11-15 a graphics card isn't needed for that: on a processor the large model takes 16-18 s per minute of sound against 5 for `base` on one 2025 laptop, and reads far more languages well (`docs/validation.md`). On 4 PersoDub EN→KO dubs scored against their exact dub scripts (2026-10-26), `large-v3-turbo` made a quarter to half fewer errors than `base` on natural Korean speech (8.3% and 2.9% of characters against 11.1% and 7.1%) at the same speed on a GPU; on lines mixing English words into Korean every recognizer did badly. SenseVoice-Small, NVIDIA Parakeet (English) and Whisper `large-v3` did no better, and all five heard "new cases" where the speaker meant "new tastes", which is why the translation check marks possible mishearings. `base` (fast, 145 MB): It mishears a few more words than `small`, which mostly shows up as extra "possible recognition error" items; for reporting-grade transcripts set `WHISPER_MODEL=small` or `medium`.

### Speech rate
Words per second (chars/s for ko/ja/zh/th) over *speaking time*, where speaking time is duration × (1 − silence ratio). Units differ between languages, so compare the dub against other dubs in the same language, not against the original.

### Loudness over time
The dBFS of each 0.25 s window, for both tracks. Peaks and gaps should line up. A shifted or stretched pattern shows timing drift that the single duration number hides.

## Score bands (audio and script)
| Measure | ✓ Good | ! Needs review | ✗ Poor |
|---|---|---|---|
| Length match: \|Δduration\| / original | ≤ 5% | ≤ 15% | above that |
| Matches your script: accuracy | ≥ 80% | ≥ 50% | below |
| Loudness match: dub vs original | within ±3 dB | within ±10 dB | beyond |
| Extra silence in the dub | ≤ 5 pts | ≤ 15 pts | above |
| Lip sync (with the download): moments that line up | ≥ 90% | between | ≤ 30% |

The script-free measures and their bands are in §4 and §5. The script bands are lenient on purpose, because paraphrases count as errors (§2).
The loudness band was 2 / 4 dB until 2026-11-01: a person graded a dub 5.1 dB off the original Good, and no dub they
graded Poor was more than 1.7 dB off. Poor moved from 6 to 10 dB on 2026-11-24 (owner's decision): a dub 6.6 dB louder,
Poor for that alone, was graded Needs review ([validation](validation.md)).

## 3. Lip sync

Measured automatically when the shared dub is lip-synced (`isLipSync`); skipped otherwise, and the report says why.
With the `lip_sync` download installed, the lip-sync check below runs and **counts in the verdict**: the share of
checked moments that line up is Good from 90%, Poor at 30% or less, Needs review between (`LIP_SYNC_PCT` in `report.py`,
the owner's decision of 2026-11-10; the check was tested on one real dub, so these bands aren't calibrated yet).
Not measured never counts. Without the download the lips aren't checked.

### The lip-sync check (`dubeval/lip_sync.py`, the `lip_sync` download)
1. **Model:** StableSyncNet from ByteDance's LatentSync 1.5 (`stable_syncnet.pt`, 1.6 GB, CreativeML OpenRAIL++-M),
   pinned to a Hugging Face revision and SHA-256, downloaded unchanged. DubEval ships only its two graphs
   (`dubeval/models/syncnet_*.onnx`, ~150 KB each, `tools/build_syncnet_onnx.py`); onnxruntime reads the weights
   straight out of the checkpoint.
2. **Moments:** separate 16-frame stretches (0.64 s at 25 fps) of the first 60 s where both tracks speak for ≥ 80%,
   spread evenly. A look at each one's middle frame drops those without a face in either video; at most **30** are
   scored, the same ones in both videos. Fewer than 8: not measured.
3. **Preparation, as LatentSync trains it:** 25 fps; the face aligned on three points (both eyebrow centres and the
   nose, from MediaPipe's landmarks where LatentSync uses InsightFace) to LatentSync's template with its smoothing,
   256×256, lower half, values in [-1, 1]; the sound as its mel spectrogram (16 kHz, 80 bands 55–7600 Hz, hop 200,
   pre-emphasis 0.97, [-4, 4]).
4. **Score:** the cosine similarity of the face and sound vectors, with the sound shifted −15…+15 frames (±0.6 s):
   every 3rd shift, then the best one's neighbours (a match stays high about 2 frames either side, so this finds the
   same peak). Each moment's best shift is kept.
5. **The dub's own timeline:** when the dub starts later or earlier than the original (pairing's shift), each
   moment is read in the dub that much later or earlier, picture and sound together, so the shift itself is never
   taken for lips out of sync. A dub cut differently (pairing's parts) has no one shift: not measured.
6. **Zero point:** the original's typical shift (the ±2-frame window holding the most moments, then their median),
   so a constant offset of the file or the model cancels out. If the original lines up in fewer than half its
   moments, its voice probably isn't the person on screen (a narrator): not measured.
7. **Reported:** how many moments line up (best shift within ±2 frames, ±0.08 s, of the zero point) in the dub and in
   the original. When most of the dub's moments agree on another shift at least 120 ms away (`LIP_OFFSET_MS`), the
   lips follow the speech but the sound is that late or early. A dub without lip sync lines up about 1 time in 6 by
   chance (5 of 31 shifts are within ±2 frames).
8. **Speed** (CPU): about 30 s for both videos; only the minute
   of sound the moments use is turned into a spectrogram. Both models run with busy-waiting off (`ort_session.cpu_session`);
   with it on they took each other's processor time and ran about 3× slower.

**Tested** (`docs/validation.md`, one real Perso EN→KO dub): the lip-synced dub lined up in 26 of 30 moments
(original 28), the same dub without lip sync in 6 of 30 (chance), and sound delays of 0.2 and 0.5 s added to the
original were measured as 0.20 and 0.48 s. A delay beyond the search (±0.6 s; 1 s was tried) shows as lips that
don't line up, with no offset: the sound-sync check (§1, ±2 s) is the one that measures those.

### The lip-movement estimate (removed 2026-11-13)

Until 2026-11-13, a dub checked without the download got a rough estimate in its place: how far the mouth was open
(MediaPipe face landmarks) against how loud the sound was, as one correlation. It was removed. On the sample video the
in-sync original scored −0.20 (56% face coverage) and the lip-synced dub −0.03, and on the first 5.5 s (99% face) every
variant tried stayed under 0.2: the number said nothing about sync, and a section headed "experimental" sat in every
report. Without the download the lips are now simply not checked: the row says so and where to get the download
(`r.lips.no_download`), and a result saved with the old estimate says it was removed instead of showing its number.
MediaPipe's face landmarker stays bundled: the lip-sync check uses it to find and align the face.

## 4. Script-free measures
Share links carry no script, so these measure the dub against the original directly.

### Which recognized lines count as speech (`keep_voiced`)
Speech recognition reads music and sound effects as words ("3몇", "하하하하") and adds lines that were never said
("See you next time", "한글자막 제공…"). Those lines change with any small change of the sound, and even between two
runs on the same sound, so every check built on the transcript moved with them. A voice detector (Silero, shipped
with faster-whisper; `asr.voice_activity`) runs on both tracks, and a line is kept only if it hears speech in at least
half of it (`VOICED_SHARE_OK`). Validation (`docs/validation.md`): on 20 test videos it kept every line of 16
talk-heavy tracks and removed all the invented lines; it also drops short shouts over loud effects and some singing
(about 1-2% of speech time), so a line it misses is kept when the other track's kept lines cover at least 30% of it
(`PARTNER_SHARE_OK`): dropped on one side only, a shouted line read to the translation check as a line added or left
out. Without faster-whisper installed, nothing is dropped.

### Speech the recognizer skipped (`fill_gaps`)
Long audio is recognized in 30 s chunks, and after loud music the recognizer can skip ahead past real lines (a real
Perso dub lost its first 15 s of lines; recognized on their own they came out word for word). Every stretch of at
least 1 s where the voice detector hears speech but the transcript covers less than 30% of it is recognized again on
its own, with 0.3 s either side, and its new lines are added (a line at least half inside one the transcript
already has is that line again, and isn't added twice). On that dub, speech-timing overlap went from 21% to 69%.

### Dub language (`detect_language`)
Whisper's language identification on the first 30 s of the dub. **Good** when it matches the target and Whisper is ≥ 50% sure, **Needs review** when it matches but Whisper is unsure, **Poor** when it's a different language. Catches the worst failure (wrong language, or the original voice left in).

### Voice clarity (`speech_clarity`)
Share of speech time in Whisper segments with `avg_logprob ≥ −1.0` (Whisper's own threshold for trusting a decode). Segments Whisper itself treats as silence (`no_speech_prob > 0.6` and `avg_logprob < −1.0`) are ignored, as are lines the voice detector hears no speech in (above); faster-whisper's large-v3-turbo reports `no_speech_prob` 0 for every line, so on it only the voice detector removes them. Good ≥ 90%, Needs review ≥ 70%. The unclear segments are listed with timestamps under *Things to check*. It's an intelligibility proxy that needs no script; ASR weaknesses on names and accents also lower it.

### Voice quality (`voice_quality.py`)
Does the dub's voice sound clean, or robotic and distorted? Microsoft's **DNSMOS P.835** (bundled ONNX model, CC BY 4.0) predicts listener scores (1–5) for the speech signal (SIG), the background (BAK) and the overall sound (OVRL) on ~9 s windows, every 2 s (widened on long videos to at most 120 windows). Only windows where **both tracks speak at least 3 s** are scored, on both tracks at the same moment, with the dub's window first brought to the original window's volume (the gain stops at full scale, so it never clips). A dub keeps the original's music and effects, so the comparison isolates the dub's own sound; absolute scores would mostly measure the music.

A window is **Needs review** when the dub's SIG is ≥ 0.6 below the original's or its OVRL is ≥ 0.5 below, **Poor** from 2.5 / 1.5 (1.0 / 0.9 until 2026-11-01: on the graded dubs, windows up to 2.2 / 1.2 below came from dubs a person graded Good or Needs review, and both reviewer votes on Poor windows were false alarms). The worst window sets the level, and flagged windows become `voice_quality` problem intervals. A stretch where the original itself scores below 1.6 isn't held against the dub: scores that low jump with any small change. Not measured when the two tracks never speak together long enough, or when the original averages below 1.6 over the video (too noisy to serve as reference).

**Why the same volume:** the model's scores move with volume alone, and volume has its own checks. A copy only 3 dB quieter moved a window by up to 1.14 on SIG and 0.64 on OVRL (95% of windows within 0.45 / 0.28), against 0.51 / 0.24 (0.16 / 0.13) at matched volume. Real damage isn't blunted: a simulated robotic voice drops the scores by the same amount either way, 0.66 SIG / 0.55 OVRL on average across 17 dubs (`docs/validation.md`).

**Why both scores:** in tests on two real EN→ES Perso dubs, a robotic (quantised) voice dropped SIG by ~0.9 but OVRL by only ~0.4, while clipping distortion dropped OVRL by ~0.7 but SIG by ~0.25 (the model books distortion under background). Clean dubs never fell more than 0.25 below the original (the Perso voices actually scored 0.3–0.4 above the film's recorded dialogue). **Blind spot:** a muffled (low-passed) voice barely changes any score.

**Why not UTMOS:** UTMOS22 (the usual TTS naturalness predictor) was tested first. It rates clean synthetic speech well (3.9) but collapses to ~1.2–1.5 on every real recording, including the originals and voices separated from the music with Demucs, so it can't tell a good dub from a bad one.

### Noise (`noise_envelope`, `intervals.noise_bursts`)
Does the dub fill with hiss or static the original doesn't have? Voices and music leave valleys in the spectrum, and noise
fills them. So DubEval follows the spectrum's floor above 1 kHz (the geometric mean of its power) and how flat the spectrum
is, each as a median over 1.5 s, every 0.25 s, against that track's usual level. It takes the dub's rise minus the
original's at the same moment, so a noisy scene in both cancels out.

**Needs review** when the floor rises at least 12 dB and the flatness at least 2 dB for at least 1.5 s (a louder passage rises
without getting flatter); otherwise **Good**, never Poor. Each stretch becomes a `noise` problem interval, except where the
sound clips, which is reported as distortion. On the tune dubs, planted bursts rose 15-39 dB; the highest rise on any clean
copy was 12.3 dB, and it never met both conditions for that long. Results: `docs/validation.md`.

**Blind spots:** hum, buzz and crackle, bursts under 1.5 s, and noise across the whole dub (there's no rise above its usual
level). It was tested on noise made for the test; no real dub has shown any yet. This isn't done with DNSMOS because it
scores 9 s windows, and normal dubs dip as much as a 4 s burst.

**With the voice-quality download: Audiobox Aesthetics.** DNSMOS was made for clean speech: over music its scores swing
by 2 points within one dub, an original with loud music scores too low to be a reference (8 of the 20 test dubs), and
it misses a muffled voice. With the download from Settings → Models (415 MB), Meta's **Audiobox Aesthetics** scores
the same stretches instead (`voice_quality.scorer()`). It was trained on listeners' ratings of speech, music and sound
together; its **production quality** (PQ, 1–10) is the score that grades, and its content-enjoyment score (CE) is a
second signal. A stretch is **Needs review** when the dub's PQ is 1.0 or more below the original's there, or 1.0 or
more below how this dub usually compares with the original (the median over its stretches), or its CE is 1.2 or more
below its usual; **Poor** from 2.5 on PQ (`VOICE_PQ_DROP`, `VOICE_CE_DROP` in `intervals.py`). There is no "too noisy"
floor. Set on 2026-11-13 from the 20 test dubs (`validation.md`): over 329 undamaged stretches the dub was never more
than 0.83 below the original or 0.8 below its own usual, and of 8 s of damage put into each dub the rule caught a
robotic voice on 20 of 20, a muffled one on 17, a clipped one on 17, with no undamaged stretch flagged. Poor is a
first guess: no real dub has reached it and nobody has labelled one. DubEval ships only the model's graph
(`models/audiobox_aesthetics.onnx`, 0.6 MB, `tools/build_audiobox_onnx.py`); the weights are Meta's own
`model.safetensors`, read where the download put it (the scores match PyTorch to 5 decimal places). It takes about
0.25 s per stretch on a laptop processor, about 20 s per minute of video (DNSMOS: 0.05 s per stretch). Every stretch
still gets DNSMOS's background score, which tells a replaced background (`report.sure_of`).

### Voice similarity (`speaker.py`)
Does the dub voice still sound like the original speaker? **WeSpeaker ResNet34-LM** (trained on VoxCeleb2's 5,994 speakers; ONNX, CC BY 4.0; 26.5 MB, downloaded once, pinned to a Hugging Face commit and SHA-256) turns speech into a 256-number voice fingerprint from 80-band Kaldi filterbanks (computed with numpy). Each original line of ≥ 2 s is compared with the dub **at the same moment** (Perso keeps the timing), which follows every character in a multi-speaker video without speaker detection. The level uses the median similarity: **40% or more is the same voice (Good), under 30% another voice, between them partly alike (both Needs review)**; never Poor, since a new voice can be a deliberate choice.

**How the number is trusted.** Some videos fool the model: on a film clip even the original's own lines were only 45% alike. So the measure also matches the original with itself: each original line against the other original line that sounds most like it (`original_self`, the median). A result under 40% is graded only when that is 60% or more (`VOICE_KNOWN`); otherwise the row says it can't tell on this video, with both numbers. A result of 40% or more is graded either way: two different people never scored that high. Bands (`VOICE_SAME`, `VOICE_DIFFERENT`) were set on 2026-11-13 from 10 real dubs and 363 line pairs taken from different videos (`validation.md`): cloned dubs scored 0.45–0.61, dubs with another voice 0.08–0.24, two different people under 0.25 in 99% of pairs (0.34 at most), and originals the model follows 0.72–0.85 against themselves. Until then only lines with a quiet background counted (DNSMOS background ≥ 3.0), which left 16 of 20 test dubs unmeasured, though the scores with the music in were the same as with the voice separated out.

**Different-voice intervals:** a line ≥ 0.2 below the dub's median similarity and below 0.65, in a dub whose median is ≥ 0.45 (it clones its speakers otherwise), is flagged `voice_change`: that line probably got another character's voice. Not on a video whose own speakers the model can't match (`original_self` under 60%). Tested: a similar female voice swapped onto one line (0.55 vs median 0.81) and a female voice on a male line (0.20) were both flagged; a good clone and a stock voice throughout flagged nothing.

### Speech timing (`speech_intervals`, `timing_alignment`)
1. Speech stretches come from Whisper word timings, merging gaps shorter than 0.3 s and dropping segments Whisper treats as silence. Word timings follow speech, not the music bed, which defeats energy-based voice detection on this kind of video.
2. Both tracks go on a 50 ms grid. `overlap_pct` is intersection over union of speaking time. Stretches of ≥ 0.5 s where only one track speaks become `mismatches` (`dub_only` / `original_only`, the 8 longest).
   A stretch counts only if a voice detector agrees (`_detector_agrees`, fine settings): the "silent" track speaks less than
   half of it (`MISMATCH_SILENT_VOICED_MAX`) and the "speaking" one at least 30% (`MISMATCH_SPEAKING_VOICED_MIN`). Word
   timings shift with any change anywhere in the file, while the detector only looks at that moment. The overlap score
   stays on the words, so this changes the listed moments, not the verdict.
3. Bands: Good ≥ 75%, Needs review ≥ 45% (Poor was below 55% until 2026-11-24: every graded dub at 47–54% was Needs review on timing to the reviewer, none Poor). **Calibration:** the real Perso EN→KO lip-sync dub of the sample scores **81%**, with two short dub-only spots. Languages differ in rhythm, so 100% isn't expected; these bands are a starting point from one sample and should be tuned on more dubs.
4. It depends on correct transcription: a dub in the wrong language gets distorted word timings (the language check flags that case separately).

### Line by line (`match_segments`, `line_timing`)
After pairing, every time is on the original's timeline. Original and dub segments are matched by time: segments
overlapping by at least 30% of the shorter one are linked, and linked segments form one *line* (a dub often splits
or merges sentences). Each line is measured from the first spoken word to the last on each side.

- **Line length:** the dub's speaking time against the original's. A line is off when it differs by more than ±15% **and** by at least 0.6 s
  (`report.line_off`); word timings move by about that much when the sound changes slightly, and validation found
  0.3 s let short lines flip between fitting and not (`docs/validation.md`). Lines shorter than 1 s
  on the original side are kept but not graded (a tiny line's percentage says little).
- **Lines running over:** a dub line still speaking more than 0.5 s after the original's next line has started
  (the lines overlap, or the next one starts late).

| Measure | Good | Needs review | Poor |
|---|---|---|---|
| Line length (share of graded lines not off) | ≥ 90% | 50–90% | < 50%, and at least 3 lines off |
| Lines running over (share of lines) | none | up to 10%, or fewer than 3 lines | > 10% and at least 3 lines |

Problem intervals: a line that is off (more than 15% and at least 0.6 s) is Needs review, Poor beyond 30%; a line
running over is Needs review, Poor from 1 s. Each names the line number and both lengths.

**Verified** on real PersoDub dubs: an untouched EN→KO dub had 12 of 13 lines fit; the same dub with its audio
slowed by 20% was Poor on line length and overruns; a 7 s clip with one line off out of two is Needs review, not Poor.
The bands are first guesses (still to be calibrated on labelled dubs). Lines near the recognizer's segment
boundaries can tip either way when the audio is shifted.

### Distortion (`clipping_pct`)
Share of dub samples at |x| ≥ 0.999. Good ≤ 0.01%, Needs review ≤ 0.1%.

### Speaking pace bands
The dub language comes from the share link's metadata (base code, so `es-MX` uses the `es` rule). Chars/s for Korean (Good ≤ 7.5, Needs review ≤ 9), Japanese (≤ 8.5, ≤ 10.5), Chinese (≤ 6, ≤ 7.5); words/s for English (≤ 3.2, ≤ 3.8) and Spanish (≤ 3.5, ≤ 4.2). Any other language has no rule: the row is **not measured**, with the reason and the measured pace, and never counts toward the verdict. Rules of thumb for "the translation is too long for the time slot"; the sample dub runs at 5.8 chars/s.

### Video integrity (`video_integrity`)
Resolution, frame rate, frame count and audio stream of both files (OpenCV + ffmpeg stream list). Poor if the dub can't be read or has no audio, Needs review if resolution or frame rate changed.

## 5. Meaning: the offline screen and the translation check

### Line by line (`pipeline.judge_lines`)
Both checks read the speech line by line: each matched line (§ Line by line) with what the original and the dub
said at the same time, then speech heard on one side only. When subtitle files are given, each line also carries
what that side was meant to say (the dub's subtitles moved onto the original's timeline by the pairing shift).

### No offline meaning screen
Until 0.1.8 a sentence model (BGE-M3) compared each line pair when no translation check ran, and flagged lines below
0.60 similarity. It was removed on 2026-11-20 (owner's decision): 6 of its 8 flags on real dubs were lines Gemini also
scored low, but it found only 6 of Gemini's 25 low lines (`docs/validation.md`), so a clean result said little while it
looked like a translation check. Without a translation check, the report says the translation wasn't checked and the
score is provisional; the numbers check below still runs. An installed copy of its 585 MB download is deleted when
DubEval starts (`packs.remove_retired`). Results saved with it keep `meaning_screen`: reports no longer show its row or moments, and
the not-measured translation check row says the evaluation was made with it (`r.tr.screen_removed`), so reopening one
doesn't look as if its flagged lines were fixed. Votes cast on its "meaning may differ" moments still count under its
name in `qa.py feedback`.

### Numbers, offline (`numbers.py`)
Every number a dub line says is compared with the numbers its original line says, without an AI. Digits are
normalized across languages (1,000 = 1.000 = 1 000 = 1000; 3,5 = 3.5; 3.50 = 3.5; 007 = 7; other digit scripts
too; 3:30 is 3 and 30), and a number also counts when the line before or after says it (a translation can move it). Only
lines with digits on both sides are compared: a number said as a word on one side ("three", 세) is skipped, since speech
recognition writes numbers either way. When every number is like that, the row is information ("Not compared (said in words)"),
not a check that failed to run; with no number on either side there is no row.

It flags a number replaced by another, and nothing else, because languages say one number differently: "July 4" is 7월 4일
(a 7 the original doesn't have), "2 million" is 200만, "$30,000" is 3만, "15,000" is 1만 5000. So numbers are compared by
their significant digits, and a number only one side says isn't flagged. The cost: it misses a number wrong only by its
zeros (5 and 50) and an added number. The translation check reads those.

| | Good | Needs review |
|---|---|---|
| Numbers | every compared line keeps its numbers | a line says a number its original doesn't (never Poor: a recognizer can mishear a digit) |

Each such line becomes a `names_numbers` problem interval, with both lines' numbers. There's no row when neither side
says a number in digits; it's not measured when the digits are on one side only, or when the dub's language wasn't
recognized. On the 20 graded dubs (2026-11-01) it compared 5 lines on 3 dubs with no false alarm, and caught 5 of 5
numbers changed in those lines (one is the translation-mistake test's "35%" → "75%", which the local judge missed
every time; `docs/validation.md`). **Blind spot:** numbers said as words aren't read ("four, three, two, one"
against "4 3 2"), so a changed number is caught only when both transcripts write it in digits.

### Translation check (`translation_judge.py`)
A judge scores **every line** against a rubric of five criteria, each from 1 to 10 against a written description of
every score (in the JSON schema the judge answers with):

| Criterion | Report row | What it scores |
|---|---|---|
| `semantic_accuracy` | Meaning preserved | the original's core meaning and nuance carried over: nothing left out, distorted or added |
| `linguistic_naturalness` | Natural wording | sounds like natural speech in the dub's language, not translationese |
| `contextual_consistency` | Fits the context | fits the lines before and after, the scene's flow and mood |
| `terminology_consistency` | Consistent terms | the same terms, names and expressions translated the same way |
| `localization_appropriateness` | Localization | register, idiom and culture right for the audience |

**One row in the report** (`report._rubric`). The five criteria were five rows that said one thing: on 16 judged
dubs the four after meaning had the same level 11 times, in near-identical sentences. The report now has one
**Translation check** row. Its level is the worst of the five (so the verdict is what it was: meaning alone can be Poor,
the others reach Needs review at most), its value is the meaning average, and the five scores are inside it (`parts`:
each with its average, its level and how many lines scored 6 or lower). It says, in order: how many lines lose or change
the meaning ("3 of 5"), the lines to listen to because they may be misheard, and what to do. Under it, a small table
gives each score's two numbers under their own headings, "Average of all lines" and "Lines scoring 6 or lower": written
together in a sentence ("Localization 5.2 / 10" and "Localization (5)") they were taken for one number. The text report
says each in words instead ("Natural wording: 7.7 / 10 on average · 1 of 3 lines at 6 or lower"). `summary.csv` keeps a level and a value column for each of the five. On the 20 graded dubs the median report went
from 26 rows to 21.5, the rows marked Needs review from 69 to 40, and no verdict changed.

For each line it also gives a reason for every score of 7 or lower (in four languages), an ideal translation when any
score is 7 or lower, one of 23 error types (omission, meaning distorted, context misread, content not in the original,
word-for-word translation, idiom misread, formality, tone, pronoun, possessive, gender/number, terms, technical term,
abbreviation, culture, translated what should stay, sentence split, clause structure, word choice, repetitive style,
wordiness, word order copied, other; or no clear error) and `may_be_recognition_error`. The judge sees every line as
context and judges up to 20 lines per request (`CHUNK_LINES`, about a minute each), sending a long video's requests
three at a time; a failed request makes the whole check not measured. **Every line must get an answer:** only the lines
a request asked about count, and lines an answer left out are asked about once more. Lines still unanswered make the
whole check not measured, saying how much was evaluated ("1 of 3 lines"), so a partial review can't look complete: no
meaning grade, the verdict can't be Good, and a comparison holds its recommendation. A Gemini model that takes longer than 120 s
(`DUBEVAL_JUDGE_TIMEOUT`) hands over to the next model at once, and a key whose daily requests are used up (free keys:
20 a day per model when last seen) says so, with when it resets and what to do, instead of "busy".
The video's title goes along as its description.

**The judge** (`--judge`, or `DUBEVAL_JUDGE`): `auto` (default) takes the first available of **Claude**
(`claude-opus-5-5`, structured JSON output, medium effort, server-side refusal fallback; `ANTHROPIC_API_KEY`),
**Gemini** (`GEMINI_API_KEY`), and a **local model through Ollama** (Gemma 4 12B, `gemma4:12b-it-q4_K_M`, by default; `DUBEVAL_OLLAMA_URL`,
`DUBEVAL_OLLAMA_MODEL`; nothing leaves the computer). Use the same judge for every dub you compare; the report
names it. Gemini's models are fixed names tried in order (`gemini-3.5-flash`, `gemini-3.8-flash`,
`gemini-3.1-flash-lite`; never a "latest" alias). Google can still serve a newer version under a name (`gemini-3.5-flash`
answered as `gemini-3.6-flash`), so the result keeps what was asked for and what answered. A dub's later requests go first to
the model that answered its first one, so one dub isn't split across models. The result keeps which model judged
which lines (`translation_judge.chunks`, `models`), and the report names every one; a comparison whose dubs were
judged by different models says so in its caution. **Locking the model** (the start page's More options, `--lock-model`,
the API's `lock_model`, or `DUBEVAL_JUDGE_PIN=1`) uses only the first model, with no server-side fallback on Claude: a busy
model makes the check not measured instead of handing over to a backup. Use it for comparisons and calibration runs,
so differences come from the dubs, though not entirely: reviews by one model still move, and a verdict can flip (`docs/validation.md`). In automatic mode, and for the checker
chosen on the app's start page, an account problem (no credit, a rejected key) still hands over to the next service with
a key, and the report says which one couldn't check and why; name the checker with `--judge` to rule that out. On a free Gemini key (20 requests a day per model when last seen) a locked run of many dubs can use up
that model's day; the report then says so, and the run has to wait for the daily reset or use a key with billing. Before a local judge runs, the speech recognizer and the sentence model are unloaded so the judge fits
in the GPU (a model that spills onto the CPU takes many minutes); its context is sized to the prompt.

**The dub type** (`--dub-type`): `human` tells the judge that adapted jokes, idioms and cultural references are
intended localization; `ai_clone` and `ai_stock` are held to a close translation. Human and stock-voice dubs also
skip voice similarity (another voice is expected).

**Local judge, measured:** Gemma 4 12B (English-only answers) caught 28 of 28 mistakes planted in real dub
transcripts and flagged none of 11 harmless rewordings, on Windows and on a Mac (`validation.md`). It takes about
11 s a line on an 8 GB laptop graphics card and 7 s on an M2 Pro, and needs about 7 GB of graphics memory; without
that it runs on the processor, much slower. It hasn't been compared with a reviewer's labels yet. It replaced Qwen3
8B (2026-11-13), which found 4 of 23 planted mistakes and reported missing content in 11 of 13 lines of a good dub.

Bands (`RUBRIC_FLAG` 6, `RUBRIC_POOR` 4, `RUBRIC_POOR_LINES` 3 in `report.py`): each row shows the average over the
lines and how many lines scored 6 or lower. **Meaning** is Poor when 3 or more lines, or most lines, score 4 or lower;
Needs review when any line scores 6 or lower (one or two serious lines included, still listed with their times); otherwise
Good. Until 2026-10-29 one serious line made meaning Poor; on 19 dubs graded by a person, a cut countdown or two
swapped sentences made dubs Poor that the person graded Good for meaning (`docs/validation.md`). The other four rows are Needs review when any line scores 6 or lower and never Poor, until labelled dubs show
they should be. Every line scoring 6 or lower on any criterion becomes an issue on that line's time span, with its
error type, the reason for its lowest score (meaning first) and the suggested translation; meaning at 4 or lower makes
it Poor (major). Meaning errors keep their timeline categories (missing / added speech, mistranslation, names and
terms); wording problems are `translation_wording`. The review's line panel shows a line's five scores, the reasons,
the error type and the suggested translation. History and compare mode show meaning out of 10 (older results, scored
1-5 by the previous check, are shown as before; History's averages scale them to 10).

It sees transcripts, not audio, so a mishearing can look like a translation error; the judge flags those, and
**flagged lines don't change a level**: they are shown as "(+N?)" and listed under *Things to check* to confirm by
ear. Without a judge it's reported as not measured, with the reason.

### Speech that can't be graded (`report.speech_problem`)
- **Recognition failed:** when the dub sounds like a third language (neither its own nor the original's) and the
  recognizer is less than 80% sure, recognition failed (an English → Uzbek dub was heard as Kazakh, 47% sure). The
  language row is "not measured" with the reason ("listen to confirm"; a dub subtitle file can confirm the language
  instead, see below), and every measure built on the recognized speech (clarity, timing, line length and overruns,
  pace and the translation check) is "not graded" instead of Poor. The translation judge isn't even run on that speech: they would only grade recognition noise (two Uzbek dubs a person
  graded Good and Needs review scored 1 of 5). A confident third language, or the original's language, stays Poor (a real
  wrong-language dub). Long silences are still listed there, without reading a word: where the voice detector hears the
  dub silent and the original speak for at least 2 s in total (`evaluate.voice_gaps`), Poor from 4 s. They're moments
  to listen to, and the timing row says it's looking for them; the verdict still comes from the rows.
- **No speech:** when the dub has no recognized speech at all while the original has (music, singing, noise), a "Speech
  found" row is **Poor**: nothing was dubbed. When the original has none, the row is Needs review: a person should watch it,
  because the speech checks couldn't run.

The first versions came from 7 labelled PersoDub pairs (agreement 3 → 5). On the 12-pair set of 2026-10-25 the
language row moved from Needs review to "not measured" (three Uzbek dubs graded Good were held at Needs review by it) and a dub
without speech from Needs review to Poor (the reviewer graded such a dub Poor).

## 6. The report and the verdict (`report.py`)
Every measure gets a level (good / check / poor / info / not measured), a one-sentence explanation and the thresholds used. **Verdict:** any Poor → Poor; otherwise any Needs review → Needs review; otherwise Good. Info (speech offsets) and not-measured items never change it, and the report lists why each unmeasured item wasn't measured.

**Quality score** (`report._score`, `SCORE_WEIGHTS`, `SCORE_POINTS`, `POOR_COSTS`; owner's decisions, 2026-11-20 to -22): a
number out of 100 shown next to the verdict, never instead of it, and never part of the compare decision rule. Each
graded check scores 100 when Good and 0 when Poor; a check that needs review scores by where its result sits between
the Poor limit (0) and the Good limit (100) (`_scale`, owner's decision, 2026-11-20: 15 of 18 lines fitting, with Good
from 90% and Poor under 50%, scores 83, not 50), at most 99 (`SCORE_CHECK_MAX`). The translation check and voice quality
use the share of lines or stretches without a problem (`_share_ok`); a check with no number to place (dub language, voice
similarity, same video, noise, numbers) keeps 50. Each check's points are `score_points` on its row. A
section scores the average of its graded checks; the score is the sections' weighted sum:

| Section | Checks | Weight |
|---|---|---|
| Translation | translation check, numbers | 30 |
| Timing | speech timing, line length, lines running over | 25 |
| Speech & voice | dub language, clarity, voice quality, voice similarity | 15 |
| Length & sound | length, loudness, silence, distortion, noise, pace | 15 |
| Same video | same video, sound in sync, coverage | 10 |
| Lip sync | lip sync | 5 |
| Video file | must pass; no weight | — |

The parts are named for what they hold (2026-11-20): "Length & sound" (was Timing & audio), "Timing" (was Timing
alignment) and "Speech & voice" (was Speech recognition, which also held the voice checks). The ids stay (`timing_audio`,
`alignment`, `speech`). The app lists the parts that need attention first (Poor, then Needs review), then by weight, as
the score table does.

**The number is the one worked out** (2026-11-21). Until then a cap held a Needs review dub at 89 and a Poor one at 59;
a dub whose checks added up to 97 showed 89, and a comparison needed "89 / 100 (97 before the Needs review limit)". Now
the score is the sum, except that only a dub with every check Good scores 100 (a Needs review one shows 99 at most), and
**in a Poor verdict each Poor result costs at least a set amount by how serious it is** instead of its share: one Poor
check is often a dealbreaker its weight doesn't show (a dub that crackles throughout would have kept 97). Three levels,
as translation QA grades errors critical, major and minor (`POOR_COSTS`, `POOR_SEVERITY`, 2026-11-22):

| Level | Costs at least | Checks | Why this level |
|---|---|---|---|
| Unusable | 100 (the score is 0) | speech found (no speech in the dub), dub language (the wrong language), same video, video file | nothing deliverable; the reviewer graded the dub without speech and the wrong-language dub Poor |
| Serious | 40 | every other check that can be Poor: translation, speech timing, line length, lines running over, lip sync, sound in sync, distortion, voice quality, voice clarity, speaking pace, length, coverage | a viewer notices and it must be fixed; translation isn't higher because the checker can be wrong (the reviewer agreed with 4 of its 5 Poor results on the test dubs, not p019) |
| Minor | 20 | loudness, silence | the mix fixes them; the reviewer graded a dub 5.1 dB off Good, and silence goes Poor when a dub's background music was removed |

Three numbers instead of one per check: the evidence is thin, so each check is put in a level by a stated reason, and
a level's number moves when graded dubs show it should. Noise, numbers and voice similarity are never Poor. A Poor
result whose share is already more than its level's cost loses its share. `raw` is the weighted sum, `poor_cost` what
Poor results cost beyond their share, and each line of `score.lost` has its `severity`. A Poor row DubEval isn't sure
of (little or unclear speech, so the verdict is Needs review) costs only its share.

**A check that wasn't measured is one of three kinds** (`report._absent`, `score.parts[].items[].absent`):

| Kind | When | In the score |
|---|---|---|
| Doesn't apply (`na`) | lip sync on a dub that isn't lip-synced; the lip check with too few faces or an original whose own lips don't line up; voice similarity for human or stock voices; sound sync on a dub that replaces the background or a clip too short; no line long enough to grade; line checks on a mostly-music video; speech checks when the original has no speech | left out, its points shared; the coverage doesn't count it |
| Couldn't be measured (`missing`) | no translation checker, the lip check off or not downloaded, speech not recognized (a known gap for less common languages, not the dub's fault), the voice model can't tell, errors | left out and shared too, but `coverage` (the % of what applies that was measured) drops and the message names it |
| The dub caused it (`dub`) | no speech in the dub: its speech checks can't run (`DUB_SPEECH_CHECKS`) | counts as 0, never shared: shared out, a dub without speech scored 90+ on the checks that still passed |

The score is **provisional** under 80% coverage (`COVERAGE_MIN`) or without the translation check, and there is **no
score** under 50% (`SCORE_MIN_COVERAGE`): three test dubs whose language wasn't recognized had 26-30% measured and showed
"99 / 100 (provisional)". The message says what was left out and why ("Lip sync wasn't checked, so its 5 points are
shared among the other sections. 91% of the checks that apply to this dub were measured."). When Poor results cost more than their share, the message says so and the table gets a last row, "Extra for Poor results", so it adds up to the score; a Poor row DubEval isn't sure of says it loses only its share; with no score ("Too little measured") there is no table or list of points; the card and each section then show
the share each section really has (Translation 31.6% when lip sync is left out), so the points add up. On the 20 test
dubs: Poor 11-60, Needs review 82-98 (one at 38 whose Poor rows DubEval isn't sure of), Good 100, and the four whose
language wasn't recognized "Too little measured". Everything is counted in
one unit, **points** out of 100: each section shows the points it got of the most it could (`score.parts[].display`,
"22.5 of 31.6 points"; no section score out of 100 beside the dub's), and each check its share of its section's
points, split evenly among the graded checks from the exact share, so a one-check section's row and header agree
(`parts[].items`, `score_share` on each measure; `score_display`, at the right of its row, only on a check that lost
points, since "2.6 of 2.6" on every Good row hid them: with Timing at 38.5 points and three checks measured, a
line length at 83 shows "10.7 of 12.8 points"; the section shows the sum, "36.4 of 38.5 points"). In the
app, a part with nothing measured and nothing to fix has no card: the Not measured list says why. Things to check lists
the moments first and folds the measures behind the verdict behind their own button ("Show the 3 measures behind the
verdict"), so "Show 3 more" never reads as three more problems. A speech-timing row that needs review but lists no
moment says why: each part that is off is too short to show. The score card lists the **points
lost** (`score.lost`: the checks that lost points, biggest first, each with its result in `why`, e.g. "2 of 7 lines
flagged"; a Poor one "−40.0 points" with "a Poor result costs at least 40 points", or "makes the dub unusable: 100
points", or "a problem the mix can fix: at least 20 points"; in the app a click opens the check),
each loss worked out from the exact points so the list adds up: the heading does the sum (`lost_display`, "11.0 points
lost, so 89 / 100", the sum of the lines as shown, "(rounded)" when 100 minus it isn't the score;
`lost_total`), and a line under it says how a check loses points (`lost_how`). Every number of points has one decimal
("23.0 of 26.3"), so a column of them lines up. The video file's section says "Not in the
score". **Translation counts
only when the translation check ran** (`SCORE_REQUIRES`): without it the numbers check (only a changed number) would
grade its 30% on its own and lift the score, so the section isn't counted
and the score is marked **provisional** (`score.provisional`), saying why, and `summary.csv` has a `score` column; a comparison shows each dub's score in
its ranking, as a label only. Each Evaluations card carries the score worked out with the current rules from its saved results
(`library._score`; `CARD_VERSION` goes up when the score's rules change), and every history record keeps `score` and
`score_provisional` (a language pair's average leaves out records without one). Example: the Tears of Steel dubs, both Needs review: A (6 of 8 lines fit, everything else
Good) scores 97, B (2 of 7 lines flagged by the translation check, 5 of 6 lines fit, 74% lined up) 89. **The weights are reasoned, not measured:** they follow the
roadmap's order (timing and meaning first, lip sync last) and haven't been checked against people's grades. Every report says so in its rule (folded in the app and the HTML report, one line in the text report).

**How sure** (`report.sure_of`): DubEval says so when its own measurement is shaky, and the verdict follows.

| Not sure because | Measured as | Effect |
|---|---|---|
| little speech | the original speaks < 35% of the video (`SURE_SPEECH_SHARE`) | only distortion, same video, coverage, file, sound sync or speech found can make it Poor; else Needs review. Line length and overruns aren't graded or listed: recognized words over music aren't reliable |
| too little speech | < 10 s of original speech (`SURE_SPEECH_SEC`) | same |
| unclear speech | the dub recognized confidently < 90% of its speech time (`SURE_CLARITY`) | same |
| background replaced | the dub's background (DNSMOS BAK) ≥ 2.0 cleaner than the original's (`BACKGROUND_REPLACED`) | silence and loudness are Needs review at most |
| words not checked | the dub's language wasn't recognized (`speech_problem` "unrecognized") | never Good |
| translation not checked | the translation check didn't run: no judge, an error, or turned off (a required check) | never Good |
| backup judge | a backup model judged the translation (`translation_judge.fallback`) | a note; no level changes |
| a language the speech model reads badly | on 25 read test sentences the model used got more than 10% of characters wrong in the dub's or the original's language (`WEAK_RECOGNITION_PCT`, `languages.RECOGNITION_ERRORS`: 36 languages, `large-v3-turbo` and `base`) | a note naming the language, the model and the measured share, and the large model when it reads that language well; no level changes. A model or language that wasn't measured gets no note |

The headline states each reason in plain words and asks the reader to listen. Set on 19 dubs a person graded:
agreement 11 → 13 of 19, all 5 graded Poor still Poor (`docs/validation.md`). There's deliberately no single 0–100 score: weights between these measures would be arbitrary and hard to defend.

## 7. Problem intervals (`intervals.py`)
(Pairing adds the `missing_in_dub` category: a part of the original that isn't in the dub, Needs review, Poor from 5 s, and `sound_sync`: the whole dub when its sound is 0.3 s or more
behind or ahead of its picture, Poor from 0.6 s.
Line timing adds `line_length` and `line_overrun`; see "Line by line" above.)
Every issue becomes a time range `{start, end, dub, category, severity (poor/check), check, description}`, in `report.problem_intervals`. Things to check are built from the same list.

| Category | Found by | Severity |
|---|---|---|
| `long_silence` | speech timing: original speaks, dub silent for ≥ 2 s, the voice detector agreeing; where the dub's words can't be read, the voice detector alone (`timing_alignment.voice_gaps`) | Poor from 4 s, else Needs review |
| `timing_mismatch` | speech timing: shorter one-track-only stretches of at least 0.8 s, the voice detector agreeing (`TIMING_MIN_SEC`; 0.5-0.8 s ones are word-timing jitter that validation saw come and go; they still count in the overlap score). The speech-timing row's "N short moments don't line up" counts only these and long silences (`listed_mismatches`), so it never promises moments the list doesn't have | Needs review |
| `missing_speech` / `added_speech` | translation check | Poor if major, else Needs review |
| `mistranslation`, `names_numbers` | translation check | Poor if major, else Needs review |
| `names_numbers` | numbers check: a number the original says (on that line or the one before or after) has become another in the dub | Needs review |
| `translation_wording` | translation check (naturalness, context, terms, localization) | Needs review |
| `distortion` | clipped samples (`dubbed_clipping_intervals`, merged within 0.5 s) | Poor if the clipping row is Poor, else Needs review |
| `loudness_jump` | loudness envelope: dub vs original level, after removing their overall offset, differs by ≥ 10 dB for ≥ 1 s where both tracks have sound | Poor from 16 dB, else Needs review |
| `wrong_language` | Whisper language detection per 10 s window of the dub, windows overlapping by half (`dubbed_language_windows`; they widen so at most 120 are checked): the original's language at ≥ 50% while it leads the expected one by at least 0.3 (`LANG_SOURCE_LEAD`: an 8 s part left in a 10 s window keeps the dub's language near 0.3), or any other language at ≥ 80% while the expected one is < 20% (stricter: Whisper guesses odd languages on noise and music) | original's language: Poor from 80%; other language: Poor from 95%; else Needs review |
| `unclear_speech` | voice clarity: segments Whisper recognised with low confidence, at least 0.5 s long (`SLIVER_SEC`) | Needs review |
| `voice_change` | voice similarity: one line's dub voice much less like the original speaker than the rest | Needs review |
| `noise` | noise: the dub fills with hiss or static the original doesn't have, for at least 1.5 s (see Noise above) | Needs review |
| `voice_quality` | voice quality: a ~9 s stretch where the dub, at the original's volume, scores below the original (SIG ≥ 0.6 or OVRL ≥ 0.5), unless the original itself scores below 1.6 there | Poor from 2.5 / 1.5, else Needs review |

Rules: ranges of the same category that overlap or are less than 0.5 s apart merge (worst severity kept, `merged` counts them); ranges are clipped to the dub's length, rounded to 0.1 s and sorted by start. A translation issue lasts until the end of the original line starting closest to it (within 1 s; the judge quotes line start times), else the line containing it, else 2 s. Issues the judge flags as probable speech-recognition errors go to `report.possible_asr_errors` and never count, except a meaning issue scored 4 or lower: the judge can't tell a mishearing from a real error there, so it stays a Needs review interval ("listen to the line to tell") and makes meaning Needs review, never Poor. The prompt allows the flag only when a similar-sounding word explains the score, never for a changed, opposite or different-number phrase. `report.problem_seconds` is the time covered by at least one interval (overlaps count once). Intervals don't change the verdict, which comes from the measure levels; compare mode uses `problem_seconds` as a tie-breaker.

**Moments (`group_moments`, `report.moments`).** Two checks often flag the same second: on 20 graded dubs, 9 reports listed
a moment twice ("left out of the translation", then called "missing speech", from the translation check and "the dub is silent" from speech timing). The findings stay
as they are in `problem_intervals` (a reviewer votes on each), and the report puts those about one moment together: two
ranges that share at least 50% of their combined time (`MOMENT_OVERLAP`), or that are about the same line (a line too long
that also runs into the next, or a finding without a line, such as "the dub is silent", lying at least 80% inside one about
a line: `MOMENT_INSIDE`). Otherwise a long range doesn't swallow a short one inside it (a 9 s voice-quality window and a 1 s
wording problem stay two moments). The finding that says most about what is wrong speaks for the moment (`LEAD_ORDER`:
the checks that read the words first, "one track speaks and the other doesn't" last), worst severity first. On those 20
dubs, 78 findings became 66 moments. *Things to check* lists each moment once, with the names of its other findings.

**What a finding says, in parts.** Besides `description` (everything in one text), each finding has `problem` (what is
wrong, in a sentence), `original` and `dubbed` (what each track says there), `suggestion` (a better translation), `doubt`
(`asr`: probably misheard; `asr_or_real`: can't tell) and `line`. A timing moment quotes the words of the track that
speaks, from the transcript lines it shares at least 0.2 s with (20 of 20 timing moments on the 20 dubs now do). The
translation check's "(nothing)" for a silent track is never shown as a quote or a suggestion.

**A moment is Poor only when its measure is** (`report._cap_moments`). Each check grades its moments one by one with the
bands above, but Poor means "this is why the dub is Poor" on a row, a moment and the verdict alike: a moment whose measure
isn't Poor (or isn't graded) is shown as Needs review. Before, 7 of 20 graded dubs showed a Poor moment in a dub with no
Poor measure. The bands above still decide which moments are listed.

**A check that passed lists no moments** (`report._drop_passed`, 2026-11-21). A Good speech-timing row (82% lined up)
listed two "Needs review · Speech timing" moments, and a row that allows some lines to be off listed the line it allowed:
the row said the dub was fine while its moments said it wasn't. Moments that report a local event the row's number
doesn't measure stay (`LISTED_WHEN_PASSED`): the dub silent where the original speaks (long silence), a stretch in the
original's language (on the 20 test dubs one Good language row would have hidden 10 s of the original's English), and a
jump in volume (the reviewer voted both loudness jumps real). On the 20 test dubs 9 of 73 findings were left out (8 short
timing mismatches and one 0.1 s distortion), and with the grouping by line above 64 moments became 49; no verdict
changed. Problem time
(`problem_seconds`, which compare mode's rule 5 reads) counts only the listed findings.

## 8. Calibrating the bands (`qa.py batch`)
Every band above is a starting point. To tune them on your own dubs: list share links with your verdict (`link,good|check|poor`), run `python qa.py batch links.txt`, and read the agreement line and the person × tool table. "Stricter than you" means the tool called a dub worse than you did; find which `<measure>_level` columns in `summary.csv` were Poor or Needs review on those rows, adjust that constant in `report.py` / `intervals.py`, and rerun. Reruns are cached (no downloads, no Whisper, no API calls), so each try takes seconds.

## Sanity warnings (`warnings` in results)
Raised automatically when:
- the duration differs by more than 20% (probably not a matching pair),
- the dub transcript is empty,
- the primary error rate is above 0.8 (probably the wrong script or language),

Each warning also appears under *Things to check* in the report.

### Dub language confirmed by its subtitle file
When a dub subtitle file is given, the dub's transcript (made in the dub's language) is compared with the file's text (`evaluate.subtitle_agreement`: 1 − character error rate, case, punctuation and spacing ignored; stored as `subtitle_match`). From `report.SUBTITLE_MATCH` (0.45) the dub is taken to be in that language: the Dub language row is Good whatever recognition guessed from the sound, speech-based checks stay graded (no "unrecognized" problem), and "another language" windows are dropped (the original's language heard in the dub is still reported). Measured on one real EN→UZ Perso dub: 0.61 against its Uzbek subtitles, 0.17-0.25 for unrelated text.
