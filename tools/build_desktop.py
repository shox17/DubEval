"""Builds what the desktop app ships next to Electron: a standalone Python with DubEval's runtime, and its models.

    python tools/build_desktop.py [--python C:\\path\\to\\Python314] [--out desktop/resources]

Windows only for now. Writes:
  <out>/python/   a copy of a Python 3.14 install (no site-packages, tests, Tk, docs or headers) with requirements.txt
                  (no PyTorch) and DubEval installed into it, then pip removed; started with `python -I -m dubeval`
  <out>/models/   faster-whisper-base/ and the speaker model, which DubEval finds through DUBEVAL_BUNDLED_MODELS
  <out>/build.json  versions, sizes and checksums
Then `npm run dist` in desktop/ makes the installer (electron-builder). The base Python must be the official
python.org build of the same minor version as the pins (3.14); the meaning, GPU and large-model packs are downloaded
later, not shipped.
"""
import argparse
import compileall
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PYTHON_MINOR = (3, 14)
# Parts of a python.org install the app never uses (relative to the install folder; any depth for the names below).
SKIP_TOP = {"Doc", "Tools", "include", "libs", "Scripts", "tcl", "NEWS.txt"}
SKIP_LIB = {"site-packages", "test", "idlelib", "tkinter", "turtledemo", "lib2to3", "unittest/test"}
SKIP_FILES = {"_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "tcl90.dll", "tcl9tk90.dll", "libtommath.dll",  # Tk 8.6/9
              "pythonw.exe"}
WHISPER_MODEL = "Systran/faster-whisper-base"
# The installer writes files one by one on one CPU core (about 12 ms each, measured 2026-10-26: 18,903 files took
# 3.5 minutes, and an update first deletes them all). Pure-Python packages are packed into one zip that Python imports
# from (zipimport, with compiled .pyc inside), which halves the file count. Never zipped: packages with compiled code
# or data read through real paths (a binary is detected below), namespace packages, and these:
ZIP_NAME = "dubeval-pure.zip"
NEVER_ZIP = {"dubeval",       # the web pages are served from real files
             "librosa",       # its numba cache (.nbi/.nbc) must sit next to the code
             "cffi"}          # compiles C at run time from its own headers
BINARY = {".pyd", ".dll", ".so", ".exe", ".lib"}
# Model files are opened by path (onnxruntime can't read one inside a zip): a package that has one stays real files.
# faster-whisper's voice detector (assets/silero_vad_v6.onnx) broke every evaluation of 0.1.2 that way.
OPENED_BY_PATH = {".onnx"}
# Runs inside the bundle at build time: librosa compiles some functions with numba the first time they load and
# caches the result next to their source (__pycache__/*.nbi, *.nbc). Doing it here ships that cache, so a fresh
# install's first evaluation doesn't spend ~10 s compiling (measured 2026-10-22).
WARM_UP = """
import tempfile, wave
from pathlib import Path
import numpy as np
from dubeval import evaluate, pairing
sr = 16000
t = np.arange(sr * 3) / sr
y = (0.2 * np.sin(2 * np.pi * 220 * t) * (t % 1 < 0.6)).astype(np.float32)
with tempfile.TemporaryDirectory() as tmp:
    path = str(Path(tmp) / "warm.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    y = evaluate.load_audio(path)
evaluate.analyze_acoustics(y)
evaluate.loudness_envelope(y)
pairing.onset_envelope(y, sr)
import librosa
for name in ("pyin", "zero_crossings", "onset.onset_detect", "util.localmax", "util.localmin", "util.peak_pick"):
    obj = librosa
    for part in name.split("."):
        obj = getattr(obj, part)
librosa.onset.onset_detect(y=y, sr=sr)
librosa.zero_crossings(y)
"""


def log(text: str) -> None:
    print(text, flush=True)


