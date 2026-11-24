"""Tests for background jobs: results, errors, cancellation, progress weighting and the stage checklist."""
import time

from dubeval.jobs import Cancelled, Progress, get_job, start_job


def wait(job, timeout=5):
    """Blocks until the job leaves the running state or the timeout passes."""
    end = time.time() + timeout
    while job.status == "running" and time.time() < end:
        time.sleep(0.01)
    return job


def test_job_runs_in_background_and_stores_result():
    def runner(report, cancel):
        report(Progress("fetch", "Reading the shared Perso project...", 1.0))
        report(Progress("download", "Downloading the dubbed video...", 0.5))
        return {"ok": True}
    job = wait(start_job(runner, {}, ["fetch", "download", "evaluate"]))
    assert job.status == "done" and job.result == {"ok": True}
    assert get_job(job.id) is job
    assert job.overall_fraction == 1.0


def test_overall_progress_and_stage_states():
    def runner(report, cancel):
        report(Progress("evaluate", "Transcribing the dubbed speech...", 0.5))
        cancel.wait(5)
        raise Cancelled()
    job = start_job(runner, {}, ["fetch", "download", "evaluate"])
    time.sleep(0.05)
    # weights: fetch 0.2, download 1, evaluate 6 (half done) -> (0.2 + 1 + 3) / 7.2
    assert abs(job.overall_fraction - 4.2 / 7.2) < 1e-6
    assert [job.stage_state(s) for s in job.stages] == ["done", "done", "active"]
    job.cancel_event.set()
    wait(job)
    assert job.status == "cancelled" and job.stage_state("evaluate") == "failed"


def test_failure_is_captured():
    def runner(report, cancel):
        raise ValueError("bad input")
    job = wait(start_job(runner, {}, ["evaluate"]))
    assert job.status == "failed" and job.error == "bad input"


# ---------------- surviving an app restart ----------------
from dubeval import jobs


def forget_memory():
    """Simulates an app restart: the in-memory registry is empty, the job files remain."""
    jobs._jobs.clear()


def test_a_finished_job_and_its_result_survive_a_restart():
    job = wait(start_job(lambda report, cancel: {"answer": "한국어", "n": 42}, {"share_url": "x"}, ["evaluate"]))
    forget_memory()
    again = get_job(job.id)
    assert again is not job and again.status == "done" and again.result == {"answer": "한국어", "n": 42}
    assert again.params == {"share_url": "x"} and again.overall_fraction == 1.0


def test_a_job_running_when_the_app_stopped_is_reported_as_interrupted():
    release = __import__("threading").Event()

    def runner(report, cancel):
        report(Progress("evaluate", "Transcribing the dubbed speech...", 0.4))
        release.wait(5)
        return {}
    job = start_job(runner, {}, ["fetch", "evaluate"])
    time.sleep(0.05)
    forget_memory()                                   # the process "died" while the job ran
    lost = get_job(job.id)
    release.set()
    assert lost.status == "interrupted" and "restarted" in lost.error
    assert lost.stage == "evaluate" and lost.stage_state("evaluate") == "failed"


def test_a_failure_on_the_input_says_running_again_cant_help_even_after_a_restart():
    from dubeval.inputs import InputError

    def unreadable(report, cancel):
        raise InputError("The original video can't be read.")
    job = wait(start_job(unreadable, {}, ["prepare"]))
    assert job.status == "failed" and job.retry_helps is False
    forget_memory()
    assert get_job(job.id).retry_helps is False
    other = wait(start_job(lambda report, cancel: 1 / 0, {}, ["prepare"]))
    assert other.status == "failed" and other.retry_helps is True


def test_unknown_or_malformed_job_ids_are_rejected_without_touching_disk():
    assert get_job("0123456789ab") is None
    assert get_job("../../etc/passwd") is None and get_job("A" * 12) is None


