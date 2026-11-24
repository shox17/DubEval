"""The quality report: turns raw measurements into verdicts a person can act on.

build_report(results, lang) gives every measure a level (good / check / poor / info / not_measured), a
plain-language explanation and how it is graded, lists timestamped things to check, and derives an overall
verdict, all in the chosen interface language (texts live in dubeval/report_text.py). render_text and render_html
present the same report. Pure: no file writes, no network.
"""
import hashlib
import html
import math
import os
import textwrap
from pathlib import Path
from typing import Callable, Optional

from dubeval.evaluate import base_lang, whisper_language
from dubeval.i18n import DEFAULT_UI_LANGUAGE, t as i18n_t
from dubeval.intervals import VOICE_CE_DROP, VOICE_FLOOR, VOICE_KNOWN, VOICE_OVRL_DROP, VOICE_PQ_DROP, VOICE_SIG_DROP, build_intervals, group_moments, total_seconds, local_text as _local,     voice_window_levels

# Thresholds, in one place so the report can print exactly what it applied.
SAME_VIDEO_PCT = (60, 25)                # matching frames at the best shift (bands in dubeval/pairing.py)
COVERAGE_PCT = (98.0, 90.0)              # share of the original found in the dub
LENGTH_PCT = (5.0, 15.0)                 # |dub - original| / original
LOUDNESS_DB = (3.0, 10.0)                # |20 log10(rms ratio)|: a person graded a dub 5.1 dB off Good, and none of
                                         # the graded Poor dubs was off by more than 1.7 dB (2026-11-01; was 2 / 4).
                                         # Poor moved 6 → 10 (owner's decision, 2026-11-24): a dub 6.6 dB louder,
                                         # Poor for that alone, was graded Needs review
SILENCE_PTS = (5.0, 15.0)                # extra silence in the dub, percentage points
CLIPPING_PCT = (0.01, 0.1)               # share of samples at full scale
# Speaking pace per dub language: chars/s for ko/ja/zh, words/s for en/es. A language without a rule is not graded.
SPEECH_RATE = {"ko": (7.5, 9.0), "ja": (8.5, 10.5), "zh": (6.0, 7.5), "en": (3.2, 3.8), "es": (3.5, 4.2)}
CLARITY_PCT = (90.0, 70.0)               # speech time Whisper recognised confidently
LANGUAGE_PROB = 0.5                      # below this the language guess is uncertain
UNRECOGNIZED_PROB = 0.8                  # a third language heard with less confidence is a recognition failure
# The dub's transcript (made in the dub's language) matches its subtitle file at least this well (1 − character error
# rate): the dub is in that language whatever recognition guessed from the sound. Set from one real EN→UZ Perso dub
# (0.61 against its Uzbek subtitles; unrelated text 0.17-0.25); a first guess to check on more pairs.
SUBTITLE_MATCH = 0.45
RECOGNIZER_NAMES = {"faster-whisper": "faster-whisper", "openai-whisper": "OpenAI Whisper"}
SOUND_SYNC_SEC = (0.3, 0.6)              # the dub's sound behind/ahead of its picture: Check from 0.3 s, Poor from 0.6
LINE_BAND_PCT = 15.0                     # a dub line within ±this % of the original line's length fits...
LINE_MIN_DIFF_SEC = 0.6                  # ...or within this many seconds: word timings move by about that much when
                                         # the sound changes slightly (validation: 0.3 s let short lines flip)
LINE_FIT_SHARE = (90.0, 50.0)            # share of lines that fit: Good from the first, Check from the second, so Poor
                                         # needs most lines off, as meaning does (the second was 70 until 2026-11-02: the one
                                         # graded dub it made Poor, 4 of 10 lines off, a person graded Needs review)
LINE_OVERRUN_SHARE = 10.0                # lines running into the next one: Check up to this share, Poor above
LINE_POOR_MIN = 3                        # Poor needs at least this many lines off (one line of two isn't Poor)
OVERLAP_PCT = (75.0, 45.0)               # speech-timing overlap; a real Perso EN→KO dub scores ~81%. Poor moved
                                         # 55 → 45 (owner's decision, 2026-11-24, on 39 graded dubs): every dub at
                                         # 45-55% (47-54%) was Needs review on timing to the reviewer, none Poor
SCRIPT_PCT = (80.0, 50.0)                # accuracy against a script
MEANING_SCORE = (4, 3)                   # LLM judge, 1-5
# The translation rubric (translation_judge.CRITERIA, each line 1-10): a line at or below RUBRIC_FLAG has a problem worth a
# look; meaning (semantic accuracy) at or below RUBRIC_POOR is a serious one. The other four criteria only reach Check
# until labelled dubs show they should grade Poor.
RUBRIC_FLAG = 6
RUBRIC_POOR = 4
RUBRIC_POOR_LINES = 3                    # meaning is Poor with this many serious lines, or when most lines are serious;
                                         # one or two are Check (labelled dubs: a cut countdown or two swapped sentences
                                         # made dubs Poor that the reviewer graded Good for meaning)
# Voice similarity (typical line, 0-1), set on 2026-11-13 from 10 real dubs and 363 line pairs of different videos
# (docs/validation.md): cloned dubs scored 0.45-0.61, dubs with another voice 0.08-0.24, two different people under
# VOICE_STRANGERS in 99% of pairs (0.34 at most). Never Poor: a new voice can be deliberate.
VOICE_SAME = 0.40                        # from this: the original speaker's voice (Good)
VOICE_DIFFERENT = 0.30                   # under this: another voice (Needs review); between: partly alike
VOICE_STRANGERS = 0.25                   # what two different people score under: said in the texts, grades nothing
LIP_OFFSET_MS = 120                      # lip sync: lips that follow the sound this far off are reported as late/early
LIP_SYNC_PCT = (90, 30)                  # lip sync: share of checked moments that line up: Good from 90%, Poor at 30% or
                                         # less, Check between (owner's decision, 2026-11-10; tested on one real dub)
# Voice-quality window bands (how far the dub may fall below the original) are in dubeval/intervals.py.

# How sure DubEval is (sure_of). When the speech measures rest on little or unclear speech, nothing but the measures in
# SURE_ANYWAY can make the dub Poor; when the dub's background was replaced, silence and loudness can't; when the dub's
# words couldn't be recognized, it is never Good. Set on 19 dubs a person graded (docs/validation.md).
SURE_SPEECH_SHARE = 35.0                 # the original speaks at least this % of the video...
SURE_SPEECH_SEC = 10.0                   # ...for at least this long...
SURE_CLARITY = 90.0                      # ...and the dub is recognized confidently at least this % of its speech time
BACKGROUND_REPLACED = 2.0                # the dub's background is this much cleaner (DNSMOS BAK, 1-5) than the original's
WEAK_RECOGNITION_PCT = 10.0              # a note under the verdict when the speech model read more than this % of
                                         # characters wrong in a side's language on test sentences
                                         # (languages.RECOGNITION_ERRORS); it changes no level
SURE_ANYWAY = ("clipping", "same_video", "coverage", "file_check", "sound_sync", "speech_found")

LEVELS = ("good", "check", "poor")
# The quality score (0-100, owner's decisions 2026-11-20 and 2026-11-21): a summary shown next to the verdict, never
# instead of it, and never part of the compare decision rule. Each graded check scores SCORE_POINTS by level; a section
# scores the average of its checks; the score is the sections' weighted sum. The video file must pass and has no
# weight. The number is the one worked out: no cap held a Needs review dub at 89 any more (its 97 had to be explained as
# "97 before the limit"); only a dub with every check Good scores 100. In a Poor verdict a Poor result costs a fixed
# amount by how serious it is (POOR_COSTS, POOR_SEVERITY), whatever its share: one Poor check is often a dealbreaker
# its weight doesn't show (a crackling dub kept 97).
# A check that wasn't measured is one of three kinds (_absent): it doesn't apply to this dub ("na": left out, its points
# shared), it couldn't be measured ("missing": left out and shared too, but the score says how much of what applies it
# covers, and is provisional under COVERAGE_MIN), or the dub itself made it impossible ("dub": counts as 0, never
# shared; a dub without speech scored 90+ on the checks that still passed). The weights are reasoned, not measured:
# check them against people's grades before relying on a number.
SCORE_WEIGHTS = {"translation": 30, "alignment": 25, "speech": 15, "timing_audio": 15, "pairing": 10, "lipsync": 5}
SCORE_POINTS = {"good": 100, "check": 50, "poor": 0}   # "check": only for a check with no number to place (see _scale)
SCORE_CHECK_MAX = 99                    # a Needs review check never scores as much as a Good one
# What a Poor result costs at the least, in a Poor verdict, by how serious it is (2026-11-22, as translation QA grades
# errors critical / major / minor). Three levels instead of a number per check: the evidence is thin, so each check is
# put in a level by a stated reason, and a level's number can move when graded dubs show it should.
#   unusable: nothing deliverable (no speech in the dub, the wrong language, another video, a file without sound or
#             that can't be read). The reviewer graded the dub without speech and the wrong-language dub Poor.
#   serious:  a viewer notices and it must be fixed (the default: translation, timing, lines, lip sync, sound sync,
#             distortion, voice quality, clarity, pace, length, coverage). Translation stays here, not higher: the
#             reviewer agreed with 4 of its 5 Poor results on the test dubs, but on p019 the checker was wrong.
#   minor:    the mix can fix it (loudness, silence). The reviewer graded a dub 5.1 dB off Good, and silence goes Poor
#             when a dub's background music was removed.
POOR_COSTS = {"unusable": 100, "serious": 40, "minor": 20}
POOR_SEVERITY = {"speech_found": "unusable", "language": "unusable", "same_video": "unusable", "file_check": "unusable",
                 "loudness_match": "minor", "silence": "minor"}         # every other check that can be Poor: serious
POOR_COST = POOR_COSTS["serious"]
# Rows that only inform (never graded): measured or not, they never count, nor lower the coverage.
INFO_ONLY = ("speech_offsets", "time_shift")
COVERAGE_MIN = 80                       # % of what applies that must be measured, or the score is provisional
# Under this % there is no score at all: 3 test dubs whose language wasn't recognized had 26-30% measured and showed
# "99 / 100 (provisional)", a number built on a quarter of the checks. A dub without a translation checker (70%) keeps one.
SCORE_MIN_COVERAGE = 50
# Speech checks a dub without any speech can't have: not measured for that reason counts as 0 ("dub").
DUB_SPEECH_CHECKS = ("clarity", "speech_overlap", "line_length", "line_overrun", "speech_rate",
                     "translation_check", "meaning", "numbers", "language", "voice_quality", "voice_similarity")
# A section counts only when this check of it was graded: without the translation check, the offline meaning screen and
# the numbers check (which can't be Poor, or only notice a changed number) would grade Translation's 30% on their own and
# lift the score; the score is then provisional and says why (owner's decision, 2026-11-20).
SCORE_REQUIRES = {"translation": ("translation_check", "meaning")}     # "meaning": results saved before the rubric
HEADLINE_NAMES = 3                      # measures the headline names before "and N more"
SKIP_BANNER_MIN = 3                      # this many checks skipped for one reason are announced at the top of the result
# The measure a moment is counted under in the headline, when it isn't the one named in the moment's "check".
MOMENTS_OF = {"translation_check": "meaning"}     # results saved before the translation check was one row
# Moments a check that passed still lists: each is a local event its row's number doesn't measure (the dub silent
# where the original speaks, a stretch in the original's language, a jump in volume). On the 20 test dubs one Good
# language row hid 10 s of the original's English; the reviewer voted both loudness jumps real.
LISTED_WHEN_PASSED = frozenset({"long_silence", "wrong_language", "loudness_jump"})
ICONS = {"good": "✅", "check": "⚠️", "poor": "❌", "info": "ℹ️", "not_measured": "·"}
Tr = Callable[..., str]


def fmt_time(sec: Optional[float]) -> str:
    """Seconds as mm:ss.s, or an empty string."""
    if sec is None:
        return ""
    m, s = divmod(max(0.0, float(sec)), 60)
    return f"{int(m):02d}:{s:04.1f}"


def _band_max(value: float, bands: tuple[float, float]) -> str:
    """Level for a value where lower is better."""
    return "good" if value <= bands[0] else "check" if value <= bands[1] else "poor"


def _band_min(value: float, bands: tuple[float, float]) -> str:
    """Level for a value where higher is better."""
    return "good" if value >= bands[0] else "check" if value >= bands[1] else "poor"


def _lname(tr: Tr, code: Optional[str], start: bool = False) -> str:
    """A language's name in the report's language ("es" -> "스페인어"), not Whisper's English one; start: capitalized."""
    from dubeval.languages import display_name
    return display_name(code or "", tr("r.lang_code"), start)


def _cap(text: str) -> str:
    """The first letter capitalized (a language name that begins a row: "espanhol" -> "Espanhol")."""
    return text[:1].upper() + text[1:]


def _pl(tr: Tr, key: str, n: int, **params) -> str:
    """The singular (key_one) or plural (key_many) text for a count."""
    return tr(f"{key}_{'one' if n == 1 else 'many'}", n=n, **params)


def _metric(tr: Tr, mid: str, level: str, message: str, value=None, display: str = "", graded: str = "", *,
            points: Optional[float] = None) -> dict:
    """One report row. value is None when not measured. points: where the result sits between the Poor limit (0) and
    the Good limit (100), what the quality score gives it when it needs review (_check_points)."""
    return {"id": mid, "label": tr(f"r.m.{mid}"), "level": level, "value": value,
            "display": display or ("—" if value is None else str(value)), "message": message, "thresholds": graded,
            "score_points": points}


def _scale(value: float, good: float, poor: float) -> float:
    """Where a value sits from the Poor limit (0) to the Good limit (100), either way round (lower or higher better)."""
    return round(min(100.0, max(0.0, 100 * (value - poor) / (good - poor))), 1)


