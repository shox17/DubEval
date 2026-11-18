"""The local translation checker: Gemma 4 12B run by Ollama on this computer, downloaded from Settings → Models.
It replaced Qwen3 8B on 2026-11-13 (docs/validation.md: the planted-mistake test on both computers).

Only what DubEval needs of Ollama v0.40.9 is downloaded, taken out of the official release zip with range requests.
On Windows: ollama.exe, its CPU libraries and the Vulkan GPU backend (any NVIDIA, AMD or Intel card; ~40 MB to
download) instead of the zip's 1.6 GB of CUDA builds. On a Mac with Apple silicon: the ollama program, llama-server
and their libraries (Metal is built in; ~45 MB) out of Ollama.app, without its window, updater and MLX engine
(580 MB). The model's files come from Ollama's registry, which names every file by its SHA-256: the GGUF build
(MODEL names its tag; the registry's default gemma4:12b needs Ollama's MLX engine on a Mac, this one doesn't), with
its small draft model and projector, as tested. Every file is pinned (size and SHA-256) like DubEval's other packs
(dubeval/packs.py) and laid out the way Ollama keeps models, so files already in the pack's folder are reused, not
downloaded again. tools/pin_ollama_runtime.py prints the runtime's pins.

When the checker runs, DubEval starts its own Ollama on a free port of 127.0.0.1 with this folder, and stops it when
DubEval quits. DUBEVAL_OLLAMA_URL still points DubEval at another Ollama instead.
"""
import atexit
import logging
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

OLLAMA_ZIP = "https://github.com/ollama/ollama/releases/download/v0.40.9/ollama-windows-amd64.zip"
MAC_ZIP = "https://github.com/ollama/ollama/releases/download/v0.40.9/Ollama-darwin.zip"
MAC_PREFIX = "Ollama.app/Contents/Resources/"             # where the runtime is inside the Mac zip
MODEL = "gemma4:12b-it-q4_K_M"                            # the name the judge asks Ollama for
MODEL_NAME = "Gemma 4 12B"
REGISTRY = "https://registry.ollama.ai/v2/library/" + MODEL.split(":")[0]
MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"
MANIFEST_PATH = "manifests/registry.ollama.ai/library/" + MODEL.replace(":", "/")
# The registry gives a manifest by tag only, so the tag is pinned by its bytes: a republished tag fails the check.
MANIFEST = (1299, "6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b")
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
# The Mac runtime (Apple silicon): (member under MAC_PREFIX, bytes, SHA-256), each kept as runtime/<member>.
MAC_RUNTIME_FILES = (
    ("CPP_HTTPLIB_LICENSE", 1075, "4b45cbe16d7b71b89ae6127e26e0d90a029198ca5e958ad8e3d0b8bbed364d8b"),
    ("FMT_LICENSE", 1431, "07580f2a3b35709ce703d523f447b242f6dfec7582a8c0df102c7fa2849375f8"),
    ("GO_LICENSE", 163159, "3d4141fbdef53a211326be2e0278e1b9959b4d848bcf727dd230636a3523c00c"),
    ("JSON_LICENSE.MIT", 1076, "86b998c792894ccb911a1cb7994f7a9652894e7a094c0b5e45be2f553f45cf14"),
    ("LLAMA_CPP_LICENSE", 1078, "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d"),
    ("LLAMA_CPP_VENDORS_LICENSE", 7257, "eb17b411e39c75c4ac40916d66e39287ee9723b8bbe54daf020fc27acf670c11"),
    ("METAL_CPP_LICENSE.txt", 11344, "f4e92c7fe2aa066e294c0da9d08683dc9fb741ee6e6debbfad99a0c96e07c1f2"),
    ("PICOJSON_LICENSE", 1414, "52a7da16781b4b899382c9ddfcf059235cdee73e2f45cfd7402c2ae9a2e9d28d"),
    ("libggml-base.0.27.0.dylib", 794768, "c25c41e069dbd38caddea839bec3b906e1bfd789f0642e83e4b9bbca71e4b720"),
    ("libggml-blas.so", 52560, "5d6d361695f48bd147e343ac41ae17c982e541130dcc4749f89759b9301f7876"),
    ("libggml.0.27.0.dylib", 57728, "f0f0ffa906254c41dcef6ac0d2eb1e44d751ff3285836b44b36d9668fa71e5c3"),
    ("libllama-common.0.7.0.dylib", 5542320, "0a021ea00e6328ce951d7d331138d6cc080540f3466ac41b3c3bd9e84e2ae1d2"),
    ("libllama-quantize-impl.dylib", 89984, "6322090306333dbe60678afa556296dcdcdf1b5521731172af671ac8c0b119da"),
    ("libllama-server-impl.dylib", 3794944, "c9d3c06fe860e99823811e0716766fae9589b40b800b91cbcb9f78dda1df2a7c"),
    ("libllama.0.7.0.dylib", 4118768, "efb6db98926a18c876f674112674f3546dd0a1c6da606d8daf171ac4618acf08"),
    ("libmtmd.0.7.0.dylib", 1613952, "7273c8904608207d72777b688c7894faf1e241ce97586267abd2161ee3a21ce3"),
    ("llama-quantize", 11571024, "4990670b4e213fefe51c0ff4e813d1d409a96b238e81f256e78df15bbbb8ccbb"),
    ("llama-server", 19177440, "831a41b83171eb00710d75e55bc1d995c8bc61e01bee547420ca52c02448275d"),
    ("ollama", 71493488, "be4b054f8ebf8b3b185daa30671849a80f22c2b2ef45e064de562f69aba46a96"),
)
# A download is a plain file: the programs get their run permission, and the libraries the names the programs load
# them by (links in the zip: name -> the file it points at), when the server starts (_prepare).
MAC_PROGRAMS = ("ollama", "llama-server", "llama-quantize")
MAC_LINKS = (
    ("libggml-base.0.dylib", "libggml-base.0.27.0.dylib"), ("libggml-base.dylib", "libggml-base.0.dylib"),
    ("libggml.0.dylib", "libggml.0.27.0.dylib"), ("libggml.dylib", "libggml.0.dylib"),
    ("libllama-common.0.dylib", "libllama-common.0.7.0.dylib"), ("libllama-common.dylib", "libllama-common.0.dylib"),
    ("libllama.0.dylib", "libllama.0.7.0.dylib"), ("libllama.dylib", "libllama.0.dylib"),
    ("libmtmd.0.dylib", "libmtmd.0.7.0.dylib"), ("libmtmd.dylib", "libmtmd.0.dylib"),
)
# The model's files (the manifest's config and layers): (SHA-256, bytes); kept as blobs/sha256-<SHA-256>.
MODEL_BLOBS = (
    ("e5ca99f918964e7d5a912f974eae708ae59370883a5b182fc0660fe7adf3f0e4", 242),          # config
    ("0cb0cd0a5c499d92942caa22fe5abb98f6e8874868d590e2b094ece4ac8e6d28", 175115616),    # projector
    ("bb722270d54346adc198f213851dbe0207e87c3ecf2a0aff4d92262726215391", 7381383680),   # the model (Q4_K_M)
    ("7008a656050bed18f6741406a631e83fa75ee1a02308f2e4f40d978cfbb3ce4b", 465109152),    # draft model
    ("b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315", 13),           # template
    ("0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594", 10174),        # license (Apache-2.0)
    ("2365fbb6d97bf654fdda0353b7505baa2254c662122cff0f153e4b47e6220ded", 64),           # params
)


