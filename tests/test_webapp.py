"""The web interface's server: launch token, uploads, a job from start to review, media, waveforms, votes."""
import os
import sys
import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from dubeval import feedback, library, pipeline, webapp
from dubeval.i18n import TEXT, translate_message
from dubeval.report import build_report
from sample_results import make_results

TOKEN = "launch-token"
BASE = "http://127.0.0.1"


@pytest.fixture
def media(tmp_path):
    (tmp_path / "o.mp4").write_bytes(b"original-bytes")
    (tmp_path / "d.mp4").write_bytes(b"dub-bytes")
    return tmp_path


@pytest.fixture
def client(monkeypatch, tmp_path, media, isolated_output):
    """A signed-in page client whose pipeline returns sample results for the files it's given."""
    seen = {}

    def fake_run(original, dub, report=None, cancel_event=None, report_lang="en", out_dir=None, **options):
        seen.update(original=original, dub=dub, out_dir=out_dir, lang=report_lang, **options)
        r = make_results(segment_alignment={"lines": [
            {"n": 1, "start": 1.0, "end": 3.0, "original_sec": 2.0, "dub_sec": 2.6, "diff_sec": 0.6, "diff_pct": 30.0,
             "start_shift_sec": 0.1, "overrun_sec": 0.0, "short": False, "original": [0], "dub": [0]}]})
        r["pipeline"].update(input_video_path=str(media / "o.mp4"), dubbed_video_path=str(media / "d.mp4"))
        r["pairing"] = {"measured": True, "same_video": True, "picture_match": 1.0, "offset_sec": 0.4,
                        "applied_offset_sec": 0.4, "coverage_pct": 100.0, "parts": [], "missing": []}
        r["report"] = build_report(r, report_lang)
        if out_dir:                                  # as the real run does: the Evaluations list reads these
            pipeline.save_report_files(r, out_dir)
        return r
    monkeypatch.setattr(pipeline, "run_files_evaluation", fake_run)
    monkeypatch.setattr(webapp, "UPLOADS_DIR", tmp_path / "uploads")
    c = TestClient(webapp.make_app(TOKEN), base_url=BASE)
    assert c.get(f"/?token_given={TOKEN}", follow_redirects=False).status_code == 303
    c.seen = seen
    return c


def finished(client, job_id: str) -> dict:
    for _ in range(200):
        body = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_only_the_launch_link_opens_the_page():
    c = TestClient(webapp.make_app(TOKEN), base_url=BASE)
    assert c.get("/").status_code == 401 and c.get("/api/info").status_code == 401
    assert c.get("/?token_given=old").status_code == 401
    resp = c.get(f"/?token_given={TOKEN}", follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert "samesite=strict" in resp.headers["set-cookie"].lower() and "httponly" in resp.headers["set-cookie"].lower()
    assert c.get("/").status_code == 200 and "/static/app.js" in c.get("/").text


def test_other_host_names_are_refused(client):
    """A page on another site that points its own host name at 127.0.0.1 (DNS rebinding) gets nothing."""
    assert client.get("/api/info", headers={"host": "evil.example:8000"}).status_code == 403


def test_errors_follow_the_page_language(client):
    resp = client.get("/api/jobs/0123456789ab", headers={"accept-language": "ko"})
    assert resp.status_code == 404 and resp.json()["detail"] == "이 번호의 작업이 없습니다."


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_info_has_every_page_text_in_the_language(client, lang):
    info = client.get(f"/api/info?lang={lang}").json()
    page_keys = {k for k in TEXT if k.startswith("w.")}
    assert page_keys <= set(info["texts"]) and info["texts"]["stage.prepare"] == TEXT["stage.prepare"][lang]
    assert info["dub_types"] == ["ai_clone", "ai_stock", "human"] and info["judges"] == []


def test_an_upload_is_kept_and_used_by_its_id(client):
    up = client.post("/api/uploads", files={"file": ("../My clip (1).mp4", b"video", "video/mp4")}).json()
    assert up["id"].startswith("upload:")
    path = webapp._upload_path(up["id"])
    assert path.endswith("My_clip_1.mp4") and open(path, "rb").read() == b"video"
    job = client.post("/api/evaluations", json={"original": up["id"], "dub": "C:/videos/dub.mp4"}).json()
    assert finished(client, job["id"])["status"] == "done"
    assert client.seen["original"] == path and client.seen["dub"] == "C:/videos/dub.mp4"


def test_unknown_or_malformed_uploads_are_refused(client):
    for bad in ("upload:0000000000000000", "upload:../../etc"):
        resp = client.post("/api/evaluations", json={"original": bad, "dub": "d.mp4"})
        assert resp.status_code == 400


def test_a_job_runs_and_its_review_has_what_the_timeline_needs(client, media):
    resp = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "dub_type": "human",
                                                 "translation_check": False, "target_lang": "ko", "lang": "ko"})
    assert resp.status_code == 202
    state = finished(client, resp.json()["id"])
    assert state["status"] == "done" and [s["id"] for s in state["stages"]] == ["prepare", "evaluate"]
    assert client.seen["dub_type"] == "human" and client.seen["use_translation_judge"] is False
    assert client.seen["target_lang"] == "ko" and client.seen["out_dir"]
    data = client.get(f"/api/jobs/{resp.json()['id']}/report?lang=pt").json()
    assert data["report"]["lang"] == "pt" and data["offset_sec"] == 0.4 and data["parts"] is None
    assert data["lines"][0]["n"] == 1 and {"start", "end", "text"} == set(data["original_segments"][0])
    assert client.get(f"/api/jobs/{resp.json()['id']}/media/dub").content == b"dub-bytes"


def test_a_bad_dub_type_is_refused_before_anything_runs(client):
    assert client.post("/api/evaluations", json={"original": "o", "dub": "d", "dub_type": "robot"}).status_code == 400


def test_media_are_only_the_jobs_own_files(client):
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    assert client.get(f"/api/jobs/{job_id}/media/original").content == b"original-bytes"
    assert client.get(f"/api/jobs/{job_id}/media/secret").status_code == 404
    assert client.get("/api/jobs/..%2F..%2Fx/media/dub").status_code == 404
    assert client.get("/api/jobs/0123456789ab/media/dub").status_code == 404


