"""Voice similarity: does the dub voice sound like the original speaker, line by line?

A speaker-embedding model (WeSpeaker ResNet34-LM, trained on VoxCeleb2's 5,994 speakers, ONNX) turns a stretch of
speech into a voice fingerprint; the cosine similarity of two fingerprints says how alike two voices are (same
voice ~0.8, different voices ~0.1). Each original line is compared with the dub at the same moment, because Perso
keeps the timing: that follows every character in a multi-speaker video without speaker detection.

Background music blurs the fingerprints (tested on a real film: even two lines of the same actor scored < 0.45), so
a line counts only where the original's background is clean (DNSMOS background score, dubeval/voice_quality.py).

The model (26.5 MB) is downloaded once to ~/.cache/dubeval/, pinned to a Hugging Face commit and checked by
SHA-256. The Kaldi filterbank features it expects are computed here with numpy (no torchaudio).
"""
import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np

log = logging.getLogger(__name__)

MODEL_NAME = "wespeaker_voxceleb_resnet34_LM.onnx"
MODEL_URL = ("https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/"
             "f0c48c298fd835726c27956a5d617bad7115627e/voxceleb_resnet34_LM.onnx")
MODEL_SHA256 = "7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068"
CACHE_DIR = Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval"))
SAMPLE_RATE = 16000
MIN_LINE_SEC = 2.0                   # shorter lines give unreliable fingerprints
CLEAN_BACKGROUND = 3.0               # DNSMOS background score of the original line needed to compare voices
MAX_LINES = 80                       # longest lines kept on long videos

_session = None
_lock = threading.Lock()


class ModelUnavailable(RuntimeError):
    """The speaker model couldn't be downloaded or verified."""


def model_path(download: Callable[[str, Path], None] = None) -> Path:
    """The verified local model file: the one shipped with the app, else the downloaded one (fetched on first use)."""
    from dubeval.paths import BUNDLED_MODELS
    if BUNDLED_MODELS and (BUNDLED_MODELS / MODEL_NAME).is_file():
        return BUNDLED_MODELS / MODEL_NAME                 # checked when the app was built (tools/build_desktop.py)
    target = CACHE_DIR / MODEL_NAME
    if target.exists() and _sha256(target) == MODEL_SHA256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    try:
        (download or _download)(MODEL_URL, tmp)
    except Exception as e:  # network or HTTP error: voice similarity becomes "not measured"
        raise ModelUnavailable(f"could not download the speaker model: {e}") from e
    if _sha256(tmp) != MODEL_SHA256:
        tmp.unlink(missing_ok=True)
        raise ModelUnavailable("the downloaded speaker model failed its checksum")
    os.replace(tmp, target)
    return target


def _download(url: str, out: Path) -> None:
    """Streams url to out."""
    import requests
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(out, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)