def this_computer() -> Optional[str]:
    """"windows" or "mac" when the checker can run here (a Mac needs Apple silicon, as DubEval's Mac app does), else
    None: there is no pinned runtime for other computers."""
    if os.name == "nt":
        return "windows"
    return "mac" if sys.platform == "darwin" and platform.machine() == "arm64" else None


def supported() -> bool:
    return this_computer() is not None


def pack_files(computer: Optional[str] = None) -> list[dict]:
    """The pack's files for dubeval/packs.py: the runtime out of the release zip (this computer's; Windows's where
    there is none, so the list is never empty), then the model and its manifest."""
    if (computer or this_computer()) == "mac":
        files = [{"zip": MAC_ZIP, "member": MAC_PREFIX + member, "name": f"runtime/{member}", "bytes": size,
                  "sha256": sha} for member, size, sha in MAC_RUNTIME_FILES]
    else:
        files = [{"zip": OLLAMA_ZIP, "member": member, "name": f"runtime/{member}", "bytes": size, "sha256": sha}
                 for member, size, sha in RUNTIME_FILES]
    files += [{"url": f"{REGISTRY}/blobs/sha256:{sha}", "name": f"blobs/sha256-{sha}", "bytes": size, "sha256": sha}
              for sha, size in MODEL_BLOBS]
    files.append({"url": f"{REGISTRY}/manifests/{MODEL.split(':')[1]}", "headers": {"Accept": MANIFEST_ACCEPT}, "name": MANIFEST_PATH,
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


def _prepare(runtime: Path) -> Path:
    """Makes a downloaded runtime runnable and returns its program. On a Mac the downloaded programs lack their run
    permission and the libraries the names they are loaded by (see MAC_PROGRAMS, MAC_LINKS)."""
    if this_computer() != "mac":
        return runtime / "ollama.exe"
    for name in MAC_PROGRAMS:
        (runtime / name).chmod(0o755)
    for name, target in MAC_LINKS:
        link = runtime / name
        if not link.is_symlink() and not link.exists():
            link.symlink_to(target)
    return runtime / "ollama"


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
            _server = subprocess.Popen([str(_prepare(folder() / "runtime")), "serve"], env=env, stdout=out,
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
