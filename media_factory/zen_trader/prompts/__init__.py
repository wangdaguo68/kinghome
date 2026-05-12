from zen_trader.prompts.system_prompts import (
    ZEN_TRADER_BASE,
    XIAOHONGSHU_SYSTEM,
    WECHAT_SYSTEM,
    XUEQIU_SYSTEM,
    SHIPINHAO_SYSTEM,
    WEIBO_SYSTEM,
    VISUAL_PROMPT_SYSTEM,
)
from zen_trader.prompts.templates import (
    TECH_ANALYSIS_TEMPLATE,
    PHILOSOPHY_MAPPING_TEMPLATE,
    XIAOHONGSHU_USER_TEMPLATE,
    WECHAT_USER_TEMPLATE,
    XUEQIU_USER_TEMPLATE,
    SHIPINHAO_USER_TEMPLATE,
    WEIBO_USER_TEMPLATE,
    VISUAL_PROMPT_TEMPLATE,
)

SYSTEM_PROMPTS = {
    "base": ZEN_TRADER_BASE,
    "xiaohongshu": XIAOHONGSHU_SYSTEM,
    "wechat": WECHAT_SYSTEM,
    "xueqiu": XUEQIU_SYSTEM,
    "shipinhao": SHIPINHAO_SYSTEM,
    "weibo": WEIBO_SYSTEM,
    "visual": VISUAL_PROMPT_SYSTEM,
}

USER_TEMPLATES = {
    "tech_analysis": TECH_ANALYSIS_TEMPLATE,
    "philosophy_mapping": PHILOSOPHY_MAPPING_TEMPLATE,
    "xiaohongshu": XIAOHONGSHU_USER_TEMPLATE,
    "wechat": WECHAT_USER_TEMPLATE,
    "xueqiu": XUEQIU_USER_TEMPLATE,
    "shipinhao": SHIPINHAO_USER_TEMPLATE,
    "weibo": WEIBO_USER_TEMPLATE,
    "visual": VISUAL_PROMPT_TEMPLATE,
}


def get_system_prompt(name: str) -> str:
    return SYSTEM_PROMPTS[name]


def get_user_template(name: str) -> str:
    return USER_TEMPLATES[name]
