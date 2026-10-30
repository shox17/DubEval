"""Inputs: turn what the user gives (a local file, a link, one audio track of a file, a subtitle file) into local
media files the evaluation can read, and check them first.

Pure apart from the files it writes into the folder it is given (downloads and extracted tracks) and the network
for links. Every user-facing failure is a ValueError or FileNotFoundError with a plain message.
"""
import os
import re
import hashlib
import logging
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit

import requests
import imageio_ffmpeg

from dubeval import network

log = logging.getLogger(__name__)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
# Put before every "-i <untrusted file>": a video can be a playlist naming other files or web addresses, and ffmpeg
# would fetch them. Only the file itself (and local files a playlist names) may be read, never the network.
LOCAL_INPUT = ("-protocol_whitelist", "file")
MAX_MINUTES = float(os.getenv("DUBEVAL_MAX_MINUTES", "120"))     # longest video accepted
MAX_MEDIA_GB = float(os.getenv("DUBEVAL_MAX_MEDIA_GB", "20"))      # largest file uploaded or downloaded
MAX_MEDIA_BYTES = int(MAX_MEDIA_GB * 1024 ** 3)
MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg",
                  ".opus"}
SUBTITLE_SUFFIXES = {".srt", ".vtt"}

NOT_A_VIDEO_LINK = ("This link opens a web page, not a video file. To evaluate videos from YouTube and other pages, "
                    "install the links extra: pip install \"dubeval[links]\".")
DOWNLOAD_FAILED = "The video couldn't be downloaded. Check the link and your internet connection, then try again."
BAD_LINK = "Links must start with http:// or https://."
TOO_BIG = f"The file is larger than {MAX_MEDIA_GB:g} GB. Use a smaller or shorter video."


def is_link(spec: str) -> bool:
    """Whether spec is a web link rather than a file path."""
    return spec.strip().lower().startswith(("http://", "https://"))


def direct_link(url: str) -> str:
    """A share link from a file host turned into a link to the file itself, so it downloads like any video link:
    Dropbox (dl=1), Google Drive (its download address) and OneDrive or SharePoint (the public shares API). Any
    other link is returned as it is."""
    import base64
    from urllib.parse import parse_qs, urlencode, urlunsplit
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    query = parse_qs(parts.query, keep_blank_values=True)
    if host.endswith("dropbox.com") and parts.path not in ("", "/"):
        query.pop("dl", None)
        query["dl"] = ["1"]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), ""))
    if host == "drive.google.com":
        match = re.search(r"/file/d/([\w-]+)", parts.path)
        file_id = match.group(1) if match else (query.get("id") or [None])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    if host in ("1drv.ms", "onedrive.live.com") or host.endswith(".sharepoint.com"):
        token = base64.urlsafe_b64encode(url.strip().encode("utf-8")).decode("ascii").rstrip("=")
        return f"https://api.onedrive.com/v1.0/shares/u!{token}/root/content"
    return url.strip()


