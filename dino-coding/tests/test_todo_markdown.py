from dino_coding.tools.todo.markdown import (
    MARKER_TO_STATUS,
    STATUS_TO_MARKER,
    markdown_to_phases,
    phases_to_markdown,
)
from dino_coding.tools.todo.types import TodoItem, TodoPhase


def test_status_marker_mappings():
    assert STATUS_TO_MARKER["pending"] == " "
    assert STATUS_TO_MARKER["in_progress"] == "/"
    assert STATUS_TO_MARKER["completed"] == "x"
    assert STATUS_TO_MARKER["abandoned"] == "-"
    assert STATUS_TO_MARKER["blocked"] == "!"

    assert MARKER_TO_STATUS[" "] == "pending"
    assert MARKER_TO_STATUS[""] == "pending"
    assert MARKER_TO_STATUS["x"] == "completed"
    assert MARKER_TO_STATUS["X"] == "completed"
    assert MARKER_TO_STATUS["/"] == "in_progress"
    assert MARKER_TO_STATUS[">"] == "in_progress"
    assert MARKER_TO_STATUS["-"] == "abandoned"
    assert MARKER_TO_STATUS["~"] == "abandoned"
    assert MARKER_TO_STATUS["!"] == "blocked"


def test_empty_phases_to_markdown():
    assert phases_to_markdown([]) == "# Todos\n"


def test_phases_to_markdown_formatting():
    phases = [
        TodoPhase(
            name="Phase 1: Setup",
            tasks=[
                TodoItem(content="Task A", status="pending"),
                TodoItem(content="Task B", status="in_progress"),
                TodoItem(content="Task C", status="completed"),
                TodoItem(content="Task D", status="abandoned"),
                TodoItem(
                    content="Task E",
                    status="blocked",
                    blocker="waiting for review",
                ),
                TodoItem(
                    content="Task F",
                    status="pending",
                    blocker="should not print comment",
                ),
            ],
        ),
        TodoPhase(
            name="Phase 2: Execution",
            tasks=[
                TodoItem(content="Task G", status="completed"),
            ],
        ),
    ]

    md = phases_to_markdown(phases)
    expected = (
        "# Phase 1: Setup\n"
        "- [ ] Task A\n"
        "- [/] Task B\n"
        "- [x] Task C\n"
        "- [-] Task D\n"
        "- [!] Task E <!-- blocker: waiting for review -->\n"
        "- [ ] Task F\n\n"
        "# Phase 2: Execution\n"
        "- [x] Task G\n"
    )
    assert md == expected


def test_round_trip_preserves_statuses_and_blockers():
    original = [
        TodoPhase(
            name="Architecture",
            tasks=[
                TodoItem(content="Design schema", status="completed"),
                TodoItem(content="Implement storage", status="in_progress"),
                TodoItem(
                    content="Deploy to cluster",
                    status="blocked",
                    blocker="CI credentials expired",
                ),
                TodoItem(content="Legacy cleanup", status="abandoned"),
                TodoItem(content="Write docs", status="pending"),
            ],
        )
    ]

    md = phases_to_markdown(original)
    parsed, errors = markdown_to_phases(md)
    assert errors == []
    assert len(parsed) == 1
    assert parsed[0].name == "Architecture"
    assert len(parsed[0].tasks) == 5

    assert parsed[0].tasks[0] == TodoItem(content="Design schema", status="completed")
    assert parsed[0].tasks[1] == TodoItem(content="Implement storage", status="in_progress")
    assert parsed[0].tasks[2] == TodoItem(
        content="Deploy to cluster",
        status="blocked",
        blocker="CI credentials expired",
    )
    assert parsed[0].tasks[3] == TodoItem(content="Legacy cleanup", status="abandoned")
    assert parsed[0].tasks[4] == TodoItem(content="Write docs", status="pending")


def test_markdown_to_phases_variations_and_escapes():
    md = """
# Getting Started
* [X] Task uppercase X
+ [>] Task alternative in_progress
- [~] Task alternative abandoned
- [] Empty marker pending
- \\[!\\] Escaped brackets with blocker <!-- blocker: missing API key -->
    - [ ] Indented task
"""
    phases, errors = markdown_to_phases(md)
    assert errors == []
    assert len(phases) == 1
    phase = phases[0]
    assert phase.name == "Getting Started"
    assert len(phase.tasks) == 6

    assert phase.tasks[0] == TodoItem(content="Task uppercase X", status="completed")
    assert phase.tasks[1] == TodoItem(content="Task alternative in_progress", status="in_progress")
    assert phase.tasks[2] == TodoItem(content="Task alternative abandoned", status="abandoned")
    assert phase.tasks[3] == TodoItem(content="Empty marker pending", status="pending")
    assert phase.tasks[4] == TodoItem(
        content="Escaped brackets with blocker",
        status="blocked",
        blocker="missing API key",
    )
    assert phase.tasks[5] == TodoItem(content="Indented task", status="pending")


def test_markdown_to_phases_no_headings_defaults_to_tasks():
    md = """
- [ ] Task 1
- [x] Task 2
"""
    phases, errors = markdown_to_phases(md)
    assert errors == []
    assert len(phases) == 1
    assert phases[0].name == "Tasks"
    assert len(phases[0].tasks) == 2
    assert phases[0].tasks[0] == TodoItem(content="Task 1", status="pending")
    assert phases[0].tasks[1] == TodoItem(content="Task 2", status="completed")


def test_markdown_to_phases_tasks_before_and_after_heading():
    md = """
- [ ] Task before heading
# Phase 1
- [x] Task in phase 1
"""
    phases, errors = markdown_to_phases(md)
    assert errors == []
    assert len(phases) == 2
    assert phases[0].name == "Tasks"
    assert len(phases[0].tasks) == 1
    assert phases[0].tasks[0].content == "Task before heading"
    assert phases[1].name == "Phase 1"
    assert len(phases[1].tasks) == 1
    assert phases[1].tasks[0].content == "Task in phase 1"


def test_markdown_to_phases_unknown_marker_generates_error():
    md = """
# Phase
- [?] Unknown marker task
"""
    phases, errors = markdown_to_phases(md)
    assert len(errors) == 1
    assert "Unknown status marker" in errors[0]
    # Still added as pending by default
    assert len(phases) == 1
    assert phases[0].tasks[0].status == "pending"
