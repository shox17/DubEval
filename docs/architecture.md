# Architecture

## Flow

```
qa.py / dubeval → dubeval/cli.py ──┐   (compare <A> <B> → run_comparison / run_files_comparison)
dubeval web → dubeval/webapp.py     │   (page: dubeval/web/, plain JavaScript)
 ├─ start (#/): original + 1-8 dubs (files, paths, links or Perso share links)
 │    POST /api/evaluations ──► jobs.start_job(run_files_evaluation | run_files_comparison |
 │                              run_share_evaluation | run_comparison) ──► #/job/<id>
 ├─ progress: polls GET /api/jobs/<id> every second ── done ──► #/report/<id> or #/compare/<id>/<dub>
 ├─ review: build_report(results, lang) + synced players, waveform timeline, lines, problems
 ├─ comparison: build_ranking(results...) → recommendation, ranking, side-by-side checks, a review per dub
 └─ history (#/history): history.summarize + feedback.summarize
                                │
pipeline.evaluate_share(share_url)                       (one dub; run_share_evaluation adds report files)
 parse_share_url → GET /projects/shared/{seq}                                 stage: fetch
 download original (or --original) + (lipSyncFileUrl | translatedFileUrl)
   into data/cache/<link hash>/, reused on reruns                             stage: download
 evaluate.run_full_evaluation(original, dub, target_lang, source_lang,
   cache=JsonCache(whisper_cache.json))                                       stage: evaluate
 check_translation → (run_share_evaluation) build_report → report.* in --out or runs/<id>/ + results.json

pipeline.run_comparison(url_a, url_b, out_dir)           stages: dub_a, dub_b, compare
 evaluate_share(A), evaluate_share(B) → compare.build_comparison → comparison.* + report_A.* + report_B.*
```

## Modules

