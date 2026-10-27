"""Problem intervals: every issue in a dub as a time range a person can jump to.

build_intervals(results, tr, lang) collects issues from the speech timing, distortion, loudness, per-window
language, voice clarity and translation checks, then merges overlapping or adjacent ranges of the same
category (gap < 0.5 s), clips them to the video length, rounds to 0.1 s and sorts them by start time.
Issues the translation check flags as probable speech-recognition errors are returned separately and never
count. Pure: no file writes, no network. Thresholds for intervals live here, next to the code that uses them.
"""
import math
from typing import Callable, Optional

import numpy as np

Tr = Callable[..., str]

MERGE_GAP_SEC = 0.5                  # same-category ranges closer than this become one
LINE_POOR_PCT = 30.0                 # a dub line this much longer or shorter than the original's is Poor
LINE_MIN_DIFF_SEC = 0.3              # ...and differences under this many seconds are never a problem
LINE_OVERRUN_POOR_SEC = 1.0          # a dub line running this far into the next one is Poor
MISSING_PART_POOR_SEC = 5.0          # a part of the original missing from the dub: Check, Poor from this long
LONG_SILENCE_SEC = (2.0, 4.0)        # original speaks, dub silent: Check from 2 s, Poor from 4 s
LOUDNESS_JUMP_DB = (10.0, 16.0)      # dub vs original level, after removing the overall offset
LOUDNESS_ACTIVE_DB = -45.0           # both tracks must be louder than this for the loudness comparison
LOUDNESS_MIN_SEC = 1.0               # a level difference must last this long to count
LANG_SOURCE = (0.5, 0.8)             # the original's language heard in the dub: Check from 0.5, Poor from 0.8
LANG_OTHER = (0.8, 0.95)             # any other language: stricter, because Whisper guesses odd languages on noise
LANG_EXPECTED_MAX = 0.2              # ...in both cases only while the expected language stays below this
VOICE_SIG_DROP = (0.6, 1.0)          # dub speech score below the original's in the same window: Check / Poor...
VOICE_OVRL_DROP = (0.5, 0.9)         # ...or its overall score (clean real dubs: at most 0.25 below)
VOICE_CHANGE_DROP = 0.2              # a line this far below the dub's typical voice similarity...
VOICE_CHANGE_MAX = 0.65              # ...and below this (similar voices of two people reach ~0.55)...
VOICE_CHANGE_MEDIAN = 0.45           # ...in a dub that otherwise clones its speakers: another voice on that line
LINE_MATCH_SEC = 1.0                 # a translation issue belongs to the original line starting this close to it
JUDGE_DEFAULT_SEC = 2.0              # length of a translation issue when no transcript line contains it

# Category id -> text key of its label. Ids are stable (JSON); labels follow the report language.
CATEGORIES = {
    "missing_speech": "r.cat.missing",
    "added_speech": "r.cat.added",
    "timing_mismatch": "r.cat.timing",
    "long_silence": "r.cat.long_silence",
    "distortion": "r.cat.distortion",
    "loudness_jump": "r.cat.loudness_jump",
    "wrong_language": "r.cat.wrong_language",
    "mistranslation": "r.cat.mistranslation",
    "names_numbers": "r.cat.name_or_number",
    "unclear_speech": "r.cat.clarity",
    "voice_quality": "r.cat.voice_quality",
    "voice_change": "r.cat.voice_change",
    "missing_in_dub": "r.cat.missing_in_dub",
    "line_length": "r.cat.line_length",
    "line_overrun": "r.cat.line_overrun",
    "meaning_drift": "r.cat.meaning_drift",
    "translation_wording": "r.cat.wording",
}
JUDGE_CATEGORY = {"missing": "missing_speech", "added": "added_speech", "mistranslation": "mistranslation",
                  "name_or_number": "names_numbers", "wording": "translation_wording"}
SEVERITY_RANK = {"check": 1, "poor": 2}


