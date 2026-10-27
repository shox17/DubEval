"""In-memory stand-in for Perso's public share endpoint and media host (shapes from https://developers.perso.ai/llms.txt)."""
import json
from typing import Optional


SHARE_TOKEN = "TESTshareTOKENaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHARE_URL = f"https://perso.ai/en/share/video-translator?seq={SHARE_TOKEN}"

# Shape of GET /projects/shared/{token}, the real response shape (placeholder values).
SHARED_PROJECT = {
    "seq": 100001, "title": "QA sample.mp4 → ko", "projectType": "VIDEO", "userName": "te*****01", "durationMs": 28683,
    "sourceLanguage": {"code": "en", "name": "English (US)", "languageTag": "default", "experiment": False},
    "targetLanguage": {"code": "ko", "name": "Korean", "languageTag": "default", "experiment": False},
    "thumbnailUrl": "/perso-storage/u/2026_09/original/thumb.webp",
    "originalFileUrl": "/perso-storage/u/2026_09/original/original video.mp4",
    "translatedFileUrl": "/perso-storage/u/2026_09/p-100000/QA_ko_TranslatedVideo.mp4",
    "lipSyncFileUrl": "/perso-storage/u/2026_09/p-100001/QA_ko_Lip-syncedVideo.mp4",
    "isLipSync": True,
}


# A second dub of the same video, for compare mode.
SHARE_TOKEN_B = "TESTshareTOKENbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
SHARE_URL_B = f"https://perso.ai/en/share/video-translator?seq={SHARE_TOKEN_B}"
SHARED_PROJECT_B = {**SHARED_PROJECT, "seq": 100002, "title": "QA sample.mp4 → ko (v2)",
                    "translatedFileUrl": "/perso-storage/u/2026_09/p-100002/QA_ko_v2_TranslatedVideo.mp4",
                    "lipSyncFileUrl": "/perso-storage/u/2026_09/p-100002/QA_ko_v2_Lip-syncedVideo.mp4"}


SHARE_TOKEN_C = "TESTshareTOKENcccccccccccccccccccccccccccccccccccccccccccccccccc"
SHARE_URL_C = f"https://perso.ai/en/share/video-translator?seq={SHARE_TOKEN_C}"
SHARED_PROJECT_C = {**SHARED_PROJECT, "seq": 100003, "title": "QA sample.mp4 → ko (v3)",
                    "translatedFileUrl": "/perso-storage/u/2026_09/p-100003/QA_ko_v3_TranslatedVideo.mp4",
                    "lipSyncFileUrl": "/perso-storage/u/2026_09/p-100003/QA_ko_v3_Lip-syncedVideo.mp4"}


class FakeResponse:
    """Minimal stand-in for requests.Response (status, JSON body, raw bytes)."""
    def __init__(self, status: int = 200, body=None, raw: Optional[bytes] = None):
        self.status_code = status
        self._body = body
        self.content = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")

    def json(self):
        return self._body if self._body is not None else json.loads(self.content)

    def iter_content(self, _size):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakePerso:
    """Scriptable fake used as the requests session: answers the shared-project call and media downloads."""

    def __init__(self, video_bytes: bytes = b"dubbed-video", original_bytes: Optional[bytes] = None,
                 shared_project: Optional[dict] = None, share_error: Optional[tuple] = None,
                 projects: Optional[dict] = None):
        self.projects = projects          # token -> project, to serve several share links (compare mode)
        self.video_bytes = video_bytes
        self.original_bytes = original_bytes if original_bytes is not None else video_bytes
        self.shared_project = shared_project if shared_project is not None else dict(SHARED_PROJECT)
        self.share_error = share_error
        self.calls: list[tuple[str, str, Optional[dict]]] = []

    def request(self, method, url, headers=None, params=None, timeout=None, **kw):
        """Answers GET /projects/shared/{token}. Records every call and checks no API key is sent."""
        path = url.split("perso.ai", 1)[1]
        self.calls.append((method, path, params))
        assert "XP-API-KEY" not in (headers or {}), "share links must not send an API key"
        if path.startswith("/video-translator/api/v1/projects/shared/"):
            if self.share_error:
                status, code = self.share_error
                return FakeResponse(status, {"code": code, "message": "nope"})
            if self.projects is not None:
                project = self.projects.get(path.rsplit("/", 1)[1])
                return FakeResponse(body=project) if project else FakeResponse(404, {"code": "X404", "message": "nope"})
            return FakeResponse(body=self.shared_project)
        return FakeResponse(404, {"code": "X404", "message": f"unknown {path}"})

    def get(self, url, stream=False, timeout=None):
        """Fake media download; checks the URL is on the media host and URL-encoded."""
        self.calls.append(("GET-MEDIA", url, None))
        assert url.startswith("https://portal-media.perso.ai/perso-storage/") and " " not in url
        return FakeResponse(200, raw=self.original_bytes if "/original/" in url else self.video_bytes)


class CopyingFakePerso(FakePerso):
    """Downloads return the bytes of a real video, so the evaluation can run on the 'dub'."""

    def __init__(self, source_video: str, **kw):
        with open(source_video, "rb") as f:
            super().__init__(video_bytes=f.read(), **kw)
