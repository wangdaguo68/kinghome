import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from anthropic.types import TextBlock

from zen_trader.config import Settings
from zen_trader.exceptions import (
    AIAuthError,
    AIRateLimitError,
    AIServerError,
    AITokenLimitError,
)
from zen_trader.providers.base import AbstractAIProvider


def _classify_error(e: Exception) -> None:
    if isinstance(e, anthropic.AuthenticationError):
        raise AIAuthError(str(e)) from e
    if isinstance(e, anthropic.RateLimitError):
        raise AIRateLimitError(str(e)) from e
    if isinstance(e, anthropic.InternalServerError):
        raise AIServerError(str(e)) from e
    if "token" in str(e).lower():
        raise AITokenLimitError(str(e)) from e
    raise AIServerError(str(e)) from e


class AnthropicProvider(AbstractAIProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.ai.api_base or None,
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
            msg = self.client.messages.create(
                model=model or self.settings.ai.model,
                max_tokens=max_tokens or self.settings.ai.max_tokens,
                temperature=temperature or self.settings.ai.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            for block in msg.content:
                if isinstance(block, TextBlock):
                    return block.text
            return ""
        except (anthropic.AuthenticationError, anthropic.RateLimitError,
                anthropic.InternalServerError) as e:
            _classify_error(e)
            raise
        except Exception as e:
            _classify_error(e)
            raise