def local_text(value, lang: str) -> str:
    """Text in lang from a {lang: text} dict, falling back to English; plain strings pass through."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or ""
    return str(value or "")


def _item(tr: Tr, start: float, end: float, category: str, severity: str, check: str, description: str) -> dict:
    """One problem interval before merging."""
    return {"start": float(start), "end": float(end), "category": category,
            "category_label": tr(CATEGORIES[category]), "severity": severity, "check": check,
            "check_label": tr(f"r.m.{check}"), "description": description}


def _timing(tr: Tr, ta: dict) -> list[dict]:
    """Stretches where only one track speaks: long silences in the dub, or timing mismatches."""
    out = []
    for m in ta.get("mismatches") or []:
        length = m["end"] - m["start"]
        if m["kind"] == "original_only" and length >= LONG_SILENCE_SEC[0]:
            sev = "poor" if length >= LONG_SILENCE_SEC[1] else "check"
            out.append(_item(tr, m["start"], m["end"], "long_silence", sev, "speech_overlap",
                             tr("r.int.long_silence", sec=f"{length:.1f}")))
        else:
            out.append(_item(tr, m["start"], m["end"], "timing_mismatch", "check", "speech_overlap",
                             tr(f"r.todo.{m['kind']}")))
    return out


def _line_items(tr: Tr, sa: Optional[dict]) -> list[dict]:
    """Lines whose length differs from the original's beyond the band, and lines running into the next one."""
    from dubeval.report import LINE_BAND_PCT, graded_lines
    out = []
    for ln in graded_lines(sa):
        pct, diff = ln["diff_pct"], ln["diff_sec"]
        if abs(pct) > LINE_BAND_PCT and abs(diff) >= LINE_MIN_DIFF_SEC:
            sev = "poor" if abs(pct) > LINE_POOR_PCT else "check"
            key = "r.int.line_long" if pct > 0 else "r.int.line_short"
            out.append(_item(tr, ln["start"], ln["end"], "line_length", sev, "line_length",
                             tr(key, n=ln["n"], d=f"{ln['dub_sec']:.1f}", o=f"{ln['original_sec']:.1f}",
                                pct=f"{abs(pct):.0f}")))
    for ln in (sa or {}).get("lines") or []:
        if ln["overrun_sec"] > 0:
            sev = "poor" if ln["overrun_sec"] >= LINE_OVERRUN_POOR_SEC else "check"
            out.append(_item(tr, ln["end"], ln["end"] + ln["overrun_sec"], "line_overrun", sev, "line_overrun",
                             tr("r.int.line_overrun", n=ln["n"], sec=f"{ln['overrun_sec']:.1f}")))
    return out


def _screen_items(tr: Tr, ms: Optional[dict], judged: bool) -> list[dict]:
    """Lines the offline meaning screen found low, when no judge ran (the judge's own issues are more precise)."""
    from dubeval.report import screen_low_lines
    if judged:
        return []
    return [_item(tr, ln["start"], ln["end"], "meaning_drift", "check", "meaning_screen",
                  tr("r.int.meaning_drift", n=ln["n"], sim=f"{ln['similarity']:.2f}")) for ln in screen_low_lines(ms)]


def _missing_parts(tr: Tr, pr: Optional[dict]) -> list[dict]:
    """Parts of the original whose pictures aren't in the dub (cut or replaced)."""
    if not pr or not pr.get("measured") or pr.get("same_video") is False:
        return []
    return [_item(tr, s, e, "missing_in_dub", "poor" if e - s >= MISSING_PART_POOR_SEC else "check", "coverage",
                  tr("r.int.missing_in_dub", sec=f"{e - s:.1f}")) for s, e in pr.get("missing") or []]


def _distortion(tr: Tr, ac: dict, poor: bool) -> list[dict]:
    """Where the dub's audio clips."""
    sev = "poor" if poor else "check"
    return [_item(tr, s, e, "distortion", sev, "clipping", tr("r.int.clipping"))
            for s, e in ac.get("dubbed_clipping_intervals") or []]


