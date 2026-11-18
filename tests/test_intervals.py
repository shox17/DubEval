"""Tests for problem intervals: merging, clipping, rounding, categories, and probable recognition errors."""
import pytest

from dubeval.i18n import t
from dubeval.intervals import build_intervals, group_moments, loudness_jumps, merge_intervals, total_seconds
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


# ---------------- moments ----------------
def test_findings_about_the_same_moment_are_one_moment_led_by_the_one_that_says_most():
    # A real dub: "missing speech" (44.3-45.4) and "the dub is silent" (44.3-45.5) were listed as two problems.
    found = merge_intervals([item(44.3, 45.5), item(44.3, 45.4, "missing_speech", "poor"),
                             item(50.0, 52.0, "unclear_speech"), item(60.0, 61.0)], 90)
    moments = group_moments(found)
    assert [(m["start"], m["end"], m["severity"]) for m in moments] == [(44.3, 45.5, "poor"), (50.0, 52.0, "check"),
                                                                        (60.0, 61.0, "check")]
    first = [found[i]["category"] for i in moments[0]["intervals"]]
    assert first == ["missing_speech", "timing_mismatch"]                  # the named cause leads, the silence follows
    assert [found[i]["moment"] for i in range(len(found))] == [0, 0, 1, 2]
    same_level = group_moments(merge_intervals([item(10.0, 12.0), item(10.0, 12.2, "mistranslation")], 90))
    assert same_level[0]["intervals"] == [1, 0]                            # at one level: by what it says


def test_a_long_range_does_not_swallow_a_short_one_inside_it():
    # A 9 s voice-quality window around a 1 s wording problem are two things to look at, not one.
    found = merge_intervals([item(0.0, 9.0, "voice_quality"), item(4.2, 5.4, "translation_wording")], 90)
    assert len(group_moments(found)) == 2


def test_findings_about_one_line_are_one_moment():
    # A line 16% too long that also runs 0.8 s into the next line: one card, though the two ranges only touch.
    long = {**item(6.4, 14.4, "line_length"), "line": 2}
    over = {**item(14.4, 15.2, "line_overrun"), "line": 2}
    other = {**item(20.0, 24.0, "line_length"), "line": 3}
    found = merge_intervals([long, over, other], 90)
    moments = group_moments(found)
    assert [(m["start"], m["end"]) for m in moments] == [(6.4, 15.2), (20.0, 24.0)]
    assert [found[i]["category"] for i in moments[0]["intervals"]] == ["line_overrun", "line_length"]


def test_a_timing_moment_quotes_the_words_and_never_the_judges_nothing():
    r = make_results(translation_judge=JUDGED)
    r["timing_alignment"]["mismatches"] = [{"start": 10.0, "end": 12.5, "kind": "original_only"},
                                           {"start": 20.0, "end": 21.0, "kind": "dub_only"}]
    r["speech_recognition"]["original_segments"] = [{"start": 9.5, "end": 12.6, "text": " My flight suit. "},
                                                    {"start": 30.0, "end": 31.0, "text": "Later."}]
    r["speech_recognition"]["dubbed_segments"] = [{"start": 19.8, "end": 21.2, "text": "어허허"}]
    found = {i["category"]: i for i in build_intervals(r, tr, "en")["intervals"]}
    silence, extra = found["long_silence"], found["timing_mismatch"]
    assert silence["original"] == "My flight suit." and silence["dubbed"] is None
    assert "“My flight suit.”" in silence["description"] and "“" not in silence["problem"]
    assert extra["dubbed"] == "어허허" and extra["original"] is None
    r["translation_judge"] = {**JUDGED, "issues": [{"type": "added", "severity": "major", "start_sec": 40.0,
                                                    "original": "(nothing)", "dubbed": "오.", "ideal_translation": "(nothing)",
                                                    "explanation": {"en": "Speech was added."}}]}
    added = next(i for i in build_intervals(r, tr, "en")["intervals"] if i["category"] == "added_speech")
    assert added["original"] is None and added["suggestion"] is None and "(nothing)" not in added["description"]


