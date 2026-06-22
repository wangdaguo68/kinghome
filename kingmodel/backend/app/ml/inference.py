from __future__ import annotations

import math
from typing import Any

from ..db import champion_model, model_system_status
from .modeling import LogisticModel, market_features, numeric_features, sector_features


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    peak = max(scores.values())
    values = {key: math.exp((value - peak) / 12) for key, value in scores.items()}
    total = sum(values.values())
    return {key: round(value / total, 4) for key, value in values.items()}


def regime_probabilities(assessment: dict[str, Any]) -> dict[str, Any]:
    money = float(assessment["money"])
    loss = float(assessment["loss"])
    trend = float(assessment["trend"])
    speculation = float(assessment["speculation"])
    style = _softmax({
        "trend": trend, "speculation": speculation,
        "mixed": min(trend, speculation) + 8, "no_edge": 100 - max(trend, speculation),
    })
    cycle = _softmax({
        "主升": money - loss * 0.4, "高位震荡": min(money, loss),
        "混沌轮动": 65 - abs(money - loss), "退潮防守": loss - money * 0.4,
        "试错修复": 55 - abs(money - 45) - loss * 0.25,
    })
    versions: set[str] = set()
    market_values = market_features(assessment)
    for key, task in (("trend", "market_trend"), ("speculation", "market_speculation")):
        registered = champion_model(task, "market")
        if registered:
            style[key] = round(LogisticModel.from_dict(registered["artifact"]).predict(market_values), 4)
            versions.add(str(registered["version"]))
    if versions:
        total = sum(style.values()) or 1
        style = {key: round(value / total, 4) for key, value in style.items()}
    learned_cycles: dict[str, float] = {}
    for name in cycle:
        registered = champion_model(f"cycle_{name}", "market")
        if registered:
            learned_cycles[name] = LogisticModel.from_dict(registered["artifact"]).predict(market_values)
            versions.add(str(registered["version"]))
    if len(learned_cycles) == len(cycle):
        total = sum(learned_cycles.values()) or 1
        cycle = {key: round(value / total, 4) for key, value in learned_cycles.items()}
    return {
        "source": "champion" if versions else "rule_probability_baseline", "model_versions": sorted(versions),
        "style": style, "cycle": cycle,
        "primary_style": max(style, key=style.get), "primary_cycle": max(cycle, key=cycle.get),
    }


def sector_probability(sector: dict[str, Any]) -> dict[str, Any]:
    registered = champion_model("sector_continuation", "all")
    if not registered:
        return {"available": False, "source": "rule_only", "probability": None, "model_version": None}
    model = LogisticModel.from_dict(registered["artifact"])
    values = sector_features(sector)
    return {
        "available": True, "source": "champion", "probability": round(model.predict(values), 4),
        "model_version": registered["version"], "explanation": model.explain(values),
    }


def stock_probability(core: dict[str, Any], assessment: dict[str, Any], ladder: dict[str, Any] | None = None) -> dict[str, Any]:
    segment = str(core.get("kind", ""))
    registered = champion_model("stock_up_probability", segment)
    if not registered:
        return {"available": False, "source": "rule_only", "probability": None, "model_version": None, "explanation": []}
    payload = {**core, "market_context": assessment, "ladder": ladder}
    model = LogisticModel.from_dict(registered["artifact"])
    features = numeric_features(payload)
    return {
        "available": True, "source": "champion", "probability": round(model.predict(features), 4),
        "model_version": registered["version"], "explanation": model.explain(features),
    }


def inference_status() -> dict[str, Any]:
    status = model_system_status()
    champions = sum(model["role"] == "champion" and model["status"] == "active" for model in status["models"])
    return {
        "stage": status["stage"], "feature_days": status["feature_days"], "outcome_days": status["outcome_days"],
        "champion_count": champions,
        "challenger_count": sum(model["role"] == "challenger" for model in status["models"]),
        "next_gate": 20 if status["outcome_days"] < 20 else 60 if status["outcome_days"] < 60 else 120 if status["outcome_days"] < 120 else None,
        "last_training_run": status["last_training_run"],
        "modules": {
            "feature_store": "active", "outcome_tracker": "active", "model_registry": "active",
            "market_regime": "champion" if any(model["task"] == "market_regime" and model["role"] == "champion" for model in status["models"]) else "waiting_data",
            "sector_ranker": "champion" if any(model["task"] == "sector_continuation" and model["role"] == "champion" for model in status["models"]) else "waiting_data",
            "stock_ranker": "champion" if champions else "waiting_data",
        },
    }
