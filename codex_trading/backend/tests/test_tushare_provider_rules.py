from datetime import date

from app.data import tushare_provider
from app.data.tushare_provider import (
    TushareError,
    fetch_recent_market_data,
    next_open_date,
    _is_limit_down,
    _is_limit_down_count,
    _is_limit_up,
    _is_limit_up_touch,
    _is_hs_market_symbol,
    _is_tradeable_symbol,
)


def test_tradeable_symbol_excludes_star_market_bj_and_st() -> None:
    assert _is_tradeable_symbol("600000.SH", "浦发银行")
    assert _is_tradeable_symbol("002123.SZ", "梦网科技")
    assert _is_tradeable_symbol("300001.SZ", "特锐德")
    assert not _is_tradeable_symbol("688001.SH", "华兴源创")
    assert not _is_tradeable_symbol("830000.BJ", "北交所样本")
    assert not _is_tradeable_symbol("002000.SZ", "*ST样本")
    assert not _is_tradeable_symbol("002000.SZ", "")


def test_limit_up_requires_board_specific_close_limit() -> None:
    assert _is_limit_up("600000.SH", "浦发银行", 10.00, 11.00, 11.00)
    assert not _is_limit_up("600000.SH", "浦发银行", 10.00, 11.00, 10.99)
    assert _is_limit_up("300001.SZ", "特锐德", 10.00, 12.00, 12.00)
    assert not _is_limit_up("300001.SZ", "特锐德", 10.00, 11.99, 11.99)


def test_limit_down_uses_board_specific_close_limit() -> None:
    assert _is_limit_down("600000.SH", "浦发银行", 10.00, 9.00, 9.00)
    assert not _is_limit_down("600000.SH", "浦发银行", 10.00, 9.00, 9.01)
    assert _is_limit_down("300001.SZ", "特锐德", 10.00, 8.00, 8.00)
    assert not _is_limit_down("300001.SZ", "特锐德", 10.00, 8.00, 8.01)


def test_market_stat_limit_counts_match_loose_market_board_thresholds() -> None:
    assert _is_limit_up_touch("600000.SH", "浦发银行", 10.00, 11.00)
    assert _is_limit_up_touch("300001.SZ", "特锐德", 10.00, 12.00)
    assert not _is_limit_up_touch("688783.SH", "西安奕材-U", 33.61, 40.33)
    assert _is_limit_down_count("600000.SH", "浦发银行", -9.5)
    assert _is_limit_down_count("300001.SZ", "特锐德", -19.5)


def test_market_width_uses_hs_a_share_close_limit_counts(monkeypatch) -> None:
    trade_date = date(2026, 6, 1)
    rows = [
        {
            "ts_code": "600001.SH",
            "trade_date": "20260601",
            "open": 10,
            "high": 11,
            "low": 10,
            "close": 11,
            "pre_close": 10,
            "pct_chg": 10,
            "amount": 200000,
        },
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260601",
            "open": 10,
            "high": 11,
            "low": 9.9,
            "close": 10.5,
            "pre_close": 10,
            "pct_chg": 5,
            "amount": 300000,
        },
        {
            "ts_code": "000002.SZ",
            "trade_date": "20260601",
            "open": 10,
            "high": 10,
            "low": 9,
            "close": 9,
            "pre_close": 10,
            "pct_chg": -10,
            "amount": 400000,
        },
        {
            "ts_code": "830000.BJ",
            "trade_date": "20260601",
            "open": 10,
            "high": 13,
            "low": 10,
            "close": 13,
            "pre_close": 10,
            "pct_chg": 30,
            "amount": 500000,
        },
    ]
    names = {
        "600001.SH": "sample sh",
        "000001.SZ": "sample sz touch",
        "000002.SZ": "sample sz down",
        "830000.BJ": "sample bj",
    }

    fetch_recent_market_data.cache_clear()
    monkeypatch.setattr(tushare_provider, "latest_trade_date", lambda: trade_date)
    monkeypatch.setattr(tushare_provider, "recent_open_dates", lambda end_date, count: [trade_date])
    monkeypatch.setattr(tushare_provider, "stock_name_map", lambda: names)
    monkeypatch.setattr(tushare_provider, "_daily_rows", lambda value, connection=None: rows)

    market_days, _ = fetch_recent_market_data(1)

    assert _is_hs_market_symbol("600001.SH")
    assert not _is_hs_market_symbol("830000.BJ")
    assert market_days[0].red_count == 2
    assert market_days[0].down_count == 1
    assert market_days[0].limit_up_count == 1
    assert market_days[0].limit_down_count == 1
    assert market_days[0].turnover_billion == 9
    assert market_days[0].sh_turnover_billion == 2
    assert market_days[0].sz_turnover_billion == 7
    fetch_recent_market_data.cache_clear()


