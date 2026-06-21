from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import get_settings
from ..db import latest_snapshot, save_snapshot
from ..engine.decision import MarketInputs, classify_cycle, position_limit, score_market
from .tdx_mcp import TdxMcpClient, TdxMcpError


DEMO_DASHBOARD: dict[str, Any] = {
    "meta": {
        "trade_date": "2026-06-18",
        "updated_at": "2026-06-18T15:00:00+08:00",
        "source": "内置核验快照",
        "freshness": "sample",
        "warning": "当前展示已核验的历史快照；配置通达信 MCP 后切换为实时数据。",
    },
    "permission": {"label": "谨慎进攻", "position_limit": 40, "allowed": "主线核心分歧回踩", "forbidden": "非主线轮动高潮追涨"},
    "state": {"cycle": "高波动分歧", "structure": "科技主线加速 / 非主线退潮", "money": 61, "loss": 68, "trend": 72, "speculation": 61},
    "breadth": {"eligible": 4364, "up": 1508, "down": 2782, "flat": 74, "median": -0.83, "limit_up": 82, "limit_down": 12, "failed_limit": 40, "continuous": 11},
    "mainlines": [
        {"name": "AI硬件", "score": 78, "role": "主线", "change": 4.0, "flow": "权重防御 → 科技成长", "tags": ["半导体", "CPO", "PCB", "消费电子"]},
        {"name": "新材料/稀有金属", "score": 69, "role": "强支线", "change": 2.66, "flow": "材料内部扩散", "tags": ["稀有金属", "非金属材料"]},
    ],
    "cores": [
        {"name": "旭光电子", "code": "600353", "kind": "情绪龙头", "score": 84, "change": 10.0, "evidence": "连续4板、区间5板，主线辨识度最高"},
        {"name": "工业富联", "code": "601138", "kind": "趋势中军", "score": 88, "change": 7.49, "evidence": "成交330.63亿元，容量与主动性突出"},
        {"name": "光迅科技", "code": "002281", "kind": "弹性先锋", "score": 82, "change": 10.0, "evidence": "CPO高容量涨停，带动通信设备"},
    ],
    "negative": [
        {"name": "保险", "change": -6.10, "severity": "high"},
        {"name": "电力", "change": -3.40, "severity": "high"},
        {"name": "证券", "change": -3.01, "severity": "medium"},
        {"name": "银行", "change": -2.60, "severity": "medium"},
    ],
    "alerts": [
        {"level": "high", "title": "容量负反馈", "detail": "高成交额前100样本仅5只上涨，中位数-2.41%"},
        {"level": "medium", "title": "强势股承接偏弱", "detail": "昨日涨停今日收益中位数-0.80%"},
    ],
    "sentiment": [
        {"topic": "AI硬件", "heat": 82, "crowding": "高", "catalyst": "产业链与涨价信息集中发酵", "validation": "竞价溢价与中军承接"},
        {"topic": "稀有金属", "heat": 61, "crowding": "中", "catalyst": "材料供给扰动", "validation": "板块成交占比继续提高"},
    ],
    "checkpoints": ["主线成交占比是否继续提高", "工业富联与光迅科技能否获得承接", "金融、电力和光伏负反馈是否扩散"],
}


