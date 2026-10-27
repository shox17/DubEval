"""The local translation checker: Qwen3 8B run by Ollama on this computer, downloaded from Settings → Models.

Only what DubEval needs of Ollama v0.40.9 for Windows is downloaded: ollama.exe, its CPU libraries and
the Vulkan GPU backend (any NVIDIA, AMD or Intel card; ~40 MB to download), taken out of the official release zip
with range requests instead of its 1.6 GB of CUDA builds. The model's files come from Ollama's registry, which names
every file by its SHA-256. Every file is pinned (size and SHA-256) like DubEval's other packs (dubeval/packs.py) and
laid out the way Ollama keeps models, so an Ollama model folder that already has Qwen3 is reused, not downloaded again.

When the checker runs, DubEval starts its own Ollama on a free port of 127.0.0.1 with this folder, and stops it when
DubEval quits. DUBEVAL_OLLAMA_URL still points DubEval at another Ollama instead.
"""
import atexit
import logging
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

OLLAMA_ZIP = "https://github.com/ollama/ollama/releases/download/v0.40.9/ollama-windows-amd64.zip"
REGISTRY = "https://registry.ollama.ai/v2/library/qwen3"
MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"
MANIFEST_PATH = "manifests/registry.ollama.ai/library/qwen3/8b"
MANIFEST = (859, "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41")
START_TIMEOUT_SEC = 60

