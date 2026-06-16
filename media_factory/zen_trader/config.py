import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_base: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    stage_1_model: Optional[str] = None
    stage_2_model: Optional[str] = None
    generator_model: Optional[str] = None
    visual_model: Optional[str] = None


class RetryConfig(BaseModel):
    max_attempts: int = 3
    base_delay_seconds: float = 1.0


class PathsConfig(BaseModel):
    input_dir: str = "input"
    output_dir: str = "output"
    output_format: str = "md"


class PlatformParams(BaseModel):
    max_chars: int = 1500
    emoji_density: Optional[str] = None
    include_section_numbers: Optional[bool] = None
    golden_quote_max_chars: Optional[int] = None
    hashtag_count: Optional[int] = None


class PlatformsConfig(BaseModel):
    enabled: list[str] = Field(
        default_factory=lambda: ["xiaohongshu", "wechat", "xueqiu", "shipinhao", "weibo"]
    )
    xiaohongshu: PlatformParams = Field(default_factory=lambda: PlatformParams(max_chars=1500))
    wechat: PlatformParams = Field(default_factory=lambda: PlatformParams(max_chars=3500))
    xueqiu: PlatformParams = Field(default_factory=lambda: PlatformParams(max_chars=2000))
    shipinhao: PlatformParams = Field(
        default_factory=lambda: PlatformParams(max_chars=200, golden_quote_max_chars=30)
    )
    weibo: PlatformParams = Field(
        default_factory=lambda: PlatformParams(max_chars=280, hashtag_count=3)
    )


class ImageConfig(BaseModel):
    default_style: str = "chinese_ink_blend"
    aspect_ratio: str = "16:9"
    generate_midjourney: bool = True
    generate_dalle: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Optional[str] = None


class Settings(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    platforms: PlatformsConfig = Field(default_factory=PlatformsConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # 运行时注入 (不从 YAML 加载)
    anthropic_api_key: str = ""
    openai_api_key: str = ""


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _apply_cli_overrides(settings: Settings, cli: Optional[dict]) -> Settings:
    if not cli:
        return settings
    if cli.get("provider"):
        settings.ai.provider = cli["provider"]
    if cli.get("model"):
        settings.ai.model = cli["model"]
    if cli.get("api_base"):
        settings.ai.api_base = cli["api_base"]
    if cli.get("temperature") is not None:
        settings.ai.temperature = cli["temperature"]
    if cli.get("output_dir"):
        settings.paths.output_dir = cli["output_dir"]
    if cli.get("platforms"):
        settings.platforms.enabled = [
            p.strip() for p in cli["platforms"].split(",")
        ]
    return settings


def load_settings(
    config_path: Optional[str] = None,
    cli_overrides: Optional[dict] = None,
) -> Settings:
    load_dotenv()

    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
    config_path = Path(config_path)

    yaml_data = _load_yaml(config_path)

    ai_raw = yaml_data.get("ai", {})
    ai_config = AIConfig(
        provider=ai_raw.get("provider", "anthropic"),
        model=ai_raw.get("model", "claude-sonnet-4-20250514"),
        api_base=ai_raw.get("api_base") or os.getenv("API_BASE"),
        max_tokens=ai_raw.get("max_tokens", 4096),
        temperature=ai_raw.get("temperature", 0.7),
        stage_1_model=ai_raw.get("stage_1_model"),
        stage_2_model=ai_raw.get("stage_2_model"),
        generator_model=ai_raw.get("generator_model"),
        visual_model=ai_raw.get("visual_model"),
    )

    retry_raw = yaml_data.get("retry", {})
    retry_config = RetryConfig(
        max_attempts=retry_raw.get("max_attempts", 3),
        base_delay_seconds=retry_raw.get("base_delay_seconds", 1.0),
    )

    paths_raw = yaml_data.get("paths", {})
    paths_config = PathsConfig(
        input_dir=paths_raw.get("input_dir", "input"),
        output_dir=paths_raw.get("output_dir", "output"),
        output_format=paths_raw.get("output_format", "md"),
    )

    platforms_raw = yaml_data.get("platforms", {})
    platforms_config = PlatformsConfig(
        enabled=platforms_raw.get(
            "enabled",
            ["xiaohongshu", "wechat", "xueqiu", "shipinhao", "weibo"],
        ),
        xiaohongshu=PlatformParams(**platforms_raw.get("xiaohongshu", {})),
        wechat=PlatformParams(**platforms_raw.get("wechat", {})),
        xueqiu=PlatformParams(**platforms_raw.get("xueqiu", {})),
        shipinhao=PlatformParams(**platforms_raw.get("shipinhao", {})),
        weibo=PlatformParams(**platforms_raw.get("weibo", {})),
    )

    image_raw = yaml_data.get("image", {})
    image_config = ImageConfig(
        default_style=image_raw.get("default_style", "chinese_ink_blend"),
        aspect_ratio=image_raw.get("aspect_ratio", "16:9"),
        generate_midjourney=image_raw.get("generate_midjourney", True),
        generate_dalle=image_raw.get("generate_dalle", True),
    )

    logging_raw = yaml_data.get("logging", {})
    logging_config = LoggingConfig(
        level=logging_raw.get("level", "INFO"),
        file=logging_raw.get("file"),
    )

    settings = Settings(
        ai=ai_config,
        retry=retry_config,
        paths=paths_config,
        platforms=platforms_config,
        image=image_config,
        logging=logging_config,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
    )

    settings = _apply_cli_overrides(settings, cli_overrides)
    return settings
