"""Tests for the REST API: starting jobs, progress and results, reports, history, auth (fake pipeline, no network)."""
import time

import pytest
from fastapi.testclient import TestClient

from dubeval import api, history, jobs, pipeline
from dubeval.compare import build_ranking
from dubeval.report import build_report
from fake_perso import SHARE_URL, SHARE_URL_B
from sample_results import make_results


@pytest.fixture
def client(monkeypatch, tmp_path, isolated_output):
    """An API client whose pipeline returns sample results and writes real report files."""
    seen = {}

    def fake_single(link, report=None, cancel_event=None, out_dir=None, report_lang="ko", **kw):
        seen["single"] = dict(link=link, out_dir=out_dir, report_lang=report_lang, **kw)
        r = make_results()
        r["report"] = build_report(r, report_lang)
        r["pipeline"]["report_files"] = pipeline.save_report_files(r, out_dir)
        return r

    def fake_compare(url_a, url_b, out_dir, more_urls=(), report=None, cancel_event=None, report_lang="ko", **kw):
        seen["compare"] = dict(urls=[url_a, url_b, *more_urls], **kw)
        a, b = make_results(acoustic_metrics={"dubbed_duration_sec": 40.0}), make_results()
        comp = build_ranking([a, b], report_lang)
        res = {"A": a, "B": b}
        for d in res:
            res[d]["report"] = comp["reports"][d]
        return {"comparison": comp, "results": res, "files": pipeline.save_comparison_files(comp, res, out_dir)}
    monkeypatch.setattr(pipeline, "run_share_evaluation", fake_single)
    monkeypatch.setattr(pipeline, "run_comparison", fake_compare)
    monkeypatch.delenv("DUBEVAL_API_TOKEN", raising=False)
    c = TestClient(api.app, base_url="http://127.0.0.1")
    c.seen = seen
    return c


def finished(client, url: str, auth: dict = None) -> dict:
    """Polls a job until it leaves the running state."""
    for _ in range(200):
        body = client.get(url, headers=auth or {}).json()
        if body["status"] != "running":
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_health_needs_nothing(client):
    assert client.get("/health").json()["status"] == "ok"


def test_an_evaluation_runs_and_returns_a_summary_and_reports(client):
    resp = client.post("/evaluations", json={"link": SHARE_URL, "lang": "en", "translation_check": False})
    assert resp.status_code == 202
    body = finished(client, resp.json()["url"])
    assert body["status"] == "done" and body["progress"] == 1.0
    result = body["result"]
    assert result["kind"] == "evaluation" and result["overall"]["level"] == "good"
    assert result["problem_intervals"][0]["category"] == "timing_mismatch"
    assert client.seen["single"]["use_translation_judge"] is False and client.seen["single"]["history_mode"] == "api"
    html = client.get(body["reports"]["html"])
    assert html.status_code == 200 and html.headers["content-type"].startswith("text/html")
    assert "DUBBING QA REPORT" in client.get(body["reports"]["text"]).text


def test_a_comparison_returns_the_recommendation(client):
    resp = client.post("/comparisons", json={"links": [SHARE_URL, SHARE_URL_B], "lang": "en"})
    body = finished(client, resp.json()["url"])
    assert body["result"]["recommendation"]["dub"] == "B" and [r["dub"] for r in body["result"]["ranking"]] == ["B", "A"]
    assert "Deliver Dub B." in client.get(body["reports"]["text"]).text


def test_bad_input_is_rejected_before_any_work(client):
    assert client.post("/evaluations", json={"link": "https://example.com/x"}).status_code == 400
    assert "share link" in client.post("/evaluations", json={"link": "https://example.com/x"}).json()["detail"]
    assert client.post("/comparisons", json={"links": [SHARE_URL]}).status_code == 422          # needs 2-8
    assert client.post("/evaluations", json={"link": SHARE_URL, "lang": "fr"}).status_code == 422
    assert client.get("/jobs/0123456789ab").status_code == 404
    assert client.get("/jobs/../../etc").status_code == 404


def test_reports_are_only_served_for_finished_jobs(client):
    release = __import__("threading").Event()
    job = jobs.start_job(lambda report, cancel: release.wait(5) or {}, {"share_url": "x"}, ["evaluate"])
    assert client.get(f"/jobs/{job.id}/report").status_code == 409
    release.set()


def test_history_and_feedback_summaries(client):
    r = make_results()
    r["report"] = build_report(r)
    history.record(r, "single")
    assert client.get("/history").json()["dubs"] == 1
    assert client.get("/history?days=0").status_code == 422
    assert client.get("/feedback").json()["intervals"] == 0


def test_a_token_protects_everything_but_health(client, monkeypatch):
    monkeypatch.setenv("DUBEVAL_API_TOKEN", "s3cret-token")
    assert client.get("/health").status_code == 200
    assert client.get("/history").status_code == 401
    assert client.get("/history", headers={"Authorization": "Bearer wrong"}).status_code == 401
    auth = {"Authorization": "Bearer s3cret-token"}
    assert client.get("/history", headers=auth).status_code == 200
    resp = client.post("/evaluations", json={"link": SHARE_URL}, headers=auth)
    assert resp.status_code == 202 and finished(client, resp.json()["url"], auth)["status"] == "done"


def test_serving_on_the_network_requires_a_token(monkeypatch):
    monkeypatch.delenv("DUBEVAL_API_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="without an API token"):
        api.serve("0.0.0.0", 8000)


def test_without_a_token_only_requests_to_this_machine_are_answered(client):
    # A web page reaching the API through DNS rebinding sends its own host name.
    assert client.get("/history", headers={"host": "evil.example:8000"}).status_code == 403
    assert client.get("/history", headers={"host": "localhost:8000"}).status_code == 200
    assert client.get("/history").headers["x-content-type-options"] == "nosniff"


def test_with_a_token_other_host_names_work(client, monkeypatch):
    monkeypatch.setenv("DUBEVAL_API_TOKEN", "s3cret-token")
    auth = {"Authorization": "Bearer s3cret-token", "host": "qa-server.lan:8000"}
    assert client.get("/history", headers=auth).status_code == 200
