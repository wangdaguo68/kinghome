from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime

from app.data.schemas import StockBar


@dataclass(frozen=True)
class IntradayQuote:
    symbol: str
    name: str
    price: float
    pre_close: float
    high: float
    low: float
    pct: float
    amount_billion: float
    sector_rank: int
    bid_seal_billion: float = 0
    source: str = "manual"
    updated_at: str = ""


def intraday_status() -> dict[str, object]:
    provider = os.getenv("INTRADAY_PROVIDER", "none").lower()
    qmt_ready = provider == "qmt" and os.getenv("QMT_QUOTE_ENABLED", "0") == "1"
    fallback_ready = os.getenv("INTRADAY_ALLOW_DAILY_FALLBACK", "0") == "1"
    return {
        "provider": provider,
        "ready": qmt_ready or fallback_ready,
        "realtime": qmt_ready,
        "message": "QMT 实时行情已启用" if qmt_ready else "实时行情未接入；不会生成盘中买点",
        "poll_seconds": int(os.getenv("INTRADAY_MONITOR_SECONDS", "20")),
    }


def load_intraday_quotes(stock_bars: list[StockBar]) -> tuple[dict[str, object], list[IntradayQuote]]:
    status = intraday_status()
    if status["realtime"]:
        return status, []
    if os.getenv("INTRADAY_ALLOW_DAILY_FALLBACK", "0") != "1":
        return status, []
    latest_date = max((bar.trade_date for bar in stock_bars), default=None)
    if latest_date is None:
        return status, []
    quotes = [
        IntradayQuote(
            symbol=bar.symbol,
            name=bar.name,
            price=bar.close_price,
            pre_close=bar.pre_close,
            high=bar.high_price,
            low=bar.low_price,
            pct=bar.close_pct,
            amount_billion=bar.amount_billion,
            sector_rank=bar.sector_rank,
            source="daily-fallback",
            updated_at=str(latest_date),
        )
        for bar in stock_bars
        if bar.trade_date == latest_date
    ]
    return {**status, "message": "使用日线快照调试盘中雷达，不可作为实盘买点"}, quotes


def scan_intraday_quotes(quotes: list[IntradayQuote], cycle_tag: str | None = None) -> dict[str, object]:
    now = datetime.now().isoformat(timespec="seconds")
    signals = []
    for quote in quotes:
        if _is_blocked_symbol(quote.symbol):
            continue
        signal = _first_limit_reseal(quote, cycle_tag, now) or _strong_repair(quote, cycle_tag, now)
        if signal is not None:
            signals.append(signal)
    return {
        "scanned_at": now,
        "cycle_tag": cycle_tag,
        "signal_count": len(signals),
        "signals": sorted(signals, key=lambda item: float(item["score"]), reverse=True)[:20],
    }


def _first_limit_reseal(quote: IntradayQuote, cycle_tag: str | None, now: str) -> dict[str, object] | None:
    limit_pct = 20 if quote.symbol.startswith(("300", "301")) else 10
    touched_limit = quote.high >= round(quote.pre_close * (1 + limit_pct / 100) + 1e-8, 2)
    near_limit = quote.pct >= limit_pct - 0.35
    if not touched_limit or not near_limit:
        return None
    if quote.amount_billion < float(os.getenv("INTRADAY_FIRST_LIMIT_AMOUNT_MIN", "3")):
        return None
    if quote.sector_rank > int(os.getenv("INTRADAY_FIRST_LIMIT_RANK_MAX", "300")):
        return None
    score = quote.pct + quote.amount_billion + max(0, 320 - quote.sector_rank) / 20
    return _signal_row(
        quote,
        pattern="IntradayFirstLimit",
        trigger="盘中触板/回封",
        score=score,
        planned_position_pct=6,
        stop_loss_pct=-5,
        execution_rule="只在回封有效、盘口承接不弱、成交额继续放大时人工确认；禁止追无量冲板",
        cycle_tag=cycle_tag,
        scanned_at=now,
    )


def _strong_repair(quote: IntradayQuote, cycle_tag: str | None, now: str) -> dict[str, object] | None:
    if quote.pct < float(os.getenv("INTRADAY_REPAIR_PCT_MIN", "6")):
        return None
    if quote.amount_billion < float(os.getenv("INTRADAY_REPAIR_AMOUNT_MIN", "5")):
        return None
    if quote.sector_rank > int(os.getenv("INTRADAY_REPAIR_RANK_MAX", "120")):
        return None
    score = quote.pct + quote.amount_billion + max(0, 150 - quote.sector_rank) / 18
    return _signal_row(
        quote,
        pattern="IntradayStrongRepair",
        trigger="盘中强势修复",
        score=score,
        planned_position_pct=5,
        stop_loss_pct=-4,
        execution_rule="只在分时回踩不破均线、再次放量转强时人工确认；弱转强失败直接放弃",
        cycle_tag=cycle_tag,
        scanned_at=now,
    )


def _signal_row(
    quote: IntradayQuote,
    pattern: str,
    trigger: str,
    score: float,
    planned_position_pct: float,
    stop_loss_pct: float,
    execution_rule: str,
    cycle_tag: str | None,
    scanned_at: str,
) -> dict[str, object]:
    return {
        "id": "|".join([pattern, quote.symbol, scanned_at[:10]]),
        "signal_type": "intraday",
        "scanned_at": scanned_at,
        "symbol": quote.symbol,
        "name": quote.name,
        "pattern": pattern,
        "trigger": trigger,
        "cycle_tag": cycle_tag,
        "price": quote.price,
        "pre_close": quote.pre_close,
        "pct": round(quote.pct, 2),
        "high": quote.high,
        "low": quote.low,
        "amount_billion": quote.amount_billion,
        "sector_rank": quote.sector_rank,
        "planned_position_pct": planned_position_pct,
        "stop_loss_pct": stop_loss_pct,
        "score": round(score, 2),
        "execution_rule": execution_rule,
        "source": quote.source,
        "raw": asdict(quote),
    }


def _is_blocked_symbol(symbol: str) -> bool:
    return symbol.startswith(("688", "8", "4", "9"))
