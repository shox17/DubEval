# DubEval desktop

A window around the web interface, so nobody needs a terminal: Electron starts DubEval's Python server
(`python -m dubeval web --port 0 --no-browser`) on a free port, reads the launch link it prints, and opens it.
Closing the window stops the server.

## Run it (development)
Needs [Node.js](https://nodejs.org) 20 or newer, and DubEval installed in the project's `.venv` (see the main README).
```bash
cd desktop
npm install          # once: downloads Electron (~100 MB); package.json allows only Electron's own install script
npm start
```
`DUBEVAL_PYTHON=/path/to/python` picks another Python with DubEval installed (for example the built bundle,
`resources/python/python.exe`, to try it before making the installer).

## Build the Windows installer
```bash
python tools/build_desktop.py      # from the project folder, with the development .venv: makes desktop/resources/
cd desktop && npm run dist         # electron-builder → desktop/dist/DubEval-Setup.exe
```
`tools/build_desktop.py` copies a python.org Python 3.14 (without tests, Tk, docs, headers), installs
`requirements.txt` (no PyTorch) and DubEval into it, removes pip and the packages' test suites, refuses the build
if PyTorch or another development package got in, and copies the faster-whisper `base` and speaker models into
`resources/models`. `resources/build.json` records versions, sizes and checksums. Pure-Python packages (51 of them, about 9,900 files) are packed into one
`Lib/site-packages/dubeval-pure.zip` that Python imports from (listed in `dubeval-pure.pth`, with compiled `.pyc`
inside): the installer writes files one by one on one CPU core, about 12 ms each, so 18,900 files took 5–7 minutes
to install and an update first deletes them all; with 9,000 files an install takes under 3 minutes (2026-10-26).
Packages with compiled code, namespace packages, `dubeval` (its web pages are served from real files), `librosa` (its
numba cache) and `cffi` stay as files; the build imports every zipped package from the bundle to check. The installer is per-user (no
admin), into `%LOCALAPPDATA%\Programs\DubEval` (keep this path short: some packages have very long file names).

In the installed app the server runs the shipped Python isolated (`-I`): nothing installed on the PC affects it.
Reports, history, votes and the `.env` with API keys (written by the Settings page) live in `%APPDATA%\DubEval\data`;
uninstalling keeps them.

**Icon:** `build/icon.ico` is stamped into `DubEval.exe` by `after-pack.js` (with rcedit, which also sets the exe's
name and version) and used for the installer and uninstaller; `build/icon.png` is the window icon when running from
source.

## How it works
- **Starting:** a "Starting DubEval" page shows until the server prints `DubEval: http://127.0.0.1:<port>/?token_given=…`
  (up to 2 minutes; usually a few seconds). If Python is missing, the server exits or it takes too long, the
  page says so in the computer's language (English, Korean, Portuguese or Spanish) with the server's last lines.
- **Security:** the server listens on 127.0.0.1 only and accepts only this launch's token (see `dubeval/webapp.py`);
  the token never touches disk (it's hidden in the log), and the port is bound before the link is printed. The
  window is sandboxed (no Node in the page, context isolation); only DubEval's own pages open in it (the server's and
  `status.html`, no other local file), and other links go to the person's browser. Electron's fuses
  (`build.electronFuses` in `package.json`) turn off running DubEval.exe as plain Node.js, `NODE_OPTIONS` and the
  debugger switches, and make it load only its own integrity-checked `app.asar`.
- **Stopping:** quitting stops the server's whole process tree, waiting until it's done (`taskkill /T` on Windows),
  and the server runs with `--exit-with-parent`: it waits on the app's process and exits on its own if the app
  crashes or is killed. It never reads stdin (the app passes none): on Windows a thread blocked on the stdin pipe
  froze scipy's first import, and evaluations hung. Both were checked on Windows (closing the window and
  force-killing Electron leave no Python running). One copy of the app runs at a time; a second launch just brings the window forward.
- **Title bar:** as in PersoDub, there is no white Windows title bar (`titleBarStyle: "hidden"` with a dark
  `titleBarOverlay`): the page's empty 36 px top strip (`.topbar`, `-webkit-app-region: drag`) moves the window and the
  window buttons are drawn over its right end; `status.html` has its own drag strip while the app starts.
- **Log:** the server's output goes to `server.log` in the app's data folder (`%APPDATA%\DubEval\logs` on
  Windows); update checks write `update.log` next to it.
- **Updates** (`updater.js`, electron-updater): a packaged app checks the GitHub Releases in `build.publish` 10 s after
  starting and every 4 hours, downloads a newer version in the background and installs it on **Restart to update** or
  when the app quits. The page learns about it only through `preload.js` (`window.dubevalShell`: get, check, restart,
  on-change), and only DubEval's own page may ask. `DUBEVAL_UPDATE_URL` points the app at another feed (a folder with
  `latest.yml` and the installer served over HTTP) to try a release before publishing it.

## Publish a new version
1. Raise the version in `dubeval/version.py` **and** `desktop/package.json` (a test checks they match) and add the
   version's lines to `dubeval/release_notes.py` in all four languages.
2. Build: `python tools/build_desktop.py`, then `cd desktop && npm run dist`.
3. Write the release's description as the version's What's new lines (the English ones from
   `dubeval/release_notes.py`, one bullet each): installed apps show it in their **Version update** window when
   they find the update (the window falls back to a link to the release page when it is empty).
4. Publish a GitHub release tagged `v<version>` in the repository from `build.publish` with **all three** files from
   `desktop/dist`: `DubEval-Setup.exe`, its `.blockmap` and `latest.yml` (or `npm run release` with a
   `GH_TOKEN` that may write releases). Installed apps find it within 4 hours, or at once from Settings → About.
   Publish it as a normal release, never a draft or a **pre-release** (even for a beta): GitHub's
   `releases/latest/download/...` link and the app's update check both skip pre-releases.
The installer's name has no version (`artifactName`), so the README's download link
(`https://github.com/shox17/DubEval/releases/latest/download/DubEval-Setup.exe`) always gives the newest one; `latest.yml` names the file, so updates work the same.
Until the installer is code-signed, an update is trusted only because it comes from that repository.

**First release only:** create the repository as exactly `shox17/DubEval` (the name in `build.publish`; another name
means installed apps never find updates). In its **About** settings, set the description to "Open-source quality
check for dubbed videos. Compare a dub with its original: timing, speech, voice and meaning, every problem on a
timeline, and which of several dubs to deliver. Runs on your computer." and the topics to `dubbing`, `dubbing-qa`,
`video-translation`, `quality-assurance`, `localization`, `speech-to-text`, `whisper`, `translation-quality`,
`ai-dubbing`, `voice-cloning`, `lip-sync`, `offline`, `privacy-first`, `open-source`. The README's version badge reads
"repo not found" until the repository and its first release exist.

## Not done yet (Phase 7)
- Code signing (until then Windows SmartScreen warns on first run, and updates are trusted by their source only),
  the macOS build. Updates need the GitHub repository and its first release.
- The desktop shell's few texts live in `status.html`; the web interface brings its own.