def _share_ok(ok: int, total: int) -> Optional[float]:
    """The share of lines (or stretches) without a problem, as points; None when there are none."""
    return round(100 * ok / total, 1) if total else None


def _na(tr: Tr, mid: str, reason: str, short: str = "") -> dict:
    """A measure that couldn't be measured, with the reason (short: a few words for the row; else nothing, since a
    dash there said nothing and the reason is in the row and the Not measured list)."""
    return {**_metric(tr, mid, "not_measured", reason), "display": short}


# ---------------- sections ----------------
def _pairing(tr: Tr, pr: Optional[dict]) -> list[dict]:
    """Same video, the dub's time shift, and how much of the original the dub contains."""
    from dubeval.pipeline import MIN_APPLIED_OFFSET
    graded = tr("r.g.same_video", good=SAME_VIDEO_PCT[0], check=SAME_VIDEO_PCT[1])
    if not pr or not pr.get("measured"):
        return [_na(tr, "same_video", tr("r.pair.na"))]
    pct = round((pr.get("picture_match") or 0) * 100)
    cov = pr.get("coverage_pct")
    shown = max(pct, round(cov or 0))
    if pr.get("evidence") == "sound":
        level = "good" if pr["same_video"] else "check"
        rows = [_metric(tr, "same_video", level, tr("r.pair.same_sound" if pr["same_video"] else "r.pair.unsure_sound"),
                        pr["same_video"], tr("r.pair.disp_sound") if pr["same_video"] else "—", graded)]
    else:
        level = {True: "good", None: "check", False: "poor"}[pr["same_video"]]
        key = {"good": "r.pair.same", "check": "r.pair.unsure", "poor": "r.pair.different"}[level]
        rows = [_metric(tr, "same_video", level, tr(key, pct=shown), pr["same_video"],
                        tr("r.pair.disp_match", pct=shown), graded)]
    offset, applied = pr.get("offset_sec") or 0.0, pr.get("applied_offset_sec") or 0.0
    parts = pr.get("parts") or []
    if pr.get("applied_parts") and len(parts) > 1:
        shifts = ", ".join(f"{p['offset_sec']:+.2f}" for p in parts)
        msg, disp = tr("r.pair.shift_parts", shifts=shifts), tr("r.pair.disp_parts", n=len(parts))
        if pr.get("drift"):
            low, high = f"{pr['drift']['low_sec']:+.1f}", f"{pr['drift']['high_sec']:+.1f}"
            msg, disp = tr("r.pair.shift_drift", low=low, high=high), tr("r.pair.disp_drift", low=low, high=high)
    elif applied:
        msg = tr("r.pair.shift_later" if applied > 0 else "r.pair.shift_earlier", sec=f"{abs(applied):.2f}")
        disp = tr("r.pair.disp_corrected", sec=f"{applied:+.2f}")
    elif abs(offset) >= 0.01 and pr["same_video"] is not False:
        msg, disp = tr("r.pair.shift_small", sec=f"{abs(offset):.2f}"), f"{offset:+.2f} s"
    else:
        msg, disp = tr("r.pair.shift_none"), tr("r.pair.disp_none")
    rows.append(_metric(tr, "time_shift", "info", msg, applied, disp, tr("r.g.time_shift", min=MIN_APPLIED_OFFSET)))
    rows += _sound_sync(tr, pr.get("sound_sync"))
    if cov is None:
        rows.append(_na(tr, "coverage", tr("r.pair.cov_na")))
        return rows
    missing = pr.get("missing") or []
    msg = tr("r.pair.cov_full") if not missing else _pl(
        tr, "r.pair.cov_missing", len(missing), sec=f"{sum(e - s for s, e in missing):.1f}")
    if pr.get("steady_offset") is False and not pr.get("applied_parts"):
        msg += " " + tr("r.pair.cut")
    level = "good" if cov >= COVERAGE_PCT[0] else "check" if cov >= COVERAGE_PCT[1] else "poor"
    rows.append(_metric(tr, "coverage", level, msg, cov, tr("r.pair.disp_coverage", pct=f"{cov:.0f}"),
                        tr("r.g.coverage", good=f"{COVERAGE_PCT[0]:.0f}", check=f"{COVERAGE_PCT[1]:.0f}"),
                        points=_scale(cov, *COVERAGE_PCT)))
    return rows


def sound_sync_level(sync: Optional[dict]) -> Optional[str]:
    """good / check / poor for the dub's sound against its picture; None when not measured."""
    if not sync or not sync.get("measured"):
        return None
    shift = abs(sync["shift_sec"])
    return "poor" if shift >= SOUND_SYNC_SEC[1] else "check" if shift >= SOUND_SYNC_SEC[0] else "good"


def _sound_sync(tr: Tr, sync: Optional[dict]) -> list[dict]:
    """Is the dub's sound in step with its own picture (the background it keeps from the original as the clock)."""
    if sync is None:
        return []                                        # results from before this check existed
    from dubeval.pairing import SYNC_MIN_SEC
    level = sound_sync_level(sync)
    if level is None:
        key = "r.sync.na_short" if sync.get("reason") == "short" else "r.sync.na_shared"
        # a dub that replaces the background, or a clip too short: nothing to measure the sound against (not a gap)
        return [{**_na(tr, "sound_sync", tr(key, sec=f"{SYNC_MIN_SEC:g}")), "absent": "na"}]
    shift = sync["shift_sec"]
    msg = tr("r.sync.good") if level == "good" else tr("r.sync.late" if shift > 0 else "r.sync.early",
                                                         sec=f"{abs(shift):.1f}")
    return [_metric(tr, "sound_sync", level, msg, shift, tr("r.sec", sec=f"{shift:+.2f}"),
                    tr("r.g.sound_sync", check=f"{SOUND_SYNC_SEC[0]:g}", poor=f"{SOUND_SYNC_SEC[1]:g}"),
                    points=_scale(abs(shift), *SOUND_SYNC_SEC))]


def _timing_audio(tr: Tr, ac: dict, sr: dict, lang: str, lang_name: str) -> list[dict]:
    """Length, loudness, silence, distortion and speaking pace."""
    rows = []
    od, dd = ac["original_duration_sec"], ac["dubbed_duration_sec"]
    if od:
        pct = abs(dd - od) / od * 100
        level = _band_max(pct, LENGTH_PCT)
        diff = dd - od
        if abs(diff) < 0.05:
            msg = tr("r.length.same", dub=f"{dd:.1f}", orig=f"{od:.1f}")
        else:
            way = "longer" if diff > 0 else "shorter"
            msg = tr(f"r.length.{way}_{'ok' if level == 'good' else 'bad'}", diff=f"{abs(diff):.1f}", pct=f"{pct:.1f}")
        rows.append(_metric(tr, "length_match", level, msg, round(pct, 1),
                            tr("r.sec_pct", sec=f"{diff:+.2f}", pct=f"{pct:.1f}"),
                            tr("r.g.length", good=f"{LENGTH_PCT[0]:g}", check=f"{LENGTH_PCT[1]:g}"),
                            points=_scale(pct, *LENGTH_PCT)))
    else:
        rows.append(_na(tr, "length_match", tr("r.length.na")))

    ratio = ac.get("rms_ratio")
    if ratio:
        db = round(20 * math.log10(ratio), 1) + 0.0  # + 0.0 turns -0.0 into 0.0
        level = _band_max(abs(db), LOUDNESS_DB)
        if abs(db) < 0.5:
            msg = tr("r.loud.same")
        else:
            way = "louder" if db > 0 else "quieter"
            msg = tr(f"r.loud.{way}_{'ok' if level == 'good' else 'bad'}", db=f"{abs(db):.1f}")
        rows.append(_metric(tr, "loudness_match", level, msg, db, f"{db:+.1f} dB",
                            tr("r.g.loudness", good=f"{LOUDNESS_DB[0]:g}", check=f"{LOUDNESS_DB[1]:g}"),
                            points=_scale(abs(db), *LOUDNESS_DB)))
    else:
        rows.append(_na(tr, "loudness_match", tr("r.loud.na")))

    extra = (ac["dubbed_silence_ratio"] - ac["original_silence_ratio"]) * 100
    level = _band_max(max(0.0, extra), SILENCE_PTS)
    before, after = f"{ac['original_silence_ratio']:.1%}", f"{ac['dubbed_silence_ratio']:.1%}"
    msg = (tr("r.silence.ok", orig=before, dub=after) if level == "good"
           else tr("r.silence.bad", pts=f"{extra:.0f}", orig=before, dub=after))
    rows.append(_metric(tr, "silence", level, msg, round(extra, 1), tr("r.silence.display", dub=after, orig=before),
                        tr("r.g.silence", good=f"{SILENCE_PTS[0]:g}", check=f"{SILENCE_PTS[1]:g}"),
                        points=_scale(max(0.0, extra), *SILENCE_PTS)))

    clip = ac.get("dubbed_clipping_pct")
    if clip is not None:
        level = _band_max(clip, CLIPPING_PCT)
        msg = tr("r.clip.ok") if level == "good" else tr("r.clip.bad", pct=f"{clip:.2f}")
        rows.append(_metric(tr, "clipping", level, msg, clip, tr("r.clip.none") if clip == 0 else f"{clip:.3f}%",
                            tr("r.g.clipping", good=f"{CLIPPING_PCT[0]:g}", check=f"{CLIPPING_PCT[1]:g}"),
                            points=_scale(clip, *CLIPPING_PCT)))

    if ac.get("noise_envelope") is not None:
        from dubeval.intervals import NOISE_FLOOR_RISE_DB, NOISE_MIN_SEC, noise_moments
        found = len(noise_moments(ac))
        rows.append(_metric(tr, "noise", "check" if found else "good", _pl(tr, "r.noise.check", found) if found else tr("r.noise.ok"),
                            found, _pl(tr, "r.noise.display", found), tr("r.g.noise", rise=f"{NOISE_FLOOR_RISE_DB:g}", sec=f"{NOISE_MIN_SEC:g}")))

    rows.append(_pace(tr, sr.get("dubbed_speech_rate"), lang, lang_name))
    return rows


def _pace(tr: Tr, rate: Optional[dict], lang: str, lang_name: str) -> dict:
    """Speaking pace of the dub, graded only for languages with a pace rule (SPEECH_RATE)."""
    if not rate:
        return _na(tr, "speech_rate", tr("r.no_speech"))
    unit = tr(f"unit.{rate['unit']}")
    shown = f"{rate['value']:.1f} {unit}"
    bands = SPEECH_RATE.get(base_lang(lang))
    if not bands:
        return _na(tr, "speech_rate", tr("r.pace.no_rule", lang=lang_name or lang or "?", rate=shown))
    level = _band_max(rate["value"], bands)
    return _metric(tr, "speech_rate", level, tr(f"r.pace.{level}", rate=shown), rate["value"], shown,
                   tr("r.g.pace", good=f"{bands[0]:g}", check=f"{bands[1]:g}", unit=unit),
                   points=_scale(rate["value"], *bands))


def _voice(tr: Tr, vq: Optional[dict]) -> dict:
    """Voice quality of the dub against the original at the same moments, by the model that scored it (Audiobox
    Aesthetics with its download, else DNSMOS)."""
    if not vq:
        return _na(tr, "voice_quality", tr("r.vq.old"))
    if not vq.get("measured"):
        return _na(tr, "voice_quality", tr(vq.get("reason_key") or "r.vq.error"))
    dub, orig, diff = vq["dub"], vq["original"], vq["difference"]
    audiobox = vq.get("scorer") == "audiobox"            # else DNSMOS (also every result saved before the choice)
    if not audiobox and orig < VOICE_FLOOR:
        return _na(tr, "voice_quality", tr("r.vq.too_noisy", orig=f"{orig:.1f}"))
    levels = voice_window_levels(vq)
    level = "poor" if "poor" in levels else "check" if "check" in levels else "good"
    flagged = sum(1 for lv in levels if lv != "good")
    shown = tr("r.vq.display", dub=f"{dub:.1f}", orig=f"{orig:.1f}", scale=vq.get("scale") or 5) \
        + (f" · {flagged}/{len(levels)}" if flagged else "")
    msg = tr("r.vq.good", dub=f"{dub:.1f}", orig=f"{orig:.1f}", scale=vq.get("scale") or 5) if level == "good" else \
        _pl(tr, f"r.vq.{level}", flagged, total=len(levels))
    graded = tr("r.g.vq_pq", drop=f"{VOICE_PQ_DROP[0]:g}", poor=f"{VOICE_PQ_DROP[1]:g}", second=f"{VOICE_CE_DROP:g}") \
        if audiobox else tr("r.g.vq", sig=f"{VOICE_SIG_DROP[0]:g}", ovr=f"{VOICE_OVRL_DROP[0]:g}",
                            sig_poor=f"{VOICE_SIG_DROP[1]:g}", ovr_poor=f"{VOICE_OVRL_DROP[1]:g}", floor=f"{VOICE_FLOOR:g}")
    return _metric(tr, "voice_quality", level, msg, diff, shown, graded,
                   points=_share_ok(len(levels) - flagged, len(levels)))


