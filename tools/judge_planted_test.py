"""Dev tool: how many planted translation mistakes does a translation checker catch?

    python tools/judge_planted_test.py <set.json> --judge ollama [--model gemma4:12b] [--url http://127.0.0.1:PORT]
                                       [--runs 3] [--out results.json]

The set (docs/validation.md, "Translation mistakes put into transcripts") holds real dub transcripts line by line and,
per changed copy, mistakes written by hand on different lines: a wrong number, a reversed meaning, a line left out and
a harmless rewording. Each dub is judged unchanged and changed, with the same code the app uses
(translation_judge.judge_translation). Caught: the changed line's meaning score is RUBRIC_FLAG or lower while it wasn't
in the unchanged copy. A line already flagged unchanged can't show a catch and isn't counted. False alarms: a flagged
harmless rewording, or an untouched line flagged only in the changed copy. The set stays local: it is other people's
dubs. This tool only reads text; with --judge gemini / claude / openai that text goes to the service, as in the app.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KINDS = ("number", "reversed", "omitted")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("set")
    ap.add_argument("--judge", required=True, choices=("ollama", "gemini", "claude", "openai"))
    ap.add_argument("--model", help="the local model's name (Ollama), e.g. gemma4:12b")
    ap.add_argument("--url", help="an Ollama server to use instead of DubEval's own")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.model:
        os.environ["DUBEVAL_OLLAMA_MODEL"] = args.model            # read when translation_judge is imported
    if args.url:
        os.environ["DUBEVAL_OLLAMA_URL"] = args.url
    from dubeval import network, pipeline, translation_judge as tj     # noqa: F401  pipeline loads the saved API keys
    from dubeval.report import RUBRIC_FLAG
    network.use_system_settings()
    data = json.loads(Path(args.set).read_text(encoding="utf-8"))

    def judge(dub: dict, lines: list[dict]) -> tuple[dict, float]:
        """{line: (meaning score, may be misheard)} for one copy, and the seconds it took; {} when not measured."""
        segs = lambda side: [{"start": ln["start"], "end": ln["end"], "text": ln[side]} for ln in lines if ln[side]]
        started = time.time()
        r = tj.judge_translation(segs("original"), segs("dub"), dub["source_lang"], dub["target_lang"], lines=lines,
                                 provider=args.judge)
        if not r.get("measured"):
            print(f"      not measured: {r.get('reason_key')} {r.get('reason') or ''}"[:160], flush=True)
            return {}, time.time() - started
        return {ln["line"]: (ln["scores"]["semantic_accuracy"], bool(ln.get("may_be_recognition_error")))
                for ln in r["lines"]}, time.time() - started

    runs = []
    for run in range(1, args.runs + 1):
        base, rows, failed, seconds, lines_judged = {}, [], 0, 0.0, 0
        for name, dub in data["dubs"].items():
            base[name], took = judge(dub, dub["lines"])
            seconds += took
            lines_judged += len(dub["lines"])
            failed += not base[name]
            print(f"  run {run} | {name} unchanged: {len(base[name])} lines in {took:.0f} s", flush=True)
        for copy in data["copies"]:
            dub = data["dubs"][copy["dub"]]
            changed = {c["line"]: c for c in copy["changes"]}
            lines = [{**ln, "dub": changed[ln["n"]]["dub"]} if ln["n"] in changed else ln for ln in dub["lines"]]
            got, took = judge(dub, lines)
            seconds += took
            lines_judged += len(lines)
            failed += not got
            print(f"  run {run} | {copy['name']}: {len(got)} lines in {took:.0f} s", flush=True)
            before = base[copy["dub"]]
            if not got or not before:
                continue
            flagged = lambda scores, n: n in scores and scores[n][0] <= RUBRIC_FLAG
            for n, c in changed.items():
                rows.append({"copy": copy["name"], "lang": dub["target_lang"], "line": n, "kind": c["kind"],
                             "before": before.get(n, (None,))[0], "after": got.get(n, (None,))[0],
                             "misheard": got.get(n, (None, False))[1], "was_flagged": flagged(before, n),
                             "flagged": flagged(got, n)})
            for ln in dub["lines"]:
                if ln["n"] not in changed and flagged(got, ln["n"]) and not flagged(before, ln["n"]):
                    rows.append({"copy": copy["name"], "lang": dub["target_lang"], "line": ln["n"], "kind": "untouched",
                                 "before": before.get(ln["n"], (None,))[0], "after": got[ln["n"]][0], "flagged": True})
        runs.append({"rows": rows, "failed_calls": failed, "seconds": round(seconds), "lines": lines_judged})

    label = args.judge + (f" ({tj.OLLAMA_MODEL})" if args.judge == "ollama" else "")
    print(f"\n{label}: planted mistakes caught (meaning {RUBRIC_FLAG} or lower; lines already flagged unchanged aren't counted)")
    for i, run in enumerate(runs, 1):
        rows = run["rows"]
        countable = [r for r in rows if r["kind"] in KINDS and not r["was_flagged"]]
        caught = Counter(r["kind"] for r in countable if r["flagged"])
        total = Counter(r["kind"] for r in countable)
        by_lang = Counter(r["lang"] for r in countable if r["flagged"]), Counter(r["lang"] for r in countable)
        harmless = [r for r in rows if r["kind"] == "harmless" and not r["was_flagged"]]
        print(f"  run {i}: " + " | ".join(f"{k} {caught[k]} of {total[k]}" for k in KINDS)
              + f" | all {sum(caught.values())} of {sum(total.values())}"
              + f" | harmless flagged {sum(r['flagged'] for r in harmless)} of {len(harmless)}"
              + f" | untouched newly flagged {sum(r['kind'] == 'untouched' for r in rows)}"
              + f" | by language " + ", ".join(f"{k} {by_lang[0][k]} of {by_lang[1][k]}" for k in sorted(by_lang[1]))
              + f" | marked maybe-misheard {sum(bool(r.get('misheard')) for r in countable)}"
              + f" | calls not measured {run['failed_calls']} | {run['seconds']} s for {run['lines']} lines")
    if args.out:
        Path(args.out).write_text(json.dumps({"judge": label, "set": data.get("made"), "runs": runs}, ensure_ascii=False,
                                             indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
