"""The Evaluations list on the app's home screen: finished evaluations (run folders) and drafts (a start page that was
filled in but not run yet), as PersoDub lists its projects.

A run folder under pipeline.RUNS_DIR holds report.json (one dub) or comparison.json + report_A.json, ... (several).
Its card is cached in card.json, made again whenever those files change, and its picture in thumb.jpg. A draft is
data/drafts/<id>.json: the start page's fields as the page saved them, a picture and, once it was started, its job.
Evaluations stay until the person deletes them, so the videos they play (uploads, share-link downloads) are kept too:
referenced_inputs() names them for the pruning of uploads and of the share-link cache.
"""
import base64
import json
import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

from dubeval import pipeline
from dubeval.paths import DATA_DIR

log = logging.getLogger(__name__)

DRAFTS_DIR = DATA_DIR / "drafts"
RUN_ID_RE = re.compile(r"^\d{8}-\d{6}_[0-9a-f]{8}$")
DRAFT_ID_RE = re.compile(r"^[0-9a-f]{12}$")
MAX_DRAFT_BYTES = 512 * 1024                 # the fields and a small picture; a bigger draft is refused
MAX_THUMB_BYTES = 400 * 1024
CARD_VERSION = 3                             # bump when a card gains or changes a field
THUMB = "thumb.jpg"
NO_SUCH_EVALUATION = "That evaluation is gone. It may have been deleted."
NO_SUCH_DRAFT = "That draft is gone. It may have been deleted or started."
DRAFT_TOO_BIG = "This draft is too big to keep."
EMPTY_TITLE = "Type a title for this result."


def _runs() -> Path:
    return Path(pipeline.RUNS_DIR)


def _drafts() -> Path:
    return Path(DRAFTS_DIR)


def _read(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write(path: Path, data: dict) -> None:
    """Writes JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def run_folder(run_id: str) -> Path:
    """The folder of an evaluation by its id; ValueError if the id is malformed or the folder is gone."""
    if not RUN_ID_RE.match(str(run_id or "")):
        raise ValueError(NO_SUCH_EVALUATION)
    folder = _runs() / run_id
    if not ((folder / "report.json").is_file() or (folder / "comparison.json").is_file()):
        raise ValueError(NO_SUCH_EVALUATION)
    return folder


# ----- finished evaluations -----

def _sources(folder: Path) -> list[Path]:
    """The files a run's card is made from (their change makes the card again)."""
    return [f for f in [folder / "report.json", folder / "comparison.json", *sorted(folder.glob("report_[A-H].json"))]
            if f.is_file()]


def _signature(folder: Path) -> list:
    """What the card was made from: each source file's name, exact time and size (a rename within one clock tick
    still changes the size)."""
    return [[f.name, f.stat().st_mtime_ns, f.stat().st_size] for f in _sources(folder)]


def _card_from_files(folder: Path) -> Optional[dict]:
    """A run's card made from its saved report(s), or None when they can't be read."""
    comp = _read(folder / "comparison.json")
    reports = ([_read(folder / f"report_{d}.json") for d in comp.get("dubs") or []] if comp
               else [_read(folder / "report.json")])
    if not reports or any(r is None or "report" not in r for r in reports):
        return None
    first = reports[0]["report"].get("project") or {}
    res = reports[0].get("results") or {}
    source_code = ((res.get("share") or {}).get("source_language_code")
                   or (res.get("metadata") or {}).get("detected_source_language"))
    # The videos the review plays, dubs first (the card's picture comes from the first one that still exists).
    inputs = list(dict.fromkeys(p for key in ("dubbed_video_path", "input_video_path") for r in reports
                                if isinstance(p := ((r.get("results") or {}).get("pipeline") or {}).get(key), str) and p))
    if comp:
        rec = comp.get("recommendation") or {}
        title, verdict = comp.get("custom_title") or rec.get("title") or first.get("title"), rec.get("verdict")
    else:
        title, verdict = first.get("title"), (reports[0]["report"].get("overall") or {}).get("level")
    return {"card_version": CARD_VERSION, "id": folder.name, "kind": "comparison" if comp else "single",
            "title": title, "verdict": verdict, "dubs": len(reports),
            "source_language": first.get("source_language"), "source_language_code": source_code,
            "target_language": first.get("target_language"),
            "target_language_code": first.get("target_language_code"), "duration_sec": first.get("duration_sec"),
            "created": first.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S",
                                                               time.localtime(folder.stat().st_mtime)),
            "inputs": inputs, "sources": _signature(folder)}


