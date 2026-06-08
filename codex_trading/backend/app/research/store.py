from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.data.mysql_store import Connection, mysql_connection


SOURCES_TABLE = "industry_research_sources"
ITEMS_TABLE = "industry_research_items"
RUNS_TABLE = "industry_research_crawl_runs"

_SCHEMA_READY = False


@dataclass
class ResearchItem:
    title: str
    summary: str = ""
    content: str = ""
    report_type: str = "产业报告"
    source_name: str = ""
    source_type: str = "公开来源"
    source_url: str = ""
    institution: str = ""
    author: str = ""
    industry: str = ""
    symbols: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    crawled_at: datetime | None = None
    content_hash: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)


def ensure_research_schema_once(connection: Connection) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    ensure_research_schema(connection)
    _SCHEMA_READY = True


def ensure_research_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SOURCES_TABLE} (
                id BIGINT NOT NULL AUTO_INCREMENT,
                name VARCHAR(128) NOT NULL,
                source_type VARCHAR(64) NOT NULL DEFAULT '公开来源',
                url VARCHAR(1024) NOT NULL DEFAULT '',
                enabled TINYINT NOT NULL DEFAULT 1,
                last_sync_at DATETIME NULL,
                last_status VARCHAR(32) NOT NULL DEFAULT 'pending',
                last_error TEXT NULL,
                config_json TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uniq_research_source_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ITEMS_TABLE} (
                id BIGINT NOT NULL AUTO_INCREMENT,
                title VARCHAR(512) NOT NULL,
                summary TEXT NULL,
                content MEDIUMTEXT NULL,
                report_type VARCHAR(64) NOT NULL DEFAULT '产业报告',
                source_name VARCHAR(128) NOT NULL DEFAULT '',
                source_type VARCHAR(64) NOT NULL DEFAULT '公开来源',
                source_url VARCHAR(1024) NOT NULL DEFAULT '',
                institution VARCHAR(128) NOT NULL DEFAULT '',
                author VARCHAR(255) NOT NULL DEFAULT '',
                industry VARCHAR(128) NOT NULL DEFAULT '',
                symbols_json TEXT NULL,
                tags_json TEXT NULL,
                published_at DATETIME NULL,
                crawled_at DATETIME NOT NULL,
                content_hash CHAR(64) NOT NULL,
                raw_payload_json MEDIUMTEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uniq_research_content_hash (content_hash),
                KEY idx_research_published (published_at, id),
                KEY idx_research_type_date (report_type, published_at),
                KEY idx_research_source_date (source_name, published_at),
                KEY idx_research_industry_date (industry, published_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RUNS_TABLE} (
                id BIGINT NOT NULL AUTO_INCREMENT,
                source_name VARCHAR(128) NOT NULL DEFAULT '',
                started_at DATETIME NOT NULL,
                finished_at DATETIME NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'running',
                inserted_count INT NOT NULL DEFAULT 0,
                seen_count INT NOT NULL DEFAULT 0,
                error TEXT NULL,
                PRIMARY KEY (id),
                KEY idx_research_runs_started (started_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )


def database_available() -> bool:
    try:
        with mysql_connection() as connection:
            if connection is None:
                return False
            ensure_research_schema_once(connection)
            return True
    except Exception:
        return False


def upsert_source(name: str, source_type: str, url: str, status: str = "ok", error: str = "", config: dict[str, Any] | None = None) -> None:
    with mysql_connection() as connection:
        if connection is None:
            return
        ensure_research_schema_once(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {SOURCES_TABLE}
                    (name, source_type, url, enabled, last_sync_at, last_status, last_error, config_json)
                VALUES (%s, %s, %s, 1, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    source_type = VALUES(source_type),
                    url = VALUES(url),
                    last_sync_at = VALUES(last_sync_at),
                    last_status = VALUES(last_status),
                    last_error = VALUES(last_error),
                    config_json = VALUES(config_json)
                """,
                (name, source_type, url, datetime.now(), status, error or None, _json(config or {})),
            )


def create_crawl_run(source_name: str) -> int | None:
    with mysql_connection() as connection:
        if connection is None:
            return None
        ensure_research_schema_once(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {RUNS_TABLE} (source_name, started_at, status)
                VALUES (%s, %s, 'running')
                """,
                (source_name, datetime.now()),
            )
            return int(cursor.lastrowid)


def finish_crawl_run(run_id: int | None, status: str, inserted_count: int, seen_count: int, error: str = "") -> None:
    if run_id is None:
        return
    with mysql_connection() as connection:
        if connection is None:
            return
        ensure_research_schema_once(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {RUNS_TABLE}
                SET finished_at = %s, status = %s, inserted_count = %s, seen_count = %s, error = %s
                WHERE id = %s
                """,
                (datetime.now(), status, inserted_count, seen_count, error or None, run_id),
            )


def upsert_research_items(items: list[ResearchItem]) -> dict[str, int]:
    if not items:
        return {"seen_count": 0, "inserted_count": 0}
    now = datetime.now()
    values = []
    for item in items:
        if not item.title or not item.content_hash:
            continue
        values.append(
            (
                item.title[:512],
                item.summary,
                item.content,
                item.report_type,
                item.source_name,
                item.source_type,
                item.source_url,
                item.institution,
                item.author,
                item.industry,
                _json(item.symbols),
                _json(item.tags),
                item.published_at,
                item.crawled_at or now,
                item.content_hash,
                _json(item.raw_payload),
            )
        )
    if not values:
        return {"seen_count": len(items), "inserted_count": 0}

    with mysql_connection() as connection:
        if connection is None:
            return {"seen_count": len(items), "inserted_count": 0}
        ensure_research_schema_once(connection)
        before = _item_count(connection)
        with connection.cursor() as cursor:
            cursor.executemany(
                f"""
                INSERT INTO {ITEMS_TABLE}
                    (title, summary, content, report_type, source_name, source_type, source_url,
                     institution, author, industry, symbols_json, tags_json, published_at,
                     crawled_at, content_hash, raw_payload_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    summary = IF(VALUES(summary) <> '', VALUES(summary), summary),
                    content = IF(VALUES(content) <> '', VALUES(content), content),
                    source_url = IF(VALUES(source_url) <> '', VALUES(source_url), source_url),
                    institution = IF(VALUES(institution) <> '', VALUES(institution), institution),
                    author = IF(VALUES(author) <> '', VALUES(author), author),
                    industry = IF(VALUES(industry) <> '', VALUES(industry), industry),
                    symbols_json = VALUES(symbols_json),
                    tags_json = VALUES(tags_json),
                    published_at = COALESCE(VALUES(published_at), published_at),
                    crawled_at = VALUES(crawled_at),
                    raw_payload_json = VALUES(raw_payload_json)
                """,
                values,
            )
        after = _item_count(connection)
    return {"seen_count": len(items), "inserted_count": max(0, after - before)}


def list_research_items(
    page: int = 1,
    page_size: int = 20,
    report_type: str = "",
    source: str = "",
    industry: str = "",
    symbol: str = "",
    keyword: str = "",
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(100, max(5, page_size))
    offset = (page - 1) * page_size
    try:
        with mysql_connection() as connection:
            if connection is None:
                return _empty_page(page, page_size, "MySQL 未连接，产业研报暂无法读取。")
            ensure_research_schema_once(connection)
            where_sql, params = _research_filters(report_type, source, industry, symbol, keyword)
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total FROM {ITEMS_TABLE} {where_sql}", params)
                total = int((cursor.fetchone() or {}).get("total", 0))
                cursor.execute(
                    f"""
                    SELECT id, title, summary, content, report_type, source_name, source_type, source_url,
                           institution, author, industry, symbols_json, tags_json, published_at, crawled_at
                    FROM {ITEMS_TABLE}
                    {where_sql}
                    ORDER BY COALESCE(published_at, crawled_at) DESC, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    [*params, page_size, offset],
                )
                rows = cursor.fetchall()
    except Exception as exc:  # noqa: BLE001
        return _empty_page(page, page_size, f"产业研报读取失败：{exc}")
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "items": [_row_to_item(row) for row in rows],
        "warning": "",
    }


def research_stats() -> dict[str, Any]:
    try:
        with mysql_connection() as connection:
            if connection is None:
                return {"total": 0, "today_count": 0, "source_count": 0, "latest_published_at": None, "latest_crawled_at": None, "warning": "MySQL 未连接。"}
            ensure_research_schema_once(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN DATE(crawled_at) = %s THEN 1 ELSE 0 END) AS today_count,
                        COUNT(DISTINCT source_name) AS source_count,
                        MAX(published_at) AS latest_published_at,
                        MAX(crawled_at) AS latest_crawled_at
                    FROM {ITEMS_TABLE}
                    """,
                    (date.today(),),
                )
                row = cursor.fetchone() or {}
    except Exception as exc:  # noqa: BLE001
        return {"total": 0, "today_count": 0, "source_count": 0, "latest_published_at": None, "latest_crawled_at": None, "warning": str(exc)}
    return {
        "total": int(row.get("total") or 0),
        "today_count": int(row.get("today_count") or 0),
        "source_count": int(row.get("source_count") or 0),
        "latest_published_at": _dt(row.get("latest_published_at")),
        "latest_crawled_at": _dt(row.get("latest_crawled_at")),
        "warning": "",
    }


def research_sources() -> dict[str, Any]:
    try:
        with mysql_connection() as connection:
            if connection is None:
                return {"sources": [], "warning": "MySQL 未连接。"}
            ensure_research_schema_once(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT name, source_type, url, enabled, last_sync_at, last_status, last_error
                    FROM {SOURCES_TABLE}
                    ORDER BY updated_at DESC, name
                    """
                )
                rows = cursor.fetchall()
    except Exception as exc:  # noqa: BLE001
        return {"sources": [], "warning": str(exc)}
    return {"sources": [_row_to_source(row) for row in rows], "warning": ""}


def _research_filters(report_type: str, source: str, industry: str, symbol: str, keyword: str) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if report_type:
        clauses.append("report_type = %s")
        params.append(report_type)
    if source:
        clauses.append("source_name = %s")
        params.append(source)
    if industry:
        clauses.append("industry = %s")
        params.append(industry)
    if symbol:
        clauses.append("symbols_json LIKE %s")
        params.append(f"%{symbol}%")
    if keyword:
        like = f"%{keyword}%"
        clauses.append("(title LIKE %s OR summary LIKE %s OR content LIKE %s OR tags_json LIKE %s)")
        params.extend([like, like, like, like])
    if not clauses:
        return "", []
    return "WHERE " + " AND ".join(clauses), params


def _row_to_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "summary": row.get("summary") or "",
        "content": row.get("content") or "",
        "report_type": row.get("report_type") or "",
        "source_name": row.get("source_name") or "",
        "source_type": row.get("source_type") or "",
        "source_url": row.get("source_url") or "",
        "institution": row.get("institution") or "",
        "author": row.get("author") or "",
        "industry": row.get("industry") or "",
        "symbols": _loads(row.get("symbols_json"), []),
        "tags": _loads(row.get("tags_json"), []),
        "published_at": _dt(row.get("published_at")),
        "crawled_at": _dt(row.get("crawled_at")),
    }


def _row_to_source(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("name") or "",
        "source_type": row.get("source_type") or "",
        "url": row.get("url") or "",
        "enabled": bool(row.get("enabled")),
        "last_sync_at": _dt(row.get("last_sync_at")),
        "last_status": row.get("last_status") or "",
        "last_error": row.get("last_error") or "",
    }


def _empty_page(page: int, page_size: int, warning: str) -> dict[str, Any]:
    return {"page": page, "page_size": page_size, "total": 0, "total_pages": 0, "items": [], "warning": warning}


def _item_count(connection: Connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS total FROM {ITEMS_TABLE}")
        return int((cursor.fetchone() or {}).get("total", 0))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _dt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)
