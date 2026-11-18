"""Tests for interface translations: every text exists in all four languages with the same placeholders."""
import string

import pytest

from dubeval.i18n import MESSAGES, TEXT, UI_LANGUAGES, pick_ui_language, t, translate_message
from dubeval.jobs import STAGES


def placeholders(text: str) -> set:
    """The {names} a text expects from str.format."""
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


# A level has one name in each language. The old second names, as a regular expression that leaves alone the same
# word used as a verb ("Check the key", "Verificar a tradução", "Revisar un doblaje"), and the texts that keep them:
# "Check" as the name of a measure, and "needs checking in person" in Korean.
RETIRED_LEVEL_WORDS = {
    "en": r"Check(?! (the|that|your|both|one|for|it))",
    "ko": r"(?<!직접 )확인 필요|나쁨",
    "pt": r"Verificar(?! (os|uma|a tradução|o) ?)",
    "es": r"Revisar(?! (un|cada|los|la|el) )|Mal",
}
OTHER_MEANING = {"f.check", "w.exp.col.check", "c.table.check", "r.pair.unsure"}


@pytest.mark.parametrize("lang", UI_LANGUAGES)
def test_each_level_has_one_name(lang):
    """One report said 확인 필요 and 검토 필요 for one level, and 미흡 and 나쁨 for another: readers took them for
    four levels. The name on a row is the verdict's name."""
    import re
    for level in ("good", "check", "poor"):
        assert TEXT[f"badge.{level}"][lang] == TEXT[f"verdict.{level}"][lang]
    assert TEXT["lab.c_check"][lang] == TEXT["verdict.check"][lang] and TEXT["lab.c_poor"][lang] == TEXT["verdict.poor"][lang]
    old = re.compile(RETIRED_LEVEL_WORDS[lang])
    assert [key for key, entry in TEXT.items() if key not in OTHER_MEANING and old.search(entry[lang])] == []


@pytest.mark.parametrize("key", sorted(TEXT))
def test_every_text_has_all_languages_and_matching_placeholders(key):
    entry = TEXT[key]
    assert set(entry) == set(UI_LANGUAGES), f"{key} is missing a language"
    assert all(entry[lang].strip() for lang in UI_LANGUAGES)
    assert {lang: placeholders(entry[lang]) for lang in UI_LANGUAGES} == \
        {lang: placeholders(entry["en"]) for lang in UI_LANGUAGES}, f"{key} placeholders differ"


def test_every_stage_and_progress_message_is_translated():
    assert all(f"stage.{key}" in TEXT for key, _ in STAGES)
    for message, entry in MESSAGES.items():
        assert set(entry) == {"ko", "pt", "es"}, message


def test_lookup_fills_placeholders_and_passes_unknown_messages_through():
    assert t("verdict.counts", "ko", good=9, check=0, poor=0, na=1) == "좋음 9 · 검토 필요 0 · 미흡 0 · 측정 안 함 1"
    assert translate_message("Downloading the original video...", "es") == "Descargando el video original..."
    assert translate_message("Something dynamic 3.2 MB", "pt") == "Something dynamic 3.2 MB"
    assert translate_message("Done", "en") == "Done"


@pytest.mark.parametrize("locale, expected", [("ko-KR", "ko"), ("pt-BR", "pt"), ("es-MX", "es"), ("en-US", "en"),
                                              ("fr-FR", "en"), (None, "en")])
def test_browser_locale_picks_interface_language(locale, expected):
    assert pick_ui_language(locale) == expected


def test_share_link_errors_are_translated():
    from dubeval.perso_api import parse_share_url
    for bad in ("", "https://youtube.com/x", "https://perso.ai/en/share/video-translator"):
        try:
            parse_share_url(bad)
        except ValueError as e:
            assert translate_message(str(e), "ko") != str(e), str(e)
