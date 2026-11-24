# DubEval desktop

A window around the web interface, so nobody needs a terminal: Electron starts DubEval's Python server
(`python -m dubeval web --no-browser`), reads the launch link it prints, and opens it. Closing the window stops the
server. The server takes the same port at every launch unless it's busy, because what the page keeps in the browser
(language, sidebar width, history period) belongs to its address.

## Run it (development)
Needs [Node.js](https://nodejs.org) 22.12 or newer (Electron 45's own requirement), and DubEval installed in the project's `.venv` (see the main README).
```bash
cd desktop
npm install
npm start            # the first start downloads Electron (~100 MB)
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
source. Both are rendered from `build/icon.svg` (48 px and up) and `build/icon-small.svg` (16-32 px), as are
`docs/images/icon.png` (README) and `dubeval/web/icon.png` (the app's loading screen); after changing a source SVG,
render them all again. `status.html` and the page's `index.html` carry a copy of `dubeval/web/icon.png` inside them (a
test checks they match).

## Build the macOS app (Apple Silicon)
A Mac app can only be made on a Mac. The signed, notarized build is made by hand on a Mac that holds ESTsoft's
Developer ID certificate in its login keychain and the notarization key saved under the name `dubeval-notary`
(once: `xcrun notarytool store-credentials dubeval-notary --key AuthKey_<id>.p8 --key-id <id> --issuer <issuer>`;
the certificate and key come from the company and never go in the repository):
```bash
python3 tools/build_desktop.py     # any Python 3.12+ with nothing installed: it downloads the app's own Python
cd desktop && npm ci && APPLE_KEYCHAIN_PROFILE=dubeval-notary npm run dist:mac   # → dist/DubEval-<version>-arm64.dmg, -arm64-mac.zip
```
Run it in the Mac's own Terminal, not over SSH: the first signing asks to use the certificate's key (type the Mac's
login password, then **Always Allow**), and an SSH session can't answer (`errSecInternalComponent`). Check the result
with `codesign --verify --deep --strict --verbose=2 dist/mac-arm64/DubEval.app`, `spctl -a -vv` on the app (it should
say `source=Notarized Developer ID`) and `xcrun stapler validate` on it.

GitHub's Macs make an unsigned test build (**Actions → build-mac → Run workflow**, `.github/workflows/build-mac.yml`, or
push a branch named `mac-build`) with `npm run dist:mac:adhoc`: signed ad-hoc, without the hardened runtime, which would
refuse the bundled Python's libraries signed by their makers.
- **Python:** python.org's Mac installer can't be moved into an app, so the bundle starts from a relocatable CPython
  3.14 (python-build-standalone, which PersoDub uses too), pinned to one release and its SHA-256
  (`MAC_PYTHON` in `tools/build_desktop.py`). The rest is the Windows recipe: `requirements.txt`, DubEval, no pip, no
  test suites, the pure-Python packages in one zip, the same two models.
- **Nothing is written inside the app.** A changed file breaks an app's signature, so the build compiles every
  Python file ahead of time (`unchecked-hash`, valid whatever the file times become) and the app starts Python with
  `-B`; the audio code's compiled cache (numba) goes to the data folder (`NUMBA_CACHE_DIR`) instead of being shipped,
  because it is tied to the CPU it was made on. The first evaluation on a Mac is about 10 s slower for that.
- **Signing:** ESTsoft's Developer ID (`build.mac.identity`, "Developer ID Application: ESTsoft corp. (WQL32M5H24)"),
  the hardened runtime and Apple's notarization (`notarize`, credentials from `APPLE_KEYCHAIN_PROFILE`), as PersoDub's.
  The hardened runtime allows only what `build/entitlements.mac.plist` lists: machine code written while running
  (Electron's engine, the audio code's numba) and Python's ctypes callbacks; every library the app loads carries
  ESTsoft's signature, so it needs no exception for other teams' libraries. electron-builder signs every non-text file
  one by one, so the bundled Python and models are left out of that (`build.mac.signIgnore`: thousands of data files,
  one of them read-only, stopped the first build), and `after-pack.js` signs their programs and libraries instead
  (each Mach-O file, found by how it starts), each with the hardened runtime and a timestamp, the programs with the
  entitlements. Everything is then sealed with the app.
- **Updates** (since 0.1.7): as on Windows, from the release's `latest-mac.yml` and `.zip` (the `.dmg` is only the
  download). Squirrel.Mac installs only an update signed with the same Developer ID, so every Mac release must be signed
  and notarized with ESTsoft's. A copy from before 0.1.7 (ad-hoc test builds) doesn't look for updates: install 0.1.7
  over it once. The `.dmg`'s name has no version (`dmg.artifactName`: `DubEval-Mac.dmg`), so
  `releases/latest/download/DubEval-Mac.dmg` always gives the newest one.
- **The window:** macOS's three buttons sit in the page's top strip (`trafficLightPosition`), and the app has the
  standard app, Edit and Window menus: without an Edit menu, Cmd+C and Cmd+V do nothing.
- **"Class AVFFrameReceiver is implemented in both"** in the Mac's server log is harmless (checked 2026-11-19): OpenCV
  (`cv2/.dylibs`) and PyAV (`av/.dylibs`, imported by faster-whisper) each ship FFmpeg 8 (the same 63.1.102 libraries),
  and macOS warns when two copies of `libavdevice` register the same Objective-C classes. Those classes are only for
  recording from a camera or microphone (AVFoundation capture), which DubEval never does: it reads files
  (`cv2.VideoCapture(path)`, ffmpeg), and each library's C functions stay bound to its own copy (two-level
  namespaces). Rewiring one package onto the other's libraries would change signed binaries for no gain.
- **Not available on macOS:** the NVIDIA speed-up (`windows_only` in `dubeval/packs.py`); speech recognition runs on
  the processor. The local translation checker runs on a Mac with Apple silicon (`local_judge.this_computer`).
- **Built and checked on a real Mac** (2026-11-12, an M2 Pro on macOS 15.7, by hand with the two commands above):
  the bundle builds in 90 s and the `.dmg` (579 MB) in 95 s; `codesign --verify --deep --strict` passes before and
  after an evaluation; a 13 s clip evaluates in 12 s; the app starts its server in about a second and stops it when
  closed. That build found three things the Windows build never meets, all fixed in `tools/build_desktop.py` and
  `package.json`: a Mac program has no file extension, so `ffmpeg` was packed into the pure-Python zip (programs are
  now known by how the file starts, `is_program`); a company network's security gateway re-signs model downloads, so
  the model step uses the computer's own trusted certificates as the app does; and the signing step above.
- **What the workflow checks on the Mac it builds on:** the signature (`codesign --verify --deep --strict`), one
  whole evaluation with the app's own Python on a clip it speaks with `say`, that the evaluation changed nothing
  inside the app, and that the app starts its server and stops it when closed. It publishes nothing: the `.dmg` is
  the run's artifact for 14 days.
- **Icon:** `build/icon-mac.png` (1024 px, the tile at 824 px as macOS icons are drawn), rendered from
  `build/icon.svg`; electron-builder turns it into the app's `.icns`.

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
- **Finished notification:** the app starts the server with `DUBEVAL_NOTIFY=1`, and the server prints one
  `DubEval-notify: {title, body, open}` line when an evaluation ends by itself (`dubeval/webapp.py` `_notify_app`).
  `main.js` shows it as a system notification unless the window is already in front; a click brings the window forward
  on that evaluation (`preload.js` `onOpen`; only `#/report|compare|job/<id>` addresses are opened). On Windows the
  notifications carry the app's id (`app.setAppUserModelId`, = `build.appId`); macOS asks once whether DubEval may show
  them.
- **Log:** the server's output goes to `server.log` in the app's data folder (`%APPDATA%\DubEval\logs` on
  Windows); update checks write `update.log` next to it.
- **Updates** (`updater.js`, electron-updater): a packaged app checks the GitHub Releases in `build.publish` 10 s after
  starting and every 4 hours and downloads a newer version in the background. The **Version update** window opens once
  to say so, and the sidebar's card takes a red dot and, once the file is on disk, reads **Update X is ready**. It installs
  only on **Restart to update**: closing the app leaves it as it is, and the update waits for the next time. The window
  lists the new version's own lines in the app's language, read from `dubeval/release_notes.json` at the release's tag (5 s
  at most, then the release's description, in English). A download that breaks says so and **Check for updates** tries
  again. The restart shows the installer's own progress window, because an update replaces about 9,000 files and takes
  minutes: a silent install left the person with no window at all. It asks nothing: `build/installer.nsh` skips the
  "who is this program for" page (keeping how DubEval is installed) and the Finish page when the installer runs with
  `--updated`, and starts DubEval when it's done; a first install still shows both (checked 2026-11-18 by running a test
  installer with `--updated --force-run` over 0.1.7: only the progress page, then DubEval started). Back from an update, the page says "Updated to X" once:
  the app compares its version with `last-version.txt` in its data folder. The page learns about all this only through
  `preload.js` (`window.dubevalShell`: get, check, restart, on-change), and only DubEval's own page may ask.
  `DUBEVAL_UPDATE_URL` points the app at another feed (a folder with `latest.yml`, the installer and
  `release_notes.json` served over HTTP) to try a release before publishing it.

