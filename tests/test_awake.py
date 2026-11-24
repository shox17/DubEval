"""Keeping the computer awake during an evaluation (dubeval/awake.py)."""
import sys
import threading

from dubeval import awake, jobs


def test_on_a_mac_caffeinate_holds_off_idle_sleep_until_the_block_ends(monkeypatch):
    started, stopped = [], []

    class Proc:
        def terminate(self):
            stopped.append(True)

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake.os.path, "exists", lambda p: p == awake.CAFFEINATE)
    monkeypatch.setattr(awake.subprocess, "Popen", lambda args, **kw: started.append(args) or Proc())
    with awake.keep_awake():
        assert started and started[0][:2] == [awake.CAFFEINATE, "-i"]     # idle sleep only, not the screen
        assert started[0][2:] == ["-w", str(awake.os.getpid())]          # it ends with DubEval even after a crash
        assert not stopped
    assert stopped == [True]


def test_on_windows_the_thread_asks_to_stay_awake_and_then_lets_go(monkeypatch):
    calls = []

    class Kernel32:
        def SetThreadExecutionState(self, flags):
            calls.append(flags)
            return 1

    class Windll:
        kernel32 = Kernel32()

    import ctypes
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", Windll(), raising=False)
    with awake.keep_awake():
        assert calls == [awake.ES_CONTINUOUS | awake.ES_SYSTEM_REQUIRED]
    assert calls[-1] == awake.ES_CONTINUOUS


def test_a_problem_keeping_awake_never_stops_the_evaluation(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake.os.path, "exists", lambda p: True)

    def broken(*a, **kw):
        raise OSError("no caffeinate here")
    monkeypatch.setattr(awake.subprocess, "Popen", broken)
    ran = []
    with awake.keep_awake():
        ran.append(True)
    assert ran == [True]


def test_every_job_runs_while_the_computer_is_kept_awake(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "JOBS_DIR", str(tmp_path))
    held = []

    class Hold:
        def __enter__(self):
            held.append("on")

        def __exit__(self, *exc):
            held.append("off")

    monkeypatch.setattr(jobs, "keep_awake", lambda: Hold())

    def runner(report, cancel):
        held.append("running")
        return {"ok": True}

    job = jobs.start_job(runner, {"kind": "test"}, ["prepare"])
    for _ in range(200):
        if job.status != "running":
            break
        threading.Event().wait(0.01)
    assert job.status == "done" and held == ["on", "running", "off"]
