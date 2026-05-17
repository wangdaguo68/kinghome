from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class PipelineContext:
    topic: str
    params: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    task_id: str = field(default_factory=lambda: uuid4().hex[:12])

    def log(self, msg: str) -> None:
        self.logs.append(msg)
