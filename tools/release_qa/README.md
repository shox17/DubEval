# Release QA

An automated "new user" test of a published DubEval release, and a report like a tester's: what passed, what failed,
timings, screenshots and logs, with the problems listed most serious first.

```bash
pip install -r tools/release_qa/requirements.txt          # once (Playwright; it drives the app, no browser download)
python tools/release_qa/release_qa.py                     # the latest GitHub release → data/qa/<tag>_<time>/
python tools/release_qa/report.py data/qa/<tag>_<time>    # report_en.html + report_en.pdf (--lang ko for Korean)
```

- **Isolated:** the app runs with its own profile (`--user-data-dir` in the run folder), so your evaluations, settings
  and API keys are never touched. Usage stats are answered "No", so a run sends nothing.
- **Installing:** when the release isn't the installed version (or with `--reinstall`), the installer runs silently
  and **replaces your installed DubEval** (it has one location per user). Close DubEval first. `--installer
  desktop/dist/DubEval-Setup.exe` tests a local build instead of a GitHub release.
- **Scenarios:** first launch and the usage-stats question, one evaluation to its report, the review walk-through and
  a vote, export (HTML, Excel, text, zip), a comparison of two dubs, a missing file and a non-video file, Stop, history,
  Settings → About, and the screen texts in every language. Inputs are the openly licensed Tears of Steel pairs in
  `data/testset/media` (p011, p012) and p018 for Stop.
- **Reviewer findings:** add `findings.json` to a run folder (a list of `{priority, title, where, detail, fix}`, from
  looking at the screenshots) and run `report.py` again; failed checks are listed on their own either way.
- Windows only. The window is driven through Chrome DevTools (`--remote-debugging-port`) with Chromium's background
  throttling off, so it keeps full speed behind other windows. Runs take about 5 minutes on a laptop GPU.
