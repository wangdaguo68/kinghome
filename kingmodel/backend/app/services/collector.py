from __future__ import annotations

import asyncio
import re
from copy import deepcopy
from datetime import datetime, timezone
from statistics import median
from typing import Any

import httpx

from ..config import get_settings
from ..db import latest_snapshot, save_snapshot
from ..engine.decision import MarketInputs, classify_cycle, position_limit, score_market
from .market_validation import (
    InvalidMarketData,
    field_value,
    is_trade_candidate,
    number,
    result_rows,
    result_total,
    row_change,
    validate_breadth_totals,
    validate_result,
)
from .ladder import calculate_ladder_metrics, trade_dates_from_tdx_kline
from .planning import build_planned_targets
from .tdx_mcp import TdxMcpClient, TdxMcpError
from .tushare_fallback import TushareError, TushareFallback


DEMO_DASHBOARD: dict[str, Any] = {
    "meta": {
        "trade_date": "2026-06-18",
        "updated_at": "2026-06-18T15:00:00+08:00",
        "source": "内置核验快照",
        "freshness": "sample",
        "warning": "历史核验快照；实时采集后按全 A（含科创板、北交所）更新。",
    },
    "permission": {"label": "谨慎进攻", "position_limit": 40, "allowed": "主线核心分歧回踩", "forbidden": "非主线轮动高潮追涨"},
    "state": {"cycle": "高波动分歧", "structure": "科技主线加速 / 非主线退潮", "money": 61, "loss": 68, "trend": 72, "speculation": 61},
    "breadth": {"eligible": 5_187, "up": 1_958, "down": 3_139, "flat": 90, "median": -0.83, "limit_up": 91, "limit_down": 12, "failed_limit": 44, "continuous": 12},
    "capacity": {"sample": 100, "up": 76, "down": 24, "median": 2.15, "label": "容量正反馈", "source": "Tushare交叉核验"},
    "mainlines": [
        {"name": "AI硬件", "score": 78, "role": "主线", "change": 4.0, "flow": "权重防御 → 科技成长", "tags": ["半导体", "CPO", "PCB", "消费电子"]},
        {"name": "新材料/稀有金属", "score": 69, "role": "强支线", "change": 2.66, "flow": "材料内部扩散", "tags": ["稀有金属", "非金属材料"]},
    ],
    "cores": [
        {"name": "旭光电子", "code": "600353", "kind": "连板情绪核心", "score": 92, "change": 10.0, "evidence": "4连板，情绪高度领先"},
        {"name": "工业富联", "code": "601138", "kind": "趋势容量核心", "score": 88, "change": 7.49, "evidence": "成交330.63亿元，容量与主动性突出"},
    ],
    "negative": [
        {"name": "保险", "change": -6.10, "severity": "high"},
        {"name": "电力", "change": -3.40, "severity": "high"},
    ],
    "alerts": [
        {"level": "low", "title": "容量正反馈", "detail": "成交额前100中76只上涨，涨跌幅中位数+2.15%"},
        {"level": "medium", "title": "强势股承接待验证", "detail": "连板晋级和炸板数据等待下一次可信快照"},
    ],
    "ladder": [],
    "planned_targets": [],
    "data_quality": {},
    "sentiment": [],
    "checkpoints": ["样例快照仅用于界面验证，正式盘中确认清单由当日主线、联动、负反馈和计划标的动态生成。"],
}


QUERIES: dict[str, tuple[str, str, int]] = {
    "up": ("今日上涨股票", "AG", 1),
    "down": ("今日下跌股票", "AG", 1),
    "flat": ("今日平盘股票", "AG", 1),
    "limit_up": ("今日非ST且上市天数大于等于10日的涨停股票", "AG", 100),
    "limit_down": ("今日非ST且上市天数大于等于10日的跌停股票", "AG", 100),
    "failed_limit": ("今日非ST且上市天数大于等于10日曾经涨停但收盘未涨停的股票", "AG", 100),
    "continuous": ("今日非ST且上市天数大于等于10日的连板股票", "AG", 100),
    "sector_top": ("今日行业板块指数按涨幅从高到低排名", "ZS", 20),
    "sector_bottom": ("今日行业板块指数按涨幅从低到高排名", "ZS", 20),
    "amount_top": ("今日A股按成交额从大到小排名", "AG", 100),
}


