"""Inputs: local files, links, one audio track of a file, subtitle files, and the checks before evaluating."""
import subprocess

import pytest

from dubeval import inputs

NO_SLEEP = lambda s: None


def make_media(path, seconds=2, audio_tracks=1, video=True):
    """A tiny real media file made with the bundled ffmpeg: a test picture and one sine tone per audio track."""
    cmd = [inputs.FFMPEG_EXE, "-nostdin", "-y", "-loglevel", "error"]
    if video:
        cmd += ["-f", "lavfi", "-i", f"testsrc=size=64x64:rate=10:duration={seconds}"]
    for i in range(audio_tracks):
        cmd += ["-f", "lavfi", "-i", f"sine=frequency={440 * (i + 1)}:duration={seconds}"]
    for i in range((1 if video else 0) + audio_tracks):
        cmd += ["-map", str(i)]
    cmd += (["-c:v", "mpeg4"] if video else []) + (["-c:a", "aac"] if audio_tracks else []) + [str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return str(path)


# ---------------- subtitles ----------------
def test_srt_is_parsed_with_tags_removed():
    text = ("1\n00:00:01,000 --> 00:00:02,500\nHi <i>everyone</i>,\nI'm Francis.\n\n"
            "2\n00:00:03,000 --> 00:00:04,000\n{\\an8}Welcome\n")
    assert inputs.parse_subtitles(text) == [{"start": 1.0, "end": 2.5, "text": "Hi everyone, I'm Francis."},
                                            {"start": 3.0, "end": 4.0, "text": "Welcome"}]


def test_vtt_with_header_short_times_and_crlf():
    text = "﻿WEBVTT\r\n\r\nintro\r\n00:01.000 --> 00:02.200 align:start\r\n안녕하세요\r\n"
    assert inputs.parse_subtitles(text) == [{"start": 1.0, "end": 2.2, "text": "안녕하세요"}]


def test_subtitle_cues_without_text_or_time_are_skipped():
    assert inputs.parse_subtitles("1\n00:00:02,000 --> 00:00:01,000\nbackwards\n\n2\nno times here\n") == []


def test_subtitle_file_errors_are_plain(tmp_path):
    with pytest.raises(FileNotFoundError):
        inputs.read_subtitles(str(tmp_path / "missing.srt"), "original")
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an .srt or .vtt"):
        inputs.read_subtitles(str(tmp_path / "notes.txt"), "dub")
    (tmp_path / "empty.srt").write_text("nothing timed", encoding="utf-8")
    with pytest.raises(ValueError, match="no timed lines"):
        inputs.read_subtitles(str(tmp_path / "empty.srt"), "dub")


# ---------------- local files and links ----------------
def test_local_file_is_used_as_is_and_a_missing_one_is_explained(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    assert inputs.fetch(str(f), tmp_path / "cache", "original video") == str(f.resolve())
    with pytest.raises(FileNotFoundError, match="original video file doesn't exist"):
        inputs.fetch(str(tmp_path / "nope.mp4"), tmp_path / "cache", "original video")


class FakeResponse:
    def __init__(self, body: bytes, status=200, content_type="video/mp4"):
        self.body, self.status_code, self.headers = body, status, {"content-type": content_type}

    def iter_content(self, size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, **kw):
        self.calls.append(url)
        return self.responses.pop(0)


def test_direct_link_is_downloaded_once_and_cached(tmp_path):
    session = FakeSession(FakeResponse(b"video"))
    url = "https://example.com/media/dub.mp4"
    first = inputs.fetch(url, tmp_path, "dubbed video", session=session, sleep=NO_SLEEP)
    assert open(first, "rb").read() == b"video" and first.endswith(".mp4")
    assert inputs.fetch(url, tmp_path, "dubbed video", session=session, sleep=NO_SLEEP) == first
    assert len(session.calls) == 1


def test_web_page_link_without_yt_dlp_explains_the_extra(tmp_path, monkeypatch):
    monkeypatch.setattr(inputs, "_has_yt_dlp", lambda: False)
    session = FakeSession(FakeResponse(b"<html>", content_type="text/html; charset=utf-8"))
    with pytest.raises(ValueError, match="links extra"):
        inputs.fetch("https://example.com/watch?v=1", tmp_path, "dubbed video", session=session, sleep=NO_SLEEP)


def test_failed_downloads_are_retried_then_explained(tmp_path):
    session = FakeSession(FakeResponse(b"", status=500), FakeResponse(b"", status=500), FakeResponse(b"", status=500))
    with pytest.raises(ValueError, match="couldn't be downloaded"):
        inputs.fetch("https://example.com/a.mp4", tmp_path, "original video", session=session, sleep=NO_SLEEP)
    assert len(session.calls) == 3


def test_only_web_links_are_accepted(tmp_path):
    with pytest.raises(ValueError, match="http:// or https://"):
        inputs.fetch("https://", tmp_path, "original video")


def test_fingerprint_changes_when_a_local_file_changes(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"one")
    before = inputs.fingerprint(str(f))
    f.write_bytes(b"three")
    assert inputs.fingerprint(str(f)) != before and inputs.fingerprint(" https://x.com/a.mp4 ") == "https://x.com/a.mp4"


# ---------------- checks and audio tracks (real ffmpeg) ----------------
def test_probe_reads_duration_video_and_audio_tracks(tmp_path):
    info = inputs.probe(make_media(tmp_path / "two.mkv", seconds=2, audio_tracks=2))
    assert info["readable"] and info["has_video"] and 1.9 <= info["duration_sec"] <= 2.2
    assert [t["index"] for t in info["audio_tracks"]] == [0, 1]


def test_check_refuses_unreadable_silent_and_too_long_files(tmp_path, monkeypatch):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="can't be read"):
        inputs.check(str(junk), "original video")
    with pytest.raises(ValueError, match="no audio track"):
        inputs.check(make_media(tmp_path / "silent.mp4", audio_tracks=0), "dubbed video")
    monkeypatch.setattr(inputs, "MAX_MINUTES", 0.01)
    with pytest.raises(ValueError, match="accepts up to"):
        inputs.check(make_media(tmp_path / "ok.mp4"), "dubbed video")


def test_one_audio_track_is_selected_from_a_two_track_file(tmp_path):
    both = make_media(tmp_path / "film.mkv", audio_tracks=2)
    assert inputs.select_track(both, None, tmp_path / "c", "original video") == both
    dub = inputs.select_track(both, 1, tmp_path / "c", "dubbed video")
    info = inputs.probe(dub)
    assert len(info["audio_tracks"]) == 1 and info["has_video"]
    assert inputs.select_track(both, 1, tmp_path / "c", "dubbed video") == dub      # reused, not extracted again
    with pytest.raises(ValueError, match="has 2 audio track"):
        inputs.select_track(both, 2, tmp_path / "c", "dubbed video")


def test_a_download_larger_than_the_limit_stops_and_is_explained(tmp_path, monkeypatch):
    monkeypatch.setattr(inputs, "MAX_MEDIA_BYTES", 4)
    with pytest.raises(ValueError, match="larger than"):              # the size the server gives
        big = FakeResponse(b"x")
        big.headers["content-length"] = "5"
        inputs.fetch("https://example.com/a.mp4", tmp_path, "dub", session=FakeSession(big), sleep=NO_SLEEP)
    with pytest.raises(ValueError, match="larger than"):              # no size given: counted while downloading
        inputs.fetch("https://example.com/b.mp4", tmp_path, "dub", session=FakeSession(FakeResponse(b"12345")),
                     sleep=NO_SLEEP)
    assert not list(tmp_path.glob("*"))                               # nothing half-written is kept


def test_ffmpeg_never_reads_from_the_network(tmp_path, monkeypatch):
    # A video can be a playlist that names web addresses; ffmpeg may only open files.
    from dubeval import evaluate, pairing
    seen = []

    class Done:
        returncode, stdout, stderr = 0, b"", b"Duration: 00:00:01.00"
    monkeypatch.setattr(inputs.subprocess, "run", lambda cmd, **kw: seen.append(cmd) or Done())
    inputs.probe("a.mp4")
    evaluate.extract_audio("a.mp4", str(tmp_path / "a.wav"))
    pairing.read_frames("a.mp4", 2.0, "ffmpeg")
    assert len(seen) == 3
    for cmd in seen:
        i = cmd.index("-i")
        assert cmd[i - 2:i] == ["-protocol_whitelist", "file"]
