#!/usr/bin/env python3
"""Generate HyperFrames HTML from segments JSON."""

import argparse
import json
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{ --aspect: {aspect_css}; }}
  body {{ margin:0; background:#000; display:flex; justify-content:center; align-items:center; min-height:100vh; }}
  .frame {{ aspect-ratio:var(--aspect); width:100%; max-height:100vh; position:relative; overflow:hidden; background:#111; }}
  .slide {{ position:absolute; inset:0; opacity:0; transition:opacity 0.5s; display:flex; flex-direction:column; justify-content:center; align-items:center; }}
  .slide.active {{ opacity:1; }}
  .slide img {{ width:100%; height:100%; object-fit:cover; position:absolute; inset:0; }}
  .caption {{ position:absolute; bottom:8%; left:5%; right:5%; color:#fff; font-size:clamp(16px,3vw,32px); text-shadow:0 2px 8px rgba(0,0,0,0.8); text-align:center; z-index:2; padding:0 1em; }}
</style>
</head>
<body>
<div class="frame" id="frame"></div>
<audio id="audio"></audio>
<script>
const SEGMENTS = {segments_json};
const FRAME = document.getElementById('frame');
const AUDIO = document.getElementById('audio');

let current = -1;

function buildSlides() {{
  SEGMENTS.forEach((seg, i) => {{
    const div = document.createElement('div');
    div.className = 'slide';
    div.innerHTML = `<img src="${{seg.image_path}}" /><div class="caption">${{seg.narration}}</div>`;
    div.dataset.index = i;
    FRAME.appendChild(div);
  }});
}}

function playNext() {{
  const next = current + 1;
  if (next >= SEGMENTS.length) return;
  current = next;
  const seg = SEGMENTS[next];
  const prev = FRAME.querySelector('.active');
  if (prev) prev.classList.remove('active');
  const el = FRAME.querySelector(`[data-index="${{next}}"]`);
  if (el) el.classList.add('active');
  AUDIO.src = seg.audio_path;
  AUDIO.play();
  AUDIO.onended = playNext;
}}

buildSlides();
playNext();
</script>
</body>
</html>"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--segments", required=True, help="Path to segments JSON file")
    p.add_argument("--topic", required=True, help="Video topic/title")
    p.add_argument("--aspect", default="9:16", help="Aspect ratio (e.g. 9:16)")
    p.add_argument("--out", required=True, help="Output HTML file path")
    args = p.parse_args()

    segments = json.loads(Path(args.segments).read_text(encoding="utf-8"))
    aspect_css = args.aspect.replace(":", " / ")

    json_segs = [
        {"narration": s["narration"], "image_path": s.get("image_path", ""), "audio_path": s.get("audio_path", "")}
        for s in segments
    ]

    html = HTML_TEMPLATE.format(
        title=args.topic,
        aspect_css=aspect_css,
        segments_json=json.dumps(json_segs, ensure_ascii=False),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(str(out.resolve()))


if __name__ == "__main__":
    main()
