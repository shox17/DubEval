"""`python -m dubeval ...`: the same as the `dubeval` command (the desktop app starts the server this way)."""
import sys

from dubeval.cli import main

sys.exit(main())
