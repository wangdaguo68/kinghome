from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.data.schemas import StockBar
from app.notify.feishu import FeishuNotifier


ROOT = Path(__file__).resolve().parents[3]
TRACK_FILE = ROOT / "cache" / "signal_tracks.json"
_TRACK_LOCK = threading.RLock()


def sync_tomorrow_signals(plan: dict[str, Any], notifier: FeishuNotifier | None = None) -> dict[str, object]:
    notifier = notifier or FeishuNotifier()
    tracks = _read_tracks()
    existing_ids = {track["id"] for track in tracks}
    new_count = 0
    sent_count = 0
    errors: list[str] = []

    for preset in plan.get("plans", []):
        if not preset.get("version_eligible"):
            continue
        for signal in preset.get("signals", []):
            track_id = _track_id(str(preset.get("id", "")), signal)
            if track_id in existing_ids:
                continue
            track = _new_track(track_id, preset, signal)
            tracks.append(track)
            existing_ids.add(track_id)
            new_count += 1
            try:
                result = notifier.send_text(format_buy_signal(track))
                track["last_notice"] = result
                if result.get("sent"):
                    sent_count += 1
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                track["last_notice"] = {"sent": False, "reason": message}
                errors.append(message)

    _write_tracks(tracks)
    return {"new_count": new_count, "sent_count": sent_count, "errors": errors, "tracks": tracks}


def sync_intraday_signals(scan: dict[str, Any], notifier: FeishuNotifier | None = None) -> dict[str, object]:
    notifier = notifier or FeishuNotifier()
    tracks = _read_tracks()
    existing_ids = {track["id"] for track in tracks}
    new_count = 0
    sent_count = 0
    errors: list[str] = []

    for signal in scan.get("signals", []):
        track_id = _intraday_track_id(signal)
        if track_id in existing_ids:
            continue
        track = _new_intraday_track(track_id, signal)
        tracks.append(track)
        existing_ids.add(track_id)
        new_count += 1
        try:
            result = notifier.send_text(format_intraday_signal(track))
            track["last_notice"] = result
            if result.get("sent"):
                sent_count += 1
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            track["last_notice"] = {"sent": False, "reason": message}
            errors.append(message)

    _write_tracks(tracks)
    return {"new_count": new_count, "sent_count": sent_count, "errors": errors, "tracks": tracks}


def refresh_tracking(stock_bars: list[StockBar], notifier: FeishuNotifier | None = None) -> dict[str, object]:
    notifier = notifier or FeishuNotifier()
    tracks = _read_tracks()
    latest_by_symbol = _latest_bars(stock_bars)
    changed = 0
    sent_count = 0
    for track in tracks:
        if track.get("status") not in {"watching", "notified", "intraday_notified"}:
            continue
        bar = latest_by_symbol.get(str(track.get("symbol", "")))
        if bar is None:
            continue
        status_before = track.get("status")
        _apply_bar(track, bar)
        if track.get("status") != status_before:
            changed += 1
            try:
                result = notifier.send_text(format_exit_signal(track))
                track["last_notice"] = result
                if result.get("sent"):
                    sent_count += 1
            except Exception as exc:  # noqa: BLE001
                track["last_notice"] = {"sent": False, "reason": str(exc)}

    _write_tracks(tracks)
    return {"changed_count": changed, "sent_count": sent_count, "tracks": tracks}


def tracked_signals() -> dict[str, object]:
    tracks = _read_tracks()
    active = [track for track in tracks if track.get("status") in {"watching", "notified", "intraday_notified"}]
    closed = [track for track in tracks if track.get("status") not in {"watching", "notified", "intraday_notified"}]
    return {"active_count": len(active), "closed_count": len(closed), "tracks": tracks}


def format_buy_signal(track: dict[str, Any]) -> str:
    return "\n".join(
        [
            "【量化买入信号】",
            f"策略维度：{track.get('preset_name')} / {track.get('version_id')}",
            f"代码：{track.get('symbol')}  {track.get('name')}",
            f"模式：{track.get('pattern')}",
            f"信号日：{track.get('signal_date')}，计划买入日：{track.get('planned_entry_date') or '待确认'}",
            f"参考价：{track.get('reference_price')}，计划仓位：{track.get('planned_position_pct')}%",
            f"止损：{track.get('stop_loss_pct')}%，止盈观察：{track.get('take_profit_pct')}%",
            f"执行策略：{track.get('execution_rule')}",
        ]
    )


def format_intraday_signal(track: dict[str, Any]) -> str:
    return "\n".join(
        [
            "【盘中买点提醒】",
            f"代码：{track.get('symbol')}  {track.get('name')}",
            f"触发：{track.get('trigger')} / {track.get('pattern')}",
            f"价格：{track.get('reference_price')}，涨幅：{track.get('trigger_pct')}%",
            f"成交额：{track.get('amount_billion')} 亿，强度排名：{track.get('sector_rank')}",
            f"计划仓位：{track.get('planned_position_pct')}%，硬止损：{track.get('stop_loss_pct')}%",
            f"执行策略：{track.get('execution_rule')}",
            "提醒：当前只做人工确认，不会自动下单。",
        ]
    )


def format_exit_signal(track: dict[str, Any]) -> str:
    return "\n".join(
        [
            "【量化跟踪结束】",
            f"代码：{track.get('symbol')}  {track.get('name')}",
            f"状态：{status_text(str(track.get('status')))}",
            f"最近价：{track.get('last_price')}，跟踪收益：{track.get('last_pnl_pct')}%",
            f"原因：{track.get('exit_reason')}",
        ]
    )


