"""Builds the meaning screen's model pack: BGE-M3 as an int8 ONNX model plus its tokenizer, for onnxruntime (no torch).

    python tools/build_meaning_onnx.py [--out DIR]

Developer tool: needs torch, transformers and onnx (the development environment has them); the desktop app and
dubeval itself only need onnxruntime and tokenizers to use the result. Steps: load BAAI/bge-m3 from the Hugging Face
cache (downloading it the first time), export the encoder with its pooling (the [CLS] vector, normalized, exactly as
sentence-transformers does for this model) to ONNX, quantize the weights to int8, and write model.onnx,
tokenizer.json and pack.json (sizes and SHA-256) into the output folder, by default the meaning screen's own folder
(dubeval/meaning.py, PACK_DIR).
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SOURCE = "BAAI/bge-m3"
MAX_TOKENS = 512            # lines are short; the pack embeds at most this many tokens per line (meaning.MAX_TOKENS)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def export(fp32: Path) -> Path:
    """The encoder + [CLS] pooling + L2 normalization, as one fp32 ONNX graph (weights in external files)."""
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModel

    folder = Path(snapshot_download(SOURCE, allow_patterns=["*.json", "model.safetensors", "*.model"]))
    model = AutoModel.from_pretrained(folder).eval()

    class Embed(torch.nn.Module):
        def __init__(self, encoder):
            super().__init__()
            self.encoder = encoder

        def forward(self, input_ids, attention_mask):
            cls = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
            return torch.nn.functional.normalize(cls, p=2, dim=1)

    ids = torch.tensor([[0, 35378, 2]], dtype=torch.long)
    mask = torch.ones_like(ids)
    torch.onnx.export(Embed(model), (ids, mask), str(fp32), input_names=["input_ids", "attention_mask"],
                      output_names=["embedding"], opset_version=17, dynamo=False,
                      dynamic_axes={"input_ids": {0: "batch", 1: "tokens"}, "attention_mask": {0: "batch", 1: "tokens"},
                                    "embedding": {0: "batch"}})
    return folder


def main() -> int:
    from dubeval.meaning import PACK_DIR
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(PACK_DIR), help=f"Output folder (default {PACK_DIR})")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="bge_m3_onnx_") as tmp:
        fp32 = Path(tmp) / "fp32" / "model.onnx"
        fp32.parent.mkdir()
        print("Exporting BGE-M3 to ONNX (fp32)...", flush=True)
        source = export(fp32)
        print("Quantizing the weights to int8...", flush=True)
        from onnxruntime.quantization import QuantType, quantize_dynamic
        quantize_dynamic(str(fp32), str(out / "model.onnx"), weight_type=QuantType.QInt8)
    shutil.copy(source / "tokenizer.json", out / "tokenizer.json")
    files = {name: {"bytes": (out / name).stat().st_size, "sha256": sha256(out / name)}
             for name in ("model.onnx", "tokenizer.json")}
    pack = {"name": "bge-m3-int8", "source": SOURCE, "license": "MIT", "pooling": "cls+l2", "max_tokens": MAX_TOKENS,
            "files": files, "built": time.strftime("%Y-%m-%d")}
    (out / "pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    total = sum(f["bytes"] for f in files.values()) / 1e6
    print(f"Done in {time.time() - started:.0f} s: {out} ({total:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
