import hashlib
import json
from datetime import date

from app.config import get_settings
from app.gateway.providers.base import BaseProvider, StoryPrompt
from app.gateway.providers.claude import ClaudeProvider
from app.gateway.providers.deepseek import DeepSeekProvider
from app.gateway.providers.qwen import QwenProvider

settings = get_settings()


def _make_cache_key(*args, **kwargs) -> str:
    raw = json.dumps({"args": args, "kwargs": {k: str(v) for k, v in kwargs.items()}}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


class QuotaExceededError(Exception):
    def __init__(self, limit: int | float, used: int):
        self.limit = limit
        self.used = used
        super().__init__(f"Quota exceeded: {used}/{limit}")


class ModelRouter:
    LIMITS = {
        "free": {"story": 3, "chat": 10, "exercise": 10},
        "monthly": {"story": float("inf"), "chat": 200, "exercise": float("inf")},
        "yearly": {"story": float("inf"), "chat": 500, "exercise": float("inf")},
    }

    COST_MAP = {
        "story": "high",
        "chat": "high",
        "exercise": "low",
        "lookup": "low",
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._providers: dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self):
        if settings.anthropic_api_key:
            self._providers["claude"] = ClaudeProvider()
        if settings.deepseek_api_key:
            self._providers["deepseek"] = DeepSeekProvider()
        if settings.qwen_api_key:
            self._providers["qwen"] = QwenProvider()

    def get_available_models(self) -> list[dict]:
        return [
            {"id": name, "name": p.name, "cost_input": p.cost_per_1k_input, "cost_output": p.cost_per_1k_output}
            for name, p in self._providers.items()
        ]

    def _pick_provider(self, task: str, preferred: str | None = None) -> BaseProvider:
        if preferred and preferred in self._providers:
            return self._providers[preferred]

        cost_tier = self.COST_MAP.get(task, "high")
        if cost_tier == "low":
            for name in ("deepseek", "qwen"):
                if name in self._providers:
                    return self._providers[name]

        return self._providers.get("claude") or next(iter(self._providers.values()))

    async def check_quota(self, user_id: str, user_plan: str, task: str) -> bool:
        limit = self.LIMITS.get(user_plan, self.LIMITS["free"]).get(task, 0)
        if limit == float("inf"):
            return True
        if not self.redis:
            return True  # no redis = no quota enforcement in dev
        today = date.today().isoformat()
        key = f"quota:{user_id}:{task}:{today}"
        used = int(await self.redis.get(key) or 0)
        return used < limit

    async def consume_quota(self, user_id: str, task: str):
        if not self.redis:
            return
        today = date.today().isoformat()
        key = f"quota:{user_id}:{task}:{today}"
        await self.redis.incr(key)
        await self.redis.expire(key, 86400)

    async def generate_story_chapter(
        self, prompt: StoryPrompt, user_id: str, user_plan: str, preferred_model: str | None = None
    ) -> dict:
        if not await self.check_quota(user_id, user_plan, "story"):
            limit = self.LIMITS[user_plan]["story"]
            raise QuotaExceededError(limit, limit)

        cache_key = _make_cache_key("story", prompt)
        if self.redis and (cached := await self.redis.get(cache_key)):
            return json.loads(cached)

        provider = self._pick_provider("story", preferred_model)
        result = await provider.generate_story_chapter(prompt)

        if self.redis:
            await self.redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=86400)

        await self.consume_quota(user_id, "story")
        return result

    async def generate_exercises(
        self, story_context: str, exercise_type: str, lang: str,
        user_id: str, user_plan: str, preferred_model: str | None = None,
    ) -> list[dict]:
        if not await self.check_quota(user_id, user_plan, "exercise"):
            limit = self.LIMITS[user_plan]["exercise"]
            raise QuotaExceededError(limit, limit)

        cache_key = _make_cache_key("exercise", story_context, exercise_type, lang)
        if self.redis and (cached := await self.redis.get(cache_key)):
            return json.loads(cached)

        provider = self._pick_provider("exercise", preferred_model)
        result = await provider.generate_exercises(story_context, exercise_type, lang)

        if self.redis:
            await self.redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=86400)

        await self.consume_quota(user_id, "exercise")
        return result

    async def chat(
        self, messages: list[dict], character_context: str, lang: str,
        user_id: str, user_plan: str, preferred_model: str | None = None,
    ) -> str:
        if not await self.check_quota(user_id, user_plan, "chat"):
            limit = self.LIMITS[user_plan]["chat"]
            raise QuotaExceededError(limit, limit)

        provider = self._pick_provider("chat", preferred_model)
        result = await provider.chat(messages, character_context, lang)

        await self.consume_quota(user_id, "chat")
        return result

    async def lookup_word(
        self, word: str, context: str, lang: str, preferred_model: str | None = None,
    ) -> dict:
        cache_key = _make_cache_key("lookup", word, context, lang)
        if self.redis and (cached := await self.redis.get(cache_key)):
            return json.loads(cached)

        provider = self._pick_provider("lookup", preferred_model)
        result = await provider.lookup_word(word, context, lang)

        if self.redis:
            await self.redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=86400)

        return result


router = ModelRouter()
