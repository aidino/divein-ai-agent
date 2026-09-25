# Phase 2: File Operations — Đọc, ghi, tìm kiếm code

> **Mục tiêu**: Trang bị cho Coding Agent khả năng tương tác trực tiếp với mã nguồn trên đĩa thông qua Virtual File System (VFS): tìm kiếm từ khóa, duyệt cây thư mục, đọc nội dung file phân trang, và phẫu thuật chỉnh sửa code chính xác từng dòng.
>
> **Thời gian ước tính**: 2 - 2.5 giờ
>
> **Prerequisites**: Hoàn thành [Phase 1: Hello Coding Agent](phase_01_hello_agent.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Virtual File System (VFS) trong Deep Agents
Một Coding Agent thực thụ không thể chỉ làm việc trên bộ nhớ đệm (RAM) hay nhận code dán vào chat. Nó phải có khả năng tương tác với hệ thống tập tin cục bộ để đọc các module phụ thuộc, tìm kiếm định nghĩa hàm và lưu lại các thay đổi code.

Deep Agents cung cấp một lớp trừu tượng hóa mạnh mẽ gọi là **Virtual File System (VFS)**:
- Agent không gọi trực tiếp các lệnh OS trần trụi (`os.system` hay `shutil`) mà thao tác thông qua **7 built-in tools** được chuẩn hóa.
- Tách rời giao diện công cụ khỏi nơi lưu trữ thực tế thông qua cơ chế **Backend cắm rút (Pluggable Backends)**.

```
┌────────────────────────────────────────────────────────┐
│            7 Built-in File Operations Tools            │
│    ls | glob | grep | read_file | write_file | ...     │
├────────────────────────────────────────────────────────┤
│             Virtual File System Abstraction            │
├────────────────────────────────────────────────────────┤
│                  Pluggable Backends                    │
│  FilesystemBackend  │   StateBackend   │  StoreBackend │
│ (Thư mục đĩa thật)  │  (In-Memory RAM) │  (Persistence)│
└────────────────────────────────────────────────────────┘
```

### 1.2 Các Storage Backend quan trọng
1. **`FilesystemBackend`**:
   - Gắn kết trực tiếp VFS vào một thư mục thực trên ổ đĩa máy tính (thường là thư mục `workspace/` của dự án).
   - Tham số **`virtual_mode=True`** (BẮT BUỘC): Giữ chân Agent bên trong `root_dir`. Nếu Agent cố tình dùng đường dẫn `../../etc/passwd` hoặc truy cập file bên ngoài thư mục được chỉ định, backend sẽ ngay lập tức chặn lại và báo lỗi Path Traversal.
2. **`StateBackend`**:
   - Lưu trữ toàn bộ file trên RAM (trong state graph của LangGraph). Rất hữu ích cho unit test tự động hoặc môi trường tạm thời.
3. **`CompositeBackend`**:
   - Cho phép định tuyến các prefix đường dẫn khác nhau đến các backend khác nhau (ví dụ: `/workspace` ghi vào đĩa, `/memory` ghi vào Store persistence).

### 1.3 7 Built-in Tools và Quy tắc sử dụng

| Tool | Công dụng | Điểm lưu ý cốt lõi |
| :--- | :--- | :--- |
| `ls` | Liệt kê danh sách file/thư mục tại đường dẫn chỉ định. | Dùng để khảo sát nhanh cấu trúc thư mục con. |
| `glob` | Tìm kiếm đường dẫn file theo pattern (VD: `**/*.py`, `tests/test_*.py`). | Giúp Agent định vị nhanh các file cần chú ý mà không cần đệ quy thủ công. |
| `grep` | Tìm kiếm chuỗi/regex trong nội dung nhiều file. | Hỗ trợ 3 output modes: `files_with_matches` (mặc định), `content` (kèm dòng code và số dòng), `count`. |
| `read_file` | Đọc nội dung file văn bản. | Hỗ trợ phân trang qua `offset` (dòng bắt đầu) và `limit` (số dòng đọc). Giúp tránh tràn context với file lớn. |
| `edit_file` | Thay thế chính xác một đoạn chuỗi cũ (`old_string`) bằng chuỗi mới (`new_string`). | **Công cụ phẫu thuật chính xác**: Chỉ sửa đúng đoạn code cần sửa, giữ nguyên phần còn lại của file. |
| `write_file` | Ghi đè toàn bộ nội dung file. | **CẢNH BÁO v0.7+**: `write_file` ghi đè toàn bộ nội dung mà không cảnh báo lỗi FileExists. Chỉ dùng khi tạo file mới hoàn toàn! |
| `delete` | Xóa một file khỏi VFS. | Cần được bảo vệ cẩn trọng trong các giai đoạn sau. |

### 1.4 Cơ chế Auto-Eviction và Summarization
Khi Agent duyệt một codebase lớn, kết quả của một lệnh `grep` hoặc `read_file` có thể lên tới hàng chục nghìn token:
- **Auto-Eviction**: Trong Deep Agents, nếu output của một tool vượt quá ngưỡng an toàn (~20.000 tokens), framework sẽ tự động lưu output đó thành một file tạm trên VFS và chỉ trả về trong cuộc trò chuyện đường dẫn file kèm một đoạn preview ngắn. Điều này bảo vệ context window không bị sập.
- **Context Summarization**: Khi tổng lịch sử hội thoại đạt khoảng 85% dung lượng ngữ cảnh của mô hình, middleware sẽ tự động tóm tắt các bước cũ và nén lại.

### 1.5 Workflow tư duy chuẩn của Coding Agent
Một Coding Agent chuyên nghiệp không bao giờ nhảy ngay vào sửa file. Nó phải tuân thủ quy trình 4 bước:
1. **Khảo sát cấu trúc**: Dùng `ls` hoặc `glob` để xem cấu trúc dự án.
2. **Định vị điểm nghi vấn**: Dùng `grep` tìm tên hàm, biến hoặc thông điệp lỗi để khoanh vùng file.
3. **Đọc chi tiết**: Dùng `read_file` đọc ngữ cảnh xung quanh dòng bị lỗi.
4. **Phẫu thuật code**: Dùng `edit_file` để sửa chính xác đoạn code bị lỗi, hoặc `write_file` nếu tạo file test mới.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [05_virtual_filesystem.md](../guideline/05_virtual_filesystem.md) | Built-in Tools & Storage Backends | Tìm hiểu chi tiết tham số của 7 file tools và cách khởi tạo `FilesystemBackend`. |
| [05_virtual_filesystem.md](../guideline/05_virtual_filesystem.md) | Tự Động Quản Lý Context & Auto-Eviction | Nắm cơ chế bảo vệ context khi đọc file lớn. |
| [01_deepagent_version_update.md](../guideline/01_deepagent_version_update.md) | Phần 6. File tool: Mạnh mẽ hơn | Hiểu thay đổi breaking change: `write_file` ghi đè và `edit_file` thay thế `patch`. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Chuẩn bị Workspace giả lập chứa bug

Tạo một thư mục con `workspace/` đóng vai trò là dự án phần mềm mà Agent sẽ thao tác. Bên trong tạo 2 file Python có chứa một lỗi logic:

```bash
mkdir -p workspace/src
mkdir -p workspace/tests
```

Tạo file `workspace/src/math_service.py`:
```python
"""Module xử lý tính toán tài chính."""


def calculate_discount(price: float, discount_percent: float) -> float:
    """Tính giá sau chiết khấu."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Tỉ lệ chiết khấu không hợp lệ")

    # BUG CỐ Ý: Nhân nhầm với 10 thay vì chia cho 100
    discount_amount = price * (discount_percent * 10)
    return price - discount_amount


def format_currency(amount: float) -> str:
    """Định dạng số tiền hiển thị."""
    return f"{amount:,.2f} VNĐ"
```

Tạo file `workspace/tests/test_math.py`:
```python
"""Unit test cho math_service."""

from src.math_service import calculate_discount


def test_discount():
    # Mua hàng 100.000 với discount 10% -> phải còn 90.000
    result = calculate_discount(100000.0, 10.0)
    assert result == 90000.0, f"Kỳ vọng 90000.0 nhưng nhận {result}"
```

### Bước 2: Cấu hình `FilesystemBackend`

Tạo file `src/backend.py` để khởi tạo backend an toàn trỏ vào thư mục `workspace/`:

```python
"""Cấu hình Storage Backend an toàn cho Coding Agent."""

import os
from deepagents.backends import FilesystemBackend


def get_workspace_backend(workspace_path: str = "workspace") -> FilesystemBackend:
    """Tạo FilesystemBackend với chế độ virtual_mode bật để cô lập Agent.

    Args:
        workspace_path: Đường dẫn tới thư mục gốc của workspace.

    Returns:
        Instance của FilesystemBackend đã được kiểm tra tính hợp lệ.
    """
    abs_path = os.path.abspath(workspace_path)
    os.makedirs(abs_path, exist_ok=True)

    # virtual_mode=True đảm bảo agent không bao giờ thoát ra khỏi thư mục này
    backend = FilesystemBackend(
        root_dir=abs_path,
        virtual_mode=True,
    )
    return backend
```

### Bước 3: Thiết kế System Prompt hướng dẫn quy trình duyệt và sửa code

Tạo file `src/prompts_v2.py`:

```python
"""System Prompt chuyên biệt cho File Operations."""

FILE_OPS_SYSTEM_PROMPT = """Bạn là một AI Software Debugger chuyên nghiệp, làm việc trực tiếp trên workspace mã nguồn.

Quy trình giải quyết vấn đề của bạn:
1. KHÔNG PHỎNG ĐOÁN: Luôn bắt đầu bằng cách dùng `glob` hoặc `ls` để tìm hiểu cấu trúc dự án.
2. ĐỊNH VỊ CHÍNH XÁC: Sử dụng `grep` với `output_mode="content"` để tìm từ khóa hoặc thông báo lỗi cụ thể kèm số dòng.
3. ĐỌC KỸ TRƯỚC KHI SỬA: Dùng `read_file` đọc ngữ cảnh các dòng trước và sau vị trí lỗi.
4. PHẪU THUẬT AN TOÀN:
   - Sử dụng `edit_file` để sửa đúng đoạn code cần sửa (`old_string` -> `new_string`).
   - TUYỆT ĐỐI KHÔNG dùng `write_file` để ghi lại file đang có sẵn vì sẽ làm mất toàn bộ code còn lại nếu bạn không ghi đầy đủ.
   - Chỉ dùng `write_file` khi tạo mới file test hoặc file module mới.
5. XÁC NHẬN: Sau khi sửa, kiểm tra lại bằng `read_file` xem file đã cập nhật đúng như kỳ vọng chưa.
"""
```

### Bước 4: Khởi tạo Agent với Backend và File Tools

Trong Deep Agents, khi bạn truyền tham số `backend` vào `create_deep_agent`, framework sẽ **tự động nạp 7 file tools** liên kết với backend đó vào danh sách công cụ của Agent!

Tạo file `src/agent_file_ops.py`:

```python
"""Coding Agent với năng lực File Operations hoàn chỉnh."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

from src.backend import get_workspace_backend
from src.prompts_v2 import FILE_OPS_SYSTEM_PROMPT

load_dotenv()


def build_file_ops_agent():
    """Khởi tạo agent tích hợp sẵn VFS và 7 file tools."""
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    # Khởi tạo backend trỏ vào workspace
    backend = get_workspace_backend("workspace")

    # Khi truyền backend, create_deep_agent tự động kích hoạt:
    # ls, glob, grep, read_file, write_file, edit_file, delete
    agent = create_deep_agent(
        model=llm,
        tools=[],  # Không cần custom tools vì file tools được harness tự inject
        backend=backend,
        system_prompt=FILE_OPS_SYSTEM_PROMPT,
    )

    return agent


if __name__ == "__main__":
    bot = build_file_ops_agent()

    # Ra lệnh cho Agent tìm và sửa bug trong workspace
    task = (
        "Trong thư mục workspace có hàm calculate_discount đang bị tính sai giá trị chiết khấu. "
        "Hãy tìm file đó, đọc hiểu nguyên nhân và sử dụng công cụ edit_file để sửa lại công thức cho đúng."
    )

    print(f"Bắt đầu thực thi nhiệm vụ: {task}\n")
    response = bot.invoke({"messages": [{"role": "user", "content": task}]})

    print("\n--- KẾT QUẢ TỪ AGENT ---")
    print(response["messages"][-1].content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm Agent:

```bash
python -m src.agent_file_ops
```

**Quan sát chuỗi hành vi thực tế của Agent**:
1. **Lệnh 1 (`glob`)**: Agent gọi `glob(pattern="**/*.py")` -> Nhận diện `src/math_service.py` và `tests/test_math.py`.
2. **Lệnh 2 (`grep`)**: Agent gọi `grep(pattern="calculate_discount", output_mode="content")` -> Xác định hàm nằm trong `src/math_service.py` tại dòng 4.
3. **Lệnh 3 (`read_file`)**: Agent gọi `read_file(path="src/math_service.py", offset=1, limit=20)` -> Phát hiện dòng code lỗi:
   ```python
   discount_amount = price * (discount_percent * 10)
   ```
4. **Lệnh 4 (`edit_file`)**: Agent gọi `edit_file`:
   - `path`: `"src/math_service.py"`
   - `old_string`: `"discount_amount = price * (discount_percent * 10)"`
   - `new_string`: `"discount_amount = price * (discount_percent / 100)"`
5. **Phản hồi**: Agent thông báo cho bạn biết đã định vị được file, chỉ rõ lỗi nhân với 10 thay vì chia cho 100, và đã sửa xong file bằng `edit_file`.

---

## 5. Checkpoint — Tự kiểm tra

Kiểm tra trực tiếp file trên đĩa để xác minh:

```bash
# Kiểm tra nội dung file math_service.py trong workspace
cat workspace/src/math_service.py
```

- [ ] Dòng tính `discount_amount` đã được sửa thành `price * (discount_percent / 100)`.
- [ ] Các hàm khác (`format_currency`) trong file vẫn còn nguyên vẹn, không bị mất.
- [ ] Chạy lệnh test xem bug đã thực sự được fix chưa:
  ```bash
  PYTHONPATH=workspace pytest workspace/tests/test_math.py
  ```
  Test phải **PASS** 100%!

---

## 6. Lỗi thường gặp & Best Practices

1. **Lỗi `PathOutsideRootError` hoặc Permission Denied**:
   - *Nguyên nhân*: Agent cố gắng truyền đường dẫn tuyệt đối dạng `/home/...` thay vì đường dẫn tương đối so với `root_dir`.
   - *Khắc phục*: Trong System Prompt, luôn hướng dẫn Agent: "Mọi đường dẫn file đều tính tương đối từ thư mục gốc của workspace (ví dụ: `src/main.py`, không dùng `/workspace/src/main.py`)".

2. **`edit_file` báo lỗi StringNotFound**:
   - *Nguyên nhân*: `old_string` không khớp 100% từng khoảng trắng, thụt đầu dòng (indentation) so với nội dung thực tế trong file.
   - *Khắc phục*: Khuyên Agent luôn gọi `read_file` trước để copy chính xác đoạn code cần thay thế bao gồm cả ký tự xuống dòng và khoảng trắng.

3. **Mất toàn bộ nội dung file do gọi nhầm `write_file`**:
   - *Nguyên nhân*: Trong v0.7+, `write_file` không kiểm tra file đã tồn tại hay chưa mà ghi đè trắng.
   - *Khắc phục*: Nghiêm cấm trong System Prompt hành vi dùng `write_file` để sửa code đang có.
