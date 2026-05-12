from abc import ABC, abstractmethod

from zen_trader.engine import ZenTraderEngine
from zen_trader.models import EnrichedContent, PlatformContent


class AbstractPlatformGenerator(ABC):
    platform_name: str = ""
    system_prompt_id: str = ""
    user_template_id: str = ""

    def __init__(self, engine: ZenTraderEngine):
        self.engine = engine

    def generate(self, content: EnrichedContent, **extra_context) -> PlatformContent:
        template_vars = self._build_template_vars(content, **extra_context)
        raw = self.engine.generate_text(
            system_name=self.system_prompt_id,
            template_name=self.user_template_id,
            **template_vars,
        )
        return self._parse_response(raw)

    def _build_template_vars(
        self, content: EnrichedContent, **extra
    ) -> dict:
        return {
            "market_summary": content.market_summary,
            "technical_patterns": "\n".join(
                f"- {p}" for p in content.technical_patterns
            ) if content.technical_patterns else "无特定形态",
            "buddhist_mappings": "\n".join(
                f"- {m.get('concept', '')}: {m.get('application', '')}"
                for m in content.buddhist_mappings
            ) if content.buddhist_mappings else "无",
            "cognitive_biases": "\n".join(
                f"- {b}" for b in content.cognitive_biases
            ) if content.cognitive_biases else "无特定偏差",
            "philosophical_themes": "\n".join(
                f"- {t}" for t in content.philosophical_themes
            ) if content.philosophical_themes else "无",
            "key_narrative": content.key_narrative,
            "sentiment": extra.get("sentiment", "neutral"),
            "default_style": extra.get("default_style", "chinese_ink_blend"),
            "aspect_ratio": extra.get("aspect_ratio", "16:9"),
        }

    def _parse_response(self, raw: str) -> PlatformContent:
        return PlatformContent(
            platform=self.platform_name,
            title=self._extract_title(raw),
            body=raw.strip(),
            hashtags=self._extract_hashtags(raw),
        )

    @staticmethod
    def _extract_title(text: str) -> str:
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("# ") or line.startswith("【"):
                return line.lstrip("# ").strip()
            if line and len(line) <= 40:
                return line
        return ""

    @staticmethod
    def _extract_hashtags(text: str) -> list[str]:
        import re
        tags = re.findall(r"#[一-鿿\w]+", text)
        return list(set(tags))
