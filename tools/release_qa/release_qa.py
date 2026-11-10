"""Release QA: installs a published DubEval release (if needed), runs it like a new user and records what happened.

    python tools/release_qa/release_qa.py                 # the latest GitHub release
    python tools/release_qa/release_qa.py --tag v0.1.5    # a given release
    python tools/release_qa/release_qa.py --installer desktop/dist/DubEval-Setup.exe   # a local build
    python tools/release_qa/report.py data/qa/<run>       # the report (HTML + PDF) from a run

The app runs with its own profile (--user-data-dir) inside the run folder, so the person's own evaluations, settings
and keys are never touched, and it's driven through Chrome DevTools (--remote-debugging-port) with Playwright. Each
scenario records a pass/fail, its timings, a screenshot and notes into results.json; the browser console and the
server log are kept next to it. Usage stats are answered "No", so a QA run never sends anything.

Installing a release that isn't the one installed replaces the installed DubEval (the installer has one location per
user); the run says so before it starts. Windows only (the installer and the app's paths).
"""
import argparse
import base64
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger("release_qa")

REPO = "shox17/DubEval"
ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "data" / "testset" / "media"
APP = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DubEval" / "DubEval.exe"
# Openly licensed test clips (Tears of Steel, credited in NOTICE) plus a longer one for Stop and a non-video file.
DEFAULT_INPUTS = {
    "original": MEDIA / "p011" / "original.mp4",
    "dub_a": MEDIA / "p011" / "dub.mp4",
    "dub_b": MEDIA / "p012" / "dub.mp4",
    "long_original": MEDIA / "p018" / "original.mp4",
    "long_dub": MEDIA / "p018" / "dub.mp4",
    "not_a_video": ROOT / "README.md",
}
EVALUATION_TIMEOUT = 15 * 60


# ---------------- the release and its installation ----------------
def release_info(tag: Optional[str]) -> dict:
    """The release to test: tag, installer link and size, publish time, and the installer's sha512 from latest.yml."""
    url = f"https://api.github.com/repos/{REPO}/releases/" + (f"tags/{tag}" if tag else "latest")
    rel = requests.get(url, timeout=30).json()
    assets = {a["name"]: a for a in rel.get("assets", [])}
    exe = assets.get("DubEval-Setup.exe")
    if not exe:
        raise SystemExit(f"No DubEval-Setup.exe in release {rel.get('tag_name') or tag}")
    sha512 = None
    if "latest.yml" in assets:
        yml = requests.get(assets["latest.yml"]["browser_download_url"], timeout=30).text
        m = re.search(r"^sha512:\s*(\S+)", yml, re.M)
        sha512 = m.group(1) if m else None
    return {"tag": rel["tag_name"], "version": rel["tag_name"].lstrip("v"), "published": rel["published_at"],
            "installer_url": exe["browser_download_url"], "installer_bytes": exe["size"], "sha512": sha512,
            "downloads": exe["download_count"]}


def installed_version() -> Optional[str]:
    """The installed DubEval's version, read from its executable (None when it isn't installed)."""
    if not APP.is_file():
        return None
    out = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-Item '{APP}').VersionInfo.ProductVersion"],
                         capture_output=True, text=True, encoding="utf-8")
    return out.stdout.strip() or None


def app_is_running() -> bool:
    """Whether the installed DubEval is open (the installer can't replace it then)."""
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process DubEval -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq '%s' }).Count"
                          % APP], capture_output=True, text=True, encoding="utf-8")
    return (out.stdout.strip() or "0") != "0"


