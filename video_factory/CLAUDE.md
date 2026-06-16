# Video Factory Agent Notes

This project runs on Windows PowerShell. Codex CLI is the primary target; read
`AGENTS.md` first. Codex should use `$video-factory` or normal text
`video-factory ...`, not the Claude-only `.claude/commands` path.

Default image generation should use the built-in `image_gen` tool and then copy
the chosen generated file into the current task workdir. Leave the original file
under `.codex/generated_images` in place. Do not use `gpt-image-2` unless the
user explicitly requests that route.

For Hacker News videos, start with:

```powershell
python main.py hn-storyboard --topic "Hacker News 热点" --out-dir output\vf_<id>\workdir --duration 60 --limit 100 --count 5
```
