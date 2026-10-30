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
| `noise_4s` | noise as loud as the voice over 4 s | a new voice-quality or clarity problem there |
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
much); **short silences** (3 s) on some dubs; the remaining false alarms are mostly the offline meaning screen and
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
language pair: it stays information only until graded lip-synced dubs, ideally with another face and language, back
it. Before the speed work the same check took about 4 minutes per dub on this computer's processor; it now takes
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
