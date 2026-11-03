"""The numbers check: digits each dub line says against its original line, without an AI."""
import pytest

from dubeval import numbers, pipeline
from dubeval.report import build_report
from tests.sample_results import make_results


def line(n, original, dub, start=None):
    start = float(n * 3) if start is None else start
    return {"n": n, "start": start, "end": start + 2.0, "original": original, "dub": dub}


@pytest.mark.parametrize("text, expected", [
    ("It costs 1,000 dollars", ["1000"]), ("Cuesta 1.000 dólares", ["1000"]), ("3,5 metros", ["3.5"]),
    ("3.50 dollars", ["3.5"]), ("at 3:30", ["3", "30"]), ("35% more", ["35"]), ("year 2024년", ["2024"]),
    ("007", ["7"]), ("no numbers here", []),
])
def test_numbers_are_normalized_across_languages(text, expected):
    assert numbers.numbers_in(text) == expected


def test_a_changed_number_is_found():
    # The planted mistake of the validation: "35%" became "75%" (the local judge missed all six).
    out = numbers.check([line(1, "Prices rose 35% this year.", "올해 가격이 75% 올랐습니다."),
                         line(2, "Thank you.", "감사합니다.")])
    assert out["measured"] and out["compared"] == 1
    assert [(c["n"], c["original"], c["dub"]) for c in out["lines"]] == [(1, ["35"], ["75"])]


def test_the_same_numbers_written_differently_match():
    out = numbers.check([line(1, "It costs 1,000 dollars at 3:30.", "3시 30분에 1000달러입니다.")])
    assert out["measured"] and out["lines"] == []


@pytest.mark.parametrize("original, dub", [
    ("We open on July 4.", "7월 4일에 엽니다."),                         # a date: the dub has a month number too
    ("Come at half past 3.", "3시 30분에 오세요."),
    ("It sold 2 million copies.", "200만 장이 팔렸습니다."),             # another unit: same digits, other zeros
    ("It costs $30,000.", "3만 달러입니다."),
    ("About 1.5 million people.", "약 150만 명입니다."),
    ("It costs 15,000 won.", "1만 5000원입니다."),                       # one number said in two parts
    ("It costs 10,000 euros.", "Cuesta 10 000 euros."),                  # spaces between thousands
    ("Prices rose 35%.", "ارتفعت الأسعار ٣٥%."),                         # other digits
])
def test_the_same_number_said_another_way_is_not_a_change(original, dub):
    out = numbers.check([line(1, original, dub)])
    assert out["measured"] and out["lines"] == []


def test_a_replaced_number_next_to_a_date_is_still_found():
    out = numbers.check([line(1, "We open on July 14.", "7월 4일에 엽니다.")])
    assert [(c["original"], c["dub"]) for c in out["lines"]] == [(["14"], ["7", "4"])]


def test_a_number_split_into_the_next_line_is_not_a_mismatch():
    out = numbers.check([line(1, "We started in 2019", "우리는 시작했습니다"),
                         line(2, "with 12 people.", "2019년에 12명으로.")])
    assert out["lines"] == []


def test_a_number_said_as_a_word_on_one_side_is_not_compared():
    out = numbers.check([line(1, "I have 3 cats.", "고양이가 세 마리 있어요.")])
    assert not out["measured"] and out["reason_key"] == "r.num.words" and out["with_numbers"] == 1
    assert numbers.check([line(1, "Hello.", "안녕하세요.")])["reason_key"] == "r.num.none"


def results_with(original, dub):
    r = make_results()
    r["speech_recognition"]["original_segments"] = [{"start": 0.0, "end": 2.0, "text": original}]
    r["speech_recognition"]["dubbed_segments"] = [{"start": 0.1, "end": 2.1, "text": dub}]
    r["segment_alignment"] = {"groups": [], "unmatched_original": [], "unmatched_dub": [], "lines": [
        {"n": 1, "start": 0.0, "end": 2.0, "original": [0], "dub": [0], "original_sec": 2.0, "dub_sec": 2.0,
         "diff_sec": 0.0, "diff_pct": 0.0, "start_shift_sec": 0.0, "overrun_sec": 0.0, "short": False}]}
    pipeline.check_numbers(r)
    return r


def numbers_row(rep):
    return next((m for s in rep["sections"] for m in s["metrics"] if m["id"] == "numbers"), None)


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_a_changed_number_is_check_and_a_moment_to_listen_to(lang):
    rep = build_report(results_with("Prices rose 35% this year.", "올해 가격이 75% 올랐습니다."), lang)
    row = numbers_row(rep)
    assert row["level"] == "check" and "{" not in row["message"] + row["display"] + row["thresholds"]
    moments = [i for i in rep["problem_intervals"] if i["check"] == "numbers"]
    assert len(moments) == 1 and moments[0]["category"] == "names_numbers" and moments[0]["severity"] == "check"
    assert "35" in moments[0]["description"] and "75" in moments[0]["description"]


def test_matching_numbers_are_good_and_no_numbers_add_no_row():
    assert numbers_row(build_report(results_with("It's 2024.", "2024년입니다."), "en"))["level"] == "good"
    assert numbers_row(build_report(results_with("Hello.", "안녕하세요."), "en")) is None
    assert numbers_row(build_report(make_results(), "en")) is None          # results from before the check


def test_numbers_are_not_graded_when_the_dub_language_was_not_recognized(monkeypatch):
    monkeypatch.setattr(pipeline, "_speech_unrecognized", lambda r: True)
    r = results_with("Prices rose 35%.", "75%")
    assert r["numbers"]["reason_key"] == "r.num.unrecognized"
    assert numbers_row(build_report(r, "en"))["level"] == "not_measured"