def _similarity(tr: Tr, vs: Optional[dict]) -> dict:
    """Whether the dub speaks with the original speaker's voice: same voice (Good), another voice or partly alike
    (Needs review, never Poor: a new voice may be chosen), or not graded when the model can't recognise the original's
    own speakers (original_self under VOICE_KNOWN) and the dub's similarity isn't high either."""
    if not vs:
        return _na(tr, "voice_similarity", tr("r.vq.old"))
    if not vs.get("measured"):
        row = _na(tr, "voice_similarity", tr(vs.get("reason_key") or "r.vs.error"))
        if vs.get("reason_key") in ("r.vs.not_compared_human", "r.vs.not_compared_stock"):
            row["absent"] = "na"          # another voice on purpose: the check isn't part of this dub's job
        return row
    med, n, own = vs["median"], len(vs["lines"]), vs.get("original_self")
    pc = lambda x: f"{max(0.0, x) * 100:.0f}%"
    say = {"sim": pc(med), "n": n, "same": pc(VOICE_SAME), "strangers": pc(VOICE_STRANGERS)}
    graded = tr("r.g.vs", same=pc(VOICE_SAME), different=pc(VOICE_DIFFERENT), strangers=pc(VOICE_STRANGERS),
                known=pc(VOICE_KNOWN))
    if med >= VOICE_SAME:                    # a match this high is itself the proof: strangers never reached it
        return _metric(tr, "voice_similarity", "good", tr("r.vs.good", **say), med, tr("r.vs.display", **say), graded)
    if own is not None and own < VOICE_KNOWN:
        # the model can't match this video's own speakers with themselves, so a low number says nothing about the dub
        return _na(tr, "voice_similarity", tr("r.vs.unsure", own=pc(own), known=pc(VOICE_KNOWN), **say),
                   tr("r.vs.cant_tell"))
    kind = "different" if med < VOICE_DIFFERENT else "partly"
    known = tr("r.vs.known", own=pc(own)) if own is not None else ""     # results saved before original_self
    return _metric(tr, "voice_similarity", "check", (tr(f"r.vs.{kind}", **say) + " " + known).strip(), med,
                   tr("r.vs.display", **say), graded)


def _speech(tr: Tr, sr: dict, lang: str, lang_name: str, vq: Optional[dict] = None,
            vs: Optional[dict] = None, subs_match: Optional[float] = None) -> list[dict]:
    """Right language, how clearly the voice is recognised, and script accuracy when a script exists.

    subs_match: the dub's match with its subtitle file when it confirms the language (subtitles_confirm_language)."""
    rows = []
    expected = whisper_language(lang)
    detected, prob = sr.get("dubbed_language_detected"), sr.get("dubbed_language_probability")
    if not expected:
        rows.append(_na(tr, "language", tr("r.lang.unsupported", lang=lang_name)))
    elif detected is None:
        rows.append(_na(tr, "language", tr("r.no_speech")))
    else:
        sure = f"{prob:.0%}" if prob is not None else "?"
        if detected == expected:
            level = "good" if (prob or 0) >= LANGUAGE_PROB else "check"
            msg = tr(f"r.lang.{level}", lang=lang_name, prob=sure)
            shown = tr("r.lang.display", lang=_cap(lang_name), prob=sure)
        else:
            level, msg = "poor", tr("r.lang.poor", lang=lang_name, detected=_lname(tr, detected))
            shown = tr("r.lang.display", lang=_lname(tr, detected, start=True), prob=sure)
        graded = tr("r.g.language", prob=f"{LANGUAGE_PROB:.0%}")
        if subs_match is not None and level != "good":
            match = f"{subs_match:.0%}"
            level, msg = "good", tr("r.lang.subs", lang=lang_name, match=match, detected=_lname(tr, detected))
            shown = tr("r.lang.subs_display", lang=_cap(lang_name), match=match)
        if subs_match is not None:
            graded = tr("r.g.language_subs", prob=f"{LANGUAGE_PROB:.0%}", match=f"{SUBTITLE_MATCH:.0%}")
        rows.append(_metric(tr, "language", level, msg, detected, shown, graded))

    clarity = sr.get("clarity") or {}
    pct = clarity.get("confident_pct")
    if pct is None:
        rows.append(_na(tr, "clarity", tr("r.no_speech")))
    else:
        level = _band_min(pct, CLARITY_PCT)
        n = len(clarity.get("unclear_segments", []))
        msg = tr(f"r.clarity.{level}", pct=f"{pct:.0f}%", unclear=f"{100 - pct:.0f}%", n=n)
        rows.append(_metric(tr, "clarity", level, msg, pct, tr("r.clarity.display", pct=f"{pct:.0f}%"),
                            tr("r.g.clarity", good=f"{CLARITY_PCT[0]:g}", check=f"{CLARITY_PCT[1]:g}"),
                            points=_scale(pct, *CLARITY_PCT)))

    rows.append(_voice(tr, vq))
    rows.append(_similarity(tr, vs))
    if sr.get("accuracy_pct") is not None:
        acc = sr["accuracy_pct"]
        rows.append(_metric(tr, "script_accuracy", _band_min(acc, SCRIPT_PCT), tr("r.script", acc=f"{acc:.0f}%"),
                            acc, f"{acc:.0f}%", tr("r.g.script", good=f"{SCRIPT_PCT[0]:g}", check=f"{SCRIPT_PCT[1]:g}"),
                            points=_scale(acc, *SCRIPT_PCT)))
    return rows


# Measures that read the dub's recognized speech: not graded when that speech can't be trusted.
SPEECH_DEPENDENT = ("clarity", "speech_overlap", "speech_offsets", "line_length", "line_overrun", "speech_rate",
                    "meaning", "completeness", "names_numbers", "mistranslations",
                    "translation_check", "numbers")


def subtitles_confirm_language(r: dict) -> Optional[float]:
    """The dub's match with its subtitle file when it is close enough to confirm the dub's language, else None."""
    match = (r.get("subtitle_match") or {}).get("dub")
    return match if match is not None and match >= SUBTITLE_MATCH else None


def speech_problem(r: dict) -> Optional[dict]:
    """Why the dub's recognized speech can't be graded, or None.

    {"kind": "unrecognized", "detected": code}: the dub sounds like a third language (neither the dub's nor the
    original's) and the recognizer is unsure (below UNRECOGNIZED_PROB): for less common languages that means
    recognition failed, not that the dub is wrong (an English → Uzbek dub was heard as Kazakh, 47% sure). A confident
    third language, or the original's language, is a real problem and stays graded (Poor).
    {"kind": "no_dub_speech" | "no_original_speech"}: no speech was recognized on that side (music, singing, noise).
    """
    from dubeval.evaluate import base_lang
    sr, ta = r.get("speech_recognition") or {}, r.get("timing_alignment") or {}
    p, meta = r.get("pipeline") or {}, r.get("metadata") or {}
    share = p.get("input") or p.get("share") or {}
    expected = whisper_language(p.get("target_language_code") or meta.get("target_language"))
    source = whisper_language(share.get("source_language_code") or meta.get("detected_source_language"))
    detected = base_lang(sr.get("dubbed_language_detected")) or None
    sure = sr.get("dubbed_language_probability")
    if expected and detected and detected not in (expected, source) and (sure is None or sure < UNRECOGNIZED_PROB) \
            and subtitles_confirm_language(r) is None:
        return {"kind": "unrecognized", "detected": detected}
    if "dubbed_speech" in ta and not ta.get("dubbed_speech") and ta.get("original_speech"):
        return {"kind": "no_dub_speech"}
    if "original_speech" in ta and not ta.get("original_speech") and ta.get("dubbed_speech"):
        return {"kind": "no_original_speech"}
    return None


def _apply_speech_problem(tr: Tr, sections: list[dict], problem: Optional[dict], lang_name: str,
                          silences_checked: bool = False) -> None:
    """Rewrites the speech rows the problem makes untrustworthy, and adds what a person should do. silences_checked:
    the voice detector looked for long silences anyway (evaluate.voice_gaps); the timing row says so."""
    if not problem:
        return
    if problem["kind"] == "unrecognized":
        detected = _lname(tr, problem["detected"])
        reason = tr("r.speech.unreliable", lang=lang_name, detected=detected)
        timing = tr("r.speech.unreliable_timing", lang=lang_name, detected=detected) if silences_checked else reason
        for s in sections:
            for i, m in enumerate(s["metrics"]):
                if m["id"] in SPEECH_DEPENDENT:
                    s["metrics"][i] = {**_na(tr, m["id"], timing if m["id"] == "speech_overlap" else reason),
                                       "cause": "unrecognized"}
                elif m["id"] == "language":
                    # A known gap in recognizing less common languages, not a fault of the dub: not graded.
                    s["metrics"][i] = {**_na(tr, "language", tr("r.lang.unrecognized", lang=lang_name,
                                                                 detected=detected)), "thresholds": m["thresholds"],
                                       "cause": "unrecognized"}
        return
    side = "dub" if problem["kind"] == "no_dub_speech" else "original"
    for s in sections:
        for m in s["metrics"]:
            if m["level"] == "not_measured" and m["id"] in DUB_SPEECH_CHECKS:
                m["absent"] = "dub" if side == "dub" else "na"
    speech = next((s for s in sections if s["id"] == "speech"), None)
    if speech is not None:
        level = "poor" if side == "dub" else "check"       # no voice in the dub: nothing was dubbed
        speech["metrics"].insert(0, _metric(tr, "speech_found", level, tr(f"r.speech.none_{side}"), False,
                                            tr("r.speech.none_display"), tr("r.g.speech_found")))


def _alignment(tr: Tr, ta: dict) -> list[dict]:
    """Whether the dub speaks at the same moments as the original."""
    ov = ta.get("overlap_pct")
    if ov is None:
        return [_na(tr, "speech_overlap", tr("r.align.na"))]
    level = _band_min(ov, OVERLAP_PCT)
    from dubeval.intervals import LONG_SILENCE_SEC, listed_mismatches
    listed = listed_mismatches(ta)           # the moments it lists; shorter ones aren't (word timings move that much)
    if level == "good":                      # a row that passed lists only its long silences (report._drop_passed)
        listed = [m for m in listed if m["kind"] == "original_only" and m["end"] - m["start"] >= LONG_SILENCE_SEC[0]]
    n = len(listed)
    # Needs review with nothing listed: say why the timeline shows none, or the reader looks for moments that aren't there
    more = _pl(tr, "r.align.spots", n) if n else tr("r.align.no_spots") if level != "good" else ""
    msg = tr(f"r.align.{level}", ov=f"{ov:.0f}%") + (" " + more if more else "")
    rows = [_metric(tr, "speech_overlap", level, msg, ov, tr("r.align.display", ov=f"{ov:.0f}%"),
                    tr("r.g.align", good=f"{OVERLAP_PCT[0]:g}", check=f"{OVERLAP_PCT[1]:g}"),
                    points=_scale(ov, *OVERLAP_PCT))]
    so, eo = ta.get("start_offset_sec"), ta.get("end_offset_sec")
    if so is not None and eo is not None:
        msg = tr("r.offsets", start=f"{abs(so):.1f}", start_way=tr("r.later" if so >= 0 else "r.earlier"),
                 end=f"{abs(eo):.1f}", end_way=tr("r.later" if eo >= 0 else "r.earlier"))
        way = lambda x: tr("r.offset.same") if abs(x) < 0.05 else \
            tr("r.offset.late" if x > 0 else "r.offset.early", sec=f"{abs(x):.1f}")
        rows.append(_metric(tr, "speech_offsets", "info", msg, so, tr("r.offsets.display", start=way(so), end=way(eo))))
    return rows


def graded_lines(sa: Optional[dict]) -> list[dict]:
    """The lines graded on length: long enough on the original side (evaluate.LINE_MIN_SEC)."""
    return [ln for ln in (sa or {}).get("lines") or [] if not ln["short"] and ln["diff_pct"] is not None]


def line_off(ln: dict) -> bool:
    """Whether a graded line's length is off: beyond ±LINE_BAND_PCT and by at least LINE_MIN_DIFF_SEC."""
    return abs(ln["diff_pct"]) > LINE_BAND_PCT and abs(ln["diff_sec"]) >= LINE_MIN_DIFF_SEC


def _line_fit(tr: Tr, sa: Optional[dict]) -> list[dict]:
    """Line by line: does each dub line take about as long as the original's, and does it end before the next one."""
    from dubeval.evaluate import LINE_MIN_SEC, LINE_OVERRUN_SEC
    if sa is None or "lines" not in sa:
        return []                                         # results from before line timing existed
    lines = graded_lines(sa)
    graded = tr("r.g.line_length", min=f"{LINE_MIN_SEC:g}", band=f"{LINE_BAND_PCT:g}", diff=f"{LINE_MIN_DIFF_SEC:g}",
                good=f"{LINE_FIT_SHARE[0]:g}", check=f"{LINE_FIT_SHARE[1]:g}", count=LINE_POOR_MIN)
    if not lines:
        return [{**_na(tr, "line_length", tr("r.line.na", min=f"{LINE_MIN_SEC:g}")), "absent": "na"}]   # no line to grade
    long_ = sum(1 for ln in lines if line_off(ln) and ln["diff_pct"] > 0)
    short = sum(1 for ln in lines if line_off(ln) and ln["diff_pct"] < 0)
    n, bad = len(lines), long_ + short
    share = (n - bad) / n * 100
    level = _band_min(share, LINE_FIT_SHARE)
    if level == "poor" and bad < LINE_POOR_MIN:
        level = "check"
    msg = tr("r.line.good" if not bad else "r.line.bad", ok=n - bad, n=n, bad=bad, long=long_, short=short,
             band=f"{LINE_BAND_PCT:g}")
    rows = [_metric(tr, "line_length", level, msg, round(share, 1), tr("r.line.display", ok=n - bad, n=n), graded,
                    points=_scale(share, *LINE_FIT_SHARE))]
    all_lines = sa.get("lines") or []
    over = [ln for ln in all_lines if ln["overrun_sec"] > 0]
    o_share = len(over) / len(all_lines) * 100 if all_lines else 0.0
    o_level = "good" if not over else "poor" if o_share > LINE_OVERRUN_SHARE and len(over) >= LINE_POOR_MIN         else "check"
    rows.append(_metric(tr, "line_overrun", o_level,
                        tr("r.overrun.none") if not over else _pl(tr, "r.overrun.some", len(over)),
                        len(over), _pl(tr, "r.overrun.display", len(over)),
                        tr("r.g.line_overrun", sec=f"{LINE_OVERRUN_SEC:g}", share=f"{LINE_OVERRUN_SHARE:g}",
                           count=LINE_POOR_MIN), points=_scale(o_share, 0.0, LINE_OVERRUN_SHARE)))
    return rows


