"""The start page's previews: Perso share links (fake endpoint), web pages, direct links and files on this computer."""
import pytest
from fake_perso import SHARE_TOKEN, SHARE_URL

from dubeval import preview


class FakeResponse:
    def __init__(self, status=200, body=b"", content_type="image/webp", json_body=None):
        self.status_code, self.body, self.headers = status, body, {"content-type": content_type}
        self._json = json_body

    def json(self):
        return self._json

    def iter_content(self, size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, **kw):
        self.calls.append(url)
        return next(r for key, r in self.routes.items() if key in url)

    def request(self, method, url, **kw):
        return self.get(url, **kw)




def test_a_perso_share_link_gives_its_title_languages_and_picture():
    project = {"title": "input", "durationMs": 95681, "sourceLanguage": {"code": "en"},
               "targetLanguage": {"code": "uz"}, "isLipSync": False, "thumbnailUrl": "/perso-storage/t.webp",
               "translatedFileUrl": "/perso-storage/d.mp4", "originalFileUrl": "/perso-storage/o.mp4"}
    session = FakeSession({f"projects/shared/{SHARE_TOKEN}": FakeResponse(json_body=project, content_type="application/json"),
                           "t.webp": FakeResponse(body=b"img")})
    p = preview.preview(SHARE_URL, session=session)
    assert (p["kind"], p["title"], p["source_lang"], p["target_lang"], p["duration_sec"]) == ("perso", "input", "en", "uz", 95.7)
    assert p["thumbnail"] == "data:image/webp;base64,aW1n"


def test_a_picture_that_isnt_an_image_or_is_too_big_is_left_out():
    assert preview._image("https://x/a", FakeSession({"x/a": FakeResponse(body=b"<html>", content_type="text/html")})) is None
    big = FakeResponse(body=b"x" * (preview.MAX_IMAGE_BYTES + 1))
    assert preview._image("https://x/b", FakeSession({"x/b": big})) is None


def test_a_direct_video_link_is_named_without_being_downloaded():
    p = preview.preview("https://example.com/media/dub.mp4", session=FakeSession({}))
    assert p["kind"] == "media_link" and p["title"] == "dub.mp4"


def test_a_web_page_that_cant_be_read_is_explained(monkeypatch):
    import yt_dlp

    class Broken:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, *a, **k):
            raise RuntimeError("no network")
    monkeypatch.setattr(yt_dlp, "YoutubeDL", Broken)
    with pytest.raises(ValueError, match="Couldn't read this link"):
        preview.preview("https://www.youtube.com/watch?v=x", session=FakeSession({}))


def test_a_missing_file_is_explained(tmp_path):
    with pytest.raises(ValueError, match="no video at this path"):
        preview.preview(str(tmp_path / "missing.mp4"))


def test_the_moments_tried_for_a_picture():
    assert preview.frame_times(60.0) == [6.0, 15.0, 30.0, 1.0]
    assert preview.frame_times(600.0)[0] == 20.0                 # past the opening, not a minute in
    assert preview.frame_times(1.0) == [0.1, 0.25, 0.5]           # a very short video: no duplicates
    assert preview.frame_times(None) == [1.0, 5.0]


def test_a_video_that_fades_in_gets_a_picture_that_is_not_black(tmp_path):
    """A clip black for its first 3 s, then bright: a frame a second in would be black."""
    import base64
    import subprocess
    from dubeval.inputs import FFMPEG_EXE
    clip = tmp_path / "fade.mp4"
    subprocess.run([FFMPEG_EXE, "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "color=white:s=160x90:d=10",
                    "-vf", "fade=in:st=0:d=0.1:color=black,fade=in:st=3:d=0.1", "-pix_fmt", "yuv420p", str(clip)],
                   check=True, timeout=60)
    uri = preview._frame(str(clip), 10.0)
    level = preview._brightness(base64.b64decode(uri.split(",", 1)[1]))
    assert level is not None and level >= preview.DARK_LEVEL
    black = tmp_path / "black.mp4"
    subprocess.run([FFMPEG_EXE, "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=160x90:d=4",
                    "-pix_fmt", "yuv420p", str(black)], check=True, timeout=60)
    assert preview._frame(str(black), 4.0).startswith("data:image/jpeg")   # all black: still a picture, never none
