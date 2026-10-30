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
- *Sound*: the onset envelope of each audio track every 10 ms. When it correlates at least 0.15, it refines the
  picture's shift within ±0.3 s; with a file that has no picture, it decides alone (and never refuses).

Motion wins whenever it explains at least 60% of the original; otherwise the answer that finds more of the original
in the dub wins. **Correction:** shifts of 0.1 s or more are corrected by moving the dub's audio onto the original's
timeline (one shift), or by laying it part by part (a differently cut dub; missing parts stay silent), so every time
in the report is the original's.

| Measure | Good | Check | Poor |
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
with every control within 0.24 s. A Check or Poor result is also a whole-dub "sound out of sync" problem interval.

Each missing part of at least 1 s is a "missing from the dub" problem interval: Check, Poor from 5 s (shorter slivers,
such as files differing in length by a frame, are never listed: `intervals.SLIVER_SEC`).

**Verified** on synthetic clips (aligned, shifted 2 s, 5 s cut out, unrelated) and on real PersoDub dubs: a dub
with 2.5 s added at the start measured +2.50 s (speech timing back to the untouched 90%); a dub with 40–45 s cut out
reported 95% coverage and the missing part at 40.1–45.1 s; an unrelated pair was refused; 7 untouched real pairs
were all "same video", no shift, 100% coverage. **Limits:** a dub that is cropped, letterboxed or reframed (for
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

Whisper's fallback sampling is seeded (`WHISPER_SEED`), so the same audio always gives the same transcript and scores.

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

The highlighted diff under **What was said** shows which is which. For meaning rather than wording, use the translation check (§5). The default speech model is **automatic**: Whisper `large-v3-turbo` when it is downloaded (Settings → Models) and the computer has an NVIDIA GPU, otherwise `base`. On 4 PersoDub EN→KO dubs scored against their exact dub scripts (2026-10-26), `large-v3-turbo` made a quarter to half fewer errors than `base` on natural Korean speech (8.3% and 2.9% of characters against 11.1% and 7.1%) at the same speed on a GPU; on lines mixing English words into Korean every recognizer did badly. SenseVoice-Small, NVIDIA Parakeet (English) and Whisper `large-v3` did no better, and all five heard "new cases" where the speaker meant "new tastes", which is why the translation check marks possible mishearings. `base` (fast, 145 MB): It mishears a few more words than `small`, which mostly shows up as extra "possible recognition error" items; for reporting-grade transcripts set `WHISPER_MODEL=small` or `medium`.

### Speech rate
Words per second (chars/s for ko/ja/zh/th) over *speaking time*, where speaking time is duration × (1 − silence ratio). Units differ between languages, so compare the dub against other dubs in the same language, not against the original.

### Loudness over time
The dBFS of each 0.25 s window, for both tracks. Peaks and gaps should line up. A shifted or stretched pattern shows timing drift that the single duration number hides.

## Score bands (audio and script)
| Measure | ✓ Good | ! Check | ✗ Poor |
|---|---|---|---|
| Length match: \|Δduration\| / original | ≤ 5% | ≤ 15% | above that |
| Matches your script: accuracy | ≥ 80% | ≥ 50% | below |
| Loudness match: dub vs original | within ±2 dB | within ±4 dB | beyond |
| Extra silence in the dub | ≤ 5 pts | ≤ 15 pts | above |
| Lip sync / lip movement | always informational ||| 

The script-free measures and their bands are in §4 and §5. The script bands are lenient on purpose, because paraphrases count as errors (§2).

## 3. Lip sync

Measured automatically when the shared dub is lip-synced (`isLipSync`); skipped otherwise, and the report says why.
Always informational. With the `lip_sync` download installed, the lip-sync check below runs; without it, the
lip-movement estimate after it.

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

### Without the download: lip movement (`analyze_lipsync`), experimental

1. Frames are sampled at about 15 fps (sequential decode) over the first 60 s. MediaPipe runs in VIDEO mode.
2. Per frame, the Mouth Aspect Ratio is `|lm13 − lm14| / |lm61 − lm291|`. Frames without a face are excluded rather than filled in.
3. Speech RMS is computed on a 10 ms grid and interpolated at each frame's timestamp, so it doesn't drift.
4. **Score:** the Pearson r at zero lag (`pearson_correlation`).
5. Diagnostic: the best r within ±200 ms (`best_lag_correlation`, `best_lag_ms`). Taking a maximum over 21 lags turns pure noise into r ≈ +0.1, so this is **never** used as the score.
6. The result is `valid: false` with a `reason` if there are fewer than 20 frames, faces appear in fewer than 50% of frames, or the mouth never moves.

`sync_quality` bands: `strong` ≥ 0.4 · `moderate` ≥ 0.2 · `weak` ≥ 0.05 · `none` below that.

### Known limitation: this heuristic does not work on the sample video
| Video | r (zero lag) | Face coverage |
|---|---|---|
| Original, which is in sync by definition | **−0.20** | 56% |
| Perso Korean lip-sync dub | −0.03 | 56% |

The original should score clearly positive, and it doesn't. The causes, found by investigation:
- **Voice-over B-roll.** The speaker is on screen but not talking (typing, walking) while narration plays. Those frames anti-correlate mouth opening with loudness.
- **Weak signal even on the talking-head part.** On the first 5.5 s (99% face coverage), every variant tried gave |r| < 0.2 and random best lags: inner vs. outer lips, face-height normalization, speech-band (300–3400 Hz) energy, and smoothing.

**Treat the lip movement row as informational.** Compare it only against `original_pearson` on the same video, never as an absolute. The lip-sync check above replaces it when its download is installed.

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
Whisper's language identification on the first 30 s of the dub. **Good** when it matches the target and Whisper is ≥ 50% sure, **Check** when it matches but Whisper is unsure, **Poor** when it's a different language. Catches the worst failure (wrong language, or the original voice left in).

### Voice clarity (`speech_clarity`)
Share of speech time in Whisper segments with `avg_logprob ≥ −1.0` (Whisper's own threshold for trusting a decode). Segments Whisper itself treats as silence (`no_speech_prob > 0.6` and `avg_logprob < −1.0`) are ignored, as are lines the voice detector hears no speech in (above); faster-whisper's large-v3-turbo reports `no_speech_prob` 0 for every line, so on it only the voice detector removes them. Good ≥ 90%, Check ≥ 70%. The unclear segments are listed with timestamps under *Things to check*. It's an intelligibility proxy that needs no script; ASR weaknesses on names and accents also lower it.

### Voice quality (`voice_quality.py`)
Does the dub's voice sound clean, or robotic and distorted? Microsoft's **DNSMOS P.835** (bundled ONNX model, CC BY 4.0) predicts listener scores (1–5) for the speech signal (SIG), the background (BAK) and the overall sound (OVRL) on ~9 s windows, every 2 s (widened on long videos to at most 120 windows). Only windows where **both tracks speak at least 3 s** are scored, on both tracks at the same moment. A dub keeps the original's music and effects, so the comparison isolates the dub's own sound; absolute scores would mostly measure the music.

A window is **Check** when the dub's SIG is ≥ 0.6 below the original's or its OVRL is ≥ 0.5 below, **Poor** from 1.0 / 0.9. The worst window sets the level, and flagged windows become `voice_quality` problem intervals. Not measured when the two tracks never speak together long enough, or when the original itself scores below 1.6 (too noisy to serve as reference).

**Why both scores:** in tests on two real EN→ES Perso dubs, a robotic (quantised) voice dropped SIG by ~0.9 but OVRL by only ~0.4, while clipping distortion dropped OVRL by ~0.7 but SIG by ~0.25 (the model books distortion under background). Clean dubs never fell more than 0.25 below the original (the Perso voices actually scored 0.3–0.4 above the film's recorded dialogue). **Blind spot:** a muffled (low-passed) voice barely changes any score.

**Why not UTMOS:** UTMOS22 (the usual TTS naturalness predictor) was tested first. It rates clean synthetic speech well (3.9) but collapses to ~1.2–1.5 on every real recording, including the originals and voices separated from the music with Demucs, so it can't tell a good dub from a bad one.

### Voice similarity (`speaker.py`)
Does the dub voice still sound like the original speaker? **WeSpeaker ResNet34-LM** (trained on VoxCeleb2's 5,994 speakers; ONNX, CC BY 4.0; 26.5 MB, downloaded once, pinned to a Hugging Face commit and SHA-256) turns speech into a 256-number voice fingerprint from 80-band Kaldi filterbanks (computed with numpy). Each original line of ≥ 2 s is compared with the dub **at the same moment** (Perso keeps the timing), which follows every character in a multi-speaker video without speaker detection. The level uses the median similarity: **Good ≥ 50%, otherwise Check** (never Poor: a new voice can be a deliberate choice).

**Only lines with a quiet background count** (the original line's DNSMOS background score ≥ 3.0). On a real film with music, even two lines of the same actor scored below 0.45, so the comparison would be noise; such videos show "not measured" with the reason. On clean speech (synthetic voices): the same voice scored 0.80–0.87 even across languages (English original, Spanish dub), different voices median 0.13, max 0.57.

**Different-voice intervals:** a line ≥ 0.2 below the dub's median similarity and below 0.65, in a dub whose median is ≥ 0.45 (it clones its speakers otherwise), is flagged `voice_change`: that line probably got another character's voice. Tested: a similar female voice swapped onto one line (0.55 vs median 0.81) and a female voice on a male line (0.20) were both flagged; a good clone and a stock voice throughout flagged nothing.

### Speech timing (`speech_intervals`, `timing_alignment`)
1. Speech stretches come from Whisper word timings, merging gaps shorter than 0.3 s and dropping segments Whisper treats as silence. Word timings follow speech, not the music bed, which defeats energy-based voice detection on this kind of video.
2. Both tracks go on a 50 ms grid. `overlap_pct` is intersection over union of speaking time. Stretches of ≥ 0.5 s where only one track speaks become `mismatches` (`dub_only` / `original_only`, the 8 longest).
3. Bands: Good ≥ 75%, Check ≥ 55%. **Calibration:** the real Perso EN→KO lip-sync dub of the sample scores **81%**, with two short dub-only spots. Languages differ in rhythm, so 100% isn't expected; these bands are a starting point from one sample and should be tuned on more dubs.
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

| Measure | Good | Check | Poor |
|---|---|---|---|
| Line length (share of graded lines not off) | ≥ 90% | 70–90% | < 70%, and at least 3 lines off |
| Lines running over (share of lines) | none | up to 10%, or fewer than 3 lines | > 10% and at least 3 lines |

Problem intervals: a line that is off (more than 15% and at least 0.6 s) is Check, Poor beyond 30%; a line
running over is Check, Poor from 1 s. Each names the line number and both lengths.

**Verified** on real PersoDub dubs: an untouched EN→KO dub had 12 of 13 lines fit; the same dub with its audio
slowed by 20% was Poor on line length and overruns; a 7 s clip with one line off out of two is Check, not Poor.
The bands are first guesses (Phase 5 calibrates them on labelled dubs). Lines near the recognizer's segment
boundaries can tip either way when the audio is shifted.

### Distortion (`clipping_pct`)
Share of dub samples at |x| ≥ 0.999. Good ≤ 0.01%, Check ≤ 0.1%.

### Speaking pace bands
The dub language comes from the share link's metadata (base code, so `es-MX` uses the `es` rule). Chars/s for Korean (Good ≤ 7.5, Check ≤ 9), Japanese (≤ 8.5, ≤ 10.5), Chinese (≤ 6, ≤ 7.5); words/s for English (≤ 3.2, ≤ 3.8) and Spanish (≤ 3.5, ≤ 4.2). Any other language has no rule: the row is **not measured**, with the reason and the measured pace, and never counts toward the verdict. Rules of thumb for "the translation is too long for the time slot"; the sample dub runs at 5.8 chars/s.

### Video integrity (`video_integrity`)
Resolution, frame rate, frame count and audio stream of both files (OpenCV + ffmpeg stream list). Poor if the dub can't be read or has no audio, Check if resolution or frame rate changed.

## 5. Meaning: the offline screen and the translation check

### Line by line (`pipeline.judge_lines`)
Both checks read the speech line by line: each matched line (§ Line by line) with what the original and the dub
said at the same time, then speech heard on one side only. When subtitle files are given, each line also carries
what that side was meant to say (the dub's subtitles moved onto the original's timeline by the pairing shift).

### Meaning similarity, offline (`meaning.py`)
A multilingual sentence model, **BGE-M3** (BAAI, MIT license), turns each
original line and each dub line into a vector; their cosine similarity (0-1) says how close they are in meaning,
across languages. It needs no cloud service and takes seconds per video.

It runs from an **ONNX pack** (BGE-M3 with int8 weights, 586 MB, on onnxruntime, about 30 ms per line on the CPU),
so DubEval needs no PyTorch; a development install can use the original model through sentence-transformers instead.
The pack is downloaded from the app's Downloads page (Xenova/bge-m3's int8 export) or built with
`tools/build_meaning_onnx.py`. On the labelled test pairs (25 lines, 2026-10-22) the downloaded pack scored on average
0.011 lower than the original (95% of lines within 0.030, at most 0.034; the self-built one: 0.009, 0.023, 0.037), and
with either no line moved across the 0.60 band. Each line is embedded on its own: the exported graph mishandles padding, which shifted padded lines by up to
0.02. The two never share cached results (`meaning.model_name()`). Recheck the comparison when the test set grows.

| | Good | Check |
|---|---|---|
| Meaning similarity | no line below 0.60 | any line below 0.60 (never Poor: the judge decides) |

The band comes from real EN→KO PersoDub lines: correct translations had a median of 0.81 with 95% above 0.59;
the same lines shuffled (wrong pairs) had a median of 0.49 with 75% below 0.56. On the Francis dub the lowest line
(0.57) was the one where the dub said 영화 (movies) instead of 영어 (English). Low lines become "meaning may
differ" problem intervals only when no judge ran (the judge's own issues are more precise). It can be fooled by
misheard words, like the judge. Optional: `pip install "dubeval[meaning]"`; `DUBEVAL_MEANING_SCREEN=off` turns it
off.

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

For each line it also gives a reason for every score of 7 or lower (in four languages), an ideal translation when any
score is 7 or lower, one of 23 error types (omission, meaning distorted, context misread, content not in the original,
word-for-word translation, idiom misread, formality, tone, pronoun, possessive, gender/number, terms, technical term,
abbreviation, culture, translated what should stay, sentence split, clause structure, word choice, repetitive style,
wordiness, word order copied, other; or no clear error) and `may_be_recognition_error`. The judge sees every line as
context and judges up to 20 lines per request (`CHUNK_LINES`, about a minute each), sending a long video's requests
three at a time; a failed request makes the whole check not measured. A Gemini model that takes longer than 120 s
(`DUBEVAL_JUDGE_TIMEOUT`) hands over to the next model at once, and a key whose daily requests are used up (free keys:
a few dozen a day per model) says so, with when it resets and what to do, instead of "busy".
The video's title goes along as its description.

**The judge** (`--judge`, or `DUBEVAL_JUDGE`): `auto` (default) takes the first available of **Claude**
(`claude-opus-5-5`, structured JSON output, medium effort, server-side refusal fallback; `ANTHROPIC_API_KEY`),
**Gemini** (`GEMINI_API_KEY`), and a **local model through Ollama** (`qwen3:8b` by default, `DUBEVAL_OLLAMA_URL`,
`DUBEVAL_OLLAMA_MODEL`; nothing leaves the computer). Use the same judge for every dub you compare; the report
names it. Before a local judge runs, the speech recognizer and the sentence model are unloaded so the judge fits
in the GPU (a model that spills onto the CPU takes many minutes); its context is sized to the prompt.

**The dub type** (`--dub-type`): `human` tells the judge that adapted jokes, idioms and cultural references are
intended localization; `ai_clone` and `ai_stock` are held to a close translation. Human and stock-voice dubs also
skip voice similarity (another voice is expected).

**Local judge, measured:** on the Francis EN→KO dub, `qwen3:8b` (English-only answers, ~50 s on an 8 GB laptop
GPU) reported missing content in 11 of 13 lines, nearly all wrongly, which made the verdict Poor. Treat its issues
as rough until Phase 5 checks it against labelled dubs; use Claude for reliable reviews.

Bands (`RUBRIC_FLAG` 6, `RUBRIC_POOR` 4, `RUBRIC_POOR_LINES` 3 in `report.py`): each row shows the average over the
lines and how many lines scored 6 or lower. **Meaning** is Poor when 3 or more lines, or most lines, score 4 or lower;
Check when any line scores 6 or lower (one or two serious lines included, still listed with their times); otherwise
Good. Until 2026-10-29 one serious line made meaning Poor; on 19 dubs graded by a person, a cut countdown or two
swapped sentences made dubs Poor that the person graded Good for meaning (`docs/validation.md`). The other four rows are Check when any line scores 6 or lower and never Poor, until labelled dubs show
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
  pace, the meaning screen and the translation check) is "not graded" instead of Poor. The translation judge and the
  meaning screen aren't even run on that speech: they would only grade recognition noise (two Uzbek dubs a person
  graded Good and Check scored 1 of 5). A confident third language, or the original's language, stays Poor (a real
  wrong-language dub).
- **No speech:** when the dub has no recognized speech at all while the original has (music, singing, noise), a "Speech
  found" row is **Poor**: nothing was dubbed. When the original has none, the row is Check: a person should watch it,
  because the speech checks couldn't run.

The first versions came from 7 labelled PersoDub pairs (agreement 3 → 5). On the 12-pair set of 2026-10-25 the
language row moved from Check to "not measured" (three Uzbek dubs graded Good were held at Check by it) and a dub
without speech from Check to Poor (the reviewer graded such a dub Poor).

## 6. The report and the verdict (`report.py`)
Every measure gets a level (good / check / poor / info / not measured), a one-sentence explanation and the thresholds used. **Verdict:** any Poor → Poor; otherwise any Check → Needs review; otherwise Good. Info (lip movement, speech offsets) and not-measured items never change it, and the report lists why each unmeasured item wasn't measured.

**How sure** (`report.sure_of`): DubEval says so when its own measurement is shaky, and the verdict follows.

| Not sure because | Measured as | Effect |
|---|---|---|
| little speech | the original speaks < 35% of the video (`SURE_SPEECH_SHARE`) | only distortion, same video, coverage, file, sound sync or speech found can make it Poor; else Needs review |
| too little speech | < 10 s of original speech (`SURE_SPEECH_SEC`) | same |
| unclear speech | the dub recognized confidently < 90% of its speech time (`SURE_CLARITY`) | same |
| background replaced | the dub's background (DNSMOS BAK) ≥ 2.0 cleaner than the original's (`BACKGROUND_REPLACED`) | silence and loudness are Check at most |
| words not checked | the dub's language wasn't recognized (`speech_problem` "unrecognized") | never Good |
| translation not checked | the translation check didn't run: no judge, an error, or turned off (a required check) | never Good |
| backup judge | a backup model judged the translation (`translation_judge.fallback`) | a note; no level changes |

The headline states each reason in plain words and asks the reader to listen. Set on 19 dubs a person graded:
agreement 11 → 13 of 19, all 5 graded Poor still Poor (`docs/validation.md`). There's deliberately no single 0–100 score: weights between these measures would be arbitrary and hard to defend.

## 7. Problem intervals (`intervals.py`)
(Pairing adds the `missing_in_dub` category: a part of the original that isn't in the dub, Check, Poor from 5 s, and `sound_sync`: the whole dub when its sound is 0.3 s or more
behind or ahead of its picture, Poor from 0.6 s.
Line timing adds `line_length` and `line_overrun`; see "Line by line" above.)
Every issue becomes a time range `{start, end, dub, category, severity (poor/check), check, description}`, in `report.problem_intervals`. Things to check are built from the same list.

| Category | Found by | Severity |
|---|---|---|
| `long_silence` | speech timing: original speaks, dub silent for ≥ 2 s | Poor from 4 s, else Check |
| `timing_mismatch` | speech timing: shorter one-track-only stretches of at least 0.8 s (`TIMING_MIN_SEC`; 0.5-0.8 s ones are word-timing jitter that validation saw come and go; they still count in the overlap score) | Check |
| `missing_speech` / `added_speech` | translation check | Poor if major, else Check |
| `mistranslation`, `names_numbers` | translation check | Poor if major, else Check |
| `translation_wording` | translation check (naturalness, context, terms, localization) | Check |
| `distortion` | clipped samples (`dubbed_clipping_intervals`, merged within 0.5 s) | Poor if the clipping row is Poor, else Check |
| `loudness_jump` | loudness envelope: dub vs original level, after removing their overall offset, differs by ≥ 10 dB for ≥ 1 s where both tracks have sound | Poor from 16 dB, else Check |
| `wrong_language` | Whisper language detection per 10 s window of the dub, windows overlapping by half (`dubbed_language_windows`; they widen so at most 120 are checked): the original's language at ≥ 50% while it leads the expected one by at least 0.3 (`LANG_SOURCE_LEAD`: an 8 s part left in a 10 s window keeps the dub's language near 0.3), or any other language at ≥ 80% while the expected one is < 20% (stricter: Whisper guesses odd languages on noise and music) | original's language: Poor from 80%; other language: Poor from 95%; else Check |
| `unclear_speech` | voice clarity: segments Whisper recognised with low confidence, at least 0.5 s long (`SLIVER_SEC`) | Check |
| `voice_change` | voice similarity: one line's dub voice much less like the original speaker than the rest | Check |
| `voice_quality` | voice quality: a ~9 s stretch where the dub scores below the original (SIG ≥ 0.6 or OVRL ≥ 0.5) | Poor from 1.0 / 0.9, else Check |

