"""Problem clips (Export → Problem clips): every moment of a report as a short video, the original and the dub side by
side, with a page ("Problem clips.html", beside the clips folder) that says what's wrong at each, for whoever fixes
the dub.

Each clip plays the moment twice: first with the original's sound, then with the dub's, the side being heard outlined
(any player can play it; a second audio track could be heard only in VLC). Times in a report are the original's, so the
dub's part comes from the same moment on its own timeline (the measured shift, or the shift of its part for a dub cut
differently). ffmpeg runs as an argument list on local files only (`inputs.LOCAL_INPUT`).
"""
import html
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

from dubeval.i18n import TEXT
from dubeval.inputs import FFMPEG_EXE, LOCAL_INPUT, probe

log = logging.getLogger(__name__)

PAD_SEC = 1.5              # seconds shown before and after a moment, so it can be heard in context
MAX_CLIP_SEC = 20.0        # a longer moment (a long missing part) is clipped from its start
MAX_CLIPS = 40             # per dub: the worst first; the rest are in the problem list
HEIGHT = 360               # each side's picture height; two 16:9 sides make a 1280 x 360 clip
GAP = 24                   # white space between the two pictures, so they don't read as one
FPS = 25
HEARD = "0xF5B700"         # the outline and label of the side whose sound plays
NO_VIDEOS = "The videos of this evaluation are gone, so no clips can be made. Run the evaluation again."
CLIP_FAILED = "A problem clip couldn't be made from these videos."

# Fonts for the "Original" / "Dub" labels on the picture: the first found that can write the language. Without one the
# clip has no labels (the page still says which side is which).
_CJK_FONTS = {"win32": ["malgun.ttf"], "darwin": ["/System/Library/Fonts/AppleSDGothicNeo.ttc"],
              "linux": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]}
_LATIN_FONTS = {"win32": ["segoeui.ttf", "arial.ttf"],
                "darwin": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"],
                "linux": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]}


def tr(key: str, lang: str, **kw) -> str:
    """A text in the page's language."""
    text = TEXT[key].get(lang) or TEXT[key]["en"]
    return text.format(**kw) if kw else text


def dub_time(sec: float, offset: float, parts: Optional[list]) -> float:
    """A moment on the original's timeline → the same moment in the dub file (as the review's players do)."""
    if parts:
        part = next((p for p in parts if p["start"] <= sec < p["end"]), None) or \
            min(parts, key=lambda p: min(abs(sec - p["start"]), abs(sec - p["end"])))
        return sec + part["offset_sec"]
    return sec + (offset or 0.0)


def plan(rep: dict, duration: Optional[float]) -> tuple[list[dict], int]:
    """The moments to clip, in time order: each with its window and findings (lead first). At most MAX_CLIPS, the
    worst kept; returns them and how many were left out."""
    intervals = rep.get("problem_intervals") or []
    moments = rep.get("moments") or [{"start": iv["start"], "end": iv["end"], "severity": iv["severity"],
                                      "intervals": [i]} for i, iv in enumerate(intervals)]
    rank = {"poor": 0, "check": 1}
    chosen = sorted(range(len(moments)), key=lambda i: (rank.get(moments[i]["severity"], 2), moments[i]["start"]))
    kept = sorted(chosen[:MAX_CLIPS])
    out = []
    for n in kept:
        m = moments[n]
        start = max(0.0, m["start"] - PAD_SEC)
        end = m["end"] + PAD_SEC
        if duration:
            end = min(end, duration)
        cut = end - start > MAX_CLIP_SEC
        out.append({"number": n + 1, "start": m["start"], "end": m["end"], "severity": m["severity"],
                    "from": round(start, 2), "length": round(min(end - start, MAX_CLIP_SEC), 2), "cut": cut,
                    "findings": [intervals[i] for i in m["intervals"] if 0 <= i < len(intervals)]})
    return out, len(moments) - len(kept)


def _font(lang: str) -> Optional[tuple[str, bool]]:
    """(font file, writes Korean) for the labels, or None when this computer has none of the known ones."""
    platform = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for names, cjk in ((_CJK_FONTS[platform], True), (_LATIN_FONTS[platform], False)):
        for name in names:
            path = fonts_dir / name if platform == "win32" else Path(name)
            if path.is_file() and "'" not in str(path):
                return str(path), cjk
    return None