def _hash(text: str) -> str:
    """A short, file-name-safe fingerprint of text."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def fingerprint(spec: str) -> str:
    """A cache key for an input: a link as written, a local file by its full path, size and modification time."""
    if is_link(spec):
        return spec.strip()
    path = Path(spec).expanduser().resolve()
    st = path.stat()
    return f"{path}|{st.st_size}|{int(st.st_mtime)}"


# ---------------- getting the media ----------------
def fetch(spec: str, folder: Path, label: str, session=None, sleep: Callable[[float], None] = time.sleep,
          progress: Optional[Callable[[float], None]] = None) -> str:
    """A local path for the input: a file as is, a link downloaded into folder (once; later calls reuse it).

    Any kind of link: a file host's share link is turned into the file's own link (direct_link); a link to a media
    file is streamed, a video page goes through yt-dlp, and when one way fails the other is tried. progress(fraction)
    hears how far a download is, when the size is known."""
    text = spec.strip()
    if not is_link(text):
        path = Path(text).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"The {label} file doesn't exist: {path}")
        return str(path.resolve())
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(BAD_LINK)
    folder.mkdir(parents=True, exist_ok=True)
    done = [p for p in folder.glob(f"{_hash(text)}.*") if not p.name.endswith(".part") and p.stat().st_size > 0]
    if done:
        log.info("Using the cached %s: %s", label, done[0].name)
        return str(done[0])
    url = direct_link(text)
    looks_like_file = Path(urlsplit(url).path).suffix.lower() in MEDIA_SUFFIXES or url != text
    if not _has_yt_dlp():
        return _download(url, folder, session, sleep, progress, key=text)
    first, second = ((lambda: _download(url, folder, session, sleep, progress, key=text)),
                     (lambda: _download_page(text, folder, progress)))
    if not looks_like_file:
        first, second = second, first
    try:
        return first()
    except ValueError as e:
        # A file link that turned out to be a web page goes to yt-dlp; a page yt-dlp can't read may be a file without
        # an extension. Any other failure (too big, the server failing) is the answer.
        if str(e) == TOO_BIG or (looks_like_file and str(e) != NOT_A_VIDEO_LINK):
            raise
        log.info("Download by the first way failed (%s); trying the other", e)
        try:
            return second()
        except ValueError as again:
            # yt-dlp is installed and read the page: "install the links extra" would be wrong (a private or removed
            # video, for example); its own reason stands.
            if not looks_like_file and str(again) == NOT_A_VIDEO_LINK:
                raise e from again
            # Otherwise the more telling reason wins: a blocked network or a page that isn't a video says more.
            raise (again if str(e) in (DOWNLOAD_FAILED, NOT_A_VIDEO_LINK) else e) from again


def _has_yt_dlp() -> bool:
    """Whether the optional yt-dlp package (for YouTube and other pages) is installed."""
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def _download(url: str, folder: Path, session, sleep, progress=None, key: Optional[str] = None) -> str:
    """Streams a direct media link into folder, with retries; refuses web pages. key names the file (the link as
    given, so a later fetch of the same link finds it)."""
    session = session or requests.Session()
    suffix = Path(urlsplit(url).path).suffix.lower()
    target = folder / f"{_hash(key or url)}{suffix if suffix in MEDIA_SUFFIXES else '.mp4'}"
    for attempt in range(3):
        try:
            with session.get(url, stream=True, timeout=600) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                if "text/html" in (resp.headers.get("content-type") or "").lower():
                    raise ValueError(NOT_A_VIDEO_LINK)
                total = int(resp.headers.get("content-length") or 0)
                if total > MAX_MEDIA_BYTES:
                    raise ValueError(TOO_BIG)
                tmp = target.with_name(target.name + ".part")
                written = 0
                with open(tmp, "wb") as f:
                    for chunk in resp.iter_content(1 << 20):
                        written += len(chunk)
                        if written > MAX_MEDIA_BYTES:          # the size header can be missing or wrong
                            break
                        f.write(chunk)
                        if progress and total:
                            progress(min(1.0, written / total))
                if written > MAX_MEDIA_BYTES:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(TOO_BIG)
                os.replace(tmp, target)
            return str(target)
        except ValueError:
            raise
        except (requests.RequestException, RuntimeError) as e:
            log.warning("Download attempt %d failed: %s", attempt + 1, e)
            if attempt == 2:
                raise ValueError(network.describe(e, DOWNLOAD_FAILED)) from e
            sleep(2 * (attempt + 1))
    return str(target)


def _download_page(url: str, folder: Path, progress=None) -> str:
    """Downloads the video on a web page (YouTube and others) with yt-dlp, into folder."""
    import yt_dlp

    def hook(d):
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if progress and total and d.get("status") == "downloading":
            progress(min(1.0, (d.get("downloaded_bytes") or 0) / total))
    options = {"outtmpl": str(folder / f"{_hash(url)}.%(ext)s"), "format": "bv*+ba/b", "merge_output_format": "mp4",
               "ffmpeg_location": FFMPEG_EXE, "quiet": True, "no_warnings": True, "noprogress": True,
               "noplaylist": True, "max_filesize": MAX_MEDIA_BYTES, "progress_hooks": [hook]}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))
    except Exception as e:                          # yt-dlp raises its own DownloadError for every kind of failure
        raise ValueError(DOWNLOAD_FAILED) from e
    merged = path.with_suffix(".mp4")
    return str(merged if merged.exists() else path)


# ---------------- checking the media ----------------
_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_STREAM = re.compile(r"Stream #\d+:\d+(?:\[\w+\])?(?:\((\w+)\))?:\s*(Video|Audio|Subtitle):\s*([^\s,]+)")


def probe(path: str) -> dict:
    """What a media file contains, read from ffmpeg's stream list: duration, a video stream, the audio tracks."""
    # ffmpeg prints the stream list to stderr and exits non-zero without an output file; that's expected.
    proc = subprocess.run([FFMPEG_EXE, "-nostdin", "-hide_banner", *LOCAL_INPUT, "-i", path], capture_output=True)
    text = proc.stderr.decode(errors="replace")
    m = _DURATION.search(text)
    duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
    audio, has_video = [], False
    for lang, kind, codec in _STREAM.findall(text):
        if kind == "Video" and codec not in ("mjpeg", "png"):          # cover art is not a video
            has_video = True
        elif kind == "Audio":
            audio.append({"index": len(audio), "language": lang if lang and lang != "und" else None, "codec": codec})
    return {"readable": m is not None, "duration_sec": round(duration, 2) if duration else None,
            "has_video": has_video, "audio_tracks": audio}


