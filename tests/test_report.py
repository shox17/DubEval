"""Tests for the report: levels, messages, verdict rule, things to check, renderers, and the timing math."""
import numpy as np
import pytest

from dubeval.evaluate import (fill_gaps, keep_voiced, speech_clarity, speech_intervals, timing_alignment,
                              unheard_speech, voice_gaps)
from dubeval.report import build_report, render_html, render_text
from sample_results import JUDGE_OFF, JUDGED, make_results


def metric(rep: dict, mid: str) -> dict:
    """The report row with this id."""
    return next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == mid)


def test_good_dub_gets_good_verdict_and_every_row_explains_itself():
    rep = build_report(make_results(translation_judge=JUDGED))
    assert rep["overall"]["level"] == "good" and rep["overall"]["label"] == "Good"
    assert rep["overall"]["headline"].startswith("The dub passed every automatic check.")
    for s in rep["sections"]:
        for m in s["metrics"]:
            assert m["message"], m["id"]
            assert m["level"] in ("good", "check", "poor", "info", "not_measured")
            if m["level"] in ("good", "check", "poor"):
                assert m["thresholds"], f"{m['id']} must print the thresholds it used"
    assert metric(rep, "language")["display"] == "Korean (99% sure)"
    assert rep["project"]["perso_seq"] == 100001 and rep["project"]["evaluated_video"] == "lip-synced video"


def test_one_poor_metric_makes_the_verdict_poor():
    rep = build_report(make_results(acoustic_metrics={"dubbed_duration_sec": 34.0}))    # +18.5%
    assert metric(rep, "length_match")["level"] == "poor"
    assert "5.3 s longer" in metric(rep, "length_match")["message"]
    assert rep["overall"]["level"] == "poor" and "1 serious problem" in rep["overall"]["headline"]


def test_the_headline_names_what_is_wrong_and_keeps_how_sure_apart():
    # "1 serious problem" sent the reader hunting through 26 rows for it; the name and its first moment say where.
    rep = build_report(make_results(acoustic_metrics={"dubbed_duration_sec": 34.0}))
    o = rep["overall"]
    assert o["summary"].startswith("1 serious problem to fix before publishing: Length match")
    music = build_report(make_results(acoustic_metrics={"rms_ratio": 4.0},
                                      timing_alignment={"original_speech": [[0.0, 6.0], [10.0, 14.0]]}))["overall"]
    assert "isn't sure of it: Loudness match" in music["summary"] and "35%" not in music["summary"]
    assert len(music["sure"]) == 2 and "35%" in music["sure"][0]          # the reason, then "Listen to the dub yourself."
    assert music["headline"] == " ".join([music["summary"], *music["sure"]])
    from dubeval.report import _headline
    from dubeval.i18n import t
    en = lambda key, **p: t(key, "en", **p)
    rows = [{"id": "loudness_match", "label": "Loudness match", "level": "check"},
            {"id": "meaning", "label": "Meaning preserved", "level": "check"},
            {"id": "speech_overlap", "label": "Speech timing", "level": "check"}]
    moments = [{"check": "speech_overlap", "start": 75.2, "end": 77.0},           # 1.8 s
               {"check": "translation_check", "start": 12.9, "end": 19.8},        # a translation moment is the meaning row's
               {"check": "translation_check", "start": 4.0, "end": 5.0}]
    assert _headline(en, "check", rows, moments) ==         "3 items need review: Meaning preserved (from 00:04.0), Speech timing (from 01:15.2), Loudness match."   # most flagged time first
    many = [{"id": f"m{i}", "label": f"M{i}", "level": "check"} for i in range(5)]
    for lang in ("en", "ko", "pt", "es"):
        text = _headline(lambda key, **p: t(key, lang, **p), "check", many, [])
        assert "M0, M1, M2" in text and "M3" not in text and "{" not in text, lang     # three names, then "and 2 more"


# Good within 3 dB, Check within 10, Poor beyond (a dub 5.1 dB off was graded Good by a person, one 6.6 dB off Needs
# review).
@pytest.mark.parametrize("ratio, level", [(1.0, "good"), (0.75, "good"), (0.6, "check"), (0.4, "check"), (0.3, "poor"),
                                          (1.3, "good"), (1.6, "check"), (2.5, "check"), (4.0, "poor")])
def test_loudness_bands(ratio, level):
    assert metric(build_report(make_results(acoustic_metrics={"rms_ratio": ratio})), "loudness_match")["level"] == level


def test_quieter_dub_message_and_no_negative_zero():
    assert "quieter" in metric(build_report(make_results(acoustic_metrics={"rms_ratio": 0.5})), "loudness_match")["message"]
    assert metric(build_report(make_results(acoustic_metrics={"rms_ratio": 0.999})), "loudness_match")["display"] == "+0.0 dB"


def test_wrong_language_is_poor():
    rep = build_report(make_results(speech_recognition={"dubbed_language_detected": "ja", "dubbed_language_probability": 0.9}))
    assert metric(rep, "language")["level"] == "poor" and "instead of Korean" in metric(rep, "language")["message"]


def test_unclear_speech_is_listed_with_timestamps():
    clarity = {"confident_pct": 75.0, "mean_logprob": -0.9, "segments": 4,
               "unclear_segments": [{"start": 12.0, "end": 14.5, "text": "웅얼웅얼"}]}
    rep = build_report(make_results(speech_recognition={"clarity": clarity}))
    assert metric(rep, "clarity")["level"] == "check"
    item = next(t for t in rep["things_to_check"] if t["category"] == "clarity")
    assert item["start"] == 12.0 and "웅얼웅얼" in item["message"]


def test_speech_timing_bands_and_mismatch_items():
    rep = build_report(make_results())
    assert metric(rep, "speech_overlap")["level"] == "good"            # 81%: a real Perso dub
    assert not rep["things_to_check"]                   # a check that passed lists no moments (its mismatch is allowed)
    mid = build_report(make_results(timing_alignment={"overlap_pct": 70.0}))
    t = mid["things_to_check"][0]
    assert (t["start"], t["end"], t["category"]) == (19.4, 20.4, "timing")
    assert metric(build_report(make_results(timing_alignment={"overlap_pct": 50.0})), "speech_overlap")["level"] == "check"
    low = build_report(make_results(timing_alignment={"overlap_pct": 40.0}))     # Poor below 45%
    assert metric(low, "speech_overlap")["level"] == "poor"


def test_missing_judge_is_not_measured_with_a_reason_and_the_dub_is_never_good():
    rep = build_report(make_results(translation_judge=JUDGE_OFF))
    ids = {x["id"]: x["reason"] for x in rep["not_measured"]}
    assert "script_accuracy" not in ids          # an optional extra (CLI --script), not a gap
    assert "turned off" in ids["translation_check"]
    assert metric(rep, "translation_check")["value"] is None
    assert rep["overall"]["counts"]["not_measured"] == 2            # one translation row (not three), and lip sync
    assert rep["overall"]["level"] == "check" and rep["overall"]["unsure"] == ["translation_unchecked"]
    assert "translation wasn't checked" in rep["overall"]["headline"]   # a required check that didn't run


@pytest.mark.parametrize("key, params, says", [
    ("r.judge.no_key", {}, "add an AI key in Settings"),
    ("r.judge.no_credit", {"model": "Claude"}, "fix what's described there"),
    ("r.judge.bad_key", {"model": "Gemini"}, "fix what's described there"),
    ("r.judge.off", {}, "turn the check on"),
])
def test_the_headline_advice_follows_why_the_translation_wasnt_checked(key, params, says):
    """A key without credit was once told to "add an AI key": only a missing key gets that advice."""
    from dubeval.translation_judge import not_measured
    for lang in ("en", "ko", "pt", "es"):
        rep = build_report(make_results(translation_judge=not_measured(key, **params)), lang)
        assert rep["overall"]["level"] == "check" and rep["overall"]["unsure"] == ["translation_unchecked"]
        assert rep["overall"]["headline"] and "{" not in rep["overall"]["headline"], lang
    headline = build_report(make_results(translation_judge=not_measured(key, **params)))["overall"]["headline"]
    assert says in headline
    assert ("add an AI key" in headline) == (key == "r.judge.no_key")


def test_translation_issues_drive_levels_and_things_to_check():
    judged = {**JUDGED, "meaning_score": 3, "summary": "Mostly right, one sentence changed.", "issues": [
        {"type": "missing", "severity": "major", "start_sec": 8.0, "original": "Thank you", "dubbed": "",
         "explanation": "The thank-you was dropped.", "may_be_recognition_error": False},
        {"type": "name_or_number", "severity": "minor", "start_sec": 3.1, "original": "Inha University",
         "dubbed": "이나데아크", "explanation": "The university name sounds wrong.", "may_be_recognition_error": True}]}
    rep = build_report(make_results(translation_judge=judged))
    assert metric(rep, "meaning")["level"] == "check"
    assert metric(rep, "completeness")["level"] == "poor"
    assert metric(rep, "names_numbers")["level"] == "good"          # only a possible recognition error
    assert "probably a speech-recognition error" in metric(rep, "names_numbers")["message"]
    names = next(t for t in rep["things_to_check"] if t["category"] == "name or number")
    assert "Probably a speech-recognition error" in names["message"] and "“이나데아크”" in names["message"]
    assert [t["start"] for t in rep["things_to_check"]] == sorted(t["start"] for t in rep["things_to_check"])


def test_broken_dub_file_is_poor():
    vi = make_results()["video_integrity"]
    vi["dubbed"]["has_audio"] = False
    rep = build_report(make_results(video_integrity=vi))
    assert metric(rep, "file_check")["level"] == "poor" and "no audio" in metric(rep, "file_check")["message"]


