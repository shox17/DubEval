# Questions, limits and troubleshooting

How far to trust a result, what DubEval can't do yet, and what to do when something goes wrong. Back to the [README](../README.md).

## How accurate is it?
DubEval measures; it doesn't replace watching the dub. Use the verdict to decide **where to look first**, and the
problem time ranges to jump there.

- **Any language pair works, without a promise.** The checks run for every language Whisper knows, and a check that
  can't work for a language says "not measured" with the reason instead of guessing. The grades have been compared
  with a person's on **19 dubs** (2026-10-29): DubEval agreed on **14**, 11 of 13 English → Korean, 2 of 2 English →
  Spanish and 1 of 4 English → Uzbek. With problems put into dubs on purpose it catches 79 of 109, and 18 of 24 on dubs
  it was never tuned on. English → Korean has the most evidence; treat other languages as a first look.
- **It says when it isn't sure.** When the video is mostly music, has very little speech, or the dub's language
  couldn't be recognized, the verdict is "Needs review" with the reason instead of a confident Good or Poor.
- **The thresholds were set from those dubs**, one reviewer's grades. Reviewers' "real problem / false alarm" votes
  and graded batches (`qa.py batch`) are how they will change. The full story: [How DubEval measures](methodology.md).
- **Speech recognition makes mistakes, and they spread.** Clarity, timing, pace and the translation check all read
  what Whisper heard. On English → Korean dubs scored against their exact scripts, Whisper `large-v3-turbo` misheard
  3 to 8% of characters on natural speech, more on lines mixing English into Korean; `base`, the model used without
  an NVIDIA GPU, misheard 7 to 11%. No other open recognizer we tried did better. Less common languages are
  recognized much worse (an Uzbek dub was heard as Kazakh): set the dub language when you start an evaluation.
- **The translation check reads the transcripts, not the audio.** An AI model (Claude, Gemini or ChatGPT, or a local
  one) scores meaning, naturalness, context, terms and localization from 1 to 10 per line. A misheard word can look
  like a translation error; the report marks those as possible mishearings, which never make a dub Poor. A line
  scored very low that might be misheard shows as Check, a moment to listen to, so a real error can't hide behind it. On the
  graded dubs its meaning grade matched the person's on 3 of 7; the misses came from misheard words. Different
  judges can disagree, so compare dubs with the same one.
- **Lip sync is informational only**: shown for lip-synced dubs, never part of the verdict. For a real check,
  download it in Settings → Models (ByteDance's StableSyncNet, 1.6 GB): it counts how often the lips line up with
  the dubbed speech next to the original, and says when the sound is late or early. Without it, a rough
  lip-movement measure is shown.

## Known limits
- **Thresholds are calibrated on only 19 real dubs** (see [How accurate is it?](faq.md#how-accurate-is-it)). Treat borderline results with care, and use labelled batches to tune them.
- **Background music makes voice checks harder:** on music-heavy videos voice similarity is not measured (by design), and speech timing and clarity are noisier.
- **Voice quality doesn't detect a muffled voice.**
- **Lip sync is information only.** The lip-sync check (download) was tested on one real dub; without it, lip
  movement is a rough heuristic.
- **The translation check reads transcripts, not audio:** a misheard word can look like a translation error (the report marks probable mishearings). It needs a Claude, Gemini or ChatGPT key, or a local model; Gemini is sometimes overloaded or out of its free daily quota, in which case the check is reported as not measured and you can run again later.
- **Speaking pace** is graded for Korean, English, Spanish, Japanese and Chinese only; other languages show "not measured".
- **Speech checks are being recalibrated for faster-whisper**, the default recognizer. The thresholds were set with the original Whisper, and on difficult audio the two can disagree (for example voice clarity 0% against 100% on the same dub). Treat clarity, timing and pace verdicts as provisional, or set `DUBEVAL_ASR=openai-whisper` for the original behaviour.
- **Less common languages are recognized poorly.** On a real English → Uzbek dub, speech recognition heard Kazakh (47% sure with `base`, 75% with `large-v3-turbo`), and with the language set to Uzbek, clarity still read 0%. Set `--target-lang`, use `large-v3-turbo`, and treat speech results for such languages as rough.
- **A job running when the server restarts can't resume**; it's reported as interrupted.

## Troubleshooting

| Problem | What to do |
|---|---|
| On a company network, model downloads or Perso links fail while the browser works | Update to 0.1.1 or later: DubEval now uses the computer's trusted certificates and proxy, as browsers do. If it still says the network blocked its secure connection or its proxy, ask IT to allow the sites DubEval uses: `huggingface.co` (models), `files.pythonhosted.org` (GPU speed-up), `registry.ollama.ai` and `github.com` (local translation model, updates), `api.perso.ai` and `portal-media.perso.ai` (Perso links), and the translation check's provider if you use one. Or use another network. The real error is in `%APPDATA%\DubEval\logs`. |
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
