"""Labelling: a local review page for a test-set sheet, so a person can watch each original and dub side by side and
give the verdicts that calibration needs (`dubeval label testset.csv`).

The person's verdicts are the answer key DubEval is tuned against, so DubEval's own verdict stays hidden until the
person has answered a pair. The server listens on 127.0.0.1 only and serves only the files the sheet names.
Answers are written back into the sheet (comment lines and column order kept, atomic write).
"""
import csv
import io
import os
import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

LABEL_COLUMNS = ("label", "length_label", "meaning_label")
TEXT_COLUMNS = ("notes", "reviewer")
CHOICES = ("good", "check", "poor")
COOKIE = "dubeval_label"
NEED_LINK = "Open the review page from the link printed by `dubeval label`."


# ---------------- the sheet ----------------
def read_sheet(path: str) -> tuple[list[str], list[str], list[dict]]:
    """(comment lines, column names, rows) of a test-set sheet; relative media paths resolved from its folder."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    comments = [ln for ln in lines if ln.strip().startswith("#")]
    reader = csv.DictReader([ln for ln in lines if not ln.strip().startswith("#")])
    columns = list(reader.fieldnames or [])
    if not {"original", "dub"} <= {c.strip().lower() for c in columns}:
        raise ValueError("This sheet has no original and dub columns. Start from examples/testset_template.csv.")
    rows = [{k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]
    rows = [r for r in rows if r.get("original") and r.get("dub")]
    for n, row in enumerate(rows, 1):
        row.setdefault("pair_id", "")
        row["pair_id"] = row["pair_id"] or f"row{n}"
    return comments, columns, rows


def write_sheet(path: str, comments: list[str], columns: list[str], rows: list[dict]) -> None:
    """Writes the sheet back: its comment lines first, then the rows in the same column order (atomically)."""
    out = io.StringIO()
    for c in comments:
        out.write(c + "\n")
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    target = Path(path)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(out.getvalue(), encoding="utf-8-sig")       # BOM: Excel opens Korean text correctly
    os.replace(tmp, target)


def save_answer(path: str, pair_id: str, answer: dict) -> dict:
    """Stores one pair's verdicts (good / check / poor, or empty), notes and reviewer in the sheet; returns the row."""
    comments, columns, rows = read_sheet(path)
    row = next((r for r in rows if r["pair_id"] == pair_id), None)
    if row is None:
        raise KeyError(pair_id)
    for key in LABEL_COLUMNS:
        if key in answer:
            value = (answer[key] or "").strip().lower()
            if value and value not in CHOICES:
                raise ValueError(f"{key} must be good, check or poor.")
            row[key] = value
    for key in TEXT_COLUMNS:
        if key in answer:
            row[key] = " ".join(str(answer[key] or "").split())
    for key in (*LABEL_COLUMNS, *TEXT_COLUMNS):
        if key not in columns:
            columns.append(key)
    write_sheet(path, comments, columns, rows)
    return row


