# Phase 3: Cognitive Anchor — Task Planning & Context Compaction

> **Chuỗi tutorial:** [Phase 1](phase_01_hello_agent.md) → [Phase 2](phase_02_file_operations.md) → [Phase 2.5](phase_025_codebase_intelligence.md) → **Bạn đang đây** → Phase 4
>
> **Nguồn tham chiếu từ `oh-my-pi` & `deepagents`:**  
> `packages/coding-agent/src/tools/todo.ts` • `packages/coding-agent/src/prompts/tools/todo.md` • `packages/coding-agent/src/agent/compaction.ts` • `deepagents.middleware.summarization` • `deepagents.create_deep_agent`
>
> **Sản phẩm bàn giao:** Bộ phân hệ **Cognitive Anchor** hoàn chỉnh cho Coding Agent gồm:
> 1. Máy trạng thái quản lý kế hoạch phân cấp (`TodoTracker` & `engine.py`) với **9 thao tác nguyên tử** (`init`, `start`, `done`, `rm`, `drop`, `block`, `unblock`, `append`, `view`), con trỏ tự động chuyển dịch (`auto-advance pointer`) và bất biến duy nhất 1 task active.
> 2. Bộ chuyển đổi Markdown hai chiều (`phases_to_markdown` / `markdown_to_phases`) bảo toàn ghi chú blocker qua comment HTML.
> 3. `TodoMiddleware` kế thừa `AgentMiddleware` chuẩn, tiêm tool `todo` vào agent, giám sát chuỗi đột biến code (Mutation Nudge sau $\ge 12$ thao tác) và cảnh báo task dang dở (Completion Reminder).
> 4. Tái sử dụng `SummarizationMiddleware` có sẵn của `deepagents` để nén context window dài mà không làm mờ mỏ neo nhận thức.

---

## 1. Lý thuyết Chuyên sâu: Cognitive Anchors trong AI Agent

### 1.1 Hiện tượng Task Drift & Cạn kiệt Token Window ở Coding Agent

Trong các tác vụ phần mềm thực tế (ví dụ: *"Khảo sát mã nguồn, di trú schema database, refactor 15 endpoints và viết test hồi quy"*), một Coding Agent phải trải qua hàng chục lượt suy luận (turns) và hàng chục lượt gọi tool đột biến (`edit`, `write`, `ast_edit`).

Khi đó, agent thường đối mặt với hai hội chứng suy sụp nhận thức (cognitive failures):

1. **Task Drift (Mất phương hướng / Rơi rụng nhiệm vụ)**:
   - Sau 10–20 lượt gọi tool sửa file, ngữ cảnh chứa đầy diff, traceback và kết quả đọc file. Model bắt đầu quên mất yêu cầu gốc ban đầu.
   - Hiện tượng **Premature Completion**: Model sửa xong 1 file rồi vội vàng kết luận *"Tôi đã hoàn thành xong nhiệm vụ"* trong khi 14 endpoints còn lại chưa được đụng tới và unit test chưa hề được chạy.
   - Hiện tượng **Looped Edits**: Agent sửa đi sửa lại một file vì không nhớ mình đã hoàn thành bước khảo sát và cần chuyển sang bước kiểm thử.
2. **Cạn kiệt Cửa sổ Ngữ cảnh (Token Exhaustion)**:
   - Context window phình to vượt quá 85–90% dung lượng tối đa. Chi phí mỗi turn tăng theo hàm số mũ, và khả năng chú ý (attention) của mô hình bị suy giảm nghiêm trọng.

Để giải quyết vấn đề này, hệ thống cần một **Cognitive Anchor (Mỏ neo nhận thức)**: một cấu trúc dữ liệu theo dõi tiến độ nhiệm vụ tách biệt khỏi dòng hội thoại, luôn giữ vững mục tiêu dài hạn bất chấp việc ngữ cảnh đàm thoại bị xáo trộn hay nén lại.

---

### 1.2 Tại sao `write_todos` thô sơ của LangChain gây lãng phí token & ảo giác?

Framework LangChain và DeepAgents có cung cấp sẵn `TodoListMiddleware` với công cụ `write_todos(todos: list[Todo])`. Tuy nhiên, trong thực tế xây dựng Coding Agent phức tạp như `oh-my-pi`, thiết kế này bộc lộ những điểm yếu chết người:

