"""Tests for problem clips: which moments get a clip, where a moment is in the dub, and real clips from small
generated videos (ffmpeg, a few seconds)."""
import subprocess

import pytest

from dubeval import clips
from dubeval.inputs import FFMPEG_EXE, probe


def _finding(start, end, severity="check", category="line_length", **kw):
    """A problem interval as report.problem_intervals has it."""
    return {"start": start, "end": end, "severity": severity, "category": category,
            "category_label": "Line length" if category == "line_length" else "Long silence",
            "check": "line_fit", "check_label": "Line length", "description": kw.get("problem", "Too long."),
            "problem": kw.get("problem", "Too long."), "original": kw.get("original"), "dubbed": kw.get("dubbed"),
            "suggestion": kw.get("suggestion"), "doubt": None, "line": kw.get("line")}


def _report(intervals, moments=None, duration=8.0):
    """The parts of a report the clips read."""
    return {"project": {"duration_sec": duration, "title": "Clip test"},
            "overall": {"level": "check", "label": "Needs review", "summary": "Line length needs review."},
            "problem_intervals": intervals,
            "moments": moments if moments is not None else [
                {"start": iv["start"], "end": iv["end"], "severity": iv["severity"], "intervals": [i]}
                for i, iv in enumerate(intervals)]}


def test_a_moment_is_found_in_the_dub_by_its_shift_or_its_part():
    assert clips.dub_time(10.0, 0.4, None) == pytest.approx(10.4)
    parts = [{"start": 0.0, "end": 20.0, "offset_sec": 1.0}, {"start": 25.0, "end": 60.0, "offset_sec": -3.0}]
    assert clips.dub_time(5.0, 0.0, parts) == 6.0 and clips.dub_time(30.0, 0.0, parts) == 27.0
    assert clips.dub_time(21.0, 0.0, parts) == 22.0          # between parts: the nearer one's shift


def test_each_moment_gets_a_window_around_it_and_long_ones_are_cut():
    rep = _report([_finding(0.5, 1.5), _finding(3.0, 40.0, "poor")], duration=60.0)
    planned, left_out = clips.plan(rep, 60.0)
    assert left_out == 0 and [c["number"] for c in planned] == [1, 2]
    assert planned[0]["from"] == 0.0 and planned[0]["length"] == pytest.approx(1.5 + clips.PAD_SEC)   # clipped at 0
    assert planned[1]["from"] == pytest.approx(3.0 - clips.PAD_SEC) and planned[1]["length"] == clips.MAX_CLIP_SEC
    assert planned[1]["cut"] and not planned[0]["cut"]


def test_too_many_moments_keep_the_worst_in_time_order(monkeypatch):
    monkeypatch.setattr(clips, "MAX_CLIPS", 2)
    rep = _report([_finding(1, 2), _finding(3, 4, "poor"), _finding(5, 6), _finding(7, 8, "poor")], duration=20.0)
    planned, left_out = clips.plan(rep, 20.0)
    assert [c["start"] for c in planned] == [3, 7] and left_out == 2


def test_a_moment_with_several_findings_leads_with_the_first():
    lead, other = _finding(1, 3, "poor", "long_silence", problem="The dub is silent."), _finding(1.5, 2.5)
    rep = _report([other, lead], moments=[{"start": 1, "end": 3, "severity": "poor", "intervals": [1, 0]}])
    planned, _ = clips.plan(rep, 8.0)
    assert planned[0]["findings"] == [lead, other]


