"""Usage stats: off until the person says yes, and only the listed values can leave the computer."""
import json

import pytest
import requests

from dubeval import jobs, usage_stats
from tests.test_webapp import client, finished, media  # noqa: F401  (fixtures)


class Fake:
    """Stands in for dubeval.com."""

    def __init__(self, status=201, error=None):
        self.status, self.error, self.sent = status, error, []

    def __call__(self, data):
        if self.error:
            raise self.error
        self.sent.append(json.loads(json.dumps(data)))
        return type("Response", (), {"status_code": self.status})()


@pytest.fixture
def site(monkeypatch):
    fake = Fake()
    monkeypatch.setattr(usage_stats, "_post", fake)
    return fake


def names(batch):
    return [e["name"] for e in batch["events"]]


def test_nothing_is_kept_or_sent_before_the_person_answers(site):
    assert usage_stats.status()["ask"] is True and usage_stats.status()["on"] is False
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.app_opened()
    usage_stats.flush()
    assert site.sent == [] and not usage_stats._queue


def test_saying_no_is_remembered_and_sends_nothing(site):
    assert usage_stats.choose(False)["ask"] is False
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.flush()
    assert site.sent == [] and usage_stats.status()["on"] is False


def test_saying_yes_sends_this_launch_once(site):
    assert usage_stats.choose(True)["on"] is True
    usage_stats.app_opened()
    usage_stats.flush()
    assert len(site.sent) == 1 and names(site.sent[0]) == ["app_opened"]
    assert set(site.sent[0]) == {"schema", "week_id", "app_version", "os", "events"}
    assert usage_stats.status()["recent"] == [{"name": "app_opened"}]


def test_only_listed_values_can_leave_the_computer(site):
    usage_stats.choose(True)
    usage_stats.record("evaluation_failed", mode="typed by someone", step=r"C:\Users\Someone\video.mp4",
                       error_type=r"Could not read C:\private\video.mp4", verdict="SECRET", source_lang="My private language",
                       target_lang="es-MX", dub_type="something typed", feature="SECRET", title="SECRET TITLE",
                       link="https://secret.example", dubs="SECRET", seconds="SECRET")
    usage_stats.flush()
    events = site.sent[0]["events"]
    assert {"name": "evaluation_failed", "target_lang": "es-MX"} in events
    text = json.dumps(site.sent)
    for secret in ("SECRET", "private", "secret.example", "Someone", "video.mp4", "typed"):
        assert secret not in text


def test_an_unknown_event_is_not_sent(site):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("my_own_event", mode="single")
    usage_stats.flush()
    assert site.sent == []


def test_durations_are_rounded(site):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_finished", seconds=123.4)
    usage_stats.flush()
    assert site.sent[0]["events"][0]["seconds"] == 120


def test_the_weekly_number_changes_with_the_week(site, monkeypatch):
    usage_stats.choose(True)
    first = usage_stats._week_id()
    assert usage_stats._week_id() == first and len(first) == 16
    monkeypatch.setattr(usage_stats.time, "strftime", lambda fmt: "2099-W01")
    assert usage_stats._week_id() != first


def test_saying_no_later_forgets_what_waits_and_the_weekly_number(site):
    usage_stats.choose(True)
    usage_stats._week_id()
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.choose(False)
    usage_stats.flush()
    assert site.sent == [] and "week_id" not in usage_stats._read()


