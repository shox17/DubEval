# AGENTS.md

Guidance for AI coding agents (Codex, Claude Code and others) working in this repository. `CLAUDE.md` imports
this file, so keep everything here.

## What this is
**DubEval**: a CLI (`dubeval`, also `qa.py`) and a web interface (`dubeval web`) that evaluate a dub against its
original, given as **two files or links**, **one file with two audio tracks**, or a Perso AI **share link**, and
write a quality report, or (**compare mode**) evaluate 2-8 dubs of the same video and recommend which one to
deliver, with the reason.

**Direction:** DubEval is becoming a general, open-source dubbing evaluator: any original and its dub, from any
service or from human voice actors (`docs/roadmap.md`). Length/timing and translation meaning come first; lip sync
comes last. **License:** AGPL-3.0-or-later (`LICENSE`); third-party code and models are listed in `NOTICE`.

1. The share link's public endpoint (no key, no account, no credits) gives the original video and the dub.
2. The tool downloads both (the lip-synced dub when there is one), then measures them: length, loudness, silence,
   distortion, speaking pace, dub language, voice clarity (Whisper), voice quality (DNSMOS), voice similarity (speaker model), speech timing, video file, lip sync
   (lip-synced dubs only: StableSyncNet, when its download is installed; without it the lips aren't checked),
   and script accuracy when a script is passed to the CLI.
3. Gemini (or Claude) checks the translation automatically when a key is set.
4. `dubeval/report.py` turns everything into a report: a verdict (Good / Needs review / Poor), every measure with a
   level, a plain explanation and how it's graded, and every issue as a **problem interval** (`dubeval/intervals.py`).
   Saved as `report.html`, `report.json` and `report.txt`, in English, Korean, Portuguese or Spanish.
5. Compare mode (`dubeval/compare.py`) runs steps 1–4 for 2 to 8 links (A, B, C, ...), ranks them with the decision rule
   (more key checks measured → better verdict → fewer Poor → fewer Check → less problem time → higher meaning score
   → higher speech timing;
   still tied → input order) and writes `comparison.txt/.json/.html` (recommended version, problem intervals,
   reasoning first) plus `report_A.*`, `report_B.*`, ...

Deeper docs: `README.md` (the front page: what it does, download, accuracy), `INSTALL.md` (desktop app, from source, Docker), `docs/usage.md` (every feature, check and score band), `docs/faq.md` (accuracy, limits, troubleshooting), `docs/development.md` (workflow, REST API, CI), `docs/architecture.md` (modules, results schema), `docs/metrics.md` (how each
measure works and its bands), `docs/methodology.md` (plain-language: how DubEval measures, how it was tested, its
limits; keep its numbers in step with `docs/validation.md`), `docs/validation.md` (the test runs), `docs/design.md`
(why each choice was made), `docs/roadmap.md` (what comes next).

## Commands
```bash
source .venv/bin/activate                                      # Windows: .venv\Scripts\activate
dubeval evaluate --original a.mp4 --dub b.mp4                  # any original + dub (files or links) → report.* in ./output
dubeval evaluate --tracks film.mkv --target-lang ko            # one file: original = audio track 0, dub = track 1
dubeval schema                                                 # the JSON Schema of report.json (= schemas/report.schema.json)
python qa.py "https://perso.ai/en/share/video-translator?seq=…"  # a Perso share link (Korean report by default)
python qa.py "<link>" --out ./output --lang en                 # another folder / language (ko | en | es | pt)
python qa.py compare "<link A>" "<link B>" [<C> ...] --out ./output  # rank 2-8 dubs, recommend one
python qa.py batch links.txt --out ./output/batch                # many links → summary.csv (+ agreement with your labels)
dubeval batch testset.csv --out ./output/testset                 # original/dub pairs (examples/testset_template.csv)
dubeval label testset.csv --results ./output/testset             # review page to label the pairs (127.0.0.1 only)
dubeval web                                                      # the web interface (127.0.0.1, per-launch link)
cd desktop && npm install && npm start                           # the same in a desktop window (needs Node.js)
python qa.py history --days 30                                    # every past evaluation: totals, pairs, trends
python qa.py feedback                                             # reviewer votes: which checks raise false alarms
dubeval validate testset.csv --out data/validation/run1          # known problems put into each dub: caught? false alarms?
python qa.py serve                                                # REST API on 127.0.0.1:8000 (docs at /docs)
docker build -t dubeval . && docker run -p 127.0.0.1:8501:8501 -v dubeval-data:/data dubeval   # container (web)
python qa.py "<link>" --json                                   # machine-readable report
pytest -m "not slow"                                           # ~30 s, offline. Run after every change
pytest                                                         # adds real speech-recognition runs (need tests/data/sample.mp4)
```
`evaluate` options: `--original-track N` / `--dub-track N`, `--original-subtitles f.srt` / `--dub-subtitles f.vtt`,
`--source-lang` / `--target-lang` (detected when not given; a guess below 80% confidence adds a report warning),
`--lipsync` (off by default for files), plus the options below. Share-link options (single and compare): `--original <file or URL>` (link without an original), `--no-cache`, `--no-lipsync`,
`--no-translation-check`, `--whisper-model small`, `--verbose` (show MediaPipe logs). Single mode only: `--script "…"`
/ `--script-file f.txt`, `--fail-on poor|check`. Exit codes: 0 done (compare: recommended dub is Good or Needs
review), 1 single: verdict failed `--fail-on` / compare: every dub Poor, 2 input or runtime error (batch: any link
failed; the summary is still written).

## Setting up a new machine
```bash
python3.11 -m venv .venv && source .venv/bin/activate      # Windows: py -3.11 -m venv .venv
pip install torch --index-url https://download.pytorch.org/whl/cu128   # dev only: NVIDIA GPU (or .../whl/cpu)
pip install -r requirements-dev.txt        # runtime (requirements.txt, no torch) + dev tools; pinned, Python 3.14
pip install --no-deps -e .                 # the dubeval command
printf 'GEMINI_API_KEY=%s\n' "<key>" > .env  # optional: turns on the translation check
pytest -m "not slow"
```
- If a pinned version has no wheel for your system, install from pyproject's ranges: `pip install -e ".[dev]"`.
- The first evaluation downloads the faster-whisper `base` model (~145 MB, Hugging Face cache). Run one evaluation
  before a demo so the download is done.
- **The runtime has no PyTorch** (`requirements.txt`): speech recognition runs on CTranslate2 and, on an NVIDIA GPU,
  needs only cuBLAS (`cublas64_12.dll` + `cublasLt64_12.dll`, 736 MB), found by `asr._add_cuda_dll_dirs` in the GPU
  pack folder (`DUBEVAL_CUDA_DIR`, default `~/.cache/dubeval/cuda`), NVIDIA's pip packages, or PyTorch's `lib`;
  without them it falls back to the CPU on its own. Keep torch out of the runtime: the desktop app ships
  `requirements.txt`.
- `.env` is git-ignored; a fresh clone has none. Without a key everything works except the translation check,
  which the report shows as "not measured" with the reason.
- The real share link, Perso and Gemini need network access. The fast tests are fully offline.

## Project map
```
qa.py                    CLI entry point → dubeval/cli.py
dubeval/perso_api.py         Share links: parse_share_url, get_shared_project (public GET), download_media
dubeval/pipeline.py          evaluate_share (fetch → cached download → evaluate → translation check), run_share_evaluation
                         (+ report files), run_comparison (two links → comparison files); per-link cache in data/cache/
dubeval/evaluate.py          All measurements (pure). run_full_evaluation returns the results dict (SCHEMA_VERSION)
dubeval/inputs.py        Inputs: local files, links (yt-dlp for pages), one audio track of a file, SRT/VTT subtitles;
                         probe + check (readable, has audio, ≤ DUBEVAL_MAX_MINUTES); a problem with the input
                         itself raises InputError, so the failed job offers no Continue (jobs.Job.retry_helps)
dubeval/asr.py           Speech recognition over faster-whisper (default) or openai-whisper (DUBEVAL_ASR); same
                         output shapes, seeded; GPU when it works, else CPU
dubeval/settings.py      API keys (Claude, Gemini, ChatGPT) from Settings → API keys: data folder's .env, status only
dubeval/packs.py         Optional downloads (meaning, gpu, large_model): pinned sources + SHA-256, resume, install,
                         remove; CATALOG = Settings → Models (built in + downloadable, grouped; /api/models)
dubeval/languages.py     Whisper's language names by code (copied, MIT): the runtime has no openai-whisper;
                         display_name() gives a name in the interface language from language_names.json
                         (Unicode CLDR, written by tools/build_language_names.mjs with Node's Intl)
dubeval/pairing.py       Same video, time shift and coverage from motion, frame hashes and background sound; the
                         dub's audio is laid onto the original's timeline (one shift, or part by part)
dubeval/schema.py        The report.json format (Pydantic models, FORMAT_VERSION) and its JSON Schema
schemas/                 report.schema.json, generated by `dubeval schema` (a test keeps it current)
pyproject.toml           Package `dubeval`, the `dubeval` command, dependency ranges and extras
dubeval/translation_judge.py Translation check: Claude, Gemini (REST), ChatGPT (OpenAI REST), local Ollama; retries + fallbacks
dubeval/numbers.py           Numbers check: the digits each dub line says vs its original line (pure, offline)
dubeval/report.py            build_report(results, lang): levels, verdict, intervals, things to check; renderers (pure)
dubeval/intervals.py         Problem intervals: collect from every check, merge (< 0.5 s), clip, round 0.1 s, sort (pure)
dubeval/compare.py           Compare mode: facts, decide (the rule), build_comparison, text/HTML renderers (pure)
dubeval/validation.py        Known-problem validation: copies each dub with one problem at a known time, compares with a
                             re-encoded control; caught / false alarms per language pair (docs/validation.md)
dubeval/batch.py             Batch mode: parse links file (+ person's verdicts), summary rows, agreement, CSV/text (pure)
dubeval/voice_quality.py     Voice quality on both tracks at the same moments and volume, where both speak: Audiobox
                             Aesthetics with its download (graph bundled, Meta's weights file in the pack), else DNSMOS P.835
dubeval/speaker.py           Voice similarity: WeSpeaker ONNX (downloaded once, SHA-256 pinned), numpy Kaldi fbank
dubeval/api.py               REST API (FastAPI) over the same job runner; token auth when DUBEVAL_API_TOKEN is set
dubeval/ort_session.py       ONNX Runtime CPU sessions (threads sleep between runs: two models taking turns ran 6x slower)
dubeval/localweb.py          What the local servers share: Host check, security headers (CSP), port bound before the link
dubeval/webapp.py            Web interface server (dubeval web): uploads, evaluations and comparisons, report, media, waveforms, votes
                             (on the report rebuilt with the current rules, `_current_report`, the list the review numbers);
                             a pasted link downloaded at once into uploads (`/api/uploads/link`, any kind: `inputs.direct_link`
                             turns Dropbox/Drive/OneDrive shares into file links); Settings → Storage
                             (opens the data folder, `/api/settings/open-data`);
                             127.0.0.1 only, per-launch token kept in a same-site cookie, Host header checked
dubeval/web/                 The page: plain JavaScript modules, no build step (boot = the start screen's words, app, home = the Evaluations screen,
                             start (+ drafts), progress, review, compare, history, settings, export = the Export dialog,
                             shell = the sidebar's Help / Send feedback / What's new and the update state + CSS)
dubeval/library.py           The Evaluations list: cards of finished run folders (card.json, thumb.jpg), rename,
                             delete, drafts (data/drafts/), and the inputs that pruning must spare
dubeval/preview.py           Start-page previews: Perso share (public endpoint), web page (yt-dlp, no download), file
                             (one ffmpeg frame); pictures as data: URIs. GET /api/preview
dubeval/local_judge.py       The local translation checker pack (Ollama CPU+Vulkan + Gemma 4 12B, pinned) and its server
dubeval/xlsx.py              A dependency-free one-sheet .xlsx writer (Export's problem list, webapp.problem_rows)
dubeval/clips.py             Export → Problem clips: each moment as a side-by-side clip (original | dub, played twice: the
                             original's sound, then the dub's) and "Problem clips.html" saying what's wrong at each
dubeval/release_notes.py     What's new per version in en/ko/pt/es; the lines are in release_notes.json (add the new version's
                             with every release), which installed apps read at a release's tag
dubeval/web_text.py          Every web-page text in en/ko/pt/es (keys w.*), merged into i18n.TEXT
dubeval/__main__.py          python -m dubeval = the dubeval command (how the desktop app starts the server)
tools/build_desktop.py       Windows and macOS build: Python 3.14 + requirements.txt + DubEval + base/speaker models →
                             desktop/resources/ (macOS: a pinned python-build-standalone CPython, built by
                             .github/workflows/build-mac.yml on one of GitHub's Macs)
desktop/                     Electron app: main.js starts `python -m dubeval web`, reads the launch link,
                             opens it in a sandboxed window (status.html while starting); updater.js (electron-updater,
                             GitHub Releases) + preload.js (window.dubevalShell: updates only); README.md there
dubeval/network.py           The computer's trusted certificates (truststore) and proxy (WinHTTP, PAC) at start-up;
                             describe() turns a blocked connection into a plain message
dubeval/paths.py             DATA_DIR (DUBEVAL_DATA, default ./data): output, cache, history, votes, jobs
dubeval/feedback.py          Reviewer votes (real problem / false alarm) per interval; per-check summary
dubeval/usage_stats.py       Opt-in usage stats from the app: off until the person says yes; only listed values can be sent
dubeval/history.py           Records every evaluation to data/history.jsonl; summarize() and the history text view
dubeval/version.py           TOOL_VERSION (= desktop/package.json's version, tested) and REPOSITORY_URL (Help, Send
                             feedback, and the releases the app updates from)
dubeval/report_text.py       Every report sentence in en/ko/pt/es (keys r.*), merged into i18n.TEXT
dubeval/i18n.py              UI text (TEXT), fixed progress/error messages (MESSAGES), t(), translate_message()
dubeval/jobs.py              Background job thread + Progress model; state and results kept in data/jobs/ across restarts;
                             evaluations take turns (queued=True: one runs, the others wait in line and start by themselves)
dubeval/awake.py             Keeps the computer from idle sleep while a job runs (Windows SetThreadExecutionState, macOS caffeinate)
dubeval/speed.py             The time-left estimate: seconds per minute of video from this computer's last 10 single evaluations
                             that measured everything themselves (data/speed.json); none until there is one
dubeval/cli.py               Argument parsing, quiet native logs, exit codes
dubeval/lip_sync.py          Lip sync: StableSyncNet (LatentSync 1.5) on the same moments of both videos, the original
                         as the zero point (the lip_sync download; runs on onnxruntime, no torch)
dubeval/models/              Bundled models with their licenses (README.md there): MediaPipe face landmarker (lip
                         movement), DNSMOS P.835 ONNX (voice quality), the Audiobox Aesthetics and lip-sync graphs (weights in their downloads)
tests/fake_perso.py      Fake share endpoint + media host, with a real response shape
tests/sample_results.py  A realistic results dict (make_results) for report/CLI/UI tests
tests/data/sample.mp4    Local only (git-ignored): any ~30 s English talking-head MP4; the 2 slow tests skip without it
data/output/             App run folders and results.json, created at run time (git-ignored); kept until deleted
data/drafts/             Start pages filled in but not run (the home screen's Draft cards; git-ignored)
data/cache/              Per share link: downloaded videos + whisper_cache.json (git-ignored)
output/                  The CLI's default --out folder (git-ignored)
data/history.jsonl       Evaluation history, one JSON line per evaluated dub (git-ignored)
data/feedback.jsonl      Reviewer votes on problem intervals (git-ignored)
```

## Rules
- **Reusing code from another project** (PersoDub is AGPL-3.0-or-later, so its code may be reused): add an entry
  to `NOTICE` with the files, the source, its copyright line ("ESTsoft corp." for PersoDub) and its license, and say
  it was modified. Never use the "Perso" or "PersoDub" names or logos for DubEval itself (ESTsoft trademarks).
- **Scope is share-link evaluation.** The tool only uses Perso's public share endpoint
  (`GET https://api.perso.ai/video-translator/api/v1/projects/shared/{seq}`) and the media host
  (`https://portal-media.perso.ai`, paths URL-encoded). Don't add Perso account features (dubbing, credits, API
  keys). Reference: https://developers.perso.ai/llms.txt.