@pytest.mark.parametrize("lang, said, shown", [
    ("en", "The source is '(nothing)' but the translation provides a new sentence '좋았어'.",
     "The source has no speech but the translation provides a new sentence '좋았어'."),
    ("en", 'The dub says "오." ( \'(nothing)\' ) here.', 'The dub says "오." here.'),      # alone in brackets: dropped
    ("en", "Compared with (nothing), the dub adds a greeting.", "Compared with no speech, the dub adds a greeting."),
    ("ko", "원본은 “(nothing)”인데 더빙이 문장을 추가했습니다.", "원본은 말 없음인데 더빙이 문장을 추가했습니다."),
    ("es", "El original es (nothing).", "El original no tiene habla."),
    ("en", "Nothing was changed (nothing to fix).", "Nothing was changed (nothing to fix)."),   # ordinary words stay
])
def test_the_judges_placeholder_for_a_silent_track_is_put_into_words(lang, said, shown):
    from dubeval.intervals import local_text
    assert local_text({lang: said, "en": said}, lang) == shown


def test_a_local_judges_english_sentence_keeps_english_words_in_a_korean_report():
    from dubeval.intervals import local_text
    said = "The source is '(nothing)' but the translation provides a new sentence."       # a plain string: English only
    assert local_text(said, "ko") == "The source has no speech but the translation provides a new sentence."
    assert local_text({"en": said}, "ko") == "The source has no speech but the translation provides a new sentence."


@pytest.mark.parametrize("original, dubbed, lang, shown", [
    ("(nothing)", "좋았어", "en", "The original has no speech here, but the dub adds a line."),
    ("", "좋았어", "ko", "원본에는 이 부분에 말이 없는데, 더빙에 문장이 추가되었습니다."),
    ("All right.", "(nothing)", "en", "The original says something here, but the dub has no speech."),
    ("All right.", "", "es", "El original dice algo aquí, pero el doblaje no tiene habla."),
])
def test_a_line_with_one_silent_side_is_said_in_dubevals_own_words(original, dubbed, lang, shown):
    said = "The source is '(nothing)' but the translation provides a new sentence '좋았어'."
    kind = "added" if original in ("", "(nothing)") else "missing"
    r = make_results(translation_judge={**JUDGED, "issues": [{"type": kind, "severity": "minor", "start_sec": 40.0,
                                                              "original": original, "dubbed": dubbed,
                                                              "explanation": said}]})
    found = build_intervals(r, lambda key, **p: t(key, lang, **p), lang)["intervals"]
    item = next(i for i in found if i["category"] in ("added_speech", "missing_speech"))
    assert item["problem"].endswith(shown) and "(nothing)" not in item["description"]
    # a sentence that doesn't lean on the placeholder is the judge's own
    r["translation_judge"]["issues"][0]["explanation"] = "The dub adds a cheer that isn't in the original."
    found = build_intervals(r, lambda key, **p: t(key, lang, **p), lang)["intervals"]
    assert any(i["problem"].endswith("The dub adds a cheer that isn't in the original.") for i in found)



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
        {"start": 15.0, "end": 15.6, "kind": "dub_only"},         # 0.6 s: word-timing jitter, not listed
        {"start": 19.4, "end": 20.4, "kind": "dub_only"}]})
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
                        "unclear_segments": [{"start": 22.0, "end": 23.0, "text": "음"},
                                             {"start": 25.0, "end": 25.2, "text": "어"}]}})   # 0.2 s: not listed
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


def test_the_original_language_left_in_is_found_when_it_clearly_leads():
    # An 8 s English part in a Spanish dub: the 10 s window still hears some Spanish (about 0.3).
    windows = [{"start": 20.0, "end": 30.0, "language": "en", "probability": 0.74, "expected_probability": 0.29},
               {"start": 40.0, "end": 50.0, "language": "en", "probability": 0.55, "expected_probability": 0.45},
               {"start": 60.0, "end": 70.0, "language": "it", "probability": 0.9, "expected_probability": 0.3}]
    r = make_results(timing_alignment={"mismatches": []}, speech_recognition={"dubbed_language_windows": windows})
    r["metadata"]["target_language"] = "es"
    r["pipeline"]["target_language_code"] = "es"
    out = [i for i in build_intervals(r, tr, "en")["intervals"] if i["category"] == "wrong_language"]
    # English leads Spanish by 0.45: found; by only 0.1: unsure; another language needs Spanish under 0.2
    assert [(i["start"], i["severity"]) for i in out] == [(20.0, "check")]
