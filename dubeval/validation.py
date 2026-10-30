"""Validation: does DubEval catch known problems, and does it stay quiet when nothing is wrong? Per language pair.

Each dub of a test-set sheet is copied as a *control* (its sound re-encoded, nothing else changed) and as *variants*,
each with one known problem at a known time: silence, the original voice left in, a loudness jump, distortion, noise,
or a cut. Every copy is evaluated the same way, and each variant is compared with the control:

- caught: a new problem of an expected kind where the problem was put (a few seconds' tolerance);
- false alarm: a new problem anywhere else (often speech recognition reading the changed sound differently);
- a *harmless* variant (the whole dub 3 dB quieter) must bring no new problem at all.

Each problem is put where both the original and the dub are speaking (the control's speech recognition decides), and
not where the control already has a problem of the kind that would catch it, so a catch can't hide behind it.
Places are chosen on the original's timeline (where DubEval reports problems) and written into the dub at the same
moment of the dub, following DubEval's own pairing when the dub is shifted or cut differently.
Comparing with the control, not with the untouched dub, cancels what DubEval already finds in the dub and the effect
of re-encoding, so any dub can be used, good or poor. Problems made on purpose are easier to catch than real ones:
this measures the checks' reach and their false alarms; agreement with people on real dubs (`qa.py batch`) is still
the measure that counts. The translation check is off here (it reads text; it is validated separately).

Pairs are split by original video, never by dub: a video's dubs are all in the tuning set or all held out. A sheet's
`split` column decides (tune | holdout); without it, the split follows a hash of the original video's content.
"""
import hashlib
import logging
import subprocess
from pathlib import Path, PureWindowsPath
from typing import Callable, Optional

import numpy as np

from dubeval.evaluate import FFMPEG_EXE, SAMPLE_RATE, extract_audio, load_audio
from dubeval.inputs import LOCAL_INPUT

log = logging.getLogger(__name__)

TOLERANCE_SEC = 2.0            # a new problem this close to the injected range counts as found there
HOLDOUT_SHARE = 4              # without a split column, about one original video in this many is held out

# Each known problem: how long it lasts and which problem kinds count as catching it.
DEFECTS = {
    "silence_3s": {"seconds": 3.0, "expect": {"long_silence", "timing_mismatch", "missing_speech"}},
    "silence_6s": {"seconds": 6.0, "expect": {"long_silence", "timing_mismatch", "missing_speech"}},
    "original_voice_8s": {"seconds": 8.0, "expect": {"wrong_language"}},
    "loudness_jump_3s": {"seconds": 3.0, "expect": {"loudness_jump", "distortion"}},
    "distortion_3s": {"seconds": 3.0, "expect": {"distortion"}},
    "noise_4s": {"seconds": 4.0, "expect": {"voice_quality", "unclear_speech"}},
    "cut_4s": {"seconds": 4.0, "expect": {"missing_in_dub"}},                # picture and sound both cut
    "sound_late_1s": {"seconds": None, "expect": {"timing_mismatch", "sound_sync"}, "shift": 1.0},   # sound behind the picture
}
HARMLESS = {"quieter_3db": {"seconds": None, "expect": set()}}


def split_of(info: dict, original: str) -> str:
    """tune or holdout: the sheet's split column, else a stable hash of the original video (its content when it exists)."""
    chosen = (info.get("split") or "").strip().lower()
    if chosen in ("tune", "holdout"):
        return chosen
    path = Path(original)
    if path.is_file():                              # by content: copies of one video often share a name like original.mp4
        with open(path, "rb") as f:
            key = f"{path.stat().st_size}:".encode() + f.read(1 << 20)
    else:                                           # either separator: a sheet written on Windows reads the same anywhere
        key = PureWindowsPath(original).name.lower().encode("utf-8")
    digest = hashlib.sha1(key).hexdigest()
    return "holdout" if int(digest, 16) % HOLDOUT_SHARE == 0 else "tune"


