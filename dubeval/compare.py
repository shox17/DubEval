"""Compare mode: dubs of the same video (2 to 8), one recommendation, and why.

build_ranking([results...], lang) builds every dub's report, ranks the dubs with the decision rule (rank), and
returns everything the comparison files show: the recommended version, problem intervals per dub, the
reasoning and the full ranking, a side-by-side table of every check, each link's metadata and measurement notes.
build_comparison(results_a, results_b) is the two-dub case. Dubs are labelled A, B, C, ... in input order. Rendering is in
render_comparison_text / render_comparison_html. Pure: no file writes, no network.
"""
import html
import time
import unicodedata
from typing import Callable, Optional

from dubeval.i18n import DEFAULT_UI_LANGUAGE, t as i18n_t
from dubeval.report import ICONS, build_report, _CSS
from dubeval.version import TOOL_VERSION

Tr = Callable[..., str]
DUBS = ("A", "B")                 # the two-dub case; N dubs are labelled from LABELS
LABELS = "ABCDEFGH"
MAX_DUBS = len(LABELS)
VERDICT_RANK = {"good": 0, "check": 1, "poor": 2}
SAME_VIDEO_PCT = 5.0              # originals differing in length by more than this may be different videos
# The checks a dub must be measured on before its verdict can be compared: they read the dub's recognized speech, so
# when recognition fails (a less common language heard as another one) they aren't graded and the verdict looks
# better than the dub may be. Rule 1 keeps such a dub from beating one that was measured.
KEY_CHECKS = ("speech_overlap", "line_length", "clarity")
# The decision rule, in order: (rule id, fact compared, which value is better). The first rule whose values differ
# decides; a rule is skipped when either dub has no value for it (for example, the translation wasn't checked).
# What makes DubEval unsure of a dub (report.sure_of) that also makes its place in the ranking unsure: when the dub
# ranked first has one, the comparison holds its recommendation and says what to check (the order still shows).
HOLD_FOR = {"little_speech": "speech", "short_speech": "speech", "unclear_speech": "speech",
            "words_unchecked": "translation", "translation_unchecked": "translation"}
RULES = (
    ("measured", "unmeasured", "lower"),
    ("verdict", "verdict_rank", "lower"),
    ("poor_items", "poor", "lower"),
    ("check_items", "check", "lower"),
    ("problem_seconds", "problem_seconds", "lower"),
    ("meaning_score", "meaning_score", "higher"),
    ("speech_timing", "overlap_pct", "higher"),
)


def facts(rep: dict, r: dict) -> dict:
    """The values the decision rule compares, from one dub's report and results."""
    tj = r.get("translation_judge") or {}
    overlap = (r.get("timing_alignment") or {}).get("overlap_pct")
    level = rep["overall"]["level"]
    rows = {m["id"]: m for s in rep["sections"] for m in s["metrics"]}
    missing = [k for k in KEY_CHECKS if k in rows and rows[k]["level"] == "not_measured"]
    return {
        "unmeasured": len(missing),
        "unmeasured_checks": missing,
        "verdict": level,
        "verdict_rank": VERDICT_RANK[level],
        "poor": rep["overall"]["counts"]["poor"],
        "check": rep["overall"]["counts"]["check"],
        "problem_seconds": round(float(rep.get("problem_seconds") or 0.0), 1),
        "meaning_score": tj.get("meaning_score") if tj.get("measured") else None,
        "meaning_scale": tj.get("scale") or 5,
        "overlap_pct": round(float(overlap), 1) if overlap is not None else None,
    }


