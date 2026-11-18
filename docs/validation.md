# Validating DubEval

How we check that DubEval's results can be trusted, per language pair: what it catches, what it flags by mistake, and
how its verdicts compare with a person's. Back to the [README](../README.md).

## Two kinds of evidence

| | Real dubs graded by people | Known problems put into dubs |
|---|---|---|
| **Question** | Does DubEval's verdict match a person's? | Does each check catch its problem, and stay quiet otherwise? |
| **Command** | `qa.py batch testset.csv` | `dubeval validate testset.csv` |
| **Answer key** | A person's grades (`dubeval label`), never DubEval's | Known by construction: the problem, its kind and its time |
| **Limit** | Slow to grow; one reviewer's taste | Made-up problems are easier to catch than real ones |

Real graded dubs are the measure that counts. Known problems show each check's reach and its false alarms, quickly and
for any language.

## Known problems (`dubeval validate`)

Every dub in the sheet is copied as a **control** (its sound re-encoded, nothing else changed) and as one copy per
known problem. The control is evaluated first: each problem is then put where its speech recognition hears both the
original and the dub speaking, and away from any problem of the kind that would catch it that the control already
has (otherwise a catch would hide behind it). The control's problems are saved in `validation.json` (`controls`).
Places are on the original's timeline, as reports are, and are written into the dub at the matching moment when
DubEval finds the dub shifted or cut differently (`pairings` in `validation.json`). A pair whose dub was made from
another edit of the video measures that mismatch, not the checks: replace its original with the file that was dubbed. All copies are evaluated the same way (translation check off) and each is compared with the control,
so what DubEval already finds in the dub cancels out and any dub can be used, good or poor.

| Known problem | What is changed | Counts as caught |
|---|---|---|
| `silence_3s`, `silence_6s` | 3 or 6 s of the dub's speech made silent | a new long silence, timing gap or missing speech there |
| `original_voice_8s` | 8 s of the dub replaced by the original's sound | a new "wrong language" range there |
| `loudness_jump_3s` | 3 s made 14 dB louder | a new loudness jump (or distortion) there |
| `distortion_3s` | 3 s amplified until it clips | new distortion there |
| `noise_4s` | noise as loud as the voice over 4 s | a new noise, voice-quality or clarity problem there |
| `cut_4s` | 4 s cut from the picture and the sound | a new "missing from the dub" range there |
| `sound_late_1s` | the whole sound 1 s behind the picture | a new timing mismatch anywhere |
| `quieter_3db` (harmless) | the whole dub 3 dB quieter | nothing new: anything is a false alarm |

"There" means within 2 seconds of the changed stretch. Any new problem elsewhere is a **false alarm**. The report
gives counts (caught / tried), never percentages of a handful, the false alarms by kind, and every miss.

```bash
dubeval validate data/testset/testset.csv --out data/validation/run1            # every pair, every known problem
dubeval validate data/testset/testset.csv --only p006 --defects silence_3s,cut_4s
dubeval validate data/testset/testset.csv --split holdout                       # once per release, see below
```

## Results so far (2026-10-29, known problems)

English to Korean, Spanish and Uzbek dubs; counts are caught / tried. **Tune**: the 16 dubs thresholds were set on.
**Holdout**: 3 dubs of one video (Perso, ElevenLabs, Descript), never used to set anything, scored before and after.

| Known problem | Tune, before | Tune, sound fixes | Tune, final | Holdout, before | Holdout, sound fixes |
|---|---|---|---|---|---|
| Silence 3 s / 6 s | 5/11, 5/9 | 8/13, 6/10 | 8/13, 7/11 | 3/3, 3/3 | 3/3, 3/3 |
| Original voice left in (8 s) | 7/10 | 9/10 | 8/9 | 0/3 | 2/3 |
| Loudness jump | 13/13 | 14/14 | 13/15 | 2/3 | 2/3 |
| Distortion | 14/14 | 14/14 | 15/15 | 3/3 | 3/3 |
| Noise (4 s) | 4/14 | 6/14 | 3/15 | 0/3 | 0/3 |
| Cut (4 s) | 9/14 | 12/14 | 11/15 | 2/3 | 2/3 |
| Sound 1 s late | 10/16 | 14/16 | 14/16 | 1/3 | 3/3 |
| **All** | **67/101** | **83/105** | **79/109** | **14/24** | **18/24** |
| False alarms (new problems elsewhere) | 167 | 37 | 69 | 2 | 2 |
| Harmless copy (3 dB quieter) flagged | 10 of 16 | 6 of 16 | 6 of 16 | 0 of 3 | 0 of 3 |

"Before" is the tool as released in v0.1.1, with problems already placed on speech (`run4`); "sound fixes" adds the
voice filter, the line and timing margins, sound in sync and the language fix (`run8`, `holdout2`); "final" adds the
two speech-recognition fixes the comparison with a person found (below: lines kept when the other track speaks,
skipped speech recognized again; `run10`). The holdout was scored before those two, and has now been used: new
held-out dubs are needed for the next round. Small counts move by a few between runs when a problem lands elsewhere.

**The trade-off in the final column.** The two speech-recognition fixes made DubEval agree with a person on real dubs
(see below) but doubled the false alarms on the planted copies, almost all in two dubs: a mostly-music one (p019, 18)
and one with a shouted line over music (p012, 11). Recognizing skipped speech again gives slightly different lines on
each damaged copy, so line, timing and meaning flags move. They are listed moments, not verdicts, and Step 2 marks
the mostly-music dub "not sure". Real dubs count more than planted copies, so the fixes stay; making the second pass
steadier is the next thing to improve.

What changed, and why:
- **Recognized words over music and effects are dropped** (a voice detector, `evaluate.keep_voiced`): the recognizer
  invented lines there that changed from run to run, so transcript-based checks flagged problems that weren't there.
  False alarms 167 → 70.
- **A dub line is off only by at least 0.6 s** as well as 15% (was 0.3 s), and **timing mismatches shorter than 0.8 s,
  unclear speech or missing parts shorter than 0.5 s aren't listed**: word timings wobble by about that much. 70 → 34.
- **Sound in sync with the picture** (new): a dub's sound behind or ahead of its picture, from the background sound it
  keeps from the original. Sound 1 s late: 10/16 → 14/16 tune, 1/3 → 3/3 holdout, no false alarm.
- **Original voice left in**: language windows overlap by half, and the original's language counts when it leads the
  dub's by 0.3. 7/10 → 9/10 tune, 0/3 → 2/3 holdout, no false alarm.

Still weak: **noise** mixed in at the voice's level for 4 s (voice quality scores 9 s windows, and normal dubs dip as
much; fixed on 2026-11-02, below); **short silences** (3 s) on some dubs; the remaining false alarms are mostly the offline meaning screen and
single timing mismatches. The holdout has now been used once after the fixes: new held-out dubs are needed for the
next round. None of this replaces agreement with people on real dubs (below), which is still to do.

## Translation mistakes put into transcripts (2026-10-29)

