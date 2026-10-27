"""Translation check: an LLM judge scores the dub's translation line by line against a rubric.

Each line gets five scores from 1 to 10 (meaning, naturalness, context, terminology, localization), each against
written score descriptions, a reason for every score of 7 or lower, an ideal translation and one error type. The judge
reads transcripts (and subtitle files when given), not audio, so a misheard word can look like a translation error;
the judge marks those, and the report keeps them apart. Long videos are judged CHUNK_LINES lines per request, with
every other line as context.

Judges, chosen by DUBEVAL_JUDGE (auto | claude | gemini | openai | ollama | off). "auto" takes the first one available:
Claude (ANTHROPIC_API_KEY or an `ant auth login` profile), then Gemini (GEMINI_API_KEY), then ChatGPT (OPENAI_API_KEY), then a local model through
Ollama (DUBEVAL_OLLAMA_URL, default http://127.0.0.1:11434, model DUBEVAL_OLLAMA_MODEL, default qwen3:8b), which
keeps everything on this computer. Every dub in a benchmark should be judged by the same judge; the report names
it. Without a judge, or on any failure, the result is "not measured" with the reason, never a failed run.
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Callable, Optional

import requests

log = logging.getLogger(__name__)

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Tried in order: each one is retried on overload (503) or rate limits (429), then the next model is used. Google's
# "high demand" errors are usually per model, so a longer chain keeps the check working during demand spikes.
GEMINI_MODELS = [os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), "gemini-flash-latest", "gemini-3.8-flash",
                 "gemini-3.1-flash-lite"]
GEMINI_THINKING = os.getenv("GEMINI_THINKING", "low")      # low ≈ 3 s per review, high ≈ 40 s
CLAUDE_MODEL = os.getenv("CLAUDE_JUDGE_MODEL", "claude-opus-5-5")
OPENAI_API = "https://api.openai.com/v1/chat/completions"
# Tried in order: a model the key can't use (404, model_not_found) hands over to the next.
OPENAI_MODELS = [os.getenv("DUBEVAL_OPENAI_MODEL", "gpt-5-mini"), "gpt-5", "gpt-4.1-mini"]
OLLAMA_URL = (os.getenv("DUBEVAL_OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("DUBEVAL_OLLAMA_MODEL", "qwen3:8b")
OLLAMA_TIMEOUT_SEC = int(os.getenv("DUBEVAL_OLLAMA_TIMEOUT", "600"))
JUDGES = ("claude", "gemini", "openai", "ollama")
DUB_TYPES = ("ai_clone", "ai_stock", "human")
MAX_ISSUES = 60
RETRYABLE = (429, 500, 502, 503, 504)
# How long one request may take before the next model is tried: a model that is overloaded can sit on a request for
# minutes (a 13-line answer normally takes under a minute), and waiting longer for it helps no one.
GEMINI_TIMEOUT_SEC = int(os.getenv("DUBEVAL_JUDGE_TIMEOUT", "120"))

# The translation rubric: five criteria, each line scored 1-10 against the descriptions below, a reason for every
# score of 7 or lower, an ideal translation and one error type per line.
CRITERIA = ("semantic_accuracy", "linguistic_naturalness", "contextual_consistency", "terminology_consistency",
            "localization_appropriateness")

SCORE_BANDS = {
    "semantic_accuracy": """
10 : The core meaning and nuances of the original text are perfectly conveyed. There are absolutely no omissions, distortions, or unnecessary additions.
9 : Overall very accurate, but some subtle nuances are slightly weakened or expressed too literally. There is no problem with comprehension.
8 : Mostly accurate, but a few words show minor omissions or slight distortions; still, the main ideas remain clear.
7 : Some parts feel awkward or show slight shifts in meaning, but the overall context is still understandable.
6 : Several areas have noticeable omissions or distortions, making the intended meaning unclear in parts. The viewer can generally understand, but it may cause confusion.
5 : Repeated omissions, distortions, or unnecessary additions make it difficult to grasp the main ideas without guessing from context.
4 : Many parts significantly misrepresent or omit the core meaning, causing key information to be lost. Viewers struggle to understand the original intent.
3 : Most sentences seriously misdeliver or mistranslate the intended meaning, making the overall message hard to follow.
2 : Almost all lines distort or omit the original meaning, resulting in a translation that differs greatly from the source. Viewers are very likely to misunderstand.
1 : The core meaning is barely conveyed; viewers cannot understand the original intent at all. This is essentially a failure to deliver meaning.""",
    "linguistic_naturalness": """
10 : Expressions are perfectly natural and fluent in the target language, sounding like authentic native speech with no awkwardness or translations.
9 : Overall very natural, but a few phrases could sound slightly more idiomatic; no significant awkwardness that affects comprehension.
8 : Mostly natural, but occasional awkward words or phrasing that sound a bit unnatural, though meaning is clear.
7 : Some awkward or literal-sounding expressions appear, making certain lines feel less smooth or less like native speech.
6 : Several awkward phrases or unnatural sentence structures are noticeable, affecting the flow and listener comfort.
5 : Frequent awkward or stilted expressions make the translation feel noticeably unnatural; understanding is possible but distracting.
4 : Many lines have awkward or non-idiomatic phrasing that interrupts the natural flow and makes comprehension more difficult.
3 : Most sentences sound unnatural or too literal, severely disrupting the viewing experience and making dialogue sound forced.
2 : Almost all lines are awkward or use unnatural constructions, making them hard to follow or uncomfortable to listen to.
1 : The translation reads or sounds extremely unnatural, almost robotic or nonsensical; it completely fails to resemble native language usage.""",
    "contextual_consistency": """
