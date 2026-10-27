"""The pipeline: evaluate the dub behind a Perso share link, or compare the dubs behind two links.

Fetch the shared project, download the original and the dub (cached per link), measure (Whisper results cached
per link too), check the translation, build the report, and save the report files: report.json / .html / .txt
for one dub; comparison.* plus report_A.* and report_B.* for two.
"""
import os
import json
import time
import uuid
import shutil
import tempfile
import hashlib
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv

from dubeval.batch import agreement, render_batch_text, summary_row, to_csv
from dubeval import history
from dubeval.paths import DATA_DIR
from dubeval.compare import LABELS, build_ranking, render_comparison_html, render_comparison_text
from dubeval import asr, inputs, meaning, pairing, schema, speaker
from dubeval.version import TOOL_VERSION
from dubeval.evaluate import (run_full_evaluation, DEFAULT_WHISPER_MODEL, CACHE_VERSION, base_lang, load_both,
                              detect_language, extract_audio, get_whisper_model, load_audio, FFMPEG_EXE,
                              SAMPLE_RATE)
from dubeval.jobs import Cancelled, Progress
from dubeval.perso_api import PersoError, download_media, get_shared_project, parse_share_url
from dubeval.report import build_report, render_html, render_text
from dubeval.translation_judge import DUB_TYPES, judge_fingerprint, judge_provider, judge_translation, not_measured

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# API keys: the project's .env (development; variables already set win), then the data folder's, where the Settings
# page saves keys (dubeval/settings.py): a key saved there wins over one set elsewhere.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(DATA_DIR / ".env", override=True)

OUTPUT_DIR = DATA_DIR / "output"
RUNS_DIR = OUTPUT_DIR / "runs"
RESULTS_FILE = OUTPUT_DIR / "results.json"
CACHE_DIR = DATA_DIR / "cache"
MAX_KEPT_RUNS = int(os.getenv("MAX_KEPT_RUNS", "0"))   # 0: the app's evaluations stay until the person deletes them
MAX_CACHED_LINKS = int(os.getenv("MAX_CACHED_LINKS", "20"))

DIFFERENT_VIDEOS = ("These look like different videos: their pictures don't match, so comparing them would be "
                    "meaningless. Check that you chose the right files, or run again with --allow-different-videos "
                    "if you're sure they belong together.")
MIN_APPLIED_OFFSET = 0.1           # shifts smaller than this (seconds) are left alone: within measuring noise
LANGUAGE_GUESS_OK = 0.8            # a detected dub language below this confidence gets a warning in the report
BAD_DUB_TYPE = "The dub type must be ai_clone, ai_stock or human."
TOO_MANY_DUB_OPTIONS = "There are more dub settings than dubs. Give one per dub, in order."
NO_DUB_LANGUAGE = "The dub's language couldn't be detected. Pass it with --target-lang (for example ko)."
NO_ORIGINAL = ("This share link has no original video. Pass the original with --original <file or URL> "
               "(command line), then try again.")


def load_results() -> Optional[dict]:
    """Loads the most recent evaluation, or None if there is none (or it is unreadable)."""
    path = Path(RESULTS_FILE)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Ignoring unreadable %s: %s", path, e)
        return None


def _write_json(path: Path, data) -> None:
    """Writes JSON atomically so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def save_results(results: dict) -> None:
    """Saves the latest evaluation for the app's "Show last result"."""
    _write_json(Path(RESULTS_FILE), results)


def _prune(folder: Path, keep: int, protect: Optional[Path] = None) -> None:
    """Deletes all but the newest `keep` subfolders of folder, never one whose files a kept evaluation or a draft
    uses (dubeval/library.py): the Evaluations list still plays them."""
    if not folder.is_dir():
        return
    dirs = sorted((d for d in folder.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime, reverse=True)
    old = [d for d in dirs[keep:] if protect is None or d.resolve() != protect.resolve()]
    if not old:
        return
    from dubeval import library
    used = library.referenced_inputs()
    for d in old:
        if not library.protects(d, used):
            shutil.rmtree(d, ignore_errors=True)


def prune_old_runs(keep: int = MAX_KEPT_RUNS, protect: Optional[str] = None) -> None:
    """Deletes all but the newest `keep` run directories; keep 0 (the default) keeps them all."""
    if keep > 0:
        _prune(Path(RUNS_DIR), keep, Path(protect) if protect else None)


def new_run_dir() -> tuple[str, str]:
    """A fresh (run_id, run_dir) pair; the directory is not created yet."""
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}"
    return run_id, str(Path(RUNS_DIR) / run_id)


def _short_hash(text: str) -> str:
    """A short, file-name-safe fingerprint of text."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class JsonCache:
    """A small key -> JSON value store in one file, used to keep Whisper results per share link."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def get(self, key: str, default=None):
        """The cached value for key, or default."""
        return self.data.get(key, default)

    def __setitem__(self, key: str, value) -> None:
        self.data[key] = value
        _write_json(self.path, self.data)


def _link_cache_dir(token: str) -> Path:
    """This share link's cache folder (videos and Whisper results); marks it as recently used."""
    folder = Path(CACHE_DIR) / _short_hash(token)
    folder.mkdir(parents=True, exist_ok=True)
    os.utime(folder)
    return folder


def _cached_download(remote: str, folder: Path, prefix: str, session, sleep, label: str) -> str:
    """Downloads a media file into the cache folder unless an earlier run already did."""
    target = folder / f"{prefix}_{_short_hash(remote)}.mp4"
    if target.exists() and target.stat().st_size > 0:
        log.info("Using cached %s: %s", label, target.name)
        return str(target)
    return download_media(remote, str(target), session=session, sleep=sleep, label=label)


