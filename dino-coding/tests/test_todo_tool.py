from __future__ import annotations

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo import (
    get_todo_tool,
    TODO_DESCRIPTION,
    TodoTracker as ExportedTodoTracker,
    TodoItem,
    TodoPhase,
    TodoStatus,
    TodoOperation,
    TodoParams,
    InitPhaseInput,
)
from dino_coding.tools.todo.tool import InitPhaseSchema, TodoInputSchema


def test_todo_tool_init_hierarchical_and_exports() -> None:
    assert ExportedTodoTracker is TodoTracker
    assert TodoItem is not None
    assert TodoPhase is not None
    assert TodoStatus is not None
    assert TodoOperation is not None
    assert TodoParams is not None
    assert InitPhaseInput is not None

    tracker = TodoTracker()
    todo_tool = get_todo_tool(tracker)

    assert todo_tool.name == "todo"
    assert todo_tool.description == TODO_DESCRIPTION
    assert todo_tool.args_schema == TodoInputSchema

    # Hierarchical init via tool invocation
    res = todo_tool.invoke({
        "op": "init",
        "list": [
            {"phase": "Phase 1", "items": ["Task A", "Task B"]},
            {"phase": "Phase 2", "items": ["Task C"]},
        ],
    })

    assert "Phase 1" in res
    assert "Task A (in progress)" in res
    assert "Task B" in res
    assert "Phase 2" in res
    assert "Task C" in res
    assert len(tracker.phases) == 2


def test_todo_tool_init_flat() -> None:
    tracker = TodoTracker()
    todo_tool = get_todo_tool(tracker)

    res = todo_tool.invoke({
        "op": "init",
        "items": ["Flat 1", "Flat 2"],
    })

    assert "Flat 1 (in progress)" in res
    assert "Flat 2" in res
    assert len(tracker.phases) == 1
    assert tracker.phases[0].name == "Tasks"


def test_todo_tool_done_block_unblock() -> None:
    tracker = TodoTracker()
    todo_tool = get_todo_tool(tracker)

    # Init
    todo_tool.invoke({
        "op": "init",
        "items": ["Task 1", "Task 2"],
    })

    # Block Task 1 with reason
    res_block = todo_tool.invoke({
        "op": "block",
        "task": "Task 1",
        "reason": "waiting for api key",
    })
    assert "Task 1 (blocked: waiting for api key)" in res_block
    # Task 2 auto-advanced
    assert "Task 2 (in progress)" in res_block

    # Unblock Task 1
    res_unblock = todo_tool.invoke({
        "op": "unblock",
        "task": "Task 1",
    })
    # Task 1 becomes pending, Task 2 still in_progress
    assert "Task 1\n" in res_unblock or "- [ ] Task 1" in res_unblock
    assert "Task 1 (blocked" not in res_unblock
    assert "Task 2 (in progress)" in res_unblock

    # Done Task 2
    res_done = todo_tool.invoke({
        "op": "done",
        "task": "Task 2",
    })
    assert "- [X] Task 2" in res_done
    # Task 1 auto-advanced to in_progress
    assert "Task 1 (in progress)" in res_done


def test_todo_tool_schema_validation() -> None:
    schema = TodoInputSchema(
        op="init",
        list=[InitPhaseSchema(phase="P1", items=["I1"])],
    )
    assert schema.op == "init"
    assert schema.list is not None
    assert schema.list[0].phase == "P1"
    assert schema.list[0].items == ["I1"]