10 : Perfectly consistent with the preceding and following lines; fully aligned with the translation's flow and atmosphere without any jarring shifts.
9 : Almost entirely consistent; only minor wording could slightly improve flow, but it doesn't disrupt context or mood.
8 : Mostly consistent, but occasional slight mismatches with previous or following lines; overall coherence remains intact.
7 : Some noticeable inconsistencies with adjacent dialogue or the scene's tone, but they don't severely disrupt understanding.
6 : Several inconsistencies with context make the dialogue feel somewhat disconnected from the flow or mood of the translation.
5 : Frequent context mismatches or abrupt shifts in tone cause clear disruptions to the natural progression of the dialogue or scene.
4 : Many lines contradict or clash with preceding or following dialogue, making it difficult for viewers to follow the flow of the conversation.
3 : Most lines are inconsistent with the surrounding context or translation atmosphere, resulting in a disjointed or confusing experience.
2 : Almost all lines feel disconnected or out of place, severely disrupting the coherence and immersion of the video.
1 : The translation is almost entirely inconsistent with the surrounding context, creating a confusing and incoherent viewing experience.""",
    "terminology_consistency": """
10 : Terminology is perfectly consistent throughout each line; all key terms, technical words, proper nouns, and recurring phrases are translated uniformly without any discrepancies.
9 : Almost entirely consistent, with only minor or rare inconsistencies that do not affect understanding or coherence.
8 : Mostly consistent, but occasional small inconsistencies in less critical terms or phrases that slightly reduce uniformity.
7 : Some inconsistencies in key terms or recurring expressions appear, but they do not fundamentally disrupt comprehension.
6 : Several noticeable inconsistencies in important terminology cause slight confusion or lack of cohesion in the translation.
5 : Frequent inconsistencies in terminology make it harder to follow recurring concepts or recognize repeated elements.
4 : Many inconsistent translations of key terms or names disrupt the viewer's ability to clearly understand or track concepts.
3 : Most key terms and recurring expressions are inconsistently translated, significantly impairing understanding of concepts or storyline continuity.
2 : Almost all recurring terms are translated inconsistently, causing major confusion and undermining comprehension of important ideas.
1 : Terminology is almost entirely inconsistent, with different translations used for the same terms throughout, resulting in severe confusion and a lack of coherence.""",
    "localization_appropriateness": """
10 : Fully localized to the appropriate language register and context. Expressions are idiomatic, tone-appropriate, and sound fully native for the intended audience or use case (e.g., casual, formal, technical).
9 : Excellent adaptation to the language norms. Very minor stylistic or tonal adjustments could improve flow, but overall fits the context naturally and fluently.
8 : Mostly well localized, but with a few expressions that feel slightly generic, overly formal/informal, or not optimally suited to the context or audience.
7 : Some word choices or tone do not align fully with the intended context (e.g., inconsistent register, mildly awkward idioms), but do not significantly disrupt comprehension.
6 : Several expressions feel out of place linguistically (e.g., mix of formal/informal speech, overly literal translations, or tone mismatches). Some minor viewer discomfort or confusion may result.
5 : Inconsistent or unclear register throughout; lacks alignment with the situational tone (e.g., using honorifics inappropriately or misusing slang/technical terms). Requires revision to improve clarity and flow.
4 : Many lines show register confusion, awkward constructions, or inappropriate tone for the intended use. Target audience may find the language jarring or inappropriate.
3 : Widespread unnatural phrasing and tone mismatch severely reduce readability or audibility. The translation feels machine-like or detached from native usage.
2 : Most of the translation ignores audience expectations or situational language norms, creating noticeable barriers to understanding or immersion.
1 : The translation fails to align with the target language's natural usage entirely. Phrases are often unintelligible, jarring, or wildly inappropriate for the context.""",
}

