import os

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from zen_trader.config import Settings
from zen_trader.exceptions import (
    AIAuthError,
    AIRateLimitError,
    AIServerError,
    AITimeoutError,
    AITokenLimitError,
)
from zen_trader.providers.base import AbstractAIProvider


def _classify_error(e: Exception) -> None:
    err_text = str(e).lower()
    err_name = type(e).__name__.lower()
    if isinstance(e, openai.AuthenticationError):
        raise AIAuthError(str(e)) from e
    if isinstance(e, openai.RateLimitError):
        raise AIRateLimitError(str(e)) from e
    if isinstance(e, openai.InternalServerError):
        raise AIServerError(str(e)) from e
    if "timeout" in err_text or "timed out" in err_text or "timeout" in err_name:
        raise AITimeoutError(f"AI 接口 { _timeout_seconds() } 秒内没有返回，请稍后重试或换更快模型") from e
    if "token" in err_text or "context length" in err_text:
        raise AITokenLimitError(str(e)) from e
    raise AIServerError(str(e)) from e


def _timeout_seconds() -> float:
    try:
        return float(os.getenv("AI_TIMEOUT_SECONDS", "90"))
    except ValueError:
        return 90.0


class OpenAIProvider(AbstractAIProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = openai.OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.ai.api_base or None,
            timeout=_timeout_seconds(),
            max_retries=0,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        return self._call(system_prompt, user_prompt, model, max_tokens, temperature)

    @retry(
        retry=retry_if_exception_type((AIRateLimitError, AIServerError)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            response = self.client.chat.completions.create(
                model=model or self.settings.ai.model,
                max_tokens=max_tokens or self.settings.ai.max_tokens,
                temperature=temperature or self.settings.ai.temperature,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except (openai.AuthenticationError, openai.RateLimitError,
                openai.InternalServerError) as e:
            _classify_error(e)
            raise
        except Exception as e:
            _classify_error(e)
            raise
