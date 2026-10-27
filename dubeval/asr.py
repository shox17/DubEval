"""Speech recognition: one interface over faster-whisper (the default) and the original openai-whisper.

Both backends return the same shapes, so the rest of DubEval never knows which one ran:
  transcribe() -> {"text", "language", "segments": [{start, end, text, avg_logprob, no_speech_prob, words}]}
  language_probs() -> {language code: probability}
DUBEVAL_ASR picks the backend ("faster-whisper" or "openai-whisper"); an unset or unavailable choice falls back to
whichever is installed. Both are seeded, so the same audio always gives the same transcript.
"""
import functools
import os
import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
SEED = 0                          # fixed seed for the fallback sampling: same audio → same transcript
FASTER, OPENAI = "faster-whisper", "openai-whisper"

_models: dict = {}
_lock = threading.Lock()


def _installed(name: str) -> bool:
    """Whether a backend's package can be imported."""
    try:
        __import__("faster_whisper" if name == FASTER else "whisper")
        return True
    except ImportError:
        return False


def backend() -> str:
    """The recognizer in use: DUBEVAL_ASR when it is installed, else faster-whisper, else openai-whisper."""
    wanted = (os.getenv("DUBEVAL_ASR") or FASTER).strip().lower()
    for name in ([wanted] if wanted in (FASTER, OPENAI) else []) + [FASTER, OPENAI]:
        if _installed(name):
            return name
    raise RuntimeError("No speech recognizer is installed. Install faster-whisper (pip install faster-whisper).")


def languages() -> set[str]:
    """The language codes the recognizer knows (Whisper's list; both backends share it)."""
    if backend() == FASTER:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        return set(_LANGUAGE_CODES)
    from whisper.tokenizer import LANGUAGES
    return set(LANGUAGES)


def language_names() -> dict[str, str]:
    """Whisper's English names for its language codes ("ko" -> "korean"), kept in dubeval/languages.py."""
    from dubeval.languages import LANGUAGES
    return dict(LANGUAGES)


def cuda_pack_dir() -> Path:
    """Where the desktop app's GPU pack keeps NVIDIA's CUDA libraries (DUBEVAL_CUDA_DIR overrides)."""
    return Path(os.getenv("DUBEVAL_CUDA_DIR") or Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval"))
                / "cuda")


def _add_cuda_dll_dirs() -> None:
    """On Windows, lets faster-whisper find NVIDIA's CUDA libraries (cuBLAS, cuDNN); CTranslate2 doesn't look for them
    by itself. Searched in order: the GPU pack (no PyTorch needed), NVIDIA's pip packages, then PyTorch's copy."""
    if os.name != "nt" or getattr(_add_cuda_dll_dirs, "done", False):
        return
    _add_cuda_dll_dirs.done = True
    import importlib.util
    dirs = [cuda_pack_dir()]
    for package, sub in (("nvidia", ["cublas/bin", "cudnn/bin", "cuda_runtime/bin"]), ("torch", ["lib"])):
        spec = importlib.util.find_spec(package)
        for base in (spec.submodule_search_locations or []) if spec else []:
            dirs += [Path(base) / s for s in sub]
    for d in dirs:
        if d.is_dir():
            os.add_dll_directory(str(d))
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def _device() -> tuple[str, str]:
    """(device, compute type) for faster-whisper: the GPU in half precision when there is one, else 8-bit CPU."""
    forced = (os.getenv("DUBEVAL_DEVICE") or "").strip().lower()
    if forced == "cpu":
        return "cpu", "int8"
    return _gpu_check()


@functools.lru_cache(maxsize=1)
def _gpu_check() -> tuple[str, str]:
    """Looks for a usable GPU once per process (the first look loads the CUDA libraries, which takes seconds)."""
    _add_cuda_dll_dirs()
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception as e:                       # a broken CUDA install must never stop an evaluation
        log.info("No usable GPU for speech recognition (%s); using the CPU", e)
    return "cpu", "int8"


def _local_model(name: str) -> Optional[str]:
    """The folder of a faster-whisper model already on this computer: shipped with the desktop app, or installed
    from its Downloads page ("faster-whisper-large-v3-turbo" in the models folder); None means download by name."""
    from dubeval.paths import BUNDLED_MODELS
    downloads = Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval"))
    for root in (BUNDLED_MODELS, downloads):
        folder = root / f"faster-whisper-{name}" if root else None
        if folder and (folder / "model.bin").is_file():
            return str(folder)
    return None


AUTO = "auto"
LARGE = "large-v3-turbo"          # the large_model download (dubeval/packs.py)


def default_model() -> str:
    """What "auto" means on this computer: large-v3-turbo when it is downloaded and a GPU runs it (fewer errors on
    natural speech at about the same speed; benchmark of 2026-10-26), else base, which is fast enough on any CPU."""
    return pick_default(backend(), bool(_local_model(LARGE)), _device()[0])


