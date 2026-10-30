"""The report file format: what every report.json contains, as Pydantic models and a JSON Schema.

report.json is DubEval's contract with other tools (PersoDub, the desktop app, scripts), so it is versioned:
FORMAT_VERSION goes up whenever a field is renamed or removed, or its meaning changes. Adding a field doesn't need a
new version, so the models allow extra fields. `python qa.py schema` prints the JSON Schema; the copy in
schemas/report.schema.json must match it (tests/test_schema.py checks).
"""
import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FORMAT = "dubeval-report"
FORMAT_VERSION = 1

Level = Literal["good", "check", "poor", "info", "not_measured"]
Verdict = Literal["good", "check", "poor"]


class _Model(BaseModel):
    """Every model accepts fields it doesn't list, so adding a field never breaks a reader."""
    model_config = ConfigDict(extra="allow")


class Metric(_Model):
    """One measure: its level, the value behind it, and plain explanations."""
    id: str
    label: str
    level: Level
    value: object = Field(None, description="The measured number or flag; null when not measured")
    display: Optional[str] = Field(None, description="The value as shown to a person")
    message: str = Field(description="What was found, what it means for a viewer, what to do")
    thresholds: Optional[str] = Field(None, description="How the level is graded")


class Section(_Model):
    """A group of measures (timing and audio, speech, alignment, translation, file, lip movement)."""
    id: str
    title: str
    metrics: list[Metric]
    note: Optional[str] = None


class Interval(_Model):
    """A problem as a time range of the video, in seconds."""
    start: float
    end: float
    category: str
    category_label: str
    severity: Literal["check", "poor"]
    check: str = Field(description="The measure that found it")
    check_label: str
    description: str
    merged: int = Field(1, description="How many findings were merged into this range")
    dub: Optional[str] = Field(None, description="Which dub (A, B, ...) in a comparison")


class Counts(_Model):
    """How many measures got each level."""
    good: int
    check: int
    poor: int
    not_measured: int


class Overall(_Model):
    """The verdict: any Poor → poor; otherwise any Check → check; otherwise good."""
    level: Verdict
    label: str
    headline: str
    counts: Counts


class Project(_Model):
    """What was evaluated."""
    title: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    target_language_code: Optional[str] = None
    duration_sec: Optional[float] = None
    timestamp: Optional[str] = None
    whisper_model: Optional[str] = None
    share_url: Optional[str] = Field(None, description="The Perso share link, when the input was one")
    perso_seq: Optional[int] = None
    is_lipsync: Optional[bool] = None
    evaluated_video: Optional[str] = None
    dub_id: Optional[str] = Field(None, description="A dub given as a file: its path, hashed (reviewer votes use it)")


class NotMeasured(_Model):
    """A measure that couldn't be taken, and why."""
    id: str
    label: str
    reason: str


class Report(_Model):
    """The report: verdict, every measure, every problem interval, in one interface language."""
    report_version: int
    lang: Literal["en", "ko", "pt", "es"]
    project: Project
    overall: Overall
    sections: list[Section]
    problem_intervals: list[Interval]
    possible_asr_errors: list[dict] = Field(description="Issues that are probably misheard words, not dub errors")
    problem_seconds: float = Field(description="Seconds of the video covered by problem intervals")
    things_to_check: list[dict]
    not_measured: list[NotMeasured]
    method: dict


class ReportFile(_Model):
    """The whole report.json: the report plus the raw measurements it was built from."""
    format: Literal["dubeval-report"]
    format_version: int = Field(description="Goes up when a field is renamed or removed")
    tool_version: str
    report: Report
    results: dict = Field(description="The raw measurements (see docs/architecture.md, results schema)")


def wrap(report: dict, results: dict, tool_version: str) -> dict:
    """The report.json content for a report and the results it was built from."""
    return {"format": FORMAT, "format_version": FORMAT_VERSION, "tool_version": tool_version,
            "report": report, "results": results}


def validate(data: dict) -> ReportFile:
    """Checks a report.json's content against the format; raises pydantic.ValidationError when it doesn't fit."""
    return ReportFile.model_validate(data)


def json_schema() -> dict:
    """The JSON Schema of report.json."""
    schema = ReportFile.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = f"DubEval report (format {FORMAT_VERSION})"
    return schema


def json_schema_text() -> str:
    """The JSON Schema as stable, readable text (the content of schemas/report.schema.json)."""
    return json.dumps(json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
