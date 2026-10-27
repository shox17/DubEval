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
