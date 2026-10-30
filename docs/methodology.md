# How DubEval measures, and how far to trust it

DubEval watches and listens to an original video and its dub and tells you where the dub may be wrong. This page
explains, in plain words, what it measures, how each verdict is reached, how it was tested and what it can't do yet.
The exact thresholds are in [metrics.md](metrics.md); the test runs are in [validation.md](validation.md). Back to the
[README](../README.md).

## In one minute

- **DubEval measures; it doesn't replace watching.** Use its verdict to decide where to look first, and its problem
  times to jump there.
- **Every grade states its rule.** There is no secret score: each measure says what it measured, how it is graded and
  why it got its level.
- **It says when it isn't sure.** Mostly music, very little speech, speech it couldn't make out: the verdict becomes
  "Needs review" with the reason, instead of a confident Good or Poor.
- **It has been tested two ways:** with problems put into dubs on purpose (it catches 79 of 109, and 18 of 24 on dubs
  it was never tuned on), and against a person's grades on 19 real dubs (it agrees on 14).
- **It runs on your computer.** Only the translation check can use an online AI, and only with your own key.

## Who makes DubEval

DubEval is developed by shox17 during an internship at ESTsoft, with guidance from an ESTsoft mentor. It is open
source (AGPL-3.0) and isn't an official ESTsoft product. ESTsoft also makes Perso, one of the dubbing services
DubEval can evaluate: that is why every service is evaluated under the same conditions (below), every rule and
threshold is written in the open, and the test results on this page are published, including where DubEval is weak.
Questions and problems go to the project's [GitHub issues](https://github.com/shox17/DubEval/issues).

## The same conditions for every service

DubEval treats a dub the same way whichever service made it:

- **Same input:** the original video and the dub file the service delivers (for a Perso share link, its lip-synced
  video when there is one). Compare mode needs every dub to be of the same original, and warns when the originals'
  lengths or languages differ.
- **Same measurements:** the same speech recognizer and model, voice detector, voice-quality and voice-similarity
  models for every dub of a run, chosen once per computer (the report names them).
- **Same rules:** every threshold is fixed in the code, the same for every service, and printed next to each grade.
  Nothing is tuned per service; the test sets mix Perso, ElevenLabs and Descript dubs.
- **Same translation judge:** the first AI service with a key, asked with the same instructions for every dub. One
  difference can creep in: when a service is busy it falls back to a backup model, which the report notes. For a
  benchmark, fix the model (`GEMINI_MODEL`) and check that every dub's report names the same one.
- **Same type of dub, same standard:** an AI dub is held to a close translation; a dub marked as made by human voice
  actors may adapt jokes and idioms. Compare dubs of the same type.

## Status by language

| Language pair | Graded by a person (DubEval agreed) | Problems put into dubs | Translation mistakes put into transcripts | Status |
|---|---|---|---|---|
| English → Korean | 13 dubs (11) | 13 dubs | 19 of 19 found (Gemini) | **Tested**: the most evidence; one reviewer |
| English → Spanish | 2 dubs (2) | 2 dubs | 4 of 4 found (Gemini) | **First evidence**: too few dubs to rely on |
| English → Uzbek | 4 dubs (1) | 4 dubs | Not testable | **Not reliable**: speech recognition hears Uzbek as Kazakh, so the words aren't checked and no dub is called Good |
| Any other pair | none | none | none | **Untested**: every check runs, without a promise |

## What happens to a dub

| Step | What DubEval does | With |
|---|---|---|
| 1. Match the videos | Compares about 10 frames a second of both videos: same video? shifted? parts missing? | Picture fingerprints and motion |
| 2. Find the speech | Marks where someone is really speaking, in both tracks | Silero voice detector |
| 3. Write down the words | Transcribes both tracks with a time for every word, then transcribes again any stretch of speech the first pass skipped | Whisper (large-v3-turbo on a graphics card, else base) |
| 4. Clean the transcript | Drops "words" read into music or effects, unless the other track speaks at that moment | The voice detector from step 2 |
| 5. Compare the sound | Length, loudness, silence, distortion, sound in sync with the picture | Plain signal measurements |
| 6. Compare the speech | Timing, line by line length, pace, language, clarity | The transcripts from step 3 |
| 7. Compare the voices | How clean the dub voice sounds next to the original; whether it sounds like the same person | DNSMOS (Microsoft), WeSpeaker |
| 8. Check the translation | Scores every line 1 to 10 for meaning and four other criteria; without an AI, a meaning-similarity screen | Claude, Gemini, ChatGPT or a local model; BGE-M3 |
| 9. Decide the verdict | Grades every measure Good, Check or Poor, then applies the verdict rule (below) | The rules in `report.py` |

## What each check tells you

| Check | It answers | How much to trust it |
|---|---|---|
| Same video, coverage | Is the dub the same video, and is any part of the original missing? | High: a mismatched pair (a dub of another edit) was found exactly |
| Sound in sync | Is the dub's sound behind or ahead of its picture? | High where it is measured (a 1 s delay was found in all 12 dubs it could measure); not measured on dubs that replaced the background music |
| Length, loudness, silence, distortion | Does the dub run as long, sound as loud and as clean as the original? | High for distortion and loudness jumps (caught 15 of 15 and 13 of 15); silence and loudness are capped at Check when the dub replaced the background |
| Speech timing, line length | Does the dub speak when the original speaks, and is each line about as long? | Good on speech, weaker on music-heavy videos (DubEval says so) |
| Original voice left in | Is any part still in the original language? | Good: 8 of 9 caught on tune dubs, 2 of 3 on unseen ones |
| Voice quality | Does the dub voice sound robotic or distorted next to the original? | Good for robotic and distorted voices; misses noise mixed in at voice level (3 of 15) |
| Voice similarity | Does the dub sound like the same person? | Measured only with a clean background; never Poor, since a new voice can be on purpose |
| Translation | Does each line mean what the original said, naturally? | With Gemini, high: 23 of 23 planted wrong numbers, reversed meanings and left-out lines found, no harmless rewording flagged. With the local model, low: 4 of 23. It reads transcripts, not audio, and scores vary between runs |
| Lip sync | Do the lips follow the dub's speech? | With the lip-sync download (StableSyncNet): on a real Perso dub it told the lip-synced version from the plain one and measured planted sound delays to the frame; tested on one video, so information only. Without it, a rough lip-movement measure |

