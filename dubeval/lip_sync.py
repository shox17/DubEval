"""Lip sync: do the lips follow the dubbed speech? (the optional lip_sync pack: StableSyncNet from LatentSync 1.5)

StableSyncNet (ByteDance, LatentSync 1.5) turns 16 frames of the lower face (0.64 s at 25 fps) and the sound of
the same moment into two vectors; their cosine similarity is high when the mouth makes the sounds heard. Each
moment is scored with the sound shifted by up to REACH frames either way: the best shift says how far the lips are
off from the sound. Moments whose best shifts agree are lips that follow the speech; a dub whose lips don't follow
it scatters (about one moment in six lands near any shift by chance).

The dub is judged against the original at the same moments, never in absolute terms: some faces, angles and
lighting score lower even in sync, and the original (filmed in sync) shows what this video can score. The
original's own typical shift is also the zero point, so a constant offset of the file or the model cancels out.

Preparation follows LatentSync: 25 fps, the face aligned on three points (both eyebrow centres and the nose) to its
template and smoothed over time, 256×256, the lower half, values in [-1, 1]; the sound as its 80-band mel
spectrogram at 16 kHz. LatentSync finds those points with InsightFace; here MediaPipe's face landmarks (already
bundled for lip movement) give the same three points. Tested on a real Perso dub: the original lined up in 91% of
moments, its lip-synced dub in 84%, the same dub without lip sync in 16% (chance), and a sound delay of 0.2, 0.5
or 1 s added to the original was measured to the frame.

Speed (CPU): at most MAX_MOMENTS moments are scored, the same ones in both videos, read side by side. A quick look at
each candidate's middle frame drops those without a face before the 16 frames are prepared, and shifts are searched
coarse-to-fine (every COARSE frames, then the best one's neighbours), which finds the same peak because a match
stays high for about two frames either side. Both models run with busy-waiting off (dubeval/ort_session.py): with
it on, the two took each other's processor time and ran 3x slower.

The weights (stable_syncnet.pt, 1.6 GB, CreativeML OpenRAIL++-M) are the lip_sync pack, downloaded unchanged from
Hugging Face; the two small graphs in dubeval/models/ (tools/build_syncnet_onnx.py) read them out of that file.
"""
import logging
import os
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterator, Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)

PACK_DIR = Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval")) / "latentsync-syncnet"
CHECKPOINT = "stable_syncnet.pt"
GRAPHS_DIR = Path(__file__).resolve().parent / "models"
AUDIO_GRAPH, VISUAL_GRAPH = "syncnet_audio.onnx", "syncnet_visual.onnx"
AUDIO_SHAPE, VISUAL_SHAPE = (1, 80, 52), (48, 128, 256)

FPS = 25                      # the model's frame rate
FRAMES = 16                   # frames per moment (0.64 s)
MEL_PER_SEC = 80              # mel frames per second (hop 200 at 16 kHz)
MEL_LEN = AUDIO_SHAPE[2]
REACH = 15                    # sound shifts tried, in frames either way (±0.6 s)
COARSE = 3                    # first pass: every 3rd shift; then the best one's neighbours
MATCH_FRAMES = 2              # a moment lines up when its best shift is this close to the typical one (±80 ms)
MAX_SECONDS = 60.0            # moments are taken from the start of the video, like lip movement
MAX_MOMENTS = 30              # scored moments at most, spread over the speech
MIN_MOMENTS = 8               # fewer moments with a face and speech in both videos: not measured
MIN_SPEECH_SHARE = 0.8        # a moment counts only when both tracks speak for most of it
MIN_ORIGINAL_MATCH = 0.5      # the original must line up this often, or its lips aren't the voice heard
MAX_HEIGHT = 720              # frames are scaled down to this before finding the face

# LatentSync's alignment template (affine_transform.py, resolution 256) and its warped face size.
_RATIO = 256 / 256 * 2.8
TEMPLATE = np.array([[19 - 2, 30 - 10], [56 + 2, 30 - 10], [37.5, 45 - 5]]) * _RATIO
FACE_SIZE = (int(75 * _RATIO), int(100 * _RATIO))            # (w, h) = (210, 280)
# MediaPipe face-mesh points for LatentSync's three: each eyebrow's centre and the lower centre of the nose.
BROW_A = [70, 63, 105, 66, 107]
BROW_B = [336, 296, 334, 293, 300]
NOSE = [1, 4, 98, 327]

_sessions = None
_lock = threading.Lock()


def ready() -> bool:
    """Whether the lip_sync pack is installed (the checkpoint is complete) and the graphs are bundled."""
    from dubeval import packs
    return packs.state("lip_sync") == "installed" and all((GRAPHS_DIR / g).is_file() for g in (AUDIO_GRAPH, VISUAL_GRAPH))


