"""Dev tool: prints the pins (member, bytes, SHA-256) of the Ollama files DubEval's local translation checker takes
out of a release zip, for dubeval/local_judge.py. Only the members asked for are downloaded, by range requests.

    python tools/pin_ollama_runtime.py <release zip URL> <prefix inside the zip> <member> [<member> ...]
    python tools/pin_ollama_runtime.py <release zip URL> <prefix> --list        # every member under the prefix

A member that is a symbolic link is printed as a link with its target (local_judge.MAC_LINKS), not as a file.
"""
import hashlib
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dubeval import network, packs  # noqa: E402


def modes(url: str, session) -> dict:
    """Each member's Unix mode from the zip's central directory (packs._zip_index doesn't read it)."""
    head = session.head(url, allow_redirects=True, timeout=60)
    size, final = int(head.headers["content-length"]), head.url
    tail = session.get(final, headers={"Range": f"bytes={max(0, size - 65536)}-{size - 1}"}, timeout=60).content
    eocd = tail.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack_from("<II", tail, eocd + 12)
    cd = session.get(final, headers={"Range": f"bytes={cd_off}-{cd_off + cd_size - 1}"}, timeout=120).content
    pos, out = 0, {}
    while cd[pos:pos + 4] == b"PK\x01\x02":
        nlen, elen, clen = struct.unpack_from("<HHH", cd, pos + 28)
        out[cd[pos + 46:pos + 46 + nlen].decode("utf-8")] = struct.unpack_from("<I", cd, pos + 38)[0] >> 16
        pos += 46 + nlen + elen + clen
    return out


def main() -> None:
    url, prefix, wanted = sys.argv[1], sys.argv[2].rstrip("/") + "/", sys.argv[3:]
    network.use_system_settings()
    session = requests.Session()
    index = packs._zip_index(url, session)
    mode = modes(url, session)
    if wanted == ["--list"]:
        for name, (_, _, size, _) in sorted(index[1].items()):
            if name.startswith(prefix) and not name.endswith("/"):
                kind = "link" if mode[name] & 0o170000 == 0o120000 else "program" if mode[name] & 0o111 else "file"
                print(f"{kind:8} {size:>11}  {name[len(prefix):]}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        for member in wanted:
            part = Path(tmp) / "member"
            digest = packs._zip_member({"member": prefix + member}, part, index, session, lambda n: None, lambda: False)
            if mode[prefix + member] & 0o170000 == 0o120000:
                print(f'    link    ("{member}", "{part.read_text(encoding="utf-8")}"),')
                continue
            assert hashlib.sha256(part.read_bytes()).hexdigest() == digest.hexdigest()
            run = "  # program" if mode[prefix + member] & 0o111 else ""
            print(f'    ("{member}", {part.stat().st_size}, "{digest.hexdigest()}"),{run}')


if __name__ == "__main__":
    main()
