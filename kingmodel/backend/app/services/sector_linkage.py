from __future__ import annotations

from statistics import median
from typing import Any


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _stock_code(row: dict[str, Any]) -> str:
    code = str(row.get("code") or row.get("ts_code") or "")
    return code.split(".", 1)[0]


def _sector_name(row: dict[str, Any]) -> str:
    return str(row.get("industry") or row.get("concept") or "").strip()


def _linkage_level(score: float, median_change: float, limit_count: int) -> str:
    if median_change < 0 and limit_count <= 1:
        return "负联动"
    if score >= 75:
        return "强联动"
    if score >= 50:
        return "中联动"
    if score >= 35:
        return "弱联动"
    return "孤立"


def build_sector_linkage(
    limit_rows: list[dict[str, Any]],
    *,
    market_rows: list[dict[str, Any]] | None = None,
    ladder: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Score sector diffusion using free limit-up pool plus optional daily market rows.

    This deliberately avoids intraday polling. It is a close-snapshot linkage
    model: strong evidence comes from same-sector limit-up breadth, 20cm
    participation, ladder depth, capacity, and same-sector daily breadth.
    """
    ladder_by_code = {str(item.get("code", "")): item for item in (ladder or [])}
    market_by_sector: dict[str, list[dict[str, Any]]] = {}
    for row in market_rows or []:
        sector = _sector_name(row)
        if sector:
            market_by_sector.setdefault(sector, []).append(row)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in limit_rows:
        sector = _sector_name(row)
        if sector:
            grouped.setdefault(sector, []).append(row)

    results: list[dict[str, Any]] = []
    for sector, rows in grouped.items():
        limit_count = len(rows)
        if limit_count <= 0:
            continue
        sector_market = market_by_sector.get(sector, [])
        leader = max(
            rows,
            key=lambda row: (
                int(row.get("vendor_ladder") or ladder_by_code.get(str(row.get("code", "")), {}).get("height") or 1),
                _float(row.get("amount")),
                _float(row.get("change")),
            ),
        )
        leader_code = str(leader.get("code", ""))
        heights = [
            int(row.get("vendor_ladder") or ladder_by_code.get(str(row.get("code", "")), {}).get("height") or 1)
            for row in rows
        ]
        tier_count = len({height for height in heights if height > 0})
        max_height = max(heights or [1])
        elastic_rows = [row for row in rows if str(row.get("code", "")).startswith(("300", "301"))]
        low_level_rows = [row for row, height in zip(rows, heights, strict=False) if height <= 2]
        amount = sum(_float(row.get("amount")) for row in rows)

        if sector_market:
            changes = [_float(row.get("pct_chg")) for row in sector_market]
            median_change = round(float(median(changes)), 2)
            strong_count = sum(value >= 5 for value in changes)
            positive_count = sum(value > 0 for value in changes)
        else:
            changes = [_float(row.get("change")) for row in rows]
            median_change = round(float(median(changes)), 2)
            strong_count = limit_count
            positive_count = limit_count

        isolated = limit_count <= 1 or (limit_count <= 2 and strong_count <= 2 and not elastic_rows)
        score = 0.0
        score += min(35, limit_count * 6)
        score += min(15, len(elastic_rows) * 5)
        score += min(15, tier_count * 4 + max(0, max_height - 1) * 1.5)
        score += min(15, strong_count * 2)
        score += 8 if median_change > 0 else -8
        score += min(12, amount / 10_0000_0000)
        if isolated:
            score -= 18
        if median_change < -2:
            score -= 10
        score = round(max(0, min(100, score)), 1)
        level = _linkage_level(score, median_change, limit_count)
        followers = sorted(
            [
                {
                    "name": str(row.get("name") or row.get("n") or _stock_code(row)),
                    "code": str(row.get("code") or _stock_code(row)),
                    "change": round(_float(row.get("change") or row.get("pct_chg")), 2),
                    "role": "20cm弹性" if str(row.get("code", "")).startswith(("300", "301")) else "后排跟随",
                }
                for row in rows
                if str(row.get("code", "")) != leader_code
            ],
            key=lambda item: (-item["change"], item["code"]),
        )[:6]
        evidence = [
            f"涨停扩散{limit_count}只",
            f"后排跟随{max(0, limit_count - 1)}只",
            f"20cm弹性{len(elastic_rows)}只",
            f"梯队层数{tier_count}层",
            f"同板块大涨5%以上{strong_count}只",
            f"板块涨幅中位数{median_change:+.2f}%",
        ]
        risks: list[str] = []
        if isolated:
            risks.append("孤立强票，缺少后排扩散")
        if median_change < 0:
            risks.append("同板块中位数为负，后排承接不足")
        if max_height >= 4 and len(low_level_rows) <= 1:
            risks.append("高位强、低位弱，存在断层风险")

        results.append(
            {
                "name": sector,
                "score": score,
                "level": level,
                "leader": str(leader.get("name") or leader.get("n") or leader_code),
                "leader_code": leader_code,
                "limit_up_count": limit_count,
                "follower_count": max(0, limit_count - 1),
                "elastic_count": len(elastic_rows),
                "low_level_count": len(low_level_rows),
                "tier_count": tier_count,
                "max_height": max_height,
                "strong_count": strong_count,
                "positive_count": positive_count,
                "median_change": median_change,
                "amount": round(amount, 2),
                "isolated": isolated,
                "evidence": evidence,
                "followers": followers,
                "risks": risks,
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), -int(item["limit_up_count"]), item["name"]))[:8]
