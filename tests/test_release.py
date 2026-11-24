"""A release is consistent: the desktop app and the engine have one version, and that version has its notes."""
import base64
import json
import re
from pathlib import Path

from dubeval import release_notes
from dubeval.version import TOOL_VERSION

ROOT = Path(__file__).resolve().parent.parent


def test_the_desktop_app_and_the_engine_have_the_same_version():
    package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == TOOL_VERSION


def test_the_python_package_has_the_same_version():
    # pip show dubeval and the installed metadata read pyproject's version; it stayed at 0.1.0 until 0.1.5.
    import tomllib
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == TOOL_VERSION


def test_this_version_has_whats_new_in_every_language():
    for lang in ("en", "ko", "pt", "es"):
        assert release_notes.NOTES[TOOL_VERSION][lang], lang
    assert len({len(release_notes.NOTES[TOOL_VERSION][lang]) for lang in ("en", "ko", "pt", "es")}) == 1


def test_releases_are_published_signed_only():
    """From 0.1.6 the app carries publisherName, so an unsigned release would strand every installed app: nothing may
    publish straight from the build, and the finish step must rebuild latest.yml and the blockmap from the signed file
    (signing changes the bytes; the build's latest.yml made 0.1.5 refuse the update in the 2026-11-10 test)."""
    package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert package["build"]["win"]["signtoolOptions"]["publisherName"] == ["ESTsoft Corp."]
    scripts = package["scripts"]
    assert not any("--publish always" in s or "--publish onTagOrDraft" in s for s in scripts.values())
    assert scripts["build:windows:release"].endswith("release-windows.js build")
    assert scripts["release:windows:finish"].endswith("release-windows.js finish")
    release = (ROOT / "desktop" / "scripts" / "release-windows.js").read_text(encoding="utf-8")
    for needed in ("buildBlockMap", "latest.yml", 'sig.status !== "Valid"', "cn !== PUBLISHER", "timestamped"):
        assert needed in release, needed


def test_the_signing_portals_address_stays_out_of_the_repository():
    # It's internal: desktop/codesign.local.json (git-ignored) or DUBEVAL_CODESIGN_PORTAL holds it.
    assert "desktop/codesign.local.json" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    files = [*ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md"), *(ROOT / "desktop").glob("*.js"),
             *(ROOT / "desktop" / "scripts").glob("*.js"), ROOT / "desktop" / "package.json", ROOT / "desktop" / "README.md"]
    for f in files:
        text = f.read_text(encoding="utf-8").lower()
        assert "altoolsbuild" not in text and "192.168." not in text, f.name


def test_updates_come_from_the_repository_the_app_names():
    from dubeval.version import REPOSITORY_URL
    publish = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))["build"]["publish"][0]
    assert REPOSITORY_URL == f"https://github.com/{publish['owner']}/{publish['repo']}"


