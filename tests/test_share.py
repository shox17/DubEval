"""Tests for share-link evaluation: link parsing, the public Perso endpoint, downloads and the share pipeline."""
import json
import os

import pytest

from dubeval import pipeline
from dubeval.perso_api import PersoError, download_media, get_shared_project, media_url, parse_share_url
from conftest import SAMPLE_VIDEO, needs_sample_video
from fake_perso import SHARE_TOKEN, SHARE_URL, SHARED_PROJECT, CopyingFakePerso, FakePerso
from sample_results import make_results

NO_SLEEP = lambda s: None


@pytest.mark.parametrize("text", [SHARE_URL, f"  {SHARE_URL}  ", SHARE_TOKEN, SHARE_URL.replace("https://", ""),
                                  SHARE_URL.replace("/en/", "/ko/") + "&utm=x", f"https://www.perso.ai/share/video-translator?seq={SHARE_TOKEN}",
                                  # gallery pages carry the same public token
                                  f"https://perso.ai/video-translator/en-es/movies-tv-shows?seq={SHARE_TOKEN}",
                                  f"https://perso.ai/video-translator/en-es/animation?seq={SHARE_TOKEN}&lang=en"])
def test_share_links_are_parsed(text):
    assert parse_share_url(text) == SHARE_TOKEN


@pytest.mark.parametrize("text, msg", [("", "Paste a Perso share link"),
                                       ("https://youtube.com/watch?v=abc", "doesn't look like a Perso share link"),
                                       ("https://perso.ai/en/workspace/vt/detail/1", "doesn't look like"),
                                       ("https://perso.ai/en/share/video-translator", "missing its seq")])
def test_bad_links_get_plain_errors(text, msg):
    with pytest.raises(ValueError, match=msg):
        parse_share_url(text)


def test_media_url_resolves_and_encodes():
    assert media_url("/perso-storage/a b/비디오.mp4") == \
        "https://portal-media.perso.ai/perso-storage/a%20b/%EB%B9%84%EB%94%94%EC%98%A4.mp4"


def test_server_errors_are_retried_then_succeed():
    fake = FakePerso()
    real = fake.request
    answers = iter([503, 429])

    def flaky(method, url, **kw):
        status = next(answers, None)
        if status:
            fake.calls.append((method, url, None))
            from fake_perso import FakeResponse
            return FakeResponse(status, {"message": "busy"})
        return real(method, url, **kw)
    fake.request = flaky
    assert get_shared_project(SHARE_TOKEN, session=fake, sleep=NO_SLEEP)["seq"] == 100001


def test_shared_project_needs_no_api_key():
    fake = FakePerso()
    project = get_shared_project(SHARE_TOKEN, session=fake, sleep=NO_SLEEP)
    assert project["seq"] == 100001
    assert fake.calls[0][1] == f"/video-translator/api/v1/projects/shared/{SHARE_TOKEN}"


def test_sharing_turned_off_explains_what_to_do():
    with pytest.raises(PersoError, match="Sharing is turned off"):
        get_shared_project(SHARE_TOKEN, session=FakePerso(share_error=(403, "VT4035")), sleep=NO_SLEEP)


def test_unknown_link_and_unfinished_project():
    with pytest.raises(PersoError, match="couldn't find a project"):
        get_shared_project(SHARE_TOKEN, session=FakePerso(share_error=(404, "X404")), sleep=NO_SLEEP)
    unfinished = {**SHARED_PROJECT, "translatedFileUrl": None, "lipSyncFileUrl": None}
    with pytest.raises(PersoError, match="no finished dubbed video"):
        get_shared_project(SHARE_TOKEN, session=FakePerso(shared_project=unfinished), sleep=NO_SLEEP)


def test_download_media_url_encodes_and_writes_atomically(tmp_path):
    fake = FakePerso(original_bytes=b"orig")
    out = download_media(SHARED_PROJECT["originalFileUrl"], str(tmp_path / "o.mp4"), session=fake, sleep=NO_SLEEP)
    assert open(out, "rb").read() == b"orig" and not os.path.exists(out + ".part")
    assert "original%20video.mp4" in fake.calls[-1][1]


