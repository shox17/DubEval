"""Speech recognition layer: backend choice, and the same output shape from both recognizers."""
import os
import sys
import types

import numpy as np
import pytest

from dubeval import asr


def test_backend_follows_the_setting_and_falls_back_to_what_is_installed(monkeypatch):
    monkeypatch.setattr(asr, "_installed", lambda name: True)
    monkeypatch.setenv("DUBEVAL_ASR", "openai-whisper")
    assert asr.backend() == asr.OPENAI
    monkeypatch.setenv("DUBEVAL_ASR", "something-else")
    assert asr.backend() == asr.FASTER
    monkeypatch.setattr(asr, "_installed", lambda name: name == asr.OPENAI)
    monkeypatch.setenv("DUBEVAL_ASR", "faster-whisper")
    assert asr.backend() == asr.OPENAI and asr.model_id("base") == "openai-whisper:base"
    monkeypatch.setattr(asr, "_installed", lambda name: True)
    monkeypatch.setenv("DUBEVAL_ASR", "faster-whisper")
    monkeypatch.setenv("DUBEVAL_DEVICE", "cpu")
    assert asr.model_id("base") == "faster-whisper:base:cpu"


def _faster_model(segments, language="ko", probs=(("ko", 0.9), ("en", 0.1))):
    """A stand-in for a faster-whisper model (the layer recognizes it by its module)."""
    seen = {}

    class Model:
        def transcribe(self, audio, **kw):
            seen.update(kw, dtype=audio.dtype)
            return iter(segments), types.SimpleNamespace(language=language)

        def detect_language(self, audio):
            seen["detect_len"] = len(audio)
            return probs[0][0], probs[0][1], list(probs)
    Model.__module__ = "faster_whisper.transcribe"
    return Model(), seen


def test_faster_whisper_output_has_the_shared_shape(monkeypatch):
    seeds = []
    monkeypatch.setitem(sys.modules, "ctranslate2", types.SimpleNamespace(set_random_seed=seeds.append))
    word = lambda s, e: types.SimpleNamespace(start=s, end=e)
    seg = types.SimpleNamespace(start=0.004, end=1.236, text=" 안녕하세요 ", avg_logprob=-0.2345, no_speech_prob=0.01,
                                words=[word(0.0, 0.5), word(0.5, 1.2)])
    model, seen = _faster_model([seg])
    out = asr.transcribe(np.zeros(16000, dtype=np.float64), model, language=None)
    assert out == {"text": "안녕하세요", "language": "ko", "segments": [
        {"start": 0.0, "end": 1.24, "text": "안녕하세요", "avg_logprob": -0.234, "no_speech_prob": 0.01,
         "words": [[0.0, 0.5], [0.5, 1.2]]}]}
    assert seeds == [asr.SEED] and seen["word_timestamps"] is True and seen["dtype"] == np.float32


def test_faster_whisper_language_probabilities_use_the_first_30_seconds():
    model, seen = _faster_model([])
    probs = asr.language_probs(np.zeros(16000 * 45, dtype=np.float32), model)
    assert probs == {"ko": 0.9, "en": 0.1} and seen["detect_len"] == 16000 * 30


def test_languages_are_whispers_codes():
    codes = asr.languages()
    assert {"en", "ko", "es", "ja", "zh"} <= codes and "xx" not in codes


@pytest.mark.skipif(os.name != "nt", reason="Windows only: DLL folders (and pretending os.name is 'nt' elsewhere breaks pathlib)")
def test_the_gpu_pack_folder_is_searched_first(monkeypatch, tmp_path):
    """Without PyTorch, NVIDIA's cuBLAS in the GPU pack folder is enough for faster-whisper on the GPU."""
    from dubeval import asr
    pack = tmp_path / "cuda"
    pack.mkdir()
    added = []
    monkeypatch.setenv("DUBEVAL_CUDA_DIR", str(pack))
    monkeypatch.setattr(asr.os, "name", "nt")
    monkeypatch.setattr(asr.os, "add_dll_directory", added.append, raising=False)
    monkeypatch.setattr(asr._add_cuda_dll_dirs, "done", False, raising=False)
    asr._add_cuda_dll_dirs()
    assert asr.cuda_pack_dir() == pack and added and added[0] == str(pack)


def test_language_names_need_no_extra_package():
    """faster-whisper only knows codes; the names come with DubEval (the runtime has no openai-whisper)."""
    from dubeval import asr
    from dubeval.languages import LANGUAGES
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    names = asr.language_names()
    assert names["ko"] == "korean" and names["uz"] == "uzbek" and set(_LANGUAGE_CODES) <= set(LANGUAGES)


def test_a_model_shipped_with_the_app_is_used_before_any_download(monkeypatch, tmp_path):
    from dubeval import asr, paths
    (tmp_path / "faster-whisper-base").mkdir()
    (tmp_path / "faster-whisper-base" / "model.bin").write_bytes(b"x")
    monkeypatch.setattr(paths, "BUNDLED_MODELS", tmp_path)
    monkeypatch.setenv("DUBEVAL_MODELS", str(tmp_path / "downloads"))
    assert asr._local_model("base") == str(tmp_path / "faster-whisper-base")
    assert asr._local_model("large-v3-turbo") is None                 # not shipped: downloaded as usual
    monkeypatch.setattr(paths, "BUNDLED_MODELS", None)
    assert asr._local_model("base") is None


# ----- "auto": the large model on a GPU when it is downloaded, else base -----

@pytest.mark.parametrize("kind, downloaded, device, expected", [
    ("faster-whisper", True, "cuda", "large-v3-turbo"),
    ("faster-whisper", True, "cpu", "base"),             # too slow on a CPU to be the default
    ("faster-whisper", False, "cuda", "base"),           # not downloaded: never fetched behind the person's back
    ("openai-whisper", True, "cuda", "base"),
])
def test_auto_picks_the_large_model_only_on_a_gpu_when_it_is_downloaded(kind, downloaded, device, expected):
    assert asr.pick_default(kind, downloaded, device) == expected


def test_auto_resolves_everywhere_a_model_name_is_used(monkeypatch):
    monkeypatch.setattr(asr, "default_model", lambda: "large-v3-turbo")
    assert asr.resolve("auto") == "large-v3-turbo" and asr.resolve("small") == "small"
    assert ":large-v3-turbo:" in asr.model_id("auto")      # cache keys name the model that ran


def test_a_voice_detector_that_cant_load_is_skipped_not_fatal(monkeypatch):
    vad = pytest.importorskip("faster_whisper.vad")

    def no_model(*a, **k):
        raise RuntimeError("NO_SUCHFILE : Load model from ...silero_vad_v6.onnx failed")
    monkeypatch.setattr(vad, "get_speech_timestamps", no_model)
    assert asr.voice_activity(np.zeros(16000, dtype=np.float32)) is None     # the evaluation goes on without it
