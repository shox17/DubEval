"""Tests for transcript scoring: text normalisation, CER vs WER and accuracy."""
from dubeval.evaluate import normalize_text, score_transcript


def test_normalize_strips_punctuation_case_and_whitespace():
    assert normalize_text("  Hello,   WORLD!! ") == "hello world"
    assert normalize_text("안녕하세요. 저는  존입니다!") == "안녕하세요 저는 존입니다"


def test_punctuation_only_differences_are_not_errors():
    s = score_transcript("안녕하세요. 저는 존입니다.", "안녕하세요 저는 존입니다", "ko")
    assert s["error_rate"] == 0.0 and s["accuracy_pct"] == 100.0


def test_cjk_uses_cer_and_ignores_spacing():
    s = score_transcript("こんにちは。ジョンです。", "こんにちは ジョンです", "ja")
    assert s["primary_metric"] == "cer"
    assert s["cer"] == 0.0


def test_korean_spacing_difference_counts_for_wer_but_not_cer():
    s = score_transcript("소프트웨어 공학을 공부합니다", "소프트웨어공학을 공부합니다", "ko")
    assert s["primary_metric"] == "cer" and s["cer"] == 0.0
    assert s["wer"] > 0


def test_latin_languages_use_wer():
    s = score_transcript("hello my name is john", "hello my name is jon", "en")
    assert s["primary_metric"] == "wer"
    assert s["error_rate"] == 0.2
    assert s["accuracy_pct"] == 80.0


def test_empty_transcript_is_total_error():
    s = score_transcript("hello world", "", "en")
    assert s["error_rate"] == 1.0 and s["accuracy_pct"] == 0.0


def test_missing_ground_truth_gives_no_score():
    s = score_transcript("   ", "anything", "en")
    assert s["error_rate"] is None and s["accuracy_pct"] is None


def test_accuracy_is_clamped_when_error_rate_exceeds_one():
    s = score_transcript("a", "x y z", "en")
    assert s["error_rate"] > 1.0 and s["accuracy_pct"] == 0.0
