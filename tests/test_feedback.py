"""Tests for reviewer feedback: votes on problem intervals, the latest vote winning, per-check summaries, CLI, app."""
import json

import pytest

from dubeval import cli, feedback

PROJECT = {"perso_seq": 100001, "share_url": "https://perso.ai/x?seq=y", "title": "QA sample"}


def iv(start: float, check: str = "speech_overlap", category: str = "timing_mismatch") -> dict:
    """A problem interval."""
    return {"category": category, "check": check, "start": start, "end": start + 1.0, "severity": "check"}


def test_votes_are_stored_and_the_latest_vote_on_an_interval_wins():
    feedback.vote(PROJECT, iv(1.0), "real")
    feedback.vote(PROJECT, iv(1.0), "false_alarm")                    # changed their mind
    feedback.vote(PROJECT, iv(5.0), "real", reviewer="mina")
    current = feedback.latest()
    assert len(feedback.load()) == 3 and len(current) == 2
    assert current["100001|timing_mismatch|1.0|2.0"]["vote"] == "false_alarm"
    assert current["100001|timing_mismatch|5.0|6.0"]["reviewer"] == "mina"
    with pytest.raises(ValueError):
        feedback.vote(PROJECT, iv(9.0), "maybe")


def test_summary_says_which_checks_flag_too_much():
    for s in (1, 2, 3, 4):
        feedback.vote(PROJECT, iv(s, "clarity", "unclear_speech"), "false_alarm" if s != 4 else "real")
    for s in (10, 11, 12):
        feedback.vote(PROJECT, iv(s), "real")
    feedback.vote(PROJECT, iv(20, "voice_quality", "voice_quality"), "false_alarm")
    summary = feedback.summarize(feedback.load())
    by = {c["check"]: c for c in summary["checks"]}
    assert (summary["intervals"], summary["real"], summary["confirmed_pct"]) == (8, 4, 50.0)
    assert by["clarity"]["status"] == "noisy" and by["clarity"]["confirmed_pct"] == 25.0
    assert by["speech_overlap"]["status"] == "reliable" and by["voice_quality"]["status"] == "few"
    assert summary["checks"][0]["check"] == "clarity"                 # most false alarms first
    text = feedback.render_feedback_text(summary, "en")
    assert "8 intervals reviewed: 4 real problems, 4 false alarms (50% confirmed)" in text
    assert "flags too much" in text and "Voice clarity" in text
    assert "검토자 피드백" in feedback.render_feedback_text(summary, "ko")


def test_feedback_cli(capsys):
    assert cli.main(["feedback", "--lang", "en"]) == 0
    assert "No votes yet" in capsys.readouterr().out
    feedback.vote(PROJECT, iv(1.0), "real")
    assert cli.main(["feedback", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["real"] == 1