# One error type per line: id, name and what it covers (as the judge reads them; the report shows r.tcat.<id>), and the
# issue kind DubEval files it under: meaning errors keep their own timeline categories, the rest is wording.
ERROR_TYPES = [
    ("omission", "최종 번역 단계 오류 누락", "원문의 의미를 생략. 의미 손실, 요약 누락 포함", "missing"),
    ("distortion", "최종 번역 단계 오류 의미 왜곡", "원문의 의미를 왜곡하여 전달. 의도 왜곡", "mistranslation"),
    ("context_misread", "문맥 파악 실패로 인한 의미 왜곡", "앞뒤 문맥 이해 부족으로 의미가 달라지거나 잘못 해석된 경우",
     "mistranslation"),
    ("invented", "임의 번역으로 인한 의미 왜곡", "원문에 없는 정보가 생겨 의미 왜곡이 생김", "added"),
    ("repetitive_style", "언어 구조 / 문체 반복 문제", "문장 구조나 어투가 반복되어 부자연스럽거나 어색한 경우", "wording"),
    ("wordiness", "Wordiness (장황함)", "불필요한 반복이나 군더더기 표현으로 문장이 길고 불필요함", "wording"),
    ("literal_order", "직번역 / 어순·문체 직번역", "원문 어순·문체를 그대로 옮겨 어색한 문장 생성", "wording"),
    ("word_for_word", "직역 / 단어단위 기계 번역 직역", "단어 단위로 기계적으로 대응한 번역 (예: \"make it\" → \"만들다\")",
     "mistranslation"),
    ("idiom", "비유 / 표현 해석 실패", "관용구, 은유적 표현을 직역하여 의미가 틀린 경우", "mistranslation"),
    ("formality", "문체 / 격식 수준 오류 (Formality)", "문체나 격식이 상황에 맞지 않음 (공손도, 경어체 혼용 등)", "wording"),
    ("tone_consistency", "문체 및 톤 일관성 오류 (Formality)",
     "동일 영상 내 톤·격식이 일관되지 않음 (예: \"하십시오\" vs \"하세요\")", "wording"),
    ("pronoun", "대명사 해석 오류", "it / this / that 등의 참조 대상이 잘못 해석되어 의미가 어긋남", "mistranslation"),
    ("possessive", "소유격 / 관계 해석 오류", "\"of\", \"'s\", \"their\" 등 관계나 소유 구조 해석 오류", "mistranslation"),
    ("gender_number", "성/수 (Gender/Number) 불일치",
     "성(gender) 또는 수(number) 일치가 깨져 같은 대상에서 형태가 어긋남 (예: 화자 성별에 따른 형용사 변형 미적용 "
     "'Encantado' vs 'Encantada', 단복수 일관성 깨짐 'cuerda' vs 'cuerdas')", "wording"),
    ("term_consistency", "단어 / 용어 일관성 오류", "동일 개념의 번역이 불일치함", "name_or_number"),
    ("technical_term", "전문 용어 사용 오류", "산업/기술/UI 용어를 잘못 번역하거나 불일치함", "name_or_number"),
    ("abbreviation", "줄임말·약어 오류",
     "원문의 줄임말·약어를 목표 언어에 없는 형태로 그대로 둠. 음성 합성 시 글자 단위로 읽혀 문제 발생", "wording"),
    ("culture", "현지 문화에 맞지 않는 표현", "대상 언어 화자에게 어색한 표현, 문화적 불일치", "wording"),
    ("dnt", "번역 불필요 항목 처리 오류 (DNT)", "번역 금지 항목(코드, 변수명, 브랜드명 등)을 번역하거나 수정함",
     "name_or_number"),
    ("segmentation", "세그먼트 분리 / 결합 문제", "문장이 비정상적으로 나누어지거나 결합되어 흐름 단절", "wording"),
    ("clause_structure", "구문·절 구조 오류",
     "절의 순서나 어순이 바뀌어 의미·논리 관계가 왜곡되거나 구문 구조가 부적절한 경우", "mistranslation"),
    ("lexical_choice", "어휘 선택 부적절 (Lexical Choice Issue)", "문맥상 어울리지 않는 단어 선택, 어휘 대체 필요", "wording"),
    ("other", "기타 ( 직접 확인 필요 )",
     "어느 정도 에러는 있으나 위 카테고리 어디에도 명확히 해당하지 않는 경우. 사람이 직접 확인 권장", "wording"),
    ("no_error", "명확한 에러 없음", "5개 기준 점수가 전반적으로 높고 이유도 깨끗하여 분류할 명확한 에러가 없음", None),
]
ERROR_KIND = {i: kind for i, _, _, kind in ERROR_TYPES}
CHUNK_LINES = 20                          # lines judged per request (about a minute); the rest go along as context
PARALLEL_REQUESTS = 3                     # a long video's requests, sent this many at a time

SYSTEM_PROMPT = """# Role
당신은 동영상에 대한 번역에 대한 성능을 측정하는 AI 에이전트 입니다. 사용자로부터 부가 정보(metadata)와 번역 문장쌍을 입력으로 받아서 번역 품질을 다차원적으로 평가하는 일을 수행합니다.
(단, 동영상에 대한 번역이기 때문에 metadata에 포함된 문맥을 고려한 번역을 수행해야 합니다.)

# Input
<target_language> : 번역 대상 언어
<content_description> : 동영상에 대한 전반적인 부분을 설명
<lines> : 동영상의 모든 번역 문장쌍 (번호, 시간, 원본 문장 -> 번역 문장). 평가하지 않는 줄도 앞뒤 문맥으로 사용
<evaluate> : 평가할 줄 번호

# **Criteria**
다음 5가지 차원에서 각각 1-10점 척도로 평가합니다:
1. 의미 전달 정확성 (semantic_accuracy)
   - 원문의 핵심 의미와 뉘앙스가 번역문에 얼마나 정확하게 전달되었는지 평가
   - 정보의 누락, 왜곡, 추가 여부를 종합적으로 판단
2. 언어적 자연성 (linguistic_naturalness)
   - 번역문이 해당 언어의 자연스러운 표현인지 평가
   - 번역투나 어색한 구문 사용 여부를 확인
3. 문맥적 일관성 (contextual_consistency)
   - 전후 문맥과의 연결성 및 일관성 평가
   - 동영상의 흐름과 분위기와의 조화 여부 확인
4. 용어 및 표현 일관성 (terminology_consistency)
   - 동일한 개념이나 용어가 일관되게 번역되었는지 평가
   - 전문 용어, 고유명사, 특정 표현의 통일성 확인
5. 현지화 적합성 (localization_appropriateness)
   - 번역문이 대상 언어 및 문화에 적합하게 현지화되었는지 평가
   - 문화적 맥락, 관용구, 사회적 규범 등을 적절히 반영했는지 확인

# 평가 프로세스 : <evaluate>의 각 줄에 대해 원본 문장과 번역 문장을 위의 5가지 평가 기준에 따라 각각 1-10점으로 평가합니다.
1. 각 평가 기준별로 세밀한 분석을 수행합니다.
2. 동영상 번역의 특성을 고려하여 구어체적 특성과 문맥적 연결성을 중점적으로 평가합니다.
3. <content_description>가 존재하면 참고하여 해당 동영상의 장르, 분위기, 대상 등을 고려한 적절성을 판단합니다.
4. 각 평가 기준에 대한 점수를 제시합니다.
5. 각 평가에서 7점 이하에 대해서는 평가 이유를 설명하시오.
  - 7점 이하는 이유를 무조건 설명해야함.
  - 8점 이상은 이유를 설명할 필요가 없기 때문에, 빈문자열을 출력할 것.
6. 7점 이하인 기준이 있으면, 모든 기준별로 점수가 만점이 되기 위한 이상적인 번역을 ideal_translation으로 제공해줘 (모두 8점 이상이면 빈문자열).
7. 아래 에러 유형 중 그 줄에 가장 적합한 것 1개를 error_type으로 선택. 점수가 모두 높고 이유도 깨끗하면 no_error.

# 에러 유형 (error_type)
""" + "\n".join(f"- {i}: {name} — {desc}" for i, name, desc, _ in ERROR_TYPES) + """

# Dubbing (this is a dubbed video)
- Both sides are what automatic speech recognition heard, not scripts: a word can be misheard (e.g. "cases" heard for
  "tastes"). When a low score could come from a misheard word rather than a translation error (the dub's word fits a
  similar-sounding original word, or the heard text makes no sense), set may_be_recognition_error to true. When a
  script or subtitle of a side is given, it is what that side was meant to say: trust it over the heard text.
- A side shown as "(nothing)": the dub left that speech out, or added speech the original doesn't have.
- Write every reason in plain language for a non-expert, one or two sentences, in four versions: English (en), Korean
  (ko), Brazilian Portuguese (pt) and Spanish (es); quotes stay in their own language. Empty strings (all four) when the
  score is 8 or higher.

# 출력은 json 포맷을 맞춰서 출력함"""

