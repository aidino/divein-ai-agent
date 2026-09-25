# Phase 3: Task Planning — Phân rã công việc phức tạp

> **Mục tiêu**: Giúp Coding Agent có khả năng tự động lập kế hoạch, phân rã các tác vụ lập trình phức tạp thành danh sách công việc (Todo Checklist), theo dõi tiến độ từng bước và duy trì "mỏ neo nhận thức" (Cognitive Anchor) khi ngữ cảnh bị nén.
>
> **Thời gian ước tính**: 1.5 - 2 giờ
>
> **Prerequisites**: Hoàn thành [Phase 2: File Operations](phase_02_file_operations.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Vấn đề "Mất phương hướng" (Context Drift) ở Coding Agent
Khi giải quyết một bài toán lập trình nhiều bước (ví dụ: *"Refactor lại toàn bộ module thanh toán, viết unit test mới và cập nhật file cấu hình"*), LLM thường gặp phải hiện tượng **Context Drift**:
- Sau 10-15 lượt gọi tool liên tiếp, lượng tin nhắn phình to khiến mô hình quên mất mục tiêu ban đầu.
- Mô hình sửa đi sửa lại một file, hoặc nhảy cóc sang bước cuối mà bỏ quên các bước trung gian (như viết test).
- Khi người dùng muốn biết Agent đang làm đến đâu, Agent không có một cấu trúc dữ liệu minh bạch để báo cáo.

### 1.2 `TodoListMiddleware` — Quản lý kế hoạch bằng State Machine
Trong Deep Agents, giải pháp cho bài toán này là **`TodoListMiddleware`**:
1. **Tự động inject Tool**: Middleware này tự động thêm tool `write_todos` vào danh sách công cụ của Agent mà bạn không cần tự code.
2. **Kênh lưu trữ độc lập (Isolated State Channel)**: Danh sách công việc được lưu trong `state["todos"]`, tách biệt hoàn toàn với lịch sử tin nhắn hội thoại (`messages`).
3. **Cấu trúc dữ liệu chuẩn hóa**:
   Mỗi công việc trong checklist tuân theo schema nghiêm ngặt:
   ```json
   {
     "content": "Nội dung việc cần làm",
     "status": "pending" | "in_progress" | "completed"
   }
   ```
4. **Vòng đời 3 trạng thái**:
   - `pending`: Đang chờ thực hiện.
   - `in_progress`: Đang làm (tại một thời điểm, Agent chỉ nên có tối đa một task ở trạng thái này).
   - `completed`: Đã hoàn thành.

```
┌────────────────────────────────────────────────────────┐
│               TodoListMiddleware Lifecycle             │
│                                                        │
│  [1. Lập kế hoạch]                                     │
│      LLM gọi write_todos([                             │
│          {content: "Khảo sát code", status: "pending"},│
│          {content: "Refactor hàm",  status: "pending"} │
│      ])                                                │
│                                                        │
│  [2. Bắt đầu làm]                                      │
│      Cập nhật task 1 -> "in_progress"                  │
│                                                        │
│  [3. Hoàn tất & Chuyển bước]                           │
│      Task 1 -> "completed", Task 2 -> "in_progress"    │
└────────────────────────────────────────────────────────┘
```

### 1.3 Khái niệm "Mỏ neo nhận thức" (Cognitive Anchor)
Khi một tác vụ kéo dài 30-50 bước, context window sẽ đầy. Khi đó, `SummarizationMiddleware` sẽ kích hoạt:
- Nén toàn bộ lịch sử 40 tin nhắn cũ thành 1 đoạn văn tóm tắt ngắn.
- **Điểm mấu chốt**: Vì danh sách `todos` nằm trong channel riêng (`state["todos"]`), nó **KHÔNG BỊ NÉN HAY LÀM MỜ**!
- Sau khi tóm tắt hội thoại, middleware tự động tiêm lại danh sách `todos` hiện tại vào prompt của lượt suy luận tiếp theo. Danh sách này đóng vai trò là "mỏ neo nhận thức" vững chắc, giúp Agent ngay lập tức nhớ ra: *"Tôi là ai, tôi vừa làm xong bước nào, và bước tiếp theo tôi cần làm gì"*.

### 1.4 Kiến trúc Middleware: Node-style vs Wrap-style Hooks
Deep Agents hỗ trợ 2 cơ chế hook khi xây dựng middleware:
- **Node-style hooks** (`before_agent`, `before_model`, `after_model`, `after_agent`): Chạy như các node độc lập trong đồ thị LangGraph. Đây là kiểu hook bắt buộc nếu bạn muốn sử dụng `interrupt()` để xin ý kiến con người (Human-in-the-Loop).
- **Wrap-style hooks** (`wrap_model_call`, `wrap_tool_call`): Bọc xung quanh quá trình gọi model hoặc tool, thích hợp cho việc đo lường thời gian (telemetry) hoặc ghi đè tham số.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [06_task_planning.md](../guideline/06_task_planning.md) | TodoListMiddleware & write_todos | Nắm rõ cấu trúc dữ liệu của task, cách kích hoạt middleware và lấy state todos. |
| [06_task_planning.md](../guideline/06_task_planning.md) | Node-style vs Wrap-style Hooks | Phân biệt 2 cơ chế hook và tầm quan trọng đối với khả năng ngắt (interrupt). |
| [06_task_planning.md](../guideline/06_task_planning.md) | Cognitive Anchor & Context Compression | Hiểu cách Todo List kết hợp cùng SummarizationMiddleware để giữ thăng bằng cho Agent. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Khởi tạo Middleware và Agent có năng lực lập kế hoạch

Trong phiên bản v0.7+, `TodoListMiddleware` không tự động bật mặc định (để tiết kiệm token cho các agent đơn giản). Chúng ta phải khai báo nó tường minh trong danh sách `middleware` của `create_deep_agent`.

Tạo file `src/agent_planner.py`:

```python
"""Coding Agent tích hợp Task Planning và TodoListMiddleware."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.middleware.todo import TodoListMiddleware

from src.backend import get_workspace_backend

load_dotenv()

PLANNING_SYSTEM_PROMPT = """Bạn là một Senior Software Architect và Tech Lead.

QUY TẮC BẮT BUỘC:
1. LUÔN LẬP KẾ HOẠCH TRƯỚC: Đối với bất kỳ yêu cầu nào gồm từ 2 bước trở lên, bạn BẮT BUỘC phải sử dụng công cụ `write_todos` để lập ra danh sách các công việc cụ thể trước khi thực hiện bất kỳ hành động nào khác.
2. NGUYÊN TẮC 'IN_PROGRESS': Tại một thời điểm, chỉ chuyển ĐÚNG MỘT nhiệm vụ sang trạng thái `in_progress`.
3. CẬP NHẬT TIẾN ĐỘ: Ngay sau khi hoàn thành một bước (ví dụ đọc xong file hoặc sửa xong file), phải gọi `write_todos` cập nhật trạng thái bước đó thành `completed` và kích hoạt bước tiếp theo.
4. KIỂM THỬ: Luôn đưa bước viết hoặc chạy test vào danh sách việc cần làm.
"""


def build_planning_agent():
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")

    # Kích hoạt TodoListMiddleware
    todo_middleware = TodoListMiddleware()

    # Truyền middleware vào create_deep_agent
    agent = create_deep_agent(
        model=llm,
        tools=[],  # VFS tools tự động nạp từ backend
        backend=backend,
        middleware=[todo_middleware],
        system_prompt=PLANNING_SYSTEM_PROMPT,
    )
    return agent
```

### Bước 2: Viết script theo dõi và hiển thị danh sách Todos thời gian thực

Để quan sát cách Agent cập nhật checklist trong lúc làm việc, ta có thể truy xuất kênh `state["todos"]` từ kết quả trả về của Agent:

Thêm hàm hiển thị trực quan vào cuối file `src/agent_planner.py`:

```python
def print_todo_checklist(todos: list):
    """In danh sách công việc dạng checklist trực quan ra terminal."""
    if not todos:
        print("  (Chưa có kế hoạch nào được ghi nhận)")
        return

    status_icons = {
        "pending": "[ ] ⏳",
        "in_progress": "[→] 🔄",
        "completed": "[✓] ✅",
    }

    print("\n--- DANH SÁCH TIẾN ĐỘ CÔNG VIỆC (TODOS) ---")
    for idx, item in enumerate(todos, start=1):
        icon = status_icons.get(item.get("status", "pending"), "[?]")
        print(f"  {idx}. {icon} {item.get('content')} (Trạng thái: {item.get('status')})")
    print("------------------------------------------\n")


if __name__ == "__main__":
    bot = build_planning_agent()

    # Nhiệm vụ phức tạp đòi hỏi nhiều bước
    complex_task = (
        "Hãy thực hiện kế hoạch bảo trì codebase trong workspace:\n"
        "1. Khảo sát toàn bộ các file hiện có.\n"
        "2. Viết thêm một hàm `calculate_tax(income: float) -> float` vào file `src/math_service.py` "
        "(thuế 10% nếu dưới 10 triệu, 20% nếu trên 10 triệu).\n"
        "3. Viết thêm unit test tương ứng vào `tests/test_math.py`.\n"
        "Yêu cầu: Hãy lập checklist kế hoạch chi tiết bằng write_todos trước khi code!"
    )

    print(f"Yêu cầu giao cho Agent:\n{complex_task}\n")

    # Chạy Agent và nhận kết quả cuối
    result = bot.invoke({"messages": [{"role": "user", "content": complex_task}]})

    # Trích xuất state todos do TodoListMiddleware quản lý
    final_todos = result.get("todos", [])
    print_todo_checklist(final_todos)

    print("--- PHẢN HỒI CUỐI CÙNG CỦA AGENT ---")
    print(result["messages"][-1].content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm Agent:

```bash
python -m src.agent_planner
```

**Quan sát diễn biến từng bước trong log / trace**:
1. **Lượt 1 (Planning)**: Ngay khi nhận đề bài, Agent không gọi `read_file` hay `write_file`. Hành động đầu tiên của nó là gọi tool `write_todos`:
   ```json
   [
     {"content": "Khảo sát cấu trúc thư mục workspace", "status": "in_progress"},
     {"content": "Viết hàm calculate_tax vào src/math_service.py", "status": "pending"},
     {"content": "Viết unit test kiểm tra thuế vào tests/test_math.py", "status": "pending"},
     {"content": "Xác nhận và kiểm tra lại toàn bộ file", "status": "pending"}
   ]
   ```
2. **Lượt 2**: Agent gọi `ls` hoặc `glob` để hoàn tất khảo sát.
3. **Lượt 3**: Agent gọi `write_todos` để đánh dấu task 1 `completed`, chuyển task 2 `in_progress`.
4. **Lượt 4**: Agent dùng `read_file` đọc `src/math_service.py` rồi dùng `edit_file` thêm hàm `calculate_tax`.
5. **Lượt 5**: Agent cập nhật task 2 `completed`, task 3 `in_progress`.
6. **Lượt 6**: Agent sửa file `tests/test_math.py` bổ sung ca kiểm thử.
7. **Lượt 7**: Agent đánh dấu tất cả hoàn tất (`completed`) và tổng kết cho người dùng.

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Trong output của terminal, bảng checklist Todos được in ra đầy đủ và tất cả các mục đều có icon `[✓] ✅ (Trạng thái: completed)`.
- [ ] Mở file `workspace/src/math_service.py`: hàm `calculate_tax` đã được thêm vào chính xác.
- [ ] Mở file `workspace/tests/test_math.py`: test case cho hàm tính thuế đã xuất hiện.
- [ ] Chạy pytest kiểm tra:
  ```bash
  PYTHONPATH=workspace pytest workspace/tests/test_math.py
  ```
  Tất cả các test đều **PASS**.
- [ ] Trên LangSmith Trace: Thấy các lượt gọi tool `write_todos` xen kẽ nhịp nhàng giữa các lượt gọi `read_file` và `edit_file`.

---

## 6. Lỗi thường gặp & Best Practices

1. **Agent "quên" gọi `write_todos` mà lao vào code ngay**:
   - *Nguyên nhân*: System Prompt chưa đủ nghiêm khắc hoặc mô hình nhỏ chưa tuân thủ quy tắc.
   - *Khắc phục*: Tăng cường câu chữ trong System Prompt: *"Nếu bạn không gọi write_todos ở bước đầu tiên, câu trả lời sẽ bị từ chối"*.

2. **Đặt tất cả nhiệm vụ là `in_progress` cùng lúc**:
   - *Khắc phục*: Hướng dẫn Agent trong prompt: *"Quy tắc độc quyền: Chỉ duy nhất 1 task được ở trạng thái in_progress để thể hiện trọng tâm hiện tại"*.

3. **Kế hoạch quá chung chung hoặc quá vụn vặt**:
   - Khuyên Agent chia task thành các mục có kết quả đo lường được (measurable outcomes), ví dụ: "Đọc file X", "Sửa hàm Y", "Chạy test Z", thay vì những câu vô nghĩa như "Suy nghĩ logic".
