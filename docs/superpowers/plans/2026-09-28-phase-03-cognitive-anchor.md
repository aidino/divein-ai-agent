# Phase 3: Cognitive Anchor (Task Planning & Context Compaction) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng phân hệ Cognitive Anchor cho `dino-coding` gồm máy trạng thái lập kế hoạch `todo` phân cấp với 9 atomic operations, chuyển đổi Markdown hai chiều, `TodoMiddleware` tích hợp vòng lặp nhắc nhở (mutation nudge & completion guard), và tái sử dụng `SummarizationMiddleware` có sẵn của `deepagents` để nén ngữ cảnh.

**Architecture:** Thiết kế theo mô hình Hybrid phân lớp: lớp dưới là State Machine thuần túy (`engine.py`) và Serializer (`markdown.py`) không side-effects; lớp giữa là `TodoTracker` in-memory quản lý phiên với defensive copying; lớp trên cùng là `TodoMiddleware` kế thừa `AgentMiddleware` chuẩn của LangChain/DeepAgents, tiêm tool `todo` 9 ops, đồng bộ `state["todos"]`, và điều phối vòng lặp nhắc nhở.

**Tech Stack:** Python 3.12, `langchain-core`, `langchain`, `deepagents`, `pydantic`, `pytest`, `rich`.

**Spec:** `docs/superpowers/specs/2026-09-28-phase-03-cognitive-anchor-design.md`

## Global Constraints

- Toàn bộ code triển khai nằm trong package `dino-coding/src/dino_coding/tools/todo/`.
- Không phụ thuộc vào thư viện bên ngoài mới ngoài những gì đã có trong virtualenv (`langchain`, `deepagents`, `pydantic`, `rich`).
- Tuyệt đối bảo toàn 594 test hiện hành của dự án (0 regression).
- Lưu trữ in-memory theo phiên (session memory), không ép ghi tự động ra đĩa `workspace/TODO.md`.
- Trạng thái `todo` áp dụng defensive copying (`deepcopy`) để triệt tiêu lỗi chia sẻ tham chiếu ngoài ý muốn.
- Mọi chuỗi thông báo hướng dẫn model giữ tiếng Anh chuẩn `oh-my-pi`; tài liệu tutorial và giao diện Rich dùng tiếng Việt.

---

### Task 1: Core Types & Data Contracts (`todo/types.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/types.py`
- Test: `dino-coding/tests/test_todo_types.py`

**Interfaces:**
- Produces:
  - `TodoStatus = Literal["pending", "in_progress", "completed", "abandoned", "blocked"]`
  - `TodoOperation = Literal["init", "start", "done", "rm", "drop", "block", "unblock", "append", "view"]`
  - `TodoItem(content: str, status: TodoStatus, blocker: Optional[str])`
  - `TodoPhase(name: str, tasks: list[TodoItem])`
  - `InitPhaseInput(phase: str, items: list[str])`
  - `TodoParams(op: TodoOperation, list: Optional[list[InitPhaseInput]], task: Optional[str], phase: Optional[str], items: Optional[list[str]], reason: Optional[str])`

- [ ] **Step 1: Write the failing test**

```python
# dino-coding/tests/test_todo_types.py
import pytest
from dino_coding.tools.todo.types import (
    TodoItem,
    TodoPhase,
    InitPhaseInput,
    TodoParams,
)


def test_todo_item_creation_defaults():
    item = TodoItem(content="Khảo sát mã nguồn")
    assert item.content == "Khảo sát mã nguồn"
    assert item.status == "pending"
    assert item.blocker is None


def test_todo_phase_with_items():
    item1 = TodoItem(content="Task 1", status="completed")
    item2 = TodoItem(content="Task 2", status="blocked", blocker="chờ review")
    phase = TodoPhase(name="Khảo sát", tasks=[item1, item2])
    assert phase.name == "Khảo sát"
    assert len(phase.tasks) == 2
    assert phase.tasks[1].blocker == "chờ review"


def test_todo_params_schema():
    params = TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1", "T2"])])
    assert params.op == "init"
    assert params.list is not None
    assert len(params.list) == 1
    assert params.list[0].items == ["T1", "T2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dino_coding.tools.todo'`

- [ ] **Step 3: Implement minimal code**

```python
# dino-coding/src/dino_coding/tools/todo/types.py
from dataclasses import dataclass, field
from typing import Literal, Optional

TodoStatus = Literal["pending", "in_progress", "completed", "abandoned", "blocked"]
TodoOperation = Literal[
    "init", "start", "done", "rm", "drop", "block", "unblock", "append", "view"
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_types.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/types.py dino-coding/tests/test_todo_types.py
git commit -m "feat(todo): add core types and data contracts"
```