- **Secrets:** never print, log, commit or read the values of `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`; they live
  in the git-ignored `.env` (development) or the data folder's `.env`, written by the Settings page
  (`dubeval/settings.py`; it wins over keys set elsewhere). The page and its routes never return, log or echo a key,
  not even in a validation error (`PUT /api/settings/keys/{provider}` reads the body by hand); tests point both
  `.env` files at temp files (`tests/conftest.py`). Send the Gemini key only in the `x-goog-api-key` header, never
  in a URL.
- **Usage stats are opt-in and can hold no free text:** `dubeval/usage_stats.py` sends nothing until the person says yes,
  and closing the question isn't a yes. Every field comes from a fixed list or strict pattern, and `worker/validate.ts`
  refuses anything else. Never add titles, file names, links, paths, error messages or measured values, and never a number
  that follows one app across weeks. A new field or event needs both lists, `docs/privacy.md`, the question and the Privacy
  tab. Stats never affect an evaluation: problems are logged and dropped. Tests never post (`tests/conftest.py`).
- **History recording never fails a run** (errors are logged); tests write history and votes to temp files
  (`tests/conftest.py`).
- **Calibrate with evidence:** reviewer votes (`qa.py feedback`, cast on each problem's card in the review) and batch
  labels (`dubeval label`, `qa.py batch`) are how thresholds should change; a check marked "flags too much" is the
  first candidate.
- **API security:** without `DUBEVAL_API_TOKEN`, `serve` refuses any host but 127.0.0.1 and answers only requests
  whose Host header is 127.0.0.1 / localhost (DNS rebinding); with it, every route but `/health` needs the Bearer
  token. Keep both. Job ids from URLs are validated (`jobs.JOB_ID_RE`) before disk access.
- **Docker:** no torch (runtime requirements), non-root `app` user, `/data` created and owned by `app` before `VOLUME`, models baked
  in. After changing system dependencies, rebuild and run the full suite inside the image (see INSTALL.md, Docker).
- **CI** (`.github/workflows/tests.yml`) must stay green on Linux, macOS and Windows; it needs no secrets.
- **Tests never call real services.** Perso: `tests/fake_perso.py`. Gemini/Claude: `tests/conftest.py` removes
  provider keys from the environment and stubs the pipeline's translation check; judge tests use fake sessions
  and clients. Keep it that way.
- **Never fail a run because of the translation check:** any problem becomes a not-measured result whose reason
  is a text key (`not_measured("r.judge.…")`).
- `dubeval/evaluate.py` and `dubeval/report.py` stay pure (no file writes except temp audio, no network, no import side
  effects). The web page (`dubeval/web/`) only renders what the server sends; it grades and decides nothing.
- **Levels, thresholds and messages live only in `dubeval/report.py`** (thresholds are constants at its top), interval
  thresholds in `dubeval/intervals.py`, and the compare decision rule only in `dubeval/compare.py` (`RULES`). The UI and
  CLI render reports and comparisons; they never re-derive levels or decisions. Every Good/Check/Poor row states
  how it's graded (`thresholds`): the app and the HTML report show it for every row, the text report for the rows that
  need attention.
- **The quality score is a summary beside the verdict** (`report._score`, owner's decision, 2026-11-20): out of 100,
  a Good check counts 100 and a Poor one 0; one at Needs review counts by where its result sits between the Poor and
  Good limits (`_scale`; translation and voice quality: the share of lines or stretches without a problem, `_share_ok`;
  no number to place: 50; at most `SCORE_CHECK_MAX`, owner's decision 2026-11-20), a section is their average, and the score
  is the sections' weighted sum (`SCORE_WEIGHTS`: translation 30, timing alignment 25, speech 15, timing & audio 15,
  same video 10, lip sync 5; the video file has no weight). **The number is the one worked out** (owner's decision,
  2026-11-21): no cap holds a Needs review dub at 89 (only a dub with every check Good scores 100: `min(value, 99)`), and
  in a Poor verdict each Poor result costs at least a set amount by how serious it is instead of its small share
  (`POOR_COSTS`, `POOR_SEVERITY`, 2026-11-22): **unusable** 100 (no speech in the dub, the wrong language, another
  video, a broken file), **minor** 20 (loudness, silence: the mix fixes them), **serious** 40 for every other check
  that can be Poor. Put a new check that can be Poor in a level by a stated reason, and move a level's number only on
  graded dubs (the reviewer graded a 5 dB-off dub Good, and agreed with 4 of 5 Poor translations). **A check without a level is one of three kinds** (`report._absent`, tagged
  where the row is made): `na` doesn't apply to this dub (lip sync on a dub that isn't lip-synced, the lip check with
  nothing to compare, voice similarity for human or stock voices, sound sync on a replaced background, no line long
  enough, line checks on a mostly-music video, speech checks when the original has no speech): left out, its points
  shared, the coverage untouched; `missing` couldn't be measured (no checker or download, the check off, speech not
  recognized, the model can't tell, errors): shared too, but `score.coverage` drops and the message names it; `dub` the
  dub itself made it impossible (no speech in the dub, `DUB_SPEECH_CHECKS`): counts as 0, never shared. Under
  `COVERAGE_MIN` (80%) the score is provisional, under `SCORE_MIN_COVERAGE` (50%) there is none ("Too little measured").
  Translation counts only when the translation check ran (`SCORE_REQUIRES`); otherwise the score is `provisional`.
  Don't share out a `dub` check or call an unrecognized language `dub`: the first lifts a broken dub, the second blames
  the dub for a recognition gap. Every
  report prints the weights and each section's points (`score.parts`, `score.rule`). It never replaces the verdict and
  is never a fact the compare rule reads (a comparison shows it beside each dub, like its name). The weights are
  reasoned, not measured: change them only on the owner's word, with `docs/metrics.md` and `docs/usage.md`.
- **Reports put problems first** (`render_text`, `render_html`): verdict, things to check, the measures that need
  attention in full, what passed in a line each (folded with its explanation in HTML), what wasn't measured. Don't go
  back to printing every row in full section by section: a 7 s clip printed 1,700 words. Checks that didn't run are
  put together by reason (`report._skipped`, `report.skipped`; a row says why in `cause`), with what to do when there
  is something (`r.skip.*`); `SKIP_BANNER_MIN` of them for one reason show as a banner in the app.
- **A dub's name is only a label** (`pipeline.dub_name`, `compare.shown_names`): it's never part of `facts` or the ranking.
- **The decision rule is deterministic and printed:** rule order, "skip a rule when any dub lacks its value", ties
  keep input order, the reasoning compares #1 with #2, rule 1 (a dub with fewer of the key checks `KEY_CHECKS` measured never
  wins), the caution when the winner still lacks key checks, the held recommendation when DubEval isn't sure of the
  winner (`HOLD_FOR`, `c.held*`), the recommendation's `status` (`recommended` = `ready`, `provisional` = held,
  `not_ready` = every dub Poor: only `recommended` may say "Deliver" or show ★), and the all-Poor warning are part of the spec; change them only together with `c.rule.*` / `c.why.*` texts,
  `c.rules_order`, `tests/test_compare.py`, `docs/usage.md` and this file.
