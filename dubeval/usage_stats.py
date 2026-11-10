"""Usage stats: small counts sent to dubeval.com, only from an app whose owner said yes, off until then.

What may leave this computer is exactly what _clean() and _batch() build, field by field from fixed lists: which step of
the app happened, the mode, the step that failed and the kind of error, the verdict, language codes, the kind of dub, the
feature used, a rounded duration, the app's version and the kind of system. Never a video, audio, a transcript, a title, a
file name, a link, an API key, an error's message or a measured value.

week_id is a random number replaced every week: it counts active apps in a week and can't follow one across weeks. Only
the app sends these, never the command line or the REST API, and nothing here may ever affect an evaluation: every problem
is logged and dropped. DUBEVAL_USAGE_STATS=0 turns the feature off completely, without the question.
"""
import json
import logging
import os
import platform
import re
import secrets
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import requests

from dubeval.paths import DATA_DIR
from dubeval.version import TOOL_VERSION

log = logging.getLogger(__name__)

SCHEMA = 1
STATS_URL = os.getenv("DUBEVAL_USAGE_STATS_URL") or "https://dubeval.com/api/usage"
STATE_FILE = Path(os.getenv("DUBEVAL_USAGE_STATS_FILE") or DATA_DIR / "usage_stats.json")
TIMEOUT = (5, 10)
SEND_AFTER_SEC = 5.0                       # events that happen together travel together
MAX_BATCH = 50
MAX_QUEUE = 200                            # offline: the oldest go first
SAVE_TRIES = 3                             # an antivirus or sync tool can hold the file for a moment
SAVE_FAILED = ("Couldn't save your choice. Usage stats stay off until you close DubEval. Check that DubEval can write to "
               "its folder, then try again.")
MAX_SECONDS = 86400
ROUND_SECONDS_TO = 10

STEPS = ("new_evaluation_opened", "dub_added", "original_added", "result_opened")   # what the page reports: only names
EVENTS = ("app_opened", *STEPS, "evaluation_started", "evaluation_finished", "evaluation_failed", "evaluation_stopped",
          "feature_used")
MODES = ("single", "compare")
FEATURES = ("export", "vote", "history", "model_download", "continue", "rename")
VERDICTS = ("good", "check", "poor")
DUB_KINDS = ("ai_clone", "ai_stock", "human")
_STEP = re.compile(r"^(prepare|fetch|download|evaluate|dub_[a-h]|compare|batch)$")
_ERROR_TYPE = re.compile(r"^[A-Za-z]{1,40}$")      # a class name such as MemoryError, never the error's message
_LANG_CODE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")
_VERSION = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}$")

_lock = threading.Lock()
_state_lock = threading.RLock()            # the saved choice: read, changed and written as one step
_queue: deque = deque(maxlen=MAX_QUEUE)
_recent: deque = deque(maxlen=MAX_BATCH)   # what this launch has sent, for Settings → Privacy
_timer: Optional[threading.Timer] = None
_opened = False
_off_this_launch = False                   # a choice that couldn't be saved: nothing is sent until the app closes
_generation = 0                            # goes up at each "no", so events already being sent can't come back after it


class NotSaved(Exception):
    """The person's choice couldn't be written; usage stats are off for now."""


def _member(value, allowed) -> Optional[str]:
    return value if value in allowed else None


def _match(value, pattern: re.Pattern) -> Optional[str]:
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _number(value, top: int, step: int = 1) -> Optional[int]:
    """A whole number within its range, rounded so a duration can't identify one particular video."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return min(top, int(round(value / step)) * step)


def _clean(name: str, fields: dict) -> Optional[dict]:
    """The event to send, with only the listed values; anything else in fields is dropped, not sent."""
    if name not in EVENTS:
        return None
    event = {"name": name, "mode": _member(fields.get("mode"), MODES), "step": _match(fields.get("step"), _STEP),
             "error_type": _match(fields.get("error_type"), _ERROR_TYPE), "verdict": _member(fields.get("verdict"), VERDICTS),
             "source_lang": _match(fields.get("source_lang"), _LANG_CODE),
             "target_lang": _match(fields.get("target_lang"), _LANG_CODE),
             "dub_type": _member(fields.get("dub_type"), DUB_KINDS), "feature": _member(fields.get("feature"), FEATURES),
             "dubs": _number(fields.get("dubs"), 8), "seconds": _number(fields.get("seconds"), MAX_SECONDS, ROUND_SECONDS_TO)}
    return {k: v for k, v in event.items() if v is not None}


def _system() -> str:
    """The kind of system, nothing finer: a Linux or macOS release string could be unusual enough to stand out."""
    name = platform.system()
    if name == "Windows":
        release = platform.release()
        return f"windows-{release}" if release in ("10", "11") else "windows-other"
    return {"Darwin": "mac", "Linux": "linux"}.get(name, "other")


def _read() -> dict:
    """The saved choice; an unreadable file counts as never answered."""
    try:
        with _state_lock:
            state = json.loads(Path(STATE_FILE).read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(state: dict) -> bool:
    """Saves the choice atomically and says whether it worked; a file problem is logged, not raised."""
    path = Path(STATE_FILE)
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(state))
        for attempt in range(SAVE_TRIES):
            try:
                os.replace(tmp, path)
                return True
            except PermissionError:
                if attempt == SAVE_TRIES - 1:
                    raise
                time.sleep(0.1)
    except OSError as e:
        log.warning("Could not save the usage-stats choice: %s", type(e).__name__)
        if tmp:
            Path(tmp).unlink(missing_ok=True)
    return False


def available() -> bool:
    """False when DUBEVAL_USAGE_STATS=0: no question and nothing sent, for managed machines and containers."""
    return (os.getenv("DUBEVAL_USAGE_STATS") or "").strip() != "0"


def enabled() -> bool:
    """Whether this person said yes."""
    return available() and not _off_this_launch and _read().get("on") is True


def status() -> dict:
    """What the page needs: whether to ask, the current choice, and what this launch has sent."""
    state = _read()
    with _lock:
        recent = list(_recent)
    on = enabled()
    about = {"week_id": state.get("week_id"), "app_version": _version(), "os": _system()} if on else None
    return {"available": available(), "on": on, "ask": available() and "on" not in state, "recent": recent, "about": about}


def _forget_waiting() -> None:
    """Drops what hasn't been sent, and makes sure what is being sent right now can't come back."""
    global _generation
    with _lock:
        _queue.clear()
        _generation += 1


def choose(on: bool) -> dict:
    """Saves the person's answer. Saying no also forgets the weekly number and anything not yet sent. If it can't be
    saved, stats stay off until the app closes and NotSaved says so: a "no" is never lost, a "yes" never assumed."""
    global _off_this_launch
    if not on:
        _forget_waiting()
    with _state_lock:
        state = _read()
        state["on"] = bool(on)
        if not on:
            state.pop("week", None)
            state.pop("week_id", None)
        saved = _write(state)
        _off_this_launch = not saved
    if not saved:
        _forget_waiting()
        raise NotSaved(SAVE_FAILED)
    if on:
        app_opened()
    return status()


def _week_id() -> Optional[str]:
    """This week's random number: a new one each week, so one app's weeks can't be linked. None if the person has said
    no, and then the saved choice isn't touched."""
    with _state_lock:
        state = _read()
        if state.get("on") is not True:
            return None
        week = time.strftime("%G-W%V")
        if state.get("week") != week or not re.fullmatch(r"[0-9a-f]{16}", str(state.get("week_id"))):
            state.update(week=week, week_id=secrets.token_hex(8))
            _write(state)
        return state["week_id"]


