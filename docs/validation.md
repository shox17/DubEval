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
