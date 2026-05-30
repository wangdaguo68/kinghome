from app.cycle.engine import build_cycle_states, classify_cycle
from app.data.demo import demo_market_days
from app.data.schemas import CycleTag


def test_classifies_ice_point() -> None:
    assert classify_cycle(860, 1450, 1800, "down", "down") == CycleTag.ICE_POINT


def test_classifies_climax() -> None:
    assert classify_cycle(4050, 3100, 2400, "up", "up") == CycleTag.CLIMAX


def test_demo_cycles_include_turn_up() -> None:
    states = build_cycle_states(demo_market_days())
    assert any(state.tag == CycleTag.TURN_UP for state in states)

