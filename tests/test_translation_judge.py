"""Tests for the translation check (the line-by-line rubric) with Gemini, Claude and ChatGPT, using fake sessions and
clients (never the real APIs)."""
import json
from types import SimpleNamespace

import pytest

from dubeval import translation_judge
from dubeval.translation_judge import build_prompt, count_issues, judge_provider, judge_translation

ORIG = [{"start": 0.0, "end": 2.0, "text": "Hi, I'm John from Uzbekistan."}]
DUB = [{"start": 0.1, "end": 2.2, "text": "안녕하세요, 우즈베키스탄에서 온 존입니다."}]


class FakeClient:
    """Records the request and returns a canned response, like client.beta.messages.create would."""

    def __init__(self, payload=None, stop_reason="end_turn", error=None):
        self.payload, self.stop_reason, self.error, self.request = payload, stop_reason, error, None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.request = kw
        if self.error:
            raise self.error
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return SimpleNamespace(stop_reason=self.stop_reason, model="claude-opus-5-5",
                               content=[SimpleNamespace(type="text", text=text)])


def judged(n, semantic=9, naturalness=9, context=9, terms=9, local=9, error_type="no_error", misheard=False,
           ideal="", reason=""):
    """One line of the judge's answer in the rubric's shape (reasons as four-language objects)."""
    def langs(text):
        return {lang: text for lang in ("en", "ko", "pt", "es")}
    scores = dict(zip(translation_judge.CRITERIA, (semantic, naturalness, context, terms, local)))
    return {"line": n, **scores, **{f"{c}_reason": langs(reason if v <= 7 else "") for c, v in scores.items()},
            "ideal_translation": ideal, "error_type": error_type, "may_be_recognition_error": misheard}


GOOD = {"lines": [judged(1)]}
BAD = {"lines": [judged(1, semantic=4, error_type="omission", ideal="안녕하세요, 우즈베키스탄에서 온 존입니다!",
                         reason="The greeting is dropped.")]}


def test_judge_scores_every_line_and_files_low_scores_as_issues():
    client = FakeClient(BAD)
    r = judge_translation(ORIG, DUB, "en", "ko", client=client)
    assert r["measured"] and r["rubric"] and r["scale"] == 10 and r["model"] == "claude-opus-5-5"
    assert r["meaning_score"] == 4.0 and r["criteria"]["linguistic_naturalness"] == 9.0
    [issue] = r["issues"]
    assert issue["severity"] == "major" and issue["type"] == "missing" and issue["error_type"] == "omission"
    assert issue["criterion"] == "semantic_accuracy" and issue["score"] == 4
    assert issue["explanation"]["ko"] == "The greeting is dropped." and issue["ideal_translation"].startswith("안녕")
    assert count_issues(r, ("missing", "added")) == 1
    req = client.request
    assert req["model"] == "claude-opus-5-5" and req["fallbacks"] == "default"
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "Hi, I'm John from Uzbekistan. -> 안녕하세요" in req["messages"][0]["content"]
    # A faithful line files nothing.
    assert judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(GOOD))["issues"] == []


def test_the_rubric_and_its_score_descriptions_reach_the_judge():
    from dubeval.translation_judge import RESULT_SCHEMA, SYSTEM_PROMPT
    line = RESULT_SCHEMA["properties"]["lines"]["items"]
    assert set(translation_judge.CRITERIA) <= set(line["required"])
    semantic = line["properties"]["semantic_accuracy"]
    assert semantic["description"].startswith("10 : The core meaning") and (semantic["minimum"], semantic["maximum"]) == (1, 10)
    assert {"omission", "no_error"} <= set(line["properties"]["error_type"]["enum"])
    assert "의미 전달 정확성 (semantic_accuracy)" in SYSTEM_PROMPT and "7점 이하는 이유를 무조건 설명해야함" in SYSTEM_PROMPT
    assert "may_be_recognition_error" in SYSTEM_PROMPT


def test_prompt_labels_languages():
    p = build_prompt(ORIG, DUB, "en", "ko", description="Self-introduction")
    assert "<source_language>en</source_language>" in p and "<target_language>ko</target_language>" in p
    assert "Title: Self-introduction." in p and "<evaluate>1</evaluate>" in p


def test_prompt_line_by_line_with_scripts_and_dub_type():
    lines = [{"n": 1, "start": 0.0, "end": 2.0, "original": "Hi, I'm John.", "dub": "안녕하세요, 존입니다.",
              "dub_script": "안녕하세요. 저는 존입니다."},
             {"n": 2, "start": 3.0, "end": 4.0, "original": "Bye.", "dub": ""}]
    p = build_prompt(ORIG, DUB, "en", "ko", lines=lines, dub_type="human")
    assert "[1] 0.0-2.0 s : Hi, I'm John. -> 안녕하세요, 존입니다." in p and "(dub script: 안녕하세요. 저는 존입니다.)" in p
    assert "[2] 3.0-4.0 s : Bye. -> (nothing)" in p and "human voice actors" in p
    assert "close translation" in build_prompt(ORIG, DUB, "en", "ko", lines=lines, dub_type="ai_clone")


