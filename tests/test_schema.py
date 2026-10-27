"""The report file format: report.json follows the versioned schema, and the published schema file is current."""
import json
from pathlib import Path

import pydantic
import pytest

from dubeval import pipeline, schema
from dubeval.report import build_report
from dubeval.version import TOOL_VERSION
from sample_results import make_results

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schemas" / "report.schema.json"


def test_saved_report_follows_the_format(tmp_path):
    r = make_results()
    r["report"] = build_report(r, "ko")
    files = pipeline.save_report_files(r, tmp_path)
    data = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert data["format"] == "dubeval-report" and data["format_version"] == schema.FORMAT_VERSION
    assert data["tool_version"] == TOOL_VERSION and "report" not in data["results"]
    parsed = schema.validate(data)
    assert parsed.report.overall.level in ("good", "check", "poor") and parsed.report.lang == "ko"


@pytest.mark.parametrize("lang", ["en", "ko", "pt", "es"])
def test_reports_in_every_language_fit_the_format(lang):
    r = make_results(timing_alignment={"overlap_pct": 40.0})
    schema.validate(schema.wrap(build_report(r, lang), r, TOOL_VERSION))


def test_a_broken_report_is_rejected():
    r = make_results()
    data = schema.wrap(build_report(r, "en"), r, TOOL_VERSION)
    data["report"]["overall"]["level"] = "excellent"
    with pytest.raises(pydantic.ValidationError):
        schema.validate(data)


def test_extra_fields_are_allowed():
    r = make_results()
    data = schema.wrap(build_report(r, "en"), r, TOOL_VERSION)
    data["report"]["something_new"] = 1
    assert schema.validate(data).report.model_extra["something_new"] == 1


def test_published_schema_file_is_current():
    """schemas/report.schema.json is what tools read; regenerate it with `python qa.py schema` after a change."""
    assert SCHEMA_FILE.read_text(encoding="utf-8") == schema.json_schema_text()