# (member of the release zip, bytes, SHA-256); each is kept as runtime/<member>.
RUNTIME_FILES = (
    ("lib/ollama/CPP_HTTPLIB_LICENSE", 1097, "bb546eae5924d8ee842e0e567e6d533c5824bdebccf605f99a5b3429034e6697"),
    ("lib/ollama/GO_LICENSE", 182211, "4285a95875d7a3ae3790910d59ee88f82339d0ba37b1cbadde4124113bd04308"),
    ("lib/ollama/LLAMA_CPP_LICENSE", 1099, "bcd8ec749126d45cb06737d0690295d73df4b6e7e194205bcf91190368f27285"),
    ("lib/ollama/LLAMA_CPP_VENDORS_LICENSE", 7424, "7547ae6372a35e7382898dd9f5519ebc16e93095f69c2466b5b74b617c33d4da"),
    ("lib/ollama/ggml-base.dll", 821640, "862b3b35b0b7aadc04b5e5cea7863c2d3637d15ecadebaadb075337fc2df17f7"),
    ("lib/ollama/ggml-cpu-alderlake.dll", 1733512, "d1dec12e98809b99300b95fe872852e7478c0eaeacd0e5c0185cbf894907ec9d"),
    ("lib/ollama/ggml-cpu-cannonlake.dll", 2020232, "2c261ac2dfee4b687380dcaa4bfc46f0c087193fbba4e03822e0a4d318eb61db"),
    ("lib/ollama/ggml-cpu-cascadelake.dll",
     1990024, "a4a7fa04db01a1ced4bbe1156e756f89f30bb1f5de671095c3e7d9835eb72d00"),
    ("lib/ollama/ggml-cpu-cooperlake.dll", 1988488, "0f614cea0240f49a68535d38b3f0bdf1162d3b0082dc00a127ec4859c4a1beab"),
    ("lib/ollama/ggml-cpu-haswell.dll", 1740680, "b43874150a88341f6de59ada14fc8296abfb79ce191a4226d556d6a89052ff89"),
    ("lib/ollama/ggml-cpu-icelake.dll", 1997704, "f0091cfb0f7e42a627a7c76978c35e5deba2566046a05efc38625aa159a12023"),
    ("lib/ollama/ggml-cpu-ivybridge.dll", 1619336, "23ea77b17294f2a01a28747bcd37199916f577964b12a04cebdc67ec4be395ea"),
    ("lib/ollama/ggml-cpu-piledriver.dll", 1625480, "3fbbef77950cfefd4c261a73040d2e641be072e1d9dcadb1e4bbb1b557e3e84e"),
    ("lib/ollama/ggml-cpu-sandybridge.dll",
     1638792, "34fe2b037e84e3cd38c4c4fc09c3ddf7e521b948a4c0e4c3471b91d4c67e3f99"),
    ("lib/ollama/ggml-cpu-sapphirerapids.dll",
     2289544, "3e5cf1b91819e809dc0a351ff06177d267c4ed1ad15ef1ef59f702fd6e48b81a"),
    ("lib/ollama/ggml-cpu-skylakex.dll", 2013064, "a43a40dc091f1fe484d93231753118687f961f111a150dd6d3c1ed641a65d035"),
    ("lib/ollama/ggml-cpu-sse42.dll", 1264008, "c63c75b7dc6fc9e0a1e36c383943a202d0a309ae148b9b4c35af550a931ed37e"),
    ("lib/ollama/ggml-cpu-x64.dll", 1250696, "54e1de79ccd541ca4b7a929f4c095057bc3c717585dab98578f792def41f57e5"),
    ("lib/ollama/ggml-cpu-zen4.dll", 1996168, "9a1bb0496616c9af8953780b7fb7d75954b71041d24fa1d8098b2c098ee046e5"),
    ("lib/ollama/ggml.dll", 49032, "f5e4b0923c651a668a2e0f7489f2cac286a776e372a66566659a08a6b4071a30"),
    ("lib/ollama/libc++.dll", 1767816, "dc18e9fce70d94f39d9da0ea6be4e7d0f75e3483b6e0ba1a766990badd5a654b"),
    ("lib/ollama/libllama-common.dll", 4363144, "ca5ad376b7d383c325fc4e21af8ea096e27b0b7199dd13cd6a1501c623e57ad3"),
    ("lib/ollama/libllama-quantize-impl.dll",
     83848, "8ef2eb3d3cd7b70255dd9359c1563e069315441d14d3aa91aff83d479bf47511"),
    ("lib/ollama/libllama-server-impl.dll",
     2822536, "5320fa52677a2e76af1c01c78ed3a1ac2f9ea7211cd7ddd3b0646cb7a97d4341"),
    ("lib/ollama/libllama.dll", 3917192, "777a2c4d5c384910bcf2275897972af833e35de8ece3e687c458be588e6bfd08"),
    ("lib/ollama/libmtmd.dll", 1529224, "a4447a39b739ce79181c877fc451f93a3e43b98d36a7ff54b81a57921ac97d4b"),
    ("lib/ollama/libomp.dll", 965000, "4e2cbbc7483ec984cf97eba85f6e1bc6541c44c6823064f8e7be6b313dbf29a1"),
    ("lib/ollama/libunwind.dll", 107912, "8f94d4890499e2cb7ed7c4b06a25c839f3483cc628551df9825e6a06bcf89f2d"),
    ("lib/ollama/libwinpthread-1.dll", 390024, "8cbb9efc6d5b6d6a5f365e3e9cb277d82beb903cdcaa80fe84a12cc73ab5eea1"),
    ("lib/ollama/llama-quantize.exe", 22920, "75dab702498ba88739c050818f00d2face10c856acff7477713e5297dcaf76cc"),
    ("lib/ollama/llama-server.exe", 22920, "44b16537d275e45931c012b2334155238816b846a391fc0c224b81867f57e743"),
    ("lib/ollama/vulkan/concrt140.dll", 311688, "b84efca0f9c1f152e0657f4cb529ba3711980c6f02c72114e7435dd5e5c73387"),
    ("lib/ollama/vulkan/ggml-vulkan.dll", 39998344, "574fa5fe5b0ec7022277d2f0e33f39a6dbfd7a83999c42b85c4cb741e3e8f746"),
    ("lib/ollama/vulkan/msvcp140.dll", 545160, "eff79bc05e7de747d6510cc9cc8ecc28290e73b8b69694a468be8d6213722e97"),
    ("lib/ollama/vulkan/msvcp140_1.dll", 23432, "f1a05284df2ba983939124ab29082da98029a27aecedc7700760de3618d4b95e"),
    ("lib/ollama/vulkan/msvcp140_2.dll", 267656, "d7898556d2227e22820a69adc2781a553eb702c7a4c523db98ff9fe9c162eb7f"),
    ("lib/ollama/vulkan/msvcp140_atomic_wait.dll",
     37768, "8011ea5c06664d9e9a1e4eb2d4e2bf22244788747375385d56a13becfe6e41fa"),
    ("lib/ollama/vulkan/msvcp140_codecvt_ids.dll",
     19336, "ab6d0a934f686eecae3b926c068e992467b27f8870a3d254beeffa52fda4d082"),
    ("lib/ollama/vulkan/vccorlib140.dll", 339848, "2c62713c7946423e677c08b840e6d2ad1b14f50b47f9142be3003c84122ec88f"),
    ("lib/ollama/vulkan/vcruntime140.dll", 112008, "43eac0c6ecb7cda1d228ba61186cfd7404c914ed9417581b4eb4f716a82f53c5"),
    ("lib/ollama/vulkan/vcruntime140_1.dll", 37256, "bae1e6a3ae4c43c979d2ddba5af1e071bec0c2bd9724709154c070627ca3debf"),
    ("lib/ollama/vulkan/vcruntime140_threads.dll",
     25992, "2f5bff2a87544dc1ce3f30582555e2add8969abbaac32c0e81fa67cfda00e5c3"),
    ("ollama.exe", 37799816, "0957bdaa7b52e163cdc7feb1275653f27c6b32e8ba309e957bdbb83493e97a4b"),
)
# The model's files (the manifest's config and layers): (SHA-256, bytes); kept as blobs/sha256-<SHA-256>.
MODEL_BLOBS = (
    ("05a61d37b08453e59290add468e3bb2f688e23a01e967fecb0e2fa41218cea76", 487),
    ("a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f", 5225374496),
    ("ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4", 1723),
    ("d18a5cc71b84bc4af394a31116bd3932b42241de70c77d2b76d69a314ec8aa12", 11338),
    ("cff3f395ef3756ab63e58b0ad1b32bb6f802905cae1472e6a12034e4246fbbdb", 120),
)


