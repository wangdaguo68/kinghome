#!/usr/bin/env python3
"""Video Factory — AI-powered media content creation pipeline.

Usage:
  python main.py --recipe hot_news --topic "黑客新闻"
  python main.py --recipe hot_news --topic "AI动态" --duration 45 --aspect 16:9
  echo '{"recipe":"hot_news","topic":"黑客新闻","duration":60}' | python main.py --json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline.runner import Runner


def check_deps() -> None:
    missing = []
    if not shutil.which("edge-tts"):
        missing.append("edge-tts (install: pip install edge-tts)")
    if not os.environ.get("BRAVE_API_KEY"):
        missing.append("BRAVE_API_KEY env var")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY env var")
    if missing:
        print("Missing dependencies:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Video Factory Pipeline")
    p.add_argument("--recipe", type=str, help="Recipe name (without .yaml)")
    p.add_argument("--topic", type=str, help="Video topic")
    p.add_argument("--duration", type=int, help="Max duration in seconds")
    p.add_argument("--aspect", type=str, help="Aspect ratio (e.g. 9:16, 16:9)")
    p.add_argument("--json", action="store_true", help="Read JSON params from stdin")
    return p.parse_args()


def main() -> None:
    check_deps()

    args = parse_args()

    if args.json:
        raw = sys.stdin.read().strip()
        if not raw:
            print("ERROR: --json mode expects JSON on stdin", file=sys.stderr)
            sys.exit(1)
        data = json.loads(raw)
        recipe_name = data["recipe"]
        topic = data["topic"]
        overrides = {k: v for k, v in data.items() if k not in ("recipe", "topic")}
    else:
        if not args.recipe or not args.topic:
            print("ERROR: --recipe and --topic required (or use --json)", file=sys.stderr)
            sys.exit(1)
        recipe_name = args.recipe
        topic = args.topic
        overrides = {}
        if args.duration:
            overrides["duration"] = args.duration
        if args.aspect:
            overrides["aspect"] = args.aspect

    recipes_dir = Path(__file__).parent / "config" / "recipes"
    runner = Runner(recipes_dir)

    try:
        ctx = runner.run(recipe_name, topic, overrides)
        video = ctx.artifacts.get("final_video_path", "")
        if video:
            print(f"\nDone: {video}")
        else:
            print("\nPipeline completed but no video path found.")
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
