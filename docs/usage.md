# Using DubEval

Everything DubEval can do, every check it runs and how to read the results. Installing: [INSTALL.md](../INSTALL.md). Back to the [README](../README.md).

## What you can do with it
| Way | How | What for |
|---|---|---|
| **Web interface** | `dubeval web` | Choose an original and its dub (or up to 8 dubs to compare and get a recommendation), follow the evaluation, then review it like an editor: both videos in sync, a timeline with both waveforms, every line and every problem. **Settings** is PersoDub's dialog: **API keys** (Claude, Gemini, ChatGPT), **Models** (built-in and optional models by purpose, with sizes: the local translation checker, NVIDIA GPU speed-up, a large speech model, the lip-sync check), **Storage** (opens the data folder where downloaded videos, reports and history are kept), **Privacy** and **About**, with **Cancel** and **Save** (Save keeps the keys you typed and a new interface language; downloads and removals happen at once). A report row that couldn't be measured for a fixable reason links straight to the tab that fixes it. A **History** page shows every past evaluation, trends and which checks reviewers call false alarms |
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
| **Length & sound** | Same length? Same loudness? Unusual gaps? Distortion? Noise? Rushed speech? | `librosa` on both tracks: duration, RMS loudness (dB), silence, clipping, bursts of noise, chars/words per second |
| **Speech** | Is the dub in the right language? Is the voice clear? | Whisper language detection, and the share of speech Whisper recognises confidently |
| **Voice** | Does the voice sound clean, not robotic or distorted? Does it still sound like the original speaker? | A voice-quality model comparing the dub with the original at the same moments (Audiobox Aesthetics with its download from Settings → Models, 415 MB, which also works over music; DNSMOS P.835 without it), and a speaker-recognition model (WeSpeaker) comparing each original line with the dub at the same moment: same voice, another voice, or "can't tell on this video" when the model doesn't recognise the original's own speakers |
| **Line by line** | Does each dub line take about as long as the original's? Does it end before the next line starts? | Original and dub sentences matched by time; each line's speaking time compared (±15%), and lines that run into the next one flagged with their line number |
| **Timing** | Does the dub speak when the original speaks? | Whisper word timings of both tracks → overlap of speech (IoU) and the places where only one track speaks |
| **Numbers** *(offline)* | Does the dub say the same numbers as the original? | Every number in each dub line is compared with its original line (1,000 = 1.000; a number said as a word on one side is skipped); a changed number is flagged for a check |
| **Translation** *(when a judge is available)* | Same meaning? Anything missing or added? Names and numbers kept? Natural for this kind of dub? | A judge reads both sides line by line: Claude (`ANTHROPIC_API_KEY`), Gemini (`GEMINI_API_KEY`), or a local model (Gemma 4 12B, downloaded in Settings → Models with the part of Ollama it needs, 8.1 GB; it runs on the graphics card and nothing leaves the computer, but it is slower: about 10 s a line, and it wants about 7 GB of graphics memory or a Mac with Apple silicon); `--dub-type human` lets it accept intended localization |
| **Video integrity** | Is the picture unchanged, with an audio track? | Resolution, frame rate and audio stream of both files |
| **Lip sync** *(lip-synced dubs only)* | Do the lips follow the dubbed speech? | With the lip-sync download (Settings → Models, ByteDance's StableSyncNet, 1.6 GB, about 30 s more per dub): how many of up to 30 moments line up, next to the original, and whether the sound is late or early. Without it, the lips aren't checked and the report says where to get it. Runs automatically when the dub is lip-synced; with the download it counts in the verdict (90% or more of moments lined up: Good, 30% or less: Poor), the estimate never does |
| **Script accuracy** *(CLI, when you pass a script)* | Is the script you expected heard in the dub? | Whisper transcript vs your script: CER for Korean, Japanese, Chinese and Thai, WER otherwise |

Every run saves `report.html` (a standalone page to share), `report.json` and `report.txt` in the `--out` folder (default `./output`). Compare mode saves `comparison.txt` / `.json` / `.html` plus `report_A.*`, `report_B.*`, … (one per dub).

## How it works

```
 share link ─► GET /projects/shared/{seq}   (public: no key, no credits)
            ─► download the original + the dub (the lip-synced one when there is one)
            ─► measure on your machine: audio · Whisper (language, clarity, timing) · voice quality · voice similarity
                                        · file check · lip sync (lip-synced dubs)
            ─► translation check on both transcripts (Gemini, or Claude), automatic when a key is set
            ─► report: verdict · sections · problem intervals  →  report.html / report.json / report.txt
            ─► recorded in the history (data/history.jsonl)

 compare: links A, B, … (2–8) ─► the pipeline above for each ─► decision rule ─► comparison.txt / .json / .html
 batch:   a file of links      ─► the pipeline above for each ─► summary.csv / .txt / .json
 API:     POST /evaluations · /comparisons ─► the same pipeline as a background job ─► GET /jobs/{id}
```

- **Verdict rule:** any Poor measure → **Poor**; otherwise any measure that needs review → **Needs review**; otherwise **Good**. Informational and not-measured items don't count, and are listed with the reason. A level has one name everywhere: a measure, a moment and the verdict are each Good, Needs review or Poor.
- **Quality score:** a number out of 100 next to the verdict, for comparing dubs at a glance; it never replaces the
  verdict or the problems. Each graded check counts 100 when Good and 0 when Poor; one that needs review counts by
  where its result sits between the Poor and Good limits (15 of 18 lines fitting, Good from 90% and Poor under 50%,
  counts 83; the translation check and voice quality count the share of lines or stretches without a problem; a check
  with no number to place counts 50), a section
  counts the average of its checks, and the score adds the sections up by their weights: Translation 30%, Timing
  25%, Speech & voice 15%, Length & sound 15%, Same video 10%, Lip sync 5% (the video file must pass and
  has no weight). The score is the number worked out: only a dub with every check Good scores 100, and in a Poor verdict
  each Poor result costs at least a set amount by how serious it is: 100 when it makes the dub unusable (no speech, the
  wrong language, another video, a broken file), 20 when the mix can fix it (loudness, silence), 40 for anything else. A check that wasn't measured either doesn't apply to this dub (lip sync on
  a dub that isn't lip-synced, voice similarity for human voice actors: left out and its points shared), couldn't be
  measured (no translation checker, the lip check off, speech not recognized: shared too, and the score says how much of
  what applies it covers, "91% of the checks that apply to this dub were measured"; provisional under 80%, no score under 50%), or couldn't be measured
  because of the dub itself (no speech in the dub: counts as 0). The review's **Quality score** card counts in points
  only: the **points lost** with their sum ("11.0 points lost, so 89 / 100"; only the checks that lost points, each with
  why, click one to open it). Each section's header under All results gives its points
  ("22.5 of 31.6 points"; the most a section can get is bigger than its weight when another section wasn't
  checked, and the card says which). A check that lost points shows them at the right of its row (e.g. Line length ·
  Needs review · 10.7 of 12.8 points). Without a translation checker,
  Translation isn't counted and the score is marked **provisional**: the numbers check alone can't tell whether a
  translation is right;
  a comparison shows every dub's score in its ranking, but the score doesn't decide which dub to deliver. The Evaluations cards show each score on the
  picture (a comparison's card, its first-ranked dub's, marked with its letter: "A · 89 / 100", as its verdict is), and
  Evaluation history has a Score column and each language pair's average (evaluations from before 0.1.8 show a dash,
  and a line under the table says why). A comparison is named after its dubs ("a vs b", "a and 2 more") until you
  rename it at the top of the comparison; each dub's tab says whose report it is. The weights
  are a first choice, not yet checked against people's grades.
- **Each moment is listed once.** When two checks flag the same moment (a missing line and the silence it leaves), the report shows one moment with both findings, led by the one that says most; the timeline's count and the review go by moments. A finding is shown in parts: what is wrong, what the original and the dub say there, and a suggested translation. Lines the translation check thinks were misheard are listed apart, under **Possibly misheard (not counted)**. A moment is Poor only when its measure is Poor, and a check that passed lists no moments, except a long silence, a stretch in the original's language or a jump in volume, which its row's number doesn't cover.
- **Reports put problems first.** The text and HTML reports go: verdict, things to check (each moment), the measures that need attention in full (with how each is graded), then what passed in a line each, then what wasn't measured. In the HTML report a passed measure opens to its explanation and grading; the text report leaves those to the HTML report and the app. On the 20 graded dubs the text report went from about 1,820 words to about 740.
- **Checks that didn't run are said once.** They are put together by reason ("10 checks didn't run: speech recognition heard Azerbaijani instead of Uzbek…"), with what to do when there is something to do (add the dub's subtitle file). Three or more for one reason show as a banner under the verdict in the app.
- **The headline names what is wrong:** up to three measures, those with the most flagged time first, each with the time of its first moment ("1 serious problem to fix before publishing: Meaning preserved (from 00:12.4)", the reports' own time format). What DubEval isn't sure of is listed under it, one line per reason. On the review screen the one count is the timeline's problems (the review goes through the same ones); the count of measures at each level sits beside **All results**.
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

The first screen is **Home**, laid out like PersoDub's and as wide as the window: a blue **New evaluation** banner
that takes the **dub**: **Upload a file** (or drop a video on the banner) or paste **a video link of any kind**; the
start page then opens with it in the dub's card, and you add the original there. Below: the ways to start (evaluate a
dub, compare dubs, History), then every evaluation as a card with a picture of the video, its verdict and its length. Click a card to open its review. A card's **...** has
**Rename** and **Delete** (Delete removes its report and results from this computer, never your own video files).
**Search** filters the cards by name.

A start page you fill in is kept as a **draft**: once a video is given it saves itself as you go, and its card
(marked **Draft**) opens it again exactly as you left it, with its files, settings and options (a draft's **...** has
Delete). A started draft shows its progress on its card; if the evaluation fails or is stopped, the card says so and
opens the filled-in page to try again. Evaluations stay until you delete them, and so do the videos they play (files
you chose are copied into DubEval's data folder as soon as you choose them).

1. Choose the **original video** and the **dubbed video**: a file (choose or drop it), a path on this computer, or a link. Each one is **previewed** (picture, title, length) before anything runs. **A pasted link is downloaded right away**, whatever kind it is: a video page (YouTube, TikTok, Reels and the other sites yt-dlp reads), a link to a video file, or a Dropbox, Google Drive or OneDrive share (turned into a download of the file); the card shows the progress, then holds the video like a chosen file. A video that needs signing in to its site (some Vimeo videos) can't be downloaded: download it yourself and choose the file. Paste a **Perso share link** in either box and DubEval fills in the rest: the share is the dub, its original comes with it, and both languages are set (Perso shares no subtitles; add subtitle files under More options if you have them). A **Perso share link** in the dub box is enough on its own: it includes the original, and for a lip-synced dub the **lip-synced video is evaluated** and **lip sync is checked automatically** when its download is installed.
2. On each dub card you can set its **kind** (AI cloned voice, AI stock voice, human voice actors; hover over **?** to see what each one changes) and its **language** (detected automatically; choose it from the list for less common languages such as Uzbek). Each video card (the original and every dub, also in a comparison) takes its own **subtitle file** (SRT or WebVTT, optional). **More options** has the translation checker, the speech model (Automatic, or the other model) and the lip-sync check (offered once its download is installed; until then, a link to it).
3. Choose the **translation checker** from the list (Claude, Gemini, ChatGPT or a local model; one without a key is greyed out, with a link to Settings), or don't check. With no checker set up at all (a new install), Home and the start page say so in a notice with **Add a key** and **Get the local checker**: the translation counts most in the score. Subtitle files are used by the checker, shown next to each line in the review (share links too), and a dub whose speech matches its subtitle file is taken to be in that file's language even when recognition guesses another (Uzbek is often heard as Kazakh). To also score an approved script, use the command line (`--script` / `--script-file`).
4. Press **Start evaluation** and follow the stages (a green tick marks each one done; the dub's file name, or each
   dub's in a comparison, is shown above them). Once this computer has finished one evaluation that measured everything from scratch, the time under the bar says about how long is left ("About 3 minutes left"), from how fast it measured the last ones; before that, or when a run takes longer than usual, there is no estimate rather than a wrong one. The computer doesn't go to sleep while an evaluation runs (the screen may still turn off), and in the desktop app a notification says when it's done ("Evaluation finished · <title> · Needs review"; click it to open the result) unless the window is already in front; while it runs, the app's taskbar button (Windows) or Dock icon (Mac) shows its progress, red on Windows when one failed, and the Dock shows how many evaluations are left. **One evaluation runs at a time:** start another while one runs (the start button then reads **Add to queue**, and the progress screen has **Set up another evaluation**) and it waits in line, then starts by itself. Its screen says which evaluation it waits for (**Open it**) and how many are ahead; its card reads **Waiting (#2)**; the running one's screen says how many wait after it, and its Stop question says the next one then starts. **Remove from queue** takes it out at once (**Removed from the queue**, with **Add to queue again**). Quitting the desktop app while evaluations run or wait asks first (**Keep DubEval open** / **Quit anyway**), and **Restart to update** warns the same way; any that were stopped come back with Continue. **Stop** asks first, like PersoDub (**Keep going** or **Stop**), then stops within moments, even in the middle of speech recognition or the translation check. A stopped evaluation offers **Continue** (it runs again and reuses the speech already recognized) and **Change and start again** (its draft); a failed one offers Continue only when running again could help, not when a file can't be read, has no audio or is too long. The review shows what matters first: the verdict, both videos with the timeline, then **What to check**, Poor first and then Needs review (each result that isn't Good, with what it means, and every moment to look at; click one to go there). Every part of the result (Same video, Timing & audio, Translation, ...) is folded below with a one-line summary; open one to see its measures. A part whose measures didn't all run says how many weren't measured (such as "1 Good · 1 Not measured") instead of "All good". The review fills the window: the **verdict**, both videos side by side (**Play** plays the one chosen under **Listen to**, with its sound, and the other follows it to the same moment), a **timeline** with both waveforms, every line and every problem (click one to see both texts, the lengths and what was found), the things to check, and every measure with how it's graded.
5. Click the result's **title** to rename it (History, exports and its card follow). **Export** (top right of the result) saves the report (HTML), the problem list (Excel: every check graded Needs review or Poor, every warning and every timed problem), a text summary, the data (JSON) or **Problem clips**, in the interface language; several files come as one ZIP. Problem clips are for whoever fixes the dub: every moment on the timeline as a short video (1.5 s before to 1.5 s after it, at most 20 s; the worst 40 per dub), the original on the left and the dub on the right with a white gap between them, labelled, played twice: first with the original's sound, then with the dub's, the side you hear outlined in yellow (any player plays it). Unzip the file and open **Problem clips.html** (the clips are in the `clips` folder beside it): it says what was found at each moment, what each track says and a better translation, plus the problems about the whole dub. Making them takes a few seconds a clip (the dialog says how many), and needs the evaluation's videos still on this computer.

The sidebar's language picker changes the interface language at once (it is in Settings → About too). **Help** explains what DubEval does, **Send feedback** offers the DubEval Discord (talk with the team; a free Discord account to write) or a GitHub issue (a free GitHub account), and the **What's new** card lists what changed in this version. The desktop app updates itself, as PersoDub does: a new version downloads in the background and the **What's new** window opens once to say so (current and new version, release date, the new version's What's new). The What's new card gets a red dot and, once the download is done, reads **Update X is ready**. **Restart to update** installs it, with the installer's progress bar, and DubEval says "Updated to …" when it's back. You pick the moment: closing DubEval doesn't install anything. The card opens the same window any time; Settings → About → Updates checks by hand and has **Restart to update** too. Settings → Storage shows how much room evaluations, added videos and share-link downloads take, and how to free it. Settings opens as a window over the screen you're on; drag the sidebar's right edge to make it wider or narrower.

### Problem intervals
Every issue in the report is a time range you can jump to, with its category, severity (Poor or Needs review), the check that found it and a one-line description, e.g. `00:12.4–00:15.1 | Missing speech | Poor | Translation check | the line about … is not spoken`. Overlapping or nearby ranges of the same kind are merged.

| Category | Means |
|---|---|
| long silence | the original speaks for 2 s or more but the dub is silent |
| timing | only one of the two tracks speaks for a moment |
| missing / added speech | the translation check found content left out or invented |
| mistranslation · name or number | the translation check found a wrong meaning, name or term, or a dub line says a number its original doesn't |
| translation wording | the translation check found unnatural wording, a wrong tone or register, or a line that doesn't fit its context |
| distortion | the dub's audio clips |
| noise | the dub fills with hiss or static the original doesn't have |
| loudness jump | the dub is much louder or quieter than the original at that moment |
| wrong language | this part sounds like another language, or like the original's (the original voice may be left in) |
| clarity | speech recognition couldn't understand the dub there |
| voice quality | the dub's voice sounds clearly worse (robotic, distorted) than the original's there |
| different voice | this line's voice doesn't match the original speaker while the rest of the dub does |

Probable speech-recognition mistakes are listed separately as "possible ASR error" and never count. Mark each problem as a **real problem** or a **false alarm** on its card (see Reviewer feedback below).

**Interface language:** English, 한국어, Português or Español (top right of the web interface). Everything follows it: the report's explanations, verdict and things to check, Gemini's translation comments, error messages, and the downloaded HTML report. The command line takes `--lang ko` (the default), `en`, `es` or `pt`.

### Compare two dubs
**In the web interface:** press **Add another dub to compare** (up to 8 dubs of one original, each with its own kind and language, or up to 8 Perso share links) and **Compare**. Each dub can have a **name**, such as the service that made it; without one it goes by its file's name when the files tell the dubs apart. Names only tell the dubs apart: they never change the ranking. Click its name under the tabs to change it later; the tabs, ranking, saved report, export and History follow. The video's own title stays one for the whole comparison. The comparison shows the recommended version and why, the ranking (verdict, Poor and Needs review counts, problems on the timeline and the time they cover, score), every check side by side, and a tab per dub with its own synced players and timeline (the **?** beside the zoom buttons explains how to move around it). Notes that differ between dubs only in their numbers are said once, with the first dub's numbers.

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
4. fewer Needs review items
5. less problem time on the timeline (seconds)
6. higher translation meaning score (average over the lines, out of 10)
7. higher speech-timing alignment (%)

Still tied → the earlier dub (A before B), and the comparison says it's a tie. With 3+ dubs the same rule sorts all of them into a ranking, and the reasoning explains #1 against #2. A rule is skipped when any dub has no value for it (for example, no translation check), and the comparison then says the decision was made without translation. If the recommended dub still has key checks that weren't measured (every dub lacked them, so rule 1 couldn't separate them), the recommendation carries a clear **caution** to watch it before delivering. If **every dub is Poor**, the best one is still named, with a clear "neither is ready to deliver" warning and what to fix first. If DubEval **isn't sure of the dub it ranks first** (little or unclear speech, or its translation wasn't checked), it keeps the order but **holds the recommendation**: "No confident recommendation yet: Dub B ranks first, but its translation wasn't checked. Listen to the dubs before choosing." (the exit code is still 0).

First place isn't always a recommendation. `recommendation.status` in `comparison.json` (and the screen) says which:

| Status | Means | On screen |
|---|---|---|
| `recommended` | Deliver it (`ready` is true) | ★ and "Deliver Dub A" ("Deliver Dub A after review" when its verdict is Needs review) |
| `provisional` | First place, but DubEval isn't sure of it (for example, the translation wasn't checked): listen before choosing | ☆ and "Provisional first place" |
| `not_ready` | Every dub is Poor: the best one to start fixing | ☆ and "Best starting point" |

If different AI models checked the dubs' translations, the comparison says so, since part of a gap may come from the models. To rule that out, use **Use one AI model only** under More options (`--lock-model` on the command line); if that model is busy, the translation isn't checked.

`comparison.txt` and the top of `comparison.html` start with **1. Recommended version** (or the provisional or starting-point title above), **2. Problems on the timeline** (per dub, one line per moment with its other findings under it, e.g. `00:12.4–00:15.1 | Left out of the translation | Poor | Translation check | The line about … is not spoken`; the check is left out when the moment's name already says it, and so is an error type that only repeats it, such as "Omission" under "Left out of the translation") and **3. Reasoning** (the rule with each dub's value beside it (`4. Fewer Needs review items (Dub A: 1 · Dub B: 3)`), a short summary; when the recommended dub has more problems on the timeline, the summary says the rules above count checks, not moments), followed by every check side by side, **The dubs** (each one's details, without empty rows), measurement notes (one per check, for every dub it applies to: "Lip sync, not measured for either dub."), the tool version and the run time (left out when it isn't known). Probable speech-recognition errors are listed separately and never count.

**Exit codes:** `0` the first-place dub is Good or Needs review (read `recommendation.status` to see whether it's a recommendation) · `1` every dub is Poor · `2` input or runtime error (invalid link, sharing turned off, …).

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
dubeval validate testset.csv --out data/validation/run1       # known problems: caught per check, false alarms (docs/validation.md)
```
Only the printed link opens the page (it carries a new token each time), so no other web page can read or change your labels.

### History and trends
Every evaluation (web interface, command line, compare, batch and API) is added to `data/history.jsonl` on your machine. See it with **History** at the top of the web interface (period filter, week-by-week chart, language pairs, most frequent problems, reviewer votes, and the latest evaluations that are on Home; the totals count every run), or:
```bash
python qa.py history --days 30 --lang en          # summary in the terminal
python qa.py history --csv history.csv            # every recorded evaluation as a spreadsheet
```
Reruns of the same link count once in the totals (the latest run wins).

### Going through the problems
**Review the problems**, under the timeline, walks through every flagged moment: **Start reviewing**, then **Previous** and **Next** (keys `N` and `P`). Each one is selected on the timeline, its card opens and the videos move to its start; nothing plays until you press **Play** (or Space), and **Listen to** picks the original or the dub.

### Reviewer feedback
The first time you open the app, it asks whether to send **usage stats**: small counts that show where evaluations fail and which features are used. They stay off unless you say yes, and you can change your answer in **Settings → Privacy**, which also lists what was sent since you opened the app ([what is sent](privacy.md)).

Open a problem (click it on the timeline or in the list, or reach it with **Review the problems**) and mark it **Real problem** or **False alarm** on its card (the latest vote counts, so you can change your mind). Votes always refer to the moments the review shows, even on an evaluation run before a rule changed, and are saved in `data/feedback.jsonl`. They don't change this report: the History page and `python qa.py feedback` add them up per check and name the checks that **flag too much** (half or more false alarms, after at least 3 votes), the first thresholds to loosen.

### The command line
```bash
python qa.py "<share link>"                        # text report on screen (Korean by default), files in ./output
python qa.py "<share link>" --script-file ko.txt   # also score script accuracy
python qa.py "<share link>" --no-lipsync --no-translation-check   # fastest (skips the lip-sync check even if lip-synced)
python qa.py "<share link>" --json                 # machine-readable
python qa.py "<share link>" --fail-on poor         # exit code 1 on a Poor verdict (automation)
python qa.py "<share link>" --out reports --lang en   # another folder (created if missing), English report
python qa.py "<share link>" --original original.mp4   # when the share link has no original (file or URL)
python qa.py "<share link>" --no-cache             # download and transcribe again
```

### Score bands
Full detail in [metrics.md](metrics.md).

| Measure | Good | Needs review | Poor |
|---|---|---|---|
| Length match | ≤ 5% | ≤ 15% | above |
| Loudness match | within ±3 dB | within ±10 dB | beyond |
| Extra silence in the dub | ≤ 5 pts | ≤ 15 pts | above |
| Noise (hiss or static the original doesn't have, 1.5 s or longer) | none | any | never |
| Speaking pace (Korean) | ≤ 7.5 chars/s | ≤ 9 | above |
| Speaking pace (English) | ≤ 3.2 words/s | ≤ 3.8 | above |
| Speaking pace (Spanish) | ≤ 3.5 words/s | ≤ 4.2 | above |
| Dub language | matches | unsure | different |
| Voice clarity | ≥ 90% | ≥ 70% | below |
| Voice similarity to the original speaker | ≥ 40%: the same voice | under 30%: another voice; 30–40%: partly alike (never Poor) | Not graded when under 40% on a video whose own speakers the model can't match with themselves (under 60%) |
| Voice quality (vs the original, per ~9 s stretch), with the voice-quality download | less than 1.0 below the original and below the dub's own usual (on a 1–10 scale) | 1.0 or more below either (or 1.2 on the model's second score) | 2.5 or more below |
| Voice quality without the download (DNSMOS, 1–5 scale) | voice < 0.6 and whole sound < 0.5 below | below that | voice ≥ 2.5 or whole sound ≥ 1.5 below |
| Speech timing overlap | ≥ 75% | ≥ 45% | below |
| Translation check (one row; every line 1–10 on meaning, natural wording, context, consistent terms, localization) | no line ≤ 6 on any of the five | a line ≤ 6 on any of them (or one or two ≤ 4 on meaning) | 3 or more lines, or most lines, ≤ 4 on meaning |
| Numbers (lines with digits on both sides) | every line keeps its numbers | a line says a different number | never |
| Script accuracy | ≥ 80% | ≥ 50% | below |
| Lip sync (with the download): moments that line up | ≥ 90% | between | ≤ 30% |

Read **lip sync** next to the original's count: a dub without lip sync lines up about 1 time in 6 by chance.
The translation check works on speech-recognition transcripts, so a misheard word can look like a translation error; the report says when an issue may be one.
