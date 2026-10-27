"""A release is consistent: the desktop app and the engine have one version, and that version has its notes."""
import json
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
