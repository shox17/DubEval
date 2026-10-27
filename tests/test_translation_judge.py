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


def test_gemini_retries_overload_then_falls_back_to_next_model(gemini_key):
    busy = (503, {"error": {"message": "high demand"}})
    s = FakeGemini(busy, busy, gemini_ok(GOOD, "gemini-flash-latest"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["measured"] and r["model"] == "gemini-flash-latest"
    assert [c["url"].split("/models/")[1].split(":")[0] for c in s.calls] == \
        ["gemini-3.5-flash"] * 2 + ["gemini-flash-latest"]


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
    s = SlowFirst(gemini_ok(GOOD, "gemini-flash-latest"))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert r["measured"] and r["model"] == "gemini-flash-latest"
    assert sum("gemini-3.5-flash" in c["url"] for c in s.calls) == 1             # not retried
    assert s.calls[0]["timeout"] == translation_judge.GEMINI_TIMEOUT_SEC


def test_a_key_out_of_daily_requests_says_so(gemini_key):
    used_up = (429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota.",
                               "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})
    s = FakeGemini(*[used_up] * len(translation_judge.GEMINI_MODELS))
    r = judge_translation(ORIG, DUB, "en", "ko", session=s, sleep=lambda x: None)
    assert not r["measured"] and r["reason_key"] == "r.judge.daily_quota" and "midnight" in r["reason"]
    assert len(s.calls) == len(dict.fromkeys(translation_judge.GEMINI_MODELS))    # each model asked once
