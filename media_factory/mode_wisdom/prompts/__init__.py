from mode_wisdom.prompts.system_prompts import (
    WISDOM_BASE,
    WISDOM_XHS_SYSTEM,
    WISDOM_WECHAT_SYSTEM,
    WISDOM_WEIBO_SYSTEM,
    WISDOM_SHIPINHAO_SYSTEM,
)
from mode_wisdom.prompts.templates import (
    WISDOM_XHS_TEMPLATE,
    WISDOM_WECHAT_TEMPLATE,
    WISDOM_WEIBO_TEMPLATE,
    WISDOM_SHIPINHAO_TEMPLATE,
)

SYSTEM_PROMPTS = {
    "base": WISDOM_BASE,
    "xiaohongshu": WISDOM_XHS_SYSTEM,
    "wechat": WISDOM_WECHAT_SYSTEM,
    "weibo": WISDOM_WEIBO_SYSTEM,
    "shipinhao": WISDOM_SHIPINHAO_SYSTEM,
}

USER_TEMPLATES = {
    "xiaohongshu": WISDOM_XHS_TEMPLATE,
    "wechat": WISDOM_WECHAT_TEMPLATE,
    "weibo": WISDOM_WEIBO_TEMPLATE,
    "shipinhao": WISDOM_SHIPINHAO_TEMPLATE,
}