def loudness_jumps(env: dict) -> list[tuple[float, float, float]]:
    """(start, end, dB) where the dub is much louder or quieter than the original, beyond their usual offset."""
    o, d, step = env.get("original_db") or [], env.get("dubbed_db") or [], env.get("step_sec") or 0.25
    n = min(len(o), len(d))
    win = max(1, int(round(LOUDNESS_MIN_SEC / step)))
    if n < 2 * win:
        return []
    o, d = np.array(o[:n], dtype=float), np.array(d[:n], dtype=float)
    active = (o > LOUDNESS_ACTIVE_DB) & (d > LOUDNESS_ACTIVE_DB)
    if active.sum() < 2 * win:
        return []
    diff = d - o - float(np.median((d - o)[active]))
    smooth = np.convolve(np.where(active, diff, 0.0), np.ones(win) / win, mode="same")
    covered = np.convolve(active.astype(float), np.ones(win) / win, mode="same") >= 0.99
    flagged = covered & (np.abs(smooth) >= LOUDNESS_JUMP_DB[0])
    edges = np.diff(np.concatenate([[0], flagged.astype(np.int8), [0]]))
    out = []
    for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
        if (b - a) >= win:
            peak = smooth[a:b][int(np.argmax(np.abs(smooth[a:b])))]
            out.append((a * step, b * step, round(float(peak), 1)))
    return out


def _loudness(tr: Tr, ac: dict) -> list[dict]:
    """Volume jumps in the dub compared with the original."""
    out = []
    for s, e, db in loudness_jumps(ac.get("loudness_envelope") or {}):
        sev = "poor" if abs(db) >= LOUDNESS_JUMP_DB[1] else "check"
        key = "r.int.louder" if db > 0 else "r.int.quieter"
        out.append(_item(tr, s, e, "loudness_jump", sev, "loudness_match", tr(key, db=f"{abs(db):.0f}")))
    return out


def _language(tr: Tr, sr: dict, expected: Optional[str], source: Optional[str], names: dict) -> list[dict]:
    """Windows where the dub sounds like another language, or like the original's (original voice left in)."""
    out = []
    name = lambda code: names.get(code) or _language_name(code)
    for w in sr.get("dubbed_language_windows") or []:
        bands = LANG_SOURCE if source and w["language"] == source else LANG_OTHER
        if not expected or w["language"] == expected or w["probability"] < bands[0] \
                or w.get("expected_probability", 0.0) >= LANG_EXPECTED_MAX:
            continue
        sev = "poor" if w["probability"] >= bands[1] else "check"
        if source and w["language"] == source:
            msg = tr("r.int.original_language", lang=name(source))
        else:
            msg = tr("r.int.other_language", detected=name(w["language"]), expected=name(expected))
        out.append(_item(tr, w["start"], w["end"], "wrong_language", sev, "language", msg))
    return out


def _language_name(code: str) -> str:
    """A readable name for a Whisper language code ("nn" -> "Nynorsk"), or the code itself."""
    from dubeval.asr import language_names
    return language_names().get(code, code).title()


def voice_window_level(w: dict) -> str:
    """good / check / poor for one voice-quality window: how far the dub falls below the original there."""
    sig, ovr = w["original_sig"] - w["dub_sig"], w["original"] - w["dub"]
    if sig >= VOICE_SIG_DROP[1] or ovr >= VOICE_OVRL_DROP[1]:
        return "poor"
    if sig >= VOICE_SIG_DROP[0] or ovr >= VOICE_OVRL_DROP[0]:
        return "check"
    return "good"


def _voice(tr: Tr, vq: Optional[dict]) -> list[dict]:
    """Windows where the dub's voice sounds clearly worse (robotic, distorted) than the original's."""
    out = []
    for w in (vq or {}).get("windows") or [] if (vq or {}).get("measured") else []:
        level = voice_window_level(w)
        if level != "good":
            out.append(_item(tr, w["start"], w["end"], "voice_quality", level, "voice_quality",
                             tr("r.int.voice_quality", dub=f"{w['dub']:.1f}", orig=f"{w['original']:.1f}")))
    return out


