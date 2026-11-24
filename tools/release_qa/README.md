# Release QA

An automated "new user" test of a published DubEval release, and a report like a tester's: what passed, what failed,
timings, screenshots and logs, with the problems listed most serious first.

```bash
pip install -r tools/release_qa/requirements.txt          # once (Playwright; it drives the app, no browser download)
python tools/release_qa/release_qa.py                     # the latest GitHub release → data/qa/<tag>_<time>/
python tools/release_qa/report.py data/qa/<tag>_<time>    # report_en.html + report_en.pdf (--lang ko for Korean)
```

- **Before a release:** `--dev` tests this repository's code instead (desktop/ with its Electron and the `.venv`):
  nothing is installed, and its data and profile stay in the run folder.
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
- `release_qa.py` is for Windows. The window is driven through Chrome DevTools (`--remote-debugging-port`) with Chromium's background
  throttling off, so it keeps full speed behind other windows. Runs take about 5 minutes on a laptop GPU.

## On a Mac

```bash
python tools/release_qa/release_qa_mac.py --host <user>@<mac address> --key ~/.ssh/<key>      # the installed app
python tools/release_qa/release_qa_mac.py --host ... --key ... --app ~/dubeval-build/desktop/dist/mac-arm64/DubEval.app
python tools/release_qa/report.py data/qa/v<version>-mac_<time>
```

The same scenarios, run from this computer on a Mac over SSH (a key, no password prompt; `DUBEVAL_MAC_HOST` and
`DUBEVAL_MAC_KEY` can stand in for the options, and neither goes in the repository). It copies the test clips into
`~/dubeval-release-qa` on the Mac, starts the app there with its own profile under `caffeinate` (a Mac that slept
mid-run once made a 3.5-minute evaluation take 16), drives it through an SSH tunnel to its DevTools port, then closes
it and deletes that folder (`--keep` keeps it). It installs nothing: install the release first (or point `--app` at a
build). The run folder is named `v<version>-mac_<time>` and holds the same `results.json`, screenshots and `server.log`.
On an M2 Pro with every optional download, the first evaluation takes about 3.5 minutes; run it once more to see the
saved-measurement timings.
