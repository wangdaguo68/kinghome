from __future__ import annotations

from typing import Any


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _score_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _risk_adjusted_speculation_score(
    *,
    limit_up: int,
    limit_down: int,
    failed: int,
    ladder_count: int,
    max_height: int,
    elasticity_count: int,
    capacity_median: float,
    down_ratio: float,
) -> tuple[int, dict[str, float]]:
    first_boards = max(0, limit_up - ladder_count)
    failed_rate = failed / max(1, limit_up + failed)
    continuation_ratio = ladder_count / max(1, limit_up)

    activity = (
        0.35 * _score_0_100(limit_up / 100 * 100)
        + 0.25 * _score_0_100(ladder_count / 25 * 100)
        + 0.20 * _score_0_100(max_height / 7 * 100)
        + 0.10 * _score_0_100(elasticity_count / 20 * 100)
        + 0.10 * _score_0_100(first_boards / 80 * 100)
    )
    quality = (
        0.35 * _score_0_100(continuation_ratio / 0.25 * 100)
        + 0.25 * _score_0_100((1 - failed_rate) * 100)
        + 0.20 * _score_0_100(max_height / 7 * 100)
        + 0.20 * _score_0_100((capacity_median + 3) / 6 * 100)
    )
    risk = (
        0.30 * _score_0_100((limit_down - 5) / 45 * 100)
        + 0.25 * _score_0_100((failed_rate - 0.15) / 0.35 * 100)
        + 0.20 * _score_0_100((-capacity_median) / 4 * 100)
        + 0.15 * _score_0_100((down_ratio - 45) / 20 * 100)
        + 0.10 * _score_0_100((max_height - 6) / 4 * 100)
    )
    raw_score = 0.50 * activity + 0.30 * quality + 0.20 * (100 - risk)
    cap = 100
    if limit_down >= 50:
        cap = 45
    elif limit_down >= 30:
        cap = 65
    elif limit_down >= 15:
        cap = 80
    score = min(_clamp(raw_score), cap)
    return score, {
        "spec_activity": round(activity, 2),
        "spec_quality": round(quality, 2),
        "spec_risk": round(risk, 2),
        "spec_failed_rate": round(failed_rate * 100, 2),
        "spec_continuation_ratio": round(continuation_ratio * 100, 2),
        "spec_hard_cap": cap,
    }


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
    down_ratio = 100 * float(breadth.get("down", 0)) / eligible
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
    speculation, speculation_detail = _risk_adjusted_speculation_score(
        limit_up=limit_up,
        limit_down=limit_down,
        failed=failed,
        ladder_count=len(ladder),
        max_height=max_height,
        elasticity_count=elasticity,
        capacity_median=capacity_median,
        down_ratio=down_ratio,
    )

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
            **speculation_detail,
        },
    }


def build_market_permission(assessment: dict[str, Any]) -> dict[str, Any]:
    """Translate market state into executable risk permission.

    The loss score is a hard risk gate: strong speculation can identify where
    opportunities are, but it cannot override broad loss feedback.
    """
    cycle = str(assessment.get("cycle") or "")
    loss = int(assessment.get("loss") or 0)

    if loss >= 80:
        return {
            "label": "防守观察",
            "position_limit": 20,
            "allowed": "仅主线核心分歧小仓试错",
            "forbidden": "高潮追涨、中后排、容量趋势硬接",
        }
    if loss >= 70:
        return {
            "label": "谨慎试错",
            "position_limit": 30,
            "allowed": "主线核心分歧承接",
            "forbidden": "非主线轮动追涨、弱转强缩量秒板",
        }
    if cycle == "主升":
        return {
            "label": "顺风进攻",
            "position_limit": 75,
            "allowed": "主线核心分歧回踩",
            "forbidden": "非主线轮动高潮追涨",
        }
    if cycle == "高位震荡":
        return {
            "label": "谨慎进攻",
            "position_limit": 40,
            "allowed": "主线核心分歧低吸",
            "forbidden": "高潮追涨与后排补涨",
        }
    if cycle == "试错修复":
        return {
            "label": "小仓试错",
            "position_limit": 35,
            "allowed": "低位新主线试错",
            "forbidden": "老周期反抽追涨",
        }
    if cycle == "混沌轮动":
        return {
            "label": "防守观察",
            "position_limit": 25,
            "allowed": "低频等待确认",
            "forbidden": "频繁切换与非核心追涨",
        }
    return {
        "label": "防守观察",
        "position_limit": 10,
        "allowed": "空仓等待",
        "forbidden": "逆势开仓",
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
