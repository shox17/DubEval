"""Tests for the audio measurements: duration, silence, loudness and volume steadiness."""
import numpy as np
import pytest

from dubeval.evaluate import analyze_acoustics, SAMPLE_RATE


def tone(seconds: float, amp: float = 0.5) -> np.ndarray:
    """A 220 Hz sine wave of the given length, used as fake speech."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def test_duration_and_silence_ratio():
    y = np.concatenate([tone(1.0), np.zeros(SAMPLE_RATE, dtype=np.float32)])
    a = analyze_acoustics(y)
    assert a["duration_sec"] == 2.0
    assert 40.0 <= a["silence_ratio_pct"] <= 60.0


def test_steady_tone_is_stable_and_not_silent():
    a = analyze_acoustics(tone(2.0))
    assert a["silence_ratio_pct"] < 5.0
    assert a["volume_stability_pct"] > 90.0
    assert abs(a["mean_rms_energy"] - 0.5 / np.sqrt(2)) < 0.01


def test_pure_silence_does_not_crash():
    a = analyze_acoustics(np.zeros(SAMPLE_RATE, dtype=np.float32))
    assert a["mean_rms_energy"] == 0.0
    assert a["volume_stability_pct"] == 0.0
    assert a["silence_ratio_pct"] == 100.0


def test_clipping_intervals_group_clipped_samples():
    from dubeval.evaluate import clipping_intervals
    y = np.zeros(16000 * 10, dtype=np.float32)
    y[16000 * 2:16000 * 2 + 100] = 1.0            # 2.0 s
    y[int(16000 * 2.3)] = -1.0                     # 0.3 s later: same interval
    y[16000 * 7] = 1.0                             # far away: its own interval
    assert clipping_intervals(y) == [[2.0, 2.3], [7.0, 7.0]]
    assert clipping_intervals(np.zeros(100, dtype=np.float32)) == []


def test_language_windows_skip_silence_and_report_each_window(monkeypatch):
    from dubeval import evaluate
    seen = []

    def fake_probs(chunk, model):
        """English for the second window, Korean otherwise."""
        seen.append(len(chunk))
        return {"ko": 0.1, "en": 0.9} if len(seen) == 2 else {"ko": 0.95, "en": 0.05}
    monkeypatch.setattr(evaluate, "_language_probs", fake_probs)
    y = np.zeros(16000 * 35, dtype=np.float32)
    speech = [[0.0, 9.0], [10.5, 19.0], [31.0, 31.5]]              # last window has only 0.5 s of speech
    out = evaluate.language_windows(y, None, speech, "ko")
    assert [(w["start"], w["end"], w["language"]) for w in out] == [(0.0, 10.0, "ko"), (10.0, 20.0, "en")]
    assert out[1]["expected_probability"] == 0.1 and seen == [160000, 160000]
    assert evaluate.language_windows(y, None, speech, None) == []   # no Whisper model for the language


def test_language_windows_count_overlapping_speech_once(monkeypatch):
    from dubeval import evaluate
    monkeypatch.setattr(evaluate, "_language_probs", lambda chunk, model: {"ko": 0.9, "en": 0.1})
    y = np.zeros(16000 * 10, dtype=np.float32)
    # Original and dub speak over the same 2 s: 2 s of speech, not 4, so the window is skipped.
    assert evaluate.language_windows(y, None, [[1.0, 3.0], [1.0, 3.0]], "ko") == []
    assert len(evaluate.language_windows(y, None, [[1.0, 3.0], [2.5, 5.0]], "ko")) == 1


def test_opencv_gets_an_ascii_path_on_windows(monkeypatch, tmp_path):
    import os
    from dubeval.evaluate import _cv2_path
    folder = tmp_path / "사용자" / "a"
    folder.mkdir(parents=True)
    video = str(folder / "v.mp4")
    assert _cv2_path(video) == video                          # macOS / Linux: unchanged
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.chdir(tmp_path / "사용자")
    assert _cv2_path(video) == os.path.join("a", "v.mp4")     # relative path is plain ASCII


def test_transcription_is_repeatable_despite_whisper_sampling():
    torch = pytest.importorskip("torch", reason="the original Whisper's seeding; the runtime has no PyTorch")
    from dubeval.evaluate import transcribe

    class SamplingModel:
        """Stands in for Whisper's temperature fallback: the output depends on torch's random numbers."""
        def transcribe(self, y, **kw):
            t = round(float(torch.rand(1)), 4)
            return {"text": str(t), "language": "en",
                    "segments": [{"start": 0.0, "end": t, "text": str(t), "avg_logprob": -0.1, "no_speech_prob": 0.0}]}
    y = np.zeros(1600, dtype=np.float32)
    before = torch.rand(1)                               # the caller's random stream isn't reset by transcribe
    assert transcribe(y, SamplingModel()) == transcribe(y, SamplingModel())
    torch.manual_seed(123)
    expected = torch.rand(1)
    torch.manual_seed(123)
    transcribe(y, SamplingModel())
    assert torch.equal(torch.rand(1), expected) and before is not None
