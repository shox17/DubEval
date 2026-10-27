"""Speech that can't be graded: a dub language recognition can't make out, and a side with no speech at all."""
import pytest

from dubeval.report import build_report, speech_problem
from sample_results import make_results


def rows(rep):
    return {m["id"]: m for s in rep["sections"] for m in s["metrics"]}


def uzbek_heard_as_kazakh(prob=0.47):
    r = make_results(speech_recognition={"dubbed_language_detected": "kk", "dubbed_language_probability": prob},
                     timing_alignment={"overlap_pct": 9.2})
    r["metadata"]["target_language"] = "uz"
    r["pipeline"] = {"target_language_code": "uz", "target_language_name": "Uzbek",
                     "input": {"source_language_code": "en", "source_language_name": "English"}}
    return r


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_an_unsure_third_language_is_a_recognition_failure_not_a_poor_dub(lang):
    rep = build_report(uzbek_heard_as_kazakh(), lang)
    m = rows(rep)
    # Not graded, with the reason: a known gap in recognizing less common languages, not a fault of the dub
    # (labelled set, 2026-10-25: three Uzbek dubs a person graded Good were all held at Check by this row).
    assert m["language"]["level"] == "not_measured" and "{" not in m["language"]["message"]
    for mid in ("clarity", "speech_overlap"):
        assert m[mid]["level"] == "not_measured" and "{" not in m[mid]["message"]
    assert rep["overall"]["level"] != "poor" or any(x["level"] == "poor" for x in m.values()
                                                    if x["id"] not in ("language", "clarity", "speech_overlap"))
    assert not [i for i in rep["problem_intervals"] if i["category"] in ("timing_mismatch", "long_silence")]


def test_a_confident_wrong_language_is_still_poor():
    r = make_results(speech_recognition={"dubbed_language_detected": "ja", "dubbed_language_probability": 0.9})
    assert speech_problem(r) is None and rows(build_report(r, "en"))["language"]["level"] == "poor"


def test_the_original_language_left_in_is_still_poor():
    r = make_results(speech_recognition={"dubbed_language_detected": "en", "dubbed_language_probability": 0.5})
    assert speech_problem(r) is None and rows(build_report(r, "en"))["language"]["level"] == "poor"


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_a_dub_without_any_speech_is_poor(lang):
    r = make_results(timing_alignment={"overlap_pct": None, "dubbed_speech": [], "mismatches": []},
                     speech_recognition={"dubbed_segments": [], "clarity": {}})
    assert speech_problem(r) == {"kind": "no_dub_speech"}
    rep = build_report(r, lang)
    found = rows(rep)["speech_found"]
    # Nothing was dubbed (labelled set, 2026-10-25: the person graded such a dub Poor).
    assert found["level"] == "poor" and rep["overall"]["level"] == "poor" and "{" not in found["message"]


def test_an_original_without_speech_is_flagged_too():
    r = make_results(timing_alignment={"overlap_pct": None, "original_speech": [], "mismatches": []})
    assert speech_problem(r) == {"kind": "no_original_speech"}
    found = rows(build_report(r, "en"))["speech_found"]
    assert "original" in found["message"] and found["level"] == "check"      # a silent original isn't the dub's fault


def test_the_judges_dont_run_on_unrecognized_speech(monkeypatch):
    # Judging recognition noise only grades the noise (an Uzbek dub heard as Kazakh scored 1 of 5), and costs a call.
    from dubeval import pipeline
    r = uzbek_heard_as_kazakh()
    called = []
    monkeypatch.setattr(pipeline, "judge_translation", lambda *a, **k: called.append(1))
    pipeline.check_translation(r, True, lambda *a: None)
    assert not called and r["translation_judge"]["reason_key"] == "r.judge.unrecognized"
    pipeline.check_meaning_screen(r, lambda *a: None)
    assert r["meaning_screen"]["reason_key"] == "r.screen.unrecognized"
    m = rows(build_report(r, "ko"))
    assert m["translation_check"]["level"] == "not_measured" and "{" not in m["translation_check"]["message"]


def test_normal_results_have_no_speech_problem():
    r = make_results()
    assert speech_problem(r) is None and "speech_found" not in rows(build_report(r, "en"))



def test_the_translation_check_is_not_graded_on_unrecognized_speech():
    from dubeval.translation_judge import CRITERIA, _result, _rubric_result
    r = uzbek_heard_as_kazakh()
    line = {"line": 1, **{c: 1 for c in CRITERIA}, **{f"{c}_reason": "Different." for c in CRITERIA},
            "ideal_translation": "", "error_type": "distortion", "may_be_recognition_error": False}
    r["translation_judge"] = _rubric_result([_result({"lines": [line]}, "gemini", "Gemini")],
                                            [{"n": 1, "start": 1.0, "end": 2.0, "original": "x", "dub": "y"}])
    rep = build_report(r, "en")
    assert rows(rep)["meaning"]["level"] == "not_measured"
    assert not [i for i in rep["problem_intervals"] if i["category"] == "mistranslation"]
