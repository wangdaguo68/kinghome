from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.backtest.engine import BacktestEngine
from app.backtest.fees import BrokerFeeModel
from app.data.schemas import MarketDay, StockBar
from app.strategies.experiment import StrategyPreset, strategies_for_preset


ROOT = Path(__file__).resolve().parents[3]
VERSION_CACHE = ROOT / "cache" / "strategy_versions.json"
CACHE_SCHEMA_VERSION = 1
_CACHE_LOCK = threading.RLock()


def build_strategy_versions(
    presets: tuple[StrategyPreset, ...],
    market_days: list[MarketDay],
    stock_bars: list[StockBar],
    fee_model: BrokerFeeModel,
    capital: float,
    candidate_fn: Callable[[StrategyPreset], list[StrategyPreset]],
    settings_fn: Callable[[StrategyPreset], dict[str, object]],
) -> dict[str, object]:
    cache_context = strategy_version_context(presets, fee_model, capital, candidate_fn, settings_fn)
    train_days, validation_days, recent_days = split_market_days(market_days)
    groups = []
    for base in presets:
        rows = []
        for candidate in candidate_fn(base):
            train_metrics = _run(candidate, train_days, stock_bars, fee_model, capital)
            validation_metrics = _run(candidate, validation_days, stock_bars, fee_model, capital)
            recent_metrics = _run(candidate, recent_days, stock_bars, fee_model, capital)
            decision = version_decision(train_metrics, validation_metrics, recent_metrics)
            rows.append(
                {
                    "version_id": candidate.id,
                    "name": candidate.name,
                    "description": candidate.description,
                    "settings": settings_fn(candidate),
                    "train": train_metrics,
                    "validation": validation_metrics,
                    "recent": recent_metrics,
                    "score": decision["score"],
                    "eligible": decision["eligible"],
                    "verdict": decision["verdict"],
                    "reasons": decision["reasons"],
                }
            )
        ordered = sorted(rows, key=lambda item: (bool(item["eligible"]), float(item["score"])), reverse=True)
        groups.append(
            {
                "base_id": base.id,
                "base_name": base.name,
                "recommended_version": ordered[0] if ordered else None,
                "versions": ordered,
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cache_key": strategy_version_fingerprint(cache_context),
        "cache_context": cache_context,
        "segments": {
            "train": _segment_meta(train_days),
            "validation": _segment_meta(validation_days),
            "recent": _segment_meta(recent_days),
        },
        "fee_model": asdict(fee_model),
        "groups": groups,
    }
    write_strategy_version_cache(payload)
    return payload


def strategy_version_context(
    presets: tuple[StrategyPreset, ...],
    fee_model: BrokerFeeModel,
    capital: float,
    candidate_fn: Callable[[StrategyPreset], list[StrategyPreset]],
    settings_fn: Callable[[StrategyPreset], dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "capital": capital,
        "fee_model": asdict(fee_model),
        "candidates": [
            {
                "base_id": base.id,
                "preset": asdict(candidate),
                "settings": settings_fn(candidate),
            }
            for base in presets
            for candidate in candidate_fn(base)
        ],
    }


def strategy_version_fingerprint(context: dict[str, object]) -> str:
    import hashlib

    raw = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_strategy_version_cache() -> dict[str, object] | None:
    with _CACHE_LOCK:
        try:
            return json.loads(VERSION_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None


def write_strategy_version_cache(payload: dict[str, object]) -> None:
    VERSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
    temp_path = VERSION_CACHE.with_name(f"{VERSION_CACHE.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with _CACHE_LOCK:
        temp_path.write_text(data, encoding="utf-8")
        temp_path.replace(VERSION_CACHE)


def split_market_days(market_days: list[MarketDay]) -> tuple[list[MarketDay], list[MarketDay], list[MarketDay]]:
    if len(market_days) < 80:
        recent_len = min(23, len(market_days))
        recent_days = market_days[-recent_len:] if recent_len else []
        remaining = market_days[:-recent_len] if recent_len else market_days
        if len(remaining) < 20:
            return remaining, [], recent_days
        train_len = max(1, int(len(remaining) * 0.7))
        return remaining[:train_len], remaining[train_len:], recent_days
    recent_len = min(23, max(10, len(market_days) // 10))
    remaining = len(market_days) - recent_len
    train_len = max(40, int(remaining * 0.7))
    return market_days[:train_len], market_days[train_len:remaining], market_days[remaining:]


def version_decision(
    train: dict[str, float],
    validation: dict[str, float],
    recent: dict[str, float],
) -> dict[str, object]:
    reasons: list[str] = []
    if train["trade_count"] < 30:
        reasons.append("训练段交易数不足 30 笔")
    if validation["trade_count"] < 10:
        reasons.append("验证段交易数不足 10 笔")
    if train["total_return_pct"] <= 0:
        reasons.append("训练段净收益未转正")
    if validation["total_return_pct"] <= 0:
        reasons.append("验证段净收益未转正")
    if validation["max_drawdown_pct"] <= -8:
        reasons.append("验证段最大回撤超过 8%")
    if recent["total_return_pct"] < 0 and recent["max_drawdown_pct"] <= -3:
        reasons.append("最近观察段收益和回撤同时走弱")

    score = round(
        validation["total_return_pct"]
        + validation["max_drawdown_pct"] * 1.5
        + recent["total_return_pct"] * 0.35
        + min(validation["trade_count"], 100) * 0.03,
        2,
    )
    eligible = not reasons
    return {
        "eligible": eligible,
        "score": score if validation["trade_count"] >= 10 else -999,
        "verdict": "可进入明日策略候选" if eligible else "继续观察",
        "reasons": reasons or ["训练段、验证段和最近观察段均通过基础门槛"],
    }


def _run(
    preset: StrategyPreset,
    market_days: list[MarketDay],
    stock_bars: list[StockBar],
    fee_model: BrokerFeeModel,
    capital: float,
) -> dict[str, float]:
    day_set = {day.trade_date for day in market_days}
    bars = [bar for bar in stock_bars if bar.trade_date in day_set]
    result = BacktestEngine(
        strategies_for_preset(preset),
        risk_min_amount_billion=preset.amount_min_billion,
        enforce_pattern_cycle=preset.cycle_filter,
        single_position_limit_pct=100 if preset.research_only else 20,
        total_position_limit_pct=100 if preset.research_only else None,
        consecutive_loss_limit=None,
        fee_model=fee_model,
        capital=capital,
    ).run(market_days, bars)
    return result.metrics


def _segment_meta(days: list[MarketDay]) -> dict[str, object]:
    if not days:
        return {"start": None, "end": None, "days": 0}
    return {"start": days[0].trade_date, "end": days[-1].trade_date, "days": len(days)}
