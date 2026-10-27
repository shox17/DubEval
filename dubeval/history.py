"""History: every evaluation is recorded, so quality can be followed over time and across language pairs.

record() appends one JSON line per evaluated dub to data/history.jsonl (DUBEVAL_HISTORY overrides the path):
when, which link, languages, verdict, counts and every measure's level. summarize() turns the records into the
numbers the history views show: totals, the verdict mix per language pair, the most frequent problems, a weekly
trend and the latest evaluations. Reruns of the same link count once in the totals (the latest run wins); the
recent list shows every run.
"""
import json
import logging
import os
import threading
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from dubeval.paths import DATA_DIR
from dubeval.version import TOOL_VERSION

log = logging.getLogger(__name__)

HISTORY_FILE = Path(os.getenv("DUBEVAL_HISTORY") or DATA_DIR / "history.jsonl")
LEVELS = ("good", "check", "poor")
_lock = threading.Lock()


def history_file() -> Path:
    """Where the history lives (module attribute, so tests can redirect it)."""
    return Path(HISTORY_FILE)


def entry(results: dict, mode: str, when: Optional[str] = None) -> dict:
    """One history record for an evaluated dub (results with a built report)."""
    rep = results["report"]
    p, share = rep["project"], ((results.get("pipeline") or {}).get("input") or (results.get("pipeline") or {}).get("share") or {})
    tj = results.get("translation_judge") or {}
    counts = rep["overall"]["counts"]
    src, tgt = share.get("source_language_code") or "", p.get("target_language_code") or ""
    return {
        "time": when or time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool_version": TOOL_VERSION,
        "mode": mode,
        "link": p.get("share_url") or "",
        "seq": p.get("perso_seq"),
        "title": p.get("title") or "",
        "languages": f"{p.get('source_language') or '?'} → {p.get('target_language') or '?'}",
        "language_pair": f"{src or '?'}→{tgt or '?'}",
        "lipsync": p.get("is_lipsync"),
        "verdict": rep["overall"]["level"],
        "poor": counts["poor"],
        "check": counts["check"],
        "problem_seconds": rep.get("problem_seconds"),
        "meaning_score": tj.get("meaning_score") if tj.get("measured") else None,
        "meaning_scale": (tj.get("scale") or 5) if tj.get("measured") else None,
        "overlap_pct": (results.get("timing_alignment") or {}).get("overlap_pct"),
        "levels": {m["id"]: m["level"] for s in rep["sections"] for m in s["metrics"]},
        "report": ((results.get("pipeline") or {}).get("report_files") or {}).get("html"),
        # Files and links have no Perso project: the original and dub identify the dub, so reruns count once.
        "inputs": f"{share['original']}|{share['dub']}" if share.get("original") and share.get("dub") else "",
    }


def record(results: dict, mode: str) -> None:
    """Appends one evaluation to the history; a failure is logged, never raised (history must not sink a run)."""
    try:
        line = json.dumps(entry(results, mode), ensure_ascii=False)
        path = history_file()
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:  # disk full, permissions, an unexpected results shape
        log.warning("Could not record the evaluation in the history: %s", e)


def rename(report_path: str, title: str) -> None:
    """Gives every record of the run whose report is report_path a new title (the result was renamed); a failure is
    logged, never raised."""
    try:
        path = history_file()
        if not path.exists():
            return
        target = Path(report_path).resolve()
        with _lock:
            lines = path.read_text(encoding="utf-8").splitlines()
            out = []
            for line in lines:
                try:
                    rec = json.loads(line)
                    if isinstance(rec, dict) and rec.get("report") and Path(rec["report"]).resolve() == target:
                        rec["title"] = title
                        line = json.dumps(rec, ensure_ascii=False)
                except (json.JSONDecodeError, OSError, ValueError):
                    pass
                out.append(line)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
            os.replace(tmp, path)
    except Exception as e:
        log.warning("Could not rename the evaluation in the history: %s", e)


def load(path: Optional[Path] = None) -> list[dict]:
    """Every readable history record, oldest first (broken lines are skipped)."""
    path = path or history_file()
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if isinstance(rec, dict) and rec.get("verdict") in LEVELS:
                    out.append(rec)
            except json.JSONDecodeError:
                continue
    return out


def latest_per_link(records: list[dict]) -> list[dict]:
    """The latest record of each dub (by Perso project, else by link, else by original and dub), so reruns count once."""
    latest = {}
    for r in records:
        latest[r.get("seq") or r.get("link") or r.get("inputs") or id(r)] = r
    return list(latest.values())


def _week(stamp: str) -> str:
    """The Monday (YYYY-MM-DD) of the week a timestamp falls in."""
    d = datetime.strptime(stamp[:10], "%Y-%m-%d").date()
    return (d - timedelta(days=d.weekday())).isoformat()


