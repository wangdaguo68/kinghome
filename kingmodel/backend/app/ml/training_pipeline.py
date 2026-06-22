from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import (
    champion_model, finish_training_run, load_feature_scope, load_training_rows, model_system_status, promote_model,
    register_model, start_training_run,
)
from ..engine.rule_selector import passes_expectancy_gate
from .modeling import (
    LogisticModel, classification_metrics, evaluation_metrics, market_features, numeric_features,
    purged_walk_forward_dates, sector_features,
)


SEGMENTS = ("连板情绪核心", "趋势容量核心", "创业板20cm弹性核心")
CYCLES = ("主升", "高位震荡", "混沌轮动", "退潮防守", "试错修复")


def promotion_eligible(metrics: dict[str, float], champion: dict[str, Any] | None, outcome_days: int) -> bool:
    if outcome_days < 120 or metrics["samples"] < 20:
        return False
    if not passes_expectancy_gate(metrics["win_rate"], metrics["avg_win"], metrics["avg_loss"]):
        return False
    if metrics["brier"] > 0.25 or metrics["max_drawdown"] < -0.20:
        return False
    if not champion:
        return True
    baseline = champion["metrics"]
    return (
        metrics["expectancy"] >= float(baseline.get("expectancy", 0))
        and metrics["brier"] <= float(baseline.get("brier", 1))
        and metrics["max_drawdown"] >= float(baseline.get("max_drawdown", -1))
    )


def classification_promotion_eligible(metrics: dict[str, float], champion: dict[str, Any] | None, feature_days: int) -> bool:
    if feature_days < 120 or metrics["samples"] < 20 or metrics["brier"] > 0.24 or metrics["accuracy"] < 0.55:
        return False
    if not champion:
        return True
    baseline = champion["metrics"]
    return metrics["brier"] <= float(baseline.get("brier", 1)) and metrics["accuracy"] >= float(baseline.get("accuracy", 0))


