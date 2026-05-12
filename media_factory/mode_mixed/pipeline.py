from pathlib import Path

from zen_trader.config import Settings
from zen_trader.engine import ZenTraderEngine
from zen_trader.generators import GENERATOR_REGISTRY, get_generator
from zen_trader.parser import parse_review
from zen_trader.writer import write_content


class MixedPipeline:
    """Mode C: 薄包装层——直接调用现有 ZenTraderEngine，不重复实现。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = ZenTraderEngine(settings)

    def run(self, input_data: dict) -> list[dict]:
        raw_text = input_data.get("raw_text", "") or input_data.get("markdown", "")
        platforms = input_data.get("platforms", [])
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",") if p.strip()]

        tmp = Path("input/_web_temp.md")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(raw_text, encoding="utf-8")
        review = parse_review(tmp)

        enriched = self.engine.enrich(review)

        results = []
        for platform in platforms:
            if platform not in GENERATOR_REGISTRY:
                continue
            gen = get_generator(platform, self.engine)
            content = gen.generate(enriched, sentiment=review.trader_sentiment)
            text_dir = Path(self.settings.paths.output_dir) / "text"
            filepath = write_content(content, text_dir)
            results.append({
                "platform": platform,
                "title": content.title,
                "body": content.body,
                "hashtags": content.hashtags,
                "file": str(filepath),
            })

        return results
