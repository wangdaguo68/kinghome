from __future__ import annotations

from datetime import date

from app import investment_calendar as calendar
from app.investment_calendar import CalendarEvent


def test_dedupe_merges_same_event_sources_and_keeps_high_impact() -> None:
    events = [
        CalendarEvent(
            date="2026-06-01",
            title="英伟达将在6月1日至4日举办GTC Taipei 2026大会",
            detail="财联社版本",
            category="科技产业",
            market="全球 / 美股",
            impact="high",
            source="财联社",
            tags=["英伟达"],
        ),
        CalendarEvent(
            date="2026-06-01",
            title="英伟达将在6月1日至4日举办GTC Taipei 2026大会",
            detail="同花顺提供的更长事件描述",
            category="科技产业",
            market="A股 / 产业",
            impact="medium",
            source="同花顺",
            tags=["英伟达概念"],
        ),
    ]

    result = calendar._dedupe_events(events)

    assert len(result) == 1
    assert result[0].impact == "high"
    assert result[0].source == "财联社 / 同花顺"
    assert result[0].detail == "同花顺提供的更长事件描述"
    assert result[0].tags == ["英伟达", "英伟达概念"]


def test_month_keys_cover_cross_month_window() -> None:
    assert calendar._month_keys(date(2026, 6, 1), date(2026, 7, 1)) == ["202606", "202607"]


def test_dedupe_merges_long_and_short_same_day_event_titles() -> None:
    events = [
        CalendarEvent(
            date="2026-06-02",
            title="第四届天津国际航运产业博览会将于6月2日至5日举办",
            detail="长标题",
            category="产业会议",
            market="A股",
            impact="medium",
            source="财联社",
        ),
        CalendarEvent(
            date="2026-06-02",
            title="第四届天津国际航运产业博览会",
            detail="短标题",
            category="行业会议",
            market="天津市",
            impact="medium",
            source="东方财富财经日历",
        ),
    ]

    result = calendar._dedupe_events(events)

    assert len(result) == 1
    assert set(result[0].source.split(" / ")) == {"财联社", "东方财富财经日历"}


def test_cls_events_parse_current_shape(monkeypatch) -> None:
    payload = {
        "code": 200,
        "data": [
            {
                "calendar_day": "2026-06-01",
                "items": [
                    {
                        "calendar_time": "2026-06-01 00:00:00",
                        "type": 2,
                        "event": {"title": "美团：董事会定于6月1日举行会议并公布2026年第一季度的未经审核财务业绩", "country": "中国", "star": 5},
                        "title": "美团：董事会定于6月1日举行会议并公布2026年第一季度的未经审核财务业绩",
                    }
                ],
            }
        ],
    }
    monkeypatch.setattr(calendar, "_request_json", lambda *args, **kwargs: payload)

    result = calendar._fetch_cls_events(date(2026, 6, 1), date(2026, 6, 30))

    assert len(result) == 1
    assert result[0].date == "2026-06-01"
    assert result[0].impact == "high"
    assert result[0].source == "财联社"


def test_ths_events_parse_jsonp_shape(monkeypatch) -> None:
    payload = {
        "stat": "ok",
        "data": [
            {
                "date": "2026-06-02",
                "week": "星期二",
                "import": "0",
                "events": [["台北电脑展（Computex 2026）将于6月2日至5日举行", "", "", ""]],
                "concept": [[{"name": "消费电子概念"}]],
                "field": [[]],
                "stocks": [[]],
            }
        ],
    }
    monkeypatch.setattr(calendar, "_request_jsonp", lambda *args, **kwargs: payload)

    result = calendar._fetch_ths_events(date(2026, 6, 1), date(2026, 6, 30))

    assert len(result) == 1
    assert result[0].date == "2026-06-02"
    assert result[0].category == "科技产业"
    assert result[0].tags == ["消费电子概念"]
