# Developing DubEval

Working on DubEval itself: the daily workflow, where things live, the ground rules, the REST API and CI. Setting up: [INSTALL.md](../INSTALL.md#get-started-on-a-new-machine). Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Keep building

### Daily workflow
```bash
source eval_env/bin/activate
dubeval web                   # the web interface; reload the page after editing dubeval/web/
pytest -m "not slow"          # run after every change (~6 s)
pytest                        # before committing (~20 s; the 2 slow tests need a local tests/data/sample.mp4)
```

### Where things live
```
qa.py                    Command line: python qa.py "<share link>"
dubeval/webapp.py            Web interface server (dubeval web): jobs, uploads, media, waveforms, votes, history
dubeval/web/                 The web page: plain JavaScript modules and CSS, no build step
dubeval/perso_api.py         Share links: parse the link, read the public project, download the videos
dubeval/pipeline.py          Share link → download (cached) → evaluate → translation check → report files; compare mode
dubeval/compare.py           Compare mode: decision rule, comparison model, text and HTML renderers (pure)
dubeval/intervals.py         Problem intervals: collect, merge, clip, round, sort (pure)
dubeval/api.py               REST API (FastAPI): jobs, reports, history, feedback
dubeval/paths.py             Where data lives (DUBEVAL_DATA)
dubeval/feedback.py          Reviewer votes on problem intervals and the per-check summary
dubeval/history.py           Evaluation history: record every run, summaries and trends
dubeval/batch.py             Batch mode: input file, summary rows, agreement with your verdicts (pure)
dubeval/version.py           Tool version printed in comparisons
dubeval/evaluate.py          All measurements (pure functions, no file writes)
dubeval/translation_judge.py Translation check: every line scored 1-10 on five criteria (rubric), with Claude, Gemini,
                             ChatGPT or a local model; retries, model fallback, structured JSON
dubeval/report.py            Verdict, levels, messages, things to check; text and HTML renderers (pure)
dubeval/cli.py               The command-line entry point behind qa.py
dubeval/jobs.py              Background job runner and progress model (stages, %, stop)
dubeval/i18n.py              Interface text in English, Korean, Portuguese and Spanish
dubeval/voice_quality.py     Voice quality with the DNSMOS model (ONNX, CPU)
dubeval/speaker.py           Voice similarity with a speaker-recognition model (ONNX, downloaded once, 26 MB)
dubeval/models/              Bundled models (face landmarks, DNSMOS) and their licenses
tests/                   pytest suite; tests/fake_perso.py fakes the share endpoint. tests/data/sample.mp4 (any ~30 s
                         English talking-head clip) is local test media, not in git; slow tests skip without it
data/cache/<link>/       Downloaded videos and Whisper results per share link (not committed)
data/output/runs/<id>/   Report files of each web or API run (not committed)
data/history.jsonl       Every evaluation, one line each (not committed)
data/feedback.jsonl      Reviewer votes on problem intervals (not committed)
output/                  The command line's default --out folder (not committed)
docs/                    Architecture, metrics, engineering review
Dockerfile, docker-compose.yml   Container image (web interface or API)
.github/workflows/tests.yml     CI on Linux, macOS and Windows
AGENTS.md                Guide and rules for AI coding agents (Codex reads it; CLAUDE.md imports it)
CLAUDE.md                Imports AGENTS.md for Claude Code
```

### Ground rules
- **Tests never call Perso, Gemini or Claude**, and never see real keys. They use the fake in `tests/fake_perso.py` and a stubbed translation check, so they are free and work offline.
- **Never put an API key in code or docs.** Keep it in `.env`.
- Perso API reference: https://developers.perso.ai/llms.txt.
- `dubeval/evaluate.py` and `dubeval/report.py` stay pure; the web page only shows what the server's reports say.
- If you rename or remove keys in the results, bump `SCHEMA_VERSION` in `dubeval/evaluate.py`.

### What's next
The plan to evaluate dubs from any service, and human dubs, is in [docs/roadmap.md](roadmap.md).

## REST API
```bash
python qa.py serve                         # http://127.0.0.1:8000 · interactive docs at /docs
```
| Endpoint | What it does |
|---|---|
| `POST /evaluations` `{"link": "...", "lang": "ko"}` | starts evaluating one dub → `202 {id, url}` |
| `POST /comparisons` `{"links": ["...", "..."]}` | starts ranking 2–8 dubs |
| `GET /jobs/{id}` | status, progress, and once done a result summary and report links |
| `GET /jobs/{id}/report?format=html\|json\|text` | the saved report or comparison |
| `GET /history?days=30` · `GET /feedback` · `GET /health` | summaries and a liveness check |

Jobs run in the background and are kept on disk, so ids stay valid across restarts. **Security:** without `DUBEVAL_API_TOKEN` the server only listens on this machine and only answers requests sent to `127.0.0.1` or `localhost`; set the token to listen on the network (`--host 0.0.0.0`), and send `Authorization: Bearer <token>` with every request except `/health`.

## Continuous integration
`.github/workflows/tests.yml` runs the fast, offline suite on **Linux, macOS and Windows** (Python 3.14, CPU PyTorch) for every push and pull request, plus a secret scan. No secrets are needed.
