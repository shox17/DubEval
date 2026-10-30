"""Background jobs: an evaluation, comparison or batch runs in a thread so the UI can show live progress, survive page
reloads (the job id is kept in the URL) and let the user stop it.

Every job also keeps its state in data/jobs/<id>.json (and its result in <id>.result.json once done), so a job is
still found after the app restarts: a finished one shows its result, one that was running when the process stopped
is reported as interrupted.
"""
import os
import re
import json
import time
import uuid
import logging
import threading
from pathlib import Path

from dubeval.paths import DATA_DIR
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)

JOBS_DIR = Path(os.getenv("DUBEVAL_JOBS") or DATA_DIR / "jobs")
MAX_KEPT_JOBS = 50
SAVE_EVERY_SEC = 2.0                 # progress snapshots are written at most this often (stage changes always)
JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")
INTERRUPTED = "The app restarted while this job was running, so it stopped. Start it again."

# Ordered stages shown in the UI checklist.
STAGES = [
    ("prepare", "Check both files"),
    ("fetch", "Read the Perso share link"),
    ("download", "Download both videos"),
    ("evaluate", "Measure quality"),
    ("dub_a", "Evaluate dub A"),
    ("dub_b", "Evaluate dub B"),
    ("dub_c", "Evaluate dub C"),
    ("dub_d", "Evaluate dub D"),
    ("dub_e", "Evaluate dub E"),
    ("dub_f", "Evaluate dub F"),
    ("dub_g", "Evaluate dub G"),
    ("dub_h", "Evaluate dub H"),
    ("compare", "Compare and recommend"),
    ("batch", "Evaluate every link"),
    ("pack", "Download"),
]
STAGE_KEYS = [k for k, _ in STAGES]


class Cancelled(RuntimeError):
    """The user stopped a job."""


@dataclass
class Progress:
    """One progress report from the pipeline."""
    stage: str                       # one of STAGE_KEYS
    message: str                     # what is happening, in plain words
    stage_fraction: float = 0.0      # 0..1 within the stage


@dataclass
class Job:
    """One background evaluation: its status, current stage, progress and, when finished, result or error."""
    id: str
    params: dict
    stages: list[str]                               # the stages this job goes through
    status: str = "running"                         # running | done | failed | cancelled | interrupted
    stage: str = ""
    message: str = "Starting..."
    stage_fraction: float = 0.0
    started_at: float = field(default_factory=time.time)
    stage_started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _saved_at: float = 0.0

    def report(self, p: Progress) -> None:
        """Records a progress update from the pipeline (called from the worker thread)."""
        with self._lock:
            new_stage = p.stage != self.stage
            if new_stage:
                self.stage_started_at = time.time()
            self.stage, self.message = p.stage, p.message
            self.stage_fraction = max(0.0, min(1.0, p.stage_fraction))
        if new_stage or time.time() - self._saved_at >= SAVE_EVERY_SEC:
            self.save()

    def snapshot(self, status: Optional[str] = None) -> dict:
        """The job's state as JSON-friendly data (without the result)."""
        return {"id": self.id, "params": self.params, "stages": self.stages, "status": status or self.status,
                "stage": self.stage, "message": self.message, "stage_fraction": self.stage_fraction,
                "started_at": self.started_at, "stage_started_at": self.stage_started_at,
                "finished_at": self.finished_at, "error": self.error}

    def save(self, status: Optional[str] = None) -> None:
        """Writes the state file (and the result once done); a failure is logged, never raised.

        status saves a final state before it is set in memory, so a restart never finds a finished job on disk
        still marked running.
        """
        self._saved_at = time.time()
        try:
            folder = Path(JOBS_DIR)
            folder.mkdir(parents=True, exist_ok=True)
            if (status or self.status) == "done" and self.result is not None:
                _write(folder / f"{self.id}.result.json", self.result)
            _write(folder / f"{self.id}.json", self.snapshot(status))
        except (OSError, TypeError, ValueError) as e:
            log.warning("Could not save job %s: %s", self.id, e)

    @property
    def overall_fraction(self) -> float:
        """Progress across all stages, weighted by their typical share of the run time."""
        weights = {"prepare": 1, "pack": 1, "fetch": 0.2, "download": 1, "evaluate": 6, "compare": 0.2, "batch": 1,
                   **{f"dub_{c}": 7 for c in "abcdefgh"}}
        total = sum(weights[s] for s in self.stages)
        if self.status == "done":
            return 1.0
        done = 0.0
        for s in self.stages:
            if s == self.stage:
                done += weights[s] * self.stage_fraction
                break
            done += weights[s]
        return min(0.99, done / total) if total else 0.0

    @property
    def elapsed_sec(self) -> float:
        """Seconds since the job started, frozen once it finishes."""
        return (self.finished_at or time.time()) - self.started_at

    def stage_state(self, stage: str) -> str:
        """pending | active | done | failed for the UI checklist."""
        if self.status == "done":
            return "done"
        order = self.stages
        if stage not in order or self.stage not in order:
            return "pending"
        i, cur = order.index(stage), order.index(self.stage)
        if i < cur:
            return "done"
        if i == cur:
            return "failed" if self.status in ("failed", "cancelled", "interrupted") else "active"
        return "pending"


