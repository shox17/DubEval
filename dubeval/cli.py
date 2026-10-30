"""Command line: evaluate a dub (files, links, two tracks of one file, or a Perso share link), or compare dubs.

    dubeval evaluate --original original.mp4 --dub dub.mp4 --out ./output --lang ko
    dubeval evaluate --tracks film.mkv                      (one file holding the original and the dubbed audio)
    dubeval schema                                          (the JSON Schema of report.json)
    python qa.py "<share link>" --out ./output --lang ko
    python qa.py compare "<link A>" "<link B>" --out ./output --lang ko
    python qa.py batch links.txt --out ./output/batch       (one link per line, optionally ",good|check|poor")
    python qa.py history --days 30                          (every past evaluation: totals, language pairs, trends)
    python qa.py feedback                                   (reviewers' votes: which checks raise false alarms)
    python qa.py serve [--host 127.0.0.1] [--port 8000]     (REST API; docs at /docs)

Progress goes to stderr, the report to stdout. Single mode saves report.json / .html / .txt in --out; compare
mode saves comparison.* plus report_A.* and report_B.*.
"""
import os
import sys
import json
import logging
import argparse
import contextlib
from pathlib import Path

from dubeval import network
from dubeval.evaluate import DEFAULT_WHISPER_MODEL
from dubeval.jobs import Cancelled, Progress
from dubeval.perso_api import PersoError
from dubeval.pipeline import run_comparison, run_files_evaluation, run_share_evaluation
from dubeval.compare import render_comparison_text
from dubeval.report import render_text

log = logging.getLogger(__name__)
FAIL_LEVELS = {"never": (), "poor": ("poor",), "check": ("check", "poor")}
LANGS = ["ko", "en", "es", "pt"]
DEFAULT_OUT = os.getenv("DUBEVAL_OUT") or "output"      # the Docker image sets /data/output (on the volume)


