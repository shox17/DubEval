"""Evaluating any original and its dub: files, links and two tracks of one file, through to the saved report."""
import json

import numpy as np

import pytest

from dubeval import cli, pipeline, schema
from sample_results import make_results
from test_inputs import make_media


@pytest.fixture
def fake_eval(monkeypatch):
    """Stands in for the measurements (speech recognition is tested elsewhere); records what it was given."""
    seen = {}

    def run(**kw):
        seen.update(kw)
        r = make_results()
        return {k: v for k, v in r.items() if k not in ("pipeline", "translation_judge")}
    monkeypatch.setattr(pipeline, "run_full_evaluation", run)
    monkeypatch.setattr(pipeline, "_detect_dub_language", lambda path, model, cache, y=None: ("ko", 0.99))
    return seen


def test_two_local_files_produce_a_valid_report(tmp_path, isolated_output, fake_eval):
    original, dub = make_media(tmp_path / "talk_en.mp4"), make_media(tmp_path / "talk_ko.mp4")
    stages = []
    r = pipeline.run_files_evaluation(original, dub, report=lambda p: stages.append(p.stage), out_dir=str(tmp_path / "out"),
                                      use_translation_judge=False, report_lang="en")
    assert fake_eval["original_video_path"] == original and fake_eval["dubbed_video_path"] == dub
    assert fake_eval["target_lang"] == "ko" and fake_eval["include_lipsync"] is False
    assert stages[0] == "prepare" and stages[-1] == "evaluate"
    p = r["pipeline"]
    assert p["input"]["kind"] == "files" and p["input"]["languages_from"] == {"source": "detected", "target": "detected"}
    assert p["input"]["title"] == "talk_ko" and p["input"]["dub_media"]["audio_tracks"]
    assert r["report"]["project"]["title"] == "talk_ko" and r["report"]["project"]["share_url"] is None
    saved = json.loads(open(p["report_files"]["json"], encoding="utf-8").read())
    schema.validate(saved)


def test_given_languages_are_used_and_subtitles_kept(tmp_path, isolated_output, fake_eval):
    srt = tmp_path / "ko.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:01,500\n안녕하세요\n", encoding="utf-8")
    r = pipeline.run_files_evaluation(make_media(tmp_path / "o.mp4"), make_media(tmp_path / "d.mp4"),
                                      out_dir=str(tmp_path / "out"), source_lang="en", target_lang="ko",
                                      dub_subtitles=str(srt), use_translation_judge=False)
    assert fake_eval["source_lang"] == "en" and fake_eval["target_lang"] == "ko"
    assert r["pipeline"]["input"]["languages_from"] == {"source": "given", "target": "given"}
    assert r["subtitles"]["dub"] == [{"start": 0.5, "end": 1.5, "text": "안녕하세요"}]
    assert r["pipeline"]["input"]["subtitles"] == {"original": None, "dub": 1}


def test_one_file_with_two_audio_tracks(tmp_path, isolated_output, fake_eval):
    film = make_media(tmp_path / "film.mkv", audio_tracks=2)
    r = pipeline.run_files_evaluation(film, film, original_track=0, dub_track=1, target_lang="ko",
                                      out_dir=str(tmp_path / "out"), use_translation_judge=False)
    assert fake_eval["original_video_path"] != fake_eval["dubbed_video_path"]
    assert fake_eval["dubbed_video_path"].endswith("_track1.mkv")
    assert r["pipeline"]["input"]["kind"] == "tracks"


def test_problems_are_found_before_any_measuring(tmp_path, isolated_output, fake_eval):
    silent = make_media(tmp_path / "silent.mp4", audio_tracks=0)
    with pytest.raises(ValueError, match="no audio track"):
        pipeline.run_files_evaluation(make_media(tmp_path / "o.mp4"), silent, target_lang="ko",
                                      out_dir=str(tmp_path / "out"))
    assert not fake_eval