The translation check reads the two transcripts, never the audio, so its known problems are planted in the text:
in real dub transcripts (3 English to Korean dubs, 2 English to Spanish), each copy got one **wrong number** ("35%" →
"75%"), one **reversed meaning** ("pay more" → "pay less", "don't be afraid" → "be afraid"), one **line left out** and
one **harmless rewording** (same meaning), each on a different line, written by hand; an unchanged copy is judged too.
Caught: the changed line is flagged (meaning 6 or lower); false alarm: a rewording, or an untouched line newly flagged.
Uzbek couldn't be tested: its dub transcript came out as nonsense characters, so there is no text to change.

| Planted mistake | Gemini (backup model, gemini-3.1-flash-lite) | Local model (qwen3:8b) | Gemma 3 4B (tried locally) |
|---|---|---|---|
| Wrong number | 6 of 6 | 0 of 6 | 0 of 6 |
| Reversed meaning | 9 of 9 | 2 of 9 | 0 of 9 |
| Line left out | 8 of 8 | 2 of 8 | 1 of 8 |
| **All** | **23 of 23** | **4 of 23** | **1 of 23** |
| Harmless rewording flagged | 0 of 9 | 0 of 9 | 0 of 9 |
| Untouched lines newly flagged | 0 and 2 (two runs; score moves of one point) | 0 | 0 |

Per language, Gemini: Korean 19 of 19, Spanish 4 of 4. Gemini's main model was busy throughout, so every answer came
from its backup model. One reversed meaning (Korean, "seek new experiences" → "avoid") was scored 1 to 2 out of 10
but marked "maybe misheard", which used to hide it from the report: a very low meaning line marked that way is now a
Check moment to listen to (`intervals._translation`, `report._rubric`), and the prompt allows the mark only when a
similar-sounding word explains it. On the 19 graded dubs that rule took agreement to 14 of 19 (an ElevenLabs dub's
wrongly translated country name had been set aside as a mishearing). **The local model misses most translation
mistakes**: it scored a removed line 7 out of 10. Use it for privacy, not for the meaning grade. Two other local
models were tried as replacements: Gemma 3 4B did worse (1 of 23), and Gemma 3 12B was stopped untested: on the test
computer (an 8 GB graphics card) it ran partly on the processor at about 3 words a second, several minutes per dub
check. Qwen3 8B stays the local model.

## A new local model: Gemma 4 12B (2026-11-13)

