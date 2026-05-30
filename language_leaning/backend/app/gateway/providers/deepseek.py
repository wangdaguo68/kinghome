import json
from openai import AsyncOpenAI
from app.config import get_settings
from app.gateway.providers.base import BaseProvider, StoryPrompt


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    cost_per_1k_input = 0.001
    cost_per_1k_output = 0.002

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )
        self.model = "deepseek-chat"

    async def _json_chat(self, prompt: str, max_tokens: int = 4096) -> dict | list:
        resp = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.choices[0].message.content)

    async def generate_story_chapter(self, prompt: StoryPrompt) -> dict:
        prev = prompt.previous_context or "First chapter."
        user = (
            "You are a historian and language teacher. Write chapter {} of a story "
            "set in {} during the {} era. "
            "Target language: {}, CEFR level: {}. "
            "Context: {}. "
            "Return JSON with keys: title, title_en, content_original, content_translation, "
            "vocabulary (array of {{word, phonetic, meaning, example, etymology}}), "
            "cultural_notes (array of {{title, content}})."
        ).format(prompt.chapter, prompt.region, prompt.era, prompt.lang, prompt.level, prev)
        return await self._json_chat(user, 4096)

    async def generate_exercises(self, story_context: str, exercise_type: str, lang: str) -> list[dict]:
        prompt = (
            "Generate 5 {} exercises for {} learners. "
            "Text: {}. "
            'Return JSON object with key "exercises" containing array of '
            '{{question, context, options: ["A","B","C","D"], correct_index: int, explanation}}.'
        ).format(exercise_type, lang, story_context[:2000])
        result = await self._json_chat(prompt, 2048)
        return result if isinstance(result, list) else result.get("exercises", [])

    async def chat(self, messages: list[dict], character_context: str, lang: str) -> str:
        system = (
            "Roleplay: {}. Speak {}. Stay in character. "
            "Add grammar corrections if needed."
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
            'Explain "{}" in {}. Context: {}. '
            "Return JSON: {{word, phonetic, meaning, example, etymology}}."
        ).format(word, lang, context)
        return await self._json_chat(prompt, 512)
