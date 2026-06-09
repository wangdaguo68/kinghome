from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader
from pytdx.hq import TdxHq_API
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route


ROOT = Path(__file__).resolve().parent
STOCK_CACHE = ROOT / "stock_list_cache.json"
TDX_SERVERS = [
    ("180.153.18.170", 7709),
    ("119.147.212.81", 7709),
    ("119.147.212.81", 7707),
    ("101.227.73.20", 7709),
    ("101.227.77.254", 7709),
    ("114.80.63.12", 7709),
    ("202.108.253.131", 7709),
]
CATEGORY_MAP = {
    "5min": 0,
    "15min": 1,
    "30min": 2,
    "60min": 3,
    "day": 9,
    "daily": 9,
    "week": 5,
    "month": 6,
}
DEFAULT_OFFICIAL_TDX_MCP_URL = "https://txmcp.tdx.com.cn:3001/txmcp"
DEFAULT_RESEARCH_QUERY = "查一下A股最新产业深度研报"
PDF_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

ACCESS_TOKEN = os.getenv("TDX_MCP_ACCESS_TOKEN", "")

mcp = FastMCP(
    "tdx-mcp",
    instructions="通达信行情 MCP：提供实时行情、K 线、股票搜索和简单筛选。",
    json_response=True,
    stateless_http=True,
)


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        if not ACCESS_TOKEN:
            return JSONResponse({"error": "TDX_MCP_ACCESS_TOKEN not configured"}, status_code=503)
        provided = _access_token_from_request(request)
        if provided != ACCESS_TOKEN:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def _access_token_from_request(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    header_token = request.headers.get("x-tdx-mcp-token", "")
    if header_token:
        return header_token.strip()
    return request.query_params.get("access_token", "").strip()


@contextmanager
def tdx_api():
    last_error: Exception | None = None
    for host, port in TDX_SERVERS:
        api = TdxHq_API(raise_exception=True, auto_retry=True)
        try:
            if api.connect(host, port, time_out=4):
                yield api, host, port
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        finally:
            try:
                api.disconnect()
            except Exception:
                pass
    raise RuntimeError(f"通达信行情服务器连接失败：{last_error}")


def market_code(code: str, market: str = "auto") -> int:
    normalized = normalize_code(code)
    market = (market or "auto").lower()
    if market in {"sh", "sha", "shanghai", "1"}:
        return 1
    if market in {"sz", "sza", "shenzhen", "0"}:
        return 0
    if normalized.startswith(("5", "6", "9", "11", "12", "13", "51", "56", "58", "60", "68")):
        return 1
    return 0


def normalize_code(code: str) -> str:
    text = str(code).strip().upper()
    text = text.replace(".SH", "").replace(".SZ", "")
    match = re.search(r"\d{6}", text)
    if not match:
        raise ValueError(f"无效证券代码：{code}")
    return match.group(0)


def quote_rows(codes: str | list[str], market: str = "auto") -> dict[str, Any]:
    code_list = split_codes(codes)
    requests = [(market_code(code, market), normalize_code(code)) for code in code_list]
    with tdx_api() as (api, host, port):
        rows = api.get_security_quotes(requests) or []
    return {
        "provider": "pytdx",
        "server": f"{host}:{port}",
        "count": len(rows),
        "quotes": [normalize_quote(row) for row in rows],
    }


def kline_rows(code: str, period: str = "day", count: int = 120, market: str = "auto") -> dict[str, Any]:
    normalized = normalize_code(code)
    category = CATEGORY_MAP.get(period.lower())
    if category is None:
        raise ValueError(f"不支持的周期：{period}")
    count = max(1, min(int(count), 800))
    with tdx_api() as (api, host, port):
        rows = api.get_security_bars(category, market_code(normalized, market), normalized, 0, count) or []
    return {
        "provider": "pytdx",
        "server": f"{host}:{port}",
        "code": normalized,
        "period": period,
        "count": len(rows),
        "bars": rows,
    }


def split_codes(codes: str | list[str]) -> list[str]:
    if isinstance(codes, list):
        values = codes
    else:
        values = re.split(r"[,，\s]+", str(codes))
    return [normalize_code(value) for value in values if str(value).strip()][:80]


def normalize_quote(row: dict[str, Any]) -> dict[str, Any]:
    price = _float(row.get("price"))
    last_close = _float(row.get("last_close"))
    pct = round((price / last_close - 1) * 100, 2) if last_close else 0
    return {
        "market": row.get("market"),
        "code": row.get("code"),
        "active1": row.get("active1"),
        "price": price,
        "last_close": last_close,
        "open": _float(row.get("open")),
        "high": _float(row.get("high")),
        "low": _float(row.get("low")),
        "volume": row.get("vol"),
        "amount": row.get("amount"),
        "pct": pct,
        "bid1": _float(row.get("bid1")),
        "ask1": _float(row.get("ask1")),
    }


def lookup_stock(keyword: str, limit: int = 20, refresh: bool = False) -> dict[str, Any]:
    keyword = str(keyword).strip()
    limit = max(1, min(int(limit), 100))
    if re.fullmatch(r"\d{1,6}", keyword):
        code = keyword.zfill(6)
        quote = quote_rows([code])
        return {
            "count": 1,
            "items": [{"market": market_code(code), "code": code, "name": "", "quote": quote["quotes"][0] if quote["quotes"] else None}],
            "warning": "",
        }
    if not refresh and not STOCK_CACHE.exists():
        return {
            "count": 0,
            "items": [],
            "warning": "股票名称缓存尚未生成；请先用 refresh=true 在低峰期刷新，或直接用 6 位代码查询。",
        }
    rows = load_stock_list(refresh=refresh)
    if not keyword:
        matches = rows[:limit]
    elif re.fullmatch(r"\d+", keyword):
        matches = [row for row in rows if keyword in row.get("code", "")][:limit]
    else:
        key = keyword.upper()
        matches = [row for row in rows if key in row.get("name", "").upper() or key in row.get("code", "")][:limit]
    return {"count": len(matches), "items": matches}


def load_stock_list(refresh: bool = False) -> list[dict[str, Any]]:
    if not refresh and STOCK_CACHE.exists() and time.time() - STOCK_CACHE.stat().st_mtime < 86400:
        return json.loads(STOCK_CACHE.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    with tdx_api() as (api, _host, _port):
        for market in [0, 1]:
            total = int(api.get_security_count(market) or 0)
            for start in range(0, total, 1000):
                batch = api.get_security_list(market, start) or []
                for item in batch:
                    code = str(item.get("code", ""))
                    name = str(item.get("name", "")).strip()
                    if re.fullmatch(r"\d{6}", code):
                        rows.append({"market": market, "code": code, "name": name})
    STOCK_CACHE.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return rows


def screener(query: str, limit: int = 30) -> dict[str, Any]:
    query = str(query).strip()
    limit = max(1, min(int(limit), 100))
    rows = load_stock_list(refresh=False)
    stock_codes = [row for row in rows if row["code"].startswith(("00", "30", "60", "68"))]
    selected = stock_codes[: min(len(stock_codes), int(os.getenv("TDX_SCREENER_SCAN_LIMIT", "1200")))]
    quotes: list[dict[str, Any]] = []
    for offset in range(0, len(selected), 80):
        batch = selected[offset : offset + 80]
        try:
            result = quote_rows([row["code"] for row in batch])
            quotes.extend(result["quotes"])
        except Exception:
            continue
    if "跌停" in query:
        filtered = [row for row in quotes if row["pct"] <= -9.7]
        filtered.sort(key=lambda row: row["pct"])
    elif "涨停" in query:
        filtered = [row for row in quotes if row["pct"] >= 9.7]
        filtered.sort(key=lambda row: row["pct"], reverse=True)
    else:
        filtered = sorted(quotes, key=lambda row: row["pct"], reverse=True)
    return {"query": query, "scanned": len(quotes), "count": len(filtered[:limit]), "items": filtered[:limit]}


async def call_official_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    token = os.getenv("TDX_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TDX_TOKEN not configured")
    headers = {"Authorization": f"Bearer {token}"}
    official_url = os.getenv("TDX_OFFICIAL_MCP_URL", DEFAULT_OFFICIAL_TDX_MCP_URL)
    async with streamablehttp_client(official_url, headers=headers) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    text_parts = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", "") == "text":
            text_parts.append(getattr(item, "text", ""))
    text = "".join(text_parts).strip()
    if not text:
        return {"ok": False, "data": [], "error": "empty official TDX MCP response"}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"ok": True, "data": parsed}
    except json.JSONDecodeError:
        return {"ok": False, "data": [], "raw_text": text}


def build_wenda_query(
    query: str = "",
    name: str = "",
    symbol: str = "",
    bdate: str = "",
    edate: str = "",
    keywords: str = "",
    desc: str = "",
) -> str:
    query = str(query or "").strip()
    if query:
        return query
    subject = str(name or symbol or "").strip()
    fields = [subject, str(bdate or "").strip(), str(edate or "").strip(), str(keywords or "").strip(), str(desc or "").strip()]
    compact = "|".join(fields).strip("|")
    return compact or os.getenv("TDX_RESEARCH_DEFAULT_QUERY", DEFAULT_RESEARCH_QUERY)


async def research_search(
    query: str = "",
    name: str = "",
    symbol: str = "",
    bdate: str = "",
    edate: str = "",
    keywords: str = "",
    desc: str = "",
    limit: int = 20,
    fetch_content: bool = False,
) -> dict[str, Any]:
    final_query = build_wenda_query(query, name, symbol, bdate, edate, keywords, desc)
    limit = max(1, min(int(limit), 100))
    payload = await call_official_tool("wenda_report_query", {"query": final_query})
    items = normalize_report_rows(payload)[:limit]
    if fetch_content:
        max_chars = int(os.getenv("TDX_RESEARCH_CONTENT_MAX_CHARS", "80000"))
        for item in items:
            detail = await research_detail(item.get("source_url", ""), item.get("title", ""), item.get("summary", ""), max_chars=max_chars)
            item["content"] = detail.get("content", "")
            if detail.get("content_error"):
                item["content_error"] = detail["content_error"]
    return {
        "ok": bool(payload.get("ok", True)) if isinstance(payload, dict) else True,
        "provider": "official-tdx-mcp",
        "tool": "wenda_report_query",
        "query": final_query,
        "count": len(items),
        "items": items,
        "raw": payload,
    }


def normalize_report_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else []
    if not isinstance(data, list) or not data:
        return []
    header = [str(value).strip() for value in data[0]] if isinstance(data[0], list) else []
    rows = data[1:] if header else data
    items: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            mapped = row
        elif isinstance(row, list):
            mapped = {header[index] if index < len(header) else str(index): value for index, value in enumerate(row)}
        else:
            continue
        title = clean_text(mapped.get("标题") or mapped.get("title"))
        if not title:
            continue
        source_url = clean_text(mapped.get("链接") or mapped.get("url") or mapped.get("source_url"))
        summary = clean_text(mapped.get("摘要") or mapped.get("summary"))
        institution = clean_text(mapped.get("来源") or mapped.get("机构") or mapped.get("institution"))
        published_at = clean_text(mapped.get("时间") or mapped.get("日期") or mapped.get("published_at"))
        items.append(
            {
                "title": title,
                "published_at": published_at,
                "source_url": source_url,
                "institution": institution,
                "summary": summary,
                "content": "",
                "source_name": "通达信问达研报",
                "source_type": "通达信MCP",
                "report_type": classify_report_type(title, summary),
                "raw_payload": mapped,
            }
        )
    return dedupe_reports(items)


def dedupe_reports(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = "|".join([item.get("source_url", ""), item.get("title", ""), item.get("published_at", "")]).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


async def research_detail(url: str, title: str = "", summary: str = "", max_chars: int = 80000) -> dict[str, Any]:
    url = str(url or "").strip()
    summary = clean_text(summary)
    if not url:
        return {"ok": bool(summary), "url": url, "title": title, "content": summary, "content_error": "missing report url"}
    try:
        if ".pdf" in url.lower():
            content = await run_in_threadpool(fetch_pdf_text, url, max_chars)
        else:
            content = await run_in_threadpool(fetch_text_url, url, max_chars)
        return {"ok": True, "url": url, "title": title, "content": content or summary, "content_error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "title": title, "content": summary, "content_error": str(exc)}


def fetch_pdf_text(url: str, max_chars: int = 80000) -> str:
    request = urllib.request.Request(quote_url(url), headers={"User-Agent": PDF_USER_AGENT, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
        data = response.read(int(os.getenv("TDX_RESEARCH_PDF_MAX_BYTES", "25165824")))
    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
        if sum(len(part) for part in parts) >= max_chars:
            break
    return clean_text_block("\n".join(parts))[:max_chars]


def fetch_text_url(url: str, max_chars: int = 80000) -> str:
    request = urllib.request.Request(quote_url(url), headers={"User-Agent": PDF_USER_AGENT, "Accept": "text/html,text/plain,*/*"})
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        data = response.read(int(os.getenv("TDX_RESEARCH_TEXT_MAX_BYTES", "5242880")))
    text = data.decode(charset, errors="ignore")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text_block(text)[:max_chars]


def quote_url(url: str) -> str:
    parts = urllib.parse.urlsplit(str(url).strip())
    path = urllib.parse.quote(parts.path, safe="/%")
    query = urllib.parse.quote(parts.query, safe="=&%/:,+")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def classify_report_type(title: str, summary: str = "") -> str:
    text = f"{title} {summary}"
    if any(word in text for word in ["晨会", "早会"]):
        return "券商晨会"
    if any(word in text for word in ["宏观", "利率", "GDP", "CPI", "PPI"]):
        return "宏观研究"
    if any(word in text for word in ["策略", "配置", "市场周报", "A股周报"]):
        return "策略报告"
    if any(word in text for word in ["财务模型", "盈利预测", "估值模型"]):
        return "财务模型"
    if re.search(r"\b(?:00|30|60|68)\d{4}\b", text) or any(word in text for word in ["公司", "个股", "评级", "目标价"]):
        return "个股拆解"
    return "产业报告"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_text_block(value: str) -> str:
    lines = [clean_text(line) for line in str(value or "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def health_payload() -> dict[str, Any]:
    token_configured = bool(os.getenv("TDX_TOKEN", ""))
    return {
        "ok": True,
        "provider": "pytdx",
        "token_configured": token_configured,
        "message": "TDX MCP 服务进程正常；行情连通性请调用 tdx_quotes 或 /quotes 验证。",
    }


def tdx_probe_payload() -> dict[str, Any]:
    token_configured = bool(os.getenv("TDX_TOKEN", ""))
    try:
        sample = quote_rows(["000001", "600000"])
        return {
            "ok": True,
            "provider": "pytdx",
            "token_configured": token_configured,
            "message": "通达信行情服务可用",
            "sample": sample["quotes"][:2],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "provider": "pytdx",
            "token_configured": token_configured,
            "message": str(exc),
            "sample": [],
        }


@mcp.tool()
def tdx_health() -> dict[str, Any]:
    """检查通达信行情服务是否可用。"""
    return health_payload()


@mcp.tool()
def tdx_probe() -> dict[str, Any]:
    """发起一次真实行情查询，验证通达信上游服务器是否可用。"""
    return tdx_probe_payload()


@mcp.tool()
def tdx_quotes(codes: str, market: str = "auto") -> dict[str, Any]:
    """查询一个或多个证券实时行情，codes 可用逗号分隔。"""
    return quote_rows(codes, market=market)


@mcp.tool()
def tdx_kline(code: str, period: str = "day", count: int = 120, market: str = "auto") -> dict[str, Any]:
    """查询 K 线，period 支持 day/week/month/60min/30min/15min/5min。"""
    return kline_rows(code, period=period, count=count, market=market)


@mcp.tool()
def tdx_lookup_stock(keyword: str, limit: int = 20, refresh: bool = False) -> dict[str, Any]:
    """按代码或名称搜索证券。"""
    return lookup_stock(keyword, limit=limit, refresh=refresh)


@mcp.tool()
def tdx_screener(query: str, limit: int = 30) -> dict[str, Any]:
    """简单筛选器，支持涨停/跌停/涨幅排行等关键词。"""
    return screener(query, limit=limit)


@mcp.tool()
async def tdx_research_search(
    query: str = "",
    name: str = "",
    symbol: str = "",
    bdate: str = "",
    edate: str = "",
    keywords: str = "",
    desc: str = "",
    limit: int = 20,
    fetch_content: bool = False,
) -> dict[str, Any]:
    """Search TDX Wenda research reports and optionally extract linked PDF text."""
    return await research_search(
        query=query,
        name=name,
        symbol=symbol,
        bdate=bdate,
        edate=edate,
        keywords=keywords,
        desc=desc,
        limit=limit,
        fetch_content=fetch_content,
    )


@mcp.tool()
async def tdx_research_detail(url: str, title: str = "", summary: str = "", max_chars: int = 80000) -> dict[str, Any]:
    """Fetch report detail content from a TDX research report URL."""
    return await research_detail(url=url, title=title, summary=summary, max_chars=max_chars)


async def health(_request: Request) -> JSONResponse:
    return JSONResponse(health_payload())


async def rest_quotes(request: Request) -> JSONResponse:
    return await safe_json_async(lambda: quote_rows(request.query_params.get("codes", ""), request.query_params.get("market", "auto")))


async def rest_kline(request: Request) -> JSONResponse:
    return await safe_json_async(
        lambda: kline_rows(
            request.path_params["code"],
            request.query_params.get("period", "day"),
            int(request.query_params.get("count", "120")),
            request.query_params.get("market", "auto"),
        )
    )


async def rest_lookup(request: Request) -> JSONResponse:
    return await safe_json_async(
        lambda: lookup_stock(
            request.query_params.get("keyword", ""),
            int(request.query_params.get("limit", "20")),
            request.query_params.get("refresh", "0").lower() in {"1", "true", "yes"},
        )
    )


async def rest_screener(request: Request) -> JSONResponse:
    return await safe_json_async(lambda: screener(request.query_params.get("query", ""), int(request.query_params.get("limit", "30"))))


async def rest_research_search(request: Request) -> JSONResponse:
    try:
        payload = await research_search(
            query=request.query_params.get("query", ""),
            name=request.query_params.get("name", ""),
            symbol=request.query_params.get("symbol", ""),
            bdate=request.query_params.get("bdate", ""),
            edate=request.query_params.get("edate", ""),
            keywords=request.query_params.get("keywords", ""),
            desc=request.query_params.get("desc", ""),
            limit=int(request.query_params.get("limit", "20")),
            fetch_content=request.query_params.get("fetch_content", "0").lower() in {"1", "true", "yes"},
        )
        return JSONResponse(payload)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


async def rest_research_detail(request: Request) -> JSONResponse:
    try:
        payload = await research_detail(
            url=request.query_params.get("url", ""),
            title=request.query_params.get("title", ""),
            summary=request.query_params.get("summary", ""),
            max_chars=int(request.query_params.get("max_chars", "80000")),
        )
        return JSONResponse(payload)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


def safe_json(builder) -> JSONResponse:
    try:
        return JSONResponse(builder())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


async def safe_json_async(builder) -> JSONResponse:
    try:
        return JSONResponse(await run_in_threadpool(builder))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def create_app() -> Starlette:
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/quotes", rest_quotes),
            Route("/kline/{code:str}", rest_kline),
            Route("/lookup", rest_lookup),
            Route("/screener", rest_screener),
            Route("/research/search", rest_research_search),
            Route("/research/detail", rest_research_detail),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(TokenAuthMiddleware)
    return app


app = create_app()
