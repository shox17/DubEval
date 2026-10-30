"""Meaning: the judge's line-by-line input, the judge choice, the local judge, the offline screen, and dub types."""
import json

import pytest

from dubeval import meaning, pipeline, translation_judge as tj
from dubeval.report import build_report
from sample_results import JUDGE_OFF, make_results

def answer_line(n, semantic=9, reason="", error_type="no_error"):
    """One line of a rubric answer: the five scores, four-language reasons, ideal translation, error type."""
    from dubeval.translation_judge import CRITERIA
    langs = {k: reason for k in ("en", "ko", "pt", "es")}
    scores = {c: (semantic if c == "semantic_accuracy" else 9) for c in CRITERIA}
    return {"line": n, **scores, **{f"{c}_reason": langs if scores[c] <= 7 else {k: "" for k in langs} for c in CRITERIA},
            "ideal_translation": "영어를 가르칩니다." if semantic <= 7 else "", "error_type": error_type,
            "may_be_recognition_error": False}


# Line 2 ("I teach English." → "영화를 가르칩니다.") is a serious meaning error; the others are fine.
GOOD_ANSWER = {"lines": [answer_line(1), answer_line(2, semantic=3, reason="English became movies.",
                                                     error_type="distortion"), answer_line(3)]}


def judged(answer, model, provider, lines):
    """The translation check's result for an answer, built the way judge_translation builds it."""
    return tj._rubric_result([tj._result(json.loads(json.dumps(answer)), model, provider)], lines)


def results_with_lines(**extra):
    """Results with three matched lines and one original-only line."""
    r = make_results(**extra)
    r["speech_recognition"]["original_segments"] = [
        {"start": 0.0, "end": 2.0, "text": "Hi, I'm Francis."}, {"start": 3.0, "end": 5.0, "text": "I teach English."},
        {"start": 6.0, "end": 7.0, "text": "Thank you."}, {"start": 8.0, "end": 9.0, "text": "Bye."}]
    r["speech_recognition"]["dubbed_segments"] = [
        {"start": 0.1, "end": 2.1, "text": "안녕하세요, 프랜시스입니다."}, {"start": 3.1, "end": 5.2, "text": "영화를 가르칩니다."},
        {"start": 6.0, "end": 7.1, "text": "감사합니다."}]
    lines = [{"n": i + 1, "start": s, "end": e, "original": [i], "dub": [i], "original_sec": e - s, "dub_sec": e - s,
              "diff_sec": 0.0, "diff_pct": 0.0, "start_shift_sec": 0.0, "overrun_sec": 0.0, "short": False}
             for i, (s, e) in enumerate([(0.0, 2.0), (3.0, 5.0), (6.0, 7.0)])]
    r["segment_alignment"] = {"groups": [], "lines": lines, "unmatched_original": [3], "unmatched_dub": []}
    r["pipeline"] = {"input": {"source_language_name": "English", "target_language_name": "Korean"}}
    return r


# ---------------- what the judge is shown ----------------
def test_judge_lines_pair_both_sides_and_keep_one_sided_speech():
    lines = pipeline.judge_lines(results_with_lines())
    assert [ln["n"] for ln in lines] == [1, 2, 3, 4]
    assert lines[1] == {"n": 2, "start": 3.0, "end": 5.0, "original": "I teach English.", "dub": "영화를 가르칩니다."}
    assert lines[3]["original"] == "Bye." and lines[3]["dub"] == ""


def test_subtitles_add_what_each_side_was_meant_to_say_on_the_original_timeline():
    r = results_with_lines(subtitles={"original": [{"start": 3.0, "end": 5.0, "text": "I teach English!"}],
                                      "dub": [{"start": 5.1, "end": 7.0, "text": "영어를 가르칩니다."}]},
                           pairing={"applied_offset_sec": 2.0})
    line = pipeline.judge_lines(r)[1]
    assert line["original_script"] == "I teach English!" and line["dub_script"] == "영어를 가르칩니다."


