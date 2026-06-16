#!/usr/bin/env python3
"""Attach generated image paths to a segments JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", required=True, help="Path to segments.json")
    parser.add_argument("--images", nargs="+", required=True, help="Image paths in segment order")
    args = parser.parse_args()

    segments_path = Path(args.segments)
    segments = json.loads(segments_path.read_text(encoding="utf-8"))

    if len(args.images) != len(segments):
        raise SystemExit(
            f"Expected {len(segments)} images for {segments_path}, got {len(args.images)}"
        )

    for segment, image in zip(segments, args.images):
        image_path = Path(image).resolve()
        if not image_path.exists():
            raise SystemExit(f"Image not found: {image_path}")
        segment["image_path"] = str(image_path)

    segments_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(segments_path.resolve()))


if __name__ == "__main__":
    main()
