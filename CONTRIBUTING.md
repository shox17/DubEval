# Contributing to DubEval

Thanks for helping. Bug reports, ideas, labelled test dubs and code are all welcome.

## Report a problem or suggest something
Open an [issue](https://github.com/shox17/DubEval/issues). For a bug, include what you ran, what you expected, what happened, your OS and Python
version, and the report files (`report.json` or `report.txt`) if you have them. Never attach videos you don't have the
right to share, and never paste API keys.

Security problems go through [SECURITY.md](SECURITY.md), not public issues.

## Set up
```bash
python3 -m venv eval_env
source eval_env/bin/activate          # Windows: eval_env\Scripts\activate
pip install -r requirements-dev.txt
pytest -m "not slow"                  # fast, offline; must pass
```
The full suite (`pytest`) adds real speech-recognition runs and needs `tests/data/sample.mp4`: any ~30 s English
talking-head MP4 of your own. That folder is git-ignored; never commit videos.

## Make a change
1. Fork the repository and create a branch from `main`.
2. Read [AGENTS.md](AGENTS.md): it has the project rules (where thresholds live, how to add a measure, how texts are
   translated). It applies to people as much as to coding agents.
3. Keep the change focused, and add or update tests.
4. Before you open a pull request:
   - `pytest -m "not slow"` passes (and `pytest` if you touched speech recognition);
   - every new text a person reads exists in English, Korean, Portuguese and Spanish (`tests/test_i18n.py` checks it);
   - docs match the change (`README.md`, `INSTALL.md`, `docs/`);
   - `git status` shows no `.env`, videos, `data/`, `output/` or `tests/data/` files.
5. Open the pull request with a short description of what changed and why. CI runs the tests on Linux, macOS and
   Windows and scans for secrets.

## Changing thresholds
Thresholds change only with evidence: reviewer votes (`qa.py feedback`) or a labelled batch (`qa.py batch`). Include
the before and after agreement numbers in the pull request.

## License of contributions
DubEval is licensed under the GNU AGPL v3.0 or later. By submitting a contribution, you agree that it is licensed
under the same terms. If your change copies or adapts code from another project, say so in the pull request and add
it to [NOTICE](NOTICE) with its copyright and license.

## Code of conduct
Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
