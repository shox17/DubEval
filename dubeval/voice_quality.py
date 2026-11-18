"""Voice quality: how clean and undistorted the dub's voice sounds, compared with the original at the same moments.

Two models can do the scoring (scorer()). With the voice_quality download (Settings → Models) it is Audiobox Aesthetics
(Meta, 2025, CC BY 4.0): a model trained on speech, music and sound together, whose production-quality score (PQ, 1-10)
stays steady over music and falls clearly for a robotic, muffled or clipped voice (docs/validation.md: planted damage
on the test dubs). DubEval ships only its graph (models/audiobox_aesthetics.onnx, tools/build_audiobox_onnx.py); the
weights are Meta's own model.safetensors, read where the pack put it. Without the download it is DNSMOS P.835, which
needs no download but swings with music and misses most of that damage there.

DNSMOS P.835 (Microsoft, dubeval/models/dnsmos_sig_bak_ovr.onnx), a model trained on real, noisy recordings that
rates audio the way listeners do on three 1-5 scales: SIG (the speech signal), BAK (background and noise) and OVRL
(overall). Each window where both tracks speak is scored on both, at the same moment: a dub keeps the original's music
and effects, so a lower dub score points at the dub's own sound. Both SIG and OVRL are kept because they catch
different damage (tested on real dubs: a robotic, quantised voice drops SIG ~0.9 but OVRL ~0.4; clipping distortion
drops OVRL ~0.7 but SIG ~0.25, since the model books it under background; clean dubs never dropped more than 0.25).
The dub is scored at the original's volume: the model's scores move with volume alone (a copy only 3 dB quieter moved a
window by up to 1.1, against 0.5 with the volumes matched), and volume has its own checks.
Known blind spot: a muffled (low-passed) voice barely changes any score. Grading is in dubeval/intervals.py.

Pure apart from loading the model: arrays in, a dict out.
"""
import os
import threading
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "models" / "dnsmos_sig_bak_ovr.onnx"
GRAPH_PATH = Path(__file__).resolve().parent / "models" / "audiobox_aesthetics.onnx"
PACK_DIR = Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval")) / "audiobox-aesthetics"
WEIGHTS = "model.safetensors"        # Meta's file, as downloaded: the graph's weights are read out of it
AXES = ("ce", "cu", "pc", "pq")      # the graph's four scores, in order: content enjoyment, content usefulness,
#                                      production complexity, production quality (the one that grades)
SAMPLE_RATE = 16000
WINDOW_SEC = 9.01                    # the model's input length
HOP_SEC = 2.0                        # step between windows...
MAX_WINDOWS = 120                    # ...widened on long videos so at most this many windows are scored per track
MIN_SPEECH_SEC = 3.0                 # a window counts when both tracks speak at least this long in it
SILENT_RMS = 1e-5                    # a window this quiet has no volume to match
# DNSMOS P.835 calibration polynomials (raw model output -> MOS), from the DNS Challenge reference code.
POLY_SIG = np.poly1d([-0.08397278, 1.22083953, 0.0052439])
POLY_BAK = np.poly1d([-0.13166888, 1.60915514, -0.39604546])
POLY_OVR = np.poly1d([-0.06766283, 1.11546468, 0.04602535])

_session = None
_aes_session = None
_lock = threading.Lock()


def ready() -> bool:
    """Whether the voice_quality pack is installed (Meta's weights are complete) and the graph is bundled."""
    from dubeval import packs
    return packs.state("voice_quality") == "installed" and GRAPH_PATH.is_file()


def scorer() -> str:
    """Which model scores voice quality now: "audiobox" with its download, else "dnsmos"."""
    return "audiobox" if ready() else "dnsmos"


def _aes_model():
    """The Audiobox Aesthetics session, loaded once (its weights are read from the pack's file)."""
    global _aes_session
    with _lock:
        if _aes_session is None:
            from dubeval.ort_session import cpu_session
            _aes_session = cpu_session(GRAPH_PATH, PACK_DIR)
        return _aes_session


def unload() -> None:
    """Forgets the loaded Audiobox model (the pack was removed or replaced; it keeps the weights file open)."""
    global _aes_session
    with _lock:
        _aes_session = None


def _window(audio: np.ndarray) -> np.ndarray:
    """One stretch at the models' input length (tiled if shorter)."""
    n = int(WINDOW_SEC * SAMPLE_RATE)
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) == 0:
        audio = np.zeros(n, dtype=np.float32)
    while len(audio) < n:
        audio = np.concatenate([audio, audio])
    return audio[:n]


