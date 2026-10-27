# Using DubEval

Everything DubEval can do, every check it runs and how to read the results. Installing: [INSTALL.md](../INSTALL.md). Back to the [README](../README.md).

## What you can do with it
| Way | How | What for |
|---|---|---|
| **Web interface** | `dubeval web` | Choose an original and its dub (or up to 8 dubs to compare and get a recommendation), follow the evaluation, then review it like an editor: both videos in sync, a timeline with both waveforms, every line and every problem; vote real problem / false alarm. **Settings** has PersoDub-style tabs: **Models** (built-in and optional models by purpose, with sizes: offline meaning check, NVIDIA GPU speed-up, a large speech model), **API keys** (Claude, Gemini, ChatGPT), **Privacy** and **About**. A report row that couldn't be measured for a fixable reason links straight to the tab that fixes it. A **History** page shows every past evaluation, trends and which checks reviewers call false alarms |
| **Command line** | `dubeval evaluate --original A --dub B`, or `python qa.py "<share link>"` | A report in the terminal plus saved files |
| **Compare** | **Add another dub** in `dubeval web`, or `python qa.py compare A B C …` | Rank 2–8 dubs of the same video and pick the one to deliver |
| **Batch** | `python qa.py batch links.txt` | Check many links at once; one summary spreadsheet, and agreement with your own verdicts |
| **History & feedback** | **History** in `dubeval web`, `qa.py history`, `qa.py feedback` | Trends over time, and which checks reviewers say raise false alarms |
| **REST API** | `python qa.py serve` | Let other tools start evaluations and fetch reports |
| **Docker** | `docker compose up` | Everything in one container, models included (works offline) |

## What it checks
| Section | What it checks | How |
|---|---|---|
| **Same video** | Are the two files the same video? Is the dub shifted in time? Is any part of the original missing? | Motion and picture fingerprints of both videos, refined by the background sound; shifts are corrected before anything else is measured, and clearly different videos are refused |
| **Timing & audio** | Same length? Same loudness? Unusual gaps? Distortion? Rushed speech? | `librosa` on both tracks: duration, RMS loudness (dB), silence, clipping, chars/words per second |
| **Speech** | Is the dub in the right language? Is the voice clear? | Whisper language detection, and the share of speech Whisper recognises confidently |
| **Voice** | Does the voice sound clean, not robotic or distorted? Does it still sound like the original speaker? | A voice-quality model (DNSMOS P.835) comparing the dub with the original at the same moments, and a speaker-recognition model (WeSpeaker) comparing each original line with the dub (lines with a quiet background only) |
| **Line by line** | Does each dub line take about as long as the original's? Does it end before the next line starts? | Original and dub sentences matched by time; each line's speaking time compared (±15%), and lines that run into the next one flagged with their line number |
| **Timing alignment** | Does the dub speak when the original speaks? | Whisper word timings of both tracks → overlap of speech (IoU) and the places where only one track speaks |
| **Meaning similarity** *(offline)* | Does each dub line roughly mean what the original line says? | A multilingual sentence model (BGE-M3) compares every line pair on your computer; low lines are flagged for a check |
| **Translation** *(when a judge is available)* | Same meaning? Anything missing or added? Names and numbers kept? Natural for this kind of dub? | A judge reads both sides line by line: Claude (`ANTHROPIC_API_KEY`), Gemini (`GEMINI_API_KEY`), or a local model (Qwen3 8B, downloaded in Settings → Models with the part of Ollama it needs, ~5.3 GB; it runs on the graphics card through Vulkan and nothing leaves the computer, but it is slower and less exact); `--dub-type human` lets it accept intended localization |
| **Video integrity** | Is the picture unchanged, with an audio track? | Resolution, frame rate and audio stream of both files |
| **Lip movement** *(experimental, lip-synced dubs only)* | Does the mouth move with the voice? | MediaPipe mouth opening vs loudness, compared with the original; measured automatically when the dub is lip-synced; never part of the verdict |
| **Script accuracy** *(CLI, when you pass a script)* | Is the script you expected heard in the dub? | Whisper transcript vs your script: CER for Korean, Japanese, Chinese and Thai, WER otherwise |

Every run saves `report.html` (a standalone page to share), `report.json` and `report.txt` in the `--out` folder (default `./output`). Compare mode saves `comparison.txt` / `.json` / `.html` plus `report_A.*`, `report_B.*`, … (one per dub).

## How it works