def test_lipsync_never_counts_toward_verdict():
    rep = build_report(make_results(translation_judge=JUDGED))
    assert metric(rep, "lip_sync")["level"] == "not_measured" and rep["overall"]["level"] == "good"
    skipped = make_results(lipsync_metrics={"measured": False, "sync": None, "reason_key": "r.lips.skipped"})
    skipped["pipeline"]["share"]["is_lipsync"] = False
    row = metric(build_report(skipped), "lip_sync")
    assert row["level"] == "not_measured" and "isn't lip-synced" in row["message"]
    # a few words in the row's value, so a comparison's cell isn't empty beside "Not measured"
    assert row["display"] == "Not a lip-synced dub"
    skipped["pipeline"]["share"]["is_lipsync"] = None
    assert metric(build_report(skipped), "lip_sync")["display"] == "Off for this run"


def test_a_lip_check_that_didnt_run_isnt_called_experimental():
    # "Lip movement (experimental)" headed a section where nothing had run, on a PC with the real check installed.
    section = lambda rep: next(s for s in rep["sections"] if s["id"] == "lipsync")
    off = make_results(lipsync_metrics={"measured": False, "valid": False, "reason": "skipped (turned off for this run)",
                                        "reason_key": "r.lips.skipped"})
    off["pipeline"]["share"]["is_lipsync"] = None
    for lang in ("en", "ko", "pt", "es"):
        s = section(build_report(off, lang))
        assert "xperiment" not in s["title"] and "실험" not in s["title"] and "note" not in s
        assert s["metrics"][0]["label"] == s["title"] and "{" not in s["metrics"][0]["message"]
    s = section(build_report(off))
    assert s["title"] == "Lip sync" and "turn it on under More options" in s["metrics"][0]["message"]
    assert "experimental" not in render_text(build_report(off)).lower() and "experimental" not in render_html(build_report(off))
    assert "xperimental" not in str(build_report(make_results(translation_judge=JUDGED)))   # the estimate is gone


def test_script_score_appears_when_a_script_was_given():
    rep = build_report(make_results(speech_recognition={"accuracy_pct": 62.0, "error_rate": 0.38, "primary_metric": "cer"}))
    assert metric(rep, "script_accuracy")["level"] == "check" and "62% of your script" in metric(rep, "script_accuracy")["message"]
    assert "script_accuracy" not in {x["id"] for x in rep["not_measured"]}


def test_renderers_show_verdict_sections_and_things_to_check():
    r = make_results()
    rep = build_report(r)
    text = render_text(rep)
    assert "OVERALL:  ✅  GOOD" in text and "PASSED (" in text and "00:19.4–00:20.4" not in text   # passed: not listed
    assert "Perso #100001" in text
    assert "NOT MEASURED" in render_text(build_report(make_results(translation_judge=JUDGE_OFF)))
    page = render_html(rep, r, "original.mp4", "dubbed_ko.mp4")
    assert page.startswith("<!doctype html>") and "prefers-color-scheme:dark" in page
    assert "<video" in page and "Speech timeline" in page and "Things to check" in page
    assert "안녕하세요" in page                                      # evidence transcripts


def test_reports_put_problems_first_and_what_passed_in_a_line_each():
    # A 7 s clip printed 1,700 words, most of them about what passed, with the one Poor row in section 5.
    r = make_results(acoustic_metrics={"dubbed_duration_sec": 34.0})         # the length is Poor
    rep = build_report(r)
    text = render_text(rep)
    order = [text.index(x) for x in ("OVERALL", "THINGS TO CHECK", "MEASURES THAT NEED ATTENTION", "PASSED (", "Method:")]
    assert order == sorted(order)
    attention, passed = text[order[2]:order[3]], text[order[3]:order[4]]
    poor, good = metric(rep, "length_match"), metric(rep, "loudness_match")
    assert poor["label"] in attention and poor["thresholds"][:40] in " ".join(attention.split())   # in full, with its grading
    assert good["label"] in passed and good["message"][:40] not in " ".join(text.split())          # a line: name and value
    assert "The HTML report and the app explain each one" in " ".join(passed.split())
    page = render_html(rep, r)
    assert page.index("Things to check") < page.index("Measures that need attention") < page.index("Passed (")
    import html
    assert html.escape(good["message"]) in page and html.escape(good["thresholds"]) in page   # folded, never dropped
    assert "<script" not in page                                             # folds are <details>: saved reports run no script
    for lang in ("ko", "pt", "es"):
        assert "{" not in render_text(build_report(r, lang)) and "{" not in render_html(build_report(r, lang), r).split("</style>")[1]


def test_checks_that_didnt_run_are_put_together_with_what_to_do():
    # An Uzbek dub heard as Kazakh repeated one sentence in 12 rows.
    from test_speech_problems import uzbek_heard_as_kazakh
    rep = build_report(uzbek_heard_as_kazakh())
    groups = rep["skipped"]
    assert sum(len(g["ids"]) for g in groups) == len(rep["not_measured"])
    big = groups[0]
    assert big["banner"] and len(big["ids"]) >= 8 and {"language", "clarity", "speech_overlap"} <= set(big["ids"])
    assert "heard Kazakh" in big["reason"] and big["action"].startswith("What to do: add the dub's subtitle file")
    assert big["title"] == f"{len(big['ids'])} checks didn't run"
    assert all(not g["banner"] and g["action"] is None for g in groups[1:] if len(g["ids"]) < 3)
    text = " ".join(render_text(rep).split())
    assert text.count("heard Kazakh") == 1 and "What to do: add the dub's subtitle file" in text
    for lang in ("ko", "pt", "es"):
        other = build_report(uzbek_heard_as_kazakh(), lang)["skipped"][0]
        assert "{" not in other["title"] + other["reason"] + other["action"]


def test_html_escapes_untrusted_text():
    r = make_results(pipeline={**make_results()["pipeline"], "share": {**make_results()["pipeline"]["share"],
                                                                       "title": "<script>alert(1)</script>"}})
    assert "<script>alert" not in render_html(build_report(r), r)


# ---------------- timing math (dubeval/evaluate.py) ----------------
def seg(start, end, words=None, logprob=-0.2, no_speech=0.01, text="x"):
    """A Whisper segment as transcribe() returns it."""
    return {"start": start, "end": end, "text": text, "avg_logprob": logprob, "no_speech_prob": no_speech,
            "words": words if words is not None else [[start, end]]}


def test_speech_intervals_merge_short_gaps_and_drop_silence():
    segs = [seg(0.0, 2.0, [[0.0, 0.8], [0.9, 2.0]]), seg(3.0, 4.0), seg(5.0, 9.0, logprob=-1.5, no_speech=0.9)]
    assert speech_intervals(segs) == [[0.0, 2.0], [3.0, 4.0]]


def test_lines_the_voice_detector_hears_no_speech_in_are_dropped():
    stt = {"text": "hello 3몇 world", "language": "ko",
           "segments": [seg(0.0, 2.0, text="hello"), seg(5.0, 6.0, text="3몇"), seg(8.0, 10.0, text="world")]}
    kept = keep_voiced(stt, [[0.0, 2.1], [8.5, 12.0]])           # music from 5 to 6 s: words read into it go
    assert [s["text"] for s in kept["segments"]] == ["hello", "world"] and kept["text"] == "hello world"
    assert keep_voiced(stt, None) is stt                          # no detector: nothing dropped
    assert stt["segments"][1]["text"] == "3몇"                    # the cached transcript itself is untouched


def test_a_line_the_detector_missed_is_kept_when_the_other_track_speaks_then():
    original = {"text": "", "language": "en", "segments": [seg(2.0, 4.0, text="You're a jerk, Tom!"), seg(8.0, 9.0, text="3")]}
    dub = [seg(2.2, 4.1, text="Eres un idiota Tom")]
    kept = keep_voiced(original, [[2.0, 2.8]], partner=dub)         # a shout over music: the detector half missed it
    assert [s["text"] for s in kept["segments"]] == ["You're a jerk, Tom!"]   # the dub speaks then; 8-9 s it doesn't
    assert keep_voiced(original, [], partner=dub)["segments"] == []   # no voice heard at all: words read into music


def test_speech_the_transcript_skipped_is_recognized_again(monkeypatch):
    from dubeval import evaluate
    stt = {"text": "later", "language": "ko", "segments": [seg(20.0, 22.0, text="later")]}
    voiced = [[4.0, 5.3], [5.6, 7.3], [20.0, 22.0], [30.0, 30.4]]    # 4-7.3 s skipped; 0.4 s at 30 s too short
    assert unheard_speech(stt, voiced) == [[4.0, 7.3]]
    seen = []

    def fake_transcribe(y, model, language=None, check=None):
        seen.append((len(y), language))
        return {"text": "뭘 쳐다봐?", "segments": [seg(0.3, 1.7, [[0.3, 1.7]], text="뭘 쳐다봐?"), seg(2.0, 2.1, text="")]}
    monkeypatch.setattr(evaluate, "transcribe", fake_transcribe)
    out = fill_gaps(stt, np.zeros(16000 * 40, dtype=np.float32), voiced, None, "ko")
    assert [(s["start"], s["text"]) for s in out["segments"]] == [(4.0, "뭘 쳐다봐?"), (20.0, "later")]
    assert out["segments"][0]["words"] == [[4.0, 5.4]] and out["text"] == "뭘 쳐다봐? later"
    assert seen == [(int(7.6 * 16000) - int(3.7 * 16000), "ko")]      # the stretch with 0.3 s either side
    assert fill_gaps(stt, None, [[20.0, 22.0]], None) is stt          # nothing skipped: untouched


def test_timing_alignment_overlap_and_mismatches():
    same = timing_alignment([[0, 5], [6, 10]], [[0, 5], [6, 10]], 10)
    assert same["overlap_pct"] == 100.0 and same["mismatches"] == []
    shifted = timing_alignment([[0, 5]], [[1, 6]], 10)
    assert 60 < shifted["overlap_pct"] < 70
    kinds = {m["kind"] for m in shifted["mismatches"]}
    assert kinds == {"dub_only", "original_only"} and shifted["start_offset_sec"] == 1
    assert timing_alignment([], [[0, 1]], 10)["overlap_pct"] is None