def _models():
    """The audio and visual encoders, loaded once (their weights are read from the pack's checkpoint)."""
    global _sessions
    with _lock:
        if _sessions is None:
            from dubeval.ort_session import cpu_session
            _sessions = tuple(cpu_session(GRAPHS_DIR / g, PACK_DIR) for g in (AUDIO_GRAPH, VISUAL_GRAPH))
        return _sessions


def unload() -> None:
    """Forgets the loaded models (the pack was removed or replaced)."""
    global _sessions
    with _lock:
        _sessions = None


def mel(y: np.ndarray) -> np.ndarray:
    """LatentSync's mel spectrogram (Wav2Lip's): pre-emphasis, 80 bands 55-7600 Hz, dB from -100, scaled to [-4, 4]."""
    import librosa
    from scipy import signal
    spec = np.abs(librosa.stft(y=signal.lfilter([1, -0.97], [1], y), n_fft=800, hop_length=200, win_length=800))
    bands = librosa.filters.mel(sr=16000, n_fft=800, n_mels=80, fmin=55, fmax=7600) @ spec
    db = 20 * np.log10(np.maximum(1e-5, bands)) - 20
    return np.clip(8 * ((db + 100) / 100) - 4, -4, 4).astype(np.float32)


def align(points: np.ndarray, p_bias: Optional[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """LatentSync's transformation_from_points: the similarity transform taking points to TEMPLATE, with its
    smoothing (the third point's offset blended with the previous frame's), as a 2x3 matrix and the new offset."""
    p1, p2 = np.asarray(points, np.float64), TEMPLATE
    c1, c2 = p1.mean(0), p2.mean(0)
    s1, s2 = (p1 - c1).std(ddof=1), (p2 - c2).std(ddof=1)            # torch.std is the sample std
    n1, n2 = (p1 - c1) / s1, (p2 - c2) / s2
    u, _, vh = np.linalg.svd(n1.T @ n2)
    v = vh.T
    r = v @ u.T
    if np.linalg.det(r) < 0:
        v[:, -1] = -v[:, -1]
        r = v @ u.T
    m = np.concatenate([(s2 / s1) * r, c2.reshape(2, 1) - (s2 / s1) * (r @ c1.reshape(2, 1))], axis=1)
    bias = n2[2] - n1[2]
    if p_bias is not None:
        bias = p_bias * 0.2 + bias * 0.8
    m[:, 2] += bias
    return m, bias


def _three_points(lm, w: int, h: int) -> np.ndarray:
    """LatentSync's three points from MediaPipe landmarks: left eyebrow, right eyebrow (by image x), nose."""
    pt = lambda ids: np.mean([[lm[k].x * w, lm[k].y * h] for k in ids], axis=0)  # noqa: E731
    a, b = pt(BROW_A), pt(BROW_B)
    left, right = (a, b) if a[0] < b[0] else (b, a)
    return np.round([left, right, pt(NOSE)])


def _frames(video_path: str, ks: list[int], check: Optional[Callable] = None) -> Iterator[tuple[int, np.ndarray]]:
    """(k, RGB frame at most MAX_HEIGHT tall) for each wanted 25 fps frame index k, in order. The video is read at
    its own rate; each 25 fps time takes the nearest source frame, and frames nobody wants are skipped undecoded."""
    from dubeval.evaluate import _cv2_path
    cap = cv2.VideoCapture(_cv2_path(video_path))
    if not cap.isOpened():
        raise ValueError("video could not be opened")
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 and not np.isnan(fps) else FPS
    wanted: dict[int, list[int]] = {}                      # source frame -> the 25 fps frames it stands for
    for k in sorted(set(ks)):
        wanted.setdefault(int(round(k * fps / FPS)), []).append(k)
    try:
        for i in range(max(wanted, default=-1) + 1):
            if i not in wanted:
                if not cap.grab():                         # decoded but not converted: the cheap way past a frame
                    return
                continue
            ok, frame = cap.read()
            if not ok:
                return
            if check:
                check()
            h, w = frame.shape[:2]
            if h > MAX_HEIGHT:
                frame = cv2.resize(frame, (round(w * MAX_HEIGHT / h), MAX_HEIGHT), interpolation=cv2.INTER_AREA)
            rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            for k in wanted[i]:
                yield k, rgb
    finally:
        cap.release()


def _detector():
    """MediaPipe's face landmarker in video mode (one per video: it tracks the face from frame to frame)."""
    import mediapipe as mp  # noqa: F401  (mp.Image is used by the caller)
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    from dubeval.evaluate import FACE_MODEL_PATH
    return vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_buffer=Path(FACE_MODEL_PATH).read_bytes()),
        running_mode=vision.RunningMode.VIDEO, num_faces=1))


