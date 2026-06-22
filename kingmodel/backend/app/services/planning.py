from __future__ import annotations

from typing import Any


TEMPLATES = {
    "连板情绪核心": {
        "observation": "观察竞价强度、同题材前排溢价与开盘后承接，不以单纯高开作为确认。",
        "invalidation": "竞价及开盘承接显著弱于同题材，或板块进入集中退潮。",
        "holding_period": "隔日观察",
    },
    "趋势容量核心": {
        "observation": "观察回踩承接、成交额是否保持活跃以及板块中军是否继续主动。",
        "invalidation": "放量跌破趋势结构，或所属方向由正反馈转为持续负反馈。",
        "holding_period": "3–10日",
    },
    "创业板20cm弹性核心": {
        "observation": "观察板块扩散、次日溢价和分时换手后的资金回流。",
        "invalidation": "高开低走且无有效承接，或弹性方向快速缩容。",
        "holding_period": "1–3日",
    },
}


def _is_allowed_code(code: str) -> bool:
    return code.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605"))


def build_planned_targets(
    cores: list[dict[str, Any]],
    ladder: list[dict[str, Any]],
    *,
    cycle: str,
    loss_score: float,
    freshness: str,
    negative_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    ladder_by_code = {str(item.get("code", "")): item for item in ladder}
    negative = [name for name in (negative_names or []) if name]
    threshold = 88 if loss_score >= 80 or cycle in {"退潮", "冰点"} else 80
    candidates: dict[str, dict[str, Any]] = {}

    for core in cores:
        code = str(core.get("code", ""))
        kind = str(core.get("kind", ""))
        score = float(core.get("score", 0))
        if not _is_allowed_code(code) or kind not in TEMPLATES or score < threshold:
            continue

        ladder_item = ladder_by_code.get(code)
        concepts = [str(item) for item in (ladder_item or {}).get("concepts", [])]
        if any(any(name in concept or concept in name for name in negative) for concept in concepts):
            continue

        confidence = str((ladder_item or {}).get("confidence") or ("中" if freshness == "live" else "低"))
        if confidence == "低":
            continue
        height = int((ladder_item or {}).get("height", 0))
        rank_score = score + min(height, 5) * 1.5 + (2 if confidence == "高" else 0)
        if kind == "趋势容量核心":
            rank_score += 1
        elif kind == "创业板20cm弹性核心":
            rank_score += 0.5

        candidate = {
            "name": str(core.get("name", code)),
            "code": code,
            "kind": kind,
            "score": round(rank_score, 1),
            "logic": str(core.get("evidence", "核心评分与市场反馈共振")),
            **TEMPLATES[kind],
            "source": str((ladder_item or {}).get("source") or core.get("source") or "通达信官方 MCP"),
            "confidence": confidence,
        }
        previous = candidates.get(code)
        if previous is None or candidate["score"] > previous["score"]:
            candidates[code] = candidate

    ranked = sorted(candidates.values(), key=lambda item: (-item["score"], item["code"]))[:5]
    for index, item in enumerate(ranked):
        item["priority"] = "A" if index < 2 and item["score"] >= 88 else "B"
    return ranked
