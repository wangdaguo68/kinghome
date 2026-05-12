import re
from dataclasses import dataclass, field

from core.provider import AbstractAIProvider


@dataclass
class PlatformContent:
    platform: str
    title: str = ""
    body: str = ""
    hashtags: list[str] = field(default_factory=list)


class PlatformGenerator:
    def __init__(
        self,
        platform: str,
        system_prompt: str,
        user_template: str,
        provider: AbstractAIProvider,
        model: str | None = None,
    ):
        self.platform = platform
        self.system_prompt = system_prompt
        self.user_template = user_template
        self.provider = provider
        self.model = model

    def generate(self, **template_vars) -> PlatformContent:
        user_prompt = self.user_template.format(**template_vars)
        raw = self.provider.chat(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            model=self.model,
        )
        return self._parse(raw)

    def _parse(self, raw: str) -> PlatformContent:
        title = self._extract_title(raw)
        hashtags = self._extract_hashtags(raw)
        return PlatformContent(
            platform=self.platform,
            title=title,
            body=raw.strip(),
            hashtags=hashtags,
        )

    def _extract_title(self, text: str) -> str:
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line.lstrip("# ").strip()
            if (line.startswith("【") or "绝了" in line or "家人们" in line) and len(line) <= 50:
                return line
        for line in text.split("\n"):
            line = line.strip()
            if line and len(line) <= 40:
                return line
        return ""

    @staticmethod
    def _extract_hashtags(text: str) -> list[str]:
        tags = re.findall(r"#[一-鿿\w]+", text)
        return list(dict.fromkeys(tags))


PLATFORM_IDS = ["xiaohongshu", "wechat", "weibo", "shipinhao"]

PLATFORM_LABELS = {
    "xiaohongshu": "小红书",
    "wechat": "公众号",
    "weibo": "微博",
    "shipinhao": "短视频脚本",
}
