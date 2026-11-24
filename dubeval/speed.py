"""How long an evaluation will take on this computer, learned from the ones it finished.

Each finished evaluation leaves its seconds per minute of video per dub (data/speed.json, the last KEEP of them). A
running evaluation's estimate is the middle of those times its video's length and number of dubs, minus the time it has
run. Before this computer has finished one, or once a run takes longer than that, there is no estimate: a wrong
number is worse than none. Speeds differ a lot between computers (a graphics card, the large speech model, the local
translation checker), which is why it learns here instead of using a fixed rate.
"""
import json
import logging
import statistics
from pathlib import Path
from typing import Optional

from dubeval.paths import DATA_DIR

log = logging.getLogger(__name__)

SPEED_FILE = Path(DATA_DIR) / "speed.json"
KEEP = 10                       # the last this many evaluations decide; older ones are forgotten
MIN_MEDIA_MIN = 0.5             # a very short clip counts as this long: loading the models takes time whatever its length
KINDS = ("files", "comparison")


def _rates() -> list[float]:
    """The kept speeds, seconds per minute of video per dub (an unreadable file counts as none)."""
    try:
        rates = json.loads(SPEED_FILE.read_text(encoding="utf-8")).get("rates") or []
        return [float(r) for r in rates if isinstance(r, (int, float)) and r > 0]
    except (OSError, ValueError, AttributeError):
        return []


def _work(job) -> Optional[float]:
    """Minutes of video times dubs: what an evaluation's time is in proportion to; None until the length is known."""
    if not job.media_sec or job.params.get("kind") not in KINDS:
        return None
    dubs = max(1, len(job.params.get("dubs") or []))
    return max(MIN_MEDIA_MIN, job.media_sec / 60) * dubs


def record(job) -> None:
    """Keeps a finished evaluation's speed: only a single evaluation that measured everything itself. A run that took
    measurements from an earlier one (the same files again, Continue) finishes in seconds, and a comparison reuses the
    original's measurements for every dub after the first; either would make the estimate far too short."""
    work = _work(job)
    run = (job.result.get("pipeline") or {}) if isinstance(job.result, dict) else {}
    if (job.status != "done" or work is None or job.params.get("kind") != "files" or job.params.get("continued")
            or job.params.get("restored") or run.get("reused_measurements") is not False):
        return
    try:
        rates = (_rates() + [round(job.elapsed_sec / work, 2)])[-KEEP:]
        SPEED_FILE.parent.mkdir(parents=True, exist_ok=True)
        SPEED_FILE.write_text(json.dumps({"rates": rates}), encoding="utf-8")
    except OSError as e:                      # an estimate must never fail an evaluation
        log.info("Couldn't keep this evaluation's speed: %s", e)


def remaining(job) -> Optional[float]:
    """Seconds a running evaluation probably still needs, or None when there's no honest estimate."""
    work = _work(job)
    rates = _rates()
    if job.status != "running" or work is None or not rates:
        return None
    left = statistics.median(rates) * work - job.elapsed_sec
    return round(left) if left > 0 else None