---

### Task 2: Pure Functional State Machine Engine (`todo/engine.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/engine.py`
- Test: `dino-coding/tests/test_todo_engine.py`

**Interfaces:**
- Consumes: `TodoItem`, `TodoPhase`, `TodoParams`, `InitPhaseInput` from `todo/types.py`
- Produces:
  - `clone_phases(phases: list[TodoPhase]) -> list[TodoPhase]`
  - `find_task_by_content(phases: list[TodoPhase], content: str) -> Optional[tuple[TodoItem, TodoPhase]]`
  - `normalize_in_progress(phases: list[TodoPhase]) -> None`
  - `apply_ops(current_phases: list[TodoPhase], entry: TodoParams) -> tuple[list[TodoPhase], list[str]]`
  - `format_summary(phases: list[TodoPhase], errors: list[str], read_only: bool = False) -> str`

- [ ] **Step 1: Write the failing tests for 9 operations and invariants**

```python
# dino-coding/tests/test_todo_engine.py
import pytest
from dino_coding.tools.todo.types import TodoParams, InitPhaseInput
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


def test_init_rejects_duplicate_phase_or_task():
    params = TodoParams(
        op="init",
        list=[
            InitPhaseInput(phase="P1", items=["Task A", "Task A"]),
        ],
    )
    phases, errors = apply_ops([], params)
    assert len(errors) == 1
    assert "Duplicate task" in errors[0]


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dino_coding.tools.todo.engine'`

- [ ] **Step 3: Implement minimal code in `engine.py`**

