import pytest
from dino_coding.tools.todo.types import TodoParams, InitPhaseInput, TodoPhase, TodoItem
from dino_coding.tools.todo.engine import apply_ops, format_summary


def test_init_hierarchical_auto_advances_first_task():
    params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["Task A", "Task B"]),
            InitPhaseInput(phase="P2", items=["Task C"]),
        ],
    )
    phases, errors = apply_ops([], params)
    assert not errors
    assert len(phases) == 2
    # Invariant: first task of first phase becomes in_progress
    assert phases[0].tasks[0].status == "in_progress"
    assert phases[0].tasks[1].status == "pending"
    assert phases[1].tasks[0].status == "pending"


def test_init_flat_items_uses_default_phase():
    params = TodoParams(
        op="init",
        items=["Task 1", "Task 2"],
    )
    phases, errors = apply_ops([], params)
    assert not errors
    assert len(phases) == 1
    assert phases[0].name == "Tasks"
    assert phases[0].tasks[0].status == "in_progress"
    assert phases[0].tasks[1].status == "pending"


def test_init_rejects_duplicate_phase_or_task():
    # Duplicate task in same phase
    params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["Task A", "Task A"]),
        ],
    )
    phases, errors = apply_ops([], params)
    assert len(errors) == 1
    assert "Duplicate task" in errors[0]

    # Duplicate phase
    params2 = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["Task A"]),
            InitPhaseInput(phase="P1", items=["Task B"]),
        ],
    )
    phases2, errors2 = apply_ops([], params2)
    assert len(errors2) == 1
    assert "Duplicate phase" in errors2[0]


def test_start_promotes_task_and_demotes_existing():
    init_params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["T1", "T2"]),
        ],
    )
    phases, _ = apply_ops([], init_params)
    assert phases[0].tasks[0].status == "in_progress"
    assert phases[0].tasks[1].status == "pending"

    start_params = TodoParams(op="start", task="T2")
    phases, errors = apply_ops(phases, start_params)
    assert not errors
    assert phases[0].tasks[0].status == "pending"
    assert phases[0].tasks[1].status == "in_progress"


def test_done_auto_advances_to_earliest_pending():
    init_params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["T1", "T2"]),
            InitPhaseInput(phase="P2", items=["T3"]),
        ],
    )
    phases, _ = apply_ops([], init_params)
    assert phases[0].tasks[0].status == "in_progress"

    done_params = TodoParams(op="done", task="T1")
    phases, errors = apply_ops(phases, done_params)
    assert not errors
    assert phases[0].tasks[0].status == "completed"
    assert phases[0].tasks[1].status == "in_progress"


def test_drop_marks_abandoned():
    init_params = TodoParams(
        op="init",
        list=[InitPhaseInput(phase="P1", items=["T1", "T2"])],
    )
    phases, _ = apply_ops([], init_params)
    drop_params = TodoParams(op="drop", task="T1")
    phases, errors = apply_ops(phases, drop_params)
    assert not errors
    assert phases[0].tasks[0].status == "abandoned"
    assert phases[0].tasks[1].status == "in_progress"


def test_block_requires_reason_and_leaves_completed_intact():
    init_params = TodoParams(
        op="init",
        list=[InitPhaseInput(phase="P1", items=["T1", "T2"])],
    )
    phases, _ = apply_ops([], init_params)
    # T1 is in_progress, mark it blocked
    block_params = TodoParams(op="block", task="T1", reason="Waiting for API key\nwith extra spaces")
    phases, errors = apply_ops(phases, block_params)
    assert not errors
    assert phases[0].tasks[0].status == "blocked"
    assert phases[0].tasks[0].blocker == "Waiting for API key with extra spaces"
    # Auto-advanced to T2
    assert phases[0].tasks[1].status == "in_progress"


def test_unblock_resets_status_and_clears_blocker():
    init_params = TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1"])])
    phases, _ = apply_ops([], init_params)
    phases, _ = apply_ops(phases, TodoParams(op="block", task="T1", reason="Test"))
    assert phases[0].tasks[0].status == "blocked"

    phases, errors = apply_ops(phases, TodoParams(op="unblock", task="T1"))
    assert not errors
    assert phases[0].tasks[0].status == "in_progress"
    assert phases[0].tasks[0].blocker is None


def test_task_id_reference_error_hint():
    init_params = TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1"])])
    phases, _ = apply_ops([], init_params)
    _, errors = apply_ops(phases, TodoParams(op="done", task="task-1"))
    assert len(errors) == 1
    assert "Tasks are referenced by content, not by IDs" in errors[0]


def test_append_adds_items_and_rejects_duplicates():
    init_params = TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1"])])
    phases, _ = apply_ops([], init_params)

    # Append duplicate
    phases, errors = apply_ops(phases, TodoParams(op="append", phase="P1", items=["T1"]))
    assert len(errors) == 1
    assert 'Task "T1" already exists' in errors[0]

    # Append new items to existing phase
    phases, errors = apply_ops(phases, TodoParams(op="append", phase="P1", items=["T2"]))
    assert not errors
    assert len(phases[0].tasks) == 2
    assert phases[0].tasks[1].content == "T2"

    # Append to new phase
    phases, errors = apply_ops(phases, TodoParams(op="append", phase="P2", items=["T3"]))
    assert not errors
    assert len(phases) == 2
    assert phases[1].name == "P2"
    assert phases[1].tasks[0].content == "T3"


def test_rm_operation():
    init_params = TodoParams(
        op="init",
        list=[InitPhaseInput(phase="P1", items=["T1", "T2"])],
    )
    phases, _ = apply_ops([], init_params)
    phases, errors = apply_ops(phases, TodoParams(op="rm", task="T1"))
    assert not errors
    assert len(phases[0].tasks) == 1
    assert phases[0].tasks[0].content == "T2"
    assert phases[0].tasks[0].status == "in_progress"


def test_view_operation_does_not_mutate():
    init_params = TodoParams(
        op="init",
        list=[InitPhaseInput(phase="P1", items=["T1"])],
    )
    phases, _ = apply_ops([], init_params)
    phases2, errors = apply_ops(phases, TodoParams(op="view"))
    assert not errors
    assert phases2 == phases


def test_format_summary_structure():
    init_params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="Khảo sát", items=["Đọc spec", "Viết test"]),
            InitPhaseInput(phase="Code", items=["Triển khai"]),
        ],
    )
    phases, _ = apply_ops([], init_params)
    summary = format_summary(phases, [])
    assert "Overall: 0/3 done, 3 open" in summary
    assert 'Active phase 1/2 "Khảo sát"' in summary
    assert "- [ ] Đọc spec (in progress)" in summary


def test_format_summary_empty_and_errors():
    assert format_summary([], []) == "Todo list is empty."
    err_summary = format_summary([], ["Something went wrong"])
    assert "Errors encountered:\n- Something went wrong" in err_summary