def judge_reason(tr: Tr, tj: Optional[dict]) -> str:
    """Why the translation check didn't run, in the report language."""
    tj = tj or {}
    if tj.get("reason_key"):
        return tr(tj["reason_key"], **tj.get("reason_params", {}))
    return tj.get("reason") or tr("r.judge.off")


def _numbers(tr: Tr, nc: Optional[dict]) -> list[dict]:
    """The numbers each dub line says against its original line (dubeval/numbers.py): Good or Check, never Poor
    (speech recognition can mishear a number). No row when neither side says a number."""
    if not nc or (not nc.get("measured") and not nc.get("with_numbers")
                  and nc.get("reason_key") != "r.num.unrecognized"):
        return []                                         # results from before the check, or no numbers at all
    graded = tr("r.g.numbers")
    if nc.get("reason_key") == "r.num.unrecognized":
        return [_metric(tr, "numbers", "not_measured", tr("r.num.unrecognized"), None, "", graded)]
    if not nc.get("measured"):        # numbers said as words on one side: information, not a check that failed to run
        return [_metric(tr, "numbers", "info", tr("r.num.words"), None, tr("r.num.words_display"), graded)]
    changed, n = len(nc["lines"]), nc["compared"]
    msg = _pl(tr, "r.num.good", n) if not changed else _pl(tr, "r.num.check", changed, total=n)
    return [_metric(tr, "numbers", "check" if changed else "good", msg, changed,
                    tr("r.num.display", changed=changed, n=n), graded)]


# The rubric's criteria (translation_judge.CRITERIA) and the report rows that show them; meaning alone can be Poor.
RUBRIC_ROWS = (("semantic_accuracy", "meaning"), ("linguistic_naturalness", "naturalness"),
               ("contextual_consistency", "context_fit"), ("terminology_consistency", "terminology"),
               ("localization_appropriateness", "localization"))


def _rubric(tr: Tr, tj: dict, lang: str) -> list[dict]:
    """The translation check as one row, with the rubric's five scores inside it ("parts": each criterion's average of
    every line's 1-10 score, how many lines scored RUBRIC_FLAG or lower, and its own level). Five rows said one thing:
    on 16 judged dubs, the four after meaning had the same level 11 times. The row's level is the worst of the five:
    meaning is Poor when RUBRIC_POOR_LINES lines (or most lines) score RUBRIC_POOR or lower; the other criteria reach
    Needs review at most. Lines the judge thinks may be misheard are counted apart and never make it Poor, but a
    meaning line scoring RUBRIC_POOR or lower makes it Needs review: the judge can't tell a mishearing from a real error
    there (validation: a reversed meaning marked "maybe misheard" vanished from the report)."""
    lines = tj.get("lines") or []
    worst = lambda j: min(j["scores"][c] for c, _ in RUBRIC_ROWS)
    parts, doubtful, lost = [], [], []
    for criterion, mid in RUBRIC_ROWS:
        avg = (tj.get("criteria") or {}).get(criterion)
        low = [j for j in lines if j["scores"][criterion] <= RUBRIC_FLAG]
        real = [j for j in low if not j.get("may_be_recognition_error")]
        bad = sum(1 for j in real if j["scores"][criterion] <= RUBRIC_POOR)
        serious = criterion == "semantic_accuracy" and bad and (bad >= RUBRIC_POOR_LINES or bad > len(lines) / 2)
        unsure = [j for j in low if j.get("may_be_recognition_error") and j["scores"][criterion] <= RUBRIC_POOR] \
            if criterion == "semantic_accuracy" else []
        if criterion == "semantic_accuracy":
            doubtful, lost = unsure, real
        # Two numbers per score, each under its own heading on the screen: the average of every line, and how many
        # lines scored RUBRIC_FLAG or lower. Side by side in a sentence ("5.2 / 10" and "(5)") they read as one.
        parts.append({"id": mid, "label": tr(f"r.m.{mid}"), "value": avg, "display": f"{avg} / 10", "low": len(real),
                      "low_display": tr("r.tr.of", n=len(real), total=len(lines)),
                      "level": "poor" if serious else "check" if real or unsure else "good"})
    meaning = parts[0]
    level = max((p["level"] for p in parts), key=LEVELS.index)
    flagged = sum(1 for j in lines if not j.get("may_be_recognition_error") and worst(j) <= RUBRIC_FLAG)
    maybe = sum(1 for j in lines if j.get("may_be_recognition_error") and worst(j) <= RUBRIC_FLAG) - len(doubtful)
    # What the meaning score found, then the lines to listen to, then the other scores, then what to do about it. A
    # line that may be misheard is the only reason for Needs review in some dubs: "every line keeps the meaning" and
    # "some meaning is lost" would both be wrong there, so that case has its own first sentence and no last one.
    first = "r.tr.low" if lost else "r.tr.none_clear" if doubtful else "r.tr.all_keep"
    last = tr(f"r.meaning.{meaning['level']}") if lost or meaning["level"] == "good" and level == "good" \
        else tr("r.tr.wording_only") if meaning["level"] == "good" else ""
    # Lines a second listen cleared (translation_judge.with_second_listen): their scores above are the second reading's.
    listened = tj.get("second_listen") or {}
    cleared = listened.get("cleared") or 0
    msg = [tr(first, n=len(lost), total=len(lines), avg=meaning["value"]),
           _pl(tr, "r.rubric.doubtful", len(doubtful)) if doubtful else "",
           _pl(tr, "r.issues.plus_maybe", maybe) if maybe > 0 else "",
           _pl(tr, "r.tr.heard_again", cleared) if cleared else "",
           last]
    shown = tr("r.tr.display_low", low=flagged, total=len(lines), avg=meaning["value"]) if flagged \
        else tr("r.tr.display_ok", avg=meaning["value"])
    graded = tr("r.g.translation", poor=RUBRIC_POOR, flag=RUBRIC_FLAG, count=RUBRIC_POOR_LINES, model=tj["model"]) \
        + (" " + tr("r.g.second_listen") if listened.get("measured") else "")
    row = _metric(tr, "translation_check", level, " ".join(x for x in msg if x), meaning["value"], shown, graded,
                  points=_share_ok(sum(1 for j in lines if worst(j) > RUBRIC_FLAG), len(lines)))
    return [{**row, "parts": parts}]


def _translation(tr: Tr, tj: Optional[dict], lang: str, had_screen: bool = False) -> list[dict]:
    """The translation check's row (results saved before the rubric show meaning, completeness, names and numbers, and
    mistranslations), or, when no check ran, the reason. (The offline meaning screen that once stood in was removed on
    2026-11-20: it found 6 of the 25 lines Gemini scored low, docs/validation.md.) had_screen: the results were saved
    with that screen, whose row and moments are no longer shown; the row says so, or reopening an old evaluation would
    look as if its flagged lines had been fixed."""
    if not tj or not tj.get("measured"):
        reason = judge_reason(tr, tj) + (" " + tr("r.tr.screen_removed") if had_screen else "")
        return [_na(tr, "translation_check", reason)]
    if tj.get("rubric"):
        return _rubric(tr, tj, lang)
    score = tj["meaning_score"]
    level = _band_min(score, MEANING_SCORE)
    rows = [_metric(tr, "meaning", level, _local(tj["summary"], lang) + " " + tr(f"r.meaning.{level}"),
                    score, f"{score} / 5",
                    tr("r.g.meaning", good=MEANING_SCORE[0], check=MEANING_SCORE[1], model=tj["model"]))]
    for mid, kinds in (("completeness", ("missing", "added")), ("names_numbers", ("name_or_number",)),
                       ("mistranslations", ("mistranslation",))):
        found = [i for i in tj["issues"] if i["type"] in kinds]
        if mid == "mistranslations" and not found:
            continue
        # Issues the judge thinks may be speech-recognition errors are listed but don't change the level.
        real = [i for i in found if not i.get("may_be_recognition_error")]
        maybe = len(found) - len(real)
        major = sum(1 for i in real if i["severity"] == "major")
        level = "good" if not real else "poor" if major else "check"
        if not found:
            msg = tr(f"r.issues.none_{mid}")
        elif not real:
            msg = _pl(tr, "r.issues.maybe_only", maybe)
        else:
            msg = _pl(tr, "r.issues.found", len(real), major=major) + (
                " " + _pl(tr, "r.issues.plus_maybe", maybe) if maybe else "")
        shown = _pl(tr, "r.issues.count", len(real)) + (" · " + _pl(tr, "r.issues.maybe_count", maybe) if maybe else "")
        rows.append(_metric(tr, mid, level, msg, len(real), shown, tr("r.g.issues")))
    return rows


def _integrity(tr: Tr, vi: Optional[dict]) -> list[dict]:
    """The dub should keep the original picture: same resolution and frame rate, with an audio track."""
    if not vi:
        return [_na(tr, "file_check", tr("r.file.na"))]
    o, d = vi["original"], vi["dubbed"]
    problems, notes = [], []
    if not d["readable"]:
        problems.append(tr("r.file.unreadable"))
    if not d["has_audio"]:
        problems.append(tr("r.file.no_audio"))
    if not vi["same_resolution"]:
        notes.append(tr("r.file.resolution", orig=f"{o['width']}×{o['height']}", dub=f"{d['width']}×{d['height']}"))
    if not vi["same_fps"]:
        notes.append(tr("r.file.fps", orig=o["fps"], dub=d["fps"]))
    level = "poor" if problems else "check" if notes else "good"
    msg = (tr("r.file.ok", res=f"{d['width']}×{d['height']}", fps=d["fps"]) if level == "good"
           else " ".join(problems + notes))
    disp = f"{d['width']}×{d['height']} · {d['fps']} fps · {tr('r.file.audio_yes' if d['has_audio'] else 'r.file.audio_no')}"
    return [_metric(tr, "file_check", level, msg, level == "good", disp, tr("r.g.file"))]


def _lip_sync(tr: Tr, sync: dict) -> list[dict]:
    """The lip-sync check (its pack installed): how often the lips line up, next to the original. Graded on the share
    of checked moments that line up (LIP_SYNC_PCT); not measured never counts."""
    from dubeval.lip_sync import FPS, MATCH_FRAMES, MAX_MOMENTS
    good, poor = LIP_SYNC_PCT
    graded = tr("r.g.lip_sync", n=MAX_MOMENTS, sec=f"{MATCH_FRAMES / FPS:.2f}", good=good, poor=poor)
    if not sync.get("measured"):
        # too few faces to check, or an original whose own lips don't line up (narrated, recut): nothing to compare
        return [{**_metric(tr, "lip_sync", "not_measured", tr(sync["reason_key"], **sync.get("reason_params", {})),
                           graded=graded), "absent": "na"}]
    n, dub, orig = sync["moments"], sync["dub_match"], sync["original_match"]
    pct = dub / n * 100 if n else sync["dub_match_pct"]          # from the counts: 27 of 30 is exactly 90%
    level = "good" if pct >= good else "poor" if pct <= poor else "check"
    msg = tr("r.sync_lips.info", dub=dub, orig=orig, n=n)
    offset = sync.get("dub_offset_ms")
    if offset is not None and abs(offset) >= LIP_OFFSET_MS:
        msg += " " + tr("r.sync_lips.late" if offset > 0 else "r.sync_lips.early", sec=f"{abs(offset) / 1000:.2f}")
    elif level != "good":
        msg += " " + tr(f"r.sync_lips.{level}_hint")
    return [_metric(tr, "lip_sync", level, msg, sync["dub_match_pct"], tr("r.sync_lips.display", dub=dub, orig=orig, n=n),
                    graded, points=_scale(pct, good, poor))]


def _lipsync(tr: Tr, ls: dict, is_lipsync: Optional[bool]) -> list[dict]:
    """Lip sync: the check from the lip_sync download (graded, part of the verdict), or why no check ran: it was off,
    its download isn't installed, or the dub has no re-drawn lips. A rough lip-movement estimate once filled in when
    the download was missing; it was removed (2026-11-13) because it wasn't reliable, and a result saved with it
    says so instead of showing its number."""
    if ls.get("sync"):
        return _lip_sync(tr, ls["sync"])
    if ls.get("reason_key") == "r.lips.no_download":
        key = "no_download"
    elif ls.get("measured") and ("valid" in ls or "pearson_correlation" in ls):
        key = "estimate_removed"               # saved when the estimate still ran
    else:
        key = "not_lipsynced" if is_lipsync is False else "skipped"
    return [{**_na(tr, "lip_sync", tr(f"r.lips.{key}"), tr(f"r.lips.short.{key}")), "off": True,
             # a dub without re-drawn lips has no lip sync to check; the check being off or not downloaded is a gap
             "absent": "na" if key == "not_lipsynced" else "missing"}]


# ---------------- things to check ----------------
def _cap_moments(intervals: list[dict], metrics: list[dict]) -> None:
    """A moment is Poor only when its measure is: Poor means "this is why the dub is Poor", on a row, a moment and the
    verdict alike. Each check grades its moments one by one (a 4 s silence, a line 30% too long), and 7 of 20 graded
    dubs showed a Poor moment in a dub with no Poor measure, which read as a verdict that contradicted itself."""
    level = {m["id"]: m["level"] for m in metrics}
    for iv in intervals:
        if iv["severity"] == "poor" and level.get(_row_of(iv["check"], level)) != "poor":
            iv["severity"] = "check"


