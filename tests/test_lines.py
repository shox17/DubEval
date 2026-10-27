"""Line by line: each dub line's length against the original's, lines running into the next, and their intervals."""
import pytest

from dubeval.evaluate import line_timing, match_segments
from dubeval.report import build_report
from sample_results import make_results


def seg(start, end, words=None):
    """A recognizer segment with word timings."""
    return {"start": start, "end": end, "text": "x", "avg_logprob": -0.2, "no_speech_prob": 0.0,
            "words": words or [[start, end]]}


def test_lines_are_measured_from_first_to_last_word():
    sa = match_segments([seg(0, 2.5, [[0.2, 1.0], [1.1, 2.2]])], [seg(0, 3.0, [[0.4, 2.8]])])
    (line,) = sa["lines"]
    assert (line["original_sec"], line["dub_sec"], line["diff_sec"]) == (2.0, 2.4, 0.4)
    assert line["diff_pct"] == 20.0 and line["start_shift_sec"] == 0.2 and line["short"] is False


def test_a_dub_line_running_into_the_next_original_line_is_found():
    sa = match_segments([seg(0, 2), seg(2.5, 4)], [seg(0, 2.0), seg(2.7, 4.2)])
    assert [ln["overrun_sec"] for ln in sa["lines"]] == [0.0, 0.0]
    sa = match_segments([seg(0, 2), seg(3.0, 6)], [seg(0, 3.8), seg(3.9, 6)])
    first = sa["lines"][0]
    assert first["overrun_sec"] == 0.8 and sa["lines"][1]["overrun_sec"] == 0.0
    sa = match_segments([seg(0, 2), seg(3.0, 6)], [seg(0, 3.4), seg(3.5, 6)])     # 0.4 s: not noticeable
    assert sa["lines"][0]["overrun_sec"] == 0.0


def test_short_lines_are_kept_but_not_graded():
    (line,) = line_timing([{"original_start": 0, "original_end": 0.6, "dub_start": 0, "dub_end": 1.2,
                            "original_sec": 0.6, "dub_sec": 1.2, "original": [0], "dub": [0]}])
    assert line["short"] is True and line["diff_pct"] == 100.0


def _line(n, start, o, d, overrun=0.0, short=False):
    return {"n": n, "start": start, "end": start + o, "original_sec": o, "dub_sec": d, "diff_sec": round(d - o, 2),
            "diff_pct": round((d - o) / o * 100, 1), "start_shift_sec": 0.0, "overrun_sec": overrun, "short": short,
            "original": [n - 1], "dub": [n - 1]}


def _levels(lines, lang="en"):
    rep = build_report(make_results(segment_alignment={"groups": [], "lines": lines}), lang)
    rows = {m["id"]: m for s in rep["sections"] for m in s["metrics"]}
    return rows, rep


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_line_fit_is_graded_in_every_language(lang):
    fits = [_line(i, i * 5.0, 3.0, 3.2) for i in range(1, 11)]                # all within ±15%
    rows, _ = _levels(fits, lang)
    assert rows["line_length"]["level"] == "good" and rows["line_overrun"]["level"] == "good"
    some = fits[:8] + [_line(9, 45.0, 3.0, 4.0), _line(10, 50.0, 3.0, 2.0)]   # 8 of 10 fit
    rows, _ = _levels(some, lang)
    assert rows["line_length"]["level"] == "check" and rows["line_length"]["value"] == 80.0
    assert all("{" not in rows[k]["message"] + rows[k]["display"] for k in ("line_length", "line_overrun"))


def test_most_lines_off_is_poor_and_each_becomes_an_interval():
    lines = [_line(1, 0.0, 3.0, 4.5), _line(2, 5.0, 3.0, 3.5), _line(3, 10.0, 3.0, 3.0, overrun=1.2),
             _line(4, 15.0, 0.5, 2.0, short=True), _line(5, 20.0, 3.0, 2.0, overrun=0.7),
             _line(6, 25.0, 3.0, 3.0, overrun=0.6)]
    rows, rep = _levels(lines)
    assert rows["line_length"]["level"] == "poor"                           # 2 of 5 graded lines fit, 3 off
    assert rows["line_overrun"]["level"] == "poor"                          # 3 of 6 lines run over
    found = {(i["category"], i["severity"], i["start"]) for i in rep["problem_intervals"]}
    assert ("line_length", "poor", 0.0) in found                            # +50%
    assert ("line_length", "check", 5.0) in found                           # +16.7%
    assert ("line_overrun", "poor", 13.0) in found                          # from line 3's end, 1.2 s in
    assert not any(i["start"] == 15.0 and i["category"] == "line_length" for i in rep["problem_intervals"])


def test_one_or_two_problem_lines_are_at_most_check():
    rows, _ = _levels([_line(1, 0.0, 4.0, 2.9), _line(2, 5.0, 3.0, 3.1)])   # 1 of 2 off: 50% but only one line
    assert rows["line_length"]["level"] == "check"
    rows, _ = _levels([_line(1, 0.0, 3.0, 3.0, overrun=1.5), _line(2, 5.0, 3.0, 3.0)])
    assert rows["line_overrun"]["level"] == "check"


def test_tiny_differences_are_never_a_problem():
    _, rep = _levels([_line(1, 0.0, 1.2, 1.45)])                            # +20.8% but only 0.25 s
    assert not [i for i in rep["problem_intervals"] if i["category"] == "line_length"]


def test_no_gradable_lines_is_not_measured():
    rows, _ = _levels([_line(1, 0.0, 0.5, 0.9, short=True)])
    assert rows["line_length"]["level"] == "not_measured" and "line_overrun" not in rows


def test_results_without_line_timing_have_no_line_rows():
    rows, _ = _levels([])
    rep = build_report(make_results(), "en")
    assert all(m["id"] not in ("line_length", "line_overrun") for s in rep["sections"] for m in s["metrics"])