def _next_day_samples(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(row["trade_date"], []).append(row)
    dates = sorted(by_date)
    samples = []
    for index, trade_date in enumerate(dates[:-1]):
        for row in by_date[trade_date]:
            samples.append((trade_date, row, {item["entity_id"]: item for item in by_date[dates[index + 1]]}))
    return samples


class TrainingPipeline:
    def train(self, version: str | None = None) -> dict[str, Any]:
        now = datetime.now().astimezone()
        version = version or now.strftime("ml-%Y%m%d-%H%M")
        if not start_training_run(version, now.isoformat(timespec="seconds")):
            return {"status": "skipped", "reason": "version_exists", "version": version}
        report: dict[str, Any] = {"version": version, "models": []}
        total = 0
        try:
            all_rows = load_training_rows(1)
            system = model_system_status()
            outcome_days = int(system["outcome_days"])
            feature_days = int(system["feature_days"])
            if feature_days < 20:
                report["reason"] = "至少需要20个特征交易日"
                finish_training_run(version, "insufficient_data", now.isoformat(timespec="seconds"), len(all_rows), report)
                return {"status": "insufficient_data", **report}

            market_rows = load_feature_scope("market")
            market_samples = _next_day_samples(market_rows)
            market_tasks = {
                "market_trend": lambda future: float(future.get("trend") or 0) >= 60,
                "market_speculation": lambda future: float(future.get("speculation") or 0) >= 60,
                **{f"cycle_{cycle}": (lambda future, expected=cycle: str(future.get("cycle")) == expected) for cycle in CYCLES},
            }
            for task, labeler in market_tasks.items():
                samples = [(date, row["payload"], next_rows.get("ALL", {}).get("payload", {})) for date, row, next_rows in market_samples if "ALL" in next_rows]
                labels = [int(labeler(future)) for _, _, future in samples]
                if len(samples) < 30 or len(set(labels)) < 2:
                    report["models"].append({"task": task, "segment": "market", "status": "insufficient_samples", "samples": len(samples)})
                    continue
                train_dates, test_dates = purged_walk_forward_dates([date for date, _, _ in samples])
                train = [(payload, label) for date, payload, _future in samples for label in [int(labeler(_future))] if date in train_dates]
                test = [(payload, label) for date, payload, _future in samples for label in [int(labeler(_future))] if date in test_dates]
                if len(train) < 20 or len(test) < 5 or len({label for _, label in train}) < 2:
                    report["models"].append({"task": task, "segment": "market", "status": "insufficient_walk_forward_classes"})
                    continue
                feature_names = tuple(market_features(train[0][0]).keys())
                model = LogisticModel.fit([market_features(payload) for payload, _ in train], [label for _, label in train], feature_names=feature_names)
                probabilities = [model.predict(market_features(payload)) for payload, _ in test]
                metrics = classification_metrics(probabilities, [label for _, label in test])
                current = champion_model(task, "market")
                eligible = classification_promotion_eligible(metrics, current, feature_days)
                record = {"task": task, "segment": "market", "version": version, "role": "challenger", "status": "validated" if eligible else "shadow", "feature_version": "rule-v1", "sample_count": len(samples), "artifact": model.to_dict(), "metrics": metrics, "trained_at": now.isoformat(timespec="seconds")}
                register_model(record)
                if eligible:
                    promote_model(task, "market", version)
                report["models"].append({"task": task, "segment": "market", "status": "promoted" if eligible else "shadow", "metrics": metrics})
                total += len(samples)

            sector_rows = load_feature_scope("sector")
            sector_samples = _next_day_samples(sector_rows)
            samples = []
            for date, row, next_rows in sector_samples:
                future = next_rows.get(row["entity_id"])
                label = int(bool(future and float(future["payload"].get("score") or 0) >= 60))
                samples.append((date, row["payload"], label))
            if len(samples) >= 30 and len({label for _, _, label in samples}) == 2:
                train_dates, test_dates = purged_walk_forward_dates([date for date, _, _ in samples])
                train = [(payload, label) for date, payload, label in samples if date in train_dates]
                test = [(payload, label) for date, payload, label in samples if date in test_dates]
                if len(train) < 20 or len(test) < 5 or len({label for _, label in train}) < 2:
                    report["models"].append({"task": "sector_continuation", "segment": "all", "status": "insufficient_walk_forward_classes"})
                else:
                    feature_names = tuple(sector_features(train[0][0]).keys())
                    model = LogisticModel.fit([sector_features(payload) for payload, _ in train], [label for _, label in train], feature_names=feature_names)
                    probabilities = [model.predict(sector_features(payload)) for payload, _ in test]
                    metrics = classification_metrics(probabilities, [label for _, label in test])
                    task = "sector_continuation"
                    current = champion_model(task, "all")
                    eligible = classification_promotion_eligible(metrics, current, feature_days)
                    record = {"task": task, "segment": "all", "version": version, "role": "challenger", "status": "validated" if eligible else "shadow", "feature_version": "rule-v1", "sample_count": len(samples), "artifact": model.to_dict(), "metrics": metrics, "trained_at": now.isoformat(timespec="seconds")}
                    register_model(record)
                    if eligible:
                        promote_model(task, "all", version)
                    report["models"].append({"task": task, "segment": "all", "status": "promoted" if eligible else "shadow", "metrics": metrics})
                    total += len(samples)
            else:
                report["models"].append({"task": "sector_continuation", "segment": "all", "status": "insufficient_samples", "samples": len(samples)})

            if outcome_days < 20:
                report["models"].append({"task": "stock_up_probability", "status": "waiting_for_outcomes", "outcome_days": outcome_days})
                finish_training_run(version, "completed", datetime.now().astimezone().isoformat(timespec="seconds"), total, report)
                return {"status": "completed", **report}
            for segment in SEGMENTS:
                rows = [row for row in all_rows if str(row["features"].get("kind")) == segment and row["outcome"].get("tradable")]
                if len(rows) < 30:
                    report["models"].append({"segment": segment, "status": "insufficient_samples", "samples": len(rows)})
                    continue
                train_dates, test_dates = purged_walk_forward_dates([row["trade_date"] for row in rows])
                train_rows = [row for row in rows if row["trade_date"] in train_dates]
                test_rows = [row for row in rows if row["trade_date"] in test_dates]
                train_labels = [1 if float(row["outcome"].get("net_return") or 0) > 0 else 0 for row in train_rows]
                if len(train_rows) < 20 or len(test_rows) < 5 or len(set(train_labels)) < 2:
                    report["models"].append({"segment": segment, "status": "insufficient_walk_forward_window"})
                    continue
                model = LogisticModel.fit(
                    [numeric_features(row["features"]) for row in train_rows],
                    train_labels,
                )
                probabilities = [model.predict(numeric_features(row["features"])) for row in test_rows]
                metrics = evaluation_metrics(probabilities, [row["outcome"] for row in test_rows])
                current = champion_model("stock_up_probability", segment)
                eligible = promotion_eligible(metrics, current, outcome_days)
                record = {
                    "task": "stock_up_probability", "segment": segment, "version": version,
                    "role": "challenger", "status": "validated" if eligible else "shadow",
                    "feature_version": "rule-v1", "sample_count": len(rows), "artifact": model.to_dict(),
                    "metrics": metrics, "trained_at": now.isoformat(timespec="seconds"),
                }
                register_model(record)
                if eligible:
                    promote_model(record["task"], segment, version)
                report["models"].append({"segment": segment, "status": "promoted" if eligible else "shadow", "metrics": metrics})
                total += len(rows)
            finish_training_run(version, "completed", datetime.now().astimezone().isoformat(timespec="seconds"), total, report)
            return {"status": "completed", **report}
        except Exception as exc:
            finish_training_run(version, "failed", datetime.now().astimezone().isoformat(timespec="seconds"), total, report, str(exc)[:300])
            raise
