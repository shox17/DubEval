# Bundled models

| File | What it does | Source and license |
|---|---|---|
| `face_landmarker.task` | Face landmarks for the lip-movement measure (MediaPipe) | Google MediaPipe Face Landmarker, Apache License 2.0 |
| `dnsmos_sig_bak_ovr.onnx` | Voice-quality scores (DNSMOS P.835: speech signal, background, overall) | Microsoft DNS Challenge, `DNSMOS/DNSMOS/sig_bak_ovr.onnx` from https://github.com/microsoft/DNS-Challenge, licensed CC BY 4.0. Reference: Reddy, Gopal, Cutler, "DNSMOS P.835: A non-intrusive perceptual objective speech quality metric to evaluate noise suppressors", ICASSP 2022. Unmodified. SHA-256 `269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd` |

| `syncnet_audio.onnx`, `syncnet_visual.onnx` | The lip-sync check's two encoders (`dubeval/lip_sync.py`), as graphs only: no weights inside | Rebuilt from ByteDance's LatentSync (`latentsync/models/stable_syncnet.py`, `attention.py`; Copyright 2024 Bytedance Ltd. and/or its affiliates, Apache License 2.0) by `tools/build_syncnet_onnx.py`. Every weight is external data that points into `stable_syncnet.pt` from https://huggingface.co/ByteDance/LatentSync-1.5 (revision `32a20d29aead0498e3e885e90dbbe8027da1b61b`, SHA-256 `dccc464554b85ed939ae5cf63000e5803d4b21d8c7dae2260544a10aeb1ac483`), which the `lip_sync` download (Settings → Models) fetches unchanged. Those weights are licensed under the CreativeML OpenRAIL++-M license, whose use restrictions apply to anyone who downloads them: read it on that page before installing |

The first two are small and loaded from this folder, so the tool works offline once installed. The lip-sync graphs do
nothing until their download is installed.