def test_voice_gaps_are_silences_in_the_dub_while_the_original_speaks():
    def gap(found, start, end, seconds):
        assert (found["start"], found["end"], found["original_sec"]) == (pytest.approx(start, abs=0.06),
                                                                         pytest.approx(end, abs=0.06),
                                                                         pytest.approx(seconds, abs=0.11))
    gap(voice_gaps([[0, 10]], [[0, 3], [6, 10]], 10)[0], 3, 6, 3)
    # The original's own pauses don't split a silence: 0.3-0.45 s between phrases hid planted silences that way.
    found = voice_gaps([[2, 3], [3.4, 4], [4.5, 5]], [], 6)
    assert len(found) == 1
    gap(found[0], 2, 5, 2.1)
    # A blip of the dub's voice doesn't end a silence; a line does.
    assert len(voice_gaps([[0, 6]], [[3, 3.2]], 6)) == 1 and len(voice_gaps([[0, 6]], [[3, 4]], 6)) == 2
    assert voice_gaps([[2, 2.4]], [], 6) == []                                  # the original barely speaks there
    assert voice_gaps([[0, 5]], [[0, 5]], 5) == [] and voice_gaps([], [[0, 5]], 5) == []
    assert voice_gaps(None, [[0, 5]], 5) is None and voice_gaps([[0, 5]], None, 5) is None     # no detector


def test_a_timing_mismatch_needs_the_voice_detector_to_agree():
    # Words recognized in the original at 4-6 s only: a mismatch while the detector agrees (the dub silent there)...
    o, d = [[0, 2], [4, 6]], [[0, 2]]
    voiced = [[0, 2], [4, 6]]
    found = timing_alignment(o, d, 8, voiced_original=voiced, voiced_dub=[[0, 2], [5.2, 6]])       # voiced 40%: silent
    assert [(m["start"], m["end"], m["kind"]) for m in found["mismatches"]] == [(4.0, 6.0, "original_only")]
    # ...not when the dub speaks there after all: the recognizer missed its words, and its timings move with any
    # change anywhere in the file.
    assert timing_alignment(o, d, 8, voiced_original=voiced, voiced_dub=[[0, 2], [4.5, 6]])["mismatches"] == []
    # Nor when the "speaking" track has no voice there: the recognizer read words into music.
    assert timing_alignment(o, d, 8, voiced_original=[[0, 2], [4, 4.4]], voiced_dub=[[0, 2]])["mismatches"] == []
    # The other side alike, and the overlap score stays on the words.
    assert timing_alignment(d, o, 8, voiced_original=[[0, 2], [4.5, 6]], voiced_dub=voiced)["mismatches"] == []
    assert timing_alignment(o, d, 8, voiced_original=voiced, voiced_dub=voiced)["overlap_pct"] == 50.0
    # Without a detector nothing changes.
    assert [m["kind"] for m in timing_alignment(o, d, 8)["mismatches"]] == ["original_only"]
    assert [m["kind"] for m in timing_alignment(o, d, 8, voiced_original=None, voiced_dub=None)["mismatches"]] == ["original_only"]


def test_speech_clarity_share_of_confident_time():
    c = speech_clarity([seg(0, 6), seg(6, 8, logprob=-1.3, text="mumble")])
    assert c["confident_pct"] == 75.0 and c["unclear_segments"][0]["text"] == "mumble"
    assert speech_clarity([])["confident_pct"] is None


# ---------------- language ----------------
import re

HANGUL = re.compile(r"[가-힣]")


def test_whole_report_follows_the_language():
    """Every sentence a person reads is in Korean when the report is built in Korean (numbers and quotes aside)."""
    judged = {**JUDGED, "meaning_score": 4, "issues": [
        {"type": "name_or_number", "severity": "minor", "start_sec": 3.1, "original": "Inha University",
         "dubbed": "이나데아크", "explanation": {"en": "Name misheard.", "ko": "이름이 잘못 들렸습니다.",
                                                  "pt": "Nome mal ouvido.", "es": "Nombre mal oído."},
         "may_be_recognition_error": True}]}
    r = make_results(translation_judge=judged, warnings=[{"key": "r.warn.no_speech", "params": {}, "text": "x"}])
    rep = build_report(r, "ko")
    texts = [rep["overall"]["label"], rep["overall"]["headline"], rep["counts_text"], rep["method"]["verdict_rule"]]
    texts += list(rep["labels"].values()) + list(rep["badges"].values())
    for s in rep["sections"]:
        texts += [s["title"], s.get("note") or "가"]
        for m in s["metrics"]:
            texts += [m["label"], m["message"]] + ([m["thresholds"]] if m["thresholds"] else [])
    texts += [t["message"] for t in rep["things_to_check"]] + [t["category"] for t in rep["things_to_check"]]
    english = [x for x in texts if not HANGUL.search(x)]
    assert english == [], english
    assert "이름이 잘못 들렸습니다." in " ".join(texts)              # the judge's Korean explanation
    assert "METRICS" not in render_html(rep, r) and "METRICS" not in render_text(rep)


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_renderers_work_in_every_language(lang):
    r = make_results(translation_judge=JUDGED)
    rep = build_report(r, lang)
    assert rep["lang"] == lang and rep["labels"]["title"].upper() in render_text(rep)
    assert f"<html lang={lang}>" in render_html(rep, r)


# ---------------- speaking pace per language ----------------
def dub_in(code: str, name: str, rate: float, unit: str = "words/s", **kw) -> dict:
    """Results for a dub into `code` speaking at `rate`."""
    r = make_results(speech_recognition={"dubbed_speech_rate": {"value": rate, "unit": unit},
                                         "dubbed_language_detected": code.split("-")[0]}, **kw)
    r["pipeline"].update(target_language_code=code, target_language_name=name)
    return r


@pytest.mark.parametrize("code, rate, level", [
    ("es", 3.5, "good"), ("es", 3.9, "check"), ("es", 4.2, "check"), ("es", 4.3, "poor"),
    ("en", 3.2, "good"), ("en", 3.5, "check"), ("en", 3.8, "check"), ("en", 3.9, "poor"),
    ("es-MX", 3.0, "good"), ("ko", 5.8, "good")])
def test_pace_bands_for_spanish_english_and_korean(code, rate, level):
    unit = "chars/s" if code == "ko" else "words/s"
    row = metric(build_report(dub_in(code, code, rate, unit)), "speech_rate")
    assert row["level"] == level and row["thresholds"]


@pytest.mark.parametrize("code", ["fr", "pt", "xx"])
def test_pace_is_not_measured_for_a_language_without_a_rule(code):
    rep = build_report(dub_in(code, "French" if code == "fr" else code, 2.9))
    row = metric(rep, "speech_rate")
    assert row["level"] == "not_measured" and row["value"] is None
    assert "no speaking-pace rule" in row["message"] and "2.9 words/s" in row["message"]
    assert "speech_rate" in {x["id"] for x in rep["not_measured"]}


def _uzbek_heard_as_kazakh(match=None):
    """An EN→UZ dub that recognition heard as Kazakh (unsure), with or without a subtitle-file match."""
    r = make_results(metadata={"target_language": "uz"},
                     speech_recognition={"dubbed_language_detected": "kk", "dubbed_language_probability": 0.47})
    r["pipeline"].update(target_language_code="uz", target_language_name="Uzbek")
    if match is not None:
        r["subtitle_match"] = {"original": None, "dub": match}
    return r


def language_row(rep):
    return next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == "language")


def test_a_dub_matching_its_subtitles_is_in_their_language_whatever_recognition_guessed():
    without = build_report(_uzbek_heard_as_kazakh(), "en")
    assert language_row(without)["level"] == "not_measured"                # "heard Kazakh instead of Uzbek": not graded
    confirmed = build_report(_uzbek_heard_as_kazakh(0.61), "en")
    row = language_row(confirmed)
    assert row["level"] == "good" and "Uzbek" in row["display"] and "61%" in row["message"]
    assert "subtitle" in row["thresholds"]
    # the speech checks are graded again instead of "not measured" (recognition is trusted)
    assert confirmed["overall"]["counts"]["not_measured"] < without["overall"]["counts"]["not_measured"]


def test_subtitles_that_dont_match_the_speech_confirm_nothing():
    rep = build_report(_uzbek_heard_as_kazakh(0.2), "en")
    assert language_row(rep)["level"] == "not_measured"


# ----- the translation rubric (five criteria, every line scored 1-10) -----

def rubric_result(*lines):
    """A rubric translation check over lines given as (semantic, naturalness, misheard) per line."""
    from dubeval import translation_judge as tj
    answer, spoken = [], []
    for n, (semantic, natural, misheard) in enumerate(lines, 1):
        scores = {c: 9 for c in tj.CRITERIA} | {"semantic_accuracy": semantic, "linguistic_naturalness": natural}
        answer.append({"line": n, **scores, **{f"{c}_reason": "Why." for c in tj.CRITERIA},
                       "ideal_translation": "더 나은 번역" if min(scores.values()) <= 7 else "",
                       "error_type": "distortion" if semantic <= 6 else "lexical_choice" if natural <= 6 else "no_error",
                       "may_be_recognition_error": misheard})
        spoken.append({"n": n, "start": n * 2.0, "end": n * 2.0 + 1.5, "original": f"line {n}", "dub": f"줄 {n}"})
    return tj._rubric_result([tj._result({"lines": answer}, "gemini-3.6-flash", "Gemini")], spoken)


