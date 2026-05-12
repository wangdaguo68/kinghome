from zen_trader.generators.base import AbstractPlatformGenerator
from zen_trader.generators.xiaohongshu import XiaohongshuGenerator
from zen_trader.generators.wechat import WeChatGenerator
from zen_trader.generators.xueqiu import XueqiuGenerator
from zen_trader.generators.shipinhao import ShipinhaoGenerator

GENERATOR_REGISTRY: dict[str, type[AbstractPlatformGenerator]] = {
    "xiaohongshu": XiaohongshuGenerator,
    "wechat": WeChatGenerator,
    "xueqiu": XueqiuGenerator,
    "shipinhao": ShipinhaoGenerator,
    "weibo": ShipinhaoGenerator,  # weibo shares shipinhao logic
}


def get_generator(platform: str, engine) -> AbstractPlatformGenerator:
    gen_cls = GENERATOR_REGISTRY.get(platform)
    if gen_cls is None:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Available: {list(GENERATOR_REGISTRY.keys())}"
        )
    return gen_cls(engine)
