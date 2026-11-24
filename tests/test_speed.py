"""The time estimate (dubeval/speed.py) and the desktop app's "finished" notification (webapp._notification)."""
import json
import os
import time

from dubeval import jobs, speed, webapp


def _job(status="running", kind="files", media_sec=120.0, dubs=1, elapsed=0.0, **params):
    job = jobs.Job(id="0123456789ab", params={"kind": kind, "dubs": ["d"] * dubs, **params}, stages=["prepare"],
                   status=status)
    job.media_sec = media_sec
    job.started_at = time.time() - elapsed
    if status != "running":
        job.finished_at = time.time()
    if status == "done":
        job.result = {"pipeline": {"reused_measurements": False}}       # measured everything itself
    return job


def test_no_estimate_until_this_computer_has_finished_an_evaluation():
    assert speed.remaining(_job()) is None


def test_the_estimate_is_the_usual_speed_times_the_video_minus_the_time_so_far():
    for elapsed in (180, 200, 220):                      # 2-minute videos: 90, 100, 110 s per minute
        speed.record(_job(status="done", elapsed=elapsed))
    left = speed.remaining(_job(elapsed=50))            # the middle, 100 s a minute x 2 minutes, less 50 s
    assert 145 <= left <= 155
    assert speed.remaining(_job(elapsed=500)) is None    # longer than usual: no number rather than a wrong one


def test_a_comparison_counts_each_dub_and_a_short_clip_counts_as_half_a_minute():
    speed.record(_job(status="done", elapsed=100, media_sec=60))          # 100 s per minute
    assert 290 <= speed.remaining(_job(kind="comparison", dubs=3, media_sec=60)) <= 300
    assert speed.remaining(_job(media_sec=5)) == 50                      # loading models takes time anyway


def test_continued_failed_and_unknown_length_runs_teach_nothing():
    speed.record(_job(status="done", elapsed=10, continued=True))       # reused what was measured before
    speed.record(_job(status="failed", elapsed=10))
    speed.record(_job(status="done", elapsed=10, media_sec=None))
    speed.record(_job(status="done", elapsed=10, kind="pack"))          # a model download
    again = _job(status="done", elapsed=10)
    again.result["pipeline"]["reused_measurements"] = True              # the same files again: done in seconds
    speed.record(again)
    speed.record(_job(status="done", elapsed=10, kind="comparison", dubs=2))   # dub B reuses the original's measuring
    assert not speed.SPEED_FILE.exists()


def test_only_the_last_evaluations_count():
    for i in range(speed.KEEP + 5):
        speed.record(_job(status="done", elapsed=60 + i, media_sec=60))
    rates = json.loads(speed.SPEED_FILE.read_text(encoding="utf-8"))["rates"]
    assert len(rates) == speed.KEEP and rates[-1] == 60 + speed.KEEP + 4


def test_the_notification_says_how_the_evaluation_ended_in_its_language():
    done = _job(status="done", request={"lang": "en"})
    done.result = {"report": {"project": {"title": "Interview"}, "overall": {"label": "Needs review"}}}
    note = webapp._notification(done)
    assert note == {"title": "Evaluation finished", "body": "Interview · Needs review", "open": "#/report/0123456789ab"}
    ko = _job(status="done", kind="comparison", request={"lang": "ko"})
    ko.result = {"comparison": {"recommendation": {"title": "Film", "headline": "Dub A"}}}
    assert webapp._notification(ko)["title"] == "비교가 끝났습니다" and webapp._notification(ko)["open"].startswith("#/compare/")
    failed = _job(status="failed", request={"lang": "en"})
    failed.error = "The original video can't be read. Check that it's a video or audio file and not damaged."
    assert webapp._notification(failed)["open"] == "#/job/0123456789ab"


def test_no_notification_for_a_stopped_run_or_a_download(monkeypatch, capsys):
    assert webapp._notification(_job(status="cancelled")) is None
    assert webapp._notification(_job(status="done", kind="pack")) is None
    done = _job(status="done")
    done.result = {"report": {}}
    monkeypatch.delenv("DUBEVAL_NOTIFY", raising=False)
    webapp._notify_app(done)
    assert capsys.readouterr().out == ""                 # only the desktop app asks for the line
    monkeypatch.setenv("DUBEVAL_NOTIFY", "1")
    webapp._notify_app(done)
    line = capsys.readouterr().out
    assert line.startswith(webapp.NOTIFY_LINE) and json.loads(line[len(webapp.NOTIFY_LINE):])["open"]
