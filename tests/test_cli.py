"""Tests for the command line (qa.py): output, saved files message and exit codes."""
import pytest

from dubeval import cli
from dubeval.perso_api import PersoError
from dubeval.report import build_report
from sample_results import make_results


def fake_run(level_results):
    """A run_share_evaluation stand-in that returns the given results with a built report."""
    def run(url, **kw):
        r = level_results
        r["report"] = build_report(r)
        r["pipeline"]["report_files"] = {"html": "/tmp/report.html", "json": "/tmp/report.json", "text": "/tmp/report.txt"}
        return r
    return run


def test_prints_text_report_and_saved_paths(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_share_evaluation", fake_run(make_results()))
    assert cli.main(["https://perso.ai/en/share/video-translator?seq=abc"]) == 0
    out, err = capsys.readouterr()
    assert "DUBBING QA REPORT" in out and "OVERALL" in out
    assert "report.html" in err


def test_json_output(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_share_evaluation", fake_run(make_results()))
    cli.main(["x", "--json"])
    assert '"overall"' in capsys.readouterr().out


@pytest.mark.parametrize("fail_on, code", [("never", 0), ("poor", 1), ("check", 1)])
def test_fail_on_exit_codes(monkeypatch, fail_on, code):
    poor = make_results(acoustic_metrics={"dubbed_duration_sec": 40.0})
    monkeypatch.setattr(cli, "run_share_evaluation", fake_run(poor))
    assert cli.main(["x", "--fail-on", fail_on]) == code


def test_errors_exit_2_with_plain_message(monkeypatch, capsys):
    def boom(url, **kw):
        raise PersoError("Sharing is turned off for this Perso project.")
    monkeypatch.setattr(cli, "run_share_evaluation", boom)
    assert cli.main(["x"]) == 2
    assert "Could not evaluate: Sharing is turned off" in capsys.readouterr().err


def test_lip_movement_is_automatic_by_default(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "run_share_evaluation", lambda url, **kw: seen.update(kw) or fake_run(make_results())(url))
    cli.main(["link", "--lang", "ko"])
    assert seen["include_lipsync"] is None and seen["report_lang"] == "ko"


def test_options_are_passed_through(monkeypatch, tmp_path):
    seen = {}

    def run(url, **kw):
        seen.update(kw, url=url)
        return fake_run(make_results())(url)
    script = tmp_path / "s.txt"
    script.write_text("안녕하세요", encoding="utf-8")
    monkeypatch.setattr(cli, "run_share_evaluation", run)
    cli.main(["link", "--script-file", str(script), "--no-lipsync", "--no-translation-check", "--whisper-model", "base"])
    assert seen["ground_truth_text"] == "안녕하세요" and seen["include_lipsync"] is False
    assert seen["report_lang"] == "ko" and seen["out_dir"] == "output"          # defaults: Korean, ./output
    assert seen["use_translation_judge"] is False and seen["whisper_model_name"] == "base"