def _escape(value: str) -> str:
    """A value for a drawtext option inside single quotes: a Windows path's colon and backslashes."""
    return value.replace("\\", "/").replace(":", "\\:")


def _labels(lang: str) -> Optional[tuple[str, str, str]]:
    """(font, "Original", "Dub") in the page's language, or in English when the font can't write it; None without
    a font."""
    found = _font(lang)
    if found is None:
        return None
    font, cjk = found
    use = lang if cjk or lang != "ko" else "en"
    return font, tr("w.clips.original_label", use), tr("w.clips.dub_label", use)


def _side(index: int, has_video: bool, length: str, name: str) -> str:
    """One side's picture, scaled to HEIGHT and exactly length seconds (a dub that ends early holds its last frame),
    split in two: [name a] for the pass with the original's sound, [name b] for the dub's."""
    scaled = f"scale=-2:{HEIGHT},setsar=1,fps={FPS}," if has_video else ""
    return (f"[{index}:v]{scaled}format=yuv420p,tpad=stop_mode=clone:stop_duration={length},trim=duration={length},"
            f"setpts=PTS-STARTPTS,split[{name}a][{name}b]")


def _dressed(src: str, heard: bool, label: Optional[str], font: Optional[str], gap: bool) -> str:
    """One side in one pass: outlined, and its label marked, while its sound plays; the left side gets the gap."""
    steps = [f"drawbox=x=0:y=0:w=iw:h=ih:color={HEARD}:t=6"] if heard else []
    if label and font:
        look = f"fontcolor=black:boxcolor={HEARD}@0.95" if heard else "fontcolor=white:boxcolor=black@0.55"
        steps.append(f"drawtext=fontfile='{_escape(font)}':text='{_escape(label)}':fontsize=22:{look}"
                     f":box=1:boxborderw=6:x=14:y=14")
    if gap:
        steps.append(f"pad=iw+{GAP}:ih:0:0:white")
    return f"[{src}]{','.join(steps) or 'null'}[{src}x]"


def make_clip(original: str, dub: str, start: float, dub_start: float, length: float, out: Path,
              labels: Optional[tuple[str, str, str]], videos: tuple[bool, bool]) -> None:
    """One side-by-side clip of length seconds (the original from start, the dub from dub_start), played twice: with
    the original's sound, then with the dub's. Raises RuntimeError with ffmpeg's last lines when it fails."""
    cmd = [FFMPEG_EXE, "-nostdin", "-y", "-hide_banner", "-loglevel", "error"]
    for path, at in ((original, start), (dub, max(0.0, dub_start))):
        cmd += ["-ss", f"{at:.3f}", "-t", f"{length:.3f}", *LOCAL_INPUT, "-i", path]
    for has_video in videos:                        # a side without a picture (an audio file) shows black
        if not has_video:
            cmd += ["-f", "lavfi", "-t", f"{length:.3f}", "-i", f"color=c=black:s=640x{HEIGHT}:r={FPS}"]
    # the black pictures are inputs 2 (and 3), in the order of the sides that need one
    picture = [0 if videos[0] else 2, 1 if videos[1] else (2 if videos[0] else 3)]
    font, left, right = labels if labels else (None, None, None)
    sec = f"{length:.3f}"
    sound = f"aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={sec},asetpts=PTS-STARTPTS"
    graph = ";".join([
        _side(picture[0], videos[0], sec, "l"), _side(picture[1], videos[1], sec, "r"),
        _dressed("la", True, left, font, True), _dressed("ra", False, right, font, False),
        _dressed("lb", False, left, font, True), _dressed("rb", True, right, font, False),
        "[lax][rax]hstack=inputs=2[va]", "[lbx][rbx]hstack=inputs=2[vb]",
        f"[0:a]{sound}[a0]", f"[1:a]{sound}[a1]",
        "[va][a0][vb][a1]concat=n=2:v=1:a=1[v][a]"])
    cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace").strip().splitlines()[-2:]
        raise RuntimeError(" | ".join(tail) or f"ffmpeg exited with {proc.returncode}")


def _clock(sec: float) -> str:
    """mm:ss.s, as the app writes times."""
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m):02d}:{s:04.1f}"


def _capital(text: str) -> str:
    """A category's name as a heading: its first letter capital (they're written to stand mid-sentence)."""
    return text[:1].upper() + text[1:]


