"""The Evaluations list (dubeval/library.py): cards of finished runs, rename, delete, drafts, and what pruning spares."""
import base64
import json
import os
import stat
from pathlib import Path

import pytest

from dubeval import library, pipeline
from dubeval.report import build_report
from sample_results import make_results

JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0 tiny jpeg").decode()


def run(tmp_path, run_id="20261025-101500_0123abcd", original=None, dub=None, title=None, lang="en") -> Path:
    """A finished one-dub run folder, as the app writes it."""
    r = make_results()
    r["pipeline"].update(input_video_path=str(original or tmp_path / "o.mp4"), dubbed_video_path=str(dub or tmp_path / "d.mp4"))
    if title:
        r["pipeline"]["custom_title"] = title
    r["report"] = build_report(r, lang)
    folder = Path(pipeline.RUNS_DIR) / run_id
    pipeline.save_report_files(r, folder)
    return folder


def comparison_run(tmp_path, run_id="20261025-111500_0123abcd") -> Path:
    folder = Path(pipeline.RUNS_DIR) / run_id
    for d in "AB":
        r = make_results()
        r["pipeline"].update(input_video_path=str(tmp_path / "o.mp4"), dubbed_video_path=str(tmp_path / f"{d}.mp4"))
        r["report"] = build_report(r, "en")
        pipeline.save_report_files(r, folder, f"report_{d}")
    (folder / "comparison.json").write_text(json.dumps(
        {"dubs": ["A", "B"], "recommendation": {"dub": "B", "title": "Trailer", "verdict": "check"}}), encoding="utf-8")
    return folder


def test_a_finished_run_is_a_card_with_its_verdict_and_videos(tmp_path):
    folder = run(tmp_path, title="Weather small talk")
    [card] = library.evaluations()
    assert card["id"] == folder.name and card["kind"] == "single" and card["title"] == "Weather small talk"
    assert card["verdict"] in ("good", "check", "poor") and card["dubs"] == 1
    assert card["inputs"] == [str(tmp_path / "d.mp4"), str(tmp_path / "o.mp4")]     # the dub first: its picture
    assert (folder / "card.json").is_file()


def test_cards_are_newest_first_and_folders_without_results_are_skipped(tmp_path):
    run(tmp_path, "20261024-090000_aaaaaaaa")
    run(tmp_path, "20261025-090000_bbbbbbbb")
    (Path(pipeline.RUNS_DIR) / "20261025-100000_cccccccc").mkdir()        # a run that failed: no report
    (Path(pipeline.RUNS_DIR) / "not-a-run").mkdir()
    assert [c["id"] for c in library.evaluations()] == ["20261025-090000_bbbbbbbb", "20261024-090000_aaaaaaaa"]


def test_a_comparison_is_one_card_with_the_recommended_verdict(tmp_path):
    comparison_run(tmp_path)
    [card] = library.evaluations()
    assert card["kind"] == "comparison" and card["dubs"] == 2
    assert card["title"] == "Trailer" and card["verdict"] == "check"
    assert str(tmp_path / "A.mp4") in card["inputs"] and str(tmp_path / "B.mp4") in card["inputs"]


@pytest.mark.parametrize("lang", ["en", "ko"])
def test_renaming_changes_the_saved_report_and_the_card(tmp_path, lang):
    folder = run(tmp_path, lang=lang)
    library.card(folder)                                              # cached before the rename
    assert library.rename(folder.name, "  New   name ") == {"id": folder.name, "title": "New name"}
    saved = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    assert saved["results"]["pipeline"]["custom_title"] == "New name"
    assert saved["report"]["project"]["title"] == "New name" and saved["report"]["lang"] == lang
    assert library.evaluations()[0]["title"] == "New name"


def test_renaming_a_comparison_keeps_each_dubs_report(tmp_path):
    folder = comparison_run(tmp_path)
    library.rename(folder.name, "Trailer, three studios")
    assert library.evaluations()[0]["title"] == "Trailer, three studios"
    assert json.loads((folder / "comparison.json").read_text(encoding="utf-8"))["recommendation"]["title"] == "Trailer"


