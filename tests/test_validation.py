"""Validation with known problems: where problems are put, what counts as caught or as a false alarm, the splits."""
import numpy as np

from dubeval import validation as v

SR = 1000


def _speech(seconds=30.0, quiet=()):
    """A steady 'voice' at SR samples per second, silent in the given (start, end) ranges."""
    y = 0.3 * np.sin(np.arange(int(seconds * SR)) * 0.3).astype(np.float32)
    for a, b in quiet:
        y[int(a * SR):int(b * SR)] = 0.0
    return y


def test_a_problem_is_put_where_the_dub_is_speaking_and_always_the_same_place():
    active = v.speech_mask([[0, 30]], [[0, 10], [20, 30]], 30)                # the dub says nothing from 10 to 20 s
    start = v.speech_window(active, 3.0, "p001:silence_3s")
    assert start is not None
    assert not (10 - 3 * 0.2 < start < 20 - 3 * 0.8)                         # at most 20% of it in the gap
    assert 0.15 * 30 <= start <= 0.85 * 30 - 3
    assert v.speech_window(active, 3.0, "p001:silence_3s") == start
    assert v.speech_window(v.speech_mask([[0, 4]], [[0, 4]], 4), 3.0, "x") is None   # too short to hold it in the middle


def test_a_problem_is_only_put_where_the_original_speaks_too():
    active = v.speech_mask([[15, 30]], [[0, 30]], 30)                         # the original is quiet until 15 s
    start = v.speech_window(active, 3.0, "p001:silence_3s")
    assert start is not None and start >= 15 - 3 * 0.2
    assert v.speech_window(v.speech_mask([], [[0, 30]], 30), 3.0, "x") is None   # music alone is not speech


def test_a_problem_is_kept_away_from_what_the_control_already_flags():
    active = v.speech_mask([[0, 30]], [[0, 30]], 30)
    for seed in ("a", "b", "c", "d", "e"):
        start = v.speech_window(active, 3.0, seed, blocked=[(8, 16)])
        assert start + 3 + v.TOLERANCE_SEC < 8 or start - v.TOLERANCE_SEC > 16
    assert v.speech_window(active, 3.0, "x", blocked=[(0, 30)]) is None


def test_a_shifted_or_recut_dub_gets_the_problem_at_the_same_moment_of_the_dub():
    assert v.dub_time(10.0, 3.0, None) == 10.0
    assert v.dub_time(10.0, 3.0, {"applied_offset_sec": 1.5}) == 11.5                      # the dub starts later
    recut = {"applied_parts": True, "parts": [{"start": 0, "end": 20, "offset_sec": 15.0},
                                              {"start": 20, "end": 40, "offset_sec": -20.0}]}
    assert v.dub_time(5.0, 3.0, recut) == 20.0 and v.dub_time(25.0, 3.0, recut) == 5.0
    assert v.dub_time(18.5, 3.0, recut) is None                                            # spans two pieces
    active = v.speech_mask([[0, 40]], [[0, 40]], 40)
    for seed in "abcdef":
        start = v.speech_window(active, 3.0, seed, pairing=recut)
        assert v.dub_time(start, 3.0, recut) is not None


def test_the_original_voice_is_taken_from_the_original_moment():
    dub, original = np.zeros(30 * SR, dtype=np.float32), np.zeros(30 * SR, dtype=np.float32)
    original[20 * SR:28 * SR] = 0.5
    out = v.apply_defect("original_voice_8s", dub, SR, 5.0, original=original, original_start=20.0)
    assert np.allclose(out[5 * SR:13 * SR], 0.5) and not out[:5 * SR].any() and not out[13 * SR:].any()


def test_each_known_problem_changes_only_its_stretch():
    y = _speech()
    silent = v.apply_defect("silence_3s", y, SR, 10.0)
    assert np.all(silent[10 * SR:13 * SR] == 0) and np.array_equal(silent[:10 * SR], y[:10 * SR])
    assert len(v.apply_defect("cut_4s", y, SR, 10.0)) == len(y) - 4 * SR
    other = np.full_like(y, 0.05)
    voice = v.apply_defect("original_voice_8s", y, SR, 5.0, original=other)
    assert np.allclose(voice[5 * SR:13 * SR], 0.05) and np.array_equal(voice[14 * SR:], y[14 * SR:])
    assert np.max(np.abs(v.apply_defect("distortion_3s", y, SR, 10.0)[10 * SR:13 * SR])) == 1.0
    assert np.allclose(v.apply_defect("quieter_3db", y, SR, None), y * 10 ** (-3 / 20))
    late = v.apply_defect("sound_late_1s", y, SR, 0.0)
    assert len(late) == len(y) and np.all(late[:SR] == 0) and np.array_equal(late[SR:], y[:-SR])


def _iv(category, start, end, severity="check"):
    return {"category": category, "start": start, "end": end, "severity": severity}


