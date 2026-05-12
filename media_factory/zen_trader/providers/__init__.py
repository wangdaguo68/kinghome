from zen_trader.config import Settings
from zen_trader.providers.base import AbstractAIProvider
from zen_trader.providers.anthropic import AnthropicProvider
from zen_trader.providers.openai import OpenAIProvider

PROVIDER_REGISTRY: dict[str, type[AbstractAIProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def get_provider(settings: Settings) -> AbstractAIProvider:
    provider_cls = PROVIDER_REGISTRY.get(settings.ai.provider)
    if provider_cls is None:
        raise ValueError(
            f"Unsupported AI provider: {settings.ai.provider}. "
            f"Available: {list(PROVIDER_REGISTRY.keys())}"
        )
    return provider_cls(settings)


def register_provider(name: str, provider_cls: type[AbstractAIProvider]) -> None:
    PROVIDER_REGISTRY[name] = provider_cls