def test_the_judge_gets_lines_and_the_dub_type(isolated_output, monkeypatch):
    seen = {}
    monkeypatch.setattr(pipeline, "judge_translation", lambda *a, **k: seen.update(k) or tj.not_measured("r.judge.off"))
    r = results_with_lines()
    r["pipeline"]["input"]["dub_type"] = "human"
    pipeline.check_translation(r, True, lambda *a, **k: None)
    assert seen["dub_type"] == "human" and len(seen["lines"]) == 4


# ---------------- choosing the judge ----------------
@pytest.mark.parametrize("setting, available, expected", [
    ("auto", {"claude": True, "gemini": True, "ollama": True}, "claude"),
    ("auto", {"claude": False, "gemini": True, "ollama": True}, "gemini"),
    ("auto", {"claude": False, "gemini": False, "ollama": True}, "ollama"),
    ("auto", {"claude": False, "gemini": False, "ollama": False}, None),
    ("ollama", {"claude": True, "gemini": True, "ollama": True}, "ollama"),
    ("gemini", {"claude": True, "gemini": False, "ollama": True}, None),
    ("off", {"claude": True, "gemini": True, "ollama": True}, None),
])
def test_judge_choice(monkeypatch, setting, available, expected):
    monkeypatch.setenv("DUBEVAL_JUDGE", setting)
    monkeypatch.setattr(tj, "claude_available", lambda: available["claude"])
    monkeypatch.setattr(tj, "gemini_key", lambda: "k" if available["gemini"] else None)
    monkeypatch.setattr(tj, "ollama_available", lambda: available["ollama"])
    assert tj.judge_provider() == expected


class FakeOllama:
    """A stand-in for Ollama's /api/chat."""
    def __init__(self, status=200, content=None, done_reason="stop"):
        self.status, self.content, self.done_reason, self.calls = status, content, done_reason, []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        body = {"message": {"content": self.content}, "done_reason": self.done_reason}
        return type("R", (), {"status_code": self.status, "json": lambda s: body})()


def test_the_local_judge_asks_ollama_for_schema_shaped_json():
    english = {**answer_line(1, semantic=3, error_type="distortion"),
               **{f"{c}_reason": "" for c in tj.CRITERIA}, "semantic_accuracy_reason": "English became movies."}
    session = FakeOllama(content=json.dumps({"lines": [english]}))
    r = tj.judge_translation([{"start": 0, "end": 1, "text": "Hi"}], [{"start": 0, "end": 1, "text": "안녕"}], "en", "ko",
                             session=session, provider="ollama")
    url, body = session.calls[0]
    assert url.endswith("/api/chat") and body["format"] == tj.LOCAL_SCHEMA and body["stream"] is False
    reason = tj.LOCAL_SCHEMA["properties"]["lines"]["items"]["properties"]["semantic_accuracy_reason"]
    assert reason["type"] == "string" and "plain English" in body["messages"][0]["content"]
    assert body["options"]["temperature"] == 0 and body["model"] == tj.OLLAMA_MODEL
    assert r["measured"] and r["meaning_score"] == 3.0 and r["model"].endswith("(local)")
    assert r["issues"][0]["explanation"]["es"] == "English became movies."      # English, shown in every language


class SlowOllama:
    def post(self, *a, **k):
        import requests
        raise requests.Timeout()


class DownOllama:
    def post(self, *a, **k):
        import requests
        raise requests.ConnectionError()


@pytest.mark.parametrize("session, reason", [
    (SlowOllama(), "didn't answer within"),
    (DownOllama(), "Start Ollama"),
    (FakeOllama(status=404), "isn't installed in Ollama"),
    (FakeOllama(content="not json"), "couldn't be read"),
    (FakeOllama(content="{}", done_reason="length"), "cut off"),
])
def test_local_judge_failures_are_not_measured_with_a_reason(session, reason):
    r = tj.judge_translation([{"start": 0, "end": 1, "text": "Hi"}], [{"start": 0, "end": 1, "text": "안녕"}], "en", "ko",
                             session=session, provider="ollama")
    assert r["measured"] is False and reason in r["reason"]


