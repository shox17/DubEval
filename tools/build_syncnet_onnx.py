"""Builds the lip-sync check's two ONNX graphs (dubeval/models/syncnet_audio.onnx, syncnet_visual.onnx).

    python tools/build_syncnet_onnx.py <stable_syncnet.pt> [--out DIR]

Developer tool: needs torch and onnx (the development environment has them). The graphs hold no weights: every
weight is "external data" that points straight into ByteDance's own stable_syncnet.pt (LatentSync 1.5), which the
lip-sync pack downloads unchanged from Hugging Face (dubeval/packs.py). So DubEval ships ~300 KB of graph and never
redistributes the 1.6 GB of weights; onnxruntime reads them from the checkpoint, which torch saves uncompressed.

The network is rebuilt here from LatentSync's latentsync/models/stable_syncnet.py and attention.py (Copyright 2024
Bytedance Ltd. and/or its affiliates, Apache-2.0), with diffusers' GEGLU feed-forward written out. Weights load
strictly (every name and shape must match), and the result is checked against torch on random input.
"""
import argparse
import pickle
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dubeval import lip_sync  # noqa: E402

AUDIO = dict(in_channels=1, block_out_channels=[32, 64, 128, 256, 512, 1024, 2048],
             downsample_factors=[[2, 1], 2, 2, 1, 2, 2, [2, 3]], attn_blocks=[0, 0, 0, 1, 1, 0, 0])
VISUAL = dict(in_channels=48, block_out_channels=[64, 128, 256, 256, 512, 1024, 2048, 2048],
              downsample_factors=[[1, 2], 2, 2, 2, 2, 2, 2, 2], attn_blocks=[0, 0, 0, 0, 1, 1, 0, 0])