```python
# dino-coding/src/dino_coding/tools/todo/engine.py
import re
from typing import Optional
from dino_coding.tools.todo.types import (
    InitPhaseInput,
    TodoItem,
    TodoParams,
    TodoPhase,
)

DEFAULT_INIT_PHASE = "Tasks"


def clone_task(task: TodoItem) -> TodoItem:
    return TodoItem(content=task.content, status=task.status, blocker=task.blocker)


def clone_phases(phases: list[TodoPhase]) -> list[TodoPhase]:
    return [
        TodoPhase(name=phase.name, tasks=[clone_task(t) for t in phase.tasks])
        for phase in phases
    ]


def find_task_by_content(
    phases: list[TodoPhase], content: str
) -> Optional[tuple[TodoItem, TodoPhase]]:
    for phase in phases:
        for task in phase.tasks:
            if task.content == content:
                return task, phase
    return None


def find_phase_by_name(phases: list[TodoPhase], name: str) -> Optional[TodoPhase]:
    for phase in phases:
        if phase.name == name:
            return phase
    return None


def normalize_in_progress(phases: list[TodoPhase]) -> None:
    ordered_tasks = [task for phase in phases for task in phase.tasks]
    if not ordered_tasks:
        return

    in_progress_tasks = [t for t in ordered_tasks if t.status == "in_progress"]
    if len(in_progress_tasks) > 1:
        for task in in_progress_tasks[1:]:
            task.status = "pending"

    if in_progress_tasks:
        return

    first_pending = next((t for t in ordered_tasks if t.status == "pending"), None)
    if first_pending:
        first_pending.status = "in_progress"


def resolve_task_or_error(
    phases: list[TodoPhase], content: Optional[str], errors: list[str]
) -> Optional[tuple[TodoItem, TodoPhase]]:
    if not content:
        errors.append("Missing task content")
        return None
    hit = find_task_by_content(phases, content)
    if not hit:
        if re.match(r"^task-\d+$", content):
            errors.append(
                f'Task "{content}" not found. Tasks are referenced by content, '
                "not by IDs — pass the task's full text from the previous result."
            )
        else:
            total_tasks = sum(len(p.tasks) for p in phases)
            hint = " (todo list is empty — was it replaced or not yet created?)" if total_tasks == 0 else ""
            errors.append(f'Task "{content}" not found{hint}')
        return None
    return hit


def resolve_phase_or_error(
    phases: list[TodoPhase], name: Optional[str], errors: list[str]
) -> Optional[TodoPhase]:
    if not name:
        errors.append("Missing phase name")
        return None
    phase = find_phase_by_name(phases, name)
    if not phase:
        errors.append(f'Phase "{name}" not found')
        return None
    return phase


def get_task_targets(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoItem]:
    if entry.task:
        hit = resolve_task_or_error(phases, entry.task, errors)
        return [hit[0]] if hit else []
    if entry.phase:
        phase = resolve_phase_or_error(phases, entry.phase, errors)
        return list(phase.tasks) if phase else []
    return [task for phase in phases for task in phase.tasks]


def init_phases(entry: TodoParams, errors: list[str]) -> list[TodoPhase]:
    raw_list = entry.list
    if not raw_list and entry.items:
        raw_list = [InitPhaseInput(phase=entry.phase or DEFAULT_INIT_PHASE, items=entry.items)]
    if not raw_list:
        errors.append("Missing list for init operation")
        return []

    seen_phases: set[str] = set()
    seen_tasks: set[str] = set()
    result: list[TodoPhase] = []

    for list_entry in raw_list:
        if list_entry.phase in seen_phases:
            errors.append(f'Duplicate phase "{list_entry.phase}" in init list')
        seen_phases.add(list_entry.phase)

        phase_tasks: list[TodoItem] = []
        for content in list_entry.items:
            if content in seen_tasks:
                errors.append(f'Duplicate task "{content}" in init list')
            seen_tasks.add(content)
            phase_tasks.append(TodoItem(content=content, status="pending"))
        result.append(TodoPhase(name=list_entry.phase, tasks=phase_tasks))
    return result


def append_items(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    if not entry.phase:
        errors.append("Missing phase name for append operation")
        return phases
    if not entry.items:
        errors.append("Missing items for append operation")
        return phases

    seen: set[str] = set()
    has_duplicate = False
    for content in entry.items:
        if content in seen or find_task_by_content(phases, content):
            errors.append(f'Task "{content}" already exists')
            has_duplicate = True
        seen.add(content)

    if has_duplicate:
        return phases

    phase = find_phase_by_name(phases, entry.phase)
    if not phase:
        phase = TodoPhase(name=entry.phase, tasks=[])
        phases.append(phase)

    for content in entry.items:
        phase.tasks.append(TodoItem(content=content, status="pending"))
    return phases


def remove_tasks(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    if entry.task:
        hit = resolve_task_or_error(phases, entry.task, errors)
        if not hit:
            return phases
        task, phase = hit
        phase.tasks = [t for t in phase.tasks if t != task]
        return phases
    if entry.phase:
        phase = resolve_phase_or_error(phases, entry.phase, errors)
        if not phase:
            return phases
        phase.tasks = []
        return phases
    for p in phases:
        p.tasks = []
    return phases


def apply_entry(
    phases: list[TodoPhase], entry: TodoParams, errors: list[str]
) -> list[TodoPhase]:
    op = entry.op
    if op == "init":
        return init_phases(entry, errors)
    elif op == "start":
        hit = resolve_task_or_error(phases, entry.task, errors)
        if not hit:
            return phases
        target_task, _ = hit
        for phase in phases:
            for candidate in phase.tasks:
                if candidate.status == "in_progress" and candidate != target_task:
                    candidate.status = "pending"
        target_task.status = "in_progress"
        return phases
    elif op == "done":
        for task in get_task_targets(phases, entry, errors):
            task.status = "completed"
        return phases
    elif op == "drop":
        for task in get_task_targets(phases, entry, errors):
            task.status = "abandoned"
        return phases
    elif op == "block":
        if not entry.task and not entry.phase:
            errors.append("block requires a task or phase target")
            return phases
        reason = re.sub(r"\s+", " ", entry.reason.strip()) if entry.reason else None
        for task in get_task_targets(phases, entry, errors):
            if task.status not in ("pending", "in_progress", "blocked"):
                continue
            task.status = "blocked"
            task.blocker = reason
        return phases
    elif op == "unblock":
        if not entry.task and not entry.phase:
            errors.append("unblock requires a task or phase target")
            return phases
        for task in get_task_targets(phases, entry, errors):
            if task.status == "blocked":
                task.status = "pending"
                task.blocker = None
        return phases
    elif op == "rm":
        return remove_tasks(phases, entry, errors)
    elif op == "append":
        return append_items(phases, entry, errors)
    elif op == "view":
        return phases
    else:
        errors.append(f'Unknown operation "{op}"')
        return phases


def apply_ops(
    current_phases: list[TodoPhase], entry: TodoParams
) -> tuple[list[TodoPhase], list[str]]:
    errors: list[str] = []
    next_phases = clone_phases(current_phases)
    next_phases = apply_entry(next_phases, entry, errors)
    if not errors and entry.op != "view":
        normalize_in_progress(next_phases)
    return next_phases, errors


def format_summary(phases: list[TodoPhase], errors: list[str], read_only: bool = False) -> str:
    if errors:
        return "Errors encountered:\n" + "\n".join(f"- {e}" for e in errors)
    if not phases:
        return "Todo list is empty."

    all_tasks = [t for p in phases for t in p.tasks]
    if not all_tasks:
        return "Todo list is empty."

    closed_all = sum(1 for t in all_tasks if t.status in ("completed", "abandoned"))
    blocked_all = sum(1 for t in all_tasks if t.status == "blocked")
    open_all = len(all_tasks) - closed_all

    # Locate earliest phase with open tasks
    current_idx = 0
    for idx, p in enumerate(phases):
        if any(t.status not in ("completed", "abandoned") for t in p.tasks):
            current_idx = idx
            break

    current = phases[current_idx]
    done_current = sum(1 for t in current.tasks if t.status in ("completed", "abandoned"))

    lines: list[str] = []
    blocked_suffix = f", {blocked_all} blocked" if blocked_all > 0 else ""
    lines.append(f"Overall: {closed_all}/{len(all_tasks)} done, {open_all} open{blocked_suffix}.")
    lines.append(f'Active phase {current_idx + 1}/{len(phases)} "{current.name}" ({done_current}/{len(current.tasks)}).')

    for phase in phases:
        lines.append(f"  {phase.name}:")
        for task in phase.tasks:
            checkbox = "[X]" if task.status == "completed" else "[ ]"
            tag = ""
            if task.status == "in_progress":
                tag = " (in progress)"
            elif task.status == "abandoned":
                tag = " (dropped)"
            elif task.status == "blocked":
                tag = f" (blocked: {task.blocker})" if task.blocker else " (blocked)"
            lines.append(f"    - {checkbox} {task.content}{tag}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_engine.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/engine.py dino-coding/tests/test_todo_engine.py
git commit -m "feat(todo): implement pure functional state machine engine"
```

