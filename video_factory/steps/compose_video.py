import json
from pathlib import Path

from pipeline.context import PipelineContext
from pipeline.base import Step

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


class Step(Step):
    def __init__(self, config: dict):
        self.config = config

    def run(self, ctx: PipelineContext) -> None:
        segments = ctx.artifacts.get("segments", [])
        if not segments:
            raise RuntimeError("No segments in context. Run media_gen first.")

        aspect = self.config.get("aspect", "9:16")
        aspect_css = aspect.replace(":", " / ")

        workdir = Path("output") / ctx.task_id / "workdir"
        workdir.mkdir(parents=True, exist_ok=True)

        # use relative paths for local file references inside HTML
        json_segments = []
        for seg in segments:
            json_segments.append({
                "narration": seg["narration"],
                "image_path": seg.get("image_path", ""),
                "audio_path": seg.get("audio_path", ""),
            })

        html = HTML_TEMPLATE.format(
            title=ctx.topic,
            aspect_css=aspect_css,
            segments_json=json.dumps(json_segments, ensure_ascii=False),
        )

        html_path = workdir / "video.html"
        html_path.write_text(html, encoding="utf-8")
        ctx.artifacts["html_path"] = str(html_path.resolve())
        ctx.log("compose: hyperframes HTML generated")