def network():
    """StableSyncNet's two encoders as torch modules (imported here so dubeval never needs torch)."""
    import torch
    from torch import nn
    from torch.nn import functional as F

    class ResnetBlock2D(nn.Module):
        def __init__(self, in_channels, out_channels, downsample_factor=2, groups=32, eps=1e-6):
            super().__init__()
            self.norm1 = nn.GroupNorm(groups, in_channels, eps=eps, affine=True)
            self.conv1 = nn.Conv2d(in_channels, out_channels, 3, 1, 1)
            self.norm2 = nn.GroupNorm(groups, out_channels, eps=eps, affine=True)
            self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, 1)
            self.act_fn = nn.SiLU()
            self.conv_shortcut = nn.Conv2d(in_channels, out_channels, 1, 1, 0) if in_channels != out_channels else None
            if isinstance(downsample_factor, list):
                downsample_factor = tuple(downsample_factor)
            if downsample_factor == 1:
                self.downsample_conv = None
            else:
                self.downsample_conv = nn.Conv2d(out_channels, out_channels, 3, stride=downsample_factor, padding=0)
                self.pad = (0, 1, 0, 1)
                if isinstance(downsample_factor, tuple):
                    if downsample_factor[0] == 1:
                        self.pad = (0, 1, 1, 1)
                    elif downsample_factor[1] == 1:
                        self.pad = (1, 1, 0, 1)

        def forward(self, x):
            h = self.conv1(self.act_fn(self.norm1(x)))
            h = self.conv2(self.act_fn(self.norm2(h)))
            if self.conv_shortcut is not None:
                x = self.conv_shortcut(x)
            h = h + x
            if self.downsample_conv is not None:
                h = self.downsample_conv(F.pad(h, self.pad, mode="constant", value=0))
            return h

    class Attention(nn.Module):
        def __init__(self, dim, heads=8):
            super().__init__()
            self.heads = heads
            self.to_q, self.to_k, self.to_v = (nn.Linear(dim, dim, bias=True) for _ in range(3))
            self.to_out = nn.ModuleList([nn.Linear(dim, dim), nn.Dropout(0.0)])

        def forward(self, x):
            b, n, d = x.shape
            split = lambda t: t.reshape(b, n, self.heads, d // self.heads).permute(0, 2, 1, 3)  # noqa: E731
            q, k, v = split(self.to_q(x)), split(self.to_k(x)), split(self.to_v(x))
            attn = torch.softmax(torch.matmul(q, k.transpose(-1, -2)) * (d // self.heads) ** -0.5, dim=-1)
            return self.to_out[0](torch.matmul(attn, v).permute(0, 2, 1, 3).reshape(b, n, d))

    class GEGLU(nn.Module):
        def __init__(self, dim, inner):
            super().__init__()
            self.proj = nn.Linear(dim, inner * 2)

        def forward(self, x):
            h, gate = self.proj(x).chunk(2, dim=-1)
            return h * F.gelu(gate)

    class FeedForward(nn.Module):
        """diffusers' FeedForward(dim, activation_fn="geglu"): net = [GEGLU, Dropout, Linear]."""
        def __init__(self, dim, mult=4):
            super().__init__()
            self.net = nn.ModuleList([GEGLU(dim, dim * mult), nn.Dropout(0.0), nn.Linear(dim * mult, dim)])

        def forward(self, x):
            for m in self.net:
                x = m(x)
            return x

    class AttentionBlock2D(nn.Module):
        def __init__(self, dim, groups=32):
            super().__init__()
            self.norm1 = nn.GroupNorm(groups, dim, eps=1e-6, affine=True)
            self.norm2 = nn.LayerNorm(dim)
            self.norm3 = nn.LayerNorm(dim)
            self.ff = FeedForward(dim)
            self.conv_in = nn.Conv2d(dim, dim, 1)
            self.conv_out = nn.Conv2d(dim, dim, 1)
            self.attn = Attention(dim, heads=8)

        def forward(self, x):
            b, c, hh, ww = x.shape
            h = self.conv_in(self.norm1(x)).flatten(2).transpose(1, 2)
            h = self.attn(self.norm2(h)) + h
            h = self.ff(self.norm3(h)) + h
            return self.conv_out(h.transpose(1, 2).reshape(b, c, hh, ww)) + x

    class DownEncoder2D(nn.Module):
        def __init__(self, in_channels, block_out_channels, downsample_factors, attn_blocks, groups=32):
            super().__init__()
            self.conv_in = nn.Conv2d(in_channels, block_out_channels[0], 3, 1, 1)
            self.down_blocks = nn.ModuleList([])
            out = block_out_channels[0]
            for i, ch in enumerate(block_out_channels):
                inp, out = out, ch
                self.down_blocks.append(ResnetBlock2D(inp, out, downsample_factors[i], groups))
                if attn_blocks[i] == 1:
                    self.down_blocks.append(AttentionBlock2D(out, groups))
            self.norm_out = nn.GroupNorm(groups, block_out_channels[-1], eps=1e-6)
            self.act_fn_out = nn.ReLU()

        def forward(self, x):
            x = self.conv_in(x)
            for block in self.down_blocks:
                x = block(x)
            return self.act_fn_out(self.norm_out(x))

    class Encoder(nn.Module):
        """One side of StableSyncNet: the embedding, flattened and made a unit vector (as StableSyncNet.forward does)."""
        def __init__(self, encoder):
            super().__init__()
            self.encoder = encoder

        def forward(self, x):
            e = self.encoder(x)
            return F.normalize(e.reshape(e.shape[0], -1), p=2, dim=1)

    return DownEncoder2D, Encoder


class _Storage:
    def __init__(self, kind):
        self.kind = kind


class _Unpickler(pickle.Unpickler):
    """Reads the checkpoint's pickle without running it: only the names a plain state_dict uses are allowed."""
    def find_class(self, module, name):
        if (module, name) == ("collections", "OrderedDict"):
            import collections
            return collections.OrderedDict
        if (module, name) == ("torch._utils", "_rebuild_tensor_v2"):
            return lambda storage, offset, size, stride, *rest: (storage, offset, tuple(size), tuple(stride))
        if module == "torch" and name.endswith("Storage"):
            return _Storage(name)
        raise pickle.UnpicklingError(f"not allowed: {module}.{name}")

    def persistent_load(self, pid):
        kind, storage, key, _location, _numel = pid
        assert kind == "storage"
        return storage.kind, key


def weight_offsets(pt: Path) -> dict:
    """Each state_dict tensor's (byte offset, byte length, shape) inside the checkpoint file."""
    z = zipfile.ZipFile(pt)
    if {i.compress_type for i in z.infolist()} != {zipfile.ZIP_STORED}:
        raise SystemExit("the checkpoint is compressed; onnxruntime can't read weights out of it")
    root = z.infolist()[0].filename.split("/")[0]
    state = _Unpickler(z.open(f"{root}/data.pkl")).load()["state_dict"]
    starts = {}
    with open(pt, "rb") as f:
        for info in z.infolist():
            f.seek(info.header_offset)
            nlen, elen = struct.unpack("<HH", f.read(30)[26:30])
            starts[info.filename] = info.header_offset + 30 + nlen + elen
    out = {}
    for name, ((kind, key), offset, size, stride) in state.items():
        if kind != "FloatStorage":
            raise SystemExit(f"{name}: {kind}, expected float32")
        if stride != tuple(int(np.prod(size[i + 1:])) for i in range(len(size))):
            raise SystemExit(f"{name}: not contiguous")
        out[name] = (starts[f"{root}/data/{key}"] + offset * 4, int(np.prod(size)) * 4, size)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("checkpoint", type=Path, help="stable_syncnet.pt from ByteDance/LatentSync-1.5")
    ap.add_argument("--out", type=Path, default=Path(lip_sync.GRAPHS_DIR))
    args = ap.parse_args()
    import onnx
    import onnxruntime as ort
    import torch

    from dubeval import packs
    expected = packs.PACKS["lip_sync"]["files"][0]
    if args.checkpoint.stat().st_size != expected["bytes"] or packs._sha256_of(args.checkpoint).hexdigest() != expected["sha256"]:
        raise SystemExit("this isn't the pinned stable_syncnet.pt (size or SHA-256 differ)")
    where = weight_offsets(args.checkpoint)
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)["state_dict"]
    DownEncoder2D, Encoder = network()
    rng = np.random.default_rng(0)
    for side, cfg, shape, file in (("audio_encoder", AUDIO, lip_sync.AUDIO_SHAPE, lip_sync.AUDIO_GRAPH),
                                   ("visual_encoder", VISUAL, lip_sync.VISUAL_SHAPE, lip_sync.VISUAL_GRAPH)):
        enc = DownEncoder2D(**cfg)
        enc.load_state_dict({k[len(side) + 1:]: v for k, v in state.items() if k.startswith(side + ".")}, strict=True)
        model = Encoder(enc).eval()
        x = torch.from_numpy(rng.standard_normal((2, *shape)).astype(np.float32))
        with torch.no_grad():
            ref = model(x).numpy()
        with tempfile.TemporaryDirectory() as tmp:
            # No constant folding, so every initializer is a state_dict tensor as saved (no transposed copies).
            torch.onnx.export(model, x, str(Path(tmp) / file), input_names=["x"], output_names=["embedding"],
                              dynamic_axes={"x": {0: "batch"}, "embedding": {0: "batch"}}, opset_version=17,
                              do_constant_folding=False, dynamo=False)
            graph = onnx.load(str(Path(tmp) / file))
        for init in graph.graph.initializer:
            key = f"{side}.{init.name.removeprefix('encoder.')}"
            if key not in where:
                raise SystemExit(f"{init.name}: not a checkpoint tensor")
            offset, length, size = where[key]
            if tuple(init.dims) != size:
                raise SystemExit(f"{init.name}: shape {tuple(init.dims)} != {size}")
            init.ClearField("raw_data")
            init.data_location = onnx.TensorProto.EXTERNAL
            del init.external_data[:]
            for k, v in (("location", lip_sync.CHECKPOINT), ("offset", str(offset)), ("length", str(length))):
                entry = init.external_data.add()
                entry.key, entry.value = k, v
        args.out.mkdir(parents=True, exist_ok=True)
        onnx.save(graph, str(args.out / file))
        opts = ort.SessionOptions()
        opts.add_session_config_entry("session.model_external_initializers_file_folder_path", str(args.checkpoint.parent))
        got = ort.InferenceSession((args.out / file).read_bytes(), opts, providers=["CPUExecutionProvider"]).run(
            None, {"x": x.numpy()})[0]
        print(f"{file}: {(args.out / file).stat().st_size / 1e3:.0f} KB, {len(graph.graph.initializer)} weights in the "
              f"checkpoint, max |onnx - torch| {float(np.abs(got - ref).max()):.1e}")


if __name__ == "__main__":
    main()
