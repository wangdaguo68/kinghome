#!/usr/bin/env python3
"""Video Factory — utility entry point for computation steps.

Usage:
  python main.py check-duration --segments workdir/segments.json --max 60
  python main.py compose-html    --segments workdir/segments.json --topic "..." --aspect "9:16" --out workdir/video.html
"""

import sys
from pathlib import Path

STEPS_DIR = Path(__file__).parent / "steps"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = sys.argv[1].replace("-", "_")
    sys.argv = sys.argv[1:]

    if cmd == "check_duration":
        from steps.check_duration import main as run
    elif cmd == "compose_html":
        from steps.compose_html import main as run
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    run()


if __name__ == "__main__":
    main()
