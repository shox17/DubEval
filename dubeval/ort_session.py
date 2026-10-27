"""ONNX Runtime sessions on the CPU, made the same way for every model DubEval runs."""
from pathlib import Path


def cpu_session(model: Path):
    """A CPU session for model whose threads sleep between runs instead of busy-waiting.

    Busy-waiting is ONNX Runtime's default; with two models taking turns (the background check and the voice model
    in voice similarity) each one's waiting threads took the processor from the other, and that step ran 6x slower
    (p006: 10.5 s → 1.8 s, measured 2026-10-23, same scores).
    """
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.log_severity_level = 3
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    return ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