def test_stock_bar_rank_keeps_full_candidate_position(monkeypatch) -> None:
    trade_date = date(2026, 5, 20)
    rows = []
    names = {}
    for index in range(120):
        symbol = f"000{index + 1:03d}.SZ"
        names[symbol] = f"样本{index + 1}"
        rows.append(
            {
                "ts_code": symbol,
                "trade_date": "20260520",
                "open": 10,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "pre_close": 10,
                "pct_chg": 2,
                "amount": 12000000 - index,
            }
        )

    fetch_recent_market_data.cache_clear()
    monkeypatch.setenv("TUSHARE_STOCK_BAR_LIMIT", "120")
    monkeypatch.setattr(tushare_provider, "latest_trade_date", lambda: trade_date)
    monkeypatch.setattr(tushare_provider, "recent_open_dates", lambda end_date, count: [trade_date])
    monkeypatch.setattr(tushare_provider, "stock_name_map", lambda: names)
    monkeypatch.setattr(tushare_provider, "_daily_rows", lambda value, connection=None: rows)

    _, stock_bars = fetch_recent_market_data(1)

    assert len(stock_bars) == 120
    assert stock_bars[-1].sector_rank == 120
    fetch_recent_market_data.cache_clear()


def test_next_open_date_uses_trade_calendar(monkeypatch) -> None:
    next_open_date.cache_clear()
    monkeypatch.setattr(
        tushare_provider,
        "call_tushare",
        lambda *args, **kwargs: {"items": [["20260529", "1"], ["20260601", "1"]]},
    )

    assert next_open_date(date(2026, 5, 28)) == date(2026, 5, 29)
    next_open_date.cache_clear()


def test_next_open_date_falls_back_to_weekday_on_rate_limit(monkeypatch) -> None:
    next_open_date.cache_clear()

    def _raise_rate_limit(*args, **kwargs):
        raise TushareError("频率超限")

    monkeypatch.setattr(tushare_provider, "call_tushare", _raise_rate_limit)

    assert next_open_date(date(2026, 5, 29)) == date(2026, 6, 1)
    next_open_date.cache_clear()


def test_recent_daily_rows_are_not_memory_cached(monkeypatch) -> None:
    trade_date = date.today()
    calls = {"count": 0}

    def _call_tushare(*args, **kwargs):
        calls["count"] += 1
        return {
            "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "amount"],
            "items": [
                [
                    "600001.SH",
                    trade_date.strftime("%Y%m%d"),
                    10,
                    10 + calls["count"],
                    10,
                    10,
                    10,
                    calls["count"],
                    100000,
                ]
            ],
        }

    fetch_recent_market_data.cache_clear()
    monkeypatch.setattr(tushare_provider, "load_daily_rows", lambda value: None)
    monkeypatch.setattr(tushare_provider, "save_daily_rows", lambda value, rows: None)
    monkeypatch.setattr(tushare_provider, "call_tushare", _call_tushare)

    first = tushare_provider._daily_rows(trade_date)
    second = tushare_provider._daily_rows(trade_date)

    assert calls["count"] == 2
    assert first[0]["high"] != second[0]["high"]
    fetch_recent_market_data.cache_clear()


def test_daily_rows_use_mysql_before_tushare(monkeypatch) -> None:
    trade_date = date(2026, 6, 1)
    db_rows = [
        {
            "ts_code": "600001.SH",
            "trade_date": "20260601",
            "open": 10,
            "high": 11,
            "low": 10,
            "close": 11,
            "pre_close": 10,
            "pct_chg": 10,
            "amount": 100000,
        }
    ]

    fetch_recent_market_data.cache_clear()
    monkeypatch.setattr(tushare_provider, "load_daily_rows", lambda value: db_rows)
    monkeypatch.setattr(tushare_provider, "call_tushare", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Tushare should not be called")))

    assert tushare_provider._daily_rows(trade_date) == db_rows
    fetch_recent_market_data.cache_clear()


def test_daily_rows_backfill_mysql_after_tushare(monkeypatch) -> None:
    trade_date = date(2026, 6, 1)
    saved = {}

    def _call_tushare(*args, **kwargs):
        return {
            "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "amount"],
            "items": [["600001.SH", "20260601", 10, 11, 10, 11, 10, 10, 100000]],
        }

    fetch_recent_market_data.cache_clear()
    monkeypatch.setattr(tushare_provider, "load_daily_rows", lambda value: None)
    monkeypatch.setattr(tushare_provider, "call_tushare", _call_tushare)
    monkeypatch.setattr(tushare_provider, "save_daily_rows", lambda value, rows: saved.update({"date": value, "rows": rows}))

    rows = tushare_provider._daily_rows(trade_date)

    assert rows[0]["ts_code"] == "600001.SH"
    assert saved["date"] == trade_date
    assert saved["rows"] == rows
    fetch_recent_market_data.cache_clear()