def tool_verdicts(results_dir: Optional[str]) -> dict:
    """DubEval's verdicts per pair from a batch run's summary.csv (shown only after the person has answered)."""
    if not results_dir or not (Path(results_dir) / "summary.csv").is_file():
        return {}
    out = {}
    with open(Path(results_dir) / "summary.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = r.get("pair_id") or r.get("link")
            out[key] = {"label": r.get("verdict") or "", "length_label": r.get("line_length_level") or
                        r.get("speech_overlap_level") or "", "meaning_label": r.get("meaning_level") or
                        r.get("meaning_screen_level") or ""}
    return out


# ---------------- the server ----------------
def make_app(sheet: str, results_dir: Optional[str] = None, lang: str = "en", *, token: str):
    """The review page's FastAPI app for one sheet; every route needs the cookie set from this launch's `token`."""
    import secrets
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
    from pydantic import BaseModel
    from dubeval.i18n import TEXT
    from dubeval.localweb import add_security_headers

    def guard(request: Request) -> None:
        _guard(request, token)

    base = Path(sheet).resolve().parent
    app = FastAPI(title="DubEval labelling", docs_url=None, redoc_url=None, openapi_url=None,
                  dependencies=[Depends(guard)])
    add_security_headers(app)

    class Answer(BaseModel):
        label: Optional[str] = None
        length_label: Optional[str] = None
        meaning_label: Optional[str] = None
        notes: Optional[str] = None
        reviewer: Optional[str] = None

    def media_path(spec: str) -> Path:
        """A sheet path as a local file (links aren't served: the page plays them from their own host)."""
        p = Path(spec).expanduser()
        return p if p.is_absolute() else base / p

    @app.get("/", response_class=HTMLResponse)
    def page(token_given: Optional[str] = None):
        if token_given is not None:                       # the launch link: becomes a cookie, the link is cleaned
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie(COOKIE, token, httponly=True, samesite="strict")
            return resp
        texts = {k[4:]: (v.get(lang) or v["en"]) for k, v in TEXT.items() if k.startswith("lab.")}
        nonce = secrets.token_urlsafe(16)                 # the page's one inline script, and nothing else, may run
        texts_js = json.dumps(texts, ensure_ascii=False).replace("<", "\\u003c")   # a text can't close the script
        html = (PAGE.replace("__TEXTS__", texts_js).replace("__LANG__", lang)
                .replace("<script>", f'<script nonce="{nonce}">'))
        return HTMLResponse(html, headers={"Content-Security-Policy": (
            f"default-src 'self'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; media-src 'self' https: http:; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")})

    @app.get("/api/pairs")
    def pairs():
        _, _, rows = read_sheet(sheet)
        verdicts = tool_verdicts(results_dir)
        out = []
        for r in rows:
            local = lambda spec: not spec.lower().startswith(("http://", "https://"))
            out.append({"pair_id": r["pair_id"], "service": r.get("service", ""), "dub_type": r.get("dub_type", ""),
                        "languages": f"{r.get('source_lang') or '?'} → {r.get('target_lang') or '?'}",
                        "title": r.get("notes", "")[:80] or Path(r["dub"]).parent.name or r["pair_id"],
                        "original": f"/media/{r['pair_id']}/original" if local(r["original"]) else r["original"],
                        "dub": f"/media/{r['pair_id']}/dub" if local(r["dub"]) else r["dub"],
                        "answer": {k: r.get(k, "") for k in (*LABEL_COLUMNS, *TEXT_COLUMNS)},
                        "tool": verdicts.get(r["pair_id"]) or verdicts.get(r["dub"]) or None})
        return out

    @app.get("/media/{pair_id}/{side}")
    def media(pair_id: str, side: str):
        if side not in ("original", "dub"):
            raise HTTPException(404)
        _, _, rows = read_sheet(sheet)
        row = next((r for r in rows if r["pair_id"] == pair_id), None)
        if row is None or row[side].lower().startswith(("http://", "https://")):
            raise HTTPException(404)
        path = media_path(row[side])
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)                         # supports range requests, so the players can seek

    @app.post("/api/pairs/{pair_id}")
    def save(pair_id: str, answer: Answer):
        try:
            row = save_answer(sheet, pair_id, answer.model_dump(exclude_none=True))
        except KeyError:
            raise HTTPException(404)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {k: row.get(k, "") for k in (*LABEL_COLUMNS, *TEXT_COLUMNS)}

    return app


def _guard(request, token: str) -> None:
    """Only this machine's browser, opened with this launch's link (blocks DNS-rebinding sites and other pages)."""
    import hmac
    from fastapi import HTTPException
    from dubeval.localweb import is_local_host
    if not is_local_host(request.headers.get("host")):
        raise HTTPException(status_code=403, detail="Open DubEval at http://127.0.0.1.")
    given = request.query_params.get("token_given") if request.url.path == "/" else None
    if given is not None:
        if not hmac.compare_digest(given, token):
            raise HTTPException(status_code=401, detail="This link is from an earlier launch. Use the new one.")
        return
    if not hmac.compare_digest(request.cookies.get(COOKIE, ""), token):
        raise HTTPException(status_code=401, detail=NEED_LINK)


