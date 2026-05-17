#!/usr/bin/env python3
"""Validate audio durations against max, apply trim/warn/error strategy."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mutagen.mp3 import MP3


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--segments", required=True, help="Path to segments JSON file")
    p.add_argument("--max", type=float, required=True, help="Max total duration in seconds")
    p.add_argument("--strategy", default="trim", choices=["trim", "warn", "error"])
    args = p.parse_args()

    segments = json.loads(Path(args.segments).read_text(encoding="utf-8"))

    durations = []
    for seg in segments:
        audio_path = seg.get("audio_path", "")
        if audio_path and Path(audio_path).exists():
            durations.append(MP3(audio_path).info.length)
        else:
            durations.append(seg.get("duration_est", 10.0))

    total = sum(durations)
    print(f"Total: {total:.1f}s, Max: {args.max}s")

    if total <= args.max:
        json.dump({"ok": True, "total": total, "segments": segments}, sys.stdout, ensure_ascii=False)
        return

    over = total - args.max

    if args.strategy == "error":
        print(f"ERROR: exceeds max by {over:.1f}s", file=sys.stderr)
        sys.exit(1)

    if args.strategy == "warn":
        print(f"WARNING: exceeds max by {over:.1f}s", file=sys.stderr)
        json.dump({"ok": True, "total": total, "warning": f"exceeds by {over:.1f}s", "segments": segments}, sys.stdout, ensure_ascii=False)
        return

    # trim strategy
    last = segments[-1]
    last_dur = durations[-1]
    keep_ratio = max(0.3, (last_dur - over) / last_dur)
    trim_at = int(len(last["narration"]) * keep_ratio)
    last["narration"] = last["narration"][:trim_at] + "。"

    workdir = Path(last["audio_path"]).parent
    new_path = workdir / "seg_last_trimmed.mp3"
    subprocess.run(
        ["edge-tts", "--voice", "zh-CN-XiaoxiaoNeural", "--text", last["narration"], "--write-media", str(new_path)],
        check=True, timeout=120,
    )
    last["audio_path"] = str(new_path.resolve())

    new_total = sum(durations[:-1]) + MP3(new_path).info.length
    print(f"Trimmed. New total: {new_total:.1f}s")
    json.dump({"ok": True, "total": new_total, "segments": segments}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
