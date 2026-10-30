"""Pairing: are the original and the dub the same video, how far is the dub shifted in time, and which parts of the
original are missing from it?

Three kinds of evidence, all read from the files only (no writes, no network):
- motion: how much the picture changes from one frame to the next (a head turn, a gesture, a cut). Its rhythm is
  distinctive even in a static talking-head shot, so cross-correlating the two motion signals finds the shift, and
  doing it window by window finds where a differently cut dub jumps (and so which part of the original is missing);
- pictures: a 64-bit difference hash ("dHash") of each frame. The dub keeps the original's picture, so at the right
  shift the hashes match: that decides "same video or not", and finds parts replaced by other pictures;
- background sound: the onset envelope of each audio track (music, effects, the rhythm of speech), which refines
  the shift to about 10 ms when it agrees with the picture, and shows when the dub's sound is behind or ahead of its
  own picture (`sound_sync`: the background the dub keeps from the original lands later or earlier than the picture).
Convention: offset_sec is how much later the same moment happens in the dub (dub time = original time + offset).
"""
import logging
import subprocess
from typing import Callable, Optional

import numpy as np

from dubeval.inputs import LOCAL_INPUT

log = logging.getLogger(__name__)

FRAME_W, FRAME_H = 32, 18             # frames are read this small (grayscale): plenty for motion and hashes
HASH_W, HASH_H = 9, 8                 # dHash: 8 comparisons per row, 8 rows → 64 bits
FRAME_MATCH_BITS = 12                 # two frames "match" when at most this many of the 64 bits differ
SAME_VIDEO = (0.6, 0.25)              # share of matching frames: ≥ first → same video; < second → different
MAX_SHIFT_SEC = 60.0                  # the largest time shift searched (also capped at half the shorter file)
MAX_FPS, MAX_FRAMES = 10.0, 6000      # frames sampled per second, fewer for long videos
WINDOW_SEC, MIN_WINDOW_FRAMES = 8.0, 30   # the motion is matched window by window, each at least this long
MOTION_CONFIDENT = 0.6                # a window's best motion correlation must reach this...
MOTION_MARGIN = 0.1                   # ...and beat the best shift more than 1 s away by this much
MIN_GAP_SEC = 1.0                     # shorter stretches of the original that aren't found aren't reported
AUDIO_HOP_SEC = 0.01                  # onset envelope resolution (10 ms)
AUDIO_REFINE_SEC = 0.3                # the sound refines the picture's shift within this range
AUDIO_CONFIDENT = 0.15                # normalized correlation above which the sound's shift is trusted
CLOSE_COVERAGE = 6.0                  # motion and hash answers this close in coverage (points) count as equally good
PLATEAU = 0.03                        # hash scores this close to the best count as equally good (static shots)
MAX_PARTS = 5                         # without motion, a differently cut dub is matched in at most this many parts
PART_MIN_SCORE = 0.15                 # ...each matching at least this share of frames
VERSION = 2                           # bump when pair()'s result changes (2: sound_sync); part of its cache key
SYNC_SEARCH_SEC = 2.0                 # the dub's sound is searched this far either side of the picture's shift...
SYNC_MIN_SEC = 15.0                   # ...on files at least this long (on a 7 s clip a stray match looked like 0.9 s)
SYNC_CONFIDENT = 0.2                  # ...and trusted when the two soundtracks match at least this well there
SHORT_READ = 0.9                      # a read with fewer frames than this share of the sound's length is read again


# ---------------- frames ----------------
def frame_rate_for(duration: Optional[float]) -> float:
    """How many frames per second to sample: MAX_FPS for short videos, at most MAX_FRAMES frames in all."""
    if not duration:
        return MAX_FPS
    return float(min(MAX_FPS, max(0.5, MAX_FRAMES / duration)))


