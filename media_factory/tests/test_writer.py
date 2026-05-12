from datetime import datetime
from pathlib import Path

from zen_trader.models import ImagePrompt, PlatformContent
from zen_trader.writer import write_all, write_content, write_image_prompt


def test_write_content(tmp_path):
    content = PlatformContent(
        platform="xiaohongshu",
        title="家人们，今天的盘面绝了！",
        body="今天市场真的好温柔啊✨✨✨\n像极了修行者的呼吸🌿🌿🌿",
        hashtags=["#A股", "#禅意交易"],
    )
    p = write_content(content, tmp_path)
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "家人们" in text
    assert "✨" in text


def test_write_all(tmp_path):
    c1 = PlatformContent(platform="wechat", title="禅意复盘", body="长篇深度内容...")
    c2 = PlatformContent(platform="weibo", title="每日金句", body="短线是毒药...")
    paths = write_all([c1, c2], tmp_path)
    assert len(paths) == 2
    for p in paths:
        assert p.exists()


def test_write_image_prompt(tmp_path):
    prompt = ImagePrompt(
        platform="common",
        market_sentiment="bullish",
        midjourney_prompt="A Zen monk at sunrise --ar 16:9 --style raw",
        dalle_prompt="Zen monk meditating at mountain sunrise, peaceful atmosphere",
        description_cn="一位禅师在日出山巅冥想",
    )
    p = write_image_prompt(prompt, tmp_path)
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Midjourney" in text
    assert "DALL-E" in text