def test_an_installed_app_can_read_the_new_versions_lines_at_its_tag():
    # desktop/updater.js reads this file at the release's tag for the Version update window, in the app's language.
    from dubeval.version import REPOSITORY_URL
    updater = (ROOT / "desktop" / "updater.js").read_text(encoding="utf-8")
    assert f'"{REPOSITORY_URL.replace("https://github.com", "https://raw.githubusercontent.com")}"' in updater
    assert "/dubeval/release_notes.json" in updater
    data = json.loads((ROOT / "dubeval" / "release_notes.json").read_text(encoding="utf-8"))
    assert all(isinstance(line, str) for lines in data[TOOL_VERSION].values() for line in lines)
    assert '"release_notes.json"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_desktop_app_leaves_the_port_to_the_server():
    # The server takes its usual port, so the page's settings last; the app must not ask for a new one at each launch.
    assert '"--port"' not in (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")


def test_the_start_page_opens_in_the_packaged_app():
    # With this fuse off, a window can't open a file:// page inside the archive: up to 0.1.3 the app was blank while it
    # started, and its failure messages never showed. The fuse stays off; the page moves out of the archive.
    build = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))["build"]
    assert build["electronFuses"]["grantFileProtocolExtraPrivileges"] is False
    assert "status.html" in build["asarUnpack"] and "status.html" in build["files"]
    assert "app.asar.unpacked" in (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")


def test_the_start_screens_show_the_apps_current_icon():
    # They carry it inside them, so it can't arrive late: the shell's page kept 0.1.0's when the icon changed in 0.1.2.
    for page in (ROOT / "desktop" / "status.html", ROOT / "dubeval" / "web" / "index.html"):
        inside = base64.b64decode(re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", page.read_text(encoding="utf-8")).group(1))
        assert inside == (ROOT / "dubeval" / "web" / "icon.png").read_bytes()


def test_the_window_appears_even_if_its_first_page_never_draws():
    main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    assert "show: false" in main and "setTimeout(show, SHOW_WITHIN_MS)" in main


def test_the_two_start_screens_say_the_same_in_the_same_font():
    # One takes over from the other while the app starts: any difference shows as a glitch.
    shell = (ROOT / "desktop" / "status.html").read_text(encoding="utf-8")
    page = (ROOT / "dubeval" / "web" / "boot.js").read_text(encoding="utf-8")
    words = re.search(r"starting: \{(.*?)\n  \}", shell, re.S).group(1)
    for lang in ("en", "ko", "pt", "es"):
        line = re.search(rf"{lang}: (\[.*?\]),", words).group(1)
        assert line in page
    font = re.search(r"font: (13px/1.5 [^;]+);", shell).group(1)
    assert f"font: {font};" in (ROOT / "dubeval" / "web" / "style.css").read_text(encoding="utf-8")


def test_a_downloaded_update_installs_only_on_restart_to_update():
    assert "updater.autoInstallOnAppQuit = false;" in (ROOT / "desktop" / "updater.js").read_text(encoding="utf-8")


def test_every_whats_new_line_is_a_whole_sentence():
    from dubeval.release_notes import NOTES
    for version, langs in NOTES.items():
        counts = {len(lines) for lines in langs.values()}
        assert len(counts) == 1, version
        for lang, lines in langs.items():
            for line in lines:
                assert line.rstrip().endswith("."), (version, lang, line)


def test_the_desktop_bundle_never_zips_a_package_with_a_model_file(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_desktop", Path(__file__).parents[1] / "tools" / "build_desktop.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    # A Mac or Linux program has no extension: imageio-ffmpeg's "ffmpeg-macos-aarch64-v7.1" was zipped by the first Mac
    # build and couldn't run. A program is known by how its file starts.
    mach_o = b"\xcf\xfa\xed\xfe" + b"\0" * 28
    for name, extra, content in (("plain", None, b""), ("withmodel", "assets/silero_vad_v6.onnx", b"model"),
                                 ("withprogram", "binaries/ffmpeg-macos-aarch64-v7.1", mach_o)):
        (tmp_path / name).mkdir()
        (tmp_path / name / "__init__.py").write_text("X = 1\n", encoding="utf-8")
        if extra:
            (tmp_path / name / extra).parent.mkdir(parents=True)
            (tmp_path / name / extra).write_bytes(content)
    _, zipped = build.zip_pure_packages(tmp_path)
    assert zipped == ["plain"] and (tmp_path / "withmodel" / "assets" / "silero_vad_v6.onnx").is_file()
    assert (tmp_path / "withprogram" / "binaries" / "ffmpeg-macos-aarch64-v7.1").is_file()


def _build_desktop():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_desktop", ROOT / "tools" / "build_desktop.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    return build


def test_the_mac_apps_python_is_one_pinned_download():
    # Like every download (AGENTS.md): one release and its SHA-256, never "latest", and the same minor version as the
    # pins in requirements.txt.
    build = _build_desktop()
    for machine, (url, digest) in build.MAC_PYTHON.items():
        assert re.fullmatch(r"https://github\.com/astral-sh/python-build-standalone/releases/download/\d{8}/"
                            r"cpython-3\.14\.\d+%2B\d{8}-\S+-apple-darwin-install_only_stripped\.tar\.gz", url), machine
        assert re.fullmatch(r"[0-9a-f]{64}", digest), machine
    assert build.site_packages(Path("python"), mac=True) == Path("python/lib/python3.14/site-packages")
    assert build.site_packages(Path("python"), mac=False) == Path("python/Lib/site-packages")


def test_the_mac_python_loses_only_what_the_app_never_uses(tmp_path):
    build = _build_desktop()
    for folder in ("include", "lib/tcl9.0", "lib/python3.14/idlelib", "lib/python3.14/tkinter", "lib/python3.14/json",
                   "lib/python3.14/lib-dynload", "lib/python3.14/site-packages/pip", "bin"):
        (tmp_path / folder).mkdir(parents=True)
    for file in ("lib/libpython3.14.dylib", "lib/libtcl9.0.dylib", "lib/python3.14/os.py",
                 "lib/python3.14/lib-dynload/_tkinter.cpython-314-darwin.so",
                 "lib/python3.14/lib-dynload/_ssl.cpython-314-darwin.so", "bin/python3.14"):
        (tmp_path / file).write_bytes(b"x")
    build.trim_mac_python(tmp_path)
    left = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert left == ["bin/python3.14", "lib/libpython3.14.dylib", "lib/python3.14/lib-dynload/_ssl.cpython-314-darwin.so",
                    "lib/python3.14/os.py"]
    assert (tmp_path / "lib/python3.14/json").is_dir() and (tmp_path / "lib/python3.14/site-packages/pip").is_dir()


def test_the_mac_app_is_built_for_apple_silicon_signed_by_estsoft_and_notarized():
    # ESTsoft's Developer ID, the hardened runtime and Apple's notarization: what lets a downloaded copy open without
    # a warning. The notarization credentials come from the build Mac's keychain (APPLE_KEYCHAIN_PROFILE), never from
    # the repository.
    package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    mac = package["build"]["mac"]
    assert {t["target"] for t in mac["target"]} == {"dmg", "zip"}
    assert all(t["arch"] == ["arm64"] for t in mac["target"])
    assert mac["identity"] == "ESTsoft corp. (WQL32M5H24)"
    assert mac["hardenedRuntime"] is True and mac["notarize"] is True
    entitlements = (ROOT / "desktop" / mac["entitlements"]).read_text(encoding="utf-8")
    assert mac["entitlementsInherit"] == mac["entitlements"]
    # Only what Electron's engine and the bundled Python's compiled code need: no library from another team.
    assert set(re.findall(r"<key>([^<]+)</key>", entitlements)) == {
        "com.apple.security.cs.allow-jit", "com.apple.security.cs.allow-unsigned-executable-memory"}
    # electron-builder would sign each of the bundled Python's and models' thousands of data files (a read-only model
    # stopped the first Mac build), so it skips them, and after-pack.js signs their programs and libraries instead,
    # each with the hardened runtime and a timestamp, as notarization requires.
    assert mac["signIgnore"] == ["/Contents/Resources/python/", "/Contents/Resources/models/"]
    after_pack = (ROOT / "desktop" / "after-pack.js").read_text(encoding="utf-8")
    assert package["build"]["afterPack"] == "after-pack.js"
    assert '"--timestamp", "--options", "runtime"' in after_pack and '["python", "models"]' in after_pack
    assert (ROOT / "desktop" / mac["icon"]).is_file()
    assert "--mac" in package["scripts"]["dist:mac"] and "--publish never" in package["scripts"]["dist:mac"]
    # A test build on a Mac without the certificate (GitHub's): ad-hoc, without the hardened runtime, which would
    # refuse the bundled Python's libraries signed by their makers.
    adhoc = package["scripts"]["dist:mac:adhoc"]
    assert "-c.mac.identity=-" in adhoc and "-c.mac.hardenedRuntime=false" in adhoc and "--publish never" in adhoc


def test_the_mac_app_never_writes_inside_its_own_bundle():
    # A changed file breaks the app's signature. Python gets -B (no .pyc) and numba's cache goes to the data folder.
    main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    assert 'serve.unshift("-B")' in main and "NUMBA_CACHE_DIR" in main
    assert 'path.basename(home) === "bin"' in main            # the bundle is found from Resources/python/bin/python3
    build = (ROOT / "tools" / "build_desktop.py").read_text(encoding="utf-8")
    assert '"--invalidation-mode", "unchecked-hash"' in build  # the shipped .pyc are used whatever the file times


def test_the_mac_app_has_an_edit_menu_and_updates_itself():
    # Without an Edit menu, Cmd+C / Cmd+V do nothing in a Mac window. Since 0.1.7 the signed Mac app updates itself from
    # the release's latest-mac.yml and .zip, as Windows does from latest.yml.
    main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    assert '{ role: "editMenu" }' in main
    updater = (ROOT / "desktop" / "updater.js").read_text(encoding="utf-8")
    assert 'process.platform === "darwin") return' not in updater
    assert "selfUpdates: true" in (ROOT / "desktop" / "preload.js").read_text(encoding="utf-8")
    # A shell that can't update itself still gets the page's pointer to the releases page.
    assert "updatesByHand" in (ROOT / "dubeval" / "web" / "settings.js").read_text(encoding="utf-8")
    # The download link stays the same from one version to the next, like DubEval-Setup.exe.
    package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert package["build"]["dmg"]["artifactName"] == "DubEval-Mac.${ext}"


def test_the_mac_build_workflow_publishes_nothing():
    workflow = (ROOT / ".github" / "workflows" / "build-mac.yml").read_text(encoding="utf-8")
    assert "contents: read" in workflow and "contents: write" not in workflow
    assert "gh release" not in workflow and "--publish never" in (ROOT / "desktop" / "package.json").read_text(encoding="utf-8")
    assert "npm run dist:mac:adhoc" in workflow       # GitHub's Mac has no Developer ID certificate
    assert "codesign --verify --deep --strict" in workflow


def test_an_update_installs_without_stopping_for_a_click():
    # Restart to update used to stop twice: on "who is this program for" and on Finish. An update now keeps the way
    # DubEval is installed and starts it when done; a first install still shows both pages.
    nsh = (ROOT / "desktop" / "build" / "installer.nsh").read_text(encoding="utf-8")
    assert "!macro customInstallMode" in nsh and "!macro customFinishPage" in nsh
    assert nsh.count("${isUpdated}") >= 3
    assert "Abort" in nsh and "MUI_PAGE_FINISH" in nsh
    package = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert package["build"]["nsis"]["oneClick"] is False          # a first install still asks
    assert "nsis" not in package["build"] or "include" not in package["build"]["nsis"]   # build/installer.nsh, by default