---

### Task 3: Markdown Round-Trip Serialization (`todo/markdown.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/markdown.py`
- Test: `dino-coding/tests/test_todo_markdown.py`

**Interfaces:**
- Consumes: `TodoItem`, `TodoPhase`, `TodoStatus` from `todo/types.py`
- Produces:
  - `phases_to_markdown(phases: list[TodoPhase]) -> str`
  - `markdown_to_phases(md: str) -> tuple[list[TodoPhase], list[str]]`

- [ ] **Step 1: Write the failing test**

```python
# dino-coding/tests/test_todo_markdown.py
import pytest
from dino_coding.tools.todo.types import TodoItem, TodoPhase
from dino_coding.tools.todo.markdown import phases_to_markdown, markdown_to_phases


def test_markdown_round_trip_preserves_phases_and_blockers():
    original = [
        TodoPhase(
            name="Khảo sát",
            tasks=[
                TodoItem(content="Task 1", status="completed"),
                TodoItem(content="Task 2", status="in_progress"),
            ],
        ),
        TodoPhase(
            name="Triển khai",
            tasks=[
                TodoItem(content="Task 3", status="blocked", blocker="chờ database"),
                TodoItem(content="Task 4", status="abandoned"),
                TodoItem(content="Task 5", status="pending"),
            ],
        ),
    ]

    md = phases_to_markdown(original)
    assert "# Khảo sát" in md
    assert "- [x] Task 1" in md
    assert "- [/] Task 2" in md
    assert "# Triển khai" in md
    assert "- [!] Task 3 <!-- blocker: chờ database -->" in md
    assert "- [-] Task 4" in md
    assert "- [ ] Task 5" in md

    parsed, errors = markdown_to_phases(md)
    assert not errors
    assert len(parsed) == 2
    assert parsed[0].name == "Khảo sát"
    assert parsed[0].tasks[0].status == "completed"
    assert parsed[0].tasks[1].status == "in_progress"
    assert parsed[1].tasks[0].status == "blocked"
    assert parsed[1].tasks[0].blocker == "chờ database"
    assert parsed[1].tasks[1].status == "abandoned"
    assert parsed[1].tasks[2].status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_markdown.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dino_coding.tools.todo.markdown'`

- [ ] **Step 3: Implement minimal code in `markdown.py`**

