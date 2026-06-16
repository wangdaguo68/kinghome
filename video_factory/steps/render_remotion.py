#!/usr/bin/env python3
"""Render the prepared Remotion template and copy the mp4 to the requested path."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent / "remotion_template"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, help="Final mp4 output path")
    p.add_argument("--composition", default="MainScene")
    p.add_argument("--entry", default="src\\index.ts")
    args = p.parse_args()

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    local_name = f"_render_{int(time.time())}.mp4"
    local_out = TEMPLATE_DIR / local_name
    if local_out.exists():
        local_out.unlink()

    cmd = ["npx.cmd", "remotion", "render", args.entry, args.composition, local_name]
    result = subprocess.run(cmd, cwd=str(TEMPLATE_DIR), text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)
    if not local_out.exists():
        raise SystemExit(f"Render completed but output not found: {local_out}")

    shutil.copy2(local_out, out)
    local_out.unlink()
    print(str(out))


if __name__ == "__main__":
    main()