def test_a_moment_is_poor_only_when_its_measure_is():
    # 7 of 20 graded dubs showed a Poor moment in a dub with no Poor measure: a verdict that seemed to contradict itself.
    one = build_report(make_results(translation_judge=rubric_result((9, 9, False), (3, 9, False), (9, 9, False))))
    assert metric(one, "translation_check")["level"] == "check"
    assert [i["severity"] for i in one["problem_intervals"] if i["check"] == "translation_check"] == ["check"]
    three = build_report(make_results(translation_judge=rubric_result((3, 9, False), (2, 9, False), (4, 9, False))))
    assert metric(three, "translation_check")["level"] == "poor"
    assert "poor" in [i["severity"] for i in three["problem_intervals"] if i["check"] == "translation_check"]
    assert all(m["severity"] == max((three["problem_intervals"][i]["severity"] for i in m["intervals"]),
                                    key=["check", "poor"].index) for m in three["moments"])


def test_things_to_check_list_each_moment_once_in_parts_and_the_misheard_apart():
    judged = rubric_result((9, 9, False), (3, 9, False), (9, 5, True))
    rep = build_report(make_results(translation_judge=judged))
    things = rep["things_to_check"]
    moments = [x for x in things if x["kind"] == "moment"]
    assert len(moments) == len(rep["moments"]) <= len(rep["problem_intervals"])
    assert sorted(i for m in rep["moments"] for i in m["intervals"]) == list(range(len(rep["problem_intervals"])))
    wrong = next(x for x in moments if x["interval"]["category"] == "mistranslation")
    # the error type isn't said again when the moment's name already says it ("Mistranslation · Meaning distorted:")
    assert not wrong["problem"].startswith("Meaning distorted") and "“" not in wrong["problem"]  # the parts are apart...
    assert wrong["original"] == "line 2" and wrong["dubbed"] == "줄 2" and wrong["suggestion"] == "더 나은 번역"
    assert "“line 2” → “줄 2”" in wrong["message"] and "더 나은 번역" in wrong["message"]            # ...and whole in one text
    misheard = [x for x in things if x["kind"] == "misheard"]
    assert len(misheard) == len(rep["possible_asr_errors"]) == 1 and misheard[0]["doubt"] == "asr" \
        and misheard[0]["interval"] is None
    text = render_text(rep)
    assert "POSSIBLY MISHEARD (NOT COUNTED)" in text and "Suggested translation: “더 나은 번역”" in text
    assert text.index("POSSIBLY MISHEARD") > text.index("[Mistranslation]")
    for lang in ("ko", "pt", "es"):
        assert "{" not in render_text(build_report(make_results(translation_judge=judged), lang))


def translation_rows(r, lang="en"):
    """Every row by id, and the scores inside the translation check's row by theirs (meaning, naturalness, ...)."""
    rows = {m["id"]: m for s in build_report(r, lang)["sections"] for m in s["metrics"]}
    return rows | {p["id"]: p for m in rows.values() for p in m.get("parts") or []}


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_rubric_rows_show_every_criterion_with_its_average(lang):
    r = make_results(translation_judge=rubric_result((9, 9, False), (8, 9, False)))
    rows = translation_rows(r, lang)
    for mid in ("meaning", "naturalness", "context_fit", "terminology", "localization"):
        assert rows[mid]["level"] == "good" and "/ 10" in rows[mid]["display"] and "{" not in rows[mid]["label"]
    assert rows["meaning"]["value"] == 8.5 and "completeness" not in rows
    # One row, with the five scores inside it: five rows said one thing (the last four had one level on 11 of 16 dubs).
    section = next(s for s in build_report(r, lang)["sections"] if s["id"] == "translation")
    assert [m["id"] for m in section["metrics"]] == ["translation_check"]
    row = section["metrics"][0]
    assert row["level"] == "good" and row["value"] == 8.5 and [p["id"] for p in row["parts"]] == [
        "meaning", "naturalness", "context_fit", "terminology", "localization"]
    assert "{" not in row["message"] + row["thresholds"] + row["label"] + row["display"]
    # A row that passed is one line in the text report; the HTML report folds its explanation and its scores.
    assert row["display"] in render_text(build_report(r, lang))
    assert all(p["label"] in render_html(build_report(r, lang)) for p in row["parts"])


def test_the_translation_row_takes_the_worst_of_its_scores_and_says_which():
    row = lambda *lines: translation_rows(make_results(translation_judge=rubric_result(*lines)))["translation_check"]
    good, wording, lost, serious = (9, 9, False), (9, 5, False), (6, 9, False), (3, 9, False)
    only_wording = row(good, good, wording)
    assert only_wording["level"] == "check" and only_wording["display"] == "1 of 3 lines flagged · meaning 9.0 / 10"
    assert "Every line keeps the original's meaning" in only_wording["message"]
    assert "The meaning is kept" in only_wording["message"]
    # Each score's two numbers are apart and named: "5.2 / 10" beside "(5)" in one sentence read as one number.
    wording_score = next(p for p in only_wording["parts"] if p["id"] == "naturalness")
    assert (wording_score["display"], wording_score["low"], wording_score["low_display"]) == ("7.7 / 10", 1, "1 of 3")
    assert "(1)" not in only_wording["message"]
    printed = " ".join(render_text(build_report(make_results(translation_judge=rubric_result(good, good, wording)))).split())
    assert "Natural wording: 7.7 / 10 on average · 1 of 3 lines at 6 or lower" in printed
    some = row(good, lost, wording)
    assert some["level"] == "check" and "Lines that lose or change the original's meaning: 1 of 3" in some["message"]
    assert some["display"].startswith("2 of 3 lines flagged")
    assert row(serious, serious, serious)["level"] == "poor" and "redone" in row(serious, serious, serious)["message"]
    assert row(good, good)["display"] == "meaning 9.0 / 10"
    # Only a line that may be misheard: neither "every line keeps the meaning" nor "some meaning is lost" is true.
    unsure = row(good, good, (2, 9, True))
    assert unsure["level"] == "check" and "No line clearly loses" in unsure["message"]
    assert "Every line keeps" not in unsure["message"] and "Some meaning is lost" not in unsure["message"]
    for lang in ("ko", "pt", "es"):
        for lines in ((good, good, wording), (good, lost, wording), (good, good, (2, 9, True))):
            shown = translation_rows(make_results(translation_judge=rubric_result(*lines)), lang)["translation_check"]
            assert "{" not in shown["message"] + shown["display"] + shown["thresholds"]


def test_meaning_is_poor_with_three_serious_lines_or_most_lines_and_check_with_one_or_two():
    good, serious = (9, 9, False), (4, 9, False)
    level = lambda *lines: translation_rows(make_results(translation_judge=rubric_result(*lines)))["meaning"]["level"]
    assert level(good, good, good, good, serious) == "check"                 # one serious line of five
    assert level(good, good, good, good, serious, serious) == "check"        # two of six
    assert level(good, good, good, serious, serious, serious) == "poor"      # three
    assert level(good, serious, serious) == "poor"                           # most of a short dub
    assert level(serious) == "poor"
    assert translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (6, 9, False))))["meaning"][
        "level"] == "check"
    assert translation_rows(make_results(translation_judge=rubric_result((7, 9, False))))["meaning"]["level"] == "good"


def test_the_other_criteria_reach_check_at_most():
    rows = translation_rows(make_results(translation_judge=rubric_result((9, 1, False))))
    assert rows["naturalness"]["level"] == "check" and rows["meaning"]["level"] == "good"
    assert rows["translation_check"]["level"] == "check"                # the row follows its worst score


def test_a_possibly_misheard_line_is_check_at_most_and_only_when_very_low():
    rows = translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (5, 9, True))))
    assert rows["meaning"]["level"] == "good" and "recognition error" in rows["translation_check"]["message"]
    for many in (1, 4):                    # very low but maybe misheard: a person listens (Check), never Poor
        rows = translation_rows(make_results(translation_judge=rubric_result((9, 9, False), *[(2, 9, True)] * many)))
        assert rows["meaning"]["level"] == "check" and "listen" in rows["translation_check"]["message"]
        assert rows["translation_check"]["level"] == "check"


def test_a_very_low_possibly_misheard_line_is_a_moment_to_listen_to():
    rep = build_report(make_results(translation_judge=rubric_result((9, 9, False), (2, 9, True), (5, 9, True))), "en")
    listen = [i for i in rep["problem_intervals"] if "listen to the line" in i["description"]]
    assert len(listen) == 1 and listen[0]["severity"] == "check"
    assert len(rep["possible_asr_errors"]) == 1                         # the 5/10 line stays a probable mishearing


def test_a_rubric_problem_is_a_timed_interval_with_its_type_and_suggested_translation():
    rep = build_report(make_results(translation_judge=rubric_result((9, 9, False), (4, 9, False), (9, 5, False))), "en")
    wrong = [i for i in rep["problem_intervals"] if i["category"] == "mistranslation"]
    wording = [i for i in rep["problem_intervals"] if i["category"] == "translation_wording"]
    # One line scoring 4 leaves Meaning at Needs review, so its moment is Needs review too (see the test below).
    assert wrong and wrong[0]["severity"] == "check" and "Meaning distorted" not in wrong[0]["description"]
    assert "Suggested translation: “더 나은 번역”" in wrong[0]["description"]
    assert wording and wording[0]["severity"] == "check" and "Word choice" in wording[0]["description"]


def test_results_saved_before_the_rubric_still_show_as_before():
    old = {"measured": True, "model": "gemini", "meaning_score": 4, "summary": {"en": "Fine."}, "issues": []}
    rows = translation_rows(make_results(translation_judge=old))
    assert rows["meaning"]["display"] == "4 / 5" and "completeness" in rows


# ---------------- how sure DubEval is (Step 2) ----------------
def _verdict(r, lang="en"):
    o = build_report(r, lang)["overall"]
    return o["level"], o["unsure"], o["headline"]


