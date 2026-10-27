# Packaging the Windows desktop app

**Decided 2026-10-22: option C.** Its two code changes are done and checked (see "Done" below); the build itself is next.


How to ship Python, DubEval, ffmpeg and the models inside the Electron app (`desktop/`) so a person installs one
thing and never sees a terminal. Measured on the development PC (2026-10-22); sizes are on disk, before compression.

## What the Python side weighs today
| Part | Size | Needed for |
|---|---|---|
| PyTorch (CUDA build) | **4.2 GB** | only the BGE-M3 meaning screen (through sentence-transformers), the optional openai-whisper recognizer, and the CUDA DLLs faster-whisper borrows on the GPU |
| Everything else in `.venv` | ~1.5 GB | OpenCV 138 MB, SciPy 113, transformers 106, numba/llvmlite 144, ffmpeg (imageio-ffmpeg) 84, MediaPipe 63, CTranslate2 60, onnxruntime 46, ... |
| of which Streamlit, pandas, pyarrow, pydeck | ~200 MB | nothing any more (Streamlit was removed): drop them |
| Standalone Python 3.14 | ~150 MB | the interpreter (PersoDub ships the same) |

Models (downloaded on first use today):
| Model | Size | Needed for |
|---|---|---|
| faster-whisper `base` | ~145 MB | speech recognition: almost every check. **Bundle it.** |
| faster-whisper `large-v3-turbo` | ~1.6 GB | better recognition of less common languages (optional) |
| BGE-M3 | 4.35 GB as downloaded today (an int8 ONNX copy is ~0.6 GB) | the offline meaning screen (optional; the judge works without it) |
| WeSpeaker | 26 MB | voice similarity. Bundle it. |
| DNSMOS, MediaPipe face | already in `dubeval/models/` | voice quality, lip movement |
| Qwen3 8B + Ollama | 5.0 GB + ~1.8 GB | the local translation judge (optional; Claude or Gemini need no download) |

The finding that shapes everything: **without PyTorch, DubEval's core drops from ~5.7 GB to ~1.3 GB.** Only two
things pull torch in, and both have torch-free routes: the meaning screen can run BGE-M3 on onnxruntime (already
installed), and faster-whisper on the GPU needs only NVIDIA's cuBLAS and cuDNN libraries (as pip wheels, ~1 GB),
not torch.

## Options

### A. PersoDub's way: small installer, environment built on first run
The installer carries Electron, a standalone Python and DubEval's code (~150-200 MB). On first launch a setup page
runs pip into `%LOCALAPPDATA%\DubEval` (CPU or CUDA torch picked by the GPU found), marks each step done, then models
download on first use.
- Good: smallest download; same technique as PersoDub; easy to update packages.
- Bad: needs internet and 5-15 minutes on first run; pip can fail on someone's machine (proxies, antivirus, PyPI
  outages), and every failure is a support case; a PC can end up with a different set of versions than we tested.

### B. Everything prebuilt in the installer, offline
Build the environment once on our side and pack it into the installer, with the `base` speech model.
- With torch (CUDA): **~6 GB installed, ~2.5-3 GB installer.** Too big; and most people have no NVIDIA GPU.
- Without torch, CPU only: **~1.5 GB installed, ~450-550 MB installer.** Works offline right after install, the
  exact versions we tested, no pip on the person's PC.
- Bad: GPU users get CPU speed; a new package version means a new installer.

### C. Recommended: prebuilt CPU core + optional packs downloaded from inside the app
Option B without torch as the installer (~450-550 MB, offline, nothing to build), plus a **Downloads** section in the
app where a person chooses extras, each with its size, a progress bar and a checksum:
| Pack | Size | Adds |
|---|---|---|
| GPU acceleration (NVIDIA only, offered only when one is found) | 736 MB (measured) | faster speech recognition through CUDA |
| Meaning screen | 586 MB (measured) | the offline line-by-line meaning check |
| Better recognition for less common languages | ~1.6 GB | `large-v3-turbo` |
| Local translation checker | ~7 GB | Ollama + Qwen3 8B, for checking without Claude or Gemini |

- Good: one reliable, offline install for everyone; nobody downloads gigabytes they don't use; the person agrees to
  each large download; the same file sets work on every PC.
- Bad: two code changes first (below), and the meaning screen's scores must be checked against today's torch
  version before its 0.60 band is trusted.

## Done (2026-10-22)
- **Meaning screen on onnxruntime.** `tools/build_meaning_onnx.py` exports BGE-M3 with its pooling and quantizes it
  to int8: `model.onnx` 569 MB + `tokenizer.json` 17 MB, built in under a minute. `dubeval/meaning.py` uses it when
  present (about 30 ms per line on the CPU, 2 s to load). On the 25 lines of the labelled pairs it scores on average
  0.009 lower than the original model, 95% of lines within 0.023, at most 0.037, and **no line crosses the 0.60
  band**, so `SCREEN_LOW` stays. Found and fixed on the way: the exported graph mishandles padding, so each line is
  embedded on its own.
- **GPU without PyTorch.** In a fresh environment with no torch, DubEval's recognizer ran on the GPU with only
  NVIDIA's cuBLAS: `cublas64_12.dll` (98 MB) + `cublasLt64_12.dll` (638 MB), from a plain folder
  (`DUBEVAL_CUDA_DIR`, default `~/.cache/dubeval/cuda`). cuDNN wasn't needed. 96 s of speech: `base` 1.7 s on the
  GPU vs 6.0 s on the CPU; `large-v3-turbo` 2.8 s vs 28.7 s. So the GPU pack matters mostly for the large model.
