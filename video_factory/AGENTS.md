# Video Factory for Codex CLI

This repository is meant to be driven by Codex CLI.

Launch Codex from this directory, or pass `-C D:\software\video_factory`, so Codex can discover this repository's `AGENTS.md` and `.agents\skills\video-factory` files.

When the user asks for `video-factory`, `$video-factory`, or a request equivalent to:

> go to Hacker News, pick 3-5 items from the top 100, and produce a 30-60 second video

run the complete workflow end to end. Do not stop after planning, storyboarding, or generating assets.

## Important CLI Behavior

Codex CLI slash commands such as `/help` are built-in TUI commands. This project does not rely on `.claude/commands`.

The preferred Codex entry is:

```text
$video-factory 帮我去黑客新闻站点找热门新闻前100条，找3-5条，做成一个30-60秒的视频
```

If the user types `video-factory ...` without the `$`, treat it the same way.

## Default Workflow

1. Create a unique output directory under `output\vf_<timestamp>\workdir`.
2. Run the Hacker News storyboard step:

```powershell
python main.py hn-storyboard --topic "Hacker News 热点" --out-dir output\vf_<timestamp>\workdir --duration 60 --limit 100 --count 5
```

Use `--duration 30` to `--duration 60` and `--count 3` to `--count 5` according to the user's request.

For CLS / 财联社 requests, use:

```powershell
python main.py cls-storyboard --topic "财联社热点" --out-dir output\vf_cls_<timestamp>\workdir --duration 58 --limit 20 --count 5
```

This reads the current `https://www.cls.cn/telegraph` Next.js payload, ranks visible telegraph items by `reading_num`, and creates a 50-60 second Chinese finance-news video structure.

3. Read the generated `segments.json`.
4. For every segment, call the built-in `image_gen` tool with that segment's `image_prompt`. Do not use `fetch-images` unless the user explicitly asks for web image fetching. Do not use `gpt-image-2` unless the user explicitly asks for that skill.
5. Use restrained, realistic editorial visuals. Avoid sci-fi glow, obvious AI-art effects, fake UI text, logos, or watermark-like marks.
6. Copy each generated image into the workdir as `seg_00.png`, `seg_01.png`, and so on. The image_gen tool stores files under `C:\Users\Administrator\.codex\generated_images\...`; use the path reported by the tool, or the newest generated PNG if needed.
7. Write those copied image paths back into `segments.json`:

```powershell
python main.py set-segment-images --segments output\vf_<timestamp>\workdir\segments.json --images output\vf_<timestamp>\workdir\seg_00.png output\vf_<timestamp>\workdir\seg_01.png
```

Pass all segment image paths in order.

8. Compose and render:

```powershell
python main.py compose-remotion --segments output\vf_<timestamp>\workdir\segments.json --topic "Hacker News 热点" --aspect 9:16 --seg-dur 10
python main.py render-remotion --out output\vf_<timestamp>\final.mp4
```

9. Verify the final MP4 exists, then report the absolute path.

## Notes

- This workflow needs network access for Hacker News and TTS.
- `render-remotion` intentionally renders inside the Remotion template first, then copies the MP4 to `output\...`; direct Remotion output to parent directories can fail on this Windows setup.
- Keep generated source data in the workdir: `news_items.json`, `segments.json`, audio, images, and final video.
- Segment timing is based on actual MP3 duration plus a small buffer. Do not use fixed 10-second cuts when audio is available.
- The rendered Remotion data must not include `image_prompt`, user prompts, or internal workflow text. Only show finished video fields such as title, source, and captions.
- Do not add an opening segment that restates the user's prompt. For finance/news videos, start directly with the first news item.
- Avoid repetitive "第 N 条" narration. Use concise, varied news-anchor style narration, and put detailed title/summary/heat information on the visual news card.