def _voice_change(tr: Tr, vs: Optional[dict]) -> list[dict]:
    """Lines whose dub voice doesn't match the original speaker while the rest of the dub does (a wrong voice)."""
    if not (vs or {}).get("measured") or vs["median"] < VOICE_CHANGE_MEDIAN:
        return []
    return [_item(tr, l["start"], l["end"], "voice_change", "check", "voice_similarity",
                  tr("r.int.voice_change", sim=f"{max(0.0, l['similarity']) * 100:.0f}%",
                     median=f"{vs['median'] * 100:.0f}%"))
            for l in vs["lines"]
            if l["similarity"] <= vs["median"] - VOICE_CHANGE_DROP and l["similarity"] < VOICE_CHANGE_MAX]


def _clarity(tr: Tr, sr: dict) -> list[dict]:
    """Stretches of the dub that speech recognition could not understand confidently."""
    return [_item(tr, s["start"], s["end"], "unclear_speech", "check", "clarity", tr("r.todo.unclear", text=s["text"]))
            for s in (sr.get("clarity") or {}).get("unclear_segments", [])]


def _line_end(segments: list[dict], start: float) -> float:
    """End of the original line the issue points at: the line starting closest to it (the judge quotes line start
    times, rounded), else the line containing it, else a default length."""
    segments = segments or []
    near = min(segments, key=lambda s: abs(s["start"] - start), default=None)
    if near and abs(near["start"] - start) <= LINE_MATCH_SEC and near["end"] > start:
        return near["end"]
    for s in segments:
        if s["start"] <= start < s["end"]:
            return s["end"]
    return start + JUDGE_DEFAULT_SEC


def _translation(tr: Tr, tj: Optional[dict], sr: dict, lang: str,
                 spans: Optional[dict] = None) -> tuple[list[dict], list[dict]]:
    """Translation-check issues as intervals (on their line's time span when the judge named the line), and the
    probable speech-recognition errors kept apart."""
    counted, asr = [], []
    if not tj or not tj.get("measured"):
        return counted, asr
    spans = spans or {}
    for i in tj.get("issues") or []:
        category = JUDGE_CATEGORY.get(i.get("type"))
        if category is None:
            continue
        maybe = bool(i.get("may_be_recognition_error"))
        quote = " → ".join(q for q in (f"“{i['original']}”" if i.get("original") else "",
                                       f"“{i['dubbed']}”" if i.get("dubbed") else "") if q)
        kind = i.get("error_type")                 # the rubric's error type, with its suggested translation
        desc = (tr(f"r.tcat.{kind}") + ": " if kind and kind != "no_error" else "") \
            + local_text(i.get("explanation"), lang) + (" " + tr("r.todo.maybe_asr") if maybe else "") \
            + (f" {quote}" if quote else "") \
            + (" " + tr("r.todo.suggested", text=i["ideal_translation"]) if i.get("ideal_translation") else "")
        start = float(i.get("start_sec") or 0.0)
        end = _line_end(sr.get("original_segments"), start)
        if i.get("line") in spans:
            start, end = spans[i["line"]]
        item = _item(tr, start, end, category,
                     "poor" if i.get("severity") == "major" else "check", "translation_check", desc.strip())
        (asr if maybe else counted).append({**item, "asr": True} if maybe else item)
    return counted, asr


def merge_intervals(items: list[dict], length: Optional[float], gap: float = MERGE_GAP_SEC) -> list[dict]:
    """Merges same-category ranges that overlap or are closer than gap, clips to [0, length], rounds to 0.1 s.

    A merged range keeps the worst severity and that item's description; `merged` counts the ranges it holds.
    """
    merged: list[dict] = []
    for item in sorted(items, key=lambda x: (x["category"], x["start"], x["end"])):
        last = merged[-1] if merged else None
        if last and last["category"] == item["category"] and item["start"] - last["end"] < gap:
            last["end"] = max(last["end"], item["end"])
            last["merged"] += 1
            if SEVERITY_RANK[item["severity"]] > SEVERITY_RANK[last["severity"]]:
                last.update(severity=item["severity"], description=item["description"], check=item["check"],
                            check_label=item["check_label"])
        else:
            merged.append({**item, "merged": 1})
    out = []
    for m in merged:
        start, end = _clip(m["start"], m["end"], length)
        out.append({**m, "start": start, "end": end})
    return sorted(out, key=lambda x: (x["start"], x["end"], x["category"]))


