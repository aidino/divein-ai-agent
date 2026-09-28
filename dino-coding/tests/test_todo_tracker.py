import pytest
from dino_coding.tools.todo.types import TodoParams, TodoPhase, TodoItem
from dino_coding.tools.todo.tracker import TodoTracker


def test_initial_state_empty():
    tracker = TodoTracker()
    assert tracker.phases == []
    assert tracker.to_markdown() == "# Todos\n"


def test_defensive_cloning_phases_property():
    tracker = TodoTracker()
    tracker.set_phases([TodoPhase(name="Phase 1", tasks=[TodoItem(content="Task 1", status="pending")])])
    
    phases = tracker.phases
    assert len(phases) == 1
    # Mutating returned list should not affect tracker
    phases.append(TodoPhase(name="Phase 2", tasks=[]))
    assert len(tracker.phases) == 1

    # Mutating task inside returned phase should not affect tracker
    phases[0].tasks[0].status = "completed"
    phases[0].tasks.append(TodoItem(content="Task 2", status="pending"))
    assert tracker.phases[0].tasks[0].status == "pending"
    assert len(tracker.phases[0].tasks) == 1


def test_defensive_cloning_set_phases():
    tracker = TodoTracker()
    input_phases = [TodoPhase(name="Phase 1", tasks=[TodoItem(content="Task 1", status="pending")])]
    tracker.set_phases(input_phases)

    # Mutating external list or items should not affect tracker
    input_phases.append(TodoPhase(name="Phase 2", tasks=[]))
    input_phases[0].tasks[0].status = "completed"

    assert len(tracker.phases) == 1
    assert tracker.phases[0].tasks[0].status == "pending"


def test_execute_op_lifecycle():
    tracker = TodoTracker()
    
    # 1. init
    summary, err = tracker.execute_op(TodoParams(op="init", items=["Task 1", "Task 2"]))
    assert not err
    assert "Task 1" in summary
    assert len(tracker.phases) == 1
    assert tracker.phases[0].tasks[0].status == "in_progress"
    assert tracker.phases[0].tasks[1].status == "pending"

    # 2. done (first task done, second task auto-advances to in_progress)
    summary, err = tracker.execute_op(TodoParams(op="done", task="Task 1"))
    assert not err
    assert tracker.phases[0].tasks[0].status == "completed"
    assert tracker.phases[0].tasks[1].status == "in_progress"

    # 3. view (read-only op)
    summary, err = tracker.execute_op(TodoParams(op="view"))
    assert not err
    assert "Task 1" in summary
    assert "Task 2" in summary


def test_execute_op_rollback_on_error():
    tracker = TodoTracker()
    tracker.execute_op(TodoParams(op="init", items=["Task 1"]))
    assert tracker.phases[0].tasks[0].status == "in_progress"

    # Invalid op: e.g. unknown task
    summary, err = tracker.execute_op(TodoParams(op="start", task="NonExistent"))
    assert err is True
    assert "not found" in summary.lower() or "error" in summary.lower()
    
    # Internal state remains unchanged
    assert len(tracker.phases) == 1
    assert tracker.phases[0].tasks[0].content == "Task 1"
    assert tracker.phases[0].tasks[0].status == "in_progress"


def test_markdown_export_and_import():
    tracker = TodoTracker()
    tracker.execute_op(TodoParams(op="init", items=["Task A", "Task B"]))
    md = tracker.to_markdown()
    assert "# Tasks" in md
    assert "[/] Task A" in md
    assert "[ ] Task B" in md

    # Import into a new tracker
    new_tracker = TodoTracker()
    errors = new_tracker.from_markdown(md)
    assert not errors
    assert len(new_tracker.phases) == 1
    assert new_tracker.phases[0].tasks[0].content == "Task A"
    assert new_tracker.phases[0].tasks[0].status == "in_progress"
    assert new_tracker.phases[0].tasks[1].content == "Task B"
    assert new_tracker.phases[0].tasks[1].status == "pending"


def test_from_markdown_error_does_not_corrupt_state():
    tracker = TodoTracker()
    tracker.execute_op(TodoParams(op="init", items=["Original Task"]))
    
    # Invalid markdown with unknown status marker e.g. [?]
    invalid_md = "# Tasks\n- [?] Unknown status task\n"
    errors = tracker.from_markdown(invalid_md)
    assert errors
    # State should remain original
    assert len(tracker.phases) == 1
    assert tracker.phases[0].tasks[0].content == "Original Task"


def test_reset():
    tracker = TodoTracker()
    tracker.execute_op(TodoParams(op="init", items=["Task 1"]))
    assert len(tracker.phases) == 1

    tracker.reset()
    assert tracker.phases == []
    assert tracker.to_markdown() == "# Todos\n"