- **Any language pair:** the dub language comes from the share metadata (base code: `es-MX` → `es`). A language
  without a pace rule (`SPEECH_RATE`) or without a Whisper model is "not measured" with the reason, never graded
  silently and never a crash.
- **Cross-platform (Windows, macOS, Linux):** pathlib for paths, `encoding="utf-8"` on every text file, no shell
  commands (ffmpeg comes from `imageio-ffmpeg` and runs as an argument list), OpenCV paths through `_cv2_path`.
- Verdict rule: any Poor → Poor; otherwise any Check → Needs review; otherwise Good. Info and not-measured rows
  never count. **How sure** (`report.sure_of`, `_apply_sure`, Step 2): with little speech (< 35% of the video or
  < 10 s) or unclear speech (< 90% confident), only the `SURE_ANYWAY` measures (distortion, same video, coverage,
  file, sound sync, speech found) can make it Poor; a replaced background caps silence and loudness at Check; a dub
  whose language wasn't recognized, or whose translation check didn't run (a required check), is never Good; a backup
  judge model is noted. Compare mode holds its recommendation (`compare.HOLD_FOR`) when the dub ranked first has a
  speech or translation reason; the order still shows. The headline says why. Issues the judge flags `may_be_recognition_error` are listed but never make anything Poor; a meaning line it scores 4 or lower still makes meaning Check and is a moment to listen to (a reversed meaning marked "maybe misheard" once vanished). The prompt allows the flag only when a similar-sounding word explains it.
