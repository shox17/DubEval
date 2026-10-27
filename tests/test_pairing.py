"""Pairing: same video or not, the dub's time shift and coverage, on small synthetic videos made with ffmpeg."""
import subprocess

import numpy as np
import pytest

from dubeval import pairing, pipeline
from dubeval.evaluate import FFMPEG_EXE, SAMPLE_RATE, extract_audio, load_audio
from dubeval.report import build_report
from sample_results import make_results


def _ffmpeg(*args):
    # Single-threaded, bit-exact encoding: the clips are the same bytes on every run, so the tests are repeatable.
    subprocess.run([FFMPEG_EXE, "-nostdin", "-y", "-loglevel", "error", "-threads", "1", *args[:-1],
                    "-threads", "1", "-flags", "+bitexact", "-fflags", "+bitexact", args[-1]], check=True)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    """A 30 s master (evolving picture, background with changing loudness) and clips cut from it, each with its
    own 'voice' tone: the original (master 5-25 s), an aligned dub, a dub that starts 2 s earlier in the master
    (so its content is 2 s later), a dub missing master 12-17 s, and an unrelated video."""
    d = tmp_path_factory.mktemp("clips")
    # The picture: a Mandelbrot zoom blended with a cellular automaton. Each alone repeats itself enough at 32x18 that
    # frames seconds apart can "match" (15% for the automaton), which let tiny decoding differences between CPUs
    # flip the cut test; together no frame 3-8 s apart matches.
    _ffmpeg("-f", "lavfi", "-i", "mandelbrot=size=64x64:rate=25[a];cellauto=rule=110:size=64x64:rate=25,format=rgb0[b];"
            "[a][b]blend=all_mode=average", "-f", "lavfi",
            "-i", "anoisesrc=c=pink:seed=7:d=30,volume='if(lt(random(0),0.4),1,0.05)':eval=frame",
            "-t", "30", "-c:v", "mpeg4", "-c:a", "aac", str(d / "master.mp4"))
    _ffmpeg("-f", "lavfi", "-i", "life=s=64x64:mold=10:r=25:ratio=0.5:seed=3", "-f", "lavfi", "-i", "anoisesrc=c=white:seed=3:d=20",
            "-t", "20", "-c:v", "mpeg4", "-c:a", "aac", str(d / "other.mp4"))

    def clip(name, start, dur, freq):
        _ffmpeg("-ss", str(start), "-t", str(dur), "-i", str(d / "master.mp4"), "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={dur}", "-filter_complex",
                "[0:a][1:a]amix=inputs=2:weights='1 0.3'[a]", "-map", "0:v", "-map", "[a]", "-c:v", "mpeg4",
                "-c:a", "aac", str(d / f"{name}.mp4"))
    clip("orig", 5, 20, 300)
    clip("aligned", 5, 20, 500)
    clip("shifted", 3, 22, 500)
    _ffmpeg("-i", str(d / "master.mp4"), "-filter_complex",
            "[0:v]trim=5:12,setpts=PTS-STARTPTS[v1];[0:v]trim=17:25,setpts=PTS-STARTPTS[v2];"
            "[0:a]atrim=5:12,asetpts=PTS-STARTPTS[a1];[0:a]atrim=17:25,asetpts=PTS-STARTPTS[a2];"
            "[v1][a1][v2][a2]concat=n=2:v=1:a=1[vc][a];[vc]fps=25[v]", "-map", "[v]", "-map", "[a]",
            "-c:v", "mpeg4", "-c:a", "aac", str(d / "cut.mp4"))
    _ffmpeg("-i", str(d / "orig.mp4"), "-vn", "-c:a", "aac", str(d / "orig_audio.m4a"))
    return d


def _pair(clips, dub, original="orig.mp4"):
    y = lambda name: load_audio(extract_audio(str(clips / name), str(clips / (name + ".wav"))))
    return pairing.pair(str(clips / original), str(clips / dub), y(original), y(dub), SAMPLE_RATE, FFMPEG_EXE)


def test_an_aligned_dub_is_the_same_video_with_no_shift(clips):
    r = _pair(clips, "aligned.mp4")
    assert r["same_video"] is True and r["picture_match"] >= 0.9
    assert abs(r["offset_sec"]) <= 0.05 and r["coverage_pct"] == 100.0 and r["missing"] == []


def test_a_shifted_dub_is_found_to_within_a_tenth_of_a_second(clips):
    r = _pair(clips, "shifted.mp4")
    assert r["same_video"] is True and abs(r["offset_sec"] - 2.0) <= 0.1
    assert r["offset_source"].endswith("+sound") and r["steady_offset"] is True


def test_a_cut_dub_reports_the_missing_part(clips):
    r = _pair(clips, "cut.mp4")
    assert r["same_video"] is True and r["steady_offset"] is False
    assert 70 <= r["coverage_pct"] <= 80
    (start, end), = r["missing"]
    assert abs(start - 7.0) <= 0.5 and abs(end - 12.0) <= 0.5