def rank(facts_by_dub: dict) -> dict:
    """Ranks dubs with the decision rule: the order, the winner, the rule separating it from the runner-up.

    A rule is skipped when any dub has no value for it. Dubs are sorted by the remaining rules in order (the first
    rule that separates two dubs decides between them); dubs still tied keep their input order (A before B before
    C), and the result says the top two are tied.
    """
    labels = list(facts_by_dub)
    used = [(n, r, k, b) for n, (r, k, b) in enumerate(RULES, 1) if all(facts_by_dub[d].get(k) is not None for d in labels)]
    skipped = [r for r, k, _ in RULES if any(facts_by_dub[d].get(k) is None for d in labels)]
    key = lambda d: tuple(facts_by_dub[d][k] if b == "lower" else -facts_by_dub[d][k] for _, _, k, b in used)
    order = sorted(labels, key=lambda d: (key(d), labels.index(d)))
    winner, runner = order[0], order[1]
    for n, r, k, _ in used:
        if facts_by_dub[winner][k] != facts_by_dub[runner][k]:
            return {"order": order, "winner": winner, "runner_up": runner, "tie": False, "rule": r, "rule_number": n,
                    "values": {d: facts_by_dub[d][k] for d in labels}, "skipped": skipped}
    return {"order": order, "winner": winner, "runner_up": runner, "tie": True, "rule": None, "rule_number": None,
            "values": None, "skipped": skipped}


def decide(a: dict, b: dict) -> dict:
    """The decision rule for two dubs (see rank): winner, tie, the deciding rule and the values for A and B."""
    r = rank({"A": a, "B": b})
    return {k: r[k] for k in ("winner", "tie", "rule", "rule_number", "values", "skipped")}


def _shown(tr: Tr, rule: str, f: dict) -> str:
    """A dub's value at a rule, as people read it."""
    key = dict((r, k) for r, k, _ in RULES)[rule]
    value = f[key]
    if value is None:
        return "—"
    if rule == "measured":
        return tr("c.shown.unmeasured", n=value, total=len(KEY_CHECKS))
    if rule == "verdict":
        return tr(f"verdict.{f['verdict']}")
    if rule == "problem_seconds":
        return f"{value:.1f} s"
    if rule == "meaning_score":
        return f"{value} / {f.get('meaning_scale', 5)}"
    if rule == "speech_timing":
        return f"{value:.1f}%"
    return str(value)


def _problems(rep: dict, limit: int = 3) -> list[str]:
    """A dub's worst measures with their level, Poor first: 'Speech timing (Check)'."""
    rows = [m for s in rep["sections"] for m in s["metrics"]]
    return [f"{m['label']} ({rep['badges'][lv]})" for lv in ("poor", "check") for m in rows if m["level"] == lv][:limit]


def _fix_first(rep: dict, limit: int = 5) -> list[str]:
    """What to fix first in a Poor dub: its Poor measures, then its Poor problem intervals."""
    rows = [f"{m['label']}: {m['message']}" for s in rep["sections"] for m in s["metrics"] if m["level"] == "poor"]
    rows += [f"{i['start']:.1f}s-{i['end']:.1f}s {i['category_label']}: {i['description']}"
             for i in rep["problem_intervals"] if i["severity"] == "poor"]
    return rows[:limit]


def _table(reps: dict) -> list[dict]:
    """Every check of every report side by side, in report order (A's order, then rows only later dubs have)."""
    order, rows = [], {}
    for dub in reps:
        for s in reps[dub]["sections"]:
            for m in s["metrics"]:
                if m["id"] not in rows:
                    order.append(m["id"])
                    rows[m["id"]] = {"id": m["id"], "section": s["title"], "label": m["label"], **{d: None for d in reps}}
                rows[m["id"]][dub] = {"level": m["level"], "display": m["display"],
                                      "badge": reps[dub]["badges"][m["level"]]}
    return [rows[i] for i in order]


def _link(tr: Tr, rep: dict) -> dict:
    """One link's metadata for the comparison."""
    p = rep["project"]
    lip = p.get("is_lipsync")
    return {"title": p.get("title"), "languages": f"{p.get('source_language') or '?'} → {p.get('target_language') or '?'}",
            "length": f"{p['duration_sec']:.1f} s" if p.get("duration_sec") else "—",
            "lipsync": "—" if lip is None else tr("c.yes" if lip else "c.no"),
            "project": f"#{p['perso_seq']}" if p.get("perso_seq") else "—",
            "evaluated": p.get("evaluated_video") or "—", "link": p.get("share_url") or "—"}