```text
LangChain write_todos(todos: [...]):
  - Gửi lại TOÀN BỘ danh sách mỗi khi có một thay đổi nhỏ:
    Turn 1: write_todos([10 items]) -> Model tạo 10 object
    Turn 2: Sửa 1 item -> Model PHẢI gửi lại đủ 10 items!
    Turn 3: Sửa 1 item -> Model lại gửi lại 10 items!
  - Hậu quả: 
    1. Lãng phí Output Tokens gấp nhiều lần (mỗi lần đổi status tốn hàng trăm token).
    2. Model Hallucination: Khi viết lại 10 items, model dễ gõ sai chữ, tự ý bỏ bớt task cũ,
       hoặc đảo lộn thứ tự các bước đã thống nhất.
    3. Không có phân cấp Phase (chỉ là flat list).
    4. Không có khái niệm Blocker (khi bị nghẽn bởi phụ thuộc bên ngoài).
```

### 1.3 Giải pháp của `oh-my-pi`: Máy trạng thái 9 Thao tác Nguyên tử & Auto-Advance

Thay vì bắt mô hình viết lại cả danh sách, `oh-my-pi` (`todo.ts`) xây dựng một **State Machine hướng sự kiện (Delta-based Event-Driven State Machine)** với 9 thao tác nguyên tử:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        9 ATOMIC OPERATIONS                             │
├────────────────────────────────────────────────────────────────────────┤
│ 1. init     : Khởi tạo toàn bộ danh sách Phase và Task                 │
│ 2. start    : Bắt đầu 1 task cụ thể -> gán in_progress                 │
│ 3. done     : Đánh dấu xong 1 task (hoặc cả phase) -> completed        │
│ 4. drop     : Hủy bỏ 1 task (hoặc cả phase) -> abandoned               │
│ 5. block    : Đánh dấu nghẽn kèm lý do -> blocked                      │
│ 6. unblock  : Gỡ nghẽn -> khôi phục pending, xóa blocker note          │
│ 7. append   : Bổ sung thêm các task mới vào 1 phase                    │
│ 8. rm       : Xóa bỏ hoàn toàn 1 task hoặc 1 phase                     │
│ 9. view     : Đọc trạng thái hiện tại (read-only, không đột biến)      │
└────────────────────────────────────────────────────────────────────────┘
```

Điểm đột phá của máy trạng thái này bao gồm:
* **Auto-advance pointer**: Khi một task đang làm (`in_progress`) chuyển sang `completed`, `abandoned` hoặc `blocked`, engine **tự động quét theo thứ tự Phase $\to$ Task để tìm task `pending` đầu tiên và nâng thành `in_progress`**. Model không cần tốn một turn riêng để "start task tiếp theo".
* **Single Active Invariant**: Tại mọi thời điểm, số lượng task `in_progress` luôn là 0 hoặc 1. Không bao giờ xảy ra tình trạng agent "vừa làm việc A vừa làm việc B".
* **Verbatim Content Addressing**: Task được định danh bằng chính nội dung văn bản nguyên văn (`task="Viết unit test"`), tuyệt đối không dùng ID tự bịa (`task-1`, `task-2`). Nếu model gọi ID tự bịa, engine lập tức từ chối và hướng dẫn dùng `op="view"` để lấy lại chuỗi chuẩn xác.
* **Tiết kiệm Token vượt trội**: Mỗi turn cập nhật, model chỉ cần gọi một lệnh ngắn: `todo(op="done", task="Viết unit test")` (chỉ tiêu tốn ~15 tokens thay vì viết lại hàng trăm tokens của toàn bộ checklist).

---

## 2. Kiến trúc Hybrid: DeepAgents Summarization + oh-my-pi Todo State Machine

Thay vì phải tự phát minh lại bánh xe hoặc chấp nhận điểm yếu của LangChain built-in, dự án của chúng ta áp dụng **Kiến trúc Hybrid** tối ưu:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DEEP CODING AGENT                               │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     TodoMiddleware                               │  │
│  │  - Tiêm công cụ `todo` (9 ops) vào danh sách Tools               │  │
│  │  - Lưu giữ TodoTracker (In-Memory Session State)                 │  │
│  │  - Mid-Run Mutation Nudge: Nhắc nhở nếu >= 12 mutating calls     │  │
│  │  - Completion Reminder: Cảnh báo nếu dừng khi còn pending task   │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Điều phối                        │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │             State Machine Core (engine.py / types.py)            │  │
│  │  - 9 Thao tác nguyên tử, Auto-advance pointer                    │  │
│  │  - Verbatim matching, Defensive copy, Rollback khi lỗi          │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │ Chuyển đổi hai chiều             │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                Markdown Serializer (markdown.py)                 │  │
│  │  - Xuất nhập format Markdown checklist tiêu chuẩn                 │  │
│  │  - Lưu blocker trong comment: <!-- blocker: lý do -->            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │      SummarizationMiddleware (Tái sử dụng từ DeepAgents)         │  │
│  │  - Tự động nén conversation context khi đạt ngưỡng token window  │  │
│  │  - Giữ nguyên các mỏ neo nhận thức cho lượt suy luận mới         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hợp đồng Dữ liệu & 9 Thao tác Nguyên tử & Markdown Round-Trip

### 3.1 Data Contracts (`types.py`)

Cấu trúc dữ liệu đại diện cho kế hoạch được chuẩn hóa chặt chẽ qua Python dataclasses:

```python
TodoStatus = Literal["pending", "in_progress", "completed", "abandoned", "blocked"]

