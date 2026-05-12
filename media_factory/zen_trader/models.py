from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketReview(BaseModel):
    """从 Markdown 笔记解析出的结构化市场数据"""

    source_file: str = ""
    date: Optional[str] = None
    market_indices: dict[str, float] = Field(default_factory=dict)
    technical_indicators: dict[str, str] = Field(default_factory=dict)
    volume_data: dict[str, str] = Field(default_factory=dict)
    key_observations: list[str] = Field(default_factory=list)
    trader_sentiment: str = "neutral"
    specific_stocks: list[str] = Field(default_factory=list)
    raw_text: str = ""


class CrawlerData(BaseModel):
    """爬虫抓取的市场情绪数据"""

    date: str = ""
    consecutive_limit_up_height: int = 0
    consecutive_limit_up_stock: str = ""
    limit_up_count: int = 0
    limit_down_count: int = 0
    advance_decline_ratio: str = ""
    total_volume_yuan: str = ""
    north_bound_flow_yuan: str = ""
    market_sentiment: str = "neutral"
    raw_summary: str = ""
    technical_indicators: dict = Field(default_factory=dict)
    index_spot: dict = Field(default_factory=dict)


class EnrichedContent(BaseModel):
    """AI 引擎加工后的富内容"""

    market_summary: str = ""
    technical_patterns: list[str] = Field(default_factory=list)
    buddhist_mappings: list[dict] = Field(default_factory=list)
    cognitive_biases: list[str] = Field(default_factory=list)
    philosophical_themes: list[str] = Field(default_factory=list)
    key_narrative: str = ""


class PlatformContent(BaseModel):
    """单个平台的生成内容"""

    platform: str
    title: str = ""
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    token_usage: dict = Field(default_factory=dict)


class ImagePrompt(BaseModel):
    """封面图提示词"""

    platform: str = "common"
    market_sentiment: str = "neutral"
    midjourney_prompt: str = ""
    dalle_prompt: str = ""
    description_cn: str = ""
    style: str = "chinese_ink_blend"