def _sha256(path: Path) -> str:
    """SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _model():
    """The ONNX session, loaded once."""
    global _session
    with _lock:
        if _session is None:
            from dubeval.ort_session import cpu_session
            _session = cpu_session(model_path())
        return _session


# ---------------- Kaldi filterbank (torchaudio.compliance.kaldi.fbank defaults) ----------------
def _mel(f):
    """Kaldi's mel scale."""
    return 1127.0 * np.log(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def mel_banks(num_bins: int, n_fft: int, sr: int, low: float = 20.0) -> np.ndarray:
    """Triangular mel filters, (num_bins, n_fft // 2 + 1), as Kaldi builds them (Nyquist bin unused)."""
    mel_low, mel_high = _mel(low), _mel(sr / 2)
    delta = (mel_high - mel_low) / (num_bins + 1)
    b = np.arange(num_bins)[:, None]
    left, center, right = mel_low + b * delta, mel_low + (b + 1) * delta, mel_low + (b + 2) * delta
    m = _mel(sr / n_fft * np.arange(n_fft // 2))[None, :]
    banks = np.maximum(0.0, np.minimum((m - left) / (center - left), (right - m) / (right - center)))
    return np.pad(banks, ((0, 0), (0, 1)))


def fbank(wave: np.ndarray, sr: int = SAMPLE_RATE, num_mel_bins: int = 80) -> np.ndarray:
    """80-band log-mel filterbank, 25 ms frames every 10 ms: DC removal, pre-emphasis 0.97, Povey window, power
    spectrum (on the 16-bit sample scale), as WeSpeaker computes it. (frames, 80) float32."""
    wave = np.asarray(wave, dtype=np.float64) * 32768.0
    win, hop = int(sr * 0.025), int(sr * 0.010)
    if len(wave) < win:
        return np.zeros((0, num_mel_bins), dtype=np.float32)
    n = 1 + (len(wave) - win) // hop
    frames = wave[np.arange(win)[None, :] + hop * np.arange(n)[:, None]]
    frames = frames - frames.mean(axis=1, keepdims=True)
    frames = np.concatenate([frames[:, :1] * (1 - 0.97), frames[:, 1:] - 0.97 * frames[:, :-1]], axis=1)
    frames = frames * (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(win) / (win - 1))) ** 0.85
    n_fft = 1 << int(np.ceil(np.log2(win)))
    power = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2
    return np.log(np.maximum(power @ mel_banks(num_mel_bins, n_fft, sr).T, np.finfo(np.float32).eps)).astype(np.float32)


def _feats(wave: np.ndarray) -> np.ndarray:
    """The model's input for one stretch: its filterbank with the per-utterance mean removed."""
    feats = fbank(wave)
    return feats - feats.mean(axis=0)


def embed(wave: np.ndarray, session=None) -> np.ndarray:
    """The unit-length voice fingerprint (256 numbers) of a stretch of 16 kHz speech."""
    e = (session or _model()).run(None, {"feats": _feats(wave)[None]})[0][0]
    return e / (np.linalg.norm(e) + 1e-9)


def similarity(a: np.ndarray, b: np.ndarray, session=None) -> float:
    """Cosine similarity of two equally long stretches' voices, both run through the model at once (same scores as
    embedding each alone, ~20% faster)."""
    if len(a) != len(b):
        return float(embed(a, session) @ embed(b, session))
    e = (session or _model()).run(None, {"feats": np.stack([_feats(a), _feats(b)])})[0]
    e = e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-9)
    return float(e[0] @ e[1])


def voice_similarity(y_orig: np.ndarray, y_dub: np.ndarray, orig_segments: list[dict],
                     background: Callable[[np.ndarray], float], session=None) -> dict:
    """Similarity of original and dub voices per original line (>= 2 s), where the original's background is clean.

    background(audio) returns the DNSMOS background score of a stretch of the original. Returns
    {measured, reason_key, median, lines[{start, end, similarity}], skipped_noisy, model}.
    """
    lines = sorted((s for s in orig_segments if s["end"] - s["start"] >= MIN_LINE_SEC),
                   key=lambda s: s["start"] - s["end"])[:MAX_LINES]
    out, noisy = [], 0
    for s in sorted(lines, key=lambda s: s["start"]):
        a, b = int(s["start"] * SAMPLE_RATE), int(s["end"] * SAMPLE_RATE)
        orig, dub = y_orig[a:b], y_dub[a:b]
        if len(dub) < MIN_LINE_SEC * SAMPLE_RATE * 0.9 or np.abs(dub).max(initial=0) < 1e-4:
            continue
        if background(orig) < CLEAN_BACKGROUND:
            noisy += 1
            continue
        out.append({"start": round(float(s["start"]), 2), "end": round(float(s["end"]), 2),
                    "similarity": round(similarity(orig, dub, session), 3)})
    if len(out) < 2:
        return {**not_measured("r.vs.noisy" if noisy else "r.vs.few_lines"), "skipped_noisy": noisy}
    return {"measured": True, "reason_key": None, "median": round(float(np.median([l["similarity"] for l in out])), 3),
            "lines": out, "skipped_noisy": noisy, "model": "WeSpeaker ResNet34-LM"}


def not_measured(reason_key: str) -> dict:
    """The result when voice similarity wasn't measured."""
    return {"measured": False, "reason_key": reason_key, "median": None, "lines": [], "skipped_noisy": 0}
