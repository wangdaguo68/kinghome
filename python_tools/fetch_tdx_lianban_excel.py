#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fetch recent A-share limit-up streak data through the configured Tongdaxin MCP
server and export a review-focused Excel workbook.

Default run:
    python fetch_tdx_lianban_excel.py

Useful options:
    python fetch_tdx_lianban_excel.py --months 3 --output 连板复盘_近3个月.xlsx
    python fetch_tdx_lianban_excel.py --start 20260311 --end 20260611
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import tomllib


DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
TOOL_NAME = "tdx_wenda_quotes"
MCP_PROTOCOL_VERSION = "2025-03-26"


@dataclass
class QueryResult:
    trade_date: str
    question: str
    total: int
    rows: list[dict[str, Any]]
    headers: list[str]
    error: str = ""


class TdxMcpClient:
    def __init__(self, config_path: Path, server_name: str = "-mcp", timeout: int = 45) -> None:
        self.config_path = config_path
        self.server_name = server_name
        self.timeout = timeout
        self.url = ""
        self.headers: dict[str, str] = {}
        self.next_id = 1
        self._load_config()
        self._initialize()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"找不到 Codex MCP 配置文件: {self.config_path}")

        cfg = tomllib.loads(self.config_path.read_text(encoding="utf-8"))
        servers = cfg.get("mcp_servers", {})
        if self.server_name not in servers:
            names = ", ".join(servers.keys()) or "(无)"
            raise KeyError(f"配置中没有 MCP server `{self.server_name}`，现有: {names}")

        server = servers[self.server_name]
        self.url = server["url"]
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/event-stream",
        }
        self.headers.update(server.get("http_headers", {}))

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(self.url, headers=self.headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        events = parse_sse_or_json(response.content)
        if not events:
            raise RuntimeError("MCP 返回为空")
        message = events[-1]
        if "error" in message:
            raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
        return message

    def _initialize(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": self._id(),
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "tdx-lianban-excel", "version": "0.1.0"},
            },
        }
        response = requests.post(self.url, headers=self.headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self.headers["mcp-session-id"] = session_id
        parse_sse_or_json(response.content)
        requests.post(
            self.url,
            headers=self.headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            timeout=self.timeout,
        ).raise_for_status()

    def _id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def call_tool(self, question: str, page: int = 1, size: int = 100, market_range: str = "AG") -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._id(),
            "method": "tools/call",
            "params": {
                "name": TOOL_NAME,
                "arguments": {
                    "question": question,
                    "range": market_range,
                    "page": str(page),
                    "size": str(size),
                },
            },
        }
        message = self._post(payload)
        result = message.get("result", {})
        structured = result.get("structuredContent")
        if structured:
            return structured

        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    return json.loads(item.get("text", "{}"))
                except json.JSONDecodeError:
                    continue
        raise RuntimeError("无法解析 MCP 工具返回")