def _drop_passed(intervals: list[dict], metrics: list[dict]) -> list[dict]:
    """The moments of a check that passed are left out (LISTED_WHEN_PASSED apart): a Good speech-timing row (82% lined
    up) listed two "Needs review · Speech timing" moments, and a row that allows some lines off listed the one it
    allowed. 9 of 73 findings on the 20 test dubs: 8 short timing mismatches and a 0.1 s distortion."""
    level = {m["id"]: m["level"] for m in metrics}
    return [iv for iv in intervals if iv["category"] in LISTED_WHEN_PASSED
            or level.get(_row_of(iv["check"], level)) != "good"]


def _row_of(check: str, rows) -> str:
    """The id of the row a moment's check is graded in: its own, or the one MOMENTS_OF names when it has none."""
    return check if check in rows else MOMENTS_OF.get(check, check)


def _skipped(tr: Tr, metrics: list[dict]) -> list[dict]:
    """The checks that didn't run, put together by reason, the largest group first: each {"title" ("9 checks didn't
    run"), "reason", "action" (what a person can do, when there is something), "labels", "ids", "banner" (enough of
    them to say so at the top)}. One dub whose language wasn't recognized repeated one sentence in 12 rows."""
    groups: dict = {}
    for m in metrics:
        if m["level"] != "not_measured":
            continue
        g = groups.setdefault(m.get("cause") or m["message"], {"cause": m.get("cause"), "reason": m["message"],
                                                              "action": None, "labels": [], "ids": []})
        g["labels"].append(m["label"])
        g["ids"].append(m["id"])
        if m["id"] == "language":                        # it says the most about why: heard as which language
            g["reason"] = m["message"]
    for g in groups.values():
        if g["cause"] == "unrecognized":
            g["action"] = tr("r.skip.unrecognized_do")
        g["title"] = _pl(tr, "r.skip.count", len(g["ids"]))
        g["banner"] = len(g["ids"]) >= SKIP_BANNER_MIN
    return sorted(groups.values(), key=lambda g: -len(g["ids"]))


def _things_to_check(tr: Tr, r: dict, found: dict, moments: list[dict]) -> list[dict]:
    """What a person should look at, in time order: each moment once (kind "moment": what its leading finding says,
    in parts, and the names of the other findings there), the probable recognition errors (kind "misheard": listed,
    never counted) and the general warnings without a time (kind "general")."""
    said = lambda i: {"category": i["category_label"], "message": i["description"],
                      **{k: i.get(k) for k in ("problem", "original", "dubbed", "suggestion", "doubt")}}
    items = []
    for n, m in enumerate(moments):
        lead, *others = (found["intervals"][i] for i in m["intervals"])
        items.append({"kind": "moment", "moment": n, "start": m["start"], "end": m["end"], "severity": m["severity"],
                      **said(lead), "also": list(dict.fromkeys(o["category_label"] for o in others)),
                      # the leading finding itself, so the screen can open it (and reviewers vote on it)
                      "interval": {k: lead[k] for k in ("category", "check", "start", "end", "severity")}})
    items += [{"kind": "misheard", "start": i["start"], "end": i["end"], "severity": i["severity"], **said(i),
               "also": [], "interval": None} for i in found["possible_asr_errors"]]
    for w in r.get("warnings", []):
        text = tr(w["key"], **w.get("params", {})) if isinstance(w, dict) else str(w)
        items.append({"kind": "general", "start": None, "end": None, "category": tr("r.cat.general"),
                      "severity": "check", "message": text, "problem": text, "also": [], "interval": None})
    return sorted(items, key=lambda x: (x["start"] is None, x["start"] or 0.0))


def _thing_lines(item: dict, lb: dict) -> list[str]:
    """The parts of one thing to check after its first sentence, each a line: the doubt, what each track says, a
    suggested translation and the other findings at the same moment."""
    return [x for x in (
        lb.get(f"doubt_{item['doubt']}") if item.get("doubt") else None,
        f"{lb['original']}: “{item['original']}”" if item.get("original") else None,
        f"{lb['dub']}: “{item['dubbed']}”" if item.get("dubbed") else None,
        f"{lb['suggested']}: “{item['suggestion']}”" if item.get("suggestion") else None,
        f"{lb['also']}: {', '.join(item['also'])}" if item.get("also") else None) if x]


# ---------------- report ----------------
def _project(r: dict) -> dict:
    """What was evaluated, for the report header."""
    p, meta = r.get("pipeline", {}), r.get("metadata", {})
    share = p.get("input") or p.get("share") or {}
    return {
        "title": p.get("custom_title") or share.get("title") or Path(p.get("input_video_path") or "").name,
        "dub_name": p.get("dub_name"),
        "perso_seq": share.get("seq"),
        "share_url": share.get("share_url"),
        "source_language": share.get("source_language_name") or meta.get("detected_source_language"),
        "target_language": p.get("target_language_name") or meta.get("target_language"),
        "target_language_code": p.get("target_language_code") or meta.get("target_language"),
        "is_lipsync": share.get("is_lipsync"),
        "evaluated_video": share.get("evaluated_video"),
        "duration_sec": r.get("acoustic_metrics", {}).get("original_duration_sec"),
        "timestamp": p.get("timestamp"),
        "whisper_model": meta.get("whisper_model"),
        "dub_id": _dub_id(p),
    }


def _dub_id(p: dict) -> Optional[str]:
    """A stable id for the dub evaluated (its file's path, hashed: no path leaves the computer), so reviewer votes on
    a dub given as a file survive renaming the evaluation and stay apart from another dub with the same title."""
    path = p.get("dubbed_video_path")
    return hashlib.sha1(os.path.normcase(str(path)).encode("utf-8")).hexdigest()[:12] if path else None


def sure_of(r: dict, problem: Optional[dict] = None) -> list[dict]:
    """What makes DubEval less sure of this dub, each {"kind", params}: little_speech, short_speech, unclear_speech
    (the speech measures rest on shaky transcripts), background_replaced (silence and loudness compare different
    soundtracks), words_unchecked (the dub's language wasn't recognized), translation_unchecked (the translation
    check didn't run: a required check, so never Good; "text" names the sentence that fits why), judge_handover (the
    chosen judge's key was rejected or out of credit and the next judge checked; a note only) and judge_fallback (a
    smaller model judged; a note only)."""
    import statistics
    ac, ta, sr = r.get("acoustic_metrics") or {}, r.get("timing_alignment") or {}, r.get("speech_recognition") or {}
    out = []
    duration = ac.get("original_duration_sec") or 0.0
    if ta.get("original_speech") is not None and duration > 0 and not problem:
        spoken = sum(b - a for a, b in ta["original_speech"])
        if spoken < SURE_SPEECH_SEC:
            out.append({"kind": "short_speech", "sec": round(spoken, 1)})
        elif spoken / duration * 100 < SURE_SPEECH_SHARE:
            out.append({"kind": "little_speech", "pct": round(spoken / duration * 100)})
    clarity = (sr.get("clarity") or {}).get("confident_pct")
    if clarity is not None and clarity < SURE_CLARITY and not problem:
        out.append({"kind": "unclear_speech", "pct": round(clarity)})
    windows = [w for w in (r.get("voice_quality") or {}).get("windows") or []
               if w.get("dub_bak") is not None and w.get("original_bak") is not None]   # older results lack them
    if windows:
        gain = statistics.median(w["dub_bak"] for w in windows) - statistics.median(w["original_bak"] for w in windows)
        if gain >= BACKGROUND_REPLACED:
            out.append({"kind": "background_replaced"})
    tj = r.get("translation_judge") or {}
    if problem and problem["kind"] == "unrecognized":
        out.append({"kind": "words_unchecked"})
    elif not tj.get("measured"):                         # a required check that didn't run: never Good
        # The advice follows the reason: "add a key" only when no key is set (a key without credit was told to add one).
        why = tj.get("reason_key")
        out.append({"kind": "translation_unchecked", "text": "r.sure.translation_unchecked" if why == "r.judge.no_key"
                    else "r.sure.translation_off" if why == "r.judge.off" else "r.sure.translation_failed"})
    if tj.get("measured") and tj.get("handed_over"):
        # The chosen judge's key was rejected or its account had no credit, and the next one checked instead: a note
        # only, so the person fixes the key they meant to use.
        h = tj["handed_over"]
        out.append({"kind": "judge_handover", "first": h.get("name") or h.get("from") or "",
                    "model": tj.get("model") or tj.get("provider") or "",
                    "text": "r.sure.judge_handover_credit" if h.get("reason_key") == "r.judge.no_credit"
                    else "r.sure.judge_handover_key"})
    if tj.get("measured") and tj.get("fallback"):
        out.append({"kind": "judge_fallback", "model": tj.get("model") or ""})
    return out + _weak_recognition(r)


def _weak_recognition(r: dict) -> list[dict]:
    """Notes for a side whose language the speech model used reads badly (languages.RECOGNITION_ERRORS above
    WEAK_RECOGNITION_PCT), and one saying the large model reads it well when it does. They change no level: the
    numbers come from read test sentences, not from this dub."""
    from dubeval.intervals import _language_name
    from dubeval.languages import LARGE_MODEL, recognition_error
    meta = r.get("metadata") or {}
    model, out, tips = meta.get("whisper_model"), [], {}
    for side, code in (("dub", meta.get("target_language")), ("original", meta.get("detected_source_language"))):
        lang = whisper_language(code)
        wrong = recognition_error(model, lang)
        if wrong is None or wrong <= WEAK_RECOGNITION_PCT:
            continue
        out.append({"kind": f"weak_{side}", "lang": _language_name(lang), "model": model, "pct": min(99, round(wrong))})
        better = recognition_error(LARGE_MODEL, lang)
        if model != LARGE_MODEL and better is not None and better <= WEAK_RECOGNITION_PCT:
            tips[lang] = {"kind": "weak_tip", "lang": _language_name(lang), "better": max(1, round(better))}
    return out + list(tips.values())


def _apply_little_speech(tr: Tr, sections: list[dict], unsure: list[dict], judged: bool = False) -> None:
    """Rewrites the rows that read recognized words line by line on a mostly-music video, where those words move with any
    change in the sound. Known-problem test: 7 of 12 line-length false alarms were on the one such dub."""
    music = next((u for u in unsure if u["kind"] == "little_speech"), None)
    if not music:
        return
    keys = {"line_length": "r.line.music", "line_overrun": "r.line.music"}
    for s in sections:
        s["metrics"] = [{**_na(tr, m["id"], tr(keys[m["id"]], pct=music["pct"])), "not_graded": True, "cause": "little_speech",
                        "absent": "na"}
                        if m["id"] in keys and m["level"] != "not_measured" else m for m in s["metrics"]]


def _apply_sure(tr: Tr, metrics: list[dict], unsure: list[dict]) -> str:
    """The verdict once what DubEval is unsure of is taken into account (it rewrites the rows it caps)."""
    kinds = {u["kind"] for u in unsure}
    if "background_replaced" in kinds:
        for m in metrics:
            if m["id"] in ("silence", "loudness_match") and m["level"] == "poor":
                m["level"] = "check"
                m["message"] += " " + tr("r.sure.capped_background")
    poor = [m for m in metrics if m["level"] == "poor"]
    level = "poor" if poor else "check" if any(m["level"] == "check" for m in metrics) else "good"
    if level == "poor" and kinds & {"little_speech", "short_speech", "unclear_speech"}             and not any(m["id"] in SURE_ANYWAY for m in poor):
        level = "check"
    if level == "good" and kinds & {"words_unchecked", "translation_unchecked"}:
        level = "check"
    return level


def _sure_lines(tr: Tr, unsure: list[dict]) -> list[str]:
    """The sentences that say what DubEval is unsure of, and what a person should do: one per reason."""
    text = [tr(u.get("text") or f"r.sure.{u['kind']}", **{k: v for k, v in u.items() if k not in ("kind", "text")})
            for u in unsure]
    if any(u["kind"] in ("little_speech", "short_speech", "unclear_speech") for u in unsure):
        text.append(tr("r.sure.listen"))                 # said once, after every speech reason
    return text


def _named(tr: Tr, rows: list[dict], intervals: list[dict]) -> str:
    """The measures a headline names: those with the most flagged time first, each with the time of its first
    moment, at most HEADLINE_NAMES of them, then "and N more"."""
    flagged: dict = {}
    for iv in intervals:
        mid = _row_of(iv.get("check"), {m["id"] for m in rows})
        seconds, first = flagged.get(mid, (0.0, iv["start"]))
        flagged[mid] = (seconds + iv["end"] - iv["start"], min(first, iv["start"]))
    ranked = sorted(rows, key=lambda m: -flagged.get(m["id"], (0.0, 0.0))[0])       # stable: ties keep the report's order
    names = [tr("r.headline.from", label=m["label"], time=fmt_time(flagged[m["id"]][1])) if m["id"] in flagged
             else m["label"] for m in ranked[:HEADLINE_NAMES]]
    more = len(ranked) - len(names)
    return ", ".join(names) + (" " + tr("r.headline.more", n=more) if more else "")


def _absent(m: dict) -> Optional[str]:
    """Why a check has no level, for the score: "na" (doesn't apply to this dub), "dub" (the dub itself made it
    impossible to measure) or "missing" (anything else: a tool, a setting or a download was missing, the speech couldn't
    be recognized). None for a graded check."""
    if m["level"] in LEVELS:
        return None
    return m.get("absent") or "missing"