def test_a_long_video_is_judged_in_chunks_with_the_rest_as_context():
    lines = [{"n": i, "start": float(i), "end": i + 0.9, "original": f"line {i}", "dub": f"줄 {i}"} for i in range(1, 36)]

    class Chunks(FakeClient):
        def __init__(self):
            super().__init__()
            self.prompts = []

        def create(self, **kw):
            text = kw["messages"][0]["content"]
            self.prompts.append(text)
            numbers = text.split("<evaluate>")[1].split("</evaluate>")[0].split(", ")
            self.payload = {"lines": [judged(int(n), semantic=6 if n == "33" else 9) for n in numbers]}
            return super().create(**kw)
    client = Chunks()
    r = judge_translation(ORIG, DUB, "en", "ko", client=client, lines=lines)
    assert len(client.prompts) == 2 and "[35]" in client.prompts[0] and "[1]" in client.prompts[1]   # all as context
    assert "<evaluate>21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35</evaluate>" in client.prompts[1]
    assert len(r["lines"]) == 35 and [i["line"] for i in r["issues"]] == [33] and r["issues"][0]["severity"] == "minor"


def test_wording_problems_misheard_lines_and_odd_answers():
    lines = [{"n": 1, "start": 0.0, "end": 2.0, "original": "new cases", "dub": "새로운 맛"},
             {"n": 2, "start": 2.0, "end": 3.0, "original": "Hello", "dub": "안녕"}]
    odd = judged(2, naturalness=5, error_type="made_up_type")
    odd["semantic_accuracy"] = 14
    answer = {"lines": [judged(1, semantic=3, misheard=True, error_type="distortion"), odd]}
    r = judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(answer), lines=lines)
    misheard, wording = r["issues"]
    assert misheard["may_be_recognition_error"] and misheard["severity"] == "major"
    assert wording["type"] == "wording" and wording["error_type"] == "other"
    assert wording["criterion"] == "linguistic_naturalness"
    assert r["lines"][1]["scores"]["semantic_accuracy"] == 10          # kept within 1-10


def test_a_failed_chunk_makes_the_whole_check_not_measured():
    lines = [{"n": i, "start": float(i), "end": i + 0.9, "original": "a", "dub": "b"} for i in range(1, 32)]
    replies = [json.dumps({"lines": [judged(i) for i in range(1, 31)]}), "not json"]

    class TwoReplies(FakeClient):
        def create(self, **kw):
            self.payload = replies.pop(0)
            return super().create(**kw)
    r = judge_translation(ORIG, DUB, "en", "ko", client=TwoReplies(), lines=lines)
    assert not r["measured"] and r["reason_key"] == "r.judge.unreadable"


def test_the_local_judge_writes_its_reasons_in_english_only():
    from dubeval.translation_judge import LOCAL_SCHEMA, LOCAL_SYSTEM_PROMPT
    line = LOCAL_SCHEMA["properties"]["lines"]["items"]["properties"]
    assert line["semantic_accuracy_reason"]["type"] == "string" and "four versions" not in LOCAL_SYSTEM_PROMPT
    assert "plain English" in LOCAL_SYSTEM_PROMPT


def test_missing_credentials_becomes_not_measured():
    r = judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(error=TypeError("Could not resolve authentication method")))
    assert not r["measured"] and "rejected the API key" in r["reason"] and r["reason_key"] == "r.judge.bad_key"
    assert count_issues(r, ("missing",)) is None


def test_network_error_refusal_and_bad_json_never_raise():
    assert "couldn't be reached" in judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(error=ConnectionError()))["reason"]
    assert "declined" in judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(GOOD, stop_reason="refusal"))["reason"]
    assert "cut off" in judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(GOOD, stop_reason="max_tokens"))["reason"]
    assert "couldn't be read" in judge_translation(ORIG, DUB, "en", "ko", client=FakeClient("not json"))["reason"]


def test_no_speech_skips_the_call():
    client = FakeClient(GOOD)
    r = judge_translation(ORIG, [], "en", "ko", client=client)
    assert not r["measured"] and client.request is None