def parse_sse_or_json(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return [json.loads(stripped)]

    events: list[dict[str, Any]] = []
    data_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "":
            if data_lines:
                events.append(json.loads("\n".join(data_lines)))
                data_lines = []
    if data_lines:
        events.append(json.loads("\n".join(data_lines)))
    return events


def yyyymmdd(value: date) -> str:
    return value.strftime("%Y%m%d")


def dotted_date(value: str) -> str:
    return f"{value[:4]}.{value[4:6]}.{value[6:8]}"


def cn_date(value: str) -> str:
    day = datetime.strptime(value, "%Y%m%d").date()
    return f"{day.year}年{day.month}月{day.day}日"


def parse_date_arg(value: str) -> date:
    value = value.strip().replace("-", "")
    return datetime.strptime(value, "%Y%m%d").date()


def default_start(end_day: date, months: int) -> date:
    return end_day - timedelta(days=months * 31)


def weekday_dates(start_day: date, end_day: date) -> list[date]:
    days: list[date] = []
    current = start_day
    while current <= end_day:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def normalize_rows(trade_date: str, headers: list[str], data: list[list[Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for values in data:
        raw = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
        row = {
            "日期": normalize_trade_date(raw.get("发生日期") or dotted_date(trade_date)),
            "代码": str(raw.get("sec_code", "")).zfill(6),
            "名称": clean_name(raw.get("sec_name", "")),
            "市场": raw.get("market", ""),
            "现价": to_number(raw.get("now_price")),
            "涨幅%": to_number(raw.get("chg")),
            "所属行业": clean_tag_text(raw.get("所属行业", "")),
            "连板数": to_int(first_existing(raw, ["连续涨停天数0#", "连续涨停天数", "几板"])),
            "几天": to_int(raw.get("几天")),
            "几板": to_int(raw.get("几板")),
            "板型": raw.get("板型", ""),
            "首次涨停": raw.get("首次涨停时间", ""),
            "最近涨停": raw.get("最近涨停时间", ""),
            "打开次数": to_int(raw.get("涨停打开次数")),
            "封单金额": to_number(first_existing(raw, ["封单金额", "封单金额0#"])),
            "涨停成交额(万)": to_number(raw.get("涨停成交额(万)")),
            "最大封单额(万)": to_number(raw.get("涨停最大封单额(万)")),
            "封成比": to_number(raw.get("封成比")),
            "题材": clean_tag_text(first_existing(raw, ["短线主题名称", "涨停分析", "涨停原因"])),
            "原因揭秘": normalize_reason(raw.get("原因揭秘", "")),
        }
        if is_st_or_delisting(row["名称"]):
            continue
        if row["连板数"] is None and row["几板"] is not None:
            row["连板数"] = row["几板"]
        if row["连板数"] is None:
            row["连板数"] = 1
        rows.append(row)
    return rows


def first_existing(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def clean_name(value: Any) -> str:
    return str(value or "").replace("XD", "").strip()


def is_st_or_delisting(name: Any) -> bool:
    text = str(name or "").strip().upper().replace(" ", "")
    return "ST" in text or text.startswith("退市") or "退市" in text


def clean_tag_text(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("@", "")
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_reason(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("\r\n", "；").replace("\n", "；")
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_trade_date(value: Any) -> str:
    text = str(value or "").strip()
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return text


def to_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").replace("%", ""))
        if math.isnan(number):
            return None
        return number
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    number = to_number(value)
    if number is None:
        return None
    return int(number)


def fetch_one_day(client: TdxMcpClient, day: date, size: int, retries: int, sleep_sec: float) -> QueryResult:
    trade_date = yyyymmdd(day)
    questions = [
        f"{cn_date(trade_date)}涨停股票",
        f"{cn_date(trade_date)}涨停股票，包含连续涨停天数、几天几板、涨停原因、短线主题名称、所属行业、板型",
        f"{cn_date(trade_date)}连续涨停股票",
    ]
    last_error = ""
    best_empty: QueryResult | None = None
    used_questions: list[str] = []
    for question in questions:
        used_questions.append(question)
        for attempt in range(retries + 1):
            try:
                headers, data, total = fetch_question_pages(client, question, size=size, sleep_sec=sleep_sec)
                rows = normalize_rows(trade_date, headers, data)
                result = QueryResult(
                    trade_date=normalize_trade_date(trade_date),
                    question=" | ".join(used_questions),
                    total=total or len(data) or len(rows),
                    rows=rows,
                    headers=headers,
                )
                if rows:
                    return result
                if best_empty is None or result.total > best_empty.total:
                    best_empty = result
                break
            except Exception as exc:  # noqa: BLE001 - keep batch job running.
                last_error = str(exc)
                if attempt < retries:
                    time.sleep(sleep_sec * (attempt + 1))
        time.sleep(sleep_sec)
    if best_empty is not None:
        best_empty.question = " | ".join(used_questions)
        return best_empty
    return QueryResult(trade_date=normalize_trade_date(trade_date), question=" | ".join(used_questions), total=0, rows=[], headers=[], error=last_error)


def fetch_question_pages(client: TdxMcpClient, question: str, size: int, sleep_sec: float) -> tuple[list[str], list[list[Any]], int]:
    page_size = min(max(size, 1), 100)
    first_payload = client.call_tool(question=question, page=1, size=page_size)
    headers = first_payload.get("headers", [])
    data = list(first_payload.get("data", []))
    meta = first_payload.get("meta", {})
    total = int(meta.get("total") or len(data))
    if total <= len(data) or not data:
        return headers, data, total

    max_pages = min(math.ceil(total / page_size), 20)
    for page in range(2, max_pages + 1):
        time.sleep(sleep_sec)
        payload = client.call_tool(question=question, page=page, size=page_size)
        page_data = payload.get("data", [])
        if not page_data:
            break
        data.extend(page_data)
        if len(data) >= total:
            break
    return headers, data, total


def build_frames(results: list[QueryResult]) -> dict[str, pd.DataFrame]:
    detail_rows = [row for result in results for row in result.rows]
    details = pd.DataFrame(detail_rows)
    if not details.empty:
        details = details.sort_values(["日期", "连板数", "封单金额"], ascending=[True, False, False])

    query_log = pd.DataFrame(
        [
            {
                "日期": result.trade_date,
                "查询总数": result.total,
                "保留涨停梯队": len(result.rows),
                "状态": "失败" if result.error else "成功",
                "错误": result.error,
                "问题": result.question,
                "返回字段": ", ".join(result.headers),
            }
            for result in results
        ]
    )

    overview_daily = make_overview_daily(details, query_log)
    overview = make_overview_matrix(details, overview_daily)
    ladder = make_ladder(details)
    themes = make_themes(details)
    daily_sections = make_daily_sections(details)

    return {
        "复盘总览": overview,
        "纵向总览": overview_daily,
        "每日分层": daily_sections,
        "连板明细": details,
        "题材热度": themes,
        "高度梯队": ladder,
        "取数日志": query_log,
    }


def make_overview_daily(details: pd.DataFrame, query_log: pd.DataFrame) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame(columns=["日期", "涨停家数", "连板家数", "最高连板", "首板", "2板", "3板", "4板", "5板及以上", "核心题材Top3", "高标"])

    rows = []
    for day, group in details.groupby("日期", sort=True):
        themes = split_theme_counts(group)
        leaders = group.sort_values(["连板数", "封单金额"], ascending=[False, False]).head(5)
        rows.append(
            {
                "日期": day,
                "涨停家数": len(group),
                "连板家数": int((group["连板数"] >= 2).sum()),
                "最高连板": int(group["连板数"].max()),
                "首板": int((group["连板数"] == 1).sum()),
                "2板": int((group["连板数"] == 2).sum()),
                "3板": int((group["连板数"] == 3).sum()),
                "4板": int((group["连板数"] == 4).sum()),
                "5板及以上": int((group["连板数"] >= 5).sum()),
                "核心题材Top3": " / ".join([f"{name}({count})" for name, count in themes.most_common(3)]),
                "高标": "、".join([f"{r['名称']}({int(r['连板数'])}板)" for _, r in leaders.iterrows()]),
            }
        )

    overview = pd.DataFrame(rows)
    missing_days = set(query_log.loc[query_log["状态"] == "成功", "日期"]) - set(overview["日期"])
    if missing_days:
        empty_rows = [{"日期": day, "涨停家数": 0, "连板家数": 0, "最高连板": 0, "首板": 0, "2板": 0, "3板": 0, "4板": 0, "5板及以上": 0, "核心题材Top3": "", "高标": ""} for day in missing_days]
        overview = pd.concat([overview, pd.DataFrame(empty_rows)], ignore_index=True)
    return overview.sort_values("日期")


def make_overview_matrix(details: pd.DataFrame, overview_daily: pd.DataFrame) -> pd.DataFrame:
    if overview_daily.empty:
        return pd.DataFrame(columns=["高度"])

    dates = overview_daily.sort_values("日期")["日期"].astype(str).tolist()
    height_rows = [
        ("高标", "10板以上", lambda value: value >= 10),
        ("高标", "9板", lambda value: value == 9),
        ("高标", "8板", lambda value: value == 8),
        ("高标", "7板", lambda value: value == 7),
        ("高标", "6板", lambda value: value == 6),
        ("高标", "5板", lambda value: value == 5),
        ("中位", "4板", lambda value: value == 4),
        ("中位", "3板", lambda value: value == 3),
        ("低位", "2板", lambda value: value == 2),
        ("低位", "首板", lambda value: value == 1),
    ]

    rows: list[dict[str, Any]] = []
    for section, label, predicate in height_rows:
        row = {"分区": section, "高度": label}
        for day in dates:
            day_group = details[details["日期"] == day] if not details.empty else pd.DataFrame()
            targets = day_group[day_group["连板数"].map(lambda value: predicate(int(value or 0)))] if not day_group.empty else pd.DataFrame()
            row[day] = format_height_targets(targets)
        rows.append(row)

    stat_rows = make_overview_stat_rows(overview_daily, dates)
    rows.extend(stat_rows)
    return pd.DataFrame(rows, columns=["分区", "高度", *dates])


def make_overview_stat_rows(overview_daily: pd.DataFrame, dates: list[str]) -> list[dict[str, Any]]:
    daily = overview_daily.sort_values("日期").copy()
    daily["梯队强度"] = daily["2板"] + daily["3板"] * 2 + daily["4板"] * 3 + daily["5板及以上"] * 4
    daily["高度断层"] = daily.apply(describe_ladder_gap, axis=1)
    metrics = [
        ("统计", "涨停家数"),
        ("统计", "连板家数"),
        ("统计", "最高连板"),
        ("统计", "梯队强度"),
        ("结构", "高度断层"),
        ("题材", "核心题材Top3"),
    ]
    rows = []
    for section, metric in metrics:
        row = {"分区": section, "高度": metric}
        for _, item in daily.iterrows():
            row[str(item["日期"])] = item.get(metric, "")
        rows.append(row)
    return rows


def format_height_targets(group: pd.DataFrame) -> str:
    if group.empty:
        return ""
    ordered = group.sort_values(["连板数", "封单金额", "首次涨停"], ascending=[False, False, True])
    values = []
    for _, row in ordered.iterrows():
        theme = str(row.get("题材") or "").split(".")[0]
        suffix = f"({theme})" if theme else ""
        values.append(f"{row['名称']}{suffix}")
    return "\n".join(values)


def describe_ladder_gap(row: pd.Series) -> str:
    highest = int(row.get("最高连板") or 0)
    if highest <= 0:
        return ""
    if highest >= 5 and int(row.get("4板") or 0) == 0:
        return "高位断层"
    if highest >= 4 and int(row.get("3板") or 0) == 0:
        return "中位断层"
    if int(row.get("2板") or 0) == 0:
        return "首板断接"
    return "梯队完整"


def make_ladder(details: pd.DataFrame) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame(columns=["日期", "连板数", "家数", "标的"])
    rows = []
    for (day, streak), group in details.groupby(["日期", "连板数"], sort=True):
        rows.append(
            {
                "日期": day,
                "连板数": int(streak),
                "家数": len(group),
                "标的": "、".join(group.sort_values("封单金额", ascending=False)["名称"].astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows).sort_values(["日期", "连板数"], ascending=[True, False])


def make_themes(details: pd.DataFrame) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame(columns=["日期", "题材", "连板家数", "最高连板", "标的"])
    rows = []
    bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for _, row in details.iterrows():
        for theme in split_themes(row.get("题材")):
            bucket[(row["日期"], theme)].append(row.to_dict())

    for (day, theme), items in bucket.items():
        names = sorted({f"{item['名称']}({int(item['连板数'])}板)" for item in items})
        rows.append(
            {
                "日期": day,
                "题材": theme,
                "连板家数": len({item["代码"] for item in items}),
                "最高连板": max(int(item["连板数"]) for item in items),
                "标的": "、".join(names),
            }
        )
    return pd.DataFrame(rows).sort_values(["日期", "连板家数", "最高连板"], ascending=[True, False, False])


def make_daily_sections(details: pd.DataFrame) -> pd.DataFrame:
    columns = ["日期", "梯队", "代码", "名称", "题材", "所属行业", "板型", "首次涨停", "打开次数", "原因揭秘"]
    if details.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for day, day_group in details.groupby("日期", sort=True):
        for streak, group in day_group.groupby("连板数", sort=False):
            ordered = group.sort_values(["封单金额", "首次涨停"], ascending=[False, True])
            for _, row in ordered.iterrows():
                rows.append(
                    {
                        "日期": day,
                        "梯队": f"{int(streak)}板",
                        "代码": row["代码"],
                        "名称": row["名称"],
                        "题材": row["题材"],
                        "所属行业": row["所属行业"],
                        "板型": row["板型"],
                        "首次涨停": row["首次涨停"],
                        "打开次数": row["打开次数"],
                        "原因揭秘": row["原因揭秘"],
                    }
                )
    return pd.DataFrame(rows, columns=columns)


def split_theme_counts(group: pd.DataFrame) -> Counter[str]:
    counter: Counter[str] = Counter()
    for value in group["题材"].tolist():
        counter.update(split_themes(value))
    return counter


def split_themes(value: Any) -> list[str]:
    text = clean_tag_text(value)
    if not text:
        return []
    parts = re.split(r"[.、,，/;；]+", text)
    return [part.strip() for part in parts if part.strip() and part.strip() not in {"非周期股", "周期股"}]


def write_excel(frames: dict[str, pd.DataFrame], output_path: Path) -> None:
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        for sheet_name, frame in frames.items():
            safe_frame = frame.copy()
            safe_frame.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        formats = build_formats(workbook)
        for sheet_name, frame in frames.items():
            worksheet = writer.sheets[sheet_name]
            style_sheet(worksheet, frame, formats, sheet_name)

        add_overview_chart(workbook, writer.sheets.get("复盘总览"), frames.get("复盘总览", pd.DataFrame()))
        add_theme_chart(workbook, writer.sheets.get("题材热度"), frames.get("题材热度", pd.DataFrame()))


def build_formats(workbook: Any) -> dict[str, Any]:
    return {
        "header": workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78", "align": "center", "valign": "vcenter", "border": 1}),
        "wrap": workbook.add_format({"text_wrap": True, "valign": "top"}),
        "date": workbook.add_format({"num_format": "yyyy-mm-dd", "align": "center"}),
        "integer": workbook.add_format({"num_format": "0", "align": "center"}),
        "money": workbook.add_format({"num_format": "#,##0.00"}),
        "error": workbook.add_format({"font_color": "#C00000", "bold": True}),
        "section": workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#595959", "align": "center", "valign": "vcenter", "border": 1}),
        "metric": workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "align": "center", "valign": "vcenter", "border": 1}),
    }


def style_sheet(worksheet: Any, frame: pd.DataFrame, formats: dict[str, Any], sheet_name: str) -> None:
    if sheet_name == "复盘总览":
        style_overview_matrix(worksheet, frame, formats)
        return

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, max(len(frame), 1), max(len(frame.columns) - 1, 0))
    worksheet.set_row(0, 24, formats["header"])

    for idx, column in enumerate(frame.columns):
        series = frame[column] if not frame.empty else pd.Series(dtype=object)
        lengths = series.head(200).map(lambda value: len(str(value))).tolist()
        max_len = max([len(str(column)), *(lengths or [0])])
        width = min(max(max_len + 2, 10), 42)
        fmt = formats["wrap"] if column in {"原因揭秘", "题材", "高标", "核心题材Top3", "标的", "问题", "返回字段", "错误"} else None
        worksheet.set_column(idx, idx, width, fmt)

    if frame.empty:
        return

    columns = {name: i for i, name in enumerate(frame.columns)}
    last_row = len(frame)
    if "连板数" in columns:
        col = columns["连板数"]
        worksheet.conditional_format(1, col, last_row, col, {"type": "3_color_scale", "min_color": "#D9EAF7", "mid_color": "#FCE4D6", "max_color": "#C00000"})
    if "最高连板" in columns:
        col = columns["最高连板"]
        worksheet.conditional_format(1, col, last_row, col, {"type": "3_color_scale", "min_color": "#D9EAD3", "mid_color": "#FFE699", "max_color": "#C00000"})
    if "连板家数" in columns:
        col = columns["连板家数"]
        worksheet.conditional_format(1, col, last_row, col, {"type": "data_bar", "bar_color": "#5B9BD5"})
    if "状态" in columns:
        col = columns["状态"]
        worksheet.conditional_format(1, col, last_row, col, {"type": "text", "criteria": "containing", "value": "失败", "format": formats["error"]})


def style_overview_matrix(worksheet: Any, frame: pd.DataFrame, formats: dict[str, Any]) -> None:
    worksheet.freeze_panes(1, 2)
    worksheet.hide_gridlines(2)
    worksheet.set_row(0, 24, formats["header"])
    worksheet.set_column(0, 0, 10, formats["section"])
    worksheet.set_column(1, 1, 12, formats["metric"])

    if frame.empty:
        return

    last_row = len(frame)
    last_col = len(frame.columns) - 1
    worksheet.autofilter(0, 0, last_row, last_col)
    if last_col >= 2:
        worksheet.set_column(2, last_col, 20, formats["wrap"])

    numeric_metrics = {"涨停家数", "连板家数", "最高连板", "梯队强度"}
    height_metrics = {"10板以上", "9板", "8板", "7板", "6板", "5板", "4板", "3板", "2板", "首板"}
    text_metrics = {"高度断层", "核心题材Top3", *height_metrics}
    for index, row in frame.iterrows():
        excel_row = index + 1
        metric = row.get("高度")
        if metric in height_metrics:
            worksheet.set_row(excel_row, 62, formats["wrap"])
        if metric in numeric_metrics and last_col >= 2:
            worksheet.conditional_format(
                excel_row,
                2,
                excel_row,
                last_col,
                {"type": "3_color_scale", "min_color": "#E2F0D9", "mid_color": "#FFE699", "max_color": "#C00000"},
            )
        if metric in text_metrics and last_col >= 2:
            worksheet.set_row(excel_row, 42, formats["wrap"])

    worksheet.conditional_format(
        1,
        0,
        last_row,
        0,
        {"type": "no_blanks", "format": formats["section"]},
    )
    worksheet.conditional_format(
        1,
        1,
        last_row,
        1,
        {"type": "no_blanks", "format": formats["metric"]},
    )


def add_overview_chart(workbook: Any, worksheet: Any, overview: pd.DataFrame) -> None:
    if worksheet is None or overview.empty or len(overview.columns) <= 2:
        return
    metric_rows = {row["高度"]: index + 1 for index, row in overview.iterrows()}
    first_date_col = 2
    last_date_col = len(overview.columns) - 1
    chart = workbook.add_chart({"type": "line"})
    categories = ["复盘总览", 0, first_date_col, 0, last_date_col]
    series_config = [
        ("涨停家数", "#A5A5A5"),
        ("连板家数", "#4472C4"),
        ("最高连板", "#C00000"),
        ("梯队强度", "#70AD47"),
    ]
    for name, color in series_config:
        row = metric_rows.get(name)
        if row is None:
            continue
        chart.add_series(
            {
                "name": ["复盘总览", row, 1],
                "categories": categories,
                "values": ["复盘总览", row, first_date_col, row, last_date_col],
                "line": {"color": color, "width": 2.0},
            }
        )
    chart.set_title({"name": "连板高度与梯队强度横向趋势"})
    chart.set_legend({"position": "bottom"})
    chart.set_size({"width": 980, "height": 360})
    worksheet.insert_chart("A14", chart)


def add_theme_chart(workbook: Any, worksheet: Any, themes: pd.DataFrame) -> None:
    if worksheet is None or themes.empty:
        return
    latest_day = themes["日期"].max()
    latest = themes[themes["日期"] == latest_day].head(10).copy()
    if latest.empty:
        return

    start_row = len(themes) + 3
    worksheet.write(start_row, 0, f"{latest_day} 题材热度Top10")
    for i, (_, row) in enumerate(latest.iterrows(), start=start_row + 1):
        worksheet.write(i, 0, row["题材"])
        worksheet.write(i, 1, row["连板家数"])

    chart = workbook.add_chart({"type": "bar"})
    chart.add_series({"name": "连板家数", "categories": ["题材热度", start_row + 1, 0, start_row + len(latest), 0], "values": ["题材热度", start_row + 1, 1, start_row + len(latest), 1], "fill": {"color": "#70AD47"}})
    chart.set_title({"name": f"{latest_day} 题材热度Top10"})
    chart.set_legend({"none": True})
    chart.set_size({"width": 720, "height": 320})
    worksheet.insert_chart("G2", chart)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过通达信 MCP 抓取连板复盘数据并导出 Excel")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Codex config.toml 路径")
    parser.add_argument("--server", default="-mcp", help="MCP server 名称，默认读取 [mcp_servers.-mcp]")
    parser.add_argument("--start", help="开始日期，YYYYMMDD 或 YYYY-MM-DD")
    parser.add_argument("--end", help="结束日期，YYYYMMDD 或 YYYY-MM-DD，默认今天")
    parser.add_argument("--months", type=int, default=3, help="未指定 --start 时向前抓取几个月，默认 3")
    parser.add_argument("--output", default="", help="输出 Excel 路径")
    parser.add_argument("--size", type=int, default=100, help="单日最大返回条数，默认 100")
    parser.add_argument("--sleep", type=float, default=0.35, help="每次请求间隔秒数，默认 0.35")
    parser.add_argument("--retries", type=int, default=2, help="单日失败重试次数，默认 2")
    parser.add_argument("--limit-days", type=int, default=0, help="调试用：只抓取最近 N 个工作日")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    end_day = parse_date_arg(args.end) if args.end else date.today()
    start_day = parse_date_arg(args.start) if args.start else default_start(end_day, args.months)
    if start_day > end_day:
        raise ValueError("--start 不能晚于 --end")

    days = weekday_dates(start_day, end_day)
    if args.limit_days:
        days = days[-args.limit_days :]
    if not days:
        raise ValueError("日期范围内没有工作日")

    output = Path(args.output) if args.output else Path.cwd() / f"通达信连板复盘_{yyyymmdd(days[0])}_{yyyymmdd(days[-1])}.xlsx"
    print(f"准备抓取 {len(days)} 个工作日：{days[0]} 至 {days[-1]}")
    print(f"输出文件：{output}")

    client = TdxMcpClient(config_path=Path(args.config), server_name=args.server)
    results: list[QueryResult] = []
    for index, day in enumerate(days, start=1):
        result = fetch_one_day(client, day, size=args.size, retries=args.retries, sleep_sec=args.sleep)
        results.append(result)
        status = "失败" if result.error else f"{len(result.rows)} 条涨停梯队"
        print(f"[{index:>3}/{len(days)}] {day}: {status}")
        time.sleep(args.sleep)

    frames = build_frames(results)
    write_excel(frames, output)

    details = frames["连板明细"]
    failures = frames["取数日志"][frames["取数日志"]["状态"] == "失败"]
    print(f"完成：明细 {len(details)} 行，失败日期 {len(failures)} 个")
    print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        raise SystemExit(130)