def test_waveforms_are_computed_once_and_the_dub_is_moved_by_the_shift(client, monkeypatch):
    calls = []
    monkeypatch.setattr(webapp, "peaks", lambda path, offset=0.0, parts=None, length=None:
                        calls.append((path.endswith("d.mp4"), offset, length)) or [0.5, 1.0])
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    first = client.get(f"/api/jobs/{job_id}/peaks/dub").json()
    assert first == {"per_sec": webapp.PEAKS_PER_SEC, "peaks": [0.5, 1.0]}
    assert client.get(f"/api/jobs/{job_id}/peaks/dub").json() == first and len(calls) == 1
    assert calls[0][:2] == (True, 0.4)


def test_peaks_are_normalized_and_follow_the_shift(monkeypatch):
    sr = 16000
    y = np.zeros(sr * 2, dtype=np.float32)
    y[sr:sr + 100] = 0.5                                        # one click at 1.0 s
    monkeypatch.setattr("dubeval.evaluate.extract_audio", lambda path, out, *a, **k: out)
    monkeypatch.setattr("dubeval.evaluate.load_audio", lambda path: y)
    p = webapp.peaks("x.mp4", per_sec=10)
    assert len(p) == 20 and p[10] == 1.0 and max(p[:10]) == 0.0
    shifted = webapp.peaks("x.mp4", offset_sec=0.5, length_sec=2.0, per_sec=10)
    assert len(shifted) == 20 and shifted[5] == 1.0              # the dub's 1.0 s is the original's 0.5 s


def test_votes_are_recorded_and_shown_on_the_review(client):
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    intervals = client.get(f"/api/jobs/{job_id}/report").json()["report"]["problem_intervals"]
    assert intervals, "the sample results should have problem intervals"
    assert client.post(f"/api/jobs/{job_id}/votes", json={"index": 0, "vote": "false_alarm"}).status_code == 200
    assert feedback.load()[-1]["vote"] == "false_alarm" and feedback.load()[-1]["reviewer"] == "web"
    assert client.get(f"/api/jobs/{job_id}/report").json()["votes"] == {"0": "false_alarm"}
    assert client.post(f"/api/jobs/{job_id}/votes", json={"index": 999, "vote": "real"}).status_code == 404
    assert client.post(f"/api/jobs/{job_id}/votes", json={"index": 0, "vote": "maybe"}).status_code == 422


def test_a_running_job_can_be_stopped(client, monkeypatch):
    from dubeval.jobs import Cancelled

    def slow(original, dub, report=None, cancel_event=None, **kw):
        while not cancel_event.is_set():
            time.sleep(0.01)
        raise Cancelled()
    monkeypatch.setattr(pipeline, "run_files_evaluation", slow)
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    assert client.get(f"/api/jobs/{job_id}/report").status_code == 409
    client.post(f"/api/jobs/{job_id}/cancel")
    assert finished(client, job_id)["status"] == "cancelled"


@pytest.fixture
def compare_client(client, monkeypatch, media):
    """The page client whose comparison pipeline ranks sample results (dub A too long, dub B fine)."""
    from dubeval.compare import build_ranking

    def fake_compare(original, dubs, out_dir, report_lang="en", report=None, cancel_event=None, **options):
        client.seen.update(original=original, dubs=dubs, out_dir=out_dir, **options)
        res = {}
        for letter, extra in zip("ABC", [{"dubbed_duration_sec": 40.0}, {}, {}][:len(dubs)]):
            r = make_results(acoustic_metrics=extra)
            r["pipeline"].update(input_video_path=str(media / "o.mp4"), dubbed_video_path=str(media / "d.mp4"))
            res[letter] = r
        comp = build_ranking(list(res.values()), report_lang, run_seconds=3.0)
        for d in comp["dubs"]:
            res[d]["report"] = comp["reports"][d]
        return {"comparison": comp, "results": res, "files": {}}
    monkeypatch.setattr(pipeline, "run_files_comparison", fake_compare)
    return client


def test_several_dubs_start_a_comparison_with_a_stage_per_dub(compare_client):
    job = compare_client.post("/api/evaluations", json={
        "original": "o.mp4", "dub": "a.mp4", "more_dubs": ["b.mp4", "c.mp4"], "dub_subtitles": "a.srt",
        "dub_type": "ai_clone"}).json()
    state = finished(compare_client, job["id"])
    assert state["status"] == "done" and state["kind"] == "comparison"
    assert [s["id"] for s in state["stages"]] == ["dub_a", "dub_b", "dub_c", "compare"]
    assert compare_client.seen["dubs"] == ["a.mp4", "b.mp4", "c.mp4"] and compare_client.seen["dub_type"] == "ai_clone"
    assert "dub_subtitles" not in compare_client.seen                     # subtitles belong to one dub


def test_the_comparison_comes_in_the_page_language_without_the_full_reports(compare_client):
    job_id = compare_client.post("/api/evaluations", json={"original": "o", "dub": "a", "more_dubs": ["b"]}).json()["id"]
    finished(compare_client, job_id)
    comp = compare_client.get(f"/api/jobs/{job_id}/comparison?lang=es").json()
    assert comp["lang"] == "es" and comp["recommendation"]["dub"] == "B" and "reports" not in comp
    assert [r["dub"] for r in comp["ranking"]] == ["B", "A"] and comp["labels"]["dub_A"]


def test_each_dub_of_a_comparison_has_its_own_review(compare_client):
    job_id = compare_client.post("/api/evaluations", json={"original": "o", "dub": "a", "more_dubs": ["b"]}).json()["id"]
    finished(compare_client, job_id)
    a = compare_client.get(f"/api/jobs/{job_id}/report?dub=A").json()["report"]
    b = compare_client.get(f"/api/jobs/{job_id}/report?dub=B").json()["report"]
    assert a["overall"]["level"] == "poor" and b["overall"]["level"] == "good"
    assert compare_client.get(f"/api/jobs/{job_id}/report?dub=Z").status_code == 404
    assert compare_client.get(f"/api/jobs/{job_id}/media/dub?dub=B").content == b"dub-bytes"
    assert compare_client.post(f"/api/jobs/{job_id}/votes?dub=A", json={"index": 0, "vote": "real"}).status_code == 200
    assert compare_client.get(f"/api/jobs/{job_id}/report?dub=A").json()["votes"] == {"0": "real"}


