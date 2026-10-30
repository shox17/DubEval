"""Tests for the lip-sync check (dubeval/lip_sync.py): preparation, the decision on top of the model's answers, the
report line, and the bundled graphs. The model itself never runs here (its 1.6 GB pack is never downloaded)."""
import re

import numpy as np
import pytest

from dubeval import lip_sync as ls
from dubeval import packs
from dubeval.report import build_report
from sample_results import JUDGED, make_results


def metric(rep: dict, mid: str) -> dict:
    """The report row with this id."""
    return next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == mid)


def test_points_on_the_template_need_no_warping():
    m, bias = ls.align(ls.TEMPLATE, None)
    assert np.allclose(m, [[1, 0, 0], [0, 1, 0]], atol=1e-9) and np.allclose(bias, 0, atol=1e-9)


def test_alignment_undoes_a_moved_scaled_face_and_smooths_the_nose_offset():
    # The same three points, twice the size and moved: the transform maps them back onto the template.
    moved = ls.TEMPLATE * 2 + [300, 120]
    m, _ = ls.align(moved, None)
    back = np.c_[moved, np.ones(3)] @ m.T
    assert np.allclose(back, ls.TEMPLATE, atol=1e-6)
    # A nose that isn't where the template expects gets an offset, blended 0.2/0.8 with the previous frame's.
    skew = moved + [[0, 0], [0, 0], [6, 0]]
    _, first = ls.align(skew, None)
    _, second = ls.align(skew, np.zeros(2))
    assert np.allclose(second, first * 0.8)


def test_mel_has_80_bands_at_80_frames_a_second_in_minus_4_to_4():
    y = np.sin(2 * np.pi * 220 * np.arange(32000) / 16000).astype(np.float32)
    spec = ls.mel(y)
    assert spec.shape[0] == 80 and abs(spec.shape[1] - 160) <= 1 and spec.min() >= -4 and spec.max() <= 4


def test_the_typical_shift_is_where_most_moments_agree():
    assert ls.typical_shift([2, 2, 3, 1, 2, -9, 14]) == 2
    assert ls.typical_shift([5, 5, 6, 7, 6]) == 6           # tied windows: the cluster's middle, not its edge
    assert ls.typical_shift([]) == 0


def test_moments_are_taken_where_both_tracks_speak_and_spread_out():
    starts = ls.pick_moments([[0.0, 30.0]], [[0.0, 10.0], [20.0, 30.0]], 30.0)
    assert starts and not any(10.2 < s / ls.FPS < 19.8 for s in starts)    # none in the dub's silence
    assert all(b - a >= ls.FRAMES for a, b in zip(starts, starts[1:]))       # separate moments
    long = ls.pick_moments([[0.0, 600.0]], [[0.0, 600.0]], 600.0)
    assert len(long) == 3 * ls.MAX_MOMENTS and long[-1] / ls.FPS < ls.MAX_SECONDS
    assert ls._spread(list(range(10)), 5) == [0, 2, 4, 6, 8]


def fake_model(monkeypatch, orig_shift, dub_shift, faces=True):
    """Stands in for face finding and the model: each moment's best shift comes from orig_shift(s) / dub_shift(s)."""
    monkeypatch.setattr(ls, "face_seen", lambda video, ks, check=None: set(ks) if faces else set())
    monkeypatch.setattr(ls, "lower_faces", lambda video, starts, check=None: {s: video for s in starts})
    monkeypatch.setattr(ls, "best_shifts", lambda faces_, y, check=None:
                        {s: ((orig_shift if v == "orig.mp4" else dub_shift)(s), 0.8) for s, v in faces_.items()})


def run(**kw):
    return ls.lip_sync("orig.mp4", None, [[0.0, 60.0]], "dub.mp4", None, [[0.0, 60.0]], 60.0, **kw)


def test_a_dub_whose_lips_line_up_like_the_original_is_measured_against_the_original(monkeypatch):
    fake_model(monkeypatch, lambda s: 2, lambda s: 2 if s % 3 else 3)       # the file's own +2 frames cancels out
    r = run()
    assert r["measured"] and r["moments"] == ls.MAX_MOMENTS
    assert r["original_match_pct"] == 100 and r["dub_match_pct"] == 100 and r["dub_offset_ms"] == 0
    assert {m["original"] for m in r["timeline"]} == {0} and all(m["dub_lines_up"] for m in r["timeline"])


def test_scattered_lips_dont_line_up_and_get_no_offset(monkeypatch):
    rng = np.random.default_rng(0)
    scatter = {}
    fake_model(monkeypatch, lambda s: 2, lambda s: scatter.setdefault(s, int(rng.integers(-15, 16))))
    r = run()
    assert r["measured"] and r["dub_match_pct"] < 40 and r["dub_offset_ms"] is None


def test_lips_that_follow_late_sound_give_its_delay(monkeypatch):
    fake_model(monkeypatch, lambda s: 2, lambda s: 7)                       # 5 frames late = 0.2 s
    r = run()
    assert r["dub_match_pct"] == 0 and r["dub_offset_ms"] == 200


def test_not_measured_without_faces_or_when_the_original_voice_isnt_on_screen(monkeypatch):
    fake_model(monkeypatch, lambda s: 2, lambda s: 2, faces=False)
    assert run()["reason_key"] == "r.sync_lips.few_moments"
    fake_model(monkeypatch, lambda s: (s * 7) % 31 - 15, lambda s: 2)       # a narrator: the original scatters
    r = run()
    assert not r["measured"] and r["reason_key"] == "r.sync_lips.original_off"