def card(folder: Path) -> Optional[dict]:
    """A run's card: the cached card.json while the reports are exactly as it was made from, else made again."""
    if not _sources(folder):
        return None
    cached = _read(folder / "card.json")
    if cached and cached.get("card_version") == CARD_VERSION and cached.get("sources") == _signature(folder):
        return cached
    made = _card_from_files(folder)
    if made:
        try:
            _write(folder / "card.json", made)
        except OSError as e:
            log.warning("Could not cache the card of %s: %s", folder.name, e)
    return made


def evaluations() -> list[dict]:
    """Every finished evaluation's card, newest first."""
    folder = _runs()
    if not folder.is_dir():
        return []
    cards = [c for c in (card(d) for d in folder.iterdir() if d.is_dir() and RUN_ID_RE.match(d.name)) if c]
    return sorted(cards, key=lambda c: c["id"], reverse=True)       # run ids start with their date and time


def thumbnail(run_id: str) -> Optional[Path]:
    """The run's picture, made once from its dub (else its original) when it has none; None if it can't be made."""
    folder = run_folder(run_id)
    path = folder / THUMB
    if path.is_file():
        return path
    c = card(folder) or {}
    from dubeval.preview import _frame
    for video in c.get("inputs") or []:
        if Path(video).is_file():
            uri = _frame(video, c.get("duration_sec"))
            if uri and save_thumbnail(path, uri):
                return path
    return None


def save_thumbnail(path: Path, data_uri: Optional[str]) -> bool:
    """Writes a data:image/... URI (a preview's picture) as an image file; False when it isn't a small image."""
    m = re.fullmatch(r"data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)", data_uri or "")
    if not m:
        return False
    try:
        data = base64.b64decode(m.group(2), validate=True)
    except ValueError:
        return False
    if not data or len(data) > MAX_THUMB_BYTES:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return True
    except OSError as e:
        log.warning("Could not save a picture: %s", e)
        return False


def rename(run_id: str, title: str) -> dict:
    """Gives a finished evaluation a new title: its saved report (one dub) or its comparison, and its card."""
    title = " ".join((title or "").split())
    if not title:
        raise ValueError(EMPTY_TITLE)
    folder = run_folder(run_id)
    if (folder / "comparison.json").is_file():
        comp = _read(folder / "comparison.json") or {}
        comp["custom_title"] = title
        _write(folder / "comparison.json", comp)
    else:
        from dubeval.report import build_report
        data = _read(folder / "report.json") or {}
        results = {**(data.get("results") or {}), "report": data.get("report") or {}}
        results.setdefault("pipeline", {})["custom_title"] = title
        results["report"] = build_report(results, results["report"].get("lang") or "en")
        pipeline.save_report_files(results, folder)
    return {"id": run_id, "title": title}


def delete(run_id: str) -> list[Path]:
    """Deletes a finished evaluation's folder; returns the inputs it used that nothing else uses any more."""
    folder = run_folder(run_id)
    used = set((card(folder) or {}).get("inputs") or [])
    shutil.rmtree(folder, ignore_errors=True)
    if folder.exists():
        raise OSError(f"Could not delete {folder}")
    still = referenced_inputs()
    return [Path(p) for p in used if p not in still]


# ----- drafts -----

def _draft_path(draft_id: str) -> Path:
    if not DRAFT_ID_RE.match(str(draft_id or "")):
        raise ValueError(NO_SUCH_DRAFT)
    return _drafts() / f"{draft_id}.json"


def get_draft(draft_id: str) -> dict:
    """A draft by id; ValueError when it is gone."""
    data = _read(_draft_path(draft_id))
    if data is None:
        raise ValueError(NO_SUCH_DRAFT)
    return data