# ---------------- Gemini ----------------
class FakeGemini:
    """A requests-like session answering generateContent with scripted (status, body) replies, in order."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        status, body = self.replies.pop(0) if self.replies else (503, {"error": {"message": "busy"}})
        return SimpleNamespace(status_code=status, json=lambda: body)


def gemini_ok(payload, model="gemini-3.5-flash"):
    """A successful generateContent response carrying payload as JSON text (with a thought part to skip)."""
    return 200, {"modelVersion": model, "candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"text": "thinking...", "thought": True}, {"text": json.dumps(payload)}]}}]}


@pytest.fixture
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_provider_prefers_gemini(monkeypatch):
    assert judge_provider() in (None, "claude")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert judge_provider() == "gemini"


def test_gemini_structured_request_and_result(gemini_key):
    s = FakeGemini(gemini_ok(GOOD))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["measured"] and r["meaning_score"] == 9.0 and r["model"] == "gemini-3.5-flash"
    call = s.calls[0]
    assert call["url"].endswith("/models/gemini-3.5-flash:generateContent")
    assert call["headers"] == {"x-goog-api-key": "test-key"}          # key in a header, never in the URL
    cfg = call["json"]["generationConfig"]
    assert cfg["responseMimeType"] == "application/json" and cfg["responseJsonSchema"]["required"]
    assert "Hi, I'm John from Uzbekistan. ->" in call["json"]["contents"][0]["parts"][0]["text"]


def asked(session):
    """The Gemini models a fake session was asked, in order."""
    return [c["url"].split("/models/")[1].split(":")[0] for c in session.calls]


def test_gemini_retries_overload_then_falls_back_to_next_model(gemini_key):
    busy = (503, {"error": {"message": "high demand"}})
    s = FakeGemini(busy, busy, gemini_ok(GOOD, "gemini-3.8-flash"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["measured"] and r["model"] == "gemini-3.8-flash" and r["fallback"]
    assert asked(s) == ["gemini-3.5-flash"] * 2 + ["gemini-3.8-flash"]


def test_the_gemini_chain_names_fixed_versions_only():
    # An alias such as gemini-flash-latest changes model under the same name, so scores would drift between runs.
    assert not [m for m in translation_judge.GEMINI_MODELS if "latest" in m]


def long_video(n=25):
    """n one-second lines on both sides, line by line: more than one request (CHUNK_LINES lines each)."""
    orig = [{"start": float(2 * i), "end": 2.0 * i + 1, "text": f"Line {i}."} for i in range(n)]
    dub = [{"start": float(2 * i), "end": 2.0 * i + 1, "text": f"대사 {i}."} for i in range(n)]
    lines = [{"n": i + 1, "start": o["start"], "end": o["end"], "original": o["text"], "dub": d["text"]}
             for i, (o, d) in enumerate(zip(orig, dub))]
    return orig, dub, lines


def test_one_dub_is_judged_by_one_model(gemini_key):
    # The first lines fell back to a backup model: the rest of the dub asks that model first, not the main one.
    busy = (503, {"error": {"message": "high demand"}})
    payload = {"lines": [judged(n) for n in range(1, 26)]}
    s = FakeGemini(busy, busy, gemini_ok(payload, "gemini-3.8-flash"), gemini_ok(payload, "gemini-3.8-flash"))
    orig, dub, lines = long_video()
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert r["measured"] and asked(s) == ["gemini-3.5-flash"] * 2 + ["gemini-3.8-flash"] * 2


def test_a_pinned_judge_never_falls_back(gemini_key, monkeypatch):
    monkeypatch.setenv("DUBEVAL_JUDGE_PIN", "1")
    busy = (503, {"error": {"message": "high demand"}})
    s = FakeGemini(busy, busy, gemini_ok(GOOD, "gemini-3.8-flash"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert not r["measured"] and r["reason_key"] == "r.judge.busy"
    assert asked(s) == ["gemini-3.5-flash"] * 2                                  # the backup was never asked


def test_pinning_changes_the_fingerprint(monkeypatch):
    before = translation_judge.judge_fingerprint("gemini")
    monkeypatch.setenv("DUBEVAL_JUDGE_PIN", "1")
    assert translation_judge.judge_fingerprint("gemini") != before          # a cached backup review isn't reused


def test_gemini_overloaded_everywhere_is_not_measured(gemini_key):
    r = judge_translation(ORIG, DUB, "en", "ko", session=FakeGemini(), sleep=lambda x: None)
    assert not r["measured"] and "busy right now" in r["reason"]


@pytest.mark.parametrize("reply, reason", [
    ((400, {"error": {"message": "API key not valid. Please pass a valid API key."}}), "rejected the API key"),
    ((403, {"error": {"message": "Permission denied"}}), "rejected the API key"),
    ((200, {"candidates": [{"finishReason": "SAFETY"}]}), "declined"),
    ((200, {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{"}]}}]}), "cut off"),
    ((200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "not json"}]}}]}), "couldn't be read"),
    (gemini_ok({"summary": "no lines"}), "Gemini's review couldn't be read"),
])
def test_gemini_failures_become_not_measured(gemini_key, reply, reason):
    r = judge_translation(ORIG, DUB, "en", "ko", session=FakeGemini(reply), sleep=lambda x: None)
    assert not r["measured"] and reason in r["reason"]


def test_no_key_at_all_is_not_measured(monkeypatch):
    monkeypatch.setattr(translation_judge, "claude_available", lambda: False)
    r = judge_translation(ORIG, DUB, "en", "ko")
    assert not r["measured"] and r["reason_key"] == "r.judge.no_key" and "API keys" in r["reason"]


def test_an_account_without_credit_says_so():
    class NoCredit(Exception):
        status_code = 400
        body = {"error": {"message": "Your credit balance is too low to access the Anthropic API."}}
    r = judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(error=NoCredit()))
    assert r["measured"] is False and r["reason_key"] == "r.judge.no_credit" and "credit" in r["reason"]


# ---------------- ChatGPT (OpenAI API) ----------------
def openai_ok(payload, model="gpt-5-mini-2026-01-01"):
    return 200, {"model": model, "choices": [{"finish_reason": "stop",
                                              "message": {"role": "assistant", "content": json.dumps(payload)}}]}


@pytest.fixture
def openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


def test_chatgpt_structured_request_and_result(openai_key):
    s = FakeGemini(openai_ok(GOOD))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None, provider="openai")
    assert r["measured"] and r["meaning_score"] == 9.0 and r["model"] == "gpt-5-mini-2026-01-01"
    call = s.calls[0]
    assert call["url"] == "https://api.openai.com/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer sk-test-key"             # the key in a header only
    fmt = call["json"]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert call["json"]["messages"][0]["role"] == "system" and "Hi, I'm John" in call["json"]["messages"][1]["content"]


def test_chatgpt_falls_back_when_a_model_isnt_available(openai_key):
    missing = (404, {"error": {"code": "model_not_found", "message": "no such model"}})
    s = FakeGemini(missing, openai_ok(GOOD, "gpt-5"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None, provider="openai")
    assert r["measured"] and [c["json"]["model"] for c in s.calls] == ["gpt-5-mini", "gpt-5"]


@pytest.mark.parametrize("reply, reason", [
    ((401, {"error": {"code": "invalid_api_key"}}), "r.judge.bad_key"),
    ((429, {"error": {"code": "insufficient_quota"}}), "r.judge.no_credit"),
    ((200, {"choices": [{"finish_reason": "stop", "message": {"refusal": "can't help"}}]}), "r.judge.declined"),
    ((200, {"choices": [{"finish_reason": "length", "message": {"content": "{"}}]}), "r.judge.cut_off"),
    ((200, {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]}), "r.judge.unreadable"),
])
def test_chatgpt_failures_become_not_measured(openai_key, reply, reason):
    r = judge_translation(ORIG, DUB, "en", "ko", session=FakeGemini(reply), sleep=lambda x: None, provider="openai")
    assert not r["measured"] and r["reason_key"] == reason and "ChatGPT" in r["reason"] + str(r["reason_params"])


def test_chatgpt_joins_the_automatic_order_after_gemini(monkeypatch):
    from dubeval import translation_judge as tj
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    assert tj.judge_provider() in ("claude", "openai") and "openai" in tj.available_judges()
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert tj.available_judges().index("gemini") < tj.available_judges().index("openai")


def test_a_slow_gemini_model_hands_over_to_the_next_at_once(gemini_key):
    import requests

    class SlowFirst(FakeGemini):
        def post(self, url, headers=None, json=None, timeout=None):
            if "gemini-3.5-flash" in url:
                self.calls.append({"url": url, "timeout": timeout})
                raise requests.ReadTimeout("no answer")
            return super().post(url, headers, json, timeout)
    s = SlowFirst(gemini_ok(GOOD, "gemini-3.8-flash"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["measured"] and r["model"] == "gemini-3.8-flash"
    assert sum("gemini-3.5-flash" in c["url"] for c in s.calls) == 1             # not retried
    assert s.calls[0]["timeout"] == translation_judge.GEMINI_TIMEOUT_SEC


def test_a_key_out_of_daily_requests_says_so(gemini_key):
    used_up = (429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota.",
                               "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})
    s = FakeGemini(*[used_up] * len(translation_judge.GEMINI_MODELS))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert not r["measured"] and r["reason_key"] == "r.judge.daily_quota" and "midnight" in r["reason"]
    assert len(s.calls) == len(dict.fromkeys(translation_judge.GEMINI_MODELS))    # each model asked once


# ---------------- every requested line must be evaluated ----------------
def test_lines_left_out_are_asked_about_again(gemini_key):
    orig, dub, lines = long_video(3)
    s = FakeGemini(gemini_ok({"lines": [judged(1)]}), gemini_ok({"lines": [judged(2), judged(3)]}))
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert r["measured"] and r["coverage"] == {"evaluated": 3, "total": 3}
    assert [ln["line"] for ln in r["lines"]] == [1, 2, 3]
    assert "<evaluate>2, 3</evaluate>" in json.dumps(s.calls[1]["json"])      # only the lines it left out


def partial_review():
    # 3 lines asked, 1 answered, twice: it used to be measured, 10/10, with the whole verdict Good.
    orig, dub, lines = long_video(3)
    only_one = gemini_ok({"lines": [judged(1, semantic=10, naturalness=10, context=10, terms=10, local=10)]})
    s = FakeGemini(only_one, only_one)
    return judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines), s


def test_a_partial_review_is_not_graded(gemini_key):
    r, s = partial_review()
    assert not r["measured"] and r["reason_key"] == "r.judge.incomplete" and r["meaning_score"] is None
    assert "1 of 3 lines" in r["reason"] and len(s.calls) == 2                # asked again once, no more


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_a_partial_review_withholds_the_meaning_grade_and_says_how_much_was_evaluated(gemini_key, lang):
    from dubeval.report import build_report
    from sample_results import make_results
    r, _ = partial_review()
    rep = build_report(make_results(translation_judge=r), lang)
    rows = {m["id"]: m for s in rep["sections"] for m in s["metrics"]}
    assert "meaning" not in rows and rows["translation_check"]["level"] == "not_measured"
    message = rows["translation_check"]["message"]
    assert "1" in message and "3" in message and "{" not in message
    assert rep["overall"]["level"] != "good" and "translation_unchecked" in rep["overall"]["unsure"]


def test_only_the_lines_a_request_asked_about_count(gemini_key):
    # An answer about a line nobody asked about doesn't fill the gap.
    orig, dub, lines = long_video(2)
    stray = gemini_ok({"lines": [judged(1), judged(7)]})
    r = judge_translation(orig, dub, "en", "ko", session=FakeGemini(stray, gemini_ok({"lines": [judged(7)]})),
                          sleep=lambda x: None, lines=lines)
    assert r["reason_key"] == "r.judge.incomplete" and r["reason_params"] == {"model": "gemini-3.5-flash", "done": "1", "total": "2"}
    # Nor does a line of another request: request 1 (lines 1-20) answering line 21 doesn't excuse request 2.
    orig, dub, lines = long_video(25)
    s = FakeGemini(gemini_ok({"lines": [judged(n) for n in range(1, 22)]}), gemini_ok({"lines": [judged(n) for n in range(22, 26)]}),
                   gemini_ok({"lines": [judged(21)]}))
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert r["measured"] and len(s.calls) == 3 and "<evaluate>21</evaluate>" in json.dumps(s.calls[2]["json"])


def test_a_failed_request_for_the_missing_lines_makes_the_check_not_measured(gemini_key):
    orig, dub, lines = long_video(2)
    s = FakeGemini(gemini_ok({"lines": [judged(1)]}))                         # then busy, for every retry
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert not r["measured"] and r["reason_key"] == "r.judge.busy"


# ---------------- which model judged what, and the lock ----------------
def test_every_chunk_keeps_the_model_that_judged_it(gemini_key):
    from dubeval.report import build_report
    from sample_results import make_results
    orig, dub, lines = long_video()
    payload = {"lines": [judged(n) for n in range(1, 26)]}
    s = FakeGemini(gemini_ok(payload, "model-a"), gemini_ok(payload, "model-b"))
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert r["models"] == ["model-a", "model-b"] and r["model"] == "model-a + model-b"
    assert [(c["model"], len(c["lines"]), c["requested"]) for c in r["chunks"]] == [
        ("model-a", 20, "gemini-3.5-flash"), ("model-b", 5, "gemini-3.5-flash")]
    rows = {m["id"]: m for sec in build_report(make_results(translation_judge=r), "en")["sections"] for m in sec["metrics"]}
    assert "model-a + model-b" in rows["translation_check"]["thresholds"]     # the report names both
    # One model: named once.
    s = FakeGemini(gemini_ok(payload, "model-a"), gemini_ok(payload, "model-a"))
    r = judge_translation(orig, dub, "en", "ko", session=s, sleep=lambda x: None, lines=lines)
    assert r["model"] == "model-a" and r["models"] == ["model-a"] and not r["fallback"]


def test_a_backup_chunk_is_marked_as_one(gemini_key):
    busy = (503, {"error": {"message": "high demand"}})
    s = FakeGemini(busy, busy, gemini_ok(GOOD, "gemini-3.8-flash"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["fallback"] and r["chunks"][0]["fallback"] and r["chunks"][0]["requested"] == "gemini-3.8-flash"


def test_a_locked_run_uses_only_the_first_model(gemini_key):
    busy = (503, {"error": {"message": "high demand"}})
    s = FakeGemini(busy, busy, gemini_ok(GOOD, "gemini-3.8-flash"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None, lock=True)
    assert not r["measured"] and r["reason_key"] == "r.judge.busy" and asked(s) == ["gemini-3.5-flash"] * 2


def test_the_lock_changes_the_fingerprint():
    assert translation_judge.judge_fingerprint("gemini", True) != translation_judge.judge_fingerprint("gemini")


def test_a_locked_claude_has_no_server_side_fallback():
    client = FakeClient(GOOD)
    assert judge_translation(ORIG, DUB, "en", "ko", client=client, lock=True)["measured"]
    assert "fallbacks" not in client.request and "betas" not in client.request


def test_a_claude_answer_from_its_fallback_model_is_marked():
    class ServedByFallback(FakeClient):
        def create(self, **kw):
            response = super().create(**kw)
            response.model = "claude-opus-4-8"
            response.usage = SimpleNamespace(iterations=[SimpleNamespace(type="message"), SimpleNamespace(type="fallback_message")])
            return response
    r = judge_translation(ORIG, DUB, "en", "ko", client=ServedByFallback(GOOD))
    assert r["fallback"] and r["model"] == "claude-opus-4-8" and r["chunks"][0]["requested"] == "claude-opus-5-5"
    assert not judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(GOOD))["fallback"]


def test_the_lock_reaches_the_judge_and_its_cache_key(monkeypatch):
    from dubeval import pipeline
    from sample_results import make_results
    seen = []
    monkeypatch.setattr(pipeline, "judge_translation", lambda *a, **k: seen.append(k) or {"measured": False})
    pipeline.check_translation(make_results(), {"judge": "gemini", "lock": True}, lambda *a, **k: None)
    pipeline.check_translation(make_results(), {"judge": None, "lock": True}, lambda *a, **k: None)
    pipeline.check_translation(make_results(), "gemini", lambda *a, **k: None)
    pipeline.check_translation(make_results(), True, lambda *a, **k: None)
    assert [(k["provider"], k["lock"]) for k in seen] == [("gemini", True), (None, True), ("gemini", False), (None, False)]


def test_the_lock_can_be_chosen_on_the_start_page_the_api_and_the_command_line(monkeypatch):
    from dubeval import api, cli, webapp
    body = lambda **k: webapp.EvaluationBody(dub="dub.mp4", **k)
    assert webapp._judge_choice(body(judge="gemini", lock_model=True)) == {"judge": "gemini", "lock": True}
    assert webapp._judge_choice(body(lock_model=True)) == {"judge": None, "lock": True}
    assert webapp._judge_choice(body(judge="gemini")) == "gemini" and webapp._judge_choice(body()) is True
    assert webapp._judge_choice(body(judge="off", lock_model=True)) is False
    request = api.ComparisonRequest(links=["a", "b"], lock_model=True)
    assert api._judge_choice(request) == {"judge": None, "lock": True}
    assert api._judge_choice(api.ComparisonRequest(links=["a", "b"])) is True
    assert api._judge_choice(api.ComparisonRequest(links=["a", "b"], lock_model=True, translation_check=False)) is False
    args = cli.parse_compare_args(["a", "b", "--lock-model"])
    assert args.lock_model and not cli.parse_compare_args(["a", "b"]).lock_model
    assert cli.parse_batch_args(["links.txt", "--lock-model"]).lock_model and cli.parse_args(["link", "--lock-model"]).lock_model
    evaluate = cli.parse_evaluate_args(["--original", "o.mp4", "--dub", "d.mp4", "--lock-model"])
    monkeypatch.delenv("DUBEVAL_JUDGE_PIN", raising=False)
    monkeypatch.setattr(cli, "_run_evaluate", lambda *a: 0)
    assert cli._run(evaluate, None) == 0 and translation_judge.judge_pinned()


# ---------------- the second listen ----------------
TWO_ORIG = [{"start": 0.0, "end": 2.0, "text": "Get the goal in the background."},
            {"start": 3.0, "end": 5.0, "text": "I'm the man who's keeping it."}]
TWO_DUB = [{"start": 0.0, "end": 2.0, "text": "대경 잡으려고."}, {"start": 3.0, "end": 5.0, "text": "나는 떠납니다."}]
TWO_LINES = [{"n": 1, "start": 0.0, "end": 2.0, "original": TWO_ORIG[0]["text"], "dub": TWO_DUB[0]["text"]},
             {"n": 2, "start": 3.0, "end": 5.0, "original": TWO_ORIG[1]["text"], "dub": TWO_DUB[1]["text"]}]
JUDGE_ARGS = (TWO_ORIG, TWO_DUB, "en", "ko")


def two_flagged():
    """A check with both lines marked down for meaning."""
    answer = {"lines": [judged(1, semantic=3, error_type="mistranslation", reason="Says something else."),
                        judged(2, semantic=2, error_type="mistranslation", reason="Says he is leaving.")]}
    return judge_translation(TWO_ORIG, TWO_DUB, "en", "ko", client=FakeClient(answer), lines=TWO_LINES)


def second(n, **scores):
    """One line's second judgement, as judge_again returns it."""
    return {**translation_judge._result({"lines": [judged(n, **scores)]}, "m", "claude")["lines"][0], "model": "m"}