def test_a_single_evaluation_has_no_comparison_and_too_many_dubs_are_refused(client):
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    assert client.get(f"/api/jobs/{job_id}/comparison").status_code == 404
    resp = client.post("/api/evaluations", json={"original": "o", "dub": "a", "more_dubs": ["x"] * 8})
    assert resp.status_code == 400 and "8" in resp.json()["detail"]


def test_files_comparison_evaluates_every_dub_against_one_original(monkeypatch, tmp_path):
    seen, stages = [], []

    def fake_evaluate(original, dub, notify, check_cancel, **options):
        seen.append((original, dub, options.get("dub_type")))
        notify("evaluate", "Measuring...", 0.5)
        return make_results(acoustic_metrics={"dubbed_duration_sec": 40.0} if dub == "a.mp4" else {})
    monkeypatch.setattr(pipeline, "evaluate_files", fake_evaluate)
    out = pipeline.run_files_comparison("o.mp4", ["a.mp4", "b.mp4"], str(tmp_path), report_lang="en",
                                        report=lambda p: stages.append(p.stage), dub_type="human")
    assert seen == [("o.mp4", "a.mp4", "human"), ("o.mp4", "b.mp4", "human")]
    assert out["comparison"]["recommendation"]["dub"] == "B" and set(out["results"]) == {"A", "B"}
    assert {"dub_a", "dub_b", "compare"} <= set(stages) and (tmp_path / "comparison.html").is_file()
    with pytest.raises(ValueError, match="between 2 and 8"):
        pipeline.run_files_comparison("o.mp4", ["a.mp4"], str(tmp_path))


def test_the_page_files_are_revalidated_on_every_load(client):
    """After an update the browser must not keep running the old script."""
    assert client.get("/static/app.js").headers["cache-control"] == "no-cache"
    assert client.get("/").headers["cache-control"] == "no-cache"


def test_each_dub_of_a_comparison_has_its_own_kind_and_language(compare_client):
    job = compare_client.post("/api/evaluations", json={
        "original": "o.mp4", "dub": "ko.mp4", "more_dubs": ["uz.mp4"], "dub_type": "ai_stock",
        "dub_options": [{"dub_type": "human", "target_lang": " ko "},
                        {"dub_type": "ai_clone", "target_lang": "uz", "subtitles": "C:/subs/uz.srt"}]}).json()
    finished(compare_client, job["id"])
    assert compare_client.seen["per_dub"] == [{"dub_type": "human", "target_lang": "ko", "dub_subtitles": None},
                                              {"dub_type": "ai_clone", "target_lang": "uz",
                                               "dub_subtitles": "C:/subs/uz.srt"}]   # each dub's own subtitle file
    assert compare_client.seen["dub_type"] == "ai_stock"                  # the shared fallback is still passed


def test_a_single_dub_takes_its_settings_from_its_card(client):
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "dub_type": "ai_stock",
                                                "dub_options": [{"dub_type": "human", "target_lang": "uz"}]}).json()
    finished(client, job["id"])
    assert client.seen["dub_type"] == "human" and client.seen["target_lang"] == "uz"


def test_bad_per_dub_settings_are_refused(client):
    bad_type = {"original": "o", "dub": "a", "more_dubs": ["b"], "dub_options": [{}, {"dub_type": "robot"}]}
    too_many = {"original": "o", "dub": "a", "dub_options": [{}, {}]}
    assert client.post("/api/evaluations", json=bad_type).status_code == 400
    resp = client.post("/api/evaluations", json=too_many, headers={"accept-language": "es"})
    assert resp.status_code == 400 and resp.json()["detail"].startswith("Hay más ajustes")


def test_files_comparison_applies_each_dubs_own_settings(monkeypatch, tmp_path):
    seen = []

    def fake_evaluate(original, dub, notify, check_cancel, **options):
        seen.append((dub, options.get("dub_type"), options.get("target_lang"), options.get("source_lang")))
        return make_results()
    monkeypatch.setattr(pipeline, "evaluate_files", fake_evaluate)
    pipeline.run_files_comparison("o.mp4", ["a.mp4", "b.mp4", "c.mp4"], str(tmp_path), source_lang="en",
                                  dub_type="ai_stock", per_dub=[{"dub_type": "human", "target_lang": None},
                                                                {"target_lang": "uz"}])
    assert seen == [("a.mp4", "human", None, "en"), ("b.mp4", "ai_stock", "uz", "en"), ("c.mp4", "ai_stock", None, "en")]
    with pytest.raises(ValueError, match="more dub settings"):
        pipeline.run_files_comparison("o.mp4", ["a.mp4", "b.mp4"], str(tmp_path), per_dub=[{}, {}, {}])


def test_history_summarizes_past_runs_and_reopens_only_known_reports(client, monkeypatch, tmp_path):
    from dubeval import history
    monkeypatch.setattr(webapp, "DATA_DIR", tmp_path)
    run = tmp_path / "output" / "runs" / "r1"
    run.mkdir(parents=True)
    (run / "report.html").write_text("<p>old report</p>", encoding="utf-8")
    (tmp_path / "secret.html").write_text("not a report", encoding="utf-8")
    r = make_results()
    r["report"] = build_report(r, "en")
    r["pipeline"]["report_files"] = {"html": str(run / "report.html")}
    history.record(r, "web")
    feedback.vote(r["report"]["project"], r["report"]["problem_intervals"][0], "false_alarm")

    data = client.get("/api/history?days=30").json()
    assert data["history"]["dubs"] == 1 and data["history"]["recent"][0]["mode"] == "web"
    assert data["history"]["recent"][0]["report"] == "output/runs/r1/report.html"
    assert data["feedback"]["intervals"] == 1 and data["feedback"]["false_alarm"] == 1
    saved = client.get("/api/reports?path=output/runs/r1/report.html")
    assert saved.text == "<p>old report</p>"
    assert "sandbox" in saved.headers["content-security-policy"]       # a saved report can never run a script
    for bad in ("secret.html", "../secret.html", "output/runs/r1/../../secret.html"):
        assert client.get(f"/api/reports?path={bad}").status_code == 404