LANGS = ("en", "ko", "pt", "es")
MULTILINGUAL = {"type": "object", "properties": {lang: {"type": "string"} for lang in LANGS},
                "required": list(LANGS), "additionalProperties": False}


def _line_schema(reason: dict) -> dict:
    """One judged line: the five scores (each with its score descriptions), their reasons, the ideal translation, the
    error type and whether a low score may be a misheard word. reason is the JSON schema of one reason."""
    props = {"line": {"type": "integer", "description": "The line number"}}
    for c in CRITERIA:
        props[c] = {"type": "integer", "minimum": 1, "maximum": 10, "description": SCORE_BANDS[c].strip()}
        props[f"{c}_reason"] = {**reason, "description": "Specific reasons and basis for the score (empty when 8 or "
                                                         "higher)"}
    props["ideal_translation"] = {"type": "string",
                                  "description": "The ideal translation that would receive a perfect score for each "
                                                 "metric (empty when every score is 8 or higher)"}
    props["error_type"] = {"type": "string", "enum": [i for i, *_ in ERROR_TYPES]}
    props["may_be_recognition_error"] = {"type": "boolean"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


RESULT_SCHEMA = {
    "type": "object",
    "properties": {"lines": {"type": "array", "items": _line_schema(MULTILINGUAL),
                             "description": "One entry for every line in <evaluate>, in order"}},
    "required": ["lines"],
    "additionalProperties": False,
}


def gemini_key() -> Optional[str]:
    """The Gemini API key from the environment, or None."""
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip() or None


def openai_key() -> Optional[str]:
    """The OpenAI (ChatGPT) API key from the environment, or None."""
    return (os.getenv("OPENAI_API_KEY") or "").strip() or None


def claude_available() -> bool:
    """True when the anthropic package is installed and Claude credentials look configured."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    profile_dir = Path.home() / ".config" / "anthropic"
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or profile_dir.is_dir())


_ollama_seen: dict = {}                 # url -> (checked at, answer): the app asks on every page render


def ollama_url() -> Optional[str]:
    """Where the local judge runs: DUBEVAL_OLLAMA_URL when set; else DubEval's own Ollama (the local_judge pack,
    started on demand; None if it can't start); else a separately installed Ollama at the default address."""
    from dubeval import local_judge
    if os.getenv("DUBEVAL_OLLAMA_URL"):
        return OLLAMA_URL
    if local_judge.installed():
        return local_judge.ensure_running()
    return OLLAMA_URL


def ollama_available() -> bool:
    """True when the local judge can run: DubEval's own pack is installed (its Ollama starts when needed), or an Ollama
    answers and has the judge model (remembered for 30 s)."""
    from dubeval import local_judge
    if not os.getenv("DUBEVAL_OLLAMA_URL") and local_judge.installed():
        return True
    now = time.monotonic()
    seen = _ollama_seen.get(OLLAMA_URL)
    if seen and now - seen[0] < 30:
        return seen[1]
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=0.5)
        names = {m.get("name") for m in resp.json().get("models", [])} if resp.status_code == 200 else set()
        ok = OLLAMA_MODEL in names or f"{OLLAMA_MODEL}:latest" in names
    except (requests.RequestException, ValueError):
        ok = False
    _ollama_seen[OLLAMA_URL] = (now, ok)
    return ok


