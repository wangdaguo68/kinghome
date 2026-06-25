from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx


class FreeMarketError(RuntimeError):
    pass


class EastMoneyFreeClient:
    POOL_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
    DOWN_POOL_URL = "https://push2ex.eastmoney.com/getTopicDTPool"
    FAILED_POOL_URL = "https://push2ex.eastmoney.com/getTopicZBPool"
    CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
    A_SHARE_FS = "m:0+t:6,m:0+t:80,m:0+t:81,m:1+t:2,m:1+t:23"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def _get_json_with_client(
        self, client: httpx.AsyncClient, url: str, params: dict[str, str], *, attempts: int = 4
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise FreeMarketError("免费接口返回值不是对象")
                return payload
            except (httpx.HTTPError, ValueError, FreeMarketError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.6 * (attempt + 1))
        raise FreeMarketError(f"免费接口连续失败：{last_error}") from last_error

    async def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.HEADERS, follow_redirects=True, trust_env=False
        ) as client:
            return await self._get_json_with_client(client, url, params)

    @staticmethod
    def _is_a_share_code(code: str) -> bool:
        return code.startswith(("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "8", "4", "92"))

    @staticmethod
    def _value(value: Any) -> float | None:
        if value in ("-", None):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _pool_count(self, url: str, trade_date: str) -> int:
        payload = await self._get_json(url, {
            "ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt", "Pageindex": "0",
            "pagesize": "10000", "sort": "fbt:asc", "date": trade_date,
        })
        data = payload.get("data") or {}
        if "tc" in data:
            return int(data.get("tc") or 0)
        pool = data.get("pool")
        return len(pool) if isinstance(pool, list) else 0

    async def market_breadth(self, trade_date: str, *, limit_up_count: int | None = None) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        total = 0
        fields = "f2,f3,f6,f12,f13,f14,f15,f16,f17,f18,f20,f21,f26,f152"
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.HEADERS, follow_redirects=True, trust_env=False
        ) as client:
            for page in range(1, 80):
                payload = await self._get_json_with_client(client, self.CLIST_URL, {
                    "pn": str(page), "pz": "100", "po": "1", "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281", "fltt": "2", "invt": "2",
                    "fid": "f3", "fs": self.A_SHARE_FS, "fields": fields,
                })
                data = payload.get("data") or {}
                if page == 1:
                    total = int(data.get("total") or 0)
                diff = data.get("diff") or []
                if not isinstance(diff, list) or not diff:
                    break
                rows.extend(diff)
                if len(rows) >= total or len(diff) < 100:
                    break
                await asyncio.sleep(0.08)

        valid = [
            row for row in rows
            if self._value(row.get("f3")) is not None
            and self._value(row.get("f2")) is not None
            and self._is_a_share_code(str(row.get("f12") or ""))
        ]
        if len(valid) < 4_000:
            raise FreeMarketError(f"{trade_date} 东方财富全A行情列表不完整：{len(valid)}")

        changes = [float(self._value(row.get("f3")) or 0) for row in valid]
        amount_top = sorted(valid, key=lambda row: float(self._value(row.get("f6")) or 0), reverse=True)[:100]
        capacity_changes = [float(self._value(row.get("f3")) or 0) for row in amount_top]
        failed_count = await self._pool_count(self.FAILED_POOL_URL, trade_date)
        down_count = await self._pool_count(self.DOWN_POOL_URL, trade_date)
        if limit_up_count is None:
            limit_up_count = await self._pool_count(self.POOL_URL, trade_date)

        return {
            "trade_date": trade_date,
            "rows": [
                {
                    "ts_code": str(row.get("f12") or ""),
                    "code": str(row.get("f12") or ""),
                    "name": str(row.get("f14") or ""),
                    "pct_chg": float(self._value(row.get("f3")) or 0),
                    "amount": float(self._value(row.get("f6")) or 0),
                    "industry": "",
                }
                for row in valid
            ],
            "breadth": {
                "eligible": len(valid),
                "up": sum(value > 0 for value in changes),
                "down": sum(value < 0 for value in changes),
                "flat": sum(value == 0 for value in changes),
                "median": round(float(median(changes)), 4),
                "limit_up": int(limit_up_count),
                "limit_down": int(down_count),
                "failed_limit": int(failed_count),
            },
            "capacity": {
                "sample": len(capacity_changes),
                "up": sum(value > 0 for value in capacity_changes),
                "down": sum(value < 0 for value in capacity_changes),
                "median": round(float(median(capacity_changes)), 4) if capacity_changes else 0,
            },
            "source": "东方财富全A行情列表",
        }

    async def trade_dates(self, count: int = 10) -> list[str]:
        params = {
            "secid": "1.000001", "klt": "101", "fqt": "0", "lmt": str(max(20, count * 2)),
            "end": "20500101", "iscca": "1", "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        payload = await self._get_json(self.KLINE_URL, params)
        klines = (payload.get("data") or {}).get("klines") or []
        dates = [str(item).split(",", 1)[0].replace("-", "") for item in klines]
        dates = [item for item in dates if len(item) == 8 and item.isdigit()]
        if len(dates) < min(5, count):
            raise FreeMarketError("东方财富指数交易日数据不完整")
        return dates[-count:][::-1]

    async def limit_up_pool(self, trade_date: str) -> list[dict[str, Any]]:
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt", "Pageindex": "0",
            "pagesize": "10000", "sort": "fbt:asc", "date": trade_date,
        }
        payload = await self._get_json(self.POOL_URL, params)
        raw_rows = (payload.get("data") or {}).get("pool")
        if raw_rows is None and payload.get("data") is None:
            return []
        if not isinstance(raw_rows, list):
            raise FreeMarketError(f"{trade_date} 东方财富涨停池结构异常")
        return [
            {
                "code": str(row.get("c", "")),
                "name": str(row.get("n", "")),
                "change": float(row.get("zdp") or 0),
                "amount": float(row.get("amount") or 0),
                "turnover": float(row.get("hs") or 0),
                "first_limit_time": str(row.get("fbt") or ""),
                "last_limit_time": str(row.get("lbt") or ""),
                "failed_count": int(row.get("zbc") or 0),
                "industry": str(row.get("hybk") or "市场热点"),
                "vendor_ladder": int(row.get("lbc") or 1),
            }
            for row in raw_rows
            if str(row.get("c", "")).isdigit() and self._is_a_share_code(str(row.get("c", "")))
        ]

    async def recent_pools(self, count: int = 6) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
        pools: dict[str, list[dict[str, Any]]] = {}
        selected: list[str] = []
        today = datetime.now(timezone(timedelta(hours=8))).date()
        for offset in range(21):
            trade_date = (today - timedelta(days=offset)).strftime("%Y%m%d")
            result = await self.limit_up_pool(trade_date)
            if not result:
                continue
            selected.append(trade_date)
            pools[trade_date] = result
            if len(selected) >= count:
                break
            await asyncio.sleep(0.2)
        if len(selected) < count:
            raise FreeMarketError(f"最近21日仅取得{len(selected)}个有效涨停池")
        return selected, pools

    async def stock_bars(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        market = "1" if code.startswith(("5", "6", "9")) else "0"
        payload = await self._get_json(self.KLINE_URL, {
            "secid": f"{market}.{code}", "klt": "101", "fqt": "0", "lmt": str(limit),
            "end": "20500101", "iscca": "1", "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        })
        klines = (payload.get("data") or {}).get("klines") or []
        rows: list[dict[str, Any]] = []
        for item in klines:
            fields = str(item).split(",")
            if len(fields) < 10:
                continue
            try:
                close = float(fields[2])
                rows.append({
                    "trade_date": fields[0].replace("-", ""), "open": float(fields[1]),
                    "close": close, "high": float(fields[3]), "low": float(fields[4]),
                    "volume": float(fields[5]), "amount": float(fields[6]), "pre_close": close - float(fields[9]),
                })
            except ValueError:
                continue
        return rows

    async def stock_meta(self, code: str) -> dict[str, Any]:
        normalized = str(code).split(".", 1)[0]
        market = "1" if normalized.startswith(("5", "6", "9")) else "0"
        payload = await self._get_json(
            self.QUOTE_URL,
            {
                "secid": f"{market}.{normalized}",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fields": "f57,f58,f127,f128",
            },
        )
        data = payload.get("data") or {}
        name = str(data.get("f58") or "").strip()
        industry = str(data.get("f127") or "").strip()
        if not name:
            raise FreeMarketError(f"{normalized} 单票名称缺失")
        return {"code": normalized, "name": name, "industry": industry, "source": "东方财富单票行情"}
