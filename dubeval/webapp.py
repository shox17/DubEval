"""The web interface: pick an original and its dub, follow the evaluation, then review it on a timeline.

    dubeval web                    # opens http://127.0.0.1:<port>/ in the browser

The page is plain JavaScript in dubeval/web/ (no build step). The server only listens on this machine, and a fresh
random token is made at every launch: the browser gets it once through the launch URL and keeps it in a
same-site cookie, so other websites and other users of the machine can't drive the server or read its files.
Media are served only from a finished job's own input files.
"""
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlsplit

import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from dubeval import asr, feedback, history, jobs, library, packs, pipeline, settings
from dubeval.compare import MAX_DUBS, build_ranking
from dubeval.i18n import TEXT, UI_LANGUAGES, translate_message
from dubeval.inputs import MAX_MEDIA_BYTES, TOO_BIG, is_link
from dubeval.localweb import PAGE_CSP, REPORT_CSP, add_security_headers, bind, is_local_host, run
from dubeval.paths import DATA_DIR
from dubeval.perso_api import SHARE_HOSTS, PersoError, parse_share_url
from dubeval.report import build_report
from dubeval.meaning import available as meaning_available
from dubeval.translation_judge import DUB_TYPES, available_judges
from dubeval.languages import LANGUAGES as SPEECH_LANGUAGES
from dubeval.release_notes import notes as release_notes
from dubeval.version import REPOSITORY_URL, TOOL_VERSION

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
UPLOADS_DIR = DATA_DIR / "uploads"
MAX_UPLOADS = 40                      # older uploaded files are deleted beyond this many
PEAKS_PER_SEC = 50                    # waveform resolution sent to the timeline
COOKIE = "dubeval_web"
UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{16}$")
TOO_MANY_DUBS = f"Compare at most {MAX_DUBS} dubs at a time."
NEED_ORIGINAL = "Choose the original video, or paste Perso share links (they include the original)."
NO_LARGE_MODEL = "The large speech model isn't installed. Get it on the Downloads page."
EXPORT_KINDS = ("html", "xlsx", "text", "json")
NO_EXPORT_KIND = "Choose at least one file to export."
EMPTY_TITLE = "Type a title for this result."
CANT_CONTINUE = "This evaluation can't continue. Start it again from its draft."
COULD_NOT_DELETE = "Couldn't delete this evaluation. Close anything that uses its files, then try again."
MIXED_INPUTS = "Use Perso share links for every dub, or files and other links for every dub, not a mix."

Lang = Literal["en", "ko", "pt", "es"]


class DubOptions(BaseModel):
    """What one dub of a comparison is: its kind and its language (each falls back to the shared value)."""
    dub_type: Optional[str] = None
    target_lang: Optional[str] = None
    subtitles: Optional[str] = None       # this dub's own subtitle file (a path or upload:<id>)


class EvaluationBody(BaseModel):
    """One original and its dub, or several dubs to compare: paths on this computer, links, or uploads (upload:<id>)."""
    original: Optional[str] = None        # may stay empty for Perso share links: the share includes the original
    dub: str = Field(min_length=1)
    original_subtitles: Optional[str] = None
    dub_subtitles: Optional[str] = None
    more_dubs: list[str] = Field(default_factory=list, description="Dubs B, C, ... to compare with the first")
    dub_options: list[DubOptions] = Field(default_factory=list, description="Per dub (A, B, ...): kind and language")
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    dub_type: Optional[str] = None
    translation_check: bool = True
    # Which translation checker (start page): auto = the first one set up, or one by name; off = none.
    judge: Literal["auto", "claude", "gemini", "openai", "ollama", "off"] = "auto"
    lipsync: bool = False
    allow_different: bool = False
    # auto: the large model on a GPU when it is downloaded, else the standard one; or either one by name
    speech_model: Literal["auto", "standard", "large"] = "auto"
    lang: Lang = "en"
    draft_id: Optional[str] = None        # the draft this start page was (its card then follows the evaluation)


class DraftBody(BaseModel):
    """A start page filled in but not run yet: its fields as the page keeps them, a name and a small picture."""
    name: Optional[str] = Field(None, max_length=200)
    thumbnail: Optional[str] = Field(None, max_length=600_000)       # a preview's data:image/... URI
    form: dict = Field(default_factory=dict)


class TitleBody(BaseModel):
    """A result's new title (the video's own name stays in the saved data)."""
    title: str = Field(min_length=1, max_length=200)


class VoteBody(BaseModel):
    """A reviewer's vote on one problem interval of a finished report."""
    index: int = Field(ge=0)
    vote: Literal["real", "false_alarm"]


def _upload_path(spec: Optional[str]) -> Optional[str]:
    """upload:<id> → the uploaded file's path; anything else (a path or a link) is passed on unchanged."""
    if not spec or not spec.startswith("upload:"):
        return (spec or "").strip() or None
    upload_id = spec[len("upload:"):]
    folder = Path(UPLOADS_DIR) / upload_id
    files = [f for f in folder.iterdir() if f.is_file()] if UPLOAD_ID_RE.match(upload_id) and folder.is_dir() else []
    if not files:
        raise HTTPException(status_code=400, detail="That uploaded file is gone. Choose it again.")
    return str(files[0])


