# no future annotations so pydantic evaluates types without evaluating 'list' as class attribute

import typing
from typing import Any, Optional, Union
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.types import InitPhaseInput, TodoOperation, TodoParams

TODO_DESCRIPTION = """Tasks identified by verbatim content, NEVER generated IDs (task-1). Unique, stable task/phase names; lost text: view, NEVER guess.
Before work, init for 3+ steps, requested task sets, or new instructions. MUST list EVERY user item separately (phased/numbered/bulleted/N); NEVER omit or remember leftovers.
After successful mutation: no active means earliest pending starts (phase order); multiple active means only earliest stays. Blocked NEVER starts automatically; unblock returns pending. Done out of order may rewind pointer but NEVER reopen completed. Mark done immediately; follow phase order.
External waits (user/agent/service): block with optional reason suppresses stop reminder, starts next pending. Unblock when actionable; append a clearing task for agent-actionable blocker.
NEVER call todo alone: init with first work; done/start with next action."""


class InitPhaseSchema(BaseModel):
    phase: str = Field(description="Name of the phase")
    items: list[str] = Field(description="Tasks in this phase")


class TodoInputSchema(BaseModel):
    op: TodoOperation = Field(description="The operation to perform")
    list: Optional[typing.List[InitPhaseSchema]] = Field(default=None, description="phases for init")
    task: Optional[str] = Field(default=None, description="verbatim task content")
    phase: Optional[str] = Field(default=None, description="phase name")
    items: Optional[typing.List[str]] = Field(default=None, description="tasks for flat init or append")
    reason: Optional[str] = Field(default=None, description="blocker note for block")


def get_todo_tool(tracker: TodoTracker) -> BaseTool:
    @tool(args_schema=TodoInputSchema, description=TODO_DESCRIPTION)
    def todo(
        op: TodoOperation,
        list: Optional[list[Union[InitPhaseSchema, dict[str, Any]]]] = None,
        task: Optional[str] = None,
        phase: Optional[str] = None,
        items: Optional[list[str]] = None,
        reason: Optional[str] = None,
    ) -> str:
        # Convert raw dicts or InitPhaseSchema in list to InitPhaseInput
        parsed_list: Optional[list[InitPhaseInput]] = None
        if list:
            parsed_list = []
            for p in list:
                if isinstance(p, InitPhaseSchema):
                    parsed_list.append(InitPhaseInput(phase=p.phase, items=p.items))
                elif isinstance(p, dict):
                    parsed_list.append(InitPhaseInput(phase=p["phase"], items=p["items"]))

        params = TodoParams(
            op=op,
            list=parsed_list,
            task=task,
            phase=phase,
            items=items,
            reason=reason,
        )
        summary, _ = tracker.execute_op(params)
        return summary

    return todo