def _resolve_original(original: str, folder: Path, session, sleep) -> str:
    """The --original video: a local file as is, or a URL downloaded into the cache."""
    text = original.strip()
    if text.lower().startswith(("http://", "https://")):
        return _cached_download(text, folder, "original_override", session, sleep, "original video")
    path = Path(text).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"The original video file doesn't exist: {path}")
    return str(path.resolve())


def save_report_files(results: dict, out_dir, name: str = "report", absolute_videos: bool = False) -> dict:
    """Writes <name>.json, <name>.html and <name>.txt into out_dir; returns their paths.

    absolute_videos: the HTML plays the videos from where they are (file:// links) instead of relative to out_dir, for a
    copy that's saved somewhere else (Export)."""
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    rep = results["report"]
    p = results.get("pipeline", {})
    files = {"json": folder / f"{name}.json", "html": folder / f"{name}.html", "text": folder / f"{name}.txt"}
    _write_json(files["json"], schema.wrap(rep, {k: v for k, v in results.items() if k != "report"}, TOOL_VERSION))
    files["html"].write_text(render_html(rep, results, _video_src(p.get("input_video_path"), folder, absolute_videos),
                                         _video_src(p.get("dubbed_video_path"), folder, absolute_videos)),
                             encoding="utf-8")
    files["text"].write_text(render_text(rep), encoding="utf-8")
    return {k: str(v) for k, v in files.items()}


def _video_src(path: Optional[str], folder: Path, absolute: bool = False) -> str:
    """How an HTML file in folder refers to a video: a relative path, or a file:// URI (asked for, or another drive)."""
    if not path or not Path(path).exists():
        return ""
    if absolute:
        return Path(path).resolve().as_uri()
    try:
        return Path(os.path.relpath(path, folder)).as_posix()
    except ValueError:                       # Windows: the video is on another drive
        return Path(path).resolve().as_uri()


def file_stages() -> list[str]:
    """The progress stages of a file or link evaluation."""
    return ["prepare", "evaluate"]


def share_stages() -> list[str]:
    """The progress stages of a share-link evaluation."""
    return ["fetch", "download", "evaluate"]


def compare_stages(n: int = 2) -> list[str]:
    """The progress stages of a comparison of n share links: one per dub, then the comparison."""
    return [f"dub_{c.lower()}" for c in LABELS[:n]] + ["compare"]