Rules: ranges of the same category that overlap or are less than 0.5 s apart merge (worst severity kept, `merged` counts them); ranges are clipped to the dub's length, rounded to 0.1 s and sorted by start. A translation issue lasts until the end of the original line starting closest to it (within 1 s; the judge quotes line start times), else the line containing it, else 2 s. Issues the judge flags as probable speech-recognition errors go to `report.possible_asr_errors` and never count, except a meaning issue scored 4 or lower: the judge can't tell a mishearing from a real error there, so it stays a Check interval ("listen to the line to tell") and makes meaning Check, never Poor. The prompt allows the flag only when a similar-sounding word explains the score, never for a changed, opposite or different-number phrase. `report.problem_seconds` is the time covered by at least one interval (overlaps count once). Intervals don't change the verdict, which comes from the measure levels; compare mode uses `problem_seconds` as a tie-breaker.

## 8. Calibrating the bands (`qa.py batch`)
Every band above is a starting point. To tune them on your own dubs: list share links with your verdict (`link,good|check|poor`), run `python qa.py batch links.txt`, and read the agreement line and the person × tool table. "Stricter than you" means the tool called a dub worse than you did; find which `<measure>_level` columns in `summary.csv` were Poor or Check on those rows, adjust that constant in `report.py` / `intervals.py`, and rerun. Reruns are cached (no downloads, no Whisper, no API calls), so each try takes seconds.

## Sanity warnings (`warnings` in results)
Raised automatically when:
- the duration differs by more than 20% (probably not a matching pair),
- the dub transcript is empty,
- the primary error rate is above 0.8 (probably the wrong script or language),
- lip movement couldn't be measured on the dub (the reason is included).

Each warning also appears under *Things to check* in the report.

### Dub language confirmed by its subtitle file
When a dub subtitle file is given, the dub's transcript (made in the dub's language) is compared with the file's text (`evaluate.subtitle_agreement`: 1 − character error rate, case, punctuation and spacing ignored; stored as `subtitle_match`). From `report.SUBTITLE_MATCH` (0.45) the dub is taken to be in that language: the Dub language row is Good whatever recognition guessed from the sound, speech-based checks stay graded (no "unrecognized" problem), and "another language" windows are dropped (the original's language heard in the dub is still reported). Measured on one real EN→UZ Perso dub: 0.61 against its Uzbek subtitles, 0.17-0.25 for unrelated text.