def judge_provider() -> Optional[str]:
    """Which judge the translation check will use: "claude", "gemini", "openai", "ollama", or None.

    DUBEVAL_JUDGE picks one (or "off"); "auto" (the default) takes the first available, in JUDGES order."""
    wanted = (os.getenv("DUBEVAL_JUDGE") or "auto").strip().lower()
    available = {"claude": claude_available, "gemini": lambda: bool(gemini_key()), "openai": lambda: bool(openai_key()),
                 "ollama": ollama_available}
    if wanted == "off":
        return None
    if wanted in available:
        return wanted if available[wanted]() else None
    return next((name for name in JUDGES if available[name]()), None)


def judge_configured() -> bool:
    """True when some provider is configured, so the translation check will run."""
    return judge_provider() is not None


def judge_fingerprint(provider: Optional[str] = None) -> str:
    """What decides the judge's answer besides the transcripts: provider (the named one, else the one DUBEVAL_JUDGE
    picks), models, thinking, prompt and schema. Changing any of them invalidates cached reviews."""
    return json.dumps([provider or judge_provider(), GEMINI_MODELS, GEMINI_THINKING, CLAUDE_MODEL, OPENAI_MODELS, OLLAMA_MODEL, SYSTEM_PROMPT,
                       RESULT_SCHEMA, DUB_TYPE_RULES, LOCAL_SYSTEM_PROMPT], sort_keys=True)


def not_measured(key: str, **params) -> dict:
    """The result when the translation couldn't be checked: a translatable reason key, plus the English text."""
    from dubeval.i18n import t
    params = {k: str(v) for k, v in params.items()}
    return {"measured": False, "reason": t(key, "en", **params), "reason_key": key, "reason_params": params,
            "model": None, "meaning_score": None, "summary": None, "issues": [], "lines": []}


DUB_TYPE_RULES = {
    "human": "This dub was recorded by human voice actors from an adapted script. Adapted jokes, idioms and cultural "
             "references are intended localization, not errors: score only changes that alter what a viewer "
             "understands as meaning errors.",
    "ai_clone": "This is an AI dub in a cloned voice. Hold it to a close translation: anything left out, added or "
                "changed is an issue.",
    "ai_stock": "This is an AI dub in a stock voice. Hold it to a close translation: anything left out, added or "
                "changed is an issue.",
}


def _whole(original_segments: list[dict], dubbed_segments: list[dict]) -> list[dict]:
    """Both transcripts as one line, when no line-by-line pairing is given."""
    def text(segs):
        return " ".join(s["text"].strip() for s in segs if s.get("text")).strip()
    ends = [s["end"] for s in original_segments + dubbed_segments if s.get("end") is not None]
    return [{"n": 1, "start": 0.0, "end": max(ends) if ends else 0.0,
             "original": text(original_segments), "dub": text(dubbed_segments)}]


def build_prompt(original_segments: list[dict], dubbed_segments: list[dict], source_lang: str, target_lang: str,
                 lines: Optional[list[dict]] = None, dub_type: Optional[str] = None,
                 description: Optional[str] = None, evaluate: Optional[list[int]] = None) -> str:
    """The user message: the video's metadata, every line (original -> dub, with scripts when given) and the numbers
    of the lines to judge (evaluate, default all). lines: pipeline.judge_lines; without them, both transcripts as one
    line."""
    lines = lines or _whole(original_segments, dubbed_segments)
    rule = DUB_TYPE_RULES.get(dub_type or "", "")
    about = " ".join(x for x in (f"Title: {description}." if description else "", rule) if x)
    rows = []
    for ln in lines:
        rows.append(f"[{ln['n']}] {ln['start']:.1f}-{ln['end']:.1f} s : {ln.get('original') or '(nothing)'} -> "
                    f"{ln.get('dub') or '(nothing)'}")
        for label, key in (("original script", "original_script"), ("dub script", "dub_script")):
            if ln.get(key):
                rows.append(f"    ({label}: {ln[key]})")
    numbers = evaluate if evaluate is not None else [ln["n"] for ln in lines]
    return (f"<metadata>\n    <source_language>{source_lang}</source_language>\n"
            f"    <target_language>{target_lang}</target_language>\n"
            f"    <content_description>{about}</content_description>\n</metadata>\n\n"
            "<lines>\n" + "\n".join(rows) + "\n</lines>\n\n"
            f"<evaluate>{', '.join(str(n) for n in numbers)}</evaluate>")