```python
# dino-coding/src/dino_coding/tools/todo/markdown.py
import re
from dino_coding.tools.todo.types import TodoItem, TodoPhase, TodoStatus

STATUS_TO_MARKER: dict[TodoStatus, str] = {
    "pending": " ",
    "in_progress": "/",
    "completed": "x",
    "abandoned": "-",
    "blocked": "!",
}

MARKER_TO_STATUS: dict[str, TodoStatus] = {
    " ": "pending",
    "": "pending",
    "x": "completed",
    "X": "completed",
    "/": "in_progress",
    ">": "in_progress",
    "-": "abandoned",
    "~": "abandoned",
    "!": "blocked",
}


def phases_to_markdown(phases: list[TodoPhase]) -> str:
    if not phases:
        return "# Todos\n"
    out: list[str] = []
    for i, phase in enumerate(phases):
        if i > 0:
            out.append("")
        out.append(f"# {phase.name}")
        for task in phase.tasks:
            marker = STATUS_TO_MARKER.get(task.status, " ")
            blocker_note = (
                f" <!-- blocker: {task.blocker} -->"
                if task.status == "blocked" and task.blocker
                else ""
            )
            out.append(f"- [{marker}] {task.content}{blocker_note}")
    return "\n".join(out) + "\n"


def markdown_to_phases(md: str) -> tuple[list[TodoPhase], list[str]]:
    errors: list[str] = []
    phases: list[TodoPhase] = []
    current_phase: TodoPhase | None = None

    lines = md.splitlines()
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", trimmed)
        if heading_match:
            current_phase = TodoPhase(name=heading_match.group(1).strip(), tasks=[])
            phases.append(current_phase)
            continue

        task_match = re.match(r"^[-*+]\s*\\?\[(.?)\\?\]\s+(.+?)\s*$", trimmed)
        if task_match:
            marker = task_match.group(1)
            raw_content = task_match.group(2)
            status = MARKER_TO_STATUS.get(marker, "pending")

            blocker: str | None = None
            content = raw_content
            blocker_match = re.search(r"\s*<!--\s*blocker:\s*(.+?)\s*-->\s*$", raw_content)
            if blocker_match:
                blocker = blocker_match.group(1).strip()
                content = raw_content[:blocker_match.start()].strip()

            if not current_phase:
                current_phase = TodoPhase(name="Tasks", tasks=[])
                phases.append(current_phase)

            current_phase.tasks.append(
                TodoItem(content=content, status=status, blocker=blocker)
            )

    return phases, errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_markdown.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/markdown.py dino-coding/tests/test_todo_markdown.py
git commit -m "feat(todo): implement bidirectional Markdown checklist serializer"
```

---

### Task 4: In-Memory Session Tracker (`todo/tracker.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/tracker.py`
- Test: `dino-coding/tests/test_todo_tracker.py`

**Interfaces:**
- Consumes: `TodoPhase`, `TodoParams` from `types.py`; `apply_ops`, `format_summary` from `engine.py`; `phases_to_markdown`, `markdown_to_phases` from `markdown.py`
- Produces:
  - `TodoTracker`:
    - `phases: list[TodoPhase]` (property returning deep copy)
    - `set_phases(phases: list[TodoPhase]) -> None`
    - `execute_op(params: TodoParams) -> tuple[str, bool]` (returns summary and is_error)
    - `to_markdown() -> str`
    - `from_markdown(md: str) -> list[str]`
    - `reset() -> None`

- [ ] **Step 1: Write the failing test**

```python
# dino-coding/tests/test_todo_tracker.py
import pytest
from dino_coding.tools.todo.types import TodoParams, InitPhaseInput
from dino_coding.tools.todo.tracker import TodoTracker


def test_tracker_defensive_cloning():
    tracker = TodoTracker()
    tracker.execute_op(
        TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1"])])
    )
    phases = tracker.phases
    # Mutating returned object must not mutate internal state
    phases[0].tasks[0].status = "completed"
    assert tracker.phases[0].tasks[0].status == "in_progress"


def test_tracker_rollback_on_error():
    tracker = TodoTracker()
    tracker.execute_op(
        TodoParams(op="init", list=[InitPhaseInput(phase="P1", items=["T1"])])
    )
    # Attempt duplicate append
    summary, is_error = tracker.execute_op(
        TodoParams(op="append", phase="P1", items=["T1"])
    )
    assert is_error
    assert "already exists" in summary
    # Previous state retained
    assert len(tracker.phases[0].tasks) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_tracker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dino_coding.tools.todo.tracker'`

- [ ] **Step 3: Implement minimal code in `tracker.py`**

