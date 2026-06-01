from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "investment_calendar.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"

SOURCE_URLS = {
    "财联社": "https://www.cls.cn/investkalendar",
    "同花顺": "https://stock.10jqka.com.cn/fincalendar.shtml",
    "东方财富财经日历": "https://data.eastmoney.com/dcrl/",
    "东方财富个股日历": "https://data.eastmoney.com/gsrl/default.html",
}

IMPACT_RANK = {"watch": 0, "medium": 1, "high": 2}


@dataclass
class CalendarEvent:
    date: str
    title: str
    detail: str
    category: str
    market: str
    impact: str
    source: str
    source_url: str = ""
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "title": self.title,
            "detail": self.detail,
            "category": self.category,
            "market": self.market,
            "impact": self.impact,
            "source": self.source,
            "source_url": self.source_url,
            "tags": self.tags,
        }


def fetch_investment_calendar(days: int = 30, force_refresh: bool = False) -> dict[str, object]:
    days = max(7, min(days, 60))
    start = date.today()
    end = start + timedelta(days=days)
    ttl = int(os.getenv("INVESTMENT_CALENDAR_CACHE_SECONDS", "1800"))

    if not force_refresh and CACHE_PATH.exists() and time.time() - CACHE_PATH.stat().st_mtime < ttl:
        try:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if cached.get("start_date") == _date_key(start) and cached.get("end_date") == _date_key(end):
                return cached
        except Exception:
            pass

    events: list[CalendarEvent] = []
    warnings: list[str] = []
    source_status: dict[str, dict[str, object]] = {}

    for source_name, fetcher in [
        ("财联社", _fetch_cls_events),
        ("同花顺", _fetch_ths_events),
        ("东方财富财经日历", _fetch_eastmoney_finance_events),
        ("东方财富个股日历", _fetch_eastmoney_stock_summary),
        ("东方财富大事提醒", _fetch_eastmoney_dcrl_events),
    ]:
        try:
            rows = fetcher(start, end)
            events.extend(rows)
            source_status[source_name] = {"ok": True, "count": len(rows), "message": ""}
        except Exception as exc:  # noqa: BLE001
            message = f"{source_name} 获取失败：{exc}"
            warnings.append(message)
            source_status[source_name] = {"ok": False, "count": 0, "message": str(exc)}

    deduped = _dedupe_events(_in_range(events, start, end))
    events_by_day = _cap_events_per_day(deduped, int(os.getenv("INVESTMENT_CALENDAR_MAX_PER_DAY", "90")))
    source_names = [name for name, status in source_status.items() if status["ok"] and int(status["count"]) > 0]

    payload = {
        "source": " + ".join(source_names) if source_names else "fallback",
        "source_status": source_status,
        "start_date": _date_key(start),
        "end_date": _date_key(end),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "event_count": len(events_by_day),
        "events": [event.as_dict() for event in events_by_day],
        "warnings": warnings,
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _fetch_cls_events(start: date, end: date) -> list[CalendarEvent]:
    url = "https://www.cls.cn/api/calendar/web/list?" + urllib.parse.urlencode({"flag": 0, "type": 0})
    payload = _request_json(url, referer=SOURCE_URLS["财联社"])
    if payload.get("code") != 200:
        raise RuntimeError(payload.get("msg") or "接口返回异常")

    events: list[CalendarEvent] = []
    for day in payload.get("data") or []:
        event_date = _parse_date(day.get("calendar_day"))
        if event_date is None or not start <= event_date <= end:
            continue
        for item in day.get("items") or []:
            title = _clean_text(item.get("title") or item.get("event", {}).get("title"))
            if not title:
                continue
            event_info = item.get("event") or {}
            economic = item.get("economic") or {}
            country = event_info.get("country") or economic.get("country") or "中国"
            star = _safe_int(event_info.get("star") or economic.get("star"), 0)
            detail_parts = []
            if country:
                detail_parts.append(f"地区：{country}")
            if economic:
                detail_parts.append(
                    "公布值/预测/前值："
                    f"{economic.get('fix') or '-'} / {economic.get('predict') or '-'} / {economic.get('before') or '-'}"
                )
            events.append(
                CalendarEvent(
                    date=_date_key(event_date),
                    title=title,
                    detail="；".join(detail_parts) or title,
                    category=_category_from_title(title, item_type=item.get("type")),
                    market=_market_from_title(title, country),
                    impact="high" if star >= 5 else _impact_from_title(title),
                    source="财联社",
                    source_url=SOURCE_URLS["财联社"],
                    tags=[country] if country else [],
                )
            )
    return events


def _fetch_ths_events(start: date, end: date) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    for month in _month_keys(start, end):
        url = "http://comment.10jqka.com.cn/tzrl/getTzrlData.php?" + urllib.parse.urlencode(
            {"type": "data", "date": month, "callback": "callback"}
        )
        payload = _request_jsonp(url, encoding="gbk", referer=SOURCE_URLS["同花顺"])
        if payload.get("stat") != "ok":
            continue
        for day in payload.get("data") or []:
            event_date = _parse_date(day.get("date"))
            if event_date is None or not start <= event_date <= end:
                continue
            concepts = day.get("concept") or []
            fields = day.get("field") or []
            stocks = day.get("stocks") or []
            for index, row in enumerate(day.get("events") or []):
                title = _clean_text(row[0] if isinstance(row, list) and row else row)
                if not title:
                    continue
                tags = _tag_names(_list_at(concepts, index)) + _tag_names(_list_at(fields, index)) + _tag_names(_list_at(stocks, index))
                detail = f"关联：{'、'.join(tags[:8])}" if tags else title
                events.append(
                    CalendarEvent(
                        date=_date_key(event_date),
                        title=title,
                        detail=detail,
                        category=_category_from_title(title),
                        market="A股 / 产业",
                        impact=_impact_from_title(title),
                        source="同花顺",
                        source_url=SOURCE_URLS["同花顺"],
                        tags=tags[:12],
                    )
                )
    return events


def _fetch_eastmoney_finance_events(start: date, end: date) -> list[CalendarEvent]:
    params = {
        "reportName": "RPT_CPH_FECALENDAR",
        "pageNumber": "1",
        "pageSize": "1000",
        "sortColumns": "START_DATE",
        "sortTypes": "1",
        "filter": f"(END_DATE>='{_date_key(start)}')(START_DATE<='{_date_key(end)}')",
        "source": "WEB",
        "client": "WEB",
        "columns": "START_DATE,END_DATE,FE_CODE,FE_NAME,FE_TYPE,CONTENT,STD_TYPE_CODE,SPONSOR_NAME,CITY",
    }
    payload = _request_json(
        "https://datacenter-web.eastmoney.com/api/data/v1/get?" + urllib.parse.urlencode(params),
        referer=SOURCE_URLS["东方财富财经日历"],
    )
    rows = ((payload.get("result") or {}).get("data") or []) if payload.get("success") is not False else []
    events: list[CalendarEvent] = []
    for row in rows:
        start_date = _parse_date(row.get("START_DATE"))
        end_date = _parse_date(row.get("END_DATE")) or start_date
        if start_date is None or end_date is None or end_date < start or start_date > end:
            continue
        event_date = max(start, start_date)
        title = _clean_text(row.get("FE_NAME"))
        if not title:
            continue
        category = _clean_text(row.get("FE_TYPE")) or _category_from_title(title)
        city = _clean_text(row.get("CITY"))
        sponsor = _clean_text(row.get("SPONSOR_NAME"))
        content = _clean_text(row.get("CONTENT")) or title
        detail = content if not sponsor else f"{content} 主办/发布：{sponsor}"
        events.append(
            CalendarEvent(
                date=_date_key(event_date),
                title=title,
                detail=detail,
                category=category,
                market=city or _market_from_title(title, "全球"),
                impact=_impact_from_title(title),
                source="东方财富财经日历",
                source_url=SOURCE_URLS["东方财富财经日历"],
                tags=[tag for tag in [category, city, sponsor] if tag],
            )
        )
    return events


def _fetch_eastmoney_stock_summary(start: date, end: date) -> list[CalendarEvent]:
    params = {
        "reportName": "RPT_SPECIAL_ALL",
        "columns": "SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,EVENT_TYPE,EVENT_CONTENT,TRADE_DATE",
        "filter": f"(TRADE_DATE>='{_date_key(start)}')(TRADE_DATE<='{_date_key(end)}')",
        "pageNumber": "1",
        "pageSize": "5000",
        "source": "WEB",
        "client": "WEB",
        "sortColumns": "TRADE_DATE,EVENT_CODE,SECURITY_CODE",
        "sortTypes": "1,1,1",
    }
    payload = _request_json(
        "https://datacenter-web.eastmoney.com/api/data/v1/get?" + urllib.parse.urlencode(params),
        referer=SOURCE_URLS["东方财富个股日历"],
    )
    rows = (payload.get("result") or {}).get("data") or []
    grouped: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        event_date = _parse_date(row.get("TRADE_DATE"))
        if event_date is None or not start <= event_date <= end:
            continue
        event_type = _clean_text(row.get("EVENT_TYPE")) or "个股事件"
        name = _clean_text(row.get("SECURITY_NAME_ABBR")) or _clean_text(row.get("SECURITY_CODE"))
        grouped.setdefault(_date_key(event_date), {}).setdefault(event_type, [])
        if name and len(grouped[_date_key(event_date)][event_type]) < 8:
            grouped[_date_key(event_date)][event_type].append(name)

    events: list[CalendarEvent] = []
    for day, types in grouped.items():
        sorted_types = sorted(types.items(), key=lambda item: len(item[1]), reverse=True)
        total = sum(len(values) for values in types.values())
        lead = "、".join(f"{event_type}{len(values)}项" for event_type, values in sorted_types[:6])
        examples = "；".join(f"{event_type}：{'、'.join(names[:5])}" for event_type, names in sorted_types[:4] if names)
        events.append(
            CalendarEvent(
                date=day,
                title=f"东方财富个股日历：{lead}",
                detail=examples or f"当日共 {total} 项个股事件。",
                category="个股日历",
                market="A股",
                impact="medium" if any(_important_stock_type(name) for name in types) else "watch",
                source="东方财富个股日历",
                source_url=SOURCE_URLS["东方财富个股日历"],
                tags=[event_type for event_type, _ in sorted_types[:8]],
            )
        )
    return events


def _fetch_eastmoney_dcrl_events(start: date, end: date) -> list[CalendarEvent]:
    url = "https://data.eastmoney.com/dataapi/dcrl/dstx?" + urllib.parse.urlencode(
        {"fromdate": _date_key(start), "todate": _date_key(end)}
    )
    payload = _request_json(url, referer=SOURCE_URLS["东方财富财经日历"])
    events: list[CalendarEvent] = []

    for row in payload.get("xsap") or []:
        event_date = _parse_date(row.get("SDATE"))
        if event_date is None or not start <= event_date <= end:
            continue
        market = _clean_text(row.get("MKT")) or "市场"
        holiday = _clean_text(row.get("HOLIDAY")) or "休市安排"
        events.append(
            CalendarEvent(
                date=_date_key(event_date),
                title=f"{market}：{holiday}休市/安排",
                detail=f"{market} {holiday}，请关注跨市场交易与资金清算安排。",
                category="休市安排",
                market=market,
                impact="medium",
                source="东方财富大事提醒",
                source_url=SOURCE_URLS["东方财富财经日历"],
                tags=[market, holiday],
            )
        )

    for row in payload.get("xgsg") or []:
        event_date = _parse_date(row.get("Date"))
        if event_date is None or not start <= event_date <= end:
            continue
        data = row.get("Data") or {}
        for key, label in [("xg", "新股申购"), ("kzz", "可转债申购")]:
            names = [_clean_text(item.get("Sname")) for item in data.get(key) or []]
            names = [name for name in names if name]
            if names:
                events.append(
                    CalendarEvent(
                        date=_date_key(event_date),
                        title=f"{label}：{'、'.join(names[:8])}",
                        detail=f"东方财富新股/转债日历收录 {len(names)} 项：{'、'.join(names[:12])}",
                        category=label,
                        market="A股",
                        impact="high" if key == "xg" else "medium",
                        source="东方财富大事提醒",
                        source_url=SOURCE_URLS["东方财富财经日历"],
                        tags=names[:12],
                    )
                )

    for key, label in [("tfpxx", "停复牌"), ("hsgg", "沪深公告"), ("nbjb", "定期报告"), ("hyhy", "行业会议"), ("gddh", "股东大会")]:
        for event in _generic_eastmoney_events(payload.get(key) or [], label, start, end):
            events.append(event)
    return events


def _generic_eastmoney_events(rows: list[Any], label: str, start: date, end: date) -> list[CalendarEvent]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        event_date = _parse_date(row.get("Date") or row.get("SDATE") or row.get("TRADE_DATE") or row.get("date"))
        if event_date is None or not start <= event_date <= end:
            continue
        names = _extract_names(row.get("Data"))
        if not names:
            names = _extract_names(row)
        grouped.setdefault(_date_key(event_date), []).extend(names)

    events = []
    for day, values in grouped.items():
        names = _unique([_clean_text(value) for value in values if value])[:20]
        if not names:
            continue
        events.append(
            CalendarEvent(
                date=day,
                title=f"{label}：{'、'.join(names[:6])}",
                detail=f"东方财富大事提醒收录 {len(names)} 项{label}事件：{'、'.join(names[:14])}",
                category=label,
                market="A股",
                impact="medium" if label in {"行业会议", "沪深公告", "定期报告"} else "watch",
                source="东方财富大事提醒",
                source_url=SOURCE_URLS["东方财富财经日历"],
                tags=names[:12],
            )
        )
    return events


def _request_json(url: str, *, referer: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Referer": referer, "Accept": "application/json,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _request_jsonp(url: str, *, encoding: str, referer: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": referer})
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode(encoding, errors="replace")
    match = re.search(r"^[^(]*\((.*)\)\s*;?$", text, re.S)
    if not match:
        raise RuntimeError("JSONP 格式异常")
    return json.loads(match.group(1))


def _dedupe_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    merged: list[CalendarEvent] = []
    for event in sorted(events, key=lambda item: (item.date, -IMPACT_RANK.get(item.impact, 0), item.title)):
        current = next(
            (
                row
                for row in merged
                if row.date == event.date and _is_duplicate_title(row.title, event.title)
            ),
            None,
        )
        if current is None:
            merged.append(event)
            continue
        current_sources = _unique([source.strip() for source in current.source.split(" / ") if source.strip()])
        event_sources = _unique([source.strip() for source in event.source.split(" / ") if source.strip()])
        current.source = " / ".join(_unique(current_sources + event_sources))
        current.tags = _unique(current.tags + event.tags)[:16]
        if IMPACT_RANK.get(event.impact, 0) > IMPACT_RANK.get(current.impact, 0):
            current.impact = event.impact
        if len(event.detail) > len(current.detail):
            current.detail = event.detail
        if not current.source_url and event.source_url:
            current.source_url = event.source_url
    return sorted(merged, key=lambda item: (item.date, -IMPACT_RANK.get(item.impact, 0), item.category, item.title))


def _cap_events_per_day(events: list[CalendarEvent], max_per_day: int) -> list[CalendarEvent]:
    if max_per_day <= 0:
        return events
    by_day: dict[str, list[CalendarEvent]] = {}
    for event in events:
        by_day.setdefault(event.date, []).append(event)

    capped: list[CalendarEvent] = []
    for day in sorted(by_day):
        day_events = by_day[day]
        keep = day_events[:max_per_day]
        overflow = day_events[max_per_day:]
        capped.extend(keep)
        if overflow:
            categories: dict[str, int] = {}
            for event in overflow:
                categories[event.category] = categories.get(event.category, 0) + 1
            detail = "；".join(f"{name}{count}项" for name, count in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:8])
            capped.append(
                CalendarEvent(
                    date=day,
                    title=f"更多低优先级事件 {len(overflow)} 项",
                    detail=detail,
                    category="事件汇总",
                    market="A股 / 全球",
                    impact="watch",
                    source="系统汇总",
                    tags=list(categories)[:8],
                )
            )
    return capped


def _in_range(events: list[CalendarEvent], start: date, end: date) -> list[CalendarEvent]:
    return [event for event in events if (parsed := _parse_date(event.date)) is not None and start <= parsed <= end]


def _month_keys(start: date, end: date) -> list[str]:
    keys = []
    current = start.replace(day=1)
    while current <= end:
        keys.append(current.strftime("%Y%m"))
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = current.replace(year=year, month=month)
    return keys


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:19] if " " in fmt else text[:10] if "-" in fmt else text[:8], fmt).date()
        except ValueError:
            continue
    return None


