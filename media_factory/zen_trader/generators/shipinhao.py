import re

from zen_trader.generators.base import AbstractPlatformGenerator
from zen_trader.models import PlatformContent


class ShipinhaoGenerator(AbstractPlatformGenerator):
    platform_name = "shipinhao"
    system_prompt_id = "shipinhao"
    user_template_id = "shipinhao"

    def _parse_response(self, raw: str) -> PlatformContent:
        golden_quote = ""
        m = re.search(r"【每日禅语】\s*\n?\s*(.+?)(?:\n|$)", raw)
        if m:
            golden_quote = m.group(1).strip()
            raw_with_quote = raw.replace(m.group(0), f"**{golden_quote}**", 1)
        else:
            raw_with_quote = raw

        return PlatformContent(
            platform=self.platform_name,
            title=golden_quote or "每日禅语",
            body=raw_with_quote.strip(),
            hashtags=self._extract_hashtags(raw),
        )
