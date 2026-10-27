"""Voice quality: how clean and undistorted the dub's voice sounds, compared with the original at the same moments.

Uses DNSMOS P.835 (Microsoft, dubeval/models/dnsmos_sig_bak_ovr.onnx), a model trained on real, noisy recordings that
rates audio the way listeners do on three 1-5 scales: SIG (the speech signal), BAK (background and noise) and OVRL
(overall). Each window where both tracks speak is scored on both, at the same moment: a dub keeps the original's music
and effects, so a lower dub score points at the dub's own sound. Both SIG and OVRL are kept because they catch
different damage (tested on real dubs: a robotic, quantised voice drops SIG ~0.9 but OVRL ~0.4; clipping distortion
drops OVRL ~0.7 but SIG ~0.25, since the model books it under background; clean dubs never dropped more than 0.25).
Known blind spot: a muffled (low-passed) voice barely changes any score. Grading is in dubeval/intervals.py.

Pure apart from loading the model: arrays in, a dict out.
"""
import threading
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "models" / "dnsmos_sig_bak_ovr.onnx"
SAMPLE_RATE = 16000
WINDOW_SEC = 9.01                    # the model's input length
HOP_SEC = 2.0                        # step between windows...
MAX_WINDOWS = 120                    # ...widened on long videos so at most this many windows are scored per track
MIN_SPEECH_SEC = 3.0                 # a window counts when both tracks speak at least this long in it
# DNSMOS P.835 calibration polynomials (raw model output -> MOS), from the DNS Challenge reference code.
POLY_SIG = np.poly1d([-0.08397278, 1.22083953, 0.0052439])
POLY_BAK = np.poly1d([-0.13166888, 1.60915514, -0.39604546])
POLY_OVR = np.poly1d([-0.06766283, 1.11546468, 0.04602535])

_session = None
_lock = threading.Lock()


def _model():
    """The ONNX session, loaded once."""
    global _session
    with _lock:
        if _session is None:
            from dubeval.ort_session import cpu_session
            _session = cpu_session(MODEL_PATH)
        return _session


def score_window(audio: np.ndarray, session=None) -> tuple[float, float, float]:
    """(SIG, BAK, OVRL) on the 1-5 scale for one window of 16 kHz audio (tiled if shorter than the model input)."""
    n = int(WINDOW_SEC * SAMPLE_RATE)
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) == 0:
        audio = np.zeros(n, dtype=np.float32)
    while len(audio) < n:
        audio = np.concatenate([audio, audio])
    sig, bak, ovr = (session or _model()).run(None, {"input_1": audio[:n][None]})[0][0]
    return float(POLY_SIG(sig)), float(POLY_BAK(bak)), float(POLY_OVR(ovr))


def _spoken(speech: list[list[float]], start: float, end: float) -> float:
    """Seconds of speech inside [start, end]."""
    return sum(max(0.0, min(e, end) - max(s, start)) for s, e in speech)


def voice_quality(y_orig: np.ndarray, y_dub: np.ndarray, orig_speech: list[list[float]],
                  dub_speech: list[list[float]], session=None) -> dict:
    """Voice-quality scores of the dub and the original at the same moments, where both speak.

    Returns windows [{start, end, dub_sig, original_sig}] and their averages; measured is False (with a reason key)
    when no window has enough speech in both tracks.
    """
    duration = min(len(y_orig), len(y_dub)) / SAMPLE_RATE
    hop = max(HOP_SEC, (duration - WINDOW_SEC) / MAX_WINDOWS) if duration > WINDOW_SEC else HOP_SEC
    starts = np.arange(0.0, max(duration - WINDOW_SEC, 0.0) + 1e-9, hop) if duration > 0 else []
    windows = []
    for start in starts:
        end = min(duration, start + WINDOW_SEC)
        if _spoken(orig_speech, start, end) < MIN_SPEECH_SEC or _spoken(dub_speech, start, end) < MIN_SPEECH_SEC:
            continue
        a, b = int(start * SAMPLE_RATE), int(end * SAMPLE_RATE)
        orig, dub = score_window(y_orig[a:b], session), score_window(y_dub[a:b], session)
        windows.append({"start": round(float(start), 2), "end": round(float(end), 2),
                        "dub": round(dub[2], 2), "original": round(orig[2], 2),
                        "dub_sig": round(dub[0], 2), "original_sig": round(orig[0], 2),
                        "dub_bak": round(dub[1], 2), "original_bak": round(orig[1], 2)})
    if not windows:
        return not_measured("r.vq.no_common_speech")
    dub_score = float(np.mean([w["dub"] for w in windows]))
    orig_score = float(np.mean([w["original"] for w in windows]))
    return {"measured": True, "reason_key": None, "dub": round(dub_score, 2), "original": round(orig_score, 2),
            "difference": round(dub_score - orig_score, 2), "windows": windows, "model": "DNSMOS P.835 (OVRL)"}


def not_measured(reason_key: str) -> dict:
    """The result when voice quality wasn't measured."""
    return {"measured": False, "reason_key": reason_key, "dub": None, "original": None, "difference": None,
            "windows": []}
