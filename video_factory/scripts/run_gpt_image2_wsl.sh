#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="/mnt/c/Users/Administrator/.agents/skills/gpt-image-2"
TMP_DIR="/tmp/gpt-image-2-skill"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/scripts"

python3 - "$SKILL_DIR/scripts/gen.sh" "$TMP_DIR/scripts/gen.sh" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
dst.write_bytes(src.read_bytes().replace(b"\r\n", b"\n"))
PY

cp "$SKILL_DIR/scripts/extract_image.py" "$TMP_DIR/scripts/extract_image.py"
chmod +x "$TMP_DIR/scripts/gen.sh"

exec bash "$TMP_DIR/scripts/gen.sh" "$@"