def _landmarks(detector, k: int, rgb: np.ndarray):
    """The face's landmarks in frame k, or None."""
    import mediapipe as mp
    res = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(k * 1000 / FPS))
    return res.face_landmarks[0] if res.face_landmarks else None


def face_seen(video_path: str, ks: list[int], check: Optional[Callable] = None) -> set:
    """The frames among ks that show a face (a quick look before the full preparation)."""
    with _detector() as detector:
        return {k for k, rgb in _frames(video_path, ks, check) if _landmarks(detector, k, rgb) is not None}


def lower_faces(video_path: str, starts: list[int], check: Optional[Callable] = None) -> dict:
    """{start: the 16 aligned lower faces (16x128x256x3, uint8 RGB)} for each moment whose frames all show a face."""
    faces: dict[int, Optional[np.ndarray]] = {}
    p_bias, prev = None, None
    with _detector() as detector:
        for k, rgb in _frames(video_path, [s + j for s in starts for j in range(FRAMES)], check):
            if prev is None or k != prev + 1:
                p_bias = None                              # the smoothing runs only over consecutive frames
            prev = k
            lm = _landmarks(detector, k, rgb)
            if lm is None:
                faces[k], p_bias = None, None
                continue
            m, p_bias = align(_three_points(lm, rgb.shape[1], rgb.shape[0]), p_bias)
            face = cv2.warpAffine(rgb, m, FACE_SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(127, 127, 127))
            faces[k] = cv2.resize(face, (256, 256), interpolation=cv2.INTER_LANCZOS4)[128:]
    return {s: np.stack([faces[k] for k in range(s, s + FRAMES)]) for s in starts
            if all(faces.get(k) is not None for k in range(s, s + FRAMES))}


def best_shifts(faces: dict, y: np.ndarray, check: Optional[Callable] = None) -> dict:
    """{start: (best sound shift in frames, + = sound late; its similarity)} for each moment, found coarse-to-fine."""
    aud, vis = _models()
    starts = sorted(faces)
    last = (max(starts, default=0) + FRAMES + REACH + 1) / FPS            # the latest moment of sound needed, seconds
    spec = mel(y[:int((last + 1.0) * 16000)])
    sound: dict[int, np.ndarray] = {}

    def embed(frames: set) -> None:
        """Sound vectors for the 25 fps frame indices not embedded yet (those with a full mel window)."""
        todo = sorted(i for i in frames
                      if i >= 0 and i not in sound and int(MEL_PER_SEC * i / FPS) + MEL_LEN <= spec.shape[1])
        for b in range(0, len(todo), 64):
            if check:
                check()
            part = todo[b:b + 64]
            x = np.stack([spec[:, int(MEL_PER_SEC * i / FPS):int(MEL_PER_SEC * i / FPS) + MEL_LEN] for i in part])
            sound.update(zip(part, aud.run(None, {"x": x[:, None]})[0]))

    looks = {}
    for b in range(0, len(starts), 8):
        if check:
            check()
        part = starts[b:b + 8]
        x = np.stack([faces[s].transpose(0, 3, 1, 2).reshape(VISUAL_SHAPE) for s in part]).astype(np.float32) / 127.5 - 1
        looks.update(zip(part, vis.run(None, {"x": x})[0]))
    coarse = range(-REACH, REACH + 1, COARSE)
    embed({s + o for s in starts for o in coarse})
    first = {s: max((o for o in coarse if s + o in sound), key=lambda o: looks[s] @ sound[s + o], default=None) for s in starts}
    embed({s + c + d for s, c in first.items() if c is not None for d in (-1, 1)})
    out = {}
    for s, c in first.items():
        if c is None:
            continue
        sims = {o: float(looks[s] @ sound[s + o]) for o in (c - 1, c, c + 1) if s + o in sound}
        best = max(sims, key=sims.get)
        out[s] = (best, round(sims[best], 3))
    return out


def typical_shift(shifts: list[int]) -> int:
    """The shift most moments agree on: the window of +/-MATCH_FRAMES holding the most moments, then the median of
    those moments (a window can tie with its neighbours; the median is the middle of the cluster)."""
    if not shifts:
        return 0
    c = max(range(-REACH, REACH + 1), key=lambda c: (sum(abs(s - c) <= MATCH_FRAMES for s in shifts), -abs(c)))
    return int(round(float(np.median([s for s in shifts if abs(s - c) <= MATCH_FRAMES]))))