- The pipeline reports progress only through `Progress` objects; the page polls the job, the worker thread never
  talks to the page. The desktop app hears it as `DubEval-progress:` lines (`webapp._job_progress`), for the bar on its
  taskbar or Dock icon.
- **One evaluation runs at a time** (`jobs.start_job(..., queued=True)` for everything the web interface evaluates): the
  others wait in line (`queued`) and start by themselves; two at once compete for the processor and graphics card, and two
  speech models can run out of graphics memory. Model downloads don't wait. Tests get their own job list (`tests/conftest.py`), and a test helper
  that waits for a job waits through `queued` too.
- **Voice quality compares the dub with the original at the same moments and volume**, never in absolute terms: DNSMOS
  scores fall with background music, which both tracks share, and move with volume alone (`voice_quality._at_volume_of`).
  It was chosen after UTMOS failed on real dubs (every real recording scored ~1.2-1.5, even after voice separation);
  don't swap in a studio-speech model without testing it on real Perso dubs. Window bands are in `dubeval/intervals.py`
  (`VOICE_SIG_DROP`, `VOICE_OVRL_DROP`, `VOICE_FLOOR`). A change to what the model is given needs a new cache key in
  `evaluate.py` (now `vq3`, with the scoring model in it), not a `CACHE_VERSION` bump, which would drop all recognition.
- **With the `voice_quality` download, Audiobox Aesthetics grades voice quality, not DNSMOS** (owner's decision,
  2026-11-13; `voice_quality.scorer()`): its production-quality score stays steady over music, where DNSMOS swings and
  can't grade. Bands are `VOICE_PQ_DROP` / `VOICE_CE_DROP` in `intervals.py`: a stretch is judged against the original
  there and against how the dub usually compares with it (`intervals.voice_window_levels`). The bundled graph reads
  Meta's `model.safetensors` unchanged (rebuild it with `tools/build_audiobox_onnx.py`; never redistribute the
  weights or host a converted copy). DNSMOS stays bundled: it grades without the download, and its background score
  is kept in every stretch because `report.sure_of` tells a replaced background by it (without it one test dub's
  silence row went from Check to Poor). Results say which model scored (`scorer`, `scale`); never grade one model's
  numbers with the other's bands.
- **Voice similarity says same voice, another voice, or can't tell** (`report._similarity`, 2026-11-13): 40% or more
  is the same voice (Good), under 30% another voice, between them partly alike (both Check, never Poor: a new voice can
  be deliberate). A result under 40% is graded only when the model recognises the original's own speakers
  (`original_self`, each original line against the other original line most like it, 60% or more: `VOICE_KNOWN` in
  `intervals.py`); else the row isn't graded and says so with both numbers. Don't bring back the rule that skipped lines
  with a loud background: it left 16 of 20 test dubs unmeasured, and the scores with the music in equalled those with
  the voice separated. Line-level "different voice" intervals are relative to the dub's own median and need a
  recognised original too.
  The model downloads on first use to `~/.cache/dubeval/` (`DUBEVAL_MODELS` overrides); tests never download
  (`tests/conftest.py`).
- Lip sync is measured automatically only when the dub is lip-synced. **With the `lip_sync` download it counts in the
  verdict** (owner's decision, 2026-11-10, on one tested real dub): the share of checked moments whose lips line up is
  Good from 90%, Poor at 30% or less, Check between (`report.LIP_SYNC_PCT`); not measured (no download, too few faces,
  a narrated original, a recut dub) never counts. The download's check is StableSyncNet
  (`dubeval/lip_sync.py`): each moment is judged against the original at the same moments (its zero point), and
  the bundled graphs read ByteDance's checkpoint unchanged (rebuild them with `tools/build_syncnet_onnx.py`, never
  redistribute the weights). **Without it the lips aren't checked**: the rough lip-movement estimate that once ran in
  its place (MediaPipe mouth opening against loudness) was removed on the owner's instruction (2026-11-13); it scored an
  in-sync original −0.20. Don't bring an estimate back under another name; the row says where to get the download
  (`r.lips.no_download`). MediaPipe's face landmarker stays: the check aligns the face with it.
- The web interface keeps options few: per dub its kind and language, subtitles, the original's language, the
  translation check on/off and the lip-sync check (automatic for lip-synced share links; offered only with its download). The Whisper model is
  automatic (`asr.default_model`: `large-v3-turbo` when it is downloaded, with or without a graphics card, else `base`;
  owner's decision, 2026-11-15: on a processor it is a few times slower, 16-18 s per minute of sound against 5 on one
  2025 laptop, and `base` read 4 of 36 languages well; the start page's More options and `WHISPER_MODEL` / the CLI can
  name one); script accuracy is CLI-only.
