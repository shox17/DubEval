"""All quality measurements for a dub: audio, speech recognition (Whisper) and lip movement (MediaPipe).

Pure functions: they take files or waveforms and return dicts. Nothing here writes files or talks to Perso.
"""
import os
import re
import logging
import subprocess
import tempfile
import threading
import unicodedata
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import librosa
import jiwer
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import imageio_ffmpeg

from dubeval import asr
from dubeval.inputs import LOCAL_INPUT

log = logging.getLogger(__name__)

SRC_DIR = Path(__file__).resolve().parent
FACE_MODEL_PATH = str(SRC_DIR / "models" / "face_landmarker.task")
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE_RATE = 16000

# base: 145 MB download and fast on CPU; on the sample it gave the same verdict and scores as small (484 MB).
# "auto": large-v3-turbo on a GPU when it is downloaded, else base (asr.default_model).
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "auto")

# Scripts written without spaces between words (or with coarse spacing units) are scored by CER.
CER_LANGS = {"ja", "zh", "ko", "th"}

# Perso language codes that Whisper spells differently.
WHISPER_CODE_ALIASES = {"fil": "tl", "jv": "jw"}

# Lip-sync analysis settings
LIPSYNC_SAMPLE_FPS = 15.0          # frames analysed per second of video
LIPSYNC_MAX_SECONDS = 60.0         # analysis window from the start of the clip
LIPSYNC_MAX_LAG_MS = 200           # diagnostic lag search range (+/-); never used for the headline score
LIPSYNC_MIN_FACE_COVERAGE = 0.5    # below this the result is reported as invalid
LIPSYNC_MIN_FRAMES = 20

# Bump when result keys are renamed or removed.
SCHEMA_VERSION = 6

# Speech timing and clarity settings
CLIP_LEVEL = 0.999                 # |sample| at or above this counts as clipped
SPEECH_GRID_SEC = 0.05             # resolution of the speech-timing comparison
SPEECH_MERGE_GAP_SEC = 0.3         # word gaps shorter than this are one stretch of speech
MISMATCH_MIN_SEC = 0.5             # only-one-track-speaks stretches shorter than this are ignored
MAX_MISMATCHES = 50                # longest mismatches kept (every one becomes a problem interval)
WHISPER_LOGPROB_OK = -1.0          # Whisper's own thresholds for trusting a segment
WHISPER_NO_SPEECH_OK = 0.6
VOICED_SHARE_OK = 0.5              # a recognized line is kept only if the voice detector hears speech in this share of it...
GAP_MIN_SEC = 1.0                  # detected speech this long that the transcript barely covers...
GAP_COVERED_MAX = 0.3              # ...(less than this share) is recognized again on its own (fill_gaps)...
GAP_MERGE_SEC = 0.5                # ...detected speech closer than this counts as one stretch...
GAP_PAD_SEC = 0.3                  # ...and is recognized with this much sound either side
GAP_DUPLICATE_SHARE = 0.5          # a re-recognized line this much inside a line already heard is that line again
PARTNER_SHARE_OK = 0.3            # ...or the other track's kept lines cover this share of it (a shout the detector
                                   # half missed; validation: dropped on one side only, it read as a line added or left out)...
PARTNER_VOICED_MIN = 0.2           # ...as long as the detector hears some voice in it (a real shout over music: 0.36;
                                   # words read into music: 0.0; keeping those too doubled the validation false alarms)
CACHE_VERSION = 5                  # bump when cached results would change (2: seeded Whisper, 3: voice quality,
                                   # 4: recognizer backend in the keys, 5: recognizer device in the keys)
CLIP_MERGE_GAP_SEC = 0.5           # clipped samples closer than this form one distortion interval
MAX_CLIP_INTERVALS = 50
LANG_WINDOW_SEC = 10.0             # the dub's language is checked per window of this length...
LANG_MAX_WINDOWS = 120             # ...widened for long videos so at most this many windows are checked...
LANG_OVERLAP = 2                   # ...each starting 1/this of a window after the last: a part in the wrong language
                                   # that straddles two windows still fills one (validation: 8 s split 5 + 3 was missed)
LANG_MIN_SPEECH_SEC = 3.0          # windows with less speech than this are skipped
SEGMENT_MIN_SHARE = 0.3            # segments overlapping by this share of the shorter one are matched
LINE_MIN_SEC = 1.0                 # lines shorter than this on the original side aren't graded on length
LINE_OVERRUN_SEC = 0.5             # a dub line ending this much past the next original line's start runs into it

def get_whisper_model(model_name: str = DEFAULT_WHISPER_MODEL):
    """Loads and caches a speech-recognition model (faster-whisper by default; see dubeval/asr.py)."""
    return asr.load_model(model_name)


def extract_audio(video_path: str, output_audio_path: str, sample_rate: int = SAMPLE_RATE) -> str:
    """Extracts 16kHz mono PCM WAV audio using the bundled ffmpeg binary."""
    Path(output_audio_path).resolve().parent.mkdir(parents=True, exist_ok=True)
    command = [
        FFMPEG_EXE, "-nostdin", "-y",
        *LOCAL_INPUT, "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        output_audio_path
    ]
    proc = subprocess.run(command, capture_output=True)
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace").strip().splitlines()[-3:]
        raise RuntimeError(f"ffmpeg could not extract audio from {video_path}: {' | '.join(tail)}")
    return output_audio_path