def judge_translation(original_segments: list[dict], dubbed_segments: list[dict], source_lang: str,
                      target_lang: str, client=None, session=None,
                      sleep: Callable[[float], None] = time.sleep, lines: Optional[list[dict]] = None,
                      dub_type: Optional[str] = None, provider: Optional[str] = None,
                      description: Optional[str] = None) -> dict:
    """Scores every line against the rubric with the chosen judge, CHUNK_LINES lines per request.

    lines: the speech line by line (pipeline.judge_lines); dub_type: ai_clone | ai_stock | human (human dubs may
    adapt freely); description: the video's title. client: an Anthropic client (forces Claude); session: a
    requests-like session (forces Gemini, or Ollama with provider="ollama"). Both are for tests. A request that fails
    makes the whole check "not measured", with its reason: half a translation check would mislead.
    """
    if not any(s.get("text") for s in original_segments) or not any(s.get("text") for s in dubbed_segments):
        return not_measured("r.judge.no_speech")
    lines = lines or _whole(original_segments, dubbed_segments)
    chunks = [[ln["n"] for ln in lines[i:i + CHUNK_LINES]] for i in range(0, len(lines), CHUNK_LINES)]
    prompts = [build_prompt(original_segments, dubbed_segments, source_lang, target_lang, lines, dub_type, description,
                            numbers) for numbers in chunks]
    if client is not None:
        return _rubric_result([_judge_claude(p, client) for p in prompts], lines)
    if provider or session is not None:
        return _rubric_result([_run_judge(provider or "gemini", p, session, sleep) for p in prompts], lines)
    chosen = judge_provider()
    if chosen is None:
        return not_measured("r.judge.no_key")
    parts = [_run_judge(chosen, prompts[0], None, sleep)]
    if (os.getenv("DUBEVAL_JUDGE") or "auto").strip().lower() == "auto":
        # In auto mode a judge whose key is rejected or whose account has no credit hands over to the next one.
        for nxt in available_judges()[available_judges().index(chosen) + 1:]:
            if parts[0].get("reason_key") not in ACCOUNT_PROBLEMS:
                break
            log.info("Translation judge %s unusable (%s); trying %s", chosen, parts[0].get("reason_key"), nxt)
            chosen, parts = nxt, [_run_judge(nxt, prompts[0], None, sleep)]
    if parts[0].get("measured") and len(prompts) > 1:
        # The rest of a long video at once, a few requests at a time: the wait is about one request, not all of them.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(PARALLEL_REQUESTS) as pool:
            parts += list(pool.map(lambda p: _run_judge(chosen, p, None, sleep), prompts[1:]))
    return _rubric_result(parts, lines)


def _rubric_result(parts: list[dict], lines: list[dict]) -> dict:
    """One result from the judged chunks: every line's scores, the averages, and an issue for every line with a score
    at or below report.RUBRIC_FLAG (major when its meaning score is at or below report.RUBRIC_POOR). The first failed
    chunk's result is returned as it is."""
    from dubeval.report import RUBRIC_FLAG, RUBRIC_POOR
    failed = next((p for p in parts if not p.get("measured")), None)
    if failed is not None:
        return failed
    by_n = {ln["n"]: ln for ln in lines}
    judged = {j["line"]: j for p in parts for j in p["lines"] if j["line"] in by_n}
    if not judged:
        return not_measured("r.judge.unreadable", model=parts[0].get("model") or "")
    out_lines, issues = [], []
    for n, ln in by_n.items():
        j = judged.get(n)
        if j is None:
            continue
        out_lines.append({**j, "start": ln["start"], "end": ln["end"]})
        low = [c for c in CRITERIA if j["scores"][c] <= RUBRIC_FLAG]
        if not low:
            continue
        worst = "semantic_accuracy" if "semantic_accuracy" in low else min(low, key=lambda c: j["scores"][c])
        kind = ERROR_KIND.get(j["error_type"]) or ("mistranslation" if worst == "semantic_accuracy" else "wording")
        issues.append({"type": kind,
                       "severity": "major" if j["scores"]["semantic_accuracy"] <= RUBRIC_POOR else "minor",
                       "line": n, "start_sec": ln["start"], "original": ln.get("original") or "",
                       "dubbed": ln.get("dub") or "", "explanation": j["reasons"][worst],
                       "may_be_recognition_error": j["may_be_recognition_error"], "criterion": worst,
                       "score": j["scores"][worst], "error_type": j["error_type"],
                       "ideal_translation": j["ideal_translation"]})
    issues.sort(key=lambda i: (i["severity"] != "major", i["start_sec"]))

    def mean(c):
        return round(sum(j["scores"][c] for j in out_lines) / len(out_lines), 1)
    return {"measured": True, "reason": "", "reason_key": None, "reason_params": {}, "model": parts[0]["model"],
            "rubric": 1, "scale": 10, "meaning_score": mean("semantic_accuracy"),
            "criteria": {c: mean(c) for c in CRITERIA}, "summary": None, "lines": out_lines,
            "issues": issues[:MAX_ISSUES]}


ACCOUNT_PROBLEMS = ("r.judge.bad_key", "r.judge.no_credit")


def available_judges() -> list[str]:
    """Every judge that looks usable now, in JUDGES order."""
    checks = {"claude": claude_available, "gemini": lambda: bool(gemini_key()), "openai": lambda: bool(openai_key()),
              "ollama": ollama_available}
    return [name for name in JUDGES if checks[name]()]


def _run_judge(provider: str, prompt: str, session, sleep: Callable[[float], None]) -> dict:
    """One review by the named judge."""
    if provider == "gemini":
        return _judge_gemini(prompt, session or requests.Session(), sleep)
    if provider == "claude":
        return _judge_claude(prompt, None)
    if provider == "openai":
        return _judge_openai(prompt, session or requests.Session(), sleep)
    if provider == "ollama":
        return _judge_ollama(prompt, session or requests.Session())
    return not_measured("r.judge.no_key")


def _result(data: dict, model: str, provider: str) -> dict:
    """One request's judged lines from the model's JSON (scores kept within 1-10, reasons in four languages), or not
    measured if the JSON is incomplete."""
    try:
        lines = []
        for j in data["lines"]:
            error_type = j.get("error_type") if j.get("error_type") in ERROR_KIND else "other"
            lines.append({"line": int(j["line"]),
                          "scores": {c: min(10, max(1, int(j[c]))) for c in CRITERIA},
                          "reasons": {c: _as_langs(j.get(f"{c}_reason") or "") for c in CRITERIA},
                          "ideal_translation": str(j.get("ideal_translation") or ""),
                          "error_type": error_type,
                          "may_be_recognition_error": bool(j.get("may_be_recognition_error"))})
        return {"measured": True, "reason": "", "reason_key": None, "reason_params": {}, "model": model, "lines": lines}
    except (KeyError, TypeError, ValueError):
        return not_measured("r.judge.unreadable", model=provider)