# ---------------- the offline screen ----------------
def fake_encode(texts):
    """Vectors that make line 2 ('English' heard as '영화') dissimilar and the rest similar."""
    return [[0.0, 1.0] if ("영화" in t) else [1.0, 0.0] for t in texts]


def test_screen_scores_every_line_both_sides_speak():
    r = meaning.screen(pipeline.judge_lines(results_with_lines()), encode=fake_encode)
    assert r["measured"] and [ln["n"] for ln in r["lines"]] == [1, 2, 3]
    assert [ln["similarity"] for ln in r["lines"]] == [1.0, 0.0, 1.0] and r["median"] == 1.0


def test_screen_without_its_package_is_not_measured():
    assert meaning.screen(pipeline.judge_lines(results_with_lines()))["reason_key"] == "r.screen.not_installed"
    assert meaning.screen([])["reason_key"] == "r.screen.no_lines"


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_a_low_line_is_check_and_becomes_an_interval_when_no_judge_ran(lang):
    r = results_with_lines(translation_judge=JUDGE_OFF)
    r["meaning_screen"] = meaning.screen(pipeline.judge_lines(r), encode=fake_encode)
    rep = build_report(r, lang)
    row = next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == "meaning_screen")
    assert row["level"] == "check" and "{" not in row["message"] + row["display"]
    drift = [i for i in rep["problem_intervals"] if i["category"] == "meaning_drift"]
    assert len(drift) == 1 and drift[0]["start"] == 3.0


def test_with_a_judge_its_issues_sit_on_their_line_and_the_screen_adds_none():
    r = results_with_lines()
    r["meaning_screen"] = meaning.screen(pipeline.judge_lines(r), encode=fake_encode)
    r["translation_judge"] = judged(GOOD_ANSWER, "claude-opus-5-5", "Claude", pipeline.judge_lines(r))
    rep = build_report(r, "en")
    assert not [i for i in rep["problem_intervals"] if i["category"] == "meaning_drift"]
    wrong = [i for i in rep["problem_intervals"] if i["category"] == "mistranslation"]
    assert wrong and (wrong[0]["start"], wrong[0]["end"]) == (3.0, 5.0)


def test_screen_rows_are_good_when_every_line_is_close():
    r = results_with_lines()
    r["meaning_screen"] = meaning.screen(pipeline.judge_lines(r), encode=lambda texts: [[1.0, 0.0] for _ in texts])
    row = next(m for s in build_report(r, "en")["sections"] for m in s["metrics"] if m["id"] == "meaning_screen")
    assert row["level"] == "good"


# ---------------- dub types ----------------
@pytest.mark.parametrize("dub_type, key", [("human", "r.vs.not_compared_human"), ("ai_stock", "r.vs.not_compared_stock")])
def test_voice_similarity_is_not_compared_for_another_voice_by_design(dub_type, key):
    r = make_results()
    pipeline.apply_dub_type(r, dub_type)
    assert r["voice_similarity"]["reason_key"] == key
    row = next(m for s in build_report(r, "en")["sections"] for m in s["metrics"] if m["id"] == "voice_similarity")
    assert row["level"] == "not_measured" and "expected" in row["message"]


def test_a_clone_keeps_its_voice_similarity():
    r = make_results()
    before = r.get("voice_similarity")
    pipeline.apply_dub_type(r, "ai_clone")
    assert r.get("voice_similarity") == before


def test_an_unknown_dub_type_is_refused(tmp_path):
    with pytest.raises(ValueError, match="ai_clone, ai_stock or human"):
        pipeline.evaluate_files("a.mp4", "b.mp4", lambda *a, **k: None, lambda: None, dub_type="robot")