def load_both(original_video_path: str, dubbed_video_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Both videos' sound as 16 kHz mono waveforms: extracted at the same time (two ffmpeg processes), then loaded
    here, one after the other.

    Only ffmpeg runs in the worker threads. librosa loads its parts lazily on first use, and two threads doing that
    first use together deadlocked on Python's import locks (both importing SciPy) and hung the evaluation forever."""
    from concurrent.futures import ThreadPoolExecutor
    with tempfile.TemporaryDirectory(prefix="dubeval_") as tmp:
        wavs = [(path, str(Path(tmp) / name)) for path, name in ((original_video_path, "orig.wav"),
                                                                  (dubbed_video_path, "dubbed.wav"))]
        with ThreadPoolExecutor(max_workers=2) as pool:
            extracted = [pool.submit(extract_audio, path, wav) for path, wav in wavs]
            paths = [job.result() for job in extracted]
        return load_audio(paths[0]), load_audio(paths[1])


def load_audio(audio_path: str) -> np.ndarray:
    """Loads a mono float32 waveform at SAMPLE_RATE."""
    y, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return y.astype(np.float32)


def analyze_acoustics(y: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Computes acoustic features: duration, mean RMS energy, volume stability, and silence ratio."""
    duration = float(len(y) / sr) if sr else 0.0

    rms_frames = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0] if len(y) else np.array([])
    mean_rms = float(np.mean(rms_frames)) if len(rms_frames) > 0 else 0.0
    std_rms = float(np.std(rms_frames)) if len(rms_frames) > 0 else 0.0

    stability = max(0.0, min(100.0, (1.0 - (std_rms / mean_rms)) * 100.0)) if mean_rms > 1e-6 else 0.0

    if len(y) and np.max(np.abs(y)) > 0:
        non_silent_intervals = librosa.effects.split(y, top_db=20)
        non_silent_duration = sum((end - start) / sr for start, end in non_silent_intervals)
    else:
        non_silent_duration = 0.0
    silence_ratio = float((duration - non_silent_duration) / duration) if duration > 0 else 0.0

    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    return {
        "duration_sec": round(duration, 2),
        "mean_rms_energy": round(mean_rms, 4),
        "rms_std": round(std_rms, 4),
        "volume_stability_pct": round(stability, 1),
        "silence_ratio_pct": round(silence_ratio * 100, 2),
        "peak_dbfs": round(20 * float(np.log10(peak)), 1) if peak > 0 else None,
        # Samples at or near full scale: audible distortion when more than a handful.
        "clipping_pct": round(float(np.mean(np.abs(y) >= CLIP_LEVEL)) * 100, 3) if len(y) else 0.0,
    }


def normalize_text(text: str) -> str:
    """Unicode-normalizes, lowercases, strips punctuation/symbols and collapses whitespace."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = "".join(" " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def score_transcript(ground_truth: str, hypothesis: str, lang: str) -> dict:
    """Scores a transcript against ground truth with WER and CER; picks the primary metric by language."""
    ref = normalize_text(ground_truth)
    hyp = normalize_text(hypothesis)
    if not ref:
        return {"wer": None, "cer": None, "primary_metric": None, "error_rate": None, "accuracy_pct": None}

    wer = float(jiwer.wer(ref, hyp)) if hyp else 1.0
    # CER ignores word boundaries, so spacing differences don't count as errors.
    cer = float(jiwer.cer(ref.replace(" ", ""), hyp.replace(" ", ""))) if hyp else 1.0
    primary = "cer" if base_lang(lang) in CER_LANGS else "wer"
    error_rate = cer if primary == "cer" else wer
    return {
        "wer": round(wer, 3),
        "cer": round(cer, 3),
        "primary_metric": primary,
        "error_rate": round(error_rate, 3),
        "accuracy_pct": round(max(0.0, 1.0 - error_rate) * 100.0, 1)
    }


def subtitle_agreement(segments: list[dict], cues: Optional[list[dict]]) -> Optional[float]:
    """How closely what was heard matches a subtitle file: 1 − the character error rate of the transcript against the
    subtitles' text (case, punctuation and spacing ignored), from 0 to 1; None without both texts."""
    def norm(text: str) -> str:
        text = unicodedata.normalize("NFKC", text).lower()
        return re.sub(r"\s+", " ", re.sub(r"[\W_]+", " ", text)).strip()
    heard = norm(" ".join(s.get("text") or "" for s in segments or []))
    script = norm(" ".join(c.get("text") or "" for c in cues or []))
    if not heard or not script:
        return None
    return round(max(0.0, 1.0 - float(jiwer.cer(script, heard))), 3)


def base_lang(code: Optional[str]) -> str:
    """The base language of a code: "es-MX" -> "es", "zh_CN" -> "zh", None -> ""."""
    return (code or "").replace("_", "-").split("-")[0].strip().lower()


def whisper_language(code: Optional[str]) -> Optional[str]:
    """Whisper's code for a Perso language code, or None when Whisper has no model for it."""
    code = base_lang(code)
    code = WHISPER_CODE_ALIASES.get(code, code)
    return code if code in asr.languages() else None


def transcribe(y: np.ndarray, whisper_model, language: Optional[str] = None, check=None) -> dict:
    """Transcribes a 16kHz waveform, keeping segment confidence and word timings (see dubeval/asr.py).

    language=None lets the recognizer detect it. Its fallback sampling is seeded, so the same audio always gives the
    same transcript (and scores). check (see run_full_evaluation) runs between recognized segments.
    """
    return asr.transcribe(y, whisper_model, language, check=check)


def _language_probs(y: np.ndarray, whisper_model) -> dict:
    """The recognizer's probability for every language, from the first 30 s of y."""
    return asr.language_probs(y, whisper_model)


def detect_language(y: np.ndarray, whisper_model) -> tuple[Optional[str], Optional[float]]:
    """Whisper's guess of the spoken language in the first 30 s, with its probability."""
    if not len(y):
        return None, None
    probs = _language_probs(y, whisper_model)
    code = max(probs, key=probs.get)
    return code, round(float(probs[code]), 3)


def language_windows(y: np.ndarray, whisper_model, speech: list[list[float]], expected: Optional[str],
                     sr: int = SAMPLE_RATE, check=None) -> list[dict]:
    """The dub's language window by window, so a part left in the original language (or another one) is found.

    Each window with enough speech gets Whisper's top language, its probability and the expected language's
    probability. Windows overlap by half (LANG_OVERLAP) and widen on long videos so at most LANG_MAX_WINDOWS are
    checked. speech should include the
    original's speech times: a dub in the wrong language transcribes badly, so its own speech times are unreliable.
    """
    duration = len(y) / sr if sr else 0.0
    if not expected or duration <= 0:
        return []
    merged: list[list[float]] = []
    for s, e in sorted([s, e] for s, e in speech if e > s):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    speech = merged
    width = max(LANG_WINDOW_SEC, LANG_OVERLAP * duration / LANG_MAX_WINDOWS)
    windows, start, end = [], 0.0, 0.0
    while end < duration:
        if check:
            check()
        end = min(duration, start + width)
        spoken = sum(max(0.0, min(e, end) - max(s, start)) for s, e in speech)
        if spoken >= min(LANG_MIN_SPEECH_SEC, (end - start) * 0.5):
            probs = _language_probs(y[int(start * sr):int(end * sr)], whisper_model)
            top = max(probs, key=probs.get)
            windows.append({"start": round(start, 2), "end": round(end, 2), "language": top,
                            "probability": round(float(probs[top]), 3),
                            "expected_probability": round(float(probs.get(expected, 0.0)), 3)})
        start += width / LANG_OVERLAP
    return windows


def match_segments(original: list[dict], dubbed: list[dict], min_share: float = SEGMENT_MIN_SHARE) -> dict:
    """Original and dub segments matched by time: segments overlapping by at least min_share of the shorter one are
    linked, and linked segments form one group (a dub often splits or merges the original's sentences).

    Returns {"groups": [{"original": [i...], "dub": [j...], "start", "end", "original_sec", "dub_sec"}],
    "unmatched_original": [i...], "unmatched_dub": [j...]}; indexes refer to the segment lists, times are seconds.
    """
    orig = [(i, s) for i, s in enumerate(original) if _is_real_speech(s) and s["end"] > s["start"]]
    dub = [(j, s) for j, s in enumerate(dubbed) if _is_real_speech(s) and s["end"] > s["start"]]
    parent: dict = {}

    def find(x):
        """The group a segment belongs to."""
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, a in orig:
        find(("o", i))
        for j, b in dub:
            find(("d", j))
            shared = min(a["end"], b["end"]) - max(a["start"], b["start"])
            if shared > 0 and shared >= min_share * min(a["end"] - a["start"], b["end"] - b["start"]):
                parent[find(("o", i))] = find(("d", j))
    groups: dict = {}
    for i, _ in orig:
        groups.setdefault(find(("o", i)), {"original": [], "dub": []})["original"].append(i)
    for j, _ in dub:
        groups.setdefault(find(("d", j)), {"original": [], "dub": []})["dub"].append(j)
    out, lonely_o, lonely_d = [], [], []
    for g in groups.values():
        if not g["dub"]:
            lonely_o += g["original"]
            continue
        if not g["original"]:
            lonely_d += g["dub"]
            continue
        segs_o, segs_d = [original[i] for i in g["original"]], [dubbed[j] for j in g["dub"]]
        (o0, o1), (d0, d1) = _spoken_span(segs_o), _spoken_span(segs_d)
        out.append({"original": sorted(g["original"]), "dub": sorted(g["dub"]),
                    "start": min(o0, d0), "end": max(o1, d1),
                    "original_start": o0, "original_end": o1, "dub_start": d0, "dub_end": d1,
                    "original_sec": round(o1 - o0, 2), "dub_sec": round(d1 - d0, 2)})
    groups = sorted(out, key=lambda g: g["start"])
    return {"groups": groups, "lines": line_timing(groups), "unmatched_original": sorted(lonely_o),
            "unmatched_dub": sorted(lonely_d)}


def _spoken_span(segs: list[dict]) -> tuple[float, float]:
    """From the first spoken word to the last (segment edges when there are no word timings)."""
    words = [w for s in segs for w in (s.get("words") or [])]
    if words:
        return round(min(w[0] for w in words), 2), round(max(w[1] for w in words), 2)
    return round(min(s["start"] for s in segs), 2), round(max(s["end"] for s in segs), 2)


def line_timing(groups: list[dict]) -> list[dict]:
    """Each matched line (original and dub segments spoken together): how long each side speaks, the difference in
    seconds and percent, how much later the dub starts, and how far the dub runs into the original's next line.

    Grading lives in report.py; lines shorter than LINE_MIN_SEC on the original side are kept but marked
    `short` (a tiny line's percentage says little).
    """
    lines = []
    for k, g in enumerate(groups):
        o, d = g["original_sec"], g["dub_sec"]
        nxt = groups[k + 1]["original_start"] if k + 1 < len(groups) else None
        overrun = round(g["dub_end"] - nxt, 2) if nxt is not None and g["dub_end"] - nxt > LINE_OVERRUN_SEC else 0.0
        lines.append({"n": k + 1, "start": g["original_start"], "end": g["original_end"],
                      "original_sec": o, "dub_sec": d, "diff_sec": round(d - o, 2),
                      "diff_pct": round((d - o) / o * 100, 1) if o > 0 else None,
                      "start_shift_sec": round(g["dub_start"] - g["original_start"], 2),
                      "overrun_sec": overrun, "short": o < LINE_MIN_SEC,
                      "original": g["original"], "dub": g["dub"]})
    return lines


def clipping_intervals(y: np.ndarray, sr: int = SAMPLE_RATE) -> list[list[float]]:
    """Where the dub's audio hits full scale: [start, end] stretches, merging clips closer than 0.5 s."""
    idx = np.flatnonzero(np.abs(y) >= CLIP_LEVEL) if len(y) else np.array([], dtype=int)
    if not len(idx):
        return []
    gap = int(CLIP_MERGE_GAP_SEC * sr)
    breaks = np.flatnonzero(np.diff(idx) > gap)
    starts, ends = np.concatenate([[idx[0]], idx[breaks + 1]]), np.concatenate([idx[breaks], [idx[-1]]])
    spans = [[round(a / sr, 2), round((b + 1) / sr, 2)] for a, b in zip(starts, ends)]
    longest = sorted(spans, key=lambda s: s[0] - s[1])[:MAX_CLIP_INTERVALS]
    return sorted(longest)


def _is_real_speech(seg: dict) -> bool:
    """False for segments Whisper itself would treat as silence (likely hallucinated over music or noise)."""
    return not (seg["no_speech_prob"] > WHISPER_NO_SPEECH_OK and seg["avg_logprob"] < WHISPER_LOGPROB_OK)


def unheard_speech(stt: dict, voiced: Optional[list[list[float]]]) -> list[list[float]]:
    """Stretches the voice detector hears speech in but the transcript doesn't cover: long audio is recognized in
    30 s chunks, and after loud music the recognizer can skip ahead past real lines."""
    if not voiced:
        return []
    merged: list[list[float]] = []
    for a, b in sorted(voiced):
        if merged and a - merged[-1][1] <= GAP_MERGE_SEC:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    covered = [[s["start"], s["end"]] for s in stt["segments"]]
    return [[a, b] for a, b in merged
            if b - a >= GAP_MIN_SEC and _share({"start": a, "end": b}, covered) < GAP_COVERED_MAX]


def fill_gaps(stt: dict, y: np.ndarray, voiced: Optional[list[list[float]]], whisper_model,
              language: Optional[str] = None, check=None, sr: int = SAMPLE_RATE) -> dict:
    """The transcript with each unheard stretch (unheard_speech) recognized again on its own and its lines added."""
    gaps = unheard_speech(stt, voiced)
    if not gaps:
        return stt
    segments = list(stt["segments"])
    heard = [[s["start"], s["end"]] for s in segments]
    for a, b in gaps:
        start = max(0.0, a - GAP_PAD_SEC)
        part = transcribe(y[int(start * sr):int((b + GAP_PAD_SEC) * sr)], whisper_model, language=language, check=check)
        for s in part["segments"]:
            new = {**s, "start": round(s["start"] + start, 2), "end": round(s["end"] + start, 2),
                   "words": [[round(ws + start, 2), round(we + start, 2)] for ws, we in s["words"]]}
            # A stretch can be partly heard already: a line mostly covered by one the transcript has is that line again.
            if s["text"] and _share(new, heard) < GAP_DUPLICATE_SHARE:
                segments.append(new)
    segments.sort(key=lambda s: s["start"])
    log.info("Recognized %d skipped stretch(es) again", len(gaps))
    return {**stt, "segments": segments, "text": " ".join(s["text"] for s in segments).strip()}


def _share(seg: dict, spans) -> float:
    """The share of a segment's time covered by [start, end] spans."""
    length = seg["end"] - seg["start"]
    heard = sum(max(0.0, min(seg["end"], b) - max(seg["start"], a)) for a, b in spans)
    return heard / length if length > 0 else 0.0


def keep_voiced(stt: dict, voiced: Optional[list[list[float]]], partner: Optional[list[dict]] = None) -> dict:
    """The transcript without lines the voice detector hears no speech in (the recognizer reading music or sound
    effects as words, which moves with every small change of the sound); as is when there's no detector.

    partner: the other track's kept lines. A line the detector misses (a shout over loud effects) is kept when the
    other track speaks at that moment: dropping it on one side only reads as speech left out or added."""
    if voiced is None:
        return stt
    spans = [[s["start"], s["end"]] for s in partner or []]

    def keep(s):
        heard = _share(s, voiced)
        return heard >= VOICED_SHARE_OK or (bool(spans) and heard >= PARTNER_VOICED_MIN
                                            and _share(s, spans) >= PARTNER_SHARE_OK)
    kept = [s for s in stt["segments"] if keep(s)]
    return {**stt, "segments": kept, "text": " ".join(s["text"] for s in kept).strip()}


def speech_intervals(segments: list[dict], merge_gap: float = SPEECH_MERGE_GAP_SEC) -> list[list[float]]:
    """Stretches of speech [start, end] from Whisper word timings, merging short gaps between words."""
    spans = []
    for seg in segments:
        if not _is_real_speech(seg):
            continue
        spans.extend(seg.get("words") or [[seg["start"], seg["end"]]])
    spans = sorted([s, e] for s, e in spans if e > s)
    merged: list[list[float]] = []
    for s, e in spans:
        if merged and s - merged[-1][1] <= merge_gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [[round(s, 2), round(e, 2)] for s, e in merged]


def speech_clarity(segments: list[dict]) -> dict:
    """Share of speech time in segments Whisper recognised confidently, plus the unclear segments."""
    real = [s for s in segments if _is_real_speech(s) and s["end"] > s["start"]]
    total = sum(s["end"] - s["start"] for s in real)
    unclear = [s for s in real if s["avg_logprob"] < WHISPER_LOGPROB_OK]
    unclear_time = sum(s["end"] - s["start"] for s in unclear)
    return {
        "confident_pct": round((1 - unclear_time / total) * 100, 1) if total > 0 else None,
        "mean_logprob": round(float(np.average([s["avg_logprob"] for s in real],
                                               weights=[s["end"] - s["start"] for s in real])), 3) if real else None,
        "segments": len(real),
        "unclear_segments": [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in unclear],
    }


def _grid(intervals: list[list[float]], n: int, step: float) -> np.ndarray:
    """Boolean speaking/not-speaking mask of n cells of step seconds."""
    mask = np.zeros(n, dtype=bool)
    for s, e in intervals:
        mask[max(0, int(s / step)):min(n, int(np.ceil(e / step)))] = True
    return mask


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) index pairs of consecutive True cells."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def timing_alignment(original: list[list[float]], dubbed: list[list[float]], duration_sec: float,
                     step: float = SPEECH_GRID_SEC) -> dict:
    """How well the dub speaks at the same moments as the original (overlap of speech stretches)."""
    empty = {"overlap_pct": None, "original_covered_pct": None, "dub_in_original_pct": None,
             "start_offset_sec": None, "end_offset_sec": None, "mismatches": []}
    if duration_sec <= 0 or not original or not dubbed:
        return empty
    n = int(np.ceil(duration_sec / step)) + 1
    o, d = _grid(original, n, step), _grid(dubbed, n, step)
    both, either = np.sum(o & d), np.sum(o | d)
    mismatches = []
    for mask, kind in ((d & ~o, "dub_only"), (o & ~d, "original_only")):
        for a, b in _runs(mask):
            if (b - a) * step >= MISMATCH_MIN_SEC:
                mismatches.append({"start": round(a * step, 2), "end": round(b * step, 2), "kind": kind})
    mismatches.sort(key=lambda m: m["end"] - m["start"], reverse=True)
    return {
        "overlap_pct": round(both / either * 100, 1) if either else None,
        "original_covered_pct": round(both / np.sum(o) * 100, 1) if np.sum(o) else None,
        "dub_in_original_pct": round(both / np.sum(d) * 100, 1) if np.sum(d) else None,
        "start_offset_sec": round(dubbed[0][0] - original[0][0], 2),
        "end_offset_sec": round(dubbed[-1][1] - original[-1][1], 2),
        "mismatches": sorted(mismatches[:MAX_MISMATCHES], key=lambda m: m["start"]),
    }


