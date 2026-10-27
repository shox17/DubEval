"""Meaning screen: how close each dub line is in meaning to the original line, from a multilingual sentence model.

BGE-M3 (BAAI, MIT license) turns each original line and each dub line into a vector; the cosine similarity of the
two says how close they are in meaning, across languages, in milliseconds per line and without any cloud service.
It catches lines that are clearly off (a different sentence, a lost half); subtle mistranslations need the judge
(translation_judge.py).

Two ways to run it, picked in this order:
- the **ONNX pack** (PACK_DIR: model.onnx + tokenizer.json, BGE-M3 with int8 weights, ~0.6 GB) on onnxruntime: no
  PyTorch, so the desktop app can ship without it. Built by tools/build_meaning_onnx.py;
- **sentence-transformers** with the original model (`pip install "dubeval[meaning]"`, PyTorch, ~4.4 GB), for
  development.
Without either, or on any error, the screen is "not measured" and the run goes on. DUBEVAL_MEANING_SCREEN=off turns
it off.
"""
import os
import json
import logging
import threading
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

MODEL_NAME = os.getenv("DUBEVAL_MEANING_MODEL", "BAAI/bge-m3")
PACK_DIR = Path(os.getenv("DUBEVAL_MEANING_PACK") or Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval"))
                / "bge-m3-int8")
PACK_NAME = "bge-m3-int8-onnx"
MAX_TOKENS = 512                 # lines are short; longer text is cut (the model was trained up to 8192)
_model = None
_lock = threading.Lock()


def not_measured(reason_key: str) -> dict:
    """A screen result for when it couldn't run."""
    return {"measured": False, "reason_key": reason_key, "model": None, "lines": [], "median": None}


def _pack_ready() -> bool:
    """Whether the ONNX pack is complete on disk (its files and their recorded sizes)."""
    try:
        files = json.loads((PACK_DIR / "pack.json").read_text(encoding="utf-8"))["files"]
        return all((PACK_DIR / name).stat().st_size == info["bytes"] for name, info in files.items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def backend() -> Optional[str]:
    """"onnx", "torch" or None: how the screen would run now."""
    if (os.getenv("DUBEVAL_MEANING_SCREEN") or "").strip().lower() == "off":
        return None
    if _pack_ready():
        return "onnx"
    return "torch" if _sentence_transformers() else None


class _OnnxModel:
    """BGE-M3 from the ONNX pack: tokenize, run, and take the normalized [CLS] vector. Our own export
    (tools/build_meaning_onnx.py) returns it ready ("embedding"); the downloaded pack (Xenova/bge-m3) returns every
    token's vector, so the first one is taken and normalized here, as sentence-transformers does for this model.

    Each text runs alone, unpadded: the exported graph doesn't mask padding the way the original does (a padded line
    scored up to 0.02 differently), and a video's few dozen short lines take well under a second anyway.
    """

    def __init__(self, folder: Path):
        from tokenizers import Tokenizer
        from dubeval.ort_session import cpu_session
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_truncation(MAX_TOKENS)
        self.session = cpu_session(folder / "model.onnx")
        self.inputs = {i.name for i in self.session.get_inputs()}
        outputs = [o.name for o in self.session.get_outputs()]
        self.output = "embedding" if "embedding" in outputs else outputs[0]

    def encode(self, texts: list[str]):
        import numpy as np
        out = []
        for text in texts:
            ids = np.array([self.tokenizer.encode(text).ids], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": np.ones_like(ids), "token_type_ids": np.zeros_like(ids)}
            vec = self.session.run([self.output], {k: v for k, v in feed.items() if k in self.inputs})[0][0]
            if vec.ndim == 2:                                   # every token's vector: [CLS] is the first
                vec = vec[0] / np.linalg.norm(vec[0])
            out.append(vec)
        return out


def _load():
    """The sentence model, loaded once: the ONNX pack, else sentence-transformers (on the GPU when there is one)."""
    global _model
    with _lock:
        if _model is None:
            if backend() == "onnx":
                log.info("Loading the meaning model from %s (onnxruntime)", PACK_DIR)
                _model = _OnnxModel(PACK_DIR)
            else:
                import torch
                from sentence_transformers import SentenceTransformer
                device = "cuda" if torch.cuda.is_available() and os.getenv("DUBEVAL_DEVICE", "").lower() != "cpu" \
                    else "cpu"
                log.info("Loading the meaning model %s on %s", MODEL_NAME, device)
                st = SentenceTransformer(MODEL_NAME, device=device)
                st.encode_texts = lambda texts: st.encode(texts, normalize_embeddings=True, batch_size=32)
                _model = st
        return _model


def unload() -> None:
    """Frees the sentence model (and its GPU memory), e.g. before a local judge needs the GPU."""
    global _model
    with _lock:
        _model = None
    from dubeval.asr import _free_gpu
    _free_gpu()


def available() -> bool:
    """Whether the screen can run: switched on, and the ONNX pack or sentence-transformers installed."""
    return backend() is not None


def screen(lines: list[dict], encode=None) -> dict:
    """Similarity (0-1) of every line that both sides speak, plus their median.

    lines: pipeline.judge_lines output ({n, start, end, original, dub, ...}); the original's script is used instead
    of what was heard when a subtitle file gave one. encode: a stand-in for the model's encode (tests).
    """
    pairs = [ln for ln in lines if (ln.get("original_script") or ln.get("original")) and ln.get("dub")]
    if not pairs:
        return not_measured("r.screen.no_lines")
    name = model_name() if encode is None else MODEL_NAME
    if encode is None:
        if not available():
            return not_measured("r.screen.off" if os.getenv("DUBEVAL_MEANING_SCREEN", "").lower() == "off"
                                else "r.screen.not_installed")
        try:
            model = _load()
            encode = model.encode if isinstance(model, _OnnxModel) else model.encode_texts
        except Exception as e:                      # a missing model or a broken GPU must never stop a run
            log.warning("Meaning screen not measured: %s", e)
            return not_measured("r.screen.error")
    try:
        a = encode([ln.get("original_script") or ln["original"] for ln in pairs])
        b = encode([ln["dub"] for ln in pairs])
    except Exception as e:
        log.warning("Meaning screen not measured: %s", e)
        return not_measured("r.screen.error")
    sims = [round(float(sum(x * y for x, y in zip(u, v))), 3) for u, v in zip(a, b)]
    out = [{"n": ln["n"], "start": ln["start"], "end": ln["end"], "similarity": s} for ln, s in zip(pairs, sims)]
    ordered = sorted(sims)
    median = ordered[len(ordered) // 2] if len(ordered) % 2 else round((ordered[len(ordered) // 2 - 1]
                                                                         + ordered[len(ordered) // 2]) / 2, 3)
    return {"measured": True, "reason_key": None, "model": name, "lines": out, "median": median}


def model_name() -> Optional[str]:
    """The screen's model as it would run now, for cache keys and the report (the ONNX pack scores a little
    differently from the original model, so the two never share cached results)."""
    b = backend()
    return PACK_NAME if b == "onnx" else MODEL_NAME if b == "torch" else None