def test_share_pipeline_flow(isolated_output, monkeypatch):
    """Fetch → download both videos (lip-synced one as the dub) → evaluate → report files; no key, no credits."""
    seen = {}

    def fake_eval(**kw):
        seen.update(kw)
        r = make_results()
        return {k: v for k, v in r.items() if k not in ("pipeline", "translation_judge")}

    monkeypatch.setattr(pipeline, "run_full_evaluation", fake_eval)
    fake = FakePerso(original_bytes=b"orig", video_bytes=b"dub")
    stages = []
    r = pipeline.run_share_evaluation(SHARE_URL, report=lambda p: stages.append(p.stage), session=fake,
                                      sleep=NO_SLEEP, use_translation_judge=False)
    media = [url for kind, url, _ in fake.calls if kind == "GET-MEDIA"]
    assert "Lip-synced" in media[1] and "original" in media[0]
    assert seen["target_lang"] == "ko" and seen["source_lang"] == "en"
    assert seen["include_lipsync"] is True           # lip-synced project → lip movement measured automatically
    assert open(seen["dubbed_video_path"], "rb").read() == b"dub"
    assert stages[0] == "fetch" and "download" in stages and stages[-1] == "evaluate"

    p = r["pipeline"]
    assert p["share"]["evaluated_video"] == "lip-synced" and p["share"]["seq"] == 100001
    assert r["translation_judge"]["measured"] is False
    assert r["report"]["overall"]["level"] in ("good", "check", "poor")
    for path in p["report_files"].values():
        assert os.path.exists(path)
    saved = json.load(open(p["report_files"]["json"], encoding="utf-8"))
    assert saved["report"]["project"]["title"] == "QA sample.mp4 → ko"
    assert pipeline.load_results()["pipeline"]["run_id"] == p["run_id"]


def test_share_pipeline_uses_plain_dub_without_lipsync(isolated_output, monkeypatch):
    monkeypatch.setattr(pipeline, "run_full_evaluation",
                        lambda **kw: {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")})
    fake = FakePerso(shared_project={**SHARED_PROJECT, "isLipSync": False, "lipSyncFileUrl": None})
    seen = {}
    monkeypatch.setattr(pipeline, "run_full_evaluation", lambda **kw: seen.update(kw) or
                        {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")})
    r = pipeline.run_share_evaluation(SHARE_URL, session=fake, sleep=NO_SLEEP, use_translation_judge=False)
    assert "TranslatedVideo" in [u for k, u, _ in fake.calls if k == "GET-MEDIA"][1]
    assert r["pipeline"]["share"]["evaluated_video"] == "dubbed"
    assert seen["include_lipsync"] is False          # not lip-synced → lip movement skipped automatically


def test_bad_link_makes_no_network_calls(isolated_output):
    fake = FakePerso()
    with pytest.raises(ValueError):
        pipeline.run_share_evaluation("https://example.com/video", session=fake, sleep=NO_SLEEP)
    assert fake.calls == []


@pytest.mark.slow
@needs_sample_video
def test_share_pipeline_end_to_end_on_sample(isolated_output):
    """Real Whisper + measurements on the sample video served through the fake share link."""
    # The "dub" is the English original itself, shared as an English "dub": a perfect pair.
    english = {**SHARED_PROJECT, "targetLanguage": {"code": "en", "name": "English (US)", "languageTag": "default"}}
    fake = CopyingFakePerso(SAMPLE_VIDEO, shared_project=english)
    r = pipeline.run_share_evaluation(SHARE_URL, session=fake, sleep=NO_SLEEP, use_translation_judge=False,
                                      include_lipsync=False, whisper_model_name="tiny")
    rep = r["report"]
    ids = {m["id"]: m for s in rep["sections"] for m in s["metrics"]}
    for mid in ("length_match", "loudness_match", "file_check", "language", "speech_overlap"):
        assert ids[mid]["level"] == "good", (mid, ids[mid])
    assert r["timing_alignment"]["overlap_pct"] > 95


def test_a_share_link_keeps_its_subtitle_file_and_dub_kind(isolated_output, monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "run_full_evaluation",
                        lambda **kw: {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")})
    subs = tmp_path / "uz.srt"
    subs.write_text("1\n00:00:00,000 --> 00:10:00,000\nHammaga salom\n", encoding="utf-8")   # covers every line
    r = pipeline.run_share_evaluation(SHARE_URL, session=FakePerso(), sleep=NO_SLEEP, use_translation_judge=False,
                                      dub_subtitles=str(subs), dub_type="human")
    assert r["subtitles"]["dub"][0]["text"] == "Hammaga salom" and r["pipeline"]["share"]["subtitles"]["dub"] == 1
    assert r["voice_similarity"]["reason_key"] == "r.vs.not_compared_human"


def test_a_named_checker_is_the_one_asked(monkeypatch):
    asked = {}
    monkeypatch.setattr(pipeline, "judge_translation", lambda *a, **kw: asked.update(kw) or {"measured": False})
    r = make_results()
    pipeline.check_translation(r, "openai", lambda *a: None)
    assert asked["provider"] == "openai"
    pipeline.check_translation(r, True, lambda *a: None)
    assert asked["provider"] is None                                       # auto: DUBEVAL_JUDGE decides