def _cv2_path(path: str) -> str:
    """A path OpenCV can open. On Windows OpenCV can't open non-ASCII paths (e.g. a Korean user name), so it
    gets a relative or 8.3 short path instead when that is plain ASCII."""
    if os.name != "nt" or path.isascii():
        return path
    try:
        rel = os.path.relpath(path)
        if rel.isascii():
            return rel
    except ValueError:                        # on another drive
        pass
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf)) and buf.value.isascii():
            return buf.value
    except (AttributeError, OSError):
        pass
    log.warning("OpenCV may not open this non-ASCII path on Windows: %s", path)
    return path


def probe_media(video_path: str) -> dict:
    """Resolution, frame rate, frame count, duration and whether an audio track exists (reads the file only)."""
    info = {"readable": False, "width": None, "height": None, "fps": None, "frames": None,
            "duration_sec": None, "has_audio": False}
    cap = cv2.VideoCapture(_cv2_path(video_path))
    try:
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            info.update(readable=frames > 0, width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), fps=round(fps, 2) if fps else None,
                        frames=frames, duration_sec=round(frames / fps, 2) if fps else None)
    finally:
        cap.release()
    # ffmpeg prints the stream list to stderr and exits non-zero without an output file; that's expected.
    proc = subprocess.run([FFMPEG_EXE, "-nostdin", "-hide_banner", *LOCAL_INPUT, "-i", video_path],
                          capture_output=True)
    info["has_audio"] = "Audio:" in proc.stderr.decode(errors="replace")
    return info


