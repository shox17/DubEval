"""Tests for the report: levels, messages, verdict rule, things to check, renderers, and the timing math."""
import pytest

from dubeval.evaluate import speech_clarity, speech_intervals, timing_alignment
from dubeval.report import build_report, render_html, render_text
from sample_results import JUDGED, make_results


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


@pytest.mark.parametrize("ratio, level", [(1.0, "good"), (0.75, "check"), (0.5, "poor"), (1.3, "check")])
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
    t = rep["things_to_check"][0]
    assert (t["start"], t["end"], t["category"]) == (19.4, 20.1, "timing")
    low = build_report(make_results(timing_alignment={"overlap_pct": 50.0}))
    assert metric(low, "speech_overlap")["level"] == "poor"


def test_missing_judge_is_not_measured_with_a_reason():
    rep = build_report(make_results())
    ids = {x["id"]: x["reason"] for x in rep["not_measured"]}
    assert "script_accuracy" not in ids          # an optional extra (CLI --script), not a gap
    assert "turned off" in ids["translation_check"]
    assert metric(rep, "translation_check")["value"] is None
    assert rep["overall"]["counts"]["not_measured"] == 1            # one translation row, not three


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
    assert metric(rep, "lip_movement")["level"] == "info"
    skipped = make_results(lipsync_metrics={"measured": False, "valid": False, "reason": "skipped (turned off for this run)"})
    skipped["pipeline"]["share"]["is_lipsync"] = False
    row = metric(build_report(skipped), "lip_movement")
    assert row["level"] == "not_measured" and "isn't lip-synced" in row["message"]


def test_script_score_appears_when_a_script_was_given():
    rep = build_report(make_results(speech_recognition={"accuracy_pct": 62.0, "error_rate": 0.38, "primary_metric": "cer"}))
    assert metric(rep, "script_accuracy")["level"] == "check" and "62% of your script" in metric(rep, "script_accuracy")["message"]
    assert "script_accuracy" not in {x["id"] for x in rep["not_measured"]}


def test_renderers_show_verdict_sections_and_things_to_check():
    r = make_results()
    rep = build_report(r)
    text = render_text(rep)
    assert "OVERALL:  ✅  GOOD" in text and "3. TIMING ALIGNMENT" in text and "00:19.4–00:20.1" in text
    assert "Perso #100001" in text and "NOT MEASURED" in text
    page = render_html(rep, r, "original.mp4", "dubbed_ko.mp4")
    assert page.startswith("<!doctype html>") and "prefers-color-scheme:dark" in page
    assert "<video" in page and "Speech timeline" in page and "Things to check" in page
    assert "안녕하세요" in page                                      # evidence transcripts


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


def test_timing_alignment_overlap_and_mismatches():
    same = timing_alignment([[0, 5], [6, 10]], [[0, 5], [6, 10]], 10)
    assert same["overlap_pct"] == 100.0 and same["mismatches"] == []
    shifted = timing_alignment([[0, 5]], [[1, 6]], 10)
    assert 60 < shifted["overlap_pct"] < 70
    kinds = {m["kind"] for m in shifted["mismatches"]}
    assert kinds == {"dub_only", "original_only"} and shifted["start_offset_sec"] == 1
    assert timing_alignment([], [[0, 1]], 10)["overlap_pct"] is None


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


def translation_rows(r, lang="en"):
    return {m["id"]: m for s in build_report(r, lang)["sections"] for m in s["metrics"]}


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_rubric_rows_show_every_criterion_with_its_average(lang):
    rows = translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (8, 9, False))), lang)
    for mid in ("meaning", "naturalness", "context_fit", "terminology", "localization"):
        assert rows[mid]["level"] == "good" and "/ 10" in rows[mid]["display"]
        assert "{" not in rows[mid]["message"] + rows[mid]["thresholds"] + rows[mid]["label"]
    assert rows["meaning"]["value"] == 8.5 and "completeness" not in rows


def test_one_serious_meaning_error_is_poor_and_a_weak_line_is_check():
    assert translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (4, 9, False))))["meaning"][
        "level"] == "poor"
    assert translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (6, 9, False))))["meaning"][
        "level"] == "check"
    assert translation_rows(make_results(translation_judge=rubric_result((7, 9, False))))["meaning"]["level"] == "good"


def test_the_other_criteria_reach_check_at_most():
    rows = translation_rows(make_results(translation_judge=rubric_result((9, 1, False))))
    assert rows["naturalness"]["level"] == "check" and rows["meaning"]["level"] == "good"


def test_a_possibly_misheard_line_never_lowers_a_level():
    rows = translation_rows(make_results(translation_judge=rubric_result((9, 9, False), (2, 9, True))))
    assert rows["meaning"]["level"] == "good" and "recognition error" in rows["meaning"]["message"]


def test_a_rubric_problem_is_a_timed_interval_with_its_type_and_suggested_translation():
    rep = build_report(make_results(translation_judge=rubric_result((9, 9, False), (4, 9, False), (9, 5, False))), "en")
    wrong = [i for i in rep["problem_intervals"] if i["category"] == "mistranslation"]
    wording = [i for i in rep["problem_intervals"] if i["category"] == "translation_wording"]
    assert wrong and wrong[0]["severity"] == "poor" and "Meaning distorted" in wrong[0]["description"]
    assert "Suggested translation: “더 나은 번역”" in wrong[0]["description"]
    assert wording and wording[0]["severity"] == "check" and "Word choice" in wording[0]["description"]


def test_results_saved_before_the_rubric_still_show_as_before():
    old = {"measured": True, "model": "gemini", "meaning_score": 4, "summary": {"en": "Fine."}, "issues": []}
    rows = translation_rows(make_results(translation_judge=old))
    assert rows["meaning"]["display"] == "4 / 5" and "completeness" in rows