def test_naming_a_dub_of_a_saved_comparison_rewrites_its_files(tmp_path):
    folder = comparison_run(tmp_path)
    library.rename(folder.name, "Trailer, three studios")
    library.rename_dub(folder.name, "A", "ElevenLabs")
    saved = json.loads((folder / "comparison.json").read_text(encoding="utf-8"))
    assert saved["labels"]["dub_A"] == "Dub A · ElevenLabs" and saved["custom_title"] == "Trailer, three studios"
    report = json.loads((folder / "report_A.json").read_text(encoding="utf-8"))
    assert report["results"]["pipeline"]["dub_name"] == "ElevenLabs" and report["report"]["project"]["dub_name"] == "ElevenLabs"
    assert "Dub A · ElevenLabs" in (folder / "comparison.html").read_text(encoding="utf-8")
    assert "ElevenLabs" in (folder / "report_A.txt").read_text(encoding="utf-8")
    assert "ElevenLabs" in (folder / "report_A.html").read_text(encoding="utf-8")
    assert library.evaluations()[0]["title"] == "Trailer, three studios"
    library.rename_dub(folder.name, "A", "")
    assert json.loads((folder / "comparison.json").read_text(encoding="utf-8"))["given_names"]["A"] is None
    with pytest.raises(ValueError):
        library.rename_dub(folder.name, "C", "x")


def test_a_damaged_report_stops_naming_before_anything_is_written(tmp_path):
    folder = comparison_run(tmp_path)
    (folder / "report_B.json").write_text("{not json", encoding="utf-8")
    before = (folder / "report_A.json").read_bytes()
    with pytest.raises(ValueError):
        library.rename_dub(folder.name, "A", "ElevenLabs")
    assert (folder / "report_A.json").read_bytes() == before


def test_a_note_that_cant_be_written_still_hides_the_files(tmp_path, monkeypatch):
    (tmp_path / "jobs").mkdir()
    def refuse(*a, **k):
        raise PermissionError("in use")
    monkeypatch.setattr(Path, "write_text", refuse)
    library.tidy_data_folder(tmp_path, "en")
    if os.name == "nt":
        assert _hidden(tmp_path / "jobs")


def _hidden(path: Path) -> bool:
    return bool(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)