def test_a_result_names_its_judge_and_the_lines_worth_a_second_listen():
    first = two_flagged()
    assert first["provider"] == "claude" and translation_judge.flagged(first) == [1, 2]
    assert translation_judge.flagged(judge_translation(ORIG, DUB, "en", "ko", client=FakeClient(GOOD))) == []


def test_the_judge_reads_only_the_changed_lines_again_with_their_new_words():
    first = two_flagged()
    now = [{**TWO_LINES[0], "dub": "배경 잡으려고."}, TWO_LINES[1]]
    client = FakeClient({"lines": [judged(1)]})
    again = translation_judge.judge_again(first, [1], *JUDGE_ARGS, lines=now, client=client)
    asked = client.request["messages"][0]["content"]
    assert "<evaluate>1</evaluate>" in asked and "배경 잡으려고." in asked and "나는 떠납니다." in asked
    assert again[1]["scores"]["semantic_accuracy"] == 9 and list(again) == [1]
    # A judge that fails, or leaves the line out, gives no second judgement at all.
    failing = FakeClient(error=RuntimeError("down"))
    assert translation_judge.judge_again(first, [1], *JUDGE_ARGS, lines=now, client=failing) is None
    skipped = FakeClient({"lines": [judged(2)]})
    assert translation_judge.judge_again(first, [1], *JUDGE_ARGS, lines=now, client=skipped) is None


