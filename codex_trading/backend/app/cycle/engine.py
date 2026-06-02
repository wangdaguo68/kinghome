from __future__ import annotations

from app.data.schemas import CycleState, CycleTag, MarketDay


def moving_average(values: list[int], end_index: int, window: int) -> float:
    start = max(0, end_index - window + 1)
    sample = values[start : end_index + 1]
    return sum(sample) / len(sample)


def trend(values: list[float]) -> str:
    if len(values) < 2:
        return "flat"
    if values[-1] > values[-2]:
        return "up"
    if values[-1] < values[-2]:
        return "down"
    return "flat"


def classify_cycle(red_count: int, ma3: float, ma5: float, ma3_trend: str, ma5_trend: str) -> CycleTag:
    if red_count <= 1000 and ma5 < 2000:
        return CycleTag.ICE_POINT
    if red_count >= 4000 and ma5 >= 2300:
        return CycleTag.CLIMAX
    if ma5_trend == "up" and ma3_trend == "up" and ma5 < 2300:
        return CycleTag.TURN_UP
    if ma5_trend == "up":
        return CycleTag.MAIN_RALLY
    if ma5_trend == "down" and ma3_trend == "down" and ma5 > 2300:
        return CycleTag.TURN_DOWN
    if ma5_trend == "down":
        return CycleTag.DOWNTREND
    if 800 <= ma5 < 2000:
        return CycleTag.LOW_SHAKE
    return CycleTag.HIGH_SHAKE


def build_cycle_states(days: list[MarketDay]) -> list[CycleState]:
    red_counts = [day.red_count for day in days]
    ma3_values: list[float] = []
    ma5_values: list[float] = []
    states: list[CycleState] = []
    for index, day in enumerate(days):
        ma3 = moving_average(red_counts, index, 3)
        ma5 = moving_average(red_counts, index, 5)
        ma3_values.append(ma3)
        ma5_values.append(ma5)
        ma3_trend = trend(ma3_values)
        ma5_trend = trend(ma5_values)
        states.append(
            CycleState(
                trade_date=day.trade_date,
                red_count=day.red_count,
                limit_up_count=day.limit_up_count,
                limit_down_count=day.limit_down_count,
                ma3=round(ma3, 2),
                ma5=round(ma5, 2),
                ma3_trend=ma3_trend,
                ma5_trend=ma5_trend,
                tag=classify_cycle(day.red_count, ma3, ma5, ma3_trend, ma5_trend),
                down_count=day.down_count,
                turnover_billion=day.turnover_billion,
                sh_turnover_billion=day.sh_turnover_billion,
                sz_turnover_billion=day.sz_turnover_billion,
            )
        )
    return states
