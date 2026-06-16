import json
import os
from pathlib import Path
from typing import Any

import httpx

from .models import SummaryResponse
from .prompts import (
    CHAT_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    build_chat_user_prompt,
    build_summary_user_prompt,
)


class DeepSeekClient:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def chat(self, mood_label: str, message: str, reply_mode: str = "comfort") -> str:
        if not self.configured:
            return "我听见你现在真的不轻松。先不用急着整理好自己，能说出来已经很不容易了。"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": build_chat_user_prompt(mood_label, message, reply_mode)},
            ],
            "temperature": 0.7,
            "max_tokens": 160,
        }
        data = await self._post_chat_completion(payload)
        return data["choices"][0]["message"]["content"].strip()

    async def summary(self, conversation_text: str) -> SummaryResponse:
        if not self.configured:
            return fallback_summary()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": build_summary_user_prompt(conversation_text)},
            ],
            "temperature": 0.5,
            "max_tokens": 360,
            "response_format": {"type": "json_object"},
        }
        data = await self._post_chat_completion(payload)
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            return SummaryResponse(
                keywords=list(parsed.get("keywords") or ["疲惫", "需要被理解", "压力"])[:4],
                emotion_color=str(parsed.get("emotion_color") or "暖灰蓝"),
                intensity=str(parsed.get("intensity") or "中度"),
                summary=str(parsed.get("summary") or "你今天承受了不少情绪，也许只是需要一点安静的时间。"),
                comfort_sentence=str(parsed.get("comfort_sentence") or "今晚先别责怪自己了。"),
                surface_emotion=str(parsed.get("surface_emotion") or ""),
                real_pain_point=str(parsed.get("real_pain_point") or ""),
                hidden_need=str(parsed.get("hidden_need") or ""),
                small_action=str(parsed.get("small_action") or ""),
                self_comfort_sentence=str(parsed.get("self_comfort_sentence") or ""),
            )
        except (TypeError, ValueError):
            return fallback_summary()

    async def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()


def fallback_summary() -> SummaryResponse:
    return SummaryResponse(
        keywords=["疲惫", "压力", "需要被理解"],
        emotion_color="暖灰蓝",
        intensity="中度",
        summary="你今天像是承受了不少压力，也有一些没有被好好看见的委屈。先允许自己慢一点。",
        comfort_sentence="今晚先别责怪自己了。",
        surface_emotion="疲惫和委屈",
        real_pain_point="努力没有被好好看见",
        hidden_need="被理解，也被允许休息",
        small_action="写下今天完成过的一件小事",
        self_comfort_sentence="你不需要今晚就证明自己。",
        fallback=True,
    )


def load_dotenv() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break
