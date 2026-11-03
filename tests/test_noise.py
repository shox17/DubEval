"""The noise check: a burst of noise the original doesn't have, on made-up sound and on made-up measurements."""
import numpy as np
import pytest

from dubeval.evaluate import noise_envelope
from dubeval.intervals import build_intervals, noise_bursts, noise_moments
from dubeval.i18n import t
from dubeval.report import build_report
from dubeval.validation import score
from sample_results import make_results

SR = 16000


def voice(seconds=20.0, seed=1):
    """Something like speech: harmonics, switched on and off a few times a second, over a quiet background."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t_ = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f * t_) / (i + 1) for i, f in enumerate((180, 360, 540, 720, 1500, 2600, 3400)))
    gate = (np.sin(2 * np.pi * 3 * t_) > -0.3).astype(np.float32)
    return (0.12 * tone * gate + rng.normal(0, 0.0005, n)).astype(np.float32)


def with_noise(y, start=8.0, seconds=4.0, seed=2):
    z = y.copy()
    a, b = int(start * SR), int((start + seconds) * SR)
    level = float(np.sqrt(np.mean(z[a:b] ** 2)))
    z[a:b] = z[a:b] + np.random.default_rng(seed).normal(0, level, b - a).astype(np.float32)
    return z


def test_a_burst_of_noise_is_found_where_it_is():
    y = voice()
    [(start, end)] = noise_bursts(noise_envelope(y, with_noise(y)))
    assert 7.0 <= start <= 9.0 and 11.0 <= end <= 13.0


def test_clean_sound_a_different_voice_and_a_louder_passage_are_not_noise():
    y = voice()
    assert noise_bursts(noise_envelope(y, y)) == []
    assert noise_bursts(noise_envelope(y, voice(seed=5) * 0.5)) == []
    louder = y.copy()
    louder[int(8 * SR):int(12 * SR)] *= 5.0                                     # 14 dB louder: a loudness jump, not noise
    assert noise_bursts(noise_envelope(y, louder)) == []


def test_noise_in_both_tracks_cancels_out():
    y = with_noise(voice())                                                     # a noisy scene in the original too
    assert noise_bursts(noise_envelope(y, y)) == []


def test_too_short_to_measure():
    assert noise_envelope(np.zeros(100), np.zeros(100))["floor_rise"] == []


def env(floor, flat):
    return {"step_sec": 0.25, "floor_rise": floor, "flatness_rise": flat}


def test_the_rule_needs_the_rise_the_flatness_and_the_length():
    quiet, loud = [0.0] * 8, [20.0] * 8
    assert noise_bursts(env(quiet + loud + quiet, quiet + [3.0] * 8 + quiet)) == [(2.0, 4.0)]
    assert noise_bursts(env(quiet + loud + quiet, quiet + [1.0] * 8 + quiet)) == []     # louder, not flatter
    assert noise_bursts(env(quiet + [9.0] * 8 + quiet, quiet + [3.0] * 8 + quiet)) == []  # flatter, not much higher
    assert noise_bursts(env(quiet + [20.0] * 4 + quiet, quiet + [3.0] * 4 + quiet)) == []  # 1 s: too short
    assert noise_bursts({}) == []


def noisy_results(**acoustic):
    return make_results(acoustic_metrics={"noise_envelope": env([0.0] * 8 + [20.0] * 8 + [0.0] * 8, [0.0] * 8 + [3.0] * 8 + [0.0] * 8),
                                          **acoustic})


def rows(rep):
    return {m["id"]: m for s in rep["sections"] for m in s["metrics"]}


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_a_burst_is_a_check_row_and_a_moment_to_listen_to(lang):
    rep = build_report(noisy_results(), lang)
    row = rows(rep)["noise"]
    assert row["level"] == "check" and row["value"] == 1
    assert "{" not in row["message"] + row["display"] + row["thresholds"]
    moments = [i for i in rep["problem_intervals"] if i["category"] == "noise"]
    assert [(i["start"], i["end"], i["severity"]) for i in moments] == [(2.0, 4.0, "check")]
    assert "2.0" in moments[0]["description"] and "{" not in moments[0]["description"]
    assert moments[0]["category_label"] == t("r.cat.noise", lang)


def test_no_burst_is_a_good_row_and_results_from_before_the_check_have_none():
    rep = build_report(make_results(acoustic_metrics={"noise_envelope": env([0.0] * 20, [0.0] * 20)}), "en")
    assert rows(rep)["noise"]["level"] == "good" and rows(rep)["noise"]["value"] == 0
    assert "noise" not in rows(build_report(make_results(), "en"))


def test_a_burst_makes_a_good_dub_needs_review_never_poor():
    clean = build_report(make_results(acoustic_metrics={"noise_envelope": env([0.0] * 20, [0.0] * 20)}), "en")
    assert build_report(noisy_results(), "en")["overall"]["level"] == ("check" if clean["overall"]["level"] != "poor" else "poor")
    assert not any(m["level"] == "poor" for m in [rows(build_report(noisy_results(), "en"))["noise"]])


def test_clipped_sound_is_reported_as_distortion_not_noise_too():
    ac = {"noise_envelope": env([0.0] * 8 + [20.0] * 8, [0.0] * 8 + [3.0] * 8), "dubbed_clipping_intervals": [[2.5, 3.0]]}
    assert noise_moments(ac) == []
    assert noise_moments({**ac, "dubbed_clipping_intervals": [[9.0, 9.5]]}) == [(2.0, 4.0)]


def test_noise_is_found_where_the_words_cant_be_read():
    r = noisy_results()
    r["speech_recognition"].update(dubbed_language_detected="kk", dubbed_language_probability=0.47)
    r["metadata"]["target_language"] = "uz"
    r["pipeline"] = {"target_language_code": "uz", "target_language_name": "Uzbek",
                     "input": {"source_language_code": "en", "source_language_name": "English"}}
    assert [i["category"] for i in build_report(r, "en")["problem_intervals"] if i["category"] == "noise"] == ["noise"]


def test_the_known_problem_test_counts_it_as_caught():
    moment = {"start": 8.0, "end": 12.0, "category": "noise", "severity": "check"}
    assert score("noise_4s", 8.0, [], [moment])["caught"]
