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
   distortion, speaking pace, dub language, voice clarity (Whisper), voice quality (DNSMOS), voice similarity (speaker model), speech timing, video file, lip movement
   (experimental, lip-synced dubs only), and script accuracy when a script is passed to the CLI.
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
measure works and its bands), `docs/design.md` (why each choice was made), `docs/roadmap.md` (what comes next).

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
  without them it falls back to the CPU on its own. The meaning screen uses the ONNX pack (`meaning.PACK_DIR`, built
  by `tools/build_meaning_onnx.py`) and only falls back to sentence-transformers in a dev env. Keep torch out of the
  runtime: the desktop app ships `requirements.txt`.
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
                         probe + check (readable, has audio, ≤ DUBEVAL_MAX_MINUTES)
dubeval/asr.py           Speech recognition over faster-whisper (default) or openai-whisper (DUBEVAL_ASR); same
                         output shapes, seeded; GPU when it works, else CPU
dubeval/settings.py      API keys (Claude, Gemini, ChatGPT) from Settings → API keys: data folder's .env, status only
dubeval/packs.py         Optional downloads (meaning, gpu, large_model): pinned sources + SHA-256, resume, install,
                         remove; CATALOG = Settings → Models (built in + downloadable, grouped; /api/models)
dubeval/languages.py     Whisper's language names by code (copied, MIT): the runtime has no openai-whisper
dubeval/pairing.py       Same video, time shift and coverage from motion, frame hashes and background sound; the
                         dub's audio is laid onto the original's timeline (one shift, or part by part)
dubeval/schema.py        The report.json format (Pydantic models, FORMAT_VERSION) and its JSON Schema
schemas/                 report.schema.json, generated by `dubeval schema` (a test keeps it current)
pyproject.toml           Package `dubeval`, the `dubeval` command, dependency ranges and extras
dubeval/translation_judge.py Translation check: Claude, Gemini (REST), ChatGPT (OpenAI REST), local Ollama; retries + fallbacks
dubeval/report.py            build_report(results, lang): levels, verdict, intervals, things to check; renderers (pure)
dubeval/intervals.py         Problem intervals: collect from every check, merge (< 0.5 s), clip, round 0.1 s, sort (pure)
dubeval/compare.py           Compare mode: facts, decide (the rule), build_comparison, text/HTML renderers (pure)
dubeval/batch.py             Batch mode: parse links file (+ person's verdicts), summary rows, agreement, CSV/text (pure)
dubeval/voice_quality.py     Voice quality: DNSMOS P.835 on both tracks at the same moments, where both speak (ONNX)
dubeval/speaker.py           Voice similarity: WeSpeaker ONNX (downloaded once, SHA-256 pinned), numpy Kaldi fbank
dubeval/api.py               REST API (FastAPI) over the same job runner; token auth when DUBEVAL_API_TOKEN is set
dubeval/ort_session.py       ONNX Runtime CPU sessions (threads sleep between runs: two models taking turns ran 6x slower)
dubeval/localweb.py          What the local servers share: Host check, security headers (CSP), port bound before the link
dubeval/webapp.py            Web interface server (dubeval web): uploads, evaluations and comparisons, report, media, waveforms, votes;
                             127.0.0.1 only, per-launch token kept in a same-site cookie, Host header checked
dubeval/web/                 The page: plain JavaScript modules, no build step (app, home = the Evaluations screen,
                             start (+ drafts), progress, review, compare, history, settings, export = the Export dialog,
                             shell = the sidebar's Help / Send feedback / What's new and the update state + CSS)
dubeval/library.py           The Evaluations list: cards of finished run folders (card.json, thumb.jpg), rename,
                             delete, drafts (data/drafts/), and the inputs that pruning must spare
dubeval/preview.py           Start-page previews: Perso share (public endpoint), web page (yt-dlp, no download), file
                             (one ffmpeg frame); pictures as data: URIs. GET /api/preview
dubeval/local_judge.py       The local translation checker pack (Ollama CPU+Vulkan + Qwen3 8B, pinned) and its server
dubeval/xlsx.py              A dependency-free one-sheet .xlsx writer (Export's problem list, webapp.problem_rows)
dubeval/release_notes.py     What's new per version in en/ko/pt/es (add the new version's lines with every release)
dubeval/web_text.py          Every web-page text in en/ko/pt/es (keys w.*), merged into i18n.TEXT
dubeval/__main__.py          python -m dubeval = the dubeval command (how the desktop app starts the server)
tools/build_desktop.py       Windows build: Python 3.14 + requirements.txt + DubEval + base/speaker models → desktop/resources/
tools/build_meaning_onnx.py  Dev tool: BGE-M3 → int8 ONNX pack (model.onnx + tokenizer.json + pack.json) for meaning.py
desktop/                     Electron app: main.js starts `python -m dubeval web --port 0`, reads the launch link,
                             opens it in a sandboxed window (status.html while starting); updater.js (electron-updater,
                             GitHub Releases) + preload.js (window.dubevalShell: updates only); README.md there
dubeval/paths.py             DATA_DIR (DUBEVAL_DATA, default ./data): output, cache, history, votes, jobs
dubeval/feedback.py          Reviewer votes (real problem / false alarm) per interval; per-check summary
dubeval/history.py           Records every evaluation to data/history.jsonl; summarize() and the history text view
dubeval/version.py           TOOL_VERSION (= desktop/package.json's version, tested) and REPOSITORY_URL (Help, Send
                             feedback, and the releases the app updates from)
dubeval/report_text.py       Every report sentence in en/ko/pt/es (keys r.*), merged into i18n.TEXT
dubeval/i18n.py              UI text (TEXT), fixed progress/error messages (MESSAGES), t(), translate_message()
dubeval/jobs.py              Background job thread + Progress model; state and results kept in data/jobs/ across restarts
dubeval/cli.py               Argument parsing, quiet native logs, exit codes
dubeval/models/              Bundled models with their licenses (README.md there): MediaPipe face landmarker (lip
                         movement), DNSMOS P.835 ONNX (voice quality)
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
- **History recording never fails a run** (errors are logged); tests write history and votes to temp files
  (`tests/conftest.py`).
- **Calibrate with evidence:** reviewer votes (`qa.py feedback`) and batch labels (`qa.py batch`) are how thresholds
  should change; a check marked "flags too much" is the first candidate.
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
  how it's graded.
- **The decision rule is deterministic and printed:** rule order, "skip a rule when any dub lacks its value", ties
  keep input order, the reasoning compares #1 with #2, rule 1 (a dub with fewer of the key checks `KEY_CHECKS` measured never
  wins), the caution when the winner still lacks key checks, and the all-Poor warning are part of the spec; change them only together with `c.rule.*` / `c.why.*` texts,
  `c.rules_order`, `tests/test_compare.py`, `docs/usage.md` and this file.