def status_text(status: str) -> str:
    return {
        "notified": "已提醒",
        "watching": "跟踪中",
        "take_profit": "止盈",
        "stop_loss": "止损",
        "time_exit": "时间退出",
        "intraday_notified": "盘中已提醒",
    }.get(status, status)


def _new_track(track_id: str, preset: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": track_id,
        "status": "notified",
        "created_at": now,
        "updated_at": now,
        "preset_id": preset.get("id"),
        "preset_name": preset.get("name"),
        "version_id": preset.get("version_id"),
        "signal_date": signal.get("signal_date"),
        "planned_entry_date": signal.get("planned_entry_date"),
        "symbol": signal.get("symbol"),
        "name": signal.get("name"),
        "pattern": signal.get("pattern"),
        "cycle_tag": signal.get("cycle_tag"),
        "reference_price": signal.get("close_price"),
        "last_price": signal.get("close_price"),
        "last_pnl_pct": 0,
        "max_pnl_pct": 0,
        "min_pnl_pct": 0,
        "planned_position_pct": signal.get("planned_position_pct"),
        "stop_loss_pct": signal.get("stop_loss_pct"),
        "take_profit_pct": float(os.getenv("TRACK_TAKE_PROFIT_PCT", "8")),
        "execution_rule": signal.get("execution_rule"),
        "reason": signal.get("reason"),
        "exit_reason": "",
    }


def _new_intraday_track(track_id: str, signal: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": track_id,
        "status": "intraday_notified",
        "created_at": now,
        "updated_at": now,
        "preset_id": "intraday",
        "preset_name": "盘中雷达",
        "version_id": str(signal.get("source", "")),
        "signal_date": str(signal.get("scanned_at", ""))[:10],
        "planned_entry_date": str(signal.get("scanned_at", ""))[:10],
        "symbol": signal.get("symbol"),
        "name": signal.get("name"),
        "pattern": signal.get("pattern"),
        "trigger": signal.get("trigger"),
        "cycle_tag": signal.get("cycle_tag"),
        "reference_price": signal.get("price"),
        "last_price": signal.get("price"),
        "trigger_pct": signal.get("pct"),
        "last_pnl_pct": 0,
        "max_pnl_pct": 0,
        "min_pnl_pct": 0,
        "amount_billion": signal.get("amount_billion"),
        "sector_rank": signal.get("sector_rank"),
        "planned_position_pct": signal.get("planned_position_pct"),
        "stop_loss_pct": signal.get("stop_loss_pct"),
        "take_profit_pct": float(os.getenv("TRACK_TAKE_PROFIT_PCT", "8")),
        "execution_rule": signal.get("execution_rule"),
        "reason": signal.get("trigger"),
        "exit_reason": "",
    }


def _apply_bar(track: dict[str, Any], bar: StockBar) -> None:
    reference = float(track.get("reference_price") or 0)
    if reference <= 0:
        return
    close_pnl = round((bar.close_price / reference - 1) * 100, 2)
    high_pnl = round((bar.high_price / reference - 1) * 100, 2)
    low_pnl = round((bar.low_price / reference - 1) * 100, 2)
    track["last_price"] = bar.close_price
    track["last_pnl_pct"] = close_pnl
    track["max_pnl_pct"] = max(float(track.get("max_pnl_pct", 0)), high_pnl)
    track["min_pnl_pct"] = min(float(track.get("min_pnl_pct", 0)), low_pnl)
    track["updated_at"] = datetime.now().isoformat(timespec="seconds")

    if low_pnl <= float(track.get("stop_loss_pct", -5)):
        track["status"] = "stop_loss"
        track["exit_reason"] = "盘中触发硬止损"
    elif high_pnl >= float(track.get("take_profit_pct", 8)):
        track["status"] = "take_profit"
        track["exit_reason"] = "盘中触发止盈观察线"
    elif _should_time_exit(str(track.get("signal_date", "")), bar.trade_date):
        track["status"] = "time_exit"
        track["exit_reason"] = "超过两日跟踪窗口，按策略时间退出"
    else:
        track["status"] = "watching"


def _should_time_exit(signal_date: str, latest_date: date) -> bool:
    try:
        start = date.fromisoformat(signal_date)
    except ValueError:
        return False
    return (latest_date - start).days >= 5


def _latest_bars(stock_bars: list[StockBar]) -> dict[str, StockBar]:
    latest: dict[str, StockBar] = {}
    for bar in stock_bars:
        current = latest.get(bar.symbol)
        if current is None or bar.trade_date > current.trade_date:
            latest[bar.symbol] = bar
    return latest


def _track_id(preset_id: str, signal: dict[str, Any]) -> str:
    return "|".join(
        [
            preset_id,
            str(signal.get("signal_date", "")),
            str(signal.get("planned_entry_date", "")),
            str(signal.get("symbol", "")),
            str(signal.get("pattern", "")),
        ]
    )


def _intraday_track_id(signal: dict[str, Any]) -> str:
    return "|".join(
        [
            "intraday",
            str(signal.get("scanned_at", ""))[:10],
            str(signal.get("symbol", "")),
            str(signal.get("pattern", "")),
        ]
    )


def _read_tracks() -> list[dict[str, Any]]:
    with _TRACK_LOCK:
        try:
            data = json.loads(TRACK_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
    return data if isinstance(data, list) else []


def _write_tracks(tracks: list[dict[str, Any]]) -> None:
    TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(tracks, ensure_ascii=False, indent=2, default=str)
    temp_path = TRACK_FILE.with_name(f"{TRACK_FILE.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with _TRACK_LOCK:
        temp_path.write_text(data, encoding="utf-8")
        temp_path.replace(TRACK_FILE)
