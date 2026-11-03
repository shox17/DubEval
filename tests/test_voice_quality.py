"""Tests for voice quality: windows where both tracks speak, grading against the original, and its intervals."""
import numpy as np
import pytest

from dubeval import voice_quality as vq
from dubeval.i18n import t
from dubeval.intervals import build_intervals
from dubeval.report import build_report
from sample_results import make_results

SR = vq.SAMPLE_RATE


class FakeSession:
    """Stands in for the ONNX model: louder audio gets a higher raw speech score; records input shapes."""
    def __init__(self):
        self.shapes = []

    def run(self, _outputs, feeds):
        x = feeds["input_1"]
        self.shapes.append(x.shape)
        level = float(np.abs(x).mean())
        return [np.array([[1.0 + 30 * level, 3.0, 1.0 + 20 * level]], dtype=np.float32)]


def metric(rep: dict, mid: str) -> dict:
    """The report row with this id."""
    return next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == mid)


def test_only_windows_where_both_tracks_speak_are_compared():
    session = FakeSession()
    orig, dub = np.full(SR * 30, 0.05, dtype=np.float32), np.full(SR * 30, 0.02, dtype=np.float32)
    dub[::2] = 0.0                                  # at the same volume, the gaps score lower with FakeSession
    result = vq.voice_quality(orig, dub, [[0.0, 12.0]], [[0.0, 30.0]], session=session)
    assert result["measured"] and all(w["start"] <= 9.0 for w in result["windows"])   # ≥ 3 s of original speech
    assert result["difference"] < 0 and result["dub"] < result["original"]
    assert all(w["dub_sig"] < w["original_sig"] for w in result["windows"])
    assert all(shape == (1, int(vq.WINDOW_SEC * SR)) for shape in session.shapes)
    none = vq.voice_quality(orig, dub, [[0.0, 2.0]], [[20.0, 30.0]], session=session)
    assert not none["measured"] and none["reason_key"] == "r.vq.no_common_speech"


def test_short_audio_is_tiled_to_the_model_input():
    session = FakeSession()
    vq.score_window(np.full(SR * 2, 0.1, dtype=np.float32), session)
    vq.score_window(np.array([], dtype=np.float32), session)
    assert session.shapes == [(1, int(vq.WINDOW_SEC * SR))] * 2


def test_the_real_model_scores_on_the_listener_scale():
    t_ = np.arange(SR * 10) / SR
    voiced = (0.3 * np.sin(2 * np.pi * 180 * t_) * (1 + np.sin(2 * np.pi * 3 * t_))).astype(np.float32)
    sig, bak, ovr = vq.score_window(voiced)
    assert all(1.0 <= x <= 5.0 for x in (sig, bak, ovr))


def window(start, dub_sig, orig_sig, dub, orig):
    """One scored window: speech (SIG) and overall (OVRL) scores of the dub and the original."""
    return {"start": start, "end": start + 9.01, "dub_sig": dub_sig, "original_sig": orig_sig, "dub": dub,
            "original": orig}


def vq_result(*windows) -> dict:
    """A measured voice-quality result with these windows."""
    dub = sum(w["dub"] for w in windows) / len(windows)
    orig = sum(w["original"] for w in windows) / len(windows)
    return {"measured": True, "dub": round(dub, 2), "original": round(orig, 2), "difference": round(dub - orig, 2),
            "windows": list(windows)}


@pytest.mark.parametrize("dub_sig, dub, level", [
    (3.4, 2.5, "good"),            # a clean dub, a little above the original (real Perso dubs)
    (2.7, 2.3, "good"),            # 0.5 below on the voice, 0 overall: still inside normal variation
    (2.5, 2.3, "check"),           # voice 0.7 below: a slightly robotic stretch
    (3.2, 1.7, "check"),           # whole sound 0.6 below: distortion the model books under background
    (2.1, 2.2, "check"),           # voice 1.1 below: Poor until 2026-11-01; graded real dubs reached 2.2 and were fine
    (3.2, 1.3, "check"),           # whole sound 1.0 below
    (0.6, 2.2, "poor"),            # voice 2.6 below: past anything a person accepted
    (3.2, 0.7, "poor"),            # whole sound 1.6 below
])
def test_each_stretch_is_graded_on_voice_or_whole_sound_drop(dub_sig, dub, level):
    r = make_results(voice_quality=vq_result(window(0.0, 3.2, 3.2, 2.3, 2.3), window(10.0, dub_sig, 3.2, dub, 2.3)))
    row = metric(build_report(r), "voice_quality")
    assert row["level"] == level and row["thresholds"]
    assert ("1/2" in row["display"]) == (level != "good")