def test_a_line_counts_only_if_it_reads_as_a_problem_both_times():
    first = two_flagged()
    heard = {1: {"original": TWO_ORIG[0]["text"], "dub": "배경 잡으려고.", "changed": True},
             2: {"original": TWO_ORIG[1]["text"], "dub": "나는 떠나요.", "changed": True}}
    again = {1: second(1), 2: second(2, semantic=3, reason="Still leaving.")}
    r = translation_judge.with_second_listen(first, TWO_LINES, heard, again, "faster-whisper:base")
    one, two = r["lines"]
    assert one["scores"]["semantic_accuracy"] == 9 and one["heard_again"]["used"]
    assert one["heard_again"]["first"]["scores"]["semantic_accuracy"] == 3 and one["heard_again"]["dub"] == "배경 잡으려고."
    assert two["scores"]["semantic_accuracy"] == 2 and not two["heard_again"]["used"]      # low both times: it stands
    assert [i["line"] for i in r["issues"]] == [2] and r["meaning_score"] == 5.5
    assert r["second_listen"] == {"measured": True, "heard": 2, "changed": 2, "cleared": 1,
                                  "recognizer": "faster-whisper:base"}
    assert first["meaning_score"] == 2.5 and "heard_again" not in first["lines"][0]         # the first result is untouched
    said = translation_judge.said(r, TWO_LINES)
    assert said[0]["dub"] == "배경 잡으려고." and said[1]["dub"] == "나는 떠납니다."


