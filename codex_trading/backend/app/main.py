from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_local_env
from app.backtest.analysis import quality_breakdown, trade_reflection
from app.backtest.engine import BacktestEngine
from app.backtest.fees import load_broker_fee_model
from app.backtest.versioning import (
    build_strategy_versions,
    read_strategy_version_cache,
    strategy_version_context,
    strategy_version_fingerprint,
)
from app.cycle.engine import build_cycle_states
from app.data.mysql_store import load_provider_summary
from app.data.schemas import Pattern, Signal, StockBar
from app.data.tushare_provider import TushareError, clear_market_data_cache, fetch_recent_market_data, next_open_date, token_available
from app.investment_calendar import fetch_investment_calendar
from app.live.intraday import intraday_status, load_intraday_quotes, scan_intraday_quotes
from app.live.qmt_adapter import QmtAdapter
from app.live.tracker import refresh_tracking, sync_intraday_signals, sync_tomorrow_signals, tracked_signals
from app.notify.feishu import FeishuNotifier
from app.risk.gates import AccountState, evaluate_signal
from app.research.service import scheduler_sleep_seconds, should_run_daily_sync, sync_industry_research
from app.research.store import get_research_item, list_research_items, research_sources, research_stats
from app.strategies.energy_breakout import EnergyBreakoutConfig, EnergyBreakoutStrategy
from app.strategies.extreme_arbitrage import ExtremeArbitrageStrategy
from app.strategies.experiment import PRESETS, StrategyPreset, strategies_for_preset
from app.strategies.first_limit import FirstLimitStrategy
from app.strategies.one_to_two import OneToTwoStrategy
from app.strategies.short_energy import ShortEnergyConfig, ShortEnergyStrategy

load_local_env()

