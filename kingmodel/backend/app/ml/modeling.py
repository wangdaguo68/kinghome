from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


FEATURE_NAMES = (
    "core_score", "change", "money", "loss", "trend", "speculation",
    "ladder_height", "recent_limit_count",
)


def numeric_features(payload: dict[str, Any]) -> dict[str, float]:
    market = payload.get("market_context") or {}
    ladder = payload.get("ladder") or {}
    return {
        "core_score": float(payload.get("score") or 0),
        "change": float(payload.get("change") or 0),
        "money": float(market.get("money") or 0),
        "loss": float(market.get("loss") or 0),
        "trend": float(market.get("trend") or 0),
        "speculation": float(market.get("speculation") or 0),
        "ladder_height": float(ladder.get("height") or 0),
        "recent_limit_count": float(ladder.get("recent_limit_count") or 0),
    }


@dataclass
class LogisticModel:
    feature_names: tuple[str, ...]
    means: list[float]
    scales: list[float]
    weights: list[float]
    bias: float

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1 / (1 + math.exp(-max(-30.0, min(30.0, value))))

    @classmethod
    def fit(
        cls,
        rows: list[dict[str, float]],
        labels: list[int],
        iterations: int = 500,
        feature_names: tuple[str, ...] | None = None,
    ) -> "LogisticModel":
        if len(rows) != len(labels) or len(rows) < 20 or len(set(labels)) < 2:
            raise ValueError("训练至少需要20条且同时包含正负样本")
        names = feature_names or tuple(FEATURE_NAMES)
        columns = [[float(row.get(name, 0)) for row in rows] for name in names]
        means = [sum(values) / len(values) for values in columns]
        scales = [max(1e-6, math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))) for values, mean in zip(columns, means)]
        matrix = [[(float(row.get(name, 0)) - means[index]) / scales[index] for index, name in enumerate(names)] for row in rows]
        weights = [0.0] * len(names)
        bias = 0.0
        rate = 0.08
        regularization = 0.002
        for _ in range(iterations):
            gradient = [0.0] * len(names)
            bias_gradient = 0.0
            for vector, label in zip(matrix, labels):
                probability = cls._sigmoid(bias + sum(weight * value for weight, value in zip(weights, vector)))
                error = probability - label
                bias_gradient += error
                for index, value in enumerate(vector):
                    gradient[index] += error * value
            count = len(matrix)
            bias -= rate * bias_gradient / count
            weights = [weight - rate * (gradient[index] / count + regularization * weight) for index, weight in enumerate(weights)]
        return cls(names, means, scales, weights, bias)

    def predict(self, row: dict[str, float]) -> float:
        vector = [(float(row.get(name, 0)) - self.means[index]) / self.scales[index] for index, name in enumerate(self.feature_names)]
        return self._sigmoid(self.bias + sum(weight * value for weight, value in zip(self.weights, vector)))

    def explain(self, row: dict[str, float], limit: int = 3) -> list[dict[str, float | str]]:
        contributions = []
        for index, name in enumerate(self.feature_names):
            standardized = (float(row.get(name, 0)) - self.means[index]) / self.scales[index]
            contributions.append({"feature": name, "contribution": round(self.weights[index] * standardized, 4)})
        return sorted(contributions, key=lambda item: abs(float(item["contribution"])), reverse=True)[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {"algorithm": "standardized_logistic_v1", "feature_names": list(self.feature_names), "means": self.means, "scales": self.scales, "weights": self.weights, "bias": self.bias}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LogisticModel":
        return cls(tuple(payload["feature_names"]), list(payload["means"]), list(payload["scales"]), list(payload["weights"]), float(payload["bias"]))


def purged_walk_forward_dates(dates: list[str], purge_days: int = 10) -> tuple[set[str], set[str]]:
    unique = sorted(set(dates))
    if len(unique) < 30:
        raise ValueError("走步验证至少需要30个结果交易日")
    split = max(20, int(len(unique) * 0.7))
    test_start = min(len(unique), split + purge_days)
    if test_start >= len(unique):
        raise ValueError("隔离区后没有测试窗口")
    return set(unique[:split]), set(unique[test_start:])


def evaluation_metrics(probabilities: list[float], outcomes: list[dict[str, Any]]) -> dict[str, float]:
    if not probabilities or len(probabilities) != len(outcomes):
        raise ValueError("评估结果为空或长度不一致")
    returns = [float(item.get("net_return") or 0) for item in outcomes]
    labels = [1 if value > 0 else 0 for value in returns]
    wins = [value for value in returns if value > 0]
    losses = [-value for value in returns if value < 0]
    win_rate = sum(labels) / len(labels)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    equity = peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1 + value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1)
    return {
        "samples": float(len(labels)), "win_rate": round(win_rate, 6),
        "avg_win": round(avg_win, 6), "avg_loss": round(avg_loss, 6),
        "payoff_ratio": round(avg_win / avg_loss, 4) if avg_loss else 0.0,
        "expectancy": round(sum(returns) / len(returns), 6),
        "brier": round(sum((probability - label) ** 2 for probability, label in zip(probabilities, labels)) / len(labels), 6),
        "max_drawdown": round(max_drawdown, 6),
    }


def classification_metrics(probabilities: list[float], labels: list[int]) -> dict[str, float]:
    if not probabilities or len(probabilities) != len(labels):
        raise ValueError("分类评估结果为空或长度不一致")
    return {
        "samples": float(len(labels)),
        "positive_rate": round(sum(labels) / len(labels), 6),
        "accuracy": round(sum((probability >= 0.5) == bool(label) for probability, label in zip(probabilities, labels)) / len(labels), 6),
        "brier": round(sum((probability - label) ** 2 for probability, label in zip(probabilities, labels)) / len(labels), 6),
    }


def market_features(payload: dict[str, Any]) -> dict[str, float]:
    inputs = payload.get("inputs") or {}
    return {
        "money": float(payload.get("money") or 0), "loss": float(payload.get("loss") or 0),
        "trend": float(payload.get("trend") or 0), "speculation": float(payload.get("speculation") or 0),
        "up_ratio": float(inputs.get("up_ratio") or 0), "median": float(inputs.get("median") or 0),
        "limit_up": float(inputs.get("limit_up") or 0), "limit_down": float(inputs.get("limit_down") or 0),
        "ladder_count": float(inputs.get("ladder_count") or 0), "max_height": float(inputs.get("max_height") or 0),
    }


def sector_features(payload: dict[str, Any]) -> dict[str, float]:
    return {
        "score": float(payload.get("score") or 0), "change": float(payload.get("change") or 0),
        "tag_count": float(len(payload.get("tags") or [])),
        "is_primary": 1.0 if str(payload.get("role", "")).startswith("主") else 0.0,
    }