def video_integrity(original_video_path: str, dubbed_video_path: str) -> dict:
    """Compares the two files' technical properties: the dub should change the voice, not the picture."""
    o, d = probe_media(original_video_path), probe_media(dubbed_video_path)
    same_res = (o["width"], o["height"]) == (d["width"], d["height"])
    same_fps = o["fps"] is not None and d["fps"] is not None and abs(o["fps"] - d["fps"]) <= 0.1
    return {"original": o, "dubbed": d, "same_resolution": same_res, "same_fps": same_fps}


def _mouth_aspect_ratio(lm) -> float:
    """How open the mouth is: lip gap divided by mouth width, from MediaPipe face landmarks."""
    v_dist = ((lm[13].x - lm[14].x) ** 2 + (lm[13].y - lm[14].y) ** 2) ** 0.5
    h_dist = ((lm[61].x - lm[291].x) ** 2 + (lm[61].y - lm[291].y) ** 2) ** 0.5
    return float(v_dist / (h_dist + 1e-6))


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation of two series; 0.0 when either is too short or flat to correlate."""
    if len(a) < 3 or np.std(a) < 1e-9 or np.std(b) < 1e-9:
        return 0.0
    r = float(np.corrcoef(a, b)[0, 1])
    return 0.0 if np.isnan(r) else r


def _sync_quality(r: float) -> str:
    """Turns a lip-sync correlation into a label: strong, moderate, weak or none."""
    if r >= 0.4:
        return "strong"
    if r >= 0.2:
        return "moderate"
    if r >= 0.05:
        return "weak"
    return "none"


def analyze_lipsync(video_path: str, y: np.ndarray, sr: int = SAMPLE_RATE,
                    model_path: str = FACE_MODEL_PATH, max_seconds: float = LIPSYNC_MAX_SECONDS, check=None) -> dict:
    """Correlates mouth opening (MediaPipe MAR) with speech loudness (RMS).

    Experimental: the headline score is the zero-lag Pearson r. The best r over a +/-200 ms lag window is
    reported only as a diagnostic, because maximising over lags inflates pure noise to r ~ +0.1.
    """
    invalid = {
        "valid": False, "reason": "", "reason_key": None, "reason_params": {},
        "pearson_correlation": None, "best_lag_correlation": None,
        "best_lag_ms": None, "sync_quality": "n/a", "face_coverage_pct": 0.0, "frames_analyzed": 0,
        "timestamps": [], "mar_waveform": [], "rms_waveform": []
    }

    cap = cv2.VideoCapture(_cv2_path(video_path))
    if not cap.isOpened():
        return {**invalid, "reason": "video could not be opened", "reason_key": "r.lips.no_video"}
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or np.isnan(fps):
        fps = 25.0
    stride = max(1, int(round(fps / LIPSYNC_SAMPLE_FPS)))
    max_frame = int(max_seconds * fps)

    options = vision.FaceLandmarkerOptions(
        # The model is passed as bytes: MediaPipe can't open non-ASCII paths on Windows.
        base_options=mp_python.BaseOptions(model_asset_buffer=Path(model_path).read_bytes()),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1
    )
    timestamps, mar_values = [], []
    try:
        with vision.FaceLandmarker.create_from_options(options) as detector:
            idx = 0
            while idx < max_frame:
                # grab() skips decoding of frames we don't analyse; retrieve() decodes only sampled ones.
                if not cap.grab():
                    break
                if idx % stride == 0:
                    if check:
                        check()
                    ok, frame = cap.retrieve()
                    if not ok:
                        break
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    t = idx / fps
                    res = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(t * 1000))
                    timestamps.append(t)
                    mar_values.append(_mouth_aspect_ratio(res.face_landmarks[0]) if res.face_landmarks else np.nan)
                idx += 1
    finally:
        cap.release()

    n = len(mar_values)
    mar = np.array(mar_values, dtype=np.float64)
    ts = np.array(timestamps, dtype=np.float64)
    face_mask = ~np.isnan(mar)
    coverage = float(face_mask.mean()) if n else 0.0
    base = {**invalid, "face_coverage_pct": round(coverage * 100, 1), "frames_analyzed": n}

    if n < LIPSYNC_MIN_FRAMES:
        return {**base, "reason": f"only {n} frames analysed", "reason_key": "r.lips.few_frames",
                "reason_params": {"n": n}}
    if coverage < LIPSYNC_MIN_FACE_COVERAGE:
        return {**base, "reason": f"face detected in only {coverage * 100:.0f}% of frames",
                "reason_key": "r.lips.few_faces", "reason_params": {"pct": f"{coverage * 100:.0f}%"}}

    # Audio RMS on a fine 10 ms grid, then sampled at (lag-shifted) frame times.
    hop = sr // 100
    rms = librosa.feature.rms(y=y, frame_length=hop * 4, hop_length=hop)[0]
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

    ts_face, mar_face = ts[face_mask], mar[face_mask]
    if np.std(mar_face) < 1e-6:
        return {**base, "reason": "mouth shape does not change", "reason_key": "r.lips.no_motion"}
    mar_z = (mar_face - mar_face.mean()) / mar_face.std()

    def corr_at(lag_s: float) -> float:
        """Correlation between mouth opening and loudness with the audio shifted by lag_s seconds."""
        audio = np.interp(ts_face + lag_s, rms_t, rms, left=0.0, right=0.0)
        return _pearson(mar_z, audio)

    lags_ms = range(-LIPSYNC_MAX_LAG_MS, LIPSYNC_MAX_LAG_MS + 1, 20)
    best_r, best_lag = max((corr_at(l / 1000.0), l) for l in lags_ms)
    zero_r = corr_at(0.0)

    audio = np.interp(ts_face, rms_t, rms, left=0.0, right=0.0)
    audio_z = (audio - audio.mean()) / (audio.std() + 1e-9)

    return {
        "valid": True,
        "reason": "", "reason_key": None, "reason_params": {},
        "pearson_correlation": round(zero_r, 4),
        "best_lag_correlation": round(best_r, 4),
        "best_lag_ms": int(best_lag),
        "sync_quality": _sync_quality(zero_r),
        "face_coverage_pct": round(coverage * 100, 1),
        "frames_analyzed": n,
        "timestamps": [round(float(t), 3) for t in ts_face],
        "mar_waveform": [round(float(v), 3) for v in mar_z],
        "rms_waveform": [round(float(v), 3) for v in audio_z]
    }


LIPSYNC_SKIPPED = {
    "valid": False, "reason": "skipped (turned off for this run)", "reason_key": "r.lips.skipped", "reason_params": {},
    "pearson_correlation": None,
    "best_lag_correlation": None, "best_lag_ms": None, "sync_quality": "n/a", "face_coverage_pct": None,
    "frames_analyzed": 0, "timestamps": [], "mar_waveform": [], "rms_waveform": []
}


def _warning(key: str, text: str, **params) -> dict:
    """A warning as a translatable key with its values, plus the English text for the JSON file."""
    return {"key": key, "params": {k: str(v) for k, v in params.items()}, "text": text}


def _quality_warnings(orig_ac: dict, dub_ac: dict, stt: dict, dub_ls: dict, dub_text: str) -> list[dict]:
    """Warnings for results that look wrong (mismatched videos, empty transcript, ...)."""
    warnings = []
    od, dd = orig_ac["duration_sec"], dub_ac["duration_sec"]
    if od > 0 and abs(dd - od) / od > 0.2:
        warnings.append(_warning("r.warn.length", f"The dub ({dd} s) and the original ({od} s) differ in length by more "
                                 "than 20%; they may not be the same video.", dub=dd, orig=od))
    if not dub_text:
        warnings.append(_warning("r.warn.no_speech", "Speech recognition found no speech in the dub."))
    if stt.get("error_rate") is not None and stt["error_rate"] > 0.8:
        warnings.append(_warning("r.warn.script", "Very little of the script was heard; check that the script "
                                 "belongs to this video and is in the dub's language."))
    if not dub_ls["valid"] and dub_ls.get("reason_key") not in (None, "r.lips.skipped", "r.lips.replaced"):
        warnings.append(_warning("r.warn.lips", f"Lip movement couldn't be measured: {dub_ls['reason']}."))
    return warnings


def loudness_envelope(y: np.ndarray, sr: int = SAMPLE_RATE, step_sec: float = 0.25) -> list[float]:
    """Loudness in dBFS per step_sec window, for plotting original vs dub over time."""
    hop = int(sr * step_sec)
    if len(y) < hop:
        return []
    rms = librosa.feature.rms(y=y, frame_length=hop, hop_length=hop, center=False)[0]
    return [round(float(v), 1) for v in 20 * np.log10(np.maximum(rms, 1e-5))]


def speech_rate(text: str, speaking_sec: float, lang: str) -> Optional[dict]:
    """Characters/s for CER languages, words/s otherwise, over non-silent time."""
    norm = normalize_text(text)
    if not norm or speaking_sec <= 0:
        return None
    if base_lang(lang) in CER_LANGS:
        count, unit = len(norm.replace(" ", "")), "chars/s"
    else:
        count, unit = len(norm.split()), "words/s"
    return {"value": round(count / speaking_sec, 2), "unit": unit}


def _voice_quality(y_orig: np.ndarray, y_dub: np.ndarray, orig_speech: list, dub_speech: list) -> dict:
    """Voice quality of both tracks (dubeval/voice_quality.py); a missing model or runtime is not measured, never fatal."""
    from dubeval import voice_quality as vq
    try:
        return vq.voice_quality(y_orig, y_dub, orig_speech, dub_speech)
    except Exception as e:  # onnxruntime missing or broken: the rest of the evaluation still counts
        log.warning("Voice quality not measured: %s", e)
        return vq.not_measured("r.vq.error")


def _voice_similarity(y_orig: np.ndarray, y_dub: np.ndarray, segments: list) -> dict:
    """Voice similarity per original line (dubeval/speaker.py); a model that can't be downloaded or run is not measured."""
    from dubeval import speaker, voice_quality
    try:
        return speaker.voice_similarity(y_orig, y_dub, segments, lambda a: voice_quality.score_window(a)[1])
    except speaker.ModelUnavailable as e:
        log.warning("Voice similarity not measured: %s", e)
        return speaker.not_measured("r.vs.no_model")
    except Exception as e:  # a broken runtime must not sink the evaluation
        log.warning("Voice similarity not measured: %s", e)
        return speaker.not_measured("r.vs.error")