def check(path: str, label: str, info: Optional[dict] = None) -> dict:
    """Checks that a file can be evaluated (readable, has audio, not too long); returns its probe."""
    info = info or probe(path)
    if not info["readable"] or not info["duration_sec"]:
        raise ValueError(f"The {label} can't be read. Check that it's a video or audio file and not damaged.")
    if not info["audio_tracks"]:
        raise ValueError(f"The {label} has no audio track, so there is no speech to evaluate.")
    if info["duration_sec"] > MAX_MINUTES * 60:
        raise ValueError(f"The {label} is {info['duration_sec'] / 60:.0f} minutes long; DubEval accepts up to "
                         f"{MAX_MINUTES:.0f} minutes. Cut it shorter, or set DUBEVAL_MAX_MINUTES.")
    return info


def select_track(path: str, track: Optional[int], folder: Path, label: str) -> str:
    """The file with only audio track number `track` (counted from 0) kept, plus the video; path itself when
    track is None. Used when one file holds both the original and the dubbed audio."""
    if track is None:
        return path
    tracks = probe(path)["audio_tracks"]
    if not 0 <= track < len(tracks):
        raise ValueError(f"The {label} has {len(tracks)} audio track(s), so there is no track {track} "
                         f"(tracks are counted from 0).")
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{_hash(fingerprint(path))}_track{track}.mkv"
    if out.exists() and out.stat().st_size > 0:
        return str(out)
    tmp = out.with_name(out.stem + ".part.mkv")
    cmd = [FFMPEG_EXE, "-nostdin", "-y", *LOCAL_INPUT, "-i", path, "-map", "0:v:0?", "-map", f"0:a:{track}",
           "-c", "copy", str(tmp)]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace").strip().splitlines()[-2:]
        raise RuntimeError(f"ffmpeg could not extract audio track {track} from {path}: {' | '.join(tail)}")
    os.replace(tmp, out)
    return str(out)


# ---------------- subtitles ----------------
_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})")
_CUE = re.compile(r"(?P<a>[\d:.,]+)\s*-->\s*(?P<b>[\d:.,]+)")
_TAG = re.compile(r"<[^>]+>|\{\\[^}]*\}")


def _seconds(stamp: str) -> float:
    """SRT/VTT time ("00:01:02,500", "01:02.500") in seconds."""
    m = _TIME.fullmatch(stamp.strip())
    if not m:
        raise ValueError(stamp)
    h, mi, s, ms = m.groups()
    return int(h or 0) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_subtitles(text: str) -> list[dict]:
    """The cues of an SRT or WebVTT text: [{start, end, text}] in time order, formatting tags removed."""
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            m = _CUE.search(line)
            if not m:
                continue
            try:
                start, end = _seconds(m["a"]), _seconds(m["b"])
            except ValueError:
                break
            words = " ".join(_TAG.sub("", ln).strip() for ln in lines[i + 1:]).strip()
            if words and end > start:
                cues.append({"start": round(start, 2), "end": round(end, 2), "text": words})
            break
    return sorted(cues, key=lambda c: c["start"])


def read_subtitles(path: str, label: str) -> list[dict]:
    """The cues of a subtitle file (SRT or WebVTT)."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"The {label} subtitle file doesn't exist: {p}")
    if p.suffix.lower() not in SUBTITLE_SUFFIXES:
        raise ValueError(f"The {label} subtitles must be an .srt or .vtt file.")
    try:
        text = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = p.read_text(encoding="cp1252", errors="replace")
    cues = parse_subtitles(text)
    if not cues:
        raise ValueError(f"The {label} subtitle file has no timed lines. Check that it's a valid .srt or .vtt file.")
    return cues