## Publish a new version
1. Raise the version in `dubeval/version.py`, `desktop/package.json` **and** `pyproject.toml` (a test checks they
   match) and add the
   version's lines to `dubeval/release_notes.json` in all four languages.
2. Build the Python bundle: `python tools/build_desktop.py`.
3. **Sign** (since 0.1.6; ESTsoft Corp.'s certificate, through the company's internal signing portal, so it can't be
   part of the build). The portal's address and the signing folder go in `desktop/codesign.local.json` (git-ignored:
   `{"dir": "C:\\dubeval_windows_codesign", "vdiDrive": "Z:", "portal": "<address>"}`; or `DUBEVAL_CODESIGN_*`
   environment variables), never in the repository.
   - `npm run build:windows:release` builds the installer, copies it to
     `<dir>\Before_Sign\DubEval-Setup-<version>-unsigned.exe` and prints the portal steps.
   - In the VDI (this PC's `C:` is its `Z:`): upload that file to the portal, then download the signed file into
     `<dir>\After_Sign\`.
   - `npm run release:windows:finish` checks the signature (valid, signed by the `publisherName` in `package.json`,
     timestamped, this version), puts the signed installer in `dist/` and **rebuilds `latest.yml` and the `.blockmap`
     from it**. Never upload an installer it didn't finish: signing changes the file's bytes, and with the build's
     `latest.yml` every installed app refuses the update (sha512 mismatch; tested 2026-11-10).
4. Optional: test the signed installer before publishing: `python tools/release_qa/release_qa.py --installer
   desktop/dist/DubEval-Setup.exe` (it replaces the installed DubEval).
   On the Mac, install the new `.dmg` there and run `python tools/release_qa/release_qa_mac.py --host <user>@<mac>
   --key <ssh key>` from this computer: the same scenarios on the Mac (`tools/release_qa/README.md`).
5. Write the release's description as the version's What's new lines (`finish` writes the English ones to
   `dist/release-notes.md`): installed apps show it in their **Version update** window when they can't read
   `release_notes.json` at the tag, or don't read it yet (0.1.3 and earlier). With neither, the window links to the
   release page.
6. Publish a GitHub release tagged `v<version>` in the repository from `build.publish` with **all three** files from
   `desktop/dist`: `DubEval-Setup.exe`, its `.blockmap` and `latest.yml` (`finish` prints the `gh release create`
   command), **and** the Mac's files from its `desktop/dist` (since 0.1.7: build them as in "Build the macOS app",
   same version): `DubEval-Mac.dmg`, `DubEval-<version>-arm64-mac.zip`, its `.blockmap` and `latest-mac.yml`. A
   release without `latest-mac.yml` leaves every Mac app's update check failing. Installed apps find it within 4
   hours, or at once from Settings → About. Publish it as a normal release,
   never a draft or a **pre-release** (even for a beta): GitHub's `releases/latest/download/...` link and the app's
   update check both skip pre-releases. There is no `npm run release` any more: it published straight from the build,
   which would now be an unsigned installer.
The installer's name has no version (`artifactName`), so the README's download link
(`https://github.com/shox17/DubEval/releases/latest/download/DubEval-Setup.exe`) always gives the newest one; `latest.yml` names the file, so updates work the same.

**Signed updates:** the app carries `publisherName` (`build.win.signtoolOptions`; it lands in the installed app's
`resources/app-update.yml`). An app without it (0.1.5 and earlier) installs any update whose sha512 matches
`latest.yml`, signed or not, so the first signed release reaches everyone. From then on electron-updater checks each
downloaded update: it must be validly signed and its signer's CN must equal `publisherName`, or it's refused ("not
signed by the application owner"). So every later release must be signed by the same publisher; publishing an
unsigned one would strand every installed app. If the certificate's name ever changes, list both names in
`publisherName` for a release before switching.

**First release only:** create the repository as exactly `shox17/DubEval` (the name in `build.publish`; another name
means installed apps never find updates). In its **About** settings, set the description to "Open-source quality
check for dubbed videos. Compare a dub with its original: timing, speech, voice and meaning, every problem on a
timeline, and which of several dubs to deliver. Runs on your computer." and the topics to `dubbing`, `dubbing-qa`,
`video-translation`, `quality-assurance`, `localization`, `speech-to-text`, `whisper`, `translation-quality`,
`ai-dubbing`, `voice-cloning`, `lip-sync`, `offline`, `privacy-first`, `open-source`. The README's version badge reads
"repo not found" until the repository and its first release exist.

## Not done yet (Phase 7)
- Signing the app's own files (`DubEval.exe`, the uninstaller, the bundled Python): the portal signs the installer,
  which is what SmartScreen checks. Signing them too would take a second trip to the portal during the build.
- macOS: an Intel build (Apple silicon only today), and a test of the Mac update path from one released version to
  the next (the first Mac release is 0.1.7).
- The desktop shell's few texts live in `status.html`; the web interface brings its own.