def _trade_date(result: dict[str, Any]) -> str:
    for header in result.get("headers", []):
        match = re.search(r"20\d{2}[.\-/]\d{2}[.\-/]\d{2}", str(header))
        if match:
            return match.group(0).replace("-", ".").replace("/", ".")
    return ""


def _capacity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changes = [row_change(row) for row in rows[:100]]
    if not changes:
        raise InvalidMarketData("成交额前100没有有效涨跌幅")
    return {
        "sample": len(changes),
        "up": sum(value > 0 for value in changes),
        "down": sum(value < 0 for value in changes),
        "median": round(float(median(changes)), 2),
    }


def _capacity_label(capacity: dict[str, Any]) -> str:
    ratio = 100 * capacity["up"] / max(1, capacity["sample"])
    if ratio >= 55 and capacity["median"] > 0:
        return "容量正反馈"
    if ratio < 40 and capacity["median"] < 0:
        return "容量负反馈"
    return "容量分歧"


def _capacity_alert(capacity: dict[str, Any]) -> dict[str, str]:
    label = _capacity_label(capacity)
    level = "low" if label == "容量正反馈" else "high" if label == "容量负反馈" else "medium"
    sign = "+" if capacity["median"] > 0 else ""
    return {
        "level": level,
        "title": label,
        "detail": f"成交额前{capacity['sample']}中{capacity['up']}只上涨，涨跌幅中位数{sign}{capacity['median']:.2f}%",
    }


def _factor_type(theme: str, reason: str) -> str:
    primary = reason.split("|", 1)[0]
    if any(word in primary for word in ("工信部", "发改委", "国务院", "政策", "规划", "监管")):
        return "政策"
    if any(word in primary for word in ("公告", "定增", "回购", "中标", "签订", "业绩")):
        return "公告"
    text = f"{theme} {reason}"
    if any(word in text for word in ("公告", "定增", "回购", "中标", "签订", "业绩")):
        return "公告"
    if any(word in text for word in ("工信部", "发改委", "国务院", "政策", "规划", "监管")):
        return "政策"
    if any(word in text for word in ("涨价", "供给", "需求", "产能", "订单", "产业链")):
        return "产业"
    if "|" in reason:
        return "事件"
    return "板块共振"


def _split_concepts(theme: str) -> list[str]:
    return [item.strip() for item in re.split(r"[+、，,/|]", theme) if item.strip()][:6]


