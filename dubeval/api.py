"""REST API: start evaluations and comparisons from other tools, follow their progress, fetch the reports.

    python qa.py serve                      # http://127.0.0.1:8000, interactive docs at /docs

Jobs run in the same background runner as the app (dubeval/jobs.py) and are kept on disk, so a job id stays valid
across restarts. Security: without DUBEVAL_API_TOKEN the server only listens on this machine (127.0.0.1) and
only answers requests addressed to 127.0.0.1 or localhost (so a web page can't reach it through DNS rebinding); with
it, every request except /health needs `Authorization: Bearer <token>`, and the server may listen on the network
(qa.py serve --host 0.0.0.0).
"""
import hmac
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from dubeval import feedback, history, jobs, pipeline
from dubeval.localweb import add_security_headers, bind, is_local_host, run
from dubeval.perso_api import parse_share_url
from dubeval.version import TOOL_VERSION

Lang = Literal["ko", "en", "es", "pt"]
MAX_DUBS = 8


def api_token() -> Optional[str]:
    """The API token from the environment, or None (then the server must stay on this machine)."""
    return (os.getenv("DUBEVAL_API_TOKEN") or "").strip() or None


def require_token(request: Request) -> None:
    """Rejects requests without the right Bearer token when a token is configured, else any not sent to this machine."""
    token = api_token()
    if token is None:
        if not is_local_host(request.headers.get("host")):
            raise HTTPException(status_code=403, detail="Without DUBEVAL_API_TOKEN, call the API at http://127.0.0.1.")
        return
    given = request.headers.get("authorization", "")
    if not (given.lower().startswith("bearer ") and hmac.compare_digest(given[7:].strip(), token)):
        raise HTTPException(status_code=401, detail="Missing or wrong API token (Authorization: Bearer <token>).",
                            headers={"WWW-Authenticate": "Bearer"})


class EvaluationRequest(BaseModel):
    """Evaluate the dub behind one Perso share link."""
    link: str = Field(description="Perso share link (or its seq token)")
    lang: Lang = Field("ko", description="Report language")
    translation_check: bool = Field(True, description="Check the translation with Gemini/Claude when a key is set")
    lipsync: Optional[bool] = Field(None, description="None = automatic (only for lip-synced dubs)")


class ComparisonRequest(BaseModel):
    """Rank 2 to 8 dubs of the same video and recommend one."""
    links: list[str] = Field(min_length=2, max_length=MAX_DUBS, description="Share links of dubs A, B, C, ...")
    lang: Lang = "ko"
    translation_check: bool = True
    lipsync: Optional[bool] = None


app = FastAPI(title="DubEval API", version=TOOL_VERSION,
              description="Evaluate Perso AI dubs from their share links. Jobs run in the background: start one, "
                          "then poll GET /jobs/{id}.")
add_security_headers(app)


