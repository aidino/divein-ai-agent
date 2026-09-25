# Phase 4: Code Execution — Chạy code an toàn (3 Options)

> **Mục tiêu**: Cung cấp cho Coding Agent khả năng thực thi code, chạy unit tests (`pytest`), kiểm tra linter và cài đặt thư viện trong môi trường an toàn, hiểu rõ sự khác biệt giữa 3 mô hình Sandbox (Local, Docker AIO, Cloud MicroVM).
>
> **Thời gian ước tính**: 2.5 - 3 giờ
>
> **AgentSeek template tham khảo**: `deepagents/sandbox`
>
> **Prerequisites**: Hoàn thành [Phase 3: Task Planning](phase_03_task_planning.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Nghịch lý thực thi mã nguồn của Coding Agent
Một Coding Agent không thể tự kiểm chứng kết quả nếu nó không được phép chạy code. Nếu chỉ đọc và viết code tĩnh, Agent sẽ liên tục mắc phải các lỗi cú pháp ngớ ngẩn (typos, sai import, lệch kiểu dữ liệu) mà không hề hay biết.

Tuy nhiên, việc cho phép LLM thực thi các câu lệnh shell tùy ý mở ra rủi ro bảo mật khổng lồ:
- Agent có thể chạy nhầm lệnh phá hoại: `rm -rf /` hoặc xóa nhầm thư mục chứa source code của máy thật.
- Rủi ro Prompt Injection: Đoạn mã độc ẩn trong repository có thể lừa Agent gửi toàn bộ biến môi trường (`.env`, `AWS_SECRET_KEY`) về máy chủ kẻ tấn công.
- Treo tài nguyên: Vòng lặp vô tận (infinite loop) hoặc fork bomb làm tê liệt máy tính chủ.

Vì vậy, kiến trúc thực thi code (Execution Architecture) là trụ cột quan trọng nhất quyết định một Coding Agent có thể đưa vào sản xuất hay không.

### 1.2 So sánh 3 lựa chọn Sandbox

```
┌────────────────────────────────────────────────────────┐
│               Coding Agent Execution Options           │
├───────────────────┬───────────────────┬────────────────┤
│ Option A: Local   │ Option B: Docker  │ Option C: Cloud│
│ LocalShellBackend │ agent-infra/AIO   │ LangSmith/E2B  │
├───────────────────┼───────────────────┼────────────────┤
│ Host Bash Shell   │ Docker Container  │ MicroVM VM     │
│ Zero Setup        │ Môi trường cô lập │ Kernel cô lập  │
│ Dùng để học dev   │ Tự host an toàn   │ Chuẩn Enterprise│
└───────────────────┴───────────────────┴────────────────┘
```

1. **Option A: `LocalShellBackend` (Dành riêng cho Local Dev & Học tập)**:
   - Framework tích hợp sẵn lệnh thực thi trên bash cục bộ của máy bạn.
   - Ưu điểm: Không cần cài Docker hay tài khoản cloud, tốc độ phản hồi tức thì (0ms latency).
   - Nhược điểm: **Hoàn toàn không có rào cản bảo mật**. Chỉ được dùng trên các thư mục workspace thử nghiệm của cá nhân.

2. **Option B: Docker Container — AIO Sandbox ([agent-infra/sandbox](https://github.com/agent-infra/sandbox))**:
   - Sử dụng một container Docker All-in-One chứa sẵn Python, Node.js, Shell, Git và hỗ trợ giao tiếp qua REST API hoặc MCP (Model Context Protocol).
   - Agent áp dụng mô hình **Sandbox-as-Tool**: Thay vì Agent chạy lệnh trên máy host, nó gọi tool `run_command_in_sandbox(cmd)` để chuyển lệnh vào trong container Docker.
   - Thư mục code của host được mount vào container, mọi tiến trình chạy, test hay cài đặt package đều bị cô lập hoàn toàn bên trong Docker.

3. **Option C: Cloud Hardware-Virtualized Sandboxes (Chuẩn Production H2/2026)**:
   - **LangSmith Sandboxes (GA tháng 5/2026)** & **E2B**: Sử dụng công nghệ MicroVM (Firecracker/Kata Containers) cung cấp khả năng cô lập ở tầng nhân hệ điều hành (Kernel-level isolation).
   - Tính năng độc quyền: **Copy-on-write Snapshots & Forks**. Agent có thể "chụp ảnh" trạng thái môi trường test, sau đó phân nhánh thành 3 luồng chạy thử nghiệm 3 cách sửa lỗi song song mà không sợ xung đột!
   - Tự động tạm dừng (Auto-pause) khi không hoạt động để tiết kiệm chi phí.

4. **Bổ trợ: `CodeInterpreterMiddleware` (QuickJS In-Process)**:
   - Chạy engine JavaScript QuickJS ngay trong bộ nhớ của tiến trình Python mà không cần mở shell hay Docker.
   - Hỗ trợ mô hình **Programmatic Tool Calling (PTC)**: Cho phép Agent viết một đoạn script nhỏ để duyệt và lọc hàng nghìn file thông qua `tools.readFile()` chỉ trong 1 roundtrip duy nhất.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [05_virtual_filesystem.md](../guideline/05_virtual_filesystem.md) | LocalShellBackend | Nắm cách cấu hình shell cục bộ và các công cụ thực thi tích hợp. |
| [12_sandboxes.md](../guideline/12_sandboxes.md) | Mô hình Sandbox-as-Tool & Ranh giới bảo mật | Hiểu sâu cách kiến trúc hóa việc gửi lệnh thực thi sang môi trường cô lập. |
| [17_interpreters.md](../guideline/17_interpreters.md) | CodeInterpreterMiddleware & PTC | Xem cách QuickJS thực thi an toàn và nạp Programmatic Tool Calling. |

---

## 3. Hướng dẫn thực hành từng bước

Chúng ta sẽ triển khai **Option A** để bạn có thể chạy thử nghiệm ngay lập tức trên máy cục bộ, sau đó xem xét code mẫu chuẩn hóa của **Option B** (Docker Sandbox) và **Option C** (Cloud Sandbox).

### Bước 1: Xây dựng công cụ Test Runner an toàn (Option A)

Thay vì trao toàn quyền chạy bất kỳ lệnh bash nào cho LLM, một mẫu thiết kế an toàn là tạo ra **Targeted Execution Tool** (Công cụ thực thi có định hướng). Chúng ta chỉ cung cấp cho Agent công cụ `run_pytest` để chạy unit test trong thư mục workspace.

Tạo file `src/tools/test_runner.py`:

```python
"""Công cụ chạy kiểm thử tự động cho Coding Agent."""

import subprocess
import os
from langchain_core.tools import tool


@tool
def run_pytest(test_target: str = "tests") -> str:
    """Chạy bộ kiểm thử pytest trong thư mục workspace và trả về kết quả chi tiết.

    Args:
        test_target: Đường dẫn file test hoặc thư mục test (mặc định là 'tests').

    Returns:
        Toàn bộ output (stdout + stderr) của pytest, bao gồm số test pass/fail và stacktrace lỗi nếu có.
    """
    workspace_dir = os.path.abspath("workspace")
    full_target_path = os.path.join(workspace_dir, test_target)

    # Đảm bảo lệnh chạy với biến môi trường PYTHONPATH trỏ vào workspace
    env = os.environ.copy()
    env["PYTHONPATH"] = workspace_dir

    try:
        # Chạy pytest dưới dạng subprocess an toàn với giới hạn thời gian (timeout)
        result = subprocess.run(
            ["pytest", full_target_path, "-v", "--no-header"],
            cwd=workspace_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,  # Ngăn chặn vòng lặp vô tận
        )
        output = result.stdout + "\n" + result.stderr
        status = "PASSED" if result.returncode == 0 else "FAILED"
        return f"=== KẾT QUẢ PYTEST ({status}) ===\n{output.strip()}"
    except subprocess.TimeoutExpired:
        return "LỖI: Kiểm thử bị timeout sau 30 giây! Có thể code bị rơi vào vòng lặp vô tận (infinite loop)."
    except Exception as e:
        return f"LỖI HỆ THỐNG KHI CHẠY TEST: {str(e)}"
```

### Bước 2: Tích hợp Docker Sandbox (Option B: Tham khảo agent-infra/sandbox)

Nếu bạn có Docker trên máy và muốn cô lập hoàn toàn, đây là cách triển khai công cụ thực thi qua Docker container:

Tạo file `src/tools/docker_sandbox_runner.py`:

```python
"""Công cụ thực thi code trong Docker Sandbox cô lập (Mô hình Option B)."""

import subprocess
import os
from langchain_core.tools import tool


@tool
def execute_in_docker_sandbox(command: str) -> str:
    """Thực thi một câu lệnh shell bên trong Docker container cô lập.
    
    Container này chứa môi trường Python sạch, không có quyền truy cập vào file hệ thống máy host.
    """
    workspace_dir = os.path.abspath("workspace")
    
    # Lệnh chạy docker ephemeral container mount thư mục workspace
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{workspace_dir}:/app",
        "-w", "/app",
        "--network", "none",  # Cắt toàn bộ internet để chống rò rỉ dữ liệu
        "--memory", "512m",   # Giới hạn RAM chống tràn bộ nhớ
        "python:3.12-slim",
        "bash", "-c", command
    ]
    
    try:
        res = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=45)
        return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\nEXIT CODE: {res.returncode}"
    except Exception as e:
        return f"Docker execution error: {e}"
```

### Bước 3: Lắp ráp Coding Agent có năng lực TDD (Test-Driven Development)

Tạo file `src/agent_executor.py`:

```python
"""Coding Agent với chu trình TDD: Code -> Run Test -> Analyze Error -> Fix."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.middleware.todo import TodoListMiddleware

from src.backend import get_workspace_backend
from src.tools.test_runner import run_pytest

load_dotenv()

EXECUTOR_SYSTEM_PROMPT = """Bạn là một Senior Python Developer thực hành văn hóa Test-Driven Development (TDD).

QUY TRÌNH BẮT BUỘC KHI SỬA CODE:
1. CHẠY TEST ĐẦU TIÊN: Trước khi sửa bất kỳ dòng code nào, hãy chạy `run_pytest` để xác định chính xác các test case đang fail và đọc stacktrace lỗi.
2. PHÂN TÍCH NGUYÊN NHÂN: Đọc file code tương ứng để hiểu tại sao logic lại không thỏa mãn assertion của test.
3. SỬA CODE BẰNG EDIT_FILE: Tiến hành chỉnh sửa tối giản nhất có thể để pass test.
4. TỰ ĐỘNG VERIFY: Sau khi sửa, BẮT BUỘC phải gọi lại `run_pytest` để kiểm chứng.
   - Nếu test PASS: Thông báo hoàn tất.
   - Nếu test vẫn FAIL: Đọc tiếp lỗi mới và lặp lại bước sửa cho đến khi xanh toàn bộ!
"""


def build_executor_agent():
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")
    todo_middleware = TodoListMiddleware()

    # Cung cấp tool run_pytest kèm theo các file tools
    tools = [run_pytest]

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        backend=backend,
        middleware=[todo_middleware],
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
    )
    return agent
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chuẩn bị một ca kiểm thử bị lỗi trong `workspace/tests/test_math.py`:

```python
# Thêm test case mới vào workspace/tests/test_math.py
def test_tax_bracket():
    from src.math_service import calculate_tax
    # Dưới 10 triệu thuế 10% -> 8 triệu thuế phải là 800.000
    assert calculate_tax(8_000_000.0) == 800_000.0
    # Trên 10 triệu thuế 20% -> 20 triệu thuế phải là 4.000.000
    assert calculate_tax(20_000_000.0) == 4_000_000.0
```

Chạy Agent để tự động giải quyết:

```bash
python -m src.agent_executor
```

Đoạn lệnh giao việc:
```python
if __name__ == "__main__":
    bot = build_executor_agent()
    task = (
        "Bộ test trong `tests/test_math.py` đang có lỗi fail ở hàm calculate_tax. "
        "Hãy chạy `run_pytest` để xem lỗi, phân tích nguyên nhân và sửa lại `src/math_service.py` "
        "cho đến khi toàn bộ test case đều PASS!"
    )
    response = bot.invoke({"messages": [{"role": "user", "content": task}]})
    print("\n--- PHẢN HỒI CUỐI CÙNG TỪ AGENT ---")
    print(response["messages"][-1].content)
```

**Nhật ký hành động của Agent**:
1. Agent gọi `run_pytest()` -> Nhận output: `FAILED tests/test_math.py::test_tax_bracket - AssertionError`.
2. Agent đọc stacktrace -> Thấy hàm `calculate_tax` tính sai ở mốc trên 10 triệu.
3. Agent dùng `read_file` đọc logic trong `src/math_service.py`.
4. Agent dùng `edit_file` sửa lại biểu thức điều kiện `if income > 10_000_000`.
5. Agent KHÔNG kết luận ngay! Nó gọi lại `run_pytest()` lượt thứ hai.
6. Output trả về: `=== KẾT QUẢ PYTEST (PASSED) === 2 passed in 0.05s`.
7. Agent vui mừng báo cáo: *"Toàn bộ 2/2 test case đã passed thành công sau khi sửa điều kiện phân loại thuế!"*

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Lệnh `run_pytest` thực thi thành công từ trong Agent và bắt được cả trường hợp test pass lẫn test fail.
- [ ] Khi gặp test fail, Agent không bỏ cuộc mà biết tự động đọc stacktrace và dùng `edit_file` để sửa code.
- [ ] Agent luôn thực hiện ít nhất một lượt gọi `run_pytest` sau cùng để xác nhận code đã pass trước khi trả lời người dùng.
- [ ] Chạy thủ công lại ở terminal: `PYTHONPATH=workspace pytest workspace/tests` -> hiển thị toàn bộ màu xanh!

---

## 6. Lỗi thường gặp & Best Practices

1. **Lỗi `ModuleNotFoundError` khi chạy pytest**:
   - *Nguyên nhân*: Thư mục `workspace` chưa được thêm vào `PYTHONPATH`.
   - *Khắc phục*: Trong tool `run_pytest`, hãy luôn thiết lập `env["PYTHONPATH"] = workspace_dir` như code mẫu.

2. **Tiến trình bị treo mãi mãi (Infinite Test Execution)**:
   - *Nguyên nhân*: Mã nguồn người dùng viết chứa `while True` hoặc chờ input từ stdin.
   - *Khắc phục*: Bắt buộc đặt tham số `timeout=30` trong lệnh `subprocess.run`.

3. **Chạy nhầm lệnh phá hoại**:
   - Nếu bạn cung cấp bash tổng quát cho Agent, luôn cấu hình `timeout`, giới hạn user quyền thấp (non-root) và không bao giờ mount các thư mục nhạy cảm (`~/.ssh`, `/etc`) vào sandbox.