def _score(tr: Tr, sections: list[dict], level: str) -> dict:
    """The quality score out of 100 and how each section adds to it (SCORE_WEIGHTS, SCORE_POINTS, POOR_COST, the kinds of
    not measured in _absent): value is None when no weighted section has a counted check. Each section and counted check
    also gets its share of the score (section["score"], metric["score_share"]) so a page can show it where the check is."""
    by_id = {s["id"]: s for s in sections}
    parts, exact = [], {}
    missing_required, not_measured = [], []            # the translation check not run; checks that couldn't be measured
    applicable_w = measured_w = 0.0
    for sid, weight in sorted(SCORE_WEIGHTS.items(), key=lambda kv: -kv[1]):
        metrics = (by_id.get(sid) or {}).get("metrics", [])
        rows = [m for m in metrics if m["level"] in LEVELS or (m["level"] == "not_measured" and m["id"] not in INFO_ONLY)]
        applies = [m for m in rows if _absent(m) != "na"]
        counted = [m for m in applies if _absent(m) in (None, "dub")]     # graded, or 0 because of the dub
        need = SCORE_REQUIRES.get(sid)
        req = [m for m in rows if need and m["id"] in need]
        ready = need is None or any(_absent(m) in (None, "dub") for m in req)
        doesnt_apply = not applies or (need is not None and req and all(_absent(m) == "na" for m in req))
        if doesnt_apply:
            counted, ready = [], True
        elif not ready:
            missing_required.append({"section": sid, "check": need[0], "weight": weight})
            counted = []
        if not doesnt_apply:
            applicable_w += weight
            measured_w += weight * len(counted) / len(applies) if counted else 0.0
            not_measured += [m for m in applies if m not in counted] if counted else []
        exact[sid] = sum(0.0 if _absent(m) == "dub" else _check_points(m) for m in counted) / len(counted) \
            if counted else None
        parts.append({"id": sid, "label": tr(f"rsec.{sid}"), "weight": weight, "checks": len(counted),
                      "points": round(exact[sid], 1) if counted else None, "counted": ready, "applies": not doesnt_apply})
    used = sum(p["weight"] for p in parts if p["points"] is not None)
    lost, costs = [], 0.0                     # costs: what Poor results cost beyond their share (POOR_COSTS)
    for p in parts:
        measured = p["points"] is not None and used
        p["share"] = round(100 * p["weight"] / used, 1) if measured else None       # its weight among what was measured
        p["contribution"] = round(p["weight"] * exact[p["id"]] / used, 1) if measured else None
        if measured:
            p["display"] = tr("r.score.section", share=_pts(p["share"]), got=_pts(p["contribution"]))
            p["of_display"] = tr("r.score.of", share=_pts(p["share"]), got=_pts(p["contribution"]))  # under the heading
        elif not p["counted"]:
            p["display"] = tr("r.score.part_needs", check=tr(f"r.m.{SCORE_REQUIRES[p['id']][0]}"))
        elif not p["applies"]:
            p["display"] = tr("r.score.part_doesnt_apply")
        else:
            p["display"] = tr("r.score.part_na")     # where its weight went is in the message
        section = by_id.get(p["id"])
        if section is not None:
            section["score"] = {"weight": p["weight"], "share": p["share"], "points": p["points"],
                                "display": p["display"]}
        rows = [m for m in (section or {}).get("metrics", [])
                if m["level"] in LEVELS or (m["level"] == "not_measured" and m["id"] not in INFO_ONLY)]
        each = 100 * p["weight"] / used / p["checks"] if measured and p["checks"] else None     # exact, not rounded
        p["items"] = []
        for m in rows:
            kind = _absent(m)
            share = round(each, 1) if each is not None and kind in (None, "dub") else None
            own = (0.0 if kind == "dub" else _check_points(m)) if share is not None else None
            exact_got = each * own / 100 if share is not None else None
            got = round(exact_got, 1) if share is not None else None
            out = m["level"] in LEVELS and not p["counted"]
            # from the exact points, not the rounded ones: the list then adds up to 100 minus the score (11.2 once
            # stood over an 89.0)
            loss = round(each - exact_got, 1) if share is not None else 0.0
            poor_cost = m["level"] == "poor" and share is not None and level == "poor"
            cost, severity = _poor_cost(m["id"])
            if m["level"] == "poor" and share is not None and each < cost and level == "poor":
                costs += cost - each
                loss = float(cost)
            detail = tr("r.score.item", share=f"{share:g}", got=f"{got:g}") if share is not None else None
            p["items"].append({"id": m["id"], "label": m["label"], "level": m["level"], "share": share, "points": got,
                               "absent": kind, "detail": detail,    # the share alone, for a page with the level as a badge
                               "display": f"{tr('badge.' + m['level'])} · {detail}" if detail and kind is None
                               else tr("r.score.item_zero") if kind == "dub"
                               else tr("r.score.item_out") if out
                               else tr("r.score.item_doesnt_apply") if kind == "na" else tr("r.score.item_na")})
            m["score_share"] = share
            m["score_points"] = own                                   # its own points out of 100, as counted
            # On the row only when it lost some: "2.6 of 2.6" on every Good row hid the few that lost points.
            m["score_display"] = (tr("r.score.lost", lost=_pts(loss)) if poor_cost
                                  else tr("r.score.share", share=_pts(share), got=_pts(got)) if share is not None and loss > 0
                                  else tr("r.score.item_out") if out else None)
            if share is not None and loss > 0:
                why = (_why_poor(tr, m, cost, severity) if poor_cost
                       # Poor in a Needs review verdict (DubEval unsure of it): only its share, and the line says why
                       else tr("r.score.why_poor_unsure", result=m.get("display") or "") if m["level"] == "poor"
                       else tr("r.score.why_zero") if kind == "dub" else m.get("display") or "")
                lost.append({"id": m["id"], "label": m["label"], "level": m["level"], "lost": loss, "why": why,
                             "severity": severity if poor_cost else None,
                             "display": tr("r.score.lost", lost=_pts(loss))})
    for section in sections:                  # the video file and any other unweighted section: not in the sum
        if section["id"] not in SCORE_WEIGHTS and any(m["level"] in LEVELS for m in section["metrics"]):
            section["score"] = {"weight": 0, "share": None, "points": None, "display": tr("r.score.section_out")}
            for m in section["metrics"]:      # ...but a Poor result there (a broken file) still costs its share
                if m["level"] == "poor" and level == "poor":
                    cost, severity = _poor_cost(m["id"])
                    costs += cost
                    m["score_display"] = tr("r.score.lost", lost=_pts(cost))
                    lost.append({"id": m["id"], "label": m["label"], "level": "poor", "lost": float(cost),
                                 "severity": severity, "why": _why_poor(tr, m, cost, severity),
                                 "display": tr("r.score.lost", lost=_pts(cost))})
    lost.sort(key=lambda x: -x["lost"])
    rule = _score_rule(tr)
    coverage = round(100 * measured_w / applicable_w) if applicable_w else None
    if not used:
        return {"value": None, "parts": parts, "lost": [], "display": tr("r.score.na"), "message": tr("r.score.na_why"),
                "rule": rule, "rule_short": _score_rule(tr, short=True), "measured_weight": 0, "coverage": coverage,
                "provisional": bool(missing_required)}
    if coverage is not None and coverage < SCORE_MIN_COVERAGE:      # too little to stand for the dub: no number
        return {"value": None, "parts": parts, "lost": [], "display": tr("r.score.too_little_display"),
                "message": tr("r.score.too_little", pct=coverage, min=SCORE_MIN_COVERAGE), "rule": rule,
                "rule_short": _score_rule(tr, short=True), "measured_weight": used, "coverage": coverage,
                "provisional": True}
    raw = sum(p["weight"] * exact[p["id"]] for p in parts if p["points"] is not None) / used   # exact, not the rounded parts
    value = max(0, round(raw - costs))
    if level != "good":                       # only a dub whose checks are all Good scores 100 (99.6 rounded up once)
        value = min(value, 99)
    low = coverage is not None and coverage < COVERAGE_MIN
    provisional = bool(missing_required) or low
    total = round(sum(x["lost"] for x in lost), 1)     # the lines as shown, so the heading is their sum
    left_na = [p for p in parts if not p["applies"]]
    left_missing = [p for p in parts if p["applies"] and p["counted"] and p["points"] is None]
    partly = [m["label"] for m in not_measured]          # checks of a measured section that couldn't be measured
    zero = [m["label"] for p in parts for m in (by_id.get(p["id"]) or {}).get("metrics", [])
            if p["points"] is not None and _absent(m) == "dub"]
    message = " ".join(x for x in [
        *(tr("r.score.provisional", check=tr(f"r.m.{x['check']}"), section=tr(f"rsec.{x['section']}"),
             weight=x["weight"]) for x in missing_required),
        # one "provisional" is enough: the missing translation check already says it (and its 30 points are the gap)
        tr("r.score.provisional_coverage", pct=coverage, min=COVERAGE_MIN) if low and not missing_required else "",
        _score_left_out(tr, left_missing, "r.score.from"),
        _score_left_out(tr, left_na, "r.score.na_from"),
        tr("r.score.coverage", pct=coverage) if coverage is not None and coverage < 100
        and not (low and not missing_required) else "",
        _pl(tr, "r.score.also_missing", len(partly), checks=_and(tr, partly)) if partly else "",
        tr("r.score.dub_zero", checks=_and(tr, zero)) if zero else "",
        # the sections add up to raw; Poor results cost more than their share, so the score is lower: say by how much
        tr("r.score.poor_extra", extra=_pts(costs), raw=_pts(raw), score=value) if costs else "",
        tr("r.score.all") if coverage == 100 and not left_na and not zero else ""] if x)
    return {"value": value, "raw": round(raw, 1), "poor_cost": round(costs, 1), "coverage": coverage,
            "provisional": provisional, "measured_weight": used, "parts": parts, "lost": lost,
            "lost_total": total if lost else 0,
            # the heading over the list, with the sum done: 100 minus what was lost is the score
            # "(rounded)" when 100 minus the points lost isn't the score itself (100 − 11.1 = 88.9 → 89)
            "lost_display": tr("r.score.lost_total" if round(100 - total, 1) == value else "r.score.lost_total_rounded",
                               lost=_pts(total), score=value) if lost else None,
            "lost_how": (tr("r.score.lost_how", cost=POOR_COSTS["serious"], critical=POOR_COSTS["unusable"],
                            minor=POOR_COSTS["minor"]) if costs else tr("r.score.lost_how_check")) if lost else None,
            "extra_display": tr("r.score.lost", lost=_pts(costs)) if costs else None,   # the table's last row
            "display": tr("r.score.value_provisional" if provisional else "r.score.value", score=value),
            "message": message, "rule": rule, "rule_short": _score_rule(tr, short=True)}


def _poor_cost(mid: str) -> tuple[int, str]:
    """What a Poor result of this check costs at the least in a Poor verdict, and its level (POOR_SEVERITY)."""
    severity = POOR_SEVERITY.get(mid, "serious")
    return POOR_COSTS[severity], severity


def _why_poor(tr: Tr, m: dict, cost: int, severity: str) -> str:
    """Why a Poor result lost what it did: its result, and how serious it is."""
    key = {"unusable": "r.score.why_poor_unusable", "minor": "r.score.why_poor_minor"}.get(severity, "r.score.why_poor")
    return tr(key, result=m.get("display") or "", cost=cost)


def _check_points(m: dict) -> float:
    """A graded check's points out of 100: Good 100, Poor 0, Needs review by where its result sits between the two
    limits (score_points, from _scale or _share_ok), kept under SCORE_CHECK_MAX; a check with no number gets 50."""
    if m["level"] != "check" or m.get("score_points") is None:
        return SCORE_POINTS[m["level"]]
    return min(float(m["score_points"]), SCORE_CHECK_MAX)


def _pts(x: float) -> str:
    """Score points as every report and the page show them: one decimal, so a column of them lines up (23.0 of 26.3)."""
    return f"{x:.1f}"


def _score_left_out(tr: Tr, left: list[dict], key: str) -> str:
    """Why the section shares are bigger than their weights: the sections left out (key: "r.score.from" for those that
    couldn't be checked, "r.score.na_from" for those that don't apply to this dub), and their weight."""
    if not left:                              # only a section that needs a check was left out: its sentence says so
        return ""
    return tr(f"{key}_one" if len(left) == 1 else f"{key}_many",
              sections=_and(tr, [p["label"] for p in left]), weight=sum(p["weight"] for p in left))   # points


def _and(tr: Tr, names: list[str]) -> str:
    """Names in a sentence: "A", "A and B", "A, B and C" (in the report's language)."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + tr("r.score.and") + names[-1]


def _score_rule(tr: Tr, short: bool = False) -> str:
    """How the score is worked out, with the weights, the Poor cost and the coverage rule (short: one line)."""
    weights = ", ".join(tr("r.score.weight", section=tr(f"rsec.{sid}"), weight=w)
                        for sid, w in sorted(SCORE_WEIGHTS.items(), key=lambda kv: -kv[1]))
    return tr("r.score.rule_short" if short else "r.score.rule", good=SCORE_POINTS["good"], check=SCORE_POINTS["check"],
              poor=SCORE_POINTS["poor"], weights=weights, cost=POOR_COSTS["serious"], critical=POOR_COSTS["unusable"],
              minor=POOR_COSTS["minor"], coverage=COVERAGE_MIN, floor=SCORE_MIN_COVERAGE)


def _headline(tr: Tr, level: str, metrics: list[dict], intervals: list[dict]) -> str:
    """One or two sentences that say the verdict's reasons by name."""
    poor, check = ([m for m in metrics if m["level"] == lv] for lv in ("poor", "check"))
    if level == "good":
        return tr("r.headline.good")
    if level == "check" and poor:                        # Poor rows DubEval isn't sure of (sure_of)
        return _pl(tr, "r.headline.unsure", len(poor), names=_named(tr, poor, intervals))
    if level == "check" and not check:                   # nothing found, but the words weren't checked
        return tr("r.headline.unchecked")
    if level == "check":
        return _pl(tr, "r.headline.check", len(check), names=_named(tr, check, intervals))
    return _pl(tr, "r.headline.poor", len(poor), names=_named(tr, poor, intervals)) + (
        " " + _pl(tr, "r.headline.plus_check", len(check)) if check else "")