def test_only_the_newest_jobs_are_kept(monkeypatch):
    monkeypatch.setattr(jobs, "MAX_KEPT_JOBS", 3)
    made = []
    for i in range(5):
        made.append(wait(start_job(lambda r, c, i=i: {"i": i}, {}, ["evaluate"])))
        time.sleep(0.01)                              # distinct modification times
    kept = {f.stem for f in jobs.JOBS_DIR.glob("*[0-9a-f].json")}
    assert len(kept) <= 3 and made[-1].id in kept and made[0].id not in kept


# ---------------- evaluations take turns ----------------
import threading


def _blocked(gate):
    """A runner that waits until gate is set."""
    def runner(report, cancel):
        report(Progress("evaluate", "Transcribing the dubbed speech...", 0.2))
        gate.wait(5)
        return {"done": True}
    return runner


def test_an_evaluation_started_while_another_runs_waits_then_starts_by_itself():
    gate = threading.Event()
    first = start_job(_blocked(gate), {}, ["evaluate"], queued=True)
    time.sleep(0.05)
    second = start_job(lambda r, c: {"second": True}, {}, ["prepare", "evaluate"], queued=True)
    third = start_job(lambda r, c: {"third": True}, {}, ["evaluate"], queued=True)
    assert first.status == "running" and second.status == third.status == "queued"
    assert jobs.queue_position(second) == 1 and jobs.queue_position(third) == 2 and jobs.waiting_count() == 2
    assert second.overall_fraction == 0.0 and second.elapsed_sec == 0.0
    assert [second.stage_state(s) for s in second.stages] == ["pending", "pending"]
    assert jobs.running_evaluation() is first
    queued_at = second.started_at
    time.sleep(0.05)
    gate.set()
    for job in (first, second, third):
        end = time.time() + 5
        while job.status in ("running", "queued") and time.time() < end:
            time.sleep(0.01)
    assert first.result == {"done": True} and second.result == {"second": True} and third.result == {"third": True}
    assert second.started_at > queued_at                 # its time in line isn't counted as the run's
    assert second.finished_at <= third.started_at        # one at a time, in order


def test_a_waiting_evaluation_leaves_the_line_at_once_when_stopped():
    gate = threading.Event()
    first = start_job(_blocked(gate), {}, ["evaluate"], queued=True)
    second = start_job(lambda r, c: {}, {}, ["evaluate"], queued=True)
    third = start_job(lambda r, c: {}, {}, ["evaluate"], queued=True)
    jobs.cancel(second)
    assert second.status == "cancelled" and second.error == jobs.REMOVED and jobs.queue_position(third) == 1
    assert second.params["removed"]                      # never started: the page offers the queue again, not Continue
    assert first.status == "running"
    gate.set()
    wait(first)
    end = time.time() + 5
    while third.status in ("running", "queued") and time.time() < end:
        time.sleep(0.01)
    assert third.status == "done" and second.status == "cancelled"


def test_downloads_dont_wait_for_an_evaluation():
    gate = threading.Event()
    start_job(_blocked(gate), {}, ["evaluate"], queued=True)
    download = wait(start_job(lambda r, c: True, {"kind": "pack"}, ["pack"]))
    gate.set()
    assert download.status == "done"


def test_an_evaluation_waiting_when_the_app_stopped_is_interrupted_and_can_start_again():
    gate = threading.Event()
    start_job(_blocked(gate), {}, ["evaluate"], queued=True)
    waiting = start_job(lambda r, c: {}, {}, ["evaluate"], queued=True)
    forget_memory()
    jobs._waiting.clear()
    lost = get_job(waiting.id)
    gate.set()
    assert lost.status == "interrupted" and lost.error == jobs.INTERRUPTED_WAITING and lost.retry_helps


def test_every_progress_report_reaches_the_watcher(monkeypatch):
    seen = []
    monkeypatch.setattr(jobs, "on_progress", lambda job: seen.append(round(job.overall_fraction, 2)))

    def runner(report, cancel):
        report(Progress("evaluate", "Transcribing the dubbed speech...", 0.5))
        return {}
    wait(start_job(runner, {}, ["evaluate"]))
    assert seen == [0.5]
