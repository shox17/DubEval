"""Numbers check: the numbers (amounts, dates, prices, times) each dub line says against its original line.

Pure and offline. It reads the speech line by line (pipeline.judge_lines) and compares only digits, so it works for
any language pair without a model; a number spoken as a word on one side can't be compared and is left alone. The
local translation judge missed every planted wrong number (0 of 6, docs/validation.md); this catches them without
an AI. Speech recognition can mishear a number, so a mismatch is a moment to listen to (Check), never Poor.

It flags a number replaced by another, and nothing else, because languages say the same number differently: "July 4" is
7월 4일 (a 7 the original doesn't have), "half past 3" is 3시 30분, "2 million" is 200만, "$30,000" is 3만. So it misses a
number only one side says, and one wrong only by its zeros (5 and 50): the translation check reads those.
"""
import re

NUMBER = re.compile(r"(?<!\d)\d{1,3}(?:[ \u00a0\u202f]\d{3}(?!\d))+|\d+(?:[.,]\d+)*")     # 10 000, 1,000, 3.5
NEIGHBOURS = 1                     # a number may sit in the next or previous line when the two sides split differently


def numbers_in(text: str) -> list[str]:
    """The numbers in a text, normalized so the same number matches across languages: 1,000 = 1.000 = 1 000 = 1000,
    3,5 = 3.5 and ٣٥ = 35; a time or a score (3:30) is two numbers."""
    out = []
    for raw in NUMBER.findall(re.sub(r"\d", lambda m: str(int(m.group())), text or "")):
        groups = re.split(r"[.,\s]", raw)
        if len(groups) > 1 and all(len(g) == 3 for g in groups[1:]):
            value = "".join(groups)                                    # thousands separators
        elif len(groups) == 2:
            value = f"{groups[0]}.{groups[1]}"                         # a decimal point or comma
        else:
            value = "".join(groups)
        whole, _, frac = value.partition(".")
        frac = frac.rstrip("0")
        out.append((whole.lstrip("0") or "0") + (f".{frac}" if frac else ""))
    return out


def _digits(number: str) -> str:
    """A number's significant digits: the same whatever unit a language counts it in (2 million = 200만, 1.5 = 150)."""
    return number.replace(".", "").strip("0") or "0"


def not_measured(key: str) -> dict:
    return {"measured": False, "reason_key": key, "compared": 0, "with_numbers": 0, "lines": []}


def check(lines: list[dict]) -> dict:
    """Lines where a number the original says has become another in the dub, on that line or a neighbouring one.

    lines: judge_lines' output, sorted by time. Only lines with digits on both sides are compared."""
    found = [(ln, numbers_in(ln.get("original") or ""), numbers_in(ln.get("dub") or "")) for ln in lines]
    with_numbers = sum(1 for _, o, d in found if o or d)
    compared, changed = 0, []
    for i, (ln, orig, dub) in enumerate(found):
        if not orig or not dub:
            continue
        compared += 1
        near = found[max(0, i - NEIGHBOURS):i + NEIGHBOURS + 1]
        said, heard = {_digits(x) for _, o, _ in near for x in o}, {_digits(x) for _, _, d in near for x in d}
        new, lost = [x for x in dub if _digits(x) not in said], [x for x in orig if _digits(x) not in heard]
        if new and lost and "".join(map(_digits, new)) != "".join(map(_digits, lost)):      # 15,000 is 1만 5000
            changed.append({"n": ln["n"], "start": ln["start"], "end": ln["end"], "original": lost, "dub": new})
    if not compared:
        return {**not_measured("r.num.words" if with_numbers else "r.num.none"), "with_numbers": with_numbers}
    return {"measured": True, "reason_key": None, "compared": compared, "with_numbers": with_numbers,
            "lines": changed}