def _notes(tr: Tr, reps: dict, res: dict, no_translation: list[str]) -> list[str]:
    """What wasn't measured and why, plus warnings about the set of links itself."""
    notes = []
    for dub in reps:
        items = reps[dub]["not_measured"]
        if items:
            notes.append(tr("c.note.not_measured", dub=dub, items="; ".join(f"{x['label']}: {x['reason']}" for x in items)))
    if no_translation:
        notes.append(tr("c.no_translation", dubs=", ".join(tr("c.dub", d=d) for d in no_translation)))
    seqs = [reps[d]["project"].get("perso_seq") for d in reps]
    if any(seqs) and len({s for s in seqs if s}) < len([s for s in seqs if s]):
        notes.append(tr("c.note.same_project"))
    lengths = [(res[d].get("acoustic_metrics") or {}).get("original_duration_sec") for d in reps]
    lengths = [x for x in lengths if x]
    if lengths and (max(lengths) - min(lengths)) / max(lengths) * 100 > SAME_VIDEO_PCT:
        notes.append(tr("c.note.other_video", a=f"{min(lengths):.1f}", b=f"{max(lengths):.1f}"))
    languages = {reps[d]["project"].get("target_language_code") or "": reps[d]["project"].get("target_language") or "?"
                 for d in reps}
    if len(languages) > 1:
        names = list(languages.values())
        notes.append(tr("c.note.other_language", a=", ".join(names[:-1]), b=names[-1]))
    return notes or [tr("c.note.none")]


def build_comparison(results_a: dict, results_b: dict, lang: str = DEFAULT_UI_LANGUAGE,
                     run_seconds: Optional[float] = None) -> dict:
    """The two-dub comparison (see build_ranking)."""
    return build_ranking([results_a, results_b], lang, run_seconds)