_jobs: dict[str, Job] = {}
_registry_lock = threading.Lock()


def _write(path: Path, data) -> None:
    """Writes JSON atomically."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _prune(keep: Optional[int] = None) -> None:
    """Deletes the files of all but the newest `keep` jobs (default MAX_KEPT_JOBS)."""
    keep = MAX_KEPT_JOBS if keep is None else keep
    folder = Path(JOBS_DIR)
    if not folder.is_dir():
        return
    states = sorted(folder.glob("*[0-9a-f].json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old in states[keep:]:
        for f in (old, old.with_name(old.stem + ".result.json")):
            f.unlink(missing_ok=True)


def _load(job_id: str) -> Optional[Job]:
    """A job from its files, or None. A job saved as running belongs to a process that is gone: interrupted."""
    folder = Path(JOBS_DIR)
    try:
        state = json.loads((folder / f"{job_id}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    job = Job(id=job_id, params=state.get("params") or {}, stages=state.get("stages") or ["evaluate"])
    for k in ("status", "stage", "message", "stage_fraction", "started_at", "stage_started_at", "finished_at", "error"):
        if state.get(k) is not None:
            setattr(job, k, state[k])
    if job.status == "running":
        job.status, job.error = "interrupted", INTERRUPTED
        job.finished_at = job.finished_at or state.get("stage_started_at") or job.started_at
        job.save()
    elif job.status == "done":
        try:
            job.result = json.loads((folder / f"{job_id}.result.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            job.status, job.error = "interrupted", INTERRUPTED
    return job


def start_job(runner: Callable[[Callable[[Progress], None], threading.Event], dict],
              params: dict, stages: list[str]) -> Job:
    """Runs runner(report, cancel_event) in a daemon thread and returns the Job immediately."""
    job = Job(id=uuid.uuid4().hex[:12], params=params, stages=stages, stage=stages[0])
    with _registry_lock:
        _jobs[job.id] = job
    job.save()
    _prune()

    def target():
        """Thread body: runs the pipeline and stores the result, error or cancellation on the job."""
        try:
            job.result = runner(job.report, job.cancel_event)
            status, job.message = "done", "Finished"
        except Exception as e:  # reported to the UI; the traceback goes to the log
            if isinstance(e, Cancelled):
                status, job.error = "cancelled", "You stopped this job."
            else:
                log.exception("Job %s failed", job.id)
                status, job.error = "failed", str(e)
        job.finished_at = time.time()
        job.save(status)                              # on disk first, then visible: see Job.save
        job.status = status

    threading.Thread(target=target, name=f"job-{job.id}", daemon=True).start()
    return job


def busy() -> bool:
    """Whether a job (an evaluation or a download) is running in this process."""
    with _registry_lock:
        return any(j.status == "running" for j in _jobs.values())


def restore_job(params: dict, stages: list[str], result: dict) -> Job:
    """A finished job made again from a past run's saved files (History opens it like any other result)."""
    job = Job(id=uuid.uuid4().hex[:12], params=params, stages=stages, stage=stages[-1], status="done",
              message="Finished", result=result)
    job.finished_at = job.started_at
    with _registry_lock:
        _jobs[job.id] = job
    job.save()
    _prune()
    return job


def find_done_job(folder: str) -> Optional[Job]:
    """The kept, finished job whose results are in folder (a run folder), if any."""
    target = _same_path(folder)
    for state_file in sorted(Path(JOBS_DIR).glob("*[0-9a-f].json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            params = json.loads(state_file.read_text(encoding="utf-8")).get("params") or {}
        except (OSError, json.JSONDecodeError):
            continue
        if params.get("folder") and _same_path(params["folder"]) == target:
            job = get_job(state_file.stem)
            if job is not None and job.status == "done" and isinstance(job.result, dict):
                return job
    return None


def forget_folder(folder: str) -> None:
    """Drops every kept job whose results are in folder (a run folder that was deleted or changed on disk), from
    memory and disk; opening that run again rebuilds it from its files."""
    target = _same_path(folder)
    for state_file in Path(JOBS_DIR).glob("*[0-9a-f].json"):
        try:
            params = json.loads(state_file.read_text(encoding="utf-8")).get("params") or {}
        except (OSError, json.JSONDecodeError):
            continue
        if params.get("folder") and _same_path(params["folder"]) == target:
            with _registry_lock:
                _jobs.pop(state_file.stem, None)
            for f in (state_file, state_file.with_name(state_file.stem + ".result.json")):
                f.unlink(missing_ok=True)


def _same_path(path: str) -> str:
    """A path in one spelling, to compare folders (case-insensitive on Windows)."""
    return os.path.normcase(str(Path(path).resolve()))


def get_job(job_id: Optional[str]) -> Optional[Job]:
    """A job by id: from memory, else from its saved files (after an app restart); None if unknown or malformed."""
    if not job_id or not JOB_ID_RE.match(str(job_id)):
        return None
    with _registry_lock:
        job = _jobs.get(job_id)
        if job is None:
            job = _load(job_id)
            if job is not None:
                _jobs[job_id] = job
        return job
