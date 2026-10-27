"""Perso share links, following https://developers.perso.ai/llms.txt.

A share link (https://perso.ai/<lang>/share/video-translator?seq=<token>) is public: no API key, no account,
no credits. Flow: parse_share_url -> get_shared_project -> download_media for the original and the dub.
"""
import os
import re
import time
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

import requests

API_BASE = os.getenv("PERSO_API_BASE", "https://api.perso.ai")
MEDIA_BASE = os.getenv("PERSO_MEDIA_BASE", "https://portal-media.perso.ai")
VT = "/video-translator/api/v1"

ERROR_HINTS = {
    "VT4035": "Sharing is turned off for this Perso project. Ask the owner to turn sharing on, then try again.",
}

SHARE_HOSTS = ("perso.ai", "www.perso.ai")
NOT_A_SHARE_LINK = ("This doesn't look like a Perso share link. Open the dubbed video in Perso, choose Share, and copy "
                    "the link (it contains ?seq=).")
SHARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-.~]{16,}$")


class PersoError(RuntimeError):
    """A Perso request failed; the message is safe to show to users."""

    def __init__(self, message: str, code: str | None = None, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


def media_url(path: str) -> str:
    """Resolves a relative /perso-storage/... path against the media host, URL-encoding the path."""
    url = path if path.startswith("http") else MEDIA_BASE.rstrip("/") + "/" + path.lstrip("/")
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=quote(parts.path, safe="/%")))


def _error_from_response(resp: requests.Response) -> PersoError:
    """Turns a failed HTTP response into a PersoError with a plain-language message."""
    try:
        body = resp.json()
    except ValueError:
        body = {}
    code = body.get("code") if isinstance(body, dict) else None
    detail = (body.get("message") or body.get("detail") or body.get("error")) if isinstance(body, dict) else None
    if code in ERROR_HINTS:
        msg = ERROR_HINTS[code]
    elif resp.status_code == 429:
        msg = "Perso is rate-limiting requests. Wait a minute and try again."
    else:
        msg = f"Perso error {resp.status_code}" + (f": {detail}" if detail else "")
    return PersoError(msg, code=code, status=resp.status_code)


def parse_share_url(url: str) -> str:
    """The share token from a Perso share link (or a bare token). Raises ValueError for anything else.

    Perso shares a dub under several URL shapes, all carrying the same public token in seq=:
    /<lang>/share/video-translator?seq=… (Share dialog) and /video-translator/<src>-<tgt>/<category>?seq=…
    (gallery pages). Any perso.ai link with a valid seq token is accepted.
    """
    text = (url or "").strip()
    if not text:
        raise ValueError("Paste a Perso share link, for example https://perso.ai/en/share/video-translator?seq=…")
    if SHARE_TOKEN_RE.match(text):
        return text
    parts = urlsplit(text if "://" in text else "https://" + text)
    token = (parse_qs(parts.query).get("seq") or [""])[0].strip()
    if parts.hostname not in SHARE_HOSTS or not (token or "/share" in parts.path):
        raise ValueError(NOT_A_SHARE_LINK)
    if not SHARE_TOKEN_RE.match(token):
        raise ValueError("The share link is missing its seq=… part. Copy the whole link from Perso again.")
    return token


def _public_get(session, url: str, sleep: Callable[[float], None], retries: int = 3, **kwargs):
    """GET without an API key, retrying network errors, rate limits and server errors with backoff."""
    for attempt in range(retries + 1):
        try:
            resp = session.request("GET", url, headers={}, timeout=kwargs.pop("timeout", 60), **kwargs)
        except requests.RequestException as e:
            if attempt == retries:
                raise PersoError("Could not reach Perso. Check your internet connection.")
            sleep(2 ** attempt)
            continue
        if (resp.status_code == 429 or resp.status_code >= 500) and attempt < retries:
            sleep(2 ** (attempt + 1))
            continue
        return resp
    raise PersoError("Perso request failed after retries.")


def get_shared_project(share_token: str, session=None, sleep: Callable[[float], None] = time.sleep) -> dict:
    """Project details behind a share link: title, languages, and original/dubbed/lip-sync video paths."""
    session = session or requests.Session()
    resp = _public_get(session, f"{API_BASE}{VT}/projects/shared/{quote(share_token, safe='')}", sleep)
    if resp.status_code in (400, 404):
        err = _error_from_response(resp)
        if err.code in ERROR_HINTS:
            raise err
        raise PersoError("Perso couldn't find a project for this share link. Check that the link is complete "
                         "and that sharing is still turned on.", code=err.code, status=resp.status_code)
    if resp.status_code >= 400:
        raise _error_from_response(resp)
    body = resp.json()
    project = body.get("result", body) if isinstance(body, dict) else {}
    # A missing original is allowed here: the pipeline can take it from --original instead.
    if not (project.get("translatedFileUrl") or project.get("lipSyncFileUrl")):
        raise PersoError("This shared project has no finished dubbed video yet. Wait until Perso finishes, then try again.")
    return project


def download_media(path: str, out_path: str, session=None, sleep: Callable[[float], None] = time.sleep,
                   label: str = "video") -> str:
    """Streams a /perso-storage/... file (URL-encoded against the media host) to out_path, with retries."""
    session = session or requests.Session()
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with session.get(media_url(path), stream=True, timeout=600) as resp:
                if resp.status_code != 200:
                    raise PersoError("Downloading the videos from Perso failed. Try again in a minute.")
                tmp = target.with_name(target.name + ".part")
                with open(tmp, "wb") as f:
                    for chunk in resp.iter_content(1 << 20):
                        f.write(chunk)
                os.replace(tmp, target)
            return out_path
        except (requests.RequestException, PersoError):
            if attempt == 2:
                raise
            sleep(2 * (attempt + 1))
    return out_path