def test_a_second_reading_that_only_softens_a_problem_changes_nothing():
    first = two_flagged()
    heard = {1: {"original": TWO_ORIG[0]["text"], "dub": "배경 잡으려.", "changed": True}}
    r = translation_judge.with_second_listen(first, TWO_LINES, heard, {1: second(1, semantic=6, reason="Vague.")}, "x")
    assert r["lines"][0]["scores"]["semantic_accuracy"] == 3 and r["second_listen"]["cleared"] == 0
    # Heard the same both times: nothing to judge again, and the line stands.
    same = {1: {"original": TWO_ORIG[0]["text"], "dub": TWO_DUB[0]["text"], "changed": False}}
    r = translation_judge.with_second_listen(first, TWO_LINES, same, {}, "x")
    assert r["issues"] == first["issues"] and r["second_listen"]["changed"] == 0


def flagged_results():
    """Results whose check marked both lines down, as pipeline.check_translation leaves them."""
    from sample_results import make_results
    r = make_results()
    r["translation_judge"] = two_flagged()
    return r


def listen(results, audio="sound", cache=None, key="key"):
    """pipeline.listen_again on the two test lines."""
    from dubeval import pipeline
    pipeline.listen_again(results, audio, JUDGE_ARGS, TWO_LINES, None, None, False, lambda *a, **k: None, cache, key)
    return results["translation_judge"]