def test_the_pack_is_not_installed_in_tests_and_a_failure_is_not_measured(monkeypatch):
    from dubeval import evaluate
    assert not ls.ready() and not evaluate._lip_sync_ready()
    monkeypatch.setattr(ls, "lip_sync", lambda *a, **k: (_ for _ in ()).throw(ValueError("video could not be opened")))
    assert evaluate._lip_sync("a", None, [], "b", None, [], 10.0)["reason_key"] == "r.sync_lips.error"

    class Stop(RuntimeError):
        pass

    def check():
        raise Stop()
    with pytest.raises(Stop):                                               # Stop goes through, never "not measured"
        evaluate._lip_sync("a", None, [], "b", None, [], 10.0, check)


SYNC = {"measured": True, "moments": 30, "original_match": 28, "dub_match": 26, "original_match_pct": 93,
        "dub_match_pct": 87, "dub_offset_ms": 0, "dub_offset_match_pct": 87, "timeline": []}


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_the_report_shows_the_lip_sync_line_instead_of_lip_movement_and_never_grades_it(lang):
    results = make_results(translation_judge=JUDGED)
    results["lipsync_metrics"]["sync"] = SYNC
    rep = build_report(results, lang)
    row = metric(rep, "lip_sync")
    assert row["level"] == "info" and row["value"] == 87 and "26" in row["message"] and "28" in row["message"]
    assert row["thresholds"] and "30" in row["thresholds"]
    assert not any(m["id"] == "lip_movement" for s in rep["sections"] for m in s["metrics"])
    section = next(s for s in rep["sections"] if s["id"] == "lipsync")
    assert section["title"] == {"en": "Lip sync", "ko": "립싱크", "pt": "Sincronia labial", "es": "Sincronía labial"}[lang]
    assert rep["overall"]["level"] == "good"


def test_the_report_says_when_the_sound_is_off_and_why_it_wasnt_measured():
    results = make_results(translation_judge=JUDGED)
    results["lipsync_metrics"]["sync"] = {**SYNC, "dub_match": 0, "dub_match_pct": 0, "dub_offset_ms": 200}
    assert "0.20 s after" in metric(build_report(results), "lip_sync")["message"]
    results["lipsync_metrics"]["sync"] = {**SYNC, "dub_offset_ms": -480}
    assert "0.48 s before" in metric(build_report(results), "lip_sync")["message"]
    results["lipsync_metrics"]["sync"] = ls.not_measured("r.sync_lips.original_off", pct="20%")
    row = metric(build_report(results), "lip_sync")
    assert row["level"] == "not_measured" and "20%" in row["message"] and "narrator" in row["message"]


def test_without_the_pack_lip_movement_points_to_the_download():
    row = metric(build_report(make_results(translation_judge=JUDGED)), "lip_movement")
    assert "Settings → Models" in row["message"]


def test_the_pack_is_ByteDances_file_pinned_to_a_revision():
    pack = packs.PACKS["lip_sync"]
    (f,) = pack["files"]
    assert re.search(r"/ByteDance/LatentSync-1\.5/resolve/[0-9a-f]{40}/stable_syncnet\.pt$", f["url"])
    assert f["name"] == ls.CHECKPOINT and f["bytes"] == 1605324224 and len(f["sha256"]) == 64
    assert "OpenRAIL" in pack["license"] and pack["folder"]() == ls.PACK_DIR


def test_the_bundled_graphs_hold_no_weights_and_read_them_from_the_checkpoint():
    onnx = pytest.importorskip("onnx")
    size = packs.PACKS["lip_sync"]["files"][0]["bytes"]
    for name, shape in ((ls.AUDIO_GRAPH, ls.AUDIO_SHAPE), (ls.VISUAL_GRAPH, ls.VISUAL_SHAPE)):
        path = ls.GRAPHS_DIR / name
        assert path.stat().st_size < 500_000
        graph = onnx.load(str(path), load_external_data=False)
        dims = [d.dim_value for d in graph.graph.input[0].type.tensor_type.shape.dim][1:]
        assert dims == list(shape)
        for init in graph.graph.initializer:
            info = {e.key: e.value for e in init.external_data}
            assert init.data_location == onnx.TensorProto.EXTERNAL and info["location"] == ls.CHECKPOINT
            assert int(info["offset"]) + int(info["length"]) <= size


def test_a_dub_that_starts_later_is_read_at_its_own_moments(monkeypatch):
    seen = {}
    monkeypatch.setattr(ls, "face_seen", lambda video, ks, check=None: set(ks))
    monkeypatch.setattr(ls, "lower_faces", lambda video, starts, check=None: {s: video for s in starts})

    def shifts(faces_, y, check=None):
        seen[next(iter(faces_.values()))] = sorted(faces_)
        return {s: (2, 0.8) for s in faces_}
    monkeypatch.setattr(ls, "best_shifts", shifts)
    r = run(dub_offset_sec=0.4)                               # the dub's picture and sound come 0.4 s (10 frames) later
    assert r["measured"] and r["dub_match_pct"] == 100 and r["dub_offset_ms"] == 0
    assert [s + 10 for s in seen["orig.mp4"]] == seen["dub.mp4"]


def test_only_the_sound_the_moments_use_becomes_a_spectrogram(monkeypatch):
    lengths = []
    monkeypatch.setattr(ls, "mel", lambda y: (lengths.append(len(y)), np.zeros((80, 0), np.float32))[1])

    class Encoder:
        def run(self, _, feeds):
            return [np.zeros((len(feeds["x"]), 4), np.float32)]
    monkeypatch.setattr(ls, "_models", lambda: (Encoder(), Encoder()))
    faces = {100: np.zeros((ls.FRAMES, 128, 256, 3), np.uint8)}
    ls.best_shifts(faces, np.zeros(16000 * 600, dtype=np.float32))     # a 10-minute track; the moment is at 4 s
    assert lengths and lengths[0] <= 16000 * 7