- **Any language pair:** the dub language comes from the share metadata (base code: `es-MX` → `es`). A language
  without a pace rule (`SPEECH_RATE`) or without a Whisper model is "not measured" with the reason, never graded
  silently and never a crash.
- **Cross-platform (Windows, macOS, Linux):** pathlib for paths, `encoding="utf-8"` on every text file, no shell
  commands (ffmpeg comes from `imageio-ffmpeg` and runs as an argument list), OpenCV paths through `_cv2_path`.
- Verdict rule: any Poor → Poor; otherwise any Check → Needs review; otherwise Good. Info and not-measured rows
  never count. Issues the judge flags `may_be_recognition_error` are listed but never lower a level.
- The pipeline reports progress only through `Progress` objects; the page polls the job, the worker thread never
  talks to the page.
- **Voice quality compares the dub with the original at the same moments**, never in absolute terms: DNSMOS scores
  fall with background music, which both tracks share. It was chosen after UTMOS failed on real dubs (every real
  recording scored ~1.2-1.5, even after voice separation); don't swap in a studio-speech model without testing it on
  real Perso dubs. Window bands are in `dubeval/intervals.py` (`VOICE_SIG_DROP`, `VOICE_OVRL_DROP`).
- **Voice similarity is only measured on lines with a clean original background** (DNSMOS background ≥ 3.0):
  music blurs voice fingerprints (on a real film even one actor's own lines scored < 0.45). It's Good or Check, never
  Poor (a new voice can be deliberate). Line-level "different voice" intervals are relative to the dub's own median.
  The model downloads on first use to `~/.cache/dubeval/` (`DUBEVAL_MODELS` overrides); tests never download
  (`tests/conftest.py`).
- Lip movement is measured automatically only when the dub is lip-synced, is always informational and never
  changes the verdict. Don't present its number as reliable (metrics.md §3).
- The web interface keeps options few: per dub its kind and language, subtitles, the original's language, the
  translation check on/off and lip movement (automatic for lip-synced share links). The Whisper model is
  automatic (`asr.default_model`: `large-v3-turbo` when downloaded and a GPU runs it, else `base`; the start page's
  More options and `WHISPER_MODEL` / the CLI can name one); script accuracy is CLI-only.
- **report.json is a contract** (`dubeval/schema.py`): renaming or removing a field, or changing its meaning, bumps
  `FORMAT_VERSION`; adding a field doesn't. After any change run `dubeval schema > schemas/report.schema.json`.
- **Speech recognition goes through `dubeval/asr.py` only.** Both backends must keep returning the same shapes, and
  cache keys include `asr.model_id()` so results from different recognizers never mix.
- **Meaning** (`pipeline.judge_lines` → `meaning.screen` and `translation_judge.judge_translation`): both read the
  speech line by line. The judge is chosen by `--judge` / `DUBEVAL_JUDGE` (`auto` = Claude → Gemini → ChatGPT → Ollama; ChatGPT uses an OpenAI API key,
  `OPENAI_API_KEY`, sent only in the Authorization header); keep
  `RESULT_SCHEMA`, `SYSTEM_PROMPT` and `DUB_TYPE_RULES` in `translation_judge.py` and change them only together with
  the judge tests. The screen's band (`SCREEN_LOW`) is in `report.py`; it is Check-only. Tests never load BGE-M3,
  never call a judge and never probe Ollama (`tests/conftest.py`). `--dub-type` (ai_clone | ai_stock | human) skips
  voice similarity for human and stock-voice dubs (`pipeline.apply_dub_type`).
- **Speech that can't be graded** (`report.speech_problem`, `SPEECH_DEPENDENT`, `UNRECOGNIZED_PROB`): an unsure
  third-language detection makes the language row and every speech-based row "not graded" (with the reason), and the
  pipeline doesn't run the translation judge or the meaning screen on that speech (`pipeline._speech_unrecognized`);
  a dub without speech adds a Poor row (nothing was dubbed), an original without speech a Check row. Both were set from
  the 12-pair labelled set of 2026-10-25. In `auto`, a judge with a rejected key or no credit hands over to the next one
  (`translation_judge.ACCOUNT_PROBLEMS`); a judge chosen with `--judge` never does.
- **Downloads (`dubeval/packs.py`)**: every file has a fixed source (a Hugging Face revision, a PyPI version, a GitHub
  release or a registry digest, never `main` or "latest") and a SHA-256 checked before it is installed; nothing
  downloads unless a person asks. A file already in the pack's folder with the right checksum is kept, not downloaded
  again. The local judge pack (`dubeval/local_judge.py`) takes only Ollama's CPU + Vulkan files out of its release zip
  by range requests and runs DubEval's own `ollama serve` on a free 127.0.0.1 port while DubEval runs; to update it,
  regenerate the pins (versions, sizes, SHA-256) for both the zip members and the registry manifest. Changing a source
  means new checksums, and for the meaning pack a fresh score comparison with the original model (METRICS.md).
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
- **The app icon is DubEval's own** (`desktop/build/icon.png` / `icon.ico`, 2026-10-26): a blue tile with a white
  waveform and a green check, in the interface's blues. It replaced PersoDub's icon, which needed ESTsoft's permission.
- **Releases and updates:** the version lives in `dubeval/version.py` and `desktop/package.json` (a test keeps them
  equal) and every version needs its lines in `dubeval/release_notes.py`. Installed apps update themselves from the
  GitHub Releases of `REPOSITORY_URL` (`build.publish`): publish the installer, its `.blockmap` and `latest.yml` together
  (`npm run release` with `GH_TOKEN`, or upload the three files from `desktop/dist`). Until the installer is code-signed,
  an update is trusted because it comes from that repository: keep its releases to the owner.
- **Labels are a person's answer key** (`dubeval label`, `dubeval/labeling.py`): never fill them from DubEval's own
  output or from an LLM, or calibration only measures DubEval against itself. The page hides DubEval's verdict until
  the person has answered, listens on 127.0.0.1 only, opens only with its launch link (token cookie, Host check,
  so no other web page can read or change the labels), and serves only files named in the sheet.
- **Line timing** (`evaluate.match_segments` → `line_timing`, raw numbers in `results["segment_alignment"]["lines"]`)
  is graded in `report._line_fit` (`LINE_BAND_PCT`, `LINE_FIT_SHARE`, `LINE_OVERRUN_SHARE`, `LINE_POOR_MIN`); its
  measuring limits (`LINE_MIN_SEC`, `LINE_OVERRUN_SEC`) are in `dubeval/evaluate.py`, interval bands
  (`LINE_POOR_PCT`, `LINE_MIN_DIFF_SEC`, `LINE_OVERRUN_POOR_SEC`) in `dubeval/intervals.py`.
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
  in `report.py` (`RUBRIC_FLAG`, `RUBRIC_POOR`, `_rubric`); only meaning can be Poor. Results saved before the rubric
  (`meaning_score` 1-5, no `rubric` key) still render with the old rows.

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
- UI copy is short, plain, second person ("Paste a Perso share link").

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
- **Things to check** are built from the problem intervals (+ untimed warnings) in `_things_to_check`
  (`dubeval/report.py`); add new timed issues as interval categories instead.
- **Change the translation check:** prompt and JSON schema are `SYSTEM_PROMPT` / `RESULT_SCHEMA` in
  `dubeval/translation_judge.py`. Summary and explanations must stay four-language objects. Gemini models are tried
  in `GEMINI_MODELS` order; `GEMINI_MODEL` / `GEMINI_THINKING` env vars override the first model and thinking.
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
- A dub subtitle file confirms the dub's language when the transcript matches it at `report.SUBTITLE_MATCH` (0.45,
  1 − character error rate): set from one EN→UZ Perso dub (0.61 against its Uzbek subtitles, unrelated text
  0.17-0.25). Check it on more pairs before relying on it.