def test_reports_outside_the_data_folder_get_no_link(client, monkeypatch, tmp_path):
    from dubeval import history
    monkeypatch.setattr(webapp, "DATA_DIR", tmp_path / "data")
    elsewhere = tmp_path / "cli-output" / "report.html"
    elsewhere.parent.mkdir()
    elsewhere.write_text("x", encoding="utf-8")
    r = make_results()
    r["report"] = build_report(r, "en")
    r["pipeline"]["report_files"] = {"html": str(elsewhere)}
    history.record(r, "single")
    assert client.get("/api/history").json()["history"]["recent"][0]["report"] is None


def test_the_history_page_texts_come_with_the_page(client):
    texts = client.get("/api/info?lang=ko").json()["texts"]
    assert texts["h.title"] and texts["f.status.noisy"] and texts["mode.web"] == "웹 화면" and texts["r.m.clarity"]


def test_perso_share_links_need_no_original_and_run_the_share_pipeline(client, monkeypatch, media):
    from fake_perso import SHARE_URL, SHARE_URL_B
    seen = {}

    def fake_share(link, report=None, cancel_event=None, out_dir=None, report_lang="en", **kw):
        seen["single"] = dict(link=link, **kw)
        r = make_results()
        r["pipeline"].update(input_video_path=str(media / "o.mp4"), dubbed_video_path=str(media / "d.mp4"))
        r["report"] = build_report(r, report_lang)
        return r

    def fake_compare(a, b, out_dir, more_urls=(), report=None, cancel_event=None, report_lang="en", **kw):
        seen["compare"] = dict(links=[a, b, *more_urls], **kw)
        return {"comparison": {"dubs": []}, "results": {}, "files": {}}
    monkeypatch.setattr(pipeline, "run_share_evaluation", fake_share)
    monkeypatch.setattr(pipeline, "run_comparison", fake_compare)

    job = client.post("/api/evaluations", json={"dub": SHARE_URL}).json()
    state = finished(client, job["id"])
    assert state["status"] == "done" and [s["id"] for s in state["stages"]] == ["fetch", "download", "evaluate"]
    assert seen["single"]["link"] == SHARE_URL and seen["single"]["original"] is None
    assert seen["single"]["include_lipsync"] is None                  # automatic: lip-synced dubs only
    assert client.get(f"/api/jobs/{job['id']}/report").json()["report"]["overall"]["level"]

    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": SHARE_URL, "more_dubs": [SHARE_URL_B],
                                                "lipsync": True}).json()
    finished(client, job["id"])
    assert seen["compare"]["links"] == [SHARE_URL, SHARE_URL_B] and seen["compare"]["original"] == "o.mp4"
    assert seen["compare"]["include_lipsync"] is True


def test_share_links_and_files_dont_mix_and_files_need_an_original(client):
    from fake_perso import SHARE_URL
    mixed = client.post("/api/evaluations", json={"dub": SHARE_URL, "more_dubs": ["b.mp4"]})
    assert mixed.status_code == 400 and "not a mix" in mixed.json()["detail"]
    bad = client.post("/api/evaluations", json={"dub": "https://perso.ai/en/share/video-translator"})
    assert bad.status_code == 400
    assert client.post("/api/evaluations", json={"dub": "d.mp4"}).json()["detail"].startswith("Choose the original")


def test_the_web_command_passes_port_host_and_browser_choice(monkeypatch):
    from dubeval import cli
    seen = {}
    monkeypatch.setattr(webapp, "serve", lambda port, open_browser=True, host="127.0.0.1":
                        seen.update(port=port, open_browser=open_browser, host=host))
    assert cli.main(["web", "--port", "8501", "--host", "0.0.0.0", "--no-browser"]) == 0
    assert seen == {"port": 8501, "open_browser": False, "host": "0.0.0.0"}


def test_the_server_exits_when_its_parent_ends():
    waited, exited = [], []
    thread = webapp.exit_with_parent(exit_now=exited.append, wait=waited.append)
    thread.join(timeout=2)
    assert waited == [os.getppid()] and exited == [0]


def test_waiting_for_a_process_that_has_ended_returns():
    import subprocess
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    thread = threading.Thread(target=webapp._wait_for_exit, args=(child.pid,), daemon=True)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_the_parent_watch_never_reads_stdin(monkeypatch):
    # A thread blocked on the stdin pipe froze scipy's first import on Windows (the evaluation hung).
    class Untouchable:
        def read(self, *_):
            raise AssertionError("stdin was read")
    monkeypatch.setattr(sys, "stdin", Untouchable())
    exited = []
    webapp.exit_with_parent(parent_pid=1, exit_now=exited.append, wait=lambda pid: None).join(timeout=2)
    assert exited == [0]


def test_the_web_command_can_watch_its_parent(monkeypatch):
    from dubeval import cli
    calls = []
    monkeypatch.setattr(webapp, "exit_with_parent", lambda: calls.append("watch"))
    monkeypatch.setattr(webapp, "serve", lambda *a, **k: calls.append("serve"))
    assert cli.main(["web", "--no-browser", "--exit-with-parent"]) == 0 and calls == ["watch", "serve"]
    calls.clear()
    assert cli.main(["web", "--no-browser"]) == 0 and calls == ["serve"]


def test_downloads_are_listed_installed_and_removed_through_the_page(client, monkeypatch):
    from dubeval import packs
    installed = set()
    monkeypatch.setattr(packs, "state", lambda pid: "installed" if pid in installed else "absent")
    monkeypatch.setattr(packs, "available", lambda pid: pid != "gpu")
    monkeypatch.setattr(packs, "installed_size_mb", lambda pid: 10 if pid in installed else None)

    def fake_install(pid, progress, stop=lambda: False, session=None):
        progress("Downloading...", 0.5)
        installed.add(pid)
        return {"id": pid}
    monkeypatch.setattr(packs, "install", fake_install)
    monkeypatch.setattr(packs, "remove", lambda pid: installed.discard(pid))

    listing = client.get("/api/packs").json()
    assert {p["id"]: p["available"] for p in listing["packs"]} == {"meaning": True, "gpu": False, "large_model": True,
                                                                   "local_judge": True}
    assert client.post("/api/packs/gpu/install").status_code == 400
    assert client.post("/api/packs/nope/install").status_code == 404
    job = client.post("/api/packs/large_model/install").json()
    assert finished(client, job["id"])["status"] == "done" and "large_model" in installed
    assert client.get("/api/info").json()["large_model"] is True
    assert client.delete("/api/packs/large_model").json()["state"] == "absent"


