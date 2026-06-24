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


def _execution_plan(kind: str, setup: str, *, hard_risk: bool) -> dict[str, list[str] | str]:
    common_preconditions = [
        "大盘/短线情绪没有开盘快速恶化，跌停和炸板没有明显扩散。",
        "所属板块至少有1个以上同方向标的维持正反馈，不能是孤立个股表现。",
        "个股不能是一字板、秒板或缩量加速；必须有可观察的换手和承接。",
    ]
    common_no_buy = [
        "高开过多且缩量，开盘直接一致加速，不追。",
        "开盘10分钟内放量跌破分时均价线，且反抽站不回，不买。",
        "同题材前排或板块核心先杀跌，不买。",
    ]
    if kind == "趋势容量核心":
        return {
            "entry_preconditions": [
                *common_preconditions,
                "成交额保持活跃，回踩时缩量，修复时放量。",
            ],
            "entry_trigger": [
                "回踩5日线、10日线或分时均价线附近止跌，重新放量站回均价线时低吸。",
                "若高开，必须先回落换手，二次上穿均价线再考虑。",
            ],
            "no_buy_conditions": [
                *common_no_buy,
                "放量跌破最近趋势支撑，不买。",
            ],
            "stop_loss": [
                "买入后跌破触发买点的承接位，先卖出。",
                "收盘跌破5日线且板块无修复，趋势计划失效。",
                "单笔浮亏达到-4%附近仍无资金回流，执行止损。",
            ],
            "take_profit": [
                "达到2R先锁定部分利润。",
                "趋势未破且板块继续加强，可保留底仓观察3–10日。",
                "放量冲高后回落跌破分时均价线，至少减仓。",
            ],
            "sell_plan": [
                "趋势票不以隔日冲高为唯一卖点，核心看趋势结构是否破坏。",
                "买入理由消失时，即使没到硬止损也退出。",
            ],
        }
    if kind == "创业板20cm弹性核心":
        return {
            "entry_preconditions": [
                *common_preconditions,
                "20cm方向有板块扩散或同方向首板/趋势票助攻。",
            ],
            "entry_trigger": [
                "竞价高开0%–6%且量能温和，开盘后换手不破均价线，再放量上穿时介入。",
                "分歧回落后不破开盘低点，板块同步回流时介入。",
            ],
            "no_buy_conditions": [
                *common_no_buy,
                "高开超过8%且没有换手承接，不追。",
                "直接冲20cm但板块没有扩散，不排队。",
            ],
            "stop_loss": [
                "跌破开盘低点或买点承接位，先卖。",
                "跌破分时均价线后10分钟内收不回，卖。",
                "单笔浮亏达到-5%附近仍无修复，执行止损。",
            ],
            "take_profit": [
                "冲高8%–15%但不继续加强，优先兑现一半以上。",
                "若封20cm且板块继续扩散，可保留小仓观察次日溢价。",
                "出现放量长上影或板块回落，兑现为主。",
            ],
            "sell_plan": [
                "弹性票以隔日或1–3日为主，不做无条件格局。",
                "买入理由消失时，即使没到硬止损也退出。",
            ],
        }
    return {
        "entry_preconditions": [
            *common_preconditions,
            "只能做低位补涨或分歧转强，不能做高位一致追涨。",
        ],
        "entry_trigger": [
            "竞价高开0%–5%，量能温和，开盘5–15分钟不破均价线，再放量上穿时介入。",
            "盘中分歧回落后不破关键承接位，重新放量回封时小仓确认。",
        ],
        "no_buy_conditions": [
            *common_no_buy,
            "一字板、秒板、缩量加速板不买；买不到就放弃。",
            "板块没有至少1只同方向助攻，不买。",
        ],
        "stop_loss": [
            "买入后跌破触发买点的承接位，先卖。",
            "炸板后回封失败，且板块没有修复，卖。",
            "单笔浮亏达到-3%到-4%且不快速修复，执行止损。",
        ],
        "take_profit": [
            "次日冲高不封板或明显弱于同题材前排，先减仓或兑现。",
            "达到2R先锁定部分利润，不把盈利票拿成亏损。",
            "若回封强且板块继续加强，可保留小仓到尾盘确认。",
        ],
        "sell_plan": [
            "连板/补涨票以隔日为主，不做无条件格局。",
            "买入理由消失时，即使没到硬止损也退出。",
        ],
    }