- Runtimes (upgraded 2026-10-23 after the security review): Electron 44.9.3 (supported: the newest three majors get
  Chromium fixes, so move on before 44 drops out) and Python 3.14.9 (bug-fix releases with Windows builds until
  2027-10). Before changing either, check every pin has a wheel for it:
  `pip install --dry-run --ignore-installed --only-binary=:all: --platform win_amd64 --python-version 3.14
  --implementation cp --target <tmp> -r requirements.txt` (openai-whisper is source-only, which is fine).
- Lip movement is a heuristic (the in-sync original of the sample scores −0.20); a SyncNet-style model would
  replace it.
- The translation check reads Whisper transcripts, not audio, so misheard words can look like translation errors
  (they're flagged as probable recognition errors).
- **Thresholds were calibrated with openai-whisper, but faster-whisper is the default** (decided 2026-10-21; recalibrate
  in Phase 5). On 7 real PersoDub dubs the two disagree: clarity 0% vs 100% on one Korean dub (faster-whisper's
  fallback ends at temperature 1.0 with a lower avg_logprob), speech timing 58% vs 26% on another, and no speech
  found in a music video. Until then, clarity, timing and pace verdicts from faster-whisper are provisional;
  `DUBEVAL_ASR=openai-whisper` reproduces the calibrated behaviour.
- **The local judge (qwen3:8b through Ollama) is unreliable but stays in `auto`** (user's decision, 2026-10-22). On
  the Francis EN→KO dub it reported missing content in 11 of 13 lines, nearly all wrongly, so the verdict became Poor;
  it answers in English only (`LOCAL_SCHEMA`) to finish in about a minute (four languages took over 10 minutes).
  Claude is the reliable judge; the offline BGE-M3 screen found the real error with no false alarm.
- Less common languages are recognized poorly: a real EN→UZ dub was heard as Kazakh (47% with `base`, 75% with
  `large-v3-turbo`), and forcing the wrong language collapses the transcript (speech timing read 0%). Users should
  pass `--target-lang`; the default model may move to `large-v3-turbo` after Phase 5 calibration.
- **Candidate change, on hold** (decided 2026-10-22): speech-timing Poor below 55% → 45%. On 7 labelled PersoDub
  pairs, dubs at 47-52% overlap were Check to the reviewer, not Poor; revisit with 20-30 labelled pairs.
- Speech-timing and pace bands are calibrated on one real Perso EN→KO dub (81–82% overlap, 5.8 chars/s).
- Google's Gemini API often returns 503 "high demand"; the judge retries and falls back across four Flash models,
  then reports "busy, try again in a minute".
- Whisper is seeded inside `transcribe` so results are repeatable; keep it that way (bump `CACHE_VERSION` in
  `dubeval/evaluate.py` when cached Whisper results would change).
- A job running when `dubeval web` restarts can't resume; it's reported as interrupted (start it again).
- Voice similarity is not measured on music-heavy videos (by design); its bands come from synthetic voices (same voice
  0.80-0.87 across languages, different voices median 0.13, max 0.57) and need real cloned dubs to confirm.
- Voice quality misses a muffled (low-passed) voice, and its bands were set from damage simulated on two real dubs
  (clean dubs: at most 0.25 below the original; robotic/distorted stretches: 0.4-2.3 below).
- Interval thresholds (long silence 2/4 s, loudness jump 10/16 dB, wrong language: original's 50/80%, other 80/95%) are first guesses checked on
  the sample only. The per-window language check needs ~3 s of speech per 10 s window.
- Compare mode was verified with fake share links (real Whisper), in the browser, and on two real EN→ES Perso dubs of
  one video; not yet on a real Windows machine.
