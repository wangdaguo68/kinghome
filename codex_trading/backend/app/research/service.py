from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.research.store import (
    ResearchItem,
    create_crawl_run,
    database_available,
    finish_crawl_run,
    upsert_research_items,
    upsert_source,
)


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
EASTMONEY_REPORT_URL = "https://reportapi.eastmoney.com/report/list"
EASTMONEY_REFERER = "https://data.eastmoney.com/report/"
LOCAL_SOURCE_NAME = "本地授权文件"

REPORT_TYPE_MAP = {
    "0": "个股拆解",
    "1": "产业报告",
    "2": "个股拆解",
    "3": "产业报告",
    "4": "策略报告",
    "5": "宏观研究",
    "6": "券商晨会",
    "7": "财务模型",
}


def sync_industry_research(force: bool = False) -> dict[str, Any]:
    if not force and not _sync_enabled():
        return {"status": "disabled", "seen_count": 0, "inserted_count": 0, "sources": [], "errors": []}
    if not database_available():
        return {"status": "error", "seen_count": 0, "inserted_count": 0, "sources": [], "errors": ["MySQL 未连接，产业研报无法入库。"]}

    started_at = datetime.now()
    total_seen = 0
    total_inserted = 0
    errors: list[str] = []
    sources: list[dict[str, Any]] = []

    for source in _configured_sources():
        run_id = create_crawl_run(source["name"])
        seen_count = 0
        inserted_count = 0
        error = ""
        try:
            items = _fetch_source(source)
            result = upsert_research_items(items)
            seen_count = int(result["seen_count"])
            inserted_count = int(result["inserted_count"])
            upsert_source(source["name"], source["source_type"], source.get("url", ""), "ok", "", source)
            finish_crawl_run(run_id, "ok", inserted_count, seen_count)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            errors.append(f"{source['name']}: {error}")
            upsert_source(source["name"], source["source_type"], source.get("url", ""), "error", error, source)
            finish_crawl_run(run_id, "error", inserted_count, seen_count, error)
        total_seen += seen_count
        total_inserted += inserted_count
        sources.append({"name": source["name"], "seen_count": seen_count, "inserted_count": inserted_count, "error": error})

    return {
        "status": "ok" if not errors else "partial",
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "seen_count": total_seen,
        "inserted_count": total_inserted,
        "sources": sources,
        "errors": errors,
    }


def should_run_daily_sync(last_run_day: str | None) -> bool:
    if not _sync_enabled():
        return False
    now = datetime.now()
    hour = int(os.getenv("INDUSTRY_RESEARCH_SYNC_HOUR", "7"))
    return now.hour >= hour and last_run_day != now.strftime("%Y-%m-%d")


def _configured_sources() -> list[dict[str, Any]]:
    sources = _default_sources()
    custom = os.getenv("INDUSTRY_RESEARCH_SOURCES_JSON", "").strip()
    if custom:
        try:
            payload = json.loads(custom)
            if isinstance(payload, list):
                sources.extend(item for item in payload if isinstance(item, dict) and item.get("name"))
        except Exception:
            pass
    import_dir = os.getenv("INDUSTRY_RESEARCH_IMPORT_DIR", "").strip()
    if import_dir:
        sources.append({"name": LOCAL_SOURCE_NAME, "source_type": "用户授权文件", "kind": "local_files", "url": import_dir})
    return [source for source in sources if str(source.get("enabled", "1")).lower() not in {"0", "false", "no", "off"}]


