#!/usr/bin/env python3
"""Generate HyperFrames-compliant HTML from segments JSON."""

import argparse
import json
from pathlib import Path

GRADIENTS = [
    "linear-gradient(135deg, #1a0000 0%, #330011 30%, #0d001a 60%, #000000 100%)",
    "linear-gradient(160deg, #0a0a0f 0%, #1a1a2e 40%, #16213e 70%, #0f3460 100%)",
    "linear-gradient(145deg, #001a0d 0%, #0d3300 35%, #001a1a 65%, #000000 100%)",
]

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN" data-composition-variables='[{"id":"topic","type":"string","label":"Topic","default":"__TITLE__"}]'>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  [data-composition-id="root"] {
    font-family: Inter, sans-serif;
    background: #000;
    overflow: hidden;
  }
  .scene-content {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
    height: 100%;
    padding: 80px 40px;
    gap: 0;
    box-sizing: border-box;
  }
  .slide-bg {
    position: absolute;
    inset: 0;
    z-index: 0;
  }
  .overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.15) 50%, rgba(0,0,0,0.35) 100%);
    z-index: 1;
  }
  .caption {
    position: relative;
    z-index: 2;
    color: #fff;
    font-size: 38px;
    font-weight: 700;
    text-shadow: 0 2px 16px rgba(0,0,0,0.95);
    text-align: center;
    max-width: 80%;
    margin-bottom: 12%;
    line-height: 1.5;
    letter-spacing: 0.04em;
  }
  .tag {
    position: absolute;
    top: 6%;
    left: 5%;
    z-index: 10;
    color: rgba(255,255,255,0.7);
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.25em;
    padding: 8px 18px;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
  }
  .progress-wrap {
    position: absolute;
    bottom: 3%;
    left: 5%;
    right: 5%;
    height: 3px;
    background: rgba(255,255,255,0.1);
    z-index: 10;
    border-radius: 2px;
  }
  .progress-bar {
    height: 100%;
    background: rgba(255,255,255,0.55);
    border-radius: 2px;
    width: 0%;
  }
  .counter {
    position: absolute;
    bottom: 8%;
    right: 5%;
    z-index: 10;
    color: rgba(255,255,255,0.5);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.1em;
  }
</style>
</head>
<body>
<div id="root-comp" data-composition-id="root" data-width="1080" data-height="1920">

  <div id="tag-el" class="tag clip" data-start="0" data-duration="__TOTAL_DUR__" data-track-index="10">CYBERSEC BRIEFING</div>

  <div class="progress-wrap clip" data-start="0" data-duration="__TOTAL_DUR__" data-track-index="11">
    <div class="progress-bar" id="progressBar"></div>
  </div>
  <div id="counter-el" class="counter clip" data-start="0" data-duration="__TOTAL_DUR__" data-track-index="12">1 / __NUM_SEGMENTS__</div>

__SLIDES_HTML__

__AUDIO_HTML__

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    var tl = gsap.timeline({ paused: true });

    // tag entrance
    tl.from("#tag-el", { y: -24, opacity: 0, duration: 0.6, ease: "expo.out" }, 0.1);

__TIMELINE_SCRIPT__

    // progress bar
    tl.fromTo("#progressBar", { width: "0%" }, { width: "100%", duration: __TOTAL_DUR__, ease: "none" }, 0);

    window.__timelines["root"] = tl;
  </script>
</div>
</body>
</html>"""


def build_slide_html(i: int, seg: dict, gradient: str, start_t: float, dur: float) -> str:
    img_html = ""
    if seg.get("image_path"):
        fname = Path(seg["image_path"]).name
        img_html = f'<img src="{fname}" style="width:100%;height:100%;object-fit:cover;" />'

    return f"""
  <div id="slide-{i}" class="clip" data-start="{start_t}" data-duration="{dur}" data-track-index="0">
    <div class="slide-bg" style="background:{gradient};">
      {img_html}
    </div>
    <div class="overlay"></div>
    <div class="caption" id="caption-{i}">{seg['narration']}</div>
  </div>"""


def build_timeline_script(segments: list[dict], seg_dur: float) -> str:
    lines = []
    for i in range(len(segments)):
        start_t = i * seg_dur
        lines.append(f'    // slide {i} entrance')
        lines.append(f'    tl.from("#caption-{i}", {{ y: 30, opacity: 0, duration: 0.5, ease: "power3.out" }}, {start_t:.1f});')
        if i < len(segments) - 1:
            next_start = (i + 1) * seg_dur
            lines.append(f'    tl.to("#slide-{i}", {{ opacity: 0, duration: 0.3, ease: "power2.in" }}, {next_start - 0.3:.1f});')

    # counter updates
    for i in range(len(segments)):
        start_t = i * seg_dur
        lines.append(f'    tl.call(function() {{ document.getElementById("counter-el").textContent = "{i + 1} / {len(segments)}"; }}, null, {start_t:.1f});')

    return "\n".join(lines)


def build_audio_html(segments: list[dict], seg_dur: float) -> str:
    lines = []
    for i, seg in enumerate(segments):
        audio_path = seg.get("audio_path", "")
        if audio_path:
            # hyperframes serves files relative to project dir, so use just the filename
            fname = Path(audio_path).name
            lines.append(
                f'  <audio id="audio-{i}" data-start="{i * seg_dur}" data-duration="{seg_dur}" '
                f'data-track-index="{5 + i}" src="{fname}" data-volume="1"></audio>'
            )
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--segments", required=True, help="Path to segments JSON")
    p.add_argument("--topic", required=True, help="Video topic")
    p.add_argument("--aspect", default="9:16", help="Aspect ratio")
    p.add_argument("--out", required=True, help="Output HTML path")
    args = p.parse_args()

    segments = json.loads(Path(args.segments).read_text(encoding="utf-8"))
    num = len(segments)
    seg_dur = 10.0
    total_dur = num * seg_dur

    # build slides HTML
    slides_html = "\n".join(
        build_slide_html(i, seg, GRADIENTS[i % len(GRADIENTS)], i * seg_dur, seg_dur)
        for i, seg in enumerate(segments)
    )

    audio_html = build_audio_html(segments, seg_dur)
    timeline_script = build_timeline_script(segments, seg_dur)

    html = (HTML_TEMPLATE
        .replace("__TITLE__", args.topic)
        .replace("__SLIDES_HTML__", slides_html)
        .replace("__AUDIO_HTML__", audio_html)
        .replace("__TIMELINE_SCRIPT__", timeline_script)
        .replace("__TOTAL_DUR__", str(total_dur))
        .replace("__NUM_SEGMENTS__", str(num)))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(str(out.resolve()))


if __name__ == "__main__":
    main()
