---
name: video-factory
description: Build a complete short news video from a user request, especially Hacker News top-story requests. Use when the user invokes "$video-factory", says "video-factory", or asks to automatically fetch news, pick 3-5 items, generate visuals, narration, and render a 30-60 second MP4 without further manual steps.
---

# Video Factory

Use this skill to produce a finished MP4, not just a plan.

Codex must be launched from `D:\software\video_factory` or with `-C D:\software\video_factory` so this repository skill is discovered.

## Trigger

Typical user input:

```text
$video-factory 帮我去黑客新闻站点找热门新闻前100条，找3-5条，做成一个30-60秒的视频
```

Codex CLI uses `$skill-name` for skills. If the user types `video-factory ...` in normal text, treat it as the same workflow.

## Workflow

1. Choose a timestamp id such as `20260519_173000`.
2. Create `output\vf_<id>\workdir`.
3. Generate the story, narration, and TTS:

```powershell
python main.py hn-storyboard --topic "Hacker News 热点" --out-dir output\vf_<id>\workdir --duration 60 --limit 100 --count 5
```

Use duration and count from the user's prompt when provided. Keep count between 3 and 5 for Hacker News requests unless the user explicitly asks otherwise.

For 财联社 / CLS requests, use this instead:

```powershell
python main.py cls-storyboard --topic "财联社热点" --out-dir output\vf_cls_<id>\workdir --duration 58 --limit 20 --count 5
```

4. Open the generated `segments.json`.
5. For each segment, call the built-in `image_gen` tool using `image_prompt`. Prefer realistic, restrained editorial visuals over obvious AI-art styling.
6. Copy each generated image into the workdir as `seg_00.png`, `seg_01.png`, etc.
7. Update `segments.json` with image paths:

```powershell
python main.py set-segment-images --segments output\vf_<id>\workdir\segments.json --images output\vf_<id>\workdir\seg_00.png output\vf_<id>\workdir\seg_01.png
```

Include every generated image path in segment order.

8. Compose and render:

```powershell
python main.py compose-remotion --segments output\vf_<id>\workdir\segments.json --topic "Hacker News 热点" --aspect 9:16 --seg-dur 10
python main.py render-remotion --out output\vf_<id>\final.mp4
```

9. Verify the MP4 exists and report the absolute path.

## Rules

- Do not ask the user to choose stories, approve scripts, approve images, or run intermediate commands.
- Do not use `fetch-images` unless the user explicitly requests real web images.
- Do not use `gpt-image-2` unless the user explicitly requests it.
- Prefer the built-in `image_gen` tool for generated visuals.
- If `image_gen` returns a file path, use it directly. If needed, locate the newest PNG under `C:\Users\Administrator\.codex\generated_images`.
- Segment cuts must follow the generated MP3 durations, not fixed scene lengths.
- The video must include readable subtitles.
- Never render `image_prompt`, user prompt text, or internal workflow text into the video.
- Do not add an explainer opener that restates the user's request. Start with the first finished news segment.
- Avoid repetitive narration such as "第 1 条 / 第 2 条" or "看屏幕上的标题" for every segment. Use varied short news-anchor lines.
- For CLS / finance videos, each scene should show a news card with title, concise summary, source, heat label, and bottom subtitles. The generated image is background context, not the main information carrier.
