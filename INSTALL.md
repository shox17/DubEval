# Installing DubEval

The desktop app for Windows, or DubEval from source on any computer (command line, web interface, REST API), or in Docker. Back to the [README](README.md).

## Install the desktop app (Windows beta)
For Windows 10 or 11 (64-bit). No Python or other tools needed.

1. [Download `DubEval-Setup.exe`](https://github.com/shox17/DubEval/releases/latest/download/DubEval-Setup.exe),
   always the newest version (about 500 MB: the app, Python and the speech, voice and picture models are inside, so
   evaluations work offline). Every version is on the [Releases page](https://github.com/shox17/DubEval/releases).
2. Open it. Because the beta isn't code-signed yet, Windows may show **"Windows protected your PC"** (SmartScreen).
   Click **More info**, check that the app is `DubEval-Setup.exe` and the publisher reads "Unknown
   publisher", then click **Run anyway**. If your browser warns about the download first, choose **Keep**. Only do
   this for a file you downloaded from this repository's Releases page.
3. Choose **Install**. It takes about 2 to 3 minutes and needs about 1.5 GB of disk space; no administrator rights
   are needed (it installs for your Windows user only).
4. DubEval opens on **Evaluations**. Choose **New evaluation**, add the original and the dub, and start.
5. Optional: **Settings → API keys** to turn on the translation check (a Claude, Gemini or ChatGPT key), and
   **Settings → Models** for optional downloads (an NVIDIA GPU speed-up, a larger speech model, an offline meaning
   check). Without a key, everything else works and the translation check shows as "not measured".

**Updates:** DubEval checks this repository's Releases when it starts. When a new version is out, it shows what's new
and installs it only when you choose to restart (it warns you first if an evaluation is still running).

**Uninstall:** Windows Settings → Apps → DubEval. Your evaluations, history, settings and keys stay in
`%APPDATA%\DubEval`, and downloaded models in `%USERPROFILE%\.cache\dubeval`; delete those folders too to remove
everything.

## Get started on a new machine
To run DubEval from source (any OS, for the command line, the REST API or development).

### 1. What you need
- **Python 3.14** (the pinned versions in `requirements.txt` were verified on 3.14; 3.11–3.13 work with the version ranges in `pyproject.toml`). Check with `python3 --version` (`py -0` on Windows lists every installed Python).
- **git**
- About **2 GB of free disk space** to run DubEval (no PyTorch needed), plus about 5 GB for the development tools (PyTorch, the original Whisper and BGE-M3).
- Optional: an **NVIDIA GPU**. Speech recognition uses it automatically and falls back to the CPU when it can't.
- A **Gemini API key** (`GEMINI_API_KEY`, from Google AI Studio) for the translation check. A Claude key (`ANTHROPIC_API_KEY`) also works. Without a key, everything else still runs and the translation check shows as "not measured".

`ffmpeg` is **not** needed separately; it comes with the `imageio-ffmpeg` package.

### 2. Install
```bash
python3.11 -m venv .venv                       # Windows: py -3.11 -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                # to run DubEval: pinned, no PyTorch

## Docker
```bash
docker build -t dubeval .
docker run -p 127.0.0.1:8501:8501 -v dubeval-data:/data --env-file .env dubeval        # web: open the printed link
docker run --rm -v dubeval-data:/data --env-file .env dubeval python qa.py "<link>"     # the CLI (files in /data/output)
docker compose up                                                                            # web; add --profile api for the API on :8000
```
CPU only and without PyTorch, runs as a non-root user, Whisper and the speaker model baked in (works offline), data, history and jobs on the `/data` volume. The image was ~3.7 GB with PyTorch; it is smaller now (not rebuilt since). A 60 s dub takes ~40–50 s in the container. On Linux ARM (Docker on Apple Silicon) the MediaPipe pin is relaxed to 1.x, because 0.10.x has no Linux ARM wheel for Python 3.14; the whole test suite, including the real-Whisper and lip-movement tests, passes inside the image.
