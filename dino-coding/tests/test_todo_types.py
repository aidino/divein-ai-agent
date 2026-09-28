from typing import get_args

from dino_coding.tools.todo.types import (
    InitPhaseInput,
    TodoItem,
    TodoOperation,
    TodoParams,
    TodoPhase,
    TodoStatus,
)


def test_todo_status_literals():
    expected = {"pending", "in_progress", "completed", "abandoned", "blocked"}
    assert set(get_args(TodoStatus)) == expected


def test_todo_operation_literals():
    expected = {
        "init",
        "start",
        "done",
        "rm",
        "drop",
        "block",
        "unblock",
        "append",
        "view",
    }
    assert set(get_args(TodoOperation)) == expected


def test_todo_item_creation_and_defaults():
    item = TodoItem(content="Design database schema")
    assert item.content == "Design database schema"
    assert item.status == "pending"
    assert item.blocker is None

    blocked_item = TodoItem(
        content="Deploy to prod",
        status="blocked",
        blocker="Waiting for security review",
    )
    assert blocked_item.status == "blocked"
    assert blocked_item.blocker == "Waiting for security review"


def test_todo_phase_creation_and_defaults():
    phase = TodoPhase(name="Phase 1: Setup")
    assert phase.name == "Phase 1: Setup"
    assert phase.tasks == []

    task1 = TodoItem(content="Task 1")
    task2 = TodoItem(content="Task 2", status="completed")
    phase_with_tasks = TodoPhase(name="Phase 2", tasks=[task1, task2])
    assert len(phase_with_tasks.tasks) == 2
    assert phase_with_tasks.tasks[0].content == "Task 1"
    assert phase_with_tasks.tasks[1].status == "completed"


def test_init_phase_input():
    input_obj = InitPhaseInput(phase="Planning", items=["Item A", "Item B"])
    assert input_obj.phase == "Planning"
    assert input_obj.items == ["Item A", "Item B"]


def test_todo_params_creation_and_defaults():
    params = TodoParams(op="view")
    assert params.op == "view"
    assert params.list is None
    assert params.task is None
    assert params.phase is None
    assert params.items is None
    assert params.reason is None

    init_params = TodoParams(
        op="init",
        list=[InitPhaseInput(phase="P1", items=["Task 1"])],
    )
    assert init_params.op == "init"
    assert init_params.list is not None
    assert len(init_params.list) == 1
    assert init_params.list[0].phase == "P1"

    action_params = TodoParams(
        op="block",
        task="Task 1",
        reason="Blocked by external dependency",
    )
    assert action_params.op == "block"
    assert action_params.task == "Task 1"
    assert action_params.reason == "Blocked by external dependency"