def test_the_large_speech_model_is_used_only_when_installed(client, monkeypatch):
    from dubeval import packs
    monkeypatch.setattr(packs, "state", lambda pid: "absent")
    resp = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "speech_model": "large"},
                       headers={"accept-language": "ko"})
    assert resp.status_code == 400 and "다운로드" in resp.json()["detail"]
    monkeypatch.setattr(packs, "state", lambda pid: "installed")
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "speech_model": "large"}).json()
    finished(client, job["id"])
    assert client.seen["whisper_model_name"] == packs.LARGE_MODEL


def test_a_download_can_be_stopped(client, monkeypatch):
    import threading
    from dubeval import packs
    go = threading.Event()

    def slow(pid, progress, stop=lambda: False, session=None):
        while not stop():
            go.set()
            threading.Event().wait(0.01)
        raise packs.Stopped()
    monkeypatch.setattr(packs, "install", slow)
    monkeypatch.setattr(packs, "available", lambda pid: True)
    job = client.post("/api/packs/meaning/install").json()
    go.wait(2)
    assert client.post("/api/packs/meaning/install").json()["id"] == job["id"]        # one download per pack
    assert client.delete("/api/packs/meaning").status_code == 409
    client.post(f"/api/jobs/{job['id']}/cancel")
    assert finished(client, job["id"])["status"] == "cancelled"


def test_settings_save_and_remove_keys_without_ever_sending_them_back(client):
    key = "AIza-test-" + "k" * 30
    view = client.get("/api/settings").json()
    assert view["keys"]["gemini"]["set"] is False and view["judge"]["order"] == ["claude", "gemini", "openai", "ollama"]
    resp = client.put("/api/settings/keys/gemini", json={"key": key})
    assert resp.status_code == 200 and key not in resp.text
    assert resp.json()["keys"]["gemini"] == {"set": True, "saved_here": True}
    assert resp.json()["judge"]["active"] == "gemini" and "gemini" in resp.json()["judge"]["available"]
    assert key not in client.get("/api/settings").text and key not in client.get("/api/info").text
    gone = client.delete("/api/settings/keys/gemini").json()
    assert gone["keys"]["gemini"]["set"] is False and gone["judge"]["active"] is None


@pytest.mark.parametrize("body", [{"key": "a b"}, {"key": 12345}, {"nokey": True}, "not json", {"key": "x" * 5000}])
def test_a_bad_key_request_never_echoes_what_was_sent(client, body):
    payload = {"content": body} if isinstance(body, str) else {"json": body}
    resp = client.put("/api/settings/keys/gemini", **payload)
    assert resp.status_code == 400 and "x" * 50 not in resp.text and "a b" not in resp.text
    assert client.put("/api/settings/keys/mistral", json={"key": "k" * 30}).status_code == 404


def test_the_models_tab_lists_built_in_and_downloadable_models_by_group(client):
    data = client.get("/api/models").json()
    groups = {g["id"]: [r["id"] for r in g["rows"]] for g in data["groups"]}
    assert groups == {"speech": ["whisper_base", "large_model"], "meaning": ["meaning", "local_judge"],
                      "voice": ["speaker", "dnsmos", "face"], "speed": ["gpu"], "base": ["engine"]}
    rows = {r["id"]: r for g in data["groups"] for r in g["rows"]}
    assert rows["dnsmos"]["kind"] == "builtin" and rows["dnsmos"]["state"] == "builtin" and rows["dnsmos"]["bytes"] > 0
    assert rows["large_model"]["kind"] == "pack" and rows["large_model"]["download_mb"] > 1000 and "job" in rows["large_model"]
    assert data["ready"] >= 3 and data["bytes"] > 0


def test_settings_say_where_the_data_is_and_can_open_it(client, monkeypatch):
    opened = []
    monkeypatch.setattr(webapp.os, "startfile", opened.append, raising=False)
    monkeypatch.setattr(webapp.subprocess if hasattr(webapp, "subprocess") else __import__("subprocess"), "Popen",
                        lambda args: opened.append(args[-1]))
    view = client.get("/api/settings").json()
    assert view["data_dir"] and view["version"]
    assert client.post("/api/settings/open-data").json() == {"opened": True} and opened


def test_the_report_says_how_to_fix_rows_that_need_a_key_or_a_model(client, monkeypatch):
    from dubeval import packs
    from dubeval.translation_judge import not_measured
    monkeypatch.setattr(packs, "state", lambda pid: "absent")
    monkeypatch.setattr(packs, "available", lambda pid: True)
    r = make_results(translation_judge=not_measured("r.judge.no_key"),
                     meaning_screen={"measured": False, "reason_key": "r.screen.not_installed", "lines": []})
    assert webapp._fixes(r) == {"translation_check": "keys", "meaning_screen": "models"}
    monkeypatch.setattr(packs, "state", lambda pid: "installed")
    r2 = make_results(translation_judge=not_measured("r.judge.busy", model="Gemini"))
    assert webapp._fixes(r2) == {}


def test_every_page_and_answer_carries_security_headers(client):
    for path in ("/", "/static/app.js", "/api/info"):
        h = client.get(path).headers
        assert "script-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h[
            "content-security-policy"]
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "no-referrer"


