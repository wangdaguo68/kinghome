from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoryPrompt:
    era: str
    region: str
    level: str
    lang: str
    chapter: int
    previous_context: str | None = None


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def cost_per_1k_input(self) -> float: ...

    @property
    @abstractmethod
    def cost_per_1k_output(self) -> float: ...

    @abstractmethod
    async def generate_story_chapter(self, prompt: StoryPrompt) -> dict: ...

    @abstractmethod
    async def generate_exercises(self, story_context: str, exercise_type: str, lang: str) -> list[dict]: ...

    @abstractmethod
    async def chat(self, messages: list[dict], character_context: str, lang: str) -> str: ...

    @abstractmethod
    async def lookup_word(self, word: str, context: str, lang: str) -> dict: ...