- **Runtime requirements without PyTorch**: `requirements.txt` is now the runtime (adds `tokenizers`,
  `python-multipart`); torch, openai-whisper, sentence-transformers and onnx moved to `requirements-dev.txt`.
  Docker no longer installs torch (not rebuilt yet).

- **The whole runtime, checked clean** (2026-10-22): a fresh Python 3.11 environment from `requirements.txt` only is
  **1.09 GB, with no PyTorch, transformers or Whisper**. A full evaluation of test pair p006 there (GPU through the
  two cuBLAS files) gave the same report as the development environment with the same settings: identical
  transcripts, meaning scores, problem intervals and levels on every measure. It took 47-70 s vs 41 s (first runs,
  cold caches). The fast test suite passes there too (one test about the original Whisper's PyTorch seeding is
  skipped). Found and fixed: language names came from the original Whisper package; they now ship with DubEval
  (`dubeval/languages.py`).
- **Install path must stay short**: pip couldn't write some `anthropic` files under a deep folder (Windows' 260-character
  path limit). Install the bundled Python under a short folder (e.g. `%LOCALAPPDATA%\DubEval\py`), or drop
  `anthropic` from the bundle and call Claude over HTTP.

- **The first Windows installer** (2026-10-22): `tools/build_desktop.py` (126 s) makes a 1,016 MB Python 3.11.9 bundle
  (no PyTorch; 84 MB of the packages' test suites removed) + 174 MB of models (faster-whisper `base`, speaker
  model); `npm run dist` makes **`DubEval-Setup-0.1.0.exe`, 488 MB**, a per-user installer. The built app started its
  own Python isolated (`-I`), served the web interface, kept its data in `%APPDATA%\DubEval\data`, and closing it
  left no Python running. A full evaluation with the bundled Python (Hugging Face offline, so the shipped model was
  used) matched the development environment on the CPU on every measure. Not signed: `signAndEditExecutable` is off
  because electron-builder's signing tools need symlinks (Windows Developer Mode); the default Electron icon.
- **Runtimes upgraded** (2026-10-23, after the security review): Python 3.14.9 (python.org, signature and checksum
  checked; every pin has a cp314 Windows wheel) and Electron 44.9.3 with electron-builder 26.15.3 and fuses on. The
  bundle stays ~1 GB (Tcl/Tk 9 and CPython's C test modules skipped); the installer is 513 MB. The built app started
  in 3 s, and a 30 s YouTube + uploaded-dub pair evaluated in 20 s on its Python. Voice similarity no longer
  fights the voice-quality model for the processor (`dubeval/ort_session.py`): on the 96 s test pair it went from
  11.8 s to 1.8 s with identical scores, and the whole evaluation from 30.4 s to 20.0 s.
- **CPU and GPU recognition differ** (found while checking): on p006 the CPU (int8) split the dub into 7 matched lines,
  the GPU (float16) into 13, and the meaning screen was Good vs Check. The desktop app runs on the CPU unless the GPU
  pack is installed, so calibration (Phase 5) should be checked on the CPU too.

- **Downloads page** (2026-10-22): `dubeval/packs.py` + `#/downloads`. No hosting of our own was needed: the meaning
  pack comes from Xenova/bge-m3's int8 ONNX export on Hugging Face, the GPU pack from NVIDIA's cuBLAS wheel on PyPI
  (only two DLLs kept), the large model from its Hugging Face repo, all pinned to fixed revisions with SHA-256.

- **Faster first run** (2026-10-22): librosa compiles 12 functions with numba the first time they load; the build now
  runs them once inside the bundle (`WARM_UP` in `tools/build_desktop.py`) so the compiled cache ships. On a 96 s pair
  the installed app's first same-video check went from 16.4 s to 5.9 s (whole evaluation 44.5 s → 31.9 s). The sound
  of both videos is now read once for the check, the language guess and the evaluation (`evaluate.load_both`);
  decoding the two pictures side by side gave no gain on this PC (ffmpeg already uses the cores for one video).

- **Release check** (2026-10-27, installer 0.1.0, about 505 MB): uninstalled (program files and shortcuts removed,
  `%APPDATA%\DubEval` kept, as `deleteAppDataOnUninstall: false` intends), moved the data aside and installed fresh:
  2.2 minutes, 1.5 GB on disk, desktop and Start menu shortcuts made, the app ready about 6 s after opening, with an
  empty Evaluations list and no keys. Downloaded models live in `~/.cache/dubeval` and survive an uninstall, so a
  first run without them was not covered here. The full test suite (1,443 tests, with the slow Whisper run) passed.

## Still to do for option C
1. DubEval's own icon and auto-update are done (see `desktop/README.md`).
2. Later: code signing (until then Windows SmartScreen warns on first run; INSTALL.md's install steps say what to
   click), the macOS build.

Licenses to add to NOTICE when shipping: Python (PSF), ffmpeg from imageio-ffmpeg (GPL build: fine under AGPL, but
its license text and source offer ship with the app), CUDA libraries (NVIDIA's redistribution terms) in the GPU pack,
and each model's license (already listed in `dubeval/models/README.md` for the bundled ones).