TodoOperation = Literal[
    "init", "start", "done", "rm", "drop", "block", "unblock", "append", "view"
]

@dataclass
class TodoItem:
    content: str                          # Nội dung nguyên văn (verbatim), định danh duy nhất
    status: TodoStatus = "pending"        # Trạng thái hiện tại
    blocker: Optional[str] = None         # Lý do chặn (chuẩn hóa 1 dòng nếu có)

@dataclass
class TodoPhase:
    name: str                             # Tên giai đoạn (ví dụ: "Khảo sát", "Triển khai")
    tasks: list[TodoItem]                 # Danh sách các task trong giai đoạn
```

### 3.2 Quy ước Markdown Checklist & Bảo toàn Blocker

Để con người có thể đọc hiểu và chỉnh sửa checklist bằng tay (human-in-the-loop), hệ thống cung cấp bộ chuyển đổi hai chiều với định dạng Markdown tiêu chuẩn:

| Ký hiệu Markdown | Trạng thái `TodoStatus` | Diễn giải |
|---|---|---|
| `- [ ]` | `pending` | Đang chờ thực hiện |
| `- [/]` hoặc `- [>]` | `in_progress` | Đang tiến hành (tối đa 1 task) |
| `- [x]` hoặc `- [X]` | `completed` | Đã hoàn thành |
| `- [-]` hoặc `- [~]` | `abandoned` | Đã hủy bỏ / bỏ qua |
| `- [!]` | `blocked` | Bị nghẽn bởi lý do bên ngoài |

**Bảo toàn Blocker qua HTML comment**:  
Khi một task bị nghẽn kèm lý do, lý do đó được nối vào cuối dòng task dưới dạng HTML comment:
```markdown
# Triển khai & Tích hợp
- [X] Viết State Machine engine.py
- [!] Tích hợp OAuth 2.0 <!-- blocker: Chờ DevOps cấp Client ID và Secret -->
- [ ] Chạy kiểm thử tích hợp
```
Bộ parser `markdown.py` sử dụng regex để trích xuất cả trạng thái checkbox lẫn nội dung blocker bên trong comment `<!-- blocker: ... -->`, đảm bảo **round-trip xuất/nhập 100% không làm mất dữ liệu**.

---

## 4. Chi tiết Mã nguồn Mẫu Từng Module

Toàn bộ hệ thống được chia thành 7 module nhỏ gọn, tường minh đặt trong thư mục `dino-coding/src/dino_coding/tools/todo/`.

### 4.1 `types.py` — Schema & Data Contracts

```python
"""Data contracts and schemas for Todo state machine."""
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
```

---

### 4.2 `markdown.py` — Chuyển đổi Markdown Hai Chiều

```python
from __future__ import annotations

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

# Regex to match task items like:
# - [ ] task description <!-- blocker: reason -->
# Supports -, *, + bullet points, leading indentation, escaped brackets \[ \], empty brackets [].
TASK_PATTERN = re.compile(
    r"^\s*[-*+]\s*\\?\[\s*(.*?)\s*\\?\]\s+(.*?)\s*$"
)

