"""Keeps the computer from going to sleep while an evaluation runs.

An idle computer goes to sleep after a few minutes, and an evaluation running at that moment simply stops until
someone wakes it: on one Mac a 3.5-minute evaluation took 16 minutes because the Mac slept for 13 of them
(2026-11-18). Only idle system sleep is held off; the screen may still turn off, and closing a laptop's lid still
puts it to sleep. Nothing here may fail an evaluation: any problem is logged and the evaluation runs as before.
"""
import contextlib
import logging
import os
import subprocess
import sys
from typing import Iterator

log = logging.getLogger(__name__)

# Windows: SetThreadExecutionState flags. ES_SYSTEM_REQUIRED keeps the system awake while the calling thread asks;
# ES_CONTINUOUS makes it last until the same thread clears it.
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
CAFFEINATE = "/usr/bin/caffeinate"                 # macOS's own tool: -i holds off idle sleep, -w ends with this process


@contextlib.contextmanager
def keep_awake() -> Iterator[None]:
    """Holds off idle sleep for the block, on Windows and macOS (elsewhere it does nothing)."""
    undo = _hold()
    try:
        yield
    finally:
        try:
            undo()
        except Exception as e:                     # releasing must never change how the evaluation ended
            log.info("Couldn't let the computer sleep again: %s", e)


def _hold():
    """Starts holding off sleep; returns how to stop."""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            if not kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED):
                raise OSError("SetThreadExecutionState failed")
            return lambda: kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        if sys.platform == "darwin" and os.path.exists(CAFFEINATE):
            proc = subprocess.Popen([CAFFEINATE, "-i", "-w", str(os.getpid())], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            def stop():
                proc.terminate()
                proc.wait(timeout=5)
            return stop
    except Exception as e:
        log.info("Couldn't keep the computer awake during the evaluation: %s", e)
    return lambda: None
