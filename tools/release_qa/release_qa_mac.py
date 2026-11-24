"""Release QA on a Mac, driven from this computer over SSH: the same "new user" scenarios as release_qa.py, on the
DubEval app installed on the Mac (or another build there), with the same results.json and report.

    python tools/release_qa/release_qa_mac.py --host me@mac.local --key ~/.ssh/mac_key
    python tools/release_qa/release_qa_mac.py --host me@mac.local --key ~/.ssh/mac_key --app ~/build/DubEval.app
    python tools/release_qa/report.py data/qa/<run>       # the report (HTML + PDF), as for Windows

What it does on the Mac: copies the openly licensed test clips (data/testset/media p011, p012, p018) into a temporary
folder, starts the app with its own profile there (--user-data-dir, so the person's evaluations, settings and keys are
never touched; usage stats are answered "No"), keeps the Mac awake while it runs (caffeinate: a Mac that slept in the
middle once turned a 3.5-minute evaluation into 16), and drives the window through Chrome DevTools over an SSH tunnel.
At the end it closes the app and deletes the temporary folder (--keep keeps it).

Needs: SSH to the Mac with a key (no password prompt), the app installed or built there, and Playwright here
(requirements.txt). Nothing is installed or changed in the app: it only runs it. The Mac's address and key never go in
the repository; pass them, or set DUBEVAL_MAC_HOST and DUBEVAL_MAC_KEY.
"""
import argparse
import json
import logging
import os
import re
import shlex
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path, PurePosixPath

import release_qa as qa

log = logging.getLogger("release_qa_mac")

REMOTE_DIR = "dubeval-release-qa"                  # in the Mac user's home; deleted at the end unless --keep
CLIPS = {"original": "p011/original.mp4", "dub_a": "p011/dub.mp4", "dub_b": "p012/dub.mp4",
         "long_original": "p018/original.mp4", "long_dub": "p018/dub.mp4"}