def test_flagged_lines_are_heard_again_only_when_asked_and_judged_on_the_new_words(monkeypatch):
    from dubeval import asr, pipeline
    calls = {"heard": 0, "judged": []}

    def hear(results, audio, lines, wanted, model):
        calls["heard"] += 1
        return {1: {"original": TWO_ORIG[0]["text"], "dub": "배경 잡으려고.", "changed": True},
                2: {"original": TWO_ORIG[1]["text"], "dub": TWO_DUB[1]["text"], "changed": False}}

    def again(first, numbers, *args, lines=None, **kw):
        calls["judged"].append((numbers, lines[0]["dub"]))
        return {1: second(1)}
    monkeypatch.setattr(pipeline, "hear_lines", hear)
    monkeypatch.setattr(translation_judge, "judge_again", again)
    monkeypatch.setattr(asr, "load_model", lambda name, cpu=False: (name, cpu))
    cache = {}
    assert "second_listen" not in listen(flagged_results(), cache=cache) and not calls["heard"]   # off unless asked for
    monkeypatch.setenv("DUBEVAL_SECOND_LISTEN", "base")
    tj = listen(flagged_results(), cache=cache)
    assert calls["judged"] == [([1], "배경 잡으려고.")]                    # only the line whose words changed
    assert tj["second_listen"]["cleared"] == 1 and len(tj["issues"]) == 1
    tj = listen(flagged_results(), cache=cache)                           # the same check again: from the cache
    assert calls["heard"] == 1 and tj["second_listen"]["cleared"] == 1
    # Without the sound, or switched off, the check stays as the judge gave it.
    assert "second_listen" not in listen(flagged_results(), audio=None, cache={})
    monkeypatch.setenv("DUBEVAL_SECOND_LISTEN", "off")
    assert "second_listen" not in listen(flagged_results()) and calls["heard"] == 1


def test_a_judge_that_fails_the_second_time_leaves_the_check_as_it_was(monkeypatch):
    from dubeval import asr, pipeline
    monkeypatch.setattr(pipeline, "hear_lines", lambda *a: {
        1: {"original": "x", "dub": "y", "changed": True}, 2: {"original": "x", "dub": "y", "changed": True}})
    monkeypatch.setattr(translation_judge, "judge_again", lambda *a, **k: None)
    monkeypatch.setattr(asr, "load_model", lambda name, cpu=False: name)
    monkeypatch.setenv("DUBEVAL_SECOND_LISTEN", "base")
    cache = {}
    tj = listen(flagged_results(), cache=cache)
    assert tj["second_listen"] == {"measured": False} and len(tj["issues"]) == 2
    assert cache == {}                                                    # asked again on the next run