```
 share link ─► GET /projects/shared/{seq}   (public: no key, no credits)
            ─► download the original + the dub (the lip-synced one when there is one)
            ─► measure on your machine: audio · Whisper (language, clarity, timing) · voice quality · voice similarity
                                        · file check · lip movement (lip-synced dubs)
            ─► translation check on both transcripts (Gemini, or Claude), automatic when a key is set
            ─► report: verdict · sections · problem intervals  →  report.html / report.json / report.txt
            ─► recorded in the history (data/history.jsonl)

 compare: links A, B, … (2–8) ─► the pipeline above for each ─► decision rule ─► comparison.txt / .json / .html
 batch:   a file of links      ─► the pipeline above for each ─► summary.csv / .txt / .json
 API:     POST /evaluations · /comparisons ─► the same pipeline as a background job ─► GET /jobs/{id}
```

- **Verdict rule:** any Poor → **Poor**; otherwise any Check → **Needs review**; otherwise **Good**. Informational and not-measured items don't count, and are listed with the reason.
- **Downloads, speech recognition and the translation review are cached per share link** (`data/cache/`), so a rerun of the same link takes seconds and costs no API call. `--no-cache` redoes the downloads and speech recognition; a failed translation review is never cached.
- **Repeatable:** the same dub always gets the same scores (the speech recognizer's random sampling is fixed), so a change in the report means the dub or the tool changed, not chance.
- In the web interface the work runs in a **background thread**, so reloading the page is safe: the job id in the URL reattaches to it, and finished results survive a restart.
- All measuring (Whisper, MediaPipe, audio) happens **on your machine**. Only the translation check sends the two transcripts (text, not audio) to Gemini or Claude.

More detail: [Architecture](architecture.md) · [Metrics and score bands](metrics.md) · [Design notes](design.md) · [Roadmap](roadmap.md)

## Using it

### Get a share link
In Perso, open the dubbed video, choose **Share**, and copy the link. It looks like `https://perso.ai/en/share/video-translator?seq=…`. Links from Perso's gallery pages work too (`https://perso.ai/video-translator/en-es/<category>?seq=…`): any perso.ai link with a `seq=` token.

### The web interface
`dubeval web` opens DubEval in your browser (only this computer can use it, with the link it prints).

The first screen is **Evaluations**, laid out like PersoDub's home: a blue **New evaluation** banner (click it, or
paste a Perso share link into it), the ways to start (evaluate a dub, compare dubs, History), then every evaluation as
a card with a picture of the video, its verdict and its length. Click a card to open its review. A card's **...** has
**Rename** and **Delete** (Delete removes its report and results from this computer, never your own video files).
**Search** filters the cards by name.