class Mac:
    """Commands and file copies to the Mac over SSH, with the key only (BatchMode: never a password prompt)."""

    def __init__(self, host: str, key: str):
        self.host = host
        self.opts = ["-i", str(Path(key).expanduser()), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
                     "-o", "ConnectTimeout=15"]

    def run(self, command: str, check: bool = True) -> str:
        """Runs a shell command on the Mac and returns its output."""
        out = subprocess.run(["ssh", *self.opts, self.host, command], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        if check and out.returncode != 0:
            raise RuntimeError(f"on the Mac: {command[:80]}… failed: {out.stderr.strip()[:300]}")
        return out.stdout.strip()

    def copy(self, local: Path, remote: str) -> None:
        """Copies one file to the Mac."""
        out = subprocess.run(["scp", "-q", *self.opts, str(local), f"{self.host}:{remote}"], capture_output=True,
                             text=True)
        if out.returncode != 0:
            raise RuntimeError(f"copying {local.name} to the Mac failed: {out.stderr.strip()[:300]}")

    def tunnel(self, port: int) -> subprocess.Popen:
        """Forwards this computer's port to the same port on the Mac (DevTools)."""
        return subprocess.Popen(["ssh", *self.opts, "-N", "-L", f"{port}:127.0.0.1:{port}", self.host],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mac_machine(mac: Mac) -> dict:
    """What the run was on: macOS version, chip and memory."""
    os_ver = mac.run("sw_vers -productName; sw_vers -productVersion", check=False).replace("\n", " ")
    chip = mac.run("sysctl -n machdep.cpu.brand_string", check=False)
    mem = mac.run("sysctl -n hw.memsize", check=False)
    return {"os": os_ver, "cpu": chip, "gpu": chip, "ram_gb": round(int(mem) / 2 ** 30) if mem.isdigit() else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=os.environ.get("DUBEVAL_MAC_HOST"), help="user@address of the Mac (SSH)")
    ap.add_argument("--key", default=os.environ.get("DUBEVAL_MAC_KEY"), help="the SSH key for it")
    ap.add_argument("--app", default="/Applications/DubEval.app", help="the app on the Mac (default: the installed one)")
    ap.add_argument("--out", type=Path, default=qa.ROOT / "data" / "qa", help="Where run folders go")
    ap.add_argument("--keep", action="store_true", help="Keep the Mac's temporary folder (clips, profile, logs)")
    args = ap.parse_args()
    if not args.host or not args.key:
        raise SystemExit("Give the Mac with --host user@address and --key <ssh key> (or DUBEVAL_MAC_HOST / DUBEVAL_MAC_KEY).")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    mac = Mac(args.host, args.key)
    home = PurePosixPath(mac.run("echo $HOME"))
    app = PurePosixPath(args.app.replace("~", str(home), 1)) if args.app.startswith("~") else PurePosixPath(args.app)
    version = mac.run(f"defaults read {shlex.quote(str(app / 'Contents/Info.plist'))} CFBundleShortVersionString")
    signer = mac.run(f"codesign -dv --verbose=2 {shlex.quote(str(app))} 2>&1 | grep -m1 '^Authority=' || true", check=False)
    work = home / REMOTE_DIR
    media, profile = work / "media", work / "profile"
    missing = [rel for rel in CLIPS.values() if not (qa.MEDIA / rel).is_file()]
    if missing:
        raise SystemExit(f"Test clips missing here: {', '.join(missing)} (data/testset/media)")

    folder = args.out / f"v{version}-mac_{datetime.now():%Y%m%d-%H%M}"
    run = qa.Run(folder)
    inputs = {k: str(media / rel) for k, rel in CLIPS.items()} | {"not_a_video": str(work / "README.md")}
    run.data.update(release={"tag": f"v{version}", "version": version, "published": "installed app (Mac)",
                             "installer_url": None, "local_installer": f"{args.host}:{app}", "installer_bytes": 0,
                             "downloads": "-", "signer": signer.removeprefix("Authority=")},
                    machine=mac_machine(mac), inputs=inputs)
    log.info("DubEval %s on the Mac (%s), run folder %s", version, signer or "unsigned", folder)

    log.info("Copying the test clips to the Mac…")
    mac.run(f"rm -rf {shlex.quote(str(work))}; mkdir -p " + " ".join(shlex.quote(str(media / d)) for d in
                                                                      sorted({PurePosixPath(r).parent for r in CLIPS.values()})))
    for rel in CLIPS.values():
        mac.copy(qa.MEDIA / rel, str(media / rel))
    mac.copy(qa.ROOT / "README.md", str(work / "README.md"))

    port = qa.free_port()
    binary = app / "Contents/MacOS/DubEval"
    mac.run(f"mkdir -p {shlex.quote(str(profile))}; nohup caffeinate -i {shlex.quote(str(binary))} "
            f"--user-data-dir={shlex.quote(str(profile))} --remote-debugging-port={port} "
            f"--disable-renderer-backgrounding --disable-backgrounding-occluded-windows "
            f"--disable-background-timer-throttling > {shlex.quote(str(work / 'app.out'))} 2>&1 & "
            f"echo $! > {shlex.quote(str(work / 'app.pid'))}")
    tunnel = mac.tunnel(port)
    try:
        t0 = time.time()
        for _ in range(360):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as resp:
                    if any(t.get("type") == "page" and re.match(r"http://127\.0\.0\.1:\d+/", t.get("url", ""))
                           for t in json.load(resp)):
                        break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("the app's page never opened on the Mac (3 minutes)")
        run.data["first_launch_seconds"] = round(time.time() - t0, 1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            page = next(p for c in browser.contexts for p in c.pages if re.match(r"http://127\.0\.0\.1:\d+/", p.url))
            run.page = page
            qa.run_scenarios(run, page, {k: PurePosixPath(v) for k, v in inputs.items()}, run.data["release"])
            browser.close()
    finally:
        # caffeinate's child is the app: ending caffeinate's process group ends both.
        mac.run(f"pid=$(cat {shlex.quote(str(work / 'app.pid'))} 2>/dev/null); [ -n \"$pid\" ] && "
                f"pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null; sleep 6; "
                f"pkill -f {shlex.quote('user-data-dir=' + str(profile))} 2>/dev/null; true", check=False)
        server_log = mac.run(f"cat {shlex.quote(str(profile / 'logs/server.log'))} 2>/dev/null", check=False)
        (folder / "server.log").write_text(server_log, encoding="utf-8")
        run.data["server_log"] = {"errors": len(re.findall(r"^ERROR", server_log, re.M)),
                                  "warnings": len(re.findall(r"^WARNING", server_log, re.M)),
                                  "tracebacks": server_log.count("Traceback (most recent call last)")}
        still = mac.run(f"pgrep -f {shlex.quote('user-data-dir=' + str(profile))} || true", check=False)
        run.data["app_stopped"] = not still
        if not args.keep:
            mac.run(f"rm -rf {shlex.quote(str(work))}", check=False)
        run.data["finished"] = datetime.now().isoformat(timespec="seconds")
        run.save()
        tunnel.terminate()
    steps = run.data["steps"]
    passed = sum(s["status"] == "pass" for s in steps)
    log.info("%d of %d scenarios passed. Report: python tools/release_qa/report.py \"%s\"", passed, len(steps), folder)
    return 0 if passed == len(steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
