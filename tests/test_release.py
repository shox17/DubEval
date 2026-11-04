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


def test_this_version_has_whats_new_in_every_language():
    for lang in ("en", "ko", "pt", "es"):
        assert release_notes.NOTES[TOOL_VERSION][lang], lang
    assert len({len(release_notes.NOTES[TOOL_VERSION][lang]) for lang in ("en", "ko", "pt", "es")}) == 1


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
    for name, extra in (("plain", None), ("withmodel", "assets/silero_vad_v6.onnx")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "__init__.py").write_text("X = 1\n", encoding="utf-8")
        if extra:
            (tmp_path / name / extra).parent.mkdir(parents=True)
            (tmp_path / name / extra).write_bytes(b"model")
    _, zipped = build.zip_pure_packages(tmp_path)
    assert zipped == ["plain"] and (tmp_path / "withmodel" / "assets" / "silero_vad_v6.onnx").is_file()
