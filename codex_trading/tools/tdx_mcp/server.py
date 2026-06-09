from __future__ import annotations

import json
import os
import re
import time
from contextlib import asynccontextmanager
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
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
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(TokenAuthMiddleware)
    return app


app = create_app()
