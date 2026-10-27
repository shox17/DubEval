"""Tests for voice similarity: filterbank features, the pinned model download, line selection, grading, intervals."""
import hashlib

import numpy as np
import pytest

from dubeval import speaker
from dubeval.i18n import t
from dubeval.intervals import build_intervals
from dubeval.report import build_report
from sample_results import make_results

SR = speaker.SAMPLE_RATE


def metric(rep: dict, mid: str) -> dict:
    """The report row with this id."""
    return next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == mid)


# ---------------- features ----------------
def test_mel_banks_cover_the_spectrum_like_kaldi():
    banks = speaker.mel_banks(80, 512, SR)
    assert banks.shape == (80, 257) and banks[:, -1].sum() == 0          # Nyquist bin unused
    assert banks.max() <= 1.0 and (banks.sum(axis=1) > 0).all()
    assert np.argmax(banks[0]) < np.argmax(banks[40]) < np.argmax(banks[79])


def test_fbank_frames_and_a_tone_lands_in_the_right_band():
    t_ = np.arange(SR) / SR
    feats = speaker.fbank((0.5 * np.sin(2 * np.pi * 1000 * t_)).astype(np.float32))
    assert feats.shape == (98, 80) and feats.dtype == np.float32           # 1 s: (16000 - 400) // 160 + 1
    peak_band = int(np.argmax(feats.mean(axis=0)))
    banks = speaker.mel_banks(80, 512, SR)
    assert abs(np.argmax(banks[peak_band]) * SR / 512 - 1000) < 100
    assert speaker.fbank(np.zeros(100, dtype=np.float32)).shape == (0, 80)


# ---------------- model download ----------------
def test_model_is_downloaded_once_and_checked(tmp_path, monkeypatch):
    payload = b"fake-onnx-bytes"
    monkeypatch.setattr(speaker, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(speaker, "MODEL_SHA256", hashlib.sha256(payload).hexdigest())
    calls = []

    def download(url, out):
        calls.append(url)
        out.write_bytes(payload)
    assert speaker.model_path(download).read_bytes() == payload
    assert speaker.model_path(download) and len(calls) == 1                # second call uses the verified file
    assert "f0c48c298fd835726c27956a5d617bad7115627e" in calls[0]         # pinned to a commit


def test_a_bad_or_failed_download_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(speaker, "CACHE_DIR", tmp_path)
    with pytest.raises(speaker.ModelUnavailable, match="checksum"):
        speaker.model_path(lambda url, out: out.write_bytes(b"tampered"))
    assert not list(tmp_path.iterdir())
    with pytest.raises(speaker.ModelUnavailable, match="download"):
        speaker.model_path(lambda url, out: (_ for _ in ()).throw(OSError("offline")))


# ---------------- comparison ----------------
class FakeSession:
    """Fingerprints from the audio's main frequency: same pitch → same voice."""
    def __init__(self):
        self.batches = []

    def run(self, _outputs, feeds):
        self.batches.append(len(feeds["feats"]))
        e = np.zeros((len(feeds["feats"]), 256), dtype=np.float32)
        for i, f in enumerate(feeds["feats"]):
            e[i, int(np.argmax(f.std(axis=0)))] = 1.0
            e[i, 255] = 0.3
        return [e]


def tone(freq: float, seconds: float) -> np.ndarray:
    """A buzzy tone (rich harmonics) standing in for a voice of this pitch."""
    t_ = np.arange(int(seconds * SR)) / SR
    return (0.3 * np.sign(np.sin(2 * np.pi * freq * t_)) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t_))).astype(np.float32)


def lines(*spans):
    """Original transcript lines."""
    return [{"start": s, "end": e, "text": "x"} for s, e in spans]


