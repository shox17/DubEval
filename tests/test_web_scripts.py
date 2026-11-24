"""The page's scripts parse (as CI's "javascript syntax" job checks): the page has no build step and no JavaScript tests,
so a syntax error passed every fast test and left the app on its start-up screen (2026-11-21)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted([*(ROOT / "dubeval" / "web").glob("*.js"), *(ROOT / "desktop").glob("*.js")])
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js isn't installed (CI's javascript job still checks)")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_every_page_script_parses(script):
    text = script.read_text(encoding="utf-8")
    module = any(line.startswith(("import ", "export ")) for line in text.splitlines())
    # a module from stdin, as it is loaded: `node --check` on a .js file guessed to be a module misses errors in it
    args = [NODE, "--input-type=module", "--check"] if module else [NODE, "--check", str(script)]
    done = subprocess.run(args, input=text if module else None, capture_output=True, text=True, encoding="utf-8",
                          timeout=60)
    assert done.returncode == 0, done.stderr
