"""Tests for the pipeline's files: results.json, run-folder pruning and cancellation."""
import os
import threading

import pytest

from dubeval import pipeline
from dubeval.jobs import Cancelled
from fake_perso import SHARE_URL, FakePerso


def test_results_roundtrip_and_corrupt_file(isolated_output):
    assert pipeline.load_results() is None
    pipeline.save_results({"schema_version": 5, "x": "한국어"})
    assert pipeline.load_results() == {"schema_version": 5, "x": "한국어"}
    (isolated_output / "results.json").write_text("{not json")
    assert pipeline.load_results() is None


def test_prune_keeps_newest_runs(isolated_output):
    runs = isolated_output / "runs"
    for i in range(5):
        d = runs / f"run{i}"
        d.mkdir(parents=True)
        os.utime(d, (i, i))
    pipeline.prune_old_runs(keep=2)
    assert sorted(os.listdir(runs)) == ["run3", "run4"]


def test_cancel_before_download(isolated_output):
    fake = FakePerso()
    stop = threading.Event()
    stop.set()
    with pytest.raises(Cancelled):
        pipeline.run_share_evaluation(SHARE_URL, cancel_event=stop, session=fake, sleep=lambda s: None)
    assert not [c for c in fake.calls if c[0] == "GET-MEDIA"]