def _common(ap: argparse.ArgumentParser) -> None:
    """Options shared by single and compare mode."""
    ap.add_argument("--out", default=DEFAULT_OUT, help="Folder for the report files (created if missing; default ./output)")
    ap.add_argument("--lang", choices=LANGS, default="ko", help="Report language (default ko)")
    ap.add_argument("--original", help="The original video (file or URL), used when a share link has none")
    ap.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL, help=f"Speech model (default {DEFAULT_WHISPER_MODEL})")
    ap.add_argument("--no-lipsync", action="store_true", help="Skip lip movement even for a lip-synced dub (faster). By default it is measured "
                         "automatically when the dub is lip-synced")
    ap.add_argument("--no-translation-check", action="store_true", help="Skip the translation check (by default it runs automatically when GEMINI_API_KEY or ANTHROPIC_API_KEY is set)")
    ap.add_argument("--no-cache", action="store_true", help="Download the videos and run speech recognition again instead of reusing earlier results")
    ap.add_argument("--json", action="store_true", help="Print the report as JSON instead of text")
    ap.add_argument("--verbose", action="store_true", help="Show library logs (MediaPipe, TensorFlow) while running")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for single mode."""
    ap = argparse.ArgumentParser(prog="qa.py", description="Evaluate the quality of a Perso AI dub from its share link. "
                                 "To compare two dubs: qa.py compare <link A> <link B>.")
    ap.add_argument("share_url", help="Perso share link (https://perso.ai/.../share/video-translator?seq=...)")
    script = ap.add_mutually_exclusive_group()
    script.add_argument("--script", help="What the dub should say, to also score script accuracy")
    script.add_argument("--script-file", help="File with what the dub should say (UTF-8)")
    _common(ap)
    ap.add_argument("--fail-on", choices=list(FAIL_LEVELS), default="never",
                    help="Exit with code 1 when the verdict is this bad (for automation)")
    args = ap.parse_args(argv)
    args.mode = "single"
    return args


def parse_evaluate_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for evaluating any original and its dub."""
    ap = argparse.ArgumentParser(prog="dubeval evaluate", description="Evaluate a dub against its original: local "
                                 "files or links (YouTube and other pages need the links extra), or two audio tracks "
                                 "of one file.")
    ap.add_argument("--original", help="The original video: a file or a link")
    ap.add_argument("--dub", help="The dubbed video: a file or a link")
    ap.add_argument("--tracks", metavar="FILE", help="One file with both audio tracks (original = track 0, dub = "
                    "track 1 unless --original-track / --dub-track say otherwise)")
    ap.add_argument("--original-track", type=int, help="Use this audio track of the original (counted from 0)")
    ap.add_argument("--dub-track", type=int, help="Use this audio track of the dub (counted from 0)")
    ap.add_argument("--original-subtitles", metavar="FILE", help="Subtitles of the original (.srt or .vtt)")
    ap.add_argument("--dub-subtitles", metavar="FILE", help="Subtitles of the dub (.srt or .vtt)")
    ap.add_argument("--source-lang", help="The original's language code (for example en); detected when not given")
    ap.add_argument("--target-lang", help="The dub's language code (for example ko); detected when not given")
    ap.add_argument("--lipsync", action="store_true", help="Also measure lip movement (slow; informational only)")
    ap.add_argument("--allow-different-videos", action="store_true", help="Evaluate even when the two files look "
                    "like different videos (by default the run stops)")
    ap.add_argument("--dub-type", choices=["ai_clone", "ai_stock", "human"], help="How the dub's voices were made: "
                    "an AI clone of the original voice, an AI stock voice, or human voice actors (human dubs may "
                    "adapt the script; voice similarity is skipped for human and stock-voice dubs)")
    ap.add_argument("--judge", choices=["auto", "claude", "gemini", "openai", "ollama", "off"], help="Who checks the "
                    "translation: auto (default: Claude, then Gemini, then ChatGPT, then a local model through "
                    "Ollama), one of them, or off")
    script = ap.add_mutually_exclusive_group()
    script.add_argument("--script", help="What the dub should say, to also score script accuracy")
    script.add_argument("--script-file", help="File with what the dub should say (UTF-8)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="Folder for the report files (created if missing; default ./output)")
    ap.add_argument("--lang", choices=LANGS, default="ko", help="Report language (default ko)")
    ap.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL, help=f"Speech model (default {DEFAULT_WHISPER_MODEL})")
    ap.add_argument("--no-translation-check", action="store_true", help="Skip the translation check (by default it "
                    "runs automatically when GEMINI_API_KEY or ANTHROPIC_API_KEY is set)")
    ap.add_argument("--no-cache", action="store_true", help="Download the videos and run speech recognition again")
    ap.add_argument("--json", action="store_true", help="Print the report as JSON instead of text")
    ap.add_argument("--verbose", action="store_true", help="Show library logs (MediaPipe, TensorFlow) while running")
    ap.add_argument("--fail-on", choices=list(FAIL_LEVELS), default="never",
                    help="Exit with code 1 when the verdict is this bad (for automation)")
    args = ap.parse_args(argv)
    if args.tracks:
        if args.original or args.dub:
            ap.error("use either --tracks or --original and --dub, not both")
        args.original = args.dub = args.tracks
        args.original_track = 0 if args.original_track is None else args.original_track
        args.dub_track = 1 if args.dub_track is None else args.dub_track
    elif not (args.original and args.dub):
        ap.error("give --original and --dub (or --tracks for one file with both audio tracks)")
    args.mode = "evaluate"
    return args


def parse_compare_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for compare mode."""
    ap = argparse.ArgumentParser(prog="qa.py compare", description="Evaluate two Perso dubs of the same video, "
                                 "recommend which one to deliver, and explain why.")
    ap.add_argument("url_a", help="Share link of dub A")
    ap.add_argument("url_b", help="Share link of dub B")
    ap.add_argument("more", nargs="*", metavar="url_c", help="More share links (dubs C, D, ...; up to 8 in all)")
    _common(ap)
    args = ap.parse_args(argv)
    args.mode = "compare"
    return args


def parse_batch_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for batch mode."""
    ap = argparse.ArgumentParser(prog="qa.py batch", description="Evaluate many dubs and write one summary "
                                 "(summary.csv / .txt / .json): share links, one per line (add ,good / ,check / ,poor "
                                 "for your own verdict), or a test-set sheet: a CSV with original and dub columns "
                                 "(see examples/testset_template.csv). Your verdicts show how often the tool agrees.")
    ap.add_argument("file", help="Share links (one per line) or a CSV sheet with original,dub,... columns")
    _common(ap)
    args = ap.parse_args(argv)
    args.mode = "batch"
    return args


