class ZenTraderError(Exception):
    """Zen Trader 基础异常"""


class ConfigError(ZenTraderError):
    """配置相关错误"""


class ParseError(ZenTraderError):
    """Markdown 解析错误"""


class CrawlerError(ZenTraderError):
    """数据爬取错误"""


class AIError(ZenTraderError):
    """AI 调用基础异常"""


class AIAuthError(AIError):
    """API 认证失败"""


class AIRateLimitError(AIError):
    """API 限流"""


class AITokenLimitError(AIError):
    """Token 超限"""


class AIServerError(AIError):
    """服务端 5xx 错误"""


class GenerationError(ZenTraderError):
    """内容生成错误"""


class WriteError(ZenTraderError):
    """文件写入错误"""
