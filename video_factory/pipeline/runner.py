import importlib
import time
import traceback
from pathlib import Path
from typing import Any

import yaml

from pipeline.context import PipelineContext


class Runner:
    def __init__(self, recipes_dir: Path):
        self.recipes_dir = recipes_dir

    def load_recipe(self, name: str, overrides: dict[str, Any]) -> dict:
        path = self.recipes_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Recipe not found: {path}")
        raw = path.read_text(encoding="utf-8")
        for key, val in overrides.items():
            raw = raw.replace(f"{{{{{key}}}}}", str(val))
        recipe = yaml.safe_load(raw)
        recipe["_name"] = name
        return recipe

    def run(self, recipe_name: str, topic: str, overrides: dict[str, Any]) -> PipelineContext:
        ctx = PipelineContext(topic=topic, params=overrides)
        recipe = self.load_recipe(recipe_name, overrides)

        print(f"\n=== Recipe: {recipe['name']} | Topic: {topic} ===\n")

        for step_def in recipe["steps"]:
            step_id = step_def["id"]
            module_name = step_def["module"]
            config = step_def.get("config", {})

            print(f"[{step_id}] starting...")
            ctx.log(f"step:{step_id} start")

            for attempt in range(3):
                try:
                    mod = importlib.import_module(module_name)
                    step = mod.Step(config)
                    step.run(ctx)
                    break
                except Exception as e:
                    if attempt < 2:
                        wait = 2 ** attempt
                        print(f"  retry {attempt + 1}/2 in {wait}s: {e}")
                        time.sleep(wait)
                    else:
                        print(f"  FAILED: {e}")
                        traceback.print_exc()
                        ctx.log(f"step:{step_id} error: {e}")
                        raise

            print(f"[{step_id}] done.")
            ctx.log(f"step:{step_id} done")

        print(f"\n=== Done. Output: output/{ctx.task_id}/ ===")
        return ctx