def _drop_unfinished_run(draft: dict) -> None:
    """Deletes the run folder of a draft's job that ended without results (stopped or failed: only its picture);
    never while that job is still running."""
    from dubeval import jobs
    started = draft.get("job") or {}
    job = jobs.get_job(started.get("id"))
    if job is not None and job.status == "running":
        return
    folder = Path(started.get("folder") or "")
    if (folder.name and RUN_ID_RE.match(folder.name) and folder.parent.resolve() == _runs().resolve()
            and folder.is_dir() and not _sources(folder)):
        shutil.rmtree(folder, ignore_errors=True)


def save_draft(draft_id: Optional[str], name: Optional[str], thumbnail_uri: Optional[str], form: dict) -> dict:
    """Creates (no id) or replaces a draft: the start page's fields (form), a name and a picture (a data: URI).
    Editing a draft whose evaluation failed makes it a plain draft again."""
    if not isinstance(form, dict):
        raise ValueError(DRAFT_TOO_BIG)
    now = time.time()
    old = get_draft(draft_id) if draft_id else {}
    _drop_unfinished_run(old)
    draft = {"id": old.get("id") or uuid.uuid4().hex[:12], "created": old.get("created") or now, "updated": now,
             "name": " ".join((name or "").split())[:200] or None,
             "thumbnail": thumbnail_uri if thumbnail_uri and thumbnail_uri.startswith("data:image/") else None,
             "form": form, "job": None}
    if len(json.dumps(draft, ensure_ascii=False).encode("utf-8")) > MAX_DRAFT_BYTES:
        draft["thumbnail"] = None                   # a big picture is dropped before the draft is refused
        if len(json.dumps(draft, ensure_ascii=False).encode("utf-8")) > MAX_DRAFT_BYTES:
            raise ValueError(DRAFT_TOO_BIG)
    _write(_draft_path(draft["id"]), draft)
    return draft


def start_draft(draft_id: str, job_id: str, folder: str) -> None:
    """Marks a draft as started (its job) and gives the run folder its picture; a failure is logged, never raised."""
    try:
        draft = get_draft(draft_id)
        draft["job"] = {"id": job_id, "folder": folder}
        _write(_draft_path(draft_id), draft)
        save_thumbnail(Path(folder) / THUMB, draft.get("thumbnail"))
    except (OSError, ValueError) as e:
        log.warning("Could not mark the draft %s as started: %s", draft_id, e)


def delete_draft(draft_id: str) -> None:
    """Deletes a draft (ValueError when it is gone)."""
    draft = get_draft(draft_id)
    _drop_unfinished_run(draft)
    _draft_path(draft_id).unlink()


def drafts() -> list[dict]:
    """Every draft, newest first."""
    folder = _drafts()
    if not folder.is_dir():
        return []
    found = [d for d in (_read(f) for f in folder.glob("*.json")) if d and DRAFT_ID_RE.match(str(d.get("id")))]
    return sorted(found, key=lambda d: d.get("updated") or 0, reverse=True)


# ----- what must not be pruned -----

def _uploads_in(value) -> set[str]:
    """The upload ids ("upload:<id>") anywhere in a draft's fields."""
    if isinstance(value, str):
        return {value[len("upload:"):]} if value.startswith("upload:") else set()
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return set().union(*(_uploads_in(v) for v in value)) if value else set()
    return set()


def referenced_inputs() -> set[str]:
    """The input files that kept evaluations play, and "upload:<id>" for every upload a draft holds."""
    used = {p for c in evaluations() for p in c.get("inputs") or []}
    for d in drafts():
        used |= {f"upload:{u}" for u in _uploads_in(d.get("form"))}
    return used


def protects(folder: Path, used: set[str]) -> bool:
    """Whether a folder (an upload or a share link's downloads) holds a file in use, or is an upload a draft holds."""
    if f"upload:{folder.name}" in used:
        return True
    root = os.path.normcase(str(folder.resolve()))
    return any(os.path.normcase(str(Path(p).resolve())).startswith(root + os.sep)
               for p in used if not p.startswith("upload:"))