def _position_plan(priority_score: float, *, hard_risk: bool) -> str:
    if hard_risk:
        return "防守环境：即使触发买点，单票不超过5%–10%；没有完美买点直接空仓。"
    if priority_score >= 88:
        return "A级计划：满足买点后单票最多20%，禁止一次性满仓；失败立即按止损处理。"
    return "B级试错：满足买点后单票最多10%–15%；只试错，不加仓摊平。"


def build_planned_targets(
    cores: list[dict[str, Any]],
    ladder: list[dict[str, Any]],
    *,
    cycle: str,
    loss_score: float,
    freshness: str,
    negative_names: list[str] | None = None,
    mainline_names: list[str] | None = None,
    sector_linkage: list[dict[str, Any]] | None = None,
    market_data_complete: bool = True,
) -> list[dict[str, Any]]:
    if freshness != "live" or not market_data_complete:
        return []

    ladder_by_code = {str(item.get("code", "")): item for item in ladder}
    max_height = max((int(item.get("height", 0) or 0) for item in ladder), default=0)
    negative = [name for name in (negative_names or []) if name]
    mainlines = [name for name in (mainline_names or []) if name]
    linkage_by_name = {str(item.get("name", "")): item for item in (sector_linkage or [])}
    linkage_by_code: dict[str, dict[str, Any]] = {}
    for item in sector_linkage or []:
        if item.get("leader_code"):
            linkage_by_code[str(item["leader_code"])] = item
        for follower in item.get("followers", []) or []:
            if follower.get("code"):
                linkage_by_code[str(follower["code"])] = item
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
        concepts = [str(item) for item in (ladder_item.get("concepts") or core.get("concepts") or []) if str(item)]
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
        linkage = linkage_by_code.get(code) or next(
            (item for name, item in linkage_by_name.items() if any(name in concept or concept in name for concept in concepts)),
            None,
        )

        # 3板以上的非主线连板，只保留观察，不进入正式计划。
        if kind == "连板情绪核心" and height >= 3 and mainlines and not mainline_match:
            continue

        score = raw_score
        score += _confidence_score(confidence)
        score += 8 if mainline_match else -4
        score -= max(0.0, loss_score - 45) * 0.25
        if linkage:
            linkage_score = float(linkage.get("score") or 0)
            if linkage_score >= 80:
                score += 8
            elif linkage_score >= 50:
                score += 4
            elif linkage_score < 35:
                score -= 6
            if linkage.get("isolated"):
                score -= 8

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

        if score < execute_threshold:
            continue

        setup = _setup(kind, height, is_max_height)
        logic = str(core.get("evidence", "核心评分与市场反馈共振"))
        logic = f"{logic}；买点类型：{setup}。"
        execution = _execution_plan(kind, setup, hard_risk=hard_risk)

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
            "sector_linkage_score": float(linkage.get("score") or 0) if linkage else None,
            "sector_linkage_level": str(linkage.get("level") or "") if linkage else "未识别",
            "sector_linkage_evidence": list(linkage.get("evidence") or []) if linkage else [],
            "leader_effect": f"{linkage.get('leader')}带动{linkage.get('follower_count')}只后排、{linkage.get('elastic_count')}只20cm弹性" if linkage else "暂无板块联动证据",
            "followers": list(linkage.get("followers") or []) if linkage else [],
            "is_isolated": bool(linkage.get("isolated")) if linkage else False,
            **execution,
        }
        previous = candidates.get(code)
        if previous is None or candidate["score"] > previous["score"]:
            candidates[code] = candidate

    ranked = sorted(candidates.values(), key=lambda item: (-item["score"], item["code"]))[:3]
    for index, item in enumerate(ranked):
        item["priority"] = "A" if index == 0 and item["score"] >= 88 else "B"
        item["position_plan"] = _position_plan(float(item["score"]), hard_risk=hard_risk)
    return ranked
