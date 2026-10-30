"""Optional downloads ("packs"): extras a person chooses to install from inside the app, each with its size.

    meaning      the offline meaning screen: BGE-M3 as an int8 ONNX model + its tokenizer (Xenova/bge-m3, MIT)
    gpu          faster speech recognition on an NVIDIA GPU: cuBLAS from NVIDIA's own package on PyPI (Windows only)
    large_model  better speech recognition for less common languages: faster-whisper large-v3-turbo (MIT)
    local_judge  the translation check on this computer: Ollama (CPU + Vulkan, MIT) and Qwen3 8B (Apache-2.0)
                 (dubeval/local_judge.py; Ollama's files are taken out of its release zip with range requests)
    lip_sync     the lip-sync check: ByteDance's StableSyncNet from LatentSync 1.5, unchanged (CreativeML OpenRAIL++-M);
                 dubeval/lip_sync.py runs it with the two small graphs bundled in dubeval/models/

Every file has a pinned source (a fixed revision or version) and a SHA-256 checked before anything is used; a
download that stops half-way resumes where it left off. A pack is installed into its own folder only once every file
is verified, then marked by a pack.json listing its files and sizes. Nothing here runs unless a person asks for it.
"""
import hashlib
import json
import logging
import os
import shutil
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Callable, Optional

from dubeval import asr, lip_sync, local_judge, meaning, network

log = logging.getLogger(__name__)

MODELS_DIR = Path(os.getenv("DUBEVAL_MODELS", Path.home() / ".cache" / "dubeval"))
CHUNK = 1 << 20
HF = "https://huggingface.co"
BGE_M3 = (f"{HF}/Xenova/bge-m3/resolve/4de13258303883538bd53b696b452bf8099f0858", "MIT")
TURBO = (f"{HF}/mobiuslabsgmbh/faster-whisper-large-v3-turbo/resolve/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf", "MIT")
LATENTSYNC = f"{HF}/ByteDance/LatentSync-1.5/resolve/32a20d29aead0498e3e885e90dbbe8027da1b61b"
CUBLAS_WHEEL = ("https://files.pythonhosted.org/packages/20/e2/fc9a0e985249d873150276d5afb02e39a66817fedbf1a385724393e505ed/"
                "nvidia_cublas_cu12-12.9.2.10-py3-none-win_amd64.whl")

