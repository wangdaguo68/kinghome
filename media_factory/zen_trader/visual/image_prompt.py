from zen_trader.engine import ZenTraderEngine
from zen_trader.models import EnrichedContent, ImagePrompt

SENTIMENT_STYLE_MAP = {
    "bullish": {
        "scene": "sunrise over mountain peaks, blooming lotus flowers, golden light rays breaking through clouds",
        "mood": "serene confidence, radiant hope, boundless possibility",
        "elements": "Zen monk standing on a summit, arms open, golden sunrise, thousand-petaled lotus blooming",
    },
    "slightly_bullish": {
        "scene": "morning mist clearing over a still lake, first light on distant peaks",
        "mood": "quiet optimism, gentle awakening, patient anticipation",
        "elements": "meditator by a calm lake, mist rising, cranes taking flight, soft dawn light",
    },
    "neutral": {
        "scene": "cloud-shrouded mountain peaks, a winding path through bamboo forest",
        "mood": "balanced stillness, watchful waiting, equanimity",
        "elements": "monk walking a mountain path, bamboo grove, light filtering through leaves, middle way",
    },
    "slightly_bearish": {
        "scene": "storm clouds gathering, a lone pine tree on a cliff, rain over the ocean",
        "mood": "vigilant calm, inner stillness amid external turbulence",
        "elements": "monk meditating in a cave overlooking stormy sea, wind but no fear, lightning in distance",
    },
    "bearish": {
        "scene": "lighthouse in a violent storm, cliff edge at night, lotus rising from dark mud",
        "mood": "unyielding peace in chaos, beauty emerging from destruction, the fertile darkness",
        "elements": "monk meditating at cliff's edge, violent waves below, single lotus blooming in dark water, lighthouse beam cutting through",
    },
}


class ImagePromptGenerator:
    def __init__(self, engine: ZenTraderEngine):
        self.engine = engine

    def generate(
        self,
        content: EnrichedContent,
        sentiment: str = "neutral",
        style: str = "chinese_ink_blend",
        aspect_ratio: str = "16:9",
    ) -> ImagePrompt:
        style_data = SENTIMENT_STYLE_MAP.get(sentiment, SENTIMENT_STYLE_MAP["neutral"])

        themes = ", ".join(content.philosophical_themes[:3]) if content.philosophical_themes else "Zen wisdom"

        raw = self.engine.generate_visual(
            template_name="visual",
            market_summary=content.market_summary[:300],
            key_narrative=content.key_narrative,
            philosophical_themes=themes,
            sentiment=sentiment,
            default_style=style,
            aspect_ratio=aspect_ratio,
        )

        return self._parse_visual_response(raw, sentiment)

    def _parse_visual_response(self, raw: str, sentiment: str) -> ImagePrompt:
        mj_prompt = ""
        dalle_prompt = ""
        desc_cn = ""

        current_section = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("### Midjourney") or line.startswith("###Midjourney"):
                current_section = "mj"
                continue
            elif line.startswith("### DALL-E") or line.startswith("###DALL-E"):
                current_section = "dalle"
                continue
            elif line.startswith("### 中文描述"):
                current_section = "cn"
                continue
            elif line.startswith("###"):
                current_section = ""
                continue

            if current_section == "mj":
                mj_prompt += line + " "
            elif current_section == "dalle":
                dalle_prompt += line + " "
            elif current_section == "cn":
                desc_cn += line + " "

        return ImagePrompt(
            platform="common",
            market_sentiment=sentiment,
            midjourney_prompt=mj_prompt.strip(),
            dalle_prompt=dalle_prompt.strip(),
            description_cn=desc_cn.strip(),
            style="chinese_ink_blend",
        )