def build_report(r: dict, lang: str = DEFAULT_UI_LANGUAGE, dub: Optional[str] = None) -> dict:
    """The full report for a results dict, in lang: overall verdict, sections of measures, problem intervals and
    things to check. dub labels the intervals ("A" / "B") when two dubs are compared."""
    tr: Tr = lambda key, **p: i18n_t(key, lang, **p)
    ac, sr = r["acoustic_metrics"], r["speech_recognition"]
    project = _project(r)
    tj, meta = r.get("translation_judge"), r.get("metadata") or {}
    code = project["target_language_code"] or ""
    # language names in the report's language: results keep Whisper's English names ("English → Spanish" in Korean)
    share = (r.get("pipeline") or {}).get("input") or (r.get("pipeline") or {}).get("share") or {}
    source_code = share.get("source_language_code") or meta.get("detected_source_language")
    # (in English the names the results keep stay: a share link's "English (US)" says more than "English")
    english = tr("r.lang_code") == "en"
    if code and not (english and project["target_language"]):
        project["target_language"] = _lname(tr, code, start=True)
    if source_code and not (english and project["source_language"]):
        project["source_language"] = _lname(tr, source_code, start=True)
    lang_name = project["target_language"] if english or not code else _lname(tr, code)
    if project["evaluated_video"] and project.get("perso_seq"):
        project["evaluated_video"] = tr("r.evaluated." + ("lipsync" if project["is_lipsync"] else "dub"))
    else:
        project["evaluated_video"] = None
    sections = ([{"id": "pairing", "metrics": _pairing(tr, r["pairing"])}] if "pairing" in r else []) + [
        {"id": "timing_audio", "metrics": _timing_audio(tr, ac, sr, code, lang_name)},
        {"id": "speech", "metrics": _speech(tr, sr, code, lang_name, r.get("voice_quality"), r.get("voice_similarity"),
                                            subtitles_confirm_language(r))},
        {"id": "alignment", "metrics": _alignment(tr, r.get("timing_alignment") or {})
         + _line_fit(tr, r.get("segment_alignment"))},
        {"id": "translation", "metrics": _translation(tr, tj, lang, bool((r.get("meaning_screen") or {}).get("measured")))
         + _numbers(tr, r.get("numbers")), "note": tr("r.note.translation")},
        {"id": "integrity", "metrics": _integrity(tr, r.get("video_integrity"))},
        {"id": "lipsync", "metrics": _lipsync(tr, r.get("lipsync_metrics") or {}, project["is_lipsync"])},
    ]
    for s in sections:
        s["title"] = tr(f"rsec.{s['id']}")
        if s["id"] == "lipsync" and not s["metrics"][0].get("off"):           # the check ran: say what its number means
            s["note"] = tr("r.note.lip_sync")
    problem = speech_problem(r)
    _apply_speech_problem(tr, sections, problem, lang_name,
                          (r.get("timing_alignment") or {}).get("voice_gaps") is not None)
    unsure = sure_of(r, problem)
    _apply_little_speech(tr, sections, unsure, bool((tj or {}).get("measured")))
    metrics = [m for s in sections for m in s["metrics"]]
    level = _apply_sure(tr, metrics, unsure)
    counts = {lv: sum(1 for m in metrics if m["level"] == lv) for lv in (*LEVELS, "not_measured")}
    clipping_poor = any(m["id"] == "clipping" and m["level"] == "poor" for m in metrics)
    found = build_intervals(r, tr, lang, clipping_poor=clipping_poor, dub=dub)
    _cap_moments(found["intervals"], metrics)
    found["intervals"] = _drop_passed(found["intervals"], metrics)
    found["problem_seconds"] = round(total_seconds(found["intervals"]), 1)
    moments = group_moments(found["intervals"])
    summary, sure = _headline(tr, level, metrics, found["intervals"]), _sure_lines(tr, unsure)
    return {
        "report_version": 2,
        "lang": lang,
        "project": project,
        "overall": {"level": level, "label": tr(f"verdict.{level}"),
                    # summary: the verdict's reasons by name; sure: what DubEval isn't sure of, one sentence each;
                    # headline: both in one text, for readers that show a single line
                    "summary": summary, "sure": sure, "headline": " ".join([summary, *sure]),
                    "counts": counts, "unsure": [u["kind"] for u in unsure]},
        "score": _score(tr, sections, level),
        "sections": sections,
        "problem_intervals": found["intervals"],
        "possible_asr_errors": found["possible_asr_errors"],
        "problem_seconds": found["problem_seconds"],
        "moments": moments,
        "things_to_check": _things_to_check(tr, r, found, moments),
        "not_measured": [{"id": m["id"], "label": m["label"], "reason": m["message"]} for m in metrics
                         if m["level"] == "not_measured"],
        "skipped": _skipped(tr, metrics),
        "method": {
            "speech_recognition": f"{RECOGNIZER_NAMES.get(meta.get('speech_recognizer'), 'OpenAI Whisper')} "
                                  f"({project['whisper_model']})",
            "translation_judge": (tj or {}).get("model") if (tj or {}).get("measured") else None,
            "verdict_rule": tr("verdict.rule"),
        },
        "labels": {**{k: tr(f"r.label.{k}") for k in ("title", "overall", "things", "nothing", "not_measured", "method",
                                                      "judged_by", "project", "languages", "length", "evaluated",
                                                      "source", "original", "dub", "evidence", "note", "generated",
                                                      "suggested", "also", "misheard", "attention", "passed", "info",
                                                      "tl_original", "tl_dub", "tl_moment",
                                                      "passed_note")},
                   "doubt_asr": tr("r.todo.maybe_asr"), "doubt_asr_or_real": tr("r.todo.maybe_asr_or_real"),
                   # the headings over the scores inside a row (the translation check's five)
                   "score": tr("r.label.score"), "average": tr("r.label.average"),
                   "low_lines": tr("r.label.low_lines", flag=RUBRIC_FLAG),
                   # a part as one line of the text report; its own values go in where the braces are
                   "part_line": tr("r.label.part_line", label="{label}", avg="{avg}", low="{low}", flag=RUBRIC_FLAG),
                   # the score's breakdown table
                   **{f"score_{k}": tr(f"r.score.h.{k}") for k in ("title", "section", "got", "lost", "how", "none",
                                                                    "extra")}},
        "badges": {lv: tr("badge." + ("na" if lv == "not_measured" else lv)) for lv in (*LEVELS, "info", "not_measured")},
        "counts_text": tr("verdict.counts", good=counts["good"], check=counts["check"], poor=counts["poor"],
                          na=counts["not_measured"]),
    }


# ---------------- renderers ----------------
def render_text(rep: dict, width: int = 78) -> str:
    """The report as plain text for the terminal, in the report's language."""
    p, o, lb = rep["project"], rep["overall"], rep["labels"]
    bar, thin = "═" * width, "─" * width
    wrap = lambda text, first, rest: textwrap.wrap(text, width, initial_indent=first, subsequent_indent=rest)
    lines = [bar, f" {lb['title'].upper()}" + (p.get("timestamp") or "").rjust(max(0, width - len(lb["title"]) - 1)),
             bar, f" {lb['project']}: {p['title']}" + (f" · {p['dub_name']}" if p.get("dub_name") else "")
             + (f"   (Perso #{p['perso_seq']})" if p.get("perso_seq") else ""),
             f" {lb['languages']}: {p.get('source_language') or '?'} → {p.get('target_language') or '?'}"
             + (f"   {lb['length']}: {p['duration_sec']:.1f} s" if p.get("duration_sec") else "")]
    if p.get("evaluated_video"):
        lines.append(f" {lb['evaluated']}: {p['evaluated_video']}")
    if p.get("share_url"):
        lines.append(f" {lb['source']}: {p['share_url']}")
    lines += [thin, f" {lb['overall'].upper()}:  {ICONS[o['level']]}  {o['label'].upper()}     {rep['counts_text']}"]
    lines += wrap(o.get("summary") or o["headline"], " ", " ")
    for note in o.get("sure") or []:
        lines += wrap(note, " · ", "   ")
    sc = rep.get("score")                     # reports saved before 0.1.8 have none
    if sc:
        lines += [thin, f" {lb['score_title'].upper()}:  {sc['display']}"]
        lines += wrap(sc["message"], " ", " ")
        lost = sc.get("lost") or []
        if sc.get("value") is not None:       # "Too little measured": no list of points and no table of shares
            lines.append(f" {sc.get('lost_display') or lb['score_lost']}" + ("" if lost else f": {lb['score_none']}"))
            if sc.get("lost_how"):
                lines += wrap(sc["lost_how"], "   ", "   ")
            for x in lost:
                lines.append(f"   {ICONS[x['level']]} {x['label']:<26} {x['display']:<14} {x.get('why', '')}")
            lines.append(f"   {lb['score_section']:<26} {lb['score_got']}")
            for part in sc["parts"]:
                lines.append(f"   {part['label']:<26} {part.get('of_display') or part['display']}")
            if sc.get("extra_display"):         # what Poor results cost beyond their share: the table then adds up
                lines.append(f"   {lb['score_extra']:<26} {sc['extra_display']}")
        lines += wrap(sc.get("rule_short") or sc["rule"], " ", " ")
    lines.append(thin)
    # What a person acts on comes first: the moments, then the measures that aren't Good in full. The rest follows in a
    # line each (a 7 s clip printed 1,700 words, most of them about what passed); every measure's explanation and
    # grading is in the HTML report and the app.
    lines.append(f" {lb['things'].upper()}")
    listed = [x for x in rep["things_to_check"] if x.get("kind") != "misheard"]
    misheard = [x for x in rep["things_to_check"] if x.get("kind") == "misheard"]

    def things(items: list[dict]) -> None:
        for n, item in enumerate(items, 1):
            when = fmt_time(item["start"]) + (f"–{fmt_time(item['end'])}" if item.get("end") is not None else "")
            first = item["problem"] if item.get("problem") else item["message"]      # reports saved before the parts
            lines.extend(wrap(f"{n:>2}. {when or '—':<15} [{_cap(item['category'])}] {first}", "  ", " " * 22))
            for part in _thing_lines(item, lb) if item.get("problem") else []:
                lines.extend(wrap(part, " " * 22, " " * 24))
    if listed:
        things(listed)
    else:
        lines.append(f"   {lb['nothing']}")
    if misheard:
        lines.append(f"\n {lb['misheard'].upper()}")
        things(misheard)
    rows = [(s, m) for s in rep["sections"] for m in s["metrics"]]
    short = lambda m: f"   {ICONS[m['level']]} {m['label']:<30} {m['display']}"
    attention = [(s, m) for lv in ("poor", "check") for s, m in rows if m["level"] == lv]
    if attention:
        lines.append(thin + f"\n {lb.get('attention', '').upper()}")
        for s, m in attention:
            lines.append(short(m))
            lines += wrap(m["message"], "        ", "        ")
            for part in m.get("parts") or []:
                lines += wrap(lb["part_line"].replace("{label}", part["label"]).replace("{avg}", part["display"])
                              .replace("{low}", str(part.get("low_display", part["low"]))), "          ", "            ")
            if m.get("thresholds"):
                lines += wrap(m["thresholds"], "        · ", "          ")
            if s.get("note") and m is [x for x in s["metrics"] if x["level"] in ("poor", "check")][-1]:
                lines += wrap(f"{lb['note']}: {s['note']}", "      ", "      ")
    passed = [m for _, m in rows if m["level"] == "good"]
    if passed:
        lines.append(thin + f"\n {lb.get('passed', '').upper()} ({len(passed)})")
        lines += [short(m) for m in passed]
        lines += wrap(lb.get("passed_note", ""), "   ", "   ")
    info = [m for _, m in rows if m["level"] == "info"]
    if info:
        lines.append(thin + f"\n {lb['info'].upper()} ({len(info)})")
        lines += [short(m) for m in info]
    if rep["not_measured"]:
        lines.append(thin + f"\n {lb['not_measured'].upper()} ({len(rep['not_measured'])})")
        # reports saved before the groups: one line per check, as it was
        for g in rep.get("skipped") or [{"labels": [x["label"]], "reason": x["reason"]} for x in rep["not_measured"]]:
            lines += wrap(f"· {', '.join(g['labels'])}: {g['reason']}", "   ", "     ")
            if g.get("action"):
                lines += wrap(g["action"], "     ", "     ")
    m = rep["method"]
    lines += [thin, f" {lb['method']}: {m['speech_recognition']}"
              + (f" · {lb['judged_by']} {m['translation_judge']}" if m.get("translation_judge") else ""),
              *wrap(m["verdict_rule"], " ", " "), bar]
    return "\n".join(lines)