```python
# dino-coding/src/dino_coding/tools/todo/tracker.py
from copy import deepcopy
from dino_coding.tools.todo.engine import apply_ops, clone_phases, format_summary
from dino_coding.tools.todo.markdown import markdown_to_phases, phases_to_markdown
from dino_coding.tools.todo.types import TodoParams, TodoPhase


class TodoTracker:
    """Manages in-memory todo state for a session with defensive copying."""

    def __init__(self) -> None:
        self._phases: list[TodoPhase] = []

    @property
    def phases(self) -> list[TodoPhase]:
        return clone_phases(self._phases)

    def set_phases(self, phases: list[TodoPhase]) -> None:
        self._phases = clone_phases(phases)

    def execute_op(self, params: TodoParams) -> tuple[str, bool]:
        read_only = params.op == "view"
        updated, errors = apply_ops(self._phases, params)
        if errors:
            summary = format_summary(self._phases, errors)
            return summary, True

        if not read_only:
            self._phases = updated

        summary = format_summary(self._phases, [])
        return summary, False

    def to_markdown(self) -> str:
        return phases_to_markdown(self._phases)

    def from_markdown(self, md: str) -> list[str]:
        phases, errors = markdown_to_phases(md)
        if not errors:
            self._phases = phases
        return errors

    def reset(self) -> None:
        self._phases = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_tracker.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/tracker.py dino-coding/tests/test_todo_tracker.py
git commit -m "feat(todo): implement in-memory TodoTracker with defensive cloning"
```

---

### Task 5: LangChain @tool `todo` & Module Wiring (`todo/tool.py`, `todo/__init__.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/tool.py`
- Create: `dino-coding/src/dino_coding/tools/todo/__init__.py`
- Test: `dino-coding/tests/test_todo_tool.py`

**Interfaces:**
- Consumes: `TodoTracker` from `tracker.py`, `TodoParams`, `InitPhaseInput` from `types.py`
- Produces:
  - `get_todo_tool(tracker: TodoTracker) -> BaseTool`: Creates `@tool def todo(...)` bound to the tracker
  - Package exports in `dino_coding.tools.todo`

- [ ] **Step 1: Write the failing test**

```python
# dino-coding/tests/test_todo_tool.py
import pytest
from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.tool import get_todo_tool


def test_todo_tool_invocations():
    tracker = TodoTracker()
    todo_tool = get_todo_tool(tracker)

    # 1. init
    res = todo_tool.invoke({
        "op": "init",
        "list": [{"phase": "P1", "items": ["T1", "T2"]}],
    })
    assert "Overall: 0/2 done" in res
    assert "- [ ] T1 (in progress)" in res

    # 2. done
    res2 = todo_tool.invoke({"op": "done", "task": "T1"})
    assert "Overall: 1/2 done" in res2
    assert "- [X] T1" in res2
    assert "- [ ] T2 (in progress)" in res2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_tool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dino_coding.tools.todo.tool'`

- [ ] **Step 3: Implement minimal code in `tool.py` and `__init__.py`**

```python
# dino-coding/src/dino_coding/tools/todo/tool.py
from typing import Any, Literal, Optional
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
    list: Optional[list[InitPhaseSchema]] = Field(default=None, description="phases for init")
    task: Optional[str] = Field(default=None, description="verbatim task content")
    phase: Optional[str] = Field(default=None, description="phase name")
    items: Optional[list[str]] = Field(default=None, description="tasks for flat init or append")
    reason: Optional[str] = Field(default=None, description="blocker note for block")


def get_todo_tool(tracker: TodoTracker) -> BaseTool:
    @tool(args_schema=TodoInputSchema, description=TODO_DESCRIPTION)
    def todo(
        op: TodoOperation,
        list: Optional[list[dict[str, Any]]] = None,
        task: Optional[str] = None,
        phase: Optional[str] = None,
        items: Optional[list[str]] = None,
        reason: Optional[str] = None,
    ) -> str:
        # Convert raw dicts in list to InitPhaseInput
        parsed_list: Optional[list[InitPhaseInput]] = None
        if list:
            parsed_list = [
                InitPhaseInput(phase=p["phase"], items=p["items"]) for p in list
            ]

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
```

```python
# dino-coding/src/dino_coding/tools/todo/__init__.py
from dino_coding.tools.todo.types import (
    TodoItem,
    TodoPhase,
    TodoStatus,
    TodoOperation,
    TodoParams,
    InitPhaseInput,
)
from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.tool import get_todo_tool, TODO_DESCRIPTION

__all__ = [
    "TodoItem",
    "TodoPhase",
    "TodoStatus",
    "TodoOperation",
    "TodoParams",
    "InitPhaseInput",
    "TodoTracker",
    "get_todo_tool",
    "TODO_DESCRIPTION",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_tool.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/tool.py dino-coding/src/dino_coding/tools/todo/__init__.py dino-coding/tests/test_todo_tool.py
git commit -m "feat(todo): add LangChain @tool todo and package exports"
```

---

### Task 6: TodoMiddleware & Todo Reminder Loop (`todo/middleware.py`)