def parse_history_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for the history view."""
    ap = argparse.ArgumentParser(prog="qa.py history", description="Summarize every past evaluation: totals, verdicts "
                                 "per language pair, the most frequent problems and a weekly trend.")
    ap.add_argument("--days", type=int, help="Only the last N days")
    ap.add_argument("--lang", choices=LANGS, default="ko", help="Language (default ko)")
    ap.add_argument("--json", action="store_true", help="Print the summary as JSON")
    ap.add_argument("--csv", help="Also write every recorded evaluation to this CSV file")
    args = ap.parse_args(argv)
    args.mode, args.verbose = "history", True
    return args


def parse_feedback_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options for the reviewer-feedback summary."""
    ap = argparse.ArgumentParser(prog="qa.py feedback", description="Summarize reviewers' votes on problem intervals: "
                                 "per check, how many flags were real problems and how many false alarms.")
    ap.add_argument("--lang", choices=LANGS, default="ko", help="Language (default ko)")
    ap.add_argument("--json", action="store_true", help="Print the summary as JSON")
    args = ap.parse_args(argv)
    args.mode, args.verbose = "feedback", True
    return args


@contextlib.contextmanager
def quiet_native_stderr(enabled: bool):
    """Sends C++ library logs (MediaPipe writes straight to fd 2) to the null device; yields a stream for our messages."""
    if not enabled:
        yield sys.stderr
        return
    sys.stderr.flush()
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    ours = os.fdopen(os.dup(saved), "w", buffering=1, encoding="utf-8", errors="replace")
    try:
        yield ours
    finally:
        ours.flush()
        os.dup2(saved, 2)
        for fd in (saved, devnull):
            os.close(fd)
        ours.close()


