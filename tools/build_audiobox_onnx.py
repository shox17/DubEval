"""Builds the voice-quality graph (dubeval/models/audiobox_aesthetics.onnx).

    pip install --no-deps audiobox_aesthetics==0.0.4      # into the development environment (it needs torch)
    python tools/build_audiobox_onnx.py <folder with model.safetensors and config.json> [--out DIR]

Developer tool: needs torch, onnx and Meta's audiobox_aesthetics package (CC BY 4.0). The graph holds no weights:
every weight is "external data" that points straight into Meta's own model.safetensors (facebook/audiobox-aesthetics
on Hugging Face), which the voice_quality pack downloads unchanged (dubeval/packs.py). So DubEval ships ~0.6 MB of
graph and never redistributes the 415 MB of weights; onnxruntime reads them from the file, where safetensors keeps
each tensor as plain little-endian bytes.

The graph takes 16 kHz mono stretches of voice_quality.WINDOW_SEC and gives four scores per stretch on their 1-10
scales, in voice_quality.AXES order. Each stretch is scored on its own (the package normalises nothing across a batch
with this model: its WavLM config has normalize off). The result is checked against torch on random input.
"""
import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dubeval import voice_quality  # noqa: E402


def weight_offsets(path: Path) -> dict:
    """Each tensor's (byte offset, byte length, shape, dtype) inside a safetensors file."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    return {name: (8 + n + t["data_offsets"][0], t["data_offsets"][1] - t["data_offsets"][0], tuple(t["shape"]), t["dtype"])
            for name, t in header.items() if name != "__metadata__"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="model.safetensors and config.json of facebook/audiobox-aesthetics")
    ap.add_argument("--out", type=Path, default=voice_quality.GRAPH_PATH.parent)
    args = ap.parse_args()
    import onnx
    import onnxruntime as ort
    import torch
    from audiobox_aesthetics.model.aes import AXES_NAME, AesMultiOutput
    from torch import nn
    from torch.nn import functional as F

    from dubeval import packs
    weights = args.folder / voice_quality.WEIGHTS
    expected = packs.PACKS["voice_quality"]["files"][0]
    if weights.stat().st_size != expected["bytes"] or packs._sha256_of(weights).hexdigest() != expected["sha256"]:
        raise SystemExit("this isn't the pinned model.safetensors (size or SHA-256 differ)")
    if tuple(a.lower() for a in AXES_NAME) != voice_quality.AXES:
        raise SystemExit(f"the package's scores {AXES_NAME} aren't in voice_quality.AXES order")

    class Scores(nn.Module):
        """wav [batch, samples] -> [batch, 4] scores, as AesMultiOutput.forward computes them with nothing padded."""
        def __init__(self, m):
            super().__init__()
            self.m = m
            self.register_buffer("mean", torch.tensor([m.target_transform[a]["mean"] for a in AXES_NAME]), persistent=False)
            self.register_buffer("std", torch.tensor([m.target_transform[a]["std"] for a in AXES_NAME]), persistent=False)

        def forward(self, wav):
            m = self.m
            (_, layers), _ = m.wavlm_model.extract_features(source=wav, padding_mask=None, output_layer=m.nth_layer,
                                                            ret_layer_results=True)
            stacked = torch.stack([g[0] for g in layers], dim=-1)             # time, batch, channels, layers
            preds = []
            for name in AXES_NAME:
                embed = torch.einsum("tbcl,l->btc", stacked, F.softmax(m.layer_weights[name], dim=-1)).mean(dim=1)
                if m.normalize_embed:
                    embed = F.normalize(embed, dim=-1)
                preds.append(m.proj_layer[name](embed).squeeze(-1))
            return torch.stack(preds, dim=-1) * self.std + self.mean

    model = AesMultiOutput.from_pretrained(str(args.folder)).eval()
    if model.wavlm_model.cfg.normalize or not model.use_weighted_layer_sum:
        raise SystemExit("this model's settings aren't the ones the graph was written for")
    wrapped = Scores(model).eval()
    samples = int(voice_quality.WINDOW_SEC * voice_quality.SAMPLE_RATE)
    x = torch.from_numpy((np.random.default_rng(0).standard_normal((2, samples)) * 0.05).astype(np.float32))
    with torch.no_grad():
        ref = wrapped(x).numpy()
        own = [model({"wav": x[i:i + 1, None, :], "mask": torch.ones(1, 1, samples, dtype=torch.bool)}) for i in range(2)]
    own = np.array([[float(o[a][0]) * model.target_transform[a]["std"] + model.target_transform[a]["mean"]
                     for a in AXES_NAME] for o in own])
    if float(np.abs(ref - own).max()) > 1e-4:
        raise SystemExit("the rewritten forward pass doesn't match the package's")

    file = voice_quality.GRAPH_PATH.name
    with tempfile.TemporaryDirectory() as tmp:
        # No constant folding, so every initializer is a checkpoint tensor as saved (no transposed or merged copies).
        torch.onnx.export(wrapped, x, str(Path(tmp) / file), input_names=["wav"], output_names=["scores"],
                          dynamic_axes={"wav": {0: "batch"}, "scores": {0: "batch"}}, opset_version=17,
                          do_constant_folding=False, dynamo=False)
        graph = onnx.load(str(Path(tmp) / file))
    where = weight_offsets(weights)
    with open(weights, "rb") as f:
        for init in graph.graph.initializer:
            key = init.name.removeprefix("m.")
            if key not in where:
                raise SystemExit(f"{init.name}: not a checkpoint tensor")
            offset, length, shape, dtype = where[key]
            f.seek(offset)
            if dtype != "F32" or tuple(init.dims) != shape or f.read(length) != init.raw_data:
                raise SystemExit(f"{init.name}: not the checkpoint's bytes")
            init.ClearField("raw_data")
            init.data_location = onnx.TensorProto.EXTERNAL
            del init.external_data[:]
            for k, v in (("location", voice_quality.WEIGHTS), ("offset", str(offset)), ("length", str(length))):
                entry = init.external_data.add()
                entry.key, entry.value = k, v
    args.out.mkdir(parents=True, exist_ok=True)
    onnx.save(graph, str(args.out / file))
    opts = ort.SessionOptions()
    opts.add_session_config_entry("session.model_external_initializers_file_folder_path", str(args.folder))
    got = ort.InferenceSession((args.out / file).read_bytes(), opts, providers=["CPUExecutionProvider"]).run(
        None, {"wav": x.numpy()})[0]
    print(f"{file}: {(args.out / file).stat().st_size / 1e3:.0f} KB, {len(graph.graph.initializer)} weights in the "
          f"checkpoint, max |onnx - torch| {float(np.abs(got - ref).max()):.1e}")


if __name__ == "__main__":
    main()
