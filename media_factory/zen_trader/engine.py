import json

from zen_trader.config import Settings
from zen_trader.exceptions import GenerationError
from zen_trader.models import EnrichedContent, MarketReview
from zen_trader.providers import get_provider
from zen_trader.providers.base import AbstractAIProvider
from zen_trader.prompts import (
    get_system_prompt,
    get_user_template,
)


class ZenTraderEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider: AbstractAIProvider = get_provider(settings)

    def enrich(self, review: MarketReview) -> EnrichedContent:
        tech_analysis = self._analyze_technicals(review)
        philosophy = self._map_philosophy(review, tech_analysis)
        return self._build_enriched(review, tech_analysis, philosophy)

    def _analyze_technicals(self, review: MarketReview) -> str:
        system = get_system_prompt("base")
        user = get_user_template("tech_analysis").format(raw_text=review.raw_text)
        model = self.settings.ai.stage_1_model or self.settings.ai.model
        try:
            return self.provider.chat(system_prompt=system, user_prompt=user, model=model)
        except Exception as e:
            raise GenerationError(f"Stage 1 (technical analysis) failed: {e}") from e

    def _map_philosophy(self, review: MarketReview, tech_analysis: str) -> str:
        system = get_system_prompt("base")
        user = get_user_template("philosophy_mapping").format(
            tech_analysis=tech_analysis,
            market_context=review.raw_text[:3000],
        )
        model = self.settings.ai.stage_2_model or self.settings.ai.model
        try:
            return self.provider.chat(system_prompt=system, user_prompt=user, model=model)
        except Exception as e:
            raise GenerationError(f"Stage 2 (philosophy mapping) failed: {e}") from e

    def _build_enriched(
        self,
        review: MarketReview,
        tech_analysis: str,
        philosophy: str,
    ) -> EnrichedContent:
        technical_patterns = self._extract_list(tech_analysis, "技术形态")
        buddhist_mappings = self._extract_mappings(philosophy, "佛法映射")
        cognitive_biases = self._extract_list(philosophy, "认知偏差")
        philosophical_themes = self._extract_list(philosophy, "哲学主题")
        key_narrative = self._extract_section(philosophy, "核心叙事") or ""

        return EnrichedContent(
            market_summary=review.raw_text[:500],
            technical_patterns=technical_patterns,
            buddhist_mappings=buddhist_mappings,
            cognitive_biases=cognitive_biases,
            philosophical_themes=philosophical_themes,
            key_narrative=key_narrative,
        )

    def generate_text(
        self,
        system_name: str,
        template_name: str,
        **template_vars,
    ) -> str:
        system = get_system_prompt(system_name)
        user = get_user_template(template_name).format(**template_vars)
        model = self.settings.ai.generator_model or self.settings.ai.model
        return self.provider.chat(system_prompt=system, user_prompt=user, model=model)

    def generate_visual(
        self,
        template_name: str,
        **template_vars,
    ) -> str:
        system = get_system_prompt("visual")
        user = get_user_template(template_name).format(**template_vars)
        model = self.settings.ai.visual_model or self.settings.ai.model
        return self.provider.chat(system_prompt=system, user_prompt=user, model=model)

    @staticmethod
    def _extract_section(text: str, heading: str) -> str | None:
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("##") and heading in line:
                idx = text.index(line) + len(line)
                rest = text[idx:]
                next_section = None
                for h2 in ["## ", "### "]:
                    pos = rest.find("\n" + h2)
                    if pos != -1 and (next_section is None or pos < next_section):
                        next_section = pos
                content = rest[:next_section] if next_section else rest
                return content.strip()
        return None

    @staticmethod
    def _extract_list(text: str, heading: str) -> list[str]:
        section = ZenTraderEngine._extract_section(text, heading)
        if not section:
            return []
        items = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                item = line.lstrip("-*• ").strip()
                if item:
                    items.append(item)
        return items

    @staticmethod
    def _extract_mappings(text: str, heading: str) -> list[dict]:
        section = ZenTraderEngine._extract_section(text, heading)
        if not section:
            return []
        mappings = []
        for line in section.split("\n"):
            line = line.strip()
            if not line or not (line.startswith("-") or line.startswith("*")):
                continue
            content = line.lstrip("-*• ").strip()
            parts = content.split("：", 1)
            if len(parts) == 2:
                mappings.append({"concept": parts[0].strip(), "application": parts[1].strip()})
            elif content:
                mappings.append({"concept": content, "application": ""})
        return mappings
