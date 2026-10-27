"""Tests for problem intervals: merging, clipping, rounding, categories, and probable recognition errors."""
import pytest

from dubeval.i18n import t
from dubeval.intervals import build_intervals, loudness_jumps, merge_intervals, total_seconds
from dubeval.report import build_report
from sample_results import JUDGED, make_results

tr = lambda key, **p: t(key, "en", **p)


def item(start, end, category="timing_mismatch", severity="check", description="x"):
    """A raw interval as the collectors build it."""
    return {"start": start, "end": end, "category": category, "category_label": category, "severity": severity,
            "check": "speech_overlap", "check_label": "Speech timing", "description": description}


def spans(intervals):
    """(start, end, category) of each interval."""
    return [(i["start"], i["end"], i["category"]) for i in intervals]


# ---------------- merging, clipping, rounding ----------------
def test_overlapping_and_adjacent_ranges_of_the_same_category_merge():
    out = merge_intervals([item(1.0, 2.0), item(1.5, 3.0), item(3.4, 4.0), item(10.0, 11.0)], 60)
    assert spans(out) == [(1.0, 4.0, "timing_mismatch"), (10.0, 11.0, "timing_mismatch")]
    assert out[0]["merged"] == 3


def test_a_gap_of_half_a_second_or_more_keeps_ranges_apart():
    assert len(merge_intervals([item(1.0, 2.0), item(2.5, 3.0)], 60)) == 2
    assert len(merge_intervals([item(1.0, 2.0), item(2.49, 3.0)], 60)) == 1


def test_different_categories_never_merge_and_output_is_sorted_by_start():
    out = merge_intervals([item(5.0, 6.0, "distortion"), item(1.0, 2.0, "unclear_speech"),
                           item(1.2, 2.2, "timing_mismatch")], 60)
    assert spans(out) == [(1.0, 2.0, "unclear_speech"), (1.2, 2.2, "timing_mismatch"), (5.0, 6.0, "distortion")]


def test_merged_range_keeps_the_worst_severity_and_its_description():
    out = merge_intervals([item(1.0, 2.0, description="minor"), item(2.2, 3.0, severity="poor", description="major")], 60)
    assert out[0]["severity"] == "poor" and out[0]["description"] == "major"


def test_ranges_are_clipped_to_the_video_and_rounded():
    out = merge_intervals([item(-1.0, 0.44), item(28.66, 31.0, "distortion"), item(12.345, 13.06, "unclear_speech")], 28.68)
    assert spans(out) == [(0.0, 0.4, "timing_mismatch"), (12.3, 13.1, "unclear_speech"), (28.6, 28.7, "distortion")]
    assert all(i["end"] - i["start"] >= 0.1 - 1e-9 for i in out)


def test_a_range_beyond_the_end_still_points_at_the_last_moment():
    (only,) = merge_intervals([item(40.0, 42.0)], 28.68)
    assert only["end"] <= 28.7 and only["end"] - only["start"] == pytest.approx(0.1)


def test_total_seconds_counts_overlaps_once():
    assert total_seconds([item(0.0, 2.0), item(1.0, 3.0, "distortion"), item(5.0, 5.5)]) == 3.5
    assert total_seconds([]) == 0.0


# ---------------- collectors ----------------
def test_long_silence_and_timing_mismatch_from_speech_timing():
    r = make_results(timing_alignment={"mismatches": [
        {"start": 2.0, "end": 7.0, "kind": "original_only"},      # 5 s silent dub: Poor long silence
        {"start": 10.0, "end": 12.5, "kind": "original_only"},    # 2.5 s: Check long silence
        {"start": 19.4, "end": 20.1, "kind": "dub_only"}]})
    out = build_intervals(r, tr, "en")["intervals"]
    assert [(i["category"], i["severity"]) for i in out] == [
        ("long_silence", "poor"), ("long_silence", "check"), ("timing_mismatch", "check")]
    assert "5.0 s" in out[0]["description"] and out[0]["check"] == "speech_overlap"


def test_translation_issues_become_ranges_and_recognition_errors_are_kept_apart():
    judged = {**JUDGED, "issues": [
        {"type": "missing", "severity": "major", "start_sec": 0.5, "original": "Thank you", "dubbed": "",
         "explanation": {"en": "The thank-you was dropped.", "ko": "감사 인사가 빠졌습니다.", "pt": "x", "es": "x"},
         "may_be_recognition_error": False},
        {"type": "name_or_number", "severity": "minor", "start_sec": 1.0, "original": "Inha", "dubbed": "이나",
         "explanation": "Name sounds wrong.", "may_be_recognition_error": True}]}
    found = build_intervals(make_results(translation_judge=judged, timing_alignment={"mismatches": []}), tr, "ko", dub="B")
    (missing,) = found["intervals"]
    assert (missing["start"], missing["end"]) == (0.5, 2.0)          # ends with the original line (0.0–2.0)
    assert missing["category"] == "missing_speech" and missing["severity"] == "poor" and missing["dub"] == "B"
    assert missing["description"].startswith("감사 인사가 빠졌습니다.") and "“Thank you”" in missing["description"]
    (asr,) = found["possible_asr_errors"]
    assert asr["asr"] and asr["category"] == "names_numbers" and asr["dub"] == "B"
    assert found["problem_seconds"] == 1.5                           # the recognition error doesn't count


