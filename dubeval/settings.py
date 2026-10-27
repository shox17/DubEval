"""API keys set from the app's Settings page: saved in the data folder's .env, never shown, logged or returned.

Keys can also come from elsewhere (the environment, the project's .env in development); the page can only change the
ones it saved, and says when a key is set somewhere else. A change applies to the running process at once.
"""
import os
import re
import threading
from pathlib import Path
from typing import Optional

from dubeval.paths import DATA_DIR, PROJECT_ROOT

ENV_FILE = Path(DATA_DIR) / ".env"
PROJECT_ENV = Path(PROJECT_ROOT) / ".env"         # a development checkout's own .env, read-only here
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
KEY_RE = re.compile(r"^[A-Za-z0-9_\-.:]{20,300}$")
BAD_KEY = "That doesn't look like an API key. Paste the whole key, with nothing else."
_lock = threading.Lock()


def _env_file() -> Path:
    """Where keys are saved (a module attribute, so tests can redirect it)."""
    return Path(ENV_FILE)


def _saved_names() -> set[str]:
    """The variable names present in the data folder's .env (values are not kept)."""
    try:
        lines = _env_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {line.split("=", 1)[0].strip() for line in lines if "=" in line and not line.lstrip().startswith("#")}


def status() -> dict:
    """For each provider: whether a key is set, and whether it was saved here (so the page can remove it)."""
    saved = _saved_names()
    return {provider: {"set": bool((os.getenv(var) or "").strip()), "saved_here": var in saved}
            for provider, var in KEYS.items()}


def _rewrite(var: str, value: Optional[str]) -> None:
    """Sets (or with None removes) one line of the data folder's .env, keeping every other line as it was."""
    path = _env_file()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    lines = [line for line in lines if line.split("=", 1)[0].strip() != var]
    if value is not None:
        lines.append(f"{var}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.unlink(missing_ok=True)
    # Created readable by this user only (POSIX), never briefly with the default permissions. On Windows the data
    # folder sits in the user's own profile, which other users can't read.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with open(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    os.replace(tmp, path)


def save_key(provider: str, value: str) -> dict:
    """Saves a provider's key and uses it from now on; returns the new status (never the key)."""
    var = KEYS[provider]
    value = (value or "").strip()
    if not KEY_RE.match(value):
        raise ValueError(BAD_KEY)
    with _lock:
        _rewrite(var, value)
        os.environ[var] = value
    return status()


def remove_key(provider: str) -> dict:
    """Removes a key saved here and stops using it; a key set elsewhere stays (status says so)."""
    var = KEYS[provider]
    with _lock:
        if var in _saved_names():
            _rewrite(var, None)
            os.environ.pop(var, None)
            # A development checkout may also have the key in the project's .env: keep using that one.
            from dotenv import load_dotenv
            load_dotenv(Path(PROJECT_ENV))
    return status()