def test_an_unrelated_video_is_different(clips):
    r = _pair(clips, "other.mp4")
    assert r["same_video"] is False and r["picture_match"] < 0.25


def test_without_a_picture_the_sound_decides_and_never_refuses(clips):
    r = _pair(clips, "aligned.mp4", original="orig_audio.m4a")
    assert r["evidence"] == "sound" and r["coverage_pct"] is None and r["same_video"] in (True, None)


def test_a_picture_read_cut_short_is_read_again(monkeypatch):
    # A frame list cut short (ffmpeg failing partway) silently raises the coverage: it is read once more.
    frame = bytes(pairing.FRAME_W * pairing.FRAME_H)

    class Run:
        def __init__(self, frames, code):
            self.stdout, self.returncode, self.stderr = frame * frames, code, b""
    runs = [Run(40, 1), Run(100, 0)]
    monkeypatch.setattr(pairing.subprocess, "run", lambda cmd, **kw: runs.pop(0))
    assert len(pairing.read_frames("a.mp4", 10.0, "ffmpeg", expected=100)) == 100 and not runs

    runs[:] = [Run(60, 0), Run(60, 0), Run(99, 0)]           # two reads that agree are what the file holds
    assert len(pairing.read_frames("a.mp4", 10.0, "ffmpeg", expected=100)) == 60 and len(runs) == 1

    runs[:] = [Run(0, 1)]                                     # no picture at all (an audio file): read once
    assert len(pairing.read_frames("a.m4a", 10.0, "ffmpeg", expected=100)) == 0 and not runs


def test_align_dub_moves_the_dub_onto_the_original_timeline():
    y = np.arange(10, dtype=np.float32)
    assert list(pairing.align_dub(y, 0.3, sr=10)) == [3, 4, 5, 6, 7, 8, 9]
    assert list(pairing.align_dub(y, -0.2, sr=10)[:4]) == [0, 0, 0, 1]


def test_hashes_of_a_file_without_picture_are_empty(clips):
    assert len(pairing.frame_hashes(str(clips / "orig_audio.m4a"), 2.0, FFMPEG_EXE)) == 0


