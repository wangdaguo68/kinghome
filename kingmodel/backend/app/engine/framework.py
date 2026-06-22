from __future__ import annotations

from typing import Any


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def assess_market(payload: dict[str, Any]) -> dict[str, Any]:
    breadth = payload.get("breadth", {})
    capacity = payload.get("capacity", {})
    cores = payload.get("cores", [])
    ladder = payload.get("ladder", [])
    eligible = max(1, int(breadth.get("eligible", 0) or 1))
    up_ratio = 100 * float(breadth.get("up", 0)) / eligible
    median = float(breadth.get("median", 0))
    limit_up = int(breadth.get("limit_up", 0))
    limit_down = int(breadth.get("limit_down", 0))
    failed = int(breadth.get("failed_limit", 0))
    max_height = max((int(item.get("height", 0)) for item in ladder), default=0)
    capacity_ratio = 100 * float(capacity.get("up", 0)) / max(1, int(capacity.get("sample", 0) or 1))
    capacity_median = float(capacity.get("median", 0))
    trend_cores = sum(item.get("kind") == "趋势容量核心" for item in cores)
    elasticity = sum(item.get("kind") == "创业板20cm弹性核心" for item in cores)

    money = _clamp(
        up_ratio * 0.35 + max(0, median + 2) * 7 + min(limit_up, 120) * 0.22
        + min(len(ladder), 30) * 0.7 + max(0, capacity_median) * 4
    )
    loss = _clamp(
        (100 - up_ratio) * 0.35 + max(0, -median) * 14 + min(limit_down, 50) * 0.9
        + min(failed, 80) * 0.3 + max(0, -capacity_median) * 5
    )
    trend = _clamp(25 + capacity_ratio * 0.45 + max(0, capacity_median) * 6 + min(trend_cores, 15) * 2)
    speculation = _clamp(20 + min(limit_up, 120) * 0.3 + min(len(ladder), 30) * 1.2 + max_height * 4 + elasticity)

    if trend >= 65 and speculation >= 65:
        style = "趋势投机共振"
    elif trend >= 60 and trend >= speculation + 8:
        style = "趋势风格"
    elif speculation >= 60 and speculation >= trend + 8:
        style = "投机连板风格"
    else:
        style = "混合轮动"

    if loss >= 70 and money < 50:
        cycle = "退潮防守"
    elif money >= 65 and loss < 45:
        cycle = "主升"
    elif money >= 55 and loss >= 55:
        cycle = "高位震荡"
    elif loss < 50 and money < 55:
        cycle = "试错修复"
    else:
        cycle = "混沌轮动"

    return {
        "money": money, "loss": loss, "trend": trend, "speculation": speculation,
        "style": style, "cycle": cycle,
        "inputs": {
            "up_ratio": round(up_ratio, 2), "median": median, "limit_up": limit_up,
            "limit_down": limit_down, "failed_limit": failed, "capacity_up_ratio": round(capacity_ratio, 2),
            "capacity_median": capacity_median, "ladder_count": len(ladder), "max_height": max_height,
        },
    }


def build_feature_snapshots(payload: dict[str, Any], assessment: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    snapshots: list[tuple[str, str, dict[str, Any]]] = [("market", "ALL", assessment)]
    for sector in payload.get("mainlines", []):
        snapshots.append(("sector", str(sector.get("name", "UNKNOWN")), dict(sector)))
    for sector in payload.get("negative", []):
        snapshots.append(("sector_negative", str(sector.get("name", "UNKNOWN")), dict(sector)))
    ladder_by_code = {str(item.get("code", "")): item for item in payload.get("ladder", [])}
    for core in payload.get("cores", []):
        code = str(core.get("code", ""))
        snapshots.append(("stock", code, {**core, "ladder": ladder_by_code.get(code), "market_context": assessment}))
    return snapshots