# Each file: where it comes from, its name in the pack, its size and SHA-256; `extract` takes files out of a zip.
PACKS = {
    "meaning": {
        "folder": lambda: meaning.PACK_DIR,
        "source": "Xenova/bge-m3 (BAAI BGE-M3, int8 ONNX)", "license": "MIT",
        "files": [
            {"url": f"{BGE_M3[0]}/onnx/model_int8.onnx", "name": "model.onnx", "bytes": 568456694,
             "sha256": "a206e10e995aa2a833924bcd725ba5dd6c3425cd34bac3cf2b5677cd2a1c51d6"},
            {"url": f"{BGE_M3[0]}/tokenizer.json", "name": "tokenizer.json", "bytes": 17082821,
             "sha256": "6710678b12670bc442b99edc952c4d996ae309a7020c1fa0096dd245c2faf790"},
        ],
        "extra": {"name": "bge-m3-int8", "source": "Xenova/bge-m3", "pooling": "cls+l2"},
    },
    "gpu": {
        "folder": lambda: asr.cuda_pack_dir(),
        "source": "NVIDIA cuBLAS 12.9 (nvidia-cublas-cu12 on PyPI)", "license": "NVIDIA software license",
        "windows_only": True, "needs_nvidia": True,
        "files": [
            {"url": CUBLAS_WHEEL, "name": "cublas.whl", "bytes": 553162896,
             "sha256": "623f43027d40d44ceadf0043f002bd25cf353e8f13ce90b9a87057019f560661",
             "extract": {"nvidia/cublas/bin/cublas64_12.dll": "cublas64_12.dll",
                         "nvidia/cublas/bin/cublasLt64_12.dll": "cublasLt64_12.dll"}},
        ],
    },
    "large_model": {
        "folder": lambda: MODELS_DIR / "faster-whisper-large-v3-turbo",
        "source": "mobiuslabsgmbh/faster-whisper-large-v3-turbo", "license": "MIT",
        "files": [
            {"url": f"{TURBO[0]}/model.bin", "name": "model.bin", "bytes": 1617884929,
             "sha256": "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da"},
            {"url": f"{TURBO[0]}/config.json", "name": "config.json", "bytes": 2263,
             "sha256": "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e"},
            {"url": f"{TURBO[0]}/preprocessor_config.json", "name": "preprocessor_config.json", "bytes": 340,
             "sha256": "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711"},
            {"url": f"{TURBO[0]}/tokenizer.json", "name": "tokenizer.json", "bytes": 2710337,
             "sha256": "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd"},
            {"url": f"{TURBO[0]}/vocabulary.json", "name": "vocabulary.json", "bytes": 1068114,
             "sha256": "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1"},
        ],
    },
}
PACKS["lip_sync"] = {
    "folder": lambda: lip_sync.PACK_DIR,
    "source": "ByteDance/LatentSync-1.5 (StableSyncNet)",
    "license": "CreativeML OpenRAIL++-M (weights), Apache-2.0 (LatentSync code)",
    "files": [
        {"url": f"{LATENTSYNC}/stable_syncnet.pt", "name": lip_sync.CHECKPOINT, "bytes": 1605324224,
         "sha256": "dccc464554b85ed939ae5cf63000e5803d4b21d8c7dae2260544a10aeb1ac483"},
    ],
}
PACKS["local_judge"] = {
    "folder": lambda: MODELS_DIR / "ollama",
    "source": "Ollama 0.40.9 (CPU + Vulkan) and Qwen3 8B (Ollama registry)", "license": "MIT (Ollama), Apache-2.0 (Qwen3)",
    "windows_only": True,
    "files": local_judge.pack_files(),
}
LARGE_MODEL = "large-v3-turbo"           # the recognizer name the large_model pack provides

BAD_DOWNLOAD = "The download didn't match its checksum, so it wasn't installed. Try again."
NOT_HERE = "This download isn't available on this computer."
DOWNLOAD_FAILED = "The download failed. Check your internet connection and try again; it continues where it stopped."


class Stopped(RuntimeError):
    """The person stopped the download; what was downloaded is kept for next time."""


def nvidia_gpu() -> bool:
    """Whether an NVIDIA driver is installed (the GPU pack is only offered then)."""
    if os.name == "nt":
        return (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvcuda.dll").is_file()
    return Path("/proc/driver/nvidia/version").exists()


def available(pack_id: str) -> bool:
    """Whether a pack can be installed on this computer."""
    pack = PACKS[pack_id]
    if pack.get("windows_only") and os.name != "nt":
        return False
    return nvidia_gpu() if pack.get("needs_nvidia") else True


def _installed_files(pack: dict) -> dict:
    """The files an installed pack keeps (an extracted zip keeps what was extracted, not the zip)."""
    out = {}
    for f in pack["files"]:
        if "extract" in f:
            out.update({name: None for name in f["extract"].values()})
        else:
            out[f["name"]] = f["bytes"]
    return out


def state(pack_id: str) -> str:
    """installed | partial (a download to resume) | absent."""
    pack = PACKS[pack_id]
    folder = Path(pack["folder"]())
    try:
        listed = json.loads((folder / "pack.json").read_text(encoding="utf-8"))["files"]
        if all((folder / name).stat().st_size == info["bytes"] for name, info in listed.items()):
            return "installed"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return "partial" if _staging(folder).is_dir() and any(_staging(folder).iterdir()) else "absent"


def summary() -> list[dict]:
    """Every pack with its state, sizes and whether this computer can use it."""
    out = []
    for pack_id, pack in PACKS.items():
        download = sum(f["bytes"] for f in pack["files"])
        out.append({"id": pack_id, "state": state(pack_id), "available": available(pack_id),
                    "download_mb": round(download / 1e6), "disk_mb": installed_size_mb(pack_id),
                    "source": pack["source"], "license": pack["license"], "folder": str(pack["folder"]())})
    return out


def _staging(folder: Path) -> Path:
    return folder.with_name(folder.name + ".download")


def _sha256_of(path: Path) -> "hashlib._Hash":
    h = hashlib.sha256()
    if path.exists():
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(CHUNK), b""):
                h.update(block)
    return h


