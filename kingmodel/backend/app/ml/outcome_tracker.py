from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import load_market_bars, load_pending_shadow_plans, save_plan_outcomes, upsert_market_bars
from ..services.tushare_fallback import TushareFallback
from ..services.free_market import EastMoneyFreeClient


HORIZONS = (1, 3, 5, 10)
LABEL_VERSION = "next-open-v2"
ENTRY_RULE = "影子标签：次日（计划日后首个交易日）开盘价买入，不代表真实盘中触发买点。"
EXIT_RULE_TEMPLATE = "影子标签：持有{horizon}个交易日后按收盘价退出；未模拟止损、止盈、回封失败或盘中卖点。"
SAMPLE_TYPE = "shadow_label_not_backtest"


def calculate_outcomes(code: str, bars: list[dict[str, Any]], cost_rate: float = 0.0015) -> list[tuple[int, dict[str, Any]]]:
    if not bars:
        return []
    entry = bars[0]
    entry_price = float(entry.get("open") or 0)
    limit_factor = 0.20 if code.startswith(("300", "301")) else 0.10
    one_price_limit = (
        entry_price > 0 and abs(float(entry.get("high") or 0) - entry_price) < 0.001
        and abs(float(entry.get("low") or 0) - entry_price) < 0.001
        and float(entry.get("pre_close") or 0) > 0
        and entry_price >= float(entry["pre_close"]) * (1 + limit_factor - 0.002)
    )
    tradable = entry_price > 0 and float(entry.get("volume") or 0) > 0 and not one_price_limit
    outcomes: list[tuple[int, dict[str, Any]]] = []
    for horizon in HORIZONS:
        if len(bars) < horizon:
            continue
        window = bars[:horizon]
        close = float(window[-1].get("close") or 0)
        gross = close / entry_price - 1 if tradable and close > 0 else 0.0
        mfe = max(float(row.get("high") or 0) / entry_price - 1 for row in window) if tradable else 0.0
        mae = min(float(row.get("low") or 0) / entry_price - 1 for row in window) if tradable else 0.0
        payoff_ratio = round(mfe / abs(mae), 4) if tradable and mae < 0 else None
        outcomes.append((horizon, {
            "entry_trade_date": entry["trade_date"], "exit_trade_date": window[-1]["trade_date"],
            "entry_price": entry_price, "exit_price": close, "tradable": tradable,
            "gross_return": round(gross, 6), "net_return": round(gross - cost_rate if tradable else 0.0, 6),
            "mfe": round(mfe, 6), "mae": round(mae, 6), "cost_rate": cost_rate,
            "payoff_ratio": payoff_ratio,
            "holding_days": horizon,
            "sample_type": SAMPLE_TYPE,
            "is_backtest": False,
            "entry_rule": ENTRY_RULE,
            "exit_rule": EXIT_RULE_TEMPLATE.format(horizon=horizon),
            "execution_model": "next_open_fixed_horizon",
            "label_version": LABEL_VERSION,
            "blocked_reason": "一字涨停不可成交" if one_price_limit else None,
        }))
    return outcomes


class OutcomeTracker:
    def __init__(self, client: EastMoneyFreeClient, tushare: TushareFallback | None = None) -> None:
        self.client = client
        self.tushare = tushare

    async def backfill(self, current_trade_date: str) -> dict[str, Any]:
        pending = [row for row in load_pending_shadow_plans() if row["trade_date"] < current_trade_date]
        fetched = tushare_fetched = completed = failed = 0
        errors: list[dict[str, str]] = []
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for item in pending:
            code = str(item["code"])
            try:
                bars = load_market_bars(code, item["trade_date"])
                if len(bars) < 10:
                    try:
                        fetched += 1
                        rows = await self.client.stock_bars(code, 40)
                        source = "东方财富免费日线"
                    except Exception as exc:
                        if not self.tushare or not self.tushare.configured:
                            raise exc
                        tushare_fetched += 1
                        rows = await self.tushare.stock_bars(code, item["trade_date"], 40)
                        source = "Tushare备用日线"
                    upsert_market_bars(code, rows, source, now)
                    bars = [row for row in rows if row["trade_date"] > item["trade_date"]]
                outcomes = calculate_outcomes(code, bars)
                if outcomes:
                    save_plan_outcomes(item["trade_date"], item["plan_version"], code, outcomes, now)
                    completed += len(outcomes)
            except Exception as exc:
                failed += 1
                errors.append({"trade_date": str(item["trade_date"]), "code": code, "error": str(exc)[:160]})
                continue
        return {
            "pending_plans": len(pending),
            "free_requests": fetched,
            "tushare_requests": tushare_fetched,
            "failed_requests": failed,
            "outcomes_written": completed,
            "errors": errors[:8],
        }
