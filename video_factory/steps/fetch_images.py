#!/usr/bin/env python3
"""Fetch free images for each segment based on image_prompt keywords.

Uses LoremFlickr (no API key needed) with progressive keyword broadening.
"""

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

STOP_WORDS = {
    "a", "an", "the", "no", "in", "on", "at", "to", "for", "of", "with",
    "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
    "style", "illustration", "editorial", "dramatic", "clean", "dark",
    "text", "image", "visual", "design", "background", "effect", "no", "not",
    "any", "all", "some", "this", "that", "it", "its", "into", "through",
    "across", "which", "one", "like",
}

DIMS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}

# Broad fallback categories for when specific keywords find nothing
FALLBACK_CATEGORIES = [
    "technology", "abstract", "nature", "city", "space",
    "architecture", "texture", "minimal", "digital", "code",
]


def extract_keywords(prompt: str) -> list[str]:
    """Pull meaningful English keywords, most significant first."""
    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    seen = set()
    ordered = []
    for w in meaningful:
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    return ordered


def try_download(w: int, h: int, keyword_str: str, dest: Path, seen_hashes: set) -> bool:
    """Try downloading from LoremFlickr. Returns True if got a unique image."""
    url = f"https://loremflickr.com/{w}/{h}/{keyword_str}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VideoFactory/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        print(f"    {keyword_str}: {e}")
        return False

    if len(data) < 2000:
        print(f"    {keyword_str}: too small ({len(data)} bytes)")
        return False

    hx = hashlib.md5(data).hexdigest()
    if hx in seen_hashes:
        print(f"    {keyword_str}: duplicate (skip)")
        return False

    dest.write_bytes(data)
    seen_hashes.add(hx)
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--segments", required=True)
    p.add_argument("--aspect", default="9:16")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    segments = json.loads(Path(args.segments).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    w, h = DIMS.get(args.aspect, (1080, 1920))
    updated = False
    seen_hashes = set()  # avoid duplicates across segments

    for i, seg in enumerate(segments):
        if seg.get("image_path") and Path(seg["image_path"]).exists():
            hx = hashlib.md5(Path(seg["image_path"]).read_bytes()).hexdigest()
            seen_hashes.add(hx)
            print(f"[{i}] OK (already has image)")
            continue

        prompt = seg.get("image_prompt", "")
        if not prompt:
            print(f"[{i}] SKIP (no image_prompt)")
            continue

        keywords = extract_keywords(prompt)
        if not keywords:
            keywords = ["technology"]

        out_path = out_dir / f"seg_{i:02d}.jpg"
        print(f"[{i}] {keywords[:5]}...")

        # Try progressively broader keyword combos until one works
        attempts = [
            ",".join(keywords[:5]),   # exact: battlefield,glowing,red,neural,network
            ",".join(keywords[:3]),   # medium: battlefield,glowing,red
            ",".join(keywords[:2]),   # broad: battlefield,glowing
            keywords[0],               # single: battlefield
        ]
        # Add a fallback if nothing works
        fallback = FALLBACK_CATEGORIES[i % len(FALLBACK_CATEGORIES)]
        attempts.append(fallback)

        success = False
        for attempt in attempts:
            time.sleep(0.3)
            if try_download(w, h, attempt, out_path, seen_hashes):
                kb = out_path.stat().st_size // 1024
                seg["image_path"] = str(out_path.resolve())
                updated = True
                print(f"    OK '{attempt}' ({kb} KB)")
                success = True
                break

        if not success:
            print(f"    FAILED all attempts")

    if updated:
        Path(args.segments).write_text(
            json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nUpdated: {args.segments}")
    else:
        print("\nNo changes")


if __name__ == "__main__":
    main()