def record(name: str, **fields) -> None:
    """Notes one event if this person said yes; does nothing otherwise, and never raises."""
    try:
        if not enabled():
            return
        event = _clean(name, fields)
        if event is None:
            log.warning("Unknown usage event: %s", name)
            return
        with _lock:
            _queue.append(event)
        _schedule()
    except Exception as e:  # stats must never get in the way of the app
        log.warning("Could not note a usage event: %s", type(e).__name__)


def app_opened() -> None:
    """Notes this launch once, whenever the person's yes comes."""
    global _opened
    with _lock:
        if _opened or not enabled():
            return
        _opened = True
    record("app_opened")


def _schedule() -> None:
    """Sends soon, in the background (tests replace this and call flush themselves)."""
    global _timer
    with _lock:
        if _timer is not None:
            return
        _timer = threading.Timer(SEND_AFTER_SEC, flush)
        _timer.daemon = True
        _timer.start()


def _version() -> str:
    """The app's version in the only shape the site accepts."""
    return TOOL_VERSION if _VERSION.fullmatch(TOOL_VERSION) else "0.0.0"


def _batch(events: list[dict]) -> Optional[dict]:
    """Everything that is sent, around the events; None if the person has said no."""
    week_id = _week_id()
    return {"schema": SCHEMA, "week_id": week_id, "app_version": _version(), "os": _system(), "events": events} if week_id else None


def _post(data: dict) -> requests.Response:
    """The one request that leaves the computer here (tests replace it)."""
    return requests.post(STATS_URL, json=data, timeout=TIMEOUT, allow_redirects=False,
                         headers={"User-Agent": f"DubEval/{TOOL_VERSION}"})


def flush() -> None:
    """Sends what's waiting. Unreachable or busy: it stays for the next event. Refused, or no answer after sending (it may
    have arrived, and counting it twice is worse than missing it): it's dropped, never retried."""
    global _timer
    with _lock:
        _timer = None
        generation = _generation
        events = [_queue.popleft() for _ in range(min(MAX_BATCH, len(_queue)))]
    if not events:
        return
    delivered = False
    try:
        data = _batch(events) if enabled() else None
        if data is None:                           # said no while these waited
            return
        resp = _post(data)
        if 200 <= resp.status_code < 300:
            delivered = True
            with _lock:
                _recent.extend(events)
        elif resp.status_code == 429 or resp.status_code >= 500:
            _put_back(events, generation)
        else:
            log.warning("dubeval.com refused usage stats: HTTP %s", resp.status_code)
    except requests.exceptions.ReadTimeout:
        log.info("Usage stats: no answer from dubeval.com, not retried")
    except requests.RequestException as e:
        log.info("Usage stats not sent: %s", type(e).__name__)
        _put_back(events, generation)
    except Exception as e:  # stats must never get in the way of the app
        log.warning("Could not send usage stats: %s", type(e).__name__)
    with _lock:
        more = delivered and len(_queue) >= MAX_BATCH
    if more:                                       # only after a success: a failing site isn't asked again and again
        _schedule()


def _put_back(events: list[dict], generation: int) -> None:
    """Keeps events for the next try, unless the person said no since they left the queue. The newest stay if it's full."""
    with _lock:
        if generation != _generation:
            return
        kept = (events + list(_queue))[-MAX_QUEUE:]
        _queue.clear()
        _queue.extend(kept)
