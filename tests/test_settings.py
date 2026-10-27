"""API keys from the Settings page: saved to the data folder's .env, never returned, removable only when saved here."""
import os

import pytest

from dubeval import settings

KEY = "sk-test-" + "x" * 30                       # a made-up key (tests never see real ones)


def test_a_saved_key_is_used_at_once_and_kept_with_the_other_lines(tmp_path):
    settings.ENV_FILE.write_text("# my settings\nDUBEVAL_JUDGE=auto\n", encoding="utf-8")
    status = settings.save_key("gemini", f"  {KEY}\n")
    assert status["gemini"] == {"set": True, "saved_here": True} and os.environ["GEMINI_API_KEY"] == KEY
    text = settings.ENV_FILE.read_text(encoding="utf-8")
    assert text.startswith("# my settings\nDUBEVAL_JUDGE=auto\n") and f"GEMINI_API_KEY={KEY}" in text
    assert KEY not in repr(status)                                  # the status never carries the key


def test_saving_again_replaces_the_line():
    settings.save_key("anthropic", KEY)
    settings.save_key("anthropic", KEY.replace("x", "y"))
    assert settings.ENV_FILE.read_text(encoding="utf-8").count("ANTHROPIC_API_KEY=") == 1


@pytest.mark.parametrize("bad", ["", "short", "two words " + "x" * 30, "x" * 20 + "\nOTHER=1", "x" * 400])
def test_anything_that_isnt_a_key_is_refused_and_nothing_is_written(bad):
    with pytest.raises(ValueError, match="doesn't look like an API key"):
        settings.save_key("gemini", bad)
    assert not settings.ENV_FILE.exists() and "GEMINI_API_KEY" not in os.environ


def test_removing_a_key_saved_here(monkeypatch):
    settings.save_key("gemini", KEY)
    status = settings.remove_key("gemini")
    assert status["gemini"] == {"set": False, "saved_here": False} and "GEMINI_API_KEY" not in os.environ
    assert "GEMINI_API_KEY" not in settings.ENV_FILE.read_text(encoding="utf-8")


def test_after_removal_a_key_in_the_project_env_is_used_again():
    settings.PROJECT_ENV.write_text(f"GEMINI_API_KEY={KEY}-project\n", encoding="utf-8")
    settings.save_key("gemini", KEY)
    status = settings.remove_key("gemini")
    assert status["gemini"] == {"set": True, "saved_here": False} and os.environ["GEMINI_API_KEY"] == f"{KEY}-project"


def test_a_key_set_elsewhere_is_reported_but_not_removed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    assert settings.status()["anthropic"] == {"set": True, "saved_here": False}
    assert settings.remove_key("anthropic")["anthropic"]["set"] is True and os.environ["ANTHROPIC_API_KEY"] == KEY


def test_the_key_file_is_created_private_and_a_leftover_temp_file_is_replaced():
    leftover = settings.ENV_FILE.with_name(settings.ENV_FILE.name + ".tmp")
    leftover.write_text("half-written", encoding="utf-8")
    settings.save_key("openai", KEY)
    assert not leftover.exists() and f"OPENAI_API_KEY={KEY}" in settings.ENV_FILE.read_text(encoding="utf-8")
    if os.name != "nt":
        assert settings.ENV_FILE.stat().st_mode & 0o077 == 0         # nobody but this user can read it