CACHE_SCHEMA_VERSION = "20260607-speed-1"
MATERIALIZED_CACHE_DIR = Path(os.getenv("MATERIALIZED_CACHE_DIR", "cache/materialized"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_signal_monitor()
    start_industry_research_scheduler()
    yield


app = FastAPI(title="A-share Quant System", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:19092",
        "http://localhost:19092",
        "http://127.0.0.1:19093",
        "http://localhost:19093",
        "http://127.0.0.1:19094",
        "http://localhost:19094",
        "http://127.0.0.1:19095",
        "http://localhost:19095",
        "http://127.0.0.1:19096",
        "http://localhost:19096",
        "http://39.106.115.87:19092",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|39\.106\.115\.87):19092",
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def make_engine() -> BacktestEngine:
    return BacktestEngine(
        [ExtremeArbitrageStrategy(), FirstLimitStrategy(), OneToTwoStrategy(), EnergyBreakoutStrategy(), ShortEnergyStrategy()],
        fee_model=load_broker_fee_model(),
        capital=backtest_capital(),
    )


def backtest_capital() -> float:
    return float(os.getenv("BACKTEST_CAPITAL", "100000"))


def preset_settings(preset: StrategyPreset) -> dict[str, object]:
    return {
        "amount_min_billion": preset.amount_min_billion,
        "rank_limit": preset.rank_limit,
        "first_limit_mode": preset.first_limit_mode,
        "one_to_two_open_min_pct": preset.one_to_two_open_min_pct,
        "cycle_filter": preset.cycle_filter,
        "position_pct": preset.position_pct,
        "max_signals_per_strategy": preset.max_signals_per_strategy,
        "research_only": preset.research_only,
        "include_energy": preset.include_energy,
    }


def optimization_score(metrics: dict[str, float]) -> float:
    trade_count = metrics.get("trade_count", 0)
    if trade_count < 30:
        return -999
    return round(metrics.get("total_return_pct", 0) + metrics.get("max_drawdown_pct", 0) * 1.5, 2)


def optimization_candidates(base: StrategyPreset) -> list[StrategyPreset]:
    variants = [
        ("baseline", base.amount_min_billion, base.rank_limit, base.one_to_two_open_min_pct),
        ("tighter", base.amount_min_billion + 1, max(20, int(base.rank_limit * 0.7)), base.one_to_two_open_min_pct + 1),
        ("looser", max(1, base.amount_min_billion - 1), min(500, int(base.rank_limit * 1.25)), max(0, base.one_to_two_open_min_pct - 1)),
    ]
    return [
        StrategyPreset(
            id=f"{base.id}-{suffix}",
            name=base.name,
            description=f"{base.description} \u81ea\u4f18\u5316\u5019\u9009\uff1a\u6210\u4ea4\u989d {amount:g} \u4ebf\uff0c\u6392\u540d {rank}\uff0c\u5f00\u76d8 {open_min:g}%\u3002",
            amount_min_billion=amount,
            rank_limit=rank,
            first_limit_mode=base.first_limit_mode,
            one_to_two_open_min_pct=open_min,
            include_extreme=base.include_extreme,
            cycle_filter=base.cycle_filter,
            position_pct=base.position_pct,
            max_signals_per_strategy=base.max_signals_per_strategy,
            research_only=base.research_only,
            include_energy=base.include_energy,
        )
        for suffix, amount, rank, open_min in variants
    ]


def load_current_strategy_versions(market_days: list, stock_bars: list) -> dict[str, object]:
    latest_date = market_days[-1].trade_date if market_days else None
    latest_date_key = str(latest_date) if latest_date is not None else None
    fee_model = load_broker_fee_model()
    capital = backtest_capital()
    expected_context = strategy_version_context(PRESETS, fee_model, capital, optimization_candidates, preset_settings)
    expected_cache_key = strategy_version_fingerprint(expected_context)
    payload = read_strategy_version_cache()
    if payload is not None:
        recent = payload.get("segments", {}).get("recent", {}) if isinstance(payload.get("segments"), dict) else {}
        if recent.get("end") != latest_date_key or payload.get("cache_key") != expected_cache_key:
            payload = None
    if payload is None:
        payload = build_strategy_versions(
            PRESETS,
            market_days,
            stock_bars,
            fee_model,
            capital,
            optimization_candidates,
            preset_settings,
        )
    return payload


def tomorrow_version_map(market_days: list, stock_bars: list) -> tuple[dict[str, object], dict[str, StrategyPreset]]:
    payload = load_current_strategy_versions(market_days, stock_bars)
    candidates = {
        candidate.id: candidate
        for base in PRESETS
        for candidate in optimization_candidates(base)
    }
    selected: dict[str, StrategyPreset] = {}
    for group in payload.get("groups", []):
        if not isinstance(group, dict):
            continue
        recommended = group.get("recommended_version")
        if not isinstance(recommended, dict) or not recommended.get("eligible"):
            continue
        version_id = str(recommended.get("version_id", ""))
        candidate = candidates.get(version_id)
        if candidate is not None:
            selected[str(group.get("base_id"))] = candidate
    return payload, selected


def execution_rule(signal: Signal) -> str:
    if signal.pattern == Pattern.SHORT_ENERGY:
        return "下一交易日只在开盘承接强、题材未退潮时人工确认买入；高开过猛或后排先弱则放弃"
    if signal.pattern == Pattern.ENERGY_BREAKOUT:
        return "下一交易日开盘买入，若明显高开冲高则按人工纪律控制追价"
    if signal.pattern == Pattern.ONE_TO_TWO and signal.min_entry_open_pct is not None:
        return f"\u4ec5\u5f53\u4e0b\u4e00\u4ea4\u6613\u65e5\u5f00\u76d8\u6da8\u5e45 >= {signal.min_entry_open_pct:g}% \u65f6\u8003\u8651\u4eba\u5de5\u4e70\u5165"
    if signal.pattern == Pattern.FIRST_LIMIT:
        return "\u4e0b\u4e00\u4ea4\u6613\u65e5\u7ade\u4ef7\u548c\u5f00\u76d8\u627f\u63a5\u4e0d\u5f31\u65f6\u4eba\u5de5\u786e\u8ba4\uff0c\u7981\u6b62\u8ffd\u9ad8\u65e0\u91cf\u51b2\u677f"
    return "\u4e0b\u4e00\u4ea4\u6613\u65e5\u5f00\u76d8\u540e\u89c2\u5bdf\u5f3a\u5f31\u4fee\u590d\uff0c\u4f4e\u4e8e\u786c\u6b62\u635f\u7eaa\u5f8b\u4e0d\u53c2\u4e0e"


def tomorrow_signal_row(signal: Signal, bar: StockBar, planned_entry_date: object, cycle_tag: object) -> dict[str, object]:
    return {
        "signal_date": signal.trade_date,
        "planned_entry_date": planned_entry_date,
        "symbol": signal.symbol,
        "name": signal.name,
        "pattern": signal.pattern,
        "cycle_tag": cycle_tag,
        "planned_position_pct": signal.planned_position_pct,
        "stop_loss_pct": signal.stop_loss_pct,
        "score": round(signal.score, 2),
        "reason": signal.reason,
        "execution_rule": execution_rule(signal),
        "close_price": bar.close_price,
        "close_pct": bar.close_pct,
        "high_pct": bar.high_pct,
        "amount_billion": bar.amount_billion,
        "sector_rank": bar.sector_rank,
        "limit_up": bar.limit_up,
        "first_limit": bar.first_limit,
        "consecutive_limits": bar.consecutive_limits,
    }


def load_market_data() -> tuple[str, list, list]:
    if not token_available():
        raise HTTPException(status_code=503, detail="TUSHARE_TOKEN not configured")
    try:
        recent_days = int(os.getenv("TUSHARE_RECENT_DAYS", "250"))
        market_days, stock_bars = fetch_recent_market_data(recent_days)
        return "tushare", market_days, stock_bars
    except TushareError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Tushare data load failed: {exc}") from exc


def market_cache_token() -> str:
    recent_days = os.getenv("TUSHARE_RECENT_DAYS", "250")
    bar_limit = os.getenv("TUSHARE_STOCK_BAR_LIMIT", "500")
    summary = load_provider_summary(int(recent_days), int(bar_limit))
    latest_date = str(summary.get("latest_date")) if summary else time.strftime("%Y%m%d%H")
    return "|".join(
        [
            recent_days,
            os.getenv("TUSHARE_CYCLE_DAYS", "23"),
            bar_limit,
            latest_date,
        ]
    )


def runtime_cache_token() -> str:
    return "|".join([CACHE_SCHEMA_VERSION, market_cache_token(), str(backtest_capital()), str(load_broker_fee_model().__dict__)])


def materialized_payload(name: str, token: str, builder) -> dict[str, object]:
    MATERIALIZED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    path = MATERIALIZED_CACHE_DIR / f"{name}-{digest}.json"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return payload
        except Exception:
            path.unlink(missing_ok=True)

    payload = builder()
    encoded = jsonable_encoder(payload)
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(encoded, handle, ensure_ascii=False, separators=(",", ":"))
    tmp_path.replace(path)
    return encoded


def backtest_coverage_payload(market_days: list) -> dict[str, object]:
    recent_days = market_days[-5:]
    last_completed_entry_date = market_days[-4].trade_date if len(market_days) >= 4 else None
    return {
        "latest_date": market_days[-1].trade_date if market_days else None,
        "last_completed_entry_date": last_completed_entry_date,
        "range_days": len(market_days),
        "completion_note": "交易明细只展示已经具备 T+1/T+2 退出行情和卖后 3 日观察窗口的交易；最近 3 个交易日只纳入行情覆盖与信号筛选。",
        "recent_market_days": [
            {
                "trade_date": day.trade_date,
                "red_count": day.red_count,
                "down_count": day.down_count,
                "limit_up_count": day.limit_up_count,
                "limit_down_count": day.limit_down_count,
                "turnover_billion": day.turnover_billion,
                "sh_turnover_billion": day.sh_turnover_billion,
                "sz_turnover_billion": day.sz_turnover_billion,
            }
            for day in recent_days
        ],
    }


def load_cycle_market_data() -> tuple[str, list, list]:
    if not token_available():
        raise HTTPException(status_code=503, detail="TUSHARE_TOKEN not configured")
    try:
        recent_days = int(os.getenv("TUSHARE_CYCLE_DAYS", "23"))
        market_days, stock_bars = fetch_recent_market_data(recent_days)
        return "tushare", market_days, stock_bars
    except TushareError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Tushare data load failed: {exc}") from exc


@app.get("/api/provider")
def provider() -> dict[str, object]:
    recent_days = int(os.getenv("TUSHARE_RECENT_DAYS", "250"))
    bar_limit = int(os.getenv("TUSHARE_STOCK_BAR_LIMIT", "500"))
    summary = load_provider_summary(recent_days, bar_limit)
    if summary is not None:
        return summary

    source, market_days, stock_bars = load_market_data()
    return {
        "source": source,
        "market_days": len(market_days),
        "stock_bars": len(stock_bars),
        "latest_date": market_days[-1].trade_date if market_days else None,
    }


@app.get("/api/fee-model")
def fee_model() -> dict[str, object]:
    model = load_broker_fee_model()
    return model.__dict__


@app.get("/api/investment-calendar")
def investment_calendar(days: int = 30, force_refresh: bool = False) -> dict[str, object]:
    return fetch_investment_calendar(days=days, force_refresh=force_refresh)


@app.get("/api/industry-research")
def industry_research(
    page: int = 1,
    page_size: int = 20,
    report_type: str = "",
    source: str = "",
    industry: str = "",
    symbol: str = "",
    keyword: str = "",
) -> dict[str, object]:
    return list_research_items(
        page=page,
        page_size=page_size,
        report_type=report_type,
        source=source,
        industry=industry,
        symbol=symbol,
        keyword=keyword,
    )


@app.get("/api/industry-research/stats")
def industry_research_stats() -> dict[str, object]:
    return research_stats()


@app.get("/api/industry-research/sources")
def industry_research_sources() -> dict[str, object]:
    return research_sources()


@app.get("/api/industry-research/sync")
def industry_research_sync(force: bool = True, reset: bool = False) -> dict[str, object]:
    return sync_industry_research(force=force, reset=reset)


@app.get("/api/industry-research/{item_id}")
def industry_research_detail(item_id: int) -> dict[str, object]:
    return get_research_item(item_id)


@app.get("/api/cycles")
def cycles() -> list[dict[str, object]]:
    _, market_days, _ = load_cycle_market_data()
    return [state.__dict__ for state in build_cycle_states(market_days)]


@app.get("/api/backtest")
def backtest() -> dict[str, object]:
    return cached_backtest(runtime_cache_token())


@app.get("/api/energy-backtest")
def energy_backtest() -> dict[str, object]:
    return cached_energy_backtest(runtime_cache_token())


@app.get("/api/short-energy-backtest")
def short_energy_backtest() -> dict[str, object]:
    return cached_short_energy_backtest(runtime_cache_token())


@lru_cache(maxsize=8)
def cached_backtest(_cache_token: str) -> dict[str, object]:
    def build() -> dict[str, object]:
        source, market_days, stock_bars = load_market_data()
        result = make_engine().run(market_days, stock_bars)
        return {
            "source": source,
            **backtest_coverage_payload(market_days),
            "metrics": result.metrics,
            "trades": [trade.__dict__ for trade in result.trades],
            "rejected_count": len(result.rejected_signals),
        }

    return materialized_payload("backtest", _cache_token, build)


@lru_cache(maxsize=8)
def cached_energy_backtest(_cache_token: str) -> dict[str, object]:
    def build() -> dict[str, object]:
        source, market_days, stock_bars = load_market_data()
        result = BacktestEngine(
            [EnergyBreakoutStrategy(EnergyBreakoutConfig(min_failed_attempts=2))],
            risk_min_amount_billion=3,
            enforce_pattern_cycle=True,
            consecutive_loss_limit=None,
            fee_model=load_broker_fee_model(),
            capital=backtest_capital(),
        ).run(market_days, stock_bars)
        return {
            "source": source,
            **backtest_coverage_payload(market_days),
            "strategy": {
                "id": "energy",
                "name": "能量策略",
                "description": "近20日至少2次长上影试探60日线失败后，放量收盘站上60日线，次日开盘买入。",
            },
            "metrics": result.metrics,
            "trades": [trade.__dict__ for trade in result.trades],
            "quality": quality_breakdown(result.trades),
            "reflection": trade_reflection(result.trades),
            "rejected_count": len(result.rejected_signals),
        }

    return materialized_payload("energy-backtest", _cache_token, build)


@lru_cache(maxsize=8)
def cached_short_energy_backtest(_cache_token: str) -> dict[str, object]:
    def build() -> dict[str, object]:
        source, market_days, stock_bars = load_market_data()
        result = BacktestEngine(
            [ShortEnergyStrategy(ShortEnergyConfig())],
            risk_min_amount_billion=3,
            enforce_pattern_cycle=True,
            consecutive_loss_limit=None,
            fee_model=load_broker_fee_model(),
            capital=backtest_capital(),
            single_position_limit_pct=30,
        ).run(market_days, stock_bars)
        return {
            "source": source,
            **backtest_coverage_payload(market_days),
            "strategy": {
                "id": "short-energy",
                "name": "超短能量交易",
                "description": "按市场能量、个股能量、前排/龙头分和买入模式筛选主线前排、低位补涨与新题材点火机会。",
            },
            "metrics": result.metrics,
            "trades": [trade.__dict__ for trade in result.trades],
            "quality": quality_breakdown(result.trades),
            "reflection": trade_reflection(result.trades),
            "rejected_count": len(result.rejected_signals),
        }

    return materialized_payload("short-energy-backtest", _cache_token, build)


@app.get("/api/strategy-experiments")
def strategy_experiments() -> dict[str, object]:
    return cached_strategy_experiments(runtime_cache_token())


@lru_cache(maxsize=8)
def cached_strategy_experiments(_cache_token: str) -> dict[str, object]:
    def build() -> dict[str, object]:
        source, market_days, stock_bars = load_market_data()
        fee_model = load_broker_fee_model()
        capital = backtest_capital()
        experiments = []
        for preset in PRESETS:
            result = BacktestEngine(
                strategies_for_preset(preset),
                risk_min_amount_billion=preset.amount_min_billion,
                enforce_pattern_cycle=preset.cycle_filter,
                single_position_limit_pct=100 if preset.research_only else 20,
                total_position_limit_pct=100 if preset.research_only else None,
                consecutive_loss_limit=None,
                fee_model=fee_model,
                capital=capital,
            ).run(market_days, stock_bars)
            experiments.append(
                {
                    "id": preset.id,
                    "name": preset.name,
                    "description": preset.description,
                    "settings": preset_settings(preset),
                    "metrics": result.metrics,
                    "trade_count": result.metrics.get("trade_count", 0),
                    "sample_trades": [trade.__dict__ for trade in sorted(result.trades, key=lambda item: item.entry_date, reverse=True)[:5]],
                    "trades": [trade.__dict__ for trade in result.trades],
                    "quality": quality_breakdown(result.trades),
                    "reflection": trade_reflection(result.trades),
                    "rejected_count": len(result.rejected_signals),
                }
            )
        return {
            "source": source,
            **backtest_coverage_payload(market_days),
            "experiments": experiments,
        }

    return materialized_payload("strategy-experiments", _cache_token, build)


@app.get("/api/strategy-optimization")
def strategy_optimization() -> dict[str, object]:
    return cached_strategy_optimization(runtime_cache_token())


@lru_cache(maxsize=8)
def cached_strategy_optimization(_cache_token: str) -> dict[str, object]:
    source, market_days, stock_bars = load_market_data()
    fee_model = load_broker_fee_model()
    capital = backtest_capital()
    groups = []
    for base in PRESETS:
        rows = []
        for candidate in optimization_candidates(base):
            result = BacktestEngine(
                strategies_for_preset(candidate),
                risk_min_amount_billion=candidate.amount_min_billion,
                enforce_pattern_cycle=candidate.cycle_filter,
                single_position_limit_pct=100 if candidate.research_only else 20,
                total_position_limit_pct=100 if candidate.research_only else None,
                consecutive_loss_limit=None,
                fee_model=fee_model,
                capital=capital,
            ).run(market_days, stock_bars)
            rows.append(
                {
                    "id": candidate.id,
                    "name": candidate.name,
                    "description": candidate.description,
                    "settings": preset_settings(candidate),
                    "metrics": result.metrics,
                    "score": optimization_score(result.metrics),
                    "reflection": trade_reflection(result.trades),
                }
            )
        groups.append(
            {
                "base_id": base.id,
                "base_name": base.name,
                "candidates": sorted(rows, key=lambda item: float(item["score"]), reverse=True)[:5],
            }
        )
    return {
        "source": source,
        "range_days": len(market_days),
        "fee_model": fee_model.__dict__,
        "groups": groups,
    }


@app.get("/api/strategy-versions")
def strategy_versions() -> dict[str, object]:
    return cached_strategy_versions(runtime_cache_token())


@app.get("/api/cache/clear")
def clear_runtime_cache() -> dict[str, object]:
    clear_market_data_cache()
    cached_backtest.cache_clear()
    cached_energy_backtest.cache_clear()
    cached_short_energy_backtest.cache_clear()
    cached_tomorrow_plan.cache_clear()
    cached_strategy_experiments.cache_clear()
    cached_strategy_optimization.cache_clear()
    cached_strategy_versions.cache_clear()
    return {"cleared": True}


@lru_cache(maxsize=8)
def cached_strategy_versions(_cache_token: str) -> dict[str, object]:
    def build() -> dict[str, object]:
        source, market_days, stock_bars = load_market_data()
        payload = build_strategy_versions(
            PRESETS,
            market_days,
            stock_bars,
            load_broker_fee_model(),
            backtest_capital(),
            optimization_candidates,
            preset_settings,
        )
        payload["source"] = source
        payload["range_days"] = len(market_days)
        return payload

    return materialized_payload("strategy-versions", _cache_token, build)


def build_tomorrow_plan() -> dict[str, object]:
    return cached_tomorrow_plan(runtime_cache_token())


@lru_cache(maxsize=8)
def cached_tomorrow_plan(_cache_token: str) -> dict[str, object]:
    return materialized_payload("tomorrow-plan", _cache_token, _build_tomorrow_plan)


def _build_tomorrow_plan() -> dict[str, object]:
    source, market_days, stock_bars = load_market_data()
    if not market_days:
        raise HTTPException(status_code=502, detail="没有可用市场数据")

    cycle_states = build_cycle_states(market_days)
    decision_cycle = cycle_states[-1]
    decision_date = decision_cycle.trade_date
    bars = [bar for bar in stock_bars if bar.trade_date == decision_date]
    bars_by_symbol = {bar.symbol: bar for bar in bars}
    history_by_symbol: dict[str, list[StockBar]] = {}
    for bar in sorted(stock_bars, key=lambda item: (item.symbol, item.trade_date)):
        history_by_symbol.setdefault(bar.symbol, []).append(bar)

    try:
        planned_entry_date = next_open_date(decision_date)
    except TushareError:
        planned_entry_date = None

    version_payload, selected_versions = tomorrow_version_map(market_days, stock_bars)
    version_rows = {
        str(group.get("base_id")): group.get("recommended_version")
        for group in version_payload.get("groups", [])
        if isinstance(group, dict)
    }

    plans = []
    for base in PRESETS:
        version_row = version_rows.get(base.id)
        selected_preset = selected_versions.get(base.id)
        version_allowed = isinstance(version_row, dict) and bool(version_row.get("eligible")) and selected_preset is not None
        preset = selected_preset if version_allowed else base
        version_reasons = version_row.get("reasons") if isinstance(version_row, dict) else []
        if isinstance(version_row, dict) and bool(version_row.get("eligible")) and selected_preset is None:
            version_reasons = ["版本库候选参数与当前代码不匹配，需重新生成版本库"]
        picks = []
        rejected_count = 0
        selected_symbols: set[str] = set()
        if version_allowed:
            for strategy in strategies_for_preset(preset):
                for signal in strategy.generate_with_history(decision_cycle, bars, history_by_symbol):
                    bar = bars_by_symbol.get(signal.symbol)
                    if bar is None:
                        rejected_count += 1
                        continue
                    if signal.symbol in selected_symbols:
                        rejected_count += 1
                        continue
                    decision = evaluate_signal(
                        signal,
                        decision_cycle,
                        bar,
                        AccountState(),
                        min_amount_billion=preset.amount_min_billion,
                        enforce_pattern_cycle=preset.cycle_filter,
                        consecutive_loss_limit=None,
                        single_position_limit_pct=100 if preset.research_only else 20,
                        total_position_limit_pct=100 if preset.research_only else None,
                    )
                    if not decision.allowed:
                        rejected_count += 1
                        continue
                    selected_symbols.add(signal.symbol)
                    picks.append(tomorrow_signal_row(signal, bar, planned_entry_date, decision_cycle.tag))

        plans.append(
            {
                "id": base.id,
                "name": base.name,
                "description": preset.description,
                "settings": preset_settings(preset),
                "version_id": preset.id,
                "version_eligible": version_allowed,
                "version_verdict": version_row.get("verdict") if isinstance(version_row, dict) else "未生成版本库",
                "version_reasons": version_reasons,
                "signals": sorted(picks, key=lambda item: float(item["score"]), reverse=True),
                "rejected_count": rejected_count,
            }
        )

    short_energy_strategy = ShortEnergyStrategy(
        ShortEnergyConfig(
            market_threshold=45,
            stock_threshold=58,
            leader_threshold=45,
            min_avg_amount_billion=1,
            min_close_pct=3,
            max_sector_rank=220,
            max_signals=6,
            position_pct=5,
            ignition_position_pct=3,
            allow_watch_candidates=True,
        ),
        cycle_filter=False,
    )
    short_energy_picks = []
    short_energy_rejected = 0
    short_energy_symbols: set[str] = set()
    for signal in short_energy_strategy.generate_with_history(decision_cycle, bars, history_by_symbol):
        bar = bars_by_symbol.get(signal.symbol)
        if bar is None or signal.symbol in short_energy_symbols:
            short_energy_rejected += 1
            continue
        decision = evaluate_signal(
            signal,
            decision_cycle,
            bar,
            AccountState(),
            min_amount_billion=3,
            enforce_pattern_cycle=False,
            consecutive_loss_limit=None,
            single_position_limit_pct=30,
            total_position_limit_pct=100,
        )
        if not decision.allowed:
            short_energy_rejected += 1
            continue
        short_energy_symbols.add(signal.symbol)
        short_energy_picks.append(tomorrow_signal_row(signal, bar, planned_entry_date, decision_cycle.tag))

    plans.append(
        {
            "id": "short-energy",
            "name": "超短能量",
            "description": "根据市场能量、个股能量和前排/龙头分筛选明日可参考标的。",
            "settings": {
                "amount_min_billion": 3,
                "rank_limit": 120,
                "first_limit_mode": "market_energy",
                "one_to_two_open_min_pct": 0,
                "cycle_filter": True,
                "position_pct": None,
                "max_signals_per_strategy": 6,
                "research_only": True,
            },
            "version_id": "short-energy-live",
            "version_eligible": True,
            "version_verdict": "独立能量扫描",
            "version_reasons": ["按最新交易日收盘数据生成；退潮期只作为观察候选，开盘承接不符合时放弃"],
            "signals": sorted(short_energy_picks, key=lambda item: float(item["score"]), reverse=True),
            "rejected_count": short_energy_rejected,
        }
    )

    return {
        "source": source,
        "decision_date": decision_date,
        "planned_entry_date": planned_entry_date,
        "cycle_tag": decision_cycle.tag,
        "strategy_version_generated_at": version_payload.get("generated_at"),
        "plans": plans,
    }


@app.get("/api/tomorrow-plan")
def tomorrow_plan() -> dict[str, object]:
    return build_tomorrow_plan()


@app.get("/api/alerts/status")
def alert_status() -> dict[str, object]:
    return {"feishu": FeishuNotifier().status(), "qmt": QmtAdapter().status()}


@app.get("/api/alerts/test-feishu")
def test_feishu_alert() -> dict[str, object]:
    return FeishuNotifier().send_text("【CycleLab 测试】飞书交易提醒通道已连通。")


@app.get("/api/alerts/sync-tomorrow")
def sync_tomorrow_alerts() -> dict[str, object]:
    plan = build_tomorrow_plan()
    sync_result = sync_tomorrow_signals(plan)
    _, _, stock_bars = load_market_data()
    tracking_result = refresh_tracking(stock_bars)
    return {"plan": plan, "sync": sync_result, "tracking": tracking_result}


@app.get("/api/intraday/status")
def intraday_radar_status() -> dict[str, object]:
    return intraday_status()


@app.get("/api/intraday/scan")
def intraday_scan() -> dict[str, object]:
    status = intraday_status()
    if not status.get("ready"):
        return {
            "status": status,
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cycle_tag": None,
            "signal_count": 0,
            "signals": [],
        }
    _, market_days, stock_bars = load_market_data()
    cycle_states = build_cycle_states(market_days)
    status, quotes = load_intraday_quotes(stock_bars)
    scan = scan_intraday_quotes(quotes, str(cycle_states[-1].tag) if cycle_states else None)
    return {"status": status, **scan}


@app.get("/api/intraday/sync-alerts")
def intraday_sync_alerts() -> dict[str, object]:
    result = intraday_scan()
    if not result.get("status", {}).get("ready"):
        return {"scan": result, "sync": {"new_count": 0, "sent_count": 0, "errors": ["实时行情未接入"]}}
    return {"scan": result, "sync": sync_intraday_signals(result)}


@app.get("/api/signals/tracked")
def signals_tracked(refresh: bool = False) -> dict[str, object]:
    if refresh:
        _, _, stock_bars = load_market_data()
        refresh_tracking(stock_bars)
    return tracked_signals()


def start_signal_monitor() -> None:
    if os.getenv("SIGNAL_MONITOR_ENABLED", "0") != "1":
        return

    def loop() -> None:
        interval = max(60, int(os.getenv("SIGNAL_MONITOR_SECONDS", "900")))
        while True:
            try:
                if os.getenv("INTRADAY_MONITOR_ENABLED", "0") == "1":
                    scan = intraday_scan()
                    if scan.get("status", {}).get("ready"):
                        sync_intraday_signals(scan)
                plan = build_tomorrow_plan()
                sync_tomorrow_signals(plan)
                _, _, stock_bars = load_market_data()
                refresh_tracking(stock_bars)
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()


_INDUSTRY_RESEARCH_SCHEDULER_STARTED = False


def start_industry_research_scheduler() -> None:
    global _INDUSTRY_RESEARCH_SCHEDULER_STARTED
    if _INDUSTRY_RESEARCH_SCHEDULER_STARTED:
        return
    _INDUSTRY_RESEARCH_SCHEDULER_STARTED = True

    def loop() -> None:
        last_run_day: str | None = None
        while True:
            try:
                if should_run_daily_sync(last_run_day):
                    sync_industry_research(force=True)
                    last_run_day = time.strftime("%Y-%m-%d")
            except Exception:
                pass
            time.sleep(scheduler_sleep_seconds())

    threading.Thread(target=loop, daemon=True).start()
