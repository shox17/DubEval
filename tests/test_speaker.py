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


def test_lines_are_compared_at_the_same_moment():
    orig = np.concatenate([tone(150, 3), tone(250, 3), tone(150, 3)])
    dub = np.concatenate([tone(150, 3), tone(400, 3), tone(150, 3)])
    r = speaker.voice_similarity(orig, dub, lines((0, 3), (3, 6), (6, 9), (8.5, 9.0)), FakeSession())
    assert r["measured"] and [l["start"] for l in r["lines"]] == [0, 3, 6]          # the 0.5 s line is skipped
    assert r["lines"][0]["similarity"] > 0.99 and r["lines"][1]["similarity"] < 0.2
    few = speaker.voice_similarity(orig, dub, lines((0, 3)), FakeSession())
    assert few["reason_key"] == "r.vs.few_lines" and few["original_self"] is None


def test_the_original_speakers_are_matched_with_themselves():
    # One speaker with three lines and another with two: every line has another line of the same voice.
    known = np.concatenate([tone(150, 3), tone(250, 3), tone(150, 3), tone(250, 3), tone(150, 3)])
    spans = lines((0, 3), (3, 6), (6, 9), (9, 12), (12, 15))
    assert speaker.voice_similarity(known, known, spans, FakeSession())["original_self"] > 0.99
    # Every line sounds like nobody else in the video (music, several people at once): the model knows no speaker.
    unknown = np.concatenate([tone(f, 3) for f in (150, 250, 400, 600, 900)])
    r = speaker.voice_similarity(unknown, known, spans, FakeSession())
    assert r["measured"] and r["original_self"] < 0.2


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
def vs_result(*sims, own=0.8) -> dict:
    """A measured voice-similarity result with these per-line similarities; own = the original's lines among
    themselves (None: a result saved before that was measured)."""
    ls = [{"start": i * 5.0, "end": i * 5.0 + 3.0, "similarity": s} for i, s in enumerate(sims)]
    return {"measured": True, "reason_key": None, "median": float(np.median(sims)), "lines": ls, "original_self": own}


@pytest.mark.parametrize("sims, level, says", [
    ((0.8, 0.85, 0.82), "good", "original speaker's voice"), ((0.41, 0.45, 0.6), "good", "original speaker's voice"),
    ((0.33, 0.35, 0.36), "check", "only partly"), ((0.15, 0.2, 0.3), "check", "different voice"),
    ((0.05, 0.02, 0.08), "check", "different voice"),                  # never Poor: a new voice can be chosen
])
def test_similarity_says_same_voice_partly_or_different_never_poor(sims, level, says):
    row = metric(build_report(make_results(voice_similarity=vs_result(*sims))), "voice_similarity")
    assert row["level"] == level and says in row["message"] and row["thresholds"] and "lines" in row["display"]
    if level == "check":
        assert "80% alike" in row["message"]              # why the number can be trusted: the original's own lines


def test_a_low_similarity_is_not_graded_when_the_model_cannot_follow_the_original():
    # A film clip: the original's own lines are 45% alike, so 24% for the dub proves nothing about its voice.
    row = metric(build_report(make_results(voice_similarity=vs_result(0.2, 0.24, 0.3, own=0.45))), "voice_similarity")
    assert row["level"] == "not_measured" and "Can't tell" in row["message"]
    assert "24%" in row["message"] and "45%" in row["message"] and "60%" in row["message"]
    # A match that high is itself the proof (two different people never reached it): it is graded all the same.
    row = metric(build_report(make_results(voice_similarity=vs_result(0.44, 0.46, 0.5, own=0.45))), "voice_similarity")
    assert row["level"] == "good"
    # A result saved before the original was matched with itself keeps a grade.
    row = metric(build_report(make_results(voice_similarity=vs_result(0.2, 0.24, 0.3, own=None))), "voice_similarity")
    assert row["level"] == "check" and "different voice" in row["message"]


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
    r["voice_similarity"]["original_self"] = 0.45        # the model can't follow this video's speakers: no line counts
    out = build_intervals(r, lambda key, **p: t(key, "en", **p), "en")["intervals"]
    assert not [i for i in out if i["category"] == "voice_change"]


def test_the_speaker_model_shipped_with_the_app_needs_no_download(monkeypatch, tmp_path):
    from dubeval import paths, speaker
    (tmp_path / speaker.MODEL_NAME).write_bytes(b"onnx")
    monkeypatch.setattr(paths, "BUNDLED_MODELS", tmp_path)
    refuse = lambda url, out: (_ for _ in ()).throw(AssertionError("must not download"))
    assert speaker.model_path(download=refuse) == tmp_path / speaker.MODEL_NAME
