"""The release QA report: one self-contained HTML page (and a PDF beside it) from a run folder of release_qa.py.

    python tools/release_qa/report.py data/qa/<run>             # English
    python tools/release_qa/report.py data/qa/<run> --lang ko   # Korean

It reads results.json (what the run measured and checked) and, when present, findings.json: a reviewer's problems
from looking at the screenshots, each {"priority": "P1"|"P2"|"P3", "title", "where", "detail", "fix"}. A failed check
becomes a problem on its own, so the report never hides one. Screenshots are embedded (scaled down), so the HTML file
can be sent as it is; the PDF is printed by Microsoft Edge when it's installed.
"""
import argparse
import base64
import html
import io
import json
import subprocess
from pathlib import Path

TEXT = {
    "en": {
        "title": "DubEval {tag} release test", "sub": "Installed and used like a new user on {date}, by an automated run.",
        "summary": "Summary", "passed": "{p} of {n} scenarios passed", "problems": "Problems, most serious first",
        "none": "No problems found.", "env": "What was tested, and on what", "release": "Release",
        "published": "published {d}", "installer": "Installer", "machine": "Computer", "inputs": "Test videos",
        "timeline": "Scenarios", "step": "Scenario", "result": "Result", "time": "Time", "detail": "What was checked",
        "metrics": "Measured", "shots": "Screens", "log": "Logs", "console": "Browser console (errors and warnings)",
        "server": "Server log", "server_counts": "{e} errors, {w} warnings, {t} tracebacks (server.log in the run folder)",
        "untested": "Not tested in this run", "pass": "pass", "fail": "fail", "error": "error",
        "auto": "found by the run", "review": "found by review", "where": "Where", "fix": "Fix",
        "first_launch": "First window to the app's page: {s} s", "eval": "One evaluation (1 min clip): {s} s",
        "compare": "Comparing two dubs: {s} s", "stop": "Stopping a running evaluation: {s} s",
        "untested_list": ["The installer's own screens (the run installs silently)", "Share links and video page links "
                          "(network)", "The file picker and drag and drop", "Model downloads (Settings → Models), "
                          "the lip-sync check and the GPU pack", "Automatic updates", "macOS, Linux, a PC without a GPU"],
    },
    "ko": {
        "title": "DubEval {tag} 릴리스 시험", "sub": "{date}에 자동 실행으로 새 사용자처럼 설치하고 써 봤습니다.",
        "summary": "요약", "passed": "시나리오 {n}개 중 {p}개 통과", "problems": "문제 (심각한 순)",
        "none": "문제가 없었습니다.", "env": "시험 대상과 환경", "release": "릴리스", "published": "{d} 게시",
        "installer": "설치 파일", "machine": "컴퓨터", "inputs": "시험 영상", "timeline": "시나리오", "step": "시나리오",
        "result": "결과", "time": "시간", "detail": "확인한 것", "metrics": "측정값", "shots": "화면", "log": "로그",
        "console": "브라우저 콘솔 (오류·경고)", "server": "서버 로그",
        "server_counts": "오류 {e}건, 경고 {w}건, 트레이스백 {t}건 (실행 폴더의 server.log)",
        "untested": "이번에 시험하지 않은 것", "pass": "통과", "fail": "실패", "error": "오류",
        "auto": "자동 확인", "review": "화면 검토", "where": "어디서", "fix": "고치는 법",
        "first_launch": "첫 창에서 앱 화면까지: {s}초", "eval": "평가 한 건 (1분 영상): {s}초",
        "compare": "더빙 두 개 비교: {s}초", "stop": "중지에 걸린 시간: {s}초",
        "untested_list": ["설치 프로그램 화면 (자동 설치로 진행)", "공유 링크와 영상 페이지 링크 (네트워크)",
                          "파일 선택 창과 끌어 놓기", "모델 다운로드 (설정 → 모델), 립싱크 검사, GPU 팩", "자동 업데이트",
                          "macOS, Linux, GPU 없는 PC"],
    },
}
ORDER = {"P1": 0, "P2": 1, "P3": 2}

CSS = """
:root{--fg:#1d2330;--muted:#5d6675;--line:#e3e6eb;--card:#f6f7f9;--good:#1a7f37;--bad:#c62828;--warn:#b26a00;--accent:#2457d6}
*{box-sizing:border-box}body{font:14px/1.55 "Segoe UI","Malgun Gothic",system-ui,sans-serif;color:var(--fg);margin:0;background:#fff}
main{max-width:980px;margin:0 auto;padding:32px 24px 48px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 10px;
padding-bottom:6px;border-bottom:2px solid var(--fg)}h3{font-size:15px;margin:18px 0 6px}.sub{color:var(--muted);margin:0 0 18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0}.kpi{background:var(--card);
border-radius:8px;padding:10px 12px}.kpi b{display:block;font-size:20px}.kpi span{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;margin:8px 0}th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--line)}
th{background:var(--card);font-weight:600}.pill{display:inline-block;padding:0 8px;border-radius:99px;font-size:12px;font-weight:600;color:#fff}
.pass{background:var(--good)}.fail,.error{background:var(--bad)}.P1{background:var(--bad)}.P2{background:var(--warn)}.P3{background:#6b7280}
.ok{color:var(--good)}.bad{color:var(--bad);font-weight:600}.muted{color:var(--muted)}code{font:12px Consolas,monospace;background:var(--card);
padding:1px 4px;border-radius:4px}figure{margin:10px 0 18px;break-inside:avoid}figure img{width:100%;border:1px solid var(--line);border-radius:6px}
figcaption{color:var(--muted);font-size:12px}ul{margin:4px 0 4px 18px;padding:0}.prob{break-inside:avoid}
@media print{main{padding:0}h2{break-after:avoid}}
"""


