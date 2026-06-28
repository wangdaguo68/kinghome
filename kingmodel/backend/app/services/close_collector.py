from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from ..config import get_settings
from ..db import (
    collection_status,
    complete_tdx_call,
    finish_collection_job,
    feature_store_status,
    get_cause_cache,
    latest_reliable_snapshot_before,
    latest_snapshot,
    latest_trusted_snapshot,
    load_stock_meta,
    load_daily_pools,
    reserve_tdx_call,
    save_cause_cache,
    save_feature_snapshots,
    save_shadow_plans,
    save_snapshot,
    upsert_stock_meta,
    start_collection_job,
    upsert_daily_pool,
    outcome_review,
)
from ..engine.framework import assess_market, build_feature_snapshots, build_market_permission
from ..engine.rule_selector import FEATURE_VERSION, PLAN_VERSION, build_shadow_top3
from ..ml.inference import inference_status, regime_probabilities, sector_probability, stock_probability
from ..ml.outcome_tracker import OutcomeTracker
from ..ml.training_pipeline import TrainingPipeline
from .capacity_core import build_capacity_cores, capacity_cores_as_candidates
from .collector import Collector, DEMO_DASHBOARD, _capacity_label
from .decision_context import build_event_signals, build_market_graph
from .free_market import EastMoneyFreeClient, FreeMarketError
from .market_validation import field_value, is_trade_candidate, result_rows
from .planning import build_planned_targets
from .sector_linkage import build_sector_linkage
from .tushare_fallback import TushareFallback


SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")

MANUAL_BREADTH_OVERRIDES: dict[str, dict[str, Any]] = {
    # 2026-06-23: user-verified market breadth after excluding Beijing Stock Exchange
    # from EastMoney limit-up pool. Keep this explicit and auditable instead of
    # publishing zeros or carrying a stale previous-day breadth snapshot when the
    # EastMoney full-market list endpoint disconnects.
    "20260623": {
        "eligible": 5196,
        "up": 2549,
        "down": 2544,
        "flat": 103,
        "limit_up": 94,
        "limit_down": 39,
        "failed_limit": 50,
    },
}