def test_a_poor_result_on_mostly_music_is_needs_review_with_the_reason():
    loud = {"rms_ratio": 4.0}                                            # 12 dB louder: Poor on its own
    assert _verdict(make_results(acoustic_metrics=loud))[0] == "poor"
    music = make_results(acoustic_metrics=loud, timing_alignment={"original_speech": [[0.0, 6.0], [10.0, 14.0]]})
    level, unsure, headline = _verdict(music)                            # 10 s of speech in 28.7 s: 35% is the line
    assert level == "check" and unsure == ["little_speech"] and "isn't sure" in headline and "35%" in headline
    for lang in ("ko", "pt", "es"):
        assert "{" not in _verdict(music, lang)[2]


def test_too_little_or_unclear_speech_is_not_sure_either():
    short = make_results(acoustic_metrics={"rms_ratio": 4.0}, timing_alignment={"original_speech": [[0.0, 6.7]]})
    assert _verdict(short)[:2] == ("check", ["short_speech"])
    unclear = make_results(acoustic_metrics={"rms_ratio": 4.0},
                           speech_recognition={"clarity": {"confident_pct": 81.5, "unclear_segments": []}})
    assert _verdict(unclear)[:2] == ("check", ["unclear_speech"])


def test_problems_that_dont_depend_on_speech_stay_poor():
    clipped = make_results(acoustic_metrics={"dubbed_clipping_pct": 1.0},
                           timing_alignment={"original_speech": [[0.0, 6.0]]})
    assert _verdict(clipped)[0] == "poor"                                # distortion is distortion, music or not


def test_a_replaced_background_caps_silence_and_loudness_at_check():
    windows = [{"start": 0.0, "end": 9.0, "dub": 3.0, "original": 3.0, "dub_sig": 3.5, "original_sig": 3.5,
                "dub_bak": 4.2, "original_bak": 1.2}]
    r = make_results(acoustic_metrics={"dubbed_silence_ratio": 0.6, "original_silence_ratio": 0.2},
                     voice_quality={"windows": windows})
    level, unsure, _ = _verdict(r)
    silence = next(m for s in build_report(r, "en")["sections"] for m in s["metrics"] if m["id"] == "silence")
    assert level == "check" and unsure == ["background_replaced"] and silence["level"] == "check"
    assert "background was replaced" in silence["message"]


def test_a_dub_whose_words_could_not_be_checked_is_never_good():
    assert _verdict(make_results())[0] == "good"
    kazakh = make_results(speech_recognition={"dubbed_language_detected": "kk", "dubbed_language_probability": 0.75})
    kazakh["pipeline"]["target_language_code"] = "uz"
    level, unsure, headline = _verdict(kazakh)
    assert level == "check" and "words_unchecked" in unsure and "can't call it Good" in headline


def test_a_backup_judge_model_is_noted_without_changing_the_level():
    judged = {**JUDGED, "fallback": True, "model": "gemini-3.1-flash-lite"}
    plain = _verdict(make_results(translation_judge=JUDGED))
    noted = _verdict(make_results(translation_judge=judged))
    assert noted[0] == plain[0] and noted[1] == ["judge_fallback"] and "gemini-3.1-flash-lite" in noted[2]


@pytest.mark.parametrize("why, said", [("r.judge.no_credit", "no credit left"), ("r.judge.bad_key", "rejected the API key")])
def test_a_judge_that_handed_over_is_noted_without_changing_the_level(why, said):
    judged = {**JUDGED, "model": "gemini-3.5-flash", "handed_over": {"from": "claude", "name": "Claude", "reason_key": why}}
    plain = _verdict(make_results(translation_judge=JUDGED))
    noted = _verdict(make_results(translation_judge=judged))
    assert noted[0] == plain[0] and noted[1] == ["judge_handover"]
    assert "Claude" in noted[2] and "gemini-3.5-flash" in noted[2] and said in noted[2]


def test_a_stretch_heard_in_part_is_not_added_twice(monkeypatch):
    from dubeval import evaluate
    stt = {"text": "hello", "language": "en", "segments": [seg(4.0, 7.0, text="hello")]}
    voiced = [[4.0, 15.0]]                                   # one stretch: 3 s already heard, 8 s skipped
    assert unheard_speech(stt, voiced) == [[4.0, 15.0]]

    def fake_transcribe(y, model, language=None, check=None):   # recognized again: the heard line and the skipped one
        return {"text": "hello world", "segments": [seg(0.3, 3.3, text="hello"), seg(3.6, 11.0, text="world")]}
    monkeypatch.setattr(evaluate, "transcribe", fake_transcribe)
    out = fill_gaps(stt, np.zeros(16000 * 20, dtype=np.float32), voiced, None, "en")
    assert [(s["start"], s["text"]) for s in out["segments"]] == [(4.0, "hello"), (7.3, "world")]


def off_line():
    """One line far shorter than the original's, running into the next one."""
    return {"groups": [], "unmatched_original": [], "unmatched_dub": [], "lines": [
        {"n": 1, "start": 0.0, "end": 4.0, "original_sec": 4.0, "dub_sec": 2.0, "diff_sec": -2.0, "diff_pct": -50.0,
         "start_shift_sec": 0.0, "overrun_sec": 0.7, "short": False, "original": [0], "dub": [0]}]}


def line_rows(rep):
    return {m["id"]: m for s in rep["sections"] for m in s["metrics"] if m["id"] in ("line_length", "line_overrun")}


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_line_length_isnt_graded_on_a_mostly_music_video(lang):
    # Word timings over music move with any change in the sound: 7 of 12 line-length false alarms were on the one such dub.
    music = make_results(segment_alignment=off_line(), timing_alignment={"original_speech": [[0.0, 6.0], [10.0, 14.0]]})
    rep = build_report(music, lang)
    assert [m["level"] for m in line_rows(rep).values()] == ["not_measured"] * 2
    assert all("35" in m["message"] and "{" not in m["message"] for m in line_rows(rep).values())
    assert not [i for i in rep["problem_intervals"] if i["category"] in ("line_length", "line_overrun")]
    assert "little_speech" in rep["overall"]["unsure"]


def test_the_same_line_is_graded_on_a_video_with_speech():
    rep = build_report(make_results(segment_alignment=off_line()), "en")
    assert line_rows(rep)["line_length"]["level"] == "check" and line_rows(rep)["line_overrun"]["level"] == "check"
    assert {i["category"] for i in rep["problem_intervals"]} >= {"line_length", "line_overrun"}


@pytest.mark.parametrize("off, level", [(0, "good"), (1, "good"), (2, "check"), (4, "check"), (5, "check"), (6, "poor")])
def test_line_length_is_poor_only_when_most_lines_are_off(off, level):
    # 4 of 10 lines off used to be Poor; the one graded dub it made Poor, a person graded Needs review.
    fit = {"short": False, "diff_pct": 0.0, "diff_sec": 0.0, "overrun_sec": 0.0}
    far = {"short": False, "diff_pct": -30.0, "diff_sec": -2.0, "overrun_sec": 0.0}
    lines = [{"n": i + 1, "start": 3.0 * i, "end": 3.0 * i + 2, "original_sec": 2.0, "dub_sec": 2.0, "start_shift_sec": 0.0,
              "original": [i], "dub": [i], **(far if i < off else fit)} for i in range(10)]
    sa = {"groups": [], "unmatched_original": [], "unmatched_dub": [], "lines": lines}
    assert line_rows(build_report(make_results(segment_alignment=sa), "en"))["line_length"]["level"] == level


# ---------------- languages the speech model reads badly ----------------
def sure_lines(lang="en", **metadata):
    """The "not sure" sentences of the sample report with its metadata changed."""
    return build_report(make_results(metadata=metadata), lang)["overall"]


def test_a_language_the_model_reads_badly_gets_a_note_and_changes_no_level():
    weak = sure_lines(target_language="uz", whisper_model="large-v3-turbo")
    fine = sure_lines(target_language="ko", whisper_model="large-v3-turbo")
    assert "weak_dub" in weak["unsure"] and "weak_dub" not in fine["unsure"]
    note = next(s for s in weak["sure"] if "Uzbek" in s)
    assert "large-v3-turbo" in note and "82%" in note and "rough" in note
    assert "weak_tip" not in weak["unsure"]                      # the large model is what read it badly


def test_the_note_points_to_the_large_model_when_it_reads_the_language_well():
    weak = sure_lines(target_language="ja", whisper_model="base")
    assert weak["unsure"][-2:] == ["weak_dub", "weak_tip"]
    assert "Japanese" in weak["sure"][-1] and "5%" in weak["sure"][-1] and "Settings → Models" in weak["sure"][-1]
    # Thai is weak with both models: the note, without the pointer.
    assert "weak_tip" not in sure_lines(target_language="th", whisper_model="base")["unsure"]


def test_the_original_language_is_noted_too_and_unmeasured_ones_say_nothing():
    both = sure_lines(target_language="ja", detected_source_language="fr", whisper_model="base")
    assert both["unsure"].count("weak_tip") == 2 and {"weak_dub", "weak_original"} <= set(both["unsure"])
    assert any("the original is in French" in s for s in both["sure"])
    for quiet in (dict(target_language="ko", whisper_model="small"),          # a model that wasn't measured
                  dict(target_language="yo", whisper_model="large-v3-turbo"),  # a language that wasn't
                  dict(target_language="es-MX", whisper_model="base")):        # read well (the base code counts)
        assert not [k for k in sure_lines(**quiet)["unsure"] if k.startswith("weak")]


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_the_weak_language_notes_exist_in_every_report_language(lang):
    weak = sure_lines(lang, target_language="ja", detected_source_language="fr", whisper_model="base")
    assert sum("base" in s for s in weak["sure"]) == 2 and sum("21%" in s or "11%" in s for s in weak["sure"]) == 2


# ---------- the quality score (report._score, SCORE_WEIGHTS) ----------
def _sections(**levels):
    """Sections by id, each with graded rows at the given levels (a list) or no rows (None)."""
    # the translation section's first row is the translation check itself (report.SCORE_REQUIRES)
    ids = lambda sid, i: "translation_check" if (sid, i) == ("translation", 0) else f"{sid}{i}"
    return [{"id": sid, "title": sid, "metrics": [{"id": ids(sid, i), "label": f"{sid} {i}", "level": lv}
                                                  for i, lv in enumerate(lvs or [])]}
            for sid, lvs in levels.items()]