def _prune_uploads(keep: int = MAX_UPLOADS) -> None:
    """Deletes all but the newest `keep` uploads, except those a kept evaluation plays or a draft holds."""
    folder = Path(UPLOADS_DIR)
    if folder.is_dir():
        old = sorted((d for d in folder.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime, reverse=True)[keep:]
        used = library.referenced_inputs() if old else set()
        for d in old:
            if not library.protects(d, used):
                shutil.rmtree(d, ignore_errors=True)


def _free_uploads(paths: list[Path]) -> None:
    """Deletes the upload folders of files a deleted evaluation used and nothing else uses (never other files)."""
    root = Path(UPLOADS_DIR).resolve()
    for p in paths:
        d = Path(p).resolve().parent
        if d.parent == root and UPLOAD_ID_RE.match(d.name):
            shutil.rmtree(d, ignore_errors=True)


def _safe_name(name: str) -> str:
    """A file name that is safe on every system (keeps the extension, which ffmpeg and the browser use)."""
    p = Path(Path(name or "file").name)
    stem = re.sub(r"[^\w-]+", "_", p.stem).strip("_")[:80] or "file"
    ext = re.sub(r"[^\w]+", "", p.suffix)[:10]
    return stem + (f".{ext}" if ext else "")


def peaks(path: str, offset_sec: float = 0.0, parts: Optional[list] = None, length_sec: Optional[float] = None,
          per_sec: int = PEAKS_PER_SEC) -> list[float]:
    """The loudest sample per 1/per_sec s (0..1), on the original's timeline when an offset or parts are given."""
    from dubeval.evaluate import SAMPLE_RATE, extract_audio, load_audio
    from dubeval.pairing import align_dub, align_dub_parts
    with tempfile.TemporaryDirectory(prefix="dubeval_") as tmp:
        y = load_audio(extract_audio(path, str(Path(tmp) / "a.wav")))
    length = int(round(length_sec * SAMPLE_RATE)) if length_sec else None
    if parts:
        y = align_dub_parts(y, parts, SAMPLE_RATE, length or len(y))
    elif offset_sec or length:
        y = align_dub(y, offset_sec, SAMPLE_RATE, length)
    step = SAMPLE_RATE // per_sec
    n = len(y) // step
    if not n:
        return []
    p = np.abs(y[:n * step]).reshape(n, step).max(axis=1)
    top = float(p.max()) or 1.0
    return [round(float(v) / top, 3) for v in p]


def _texts(lang: str) -> dict:
    """The page's texts (w.*, stage.*, report labels) in one language."""
    keys = [k for k in TEXT if k.startswith(("w.", "stage.", "h.", "f.", "verdict.", "mode.", "r.m.", "table.measure"))]
    return {k: TEXT[k].get(lang) or TEXT[k]["en"] for k in keys}


def make_app(token: str) -> FastAPI:
    """The web app; every route but the launch page needs the session cookie set from `token`."""
    app = FastAPI(title="DubEval", version=TOOL_VERSION, docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(HTTPException)
    async def translated(request: Request, exc: HTTPException):
        """Errors in the page's language (it sends Accept-Language: en | ko | pt | es)."""
        lang = (request.headers.get("accept-language") or "en")[:2]
        detail = translate_message(exc.detail, lang) if isinstance(exc.detail, str) else exc.detail
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)

    def guard(request: Request) -> None:
        """Only this machine's browser with this launch's cookie (also blocks DNS-rebinding hosts)."""
        if not is_local_host(request.headers.get("host")):
            raise HTTPException(status_code=403, detail="Open DubEval at http://127.0.0.1.")
        if not hmac.compare_digest(request.cookies.get(COOKIE, ""), token):
            raise HTTPException(status_code=401, detail="Open DubEval from the link printed by `dubeval web`.")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, token_given: Optional[str] = None):
        """The page. The launch link carries ?token_given=...; it becomes a cookie and the link is cleaned."""
        if token_given is not None:
            if not hmac.compare_digest(token_given, token):
                raise HTTPException(status_code=401, detail="This link is from an earlier launch. Use the new one.")
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie(COOKIE, token, httponly=True, samesite="strict")
            return resp
        guard(request)
        return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))

    @app.middleware("http")
    async def revalidate(request: Request, call_next):
        """The page's own files are checked on every load, so an updated DubEval never runs yesterday's script."""
        response = await call_next(request)
        if request.url.path.startswith("/static/") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache"
        return response

    add_security_headers(app, csp=lambda path: PAGE_CSP)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    api = [Depends(guard)]

    @app.get("/api/info", dependencies=api)
    def info(lang: Lang = "en") -> dict:
        """Texts, languages, dub types and which translation judges are ready."""
        return {"version": TOOL_VERSION, "languages": UI_LANGUAGES, "texts": _texts(lang), "dub_types": list(DUB_TYPES),
                "judges": available_judges(), "large_model": packs.state("large_model") == "installed",
                "speech_auto": asr.default_model(),
                "meaning_ready": meaning_available(),
                "speech_languages": {code: name.title() for code, name in SPEECH_LANGUAGES.items()},
                "whats_new": release_notes(TOOL_VERSION, lang), "repository": REPOSITORY_URL}

    def settings_view() -> dict:
        """Which keys are set (never the keys themselves) and which translation checker runs."""
        from dubeval import translation_judge as tj
        return {"keys": settings.status(), "judge": {
            "active": tj.judge_provider(), "available": tj.available_judges(),
            "choice": (os.getenv("DUBEVAL_JUDGE") or "auto").strip().lower(), "order": list(tj.JUDGES),
            "local_model": tj.OLLAMA_MODEL}, "data_dir": str(Path(DATA_DIR).resolve()), "version": TOOL_VERSION}

    @app.get("/api/models", dependencies=api)
    def list_models() -> dict:
        """Settings → Models: every model, built in or downloadable, grouped, with any running download."""
        out = packs.catalog()
        for group in out["groups"]:
            for row in group["rows"]:
                job = pack_job(row["id"]) if row["kind"] == "pack" else None
                row["job"] = job.id if job else None
        return out

    @app.post("/api/settings/open-data", dependencies=api)
    def open_data() -> dict:
        """Opens DubEval's data folder (reports, history, votes, keys) in the file manager. Only that folder."""
        folder = Path(DATA_DIR).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(folder))                         # noqa: S606 - our own folder, no user input
        else:
            import subprocess
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])
        return {"opened": True}

    @app.get("/api/settings", dependencies=api)
    def get_settings() -> dict:
        return settings_view()

    @app.put("/api/settings/keys/{provider}", dependencies=api)
    async def put_key(provider: str, request: Request) -> dict:
        """Saves an API key. Read by hand, not through a model: a validation error must never echo the key back."""
        if provider not in settings.KEYS:
            raise HTTPException(status_code=404, detail="No setting with this name.")
        try:
            body = await request.json()
            key = body.get("key") if isinstance(body, dict) else None
        except ValueError:
            key = None
        if not isinstance(key, str):
            raise HTTPException(status_code=400, detail=settings.BAD_KEY)
        try:
            settings.save_key(provider, key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return settings_view()

    @app.delete("/api/settings/keys/{provider}", dependencies=api)
    def delete_key(provider: str) -> dict:
        """Removes a key saved from this page (a key set elsewhere stays; the response says so)."""
        if provider not in settings.KEYS:
            raise HTTPException(status_code=404, detail="No setting with this name.")
        settings.remove_key(provider)
        return settings_view()

    pack_jobs: dict[str, str] = {}          # pack id → the id of the job downloading it

    def pack_job(pack_id: str) -> Optional[jobs.Job]:
        """The running download of a pack, if any."""
        job = jobs.get_job(pack_jobs.get(pack_id))
        return job if job is not None and job.status == "running" else None

    @app.get("/api/packs", dependencies=api)
    def list_packs() -> dict:
        """The optional downloads: state, sizes, whether this computer can use each, and any running download."""
        return {"packs": [{**p, "job": (pack_job(p["id"]).id if pack_job(p["id"]) else None)} for p in packs.summary()],
                "nvidia_gpu": packs.nvidia_gpu()}

    @app.post("/api/packs/{pack_id}/install", status_code=202, dependencies=api)
    def install_pack(pack_id: str) -> dict:
        """Starts (or resumes) downloading a pack; follow it with /api/jobs/{id}, stop it with its cancel route."""
        if pack_id not in packs.PACKS:
            raise HTTPException(status_code=404, detail="No download with this name.")
        if not packs.available(pack_id):
            raise HTTPException(status_code=400, detail=packs.NOT_HERE)
        running = pack_job(pack_id)
        if running:
            return {"id": running.id}

        def runner(report, cancel):
            try:
                return {"pack": packs.install(pack_id, lambda message, fraction: report(jobs.Progress(
                    "pack", message, fraction)), stop=cancel.is_set)}
            except packs.Stopped:
                raise jobs.Cancelled()
        job = jobs.start_job(runner, {"kind": "pack", "pack": pack_id}, ["pack"])
        pack_jobs[pack_id] = job.id
        return {"id": job.id}

    @app.delete("/api/packs/{pack_id}", dependencies=api)
    def remove_pack(pack_id: str) -> dict:
        """Deletes an installed pack (or a half-finished download of it)."""
        if pack_id not in packs.PACKS:
            raise HTTPException(status_code=404, detail="No download with this name.")
        if pack_job(pack_id):
            raise HTTPException(status_code=409, detail="Stop the download first.")
        packs.remove(pack_id)
        return next(p for p in packs.summary() if p["id"] == pack_id)

    @app.get("/api/preview", dependencies=api)
    def source_preview(source: str = Query(..., max_length=4096)) -> dict:
        """What the start page shows for a link or a path before anything runs (dubeval/preview.py)."""
        from dubeval import preview
        try:
            return preview.preview(_upload_path(source) if source.startswith("upload:") else source)
        except (ValueError, PersoError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/uploads", dependencies=api)
    def upload(file: UploadFile = File(...)) -> dict:
        """Saves a chosen file under data/uploads/<id>/; evaluations refer to it as upload:<id>."""
        upload_id = uuid.uuid4().hex[:16]
        folder = Path(UPLOADS_DIR) / upload_id
        folder.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(folder / _safe_name(file.filename), "wb") as out:
            while chunk := file.file.read(1 << 20):
                written += len(chunk)
                if written > MAX_MEDIA_BYTES:              # a huge file would fill the disk
                    break
                out.write(chunk)
        if written > MAX_MEDIA_BYTES:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(status_code=413, detail=TOO_BIG)
        _prune_uploads()
        return {"id": f"upload:{upload_id}", "name": file.filename}

    @app.post("/api/evaluations", status_code=202, dependencies=api)
    def start(body: EvaluationBody) -> dict:
        """Starts an evaluation (one dub) or a comparison (more_dubs given) in the background; poll /api/jobs/{id}."""
        if any(t and t not in DUB_TYPES for t in [body.dub_type, *(o.dub_type for o in body.dub_options)]):
            raise HTTPException(status_code=400, detail=pipeline.BAD_DUB_TYPE)
        if len(body.more_dubs) + 1 > MAX_DUBS:
            raise HTTPException(status_code=400, detail=TOO_MANY_DUBS)
        if len(body.dub_options) > len(body.more_dubs) + 1:
            raise HTTPException(status_code=400, detail=pipeline.TOO_MANY_DUB_OPTIONS)
        per_dub = [{"dub_type": o.dub_type or None, "target_lang": (o.target_lang or "").strip() or None,
                    "dub_subtitles": _upload_path(o.subtitles)} for o in body.dub_options]
        original = _upload_path(body.original)
        dubs = [_upload_path(d) for d in [body.dub, *body.more_dubs]]
        shares = [_is_share_link(d) for d in dubs]
        if any(shares):
            if not all(shares):
                raise HTTPException(status_code=400, detail=MIXED_INPUTS)
            return {"id": _started(body, _start_share_job(body, original, dubs)).id}
        if not original:
            raise HTTPException(status_code=400, detail=NEED_ORIGINAL)
        options = dict(original_subtitles=_upload_path(body.original_subtitles), source_lang=body.source_lang or None,
                       target_lang=body.target_lang or None, dub_type=body.dub_type or None,
                       use_translation_judge=_judge_choice(body), include_lipsync=body.lipsync,
                       allow_different=body.allow_different, **_speech_model(body))
        _, folder = pipeline.new_run_dir()
        params = {"original": body.original, "dubs": [body.dub, *body.more_dubs], "folder": folder}
        if len(dubs) == 1:
            own = {k: v for k, v in (per_dub[0] if per_dub else {}).items() if v is not None}
            own.setdefault("dub_subtitles", _upload_path(body.dub_subtitles))   # the card's own field, else the old one
            job = jobs.start_job(lambda report, cancel: pipeline.run_files_evaluation(
                original, dubs[0], report=report, cancel_event=cancel, report_lang=body.lang, out_dir=folder,
                history_mode="web", **{**options, **own}),
                {"kind": "files", **params}, pipeline.file_stages())
        else:
            # Each dub's own subtitle file comes with its settings (per_dub); body.dub_subtitles is one dub's.
            job = jobs.start_job(lambda report, cancel: pipeline.run_files_comparison(
                original, dubs, folder, report_lang=body.lang, report=report, cancel_event=cancel, per_dub=per_dub,
                **options),
                {"kind": "comparison", **params}, pipeline.files_compare_stages(len(dubs)))
        return {"id": _started(body, job).id}

    def _started(body: EvaluationBody, job: jobs.Job) -> jobs.Job:
        """Keeps the request (Continue runs it again) and ties the job to its draft: the draft's card shows the run,
        and the run folder gets its picture."""
        job.params["request"] = body.model_dump()
        if body.draft_id:
            library.start_draft(body.draft_id, job.id, job.params["folder"])
            job.params["draft_id"] = body.draft_id
        job.save()
        return job

    @app.post("/api/jobs/{job_id}/continue", status_code=202, dependencies=api)
    def continue_job(job_id: str) -> dict:
        """Runs a stopped (or interrupted) evaluation again with the same request, as PersoDub's Resume: what was
        already measured (speech recognition, the same-video check) comes back from the cache, so it picks up about
        where it stopped. Returns the new job's id."""
        job = jobs.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No job with this id.")
        request = job.params.get("request")
        if job.status not in ("cancelled", "interrupted", "failed") or not isinstance(request, dict):
            raise HTTPException(status_code=409, detail=CANT_CONTINUE)
        try:
            body = EvaluationBody(**request)
        except ValueError:
            raise HTTPException(status_code=409, detail=CANT_CONTINUE)
        return start(body)

    # ----- the Evaluations list (home screen) -----

    def _draft_card(d: dict) -> Optional[dict]:
        """A draft's card; a started draft follows its job (running, failed, ...) and goes once the job is done."""
        form = d.get("form") or {}
        out = {"id": d["id"], "name": d.get("name"), "thumbnail": d.get("thumbnail"), "updated": d.get("updated"),
               "dubs": max(1, len(form.get("dubs") or [])), "state": "draft", "job_id": None, "progress": None}
        started = d.get("job") or {}
        job = jobs.get_job(started.get("id")) if started else None
        if job is None:
            return out
        if job.status == "done":
            try:
                library.delete_draft(d["id"])            # its evaluation has its own card now
            except (OSError, ValueError):
                pass
            return None
        state = {"running": "running", "failed": "failed"}.get(job.status, "stopped")
        return {**out, "state": state, "job_id": job.id, "progress": round(job.overall_fraction, 3)}

    @app.get("/api/evaluations", dependencies=api)
    def evaluation_list() -> dict:
        """The home screen's cards: drafts (with started ones following their job), then finished evaluations."""
        cards = [{k: v for k, v in c.items() if k not in ("inputs", "sources", "card_version")}
                 for c in library.evaluations()]
        return {"drafts": [c for c in (_draft_card(d) for d in library.drafts()) if c], "evaluations": cards}

    def _run(run_id: str) -> Path:
        try:
            return library.run_folder(run_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/evaluations/{run_id}/thumb", dependencies=api)
    def evaluation_thumb(run_id: str):
        """A finished evaluation's picture (made from its dub the first time)."""
        _run(run_id)
        path = library.thumbnail(run_id)
        if path is None:
            raise HTTPException(status_code=404, detail="No picture.")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})

    @app.post("/api/evaluations/{run_id}/open", dependencies=api)
    def evaluation_open(run_id: str) -> dict:
        """A finished evaluation as a job the review screen shows: its kept job, or one made again from its files."""
        folder = _run(run_id)
        job = jobs.find_done_job(str(folder)) or _restore(folder)
        if job is None:
            raise HTTPException(status_code=404, detail=library.NO_SUCH_EVALUATION)
        return {"id": job.id, "kind": "comparison" if "comparison" in job.result else "files"}

    @app.put("/api/evaluations/{run_id}/title", dependencies=api)
    def evaluation_rename(run_id: str, body: TitleBody) -> dict:
        """Renames a finished evaluation (its card, its saved report and History)."""
        folder = _run(run_id)
        try:
            out = library.rename(run_id, body.title)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        jobs.forget_folder(str(folder))                  # a kept job still has the old title: open it from the files
        if (folder / "report.html").is_file():
            history.rename(str(folder / "report.html"), out["title"])
        return out

    @app.delete("/api/evaluations/{run_id}", dependencies=api)
    def evaluation_delete(run_id: str) -> dict:
        """Deletes a finished evaluation: its folder, its kept job and the uploaded videos only it used."""
        folder = _run(run_id)
        jobs.forget_folder(str(folder))
        try:
            _free_uploads(library.delete(run_id))
        except OSError as e:
            log.warning("Could not delete %s: %s", run_id, e)
            raise HTTPException(status_code=409, detail=COULD_NOT_DELETE)
        return {"id": run_id}

    def _draft_or_404(draft_id: str) -> dict:
        try:
            return library.get_draft(draft_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/drafts", dependencies=api)
    def draft_create(body: DraftBody) -> dict:
        """Keeps a start page that was filled in, so its card can open it again."""
        try:
            return library.save_draft(None, body.name, body.thumbnail, body.form)
        except ValueError as e:
            raise HTTPException(status_code=413, detail=str(e))

    @app.put("/api/drafts/{draft_id}", dependencies=api)
    def draft_save(draft_id: str, body: DraftBody) -> dict:
        """Saves the draft's fields again (the start page saves as it is edited)."""
        _draft_or_404(draft_id)
        try:
            return library.save_draft(draft_id, body.name, body.thumbnail, body.form)
        except ValueError as e:
            raise HTTPException(status_code=413, detail=str(e))

    @app.get("/api/drafts/{draft_id}", dependencies=api)
    def draft_get(draft_id: str) -> dict:
        """A draft's fields, to fill the start page in again."""
        return _draft_or_404(draft_id)

    @app.delete("/api/drafts/{draft_id}", dependencies=api)
    def draft_delete(draft_id: str) -> dict:
        """Deletes a draft (its uploaded videos are then free to be cleaned up)."""
        _draft_or_404(draft_id)
        library.delete_draft(draft_id)
        return {"id": draft_id}

    def finished(job_id: str) -> jobs.Job:
        """A finished job, or 404/409."""
        job = jobs.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No job with this id.")
        if job.status != "done" or not isinstance(job.result, dict) or not (
                "report" in job.result or "comparison" in job.result):           # e.g. a model download's job
            raise HTTPException(status_code=409, detail=f"The job is {job.status}.")
        return job

    def results_of(job: jobs.Job, dub: Optional[str]) -> dict:
        """One dub's results: the job's own for one dub, else dub A, B, ... of the comparison."""
        if "comparison" not in job.result:
            return job.result
        found = job.result["results"].get(dub or "A")
        if found is None:
            raise HTTPException(status_code=404, detail="No dub with this letter.")
        return found

    @app.get("/api/jobs/{job_id}", dependencies=api)
    def job_state(job_id: str, lang: Lang = "en") -> dict:
        """Status, stage checklist and progress of a job."""
        job = jobs.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No job with this id.")
        return {"id": job.id, "status": job.status, "stage": job.stage, "kind": job.params.get("kind", "files"),
                "message": translate_message(job.message, lang), "progress": round(job.overall_fraction, 3),
                "elapsed_sec": round(job.elapsed_sec, 1), "draft_id": job.params.get("draft_id"),
                "can_continue": job.status in ("cancelled", "interrupted", "failed") and "request" in job.params,
                "error": translate_message(job.error, lang) if job.error else None,
                "stages": [{"id": s, "state": job.stage_state(s)} for s in job.stages]}

    @app.post("/api/jobs/{job_id}/cancel", dependencies=api)
    def cancel(job_id: str) -> dict:
        """Asks a running job to stop."""
        job = jobs.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No job with this id.")
        job.cancel_event.set()
        return {"id": job.id}

    @app.get("/api/jobs/{job_id}/comparison", dependencies=api)
    def comparison(job_id: str, lang: Lang = "en") -> dict:
        """The recommendation, its reasoning and the ranking, in the page's language (without the full reports)."""
        job = finished(job_id)
        if "comparison" not in job.result:
            raise HTTPException(status_code=404, detail="This job evaluated one dub; there is no comparison.")
        res, saved = job.result["results"], job.result["comparison"]
        comp = build_ranking([res[d] for d in saved["dubs"]], lang, run_seconds=saved["meta"].get("run_seconds"))
        return {k: v for k, v in comp.items() if k != "reports"}

    @app.get("/api/jobs/{job_id}/report", dependencies=api)
    def report(job_id: str, lang: Lang = "en", dub: Optional[str] = None) -> dict:
        """One dub's report in the page's language, plus what the timeline needs from its results."""
        job = finished(job_id)
        r = results_of(job, dub)
        sr, seg, pair = r.get("speech_recognition") or {}, r.get("segment_alignment") or {}, r.get("pairing") or {}
        parts = pipeline.applied_parts(pair) if pair else None
        rep = build_report(r, lang, dub=dub or "A") if "comparison" in job.result else build_report(r, lang)
        return {"report": rep, "duration_sec": rep["project"].get("duration_sec"),
                "offset_sec": pair.get("applied_offset_sec") or 0.0, "parts": parts,
                "lines": _with_scripts(r, seg.get("lines") or []),
                "original_segments": [{k: s[k] for k in ("start", "end", "text")} for s in sr.get("original_segments") or []],
                "dub_segments": [{k: s[k] for k in ("start", "end", "text")} for s in sr.get("dubbed_segments") or []],
                "votes": _votes(r), "fixes": _fixes(r), "rubric": _rubric_lines(r, lang)}

    def media_path(r: dict, side: str) -> Path:
        """One dub's own original or dub file (never a path taken from the request)."""
        key = {"original": "input_video_path", "dub": "dubbed_video_path"}.get(side)
        path = Path((r.get("pipeline") or {}).get(key) or "") if key else None
        if path is None or not path.is_file():
            raise HTTPException(status_code=404, detail="That file is gone. Run the evaluation again.")
        return path

    @app.get("/api/jobs/{job_id}/media/{side}", dependencies=api)
    def media(job_id: str, side: str, dub: Optional[str] = None):
        """The original or dub video, with range requests so the player can seek."""
        return FileResponse(media_path(results_of(finished(job_id), dub), side))

    @app.get("/api/jobs/{job_id}/peaks/{side}", dependencies=api)
    def waveform(job_id: str, side: str, dub: Optional[str] = None) -> dict:
        """The waveform of one side on the original's timeline (the dub moved by the measured shift); cached."""
        job = finished(job_id)
        r = results_of(job, dub)
        path = media_path(r, side)
        compared = "comparison" in job.result and side == "dub"
        cache = Path(job.params.get("folder") or tempfile.gettempdir()) / (
            f"peaks_{side}_{dub or 'A'}.json" if compared else f"peaks_{side}.json")
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        pair = r.get("pairing") or {}
        length = r["report"]["project"].get("duration_sec") if side == "dub" else None
        out = {"per_sec": PEAKS_PER_SEC, "peaks": peaks(str(path), pair.get("applied_offset_sec") or 0.0
                                                        if side == "dub" else 0.0,
                                                        pipeline.applied_parts(pair) if side == "dub" else None, length)}
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(out), encoding="utf-8")
        except OSError as e:
            log.warning("Could not cache the waveform: %s", e)
        return out

    @app.put("/api/jobs/{job_id}/title", dependencies=api)
    def rename(job_id: str, body: TitleBody, dub: Optional[str] = None) -> dict:
        """Renames a finished result: the review, exports, its saved report and History use the new title."""
        job = finished(job_id)
        r = results_of(job, dub)
        title = " ".join(body.title.split())
        if not title:
            raise HTTPException(status_code=400, detail=EMPTY_TITLE)
        r.setdefault("pipeline", {})["custom_title"] = title
        job.save()
        report_html = (r.get("pipeline") or {}).get("report_files", {}).get("html")
        if "comparison" not in job.result and job.params.get("folder"):
            try:                                                 # the run's own files, which History reopens
                r["report"] = build_report(r, r["report"].get("lang") or "en")
                pipeline.save_report_files(r, job.params["folder"])
            except (OSError, KeyError, ValueError) as e:
                log.warning("Could not save the renamed report: %s", e)
        if report_html:
            history.rename(report_html, title)
        return {"title": title}

    @app.post("/api/jobs/{job_id}/votes", dependencies=api)
    def vote(job_id: str, body: VoteBody, dub: Optional[str] = None) -> dict:
        """Records a reviewer's vote on one problem interval (dubeval/feedback.py)."""
        rep = results_of(finished(job_id), dub)["report"]
        if body.index >= len(rep["problem_intervals"]):
            raise HTTPException(status_code=404, detail="No problem interval with this number.")
        feedback.vote(rep["project"], rep["problem_intervals"][body.index], body.vote, reviewer="web")
        return {"index": body.index, "vote": body.vote}

    @app.get("/api/jobs/{job_id}/export", dependencies=api)
    def export(job_id: str, kinds: str = "html", lang: Lang = "en"):
        """The finished job's results to save (Export): one file, or several in a ZIP, written in the page's language.

        kinds: a comma-separated choice of html (the report), xlsx (the problem list for Excel), text (the summary),
        json (data).
        """
        job = finished(job_id)
        wanted = [k for k in EXPORT_KINDS if k in kinds.split(",")]
        if not wanted:
            raise HTTPException(status_code=400, detail=NO_EXPORT_KIND)
        folder = Path(tempfile.mkdtemp(prefix="dubeval_export_"))
        try:
            files, title = _export_files(job.result, lang, wanted, folder)
            name = _export_name(title)
            if len(files) == 1:
                path = files[0]
                filename = f"{name} - DubEval{path.suffix}"
            else:
                path = folder / "export.zip"
                with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                    for f in files:
                        z.write(f, f.name)
                filename = f"{name} - DubEval.zip"
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return FileResponse(path, filename=filename, background=BackgroundTask(shutil.rmtree, folder, True))

    @app.get("/api/history", dependencies=api)
    def history_summary(days: Optional[int] = Query(None, ge=1, le=3650)) -> dict:
        """Every past evaluation summarized (dubeval/history.py) plus the reviewer votes (dubeval/feedback.py).

        Each recent run carries `report`: a path under the data folder the page can open with /api/reports, or None
        when its report lives elsewhere (CLI runs into ./output) or is gone.
        """
        records = history.load()
        summary = history.summarize(records, days=days)
        # The latest evaluations leave out ones whose report is gone (deleted on the Evaluations screen): a row the
        # person can't open again. The totals and trends above still count every evaluation that was run.
        kept = [r for r in records if not r.get("report") or Path(r["report"]).is_file()]
        summary["recent"] = [{k: r.get(k) for k in ("time", "mode", "title", "languages", "verdict", "poor", "check",
                                                    "problem_seconds")} | {"report": _report_ref(r.get("report"))}
                             for r in history.summarize(kept, days=days)["recent"]]
        return {"history": summary, "feedback": feedback.summarize(feedback.load())}

    @app.post("/api/history/open", dependencies=api)
    def open_past(path: str) -> dict:
        """A past evaluation (one History names) as a job the review screen can show: its kept job, or one made again
        from the report files in its run folder. Returns {id, kind, dub}: kind "comparison" opens on that dub's tab."""
        known = {_report_ref(r.get("report")) for r in history.load()} - {None}
        if path not in known:
            raise HTTPException(status_code=404, detail="That report is gone (old runs are pruned). Run it again.")
        report_file = Path(DATA_DIR) / path
        m = re.fullmatch(r"report_([A-H])\.html", report_file.name)
        dub = m.group(1) if m else None
        folder = report_file.parent
        job = jobs.find_done_job(str(folder)) or _restore(folder)
        if job is None:
            raise HTTPException(status_code=404, detail="That report is gone (old runs are pruned). Run it again.")
        kind = "comparison" if "comparison" in job.result else "files"
        return {"id": job.id, "kind": kind, "dub": dub if kind == "comparison" else None}

    @app.get("/api/reports", dependencies=api)
    def saved_report(path: str):
        """A past evaluation's saved HTML report: only one the history names, and only under the data folder."""
        known = {_report_ref(r.get("report")) for r in history.load()} - {None}
        if path not in known:
            raise HTTPException(status_code=404, detail="That report is gone (old runs are pruned). Run it again.")
        return FileResponse(Path(DATA_DIR) / path, media_type="text/html; charset=utf-8",
                            headers={"Content-Security-Policy": REPORT_CSP})

    return app


def _restore(folder: Path) -> Optional[jobs.Job]:
    """A finished job rebuilt from a run folder's saved files (report.json, or comparison.json + report_A.json, ...)."""
    def results_of(report_json: Path) -> dict:
        data = json.loads(report_json.read_text(encoding="utf-8"))
        return {**data["results"], "report": data["report"]}
    try:
        if (folder / "comparison.json").is_file():
            comp = json.loads((folder / "comparison.json").read_text(encoding="utf-8"))
            results = {d: results_of(folder / f"report_{d}.json") for d in comp["dubs"]}
            return jobs.restore_job({"kind": "comparison", "folder": str(folder), "restored": True},
                                    pipeline.files_compare_stages(len(comp["dubs"])),
                                    {"comparison": comp, "results": results, "files": {}})
        if (folder / "report.json").is_file():
            return jobs.restore_job({"kind": "files", "folder": str(folder), "restored": True}, pipeline.file_stages(),
                                    results_of(folder / "report.json"))
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("Could not open the past run in %s: %s", folder, e)
    return None


def _with_scripts(results: dict, lines: list[dict]) -> list[dict]:
    """The review's lines, each with what the subtitle files say for it (original_script / dub_script), when given."""
    if not any((results.get("subtitles") or {}).values()):
        return lines
    scripts = {ln["n"]: ln for ln in pipeline.judge_lines(results)}
    return [{**ln, **{k: scripts.get(ln["n"], {}).get(k) for k in ("original_script", "dub_script")
                      if scripts.get(ln["n"], {}).get(k)}} for ln in lines]


def _export_files(result: dict, lang: str, kinds: list[str], folder: Path) -> tuple[list[Path], Optional[str]]:
    """Writes the chosen files of a finished job into folder (a comparison: the comparison and every dub's report);
    returns them and the video's title."""
    if "comparison" in result:
        res, saved = result["results"], result["comparison"]
        comp = build_ranking([res[d] for d in saved["dubs"]], lang, run_seconds=saved["meta"].get("run_seconds"))
        per_dub = {d: {**res[d], "report": comp["reports"][d]} for d in comp["dubs"]}
        written = pipeline.save_comparison_files(comp, per_dub, folder, absolute_videos=True)
        reports = [(d, per_dub[d]["report"]) for d in comp["dubs"]]
        title = comp["recommendation"].get("title")
    else:
        r = {**result, "report": build_report(result, lang)}
        written = pipeline.save_report_files(r, folder, absolute_videos=True)
        reports, title = [(None, r["report"])], r["report"]["project"].get("title")
    files = [Path(p) for key, p in written.items() if key.split("_")[0] in kinds]
    if "xlsx" in kinds:
        files.append(_problems_xlsx(reports, lang, folder / "problems.xlsx"))
    order = {".html": 0, ".xlsx": 1, ".txt": 2, ".json": 3}
    return sorted(files, key=lambda p: (order.get(p.suffix, 9), p.name)), title


def _export_name(title: Optional[str]) -> str:
    """The video's title as a file name: as written, minus what Windows forbids in names (and at most 100 characters)."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", title or "").strip(" .")
    return re.sub(r"\s+", " ", name)[:100].strip() or "DubEval"


def problem_rows(rep: dict, lang: str) -> list[list]:
    """Everything the report asks a person to look at, as table rows [start, end, check, level, description]: every
    check graded Check or Poor (no time: they're about the whole dub), the untimed things to check, then every timed
    problem interval (start and end in seconds)."""
    tr = lambda key: TEXT[key].get(lang) or TEXT[key]["en"]
    level = lambda lv: tr(f"badge.{lv}") if f"badge.{lv}" in TEXT else lv
    rows = [[None, None, m["label"], level(m["level"]), m.get("message") or ""]
            for s in rep["sections"] for m in s["metrics"] if m["level"] in ("check", "poor")]
    rows += [[None, None, tr("w.exp.general"), level(item.get("severity") or "check"), item.get("message") or ""]
             for item in rep.get("things_to_check") or [] if item.get("start") is None]
    rows += [[iv["start"], iv["end"], iv.get("check_label") or iv["check"], level(iv["severity"]), iv["description"]]
             for iv in rep["problem_intervals"]]
    return rows


def _problems_xlsx(reports: list[tuple[Optional[str], dict]], lang: str, path: Path) -> Path:
    """The problem list (problem_rows) of one dub, or of every dub of a comparison, as an Excel sheet headed in the
    page's language."""
    from dubeval.xlsx import write_xlsx
    tr = lambda key: TEXT[key].get(lang) or TEXT[key]["en"]
    many = len(reports) > 1
    head = ([tr("w.exp.col.dub")] if many else []) + [tr(f"w.exp.col.{c}") for c in
                                                       ("start", "end", "check", "severity", "description")]
    rows = [([dub] if many else []) + row for dub, rep in reports for row in problem_rows(rep, lang)]
    widths = ([6] if many else []) + [9, 9, 24, 12, 90]
    return write_xlsx(path, tr("w.exp.sheet"), head, rows, widths, wrap=[len(head) - 1])


def _speech_model(body: EvaluationBody) -> dict:
    """The recognizer to use: this computer's default (auto), the standard one, or the large one when its pack is
    installed."""
    if body.speech_model == "auto":
        return {}
    if body.speech_model == "standard":
        return {"whisper_model_name": "base"}
    if packs.state("large_model") != "installed":
        raise HTTPException(status_code=400, detail=NO_LARGE_MODEL)
    return {"whisper_model_name": packs.LARGE_MODEL}


def _judge_choice(body: EvaluationBody):
    """use_translation_judge for the pipeline: False (off), True (auto) or the chosen checker's name."""
    if not body.translation_check or body.judge == "off":
        return False
    return True if body.judge == "auto" else body.judge


def _is_share_link(spec: Optional[str]) -> bool:
    """Whether a dub is given as a Perso share link (its original and dub then come from Perso's public endpoint)."""
    return bool(spec) and is_link(spec) and (urlsplit(spec.strip()).hostname or "") in SHARE_HOSTS


def _start_share_job(body: EvaluationBody, original: Optional[str], links: list[str]) -> jobs.Job:
    """Evaluates one Perso share link, or compares several, like `dubeval evaluate`/`compare` with share links.

    Each share's metadata gives its languages and lip-sync, so per-dub languages don't apply; one share takes
    subtitle files and its dub kind like any dub (Perso's public share has no subtitles). Lip movement stays automatic
    (lip-synced dubs only) unless asked for.
    """
    try:
        for link in links:
            parse_share_url(link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _, folder = pipeline.new_run_dir()
    common = dict(report_lang=body.lang, use_translation_judge=_judge_choice(body),
                  include_lipsync=True if body.lipsync else None, original=original or None, **_speech_model(body))
    params = {"original": body.original, "dubs": links, "folder": folder, "share": True}
    if len(links) == 1:
        own = (body.dub_options[0] if body.dub_options else None)
        extra = dict(original_subtitles=_upload_path(body.original_subtitles),
                     dub_subtitles=_upload_path(own.subtitles if own and own.subtitles else body.dub_subtitles),
                     dub_type=(own.dub_type if own and own.dub_type else body.dub_type) or None)
        return jobs.start_job(lambda report, cancel: pipeline.run_share_evaluation(
            links[0], report=report, cancel_event=cancel, out_dir=folder, history_mode="web", **common, **extra),
            {"kind": "files", **params}, pipeline.share_stages())
    per_dub = [{"dub_subtitles": _upload_path(o.subtitles), "dub_type": o.dub_type or None} for o in body.dub_options]
    return jobs.start_job(lambda report, cancel: pipeline.run_comparison(
        links[0], links[1], folder, more_urls=tuple(links[2:]), report=report, cancel_event=cancel,
        original_subtitles=_upload_path(body.original_subtitles), per_dub=per_dub, **common),
        {"kind": "comparison", **params}, pipeline.compare_stages(len(links)))


def _report_ref(path: Optional[str]) -> Optional[str]:
    """A saved report's path relative to the data folder (forward slashes), or None if it's elsewhere or gone."""
    if not path:
        return None
    try:
        p, root = Path(path).resolve(), Path(DATA_DIR).resolve()
        return p.relative_to(root).as_posix() if p.suffix == ".html" and p.is_file() else None
    except (OSError, ValueError):
        return None


def _rubric_lines(results: dict, lang: str) -> dict:
    """Each judged line's rubric in the page's language, by line number: scores, the reasons for low ones, the error
    type and the suggested translation (empty when the check didn't use the rubric)."""
    from dubeval.i18n import t
    from dubeval.intervals import local_text
    tj = results.get("translation_judge") or {}
    if not tj.get("measured") or not tj.get("rubric"):
        return {}
    return {str(j["line"]): {"scores": j["scores"], "reasons": {c: local_text(v, lang) for c, v in j["reasons"].items()},
                             "error_type": t(f"r.tcat.{j['error_type']}", lang) if j["error_type"] != "no_error" else "",
                             "suggested": j.get("ideal_translation") or "",
                             "misheard": bool(j.get("may_be_recognition_error"))}
            for j in tj.get("lines") or []}


def _fixes(results: dict) -> dict:
    """For report rows that weren't measured for a reason the person can fix here: where to fix it (a Settings tab).

    {"translation_check": "keys"} when no translation checker works; {"meaning_screen": "models"} when the offline
    meaning model isn't installed; {"language": "models"} when recognition couldn't make out the dub's language and
    the large speech model isn't installed yet."""
    from dubeval.report import speech_problem
    fixes = {}
    tj, ms = results.get("translation_judge") or {}, results.get("meaning_screen") or {}
    if tj.get("reason_key") in ("r.judge.no_key", "r.judge.bad_key", "r.judge.no_credit"):
        fixes["translation_check"] = "keys"
    if ms.get("reason_key") == "r.screen.not_installed" and packs.available("meaning") \
            and packs.state("meaning") != "installed":
        fixes["meaning_screen"] = "models"
    problem = speech_problem(results)
    if problem and problem["kind"] == "unrecognized" and packs.state("large_model") != "installed":
        fixes["language"] = "models"
    return fixes


def _votes(results: dict) -> dict:
    """The current vote per problem-interval index of this report."""
    rep, current = results["report"], feedback.latest()
    out = {}
    for i, interval in enumerate(rep["problem_intervals"]):
        entry = current.get(feedback.interval_key(rep["project"], interval))
        if entry:
            out[str(i)] = entry["vote"]
    return out


def _wait_for_exit(pid: int) -> None:
    """Returns once the process pid has ended (at once if it already has)."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        handle = kernel32.OpenProcess(0x00100000, False, pid)            # SYNCHRONIZE
        if not handle:
            return
        kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0xFFFFFFFF)  # INFINITE
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return
    import time
    while os.getppid() == pid:                                            # an orphan gets a new parent
        time.sleep(1.0)


def exit_with_parent(parent_pid: Optional[int] = None, exit_now=os._exit, wait=_wait_for_exit) -> threading.Thread:
    """Ends this process when the program that started it (the desktop app) is gone, even after it crashed.

    It waits on the parent process, never on stdin: on Windows a thread blocked reading the stdin pipe froze any
    other thread that loaded scipy's math libraries (their start-up looks at the standard handles), so evaluations
    hung at "Reading the sound of both videos...".
    """
    parent_pid = parent_pid or os.getppid()

    def watch():
        """Blocks until the parent ends, then exits at once (no clean-up runs: the parent is already gone)."""
        wait(parent_pid)
        try:                                        # os._exit skips atexit: stop DubEval's own Ollama here
            from dubeval import local_judge
            local_judge.stop()
        except Exception as e:
            log.warning("Could not stop the local translation checker: %s", e)
        exit_now(0)

    thread = threading.Thread(target=watch, name="exit-with-parent", daemon=True)
    thread.start()
    return thread


def serve(port: int = 0, open_browser: bool = True, host: str = "127.0.0.1") -> None:
    """Runs the web interface on 127.0.0.1 (a free port unless given) with a new token, and opens it.

    host 0.0.0.0 is for a container, whose port is published to the machine running it: the page still opens only
    with this launch's link and only as http://127.0.0.1 or http://localhost (the Host check), so other computers
    can't use it.
    """
    import webbrowser
    sock = bind(host, port)                        # bound before the link is printed
    port = sock.getsockname()[1]
    token = secrets.token_urlsafe(24)
    url = f"http://127.0.0.1:{port}/?token_given={token}"
    print(f"DubEval: {url}\n(only this link works; press Ctrl+C here to stop)", flush=True)
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    run(make_app(token), sock)