class CloseCollector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.free = EastMoneyFreeClient()
        self.tdx = Collector()
        self.tushare = TushareFallback(self.settings.tushare_token, self.settings.tushare_api_url)
        self.outcomes = OutcomeTracker(self.free, self.tushare)
        self.training = TrainingPipeline()
        self._lock = asyncio.Lock()

    FREE_META_LIMIT = 24
    TDX_META_LIMIT = 5

    @staticmethod
    def _compact_date(value: str) -> str:
        return value.replace(".", "").replace("-", "")

    def current(self) -> dict[str, Any]:
        latest = latest_snapshot()
        trusted = latest_trusted_snapshot()
        today = datetime.now(SHANGHAI).strftime("%Y%m%d")
        latest_date = self._compact_date(str((latest or {}).get("meta", {}).get("trade_date", "")))
        payload = deepcopy(latest if latest and latest_date == today else trusted or latest or DEMO_DASHBOARD)
        trade_date = self._compact_date(str(payload.get("meta", {}).get("trade_date", "")))
        payload.setdefault("meta", {})
        if payload["meta"].get("version_label") != "今日部分收盘版":
            payload["meta"]["version_label"] = "今日收盘版" if trade_date == today else "上一可信收盘版"
        payload["collection_status"] = collection_status(today, self.settings.tdx_daily_call_limit)
        if "ml_shadow" not in payload:
            assessment = assess_market(payload)
            payload["permission"] = build_market_permission(assessment)
            payload["ml_shadow"] = build_shadow_top3(payload, assessment)
        else:
            payload["permission"] = build_market_permission(assess_market(payload))
        payload["feature_store_status"] = feature_store_status()
        payload["ml_system"] = inference_status()
        payload["ml_review"] = outcome_review()
        payload.setdefault("capacity_cores", [])
        payload.setdefault("negative_stocks", [])
        payload["negative_stocks"] = self._sanitize_negative_stock_items(payload.get("negative_stocks", []))
        payload["sentiment"] = self._validated_sentiment(payload)
        self._apply_linkage_to_mainlines(payload)
        payload["event_signals"] = build_event_signals(
            payload.get("sentiment", []),
            mainlines=payload.get("mainlines", []),
            sector_linkage=payload.get("sector_linkage", []),
            ml_review=payload.get("ml_review", {}),
        )
        payload["checkpoints"] = self._build_checkpoints(payload)
        payload["market_graph"] = build_market_graph(payload)
        return payload

    def bootstrap_shadow(self) -> None:
        """Backfill the latest trusted snapshot locally; this never calls a market-data service."""
        payload = deepcopy(latest_trusted_snapshot() or latest_snapshot())
        if not payload:
            return
        trade_date = self._compact_date(str(payload.get("meta", {}).get("trade_date", "")))
        if len(trade_date) != 8:
            return
        assessment = assess_market(payload)
        payload["permission"] = build_market_permission(assessment)
        shadow = build_shadow_top3(payload, assessment)
        shadow["regime"] = regime_probabilities(assessment)
        for sector in payload.get("mainlines", []):
            sector["model_prediction"] = sector_probability(sector)
        ladder_by_code = {str(item.get("code", "")): item for item in payload.get("ladder", [])}
        cores_by_code = {str(item.get("code", "")): item for item in payload.get("cores", [])}
        for plan in shadow["plans"]:
            plan["model_prediction"] = stock_probability(cores_by_code.get(plan["code"], {}), assessment, ladder_by_code.get(plan["code"]))
        now = datetime.now(SHANGHAI).isoformat(timespec="seconds")
        save_feature_snapshots(trade_date, FEATURE_VERSION, build_feature_snapshots(payload, assessment), now)
        save_shadow_plans(trade_date, PLAN_VERSION, shadow["plans"], now)
        if payload.get("ml_shadow") != shadow:
            payload["ml_shadow"] = shadow
            save_snapshot(payload, official=True)

    @staticmethod
    def _free_cause(row: dict[str, Any]) -> dict[str, Any]:
        industry = str(row.get("industry") or "市场热点")
        return {
            "concepts": [industry],
            "primary_factor": f"{industry}方向形成涨停资金共振，具体催化等待公告与公开资讯交叉确认",
            "factor_type": "板块共振",
            "confidence": "中",
            "evidence": f"东方财富涨停池所属行业：{industry}；首次封板时间：{row.get('first_limit_time') or '未提供'}",
            "source": "东方财富免费涨停池",
        }

    @staticmethod
    def _mainlines_from_limit_pool(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            industry = str(row.get("industry") or "").strip()
            if not industry:
                continue
            bucket = grouped.setdefault(industry, {"count": 0, "amount": 0.0, "changes": []})
            bucket["count"] += 1
            bucket["amount"] += float(row.get("amount") or 0)
            bucket["changes"].append(float(row.get("change") or 0))
        ranked: list[dict[str, Any]] = []
        for industry, bucket in grouped.items():
            count = int(bucket["count"])
            if count < 2:
                continue
            amount = float(bucket["amount"])
            changes = [float(value) for value in bucket["changes"]]
            score = min(92, round(58 + count * 4 + min(amount / 1_000_000_000, 12) + max(changes) * 0.5))
            ranked.append(
                {
                    "name": industry,
                    "score": score,
                    "role": "主线候选" if len(ranked) == 0 else "强支线",
                    "change": round(float(median(changes)), 2),
                    "flow": f"当日涨停池{count}只，成交额约{amount / 100_000_000:.1f}亿元",
                    "tags": ["东方财富涨停池", "同日行业热度"],
                    "source": "东方财富免费涨停池行业聚合",
                }
            )
        ranked.sort(key=lambda item: (-item["score"], -item["change"], item["name"]))
        for index, item in enumerate(ranked[:4]):
            item["role"] = "主线候选" if index == 0 else "强支线"
        return ranked[:4]

    @staticmethod
    def _same_day_market_missing_payload(reason: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        return (
            {"eligible": 0, "up": 0, "down": 0, "flat": 0, "median": 0, "limit_down": 0, "failed_limit": 0},
            {"sample": 0, "up": 0, "down": 0, "median": 0, "source": "同日Tushare缺失", "label": "容量数据缺失"},
            [{"name": "同日负反馈缺失", "change": 0, "severity": "medium", "source": reason[:120]}],
        )

    @staticmethod
    def _row_code(row: dict[str, Any]) -> str:
        return str(row.get("code") or row.get("ts_code") or "").split(".", 1)[0]

    @staticmethod
    def _has_real_name(row: dict[str, Any]) -> bool:
        code = CloseCollector._row_code(row)
        name = str(row.get("name") or "").strip()
        return bool(name and name != code)

    @staticmethod
    def _apply_stock_meta(rows: list[dict[str, Any]], meta: dict[str, dict[str, Any]]) -> None:
        for row in rows:
            code = CloseCollector._row_code(row)
            info = meta.get(code) or {}
            if not info:
                continue
            if not CloseCollector._has_real_name(row):
                row["name"] = str(info.get("name") or row.get("name") or code)
            if not str(row.get("industry") or "").strip():
                row["industry"] = str(info.get("industry") or "")

    @staticmethod
    def _seed_meta_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seeded: list[dict[str, Any]] = []
        for row in rows:
            code = CloseCollector._row_code(row)
            name = str(row.get("name") or "").strip()
            if not code or not name or name == code:
                continue
            seeded.append(
                {
                    "code": code,
                    "name": name,
                    "industry": str(row.get("industry") or "").strip(),
                    "source": str(row.get("source") or "行情快照"),
                }
            )
        return seeded

    @staticmethod
    def _market_negative_fallback(
        breadth: dict[str, Any], capacity: dict[str, Any], source: str
    ) -> list[dict[str, Any]]:
        eligible = max(1, int(breadth.get("eligible") or 1))
        down_ratio = float(breadth.get("down") or 0) / eligible
        median_value = float(breadth.get("median") or 0)
        limit_down = int(breadth.get("limit_down") or 0)
        failed_limit = int(breadth.get("failed_limit") or 0)
        capacity_median = float(capacity.get("median") or 0)
        items: list[dict[str, Any]] = []
        if median_value <= -0.5 or down_ratio >= 0.55:
            items.append(
                {
                    "name": "全市场普跌负反馈",
                    "change": round(median_value, 2),
                    "severity": "high" if median_value <= -2 or down_ratio >= 0.68 else "medium",
                    "source": f"{source}市场广度兜底",
                    "detail": f"下跌占比{down_ratio * 100:.1f}%，全市场中位{median_value:+.2f}%",
                }
            )
        if limit_down >= 15 or failed_limit >= 35:
            pressure = -max(limit_down / 10, failed_limit / 20)
            items.append(
                {
                    "name": "跌停炸板负反馈",
                    "change": round(pressure, 2),
                    "severity": "high" if limit_down >= 30 or failed_limit >= 55 else "medium",
                    "source": f"{source}跌停/炸板统计",
                    "detail": f"跌停{limit_down}只，炸板{failed_limit}只",
                }
            )
        if capacity_median >= 1 and median_value <= -0.5 and down_ratio >= 0.55:
            items.append(
                {
                    "name": "容量抱团与小票背离",
                    "change": round(median_value, 2),
                    "severity": "medium",
                    "source": f"{source}容量/广度对比",
                    "detail": f"容量中位{capacity_median:+.2f}%，全市场中位{median_value:+.2f}%",
                }
            )
        return items[:4]

    @staticmethod
    def _amount_label(amount: float) -> str:
        if amount >= 100_000_000:
            return f"{amount / 100_000_000:.1f}亿"
        if amount >= 10_000:
            return f"{amount / 10_000:.0f}万"
        return f"{amount:.0f}"

    @staticmethod
    def _is_unbounded_new_share(row: dict[str, Any]) -> bool:
        """Exclude IPO/new-share no-limit moves from normal loss-feedback math."""
        name = str(row.get("name") or "").strip().upper()
        if name.startswith(("N", "C")):
            return True
        change = float(row.get("pct_chg") or row.get("change") or 0)
        high = float(row.get("high") or 0)
        pre_close = float(row.get("pre_close") or 0)
        high_change = (high / pre_close - 1) * 100 if high > 0 and pre_close > 0 else 0.0
        return change >= 30 or high_change >= 35

    @staticmethod
    def _validated_sentiment(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Keep only auditable sentiment; drop built-in/static placeholders."""
        result: list[dict[str, Any]] = []
        for item in payload.get("sentiment", []) or []:
            topic = str(item.get("topic") or "").strip()
            source = str(item.get("source") or "").strip()
            if not topic:
                continue
            if not source and topic in {"AI硬件", "稀有金属", "新材料/稀有金属"}:
                continue
            if source in {"本地舆情清单/人工录入", "内置核验快照"}:
                continue
            if not source:
                continue
            result.append(item)
        return result

    @staticmethod
    def _sanitize_negative_stock_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in items or []:
            name = str(item.get("name") or "").strip().upper()
            change = float(item.get("change") or 0)
            drawdown = float(item.get("drawdown") or 0)
            if name.startswith(("N", "C")) or change >= 30 or drawdown >= 35:
                continue
            result.append(item)
        return result

    @staticmethod
    def _apply_linkage_to_mainlines(payload: dict[str, Any]) -> None:
        linkage_by_name = {str(item.get("name", "")): item for item in payload.get("sector_linkage", []) if item.get("name")}
        for line in payload.get("mainlines", []) or []:
            name = str(line.get("name") or "")
            linkage = linkage_by_name.get(name) or next(
                (
                    item for item in linkage_by_name.values()
                    if name and (name in str(item.get("name", "")) or str(item.get("name", "")) in name)
                ),
                None,
            )
            if not linkage:
                continue
            line["change"] = round(float(linkage.get("median_change") or 0), 2)
            tags = list(line.get("tags") or [])
            if "全板块中位涨跌" not in tags:
                tags.append("全板块中位涨跌")
            line["tags"] = tags

    @staticmethod
    def _build_checkpoints(payload: dict[str, Any]) -> list[str]:
        checkpoints: list[str] = []
        mainline = (payload.get("mainlines") or [{}])[0]
        linkage = (payload.get("sector_linkage") or [{}])[0]
        negative_stock = (payload.get("negative_stocks") or [{}])[0]
        capacity_core = (payload.get("capacity_cores") or [{}])[0]
        plan = (payload.get("planned_targets") or [{}])[0]
        breadth = payload.get("breadth") or {}
        capacity = payload.get("capacity") or {}

        if mainline.get("name"):
            checkpoints.append(
                f"主线{mainline['name']}：竞价后看龙头溢价、后排是否继续扩散，板块中位涨跌需不弱于全市场中位。"
            )
        if linkage.get("name"):
            checkpoints.append(
                f"板块联动{linkage['name']}：涨停{linkage.get('limit_up_count', 0)}只、后排{linkage.get('follower_count', 0)}只，板块中位{float(linkage.get('median_change') or 0):+.2f}%。"
            )
        if negative_stock.get("name"):
            checkpoints.append(
                f"负反馈扩散：重点盯{negative_stock['name']}({negative_stock.get('code', '')})及同板块是否继续跌停/大回撤。"
            )
        if capacity_core.get("name"):
            checkpoints.append(
                f"容量承接：{capacity_core['name']}({capacity_core.get('code', '')})不能继续放量杀跌，容量TOP{capacity.get('sample', 0)}中位{float(capacity.get('median') or 0):+.2f}%。"
            )
        if plan.get("name"):
            checkpoints.append(
                f"计划标的{plan['name']}：只在买入前提和触发买点同时满足时执行，不满足则放弃。"
            )
        else:
            checkpoints.append(
                f"无达标计划时保持空仓；若上涨{breadth.get('up', 0)}、下跌{breadth.get('down', 0)}的广度不修复，不做弱标补位。"
            )
        return checkpoints[:5]

    @staticmethod
    def _limit_factor(code: str, direction: str) -> float:
        if code.startswith(("4", "8", "9")):
            return 1.30 if direction == "up" else 0.70
        if code.startswith(("300", "301", "688")):
            return 1.20 if direction == "up" else 0.80
        return 1.10 if direction == "up" else 0.90

    @staticmethod
    def _build_negative_stocks(
        market_rows: list[dict[str, Any]],
        *,
        recent_limit_codes: set[str] | None = None,
        limit_codes: set[str] | None = None,
        limit: int = 16,
    ) -> list[dict[str, Any]]:
        rows = [row for row in market_rows if CloseCollector._row_code(row)]
        if not rows:
            return []
        max_raw_amount = max((float(row.get("amount") or 0) for row in rows), default=1.0)
        amount_unit = 1000.0 if max_raw_amount < 1_000_000_000 else 1.0
        recent_limit_codes = recent_limit_codes or set()
        limit_codes = limit_codes or set()
        items_by_code: dict[str, dict[str, Any]] = {}

        def upsert(row: dict[str, Any], tag: str, severity: str, base_score: float, detail: str) -> None:
            code = CloseCollector._row_code(row)
            if not code:
                return
            name = str(row.get("name") or code)
            if "ST" in name.upper() or "退" in name or CloseCollector._is_unbounded_new_share(row):
                return
            change = float(row.get("pct_chg") or row.get("change") or 0)
            high = float(row.get("high") or 0)
            close = float(row.get("close") or 0)
            pre_close = float(row.get("pre_close") or 0)
            high_change = (high / pre_close - 1) * 100 if high > 0 and pre_close > 0 else max(change, 0.0)
            drawdown = max(0.0, high_change - change)
            amount = float(row.get("amount") or 0) * amount_unit
            current = items_by_code.get(code)
            score = base_score + min(20.0, amount / 1_000_000_000) + min(18.0, drawdown)
            if current and float(current.get("_score") or 0) >= score:
                if tag not in current["tags"]:
                    current["tags"].append(tag)
                return
            tags = [tag]
            if code in recent_limit_codes:
                tags.append("前强负反馈")
            if code in limit_codes:
                tags.append("当日涨停后风险")
            items_by_code[code] = {
                "name": name,
                "code": code,
                "industry": str(row.get("industry") or "未分行业"),
                "change": round(change, 2),
                "drawdown": round(drawdown, 2),
                "amount": amount,
                "amount_label": CloseCollector._amount_label(amount),
                "severity": severity,
                "reason": detail,
                "tags": tags,
                "source": str(row.get("source") or "同日全市场日线"),
                "_score": round(score, 2),
            }

        for row in rows:
            code = CloseCollector._row_code(row)
            change = float(row.get("pct_chg") or row.get("change") or 0)
            high = float(row.get("high") or 0)
            close = float(row.get("close") or 0)
            pre_close = float(row.get("pre_close") or 0)
            if CloseCollector._is_unbounded_new_share(row):
                continue
            amount = float(row.get("amount") or 0) * amount_unit
            up_limit = pre_close * CloseCollector._limit_factor(code, "up") if pre_close > 0 else 0
            down_limit = pre_close * CloseCollector._limit_factor(code, "down") if pre_close > 0 else 0
            high_change = (high / pre_close - 1) * 100 if high > 0 and pre_close > 0 else 0.0
            drawdown = max(0.0, high_change - change)
            if down_limit > 0 and close > 0 and close <= down_limit + 0.011:
                upsert(row, "跌停", "high", 95, "收盘触及跌停，是最直接的亏钱效应来源")
                continue
            if up_limit > 0 and high >= up_limit - 0.011 and change < CloseCollector._limit_factor(code, "up") * 100 - 100 - 1.0:
                upsert(row, "炸板大面", "high" if drawdown >= 10 else "medium", 88, f"盘中触及涨停后回落{drawdown:.1f}个百分点")
            if drawdown >= 8 and high_change >= 4:
                upsert(row, "冲高回落", "high" if drawdown >= 12 else "medium", 78, f"盘中最高涨幅{high_change:.1f}%，收盘回撤{drawdown:.1f}个百分点")
            if amount >= 4_000_000_000 and change <= -4:
                upsert(row, "容量杀跌", "high" if change <= -7 else "medium", 82, f"成交额{CloseCollector._amount_label(amount)}且收跌{change:.1f}%")
            if code in recent_limit_codes and code not in limit_codes and (change <= -4 or drawdown >= 7):
                upsert(row, "前强断板", "high" if change <= -7 or drawdown >= 10 else "medium", 84, "近期涨停/连板活跃股出现断板或大幅回撤")

        result = sorted(
            items_by_code.values(),
            key=lambda item: (
                0 if item["severity"] == "high" else 1,
                -float(item.get("_score") or 0),
                float(item.get("change") or 0),
                item["code"],
            ),
        )[:limit]
        for item in result:
            item.pop("_score", None)
        return result

    async def _tdx_stock_meta(self, trade_date: str, code: str) -> dict[str, Any] | None:
        now = datetime.now(SHANGHAI).isoformat(timespec="seconds")
        if not reserve_tdx_call(trade_date, code, "stock_meta", now, self.settings.tdx_daily_call_limit):
            return None
        try:
            result = await self.tdx.client.call_tool(
                self.tdx.tool_name,
                {"message": f"查询股票代码{code}的股票名称和所属行业", "rang": "全部A股", "pageNo": "1", "pageSize": "5"},
            )
            matched = None
            for row in result_rows(result):
                row_code = str(field_value(row, "sec_code", "代码", default="")).split(".", 1)[0]
                if row_code == code:
                    matched = row
                    break
            matched = matched or (result_rows(result)[0] if result_rows(result) else None)
            if not matched:
                raise FreeMarketError("通达信未返回股票元数据")
            name = str(field_value(matched, "sec_name", "名称", "股票名称", default="")).strip()
            industry = str(field_value(matched, "行业", "所属行业", "板块", default="")).strip()
            if not name:
                raise FreeMarketError("通达信股票名称为空")
            complete_tdx_call(trade_date, code, "stock_meta", "success")
            return {"code": code, "name": name, "industry": industry, "source": "通达信MCP股票元数据"}
        except Exception:
            complete_tdx_call(trade_date, code, "stock_meta", "failed")
            return None

    async def _enrich_stock_meta(
        self,
        trade_date: str,
        market_rows: list[dict[str, Any]],
        reference_rows: list[dict[str, Any]],
        *,
        allow_tdx: bool,
        priority_codes: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        priority = priority_codes or []
        priority_set = set(priority)
        priority_rows = [row for row in market_rows if self._row_code(row) in priority_set]
        amount_rows = sorted(
            [row for row in market_rows if self._row_code(row) not in priority_set],
            key=lambda row: float(row.get("amount") or 0),
            reverse=True,
        )
        candidate_rows = priority_rows + amount_rows[:140]
        codes = [self._row_code(row) for row in candidate_rows if self._row_code(row)]
        now = datetime.now(SHANGHAI).isoformat(timespec="seconds")
        seeded = self._seed_meta_from_rows(reference_rows + market_rows)
        upsert_stock_meta(seeded, now)
        meta = load_stock_meta(codes)
        missing = [
            code for code in codes
            if code and (code not in meta or not meta[code].get("name") or meta[code].get("name") == code)
        ]
        fetched: list[dict[str, Any]] = []
        for code in missing[: self.FREE_META_LIMIT]:
            try:
                fetched.append(await self.free.stock_meta(code))
            except Exception:
                continue
        if fetched:
            upsert_stock_meta(fetched, now)
            meta.update({str(row["code"]): row for row in fetched})
        if allow_tdx:
            missing = [
                code for code in codes
                if code and (code not in meta or not meta[code].get("name") or meta[code].get("name") == code)
            ]
            tdx_rows: list[dict[str, Any]] = []
            for code in missing[: self.TDX_META_LIMIT]:
                item = await self._tdx_stock_meta(trade_date, code)
                if item:
                    tdx_rows.append(item)
            if tdx_rows:
                upsert_stock_meta(tdx_rows, now)
                meta.update({str(row["code"]): row for row in tdx_rows})
        return meta

    async def _same_day_market_snapshot(self, trade_date: str, limit_up_count: int) -> tuple[dict[str, Any] | None, str]:
        try:
            snapshot = await self.free.market_breadth(trade_date, limit_up_count=limit_up_count)
        except Exception as exc:
            if not self.tushare.configured:
                return None, str(exc)[:180]
            try:
                snapshot = await self.tushare.market_snapshot(trade_date)
            except Exception as fallback_exc:
                return None, f"{str(exc)[:120]}；Tushare备用失败：{str(fallback_exc)[:120]}"
            override = MANUAL_BREADTH_OVERRIDES.get(trade_date)
            if override:
                snapshot.setdefault("breadth", {}).update(override)
                snapshot["source"] = "人工校准广度 + Tushare容量"
                snapshot["calibrated_breadth"] = True
            else:
                snapshot["source"] = "Tushare备用日线"
        if str(snapshot.get("trade_date")) != trade_date:
            return None, f"东方财富返回日期 {snapshot.get('trade_date')} 与发布日期 {trade_date} 不一致"
        snapshot.setdefault("source", "东方财富全A行情列表")
        return snapshot, ""

    async def _enrich_causes(self, trade_date: str, ladder: list[dict[str, Any]]) -> None:
        if not self.settings.tdx_close_enrichment_enabled:
            return
        for item in ladder:
            if item["confidence"] == "高":
                continue
            now = datetime.now(SHANGHAI).isoformat(timespec="seconds")
            if not reserve_tdx_call(trade_date, item["code"], "limit_up_cause", now, self.settings.tdx_daily_call_limit):
                continue
            cause = await self.tdx._cause(item["code"], trade_date, item["concepts"][0])
            valid = bool(cause.get("analysis_valid"))
            complete_tdx_call(trade_date, item["code"], "limit_up_cause", "success" if valid else "failed")
            if not valid:
                continue
            cleaned = {key: value for key, value in cause.items() if key not in {"limit_dates", "analysis_valid"}}
            save_cause_cache(trade_date, item["code"], cleaned, True, now)
            item.update(cleaned)

    async def refresh(self, *, allow_tdx: bool = False) -> dict[str, Any]:
        now = datetime.now(SHANGHAI)
        close_ready = (now.hour, now.minute) >= (self.settings.close_collection_hour, self.settings.close_collection_minute)
        if not close_ready:
            payload = self.current()
            payload["meta"]["warning"] = "盘中继续展示上一可信收盘版；15:10 后生成今日收盘版。"
            return payload

        async with self._lock:
            today = now.strftime("%Y%m%d")
            existing_job = collection_status(today, self.settings.tdx_daily_call_limit).get("job") or {}
            if existing_job.get("status") == "published":
                return self.current()
            try:
                trade_dates, fetched = await self.free.recent_pools(6)
            except Exception as exc:
                payload = self.current()
                payload["meta"]["warning"] = f"免费收盘数据获取失败，继续展示上一可信版本：{str(exc)[:120]}"
                return payload

            trade_date = trade_dates[0]
            if not start_collection_job(trade_date, now.isoformat(timespec="seconds")):
                return self.current()

            try:
                for date, rows in fetched.items():
                    upsert_daily_pool(date, rows)
                pools = load_daily_pools(trade_dates)
                today_rows = pools[trade_date]
                if len(today_rows) < 5:
                    raise FreeMarketError("当日免费涨停池未通过完整性校验")

                code_sets = {date: {str(row["code"]) for row in rows} for date, rows in pools.items()}
                ladder: list[dict[str, Any]] = []
                for row in today_rows:
                    code = str(row["code"])
                    if not is_trade_candidate(code):
                        continue
                    consecutive = 0
                    for date in trade_dates:
                        if code not in code_sets[date]:
                            break
                        consecutive += 1
                    if consecutive < 2:
                        continue
                    cached = get_cause_cache(trade_date, code)
                    cause = cached or self._free_cause(row)
                    if not cached:
                        save_cause_cache(trade_date, code, cause, False, now.isoformat(timespec="seconds"))
                    ladder.append({
                        "name": row["name"], "code": code, "height": consecutive,
                        "recent_limit_count": sum(code in code_sets[date] for date in trade_dates[:5]),
                        "recent_window_days": min(5, len(trade_dates)), "change": float(row["change"]), **cause,
                    })
                ladder.sort(key=lambda item: (-item["height"], -item["change"], item["code"]))

                if allow_tdx:
                    await self._enrich_causes(trade_date, ladder)

                diagnostic = latest_snapshot()
                published = latest_trusted_snapshot()
                base = diagnostic if diagnostic and self._compact_date(str(diagnostic["meta"]["trade_date"])) == trade_date else published
                payload = deepcopy(base or DEMO_DASHBOARD)
                payload["ladder"] = ladder

                market_snapshot, market_error = await self._same_day_market_snapshot(trade_date, len(today_rows))
                payload.setdefault("data_quality", {})
                same_day_market_complete = bool(market_snapshot)
                stale_market_fallback = False
                fallback_market_date = ""
                market_source = "东方财富全A行情列表"
                if market_snapshot:
                    market_source = str(market_snapshot.get("source") or "东方财富全A行情列表")
                    breadth_status = "calibrated" if market_snapshot.get("calibrated_breadth") else "validated"
                    payload["breadth"].update(market_snapshot["breadth"])
                    capacity = dict(market_snapshot["capacity"])
                    capacity["source"] = market_source
                    capacity["label"] = _capacity_label(capacity)
                    payload["capacity"] = capacity
                    negative = market_snapshot.get("negative_sectors") or []
                    negative_from_fallback = False
                    if not negative and capacity["median"] < 0:
                        negative = [
                            {
                                "name": "容量前100负反馈",
                                "change": capacity["median"],
                                "severity": "high" if capacity["median"] <= -3 else "medium",
                                "source": market_source,
                            }
                        ]
                    if not negative:
                        negative = self._market_negative_fallback(payload["breadth"], capacity, market_source)
                        negative_from_fallback = bool(negative)
                    payload["negative"] = negative
                    payload["data_quality"].update({
                        "breadth": {"source": market_source, "status": breadth_status, "scope": "全A股，含科创板、北交所"},
                        "capacity": {"source": market_source, "status": "validated"},
                        "median": {"source": market_source, "status": "validated"},
                        "limit_down": {"source": market_source if market_snapshot.get("calibrated_breadth") else "东方财富跌停池", "status": breadth_status},
                        "failed_limit": {"source": market_source if market_snapshot.get("calibrated_breadth") else "东方财富炸板池", "status": breadth_status},
                        "negative": {
                            "source": market_source if not negative_from_fallback else f"{market_source}市场级兜底",
                            "status": "fallback" if negative_from_fallback else "validated" if negative else "empty",
                        },
                    })
                    market_rows = market_snapshot.get("rows") or []
                else:
                    fallback = latest_reliable_snapshot_before(trade_date)
                    if fallback:
                        stale_market_fallback = True
                        fallback_market_date = str(fallback.get("meta", {}).get("trade_date") or "")
                        fallback_label = f"上一可信收盘版 {fallback_market_date}".strip()
                        payload["breadth"] = deepcopy(fallback.get("breadth") or {})
                        payload["capacity"] = deepcopy(fallback.get("capacity") or {})
                        if payload["capacity"]:
                            payload["capacity"]["source"] = fallback_label
                            payload["capacity"]["label"] = _capacity_label(payload["capacity"])
                        payload["negative"] = deepcopy(fallback.get("negative") or [])
                        payload["negative_stocks"] = deepcopy(fallback.get("negative_stocks") or [])
                        fallback_quality = {"source": fallback_label, "status": "stale_fallback", "reason": market_error}
                        payload["data_quality"].update({
                            "breadth": {**fallback_quality, "scope": "全A股，含科创板、北交所"},
                            "capacity": fallback_quality,
                            "median": fallback_quality,
                            "limit_down": fallback_quality,
                            "failed_limit": fallback_quality,
                            "negative": fallback_quality,
                            "negative_stocks": fallback_quality,
                        })
                    else:
                        missing_breadth, missing_capacity, missing_negative = self._same_day_market_missing_payload(market_error)
                        payload["breadth"].update(missing_breadth)
                        payload["capacity"] = missing_capacity
                        payload["negative"] = missing_negative
                        payload["negative_stocks"] = []
                        payload["data_quality"].update({
                            "breadth": {"source": "东方财富全A行情列表", "status": "missing", "reason": market_error},
                            "capacity": {"source": "东方财富全A行情列表", "status": "missing", "reason": market_error},
                            "median": {"source": "东方财富全A行情列表", "status": "missing", "reason": market_error},
                            "negative": {"source": "东方财富容量聚合", "status": "missing", "reason": market_error},
                            "negative_stocks": {"source": "同日全市场日线", "status": "missing", "reason": market_error},
                        })
                    market_rows = []
                payload["breadth"]["limit_up"] = len(today_rows)
                payload["breadth"]["continuous"] = len(ladder)
                payload["data_quality"]["limit_up"] = {"source": "东方财富免费涨停池", "status": "validated"}
                payload.setdefault("negative_stocks", [])

                cores: list[dict[str, Any]] = [
                    {
                        "name": item["name"], "code": item["code"], "kind": "连板情绪核心",
                        "score": min(98, 80 + item["height"] * 3), "change": item["change"],
                        "evidence": f"连续{item['height']}板、近5日{item['recent_limit_count']}板；{item['primary_factor']}",
                        "source": item["source"], "confidence": item["confidence"],
                    }
                    for item in ladder
                ]
                ladder_codes = {item["code"] for item in ladder}
                for row in today_rows:
                    code = str(row["code"])
                    if code.startswith(("300", "301")) and float(row["change"]) >= 15 and code not in ladder_codes:
                        cores.append({
                            "name": row["name"], "code": code, "kind": "创业板20cm弹性核心",
                            "score": min(96, round(72 + float(row["change"]))), "change": float(row["change"]),
                            "evidence": "创业板高弹性涨停，观察板块扩散与次日溢价",
                            "source": "东方财富免费涨停池", "confidence": "中",
                            "concepts": [str(row.get("industry") or "弹性方向")],
                        })
                payload["cores"] = cores
                mainlines = self._mainlines_from_limit_pool(today_rows)
                if mainlines:
                    payload["mainlines"] = mainlines
                    payload["data_quality"]["mainlines"] = {"source": "东方财富免费涨停池行业聚合", "status": "validated"}
                if market_rows:
                    recent_limit_codes = {
                        code
                        for date in trade_dates[1:4]
                        for code in code_sets.get(date, set())
                    }
                    today_limit_codes = {str(row.get("code", "")) for row in today_rows}
                    preliminary_negative_stocks = self._build_negative_stocks(
                        market_rows,
                        recent_limit_codes=recent_limit_codes,
                        limit_codes=today_limit_codes,
                    )
                    stock_meta = await self._enrich_stock_meta(
                        trade_date,
                        market_rows,
                        today_rows,
                        allow_tdx=allow_tdx,
                        priority_codes=[str(item.get("code", "")) for item in preliminary_negative_stocks],
                    )
                    self._apply_stock_meta(market_rows, stock_meta)
                    payload["negative_stocks"] = self._build_negative_stocks(
                        market_rows,
                        recent_limit_codes=recent_limit_codes,
                        limit_codes=today_limit_codes,
                    )
                    unresolved = [
                        self._row_code(row)
                        for row in sorted(market_rows, key=lambda item: float(item.get("amount") or 0), reverse=True)[:120]
                        if not self._has_real_name(row)
                    ]
                    payload["data_quality"]["stock_meta"] = {
                        "source": "本地缓存 + 东方财富单票行情 + 通达信MCP限额兜底",
                        "status": "validated" if not unresolved else "partial",
                        "unresolved_top_count": len(unresolved),
                    }
                    payload["data_quality"]["negative_stocks"] = {
                        "source": f"{market_source} + 本地涨停池交易日缓存",
                        "status": "validated" if payload["negative_stocks"] else "empty",
                    }
                payload["sector_linkage"] = build_sector_linkage(today_rows, market_rows=market_rows, ladder=ladder)
                payload["data_quality"]["sector_linkage"] = {
                    "source": "东方财富涨停池 + Tushare行业日线" if market_rows else "东方财富涨停池",
                    "status": "validated" if payload["sector_linkage"] else "empty",
                }
                self._apply_linkage_to_mainlines(payload)
                if market_rows:
                    payload["capacity_cores"] = build_capacity_cores(
                        market_rows,
                        mainlines=payload.get("mainlines", []),
                        sector_linkage=payload.get("sector_linkage", []),
                        reference_rows=today_rows,
                        limit_codes={str(row.get("code", "")) for row in today_rows},
                    )
                    payload["data_quality"]["capacity_cores"] = {
                        "source": market_source,
                        "status": "validated" if payload["capacity_cores"] else "empty",
                    }
                elif stale_market_fallback:
                    payload["capacity_cores"] = deepcopy((fallback or {}).get("capacity_cores") or [])
                    payload["data_quality"]["capacity_cores"] = {
                        "source": f"上一可信收盘版 {fallback_market_date}".strip(),
                        "status": "stale_fallback",
                        "reason": market_error,
                    }
                else:
                    payload["capacity_cores"] = []
                    payload["data_quality"]["capacity_cores"] = {
                        "source": "同日全市场日线缺失",
                        "status": "missing",
                        "reason": market_error,
                    }
                existing_core_codes = {str(item.get("code", "")) for item in cores}
                if same_day_market_complete:
                    for candidate in capacity_cores_as_candidates(payload["capacity_cores"]):
                        if candidate["code"] not in existing_core_codes:
                            cores.append(candidate)
                            existing_core_codes.add(candidate["code"])
                payload["cores"] = cores
                payload["ml_review"] = outcome_review()
                payload["sentiment"] = self._validated_sentiment(payload)
                payload["event_signals"] = build_event_signals(
                    payload.get("sentiment", []),
                    mainlines=payload.get("mainlines", []),
                    sector_linkage=payload.get("sector_linkage", []),
                    ml_review=payload.get("ml_review", {}),
                )
                assessment = assess_market(payload)
                payload.setdefault("state", {}).update({
                    "money": assessment["money"], "loss": assessment["loss"],
                    "trend": assessment["trend"], "speculation": assessment["speculation"],
                    "cycle": assessment["cycle"], "structure": assessment["style"],
                })
                payload["permission"] = build_market_permission(assessment)
                payload["planned_targets"] = build_planned_targets(
                    cores, ladder, cycle=str(payload["state"].get("cycle", "高波动分歧")),
                    loss_score=float(payload["state"].get("loss", 50)),
                    freshness="live" if same_day_market_complete else "stale",
                    negative_names=[str(item.get("name", "")) for item in payload.get("negative", [])],
                    mainline_names=[str(item.get("name", "")) for item in payload.get("mainlines", [])],
                    sector_linkage=payload.get("sector_linkage", []),
                    event_signals=payload.get("event_signals", []),
                    market_data_complete=same_day_market_complete,
                )
                payload["checkpoints"] = self._build_checkpoints(payload)
                payload["market_graph"] = build_market_graph(payload)
                payload["ml_shadow"] = build_shadow_top3(payload, assessment)
                payload["ml_regime"] = regime_probabilities(assessment)
                payload["ml_shadow"]["regime"] = payload["ml_regime"]
                for sector in payload.get("mainlines", []):
                    sector["model_prediction"] = sector_probability(sector)
                ladder_by_code = {str(item.get("code", "")): item for item in ladder}
                for plan in payload["ml_shadow"]["plans"]:
                    core = next((item for item in cores if str(item.get("code", "")) == plan["code"]), {})
                    plan["model_prediction"] = stock_probability(core, assessment, ladder_by_code.get(plan["code"]))
                created_at = now.isoformat(timespec="seconds")
                if same_day_market_complete:
                    save_feature_snapshots(
                        trade_date, FEATURE_VERSION, build_feature_snapshots(payload, assessment), created_at
                    )
                    save_shadow_plans(trade_date, PLAN_VERSION, payload["ml_shadow"]["plans"], created_at)
                try:
                    payload["outcome_backfill"] = await self.outcomes.backfill(trade_date)
                except Exception as exc:
                    payload["outcome_backfill"] = {"error": str(exc)[:160]}
                if now.weekday() == 4:
                    try:
                        payload["training_run"] = self.training.train(now.strftime("ml-%Y%m%d"))
                    except Exception as exc:
                        payload["training_run"] = {"status": "failed", "error": str(exc)[:160]}
                payload["feature_store_status"] = feature_store_status()
                payload["ml_system"] = inference_status()
                payload.setdefault("data_quality", {})["continuous"] = {
                    "source": "东方财富免费涨停池 + 本地交易日缓存", "status": "validated",
                }
                payload["alerts"] = [
                    item for item in payload.get("alerts", []) if item.get("title") != "涨停承接"
                ] + [{
                    "level": "low", "title": "涨停承接",
                    "detail": f"免费涨停池{len(today_rows)}只、可交易真实连板{len(ladder)}只；逐股原因使用持久化缓存",
                }]
                if same_day_market_complete:
                    meta_source = f"{market_source} + 东方财富涨停池 + 本地持久化缓存"
                    meta_freshness = "live"
                    version_label = "今日收盘版"
                    meta_warning = f"通达信 MCP 仅在免费/缓存缺失时按审计额度兜底；广度为全A股口径，含科创板、北交所；市场广度来源：{market_source}。"
                    official_snapshot = True
                    job_status = "published"
                    job_error = None
                elif stale_market_fallback:
                    fallback_label = f"上一可信收盘版 {fallback_market_date}".strip()
                    meta_source = f"东方财富免费涨停池 + {fallback_label}广度/容量"
                    meta_freshness = "stale"
                    version_label = "今日部分收盘版"
                    meta_warning = (
                        f"通达信 MCP 仅在免费/缓存缺失时按审计额度兜底；今日全市场广度/容量暂缺，已沿用{fallback_label}作参考；"
                        f"正式计划等待同日数据补齐：{market_error}"
                    )
                    official_snapshot = False
                    job_status = "failed"
                    job_error = f"same-day market missing, carried {fallback_label}: {market_error}"[:300]
                else:
                    meta_source = "东方财富免费涨停池 + 同日广度缺失"
                    meta_freshness = "stale"
                    version_label = "今日部分收盘版"
                    meta_warning = f"通达信 MCP 仅在免费/缓存缺失时按审计额度兜底；今日全市场广度/容量缺失，暂无可信兜底；正式计划已暂停：{market_error}"
                    official_snapshot = False
                    job_status = "failed"
                    job_error = f"same-day market missing: {market_error}"[:300]
                payload["meta"].update({
                    "trade_date": f"{trade_date[:4]}.{trade_date[4:6]}.{trade_date[6:]}",
                    "updated_at": now.isoformat(timespec="seconds"),
                    "source": meta_source,
                    "freshness": meta_freshness,
                    "version_label": version_label,
                    "warning": meta_warning,
                })
                payload["collection_status"] = collection_status(trade_date, self.settings.tdx_daily_call_limit)
                save_snapshot(payload, official=official_snapshot)
                finish_collection_job(trade_date, job_status, now.isoformat(timespec="seconds"), job_error)
                return self.current()
            except Exception as exc:
                finish_collection_job(trade_date, "failed", datetime.now(SHANGHAI).isoformat(timespec="seconds"), str(exc)[:300])
                payload = self.current()
                payload["meta"]["warning"] = f"今日收盘版生成失败，继续展示上一可信版本：{str(exc)[:120]}"
                return payload