def build_ranking(results: list[dict], lang: str = DEFAULT_UI_LANGUAGE, run_seconds: Optional[float] = None) -> dict:
    """Every dub's report, the recommendation with its reasoning and the ranking, and everything the comparison
    files show, in lang. Dubs are labelled A, B, C, ... in input order (2 to MAX_DUBS)."""
    if not 2 <= len(results) <= MAX_DUBS:
        raise ValueError(f"Compare between 2 and {MAX_DUBS} dubs.")
    tr: Tr = lambda key, **p: i18n_t(key, lang, **p)
    dubs = list(LABELS[:len(results)])
    res = dict(zip(dubs, results))
    reps = {dub: build_report(res[dub], lang, dub=dub) for dub in dubs}
    f = {dub: facts(reps[dub], res[dub]) for dub in dubs}
    dec = rank(f)
    win, lose = dec["winner"], dec["runner_up"]
    all_poor = all(f[d]["verdict"] == "poor" for d in dubs)
    no_translation = [dub for dub in dubs if f[dub]["meaning_score"] is None]

    if dec["tie"]:
        why = tr("c.why.tie", d=win, other=lose)
    else:
        why = tr(f"c.why.{dec['rule']}", win=win, lose=lose, win_value=_shown(tr, dec["rule"], f[win]),
                 lose_value=_shown(tr, dec["rule"], f[lose]))
    other = _problems(reps[lose])
    summary = [why, tr("c.loser_problems", dub=lose, items=", ".join(other)) if other else tr("c.loser_clean", dub=lose),
               tr(f"c.ready.{f[win]['verdict']}", dub=win)]
    values = ({dub: _shown(tr, dec["rule"], f[dub]) for dub in dubs} if dec["rule"] else
              {dub: tr(f"verdict.{f[dub]['verdict']}") for dub in dubs})
    ranking = [{"rank": i, "dub": d, "title": reps[d]["project"].get("title"), "verdict": f[d]["verdict"],
                "verdict_label": tr(f"verdict.{f[d]['verdict']}"), "poor": f[d]["poor"], "check": f[d]["check"],
                "problem_seconds": f[d]["problem_seconds"]} for i, d in enumerate(dec["order"], 1)]
    not_ready = (tr("c.not_ready", d=win) if len(dubs) == 2 else tr("c.not_ready_all", d=win)) if all_poor else None
    # Every dub may lack the same key checks (rule 1 then can't separate them): the recommendation still says so.
    caution = tr("c.caution.unmeasured", d=win, items=", ".join(tr(f"r.m.{k}") for k in f[win]["unmeasured_checks"])) \
        if f[win]["unmeasured"] else None
    held = list(dict.fromkeys(HOLD_FOR[k] for k in reps[win]["overall"].get("unsure", []) if k in HOLD_FOR))
    if held:
        headline = tr("c.held", d=win, why=" ".join(tr(f"c.held.{k}", d=win) for k in held))
    else:
        headline = tr("c.recommend_tie", d=win, other=lose) if dec["tie"] else tr("c.recommend", d=win)
    return {
        "comparison_version": 2,
        "lang": lang,
        "dubs": dubs,
        "recommendation": {
            "dub": win, "tie": dec["tie"], "both_poor": all_poor, "all_poor": all_poor, "ready": not all_poor,
            "title": reps[win]["project"].get("title"), "verdict": f[win]["verdict"],
            "verdict_label": tr(f"verdict.{f[win]['verdict']}"),
            "headline": headline, "held": held,
            "warning": not_ready,
            "caution": caution,
            "fix_first": _fix_first(reps[win]) if all_poor else [],
        },
        "ranking": ranking,
        "intervals": {dub: reps[dub]["problem_intervals"] for dub in dubs},
        "possible_asr_errors": {dub: reps[dub]["possible_asr_errors"] for dub in dubs},
        "problem_seconds": {dub: f[dub]["problem_seconds"] for dub in dubs},
        "reasoning": {
            "rule": dec["rule"] or "tie", "rule_number": dec["rule_number"],
            "rule_label": tr(f"c.rule.{dec['rule'] or 'tie'}"),
            "values": values, "deciding_factor": why, "summary": summary,
            "skipped_rules": [tr(f"c.rule.{r}") for r in dec["skipped"]],
            "translation_used": not no_translation,
            "translation_note": (tr("c.no_translation", dubs=", ".join(tr("c.dub", d=d) for d in no_translation))
                                 if no_translation else tr("c.translation_used")),
            "rules_order": tr("c.rules_order"),
        },
        "facts": f,
        "decision": dec,
        "table": _table(reps),
        "links": {dub: _link(tr, reps[dub]) for dub in dubs},
        "notes": _notes(tr, reps, res, no_translation),
        "meta": {"tool_version": TOOL_VERSION, "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "run_seconds": round(run_seconds, 1) if run_seconds is not None else None},
        "labels": {k: tr(f"c.{k}") for k in (
            "title", "sec.recommended", "sec.intervals", "sec.reasoning", "sec.table", "sec.links", "sec.notes",
            "rule_label", "values_label", "summary_label", "fix_first", "asr", "no_intervals", "table.check",
            "verdict", "open_report", "meta.title", "meta.languages", "meta.length", "meta.lipsync", "meta.project",
            "meta.evaluated", "meta.link", "skipped", "ranking_label")}
                  | {f"dub_{d}": tr("c.dub", d=d) for d in dubs} | {f"count_{d}": _count(tr, reps[d]) for d in dubs}
                  | {"footer": tr("c.footer", version=TOOL_VERSION,
                                  sec=f"{run_seconds:.0f}" if run_seconds is not None else "—",
                                  time=time.strftime("%Y-%m-%d %H:%M:%S"))},
        "badges": reps["A"]["badges"],
        "reports": reps,
    }


def _count(tr: Tr, rep: dict) -> str:
    """'3 problem intervals, 7.5 s in total' for one dub."""
    n = len(rep["problem_intervals"])
    return tr(f"c.intervals_count_{'one' if n == 1 else 'many'}", n=n, sec=f"{rep['problem_seconds']:.1f}")


def interval_line(i: dict, lb: dict, badges: dict) -> str:
    """One problem interval as a line: '12.4s-15.1s | Dub B | missing speech | Poor | Translation check | ...'."""
    dub = lb.get(f"dub_{i.get('dub')}", "") if i.get("dub") else ""
    parts = [f"{i['start']:.1f}s-{i['end']:.1f}s"] + ([dub] if dub else []) + [
        i["category_label"], badges.get(i["severity"], i["severity"]), i["check_label"], i["description"]]
    return " | ".join(parts)


# ---------------- renderers ----------------
def text_width(text: str) -> int:
    """Columns text takes in a terminal: Hangul, CJK and emoji count double."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 if ch == "\ufe0f" else
               0 if unicodedata.combining(ch) else 1 for ch in text)


def pad(text: str, width: int) -> str:
    """text padded with spaces to width terminal columns."""
    return text + " " * max(0, width - text_width(text))


def wrap(text: str, width: int, first: str, rest: str = "") -> list[str]:
    """Word-wraps text to width terminal columns (Korean-aware); long words such as URLs are never split."""
    rest = rest or " " * len(first)
    lines, line = [], first
    for word in text.split():
        candidate = word if line in (first, rest) else f" {word}"
        if text_width(line + candidate) > width and line not in (first, rest):
            lines.append(line)
            line, candidate = rest, word
        line += candidate
    lines.append(line)
    return lines


def render_comparison_text(comp: dict, width: int = 100) -> str:
    """The comparison as plain text: recommended version, problem intervals, reasoning, then the details."""
    lb, rec, why = comp["labels"], comp["recommendation"], comp["reasoning"]
    bar, thin = "═" * width, "─" * width
    w_ = lambda text, first, rest="": wrap(text, width, first, rest)
    icon = ICONS[rec["verdict"]]
    title = f" {lb['title'].upper()}"
    lines = [bar, title + " " * max(1, width - text_width(title) - len(comp["meta"]["generated"])) + comp["meta"]["generated"], bar,
             f" 1. {lb['sec.recommended'].upper()}"]
    lines += w_(f"{icon} {rec['headline']}", "    ")
    lines += w_(f"{lb['dub_' + rec['dub']]}: {rec['title'] or ''} · {lb['verdict']}: {rec['verdict_label']}", "    ")
    if rec.get("caution"):
        lines += w_(f"⚠️ {rec['caution']}", "    ", "       ")
    if rec["warning"]:
        lines += w_(f"❌ {rec['warning']}", "    ")
        lines.append(f"    {lb['fix_first']}:")
        for item in rec["fix_first"]:
            lines += w_(f"- {item}", "      ", "        ")
    lines += ["", thin, f" 2. {lb['sec.intervals'].upper()}"]
    for dub in comp.get("dubs", DUBS):
        lines.append(f"  {lb['dub_' + dub]} ({lb['count_' + dub]})")
        items = comp["intervals"][dub]
        if not items:
            lines.append(f"    {lb['no_intervals']}")
        for i in items:
            lines += w_(interval_line(i, lb, comp["badges"]), "    ", "      ")
        if comp["possible_asr_errors"][dub]:
            lines.append(f"    {lb['asr']}:")
            for i in comp["possible_asr_errors"][dub]:
                lines += w_(interval_line(i, lb, comp["badges"]), "      ", "        ")
    lines += ["", thin, f" 3. {lb['sec.reasoning'].upper()}"]
    lines += w_(f"{lb['rule_label']}: {why['rule_label']}", "    ")
    dubs = comp.get("dubs", DUBS)
    lines += w_(f"{lb['values_label']}: " + " · ".join(f"{lb['dub_' + d]} = {why['values'][d]}" for d in dubs), "    ")
    if len(dubs) > 2:
        lines += w_(f"{lb['ranking_label']}: " + " · ".join(f"{r['rank']}. {lb['dub_' + r['dub']]} ({r['verdict_label']})"
                                                            for r in comp["ranking"]), "    ")
    lines += w_(f"{lb['summary_label']}: " + " ".join(why["summary"]), "    ")
    lines += w_(why["translation_note"], "    ")
    if why["skipped_rules"]:
        lines += w_(f"{lb['skipped']}: " + ", ".join(why["skipped_rules"]), "    ")
    lines += w_(why["rules_order"], "    ")

    lines += ["", thin, f" {lb['sec.table'].upper()}"]
    cell = lambda c: f"{ICONS[c['level']]} {c['badge']} · {c['display']}" if c else "—"
    w = max([text_width(r["label"]) for r in comp["table"]] + [text_width(lb["table.check"])]) + 2
    cols = {d: max([text_width(cell(r[d])) for r in comp["table"]] + [text_width(lb["dub_" + d])]) + 3 for d in dubs}
    lines.append(f"    {pad(lb['table.check'], w)}" + "".join(pad(lb["dub_" + d], cols[d]) for d in dubs).rstrip())
    for row in comp["table"]:
        lines.append(f"    {pad(row['label'], w)}" + "".join(pad(cell(row[d]), cols[d]) for d in dubs).rstrip())
    lines += ["", thin, f" {lb['sec.links'].upper()}"]
    for dub in comp.get("dubs", DUBS):
        link = comp["links"][dub]
        lines.append(f"  {lb['dub_' + dub]}")
        for key in ("title", "languages", "length", "lipsync", "project", "evaluated", "link"):
            lines += w_(f"{lb['meta.' + key]}: {link[key]}", "    ", "      ")
    lines += ["", thin, f" {lb['sec.notes'].upper()}"]
    for note in comp["notes"]:
        lines += w_(f"· {note}", "    ", "      ")
    lines += [thin, f" {lb['footer']}", bar]
    return "\n".join(lines)


_EXTRA_CSS = """
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.rec{border-width:2px}.rec.good{border-color:var(--good);background:var(--good-bg)}.rec.check{border-color:var(--check);
background:var(--check-bg)}.rec.poor{border-color:var(--poor);background:var(--poor-bg)}
.warn{color:var(--poor);font-weight:600}th{text-align:left;font-size:13px;color:var(--muted);padding:6px}
ol.fix li{margin:4px 0}.small{font-size:13px}
"""


def render_comparison_html(comp: dict) -> str:
    """A self-contained HTML comparison (light and dark), with the three decision sections at the top."""
    e = lambda x: html.escape(str(x)) if x is not None else ""
    lb, rec, why = comp["labels"], comp["recommendation"], comp["reasoning"]
    dubs = comp.get("dubs", DUBS)
    out = [f"<!doctype html><html lang={e(comp.get('lang', 'en'))}><head><meta charset=utf-8><meta name=viewport "
           f"content='width=device-width,initial-scale=1'><title>{e(lb['title'])}</title><style>{_CSS}{_EXTRA_CSS}"
           f"</style></head><body><main><h1>{e(lb['title'])}</h1><div class='meta muted'>"
           f"<span>{e(comp['meta']['generated'])}</span></div>",
           f"<div class='card rec {rec['verdict']}'><h2>1. {e(lb['sec.recommended'])}</h2>"
           f"<div class=big>{ICONS[rec['verdict']]} {e(rec['headline'])}</div>"
           f"<p>{e(lb['dub_' + rec['dub']])}: <b>{e(rec['title'])}</b> · {e(lb['verdict'])}: "
           f"<span class='badge b-{rec['verdict']}'>{e(rec['verdict_label'])}</span></p>"]
    if rec.get("caution"):
        out.append(f"<p class=warn>⚠️ {e(rec['caution'])}</p>")
    if rec["warning"]:
        out.append(f"<p class=warn>{e(rec['warning'])}</p><b>{e(lb['fix_first'])}</b><ol class=fix>"
                   + "".join(f"<li>{e(x)}</li>" for x in rec["fix_first"]) + "</ol>")
    out.append("</div>")
    out.append(f"<div class=card><h2>2. {e(lb['sec.intervals'])}</h2><div class=cols>")
    for dub in comp.get("dubs", DUBS):
        out.append(f"<div><b>{e(lb['dub_' + dub])}</b> <span class=muted>({e(lb['count_' + dub])})</span> "
                   f"<a href='report_{dub}.html'>{e(lb['open_report'])}</a><table>")
        if not comp["intervals"][dub]:
            out.append(f"<tr><td class=muted>{e(lb['no_intervals'])}</td></tr>")
        for i in comp["intervals"][dub]:
            out.append(f"<tr><td class='v t'>{i['start']:.1f}s–{i['end']:.1f}s</td><td><span class='badge "
                       f"b-{i['severity']}'>{e(i['category_label'])}</span> {e(i['description'])}"
                       f"<div class=th>{e(comp['badges'][i['severity']])} · {e(i['check_label'])}</div></td></tr>")
        out.append("</table>")
        if comp["possible_asr_errors"][dub]:
            out.append(f"<p class='small muted'><b>{e(lb['asr'])}</b></p><ul class='small muted'>" + "".join(
                f"<li>{i['start']:.1f}s–{i['end']:.1f}s · {e(i['category_label'])}: {e(i['description'])}</li>"
                for i in comp["possible_asr_errors"][dub]) + "</ul>")
        out.append("</div>")
    out.append("</div></div>")
    values = " · ".join(f"{e(lb['dub_' + d])}: <b>{e(why['values'][d])}</b>" for d in dubs)
    out.append(f"<div class=card><h2>3. {e(lb['sec.reasoning'])}</h2><table>"
               f"<tr><td class=l>{e(lb['rule_label'])}</td><td>{e(why['rule_label'])}</td></tr>"
               f"<tr><td class=l>{e(lb['values_label'])}</td><td>{values}</td></tr>")
    if len(dubs) > 2:
        ranking = " · ".join(f"{r['rank']}. {e(lb['dub_' + r['dub']])} <span class='badge b-{r['verdict']}'>"
                             f"{e(r['verdict_label'])}</span>" for r in comp["ranking"])
        out.append(f"<tr><td class=l>{e(lb['ranking_label'])}</td><td>{ranking}</td></tr>")
    skipped = f" {e(lb['skipped'])}: {e(', '.join(why['skipped_rules']))}." if why["skipped_rules"] else ""
    out.append(f"<tr><td class=l>{e(lb['summary_label'])}</td><td>{e(' '.join(why['summary']))}</td></tr></table>"
               f"<p class=note>{e(why['translation_note'])}{skipped}</p>"
               f"<p class=note>{e(why['rules_order'])}</p></div>")
    out.append(f"<div class=card><h2>{e(lb['sec.table'])}</h2><table><tr><th>{e(lb['table.check'])}</th>"
               + "".join(f"<th>{e(lb['dub_' + d])}</th>" for d in dubs) + "</tr>")
    cell = lambda c: (f"<span class='badge b-{c['level']}'>{e(c['badge'])}</span> <span class=t>{e(c['display'])}</span>"
                      if c else "—")
    for row in comp["table"]:
        out.append(f"<tr><td class=l>{e(row['label'])}</td>" + "".join(f"<td>{cell(row[d])}</td>" for d in dubs) + "</tr>")
    out.append("</table></div>")
    out.append(f"<div class=card><h2>{e(lb['sec.links'])}</h2><div class=cols>")
    for dub in comp.get("dubs", DUBS):
        link = comp["links"][dub]
        out.append(f"<div><b>{e(lb['dub_' + dub])}</b><table>" + "".join(
            f"<tr><td class=l>{e(lb['meta.' + k])}</td><td>{e(link[k])}</td></tr>"
            for k in ("title", "languages", "length", "lipsync", "project", "evaluated", "link")) + "</table></div>")
    out.append("</div></div>")
    out.append(f"<div class=card><h2>{e(lb['sec.notes'])}</h2><ul>"
               + "".join(f"<li>{e(n)}</li>" for n in comp["notes"]) + "</ul></div>")
    out.append(f"<p class=note>{e(lb['footer'])}</p></main></body></html>")
    return "".join(out)
