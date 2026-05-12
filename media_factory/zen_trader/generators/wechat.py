from zen_trader.generators.base import AbstractPlatformGenerator
from zen_trader.models import PlatformContent


class WeChatGenerator(AbstractPlatformGenerator):
    platform_name = "wechat"
    system_prompt_id = "wechat"
    user_template_id = "wechat"

    def _parse_response(self, raw: str) -> PlatformContent:
        title = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break
        if not title:
            title = "禅意复盘"

        return PlatformContent(
            platform=self.platform_name,
            title=title,
            body=raw.strip(),
            hashtags=[],
        )