def _zip_index(url: str, session) -> tuple[str, dict]:
    """A remote zip's final address and its members {name: (method, compressed, size, header offset)}, read from its
    central directory with two range requests (the zip itself isn't downloaded)."""
    head = session.head(url, allow_redirects=True, timeout=60)
    size, final = int(head.headers["content-length"]), head.url
    tail = session.get(final, headers={"Range": f"bytes={max(0, size - 65536)}-{size - 1}"}, timeout=60).content
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("not a zip")
    cd_size, cd_off = struct.unpack_from("<II", tail, eocd + 12)
    cd = session.get(final, headers={"Range": f"bytes={cd_off}-{cd_off + cd_size - 1}"}, timeout=120).content
    pos, members = 0, {}
    while cd[pos:pos + 4] == b"PK\x01\x02":
        method, = struct.unpack_from("<H", cd, pos + 10)
        csize, usize = struct.unpack_from("<II", cd, pos + 20)
        nlen, elen, clen = struct.unpack_from("<HHH", cd, pos + 28)
        offset, = struct.unpack_from("<I", cd, pos + 42)
        members[cd[pos + 46:pos + 46 + nlen].decode("utf-8")] = (method, csize, usize, offset)
        pos += 46 + nlen + elen + clen
    return final, members


def _zip_member(f: dict, part: Path, index: tuple[str, dict], session, report, stop) -> "hashlib._Hash":
    """One member of a remote zip (stored or deflated) into part, by range requests; returns its SHA-256."""
    final, members = index
    if f["member"] not in members:
        raise RuntimeError(f"{f['member']} is not in the zip")
    method, csize, _, offset = members[f["member"]]
    local = session.get(final, headers={"Range": f"bytes={offset}-{offset + 29}"}, timeout=60).content
    nlen, elen = struct.unpack_from("<HH", local, 26)
    start = offset + 30 + nlen + elen
    digest, have = hashlib.sha256(), 0
    inflate = zlib.decompressobj(-15) if method == 8 else None
    with session.get(final, headers={"Range": f"bytes={start}-{start + csize - 1}"}, stream=True, timeout=60) as resp, \
            open(part, "wb") as out:
        if resp.status_code != 206:
            raise RuntimeError(f"HTTP {resp.status_code}")
        for chunk in resp.iter_content(CHUNK):
            if stop():
                raise Stopped()
            data = inflate.decompress(chunk) if inflate else chunk
            out.write(data)
            digest.update(data)
            have += len(data)
            report(have)
        if inflate:
            data = inflate.flush()
            out.write(data)
            digest.update(data)
    return digest