def read_frames(path: str, fps: float, ffmpeg: str, expected: int = 0) -> np.ndarray:
    """The video's frames at fps, tiny and grayscale: (n, FRAME_H, FRAME_W) floats; empty without a picture.

    A read that fails partway, or brings far fewer than the expected frames (from the sound's length), is read once
    more: a frame list cut short silently changes the coverage. Two reads that agree are what the file holds."""
    cmd = [ffmpeg, "-nostdin", "-loglevel", "error", *LOCAL_INPUT, "-i", path, "-an", "-sn", "-dn",
           "-vf", f"fps={fps},scale={FRAME_W}:{FRAME_H}:flags=area,format=gray", "-f", "rawvideo", "-"]
    counts = []
    while True:
        proc = subprocess.run(cmd, capture_output=True)
        raw = np.frombuffer(proc.stdout, dtype=np.uint8)
        n = len(raw) // (FRAME_W * FRAME_H)
        short = n and (proc.returncode != 0 or n < SHORT_READ * expected)
        if not short or n in counts or len(counts) == 2:
            break
        log.warning("Reading the picture of %s stopped after %d frames (ffmpeg exit %d); reading it again",
                    path, n, proc.returncode)
        counts.append(n)
    return raw[: n * FRAME_W * FRAME_H].reshape(n, FRAME_H, FRAME_W).astype(np.float32)


def hashes(frames: np.ndarray) -> np.ndarray:
    """dHashes (uint64) of frames: each averaged down to 9×8, then whether each pixel is brighter than its left
    neighbour."""
    if not len(frames):
        return np.zeros(0, dtype=np.uint64)
    ys = np.array_split(np.arange(FRAME_H), HASH_H)
    xs = np.array_split(np.arange(FRAME_W), HASH_W)
    small = np.stack([np.stack([frames[:, y][:, :, x].mean(axis=(1, 2)) for x in xs], axis=-1) for y in ys], axis=1)
    bits = (small[:, :, 1:] > small[:, :, :-1]).reshape(len(frames), 64)
    weights = np.uint64(1) << np.arange(64, dtype=np.uint64)
    return (bits.astype(np.uint64) * weights).sum(axis=1).astype(np.uint64)


def frame_hashes(path: str, fps: float, ffmpeg: str) -> np.ndarray:
    """dHashes of a video's frames sampled at fps; empty when the file has no picture."""
    return hashes(read_frames(path, fps, ffmpeg))


def motion(frames: np.ndarray) -> Optional[np.ndarray]:
    """How much each frame differs from the one before, normalized; None when the picture never changes."""
    if len(frames) < 3:
        return None
    d = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    if d.std() < 1e-3:
        return None
    m = np.log1p(np.concatenate([d[:1], d]))          # the first frame has no predecessor: repeat the second's value
    m = (m - m.mean()) / (m.std() + 1e-9)
    return np.clip(m, -4.0, 4.0)                       # one extreme frame mustn't decide the match