- **report.json is a contract** (`dubeval/schema.py`): renaming or removing a field, or changing its meaning, bumps
  `FORMAT_VERSION`; adding a field doesn't. After any change run `dubeval schema > schemas/report.schema.json`.
- **Speech recognition goes through `dubeval/asr.py` only.** Both backends must keep returning the same shapes, and
  cache keys include `asr.model_id()` so results from different recognizers never mix.
- **Meaning** (`pipeline.judge_lines` → `translation_judge.judge_translation`): the judge reads the speech line by line. The judge is chosen by `--judge` / `DUBEVAL_JUDGE` (`auto` = Claude → Gemini → ChatGPT → Ollama; ChatGPT uses an OpenAI API key,
  `OPENAI_API_KEY`, sent only in the Authorization header); keep
  `RESULT_SCHEMA`, `SYSTEM_PROMPT` and `DUB_TYPE_RULES` in `translation_judge.py` and change them only together with
  the judge tests. **There is no offline meaning screen** (owner's decision, 2026-11-20): BGE-M3 sentence similarity
  found 6 of the 25 lines Gemini scored low, and a clean result made a translation look checked when it mostly wasn't
  (`docs/validation.md`). It was removed with its 585 MB download (`packs.remove_retired` deletes an installed copy at
  start-up); without a judge the translation isn't checked and the score is provisional. Don't bring a similarity
  screen back as a stand-in. The numbers check (`numbers.py`, `pipeline.check_numbers`) compares digits only,
  skips lines with digits on one side, flags only a number replaced by another (languages say one number differently: 7월 4일,
  200만) and is Check-only (a recognizer can mishear a digit). Tests never call a judge and never probe Ollama (`tests/conftest.py`). `--dub-type` (ai_clone | ai_stock | human) skips
  voice similarity for human and stock-voice dubs (`pipeline.apply_dub_type`).
- **Speech that can't be graded** (`report.speech_problem`, `SPEECH_DEPENDENT`, `UNRECOGNIZED_PROB`): an unsure
  third-language detection makes the language row and every speech-based row "not graded" (with the reason), and the
  pipeline doesn't run the translation judge on that speech (`pipeline._speech_unrecognized`);
  long silences are still listed for an unrecognized dub, from the voice detector alone (`evaluate.voice_gaps`,
  `intervals._voice_gaps`; same category and bands, moments only, never a row);
  a dub without speech adds a Poor row (nothing was dubbed), an original without speech a Check row. Both were set from
  the 12-pair labelled set of 2026-10-25. In `auto`, and for the judge the app's start page chose (it preselects
  the first with a key), a judge with a rejected key or no credit hands over to the next one
  (`translation_judge.ACCOUNT_PROBLEMS`), and the report notes it (`handed_over`, `r.sure.judge_handover_*`); a judge
  chosen with `--judge` never does.
- **Downloads (`dubeval/packs.py`)**: every file has a fixed source (a Hugging Face revision, a PyPI version, a GitHub
  release or a registry digest, never `main` or "latest") and a SHA-256 checked before it is installed; nothing
  downloads unless a person asks. A file already in the pack's folder with the right checksum is kept, not downloaded
  again. The local judge pack (`dubeval/local_judge.py`) takes only the Ollama files it needs out of the release zip
  by range requests (Windows: CPU + Vulkan; a Mac with Apple silicon: the programs and libraries inside Ollama.app,
  Metal built in, without its MLX engine) and runs DubEval's own `ollama serve` on a free 127.0.0.1 port while DubEval
  runs. A Mac's downloaded programs get their run permission and library links when the server starts (`_prepare`).
  There is no pinned runtime for an Intel Mac or Linux (`local_judge.this_computer`). To update it, regenerate the pins
  (versions, sizes, SHA-256) for the zip members of both computers (`tools/pin_ollama_runtime.py`) and the registry
  manifest. Changing a source
  means new checksums.
- **Evaluations stay until the person deletes them** (like PersoDub's projects): the app's run folders are not pruned
  (`MAX_KEPT_RUNS` 0), and the pruning of uploads and of the share-link cache spares every file a kept evaluation plays
  or a draft holds (`library.referenced_inputs`). Deleting an evaluation deletes its folder and the uploads only it
  used, never a file the person chose from their own disk. Keep both when changing any pruning.
- **Web interface security** (`dubeval/webapp.py`): 127.0.0.1 only (`--host 0.0.0.0` exists for a container, whose
  port is published to 127.0.0.1), a new token per launch kept in a SameSite=Strict cookie, the Host header checked
  (only 127.0.0.1 / localhost), media served only from a job's own input files, past reports only when the history
  names them and they're under the data folder. Every response carries `localweb` security headers: the page's CSP
  allows only its own files (no inline script or `style=` attribute in `dubeval/web/`), saved reports are sandboxed
  (no script). The server binds its port before printing the launch link (`localweb.bind`). Uploads and downloaded
  videos stop at `inputs.MAX_MEDIA_GB` (20 GB). Every ffmpeg call on a video passes `inputs.LOCAL_INPUT` before `-i`
  (no network from inside a file). Keep all of these. The page grades nothing: it shows the report's
  levels and texts.
- **The app icon is DubEval's own** (2026-10-28): the original and the dub as two glowing timeline tracks (cyan-blue,
  violet-pink) under a white playhead, on a dark navy tile. Sources: `desktop/build/icon.svg` (48 px and up) and
  `icon-small.svg` (16-32 px, bolder and flat); `icon.png`, `icon.ico`, `docs/images/icon.png` and
  `dubeval/web/icon.png` are rendered from them. It replaced a blue waveform-and-check tile (2026-10-26), which had
  replaced PersoDub's icon (that needed ESTsoft's permission).