A start page you fill in is kept as a **draft**: once a video is given it saves itself as you go, and its card
(marked **Draft**) opens it again exactly as you left it, with its files, settings and options (a draft's **...** has
Delete). A started draft shows its progress on its card; if the evaluation fails or is stopped, the card says so and
opens the filled-in page to try again. Evaluations stay until you delete them, and so do the videos they play (files
you chose are copied into DubEval's data folder as soon as you choose them).

1. Choose the **original video** and the **dubbed video**: a file (choose or drop it), a path on this computer, or a link. Each one is **previewed** (picture, title, length) before anything runs. Paste a **Perso share link** in either box and DubEval fills in the rest: the share is the dub, its original comes with it, and both languages are set (Perso shares no subtitles; add subtitle files under More options if you have them). A **Perso share link** in the dub box is enough on its own: it includes the original, and for a lip-synced dub the **lip-synced video is evaluated** and **lip movement is measured automatically**.
2. On each dub card you can set its **kind** (AI cloned voice, AI stock voice, human voice actors; hover over **?** to see what each one changes) and its **language** (detected automatically; choose it from the list for less common languages such as Uzbek). Each video card (the original and every dub, also in a comparison) takes its own **subtitle file** (SRT or WebVTT, optional). **More options** has the translation checker, the speech model and lip movement.
3. Choose the **translation checker** from the list (Claude, Gemini, ChatGPT or a local model; one without a key is greyed out, with a link to Settings), or don't check. Subtitle files are used by the checker, shown next to each line in the review (share links too), and a dub whose speech matches its subtitle file is taken to be in that file's language even when recognition guesses another (Uzbek is often heard as Kazakh). To also score an approved script, use the command line (`--script` / `--script-file`).
4. Press **Start evaluation** and follow the stages (a green tick marks each one done). **Stop** asks first, like PersoDub (**Keep going** or **Stop**), then stops within moments, even in the middle of speech recognition or the translation check. A stopped evaluation offers **Continue** (it runs again and reuses the speech already recognized) and **Change and start again** (its draft). The review shows what matters first: the verdict, both videos with the timeline, then **What to check**, Poor first and then Check (each result that isn't Good, with what it means, and every moment to look at; click one to go there). Every part of the result (Same video, Timing & audio, Translation, ...) is folded below with a one-line summary; open one to see its measures. The review fills the window: the **verdict**, both videos side by side (**Play** plays the one chosen under **Listen to**, with its sound, and the other follows it to the same moment), a **timeline** with both waveforms, every line and every problem (click one to see both texts, the lengths and what was found), the things to check, and every measure with how it's graded.
5. Click the result's **title** to rename it (History, exports and its card follow). **Export** (top right of the result) saves the report (HTML), the problem list (Excel: every check graded Check or Poor, every warning and every timed problem), a text summary or the data (JSON), in the interface language; several files come as one ZIP.

The sidebar's **Help** explains what DubEval does, **Send feedback** opens the project's issues page, and the **What's new** card lists what changed in this version. The desktop app updates itself, as PersoDub does: a new version downloads in the background and the **Version update** window opens once to say so (current and new version, release date, the new version's What's new). **Restart to update** installs it, with the installer's progress bar, and DubEval says "Updated to …" when it's back. The What's new card opens the same window any time; Settings → About → Updates checks by hand. The interface language is in Settings → About. Settings opens as a window over the screen you're on; drag the sidebar's right edge to make it wider or narrower.

### Problem intervals
Every issue in the report is a time range you can jump to, with its category, severity (Poor or Check), the check that found it and a one-line description, e.g. `12.4s-15.1s | missing speech | Poor | Translation check | the line about … is not spoken`. Overlapping or nearby ranges of the same kind are merged.

| Category | Means |
|---|---|
| long silence | the original speaks for 2 s or more but the dub is silent |
| timing | only one of the two tracks speaks for a moment |
| missing / added speech | the translation check found content left out or invented |
| mistranslation · name or number | the translation check found a wrong meaning, name or term |
| translation wording | the translation check found unnatural wording, a wrong tone or register, or a line that doesn't fit its context |
| distortion | the dub's audio clips |
| loudness jump | the dub is much louder or quieter than the original at that moment |
| wrong language | this part sounds like another language, or like the original's (the original voice may be left in) |
| clarity | speech recognition couldn't understand the dub there |
| voice quality | the dub's voice sounds clearly worse (robotic, distorted) than the original's there |
| different voice | this line's voice doesn't match the original speaker while the rest of the dub does |

Probable speech-recognition mistakes are listed separately as "possible ASR error" and never count. Mark each interval as a **real problem** or a **false alarm** in the web interface (see Reviewer feedback below).

**Interface language:** English, 한국어, Português or Español (top right of the web interface). Everything follows it: the report's explanations, verdict and things to check, Gemini's translation comments, error messages, and the downloaded HTML report. The command line takes `--lang ko` (the default), `en`, `es` or `pt`.

### Compare two dubs
**In the web interface:** press **Add another dub to compare** (up to 8 dubs of one original, each with its own kind and language, or up to 8 Perso share links) and **Compare**. The comparison shows the recommended version and why, the ranking, every check side by side, and a tab per dub with its own synced players and timeline.

**On the command line:**
```bash
python qa.py compare "<link A>" "<link B>" --out ./output --lang ko
python qa.py compare "<link A>" "<link B>" "<link C>" "<link D>"     # up to 8 dubs: a full ranking
```
Every dub goes through the full pipeline. **Decision rule**, stopping at the first rule that separates them:
1. more of the key checks measured (speech timing, line length, voice clarity): these read the dub's recognized
   speech, so when recognition fails (a less common language heard as another one) they aren't graded and the verdict
   looks better than the dub may be. A dub that couldn't be checked never beats one that was
2. better overall verdict (Good > Needs review > Poor)
3. fewer Poor items
4. fewer Check items
5. less total time in problem intervals (seconds)
6. higher translation meaning score (average over the lines, out of 10)
7. higher speech-timing alignment (%)

Still tied → the earlier dub (A before B), and the comparison says it's a tie. With 3+ dubs the same rule sorts all of them into a ranking, and the reasoning explains #1 against #2. A rule is skipped when any dub has no value for it (for example, no translation check), and the comparison then says the decision was made without translation. If the recommended dub still has key checks that weren't measured (every dub lacked them, so rule 1 couldn't separate them), the recommendation carries a clear **caution** to watch it before delivering. If **every dub is Poor**, the best one is still named, with a clear "neither is ready to deliver" warning and what to fix first.

`comparison.txt` and the top of `comparison.html` start with **1. Recommended version**, **2. Problem intervals** (per dub, e.g. `12.4s-15.1s | Dub B | missing speech | Poor | Translation check | The line about … is not spoken`) and **3. Reasoning** (the rule, the values for A and B, a short summary), followed by every check side by side, each link's details, measurement notes, the tool version and the run time. Probable speech-recognition errors are listed separately and never count.

**Exit codes:** `0` the recommended dub is Good or Needs review · `1` every dub is Poor · `2` input or runtime error (invalid link, sharing turned off, …).

### Batch mode: many links, one summary
```bash
python qa.py batch links.txt --out ./output/batch --lang en
```
`links.txt` has one share link per line (`#` comments and a `url,label` header are fine). Each link gets its own report folder (`001/`, `002/`, …), and the batch writes `summary.csv` (every measure's level and value per link; opens in Excel with Korean intact), `summary.txt` and `summary.json`. A broken link is recorded with its error and the batch goes on (exit code 2 if any failed, else 0).

**Calibrate the tool against your ears:** after each link, add your own verdict, `good`, `check` (or `needs review`) or `poor`:
```
https://perso.ai/…?seq=…,good
https://perso.ai/…?seq=…,poor
```
The summary then shows how often the tool agrees with you, whether it is stricter or more lenient, and a person × tool table. Use the CSV to see which measure drove each disagreement before you change a threshold.

**A test set of original/dub pairs** works the same way: a CSV with `original` and `dub` columns (files or links),
your verdicts in `label`, `length_label` and `meaning_label`, and optional `source_lang`, `target_lang`,
`original_track`, `dub_track`, `service`, `dub_type` and `notes`. Start from
[examples/testset_template.csv](../examples/testset_template.csv):
```bash
dubeval batch testset.csv --out ./output/testset          # summary.csv has every measure plus your columns
```
Keep the videos and a sheet with private paths out of git.

**Label the test set** on a review page: both videos side by side, three questions (length and timing, meaning,
overall), and DubEval's verdict shown only after you answer, so it doesn't sway you. Answers are saved into the sheet:
```bash
dubeval label testset.csv --results ./output/testset          # opens http://127.0.0.1:<port> in your browser
```
Only the printed link opens the page (it carries a new token each time), so no other web page can read or change your labels.

### History and trends
Every evaluation (web interface, command line, compare, batch and API) is added to `data/history.jsonl` on your machine. See it with **History** at the top of the web interface (period filter, week-by-week chart, language pairs, most frequent problems, reviewer votes, latest runs with their reports), or:
```bash
python qa.py history --days 30 --lang en          # summary in the terminal
python qa.py history --csv history.csv            # every recorded evaluation as a spreadsheet
```
Reruns of the same link count once in the totals (the latest run wins).

### Reviewer feedback
On every problem in the web interface's review, mark it **real problem** or **false alarm** (the latest vote counts, so you can change your mind). Votes are saved in `data/feedback.jsonl`. The History page and `python qa.py feedback` then show, per check, how many flags reviewers confirmed and which checks **flag too much** (half or more false alarms, after at least 3 votes): the place to loosen a threshold.

### The command line
```bash
python qa.py "<share link>"                        # text report on screen (Korean by default), files in ./output
python qa.py "<share link>" --script-file ko.txt   # also score script accuracy
python qa.py "<share link>" --no-lipsync --no-translation-check   # fastest (skips lip movement even if lip-synced)
python qa.py "<share link>" --json                 # machine-readable
python qa.py "<share link>" --fail-on poor         # exit code 1 on a Poor verdict (automation)
python qa.py "<share link>" --out reports --lang en   # another folder (created if missing), English report
python qa.py "<share link>" --original original.mp4   # when the share link has no original (file or URL)
python qa.py "<share link>" --no-cache             # download and transcribe again
```

### Score bands
Full detail in [metrics.md](metrics.md).

| Measure | Good | Check | Poor |
|---|---|---|---|
| Length match | ≤ 5% | ≤ 15% | above |
| Loudness match | within ±2 dB | within ±4 dB | beyond |
| Extra silence in the dub | ≤ 5 pts | ≤ 15 pts | above |
| Speaking pace (Korean) | ≤ 7.5 chars/s | ≤ 9 | above |
| Speaking pace (English) | ≤ 3.2 words/s | ≤ 3.8 | above |
| Speaking pace (Spanish) | ≤ 3.5 words/s | ≤ 4.2 | above |
| Dub language | matches | unsure | different |
| Voice clarity | ≥ 90% | ≥ 70% | below |
| Voice similarity to the original speaker (lines with a quiet background) | ≥ 50% | below (never Poor) | |
| Voice quality (vs the original, per ~9 s stretch) | voice < 0.6 and whole sound < 0.5 below | below that | voice ≥ 1.0 or whole sound ≥ 0.9 below |
| Speech timing overlap | ≥ 75% | ≥ 55% | below |
| Meaning (every line 1–10) | no line ≤ 6 | a line ≤ 6 | a line ≤ 4 |
| Natural wording · fits the context · consistent terms · localization (every line 1–10) | no line ≤ 6 | a line ≤ 6 | never |
| Script accuracy | ≥ 80% | ≥ 50% | below |
| Lip movement | always informational | | |

The **lip movement number is not reliable on its own**; only compare it with the original video's score. The translation check works on speech-recognition transcripts, so a misheard word can look like a translation error; the report says when an issue may be one.