def _default_sources() -> list[dict[str, Any]]:
    days = int(os.getenv("INDUSTRY_RESEARCH_EASTMONEY_DAYS", "14"))
    page_size = min(100, max(10, int(os.getenv("INDUSTRY_RESEARCH_EASTMONEY_PAGE_SIZE", "50"))))
    max_pages = min(20, max(1, int(os.getenv("INDUSTRY_RESEARCH_EASTMONEY_MAX_PAGES", "4"))))
    return [
        {
            "name": "东方财富研报中心-个股研报",
            "source_type": "公开来源",
            "kind": "eastmoney_reports",
            "url": "https://data.eastmoney.com/report/stock.jshtml",
            "q_type": "0",
            "report_type": "个股拆解",
            "days": days,
            "page_size": page_size,
            "max_pages": max_pages,
        },
        {
            "name": "东方财富研报中心-行业研报",
            "source_type": "公开来源",
            "kind": "eastmoney_reports",
            "url": "https://data.eastmoney.com/report/industry.jshtml",
            "q_type": "1",
            "report_type": "产业报告",
            "days": days,
            "page_size": page_size,
            "max_pages": max_pages,
        },
    ]


def _fetch_source(source: dict[str, Any]) -> list[ResearchItem]:
    kind = source.get("kind") or source.get("parser") or "html"
    if kind == "eastmoney_reports":
        return _fetch_eastmoney_reports(source)
    if kind == "rss":
        return _fetch_rss_source(source)
    if kind == "json":
        return _fetch_json_source(source)
    if kind == "local_files":
        return _fetch_local_files(source)
    return _fetch_html_source(source)


def _fetch_eastmoney_reports(source: dict[str, Any]) -> list[ResearchItem]:
    end = date.today()
    start = end - timedelta(days=max(1, int(source.get("days", 14))))
    page_size = min(100, max(10, int(source.get("page_size", 50))))
    max_pages = min(30, max(1, int(source.get("max_pages", 4))))
    q_type = str(source.get("q_type", "1"))
    items: list[ResearchItem] = []

    for page_no in range(1, max_pages + 1):
        params = {
            "cb": "",
            "industryCode": "*",
            "pageSize": str(page_size),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": start.strftime("%Y-%m-%d"),
            "endTime": end.strftime("%Y-%m-%d"),
            "pageNo": str(page_no),
            "fields": "",
            "qType": q_type,
            "orgCode": "",
            "code": "*",
            "rcode": "",
            "p": str(page_no),
            "pageNum": str(page_no),
        }
        payload = _request_json(EASTMONEY_REPORT_URL + "?" + urllib.parse.urlencode(params), referer=source.get("url") or EASTMONEY_REFERER)
        rows = payload.get("data") or []
        if not rows:
            break
        for row in rows:
            item = _eastmoney_row_to_item(row, source)
            if item is not None:
                items.append(item)
        total_page = int(payload.get("TotalPage") or page_no)
        if page_no >= total_page:
            break
    return items


def _eastmoney_row_to_item(row: dict[str, Any], source: dict[str, Any]) -> ResearchItem | None:
    title = _clean(row.get("title"))
    if not title:
        return None
    published_at = _parse_datetime(row.get("publishDate"))
    stock_name = _clean(row.get("stockName"))
    stock_code = _clean(row.get("stockCode"))
    industry = _clean(row.get("industryName") or row.get("indvInduName"))
    institution = _clean(row.get("orgSName") or row.get("orgName"))
    author = _clean(row.get("researcher") or ",".join(_clean_author(item) for item in row.get("author") or []))
    report_type = str(source.get("report_type") or REPORT_TYPE_MAP.get(str(row.get("reportType") or ""), "产业报告"))
    tags = [value for value in [industry, _clean(row.get("emRatingName") or row.get("sRatingName")), f"{row.get('attachPages') or 0}页"] if value and value != "0页"]
    symbols = [f"{stock_code} {stock_name}".strip()] if stock_code or stock_name else []
    summary = _summary_from_eastmoney(title, row, report_type)
    content_hash = _hash("|".join([str(row.get("infoCode") or ""), title, institution, str(published_at or "")]))
    return ResearchItem(
        title=title,
        summary=summary,
        content="",
        report_type=report_type,
        source_name=str(source["name"]),
        source_type=str(source.get("source_type", "公开来源")),
        source_url=_eastmoney_detail_url(row, source),
        institution=institution,
        author=author,
        industry=industry,
        symbols=symbols,
        tags=tags,
        published_at=published_at,
        crawled_at=datetime.now(),
        content_hash=content_hash,
        raw_payload=row,
    )


