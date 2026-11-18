"""Dev tool: a person's answers on single translation lines, to check the translation check line by line.

    python tools/label_lines.py prepare data/testset/run14 data/validation/line_review [--extra 20]
    python tools/label_lines.py serve data/validation/line_review
    python tools/label_lines.py reask data/testset/run14 data/validation/line_review data/validation/line_review_2

reask asks again, in a new folder, about the lines of an answered review that have words on both sides: every one the
check marked down and the same number of lines it didn't (as blind controls, `--controls`), in a fixed random order.
Its clips keep only TIGHT_PAD_SEC around a line, so the end of the line before isn't heard as part of this one (the
first review's "small difference" answers were mostly that); the page can still play the wide clip for context.

prepare reads a batch run's saved reports and takes every line the translation check marked down (a score of
report.RUBRIC_FLAG or lower) plus `--extra` lines it didn't, picked at random with a fixed seed. Per line it cuts the
same moment out of the original's and the dub's sound, as DubEval measured them (the dub on the original's timeline),
and writes lines.csv (the sheet the answers go into), clips/ and judge.json (what the judge said).

serve opens a page on 127.0.0.1 that plays both clips of a line and asks three things: is the original written down
right, is the dub written down right, and does the dub say what the original says. The answers are a person's: the
page doesn't say which lines were marked down, and shows the judge's scores for a line only after its three answers.
Like `dubeval label`, it opens only with its launch link and serves only the clips the sheet names.
The folder stays local: it holds other people's dubs.
"""
import argparse
import csv
import io
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PAD_SEC = 1.5                                     # sound kept before and after a line, so a short line has context
TIGHT_PAD_SEC = 0.2                               # reask: just enough not to cut the line's first and last sounds
FADE_SEC = 0.02                                   # a tight clip's edges fade, so a cut word doesn't click
SEED = 0
SIDES = ("original", "dub")
CLIPS = (*SIDES, "original_wide", "dub_wide")      # reask also keeps the wide clips, for context
HEARD = ("yes", "other", "silent")                # written down right / something else is said / nobody speaks
MEANING = ("same", "small", "wrong", "unsure")
ANSWERS = {"original_heard": HEARD, "dub_heard": HEARD, "meaning": MEANING}
TEXTS = ("original_said", "dub_said", "notes")
COLUMNS = ("id", "pair_id", "line", "start", "end", "languages", "before", "original", "dub", "after",
           *ANSWERS, *TEXTS)
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


# ---------------- the sheet ----------------
def read_sheet(folder: Path) -> list[dict]:
    """The rows of lines.csv."""
    with open(folder / "lines.csv", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items() if k} for row in csv.DictReader(f)]


def write_sheet(folder: Path, rows: list[dict]) -> None:
    """Writes lines.csv (atomically; with a BOM so Excel opens Korean text correctly)."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in COLUMNS})
    tmp = folder / "lines.csv.tmp"
    tmp.write_text(out.getvalue(), encoding="utf-8-sig", newline="")
    os.replace(tmp, folder / "lines.csv")


def save_answer(folder: Path, line_id: str, answer: dict) -> dict:
    """Stores one line's answers (an empty value clears one); returns the row's answers."""
    rows = read_sheet(folder)
    row = next((r for r in rows if r["id"] == line_id), None)
    if row is None:
        raise KeyError(line_id)
    for key, choices in ANSWERS.items():
        if key in answer:
            value = str(answer[key] or "").strip().lower()
            if value and value not in choices:
                raise ValueError(f"{key} must be one of: {', '.join(choices)}.")
            row[key] = value
    for key in TEXTS:
        if key in answer:
            row[key] = " ".join(str(answer[key] or "").split())
    write_sheet(folder, rows)
    return answers_of(row)


def answers_of(row: dict) -> dict:
    """A row's answers and notes."""
    return {k: row.get(k, "") for k in (*ANSWERS, *TEXTS)}


def answered(row: dict) -> bool:
    """Whether the three questions of a line are answered."""
    return all(row.get(k) for k in ANSWERS)