def test_evaluate_command(tmp_path, isolated_output, fake_eval, capsys):
    original, dub = make_media(tmp_path / "o.mp4"), make_media(tmp_path / "d.mp4")
    code = cli.main(["evaluate", "--original", original, "--dub", dub, "--target-lang", "ko", "--lang", "en",
                     "--out", str(tmp_path / "out"), "--no-translation-check", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["overall"]["level"] in ("good", "check", "poor")


def test_evaluate_command_with_tracks_and_bad_input(tmp_path, isolated_output, fake_eval, capsys):
    args = cli.parse_evaluate_args(["--tracks", "film.mkv", "--dub-track", "2"])
    assert (args.original, args.dub, args.original_track, args.dub_track) == ("film.mkv", "film.mkv", 0, 2)
    with pytest.raises(SystemExit):
        cli.parse_evaluate_args(["--original", "a.mp4"])
    code = cli.main(["evaluate", "--original", str(tmp_path / "missing.mp4"), "--dub", str(tmp_path / "x.mp4"),
                     "--out", str(tmp_path / "out")])
    assert code == 2 and "doesn't exist" in capsys.readouterr().err


def test_an_unsure_language_guess_is_flagged_in_the_report(tmp_path, isolated_output, fake_eval, monkeypatch):
    monkeypatch.setattr(pipeline, "_detect_dub_language", lambda path, model, cache, y=None: ("kk", 0.47))
    r = pipeline.run_files_evaluation(make_media(tmp_path / "o.mp4"), make_media(tmp_path / "d.mp4"),
                                      out_dir=str(tmp_path / "out"), use_translation_judge=False, report_lang="en")
    general = [t["message"] for t in r["report"]["things_to_check"] if t["start"] is None]
    assert any("only 47% sure" in m and "--target-lang" in m for m in general)


def test_report_title_skips_generic_file_names(tmp_path):
    job = tmp_path / "Self introduction_ko"
    job.mkdir()
    assert pipeline._title(str(job / "dubbed.mp4")) == "Self introduction_ko"
    assert pipeline._title(str(tmp_path / "talk_ko.mp4")) == "talk_ko"
    assert pipeline._title("https://example.com/media/clip.mp4?x=1") == "clip"


def test_schema_command_prints_the_schema(capsys):
    assert cli.main(["schema"]) == 0
    assert json.loads(capsys.readouterr().out)["title"].startswith("DubEval report")


def pairing_result() -> dict:
    return {"measured": True, "same_video": True, "offset_sec": 0.0, "parts": [], "steady_offset": True,
            "coverage_pct": 100.0, "missing": []}


def test_the_sound_is_read_once_for_the_check_the_language_and_the_evaluation(monkeypatch, tmp_path):
    """One extraction of both tracks feeds pairing, the language guess and the evaluation."""
    from dubeval import evaluate
    calls, seen = [], {}
    y = (np.zeros(16000, dtype=np.float32), np.ones(16000, dtype=np.float32))
    monkeypatch.setattr(pipeline, "load_both", lambda o, d: calls.append((o, d)) or y)
    monkeypatch.setattr(pipeline.pairing, "pair", lambda o, d, yo, yd, *a, **k: seen.update(pair=(yo is y[0], yd is y[1]))
                        or pairing_result())
    monkeypatch.setattr(pipeline, "_detect_dub_language", lambda path, model, cache, y=None: seen.update(lang=y is not None)
                        or ("ko", 0.99))
    monkeypatch.setattr(pipeline, "run_full_evaluation", lambda **kw: seen.update(eval=kw.get("audio") is y)
                        or (_ for _ in ()).throw(RuntimeError("stop here")))
    o, d = tmp_path / "o.mp4", tmp_path / "d.mp4"
    o.write_bytes(b"o")
    d.write_bytes(b"d")
    monkeypatch.setattr(pipeline.inputs, "check", lambda path, label: {})
    with pytest.raises(RuntimeError, match="stop here"):
        pipeline.evaluate_files(str(o), str(d), lambda *a: None, lambda: None, use_cache=False)
    assert len(calls) == 1 and seen == {"pair": (True, True), "lang": True, "eval": True}


def test_the_sound_is_loaded_in_the_calling_thread_never_in_workers(monkeypatch, tmp_path):
    """Regression (2026-10-23): librosa's first use in two worker threads at once deadlocked on Python's import locks
    and hung "Reading the sound of both videos..." forever. Only ffmpeg may run in the workers."""
    import threading
    from dubeval import evaluate
    caller = threading.current_thread()
    extracted, loaded = [], []

    def fake_extract(path, out, *a, **k):
        extracted.append(threading.current_thread() is caller)
        return out

    def fake_load(path):
        loaded.append(threading.current_thread() is caller)
        return np.zeros(16000, dtype=np.float32)
    monkeypatch.setattr(evaluate, "extract_audio", fake_extract)
    monkeypatch.setattr(evaluate, "load_audio", fake_load)
    a, b = evaluate.load_both("o.mp4", "d.mp4")
    assert len(a) == len(b) == 16000
    assert extracted == [False, False] and loaded == [True, True]