### `dubeval/perso_api.py`
Share links only; no API key, no account (https://developers.perso.ai/llms.txt).
- `parse_share_url` takes the `seq=` token from any perso.ai link: the Share dialog's `https://perso.ai/<lang>/share/video-translator?seq=…`, gallery pages like `https://perso.ai/video-translator/en-es/<category>?seq=…`, or a bare token, and raises `ValueError` with a plain message for anything else, before any network call.
- `get_shared_project` calls the public `GET /video-translator/api/v1/projects/shared/{token}`. It returns title, `durationMs`, `sourceLanguage` / `targetLanguage`, and `originalFileUrl`, `translatedFileUrl`, `lipSyncFileUrl`, `isLipSync`. VT4035 becomes "sharing is turned off"; an unknown link or a project without a finished dub also get plain messages. 429 and 5xx are retried with backoff.
- A project without `originalFileUrl` is accepted here; the pipeline then needs `--original` (else a plain error).
- `download_media` streams a relative `/perso-storage/…` path from `https://portal-media.perso.ai` (URL-encoded) with retries and an atomic `.part` rename.

### `dubeval/pipeline.py`
- `evaluate_share` parses the link, reads the project, downloads the original and the dub (the lip-synced video when `isLipSync`) into the link's cache folder `data/cache/<sha1(token)[:16]>/` (files named after a hash of their Perso path, so a re-rendered dub is downloaded again), and evaluates with the project's source and target languages. Whisper results go to `whisper_cache.json` in the same folder. `use_cache=False` (`--no-cache`) empties the folder first. The newest `MAX_CACHED_LINKS` link folders are kept. Lip movement is measured only when the evaluated video is lip-synced (`include_lipsync=None` = automatic; `--no-lipsync` forces it off). `original` (a file or URL) is used when the link has no original. It checks the stop signal between steps, then runs `check_translation` (any failure is a not-measured result).
- `run_share_evaluation` = `evaluate_share` + `build_report` + `save_report_files` (`report.json` = report + results, `report.html`, `report.txt`) into `out_dir` (the CLI's `--out`) or a new `data/output/runs/<run-id>/` (kept until deleted; see `dubeval/library.py`), then `results.json`.
- `check_translation` caches successful reviews in the link's `judge_cache.json` under a fingerprint of both transcripts, the languages and `translation_judge.judge_fingerprint()` (provider, models, thinking, prompt, schema); failures are never cached.
- `run_comparison(url_a, url_b, out_dir, more_urls=())` evaluates every link (2–8), calls `build_comparison`, and `save_comparison_files` writes `comparison.txt` / `.json` (without the embedded reports) / `.html` and `report_A.*` / `report_B.*`. Progress is mapped onto the stages `dub_a`, `dub_b`, `compare`.
- HTML reports refer to the cached videos by relative path (a `file://` URI when they are on another Windows drive).

### `dubeval/evaluate.py`
Pure: no file writes (only temp audio) and no side effects on import. `run_full_evaluation` reports sub-steps through `on_step`, takes `include_lipsync` (skip the slow experimental step), `source_lang`, and an optional dict-like `cache` for Whisper results (transcripts, language detection, language windows) keyed by model, language and media file; the Whisper model is loaded only on a cache miss. On Windows, OpenCV gets an ASCII path (`_cv2_path`) and MediaPipe gets its model as bytes, because both fail on non-ASCII paths. It returns audio measures, both transcripts with Whisper segments, the dub's detected language, clarity, speech intervals and their alignment, clipping, a technical comparison of both files, and lip movement. See [metrics.md](metrics.md).

### `dubeval/voice_quality.py`
`voice_quality(y_orig, y_dub, orig_speech, dub_speech)` scores ~9 s windows where both tracks speak with DNSMOS P.835 (`dubeval/models/dnsmos_sig_bak_ovr.onnx`, onnxruntime on CPU, session loaded once) and returns `{measured, reason_key, dub, original, difference, windows[{start, end, dub, original, dub_sig, original_sig, dub_bak, original_bak}], model}`. `evaluate.run_full_evaluation` calls it through the per-link cache; a missing runtime becomes `not_measured("r.vq.error")`. Grading: `intervals.voice_window_level`, used by both the report row and the intervals.

### `dubeval/lip_sync.py`
`lip_sync(orig_video, y_orig, orig_speech, dub_video, y_dub, dub_speech, duration, check, dub_offset_sec)` (y_dub: the
dub's own sound, not moved onto the original's timeline; the dub's frames and sound are read `dub_offset_sec` later;
a recut dub is `not_measured("r.sync_lips.recut")`) runs only when the
`lip_sync` pack is installed (`ready()`), in place of `analyze_lipsync`. `pick_moments` takes separate 16-frame
moments (25 fps) where both tracks speak for ≥ 80% in the first 60 s; `face_seen` looks at each one's middle frame in
both videos (read side by side in two threads); `lower_faces` prepares the 16 frames of up to 36 of them as LatentSync
does (MediaPipe's three points → `align`, warp, 256×256, lower half); `best_shifts` embeds faces and sound
(`mel`) with the two bundled graphs (`ort_session.cpu_session(graph, PACK_DIR)`: the weights are external data in the
pack's `stable_syncnet.pt`) and searches the sound shift coarse-to-fine over ±15 frames. `typical_shift` of the
original is the zero point. Returns `{measured, moments, original_match, dub_match, original_match_pct,
dub_match_pct, dub_offset_ms, dub_offset_match_pct, timeline[{time, end, original, dub, dub_lines_up}]}` or
`not_measured(reason_key)`; `evaluate._lip_sync` turns any failure into `r.sync_lips.error`. The graphs are built by
`tools/build_syncnet_onnx.py` from the pinned checkpoint (torch and onnx, developer only).

### `dubeval/speaker.py`
`voice_similarity(y_orig, y_dub, orig_segments, background)` embeds each original line ≥ 2 s and the dub over the same span with WeSpeaker ResNet34-LM (ONNX; `fbank` is a numpy port of torchaudio's Kaldi fbank defaults, then per-utterance mean normalisation) and returns `{measured, reason_key, median, lines[{start, end, similarity}], skipped_noisy, model}`. `background(audio)` is DNSMOS's background score; lines below `CLEAN_BACKGROUND` are skipped. `model_path()` downloads the model once to `~/.cache/dubeval/` (pinned commit URL, SHA-256 checked, atomic `.part` rename); failures become `not_measured("r.vs.no_model")`.

### `dubeval/translation_judge.py`
One LLM review of both timestamped transcripts: a 1–5 meaning score, a summary, and issues typed `missing / added / mistranslation / name_or_number` with severity, time, exact quotes and `may_be_recognition_error`.
- **Provider:** Gemini when `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) is set, else Claude when `ANTHROPIC_API_KEY` is available (`judge_provider()`).
- **Gemini:** REST `generateContent` with the key in the `x-goog-api-key` header, `responseJsonSchema` for structured output, temperature 0, `thinkingLevel` low. 429/5xx are retried twice with backoff, then the next model in `GEMINI_MODELS` is tried (`gemini-3.5-flash` → `gemini-flash-latest` → `gemini-3.8-flash` → `gemini-3.1-flash-lite`); 404 skips to the next model. Google's "high demand" 503s are frequent and per model, hence the chain.
- **Claude:** `claude-opus-5-5` with structured output and server-side refusal fallback.
- Any failure (no key, rejected key, overload, refusal, unreadable output) returns a not-measured result with the reason; it never fails the run. Tests replace it with a stub (`tests/conftest.py`) and remove all provider keys from the environment.

### `dubeval/report.py` / `dubeval/report_text.py`
Pure. `build_report(results, lang)` builds the whole report in the interface language (`en`, `ko`, `pt`, `es`); every sentence comes from `dubeval/report_text.py` (keys `r.*`), and the judge's summary and explanations are picked from its four-language output. The web interface rebuilds the report for each request, so switching language switches the report. It returns `{project, overall{level,label,headline,counts}, sections[{id,title,metrics[{id,label,level,value,unit,display,message,thresholds}],note}], things_to_check[{start,end,category,severity,message}], not_measured[], method}`. All thresholds are constants at the top of the file and are printed in every row. `render_text` and `render_html` present the same report; the HTML is self-contained (light/dark) and embeds the videos by relative path when saved in the run folder.

### `dubeval/intervals.py`
Pure. `build_intervals(results, tr, lang)` turns speech-timing mismatches (long silence ≥ 2 s or timing mismatch), clipping locations, loudness jumps (from the loudness envelope), per-window wrong language, unclear speech and translation issues into `{start, end, dub, category, category_label, severity, check, check_label, description, merged}` ranges, merges same-category ranges closer than 0.5 s, clips to the dub's length, rounds to 0.1 s and sorts. Probable recognition errors are returned separately. `total_seconds` is the union length. See [metrics.md](metrics.md) §7.

### `dubeval/compare.py`
Pure. `facts(report, results)` → how many of `KEY_CHECKS` (speech_overlap, line_length, clarity: they need the dub's recognized speech) are present but not graded (`unmeasured`, rule 1, and which), verdict, Poor/Check counts, problem seconds, meaning score, overlap. `rank(facts_by_dub)` skips rules any dub lacks, sorts the dubs lexicographically by the remaining `RULES` (ties keep input order) and returns the order, winner, runner-up, the rule separating them, the values at it and the skipped rules; `decide(a, b)` is the two-dub view. `build_ranking([results...], lang)` (2–8 dubs; `build_comparison(a, b)` is the two-dub case) returns `{dubs[], ranking[{rank, dub, title, verdict, poor, check, problem_seconds}], recommendation{dub, tie, all_poor, both_poor, ready, headline, caution (the winner lacks key checks), warning, fix_first[]}, intervals{A,B}, possible_asr_errors{A,B}, problem_seconds{A,B}, reasoning{rule, rule_label, values{A,B}, deciding_factor, summary[], skipped_rules[], translation_used, translation_note}, facts, decision, table[], links{A,B}, notes[], meta{tool_version, generated, run_seconds}, labels, badges, reports{A,B}}`, every text in the chosen language (keys `c.*` in `report_text.py`). `render_comparison_text` (Korean-aware column widths) and `render_comparison_html` put the three decision sections first.

### `dubeval/batch.py`
Pure. `parse_batch_file` reads one link per line with an optional person's verdict (`good`, `check`/`needs review`, `poor`), skipping comments and a `url,label` header. `summary_row` flattens one evaluation (or its error) into base columns plus `<metric>_level` / `<metric>_value` for every measure; `agreement` returns matches, too strict / too lenient counts and a person × tool table; `to_csv` and `render_batch_text` present them. `pipeline.run_batch` evaluates each link into `<out>/<nnn>/` (a failing link becomes an error row) and writes `summary.csv` (UTF-8 with BOM for Excel), `summary.txt`, `summary.json`.

### `dubeval/history.py`
`record(results, mode)` (mode single / compare / batch / api / web) appends one JSON line per evaluated dub to `data/history.jsonl` (`DUBEVAL_HISTORY` overrides): time, tool version, mode (single / compare / batch), link, Perso project, languages and language pair, lip-sync, verdict, Poor/Check counts, problem seconds, meaning score, speech-timing overlap, every measure's level and the report path. Failures are logged, never raised. `summarize(records, days)` counts each dub once (latest run; by Perso project, link, or for files the `inputs` original|dub), and returns totals, per-pair verdict mix and averages, the most frequent Check/Poor measures, a weekly trend and the 20 latest runs; `render_history_text` prints it. `pipeline.run_share_evaluation` (with `history_mode`), `run_comparison` (every dub) and `run_batch` record.

### `dubeval/feedback.py`
`vote(project, interval, verdict)` appends `{time, key, link, seq, category, check, severity, start, end, vote, reviewer}` to `data/feedback.jsonl` (`DUBEVAL_FEEDBACK` overrides); `interval_key` = the dub (Perso project, or `file:<dub_id>` for a dub given as a file: its path hashed, so a rename
keeps its votes) | category | start | end (`legacy_key` finds votes keyed by title before `dub_id`), and `latest()` keeps
the newest vote per key. `summarize(votes)` gives totals and, per check, confirmed / false-alarm counts, the confirmed share and a status (`few` under 3 votes, `noisy` at ≥ 50% false alarms, else `reliable`). Report things-to-check items carry their `interval`; the web review's real problem / false alarm buttons vote on `problem_intervals` by index.

### `dubeval/api.py`
FastAPI app: `POST /evaluations`, `POST /comparisons` (validate links, then `jobs.start_job` with `run_share_evaluation` / `run_comparison` into a new run folder; 202 with the job url), `GET /jobs/{id}` (status, progress, elapsed, error; when done a result summary and report links), `GET /jobs/{id}/report?format=` (409 while running, 410 if pruned), `GET /history`, `GET /feedback`, `GET /health`. `require_token` checks `Authorization: Bearer` with `hmac.compare_digest` when `DUBEVAL_API_TOKEN` is set, and without it answers only a local `Host` header (`localweb.is_local_host`, against DNS rebinding); `serve()` refuses non-local hosts without it.

### `dubeval/webapp.py` and `dubeval/web/`
`dubeval web` (`serve`) runs `make_app(token)` on 127.0.0.1 with a fresh `secrets.token_urlsafe` token per launch. The printed link `/?token_given=…` sets an HttpOnly, SameSite=Strict cookie and redirects to `/`; every other route checks that cookie (`hmac.compare_digest`) and a local `Host` header (against DNS rebinding). `dubeval/localweb.py` adds `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` and the page's Content-Security-Policy (own files only; saved reports get a sandboxed policy), and binds the port before the link is printed (exclusive on Windows). Uploads over `inputs.MAX_MEDIA_GB` (20 GB, `DUBEVAL_MAX_MEDIA_GB`) get 413 and are removed. `dubeval label` (`labeling.make_app(..., token=)`) works the same way: launch link → cookie, Host check, a nonce for its one inline script. Routes: `GET /api/info?lang=` (the page texts `w.*`/`stage.*`, languages, dub types, ready judges), `POST /api/uploads` (multipart into `data/uploads/<id>/`, newest 40 kept; referred to as `upload:<id>`), `POST /api/evaluations` (paths, links or uploads → `jobs.start_job` with `pipeline.run_files_evaluation`, stages `prepare`/`evaluate`; with `more_dubs` it is a comparison: `pipeline.run_files_comparison` evaluates every dub against the one original with `evaluate_files`, then `compare.build_ranking`, stages `dub_a`… `compare`; dub subtitles are not used there; `dub_options` gives each dub its own kind and language, passed as `per_dub` and overriding the shared values, so a human and an AI dub, or dubs in different languages, are each judged by their own rules), `GET /api/jobs/{id}/comparison?lang=` (the ranking rebuilt in that language, without the full reports); the report, media, peaks and votes routes take `?dub=A` for one dub of a comparison, `GET /api/jobs/{id}` (stage checklist, translated message), `POST /api/jobs/{id}/cancel`, `GET /api/jobs/{id}/report?lang=` (the report rebuilt in that language plus lines, segments, applied offset/parts and current votes), `GET /api/jobs/{id}/media/{original|dub}` (only the job's own input files; range requests), `GET /api/jobs/{id}/peaks/{side}` (`peaks()`: loudest sample per 1/50 s, the dub laid onto the original's timeline with `pairing.align_dub`/`align_dub_parts`; cached in the run folder), `POST /api/jobs/{id}/votes` (`feedback.vote`, reviewer `web`), `GET /api/models` (Settings → Models), `GET /api/settings` (which keys are set, the data folder, the version and whether saved here, the active translation checker and its order), `PUT`/`DELETE /api/settings/keys/{anthropic|gemini}` (`dubeval/settings.py`: the data folder's `.env`, applied at once; the key is never returned), `GET /api/packs`, `POST /api/packs/{id}/install` (a background job, stage `pack`; one per pack; stop it with the job's cancel route and it resumes later), `DELETE /api/packs/{id}` (`dubeval/packs.py`), `GET /api/history?days=` (`history.summarize` with each recent run's report as a path under the data folder, plus `feedback.summarize`), `GET /api/reports?path=` (a past HTML report: only a path the history names and only under the data folder), `GET /api/jobs/{id}/export?kinds=html,csv,text,json&lang=` (Export: the report, problem list, summary and data written again in that language, videos linked where they are; one file, or a ZIP; a comparison adds every dub's report). `GET /api/preview?source=` (`dubeval/preview.py`: title, length, picture as a data: URI, and for a Perso share link its languages and lip-sync, so the start page fills in the original and both languages; 400 with a plain message when a link or path can't be read). `EvaluationBody.original` may be null (a share link brings its original). `/api/info` also gives the speech languages (codes → English names; the page shows them in its own language), this version's release notes (`dubeval/release_notes.py`) and the repository URL. Errors are translated with `translate_message` from the page's `Accept-Language`.

The page (`dubeval/web/`, ES modules, no build step) has eight screens routed by the URL hash: home (`#/`,
PersoDub's first screen with Evaluations for Projects: a banner to start (it takes a Perso share link too), the ways
to start, then one card per draft and per finished evaluation from `GET /api/evaluations`, with Rename and Delete in
each card's "..." menu, search, and polling while a started draft runs), new (`#/new`, `#/new/compare` with two dub
cards), draft (`#/draft/<id>`: the start page filled in again from `GET /api/drafts/<id>`; the page saves its fields
with `POST`/`PUT /api/drafts` 0.7 s after each change once a video is given, adds chosen files with
`POST /api/uploads` at once so the draft holds them, and passes `draft_id` when it starts the run), plus settings (`#/settings/<keys|models|storage|privacy|about>`, PersoDub's dialog with Cancel and Save: Save keeps
typed API keys and a new language, everything else acts at once; Storage = `GET /api/settings/storage` (evaluations,
downloaded videos and the part no evaluation or draft uses, models, the data folder) and
`POST /api/settings/storage/clear` (deletes those unused downloads, never while a job or a link download runs, never
an upload under a day old); Models = `packs.catalog()` grouped with sizes and download/stop/resume/remove; API keys for Claude, Gemini and ChatGPT as password fields, never shown back, plus the checker in use; Privacy with the data folder and `POST /api/settings/open-data`; About with version, language, license and acknowledgements; `#/downloads` redirects to Models), history (`#/history`: totals, week-by-week bars, language pairs, the most frequent problems, reviewer votes per check, the latest runs with their reports), progress (`#/job/<id>`, polled every second), comparison (`#/compare/<id>/<dub>`: the recommendation and its reasoning, the ranking, every check side by side, then one tab per dub holding that dub's review) and review (`#/report/<id>`): two players kept in sync on the original's clock (the dub follows through the applied shift or parts and is re-synced past 0.25 s of drift), a canvas timeline (ruler, both waveforms, lines, problem intervals; scroll, Ctrl+scroll zoom, click to seek or select), a detail panel (both texts, lengths, problems with votes), things to check and every section's measures. It shows the server's levels and texts only; nothing is graded in the browser.

### `dubeval/library.py`
The home screen's Evaluations list. A finished run folder (`data/output/runs/<YYYYMMDD-HHMMSS_hex8>/`) is one card:
`card(folder)` reads `report.json` (one dub) or `comparison.json` + `report_A.json`, ... and caches the card in
`card.json` until those files change (title, verdict, kind, dubs, languages, length, created, and `inputs`: the videos
it plays, dubs first). `thumbnail` keeps `thumb.jpg`: the draft's picture when it was started from one, else one ffmpeg
frame of its dub (else original) made on first request. `rename` writes the new title into the saved report (one dub,
rebuilt in its language) or `comparison.json`'s `custom_title`; the web route then forgets the kept job
(`jobs.forget_folder`) so opening it rebuilds from the files, and renames the History records. `delete` removes the
folder and returns the inputs nothing else uses; the route deletes those that are uploads.
Drafts are `data/drafts/<hex12>.json` (`{id, created, updated, name, thumbnail (data:image URI), form, job}`, at most
512 KB; a picture that makes it bigger is dropped). `start_draft` records the job and copies the picture into the run
folder; `GET /api/evaluations` shows a started draft as running / failed / stopped while its job is, and deletes it
once the job is done (the run's own card takes over). Saving a draft again clears its job (a failed run edited to try
again). A run that ended without results (stopped or failed) leaves a folder with only its picture;
it is deleted when its draft is saved again or deleted, never while that job is running. `referenced_inputs()` = every kept run's inputs + `upload:<id>` of every upload a draft holds; the pruning of
uploads (`webapp._prune_uploads`) and of run/cache folders (`pipeline._prune`) skips folders that `protects()` says
hold one.

### `dubeval/packs.py`
Optional downloads a person installs from the Downloads page: `meaning` (Xenova/bge-m3 `onnx/model_int8.onnx` +
`tokenizer.json`, into `meaning.PACK_DIR`), `gpu` (NVIDIA's `nvidia-cublas-cu12` 12.9.2.10 Windows wheel from PyPI, of
which only `cublas64_12.dll` and `cublasLt64_12.dll` are kept, into `asr.cuda_pack_dir()`; offered only on Windows
with an NVIDIA driver) and `large_model` (faster-whisper large-v3-turbo into `~/.cache/dubeval/faster-whisper-large-v3-turbo`,
which `asr._local_model` finds; the start page then offers it). `PACKS` pins each file's URL (fixed revision), size and
SHA-256. `install` downloads into `<folder>.download/` with resumable `.part` files (Range requests; a server that
ignores them restarts the file), checks every checksum, extracts zip members, writes `pack.json` and swaps the folder
in; then `_changed` makes the running process reload the meaning model or look for CUDA again. `state` is installed /
partial / absent; `remove` deletes both folders.

### `dubeval/paths.py`
`DATA_DIR`: the project's `data/` or `DUBEVAL_DATA`. Output runs, the per-link cache, history, votes and jobs all live under it (each still overridable by its own variable).

### `dubeval/cli.py` / `qa.py`
`python qa.py "<share link>" [--out DIR] [--lang ko|en|es|pt] [--original FILE_OR_URL] [--script/--script-file] [--no-lipsync] [--no-translation-check] [--no-cache] [--whisper-model] [--json] [--fail-on never|poor|check] [--verbose]` and `python qa.py compare <A> <B>` with the same options (no script / fail-on). `--out` defaults to `./output` and is created if missing; `--lang` defaults to `ko`. stdout/stderr are switched to UTF-8. Progress on stderr, report on stdout; MediaPipe's native logs are silenced unless `--verbose`. Exit codes: single 0 done / 1 verdict failed `--fail-on`; compare 0 recommended dub Good or Needs review / 1 both Poor; both 2 input or runtime error.

### Stop and Continue
`POST /api/jobs/{id}/cancel` sets the job's stop flag; the pipeline's `check_cancel` raises `Cancelled` at the next
check. Checks run between steps, inside the measurements (`run_full_evaluation(check=...)`: between measurements,
after each recognized segment in `asr._transcribe_faster`, each sampled frame in `analyze_lipsync`, each window in
`language_windows`), and before the report is written, so a stopped run writes nothing and records no history. The
meaning screen and the translation check run through `pipeline._abandonable`: a thread the run stops waiting for at
once (the abandoned web request ends on its own; its result is dropped). Each job keeps its request
(`params["request"]`), and `POST /api/jobs/{id}/continue` starts it again for a cancelled, failed or interrupted job
(`can_continue` in the job state); cached speech recognition and the same-video check make it pick up about where it
stopped, and its draft follows the new job.

### `dubeval/jobs.py`
- `start_job(runner, params, stages)` runs `runner(report, cancel_event)` in a daemon thread. Jobs live in a process-wide registry, so a page reload (`?job=<id>`) reattaches to them. `Cancelled` marks a stopped job.
- `Job.overall_fraction` weights stages by typical duration (prepare 1, fetch 0.2, download 1, evaluate 6; compare: dub_a 7, dub_b 7, compare 0.2). `stage_state()` drives the done / active / pending / failed checklist.
- Jobs write `data/jobs/<id>.json` (state; on stage changes and every 2 s) and `<id>.result.json` (when done); `get_job` falls back to them, so finished jobs survive restarts and jobs that were running come back as `interrupted`. A final state is written to disk before it is set in memory. The newest 50 jobs are kept.

### `dubeval/i18n.py`
- `TEXT` holds every interface string in `en`, `ko`, `pt` (Brazil) and `es`, plus every report and comparison sentence from `report_text.py` (`r.*`, `c.*`). The web page gets its texts (`w.*` from `web_text.py`, plus stage, history and measure names) from `/api/info` in the language picked at the top right (default: the browser locale); the CLI uses `t(key, lang, **values)`.
- `MESSAGES` translates the fixed progress messages from `dubeval/`.
- `tests/test_i18n.py` checks that every key has all four languages with the same `{placeholders}`.

## `results.json` (schema_version 6)
- `metadata`: videos, `target_language`, `detected_source_language`, `whisper_model`.
- `acoustic_metrics`: durations, speaking time, RMS and ratio, volume stability, silence, `original_peak_dbfs`, `dubbed_peak_dbfs`, `dubbed_clipping_pct`, `dubbed_clipping_intervals[[start, end]]`, `loudness_envelope {step_sec, original_db[], dubbed_db[]}`.
- `speech_recognition`: script scores (`wer`, `cer`, `primary_metric`, `error_rate`, `accuracy_pct`; `null` unless the CLI got `--script`), `ground_truth`, both transcripts, both speech rates, `dubbed_language_detected`, `dubbed_language_probability`, `dubbed_language_windows[{start, end, language, probability, expected_probability}]`, `clarity {confident_pct, mean_logprob, segments, unclear_segments[]}`, `original_segments[]`, `dubbed_segments[]`.
- `timing_alignment`: `overlap_pct`, `original_covered_pct`, `dub_in_original_pct`, `start_offset_sec`, `end_offset_sec`, `mismatches[{start, end, kind}]`, `original_speech[]`, `dubbed_speech[]`.
- `voice_quality`: see `dubeval/voice_quality.py` above. `voice_similarity`: see `dubeval/speaker.py` above.
- `video_integrity`: `original` / `dubbed` `{readable, width, height, fps, frames, duration_sec, has_audio}`, `same_resolution`, `same_fps`.
- `lipsync_metrics`: `measured`, `sync` (the lip-sync check's result, `dubeval/lip_sync.py`; `None` when it didn't run, and then `valid`, `reason`, zero-lag and best-lag correlation, face coverage, the original's values and waveforms come from the lip-movement estimate).
- `translation_judge`: `{measured, reason, model, meaning_score, summary, issues[]}`.
- `report`: the output of `build_report`, including `problem_intervals[]`, `possible_asr_errors[]` and `problem_seconds`.
- `pipeline`: `run_id`, `execution_mode`, local video paths, target language name/code/id, `share {share_url, seq, title, source_language_name, source_language_code, target_language_name, is_lipsync, evaluated_video, duration_ms, created, original_from}`, `timestamp`, `report_files`.

Version 6 turned `warnings` into `{key, params, text}` objects, added `reason_key` / `reason_params` to lip-sync and translation-check results, and made the judge's `summary` and issue `explanation` `{en, ko, pt, es}` objects. Version 5 removed the dubbing-only keys (`perso_translation`, `vs_perso_script`, `perso_translation_vs_target`, `pipeline.perso`, `lip_dubbing_enabled`). When you rename or remove keys, bump `SCHEMA_VERSION` in `evaluate.py`.

## Configuration
| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | none | Turns on the translation check with Gemini (preferred) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | First Gemini model tried (`gemini-flash-latest` is the fallback) |
| `GEMINI_THINKING` | `low` | Gemini thinking level: `low` ≈ 3 s per review, `high` ≈ 40 s |
| `ANTHROPIC_API_KEY` | none | Translation check with Claude, when no Gemini key is set |
| `CLAUDE_JUDGE_MODEL` | `claude-opus-5-5` | Claude model for the translation check |
| `WHISPER_MODEL` | `auto` | Speech model: **automatic**: Whisper `large-v3-turbo` when it is downloaded (Settings → Models) and the computer has an NVIDIA GPU, otherwise `base` (`asr.default_model`; `auto` is resolved where a model is loaded and in cache keys, so results name the model that ran). The start page's More options and the CLI's `--whisper-model` can name one |
| `MAX_KEPT_RUNS` | `0` | App run folders kept (0: all, until the person deletes them on the Evaluations screen) |
| `MAX_CACHED_LINKS` | `20` | Share links whose downloads and Whisper results stay cached |
| `PERSO_API_BASE` / `PERSO_MEDIA_BASE` | `https://api.perso.ai` / `https://portal-media.perso.ai` | Endpoints |

## Inputs, speech recognition and the report format (engine foundation)

### `dubeval/inputs.py`
Turns what the user gives into local media and checks it before anything is measured. `fetch(spec, folder, label)`:
a local path as is (resolved), or a link downloaded into the cache folder once (`<hash>.<ext>`; a direct media link
over HTTP with retries, a web page through yt-dlp when installed, otherwise a plain error that names the `links`
extra). `select_track(path, n, folder, label)` keeps only audio track `n` (counted from 0) plus the video, into
`<hash>_track<n>.mkv` with `-c copy`. `probe(path)` reads ffmpeg's stream list (duration, a video stream, the audio
tracks with their language tags); `check(path, label)` refuses unreadable files, files without audio and videos
longer than `DUBEVAL_MAX_MINUTES` (default 120). `read_subtitles(path, label)` parses SRT and WebVTT into
`[{start, end, text}]` with formatting tags removed.

### `dubeval/pipeline.py`: `evaluate_files` / `run_files_evaluation`
Inputs are fetched, tracks selected and both files checked; the dub's language is detected from its first 30 s
when `target_lang` isn't given (a guess below `LANGUAGE_GUESS_OK` = 0.8 adds the `r.warn.lang_guess` warning);
then `run_full_evaluation` runs as for share links, with lip movement off unless asked. The cache folder is keyed by
the inputs as given. `pipeline["input"]` records `{kind: files | tracks, title, original, dub, original_track,
dub_track, source/target language name and code, languages_from {source, target: given | detected},
original_media, dub_media (probes), subtitles {original, dub: cue counts}}`; the cues themselves are in
`results["subtitles"]`. The title is the dub's file name, or its folder's name when the file name is generic
(`dubbed.mp4`).

### `dubeval/asr.py`
One interface over faster-whisper (default) and openai-whisper, chosen by `DUBEVAL_ASR` (falls back to whichever is
installed). `transcribe` returns `{text, language, segments[{start, end, text, avg_logprob, no_speech_prob,
words[[start, end]]}]}` from both; `language_probs` returns `{code: probability}` from the first 30 s. Both are
seeded (`SEED`). `voice_activity` returns where Silero's voice detector (bundled with faster-whisper) hears speech;
`evaluate.keep_voiced` uses it to drop recognized lines over music and effects. faster-whisper runs on the GPU in float16 when CTranslate2 sees one (tested once at load, so a
missing CUDA library falls back to 8-bit CPU), else on the CPU; `DUBEVAL_DEVICE=cpu` forces the CPU. On Windows,
PyTorch's `lib` folder is added to the DLL search path so CTranslate2 finds cuBLAS/cuDNN. Cache keys and
`metadata.speech_recognizer` use `model_id()` (`faster-whisper:base`).

### `dubeval/schema.py` and `schemas/report.schema.json`
report.json is `{format: "dubeval-report", format_version, tool_version, report, results}`. The Pydantic models
type the report (overall, sections and metrics, problem intervals, project, not measured) and allow extra fields;
`FORMAT_VERSION` goes up only when a field is renamed or removed or changes meaning. `dubeval schema` prints the
JSON Schema; `tests/test_schema.py` checks that saved reports validate and that the committed schema is current.