def pick_moments(orig_speech: list, dub_speech: list, duration: float) -> list[int]:
    """Start frames of up to 3 * MAX_MOMENTS separate moments where both tracks speak, spread evenly (some show no
    face; at most MAX_MOMENTS of the rest are scored)."""
    def share(t0: float, t1: float, speech: list) -> float:
        return sum(max(0.0, min(e, t1) - max(s, t0)) for s, e in speech) / (t1 - t0)
    end = int(min(duration, MAX_SECONDS) * FPS) - FRAMES - REACH
    starts, s = [], REACH
    while s <= end:
        t0, t1 = s / FPS, (s + FRAMES) / FPS
        if share(t0, t1, orig_speech) >= MIN_SPEECH_SHARE and share(t0, t1, dub_speech) >= MIN_SPEECH_SHARE:
            starts.append(s)
            s += FRAMES
        else:
            s += 4
    return _spread(starts, 3 * MAX_MOMENTS)


def _spread(items: list, n: int) -> list:
    """At most n of items, evenly spaced."""
    if len(items) <= n:
        return items
    return [items[int(i * len(items) / n)] for i in range(n)]


def not_measured(reason_key: str, **params) -> dict:
    """A lip-sync result that wasn't measured, with the reason as a text key."""
    return {"measured": False, "reason_key": reason_key, "reason_params": {k: str(v) for k, v in params.items()}}


def lip_sync(orig_video: str, y_orig: np.ndarray, orig_speech: list, dub_video: str, y_dub: np.ndarray,
             dub_speech: list, duration: float, check: Optional[Callable] = None, dub_offset_sec: float = 0.0) -> dict:
    """How often the dub's lips line up with its speech, and how far its sound is off, next to the original's.

    Moments are chosen on the original's timeline (orig_speech and dub_speech are both on it); in the dub the same
    moment comes dub_offset_sec later, so its frames and its own sound (y_dub, not moved) are read from there."""
    shift = int(round(dub_offset_sec * FPS))
    starts = [s for s in pick_moments(orig_speech, dub_speech, duration) if s + shift >= REACH]
    with ThreadPoolExecutor(2) as pool:                    # the two videos are read side by side
        mid = [s + FRAMES // 2 for s in starts]
        jobs = [pool.submit(face_seen, orig_video, mid, check), pool.submit(face_seen, dub_video, [m + shift for m in mid], check)]
        seen_o, seen_d = (f.result() for f in jobs)
        starts = _spread([s for s in starts if s + FRAMES // 2 in seen_o and s + FRAMES // 2 + shift in seen_d],
                         int(MAX_MOMENTS * 1.2))           # a few spare: a face can drop out within a moment
        jobs = [pool.submit(lower_faces, orig_video, starts, check),
                pool.submit(lower_faces, dub_video, [s + shift for s in starts], check)]
        orig_faces, dub_faces = (f.result() for f in jobs)
    both = _spread([s for s in starts if s in orig_faces and s + shift in dub_faces], MAX_MOMENTS)
    if len(both) < MIN_MOMENTS:
        return not_measured("r.sync_lips.few_moments", n=len(both))
    orig = best_shifts({s: orig_faces[s] for s in both}, y_orig, check)
    dub = {s - shift: v for s, v in best_shifts({s + shift: dub_faces[s + shift] for s in both}, y_dub, check).items()}
    both = [s for s in both if s in orig and s in dub]
    if len(both) < MIN_MOMENTS:
        return not_measured("r.sync_lips.few_moments", n=len(both))
    zero = typical_shift([orig[s][0] for s in both])
    orig_match = sum(abs(orig[s][0] - zero) <= MATCH_FRAMES for s in both) / len(both)
    if orig_match < MIN_ORIGINAL_MATCH:
        return not_measured("r.sync_lips.original_off", pct=f"{orig_match:.0%}")
    dub_zero = typical_shift([dub[s][0] for s in both])
    dub_match = sum(abs(dub[s][0] - zero) <= MATCH_FRAMES for s in both) / len(both)
    dub_own = sum(abs(dub[s][0] - dub_zero) <= MATCH_FRAMES for s in both) / len(both)
    return {
        "measured": True,
        "moments": len(both),
        "original_match": round(orig_match * len(both)),
        "dub_match": round(dub_match * len(both)),
        "original_match_pct": round(orig_match * 100),
        "dub_match_pct": round(dub_match * 100),
        # Lips that follow the speech at another shift: the dub's sound is off by a constant amount.
        "dub_offset_ms": round((dub_zero - zero) * 1000 / FPS) if dub_own >= MIN_ORIGINAL_MATCH else None,
        "dub_offset_match_pct": round(dub_own * 100),
        "timeline": [{"time": round(s / FPS, 2), "end": round((s + FRAMES) / FPS, 2),
                      "original": orig[s][0] - zero, "dub": dub[s][0] - zero,
                      "dub_lines_up": abs(dub[s][0] - zero) <= MATCH_FRAMES} for s in both],
    }