def test_the_page_has_no_inline_script_the_policy_would_block():
    page = (webapp.WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in page and " on" + "click=" not in page and "style=" not in page


def test_an_upload_larger_than_the_limit_is_refused_and_removed(client, monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, "MAX_MEDIA_BYTES", 4)
    resp = client.post("/api/uploads", files={"file": ("big.mp4", b"12345", "video/mp4")})
    assert resp.status_code == 413 and "larger than" in resp.json()["detail"]
    assert not list((tmp_path / "uploads").glob("*"))


def test_the_launch_link_is_printed_only_once_the_port_is_ours(monkeypatch, capsys):
    from dubeval import localweb
    served = {}
    monkeypatch.setattr(webapp, "run", lambda app, sock: served.update(port=sock.getsockname()[1], sock=sock))
    webapp.serve(open_browser=False)
    try:
        printed = capsys.readouterr().out
        assert f"http://127.0.0.1:{served['port']}/?token_given=" in printed
        with pytest.raises(OSError):                       # nobody else can take the port meanwhile
            localweb.bind("127.0.0.1", served["port"]).close()
    finally:
        served["sock"].close()


def test_a_job_that_isnt_an_evaluation_has_no_report(client):
    from dubeval import jobs
    job = jobs.start_job(lambda report, cancel: True, {"kind": "pack", "pack": "meaning"}, ["pack"])
    for _ in range(200):
        if jobs.get_job(job.id).status != "running":
            break
        time.sleep(0.02)
    assert client.get(f"/api/jobs/{job.id}/report").status_code == 409


def test_export_gives_one_file_or_a_zip_in_the_pages_language(client):
    import io
    import zipfile
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    one = client.get(f"/api/jobs/{job_id}/export?kinds=html&lang=ko")
    assert one.status_code == 200 and one.headers["content-type"].startswith("text/html")
    assert "attachment" in one.headers["content-disposition"] and "DubEval.html" in one.headers["content-disposition"]
    assert '<html lang="ko"' in one.text or "lang=ko" in one.text
    both = client.get(f"/api/jobs/{job_id}/export?kinds=html,xlsx,text,json&lang=en")
    names = zipfile.ZipFile(io.BytesIO(both.content)).namelist()
    assert names == ["report.html", "problems.xlsx", "report.txt", "report.json"]
    rows = sheet_rows(zipfile.ZipFile(io.BytesIO(both.content)).read("problems.xlsx"))
    assert rows[0] == ["Start", "End", "Check", "Level", "Description"] and len(rows) > 1
    assert client.get(f"/api/jobs/{job_id}/export?kinds=exe").status_code == 400


def test_a_comparison_exports_the_comparison_and_every_dubs_report(compare_client):
    import io
    import zipfile
    job_id = compare_client.post("/api/evaluations", json={"original": "o", "dub": "a", "more_dubs": ["b"]}).json()["id"]
    finished(compare_client, job_id)
    z = zipfile.ZipFile(io.BytesIO(compare_client.get(f"/api/jobs/{job_id}/export?kinds=html,xlsx").content))
    assert z.namelist() == ["comparison.html", "report_A.html", "report_B.html", "problems.xlsx"]
    rows = sheet_rows(z.read("problems.xlsx"))
    assert rows[0][:3] == ["Dub", "Start", "End"] and {r[0] for r in rows[1:]} <= {"A", "B"}


def sheet_rows(xlsx_bytes: bytes) -> list[list[str]]:
    """The text of every row of an exported sheet (enough to check what Excel will show)."""
    import io
    import re
    import zipfile
    xml = zipfile.ZipFile(io.BytesIO(xlsx_bytes)).read("xl/worksheets/sheet1.xml").decode("utf-8")
    cell = re.compile(r"<t xml:space=\"preserve\">(.*?)</t>|<v>(.*?)</v>")
    return [["".join(m) for m in cell.findall(row)] for row in re.findall(r"<row [^>]*>(.*?)</row>", xml)]


def test_the_problem_list_also_has_checks_about_the_whole_dub():
    # A dub whose only issues are Check rows without a time (loudness, language) must not export an empty list.
    rep = {"sections": [{"metrics": [{"label": "Loudness match", "level": "check", "message": "Louder than the original."},
                                     {"label": "Length", "level": "good", "message": "Fine."}]}],
           "things_to_check": [{"start": None, "end": None, "severity": "check", "message": "No speech in the dub."}],
           "problem_intervals": []}
    rows = webapp.problem_rows(rep, "en")
    assert rows == [[None, None, "Loudness match", "Check", "Louder than the original."],
                    [None, None, "General", "Check", "No speech in the dub."]]


def test_the_page_gets_speech_languages_release_notes_and_the_repository(client):
    info = client.get("/api/info?lang=ko").json()
    assert info["speech_languages"]["uz"] == "Uzbek" and len(info["speech_languages"]) > 90
    assert info["whats_new"] and info["repository"].startswith("https://github.com/")


def test_export_file_names_keep_the_title_minus_what_windows_forbids():
    assert webapp._export_name("Learn English: Weather (Subtitles)_ko") == "Learn English Weather (Subtitles)_ko"
    assert webapp._export_name("날씨 이야기") == "날씨 이야기"
    assert webapp._export_name(r'a/b\c?d*"e') == "a b c d e"
    assert webapp._export_name(None) == webapp._export_name("...") == "DubEval"


def test_a_past_run_opens_in_the_review_even_after_its_job_is_gone(client, monkeypatch, tmp_path):
    from dubeval import history
    monkeypatch.setattr(webapp, "DATA_DIR", tmp_path)
    run = tmp_path / "output" / "runs" / "r1"
    r = make_results()
    r["report"] = build_report(r, "en")
    r["pipeline"]["report_files"] = pipeline.save_report_files(r, run)
    history.record(r, "web")
    first = client.post("/api/history/open?path=output/runs/r1/report.html").json()
    assert first["kind"] == "files" and first["dub"] is None
    again = client.post("/api/history/open?path=output/runs/r1/report.html").json()
    assert again["id"] == first["id"]                                   # the same job, not a new copy each time
    rep = client.get(f"/api/jobs/{first['id']}/report?lang=ko").json()["report"]
    assert rep["lang"] == "ko" and rep["overall"]["level"] == r["report"]["overall"]["level"]
    assert client.post("/api/history/open?path=secret.html").status_code == 404


def test_a_past_comparison_opens_on_the_chosen_dubs_tab(client, monkeypatch, tmp_path):
    from dubeval import history
    from dubeval.compare import build_ranking
    monkeypatch.setattr(webapp, "DATA_DIR", tmp_path)
    run = tmp_path / "output" / "runs" / "c1"
    res = {"A": make_results(), "B": make_results()}
    comp = build_ranking([res["A"], res["B"]], "en")
    for d in comp["dubs"]:
        res[d]["report"] = comp["reports"][d]
    pipeline.save_comparison_files(comp, res, run)
    for d in comp["dubs"]:
        history.record(res[d], "compare")                                 # each dub links to its own report
    past = client.post("/api/history/open?path=output/runs/c1/report_B.html").json()
    assert past["kind"] == "comparison" and past["dub"] == "B"
    assert client.get(f"/api/jobs/{past['id']}/comparison").json()["dubs"] == ["A", "B"]
    assert client.get(f"/api/jobs/{past['id']}/report?dub=B").status_code == 200


def test_a_share_link_needs_no_original_even_when_the_page_sends_none(client, monkeypatch):
    # The start page sends original: null for a Perso share link (it brings its own original).
    seen = {}
    monkeypatch.setattr(pipeline, "run_share_evaluation", lambda link, **kw: seen.setdefault("link", link) or {})
    from fake_perso import SHARE_URL
    resp = client.post("/api/evaluations", json={"original": None, "dub": SHARE_URL})
    assert resp.status_code == 202


def test_the_start_page_previews_a_source_and_explains_one_it_cant_read(client, monkeypatch):
    from dubeval import preview
    monkeypatch.setattr(preview, "preview", lambda source: {"kind": "perso", "title": "input", "source_lang": "en",
                                                            "target_lang": "uz", "thumbnail": None})
    assert client.get("/api/preview?source=https://perso.ai/x").json()["target_lang"] == "uz"
    monkeypatch.setattr(preview, "preview", lambda source: (_ for _ in ()).throw(ValueError(preview.NO_SUCH_FILE)))
    resp = client.get("/api/preview?source=C:/nothing.mp4", headers={"Accept-Language": "ko"})
    assert resp.status_code == 400 and "영상이 없습니다" in resp.json()["detail"]


def test_the_start_page_can_name_the_translation_checker(client):
    client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "judge": "gemini"})
    assert client.seen["use_translation_judge"] == "gemini"
    client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "judge": "off"})
    assert client.seen["use_translation_judge"] is False
    client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"})
    assert client.seen["use_translation_judge"] is True                     # auto: the first one set up
    assert client.post("/api/evaluations", json={"original": "o", "dub": "d", "judge": "bard"}).status_code == 422