def _file_name(prefix: str, clip: dict) -> str:
    """The clip's file name: number, time and what's wrong, without what file names can't hold."""
    lead = clip["findings"][0] if clip["findings"] else {}
    what = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", _capital(lead.get("category_label") or "")).strip(" .")
    m, s = divmod(int(clip["start"]), 60)
    return re.sub(r"\s+", " ", f"{prefix}{clip['number']:02d} {m:02d}m{s:02d}s {what}").strip()[:90] + ".mp4"


def page_name(lang: str) -> str:
    """The clips page's file name in the page's language ("Problem clips.html")."""
    return re.sub(r'[<>:"/\\|?*]+', " ", tr("w.exp.clips", lang)).strip() + ".html"


def write_clips(dubs: list[dict], folder: Path, lang: str, title: Optional[str],
                on_clip: Optional[Callable[[int, int], None]] = None) -> list[Path]:
    """Writes every dub's clips into folder/clips and the page that goes with them into folder (page_name); returns
    the page, then the clips.

    dubs: [{"label": "A · name" or None, "report": the report, "original": file, "dub": file, "offset": shift,
    "parts": parts or None, "general": [(check, level label, message), ...] the problems about the whole dub}].
    """
    clip_dir = folder / "clips"
    clip_dir.mkdir(parents=True, exist_ok=True)
    labels = _labels(lang)
    plans = []
    for n, d in enumerate(dubs):
        for path in (d["original"], d["dub"]):
            if not path or not Path(path).is_file():
                raise FileNotFoundError(NO_VIDEOS)
        clips, left_out = plan(d["report"], (d["report"].get("project") or {}).get("duration_sec"))
        plans.append((d, clips, left_out, f"{'ABCDEFGH'[n]}-" if len(dubs) > 1 else ""))
    total = sum(len(c) for _, c, _, _ in plans)
    written, done = [], 0
    for d, clips, _, prefix in plans:
        videos = (probe(d["original"])["has_video"], probe(d["dub"])["has_video"])
        for clip in clips:
            clip["file"] = _file_name(prefix, clip)
            out = clip_dir / clip["file"]
            start = clip["from"]
            try:
                make_clip(d["original"], d["dub"], start, dub_time(start, d["offset"], d["parts"]), clip["length"], out,
                          labels, videos)
            except RuntimeError as e:
                if labels is None:
                    log.warning("Clip %s failed: %s", clip["file"], e)
                    raise RuntimeError(CLIP_FAILED) from e
                log.info("Clip %s failed with labels, trying without: %s", clip["file"], e)
                labels = None                           # e.g. a font ffmpeg can't read: no labels from here on
                try:
                    make_clip(d["original"], d["dub"], start, dub_time(start, d["offset"], d["parts"]), clip["length"],
                              out, None, videos)
                except RuntimeError as e2:
                    log.warning("Clip %s failed: %s", clip["file"], e2)
                    raise RuntimeError(CLIP_FAILED) from e2
            clip["labelled"] = labels is not None
            written.append(out)
            done += 1
            if on_clip:
                on_clip(done, total)
    index = folder / page_name(lang)
    index.write_text(render_index(plans, lang, title), encoding="utf-8")
    return [index, *written]


