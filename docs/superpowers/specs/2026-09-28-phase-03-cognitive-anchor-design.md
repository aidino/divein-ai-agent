# Thiết kế Kiến trúc: Phase 3 — Cognitive Anchor (Task Planning & Context Compaction)

- **Ngày tạo**: 28/09/2026
- **Trạng thái**: Bản thảo thiết kế đặc tả (Design Spec)
- **Tác giả**: Assistant & User
- **Mục tiêu**: Xây dựng phân hệ Cognitive Anchor (máy trạng thái quản lý kế hoạch `todo` phân cấp, cơ chế nhắc nhở tiến độ, và tận dụng cơ chế nén ngữ cảnh `compaction` của framework `deepagents`) theo chuẩn kiến trúc `oh-my-pi` (`todo.ts` + `compaction.ts`).

---

## 1. Bối cảnh & Mục tiêu Kỹ thuật

### 1.1 Vấn đề cần giải quyết
Trong quá trình thực thi các nhiệm vụ lập trình đa bước phức tạp, AI Coding Agent thường gặp hai thất bại nhận thức (cognitive failures) phổ biến:
1. **Mất phương hướng / Rơi rụng nhiệm vụ (Task Drift)**: Agent lập kế hoạch ở các lượt đầu, nhưng sau chuỗi thao tác sửa code qua các công cụ đột biến (`edit`, `write`, `ast_edit`), agent quên mất mục tiêu ban đầu, không cập nhật tiến độ, hoặc tự ý kết luận sớm khi các hạng mục cốt lõi chưa hoàn thành.
2. **Tràn cửa sổ ngữ cảnh (Context Overflow)**: Lịch sử hội thoại dài làm cạn kiệt token window, đẩy chi phí lên cao và làm suy giảm khả năng suy luận của mô hình nếu không có cơ chế nén ngữ cảnh định kỳ.

### 1.2 Quyết định Kiến trúc & Đối chiếu Framework
- **Khảo sát LangChain MCP & DeepAgents**:
  - `deepagents` đã tích hợp sẵn `SummarizationMiddleware` trong lõi `create_deep_agent`. Middleware này tự động tính toán ngưỡng context window của từng model, quản lý cắt tỉa đối số công cụ cũ và lưu trữ lịch sử bị thu hồi (history offload). Chúng ta **tái sử dụng hoàn toàn** cơ chế này để thực hiện Compaction, không viết lại từ đầu.
  - `langchain.agents.middleware.TodoListMiddleware` cung cấp công cụ `write_todos` nhưng có nhược điểm lớn: yêu cầu model gửi lại toàn bộ danh sách ở mỗi lượt (`write_todos(todos: list[Todo])`), gây tốn token nghiêm trọng, dễ hallucinate và thiếu các thao tác nguyên tử.
- **Giải pháp Hybrid (Quyết định chọn)**:
  - Port máy trạng thái kế hoạch phân cấp của `oh-my-pi` (`todo.ts`) với 9 thao tác nguyên tử (`init`, `start`, `done`, `rm`, `drop`, `block`, `unblock`, `append`, `view`), phân cấp Phase, định danh nguyên văn (verbatim), và auto-advance pointer.
  - Đóng gói thành `TodoMiddleware` kế thừa `AgentMiddleware` chuẩn của LangChain/DeepAgents, đồng bộ trạng thái phản ứng `state["todos"]` cho UI stream.
  - Tích hợp vòng lặp nhắc nhở (Todo Reminder Loop) để tự động nhắc agent khi thực hiện liên tiếp các thao tác sửa code mà quên cập nhật checklist.
  - Lưu trữ in-memory theo session (không ép ghi `workspace/TODO.md`), có sẵn module chuyển đổi hai chiều với Markdown (`phases_to_markdown` / `markdown_to_phases`).

---

## 2. Mô hình Dữ liệu (Data Contracts)

```python
from dataclasses import dataclass
from typing import Literal, Optional

TodoStatus = Literal["pending", "in_progress", "completed", "abandoned", "blocked"]
TodoOperation = Literal[
    "init", "start", "done", "rm", "drop", "block", "unblock", "append", "view"
]


@dataclass
class TodoItem:
  content: str  # Nội dung nguyên văn (verbatim), định danh duy nhất
  status: TodoStatus = "pending"
  blocker: Optional[str] = None  # Lý do chặn (chuẩn hóa trên 1 dòng)


@dataclass
class TodoPhase:
  name: str  # Tên giai đoạn (ví dụ: "Nghiên cứu", "Triển khai", "Kiểm thử")
  tasks: list[TodoItem]


@dataclass
class InitPhaseInput:
  phase: str
  items: list[str]
```