def test_voice_quality_is_not_measured_with_a_reason():
    noisy = make_results(voice_quality=vq_result(window(0.0, 1.3, 1.2, 1.2, 1.1)))
    row = metric(build_report(noisy), "voice_quality")
    assert row["level"] == "not_measured" and "can't serve as a reference" in row["message"]
    old = make_results()
    del old["voice_quality"]
    row = metric(build_report(old), "voice_quality")
    assert row["level"] == "not_measured" and "Run the evaluation again" in row["message"]
    failed = make_results(voice_quality=vq.not_measured("r.vq.error"))
    assert "couldn't run" in metric(build_report(failed), "voice_quality")["message"]


def test_stretches_with_a_worse_voice_become_intervals():
    r = make_results(timing_alignment={"mismatches": []}, acoustic_metrics={"dubbed_duration_sec": 40.0},
                     voice_quality=vq_result(window(0.0, 3.3, 3.2, 2.4, 2.3), window(12.0, 2.5, 3.2, 2.3, 2.3),
                                             window(24.0, 3.2, 3.2, 0.7, 2.3)))
    out = build_intervals(r, lambda key, **p: t(key, "en", **p), "en")["intervals"]
    assert [(i["start"], i["category"], i["severity"]) for i in out] == [
        (12.0, "voice_quality", "check"), (24.0, "voice_quality", "poor")]
    assert "robotic" in out[0]["description"] and out[0]["check_label"] == "Voice quality"


def test_volume_alone_doesnt_change_the_score():
    # The model's scores move with volume, and volume has its own checks: a copy only 3 dB quieter got "a worse voice".
    y = 0.2 * np.random.default_rng(1).standard_normal(20 * SR).astype(np.float32)
    speech = [[0.0, 20.0]]
    same = vq.voice_quality(y, y, speech, speech, FakeSession())["windows"]
    for gain in (0.7, 1.5):
        other = vq.voice_quality(y, y * gain, speech, speech, FakeSession())["windows"]
        assert [w["dub_sig"] for w in other] == pytest.approx([w["dub_sig"] for w in same], abs=0.02)
        assert [w["original"] for w in other] == [w["original"] for w in same]      # the original is never touched


def test_matching_the_volume_never_clips_or_divides_by_silence():
    quiet = 0.01 * np.random.default_rng(2).standard_normal(SR)
    quiet = np.clip(quiet, -0.05, 0.05)
    quiet[100] = 0.9
    louder = vq._at_volume_of(quiet, np.full(SR, 0.5))
    assert np.max(np.abs(louder)) == pytest.approx(1.0)         # stopped at full scale, short of the original's volume
    silent = np.zeros(SR)
    assert np.array_equal(vq._at_volume_of(silent, quiet), silent)
    assert np.array_equal(vq._at_volume_of(quiet, silent), quiet)


def test_a_stretch_too_noisy_to_compare_isnt_held_against_the_dub():
    # Scores this low jump with any small change (a real one: 1.86 to 1.36 for 2.3 dB). A clean stretch still counts.
    r = make_results(timing_alignment={"mismatches": []}, acoustic_metrics={"dubbed_duration_sec": 40.0},
                     voice_quality=vq_result(window(0.0, 1.4, 2.1, 1.1, 1.4), window(12.0, 2.5, 3.2, 2.3, 2.3)))
    rep = build_report(r)
    assert [(i["start"], i["category"]) for i in rep["problem_intervals"] if i["category"] == "voice_quality"] == [
        (12.0, "voice_quality")]
    assert metric(rep, "voice_quality")["level"] == "check"
    too_noisy = make_results(voice_quality=vq_result(window(0.0, 1.4, 2.1, 1.1, 1.4)))
    assert metric(build_report(too_noisy), "voice_quality")["level"] == "not_measured"