def test_a_new_problem_of_the_right_kind_at_the_right_place_is_caught():
    control = [_iv("line_length", 2, 3)]
    variant = control + [_iv("long_silence", 10.5, 13.0, "poor")]
    r = v.score("silence_3s", 10.0, control, variant)
    assert r["caught"] is True and r["false_alarms"] == []


def test_what_the_dub_already_had_cancels_out_and_new_problems_elsewhere_are_false_alarms():
    control = [_iv("long_silence", 10, 13)]                                  # already there before the change
    variant = control + [_iv("line_length", 25, 26)]
    r = v.score("silence_3s", 10.0, control, variant)
    assert r["caught"] is False and [iv["category"] for iv in r["false_alarms"]] == ["line_length"]


def test_a_new_problem_of_another_kind_at_the_place_is_neither_caught_nor_a_false_alarm():
    r = v.score("distortion_3s", 10.0, [], [_iv("voice_quality", 10, 12)])
    assert r["caught"] is False and r["false_alarms"] == [] and len(r["new"]) == 1


def test_a_whole_dub_problem_is_caught_anywhere():
    r = v.score("sound_late_1s", 0.0, [], [_iv("timing_mismatch", 40, 41)])
    assert r["caught"] is True and r["false_alarms"] == []


def test_any_new_problem_on_the_harmless_copy_is_a_false_alarm():
    r = v.score("quieter_3db", None, [], [_iv("loudness_jump", 4, 6)])
    assert r["caught"] is None and len(r["false_alarms"]) == 1


def test_dubs_of_one_original_video_are_always_in_the_same_split():
    a = v.split_of({}, r"C:\videos\talk.mp4")
    assert v.split_of({}, r"D:\other\folder\TALK.mp4") == a                  # by the original's file name
    assert v.split_of({"split": "holdout"}, r"C:\videos\talk.mp4") == "holdout"
    names = [f"video{i}.mp4" for i in range(200)]
    held = sum(v.split_of({}, n) == "holdout" for n in names)
    assert 25 <= held <= 75                                                   # about one in HOLDOUT_SHARE


def test_a_video_file_is_split_by_its_content_not_its_name(tmp_path):
    first = tmp_path / "p1" / "original.mp4"
    copy = tmp_path / "elsewhere" / "talk.mp4"
    for path in (first, copy):
        path.parent.mkdir()
        path.write_bytes(b"the same video")
    assert v.split_of({}, str(first)) == v.split_of({}, str(copy))
    parts = set()
    for i in range(40):                             # different videos all named original.mp4 still land on both sides
        path = tmp_path / f"v{i}" / "original.mp4"
        path.parent.mkdir()
        path.write_bytes(f"video {i}".encode())
        parts.add(v.split_of({}, str(path)))
    assert parts == {"tune", "holdout"}


def test_the_summary_counts_per_language_and_never_hides_misses():
    runs = [{"pair_id": "p1", "languages": "en>ko", "defect": "silence_3s", "start": 5.0, "caught": True,
             "false_alarms": [], "new": [_iv("long_silence", 5, 8)]},
            {"pair_id": "p2", "languages": "en>ko", "defect": "silence_3s", "start": 9.0, "caught": False,
             "false_alarms": [_iv("line_length", 20, 21)], "new": [_iv("line_length", 20, 21)]},
            {"pair_id": "p2", "languages": "en>ko", "defect": "quieter_3db", "start": None, "caught": None,
             "false_alarms": [], "new": []},
            {"pair_id": "p3", "languages": "en>uz", "defect": "cut_4s", "error": "no stretch of speech long enough"}]
    rows = {(t["languages"], t["defect"]): t for t in v.summarize(runs)["rows"]}
    assert rows[("en>ko", "silence_3s")] == {"languages": "en>ko", "defect": "silence_3s", "tried": 2, "caught": 1,
                                             "false_alarms": 1, "runs_with_false_alarms": 1}
    assert ("en>uz", "cut_4s") not in rows
    text = v.render_text(v.summarize(runs), runs)
    assert "1/2" in text and "p2 silence_3s at 9.0 s" in text and "line_length 1" in text


def test_one_copy_that_cant_be_made_doesnt_lose_the_others(tmp_path, monkeypatch):
    from dubeval import validation
    monkeypatch.setattr(validation, "extract_audio", lambda path, out: out)
    monkeypatch.setattr(validation, "load_audio", lambda path: np.zeros(16000 * 30, dtype=np.float32))

    def write(dub, audio, out, cut=None):
        if out.stem == "sound_late_1s":
            raise RuntimeError("ffmpeg failed")
        return out
    monkeypatch.setattr(validation, "write_variant", write)
    made = validation.make_variants("p001", "o.mp4", "d.mp4", tmp_path, ["sound_late_1s", "quieter_3db"],
                                    [], [], None)
    assert made["sound_late_1s"]["path"] is None and "ffmpeg failed" in made["sound_late_1s"]["skipped"]
    assert made["quieter_3db"]["path"]
