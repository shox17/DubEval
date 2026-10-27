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
