#!/usr/bin/env python3
"""Generate an image through Codex CLI's GPT Image 2 imagegen tool.

This is a Windows-native wrapper for the gpt-image-2 skill flow. It avoids the
skill's Bash script because Windows' bash.exe is often only the WSL launcher.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


IMAGE_MAGIC_PREFIXES = {
    "iVBORw0KGgo": "png",
    "/9j/": "jpg",
    "UklGR": "webp",
}
BASE64_BLOB_PATTERN = re.compile(r'"([A-Za-z0-9+/=]{200,})"')
ALLOWED_OUTPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def find_codex() -> str:
    """Find a Codex executable that works from Windows PowerShell."""
    candidates = [
        shutil.which("codex.cmd"),
        shutil.which("codex.exe"),
        shutil.which("codex"),
        str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError("codex CLI not found. Install Codex CLI and run 'codex login'.")


def list_sessions(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {p.resolve() for p in root.rglob("rollout-*.jsonl") if p.is_file()}


def extract_best_image(session_paths: list[Path]) -> bytes | None:
    best_blob: str | None = None
    for session_path in session_paths:
        try:
            lines = session_path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            flat = json.dumps(obj)
            for match in BASE64_BLOB_PATTERN.finditer(flat):
                blob = match.group(1)
                if any(blob.startswith(prefix) for prefix in IMAGE_MAGIC_PREFIXES):
                    if best_blob is None or len(blob) > len(best_blob):
                        best_blob = blob
    return base64.b64decode(best_blob) if best_blob else None


def validate_output(path: str) -> Path:
    out = Path(path).expanduser().resolve()
    if out.suffix.lower() not in ALLOWED_OUTPUT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_OUTPUT_EXTENSIONS))
        raise ValueError(f"--out must end with one of: {allowed}")
    return out


def build_instruction(prompt: str, refs: list[str]) -> str:
    instruction = "Use the imagegen tool to generate the image for this request."
    if refs:
        instruction += " Use the attached image(s) as visual reference / input for image-to-image."
    instruction += "\nRequirements: generate the image directly, return only the image, no explanation."
    instruction += "\n\nRequest:\n" + prompt
    return instruction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ref", action="append", default=[])
    parser.add_argument("--timeout-sec", type=int, default=300)
    args = parser.parse_args()

    out_path = validate_output(args.out)
    refs = [str(Path(ref).expanduser().resolve()) for ref in args.ref]
    for ref in refs:
        if not Path(ref).is_file():
            raise SystemExit(f"Reference image not found: {ref}")

    sessions_root = Path.home() / ".codex" / "sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    before = list_sessions(sessions_root)
    started = time.time()

    cmd = [
        find_codex(),
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--enable",
        "image_generation",
        "--cd",
        str(Path.cwd()),
    ]
    if refs:
        cmd.append("-i")
        cmd.extend(refs)

    try:
        proc = subprocess.run(
            cmd,
            input=build_instruction(args.prompt, refs),
            text=True,
            capture_output=True,
            timeout=args.timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"codex exec timed out after {args.timeout_sec}s") from exc

    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-30:])
        raise SystemExit(f"codex exec failed with exit={proc.returncode}\n{tail}")

    after = list_sessions(sessions_root)
    new_sessions = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if not new_sessions:
        # Some Codex builds update an existing file; scan files touched by this run.
        new_sessions = sorted(
            [p for p in after if p.stat().st_mtime >= started - 1],
            key=lambda p: p.stat().st_mtime,
        )
    if not new_sessions:
        raise SystemExit(f"No Codex rollout session found under {sessions_root}")

    image_bytes = extract_best_image(new_sessions)
    if image_bytes is None:
        raise SystemExit("Image payload not found in Codex session; imagegen may not be enabled.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
    print(out_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
