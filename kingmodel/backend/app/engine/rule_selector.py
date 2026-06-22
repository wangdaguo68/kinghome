from __future__ import annotations

from typing import Any


FEATURE_VERSION = "rule-v1"
PLAN_VERSION = "shadow-rule-v1"


def expected_value(win_rate: float, avg_win: float, avg_loss: float, costs: float = 0.0) -> float:
    """Return expectancy in R units. avg_loss and costs must be non-negative."""
    probability = max(0.0, min(1.0, win_rate))
    return probability * max(0.0, avg_win) - (1 - probability) * max(0.0, avg_loss) - max(0.0, costs)


def required_payoff_ratio(win_rate: float, costs_in_r: float = 0.0) -> float:
    """Apply the strategy floor and keep a 25% margin over break-even payoff."""
    probability = max(0.01, min(0.99, win_rate))
    strategy_floor = 3.0 if probability < 0.35 else 2.2 if probability < 0.45 else 1.8
    break_even_with_margin = (((1 - probability) + max(0.0, costs_in_r)) / probability) * 1.25
    return round(max(strategy_floor, break_even_with_margin), 2)


def passes_expectancy_gate(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    costs: float = 0.0,
) -> bool:
    if avg_loss <= 0:
        return False
    payoff = avg_win / avg_loss
    return expected_value(win_rate, avg_win, avg_loss, costs) > 0 and payoff >= required_payoff_ratio(
        win_rate, costs / avg_loss
    )


def _period(kind: str, style: str, cycle: str) -> str:
    if kind == "趋势容量核心":
        return "3日" if cycle in {"高位震荡", "混沌轮动"} else "5–10日"
    if kind == "创业板20cm弹性核心":
        return "1日" if cycle in {"高位震荡", "混沌轮动"} else "1–3日"
    return "隔日"


def build_shadow_top3(payload: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    style = str(assessment["style"])
    cycle = str(assessment["cycle"])
    loss = int(assessment["loss"])
    ladder_by_code = {str(item.get("code", "")): item for item in payload.get("ladder", [])}
    ranked: list[dict[str, Any]] = []

    if cycle == "退潮防守":
        return {"mode": "shadow", "status": "empty", "reason": "退潮防守周期触发空仓硬门槛", "plans": []}

    for core in payload.get("cores", []):
        code = str(core.get("code", ""))
        kind = str(core.get("kind", ""))
        ladder = ladder_by_code.get(code, {})
        core_score = float(core.get("score", 0))
        confidence = str(core.get("confidence") or ladder.get("confidence") or "低")

        probability = min(30, max(0, round((core_score - 55) * 0.55)))
        expectancy = 0  # 有足够走步样本前不得伪造正期望和盈亏比。
        mainline = min(15, round(core_score * 0.15))
        style_match = 4
        if ("趋势" in style and kind == "趋势容量核心") or ("投机" in style and kind == "连板情绪核心"):
            style_match = 10
        elif "共振" in style:
            style_match = 8
        tradeability = 8 if abs(float(core.get("change", 0))) < 19.9 else 6
        reliability = {"高": 10, "中": 7, "低": 3}.get(confidence, 3)
        penalty = min(20, round(max(0, loss - 45) * 0.35))
        total = max(0, min(100, probability + expectancy + mainline + style_match + tradeability + reliability - penalty))
        ranked.append({
            "code": code, "name": core.get("name", code), "kind": kind, "score": total,
            "score_breakdown": {
                "calibrated_probability": probability, "expectancy_payoff": expectancy,
                "mainline_core": mainline, "style_cycle_match": style_match,
                "tradeability": tradeability, "data_model_reliability": reliability,
                "risk_penalty": penalty,
            },
            "holding_period": _period(kind, style, cycle),
            "eligible_for_live": False,
            "blocked_reason": "走步样本不足，尚未形成可信胜率、盈亏比和正期望",
            "evidence": core.get("evidence", ""),
        })

    ranked.sort(key=lambda item: (-item["score"], item["code"]))
    plans = ranked[:3]
    previous_score = 100.1
    for index, plan in enumerate(plans):
        plan["score"] = round(min(float(plan["score"]), previous_score - 0.1), 1)
        previous_score = plan["score"]
        plan["rank"] = index + 1
    return {
        "mode": "shadow", "status": "collecting_samples", "feature_version": FEATURE_VERSION,
        "plan_version": PLAN_VERSION, "market_style": style, "cycle": cycle,
        "reason": "规则影子排名仅用于积累样本，不替换正式交易计划", "plans": plans,
    }
