from zen_trader.generators.base import AbstractPlatformGenerator
from zen_trader.models import PlatformContent


class XiaohongshuGenerator(AbstractPlatformGenerator):
    platform_name = "xiaohongshu"
    system_prompt_id = "xiaohongshu"
    user_template_id = "xiaohongshu"

    def _parse_response(self, raw: str) -> PlatformContent:
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        title = ""
        for line in lines:
            if ("绝了" in line or "家人们" in line) and len(line) <= 40:
                title = line
                break
        if not title:
            title = lines[0] if lines else ""

        return PlatformContent(
            platform=self.platform_name,
            title=title,
            body=raw.strip(),
            hashtags=self._extract_hashtags(raw),
        )