class Collector:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = TdxMcpClient(settings.tdx_mcp_url, settings.tdx_mcp_token)
        self.tool_name = settings.tdx_mcp_tool
        self.last_error: str | None = None

    def current(self) -> dict[str, Any]:
        return latest_snapshot() or deepcopy(DEMO_DASHBOARD)

    async def refresh(self) -> dict[str, Any]:
        if not self.client.configured:
            return self.current()
        try:
            queries: dict[str, tuple[str, str, int]] = {
                "up": ("今日上涨股票", "AG", 1),
                "down": ("今日下跌股票", "AG", 1),
                "flat": ("今日平盘股票", "AG", 1),
                "limit_up": ("今日非ST且上市天数大于等于60日的涨停股票", "AG", 100),
                "limit_down": ("今日非ST且上市天数大于等于60日的跌停股票", "AG", 100),
                "failed_limit": ("今日非ST且上市天数大于等于60日曾经涨停但收盘未涨停的股票", "AG", 100),
                "continuous": ("今日非ST且上市天数大于等于60日的连板股票", "AG", 100),
                "sector_top": ("今日行业板块指数按涨幅从高到低排名", "ZS", 20),
                "sector_bottom": ("今日行业板块指数按涨幅从低到高排名", "ZS", 20),
                "amount_top": ("今日非ST且上市天数大于等于60日的股票按成交额从大到小排名", "AG", 50),
            }
            totals: dict[str, int] = {}
            results: dict[str, dict[str, Any]] = {}
            trade_date = ""
            for key, (query, market, size) in queries.items():
                result = await self.client.call_tool(
                    self.tool_name,
                    {"message": query, "rang": market, "pageNo": "1", "pageSize": str(size)},
                )
                results[key] = result
                totals[key] = int(result.get("meta", {}).get("total", 0))
                headers = result.get("headers", [])
                for header in headers:
                    if "20" in str(header):
                        trade_date = str(header).split("<br>")[-1].split("0#")[0]
                        break
            payload = deepcopy(self.current())
            now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            payload["meta"].update({
                "updated_at": now,
                "trade_date": trade_date or payload["meta"]["trade_date"],
                "source": "通达信官方 MCP",
                "freshness": "live",
                "warning": "盘中广度为全A情绪口径；候选标的执行主板/创业板过滤，中位数沿用最近完整快照。",
            })
            payload["breadth"].update({key: value for key, value in totals.items() if key in payload["breadth"]})
            payload["breadth"]["eligible"] = totals["up"] + totals["down"] + totals["flat"]

            def row_value(row: dict[str, Any], *prefixes: str, default: Any = "") -> Any:
                for prefix in prefixes:
                    for field, value in row.items():
                        if str(field).startswith(prefix):
                            return value
                return default

            def trade_rows(key: str) -> list[dict[str, Any]]:
                prefixes = ("000", "001", "002", "003", "300", "301", "600", "601", "603", "605")
                return [
                    row for row in results[key].get("data", [])
                    if str(row.get("sec_code", "")).startswith(prefixes)
                    and "ST" not in str(row.get("sec_name", "")).upper()
                ]

            top_sectors = [
                row for row in results["sector_top"].get("data", [])
                if str(row.get("sec_code", "")).startswith(("880", "881"))
            ][:4]
            if top_sectors:
                payload["mainlines"] = [
                    {
                        "name": row.get("sec_name", "未知板块"),
                        "score": min(90, max(50, round(58 + float(row.get("chg", 0)) * 4))),
                        "role": "主线候选" if index == 0 else "强支线",
                        "change": float(row.get("chg", 0)),
                        "flow": "板块强度与成交共振待确认",
                        "tags": ["实时强度", "次日溢价待验证"],
                    }
                    for index, row in enumerate(top_sectors[:2])
                ]

            bottom_sectors = results["sector_bottom"].get("data", [])[:4]
            if bottom_sectors:
                payload["negative"] = [
                    {
                        "name": row.get("sec_name", "未知"),
                        "change": float(row.get("chg", 0)),
                        "severity": "high" if float(row.get("chg", 0)) <= -4 else "medium",
                    }
                    for row in bottom_sectors
                ]

            limit_rows = trade_rows("limit_up")
            continuous_rows = trade_rows("continuous")
            amount_rows = [row for row in trade_rows("amount_top") if float(row.get("chg", 0) or 0) > 0]
            core_rows: list[dict[str, Any]] = []
            if continuous_rows:
                row = max(continuous_rows, key=lambda item: float(row_value(item, "几板", default=1) or 1))
                core_rows.append({"name": row.get("sec_name"), "code": row.get("sec_code"), "kind": "情绪龙头", "score": 84, "change": float(row.get("chg", 0)), "evidence": f"连板梯队领先，区间{row_value(row, '几板', default='-')}板"})
            if amount_rows:
                row = amount_rows[0]
                amount = float(row_value(row, "成交额", default=0) or 0) / 100_000_000
                core_rows.append({"name": row.get("sec_name"), "code": row.get("sec_code"), "kind": "趋势中军", "score": 86, "change": float(row.get("chg", 0)), "evidence": f"成交额约{amount:.1f}亿元，容量与主动性领先"})
            if limit_rows:
                existing = {item.get("code") for item in core_rows}
                row = next((item for item in limit_rows if item.get("sec_code") not in existing), limit_rows[0])
                core_rows.append({"name": row.get("sec_name"), "code": row.get("sec_code"), "kind": "弹性先锋", "score": 80, "change": float(row.get("chg", 0)), "evidence": "涨停强度领先，板块影响力待盘中验证"})
            if core_rows:
                payload["cores"] = core_rows

            top_change = max([float(row.get("chg", 0)) for row in top_sectors], default=0)
            scores = score_market(MarketInputs(
                up_ratio=100 * totals["up"] / max(1, totals["up"] + totals["down"] + totals["flat"]),
                median_change=float(payload["breadth"].get("median", 0)),
                limit_up=totals["limit_up"],
                limit_down=totals["limit_down"],
                failed_limit=totals["failed_limit"],
                continuation_rate=100 * totals["continuous"] / max(1, totals["limit_up"]),
                trend_strength=min(90, 55 + top_change * 4),
                speculation_strength=min(90, 45 + totals["limit_up"] * 0.25),
                loss_spreading=totals["limit_down"] >= 20,
            ))
            cycle = classify_cycle(scores)
            payload["state"].update(scores)
            payload["state"]["cycle"] = cycle
            payload["permission"]["position_limit"] = position_limit(cycle, scores["loss"])
            payload["permission"]["label"] = "顺风进攻" if cycle == "主升" else "谨慎进攻" if cycle in {"高波动分歧", "试错修复"} else "防守观察"
            self.last_error = None
            save_snapshot(payload)
            return payload
        except (TdxMcpError, httpx.HTTPError, ValueError, KeyError) as exc:
            self.last_error = str(exc)
            payload = deepcopy(self.current())
            payload["meta"]["freshness"] = "stale"
            payload["meta"]["warning"] = f"通达信 MCP 更新失败，保留最近成功值：{self.last_error}"
            return payload