## How the verdict is decided

1. Every measure gets a level: **Good**, **Check** or **Poor**, each with its rule written next to it.
2. **Any Poor makes the dub Poor; otherwise any Check makes it Needs review; otherwise it is Good.** Information
   rows and checks that couldn't run never count, and each one that couldn't run says why.
3. **Meaning is Poor only with 3 or more seriously wrong lines (or most lines).** One or two are Check, still listed
   with their times.
   A line the AI thinks may be misheard never makes the dub Poor, but if it scored very low it is Check: the AI
   can't tell a mishearing from a real error there, so you listen.
4. **When DubEval isn't sure, it doesn't let a shaky measurement decide:**
   - little speech (under 35% of the video, or under 10 s), or speech it couldn't make out clearly: only problems that
     don't depend on speech (distortion, a different or incomplete video, sound out of sync) can make the dub Poor;
   - the dub replaced the background music: silence and loudness are Check at most;
   - the dub's language couldn't be recognized, or the translation check didn't run at all (no AI key, no local
     model, or turned off), so its words weren't checked: the dub is never called Good;
   - a backup AI model judged the translation because the first one was busy: the report notes it.

   The verdict's first lines say which of these applied and ask you to listen yourself.
5. **Comparing dubs, DubEval holds its recommendation when it isn't sure of the dub it ranks first** (little or
   unclear speech, or its translation wasn't checked): it shows the order but says "No confident recommendation yet"
   and what to check, instead of "Deliver Dub A".

## How it was tested

**Problems put into dubs on purpose.** Each real dub was copied with one known problem at a known moment (silence,
the original voice put back, a loudness jump, distortion, noise, a cut, the sound 1 s late) and once with a harmless
change (3 dB quieter). A problem counts as caught when DubEval flags it at that moment; anything else it newly flags
is a false alarm. Thresholds were set on 16 "tune" dubs only; 3 "holdout" dubs were kept apart to check the fixes.

| | Before the fixes | After |
|---|---|---|
| Problems caught (16 tune dubs) | 67 of 101 | 79 of 109 |
| Problems caught (3 unseen dubs) | 14 of 24 | 18 of 24 |
| False alarms (16 tune dubs) | 167 | 69 |
| Harmless copy flagged | 10 of 16 | 6 of 16 |

False alarms were down to 37 before the last two fixes, which recover lines that speech recognition lost on real dubs
(a line shouted over music, a stretch skipped after loud music). Those fixes raised agreement with the person but made
two music-heavy dubs' flags less steady on the planted copies; real dubs count more, so they stay.

**A person's grades on real dubs.** One reviewer graded 19 real dubs (Perso, ElevenLabs, Descript) on DubEval's
review page before seeing DubEval's results. DubEval's verdict matched theirs on **14 of 19**: 11 of 13 English →
Korean, 2 of 2 English → Spanish and 1 of 4 English → Uzbek. All 5 dubs the person graded Poor, DubEval graded Poor.

These are counts, not percentages: 19 dubs and one person say where DubEval stands and which way to improve it, not
how good it is in general.

## What DubEval can't do yet

- **Noise mixed into the voice** for a few seconds is mostly missed: the voice-quality model judges 9-second
  stretches, and normal music-heavy dubs vary as much.
- **Music, singing and shouting over effects** confuse speech recognition. DubEval detects these cases and says it
  isn't sure, but it can't grade the speech in them well.
- **Less common languages** are recognized poorly (an Uzbek dub was heard as Kazakh). DubEval then doesn't grade the
  words and never calls the dub Good; adding the dub's subtitle file helps.
- **The translation check isn't fully repeatable.** An AI model's scores can change between runs, more so when a busy
  service falls back to a smaller model. **The local model is private but weak**: in testing it found 4 of 23 planted
  translation mistakes, against 23 of 23 for Gemini.
- **Lip sync** never changes the verdict. The lip-sync check (an optional 1.6 GB download) has been tested on one
  real dub and planted delays; without it, only a rough lip-movement measure is shown.
- **The evidence is still small:** 19 graded dubs, one reviewer, three languages. Korean has the most.

## How it gets better

- **Your votes:** each problem's card in the review asks whether it is a real problem or a false alarm. Votes add
  up per check (History, or `dubeval feedback`); the checks that collect the most false alarms are the first to be
  re-tuned.
- **Graded batches:** grade dubs on the review page (`dubeval label`), run `dubeval batch`, and see where DubEval and
  people disagree.
- **Problems put in on purpose:** `dubeval validate` reruns the planted-problem test after every change to a check.
- **More reviewers and more languages:** two people grading the same dubs show how far people themselves agree,
  which is the most DubEval can be expected to match.

## What leaves your computer

Videos, audio, pictures and scores stay on your computer. The translation check is the only part that can send
anything about a dub: the two **transcripts** (the words, with times) and the video's title, to the first AI service
whose key you set (Claude, then Gemini, then ChatGPT). With the local judge (`DUBEVAL_JUDGE=ollama`) or none
(`off`), nothing about the dub leaves the computer. Downloads (models, share links, links you give) are listed in
[privacy.md](privacy.md).