### Hợp đồng Schema Công cụ `todo`
- `op`: `Literal["init", "start", "done", "rm", "drop", "block", "unblock", "append", "view"]`
- `list`: Danh sách `InitPhaseInput` dùng cho `init` phân cấp.
- `items`: Danh sách task dùng cho `init` dạng phẳng hoặc `append`.
- `phase`: Tên giai đoạn mục tiêu (dùng cho `append`, `done`, `drop`, `block`, `unblock`, `rm`).
- `task`: Nội dung nguyên văn của task mục tiêu (dùng cho `start`, `done`, `drop`, `block`, `unblock`, `rm`).
- `reason`: Lý do chặn khi gọi `block`.

---

## 3. Máy Trạng thái Kế hoạch (Todo State Machine)

### 3.1 Thao tác & Quy tắc Biển đổi Trạng thái

1. **`init`**:
   - Khởi tạo toàn bộ danh sách phase và task.
   - Bác bỏ nếu trùng tên phase hoặc trùng nội dung task.
   - Khởi tạo mọi task ở trạng thái `pending`.
   - Tự động chuẩn hóa: chuyển task đầu tiên của phase đầu tiên thành `in_progress`.
2. **`start`**:
   - Chuyển task chỉ định sang `in_progress`.
   - Hạ task đang `in_progress` trước đó (nếu có) về `pending`, đảm bảo bất biến duy nhất 1 task active.
3. **`done`**:
   - Đánh dấu task hoặc toàn bộ task trong phase chỉ định thành `completed`.
   - Kích hoạt auto-advance pointer.
4. **`drop`**:
   - Đánh dấu task hoặc phase thành `abandoned`.
   - Kích hoạt auto-advance pointer.
5. **`block`**:
   - Đánh dấu task hoặc phase thành `blocked`, lưu `blocker` (chuẩn hóa whitespace thành 1 dòng).
   - Chỉ áp dụng trên các task đang mở (`pending`, `in_progress`, `blocked`). Tuyệt đối không mở lại hoặc đổi trạng thái task đã `completed` hay `abandoned`.
   - Kích hoạt auto-advance pointer.
6. **`unblock`**:
   - Giải phóng task từ `blocked` về `pending`, xóa `blocker`.
7. **`rm`**:
   - Xóa bỏ task hoặc dọn sạch phase khỏi checklist.
8. **`append`**:
   - Thêm các task mới vào phase chỉ định (tạo mới phase nếu chưa tồn tại).
   - Kiểm tra trùng lặp trên toàn bộ danh sách trước khi bổ sung.
9. **`view`**:
   - Thao tác chỉ đọc, trả về chuỗi tóm tắt tiến độ hiện tại, không làm biến đổi trạng thái.

### 3.2 Các Bất biến Cốt lõi (Invariants)
- **Single Active Pointer**: Tại mọi thời điểm, số lượng task `in_progress` luôn là 0 hoặc 1.
- **Auto-Advancement**: Khi task active chuyển sang `completed`, `abandoned` hoặc `blocked`, engine tự động quét theo thứ tự Phase $\to$ Task để tìm task `pending` đầu tiên và nâng thành `in_progress`.
- **Out-of-Order Safety**: Hoàn thành sớm các task ở phase sau không làm thay đổi trạng thái của các task đã hoàn thành trước đó.
- **Verbatim Addressing**: Định danh task bằng đúng chuỗi ký tự nội dung. Truyền dạng `task-1`, `task-2` sẽ bị trả lỗi kèm thông báo hướng dẫn.
- **All-or-Nothing Mutation**: Mọi lỗi xảy ra trong batch lệnh sẽ hủy bỏ toàn bộ thay đổi, giữ nguyên trạng thái phiên trước đó.

---

## 4. Chuyển đổi Markdown Hai chiều (Markdown Round-Trip)

Module `markdown.py` cung cấp hai hàm:
- `phases_to_markdown(phases: list[TodoPhase]) -> str`
- `markdown_to_phases(md: str) -> tuple[list[TodoPhase], list[str]]`

### Quy ước Định dạng Markdown:
- Heading `# <Tên Phase>` đại diện cho giai đoạn.
- Ký tự checkbox:
  - `[ ]`: `pending`
  - `[/]` hoặc `[>]`: `in_progress`
  - `[x]` hoặc `[X]`: `completed`
  - `[-]` hoặc `[~]`: `abandoned`
  - `[!]`: `blocked`
- Ghi chú lý do chặn: Đặt trong HTML comment ở cuối dòng task bị block:
  `- [!] Thiết kế database <!-- blocker: chờ phê duyệt schema -->`