# Regex to extract trailing HTML blocker comment: <!-- blocker: <reason> -->
BLOCKER_COMMENT_PATTERN = re.compile(
    r"\s*<!--\s*blocker:\s*(.*?)\s*-->\s*$"
)

# Regex to match heading lines like: # Phase Name
HEADING_PATTERN = re.compile(r"^\s*#+\s*(.*?)\s*$")


def phases_to_markdown(phases: list[TodoPhase]) -> str:
    """Serializes a list of TodoPhase into markdown checklist format."""
    if not phases:
        return "# Todos\n"

    sections: list[str] = []
    for phase in phases:
        lines: list[str] = [f"# {phase.name}"]
        for task in phase.tasks:
            marker = STATUS_TO_MARKER.get(task.status, " ")
            line = f"- [{marker}] {task.content}"
            if task.status == "blocked" and task.blocker:
                line += f" <!-- blocker: {task.blocker} -->"
            lines.append(line)
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"


def markdown_to_phases(md: str) -> tuple[list[TodoPhase], list[str]]:
    """Parses markdown checklist format into a list of TodoPhase and any errors."""
    phases: list[TodoPhase] = []
    errors: list[str] = []

    current_phase: TodoPhase | None = None

    for line_num, line in enumerate(md.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # Check for task first, since indented headings are rare but task regex is specific
        task_match = TASK_PATTERN.match(line)
        if task_match:
            marker = task_match.group(1)
            raw_content = task_match.group(2)

            blocker: str | None = None
            blocker_match = BLOCKER_COMMENT_PATTERN.search(raw_content)
            if blocker_match:
                blocker = blocker_match.group(1)
                content = BLOCKER_COMMENT_PATTERN.sub("", raw_content).strip()
            else:
                content = raw_content.strip()

            if marker in MARKER_TO_STATUS:
                status = MARKER_TO_STATUS[marker]
            else:
                status = "pending"
                errors.append(f"Line {line_num}: Unknown status marker '{marker}', defaulted to 'pending'")

            item = TodoItem(content=content, status=status, blocker=blocker)

            if current_phase is None:
                current_phase = TodoPhase(name="Tasks")
                phases.append(current_phase)

            current_phase.tasks.append(item)
            continue

        # Check for heading
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            heading_text = heading_match.group(1)
            current_phase = TodoPhase(name=heading_text)
            phases.append(current_phase)
            continue

    return phases, errors
```

---

### 4.3 `engine.py` — Máy Trạng thái Kế hoạch Thuần Túy (Pure State Machine)

Module `engine.py` là trái tim logic: áp dụng thay đổi trên bản sao dữ liệu (all-or-nothing), điều phối auto-advance pointer, và định dạng tóm tắt trực quan:

```python
from __future__ import annotations

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

---

### 4.4 `tracker.py` — Quản lý Trạng thái Phiên (Session State Manager)

Lớp `TodoTracker` nắm giữ trạng thái chuẩn mực trong RAM của phiên làm việc hiện tại, thực hiện defensive copy để đảm bảo an toàn đa luồng:

```python
from __future__ import annotations

from typing import Optional
from dino_coding.tools.todo.engine import apply_ops, clone_phases, format_summary
from dino_coding.tools.todo.markdown import markdown_to_phases, phases_to_markdown
from dino_coding.tools.todo.types import TodoParams, TodoPhase


class TodoTracker:
    """In-memory state manager that holds the canonical todo state for an agent session."""

    def __init__(self) -> None:
        self._phases: list[TodoPhase] = []

    @property
    def phases(self) -> list[TodoPhase]:
        """Returns a defensive clone of the internal phases."""
        return clone_phases(self._phases)

    def set_phases(self, phases: list[TodoPhase]) -> None:
        """Sets internal phases to a defensive clone of the provided phases."""
        self._phases = clone_phases(phases)

    def execute_op(self, params: TodoParams) -> tuple[str, bool]:
        """Executes a todo operation.

        Returns (summary, error_occurred).
        Rolls back (leaves state unchanged) on error.
        """
        updated_phases, errors = apply_ops(self._phases, params)
        if errors:
            return format_summary(self._phases, errors), True

        if params.op != "view":
            self._phases = updated_phases

        return format_summary(self._phases, []), False

    def to_markdown(self) -> str:
        """Serializes current phases to markdown format."""
        return phases_to_markdown(self._phases)

    def from_markdown(self, md: str) -> list[str]:
        """Parses markdown into phases. Updates state only if no errors occur."""
        phases, errors = markdown_to_phases(md)
        if not errors:
            self._phases = phases
        return errors

    def reset(self) -> None:
        """Clears all todo state."""
        self._phases = []
```

---

### 4.5 `tool.py` — LangChain Tool Đóng Gói

```python
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
```

---

### 4.6 `middleware.py` — TodoMiddleware & Reminder Loop

Module này thực hiện hook `wrap_model_call` để theo dõi các lệnh sửa file và tiêm lời nhắc nhở:

```python
from __future__ import annotations

from typing import Any, Callable, Optional, Sequence
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool

from dino_coding.tools.todo.tracker import TodoTracker
from dino_coding.tools.todo.tool import get_todo_tool

MUTATING_TOOLS: frozenset[str] = frozenset({"edit", "write", "ast_edit", "execute"})
DEFAULT_MUTATION_THRESHOLD = 12
DEFAULT_MAX_NUDGES_PER_PROMPT = 2
MID_RUN_NUDGE_PROMPT = (
    "System reminder: Bạn đã thực hiện nhiều thao tác sửa code liên tiếp mà chưa cập nhật tiến độ. "
    "Hãy dùng `todo` để cập nhật checklist hoặc đánh dấu công việc đã hoàn thành."
)
COMPLETION_REMINDER_PROMPT = (
    "System reminder: Còn {count} công việc chưa hoàn thành trong checklist. "
    "Hãy tiếp tục giải quyết hoặc dùng op `block`/`drop` nếu gặp trở ngại."
)


class TodoMiddleware(AgentMiddleware[Any, Any, Any]):
    """Middleware injecting todo tool, tracking mutations, and enforcing reminder loop."""

    tools: Sequence[BaseTool]

    def __init__(
        self,
        tracker: Optional[TodoTracker] = None,
        mutation_threshold: int = DEFAULT_MUTATION_THRESHOLD,
        max_nudges_per_prompt: int = DEFAULT_MAX_NUDGES_PER_PROMPT,
    ) -> None:
        self.tracker = tracker if tracker is not None else TodoTracker()
        self.mutation_threshold = mutation_threshold
        self.max_nudges_per_prompt = max_nudges_per_prompt
        self.consecutive_mutations: int = 0
        self.nudges_sent: int = 0
        self.tools = [get_todo_tool(self.tracker)]
        self._processed_msg_ids: set[str] = set()
        self._processed_tool_call_ids: set[str] = set()

    def _record_tool_call_once(self, tool_name: str, tool_call_id: Optional[str] = None) -> None:
        """Records a tool call only once based on its ID if available."""
        if tool_call_id:
            if tool_call_id in self._processed_tool_call_ids:
                return
            self._processed_tool_call_ids.add(tool_call_id)
        self.record_tool_call(tool_name)

    def record_tool_call(self, tool_name: str) -> None:
        """Records a tool call to update consecutive mutations counter."""
        if tool_name == "todo":
            self.consecutive_mutations = 0
        elif tool_name in MUTATING_TOOLS:
            self.consecutive_mutations += 1

    def should_nudge(self) -> bool:
        """Determines if a mid-run nudge should be sent."""
        return (
            self.consecutive_mutations >= self.mutation_threshold
            and self.nudges_sent < self.max_nudges_per_prompt
        )

    def consume_nudge(self) -> Optional[str]:
        """Consumes a nudge if eligible, resetting counter and incrementing nudges_sent."""
        if self.should_nudge():
            self.nudges_sent += 1
            self.consecutive_mutations = 0
            return MID_RUN_NUDGE_PROMPT
        return None

    def get_open_tasks_count(self) -> int:
        """Returns count of tasks with status 'pending' or 'in_progress' from tracker."""
        count = 0
        for phase in self.tracker.phases:
            for task in phase.tasks:
                if task.status in ("pending", "in_progress"):
                    count += 1
        return count

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any] | AIMessage:
        """Intercepts model call to track tool calls, inject nudges, and remind open tasks."""
        # Check request.messages for tool calls
        for idx, msg in enumerate(request.messages):
            msg_id = getattr(msg, "id", None) or f"msg_{idx}_{type(msg).__name__}"
            if msg_id in self._processed_msg_ids:
                continue
            self._processed_msg_ids.add(msg_id)

            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if name:
                        self._record_tool_call_once(name, tc_id)

        # Check if we should inject mid-run nudge
        nudge_content = self.consume_nudge()
        current_request = request
        if nudge_content is not None:
            updated_messages = list(request.messages) + [SystemMessage(content=nudge_content)]
            current_request = request.override(messages=updated_messages)

        response = handler(current_request)

        # Inspect response
        ai_msg: Optional[AIMessage] = None
        has_tool_calls = False

        if isinstance(response, ModelResponse):
            for res_msg in response.result:
                if isinstance(res_msg, AIMessage):
                    ai_msg = res_msg
                    if res_msg.tool_calls:
                        has_tool_calls = True
                        for tc in res_msg.tool_calls:
                            name = (
                                tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                            )
                            tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                            if name:
                                self._record_tool_call_once(name, tc_id)
        elif isinstance(response, AIMessage):
            ai_msg = response
            if response.tool_calls:
                has_tool_calls = True
                for tc in response.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if name:
                        self._record_tool_call_once(name, tc_id)

        # If model is finishing (no tool calls) and tasks remain open, append completion reminder
        if not has_tool_calls:
            open_count = self.get_open_tasks_count()
            if open_count > 0:
                reminder = COMPLETION_REMINDER_PROMPT.format(count=open_count)
                if isinstance(response, ModelResponse) and ai_msg is not None:
                    new_content = f"{ai_msg.content}\n\n{reminder}" if ai_msg.content else reminder
                    new_ai_msg = AIMessage(
                        content=new_content,
                        tool_calls=ai_msg.tool_calls,
                        id=ai_msg.id,
                        additional_kwargs=ai_msg.additional_kwargs,
                        response_metadata=ai_msg.response_metadata,
                    )
                    # Replace ai_msg in result
                    new_result = [
                        new_ai_msg if m is ai_msg else m for m in response.result
                    ]
                    return ModelResponse(
                        result=new_result,
                        structured_response=response.structured_response,
                    )
                elif isinstance(response, AIMessage):
                    new_content = f"{response.content}\n\n{reminder}" if response.content else reminder
                    return AIMessage(
                        content=new_content,
                        tool_calls=response.tool_calls,
                        id=response.id,
                        additional_kwargs=response.additional_kwargs,
                        response_metadata=response.response_metadata,
                    )

        return response
```

---

### 4.7 Wiring vào Hệ Thống (`prompt.py` & `agent.py`)

Trong `dino-coding/src/dino_coding/prompt.py`, bổ sung mục hướng dẫn quy chuẩn cho model:

```python
## 5. TASK PLANNING & PROGRESS TRACKING (todo tool):
- Tasks identified by verbatim content: NEVER invent fake or generated IDs like task-1. Task text is the exact identifier. If task text is forgotten: call todo(op="view"), NEVER guess.
- When to initialize: Call todo(op="init", ...) before starting any multi-step task (>= 3 steps), requested task sets, or new instructions. MUST list EVERY user item separately across phases/numbered/bulleted items; NEVER omit or remember leftovers.
- Auto-advance invariant: Marking done, drop, or block automatically advances to the earliest pending task in phase order. Marking out of order may rewind the pointer to the earliest unfinished task, but NEVER reopens completed work.
- Blocker rule: block only actionable open work with an optional reason explaining the blocker (this suppresses stop reminders and advances to the next pending item). Call unblock when resolved to return the task to pending.
- Never call todo alone: Always pair init with the first unit of actual work, and pair done/start with the next action in the same turn.
- Supported operations (9 ops): init, view, start, done, drop, block, unblock, append, rm.
```

Trong `dino-coding/src/dino_coding/agent.py`, cắm `TodoMiddleware` vào danh sách `middleware`:

```python
from dino_coding.tools.todo import TodoMiddleware

def create_my_coding_agent() -> CompiledStateGraph:
    llm = config.get_llm()
    system_prompt = build_coding_system_prompt()
    workspace_root = _get_workspace_root()

    backend = FilesystemBackend(root_dir=workspace_root, virtual_mode=False)
    todo_middleware = TodoMiddleware()

    agent: CompiledStateGraph = create_deep_agent(
        model=llm,
        tools=[*initial_tools, *file_tools, edit, *ast_tools],
        system_prompt=system_prompt,
        middleware=[todo_middleware],
        backend=backend,
    )
    return agent
```

---

## 5. Bộ Test Suite (47 Unit & Integration Tests)

Hệ thống được bảo vệ bởi **47 unit & integration tests** trong `dino-coding/tests/test_todo_*.py`. Toàn bộ 641 tests của dự án đều chạy xanh (100% pass):

```bash
cd dino-coding && uv run pytest tests/test_todo* -v
```

Cấu trúc các file test:
* `test_todo_types.py` (5 tests): Kiểm thử dataclass, literal values, và defaults.
* `test_todo_engine.py` (20 tests): Kiểm thử 9 atomic operations, auto-advance pointer, rollback khi duplicate, out-of-order execution, và format summary.
* `test_todo_markdown.py` (8 tests): Kiểm thử round-trip xuất nhập Markdown, bảo toàn HTML comment blocker, phân tích heading và ký tự checkbox.
* `test_todo_tracker.py` (6 tests): Kiểm thử defensive copy (`clone_phases`), khôi phục từ Markdown, và trạng thái in-memory.
* `test_todo_tool.py` (4 tests): Kiểm thử Pydantic validation và invoke LangChain tool.
* `test_todo_middleware.py` (4 tests): Kiểm thử deduplication tool call ID, mutation nudge counter ($\ge 12$), reset khi gọi `todo`, và completion reminder.

---

## 6. Kịch bản Nghiệm thu Terminal

Chúng ta cung cấp sẵn 2 kịch bản nghiệm thu độc lập không cần phụ thuộc vào API key của LLM:

### 6.1 Demo Trực quan Console (`scripts/demo_todo.py`)

Chạy lệnh:
```bash
cd dino-coding && uv run python scripts/demo_todo.py
```

Kịch bản thực hiện 5 bước mô phỏng thực tế với bảng Rich:
1. Khởi tạo 3 Phase: Khảo sát, Triển khai, Kiểm thử $\to$ Task 1 tự động chuyển sang `[>] in_progress`.
2. Hoàn thành Task 1 (`op='done'`) $\to$ Con trỏ tự động advance sang Task 2 của Phase 1.
3. Gặp trở ngại ở Task 2 (`op='block'`, `reason="Chờ Architect team"`) $\to$ Task 2 chuyển thành `[!] blocked`, con trỏ tự động nhảy sang Task 1 của Phase 2.
4. Gỡ trở ngại (`op='unblock'`) $\to$ Task 2 khôi phục `[ ] pending`, xóa sạch blocker note.
5. Xuất `to_markdown()` và import lại `from_markdown()` $\to$ Đồng nhất 100% cấu trúc, trạng thái và ghi chú blocker!

### 6.2 Nghiệm thu E2E Sprint Tích Hợp (`scripts/acceptance_phase3.py`)

Chạy lệnh:
```bash
cd dino-coding && uv run python scripts/acceptance_phase3.py
```

Kết quả nghiệm thu 7/7 checks đạt tuyệt đối:
```text
=== Kịch bản nghiệm thu E2E Phase 3: Multi-Phase Refactoring Sprint ===
  [PASS] Check 1: todo tool `init` với 3 phases khởi tạo đúng và task 1 chuyển sang in_progress
  [PASS] Check 2: op='done' ở task 1 tự động advance con trỏ sang task 2 trong cùng phase
  [PASS] Check 3: op='block' ở task 2 lưu lý do và auto-advance sang task 1 của phase 2
  [PASS] Check 4: Hoàn thành task out-of-order ở phase 3 không làm mất trạng thái các task trước
  [PASS] Check 5: op='unblock' task 2 khôi phục trạng thái và xóa sạch blocker
  [PASS] Check 6: TodoMiddleware theo dõi đột biến: 12 thao tác sửa code kích hoạt nudge, todo reset counter
  [PASS] Check 7: Tất cả task hoàn thành -> 0 open tasks, tổng kết 6/6 done

=== Kết quả nghiệm thu Phase 3 ===
ALL 7 CHECKS PASSED — Phase 3 Cognitive Anchor hoạt động hoàn hảo!
```

---

## 7. Bảng Defer & Điều kiện Nâng cấp

Để đảm bảo dự án gọn gàng và bám sát nguyên tắc kỹ thuật, một số tính năng mở rộng được ghi nhận để tích hợp ở các Phase sau:

| Hạng mục Defer | Cảm hứng `oh-my-pi` | Điều kiện Nâng cấp tương ứng |
|---|---|---|
| **Subagent Todo Isolation** | `task/worktree.ts` | Triển khai ở **Phase 5 (Subagents & Git Worktree)**: mỗi subagent được cấp 1 tracker độc lập, chỉ trả về kết quả tóm tắt cho orchestrator. |
| **Persistent Branch Rehydration** | `session/todo-persist.ts` | Khi cần khôi phục lại trạng thái `TODO.md` trên đĩa giữa các lần khởi động lại CLI. Hiện tại lưu in-memory session. |
| **Interactive Terminal Task Picker** | `tui/task-select.ts` | Khi xây dựng giao diện TUI tương tác hoàn chỉnh ở Phase 9. |
| **Dynamic DAG Dependency Graphs** | `task-dag.ts` | Khi có yêu cầu các task phụ thuộc phi tuyến tính (DAG) thay vì Phase tuần tự. |

---

## 8. Checklist Nghiệm thu Phase 3 (15 Mục)

Hãy đảm bảo toàn bộ 15 tiêu chí dưới đây đều đạt trước khi chuyển sang Phase 4:

- [ ] 1. Cài đặt đầy đủ 7 module trong `dino-coding/src/dino_coding/tools/todo/` (`types.py`, `markdown.py`, `engine.py`, `tracker.py`, `tool.py`, `middleware.py`, `__init__.py`).
- [ ] 2. Máy trạng thái hỗ trợ đầy đủ 9 thao tác nguyên tử: `init`, `start`, `done`, `rm`, `drop`, `block`, `unblock`, `append`, `view`.
- [ ] 3. Bất biến **Single Active Pointer**: Tại mọi thời điểm chỉ có tối đa 1 task giữ trạng thái `in_progress`.
- [ ] 4. Tính năng **Auto-advance Pointer**: Khi task active chuyển thành `completed`, `abandoned` hoặc `blocked`, engine tự động nâng task `pending` sớm nhất thành `in_progress`.
- [ ] 5. Định danh nguyên văn (**Verbatim Addressing**): Task được gọi bằng đúng content chuỗi ký tự; truyền dạng ID số (`task-1`) bị trả thông báo lỗi hướng dẫn.
- [ ] 6. Tính nguyên tử (**All-or-Nothing Mutation**): Khi một tham số trong lệnh gọi bị lỗi, toàn bộ trạng thái phiên được giữ nguyên (rollback), không có tác dụng phụ.
- [ ] 7. Chuyển đổi Markdown hai chiều bảo toàn đầy đủ các loại checkbox (`[ ]`, `[/]`, `[x]`, `[-]`, `[!]`).
- [ ] 8. Ghi chú blocker được bảo toàn trọn vẹn qua cú pháp comment `<!-- blocker: ... -->` khi round-trip Markdown.
- [ ] 9. Lớp `TodoTracker` sử dụng defensive copy (`clone_phases`) cho cả getter `phases` lẫn setter `set_phases`.
- [ ] 10. `TodoMiddleware` theo dõi đúng các công cụ đột biến mã nguồn (`{"edit", "write", "ast_edit", "execute"}`).
- [ ] 11. Cơ chế **Mid-Run Mutation Nudge**: Tự động kích hoạt khi có $\ge 12$ lượt gọi sửa code liên tiếp mà không cập nhật `todo`; reset bộ đếm ngay khi `todo` được gọi.
- [ ] 12. Cơ chế **Completion Reminder**: Tự động chèn cảnh báo vào phản hồi khi model kết thúc mà vẫn còn task chưa xong.
- [ ] 13. System prompt (`prompt.py`) được bổ sung mục *"5. TASK PLANNING & PROGRESS TRACKING (todo tool)"* bằng tiếng Anh chuẩn.
- [ ] 14. Bộ test suite Phase 3 đạt **47/47 passed**; toàn bộ dự án đạt **641 passed**, 0 regressions.
- [ ] 15. Cả 2 kịch bản nghiệm thu (`demo_todo.py` và `acceptance_phase3.py`) chạy thành công, exit code 0 với 7/7 checks PASS.

---

*(Khi cả 15 mục trên khớp, Phase 3 chính thức đóng sổ. Phase tiếp theo — **Phase 4: Execution Engine & Loopback Bridge** — sẽ đưa vào Persistent Python REPL chạy ngầm với khả năng tương tác hai chiều loopback!)*