def speech_mask(original_speech: list, dubbed_speech: list, duration: float) -> np.ndarray:
    """Per 0.1 s: whether the original and the dub are both speaking ([start, end] stretches from speech recognition)."""
    n = max(0, int(duration * 10))

    def mask(spans):
        m = np.zeros(n, dtype=bool)
        for a, b in spans:
            m[max(0, int(a * 10)):max(0, int(np.ceil(b * 10)))] = True
        return m
    return mask(original_speech) & mask(dubbed_speech)


def dub_time(start: float, seconds: float, pairing: Optional[dict]) -> Optional[float]:
    """Where the original's stretch [start, start + seconds] is in the dub, from the evaluation's pairing (the dub laid
    onto the original by one shift, or part by part); None when the stretch isn't one piece of the dub."""
    pairing = pairing or {}
    if pairing.get("applied_parts"):
        part = next((x for x in pairing.get("parts") or []
                     if x["start"] <= start and start + seconds <= x["end"]), None)
        return None if part is None else round(start + part["offset_sec"], 2)
    return round(start + (pairing.get("applied_offset_sec") or 0.0), 2)


def speech_window(active: np.ndarray, seconds: float, seed: str, blocked: list = (),
                  pairing: Optional[dict] = None) -> Optional[float]:
    """The start of a stretch of `seconds` that is at least 80% speech (`active`, per 0.1 s; speech has short pauses),
    in the middle 70% of the dub, clear of the `blocked` (start, end) ranges by TOLERANCE_SEC and in one piece of the
    dub (`pairing`), chosen the same way every time for the same seed; None when there is no such stretch."""
    if not len(active):
        return None
    need = int(round(seconds * 10))
    free = np.array([dub_time(i / 10, seconds, pairing) is not None for i in range(len(active))], dtype=bool)
    for a, b in blocked:                            # a start here would put the problem within reach of (a, b)
        free[max(0, int((a - TOLERANCE_SEC - seconds) * 10)):max(0, int(np.ceil((b + TOLERANCE_SEC) * 10)) + 1)] = False
    lo, hi = int(len(active) * 0.15), int(len(active) * 0.85) - need
    starts = [i for i in range(lo, hi + 1) if free[i] and active[i:i + need].mean() >= 0.8]   # empty when it can't fit
    if not starts:
        return None
    pick = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % len(starts)
    return starts[pick] / 10


def apply_defect(name: str, y: np.ndarray, sr: int, start: Optional[float], original: Optional[np.ndarray] = None,
                 seed: int = 0, original_start: Optional[float] = None) -> np.ndarray:
    """The dub's sound with the known problem `name` from `start` (seconds of the dub), as a new array; the original
    voice is taken from `original_start` (seconds of the original; default the same as start)."""
    out = y.astype(np.float32).copy()
    if name == "quieter_3db":
        return out * np.float32(10 ** (-3 / 20))
    if name == "sound_late_1s":
        pad = np.zeros(int(DEFECTS[name]["shift"] * sr), dtype=np.float32)
        return np.concatenate([pad, out])[: len(out)]
    seconds = DEFECTS[name]["seconds"]
    a, b = int(start * sr), min(len(out), int((start + seconds) * sr))
    if name.startswith("silence"):
        out[a:b] = 0.0
    elif name == "original_voice_8s":
        src = original if original is not None else np.zeros_like(out)
        oa = int((start if original_start is None else original_start) * sr)
        piece = src[oa:oa + (b - a)]
        out[a:b] = np.pad(piece, (0, b - a - len(piece)))
    elif name == "loudness_jump_3s":
        out[a:b] = np.clip(out[a:b] * np.float32(10 ** (14 / 20)), -1.0, 1.0)
    elif name == "distortion_3s":
        peak = float(np.max(np.abs(out[a:b]))) or 1.0
        out[a:b] = np.clip(out[a:b] * np.float32(8.0 / peak), -1.0, 1.0)
    elif name == "noise_4s":
        level = float(np.sqrt(np.mean(out[a:b] ** 2))) or 0.05
        out[a:b] = out[a:b] + np.random.default_rng(seed).normal(0, level, b - a).astype(np.float32)
    elif name == "cut_4s":
        out = np.concatenate([out[:a], out[b:]])
    else:
        raise ValueError(f"Unknown defect: {name}")
    return np.clip(out, -1.0, 1.0)


