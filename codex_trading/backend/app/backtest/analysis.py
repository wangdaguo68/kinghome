from __future__ import annotations

from collections.abc import Callable

from app.backtest.metrics import summarize_trades
from app.data.schemas import Trade


def quality_breakdown(trades: list[Trade]) -> dict[str, list[dict[str, object]]]:
    return {
        "by_pattern": _grouped_summary(trades, lambda trade: str(trade.pattern)),
        "by_month": _grouped_summary(trades, lambda trade: trade.entry_date.strftime("%Y-%m")),
        "by_board": _grouped_summary(trades, lambda trade: board_name(trade.symbol)),
    }


def trade_reflection(trades: list[Trade]) -> dict[str, object]:
    metrics = summarize_trades(trades)
    quality = quality_breakdown(trades)
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    if metrics["trade_count"] < 30:
        suggestions.append("样本少于 30 笔，只做观察，不建议据此上调仓位。")
    elif metrics["max_drawdown_pct"] <= -8:
        suggestions.append("最大回撤偏高，下一轮应降低单票仓位或收紧开盘确认条件。")
    else:
        suggestions.append("整体回撤暂可接受，优先从亏损分组做过滤，而不是直接扩大仓位。")

    _append_group_reflections("模式", quality["by_pattern"], strengths, weaknesses, suggestions)
    _append_group_reflections("月份", quality["by_month"], strengths, weaknesses, suggestions)
    _append_group_reflections("板块", quality["by_board"], strengths, weaknesses, suggestions)

    if not strengths:
        strengths.append("暂未发现足够稳定的优势分组，需要继续扩大样本。")
    if not weaknesses:
        weaknesses.append("暂未发现需要立即剔除的亏损分组，下一步重点观察回撤和连续亏损。")

    return {
        "verdict": _verdict(metrics),
        "confidence": "样本充足" if metrics["trade_count"] >= 100 else "样本偏少",
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "suggestions": suggestions[:6],
    }


def board_name(symbol: str) -> str:
    if symbol.startswith(("300", "301")):
        return "创业板"
    return "沪深主板"


def _append_group_reflections(
    label: str,
    rows: list[dict[str, object]],
    strengths: list[str],
    weaknesses: list[str],
    suggestions: list[str],
) -> None:
    for row in rows:
        key = str(row["key"])
        metrics = row["metrics"]
        if not isinstance(metrics, dict):
            continue
        trade_count = float(metrics.get("trade_count", 0))
        total_return = float(metrics.get("total_return_pct", 0))
        win_rate = float(metrics.get("win_rate_pct", 0))
        max_drawdown = float(metrics.get("max_drawdown_pct", 0))
        profit_loss_ratio = float(metrics.get("profit_loss_ratio", 0))
        if trade_count < 5:
            continue
        if total_return > 0 and (win_rate >= 45 or profit_loss_ratio >= 2):
            strengths.append(
                f"{label} {key} 表现较强：{trade_count:g} 笔，总收益 {_pct(total_return)}，胜率 {_pct(win_rate)}。"
            )
        if total_return < 0 or max_drawdown <= -6:
            weaknesses.append(
                f"{label} {key} 表现较弱：{trade_count:g} 笔，总收益 {_pct(total_return)}，最大回撤 {_pct(max_drawdown)}。"
            )
            suggestions.append(f"下一轮对 {label} {key} 降仓或增加过滤条件，直到回测转正再恢复。")


def _verdict(metrics: dict[str, float]) -> str:
    trade_count = metrics["trade_count"]
    total_return = metrics["total_return_pct"]
    max_drawdown = metrics["max_drawdown_pct"]
    if trade_count < 30:
        return "继续观察"
    if total_return > 0 and max_drawdown > -6:
        return "可小仓验证"
    if total_return > 0:
        return "收益有效但需控回撤"
    return "暂不升级"


def _pct(value: float) -> str:
    return f"{value:+.2f}%"


def _grouped_summary(trades: list[Trade], key_fn: Callable[[Trade], str]) -> list[dict[str, object]]:
    buckets: dict[str, list[Trade]] = {}
    for trade in trades:
        buckets.setdefault(key_fn(trade), []).append(trade)

    rows = []
    for key, items in buckets.items():
        rows.append(
            {
                "key": key,
                "metrics": summarize_trades(items),
            }
        )
    return sorted(rows, key=lambda row: str(row["key"]))