# ---------------- prepare ----------------
def prepare(run: Path, out: Path, extra: int) -> None:
    """Writes lines.csv, clips/ and judge.json for the run's marked-down lines and `extra` others."""
    import soundfile
    from dubeval import evaluate, pairing, pipeline, translation_judge
    from dubeval.evaluate import SAMPLE_RATE
    if (out / "lines.csv").exists():
        raise SystemExit(f"{out / 'lines.csv'} is already there, maybe with answers. Choose another folder.")
    with open(run / "summary.csv", encoding="utf-8-sig", newline="") as f:
        pair_ids = [r["pair_id"] for r in csv.DictReader(f)]
    folders = dict(zip(pair_ids, sorted(p for p in run.iterdir() if p.is_dir())))
    dubs, others = {}, []
    for pid, folder in folders.items():
        res = json.loads((folder / "report.json").read_text(encoding="utf-8"))["results"]
        tj = res.get("translation_judge") or {}
        if not (tj.get("measured") and tj.get("rubric")):
            continue
        marked = set(translation_judge.flagged(tj))
        dubs[pid] = {"results": res, "judge": tj, "marked": marked, "chosen": set(marked)}
        others += [(pid, j["line"]) for j in tj["lines"] if j["line"] not in marked]
    for pid, n in random.Random(SEED).sample(others, min(extra, len(others))):
        dubs[pid]["chosen"].add(n)

    (out / "clips").mkdir(parents=True, exist_ok=True)
    rows, judge = [], {}
    for pid, d in dubs.items():
        if not d["chosen"]:
            continue
        res, meta, pair = d["results"], d["results"].get("metadata") or {}, d["results"].get("pairing") or {}
        y_orig, y_dub = evaluate.load_both(res["pipeline"]["input_video_path"], res["pipeline"]["dubbed_video_path"])
        parts = pipeline.applied_parts(pair)             # the dub on the original's timeline, as it was measured
        y_dub = pairing.align_dub_parts(y_dub, parts, SAMPLE_RATE, len(y_orig)) if parts else \
            pairing.align_dub(y_dub, pair.get("applied_offset_sec") or 0.0, SAMPLE_RATE)
        lines = sorted(pipeline.judge_lines(res), key=lambda ln: ln["start"])
        judged = {j["line"]: j for j in d["judge"]["lines"]}
        languages = f"{meta.get('detected_source_language') or meta.get('source_language') or '?'} → " \
                    f"{meta.get('target_language') or '?'}"
        for i, ln in enumerate(lines):
            if ln["n"] not in d["chosen"]:
                continue
            line_id = f"{pid}-L{ln['n']}"
            for side, y in (("original", y_orig), ("dub", y_dub)):
                a = max(0, int((ln["start"] - PAD_SEC) * SAMPLE_RATE))
                b = min(len(y), int((ln["end"] + PAD_SEC) * SAMPLE_RATE))
                soundfile.write(out / "clips" / f"{line_id}_{side}.wav", y[a:b], SAMPLE_RATE, subtype="PCM_16")
            rows.append({"id": line_id, "pair_id": pid, "line": ln["n"], "start": ln["start"], "end": ln["end"],
                         "languages": languages, "original": ln.get("original") or "", "dub": ln.get("dub") or "",
                         "before": _context(lines[i - 1]) if i else "",
                         "after": _context(lines[i + 1]) if i + 1 < len(lines) else ""})
            j = judged[ln["n"]]
            low = min(j["scores"], key=j["scores"].get)
            judge[line_id] = {"marked": ln["n"] in d["marked"], "meaning": j["scores"]["semantic_accuracy"],
                              "lowest": j["scores"][low], "lowest_of": low, "error_type": j.get("error_type") or "",
                              "maybe_misheard": bool(j.get("may_be_recognition_error")),
                              "reason": _reason(j, low), "model": d["judge"].get("model") or ""}
        print(f"{pid}: {len(d['chosen'])} lines ({len(d['marked'])} marked down)", flush=True)
    write_sheet(out, rows)
    (out / "judge.json").write_text(json.dumps(judge, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} lines, {sum(j['marked'] for j in judge.values())} of them marked down, in {out}")


def _cut(y, start: float, end: float, pad: float, fade: float = 0.0):
    """The sound of [start - pad, end + pad], its edges faded over `fade` seconds."""
    import numpy as np
    from dubeval.evaluate import SAMPLE_RATE
    a, b = max(0, int((start - pad) * SAMPLE_RATE)), min(len(y), int((end + pad) * SAMPLE_RATE))
    clip = np.array(y[a:b], dtype=np.float32)
    n = min(int(fade * SAMPLE_RATE), len(clip) // 2)
    if n:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        clip[:n] *= ramp
        clip[-n:] *= ramp[::-1]
    return clip


def reask_choice(rows: list[dict], judge: dict, controls: Optional[int] = None) -> list[dict]:
    """The rows to ask again: those with words on both sides, every marked-down one plus `controls` others (default as
    many as marked down, or all there are), in a fixed random order so the marked ones don't come together."""
    both = [r for r in rows if r["original"].strip() and r["dub"].strip()]
    marked = [r for r in both if (judge.get(r["id"]) or {}).get("marked")]
    others = [r for r in both if not (judge.get(r["id"]) or {}).get("marked")]
    rng = random.Random(SEED)
    chosen = marked + rng.sample(others, min(len(others), len(marked) if controls is None else controls))
    rng.shuffle(chosen)
    return chosen


def reask(run: Path, answered_folder: Path, out: Path, controls: Optional[int] = None) -> None:
    """Writes a new review folder for answered_folder's lines with words on both sides (reask_choice), with tight clips
    and the wide ones; no answers are copied, so the person answers afresh."""
    import soundfile
    from dubeval import evaluate, pairing, pipeline
    from dubeval.evaluate import SAMPLE_RATE
    if (out / "lines.csv").exists():
        raise SystemExit(f"{out / 'lines.csv'} is already there, maybe with answers. Choose another folder.")
    judge = json.loads((answered_folder / "judge.json").read_text(encoding="utf-8"))
    chosen = reask_choice(read_sheet(answered_folder), judge, controls)
    with open(run / "summary.csv", encoding="utf-8-sig", newline="") as f:
        pair_ids = [r["pair_id"] for r in csv.DictReader(f)]
    folders = dict(zip(pair_ids, sorted(p for p in run.iterdir() if p.is_dir())))
    (out / "clips").mkdir(parents=True, exist_ok=True)
    for pid in dict.fromkeys(r["pair_id"] for r in chosen):
        res = json.loads((folders[pid] / "report.json").read_text(encoding="utf-8"))["results"]
        pair = res.get("pairing") or {}
        y_orig, y_dub = evaluate.load_both(res["pipeline"]["input_video_path"], res["pipeline"]["dubbed_video_path"])
        parts = pipeline.applied_parts(pair)             # the dub on the original's timeline, as it was measured
        y_dub = pairing.align_dub_parts(y_dub, parts, SAMPLE_RATE, len(y_orig)) if parts else \
            pairing.align_dub(y_dub, pair.get("applied_offset_sec") or 0.0, SAMPLE_RATE)
        for r in (r for r in chosen if r["pair_id"] == pid):
            start, end = float(r["start"]), float(r["end"])
            for side, y in (("original", y_orig), ("dub", y_dub)):
                soundfile.write(out / "clips" / f"{r['id']}_{side}.wav", _cut(y, start, end, TIGHT_PAD_SEC, FADE_SEC),
                                SAMPLE_RATE, subtype="PCM_16")
                soundfile.write(out / "clips" / f"{r['id']}_{side}_wide.wav", _cut(y, start, end, PAD_SEC),
                                SAMPLE_RATE, subtype="PCM_16")
        print(f"{pid}: {sum(r['pair_id'] == pid for r in chosen)} lines", flush=True)
    write_sheet(out, [{c: r.get(c, "") for c in COLUMNS[:10]} for r in chosen])
    (out / "judge.json").write_text(json.dumps({r["id"]: judge[r["id"]] for r in chosen if r["id"] in judge},
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    marked = sum((judge.get(r["id"]) or {}).get("marked", False) for r in chosen)
    print(f"{len(chosen)} lines ({marked} marked down, {len(chosen) - marked} not), in {out}")


def _context(line: dict) -> str:
    """A neighbouring line as the original said it (or the dub, where the original said nothing)."""
    return line.get("original") or line.get("dub") or ""


def _reason(judgement: dict, criterion: str) -> str:
    """The judge's reason for its lowest score, in English."""
    reasons = judgement.get("reasons") or {}
    reason = reasons.get(criterion) or reasons.get("semantic_accuracy") or ""
    return (reason.get("en") or "") if isinstance(reason, dict) else str(reason)


# ---------------- the page ----------------
def make_app(folder: Path, *, token: str):
    """The review page's FastAPI app for one prepared folder; every route needs this launch's cookie."""
    import secrets
    from typing import Optional
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
    from pydantic import BaseModel
    from dubeval.labeling import COOKIE, _guard
    from dubeval.localweb import add_security_headers

    def guard(request: Request) -> None:
        _guard(request, token)

    app = FastAPI(title="DubEval line review", docs_url=None, redoc_url=None, openapi_url=None,
                  dependencies=[Depends(guard)])
    add_security_headers(app)
    judge = json.loads((folder / "judge.json").read_text(encoding="utf-8"))

    class Answer(BaseModel):
        original_heard: Optional[str] = None
        dub_heard: Optional[str] = None
        meaning: Optional[str] = None
        original_said: Optional[str] = None
        dub_said: Optional[str] = None
        notes: Optional[str] = None

    def shown(row: dict) -> dict:
        """A line as the page gets it: the judge's part only once the person has answered."""
        out = {k: row[k] for k in ("id", "pair_id", "line", "start", "end", "languages", "before", "original", "dub",
                                   "after")}
        out["answer"] = answers_of(row)
        out["judge"] = judge.get(row["id"]) if answered(row) else None
        out["wide"] = (folder / "clips" / f"{row['id']}_original_wide.wav").is_file()   # a reask folder
        return out

    @app.get("/", response_class=HTMLResponse)
    def page(token_given: Optional[str] = None):
        if token_given is not None:                       # the launch link: becomes a cookie, the link is cleaned
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie(COOKIE, token, httponly=True, samesite="strict")
            return resp
        nonce = secrets.token_urlsafe(16)                 # the page's one inline script, and nothing else, may run
        return HTMLResponse(PAGE.replace("<script>", f'<script nonce="{nonce}">'), headers={
            "Cache-Control": "no-store", "Content-Security-Policy": (
                f"default-src 'self'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; media-src 'self'; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")})

    @app.get("/api/lines")
    def lines():
        return [shown(r) for r in read_sheet(folder)]

    @app.get("/clip/{line_id}/{side}")
    def clip(line_id: str, side: str):
        if side not in CLIPS or not ID_RE.match(line_id) or all(r["id"] != line_id for r in read_sheet(folder)):
            raise HTTPException(404)
        path = folder / "clips" / f"{line_id}_{side}.wav"
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/lines/{line_id}")
    def save(line_id: str, answer: Answer):
        try:
            save_answer(folder, line_id, answer.model_dump(exclude_none=True))
        except KeyError:
            raise HTTPException(404)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return shown(next(r for r in read_sheet(folder) if r["id"] == line_id))

    return app


def serve(folder: Path, port: int = 0, open_browser: bool = True) -> None:
    """Runs the page on 127.0.0.1 (a free port unless given) with a new token, and opens it in the browser."""
    import secrets
    import threading
    import webbrowser
    from dubeval.localweb import bind, run
    read_sheet(folder)                                    # a missing sheet fails here
    sock = bind("127.0.0.1", port)                        # bound before the link is printed
    token = secrets.token_urlsafe(24)
    url = f"http://127.0.0.1:{sock.getsockname()[1]}/?token_given={token}"
    print(f"Line review: {url}   (only this link works; press Ctrl+C here when you're done; answers are saved as "
          "you go)", flush=True)
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    run(make_app(folder, token=token), sock)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DubEval line review</title>
<style>
:root{--bg:#f6f6f4;--card:#fff;--text:#1d1d1b;--muted:#6b6a65;--line:#deddd7;--accent:#3d5afe;--good:#2e7d32;--check:#b26a00;--poor:#c62828}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#20201e;--text:#ecebe6;--muted:#a3a29b;--line:#3a3a36;--accent:#8c9eff;--good:#81c784;--check:#ffb74d;--poor:#ef9a9a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:17px;margin:0;font-weight:600}.muted{color:var(--muted);font-size:13px}
main{max-width:980px;margin:0 auto;padding:16px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:8px;padding:7px 12px;cursor:pointer}
button:hover{border-color:var(--muted)}button.on{background:var(--accent);border-color:var(--accent);color:#fff}
button.on[data-v=yes],button.on[data-v=same]{background:var(--good);border-color:var(--good)}
button.on[data-v=small],button.on[data-v=other]{background:var(--check);border-color:var(--check)}
button.on[data-v=wrong]{background:var(--poor);border-color:var(--poor)}
.sides{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}
@media (max-width:760px){.sides{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-width:0}
.card h2{font-size:13px;font-weight:600;margin:0 0 8px;color:var(--muted)}
audio{width:100%;margin-bottom:6px}button.small{font-size:13px;padding:4px 10px;margin-bottom:10px}
.heard{font-size:17px;margin:2px 0 12px;overflow-wrap:anywhere}.heard.none{color:var(--muted);font-style:italic;font-size:15px}
.q{font-weight:600;margin:10px 0 6px}.choices{display:flex;gap:8px;flex-wrap:wrap}
.context{font-size:13px;color:var(--muted);margin:10px 0;overflow-wrap:anywhere}
input[type=text]{font:inherit;width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text);margin-top:8px}
.hint{font-size:13px;color:var(--muted);margin:4px 0 8px}
.judge{margin-top:12px;font-size:14px}.status{font-size:13px;color:var(--muted);min-height:20px;margin-top:8px}
.err{color:var(--poor);font-size:13px}
</style></head><body>
<header><div><h1>Line review</h1><div class="muted">Listen to both sides of one line, then answer three questions. Answers are saved as you go.</div></div>
<div class="bar"><span class="muted" id="count"></span><button id="prev">Back</button><button id="next">Next</button><button id="todo">Next unanswered</button></div></header>
<main>
<div class="muted" id="meta"></div>
<div class="context" id="before"></div>
<div class="bar"><button id="both">Play original, then dub</button></div>
<div class="sides">
 <div class="card" id="c-original"></div>
 <div class="card" id="c-dub"></div>
</div>
<div class="context" id="after"></div>
<div class="card" id="c-meaning"></div>
<div class="judge card" id="judge"></div>
<div class="status" id="status"></div>
</main>
<script>
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const HEARD = [["yes", "Yes"], ["other", "No, something else is said"], ["silent", "No, nobody speaks"]];
const HEARD_NONE = [["yes", "Yes, nobody speaks"], ["other", "No, someone speaks"]];
const MEANING = [["same", "Yes"], ["small", "Small difference"], ["wrong", "No"], ["unsure", "Can't tell"]];
const NAMES = {semantic_accuracy: "meaning", linguistic_naturalness: "naturalness", contextual_consistency: "context",
               terminology_consistency: "terms", localization_appropriateness: "localization"};
let lines = [], cur = 0;
const players = {}, wide = new Audio();
const done = l => l.answer.original_heard && l.answer.dub_heard && l.answer.meaning;

function choices(key, options){
  const l = lines[cur], box = el("div", "choices");
  for (const [v, label] of options){
    const b = el("button", l.answer[key] === v ? "on" : "", label); b.dataset.v = v;
    b.onclick = () => save({[key]: l.answer[key] === v ? "" : v}); box.appendChild(b);
  }
  return box;
}
function field(key, placeholder){
  const inp = el("input"); inp.type = "text"; inp.placeholder = placeholder; inp.value = lines[cur].answer[key] || "";
  inp.onchange = () => save({[key]: inp.value}); return inp;
}
function side(name, title){
  const l = lines[cur], card = $("c-" + name); card.textContent = "";
  card.appendChild(el("h2", "", title));
  const a = el("audio"); a.controls = true; a.preload = "auto"; a.src = `/clip/${encodeURIComponent(l.id)}/${name}`;
  players[name] = a; card.appendChild(a);
  if (l.wide){                                   // a reask: the clip is tight; the wide one gives the context
    const w = el("button", "small", "Play with 1.5 s around it");
    w.onclick = () => { for (const p of Object.values(players)) p.pause(); wide.src = `/clip/${encodeURIComponent(l.id)}/${name}_wide`; wide.play(); };
    card.appendChild(w);
  }
  card.appendChild(el("div", "muted", "DubEval heard:"));
  card.appendChild(l[name] ? el("div", "heard", l[name]) : el("div", "heard none", "no speech"));
  card.appendChild(el("div", "q", "Is that what you hear?"));
  card.appendChild(choices(name + "_heard", l[name] ? HEARD : HEARD_NONE));
  if (l.answer[name + "_heard"] === "other") card.appendChild(field(name + "_said", "What is really said (optional)"));
}
function show(i){
  cur = (i + lines.length) % lines.length; const l = lines[cur];
  for (const a of Object.values(players)) a.pause();
  wide.pause();
  $("count").textContent = `${lines.filter(done).length} of ${lines.length} answered`;
  $("meta").textContent = `Line ${cur + 1} of ${lines.length} · ${l.pair_id} · ${l.languages} · at ${Number(l.start).toFixed(1)}–${Number(l.end).toFixed(1)} s`;
  $("before").textContent = l.before ? "Line before: " + l.before : "";
  $("after").textContent = l.after ? "Line after: " + l.after : "";
  side("original", "Original"); side("dub", "Dub");
  const m = $("c-meaning"); m.textContent = "";
  m.appendChild(el("div", "q", "Does the dub say what the original says?"));
  m.appendChild(el("div", "hint", l.wide
    ? "Only this line counts: a word cut off at either edge belongs to the line before or after, so leave it out. Go by what you hear, not by the text. A small difference: the idea is there, a detail is off."
    : "Go by what you hear, not by the text. A small difference: the idea is there, a detail is off."));
  m.appendChild(choices("meaning", MEANING));
  m.appendChild(field("notes", "Notes (optional)"));
  const j = $("judge"); j.textContent = "";
  if (!done(l)) j.appendChild(el("div", "muted", "What DubEval's translation check said about this line shows after your three answers."));
  else if (l.judge){
    const g = l.judge;
    j.appendChild(el("div", "q", g.marked ? "DubEval marked this line down" : "DubEval didn't mark this line down"));
    j.appendChild(el("div", "", `Meaning ${g.meaning} of 10` + (g.lowest_of !== "semantic_accuracy" ? ` · lowest score: ${NAMES[g.lowest_of] || g.lowest_of} ${g.lowest}` : "")
      + (g.error_type && g.error_type !== "none" ? ` · ${g.error_type.replace(/_/g, " ")}` : "") + (g.maybe_misheard ? " · maybe misheard" : "")));
    if (g.reason) j.appendChild(el("div", "muted", g.reason));
  }
}
async function save(change){
  const l = lines[cur];
  try {
    const r = await fetch(`/api/lines/${encodeURIComponent(l.id)}`, {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(change)});
    if (!r.ok) throw new Error(await r.text());
    const times = Object.fromEntries(Object.entries(players).map(([k, a]) => [k, [a.currentTime, !a.paused]]));
    lines[cur] = await r.json(); $("status").textContent = "Saved."; show(cur);
    for (const [k, [t, playing]] of Object.entries(times)) { players[k].currentTime = t; if (playing) players[k].play(); }
  } catch (e) { $("status").textContent = "Couldn't save. Is the review still running in its terminal?"; }
}
$("prev").onclick = () => show(cur - 1);
$("next").onclick = () => show(cur + 1);
$("todo").onclick = () => { const order = lines.map((_, i) => (cur + 1 + i) % lines.length), i = order.find(i => !done(lines[i]));
  if (i === undefined) $("status").textContent = "Every line is answered. Thank you."; else show(i); };
$("both").onclick = () => { const o = players.original, d = players.dub; d.pause(); d.currentTime = 0; o.currentTime = 0;
  o.onended = () => { o.onended = null; d.play(); }; o.play(); };
fetch("/api/lines").then(r => r.json()).then(d => { lines = d; if (lines.length) show(Math.max(0, lines.findIndex(l => !done(l)))); });
</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="A person's answers on single translation lines.")
    sub = parser.add_subparsers(dest="step", required=True)
    p = sub.add_parser("prepare", help="cut the lines of a batch run into a review folder")
    p.add_argument("run", type=Path)
    p.add_argument("folder", type=Path)
    p.add_argument("--extra", type=int, default=20, help="lines the check didn't mark down, picked at random")
    a = sub.add_parser("reask", help="ask again about an answered review's lines with words on both sides, tight clips")
    a.add_argument("run", type=Path)
    a.add_argument("answered", type=Path)
    a.add_argument("folder", type=Path)
    a.add_argument("--controls", type=int, default=None, help="lines the check didn't mark down (default: as many as it did)")
    s = sub.add_parser("serve", help="open the review page for a prepared folder")
    s.add_argument("folder", type=Path)
    s.add_argument("--port", type=int, default=0)
    s.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.step == "prepare":
        prepare(args.run, args.folder, args.extra)
    elif args.step == "reask":
        reask(args.run, args.answered, args.folder, args.controls)
    else:
        serve(args.folder.resolve(), args.port, not args.no_browser)


if __name__ == "__main__":
    main()
