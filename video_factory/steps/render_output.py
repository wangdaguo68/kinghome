import subprocess
from pathlib import Path

from pipeline.context import PipelineContext
from pipeline.base import Step


class Step(Step):
    def __init__(self, config: dict):
        self.config = config

    def run(self, ctx: PipelineContext) -> None:
        html_path = ctx.artifacts.get("html_path", "")
        if not html_path or not Path(html_path).exists():
            raise RuntimeError("No html_path in context. Run compose_video first.")

        out_dir = Path("output") / ctx.task_id
        out_file = out_dir / "final.mp4"

        subprocess.run(
            [
                "hyperframes", "render",
                "--input", html_path,
                "--output", str(out_file),
            ],
            check=True,
            timeout=600,
        )

        ctx.artifacts["final_video_path"] = str(out_file.resolve())
        ctx.log(f"render: output -> {out_file}")