def test_the_local_judge_keeps_the_graphics_card_while_lines_are_heard_again(monkeypatch):
    from dubeval import asr, pipeline
    loaded = []
    monkeypatch.setenv("DUBEVAL_SECOND_LISTEN", "base")
    monkeypatch.setattr(asr, "load_model", lambda name, cpu=False: loaded.append((name, cpu)))
    monkeypatch.setattr(pipeline, "hear_lines", lambda *a: {
        n: {"original": TWO_LINES[n - 1]["original"], "dub": TWO_LINES[n - 1]["dub"], "changed": False} for n in (1, 2)})
    for provider in ("ollama", "gemini"):
        r = flagged_results()
        r["translation_judge"]["provider"] = provider
        listen(r)
    assert loaded == [("base", True), ("base", False)]


def test_a_line_is_heard_again_on_its_own_and_music_alone_says_nothing(monkeypatch):
    import numpy as np
    from dubeval import asr, evaluate
    seen = []

    def transcribe(clip, model, language=None, check=None):
        seen.append((len(clip), language))
        return {"segments": [{"text": "배경 잡으려고.", "no_speech_prob": 0.1, "avg_logprob": -0.2},
                             {"text": "구독", "no_speech_prob": 0.9, "avg_logprob": -1.5}]}
    monkeypatch.setattr(evaluate, "transcribe", transcribe)
    monkeypatch.setattr(asr, "voice_activity", lambda clip, fine=False: [[0.1, 1.0]])
    y = np.zeros(10 * evaluate.SAMPLE_RATE, dtype=np.float32)
    assert evaluate.hear_again(y, 2.0, 4.0, "model", "ko") == "배경 잡으려고."      # the invented line is dropped
    assert seen == [(int((2.0 + 2 * evaluate.HEAR_AGAIN_PAD_SEC) * evaluate.SAMPLE_RATE), "ko")]
    monkeypatch.setattr(asr, "voice_activity", lambda clip, fine=False: [])
    assert evaluate.hear_again(y, 2.0, 4.0, "model", "ko") == "" and len(seen) == 1   # no voice: not even recognized


def test_both_sides_of_a_flagged_line_are_heard_again_and_silence_keeps_the_first_words(monkeypatch):
    import numpy as np
    from dubeval import evaluate, pipeline
    from sample_results import make_results
    heard = iter(["Get the goal in the background!", "배경 잡으려고.", "", ""])
    monkeypatch.setattr(evaluate, "hear_again", lambda y, start, end, model, language: next(heard))
    y = np.zeros(8 * evaluate.SAMPLE_RATE, dtype=np.float32)
    out = pipeline.hear_lines(make_results(), (y, y), TWO_LINES, [1, 2], "model")
    assert out[1] == {"original": "Get the goal in the background!", "dub": "배경 잡으려고.", "changed": True}
    assert out[2] == {"original": TWO_LINES[1]["original"], "dub": TWO_LINES[1]["dub"], "changed": False}


def cleared_results():
    """Results after a second listen cleared line 1 (heard as another word at first) and left line 2 standing."""
    r = flagged_results()
    heard = {1: {"original": TWO_ORIG[0]["text"], "dub": "배경 잡으려고.", "changed": True},
             2: {"original": TWO_ORIG[1]["text"], "dub": TWO_DUB[1]["text"], "changed": False}}
    r["translation_judge"] = translation_judge.with_second_listen(r["translation_judge"], TWO_LINES, heard,
                                                                  {1: second(1)}, "faster-whisper:base")
    return r


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_the_report_counts_a_cleared_line_apart_and_lists_it_as_possibly_misheard(lang):
    from dubeval.report import build_report
    rep = build_report(cleared_results(), lang)
    row = next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == "translation_check")
    assert row["level"] == "check" and row["parts"][0]["low"] == 1          # line 2 alone counts
    [listed] = rep["possible_asr_errors"]
    assert "대경 잡으려고." in listed["description"] and "배경 잡으려고." in listed["description"]
    assert listed["dubbed"] == "배경 잡으려고." and listed["doubt"] == "asr"
    assert all(i["dubbed"] != "배경 잡으려고." for i in rep["problem_intervals"])
    if lang == "en":
        assert "1 line was marked down at first but reads fine when heard again" in row["message"]
        assert "heard a second time" in row["thresholds"]


def test_a_check_without_a_second_listen_reads_as_before():
    from dubeval.report import build_report
    rep = build_report(flagged_results(), "en")
    row = next(m for s in rep["sections"] for m in s["metrics"] if m["id"] == "translation_check")
    assert "heard again" not in row["message"] and "second time" not in row["thresholds"]
    assert rep["possible_asr_errors"] == []


def test_a_line_that_looked_left_out_says_what_the_second_listen_heard():
    from dubeval.report import build_report
    r = flagged_results()
    lines = [TWO_LINES[0], {**TWO_LINES[1], "dub": ""}]
    heard = {2: {"original": TWO_ORIG[1]["text"], "dub": "내가 그걸 가질 사람이야.", "changed": True}}
    r["translation_judge"] = translation_judge.with_second_listen(r["translation_judge"], lines, heard, {2: second(2)}, "x")
    [listed] = build_report(r, "en")["possible_asr_errors"]
    assert listed["problem"].startswith("No dub speech was heard here at first") and "내가 그걸 가질 사람이야." in listed["problem"]