def evaluate_share(
    share_url: str,
    notify: Callable[..., None],
    check_cancel: Callable[[], None],
    ground_truth_text: Optional[str] = None,
    whisper_model_name: str = DEFAULT_WHISPER_MODEL,
    include_lipsync: Optional[bool] = None,
    use_translation_judge: bool = True,
    original: Optional[str] = None,
    use_cache: bool = True,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
    original_subtitles: Optional[str] = None,
    dub_subtitles: Optional[str] = None,
    dub_type: Optional[str] = None,
) -> dict:
    """Fetches, downloads (cached), measures and checks the translation of one share link; returns the results.

    The lip-synced video is evaluated when the project has one, because that is the version viewers get, and only
    then is lip movement measured (include_lipsync=None); True/False forces it on or off. original is used when
    the share link has no original video (a file path or a URL). Subtitle files (Perso's public share has none) and
    the dub type work as for files (evaluate_files).
    """
    if dub_type is not None and dub_type not in DUB_TYPES:
        raise ValueError(BAD_DUB_TYPE)
    original_subs = inputs.read_subtitles(original_subtitles, "original") if original_subtitles else None
    dub_subs = inputs.read_subtitles(dub_subtitles, "dub") if dub_subtitles else None
    token = parse_share_url(share_url)
    notify("fetch", "Reading the shared Perso project...", 0.3)
    project = get_shared_project(token, session=session, sleep=sleep)
    check_cancel()

    target, source = project.get("targetLanguage") or {}, project.get("sourceLanguage") or {}
    tag = target.get("languageTag")
    target_id = tag if tag and tag != "default" else target.get("code", "")
    if not target.get("code"):
        raise PersoError("The shared project doesn't say which language it was dubbed into.")
    use_lipsync = bool(project.get("isLipSync") and project.get("lipSyncFileUrl"))
    measure_lips = use_lipsync if include_lipsync is None else include_lipsync
    dubbed_remote = project["lipSyncFileUrl"] if use_lipsync else project["translatedFileUrl"]
    if not project.get("originalFileUrl") and not original:
        raise PersoError(NO_ORIGINAL)

    folder = _link_cache_dir(token)
    if not use_cache:
        for f in folder.glob("*"):
            f.unlink()
    notify("download", "Downloading the original video...", 0.1)
    if project.get("originalFileUrl"):
        original_path = _cached_download(project["originalFileUrl"], folder, "original", session, sleep, "original video")
    else:
        original_path = _resolve_original(original, folder, session, sleep)
    check_cancel()
    notify("download", "Downloading the dubbed video...", 0.55)
    dubbed_path = _cached_download(dubbed_remote, folder, f"dubbed_{target_id}", session, sleep, "dubbed video")
    _prune(Path(CACHE_DIR), MAX_CACHED_LINKS, protect=folder)
    check_cancel()

    source_code = source.get("code") if source.get("code") not in (None, "", "auto") else None
    cache = JsonCache(folder / "whisper_cache.json")
    notify("download", "Reading the sound of both videos...", 0.85)
    audio = _load_both(original_path, dubbed_path)              # once, for the check and the evaluation
    notify("download", "Checking that both files are the same video...", 0.9)
    pair = pair_videos(original_path, dubbed_path, cache, audio,
                       lambda message, fraction: notify("download", message, 0.9 + 0.1 * fraction))
    check_cancel()
    eval_results = run_full_evaluation(
        original_video_path=original_path,
        dubbed_video_path=dubbed_path,
        ground_truth_text=(ground_truth_text or "").strip(),
        target_lang=target["code"],
        whisper_model_name=whisper_model_name,
        on_step=lambda msg, frac: notify("evaluate", msg, frac * 0.95),
        include_lipsync=measure_lips,
        source_lang=source_code,
        cache=cache,
        dub_offset_sec=applied_offset(pair),
        dub_parts=applied_parts(pair),
        audio=audio,
        check=check_cancel,
    )
    eval_results["pairing"] = {**pair, "applied_offset_sec": applied_offset(pair),
                               "applied_parts": bool(applied_parts(pair))}
    check_cancel()
    eval_results["pipeline"] = {
        "run_id": f"{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "execution_mode": "Perso share link" + (" (lip-synced video)" if use_lipsync else ""),
        "input_video_path": original_path,
        "dubbed_video_path": dubbed_path,
        "target_language_name": target.get("name") or target_id,
        "target_language_code": target["code"],
        "target_language_id": target_id,
        "share": {
            "share_url": share_url.strip(),
            "seq": project.get("seq"),
            "title": project.get("title"),
            "source_language_name": source.get("name"),
            "source_language_code": source.get("code"),
            "target_language_name": target.get("name"),
            "is_lipsync": bool(project.get("isLipSync")),
            "evaluated_video": "lip-synced" if use_lipsync else "dubbed",
            "duration_ms": project.get("durationMs"),
            "created": project.get("createDate"),
            "original_from": "share link" if project.get("originalFileUrl") else "--original",
            "dub_type": dub_type,
            "subtitles": {"original": len(original_subs) if original_subs else None,
                          "dub": len(dub_subs) if dub_subs else None},
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "logs": "Read from a Perso share link; videos and speech recognition are cached per link. No credits were spent.",
    }
    eval_results["subtitles"] = {"original": original_subs, "dub": dub_subs}
    eval_results["subtitle_match"] = subtitle_match(eval_results)
    apply_dub_type(eval_results, dub_type)
    judge_cache = JsonCache(folder / "judge_cache.json")
    _abandonable(lambda: check_meaning_screen(eval_results, notify, cache=judge_cache), check_cancel)
    _abandonable(lambda: check_translation(eval_results, use_translation_judge, notify, cache=judge_cache), check_cancel)
    return eval_results


def _texts(segments: list[dict], indexes: list[int]) -> str:
    """The text of the given segments, in order."""
    return " ".join(segments[i]["text"] for i in indexes if i < len(segments) and segments[i].get("text")).strip()


def _cues(cues: Optional[list[dict]], start: float, end: float, shift: float = 0.0) -> str:
    """The subtitle text overlapping [start, end] on the original's timeline (cue times moved by -shift)."""
    picked = [c["text"] for c in cues or [] if c["start"] - shift < end and c["end"] - shift > start]
    return " ".join(picked).strip()


def judge_lines(results: dict) -> list[dict]:
    """The speech of both sides line by line, for the meaning check and the screen: each matched line
    (segment_alignment) with what each side said, then speech heard on one side only. Subtitle files, when given,
    add what each side was meant to say. Times are the original's."""
    sr, sa = results.get("speech_recognition") or {}, results.get("segment_alignment") or {}
    orig, dub = sr.get("original_segments") or [], sr.get("dubbed_segments") or []
    subs = results.get("subtitles") or {}
    shift = (results.get("pairing") or {}).get("applied_offset_sec") or 0.0
    lines = []
    for ln in sa.get("lines") or []:
        lines.append({"n": ln["n"], "start": ln["start"], "end": ln["end"],
                      "original": _texts(orig, ln["original"]), "dub": _texts(dub, ln["dub"])})
    n = len(lines)
    for i in sa.get("unmatched_original") or []:
        if i < len(orig) and orig[i].get("text"):
            n += 1
            lines.append({"n": n, "start": orig[i]["start"], "end": orig[i]["end"], "original": orig[i]["text"], "dub": ""})
    for j in sa.get("unmatched_dub") or []:
        if j < len(dub) and dub[j].get("text"):
            n += 1
            lines.append({"n": n, "start": dub[j]["start"], "end": dub[j]["end"], "original": "", "dub": dub[j]["text"]})
    for ln in lines:
        if subs.get("original"):
            ln["original_script"] = _cues(subs["original"], ln["start"], ln["end"])
        if subs.get("dub"):
            ln["dub_script"] = _cues(subs["dub"], ln["start"], ln["end"], shift)
    return sorted(lines, key=lambda ln: ln["start"])


def _speech_unrecognized(results: dict) -> bool:
    """Whether recognition couldn't make out the dub's language (report.speech_problem "unrecognized")."""
    from dubeval.report import speech_problem
    try:
        return (speech_problem(results) or {}).get("kind") == "unrecognized"
    except (KeyError, TypeError):                       # results without the parts the rule reads
        return False


def check_translation(results: dict, enabled, notify: Callable[..., None], cache=None) -> None:
    """Adds the translation check to results; any failure becomes a not-measured result, never an error.

    enabled: False (off), True (the checker DUBEVAL_JUDGE picks, auto by default) or a checker's name (claude,
    gemini, openai, ollama), as chosen on the start page.

    The judge reads the speech line by line (judge_lines) and the dub type (human dubs may adapt freely). A
    successful review is cached (when cache is given) under a fingerprint of everything it was shown, the prompt
    and the models, so a rerun gets the same answer without another API call. Failures are never cached.
    """
    if not enabled:
        results["translation_judge"] = not_measured("r.judge.off")
        return
    if _speech_unrecognized(results):
        # The dub's words are recognition noise (e.g. Uzbek heard as Kazakh): judging them would only grade the noise.
        results["translation_judge"] = not_measured("r.judge.unrecognized")
        return
    notify("evaluate", "Checking the translation...", 0.96)
    p = results["pipeline"]
    sr, meta, share = results["speech_recognition"], results["metadata"], (p.get("input") or p.get("share") or {})
    name = lambda label, code: f"{label} ({code})" if label and code else (label or code or "unknown")
    args = (sr.get("original_segments") or [], sr.get("dubbed_segments") or [],
            name(share.get("source_language_name"), meta.get("detected_source_language")),
            name(share.get("target_language_name"), meta.get("target_language")))
    lines, dub_type = judge_lines(results), share.get("dub_type")
    title = p.get("custom_title") or share.get("title")          # the rubric's description of the video
    named = enabled if isinstance(enabled, str) else None
    key = _short_hash(json.dumps([args, lines, dub_type, title, judge_fingerprint(named)], ensure_ascii=False,
                                 sort_keys=True))
    cached = cache.get(key) if cache is not None else None
    if cached:
        results["translation_judge"] = {**cached, "cached": True}
        return
    if (named or judge_provider()) == "ollama":
        # A local judge shares the GPU: free the recognizer and the sentence model first, or the judge spills onto
        # the CPU and takes many minutes instead of seconds.
        asr.unload()
        meaning.unload()
    results["translation_judge"] = judge_translation(*args, lines=lines, dub_type=dub_type, provider=named,
                                                     description=title)
    if cache is not None and results["translation_judge"].get("measured"):
        cache[key] = results["translation_judge"]


def check_meaning_screen(results: dict, notify: Callable[..., None], cache=None) -> None:
    """Adds the offline meaning screen (dubeval/meaning.py) to results, cached like the judge; never fails."""
    if _speech_unrecognized(results):
        results["meaning_screen"] = meaning.not_measured("r.screen.unrecognized")
        return
    lines = judge_lines(results)
    key = _short_hash(json.dumps(["screen", meaning.model_name(), lines], ensure_ascii=False, sort_keys=True))
    cached = cache.get(key) if cache is not None else None
    if cached:
        results["meaning_screen"] = cached
        return
    notify("evaluate", "Comparing the meaning of each line...", 0.95)
    results["meaning_screen"] = meaning.screen(lines)
    if cache is not None and results["meaning_screen"].get("measured"):
        cache[key] = results["meaning_screen"]


def subtitle_match(results: dict) -> dict:
    """How closely each side's transcript matches its subtitle file (evaluate.subtitle_agreement); None per side
    without a file. The report uses the dub's to confirm its language when recognition can't tell (Uzbek is often
    heard as Kazakh)."""
    from dubeval.evaluate import subtitle_agreement
    sr, subs = results.get("speech_recognition") or {}, results.get("subtitles") or {}
    return {"original": subtitle_agreement(sr.get("original_segments"), subs.get("original")),
            "dub": subtitle_agreement(sr.get("dubbed_segments"), subs.get("dub"))}


def apply_dub_type(results: dict, dub_type: Optional[str]) -> None:
    """Human and stock-voice dubs use another voice on purpose: voice similarity isn't compared for them."""
    if dub_type == "human":
        results["voice_similarity"] = speaker.not_measured("r.vs.not_compared_human")
    elif dub_type == "ai_stock":
        results["voice_similarity"] = speaker.not_measured("r.vs.not_compared_stock")


def _notifier(report: Optional[Callable[[Progress], None]]):
    """A notify(stage, message, fraction) function that forwards to report, if anyone is listening."""
    def notify(stage: str, message: str, fraction: float = 0.0):
        """Sends a progress update to the UI."""
        if report:
            report(Progress(stage=stage, message=message, stage_fraction=fraction))
    return notify


def _abandonable(work: Callable[[], None], check_cancel: Callable[[], None], poll_sec: float = 0.2) -> None:
    """Runs work (a translation check: a web request that may take a minute) in its own thread and waits for it, but
    gives up at once when the run is stopped: Stop shouldn't wait for an answer nobody will read. An abandoned call
    ends on its own; its result is dropped with the stopped run. Errors in work are raised here."""
    check_cancel()
    failed: list[BaseException] = []

    def target():
        try:
            work()
        except BaseException as e:            # handed to the waiting thread
            failed.append(e)
    worker = threading.Thread(target=target, name="judge", daemon=True)
    worker.start()
    while worker.is_alive():
        worker.join(poll_sec)
        check_cancel()
    if failed:
        raise failed[0]
    check_cancel()


def _canceller(cancel_event: Optional[threading.Event]):
    """A check_cancel() function that stops the run once the user pressed Stop waiting."""
    def check_cancel():
        """Raises Cancelled if the user stopped the job."""
        if cancel_event is not None and cancel_event.is_set():
            raise Cancelled("Stopped by user.")
    return check_cancel


def run_share_evaluation(
    share_url: str,
    ground_truth_text: Optional[str] = None,
    report: Optional[Callable[[Progress], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    whisper_model_name: str = DEFAULT_WHISPER_MODEL,
    include_lipsync: Optional[bool] = None,
    use_translation_judge: bool = True,
    report_lang: str = "en",
    out_dir: Optional[str] = None,
    original: Optional[str] = None,
    use_cache: bool = True,
    history_mode: str = "single",
    session=None,
    sleep: Callable[[float], None] = time.sleep,
    **options,
) -> dict:
    """Evaluates the dub behind a Perso share link and saves report.json / .html / .txt.

    options: evaluate_share's subtitle files and dub type.

    Needs no Perso API key and spends no credits. The files go to out_dir when given (the CLI's --out),
    otherwise to a new run folder under data/output/runs/. results.json keeps the latest run for the app.
    """
    notify, check_cancel = _notifier(report), _canceller(cancel_event)
    results = evaluate_share(share_url, notify, check_cancel, ground_truth_text=ground_truth_text,
                             whisper_model_name=whisper_model_name, include_lipsync=include_lipsync,
                             use_translation_judge=use_translation_judge, original=original, use_cache=use_cache,
                             session=session, sleep=sleep, **options)
    check_cancel()                               # stopped at the very end: still nothing is written or recorded
    notify("evaluate", "Writing the report...", 0.99)
    results["report"] = build_report(results, report_lang)
    if out_dir is None:
        run_id, folder = new_run_dir()
        results["pipeline"]["run_id"] = run_id
        prune_old_runs(protect=folder)
    else:
        folder = out_dir
    results["pipeline"]["report_files"] = save_report_files(results, folder)
    save_results(results)
    history.record(results, history_mode)
    return results


def _language_name(code: Optional[str]) -> Optional[str]:
    """A readable name for a language code ("ko" -> "Korean"), or the code itself."""
    if not code:
        return None
    return asr.language_names().get(base_lang(code), code).title()


GENERIC_NAMES = {"dub", "dubbed", "input", "output", "original", "source", "video", "audio", "final", "result"}


def _title(spec: str) -> str:
    """A title for the report: the file name, or its folder's name when the file name says nothing ("dubbed.mp4")."""
    if inputs.is_link(spec):
        return Path(spec.split("?")[0].rstrip("/")).stem or spec
    path = Path(spec).expanduser()
    if path.stem.lower() in GENERIC_NAMES and path.parent.name:
        return path.parent.name
    return path.stem


def _detect_dub_language(path: str, whisper_model_name: str, cache, y=None) -> tuple[str, Optional[float]]:
    """The dub's spoken language and how sure the recognizer is, from its first 30 s (cached). y: its sound, when
    already loaded."""
    key = f"v{CACHE_VERSION}|filelang2|{asr.model_id(whisper_model_name)}|{inputs.fingerprint(path)}"
    found = cache.get(key)
    if not (isinstance(found, list) and len(found) == 2):
        if y is None:
            with tempfile.TemporaryDirectory(prefix="dubeval_") as tmp:
                y = load_audio(extract_audio(path, str(Path(tmp) / "dub.wav")))
        found = list(detect_language(y, get_whisper_model(whisper_model_name)))
        cache[key] = found
    if not found or not found[0]:
        raise ValueError(NO_DUB_LANGUAGE)
    return found[0], found[1]


def _load_both(original_path: str, dub_path: str):
    """Both videos' sound, loaded once for the same-video check, the language guess and the evaluation; None when it
    can't be read here, so each step reports the problem as it did on its own (pairing: not measured; the
    evaluation: the file's error)."""
    try:
        return load_both(original_path, dub_path)
    except Exception as e:
        log.warning("Loading both sound tracks up front failed: %s", e)
        return None


def pair_videos(original_path: str, dub_path: str, cache, audio=None,
                progress: Optional[Callable[[str, float], None]] = None) -> dict:
    """Same video or not, the dub's time shift and coverage (dubeval/pairing.py), cached by both files.

    audio: both waveforms when already loaded (evaluate.load_both). progress(message, fraction) follows the check.
    Never fails the run: a pairing that can't be measured is reported as not measured, with no shift applied.
    """
    key = f"v{CACHE_VERSION}|pair|{inputs.fingerprint(original_path)}|{inputs.fingerprint(dub_path)}"
    found = cache.get(key)
    if isinstance(found, dict):
        return found
    try:
        y_o, y_d = audio if audio is not None else load_both(original_path, dub_path)
        found = pairing.pair(original_path, dub_path, y_o, y_d, SAMPLE_RATE, FFMPEG_EXE, progress=progress)
    except Exception as e:                   # pairing is a check: it must never stop the evaluation
        log.warning("Pairing not measured: %s", e)
        return pairing.not_measured("error")
    cache[key] = found
    return found


def applied_parts(pair: dict) -> Optional[list]:
    """The parts to lay the dub onto the original by, when the dub is cut differently (several shifts); else None."""
    if not pair.get("measured") or pair.get("same_video") is False or pair.get("steady_offset") is not False:
        return None
    parts = pair.get("parts") or []
    return parts if len(parts) > 1 else None


def applied_offset(pair: dict) -> float:
    """The shift to correct for: the measured one, unless it's within measuring noise or unknown."""
    offset = pair.get("offset_sec") or 0.0
    return offset if pair.get("measured") and pair.get("same_video") is not False and abs(offset) >= MIN_APPLIED_OFFSET \
        else 0.0


def evaluate_files(
    original: str,
    dub: str,
    notify: Callable[..., None],
    check_cancel: Callable[[], None],
    original_track: Optional[int] = None,
    dub_track: Optional[int] = None,
    original_subtitles: Optional[str] = None,
    dub_subtitles: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    ground_truth_text: Optional[str] = None,
    whisper_model_name: str = DEFAULT_WHISPER_MODEL,
    include_lipsync: bool = False,
    use_translation_judge: bool = True,
    use_cache: bool = True,
    allow_different: bool = False,
    dub_type: Optional[str] = None,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Evaluates any original and its dub: local files or links, optionally one audio track of a file each.

    original and dub may be the same file with two audio tracks (pass original_track and dub_track). Languages are
    detected when not given. Subtitle files (SRT or WebVTT) are read, checked and kept with the results. Lip
    movement is off unless include_lipsync is True (it's slow and informational only). The pair is checked first:
    clearly different videos stop the run (unless allow_different), and a time shift is corrected. dub_type
    (ai_clone | ai_stock | human) tells the meaning check how freely the dub may adapt, and skips voice similarity
    for dubs that use another voice on purpose.
    """
    if dub_type is not None and dub_type not in DUB_TYPES:
        raise ValueError(BAD_DUB_TYPE)
    notify("prepare", "Checking the files...", 0.05)
    original_subs = inputs.read_subtitles(original_subtitles, "original") if original_subtitles else None
    dub_subs = inputs.read_subtitles(dub_subtitles, "dub") if dub_subtitles else None
    folder = _link_cache_dir("files|" + json.dumps([original.strip(), dub.strip(), original_track, dub_track]))
    if not use_cache:
        for f in folder.glob("*"):
            f.unlink()
    notify("prepare", "Getting the original video...", 0.15)
    original_path = inputs.fetch(original, folder, "original video", session=session, sleep=sleep)
    check_cancel()
    notify("prepare", "Getting the dubbed video...", 0.45)
    dub_path = inputs.fetch(dub, folder, "dubbed video", session=session, sleep=sleep)
    check_cancel()
    original_path = inputs.select_track(original_path, original_track, folder, "original video")
    dub_path = inputs.select_track(dub_path, dub_track, folder, "dubbed video")
    original_info = inputs.check(original_path, "original video")
    dub_info = inputs.check(dub_path, "dubbed video")
    _prune(Path(CACHE_DIR), MAX_CACHED_LINKS, protect=folder)
    check_cancel()

    cache = JsonCache(folder / "whisper_cache.json")
    notify("prepare", "Reading the sound of both videos...", 0.5)
    audio = _load_both(original_path, dub_path)                # once, for the check and the evaluation
    check_cancel()
    notify("prepare", "Checking that both files are the same video...", 0.55)
    pair = pair_videos(original_path, dub_path, cache, audio,
                       lambda message, fraction: notify("prepare", message, 0.55 + 0.25 * fraction))
    if pair.get("same_video") is False and not allow_different:
        raise ValueError(DIFFERENT_VIDEOS)
    check_cancel()
    target_given, target_prob = bool(target_lang), None
    if not target_given:
        notify("prepare", "Detecting the dub's language...", 0.8)
        target_lang, target_prob = _detect_dub_language(dub_path, whisper_model_name, cache,
                                                        y=audio[1] if audio else None)
    check_cancel()
    eval_results = run_full_evaluation(
        original_video_path=original_path,
        dubbed_video_path=dub_path,
        ground_truth_text=(ground_truth_text or "").strip(),
        target_lang=target_lang,
        whisper_model_name=whisper_model_name,
        on_step=lambda msg, frac: notify("evaluate", msg, frac * 0.95),
        include_lipsync=include_lipsync,
        source_lang=source_lang,
        cache=cache,
        dub_offset_sec=applied_offset(pair),
        dub_parts=applied_parts(pair),
        audio=audio,
        check=check_cancel,
    )
    eval_results["pairing"] = {**pair, "applied_offset_sec": applied_offset(pair),
                               "applied_parts": bool(applied_parts(pair))}
    check_cancel()
    source_code = source_lang or eval_results["metadata"].get("detected_source_language")
    same_file = original.strip() == dub.strip()
    eval_results["pipeline"] = {
        "run_id": f"{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "execution_mode": "Two audio tracks of one file" if same_file else "Files or links",
        "input_video_path": original_path,
        "dubbed_video_path": dub_path,
        "target_language_name": _language_name(target_lang),
        "target_language_code": target_lang,
        "target_language_id": target_lang,
        "input": {
            "kind": "tracks" if same_file else "files",
            "title": _title(original if inputs.is_link(dub) else dub),
            "original": original.strip(),
            "dub": dub.strip(),
            "original_track": original_track,
            "dub_track": dub_track,
            "source_language_name": _language_name(source_code),
            "source_language_code": source_code,
            "target_language_name": _language_name(target_lang),
            "languages_from": {"source": "given" if source_lang else "detected",
                               "target": "given" if target_given else "detected"},
            "is_lipsync": None,
            "evaluated_video": "dubbed",
            "dub_type": dub_type,
            "original_media": original_info,
            "dub_media": dub_info,
            "subtitles": {"original": len(original_subs) if original_subs else None,
                          "dub": len(dub_subs) if dub_subs else None},
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "logs": "Read from local files or links; downloads and speech recognition are cached.",
    }
    eval_results["subtitles"] = {"original": original_subs, "dub": dub_subs}
    eval_results["subtitle_match"] = subtitle_match(eval_results)
    apply_dub_type(eval_results, dub_type)
    if not target_given and target_prob is not None and target_prob < LANGUAGE_GUESS_OK:
        eval_results.setdefault("warnings", []).insert(0, {
            "key": "r.warn.lang_guess", "params": {"lang": _language_name(target_lang), "pct": round(target_prob * 100)},
            "text": f"The dub's language was guessed as {target_lang}, only {target_prob:.0%} sure."})
    judge_cache = JsonCache(folder / "judge_cache.json")
    _abandonable(lambda: check_meaning_screen(eval_results, notify, cache=judge_cache), check_cancel)
    _abandonable(lambda: check_translation(eval_results, use_translation_judge, notify, cache=judge_cache), check_cancel)
    return eval_results


def run_files_evaluation(
    original: str,
    dub: str,
    report: Optional[Callable[[Progress], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    report_lang: str = "en",
    out_dir: Optional[str] = None,
    history_mode: str = "single",
    **options,
) -> dict:
    """Evaluates an original and its dub (files, links or two tracks of one file) and saves report.json/.html/.txt.

    options are evaluate_files' keyword arguments. The files go to out_dir when given, otherwise to a new run
    folder under data/output/runs/.
    """
    notify, check_cancel = _notifier(report), _canceller(cancel_event)
    results = evaluate_files(original, dub, notify, check_cancel, **options)
    check_cancel()                               # stopped at the very end: still nothing is written or recorded
    notify("evaluate", "Writing the report...", 0.99)
    results["report"] = build_report(results, report_lang)
    if out_dir is None:
        run_id, folder = new_run_dir()
        results["pipeline"]["run_id"] = run_id
        prune_old_runs(protect=folder)
    else:
        folder = out_dir
    results["pipeline"]["report_files"] = save_report_files(results, folder)
    save_results(results)
    history.record(results, history_mode)
    return results


def save_comparison_files(comp: dict, results: dict, out_dir, absolute_videos: bool = False) -> dict:
    """Writes comparison.txt / .json / .html and report_A.*, report_B.*, ... into out_dir; returns their paths."""
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    files = {"text": folder / "comparison.txt", "json": folder / "comparison.json", "html": folder / "comparison.html"}
    files["text"].write_text(render_comparison_text(comp), encoding="utf-8")
    _write_json(files["json"], {k: v for k, v in comp.items() if k != "reports"})
    files["html"].write_text(render_comparison_html(comp), encoding="utf-8")
    out = {k: str(v) for k, v in files.items()}
    for dub in comp["dubs"]:
        own = save_report_files(results[dub], folder, f"report_{dub}", absolute_videos)
        for kind, path in own.items():
            out[f"{kind}_{dub}"] = path
        if not absolute_videos:                     # the run's own files: History links each dub to its report
            results[dub].setdefault("pipeline", {})["report_files"] = own
    return out


def run_comparison(
    url_a: str,
    url_b: str,
    out_dir: str,
    report_lang: str = "ko",
    original: Optional[str] = None,
    report: Optional[Callable[[Progress], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    whisper_model_name: str = DEFAULT_WHISPER_MODEL,
    include_lipsync: Optional[bool] = None,
    use_translation_judge: bool = True,
    use_cache: bool = True,
    more_urls: tuple = (),
    session=None,
    sleep: Callable[[float], None] = time.sleep,
    original_subtitles: Optional[str] = None,
    per_dub: Optional[list[dict]] = None,
) -> dict:
    """Evaluates dubs of the same video with the full pipeline, ranks them, recommends one, and saves every file.

    url_a and url_b are dubs A and B; more_urls adds C, D, ... (up to 8 in all). per_dub (one dict per dub, in order)
    gives a dub its own dub_subtitles and dub_type; original_subtitles is shared. Returns {"comparison", "results":
    {"A", "B", ...}, "files"}. The decision rule lives in dubeval/compare.py.
    """
    urls = [url_a, url_b, *more_urls]
    if len(urls) > len(LABELS):
        raise ValueError(f"Compare at most {len(LABELS)} dubs at a time.")
    per_dub = list(per_dub or [])
    if len(per_dub) > len(urls):
        raise ValueError(TOO_MANY_DUB_OPTIONS)
    per_dub += [{}] * (len(urls) - len(per_dub))
    started = time.time()
    outer = _notifier(report)
    check_cancel = _canceller(cancel_event)
    results = {}
    for dub, url, own in zip(LABELS, urls, per_dub):
        span = {"fetch": (0.0, 0.03), "download": (0.03, 0.15), "evaluate": (0.15, 1.0)}

        def notify(stage, message, fraction=0.0, _dub=dub):
            """Maps one dub's fetch/download/evaluate progress onto its dub_a / dub_b stage."""
            lo, hi = span.get(stage, (0.0, 1.0))
            outer(f"dub_{_dub.lower()}", message, lo + (hi - lo) * fraction)
        results[dub] = evaluate_share(url, notify, check_cancel, whisper_model_name=whisper_model_name,
                                      include_lipsync=include_lipsync, use_translation_judge=use_translation_judge,
                                      original=original, use_cache=use_cache, session=session, sleep=sleep,
                                      original_subtitles=original_subtitles,
                                      **{k: v for k, v in own.items() if k in ("dub_subtitles", "dub_type") and v})
    outer("compare", "Comparing the dubs...", 0.5)
    comp = build_ranking(list(results.values()), report_lang, run_seconds=time.time() - started)
    for dub in comp["dubs"]:
        results[dub]["report"] = comp["reports"][dub]
    files = save_comparison_files(comp, results, out_dir)
    for dub in comp["dubs"]:
        history.record(results[dub], "compare")
    outer("compare", "Comparing the dubs...", 1.0)
    return {"comparison": comp, "results": results, "files": files}


def files_compare_stages(n: int = 2) -> list[str]:
    """The stages of comparing n dubs of one original (files or links)."""
    return [f"dub_{d.lower()}" for d in LABELS[:n]] + ["compare"]


def run_files_comparison(
    original: str,
    dubs: list[str],
    out_dir: str,
    report_lang: str = "en",
    report: Optional[Callable[[Progress], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    per_dub: Optional[list[dict]] = None,
    **options,
) -> dict:
    """Evaluates 2-8 dubs of one original (files or links), ranks them, recommends one, and saves every file.

    options are evaluate_files' keyword arguments, shared by every dub; per_dub (one dict per dub, in order) overrides
    them for that dub, e.g. [{"dub_type": "human"}, {"dub_type": "ai_clone", "target_lang": "uz"}]: a human and an
    AI dub, or dubs in different languages, are each judged by their own rules. Returns {"comparison", "results":
    {"A", "B", ...}, "files"}, like run_comparison. The decision rule lives in dubeval/compare.py.
    """
    if not 2 <= len(dubs) <= len(LABELS):
        raise ValueError(f"Compare between 2 and {len(LABELS)} dubs.")
    per_dub = list(per_dub or [])
    if len(per_dub) > len(dubs):
        raise ValueError(TOO_MANY_DUB_OPTIONS)
    per_dub += [{}] * (len(dubs) - len(per_dub))
    started = time.time()
    outer = _notifier(report)
    check_cancel = _canceller(cancel_event)
    results = {}
    for dub, path, own in zip(LABELS, dubs, per_dub):
        span = {"prepare": (0.0, 0.15), "evaluate": (0.15, 1.0)}

        def notify(stage, message, fraction=0.0, _dub=dub):
            """Maps one dub's prepare/evaluate progress onto its dub_a / dub_b ... stage."""
            lo, hi = span.get(stage, (0.0, 1.0))
            outer(f"dub_{_dub.lower()}", message, lo + (hi - lo) * fraction)
        results[dub] = evaluate_files(original, path, notify, check_cancel,
                                      **{**options, **{k: v for k, v in own.items() if v is not None}})
    outer("compare", "Comparing the dubs...", 0.5)
    comp = build_ranking(list(results.values()), report_lang, run_seconds=time.time() - started)
    for dub in comp["dubs"]:
        results[dub]["report"] = comp["reports"][dub]
    files = save_comparison_files(comp, results, out_dir)
    for dub in comp["dubs"]:
        history.record(results[dub], "compare")
    outer("compare", "Comparing the dubs...", 1.0)
    return {"comparison": comp, "results": results, "files": files}


def run_batch(entries: list[dict], out_dir: str, report_lang: str = "ko",
              report: Optional[Callable[[Progress], None]] = None, cancel_event: Optional[threading.Event] = None,
              session=None, sleep: Callable[[float], None] = time.sleep, **options) -> dict:
    """Evaluates every entry of a batch (share links or original/dub pairs, see dubeval/batch.py) and writes
    summary.csv / .txt / .json plus one report folder per entry. An entry that fails is recorded with its error; the
    batch goes on. Returns {"rows", "agreement", "files"}."""
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    outer, check_cancel = _notifier(report), _canceller(cancel_event)
    rows = []
    for n, entry in enumerate(entries, 1):
        check_cancel()
        outer("batch", f"{n}/{len(entries)} {entry['link']}", (n - 1) / len(entries))
        inner = lambda p, _n=n: outer("batch", f"{_n}/{len(entries)} · {p.message}", (_n - 1) / len(entries))
        try:
            if "original" in entry:                       # a pair from a test-set sheet
                file_options = {k: options[k] for k in ("whisper_model_name", "use_translation_judge", "use_cache")
                                if k in options}
                results = run_files_evaluation(entry["original"], entry["dub"], report_lang=report_lang,
                                               out_dir=str(folder / f"{n:03d}"), report=inner,
                                               cancel_event=cancel_event, history_mode="batch", session=session,
                                               sleep=sleep, include_lipsync=options.get("include_lipsync") is True,
                                               **file_options, **entry.get("options", {}))
            else:
                results = run_share_evaluation(entry["link"], report_lang=report_lang, out_dir=str(folder / f"{n:03d}"),
                                               report=inner, cancel_event=cancel_event, session=session, sleep=sleep,
                                               history_mode="batch", **options)
            rows.append(summary_row(n, entry, results))
        except Cancelled:
            raise
        except Exception as e:  # one broken link must not stop the batch
            log.warning("Batch link %d failed: %s", n, e)
            rows.append(summary_row(n, entry, error=str(e) or e.__class__.__name__))
    files = {"csv": folder / "summary.csv", "text": folder / "summary.txt", "json": folder / "summary.json"}
    files["csv"].write_text(to_csv(rows), encoding="utf-8-sig")       # BOM: Excel opens Korean text correctly
    files["text"].write_text(render_batch_text(rows, report_lang), encoding="utf-8")
    _write_json(files["json"], {"rows": rows, "agreement": agreement(rows)})
    outer("batch", "Done", 1.0)
    return {"rows": rows, "agreement": agreement(rows), "files": {k: str(v) for k, v in files.items()}}