def _download(f: dict, target: Path, session, report: Callable[[int], None], stop: Callable[[], bool],
              zips: Optional[dict] = None) -> None:
    """One file into target, resuming a .part file; raises ValueError when its checksum is wrong. A file with "zip"
    and "member" is taken out of that remote zip (zips caches each zip's index for the install)."""
    if target.exists() and target.stat().st_size == f["bytes"] and _sha256_of(target).hexdigest() == f["sha256"]:
        report(f["bytes"])
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if "zip" in f:
        part = target.with_name(target.name + ".part")
        if zips is None:
            zips = {}
        if f["zip"] not in zips:
            zips[f["zip"]] = _zip_index(f["zip"], session)
        digest = _zip_member(f, part, zips[f["zip"]], session, report, stop)
        if part.stat().st_size != f["bytes"] or digest.hexdigest() != f["sha256"]:
            part.unlink(missing_ok=True)
            raise ValueError(BAD_DOWNLOAD)
        os.replace(part, target)
        return
    part = target.with_name(target.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    if have > f["bytes"]:
        part.unlink()
        have = 0
    digest = _sha256_of(part)
    report(have)
    if have < f["bytes"]:
        headers = {**f.get("headers", {}), **({"Range": f"bytes={have}-"} if have else {})}
        with session.get(f["url"], headers=headers, stream=True, timeout=60) as resp:
            if have and resp.status_code == 200:               # the server ignored the range: start over
                have, digest = 0, hashlib.sha256()
                part.unlink(missing_ok=True)
            elif resp.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {resp.status_code}")
            with open(part, "ab") as out:
                for chunk in resp.iter_content(CHUNK):
                    if stop():
                        raise Stopped()
                    out.write(chunk)
                    digest.update(chunk)
                    have += len(chunk)
                    report(have)
    if have != f["bytes"] or digest.hexdigest() != f["sha256"]:
        part.unlink(missing_ok=True)
        raise ValueError(BAD_DOWNLOAD)
    os.replace(part, target)


def install(pack_id: str, progress: Callable[[str, float], None] = lambda message, fraction: None,
            stop: Callable[[], bool] = lambda: False, session=None) -> dict:
    """Downloads, verifies and installs a pack; returns its summary. A stopped or failed download is kept to resume."""
    if pack_id not in PACKS or not available(pack_id):
        raise ValueError(NOT_HERE)
    pack = PACKS[pack_id]
    folder = Path(pack["folder"]())
    staging = _staging(folder)
    staging.mkdir(parents=True, exist_ok=True)
    total = sum(f["bytes"] for f in pack["files"])
    done_before = 0
    if session is None:
        import requests
        session = requests.Session()
    zips: dict = {}
    for f in pack["files"]:
        report = lambda n, base=done_before: progress("Downloading...", min(0.97, (base + n) / total))
        old, new = folder / f["name"], staging / f["name"]
        if not new.exists() and old.is_file() and old.stat().st_size == f["bytes"]:
            new.parent.mkdir(parents=True, exist_ok=True)
            os.replace(old, new)                            # already here (an older install): checked, not downloaded
        try:
            _download(f, new, session, report, stop, zips)
        except (Stopped, ValueError):
            raise
        except Exception as e:                              # network trouble: keep the partial file for next time
            log.warning("Download of %s failed: %s", f["url"], e)
            raise RuntimeError(network.describe(e, DOWNLOAD_FAILED)) from e
        done_before += f["bytes"]
    progress("Installing...", 0.98)
    for f in pack["files"]:
        if "extract" in f:
            with zipfile.ZipFile(staging / f["name"]) as z:
                for member, name in f["extract"].items():
                    with z.open(member) as src, open(staging / name, "wb") as dst:
                        shutil.copyfileobj(src, dst, CHUNK)
            (staging / f["name"]).unlink()
    files = {name: {"bytes": (staging / name).stat().st_size} for name in _installed_files(pack)}
    (staging / "pack.json").write_text(json.dumps({**pack.get("extra", {}), "pack": pack_id, "source": pack["source"],
                                                   "license": pack["license"], "files": files}, indent=2),
                                       encoding="utf-8")
    shutil.rmtree(folder, ignore_errors=True)
    os.replace(staging, folder)
    _changed(pack_id)
    progress("Installed", 1.0)
    return next(p for p in summary() if p["id"] == pack_id)


def remove(pack_id: str) -> None:
    """Deletes an installed pack (and any half-finished download of it)."""
    if pack_id == "local_judge":
        local_judge.stop()                                  # its server holds the files open
    elif pack_id == "lip_sync":
        lip_sync.unload()                                   # the loaded models keep the checkpoint open
    folder = Path(PACKS[pack_id]["folder"]())
    shutil.rmtree(folder, ignore_errors=True)
    shutil.rmtree(_staging(folder), ignore_errors=True)
    _changed(pack_id)


def _changed(pack_id: str) -> None:
    """Lets the running process pick up a pack that appeared or went away."""
    if pack_id == "meaning":
        meaning.unload()
    elif pack_id == "gpu":
        asr._add_cuda_dll_dirs.done = False
        asr._gpu_check.cache_clear()                 # look for the GPU again with the new libraries
        asr.unload()
    elif pack_id == "local_judge":
        from dubeval import translation_judge
        local_judge.stop()
        translation_judge._ollama_seen.clear()
    elif pack_id == "lip_sync":
        lip_sync.unload()


# The Models list (Settings → Models): every model DubEval uses, grouped by what it does, built in or downloadable.
# (group, id, name, where it lives). Names are product names; groups and notes are translated by the page (w.mod.*).
CATALOG = (
    ("speech", "whisper_base", "Whisper base", "builtin"),
    ("speech", "large_model", "Whisper large-v3-turbo", "pack"),
    ("meaning", "meaning", "BGE-M3 (int8)", "pack"),
    ("meaning", "local_judge", "Qwen3 8B (Ollama)", "pack"),
    ("voice", "speaker", "WeSpeaker ResNet34", "builtin"),
    ("voice", "dnsmos", "DNSMOS P.835", "builtin"),
    ("voice", "face", "MediaPipe Face Landmarker", "builtin"),
    ("voice", "lip_sync", "LatentSync StableSyncNet", "pack"),
    ("speed", "gpu", "NVIDIA cuBLAS", "pack"),
    ("base", "engine", "DubEval engine (Python)", "builtin"),
)


def _size(path: Optional[Path]) -> Optional[int]:
    """Bytes in a file or folder, or None if it isn't there."""
    if path is None or not path.exists():
        return None
    return path.stat().st_size if path.is_file() else sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _builtin_bytes(model_id: str) -> Optional[int]:
    """Where a built-in model is on this computer, measured; None when unknown (e.g. not downloaded yet)."""
    from dubeval import speaker, voice_quality
    from dubeval.evaluate import FACE_MODEL_PATH
    from dubeval.paths import BUNDLED_MODELS
    if model_id == "whisper_base":
        local = asr._local_model("base")
        hf = Path(os.getenv("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub" / \
            "models--Systran--faster-whisper-base"
        return _size(Path(local)) if local else _size(hf)
    if model_id == "speaker":
        shipped = BUNDLED_MODELS / speaker.MODEL_NAME if BUNDLED_MODELS else None
        return _size(shipped) if shipped and shipped.exists() else _size(speaker.CACHE_DIR / speaker.MODEL_NAME)
    if model_id == "dnsmos":
        return _size(voice_quality.MODEL_PATH)
    if model_id == "face":
        return _size(Path(FACE_MODEL_PATH))
    if model_id == "engine" and BUNDLED_MODELS:
        try:
            info = json.loads((BUNDLED_MODELS.parent / "build.json").read_text(encoding="utf-8"))
            return int(info["python_mb"]) * 1_000_000
        except (OSError, ValueError, KeyError, TypeError):
            return None
    return None


def catalog() -> dict:
    """The Models list: groups of rows {id, name, kind, state, bytes, available}, and what is on this computer."""
    packs = {p["id"]: p for p in summary()}
    groups: dict[str, list] = {}
    for group, model_id, name, kind in CATALOG:
        if kind == "pack":
            p = packs[model_id]
            row = {"id": model_id, "name": name, "kind": "pack", "state": p["state"], "available": p["available"],
                   "bytes": (p["disk_mb"] or p["download_mb"]) * 1_000_000, "download_mb": p["download_mb"],
                   "source": p["source"], "license": p["license"]}
        else:
            size = _builtin_bytes(model_id)
            row = {"id": model_id, "name": name, "kind": "builtin",
                   "state": "builtin" if size or model_id == "engine" else "auto",
                   "available": True, "bytes": size}
        groups.setdefault(group, []).append(row)
    ready = [r for rows in groups.values() for r in rows if r["state"] in ("builtin", "installed")]
    return {"groups": [{"id": g, "rows": rows} for g, rows in groups.items()],
            "ready": len(ready), "bytes": sum(r["bytes"] or 0 for r in ready)}


def installed_size_mb(pack_id: str) -> Optional[int]:
    """Disk space an installed pack takes."""
    folder = Path(PACKS[pack_id]["folder"]())
    if state(pack_id) != "installed":
        return None
    return round(sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) / 1e6)
