"""What's new in each version, as the app's "What's new" card shows it: a few plain lines per language.

The lines live in release_notes.json: add the new version's there (en, ko, pt, es) whenever TOOL_VERSION changes; tests
check the current one exists. An installed app reads that file at the new version's release tag for its Version update
window (desktop/updater.js), so it stays plain JSON at this path.
"""
import json
from pathlib import Path

NOTES = json.loads(Path(__file__).with_name("release_notes.json").read_text(encoding="utf-8"))


def notes(version: str, lang: str) -> list[str]:
    """The lines for version in lang (English when that language has none; empty for an unknown version)."""
    entry = NOTES.get(version) or {}
    return list(entry.get(lang) or entry.get("en") or [])
