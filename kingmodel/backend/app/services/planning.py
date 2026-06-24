from __future__ import annotations

from typing import Any


TEMPLATES = {
    "连板情绪核心": {
        "observation": "只看分歧后的承接和回封质量；一字、秒板、高开缩量加速不作为买点。",
        "invalidation": "竞价及开盘承接弱于同题材前排，或板块出现集中退潮、炸板扩散。",
        "holding_period": "隔日观察",
    },
    "趋势容量核心": {
        "observation": "优先等回踩均线/分时承接后的低吸或换手确认，不追当日高潮。",
        "invalidation": "放量跌破趋势结构，或所属方向由正反馈转为持续负反馈。",
        "holding_period": "3–10日",
    },
    "创业板20cm弹性核心": {
        "observation": "只做板块扩散后的换手回流确认；高开过多或缩量一致不追。",
        "invalidation": "高开低走且无有效承接，或弹性方向快速缩容。",
        "holding_period": "1–3日",
    },
}


def _is_allowed_code(code: str) -> bool:
    return code.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605"))


def _matches_any(concepts: list[str], names: list[str]) -> bool:
    if not concepts or not names:
        return False
    return any(name and concept and (name in concept or concept in name) for name in names for concept in concepts)


def _confidence_score(confidence: str) -> float:
    return {"高": 4.0, "中": 0.0, "低": -10.0}.get(confidence, -4.0)


def _payoff_label(kind: str, height: int, mainline_match: bool) -> tuple[str, float]:
    if kind == "趋势容量核心":
        return "中等胜率 / 中高盈亏比：只接受回踩承接买点", 8.0
    if kind == "创业板20cm弹性核心":
        return "低中胜率 / 高盈亏比：只接受换手回流买点", 6.0 if mainline_match else 2.0
    if height >= 4:
        return "低胜率 / 高波动：最高板只可作为情绪锚，交易门槛极高", -10.0
    if height == 3:
        return "中低胜率 / 中等盈亏比：只接受分歧转强", -2.0
    return "中等胜率 / 中等盈亏比：低位主线补涨试错", 5.0


def _setup(kind: str, height: int, is_max_height: bool) -> str:
    if kind == "趋势容量核心":
        return "主线容量核心分歧回踩"
    if kind == "创业板20cm弹性核心":
        return "20cm弹性核心换手回流"
    if is_max_height and height >= 4:
        return "最高板情绪锚，仅分歧回封观察"
    if height >= 3:
        return "连板核心分歧转强"
    return "低位主线补涨试错"


def build_planned_targets(
    cores: list[dict[str, Any]],
    ladder: list[dict[str, Any]],
    *,
    cycle: str,
    loss_score: float,
    freshness: str,
    negative_names: list[str] | None = None,
    mainline_names: list[str] | None = None,
    market_data_complete: bool = True,
) -> list[dict[str, Any]]:
    if freshness != "live" or not market_data_complete:
        return []

    ladder_by_code = {str(item.get("code", "")): item for item in ladder}
    max_height = max((int(item.get("height", 0) or 0) for item in ladder), default=0)
    negative = [name for name in (negative_names or []) if name]
    mainlines = [name for name in (mainline_names or []) if name]
    hard_risk = loss_score >= 80 or cycle in {"退潮", "退潮防守", "冰点"}
    execute_threshold = 86 if hard_risk else 78
    candidates: dict[str, dict[str, Any]] = {}

    for core in cores:
        code = str(core.get("code", ""))
        kind = str(core.get("kind", ""))
        raw_score = float(core.get("score", 0) or 0)
        if not _is_allowed_code(code) or kind not in TEMPLATES or raw_score < 82:
            continue

        ladder_item = ladder_by_code.get(code, {})
        concepts = [str(item) for item in ladder_item.get("concepts", []) if str(item)]
        if _matches_any(concepts, negative):
            continue

        confidence = str(ladder_item.get("confidence") or core.get("confidence") or "中")
        if confidence == "低":
            continue

        height = int(ladder_item.get("height", 0) or 0)
        is_max_height = height > 0 and height == max_height
        if is_max_height and height >= 4:
            continue
        mainline_match = _matches_any(concepts, mainlines)
        if not mainlines:
            mainline_match = kind in {"趋势容量核心", "创业板20cm弹性核心"}

        # 最高板是情绪温度计，不是默认交易标的；4板以上默认只进连板梯队观察，不进正式计划。

        # 3板以上的非主线连板，只保留观察，不进入正式计划。
        if kind == "连板情绪核心" and height >= 3 and mainlines and not mainline_match:
            continue

        score = raw_score
        score += _confidence_score(confidence)
        score += 8 if mainline_match else -4
        score -= max(0.0, loss_score - 45) * 0.25

        payoff_note, payoff_bonus = _payoff_label(kind, height, mainline_match)
        score += payoff_bonus

        if kind == "趋势容量核心":
            score += 5
        elif kind == "创业板20cm弹性核心":
            score += 2
            if abs(float(core.get("change", 0) or 0)) >= 19.8:
                score -= 4
        elif kind == "连板情绪核心":
            score += 3 if height <= 2 else 0
            score -= max(0, height - 2) * 3
            if is_max_height and height >= 4:
                score -= 12

        if score < execute_threshold:
            continue

        setup = _setup(kind, height, is_max_height)
        logic = str(core.get("evidence", "核心评分与市场反馈共振"))
        if kind == "连板情绪核心" and height >= 4:
            logic = f"{logic}；注意：该股为高位连板，只作为情绪锚，必须等待分歧回封确认。"
        else:
            logic = f"{logic}；买点类型：{setup}。"

        candidate = {
            "name": str(core.get("name", code)),
            "code": code,
            "kind": kind,
            "score": round(score, 1),
            "logic": logic,
            **TEMPLATES[kind],
            "setup": setup,
            "payoff": payoff_note,
            "risk_note": "市场亏钱效应较强，宁可空仓也不追高。" if hard_risk else "仅在计划买点出现时执行，不做盘中冲动追高。",
            "source": str(ladder_item.get("source") or core.get("source") or "本地规则引擎"),
            "confidence": confidence,
        }
        previous = candidates.get(code)
        if previous is None or candidate["score"] > previous["score"]:
            candidates[code] = candidate

    ranked = sorted(candidates.values(), key=lambda item: (-item["score"], item["code"]))[:3]
    for index, item in enumerate(ranked):
        item["priority"] = "A" if index == 0 and item["score"] >= 88 else "B"
    return ranked
