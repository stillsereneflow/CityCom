"""Write results/event_pilot/impl/EVENT_READY: sha256 of the four event-pilot artefacts.

Format matches the frozen-input READY files (``<sha256>  <path>``, one per line, paths relative to the
repo root).

Usage: python results/event_pilot/impl/make_ready.py
"""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FILES = ("citypulse/twin/event.py", "citypulse/twin/service.py", "citypulse/branching/engine.py",
         "results/event_pilot/impl/sigma_event.json")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while True:
            chunk = fh.read(1 << 16)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main():
    lines = []
    for rel in FILES:
        p = REPO / rel
        if not p.exists():
            print(f"MISSING: {rel}")
            return 1
        digest = sha256_file(p)
        lines.append(f"{digest}  {rel}")
        print(f"{digest}  {rel}")
    (OUT / "EVENT_READY").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'EVENT_READY'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