def download(url: str, target: Path) -> dict:
    """Streams a file to target; returns its size, seconds and speed."""
    start = time.time()
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(target, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
    sec = time.time() - start
    size = target.stat().st_size
    return {"bytes": size, "seconds": round(sec, 1), "mb_per_s": round(size / 1e6 / sec, 1) if sec else None}


def sha512_b64(path: Path) -> str:
    """The file's sha512 in base64, as electron-builder writes it in latest.yml."""
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode("ascii")


# ---------------- the machine ----------------
def machine() -> dict:
    """What the run was on: Windows edition, processor, graphics card and memory (from CIM)."""
    script = ("$o=Get-CimInstance Win32_OperatingSystem; $c=Get-CimInstance Win32_Processor | Select-Object -First 1; "
              "$g=(Get-CimInstance Win32_VideoController | ForEach-Object Name) -join ', '; "
              "[pscustomobject]@{os=\"$($o.Caption) $($o.Version)\"; cpu=$c.Name.Trim(); gpu=$g; "
              "ram_gb=[math]::Round($o.TotalVisibleMemorySize/1MB)} | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True,
                         encoding="utf-8")
    try:
        return json.loads(out.stdout)
    except ValueError:
        return {"os": platform.platform()}


def free_port() -> int:
    """A free TCP port on 127.0.0.1 for the DevTools connection."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------- recording ----------------
class Run:
    """The run folder and results.json: one entry per scenario, saved after each so a crash keeps what was done."""

    def __init__(self, folder: Path):
        self.folder = folder
        (folder / "screens").mkdir(parents=True, exist_ok=True)
        self.data = {"started": datetime.now().isoformat(timespec="seconds"), "steps": [], "console": []}
        self.page = None
        self.shots = 0

    def save(self) -> None:
        (self.folder / "results.json").write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def shot(self, name: str) -> Optional[str]:
        """A screenshot of the app window; its path relative to the run folder, or None when it couldn't be taken."""
        if not self.page:
            return None
        self.shots += 1
        rel = f"screens/{self.shots:02d}_{name}.png"
        try:
            self.page.screenshot(path=str(self.folder / rel))
            return rel
        except Exception as e:  # a screenshot never fails the step
            log.warning("Screenshot %s failed: %s", name, e)
            return None

    def step(self, sid: str, title: str, fn: Callable[[dict], None]) -> dict:
        """Runs one scenario: fn fills notes and checks; any exception or failed check makes it a failure."""
        entry = {"id": sid, "title": title, "start": datetime.now().strftime("%H:%M:%S"), "checks": [], "notes": [],
                 "metrics": {}}
        t0 = time.time()
        try:
            fn(entry)
            entry["status"] = "pass" if all(c["ok"] for c in entry["checks"]) else "fail"
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = f"{type(e).__name__}: {e}"[:600]
            log.exception("Step %s failed", sid)
        entry["seconds"] = round(time.time() - t0, 1)
        entry["screenshot"] = entry.get("screenshot") or self.shot(sid)
        self.data["steps"].append(entry)
        self.save()
        log.info("%-14s %-5s %5.1fs  %s", sid, entry["status"], entry["seconds"], title)
        return entry


def check(entry: dict, ok: bool, what: str, detail: str = "") -> bool:
    """Records one check of a scenario (what was expected; detail: what was seen)."""
    entry["checks"].append({"ok": bool(ok), "what": what, "detail": str(detail)[:300]})
    return bool(ok)


# ---------------- driving the app ----------------
def api(page, path: str, method: str = "GET", body: Optional[dict] = None):
    """Calls the app's own API from inside the page (its launch cookie), in English."""
    return page.evaluate(
        """async ([path, method, body]) => {
             const r = await fetch(path, {method, headers: {'Content-Type': 'application/json', 'Accept-Language': 'en'},
                                          body: body ? JSON.stringify(body) : undefined});
             const text = await r.text(); let json = null; try { json = JSON.parse(text); } catch {}
             return {status: r.status, json, text: text.slice(0, 500)};
           }""", [path, method, body])


def wait_job(page, job_id: str, timeout: float = EVALUATION_TIMEOUT) -> dict:
    """Polls a job until it leaves "running"; returns its final state."""
    end = time.time() + timeout
    while time.time() < end:
        state = api(page, f"/api/jobs/{job_id}")["json"] or {}
        if state.get("status") not in (None, "running"):
            return state
        time.sleep(1.0)
    raise TimeoutError(f"job {job_id} still running after {timeout:.0f} s")


def job_from_address(page, timeout: float = 30) -> str:
    """The job id once the page has moved to #/job/<id> (or straight to a result)."""
    end = time.time() + timeout
    while time.time() < end:
        m = re.search(r"#/(?:job|report|compare)/([0-9a-f]{12})", page.evaluate("location.hash"))   # live, not cached
        if m:
            return m.group(1)
        time.sleep(0.2)
    shown = [t.strip() for t in page.locator("main .error, main [role=alert], .modal-overlay").all_inner_texts() if t.strip()]
    raise TimeoutError(f"no job started (address {page.url}; on screen: {' | '.join(shown)[:200] or 'no message'})")


def type_into(page, label: str, text: str, index: int = 0) -> None:
    """Types into the text box with this accessible name, as a person would (the page reads it as it's typed)."""
    box = page.get_by_role("textbox", name=label, exact=True).nth(index)
    box.click()
    box.fill("")
    box.type(text, delay=5)
    # Leave the box without Tab: Tab lands on the "Kind of dub" help button, whose tooltip then swallows the next click.
    box.evaluate("el => el.blur()")
    page.keyboard.press("Escape")


def run_scenarios(run: Run, page, inputs: dict, release: dict) -> None:
    """The scenarios, in the order a new user meets them."""
    page.on("console", lambda m: run.data["console"].append({"type": m.type, "text": m.text[:300]})
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: run.data["console"].append({"type": "pageerror", "text": str(e)[:300]}))

    def first_launch(e):
        page.wait_for_selector("main", timeout=60000)
        page.wait_for_timeout(1500)
        e["screenshot"] = run.shot("first_launch")
        has_stats = "usage_stats" in (api(page, "/api/settings")["json"] or {})   # releases before 0.1.6 have none
        e["metrics"]["usage_stats_in_release"] = has_stats
        if has_stats:
            check(e, page.locator(".modal-overlay").count() > 0, "The usage-stats question appears on first launch")
        else:
            e["notes"].append("This release has no usage stats: their checks are skipped")
        e["metrics"]["page_language"] = page.evaluate("document.documentElement.lang")
        # The rest runs in English so the checks can read the screen; the first screen above is in the PC's language.
        page.evaluate("localStorage.setItem('dubeval.lang', 'en')")
        page.reload()
        page.wait_for_selector("main", timeout=60000)
        page.wait_for_timeout(1000)
        if has_stats:
            page.get_by_role("button", name="No, thanks").click()
            stats = (api(page, "/api/settings")["json"] or {}).get("usage_stats") or {}
            check(e, stats.get("ask") is False and stats.get("on") is False,
                  "Answering No saves the choice and sends nothing", json.dumps({k: stats.get(k) for k in ("ask", "on")}))
    run.step("first_launch", "First launch and the usage-stats question", first_launch)

    single = {}

    def evaluate_one(e):
        page.goto(page.url.split("#")[0] + "#/new")
        page.wait_for_timeout(800)
        type_into(page, "Original video", str(inputs["original"]))
        type_into(page, "Dubbed video", str(inputs["dub_a"]))
        page.wait_for_timeout(2500)
        e["screenshot"] = run.shot("new_evaluation")
        page.get_by_role("button", name="Start evaluation").click()
        job = job_from_address(page)
        state = wait_job(page, job)
        single["job"] = job
        e["metrics"]["evaluation_seconds"] = state.get("elapsed_sec")
        check(e, state.get("status") == "done", "The evaluation finishes", state.get("error") or state.get("status"))
        page.wait_for_timeout(2500)
        rep = (api(page, f"/api/jobs/{job}/report?lang=en")["json"] or {}).get("report") or {}
        overall = rep.get("overall") or {}
        e["metrics"].update(verdict=overall.get("level"), counts=overall.get("counts"),
                            headline=overall.get("headline"), problems=len(rep.get("problem_intervals") or []))
        check(e, bool(overall.get("headline")), "The report has a verdict and a headline", overall.get("label"))
        e["screenshot"] = run.shot("report")
    run.step("evaluate", "One evaluation from start to report", evaluate_one)

    def review(e):
        if not single.get("job"):
            raise RuntimeError("no evaluation to review")
        start = page.get_by_role("button", name="Start reviewing")
        if not check(e, start.count() > 0, "The review walk-through is offered"):
            return
        start.click()
        page.wait_for_timeout(500)
        first = page.locator(".review-flow").inner_text()
        page.keyboard.press("n")
        page.wait_for_timeout(500)
        second = page.locator(".review-flow").inner_text()
        check(e, first != second, "N moves to the next problem", second.splitlines()[1] if "\n" in second else second)
        page.get_by_role("button", name="False alarm").first.click()
        page.wait_for_timeout(500)
        pressed = page.get_by_role("button", name="False alarm").first.get_attribute("aria-pressed")
        check(e, pressed == "true", "A vote is saved and shown as pressed", pressed)
    run.step("review", "Review the problems and vote", review)

    def export(e):
        job = single.get("job")
        if not job:
            raise RuntimeError("no evaluation to export")
        for kinds, expect in (("html", "text/html"), ("xlsx", "spreadsheetml"), ("text", "text/plain"),
                              ("html,xlsx,text", "zip")):
            res = page.evaluate("""async (u) => { const r = await fetch(u); const b = await r.blob();
                                   return {status: r.status, type: r.headers.get('content-type') || '', bytes: b.size}; }""",
                                f"/api/jobs/{job}/export?kinds={kinds}&lang=en")
            check(e, res["status"] == 200 and expect in res["type"] and res["bytes"] > 500, f"Export {kinds}",
                  f"{res['status']} {res['type']} {res['bytes']} bytes")
    run.step("export", "Export the report (HTML, Excel, text, zip)", export)

    def compare(e):
        page.goto(page.url.split("#")[0] + "#/new/compare")
        page.wait_for_timeout(800)
        type_into(page, "Original video", str(inputs["original"]))
        type_into(page, "Dub A", str(inputs["dub_a"]))
        type_into(page, "Dub B", str(inputs["dub_b"]))
        page.wait_for_timeout(2500)
        page.get_by_role("button", name=re.compile(r"Compare \d dubs")).click()
        job = job_from_address(page)
        state = wait_job(page, job)
        e["metrics"]["comparison_seconds"] = state.get("elapsed_sec")
        check(e, state.get("status") == "done", "The comparison finishes", state.get("error") or state.get("status"))
        page.wait_for_timeout(3000)
        text = page.locator("main").inner_text()
        e["metrics"]["recommendation"] = text.split("\n")[1] if "\n" in text else ""
        check(e, "Ranking" in text, "The ranking and reasoning are shown")
        # A new profile has no AI key, so the translation check can't run: then nothing may tell you to deliver
        # (0.1.5 said "Deliver Dub B." with a star). Read from the single evaluation's report, not from wording.
        rep = (api(page, f"/api/jobs/{single['job']}/report?lang=en")["json"] or {}).get("report") or {} \
            if single.get("job") else {}
        unchecked = any(m.get("id") == "translation_check" and m.get("level") == "not_measured"
                        for s in rep.get("sections", []) for m in s.get("metrics", []))
        e["metrics"]["translation_checked"] = not unchecked
        if unchecked:
            check(e, "Deliver" not in text and "★" not in text,
                  "Without a translation check, the comparison doesn't say Deliver", text.split("\n")[1][:120])
        e["screenshot"] = run.shot("comparison")
    run.step("compare", "Compare two dubs of one video", compare)

    def bad_inputs(e):
        page.goto(page.url.split("#")[0] + "#/new")
        page.wait_for_timeout(800)
        type_into(page, "Dubbed video", r"C:\nope\missing.mp4")
        page.wait_for_timeout(2000)
        check(e, "There's no video at this path" in page.locator("main").inner_text(),
              "A missing file is named at once, before starting")
        res = api(page, "/api/evaluations", "POST", {"original": str(inputs["not_a_video"]), "dub": str(inputs["dub_a"]),
                                                     "lang": "en"})
        job = (res["json"] or {}).get("id")
        if not check(e, bool(job), "A non-video file can be submitted", res["text"][:120]):
            return
        page.goto(page.url.split("#")[0] + f"#/job/{job}")
        state = wait_job(page, job, 120)
        page.wait_for_timeout(1500)
        check(e, state.get("status") == "failed" and "can't be read" in (state.get("error") or ""),
              "A non-video file fails fast with a plain message", state.get("error"))
        check(e, state.get("can_continue") is False, "No Continue for a file that can't be read",
              f"can_continue={state.get('can_continue')}")
        e["metrics"]["fail_seconds"] = state.get("elapsed_sec")
        e["screenshot"] = run.shot("bad_input")
    run.step("bad_inputs", "A missing file and a file that isn't a video", bad_inputs)

    def stop(e):
        res = api(page, "/api/evaluations", "POST", {"original": str(inputs["long_original"]),
                                                     "dub": str(inputs["long_dub"]), "lang": "en"})
        job = (res["json"] or {}).get("id")
        if not check(e, bool(job), "A long evaluation starts", res["text"][:120]):
            return
        page.goto(page.url.split("#")[0] + f"#/job/{job}")
        page.wait_for_timeout(4000)
        page.get_by_role("button", name="Stop").first.click()
        dialog = page.get_by_role("alertdialog")
        dialog.wait_for(timeout=5000)
        t0 = time.time()
        dialog.get_by_role("button", name="Stop").click()
        state = wait_job(page, job, 180)
        e["metrics"]["seconds_to_stop"] = round(time.time() - t0, 1)
        e["metrics"]["stopped_in_stage"] = state.get("stage")
        check(e, state.get("status") == "cancelled", "Stop asks first, then stops", state.get("status"))
        check(e, e["metrics"]["seconds_to_stop"] <= 10, "It stops within 10 seconds (the dialog says right away)",
              f"{e['metrics']['seconds_to_stop']} s in stage {state.get('stage')}")
        check(e, state.get("can_continue") is True, "A stopped evaluation offers Continue")
        page.wait_for_timeout(1000)
        e["screenshot"] = run.shot("stopped")
    run.step("stop", "Stop a running evaluation", stop)

    def history(e):
        page.goto(page.url.split("#")[0] + "#/history")
        page.wait_for_timeout(4000)
        text = page.locator("main").inner_text()
        m = re.search(r"(\d+) runs? on (\d+) dubs?", text)
        e["metrics"]["history"] = m.group(0) if m else None
        check(e, bool(m), "History counts this run's evaluations", m.group(0) if m else text[:120])
    run.step("history", "Evaluation history", history)

    def about(e):
        # After the evaluations: closing Settings moves the address back, which once undid the move to a new form.
        info = api(page, "/api/info?lang=en")["json"] or {}
        check(e, info.get("version") == release["version"], "The app reports the release's version",
              f"app {info.get('version')}, release {release['version']}")
        page.goto(page.url.split("#")[0] + "#/settings/about")
        page.wait_for_timeout(1200)
        e["screenshot"] = run.shot("settings_about")
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
        page.goto(page.url.split("#")[0] + "#/")
    run.step("settings", "Settings → About", about)

    def languages(e):
        en = (api(page, "/api/info?lang=en")["json"] or {}).get("texts") or {}
        for lang in ("ko", "pt", "es"):
            texts = (api(page, f"/api/info?lang={lang}")["json"] or {}).get("texts") or {}
            missing = [k for k in en if k not in texts]
            check(e, not missing, f"Every screen text exists in {lang}", ", ".join(missing[:5]))
        page.evaluate("localStorage.setItem('dubeval.lang', 'ko')")
        page.goto(page.url.split("#")[0] + "#/")
        page.reload()
        page.wait_for_timeout(2500)
        e["screenshot"] = run.shot("home_korean")
        page.evaluate("localStorage.setItem('dubeval.lang', 'en')")
    run.step("languages", "Screen texts in Korean, Portuguese and Spanish", languages)


# ---------------- the run ----------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", help="Release to test (default: the latest)")
    ap.add_argument("--installer", type=Path, help="Test this local installer instead of a GitHub release")
    ap.add_argument("--reinstall", action="store_true", help="Install even when this version is already installed")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "qa", help="Where run folders go")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    release = release_info(args.tag)
    if args.installer:                   # a local build (such as a signed one not yet published): its own version
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              f"(Get-Item '{args.installer.resolve()}').VersionInfo.ProductVersion"],
                             capture_output=True, text=True, encoding="utf-8")
        version = out.stdout.strip() or release["version"]
        release.update(tag=f"v{version}", version=version, published="local build", installer_url=None,
                       installer_bytes=args.installer.stat().st_size, sha512=None, downloads=0,
                       local_installer=str(args.installer.resolve()))
    folder = args.out / f"{release['tag']}_{datetime.now():%Y%m%d-%H%M}"
    run = Run(folder)
    run.data.update(release=release, machine=machine(), inputs={k: str(v) for k, v in DEFAULT_INPUTS.items()})
    missing = [k for k, p in DEFAULT_INPUTS.items() if not p.is_file()]
    if missing:
        raise SystemExit(f"Test inputs missing: {', '.join(missing)} (data/testset/media)")
    log.info("Release %s (published %s), run folder %s", release["tag"], release["published"], folder)

    def install(e):
        before = installed_version()
        e["metrics"]["installed_before"] = before
        if before == release["version"] and not args.reinstall and not args.installer:
            e["notes"].append(f"{before} is already installed: install skipped (--reinstall to install anyway)")
            check(e, True, "The release is installed")
            return
        if app_is_running():
            raise RuntimeError("DubEval is open: close it, then run again (the installer can't replace it)")
        log.warning("Installing %s replaces the installed DubEval %s", release["version"], before or "(none)")
        target = Path(args.installer) if args.installer else folder / "DubEval-Setup.exe"
        if not args.installer:
            e["metrics"]["download"] = download(release["installer_url"], target)
            if release["sha512"]:
                check(e, sha512_b64(target) == release["sha512"], "The installer matches latest.yml's sha512")
        t0 = time.time()
        proc = subprocess.run([str(target), "/S"], timeout=600)
        e["metrics"]["install_seconds"] = round(time.time() - t0, 1)
        after = installed_version()
        e["metrics"]["installed_after"] = after
        check(e, proc.returncode == 0 and after == release["version"], "The silent install puts the release in place",
              f"exit {proc.returncode}, installed {after}")
    run.step("install", "Download and install", install)

    from playwright.sync_api import sync_playwright
    profile = folder / "profile"
    port = free_port()
    proc = None
    try:
        t0 = time.time()
        # Chromium slows a window it thinks is hidden or covered (timers, drawing): screenshots then time out and the
        # page lags. These switches keep the QA window running at full speed behind other windows.
        proc = subprocess.Popen([str(APP), f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
                                 "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
                                 "--disable-background-timer-throttling"])
        # Wait until DevTools lists the app's own page (after the starting screen) before attaching: Playwright
        # attached while only the starting screen existed never saw the page that replaced it.
        for _ in range(360):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as resp:
                    if any(t.get("type") == "page" and re.match(r"http://127\.0\.0\.1:\d+/", t.get("url", ""))
                           for t in json.load(resp)):
                        break
            except OSError:
                pass
            if proc.poll() is not None:
                raise RuntimeError(f"the app quit while starting (exit {proc.returncode})")
            time.sleep(0.5)
        else:
            raise RuntimeError("the app's page never opened (3 minutes)")
        run.data["first_launch_seconds"] = round(time.time() - t0, 1)
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            page = next(p for c in browser.contexts for p in c.pages if re.match(r"http://127\.0\.0\.1:\d+/", p.url))
            run.page = page
            run_scenarios(run, page, DEFAULT_INPUTS, release)
            browser.close()
    finally:
        if proc and proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        server_log = profile / "logs" / "server.log"
        if server_log.is_file():
            shutil.copy(server_log, folder / "server.log")
            text = server_log.read_text(encoding="utf-8", errors="replace")
            run.data["server_log"] = {"errors": len(re.findall(r"^ERROR", text, re.M)),
                                      "warnings": len(re.findall(r"^WARNING", text, re.M)),
                                      "tracebacks": text.count("Traceback (most recent call last)")}
        run.data["finished"] = datetime.now().isoformat(timespec="seconds")
        run.save()
    steps = run.data["steps"]
    passed = sum(s["status"] == "pass" for s in steps)
    log.info("%d of %d scenarios passed. Report: python tools/release_qa/report.py \"%s\"", passed, len(steps), folder)
    return 0 if passed == len(steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