def esc(x) -> str:
    return html.escape(str(x)) if x is not None else ""


def embed(path: Path, width: int = 1200) -> str:
    """A screenshot as a data: URI, scaled down to width and stored as JPEG so the page stays small to send."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        if img.width > width:
            img = img.resize((width, round(img.height * width / img.width)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=82)
        data, kind = buf.getvalue(), "jpeg"
    except Exception:
        data, kind = path.read_bytes(), "png"
    return f"data:image/{kind};base64,{base64.b64encode(data).decode('ascii')}"


def problems(results: dict, findings: list, t: dict) -> list:
    """Every problem: each failed check or crashed scenario (P1), server tracebacks (P2), then the reviewer's."""
    out = []
    for s in results["steps"]:
        if s["status"] == "error":
            out.append({"priority": "P1", "title": f"{s['title']}: the scenario couldn't finish", "where": s["id"],
                        "detail": s.get("error", ""), "source": t["auto"]})
        for c in s["checks"]:
            if not c["ok"]:
                out.append({"priority": "P1", "title": c["what"], "where": s["title"], "detail": c["detail"],
                            "source": t["auto"]})
    log = results.get("server_log") or {}
    if log.get("tracebacks"):
        out.append({"priority": "P2", "title": f"{log['tracebacks']} tracebacks in the server log", "where": "server.log",
                    "detail": "Expected failures (a non-video file) shouldn't be logged as crashes.", "source": t["auto"]})
    for f in findings:
        out.append({**f, "source": t["review"]})
    return sorted(out, key=lambda p: ORDER.get(p.get("priority"), 3))


def metric_text(m: dict) -> str:
    """A scenario's measured values, one per line."""
    rows = []
    for k, v in m.items():
        if isinstance(v, dict):
            v = ", ".join(f"{a} {b}" for a, b in v.items())
        rows.append(f"<div><span class=muted>{esc(k)}</span> {esc(v)}</div>")
    return "".join(rows)