- **Releases and updates:** the version lives in `dubeval/version.py`, `desktop/package.json` and `pyproject.toml`
  (a test keeps them equal) and every version needs its lines in `dubeval/release_notes.json`. Installed apps update themselves from the
  GitHub Releases of `REPOSITORY_URL` (`build.publish`): publish the installer, its `.blockmap` and `latest.yml` together,
  and (since 0.1.7) the Mac's `DubEval-Mac.dmg`, `.zip`, its `.blockmap` and `latest-mac.yml` in the same release.
  **Since 0.1.6 the installer is signed** (ESTsoft Corp., through the company's internal portal, by hand):
  `npm run build:windows:release`, sign in the portal, then `npm run release:windows:finish`, which checks the signature
  and rebuilds `latest.yml` and the `.blockmap` from the signed file (signing changes the bytes; with the build's
  `latest.yml` every app refuses the update). Never upload an installer `finish` didn't process, and never publish an
  unsigned one again: the app's `publisherName` (`build.win.signtoolOptions`) makes electron-updater refuse any update not
  validly signed by that CN. The portal's address stays in the git-ignored `desktop/codesign.local.json`, never in the
  repository. Steps in `desktop/README.md`.
- **The page keeps its address between launches:** what it keeps in the browser (language, sidebar width, history period)
  belongs to the address, so `dubeval web` takes the first free of `webapp.USUAL_PORTS`. Don't go back to a new port per
  launch, and keep `Cache-Control: no-cache` on the page's files, or an update would run yesterday's script from the cache.
- **The start page stays outside the app's archive** (`asarUnpack`, `desktop/main.js` `STATUS_PAGE`): with the
  `grantFileProtocolExtraPrivileges` fuse off, a window can't open a `file://` page inside it and shows nothing.
- **A downloaded update installs only on Restart to update** (`autoInstallOnAppQuit = false`, a test keeps it): closing the
  app never installs. The restart isn't silent, unlike PersoDub's: DubEval's update replaces about 9,000 files, and a silent
  install left the person with no window for minutes. It asks nothing either (since the installer after 0.1.7):
  `desktop/build/installer.nsh` skips the "who is this program for" page and the Finish page when the installer runs
  with `--updated`, and starts DubEval itself; a first install still shows both. A change to this flow needs a run of the real updater: `npm start`
  doesn't update, so use a packaged app with `DUBEVAL_UPDATE_URL` (`desktop/README.md`).
- **The macOS app is signed with ESTsoft's Developer ID and notarized** (2026-11-18; Apple Silicon only): built by
  hand on a Mac with the certificate in its keychain and the notarization key saved as `dubeval-notary`
  (`APPLE_KEYCHAIN_PROFILE=dubeval-notary npm run dist:mac`, in the Mac's own Terminal: SSH can't use the key), with
  the hardened runtime and only the entitlements in `desktop/build/entitlements.mac.plist`. electron-builder skips the
  bundled Python and models (`signIgnore`) and `desktop/after-pack.js` signs their Mach-O files with the Developer ID,
  the hardened runtime and a timestamp; a new native library is covered by that, a new kind of exception needs an
  entitlement and a notarization run. GitHub's Macs make an ad-hoc test build (`dist:mac:adhoc`, `build-mac.yml`,
  which publishes nothing). The certificate, its password and the notarization key never go in the repository or a
  log. Keep three things: it never writes inside its own bundle (Python `-B`, every `.pyc` compiled at
  build time, `NUMBA_CACHE_DIR` in the data folder), every release carries its `latest-mac.yml`, `.zip` and
  `DubEval-Mac.dmg` beside the Windows files (it updates itself since 0.1.7, and only from an update signed with the
  same Developer ID), and its Python is one pinned download with a SHA-256 (`MAC_PYTHON`). Details in `desktop/README.md`.
- **Labels are a person's answer key** (`dubeval label`, `dubeval/labeling.py`): never fill them from DubEval's own
  output or from an LLM, or calibration only measures DubEval against itself. The page hides DubEval's verdict until
  the person has answered, listens on 127.0.0.1 only, opens only with its launch link (token cookie, Host check,
  so no other web page can read or change the labels), and serves only files named in the sheet.
- **Timing moments need the voice detector to agree** (`evaluate._detector_agrees`, `asr.voice_activity(fine=True)`,
  `MISMATCH_SILENT_VOICED_MAX`, `MISMATCH_SPEAKING_VOICED_MIN`). Don't use the detector's default settings here: they
  join anything closer than 2 s, which hides real short gaps and still looks fine on the known-problem test (its planted
  silences are 3 s or longer). Check changes against `data/feedback.jsonl` votes too. The overlap score stays on words.
- **Line timing** (`evaluate.match_segments` → `line_timing`, raw numbers in `results["segment_alignment"]["lines"]`)
  is graded in `report._line_fit` (`LINE_BAND_PCT`, `LINE_MIN_DIFF_SEC`, `LINE_FIT_SHARE`, `LINE_OVERRUN_SHARE`,
  `LINE_POOR_MIN`; `report.line_off` is the one rule for a line being off, used by the measure and the intervals); its
  measuring limits (`LINE_MIN_SEC`, `LINE_OVERRUN_SEC`) are in `dubeval/evaluate.py`, interval bands
  (`LINE_POOR_PCT`, `LINE_OVERRUN_POOR_SEC`) in `dubeval/intervals.py`. On a mostly-music video (`little_speech`) neither
  line row is graded or listed (`report._apply_little_speech`). Don't confirm line flags with the voice detector: it was
  tried, and on real dubs it mostly agreed with the words, while settings that removed false alarms also removed a line a
  person voted real (`docs/validation.md`).
- **Pairing runs before any measuring** (`pipeline.pair_videos`): clearly different videos stop a files/links run
  (`--allow-different-videos` overrides; share links are only reported), and a shift ≥ `MIN_APPLIED_OFFSET` (0.1 s)
  is corrected, so every time in the results is the original's. Pairing never fails a run: an error becomes
  `pairing.not_measured`. Bands live in `dubeval/pairing.py` (evidence) and `dubeval/report.py` (`SAME_VIDEO_PCT`,
  `COVERAGE_PCT`); the `missing_in_dub` interval threshold is in `dubeval/intervals.py`.
- **Inputs are checked before any measuring** (`inputs.check`): an unreadable file, a file without audio, or a too
  long video fails fast with a plain message. A pipeline's `pipeline["input"]` (files) or `pipeline["share"]` (Perso)
  says what was evaluated; readers use `input` first, then `share`.
- If you rename or remove result keys, bump `SCHEMA_VERSION` (`dubeval/evaluate.py`).

- **The translation check is a rubric** (`translation_judge.py`): every line scored 1-10 on five criteria against the
  written score descriptions in `SCORE_BANDS`, reasons for scores of 7 or lower, an ideal translation and one of
  `ERROR_TYPES`. The judges only read text (transcripts and subtitle files); they never listen to audio. Grading lives
  in `report.py` (`RUBRIC_FLAG`, `RUBRIC_POOR`, `RUBRIC_POOR_LINES`, `_rubric`); only meaning can be Poor, and only with
  3 or more serious lines or most lines. **The report shows it as one row** (`translation_check`, level = the worst of
  the five, the five scores in its `parts`): don't split it into rows again, five rows said one thing and inflated
  every count of items (the headline's, compare mode's "fewer Needs review items"). Every requested line must be answered (`_ask_again`, `_rubric_result`):
  anything less is not measured (`r.judge.incomplete`), never a grade from part of the dub. The result keeps each
  request's model (`chunks`, `models`). Results saved before the rubric
  (`meaning_score` 1-5, no `rubric` key) still render with the old rows.
- **A language the speech model reads badly gets a note, not a grade** (`report._weak_recognition`,
  `WEAK_RECOGNITION_PCT`, 2026-11-15): when the model used read more than 10% of characters wrong in the dub's or
  the original's language on test sentences (`languages.RECOGNITION_ERRORS`: 25 read FLEURS sentences per language,
  36 languages, `large-v3-turbo` and `base`), the report says so under the verdict (`r.sure.weak_dub`,
  `r.sure.weak_original`), and points to the large model when that one reads the language well (`r.sure.weak_tip`).
  It changes no level and holds no comparison: the numbers come from clean read speech, not from the dub. A model
  or language not in the table says nothing. Measure again when a recognizer changes
  (`data/validation/languages/`, `docs/validation.md`).
- **The second listen stays off** (`pipeline.listen_again`, `DUBEVAL_SECOND_LISTEN`; tried 2026-11-15): recognizing each
  marked-down line again on its own and judging it again where the words differ lowered agreement with the reviewer
  (meaning 7 → 5 of 16 with `base`, 7 → 7 with `large-v3-turbo`, and two right verdicts lost). A line heard alone often
  comes out as other wrong words, a recognizer told the dub's language wrote an untranslated English line out in Korean,
  and the judge scores the same words differently when asked twice. Don't turn it on by default without the reviewer's
  answers on the flagged lines themselves (`docs/validation.md`).