def new_problems(control: list[dict], variant: list[dict]) -> list[dict]:
    """The variant's problem intervals that the control doesn't have (no control interval of the same kind overlaps)."""
    def overlaps(x, y):
        if x.get("start") is None or y.get("start") is None:
            return x.get("start") is None and y.get("start") is None
        return x["start"] <= (y.get("end") or y["start"]) and y["start"] <= (x.get("end") or x["start"])
    return [v for v in variant if not any(c["category"] == v["category"] and overlaps(c, v) for c in control)]


def score(name: str, start: Optional[float], control: list[dict], variant: list[dict]) -> dict:
    """Caught or not, and the false alarms: new problems away from the injected range or of unexpected kinds."""
    spec = DEFECTS.get(name) or HARMLESS[name]
    new = new_problems(control, variant)
    if name in HARMLESS:                              # harmless: every new problem is a false alarm
        return {"defect": name, "caught": None, "false_alarms": new, "new": new}
    if spec["seconds"] is None:                       # the whole dub: caught anywhere, no false alarms by place
        hits = [iv for iv in new if iv["category"] in spec["expect"]]
        return {"defect": name, "caught": bool(hits), "hits": hits, "false_alarms": [], "new": new}
    lo, hi = start - TOLERANCE_SEC, start + spec["seconds"] + TOLERANCE_SEC

    def near(iv):
        if iv.get("start") is None:
            return False
        return iv["start"] <= hi and (iv.get("end") or iv["start"]) >= lo
    hits = [iv for iv in new if iv["category"] in spec["expect"] and near(iv)]
    side = [iv for iv in new if iv not in hits and not near(iv)]
    return {"defect": name, "caught": bool(hits), "hits": hits, "false_alarms": side, "new": new}