def test_a_share_link_takes_subtitle_files_and_its_dub_kind(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(pipeline, "run_share_evaluation", lambda link, **kw: seen.update(kw) or {})
    from fake_perso import SHARE_URL
    client.post("/api/evaluations", json={"dub": SHARE_URL, "dub_subtitles": "C:/subs/uz.srt",
                                          "dub_options": [{"dub_type": "ai_clone"}], "judge": "claude"})
    for _ in range(100):
        if seen:
            break
        time.sleep(0.02)
    assert seen["dub_subtitles"] == "C:/subs/uz.srt" and seen["dub_type"] == "ai_clone"
    assert seen["use_translation_judge"] == "claude"


def test_a_result_can_be_renamed_and_history_follows(client, monkeypatch, tmp_path):
    from dubeval import history
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    resp = client.put(f"/api/jobs/{job_id}/title", json={"title": "  My  clip  "})
    assert resp.json() == {"title": "My clip"}
    assert client.get(f"/api/jobs/{job_id}/report").json()["report"]["project"]["title"] == "My clip"
    assert client.put(f"/api/jobs/{job_id}/title", json={"title": "   "}).status_code == 400


def test_the_review_shows_what_the_subtitles_say_for_each_line(client, monkeypatch):
    job_id = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    finished(client, job_id)
    from dubeval import jobs
    r = jobs.get_job(job_id).result
    line = r["segment_alignment"]["lines"][0]
    r["subtitles"] = {"original": None, "dub": [{"start": line["start"], "end": line["end"], "text": "Salom hammaga"}]}
    lines = client.get(f"/api/jobs/{job_id}/report").json()["lines"]
    assert lines[0]["dub_script"] == "Salom hammaga" and "original_script" not in lines[0]


# ----- the Evaluations list (home screen) and drafts -----

JPEG = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ=="


def test_a_draft_follows_its_evaluation_and_gives_way_to_its_card(client):
    draft = client.post("/api/drafts", json={"name": "Weather clip", "thumbnail": JPEG,
                                             "form": {"original": {"typed": "o.mp4"}, "dubs": [{"typed": "d.mp4"}]}}).json()
    listed = client.get("/api/evaluations").json()
    assert [d["state"] for d in listed["drafts"]] == ["draft"] and listed["evaluations"] == []
    assert client.get(f"/api/drafts/{draft['id']}").json()["form"]["dubs"] == [{"typed": "d.mp4"}]
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "draft_id": draft["id"]}).json()
    assert finished(client, job["id"])["draft_id"] == draft["id"]
    listed = client.get("/api/evaluations").json()
    assert listed["drafts"] == []                                   # done: the draft became the evaluation's card
    [card] = listed["evaluations"]
    assert card["kind"] == "single" and card["verdict"] and "inputs" not in card
    # The draft's picture became the evaluation's.
    assert client.get(f"/api/evaluations/{card['id']}/thumb").status_code == 200


def test_a_failed_evaluation_keeps_its_draft_to_try_again(client, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("Couldn't read the dub.")
    monkeypatch.setattr(pipeline, "run_files_evaluation", broken)
    draft = client.post("/api/drafts", json={"form": {"dubs": [{"typed": "d.mp4"}]}}).json()
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "draft_id": draft["id"]}).json()
    assert finished(client, job["id"])["status"] == "failed"
    [card] = client.get("/api/evaluations").json()["drafts"]
    assert card["state"] == "failed" and card["job_id"] == job["id"]
    client.put(f"/api/drafts/{draft['id']}", json={"form": {"dubs": [{"typed": "d2.mp4"}]}})
    assert client.get("/api/evaluations").json()["drafts"][0]["state"] == "draft"