## Conventions
- Plain functions returning dicts. Type hints, one-line docstrings, comments only where the why isn't obvious.
  Use `logging`, never `print` (except the CLI's own output). Match the surrounding style.
- User-facing failures raise `PersoError`, `ValueError` or `FileNotFoundError` with an actionable, plain-language
  message; add the exact English text to `i18n.MESSAGES` so the UI can translate it.
- `None` means "not measured". Never use sentinel numbers.
- **Everything a person reads follows the interface language.** UI text → `dubeval/i18n.py` `TEXT`; report sentences
  → `dubeval/report_text.py`; fixed progress/error messages → `i18n.MESSAGES`. Every string needs `en`, `ko`, `pt`,
  `es` with identical `{placeholders}` (`tests/test_i18n.py` enforces it). Counted texts use `_one` / `_many`
  keys. Never hard-code UI text in `dubeval/web/` or sentences in `report.py`.
- In Korean, don't put a particle (이/가/을/를/은/는) right after a `{placeholder}`; rephrase instead.
- Explanations say what was measured, what it means for a viewer, and what to do. No file references
  (metrics.md) and no jargon (IoU, r, CER, dBFS) in anything the user reads.
- **The web interface looks like the PersoDub desktop app** (owner's decision, 2026-10-22): dark only, its palette,
  12 px Onest type, a top bar, a left sidebar panel and a work panel on a darker desk; every colour is a token at the
  top of `dubeval/web/style.css` (credited in NOTICE). New screens use those tokens and components, not new colours.
- **Dropdowns are drawn by the page** (`select` in `style.css`: its own arrow, and `appearance: base-select` so the list
  opens inside the page). The system's dropdown on a Mac is a light list as tall as the screen with the arrow against the
  edge. Such a dropdown is only as wide as its chosen option: give a new one a width if something stands beside it.
- UI copy is short, plain, second person ("Paste a Perso share link").
- **A level has one name in each language**, the verdict's: Good / Needs review / Poor (ko 좋음 / 검토 필요 / 미흡, pt Bom /
  Precisa de revisão / Ruim, es Bien / Necesita revisión / Deficiente). `check` and "Check" are only the level's id in the
  code, the JSON and these notes; no text a person reads uses a second word (`tests/test_i18n.py`). The headline
  (`report._headline`, `overall.summary`) names the measures behind the verdict; what DubEval isn't sure of is
  `overall.sure`, one sentence each, shown under it; `overall.headline` keeps both in one text.

## How to do common tasks
- **Add a measure:** compute it in `dubeval/evaluate.py` (pure) and add it to the `run_full_evaluation` result →
  grade it in the right section function of `dubeval/report.py` with `_metric(tr, "<id>", level, message, value,
  display, graded)` → add `r.m.<id>`, its messages and its `r.g.<id>` grading sentence to `dubeval/report_text.py`
  in all four languages → add a test in `tests/test_report.py` (use `make_results(...)`) → update
  `docs/metrics.md`. New result keys need no schema bump; renames/removals do.
- **Calibrate thresholds:** run `qa.py batch` on labelled links (`link,good|check|poor`), read the agreement and
  `summary.csv` (every measure's level and value), change the constant, rerun (cached: seconds, no API calls).
- **Change a threshold:** edit the constant at the top of `dubeval/report.py` (or `dubeval/intervals.py` for intervals);
  the grading sentences read it. Update the bands in `docs/metrics.md` and `docs/usage.md`.
- **Add a pace rule for a language:** add `"<code>": (good, check)` to `SPEECH_RATE` in `dubeval/report.py` (chars/s for
  ko/ja/zh/th, words/s otherwise), a test in `tests/test_report.py`, and the band in `docs/usage.md` and `docs/metrics.md`.
- **Add an interval category:** add the id → `r.cat.*` label to `CATEGORIES` in `dubeval/intervals.py`, a collector that
  returns `_item(...)` ranges, its texts in `dubeval/report_text.py` (4 languages), a test in `tests/test_intervals.py`,
  and a row in metrics.md §7.
- **Things to check** are built from the moments (+ the possibly misheard lines and untimed warnings) in
  `_things_to_check` (`dubeval/report.py`); add new timed issues as interval categories instead. A finding
  (`problem_intervals[i]`, what a reviewer votes on) keeps its own range and says what it found in parts (`problem`,
  `original`, `dubbed`, `suggestion`, `doubt`, `line`; `description` is all of them in one text); a collector passes them
  to `_item`. `intervals.group_moments` puts the findings about one moment together (`MOMENT_OVERLAP`, the same
  `line`, or a finding without a line lying inside one about a line, `MOMENT_INSIDE`), the one that says most first (`LEAD_ORDER`: give a new category its place there). The screen's count, the
  review flow and the list go by moments. **A moment is Poor only when its measure is** (`report._cap_moments`,
  `MOMENTS_OF`): keep it, or a "Needs review" dub shows Poor moments again. **A check that passed lists no moments**
  (`report._drop_passed`, owner's decision 2026-11-21) except the local events its row doesn't measure
  (`LISTED_WHEN_PASSED`: long silences, wrong-language stretches, loudness jumps); problem time counts only what is
  listed. Compare mode counts and lists moments, a moment's other findings under its lead.
- **Change the translation check:** prompt and JSON schema are `SYSTEM_PROMPT` / `RESULT_SCHEMA` in
  `dubeval/translation_judge.py`. Summary and explanations must stay four-language objects. Gemini models are tried
  in `GEMINI_MODELS` order; `GEMINI_MODEL` / `GEMINI_THINKING` env vars override the first model and thinking.
  Keep them fixed names (no `-latest` aliases): a judge that changes underneath makes runs incomparable. Google can
  still serve a newer version under a name, so results keep what was asked for and what answered (`chunks`). A dub's
  later requests prefer the model of its first one (`model_order`); locking (`DUBEVAL_JUDGE_PIN=1`, `--lock-model`, `lock_model`) uses only the first model.
- **Retake the README's images** (`docs/images/*-screen.png`, `new-evaluation.png`): 1400x875, from the app on an empty data
  folder (`DUBEVAL_DATA`) so nobody's evaluations show, with the openly licensed Tears of Steel pair in the test set (p011,
  p012; its credit is in `README.md` and `NOTICE`). Never show a clip that isn't ours to show, or a language recognition
  can't read: most of the report is then not measured.
- **Add UI text:** add a `w.*` key to `WEB_TEXT` in `dubeval/web_text.py` in all four languages and use `t("key")`
  in the page's JavaScript (it gets the texts from `/api/info`).
- **Inspect a share link by hand:**
  `curl -s "https://api.perso.ai/video-translator/api/v1/projects/shared/<seq>" | python3 -m json.tool`
  (public; returns title, languages, `originalFileUrl`, `translatedFileUrl`, `lipSyncFileUrl`, `isLipSync`).

## Definition of done
1. `pytest -m "not slow"` passes (and `pytest` before committing).
2. New user-facing text exists in en/ko/pt/es.
3. Docs match the change (`README.md`, `INSTALL.md`, `docs/*.md`, this file). The README stays short (PersoDub's layout); detail goes in `docs/`. Screenshots live in `docs/images/` (1400×875 PNG).
4. `git status` shows no `.env`, videos, `data/`, `output/` or `tests/data/` files. Never commit videos: git keeps them in
   history forever and every clone downloads them.
5. Commit only when the user asks.

## Known limits
- A dub whose picture drifts (slowed down or sped up in places) is followed only when the usual matching finds under 90% of
  the original (`pairing._followed`), so other dubs are matched as before. It rests on one real dub, and the guard against a
  cut in a still shot (`DRIFT_MAX_FALL`) on one real cut (`docs/validation.md`).
- A dub subtitle file confirms the dub's language when the transcript matches it at `report.SUBTITLE_MATCH` (0.45,
  1 − character error rate): set from one EN→UZ Perso dub (0.61 against its Uzbek subtitles, unrelated text
  0.17-0.25). Check it on more pairs before relying on it.
- Runtimes: Electron 45.2.2 (upgraded 2026-11-04; the newest three majors get Chromium fixes, and 45's end about
  2027-04-27, so move on before then; since 45 it downloads on first use, not at `npm install`) and Python 3.14.9 (bug-fix releases with Windows builds until
  2027-10). Before changing either, check every pin has a wheel for it:
  `pip install --dry-run --ignore-installed --only-binary=:all: --platform win_amd64 --python-version 3.14
  --implementation cp --target <tmp> -r requirements.txt` (openai-whisper is source-only, which is fine).
- The lip-sync check was tested on one real Perso EN→KO dub and planted sound delays only; on a CPU it adds about
  30 s (at most 30 moments from the first 60 s).
- The translation check reads Whisper transcripts, not audio, so misheard words can look like translation errors
  (they're flagged as probable recognition errors).
- **Thresholds were calibrated with openai-whisper, but faster-whisper is the default** (decided 2026-10-21; recalibration
  is on the roadmap). On 7 real PersoDub dubs the two disagree: clarity 0% vs 100% on one Korean dub (faster-whisper's
  fallback ends at temperature 1.0 with a lower avg_logprob), speech timing 58% vs 26% on another, and no speech
  found in a music video. Until then, clarity, timing and pace verdicts from faster-whisper are provisional;
  `DUBEVAL_ASR=openai-whisper` reproduces the calibrated behaviour.
- **The local judge is Gemma 4 12B** (`local_judge.MODEL`, the GGUF tag `gemma4:12b-it-q4_K_M`; owner's decision,
  2026-11-13). It replaced Qwen3 8B, which found 4 of 23 planted mistakes, reported missing content in 11 of 13 lines of
  a good dub and, on the new set, never stopped writing. Gemma 4 12B caught 28 of 28 planted mistakes on Windows and on
  the Mac with no harmless rewording flagged (`docs/validation.md`), but that is planted mistakes on 8 dubs, one run
  each: it hasn't been compared with the reviewer's labels. It is slow (about 11 s a line on an 8 GB NVIDIA laptop,
  7 s on an M2 Pro), needs about 7 GB of graphics memory, answers in English only (`LOCAL_SCHEMA`), and stays last in
  `auto`. Gemma 4 E4B is not a smaller substitute: it missed every left-out line. When the model doesn't fit the
  graphics card as Ollama splits it, its runner crashes (HTTP 500): with 1.8 GB of an 8 GB card in use it put 36 of
  49 layers on the card and every request failed, so `_judge_ollama` asks again with 24 layers on the card and then
  none (`LOCAL_GPU_LAYERS`; 81 s and 186 s for a 6-line check against 72 s with the whole card). Keep the step-down. A pack installed with the old
  model is `outdated` (`packs.state`): it isn't used, and Settings → Models offers Update or Remove.
- Less common languages are recognized poorly: a real EN→UZ dub was heard as Kazakh (47% with `base`, 75% with
  `large-v3-turbo`), and forcing the wrong language collapses the transcript (speech timing read 0%). Users should
  pass `--target-lang`. `large-v3-turbo` is the default wherever it is downloaded (2026-11-15); it still can't read
  Uzbek, and its speed on a processor was timed on one laptop only (not on a Mac, not on an older processor).
- **Speech-timing Poor is below 45%, loudness Poor beyond 10 dB** (owner's decision, 2026-11-24, on 39 graded dubs:
  `data/testset/round2`, `docs/validation.md`): every dub at 47-54% overlap was Needs review on timing to the reviewer,
  and a dub Poor only for being 6.6 dB louder was graded Needs review. Both still rest on one reviewer.
- Speech-timing and pace bands are calibrated on one real Perso EN→KO dub (81–82% overlap, 5.8 chars/s).
- Google's Gemini API often returns 503 "high demand"; the judge retries and falls back across four Flash models,
  then reports "busy, try again in a minute".
- Whisper is seeded inside `transcribe`, which keeps its fallback sampling repeatable; keep it that way (bump `CACHE_VERSION` in
  `dubeval/evaluate.py` when cached Whisper results would change, `pairing.VERSION` when `pair()`'s result changes).
  Cache keys of steps that read speech times use `_spans_id(...)` of those times, never only their count. Over music and effects the recognizer invents
  lines that change from run to run, even on the GPU with the same seed; `evaluate.keep_voiced` drops every line the
  voice detector hears no speech in (those lines made transcript checks flag problems that weren't there). A line
  the detector misses is kept when the other track speaks then, and detected speech the transcript skipped is
  recognized again (`fill_gaps`). It also
  drops short shouts over loud effects and some singing (~1-2% of speech time).
- A job running when `dubeval web` restarts can't resume; it's reported as interrupted (start it again).
- Voice similarity's bands rest on 10 real dubs and 363 line pairs of different videos (`docs/validation.md`), with no
  person's answer except one: the owner listened to the two dubs it calls "another voice" (p015, p018) and found both
  a different voice (2026-11-13); nobody has listened to the "same voice" ones. Results on 2 or 3 lines
  are graded and are thin. On 6 of 20 test dubs it can't tell (a film clip, videos with 2-3 lines).
- Recognition on a graphics card isn't exactly repeatable even with the seed set: the same audio gave different text on 2 of 3
  copies tried (2026-11-03). Don't read a few false alarms' difference between two runs as an effect (`docs/validation.md`).
- Audiobox Aesthetics' bands rest on damage put into the 20 test dubs (8 s, one stretch each) and on no person's
  answer: no real dub with a bad voice has been tested, mild damage is mostly missed (a 4 kHz low-pass on 2 of 20,
  3x clipping on none), Poor (2.5) has never been reached, and it adds about 20 s per minute of video on a processor.
- Without that download, voice quality (DNSMOS) misses a muffled (low-passed) voice, and its bands were set from damage simulated on two real dubs
  (clean dubs: at most 0.25 below the original; robotic/distorted stretches: 0.4-2.3 below). Poor moved from
  1.0 / 0.9 to 2.5 / 1.5 on 2026-11-01 (graded real dubs reached 2.2 / 1.2 and were fine), so most simulated damage
  is now Check, not Poor. A simulated robotic voice (8 s quantised to 16 levels) is flagged on only 9 of 17 tune dubs. The
  bands were kept when the volumes were matched (2026-11-03).
- Interval thresholds (long silence 2/4 s, loudness jump 10/16 dB, wrong language: original's 50/80%, other 80/95%) are first guesses checked on
  the sample only. The per-window language check needs ~3 s of speech per 10 s window.
- The noise check (`evaluate.noise_envelope`, `intervals.noise_bursts`) misses hum, buzz, crackle, bursts under 1.5 s and noise
  across a whole dub, and was tested on planted noise only: no real dub has shown any. DNSMOS isn't the place for this:
  it scores 9 s windows, and normal dubs dip as much as a noisy spot. "Sound in sync" is not measured on dubs that
  replace the background.
- Compare mode was verified with fake share links (real Whisper), in the browser, and on two real EN→ES Perso dubs of
  one video; not yet on a real Windows machine.
- The macOS app was built and checked on one Mac (2026-11-12, an M2 Pro on macOS 15.7: signature, one evaluation,
  start and stop; an earlier copy was used by hand there). The GitHub workflow that does the same has never run, there
  is no Intel build, and thresholds were all set on Windows.
