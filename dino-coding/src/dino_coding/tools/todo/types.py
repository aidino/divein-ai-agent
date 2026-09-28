from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

TodoStatus = Literal["pending", "in_progress", "completed", "abandoned", "blocked"]

TodoOperation = Literal[
    "init",
    "start",
    "done",
    "rm",
    "drop",
    "block",
    "unblock",
    "append",
    "view",
]


@dataclass
class TodoItem:
    content: str
    status: TodoStatus = "pending"
    blocker: Optional[str] = None


@dataclass
class TodoPhase:
    name: str
    tasks: list[TodoItem] = field(default_factory=list)


@dataclass
class InitPhaseInput:
    phase: str
    items: list[str]


@dataclass
class TodoParams:
    op: TodoOperation
    list: Optional[list[InitPhaseInput]] = None
    task: Optional[str] = None
    phase: Optional[str] = None
    items: Optional[list[str]] = None
    reason: Optional[str] = None
