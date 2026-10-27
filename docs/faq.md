# Questions, limits and troubleshooting

How far to trust a result, what DubEval can't do yet, and what to do when something goes wrong. Back to the [README](../README.md).

## How accurate is it?
DubEval measures; it doesn't replace watching the dub. Use the verdict to decide **where to look first**, and the
problem time ranges to jump there.

- **Any language pair works, without a promise.** The checks run for every language Whisper knows, and a check that
  can't work for a language says "not measured" with the reason instead of guessing. But the grades have been compared
  with a person's on only **12 dubs**: 6 English → Korean, 4 English → Uzbek and 2 English → Spanish (2026-10-25).
  DubEval agreed with the person's verdict on **5 of the 6 Korean dubs**, 1 of the 4 Uzbek and 0 of the 2 Spanish
  ones (6 of 12 in all). Only English → Korean has enough agreement to trust; treat other languages as a first look.
- **The thresholds are first guesses** set from those 12 dubs. More graded dubs are the next step; reviewers'
  "real problem / false alarm" votes and graded batches (`qa.py batch`) are how they will change.
- **Speech recognition makes mistakes, and they spread.** Clarity, timing, pace and the translation check all read
  what Whisper heard. On English → Korean dubs scored against their exact scripts, Whisper `large-v3-turbo` misheard
  3 to 8% of characters on natural speech, more on lines mixing English into Korean; `base`, the model used without
  an NVIDIA GPU, misheard 7 to 11%. No other open recognizer we tried did better. Less common languages are
  recognized much worse (an Uzbek dub was heard as Kazakh): set the dub language when you start an evaluation.
- **The translation check reads the transcripts, not the audio.** An AI model (Claude, Gemini or ChatGPT, or a local
  one) scores meaning, naturalness, context, terms and localization from 1 to 10 per line. A misheard word can look
  like a translation error; the report marks those as possible mishearings and they never lower a grade. On the
  graded dubs its meaning grade matched the person's on 3 of 7; the misses came from misheard words. Different
  judges can disagree, so compare dubs with the same one.
- **Lip sync is informational only** in v0.1: a rough measure shown for lip-synced dubs, never part of the verdict. A
  real lip-sync check is planned after v0.1.

## Known limits
- **Thresholds are calibrated on only 12 real dubs** (see [How accurate is it?](faq.md#how-accurate-is-it)). Treat borderline results with care, and use labelled batches and 👍/👎 votes to tune them.
- **Background music makes voice checks harder:** on music-heavy videos voice similarity is not measured (by design), and speech timing and clarity are noisier.
- **Voice quality doesn't detect a muffled voice.**
- **Lip movement is a rough heuristic:** shown for information only, never part of the verdict.
- **The translation check reads transcripts, not audio:** a misheard word can look like a translation error (the report marks probable mishearings). It needs a Claude, Gemini or ChatGPT key, or a local model; Gemini is sometimes overloaded or out of its free daily quota, in which case the check is reported as not measured and you can run again later.
- **Speaking pace** is graded for Korean, English, Spanish, Japanese and Chinese only; other languages show "not measured".
- **Speech checks are being recalibrated for faster-whisper**, the default recognizer. The thresholds were set with the original Whisper, and on difficult audio the two can disagree (for example voice clarity 0% against 100% on the same dub). Treat clarity, timing and pace verdicts as provisional, or set `DUBEVAL_ASR=openai-whisper` for the original behaviour.
- **Less common languages are recognized poorly.** On a real English → Uzbek dub, speech recognition heard Kazakh (47% sure with `base`, 75% with `large-v3-turbo`), and with the language set to Uzbek, clarity still read 0%. Set `--target-lang`, use `large-v3-turbo`, and treat speech results for such languages as rough.
- **A job running when the server restarts can't resume**; it's reported as interrupted.

## Troubleshooting

| Problem | What to do |
|---|---|
| `pip install` fails on `mediapipe` or `numpy` | Use Python 3.14 (`python3 --version`). If a pinned version still has no wheel for your system, install from the version ranges instead: `pip install -e ".[dev]"`. |
| "The dub's language was guessed as …, only …% sure" | Run again with the language set, for example `--target-lang uz`. |
| "This link opens a web page, not a video file" | Install the links extra (`pip install "dubeval[links]"`) to evaluate YouTube and other pages, or download the video and pass the file. |
| Speech recognition is slow | It's running on the CPU. With an NVIDIA GPU, `pip install nvidia-cublas-cu12` (or put `cublas64_12.dll` and `cublasLt64_12.dll` in `~/.cache/dubeval/cuda`); DubEval then uses the GPU automatically. No PyTorch needed. |
| "This doesn't look like a Perso share link" | Copy the whole link from Perso (Share dialog or gallery page); it must be on perso.ai and contain `?seq=`. |
| "Sharing is turned off for this Perso project" | Ask the owner to turn sharing on for that video in Perso, then try again. |
| "This shared project has no finished dubbed video yet" | Wait until Perso finishes dubbing, then try again. |
| "This share link has no original video" | Pass the original with `--original <file or URL>`. |
| Korean text shows as `???` in a Windows console | The CLI switches its output to UTF-8; use Windows Terminal, or open `comparison.txt` / `report.txt`, which are always UTF-8. |
| Translation check shows "not measured" | Add `GEMINI_API_KEY` to `.env` and restart. The reason in the report says what went wrong; everything else still works. |
| "Gemini is overloaded right now" | A temporary Google capacity problem (HTTP 503). The tool already retried and tried a second model; run it again in a minute. |
| First run is slow | It's downloading the Whisper speech model (~145 MB). This happens only once. |
| Progress page says the job was interrupted | `dubeval web` was restarted during a run. Start the evaluation again. |