def _score_of(level="good", lang="en", **levels):
    from dubeval.i18n import t as i18n_t
    from dubeval.report import _score
    return _score(lambda key, **p: i18n_t(key, lang, **p), _sections(**levels), level)


def test_the_score_adds_the_sections_up_by_their_weights():
    from dubeval.report import POOR_COST, SCORE_WEIGHTS
    assert sum(SCORE_WEIGHTS.values()) == 100
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sc = _score_of(**every)
    assert sc["value"] == 100 and sc["measured_weight"] == 100 and sc["coverage"] == 100 and sc["poor_cost"] == 0
    assert [p["id"] for p in sc["parts"]] == sorted(SCORE_WEIGHTS, key=lambda s: -SCORE_WEIGHTS[s])   # heaviest first
    # Translation (30) at Needs review loses half its weight; one of two alignment checks is Poor: its share is 12.5,
    # but a Poor result costs POOR_COST (40), so 27.5 more: 72.5 − 27.5 = 45, the number worked out, no cap.
    sc = _score_of("poor", **{**every, "translation": ["check"], "alignment": ["good", "poor"]})
    assert sc["raw"] == 72.5 and sc["poor_cost"] == POOR_COST - 12.5 and sc["value"] == 45
    assert sc["lost_total"] == 55 and sc["lost_display"] == "55.0 points lost, so 45 / 100"
    sc = _score_of("check", **{**every, "translation": ["check"]})
    assert sc["value"] == 85
    by = {p["id"]: p for p in sc["parts"]}
    assert by["translation"]["points"] == 50 and by["translation"]["contribution"] == 15 and by["speech"]["share"] == 15


def test_a_section_with_nothing_graded_gives_its_weight_to_the_others():
    # Lip sync wasn't measured (a missing check: shared, and the coverage says so); no Same video rows at all (a share
    # link has no pairing): nothing there applies, so its weight is shared without lowering the coverage.
    sc = _score_of("check", translation=["check"], alignment=["good"], speech=["good"], timing_audio=["good"],
                   pairing=None, lipsync=["not_measured"])
    assert sc["measured_weight"] == 85 and sc["raw"] == round(100 * (15 + 25 + 15 + 15) / 85, 1)
    na = {p["id"]: p for p in sc["parts"]}
    assert na["lipsync"]["points"] is None and na["pairing"]["contribution"] is None
    assert sc["coverage"] == round(100 * 85 / 90) and not sc["provisional"]
    assert sc["message"] == ("Lip sync wasn't checked, so its 5 points are shared among the other sections. Same video "
                             "doesn't apply to this dub, so its 10 points are shared among the other sections. 94% of the checks that "
                             "apply to this dub were measured.")
    assert na["lipsync"]["display"] == "Not checked" and na["pairing"]["display"] == "Doesn't apply"
    one = _score_of("check", translation=["check"], alignment=["good"], speech=["good"], timing_audio=["good"],
                    pairing=["good"], lipsync=["not_measured"])
    assert one["message"] == ("Lip sync wasn't checked, so its 5 points are shared among the other sections. 95% of the checks that "
                              "apply to this dub were measured.")
    assert "pairing" in na
    assert _score_of(translation=None, lipsync=None)["value"] is None


def test_the_score_is_the_number_worked_out_and_only_all_good_is_100():
    from dubeval.report import SCORE_WEIGHTS
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    assert _score_of(**every)["display"] == "100 / 100"
    # No cap at 89 for Needs review any more: the score is what the checks add up to...
    sc = _score_of("check", **{**every, "alignment": ["good", "check", "good"]})
    assert sc["value"] == round(100 - 25 / 3 * 0.5) == 96 and "cap" not in sc and "ranking_display" not in sc
    # ...but 100 is only for a dub whose checks are all Good: Needs review for a reason outside them shows 99 at most.
    assert _score_of("check", **every)["value"] == 99
    assert sc["lost_total"] == round(sum(x["lost"] for x in sc["lost"]), 1)      # the heading is the lines' sum


def test_a_check_that_needs_review_scores_by_where_its_result_sits_between_the_limits():
    from dubeval.report import SCORE_CHECK_MAX, SCORE_WEIGHTS, _scale, _share_ok
    assert _scale(100 * 15 / 18, 90, 50) == 83.3           # line length: 15 of 18 lines fit
    assert _scale(4.5, 3.0, 6.0) == 50                     # lower is better: halfway between the dB limits
    assert _scale(95, 90, 50) == 100 and _scale(30, 90, 50) == 0       # outside the limits: clamped
    assert _share_ok(9, 10) == 90 and _share_ok(0, 0) is None
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sections = _sections(**{**every, "alignment": ["good", "check", "good"]})
    line = next(s for s in sections if s["id"] == "alignment")["metrics"][1]
    line["score_points"] = 83.3
    from dubeval.i18n import t as i18n_t
    from dubeval.report import _score
    sc = _score(lambda key, **p: i18n_t(key, "en", **p), sections, "check")
    # 25 points over three checks: 8.3 each; the line-length check keeps 83.3% of its 8.3 and loses 1.4
    assert line["score_points"] == 83.3 and line["score_display"] == "6.9 of 8.3 points"   # one decimal
    assert sc["raw"] == round(100 - 25 / 3 * (1 - 0.833), 1) and sc["value"] == 99    # 98.6, the real number
    assert [x["lost"] for x in sc["lost"]] == [1.4]
    align = next(s for s in sections if s["id"] == "alignment")["score"]
    assert align["display"] == "23.6 of 25.0 points"
    # the list's heading does the sum, and the line under it says how checks lose points
    assert sc["lost_display"] == "1.4 points lost, so 99 / 100 (rounded)" and "how far" in sc["lost_how"]
    # no Poor result cost anything here, so the 100 / 40 / 20 part isn't said
    assert sc["lost_how"] == "A check that needs review loses points by how far its result is from Good."
    # A Needs review check never scores as a Good one, and one with no number to place keeps 50.
    line["score_points"] = 100
    _score(lambda key, **p: i18n_t(key, "en", **p), sections, "check")
    assert line["score_points"] == SCORE_CHECK_MAX
    line["score_points"] = None
    _score(lambda key, **p: i18n_t(key, "en", **p), sections, "check")
    assert line["score_points"] == 50


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_the_score_is_in_every_report_and_every_language(lang):
    rep = build_report(make_results(), lang)
    sc = rep["score"]
    assert sc["value"] is not None and "{" not in sc["message"] + sc["rule"] + sc["display"]
    assert all("{" not in p["display"] for p in sc["parts"])
    assert rep["labels"]["score_title"].upper() in render_text(rep)
    page = render_html(rep, make_results())
    from html import escape
    assert rep["labels"]["score_title"] in page and all(escape(p["label"]) in page for p in sc["parts"])
    for k in ("score_section", "score_got"):
        assert rep["labels"][k] and "{" not in rep["labels"][k]


def test_each_check_shows_its_level_and_its_own_share_of_the_score():
    from dubeval.report import SCORE_WEIGHTS
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sc = _score_of("check", **{**every, "speech": ["good", "good", "check", "not_measured"]})
    speech = next(p for p in sc["parts"] if p["id"] == "speech")
    graded = [i for i in speech["items"] if i["share"] is not None]
    # Speech weighs 15 of 100; its three graded checks share it evenly, the unmeasured one is listed with no share.
    assert [i["share"] for i in graded] == [5.0, 5.0, 5.0] and [i["points"] for i in graded] == [5.0, 5.0, 2.5]
    assert speech["items"][3]["share"] is None and speech["items"][3]["detail"] is None
    assert graded[2]["display"].startswith("Needs review · 5%")
    # Every check's points add up to the score itself.
    assert round(sum(i["points"] or 0 for p in sc["parts"] for i in p["items"]), 1) == sc["raw"] == 97.5



def test_without_the_translation_check_translation_isnt_counted_and_the_score_is_provisional():
    from dubeval.report import SCORE_WEIGHTS
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    # The check didn't run; the numbers check (Good) is there but doesn't stand in for it.
    sc = _score_of("check", **{**every, "translation": ["not_measured", "good"]})
    tr_part = next(p for p in sc["parts"] if p["id"] == "translation")
    assert sc["provisional"] and tr_part["points"] is None and not tr_part["counted"]
    assert sc["measured_weight"] == 70 and "(provisional" in sc["display"] and "Provisional" in sc["message"]
    assert [i["display"] for i in tr_part["items"][1:]] == ["Not counted in the score"]
    # With the check, the section counts as before and the score isn't provisional.
    sc = _score_of("check", **{**every, "translation": ["check", "good"]})
    assert not sc["provisional"] and next(p for p in sc["parts"] if p["id"] == "translation")["points"] == 75


def test_a_one_check_sections_row_and_header_give_the_same_points():
    from dubeval.report import SCORE_WEIGHTS, _score
    from dubeval.i18n import t as i18n_t
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sections = _sections(**{**every, "translation": ["check"], "lipsync": None})
    sections[0]["metrics"][0]["score_points"] = 71.4                 # 2 of 7 lines flagged
    sc = _score(lambda key, **p: i18n_t(key, "en", **p), sections, "check")
    row, header = sections[0]["metrics"][0]["score_display"], sections[0]["score"]["display"]
    assert row == header == "22.5 of 31.6 points"            # the row once said 22.6 (from the rounded 31.6)
    # from the exact points (31.58 × 28.6%), not 31.6 − 22.5: the list then adds up to 100 minus the score
    assert sc["lost"][0]["lost"] == 9.0


