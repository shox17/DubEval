"""Stop: it takes effect inside the long steps (each recognized line, each lip-movement frame, each language window),
abandons a translation check that is still waiting for an answer, writes nothing once stopped, and Continue runs the
same evaluation again."""
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from dubeval import asr, evaluate, history, pipeline
from dubeval.jobs import Cancelled
from sample_results import make_results


def stop_after(n):
    """A check() that lets n calls through, then stops the run (as the pipeline's does once Stop is pressed)."""
    calls = []

    def check():
        calls.append(1)
        if len(calls) > n:
            raise Cancelled("Stopped by user.")
    check.calls = calls
    return check


class FakeWhisper:
    """A faster-whisper-like model whose segments come one at a time (and say how many were made)."""
    __module__ = "faster_whisper.fake"

    def __init__(self):
        self.made = 0

    def transcribe(self, y, language=None, word_timestamps=True):
        def segments():
            for i in range(50):
                self.made += 1
                yield SimpleNamespace(start=i, end=i + 1, text=f"line {i}", avg_logprob=-0.1, no_speech_prob=0.0, words=[])
        return segments(), SimpleNamespace(language="en")


def test_speech_recognition_stops_between_lines(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", SimpleNamespace(set_random_seed=lambda s: None))
    model = FakeWhisper()
    with pytest.raises(Cancelled):
        asr.transcribe(np.zeros(16000, dtype=np.float32), model, "en", check=stop_after(3))
    assert model.made == 4                      # not the 50 lines of the whole track
    # Without a check it reads every line, as before.
    assert len(asr.transcribe(np.zeros(16000, dtype=np.float32), FakeWhisper(), "en")["segments"]) == 50


def test_the_language_check_stops_between_windows(monkeypatch):
    seen = []
    monkeypatch.setattr(evaluate, "_language_probs", lambda y, m: seen.append(1) or {"ko": 1.0})
    y = np.zeros(16000 * 120, dtype=np.float32)
    with pytest.raises(Cancelled):
        evaluate.language_windows(y, None, [[0.0, 120.0]], "ko", check=stop_after(2))
    assert len(seen) == 2


def test_a_waiting_translation_check_is_abandoned_at_once():
    stop = threading.Event()
    check = pipeline._canceller(stop)
    started = time.monotonic()
    threading.Timer(0.2, stop.set).start()
    with pytest.raises(Cancelled):
        pipeline._abandonable(lambda: time.sleep(10), check)      # a judge still waiting for its answer
    assert time.monotonic() - started < 2


def test_an_abandonable_check_still_reports_its_own_errors():
    def broken():
        raise ValueError("bad answer")
    with pytest.raises(ValueError):
        pipeline._abandonable(broken, pipeline._canceller(threading.Event()))


def test_stopped_at_the_very_end_writes_nothing(monkeypatch, tmp_path, isolated_output):
    stop = threading.Event()

    def finishes_as_stop_is_pressed(original, dub, notify, check_cancel, **options):
        stop.set()                              # pressed while the last check ran
        return make_results()
    monkeypatch.setattr(pipeline, "evaluate_files", finishes_as_stop_is_pressed)
    with pytest.raises(Cancelled):
        pipeline.run_files_evaluation("o.mp4", "d.mp4", cancel_event=stop, out_dir=str(tmp_path / "run"))
    assert not (tmp_path / "run").exists() and history.load() == []
