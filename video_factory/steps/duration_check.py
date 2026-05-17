import subprocess
import json
from pathlib import Path

from mutagen.mp3 import MP3

from pipeline.context import PipelineContext
from pipeline.base import Step


class Step(Step):
    def __init__(self, config: dict):
        self.config = config

    def run(self, ctx: PipelineContext) -> None:
        segments = ctx.artifacts.get("segments", [])
        if not segments:
            raise RuntimeError("No segments in context. Run media_gen first.")

        max_sec = float(self.config.get("max_duration_sec", 60))
        strategy = self.config.get("strategy", "trim")

        total = 0.0
        durations = []
        for i, seg in enumerate(segments):
            audio_path = seg.get("audio_path", "")
            if audio_path and Path(audio_path).exists():
                d = MP3(audio_path).info.length
            else:
                d = seg.get("duration_est", 10.0)
            durations.append(d)
            total += d

        ctx.log(f"duration_check: total={total:.1f}s, max={max_sec}s, strategy={strategy}")

        if total <= max_sec:
            return

        over = total - max_sec

        if strategy == "error":
            raise RuntimeError(f"Duration {total:.1f}s exceeds max {max_sec}s")

        if strategy == "warn":
            print(f"  WARNING: total duration {total:.1f}s exceeds max {max_sec}s by {over:.1f}s")
            return

        if strategy == "trim":
            self._trim(segments, durations, over)

    def _trim(self, segments: list[dict], durations: list[float], over: float) -> None:
        # trim from last segment, reduce narration proportionally
        last = segments[-1]
        orig_text = last["narration"]
        last_dur = durations[-1]
        keep_ratio = max(0.3, (last_dur - over) / last_dur)
        trim_at = int(len(orig_text) * keep_ratio)
        last["narration"] = orig_text[:trim_at] + "。"

        workdir = Path(segments[-1]["audio_path"]).parent
        new_path = workdir / "seg_last_trimmed.mp3"
        subprocess.run(
            [
                "edge-tts",
                "--voice", "zh-CN-XiaoxiaoNeural",
                "--text", last["narration"],
                "--write-media", str(new_path),
            ],
            check=True,
            timeout=120,
        )
        last["audio_path"] = str(new_path.resolve())