def size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def copy_python(base: Path, target: Path) -> None:
    """The interpreter and standard library, without what an app never needs."""
    def ignore(folder, names):
        rel = Path(folder).relative_to(base)
        skip = {n for n in names if n in SKIP_FILES or n == "__pycache__" or n.endswith(".pdb")
                or (n.startswith("_test") and n.endswith(".pyd"))}          # CPython's own C test modules
        if rel == Path("."):
            skip |= {n for n in names if n in SKIP_TOP}
        if rel.parts[:1] == ("Lib",):
            inner = Path(*rel.parts[1:]) if len(rel.parts) > 1 else Path()
            skip |= {n for n in names if (inner / n).as_posix() in SKIP_LIB}
        return skip
    shutil.copytree(base, target, ignore=ignore)
    (target / "Lib" / "site-packages").mkdir()


def run(python: Path, *args: str) -> str:
    """Runs the bundled Python isolated from the user's environment (-I: no user site, no PYTHON* variables)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    out = subprocess.run([str(python), "-I", *args], cwd=REPO, env=env, capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"Failed: python {' '.join(args)}\n{out.stdout[-3000:]}\n{out.stderr[-3000:]}")
    return out.stdout


def strip_site_packages(site: Path) -> float:
    """Removes the packages' own test suites and pip's leftovers; returns the MB saved."""
    before = size_mb(site)
    for folder in [p for p in site.rglob("*") if p.is_dir() and p.name in ("tests", "test")]:
        if folder.exists() and folder.parent != site:            # a package's tests, never a top-level package
            shutil.rmtree(folder)
    return before - size_mb(site)


def zip_pure_packages(site: Path) -> tuple[int, list[str]]:
    """Packs pure-Python packages into site/ZIP_NAME (with legacy-layout .pyc, which zipimport reads) and adds it to
    sys.path through a .pth file; returns the files removed and the packages zipped."""
    packages = []
    for d in sorted(site.iterdir()):
        if (not d.is_dir() or d.name in NEVER_ZIP or d.name.endswith((".dist-info", ".egg-info", ".data"))
                or d.name == "__pycache__" or not (d / "__init__.py").is_file()):
            continue
        files = [f for f in d.rglob("*") if f.is_file()]
        if any(f.suffix.lower() in BINARY | OPENED_BY_PATH for f in files):
            continue
        packages.append(d.name)
    removed = 0
    with zipfile.ZipFile(site / ZIP_NAME, "w", zipfile.ZIP_STORED) as z:      # the installer compresses it anyway
        for name in packages:
            folder = site / name
            for cache in folder.rglob("__pycache__"):
                shutil.rmtree(cache)
            compileall.compile_dir(str(folder), legacy=True, quiet=1, workers=0)   # module.pyc next to module.py
            for f in sorted(folder.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(site).as_posix())
                    removed += 1
            shutil.rmtree(folder)
    (site / "dubeval-pure.pth").write_text(ZIP_NAME + "\n", encoding="utf-8")
    return removed, packages


def copy_models(models: Path) -> dict:
    """The faster-whisper base model and the speaker model (downloaded into the usual caches first if needed)."""
    from huggingface_hub import snapshot_download
    from dubeval import speaker
    whisper_dir = models / "faster-whisper-base"
    source = Path(snapshot_download(WHISPER_MODEL))
    shutil.copytree(source, whisper_dir)                          # follows the cache's links: real files
    shutil.copy(speaker.model_path(), models / speaker.MODEL_NAME)  # checksum-verified by model_path
    return {p.relative_to(models).as_posix(): {"bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(models.rglob("*")) if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", default=sys.base_prefix, help="A python.org Python 3.14 install folder "
                    "(default: the one behind this interpreter)")
    ap.add_argument("--out", default=str(REPO / "desktop" / "resources"), help="Output folder")
    args = ap.parse_args()
    if os.name != "nt":
        raise SystemExit("Windows only for now.")
    base, out = Path(args.python), Path(args.out)
    if not (base / "python.exe").is_file() or not (base / "Lib" / "os.py").is_file():
        raise SystemExit(f"Not a Python install folder: {base}")
    started = time.time()
    for part in ("python", "models"):
        shutil.rmtree(out / part, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    log(f"1/5 Copying Python from {base}...")
    copy_python(base, out / "python")
    python = out / "python" / "python.exe"
    version = run(python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])").strip()
    if tuple(map(int, version.split(".")[:2])) != PYTHON_MINOR:
        raise SystemExit(f"Python {version} found; the pins in requirements.txt are for {PYTHON_MINOR[0]}.{PYTHON_MINOR[1]}.")

    log("2/5 Installing requirements.txt (no PyTorch) and DubEval...")
    run(python, "-m", "ensurepip", "--default-pip")
    run(python, "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location",
        "-r", str(REPO / "requirements.txt"))
    run(python, "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "--no-deps",
        str(REPO))
    packages = dict(line.split("==", 1) for line in run(python, "-m", "pip", "freeze").split() if "==" in line)

    log("3/5 Checking the bundle...")
    for banned in ("torch", "transformers", "sentence-transformers", "openai-whisper", "streamlit"):
        if banned in packages:
            raise SystemExit(f"{banned} ended up in the bundle; it must stay out of the runtime.")
    run(python, "-c", "import dubeval.webapp, dubeval.evaluate, dubeval.meaning, faster_whisper, onnxruntime, cv2")

    log("4/5 Removing pip and the packages' test suites...")
    run(python, "-m", "pip", "uninstall", "-y", "--disable-pip-version-check", "pip", "setuptools")
    shutil.rmtree(out / "python" / "Lib" / "ensurepip", ignore_errors=True)
    shutil.rmtree(out / "python" / "Scripts", ignore_errors=True)   # pip's launchers point at this build machine
    saved = strip_site_packages(out / "python" / "Lib" / "site-packages")
    run(python, "-c", "import dubeval.webapp, dubeval.evaluate, faster_whisper, onnxruntime, cv2, librosa, mediapipe")

    log("    Compiling the audio code once (librosa's numba functions), so the first evaluation isn't slower...")
    run(python, "-c", WARM_UP)
    compiled = len(list((out / "python" / "Lib" / "site-packages").rglob("*.nbi")))
    if not compiled:
        raise SystemExit("The audio code left no compiled cache; the first evaluation would be ~10 s slower.")
    log(f"    {compiled} compiled functions cached")

    log("    Packing the pure-Python packages into one zip (a faster install and update)...")
    removed, zipped = zip_pure_packages(out / "python" / "Lib" / "site-packages")
    # Every zipped package must still import from the bundle, as must the whole app.
    run(python, "-c", "import importlib, sys\n"
        f"for name in {zipped!r}:\n"
        "    mod = importlib.import_module(name)\n"
        f"    assert '{ZIP_NAME}' in (getattr(mod, '__file__', '') or ''), name\n"
        "import dubeval.webapp, dubeval.evaluate, dubeval.meaning, faster_whisper, onnxruntime, cv2, librosa, mediapipe\n"
        "import yt_dlp, anthropic, zoneinfo; zoneinfo.ZoneInfo('Asia/Seoul')\n"
        "import requests, certifi; open(certifi.where()).read(10)\n"
        # Run what loads model files, not just import it: the voice detector must find its model.
        "import numpy as np; from dubeval import asr\n"
        "assert asr.voice_activity(np.zeros(32000, dtype=np.float32)) is not None, 'the voice detector did not load'")
    files = sum(1 for _ in (out / "python").rglob("*") if _.is_file())
    log(f"    {len(zipped)} packages zipped ({removed} files); the bundle now has {files} files")

    log("5/5 Copying the models...")
    (out / "models").mkdir()
    models = copy_models(out / "models")

    from dubeval.version import TOOL_VERSION
    info = {"dubeval": TOOL_VERSION, "python": version, "built": time.strftime("%Y-%m-%d %H:%M"),
            "python_mb": round(size_mb(out / "python")), "models_mb": round(size_mb(out / "models")),
            "packages": packages, "models": models}
    (out / "build.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    log(f"Done in {time.time() - started:.0f} s: Python {version} {info['python_mb']} MB "
        f"(test suites removed: {saved:.0f} MB), models {info['models_mb']} MB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
