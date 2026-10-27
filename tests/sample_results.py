"""A realistic results dict (the shape run_full_evaluation + run_share_evaluation produce) for report/CLI/UI tests."""
import copy

BASE = {
    "schema_version": 6,
    "metadata": {"original_video": "o.mp4", "dubbed_video": "d.mp4", "target_language": "ko",
                 "detected_source_language": "en", "whisper_model": "small"},
    "acoustic_metrics": {
        "original_duration_sec": 28.68, "dubbed_duration_sec": 28.68, "duration_diff_sec": 0.0,
        "original_speaking_sec": 28.65, "dubbed_speaking_sec": 28.5, "original_rms": 0.0313, "dubbed_rms": 0.0313,
        "rms_ratio": 1.0, "original_volume_stability_pct": 60.4, "dubbed_volume_stability_pct": 62.5,
        "original_silence_ratio": 0.0011, "dubbed_silence_ratio": 0.006, "silence_diff": 0.0049,
        "original_peak_dbfs": -3.0, "dubbed_peak_dbfs": -3.2, "dubbed_clipping_pct": 0.0,
        "loudness_envelope": {"step_sec": 0.25, "original_db": [-30.0, -28.0], "dubbed_db": [-30.5, -27.9]},
    },
    "speech_recognition": {
        "wer": None, "cer": None, "primary_metric": None, "error_rate": None, "accuracy_pct": None,
        "ground_truth": "", "dubbed_transcript": "안녕하세요. 저는 존입니다.", "original_transcript": "Hi, I'm John.",
        "original_speech_rate": {"value": 2.6, "unit": "words/s"}, "dubbed_speech_rate": {"value": 5.8, "unit": "chars/s"},
        "dubbed_language_detected": "ko", "dubbed_language_probability": 0.99,
        "clarity": {"confident_pct": 100.0, "mean_logprob": -0.2, "segments": 2, "unclear_segments": []},
        "original_segments": [{"start": 0.0, "end": 2.0, "text": "Hi, I'm John."}],
        "dubbed_segments": [{"start": 0.1, "end": 2.1, "text": "안녕하세요. 저는 존입니다."}],
    },
    "timing_alignment": {
        "overlap_pct": 81.0, "original_covered_pct": 90.0, "dub_in_original_pct": 88.0, "start_offset_sec": 0.0,
        "end_offset_sec": -0.1, "mismatches": [{"start": 19.4, "end": 20.1, "kind": "dub_only"}],
        "original_speech": [[0.0, 19.0], [20.5, 28.5]], "dubbed_speech": [[0.0, 20.1], [20.6, 28.4]],
    },
    "video_integrity": {
        "original": {"readable": True, "width": 1920, "height": 1080, "fps": 60.0, "frames": 1721, "duration_sec": 28.68, "has_audio": True},
        "dubbed": {"readable": True, "width": 1920, "height": 1080, "fps": 60.0, "frames": 1721, "duration_sec": 28.68, "has_audio": True},
        "same_resolution": True, "same_fps": True,
    },
    "lipsync_metrics": {"measured": True, "valid": True, "reason": "", "pearson_correlation": -0.03,
                        "best_lag_correlation": 0.1, "best_lag_ms": 40, "sync_quality": "none", "face_coverage_pct": 56.0,
                        "original_valid": True, "original_pearson": -0.2, "original_sync_quality": "none",
                        "original_face_coverage_pct": 56.0, "waveform_data": {"timestamps": [], "mar_norm": [], "rms_norm": []}},
    "voice_quality": {"measured": True, "reason_key": None, "dub": 2.5, "original": 2.3, "difference": 0.2,
                      "model": "DNSMOS P.835 (OVRL)",
                      "windows": [{"start": 0.0, "end": 9.01, "dub": 2.5, "original": 2.3, "dub_sig": 3.4,
                                   "original_sig": 3.2, "dub_bak": 3.0, "original_bak": 2.8}]},
    "voice_similarity": {"measured": True, "reason_key": None, "median": 0.62, "skipped_noisy": 0,
                         "model": "WeSpeaker ResNet34-LM",
                         "lines": [{"start": 0.0, "end": 2.0, "similarity": 0.62}, {"start": 20.5, "end": 24.0,
                                                                                  "similarity": 0.64}]},
    "warnings": [],
    "translation_judge": {"measured": False, "reason": "The translation check was turned off for this run.",
                          "model": None, "meaning_score": None, "summary": None, "issues": []},
    "pipeline": {
        "run_id": "r1", "execution_mode": "Perso share link (lip-synced video)", "input_video_path": "o.mp4",
        "dubbed_video_path": "d.mp4", "target_language_name": "Korean", "target_language_code": "ko",
        "target_language_id": "ko",
        "share": {"share_url": "https://perso.ai/en/share/video-translator?seq=abc", "seq": 100001,
                  "title": "QA sample.mp4 → ko", "source_language_name": "English (US)", "source_language_code": "en",
                  "target_language_name": "Korean", "is_lipsync": True, "evaluated_video": "lip-synced",
                  "duration_ms": 28683, "created": "2026-09-26"},
        "timestamp": "2026-09-29 20:16:39", "logs": "",
    },
}

JUDGED = {"measured": True, "reason": "", "model": "gemini-3.5-flash", "meaning_score": 5,
          "summary": {"en": "The dub keeps the original meaning.", "ko": "더빙이 원래 의미를 유지합니다.",
                      "pt": "A dublagem mantém o sentido original.", "es": "El doblaje mantiene el sentido original."},
          "issues": []}


def make_results(**sections) -> dict:
    """A deep copy of BASE with top-level sections updated: make_results(acoustic_metrics={"rms_ratio": 0.5})."""
    r = copy.deepcopy(BASE)
    for key, value in sections.items():
        if isinstance(value, dict) and isinstance(r.get(key), dict):
            r[key].update(value)
        else:
            r[key] = value
    return r