def _lip_sync_ready() -> bool:
    """Whether the lip-sync check can run (its pack is installed)."""
    from dubeval import lip_sync
    try:
        return lip_sync.ready()
    except Exception as e:  # a broken pack folder must not sink the evaluation
        log.warning("Lip sync not available: %s", e)
        return False


def _lip_sync(orig_video: str, y_orig: np.ndarray, orig_speech: list, dub_video: str, y_dub: np.ndarray,
              dub_speech: list, duration: float, check=None, dub_offset_sec: float = 0.0) -> dict:
    """The lip-sync check (dubeval/lip_sync.py); a model or video that can't be read is not measured, never fatal.
    y_dub is the dub's own sound (not moved onto the original's timeline); dub_offset_sec is how much later the same
    moment comes in the dub."""
    from dubeval import lip_sync
    try:
        return lip_sync.lip_sync(orig_video, y_orig, orig_speech, dub_video, y_dub, dub_speech, duration, check,
                                 dub_offset_sec)
    except Exception as e:
        if check:
            check()                       # a Stop raised inside goes on (asking again raises it again)
        log.warning("Lip sync not measured: %s", e)
        return lip_sync.not_measured("r.sync_lips.error")


def _spans_id(spans: list) -> str:
    """A short id for a list of [start, end] spans, for cache keys: a changed transcript gives another id."""
    import hashlib
    import json
    return hashlib.sha1(json.dumps(spans).encode("utf-8")).hexdigest()[:10]


