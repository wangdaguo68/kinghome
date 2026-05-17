import os
import subprocess
from pathlib import Path

from pipeline.context import PipelineContext
from pipeline.base import Step


class Step(Step):
    def __init__(self, config: dict):
        self.config = config
        self.workdir: Path | None = None

    def run(self, ctx: PipelineContext) -> None:
        segments = ctx.artifacts.get("segments", [])
        if not segments:
            raise RuntimeError("No segments in context. Run storyboard first.")

        workdir = Path("output") / ctx.task_id / "workdir"
        workdir.mkdir(parents=True, exist_ok=True)
        self.workdir = workdir

        tts_voice = self.config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        tts_speed = self.config.get("tts_speed", "+0%")

        for i, seg in enumerate(segments):
            mp3_path = workdir / f"seg_{i:02d}.mp3"
            self._tts(seg["narration"], str(mp3_path), tts_voice, tts_speed)
            seg["audio_path"] = str(mp3_path.resolve())

            png_path = workdir / f"seg_{i:02d}.png"
            self._gen_image(seg["image_prompt"], str(png_path))
            seg["image_path"] = str(png_path.resolve())

        ctx.artifacts["segments"] = segments
        ctx.log(f"media_gen: generated {len(segments)} audio + image pairs")

    def _tts(self, text: str, out_path: str, voice: str, speed: str) -> None:
        subprocess.run(
            [
                "edge-tts",
                "--voice", voice,
                "--rate", speed,
                "--text", text,
                "--write-media", out_path,
            ],
            check=True,
            timeout=120,
        )

    def _gen_image(self, prompt: str, out_path: str) -> None:
        subprocess.run(
            ["codex", "gpt-image-2", "--prompt", prompt, "--output", out_path],
            check=True,
            timeout=300,
        )
