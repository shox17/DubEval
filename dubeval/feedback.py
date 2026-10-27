"""Reviewer feedback: people mark each problem interval as a real problem or a false alarm.

Votes are appended to data/feedback.jsonl (DUBEVAL_FEEDBACK overrides); the latest vote on an interval wins, so a
reviewer can change their mind. summarize() tells, per check, how many flagged intervals reviewers confirmed and how
many were false alarms: the evidence for loosening or tightening that check's thresholds.
"""
import json
import logging
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from dubeval.paths import DATA_DIR
from dubeval.version import TOOL_VERSION

log = logging.getLogger(__name__)

FEEDBACK_FILE = Path(os.getenv("DUBEVAL_FEEDBACK") or DATA_DIR / "feedback.jsonl")
VOTES = ("real", "false_alarm")
MIN_VOTES = 3                        # a check needs this many votes before the summary calls it noisy or reliable
NOISY_PCT = 50.0                     # at least this share of false alarms: the check flags too much
_lock = threading.Lock()


def feedback_file() -> Path:
    """Where votes live (module attribute, so tests can redirect it)."""
    return Path(FEEDBACK_FILE)


def interval_key(project: dict, interval: dict) -> str:
    """A stable id for one problem interval of one dub: link, category and time range."""
    link = project.get("perso_seq") or project.get("share_url") or project.get("title") or "?"
    return f"{link}|{interval['category']}|{interval['start']:.1f}|{interval['end']:.1f}"


def vote(project: dict, interval: dict, verdict: str, reviewer: str = "") -> dict:
    """Records a reviewer's vote on a problem interval and returns the stored entry."""
    if verdict not in VOTES:
        raise ValueError(f"A vote is one of {VOTES}.")
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "tool_version": TOOL_VERSION,
             "key": interval_key(project, interval), "link": project.get("share_url") or "",
             "seq": project.get("perso_seq"), "title": project.get("title") or "",
             "category": interval["category"], "check": interval.get("check"), "severity": interval.get("severity"),
             "start": interval["start"], "end": interval["end"], "vote": verdict, "reviewer": reviewer}
    with _lock:
        path = feedback_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load(path: Optional[Path] = None) -> list[dict]:
    """Every readable vote, oldest first."""
    path = path or feedback_file()
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if isinstance(e, dict) and e.get("vote") in VOTES and e.get("key"):
                    out.append(e)
            except json.JSONDecodeError:
                continue
    return out


def latest(votes: Optional[list[dict]] = None) -> dict:
    """The current vote per interval key (the latest one wins)."""
    current = {}
    for e in votes if votes is not None else load():
        current[e["key"]] = e
    return current


def summarize(votes: list[dict]) -> dict:
    """Per check: confirmed problems, false alarms, the confirmed share, and whether it looks noisy."""
    per = defaultdict(lambda: {"real": 0, "false_alarm": 0})
    current = latest(votes)
    for e in current.values():
        per[e.get("check") or e["category"]][e["vote"]] += 1
    checks = []
    for check, c in per.items():
        n = c["real"] + c["false_alarm"]
        checks.append({"check": check, "real": c["real"], "false_alarm": c["false_alarm"], "votes": n,
                       "confirmed_pct": round(c["real"] / n * 100, 1),
                       "status": ("few" if n < MIN_VOTES else
                                  "noisy" if c["false_alarm"] / n * 100 >= NOISY_PCT else "reliable")})
    total = len(current)
    real = sum(1 for e in current.values() if e["vote"] == "real")
    return {"intervals": total, "real": real, "false_alarm": total - real,
            "confirmed_pct": round(real / total * 100, 1) if total else None,
            "checks": sorted(checks, key=lambda x: (-x["false_alarm"], -x["votes"], x["check"]))}


def render_feedback_text(summary: dict, lang: str = "en", width: int = 100) -> str:
    """The feedback summary as plain text, in lang."""
    from dubeval.compare import pad, wrap
    from dubeval.i18n import t as i18n_t
    tr = lambda key, **p: i18n_t(key, lang, **p)
    bar, thin = "═" * width, "─" * width
    lines = [bar, f" {tr('f.title').upper()}", bar]
    if not summary["intervals"]:
        return "\n".join(lines + wrap(tr("f.empty"), width, " ") + [bar])
    lines += wrap(tr("f.totals", n=summary["intervals"], real=summary["real"], false=summary["false_alarm"],
                     pct=f"{summary['confirmed_pct']:.0f}"), width, " ")
    lines.append(thin)
    lines.append("   " + pad(tr("f.check"), 30) + "".join(pad(x, 16) for x in (tr("f.real"), tr("f.false"), tr("f.confirmed"))))
    for c in summary["checks"]:
        lines.append("   " + pad(tr("r.m." + c["check"]), 30) + "".join(pad(str(x), 16) for x in (
            c["real"], c["false_alarm"], f"{c['confirmed_pct']:.0f}%")) + tr(f"f.status.{c['status']}"))
    lines.append(bar)
    return "\n".join(lines)