def test_clipping_language_and_clarity_ranges():
    r = make_results(
        acoustic_metrics={"dubbed_clipping_intervals": [[3.0, 3.2], [3.5, 3.6]]},
        timing_alignment={"mismatches": []},
        speech_recognition={
            "dubbed_language_windows": [
                {"start": 0.0, "end": 10.0, "language": "ko", "probability": 0.97, "expected_probability": 0.97},
                {"start": 10.0, "end": 20.0, "language": "en", "probability": 0.9, "expected_probability": 0.05},
                {"start": 20.0, "end": 28.68, "language": "ja", "probability": 0.4, "expected_probability": 0.3}],
            "clarity": {"confident_pct": 80.0, "mean_logprob": -0.8, "segments": 3,
                        "unclear_segments": [{"start": 22.0, "end": 23.0, "text": "음"}]}})
    out = build_intervals(r, tr, "en")["intervals"]
    assert spans(out) == [(3.0, 3.6, "distortion"), (10.0, 20.0, "wrong_language"), (22.0, 23.0, "unclear_speech")]
    lang = out[1]
    assert lang["severity"] == "poor" and "English (US), the original language" in lang["description"]


def test_loudness_jump_is_found_beyond_the_usual_offset():
    orig = [-25.0] * 40
    dub = [-28.0] * 40                    # 3 dB quieter overall: normal, not a jump
    dub[20:28] = [-10.0] * 8              # 2 s about 18 dB louder than usual
    jumps = loudness_jumps({"step_sec": 0.25, "original_db": orig, "dubbed_db": dub})
    assert len(jumps) == 1
    start, end, db = jumps[0]
    assert 4.5 <= start <= 5.25 and 6.75 <= end <= 7.5 and db > 10
    assert loudness_jumps({"step_sec": 0.25, "original_db": orig, "dubbed_db": [-28.0] * 40}) == []


def test_report_lists_intervals_and_things_to_check_from_the_same_source():
    rep = build_report(make_results(timing_alignment={"mismatches": [{"start": 2.0, "end": 7.0, "kind": "original_only"}]}))
    assert [i["category"] for i in rep["problem_intervals"]] == ["long_silence"]
    assert rep["problem_seconds"] == 5.0
    assert rep["things_to_check"][0]["category"] == "long silence" and rep["things_to_check"][0]["end"] == 7.0


def test_noise_guessed_as_an_odd_language_is_not_flagged_but_the_original_language_is():
    windows = [{"start": 10.0, "end": 20.0, "language": "nn", "probability": 0.51, "expected_probability": 0.01},
               {"start": 20.0, "end": 30.0, "language": "en", "probability": 0.55, "expected_probability": 0.05},
               {"start": 40.0, "end": 50.0, "language": "ja", "probability": 0.9, "expected_probability": 0.02}]
    r = make_results(timing_alignment={"mismatches": []}, speech_recognition={"dubbed_language_windows": windows},
                     acoustic_metrics={"dubbed_duration_sec": 60.0, "original_duration_sec": 60.0})
    out = build_intervals(r, tr, "en")["intervals"]
    assert [(i["start"], i["severity"]) for i in out] == [(20.0, "check"), (40.0, "check")]
    assert "original language" in out[0]["description"] and "Japanese" in out[1]["description"]


def test_a_translation_issue_takes_the_line_starting_at_its_time():
    segs = [{"start": 23.78, "end": 26.84, "text": "a"}, {"start": 26.84, "end": 30.04, "text": "b"}]
    judged = {**JUDGED, "issues": [{"type": "missing", "severity": "minor", "start_sec": 26.8, "original": "b",
                                    "dubbed": "", "explanation": "x", "may_be_recognition_error": False}]}
    r = make_results(translation_judge=judged, timing_alignment={"mismatches": []},
                     speech_recognition={"original_segments": segs},
                     acoustic_metrics={"dubbed_duration_sec": 60.0, "original_duration_sec": 60.0})
    (i,) = build_intervals(r, tr, "en")["intervals"]
    assert (i["start"], i["end"]) == (26.8, 30.0)