def test_lines_are_compared_at_the_same_moment_and_noisy_ones_skipped():
    orig = np.concatenate([tone(150, 3), tone(250, 3), tone(150, 3)])
    dub = np.concatenate([tone(150, 3), tone(400, 3), tone(150, 3)])
    quiet_bg = lambda audio: 4.0
    r = speaker.voice_similarity(orig, dub, lines((0, 3), (3, 6), (6, 9), (8.5, 9.0)), quiet_bg, FakeSession())
    assert r["measured"] and [l["start"] for l in r["lines"]] == [0, 3, 6]          # the 0.5 s line is skipped
    assert r["lines"][0]["similarity"] > 0.99 and r["lines"][1]["similarity"] < 0.2
    loud_bg = lambda audio: 2.0
    noisy = speaker.voice_similarity(orig, dub, lines((0, 3), (3, 6)), loud_bg, FakeSession())
    assert not noisy["measured"] and noisy["reason_key"] == "r.vs.noisy" and noisy["skipped_noisy"] == 2
    few = speaker.voice_similarity(orig, dub, lines((0, 3)), quiet_bg, FakeSession())
    assert few["reason_key"] == "r.vs.few_lines"


def test_both_stretches_of_a_line_go_through_the_model_together():
    session = FakeSession()
    a, b = tone(150, 3), tone(400, 3)
    together = speaker.similarity(a, b, session)
    assert session.batches == [2]
    assert together == pytest.approx(float(speaker.embed(a, session) @ speaker.embed(b, session)), abs=1e-6)
    session.batches.clear()
    speaker.similarity(a, b[:-100], session)                   # different lengths: one at a time
    assert session.batches == [1, 1]


def test_onnx_sessions_sleep_between_runs():
    # Busy-waiting threads of one model slowed the other one taking turns with it 6x (voice similarity).
    from dubeval import voice_quality
    from dubeval.ort_session import cpu_session
    options = cpu_session(voice_quality.MODEL_PATH).get_session_options()
    assert options.get_session_config_entry("session.intra_op.allow_spinning") == "0"


# ---------------- grading and intervals ----------------
def vs_result(*sims) -> dict:
    """A measured voice-similarity result with these per-line similarities."""
    ls = [{"start": i * 5.0, "end": i * 5.0 + 3.0, "similarity": s} for i, s in enumerate(sims)]
    return {"measured": True, "reason_key": None, "median": float(np.median(sims)), "lines": ls, "skipped_noisy": 0}


@pytest.mark.parametrize("sims, level", [((0.8, 0.85, 0.82), "good"), ((0.5, 0.52, 0.49), "good"),
                                         ((0.15, 0.2, 0.3), "check")])
def test_similarity_is_good_or_check_never_poor(sims, level):
    row = metric(build_report(make_results(voice_similarity=vs_result(*sims))), "voice_similarity")
    assert row["level"] == level and row["thresholds"] and "lines" in row["display"]


def test_not_measured_reasons_are_explained():
    row = metric(build_report(make_results(voice_similarity=speaker.not_measured("r.vs.noisy"))), "voice_similarity")
    assert row["level"] == "not_measured" and "too loud" in row["message"]
    row = metric(build_report(make_results(voice_similarity=speaker.not_measured("r.vs.no_model"))), "voice_similarity")
    assert "couldn't be downloaded" in row["message"]


@pytest.mark.parametrize("sims, flagged", [
    ((0.8, 0.86, 0.87, 0.81), []),            # a good clone: nothing stands out
    ((0.8, 0.86, 0.55, 0.81), [10.0]),        # a similar but different voice on one line
    ((0.8, 0.2, 0.87, 0.81), [5.0]),          # the other character's voice on one line
    ((0.08, 0.22, 0.08, 0.3), []),            # a stock voice throughout: low overall, no single odd line
])
def test_a_line_with_another_voice_becomes_an_interval(sims, flagged):
    r = make_results(timing_alignment={"mismatches": []}, acoustic_metrics={"dubbed_duration_sec": 30.0},
                     voice_similarity=vs_result(*sims))
    out = build_intervals(r, lambda key, **p: t(key, "en", **p), "en")["intervals"]
    assert [i["start"] for i in out if i["category"] == "voice_change"] == flagged


def test_the_speaker_model_shipped_with_the_app_needs_no_download(monkeypatch, tmp_path):
    from dubeval import paths, speaker
    (tmp_path / speaker.MODEL_NAME).write_bytes(b"onnx")
    monkeypatch.setattr(paths, "BUNDLED_MODELS", tmp_path)
    refuse = lambda url, out: (_ for _ in ()).throw(AssertionError("must not download"))
    assert speaker.model_path(download=refuse) == tmp_path / speaker.MODEL_NAME
