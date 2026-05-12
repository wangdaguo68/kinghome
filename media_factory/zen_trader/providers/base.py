from abc import ABC, abstractmethod


class AbstractAIProvider(ABC):
    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """统一接口：输入 prompt，返回 AI 生成的文本。"""
        ...