def _summary_from_eastmoney(title: str, row: dict[str, Any], report_type: str) -> str:
    parts = [f"{report_type}：{title}"]
    stock_name = _clean(row.get("stockName"))
    stock_code = _clean(row.get("stockCode"))
    if stock_name or stock_code:
        parts.append(f"标的：{stock_code} {stock_name}".strip())
    rating = _clean(row.get("emRatingName") or row.get("sRatingName"))
    if rating:
        parts.append(f"评级：{rating}")
    eps = _clean(row.get("predictThisYearEps"))
    pe = _clean(row.get("predictThisYearPe"))
    if eps or pe:
        parts.append(f"本年预测 EPS/PE：{eps or '-'} / {pe or '-'}")
    pages = _clean(row.get("attachPages"))
    size = _clean(row.get("attachSize"))
    if pages:
        parts.append(f"附件：{pages} 页，约 {size or '-'} KB")
    parts.append("来源为东方财富研报中心公开元数据；如需全文，请使用已授权渠道导入。")
    return "；".join(parts)


def _fetch_rss_source(source: dict[str, Any]) -> list[ResearchItem]:
    content = _request_text(str(source["url"]), referer=str(source.get("referer", "")))
    root = ET.fromstring(content)
    items = []
    for node in root.findall(".//item")[: int(source.get("limit", 50))]:
        title = _clean(_node_text(node, "title"))
        link = _clean(_node_text(node, "link"))
        summary = _clean(_node_text(node, "description"))
        published_at = _parse_datetime(_node_text(node, "pubDate"))
        if title:
            items.append(_generic_item(source, title, summary, "", link, published_at))
    return items


def _fetch_json_source(source: dict[str, Any]) -> list[ResearchItem]:
    payload = _request_json(str(source["url"]), referer=str(source.get("referer", "")))
    path = str(source.get("items_path", "data")).split(".")
    rows: Any = payload
    for key in path:
        rows = rows.get(key, []) if isinstance(rows, dict) else []
    items = []
    for row in rows[: int(source.get("limit", 50))] if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        title = _clean(row.get(str(source.get("title_field", "title"))))
        if not title:
            continue
        summary = _clean(row.get(str(source.get("summary_field", "summary"))))
        link = _clean(row.get(str(source.get("url_field", "url"))))
        published_at = _parse_datetime(row.get(str(source.get("date_field", "published_at"))))
        item = _generic_item(source, title, summary, "", link, published_at)
        item.raw_payload = row
        items.append(item)
    return items


def _fetch_html_source(source: dict[str, Any]) -> list[ResearchItem]:
    content = _request_text(str(source["url"]), referer=str(source.get("referer", "")))
    title_pattern = str(source.get("title_regex", r"<title[^>]*>(.*?)</title>"))
    matches = re.findall(title_pattern, content, flags=re.I | re.S)
    items = []
    for match in matches[: int(source.get("limit", 20))]:
        title = _clean_html(match[0] if isinstance(match, tuple) else match)
        if title:
            items.append(_generic_item(source, title, title, "", str(source["url"]), datetime.now()))
    return items


def _fetch_local_files(source: dict[str, Any]) -> list[ResearchItem]:
    root = Path(str(source["url"])).expanduser()
    if not root.exists():
        return []
    files = [path for path in root.rglob("*") if path.suffix.lower() in {".md", ".txt", ".json"}]
    items: list[ResearchItem] = []
    for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)[: int(source.get("limit", 200))]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".json":
            item = _local_json_item(source, path, text)
        else:
            item = _local_text_item(source, path, text)
        if item is not None:
            items.append(item)
    return items