_CSS = """
.rule{white-space:pre-line}
:root{--bg:#f7f7f8;--card:#fff;--ink:#1d1d1f;--muted:#6b6b76;--line:#e4e4e8;--good:#1f8a4c;--check:#b86e00;
--poor:#c62828;--info:#5b5bd6;--na:#8a8a94;--good-bg:#e7f5ec;--check-bg:#fdf1de;--poor-bg:#fde8e8}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111114;--card:#1b1b20;--ink:#ececf1;
--muted:#9a9aa6;--line:#2c2c33;--good:#4cc27d;--check:#f0a73a;--poor:#ef6b6b;--info:#9d9dff;--na:#77777f;
--good-bg:#15291d;--check-bg:#2e2410;--poor-bg:#321616}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,
"Segoe UI","Apple SD Gothic Neo","Malgun Gothic",sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0 0 12px}.muted{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0}
.verdict{display:flex;gap:16px;align-items:center;border-width:2px}.sure{margin-top:6px;font-size:13px}
.part{margin-top:3px;font-size:13px}h2.sub{margin:18px 0 8px;font-size:14px}
table.scores{width:auto;margin:8px 0;font-size:13px}table.scores th,table.scores td{padding:3px 14px 3px 0;text-align:left}
table.scores th{font-weight:600;color:var(--muted)}
details.row{border-top:1px solid var(--line);padding:7px 0}details.row:first-of-type{border-top:0}
details.row summary{display:flex;gap:12px;align-items:baseline;cursor:pointer}
details.row .l{flex:0 0 240px;font-weight:600}details.row .v{flex:1;color:var(--muted)}
details.row .more{margin:6px 0 4px 252px;font-size:14px}
.verdict.good{border-color:var(--good);background:var(--good-bg)}.verdict.check{border-color:var(--check);
background:var(--check-bg)}.verdict.poor{border-color:var(--poor);background:var(--poor-bg)}
.big{font-size:24px;font-weight:700;white-space:nowrap}.meta{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px}
.badge{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:600;white-space:nowrap}
.b-good{background:var(--good-bg);color:var(--good)}.b-check{background:var(--check-bg);color:var(--check)}
.b-poor{background:var(--poor-bg);color:var(--poor)}.b-info{color:var(--info);border:1px solid var(--info)}
.b-not_measured{color:var(--na);border:1px solid var(--line)}
table{width:100%;border-collapse:collapse}td{padding:8px 6px;border-top:1px solid var(--line);vertical-align:top}
td.l{width:22%;font-weight:600}td.v{width:18%;white-space:nowrap;font-variant-numeric:tabular-nums}
.th{font-size:12px;color:var(--muted);margin-top:2px}.videos{display:grid;grid-template-columns:1fr 1fr;gap:12px}
video{width:100%;border-radius:8px;background:#000}.t{font-variant-numeric:tabular-nums;white-space:nowrap}
.note{font-size:13px;color:var(--muted);margin-top:8px}details summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace;margin:8px 0}
svg text{fill:var(--muted);font-size:11px}@media (max-width:640px){.videos{grid-template-columns:1fr}
td.l,td.v{width:auto}}
"""


def timeline_svg(ta: dict, duration: float, labels: tuple[str, str] = ("Original", "Dub"),
                 marks: Optional[list] = None, legend: tuple[str, str, str] = ()) -> str:
    """Two bars showing when each track speaks, with the moments the report lists outlined in red (marks: (start, end)
    pairs; every timing mismatch once, which drew 5 red marks beside a list of 3), and a legend under them."""
    if not duration or not (ta.get("original_speech") or ta.get("dubbed_speech")):
        return ""
    w, x0 = 900, 70
    sx = lambda t: x0 + (w - x0 - 10) * min(max(t, 0), duration) / duration
    height = 118 if legend else 96
    parts = [f'<svg viewBox="0 0 {w} {height}" width="100%" role="img" aria-label="Speech timeline" '
             f'fill="currentColor" font-size="11">']
    for row, (label, key, color) in enumerate(((labels[0], "original_speech", "var(--info,#5b5bd6)"),
                                               (labels[1], "dubbed_speech", "var(--good,#1f8a4c)"))):
        y = 10 + row * 32
        parts.append(f'<text x="0" y="{y + 15}">{html.escape(label)}</text>')
        parts.append(f'<rect x="{x0}" y="{y}" width="{w - x0 - 10}" height="22" rx="4" fill="var(--line,#8884)"/>')
        for s, e in ta.get(key, []):
            parts.append(f'<rect x="{sx(s):.1f}" y="{y}" width="{max(1.0, sx(e) - sx(s)):.1f}" height="22" fill="{color}"/>')
    for start, end in marks or []:
        parts.append(f'<rect x="{sx(start):.1f}" y="6" width="{max(1.0, sx(end) - sx(start)):.1f}" '
                     f'height="62" fill="none" stroke="var(--poor,#d63b3b)" stroke-width="2" rx="3"/>')
    for i in range(0, int(duration) + 1, max(1, int(duration // 8) or 1)):
        parts.append(f'<text x="{sx(i):.1f}" y="90" text-anchor="middle">{fmt_time(i)}</text>')
    if legend:
        x = x0
        for text, swatch in zip(legend, ('fill="var(--info,#5b5bd6)"', 'fill="var(--good,#1f8a4c)"',
                                         'fill="none" stroke="var(--poor,#d63b3b)" stroke-width="2"')):
            parts.append(f'<rect x="{x}" y="104" width="12" height="10" rx="2" {swatch}/>'
                         f'<text x="{x + 18}" y="113">{html.escape(text)}</text>')
            x += 30 + 7 * len(text)
    parts.append("</svg>")
    return "".join(parts)


def render_html(rep: dict, results: Optional[dict] = None, original_src: str = "", dubbed_src: str = "") -> str:
    """A self-contained HTML report (light and dark) in the report's language; embeds the videos when given."""
    e = lambda x: html.escape(str(x)) if x is not None else ""
    p, o, lb = rep["project"], rep["overall"], rep["labels"]
    out = [f"<!doctype html><html lang={e(rep.get('lang', 'en'))}><head><meta charset=utf-8><meta name=viewport "
           f"content='width=device-width,initial-scale=1'><title>{e(lb['title'])}</title><style>{_CSS}</style>"
           f"</head><body><main>",
           f"<h1>{e(lb['title'])}</h1><div class='meta muted'><span>{e(p['title'] + (' · ' + p['dub_name'] if p.get('dub_name') else ''))}</span>"
           + (f"<span>Perso #{e(p['perso_seq'])}</span>" if p.get("perso_seq") else "")
           + f"<span>{e(p.get('source_language') or '?')} → {e(p.get('target_language') or '?')}</span>"
           + (f"<span>{p['duration_sec']:.1f} s</span>" if p.get("duration_sec") else "")
           + (f"<span>{e(lb['evaluated'])}: {e(p['evaluated_video'])}</span>" if p.get("evaluated_video") else "")
           + f"<span>{e(p.get('timestamp'))}</span></div>",
           f"<div class='card verdict {o['level']}'><div class=big>{ICONS[o['level']]} {e(o['label'])}</div><div>"
           f"<div>{e(o.get('summary') or o['headline'])}</div>"
           + "".join(f"<div class=sure>{e(note)}</div>" for note in o.get("sure") or [])
           + f"<div class=muted>{e(rep['counts_text'])}</div></div></div>"]
    sc = rep.get("score")                     # reports saved before 0.1.8 have none
    if sc:
        # The app's order: why, the points lost (with their sum), the sections; the rule folded.
        scored = sc.get("value") is not None           # "Too little measured": the message alone, and the rule
        out.append(f"<div class=card><h2>{e(lb['score_title'])} · {e(sc['display'])}</h2>"
                   f"<div class=muted>{e(sc['message'])}</div>"
                   + (f"<h3>{e(sc.get('lost_display') or lb['score_lost'])}</h3>"
                      + (f"<div class=muted>{e(sc['lost_how'])}</div>" if sc.get("lost_how") else "")
                      + ("<ul>" + "".join(f"<li><span class='badge b-{x['level']}'>{e(rep['badges'][x['level']])}</span> "
                                          f"{e(x['label'])} <b>{e(x['display'])}</b> <span class=muted>"
                                          f"{e(x.get('why', ''))}</span></li>" for x in sc["lost"]) + "</ul>"
                         if sc.get("lost") else f"<div class=muted>{e(lb['score_none'])}</div>")
                      + "<table class=scores><tr>"
                      + "".join(f"<th>{e(lb[k])}</th>" for k in ("score_section", "score_got"))
                      + "</tr>" + "".join(f"<tr><td>{e(x['label'])}</td><td>{e(x.get('of_display') or x['display'])}</td></tr>"
                                          for x in sc["parts"])
                      + (f"<tr><td>{e(lb['score_extra'])}</td><td>{e(sc['extra_display'])}</td></tr>"
                         if sc.get("extra_display") else "")
                      + "</table>" if scored else "")
                   + f"<details><summary class=th>{e(lb['score_how'])}</summary>"
                   f"<div class='th rule'>{e(sc['rule'])}</div></details></div>")
    if original_src and dubbed_src:
        out.append(f"<div class='card videos'><div><b>{e(lb['original'])}</b><video controls preload=metadata "
                   f"src='{e(original_src)}'></video></div><div><b>{e(lb['dub'])}</b><video controls preload=metadata "
                   f"src='{e(dubbed_src)}'></video></div></div>")
    out.append(f"<div class=card><h2>{e(lb['things'])}</h2>")
    listed = [x for x in rep["things_to_check"] if x.get("kind") != "misheard"]
    misheard = [x for x in rep["things_to_check"] if x.get("kind") == "misheard"]

    def things(items: list[dict]) -> None:
        out.append("<table>")
        for item in items:
            when = fmt_time(item["start"]) + (f"–{fmt_time(item['end'])}" if item.get("end") is not None else "")
            first = item["problem"] if item.get("problem") else item["message"]      # reports saved before the parts
            parts = "".join(f"<div class='muted part'>{e(x)}</div>" for x in _thing_lines(item, lb)) \
                if item.get("problem") else ""
            out.append(f"<tr><td class='v t'>{e(when) or '—'}</td><td><span class='badge b-{item['severity']}'>"
                       f"{e(_cap(item['category']))}</span> {e(first)}{parts}</td></tr>")
        out.append("</table>")
    if listed:
        things(listed)
    else:
        out.append(f"<p class=muted>{e(lb['nothing'])}</p>")
    if misheard:
        out.append(f"<h2 class=sub>{e(lb['misheard'])}</h2>")
        things(misheard)
    out.append("</div>")
    if results:
        marks = [(m["start"], m["end"]) for m in rep.get("moments") or rep.get("problem_intervals") or []
                 if m.get("start") is not None and m.get("end") is not None]
        out.append("<div class=card>" + timeline_svg(results.get("timing_alignment") or {}, p.get("duration_sec") or 0,
                                                     (lb["original"], lb["dub"]), marks,
                                                     (lb["tl_original"], lb["tl_dub"], lb["tl_moment"])) + "</div>")
    badge = lambda m: f"<span class='badge b-{m['level']}'>{e(rep['badges'][m['level']])}</span>"
    scores = lambda m: (f"<table class=scores><tr><th>{e(lb['score'])}</th><th>{e(lb['average'])}</th>"
                        f"<th>{e(lb['low_lines'])}</th></tr>" + "".join(
                            f"<tr><td>{e(x['label'])}</td><td>{e(x['display'])}</td>"
                            f"<td>{e(x.get('low_display', x['low']))}</td></tr>" for x in m["parts"])
                        + "</table>" if m.get("parts") else "")
    graded = lambda m: f"<div class=th>{e(m['thresholds'])}</div>" if m.get("thresholds") else ""
    share = lambda m: f"<div class='muted part'>{e(m['score_display'])}</div>" if m.get("score_display") else ""
    rows = [(s, m) for s in rep["sections"] for m in s["metrics"]]
    attention = [(s, m) for lv in ("poor", "check") for s, m in rows if m["level"] == lv]
    if attention:
        out.append(f"<div class=card><h2>{e(lb.get('attention', ''))}</h2><table>")
        for s, m in attention:
            out.append(f"<tr><td class=l>{e(m['label'])}<div class='muted part'>{e(s['title'])}</div></td>"
                       f"<td class=v>{e(m['display'])}{share(m)}</td><td>{badge(m)} {e(m['message'])}{scores(m)}{graded(m)}</td></tr>")
        out.append("</table>" + "".join(f"<div class=note>{e(s['note'])}</div>" for s in rep["sections"]
                                        if s.get("note") and any(x is s for x, _ in attention)) + "</div>")
    # What passed, and what is only for information: a line each; a click opens its explanation and how it's graded.
    row_html = lambda m: (f"<details class=row><summary><span class=l>{e(m['label'])}</span><span class=v>"
                          f"{e(m['display'])}{share(m)}</span>{badge(m)}</summary><div class=more>{e(m['message'])}"
                          f"{scores(m)}{graded(m)}</div></details>")
    good = [m for _, m in rows if m["level"] == "good"]
    info = [m for _, m in rows if m["level"] == "info"]
    if good or info:                          # the count is the rows under it: "Passed (14)" once listed 17
        out.append("<div class=card>"
                   + (f"<h2>{e(lb.get('passed', ''))} ({len(good)})</h2>" + "".join(map(row_html, good)) if good else "")
                   + (f"<h2 class=sub>{e(lb['info'])} ({len(info)})</h2>" + "".join(map(row_html, info)) if info else "")
                   + "</div>")
    if rep["not_measured"]:
        out.append(f"<div class=card><h2>{e(lb['not_measured'])} ({len(rep['not_measured'])})</h2><ul>" + "".join(
            f"<li><b>{e(', '.join(g['labels']))}</b>: {e(g['reason'])}"
            + (f"<div class=part>{e(g['action'])}</div>" if g.get("action") else "") + "</li>"
            for g in rep.get("skipped") or [{"labels": [x["label"]], "reason": x["reason"]} for x in rep["not_measured"]])
            + "</ul></div>")
    if results:
        sr = results.get("speech_recognition", {})
        out.append(f"<div class=card><details><summary>{e(lb['evidence'])}</summary>"
                   f"<h2 style='margin-top:12px'>{e(lb['original'])}</h2>"
                   f"<pre>{e(_lines(sr.get('original_segments')) or sr.get('original_transcript'))}</pre>"
                   f"<h2>{e(lb['dub'])}</h2><pre>{e(_lines(sr.get('dubbed_segments')) or sr.get('dubbed_transcript'))}</pre>"
                   "</details></div>")
    m = rep["method"]
    out.append(f"<p class=note>{e(lb['method'])}: {e(m['speech_recognition'])}"
               + (f" · {e(lb['judged_by'])} {e(m['translation_judge'])}" if m.get("translation_judge") else "")
               + f". {e(m['verdict_rule'])} {e(lb['generated'])}</p></main></body></html>")
    return "".join(out)


def _lines(segments: Optional[list[dict]]) -> str:
    """Timestamped transcript lines for the evidence section."""
    return "\n".join(f"[{fmt_time(s['start'])}] {s['text']}" for s in segments or [] if s.get("text"))