The October set was never saved, so a new one was written by hand the same way, on 8 real dub transcripts (6 English
to Korean, 2 English to Spanish; 233 lines over the 20 copies judged): 12 changed copies with 6 wrong numbers, 12
reversed meanings, 12 lines left out and 12 harmless rewordings (`tools/judge_planted_test.py`; the set is other
people's dubs and stays local). A changed line already flagged in the unchanged copy can't show a catch and isn't
counted, which is why the totals differ between judges. One run each.

| | Gemma 4 12B, Windows (8 GB NVIDIA) | Gemma 4 12B, Mac (M2 Pro) | Gemma 4 E4B, Windows | Gemini (reference) |
|---|---|---|---|---|
| Wrong number | 5 of 5 | 5 of 5 | 3 of 6 | 5 of 6 |
| Reversed meaning | 11 of 11 | 11 of 11 | 9 of 12 | 11 of 11 |
| Line left out | 12 of 12 | 12 of 12 | 0 of 12 | 11 of 11 |
| **All** | **28 of 28** | **28 of 28** | **12 of 30** | **27 of 28** |
| Harmless rewording flagged | 0 of 11 | 0 of 11 | 0 of 11 | 2 of 11 |
| Untouched lines newly flagged | 1 | 1 | 5 | 4 |
| Requests that failed | 0 | 0 | 0 | 1 (busy) |
| Time for the 233 lines | 2,601 s (11.2 s a line) | 1,590 s (6.8 s a line) | 832 s (3.6 s a line) | 1,387 s |

**Qwen3 8B gave no result on this set**: on the first transcript (6 lines) it wrote over 14,000 tokens without
finishing, and the run was stopped. **Gemma 4 12B became the local model** (`local_judge.MODEL`): the GGUF build
`gemma4:12b-it-q4_K_M`, 8.0 GB, about 6.9 GB of graphics memory while it runs; the registry's default `gemma4:12b`
asks for Ollama's MLX engine on a Mac, which DubEval's runtime leaves out. Gemma 4 E4B is faster but never noticed a
line that was left out, so it isn't offered as a smaller choice.

What this doesn't show: how it grades real dubs. These are planted mistakes, one run, two languages; it hasn't been
run on the graded test set against the reviewer's meaning labels, and Uzbek still has no readable transcript to test.

## Voice similarity without the quiet-background rule (2026-11-13)

Until now a line counted only where the original's background was quiet, which left 16 of the 20 test dubs without a
result. Three label-free tests on those dubs (all listed as voice-clone dubs), then one check by ear:

**1. Is the music the problem?** Five dubs, every line of 2 s or more, as recorded and with the voice separated from
the background first (Hybrid Demucs): 0.44 and 0.45, 0.21 and 0.21, 0.60 and 0.65, 0.23 and 0.24, 0.57 and 0.57. The
music wasn't changing the scores; the rule was hiding them.

**2. What do different voices score?** Each original's lines against the dub lines of a video with another original:
363 pairs, median 0.04, 90% under 0.16, 99% under 0.25, the highest 0.34.

**3. Does the model know the original's speakers?** Each original line against the other original line most like it
(the median is `original_self`):

| Dub (service) | Original with itself | Dub with the original | Reads as |
|---|---|---|---|
| p013 (Perso) | 0.75 | 0.61 | the same voice |
| p014 (ElevenLabs, the same original) | 0.75 | 0.59 | the same voice |
| p015 (Descript, the same original) | 0.75 | 0.08 | another voice |
| p022 | 0.81 | 0.60 | the same voice |
| p006 | 0.85 | 0.45 | the same voice |
| p018 | 0.72 | 0.22 | another voice |
| p011, p012 (one film clip) | 0.45 | 0.21, 0.22 | can't tell |
| p019 (3 lines) | 0.12 | 0.27 | can't tell |
| p009 (2 lines) | 0.51 | 0.46 | the same voice (a match that high needs no second proof) |

**The rule now** (`report.VOICE_SAME` 0.40, `VOICE_DIFFERENT` 0.30, `intervals.VOICE_KNOWN` 0.60): 40% or more is the
same voice; under that it is graded (another voice, or partly alike) only when the original matches itself at 60% or
more, and is otherwise not graded, with both numbers in the row. On the 20 test dubs, with nothing else measured
again: 12 graded (4 before), of them 10 the same voice and 2 another voice; 6 can't tell; 2 have fewer than two lines
of 2 s. No verdict changed. One earlier result fell away: p021 read 0.42 on the 2 lines the old rule let through, and
reads 0.08 over all 5 lines with an original that matches itself at only 0.32.

**By ear (2026-11-13).** The owner listened to the two dubs the rule calls "another voice", p015 (Descript) and
p018 (Perso), each next to its original, and found both a different voice from the original speaker: the rule was
right on both. Nobody has listened to the ten "same voice" dubs or the six "can't tell" ones.

**What this doesn't show.** Two answers by ear, both on the "another voice" side. Ten dubs set the bands. Voice separation was also tried for voice quality on the same five dubs: it
gave every dub a grade (5 of 5, against 3), but removed a simulated robotic voice (0 of 5 caught, against 2 of 2 as
recorded) and changed two answers, so it wasn't adopted.

## A voice-quality model for speech over music: Audiobox Aesthetics (2026-11-13)

DNSMOS left 8 of the 20 test dubs without a voice-quality grade (the original's own voice scored under 1.6 of 5 over
its music) and its scores moved by more than 2 points within one dub. Three tests, none with a person's labels:

**1. Next to DNSMOS, five dubs** (one clean, four with music), 8 s of damage in one stretch of each. "Noticed": the
score fell by 3 or more times its usual movement between stretches of the undamaged dub.

| | DNSMOS (speech score) | Audiobox (production quality) |
|---|---|---|
| Movement of "dub minus original" between undamaged stretches | 0.09 clean, 0.55-0.87 with music (of 5) | 0.14-0.30 (of 10) |
| Robotic voice (quantised to 16 levels) noticed | 1 of 5 | 4 of 5 (5 of 5 on its second score) |
| Muffled voice (low-passed at 2 kHz) noticed | 0 of 5 | 5 of 5 |
| Clipped voice (driven 8x into the limit) noticed | 0 of 5 | 5 of 5 |

**2. Bands, all 20 dubs**, with the graph DubEval ships. Over 329 undamaged stretches the dub's production quality
was at most 0.83 below the original's and under 0.8 below its own usual; its second score at most 1.0 below its usual.
With the bands chosen (1.0 below the original or below the dub's usual, or 1.2 on the second score):

| Damage (8 s in one stretch of each dub) | Caught |
|---|---|
| Robotic, 16 levels | 20 of 20 |
| Robotic, 32 levels | 14 of 20 |
| Muffled, low-passed at 2 kHz | 17 of 20 |
| Muffled, low-passed at 4 kHz | 2 of 20 |
| Clipped, 8x | 17 of 20 |
| Clipped, 3x | 0 of 20 |
| Undamaged stretches flagged | 0 of 329 |

**3. The 20 dubs as they are**, voice quality alone measured again: Audiobox grades 20 of 20 (DNSMOS 12), every one
Good. The two dubs DNSMOS marked Needs review (p019, p022) are Good; on p022 the reviewer's last votes on both
DNSMOS moments were "false alarm". No verdict changed.

**What this doesn't show.** The bands were chosen on the same 20 dubs that show no false alarm, so the margin is
thin (at 0.6 below the dub's usual, 7 undamaged stretches would be flagged). The damage is artificial and strong; mild
damage is mostly missed, and no real dub with a bad voice has been tested. Poor (2.5) is a first guess. On a laptop
processor it takes about 0.25 s per stretch, about 20 s per minute of video.

## The 20 test dubs with everything of 2026-11-13 together

One full run of the test set after the day's changes (the reports' new layout, no lip-movement estimate, Gemma 4 12B
as the judge, the new voice similarity, Audiobox Aesthetics for voice quality), against the run of 2026-11-12, whose
judge was Gemini. 40 minutes on an 8 GB NVIDIA laptop; no request of the local judge failed.

| | 2026-11-12 (Gemini) | 2026-11-13 (Gemma 4 12B, local) |
|---|---|---|
| Verdict the same as the reviewer's | 12 of 20 (5 stricter, 3 gentler) | 14 of 20 (5 stricter, 1 gentler) |
| Meaning grade the same as the reviewer's meaning label | 4 of 16 (8 stricter, 4 gentler) | 7 of 16 (8 stricter, 1 gentler) |
| Line length the same as the reviewer's length label | 7 of 15 | 7 of 15 |
| Voice quality graded | 12 of 20 | 20 of 20 |
| Voice similarity graded | 4 of 20 | 12 of 20 |

Both verdicts that changed (p002, p003: Needs review to Poor, as the reviewer has them) came from the judge: Gemma
graded their meaning Poor where Gemini had said Needs review. No verdict changed because of a voice measure. Never
Good against Poor in either run.

**Still wrong, the same way as before.** On 8 of the 16 dubs with a readable transcript the meaning grade is stricter
than the reviewer's (the reviewer says the meaning is good, the judge flags lines), with either judge; one of them,
p021, is Poor to the tool and Needs review to the reviewer for that reason alone. The four Uzbek dubs still have no
readable transcript, so three dubs the reviewer calls Good can't be called Good. One short dub the reviewer calls Poor
(p005, 6.7 s of speech) stays Needs review.

## Why the translation check is stricter than the reviewer (2026-11-13)

On 8 of the 16 dubs with a readable transcript the meaning grade is stricter than the reviewer's label, with Gemini
and with Gemma alike. Gemma flags 27 lines on those 8 dubs (39 on all 16). Each was read, and then recognized a
second time on its own with the small recognizer (`data/validation/judge_strictness/`, local):

| The 27 flagged lines | Lines | A second recognition |
|---|---|---|
| One side has no speech (the dub "left out" or "added" a line) | 9 | found speech on the silent side on 7 |
| Both sides speak, and the words change when recognized again | 12 | e.g. `대경 잡으려고` became `배경 잡으려고`, the right translation |
| Both sides speak, the words are stable | 6 | 3 are fair translations the judge marked down, 2 hide one misheard key word, 1 is a countdown cut short both times |

So about 21 of the 27 flags come from speech recognition, about 3 from the judge being strict with a fair
translation, and at most 2 are translation errors a person might accept as such. The judge marked none of the 27 as
possibly misheard, though several hold words that aren't words (`과일 백스탄`, `비념`, `틀라이들`).

**Two simple rules were tried and rejected** (the grade recomputed from the saved scores): leaving one-sided lines out
of the grade, and counting them only where the voice detector agrees that one track is silent. Both lower agreement
with the reviewer from 7 to 6 of 16, because the same kind of line is what marks the dubs the reviewer calls Poor
(p001, p002).

A second recognition of each flagged line before it counts was built next and didn't help (below). The "about 21 of
27" above was too confident: words that change on a second recognition don't show that the second reading is right.

## A second listen for flagged lines: built, measured, left off (2026-11-15)

**What it does** (`pipeline.listen_again`, off unless `DUBEVAL_SECOND_LISTEN` names a recognizer): every line the judge
scores 6 or lower is recognized again on its own, both tracks, 0.4 s wider than the line; where the words differ, the
same judge reads the line once more, and the line takes the second judgement only when that one keeps the meaning
(above 6) and is better overall. A cleared line is listed with the possibly misheard ones, with both readings.

**Measured** on the saved run of 2026-11-13 (Gemma 4 12B; 40 flagged lines on 14 of the 16 judged dubs):

| Second listen with | Heard differently | Cleared | Meaning grade the same as the reviewer's (was 7 of 16) |
|---|---|---|---|
| `base`, on the processor | 34 of 40 | 4 | 5 of 16 |
| `large-v3-turbo` (the run's own recognizer) | 37 of 40 | 9 | 7 of 16 (p006 right now, p002 wrong now) |

With `base`, two verdicts the tool had right become wrong (p001, p002: Poor to Needs review; the reviewer says Poor), so
verdict agreement would fall from 14 to 12 of 20. With either recognizer p019 and p021 stay Poor for meaning.

**Why it doesn't work:**

- **A line heard alone often comes out as other wrong words.** `My flight suit.` against a silent dub came back as
  `어.. 이 개쇼..` (`base`) and `읍! 기칫!` (large). Short clips also draw the recognizer's stock phrases
  (`다음 영상에서 만나요.`, `감사합니다.`, `I'll see you next time.`). Two wrong readings can even agree: `size?` against a
  silent dub came back from `base` as `Bye!` and `빠이빠이`, and the line was cleared.
- **It can hide a real error.** p002's dub leaves a line in English. Told the line is Korean, the large recognizer
  wrote it out in Korean (`정말. 더 더? 댓글에 남겨주세요.`): an untranslated line read as a translation.
- **The judge isn't steady.** Asked again about nearly the same words, Gemma moved a line from 7 to 4 (p001), and gave
  10 to a dub line whose original side was still silent (p001: that clear is what took the verdict off Poor).
- **Where it is right, it removes what made the grade right.** p002's dub does say `네` where the first reading heard
  nothing (both recognizers agree). Without that false "left out" line the dub has one serious line, the untranslated
  one, and the rule needs three (or most lines) for Poor.

The large recognizer's nine clears read as real corrections (`새로운 맛` for "new tastes" where the original was first
heard as "new cases"; `넣자` for `놓자`; a dub line the first reading had cut short), but they change no grade the
reviewer disagrees with except p006.

**What the labels can and can't settle.** On these 20 dubs the stricter meaning grade changes one verdict only (p021);
the other dubs where it is stricter are Needs review to the reviewer for other reasons. Recomputed from the saved
scores, a line flag at 5 or 4 instead of 6 changes no verdict (14 of 20 each time) and moves the meaning grade to 8
and 10 of 16. Sixteen dub-level labels can't tell a right line from a wrong one: the next step is the reviewer's
answer on the flagged lines themselves (real problem or false alarm, by ear), then any rule can be scored on lines.

**The line review** (`tools/label_lines.py`, prepared 2026-11-15, not answered yet): the 40 lines the check marked
down in that run and 20 it passed (picked at random, fixed seed), from 16 dubs. The page plays the same moment of the
original and of the dub and asks three things per line: is the original written down right, is the dub written down
right, and does the dub say what the original says. It doesn't say which lines were marked down, and shows the judge's
scores for a line only after the three answers. The sheet and clips stay local (`data/validation/line_review/`).

## Other recognizers for the languages Whisper reads badly (2026-11-15)

Two small tests, nothing changed in DubEval. There is no Uzbek script to score against, so the number is the offline
meaning model's similarity between each dub line and the original's words at that time (higher is better), next to a
reading of the text. Scripts and transcripts: `data/validation/uzbek_recognition/`, `data/validation/omnilingual/`.

**Whisper models trained on Uzbek** (CTranslate2, loaded by the recognizer DubEval has), the four Uzbek dubs, whole track:

| Model | Size | Meaning against the original | Reading |
|---|---|---|---|
| Whisper `large-v3-turbo` (today) | 1.6 GB | 0.61 | guesses Kazakh, Azerbaijani or Persian; `Bugim Rosso sooqa` |
| rubaistt v2 medium (`islomov/rubaistt_v2_medium`, Apache-2.0) | 1.5 GB | 0.76 | `bugun rosa sovuq a? ha, ancha salqin ekan.` |
| Kotib `uzbek_stt_v1` (Apache-2.0) | 3.1 GB | 0.79 | nearly the same text as rubaistt |
| UniVoice (Apache-2.0) | 0.8 GB | 0.78 | no punctuation; skipped 20 s of one dub |
| Whisper turbo trained on Uzbek (MIT) | 1.6 GB | 0.72 | more mistakes, one runaway repetition |

They return one block of text per 30 s, not lines, and can't tell which language is spoken. Splitting their timed words
into sentences at `. ? !` gave lines that sat on detected speech (95 to 98% of their time with rubaistt, 75% on two
dubs with Kotib) and paired with the original's lines. Not checked by a person who reads Uzbek, and three of the four
dubs are one video.

**Meta's Omnilingual ASR** (1,600+ languages, Apache-2.0), its CTC models as ONNX on the processor, against Whisper on
the same stretches of speech (cut at pauses), 10 dubs:

| Dub language | Whisper `large-v3-turbo` | Omnilingual CTC 300M | Omnilingual CTC 1B | Trained on the language |
|---|---|---|---|---|
| Korean (4 dubs) | 0.78 | 0.70 | 0.73 | |
| Spanish (2) | 0.79 | 0.74 | 0.72 | |
| Uzbek (4) | 0.67 | 0.63 | 0.68 | 0.76 (rubaistt) |

The CTC models write what they hear letter by letter, with no punctuation and no knowledge of the language: Korean
comes out misspelled (`우주백키스탄에서운`, `공확`), Uzbek in mixed Latin and Cyrillic letters, short sounds as Chinese or
Arabic characters. They don't invent text over a short noise, where Whisper wrote `Gracias por ver el video.` Speed on
this laptop's processor: 499 s of sound in 35 s (300M) and 87 s (1B). **Not tested:** the LLM versions, which are told
the language and carry Meta's best numbers; the smallest is about 6.5 GB and needs PyTorch or its own decoding loop.

## Today's recognizers, language by language (2026-11-15)

Whisper `large-v3-turbo` (GPU) and `base` on 25 read sentences per language from FLEURS (Google, CC BY 4.0), 36
languages, scored against the sentences' own text: the share of characters read wrong with the language given (lower
case, no punctuation), and how often the model names the clip's language by itself. Scripts and numbers:
`data/validation/languages/`.

| Wrong characters, language given | `large-v3-turbo` | `base` |
|---|---|---|
| Under 5% | 22 languages: Spanish 0.4, Italian 0.6, German 0.8, Russian 1.1, Dutch 1.2, Portuguese 1.3, Polish 1.7, Turkish 2.1, Malay 2.2, Indonesian 2.3, Ukrainian 2.3, French 2.5, English 2.6, Romanian 2.9, Arabic 3.1, Korean 3.4, Swedish 3.4, Vietnamese 3.7, Greek 3.9, Czech 4.3, Tagalog 4.7, Japanese 4.9 | 4: Spanish 2.4, English 4.2, Italian 4.6, German 4.7 |
| 5 to 10% | 7: Persian 5.1, Kazakh 5.7, Hungarian 5.8, Urdu 8.0, Chinese 8.9, Swahili 9.1, Hindi 9.5 | 7: Portuguese 5.3, Russian 5.4, Turkish 7.4, Polish 8.5, Indonesian 9.4, Malay 9.6, Korean 9.9 |
| Over 10% | 7: Azerbaijani 11.0, Thai 12.9, Hebrew 14.7, Mongolian 37.4, Bengali 38.9, Tamil 39.5, Uzbek 82.5 | 25, from Ukrainian 10.3 and French 10.9 to Hindi, Bengali and Mongolian near 100 |

**Naming the language.** `large-v3-turbo` names every clip right in 29 of the 36 languages, `base` in 18. The large
model never names Uzbek (0 of 25: Kazakh 16, Tibetan 8) or Mongolian (0 of 25), names Bengali on 3 of 25 (Hindi,
Gujarati), and mixes neighbours: Malay as Indonesian (6), Urdu as Hindi (6), Hindi as Urdu (4). Told a clip is Uzbek,
it still writes it in Cyrillic letters with Kazakh spelling, which is most of the 82.5%.

**In the report.** A dub or original in a language the model used read more than 10% wrong here gets a note under
the verdict (`report.WEAK_RECOGNITION_PCT`, `languages.RECOGNITION_ERRORS`), with a pointer to the large model when
that one reads the language well. It grades nothing.

**What this doesn't show.** Read sentences in a quiet room are easier than a dub with music. 25 clips a language is a
rough number, the first clips of each archive come from few speakers, numbers written as digits count as errors
against spelled-out text, and scoring by characters is strict for scripts with several spellings of one sound.

## The large recognizer without a graphics card (2026-11-15)

Until this test `large-v3-turbo` was used only with an NVIDIA card and everyone else got `base`, which read 4 of 36
languages well (above). After it, the large model is the default wherever it is downloaded (`asr.pick_default`). Timed on this laptop's processor (Intel Core Ultra 7 255H, 16 cores, 8-bit, a 96 s Korean track):

| Model, where | Seconds per minute of sound | Times faster than real time |
|---|---|---|
| `base`, processor | 5 | 12.7 |
| `large-v3-turbo`, processor, 4 threads (the default) | 18 | 3.4 |
| `large-v3-turbo`, processor, 8 threads | 16 | 3.8 |
| `large-v3-turbo`, processor, 16 threads | 19 | 3.1 |

A whole evaluation of a 29 s dub on the processor (translation check off) took 79 s with the large model and 30 s with
`base`: recognition runs on both tracks and again for the language and for skipped stretches. It reads as well on
the processor as on the card on three of four languages tried (25 FLEURS sentences each, wrong characters, processor
against card): Arabic 3.2 / 3.1, French 2.4 / 2.5, Japanese 4.9 / 4.9. Korean read 7.3 against 3.4: one sentence of
the 25 was cut short at 8-bit precision; at full precision Korean read 3.8, 1.7 times slower. `base` reads Korean at
9.9. **Not measured:** the Mac (it wasn't reachable) and an older or smaller processor.
Scripts: `data/validation/speed/`.

## Lip sync (2026-10-29)

The lip-sync check (StableSyncNet, `dubeval/lip_sync.py`) on p022, a real Perso English to Korean dub the reviewer
graded Good, which Perso delivers both lip-synced and plain. Each row compares the original's first 60 s with
another track at the same 30 moments; the delayed copies are the original with silence put before its sound.

| Compared with the original | Lines up (of 30) | The original (of 30) | Sound offset found |
|---|---|---|---|
| Perso's lip-synced dub | 26 | 28 | none (0 s) |
| The same dub without lip sync | 6 (chance is about 5) | 29 | none: the lips don't follow |
| The original, sound 0.2 s late | 0 | 29 | 0.20 s late |
| The original, sound 0.5 s late | 0 | 29 | 0.48 s late (40 ms steps) |
| The original, sound 1 s late | 0 | 29 | none: beyond the ±0.6 s search |

So the check tells a lip-synced dub from a plain one and measures a delay to the frame, and a delay beyond its reach
still shows as lips that don't line up (the sound-sync check measures those, up to 2 s). One video, one face, one
language pair. Since 2026-11-10 it counts in the verdict anyway (the owner's decision: 90% of moments lined up is Good,
30% or less Poor); on this video the lip-synced dub (84%) would be Check and the plain one (16%) Poor. Graded
lip-synced dubs, ideally with another face and language, should still confirm those bands. Before the speed work the same check took about 4 minutes per dub on this computer's processor; it now takes
about 30 s (30 moments at most, faces found only where needed, a coarse-to-fine shift search, busy-waiting off).

## Agreement with a person (2026-10-29)

One reviewer graded 19 real dubs (English to Korean, Uzbek and Spanish; Perso, ElevenLabs, Descript) on the review
page before seeing DubEval's results; `qa.py batch` then compared DubEval's verdict with theirs. Counts, not
percentages: 19 dubs and one person's taste say which way to look, not how good DubEval is.

| | DubEval Good | DubEval Check | DubEval Poor |
|---|---|---|---|
| Person: Good (4) | 2 | 1 | 1 |
| Person: Check (10) | 2 | 5 | 3 |
| Person: Poor (5) | 0 | 1 | 4 |

Agreement went from **7 to 11 of 19** with two fixes the comparison found:
- **Lines lost by speech recognition.** A shouted line over loud effects was dropped on one side only, or the
  recognizer skipped 15 s of real lines after loud music; the translation check then saw lines "invented" or "left
  out". Dropped lines the voice detector half hears are kept when the other track speaks then, and skipped speech is
  recognized again (`evaluate.keep_voiced`, `evaluate.fill_gaps`).
- **One serious line no longer makes meaning Poor**: Poor needs 3 serious lines or most lines (a cut countdown, two
  swapped sentences or "IELTS" heard as "IH" made dubs Poor that the person graded Good for meaning).

**Step 2 (how sure DubEval is) then took it to 13 of 19**: a mostly-music dub (speech 27% of the video) and a dub
whose background music was removed are Needs review instead of Poor, and a dub whose words couldn't be recognized is
Needs review instead of Good (one of those the person graded Good: DubEval no longer claims what it didn't check).

Still apart, each on one or two dubs (not changed until more dubs are graded): an overall level 5 dB off the original
is Poor (the person: Good); a Descript dub with its background music removed is Poor for silence; DubEval is gentler
on a sung music video and a 7 s clip the person graded Poor. **The translation check isn't repeatable** when Gemini
falls back to a smaller model under load (one dub's meaning score went 9.7 → 7.3 on the same transcripts): pin the
model or use the local judge for calibration runs. Next: a second reviewer, and about 20 English to Korean dubs.

## Quick wins (2026-11-01)

The four quick wins, measured on the 20 graded dubs by grading the saved measurements of two runs (2026-10-29 and
2026-11-01, the same dubs) with the old and the new rules. The thresholds moved on tune dubs only (p008, p019, p022).

| | Run of 2026-10-29 | Run of 2026-11-01 |
|---|---|---|
| Agreement with the person, old rules → new rules | 14 → 14 of 20 | 11 → 11 of 20 |
| Graded Good, DubEval Poor | 2 → 0 | 2 → 0 |
| Graded Poor, DubEval Poor | 4 → 4 of 5 | 2 → 2 of 5 |

- **Loudness:** Good within 3 dB, Check within 6 (was 2 / 4). A dub 5.1 dB off that the person graded Good (p008) is
  Needs review instead of Poor; no dub graded Poor was more than 1.7 dB off.
- **Voice quality:** Poor from 2.5 / 1.5 below the original (was 1.0 / 0.9). The only two dubs that reached the old
  Poor were graded Good (p022, now Needs review) and Needs review (p019); both reviewer votes on those windows were
  false alarms.
- **Meaning screen:** information only when the translation check ran. Five dubs lost a Check row; no verdict changed,
  because the judge's rows already set it.
- **Numbers check (new, offline):** 5 lines on 3 dubs had numbers in digits on both sides; no false alarm. A changed
  number planted in each of those lines was caught 5 of 5 (one is "35%" → "75%", the wrong number the local judge
  missed 0 of 6 times). It can't read numbers said as words: 5 dub lines wrote digits where the original's transcript
  had words ("four, three, two, one"), and those aren't compared. Changed before release (2026-11-03): a code review showed
  that a correct "July 4" → "7월 4일" or "2 million" → "200만" would be flagged, so it now flags only a number replaced by
  another and compares significant digits. On the graded dubs that removes the one flag left (p010, a garbled transcript) and
  still catches 6 of 6 planted wrong numbers on the 6 lines compared. It now misses a number wrong only by its zeros.
- **Translation check pinned:** Gemini's `gemini-flash-latest` alias is out of the chain, a dub's requests stay with
  the model of its first one, and locking the model (`DUBEVAL_JUDGE_PIN=1`, later also `--lock-model`) uses only the first one. Why it matters: with the same rules,
  the two runs disagree on 8 dubs' translation rows and 3 verdicts (p002, p003, p021); 7 of the 8 were judged by a
  different model in each run (the eighth, by the same one, moved one row a band). On 2026-11-01, 9 of the 16 judged dubs got a backup model (three model versions answered
  in one run). That alone moved agreement from 14 to 11. A pinned run of the graded set is still to do: the first try
  (2026-11-01) judged none of the 16 dubs, because the free key's daily requests for the first model were already
  used up by that day's runs. A pinned run needs a fresh day's requests or a key with billing.

Still apart on 2026-11-01: three dubs graded Poor are Needs review (two whose meaning grade depends on which model
answered, p002 and p003, both Poor on 2026-10-29; and a 7 s clip with too little speech to be sure, p005); two graded
Needs review are Poor (p006: 4 of its 10 lines run much longer or shorter than the original's; p021: a meaning grade
that depends on the model); and the Uzbek dubs graded Good stay Needs review, because their words couldn't be
recognized.

## False alarms: timing moments (2026-11-02)

Timing moments come from recognized word timings, and a small change anywhere in a file can shift those all over it. A
voice detector (fine settings, `asr.voice_activity(fine=True)`) now has to agree that one track speaks and the other
doesn't. Measured on the 17 tune dubs (the holdout wasn't used), with the same copies evaluated before and after:

| | Before | After |
|---|---|---|
| Known problems caught | 80 of 112 | 80 of 112 (the same ones) |
| False alarms | 65 | 53 |
| of which timing and silence | 18 | 6 |
| Harmless copy flagged | 5 of 17 | 5 of 17 |

No other kind of false alarm moved, copy by copy, so the difference is this change and not recognition varying between
runs. Three of the six timing false alarms left are in one cut copy (p012).

**A person's votes agree.** With the new code, all 5 moments on p001, p020 and p022 voted real are still flagged, and
the one voted a false alarm (p020 at 28.6 s) is gone. One false-alarm vote is thin evidence; more votes would firm it up.
Two older p001 votes (at 3.0 s and 17.4 s, tool version 0.1.0) were already not flagged before this change.

**Real dubs:** on the 20 graded dubs, 7 of the 27 timing and silence moments go (estimated from the saved results of
2026-11-01 with the detector's answer at each moment). No verdict or row level changes: the overlap score stays on the
words, so agreement stays where it was. Compare mode's tie-breaker, problem time, can move slightly.

**The first version was wrong, and only the votes showed it.** It used the detector's default settings, which ignore
silences under 2 s and pad speech by 0.4 s. The test looked excellent, because its planted silences are all 3 s or
longer, but it removed short gaps a person had voted real. Known-problem results alone can't judge a change like this.

What's left: meaning similarity 19 (only reports moments when no translation check ran), line length 12, missing from
the dub 5, voice quality 5, unclear speech 3, line overrun 2, loudness jump 1, timing and silence 6.

## Silences in dubs recognition can't read (2026-11-02)

When recognition can't make out a dub's language, its words aren't graded, so silences went unnoticed too: 0 of 8 planted
in the four English to Uzbek dubs. The voice detector doesn't need the words (`evaluate.voice_gaps`). Where it hears the
dub silent and the original speak for at least 2 s in total, the report lists a long silence, as on any other dub. It's a
moment to listen to: the verdict still comes from the rows, and the words still aren't graded.

| The 4 Uzbek dubs, same copies | Before | After |
|---|---|---|
| Planted silences caught | 0 of 8 | 8 of 8 |
| All known problems caught | 16 of 31 | 24 of 31 |
| False alarms | 3 | 3 |
| Harmless copy flagged | 0 of 4 | 0 of 4 |

No catch was lost, and the original Uzbek dubs get no new moment. That takes the 17 tune dubs to **88 of 112** caught. All
of this is on the tune dubs; the holdout wasn't used and its 18 of 24 is from before these changes.

**A wider check of the rule.** The detector alone, on all 17 dubs (cut copies left out, their timeline differs): 26 of 26
planted silences, against 17 of 26 from the words, and nothing on the harmless copies. On the clean copies it finds two
gaps, both beside moments the words find too (p019 at 78.5 s, p011 at 8.8 s). One extra find elsewhere, on p019's "sound
1 s late" copy, a mostly-music dub whose whole soundtrack moved. It still runs only where the words can't be read: on the
other dubs it would add one catch (a 7 s clip, p005) for a second source of moments.

**The first rule missed 3 of the 8.** It looked for stretches of "original voiced, dub not", joining breaks up to 0.3 s,
and the original's own pauses of 0.3-0.45 s between phrases split a silence into pieces too short to flag. So the rule
counts the original's speech inside the dub's silence instead. **Limit:** these are silences made by muting a stretch of
the dub. No real missing line in an unreadable dub has been seen yet, and a dub with loud sound over the gap may read as
voiced.

## Partial translation reviews and the model used (2026-11-02)

A reviewer's test with made-up judge answers found that a review covering 1 of 3 lines still came out measured, 10 of
10, with the whole verdict Good. Now only the lines a request asked about count, lines left out are asked about once
more, and any still unanswered make the check not measured, saying how much was evaluated. In the saved runs this had
not happened yet: **0 of 60** reviews (Gemini and the local model) left a line out, so no past verdict changes.

The same review found that a result named only the first request's model, so the result now keeps which model judged
which lines, and a comparison says when different models judged its dubs. These checks are about the logic; they don't
show how accurate the translation check is.

**With real Gemini, on one short video** (two 28 s dubs of 6 lines, English to Korean, 2026-11-02; 10 requests):

- **The lock.** A locked comparison finished on the first model with no backup, 6 of 6 lines on both dubs.
- **A skipped line.** Gemini answered for real, and one line was removed from its answer on the way back. Asking again
  recovered it with real scores. Removed every time, the grade was withheld ("evaluated only 5 of 6 lines") and the
  comparison became provisional. A real answer that skips a line on its own still hasn't been seen.
- **A name doesn't fix the version.** Asked for `gemini-3.5-flash`, Google answered as `gemini-3.6-flash`. The result
  now keeps both, and a comparison calls out different answering models.
- **Reviewing the same transcripts again**, same model, temperature 0:

| | Meaning out of 10, four reviews | Row levels and verdict |
|---|---|---|
| Dub A | 10.0, 10.0, 9.8, 9.8 | the same every time (Good) |
| Dub B | 8.3, 8.7, 8.2, 8.0 | the same every time (Needs review) |

So locking removes model switching, but the scores still move, by up to 0.7 on this short dub (individual line scores by
up to 3): a small gap in meaning score, which decides a comparison under rule 6, can be noise. The first of the four
reviews is the unlocked one of 2026-10-30, which got the same model. Two dubs of 6 lines say which way to look, not how
steady the check is; the graded set hasn't been run locked yet.

## Bursts of noise (2026-11-02)

Noise was the weakest check: voice quality scores 9 s windows, so a 4 s burst got averaged away. A new check follows the
spectrum's floor against the dub's own usual level and the original at the same moment (`docs/metrics.md`, Noise).

| | Before | After |
|---|---|---|
| Planted noise caught (17 tune dubs) | 1 of 15 | **15 of 15** |
| All known problems caught | 88 of 112 | **102 of 112** |
| False alarms | 53 | 53 (none new) |
| Harmless copy flagged | 5 of 17 | 5 of 17 |
| Held-out dubs, which played no part in setting the rule: noise caught | 0 of 3 | 3 of 3, no false alarm |
| Real dubs flagged (20 graded, 2 more) | | **0 of 22**, so no verdict changes |

The totals come from running the real check on every saved copy and adding it to the last results; 34 copies of 4 dubs
were then evaluated through the whole pipeline, and all 34 agreed. The rule was set on the tune dubs only. (The first full run
of all copies, on 2026-11-03, found 2 noise false alarms on cut copies that this estimate missed.)

To see whether it was built only for this test, other noise was added to the tune dubs too:

| Noise added for 4 s | Caught |
|---|---|
| The test's noise 6 dB quieter, and 12 dB quieter | 14 of 15, 13 of 15 |
| Pink noise | 14 of 15 |
| The test's noise for only 2 s | 15 of 15 |
| High-pitched hiss only (4-8 kHz) | 6 of 15 |
| Buzz, hum, crackle | 1, 0 and 0 of 15 |

**Limits:** all of this noise was made for the test, and no real dub has shown any yet, so a real catch hasn't been seen.
Hum, buzz, crackle, bursts under 1.5 s and noise across a whole dub aren't found.

## Line length on mostly-music videos (2026-11-02)

12 of the 53 false alarms were lines flagged as too long or too short, the biggest source left that also shows when the
translation check runs. 7 of the 12 were on one dub, p019, where speech fills 27% of the video: word timings over music move
with any change in the sound. On a mostly-music video (`little_speech`), line length and overruns are now "not graded", with
the reason, and list no moments.

| | Before | After |
|---|---|---|
| Line-length false alarms | 12 | 5 |
| All false alarms | 53 | 46 |
| Known problems caught | 102 of 112 | 102 of 112 |
| Agreement with the person | 11 and 14 of 20 | the same, with the same verdict on every dub (before the Poor line below) |

p019's copies were evaluated again through the whole pipeline: its line-length false alarms went from 7 to 0, with no catch
lost. Three other false alarms on p019 went too, but recognition can vary between runs, so they aren't counted above.

**What didn't work: asking the voice detector.** It fixed timing moments, so it was tried here first, and it doesn't help.
On real dubs it mostly agrees with the words: p006's flagged lines measure 12-28% shorter by the detector too, so those
lines really are shorter. At the only settings that keep the lines a person voted real, it removed 3 of the 7 false alarms
that could be checked. Slightly looser settings removed a line voted real (p022 at 50.8 s), and on p019 the detector reads
+338%, which means nothing over music.

**The Poor line moved too.** p006 was Poor only because 4 of its 10 lines were off, where the person said Needs review. The
measurement looks right, so the question was how strict to be: line length is now Poor below 50% of lines fitting, not 70%,
so it takes most lines off, as meaning does. p006 is the only graded dub this changes, and agreement goes from 11 to 12 and
from 14 to 15 of 20 on the two runs. That rests on one dub and one reviewer, and it was fitted to that dub, so read the extra
match as a correction to check on more dubs, not as proof that DubEval got more accurate.

## Does one model repeat itself? (2026-11-02, not finished)

To see whether verdicts repeat with the model locked, the graded set was run twice with Gemini's first model only. **The runs
didn't finish.** A free key allows 20 requests a day per model (Google's own error: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
limit 20, on `gemini-3.6-flash`, which is what `gemini-3.5-flash` counts as), and two runs need about 36. Only 7 dubs were
reviewed in the first run and 4 in the second, and just 2 in both, so the runs' own agreement figures mean little. The lock
itself held: all 11 reviews came from the first model, with no backup.

Reviews saved from other runs fill part of the gap: the same model on identical transcripts, with today's prompt.

| Dub | Person | Meaning out of 10, each review | Verdict |
|---|---|---|---|
| p002 | Poor | 5.0, 4.2 | **Needs review, then Poor** |
| p003 | Poor | 4.5, 5.2, 4.5 | Needs review every time |
| p006 | Needs review | 9.2, 8.6 | Needs review both times |
| p018 | Needs review | 9.2, 9.0 | Needs review both times |
| self-intro (2 dubs) | not graded | 10.0, 10.0, 9.8, 9.8 and 8.3, 8.7, 8.2, 8.0 | the same every time |

So on 1 of these 6 dubs the verdict flipped with nothing changed. On p002 one line scored 5 out of 10 in one review and 1 in
the other, which crossed the "3 serious lines" rule for Poor. Reviews from 2026-10-29 may have used an earlier prompt, so they
aren't in the table, but they point the same way: p001 went between Poor and Needs review, and p015's meaning row between Good
and Check.

**What this means:** locking removes one cause of the swing but not all of it. Six dubs say which way to look, not how often it
happens. The saved runs are `data/batch/locked-1` and `locked-2`; finishing them takes about two more days of free requests, or
minutes with billing on the key.

## What the offline meaning check's false alarms really are (2026-11-02)

Meaning similarity was the biggest false-alarm source left: 19 of 46. They only show when no translation check ran, so these
are the only meaning signal someone without an AI key gets. Comparing it with Gemini, line by line, on 122 lines of 16 real dubs:

| Cutoff | Lines flagged | Gemini also scored them 6 or lower | Of Gemini's 25 low lines, found |
|---|---|---|---|
| 0.70 | 29 | 12 (41%) | 12 |
| 0.65 | 16 | 10 (62%) | 10 |
| **0.60 (today)** | **8** | **6 (75%)** | **6** |
| 0.55 | 3 | 2 | 2 |
| 0.50 | 2 | 1 | 1 |

So its flags are mostly useful, and it misses most of what Gemini finds: a rough check, not a stand-in. Lowering the cutoff to
0.50 would remove 13 of the 19 false alarms and also 5 of the 6 useful flags, so it stays at 0.60.

The 19 false alarms, by what's behind them:

| Cause | False alarms |
|---|---|
| The line is also flagged on the real dub (p001, p021); the test's clean copy happened to escape the flag | 6 |
| Recognition heard the line differently (p006, p012: one line goes from 0.82 to about 0.55 in five copies) | 8 |
| The mostly-music dub, p019 | 5 |

Only the last has a clean fix, the same as for line length: on a mostly-music video with no translation check, this row is now
"not graded" and lists no moments. That takes false alarms from **46 to 41**, with no catch lost and no verdict changed. It's
still fooled by short phrases: p021's "You are kidding me." → "설마요" scores 0.42, while Gemini gives it 9 out of 10.

## Voice quality at the same volume (2026-11-03)

A copy only 3 dB quieter should get nothing new, yet 5 of 17 did, 2 of them for "a worse voice". The voice-quality model's scores
move with volume alone, so the dub's window is now scored at the original window's volume (the gain stops at full scale, on 23
of 329 windows of the real dubs: p018 20, p011 3). A stretch where the original itself scores below 1.6 no longer counts against the dub.

| What a change does to a window's score | SIG | OVRL |
|---|---|---|
| 3 dB quieter, as before: largest move (95% within) | 1.14 (0.45) | 0.64 (0.28) |
| 3 dB quieter, volumes matched: largest move (95% within) | 0.51 (0.16) | 0.24 (0.13) |
| Simulated robotic voice, largest drop on each dub, average: before and after | 0.66 and 0.66 | 0.55 and 0.55 |

Measured through the whole pipeline on all 17 tune dubs (the holdout wasn't used):

| | Before | After |
|---|---|---|
| Voice-quality false alarms | 5 | **1** |
| Harmless copy flagged | 5 of 17 | **4 of 17** |
| Known problems caught | 102 of 112 | 102 of 112, with no catch lost |
| All false alarms | 41 | 42 (explained below) |
| Agreement with the person (saved reports with re-scored voices) | 12 and 15 of 20 | the same, with the same verdict on every dub |

Matching the volumes removed all four voice-quality false alarms that went: p005's and p018's on the harmless copy, p020's on
two copies and p019's on a cut copy. The per-stretch rule removed none of them. Its job is to stop matching adding a moment on
p001, where the original scores 1.4 and a 2.3 dB change moved the dub's SIG from 1.86 to 1.36.

**Real dubs:** p019's moment at 52-61 s and p020's at 42-51 s go, and p020's row goes from Check to Good. p019's 0-13 s becomes
0-11 s. p022's moments, the only voice-quality ones with votes, stay, with 38-51 s now 40-51 s, so its false-alarm votes are not resolved.

**Simulated damage:** a robotic voice was flagged on 10 of 17 dubs before and 9 of 17 after. p010 fell just under the band (0.47
against 0.5), with about the same drop as before. Distortion was flagged by this check on 4 of 15 before and 5 of 15 after (the
distortion check still catches all 15). Applying the 1.6 rule to the whole video was tried first and rejected: it dropped the robotic voice
to 7 of 17, losing clean stretches of noisy videos.

**Why the total didn't fall.** Voice quality fell by 4, but this was the first full run since the noise check, and it counts:

| False alarms | Before | After | Why |
|---|---|---|---|
| Voice quality | 5 | 1 | This change |
| Noise | 0 | 2 | Already there: cut copies of p007 and p010, which the noise check's estimate didn't catch |
| Unclear speech | 3 | 6 | Recognition doesn't repeat exactly (below); voice quality can't affect it |
| Meaning similarity 14, line length 5, missing from the dub 5, timing and silence 6, line overrun 2, loudness jump 1 | 33 | 33 | |

**Recognition doesn't repeat exactly on a graphics card.** The same audio recognized three times in one run, with the seed set
each time, gave different text on 2 of 3 copies tried (p011, p022), and p022's unclear stretches went from 1 to 8. So small
moves in false alarms between runs are to be expected, and neither of the two unclear-speech moments retried (p010, p011) came
back. A difference of a few false alarms between two runs says little.

**What's left on the harmless copy, 4 flags:**

| Dub | Flag | Cause |
|---|---|---|
| p018 | Voice quality, 2-11 s | A different stretch from before, over both bands by 0.01. At the same volume the copy still scores 0.26 lower than the clean copy, so this is the second encode, not volume |
| p012 | Meaning similarity, line 2 | **Volume.** The clean copy at -3 dB gets the same flag, and the quieter copy at +3 dB reads word for word like the clean copy: recognition splits the line differently |
| p001 | Meaning similarity, line 3 | Not volume: still flagged at +3 dB. The real dub has the same flag, and the clean copy heard the line differently |
| p021 | Meaning similarity, line 9 | Not volume: the same. Recognition dropping a full stop alone moves "You are kidding me." → "설마요" from 0.63 to 0.42 |

Evening out the volume before recognition would fix only p012, drop all cached recognition and need a full re-measure, so it
wasn't done. Removing punctuation before comparing doesn't help either: most low lines score lower still, and 6 of 40 lines
cross the cutoff. The meaning check stays as it is, and it only lists moments when no translation check ran.

## A dub whose picture drifts (2026-11-03)

A person compared three dubs of an 84 s English → Korean video. One came back Poor with only 14 lines against 22, and the
timeline's line stood still while it played. The dub was fine. Its picture was slowed down and sped up in places, drifting
between 0 and 5.1 s from the original, and no fixed shift fits that. DubEval called most of the first 25 s missing and left
those stretches silent, so speech recognition never heard those lines.

DubEval now follows the drift when the usual matching finds under 90% of the original.

| That dub | Before | After |
|---|---|---|
| Original found in the dub | 77% (Poor) | 100% |
| Lines | 14 | 22 |
| Speech lined up | 58% | 82% |
| Verdict | Poor | Needs review |
| Place among the 3 dubs | 3rd | 2nd |

What else it could have changed:

- **The 20 graded dubs:** matching is identical on all of them, so no verdict changes.
- **Real cuts:** the first version hid a real 4 s cut in a still shot (p009), because frames there also match at the wrong
  time. A shift that falls 2 s within 5 s now counts as a cut. On all 146 test copies none is now treated as a drift, and the 15 cut copies report the same missing parts as before.
- **Speaking pace:** lining the dub up drops 6.4 s of its sound, which read as 9.5 chars/s (Poor) against a true 8.7 (Check).
  Pace is now measured on the dub's own sound.

Still open: this rests on one drifting dub. Its 5 lines flagged for length may be fair, since they do run longer than the
original's, but a viewer may not notice when the picture was slowed to fit them. Whether to grade those differently needs
more drifting dubs.

## Tuning and held-out pairs

Thresholds are tuned on the **tune** pairs only. The **holdout** pairs are scored once per release and never used to
change a threshold; once they have been used to tune, they move to tune and new pairs are held out. Pairs are split by
**original video**: all dubs of one video are on the same side, so a video seen in tuning can't make the held-out score
look better. The sheet's `split` column decides; without it, a hash of the original video's content does
(about one video in four is held out), so it doesn't matter what the file is called.

## Ground rules
- Grades come from people (`dubeval label`), graded **before** looking at DubEval's result for that dub.
- A second person grades part of the set on their own. Where two people disagree, DubEval can't be expected to agree
  with either, so their agreement is the ceiling.
- Each language pair is reported on its own; a result for one language says nothing about another.
