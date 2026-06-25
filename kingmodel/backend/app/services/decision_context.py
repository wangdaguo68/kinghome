from __future__ import annotations

from typing import Any


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _match_score(topic: str, names: list[str]) -> float:
    if not topic:
        return 0.0
    return 1.0 if any(name and (name in topic or topic in name) for name in names) else 0.0


def _crowding_penalty(crowding: str) -> float:
    return {"高": 10.0, "中": 3.0, "低": 0.0}.get(crowding, 4.0)


def build_event_signals(
    sentiment: list[dict[str, Any]] | None,
    *,
    mainlines: list[dict[str, Any]] | None = None,
    sector_linkage: list[dict[str, Any]] | None = None,
    ml_review: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Turn overnight sentiment and post-market review into auditable signals.

    The signal is allowed to influence planning only as expectation/validation.
    It does not override market confirmation, and high crowding can reduce score.
    """

    mainline_names = [str(item.get("name", "")) for item in (mainlines or []) if item.get("name")]
    linkage_names = [str(item.get("name", "")) for item in (sector_linkage or []) if item.get("name")]
    linkage_by_name = {str(item.get("name", "")): item for item in (sector_linkage or []) if item.get("name")}
    signals: dict[str, dict[str, Any]] = {}

    for entry in sentiment or []:
        topic = str(entry.get("topic") or "").strip()
        if not topic:
            continue
        heat = _float(entry.get("heat"))
        crowding = str(entry.get("crowding") or "中")
        mainline_match = bool(_match_score(topic, mainline_names))
        linkage_match = next((item for name, item in linkage_by_name.items() if name in topic or topic in name), None)
        score = heat * 0.55
        score += 18 if mainline_match else 0
        score += min(18, _float(linkage_match.get("score")) * 0.18) if linkage_match else 0
        score -= _crowding_penalty(crowding)
        signals[topic] = {
            "topic": topic,
            "score": round(max(0.0, min(100.0, score)), 1),
            "type": "overnight_sentiment",
            "heat": round(heat, 1),
            "crowding": crowding,
            "catalyst": str(entry.get("catalyst") or "暂无明确催化"),
            "validation": str(entry.get("validation") or "次日盘面确认"),
            "mainline_match": mainline_match,
            "linkage_match": bool(linkage_match),
            "source": str(entry.get("source") or "本地舆情清单/人工录入"),
            "usable": True,
            "risk": "一致性较高，必须等待竞价和开盘承接确认" if crowding == "高" else "按盘面验证，不因热度直接买入",
        }

    for line in mainlines or []:
        name = str(line.get("name") or "").strip()
        if not name:
            continue
        linkage = next((item for lname, item in linkage_by_name.items() if lname in name or name in lname), None)
        score = _float(line.get("score")) * 0.45 + max(0.0, _float(line.get("change"))) * 3
        score += min(25, _float(linkage.get("score")) * 0.25) if linkage else 0
        current = signals.get(name)
        review_signal = {
            "topic": name,
            "score": round(max(0.0, min(100.0, score)), 1),
            "type": "post_market_review",
            "heat": None,
            "crowding": "盘后确认",
            "catalyst": str(line.get("flow") or "盘后结构确认"),
            "validation": "次日看容量承接、龙头溢价和后排是否继续扩散",
            "mainline_match": True,
            "linkage_match": bool(linkage),
            "source": str(line.get("source") or "收盘结构复盘"),
            "usable": True,
            "risk": "如果竞价不及预期或后排退潮，盘后强度作废",
        }
        if current is None or review_signal["score"] > current["score"]:
            signals[name] = review_signal

    summary = (ml_review or {}).get("summary") or []
    if summary:
        samples = sum(int(item.get("samples") or 0) for item in summary)
        wins = [
            _float(item.get("win_rate"))
            for item in summary
            if item.get("win_rate") is not None
        ]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        signals["模型复盘"] = {
            "topic": "模型复盘",
            "score": round(min(100.0, 35 + samples * 0.5 + avg_win * 35), 1),
            "type": "outcome_review",
            "heat": None,
            "crowding": "样本回填",
            "catalyst": f"已回填{samples}个收益样本",
            "validation": "只作为模型成熟度参考，不直接触发买入",
            "mainline_match": False,
            "linkage_match": False,
            "source": "本地机器学习收益回填",
            "usable": samples > 0,
            "risk": "样本不足时不能提高正式计划仓位",
        }

    return sorted(signals.values(), key=lambda item: (-float(item["score"]), item["topic"]))[:10]


def build_market_graph(payload: dict[str, Any]) -> dict[str, Any]:
    state = payload.get("state", {})
    breadth = payload.get("breadth", {})
    capacity = payload.get("capacity", {})
    nodes: list[dict[str, Any]] = [
        {
            "id": "market",
            "label": str(state.get("cycle") or "市场状态"),
            "type": "market",
            "score": round((_float(state.get("money")) + (100 - _float(state.get("loss")))) / 2, 1),
            "detail": f"{state.get('structure', '')}；上涨{breadth.get('up', 0)} / 下跌{breadth.get('down', 0)}",
        },
        {
            "id": "capacity",
            "label": str(capacity.get("label") or "容量反馈"),
            "type": "capacity",
            "score": round(50 + _float(capacity.get("median")) * 8, 1),
            "detail": f"成交额前{capacity.get('sample', 0)}，上涨{capacity.get('up', 0)}，中位{_float(capacity.get('median')):+.2f}%",
        },
    ]
    edges: list[dict[str, Any]] = [{"source": "market", "target": "capacity", "label": "风格约束", "tone": "neutral"}]

    for index, item in enumerate(payload.get("negative", [])[:4], start=1):
        node_id = f"neg-{index}"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("name") or "负反馈"),
                "type": "negative",
                "score": abs(_float(item.get("change"))) * 10,
                "detail": f"跌幅/中位{_float(item.get('change')):+.2f}%",
            }
        )
        edges.append({"source": node_id, "target": "market", "label": "拖累风险偏好", "tone": "negative"})

    for index, item in enumerate(payload.get("negative_stocks", [])[:6], start=1):
        code = str(item.get("code") or index)
        node_id = f"negstock-{code}"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("name") or code),
                "type": "negative_stock",
                "score": min(100, abs(_float(item.get("change"))) * 8 + _float(item.get("drawdown")) * 3),
                "detail": f"{code} {_float(item.get('change')):+.2f}% / 回撤{_float(item.get('drawdown')):.1f}%；{item.get('reason', '')}",
            }
        )
        target = next(
            (
                f"neg-{i}"
                for i, sector in enumerate(payload.get("negative", [])[:4], start=1)
                if str(sector.get("name", "")) in str(item.get("industry", ""))
                or str(item.get("industry", "")) in str(sector.get("name", ""))
            ),
            "market",
        )
        edges.append({"source": node_id, "target": target, "label": "个股亏钱效应", "tone": "negative"})

    for index, line in enumerate(payload.get("mainlines", [])[:4], start=1):
        node_id = f"line-{index}"
        nodes.append(
            {
                "id": node_id,
                "label": str(line.get("name") or "主线"),
                "type": "mainline" if index == 1 else "sector",
                "score": _float(line.get("score")),
                "detail": str(line.get("flow") or ""),
            }
        )
        edges.append({"source": "market", "target": node_id, "label": "正反馈", "tone": "positive"})

    for index, item in enumerate(payload.get("sector_linkage", [])[:6], start=1):
        node_id = f"link-{index}"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("name") or "联动"),
                "type": "linkage",
                "score": _float(item.get("score")),
                "detail": f"{item.get('level', '')}：涨停{item.get('limit_up_count', 0)}，后排{item.get('follower_count', 0)}，20cm {item.get('elastic_count', 0)}",
            }
        )
        target = next((f"line-{i}" for i, line in enumerate(payload.get("mainlines", [])[:4], start=1) if str(line.get("name", "")) in str(item.get("name", "")) or str(item.get("name", "")) in str(line.get("name", ""))), "market")
        edges.append({"source": target, "target": node_id, "label": "板块扩散", "tone": "positive"})
        leader_code = str(item.get("leader_code") or "")
        if leader_code:
            leader_id = f"leader-{leader_code}"
            nodes.append(
                {
                    "id": leader_id,
                    "label": str(item.get("leader") or leader_code),
                    "type": "leader",
                    "score": _float(item.get("score")),
                    "detail": f"{leader_code} 带动{item.get('follower_count', 0)}只后排",
                }
            )
            edges.append({"source": node_id, "target": leader_id, "label": "核心带动", "tone": "positive"})

    for index, item in enumerate(payload.get("capacity_cores", [])[:5], start=1):
        node_id = f"capcore-{item.get('code')}"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("name") or item.get("code")),
                "type": "capacity_core",
                "score": _float(item.get("score")),
                "detail": f"{item.get('industry', '')} 成交额{item.get('amount_label', '')}，涨跌{_float(item.get('change')):+.2f}%",
            }
        )
        edges.append({"source": "capacity", "target": node_id, "label": "容量核心", "tone": "positive" if _float(item.get("change")) >= 0 else "neutral"})

    for index, item in enumerate(payload.get("planned_targets", [])[:3], start=1):
        node_id = f"plan-{item.get('code')}"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("name") or item.get("code")),
                "type": "plan",
                "score": _float(item.get("score")),
                "detail": f"{item.get('priority', 'B')}级计划：{item.get('setup', '')}",
            }
        )
        source = f"leader-{item.get('code')}" if any(str(n.get("id")) == f"leader-{item.get('code')}" for n in nodes) else "market"
        edges.append({"source": source, "target": node_id, "label": "交易计划", "tone": "plan"})

    seen: set[str] = set()
    unique_nodes = []
    for node in nodes:
        if node["id"] in seen:
            continue
        seen.add(node["id"])
        unique_nodes.append(node)
    return {"nodes": unique_nodes, "edges": edges[:32]}
