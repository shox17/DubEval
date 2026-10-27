"""What the start page shows for a source before anything runs: its title, length and a picture.

A Perso share link also gives its languages and whether the dub is lip-synced, so the page fills the other fields
from it. Web pages (YouTube, TikTok, Reels and others) are read with yt-dlp without downloading the video; a path on
this computer gives one frame with ffmpeg. Pictures come back as data: URIs, so the page loads nothing from other sites.
"""
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import requests

from dubeval import perso_api
from dubeval.inputs import FFMPEG_EXE, LOCAL_INPUT, MEDIA_SUFFIXES, is_link, probe

log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 3 * 1024 * 1024
LINK_UNREADABLE = "Couldn't read this link. Check it and your internet connection."
NO_SUCH_FILE = "There's no video at this path on this computer."


def preview(source: str, session=None) -> dict:
    """{kind: perso | page | media_link | file, title, duration_sec, thumbnail, site, source_lang, target_lang,
    lipsync} for a link or a path; raises ValueError with a plain message when it can't be read."""
    source = (source or "").strip()
    session = session or requests.Session()
    if is_link(source):
        host = (urlsplit(source).hostname or "").lower()
        if host in perso_api.SHARE_HOSTS:
            return _perso(source, session)
        if Path(urlsplit(source).path).suffix.lower() in MEDIA_SUFFIXES:
            return _result("media_link", Path(urlsplit(source).path).name, site=host)
        return _page(source, session)
    return _file(source)


def _result(kind: str, title: Optional[str], duration_sec=None, thumbnail=None, site=None, source_lang=None,
            target_lang=None, lipsync=None) -> dict:
    return {"kind": kind, "title": title or "", "duration_sec": round(duration_sec, 1) if duration_sec else None,
            "thumbnail": thumbnail, "site": site, "source_lang": source_lang, "target_lang": target_lang,
            "lipsync": lipsync}


def _perso(link: str, session) -> dict:
    """The share's title, languages, length and thumbnail from Perso's public endpoint."""
    project = perso_api.get_shared_project(perso_api.parse_share_url(link), session=session)
    code = lambda lang: (((lang or {}).get("code") or "").split("-")[0].lower() or None)
    thumb = project.get("thumbnailUrl")
    return _result("perso", project.get("title"), (project.get("durationMs") or 0) / 1000 or None,
                   _image(perso_api.media_url(thumb), session) if thumb else None, "Perso",
                   code(project.get("sourceLanguage")), code(project.get("targetLanguage")),
                   bool(project.get("isLipSync")))


def _page(link: str, session) -> dict:
    """A video page's title, length and thumbnail, read with yt-dlp without downloading the video."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(link, download=False)
    except Exception as e:                          # yt-dlp raises its own errors for every kind of failure
        log.info("No preview for %s: %s", link, e)
        raise ValueError(LINK_UNREADABLE) from e
    thumb = info.get("thumbnail")
    return _result("page", info.get("title"), info.get("duration"),
                   _image(thumb, session) if thumb and thumb.startswith("https://") else None,
                   info.get("extractor_key") or urlsplit(link).hostname)


def _file(path: str) -> dict:
    """A video on this computer: its name, length and one frame."""
    p = Path(path.strip('"')).expanduser()
    if not p.is_file():
        raise ValueError(NO_SUCH_FILE)
    info = probe(str(p))
    return _result("file", p.name, info.get("duration_sec"), _frame(str(p), info.get("duration_sec")))


def _frame(path: str, duration: Optional[float]) -> Optional[str]:
    """One frame (a second in, or the middle of a short video) as a small JPEG data: URI, or None."""
    at = min(1.0, (duration or 0) / 2)
    cmd = [FFMPEG_EXE, "-nostdin", "-loglevel", "error", "-ss", f"{at:.2f}", *LOCAL_INPUT, "-i", path,
           "-frames:v", "1", "-vf", "scale=480:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return "data:image/jpeg;base64," + base64.b64encode(out).decode("ascii") if out else None


def _image(url: str, session) -> Optional[str]:
    """An image from the web as a data: URI (only an image, at most MAX_IMAGE_BYTES), or None."""
    try:
        with session.get(url, stream=True, timeout=10) as resp:
            kind = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            if resp.status_code != 200 or not kind.startswith("image/"):
                return None
            data = b""
            for chunk in resp.iter_content(64 * 1024):
                data += chunk
                if len(data) > MAX_IMAGE_BYTES:
                    return None
    except requests.RequestException:
        return None
    return f"data:{kind};base64," + base64.b64encode(data).decode("ascii")
