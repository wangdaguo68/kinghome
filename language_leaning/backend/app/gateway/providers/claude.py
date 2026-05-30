import json
import anthropic
from app.config import get_settings
from app.gateway.providers.base import BaseProvider, StoryPrompt


class ClaudeProvider(BaseProvider):
    name = "claude"
    cost_per_1k_input = 0.015
    cost_per_1k_output = 0.075

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    async def generate_story_chapter(self, prompt: StoryPrompt) -> dict:
        system = (
            f"You are a historian and language teacher creating content for {prompt.lang} learners "
            f"at CEFR level {prompt.level}. Write engaging, historically accurate content."
        )
        prev = prompt.previous_context or "This is the first chapter."
        user = (
            f"Write chapter {prompt.chapter} of a story set in {prompt.region} during the {prompt.era} era.\n"
            f"Language: {prompt.lang}, Level: {prompt.level}\n"
            f"Previous context: {prev}\n\n"
            "Output JSON with keys: title, title_en, content_original, content_translation, "
            "vocabulary (array), cultural_notes (array)."
        )
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return json.loads(resp.content[0].text)

    async def generate_exercises(self, story_context: str, exercise_type: str, lang: str) -> list[dict]:
        prompt = (
            "Generate 5 {} exercises for {} learners based on this text:\n"
            "{}\n\n"
            'Output JSON array: [{"question": "...", "context": "...", '
            '"options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}]'
        ).format(exercise_type, lang, story_context[:2000])
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text)

    async def chat(self, messages: list[dict], character_context: str, lang: str) -> str:
        system = (
            "You are roleplaying as: {}. "
            "Speak in {}. Stay in character. Keep responses natural and conversational. "
            "After your reply, add a line with grammar fixes if the user made mistakes."
        ).format(character_context, lang)
        formatted = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=formatted,
        )
        return resp.content[0].text

    async def lookup_word(self, word: str, context: str, lang: str) -> dict:
        prompt = (
            'Explain the word/phrase "{}" in {}. Context: {}. '
            'Output JSON: {{"word": "...", "phonetic": "...", "meaning": "...", '
            '"example": "...", "etymology": "..."}}'
        ).format(word, lang, context)
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text)
