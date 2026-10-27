"""Where the tool keeps its data: run outputs, the per-link cache, history, votes and jobs.

Everything lives under DATA_DIR: the project's data/ folder by default, or DUBEVAL_DATA (the Docker image uses
/data, a volume, so results survive container restarts).
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DUBEVAL_DATA") or PROJECT_ROOT / "data")
# Models shipped read-only with the desktop app (the faster-whisper base model, the speaker model); looked up before
# anything is downloaded. Unset in development.
BUNDLED_MODELS = Path(os.environ["DUBEVAL_BUNDLED_MODELS"]) if os.getenv("DUBEVAL_BUNDLED_MODELS") else None