**Files:**
- Create: `dino-coding/src/dino_coding/tools/todo/middleware.py`
- Modify: `dino-coding/src/dino_coding/tools/todo/__init__.py`
- Test: `dino-coding/tests/test_todo_middleware.py`

**Interfaces:**
- Consumes: `TodoTracker` from `tracker.py`, `get_todo_tool` from `tool.py`
- Produces: `TodoMiddleware(AgentMiddleware)` with mutation nudge and completion reminder

- [ ] **Step 1: Write the failing test**

```python
# dino-coding/tests/test_todo_middleware.py
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.middleware import TodoMiddleware, MUTATING_TOOLS


def test_todo_middleware_tracks_mutations():
    tracker = TodoTracker()
    mw = TodoMiddleware(tracker=tracker)

    # Simulating tool calls
    assert mw.consecutive_mutations == 0
    mw.record_tool_call("edit")
    mw.record_tool_call("write")
    assert mw.consecutive_mutations == 2

    # A todo tool call resets the mutation counter
    mw.record_tool_call("todo")
    assert mw.consecutive_mutations == 0


def test_todo_middleware_nudge_threshold():
    tracker = TodoTracker()
    mw = TodoMiddleware(tracker=tracker, mutation_threshold=3)
    for _ in range(3):
        mw.record_tool_call("edit")
    assert mw.should_nudge()
    nudge_msg = mw.consume_nudge()
    assert nudge_msg is not None
    assert "chưa cập nhật tiến độ" in nudge_msg
    # Max nudges reached
    assert not mw.should_nudge()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dino-coding && uv run pytest tests/test_todo_middleware.py -v`
Expected: FAIL with `ImportError: cannot import name 'TodoMiddleware'`

- [ ] **Step 3: Implement minimal code in `middleware.py`**

```python
# dino-coding/src/dino_coding/tools/todo/middleware.py
from collections.abc import Callable
from typing import Any, Optional
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage

from dino_coding.tools.todo.tool import get_todo_tool
from dino_coding.tools.todo.tracker import TodoTracker

MUTATING_TOOLS: frozenset[str] = frozenset({"edit", "write", "ast_edit", "execute"})
DEFAULT_MUTATION_THRESHOLD = 12
DEFAULT_MAX_NUDGES_PER_PROMPT = 2


class TodoMiddleware(AgentMiddleware[Any, Any, Any]):
    """Middleware managing Todo state synchronization, tool injection, and reminder loop."""

    def __init__(
        self,
        tracker: Optional[TodoTracker] = None,
        mutation_threshold: int = DEFAULT_MUTATION_THRESHOLD,
        max_nudges_per_prompt: int = DEFAULT_MAX_NUDGES_PER_PROMPT,
    ) -> None:
        super().__init__()
        self.tracker = tracker or TodoTracker()
        self.mutation_threshold = mutation_threshold
        self.max_nudges_per_prompt = max_nudges_per_prompt
        self.consecutive_mutations = 0
        self.nudges_sent = 0

        # Inject todo tool into agent tools
        self.tools = [get_todo_tool(self.tracker)]

    def record_tool_call(self, tool_name: str) -> None:
        if tool_name == "todo":
            self.consecutive_mutations = 0
        elif tool_name in MUTATING_TOOLS:
            self.consecutive_mutations += 1

    def should_nudge(self) -> bool:
        return (
            self.consecutive_mutations >= self.mutation_threshold
            and self.nudges_sent < self.max_nudges_per_prompt
        )

    def consume_nudge(self) -> Optional[str]:
        if not self.should_nudge():
            return None
        self.nudges_sent += 1
        self.consecutive_mutations = 0
        return (
            "System reminder: Bạn đã thực hiện nhiều thao tác sửa code liên tiếp mà "
            "chưa cập nhật tiến độ. Hãy dùng `todo` để cập nhật checklist."
        )

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any] | AIMessage:
        # Check if previous turn had tool calls
        messages = request.messages
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    self.record_tool_call(tc.get("name", ""))

        # Inject nudge if needed
        nudge = self.consume_nudge()
        if nudge:
            request = request.override(
                messages=[*request.messages, SystemMessage(content=nudge)]
            )

        response = handler(request)

        # Inspect response for tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                self.record_tool_call(tc.get("name", ""))

        return response
```