def serve(sheet: str, results_dir: Optional[str] = None, lang: str = "en", port: int = 0,
          open_browser: bool = True) -> None:
    """Runs the review page on 127.0.0.1 (a free port unless given) with a new token, and opens it in the browser."""
    import secrets
    import threading
    import webbrowser
    from dubeval.localweb import bind, run
    read_sheet(sheet)                                     # a broken sheet fails here, with a plain message
    sock = bind("127.0.0.1", port)                        # bound before the link is printed
    token = secrets.token_urlsafe(24)
    url = f"http://127.0.0.1:{sock.getsockname()[1]}/?token_given={token}"
    print(f"Review page: {url}   (only this link works; press Ctrl+C here when you're done; answers are saved as you "
          "go)", flush=True)
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    run(make_app(sheet, results_dir, lang, token=token), sock)


PAGE = r"""<!doctype html>
<html lang="__LANG__"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DubEval labelling</title>
<style>
:root{--bg:#f6f6f4;--card:#fff;--text:#1d1d1b;--muted:#6b6a65;--line:#deddd7;--accent:#3d5afe;--good:#2e7d32;--check:#b26a00;--poor:#c62828}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#20201e;--text:#ecebe6;--muted:#a3a29b;--line:#3a3a36;--accent:#8c9eff;--good:#81c784;--check:#ffb74d;--poor:#ef9a9a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 20px;border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:17px;margin:0;font-weight:600}.muted{color:var(--muted);font-size:13px}
main{max-width:1200px;margin:0 auto;padding:16px 20px}
.nav{display:flex;gap:6px;flex-wrap:wrap}.nav button{min-width:34px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:8px;padding:6px 12px;cursor:pointer}
button:hover{border-color:var(--muted)}button.on{background:var(--accent);border-color:var(--accent);color:#fff}
.nav button.done{border-color:var(--good)}.nav button.cur{outline:2px solid var(--accent)}
.videos{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}
@media (max-width:760px){.videos{grid-template-columns:1fr}}
.vbox{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
video{width:100%;border-radius:8px;background:#000;max-height:46vh}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.q{display:grid;grid-template-columns:minmax(150px,220px) 1fr;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
.q:last-of-type{border-bottom:0}.q .hint{grid-column:2;font-size:13px;color:var(--muted);margin-top:-6px}
.choices{display:flex;gap:8px;flex-wrap:wrap}.choices button[data-v=good].on{background:var(--good);border-color:var(--good)}
.choices button[data-v=check].on{background:var(--check);border-color:var(--check)}.choices button[data-v=poor].on{background:var(--poor);border-color:var(--poor)}
input[type=text]{font:inherit;width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text)}
.tool{margin-top:12px;font-size:14px}.status{font-size:13px;color:var(--muted);min-height:20px}
.err{color:var(--poor);font-size:13px}
</style></head><body>
<header><div><h1 id="t-title"></h1><div class="muted" id="t-intro"></div></div><div class="nav" id="nav"></div></header>
<main>
<div class="muted" id="meta"></div>
<div class="videos">
 <div class="vbox"><div class="muted" id="t-original"></div><video id="vo" controls preload="metadata"></video></div>
 <div class="vbox"><div class="muted" id="t-dub"></div><video id="vd" controls preload="metadata"></video></div>
</div>
<div class="controls">
 <button id="play"></button><button id="back5">−5 s</button><button id="fwd5">+5 s</button>
 <span class="muted" id="t-listen"></span>
 <span class="choices" id="listen"><button data-l="dub"></button><button data-l="original"></button></span>
</div>
<div class="card" id="form"></div>
<div class="tool" id="tool"></div>
<div class="status" id="status"></div>
</main>
<script>
const T = __TEXTS__;
const $ = id => document.getElementById(id);
let pairs = [], cur = 0, listen = "dub";
const vo = $("vo"), vd = $("vd");
for (const [id, key] of [["t-title","title"],["t-intro","intro"],["t-original","original"],["t-dub","dub"],["t-listen","listen"]]) $(id).textContent = T[key];
$("listen").children[0].textContent = T.listen_dub; $("listen").children[1].textContent = T.listen_original;
const QUESTIONS = [["length_label","q_length","h_length"],["meaning_label","q_meaning","h_meaning"],["label","q_overall","h_overall"]];
function done(p){ return QUESTIONS.every(([k]) => p.answer[k]); }
function nav(){
  $("nav").innerHTML = "";
  pairs.forEach((p, i) => { const b = document.createElement("button"); b.textContent = i + 1;
    b.className = (done(p) ? "done " : "") + (i === cur ? "cur" : ""); b.title = p.pair_id; b.onclick = () => show(i); $("nav").appendChild(b); });
}
function setListen(l){ listen = l; vo.muted = l === "dub"; vd.muted = l === "original";
  [...$("listen").children].forEach(b => b.classList.toggle("on", b.dataset.l === l)); }
function show(i){
  cur = i; const p = pairs[i]; vo.pause(); vd.pause();
  vo.src = p.original; vd.src = p.dub; setListen(listen);
  $("meta").textContent = `${i + 1} / ${pairs.length} · ${p.pair_id} · ${p.languages} · ${p.service || ""} ${p.dub_type || ""} · ${p.title}`;
  const f = $("form"); f.innerHTML = "";
  for (const [key, q, h] of QUESTIONS){
    const row = document.createElement("div"); row.className = "q";
    row.innerHTML = `<div><b>${T[q]}</b></div><div class="choices"></div><div class="hint">${T[h]}</div>`;
    for (const v of ["good","check","poor"]){ const b = document.createElement("button"); b.dataset.v = v; b.textContent = T["c_" + v];
      b.classList.toggle("on", p.answer[key] === v); b.onclick = () => save({[key]: p.answer[key] === v ? "" : v});
      row.querySelector(".choices").appendChild(b); }
    f.appendChild(row);
  }
  for (const [key, label] of [["notes","notes"],["reviewer","reviewer"]]){
    const row = document.createElement("div"); row.className = "q";
    row.innerHTML = `<div><b>${T[label]}</b></div><div><input type="text"></div>`;
    const inp = row.querySelector("input"); inp.value = p.answer[key] || ""; inp.onchange = () => save({[key]: inp.value});
    f.appendChild(row);
  }
  const next = document.createElement("div"); next.className = "q";
  next.innerHTML = `<div></div><div><button id="next">${T.next}</button> <span class="err" id="err"></span></div>`; f.appendChild(next);
  $("next").onclick = () => { if (!done(p)) { $("err").textContent = T.answer_all; return; } show((cur + 1) % pairs.length); };
  tool(); nav();
}
function tool(){
  const p = pairs[cur], t = p.tool;
  if (!t) { $("tool").textContent = ""; return; }
  if (!done(p)) { $("tool").textContent = T.tool_hidden; return; }
  const name = v => T["c_" + v] || T["c_" + ({not_measured:"na"}[v] || "na")] || v || "—";
  $("tool").textContent = `${T.tool_says}: ${T.q_length} ${name(t.length_label)} · ${T.q_meaning} ${name(t.meaning_label)} · ${T.q_overall} ${name(t.label)}`;
}
async function save(change){
  const p = pairs[cur];
  try {
    const r = await fetch(`/api/pairs/${encodeURIComponent(p.pair_id)}`, {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(change)});
    if (!r.ok) throw new Error(await r.text());
    p.answer = {...p.answer, ...(await r.json())}; $("status").textContent = T.saved;
    const keep = {t: vo.currentTime, playing: !vo.paused}; show(cur); vo.currentTime = vd.currentTime = keep.t;
    if (keep.playing) { vo.play(); vd.play(); }
  } catch (e) { $("status").textContent = T.save_failed; }
}
$("play").textContent = T.play;
$("play").onclick = () => { if (vo.paused) { vd.currentTime = vo.currentTime; vo.play(); vd.play(); $("play").textContent = T.pause; }
                            else { vo.pause(); vd.pause(); $("play").textContent = T.play; } };
const jump = d => { vo.currentTime = Math.max(0, vo.currentTime + d); vd.currentTime = vo.currentTime; };
$("back5").onclick = () => jump(-5); $("fwd5").onclick = () => jump(5);
vo.addEventListener("seeked", () => { if (Math.abs(vd.currentTime - vo.currentTime) > 0.3) vd.currentTime = vo.currentTime; });
[...$("listen").children].forEach(b => b.onclick = () => setListen(b.dataset.l));
fetch("/api/pairs").then(r => r.json()).then(d => { pairs = d; if (pairs.length) show(Math.max(0, pairs.findIndex(p => !done(p)))); });
</script></body></html>"""
