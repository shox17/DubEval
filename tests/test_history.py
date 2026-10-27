"""Tests for the evaluation history: recording, reading, summaries, the CLI view and the app page."""
import csv
import json
from datetime import date

from dubeval import cli, history, pipeline
from dubeval.report import build_report
from fake_perso import SHARE_TOKEN, SHARE_TOKEN_B, SHARE_URL, SHARE_URL_B, SHARED_PROJECT, SHARED_PROJECT_B, FakePerso
from sample_results import make_results

NO_SLEEP = lambda s: None


def evaluated(**sections) -> dict:
    """Results with a built report, as the pipeline records them."""
    r = make_results(**sections)
    r["report"] = build_report(r)
    return r


def rec(when: str, verdict: str, seq: int, pair: str = "en→ko", languages: str = "English → Korean", **levels) -> dict:
    """A history record."""
    return {"time": when, "verdict": verdict, "seq": seq, "link": f"L{seq}", "title": f"T{seq}", "mode": "single",
            "language_pair": pair, "languages": languages, "overlap_pct": 80.0, "meaning_score": 4,
            "levels": levels or {"length_match": "good"}}


def test_record_and_load_round_trip_and_skip_broken_lines():
    history.record(evaluated(), "single")
    history.record(evaluated(acoustic_metrics={"dubbed_duration_sec": 40.0}), "compare")
    with open(history.history_file(), "a", encoding="utf-8") as f:
        f.write("{not json\n")
    records = history.load()
    assert [(r["verdict"], r["mode"]) for r in records] == [("good", "single"), ("poor", "compare")]
    first = records[0]
    assert first["seq"] == 100001 and first["language_pair"] == "en→ko" and first["levels"]["length_match"] == "good"
    assert first["languages"] == "English (US) → Korean" and first["tool_version"]


def test_recording_never_breaks_a_run(monkeypatch, tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("x")
    monkeypatch.setattr(history, "HISTORY_FILE", blocked / "history.jsonl")      # parent is a file: can't write
    history.record(evaluated(), "single")                                          # logged, not raised
    history.record({"no": "report"}, "single")


def test_summary_counts_reruns_once_and_groups_by_language_pair():
    records = [rec("2026-09-01 10:00:00", "poor", 1, timing="poor"),
               rec("2026-09-02 10:00:00", "good", 1),                              # rerun of the same link: wins
               rec("2026-09-08 09:00:00", "check", 2, "en→es", "English → Spanish", clarity="check"),
               rec("2026-09-09 09:00:00", "poor", 3, "en→es", "English → Spanish", clarity="poor", speech_rate="check")]
    s = history.summarize(records)
    assert (s["runs"], s["dubs"]) == (4, 3) and s["verdicts"] == {"good": 1, "check": 1, "poor": 1}
    assert s["good_pct"] == 33.3
    es = next(p for p in s["pairs"] if p["pair"] == "en→es")
    # Meaning out of 10: these records predate the rubric (scored 1-5), so their 4 / 5 shows as 8 / 10.
    assert (es["dubs"], es["check"], es["poor"], es["overlap_pct"], es["meaning_score"]) == (2, 1, 1, 80.0, 8.0)
    assert s["problems"][0] == {"measure": "clarity", "check": 1, "poor": 1, "dubs": 2}
    assert [w["week"] for w in s["weekly"]] == ["2026-08-31", "2026-09-07"]
    assert s["recent"][0]["seq"] == 3                                              # newest first, every run
    recent = history.summarize(records, days=5, today=date(2026, 9, 12))     # since 7 September
    assert recent["dubs"] == 2


def test_history_text_in_two_languages():
    s = history.summarize([rec("2026-09-01 10:00:00", "good", 1), rec("2026-09-02 10:00:00", "poor", 2, clarity="poor")])
    text = history.render_history_text(s, "en")
    assert "EVALUATION HISTORY" in text and "2 runs on 2 dubs" in text and "Voice clarity" in text
    assert "평가 기록" in history.render_history_text(s, "ko")
    assert "No evaluations recorded yet" in history.render_history_text(history.summarize([]), "en")


def test_the_pipeline_records_single_compare_and_batch_runs(monkeypatch, isolated_output, tmp_path):
    fake = FakePerso(projects={SHARE_TOKEN: dict(SHARED_PROJECT), SHARE_TOKEN_B: dict(SHARED_PROJECT_B)})
    monkeypatch.setattr(pipeline, "run_full_evaluation",
                        lambda **kw: {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")})
    pipeline.run_share_evaluation(SHARE_URL, use_translation_judge=False, session=fake, sleep=NO_SLEEP)
    pipeline.run_comparison(SHARE_URL, SHARE_URL_B, str(tmp_path / "c"), use_translation_judge=False,
                            session=fake, sleep=NO_SLEEP)
    pipeline.run_batch([{"link": SHARE_URL_B, "label": None}], str(tmp_path / "b"), use_translation_judge=False,
                       session=fake, sleep=NO_SLEEP)
    assert [r["mode"] for r in history.load()] == ["single", "compare", "compare", "batch"]


def test_history_cli_prints_the_summary_and_writes_csv(tmp_path, capsys):
    history.record(evaluated(), "single")
    out = tmp_path / "h.csv"
    assert cli.main(["history", "--lang", "en", "--csv", str(out)]) == 0
    assert "1 runs on 1 dubs" in capsys.readouterr().out
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
    assert rows[0]["verdict"] == "good" and rows[0]["languages"] == "English (US) → Korean"
    assert cli.main(["history", "--json"]) == 0 and json.loads(capsys.readouterr().out)["dubs"] == 1


def test_reruns_of_the_same_files_count_once():
    from dubeval.history import latest_per_link
    a1 = {"seq": None, "link": "", "inputs": "o.mp4|a.mp4", "verdict": "poor"}
    a2 = {"seq": None, "link": "", "inputs": "o.mp4|a.mp4", "verdict": "good"}
    b = {"seq": None, "link": "", "inputs": "o.mp4|b.mp4", "verdict": "check"}
    assert [r["verdict"] for r in latest_per_link([a1, b, a2])] == ["good", "check"]


def test_renaming_a_run_changes_its_title_in_the_history(tmp_path):
    from sample_results import make_results
    from dubeval.report import build_report
    r = make_results()
    r["report"] = build_report(r, "en")
    r["pipeline"]["report_files"] = {"html": str(tmp_path / "report.html")}
    history.record(r, "web")
    history.rename(str(tmp_path / "report.html"), "New name")
    assert [e["title"] for e in history.load()] == ["New name"]