def summarize(records: list[dict], days: Optional[int] = None, today: Optional[date] = None) -> dict:
    """Totals, per-language-pair verdict mix, the most frequent problems, a weekly trend and the recent runs."""
    if days is not None:
        since = ((today or date.today()) - timedelta(days=days)).isoformat()
        records = [r for r in records if r["time"][:10] >= since]
    unique = latest_per_link(records)
    verdicts = Counter(r["verdict"] for r in unique)
    pairs = defaultdict(list)
    for r in unique:
        pairs[r["language_pair"]].append(r)
    problems = Counter()
    for r in unique:
        for mid, level in (r.get("levels") or {}).items():
            if level in ("check", "poor"):
                problems[(mid, level)] += 1
    by_measure = defaultdict(lambda: {"check": 0, "poor": 0})
    for (mid, level), n in problems.items():
        by_measure[mid][level] += n
    weekly = defaultdict(Counter)
    for r in unique:
        weekly[_week(r["time"])][r["verdict"]] += 1
    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    return {
        "runs": len(records),
        "dubs": len(unique),
        "verdicts": {lv: verdicts.get(lv, 0) for lv in LEVELS},
        "good_pct": round(verdicts.get("good", 0) / len(unique) * 100, 1) if unique else None,
        "pairs": sorted(({"pair": k, "languages": v[-1]["languages"], "dubs": len(v),
                          **{lv: sum(1 for r in v if r["verdict"] == lv) for lv in LEVELS},
                          "overlap_pct": mean([r["overlap_pct"] for r in v if r.get("overlap_pct") is not None]),
                          # out of 10: the rubric scores 1-10, records made before it scored 1-5
                          "meaning_score": mean([r["meaning_score"] * 10 / (r.get("meaning_scale") or 5)
                                                 for r in v if r.get("meaning_score") is not None])}
                         for k, v in pairs.items()), key=lambda x: -x["dubs"]),
        "problems": sorted(({"measure": mid, **c, "dubs": c["check"] + c["poor"]} for mid, c in by_measure.items()),
                           key=lambda x: (-x["poor"], -x["dubs"], x["measure"])),
        "weekly": [{"week": w, **{lv: c.get(lv, 0) for lv in LEVELS}} for w, c in sorted(weekly.items())],
        "recent": list(reversed(records))[:20],
    }


def render_history_text(summary: dict, lang: str = "en", width: int = 100) -> str:
    """The history summary as plain text, in lang."""
    from dubeval.compare import pad, wrap
    from dubeval.i18n import t as i18n_t
    tr = lambda key, **p: i18n_t(key, lang, **p)
    bar, thin = "═" * width, "─" * width
    v = summary["verdicts"]
    lines = [bar, f" {tr('h.title').upper()}", bar]
    if not summary["dubs"]:
        return "\n".join(lines + [" " + tr("h.empty"), bar])
    lines += wrap(tr("h.totals", runs=summary["runs"], dubs=summary["dubs"], good=v["good"], check=v["check"],
                     poor=v["poor"], pct=f"{summary['good_pct']:.0f}"), width, " ")
    lines += [thin, f" {tr('h.pairs').upper()}"]
    lines.append("   " + pad(tr("h.pair"), 34) + "".join(pad(x, 14) for x in (
        tr("h.dubs"), tr("verdict.good"), tr("verdict.check"), tr("verdict.poor"), tr("h.timing"), tr("h.meaning"))))
    for p in summary["pairs"]:
        lines.append("   " + pad(p["languages"], 34) + "".join(pad(str(x), 14) for x in (
            p["dubs"], p["good"], p["check"], p["poor"],
            f"{p['overlap_pct']:.0f}%" if p["overlap_pct"] is not None else "—",
            f"{p['meaning_score']:.1f}/10" if p["meaning_score"] is not None else "—")))
    lines += [thin, f" {tr('h.problems').upper()}"]
    for x in summary["problems"][:10] or []:
        lines.append(f"   {pad(tr('r.m.' + x['measure']), 34)}{tr('h.problem_counts', poor=x['poor'], check=x['check'])}")
    if not summary["problems"]:
        lines.append("   " + tr("h.no_problems"))
    lines += [thin, f" {tr('h.weekly').upper()}"]
    for w in summary["weekly"]:
        total = w["good"] + w["check"] + w["poor"]
        lines.append(f"   {w['week']}  " + "█" * w["good"] + "▒" * w["check"] + "░" * w["poor"]
                     + f"  {tr('h.week_counts', good=w['good'], check=w['check'], poor=w['poor'], n=total)}")
    lines += [thin, f" {tr('h.recent').upper()}"]
    for r in summary["recent"]:
        lines += wrap(f"{r['time'][:16]}  {tr('verdict.' + r['verdict'])} · {r['title']} ({r['languages']}) · {r['mode']}",
                      width, "   ", "      ")
    lines.append(bar)
    return "\n".join(lines)