def test_auto_moves_on_when_a_judge_has_no_credit(monkeypatch):
    calls = []
    answers = {"claude": tj.not_measured("r.judge.no_credit", model="Claude"),
               "gemini": tj._result({"lines": [answer_line(1)]}, "gemini-3.5-flash", "Gemini")}
    monkeypatch.setenv("DUBEVAL_JUDGE", "auto")
    monkeypatch.setattr(tj, "claude_available", lambda: True)
    monkeypatch.setattr(tj, "gemini_key", lambda: "k")
    monkeypatch.setattr(tj, "_run_judge", lambda p, *a: calls.append(p) or answers[p])
    r = tj.judge_translation([{"start": 0, "end": 1, "text": "Hi"}], [{"start": 0, "end": 1, "text": "안녕"}], "en", "ko")
    assert calls == ["claude", "gemini"] and r["measured"] and r["model"] == "gemini-3.5-flash"


def test_a_chosen_judge_never_hands_over(monkeypatch):
    calls = []
    monkeypatch.setenv("DUBEVAL_JUDGE", "claude")
    monkeypatch.setattr(tj, "claude_available", lambda: True)
    monkeypatch.setattr(tj, "gemini_key", lambda: "k")
    monkeypatch.setattr(tj, "_run_judge", lambda p, *a: calls.append(p) or tj.not_measured("r.judge.no_credit", model="Claude"))
    r = tj.judge_translation([{"start": 0, "end": 1, "text": "Hi"}], [{"start": 0, "end": 1, "text": "안녕"}], "en", "ko")
    assert calls == ["claude"] and r["reason_key"] == "r.judge.no_credit"


# ---------------- which model the screen runs ----------------
@pytest.fixture
def real_backend(monkeypatch, tmp_path):
    """The real backend choice (conftest stubs it out), with the pack folder in tmp_path."""
    import importlib
    monkeypatch.setattr(meaning, "backend", importlib.reload(meaning).backend)
    monkeypatch.setattr(meaning, "PACK_DIR", tmp_path / "pack")
    monkeypatch.delenv("DUBEVAL_MEANING_SCREEN", raising=False)
    return tmp_path / "pack"


def write_pack(folder, model=b"onnx-bytes", sizes=None):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model.onnx").write_bytes(model)
    (folder / "tokenizer.json").write_text("{}", encoding="utf-8")
    files = sizes or {"model.onnx": {"bytes": len(model)}, "tokenizer.json": {"bytes": 2}}
    (folder / "pack.json").write_text(json.dumps({"files": files}), encoding="utf-8")


def test_the_onnx_pack_is_preferred_and_named_apart_in_caches(real_backend, monkeypatch):
    monkeypatch.setattr(meaning, "_sentence_transformers", lambda: True)
    assert meaning.backend() == "torch" and meaning.model_name() == meaning.MODEL_NAME
    write_pack(real_backend)
    assert meaning.backend() == "onnx" and meaning.model_name() == meaning.PACK_NAME != meaning.MODEL_NAME


def test_an_incomplete_pack_is_not_used(real_backend, monkeypatch):
    monkeypatch.setattr(meaning, "_sentence_transformers", lambda: False)
    write_pack(real_backend, sizes={"model.onnx": {"bytes": 999}, "tokenizer.json": {"bytes": 2}})  # cut download
    assert meaning.backend() is None and not meaning.available()
    assert meaning.screen(pipeline.judge_lines(results_with_lines()))["reason_key"] == "r.screen.not_installed"


def test_the_screen_can_be_switched_off_even_with_the_pack(real_backend, monkeypatch):
    write_pack(real_backend)
    monkeypatch.setenv("DUBEVAL_MEANING_SCREEN", "off")
    assert meaning.backend() is None
    assert meaning.screen(pipeline.judge_lines(results_with_lines()))["reason_key"] == "r.screen.off"