def pack_files() -> list[dict]:
    """The pack's files for dubeval/packs.py: the runtime out of the release zip, then the model and its manifest."""
    files = [{"zip": OLLAMA_ZIP, "member": member, "name": f"runtime/{member}", "bytes": size, "sha256": sha}
             for member, size, sha in RUNTIME_FILES]
    files += [{"url": f"{REGISTRY}/blobs/sha256:{sha}", "name": f"blobs/sha256-{sha}", "bytes": size, "sha256": sha}
              for sha, size in MODEL_BLOBS]
    files.append({"url": f"{REGISTRY}/manifests/8b", "headers": {"Accept": MANIFEST_ACCEPT}, "name": MANIFEST_PATH,
                  "bytes": MANIFEST[0], "sha256": MANIFEST[1]})
    return files


_server: Optional[subprocess.Popen] = None
_url: Optional[str] = None
_lock = threading.Lock()


def folder() -> Path:
    """Where the pack lives (the runtime and the model)."""
    from dubeval import packs
    return Path(packs.PACKS["local_judge"]["folder"]())


def installed() -> bool:
    from dubeval import packs
    return packs.state("local_judge") == "installed"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _answers(url: str) -> bool:
    try:
        return requests.get(f"{url}/api/version", timeout=1).ok
    except requests.RequestException:
        return False


def ensure_running() -> Optional[str]:
    """The address of DubEval's own Ollama, started now if needed; None when the pack isn't installed or Ollama
    doesn't start (the log says why)."""
    global _server, _url
    with _lock:
        if _server is not None and _server.poll() is None and _url and _answers(_url):
            return _url
        if not installed():
            return None
        from dubeval.paths import DATA_DIR
        port = _free_port()
        url = f"http://127.0.0.1:{port}"
        env = {**os.environ, "OLLAMA_HOST": f"127.0.0.1:{port}", "OLLAMA_MODELS": str(folder()),
               "OLLAMA_VULKAN": "1", "OLLAMA_NOPRUNE": "1", "OLLAMA_NO_CLOUD": "1"}
        logs = Path(DATA_DIR) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        out = open(logs / "ollama.log", "ab")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            _server = subprocess.Popen([str(folder() / "runtime" / "ollama.exe"), "serve"], env=env, stdout=out,
                                       stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags)
        except OSError as e:
            log.warning("Could not start the local translation checker: %s", e)
            return None
        finally:
            out.close()
        deadline = time.monotonic() + START_TIMEOUT_SEC
        while time.monotonic() < deadline and _server.poll() is None:
            if _answers(url):
                _url = url
                return url
            time.sleep(0.3)
        log.warning("The local translation checker didn't start (see logs/ollama.log)")
        _stop_locked()
        return None


def running_url() -> Optional[str]:
    """The address of DubEval's own Ollama if it is running now."""
    return _url if _server is not None and _server.poll() is None else None


def _stop_locked() -> None:
    global _server, _url
    if _server is not None and _server.poll() is None:
        _server.terminate()
        try:
            _server.wait(10)
        except subprocess.TimeoutExpired:
            _server.kill()
    _server, _url = None, None


def stop() -> None:
    """Stops DubEval's own Ollama (when DubEval quits, or the pack is removed)."""
    with _lock:
        _stop_locked()


atexit.register(stop)