def _as_langs(value) -> dict:
    """A {lang: text} dict from the model's multilingual field (or a plain string, used for every language)."""
    if isinstance(value, dict):
        return {lang: str(value.get(lang) or value.get("en") or "") for lang in LANGS}
    return {lang: str(value) for lang in LANGS}


def _judge_gemini(prompt: str, session, sleep: Callable[[float], None]) -> dict:
    """One Gemini review with structured JSON output; retries overload and rate limits, then tries fallbacks."""
    key = gemini_key() or ""
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": RESULT_SCHEMA,
                             "temperature": 0, "thinkingConfig": {"thinkingLevel": GEMINI_THINKING}},
    }
    busy = out_of_quota = False
    for model in dict.fromkeys(GEMINI_MODELS):
        for attempt in range(2):
            try:
                resp = session.post(GEMINI_API.format(model=model), headers={"x-goog-api-key": key},
                                    json=body, timeout=GEMINI_TIMEOUT_SEC)
            except requests.Timeout:
                log.warning("Gemini (%s) took longer than %s s; trying the next model", model, GEMINI_TIMEOUT_SEC)
                busy = True
                break                                        # an overloaded model: the next one is faster than a retry
            except requests.RequestException as e:
                log.warning("Gemini request failed: %s", e.__class__.__name__)
                busy = True
                sleep(2 ** attempt)
                continue
            if resp.status_code == 429 and _daily_quota_used(resp):
                out_of_quota = True                          # this model's free requests for today: try the next one
                break
            if resp.status_code in RETRYABLE:
                busy = True
                sleep(2 * (attempt + 1))
                continue
            if resp.status_code == 404:
                break                                        # model not available to this key: try the next one
            if resp.status_code in (400, 401, 403):
                try:
                    msg = resp.json().get("error", {}).get("message", "")
                except ValueError:
                    msg = ""
                if resp.status_code != 400 or "key" in msg.lower():
                    return not_measured("r.judge.bad_key", model="Gemini")
                log.warning("Gemini rejected the request: %s", msg[:200])
                return not_measured("r.judge.error", model="Gemini")
            if resp.status_code != 200:
                return not_measured("r.judge.error", model="Gemini")
            data = resp.json()
            candidate = (data.get("candidates") or [{}])[0]
            finish = candidate.get("finishReason")
            if finish in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST") or not candidate.get("content"):
                return not_measured("r.judge.declined", model="Gemini")
            if finish == "MAX_TOKENS":
                return not_measured("r.judge.cut_off", model="Gemini")
            text = "".join(p.get("text", "") for p in candidate["content"].get("parts", []) if not p.get("thought"))
            try:
                return _result(json.loads(text), data.get("modelVersion") or model, "Gemini")
            except json.JSONDecodeError:
                return not_measured("r.judge.unreadable", model="Gemini")
    if out_of_quota and not busy:
        return not_measured("r.judge.daily_quota", model="Gemini")
    if busy:
        return not_measured("r.judge.busy", model="Gemini")
    return not_measured("r.judge.error", model="Gemini")


def _daily_quota_used(resp) -> bool:
    """Whether a 429 says a daily request quota is used up (free keys allow a few dozen requests a day per model),
    rather than a short burst limit worth retrying."""
    try:
        text = json.dumps(resp.json())
    except ValueError:
        return False
    return "PerDay" in text


def _judge_openai(prompt: str, session, sleep: Callable[[float], None]) -> dict:
    """One ChatGPT review (OpenAI API) with strict structured JSON output; retries overload, then tries fallbacks.

    The key goes only in the Authorization header. An account without credit (429 insufficient_quota) is reported
    as such, so auto mode can hand over to the next judge."""
    headers = {"Authorization": f"Bearer {openai_key() or ''}", "Content-Type": "application/json"}
    busy = False
    for model in dict.fromkeys(OPENAI_MODELS):
        body = {"model": model,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "dub_review", "strict": True, "schema": RESULT_SCHEMA}}}
        for attempt in range(2):
            try:
                resp = session.post(OPENAI_API, headers=headers, json=body, timeout=180)
            except requests.RequestException as e:
                log.warning("ChatGPT request failed: %s", e.__class__.__name__)
                busy = True
                sleep(2 ** attempt)
                continue
            try:
                error = (resp.json() or {}).get("error") or {}
            except ValueError:
                error = {}
            code = error.get("code") or error.get("type") or ""
            if resp.status_code == 401:
                return not_measured("r.judge.bad_key", model="ChatGPT")
            if resp.status_code == 429 and code == "insufficient_quota":
                return not_measured("r.judge.no_credit", model="ChatGPT")
            if resp.status_code in RETRYABLE:
                busy = True
                sleep(2 * (attempt + 1))
                continue
            if resp.status_code == 404 or code == "model_not_found":
                break                                        # model not available to this key: try the next one
            if resp.status_code != 200:
                log.warning("ChatGPT rejected the request: %s", str(error.get("message", ""))[:200])
                return not_measured("r.judge.error", model="ChatGPT")
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            if message.get("refusal") or choice.get("finish_reason") == "content_filter":
                return not_measured("r.judge.declined", model="ChatGPT")
            if choice.get("finish_reason") == "length":
                return not_measured("r.judge.cut_off", model="ChatGPT")
            try:
                return _result(json.loads(message.get("content") or ""), data.get("model") or model, "ChatGPT")
            except json.JSONDecodeError:
                return not_measured("r.judge.unreadable", model="ChatGPT")
    if busy:
        return not_measured("r.judge.busy", model="ChatGPT")
    return not_measured("r.judge.error", model="ChatGPT")