def test_an_evaluation_opens_renames_and_deletes_from_its_card(client):
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()
    finished(client, job["id"])
    [card] = client.get("/api/evaluations").json()["evaluations"]
    opened = client.post(f"/api/evaluations/{card['id']}/open").json()
    assert opened["kind"] == "files" and client.get(f"/api/jobs/{opened['id']}/report").status_code == 200
    assert client.put(f"/api/evaluations/{card['id']}/title", json={"title": "Weather, Korean"}).json()["title"] ==         "Weather, Korean"
    assert client.get("/api/evaluations").json()["evaluations"][0]["title"] == "Weather, Korean"
    reopened = client.post(f"/api/evaluations/{card['id']}/open").json()      # rebuilt from the renamed files
    assert client.get(f"/api/jobs/{reopened['id']}/report").json()["report"]["project"]["title"] == "Weather, Korean"
    assert client.delete(f"/api/evaluations/{card['id']}").status_code == 200
    assert client.get("/api/evaluations").json()["evaluations"] == []
    assert client.get(f"/api/jobs/{reopened['id']}/report").status_code == 404
    assert client.post(f"/api/evaluations/{card['id']}/open").status_code == 404


def test_deleting_an_evaluation_deletes_the_upload_only_it_used(client, monkeypatch):
    def keeps_its_inputs(original, dub, out_dir=None, report_lang="en", **_):
        r = make_results()
        r["pipeline"].update(input_video_path=original, dubbed_video_path=dub)
        r["report"] = build_report(r, report_lang)
        pipeline.save_report_files(r, out_dir)
        return r
    monkeypatch.setattr(pipeline, "run_files_evaluation", keeps_its_inputs)
    up = client.post("/api/uploads", files={"file": ("clip.mp4", b"video", "video/mp4")}).json()
    folder = webapp.Path(webapp.UPLOADS_DIR) / up["id"].split(":")[1]
    job = client.post("/api/evaluations", json={"original": up["id"], "dub": "d.mp4"}).json()
    finished(client, job["id"])
    assert folder.is_dir()
    [card] = client.get("/api/evaluations").json()["evaluations"]
    client.delete(f"/api/evaluations/{card['id']}")
    assert not folder.exists()


def test_uploads_a_draft_holds_are_not_pruned(client, monkeypatch):
    held = client.post("/api/uploads", files={"file": ("held.mp4", b"v", "video/mp4")}).json()["id"]
    client.post("/api/drafts", json={"form": {"original": {"upload": held, "name": "held.mp4"}}})
    monkeypatch.setattr(webapp, "MAX_UPLOADS", 0)
    for i in range(2):
        client.post("/api/uploads", files={"file": (f"n{i}.mp4", b"v", "video/mp4")})
    webapp._prune_uploads(keep=0)
    assert (webapp.Path(webapp.UPLOADS_DIR) / held.split(":")[1]).is_dir()


@pytest.mark.parametrize("bad", ["..%2F..%2Fetc", "20261025-101500_0123abcz", "nothing"])
def test_unknown_evaluations_and_drafts_are_404(client, bad):
    assert client.get(f"/api/evaluations/{bad}/thumb").status_code == 404
    assert client.put(f"/api/evaluations/{bad}/title", json={"title": "x"}).status_code == 404
    assert client.delete(f"/api/evaluations/{bad}").status_code == 404
    assert client.get(f"/api/drafts/{bad}").status_code == 404
    assert client.delete(f"/api/drafts/{bad}").status_code == 404


def test_a_draft_that_is_too_big_is_refused_in_the_page_language(client):
    resp = client.post("/api/drafts", json={"form": {"x": "y" * 600_000}}, headers={"accept-language": "ko"})
    assert resp.status_code == 413 and resp.json()["detail"] == translate_message(library.DRAFT_TOO_BIG, "ko")
    assert resp.json()["detail"] != library.DRAFT_TOO_BIG


# ----- Stop and Continue -----

def test_a_stopped_evaluation_continues_with_the_same_request(client, monkeypatch):
    from dubeval.jobs import Cancelled
    ran, fake = [], pipeline.run_files_evaluation

    def stoppable(original, dub, report=None, cancel_event=None, **options):
        ran.append(dict(options))
        for _ in range(500):                        # a long measurement that checks for Stop
            if cancel_event.is_set():
                raise Cancelled("Stopped by user.")
            time.sleep(0.01)
        return fake(original, dub, report=report, cancel_event=cancel_event, **options)
    monkeypatch.setattr(pipeline, "run_files_evaluation", stoppable)
    draft = client.post("/api/drafts", json={"form": {"dubs": [{"typed": "d.mp4"}]}}).json()
    first = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4", "dub_type": "human",
                                                  "draft_id": draft["id"]}).json()["id"]
    client.post(f"/api/jobs/{first}/cancel")
    stopped = finished(client, first)
    assert stopped["status"] == "cancelled" and stopped["can_continue"]
    assert client.get("/api/evaluations").json()["drafts"][0]["state"] == "stopped"
    monkeypatch.setattr(pipeline, "run_files_evaluation", fake)
    second = client.post(f"/api/jobs/{first}/continue").json()["id"]
    assert second != first and finished(client, second)["status"] == "done"
    assert client.seen["dub_type"] == "human" and ran[0]["dub_type"] == "human"   # the same request again
    listed = client.get("/api/evaluations").json()
    assert listed["drafts"] == [] and len(listed["evaluations"]) == 1         # the draft followed the new run


def test_only_a_stopped_evaluation_can_continue(client):
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()["id"]
    assert finished(client, job)["can_continue"] is False
    assert client.post(f"/api/jobs/{job}/continue").status_code == 409
    assert client.post("/api/jobs/0123456789ab/continue").status_code == 404


def test_latest_evaluations_leave_out_deleted_ones(client, monkeypatch):
    from dubeval import history
    fake = pipeline.run_files_evaluation

    def records_history(*a, **k):                    # as the real run: report files, then a History record
        r = fake(*a, **k)
        r["pipeline"]["report_files"] = pipeline.save_report_files(r, k["out_dir"])
        history.record(r, "web")
        return r
    monkeypatch.setattr(pipeline, "run_files_evaluation", records_history)
    job = client.post("/api/evaluations", json={"original": "o.mp4", "dub": "d.mp4"}).json()
    finished(client, job["id"])
    assert len(client.get("/api/history").json()["history"]["recent"]) == 1
    [card] = client.get("/api/evaluations").json()["evaluations"]
    client.delete(f"/api/evaluations/{card['id']}")
    summary = client.get("/api/history").json()["history"]
    assert summary["recent"] == [] and summary["runs"] == 1          # still counted in the totals
