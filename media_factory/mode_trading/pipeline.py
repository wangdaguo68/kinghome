from core.generator import PlatformGenerator, PLATFORM_IDS
from core.provider import get_provider
from core.validator import FactChecker
from core.writer import write_all_contents
from mode_trading.parser import TradingParser
from mode_trading.prompts import SYSTEM_PROMPTS, USER_TEMPLATES


class TradingPipeline:
    def __init__(self, settings):
        self.settings = settings
        self.provider = get_provider(settings)
        self.checker = FactChecker()

    def run(self, input_data: dict) -> list[dict]:
        raw_text = input_data.get("raw_text", "") or input_data.get("markdown", "")
        platforms = input_data.get("platforms", list(PLATFORM_IDS))
        if isinstance(platforms, str):
            platforms = [p.strip() for p in platforms.split(",") if p.strip()]

        market_data = TradingParser.parse(raw_text)
        template_vars = self._build_vars(market_data)
        model = self.settings.ai.model

        results = []
        for p_id in platforms:
            if p_id not in SYSTEM_PROMPTS or p_id == "base":
                continue
            gen = PlatformGenerator(
                platform=p_id,
                system_prompt=SYSTEM_PROMPTS[p_id],
                user_template=USER_TEMPLATES[p_id],
                provider=self.provider,
                model=model,
            )
            content = gen.generate(**template_vars)

            check = self.checker.verify(content.body, raw_text)
            if not check.passed and check.warnings:
                content.body = f"[数据校验警告: {'; '.join(check.warnings)}]\n\n{content.body}"

            results.append({
                "platform": p_id,
                "title": content.title,
                "body": content.body,
                "hashtags": content.hashtags,
            })

        output_dir = f"{self.settings.paths.output_dir}/text"
        write_all_contents(results, output_dir)
        return results

    def _build_vars(self, d) -> dict:
        return {
            "market_data": d.raw_text[:2000],
            "macd_signal": d.macd_signal,
            "kdj_signal": d.kdj_signal,
            "bollinger_signal": d.bollinger_signal,
            "ma_signal": d.ma_signal,
            "volume_signal": d.volume_signal,
            "support_levels": d.support_levels,
            "resistance_levels": d.resistance_levels,
            "breadth": d.breadth,
            "north_flow": d.north_flow,
            "key_signal": d.key_signal,
            "market_summary": d.market_summary,
        }