def test_opening_the_data_folder_hides_what_only_the_app_reads_and_leaves_one_note(tmp_path):
    for name in ("cache", "drafts", "jobs", "output", "uploads"):
        (tmp_path / name).mkdir()
    for name in (".env", "history.jsonl", "feedback.jsonl"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    library.tidy_data_folder(tmp_path, "en")
    library.tidy_data_folder(tmp_path, "es")            # the language changed: one note, not two
    notes = [p.name for p in tmp_path.glob("*.txt")]
    assert notes == ["Qué hay en esta carpeta.txt"]
    assert "uploads" in (tmp_path / notes[0]).read_text(encoding="utf-8")
    if os.name == "nt":
        assert all(_hidden(tmp_path / n) for n in ("cache", "drafts", "jobs", ".env", "history.jsonl", "feedback.jsonl"))
        assert not any(_hidden(tmp_path / n) for n in ("output", "uploads", notes[0]))


def test_the_app_can_still_write_its_files_once_they_are_hidden(tmp_path, monkeypatch):
    from dubeval import history, settings
    monkeypatch.setattr(settings, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "history.jsonl")
    (tmp_path / ".env").write_text("", encoding="utf-8")
    r = make_results()
    r["report"] = build_report(r, "en")
    r["pipeline"]["report_files"] = {"html": str(tmp_path / "report.html")}
    history.record(r, "web")
    library.tidy_data_folder(tmp_path, "en")
    history.record(r, "web")                            # appends
    library.tidy_data_folder(tmp_path, "en")
    history.rename(str(tmp_path / "report.html"), "New")  # replaces
    settings.save_key("gemini", "AIza" + "x" * 35)      # replaces
    assert [e["title"] for e in history.load(tmp_path / "history.jsonl")] == ["New", "New"]
    assert "GEMINI_API_KEY" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_an_empty_title_or_an_unknown_run_is_refused(tmp_path):
    folder = run(tmp_path)
    with pytest.raises(ValueError):
        library.rename(folder.name, "   ")
    for bad in ("../../etc", "20261025-101500_0123abcz", "", "20261025-101500_ffffffff"):
        with pytest.raises(ValueError):
            library.run_folder(bad)


def test_deleting_a_run_frees_only_the_videos_nothing_else_uses(tmp_path):
    shared = tmp_path / "shared_original.mp4"
    a = run(tmp_path, "20261025-090000_aaaaaaaa", original=shared, dub=tmp_path / "dub_a.mp4")
    run(tmp_path, "20261025-090001_bbbbbbbb", original=shared, dub=tmp_path / "dub_b.mp4")
    freed = library.delete(a.name)
    assert not a.exists()
    assert freed == [tmp_path / "dub_a.mp4"]                        # the other run still plays the original
    with pytest.raises(ValueError):
        library.delete(a.name)


def test_a_picture_must_be_a_small_image(tmp_path):
    assert library.save_thumbnail(tmp_path / "t.jpg", JPEG) and (tmp_path / "t.jpg").read_bytes().startswith(b"\xff\xd8")
    big = "data:image/jpeg;base64," + base64.b64encode(b"x" * (library.MAX_THUMB_BYTES + 1)).decode()
    for bad in (None, "", "data:text/html;base64,PGI+", "https://example.com/a.jpg", "data:image/jpeg;base64,***", big):
        assert not library.save_thumbnail(tmp_path / "bad.jpg", bad)
    assert not (tmp_path / "bad.jpg").exists()


def test_a_runs_picture_is_kept_and_none_is_made_without_its_videos(tmp_path):
    folder = run(tmp_path)                                           # its videos don't exist
    assert library.thumbnail(folder.name) is None
    library.save_thumbnail(folder / library.THUMB, JPEG)
    assert library.thumbnail(folder.name) == folder / library.THUMB


def test_drafts_are_saved_again_under_their_id_and_listed_newest_first():
    first = library.save_draft(None, "Clip", JPEG, {"original": {"typed": "C:/v/o.mp4"}})
    second = library.save_draft(None, None, None, {"dubs": [{"typed": "https://perso.ai/x"}]})
    again = library.save_draft(first["id"], "Clip 2", "javascript:alert(1)", {"original": {"typed": "C:/v/o2.mp4"}})
    assert again["id"] == first["id"] and again["created"] == first["created"] and again["name"] == "Clip 2"
    assert again["thumbnail"] is None                               # only a data:image picture is kept
    assert [d["id"] for d in library.drafts()] == [first["id"], second["id"]]
    assert library.get_draft(first["id"])["form"] == {"original": {"typed": "C:/v/o2.mp4"}}
    library.delete_draft(second["id"])
    with pytest.raises(ValueError):
        library.get_draft(second["id"])
    for bad in ("../x", "ABCDEF012345", "123"):
        with pytest.raises(ValueError):
            library.get_draft(bad)


def test_a_big_draft_drops_its_picture_then_is_refused():
    big_picture = "data:image/jpeg;base64," + "A" * library.MAX_DRAFT_BYTES
    kept = library.save_draft(None, "Clip", big_picture, {"note": "x"})
    assert kept["thumbnail"] is None
    with pytest.raises(ValueError):
        library.save_draft(None, "Clip", None, {"note": "x" * library.MAX_DRAFT_BYTES})


def test_a_started_draft_remembers_its_job_and_gives_the_run_its_picture(tmp_path):
    d = library.save_draft(None, "Clip", JPEG, {"dubs": [{"upload": "upload:0123456789abcdef"}]})
    library.start_draft(d["id"], "abcdef012345", str(tmp_path / "run"))
    assert library.get_draft(d["id"])["job"] == {"id": "abcdef012345", "folder": str(tmp_path / "run")}
    assert (tmp_path / "run" / library.THUMB).is_file()
    # Editing it again (after a failed run) makes it a plain draft.
    assert library.save_draft(d["id"], "Clip", JPEG, {})["job"] is None


def test_what_kept_runs_play_and_drafts_hold_is_protected(tmp_path):
    cache = tmp_path / "cache" / "a514ea8a366fc314"
    run(tmp_path, original=cache / "original.mp4", dub=cache / "dubbed.mp4")
    library.save_draft(None, "Clip", None, {"original": {"upload": "upload:0123456789abcdef", "name": "o.mp4"},
                                              "dubs": [{"typed": "C:/v/d.mp4", "subtitles": {"upload": "upload:fedcba9876543210"}}]})
    used = library.referenced_inputs()
    assert {"upload:0123456789abcdef", "upload:fedcba9876543210", str(cache / "original.mp4")} <= used
    assert library.protects(cache, used)
    assert library.protects(tmp_path / "uploads" / "0123456789abcdef", used)
    assert not library.protects(tmp_path / "cache" / "ffffffffffffffff", used)
    assert not library.protects(tmp_path / "cache" / "a514ea8a366fc31", used)   # a prefix of the name isn't inside


def test_pruning_spares_the_downloads_of_kept_evaluations(tmp_path):
    cache = Path(pipeline.CACHE_DIR)
    for i, name in enumerate(["kept", "old", "new"]):
        (cache / name).mkdir(parents=True)
        (cache / name / "dubbed.mp4").write_bytes(b"v")
        os.utime(cache / name, (i, i))
    os.utime(cache / "kept", (0, 0))
    run(tmp_path, original=cache / "kept" / "original.mp4", dub=cache / "kept" / "dubbed.mp4")
    pipeline._prune(cache, keep=1)
    assert sorted(p.name for p in cache.iterdir()) == ["kept", "new"]


def test_the_apps_runs_are_kept_until_deleted(tmp_path):
    for i in range(3):
        run(tmp_path, f"20261025-09000{i}_aaaaaaaa")
    pipeline.prune_old_runs()
    assert len(library.evaluations()) == 3


def test_a_stopped_runs_leftover_folder_goes_with_its_draft(tmp_path):
    left = Path(pipeline.RUNS_DIR) / "20261025-120000_aaaaaaaa"
    kept = run(tmp_path, "20261025-120001_bbbbbbbb")                 # a finished run is never touched this way
    for folder in (left, kept):
        d = library.save_draft(None, "Clip", JPEG, {})
        library.start_draft(d["id"], "abcdef012345", str(folder))
        assert (folder / library.THUMB).is_file()
        library.delete_draft(d["id"])
    assert not left.exists() and (kept / "report.json").is_file()
    # Editing a draft after its run stopped (to try again) also drops that run's leftover folder.
    d = library.save_draft(None, "Clip", JPEG, {})
    library.start_draft(d["id"], "abcdef012345", str(left))
    library.save_draft(d["id"], "Clip", JPEG, {"changed": True})
    assert not left.exists()


def test_a_running_evaluations_folder_is_never_dropped(tmp_path, monkeypatch):
    from dubeval import jobs
    folder = Path(pipeline.RUNS_DIR) / "20261025-130000_cccccccc"
    d = library.save_draft(None, "Clip", JPEG, {})
    library.start_draft(d["id"], "abcdef012345", str(folder))
    monkeypatch.setattr(jobs, "get_job", lambda job_id: type("J", (), {"status": "running"})())
    library.save_draft(d["id"], "Clip", JPEG, {"changed": True})
    assert (folder / library.THUMB).is_file()
