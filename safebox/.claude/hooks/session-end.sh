#!/usr/bin/env bash
# SessionEnd hook: copy transcript to project docs/transcripts/
read -r json_input
transcript_path=$(echo "$json_input" | python3 -c "import sys,json; print(json.load(sys.stdin)['transcript_path'])")
session_id=$(echo "$json_input" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
if [ -n "$transcript_path" ] && [ -f "$transcript_path" ]; then
  dest="D:/software/safebox/docs/transcripts/${session_id}.jsonl"
  cp "$transcript_path" "$dest"
  echo "Transcript saved to $dest"
fi