def score_production(stretches: list, session=None) -> list[dict]:
    """Audiobox Aesthetics scores of 16 kHz stretches, each on its own: [{ce, cu, pc, pq}] on 1-10 scales."""
    got = (session or _aes_model()).run(None, {"wav": np.stack([_window(a) for a in stretches])})[0]
    return [{axis: float(v) for axis, v in zip(AXES, row)} for row in got]


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
    sig, bak, ovr = (session or _model()).run(None, {"input_1": _window(audio)[None]})[0][0]
    return float(POLY_SIG(sig)), float(POLY_BAK(bak)), float(POLY_OVR(ovr))


def _at_volume_of(audio: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """audio at reference's volume, or as near as it gets without clipping (that would damage the voice being scored)."""
    level, target = float(np.sqrt(np.mean(np.square(audio)))), float(np.sqrt(np.mean(np.square(reference))))
    if level < SILENT_RMS or target < SILENT_RMS:
        return audio
    return audio * min(target / level, 1.0 / float(np.max(np.abs(audio))))


def _spoken(speech: list[list[float]], start: float, end: float) -> float:
    """Seconds of speech inside [start, end]."""
    return sum(max(0.0, min(e, end) - max(s, start)) for s, e in speech)


def voice_quality(y_orig: np.ndarray, y_dub: np.ndarray, orig_speech: list[list[float]],
                  dub_speech: list[list[float]], session=None, scorer: str = None, dnsmos_session=None) -> dict:
    """Voice-quality scores of the dub and the original at the same moments and volume, where both speak.

    scorer: "audiobox" or "dnsmos" (default: scorer(), by what is installed); session: that model's session, for
    tests. Returns {scorer, scale (the top of the 1-N scale), dub, original, difference, windows} with, per window,
    {start, end, dub, original} and the model's second score: dub_ce / original_ce (Audiobox: dub and original are
    its production quality) or dub_sig / original_sig (DNSMOS: dub and original are its overall score). Every window
    also has dub_bak / original_bak, DNSMOS's background score, whichever model grades: the report tells a replaced
    background by it (report.sure_of). measured is False (with a reason key) when no window has enough speech in both
    tracks.
    """
    by = scorer or globals()["scorer"]()
    duration = min(len(y_orig), len(y_dub)) / SAMPLE_RATE
    hop = max(HOP_SEC, (duration - WINDOW_SEC) / MAX_WINDOWS) if duration > WINDOW_SEC else HOP_SEC
    starts = np.arange(0.0, max(duration - WINDOW_SEC, 0.0) + 1e-9, hop) if duration > 0 else []
    windows = []
    for start in starts:
        end = min(duration, start + WINDOW_SEC)
        if _spoken(orig_speech, start, end) < MIN_SPEECH_SEC or _spoken(dub_speech, start, end) < MIN_SPEECH_SEC:
            continue
        a, b = int(start * SAMPLE_RATE), int(end * SAMPLE_RATE)
        if by == "audiobox":
            pair = [y_orig[a:b], _at_volume_of(y_dub[a:b], y_orig[a:b])]
            o, d = score_production(pair, session)
            windows.append({"start": round(float(start), 2), "end": round(float(end), 2),
                            "dub": round(d["pq"], 2), "original": round(o["pq"], 2),
                            "dub_ce": round(d["ce"], 2), "original_ce": round(o["ce"], 2),
                            "dub_bak": round(score_window(pair[1], dnsmos_session)[1], 2),
                            "original_bak": round(score_window(pair[0], dnsmos_session)[1], 2)})
            continue
        orig, dub = score_window(y_orig[a:b], session), score_window(_at_volume_of(y_dub[a:b], y_orig[a:b]), session)
        windows.append({"start": round(float(start), 2), "end": round(float(end), 2),
                        "dub": round(dub[2], 2), "original": round(orig[2], 2),
                        "dub_sig": round(dub[0], 2), "original_sig": round(orig[0], 2),
                        "dub_bak": round(dub[1], 2), "original_bak": round(orig[1], 2)})
    if not windows:
        return not_measured("r.vq.no_common_speech")
    dub_score = float(np.mean([w["dub"] for w in windows]))
    orig_score = float(np.mean([w["original"] for w in windows]))
    return {"measured": True, "reason_key": None, "dub": round(dub_score, 2), "original": round(orig_score, 2),
            "difference": round(dub_score - orig_score, 2), "windows": windows, "scorer": by,
            "scale": 10 if by == "audiobox" else 5,
            "model": "Audiobox Aesthetics (production quality)" if by == "audiobox" else "DNSMOS P.835 (OVRL)"}


def not_measured(reason_key: str) -> dict:
    """The result when voice quality wasn't measured."""
    return {"measured": False, "reason_key": reason_key, "dub": None, "original": None, "difference": None,
            "windows": []}