def render(folder: Path, lang: str) -> str:
    t = TEXT[lang]
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    fpath = folder / "findings.json"
    findings = json.loads(fpath.read_text(encoding="utf-8")) if fpath.is_file() else []
    rel, mach, steps = results["release"], results.get("machine") or {}, results["steps"]
    by_id = {s["id"]: s for s in steps}
    passed = sum(s["status"] == "pass" for s in steps)
    probs = problems(results, findings, t)
    date = results["started"].replace("T", " ")[:16]
    out = [f"<!doctype html><html lang={lang}><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
           f"initial-scale=1'><title>{esc(t['title'].format(tag=rel['tag']))}</title><style>{CSS}</style></head><body><main>",
           f"<h1>{esc(t['title'].format(tag=rel['tag']))}</h1><p class=sub>{esc(t['sub'].format(date=date))}</p>",
           f"<h2>{t['summary']}</h2><div class=kpis>",
           f"<div class=kpi><b>{esc(t['passed'].format(p=passed, n=len(steps)))}</b><span>{esc(rel['tag'])}</span></div>"]
    kpis = [("first_launch", results.get("first_launch_seconds")),
            ("eval", (by_id.get("evaluate") or {}).get("metrics", {}).get("evaluation_seconds")),
            ("compare", (by_id.get("compare") or {}).get("metrics", {}).get("comparison_seconds")),
            ("stop", (by_id.get("stop") or {}).get("metrics", {}).get("seconds_to_stop"))]
    for key, val in kpis:
        if val is not None:
            label, _, rest = t[key].partition(":")
            out.append(f"<div class=kpi><b>{esc(rest.strip().format(s=val))}</b><span>{esc(label)}</span></div>")
    out.append("</div>")

    out.append(f"<h3>{t['problems']}</h3>")
    if not probs:
        out.append(f"<p class=ok>{t['none']}</p>")
    for p in probs:
        fix = f"<div><span class=muted>{t['fix']}:</span> {esc(p['fix'])}</div>" if p.get("fix") else ""
        out.append(f"<div class=prob><p><span class='pill {esc(p['priority'])}'>{esc(p['priority'])}</span> "
                   f"<b>{esc(p['title'])}</b> <span class=muted>· {esc(p.get('where', ''))} · {esc(p['source'])}</span>"
                   f"<br>{esc(p.get('detail', ''))}</p>{fix}</div>")

    out.append(f"<h2>{t['env']}</h2><table>")
    out.append(f"<tr><th>{t['release']}</th><td>{esc(rel['tag'])} · {esc(t['published'].format(d=rel['published'][:10]))}"
               f" · {rel.get('downloads', '?')} downloads</td></tr>")
    inst = by_id.get("install") or {}
    out.append(f"<tr><th>{t['installer']}</th><td>{esc(rel.get('installer_url') or rel.get('local_installer'))}<br>"
               f"{round(rel['installer_bytes'] / 1e6, 1)} MB · {esc('; '.join(inst.get('notes', [])))}</td></tr>")
    out.append(f"<tr><th>{t['machine']}</th><td>{esc(mach.get('os'))}<br>{esc(mach.get('cpu'))} · {esc(mach.get('gpu'))}"
               f" · {esc(mach.get('ram_gb'))} GB RAM</td></tr>")
    inputs = results.get("inputs") or {}
    out.append(f"<tr><th>{t['inputs']}</th><td>" + "<br>".join(f"<code>{esc(k)}</code> {esc(Path(v).name)} "
               f"<span class=muted>({esc(Path(v).parent.name)})</span>" for k, v in inputs.items()) + "</td></tr></table>")

    out.append(f"<h2>{t['timeline']}</h2><table><tr><th>{t['step']}</th><th>{t['result']}</th><th>{t['time']}</th>"
               f"<th>{t['detail']}</th><th>{t['metrics']}</th></tr>")
    for s in steps:
        checks = "".join(f"<div class={'ok' if c['ok'] else 'bad'}>{'✓' if c['ok'] else '✗'} {esc(c['what'])}"
                         f"{(' <span class=muted>— ' + esc(c['detail']) + '</span>') if c['detail'] and not c['ok'] else ''}"
                         f"</div>" for c in s["checks"])
        notes = "".join(f"<div class=muted>{esc(n)}</div>" for n in s.get("notes", []))
        err = f"<div class=bad>{esc(s['error'])}</div>" if s.get("error") else ""
        out.append(f"<tr><td><b>{esc(s['title'])}</b><br><span class=muted>{esc(s['start'])}</span></td>"
                   f"<td><span class='pill {s['status']}'>{t[s['status']]}</span></td><td>{s['seconds']} s</td>"
                   f"<td>{checks}{notes}{err}</td><td>{metric_text(s.get('metrics', {}))}</td></tr>")
    out.append("</table>")

    out.append(f"<h2>{t['shots']}</h2>")
    for s in steps:
        shots = sorted((folder / "screens").glob(f"*_{s['id']}*.png")) if s.get("screenshot") else []
        named = [folder / s["screenshot"]] if s.get("screenshot") else []
        for path in dict.fromkeys(named + shots):
            if path.is_file():
                out.append(f"<figure><img src='{embed(path)}' alt=''><figcaption>{esc(s['title'])} · {esc(path.name)}"
                           f"</figcaption></figure>")

    out.append(f"<h2>{t['log']}</h2><h3>{t['console']}</h3>")
    console = results.get("console") or []
    out.append("<ul>" + "".join(f"<li><code>{esc(c['type'])}</code> {esc(c['text'])}</li>" for c in console) + "</ul>"
               if console else "<p class=muted>—</p>")
    log = results.get("server_log") or {}
    out.append(f"<h3>{t['server']}</h3><p>{esc(t['server_counts'].format(e=log.get('errors', 0), w=log.get('warnings', 0), t=log.get('tracebacks', 0)))}</p>")
    out.append(f"<h2>{t['untested']}</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in t["untested_list"]) + "</ul>")
    out.append("</main></body></html>")
    return "".join(out)


def to_pdf(page: Path) -> Path | None:
    """Prints the HTML page to a PDF next to it with Microsoft Edge (None when Edge isn't there)."""
    edge = next((p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                             Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.is_file()), None)
    if not edge:
        return None
    import tempfile
    pdf = page.with_suffix(".pdf").resolve()                   # Edge writes nothing for a relative path
    with tempfile.TemporaryDirectory() as profile:              # its own profile: works while Edge is open
        subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", page.resolve().as_uri()],
                       capture_output=True, timeout=180)
    return pdf if pdf.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="A run folder (data/qa/<tag>_<time>)")
    ap.add_argument("--lang", choices=sorted(TEXT), default="en")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    page = args.run / f"report_{args.lang}.html"
    page.write_text(render(args.run, args.lang), encoding="utf-8")
    print(f"HTML: {page}")
    if not args.no_pdf:
        pdf = to_pdf(page)
        print(f"PDF:  {pdf}" if pdf else "PDF:  not made (Microsoft Edge not found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