def render_index(plans: list, lang: str, title: Optional[str]) -> str:
    """The page that goes with the clips: for each dub, what's about the whole dub, then each moment's clip and what
    was found there. No script; the clips are beside it."""
    e = html.escape
    out = [f"<!doctype html><html lang='{e(lang)}'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
           f"<title>{e(tr('w.clips.title', lang, title=title or 'DubEval'))}</title><style>{_CSS}</style></head><body>",
           f"<h1>{e(tr('w.clips.title', lang, title=title or 'DubEval'))}</h1>",
           f"<p class='how'>{e(tr('w.clips.how', lang))}</p>"]
    for d, clips, left_out, _ in plans:
        rep = d["report"]
        overall = rep.get("overall") or {}
        out.append("<section class='dub'>")
        if d.get("label"):
            out.append(f"<h2>{e(d['label'])}</h2>")
        out.append(f"<p><span class='badge {e(overall.get('level') or '')}'>{e(overall.get('label') or '')}</span> "
                   f"{e(overall.get('summary') or '')}</p>")
        if d.get("general"):
            out.append(f"<h3>{e(tr('w.clips.whole', lang))}</h3><ul class='general'>")
            out += [f"<li><b>{e(check)}</b> <span class='level'>{e(level)}</span> {e(_for_page(message, lang))}</li>"
                    for check, level, message in d["general"]]
            out.append("</ul>")
        if not clips:
            out.append(f"<p class='muted'>{e(tr('w.clips.none', lang))}</p>")
        for clip in clips:
            lead, *rest = clip["findings"] or [{}]
            sev = clip["severity"]
            out.append(f"<article class='moment {e(sev)}'><h3><span class='num'>{clip['number']}</span> "
                       f"{_clock(clip['start'])} – {_clock(clip['end'])} "
                       f"<span class='badge {e(sev)}'>{e(tr(f'badge.{sev}', lang) if f'badge.{sev}' in TEXT else sev)}"
                       f"</span> {e(_capital(lead.get('category_label') or lead.get('check_label') or ''))}</h3>")
            if not clip.get("labelled"):              # the picture has no labels: say which side is which above it
                out.append(f"<div class='sides'><span>{e(tr('w.clips.original_label', lang))}</span>"
                           f"<span>{e(tr('w.clips.dub_label', lang))}</span></div>")
            out.append(f"<video controls preload='metadata' src='{e(quote('clips/' + clip['file']), quote=True)}'>"
                       "</video>")
            if clip["cut"]:
                out.append(f"<p class='muted'>{e(tr('w.clips.cut', lang, sec=int(MAX_CLIP_SEC)))}</p>")
            out.append(_finding(lead, lang))
            if rest:
                out.append(f"<p class='also'>{e(tr('w.clips.also', lang))}</p><ul>")
                out += [f"<li>{e(f.get('check_label') or '')}: {e(f.get('description') or '')}</li>" for f in rest]
                out.append("</ul>")
            out.append("</article>")
        if left_out:
            key = "w.clips.more_one" if left_out == 1 else "w.clips.more_many"
            out.append(f"<p class='muted'>{e(tr(key, lang, n=left_out))}</p>")
        out.append("</section>")
    out.append("<footer>DubEval</footer></body></html>")
    return "\n".join(out)


# A report sentence ends "...listed under Things to check": a screen of the app, which whoever gets the clips doesn't
# have. On this page it points at the clips below instead (the words before the screen's name, per language).
_THINGS_BEFORE = {"en": "under ", "ko": "", "pt": "em ", "es": "en "}


def _for_page(text: str, lang: str) -> str:
    """A report sentence for the clips page: a pointer to the app's Things to check points at the clips below."""
    things, below = tr("r.label.things", lang), tr("w.clips.below", lang)
    return text.replace(_THINGS_BEFORE.get(lang, "") + things, below).replace(things, below)


def _finding(f: dict, lang: str) -> str:
    """What a moment's lead finding says, in parts: the problem, what each track says, a better translation."""
    e = html.escape
    rows = [f"<p class='problem'>{e(f.get('problem') or f.get('description') or '')}</p>"]
    for key, text in (("w.clips.original_says", f.get("original")), ("w.clips.dub_says", f.get("dubbed")),
                      ("w.clips.suggested", f.get("suggestion"))):
        if text:
            rows.append(f"<p class='said'><b>{e(tr(key, lang))}</b> {e(text)}</p>")
    return "".join(rows)


_CSS = """
body{font:15px/1.5 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;max-width:1340px;margin:24px auto;
padding:0 16px;color:#1d2330;background:#fff}
h1{font-size:22px;margin:0 0 6px}h2{font-size:18px;margin:28px 0 6px}h3{font-size:15px;margin:0 0 8px}
.how{color:#4a5263;margin:0 0 18px}.muted{color:#6b7385}
.moment{border:1px solid #dde1ea;border-left:5px solid #e0a020;border-radius:8px;padding:14px 16px;margin:14px 0}
.moment.poor{border-left-color:#d33c3c}
.num{display:inline-block;min-width:22px;padding:0 6px;border-radius:11px;background:#1d2330;color:#fff;text-align:center}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;background:#fdf0d5;
color:#7a5300}.badge.poor{background:#fbe1e1;color:#9b1c1c}.badge.good{background:#ddf3e4;color:#17602f}
.sides{display:flex;max-width:1280px;font-size:12px;color:#6b7385}.sides span{flex:1}
video{width:100%;max-width:1280px;background:#fff;display:block}
.problem{font-weight:600;margin:10px 0 4px}.said{margin:2px 0}.also{margin:10px 0 2px;color:#4a5263}
.general .level{color:#6b7385;font-size:13px}footer{color:#9aa1b0;font-size:12px;margin:30px 0}
"""