---

## 5. Quản lý Phiên & Bộ đệm (TodoTracker)

Lớp `TodoTracker` quản lý trạng thái in-memory trong phiên làm việc:
- Deep copy mọi trạng thái khi đọc/ghi để ngăn chặn lỗi chia sẻ tham chiếu ngoài ý muốn.
- `execute_op(params: dict) -> tuple[str, bool]`: Tiếp nhận tham số, ủy quyền cho engine, cập nhật trạng thái nếu thành công và trả về chuỗi tóm tắt trực quan:
  ```text
  Overall: 2/5 done, 3 open, 1 blocked.
  Active phase 2/3 "Triển khai" (0/2).
    Khảo sát:
      - [X] Đọc tài liệu LangChain MCP
    Triển khai:
      - [ ] Viết TodoEngine (in progress)
      - [ ] Tích hợp Middleware
    Kiểm thử:
      - [ ] Chạy unit test (blocked: chờ hoàn thành engine)
  ```

---

## 6. Nối dây Middleware & Vòng lặp Nhắc nhở (Todo Reminder Loop)

### 6.1 `TodoMiddleware`
- Kế thừa `langchain.agents.middleware.AgentMiddleware`.
- Khai báo `state_schema = PlanningState` (đồng bộ `todos: list[dict]`).
- Tiêm công cụ `todo` vào danh sách công cụ của agent.

### 6.2 Vòng lặp Nhắc nhở (Reminder Loop)
1. **Mid-Run Mutation Nudge**:
   - Theo dõi chuỗi gọi tool qua hook `wrap_model_call`.
   - Nếu phát hiện $\ge 12$ lượt gọi liên tiếp các công cụ đột biến mã nguồn (`MUTATING_TOOLS = {"edit", "write", "ast_edit", "execute"}`) mà không có lệnh gọi `todo`, tự động chèn thông điệp nhắc nhở vào prompt của lượt tiếp theo.
   - Giới hạn tối đa 2 lần nhắc mỗi phiên.
2. **Completion Reminder**:
   - Khi model trả về phản hồi kết thúc (không gọi tool nữa), kiểm tra nếu checklist vẫn còn task `pending` hoặc `in_progress` $\to$ ghi nhận cảnh báo nhắc nhở hoàn thành công việc.

---

## 7. Cấu trúc Thư mục & Phân chia Module

```text
dino-coding/
├── src/dino_coding/tools/todo/
│   ├── __init__.py          # Export TodoMiddleware, TodoTracker, todo tool
│   ├── types.py             # TodoItem, TodoPhase, TodoStatus, TodoOperation
│   ├── engine.py            # apply_entry, normalize_in_progress, format_summary
│   ├── markdown.py          # phases_to_markdown, markdown_to_phases
│   ├── tracker.py           # TodoTracker (in-memory session state)
│   ├── tool.py              # LangChain @tool def todo(...)
│   └── middleware.py        # TodoMiddleware (state sync, wrap_model_call hooks)
├── tests/
│   ├── test_todo.py         # Unit tests cho engine, 9 ops, markdown round-trip
│   └── test_todo_middleware.py # Tests cho middleware, state sync, mutation nudge
├── scripts/
│   ├── demo_todo.py         # Demo tương tác 9 ops + Rich format
│   └── acceptance_phase3.py # Kịch bản nghiệm thu E2E Phase 3
└── build-coding-agent-tutorial/
    └── phase_03_task_planning.md # Tài liệu hướng dẫn tutorial chi tiết
```

---

## 8. Kế hoạch Kiểm chứng & Nghiệm thu

1. **Unit Test Suite**:
   - Kiểm thử độc lập 9 ops với đầy đủ biên lỗi (duplicate, missing task, invalid op).
   - Kiểm thử bảo toàn tính bất biến (auto-advance, single in_progress).
   - Kiểm thử round-trip Markdown serialization.
   - Đảm bảo toàn bộ 594 test hiện có của dự án không bị hồi quy.
2. **Demo Engine (`demo_todo.py`)**:
   - Chạy độc lập không cần LLM, in ra màn hình Rich tables/panels mô tả từng bước chuyển đổi trạng thái của State Machine.
3. **Acceptance Test E2E (`acceptance_phase3.py`)**:
   - Mô phỏng quy trình hoàn chỉnh: Tạo danh sách $\to$ Khởi động $\to$ Thực hiện tác vụ $\to$ Gặp blocker $\to$ Giải phóng blocker $\to$ Hoàn tất toàn bộ $\to$ Báo cáo tổng kết.
