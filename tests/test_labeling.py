"""The labelling page: answers are saved into the sheet intact, only the sheet's files are served."""
import pytest
from fastapi.testclient import TestClient

from dubeval import labeling

SHEET = """# my test set
# labels: good / check / poor
pair_id,service,original,dub,label,length_label,meaning_label,notes
p1,perso,videos/a_en.mp4,videos/a_ko.mp4,,,,
p2,human,https://example.com/o.mp4,videos/b_ko.mp4,good,good,good,already done
"""


TOKEN = "launch-token"


def opened(app) -> TestClient:
    """A browser on this machine that opened the page with this launch's link."""
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.get(f"/?token_given={TOKEN}", follow_redirects=False).status_code == 303
    return client


@pytest.fixture
def sheet(tmp_path):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "a_en.mp4").write_bytes(b"orig")
    (tmp_path / "videos" / "a_ko.mp4").write_bytes(b"dub")
    (tmp_path / "secret.txt").write_text("not in the sheet", encoding="utf-8")
    path = tmp_path / "set.csv"
    path.write_text(SHEET, encoding="utf-8")
    return path


def test_an_answer_is_saved_and_the_sheet_keeps_its_comments_and_columns(sheet):
    row = labeling.save_answer(str(sheet), "p1", {"label": "Check", "meaning_label": "poor", "notes": " movie,\n not English "})
    assert row["label"] == "check" and row["meaning_label"] == "poor" and row["notes"] == "movie, not English"
    text = sheet.read_text(encoding="utf-8-sig")
    assert text.startswith("# my test set\n# labels: good / check / poor\npair_id,service,original,dub,label,")
    _, columns, rows = labeling.read_sheet(str(sheet))
    assert columns[-1] == "reviewer" or "reviewer" not in columns
    assert rows[1]["notes"] == "already done" and rows[0]["length_label"] == ""


def test_bad_answers_and_unknown_pairs_are_refused(sheet):
    with pytest.raises(ValueError, match="good, check or poor"):
        labeling.save_answer(str(sheet), "p1", {"label": "great"})
    with pytest.raises(KeyError):
        labeling.save_answer(str(sheet), "p9", {"label": "good"})


def test_a_sheet_without_original_and_dub_columns_is_explained(tmp_path):
    bad = tmp_path / "x.csv"
    bad.write_text("link,label\nhttps://perso.ai/x?seq=1,good\n", encoding="utf-8")
    with pytest.raises(ValueError, match="original and dub columns"):
        labeling.read_sheet(str(bad))


def test_the_page_lists_pairs_serves_their_files_and_saves(sheet, tmp_path):
    results = tmp_path / "run"
    results.mkdir()
    (results / "summary.csv").write_text("n,link,pair_id,verdict,line_length_level,meaning_level\n"
                                         "1,videos/a_ko.mp4,p1,poor,check,not_measured\n", encoding="utf-8")
    client = opened(labeling.make_app(str(sheet), str(results), "ko", token=TOKEN))
    page = client.get("/")
    assert page.status_code == 200 and "테스트 세트 라벨링" in page.text
    pairs = client.get("/api/pairs").json()
    assert [p["pair_id"] for p in pairs] == ["p1", "p2"]
    assert pairs[0]["original"] == "/media/p1/original" and pairs[1]["original"] == "https://example.com/o.mp4"
    assert pairs[0]["tool"] == {"label": "poor", "length_label": "check", "meaning_label": "not_measured"}
    assert client.get("/media/p1/dub").content == b"dub"
    assert client.post("/api/pairs/p1", json={"length_label": "good"}).json()["length_label"] == "good"
    assert client.post("/api/pairs/p1", json={"label": "awful"}).status_code == 400


def test_only_files_named_in_the_sheet_are_served(sheet):
    client = opened(labeling.make_app(str(sheet), token=TOKEN))
    assert client.get("/media/p2/original").status_code == 404           # a link is played from its own host
    assert client.get("/media/p1/secret").status_code == 404
    assert client.get("/media/p9/dub").status_code == 404
    assert client.get("/media/..%2Fsecret.txt/dub").status_code == 404
    assert client.post("/api/pairs/p9", json={"label": "good"}).status_code == 404


def test_the_page_needs_this_launchs_link(sheet):
    client = TestClient(labeling.make_app(str(sheet), token=TOKEN), base_url="http://127.0.0.1")
    assert client.get("/").status_code == 401
    assert client.get("/api/pairs").status_code == 401
    assert client.post("/api/pairs/p1", json={"label": "good"}).status_code == 401      # labels stay the person's
    assert client.get("/?token_given=an-old-one").status_code == 401
    assert client.get(f"/?token_given={TOKEN}").status_code == 200                      # cookie set, page shown
    assert client.get("/api/pairs").status_code == 200


def test_the_page_answers_only_requests_to_this_machine(sheet):
    client = opened(labeling.make_app(str(sheet), token=TOKEN))
    assert client.get("/api/pairs", headers={"host": "evil.example:8000"}).status_code == 403


def test_only_the_pages_own_script_may_run(sheet):
    page = opened(labeling.make_app(str(sheet), token=TOKEN)).get("/")
    policy = page.headers["content-security-policy"]
    nonce = policy.split("'nonce-")[1].split("'")[0]
    assert f'<script nonce="{nonce}">' in page.text and page.text.count("<script") == 1
    assert "frame-ancestors 'none'" in policy and page.headers["x-content-type-options"] == "nosniff"
