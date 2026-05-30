import json
from openai import AsyncOpenAI
from app.config import get_settings
from app.gateway.providers.base import BaseProvider, StoryPrompt


class QwenProvider(BaseProvider):
    """通义千问 provider - strong Chinese, low cost"""
    name = "qwen"
    cost_per_1k_input = 0.0005
    cost_per_1k_output = 0.002

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = "qwen-turbo"

    async def _json_chat(self, prompt: str, max_tokens: int = 4096) -> dict | list:
        resp = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.choices[0].message.content)

    async def generate_story_chapter(self, prompt: StoryPrompt) -> dict:
        prev = prompt.previous_context or "第一章"
        user = (
            "你是一位历史学者和语言教师。请用{}写一个历史故事的第{}章。"
            "地点：{}，时代：{}，难度：CEFR {}。"
            "前情：{}。"
            "返回JSON，包含字段：title, title_en, content_original, content_translation, "
            "vocabulary (词表数组), cultural_notes (文化注释数组)。"
        ).format(prompt.lang, prompt.chapter, prompt.region, prompt.era, prompt.level, prev)
        return await self._json_chat(user, 4096)

    async def generate_exercises(self, story_context: str, exercise_type: str, lang: str) -> list[dict]:
        prompt = (
            "基于以下文本为{}学习者生成5道{}练习题。"
            "文本：{}。"
            '返回JSON对象，key为"exercises"，数组元素含：question, context, options, correct_index, explanation。'
        ).format(lang, exercise_type, story_context[:2000])
        result = await self._json_chat(prompt, 2048)
        return result if isinstance(result, list) else result.get("exercises", [])

    async def chat(self, messages: list[dict], character_context: str, lang: str) -> str:
        system = (
            "角色扮演：{}。用{}对话。保持角色一致性。如有语法错误，添加修改建议。"
        ).format(character_context, lang)
        resp = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system}]
            + [{"role": m["role"], "content": m["content"]} for m in messages],
        )
        return resp.choices[0].message.content

    async def lookup_word(self, word: str, context: str, lang: str) -> dict:
        prompt = (
            '解释词语"{}"（{}）。语境：{}。返回JSON：{{word, phonetic, meaning, example, etymology}}。'
        ).format(word, lang, context)
        return await self._json_chat(prompt, 512)