def _check_links(links: list[str]) -> list[str]:
    """Validates share links before any work starts (400 with the plain message on a bad one)."""
    try:
        for link in links:
            parse_share_url(link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [link.strip() for link in links]


def _started(job: jobs.Job, request: Request) -> dict:
    """The 202 response for a new job."""
    return {"id": job.id, "status": job.status, "url": str(request.url_for("get_job", job_id=job.id))}


@app.get("/health")
def health() -> dict:
    """Is the server up, and which version is it."""
    return {"status": "ok", "version": TOOL_VERSION}


@app.post("/evaluations", status_code=202, dependencies=[Depends(require_token)])
def start_evaluation(body: EvaluationRequest, request: Request) -> dict:
    """Starts evaluating one dub; poll the returned url for progress and the result."""
    (link,) = _check_links([body.link])
    _, folder = pipeline.new_run_dir()
    job = jobs.start_job(lambda report, cancel: pipeline.run_share_evaluation(
        link, report=report, cancel_event=cancel, report_lang=body.lang, out_dir=folder,
        use_translation_judge=body.translation_check, include_lipsync=body.lipsync, history_mode="api"),
        {"share_url": link, "kind": "evaluation"}, pipeline.share_stages())
    return _started(job, request)


@app.post("/comparisons", status_code=202, dependencies=[Depends(require_token)])
def start_comparison(body: ComparisonRequest, request: Request) -> dict:
    """Starts ranking 2-8 dubs; poll the returned url for progress and the recommendation."""
    links = _check_links(body.links)
    _, folder = pipeline.new_run_dir()
    job = jobs.start_job(lambda report, cancel: pipeline.run_comparison(
        links[0], links[1], folder, more_urls=tuple(links[2:]), report=report, cancel_event=cancel,
        report_lang=body.lang, use_translation_judge=body.translation_check, include_lipsync=body.lipsync),
        {"share_url": links[0], "links": links, "kind": "comparison"}, pipeline.compare_stages(len(links)))
    return _started(job, request)


def _job_or_404(job_id: str) -> jobs.Job:
    """The job, or 404."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No job with this id.")
    return job


def _summary(result: dict) -> dict:
    """The parts of a finished job a caller usually needs (the full report is at /jobs/{id}/report)."""
    if "comparison" in result:
        comp = result["comparison"]
        return {"kind": "comparison", "recommendation": comp["recommendation"], "ranking": comp["ranking"],
                "reasoning": comp["reasoning"], "intervals": comp["intervals"], "notes": comp["notes"]}
    rep = result["report"]
    return {"kind": "evaluation", "project": rep["project"], "overall": rep["overall"],
            "problem_intervals": rep["problem_intervals"], "not_measured": rep["not_measured"],
            "sections": [{"id": s["id"], "title": s["title"],
                          "metrics": [{k: m[k] for k in ("id", "label", "level", "display", "message")}
                                      for m in s["metrics"]]} for s in rep["sections"]]}


@app.get("/jobs/{job_id}", name="get_job", dependencies=[Depends(require_token)])
def get_job(job_id: str, request: Request) -> dict:
    """A job's status and progress; once done, a summary of its result and links to the report files."""
    job = _job_or_404(job_id)
    out = {"id": job.id, "status": job.status, "stage": job.stage, "message": job.message,
           "progress": round(job.overall_fraction, 3), "elapsed_sec": round(job.elapsed_sec, 1), "error": job.error,
           "params": job.params}
    if job.status == "done" and job.result:
        out["result"] = _summary(job.result)
        base = str(request.url_for("get_report", job_id=job.id))
        out["reports"] = {fmt: f"{base}?format={fmt}" for fmt in ("html", "json", "text")}
    return out


def _report_path(result: dict, fmt: str) -> Optional[Path]:
    """The saved report file of a finished job in the given format."""
    files = result.get("files") if "comparison" in result else (result.get("pipeline") or {}).get("report_files")
    path = (files or {}).get(fmt)
    return Path(path) if path else None


@app.get("/jobs/{job_id}/report", name="get_report", dependencies=[Depends(require_token)])
def get_report(job_id: str, format: Literal["html", "json", "text"] = "html"):
    """The report (one dub) or the comparison (several) of a finished job, as html, json or text."""
    job = _job_or_404(job_id)
    if job.status != "done" or not job.result:
        raise HTTPException(status_code=409, detail=f"The job is {job.status}; reports exist once it's done.")
    path = _report_path(job.result, format)
    if path is None or not path.is_file():
        raise HTTPException(status_code=410, detail="The report files are gone (old runs are pruned). Run it again.")
    media = {"html": "text/html", "json": "application/json", "text": "text/plain"}[format]
    return FileResponse(path, media_type=f"{media}; charset=utf-8")


@app.get("/history", dependencies=[Depends(require_token)])
def get_history(days: Optional[int] = Query(None, ge=1, description="Only the last N days")) -> dict:
    """Every past evaluation summarized: totals, language pairs, most frequent problems, weekly trend."""
    return history.summarize(history.load(), days=days)


@app.get("/feedback", dependencies=[Depends(require_token)])
def get_feedback() -> dict:
    """Reviewer votes summarized per check: confirmed problems, false alarms, noisy checks."""
    return feedback.summarize(feedback.load())


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Runs the API with uvicorn. Listening beyond this machine requires DUBEVAL_API_TOKEN."""
    if host not in ("127.0.0.1", "localhost", "::1") and api_token() is None:
        raise SystemExit("Refusing to listen on the network without an API token. Set DUBEVAL_API_TOKEN, or "
                         "keep the default host 127.0.0.1.")
    run(app, bind(host, port), log_level="info")
