from __future__ import annotations

from abc import ABC, abstractmethod

from app.data.schemas import CycleState, CycleTag, Signal, StockBar


class Strategy(ABC):
    enabled_cycles: set[CycleTag]

    @abstractmethod
    def generate(self, cycle: CycleState, bars: list[StockBar]) -> list[Signal]:
        raise NotImplementedError

    def generate_with_history(
        self,
        cycle: CycleState,
        bars: list[StockBar],
        history_by_symbol: dict[str, list[StockBar]],
    ) -> list[Signal]:
        return self.generate(cycle, bars)
