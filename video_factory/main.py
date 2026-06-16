#!/usr/bin/env python3
"""Video Factory — utility entry point for computation steps.

Usage:
  python main.py check-duration   --segments workdir/segments.json --max 60
  python main.py compose-remotion --segments workdir/segments.json --topic "..." --aspect "9:16"
  python main.py compose-html     --segments workdir/segments.json --topic "..." --aspect "9:16" --out workdir/video.html
  python main.py hn-storyboard    --topic "..." --out-dir output/vf_<id>/workdir --duration 60
  python main.py cls-storyboard   --topic "..." --out-dir output/vf_<id>/workdir --duration 58
  python main.py set-segment-images --segments workdir/segments.json --images workdir/seg_00.png ...
  python main.py render-remotion  --out output/vf_<id>/final.mp4
  python main.py gpt-image-2      --prompt "..." --out workdir/image.png
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
    elif cmd == "hn_storyboard":
        from steps.hn_storyboard import main as run
    elif cmd == "cls_storyboard":
        from steps.cls_storyboard import main as run
    elif cmd == "compose_remotion":
        from steps.compose_remotion import main as run
    elif cmd == "render_remotion":
        from steps.render_remotion import main as run
    elif cmd == "fetch_images":
        from steps.fetch_images import main as run
    elif cmd == "set_segment_images":
        from steps.set_segment_images import main as run
    elif cmd == "gpt_image_2":
        from steps.gpt_image_2 import main as run
    elif cmd == "compose_html":
        from steps.compose_html import main as run
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    run()


if __name__ == "__main__":
    main()