def use_utf8_console() -> None:
    """Prints Korean and other non-ASCII text correctly on every console (Windows defaults to a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass                                  # replaced streams (tests, pipes in some IDEs) keep their encoding


def main(argv: list[str] | None = None) -> int:
    """Runs one evaluation or a comparison. Exit codes: 0 done, 1 see below, 2 input or runtime error.

    Single mode: 1 when the verdict fails --fail-on. Compare mode: 1 when every dub is Poor. Batch mode: 0 when every
    link was evaluated, 2 when any link failed (the summary is written either way).
    """
    use_utf8_console()
    network.use_system_settings()                  # the computer's certificates and proxy, as browsers use them
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["serve"]:
        return _serve(argv[1:])
    if argv[:1] == ["label"]:
        return _label(argv[1:])
    if argv[:1] == ["web"]:
        return _web(argv[1:])
    if argv[:1] == ["validate"]:
        return _validate(argv[1:])
    if argv[:1] == ["schema"]:
        from dubeval.schema import json_schema_text
        print(json_schema_text(), end="")
        return 0
    parsers = {"evaluate": parse_evaluate_args, "compare": parse_compare_args, "batch": parse_batch_args,
               "history": parse_history_args, "feedback": parse_feedback_args}
    args = parsers[argv[0]](argv[1:]) if argv[:1] and argv[0] in parsers else parse_args(argv)
    with quiet_native_stderr(not args.verbose and _has_real_stderr()) as err:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s", stream=err, force=True)
        return _run(args, err)


def _serve(argv: list[str]) -> int:
    """Runs the REST API (dubeval/api.py)."""
    ap = argparse.ArgumentParser(prog="qa.py serve", description="Run the REST API (interactive docs at /docs). "
                                 "Listening beyond this machine requires DUBEVAL_API_TOKEN.")
    ap.add_argument("--host", default="127.0.0.1", help="Address to listen on (default 127.0.0.1: this machine only)")
    ap.add_argument("--port", type=int, default=8000, help="Port (default 8000)")
    args = ap.parse_args(argv)
    from dubeval.api import serve
    serve(args.host, args.port)
    return 0


def _validate(argv: list[str]) -> int:
    """Validates DubEval with known problems put into the dubs of a test-set sheet (dubeval/validation.py)."""
    from dubeval import validation
    ap = argparse.ArgumentParser(prog="dubeval validate", description="Check that DubEval catches known problems "
                                 "(silence, the original voice left in, loudness jumps, distortion, noise, cuts) put "
                                 "into each dub of a test-set sheet, and count its false alarms, per language pair.")
    ap.add_argument("sheet", help="The test-set sheet (CSV with pair_id, original, dub, source_lang, target_lang, ...)")
    ap.add_argument("--out", default="data/validation", help="Folder for the copies and validation.txt/.json")
    ap.add_argument("--only", help="Only these pair ids, comma separated")
    ap.add_argument("--defects", help="Only these known problems, comma separated: "
                    + ", ".join([*validation.DEFECTS, *validation.HARMLESS]))
    ap.add_argument("--split", choices=["tune", "holdout"], help="Only the pairs of this split")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    names = [d.strip() for d in args.defects.split(",")] if args.defects else None
    unknown = [d for d in names or [] if d not in validation.DEFECTS and d not in validation.HARMLESS]
    if unknown:
        print(f"Unknown problem type: {', '.join(unknown)}", file=sys.stderr)
        return 2
    try:
        result = validation.run(args.sheet, args.out, names, [p.strip() for p in args.only.split(",")] if args.only
                                else None, args.split, progress=lambda m: print(m, file=sys.stderr, flush=True))
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(result["text"], end="")
    return 0


def _web(argv: list[str]) -> int:
    """Opens the web interface (dubeval/webapp.py)."""
    ap = argparse.ArgumentParser(prog="dubeval web", description="Open DubEval in the browser: choose an original and "
                                 "its dub, follow the evaluation, then review it on a timeline. Only this computer "
                                 "can open it, with the link printed at launch.")
    ap.add_argument("--port", type=int, default=0, help="Port on 127.0.0.1 (default: a free one)")
    ap.add_argument("--no-browser", action="store_true", help="Don't open the browser")
    ap.add_argument("--host", default="127.0.0.1", help="Address to listen on (default 127.0.0.1; 0.0.0.0 only "
                    "inside a container: the page still opens only as http://localhost with the printed link)")
    ap.add_argument("--exit-with-parent", action="store_true", help="Stop when the program that started this one "
                    "ends (the desktop app uses this, so no server is left running after it quits or crashes)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    from dubeval.webapp import exit_with_parent, serve
    if args.exit_with_parent:
        exit_with_parent()
    serve(args.port, open_browser=not args.no_browser, host=args.host)
    return 0


def _label(argv: list[str]) -> int:
    """Opens the review page for a test-set sheet (dubeval/labeling.py)."""
    ap = argparse.ArgumentParser(prog="dubeval label", description="Open a review page to label a test-set sheet: "
                                 "watch each original and dub side by side and give your own verdicts. They are "
                                 "saved into the sheet; calibration compares DubEval with them.")
    ap.add_argument("sheet", help="The test-set sheet (CSV with original and dub columns)")
    ap.add_argument("--results", help="A batch run folder (dubeval batch --out ...): its verdicts are shown after you "
                    "answer each pair")
    ap.add_argument("--lang", choices=LANGS, default="ko", help="Page language (default ko)")
    ap.add_argument("--port", type=int, default=0, help="Port on 127.0.0.1 (default: a free one)")
    ap.add_argument("--no-browser", action="store_true", help="Don't open the browser")
    args = ap.parse_args(argv)
    from dubeval.labeling import serve
    try:
        serve(args.sheet, args.results, args.lang, args.port, open_browser=not args.no_browser)
    except (ValueError, FileNotFoundError) as e:
        print(f"Could not open the sheet: {e}", file=sys.stderr)
        return 2
    return 0


def _has_real_stderr() -> bool:
    """False under test capture, where fd 2 isn't the process's stderr."""
    try:
        return sys.stderr.fileno() == 2
    except (AttributeError, OSError, ValueError):
        return False


def _progress(err):
    """A progress callback that prints each new message once."""
    last = {"msg": None}

    def progress(p: Progress):
        """Prints a progress line when the message changes."""
        if p.message != last["msg"]:
            last["msg"] = p.message
            print(f"  [{p.stage}] {p.message}", file=err, flush=True)
    return progress


def _run_history(args: argparse.Namespace, err) -> int:
    """Prints the history summary (and writes the CSV when asked)."""
    import csv
    from dubeval import history
    records = history.load()
    summary = history.summarize(records, days=args.days)
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else history.render_history_text(summary, args.lang))
    if args.csv:
        fields = ["time", "mode", "title", "languages", "language_pair", "lipsync", "verdict", "poor", "check",
                  "problem_seconds", "meaning_score", "overlap_pct", "link", "seq", "tool_version", "report"]
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        print(f"\nSaved: {args.csv}", file=err)
    return 0


def _run(args: argparse.Namespace, err) -> int:
    """The evaluation or comparison itself, printing progress and errors to err."""
    if args.mode == "history":
        return _run_history(args, err)
    if args.mode == "feedback":
        from dubeval import feedback
        summary = feedback.summarize(feedback.load())
        print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json
              else feedback.render_feedback_text(summary, args.lang))
        return 0
    script = getattr(args, "script", None)
    if getattr(args, "script_file", None):
        try:
            script = Path(args.script_file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"Can't read the script file: {e}", file=err)
            return 2
    if args.mode == "evaluate":
        return _run_evaluate(args, script, err)
    options = dict(report=_progress(err), whisper_model_name=args.whisper_model,
                   # None = automatic: lip movement is measured only when the dub is lip-synced.
                   include_lipsync=False if args.no_lipsync else None,
                   use_translation_judge=not args.no_translation_check, report_lang=args.lang,
                   original=args.original, use_cache=not args.no_cache)
    if args.mode == "batch":
        return _run_batch(args, options, err)
    try:
        if args.mode == "compare":
            run = run_comparison(args.url_a, args.url_b, out_dir=args.out, more_urls=tuple(args.more), **options)
        else:
            results = run_share_evaluation(args.share_url, ground_truth_text=script, out_dir=args.out, **options)
    except (ValueError, FileNotFoundError, PersoError) as e:
        print(f"\nCould not evaluate: {e}", file=err)
        return 2
    except (Cancelled, KeyboardInterrupt):
        print("\nStopped.", file=err)
        return 2
    except Exception as e:  # anything unexpected (ffmpeg, a broken video) is a runtime error, exit code 2
        log.debug("Evaluation failed", exc_info=True)
        print(f"\nCould not evaluate: {e.__class__.__name__}: {e}", file=err)
        return 2

    if args.mode == "compare":
        comp = run["comparison"]
        print(json.dumps({k: v for k, v in comp.items() if k != "reports"}, ensure_ascii=False, indent=2)
              if args.json else render_comparison_text(comp))
        print("\nSaved: " + "\n       ".join(run["files"][k] for k in ("text", "html", "json")), file=err)
        return 1 if comp["recommendation"]["all_poor"] else 0

    rep = results["report"]
    print(json.dumps(rep, ensure_ascii=False, indent=2) if args.json else render_text(rep))
    files = results["pipeline"].get("report_files", {})
    if files:
        print(f"\nSaved: {files['html']}\n       {files['json']}", file=err)
    return 1 if rep["overall"]["level"] in FAIL_LEVELS[args.fail_on] else 0


def _run_evaluate(args: argparse.Namespace, script, err) -> int:
    """Evaluates an original and its dub given as files, links or tracks; prints the report."""
    if args.judge:
        os.environ["DUBEVAL_JUDGE"] = args.judge
    try:
        results = run_files_evaluation(
            args.original, args.dub, report=_progress(err), report_lang=args.lang, out_dir=args.out,
            original_track=args.original_track, dub_track=args.dub_track,
            original_subtitles=args.original_subtitles, dub_subtitles=args.dub_subtitles,
            source_lang=args.source_lang, target_lang=args.target_lang, ground_truth_text=script,
            whisper_model_name=args.whisper_model, include_lipsync=args.lipsync,
            use_translation_judge=not args.no_translation_check, use_cache=not args.no_cache,
            allow_different=args.allow_different_videos, dub_type=args.dub_type)
    except (ValueError, FileNotFoundError) as e:
        print(f"\nCould not evaluate: {e}", file=err)
        return 2
    except (Cancelled, KeyboardInterrupt):
        print("\nStopped.", file=err)
        return 2
    except Exception as e:  # anything unexpected (ffmpeg, a broken video) is a runtime error, exit code 2
        log.debug("Evaluation failed", exc_info=True)
        print(f"\nCould not evaluate: {e.__class__.__name__}: {e}", file=err)
        return 2
    rep = results["report"]
    print(json.dumps(rep, ensure_ascii=False, indent=2) if args.json else render_text(rep))
    files = results["pipeline"].get("report_files", {})
    if files:
        print(f"\nSaved: {files['html']}\n       {files['json']}", file=err)
    return 1 if rep["overall"]["level"] in FAIL_LEVELS[args.fail_on] else 0


def _run_batch(args: argparse.Namespace, options: dict, err) -> int:
    """Batch mode: evaluate every link in the file, print the summary, write summary files."""
    from dubeval.batch import parse_batch_file, render_batch_text
    from dubeval.pipeline import run_batch
    try:
        entries = parse_batch_file(Path(args.file).read_text(encoding="utf-8-sig"), base_dir=str(Path(args.file).parent))
    except OSError as e:
        print(f"Can't read the batch file: {e}", file=err)
        return 2
    except ValueError as e:
        print(f"Could not read the batch file: {e}", file=err)
        return 2
    try:
        batch = run_batch(entries, args.out, **options)
    except (Cancelled, KeyboardInterrupt):
        print("\nStopped.", file=err)
        return 2
    print(json.dumps({"rows": batch["rows"], "agreement": batch["agreement"]}, ensure_ascii=False, indent=2)
          if args.json else render_batch_text(batch["rows"], args.lang))
    print("\nSaved: " + "\n       ".join(batch["files"][k] for k in ("csv", "text", "json")), file=err)
    return 2 if any(r["error"] for r in batch["rows"]) else 0


if __name__ == "__main__":
    sys.exit(main())