def _distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Bits that differ between two equal-length hash arrays."""
    x = np.bitwise_xor(a, b).view(np.uint8).reshape(-1, 8)
    return np.unpackbits(x, axis=1).sum(axis=1)


# ---------------- matching ----------------
def _ncc(a: np.ndarray, b: np.ndarray, lag: int, lo: int, hi: int, min_len: int) -> Optional[float]:
    """Normalized correlation of a[lo:hi] with b shifted by lag (b index = a index + lag); None if too short."""
    i0, i1 = max(lo, -lag, 0), min(hi, len(a), len(b) - lag)   # a window can run past a short video's end
    if i1 - i0 < min_len:
        return None
    x, y = a[i0:i1] - a[i0:i1].mean(), b[i0 + lag:i1 + lag] - b[i0 + lag:i1 + lag].mean()
    den = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.dot(x, y) / den) if den > 1e-9 else None


def _scan(a: np.ndarray, b: np.ndarray, max_lag: int, lo: int, hi: int, min_len: int) -> dict[int, float]:
    """Motion correlation at every lag within ±max_lag, for the stretch a[lo:hi]."""
    out = {}
    for lag in range(-max_lag, max_lag + 1):
        c = _ncc(a, b, lag, lo, hi, min_len)
        if c is not None:
            out[lag] = c
    return out


def _peak(scores: dict[int, float], fps: float) -> tuple[Optional[int], float, float]:
    """(best lag, its score, its margin over the best lag more than 1 s away)."""
    if not scores:
        return None, 0.0, 0.0
    lag = max(scores, key=scores.get)
    far = [s for l, s in scores.items() if abs(l - lag) > fps]
    return lag, scores[lag], scores[lag] - (max(far) if far else -1.0)


def _parts(ma: np.ndarray, mb: np.ndarray, fps: float, max_lag: int) -> list[dict]:
    """Stretches of the original that sit at one shift in the dub, found window by window from the motion."""
    size = max(MIN_WINDOW_FRAMES, int(WINDOW_SEC * fps))
    step = max(1, size // 4)
    found = []
    for lo in range(0, max(1, len(ma) - size + 1), step):
        lag, score, margin = _peak(_scan(ma, mb, max_lag, lo, lo + size, size // 2), fps)
        if lag is not None and score >= MOTION_CONFIDENT and margin >= MOTION_MARGIN:
            found.append((lo, min(len(ma), lo + size), lag))
    parts: list[dict] = []
    for lo, hi, lag in found:
        if parts and abs(parts[-1]["lag"] - lag) <= 1 and lo <= parts[-1]["hi"]:
            parts[-1]["hi"] = hi
        else:
            parts.append({"lo": lo, "hi": hi, "lag": lag})
    # A window that straddles a cut can land on a stray shift: keep parts confirmed by at least two windows.
    return [p for p in parts if p["hi"] - p["lo"] >= size + step] or parts


MISSING = -10**9                      # the lag of an original frame that isn't in the dub


def _residual(ma: np.ndarray, mb: np.ndarray, lag: int, lo: int, hi: int) -> np.ndarray:
    """How badly the dub's motion fits the original's at a lag, frame by frame over [lo, hi)."""
    i = np.arange(lo, hi)
    j = i + lag
    r = np.full(hi - lo, 5.0)
    ok = (j >= 0) & (j < len(mb))
    r[ok] = np.abs(ma[i[ok]] - mb[j[ok]])
    return r


def _assign(ma: np.ndarray, mb: np.ndarray, n: int, parts: list[dict], size: int) -> np.ndarray:
    """The dub lag of every original frame (MISSING where the frame isn't in the dub).

    Between two parts the split is placed where the motion fits best; when the dub jumps back in time, the frames
    right after the split are the part of the original that was cut.
    """
    lags = np.full(n, parts[0]["lag"] if parts else MISSING, dtype=np.int64)
    for p, q in zip(parts, parts[1:]):
        gap = max(0, p["lag"] - q["lag"])
        lo = max(0, min(p["hi"] - size, q["lo"]))
        hi = min(n, max(q["lo"] + size, p["hi"]) + gap)
        cp = np.concatenate([[0.0], np.cumsum(_residual(ma, mb, p["lag"], lo, hi))])
        cq = np.concatenate([[0.0], np.cumsum(_residual(ma, mb, q["lag"], lo, hi))])
        splits = np.arange(lo, max(lo, hi - gap) + 1)
        cost = cp[splits - lo] + cq[-1] - cq[np.minimum(splits + gap, hi) - lo]
        split = int(splits[int(np.argmin(cost))])
        lags[split:] = q["lag"]
        lags[split:split + gap] = MISSING
    return lags


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) index ranges where mask is True."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def coverage(ha: np.ndarray, hb: np.ndarray, lags: np.ndarray, fps: float) -> dict:
    """Which original frames are in the dub at their assigned lag (in range, and the picture matches), the parts
    and their shifts, and the stretches of the original that are missing."""
    n = len(ha)
    idx = np.arange(n)
    j = idx + lags
    inside = (lags != MISSING) & (j >= 0) & (j < len(hb))
    match = np.zeros(n, dtype=bool)
    match[inside] = _distance(ha[inside], hb[j[inside]]) <= FRAME_MATCH_BITS
    # Isolated mismatching frames (a fade, a caption) don't make a part missing: only runs of MIN_GAP_SEC do.
    gap = max(1, int(round(MIN_GAP_SEC * fps)))
    found = inside.copy()
    for s, e in _runs(inside & ~match):
        if e - s >= gap:
            found[s:e] = False
    parts = [{"start": round(float(s) / fps, 2), "end": round(float(e) / fps, 2),
              "offset_sec": round(int(lags[s]) / fps, 2)} for s, e in _runs(found)]
    missing = [[round(float(s) / fps, 2), round(float(e) / fps, 2)] for s, e in _runs(~found) if e - s >= gap]
    return {"coverage_pct": round(float(found.mean()) * 100, 1) if n else None, "parts": parts, "missing": missing,
            "steady_offset": len({p["offset_sec"] for p in parts}) <= 1,
            "picture_match": round(float(match[inside].mean()), 3) if inside.any() else 0.0}


# ---------------- sound ----------------
def onset_envelope(y: np.ndarray, sr: int) -> np.ndarray:
    """The track's onset strength every 10 ms, normalized (mean 0, standard deviation 1)."""
    import librosa
    hop = int(sr * AUDIO_HOP_SEC)
    env = librosa.onset.onset_strength(y=y.astype(np.float32), sr=sr, hop_length=hop)
    env = env - env.mean()
    std = env.std()
    return env / std if std > 1e-9 else env


def audio_offset(env_o: np.ndarray, env_d: np.ndarray, around: Optional[float], max_shift: float,
                 reach_sec: float = AUDIO_REFINE_SEC) -> tuple[float, float]:
    """(offset in seconds, correlation) of the best match of the two envelopes, searched within reach_sec of
    `around` when given, else within ±max_shift."""
    if around is None:
        center, reach = 0, int(max_shift / AUDIO_HOP_SEC)
    else:
        center, reach = int(round(around / AUDIO_HOP_SEC)), int(reach_sec / AUDIO_HOP_SEC)
    best, best_c = 0, -1.0
    for lag in range(center - reach, center + reach + 1):
        i0, i1 = max(0, -lag), min(len(env_o), len(env_d) - lag)
        if i1 - i0 < 100:                    # less than a second of overlap says nothing
            continue
        c = float(np.dot(env_o[i0:i1], env_d[i0 + lag:i1 + lag]) / (i1 - i0))
        if c > best_c:
            best, best_c = lag, c
    return round(best * AUDIO_HOP_SEC, 2), round(max(best_c, 0.0), 3)


def sound_sync(env_o: np.ndarray, env_d: np.ndarray, picture_offset: float, duration: float,
               picture_step: float = 0.0) -> dict:
    """How far the dub's sound is behind (+) or ahead of (-) its own picture: where the background sound it keeps
    from the original lines up, against where the picture does. Not measured on short files, or when the two
    soundtracks don't share enough sound (a dub that replaced the music and effects).

    picture_step: the time between the frames compared (longer on long videos, frame_rate_for). The picture's shift
    is only known to within half of it, so that much of the gap is never counted: a long film whose sound is in step
    isn't called late because its frames were sampled every 0.6 s."""
    if duration < SYNC_MIN_SEC:
        return {"measured": False, "reason": "short"}
    offset, corr = audio_offset(env_o, env_d, picture_offset, SYNC_SEARCH_SEC, reach_sec=SYNC_SEARCH_SEC)
    if corr < SYNC_CONFIDENT:
        return {"measured": False, "reason": "no_shared_sound", "correlation": corr}
    gap, slack = offset - picture_offset, picture_step / 2
    shift = float(np.sign(gap)) * max(0.0, abs(gap) - slack)
    return {"measured": True, "shift_sec": round(shift, 2), "correlation": corr, "picture_step_sec": round(picture_step, 2)}


# ---------------- the whole check ----------------
def _hash_lag(ha: np.ndarray, hb: np.ndarray, max_lag: int) -> tuple[Optional[int], dict, list[int]]:
    """The lag where the most frame hashes match, every lag's score, and every lag about as good (static shots)."""
    scores = {}
    min_overlap = max(4, int(0.3 * min(len(ha), len(hb))))
    for lag in range(-max_lag, max_lag + 1):
        i0, i1 = max(0, -lag), min(len(ha), len(hb) - lag)
        if i1 - i0 >= min_overlap:
            scores[lag] = float(np.mean(_distance(ha[i0:i1], hb[i0 + lag:i1 + lag]) <= FRAME_MATCH_BITS))
    if not scores:
        return None, {}, []
    best = max(scores.values())
    plateau = [lag for lag, s in scores.items() if s >= best - PLATEAU]
    return min(plateau, key=abs), scores, plateau


def _hash_assign(ha: np.ndarray, hb: np.ndarray, fps: float, scores: dict, main: int) -> np.ndarray:
    """Without usable motion: the dub lag of every original frame from the hashes alone. Frames are matched at the
    main lag first, then at up to MAX_PARTS - 1 other clear peaks (a differently cut dub), in runs of at least
    MIN_GAP_SEC so a stray look-alike frame doesn't count."""
    peaks, spacing = [main], max(1, int(fps))
    for lag, sc in sorted(scores.items(), key=lambda kv: -kv[1]):
        if len(peaks) >= MAX_PARTS or sc < PART_MIN_SCORE:
            break
        if all(abs(lag - p) >= spacing for p in peaks) and sc >= scores.get(lag - 1, 0) and sc >= scores.get(lag + 1, 0):
            peaks.append(lag)
    n, run = len(ha), max(2, int(round(MIN_GAP_SEC * fps)))
    lags = np.full(n, MISSING, dtype=np.int64)
    for lag in peaks:
        ok = np.zeros(n, dtype=bool)
        i0, i1 = max(0, -lag), min(n, len(hb) - lag)
        if i1 > i0:
            ok[i0:i1] = _distance(ha[i0:i1], hb[i0 + lag:i1 + lag]) <= FRAME_MATCH_BITS
        for a, b in _runs(ok & (lags == MISSING)):
            if b - a >= run:
                lags[a:b] = lag
    return lags


def read_both(original_path: str, dub_path: str, fps: float, ffmpeg: str,
              expected: tuple[int, int] = (0, 0)) -> tuple[np.ndarray, np.ndarray]:
    """Both videos' frames, decoded at the same time (two ffmpeg processes; decoding is most of the check's time)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(read_frames, original_path, fps, ffmpeg, expected[0])
        fb = pool.submit(read_frames, dub_path, fps, ffmpeg, expected[1])
        return fa.result(), fb.result()


def pair(original_path: str, dub_path: str, y_orig: np.ndarray, y_dub: np.ndarray, sr: int, ffmpeg: str,
         original_duration: Optional[float] = None, dub_duration: Optional[float] = None,
         progress: Optional[Callable[[str, float], None]] = None) -> dict:
    """Same video or not, the dub's time shift, and the original's coverage by the dub.

    progress(message, fraction) is told when the slow parts start: reading the pictures, then matching them."""
    report = progress or (lambda message, fraction: None)
    dur_o = original_duration or len(y_orig) / sr
    dur_d = dub_duration or len(y_dub) / sr
    max_shift = min(MAX_SHIFT_SEC, 0.5 * min(dur_o, dur_d))
    fps = frame_rate_for(max(dur_o, dur_d))
    report("Reading the picture of both videos...", 0.0)
    fa, fb = read_both(original_path, dub_path, fps, ffmpeg, (int(dur_o * fps), int(dur_d * fps)))
    report("Matching the two videos...", 0.7)
    env_o, env_d = onset_envelope(y_orig, sr), onset_envelope(y_dub, sr)
    result = {"measured": True, "frames_per_second": fps, "duration_original_sec": round(dur_o, 2),
              "duration_dub_sec": round(dur_d, 2)}

    if len(fa) < 4 or len(fb) < 4:
        # No picture on one side (an audio-only file): the sound decides, and never refuses.
        offset, corr = audio_offset(env_o, env_d, None, max_shift)
        trusted = corr >= AUDIO_CONFIDENT
        result.update(evidence="sound", same_video=True if trusted else None, picture_match=None,
                      sound_correlation=corr, offset_sec=offset if trusted else 0.0,
                      offset_source="sound" if trusted else "none", coverage_pct=None, missing=[],
                      steady_offset=None, parts=[])
        return result

    ha, hb = hashes(fa), hashes(fb)
    ma, mb = motion(fa), motion(fb)
    max_lag = int(max_shift * fps)
    parts = _parts(ma, mb, fps, max_lag) if ma is not None and mb is not None else []
    # The hashes always give one answer; the motion another when the picture moves. Keep the one that finds more of
    # the original in the dub (a stray motion match must never make the same video look different).
    main_h, scores, plateau = _hash_lag(ha, hb, max_lag)
    if main_h is None and not parts:
        return {**result, "measured": False, "reason": "too_short"}
    candidates = []
    if main_h is not None:
        snd_off, snd_corr = audio_offset(env_o, env_d, None, max_shift)
        snd_lag = int(round(snd_off * fps))
        if snd_corr >= AUDIO_CONFIDENT and any(abs(l - snd_lag) <= 1 for l in plateau):
            main_h = min(plateau, key=lambda l: abs(l - snd_lag))     # static shots: the sound picks among equals
        lags_h = _hash_assign(ha, hb, fps, scores, main_h)
        candidates.append((coverage(ha, hb, lags_h, fps), lags_h, main_h, "picture"))
    if parts:
        size = max(MIN_WINDOW_FRAMES, int(WINDOW_SEC * fps))
        lags_m = _assign(ma, mb, len(ha), parts, size)
        main_m = max(parts, key=lambda p: p["hi"] - p["lo"])["lag"]
        candidates.append((coverage(ha, hb, lags_m, fps), lags_m, main_m, "motion"))
    # Motion is the sharper evidence (hashes of a static shot match at any shift), so it wins whenever it explains
    # most of the original; otherwise the answer that finds more of the original in the dub wins.
    # When both explain about as much (within CLOSE_COVERAGE points), the one whose frames match better wins.
    best_cov = max(c[0]["coverage_pct"] or 0 for c in candidates)
    pool = [c for c in candidates if (c[0]["coverage_pct"] or 0) >= best_cov - CLOSE_COVERAGE]
    motion_ok = [c for c in pool if c[3] == "motion" and (c[0]["coverage_pct"] or 0) >= SAME_VIDEO[0] * 100]
    if motion_ok and len(pool) > 1:
        other = [c for c in pool if c[3] != "motion"][0]
        if other[0]["picture_match"] > motion_ok[0][0]["picture_match"] + 0.05:
            motion_ok = []
    cov, lags, main, source = motion_ok[0] if motion_ok else max(
        pool, key=lambda c: (c[0]["picture_match"], c[0]["coverage_pct"] or 0))
    offset, corr = audio_offset(env_o, env_d, main / fps, max_shift)
    if corr >= AUDIO_CONFIDENT:
        source += "+sound"
    else:
        offset = round(main / fps, 2)
    share = (cov["coverage_pct"] or 0) / 100
    evidence = max(cov["picture_match"], share)
    same = True if evidence >= SAME_VIDEO[0] else False if evidence < SAME_VIDEO[1] else None
    result.update(evidence="picture", same_video=same, sound_correlation=corr, offset_sec=offset,
                  offset_source=source, **cov)
    if same is not False and len(cov.get("parts") or []) <= 1:      # a recut dub has no single shift to compare with
        result["sound_sync"] = sound_sync(env_o, env_d, round(main / fps, 2), min(dur_o, dur_d), 1 / fps)
    return result


def not_measured(reason: str) -> dict:
    """A pairing result for when the check couldn't run."""
    return {"measured": False, "reason": reason, "same_video": None, "offset_sec": 0.0, "offset_source": "none",
            "coverage_pct": None, "missing": [], "parts": []}


def align_dub_parts(y_dub: np.ndarray, parts: list[dict], sr: int, length: int) -> np.ndarray:
    """The dub's audio laid onto the original's timeline part by part (a differently cut dub): each part of the
    original [start, end] gets the dub's audio from [start + offset, end + offset]; missing parts stay silent."""
    out = np.zeros(length, dtype=y_dub.dtype)
    for p in parts:
        s, e = int(round(p["start"] * sr)), min(length, int(round(p["end"] * sr)))
        src = s + int(round(p["offset_sec"] * sr))
        a, b = max(src, 0), min(len(y_dub), src + (e - s))
        if b > a:
            out[s + (a - src):s + (b - src)] = y_dub[a:b]
    return out


def align_dub(y_dub: np.ndarray, offset_sec: float, sr: int, length: Optional[int] = None) -> np.ndarray:
    """The dub's audio moved onto the original's timeline: the first offset_sec cut (offset > 0) or that much
    silence added (offset < 0); then padded or cut to `length` samples when given."""
    shift = int(round(offset_sec * sr))
    y = y_dub[shift:] if shift >= 0 else np.concatenate([np.zeros(-shift, dtype=y_dub.dtype), y_dub])
    if length is not None:
        y = y[:length] if len(y) >= length else np.concatenate([y, np.zeros(length - len(y), dtype=y.dtype)])
    return y