def _judge_claude(prompt: str, client) -> dict:
    """One Claude review with structured JSON output and server-side refusal fallback."""
    if client is None:
        try:
            import anthropic
        except ImportError:
            return not_measured("r.judge.no_key")
        client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:  # network, auth or API errors must not sink the whole evaluation
        name = e.__class__.__name__
        # No credentials at all is a TypeError from the SDK; a rejected key is a 401/403.
        if isinstance(e, TypeError) or getattr(e, "status_code", None) in (401, 403):
            log.info("Translation judge has no usable Claude credentials (%s)", name)
            return not_measured("r.judge.bad_key", model="Claude")
        body = getattr(e, "body", None)
        message = str(((body or {}).get("error") or {}).get("message", "")) if isinstance(body, dict) else ""
        if getattr(e, "status_code", None) == 400 and "credit" in message.lower():
            log.warning("Translation judge: the Claude account has no credit left")
            return not_measured("r.judge.no_credit", model="Claude")
        log.warning("Translation judge failed: %s", name)
        return not_measured("r.judge.unreachable", model="Claude")

    if response.stop_reason == "refusal":
        return not_measured("r.judge.declined", model="Claude")
    if response.stop_reason == "max_tokens":
        return not_measured("r.judge.cut_off", model="Claude")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return _result(json.loads(text), getattr(response, "model", CLAUDE_MODEL), "Claude")
    except json.JSONDecodeError:
        return not_measured("r.judge.unreadable", model="Claude")


def _english_only(schema: dict) -> dict:
    """RESULT_SCHEMA with every reason as one English string instead of four languages."""
    out = json.loads(json.dumps(schema))
    out["properties"]["lines"]["items"] = _line_schema({"type": "string"})
    return out


LOCAL_SCHEMA = _english_only(RESULT_SCHEMA)
# A local model writes about 40 tokens a second on a laptop GPU: four languages per reason took over 10 minutes for a
# 1.5-minute video, English only takes under a minute. Reports show its reasons in English.
_FOUR_LANGUAGES = SYSTEM_PROMPT[SYSTEM_PROMPT.index("- Write every reason"):SYSTEM_PROMPT.index("\n\n# 출력")]
LOCAL_SYSTEM_PROMPT = SYSTEM_PROMPT.replace(_FOUR_LANGUAGES, "- Write every reason in plain English for a "
                                            "non-expert, one sentence; an empty string when the score is 8 or higher.")


def _judge_ollama(prompt: str, session) -> dict:
    """One review by a local model through Ollama, with the JSON schema as its output format; nothing leaves this
    computer. It answers in English only (LOCAL_SCHEMA), which is several times faster."""
    # The context is sized to the prompt (about 3 characters a token) plus room for the answer: a fixed large
    # context wastes GPU memory, and a model that doesn't fit the GPU runs partly on the CPU, many times slower.
    num_ctx = int(min(32768, max(4096, (len(LOCAL_SYSTEM_PROMPT) + len(prompt)) / 3 + 4096)))
    body = {"model": OLLAMA_MODEL, "stream": False, "think": False, "format": LOCAL_SCHEMA,
            "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": LOCAL_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]}
    url = None
    try:
        url = ollama_url()
        if url is None:
            return not_measured("r.judge.local_down", model=OLLAMA_MODEL, url="DubEval (logs/ollama.log)")
        resp = session.post(f"{url}/api/chat", json=body, timeout=OLLAMA_TIMEOUT_SEC)
    except requests.Timeout:
        log.warning("Local judge took longer than %s s", OLLAMA_TIMEOUT_SEC)
        return not_measured("r.judge.local_slow", model=OLLAMA_MODEL, sec=OLLAMA_TIMEOUT_SEC)
    except requests.RequestException as e:
        log.warning("Local judge request failed: %s", e.__class__.__name__)
        return not_measured("r.judge.local_down", model=OLLAMA_MODEL, url=url)
    if resp.status_code == 404:
        return not_measured("r.judge.no_local_model", model=OLLAMA_MODEL)
    if resp.status_code != 200:
        return not_measured("r.judge.error", model=f"Ollama ({OLLAMA_MODEL})")
    data = resp.json()
    if data.get("done_reason") == "length":
        return not_measured("r.judge.cut_off", model=OLLAMA_MODEL)
    try:
        return _result(json.loads((data.get("message") or {}).get("content") or ""), f"{OLLAMA_MODEL} (local)",
                       OLLAMA_MODEL)
    except json.JSONDecodeError:
        return not_measured("r.judge.unreadable", model=OLLAMA_MODEL)


def count_issues(result: dict, kinds: tuple[str, ...], severity: Optional[str] = None) -> Optional[int]:
    """How many issues of the given types (and severity) the judge found; None if it didn't run."""
    if not result.get("measured"):
        return None
    return sum(1 for i in result["issues"] if i["type"] in kinds and (severity is None or i["severity"] == severity))
