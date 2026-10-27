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