class Collector:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = TdxMcpClient(settings.tdx_mcp_url, settings.tdx_mcp_token)
        self.tushare = TushareFallback(settings.tushare_token, settings.tushare_api_url)
        self.tool_name = settings.tdx_mcp_tool
        self.last_error: str | None = None
        self._cause_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def current(self) -> dict[str, Any]:
        payload = latest_snapshot() or deepcopy(DEMO_DASHBOARD)
        for key in ("capacity", "ladder", "planned_targets", "data_quality"):
            payload.setdefault(key, deepcopy(DEMO_DASHBOARD[key]))
        legacy_kinds = {"情绪龙头": "连板情绪核心", "趋势中军": "趋势容量核心", "弹性先锋": "创业板20cm弹性核心"}
        for core in payload.get("cores", []):
            core["kind"] = legacy_kinds.get(core.get("kind"), core.get("kind"))
        return payload

    async def _tdx_results(self) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        results: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        for key, (query, market, size) in QUERIES.items():
            try:
                result = await self.client.call_tool(
                    self.tool_name,
                    {"message": query, "rang": market, "pageNo": "1", "pageSize": str(size)},
                )
                validate_result(key, result)
                results[key] = result
            except (TdxMcpError, httpx.HTTPError, InvalidMarketData, ValueError, KeyError) as exc:
                errors[key] = str(exc)
        if all(key in results for key in ("up", "down", "flat")):
            try:
                validate_breadth_totals(*(result_total(results[key]) for key in ("up", "down", "flat")))
            except InvalidMarketData as exc:
                for key in ("up", "down", "flat"):
                    errors[key] = str(exc)
                    results.pop(key, None)
        return results, errors

    async def _cause(self, code: str, trade_date: str, fallback_concept: str) -> dict[str, Any]:
        cache_key = (trade_date, code)
        if cache_key in self._cause_cache:
            return self._cause_cache[cache_key]
        try:
            result = await self.client.call_tool(
                "tdx_api_data",
                {"entry": "TdxSharePCCW.tdxf10_gg_jyds", "code": code, "fixedTag": "ztfx", "extra": ""},
            )
            transformed = result.get("response", {}).get("transformed", {})
            rows = [row for table in transformed.get("tables", []) for row in table.get("rows", [])]
            compact = trade_date.replace(".", "").replace("-", "")
            normalized = f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}" if len(compact) == 8 else trade_date.replace(".", "-")
            row = next((item for item in rows if str(item.get("日期", "")) == normalized and item.get("类型") == "涨停"), None)
            row = row or next((item for item in rows if item.get("类型") == "涨停"), None)
            if not row:
                raise InvalidMarketData("涨停分析没有有效记录")
            limit_dates = sorted(
                {str(item.get("日期", "")) for item in rows if item.get("类型") == "涨停" and item.get("日期")},
                reverse=True,
            )
            theme = str(row.get("涨停主题") or fallback_concept or "板块共振")
            reason = str(row.get("原因揭秘") or "")
            primary = reason.split("|", 1)[0].strip() if reason else f"{theme}方向形成资金共振"
            exact_date = str(row.get("日期", "")) == normalized
            cause = {
                "concepts": _split_concepts(theme),
                "primary_factor": primary[:120],
                "factor_type": _factor_type(theme, reason),
                "confidence": "高" if exact_date and reason else "中" if reason else "低",
                "evidence": reason[:220] or f"涨停主题：{theme}",
                "source": "通达信涨停分析",
                "limit_dates": limit_dates,
                "analysis_valid": True,
            }
        except (TdxMcpError, httpx.HTTPError, InvalidMarketData, ValueError, KeyError) as exc:
            concept = fallback_concept or "市场热点"
            cause = {
                "concepts": [concept],
                "primary_factor": f"{concept}方向形成板块共振",
                "factor_type": "板块共振",
                "confidence": "低",
                "evidence": f"结构化涨停分析暂不可用：{str(exc)[:100]}",
                "source": "模型推断",
                "limit_dates": [],
                "analysis_valid": False,
            }
        self._cause_cache[cache_key] = cause
        return cause

    @staticmethod
    def _trade_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            row for row in result_rows(result)
            if is_trade_candidate(str(row.get("sec_code", "")))
            and "ST" not in str(row.get("sec_name", "")).upper()
        ]

    async def _recent_trade_dates(self, target_date: str, count: int = 15) -> tuple[list[str], str, str]:
        tdx_error = ""
        try:
            result = await self.client.call_tool(
                "tdx_kline",
                {
                    "code": "000001",
                    "setcode": "1",
                    "target": "0",
                    "period": "4",
                    "wantNum": str(max(30, count * 2)),
                    "startxh": "0",
                    "tqFlag": "0",
                },
            )
            return trade_dates_from_tdx_kline(result, target_date, count), "通达信指数日线", ""
        except (TdxMcpError, httpx.HTTPError, ValueError, KeyError) as exc:
            tdx_error = str(exc)[:120]
        dates = await self.tushare.recent_trade_dates(target_date, count)
        return dates, "Tushare交易日历", f"通达信交易日序列失败：{tdx_error}"

    async def refresh(self) -> dict[str, Any]:
        current = deepcopy(self.current())
        results: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        if self.client.configured:
            results, errors = await self._tdx_results()
        else:
            errors["tdx"] = "通达信 MCP 未配置"

        target_date = next((_trade_date(result) for result in results.values() if _trade_date(result)), "")
        fallback: dict[str, Any] | None = None
        fallback_error = ""
        # 通达信选股提供方向和榜单，但不提供可靠的全市场涨跌幅中位数；
        # Tushare 日线在此作为该单项的备用计算源，同时承接其他失败项。
        needs_fallback = True
        if self.tushare.configured and (needs_fallback or "amount_top" not in results):
            try:
                fallback = await self.tushare.market_snapshot(target_date or None)
            except (TushareError, httpx.HTTPError, ValueError, KeyError) as exc:
                fallback_error = str(exc)
                if not target_date:
                    try:
                        fallback = await self.tushare.market_snapshot(str(current["meta"]["trade_date"]))
                    except (TushareError, httpx.HTTPError, ValueError, KeyError) as retry_exc:
                        fallback_error = f"{fallback_error}; {retry_exc}"

        if not results and not fallback:
            current["meta"]["freshness"] = "stale"
            current["meta"]["warning"] = "通达信与 Tushare 均不可用，保留最近可信快照。"
            self.last_error = "; ".join([*errors.values(), fallback_error])
            return current

        payload = current
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        quality: dict[str, dict[str, str]] = {}

        if all(key in results for key in ("up", "down", "flat")):
            breadth_values = {key: result_total(results[key]) for key in ("up", "down", "flat")}
            breadth_values["eligible"] = sum(breadth_values.values())
            breadth_source = "通达信官方 MCP"
        elif fallback:
            breadth_values = {key: fallback["breadth"][key] for key in ("up", "down", "flat", "eligible")}
            breadth_source = "Tushare备用"
        else:
            breadth_values = {key: payload["breadth"][key] for key in ("up", "down", "flat", "eligible")}
            breadth_source = "最近可信快照"
        payload["breadth"].update(breadth_values)

        for key in ("limit_up", "limit_down", "failed_limit"):
            if key in results:
                payload["breadth"][key] = result_total(results[key])
                quality[key] = {"source": "通达信官方 MCP", "status": "validated"}
            elif fallback:
                payload["breadth"][key] = fallback["breadth"][key]
                quality[key] = {"source": "Tushare备用", "status": "fallback", "reason": errors.get(key, "")[:120]}
            else:
                quality[key] = {"source": "最近可信快照", "status": "stale", "reason": errors.get(key, "")[:120]}

        if fallback:
            payload["breadth"]["median"] = fallback["breadth"]["median"]
            quality["median"] = {"source": "Tushare备用", "status": "validated"}

        if "amount_top" in results:
            capacity = _capacity(result_rows(results["amount_top"]))
            capacity["source"] = "通达信官方 MCP"
        elif fallback:
            capacity = dict(fallback["capacity"])
            capacity["source"] = "Tushare备用"
        else:
            capacity = dict(payload.get("capacity", DEMO_DASHBOARD["capacity"]))
            capacity["source"] = "最近可信快照"
        capacity["label"] = _capacity_label(capacity)
        payload["capacity"] = capacity
        top_sectors = []
        if "sector_top" in results:
            top_sectors = [row for row in result_rows(results["sector_top"]) if str(row.get("sec_code", "")).startswith(("880", "881"))][:6]
            payload["mainlines"] = [
                {
                    "name": row.get("sec_name", "未知板块"),
                    "score": min(90, max(50, round(58 + row_change(row) * 4))),
                    "role": "主线候选" if index == 0 else "强支线",
                    "change": row_change(row),
                    "flow": "板块强度与成交共振待确认",
                    "tags": ["实时强度", "次日溢价待验证"],
                }
                for index, row in enumerate(top_sectors[:4])
            ]
        if "sector_bottom" in results:
            bottom = [row for row in result_rows(results["sector_bottom"]) if str(row.get("sec_code", "")).startswith(("880", "881"))][:6]
            payload["negative"] = [
                {"name": row.get("sec_name", "未知"), "change": row_change(row), "severity": "high" if row_change(row) <= -4 else "medium"}
                for row in bottom
            ]

        limit_rows = self._trade_rows(results["limit_up"]) if "limit_up" in results else []
        continuous_rows = self._trade_rows(results["continuous"]) if "continuous" in results else []
        amount_rows = self._trade_rows(results["amount_top"]) if "amount_top" in results else []
        fallback_concept = payload["mainlines"][0]["name"] if payload.get("mainlines") else "市场热点"
        analysis_date = target_date or (fallback["trade_date"] if fallback else str(payload["meta"]["trade_date"]))

        ladder: list[dict[str, Any]] = []
        if "continuous" in results:
            try:
                trade_dates, calendar_source, calendar_reason = await self._recent_trade_dates(analysis_date, 15)
                causes = await asyncio.gather(*(
                    self._cause(str(row.get("sec_code", "")), analysis_date, fallback_concept)
                    for row in continuous_rows
                ))
                for row, cause in zip(continuous_rows, causes, strict=False):
                    if not cause.get("analysis_valid"):
                        continue
                    metrics = calculate_ladder_metrics(cause.get("limit_dates", []), trade_dates, analysis_date)
                    if metrics.consecutive < 2:
                        continue
                    code = str(row.get("sec_code", ""))
                    ladder.append({
                        "name": row.get("sec_name", code),
                        "code": code,
                        "height": metrics.consecutive,
                        "recent_limit_count": metrics.recent_limit_count,
                        "recent_window_days": metrics.recent_window_days,
                        "change": row_change(row),
                        **{key: value for key, value in cause.items() if key not in {"limit_dates", "analysis_valid"}},
                    })
                ladder.sort(key=lambda item: (-item["height"], -item["change"], item["code"]))
                payload["breadth"]["continuous"] = len(ladder)
                quality["continuous"] = {
                    "source": f"通达信涨停分析 + {calendar_source}",
                    "status": "validated" if calendar_source.startswith("通达信") else "fallback",
                    **({"reason": calendar_reason} if calendar_reason else {}),
                }
            except (TushareError, httpx.HTTPError, ValueError, KeyError) as exc:
                quality["continuous"] = {"source": "最近可信快照", "status": "stale", "reason": str(exc)[:120]}
            else:
                payload["ladder"] = ladder
        else:
            quality["continuous"] = {"source": "最近可信快照", "status": "stale", "reason": errors.get("continuous", "")[:120]}

        payload["alerts"] = [
            _capacity_alert(capacity),
            {
                "level": "medium" if payload["breadth"]["failed_limit"] > 30 else "low",
                "title": "涨停承接",
                "detail": f"涨停{payload['breadth']['limit_up']}只、炸板{payload['breadth']['failed_limit']}只、可交易真实连板{payload['breadth']['continuous']}只",
            },
        ]

        if quality.get("continuous", {}).get("status") in {"validated", "fallback"}:
            payload["ladder"] = ladder

        cores: list[dict[str, Any]] = []
        for item in ladder:
            cores.append({"name": item["name"], "code": item["code"], "kind": "连板情绪核心", "score": min(98, 80 + item["height"] * 3), "change": item["change"], "evidence": f"连续{item['height']}板、近{item['recent_window_days']}日{item['recent_limit_count']}板；{item['primary_factor']}", "source": item["source"], "confidence": item["confidence"]})
        for row in amount_rows:
            code = str(row.get("sec_code", ""))
            amount = number(field_value(row, "成交额", default=0))
            change = row_change(row)
            if amount >= 10_000_000_000 and change > 0:
                cores.append({"name": row.get("sec_name", code), "code": code, "kind": "趋势容量核心", "score": min(95, round(78 + min(change, 10))), "change": change, "evidence": f"成交额约{amount / 100_000_000:.1f}亿元，容量与主动性共振", "source": "通达信官方 MCP", "confidence": "中"})
        for row in limit_rows:
            code = str(row.get("sec_code", ""))
            change = row_change(row)
            if code.startswith(("300", "301")) and change >= 15:
                cores.append({"name": row.get("sec_name", code), "code": code, "kind": "创业板20cm弹性核心", "score": min(96, round(72 + change)), "change": change, "evidence": "创业板高弹性涨停，观察板块扩散与次日溢价", "source": "通达信官方 MCP", "confidence": "中"})
        if cores:
            payload["cores"] = cores

        top_change = max([row_change(row) for row in top_sectors], default=0)
        scores = score_market(MarketInputs(
            up_ratio=100 * payload["breadth"]["up"] / max(1, payload["breadth"]["eligible"]),
            median_change=float(payload["breadth"].get("median", 0)),
            limit_up=int(payload["breadth"]["limit_up"]),
            limit_down=int(payload["breadth"]["limit_down"]),
            failed_limit=int(payload["breadth"]["failed_limit"]),
            continuation_rate=100 * payload["breadth"]["continuous"] / max(1, payload["breadth"]["limit_up"]),
            trend_strength=min(90, 55 + top_change * 4),
            speculation_strength=min(90, 45 + payload["breadth"]["limit_up"] * 0.25),
            loss_spreading=payload["breadth"]["limit_down"] >= 20,
        ))
        cycle = classify_cycle(scores)
        payload["state"].update(scores)
        payload["state"]["cycle"] = cycle
        payload["permission"]["position_limit"] = position_limit(cycle, scores["loss"])
        payload["permission"]["label"] = "顺风进攻" if cycle == "主升" else "谨慎进攻" if cycle in {"高波动分歧", "试错修复"} else "防守观察"

        used_sources = {breadth_source, capacity["source"], *(item.get("source", "") for item in quality.values())}
        used_sources.discard("")
        source = " + ".join(sorted(used_sources - {"最近可信快照"})) or "最近可信快照"
        target = target_date or (fallback["trade_date"] if fallback else payload["meta"]["trade_date"])
        payload["meta"].update({
            "updated_at": now,
            "trade_date": target[:4] + "." + target[4:6] + "." + target[6:8] if target.isdigit() and len(target) == 8 else target,
            "source": source,
            "freshness": "live" if "最近可信快照" not in used_sources else "stale",
            "warning": "市场广度为全 A（含科创板、北交所）；交易候选排除科创板和北交所。" + (f" {len(errors)}项通达信结果已降级。" if errors else ""),
        })
        payload["planned_targets"] = build_planned_targets(
            payload.get("cores", []),
            payload.get("ladder", []),
            cycle=cycle,
            loss_score=scores["loss"],
            freshness=payload["meta"]["freshness"],
            negative_names=[str(item.get("name", "")) for item in payload.get("negative", [])],
            mainline_names=[str(item.get("name", "")) for item in payload.get("mainlines", [])],
            market_data_complete=bool(payload.get("breadth", {}).get("eligible")),
        )
        quality["breadth"] = {"source": breadth_source, "status": "validated" if breadth_source != "最近可信快照" else "stale"}
        quality["capacity"] = {"source": capacity["source"], "status": "validated" if capacity["source"] != "最近可信快照" else "stale"}
        payload["data_quality"] = quality
        self.last_error = "; ".join([*errors.values(), fallback_error]) or None
        save_snapshot(payload)
        return payload
