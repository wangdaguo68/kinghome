# Video Factory

Run the full Video Factory workflow for the user's request:

```text
$ARGUMENTS
```

The user expects one command to produce a finished video without follow-up
questions unless a hard prerequisite is missing. Prefer sensible defaults:
Hacker News top 100, 3-5 selected items, about 60 seconds, vertical 9:16,
Chinese narration, `zh-CN-XiaoxiaoNeural`, and output under
`output/vf_<yyyyMMdd_HHmmss>/`.

## Workflow

1. Create a task id and work directory:
   - `output/vf_<yyyyMMdd_HHmmss>/workdir`
   - final video: `output/vf_<yyyyMMdd_HHmmss>/final.mp4`
2. Generate the Hacker News storyboard and audio:
   ```powershell
   python main.py hn-storyboard --topic "Hacker News 热点" --out-dir output\vf_<id>\workdir --duration 60 --limit 100 --count 5
   ```
3. Read `segments.json`.
4. For each segment, generate an image with the built-in `image_gen` tool.
   Use `segments[i].image_prompt` as the prompt. Do not use `gpt-image-2`
   unless the user explicitly asks for that path.
5. Copy each generated image from the Codex generated-images directory into the
   work directory as `seg_00.png`, `seg_01.png`, etc. Leave the original
   generated image in place.
6. Update `segments.json` so every segment has `image_path` pointing to the
   copied image.
7. Prepare Remotion:
   ```powershell
   python main.py compose-remotion --segments output\vf_<id>\workdir\segments.json --topic "Hacker News 热点" --aspect 9:16 --seg-dur 10
   ```
8. Render the video through the project helper. It renders inside the Remotion
   template first, then copies to `output`, avoiding Windows FFmpeg permission
   issues with parent-directory outputs:
   ```powershell
   python main.py render-remotion --out output\vf_<id>\final.mp4
   ```
9. Confirm `final.mp4` exists and report only the important paths:
   - final video
   - workdir
   - selected `news_items.json`

## Failure Handling

- If Hacker News fetch fails due to network, say the network layer failed and
  include the failed command.
- If `edge-tts` is missing, install/use it only if allowed by the environment;
  otherwise report the missing dependency.
- If built-in `image_gen` fails, stop and report that image generation failed;
  do not silently fall back to stock images.
- On Windows PowerShell, use `python main.py render-remotion`; it uses
  `npx.cmd` internally and avoids direct FFmpeg writes outside the template
  directory.
- If Remotion render fails because dependencies are missing, run `npm install`
  in `steps/remotion_template` if allowed, then retry once.

Keep the run non-interactive. Do not ask the user to choose stories, approve
prompts, or confirm intermediate files.