def _date_key(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u3000", " ")).strip()


def _dedupe_key(value: str) -> str:
    text = re.sub(r"[，。、《》：:；;（）()\[\]\s\"'“”‘’_\-—]+", "", value.lower())
    return text[:80]


def _semantic_title_key(value: str) -> str:
    text = _dedupe_key(value)
    text = re.sub(r"将于\d{1,2}月\d{1,2}日(?:至\d{1,2}日)?(?:举办|举行|召开|开幕|启动)", "", text)
    text = re.sub(r"定于\d{1,2}月\d{1,2}(?:至\d{1,2})?日(?:举办|举行|召开)", "", text)
    text = re.sub(r"于\d{1,2}月\d{1,2}日(?:至\d{1,2}日)?(?:举办|举行|召开|开幕|启动)", "", text)
    text = re.sub(r"自\d{1,2}月\d{1,2}日起", "", text)
    text = text.replace("同传", "")
    return text[:80]


def _is_duplicate_title(left: str, right: str) -> bool:
    left_key = _semantic_title_key(left)
    right_key = _semantic_title_key(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True
    short, long = sorted([left_key, right_key], key=len)
    return len(short) >= 10 and short in long


def _category_from_title(title: str, item_type: Any = None) -> str:
    if item_type == 1:
        return "宏观数据"
    if item_type == 2:
        return "事件"
    if any(word in title for word in ["FOMC", "美联储", "央行", "利率", "LPR", "逆回购"]):
        return "央行/利率"
    if any(word in title for word in ["CPI", "PPI", "PCE", "PMI", "非农", "GDP", "就业", "零售销售", "经济数据"]):
        return "宏观数据"
    if any(word in title for word in ["IPO", "上市", "上会", "申购", "中签"]):
        return "IPO/新股"
    if any(word in title for word in ["业绩", "财报", "年报", "季报"]):
        return "公司业绩"
    if any(word in title for word in ["AI", "人工智能", "英伟达", "算力", "机器人", "华为", "苹果", "微软", "Computex", "GTC", "WWDC", "Build"]):
        return "科技产业"
    if any(word in title for word in ["光伏", "储能", "电池", "新能源"]):
        return "新能源"
    if any(word in title for word in ["半导体", "芯片", "封装", "电子特气"]):
        return "半导体"
    if any(word in title for word in ["大会", "会议", "论坛", "展览", "博览会"]):
        return "产业会议"
    if any(word in title for word in ["休市", "假期"]):
        return "休市安排"
    return "市场事件"


def _impact_from_title(title: str) -> str:
    high_words = [
        "FOMC",
        "美联储",
        "CPI",
        "PCE",
        "非农",
        "GDP",
        "PMI",
        "LPR",
        "利率决议",
        "英伟达",
        "苹果",
        "华为",
        "微软",
        "GTC",
        "Computex",
        "WWDC",
        "IPO",
        "上会",
        "业绩",
    ]
    if any(word.lower() in title.lower() for word in high_words):
        return "high"
    if any(word in title for word in ["大会", "会议", "论坛", "展览", "博览会", "申购", "休市", "政策", "发布会"]):
        return "medium"
    return "watch"


def _market_from_title(title: str, fallback: str) -> str:
    if any(word in title for word in ["美联储", "美国", "英伟达", "微软", "苹果", "WWDC", "GTC"]):
        return "全球 / 美股"
    if any(word in title for word in ["港股", "美团"]):
        return "港股"
    if any(word in title for word in ["A股", "科创板", "IPO", "上会", "申购"]):
        return "A股"
    return fallback or "全球"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list_at(rows: Any, index: int) -> Any:
    return rows[index] if isinstance(rows, list) and index < len(rows) else []


def _tag_names(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        return []
    names = []
    for row in rows:
        if isinstance(row, dict):
            name = _clean_text(row.get("name") or row.get("Sname") or row.get("SECURITY_NAME_ABBR"))
            if name:
                names.append(name)
    return _unique(names)


def _extract_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            names.extend(_extract_names(item))
        for key in ["Sname", "SECURITY_NAME_ABBR", "name", "TITLE", "EVENT_TYPE"]:
            text = _clean_text(value.get(key))
            if text:
                names.append(text)
    elif isinstance(value, list):
        for item in value:
            names.extend(_extract_names(item))
    elif isinstance(value, str):
        names.append(value)
    return names


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = _dedupe_key(value)
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _important_stock_type(name: str) -> bool:
    return any(word in name for word in ["业绩", "增发", "上市", "申购", "股权登记", "停牌", "复牌", "特别处理"])