def _local_json_item(source: dict[str, Any], path: Path, text: str) -> ResearchItem | None:
    try:
        payload = json.loads(text)
    except Exception:
        return _local_text_item(source, path, text)
    if not isinstance(payload, dict):
        return _local_text_item(source, path, text)
    title = _clean(payload.get("title") or path.stem)
    published_at = _parse_datetime(payload.get("published_at")) or datetime.fromtimestamp(path.stat().st_mtime)
    symbols = payload.get("symbols") if isinstance(payload.get("symbols"), list) else []
    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
    return ResearchItem(
        title=title,
        summary=_clean(payload.get("summary") or payload.get("content") or "")[:500],
        content=str(payload.get("content") or ""),
        report_type=_clean(payload.get("report_type") or "授权导入"),
        source_name=str(source["name"]),
        source_type=str(source.get("source_type", "用户授权文件")),
        source_url=str(path),
        institution=_clean(payload.get("institution")),
        author=_clean(payload.get("author")),
        industry=_clean(payload.get("industry")),
        symbols=[str(item) for item in symbols],
        tags=[str(item) for item in tags],
        published_at=published_at,
        crawled_at=datetime.now(),
        content_hash=_hash(f"{path}|{path.stat().st_mtime}|{title}"),
        raw_payload=payload,
    )


def _local_text_item(source: dict[str, Any], path: Path, text: str) -> ResearchItem | None:
    clean_text = _clean_text_block(text)
    if not clean_text:
        return None
    title = _extract_title(clean_text, path.stem)
    return ResearchItem(
        title=title,
        summary=clean_text[:500],
        content=clean_text,
        report_type="授权导入",
        source_name=str(source["name"]),
        source_type=str(source.get("source_type", "用户授权文件")),
        source_url=str(path),
        institution="",
        author="",
        industry="",
        symbols=_extract_symbols(clean_text),
        tags=[],
        published_at=datetime.fromtimestamp(path.stat().st_mtime),
        crawled_at=datetime.now(),
        content_hash=_hash(f"{path}|{path.stat().st_mtime}|{title}"),
        raw_payload={"path": str(path)},
    )


def _generic_item(source: dict[str, Any], title: str, summary: str, content: str, url: str, published_at: datetime | None) -> ResearchItem:
    return ResearchItem(
        title=title,
        summary=summary[:1000],
        content=content,
        report_type=str(source.get("report_type", "产业报告")),
        source_name=str(source["name"]),
        source_type=str(source.get("source_type", "公开来源")),
        source_url=url,
        institution=str(source.get("institution", "")),
        author="",
        industry=str(source.get("industry", "")),
        symbols=[],
        tags=[str(item) for item in source.get("tags", [])] if isinstance(source.get("tags"), list) else [],
        published_at=published_at,
        crawled_at=datetime.now(),
        content_hash=_hash("|".join([str(source["name"]), title, url, str(published_at or "")])),
        raw_payload={"url": url},
    )


def _request_json(url: str, referer: str = "") -> dict[str, Any]:
    text = _request_text(url, referer)
    stripped = text.strip()
    if stripped.startswith("callback(") and stripped.endswith(")"):
        stripped = stripped[len("callback(") : -1]
    return json.loads(stripped)


def _request_text(url: str, referer: str = "") -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer or url,
            "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        data = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return data.decode(charset, errors="ignore")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_author(value: Any) -> str:
    text = _clean(value)
    return text.split(".", 1)[1] if "." in text else text


def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return _clean(html.unescape(value))


def _clean_text_block(value: str) -> str:
    lines = [_clean(line.strip("# ").strip()) for line in value.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line:
            return line[:180]
    return fallback


def _extract_symbols(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b(?:00|30|60|68)\d{4}\b", text)))[:20]


def _node_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return child.text if child is not None and child.text else ""


def _parse_datetime(value: Any) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _eastmoney_detail_url(row: dict[str, Any], source: dict[str, Any]) -> str:
    info_code = _clean(row.get("infoCode"))
    if info_code:
        return f"{source.get('url') or EASTMONEY_REFERER}?infoCode={urllib.parse.quote(info_code)}"
    return str(source.get("url") or EASTMONEY_REFERER)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _sync_enabled() -> bool:
    return os.getenv("INDUSTRY_RESEARCH_SYNC_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def scheduler_sleep_seconds() -> int:
    return max(60, int(os.getenv("INDUSTRY_RESEARCH_SCHEDULER_SECONDS", "900")))