def _media_id(path: str) -> str:
    """A cache key for a media file: its name and size (cached downloads are named after their source)."""
    return f"{Path(path).name}:{Path(path).stat().st_size}"


def run_full_evaluation(original_video_path: str, dubbed_video_path: str, ground_truth_text: str,
                        target_lang: str = "ko", whisper_model_name: str = DEFAULT_WHISPER_MODEL,
                        on_step: Optional[Callable[[str, float], None]] = None,
                        include_lipsync: bool = True, source_lang: Optional[str] = None,
                        cache=None, dub_offset_sec: float = 0.0, dub_parts: Optional[list] = None,
                        audio: Optional[tuple] = None, check: Optional[Callable[[], None]] = None) -> dict:
    """Runs the acoustic, speech-recognition, timing, file and lip-sync evaluation. Returns results; writes no files.

    include_lipsync: the experimental lip-movement analysis is the slowest step; False skips it.
    source_lang: the original's language when known (share links say it); None lets Whisper detect it.
    cache: an optional dict-like store (get / item assignment) for Whisper results, keyed by model, language and
    media file, so a rerun on the same videos skips speech recognition. The caller owns any file it writes to.
    dub_offset_sec: how much later the same moment happens in the dub (dubeval/pairing.py). The dub's audio is moved
    onto the original's timeline first, so every measure and every time in the results is the original's.
    dub_parts: for a dub cut differently, the parts of the original with their own offsets (pairing's "parts"); the
    dub is then laid onto the original's timeline part by part instead, and missing parts are silent.
    audio: both waveforms when the caller already has them (load_both), so the sound isn't extracted twice.
    check: called between measurements and inside the long ones (each recognized line, each sampled video frame, each
    language window); it raises to stop the run (the pipeline's Stop), so Stop never waits for a whole stage.
    """
    cache = cache if cache is not None else {}

    def cached(key: str, compute: Callable[[], object]):
        """The cached value for key, computing and storing it on a miss."""
        value = cache.get(key)
        if value is None:
            value = compute()
            cache[key] = value
        return value
    def step(msg: str, frac: float):
        """Stops here when asked (check), then reports evaluation progress, if a callback was given."""
        if check:
            check()
        if on_step:
            on_step(msg, frac)

    step("Loading the speech recognition model...", 0.02)
    model = lambda: get_whisper_model(whisper_model_name)      # loaded only when a result isn't cached
    asr_id = asr.model_id(whisper_model_name)                  # backend + model: cached results never mix recognizers

    if audio is None:
        step("Extracting audio from both videos...", 0.10)
        audio = load_both(original_video_path, dubbed_video_path)
    y_orig, y_dub = audio
    y_dub_own = y_dub                                  # the dub's sound on its own timeline, with its own picture
    if dub_parts:
        from dubeval.pairing import align_dub_parts
        y_dub = align_dub_parts(y_dub, dub_parts, SAMPLE_RATE, len(y_orig))
    elif dub_offset_sec:
        from dubeval.pairing import align_dub
        y_dub = align_dub(y_dub, dub_offset_sec, SAMPLE_RATE)

    step("Measuring loudness and silence...", 0.15)
    orig_ac = analyze_acoustics(y_orig)
    dub_ac = analyze_acoustics(y_dub)

    orig_id, dub_id = _media_id(original_video_path), _media_id(dubbed_video_path)
    if dub_parts:                                                # re-laid audio gives other transcripts
        dub_id += "@" + ";".join(f"{p['start']}-{p['end']}{p['offset_sec']:+.2f}" for p in dub_parts)
    elif dub_offset_sec:
        dub_id += f"@{dub_offset_sec:+.2f}"
    src_lang = whisper_language(source_lang) if source_lang else None
    stt_lang = whisper_language(target_lang)
    step("Transcribing the original speech...", 0.20)
    orig_stt = cached(f"v{CACHE_VERSION}|stt|{asr_id}|{src_lang or 'auto'}|{orig_id}",
                      lambda: transcribe(y_orig, model(), language=src_lang, check=check))
    step("Checking which language the dub is in...", 0.40)
    dub_detected, dub_detected_prob = cached(f"v{CACHE_VERSION}|lang|{asr_id}|{dub_id}", lambda: detect_language(y_dub, model()))
    step("Transcribing the dubbed speech...", 0.45)
    dub_stt = cached(f"v{CACHE_VERSION}|stt|{asr_id}|{stt_lang or 'auto'}|{dub_id}",
                     lambda: transcribe(y_dub, model(), language=stt_lang, check=check))
    vad_orig = cached(f"v{CACHE_VERSION}|vad|{orig_id}", lambda: asr.voice_activity(y_orig))
    vad_dub = cached(f"v{CACHE_VERSION}|vad|{dub_id}", lambda: asr.voice_activity(y_dub))
    orig_stt = cached(f"v{CACHE_VERSION}|sttfill|{asr_id}|{src_lang or 'auto'}|{orig_id}",
                      lambda: fill_gaps(orig_stt, y_orig, vad_orig, model(), src_lang, check))
    dub_stt = cached(f"v{CACHE_VERSION}|sttfill|{asr_id}|{stt_lang or 'auto'}|{dub_id}",
                     lambda: fill_gaps(dub_stt, y_dub, vad_dub, model(), stt_lang, check))
    heard_orig, heard_dub = keep_voiced(orig_stt, vad_orig), keep_voiced(dub_stt, vad_dub)
    orig_stt = keep_voiced(orig_stt, vad_orig, partner=heard_dub["segments"])
    dub_stt = keep_voiced(dub_stt, vad_dub, partner=heard_orig["segments"])
    scores = score_transcript(ground_truth_text, dub_stt["text"], target_lang)

    step("Comparing when each track speaks...", 0.65)
    orig_speech = speech_intervals(orig_stt["segments"])
    dub_speech = speech_intervals(dub_stt["segments"])
    alignment = timing_alignment(orig_speech, dub_speech, max(orig_ac["duration_sec"], dub_ac["duration_sec"]))
    segments = match_segments(orig_stt["segments"], dub_stt["segments"])
    clarity = speech_clarity(dub_stt["segments"])
    step("Rating the voice quality of both tracks...", 0.66)
    speech_id = _spans_id(orig_speech + [None] + dub_speech)    # what the speech-time steps below were given
    vq = cached(f"v{CACHE_VERSION}|vq|{orig_id}|{dub_id}|{speech_id}",
                lambda: _voice_quality(y_orig, y_dub, orig_speech, dub_speech))
    step("Checking the dub's language part by part...", 0.67)
    step("Comparing the dub voice with the original speakers...", 0.665)
    vs = cached(f"v{CACHE_VERSION}|vs|{orig_id}|{dub_id}|{_spans_id([[s['start'], s['end']] for s in orig_stt['segments']])}",
                lambda: _voice_similarity(y_orig, y_dub, orig_stt["segments"]))
    lang_windows = cached(f"v{CACHE_VERSION}|langwin{LANG_OVERLAP}|{asr_id}|{stt_lang}|{dub_id}|{speech_id}",
                          lambda: language_windows(y_dub, model(), orig_speech + dub_speech, stt_lang, check=check))
    integrity = video_integrity(original_video_path, dubbed_video_path)

    sync = None
    if include_lipsync and _lip_sync_ready():
        # The real check (the lip_sync pack) replaces the lip-movement estimate, which then isn't run.
        step("Checking lip sync in both videos...", 0.70)
        duration = min(orig_ac["duration_sec"], dub_ac["duration_sec"])
        if dub_parts:                    # cut differently: no one shift takes the original's moments to the dub's
            from dubeval import lip_sync
            sync = lip_sync.not_measured("r.sync_lips.recut")
        else:
            sync = cached(f"v{CACHE_VERSION}|lipsync|{orig_id}|{dub_id}|{speech_id}",
                          lambda: _lip_sync(original_video_path, y_orig, orig_speech, dubbed_video_path, y_dub_own,
                                            dub_speech, duration, check, dub_offset_sec))
        dub_ls = orig_ls = {**LIPSYNC_SKIPPED, "reason": "replaced by the lip-sync check", "reason_key": "r.lips.replaced"}
    elif include_lipsync:
        step("Analyzing lip movement in the dubbed video...", 0.70)
        dub_ls = analyze_lipsync(dubbed_video_path, y_dub_own, check=check)   # its picture with its own sound
        step("Analyzing lip movement in the original video...", 0.85)
        orig_ls = analyze_lipsync(original_video_path, y_orig, check=check)
    else:
        dub_ls = orig_ls = {**LIPSYNC_SKIPPED}

    orig_speaking = orig_ac["duration_sec"] * (1 - orig_ac["silence_ratio_pct"] / 100)
    dub_speaking = dub_ac["duration_sec"] * (1 - dub_ac["silence_ratio_pct"] / 100)
    source_lang = orig_stt["language"] or "en"
    step("Done", 1.0)

    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "original_video": original_video_path,
            "dubbed_video": dubbed_video_path,
            "target_language": target_lang,
            "detected_source_language": source_lang,
            "whisper_model": asr.resolve(whisper_model_name),
            "speech_recognizer": asr.backend()
        },
        "acoustic_metrics": {
            "original_duration_sec": orig_ac["duration_sec"],
            "dubbed_duration_sec": dub_ac["duration_sec"],
            "duration_diff_sec": round(dub_ac["duration_sec"] - orig_ac["duration_sec"], 2),
            "original_speaking_sec": round(orig_speaking, 2),
            "dubbed_speaking_sec": round(dub_speaking, 2),
            "original_rms": orig_ac["mean_rms_energy"],
            "dubbed_rms": dub_ac["mean_rms_energy"],
            "rms_ratio": round(dub_ac["mean_rms_energy"] / orig_ac["mean_rms_energy"], 4) if orig_ac["mean_rms_energy"] > 1e-6 else None,
            "original_volume_stability_pct": orig_ac["volume_stability_pct"],
            "dubbed_volume_stability_pct": dub_ac["volume_stability_pct"],
            "original_silence_ratio": round(orig_ac["silence_ratio_pct"] / 100.0, 4),
            "dubbed_silence_ratio": round(dub_ac["silence_ratio_pct"] / 100.0, 4),
            "silence_diff": round((dub_ac["silence_ratio_pct"] - orig_ac["silence_ratio_pct"]) / 100.0, 4),
            "original_peak_dbfs": orig_ac["peak_dbfs"],
            "dubbed_peak_dbfs": dub_ac["peak_dbfs"],
            "dubbed_clipping_pct": dub_ac["clipping_pct"],
            "dubbed_clipping_intervals": clipping_intervals(y_dub),
            "loudness_envelope": {
                "step_sec": 0.25,
                "original_db": loudness_envelope(y_orig),
                "dubbed_db": loudness_envelope(y_dub)
            }
        },
        "speech_recognition": {
            **scores,
            "ground_truth": (ground_truth_text or "").strip(),
            "dubbed_transcript": dub_stt["text"],
            "original_transcript": orig_stt["text"],
            "original_speech_rate": speech_rate(orig_stt["text"], orig_speaking, source_lang),
            "dubbed_speech_rate": speech_rate(dub_stt["text"], dub_speaking, target_lang),
            "dubbed_language_detected": dub_detected,
            "dubbed_language_probability": dub_detected_prob,
            "dubbed_language_windows": lang_windows,
            "clarity": clarity,
            "original_segments": [{k: s[k] for k in ("start", "end", "text")} for s in orig_stt["segments"]],
            "dubbed_segments": [{k: s[k] for k in ("start", "end", "text")} for s in dub_stt["segments"]]
        },
        "timing_alignment": {
            **alignment,
            "original_speech": orig_speech,
            "dubbed_speech": dub_speech
        },
        "segment_alignment": segments,
        "video_integrity": integrity,
        "voice_quality": vq,
        "voice_similarity": vs,
        "lipsync_metrics": {
            "measured": include_lipsync,
            # The lip-sync check (dubeval/lip_sync.py) when its pack is installed; None when it didn't run.
            "sync": sync,
            "valid": dub_ls["valid"],
            "reason": dub_ls["reason"],
            "reason_key": dub_ls.get("reason_key"),
            "reason_params": dub_ls.get("reason_params", {}),
            "pearson_correlation": dub_ls["pearson_correlation"],
            "best_lag_correlation": dub_ls["best_lag_correlation"],
            "best_lag_ms": dub_ls["best_lag_ms"],
            "sync_quality": dub_ls["sync_quality"],
            "face_coverage_pct": dub_ls["face_coverage_pct"],
            "original_valid": orig_ls["valid"],
            "original_pearson": orig_ls["pearson_correlation"],
            "original_sync_quality": orig_ls["sync_quality"],
            "original_face_coverage_pct": orig_ls["face_coverage_pct"],
            "waveform_data": {
                "timestamps": dub_ls["timestamps"],
                "mar_norm": dub_ls["mar_waveform"],
                "rms_norm": dub_ls["rms_waveform"]
            }
        },
        "warnings": ([] if stt_lang else [_warning(
            "r.warn.no_whisper", f"Speech recognition doesn't know {target_lang}, so it guessed the language; "
            "treat speech results as rough.", lang=target_lang)]) + _quality_warnings(orig_ac, dub_ac, scores, dub_ls, dub_stt["text"])
    }