def pick_default(kind: str, large_downloaded: bool, device: str) -> str:
    """The rule behind default_model, from what this computer has."""
    return LARGE if kind == FASTER and large_downloaded and device == "cuda" else "base"


def resolve(name: str) -> str:
    """A model name with "auto" replaced by this computer's default."""
    return default_model() if (name or AUTO) == AUTO else name


def load_model(name: str):
    """Loads and caches a recognizer model by name ("base", "small", "large-v3-turbo", or "auto")."""
    name = resolve(name)
    kind = backend()
    with _lock:
        key = (kind, name)
        if key not in _models:
            log.info("Loading %s model %r", kind, name)
            if kind == FASTER:
                from faster_whisper import WhisperModel
                device, compute = _device()
                source = _local_model(name) or name
                try:
                    model = WhisperModel(source, device=device, compute_type=compute)
                    if device != "cpu":
                        # CUDA libraries load on first use, not at creation: run once now so a missing or
                        # incompatible library falls back to the CPU here instead of failing mid-evaluation.
                        model.detect_language(audio=np.zeros(SAMPLE_RATE, dtype=np.float32))
                    _models[key] = model
                except Exception as e:           # e.g. a GPU the CUDA runtime can't drive: fall back to the CPU
                    if device == "cpu":
                        raise
                    log.warning("Speech recognition on the GPU failed (%s); using the CPU", e)
                    _models[key] = WhisperModel(source, device="cpu", compute_type="int8")
            else:
                import whisper
                _models[key] = whisper.load_model(name)
        return _models[key]


def unload() -> None:
    """Frees the loaded recognizer models (and their GPU memory), e.g. before a local judge needs the GPU."""
    with _lock:
        _models.clear()
    _free_gpu()


def _free_gpu() -> None:
    """Returns cached GPU memory to the driver, when PyTorch is in use."""
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def model_id(name: str) -> str:
    """The backend, model and (for faster-whisper) where it runs, for cache keys: "faster-whisper:base:cuda".
    GPU (float16) and CPU (int8) transcripts differ slightly, so their cached results must never mix."""
    name = resolve(name)
    kind = backend()
    if kind != FASTER:
        return f"{kind}:{name}"
    model = _models.get((kind, name))
    device = getattr(getattr(model, "model", None), "device", None) or _device()[0]
    return f"{kind}:{name}:{device}"


def transcribe(y: np.ndarray, model, language: Optional[str] = None, check=None) -> dict:
    """Transcribes a 16 kHz waveform, keeping segment confidence and word timings. language=None detects it.

    check, when given, is called after each recognized segment (faster-whisper), so a stopped run can end mid-track:
    it raises to stop."""
    if _is_faster(model):
        return _transcribe_faster(y, model, language, check)
    return _transcribe_openai(y, model, language)


def language_probs(y: np.ndarray, model) -> dict:
    """The probability of every language, from the first 30 s of y."""
    audio = y[: 30 * SAMPLE_RATE].astype(np.float32)
    if _is_faster(model):
        _, _, probs = model.detect_language(audio=audio)
        return {code: float(p) for code, p in probs}
    import whisper
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    return probs


def _is_faster(model) -> bool:
    """Whether model is a faster-whisper model."""
    return type(model).__module__.startswith("faster_whisper")


def _segment(start, end, text, avg_logprob, no_speech_prob, words) -> dict:
    """One segment in DubEval's shape."""
    return {"start": round(float(start), 2), "end": round(float(end), 2), "text": (text or "").strip(),
            "avg_logprob": round(float(avg_logprob or 0.0), 3), "no_speech_prob": round(float(no_speech_prob or 0.0), 3),
            "words": [[round(float(ws), 2), round(float(we), 2)] for ws, we in words]}


def _transcribe_faster(y: np.ndarray, model, language: Optional[str], check=None) -> dict:
    """faster-whisper, seeded so its temperature fallback is repeatable. Its segments come one at a time, so check
    runs between them."""
    import ctranslate2
    ctranslate2.set_random_seed(SEED)
    segments, info = model.transcribe(y.astype(np.float32), language=language, word_timestamps=True)
    out = []
    for s in segments:
        if check:
            check()
        out.append(_segment(s.start, s.end, s.text, s.avg_logprob, s.no_speech_prob,
                            [(w.start, w.end) for w in (s.words or [])]))
    return {"text": " ".join(s["text"] for s in out).strip(), "language": info.language or language, "segments": out}


def _transcribe_openai(y: np.ndarray, model, language: Optional[str]) -> dict:
    """openai-whisper, seeded inside the call without touching the caller's random stream."""
    import torch
    with torch.random.fork_rng():
        torch.manual_seed(SEED)
        result = model.transcribe(y, language=language, fp16=False, word_timestamps=True)
    out = [_segment(s["start"], s["end"], s.get("text", ""), s.get("avg_logprob"), s.get("no_speech_prob"),
                    [(w["start"], w["end"]) for w in s.get("words", [])]) for s in result.get("segments", [])]
    return {"text": result.get("text", "").strip(), "language": result.get("language", language), "segments": out}