Update `dino-coding/src/dino_coding/tools/todo/__init__.py` to export `TodoMiddleware`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dino-coding && uv run pytest tests/test_todo_middleware.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/tools/todo/middleware.py dino-coding/src/dino_coding/tools/todo/__init__.py dino-coding/tests/test_todo_middleware.py
git commit -m "feat(todo): implement TodoMiddleware with mutation nudge loop"
```

---

### Task 7: System Prompt & Agent Wiring (`prompt.py`, `agent.py`)

**Files:**
- Modify: `dino-coding/src/dino_coding/prompt.py`
- Modify: `dino-coding/src/dino_coding/agent.py`
- Test: `cd dino-coding && uv run pytest tests/ -q`

**Interfaces:**
- Consumes: `TodoMiddleware` from `dino_coding.tools.todo`
- Produces: Updated `create_my_coding_agent()` equipped with `TodoMiddleware` and updated system prompt.

- [ ] **Step 1: Update `prompt.py` to add section 5 TASK PLANNING**

Add `## 5. TASK PLANNING & PROGRESS TRACKING` with exact instructions on 9 ops, verbatim matching, auto-advancement, and never using fake task IDs.

- [ ] **Step 2: Update `agent.py` to plug `TodoMiddleware`**

Wire `TodoMiddleware` into `create_my_coding_agent(middleware=[todo_middleware])`.

- [ ] **Step 3: Run full pytest suite to verify no regressions**

Run: `cd dino-coding && uv run pytest tests/ -q`
Expected: PASS (all 594+ tests pass)

- [ ] **Step 4: Run ruff check**

Run: `cd dino-coding && uvx ruff check src tests --select F,E9`
Expected: "All checks passed!"

- [ ] **Step 5: Commit**

```bash
git add dino-coding/src/dino_coding/prompt.py dino-coding/src/dino_coding/agent.py
git commit -m "feat(agent): wire TodoMiddleware and system prompt into coding agent"
```

---

### Task 8: Demo Script & Acceptance Script (`scripts/demo_todo.py`, `scripts/acceptance_phase3.py`)

**Files:**
- Create: `dino-coding/scripts/demo_todo.py`
- Create: `dino-coding/scripts/acceptance_phase3.py`

**Interfaces:**
- `demo_todo.py`: Pure engine demonstration in Rich console showing 9 ops and Markdown round-trip.
- `acceptance_phase3.py`: E2E script simulating a realistic multi-step coding task with blockers, unblocking, and progress validation.

- [ ] **Step 1: Implement `scripts/demo_todo.py`**

Demonstrate 5 steps:
1. `init` with hierarchical phases
2. `start` and `done` with auto-advance pointer
3. `block` with reason & auto-advance to next pending
4. `unblock` and complete
5. Markdown export and import

- [ ] **Step 2: Implement `scripts/acceptance_phase3.py`**

Simulate 7 steps:
1. Agent inits 3-phase checklist for refactoring
2. First task completed, verify auto-advance
3. Third task blocked due to external dependency
4. Out-of-order task completed in later phase
5. Unblock and resolve
6. Final verification: all tasks completed, 0 open
7. Self-checking assertions exit code 0

- [ ] **Step 3: Run both scripts to verify clean execution**

Run: `cd dino-coding && uv run python scripts/demo_todo.py && uv run python scripts/acceptance_phase3.py`
Expected: Clean Rich output, all assertions PASS, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add dino-coding/scripts/demo_todo.py dino-coding/scripts/acceptance_phase3.py
git commit -m "feat(scripts): add Phase 3 demo and E2E acceptance scripts"
```

---

### Task 9: Tutorial Documentation (`build-coding-agent-tutorial/phase_03_task_planning.md`) & PROGRESS Sync

**Files:**
- Create: `build-coding-agent-tutorial/phase_03_task_planning.md`
- Modify: `build-coding-agent-tutorial/PROGRESS.md`

- [ ] **Step 1: Write `phase_03_task_planning.md`**

Follow the established standard:
- §1: Lý thuyết Chuyên sâu: Cognitive Anchors trong AI Agent (Task Drift, Context Window vs Cognitive Load).
- §2: Kiến trúc Hybrid: DeepAgents Summarization + oh-my-pi Todo State Machine.
- §3: Máy trạng thái 9 Operations & Markdown Round-Trip.
- §4: Triển khai Từng Module (types, engine, markdown, tracker, tool, middleware).
- §5: Bộ Test Suite & Kịch bản Nghiệm thu.
- §6: Bảng Defer & Checklist Nghiệm thu.

- [ ] **Step 2: Update `PROGRESS.md`**

Update Phase 3 status and add Quyết định 23 (kiến trúc Hybrid Cognitive Anchor).

- [ ] **Step 3: Commit**

```bash
git add build-coding-agent-tutorial/phase_03_task_planning.md build-coding-agent-tutorial/PROGRESS.md
git commit -m "docs: add Phase 3 tutorial document and update PROGRESS.md"
```
