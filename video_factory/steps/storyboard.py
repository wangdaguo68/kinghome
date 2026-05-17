import json
import os

import requests

from pipeline.context import PipelineContext
from pipeline.base import Step

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are a video scriptwriter. Given news items, produce a short video script in Chinese.

Output valid JSON only:
{
  "segments": [
    {
      "narration": "旁白文本...",
      "image_prompt": "用于AI图片生成的英文prompt，匹配该段内容",
      "duration_est": 15.0
    }
  ]
}

Rules:
- Each segment's narration should be 30-80 Chinese characters
- duration_est is estimated speaking time in seconds (Chinese ~3 chars/sec)
- image_prompt must be in English, editorial illustration style, no text in image
- Total segments: use the number specified in the prompt"""


class Step(Step):
    def __init__(self, config: dict):
        self.config = config

    def run(self, ctx: PipelineContext) -> None:
        news_items = ctx.artifacts.get("news_items", [])
        if not news_items:
            raise RuntimeError("No news_items in context. Run fetch_news first.")

        tone = self.config.get("tone", "punchy")
        num_segments = len(news_items)

        news_text = "\n\n".join(
            f"{i + 1}. {item['title']}\n   {item['description']}"
            for i, item in enumerate(news_items)
        )

        user_prompt = (
            f"Topic: {ctx.topic}\n"
            f"Tone: {tone}\n"
            f"Create {num_segments} segments, one per news item.\n\n"
            f"News:\n{news_text}"
        )

        segments = self._call_llm(user_prompt)
        ctx.artifacts["segments"] = segments
        ctx.log(f"storyboard: generated {len(segments)} segments")

    def _call_llm(self, user_prompt: str) -> list[dict]:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY env var not set")

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        resp = requests.post(ANTHROPIC_URL, json=body, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"]

        parsed = json.loads(text) if "```" not in text else json.loads(
            text.split("```json")[1].split("```")[0].strip()
        )
        return parsed["segments"]