@pytest.fixture(scope="module")
def videos(tmp_path_factory):
    """An 8 s original and dub (a test picture and a tone each), and a dub that is sound only."""
    folder = tmp_path_factory.mktemp("clipmedia")
    made = {}
    for name, size, tone in (("original.mp4", "320x180", 440), ("dub.mp4", "320x240", 660)):
        path = folder / name
        subprocess.run([FFMPEG_EXE, "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"testsrc=size={size}:rate=25:duration=8", "-f", "lavfi", "-i",
                        f"sine=frequency={tone}:duration=8", "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)
        made[name] = path
    audio = folder / "dub.m4a"
    subprocess.run([FFMPEG_EXE, "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=550:duration=8", "-c:a", "aac", str(audio)], check=True)
    made["audio"] = audio
    return made


def test_clips_and_their_page_are_written(videos, tmp_path):
    rep = _report([_finding(2.0, 3.0, original="Hello there.", dubbed="Hola.", suggestion="Hola a todos."),
                   _finding(5.0, 6.0, "poor", "long_silence", problem="The dub is silent.")])
    general = [("Loudness", "Needs review", "Louder than the original."),
               ("Line length", "Needs review", "2 of 8 lines are off. They're listed under Things to check.")]
    written = clips.write_clips([{"label": None, "report": rep, "original": str(videos["original.mp4"]),
                                  "dub": str(videos["dub.mp4"]), "offset": 0.4, "parts": None, "general": general}],
                                tmp_path, "en", "Clip test")
    index, *made = written
    assert index == tmp_path / "Problem clips.html"                          # at the top, the clips in a folder
    assert [p.relative_to(tmp_path).as_posix() for p in made] == ["clips/01 00m02s Line length.mp4",
                                                                   "clips/02 00m05s Long silence.mp4"]
    info = probe(str(made[0]))
    assert info["has_video"] and len(info["audio_tracks"]) == 1
    assert 7.0 <= info["duration_sec"] <= 9.0          # 1 s moment + 1.5 s on each side, twice: original's sound, dub's
    page = index.read_text(encoding="utf-8")
    for text in ("Problems to fix: Clip test", "clips/01%2000m02s%20Line%20length.mp4", "Hola a todos.",
                 "The dub is silent.", "Louder than the original.", "Needs review", "listed in the clips below"):
        assert text in page
    assert "<script" not in page and "Things to check" not in page          # the app's screens mean nothing here


def test_a_comparison_names_each_dubs_clips_and_a_sound_only_dub_shows_black(videos, tmp_path):
    rep = _report([_finding(2.0, 3.0)])
    source = lambda label, dub: {"label": label, "report": rep, "original": str(videos["original.mp4"]), "dub": dub,
                                 "offset": 0.0, "parts": None, "general": []}
    written = clips.write_clips([source("A · Perso", str(videos["dub.mp4"])), source("B", str(videos["audio"]))],
                                tmp_path, "ko", "비교")
    assert written[0].name == "문제 클립.html"
    assert [p.name for p in written[1:]] == ["A-01 00m02s Line length.mp4", "B-01 00m02s Line length.mp4"]
    assert probe(str(written[2]))["has_video"]
    page = written[0].read_text(encoding="utf-8")
    assert "A · Perso" in page and "고칠 문제: 비교" in page and "더빙" in page


def test_without_the_videos_no_clips_are_made(tmp_path):
    rep = _report([_finding(2.0, 3.0)])
    with pytest.raises(FileNotFoundError, match="gone"):
        clips.write_clips([{"label": None, "report": rep, "original": str(tmp_path / "gone.mp4"),
                            "dub": str(tmp_path / "gone2.mp4"), "offset": 0.0, "parts": None, "general": []}],
                          tmp_path, "en", None)


def test_a_dub_with_nothing_to_look_at_gets_a_page_and_no_clips(videos, tmp_path):
    written = clips.write_clips([{"label": None, "report": _report([]), "original": str(videos["original.mp4"]),
                                  "dub": str(videos["dub.mp4"]), "offset": 0.0, "parts": None, "general": []}],
                                tmp_path, "es", "Nada")
    assert len(written) == 1 and "no hay clips" in written[0].read_text(encoding="utf-8")


def test_a_pointer_to_the_apps_things_to_check_points_at_the_clips_in_every_language():
    from dubeval.report_text import REPORT_TEXT as R
    for lang, said in (("en", "in the clips below"), ("ko", "아래 클립"), ("pt", "nos clipes abaixo"),
                       ("es", "en los clips de abajo")):
        for key in ("r.align.spots_many", "r.line.bad", "r.issues.maybe_only_one", "r.clarity.poor"):
            text = clips._for_page(R[key][lang], lang)
            assert R["r.label.things"][lang] not in text and said in text, (lang, key, text)


def test_the_clip_shows_a_gap_and_outlines_the_side_being_heard(videos, tmp_path):
    out = tmp_path / "one.mp4"
    clips.make_clip(str(videos["original.mp4"]), str(videos["dub.mp4"]), 1.0, 1.0, 2.0, out, None, (True, True))
    import numpy as np
    left_width = 320 * clips.HEIGHT // 180                 # the 320x180 original scaled to 360 high
    width = left_width + clips.GAP + 320 * clips.HEIGHT // 240
    raw = subprocess.run([FFMPEG_EXE, "-nostdin", "-loglevel", "error", "-i", str(out), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, clips.HEIGHT, width, 3)
    assert 98 <= len(frames) <= 100                        # 2 s at 25 frames a second, twice
    first, second = frames[10], frames[60]
    assert first[clips.HEIGHT // 2, left_width + clips.GAP // 2].min() > 240   # white space between the pictures
    yellow = lambda px: px[0] > 200 and px[1] > 150 and px[2] < 90
    mid = clips.HEIGHT // 2
    assert yellow(first[mid, 2]) and not yellow(first[mid, width - 3])          # the original's sound: left outlined
    assert yellow(second[mid, width - 3]) and not yellow(second[mid, 2])        # then the dub's: right outlined
