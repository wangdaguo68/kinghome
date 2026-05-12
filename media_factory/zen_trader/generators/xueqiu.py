from zen_trader.generators.base import AbstractPlatformGenerator
from zen_trader.models import PlatformContent


class XueqiuGenerator(AbstractPlatformGenerator):
    platform_name = "xueqiu"
    system_prompt_id = "xueqiu"
    user_template_id = "xueqiu"

    def _parse_response(self, raw: str) -> PlatformContent:
        title = ""
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("##") or line.startswith("【"):
                title = line.lstrip("# ").strip()
                break
        if not title:
            title = "禅意解盘"

        return PlatformContent(
            platform=self.platform_name,
            title=title,
            body=raw.strip(),
            hashtags=self._extract_hashtags(raw),
        )