# ---------------- in the pipeline and the report ----------------
def test_different_videos_stop_the_run_unless_allowed(clips, tmp_path, isolated_output, monkeypatch):
    monkeypatch.setattr(pipeline, "run_full_evaluation",
                        lambda **kw: {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")})
    with pytest.raises(ValueError, match="different videos"):
        pipeline.run_files_evaluation(str(clips / "orig.mp4"), str(clips / "other.mp4"), target_lang="ko",
                                      out_dir=str(tmp_path / "a"), use_translation_judge=False)
    r = pipeline.run_files_evaluation(str(clips / "orig.mp4"), str(clips / "other.mp4"), target_lang="ko",
                                      out_dir=str(tmp_path / "b"), use_translation_judge=False, allow_different=True,
                                      report_lang="en")
    same = next(m for s in r["report"]["sections"] for m in s["metrics"] if m["id"] == "same_video")
    assert same["level"] == "poor" and r["report"]["overall"]["level"] == "poor"


def test_the_shift_is_applied_to_the_evaluation(clips, tmp_path, isolated_output, monkeypatch):
    seen = {}

    def fake_eval(**kw):
        seen.update(kw)
        return {k: v for k, v in make_results().items() if k not in ("pipeline", "translation_judge")}
    monkeypatch.setattr(pipeline, "run_full_evaluation", fake_eval)
    r = pipeline.run_files_evaluation(str(clips / "orig.mp4"), str(clips / "shifted.mp4"), target_lang="ko",
                                      out_dir=str(tmp_path / "o"), use_translation_judge=False, report_lang="en")
    assert abs(seen["dub_offset_sec"] - 2.0) <= 0.1 and r["pairing"]["applied_offset_sec"] == seen["dub_offset_sec"]
    shift = next(m for s in r["report"]["sections"] for m in s["metrics"] if m["id"] == "time_shift")
    assert shift["level"] == "info" and "later in the dub" in shift["message"]


@pytest.mark.parametrize("pairing_result, levels", [
    ({"measured": True, "evidence": "picture", "same_video": True, "picture_match": 0.97, "coverage_pct": 100.0,
      "missing": [], "steady_offset": True, "offset_sec": 0.0, "applied_offset_sec": 0.0},
     {"same_video": "good", "time_shift": "info", "coverage": "good"}),
    ({"measured": True, "evidence": "picture", "same_video": True, "picture_match": 0.53, "coverage_pct": 75.0,
      "missing": [[7.0, 12.0]], "steady_offset": False, "offset_sec": -5.0, "applied_offset_sec": -5.0},
     {"same_video": "good", "time_shift": "info", "coverage": "poor"}),
    ({"measured": True, "evidence": "picture", "same_video": None, "picture_match": 0.4, "coverage_pct": 40.0,
      "missing": [], "steady_offset": True, "offset_sec": 0.0, "applied_offset_sec": 0.0},
     {"same_video": "check", "time_shift": "info", "coverage": "poor"}),
    ({"measured": True, "evidence": "sound", "same_video": True, "picture_match": None, "coverage_pct": None,
      "missing": [], "offset_sec": 0.0, "applied_offset_sec": 0.0},
     {"same_video": "good", "time_shift": "info", "coverage": "not_measured"}),
    (pairing.not_measured("error"), {"same_video": "not_measured"}),
])
def test_pairing_is_graded_in_every_language(pairing_result, levels):
    for lang in ("en", "ko", "pt", "es"):
        rep = build_report(make_results(pairing=pairing_result), lang)
        section = rep["sections"][0]
        assert section["id"] == "pairing" and {m["id"]: m["level"] for m in section["metrics"]} == levels
        assert all(m["message"] and "{" not in m["message"] for m in section["metrics"])


def test_a_missing_part_becomes_a_problem_interval():
    pr = {"measured": True, "evidence": "picture", "same_video": True, "picture_match": 0.53, "coverage_pct": 75.0,
          "missing": [[7.0, 12.0]], "steady_offset": False, "offset_sec": -5.0, "applied_offset_sec": -5.0}
    rep = build_report(make_results(pairing=pr), "en")
    gap = [i for i in rep["problem_intervals"] if i["category"] == "missing_in_dub"]
    assert gap and gap[0]["start"] == 7.0 and gap[0]["end"] == 12.0 and gap[0]["severity"] == "poor"


def test_results_without_pairing_have_no_pairing_section():
    assert all(s["id"] != "pairing" for s in build_report(make_results(), "en")["sections"])


def test_a_cut_dub_is_laid_onto_the_original_part_by_part():
    y = np.arange(1, 11, dtype=np.float32)                   # dub: original 0-4 s, then (original 6-10 s)
    parts = [{"start": 0.0, "end": 4.0, "offset_sec": 0.0}, {"start": 6.0, "end": 10.0, "offset_sec": -2.0}]
    assert list(pairing.align_dub_parts(y, parts, sr=1, length=10)) == [1, 2, 3, 4, 0, 0, 5, 6, 7, 8]


def test_a_dub_with_several_parts_says_each_was_corrected():
    pr = {"measured": True, "evidence": "picture", "same_video": True, "picture_match": 1.0, "coverage_pct": 95.0,
          "missing": [[40.1, 45.1]], "steady_offset": False, "offset_sec": -5.0, "applied_offset_sec": -5.0,
          "applied_parts": True, "parts": [{"start": 0.0, "end": 40.1, "offset_sec": 0.0},
                                           {"start": 45.1, "end": 95.7, "offset_sec": -5.0}]}
    for lang in ("en", "ko", "pt", "es"):
        shift = next(m for m in build_report(make_results(pairing=pr), lang)["sections"][0]["metrics"]
                     if m["id"] == "time_shift")
        assert "+0.00, -5.00" in shift["message"] and "{" not in shift["display"]


def test_a_clip_shorter_than_one_matching_window_is_paired(clips):
    """A real 7 s short crashed the motion matching once (a window ran past the video's end)."""
    _ffmpeg("-t", "5", "-i", str(clips / "orig.mp4"), "-c", "copy", str(clips / "short_o.mp4"))
    _ffmpeg("-t", "5", "-i", str(clips / "aligned.mp4"), "-c", "copy", str(clips / "short_d.mp4"))
    r = _pair(clips, "short_d.mp4", original="short_o.mp4")
    assert r["measured"] and r["same_video"] is True and abs(r["offset_sec"]) <= 0.1


def test_motion_correlation_never_fails_on_uneven_lengths():
    a, b = np.random.default_rng(0).normal(size=37), np.random.default_rng(1).normal(size=60)
    for lag in range(-30, 31):
        pairing._ncc(a, b, lag, 0, 80, 5)                     # a window longer than the signal


def test_both_videos_are_read_at_the_same_time(monkeypatch):
    """The two decodes run side by side: together they take about as long as one."""
    import threading
    import time
    from dubeval import pairing
    running, peak = [0], [0]
    lock = threading.Lock()

    def slow_read(path, fps, ffmpeg, expected=0):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.2)
        with lock:
            running[0] -= 1
        return np.zeros((3, pairing.FRAME_H, pairing.FRAME_W)) if path == "a" else np.ones((2, pairing.FRAME_H, pairing.FRAME_W))
    monkeypatch.setattr(pairing, "read_frames", slow_read)
    fa, fb = pairing.read_both("a", "b", 5.0, "ffmpeg")
    assert peak[0] == 2 and len(fa) == 3 and len(fb) == 2          # order kept: original first


def test_the_check_reports_its_steps(monkeypatch):
    from dubeval import pairing
    monkeypatch.setattr(pairing, "read_both", lambda *a: (np.zeros((0, 1, 1)), np.zeros((0, 1, 1))))
    seen = []
    y = np.zeros(16000 * 4, dtype=np.float32)
    pairing.pair("a", "b", y, y, 16000, "ffmpeg", progress=lambda message, fraction: seen.append(message))
    assert seen == ["Reading the picture of both videos...", "Matching the two videos..."]
