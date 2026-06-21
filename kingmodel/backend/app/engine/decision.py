from dataclasses import dataclass


@dataclass(frozen=True)
class MarketInputs:
    up_ratio: float
    median_change: float
    limit_up: int
    limit_down: int
    failed_limit: int
    continuation_rate: float
    trend_strength: float
    speculation_strength: float
    loss_spreading: bool = False


def clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def score_market(data: MarketInputs) -> dict[str, int]:
    money = clamp(
        data.up_ratio * 0.45
        + max(0, data.median_change + 3) * 5
        + min(data.limit_up, 100) * 0.3
        + data.continuation_rate * 0.2
    )
    loss = clamp(
        (100 - data.up_ratio) * 0.45
        + max(0, -data.median_change) * 12
        + min(data.limit_down, 50) * 0.8
        + min(data.failed_limit, 80) * 0.25
        + (12 if data.loss_spreading else 0)
    )
    return {
        "money": money,
        "loss": loss,
        "trend": clamp(data.trend_strength),
        "speculation": clamp(data.speculation_strength),
    }


def classify_cycle(scores: dict[str, int]) -> str:
    money, loss = scores["money"], scores["loss"]
    if loss >= 70 and money < 50:
        return "退潮防守"
    if money >= 65 and loss < 45:
        return "主升"
    if money >= 55 and loss >= 55:
        return "高波动分歧"
    if loss < 50 and money < 55:
        return "试错修复"
    return "混沌轮动"


def position_limit(cycle: str, loss_score: int) -> int:
    base = {
        "退潮防守": 10,
        "试错修复": 35,
        "主升": 75,
        "高波动分歧": 40,
        "混沌轮动": 25,
    }.get(cycle, 20)
    return min(base, 20) if loss_score >= 75 else base