def test_no_connection_keeps_events_for_later_and_a_refusal_drops_them(monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_started", mode="single")
    monkeypatch.setattr(usage_stats, "_post", Fake(error=requests.ConnectionError()))
    usage_stats.flush()
    assert len(usage_stats._queue) == 1
    monkeypatch.setattr(usage_stats, "_post", Fake(status=503))
    usage_stats.flush()
    assert len(usage_stats._queue) == 1
    monkeypatch.setattr(usage_stats, "_post", Fake(status=400))
    usage_stats.flush()
    assert not usage_stats._queue


def test_a_problem_never_reaches_the_app(monkeypatch, tmp_path):
    usage_stats.choose(True)
    monkeypatch.setattr(usage_stats, "_post", Fake(error=RuntimeError("boom")))
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.flush()                                                  # raises nothing
    monkeypatch.setattr(usage_stats, "_clean", lambda *a: 1 / 0)
    usage_stats.record("evaluation_started")                             # raises nothing
    monkeypatch.setattr(usage_stats, "STATE_FILE", tmp_path)             # a folder: can't be read as a file
    assert usage_stats.status()["ask"] is True


def test_the_off_switch_removes_the_question_and_sends_nothing(site, monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    monkeypatch.setenv("DUBEVAL_USAGE_STATS", "0")
    assert usage_stats.status() == {"available": False, "on": False, "ask": False, "recent": [], "about": None}
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.flush()
    assert site.sent == []


def test_the_page_asks_until_answered_and_the_answer_applies_at_once(client, site):
    assert client.get("/api/info").json()["ask_usage_stats"] is True
    assert site.sent == [] and not usage_stats._queue
    assert client.put("/api/settings/usage-stats", json={"on": True}).json()["on"] is True
    assert client.get("/api/info").json()["ask_usage_stats"] is False
    assert client.get("/api/settings").json()["usage_stats"]["on"] is True
    usage_stats.flush()
    assert names(site.sent[0]) == ["app_opened"]
    assert client.put("/api/settings/usage-stats", json={"on": False}).json()["on"] is False
    assert client.put("/api/settings/usage-stats", json={"on": "maybe"}).status_code == 422


def test_an_evaluation_reports_how_it_went_only_after_yes(client, site, monkeypatch):
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    assert not usage_stats._queue                                        # no answer yet: nothing noted

    client.put("/api/settings/usage-stats", json={"on": True})
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    client.get(f"/api/jobs/{job_id}/export?kinds=json")
    for _ in range(100):
        if any(e["name"] == "feature_used" for e in usage_stats._queue) and any(
                e["name"] == "evaluation_finished" for e in usage_stats._queue):
            break
        jobs.time.sleep(0.02)
    usage_stats.flush()
    events = {e["name"]: e for e in site.sent[0]["events"]}
    assert events["evaluation_started"] == {"name": "evaluation_started", "mode": "single", "dubs": 1}
    assert events["evaluation_finished"]["mode"] == "single"
    assert events["feature_used"]["feature"] == "export"
    text = json.dumps(site.sent)
    assert "o.mp4" not in text and "d.mp4" not in text


def test_the_page_reports_steps_by_name_only_and_only_after_yes(client, site):
    for step in usage_stats.STEPS:
        assert client.post("/api/settings/usage-stats/step", json={"step": step}).status_code == 200
    assert not usage_stats._queue                                        # no answer yet: nothing noted

    client.put("/api/settings/usage-stats", json={"on": True})
    usage_stats._queue.clear()
    for step in usage_stats.STEPS:
        client.post("/api/settings/usage-stats/step", json={"step": step, "mode": "compare"})
    usage_stats.flush()
    assert site.sent[0]["events"] == [{"name": step, "mode": "compare"} for step in usage_stats.STEPS]


@pytest.mark.parametrize("body", [{"step": "my_own_step"}, {"step": r"C:\private\video.mp4"}, {"step": "dub_added", "mode": "typed"},
                                  {}])
def test_the_page_can_report_nothing_else(client, site, body):
    client.put("/api/settings/usage-stats", json={"on": True})
    usage_stats._queue.clear()
    assert client.post("/api/settings/usage-stats/step", json=body).status_code == 422
    assert not usage_stats._queue


def test_extra_fields_from_the_page_are_not_sent(client, site):
    client.put("/api/settings/usage-stats", json={"on": True})
    usage_stats._queue.clear()
    client.post("/api/settings/usage-stats/step", json={"step": "dub_added", "file": "SECRET.mp4", "title": "SECRET"})
    usage_stats.flush()
    assert site.sent[0]["events"] == [{"name": "dub_added", "mode": "single"}]


def test_a_failed_job_sends_its_step_and_error_kind_but_never_the_message(site):
    usage_stats.choose(True)
    usage_stats._queue.clear()

    def fails(report, cancel):
        report(jobs.Progress("evaluate", "Measuring"))
        raise MemoryError(r"C:\Users\Someone\secret video.mp4 was too big")
    from dubeval import webapp
    assert jobs.on_finish is webapp._report_job_to_stats
    job = jobs.start_job(fails, {"kind": "files", "dubs": ["d.mp4"]}, ["prepare", "evaluate"])
    for _ in range(200):
        if job.status != "running" and usage_stats._queue:
            break
        jobs.time.sleep(0.01)
    usage_stats.flush()
    assert site.sent[0]["events"] == [{"name": "evaluation_failed", "mode": "single", "step": "evaluate",
                                       "error_type": "MemoryError", "dubs": 1}]
    assert "secret" not in json.dumps(site.sent)


def test_a_stats_problem_never_changes_how_a_job_ended(monkeypatch):
    def broken(job):
        raise RuntimeError("boom")
    monkeypatch.setattr(jobs, "on_finish", broken)
    job = jobs.start_job(lambda report, cancel: {"fine": True}, {"kind": "files"}, ["evaluate"])
    for _ in range(200):
        if job.status != "running":
            break
        jobs.time.sleep(0.01)
    assert job.status == "done" and job.result == {"fine": True}


def test_a_no_that_cannot_be_saved_still_stops_everything(site, monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_started", mode="single")

    def locked(*args):
        raise PermissionError("held by an antivirus")
    monkeypatch.setattr(usage_stats.os, "replace", locked)
    monkeypatch.setattr(usage_stats.time, "sleep", lambda s: None)
    with pytest.raises(usage_stats.NotSaved):
        usage_stats.choose(False)
    assert usage_stats.enabled() is False and not usage_stats._queue
    usage_stats.record("evaluation_started", mode="single")
    usage_stats.flush()
    assert site.sent == [] and not usage_stats._queue


def test_a_yes_that_cannot_be_saved_stays_off(site, monkeypatch):
    def locked(*args):
        raise PermissionError("held by an antivirus")
    monkeypatch.setattr(usage_stats.os, "replace", locked)
    monkeypatch.setattr(usage_stats.time, "sleep", lambda s: None)
    with pytest.raises(usage_stats.NotSaved):
        usage_stats.choose(True)
    assert usage_stats.enabled() is False and not usage_stats._queue


def test_the_page_hears_when_a_choice_cannot_be_saved(client, site, monkeypatch):
    def locked(*args):
        raise PermissionError("held by an antivirus")
    monkeypatch.setattr(usage_stats.os, "replace", locked)
    monkeypatch.setattr(usage_stats.time, "sleep", lambda s: None)
    resp = client.put("/api/settings/usage-stats", json={"on": False})
    assert resp.status_code == 503 and "stay off" in resp.json()["detail"]


def test_a_brief_file_lock_is_waited_out(site, monkeypatch):
    real, calls = usage_stats.os.replace, []

    def once_locked(a, b):
        calls.append(a)
        if len(calls) == 1:
            raise PermissionError("held for a moment")
        return real(a, b)
    monkeypatch.setattr(usage_stats.os, "replace", once_locked)
    monkeypatch.setattr(usage_stats.time, "sleep", lambda s: None)
    assert usage_stats.choose(False)["on"] is False and usage_stats._read()["on"] is False
    assert list(usage_stats.Path(usage_stats.STATE_FILE).parent.glob("usage_stats.json.*")) == []   # no stray files


def test_events_being_sent_cannot_come_back_after_a_no(monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_started", mode="single")

    def says_no_while_sending(data):
        usage_stats.choose(False)
        raise requests.ConnectionError()
    monkeypatch.setattr(usage_stats, "_post", says_no_while_sending)
    usage_stats.flush()
    assert not usage_stats._queue
    site = Fake()
    monkeypatch.setattr(usage_stats, "_post", site)
    monkeypatch.setattr(usage_stats, "_opened", True)
    usage_stats.choose(True)
    usage_stats.flush()
    assert site.sent == []


def test_the_weekly_number_never_rewrites_a_no():
    usage_stats.choose(False)
    assert usage_stats._week_id() is None
    assert usage_stats._read() == {"on": False}


def test_a_full_queue_keeps_the_newest(monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    monkeypatch.setattr(usage_stats, "MAX_QUEUE", 5)
    monkeypatch.setattr(usage_stats, "_queue", usage_stats.deque(maxlen=5))
    usage_stats.record("evaluation_started", dubs=1)
    usage_stats.record("evaluation_started", dubs=2)
    monkeypatch.setattr(usage_stats, "_post", Fake(error=requests.ConnectionError()))
    first = [usage_stats._queue.popleft(), usage_stats._queue.popleft()]
    for n in range(3, 8):
        usage_stats.record("evaluation_started", dubs=n)
    usage_stats._put_back(first, usage_stats._generation)
    assert [e["dubs"] for e in usage_stats._queue] == [3, 4, 5, 6, 7]


def test_a_failing_site_is_not_asked_again_and_again(monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    for _ in range(usage_stats.MAX_BATCH * 2 + 5):
        usage_stats.record("evaluation_started")
    asked = []
    monkeypatch.setattr(usage_stats, "_schedule", lambda: asked.append(1))
    monkeypatch.setattr(usage_stats, "_post", Fake(status=429))
    usage_stats.flush()
    assert asked == []                                                   # busy: waits for the next event
    monkeypatch.setattr(usage_stats, "_post", Fake())
    usage_stats.flush()
    assert asked == [1]                                                  # delivered, and a full batch still waits


def test_no_answer_after_sending_is_not_sent_twice(monkeypatch):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_started", mode="single")
    monkeypatch.setattr(usage_stats, "_post", Fake(error=requests.exceptions.ReadTimeout()))
    usage_stats.flush()
    assert not usage_stats._queue


@pytest.mark.parametrize("bad", ["en\n", "ko\n", "en\r\n"])
def test_a_value_with_a_line_break_is_dropped_so_the_site_never_refuses_the_batch(site, bad):
    usage_stats.choose(True)
    usage_stats._queue.clear()
    usage_stats.record("evaluation_finished", source_lang=bad, target_lang=bad, step="evaluate\n", error_type="ValueError\n")
    usage_stats.flush()
    assert site.sent[0]["events"] == [{"name": "evaluation_finished"}]


def test_settings_show_what_travels_with_the_events(site):
    usage_stats.choose(True)
    usage_stats.flush()
    about = usage_stats.status()["about"]
    assert set(about) == {"week_id", "app_version", "os"} and about["week_id"] == site.sent[0]["week_id"]


def test_an_empty_rename_is_not_counted(client, site):
    client.put("/api/settings/usage-stats", json={"on": True})
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    usage_stats._queue.clear()
    assert client.put(f"/api/jobs/{job_id}/title", json={"title": "   "}).status_code in (400, 422)
    assert not [e for e in usage_stats._queue if e.get("feature") == "rename"]


def test_the_help_page_tells_the_truth_about_usage_stats():
    from dubeval.web_text import WEB_TEXT
    for lang, text in WEB_TEXT["w.help.where_more"].items():
        assert "dubeval.com" in text, lang
    assert "Only" not in WEB_TEXT["w.help.where_text"]["en"]

