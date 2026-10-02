"""Entry point for the Windows scheduled task (run with pythonw.exe, no console window).

The task fires every 10 minutes; recorder.live() exits immediately if another instance holds the lock,
so exactly one recorder runs and a dead one is restarted within 10 minutes (including after a reboot
and logon).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from citypulse.config import HK_DIR  # noqa: E402
from citypulse.hkdata.recorder import live  # noqa: E402

if __name__ == "__main__":
    live(60, HK_DIR / "raw")