def test_the_points_lost_heading_says_rounded_when_the_sum_is_not_the_score():
    from dubeval.report import SCORE_WEIGHTS, _score
    from dubeval.i18n import t as i18n_t
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sections = _sections(**{**every, "alignment": ["good", "check", "good"]})
    sections[1]["metrics"][1]["score_points"] = 60          # alignment: 25 over three, one at 60 → 3.3 lost
    sc = _score(lambda key, **p: i18n_t(key, "en", **p), sections, "good")
    assert sc["value"] == 97 and sc["lost_display"] == "3.3 points lost, so 97 / 100 (rounded)"


def test_points_lost_lists_only_the_checks_that_lost_some_biggest_first():
    from dubeval.report import SCORE_WEIGHTS
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sections = _sections(**{**every, "translation": ["check"], "timing_audio": ["good", "poor", "good"]})
    sections[0]["metrics"][0]["display"] = "2 of 7 lines flagged"
    crackle = next(x for x in sections if x["id"] == "timing_audio")["metrics"][1]
    crackle["display"] = "Crackles"
    from dubeval.i18n import t as i18n_t
    from dubeval.report import _score
    sc = _score(lambda key, **p: i18n_t(key, "en", **p), sections, "poor")
    # the Poor check's share is 5 (15 over three), but a Poor result costs at least 40: it leads the list
    assert [(x["label"], x["lost"]) for x in sc["lost"]] == [("timing_audio 1", 40.0), ("translation 0", 15.0)]
    assert [x["why"] for x in sc["lost"]] == ["Crackles · Poor: a serious problem", "2 of 7 lines flagged"]
    assert "100 when it makes the dub unusable, 40 for most problems, 20" in sc["lost_how"]
    # the sections add up to 80, the score is 45: the message and the table's last row say why
    assert "Poor results cost 35.0 points more than their share, so the sections add up to 80.0 but the score is 45"         in sc["message"] and sc["extra_display"] == "−35.0 points"
    assert sc["lost_total"] == 55 and sc["value"] == 45 and crackle["score_display"] == "−40.0 points"
    assert sc["lost"][1]["display"] == "−15.0 points" and _score_of(**every)["lost"] == []


def test_each_section_and_check_carries_its_share_for_the_page():
    rep = build_report(make_results())
    speech = next(s for s in rep["sections"] if s["id"] == "speech")
    assert speech["score"]["display"].endswith(" points")
    graded = [m for m in rep["sections"][0]["metrics"] + speech["metrics"] if m["level"] in ("good", "check", "poor")]
    # every graded check keeps its share; only the ones that lost points say "got of share" on their row (on every Good
    # row it hid the few that lost some); the section's header has the total
    assert graded and all(m["score_share"] for m in graded)
    lost = [m for m in graded if m["score_points"] < 100]
    assert all(" of " in m["score_display"] and m["score_display"].endswith(" points") for m in lost)
    assert all(m["score_display"] is None for m in graded if m["score_points"] == 100)
    assert all(m.get("score_display") is None for s in rep["sections"] for m in s["metrics"] if m["level"] == "info")
    # The video file has no weight, and its section says so rather than saying nothing.
    file = next(s for s in rep["sections"] if s["id"] == "integrity")
    assert file["score"]["display"] == "Not in the score"


def test_the_card_counts_in_score_points_only_and_says_the_weights_are_untested():
    from dubeval.report import SCORE_WEIGHTS
    every = {sid: ["good"] for sid in SCORE_WEIGHTS}
    sc = _score_of("check", **{**every, "translation": ["check"]})
    tr_part = next(p for p in sc["parts"] if p["id"] == "translation")
    # one unit: the points it got of the most it could; no section score out of 100 beside the dub's
    assert tr_part["display"] == "15.0 of 30.0 points" and "/ 100" not in tr_part["display"]
    assert tr_part["of_display"] == "15.0 of 30.0"                 # in the table, under the "Score points" heading
    assert "not yet tested" in sc["rule"] and "not yet tested" in sc["rule_short"]
    assert len(sc["rule_short"]) < len(sc["rule"])


def test_every_report_shows_the_score_in_the_same_order_with_the_rule_folded_or_short():
    rep = build_report(make_results())
    lb, sc = rep["labels"], rep["score"]
    text = render_text(rep)
    block = text[text.index(lb["score_title"].upper()):]
    # why, the points lost, the sections under their headings, then the rule in one line (not the long one)
    heading = sc.get("lost_display") or lb["score_lost"]          # without points lost: the plain heading
    assert block.index(heading) < block.index(lb["score_section"]) < block.index(sc["rule_short"][:40])
    assert sc["rule"][:60] not in text
    page = render_html(rep, make_results())
    card = page[page.index(lb["score_title"]):]
    assert card.index(heading) < card.index(lb["score_section"]) < card.index(lb["score_how"])
    assert f"<details><summary class=th>{lb['score_how']}</summary>" in card


def test_values_say_what_they_mean_without_decoding():
    from dubeval.report import build_report
    r = make_results()
    r["timing_alignment"].update({"start_offset_sec": -0.8, "end_offset_sec": 0.0})
    r["acoustic_metrics"].update({"original_silence_ratio": 0.168, "dubbed_silence_ratio": 0.202,
                                  "dubbed_clipping_pct": 0.0})
    rows = {m["id"]: m for s in build_report(r, "en")["sections"] for m in s["metrics"]}
    assert rows["speech_offsets"]["display"] == "Against the original: starts 0.8 s early · ends on time"       # not "−0.8 s / +0.0 s"
    assert rows["silence"]["display"] == "20.2% vs 16.8% original"                      # not "16.8% → 20.2%"
    assert rows["clipping"]["display"] == "None"                                        # not "0.000%"
    # a check that wasn't measured has no dash on its row: its reason is in the row and the Not measured list
    assert all(m["display"] != "—" for m in rows.values() if m["level"] == "not_measured")


def test_the_parts_have_names_that_say_what_they_hold():
    from dubeval.report import build_report
    titles = {s["id"]: s["title"] for s in build_report(make_results(), "en")["sections"]}
    assert (titles["timing_audio"], titles["alignment"], titles["speech"]) == ("Length & sound", "Timing", "Speech & voice")


def test_the_speech_timing_row_counts_only_the_moments_it_lists():
    from dubeval.intervals import TIMING_MIN_SEC
    r = make_results()
    short = [{"start": 10.0 + i, "end": 10.0 + i + TIMING_MIN_SEC / 2, "kind": "dub_only"} for i in range(5)]
    r["timing_alignment"]["mismatches"] = short
    row = {m["id"]: m for s in build_report(r, "en")["sections"] for m in s["metrics"]}["speech_overlap"]
    assert "Things to check" not in row["message"]          # five too short to list: it promised them before
    r["timing_alignment"]["mismatches"] = short + [{"start": 20.0, "end": 21.5, "kind": "dub_only"}]
    row = {m["id"]: m for s in build_report(r, "en")["sections"] for m in s["metrics"]}["speech_overlap"]
    assert "short moment" not in row["message"]               # Good: the row lists no moments, so it promises none
    r["timing_alignment"]["overlap_pct"] = 70.0
    row = {m["id"]: m for s in build_report(r, "en")["sections"] for m in s["metrics"]}["speech_overlap"]
    assert "1 short moment" in row["message"]
    r["timing_alignment"]["mismatches"] = short                 # Needs review, none long enough: it says why none show
    row = {m["id"]: m for s in build_report(r, "en")["sections"] for m in s["metrics"]}["speech_overlap"]
    assert "too short to show on the timeline" in row["message"]


def test_the_score_rule_is_short_lines():
    rule = build_report(make_results(), "en")["score"]["rule"]
    assert rule.count(chr(10)) == 5 and all(len(line) < 400 for line in rule.split(chr(10)))


def test_language_names_follow_the_report_language():
    r = make_results()
    r["metadata"].update({"target_language": "es", "detected_source_language": "en"})
    r["pipeline"]["target_language_code"] = "es"
    ko = build_report(r, "ko")
    assert (ko["project"]["source_language"], ko["project"]["target_language"]) == ("영어", "스페인어")
    pt = build_report(r, "pt")
    assert pt["project"]["target_language"] == "Espanhol"                 # capitalized where it starts a line


def test_seconds_use_each_languages_unit():
    rows = {m["id"]: m for s in build_report(make_results(), "ko")["sections"] for m in s["metrics"]}
    assert rows["length_match"]["display"].split(" ")[0].endswith("초")


def test_the_html_timeline_marks_the_moments_the_report_lists_and_says_what_it_shows():
    r = make_results()
    r["timing_alignment"]["mismatches"] = [{"start": 3.0 + i, "end": 3.2 + i, "kind": "dub_only"} for i in range(5)]
    rep = build_report(r, "en")
    page = render_html(rep, r)
    timeline = page[page.index('aria-label="Speech timeline"'):]
    timeline = timeline[:timeline.index("</svg>")]
    assert timeline.count('fill="none" stroke=') == len(rep["moments"]) + 1     # each moment, plus the legend's swatch
    assert "Moment to check" in timeline and "Dub speaking" in timeline
    # the Passed heading counts the rows under it; information rows have their own
    good = sum(1 for s in rep["sections"] for m in s["metrics"] if m["level"] == "good")
    assert f"Passed ({good})</h2>" in page and "For information (" in page



def _row(mid, level="good", **extra):
    return {"id": mid, "label": mid, "level": level, "display": "", "message": "", "thresholds": "", "value": None,
            "score_points": None, **extra}


def _report_sections(**by_section):
    return [{"id": sid, "title": sid, "metrics": rows} for sid, rows in by_section.items()]


def _score_rows(level="good", **by_section):
    from dubeval.i18n import t as i18n_t
    from dubeval.report import _score
    return _score(lambda key, **p: i18n_t(key, "en", **p), _report_sections(**by_section), level)


BASE = dict(translation=[_row("translation_check")], alignment=[_row("speech_overlap"), _row("line_length")],
            speech=[_row("clarity"), _row("language")], timing_audio=[_row("length_match")],
            pairing=[_row("same_video")])


