# Phase 5: Sub-agents — Phân chia chuyên môn

> **Mục tiêu**: Xây dựng kiến trúc Đa Đặc vụ (Multi-Agent Architecture) theo mô hình Điều phối viên (Coordinator Pattern), phân chia công việc cho 3 sub-agent chuyên trách: Researcher (khảo sát), Coder (viết code), Tester (kiểm thử), và nắm vững cơ chế cách ly ngữ cảnh (Context Isolation).
>
> **Thời gian ước tính**: 2 - 2.5 giờ
>
> **AgentSeek template tham khảo**: `deepagents/subagents-dynamic`
>
> **Prerequisites**: Hoàn thành [Phase 4: Code Execution](phase_04_code_execution.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Vấn đề của Monolithic Agent (Agent đơn khối)
Khi dự án phần mềm ngày càng lớn, việc nhồi nhét tất cả công cụ vào một Agent duy nhất (Monolithic Agent) dẫn đến nhiều vấn đề nghiêm trọng:
1. **Quá tải công cụ (Tool Overfitting & Confusion)**: Khi một Agent có 20-30 công cụ khác nhau (vừa đọc file, sửa file, chạy bash, gọi API, phân tích AST...), mô hình dễ bị lẫn lộn tham số và chọn sai công cụ.
2. **Ô nhiễm ngữ cảnh (Context Pollution)**: Khi Agent duyệt qua 15 file mã nguồn để tìm một thông tin nhỏ, toàn bộ 15 file đó nằm lại trong context window của Agent chính, làm loãng sự chú ý và lãng phí token cho các bước tiếp theo.
3. **Mâu thuẫn vai trò**: Một Agent vừa tự viết code vừa tự đánh giá code của mình thường có xu hướng "tự mãn", bỏ qua các lỗi tiềm ẩn do dùng chung điểm mù nhận thức.

### 1.2 Cơ chế Sub-agents và Cách ly ngữ cảnh (Context Isolation)
Trong Deep Agents, giải pháp tối ưu là phân tách thành các **Sub-agents** chuyên biệt hoạt động dưới sự điều phối của một **Coordinator (Lead Agent)**:
- **Tự động cấp tool `task`**: Khi bạn khai báo danh sách `subagents=[...]` trong `create_deep_agent`, framework sẽ tự động cung cấp cho Agent chính một công cụ đặc biệt tên là **`task`**.
- **Cách ly ngữ cảnh hoàn toàn (Strict Context Isolation)**:
  - Khi Coordinator gọi `task(subagent_name="researcher", description="Tìm hàm lỗi trong payment")`, Sub-agent được khởi tạo với một context window **hoàn toàn mới**.
  - Sub-agent **không nhìn thấy** toàn bộ lịch sử trò chuyện dài dòng trước đó của Coordinator.
  - Sub-agent chỉ nhìn thấy nhiệm vụ được giao trong `description` và các công cụ được cấp riêng cho nó.
  - Sau khi hoàn thành, Sub-agent chỉ gửi lại **bản báo cáo kết quả cuối cùng** về cho Coordinator. Toàn bộ hàng chục lượt gọi tool đọc file trung gian của Sub-agent được dọn dẹp sạch sẽ, giữ cho context của Coordinator luôn tinh gọn!

```
┌────────────────────────────────────────────────────────┐
│             COORDINATOR (LEAD TECH AGENT)              │
│       Quản lý kế hoạch, giao việc, tổng hợp báo cáo    │
└──────────────────────────┬─────────────────────────────┘
                           │ Lệnh: task(name, description)
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ RESEARCHER  │ │    CODER    │ │   TESTER    │
     │  (Chỉ đọc)  │ │ (Đọc & Sửa) │ │ (Chạy Test) │
     │             │ │             │ │             │
     │ read_file   │ │ edit_file   │ │ run_pytest  │
     │ grep, glob  │ │ write_file  │ │ linter      │
     │ ast_map     │ │ read_file   │ │             │
     └─────────────┘ └─────────────┘ └─────────────┘
```

### 1.3 Thiết kế bộ 3 Sub-agents cho Software Development
1. **Researcher (Nhà nghiên cứu)**:
   - *Công cụ*: `glob`, `grep`, `read_file`, `generate_repo_map`.
   - *Quyền hạn*: **Read-only**. Tuyệt đối không có công cụ sửa file hay chạy lệnh.
   - *Nhiệm vụ*: Định vị điểm lỗi, phân tích nguyên nhân gốc rễ (Root Cause Analysis), và viết bản đặc tả giải pháp.
2. **Coder (Lập trình viên)**:
   - *Công cụ*: `read_file`, `edit_file`, `write_file`.
   - *Nhiệm vụ*: Đọc bản đặc tả của Researcher và thực hiện phẫu thuật code một cách chính xác, tuân thủ coding conventions.
3. **Tester (Chuyên viên kiểm thử)**:
   - *Công cụ*: `run_pytest`, `read_file`.
   - *Nhiệm vụ*: Chạy test suite, kiểm tra độ bao phủ (coverage), và đưa ra bằng chứng khách quan xem code đã thực sự đạt chuẩn chưa.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [07_subagents.md](../guideline/07_subagents.md) | Cấu hình subagents & Tool `task` | Nắm rõ cú pháp khai báo dictionary subagents và nguyên lý cách ly context. |
| [08_async_subagents.md](../guideline/08_async_subagents.md) | Subagents bất đồng bộ (Parallel Execution) | Cách khởi chạy nhiều subagent song song để review nhiều file cùng lúc. |
| [18_dynamic_subagents.md](../guideline/18_dynamic_subagents.md) | Dynamic Subagents với QuickJS | Kỹ thuật nâng cao: cho phép LLM tự sinh mã gọi `task()` hàng loạt xử lý lô. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Khai báo các Sub-agents chuyên trách

Tạo file `src/subagents_config.py` để định nghĩa cấu hình và phân quyền cho từng Sub-agent:

```python
"""Cấu hình các Sub-agents chuyên biệt."""

from src.tools.test_runner import run_pytest

RESEARCHER_PROMPT = """Bạn là một Senior Code Analyst và Bug Investigator.
Nhiệm vụ của bạn là khảo sát codebase, định vị vị trí lỗi và phân tích nguyên nhân gốc rễ.
QUY TẮC: Bạn chỉ có quyền đọc file, không sửa code. Báo cáo của bạn phải chỉ rõ:
- Tên file và số dòng bị lỗi.
- Giải thích tại sao logic hiện tại bị sai.
- Đề xuất giải pháp sửa cụ thể (đoạn code cũ và đoạn code mới cần thay thế).
"""

CODER_PROMPT = """Bạn là một Senior Python Coder.
Nhiệm vụ của bạn là nhận giải pháp từ Researcher và tiến hành sửa code bằng `edit_file`.
QUY TẮC: Chỉ sửa đúng phần code được chỉ định, không tự ý sửa đổi các hàm khác ngoài phạm vi.
"""

TESTER_PROMPT = """Bạn là một QA Automation Engineer.
Nhiệm vụ của bạn là chạy bộ kiểm thử bằng công cụ `run_pytest`.
QUY TẮC: Phân tích khách quan output của pytest. Nếu có lỗi, trích xuất dòng fail và thông báo lại cho Coordinator.
"""


def get_software_team_subagents(model, backend):
    """Tạo danh sách cấu hình subagents chuyên môn hóa."""
    return [
        {
            "name": "researcher",
            "model": model,
            "backend": backend,
            "system_prompt": RESEARCHER_PROMPT,
            # Chỉ cấp công cụ đọc (sẽ được cấu hình qua permission ở Phase 6)
        },
        {
            "name": "coder",
            "model": model,
            "backend": backend,
            "system_prompt": CODER_PROMPT,
        },
        {
            "name": "tester",
            "model": model,
            "backend": backend,
            "tools": [run_pytest],
            "system_prompt": TESTER_PROMPT,
        },
    ]
```

### Bước 2: Xây dựng Coordinator Agent

Tạo file `src/agent_team.py` kết nối Coordinator với đội ngũ Sub-agents:

```python
"""Coordinator Agent điều phối nhóm lập trình viên AI."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.middleware.todo import TodoListMiddleware

from src.backend import get_workspace_backend
from src.subagents_config import get_software_team_subagents

load_dotenv()

COORDINATOR_SYSTEM_PROMPT = """Bạn là Engineering Manager và Lead Coordinator của một nhóm phát triển phần mềm.

Dưới quyền bạn có 3 sub-agents chuyên trách (gọi qua công cụ `task`):
1. `researcher`: Chuyên điều tra và định vị lỗi trong code.
2. `coder`: Chuyên dùng `edit_file` để thực thi sửa đổi code.
3. `tester`: Chuyên chạy `run_pytest` để kiểm chứng kết quả.

QUY TRÌNH ĐIỀU PHỐI BẮT BUỘC:
- BƯỚC 1: Gọi `task(subagent_name="researcher", description="...")` để khảo sát và tìm nguyên nhân lỗi.
- BƯỚC 2: Đọc báo cáo của `researcher`. Sau đó giao việc cho `coder`: `task(subagent_name="coder", description="...")` kèm theo chỉ dẫn sửa đổi cụ thể.
- BƯỚC 3: Sau khi `coder` sửa xong, giao việc cho `tester`: `task(subagent_name="tester", description="...")` để chạy pytest kiểm chứng.
- BƯỚC 4: Nếu `tester` báo cáo PASS -> Bạn tổng hợp kết quả báo cáo người dùng. Nếu FAIL -> Lặp lại bước giao việc cho coder sửa tiếp.

Bạn KHÔNG tự mình sửa code, hãy tận dụng sức mạnh của các sub-agents chuyên môn!
"""


def build_team_coordinator():
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")
    subagents = get_software_team_subagents(llm, backend)

    # Khởi tạo Coordinator Agent với tham số subagents
    agent = create_deep_agent(
        model=llm,
        backend=backend,
        subagents=subagents,  # Harness tự động nạp tool `task`
        middleware=[TodoListMiddleware()],
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
    )
    return agent


if __name__ == "__main__":
    bot = build_team_coordinator()

    mission = (
        "Khách hàng báo cáo rằng hệ thống tính thuế trong file math_service.py đang có vấn đề, "
        "khiến bộ unit test trong test_math.py bị lỗi. "
        "Hãy điều phối team của bạn để điều tra, sửa chữa và kiểm chứng lại toàn bộ!"
    )

    print(f"Nhiệm vụ bàn giao cho Coordinator:\n{mission}\n")
    response = bot.invoke({"messages": [{"role": "user", "content": mission}]})

    print("\n--- BÁO CÁO TỔNG HỢP TỪ LEAD COORDINATOR ---")
    print(response["messages"][-1].content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm toàn bộ đội ngũ AI:

```bash
python -m src.agent_team
```

**Quan sát luồng điều phối trên LangSmith Trace**:
1. **Coordinator nhận việc**: Quyết định không tự làm mà gọi tool:
   `task(subagent_name="researcher", description="Khảo sát lỗi thuế trong math_service.py")`
2. **Researcher Sub-agent thức tỉnh**:
   - Sử dụng context riêng biệt, gọi `grep` và `read_file`.
   - Tìm ra điều kiện logic bị sai.
   - Trả về báo cáo súc tích: *"Lỗi tại dòng 15: Biểu thức tính thuế đang bị thiếu dấu ngoặc đơn khiến phép nhân ưu tiên sai"*.
3. **Coordinator nhận báo cáo**: Gọi tiếp:
   `task(subagent_name="coder", description="Sửa dòng 15 của src/math_service.py theo đúng công thức: ...")`
4. **Coder Sub-agent hành động**:
   - Dùng `edit_file` thực hiện sửa đổi chính xác.
   - Báo cáo lại: *"Đã sửa thành công file src/math_service.py"*.
5. **Coordinator chuyển giao cho Tester**:
   `task(subagent_name="tester", description="Chạy pytest toàn bộ workspace/tests/test_math.py")`
6. **Tester kiểm tra**:
   - Chạy `run_pytest()`, nhận kết quả `PASSED: 2 passed`.
   - Báo cáo: *"Mọi bài test đều đã xanh!"*.
7. **Coordinator tổng kết**: Xuất báo cáo hoàn chỉnh cho người dùng bao gồm nguyên nhân, giải pháp và bằng chứng kiểm thử.

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Trên giao diện LangSmith Dashboard:
  - Trace của Coordinator phân nhánh rõ ràng thành 3 sub-traces con mang tên `researcher`, `coder`, `tester`.
  - Context của Coordinator không bị phình to bởi nội dung các file mà `researcher` đã đọc.
- [ ] Sub-agent `researcher` chỉ thực hiện đọc file và không phát sinh bất kỳ tool call `edit_file` nào.
- [ ] Toàn bộ chu trình từ Khảo sát -> Sửa -> Chạy Test diễn ra tự động 100% không cần can thiệp thủ công.

---

## 6. Lỗi thường gặp & Best Practices

1. **Coordinator "quên" gọi `task` mà tự làm một mình**:
   - *Nguyên nhân*: Prompt chưa nhấn mạnh đủ mạnh mẽ vai trò của Lead.
   - *Khắc phục*: Cấm Coordinator sử dụng các file tools trực tiếp, chỉ cho phép dùng `task` và `write_todos`.

2. **Lệnh giao việc trong `description` quá mơ hồ**:
   - *Nguyên nhân*: Coordinator chỉ nói "Hãy sửa bug đi", Sub-agent không có lịch sử hội thoại trước đó nên không biết bug gì.
   - *Khắc phục*: Trong prompt Coordinator, yêu cầu: *"Mọi lệnh giao việc trong tham số description phải tự chứa đầy đủ ngữ cảnh (self-contained), bao gồm tên file, triệu chứng và yêu cầu cụ thể"*.

3. **Sub-agents gọi lồng nhau vô hạn (Recursion Loop)**:
   - Framework ngăn chặn sub-agent gọi ngược lại coordinator để tránh vòng lặp vô tận. Luôn giữ cấu trúc hình cây 1 tầng (Coordinator -> Workers).
