"""Optional downloads: checksums, resuming, stopping, zip extraction, availability, removal (fake server, no network)."""
import hashlib
import io
import json
import os
import zipfile

import pytest

from dubeval import meaning, packs


class FakeResponse:
    def __init__(self, data: bytes, status: int):
        self.data, self.status_code = data, status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, size):
        for i in range(0, len(self.data), 4):
            yield self.data[i:i + 4]


class FakeServer:
    """Serves files by URL, honouring Range requests; counts what it was asked."""
    def __init__(self, files: dict, ranges=True):
        self.files, self.ranges, self.requests = files, ranges, []

    def get(self, url, headers=None, stream=True, timeout=None):
        headers = headers or {}
        self.requests.append((url, headers.get("Range")))
        data = self.files[url]
        if self.ranges and "Range" in headers:
            start = int(headers["Range"].split("=")[1].rstrip("-"))
            return FakeResponse(data[start:], 206)
        return FakeResponse(data, 200)


def entry(url, name, data, **extra):
    return {"url": url, "name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), **extra}


@pytest.fixture
def pack(monkeypatch, tmp_path):
    """One test pack with two files, installed into tmp_path/pack."""
    model, tok = b"model-bytes-" * 10, b'{"tokenizer": true}'
    spec = {"folder": lambda: tmp_path / "pack", "source": "test", "license": "MIT",
            "files": [entry("https://x/model.onnx", "model.onnx", model), entry("https://x/tok.json", "tokenizer.json", tok)]}
    monkeypatch.setattr(packs, "PACKS", {"meaning": spec})
    return {"dir": tmp_path / "pack", "server": FakeServer({"https://x/model.onnx": model, "https://x/tok.json": tok}),
            "model": model}


def test_a_pack_is_downloaded_checked_and_marked_installed(pack):
    seen = []
    info = packs.install("meaning", lambda message, fraction: seen.append(fraction), session=pack["server"])
    assert info["state"] == "installed" and packs.state("meaning") == "installed"
    assert (pack["dir"] / "model.onnx").read_bytes() == pack["model"]
    listed = json.loads((pack["dir"] / "pack.json").read_text(encoding="utf-8"))["files"]
    assert listed == {"model.onnx": {"bytes": len(pack["model"])}, "tokenizer.json": {"bytes": 19}}
    assert seen[-1] == 1.0 and seen == sorted(seen) and not (pack["dir"].parent / "pack.download").exists()


def test_the_installed_meaning_pack_is_what_the_screen_looks_for(pack, monkeypatch):
    monkeypatch.setattr(meaning, "PACK_DIR", pack["dir"])
    assert not meaning._pack_ready()
    packs.install("meaning", session=pack["server"])
    assert meaning._pack_ready()


def test_a_wrong_checksum_installs_nothing(pack):
    pack["server"].files["https://x/model.onnx"] = b"tampered" * 15
    with pytest.raises(ValueError, match="checksum"):
        packs.install("meaning", session=pack["server"])
    assert packs.state("meaning") != "installed" and not (pack["dir"] / "model.onnx").exists()


def test_a_stopped_download_resumes_where_it_left_off(pack):
    calls = iter(range(1000))
    with pytest.raises(packs.Stopped):
        packs.install("meaning", stop=lambda: next(calls) > 5, session=pack["server"])
    assert packs.state("meaning") == "partial"
    part = pack["dir"].parent / "pack.download" / "model.onnx.part"
    have = part.stat().st_size
    assert 0 < have < len(pack["model"])
    pack["server"].requests.clear()
    packs.install("meaning", session=pack["server"])
    assert ("https://x/model.onnx", f"bytes={have}-") in pack["server"].requests
    assert (pack["dir"] / "model.onnx").read_bytes() == pack["model"]


def test_a_server_that_ignores_ranges_starts_the_file_over(pack):
    with pytest.raises(packs.Stopped):
        calls = iter(range(1000))
        packs.install("meaning", stop=lambda: next(calls) > 5, session=pack["server"])
    pack["server"].ranges = False
    packs.install("meaning", session=pack["server"])
    assert (pack["dir"] / "model.onnx").read_bytes() == pack["model"]


def test_a_pack_installed_with_an_earlier_file_list_is_outdated_until_updated(pack):
    packs.install("meaning", session=pack["server"])
    newer = b"a better model " * 20                          # the pack now names another model file
    spec = packs.PACKS["meaning"]
    spec["files"] = [entry("https://x/newer.onnx", "newer.onnx", newer), spec["files"][1]]
    pack["server"].files["https://x/newer.onnx"] = newer
    assert packs.state("meaning") == "outdated"              # not "installed": nothing uses the old model
    assert next(p for p in packs.summary() if p["id"] == "meaning")["disk_mb"] is None
    pack["server"].requests.clear()
    packs.install("meaning", session=pack["server"])
    assert packs.state("meaning") == "installed"
    assert [url for url, _ in pack["server"].requests] == ["https://x/newer.onnx"]     # the kept file wasn't sent again
    assert sorted(f.name for f in pack["dir"].iterdir()) == ["newer.onnx", "pack.json", "tokenizer.json"]


def test_an_outdated_pack_can_be_removed(pack):
    packs.install("meaning", session=pack["server"])
    packs.PACKS["meaning"]["files"] = [entry("https://x/newer.onnx", "newer.onnx", b"x" * 40)]
    assert packs.state("meaning") == "outdated"
    packs.remove("meaning")
    assert packs.state("meaning") == "absent" and not pack["dir"].exists()


def test_files_are_taken_out_of_a_zip_and_the_zip_is_dropped(monkeypatch, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("nvidia/cublas/bin/cublas64_12.dll", b"dll-a")
        z.writestr("nvidia/cublas/bin/other.txt", b"skip")
    wheel = buf.getvalue()
    spec = {"folder": lambda: tmp_path / "cuda", "source": "test", "license": "test", "files": [
        entry("https://x/w.whl", "cublas.whl", wheel, extract={"nvidia/cublas/bin/cublas64_12.dll": "cublas64_12.dll"})]}
    monkeypatch.setattr(packs, "PACKS", {"gpu": spec})
    packs.install("gpu", session=FakeServer({"https://x/w.whl": wheel}))
    assert sorted(p.name for p in (tmp_path / "cuda").iterdir()) == ["cublas64_12.dll", "pack.json"]
    assert packs.state("gpu") == "installed"


def test_the_gpu_pack_is_only_offered_with_an_nvidia_card_on_windows(monkeypatch):
    monkeypatch.setattr(packs, "nvidia_gpu", lambda: False)
    assert not packs.available("gpu")
    with pytest.raises(ValueError, match="isn't available"):
        packs.install("gpu", session=FakeServer({}))
    assert packs.available("meaning") and packs.available("large_model")


def test_removing_a_pack_deletes_it_and_any_half_download(pack):
    packs.install("meaning", session=pack["server"])
    (pack["dir"].parent / "pack.download").mkdir()
    packs.remove("meaning")
    assert packs.state("meaning") == "absent" and not pack["dir"].exists()


def test_every_real_pack_has_a_pinned_source_and_checksum():
    for pack_id, spec in packs.PACKS.items():
        for f in spec["files"]:
            source = f.get("url") or f["zip"]
            assert source.startswith("https://") and len(f["sha256"]) == 64 and f["bytes"] > 0
            assert "/resolve/main/" not in source                 # a fixed revision, never a moving branch
            assert "/latest/" not in source                       # a fixed release, never "the latest"
        assert spec["license"] and spec["source"]


# ---------------- files taken out of a remote zip (the local judge's Ollama) ----------------
class RangeResponse:
    """One answer to a range request."""
    def __init__(self, body: bytes):
        self.status_code, self.content = 206, body

    def iter_content(self, size):
        return [self.content[i:i + size] for i in range(0, len(self.content), size)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class RangeServer:
    """A zip served with HTTP range requests (HEAD gives its size), recording how many bytes were sent."""
    def __init__(self, data: bytes):
        self.data, self.sent = data, 0

    def head(self, url, **kw):
        return RangeHead(url, len(self.data))

    def get(self, url, headers=None, **kw):
        start, end = map(int, headers["Range"].split("=")[1].split("-"))
        self.sent += end + 1 - start
        return RangeResponse(self.data[start:end + 1])


class RangeHead:
    def __init__(self, url, size):
        self.url, self.headers = url, {"content-length": str(size)}


def _zip_with(files: dict) -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_one_file_comes_out_of_a_remote_zip_without_downloading_the_zip(tmp_path):
    exe = b"MZ" + bytes(range(256)) * 400
    server = RangeServer(_zip_with({"ollama.exe": exe, "lib/ollama/cuda_v12/huge.dll": os.urandom(400_000)}))
    f = {"zip": "https://example.com/o.zip", "member": "ollama.exe", "name": "runtime/ollama.exe", "bytes": len(exe),
         "sha256": hashlib.sha256(exe).hexdigest()}
    packs._download(f, tmp_path / f["name"], server, lambda n: None, lambda: False)
    assert (tmp_path / "runtime" / "ollama.exe").read_bytes() == exe
    assert server.sent < 100_000                              # the 400 kB CUDA file was never sent
    bad = {**f, "name": "runtime/bad.exe", "sha256": "0" * 64}
    with pytest.raises(ValueError):
        packs._download(bad, tmp_path / bad["name"], server, lambda n: None, lambda: False)
    assert not (tmp_path / "runtime" / "bad.exe").exists()


def test_a_file_already_in_the_pack_folder_is_checked_not_downloaded_again(tmp_path, monkeypatch):
    blob = b"model weights" * 1000
    pack = {"folder": lambda: tmp_path / "ollama", "source": "test", "license": "MIT",
            "files": [{"url": "https://example.com/blob", "name": "blobs/sha256-x", "bytes": len(blob),
                       "sha256": hashlib.sha256(blob).hexdigest()}]}
    monkeypatch.setitem(packs.PACKS, "test_pack", pack)
    (tmp_path / "ollama" / "blobs").mkdir(parents=True)
    (tmp_path / "ollama" / "blobs" / "sha256-x").write_bytes(blob)          # e.g. an Ollama folder made earlier

    class NoNetwork:
        def get(self, *a, **k):
            raise AssertionError("downloaded again")
    packs.install("test_pack", session=NoNetwork())
    assert packs.state("test_pack") == "installed"
    assert (tmp_path / "ollama" / "blobs" / "sha256-x").read_bytes() == blob


# ---------------- the local translation checker on a Mac ----------------
def test_the_local_checker_is_offered_on_windows_and_on_apple_silicon_macs_only(monkeypatch):
    from dubeval import local_judge
    here = lambda name, platform, machine: (monkeypatch.setattr(local_judge.os, "name", name),
                                            monkeypatch.setattr(local_judge.sys, "platform", platform),
                                            monkeypatch.setattr(local_judge.platform, "machine", lambda: machine))
    here("nt", "win32", "AMD64")
    assert local_judge.this_computer() == "windows" and packs.available("local_judge")
    here("posix", "darwin", "arm64")
    assert local_judge.this_computer() == "mac" and packs.available("local_judge")
    for platform, machine in (("darwin", "x86_64"), ("linux", "x86_64"), ("linux", "aarch64")):
        here("posix", platform, machine)                     # no pinned runtime for an Intel Mac or for Linux
        assert local_judge.this_computer() is None and not packs.available("local_judge")
        with pytest.raises(ValueError, match="isn't available"):
            packs.install("local_judge")


def test_the_local_checker_is_the_gguf_build_of_gemma_4_12b():
    from dubeval import local_judge
    assert local_judge.MODEL == "gemma4:12b-it-q4_K_M"       # the default gemma4:12b needs Ollama's MLX engine on a Mac
    files = local_judge.pack_files("windows")
    manifest = files[-1]
    assert manifest["url"] == "https://registry.ollama.ai/v2/library/gemma4/manifests/12b-it-q4_K_M"
    assert manifest["name"] == "manifests/registry.ollama.ai/library/gemma4/12b-it-q4_K_M"   # where Ollama looks for it
    blobs = [f for f in files if f["name"].startswith("blobs/")]
    assert all(f["name"] == f"blobs/sha256-{f['sha256']}" and f["url"].endswith(f"sha256:{f['sha256']}") for f in blobs)
    assert 7.9e9 < sum(f["bytes"] for f in blobs) < 8.1e9
    assert packs.PACKS["local_judge"]["files"][-1] == local_judge.pack_files()[-1]
    assert "Gemma 4 12B" in next(name for _, model_id, name, _ in packs.CATALOG if model_id == "local_judge")


def test_each_computer_gets_its_own_runtime_and_the_same_model():
    from dubeval import local_judge
    mac, windows = local_judge.pack_files("mac"), local_judge.pack_files("windows")
    runtime = lambda files: [f for f in files if f["name"].startswith("runtime/")]
    assert all(f["zip"] == local_judge.MAC_ZIP and f["member"].startswith(local_judge.MAC_PREFIX) for f in runtime(mac))
    assert all(f["zip"] == local_judge.OLLAMA_ZIP for f in runtime(windows))
    names = {f["name"] for f in runtime(mac)}
    assert {"runtime/ollama", "runtime/llama-server"} <= names and "runtime/ollama.exe" not in names
    assert not any("mlx" in n.lower() for n in names)        # its MLX engine (580 MB) isn't needed for this model
    assert all(len(f["sha256"]) == 64 and f["bytes"] > 0 and "v0.40.9" in f["zip"] for f in runtime(mac))
    assert sum(f["bytes"] for f in runtime(mac)) < 150e6
    model = lambda files: [f for f in files if not f["name"].startswith("runtime/")]
    assert model(mac) == model(windows)
    targets = {name for name, _ in local_judge.MAC_LINKS} | {f["name"][len("runtime/"):] for f in runtime(mac)}
    assert all(target in targets for _, target in local_judge.MAC_LINKS)          # every link leads to a real file
    assert all(f"runtime/{p}" in names for p in local_judge.MAC_PROGRAMS)


@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
def test_a_downloaded_mac_runtime_is_made_runnable(tmp_path, monkeypatch):
    from dubeval import local_judge
    monkeypatch.setattr(local_judge, "this_computer", lambda: "mac")
    for member, _, _ in local_judge.MAC_RUNTIME_FILES:
        (tmp_path / member).write_bytes(b"x")                # as a download leaves it: a plain file, not runnable
        (tmp_path / member).chmod(0o644)
    program = local_judge._prepare(tmp_path)
    assert program == tmp_path / "ollama" and os.access(program, os.X_OK) and os.access(tmp_path / "llama-server", os.X_OK)
    assert (tmp_path / "libllama.dylib").resolve() == (tmp_path / "libllama.0.7.0.dylib").resolve()
    assert local_judge._prepare(tmp_path) == program         # a second start changes nothing


# ---------------- the voice-quality model ----------------
def test_the_voice_quality_pack_is_metas_file_unchanged_from_a_pinned_revision():
    from dubeval import voice_quality
    pack = packs.PACKS["voice_quality"]
    assert pack["folder"]() == voice_quality.PACK_DIR and "CC BY 4.0" in pack["license"]
    (weights,) = pack["files"]
    assert weights["url"].startswith("https://huggingface.co/facebook/audiobox-aesthetics/resolve/")
    assert "/main/" not in weights["url"] and weights["bytes"] == 415472992      # a fixed revision, never "main"
    assert packs.available("voice_quality")                      # every computer: it runs on the processor