def test_lip_sync_on_a_dub_that_isnt_lip_synced_doesnt_apply_but_turned_off_lowers_the_coverage():
    na = _score_rows(**BASE, lipsync=[_row("lip_sync", "not_measured", absent="na")])
    off = _score_rows(**BASE, lipsync=[_row("lip_sync", "not_measured", absent="missing")])
    assert na["value"] == off["value"] == 100                     # both shared: the score itself is the same...
    assert na["coverage"] == 100 and off["coverage"] == 95        # ...but only the one that was off is a gap
    assert "Lip sync doesn't apply to this dub" in na["message"] and "were measured" not in na["message"]
    assert "Lip sync wasn't checked" in off["message"] and "95% of the checks that apply to this dub were measured" in off["message"]
    item = lambda sc: next(p for p in sc["parts"] if p["id"] == "lipsync")["items"][0]
    assert item(na)["display"] == "Doesn't apply to this dub · no share" and item(na)["absent"] == "na"
    assert item(off)["absent"] == "missing"


def test_a_dub_without_speech_counts_its_speech_checks_as_zero_instead_of_sharing_them():
    none = lambda mid: _row(mid, "not_measured", absent="dub")
    sc = _score_rows("poor", translation=[none("translation_check")],
                     alignment=[none("speech_overlap"), none("line_length")],
                     speech=[_row("speech_found", "poor"), none("clarity"), none("language")],
                     timing_audio=[_row("length_match")], pairing=[_row("same_video")],
                     lipsync=[_row("lip_sync", "not_measured", absent="na")])
    # Shared out, the length and same-video checks alone would have made it 100; counted as 0 it's 25 of 100, and the
    # Poor "no speech" result costs 40 at the least: nothing left.
    assert sc["raw"] == round(100 * (15 + 10) / 95, 1) and sc["value"] == 0 and not sc["provisional"]
    assert "count as 0 instead of being shared" in sc["message"] and sc["coverage"] == 100
    zero = next(p for p in sc["parts"] if p["id"] == "translation")["items"][0]
    assert zero["display"].startswith("Counts as 0") and zero["points"] == 0


def test_speech_that_couldnt_be_recognized_is_a_gap_not_the_dubs_fault_and_makes_the_score_provisional():
    gap = lambda mid: _row(mid, "not_measured")                  # "missing": the default kind
    sc = _score_rows("check", translation=[gap("translation_check")], alignment=[gap("speech_overlap")],
                     speech=[gap("clarity"), _row("voice_quality")], timing_audio=[_row("length_match")],
                     pairing=[_row("same_video")], lipsync=[_row("lip_sync")])
    # a gap, never 0 (recognition failed, not the dub): with 38% measured there is no score at all, rather than 99
    assert sc["value"] is None and sc["coverage"] == 38 and sc["provisional"]
    assert all(i["absent"] in (None, "missing") for p in sc["parts"] for i in p["items"])
    # with enough measured, the missing translation check makes it provisional, said once
    part = _score_rows("check", **{**BASE, "translation": [gap("translation_check")]}, lipsync=[_row("lip_sync")])
    assert part["message"].startswith("Provisional: the translation wasn't checked")
    assert "Provisional: only" not in part["message"]


def test_a_poor_result_outside_the_weighted_sections_still_costs_its_points():
    # a file without sound has no weight in the sum, but it makes the dub unusable: 100 points
    sc = _score_rows("poor", **BASE, lipsync=[_row("lip_sync")], integrity=[_row("file_check", "poor", display="No audio")])
    assert sc["raw"] == 100 and sc["value"] == 0 and sc["lost"][0]["id"] == "file_check" and sc["lost"][0]["lost"] == 100
    assert sc["lost"][0]["severity"] == "unusable" and sc["lost"][0]["why"] == "No audio · Poor: makes the dub unusable"


def test_a_poor_result_costs_by_how_serious_it_is():
    from dubeval.report import POOR_COSTS, POOR_SEVERITY
    assert POOR_COSTS == {"unusable": 100, "serious": 40, "minor": 20}
    # every check that can make a dub unusable, and the two the mix can fix; everything else is serious
    assert {k for k, v in POOR_SEVERITY.items() if v == "unusable"} == {"speech_found", "language", "same_video", "file_check"}
    assert {k for k, v in POOR_SEVERITY.items() if v == "minor"} == {"loudness_match", "silence"}
    with_poor = lambda section, mid: _score_rows("poor", **{**BASE, section: [_row(mid, "poor", display="x")]},
                                                 lipsync=[_row("lip_sync")])
    loud = with_poor("timing_audio", "loudness_match")       # Length & sound has one check here: its share is 15
    assert loud["lost"][0]["lost"] == 20 and loud["value"] == 80 and loud["lost"][0]["severity"] == "minor"
    assert loud["lost"][0]["why"] == "x · Poor: the mix can fix it"
    wrong = with_poor("speech", "language")                   # the wrong language: nothing deliverable
    assert wrong["value"] == 0 and wrong["lost"][0]["lost"] == 100
    timing = with_poor("alignment", "speech_overlap")         # serious: 40, as before
    assert timing["lost"][0]["lost"] == 40 and timing["lost"][0]["severity"] == "serious"
    # a minor problem whose share is more than 20 loses its share, never less: alone in Timing (25%) it loses 25
    big = _score_rows("poor", **{**BASE, "alignment": [_row("silence", "poor")]}, lipsync=[_row("lip_sync")])
    assert big["lost"][0]["lost"] == 25.0 and big["poor_cost"] == 0


def test_each_reason_for_not_measuring_is_sorted_into_its_kind():
    from dubeval.i18n import t as i18n_t
    from dubeval.report import _apply_speech_problem, _lipsync, _similarity, _sound_sync
    tr = lambda key, **p: i18n_t(key, "en", **p)
    # lip sync: a dub without re-drawn lips has none to check; turned off or not downloaded is a gap
    assert _lipsync(tr, {}, False)[0]["absent"] == "na"
    assert _lipsync(tr, {}, True)[0]["absent"] == "missing"
    assert _lipsync(tr, {"reason_key": "r.lips.no_download"}, True)[0]["absent"] == "missing"
    # the lip check ran but had nothing to compare (too few faces, an original whose own lips don't line up)
    assert _lipsync(tr, {"sync": {"measured": False, "reason_key": "r.sync_lips.few_moments",
                                  "reason_params": {"n": 2}}}, True)[0]["absent"] == "na"
    # voice similarity: another voice on purpose doesn't apply; the model not telling is a gap
    assert _similarity(tr, {"measured": False, "reason_key": "r.vs.not_compared_human"})["absent"] == "na"
    assert "absent" not in _similarity(tr, {"measured": False, "reason_key": "r.vs.no_model"})
    # sound sync on a dub that replaces the background: nothing to measure it against
    assert _sound_sync(tr, {"reason": "shared"})[0]["absent"] == "na"
    # no speech in the dub: its speech checks count as 0; none in the original: nothing to dub, they don't apply
    for kind, want in (("no_dub_speech", "dub"), ("no_original_speech", "na")):
        sections = [{"id": "speech", "metrics": [{"id": "clarity", "level": "not_measured"}]},
                    {"id": "translation", "metrics": [{"id": "translation_check", "level": "not_measured"}]}]
        _apply_speech_problem(tr, sections, {"kind": kind}, "Spanish")
        assert [m.get("absent") for s in sections for m in s["metrics"] if m["level"] == "not_measured"] == [want, want]


def test_too_little_measured_gives_no_score_instead_of_a_number_built_on_a_quarter_of_the_checks():
    gap = lambda mid: _row(mid, "not_measured")
    sc = _score_rows("check", translation=[gap("translation_check")], alignment=[gap("speech_overlap")],
                     speech=[gap("clarity"), gap("language")], timing_audio=[_row("length_match")],
                     pairing=[_row("same_video")], lipsync=[gap("lip_sync")])
    assert sc["value"] is None and sc["coverage"] == 25 and sc["display"] == "Too little measured"
    assert sc["message"] == "Only 25% of the checks that apply to this dub could be measured, too little for a score (it takes 50%)."
    # without a translation checker (70% measured) there still is one, provisional
    no_judge = _score_rows("check", **{**BASE, "translation": [gap("translation_check")]}, lipsync=[_row("lip_sync")])
    assert no_judge["value"] == 99 and no_judge["provisional"] and no_judge["coverage"] == 70


def test_a_poor_result_dubeval_isnt_sure_of_costs_only_its_share():
    # Little or unclear speech: a Poor row that doesn't make the verdict Poor (Needs review) loses its share, not 40.
    rows = {**BASE, "translation": [_row("translation_check", "poor")]}
    unsure = _score_rows("check", **rows, lipsync=[_row("lip_sync")])
    sure = _score_rows("poor", **rows, lipsync=[_row("lip_sync")])
    assert unsure["value"] == 70 and unsure["poor_cost"] == 0
    assert sure["value"] == 60 and sure["poor_cost"] == 10



def test_the_score_card_says_why_a_poor_row_lost_only_its_share_and_shows_no_table_without_a_score():
    from dubeval.report import render_text
    unsure = _score_rows("check", **{**BASE, "translation": [_row("translation_check", "poor", display="5.9 / 10")]},
                         lipsync=[_row("lip_sync")])
    assert unsure["lost"][0]["why"] == "5.9 / 10 · Poor, but DubEval isn't sure of it, so it loses only its share"
    rep = build_report(make_results(), "en")
    rep["score"] = {**rep["score"], "value": None, "display": "Too little measured", "message": "Only 26%."}
    text = render_text(rep)
    block = text[text.index("QUALITY SCORE"):]
    block = block[:block.index("──")]
    assert "Only 26%." in block and rep["labels"]["score_section"] not in block and rep["labels"]["score_none"] not in block