def _clip(start: float, end: float, length: Optional[float]) -> tuple[float, float]:
    """A range clipped to the video and rounded to 0.1 s, at least 0.1 s long."""
    hi = length if length and length > 0 else math.inf
    s = min(max(0.0, start), hi)
    e = min(max(s, end), hi)
    s, e = round(s, 1), round(e, 1)
    if e - s < 0.1:
        e = round(min(hi, s + 0.1), 1)
        s = round(max(0.0, e - 0.1), 1) if e - s < 0.1 else s
    return s, e


def total_seconds(intervals: list[dict]) -> float:
    """Seconds of the video covered by at least one interval (overlaps across categories count once)."""
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted((i["start"], i["end"]) for i in intervals):
        if cur_e is None or s > cur_e:
            total += (cur_e - cur_s) if cur_e is not None else 0.0
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    total += (cur_e - cur_s) if cur_e is not None else 0.0
    return round(total, 1)


def video_length(r: dict) -> Optional[float]:
    """The dub's length (what the intervals point into), falling back to the original's."""
    ac = r.get("acoustic_metrics") or {}
    return ac.get("dubbed_duration_sec") or ac.get("original_duration_sec") or None


def build_intervals(r: dict, tr: Tr, lang: str, clipping_poor: bool = False, dub: Optional[str] = None,
                    language_names: Optional[dict] = None) -> dict:
    """Every problem interval of one dub, the probable recognition errors, and the seconds the problems cover."""
    from dubeval.evaluate import base_lang, whisper_language
    ac, sr = r.get("acoustic_metrics") or {}, r.get("speech_recognition") or {}
    p, meta = r.get("pipeline") or {}, r.get("metadata") or {}
    expected = whisper_language(p.get("target_language_code") or meta.get("target_language"))
    share = p.get("input") or p.get("share") or {}
    source = whisper_language(share.get("source_language_code") or meta.get("detected_source_language"))
    names = {expected: p.get("target_language_name"), source: share.get("source_language_name"),
             **(language_names or {})}
    names = {base_lang(k): v for k, v in names.items() if k and v}
    tj = r.get("translation_judge") or {}
    spans = {ln["n"]: (ln["start"], ln["end"]) for ln in (r.get("segment_alignment") or {}).get("lines") or []}
    from dubeval.report import speech_problem
    problem = speech_problem(r)
    trusted = not problem or problem["kind"] != "unrecognized"     # otherwise speech-based ranges are noise
    counted, asr = _translation(tr, tj, sr, lang, spans) if trusted else ([], [])
    counted += _distortion(tr, ac, clipping_poor) + _loudness(tr, ac) + _voice(tr, r.get("voice_quality")) \
        + _voice_change(tr, r.get("voice_similarity")) + _missing_parts(tr, r.get("pairing"))
    if trusted:
        from dubeval.report import subtitles_confirm_language
        languages = _language(tr, sr, expected, source, names)
        if subtitles_confirm_language(r) is not None:
            # The subtitles confirm the dub's language: other languages heard in a window are recognition noise; the
            # original's language heard there is still worth reporting (the original voice left in).
            languages = [i for i in languages if source and names.get(source) and names[source] in i["description"]]
        counted += _screen_items(tr, r.get("meaning_screen"), bool(tj.get("measured"))) \
            + _timing(tr, r.get("timing_alignment") or {}) + languages \
            + _clarity(tr, sr) + _line_items(tr, r.get("segment_alignment"))
    else:
        # The original's language left in the dub is still worth reporting; other languages are recognition noise.
        counted += [i for i in _language(tr, sr, expected, source, names)
                    if source and names.get(source) and names[source] in i["description"]]
    length = video_length(r)
    intervals = merge_intervals(counted, length)
    asr = sorted(({**a, **dict(zip(("start", "end"), _clip(a["start"], a["end"], length)))} for a in asr),
                 key=lambda x: x["start"])
    for i in intervals + asr:
        i["dub"] = dub
    return {"intervals": intervals, "possible_asr_errors": asr, "problem_seconds": total_seconds(intervals)}
