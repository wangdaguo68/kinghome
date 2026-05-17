from abc import ABC, abstractmethod

from pipeline.context import PipelineContext


class Step(ABC):
    @abstractmethod
    def run(self, ctx: PipelineContext) -> None:
        ...