def write_variant(dub: str, audio: np.ndarray, out: Path, sr: int = SAMPLE_RATE,
                  cut: Optional[tuple[float, float]] = None) -> Path:
    """A copy of the dub video with this sound. The picture is copied untouched, or, with cut=(start, end), the
    same stretch is removed from the picture too (the sound given is already cut)."""
    import soundfile
    out.parent.mkdir(parents=True, exist_ok=True)
    wav = out.with_suffix(".wav")
    soundfile.write(str(wav), audio, sr, subtype="PCM_16")
    if cut:
        a, b = cut
        picture = ["-filter_complex", f"[0:v]trim=0:{a},setpts=PTS-STARTPTS[v1];[0:v]trim=start={b},"
                   "setpts=PTS-STARTPTS[v2];[v1][v2]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    else:
        picture = ["-map", "0:v:0?", "-c:v", "copy"]
    subprocess.run([FFMPEG_EXE, "-nostdin", "-y", "-loglevel", "error", *LOCAL_INPUT, "-i", dub, *LOCAL_INPUT,
                    "-i", str(wav), *picture, "-map", "1:a:0", "-c:a", "aac", "-b:a", "160k", str(out)],
                   check=True, capture_output=True)
    wav.unlink(missing_ok=True)
    return out


def make_control(dub: str, folder: Path) -> str:
    """Writes control.mp4: the dub with its sound decoded and encoded again, nothing else changed."""
    folder.mkdir(parents=True, exist_ok=True)
    y = load_audio(extract_audio(dub, str(folder / "dub.wav")))
    (folder / "dub.wav").unlink(missing_ok=True)
    return str(write_variant(dub, y, folder / "control.mp4"))


def make_variants(pair_id: str, original: str, dub: str, folder: Path, names: list[str], active: np.ndarray,
                  control: list[dict] = (), pairing: Optional[dict] = None) -> dict:
    """Writes one video per known problem into folder, each where both tracks speak (`active`, per 0.1 s of the
    original) and away from the control's problems of the kinds that would catch it; returns {name: {path, start,
    dub_start}}: start on the original's timeline (as reports are), dub_start where it was written into the dub."""
    folder.mkdir(parents=True, exist_ok=True)
    y = load_audio(extract_audio(dub, str(folder / "dub.wav")))
    o = load_audio(extract_audio(original, str(folder / "original.wav")))
    made = {}
    for name in names:
        spec = DEFECTS.get(name) or HARMLESS[name]
        blocked = [(iv["start"], iv.get("end") or iv["start"]) for iv in control
                   if iv.get("start") is not None and iv["category"] in spec["expect"]]
        start = (None if spec["seconds"] is None
                 else speech_window(active, spec["seconds"], f"{pair_id}:{name}", blocked, pairing))
        if name == "sound_late_1s":
            start = 0.0                                              # the whole dub, from the start
        if spec["seconds"] is not None and start is None:
            made[name] = {"path": None, "start": None,
                          "skipped": "no stretch where both tracks speak long enough, away from the dub's own problems"}
            continue
        at = start if spec["seconds"] is None else dub_time(start, spec["seconds"], pairing)
        seed = int(hashlib.sha1(f"{pair_id}:{name}".encode()).hexdigest(), 16) % (2 ** 32)
        try:
            audio = apply_defect(name, y, SAMPLE_RATE, at, original=o, seed=seed, original_start=start)
            cut = (at, at + spec["seconds"]) if name == "cut_4s" else None
            made[name] = {"path": str(write_variant(dub, audio, folder / f"{name}.mp4", cut=cut)), "start": start,
                          "dub_start": at}
        except Exception as err:                 # this copy only (an audio-only dub can't be cut, for example)
            log.warning("Validation copy %s %s couldn't be made: %s", pair_id, name, err)
            made[name] = {"path": None, "start": start, "skipped": f"couldn't make this copy: {err}"}
    for f in ("dub.wav", "original.wav"):
        (folder / f).unlink(missing_ok=True)
    return made


def summarize(rows: list[dict]) -> dict:
    """Per language pair and known problem: how many were tried, caught, and how many false alarms came with them."""
    table: dict = {}
    for r in rows:
        if r.get("error") or (r.get("caught") is None and r["defect"] not in HARMLESS):
            continue
        key = (r["languages"], r["defect"])
        t = table.setdefault(key, {"languages": r["languages"], "defect": r["defect"], "tried": 0, "caught": 0,
                                   "false_alarms": 0, "runs_with_false_alarms": 0})
        t["tried"] += 1
        t["caught"] += 1 if r.get("caught") else 0
        t["false_alarms"] += len(r["false_alarms"])
        t["runs_with_false_alarms"] += 1 if r["false_alarms"] else 0
    return {"rows": sorted(table.values(), key=lambda t: (t["languages"], t["defect"]))}


def render_text(summary: dict, results: list[dict]) -> str:
    """The validation table as plain text: counts, never percentages of a handful."""
    lines = ["DubEval validation with known problems (counts: caught / tried; false alarms = new problems elsewhere)", ""]
    current = None
    for t in summary["rows"]:
        if t["languages"] != current:
            current = t["languages"]
            lines += ["", f"{current}", f"  {'known problem':20s} {'caught':>8s} {'false alarms':>14s} {'runs with any':>14s}"]
        caught = "-" if t["defect"] in HARMLESS else f"{t['caught']}/{t['tried']}"
        lines.append(f"  {t['defect']:20s} {caught:>8s} {t['false_alarms']:>14d} {t['runs_with_false_alarms']:>11d}/{t['tried']}")
    kinds: dict = {}
    for r in results:
        for iv in r.get("false_alarms") or []:
            kinds[iv["category"]] = kinds.get(iv["category"], 0) + 1
    if kinds:
        lines += ["", "False alarms by kind: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))]
    missed = [r for r in results if r.get("caught") is False]
    if missed:
        lines += ["", "Missed:"] + [f"  {r['pair_id']} {r['defect']} at {r['start']:.1f} s; new instead: "
                                    f"{', '.join(sorted({iv['category'] for iv in r['new']})) or 'nothing'}" for r in missed]
    return "\n".join(lines) + "\n"


def run(sheet: str, out_dir: str, defects: Optional[list[str]] = None, only: Optional[list[str]] = None,
        split: Optional[str] = None, progress: Callable[[str], None] = print) -> dict:
    """Validates every pair of the sheet (or `only` these pair ids, or one split) and writes validation.json/.txt."""
    import json
    from dubeval import batch, pipeline
    from dubeval.report import build_report
    names = defects or [*DEFECTS, *HARMLESS]
    sheet_path = Path(sheet)
    entries = batch.parse_batch_file(sheet_path.read_text(encoding="utf-8"), str(sheet_path.parent))
    out = Path(out_dir)
    rows, controls, pairings = [], {}, {}
    for e in entries:
        pair_id = e["info"].get("pair_id") or f"row{e['line']}"
        part = split_of(e["info"], e["original"])
        if (only and pair_id not in only) or (split and part != split):
            continue
        opts = {k: v for k, v in e["options"].items() if k in ("source_lang", "target_lang", "dub_type")}
        languages = f"{opts.get('source_lang', '?')}>{opts.get('target_lang', '?')}"
        folder = out / "media" / pair_id

        def evaluate(path, e=e, opts=opts):
            return pipeline.evaluate_files(e["original"], path, lambda *a, **k: None, lambda: None,
                                           use_translation_judge=False, include_lipsync=False, **opts)
        progress(f"{pair_id} ({languages}, {part}): evaluating the control")
        try:                                                      # one broken pair never stops the rest
            results = evaluate(make_control(e["dub"], folder))
            control = build_report(results, "en")["problem_intervals"]
            timing = results.get("timing_alignment") or {}
            spans = (timing.get("original_speech") or []) + (timing.get("dubbed_speech") or [])
            active = speech_mask(timing.get("original_speech") or [], timing.get("dubbed_speech") or [],
                                 max([b for _, b in spans] or [0]))
            controls[pair_id] = control
            progress(f"{pair_id}: making the copies")
            pairings[pair_id] = {k: (results.get("pairing") or {}).get(k) for k in
                                 ("same_video", "offset_sec", "applied_offset_sec", "applied_parts", "coverage_pct")}
            made = make_variants(pair_id, e["original"], e["dub"], folder, names, active, control,
                                 results.get("pairing"))
        except Exception as err:
            log.warning("Validation control %s failed: %s", pair_id, err)
            rows.append({"pair_id": pair_id, "languages": languages, "split": part, "defect": "control",
                         "error": str(err)})
            continue
        reports = {"control": control}
        for name, item in made.items():
            if not item.get("path"):
                continue
            progress(f"{pair_id}: evaluating {name}")
            try:
                reports[name] = build_report(evaluate(item["path"]), "en")["problem_intervals"]
            except Exception as err:
                log.warning("Validation run %s %s failed: %s", pair_id, name, err)
                reports[name] = err
        for name in names:
            item, found = made.get(name) or {}, reports.get(name)
            if item.get("skipped") or not isinstance(found, list):
                rows.append({"pair_id": pair_id, "languages": languages, "split": part, "defect": name,
                             "error": item.get("skipped") or str(found)})
                continue
            rows.append({"pair_id": pair_id, "languages": languages, "split": part, "start": item["start"],
                         "dub_start": item.get("dub_start"),
                         **score(name, item["start"], reports["control"], found)})
    summary = summarize(rows)
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation.json").write_text(json.dumps({"summary": summary, "runs": rows, "controls": controls,
                                                    "pairings": pairings}, ensure_ascii=False, indent=1,
                                                    default=str), encoding="utf-8")
    text = render_text(summary, rows)
    (out / "validation.txt").write_text(text, encoding="utf-8")
    return {"summary": summary, "runs": rows, "text": text}
