from __future__ import annotations

from statistics import median
from typing import Any

from .market_validation import is_trade_candidate


def _code(value: str) -> str:
    return str(value or "").split(".", 1)[0]


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _matches_any(text: str, names: list[str]) -> bool:
    return any(name and text and (name in text or text in name) for name in names)


def _amount_label(amount: float) -> str:
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.1f}亿"
    return f"{amount / 10_000:.0f}万"


def build_capacity_cores(
    market_rows: list[dict[str, Any]] | None,
    *,
    mainlines: list[dict[str, Any]] | None = None,
    sector_linkage: list[dict[str, Any]] | None = None,
    reference_rows: list[dict[str, Any]] | None = None,
    limit_codes: set[str] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Select large-liquidity trend candidates from same-day daily rows.

    These are not limit-up emotion names. They answer: where is big money still
    willing to carry risk, and which tradable large-capacity names can be used
    for a 3-10 day plan when the market style is trend/capacity.
    """

    rows = [row for row in (market_rows or []) if _float(row.get("amount")) > 0]
    if not rows:
        return []

    ranked_by_amount = sorted(rows, key=lambda row: _float(row.get("amount")), reverse=True)
    amount_top = ranked_by_amount[:120]
    changes = [_float(row.get("pct_chg")) for row in amount_top]
    market_capacity_median = round(float(median(changes)), 2) if changes else 0.0
    max_raw_amount = max((_float(row.get("amount")) for row in amount_top), default=1.0)
    # Tushare daily.amount is in thousand yuan, EastMoney f6 is in yuan.
    amount_unit = 1000.0 if max_raw_amount < 1_000_000_000 else 1.0
    max_amount = max_raw_amount * amount_unit
    mainline_names = [str(item.get("name", "")) for item in (mainlines or []) if item.get("name")]
    linkage_by_sector = {str(item.get("name", "")): item for item in (sector_linkage or []) if item.get("name")}
    reference_by_code = {str(row.get("code") or "").split(".", 1)[0]: row for row in (reference_rows or [])}
    limit_codes = limit_codes or set()

    result: list[dict[str, Any]] = []
    for rank, row in enumerate(amount_top, start=1):
        code = _code(str(row.get("ts_code") or row.get("code") or ""))
        if not code or "ST" in str(row.get("name", "")).upper() or "退" in str(row.get("name", "")):
            continue
        ref = reference_by_code.get(code, {})
        change = _float(row.get("pct_chg"))
        amount = _float(row.get("amount")) * amount_unit
        industry = str(ref.get("industry") or row.get("industry") or "未分行业")
        name = str(ref.get("name") or row.get("name") or code)
        tradable = is_trade_candidate(code)
        linkage = linkage_by_sector.get(industry)
        linkage_score = _float(linkage.get("score")) if linkage else 0.0
        mainline_match = _matches_any(industry, mainline_names)
        amount_score = min(30.0, amount / max_amount * 30.0)
        rank_score = max(0.0, 20.0 - rank * 0.12)
        change_score = max(-18.0, min(24.0, change * 2.4))
        linkage_bonus = min(16.0, linkage_score * 0.16)
        mainline_bonus = 10.0 if mainline_match else 0.0
        limit_penalty = 8.0 if code in limit_codes else 0.0
        unsupported_penalty = 14.0 if not tradable else 0.0
        score = round(max(0.0, min(100.0, 45 + amount_score + rank_score + change_score + linkage_bonus + mainline_bonus - limit_penalty - unsupported_penalty)), 1)

        tags = ["成交额前120"]
        if mainline_match:
            tags.append("主线匹配")
        if linkage and linkage_score >= 50:
            tags.append(str(linkage.get("level") or "板块联动"))
        if change > market_capacity_median:
            tags.append("强于容量中位")
        if code in limit_codes:
            tags.append("当日涨停")
        if not tradable:
            tags.append("仅观察")

        result.append(
            {
                "name": name,
                "code": code,
                "industry": industry,
                "rank": rank,
                "score": score,
                "change": round(change, 2),
                "amount": amount,
                "amount_label": _amount_label(amount),
                "capacity_median": market_capacity_median,
                "linkage_score": round(linkage_score, 1) if linkage else None,
                "linkage_level": str(linkage.get("level") or "") if linkage else "未识别",
                "mainline_match": mainline_match,
                "tradable": tradable,
                "tags": tags,
                "reason": (
                    f"成交额排名第{rank}，当日涨跌幅{change:+.2f}%，"
                    f"所属{industry}；容量中位数{market_capacity_median:+.2f}%"
                ),
                "source": "Tushare日线成交额排序",
            }
        )

    return sorted(result, key=lambda item: (-float(item["score"]), int(item["rank"])))[:limit]


def capacity_cores_as_candidates(capacity_cores: list[dict[str, Any]], *, min_score: float = 82.0) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in capacity_cores:
        if not item.get("tradable") or float(item.get("score") or 0) < min_score:
            continue
        candidates.append(
            {
                "name": item["name"],
                "code": item["code"],
                "kind": "趋势容量核心",
                "score": item["score"],
                "change": item["change"],
                "evidence": f"{item['reason']}；{','.join(item.get('tags') or [])}",
                "source": item.get("source", "容量核心筛选"),
                "confidence": "中" if item.get("mainline_match") or float(item.get("linkage_score") or 0) >= 50 else "低",
                "concepts": [item.get("industry", "")],
                "capacity_rank": item.get("rank"),
                "capacity_amount": item.get("amount"),
                "capacity_tags": item.get("tags", []),
            }
        )
    return candidates
